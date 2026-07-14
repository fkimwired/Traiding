from __future__ import annotations

import ast
import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "services/api/migrations/versions/0005_phase5_evaluation.py"
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
}

PHASE5_TABLES = {
    "evaluation_policies",
    "evaluation_feature_specs",
    "evaluation_label_specs",
    "evaluation_blocked_outcomes",
    "evaluation_reports",
    "evaluation_report_snapshots",
    "evaluation_trials",
    "evaluation_folds",
    "evaluation_preprocessing_fits",
    "evaluation_oos_ledger",
    "evaluation_cost_ledger",
    "evaluation_gate_results",
}

ARTIFACT_COLUMNS = {"canonical_json", "payload", "created_at_utc"}
TABLE_COLUMNS = {
    "evaluation_policies": {
        "policy_id",
        "policy_version",
        "schema_version",
        "policy_sha256",
        "strategy_family",
        "selection_scope",
        "approved_by",
        "synthetic_fixture_policy",
        "signal_specification",
        "forecast_horizon",
        "required_snapshot_capabilities",
        "label_interval_rule",
        "transaction_cost_model",
        "slippage_model",
        "walk_forward_geometry",
        "risk_limits",
        "selection_policy",
        "sample_adequacy_policy",
        "missing_return_policy",
        "no_trade_return_policy",
        "regime_policy",
        "reproducibility_policy",
        "cost_stress_multiplier",
        "expected_feature_spec_count",
        "expected_label_spec_count",
        "feature_spec_hashes",
        "label_spec_hashes",
    }
    | ARTIFACT_COLUMNS,
    "evaluation_feature_specs": {
        "feature_spec_id",
        "feature_spec_sha256",
        "policy_id",
        "policy_version",
        "policy_sha256",
        "ordinal",
        "feature_name",
        "feature_schema_version",
        "information_interval",
        "required_capabilities",
    }
    | ARTIFACT_COLUMNS,
    "evaluation_label_specs": {
        "label_spec_id",
        "label_spec_sha256",
        "policy_id",
        "policy_version",
        "policy_sha256",
        "ordinal",
        "label_name",
        "label_schema_version",
        "information_interval",
        "forecast_horizon",
    }
    | ARTIFACT_COLUMNS,
    "evaluation_blocked_outcomes": {
        "outcome_id",
        "outcome_sha256",
        "idempotency_sha256",
        "idempotency_canonical_json",
        "idempotency_payload",
        "schema_version",
        "submission_sha256",
        "submission_canonical_json",
        "submission_payload",
        "policy_id",
        "policy_version",
        "mapping_id",
        "snapshot_ids",
        "fixture_id",
        "resolved_policy_sha256",
        "resolved_fixture_sha256",
        "resolved_fixture_random_seed",
        "resolved_raw_trial_count",
        "resolved_snapshots",
        "git_sha",
        "failure_stage",
        "state",
        "reason_codes",
        "synthetic",
        "no_real_performance_claim",
    }
    | ARTIFACT_COLUMNS,
    "evaluation_reports": {
        "report_id",
        "report_sha256",
        "report_schema_version",
        "run_fingerprint_sha256",
        "run_fingerprint_canonical_json",
        "run_fingerprint_payload",
        "policy_id",
        "policy_version",
        "policy_sha256",
        "mapping_id",
        "mapping_version",
        "mapping_input_sha256",
        "configuration_sha256",
        "fixture_id",
        "fixture_sha256",
        "snapshot_bundle_sha256",
        "snapshot_bundle_canonical_json",
        "sample_lineage_sha256",
        "sample_lineage_canonical_json",
        "source_observations",
        "sample_lineage",
        "git_sha",
        "random_seed",
        "decision_time_utc",
        "raw_trial_count",
        "effective_trial_count",
        "effective_trial_count_method",
        "synthetic",
        "no_real_performance_claim",
        "state",
        "expected_snapshot_count",
        "expected_source_observation_count",
        "expected_sample_lineage_count",
        "expected_trial_count",
        "expected_fold_count",
        "expected_preprocessing_fit_count",
        "expected_oos_ledger_count",
        "expected_cost_ledger_count",
        "expected_gate_result_count",
    }
    | ARTIFACT_COLUMNS,
    "evaluation_report_snapshots": {
        "report_snapshot_id",
        "report_snapshot_sha256",
        "report_id",
        "report_sha256",
        "ordinal",
        "snapshot_id",
        "snapshot_sha256",
        "capability",
        "as_of_utc",
        "provider_id",
        "adapter_id",
        "adapter_version",
        "dataset_id",
        "product_id",
        "dataset_schema_id",
        "dataset_schema_version",
        "dataset_schema_versions",
        "quality_status",
        "fixture_set_version",
    }
    | ARTIFACT_COLUMNS,
    "evaluation_trials": {
        "trial_id",
        "trial_sha256",
        "report_id",
        "report_sha256",
        "ordinal",
        "trial_key",
        "status",
        "strategy_family",
        "selection_scope",
        "initiated_by",
        "initiated_at_utc",
        "oos_return_state",
        "net_returns",
        "return_statuses",
        "return_timestamps_utc",
        "return_observation_count",
        "missing_return_count",
        "no_trade_count",
        "config_sha256",
        "config_canonical_json",
        "config_preimage",
        "configuration",
        "failure_reason",
    }
    | ARTIFACT_COLUMNS,
    "evaluation_folds": {
        "fold_id",
        "fold_sha256",
        "report_id",
        "report_sha256",
        "ordinal",
        "fold_kind",
        "parent_fold_id",
        "train_start_utc",
        "train_end_utc",
        "test_start_utc",
        "test_end_utc",
        "training_row_count",
        "test_row_count",
        "purged_row_count",
        "embargoed_row_count",
        "embargo_duration_seconds",
        "embargo_applied",
    }
    | ARTIFACT_COLUMNS,
    "evaluation_preprocessing_fits": {
        "fit_id",
        "fit_sha256",
        "statistics_sha256",
        "report_id",
        "report_sha256",
        "fold_id",
        "ordinal",
        "transformer_id",
        "transformer_version",
        "training_row_count",
        "train_sample_ids",
        "train_sample_ids_sha256",
        "mean",
        "standard_deviation",
        "ddof",
        "record_payload",
    }
    | ARTIFACT_COLUMNS,
    "evaluation_oos_ledger": {
        "oos_entry_id",
        "oos_entry_sha256",
        "report_id",
        "report_sha256",
        "trial_id",
        "fold_id",
        "ordinal",
        "sample_id",
        "sample_sha256",
        "source_observation_refs",
        "information_start_utc",
        "information_end_utc",
        "decision_time_utc",
        "label_t0_utc",
        "label_t1_utc",
        "prediction_value",
        "gross_return",
        "baseline_net_return",
        "return_status",
        "delisting_return_handled",
    }
    | ARTIFACT_COLUMNS,
    "evaluation_cost_ledger": {
        "cost_entry_id",
        "cost_entry_sha256",
        "report_id",
        "report_sha256",
        "ordinal",
        "sample_id",
        "scenario",
        "allocation_input_sha256",
        "return_status",
        "stress_multiplier",
        "requested_quantity",
        "filled_quantity",
        "rejected_quantity",
        "unfilled_quantity",
        "fill_status",
        "hard_to_borrow_available",
        "gross_return",
        "fee_cost",
        "spread_cost",
        "impact_cost",
        "latency_cost",
        "borrow_cost",
        "capacity_cost",
        "total_cost",
        "net_return",
        "participation_rate",
        "capacity_breached",
    }
    | ARTIFACT_COLUMNS,
    "evaluation_gate_results": {
        "gate_result_id",
        "gate_result_sha256",
        "report_id",
        "report_sha256",
        "ordinal",
        "config_hash",
        "gate_code",
        "outcome",
        "computable",
        "passed",
        "blocking",
        "reason_codes",
        "metric_value",
        "threshold_value",
    }
    | ARTIFACT_COLUMNS,
}

