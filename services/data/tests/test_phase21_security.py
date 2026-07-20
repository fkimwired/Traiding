from __future__ import annotations

import ast
import json
import socket
from pathlib import Path

import pytest
from fable5_data.phase21.decision_requirements import (
    build_family_a_operational_composition_decision_requirements,
    canonical_operational_composition_decision_requirements_bytes,
)

ROOT = Path(__file__).resolve().parents[3]
GENERATOR = ROOT / "scripts/generate_family_a_operational_composition_decision_requirements.py"
VERIFIER = ROOT / "scripts/verify_family_a_operational_composition_decision_requirements.py"
HARDENED_READER = ROOT / "scripts/verify_family_a_evaluation_holdout_input_register.py"


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    result: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.update(item.name for item in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            result.add(node.module)
    return result


def test_domain_is_database_network_environment_clock_random_subprocess_and_git_free() -> None:
    root = Path("services/data/src/fable5_data/phase21")
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
        raise AssertionError("Phase 21 attempted network access")

    monkeypatch.setattr(socket, "create_connection", deny)
    monkeypatch.setattr(socket.socket, "connect", deny)
    artifact = build_family_a_operational_composition_decision_requirements()
    assert attempted == []
    assert artifact.runtime_network_disabled is True
    assert artifact.operational_external_request_performed is False


def test_ambient_environment_cannot_change_canonical_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    before = canonical_operational_composition_decision_requirements_bytes()
    monkeypatch.setenv("FABLE5_PHASE21_FAKE_CREDENTIAL", "phase21-secret-canary")
    monkeypatch.setenv("DATABASE_URL", "postgresql://phase21-secret-canary")
    monkeypatch.setenv("HTTP_PROXY", "http://phase21-secret-canary.invalid")
    after = canonical_operational_composition_decision_requirements_bytes()
    assert after == before
    assert b"phase21-secret-canary" not in after


def test_artifact_contains_no_credential_payload_or_decision_value() -> None:
    artifact = build_family_a_operational_composition_decision_requirements()
    rendered = json.dumps(artifact.model_dump(mode="json"), sort_keys=True).casefold()
    for forbidden in (
        "api_key",
        "api token",
        "authorization header",
        "secret key",
        "account number",
        "raw price payload",
        "provider body",
        "observation_value",
        '"selection_evidence_sha256":',
        '"operational_source_product_composition_sha256":',
    ):
        assert forbidden not in rendered
    assert artifact.composition_value_present is False
    assert artifact.selection_evidence_produced is False


def test_cli_sources_install_and_actively_prove_offline_boundaries() -> None:
    source = "\n".join(path.read_text(encoding="utf-8") for path in (GENERATOR, VERIFIER))
    for path in (GENERATOR, VERIFIER):
        cli_source = path.read_text(encoding="utf-8")
        assert "sys.addaudithook(_offline_audit_hook)" in cli_source
        assert 'event.startswith("socket.")' in cli_source
        assert 'frozenset({"os.system", "subprocess.Popen"})' in cli_source
        assert "_prove_offline_boundary()" in cli_source
    assert "getenv" not in source
    assert "environ" not in source
    assert "database_url" not in source.casefold()
    for forbidden_argument in (
        "--output",
        "--provider",
        "--url",
        "--source",
        "--status",
        "--select",
        "--rank",
        "--value",
        "--submit",
        "--credential",
        "--account",
        "--rights",
        "--data",
        "--authority",
        "--repair",
        "--capture",
        "--ingestion",
        "--research",
        "--order",
    ):
        assert forbidden_argument not in source


def test_verifier_reuses_hardened_handle_relative_reader() -> None:
    source = VERIFIER.read_text(encoding="utf-8")
    reader = HARDENED_READER.read_text(encoding="utf-8")
    assert "hardened._read_register(path_text)" in source
    for required in (
        "dir_fd=parent_descriptor",
        'getattr(os, "O_DIRECTORY", 0)',
        'getattr(os, "O_NOFOLLOW", 0)',
        "_WINDOWS_FILE_FLAG_OPEN_REPARSE_POINT",
        "_WINDOWS_FILE_SHARE_READ | _WINDOWS_FILE_SHARE_WRITE",
        "msvcrt.open_osfhandle(",
    ):
        assert required in reader
    for forbidden in (".resolve(", ".realpath(", ".lstat("):
        assert forbidden not in reader
