from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from fable5_backtester.repository import EvaluationRepository
from fable5_data.contracts import DataCapability
from fable5_data.repository import SnapshotRepository
from fable5_research.contracts import (
    FamilyBEvidence,
    ResearchConfigurationId,
    ResearchRunCreateRequest,
)
from fable5_research.repository import ResearchRepository
from fable5_research.workflow import ResearchWorkflow
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
                        "'ck_data_quality_finding_code',"
                        "'ck_research_pipeline_snapshot_binding_identity')"
                    )
                ).mappings()
            }
            snapshot_versions = constraints["ck_data_snapshot_frozen_versions"]
            assert "phase4-synthetic-pit-fixtures-v1" in snapshot_versions
            assert "phase6-synthetic-pit-fixtures-v1" in snapshot_versions
            assert "phase6-synthetic-pit-fixtures-v2" in snapshot_versions
            quality_versions = constraints["ck_data_quality_finding_identities"]
            assert "phase4-data-quality-v1" in quality_versions
            assert "phase6-data-contract-quality-v1" in quality_versions
            assert "phase6-data-contract-quality-v2" in quality_versions
            assert (
                "macro_regime_inputs"
                in constraints["ck_research_pipeline_snapshot_binding_identity"]
            )
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
            assert fixture_counts["phase6-synthetic-pit-fixtures-v2"] > 0
    finally:
        engine.dispose()