PROMOTION_STATES = {
    "PASS_RESEARCH",
    "FAIL_REJECT",
    "BLOCKED_MISSING_POLICY",
    "BLOCKED_UNCOMPUTABLE",
    "RESEARCH_ONLY_REGIME_DEPENDENT",
}
TRIAL_STATUSES = {"completed", "failed", "abandoned", "no_return"}
COST_SCENARIOS = {"baseline", "all_cost_stress", "liquidity_stress"}
GATE_CODES = {
    "DATA_PIT",
    "CV_CHRONOLOGY",
    "PREPROCESSING",
    "TRIAL_REGISTRY",
    "DSR",
    "PBO",
    "COST_STRESS",
    "LEAKAGE",
    "SAMPLE_ADEQUACY",
    "REGIME",
    "RISK_LIMITS",
    "REPRODUCIBILITY",
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


def created_table_columns() -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for call in ast.walk(function_node("upgrade")):
        if not (
            isinstance(call, ast.Call)
            and isinstance(call.func, ast.Attribute)
            and call.func.attr == "create_table"
            and call.args
            and isinstance(call.args[0], ast.Constant)
        ):
            continue
        table = call.args[0].value
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
                isinstance(argument, ast.Starred)
                and isinstance(argument.value, ast.Call)
                and isinstance(argument.value.func, ast.Name)
                and argument.value.func.id == "_artifact_payload_columns"
            ):
                columns.update(ARTIFACT_COLUMNS)
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
        for keyword in call.keywords:
            if (
                keyword.arg == "name"
                and isinstance(keyword.value, ast.Constant)
                and keyword.value.value == constraint_name
            ):
                return call.args[0].value
    raise AssertionError(f"missing check constraint {constraint_name}")


