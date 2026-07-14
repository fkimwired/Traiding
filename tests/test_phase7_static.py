from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FROZEN_MIGRATIONS = {
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


def normalized(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")


def imported_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", 1)[0])
    return roots


def test_phase7_preserves_all_earlier_migrations_byte_for_byte() -> None:
    migration_root = ROOT / "services/api/migrations/versions"
    for filename, expected in FROZEN_MIGRATIONS.items():
        assert hashlib.sha256((migration_root / filename).read_bytes()).hexdigest() == expected


def test_phase7_migration_is_additive_reversible_and_append_only() -> None:
    migration = normalized(ROOT / "services/api/migrations/versions/0007_phase7_approval_risk.py")
    assert 'revision: str = "0007_phase7"' in migration
    assert 'down_revision: str | None = "0006_phase6"' in migration
    for table in PHASE7_TABLES:
        assert table in migration
    for evidence in (
        "CREATE FUNCTION reject_phase7_approval_mutation()",
        "CREATE TRIGGER {table}_immutable",
        "CREATE TRIGGER {table}_no_truncate",
        "Phase 7 approval and risk artifacts are append-only",
        "DEFERRABLE INITIALLY DEFERRED",
    ):
        assert evidence in migration


def test_phase7_workflow_uses_promotion_state_not_configuration_tokens() -> None:
    workflow = normalized(ROOT / "services/risk/src/fable5_risk/workflow.py")
    assert "PromotionState.PASS_RESEARCH" in workflow
    assert "phase6-a-pass-v2" not in workflow
    assert "-pass-" not in workflow
    assert "ApprovalCheckCode.RESEARCH_PASS" in workflow


def test_phase7_domain_has_no_vendor_network_or_executable_dependency() -> None:
    forbidden_imports = {
        "aiohttp",
        "alpaca",
        "alpaca_py",
        "alpaca_trade_api",
        "ccxt",
        "httpx",
        "ib_insync",
        "ibapi",
        "requests",
        "socket",
        "urllib3",
    }
    risk_root = ROOT / "services/risk/src/fable5_risk"
    for path in risk_root.rglob("*.py"):
        assert not (imported_roots(path) & forbidden_imports)
    dependencies = normalized(ROOT / "pyproject.toml").casefold()
    for dependency in ("alpaca-py", "ib_insync", "ibapi", "ccxt"):
        assert dependency not in dependencies


def test_phase7_contract_safety_flags_are_literal_and_llm_boundary_is_unchanged() -> None:
    contracts = normalized(ROOT / "services/risk/src/fable5_risk/contracts.py")
    for invariant in (
        "class ApprovalAssessmentOutcome(StrEnum):",
        'APPROVED_PAPER = "APPROVED_PAPER"',
        'FAIL_REJECT = "FAIL_REJECT"',
        "synthetic: Literal[True]",
        "simulated_paper_only: Literal[True]",
        "execution_authorized: Literal[False]",
        "execution_ready: Literal[False]",
        "no_personalized_investment_advice: Literal[True]",
        "no_real_performance_claimed: Literal[True]",
    ):
        assert invariant in contracts
    phase6_extraction = normalized(ROOT / "services/research/src/fable5_research/contracts.py")
    assert "structured_features_only" in phase6_extraction
    for forbidden_field in (
        "buy_sell_call",
        "position_size",
        "risk_override",
        "execution_instruction",
    ):
        assert forbidden_field not in contracts
        assert forbidden_field not in phase6_extraction


def test_phase7_openapi_is_exact_create_read_list_and_non_executable() -> None:
    schema = json.loads((ROOT / "packages/contracts/openapi.json").read_text(encoding="utf-8"))
    phase7_methods = {"get", "post", "put", "patch", "delete"}
    phase7_path_terms = (
        "approval",
        "authorization",
        "revocation",
        "risk",
        "governance",
        "pre-order",
        "pre_order",
    )
    expected_phase7_paths = {
        "/v1/approval-assessments": {"get", "post"},
        "/v1/approval-assessments/{assessment_id}": {"get"},
        "/v1/approval-revocations": {"get", "post"},
        "/v1/approval-revocations/{revocation_id}": {"get"},
    }
    phase7_paths: dict[str, set[str]] = {}
    for path, operations in schema["paths"].items():
        methods = set(operations) & phase7_methods
        tags = {
            tag
            for method, operation in operations.items()
            if method in phase7_methods and isinstance(operation, dict)
            for tag in operation.get("tags", [])
        }
        if (
            path in expected_phase7_paths
            or "approval-governance" in tags
            or any(term in path.casefold() for term in phase7_path_terms)
        ):
            phase7_paths[path] = methods
    assert phase7_paths == expected_phase7_paths
    for path, operations in schema["paths"].items():
        methods = set(operations) & phase7_methods
        assert methods <= {"get", "post"}
        if path.startswith("/v1/"):
            assert not any(
                token in path.casefold()
                for token in ("broker", "fill", "position", "orders", "execution", "live")
            )


def test_phase7_does_not_relabel_or_mutate_phase5_or_phase6_domains() -> None:
    for path in (
        ROOT / "services/backtester/src/fable5_backtester/contracts.py",
        ROOT / "services/research/src/fable5_research/contracts.py",
        ROOT / "services/api/migrations/versions/0006_phase6_research.py",
    ):
        assert "APPROVED_PAPER" not in path.read_text(encoding="utf-8")
