from __future__ import annotations

import ast
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = (
    ROOT / "services/api/migrations/versions/0009_phase12_external_paper_shadow_readiness.py"
)
REPOSITORY = ROOT / "services/paper/src/fable5_paper/phase12/repository.py"
PHASE10_MIGRATION = ROOT / "services/api/migrations/versions/0008_phase10_local_paper.py"
PHASE10_SHA256 = "947293ff5c6b471045479aee280904346a6ef03733ec2b8e92dc03b87a30e405"

PHASE12_TABLES = {
    "paper_shadow_readiness_runs",
    "paper_shadow_readiness_checks",
}
CHECK_CODES = (
    "SOURCE_KIND_EXACT",
    "READ_ONLY_TRANSPORT_EXACT",
    "ACCOUNT_READY",
    "MARKET_CLOCK_OPEN",
    "INSTRUMENT_ACTIVE_TRADABLE",
    "POSITIONS_EMPTY",
    "OPEN_ORDERS_EMPTY",
    "IEX_QUOTE_FRESH_VALID",
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


def test_phase12_directly_extends_the_frozen_phase10_revision() -> None:
    assert assignment("revision") == "0009_phase12"
    assert assignment("down_revision") == "0008_phase10"
    assert hashlib.sha256(PHASE10_MIGRATION.read_bytes()).hexdigest() == PHASE10_SHA256


def test_phase12_creates_exactly_two_tables_and_no_seed_rows() -> None:
    assert set(create_table_calls()) == PHASE12_TABLES
    lowered = source().lower()
    assert "bulk_insert" not in lowered
    assert "insert into paper_shadow_readiness" not in lowered


def test_phase12_root_and_children_hold_only_sanitized_hash_bound_evidence() -> None:
    calls = create_table_calls()
    assert {
        "readiness_assessment_id",
        "artifact_schema_version",
        "artifact_sha256",
        "request_fingerprint_sha256",
        "readiness_idempotency_key",
        "source_kind",
        "transport_profile_sha256",
        "outcome",
        "reason_codes",
        "phase12_code_version_git_sha",
        "assessment_started_at_utc",
        "assessment_completed_at_utc",
        "expires_at_utc",
        "order_submission_authorized",
        "strategy_execution_eligible",
        "live_path_absent",
        "no_personalized_investment_advice",
        "no_real_performance_claimed",
        "artifact_payload",
        "created_at_utc",
    } == column_names(calls["paper_shadow_readiness_runs"])
    assert {
        "readiness_assessment_id",
        "readiness_artifact_sha256",
        "schema_version",
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
    } == column_names(calls["paper_shadow_readiness_checks"])
    lowered = source().lower()
    for forbidden in (
        "api_key",
        "secret_key",
        "authorization_header",
        "account_number",
        "raw_payload",
        "order_side",
        "order_quantity",
        "fill_price",
    ):
        assert forbidden not in lowered


def test_phase12_uses_composite_hash_lineage_without_cascade() -> None:
    migration = source()
    assert "paper_shadow_readiness_runs.readiness_assessment_id" in migration
    assert "paper_shadow_readiness_runs.artifact_sha256" in migration
    assert 'ondelete="RESTRICT"' in migration
    assert "CASCADE" not in migration
    assert "uq_paper_shadow_readiness_run_artifact" in migration


def test_phase12_recomputes_request_artifact_and_check_hashes_and_identity() -> None:
    migration = source()
    for domain in (
        "phase12-paper-shadow-request-v1",
        "phase12-paper-shadow-artifact-v1",
        "phase12-paper-shadow-check-v1",
    ):
        assert f"'{domain}'" in migration
    assert "f1195f7e-e891-5c21-9d3b-a0ced8881212" in migration
    assert migration.count("phase6_domain_sha256(") >= 3
    assert "phase6_uuid5(" in migration
    assert "expected_request IS DISTINCT FROM NEW.request_fingerprint_sha256" in migration
    assert "expected_artifact IS DISTINCT FROM NEW.artifact_sha256" in migration
    assert "actual_checks IS DISTINCT FROM run_row.artifact_payload->'checks'" in migration


def test_phase12_uses_exact_deferred_eight_check_completeness() -> None:
    assert assignment("PHASE12_CHECK_CODES") == CHECK_CODES
    migration = source()
    assert "DEFERRABLE INITIALLY DEFERRED" in migration
    assert "for table in PHASE12_TABLES" in migration
    assert "check_count <> {len(PHASE12_CHECK_CODES)}" in migration
    assert "minimum_ordinal <> 1" in migration
    assert "expected_outcome IS DISTINCT FROM run_row.outcome" in migration
    assert "all_mock_readiness_checks_passed" in migration
    assert "all_external_shadow_readiness_checks_passed" in migration


def test_phase12_enforces_mock_external_outcomes_ttl_and_false_authority() -> None:
    migration = source()
    for required in (
        "DETERMINISTIC_MOCK",
        "ALPACA_PAPER_READ_ONLY",
        "MOCK_PROOF_COMPLETE",
        "SHADOW_READY",
        "BLOCKED",
        "interval '60 seconds'",
        "0abdef0f61353960485a354cb00bebd137e387e857202f020a2caec25cb5926c",
        "NOT order_submission_authorized",
        "NOT strategy_execution_eligible",
        "live_path_absent",
        "no_personalized_investment_advice",
        "no_real_performance_claimed",
    ):
        assert required in migration
    assert "source_kind = 'DETERMINISTIC_MOCK' AND outcome = 'SHADOW_READY'" in migration
    assert "schema_version = 'phase12-paper-shadow-readiness-check-v1'" in migration


def test_phase12_database_owns_timestamps_locks_writers_and_is_append_only() -> None:
    migration = source()
    assert "NEW.created_at_utc := clock_timestamp()" in migration
    assert "pg_advisory_xact_lock" in migration
    assert "phase12-readiness-workflow:" in migration
    assert "Phase 12 paper shadow-readiness artifacts are append-only" in migration
    assert "BEFORE UPDATE OR DELETE" in migration
    assert "BEFORE TRUNCATE" in migration
    assert "FOR EACH STATEMENT" in migration


def test_phase12_repository_revalidates_hashes_and_serializes_before_lookup() -> None:
    repository = repository_source()
    for required in (
        "PHASE12_ARTIFACT_HASH_DOMAIN",
        "PHASE12_CHECK_HASH_DOMAIN",
        '_same(payload.get("checks"), checks)',
        "readiness idempotency key is bound to a different request fingerprint",
        "readiness request fingerprint is bound to another idempotency key",
    ):
        assert required in repository
    serialized = repository.split("def serialized_creation", 1)[1].split("def create_readiness", 1)[
        0
    ]
    assert serialized.index("_workflow_lock_identity(key)") < serialized.index("yield")


def test_phase12_downgrade_removes_only_phase12_objects() -> None:
    downgrade = ast.get_source_segment(source(), function_node("downgrade"))
    assert downgrade is not None
    assert "for table in reversed(PHASE12_TABLES)" in downgrade
    assert "drop_column" not in downgrade
    assert "paper_simulation" not in downgrade
    assert "approval_" not in downgrade
    assert "research_" not in downgrade
