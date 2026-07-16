from __future__ import annotations

import argparse
import ast
import contextlib
import dataclasses
import datetime as dt
import hashlib
import json
import math
import os
import platform
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
import uuid
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any, BinaryIO

ROOT = Path(__file__).resolve().parents[1]
PHASE_8_BASELINE_SHA = "94bcfaabf9de457aec47e49e332865a8dcc74f30"
MANIFEST_SCHEMA_VERSION = "fable5-phase9-evidence-v1"
RAW_LOG_NAME = "phase-gate.raw.log"
SANITIZED_LOG_NAME = "phase-gate.sanitized.log"
HEARTBEAT_NAME = "phase-gate.heartbeat.json"
MANIFEST_NAME = "phase-gate.manifest.json"
STAGE_PREFIX = "FABLE5_PHASE9_STAGE "
RUNNER_EVENT_PREFIX = "RUNNER_EVENT "
PHASE8_MARKER = "Full Compose Phase 8 verification passed."
PHASE9_MARKER = "Full Compose Phase 9 verification passed."
STATIC_MARKERS = {
    "Static repository policy checks passed for Phase 8.",
    "Static repository policy checks passed for Phase 9.",
}
SNAPSHOT_DIRECTORY = ROOT / "services/frontend/e2e/__screenshots__/phase8.visual.spec.ts"
SNAPSHOT_MODES = (
    "idea-intake",
    "research-lab",
    "simulated-paper-status",
    "risk-compliance",
)
SNAPSHOT_STATES = ("mode", "negative")
SNAPSHOT_PROJECTS = ("mobile", "tablet", "desktop")
REQUIRED_PHASE9_STAGES = (
    "phase1_8_static",
    "phase9_static",
    "compose_startup",
    "phase2_acceptance",
    "phase3_acceptance",
    "phase4_acceptance",
    "phase5_acceptance",
    "phase6_acceptance",
    "phase6_schema_cycle",
    "phase6_api",
    "phase6_postgres_tests",
    "phase6_append_only",
    "phase7_acceptance",
    "phase8_acceptance",
    "phase8_timeline_api",
    "phase8_browser_pre_snapshot",
    "phase8_browser_playwright",
    "phase8_browser_post_snapshot",
    "compose_cleanup",
)
STANDARD_LIBRARY_MODULES = {
    "__future__",
    "argparse",
    "ast",
    "collections",
    "contextlib",
    "dataclasses",
    "datetime",
    "fcntl",
    "hashlib",
    "json",
    "math",
    "msvcrt",
    "os",
    "pathlib",
    "platform",
    "re",
    "shutil",
    "signal",
    "stat",
    "subprocess",
    "sys",
    "tempfile",
    "time",
    "typing",
    "uuid",
}


class GateRunnerError(RuntimeError):
    pass


@dataclasses.dataclass(frozen=True)
class EvidenceContext:
    current_sha: str
    current_tree: str
    platform: str
    child_command: list[str]
    snapshots: dict[str, str]
    required_stages: tuple[str, ...] = ()


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def manifest_digest(manifest: dict[str, Any]) -> str:
    payload = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    return sha256_bytes(canonical_json_bytes(payload))


def imported_module_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", 1)[0])
    return roots


def atomic_write_bytes(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("wb") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        if os.name != "nt":
            directory = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)


def atomic_write_json(path: Path, value: object) -> None:
    atomic_write_bytes(path, canonical_json_bytes(value) + b"\n")


def _path_is_reparsed(path: Path) -> bool:
    try:
        metadata = os.lstat(path)
    except FileNotFoundError:
        return False
    if stat.S_ISLNK(metadata.st_mode):
        return True
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    file_attributes = getattr(metadata, "st_file_attributes", 0)
    return bool(reparse_flag and file_attributes & reparse_flag)


def _existing_components(path: Path) -> Iterator[Path]:
    current = path
    components: list[Path] = []
    while True:
        components.append(current)
        if current == current.parent:
            break
        current = current.parent
    yield from reversed(components)