def in_vocabulary(constraint_name: str, column_name: str) -> set[str]:
    expression = check_constraint_expression(constraint_name)
    match = re.search(rf"\b{column_name} IN \(([^)]*)\)", expression)
    assert match is not None, expression
    return set(re.findall(r"'([^']+)'", match.group(1)))


def test_phase5_revision_chain_and_all_prior_migration_bytes_are_exact() -> None:
    source = migration_source()
    assignments = {
        node.target.id: node.value.value
        for node in migration_tree().body
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and isinstance(node.value, ast.Constant)
    }
    assert assignments["revision"] == "0005_phase5"
    assert assignments["down_revision"] == "0004_phase4"
    assert "create_all" not in source

    versions = ROOT / "services/api/migrations/versions"
    for filename, expected_hash in PRIOR_MIGRATIONS.items():
        assert hashlib.sha256((versions / filename).read_bytes()).hexdigest() == expected_hash


def test_phase5_owns_exactly_twelve_tables_with_exact_columns() -> None:
    assert literal_table_calls("upgrade", "create_table") == PHASE5_TABLES
    assert literal_table_calls("downgrade", "drop_table") == PHASE5_TABLES
    assert created_table_columns() == TABLE_COLUMNS


def test_phase5_uses_only_restrictive_foreign_keys_and_server_utc_timestamps() -> None:
    source = migration_source()
    foreign_keys = [
        call
        for call in ast.walk(function_node("upgrade"))
        if isinstance(call, ast.Call)
        and isinstance(call.func, ast.Attribute)
        and call.func.attr == "ForeignKeyConstraint"
    ]
    assert len(foreign_keys) == 17
    for foreign_key in foreign_keys:
        ondelete = next(
            (keyword.value for keyword in foreign_key.keywords if keyword.arg == "ondelete"),
            None,
        )
        assert isinstance(ondelete, ast.Constant)
        assert ondelete.value == "RESTRICT"

    assert source.count("*_artifact_payload_columns()") == len(PHASE5_TABLES)
    created_at = function_source("_created_at")
    assert "sa.DateTime(timezone=True)" in created_at
    assert 'server_default=sa.text("CURRENT_TIMESTAMP")' in created_at


