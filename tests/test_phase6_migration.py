from __future__ import annotations

import ast
import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "services/api/migrations/versions/0006_phase6_research.py"
PRIOR_MIGRATIONS = {
    "0001_phase1_audit_spine.py": (
        "5cd27e1bde6b03720f54fe5e1260cf5f9085e16a4eebed957aeeba1a3a7d17f8"
    ),
    "0002_phase2_source_extraction.py": (
        "d45c1cb0ade079cfba7492c75c1aff13fc714aaae0a81637f21942c175c4e5c8"
    ),
    "0003_phase3_canon_mapping.py": (
        "6859c63723dc31d6ede4cdd5528a42640f16e3c6103567b5d900a46741edf07d"
    ),
    "0004_phase4_point_in_time_data.py": (
        "78c52c613358708940d88cbd47069bdde9bc857046bf646d7461bd13b57b3008"
    ),
    "0005_phase5_evaluation.py": (
        "b368edf97c35c5b7d7ac651073a02c204816b638855d3bcae4d7cabf265a1404"
    ),
}

PHASE6_TABLES = {
    "research_pipeline_runs",
    "research_pipeline_snapshot_bindings",
    "research_pipeline_attempts",
    "research_feature_rows",
    "research_score_outputs",
    "research_baseline_comparisons",
    "research_text_extractions",
    "research_text_corroborations",
}

TABLE_COLUMNS = {
    "research_pipeline_runs": {
        "id",
        "schema_version",
        "request_fingerprint_sha256",
        "artifact_sha256",
        "configuration_id",
        "configuration_sha256",
        "mapping_id",
        "canonical_family",
        "specification_sha256",
        "feature_lineage_sha256",
        "snapshot_bundle_sha256",
        "phase5_policy_id",
        "phase5_policy_version",
        "phase5_policy_sha256",
        "phase5_fixture_id",
        "phase5_fixture_sha256",
        "evaluation_report_id",
        "evaluation_outcome_id",
        "promotion_state",
        "status",
        "artifact_payload",
        "reason_codes",
        "warnings",
        "no_real_performance_claimed",
        "paper_approval_granted",
        "created_at_utc",
    },
    "research_pipeline_snapshot_bindings": {
        "run_id",
        "ordinal",
        "snapshot_id",
        "snapshot_sha256",
        "capability",
        "binding_sha256",
        "payload",
        "created_at_utc",
    },
    "research_pipeline_attempts": {
        "run_id",
        "ordinal",
        "phase5_report_id",
        "phase5_trial_id",
        "phase5_trial_key",
        "status",
        "config_sha256",
        "failure_reason",
        "payload",
        "attempt_sha256",
        "created_at_utc",
    },
    "research_feature_rows": {
        "run_id",
        "ordinal",
        "row_id",
        "sample_id",
        "entity_id",
        "decision_time_utc",
        "row_sha256",
        "payload",
        "created_at_utc",
    },
    "research_score_outputs": {
        "run_id",
        "ordinal",
        "score_id",
        "sample_id",
        "model_id",
        "research_score",
        "explanation_sha256",
        "output_sha256",
        "payload",
        "created_at_utc",
    },
    "research_baseline_comparisons": {
        "run_id",
        "ordinal",
        "comparison_id",
        "candidate_model_id",
        "baseline_model_id",
        "outcome",
        "comparison_sha256",
        "payload",
        "created_at_utc",
    },
    "research_text_extractions": {
        "run_id",
        "ordinal",
        "extraction_id",
        "source_version_id",
        "document_sha256",
        "extractor_id",
        "extractor_version",
        "model_id",
        "prompt_version",
        "schema_version",
        "extraction_sha256",
        "payload",
        "created_at_utc",
    },
    "research_text_corroborations": {
        "run_id",
        "ordinal",
        "corroboration_id",
        "social_record_id",
        "official_source_version_id",
        "official_document_sha256",
        "corroboration_sha256",
        "payload",
        "created_at_utc",
    },
}

