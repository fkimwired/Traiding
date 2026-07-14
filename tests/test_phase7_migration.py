from __future__ import annotations

import ast
import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "services/api/migrations/versions/0007_phase7_approval_risk.py"
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
    "0006_phase6_research.py": ("7f4ab516a31208b7c5f5400b1b593d7675c75570fa839f524bfddea3152d7070"),
}

PHASE7_TABLES = {
    "approval_policies",
    "approval_scopes",
    "approval_authorizations",
    "approval_revocations",
    "approval_risk_inputs",
    "approval_assessments",
    "approval_checks",
}

CHECK_CODES = (
    "RESEARCH_PASS",
    "PHASE6_LINEAGE_COMPLETE",
    "POLICY_CURRENT",
    "POLICY_MATCH",
    "SCOPE_CURRENT",
    "SCOPE_MATCH",
    "AUTHORIZATION_CURRENT",
    "AUTHORIZATION_MATCH",
    "REVOCATION_CLEAR",
    "RISK_INPUT_FRESH",
    "GLOBAL_CONTROL_CLEAR",
    "STRATEGY_CONTROL_CLEAR",
    "DATA_QUALITY_CONTROL_CLEAR",
    "MARKET_CALENDAR_OPEN",
    "DUPLICATE_CONTEXT_CLEAR",
    "NOTIONAL_LIMIT",
    "GROSS_EXPOSURE_LIMIT",
    "NET_EXPOSURE_LIMIT",
    "SECTOR_EXPOSURE_LIMIT",
    "CONCENTRATION_LIMIT",
    "LIQUIDITY_MINIMUM",
    "TURNOVER_LIMIT",
    "VOLATILITY_LIMIT",
    "DAILY_LOSS_LIMIT",
    "DRAWDOWN_LIMIT",
)

TABLE_COLUMNS = {
    "approval_policies": {
        "approval_policy_version_id",
        "schema_version",
        "policy_id",
        "policy_version",
        "policy_sha256",
        "valid_from_utc",
        "expires_at_utc",
        "authorization_max_age_seconds",
        "risk_input_max_age_seconds",
        "required_check_codes",
        "max_notional",
        "max_gross_exposure",
        "max_abs_net_exposure",
        "max_sector_exposure",
        "max_concentration",
        "min_liquidity",
        "max_turnover",
        "max_volatility",
        "max_daily_loss",
        "max_drawdown",
        "synthetic",
        "payload",
        "created_at_utc",
    },
    "approval_scopes": {
        "approval_scope_version_id",
        "scope_sha256",
        "research_run_id",
        "research_artifact_sha256",
        "approval_policy_version_id",
        "permitted_universe_ids",
        "max_notional",
        "payload",
        "created_at_utc",
    },
    "approval_authorizations": {
        "human_authorization_evidence_id",
        "authorization_sha256",
        "research_run_id",
        "research_artifact_sha256",
        "approval_policy_version_id",
        "approval_scope_version_id",
        "authorized_by",
        "authorized_role",
        "authorized_at_utc",
        "review_at_utc",
        "expires_at_utc",
        "human_controlled",
        "payload",
        "created_at_utc",
    },
    "approval_risk_inputs": {
        "risk_input_id",
        "risk_input_sha256",
        "research_run_id",
        "research_artifact_sha256",
        "approval_policy_version_id",
        "approval_scope_version_id",
        "observed_at_utc",
        "global_control_clear",
        "strategy_control_clear",
        "data_quality_control_clear",
        "market_calendar_open",
        "duplicate_context_clear",
        "proposed_notional",
        "gross_exposure",
        "net_exposure",
        "sector_exposure",
        "concentration",
        "available_liquidity",
        "turnover",
        "volatility",
        "daily_loss",
        "drawdown",
        "payload",
        "created_at_utc",
    },
    "approval_revocations": {
        "revocation_id",
        "artifact_sha256",
        "request_fingerprint_sha256",
        "human_authorization_evidence_id",
        "authorization_sha256",
        "revocation_evidence_id",
        "revocation_evidence_sha256",
        "effective_at_utc",
        "artifact_payload",
        "created_at_utc",
    },
    "approval_assessments": {
        "assessment_id",
        "artifact_sha256",
        "request_fingerprint_sha256",
        "currentness_state_sha256",
        "revocation_set_sha256",
        "research_run_id",
        "research_artifact_sha256",
        "approval_policy_version_id",
        "approval_policy_sha256",
        "approval_scope_version_id",
        "approval_scope_sha256",
        "human_authorization_evidence_id",
        "authorization_sha256",
        "risk_input_id",
        "risk_input_sha256",
        "phase6_lineage_sha256",
        "revocation_ids",
        "outcome",
        "reason_codes",
        "execution_authorized",
        "execution_ready",
        "artifact_payload",
        "created_at_utc",
    },
    "approval_checks": {
        "assessment_id",
        "assessment_artifact_sha256",
        "ordinal",
        "code",
        "status",
        "reason_code",
        "observed_value",
        "threshold_value",
        "evidence_sha256s",
        "check_sha256",
        "payload",
        "created_at_utc",
    },
}


