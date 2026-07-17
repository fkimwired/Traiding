from __future__ import annotations

import ast
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "services/api/migrations/versions/0008_phase10_local_paper.py"
REPOSITORY = ROOT / "services/paper/src/fable5_paper/repository.py"
PHASE7_MIGRATION = ROOT / "services/api/migrations/versions/0007_phase7_approval_risk.py"
PHASE7_SHA256 = "4ef4e6301f205fb9a18f478ac3fa6d6920dbe0af462b6f371e83dd2d622a8090"

PHASE10_TABLES = {
    "paper_simulation_runs",
    "paper_simulation_checks",
    "paper_simulation_ledger_entries",
}
CHECK_CODES = (
    "SOURCE_APPROVAL_EXACT",
    "TRANSITION_APPROVAL_FRESH",
    "RESEARCH_PREREQUISITES_COMPLETE",
    "SIMULATION_CONFIGURATION_EXACT",
    "RISK_CONTEXT_EXACT",
    "COST_SLIPPAGE_COMPLETE",
    "LOCAL_BOUNDARY_ENFORCED",
)


def source() -> str:
    return MIGRATION.read_text(encoding="utf-8")


def repository_source() -> str:
    return REPOSITORY.read_text(encoding="utf-8")


def tree() -> ast.Module:
    return ast.parse(source())


def function_node(name: str) -> ast.FunctionDef:
    for node in tree().body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"missing migration function {name}")


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
        ):
            names.add(str(argument.args[0].value))
        elif isinstance(argument, ast.Call) and isinstance(argument.func, ast.Name):
            if argument.func.id == "_payload":
                names.add("payload")
            elif argument.func.id == "_created_at":
                names.add("created_at_utc")
            elif argument.func.id == "_decimal" and isinstance(argument.args[0], ast.Constant):
                names.add(str(argument.args[0].value))
    return names


def assignment(name: str) -> object:
    for node in tree().body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.target.id == name:
                return ast.literal_eval(node.value)
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            if node.targets[0].id == name:
                return ast.literal_eval(node.value)
    raise AssertionError(f"missing assignment {name}")


def test_phase10_directly_extends_the_frozen_phase7_revision() -> None:
    assert assignment("revision") == "0008_phase10"
    assert assignment("down_revision") == "0007_phase7"
    assert hashlib.sha256(PHASE7_MIGRATION.read_bytes()).hexdigest() == PHASE7_SHA256


def test_phase10_creates_exactly_three_tables_and_no_seed_rows() -> None:
    assert set(create_table_calls()) == PHASE10_TABLES
    lowered = source().lower()
    assert "bulk_insert" not in lowered
    assert "insert into paper_simulation" not in lowered


def test_phase10_tables_hold_exact_lineage_hashes_and_immutable_children() -> None:
    calls = create_table_calls()
    run_columns = column_names(calls["paper_simulation_runs"])
    for prefix in (
        "source_assessment",
        "transition_assessment",
        "research_artifact",
        "approval_policy",
        "approval_scope",
        "authorization",
        "risk_input",
        "configuration",
    ):
        assert any(column.startswith(prefix) for column in run_columns), prefix
    assert {
        "artifact_sha256",
        "request_fingerprint_sha256",
        "currentness_state_sha256",
        "artifact_payload",
        "decision_time_utc",
        "created_at_utc",
    } <= run_columns
    for table in ("paper_simulation_checks", "paper_simulation_ledger_entries"):
        assert {
            "simulation_run_id",
            "simulation_artifact_sha256",
            "payload",
            "created_at_utc",
        } <= column_names(calls[table])


def test_phase10_uses_composite_hash_foreign_keys_without_cascade() -> None:
    migration = source()
    for target in (
        "approval_assessments.assessment_id",
        "research_pipeline_runs.id",
        "approval_policies.approval_policy_version_id",
        "approval_scopes.approval_scope_version_id",
        "approval_authorizations.human_authorization_evidence_id",
        "approval_risk_inputs.risk_input_id",
        "paper_simulation_runs.simulation_run_id",
    ):
        assert target in migration
    assert migration.count('ondelete="RESTRICT"') == 9
    assert "CASCADE" not in migration


def test_phase10_recomputes_every_hash_identity_and_binds_child_payloads() -> None:
    migration = source()
    for domain in (
        "phase10-local-simulation-currentness-v1",
        "phase10-local-simulation-request-v1",
        "phase10-local-simulation-configuration-v1",
        "phase10-local-simulation-check-v1",
        "phase10-local-simulation-ledger-v1",
        "phase10-local-simulation-artifact-v1",
    ):
        assert f"'{domain}'" in migration
    for namespace in (
        "94855828-a04c-54f9-ae66-dd00ef7a1010",
        "156cc8af-3b68-508b-b7f2-8bb1818f1010",
        "052c40b0-7781-57d9-942a-651518c41010",
    ):
        assert namespace in migration
    assert migration.count("phase6_domain_sha256(") >= 6
    assert migration.count("phase6_uuid5(") >= 3
    assert "actual_checks IS DISTINCT FROM run_row.artifact_payload->'checks'" in migration
    assert "actual_ledger IS DISTINCT FROM run_row.artifact_payload->'ledger_entries'" in migration