EXPECTED_FOREIGN_KEYS = {
    (("mapping_id",), ("research_mapping_versions.id",)),
    (
        ("phase5_policy_id", "phase5_policy_version", "phase5_policy_sha256"),
        (
            "evaluation_policies.policy_id",
            "evaluation_policies.policy_version",
            "evaluation_policies.policy_sha256",
        ),
    ),
    (("evaluation_report_id",), ("evaluation_reports.report_id",)),
    (("evaluation_outcome_id",), ("evaluation_blocked_outcomes.outcome_id",)),
    (("run_id",), ("research_pipeline_runs.id",)),
    (("snapshot_id",), ("data_snapshots.snapshot_id",)),
    (("snapshot_sha256",), ("data_snapshots.snapshot_sha256",)),
    (
        ("phase5_report_id", "phase5_trial_id"),
        ("evaluation_trials.report_id", "evaluation_trials.trial_id"),
    ),
    (("source_version_id",), ("research_source_versions.id",)),
    (("official_source_version_id",), ("research_source_versions.id",)),
}


def migration_source() -> str:
    return MIGRATION.read_text(encoding="utf-8")


def migration_tree() -> ast.Module:
    return ast.parse(migration_source())


def function_node(name: str) -> ast.FunctionDef:
    for node in migration_tree().body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"missing migration function {name}")


def function_source(name: str) -> str:
    rendered = ast.get_source_segment(migration_source(), function_node(name))
    assert rendered is not None
    return rendered


def literal_table_calls(function_name: str, operation: str) -> set[str]:
    result: set[str] = set()
    for call in ast.walk(function_node(function_name)):
        if (
            isinstance(call, ast.Call)
            and isinstance(call.func, ast.Attribute)
            and call.func.attr == operation
            and call.args
            and isinstance(call.args[0], ast.Constant)
            and isinstance(call.args[0].value, str)
        ):
            result.add(call.args[0].value)
    return result


def create_table_calls() -> dict[str, ast.Call]:
    result: dict[str, ast.Call] = {}
    for call in ast.walk(function_node("upgrade")):
        if (
            isinstance(call, ast.Call)
            and isinstance(call.func, ast.Attribute)
            and call.func.attr == "create_table"
            and call.args
            and isinstance(call.args[0], ast.Constant)
        ):
            result[call.args[0].value] = call
    return result


def created_table_columns() -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for table, call in create_table_calls().items():
        columns: set[str] = set()
        for argument in call.args[1:]:
            if (
                isinstance(argument, ast.Call)
                and isinstance(argument.func, ast.Attribute)
                and argument.func.attr == "Column"
                and argument.args
                and isinstance(argument.args[0], ast.Constant)
            ):
                columns.add(argument.args[0].value)
            elif (
                isinstance(argument, ast.Call)
                and isinstance(argument.func, ast.Name)
                and argument.func.id == "_created_at"
            ):
                columns.add("created_at_utc")
            elif (
                isinstance(argument, ast.Call)
                and isinstance(argument.func, ast.Name)
                and argument.func.id == "_payload"
            ):
                if argument.args:
                    assert isinstance(argument.args[0], ast.Constant)
                    columns.add(argument.args[0].value)
                else:
                    columns.add("payload")
        result[table] = columns
    return result


def check_constraint_expression(constraint_name: str) -> str:
    for call in ast.walk(function_node("upgrade")):
        if not (
            isinstance(call, ast.Call)
            and isinstance(call.func, ast.Attribute)
            and call.func.attr == "CheckConstraint"
            and call.args
            and isinstance(call.args[0], ast.Constant)
            and isinstance(call.args[0].value, str)
        ):
            continue
        if any(
            keyword.arg == "name"
            and isinstance(keyword.value, ast.Constant)
            and keyword.value.value == constraint_name
            for keyword in call.keywords
        ):
            return call.args[0].value
    raise AssertionError(f"missing check constraint {constraint_name}")


def in_vocabulary(constraint_name: str, column_name: str) -> set[str]:
    expression = check_constraint_expression(constraint_name)
    match = re.search(rf"\b{column_name} IN \(([^)]*)\)", expression)
    assert match is not None, expression
    return set(re.findall(r"'([^']+)'", match.group(1)))