def source() -> str:
    return MIGRATION.read_text(encoding="utf-8")


def tree() -> ast.Module:
    return ast.parse(source())


def function_node(name: str) -> ast.FunctionDef:
    for node in tree().body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"missing migration function {name}")


def literal_calls(function_name: str, operation: str) -> set[str]:
    values: set[str] = set()
    for call in ast.walk(function_node(function_name)):
        if (
            isinstance(call, ast.Call)
            and isinstance(call.func, ast.Attribute)
            and call.func.attr == operation
            and call.args
            and isinstance(call.args[0], ast.Constant)
            and isinstance(call.args[0].value, str)
        ):
            values.add(call.args[0].value)
    return values


def create_table_calls() -> dict[str, ast.Call]:
    calls: dict[str, ast.Call] = {}
    for call in ast.walk(function_node("upgrade")):
        if (
            isinstance(call, ast.Call)
            and isinstance(call.func, ast.Attribute)
            and call.func.attr == "create_table"
            and call.args
            and isinstance(call.args[0], ast.Constant)
            and isinstance(call.args[0].value, str)
        ):
            calls[call.args[0].value] = call
    return calls


def column_names(call: ast.Call) -> set[str]:
    names: set[str] = set()
    for argument in call.args[1:]:
        if (
            isinstance(argument, ast.Call)
            and isinstance(argument.func, ast.Attribute)
            and argument.func.attr == "Column"
            and argument.args
            and isinstance(argument.args[0], ast.Constant)
            and isinstance(argument.args[0].value, str)
        ):
            names.add(argument.args[0].value)
        elif isinstance(argument, ast.Call) and isinstance(argument.func, ast.Name):
            if argument.func.id == "_payload":
                if argument.args and isinstance(argument.args[0], ast.Constant):
                    names.add(str(argument.args[0].value))
                else:
                    names.add("payload")
            elif argument.func.id == "_created_at":
                names.add("created_at_utc")
            elif argument.func.id == "_decimal" and isinstance(argument.args[0], ast.Constant):
                names.add(str(argument.args[0].value))
    return names


def test_phase7_revision_directly_extends_frozen_phase6() -> None:
    module = tree()
    assignments: dict[str, object] = {}
    for node in module.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            assignments[node.target.id] = ast.literal_eval(node.value)
        elif (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
        ):
            assignments[node.targets[0].id] = ast.literal_eval(node.value)
    assert assignments["revision"] == "0007_phase7"
    assert assignments["down_revision"] == "0006_phase6"


def test_phase7_does_not_modify_any_prior_migration_bytes() -> None:
    versions = ROOT / "services/api/migrations/versions"
    for filename, expected in PRIOR_MIGRATIONS.items():
        actual = hashlib.sha256((versions / filename).read_bytes()).hexdigest()
        assert actual == expected, filename


def test_phase7_creates_exactly_seven_approval_tables_and_no_seed_rows() -> None:
    assert set(create_table_calls()) == PHASE7_TABLES
    lowered = source().lower()
    assert "bulk_insert" not in lowered
    assert "insert into approval_" not in lowered


def test_phase7_tables_contain_the_required_lineage_and_safety_columns() -> None:
    calls = create_table_calls()
    for table, required in TABLE_COLUMNS.items():
        assert required <= column_names(calls[table]), table


def test_phase7_exact_composite_lineage_and_restrict_foreign_keys_are_present() -> None:
    migration = source()
    assert "uq_research_pipeline_run_id_artifact_sha256" in migration
    assert '["research_run_id", "research_artifact_sha256"]' in migration
    assert '["research_pipeline_runs.id", "research_pipeline_runs.artifact_sha256"]' in migration
    assert migration.count('ondelete="RESTRICT"') >= 15
    assert "CASCADE" not in migration


def test_phase7_uses_the_exact_frozen_ordered_check_registry() -> None:
    module = tree()
    assignment = next(
        node
        for node in module.body
        if isinstance(node, ast.Assign)
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id == "PHASE7_CHECK_CODES"
    )
    assert ast.literal_eval(assignment.value) == CHECK_CODES
    migration = source()
    assert "actual_count <> {len(PHASE7_CHECK_CODES)}" in migration
    assert "minimum_ordinal <> 1" in migration
    assert "maximum_ordinal <> {len(PHASE7_CHECK_CODES)}" in migration
    assert "actual_payloads IS DISTINCT FROM" in migration