def test_phase10_uses_the_frozen_check_registry_and_deferred_exact_completeness() -> None:
    assert assignment("PHASE10_CHECK_CODES") == CHECK_CODES
    migration = source()
    assert "DEFERRABLE INITIALLY DEFERRED" in migration
    assert "for table in PHASE10_TABLES" in migration
    assert "check_count <> {len(PHASE10_CHECK_CODES)}" in migration
    assert "minimum_ordinal <> 1" in migration
    assert "ledger_count <> 1" in migration
    assert "ledger_count <> 0" in migration
    assert "(run_row.outcome = 'SIMULATED_COMPLETE') IS DISTINCT FROM all_pass" in migration


def test_phase10_database_revalidates_authority_under_a_shared_lock() -> None:
    migration = source()
    assert "pg_advisory_xact_lock" in migration
    assert "hashtextextended(NEW.human_authorization_evidence_id::text, 0)" in migration
    assert "source and transition lineage mismatch" in migration
    assert "NEW.outcome <> 'BLOCKED'" in migration
    assert "transition_row.outcome <> 'FAIL_REJECT'" in migration
    assert "candidate.policy_id = source_policy_row.policy_id" in migration
    assert "candidate.scope_id = source_scope_row.scope_id" in migration
    assert "ORDER BY candidate.policy_version DESC" in migration
    assert "ORDER BY candidate.scope_version DESC" in migration
    assert "current_revocations IS DISTINCT FROM transition_row.revocation_ids" in migration
    assert "effective_at_utc <= NEW.created_at_utc" in migration
    assert "NEW.decision_time_utc > NEW.created_at_utc" in migration
    assert migration.index("source and transition lineage mismatch") < migration.index(
        "IF NEW.outcome <> 'SIMULATED_COMPLETE'"
    )
    assert "risk_row.proposed_notional > LEAST" in migration
    assert "Phase 10 simulation authority is stale, revoked, mismatched, or unsafe" in migration


def test_phase10_database_binds_all_ledger_columns_to_the_hashed_payload() -> None:
    migration = source()
    validator = migration.split("CREATE FUNCTION validate_phase10_ledger_payload()", 1)[1]
    validator = validator.split("CREATE FUNCTION validate_phase10_simulation_completeness()", 1)[0]
    ledger_columns = column_names(create_table_calls()["paper_simulation_ledger_entries"])
    excluded = {"simulation_artifact_sha256", "payload", "created_at_utc"}
    for column in ledger_columns - excluded:
        assert f"NEW.payload->>'{column}'" in validator, column
    assert "filled_quantity + NEW.unfilled_quantity" in validator
    assert "NEW.total_cost <> NEW.commission_cost" in validator
    assert "NEW.cash_after" in validator


def test_phase10_root_enforces_local_mock_only_configuration_and_disclaimer() -> None:
    migration = source()
    assert "count(*) FROM jsonb_object_keys(configuration)) <> 46" in migration
    assert "phase10-a-local-mock-qa-v1" in migration
    assert "phase10-local-transparent-cost-v1" in migration
    assert "phase10-local-transparent-slippage-v1" in migration
    assert "llm_decision_role_absent" in migration
    assert "Deterministic synthetic local paper simulation only" in migration
    assert "configuration->>'observed_at_utc'" in migration
    assert "configuration->>'available_at_utc'" in migration


def test_phase10_all_tables_are_database_timestamped_and_append_only() -> None:
    migration = source()
    assert "NEW.created_at_utc := clock_timestamp()" in migration
    assert "Phase 10 local paper simulation artifacts are append-only" in migration
    assert "BEFORE UPDATE OR DELETE" in migration
    assert "BEFORE TRUNCATE" in migration
    assert "FOR EACH STATEMENT" in migration


def test_phase10_repository_revalidates_hashes_children_and_serializes_writers() -> None:
    repository = repository_source()
    for required in (
        "PHASE10_ARTIFACT_HASH_DOMAIN",
        "PHASE10_CHECK_HASH_DOMAIN",
        "PHASE10_LEDGER_HASH_DOMAIN",
        '_same(payload.get("checks"), checks)',
        '_same(payload.get("ledger_entries"), ledger_entries)',
        "authorization revocation set changed before simulation persistence",
        "simulation idempotency key is bound to different evidence",
        "simulation request fingerprint is bound to another idempotency key",
    ):
        assert required in repository
    create = repository.split("def create_simulation", 1)[1].split("def get_simulation", 1)[0]
    assert create.index("artifact.human_authorization_evidence_id") < create.index(
        "artifact.simulation_idempotency_key"
    )
    assert create.index("_lock(connection") < create.index("_insert_simulation(connection")


def test_phase10_downgrade_removes_only_phase10_objects() -> None:
    downgrade = ast.get_source_segment(source(), function_node("downgrade"))
    assert downgrade is not None
    assert "for table in reversed(PHASE10_TABLES)" in downgrade
    assert "drop_column" not in downgrade
    assert "approval_" not in downgrade
    assert "research_pipeline_runs" not in downgrade


def test_phase10_storage_contains_no_external_submission_capability() -> None:
    lowered = (source() + repository_source()).lower()
    for forbidden in (
        "broker_url",
        "broker_client",
        "order_submission",
        "requests.post",
        "httpx.client",
        "live_trading_mode",
    ):
        assert forbidden not in lowered
    assert "not external_submission" in lowered
    assert "live_path_absent" in lowered
