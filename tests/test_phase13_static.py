from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest
from fable5_data.phase13.canonical import PHASE13_FIXED_ENDPOINTS

ROOT = Path(__file__).resolve().parents[1]
BASELINE_SHA = "37530a94f841d538a162447cb01ec3e11f375ead"
BASELINE_TREE = "d8d747ffccb76c3d754cdd2cc14b8ec49fb97287"
QUALIFICATION_PATH = "/v1/point-in-time-data-qualifications/{qualification_id}"
CAPABILITIES = (
    "SECURITY_MASTER_STABLE_IDENTITY",
    "POINT_IN_TIME_UNIVERSE_MEMBERSHIP",
    "RAW_OHLCV_AVAILABILITY",
    "CORPORATE_ACTION_ANNOUNCEMENT_REVISION",
    "DELISTING_RETURN_SEMANTICS",
    "AS_REPORTED_FUNDAMENTAL_REVISION",
)
CHECKS = (
    "SOURCE_KIND_EXACT",
    "READ_ONLY_TRANSPORT_EXACT",
    "USE_RIGHTS_CURRENT_SUFFICIENT",
    *CAPABILITIES,
    "RAW_NORMALIZED_RECONCILIATION",
    "NULL_SENTINEL_SCHEMA_DRIFT",
    "DETERMINISTIC_CAPTURE_MANIFEST",
)