def test_phase5_closed_vocabularies_are_exact() -> None:
    assert in_vocabulary("ck_eval_report_state", "state") == PROMOTION_STATES
    assert in_vocabulary("ck_eval_trial_status", "status") == TRIAL_STATUSES
    assert in_vocabulary("ck_eval_cost_scenario", "scenario") == COST_SCENARIOS
    assert in_vocabulary("ck_eval_gate_code", "gate_code") == GATE_CODES
    assert in_vocabulary("ck_eval_gate_outcome", "outcome") == {
        "pass",
        "fail",
        "blocked_missing_policy",
        "blocked_uncomputable",
        "research_only",
    }


def test_phase5_reports_bind_frozen_audit_and_server_input_fields() -> None:
    source = migration_source()
    report_columns = TABLE_COLUMNS["evaluation_reports"]
    for required in (
        "policy_sha256",
        "mapping_id",
        "configuration_sha256",
        "fixture_sha256",
        "snapshot_bundle_sha256",
        "git_sha",
        "random_seed",
        "raw_trial_count",
        "effective_trial_count",
        "effective_trial_count_method",
        "synthetic",
        "no_real_performance_claim",
        "payload",
        "state",
    ):
        assert required in report_columns
    assert "git_sha ~ '^[0-9a-f]{40}$'" in source
    assert "synthetic AND no_real_performance_claim" in source
    assert "expected_trial_count = raw_trial_count" in source
    assert "effective_trial_count <= raw_trial_count" in source
    assert "phase5-evaluation-request-v1" in source
    assert "phase5-evaluation-config-v1" in source
    assert "report columns are not bound by its frozen payload" in source
    for audit_binding in (
        "raw_trial_count",
        "effective_trial_count",
        "promotion_state",
    ):
        assert f"NEW.payload->>'{audit_binding}'" in source
    for child_collection in (
        "data_snapshots",
        "trials",
        "folds",
        "preprocessing_fits",
        "oos_ledger",
        "cost_ledger",
        "gates",
    ):
        assert f"jsonb_array_length(NEW.payload->'{child_collection}')" in source
    for binding in (
        "policy_id",
        "policy_version",
        "policy_sha256",
        "mapping_id",
        "mapping_version",
        "mapping_input_sha256",
        "fixture_id",
        "fixture_sha256",
        "snapshot_bundle_sha256",
        "code_version_git_sha",
        "random_seed",
    ):
        assert f"run_fingerprint_payload->>'{binding}'" in source


def test_phase5_artifact_hashes_are_domain_separated_and_payload_exact() -> None:
    source = migration_source()
    assert "CREATE FUNCTION validate_phase5_artifact_identity()" in source
    assert "artifact_canonical_json::jsonb IS DISTINCT FROM artifact_payload" in source
    assert "|| decode('00', 'hex')" in source
    assert "sha256(" in source

    identities_assignment = next(
        node
        for node in migration_tree().body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "ARTIFACT_IDENTITIES"
            for target in node.targets
        )
    )
    identities = ast.literal_eval(identities_assignment.value)
    assert set(identities) == PHASE5_TABLES
    assert len({domain for _, domain in identities.values()}) == len(PHASE5_TABLES)
    for table, (hash_column, domain) in identities.items():
        assert hash_column in TABLE_COLUMNS[table]
        assert domain.startswith("phase5-") and domain.endswith("-v1")
    assert identities["evaluation_feature_specs"][1] == "phase5-feature-specification-v1"
    assert identities["evaluation_label_specs"][1] == "phase5-label-specification-v1"
    assert identities["evaluation_blocked_outcomes"][1] == ("phase5-evaluation-blocked-outcome-v1")
    assert identities["evaluation_reports"][1] == "phase5-evaluation-artifact-v1"
    assert identities["evaluation_preprocessing_fits"] == (
        "statistics_sha256",
        "phase5-preprocessing-fit-v1",
    )
    assert identities["evaluation_oos_ledger"][1] == "phase5-ledger-entry-v1"


