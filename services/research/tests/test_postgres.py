from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from fable5_research.repository import ResearchRepository
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

DATABASE_URL = os.environ.get("FABLE5_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    DATABASE_URL is None,
    reason="set FABLE5_TEST_DATABASE_URL after creating Phase 6 acceptance runs",
)

PHASE6_TABLES = (
    "research_pipeline_runs",
    "research_pipeline_snapshot_bindings",
    "research_pipeline_attempts",
    "research_feature_rows",
    "research_score_outputs",
    "research_baseline_comparisons",
    "research_text_extractions",
    "research_text_corroborations",
)


def _repository() -> ResearchRepository:
    assert DATABASE_URL is not None
    return ResearchRepository(DATABASE_URL)


def test_phase6_versioned_phase4_snapshot_contracts_coexist_with_prior_rows() -> None:
    assert DATABASE_URL is not None
    engine = create_engine(DATABASE_URL)
    try:
        with engine.connect() as connection:
            constraints = {
                row["conname"]: row["definition"]
                for row in connection.execute(
                    text(
                        "SELECT conname, pg_get_constraintdef(oid) AS definition "
                        "FROM pg_constraint "
                        "WHERE conname IN ("
                        "'ck_data_snapshot_frozen_versions',"
                        "'ck_data_quality_finding_identities',"
                        "'ck_data_quality_finding_code')"
                    )
                ).mappings()
            }
            snapshot_versions = constraints["ck_data_snapshot_frozen_versions"]
            assert "phase4-synthetic-pit-fixtures-v1" in snapshot_versions
            assert "phase6-synthetic-pit-fixtures-v1" in snapshot_versions
            quality_versions = constraints["ck_data_quality_finding_identities"]
            assert "phase4-data-quality-v1" in quality_versions
            assert "phase6-data-contract-quality-v1" in quality_versions
            quality_codes = constraints["ck_data_quality_finding_code"]
            for phase6_code in (
                "pit_classification_invalid",
                "document_content_hash_mismatch",
                "document_correction_timing_invalid",
                "official_corroboration_mismatch",
            ):
                assert phase6_code in quality_codes

            fixture_counts = {
                row["fixture_set_version"]: row["row_count"]
                for row in connection.execute(
                    text(
                        "SELECT fixture_set_version, count(*) AS row_count "
                        "FROM data_snapshots "
                        "GROUP BY fixture_set_version"
                    )
                ).mappings()
            }
            assert fixture_counts["phase4-synthetic-pit-fixtures-v1"] > 0
            assert fixture_counts["phase6-synthetic-pit-fixtures-v1"] > 0
    finally:
        engine.dispose()


def test_phase6_repository_reconstructs_complete_a_b_c_artifacts_and_children() -> None:
    repository = _repository()
    try:
        summaries = repository.list_runs(limit=100)
        assert {item.configuration_id.value for item in summaries} >= {
            "phase6-a-pass-v1",
            "phase6-a-fail-cost-v1",
            "phase6-b-pass-v1",
            "phase6-b-fail-crash-v1",
            "phase6-c-pass-v1",
        }
        artifacts = [repository.get_run(item.run_id) for item in summaries]
        assert {item.family.value for item in artifacts} == {
            "A_CROSS_SECTIONAL_EQUITY_RANKING",
            "B_TIME_SERIES_MOMENTUM_REGIME",
            "C_OFFICIAL_EVENT_TEXT_OVERLAY",
        }
        for artifact in artifacts:
            assert artifact.snapshot_bindings
            assert artifact.feature_rows
            assert len(artifact.scores) == len(artifact.feature_rows)
            assert len(artifact.attempts) == artifact.phase5_evaluation.raw_trial_count == 6
            assert len({item.phase5_trial_id for item in artifact.attempts}) == 6
            assert len({item.phase5_trial_key for item in artifact.attempts}) == 6
            assert artifact.phase5_evaluation.phase5_trial_set_sha256 is not None
            assert artifact.baseline_comparisons
            assert artifact.no_real_performance_claimed is True
            assert artifact.paper_approval_granted is False
            assert repository.get_run(artifact.run_id) == artifact
    finally:
        repository.dispose()


