from __future__ import annotations

import ast
import json
import socket
from pathlib import Path

import pytest
from fable5_data.phase15.specification import (
    build_family_a_research_admission_specification,
)


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    result: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.update(item.name for item in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            result.add(node.module)
    return result


def test_domain_is_database_network_provider_clock_and_random_free() -> None:
    root = Path("services/data/src/fable5_data/phase15")
    imports = set().union(*(_imports(path) for path in root.glob("*.py")))
    forbidden = (
        "aiohttp",
        "fable5_api",
        "fable5_paper",
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
        "time",
        "urllib",
    )

    assert not {
        name
        for name in imports
        if any(name == item or name.startswith(f"{item}.") for item in forbidden)
    }
    source = "\n".join(path.read_text(encoding="utf-8") for path in root.glob("*.py"))
    assert "datetime.now" not in source
    assert "utcnow" not in source
    assert "getenv" not in source
    assert "environ" not in source


def test_builder_succeeds_while_network_entrypoints_are_denied(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempted: list[str] = []

    def deny(*args: object, **kwargs: object) -> None:
        del args, kwargs
        attempted.append("network")
        raise AssertionError("Phase 15 attempted network access")

    monkeypatch.setattr(socket, "create_connection", deny)
    monkeypatch.setattr(socket.socket, "connect", deny)

    artifact = build_family_a_research_admission_specification()

    assert attempted == []
    assert artifact.external_request_performed is False
    assert artifact.external_data_capture_authorized is False


def test_portable_artifact_contains_no_secret_provider_or_observation_payload() -> None:
    encoded = json.loads(build_family_a_research_admission_specification().model_dump_json())
    rendered = json.dumps(encoded, sort_keys=True).casefold()

    for forbidden in (
        "api_key",
        "authorization header",
        "credential",
        "secret",
        "raw price",
        "provider body",
        "account number",
        "https://",
    ):
        assert forbidden not in rendered


def test_cli_sources_have_no_environment_database_or_transport_configuration() -> None:
    paths = (
        Path("scripts/generate_family_a_research_admission_specification.py"),
        Path("scripts/verify_family_a_research_admission_specification.py"),
    )
    source = "\n".join(path.read_text(encoding="utf-8") for path in paths)

    assert "FABLE5_" not in source
    assert "getenv" not in source
    assert "environ" not in source
    assert "database_url" not in source
    assert "http://" not in source
    assert "https://" not in source
    assert "--provider" not in source
    assert "--url" not in source
    assert "--credential" not in source