def test_phase5_blocked_outcomes_bind_semantic_idempotency_and_full_artifact() -> None:
    source = migration_source()
    columns = TABLE_COLUMNS["evaluation_blocked_outcomes"]
    for required in (
        "submission_sha256",
        "idempotency_sha256",
        "idempotency_canonical_json",
        "idempotency_payload",
        "resolved_policy_sha256",
        "resolved_fixture_sha256",
        "resolved_fixture_random_seed",
        "resolved_raw_trial_count",
        "resolved_snapshots",
        "failure_stage",
        "reason_codes",
        "created_at_utc",
    ):
        assert required in columns
    assert "phase5-evaluation-blocked-submission-v1" in source
    assert "phase5-evaluation-blocked-outcome-idempotency-v1" in source
    assert "phase5-evaluation-blocked-outcome-v1" in source
    assert "NEW.payload - 'idempotency_sha256' - 'created_at_utc'" in source
    assert "NEW.payload->>'created_at_utc'" in source
    assert "uq_eval_blocked_outcome_idempotency_sha256" in source
    assert "CREATE TRIGGER evaluation_blocked_outcomes_10_payload" in source


def test_phase5_policy_hash_commits_to_complete_information_specs() -> None:
    source = migration_source()
    for payload_binding in (
        "NEW.payload->'signal_specification'",
        "NEW.payload#>>'{signal_specification,forecast_horizon}'",
        "NEW.payload->'required_snapshot_capabilities'",
        "NEW.payload#>>'{label_specification,information_interval_rule}'",
        "NEW.payload->'costs'",
        "NEW.payload#>>'{costs,slippage_model_id}'",
        "NEW.payload->'walk_forward'",
        "NEW.payload->'risk'",
        "NEW.payload->'selection'",
        "NEW.payload->'sample_adequacy'",
        "NEW.payload#>>'{label_specification,missing_return_policy}'",
        "NEW.payload#>>'{sample_adequacy,missing_return_policy}'",
        "NEW.payload#>>'{label_specification,no_trade_return_policy}'",
        "NEW.payload#>>'{sample_adequacy,no_trade_return_policy}'",
        "NEW.payload->'regimes'",
        "NEW.payload->'audit'",
        "NEW.payload#>>'{stress,all_cost_multiplier}'",
    ):
        assert payload_binding in source
    assert "cost_stress_multiplier >= 2" in source
    assert "missing_return_policy = 'block_missing_return_v1'" in source
    assert "no_trade_return_policy = 'explicit_zero_research_observation_v1'" in source
    assert "NEW.expected_feature_spec_count <> 1" in source
    assert "NEW.expected_label_spec_count <> 1" in source
    assert "required capabilities must be unique and sorted" in source
    assert "policy.feature_spec_hashes IS DISTINCT FROM actual_feature_hashes" in source
    assert "policy.label_spec_hashes IS DISTINCT FROM actual_label_hashes" in source
    assert "CREATE CONSTRAINT TRIGGER evaluation_policies_complete" in source
    assert "evaluation_feature_specs'::regclass" in source
    assert "evaluation_label_specs'::regclass" in source


def test_phase5_snapshot_lineage_is_persisted_authorized_and_exact() -> None:
    source = migration_source()
    snapshot_columns = TABLE_COLUMNS["evaluation_report_snapshots"]
    for required in (
        "ordinal",
        "snapshot_id",
        "snapshot_sha256",
        "capability",
        "as_of_utc",
        "provider_id",
        "adapter_id",
        "adapter_version",
        "dataset_id",
        "product_id",
        "dataset_schema_id",
        "dataset_schema_version",
        "fixture_set_version",
    ):
        assert required in snapshot_columns
    assert "FROM data_snapshots" in source
    assert "FROM data_snapshot_manifests" in source
    assert "snapshot.mapping_id IS DISTINCT FROM report_mapping_id" in source
    assert "OR NOT snapshot.synthetic" in source
    assert "snapshot.quality_status IN (" in source
    assert "mapping_verdict <> 'BUILD_RESEARCH'" in source
    for family in (
        "A_CROSS_SECTIONAL_EQUITY_RANKING",
        "B_TIME_SERIES_MOMENTUM_REGIME",
        "C_OFFICIAL_EVENT_TEXT_OVERLAY",
    ):
        assert family in source
    assert "policy.required_snapshot_capabilities" in source
    assert "phase5-snapshot-bundle-v1" in source
    assert "snapshot bundle canonical payload mismatch" in source


