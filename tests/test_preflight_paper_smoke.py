from __future__ import annotations

import json
import socket
import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from fable5_paper.phase12.contracts import PaperShadowReadinessArtifact

import scripts.preflight_paper_smoke as preflight

GIT_SHA = "4d70b823947fd61d0ea17df14c9f1ff9f93fd45b"
DATABASE_URL = "postgresql+psycopg://fable5:dev-only@127.0.0.1:5432/fable5"
FIXED_NOW = datetime(2026, 7, 21, 22, 30, 0, 123456, tzinfo=UTC)
KEY_CANARY = "CANARY_KEY_9f3"
SECRET_CANARY = "CANARY_SECRET_7c1"


class _ScalarResult:
    def __init__(self, value: int) -> None:
        self.value = value

    def scalar_one(self) -> int:
        return self.value


class _Connection:
    def __init__(self, repository: _MemoryRepository) -> None:
        self.repository = repository

    def __enter__(self) -> _Connection:
        if not self.repository.reachable:
            raise RuntimeError("database-down-canary")
        return self

    def __exit__(self, *args: object) -> None:
        del args

    def exec_driver_sql(self, statement: str) -> _ScalarResult:
        assert statement == "SELECT 1"
        self.repository.events.append("database")
        return _ScalarResult(1)


class _Engine:
    def __init__(self, repository: _MemoryRepository) -> None:
        self.repository = repository

    def connect(self) -> _Connection:
        return _Connection(self.repository)


class _MemoryRepository:
    def __init__(self, *, reachable: bool = True, events: list[str] | None = None) -> None:
        self.reachable = reachable
        self.events = events if events is not None else []
        self.engine = _Engine(self)
        self.by_key: dict[str, PaperShadowReadinessArtifact] = {}
        self.by_id: dict[UUID, PaperShadowReadinessArtifact] = {}
        self.disposed = False

    @contextmanager
    def serialized_creation(self, key: str) -> Iterator[_MemoryRepository]:
        del key
        yield self

    def find_by_idempotency_key(self, key: str) -> PaperShadowReadinessArtifact | None:
        return self.by_key.get(key)

    def create_readiness(
        self, artifact: PaperShadowReadinessArtifact
    ) -> PaperShadowReadinessArtifact:
        self.events.append("mock")
        self.by_key[artifact.readiness_idempotency_key] = artifact
        self.by_id[artifact.readiness_assessment_id] = artifact
        return artifact

    def get_readiness(self, readiness_assessment_id: UUID) -> PaperShadowReadinessArtifact:
        return self.by_id[readiness_assessment_id]

    def dispose(self) -> None:
        self.disposed = True