def test_phase6_repository_reconstructs_complete_a_b_c_artifacts_and_children(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _repository()
    try:
        with monkeypatch.context() as context:
            context.setattr(
                ResearchRepository,
                "_load_run",
                lambda *args, **kwargs: pytest.fail(
                    "summary listing must not reconstruct complete research artifacts"
                ),
            )
            summaries = repository.list_runs(limit=100)
        assert {item.configuration_id.value for item in summaries} >= {
            "phase6-a-pass-v2",
            "phase6-a-fail-cost-v2",
            "phase6-b-pass-v2",
            "phase6-b-fail-crash-v2",
            "phase6-c-pass-v2",
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
            assert len(artifact.model_output_sets) == 4
            for output_set in artifact.model_output_sets:
                assert len(output_set.outputs) == len(artifact.feature_rows)
                assert len(output_set.ledger_cells) == len(artifact.feature_rows)
                assert tuple(item.sample_id for item in output_set.outputs) == tuple(
                    item.sample_id for item in output_set.ledger_cells
                )
                assert tuple(item.output_value for item in output_set.outputs) == tuple(
                    item.model_output for item in output_set.ledger_cells
                )
            needs_calendar = (
                DataCapability.TRADING_CALENDAR in artifact.specification.required_capabilities
            )
            assert bool(artifact.calendar_source_references) is needs_calendar
            assert all(
                item.capability is DataCapability.TRADING_CALENDAR
                and item.record_type == "calendar_session"
                for item in artifact.calendar_source_references
            )
            if isinstance(artifact.family_evidence, FamilyBEvidence):
                evidence = artifact.family_evidence
                assert evidence.rate_evidence_available is False
                assert evidence.rate_evidence_reason == "rate_regime_source_unavailable"
                assert evidence.crisis_geometry_available is False
                assert evidence.crisis_evidence_reason == ("crisis_window_geometry_unavailable")
                assert evidence.crash_evidence_complete is False
                assert evidence.crash_concentration is None
                assert evidence.crash_concentration_limit is None
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


def test_phase6_database_installs_canonical_hash_and_identity_authority() -> None:
    assert DATABASE_URL is not None
    engine = create_engine(DATABASE_URL)
    try:
        with engine.connect() as connection:
            functions = {
                row["proname"]: row["definition"]
                for row in connection.execute(
                    text(
                        "SELECT proname, pg_get_functiondef(oid) AS definition "
                        "FROM pg_proc WHERE proname IN ("
                        "'phase6_canonical_json','phase6_domain_sha256','phase6_sha1',"
                        "'phase6_uuid5',"
                        "'validate_phase6_payload_columns','validate_phase6_run_completeness')"
                    )
                ).mappings()
            }
            assert set(functions) == {
                "phase6_canonical_json",
                "phase6_domain_sha256",
                "phase6_sha1",
                "phase6_uuid5",
                "validate_phase6_payload_columns",
                "validate_phase6_run_completeness",
            }
            payload_validator = functions["validate_phase6_payload_columns"]
            assert "phase6-research-artifact-v2" in payload_validator
            assert "phase6-research-request-v2" in payload_validator
            assert "phase6-research-specification-v2" in payload_validator
            assert "phase6-phase5-model-output-registry-entry-v2" in payload_validator
            assert "Phase 6 research artifact canonical hash mismatch" in payload_validator
            assert "Phase 6 research request canonical identity mismatch" in payload_validator
            completeness = functions["validate_phase6_run_completeness"]
            assert "phase6-phase5-trial-set-v1" in completeness
            assert "Phase 6 artifact source reference lineage mismatch" in completeness
            assert "TG_TABLE_NAME <> 'research_pipeline_runs'" in completeness
            assert "current_run.xmin = pg_current_xact_id()::xid" in completeness
            assert completeness.index("current_run.xmin = pg_current_xact_id()::xid") < (
                completeness.index("SELECT * INTO run_row")
            )
    finally:
        engine.dispose()


def test_phase6_own_transaction_children_defer_to_the_root_completeness_event() -> None:
    assert DATABASE_URL is not None
    engine = create_engine(DATABASE_URL)
    try:
        with engine.connect() as connection:
            run_id = uuid4()
            connection.execute(
                text(
                    "ALTER TABLE research_pipeline_runs DISABLE TRIGGER "
                    "research_pipeline_runs_05_payload_columns"
                )
            )
            connection.execute(
                text(
                    "ALTER TABLE research_pipeline_runs DISABLE TRIGGER "
                    "research_pipeline_runs_10_lineage"
                )
            )
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
                    "SELECT :run_id, schema_version, :fingerprint, :artifact_sha256, "
                    "configuration_id, configuration_sha256, mapping_id, canonical_family, "
                    "specification_sha256, feature_lineage_sha256, snapshot_bundle_sha256, "
                    "phase5_policy_id, phase5_policy_version, phase5_policy_sha256, "
                    "phase5_fixture_id, phase5_fixture_sha256, evaluation_report_id, "
                    "evaluation_outcome_id, promotion_state, status, artifact_payload, "
                    "reason_codes, warnings, no_real_performance_claimed, "
                    "paper_approval_granted "
                    "FROM research_pipeline_runs ORDER BY created_at_utc LIMIT 1"
                ),
                {
                    "run_id": run_id,
                    "fingerprint": uuid4().hex * 2,
                    "artifact_sha256": uuid4().hex * 2,
                },
            )
            connection.execute(
                text(
                    "INSERT INTO research_feature_rows ("
                    "run_id, ordinal, row_id, sample_id, entity_id, decision_time_utc, "
                    "row_sha256, payload) "
                    "SELECT :run_id, ordinal, row_id, sample_id, entity_id, "
                    "decision_time_utc, row_sha256, payload "
                    "FROM research_feature_rows ORDER BY run_id, ordinal LIMIT 1"
                ),
                {"run_id": run_id},
            )

            # The child event sees the own-transaction root and delegates the
            # expensive final-state check to that root's deferred event.
            connection.execute(text("SET CONSTRAINTS research_feature_rows_run_complete IMMEDIATE"))
            # The root event remains authoritative and rejects this deliberately
            # incomplete registry when it is forced.
            with pytest.raises(
                DBAPIError,
                match="Phase 6 Phase 5 trial, gate, and research-ledger lineage mismatch",
            ):
                connection.execute(
                    text("SET CONSTRAINTS research_pipeline_runs_complete IMMEDIATE")
                )
            connection.rollback()

            with pytest.raises(DBAPIError, match="fk_research_feature_row_run"):
                connection.execute(
                    text(
                        "INSERT INTO research_feature_rows ("
                        "run_id, ordinal, row_id, sample_id, entity_id, decision_time_utc, "
                        "row_sha256, payload) "
                        "SELECT :run_id, ordinal, row_id, sample_id, entity_id, "
                        "decision_time_utc, row_sha256, payload "
                        "FROM research_feature_rows ORDER BY run_id, ordinal LIMIT 1"
                    ),
                    {"run_id": uuid4()},
                )
            connection.rollback()
    finally:
        engine.dispose()


