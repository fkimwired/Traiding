from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PHASE_8_BASELINE_SHA = "94bcfaabf9de457aec47e49e332865a8dcc74f30"
EXPECTED_PHASE_8_TREE = "56d2cf38ba0ff3d5427fbf5f20aefa13d5224581"
PHASE_9_ACCEPTED_SHA = "12a87e9dfb71afd7bb02d1f947ffea63be56a0a3"
EXPECTED_PHASE_9_TREE = "472792e0f53fc5c29ef8d4d73bdef60d6f25a1c9"
PHASE_8_ACCESSIBILITY_SPEC = "services/frontend/e2e/phase8.accessibility.spec.ts"
PHASE_8_LINEAGE_TIMEOUT_BASELINE = b"  test.setTimeout(1_200_000);"
PHASE_9_LINEAGE_TIMEOUT_REPLACEMENT = (
    b"  test.setTimeout(\n"
    b'    process.env.FABLE5_PHASE9_BROWSER_TIMEOUT_PROFILE === "1" ? '
    b"2_100_000 : 1_200_000,\n"
    b"  );"
)
PHASE_9_ALLOWED_WRITES = {
    ".github/workflows/ci.yml",
    "Makefile",
    "README.md",
    "docs/IMPLEMENTATION_PLAN.md",
    "docs/PHASE_09_RELEASE_ACCEPTANCE_DECISIONS.md",
    "docs/handoffs/PHASE_09.md",
    "scripts/check.ps1",
    "scripts/check.sh",
    "scripts/run_phase_gate.py",
    "scripts/verify_phase1.py",
    PHASE_8_ACCESSIBILITY_SPEC,
    "tests/test_phase5_postgres.py",
    "tests/test_phase9_gate_runner.py",
    "tests/test_phase9_static.py",
    "tests/test_repository_policy.py",
}
CONTRACT_SHA256 = {
    "packages/contracts/openapi.json": (
        "d89a72e31778ed7d6edcaaf5611e99506aecdc49c640df336e2a622023a0bb25"
    ),
    "packages/contracts/src/api.generated.ts": (
        "5fa0ce5d903529705709dc2dc0f4c86d71830fc634548551d145cf3bb7a0003e"
    ),
    "packages/contracts/src/runtime.generated.ts": (
        "905810491adf9f52090ff8af109137df76c76367293a21cd39a71dc643a4b964"
    ),
    "packages/contracts/src/validate-response.ts": (
        "57f74259a7d8f00bd739099a01eebd25d4fa7fed01d2e12320d28d67620e3503"
    ),
}
MIGRATION_SHA256 = {
    "services/api/migrations/versions/0001_phase1_audit_spine.py": (
        "5cd27e1bde6b03720f54fe5e1260cf5f9085e16a4eebed957aeeba1a3a7d17f8"
    ),
    "services/api/migrations/versions/0002_phase2_source_extraction.py": (
        "d45c1cb0ade079cfba7492c75c1aff13fc714aaae0a81637f21942c175c4e5c8"
    ),
    "services/api/migrations/versions/0003_phase3_canon_mapping.py": (
        "6859c63723dc31d6ede4cdd5528a42640f16e3c6103567b5d900a46741edf07d"
    ),
    "services/api/migrations/versions/0004_phase4_point_in_time_data.py": (
        "78c52c613358708940d88cbd47069bdde9bc857046bf646d7461bd13b57b3008"
    ),
    "services/api/migrations/versions/0005_phase5_evaluation.py": (
        "b368edf97c35c5b7d7ac651073a02c204816b638855d3bcae4d7cabf265a1404"
    ),
    "services/api/migrations/versions/0006_phase6_research.py": (
        "7f4ab516a31208b7c5f5400b1b593d7675c75570fa839f524bfddea3152d7070"
    ),
    "services/api/migrations/versions/0007_phase7_approval_risk.py": (
        "4ef4e6301f205fb9a18f478ac3fa6d6920dbe0af462b6f371e83dd2d622a8090"
    ),
}
IMMUTABLE_PREFIXES = (
    "services/extraction/tests/fixtures/",
    "services/data/src/fable5_data/fixtures/",
    "services/frontend/e2e/__screenshots__/phase8.visual.spec.ts/",
)
IMMUTABLE_ARTIFACTS = (
    "docs/PHASE_02_SCHEMA_DECISIONS.md",
    "docs/PHASE_03_MAPPING_DECISIONS.md",
    "docs/PHASE_04_DATA_DECISIONS.md",
    "docs/PHASE_06_RESEARCH_DECISIONS.md",
    "docs/PHASE_07_APPROVAL_DECISIONS.md",
    "docs/PHASE_08_UI_DECISIONS.md",
    "docs/handoffs/PHASE_02.md",
    "docs/handoffs/PHASE_03.md",
    "docs/handoffs/PHASE_04.md",
    "docs/handoffs/PHASE_07.md",
    "docs/handoffs/PHASE_08.md",
)