def sequence_values(node: ast.expr) -> tuple[str, ...]:
    assert isinstance(node, (ast.List, ast.Tuple))
    values: list[str] = []
    for element in node.elts:
        assert isinstance(element, ast.Constant)
        assert isinstance(element.value, str)
        values.append(element.value)
    return tuple(values)


def foreign_key_identities() -> tuple[set[tuple[tuple[str, ...], tuple[str, ...]]], int]:
    result: set[tuple[tuple[str, ...], tuple[str, ...]]] = set()
    count = 0
    for call in ast.walk(function_node("upgrade")):
        if not (
            isinstance(call, ast.Call)
            and isinstance(call.func, ast.Attribute)
            and call.func.attr == "ForeignKeyConstraint"
        ):
            continue
        count += 1
        result.add((sequence_values(call.args[0]), sequence_values(call.args[1])))
        ondelete = next(
            (keyword.value for keyword in call.keywords if keyword.arg == "ondelete"),
            None,
        )
        assert isinstance(ondelete, ast.Constant)
        assert ondelete.value == "RESTRICT"
    return result, count


def named_constraint_columns(kind: str, name: str) -> tuple[str, ...]:
    for call in ast.walk(function_node("upgrade")):
        if not (
            isinstance(call, ast.Call)
            and isinstance(call.func, ast.Attribute)
            and call.func.attr == kind
        ):
            continue
        constraint_name = next(
            (
                keyword.value.value
                for keyword in call.keywords
                if keyword.arg == "name" and isinstance(keyword.value, ast.Constant)
            ),
            None,
        )
        if constraint_name == name:
            return tuple(
                argument.value
                for argument in call.args
                if isinstance(argument, ast.Constant) and isinstance(argument.value, str)
            )
    raise AssertionError(f"missing {kind} {name}")


def test_phase6_revision_chain_and_prior_migration_bytes_are_exact() -> None:
    source = migration_source()
    assignments = {
        node.target.id: node.value.value
        for node in migration_tree().body
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and isinstance(node.value, ast.Constant)
    }
    assert assignments["revision"] == "0006_phase6"
    assert assignments["down_revision"] == "0005_phase5"
    assert "create_all" not in source

    versions = ROOT / "services/api/migrations/versions"
    for filename, expected_hash in PRIOR_MIGRATIONS.items():
        assert hashlib.sha256((versions / filename).read_bytes()).hexdigest() == expected_hash


def test_phase6_owns_exactly_eight_tables_with_exact_columns() -> None:
    assert literal_table_calls("upgrade", "create_table") == PHASE6_TABLES
    assert literal_table_calls("downgrade", "drop_table") == PHASE6_TABLES
    assert created_table_columns() == TABLE_COLUMNS


def test_phase6_foreign_keys_are_restrictive_and_cover_prior_phase_authorities() -> None:
    identities, count = foreign_key_identities()
    assert count == 16
    assert identities == EXPECTED_FOREIGN_KEYS
    source = migration_source()
    assert "uq_phase6_evaluation_trials_trial_id" not in source
    assert '["phase5_report_id", "phase5_trial_id"]' in source
    assert '["evaluation_trials.report_id", "evaluation_trials.trial_id"]' in source