def test_phase7_positive_branch_is_fail_closed_but_negative_evidence_can_persist() -> None:
    migration = source()
    assert "IF TG_TABLE_NAME = 'approval_assessments' THEN" in migration
    assert "TG_TABLE_NAME = 'approval_assessments'\n               AND NEW.outcome" not in migration
    assert "TG_TABLE_NAME <> 'approval_assessments'\n               OR NEW.outcome" not in migration
    assert "NEW.outcome = 'APPROVED_PAPER'" in migration
    assert "run_row.promotion_state <> 'PASS_RESEARCH'" in migration
    assert "IF NEW.outcome = 'FAIL_REJECT' THEN" in migration
    assert "(assessment_row.outcome = 'APPROVED_PAPER') IS DISTINCT FROM all_pass" in migration
    assert "Phase 7 assessment evidence lineage mismatch" in migration
    assert "risk_row.global_control_clear IS DISTINCT FROM TRUE" in migration
    assert "risk_row.proposed_notional > LEAST" in migration
    assert "approval_revocations AS revocation" in migration
    assert "positive approval evidence is stale, revoked" in migration


def test_phase7_database_recomputes_hashes_and_deterministic_identities() -> None:
    migration = source()
    for domain in (
        "phase7-approval-policy-v1",
        "phase7-approval-scope-v1",
        "phase7-human-authorization-evidence-v1",
        "phase7-approval-risk-input-v1",
        "phase7-phase6-approval-lineage-v1",
        "phase7-approval-check-v1",
        "phase7-authorization-revocation-set-v1",
        "phase7-approval-currentness-state-v1",
        "phase7-approval-assessment-request-v1",
        "phase7-approval-assessment-v1",
        "phase7-authorization-revocation-v1",
    ):
        assert f"'{domain}'" in migration
    assert migration.count("phase6_domain_sha256(") >= 11
    assert migration.count("phase6_uuid5(") >= 6
    assert "assessment revocation-set hash mismatch" in migration
    assert "assessment currentness-state hash mismatch" in migration
    assert "assessment request fingerprint mismatch" in migration


def test_phase7_serializes_assessment_and_revocation_on_authorization_identity() -> None:
    migration = source()
    assert "phase7_lock_authorization_identity" in migration
    assert "approval_assessments_40_authorization_lock" in migration
    assert "approval_revocations_40_authorization_lock" in migration
    assert "hashtextextended(NEW.human_authorization_evidence_id::text, 0)" in migration


def test_phase7_all_tables_reject_update_delete_and_truncate_with_exact_error() -> None:
    migration = source()
    assert "Phase 7 approval and risk artifacts are append-only" in migration
    assert "for table in PHASE7_TABLES" in migration
    assert "BEFORE UPDATE OR DELETE" in migration
    assert "BEFORE TRUNCATE" in migration
    assert "FOR EACH STATEMENT" in migration


def test_phase7_created_timestamps_are_database_owned() -> None:
    migration = source()
    assert "CREATE FUNCTION own_phase7_created_at_utc()" in migration
    assert "NEW.created_at_utc := clock_timestamp()" in migration
    assert "NEW.created_at_utc := CURRENT_TIMESTAMP" not in migration
    assert "CREATE TRIGGER {table}_00_created_at_utc" in migration
    assert "assessment_time := NEW.created_at_utc" in migration
    assert "2026-07-14 12:00:00+00" not in migration


