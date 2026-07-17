from __future__ import annotations

import ast
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = (
    ROOT / "services/api/migrations/versions/0010_phase13_point_in_time_data_qualification.py"
)
REPOSITORY = ROOT / "services/data/src/fable5_data/phase13/repository.py"
PHASE12_MIGRATION = (
    ROOT / "services/api/migrations/versions/0009_phase12_external_paper_shadow_readiness.py"
)
PHASE12_SHA256 = "91de6880e4f1f3520fb47619e29bc92bce20f0d2cd15d08e62a7602183f31e02"

PHASE13_TABLES = {
    "point_in_time_qualification_runs",
    "point_in_time_qualification_payloads",
    "point_in_time_qualification_checks",
}
CAPABILITY_CODES = (
    "SECURITY_MASTER_STABLE_IDENTITY",
    "POINT_IN_TIME_UNIVERSE_MEMBERSHIP",
    "RAW_OHLCV_AVAILABILITY",
    "CORPORATE_ACTION_ANNOUNCEMENT_REVISION",
    "DELISTING_RETURN_SEMANTICS",
    "AS_REPORTED_FUNDAMENTAL_REVISION",
)
CHECK_CODES = (
    "SOURCE_KIND_EXACT",
    "READ_ONLY_TRANSPORT_EXACT",
    "USE_RIGHTS_CURRENT_SUFFICIENT",
    "SECURITY_MASTER_STABLE_IDENTITY",
    "POINT_IN_TIME_UNIVERSE_MEMBERSHIP",
    "RAW_OHLCV_AVAILABILITY",
    "CORPORATE_ACTION_ANNOUNCEMENT_REVISION",
    "DELISTING_RETURN_SEMANTICS",
    "AS_REPORTED_FUNDAMENTAL_REVISION",
    "RAW_NORMALIZED_RECONCILIATION",
    "NULL_SENTINEL_SCHEMA_DRIFT",
    "DETERMINISTIC_CAPTURE_MANIFEST",
)
FUNCTIONS = (
    "own_phase13_created_at_utc",
    "phase13_lock_qualification_idempotency",
    "validate_phase13_qualification_root_payload",
    "validate_phase13_qualification_payload_manifest",
    "validate_phase13_qualification_check_payload",
    "validate_phase13_qualification_completeness",
    "reject_phase13_qualification_mutation",
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


def assignment(name: str) -> object:
    for node in tree().body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.target.id == name:
                return ast.literal_eval(node.value)
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            if node.targets[0].id == name:
                return ast.literal_eval(node.value)
    raise AssertionError(f"missing assignment {name}")


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


def test_phase13_directly_extends_the_accepted_phase12_revision() -> None:
    assert assignment("revision") == "0010_phase13"
    assert assignment("down_revision") == "0009_phase12"
    assert hashlib.sha256(PHASE12_MIGRATION.read_bytes()).hexdigest() == PHASE12_SHA256


def test_phase13_creates_exactly_three_tables_without_seed_rows() -> None:
    assert set(create_table_calls()) == PHASE13_TABLES
    lowered = source().lower()
    assert "bulk_insert" not in lowered
    assert "insert into point_in_time_qualification" not in lowered


def test_phase13_freezes_exact_capability_and_check_registries() -> None:
    assert assignment("PHASE13_CAPABILITY_CODES") == CAPABILITY_CODES
    assert assignment("PHASE13_CHECK_CODES") == CHECK_CODES
    migration = source()
    assert "DEFERRABLE INITIALLY DEFERRED" in migration
    assert "payload_count <> {len(PHASE13_CAPABILITY_CODES)}" in migration
    assert "check_count <> {len(PHASE13_CHECK_CODES)}" in migration


def test_phase13_uses_composite_hash_lineage_and_recomputes_canonical_identity() -> None:
    migration = source()
    assert "point_in_time_qualification_runs.qualification_id" in migration
    assert "point_in_time_qualification_runs.artifact_sha256" in migration
    assert 'ondelete="RESTRICT"' in migration
    assert " CASCADE" not in migration
    for domain in (
        "phase13-pit-qualification-request-v1",
        "phase13-pit-qualification-artifact-v1",
        "phase13-pit-capability-manifest-v1",
        "phase13-pit-qualification-check-v1",
    ):
        assert domain in migration
    assert "phase6_domain_sha256(" in migration
    assert "phase6_uuid5(" in migration


def test_phase13_enforces_source_outcome_and_false_authority_boundary() -> None:
    migration = source()
    for required in (
        "DETERMINISTIC_MOCK",
        "TIINGO_CANDIDATE_READ_ONLY",
        "MOCK_PROOF_COMPLETE",
        "EXTERNAL_SAMPLE_QUALIFIED",
        "BLOCKED",
        "NOT research_data_eligible",
        "NOT strategy_promotion_authorized",
        "NOT strategy_execution_eligible",
        "NOT execution_authorized",
        "NOT order_submission_authorized",
        "live_path_absent",
        "no_personalized_investment_advice",
        "no_real_performance_claimed",
    ):
        assert required in migration
    assert "NOT (source_kind = 'DETERMINISTIC_MOCK'" in migration
    assert "AND outcome = 'EXTERNAL_SAMPLE_QUALIFIED')" in migration


def test_phase13_owns_timestamps_locks_and_every_mutation_guard() -> None:
    migration = source()
    for name in FUNCTIONS:
        assert f"CREATE FUNCTION {name}()" in migration
    assert "NEW.created_at_utc := clock_timestamp()" in migration
    assert "pg_advisory_xact_lock" in migration
    assert "phase13-qualification-workflow:" in migration
    assert "Phase 13 point-in-time qualification artifacts are append-only" in migration
    assert "BEFORE UPDATE OR DELETE" in migration
    assert "BEFORE TRUNCATE" in migration
    assert "FOR EACH STATEMENT" in migration


def test_phase13_persistence_contains_no_secret_body_research_or_order_storage() -> None:
    lowered = f"{source()}\n{repository_source()}".lower()
    for forbidden in (
        "api_token",
        "authorization_header",
        "raw_body_bytes",
        "raw_provider_body",
        "raw_price",
        "issuer_statement_value",
        "order_side",
        "order_quantity",
        "fill_price",
        "research_data_snapshot",
    ):
        assert forbidden not in lowered


def test_phase13_repository_serializes_before_lookup_and_revalidates_children() -> None:
    repository = repository_source()
    for required in (
        "class PointInTimeQualificationRepository",
        "class PointInTimeQualificationNotFound",
        "class PointInTimeQualificationRepositoryConflict",
        "def serialized_creation",
        "def find_by_idempotency_key",
        "def create_qualification",
        "def get_qualification",
        "qualification idempotency key is bound to a different request fingerprint",
        "qualification request fingerprint is bound to another idempotency key",
    ):
        assert required in repository
    serialized = repository.split("def serialized_creation", 1)[1].split(
        "def create_qualification", 1
    )[0]
    assert serialized.index("_workflow_lock_identity(key)") < serialized.index("yield")


def test_phase13_downgrade_removes_only_phase13_objects() -> None:
    downgrade = ast.get_source_segment(source(), function_node("downgrade"))
    assert downgrade is not None
    assert "for table in reversed(PHASE13_TABLES)" in downgrade
    assert "drop_column" not in downgrade
    for inherited in (
        "paper_shadow_readiness",
        "paper_simulation",
        "approval_",
        "research_pipeline",
        "evaluation_",
        "data_snapshot",
    ):
        assert inherited not in downgrade
