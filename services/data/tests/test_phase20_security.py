from __future__ import annotations

import ast
import importlib.util
import json
import socket
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest
from fable5_data.phase20.input_register import (
    build_family_a_evaluation_holdout_input_register,
    canonical_evaluation_holdout_input_register_bytes,
)

ROOT = Path(__file__).resolve().parents[3]
GENERATOR = ROOT / "scripts/generate_family_a_evaluation_holdout_input_register.py"
VERIFIER = ROOT / "scripts/verify_family_a_evaluation_holdout_input_register.py"
FAILURE = "Family A evaluation/holdout input-register verification failed.\n"


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    result: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.update(item.name for item in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            result.add(node.module)
    return result


def _load_verifier() -> ModuleType:
    spec = importlib.util.spec_from_file_location("phase20_test_verifier", VERIFIER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_domain_is_database_network_environment_clock_random_subprocess_and_git_free() -> None:
    root = Path("services/data/src/fable5_data/phase20")
    imports = set().union(*(_imports(path) for path in root.glob("*.py")))
    forbidden = (
        "aiohttp",
        "fastapi",
        "fable5_api",
        "fable5_jobs",
        "fable5_paper",
        "fable5_research",
        "http",
        "httpx",
        "os",
        "psycopg",
        "random",
        "redis",
        "requests",
        "rq",
        "socket",
        "sqlalchemy",
        "sqlite3",
        "subprocess",
        "time",
        "urllib",
    )
    assert not {
        name
        for name in imports
        if any(name == item or name.startswith(f"{item}.") for item in forbidden)
    }
    source = "\n".join(path.read_text(encoding="utf-8") for path in root.glob("*.py"))
    for forbidden_text in (
        "datetime.now",
        "datetime.utcnow",
        "getenv",
        "environ",
        "uuid4",
        "git ",
        "create_engine",
        "glob(",
        "rglob(",
    ):
        assert forbidden_text not in source


def test_builder_succeeds_while_network_entrypoints_are_denied(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempted: list[str] = []

    def deny(*args: object, **kwargs: object) -> None:
        del args, kwargs
        attempted.append("network")
        raise AssertionError("Phase 20 attempted network access")

    monkeypatch.setattr(socket, "create_connection", deny)
    monkeypatch.setattr(socket.socket, "connect", deny)

    artifact = build_family_a_evaluation_holdout_input_register()
    assert attempted == []
    assert artifact.runtime_network_disabled is True
    assert artifact.operational_external_request_performed is False
    assert artifact.provider_data_request_performed is False


def test_ambient_environment_cannot_change_canonical_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    before = canonical_evaluation_holdout_input_register_bytes()
    monkeypatch.setenv("FABLE5_PHASE20_FAKE_CREDENTIAL", "phase20-secret-canary")
    monkeypatch.setenv("DATABASE_URL", "postgresql://phase20-secret-canary")
    monkeypatch.setenv("HTTP_PROXY", "http://phase20-secret-canary.invalid")

    after = canonical_evaluation_holdout_input_register_bytes()
    assert after == before
    assert b"phase20-secret-canary" not in after


def test_artifact_contains_no_credential_payload_observation_or_policy_instance() -> None:
    artifact = build_family_a_evaluation_holdout_input_register()
    rendered = json.dumps(artifact.model_dump(mode="json"), sort_keys=True).casefold()

    for forbidden in (
        "api_key",
        "api token",
        "authorization header",
        "secret key",
        "account number",
        "raw price payload",
        "provider body",
        "contract body",
        "observation_value",
        "qualification_artifact_set_sha256",
    ):
        assert forbidden not in rendered
    assert artifact.provider_payload_persisted is False
    assert artifact.licensed_data_persisted is False
    assert artifact.external_sample_qualified is False
    assert artifact.confirmation_holdout_defined is False


def test_cli_sources_install_and_actively_prove_offline_boundaries() -> None:
    source = "\n".join(path.read_text(encoding="utf-8") for path in (GENERATOR, VERIFIER))
    for path in (GENERATOR, VERIFIER):
        cli_source = path.read_text(encoding="utf-8")
        assert "sys.addaudithook(_offline_audit_hook)" in cli_source
        assert 'event.startswith("socket.")' in cli_source
        assert 'frozenset({"os.system", "subprocess.Popen"})' in cli_source
        assert "_prove_socket_construction_is_denied()" in cli_source
        assert "_prove_subprocess_construction_is_denied()" in cli_source
    assert "FABLE5_" not in source
    assert "getenv" not in source
    assert "environ" not in source
    assert "database_url" not in source.casefold()
    for forbidden_argument in (
        "--output",
        "--provider",
        "--url",
        "--source",
        "--status",
        "--policy",
        "--holdout",
        "--clock",
        "--time",
        "--hash",
        "--credential",
        "--account",
        "--entitlement",
        "--rights",
        "--data",
        "--authority",
        "--repair",
        "--expected-hash",
        "--capture",
        "--ingestion",
        "--research",
        "--order",
    ):
        assert forbidden_argument not in source


def test_verifier_source_uses_component_handles_instead_of_path_reopen() -> None:
    source = VERIFIER.read_text(encoding="utf-8")
    for required in (
        "dir_fd=parent_descriptor",
        'getattr(os, "O_DIRECTORY", 0)',
        'getattr(os, "O_NOFOLLOW", 0)',
        "_WINDOWS_FILE_FLAG_OPEN_REPARSE_POINT",
        "_WINDOWS_FILE_SHARE_READ | _WINDOWS_FILE_SHARE_WRITE",
        "msvcrt.open_osfhandle(",
    ):
        assert required in source
    for forbidden in (".resolve(", ".realpath(", ".lstat("):
        assert forbidden not in source


@pytest.mark.parametrize("directory", [False, True])
def test_windows_component_open_policy_never_shares_delete(
    monkeypatch: pytest.MonkeyPatch,
    directory: bool,
) -> None:
    verifier = _load_verifier()
    calls: list[tuple[int, int, int]] = []

    def fake_create_file(
        path_text: str,
        desired_access: int,
        share_mode: int,
        flags_and_attributes: int,
    ) -> int:
        del path_text
        calls.append((desired_access, share_mode, flags_and_attributes))
        return 123

    monkeypatch.setattr(verifier, "_windows_create_file", fake_create_file)
    assert verifier._windows_open_component(r"C:\trusted\candidate", directory=directory) == 123
    assert len(calls) == 1
    access, share_mode, flags = calls[0]
    assert access & verifier._WINDOWS_FILE_READ_ATTRIBUTES
    assert bool(access & verifier._WINDOWS_GENERIC_READ) is (not directory)
    assert share_mode == verifier._WINDOWS_FILE_SHARE_READ | verifier._WINDOWS_FILE_SHARE_WRITE
    assert flags & verifier._WINDOWS_FILE_FLAG_OPEN_REPARSE_POINT
    assert bool(flags & verifier._WINDOWS_FILE_FLAG_BACKUP_SEMANTICS) is directory


def test_windows_trusted_root_reparse_does_not_allow_descendant_reparse_descent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    verifier = _load_verifier()
    opened: list[tuple[str, bool]] = []
    closed: list[int] = []

    def fake_open_component(path_text: str, *, directory: bool) -> int:
        opened.append((path_text, directory))
        return 100 + len(opened)

    def fake_attribute_tag(handle: int) -> tuple[int, int]:
        assert handle in {101, 102}
        return (
            verifier._WINDOWS_FILE_ATTRIBUTE_DIRECTORY
            | verifier._WINDOWS_FILE_ATTRIBUTE_REPARSE_POINT,
            0xA000000C,
        )

    def fake_fingerprint(handle: int) -> tuple[int, ...]:
        return (7, 0, handle, verifier._WINDOWS_FILE_ATTRIBUTE_DIRECTORY, 0, 0, 0, 0)

    monkeypatch.setattr(verifier, "_windows_open_component", fake_open_component)
    monkeypatch.setattr(verifier, "_windows_attribute_tag", fake_attribute_tag)
    monkeypatch.setattr(verifier, "_windows_handle_fingerprint", fake_fingerprint)
    monkeypatch.setattr(verifier, "_windows_close_handle", closed.append)

    with pytest.raises(verifier._InvalidRegister):
        verifier._read_windows_register(r"C:\trusted", ("surrogate", "register.json"))
    assert opened == [
        (r"C:\trusted", True),
        (r"C:\trusted\surrogate", True),
    ]
    assert closed == [102, 101]


@pytest.mark.parametrize(
    "path_text",
    [
        r"\\server\share\phase20.json",
        r"//server/share/phase20.json",
        r"\\?\C:\phase20.json",
        r"\\.\C:\phase20.json",
    ],
)
def test_verifier_rejects_network_and_device_paths_before_path_construction(
    monkeypatch: pytest.MonkeyPatch,
    path_text: str,
) -> None:
    verifier = _load_verifier()
    touched: list[str] = []

    def fail_path(value: str) -> Path:
        touched.append(value)
        raise AssertionError("filesystem path construction was reached")

    monkeypatch.setattr(verifier, "Path", fail_path)
    with pytest.raises(verifier._InvalidRegister):
        verifier._local_register_path(path_text)
    assert touched == []


def test_verifier_rejects_different_windows_drive_before_target_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    verifier = _load_verifier()
    touched: list[str] = []

    monkeypatch.setattr(verifier, "_IS_WINDOWS", True)
    monkeypatch.setattr(verifier.os, "getcwd", lambda: r"C:\workspace")

    def fail_path(value: str) -> Path:
        touched.append(value)
        raise AssertionError("target filesystem access was reached")

    monkeypatch.setattr(verifier, "Path", fail_path)
    with pytest.raises(verifier._InvalidRegister):
        verifier._local_register_path(r"D:\phase20.json")
    assert touched == []


def test_generator_and_verifier_cli_round_trip(tmp_path: Path) -> None:
    generated = subprocess.run(
        [sys.executable, str(GENERATOR), "--confirm-input-register-only"],
        check=False,
        capture_output=True,
    )
    assert generated.returncode == 0
    assert generated.stderr == b""
    assert generated.stdout == canonical_evaluation_holdout_input_register_bytes()

    path = tmp_path / "phase20.json"
    path.write_bytes(generated.stdout)
    verified = subprocess.run(
        [sys.executable, str(VERIFIER), "--register", str(path)],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )
    assert verified.returncode == 0
    assert verified.stderr == ""
    receipt = json.loads(verified.stdout)
    assert receipt["register_state"] == "INPUTS_FROZEN"
    assert receipt["input_requirement_count"] == 20
    assert receipt["transition_rule_count"] == 10
    assert receipt["step3_eligible"] is False


@pytest.mark.parametrize(
    "arguments",
    [[], ["--register"], ["--register", "a", "--register", "b"], ["--unknown"]],
)
def test_verifier_invalid_invocation_is_sanitized(arguments: list[str]) -> None:
    result = subprocess.run(
        [sys.executable, str(VERIFIER), *arguments],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert result.stdout == ""
    assert result.stderr == FAILURE


def test_verifier_rejects_semantic_tamper_with_generic_error(tmp_path: Path) -> None:
    payload = build_family_a_evaluation_holdout_input_register().model_dump(mode="json")
    payload["input_requirements"][0]["input_value_present"] = True
    path = tmp_path / "tampered.json"
    path.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    result = subprocess.run(
        [sys.executable, str(VERIFIER), "--register", str(path)],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert result.stdout == ""
    assert result.stderr == FAILURE