def test_phase6_uses_database_owned_utc_and_strict_json_hash_identities() -> None:
    source = migration_source()
    created_at = function_source("_created_at")
    assert "sa.DateTime(timezone=True)" in created_at
    assert 'server_default=sa.text("CURRENT_TIMESTAMP")' in created_at
    assert source.count("_created_at(),") == len(PHASE6_TABLES)
    assert "CREATE FUNCTION own_phase6_created_at_utc()" in source
    assert "NEW.created_at_utc := CURRENT_TIMESTAMP" in source
    assert "CREATE TRIGGER {table}_00_created_at_utc" in source
    assert "DROP TRIGGER IF EXISTS {table}_00_created_at_utc ON {table}" in source
    assert "DROP FUNCTION IF EXISTS own_phase6_created_at_utc()" in source
    assert source.count("jsonb_typeof(payload) = 'object'") == len(PHASE6_TABLES) - 1
    assert "jsonb_typeof(artifact_payload) = 'object'" in source
    assert "^[0-9a-f]{{64}}$" in source

    for identity in (
        "uq_research_pipeline_run_request_fingerprint",
        "uq_research_pipeline_snapshot_binding_capability",
        "uq_research_pipeline_attempt_trial",
        "uq_research_pipeline_attempt_trial_key",
        "uq_research_feature_row_semantic_identity",
        "uq_research_score_output_semantic_identity",
        "uq_research_baseline_comparison_semantic_identity",
        "uq_research_text_extraction_semantic_identity",
        "uq_research_text_corroboration_semantic_identity",
    ):
        assert identity in source

    assert "CREATE FUNCTION validate_phase6_payload_columns()" in source
    assert "CREATE TRIGGER {table}_05_payload_columns" in source
    assert "FOR EACH ROW EXECUTE FUNCTION validate_phase6_payload_columns()" in source
    assert "DROP TRIGGER IF EXISTS {table}_05_payload_columns ON {table}" in source
    assert "DROP FUNCTION IF EXISTS validate_phase6_payload_columns()" in source
    for mismatch in (
        "run payload differs from bound columns",
        "snapshot-binding payload mismatch",
        "attempt payload mismatch",
        "feature-row payload mismatch",
        "score-output payload mismatch",
        "baseline-comparison payload mismatch",
        "text-extraction payload mismatch",
        "text-corroboration payload mismatch",
    ):
        assert mismatch in source


def test_phase6_defers_exact_run_child_completeness_until_commit() -> None:
    source = migration_source()
    upgrade = function_source("upgrade")
    downgrade = function_source("downgrade")
    assert "CREATE FUNCTION phase6_registry_matches_artifact(" in source
    assert "jsonb_typeof(expected_payloads) IS DISTINCT FROM 'array'" in source
    assert "actual_count = expected_count" in source
    assert "minimum_ordinal = 1" in source
    assert "maximum_ordinal = expected_count" in source
    assert "actual_payloads IS NOT DISTINCT FROM expected_payloads" in source
    assert "actual_attempt_count" in source
    assert "SELECT trial_id, trial_key, status, config_sha256" in source
    assert "SELECT phase5_trial_id, phase5_trial_key, status, config_sha256" in source
    assert source.count("EXCEPT") >= 2
    assert "Phase 6 attempt registry does not exactly match Phase 5 trials" in source
    assert "CREATE FUNCTION validate_phase6_run_completeness()" in source
    for expected_registry in (
        "run_row.artifact_payload->'snapshot_bindings'",
        "run_row.artifact_payload->'attempts'",
        "run_row.artifact_payload->'feature_rows'",
        "run_row.artifact_payload->'scores'",
        "run_row.artifact_payload->'baseline_comparisons'",
        "run_row.artifact_payload#>'{family_evidence,extractions}'",
        "run_row.artifact_payload#>'{family_evidence,corroborations}'",
    ):
        assert expected_registry in source
    assert "Phase 6 research run has incomplete child registries" in source
    assert "CREATE CONSTRAINT TRIGGER research_pipeline_runs_complete" in upgrade
    assert "for table in PHASE6_CHILD_TABLES:" in upgrade
    assert "CREATE CONSTRAINT TRIGGER {table}_run_complete" in upgrade
    assert upgrade.count("DEFERRABLE INITIALLY DEFERRED") == 2
    assert "AFTER INSERT ON research_pipeline_runs" in upgrade
    assert "AFTER INSERT ON {table}" in upgrade
    assert "FOR EACH ROW EXECUTE FUNCTION validate_phase6_run_completeness()" in upgrade
    assert "DROP TRIGGER IF EXISTS {table}_run_complete ON {table}" in downgrade
    assert "DROP TRIGGER IF EXISTS research_pipeline_runs_complete" in downgrade
    assert "DROP FUNCTION IF EXISTS validate_phase6_run_completeness()" in downgrade
    assert (
        "DROP FUNCTION IF EXISTS phase6_registry_matches_artifact(regclass, uuid, jsonb)"
        in downgrade
    )