def test_phase6_attempt_lineage_uses_the_phase5_report_scoped_trial_key() -> None:
    assert DATABASE_URL is not None
    engine = create_engine(DATABASE_URL)
    try:
        with engine.connect() as connection:
            attempt_fk = connection.execute(
                text(
                    "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                    "WHERE conrelid = 'research_pipeline_attempts'::regclass "
                    "AND conname = 'fk_research_pipeline_attempt_trial'"
                )
            ).scalar_one()
            assert attempt_fk == (
                "FOREIGN KEY (phase5_report_id, phase5_trial_id) "
                "REFERENCES evaluation_trials(report_id, trial_id) ON DELETE RESTRICT"
            )

            evaluation_trial_keys = tuple(
                connection.execute(
                    text(
                        "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                        "WHERE conrelid = 'evaluation_trials'::regclass "
                        "AND contype IN ('p', 'u') ORDER BY conname"
                    )
                ).scalars()
            )
            assert "PRIMARY KEY (report_id, trial_id)" in evaluation_trial_keys
            assert "UNIQUE (trial_id)" not in evaluation_trial_keys

            mismatch_count = connection.execute(
                text(
                    "SELECT count(*) FROM research_pipeline_attempts AS attempt "
                    "JOIN research_pipeline_runs AS run ON run.id = attempt.run_id "
                    "LEFT JOIN evaluation_trials AS trial "
                    "ON trial.report_id = attempt.phase5_report_id "
                    "AND trial.trial_id = attempt.phase5_trial_id "
                    "WHERE (run.evaluation_report_id IS NULL AND ("
                    "attempt.phase5_report_id IS NOT NULL OR attempt.phase5_trial_id IS NOT NULL "
                    "OR attempt.phase5_trial_key IS NOT NULL"
                    ")) OR (run.evaluation_report_id IS NOT NULL AND ("
                    "attempt.phase5_report_id IS DISTINCT FROM run.evaluation_report_id "
                    "OR trial.trial_id IS NULL "
                    "OR trial.trial_key IS DISTINCT FROM attempt.phase5_trial_key "
                    "OR trial.status IS DISTINCT FROM attempt.status "
                    "OR trial.config_sha256 IS DISTINCT FROM attempt.config_sha256))"
                )
            ).scalar_one()
            assert mismatch_count == 0
            assert (
                connection.execute(
                    text(
                        "SELECT bool_and(NOT (payload ? 'phase5_report_id')) "
                        "FROM research_pipeline_attempts"
                    )
                ).scalar_one()
                is True
            )
    finally:
        engine.dispose()


def test_phase6_completeness_is_deferred_from_root_and_all_seven_child_tables() -> None:
    assert DATABASE_URL is not None
    engine = create_engine(DATABASE_URL)
    try:
        with engine.connect() as connection:
            installed = tuple(
                connection.execute(
                    text(
                        "SELECT relation.relname, trigger.tgname, trigger.tgdeferrable, "
                        "trigger.tginitdeferred, procedure.proname "
                        "FROM pg_trigger AS trigger "
                        "JOIN pg_class AS relation ON relation.oid = trigger.tgrelid "
                        "JOIN pg_proc AS procedure ON procedure.oid = trigger.tgfoid "
                        "WHERE NOT trigger.tgisinternal "
                        "AND procedure.proname = 'validate_phase6_run_completeness' "
                        "ORDER BY relation.relname"
                    )
                )
            )
            expected = tuple(
                sorted(
                    (
                        table,
                        (
                            "research_pipeline_runs_complete"
                            if table == "research_pipeline_runs"
                            else f"{table}_run_complete"
                        ),
                        True,
                        True,
                        "validate_phase6_run_completeness",
                    )
                    for table in PHASE6_TABLES
                )
            )
            assert installed == expected
    finally:
        engine.dispose()


def test_phase6_deferred_completeness_rejects_incomplete_root_and_extra_child() -> None:
    assert DATABASE_URL is not None
    engine = create_engine(DATABASE_URL)
    try:
        with engine.connect() as connection:
            run_id = uuid4()
            fingerprint = uuid4().hex * 2
            artifact_sha256 = uuid4().hex * 2
            connection.execute(
                text(
                    "INSERT INTO research_pipeline_runs ("
                    "id, schema_version, request_fingerprint_sha256, artifact_sha256, "
                    "configuration_id, configuration_sha256, mapping_id, canonical_family, "
                    "specification_sha256, feature_lineage_sha256, snapshot_bundle_sha256, "
                    "phase5_policy_id, phase5_policy_version, phase5_policy_sha256, "
                    "phase5_fixture_id, phase5_fixture_sha256, evaluation_report_id, "
                    "evaluation_outcome_id, promotion_state, status, artifact_payload, "
                    "reason_codes, warnings, no_real_performance_claimed, "
                    "paper_approval_granted) "
                    "SELECT :run_id, schema_version, CAST(:fingerprint AS text), "
                    "CAST(:artifact_sha256 AS text), "
                    "configuration_id, configuration_sha256, mapping_id, canonical_family, "
                    "specification_sha256, feature_lineage_sha256, snapshot_bundle_sha256, "
                    "phase5_policy_id, phase5_policy_version, phase5_policy_sha256, "
                    "phase5_fixture_id, phase5_fixture_sha256, evaluation_report_id, "
                    "evaluation_outcome_id, promotion_state, status, "
                    "jsonb_set(artifact_payload, '{request_fingerprint_sha256}', "
                    "to_jsonb(CAST(:fingerprint AS text)), false), reason_codes, warnings, "
                    "no_real_performance_claimed, paper_approval_granted "
                    "FROM research_pipeline_runs ORDER BY id LIMIT 1"
                ),
                {
                    "run_id": run_id,
                    "fingerprint": fingerprint,
                    "artifact_sha256": artifact_sha256,
                },
            )
            with pytest.raises(
                DBAPIError,
                match="Phase 6 attempt registry does not exactly match Phase 5 trials",
            ):
                connection.execute(
                    text("SET CONSTRAINTS research_pipeline_runs_complete IMMEDIATE")
                )
            connection.rollback()

            ordinal = 999
            row_id = uuid4()
            sample_id = f"phase6-completeness-probe-{uuid4()}"
            row_sha256 = uuid4().hex * 2
            connection.execute(
                text(
                    "INSERT INTO research_feature_rows ("
                    "run_id, ordinal, row_id, sample_id, entity_id, decision_time_utc, "
                    "row_sha256, payload) "
                    "SELECT run_id, :ordinal, :row_id, :sample_id, entity_id, "
                    "decision_time_utc, :row_sha256, "
                    "jsonb_set(jsonb_set(jsonb_set(jsonb_set(payload, '{ordinal}', "
                    "to_jsonb(CAST(:ordinal_json AS integer)), false), '{row_id}', "
                    "to_jsonb(CAST(:row_id_json AS text)), false), '{sample_id}', "
                    "to_jsonb(CAST(:sample_id_json AS text)), false), '{row_sha256}', "
                    "to_jsonb(CAST(:row_sha256_json AS text)), false) "
                    "FROM research_feature_rows ORDER BY run_id, ordinal LIMIT 1"
                ),
                {
                    "ordinal": ordinal,
                    "row_id": row_id,
                    "sample_id": sample_id,
                    "row_sha256": row_sha256,
                    "ordinal_json": ordinal,
                    "row_id_json": str(row_id),
                    "sample_id_json": sample_id,
                    "row_sha256_json": row_sha256,
                },
            )
            with pytest.raises(
                DBAPIError,
                match="Phase 6 research run has incomplete child registries",
            ):
                connection.execute(
                    text("SET CONSTRAINTS research_feature_rows_run_complete IMMEDIATE")
                )
            connection.rollback()
    finally:
        engine.dispose()