def _completed(
    command: tuple[str, ...],
    *,
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(list(command), returncode, stdout, stderr)


def _successful_command_runner(
    calls: list[tuple[str, ...]],
    *,
    child_stdout_canary: str = "",
    child_stderr_canary: str = "",
    overrides: dict[tuple[str, ...], int] | None = None,
) -> Any:
    verifier = (
        sys.executable,
        str(preflight.ROOT / "scripts" / "verify_phase1.py"),
        "--static-only",
        "--phase",
        "26",
    )
    known = {
        ("node", "--version"): "v22.14.0",
        ("docker", "compose", "config", "--quiet"): child_stdout_canary,
        verifier: child_stdout_canary,
        ("git", "rev-parse", "--verify", "HEAD"): GIT_SHA,
        ("git", "status", "--porcelain=v1", "--untracked-files=all"): " M AGENTS.md\n",
    }
    returncodes = overrides or {}

    def run(command: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        assert command in known
        return _completed(
            command,
            returncode=returncodes.get(command, 0),
            stdout=known[command],
            stderr=child_stderr_canary,
        )

    return run


def _prepare_success(
    monkeypatch: pytest.MonkeyPatch,
    *,
    repository: _MemoryRepository | None = None,
    child_stdout_canary: str = "",
    child_stderr_canary: str = "",
    overrides: dict[tuple[str, ...], int] | None = None,
) -> tuple[list[tuple[str, ...]], list[_MemoryRepository]]:
    calls: list[tuple[str, ...]] = []
    repositories: list[_MemoryRepository] = []
    monkeypatch.setattr(preflight, "_current_python_version", lambda: (3, 12, 13))
    monkeypatch.setattr(preflight, "_utc_now", lambda: FIXED_NOW)
    monkeypatch.setattr(
        preflight,
        "_run_command",
        _successful_command_runner(
            calls,
            child_stdout_canary=child_stdout_canary,
            child_stderr_canary=child_stderr_canary,
            overrides=overrides,
        ),
    )

    def new_repository(database_url: str) -> _MemoryRepository:
        assert database_url == DATABASE_URL
        instance = repository if repository is not None else _MemoryRepository()
        repositories.append(instance)
        return instance

    monkeypatch.setattr(preflight, "_new_repository", new_repository)
    monkeypatch.setenv(preflight.DATABASE_URL_ENV_NAME, DATABASE_URL)
    return calls, repositories


def _clear_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in preflight.PAPER_CREDENTIAL_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)


def _report_from_stdout(output: str) -> dict[str, Any]:
    parsed = json.loads(output)
    assert isinstance(parsed, dict)
    return parsed


def _check(report: dict[str, Any], name: str) -> dict[str, Any]:
    return next(item for item in report["checks"] if item["name"] == name)


def _all_object_keys(value: object) -> Iterator[str]:
    if isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from _all_object_keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from _all_object_keys(item)


def test_all_pass_absent_credentials_warns_and_emits_canonical_mock_proof(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls, repositories = _prepare_success(monkeypatch)
    _clear_credentials(monkeypatch)

    def deny_external_socket(*args: object, **kwargs: object) -> socket.socket:
        del args, kwargs
        raise AssertionError("external socket attempted")

    monkeypatch.setattr(socket, "create_connection", deny_external_socket)
    output_path = tmp_path / "preflight.json"

    assert preflight.main(["--output", str(output_path)]) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    assert output_path.read_text(encoding="utf-8") == captured.out

    report = _report_from_stdout(captured.out)
    assert report["overall_status"] == "PASS"
    assert report["credential_pair"] == "ABSENT_PAIR"
    assert report["mock_readiness"] == "MOCK_PROOF_COMPLETE"
    assert report["execution_mode"] == "paper"
    assert report["simulated_paper_only"] is True
    assert report["no_personalized_investment_advice"] is True
    assert report["git_sha"] == GIT_SHA
    assert report["dirty_tree"] is True
    assert report["generated_at_utc"] == "2026-07-21T22:30:00.123456Z"
    assert report["config_sha256"] == preflight.CONFIG_SHA256
    assert report["random_seed"] is None
    assert report["trial_count"] is None
    assert [item["name"] for item in report["checks"]] == list(preflight.CHECK_ORDER)
    assert _check(report, "credential_pair") == {
        "name": "credential_pair",
        "status": "WARN",
        "reason_code": "ABSENT_PAIR",
    }
    assert _check(report, "mock_readiness")["status"] == "PASS"

    body = dict(report)
    report_sha256 = body.pop("report_sha256")
    assert (
        report_sha256 == preflight.hashlib.sha256(preflight.canonical_json_bytes(body)).hexdigest()
    )
    assert output_path.read_bytes() == preflight.canonical_json_bytes(report) + b"\n"

    assert len(repositories) == 1
    repository = repositories[0]
    assert repository.disposed is True
    assert len(repository.by_id) == 1
    artifact = next(iter(repository.by_id.values()))
    assert str(artifact.readiness_assessment_id) == report["mock_readiness_assessment_id"]
    assert artifact.artifact_sha256 == report["mock_readiness_artifact_sha256"]
    assert len(artifact.checks) == 8

    verifier = (
        sys.executable,
        str(preflight.ROOT / "scripts" / "verify_phase1.py"),
        "--static-only",
        "--phase",
        "26",
    )
    assert calls == [
        ("node", "--version"),
        ("docker", "compose", "config", "--quiet"),
        verifier,
        ("git", "rev-parse", "--verify", "HEAD"),
        ("git", "status", "--porcelain=v1", "--untracked-files=all"),
    ]


def test_report_is_byte_deterministic_for_fixed_inputs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _prepare_success(monkeypatch)
    _clear_credentials(monkeypatch)
    first_path = tmp_path / "first.json"
    second_path = tmp_path / "second.json"

    assert preflight.main(["--output", str(first_path)]) == 0
    first_stdout = capsys.readouterr().out
    assert preflight.main(["--output", str(second_path)]) == 0
    second_stdout = capsys.readouterr().out

    assert first_stdout == second_stdout
    assert first_path.read_bytes() == second_path.read_bytes()


def test_credentials_and_captured_child_text_never_leak(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _prepare_success(
        monkeypatch,
        child_stdout_canary=f"{KEY_CANARY}:{SECRET_CANARY}",
        child_stderr_canary=f"{SECRET_CANARY}:{KEY_CANARY}",
    )
    monkeypatch.setenv(preflight.PAPER_CREDENTIAL_ENV_NAMES[0], KEY_CANARY)
    monkeypatch.setenv(preflight.PAPER_CREDENTIAL_ENV_NAMES[1], SECRET_CANARY)
    output_path = tmp_path / "canary-report.json"

    assert preflight.main(["--output", str(output_path)]) == 0
    captured = capsys.readouterr()
    rendered = captured.out + captured.err + output_path.read_text(encoding="utf-8")
    for forbidden in (KEY_CANARY, SECRET_CANARY, "CANARY_KEY", "CANARY_SECRET", "9f3", "7c1"):
        assert forbidden not in rendered
    report = _report_from_stdout(captured.out)
    assert report["credential_pair"] == "PRESENT_PAIR"
    assert _check(report, "credential_pair")["status"] == "PASS"
    assert not any(
        term in key.lower()
        for key in _all_object_keys(json.loads(captured.out))
        for term in (
            "credential_value",
            "credential_length",
            "credential_prefix",
            "credential_suffix",
        )
    )


@pytest.mark.parametrize("present_name", preflight.PAPER_CREDENTIAL_ENV_NAMES)
def test_incomplete_credential_pair_is_sanitized_and_nonzero(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    present_name: str,
) -> None:
    _prepare_success(monkeypatch)
    _clear_credentials(monkeypatch)
    canary = KEY_CANARY if present_name.endswith("ID") else SECRET_CANARY
    monkeypatch.setenv(present_name, canary)

    assert preflight.main([]) == 1
    captured = capsys.readouterr()
    assert captured.err == ""
    assert canary not in captured.out
    report = _report_from_stdout(captured.out)
    assert report["overall_status"] == "FAIL"
    assert report["credential_pair"] == "INCOMPLETE_PAIR"
    assert _check(report, "credential_pair")["status"] == "FAIL"
    assert report["mock_readiness"] == "MOCK_PROOF_COMPLETE"


def test_database_down_is_nonzero_and_leaves_no_partial_artifact(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = _MemoryRepository(reachable=False)
    _prepare_success(monkeypatch, repository=repository)
    _clear_credentials(monkeypatch)

    assert preflight.main([]) == 1
    captured = capsys.readouterr()
    report = _report_from_stdout(captured.out)
    assert captured.err == ""
    assert _check(report, "database_reachability")["reason_code"] == "DATABASE_UNREACHABLE"
    assert _check(report, "mock_readiness")["reason_code"] == "MOCK_PROOF_NOT_RUN"
    assert report["mock_readiness"] == "NOT_PROVEN"
    assert repository.by_key == {}
    assert repository.by_id == {}
    assert repository.disposed is True


@pytest.mark.parametrize(
    "database_url",
    (
        "postgresql+psycopg://fable5:do-not-render@database.example:5432/fable5",
        "postgresql+psycopg://fable5:do-not-render@127.0.0.1:5432/fable5?hostaddr=203.0.113.1",
        "postgresql+psycopg://fable5:do-not-render@127.0.0.1:5432/fable5?host=database.example",
        "postgresql+psycopg://fable5:do-not-render@/fable5"
        "?host=database.example&hostaddr=203.0.113.1",
    ),
)
def test_nonlocal_database_routing_is_rejected_before_construction_or_socket(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    database_url: str,
) -> None:
    _prepare_success(monkeypatch)
    _clear_credentials(monkeypatch)
    monkeypatch.setenv(preflight.DATABASE_URL_ENV_NAME, database_url)

    def forbidden_repository(database_url: str) -> _MemoryRepository:
        del database_url
        raise AssertionError("repository construction was attempted")

    def forbidden_socket(*args: object, **kwargs: object) -> socket.socket:
        del args, kwargs
        raise AssertionError("socket was attempted")

    monkeypatch.setattr(preflight, "_new_repository", forbidden_repository)
    monkeypatch.setattr(socket, "create_connection", forbidden_socket)

    assert preflight.main([]) == 1
    captured = capsys.readouterr()
    assert "do-not-render" not in captured.out + captured.err
    report = _report_from_stdout(captured.out)
    assert _check(report, "database_reachability")["reason_code"] == "DATABASE_URL_NOT_LOCAL"
    assert report["mock_readiness"] == "NOT_PROVEN"


@pytest.mark.parametrize("routing_name", preflight.LIBPQ_ROUTING_ENV_NAMES)
def test_ambient_libpq_routing_is_rejected_before_construction_or_socket(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    routing_name: str,
) -> None:
    _prepare_success(monkeypatch)
    _clear_credentials(monkeypatch)
    monkeypatch.setenv(routing_name, "external-routing-canary")

    def forbidden_repository(database_url: str) -> _MemoryRepository:
        del database_url
        raise AssertionError("repository construction was attempted")

    def forbidden_socket(*args: object, **kwargs: object) -> socket.socket:
        del args, kwargs
        raise AssertionError("socket was attempted")

    monkeypatch.setattr(preflight, "_new_repository", forbidden_repository)
    monkeypatch.setattr(socket, "create_connection", forbidden_socket)

    assert preflight.main([]) == 1
    captured = capsys.readouterr()
    assert "external-routing-canary" not in captured.out + captured.err
    report = _report_from_stdout(captured.out)
    assert _check(report, "database_reachability")["reason_code"] == "DATABASE_URL_NOT_LOCAL"
    assert report["mock_readiness"] == "NOT_PROVEN"


@pytest.mark.parametrize(
    ("version", "status"),
    (((3, 12, 0), "PASS"), ((3, 11, 9), "FAIL"), ((3, 13, 0), "FAIL")),
)
def test_python_version_boundary(
    monkeypatch: pytest.MonkeyPatch, version: tuple[int, int, int], status: str
) -> None:
    monkeypatch.setattr(preflight, "_current_python_version", lambda: version)
    assert preflight._python_version_check().status == status


@pytest.mark.parametrize(
    ("rendered", "status", "reason"),
    (
        ("v22.14.0", "PASS", "NODE_VERSION_SUPPORTED"),
        ("v23.0.0", "PASS", "NODE_VERSION_SUPPORTED"),
        ("v22.13.9", "FAIL", "NODE_VERSION_UNSUPPORTED"),
        (KEY_CANARY, "FAIL", "NODE_VERSION_CHECK_FAILED"),
        (f"v{'9' * 5000}.0.0", "FAIL", "NODE_VERSION_CHECK_FAILED"),
    ),
)
def test_node_version_boundary_discards_raw_output(
    monkeypatch: pytest.MonkeyPatch, rendered: str, status: str, reason: str
) -> None:
    monkeypatch.setattr(
        preflight,
        "_run_command",
        lambda command: _completed(command, stdout=rendered, stderr=SECRET_CANARY),
    )
    check = preflight._node_version_check()
    assert check.status == status
    assert check.reason_code == reason
    assert KEY_CANARY not in json.dumps(check.as_report_value())
    assert SECRET_CANARY not in json.dumps(check.as_report_value())


def test_subprocess_boundary_captures_output_and_scrubs_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(preflight.PAPER_CREDENTIAL_ENV_NAMES[0], KEY_CANARY)
    monkeypatch.setenv(preflight.PAPER_CREDENTIAL_ENV_NAMES[1], SECRET_CANARY)
    monkeypatch.setenv(preflight.DATABASE_URL_ENV_NAME, DATABASE_URL)
    observed: dict[str, object] = {}

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        observed.update(kwargs)
        return subprocess.CompletedProcess(command, 0, "v22.14.0", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = preflight._run_command(("node", "--version"))

    assert result is not None and result.returncode == 0
    environment = observed["env"]
    assert isinstance(environment, dict)
    assert not set(preflight.PAPER_CREDENTIAL_ENV_NAMES) & set(environment)
    assert preflight.DATABASE_URL_ENV_NAME not in environment
    assert observed["capture_output"] is True
    assert observed["shell"] is False
    assert observed["cwd"] == preflight.ROOT


@pytest.mark.parametrize(
    "arguments",
    (
        ["--unknown", KEY_CANARY],
        ["--output", "first.json", "--output", SECRET_CANARY],
        ["--output"],
    ),
)
def test_parser_failures_are_generic_and_never_echo_arguments(
    capsys: pytest.CaptureFixture[str], arguments: list[str]
) -> None:
    assert preflight.main(arguments) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == f"{preflight.FAILURE_MESSAGE}\n"
    assert KEY_CANARY not in captured.err
    assert SECRET_CANARY not in captured.err


def test_help_is_the_only_non_preflight_success_surface(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as raised:
        preflight.main(["--help"])
    assert raised.value.code == 0
    captured = capsys.readouterr()
    assert "PAPER ONLY" in captured.out
    assert captured.err == ""


def test_script_contains_no_external_or_mutating_surface() -> None:
    source = (preflight.ROOT / "scripts" / "preflight_paper_smoke.py").read_text(encoding="utf-8")
    lowered = source.lower()
    for forbidden in (
        "phase12.alpaca",
        "build_alpaca_paper_read_only_adapter",
        "paper-api.alpaca.markets",
        "data.alpaca.markets",
        "--provider",
        "--url",
        "--symbol",
        "requests.",
        "urllib",
        "socket.",
        "submit_order",
        "replace_order",
        "cancel_order",
        "scheduler",
    ):
        assert forbidden not in lowered