def test_phase6_child_identities_are_run_scoped_for_valid_cross_run_reuse() -> None:
    for name in (
        "uq_research_pipeline_snapshot_binding_sha256",
        "uq_research_pipeline_attempt_sha256",
        "uq_research_feature_row_sha256",
        "uq_research_score_output_sha256",
        "uq_research_baseline_comparison_sha256",
        "uq_research_text_extraction_sha256",
        "uq_research_text_corroboration_sha256",
    ):
        assert named_constraint_columns("UniqueConstraint", name)[0] == "run_id"
    for name in (
        "pk_research_feature_rows",
        "pk_research_score_outputs",
        "pk_research_baseline_comparisons",
        "pk_research_text_extractions",
        "pk_research_text_corroborations",
    ):
        assert named_constraint_columns("PrimaryKeyConstraint", name)[0] == "run_id"


def test_phase6_closed_vocabularies_are_exact() -> None:
    assert in_vocabulary("ck_research_pipeline_run_identity", "configuration_id") == {
        "phase6-a-pass-v1",
        "phase6-a-fail-cost-v1",
        "phase6-b-pass-v1",
        "phase6-b-fail-crash-v1",
        "phase6-c-pass-v1",
        "phase6-c-fail-corroboration-v1",
    }
    assert in_vocabulary("ck_research_pipeline_run_family", "canonical_family") == {
        "A_CROSS_SECTIONAL_EQUITY_RANKING",
        "B_TIME_SERIES_MOMENTUM_REGIME",
        "C_OFFICIAL_EVENT_TEXT_OVERLAY",
    }
    assert in_vocabulary("ck_research_pipeline_run_promotion_state", "promotion_state") == {
        "PASS_RESEARCH",
        "FAIL_REJECT",
        "BLOCKED_MISSING_POLICY",
        "BLOCKED_UNCOMPUTABLE",
        "RESEARCH_ONLY_REGIME_DEPENDENT",
    }
    assert in_vocabulary("ck_research_pipeline_attempt_status", "status") == {
        "completed",
        "failed",
        "abandoned",
        "no_return",
        "blocked",
    }
    assert in_vocabulary("ck_research_baseline_comparison_identity", "outcome") == {
        "survives",
        "rejected",
    }
    assert in_vocabulary("ck_research_pipeline_snapshot_binding_identity", "capability") == {
        "security_master",
        "universe_membership",
        "ohlcv",
        "corporate_actions",
        "delistings",
        "as_reported_fundamentals",
        "trading_calendar",
        "volatility_return_inputs",
        "official_document_event_metadata",
    }


def test_phase6_run_is_exactly_bound_to_phase5_and_is_never_paper_approved() -> None:
    source = migration_source()
    run_columns = TABLE_COLUMNS["research_pipeline_runs"]
    assert {
        "configuration_sha256",
        "specification_sha256",
        "feature_lineage_sha256",
        "snapshot_bundle_sha256",
        "phase5_policy_id",
        "phase5_policy_version",
        "phase5_policy_sha256",
        "phase5_fixture_id",
        "phase5_fixture_sha256",
        "evaluation_report_id",
        "evaluation_outcome_id",
    } <= run_columns
    terminal = check_constraint_expression("ck_research_pipeline_run_terminal_binding")
    assert "(evaluation_report_id IS NOT NULL) <> (evaluation_outcome_id IS NOT NULL)" in terminal
    assert "CREATE FUNCTION validate_phase6_research_pipeline_run()" in source
    for prior_field in (
        "mapping_id",
        "policy_id",
        "policy_version",
        "policy_sha256",
        "configuration_sha256",
        "fixture_id",
        "fixture_sha256",
        "snapshot_bundle_sha256",
        "state",
    ):
        assert f"report_row.{prior_field}" in source
    assert "no_real_performance_claimed" in source
    assert "AND NOT paper_approval_granted" in source
    assert "artifact_payload->>'code_version_git_sha' ~ '^[0-9a-f]{40}$'" in source
    assert "artifact_payload->>'random_seed'" in source
    assert "{phase5_evaluation,raw_trial_count}" in source
    assert "{phase5_evaluation,effective_trial_count}" in source
    assert "report_row.report_sha256" in source


