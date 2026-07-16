from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / "scripts/run_phase_gate.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_phase_gate", RUNNER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def valid_bundle(runner):
    run_id = "phase9-test-run"
    platform = "win32"
    sha = "a" * 40
    tree = "b" * 40
    start_event = {
        "event": "start",
        "platform": platform,
        "run_id": run_id,
        "sha": sha,
        "tree": tree,
    }
    end_event = {"event": "end", "run_id": run_id}
    stage = {
        "elapsed_seconds": 1.25,
        "end_utc": "2026-07-16T00:00:01.250000Z",
        "result": "pass",
        "stage": "phase9_static",
        "start_utc": "2026-07-16T00:00:00.000000Z",
    }
    lines = [
        f"RUNNER_EVENT {json.dumps(start_event, sort_keys=True, separators=(',', ':'))}",
        f"FABLE5_PHASE9_STAGE {json.dumps(stage, sort_keys=True, separators=(',', ':'))}",
        "Full Compose Phase 8 verification passed.",
        "Full Compose Phase 9 verification passed.",
        f"RUNNER_EVENT {json.dumps(end_event, sort_keys=True, separators=(',', ':'))}",
    ]
    sanitized_log = ("\n".join(lines) + "\n").encode()
    command = ["python", "scripts/verify_phase1.py", "--phase", "9"]
    snapshots = {"idea-intake-mode-mobile-win32.png": "c" * 64}
    manifest = {
        "schema_version": runner.MANIFEST_SCHEMA_VERSION,
        "phase": 9,
        "run_id": run_id,
        "phase_8_baseline_sha": runner.PHASE_8_BASELINE_SHA,
        "current_sha": sha,
        "current_tree": tree,
        "git_status_pre": "",
        "git_status_post": "",
        "child_command": command,
        "platform": platform,
        "tool_versions": {"python": "3.12.0"},
        "started_at_utc": "2026-07-16T00:00:00.000000Z",
        "ended_at_utc": "2026-07-16T00:00:02.000000Z",
        "stage_durations": [stage],
        "snapshots": snapshots,
        "sanitized_log_sha256": hashlib.sha256(sanitized_log).hexdigest(),
        "child_exit_code": 0,
        "markers": {"phase8": True, "phase9": True},
        "cleanup": {"status": "passed", "remaining_resources": []},
        "timed_out": False,
        "interrupted": False,
    }
    manifest["manifest_sha256"] = runner.manifest_digest(manifest)
    context = runner.EvidenceContext(
        current_sha=sha,
        current_tree=tree,
        platform=platform,
        child_command=command,
        snapshots=snapshots,
    )
    return manifest, sanitized_log, context


def test_parser_accepts_only_phase9_for_run(tmp_path: Path) -> None:
    runner = load_runner()
    parser = runner.build_parser()
    parsed = parser.parse_args(
        [
            "run",
            "--phase",
            "9",
            "--evidence-dir",
            str(tmp_path / "evidence"),
            "--timeout-seconds",
            "5100",
        ]
    )
    assert parsed.phase == 9
    for invalid in ("0", "8", "10"):
        with pytest.raises(SystemExit):
            parser.parse_args(
                ["run", "--phase", invalid, "--evidence-dir", str(tmp_path / invalid)]
            )


def test_evidence_directory_must_be_absolute_external_and_not_reparsed(tmp_path: Path) -> None:
    runner = load_runner()
    with pytest.raises(runner.GateRunnerError):
        runner.canonical_evidence_dir(Path("relative-evidence"))
    with pytest.raises(runner.GateRunnerError):
        runner.canonical_evidence_dir(ROOT / "phase9-evidence")

    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation is unavailable on this host")
    with pytest.raises(runner.GateRunnerError):
        runner.canonical_evidence_dir(link / "evidence")


