from __future__ import annotations

import ast
import json
import socket
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from fable5_data.phase18.rights_review import build_family_a_current_use_rights_review


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
    root = Path("services/data/src/fable5_data/phase18")
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
        raise AssertionError("Phase 18 attempted network access")

    monkeypatch.setattr(socket, "create_connection", deny)
    monkeypatch.setattr(socket.socket, "connect", deny)

    artifact = build_family_a_current_use_rights_review()
    assert attempted == []
    assert artifact.runtime_network_disabled is True
    assert artifact.operational_external_request_performed is False
    assert artifact.provider_data_request_performed is False


def test_artifact_contains_only_allowlisted_inert_official_https_citations() -> None:
    artifact = build_family_a_current_use_rights_review()
    urls = tuple(item.official_url for item in artifact.terms_sources)

    assert all(url.startswith("https://") for url in urls)
    assert {urlsplit(url).hostname for url in urls} == {
        "app.tiingo.com",
        "fred.stlouisfed.org",
        "indexes.morningstar.com",
        "www.lseg.com",
        "www.morningstar.com",
        "www.sec.gov",
        "www.tiingo.com",
    }
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
    ):
        assert forbidden not in rendered
    assert artifact.official_citations_inert is True
    assert artifact.terms_body_persisted is False
    assert artifact.external_document_persisted is False
    assert artifact.provider_payload_persisted is False
    assert artifact.licensed_data_persisted is False


def test_cli_sources_have_no_environment_database_transport_or_mutation_configuration() -> None:
    paths = (
        Path("scripts/generate_family_a_current_use_rights_review.py"),
        Path("scripts/verify_family_a_current_use_rights_review.py"),
    )
    source = "\n".join(path.read_text(encoding="utf-8") for path in paths)
    for path in paths:
        cli_source = path.read_text(encoding="utf-8")
        assert "sys.addaudithook(_offline_audit_hook)" in cli_source
        assert 'event.startswith("socket.")' in cli_source
        assert 'frozenset({"os.system", "subprocess.Popen"})' in cli_source
        assert "_prove_socket_construction_is_denied()" in cli_source
    assert "FABLE5_" not in source
    assert "getenv" not in source
    assert "environ" not in source
    assert "database_url" not in source
    for forbidden_argument in (
        "--output",
        "--provider",
        "--url",
        "--source",
        "--status",
        "--terms",
        "--body",
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