def _is_within(candidate: Path, parent: Path) -> bool:
    try:
        return os.path.commonpath((str(candidate), str(parent))) == str(parent)
    except ValueError:
        return False


def canonical_evidence_dir(path: Path) -> Path:
    if not path.is_absolute():
        raise GateRunnerError("Evidence directory must be an absolute path outside the repository.")

    lexical = Path(os.path.abspath(path))
    lexical_root = Path(os.path.abspath(ROOT))
    if _is_within(lexical, lexical_root):
        raise GateRunnerError("Evidence directory must not be inside the repository.")
    for component in _existing_components(lexical):
        if _path_is_reparsed(component):
            raise GateRunnerError(
                f"Evidence directory must not traverse a symlink or junction: {component}"
            )

    canonical = lexical.resolve(strict=False)
    canonical_root = ROOT.resolve()
    if _is_within(canonical, canonical_root):
        raise GateRunnerError(
            "Evidence directory resolves inside the repository through filesystem indirection."
        )
    if canonical.exists() and not canonical.is_dir():
        raise GateRunnerError("Evidence path exists but is not a directory.")
    return canonical


def _lock_paths(repo_root: Path) -> tuple[Path, Path]:
    canonical = str(repo_root.resolve())
    if os.name == "nt":
        canonical = canonical.casefold()
    key = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    root = Path(tempfile.gettempdir())
    return root / f"fable5-phase-gate-{key}.lock", root / f"fable5-phase-gate-{key}.json"


def _lock_nonblocking(handle: BinaryIO) -> None:
    if os.name == "nt":
        import msvcrt

        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"\0")
            handle.flush()
        handle.seek(0)
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as exc:
            raise BlockingIOError from exc
    else:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock(handle: BinaryIO) -> None:
    if os.name == "nt":
        import msvcrt

        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


@contextlib.contextmanager
def acquire_repo_lock(repo_root: Path, active_record: dict[str, object]) -> Iterator[None]:
    lock_path, record_path = _lock_paths(repo_root)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = lock_path.open("a+b")
    try:
        try:
            _lock_nonblocking(handle)
        except BlockingIOError as exc:
            active: dict[str, object] = {}
            for _ in range(10):
                time.sleep(0.05)
                try:
                    candidate = json.loads(record_path.read_text(encoding="utf-8"))
                except (FileNotFoundError, json.JSONDecodeError, OSError):
                    continue
                if isinstance(candidate, dict) and candidate.get("run_id"):
                    active = candidate
                    break
            active_run = str(active.get("run_id", "unknown"))
            evidence_dir = str(active.get("evidence_dir", "unknown"))
            follow_command = subprocess.list2cmdline(
                [
                    sys.executable,
                    "scripts/run_phase_gate.py",
                    "follow",
                    "--evidence-dir",
                    evidence_dir,
                ]
            )
            raise GateRunnerError(
                "A Phase 9 verifier is already active for this canonical repository. "
                f"Active run: {active_run}. Follow it with: {follow_command}"
            ) from exc

        atomic_write_json(record_path, active_record)
        try:
            yield
        finally:
            try:
                existing = json.loads(record_path.read_text(encoding="utf-8"))
            except (FileNotFoundError, json.JSONDecodeError, OSError):
                existing = {}
            if existing.get("run_id") == active_record.get("run_id"):
                record_path.unlink(missing_ok=True)
            _unlock(handle)
    finally:
        handle.close()


def platform_name() -> str:
    if sys.platform == "win32":
        return "win32"
    if sys.platform.startswith("linux"):
        return "linux"
    raise GateRunnerError(f"Phase 9 evidence supports only win32 and Linux, not {sys.platform}.")