def test_phase6_snapshot_trial_and_text_lineage_fail_closed() -> None:
    source = migration_source()
    assert "Phase 6 snapshot is absent from the Phase 5 report" in source
    assert "Phase 6 attempt requires its Phase 5 trial" in source
    assert "NEW.phase5_report_id IS DISTINCT FROM run_row.evaluation_report_id" in source
    assert "WHERE report_id = NEW.phase5_report_id" in source
    assert "trial_row.trial_key IS DISTINCT FROM NEW.phase5_trial_key" in source
    assert "trial_row.status IS DISTINCT FROM NEW.status" in source
    assert "official_document_content" in source
    assert "document_content_sha256" in source
    assert "Phase 6 text extraction lacks exact immutable document lineage" in source
    assert "btrim(social_record_id) <> ''" in source
    assert "official_authority IS DISTINCT FROM 'official'" in source
    assert "mapping_official_corroborations" in source
    assert "Phase 6 social attention requires exact official corroboration" in source
    assert "social.payload->>'social_attention_record_id' = NEW.social_record_id" in source
    assert "social.source_record_id = NEW.social_record_id" not in source
    assert (
        "social.source_record_id\n"
        "                            = NEW.payload#>>'{social_source_reference,source_record_id}'"
        in source
    )
    assert "'label','signal','model_decision','trade_instruction','position_size'" in source


def test_phase6_additive_phase4_support_is_scoped_and_exactly_reversible() -> None:
    source = migration_source()
    upgrade = function_source("upgrade")
    downgrade = function_source("downgrade")
    snapshot_versions = function_source("_phase4_snapshot_frozen_versions_constraint")
    quality_identities = function_source("_phase4_quality_finding_identity_constraint")
    quality_codes = function_source("_phase4_quality_finding_code_constraint")
    assert "sector_classification" in source
    assert "official_document_content" in source
    assert "sector_history" not in source
    assert "CREATE OR REPLACE FUNCTION phase4_record_type_matches_capability" in source
    assert "CREATE OR REPLACE FUNCTION validate_phase4_snapshot_request" in source
    record_type_function = function_source("_phase4_record_type_function")
    snapshot_request_function = function_source("_phase4_snapshot_request_function")
    assert "else \"checked_record_type = 'official_document_event'\"" in record_type_function
    assert "{family_b_extra}'ohlcv'," in snapshot_request_function
    assert "extended=True" in upgrade
    assert "extended=True" in upgrade
    assert "extended=False" in downgrade
    assert "extended=False" in downgrade
    assert upgrade.count('"ck_data_snapshot_constituent_record_type"') == 2
    assert downgrade.count('"ck_data_snapshot_constituent_record_type"') == 2
    assert upgrade.count('"ck_data_quality_finding_record_type"') == 2
    assert downgrade.count('"ck_data_quality_finding_record_type"') == 2
    assert upgrade.count('"ck_data_snapshot_frozen_versions"') == 2
    assert downgrade.count('"ck_data_snapshot_frozen_versions"') == 2
    assert upgrade.count('"ck_data_quality_finding_identities"') == 2
    assert downgrade.count('"ck_data_quality_finding_identities"') == 2
    assert upgrade.count('"ck_data_quality_finding_code"') == 2
    assert downgrade.count('"ck_data_quality_finding_code"') == 2
    assert "'phase4-synthetic-pit-fixtures-v1'" in snapshot_versions
    assert "'phase6-synthetic-pit-fixtures-v1'" in snapshot_versions
    assert "'phase4-data-quality-v1'" in quality_identities
    assert "'phase6-data-contract-quality-v1'" in quality_identities
    for phase6_code in (
        "pit_classification_invalid",
        "document_content_hash_mismatch",
        "document_correction_timing_invalid",
        "official_corroboration_mismatch",
    ):
        assert phase6_code in quality_codes
    assert "fixture_set_version = 'phase6-synthetic-pit-fixtures-v1'" in downgrade
    assert "rule_set_version = 'phase6-data-contract-quality-v1'" in downgrade
    assert "Phase 6 downgrade blocked by additive Phase 4 record types" in downgrade