def test_phase6_macro_rate_payload_equivalence_is_numeric_and_strictly_scoped() -> None:
    assert DATABASE_URL is not None
    engine = create_engine(DATABASE_URL)
    left = {
        "record_type": "macro_rate_observation",
        "series_id": "001",
        "released_at": "2020-01-02T13:00:00Z",
        "rate_value": "1.60",
        "previous_rate_value": "1.50",
        "rate_change": "0.10",
    }
    equivalent = {
        **left,
        "released_at": "2020-01-02T13:00:00.000000Z",
        "rate_value": "1.6",
        "previous_rate_value": "1.5",
        "rate_change": "0.1",
    }
    changed_rate = {**equivalent, "rate_change": "0.2"}
    changed_identifier = {**equivalent, "series_id": "1"}
    statement = text(
        "SELECT phase6_source_payload_equivalent("
        ":capability, CAST(:left AS jsonb), CAST(:right AS jsonb))"
    )
    try:
        with engine.connect() as connection:
            function_definition = connection.execute(
                text(
                    "SELECT pg_get_functiondef("
                    "'validate_phase5_report_source_lineage(uuid)'::regprocedure)"
                )
            ).scalar_one()
            assert "phase6_source_payload_equivalent" in function_definition

            def compare(right: dict[str, object]) -> bool:
                return bool(
                    connection.execute(
                        statement,
                        {
                            "capability": "macro_regime_inputs",
                            "left": json.dumps(left),
                            "right": json.dumps(right),
                        },
                    ).scalar_one()
                )

            assert compare(equivalent) is True
            assert compare(changed_rate) is False
            assert compare(changed_identifier) is False
            assert (
                connection.execute(
                    statement,
                    {
                        "capability": "ohlcv",
                        "left": json.dumps(left),
                        "right": json.dumps(equivalent),
                    },
                ).scalar_one()
                is False
            )
    finally:
        engine.dispose()


