from __future__ import annotations

import ast
import importlib.util
import json
import subprocess
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]

EXPECTED_PATHS = {
    "/v1/local-simulations": {"get", "post"},
    "/v1/local-simulations/{simulation_run_id}": {"get"},
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
VISUAL_BASELINES = {
    f"phase10-{state}-{project}-{platform}.png"
    for state in ("completed", "blocked")
    for project in ("mobile", "tablet", "desktop")
    for platform in ("win32", "linux")
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


def verifier_module() -> ModuleType:
    path = ROOT / "scripts/verify_phase1.py"
    spec = importlib.util.spec_from_file_location("phase10_verifier", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_phase10_domain_has_no_vendor_or_network_dependency() -> None:
    forbidden = {
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
        "urllib",
        "urllib3",
    }
    for path in (ROOT / "services/paper/src/fable5_paper").rglob("*.py"):
        assert not (imported_roots(path) & forbidden), path
    dependencies = normalized(ROOT / "pyproject.toml").casefold()
    for dependency in ("alpaca-py", "ib_insync", "ibapi", "ccxt"):
        assert dependency not in dependencies


def test_phase10_request_is_reference_only_and_strict() -> None:
    schema = json.loads((ROOT / "packages/contracts/openapi.json").read_text(encoding="utf-8"))
    request = schema["components"]["schemas"]["PaperSimulationCreateRequest"]
    expected = {"approval_assessment_id", "simulation_idempotency_key"}
    assert set(request["properties"]) == expected
    assert set(request["required"]) == expected
    assert request["additionalProperties"] is False


def test_phase10_api_surface_is_exact_and_has_no_action_route() -> None:
    schema = json.loads((ROOT / "packages/contracts/openapi.json").read_text(encoding="utf-8"))
    methods = {"get", "post", "put", "patch", "delete"}
    actual: dict[str, set[str]] = {}
    for path, operations in schema["paths"].items():
        tags = {
            tag
            for method, operation in operations.items()
            if method in methods and isinstance(operation, dict)
            for tag in operation.get("tags", [])
        }
        if path in EXPECTED_PATHS or "paper-simulation" in tags:
            actual[path] = set(operations) & methods
    assert actual == EXPECTED_PATHS
    assert not any(
        token in path.casefold()
        for path in schema["paths"]
        for token in ("broker", "account", "credential", "submit", "cancel", "live")
    )


def test_phase10_contracts_freeze_checks_and_non_execution_literals() -> None:
    contracts = normalized(ROOT / "services/paper/src/fable5_paper/contracts.py")
    for check in CHECK_CODES:
        assert f'{check} = "{check}"' in contracts
    for invariant in (
        "PaperTransitionRevalidationProof",
        "revalidation_proof_sha256",
        "synthetic: Literal[True]",
        "simulated_paper_only: Literal[True]",
        "local_mock_only: Literal[True]",
        "external_submission: Literal[False]",
        "external_routing_absent: Literal[True]",
        "live_path_absent: Literal[True]",
        "no_personalized_investment_advice: Literal[True]",
        "no_real_performance_claimed: Literal[True]",
    ):
        assert invariant in contracts
    for forbidden in ("SELL", "SHORT", "broker_account", "credential", "live_endpoint"):
        assert forbidden not in contracts


def test_phase10_workflow_requires_fresh_phase7_transition_and_all_checks() -> None:
    workflow = normalized(ROOT / "services/paper/src/fable5_paper/workflow.py")
    assert "ApprovalWorkflow(" in workflow
    assert "revalidate_assessment" in workflow
    assert "build_transition_revalidation_proof" in workflow
    assert "all(item.status is PaperCheckStatus.PASS for item in checks)" in workflow
    assert "PaperSimulationOutcome.BLOCKED" in workflow
    assert "build_simulation_ledger" in workflow
    assert "phase10_code_version_git_sha_missing" in workflow


def test_phase10_fixture_is_one_server_owned_synthetic_long_only_rehearsal() -> None:
    fixture = normalized(ROOT / "services/paper/src/fable5_paper/fixtures.py")
    for required in (
        '"phase10-a-local-mock-qa-v1"',
        '"SYNTHETIC-ASSET-001"',
        '"sector-relative-rank-linear-v1"',
        '"phase6-a-score-positive-long-flat-v1"',
        '"signal_state": "LONG"',
        '"simulated_side": "BUY"',
        '"fill_status": "SIMULATED_FILLED"',
        '"external_submission": False',
    ):
        assert required in fixture or required in normalized(
            ROOT / "services/paper/src/fable5_paper/contracts.py"
        )
    for forbidden in ("random.random", "requests.", "httpx.", "socket."):
        assert forbidden not in fixture


def test_phase10_frontend_exposes_no_trade_parameters() -> None:
    workspace = normalized(ROOT / "services/frontend/src/app/paper/PaperStatusWorkspace.tsx")
    for copy in (
        "SIMULATED",
        "LOCAL MOCK",
        "Run deterministic local simulation",
        "no personalized investment advice",
        "no live path",
    ):
        assert copy.casefold() in workspace.casefold()
    for field in ('name="quantity"', 'name="price"', 'name="side"', 'name="symbol"'):
        assert field not in workspace


def test_phase10_contracts_are_generated_from_fastapi() -> None:
    generated = normalized(ROOT / "packages/contracts/src/api.generated.ts")
    runtime = normalized(ROOT / "packages/contracts/src/runtime.generated.ts")
    type_test = normalized(ROOT / "packages/contracts/src/phase10-contract.type-test.ts")
    for required in (
        "PaperSimulationArtifact:",
        "PaperSimulationCreateRequest:",
        '"/v1/local-simulations"',
        '"/v1/local-simulations/{simulation_run_id}"',
    ):
        assert required in generated
    assert "PaperSimulationArtifact" in runtime
    assert "@ts-expect-error" in type_test


def test_phase10_visual_baseline_matrix_is_exact_and_nonempty() -> None:
    snapshot_root = ROOT / "services/frontend/e2e/__screenshots__/phase10.visual.spec.ts"
    snapshots = list(snapshot_root.glob("*.png"))
    assert {path.name for path in snapshots} == VISUAL_BASELINES
    assert all(path.stat().st_size > 0 for path in snapshots)


def test_phase10_linux_acceptance_mount_is_read_only_and_immutable() -> None:
    verifier = verifier_module()
    command = verifier.phase10_linux_playwright_command(
        "phase10-test",
        "http://127.0.0.1:3000",
    )
    mount = command[command.index("--mount") + 1]
    assert mount.endswith(",readonly")
    assert verifier.PHASE_9_LINUX_PLAYWRIGHT_IMAGE in command
    assert "FABLE5_UPDATE_SNAPSHOTS=1" not in command
    assert "FABLE5_VISUAL_CORPUS=synthetic" not in command
    assert f"{verifier.PHASE_9_BROWSER_TIMEOUT_FLAG}=1" not in command


def test_phase10_linux_snapshot_generation_requires_an_explicit_writable_profile() -> None:
    verifier = verifier_module()
    command = verifier.phase10_linux_playwright_command(
        "phase10-snapshot-test",
        "http://host.docker.internal:3000",
        generate_snapshots=True,
    )
    mount = command[command.index("--mount") + 1]
    assert not mount.endswith(",readonly")
    assert "FABLE5_UPDATE_SNAPSHOTS=1" in command
    assert "FABLE5_VISUAL_CORPUS=synthetic" in command
    assert f"{verifier.PHASE_9_BROWSER_TIMEOUT_FLAG}=1" not in command


def test_phase10_runs_inherited_phase8_browser_specs_in_the_pinned_linux_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    verifier = verifier_module()
    captured: list[tuple[list[str], dict[str, str]]] = []
    cleaned: list[str] = []
    monkeypatch.setattr(verifier.sys, "platform", "linux")
    monkeypatch.setattr(verifier.shutil, "which", lambda _: "/usr/bin/npm")
    monkeypatch.setattr(
        verifier,
        "snapshot_tables",
        lambda project, environment, tables: {"stable": (1, "a" * 64)},
    )
    monkeypatch.setattr(
        verifier,
        "run",
        lambda command, *, env: captured.append((command, env.copy())),
    )
    monkeypatch.setattr(
        verifier,
        "cleanup_phase10_linux_playwright_container",
        lambda project, environment: cleaned.append(project),
    )
    monkeypatch.setattr(
        verifier,
        "cleanup_phase11_linux_playwright_container",
        lambda project, environment: cleaned.append(project),
    )

    phase10_environment = {
        "FABLE5_VERIFY_PHASE": "10",
        verifier.PHASE_9_BROWSER_TIMEOUT_FLAG: "ambient-value",
    }
    original_phase10_environment = phase10_environment.copy()
    verifier.verify_phase8_browser(
        "phase10-inherited",
        phase10_environment,
        "http://127.0.0.1:3000",
    )

    command, environment = captured[-1]
    assert phase10_environment == original_phase10_environment
    assert "e2e/phase8.accessibility.spec.ts" in command
    assert "e2e/phase8.visual.spec.ts" in command
    assert "e2e/phase10.accessibility.spec.ts" not in command
    assert "FABLE5_VERIFY_PHASE=10" in command
    timeout_flag = f"{verifier.PHASE_9_BROWSER_TIMEOUT_FLAG}=1"
    assert command.count(timeout_flag) == 1
    assert command[command.index("--mount") + 1].endswith(",readonly")
    assert environment["FABLE5_VERIFY_PHASE"] == "10"
    assert environment[verifier.PHASE_9_BROWSER_TIMEOUT_FLAG] == "1"
    assert cleaned == ["phase10-inherited"]

    phase12_environment = {
        "FABLE5_VERIFY_PHASE": "12",
        verifier.PHASE_9_BROWSER_TIMEOUT_FLAG: "ambient-value",
    }
    original_phase12_environment = phase12_environment.copy()
    verifier.verify_phase8_browser(
        "phase12-inherited",
        phase12_environment,
        "http://127.0.0.1:3000",
    )
    phase12_command, phase12_host_environment = captured[-1]
    assert phase12_environment == original_phase12_environment
    assert "FABLE5_VERIFY_PHASE=12" in phase12_command
    assert phase12_command.count(timeout_flag) == 1
    assert phase12_command[phase12_command.index("--mount") + 1].endswith(",readonly")
    assert phase12_host_environment["FABLE5_VERIFY_PHASE"] == "12"
    assert cleaned == ["phase10-inherited", "phase12-inherited"]

    phase13_environment = {
        "FABLE5_VERIFY_PHASE": "13",
        verifier.PHASE_9_BROWSER_TIMEOUT_FLAG: "ambient-value",
    }
    original_phase13_environment = phase13_environment.copy()
    verifier.verify_phase8_browser(
        "phase13-inherited", phase13_environment, "http://127.0.0.1:3000"
    )
    phase13_command, phase13_host_environment = captured[-1]
    assert phase13_environment == original_phase13_environment
    assert "FABLE5_VERIFY_PHASE=13" in phase13_command
    assert phase13_command.count(timeout_flag) == 1
    assert phase13_host_environment["FABLE5_VERIFY_PHASE"] == "13"
    assert cleaned == ["phase10-inherited", "phase12-inherited", "phase13-inherited"]

    phase14_environment = {
        "FABLE5_VERIFY_PHASE": "14",
        verifier.PHASE_9_BROWSER_TIMEOUT_FLAG: "ambient-value",
    }
    original_phase14_environment = phase14_environment.copy()
    verifier.verify_phase8_browser(
        "phase14-inherited", phase14_environment, "http://127.0.0.1:3000"
    )
    phase14_command, phase14_host_environment = captured[-1]
    assert phase14_environment == original_phase14_environment
    assert "FABLE5_VERIFY_PHASE=14" in phase14_command
    assert phase14_command.count(timeout_flag) == 1
    assert phase14_host_environment["FABLE5_VERIFY_PHASE"] == "14"
    assert cleaned == [
        "phase10-inherited",
        "phase12-inherited",
        "phase13-inherited",
        "phase14-inherited",
    ]

    phase15_environment = {
        "FABLE5_VERIFY_PHASE": "15",
        verifier.PHASE_9_BROWSER_TIMEOUT_FLAG: "ambient-value",
    }
    original_phase15_environment = phase15_environment.copy()
    verifier.verify_phase8_browser(
        "phase15-inherited", phase15_environment, "http://127.0.0.1:3000"
    )
    phase15_command, phase15_host_environment = captured[-1]
    assert phase15_environment == original_phase15_environment
    assert "FABLE5_VERIFY_PHASE=15" in phase15_command
    assert phase15_command.count(timeout_flag) == 1
    assert phase15_host_environment["FABLE5_VERIFY_PHASE"] == "15"
    assert cleaned[-1] == "phase15-inherited"

    phase16_environment = {
        "FABLE5_VERIFY_PHASE": "16",
        verifier.PHASE_9_BROWSER_TIMEOUT_FLAG: "ambient-value",
    }
    original_phase16_environment = phase16_environment.copy()
    verifier.verify_phase8_browser(
        "phase16-inherited", phase16_environment, "http://127.0.0.1:3000"
    )
    phase16_command, phase16_host_environment = captured[-1]
    assert phase16_environment == original_phase16_environment
    assert "FABLE5_VERIFY_PHASE=16" in phase16_command
    assert phase16_command.count(timeout_flag) == 1
    assert phase16_host_environment["FABLE5_VERIFY_PHASE"] == "16"
    assert cleaned[-1] == "phase16-inherited"

    phase17_environment = {
        "FABLE5_VERIFY_PHASE": "17",
        verifier.PHASE_9_BROWSER_TIMEOUT_FLAG: "ambient-value",
    }
    original_phase17_environment = phase17_environment.copy()
    verifier.verify_phase8_browser(
        "phase17-inherited", phase17_environment, "http://127.0.0.1:3000"
    )
    phase17_command, phase17_host_environment = captured[-1]
    assert phase17_environment == original_phase17_environment
    assert "FABLE5_VERIFY_PHASE=17" in phase17_command
    assert phase17_command.count(timeout_flag) == 1
    assert phase17_host_environment["FABLE5_VERIFY_PHASE"] == "17"
    assert cleaned[-1] == "phase17-inherited"

    phase18_environment = {
        "FABLE5_VERIFY_PHASE": "18",
        verifier.PHASE_9_BROWSER_TIMEOUT_FLAG: "ambient-value",
    }
    original_phase18_environment = phase18_environment.copy()
    verifier.verify_phase8_browser(
        "phase18-inherited", phase18_environment, "http://127.0.0.1:3000"
    )
    phase18_command, phase18_host_environment = captured[-1]
    assert phase18_environment == original_phase18_environment
    assert "FABLE5_VERIFY_PHASE=18" in phase18_command
    assert phase18_command.count(timeout_flag) == 1
    assert phase18_host_environment["FABLE5_VERIFY_PHASE"] == "18"
    assert cleaned[-1] == "phase18-inherited"

    future_environment = {
        "FABLE5_VERIFY_PHASE": "19",
        verifier.PHASE_9_BROWSER_TIMEOUT_FLAG: "ambient-value",
    }
    original_future_environment = future_environment.copy()
    verifier.verify_phase8_browser("future", future_environment, "http://127.0.0.1:3000")
    future_command, future_host_environment = captured[-1]
    assert future_environment == original_future_environment
    assert timeout_flag not in future_command
    assert verifier.PHASE_9_BROWSER_TIMEOUT_FLAG not in future_host_environment
    assert cleaned[-1] == "phase18-inherited"


def test_phase10_allowlist_enumerates_paper_and_visual_files_exactly() -> None:
    verifier = verifier_module()
    expected_paper_paths = {
        "services/paper/README.md",
        "services/paper/src/fable5_paper/__init__.py",
        "services/paper/src/fable5_paper/canonical.py",
        "services/paper/src/fable5_paper/contracts.py",
        "services/paper/src/fable5_paper/fixtures.py",
        "services/paper/src/fable5_paper/repository.py",
        "services/paper/src/fable5_paper/workflow.py",
        "services/paper/tests/test_phase10_postgres.py",
        "services/paper/tests/test_phase10_workflow.py",
    }
    assert verifier.PHASE_10_PAPER_PATHS == expected_paper_paths
    assert verifier.PHASE_10_VISUAL_BASELINE_PATHS == {
        f"services/frontend/e2e/__screenshots__/phase10.visual.spec.ts/{name}"
        for name in VISUAL_BASELINES
    }
    assert verifier.PHASE_10_PAPER_PATHS <= verifier.PHASE_10_ALLOWED_WRITES
    assert verifier.PHASE_10_VISUAL_BASELINE_PATHS <= verifier.PHASE_10_ALLOWED_WRITES
    source = normalized(ROOT / "scripts/verify_phase1.py")
    assert (
        'allowed.update(path for path in changed_paths if path.startswith("services/paper/")'
        not in source
    )
    assert "changed_paths - PHASE_10_ALLOWED_WRITES" in source


def test_phase10_clean_identity_rejects_dirty_or_changed_source(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    verifier = verifier_module()
    sha = "1" * 40
    tree = "2" * 40

    def clean_git(*arguments: str) -> str:
        values = {
            ("status", "--porcelain=v1", "--untracked-files=all"): "",
            ("rev-parse", "--verify", "HEAD"): sha,
            ("show", "-s", "--format=%T", "HEAD"): tree,
        }
        return values[arguments]

    monkeypatch.setattr(verifier, "git_text", clean_git)
    assert verifier.phase10_clean_git_identity("preflight") == (sha, tree)
    assert "sha=" + sha in capsys.readouterr().out
    with pytest.raises(AssertionError, match="identity changed"):
        verifier.phase10_clean_git_identity("post-cleanup", expected=("3" * 40, tree))

    monkeypatch.setattr(
        verifier,
        "git_text",
        lambda *arguments: " M tracked.py" if arguments[0] == "status" else clean_git(*arguments),
    )
    with pytest.raises(AssertionError, match="clean worktree and index"):
        verifier.phase10_clean_git_identity("preflight")


def test_phase10_resource_inventory_is_global_and_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    verifier = verifier_module()
    commands: list[list[str]] = []

    def empty_run(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="")

    monkeypatch.setattr(verifier.subprocess, "run", empty_run)
    verifier.verify_phase10_acceptance_resource_namespace("preflight", {"PATH": "safe"})
    assert [command[1:3] for command in commands] == [
        ["ps", "--all"],
        ["network", "ls"],
        ["volume", "ls"],
    ]
    assert all("name=fable5_acceptance_" in command for command in commands)

    def dirty_run(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        stdout = "fable5_acceptance_abcd_api_1\n" if command[1] == "ps" else ""
        return subprocess.CompletedProcess(command, 0, stdout=stdout)

    monkeypatch.setattr(verifier.subprocess, "run", dirty_run)
    with pytest.raises(AssertionError, match="ambiguous cleanup ownership"):
        verifier.verify_phase10_acceptance_resource_namespace("preflight", {"PATH": "safe"})


def test_phase10_full_verifier_binds_identity_cleanup_and_inherited_browser() -> None:
    source = normalized(ROOT / "scripts/verify_phase1.py")
    assert "if phase in {10, 11, 12, 13, 14, 15, 16, 17, 18}" in source
    assert 'phase10_clean_git_identity("preflight", phase=phase)' in source
    assert 'verify_phase10_acceptance_resource_namespace(\n            "preflight"' in source
    post_cleanup_resources = (
        'verify_phase10_acceptance_resource_namespace(\n                        "post-cleanup"'
    )
    assert post_cleanup_resources in source
    post_cleanup_identity = (
        '"post-cleanup",\n                        expected=acceptance_identity,\n'
        "                        phase=phase,"
    )
    assert post_cleanup_identity in source
    assert "if phase in {8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18}:" in source
    assert "spec_paths=PHASE_8_BROWSER_SPECS" in source

    accessibility = normalized(ROOT / "services/frontend/e2e/phase8.accessibility.spec.ts")
    visual = normalized(ROOT / "services/frontend/e2e/phase8.visual.spec.ts")
    for spec in (accessibility, visual):
        assert 'process.env.FABLE5_VERIFY_PHASE ?? "18"' in spec
        assert "inheritedModes" in spec
