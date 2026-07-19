from __future__ import annotations

import argparse
import ast
import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest
from fable5_data.phase14.canonical import PHASE14_POLICY_ID
from fable5_data.phase14.contracts import (
    PHASE14_ARTIFACT_SCHEMA_VERSION,
    PHASE14_CHECK_ORDER,
    PHASE14_CHECK_SCHEMA_VERSION,
    PHASE14_PAYLOAD_SCHEMA_VERSION,
)

ROOT = Path(__file__).resolve().parents[1]
BASELINE_SHA = "47e8e6a9c878a3a8ca7a4b22be3e23ab0357716f"
BASELINE_TREE = "d4ac6b6f4b6ba28f5359d8ea85c35845bdb9f285"
ELIGIBILITY_PATH = "/v1/research-ingestion-eligibility/{assessment_id}"
CHECKS = (
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


def normalized(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")


def verifier_module() -> ModuleType:
    path = ROOT / "scripts/verify_phase1.py"
    spec = importlib.util.spec_from_file_location("phase14_verifier", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_phase14_baseline_parser_registries_and_exact_allowlist_are_frozen() -> None:
    verifier = verifier_module()
    assert verifier.PHASE_14_BASELINE_SHA == BASELINE_SHA
    assert verifier.EXPECTED_PHASE_14_BASELINE_TREE == BASELINE_TREE
    assert verifier.PHASE_14_ELIGIBILITY_PATH == ELIGIBILITY_PATH
    assert verifier.PHASE_14_OUTCOMES == {"MOCK_PROOF_COMPLETE", "BLOCKED"}
    assert verifier.PHASE_14_STATUSES == {"PASS", "BLOCKED", "UNCOMPUTABLE"}
    assert verifier.PHASE_14_CHECK_CODES == CHECKS
    assert tuple(item.value for item in PHASE14_CHECK_ORDER) == CHECKS
    assert verifier.PHASE_14_ARTIFACT_SCHEMA_VERSION == PHASE14_ARTIFACT_SCHEMA_VERSION
    assert verifier.PHASE_14_PAYLOAD_SCHEMA_VERSION == PHASE14_PAYLOAD_SCHEMA_VERSION
    assert verifier.PHASE_14_CHECK_SCHEMA_VERSION == PHASE14_CHECK_SCHEMA_VERSION
    assert verifier.PHASE_14_POLICY_ID == PHASE14_POLICY_ID
    assert [verifier.phase_number(str(phase)) for phase in range(1, 18)] == list(range(1, 18))
    for invalid in ("0", "18", "not-a-phase"):
        with pytest.raises(argparse.ArgumentTypeError):
            verifier.phase_number(invalid)

    assert verifier.PHASE_14_ALLOWED_WRITES == {
        ".github/workflows/ci.yml",
        "Makefile",
        "README.md",
        "docs/COMPLIANCE_NOTES.md",
        "docs/DATA_SOURCES.md",
        "docs/IMPLEMENTATION_PLAN.md",
        "docs/PHASE_14_RESEARCH_INGESTION_ELIGIBILITY_DECISIONS.md",
        "docs/RISK_POLICY.md",
        "docs/handoffs/PHASE_14.md",
        "packages/contracts/openapi.json",
        "packages/contracts/src/api.generated.ts",
        "packages/contracts/src/phase14-contract.type-test.ts",
        "packages/contracts/src/runtime.generated.ts",
        "scripts/assess_research_ingestion_eligibility.py",
        "scripts/check.ps1",
        "scripts/check.sh",
        "scripts/verify_phase1.py",
        "services/api/migrations/versions/0011_phase14_research_ingestion_eligibility.py",
        "services/api/src/fable5_api/main.py",
        "services/api/src/fable5_api/research_ingestion_eligibility.py",
        "services/api/tests/test_phase14_openapi_contract.py",
        "services/api/tests/test_phase14_routes.py",
        "services/data/src/fable5_data/phase14/__init__.py",
        "services/data/src/fable5_data/phase14/canonical.py",
        "services/data/src/fable5_data/phase14/contracts.py",
        "services/data/src/fable5_data/phase14/repository.py",
        "services/data/src/fable5_data/phase14/workflow.py",
        "services/data/tests/test_phase14_contracts.py",
        "services/data/tests/test_phase14_postgres.py",
        "services/data/tests/test_phase14_security.py",
        "services/data/tests/test_phase14_workflow.py",
        "services/frontend/e2e/phase8.accessibility.spec.ts",
        "services/frontend/e2e/phase8.visual.spec.ts",
        "tests/test_phase10_static.py",
        "tests/test_phase11_static.py",
        "tests/test_phase12_static.py",
        "tests/test_phase13_static.py",
        "tests/test_phase14_migration.py",
        "tests/test_phase14_static.py",
        "tests/test_phase5_postgres.py",
        "tests/test_phase9_static.py",
        "tests/test_repository_policy.py",
    }


def test_phase14_generated_contract_is_exactly_one_historical_get() -> None:
    schema = json.loads((ROOT / "packages/contracts/openapi.json").read_text(encoding="utf-8"))
    path_item = schema["paths"][ELIGIBILITY_PATH]
    assert set(path_item) & {"get", "post", "put", "patch", "delete"} == {"get"}
    operation = path_item["get"]
    assert "requestBody" not in operation
    assert operation["parameters"] == [
        {
            "in": "path",
            "name": "assessment_id",
            "required": True,
            "schema": {
                "format": "uuid",
                "title": "Assessment Id",
                "type": "string",
            },
        }
    ]
    assert set(operation["responses"]) == {"200", "404", "409", "422"}
    components = schema["components"]["schemas"]
    artifact = components["ResearchIngestionEligibilityArtifact"]
    properties = artifact["properties"]
    outcome_name = properties["outcome"]["$ref"].rsplit("/", 1)[-1]
    assert components[outcome_name]["enum"] == ["MOCK_PROOF_COMPLETE", "BLOCKED"]
    rendered = json.dumps(components, sort_keys=True)
    for required in (*CHECKS, PHASE14_POLICY_ID, "ResearchIngestionEligibilityArtifact"):
        assert required in rendered
    for field in (
        "external_request_performed",
        "provider_payload_persisted",
        "research_ingestion_authorized",
        "research_snapshot_created",
        "research_data_eligible",
        "research_run_created",
        "research_run_authorized",
        "research_executed",
        "performance_computed",
        "pass_research_granted",
        "strategy_promotion_authorized",
        "paper_approval_granted",
        "strategy_execution_eligible",
        "execution_authorized",
        "order_submission_authorized",
    ):
        assert properties[field]["const"] is False
    for field in (
        "live_path_absent",
        "no_personalized_investment_advice",
        "no_real_performance_claimed",
    ):
        assert properties[field]["const"] is True

    generated = normalized(ROOT / "packages/contracts/src/api.generated.ts")
    runtime = normalized(ROOT / "packages/contracts/src/runtime.generated.ts")
    type_test = normalized(ROOT / "packages/contracts/src/phase14-contract.type-test.ts")
    for source in (generated, runtime):
        assert ELIGIBILITY_PATH in source
        assert "ResearchIngestionEligibilityArtifact" in source
    for proof in ("NoPost", "NoPut", "NoPatch", "NoDelete", "@ts-expect-error"):
        assert proof in type_test


def test_phase14_domain_and_cli_are_database_only_and_authority_closed() -> None:
    phase14_root = ROOT / "services/data/src/fable5_data/phase14"
    forbidden_imports = {
        "aiohttp",
        "alpaca",
        "http",
        "httpx",
        "requests",
        "socket",
        "ssl",
        "urllib",
        "websocket",
        "websockets",
    }
    imported: set[str] = set()
    production = ""
    for path in sorted(phase14_root.glob("*.py")):
        source = normalized(path)
        production += source.casefold()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".", 1)[0])
    assert imported.isdisjoint(forbidden_imports)
    for forbidden in (
        "secretstr",
        "api_token",
        "credential",
        "submit_order",
        "place_order",
        "create_order",
        "base_url",
        "urljoin",
        "websocket",
        "asyncio",
        "retry",
        "fable5_research",
        "fable5_paper",
    ):
        assert forbidden not in production

    cli = normalized(ROOT / "scripts/assess_research_ingestion_eligibility.py")
    for required in (
        "--idempotency-key",
        "--qualification-id",
        "--confirm-research-eligibility-only",
    ):
        assert required in cli
    for forbidden in (
        "--provider",
        "--url",
        "--credential",
        "--rights",
        "--data",
        "--strategy",
        "--signal",
        "--side",
        "--quantity",
        "--price",
        "--allocation",
        "--broker",
        "--order",
        "--retry",
        "--execution",
        "--ingestion",
        "--promotion",
    ):
        assert forbidden not in cli


def test_phase14_ci_full_verifier_inherited_browser_and_cleanup_are_bound() -> None:
    verifier = normalized(ROOT / "scripts/verify_phase1.py")
    for required in (
        "verify_phase14_migration_cycle(",
        "verify_phase14_offline_network_denial(",
        "verify_phase14_assessment_cli(",
        "verify_phase14_api(",
        "verify_phase14_postgres_acceptance(",
        "verify_phase14_append_only(",
        'print("Full Compose Phase 14 verification passed.")',
        "if phase in {8, 9, 10, 11, 12, 13, 14, 15, 16, 17}:",
        "if phase in {10, 11, 12, 13, 14, 15, 16, 17}:",
        "if phase in {11, 12, 13, 14, 15, 16, 17}:",
        "if phase in {12, 13, 14, 15, 16, 17}:",
        "if phase in {13, 14, 15, 16, 17}:",
        'default=os.environ.get("FABLE5_VERIFY_PHASE", "17")',
    ):
        assert required in verifier

    workflow = normalized(ROOT / ".github/workflows/ci.yml")
    assert workflow.startswith("name: phase-17-ci\n")
    assert 'FABLE5_VERIFY_PHASE: "17"' in workflow
    assert "phase17-compose:" in workflow
    assert workflow.count("python scripts/verify_phase1.py --phase 17") == 1
    assert workflow.count("python scripts/verify_phase1.py --static-only --phase 17") == 1
    assert "secrets." not in workflow
    module = verifier_module()
    for environment_name in (
        *module.PHASE_12_CREDENTIAL_ENV_NAMES,
        *module.PHASE_13_CREDENTIAL_ENV_NAMES,
    ):
        assert f'{environment_name}: ""' in workflow

    for path in (
        ROOT / "services/frontend/e2e/phase8.accessibility.spec.ts",
        ROOT / "services/frontend/e2e/phase8.visual.spec.ts",
    ):
        source = normalized(path)
        assert 'process.env.FABLE5_VERIFY_PHASE ?? "17"' in source
        assert 'new Set(["10", "11", "12", "13", "14", "15", "16", "17"])' in source