def normalized(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")


def verifier_module() -> ModuleType:
    path = ROOT / "scripts/verify_phase1.py"
    spec = importlib.util.spec_from_file_location("phase13_verifier", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_phase13_baseline_parser_registries_and_exact_allowlist_are_frozen() -> None:
    verifier = verifier_module()
    assert verifier.PHASE_13_BASELINE_SHA == BASELINE_SHA
    assert verifier.EXPECTED_PHASE_13_BASELINE_TREE == BASELINE_TREE
    assert verifier.PHASE_13_QUALIFICATION_PATH == QUALIFICATION_PATH
    assert verifier.PHASE_13_SOURCE_KINDS == {
        "DETERMINISTIC_MOCK",
        "TIINGO_CANDIDATE_READ_ONLY",
    }
    assert verifier.PHASE_13_OUTCOMES == {
        "MOCK_PROOF_COMPLETE",
        "EXTERNAL_SAMPLE_QUALIFIED",
        "BLOCKED",
    }
    assert verifier.PHASE_13_ARTIFACT_SCHEMA_VERSION == "phase13-pit-qualification-v1"
    assert verifier.PHASE_13_CAPABILITY_SCHEMA_VERSION == ("phase13-pit-capability-manifest-v1")
    assert verifier.PHASE_13_CHECK_SCHEMA_VERSION == "phase13-pit-qualification-check-v1"
    assert verifier.PHASE_13_CAPABILITIES == CAPABILITIES
    assert verifier.PHASE_13_CHECK_CODES == CHECKS
    assert [verifier.phase_number(str(phase)) for phase in range(1, 23)] == list(range(1, 23))
    for invalid in ("0", "23", "not-a-phase"):
        with pytest.raises(argparse.ArgumentTypeError):
            verifier.phase_number(invalid)

    assert verifier.PHASE_13_ALLOWED_WRITES == {
        ".github/workflows/ci.yml",
        "Makefile",
        "README.md",
        "docs/COMPLIANCE_NOTES.md",
        "docs/DATA_SOURCES.md",
        "docs/IMPLEMENTATION_PLAN.md",
        "docs/PHASE_13_POINT_IN_TIME_DATA_QUALIFICATION_DECISIONS.md",
        "docs/RISK_POLICY.md",
        "docs/handoffs/PHASE_13.md",
        "packages/contracts/openapi.json",
        "packages/contracts/src/api.generated.ts",
        "packages/contracts/src/phase13-contract.type-test.ts",
        "packages/contracts/src/runtime.generated.ts",
        "scripts/capture_point_in_time_data_qualification.py",
        "scripts/check.ps1",
        "scripts/check.sh",
        "scripts/verify_phase1.py",
        "services/api/migrations/versions/0010_phase13_point_in_time_data_qualification.py",
        "services/api/src/fable5_api/data_qualifications.py",
        "services/api/src/fable5_api/main.py",
        "services/api/tests/test_phase13_openapi_contract.py",
        "services/api/tests/test_phase13_routes.py",
        "services/data/src/fable5_data/phase13/__init__.py",
        "services/data/src/fable5_data/phase13/adapters.py",
        "services/data/src/fable5_data/phase13/canonical.py",
        "services/data/src/fable5_data/phase13/contracts.py",
        "services/data/src/fable5_data/phase13/repository.py",
        "services/data/src/fable5_data/phase13/settings.py",
        "services/data/src/fable5_data/phase13/tiingo.py",
        "services/data/src/fable5_data/phase13/workflow.py",
        "services/data/tests/test_phase13_adapters.py",
        "services/data/tests/test_phase13_contracts.py",
        "services/data/tests/test_phase13_postgres.py",
        "services/data/tests/test_phase13_security.py",
        "services/data/tests/test_phase13_workflow.py",
        "services/frontend/e2e/phase8.accessibility.spec.ts",
        "services/frontend/e2e/phase8.visual.spec.ts",
        "tests/test_phase10_static.py",
        "tests/test_phase11_static.py",
        "tests/test_phase12_static.py",
        "tests/test_phase13_migration.py",
        "tests/test_phase13_static.py",
        "tests/test_phase5_postgres.py",
        "tests/test_phase9_static.py",
        "tests/test_repository_policy.py",
    }


def test_phase13_generated_contract_is_exactly_one_historical_get() -> None:
    schema = json.loads((ROOT / "packages/contracts/openapi.json").read_text(encoding="utf-8"))
    path_item = schema["paths"][QUALIFICATION_PATH]
    assert set(path_item) & {"get", "post", "put", "patch", "delete"} == {"get"}
    operation = path_item["get"]
    assert "requestBody" not in operation
    assert operation["parameters"] == [
        {
            "in": "path",
            "name": "qualification_id",
            "required": True,
            "schema": {
                "format": "uuid",
                "title": "Qualification Id",
                "type": "string",
            },
        }
    ]
    assert set(operation["responses"]) == {"200", "404", "409", "422"}
    rendered = json.dumps(schema["components"]["schemas"], sort_keys=True)
    for required in (*CAPABILITIES, *CHECKS, "PointInTimeQualificationArtifact"):
        assert required in rendered
    for field, value in (
        ("research_data_eligible", False),
        ("strategy_promotion_authorized", False),
        ("strategy_execution_eligible", False),
        ("execution_authorized", False),
        ("order_submission_authorized", False),
        ("live_path_absent", True),
        ("no_personalized_investment_advice", True),
        ("no_real_performance_claimed", True),
    ):
        assert f'"{field}"' in rendered
        assert (
            schema["components"]["schemas"]["PointInTimeQualificationArtifact"]["properties"][
                field
            ]["const"]
            is value
        )

    generated = normalized(ROOT / "packages/contracts/src/api.generated.ts")
    runtime = normalized(ROOT / "packages/contracts/src/runtime.generated.ts")
    type_test = normalized(ROOT / "packages/contracts/src/phase13-contract.type-test.ts")
    for source in (generated, runtime):
        assert QUALIFICATION_PATH in source
        assert "PointInTimeQualificationArtifact" in source
    for proof in ("NoPost", "NoPut", "NoPatch", "NoDelete", "@ts-expect-error"):
        assert proof in type_test


def test_phase13_transport_cli_and_security_boundary_are_fixed() -> None:
    verifier = verifier_module()
    assert (
        tuple(
            f"https://{endpoint['host']}{endpoint['target']}"
            for endpoint in PHASE13_FIXED_ENDPOINTS
        )
        == verifier.PHASE_13_FIXED_GET_TARGETS
    )
    assert {endpoint["method"] for endpoint in PHASE13_FIXED_ENDPOINTS} == {"GET"}
    assert {endpoint["host"] for endpoint in PHASE13_FIXED_ENDPOINTS} == {"api.tiingo.com"}
    assert {endpoint["port"] for endpoint in PHASE13_FIXED_ENDPOINTS} == {443}

    production = "\n".join(
        normalized(path)
        for path in sorted((ROOT / "services/data/src/fable5_data/phase13").glob("*.py"))
    ).casefold()
    for forbidden in (
        "submit_order",
        "place_order",
        "create_order",
        "base_url",
        "urljoin",
        "websocket",
        "alpaca",
    ):
        assert forbidden not in production

    cli = normalized(ROOT / "scripts/capture_point_in_time_data_qualification.py")
    assert "--idempotency-key" in cli
    assert "--confirm-read-only-qualification" in cli
    for forbidden in (
        "--provider",
        "--url",
        "--symbol",
        "--date",
        "--capability",
        "--credential",
        "--rights",
        "--strategy",
        "--action",
        "--side",
        "--quantity",
        "--price",
        "--allocation",
        "--retry",
        "--broker",
        "--execution",
    ):
        assert forbidden not in cli


def test_phase13_ci_full_verifier_inherited_browser_and_cleanup_are_bound() -> None:
    verifier = normalized(ROOT / "scripts/verify_phase1.py")
    for required in (
        "verify_phase13_migration_cycle(",
        "verify_phase13_mock_network_denial(",
        "verify_phase13_capture_cli(",
        "verify_phase13_api(",
        "verify_phase13_postgres_acceptance(",
        "verify_phase13_append_only(",
        'print("Full Compose Phase 13 verification passed.")',
        "if phase in {",
        "if phase in {10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22}:",
        "if phase in {11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22}:",
        'default=os.environ.get("FABLE5_VERIFY_PHASE", "22")',
    ):
        assert required in verifier

    workflow = normalized(ROOT / ".github/workflows/ci.yml")
    assert workflow.startswith("name: phase-22-ci\n")
    assert 'FABLE5_VERIFY_PHASE: "22"' in workflow
    assert "phase22-compose:" in workflow
    assert workflow.count("python scripts/verify_phase1.py --phase 22") == 1
    assert workflow.count("python scripts/verify_phase1.py --static-only --phase 22") == 1
    assert "secrets." not in workflow
    for environment_name in verifier_module().PHASE_13_CREDENTIAL_ENV_NAMES:
        assert f'{environment_name}: ""' in workflow

    for path in (
        ROOT / "services/frontend/e2e/phase8.accessibility.spec.ts",
        ROOT / "services/frontend/e2e/phase8.visual.spec.ts",
    ):
        source = normalized(path)
        assert 'process.env.FABLE5_VERIFY_PHASE ?? "22"' in source
        assert '"20",\n  "21",\n  "22",' in source