def snapshot_inventory(repo_root: Path, target_platform: str) -> dict[str, str]:
    if target_platform not in {"win32", "linux"}:
        raise GateRunnerError(f"Unsupported snapshot platform: {target_platform}")
    directory = repo_root / SNAPSHOT_DIRECTORY.relative_to(ROOT)
    expected = {
        f"{mode}-{state}-{project}-{target_platform}.png"
        for mode in SNAPSHOT_MODES
        for state in SNAPSHOT_STATES
        for project in SNAPSHOT_PROJECTS
    }
    actual = {path.name for path in directory.glob(f"*-{target_platform}.png")}
    if actual != expected:
        missing = sorted(expected - actual)
        unexpected = sorted(actual - expected)
        raise GateRunnerError(
            f"Platform snapshot inventory mismatch: missing={missing}, unexpected={unexpected}"
        )
    return {name: sha256_bytes((directory / name).read_bytes()) for name in sorted(expected)}


def _parse_utc(value: object) -> dt.datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise GateRunnerError(f"Expected an explicit UTC timestamp, got {value!r}.")
    try:
        parsed = dt.datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise GateRunnerError(f"Invalid UTC timestamp: {value!r}") from exc
    if parsed.utcoffset() != dt.timedelta(0):
        raise GateRunnerError(f"Timestamp is not UTC: {value!r}")
    return parsed


def _parse_stage_line(line: str) -> dict[str, object]:
    try:
        stage = json.loads(line.removeprefix(STAGE_PREFIX))
    except json.JSONDecodeError as exc:
        raise GateRunnerError("Malformed Phase 9 stage marker.") from exc
    expected_fields = {
        "stage",
        "start_utc",
        "end_utc",
        "elapsed_seconds",
        "result",
    }
    if not isinstance(stage, dict) or set(stage) != expected_fields:
        raise GateRunnerError("Phase 9 stage marker has unexpected fields.")
    name = stage["stage"]
    elapsed = stage["elapsed_seconds"]
    if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9_]+", name):
        raise GateRunnerError("Phase 9 stage name is not sanitized.")
    if not isinstance(elapsed, (int, float)) or isinstance(elapsed, bool):
        raise GateRunnerError("Phase 9 stage duration is not numeric.")
    if not math.isfinite(float(elapsed)) or float(elapsed) < 0:
        raise GateRunnerError("Phase 9 stage duration is invalid.")
    if stage["result"] not in {"pass", "fail"}:
        raise GateRunnerError("Phase 9 stage result must be pass or fail.")
    start = _parse_utc(stage["start_utc"])
    end = _parse_utc(stage["end_utc"])
    if end < start:
        raise GateRunnerError("Phase 9 stage ends before it starts.")
    return stage


def sanitize_child_line(line: str) -> str | None:
    stripped = line.rstrip("\r\n")
    if stripped in {PHASE8_MARKER, PHASE9_MARKER, *STATIC_MARKERS}:
        return stripped
    if not stripped.startswith(STAGE_PREFIX):
        return None
    try:
        stage = _parse_stage_line(stripped)
    except GateRunnerError:
        return None
    return STAGE_PREFIX + canonical_json_bytes(stage).decode("utf-8")