def test_phase5_source_observations_and_sample_lineage_are_db_bound_exactly() -> None:
    source = migration_source()
    report_columns = TABLE_COLUMNS["evaluation_reports"]
    oos_columns = TABLE_COLUMNS["evaluation_oos_ledger"]
    for required in (
        "sample_lineage_sha256",
        "sample_lineage_canonical_json",
        "source_observations",
        "sample_lineage",
        "expected_source_observation_count",
        "expected_sample_lineage_count",
    ):
        assert required in report_columns
    assert {"sample_sha256", "source_observation_refs"} <= oos_columns
    assert "CREATE FUNCTION validate_phase5_report_source_lineage" in source
    assert "CREATE FUNCTION phase5_json_payload_equivalent" in source
    assert "left_text::timestamptz = right_text::timestamptz" in source
    assert "phase5-sample-source-lineage-v1" in source
    assert "sample lineage canonical payload mismatch" in source
    assert "LEFT JOIN data_snapshots AS snapshot" in source
    assert "FROM jsonb_array_elements(report_row.source_observations)" in source
    assert "LEFT JOIN data_normalized_observations AS observation" in source
    assert "LEFT JOIN data_snapshot_constituents AS constituent" in source
    assert "source_item#>'{normalized_observation,payload}'" in source
    assert "'included_as_of','retained_historical_vintage','explicit_missingness'" in source
    assert "unused_source_count" in source
    assert "invalid_derivation_count" in source
    assert "invalid_lineage_capability_count" in source
    assert "required_capabilities" in source
    assert "membership_source_observation_key" in source
    assert "invalid_membership_count" in source
    assert "'{normalized_observation,payload,status}'" in source
    assert "IS DISTINCT FROM 'included'" in source
    assert "feature_source.source_item#>>'{normalized_observation,instrument_id}'" in source
    assert "feature_source.source_item#>>'{normalized_observation,listing_id}'" in source
    assert "source-decimal-times-frozen-multiplier-v1" in source
    assert "deterministic-synthetic-research-ledger-input-v1" in source
    assert "'{normalized_observation,event_time}')::timestamptz" in source
    assert "'{normalized_observation,available_at}')::timestamptz" in source
    normalized_source = re.sub(r"\s+", " ", source)
    assert (
        "(resolved.source_item#>>'{normalized_observation,event_time}')::timestamptz "
        "> (lineage_item->>'feature_available_at_utc')::timestamptz" in normalized_source
    )
    assert (
        "(resolved.source_item#>>'{normalized_observation,available_at}')::timestamptz "
        "> (lineage_item->>'feature_available_at_utc')::timestamptz" in normalized_source
    )
    assert "'{normalized_observation,valid_from}')::timestamptz" in source
    assert "'{normalized_observation,valid_to}' IS NOT NULL" in source
    assert "oos.source_observation_refs IS DISTINCT FROM" in source
    assert "Phase 5 OOS row differs from frozen sample lineage" in source