def git(*args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=check,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def baseline_bytes(path: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"{PHASE_8_BASELINE_SHA}:{path}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout


def phase9_bytes(path: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"{PHASE_9_ACCEPTED_SHA}:{path}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout


def phase9_text(path: str) -> str:
    return phase9_bytes(path).decode("utf-8")


def tracked_baseline_paths() -> set[str]:
    return set(git("ls-tree", "-r", "--name-only", PHASE_8_BASELINE_SHA).splitlines())


def accepted_phase9_changed_paths() -> set[str]:
    return {
        path.replace("\\", "/")
        for path in git(
            "diff", "--name-only", PHASE_8_BASELINE_SHA, PHASE_9_ACCEPTED_SHA, "--"
        ).splitlines()
        if path
    }


def test_phase8_baseline_tree_is_the_authorized_source() -> None:
    assert git("show", "-s", "--format=%T", PHASE_8_BASELINE_SHA) == EXPECTED_PHASE_8_TREE
    assert git("show", "-s", "--format=%T", PHASE_9_ACCEPTED_SHA) == EXPECTED_PHASE_9_TREE


def test_phase9_worktree_diff_stays_inside_the_exact_allowlist() -> None:
    assert accepted_phase9_changed_paths() <= PHASE_9_ALLOWED_WRITES


def test_phase9_contracts_and_migrations_are_exact_phase8_bytes() -> None:
    accepted_paths = set(git("ls-tree", "-r", "--name-only", PHASE_9_ACCEPTED_SHA).splitlines())
    accepted_migrations = {
        path
        for path in accepted_paths
        if path.startswith("services/api/migrations/versions/") and path.endswith(".py")
    }
    assert accepted_migrations == set(MIGRATION_SHA256)
    assert not any(path.rsplit("/", 1)[-1].startswith("0008") for path in accepted_migrations)

    for path, expected_hash in {**CONTRACT_SHA256, **MIGRATION_SHA256}.items():
        accepted = phase9_bytes(path)
        assert accepted == baseline_bytes(path)
        assert hashlib.sha256(accepted).hexdigest() == expected_hash


def test_phase9_fixtures_artifacts_and_all_48_snapshots_are_phase8_bytes() -> None:
    baseline_paths = tracked_baseline_paths()
    immutable_paths = sorted(path for path in baseline_paths if path.startswith(IMMUTABLE_PREFIXES))
    assert immutable_paths
    for path in immutable_paths:
        assert phase9_bytes(path) == baseline_bytes(path)
    for path in IMMUTABLE_ARTIFACTS:
        assert phase9_bytes(path) == baseline_bytes(path)

    snapshot_prefix = IMMUTABLE_PREFIXES[-1]
    snapshots = [path for path in immutable_paths if path.startswith(snapshot_prefix)]
    assert len(snapshots) == 48
    assert sum(path.endswith("-win32.png") for path in snapshots) == 24
    assert sum(path.endswith("-linux.png") for path in snapshots) == 24


def test_phase9_phase8_timeout_exception_is_exact_and_verifier_owned(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    baseline = baseline_bytes(PHASE_8_ACCESSIBILITY_SPEC)
    assert baseline.count(PHASE_8_LINEAGE_TIMEOUT_BASELINE) == 1
    assert phase9_bytes(PHASE_8_ACCESSIBILITY_SPEC) == baseline.replace(
        PHASE_8_LINEAGE_TIMEOUT_BASELINE,
        PHASE_9_LINEAGE_TIMEOUT_REPLACEMENT,
        1,
    )

    verifier_path = ROOT / "scripts/verify_phase1.py"
    spec = importlib.util.spec_from_file_location("phase9_browser_verifier", verifier_path)
    assert spec is not None and spec.loader is not None
    verifier = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(verifier)

    browser_environments: list[dict[str, str]] = []
    monkeypatch.setattr(verifier.sys, "platform", "win32")
    monkeypatch.setattr(verifier.shutil, "which", lambda command: "npm.CMD")
    monkeypatch.setattr(
        verifier,
        "snapshot_tables",
        lambda project, environment, tables: {"stable": [{"id": 1}]},
    )

    def capture_run(command: list[str], *, env: dict[str, str]) -> None:
        assert command == ["npm.CMD", "--workspace", "@fable5/frontend", "run", "test:e2e"]
        browser_environments.append(env.copy())

    monkeypatch.setattr(verifier, "run", capture_run)

    inherited_environment = {
        "FABLE5_VERIFY_PHASE": "8",
        verifier.PHASE_9_BROWSER_TIMEOUT_FLAG: "ambient-value",
    }
    verifier.verify_phase8_browser("project", inherited_environment, "http://frontend")
    assert inherited_environment[verifier.PHASE_9_BROWSER_TIMEOUT_FLAG] == "ambient-value"
    assert verifier.PHASE_9_BROWSER_TIMEOUT_FLAG not in browser_environments[-1]
    assert "FABLE5_PHASE9_STAGE " not in capsys.readouterr().out

    phase9_environment = {
        "FABLE5_VERIFY_PHASE": "9",
        verifier.PHASE_9_BROWSER_TIMEOUT_FLAG: "ambient-value",
    }
    verifier.verify_phase8_browser("project", phase9_environment, "http://frontend")
    assert phase9_environment[verifier.PHASE_9_BROWSER_TIMEOUT_FLAG] == "ambient-value"
    assert browser_environments[-1][verifier.PHASE_9_BROWSER_TIMEOUT_FLAG] == "1"
    stage_names = [
        json.loads(line.removeprefix("FABLE5_PHASE9_STAGE "))["stage"]
        for line in capsys.readouterr().out.splitlines()
        if line.startswith("FABLE5_PHASE9_STAGE ")
    ]
    assert stage_names == [
        "phase8_browser_pre_snapshot",
        "phase8_browser_playwright",
        "phase8_browser_post_snapshot",
    ]

    source = verifier_path.read_text(encoding="utf-8")
    assert 'with phase9_stage(phase, "phase8_timeline_api"):' in source


def test_phase9_linux_browser_uses_the_exact_pinned_read_only_runtime_and_cleans(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    verifier_path = ROOT / "scripts/verify_phase1.py"
    spec = importlib.util.spec_from_file_location("phase9_linux_browser_verifier", verifier_path)
    assert spec is not None and spec.loader is not None
    verifier = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(verifier)

    captured_runs: list[tuple[list[str], dict[str, str]]] = []
    cleanup_calls: list[tuple[list[str], dict[str, object]]] = []
    monkeypatch.setattr(verifier.sys, "platform", "linux")
    monkeypatch.setattr(verifier.shutil, "which", lambda command: "/usr/bin/npm")
    monkeypatch.setattr(
        verifier,
        "snapshot_tables",
        lambda project, environment, tables: {"stable": [{"id": 1}]},
    )

    def capture_run(command: list[str], *, env: dict[str, str]) -> None:
        captured_runs.append((command, env.copy()))

    def capture_linux_run(command: list[str], environment: dict[str, str]) -> None:
        captured_runs.append((command, environment.copy()))

    def capture_cleanup(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        cleanup_calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 1)

    monkeypatch.setattr(verifier, "run", capture_run)
    monkeypatch.setattr(verifier, "run_phase9_linux_playwright", capture_linux_run)
    monkeypatch.setattr(verifier.subprocess, "run", capture_cleanup)

    inherited_environment = {
        "FABLE5_VERIFY_PHASE": "8",
        verifier.PHASE_9_BROWSER_TIMEOUT_FLAG: "ambient-value",
    }
    verifier.verify_phase8_browser("project", inherited_environment, "http://frontend")
    assert captured_runs[-1][0] == [
        "/usr/bin/npm",
        "--workspace",
        "@fable5/frontend",
        "run",
        "test:e2e",
    ]
    assert verifier.PHASE_9_BROWSER_TIMEOUT_FLAG not in captured_runs[-1][1]
    assert cleanup_calls == []
    assert "FABLE5_PHASE9_STAGE " not in capsys.readouterr().out

    phase9_environment = {
        "FABLE5_VERIFY_PHASE": "9",
        verifier.PHASE_9_BROWSER_TIMEOUT_FLAG: "ambient-value",
        "FABLE5_UPDATE_SNAPSHOTS": "1",
        "FABLE5_VISUAL_CORPUS": "synthetic",
        "SECRET_SENTINEL": "must-not-enter-container",
    }
    original_phase9_environment = phase9_environment.copy()
    verifier.verify_phase8_browser("project", phase9_environment, "http://frontend")
    assert phase9_environment == original_phase9_environment

    expected_image = (
        "mcr.microsoft.com/playwright:v1.61.1-noble@"
        "sha256:5b8f294aff9041b7191c34a4bab3ac270157a28774d4b0660e9743297b697e48"
    )
    expected_command = [
        "docker",
        "run",
        "--rm",
        "--init",
        "--name",
        "project_phase9_playwright",
        "--label",
        "com.docker.compose.project=project",
        "--network",
        "host",
        "--ipc",
        "host",
        "--mount",
        f"type=bind,source={verifier.ROOT.resolve()},target=/work,readonly",
        "--workdir",
        "/work/services/frontend",
        "--env",
        "PLAYWRIGHT_BASE_URL=http://frontend",
        "--env",
        f"{verifier.PHASE_9_BROWSER_TIMEOUT_FLAG}=1",
        "--env",
        "CI=true",
        expected_image,
        "node",
        "../../node_modules/@playwright/test/cli.js",
        "test",
        "--reporter=json",
        "--output=/tmp/playwright-results",
    ]
    command, host_environment = captured_runs[-1]
    assert command == expected_command
    assert host_environment[verifier.PHASE_9_BROWSER_TIMEOUT_FLAG] == "1"
    assert [command[index + 1] for index, value in enumerate(command) if value == "--env"] == [
        "PLAYWRIGHT_BASE_URL=http://frontend",
        f"{verifier.PHASE_9_BROWSER_TIMEOUT_FLAG}=1",
        "CI=true",
    ]
    assert "FABLE5_UPDATE_SNAPSHOTS" not in " ".join(command)
    assert "FABLE5_VISUAL_CORPUS" not in " ".join(command)
    assert "must-not-enter-container" not in " ".join(command)
    assert verifier.PHASE_9_LINUX_PLAYWRIGHT_IMAGE == expected_image
    assert cleanup_calls[-1][0] == [
        "docker",
        "container",
        "rm",
        "--force",
        "project_phase9_playwright",
    ]
    assert cleanup_calls[-1][1]["cwd"] == verifier.ROOT
    assert cleanup_calls[-1][1]["check"] is False
    stage_names = [
        json.loads(line.removeprefix("FABLE5_PHASE9_STAGE "))["stage"]
        for line in capsys.readouterr().out.splitlines()
        if line.startswith("FABLE5_PHASE9_STAGE ")
    ]
    assert stage_names == [
        "phase8_browser_pre_snapshot",
        "phase8_browser_playwright",
        "phase8_browser_post_snapshot",
    ]

    cleanup_calls.clear()

    def fail_run(command: list[str], environment: dict[str, str]) -> None:
        raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(verifier, "run_phase9_linux_playwright", fail_run)
    with pytest.raises(subprocess.CalledProcessError):
        verifier.verify_phase8_browser("project", phase9_environment, "http://frontend")
    assert len(cleanup_calls) == 1
    assert cleanup_calls[0][0][-1] == "project_phase9_playwright"


def test_phase9_linux_playwright_emits_only_allowlisted_failure_identity(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    verifier_path = ROOT / "scripts/verify_phase1.py"
    spec = importlib.util.spec_from_file_location(
        "phase9_playwright_result_verifier", verifier_path
    )
    assert spec is not None and spec.loader is not None
    verifier = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(verifier)

    report = {
        "stats": {"unexpected": 1},
        "suites": [
            {
                "title": "SECRET TITLE",
                "specs": [
                    {
                        "file": "phase8.accessibility.spec.ts",
                        "line": 570,
                        "title": "SECRET TEST TITLE",
                        "tests": [
                            {
                                "projectName": "desktop",
                                "status": "unexpected",
                                "timeout": 2_100_000,
                                "results": [
                                    {
                                        "status": "timedOut",
                                        "duration": 2_100_123,
                                        "error": {"message": "API_KEY=secret-value"},
                                        "stderr": ["licensed source payload"],
                                    }
                                ],
                            }
                        ],
                    }
                ],
            }
        ],
        "errors": [{"message": "postgres://user:password@example.invalid/db"}],
    }

    def completed_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            command,
            1,
            stdout=json.dumps(report),
            stderr="AWS_SECRET_ACCESS_KEY=secret",
        )

    monkeypatch.setattr(verifier.subprocess, "run", completed_run)
    with pytest.raises(subprocess.CalledProcessError):
        verifier.run_phase9_linux_playwright(["docker", "run"], {"PATH": "safe"})
    output = capsys.readouterr().out
    expected = {
        "duration_ms": 2_100_123,
        "file": "phase8.accessibility.spec.ts",
        "line": 570,
        "project": "desktop",
        "status": "timedOut",
        "timeout_ms": 2_100_000,
    }
    assert (
        verifier.PHASE_9_PLAYWRIGHT_RESULT_PREFIX
        + json.dumps(expected, sort_keys=True, separators=(",", ":"))
    ) in output
    for secret in (
        "SECRET TITLE",
        "SECRET TEST TITLE",
        "API_KEY",
        "licensed source payload",
        "postgres://",
        "AWS_SECRET_ACCESS_KEY",
    ):
        assert secret not in output

    invalid = json.loads(json.dumps(report))
    invalid["suites"][0]["specs"][0]["file"] = "e2e/secret.spec.ts"
    with pytest.raises(AssertionError, match="location is not allowlisted"):
        verifier.phase9_playwright_failure_records(invalid)

    invalid = json.loads(json.dumps(report))
    invalid["suites"][0]["specs"][0]["tests"][0]["timeout"] = 1_500_000
    with pytest.raises(AssertionError, match="timing is invalid"):
        verifier.phase9_playwright_failure_records(invalid)

    invalid = json.loads(json.dumps(report))
    invalid["suites"][0]["specs"][0]["tests"][0]["results"][0]["duration"] = True
    with pytest.raises(AssertionError, match="duration is invalid"):
        verifier.phase9_playwright_failure_records(invalid)


def test_phase9_verifier_runs_inherited_static_first_and_full_cleanup_last() -> None:
    source = phase9_text("scripts/verify_phase1.py")
    assert "PHASE_8_BASELINE_SHA" in source
    assert "PHASE_9_ALLOWED_WRITES" in source
    assert "def verify_phase9_static" in source
    assert "verify_static_inherited(8)" in source
    wrapper = source.split("def verify_static(phase: int = 1)", maxsplit=1)[1].split(
        "def run(", maxsplit=1
    )[0]
    assert wrapper.index("verify_static_inherited(8)") < wrapper.index("verify_phase9_static()")
    assert "Full Compose Phase 8 verification passed." in source
    assert "Full Compose Phase 9 verification passed." in source
    assert source.index("verify_phase9_compose_cleanup") < source.index(
        'print("Full Compose Phase 9 verification passed.")'
    )
    assert "FABLE5_PHASE9_STAGE" in source


def verify_compose_named_calls(source: str) -> list[str]:
    tree = ast.parse(source)
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "verify_compose"
    )
    calls: list[str] = []

    class CallVisitor(ast.NodeVisitor):
        def visit_Call(self, node: ast.Call) -> None:
            if isinstance(node.func, ast.Name):
                calls.append(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.append(node.func.attr)
            self.generic_visit(node)

    CallVisitor().visit(function)
    return calls


def test_phase9_full_verifier_preserves_the_inherited_phase1_8_call_sequence() -> None:
    baseline = baseline_bytes("scripts/verify_phase1.py").decode("utf-8")
    current = phase9_text("scripts/verify_phase1.py")
    baseline_calls = verify_compose_named_calls(baseline)
    phase9_only_calls = {
        "phase9_stage",
        "phase6_request_timeout_context",
        "verify_phase9_compose_cleanup",
    }
    current_inherited_calls = [
        name for name in verify_compose_named_calls(current) if name not in phase9_only_calls
    ]
    assert current_inherited_calls[: len(baseline_calls)] == baseline_calls
    assert current_inherited_calls[len(baseline_calls) :] == ["AssertionError", "print"]


def test_phase9_preserves_serial_browser_configuration() -> None:
    source = phase9_text("services/frontend/playwright.config.ts")
    assert "fullyParallel: false" in source
    assert "retries: 0" in source
    assert "workers: 1" in source


def test_phase9_wrappers_default_validate_and_forward_phase9() -> None:
    for path in ("scripts/check.ps1", "scripts/check.sh", "Makefile"):
        source = phase9_text(path)
        assert "FABLE5_VERIFY_PHASE" in source
        assert "--phase" in source
        assert "9" in source
    assert "${FABLE5_VERIFY_PHASE:-9}" in phase9_text("scripts/check.sh")
    assert "${FABLE5_VERIFY_PHASE:-9}" in phase9_text("Makefile")
    assert 'else { "9" }' in phase9_text("scripts/check.ps1")

    for unchanged in ("scripts/test.ps1", "scripts/test.sh"):
        assert phase9_bytes(unchanged) == baseline_bytes(unchanged)


def test_phase9_ci_is_split_pinned_serial_and_uploads_only_sanitized_evidence() -> None:
    workflow = phase9_text(".github/workflows/ci.yml")
    assert workflow.startswith("name: phase-9-ci\n")
    assert "permissions:\n  contents: read" in workflow
    assert 'FABLE5_VERIFY_PHASE: "9"' in workflow
    assert "fetch-depth: 0" in workflow
    assert "preflight:" in workflow
    assert "unit:" in workflow and "needs: preflight" in workflow
    assert "phase9-compose:" in workflow
    assert "timeout-minutes: 120" in workflow
    assert "timeout-minutes: 90" not in workflow
    assert "run_phase_gate.py run --phase 9" in workflow
    assert workflow.count("--timeout-seconds 6300") == 1
    assert "--timeout-seconds 5100" not in workflow
    assert "run_phase_gate.py verify-evidence" in workflow
    assert "retention-days: 14" in workflow
    assert "if-no-files-found: error" in workflow
    assert "phase-gate.manifest.json" in workflow
    assert "phase-gate.sanitized.log" in workflow
    assert "phase-gate.raw.log" not in workflow
    assert "runner_exit" in workflow and "evidence_exit" in workflow
    assert "cancel-in-progress: ${{ github.event_name == 'pull_request' }}" in workflow
    assert "npx playwright install --with-deps chromium" not in workflow
    immutable_image = (
        "mcr.microsoft.com/playwright:v1.61.1-noble@"
        "sha256:5b8f294aff9041b7191c34a4bab3ac270157a28774d4b0660e9743297b697e48"
    )
    immutable_pull = f"docker pull {immutable_image}"
    assert workflow.count(immutable_pull) == 1
    compose = workflow.split("\n  phase9-compose:\n", 1)[1]
    assert compose.index("- run: npm ci") < compose.index(immutable_pull)
    assert compose.index(immutable_pull) < compose.index("run_phase_gate.py run --phase 9")

    action_lines = [line.strip() for line in workflow.splitlines() if "uses:" in line]
    assert action_lines
    for line in action_lines:
        revision = line.split("@", 1)[1].split()[0]
        assert len(revision) == 40
        int(revision, 16)
        assert "# v" in line


def test_phase9_ci_hydrates_exact_frozen_linux_rolldown_binding_only_for_unit() -> None:
    lock = json.loads(phase9_text("package-lock.json"))
    binding_version = lock["packages"]["node_modules/rolldown"]["optionalDependencies"][
        "@rolldown/binding-linux-x64-gnu"
    ]
    install = (
        "npm install --no-save --ignore-scripts --no-audit --no-fund "
        f"@rolldown/binding-linux-x64-gnu@{binding_version}"
    )
    metadata_check = (
        "git diff --exit-code -- package.json package-lock.json "
        "packages/contracts/package.json services/frontend/package.json"
    )
    workflow = phase9_text(".github/workflows/ci.yml")
    preflight, remainder = workflow.split("\n  unit:\n", 1)
    unit, compose = remainder.split("\n  phase9-compose:\n", 1)

    assert binding_version == "1.1.5"
    assert workflow.count(install) == 1
    assert workflow.count(metadata_check) == 1
    assert install not in preflight
    assert install not in compose
    assert unit.index("- run: npm ci") < unit.index(install) < unit.index("- run: npm test")
    assert unit.index(install) < unit.index(metadata_check) < unit.index("- run: npm test")


def test_phase9_through_phase12_widen_phase6_transport_patience_and_record_substages() -> None:
    verifier_path = ROOT / "scripts/verify_phase1.py"
    spec = importlib.util.spec_from_file_location("phase9_timeout_verifier", verifier_path)
    assert spec is not None and spec.loader is not None
    verifier = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(verifier)

    for inherited_phase in (6, 7, 8, 27):
        assert verifier.phase6_request_timeout_profile(inherited_phase) == (240, 60, 10)
    assert verifier.PHASE_6_TIMEOUT_PHASE.get() == 6
    for closure_phase in (
        9,
        10,
        11,
        12,
        13,
        14,
        15,
        16,
        17,
        18,
        19,
        20,
        21,
        22,
        23,
        24,
        25,
        26,
    ):
        assert verifier.phase6_request_timeout_profile(closure_phase) == (480, 180, 30)
        with verifier.phase6_request_timeout_context(closure_phase):
            assert verifier.PHASE_6_TIMEOUT_PHASE.get() == closure_phase
        assert verifier.PHASE_6_TIMEOUT_PHASE.get() == 6

    source = verifier_path.read_text(encoding="utf-8")
    phase6_api = source.split("def verify_phase6_api", 1)[1].split("def compose_exec", 1)[0]
    assert "timeout_seconds=PHASE_6_REQUEST_TIMEOUT_SECONDS" not in phase6_api
    assert "timeout_seconds=60" not in phase6_api
    assert phase6_api.count("timeout_seconds=request_timeout_seconds") == 3
    assert "timeout_seconds=detail_timeout_seconds" in phase6_api
    assert "timeout_seconds=validation_timeout_seconds" in phase6_api
    assert "with phase6_request_timeout_context(phase):" in source
    assert "phase6_run_ids = verify_phase6_api(api_url)" in source

    runner = phase9_text("scripts/run_phase_gate.py")
    for stage in (
        "phase6_schema_cycle",
        "phase6_api",
        "phase6_postgres_tests",
        "phase6_append_only",
        "phase8_timeline_api",
        "phase8_browser_pre_snapshot",
        "phase8_browser_playwright",
        "phase8_browser_post_snapshot",
    ):
        assert f'with phase9_stage(phase, "{stage}")' in source
        assert f'"{stage}",' in runner


def test_phase9_decisions_and_handoff_keep_the_release_boundary_closed() -> None:
    for path in (
        "docs/PHASE_09_RELEASE_ACCEPTANCE_DECISIONS.md",
        "docs/handoffs/PHASE_09.md",
    ):
        body = phase9_text(path)
        assert PHASE_8_BASELINE_SHA in body
        assert "Phase 9" in body
        assert "Ubuntu" in body
        assert "not accepted" in body
        for forbidden in (
            "live trading",
            "broker integration",
            "order submission",
            "paper execution",
        ):
            assert forbidden in body.lower()


def test_phase9_expected_contract_hashes_are_documented_verbatim() -> None:
    decisions = phase9_text("docs/PHASE_09_RELEASE_ACCEPTANCE_DECISIONS.md")
    for path, digest in CONTRACT_SHA256.items():
        assert path in decisions
        assert digest in decisions


def test_phase9_snapshot_matrix_names_are_stable_json_safe_strings() -> None:
    names = sorted(
        path.rsplit("/", 1)[-1]
        for path in git("ls-tree", "-r", "--name-only", PHASE_9_ACCEPTED_SHA).splitlines()
        if path.startswith("services/frontend/e2e/__screenshots__/phase8.visual.spec.ts/")
        and path.endswith(".png")
    )
    assert json.loads(json.dumps(names)) == names