def test_phase6_phase5_lineage_bridge_is_additive_and_restores_exact_base() -> None:
    source = migration_source()
    upgrade = function_source("upgrade")
    downgrade = function_source("downgrade")
    for literal in (
        "phase5-source-feature-derivation-v2",
        "source-sha256-prefix64-times-frozen-multiplier-v1",
        "phase6-source-feature-derivation-v1",
        "source-decimal-times-frozen-multiplier-quantized-1e-12-v1",
        "document_content_sha256",
        "official_document_event_metadata",
        "phase4-universe_membership.%",
    ):
        assert literal in source
    assert "18446744073709551616 (2^64)" in source
    assert "0.0000000000000000000542101086242752217003726400434970855712890625" in source
    assert "pg_get_functiondef" in source
    assert "validate_phase5_report_source_lineage_phase5_base" in source
    assert "_phase5_source_lineage_bridge_sql()" in upgrade
    assert "DROP FUNCTION validate_phase5_report_source_lineage(uuid)" in downgrade
    assert "ALTER FUNCTION validate_phase5_report_source_lineage_phase5_base(uuid) " in downgrade
    assert "RENAME TO validate_phase5_report_source_lineage" in downgrade
    assert "DROP FUNCTION phase6_sha256_prefix64_fraction(text)" in downgrade
    assert "NOT IN ('object','null')" in source
    assert "IS DISTINCT FROM 'null'" in source
    assert "Phase 6 could not generalize sample-scoped capability lineage" in source
    assert "Phase 6 could not permit report-wide capability witnesses" in source
    assert "SELECT DISTINCT source_item#>>'{key,capability}' AS capability" in source


def test_phase6_all_tables_reject_update_delete_and_truncate() -> None:
    source = migration_source()
    downgrade = function_source("downgrade")
    assert "Phase 6 research artifacts are append-only" in source
    assert "for table in PHASE6_TABLES:" in source
    assert "CREATE TRIGGER {table}_immutable" in source
    assert "BEFORE UPDATE OR DELETE ON {table}" in source
    assert "CREATE TRIGGER {table}_no_truncate" in source
    assert "BEFORE TRUNCATE ON {table}" in source
    assert "for table in reversed(PHASE6_TABLES):" in downgrade
    first_table_drop = min(downgrade.index(f'op.drop_table("{table}")') for table in PHASE6_TABLES)
    assert downgrade.rindex("DROP TRIGGER IF EXISTS") < first_table_drop
    assert downgrade.rindex("DROP FUNCTION IF EXISTS") < first_table_drop


def test_phase6_downgrade_preserves_prior_tables_and_removes_only_its_artifacts() -> None:
    downgrade = function_source("downgrade")
    for protected_prefix in (
        "evaluation_",
        "data_",
        "research_mapping_versions",
        "research_source_versions",
        "trading_idea_cards",
        "audit_events",
    ):
        assert f'op.drop_table("{protected_prefix}' not in downgrade
    assert "uq_phase6_evaluation_trials_trial_id" not in downgrade
    assert "ck_data_snapshot_constituent_record_type" in downgrade
    assert "ck_data_quality_finding_record_type" in downgrade


def test_phase6_migration_contains_no_phase7_execution_or_claim_capability() -> None:
    source = migration_source()
    lowered = source.lower()
    for forbidden in (
        "approved_paper",
        "broker",
        "pre_order",
        "live_endpoint",
        "live_order",
        "paper_execution",
        "personalized_investment_advice",
        'position_size", sa.',
        'allocation", sa.',
        'order_id", sa.',
    ):
        assert forbidden not in lowered
    performance_lines = [line for line in lowered.splitlines() if "performance" in line]
    assert performance_lines
    assert all("no_real_performance_claim" in line for line in performance_lines)
    assert "and not paper_approval_granted" in lowered