def test_phase5_deferred_completeness_counts_all_trials_and_exact_ordinals() -> None:
    source = migration_source()
    assert "CREATE FUNCTION guard_phase5_expected_child_count()" in source
    assert "Phase 5 child append exceeds frozen expected count" in source
    assert "CREATE FUNCTION phase5_exact_ordinals(" in source
    assert "minimum_ordinal = 0" in source
    assert "maximum_ordinal = expected_count - 1" in source
    assert "actual_trial_count <> report.raw_trial_count" in source
    assert "raw trial count omits failed or abandoned trials" in source
    assert "DEFERRABLE INITIALLY DEFERRED" in source
    assert "CREATE CONSTRAINT TRIGGER evaluation_reports_complete" in source
    assert "CREATE TRIGGER {table}_00_expected_count" in source
    assert "CREATE CONSTRAINT TRIGGER {table}_report_complete" in source
    expected_count_tables = PHASE5_TABLES - {
        "evaluation_policies",
        "evaluation_blocked_outcomes",
        "evaluation_reports",
    }
    report_child_tables = PHASE5_TABLES - {
        "evaluation_policies",
        "evaluation_feature_specs",
        "evaluation_label_specs",
        "evaluation_blocked_outcomes",
        "evaluation_reports",
    }
    assert (
        set(
            ast.literal_eval(
                next(
                    node.value
                    for node in migration_tree().body
                    if isinstance(node, ast.Assign)
                    and any(
                        isinstance(target, ast.Name) and target.id == "PHASE5_POLICY_CHILD_TABLES"
                        for target in node.targets
                    )
                )
            )
        )
        | report_child_tables
        == expected_count_tables
    )
    assert (
        set(
            ast.literal_eval(
                next(
                    node.value
                    for node in migration_tree().body
                    if isinstance(node, ast.Assign)
                    and any(
                        isinstance(target, ast.Name) and target.id == "PHASE5_REPORT_CHILD_TABLES"
                        for target in node.targets
                    )
                )
            )
        )
        == report_child_tables
    )


def test_phase5_cost_and_gate_completeness_fail_closed() -> None:
    source = migration_source()
    for component in (
        "fee_cost",
        "spread_cost",
        "impact_cost",
        "latency_cost",
        "borrow_cost",
        "capacity_cost",
    ):
        assert f"stressed.{component} + power(10::numeric, -29)" in source
        assert f"baseline.{component} * 2" in source
    assert "count(DISTINCT cost.allocation_input_sha256) <> 1" in source
    assert "count(DISTINCT gross_return) <> 1" not in source
    assert "invalid_liquidity_stress_count" in source
    assert "stressed.fill_status = 'capacity_rejected'" in source
    assert "stressed.participation_rate < baseline.participation_rate" in source
    assert "scenario IN ('all_cost_stress','liquidity_stress')" in source
    assert "HAVING sum(net_return) <= 0" in source
    assert "report does not contain the exact gate set" in source
    assert "PASS_RESEARCH cannot bypass a gate or stressed edge" in source
    assert "blocked state requires a blocked gate" in source
    assert "regime-dependent state requires regime evidence" in source