def test_phase6_database_recomputes_root_and_child_hash_identities() -> None:
    assert DATABASE_URL is not None
    engine = create_engine(DATABASE_URL)
    try:
        with engine.connect() as connection:
            mismatches = {
                row["artifact_kind"]: row["mismatch_count"]
                for row in connection.execute(
                    text(
                        "SELECT 'run' AS artifact_kind, count(*) AS mismatch_count "
                        "FROM research_pipeline_runs WHERE "
                        "artifact_sha256 IS DISTINCT FROM phase6_domain_sha256("
                        "'phase6-research-artifact-v2', artifact_payload) "
                        "OR request_fingerprint_sha256 IS DISTINCT FROM phase6_domain_sha256("
                        "'phase6-research-request-v2', jsonb_build_object("
                        "'mapping_id', artifact_payload->'mapping_id', "
                        "'mapping_version', artifact_payload->'mapping_version', "
                        "'mapping_input_sha256', artifact_payload->'mapping_input_sha256', "
                        "'snapshot_bundle_sha256', artifact_payload->'snapshot_bundle_sha256', "
                        "'configuration_id', artifact_payload->'configuration_id', "
                        "'configuration_sha256', artifact_payload->'configuration_sha256', "
                        "'specification_sha256', "
                        "artifact_payload#>'{specification,specification_sha256}', "
                        "'code_version_git_sha', artifact_payload->'code_version_git_sha', "
                        "'random_seed', artifact_payload->'random_seed', "
                        "'pipeline_input_sha256', artifact_payload->'pipeline_input_sha256')) "
                        "OR id IS DISTINCT FROM phase6_uuid5("
                        "'09972cb7-9a87-543c-a70a-3835ee8e593c'::uuid, "
                        "request_fingerprint_sha256) "
                        "UNION ALL SELECT 'snapshot_binding', count(*) "
                        "FROM research_pipeline_snapshot_bindings WHERE "
                        "binding_sha256 IS DISTINCT FROM phase6_domain_sha256("
                        "'phase6-research-snapshot-binding-v1', payload - 'binding_sha256') "
                        "UNION ALL SELECT 'attempt', count(*) "
                        "FROM research_pipeline_attempts WHERE "
                        "attempt_sha256 IS DISTINCT FROM phase6_domain_sha256("
                        "'phase6-research-attempt-v1', payload - 'attempt_sha256') "
                        "UNION ALL SELECT 'feature_row', count(*) "
                        "FROM research_feature_rows WHERE "
                        "row_sha256 IS DISTINCT FROM phase6_domain_sha256("
                        "'phase6-research-feature-row-v1', "
                        "payload - ARRAY['row_id','row_sha256']) "
                        "OR row_id IS DISTINCT FROM phase6_uuid5("
                        "'5b7df50c-9da2-5f51-9b71-39187e491ce7'::uuid, row_sha256) "
                        "UNION ALL SELECT 'score', count(*) "
                        "FROM research_score_outputs WHERE "
                        "output_sha256 IS DISTINCT FROM phase6_domain_sha256("
                        "'phase6-research-score-output-v1', "
                        "payload - ARRAY['score_id','output_sha256']) "
                        "OR score_id IS DISTINCT FROM phase6_uuid5("
                        "'e52726b7-d313-57d4-85f9-49c96816cf4e'::uuid, output_sha256) "
                        "UNION ALL SELECT 'baseline', count(*) "
                        "FROM research_baseline_comparisons WHERE "
                        "comparison_sha256 IS DISTINCT FROM phase6_domain_sha256("
                        "'phase6-research-baseline-comparison-v1', "
                        "payload - ARRAY['comparison_id','comparison_sha256']) "
                        "OR comparison_id IS DISTINCT FROM phase6_uuid5("
                        "'4b2f565f-b0bc-53dd-9097-da44e2cf6d88'::uuid, "
                        "comparison_sha256) "
                        "UNION ALL SELECT 'text_extraction', count(*) "
                        "FROM research_text_extractions WHERE "
                        "extraction_sha256 IS DISTINCT FROM phase6_domain_sha256("
                        "'phase6-text-feature-extraction-v1', "
                        "payload - ARRAY['extraction_id','extraction_sha256']) "
                        "OR extraction_id IS DISTINCT FROM phase6_uuid5("
                        "'aa25921e-a1a6-59e2-ae53-424560158b4c'::uuid, "
                        "extraction_sha256) "
                        "UNION ALL SELECT 'text_corroboration', count(*) "
                        "FROM research_text_corroborations WHERE "
                        "corroboration_sha256 IS DISTINCT FROM phase6_domain_sha256("
                        "'phase6-social-official-corroboration-v1', "
                        "payload - ARRAY['corroboration_id','corroboration_sha256']) "
                        "OR corroboration_id IS DISTINCT FROM phase6_uuid5("
                        "'573eeb0a-15fe-531a-9e60-e9972c535ba0'::uuid, "
                        "corroboration_sha256)"
                    )
                ).mappings()
            }
            assert set(mismatches) == {
                "run",
                "snapshot_binding",
                "attempt",
                "feature_row",
                "score",
                "baseline",
                "text_extraction",
                "text_corroboration",
            }
            assert mismatches == dict.fromkeys(mismatches, 0)
    finally:
        engine.dispose()