def _append_line(path: Path, line: str) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(line + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _runner_event(event: str, **values: object) -> str:
    payload = {"event": event, **values}
    return RUNNER_EVENT_PREFIX + canonical_json_bytes(payload).decode("utf-8")


def _drain_raw_log(
    raw_path: Path,
    offset: int,
    pending: bytes,
    sanitized_path: Path,
    stages: list[dict[str, object]],
    markers: dict[str, bool],
    *,
    final: bool,
) -> tuple[int, bytes]:
    with raw_path.open("rb") as handle:
        handle.seek(offset)
        new_bytes = handle.read()
    offset += len(new_bytes)
    buffer = pending + new_bytes
    lines = buffer.split(b"\n")
    if final:
        pending = b""
        if lines[-1:] == [b""]:
            lines.pop()
    else:
        pending = lines.pop()
    for raw_line in lines:
        candidate = raw_line.decode("utf-8", errors="replace").rstrip("\r")
        safe = sanitize_child_line(candidate)
        if safe is None:
            continue
        _append_line(sanitized_path, safe)
        if safe.startswith(STAGE_PREFIX):
            stages.append(_parse_stage_line(safe))
        elif safe == PHASE8_MARKER:
            markers["phase8"] = True
        elif safe == PHASE9_MARKER:
            markers["phase9"] = True
    return offset, pending


def _capture(command: Sequence[str], *, cwd: Path = ROOT) -> str:
    logical_command = list(command)
    executable = shutil.which(logical_command[0])
    if executable is None:
        raise GateRunnerError(f"Required command failed: {' '.join(logical_command)}")
    try:
        return subprocess.run(
            [executable, *logical_command[1:]],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise GateRunnerError(f"Required command failed: {' '.join(logical_command)}") from exc


def git_status(repo_root: Path = ROOT) -> str:
    return _capture(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=repo_root,
    )


def git_identity(repo_root: Path = ROOT) -> tuple[str, str]:
    sha = _capture(["git", "rev-parse", "HEAD"], cwd=repo_root)
    tree = _capture(["git", "show", "-s", "--format=%T", "HEAD"], cwd=repo_root)
    return sha, tree


def child_command() -> list[str]:
    return [sys.executable, str(ROOT / "scripts/verify_phase1.py"), "--phase", "9"]


def tool_versions() -> dict[str, str]:
    return {
        "python": platform.python_version(),
        "git": _capture(["git", "--version"]),
        "node": _capture(["node", "--version"]),
        "npm": _capture(["npm", "--version"]),
        "docker": _capture(["docker", "--version"]),
        "docker_compose": _capture(["docker", "compose", "version"]),
    }


def _docker_resource_inventory() -> list[str]:
    commands = (
        (
            "container",
            ["docker", "ps", "-a", "--filter", "name=fable5_acceptance_", "--format", "{{.Names}}"],
        ),
        (
            "network",
            [
                "docker",
                "network",
                "ls",
                "--filter",
                "name=fable5_acceptance_",
                "--format",
                "{{.Name}}",
            ],
        ),
        (
            "volume",
            [
                "docker",
                "volume",
                "ls",
                "--filter",
                "name=fable5_acceptance_",
                "--format",
                "{{.Name}}",
            ],
        ),
    )
    resources: list[str] = []
    for kind, command in commands:
        output = _capture(command)
        resources.extend(f"{kind}:{name}" for name in output.splitlines() if name)
    return sorted(resources)


def signal_child_for_cleanup(child: Any, *, cleanup_timeout_seconds: int) -> int:
    interrupt_signal = signal.CTRL_BREAK_EVENT if os.name == "nt" else signal.SIGINT
    child.send_signal(interrupt_signal)
    try:
        return int(child.wait(timeout=cleanup_timeout_seconds))
    except subprocess.TimeoutExpired:
        child.terminate()
        try:
            return int(child.wait(timeout=30))
        except subprocess.TimeoutExpired:
            child.kill()
            return int(child.wait(timeout=30))


def _write_heartbeat(
    evidence_dir: Path,
    *,
    run_id: str,
    pid: int | None,
    state: str,
    started_at_utc: str,
) -> None:
    atomic_write_json(
        evidence_dir / HEARTBEAT_NAME,
        {
            "evidence_dir": str(evidence_dir),
            "heartbeat_at_utc": utc_now(),
            "pid": pid,
            "run_id": run_id,
            "started_at_utc": started_at_utc,
            "state": state,
        },
    )


def _prepare_evidence_directory(path: Path) -> None:
    if path.exists() and any(path.iterdir()):
        raise GateRunnerError(
            "Evidence directory must be new or empty; existing evidence is immutable."
        )
    path.mkdir(parents=True, exist_ok=True)


def _run_gate_locked(
    evidence_dir: Path,
    run_id: str,
    started_at: str,
    active_record: dict[str, object],
    timeout_seconds: int,
) -> int:
    pre_status = git_status()
    if pre_status:
        raise GateRunnerError(f"Phase 9 runner requires a clean pre-run worktree: {pre_status!r}")
    _prepare_evidence_directory(evidence_dir)
    _write_heartbeat(
        evidence_dir,
        run_id=run_id,
        pid=None,
        state="preflight",
        started_at_utc=started_at,
    )

    sha, tree = git_identity()
    target_platform = platform_name()
    snapshots = snapshot_inventory(ROOT, target_platform)
    versions = tool_versions()
    existing_resources = _docker_resource_inventory()
    if existing_resources:
        raise GateRunnerError(
            "Pre-existing verifier resources make cleanup ownership ambiguous: "
            + ", ".join(existing_resources)
        )

    raw_path = evidence_dir / RAW_LOG_NAME
    sanitized_path = evidence_dir / SANITIZED_LOG_NAME
    raw_path.touch(exist_ok=False)
    sanitized_path.touch(exist_ok=False)
    command = child_command()
    start_event = _runner_event(
        "start",
        platform=target_platform,
        run_id=run_id,
        sha=sha,
        tree=tree,
    )
    _append_line(sanitized_path, start_event)
    child_exit_code = 1
    timed_out = False
    interrupted = False
    stages: list[dict[str, object]] = []
    markers = {"phase8": False, "phase9": False}
    offset = 0
    pending = b""
    creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    with raw_path.open("ab", buffering=0) as raw_handle:
        child = subprocess.Popen(
            command,
            cwd=ROOT,
            env={**os.environ, "FABLE5_VERIFY_PHASE": "9"},
            stdout=raw_handle,
            stderr=subprocess.STDOUT,
            creationflags=creation_flags,
            start_new_session=os.name != "nt",
        )
        active_record["pid"] = child.pid
        _, record_path = _lock_paths(ROOT)
        atomic_write_json(record_path, active_record)
        _write_heartbeat(
            evidence_dir,
            run_id=run_id,
            pid=child.pid,
            state="running",
            started_at_utc=started_at,
        )
        deadline = time.monotonic() + timeout_seconds
        next_heartbeat = time.monotonic() + 5
        try:
            while child.poll() is None:
                offset, pending = _drain_raw_log(
                    raw_path,
                    offset,
                    pending,
                    sanitized_path,
                    stages,
                    markers,
                    final=False,
                )
                now = time.monotonic()
                if now >= deadline:
                    timed_out = True
                    child_exit_code = signal_child_for_cleanup(
                        child,
                        cleanup_timeout_seconds=300,
                    )
                    break
                if now >= next_heartbeat:
                    _write_heartbeat(
                        evidence_dir,
                        run_id=run_id,
                        pid=child.pid,
                        state="running",
                        started_at_utc=started_at,
                    )
                    next_heartbeat = now + 5
                time.sleep(1)
            else:
                child_exit_code = int(child.returncode)
            if child.poll() is not None:
                child_exit_code = int(child.returncode)
        except KeyboardInterrupt:
            interrupted = True
            child_exit_code = signal_child_for_cleanup(
                child,
                cleanup_timeout_seconds=300,
            )
        finally:
            raw_handle.flush()

    offset, pending = _drain_raw_log(
        raw_path,
        offset,
        pending,
        sanitized_path,
        stages,
        markers,
        final=True,
    )
    del offset, pending

    post_status = git_status()
    remaining_resources = _docker_resource_inventory()
    cleanup = {
        "remaining_resources": remaining_resources,
        "status": "passed" if not remaining_resources else "failed",
    }
    ended_at = utc_now()
    _append_line(sanitized_path, _runner_event("end", run_id=run_id))
    sanitized_bytes = sanitized_path.read_bytes()
    manifest: dict[str, Any] = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "phase": 9,
        "run_id": run_id,
        "phase_8_baseline_sha": PHASE_8_BASELINE_SHA,
        "current_sha": sha,
        "current_tree": tree,
        "git_status_pre": pre_status,
        "git_status_post": post_status,
        "child_command": command,
        "platform": target_platform,
        "tool_versions": versions,
        "started_at_utc": started_at,
        "ended_at_utc": ended_at,
        "stage_durations": stages,
        "snapshots": snapshots,
        "sanitized_log_sha256": sha256_bytes(sanitized_bytes),
        "child_exit_code": child_exit_code,
        "markers": markers,
        "cleanup": cleanup,
        "timed_out": timed_out,
        "interrupted": interrupted,
    }
    manifest["manifest_sha256"] = manifest_digest(manifest)
    atomic_write_json(evidence_dir / MANIFEST_NAME, manifest)

    context = EvidenceContext(
        current_sha=sha,
        current_tree=tree,
        platform=target_platform,
        child_command=command,
        snapshots=snapshots,
        required_stages=REQUIRED_PHASE9_STAGES,
    )
    try:
        validate_bundle(manifest, sanitized_bytes, context)
    except GateRunnerError:
        _write_heartbeat(
            evidence_dir,
            run_id=run_id,
            pid=None,
            state="failed",
            started_at_utc=started_at,
        )
        return 1
    _write_heartbeat(
        evidence_dir,
        run_id=run_id,
        pid=None,
        state="complete",
        started_at_utc=started_at,
    )
    return 0


def run_gate(phase: int, evidence_path: Path, timeout_seconds: int) -> int:
    if phase != 9:
        raise GateRunnerError("The release-acceptance runner supports Phase 9 only.")
    if timeout_seconds <= 0:
        raise GateRunnerError("Timeout must be a positive number of seconds.")
    evidence_dir = canonical_evidence_dir(evidence_path)
    run_id = uuid.uuid4().hex
    started_at = utc_now()
    active_record: dict[str, object] = {
        "evidence_dir": str(evidence_dir),
        "pid": None,
        "run_id": run_id,
        "started_at_utc": started_at,
    }
    with acquire_repo_lock(ROOT, active_record):
        return _run_gate_locked(
            evidence_dir,
            run_id,
            started_at,
            active_record,
            timeout_seconds,
        )


def _parse_runner_events(lines: list[str]) -> tuple[dict[str, object], dict[str, object]]:
    events: list[dict[str, object]] = []
    for line in lines:
        if not line.startswith(RUNNER_EVENT_PREFIX):
            continue
        try:
            event = json.loads(line.removeprefix(RUNNER_EVENT_PREFIX))
        except json.JSONDecodeError as exc:
            raise GateRunnerError("Sanitized log contains a malformed runner event.") from exc
        if not isinstance(event, dict):
            raise GateRunnerError("Sanitized runner event is not an object.")
        events.append(event)
    if len(events) != 2 or events[0].get("event") != "start" or events[1].get("event") != "end":
        raise GateRunnerError("Sanitized log must contain exactly one start and one end event.")
    if set(events[0]) != {"event", "platform", "run_id", "sha", "tree"}:
        raise GateRunnerError("Runner start event contains unexpected fields.")
    if set(events[1]) != {"event", "run_id"}:
        raise GateRunnerError("Runner end event contains unexpected fields.")
    return events[0], events[1]


def validate_bundle(
    manifest: dict[str, Any],
    sanitized_log: bytes,
    context: EvidenceContext,
) -> None:
    required_fields = {
        "schema_version",
        "phase",
        "run_id",
        "phase_8_baseline_sha",
        "current_sha",
        "current_tree",
        "git_status_pre",
        "git_status_post",
        "child_command",
        "platform",
        "tool_versions",
        "started_at_utc",
        "ended_at_utc",
        "stage_durations",
        "snapshots",
        "sanitized_log_sha256",
        "child_exit_code",
        "markers",
        "cleanup",
        "timed_out",
        "interrupted",
        "manifest_sha256",
    }
    if set(manifest) != required_fields:
        raise GateRunnerError("Evidence manifest fields do not match the frozen schema.")
    if manifest.get("manifest_sha256") != manifest_digest(manifest):
        raise GateRunnerError("Evidence manifest was mutated.")
    if manifest.get("sanitized_log_sha256") != sha256_bytes(sanitized_log):
        raise GateRunnerError("Sanitized evidence log was mutated.")

    try:
        text = sanitized_log.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise GateRunnerError("Sanitized evidence log is not UTF-8.") from exc
    if not text.endswith("\n"):
        raise GateRunnerError("Sanitized evidence log is not newline-terminated.")
    lines = text.splitlines()
    start_event, end_event = _parse_runner_events(lines)
    for line in lines:
        if line.startswith(RUNNER_EVENT_PREFIX):
            continue
        safe = sanitize_child_line(line)
        if safe is None or safe != line:
            raise GateRunnerError("Sanitized evidence contains an unapproved line.")

    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION or manifest.get("phase") != 9:
        raise GateRunnerError("Evidence does not use the Phase 9 schema.")
    if manifest.get("phase_8_baseline_sha") != PHASE_8_BASELINE_SHA:
        raise GateRunnerError("Evidence binds the wrong Phase 8 baseline.")
    if manifest.get("current_sha") != context.current_sha:
        raise GateRunnerError("Evidence SHA does not match the current commit.")
    if manifest.get("current_tree") != context.current_tree:
        raise GateRunnerError("Evidence tree does not match the current commit.")
    if manifest.get("platform") != context.platform:
        raise GateRunnerError("Evidence platform does not match the verifier host.")
    if manifest.get("child_command") != context.child_command:
        raise GateRunnerError("Evidence child command is not exact.")
    if manifest.get("snapshots") != context.snapshots:
        raise GateRunnerError("Evidence snapshot names or hashes do not match the platform corpus.")
    if manifest.get("git_status_pre") != "" or manifest.get("git_status_post") != "":
        raise GateRunnerError("Evidence records a dirty pre-run or post-run worktree.")
    if manifest.get("child_exit_code") != 0:
        raise GateRunnerError("Verifier child exited nonzero.")
    if manifest.get("timed_out") is not False or manifest.get("interrupted") is not False:
        raise GateRunnerError("Timed out or interrupted evidence cannot pass.")
    if manifest.get("markers") != {"phase8": True, "phase9": True}:
        raise GateRunnerError("Inherited Phase 8 or final Phase 9 marker is missing.")
    if manifest.get("cleanup") != {"status": "passed", "remaining_resources": []}:
        raise GateRunnerError("Verifier cleanup did not prove an empty resource set.")

    run_id = manifest.get("run_id")
    if not isinstance(run_id, str) or not run_id:
        raise GateRunnerError("Evidence run ID is missing.")
    if start_event.get("run_id") != run_id or end_event.get("run_id") != run_id:
        raise GateRunnerError("Evidence run ID conflicts with the sanitized log.")
    if (
        start_event.get("sha") != context.current_sha
        or start_event.get("tree") != context.current_tree
        or start_event.get("platform") != context.platform
    ):
        raise GateRunnerError("Sanitized start event conflicts with manifest identity.")
    if PHASE8_MARKER not in lines or PHASE9_MARKER not in lines:
        raise GateRunnerError("Sanitized evidence is missing a final marker.")

    started = _parse_utc(manifest.get("started_at_utc"))
    ended = _parse_utc(manifest.get("ended_at_utc"))
    if ended < started:
        raise GateRunnerError("Evidence end precedes its start.")
    tools = manifest.get("tool_versions")
    if (
        not isinstance(tools, dict)
        or not tools
        or any(
            not isinstance(key, str) or not isinstance(value, str) or not value
            for key, value in tools.items()
        )
    ):
        raise GateRunnerError("Tool-version evidence is incomplete.")

    log_stages = [_parse_stage_line(line) for line in lines if line.startswith(STAGE_PREFIX)]
    if manifest.get("stage_durations") != log_stages or not log_stages:
        raise GateRunnerError("Stage durations do not match the sanitized stage log.")
    if any(stage.get("result") != "pass" for stage in log_stages):
        raise GateRunnerError("A Phase 9 stage did not pass.")
    stage_names = [str(stage["stage"]) for stage in log_stages]
    if len(stage_names) != len(set(stage_names)):
        raise GateRunnerError("Phase 9 stage names are duplicated.")
    missing_stages = sorted(set(context.required_stages) - set(stage_names))
    if missing_stages:
        raise GateRunnerError(f"Required Phase 9 stages are missing: {missing_stages}")


def _current_evidence_context() -> EvidenceContext:
    status = git_status()
    if status:
        raise GateRunnerError(f"Evidence verification requires a clean worktree: {status!r}")
    sha, tree = git_identity()
    target_platform = platform_name()
    return EvidenceContext(
        current_sha=sha,
        current_tree=tree,
        platform=target_platform,
        child_command=child_command(),
        snapshots=snapshot_inventory(ROOT, target_platform),
        required_stages=REQUIRED_PHASE9_STAGES,
    )


def follow_gate(evidence_path: Path) -> int:
    evidence_dir = canonical_evidence_dir(evidence_path)
    if not evidence_dir.is_dir():
        raise GateRunnerError("Evidence directory does not exist.")
    sanitized_path = evidence_dir / SANITIZED_LOG_NAME
    if sanitized_path.is_file():
        sys.stdout.write(sanitized_path.read_text(encoding="utf-8"))
    manifest_path = evidence_dir / MANIFEST_NAME
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise GateRunnerError("Evidence manifest is not valid JSON.") from exc
        if not isinstance(manifest, dict):
            raise GateRunnerError("Evidence manifest is not an object.")
        passed = False
        if sanitized_path.is_file():
            try:
                validate_bundle(
                    manifest,
                    sanitized_path.read_bytes(),
                    _current_evidence_context(),
                )
            except GateRunnerError:
                pass
            else:
                passed = True
        print(
            canonical_json_bytes(
                {
                    "child_exit_code": manifest.get("child_exit_code"),
                    "run_id": manifest.get("run_id"),
                    "state": "complete" if passed else "failed",
                }
            ).decode("utf-8")
        )
        return 0 if passed else 1
    heartbeat_path = evidence_dir / HEARTBEAT_NAME
    if not heartbeat_path.is_file():
        raise GateRunnerError("No heartbeat or manifest exists for this evidence directory.")
    print(heartbeat_path.read_text(encoding="utf-8").strip())
    return 0


def verify_evidence(evidence_path: Path) -> int:
    evidence_dir = canonical_evidence_dir(evidence_path)
    manifest_path = evidence_dir / MANIFEST_NAME
    sanitized_path = evidence_dir / SANITIZED_LOG_NAME
    if not manifest_path.is_file() or not sanitized_path.is_file():
        raise GateRunnerError("Evidence bundle is missing its manifest or sanitized log.")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise GateRunnerError("Evidence manifest is not valid JSON.") from exc
    if not isinstance(manifest, dict):
        raise GateRunnerError("Evidence manifest is not an object.")
    validate_bundle(manifest, sanitized_path.read_bytes(), _current_evidence_context())
    print(
        "Verified Phase 9 evidence "
        f"run={manifest['run_id']} manifest_sha256={manifest['manifest_sha256']}"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run and verify the single-flight Phase 9 gate.")
    commands = parser.add_subparsers(dest="command", required=True)

    run_parser = commands.add_parser("run")
    run_parser.add_argument("--phase", type=int, choices=(9,), required=True)
    run_parser.add_argument("--evidence-dir", type=Path, required=True)
    run_parser.add_argument("--timeout-seconds", type=int, default=6300)

    follow_parser = commands.add_parser("follow")
    follow_parser.add_argument("--evidence-dir", type=Path, required=True)

    verify_parser = commands.add_parser("verify-evidence")
    verify_parser.add_argument("--evidence-dir", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "run":
            return run_gate(args.phase, args.evidence_dir, args.timeout_seconds)
        if args.command == "follow":
            return follow_gate(args.evidence_dir)
        if args.command == "verify-evidence":
            return verify_evidence(args.evidence_dir)
        raise GateRunnerError(f"Unsupported command: {args.command}")
    except GateRunnerError as exc:
        print(f"Phase 9 gate runner failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
