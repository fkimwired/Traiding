from __future__ import annotations

import ast
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "services/api/migrations/versions/0011_phase14_research_ingestion_eligibility.py"
REPOSITORY = ROOT / "services/data/src/fable5_data/phase14/repository.py"
PHASE13_MIGRATION = (
    ROOT / "services/api/migrations/versions/0010_phase13_point_in_time_data_qualification.py"
)
PHASE13_SHA256 = "b06c7eaeb92b9b6ce04ec54394f99f285524c7299143cf138839875103911a90"

PHASE14_TABLES = {
    "research_ingestion_eligibility_assessments",
    "research_ingestion_eligibility_payloads",
    "research_ingestion_eligibility_checks",
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
    "QUALIFICATION_IDENTITY_INTEGRITY",
    "QUALIFICATION_SOURCE_KIND_ALLOWED",
    "QUALIFICATION_OUTCOME_ELIGIBLE_OR_MOCK",
    "CAPABILITY_MANIFEST_COMPLETE_PASSING",
    "QUALIFICATION_CHECKS_COMPLETE_PASSING",
    "EXTERNAL_REQUEST_EVIDENCE_COMPLETE_OR_MOCK",
    "INDEPENDENT_RIGHTS_REFERENCE_PRESENT_OR_MOCK",
    "USE_RIGHTS_CURRENT_OR_MOCK",
    "USE_RIGHTS_SCOPE_SUFFICIENT_OR_MOCK",
    "LICENSED_PAYLOAD_ABSENT",
    "RESEARCH_SNAPSHOT_ABSENT",
    "PROMOTION_EXECUTION_AUTHORITY_ABSENT",
)
FUNCTIONS = (
    "own_phase14_created_at_utc",
    "phase14_lock_eligibility_idempotency",
    "validate_phase14_eligibility_root_payload",
    "validate_phase14_eligibility_payload",
    "validate_phase14_eligibility_check_payload",
    "validate_phase14_eligibility_completeness",
    "reject_phase14_eligibility_mutation",
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


def test_phase14_directly_extends_the_accepted_phase13_revision() -> None:
    assert assignment("revision") == "0011_phase14"
    assert assignment("down_revision") == "0010_phase13"
    assert hashlib.sha256(PHASE13_MIGRATION.read_bytes()).hexdigest() == PHASE13_SHA256


def test_phase14_creates_exactly_three_tables_without_seed_rows() -> None:
    assert set(create_table_calls()) == PHASE14_TABLES
    lowered = source().lower()
    assert "bulk_insert" not in lowered
    assert "insert into research_ingestion_eligibility" not in lowered


def test_phase14_freezes_six_payloads_and_twelve_checks() -> None:
    assert assignment("PHASE14_CAPABILITY_CODES") == CAPABILITY_CODES
    assert assignment("PHASE14_CHECK_CODES") == CHECK_CODES
    migration = source()
    assert "DEFERRABLE INITIALLY DEFERRED" in migration
    assert "payload_count <> {len(PHASE14_CAPABILITY_CODES)}" in migration
    assert "check_count <> {len(PHASE14_CHECK_CODES)}" in migration


def test_phase14_composite_lineage_revalidates_the_complete_phase13_source() -> None:
    migration = source()
    assert "point_in_time_qualification_runs.qualification_id" in migration
    assert "point_in_time_qualification_runs.artifact_sha256" in migration
    assert 'ondelete="RESTRICT"' in migration
    assert " CASCADE" not in migration
    for required in (
        "point_in_time_qualification_payloads",
        "point_in_time_qualification_checks",
        "phase13-pit-qualification-artifact-v1",
        "phase13-pit-capability-manifest-v1",
        "phase13-pit-qualification-check-v1",
        "phase13-pit-capture-manifest-v1",
        "phase6_domain_sha256(",
        "phase6_uuid5(",
    ):
        assert required in migration


def test_phase14_has_no_positive_eligibility_or_action_state() -> None:
    migration = source()
    assert "outcome IN ('MOCK_PROOF_COMPLETE','BLOCKED')" in migration
    for required in (
        "NOT external_request_performed",
        "NOT provider_payload_persisted",
        "NOT research_ingestion_authorized",
        "NOT research_snapshot_created",
        "NOT research_data_eligible",
        "NOT research_run_created",
        "NOT research_run_authorized",
        "NOT research_executed",
        "NOT performance_computed",
        "NOT pass_research_granted",
        "NOT strategy_promotion_authorized",
        "NOT paper_approval_granted",
        "NOT strategy_execution_eligible",
        "NOT execution_authorized",
        "NOT order_submission_authorized",
        "live_path_absent",
        "no_personalized_investment_advice",
        "no_real_performance_claimed",
    ):
        assert required in migration
    for forbidden in ("RESEARCH_ELIGIBLE", "PASS_RESEARCH", "APPROVED_PAPER"):
        assert forbidden not in migration


def test_phase14_owns_exactly_seven_functions_and_every_mutation_guard() -> None:
    migration = source()
    for name in FUNCTIONS:
        assert f"CREATE FUNCTION {name}()" in migration
    assert "NEW.created_at_utc := clock_timestamp()" in migration
    assert "pg_advisory_xact_lock" in migration
    assert "phase14-eligibility-workflow:" in migration
    assert "Phase 14 research-ingestion eligibility artifacts are append-only" in migration
    assert "BEFORE UPDATE OR DELETE" in migration
    assert "BEFORE TRUNCATE" in migration
    assert "FOR EACH STATEMENT" in migration


def test_phase14_persistence_contains_no_transport_payload_research_or_order_storage() -> None:
    lowered = f"{source()}\n{repository_source()}".lower()
    for forbidden in (
        "api_token",
        "authorization_header",
        "raw_body_bytes",
        "raw_provider_body",
        "raw_price",
        "issuer_statement_value",
        "research_score",
        "trial_return",
        "order_side",
        "order_quantity",
        "fill_price",
    ):
        assert forbidden not in lowered


def test_phase14_repository_serializes_and_exposes_only_assessment_persistence() -> None:
    repository = repository_source()
    for required in (
        "class ResearchIngestionEligibilityRepository",
        "class ResearchIngestionEligibilityNotFound",
        "class ResearchIngestionEligibilityRepositoryConflict",
        "def serialized_creation",
        "def find_by_idempotency_key",
        "def create_assessment",
        "def get_assessment",
        "assessment idempotency key is bound to a different request fingerprint",
        "assessment request fingerprint is bound to another idempotency key",
    ):
        assert required in repository
    serialized = repository.split("def serialized_creation", 1)[1].split(
        "def create_assessment", 1
    )[0]
    assert serialized.index("_workflow_lock_identity(key)") < serialized.index("yield")


def test_phase14_downgrade_removes_only_phase14_objects() -> None:
    downgrade = ast.get_source_segment(source(), function_node("downgrade"))
    assert downgrade is not None
    assert "for table in reversed(PHASE14_TABLES)" in downgrade
    assert "drop_column" not in downgrade
    for inherited in (
        "point_in_time_qualification",
        "paper_shadow_readiness",
        "paper_simulation",
        "approval_",
        "research_pipeline",
        "evaluation_",
        "data_snapshot",
    ):
        assert inherited not in downgrade