def test_phase6_rejects_noncanonical_root_and_deferred_extra_child() -> None:
    assert DATABASE_URL is not None
    engine = create_engine(DATABASE_URL)
    try:
        with engine.connect() as connection:
            run_id = uuid4()
            fingerprint = uuid4().hex * 2
            artifact_sha256 = uuid4().hex * 2
            with pytest.raises(
                DBAPIError,
                match="Phase 6 research artifact canonical hash mismatch",
            ):
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
                        "to_jsonb(CAST(:fingerprint AS text)), false), "
                        "reason_codes, warnings, no_real_performance_claimed, "
                        "paper_approval_granted "
                        "FROM research_pipeline_runs ORDER BY id LIMIT 1"
                    ),
                    {
                        "run_id": run_id,
                        "fingerprint": fingerprint,
                        "artifact_sha256": artifact_sha256,
                    },
                )
            connection.rollback()

            ordinal = 999
            sample_id = f"phase6-completeness-probe-{uuid4()}"
            connection.execute(
                text(
                    "WITH source AS ("
                    "SELECT run_id, entity_id, decision_time_utc, "
                    "jsonb_set(jsonb_set(payload, '{ordinal}', "
                    "to_jsonb(CAST(:ordinal_json AS integer)), false), '{sample_id}', "
                    "to_jsonb(CAST(:sample_id_json AS text)), false) AS payload "
                    "FROM research_feature_rows ORDER BY run_id, ordinal LIMIT 1"
                    "), hashed AS ("
                    "SELECT *, phase6_domain_sha256("
                    "'phase6-research-feature-row-v1', "
                    "payload - ARRAY['row_id','row_sha256']) AS row_sha256 FROM source"
                    "), identified AS ("
                    "SELECT *, phase6_uuid5("
                    "'5b7df50c-9da2-5f51-9b71-39187e491ce7'::uuid, row_sha256"
                    ") AS row_id FROM hashed"
                    ") "
                    "INSERT INTO research_feature_rows ("
                    "run_id, ordinal, row_id, sample_id, entity_id, decision_time_utc, "
                    "row_sha256, payload) "
                    "SELECT run_id, :ordinal, row_id, :sample_id, entity_id, "
                    "decision_time_utc, row_sha256, "
                    "jsonb_set(jsonb_set(payload, '{row_id}', "
                    "to_jsonb(row_id::text), false), '{row_sha256}', "
                    "to_jsonb(row_sha256), false) FROM identified"
                ),
                {
                    "ordinal": ordinal,
                    "sample_id": sample_id,
                    "ordinal_json": ordinal,
                    "sample_id_json": sample_id,
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
            if item.configuration_id.value == "phase6-a-pass-v2"
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


def test_phase6_full_workflow_concurrent_first_write_is_idempotent() -> None:
    seed_repository = _repository()
    try:
        seed = next(
            seed_repository.get_run(item.run_id)
            for item in seed_repository.list_runs(limit=100)
            if item.configuration_id is ResearchConfigurationId.A_PASS
        )
    finally:
        seed_repository.dispose()

    request = ResearchRunCreateRequest(
        mapping_id=seed.mapping_id,
        snapshot_ids=tuple(sorted(item.snapshot_id for item in seed.snapshot_bindings)),
        research_configuration_id=ResearchConfigurationId.A_PASS,
    )
    # A fresh git identity forces a first write through the Phase 5 report and
    # Phase 6 run registries instead of retrying the acceptance artifact.
    code_version_git_sha = f"{uuid4().hex}{uuid4().hex[:8]}"
    barrier = Barrier(2)

    def create() -> tuple[str, str, str]:
        assert DATABASE_URL is not None
        research_repository = ResearchRepository(DATABASE_URL)
        evaluation_repository = EvaluationRepository(DATABASE_URL)
        snapshot_repository = SnapshotRepository(DATABASE_URL)
        workflow = ResearchWorkflow(
            repository=research_repository,
            evaluation_repository=evaluation_repository,
            snapshot_repository=snapshot_repository,
            code_version_git_sha=code_version_git_sha,
        )
        try:
            barrier.wait()
            stored = workflow.create_run(request)
            return str(stored.run_id), stored.artifact_sha256, stored.code_version_git_sha
        finally:
            snapshot_repository.dispose()
            evaluation_repository.dispose()
            research_repository.dispose()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = tuple(executor.map(lambda _: create(), range(2)))

    assert results[0] == results[1]
    assert results[0][2] == code_version_git_sha

    assert DATABASE_URL is not None
    engine = create_engine(DATABASE_URL)
    try:
        with engine.connect() as connection:
            assert (
                connection.execute(
                    text("SELECT count(*) FROM evaluation_reports WHERE git_sha = :git_sha"),
                    {"git_sha": code_version_git_sha},
                ).scalar_one()
                == 1
            )
            assert (
                connection.execute(
                    text(
                        "SELECT count(*) FROM research_pipeline_runs AS run "
                        "JOIN evaluation_reports AS report "
                        "ON report.report_id = run.evaluation_report_id "
                        "WHERE report.git_sha = :git_sha"
                    ),
                    {"git_sha": code_version_git_sha},
                ).scalar_one()
                == 1
            )
    finally:
        engine.dispose()


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