def test_phase5_child_hash_preimages_and_numeric_precision_are_frozen() -> None:
    source = migration_source()
    assert "CREATE FUNCTION validate_phase5_child_payload_columns()" in source
    for table in (
        "evaluation_trials",
        "evaluation_folds",
        "evaluation_oos_ledger",
        "evaluation_cost_ledger",
        "evaluation_gate_results",
    ):
        assert table in source
    for report_collection in (
        "trials",
        "folds",
        "preprocessing_fits",
        "oos_ledger",
        "cost_ledger",
        "gates",
    ):
        assert f"report.payload->'{report_collection}'" in source
    assert "report payload differs from persisted child artifacts" in source
    assert "policy payload differs from persisted specifications" in source
    assert "evaluation_preprocessing_fits_10_record" in source
    assert "statistics preimage mismatch" in source
    assert "uq_eval_preprocessing_fit_fold" in source
    assert "expected_preprocessing_fit_count" in source
    assert "IS DISTINCT FROM NEW.expected_fold_count" in source
    assert "phase5-preprocessing-train-ids-v1" in source
    assert "phase5-train-only-fit-record-v1" in source
    assert "train_sample_ids_canonical_json" in source
    assert "fit_preimage_canonical_json" in source
    assert "stddev_samp" in source
    assert "NEW.train_sample_ids IS DISTINCT FROM fold_row.payload->'train_sample_ids'" in source
    assert "fold_row.payload->'test_sample_ids'" in source
    assert "fold_row.payload->'purged_sample_ids'" in source
    assert "fold_row.payload->'embargoed_sample_ids'" in source
    assert "lineage.lineage_item->>'sample_sha256'" in source
    assert "sa.Numeric(precision=38, scale=30)" in source
    assert "sa.Numeric(precision=38, scale=18)" not in source
    assert 'sa.Column("outcome", sa.String(length=32)' in source
    assert "fold_kind IN ('outer','inner','cpcv')" in source
    assert "fold_kind = 'cpcv' OR train_end_utc < test_start_utc" in source
    assert "capacity_cost >= 0" in source
    assert "return_status IN ('observed','no_trade','delisted','missing')" in source
    assert "return_status IN ('observed','no_trade','delisted')" in source
    assert "return_status = 'no_trade' AND fill_status = 'no_trade'" in source
    assert "fill_status = 'filled' OR (gross_return = 0" in source
    assert "filled_quantity + unfilled_quantity = requested_quantity" in source
    assert "rejected_quantity = unfilled_quantity" in source
    assert "config_canonical_json::jsonb = config_preimage" in source
    assert "CREATE FUNCTION validate_phase5_trial_return_calendar()" in source
    assert "Phase 5 missing trial return must retain a null value" in source
    assert "Phase 5 no-trade trial return must be exact zero" in source
    assert "return_observation_count = jsonb_array_length(net_returns)" in source
    assert "trial, OOS, and cost return statuses are not reconciled" in source
    assert "power(10::numeric, -29)" in source


def test_phase5_all_tables_reject_update_delete_and_truncate() -> None:
    source = migration_source()
    assert "CREATE FUNCTION reject_phase5_evaluation_mutation()" in source
    assert "Phase 5 evaluation records are append-only" in source
    assert "for table in PHASE5_TABLES:" in source
    assert "CREATE TRIGGER {table}_immutable" in source
    assert "BEFORE UPDATE OR DELETE ON {table}" in source
    assert "CREATE TRIGGER {table}_no_truncate" in source
    assert "BEFORE TRUNCATE ON {table}" in source


def test_phase5_downgrade_removes_only_phase5_objects_in_dependency_order() -> None:
    downgrade = function_source("downgrade")
    first_table_drop = min(downgrade.index(f'op.drop_table("{table}"') for table in PHASE5_TABLES)
    assert downgrade.rindex("DROP TRIGGER IF EXISTS") < first_table_drop
    assert downgrade.rindex("DROP FUNCTION IF EXISTS") < first_table_drop

    ordered_tables = (
        "evaluation_gate_results",
        "evaluation_cost_ledger",
        "evaluation_oos_ledger",
        "evaluation_preprocessing_fits",
        "evaluation_folds",
        "evaluation_trials",
        "evaluation_report_snapshots",
        "evaluation_blocked_outcomes",
        "evaluation_reports",
        "evaluation_label_specs",
        "evaluation_feature_specs",
        "evaluation_policies",
    )
    positions = [downgrade.index(f'op.drop_table("{table}"') for table in ordered_tables]
    assert positions == sorted(positions)
    for protected_prefix in (
        "research_audit_events",
        "source_",
        "extraction_",
        "research_mapping_",
        "mapping_",
        "data_",
    ):
        assert f'op.drop_table("{protected_prefix}' not in downgrade


def test_phase5_migration_contains_no_execution_or_real_performance_capability() -> None:
    source = migration_source().lower()
    assert "synthetic and no_real_performance_claim" in source
    for forbidden in (
        "broker",
        "buy_signal",
        "sell_signal",
        "position_size",
        "paper_order",
        "live_order",
        "phase6",
        "phase7",
    ):
        assert forbidden not in source