def test_phase6_repository_concurrent_identical_create_is_idempotent() -> None:
    seed_repository = _repository()
    try:
        artifact = next(
            seed_repository.get_run(item.run_id)
            for item in seed_repository.list_runs(limit=100)
            if item.configuration_id.value == "phase6-a-pass-v1"
        )
    finally:
        seed_repository.dispose()

    barrier = Barrier(2)

    def create() -> tuple[str, str]:
        repository = _repository()
        try:
            barrier.wait()
            stored = repository.create_run(artifact)
            return str(stored.run_id), stored.artifact_sha256
        finally:
            repository.dispose()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = tuple(executor.map(lambda _: create(), range(2)))

    assert results[0] == results[1] == (str(artifact.run_id), artifact.artifact_sha256)


def test_phase6_payload_column_trigger_rejects_inconsistent_attempt_insert() -> None:
    assert DATABASE_URL is not None
    engine = create_engine(DATABASE_URL)
    try:
        with engine.connect() as connection:
            run_id = connection.execute(
                text("SELECT id FROM research_pipeline_runs ORDER BY id LIMIT 1")
            ).scalar_one()
            payload = {
                "ordinal": 99,
                "phase5_trial_id": None,
                "phase5_trial_key": None,
                "status": "blocked",
                "configuration_sha256": "2" * 64,
                "failure_reason": "synthetic payload mismatch probe",
                "attempt_sha256": "3" * 64,
            }
            with pytest.raises(DBAPIError, match="attempt payload mismatch"):
                connection.execute(
                    text(
                        "INSERT INTO research_pipeline_attempts "
                        "(run_id, ordinal, phase5_trial_id, status, config_sha256, "
                        "failure_reason, payload, attempt_sha256) VALUES "
                        "(:run_id, 99, NULL, 'blocked', :config_sha256, :failure_reason, "
                        "CAST(:payload AS jsonb), :attempt_sha256)"
                    ),
                    {
                        "run_id": run_id,
                        "config_sha256": "1" * 64,
                        "failure_reason": "synthetic payload mismatch probe",
                        "payload": json.dumps(payload),
                        "attempt_sha256": "3" * 64,
                    },
                )
            connection.rollback()
    finally:
        engine.dispose()


def test_phase6_all_eight_tables_reject_update_delete_and_truncate() -> None:
    assert DATABASE_URL is not None
    engine = create_engine(DATABASE_URL)
    try:
        with engine.connect() as connection:
            for table in PHASE6_TABLES:
                assert connection.execute(text(f"SELECT count(*) FROM {table}")).scalar_one() > 0
                column = connection.execute(
                    text(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_schema = 'public' AND table_name = :table "
                        "ORDER BY ordinal_position LIMIT 1"
                    ),
                    {"table": table},
                ).scalar_one()
                for statement in (
                    f'UPDATE {table} SET "{column}" = "{column}"',
                    f"DELETE FROM {table}",
                    f"TRUNCATE {table} CASCADE",
                ):
                    with pytest.raises(
                        DBAPIError, match="Phase 6 research artifacts are append-only"
                    ):
                        connection.execute(text(statement))
                    connection.rollback()
    finally:
        engine.dispose()