def test_phase7_hashed_payloads_bind_every_persisted_decision_column() -> None:
    migration = source()
    validator = migration.split(
        "CREATE FUNCTION validate_phase7_payload_consistency()", maxsplit=1
    )[1].split("CREATE FUNCTION validate_phase7_assessment_lineage()", maxsplit=1)[0]
    branch_markers = (
        "approval_policies",
        "approval_scopes",
        "approval_authorizations",
        "approval_risk_inputs",
        "approval_assessments",
        "approval_revocations",
        "approval_checks",
    )
    branches: dict[str, str] = {}
    for index, table in enumerate(branch_markers):
        start = validator.index(f"TG_TABLE_NAME = '{table}'")
        end = (
            validator.index(f"TG_TABLE_NAME = '{branch_markers[index + 1]}'", start)
            if index + 1 < len(branch_markers)
            else len(validator)
        )
        branches[table] = validator[start:end]

    expected_payload_key_counts = {
        "approval_policies": 19,
        "approval_scopes": 11,
        "approval_authorizations": 13,
        "approval_risk_inputs": 23,
        "approval_assessments": 26,
        "approval_revocations": 16,
        "approval_checks": 8,
    }
    persisted_payload_bindings = {
        "approval_policies": {
            "approval_policy_version_id",
            "schema_version",
            "policy_id",
            "policy_version",
            "policy_sha256",
            "valid_from_utc",
            "expires_at_utc",
            "risk_input_max_age_seconds",
            "authorization_max_age_seconds",
            "required_check_codes",
            "max_notional",
            "max_gross_exposure",
            "max_abs_net_exposure",
            "max_sector_exposure",
            "max_concentration",
            "min_liquidity",
            "max_turnover",
            "max_volatility",
            "max_daily_loss",
            "max_drawdown",
            "synthetic",
        },
        "approval_scopes": {
            "approval_scope_version_id",
            "schema_version",
            "scope_id",
            "scope_version",
            "scope_sha256",
            "research_run_id",
            "research_artifact_sha256",
            "approval_policy_version_id",
            "permitted_universe_ids",
            "max_notional",
            "valid_from_utc",
            "expires_at_utc",
            "synthetic",
        },
        "approval_authorizations": {
            "human_authorization_evidence_id",
            "schema_version",
            "authorization_sha256",
            "research_run_id",
            "research_artifact_sha256",
            "approval_policy_version_id",
            "approval_scope_version_id",
            "authorized_by",
            "authorized_role",
            "rationale",
            "authorized_at_utc",
            "review_at_utc",
            "expires_at_utc",
            "human_controlled",
            "synthetic",
        },
        "approval_risk_inputs": {
            "risk_input_id",
            "schema_version",
            "risk_input_sha256",
            "research_run_id",
            "research_artifact_sha256",
            "approval_policy_version_id",
            "approval_scope_version_id",
            "universe_id",
            "observed_at_utc",
            "global_control_clear",
            "strategy_control_clear",
            "data_quality_control_clear",
            "market_calendar_open",
            "duplicate_context_clear",
            "proposed_notional",
            "gross_exposure",
            "net_exposure",
            "sector_exposure",
            "concentration",
            "available_liquidity",
            "turnover",
            "volatility",
            "daily_loss",
            "drawdown",
            "synthetic",
        },
        "approval_assessments": {
            "assessment_id",
            "artifact_schema_version",
            "artifact_sha256",
            "request_fingerprint_sha256",
            "currentness_state_sha256",
            "revocation_set_sha256",
            "research_run_id",
            "research_artifact_sha256",
            "approval_policy_version_id",
            "approval_policy_sha256",
            "approval_scope_version_id",
            "approval_scope_sha256",
            "human_authorization_evidence_id",
            "authorization_sha256",
            "risk_input_id",
            "risk_input_sha256",
            "phase6_lineage_sha256",
            "revocation_ids",
            "outcome",
            "reason_codes",
            "phase7_code_version_git_sha",
            "synthetic",
            "simulated_paper_only",
            "execution_authorized",
            "execution_ready",
            "no_personalized_investment_advice",
            "no_real_performance_claimed",
        },
        "approval_revocations": {
            "revocation_id",
            "artifact_schema_version",
            "artifact_sha256",
            "request_fingerprint_sha256",
            "human_authorization_evidence_id",
            "authorization_sha256",
            "revocation_evidence_id",
            "revocation_evidence_sha256",
            "revoked_by",
            "reason",
            "effective_at_utc",
            "phase7_code_version_git_sha",
            "synthetic",
            "simulated_paper_only",
            "execution_authorized",
            "execution_ready",
            "no_personalized_investment_advice",
            "no_real_performance_claimed",
        },
        "approval_checks": {
            "ordinal",
            "code",
            "status",
            "reason_code",
            "observed_value",
            "threshold_value",
            "evidence_sha256s",
            "check_sha256",
        },
    }

    for table, expected_count in expected_payload_key_counts.items():
        branch = branches[table]
        assert f"<> {expected_count}" in branch, table
        for column in persisted_payload_bindings[table]:
            pattern = rf"IS DISTINCT FROM\s+NEW\.{re.escape(column)}\b"
            assert re.search(pattern, branch), f"{table}.{column} is not payload-bound"


def test_phase7_downgrade_drops_only_phase7_tables_and_restores_phase6_shape() -> None:
    assert literal_calls("downgrade", "drop_table") == set()
    downgrade = ast.get_source_segment(source(), function_node("downgrade"))
    assert downgrade is not None
    assert "for table in reversed(PHASE7_TABLES)" in downgrade
    assert "uq_research_pipeline_run_id_artifact_sha256" in downgrade
    assert "research_pipeline_runs" in downgrade
    assert "drop_column" not in downgrade
    assert 'drop_table("research_pipeline_runs")' not in downgrade


def test_phase7_migration_contains_no_execution_storage_or_live_path() -> None:
    lowered = source().lower()
    for forbidden in (
        "broker_url",
        "broker_client",
        "order_submission",
        "paper_execution",
        "live_trading",
        "position_size",
        "fill_price",
    ):
        assert forbidden not in lowered
    assert "not execution_authorized" in lowered
    assert "not execution_ready" in lowered
