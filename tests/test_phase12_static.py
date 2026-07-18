from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import re
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
BASELINE_SHA = "b8657abe34d3290a42cb92cb1ad751d0d9d73ad5"
BASELINE_TREE = "b6f57d6448dea70911f6f80695100ae53c6b6513"
READINESS_PATH = "/v1/paper-shadow-readiness/{readiness_assessment_id}"
OUTCOMES = {"MOCK_PROOF_COMPLETE", "SHADOW_READY", "BLOCKED"}
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


def verifier_module() -> ModuleType:
    path = ROOT / "scripts/verify_phase1.py"
    spec = importlib.util.spec_from_file_location("phase12_verifier", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_phase12_baseline_parser_and_exact_allowlist_are_frozen() -> None:
    verifier = verifier_module()
    assert verifier.PHASE_12_BASELINE_SHA == BASELINE_SHA
    assert verifier.EXPECTED_PHASE_12_BASELINE_TREE == BASELINE_TREE
    assert verifier.PHASE_12_READINESS_PATH == READINESS_PATH
    assert verifier.PHASE_12_OUTCOMES == OUTCOMES
    assert verifier.PHASE_12_CHECK_CODES == CHECK_CODES
    assert verifier.FORBIDDEN_EXECUTABLE_PATTERNS.search("/v2/orders") is not None
    assert [verifier.phase_number(str(phase)) for phase in range(1, 16)] == list(range(1, 16))
    for invalid in ("0", "16", "not-a-phase"):
        with pytest.raises(argparse.ArgumentTypeError):
            verifier.phase_number(invalid)

    expected_allowed_writes = {
        ".github/workflows/ci.yml",
        "Makefile",
        "README.md",
        "docs/COMPLIANCE_NOTES.md",
        "docs/DATA_SOURCES.md",
        "docs/IMPLEMENTATION_PLAN.md",
        "docs/PHASE_12_EXTERNAL_PAPER_SHADOW_READINESS_DECISIONS.md",
        "docs/RISK_POLICY.md",
        "docs/handoffs/PHASE_12.md",
        "packages/contracts/openapi.json",
        "packages/contracts/src/api.generated.ts",
        "packages/contracts/src/phase12-contract.type-test.ts",
        "packages/contracts/src/runtime.generated.ts",
        "scripts/capture_paper_shadow_readiness.py",
        "scripts/check.ps1",
        "scripts/check.sh",
        "scripts/verify_phase1.py",
        "services/api/migrations/versions/0009_phase12_external_paper_shadow_readiness.py",
        "services/api/src/fable5_api/main.py",
        "services/api/src/fable5_api/paper_shadow_readiness.py",
        "services/api/tests/test_phase12_openapi_contract.py",
        "services/api/tests/test_phase12_routes.py",
        "services/frontend/e2e/phase8.accessibility.spec.ts",
        "services/frontend/e2e/phase8.visual.spec.ts",
        "services/paper/README.md",
        "services/paper/src/fable5_paper/phase12/__init__.py",
        "services/paper/src/fable5_paper/phase12/adapters.py",
        "services/paper/src/fable5_paper/phase12/alpaca.py",
        "services/paper/src/fable5_paper/phase12/canonical.py",
        "services/paper/src/fable5_paper/phase12/contracts.py",
        "services/paper/src/fable5_paper/phase12/repository.py",
        "services/paper/src/fable5_paper/phase12/settings.py",
        "services/paper/src/fable5_paper/phase12/workflow.py",
        "services/paper/tests/test_phase12_adapters.py",
        "services/paper/tests/test_phase12_postgres.py",
        "services/paper/tests/test_phase12_security.py",
        "services/paper/tests/test_phase12_workflow.py",
        "tests/test_phase10_static.py",
        "tests/test_phase11_static.py",
        "tests/test_phase12_migration.py",
        "tests/test_phase12_static.py",
        "tests/test_phase5_postgres.py",
        "tests/test_phase9_static.py",
        "tests/test_repository_policy.py",
    }
    assert verifier.PHASE_12_ALLOWED_WRITES == expected_allowed_writes


def test_phase12_openapi_and_generated_contract_are_get_only_and_exact() -> None:
    schema = json.loads((ROOT / "packages/contracts/openapi.json").read_text(encoding="utf-8"))
    path_item = schema["paths"][READINESS_PATH]
    assert set(path_item) & {"get", "post", "put", "patch", "delete"} == {"get"}
    operation = path_item["get"]
    assert "requestBody" not in operation
    assert len(operation["parameters"]) == 1
    parameter = operation["parameters"][0]
    assert parameter["name"] == "readiness_assessment_id"
    assert parameter["in"] == "path"
    assert parameter["required"] is True
    assert parameter["schema"]["type"] == "string"
    assert parameter["schema"]["format"] == "uuid"
    assert set(operation["responses"]) == {"200", "404", "409", "422"}

    artifact = schema["components"]["schemas"]["PaperShadowReadinessArtifact"]
    properties = artifact["properties"]
    assert artifact["additionalProperties"] is False
    assert set(artifact["required"]) == set(properties)
    outcome_name = properties["outcome"]["$ref"].rsplit("/", 1)[-1]
    assert set(schema["components"]["schemas"][outcome_name]["enum"]) == OUTCOMES
    for field, literal in {
        "order_submission_authorized": False,
        "strategy_execution_eligible": False,
        "live_path_absent": True,
        "no_personalized_investment_advice": True,
        "no_real_performance_claimed": True,
    }.items():
        assert properties[field]["const"] is literal

    generated = normalized(ROOT / "packages/contracts/src/api.generated.ts")
    runtime = normalized(ROOT / "packages/contracts/src/runtime.generated.ts")
    type_test = normalized(ROOT / "packages/contracts/src/phase12-contract.type-test.ts")
    for required in ("PaperShadowReadinessArtifact:", f'"{READINESS_PATH}"'):
        assert required in generated
    assert "PaperShadowReadinessArtifact" in runtime
    assert READINESS_PATH in runtime
    for required in ("@ts-expect-error", "NoPost", "NoPut", "NoPatch", "NoDelete"):
        assert required in type_test


def test_phase12_adapter_is_read_only_fixed_and_has_no_live_or_vendor_path() -> None:
    phase12_root = ROOT / "services/paper/src/fable5_paper/phase12"
    adapters = normalized(phase12_root / "adapters.py")
    canonical = normalized(phase12_root / "canonical.py")
    alpaca_path = phase12_root / "alpaca.py"
    alpaca = normalized(alpaca_path)
    for method in (
        "inspect_account",
        "inspect_clock",
        "inspect_instrument",
        "inspect_positions",
        "inspect_open_orders",
        "inspect_latest_quote",
    ):
        assert method in adapters
        assert method in alpaca
    for target in verifier_module().PHASE_12_FIXED_GET_TARGETS:
        host, path = target.removeprefix("https://").split("/", 1)
        assert host in canonical
        assert canonical.count(f'"/{path}"') == 1
    assert canonical.count('"method": "GET"') == 6
    assert canonical.count('"port": 443') == 6
    assert not (
        imported_roots(alpaca_path)
        & {"alpaca", "alpaca_py", "alpaca_trade_api", "ccxt", "ib_insync", "ibapi"}
    )
    production = "\n".join(normalized(path) for path in sorted(phase12_root.glob("*.py")))
    assert re.search(r"(?<!paper-)api\.alpaca\.markets", production, re.IGNORECASE) is None
    for forbidden in (
        "submit_order",
        "place_order",
        "create_order",
        "replace_order",
        "cancel_order",
        "close_position",
        "liquidate",
        "websocket",
        "base_url",
        "urljoin",
    ):
        assert forbidden not in production.casefold()


def test_phase12_credentials_cli_and_security_are_fail_closed() -> None:
    phase12_root = ROOT / "services/paper/src/fable5_paper/phase12"
    settings = normalized(phase12_root / "settings.py")
    assert "SecretStr" in settings
    assert 'env_prefix="FABLE5_ALPACA_PAPER_"' in settings
    assert "api_key_id: SecretStr" in settings
    assert "secret_key: SecretStr" in settings

    cli = normalized(ROOT / "scripts/capture_paper_shadow_readiness.py")
    assert "--idempotency-key" in cli
    assert "--confirm-paper-only-readiness" in cli
    for forbidden in (
        "--url",
        "--symbol",
        "--account",
        "--strategy",
        "--side",
        "--quantity",
        "--allocation",
        "--price",
        "--credential",
        "--retry",
        "--submission",
        "--cancellation",
        "--provider",
    ):
        assert forbidden not in cli

    security_tests = normalized(ROOT / "services/paper/tests/test_phase12_security.py")
    for required in (
        "socket",
        "FABLE5_ALPACA_PAPER_API_KEY_ID",
        "FABLE5_ALPACA_PAPER_SECRET_KEY",
        "canary",
    ):
        assert required.casefold() in security_tests.casefold()

    api = normalized(ROOT / "services/api/src/fable5_api/paper_shadow_readiness.py")
    assert "Alpaca" not in api
    assert "PaperBrokerAdapter" not in api
    assert "create_readiness" not in api


def test_phase12_ci_full_verifier_and_cleanup_are_bound() -> None:
    workflow = normalized(ROOT / ".github/workflows/ci.yml")
    assert workflow.startswith("name: phase-15-ci\n")
    assert 'FABLE5_VERIFY_PHASE: "15"' in workflow
    assert 'FABLE5_ALPACA_PAPER_API_KEY_ID: ""' in workflow
    assert 'FABLE5_ALPACA_PAPER_SECRET_KEY: ""' in workflow
    assert "secrets." not in workflow
    assert "phase15-compose:" in workflow
    assert "timeout-minutes: 180" in workflow
    assert workflow.count("python scripts/verify_phase1.py --phase 15") == 1
    assert workflow.count("python scripts/verify_phase1.py --static-only --phase 15") == 1
    assert "FABLE5_UPDATE_SNAPSHOTS" not in workflow
    assert "run_phase_gate.py run --phase 12" not in workflow

    verifier = normalized(ROOT / "scripts/verify_phase1.py")
    for required in (
        "verify_phase12_migration_cycle(",
        "verify_phase12_mock_network_denial(",
        "verify_phase12_capture_cli(",
        "verify_phase12_api(",
        "verify_phase12_postgres_acceptance(",
        "verify_phase12_append_only(",
        'verify_phase10_acceptance_resource_namespace(\n            "preflight"',
        'verify_phase10_acceptance_resource_namespace(\n                        "post-cleanup"',
        "verify_phase9_compose_cleanup(project, environment, phase=phase)",
        'print("Full Compose Phase 12 verification passed.")',
    ):
        assert required in verifier
    assert "if phase in {8, 9, 10, 11, 12, 13, 14, 15}:" in verifier
    assert "if phase in {10, 11, 12, 13, 14, 15}:" in verifier
    assert "if phase in {11, 12, 13, 14, 15}:" in verifier
    assert 'default=os.environ.get("FABLE5_VERIFY_PHASE", "15")' in verifier

    for path in (
        ROOT / "services/frontend/e2e/phase8.accessibility.spec.ts",
        ROOT / "services/frontend/e2e/phase8.visual.spec.ts",
    ):
        source = normalized(path)
        assert 'process.env.FABLE5_VERIFY_PHASE ?? "15"' in source
        assert 'new Set(["10", "11", "12", "13", "14", "15"])' in source
        assert "inheritedModes" in source