def test_reparse_component_rejection_is_enforced_without_host_symlink_support(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = load_runner()
    evidence = tmp_path / "junction" / "evidence"
    junction = evidence.parent
    original = runner._path_is_reparsed
    monkeypatch.setattr(
        runner,
        "_path_is_reparsed",
        lambda path: path == junction or original(path),
    )
    with pytest.raises(runner.GateRunnerError, match="symlink or junction"):
        runner.canonical_evidence_dir(evidence)


def test_sanitizer_allows_only_structured_stages_and_exact_final_markers() -> None:
    runner = load_runner()
    stage = {
        "elapsed_seconds": 0.1,
        "end_utc": "2026-07-16T00:00:00.100000Z",
        "result": "pass",
        "stage": "phase9_static",
        "start_utc": "2026-07-16T00:00:00.000000Z",
    }
    safe = f"FABLE5_PHASE9_STAGE {json.dumps(stage, sort_keys=True, separators=(',', ':'))}"
    assert runner.sanitize_child_line(safe) == safe
    assert (
        runner.sanitize_child_line("Full Compose Phase 8 verification passed.")
        == "Full Compose Phase 8 verification passed."
    )
    assert (
        runner.sanitize_child_line("Full Compose Phase 9 verification passed.")
        == "Full Compose Phase 9 verification passed."
    )
    for unsafe in (
        "AWS_SECRET_ACCESS_KEY=secret",
        "postgres://user:password@example.invalid/db",
        '{"source_payload":"licensed text"}',
        'FABLE5_PHASE9_STAGE {"credential":"secret","stage":"phase9_static"}',
        "FABLE5_PHASE9_STAGE not-json",
        "Full Compose Phase 9 verification passed. extra",
    ):
        assert runner.sanitize_child_line(unsafe) is None


def test_phase6_substages_are_required_without_weakening_stage_validation() -> None:
    runner = load_runner()
    expected = {
        "phase6_schema_cycle",
        "phase6_api",
        "phase6_postgres_tests",
        "phase6_append_only",
    }
    assert expected <= set(runner.REQUIRED_PHASE9_STAGES)

    manifest, sanitized_log, context = valid_bundle(runner)
    required_context = runner.EvidenceContext(
        current_sha=context.current_sha,
        current_tree=context.current_tree,
        platform=context.platform,
        child_command=context.child_command,
        snapshots=context.snapshots,
        required_stages=tuple(sorted(expected)),
    )
    with pytest.raises(runner.GateRunnerError, match="Required Phase 9 stages are missing"):
        runner.validate_bundle(manifest, sanitized_log, required_context)

    failed_stage = dict(manifest["stage_durations"][0])
    failed_stage["stage"] = "phase6_api"
    failed_stage["result"] = "fail"
    start, _, marker8, marker9, end = sanitized_log.decode("utf-8").splitlines()
    failed_line = (
        f"{runner.STAGE_PREFIX}{json.dumps(failed_stage, sort_keys=True, separators=(',', ':'))}"
    )
    failed_log = ("\n".join((start, failed_line, marker8, marker9, end)) + "\n").encode()
    failed_manifest = dict(manifest)
    failed_manifest["stage_durations"] = [failed_stage]
    failed_manifest["sanitized_log_sha256"] = hashlib.sha256(failed_log).hexdigest()
    failed_manifest["manifest_sha256"] = runner.manifest_digest(failed_manifest)
    with pytest.raises(runner.GateRunnerError, match="stage did not pass"):
        runner.validate_bundle(failed_manifest, failed_log, context)


def test_bundle_detects_log_and_manifest_mutation_and_forged_identity() -> None:
    runner = load_runner()
    manifest, sanitized_log, context = valid_bundle(runner)
    runner.validate_bundle(manifest, sanitized_log, context)

    with pytest.raises(runner.GateRunnerError):
        runner.validate_bundle(manifest, sanitized_log + b"mutation\n", context)

    mutated = dict(manifest)
    mutated["child_exit_code"] = 1
    with pytest.raises(runner.GateRunnerError):
        runner.validate_bundle(mutated, sanitized_log, context)

    forged = dict(manifest)
    forged["current_sha"] = "d" * 40
    forged["manifest_sha256"] = runner.manifest_digest(forged)
    with pytest.raises(runner.GateRunnerError):
        runner.validate_bundle(forged, sanitized_log, context)

    forged = dict(manifest)
    forged["platform"] = "linux"
    forged["manifest_sha256"] = runner.manifest_digest(forged)
    with pytest.raises(runner.GateRunnerError):
        runner.validate_bundle(forged, sanitized_log, context)

    forged = dict(manifest)
    forged["run_id"] = "forged-run"
    forged["manifest_sha256"] = runner.manifest_digest(forged)
    with pytest.raises(runner.GateRunnerError):
        runner.validate_bundle(forged, sanitized_log, context)


def test_follow_reports_verified_completion_and_does_not_trust_child_exit_alone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    runner = load_runner()
    manifest, sanitized_log, context = valid_bundle(runner)
    evidence = tmp_path / "follow-evidence"
    evidence.mkdir()
    runner.atomic_write_json(evidence / runner.MANIFEST_NAME, manifest)
    (evidence / runner.SANITIZED_LOG_NAME).write_bytes(sanitized_log)
    monkeypatch.setattr(runner, "_current_evidence_context", lambda: context)

    assert runner.follow_gate(evidence) == 0
    assert '"state":"complete"' in capsys.readouterr().out

    manifest["markers"] = {"phase8": True, "phase9": False}
    manifest["manifest_sha256"] = runner.manifest_digest(manifest)
    runner.atomic_write_json(evidence / runner.MANIFEST_NAME, manifest)
    assert runner.follow_gate(evidence) == 1
    assert '"state":"failed"' in capsys.readouterr().out


def test_nonzero_exit_dirty_state_missing_markers_cleanup_and_snapshot_mismatch_fail() -> None:
    runner = load_runner()
    manifest, sanitized_log, context = valid_bundle(runner)
    mutations = (
        ("child_exit_code", 7),
        ("git_status_pre", " M README.md"),
        ("git_status_post", "?? residue"),
        ("markers", {"phase8": False, "phase9": True}),
        ("cleanup", {"status": "failed", "remaining_resources": ["volume"]}),
        ("snapshots", {"wrong-win32.png": "e" * 64}),
    )
    for key, value in mutations:
        candidate = dict(manifest)
        candidate[key] = value
        candidate["manifest_sha256"] = runner.manifest_digest(candidate)
        with pytest.raises(runner.GateRunnerError):
            runner.validate_bundle(candidate, sanitized_log, context)


def test_platform_snapshot_inventory_is_exactly_24_current_platform_files() -> None:
    runner = load_runner()
    platform = runner.platform_name()
    inventory = runner.snapshot_inventory(ROOT, platform)
    assert len(inventory) == 24
    assert all(name.endswith(f"-{platform}.png") for name in inventory)
    assert all(len(digest) == 64 for digest in inventory.values())


def test_repository_lock_reports_the_active_run_and_follow_command(tmp_path: Path) -> None:
    runner = load_runner()
    active = {
        "run_id": "active-phase9-run",
        "evidence_dir": str(tmp_path / "active-evidence"),
        "pid": 12345,
        "started_at_utc": "2026-07-16T00:00:00.000000Z",
    }
    with runner.acquire_repo_lock(ROOT, active):
        probe = f"""
import importlib.util
import sys
from pathlib import Path
spec = importlib.util.spec_from_file_location('run_phase_gate_probe', {str(RUNNER_PATH)!r})
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
try:
    with module.acquire_repo_lock(Path({str(ROOT)!r}), {{'run_id': 'competitor'}}):
        raise SystemExit(99)
except module.GateRunnerError as exc:
    print(str(exc))
    raise SystemExit(2)
"""
        result = subprocess.run(
            [sys.executable, "-c", probe],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
    assert result.returncode == 2
    assert "active-phase9-run" in result.stdout
    assert "follow --evidence-dir" in result.stdout
    assert str(tmp_path / "active-evidence") in result.stdout


def test_dirty_preflight_fails_under_lock_without_evidence_or_child(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = load_runner()
    evidence = tmp_path / "dirty-evidence"
    monkeypatch.setattr(runner, "git_status", lambda: " M user-owned.txt")
    with pytest.raises(runner.GateRunnerError, match="clean pre-run worktree"):
        runner.run_gate(9, evidence, 5100)
    assert not evidence.exists()


def test_capture_resolves_windows_command_wrappers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = load_runner()
    resolved_npm = r"C:\Program Files\nodejs\npm.CMD"
    captured: dict[str, object] = {}

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        captured["command"] = command
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(command, 0, stdout="11.16.0\n", stderr="")

    monkeypatch.setattr(runner.shutil, "which", lambda command: resolved_npm)
    monkeypatch.setattr(runner.subprocess, "run", fake_run)

    assert runner._capture(["npm", "--version"]) == "11.16.0"
    assert captured["command"] == [resolved_npm, "--version"]
    assert captured["kwargs"] == {
        "capture_output": True,
        "check": True,
        "cwd": ROOT,
        "text": True,
    }


def test_capture_fails_closed_when_command_cannot_be_resolved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = load_runner()
    monkeypatch.setattr(runner.shutil, "which", lambda command: None)

    with pytest.raises(runner.GateRunnerError, match="Required command failed: npm --version"):
        runner._capture(["npm", "--version"])


def test_runner_has_one_spawn_after_lock_and_follow_never_spawns() -> None:
    source = RUNNER_PATH.read_text(encoding="utf-8")
    assert source.count("subprocess.Popen(") == 1
    run_body = source.split("def run_gate(", 1)[1].split("def _parse_runner_events(", 1)[0]
    assert "with acquire_repo_lock" in run_body
    assert "return _run_gate_locked(" in run_body
    locked_body = source.split("def _run_gate_locked(", 1)[1].split("def run_gate(", 1)[0]
    assert locked_body.index("git_status()") < locked_body.index("subprocess.Popen(")
    assert locked_body.index("_docker_resource_inventory()") < locked_body.index(
        "subprocess.Popen("
    )
    follow_body = source.split("def follow_gate(", 1)[1].split("def verify_evidence(", 1)[0]
    assert "Popen" not in follow_body
    assert "verify_phase1.py" not in follow_body


def test_timeout_or_interrupt_signals_same_child_and_does_not_retry() -> None:
    runner = load_runner()

    class FakeChild:
        pid = 24680

        def __init__(self) -> None:
            self.signals: list[int] = []
            self.waits: list[int] = []

        def send_signal(self, signal_number: int) -> None:
            self.signals.append(signal_number)

        def wait(self, timeout: int | None = None) -> int:
            assert timeout is not None
            self.waits.append(timeout)
            return 1

    child = FakeChild()
    runner.signal_child_for_cleanup(child, cleanup_timeout_seconds=300)
    assert len(child.signals) == 1
    assert child.waits == [300]


def test_atomic_json_never_leaves_a_partial_target(tmp_path: Path) -> None:
    runner = load_runner()
    target = tmp_path / "manifest.json"
    runner.atomic_write_json(target, {"run_id": "one"})
    assert json.loads(target.read_text(encoding="utf-8")) == {"run_id": "one"}
    assert not list(tmp_path.glob("*.tmp"))


def test_runner_is_standard_library_only() -> None:
    runner = load_runner()
    imported_roots = runner.imported_module_roots(RUNNER_PATH)
    assert imported_roots <= runner.STANDARD_LIBRARY_MODULES
