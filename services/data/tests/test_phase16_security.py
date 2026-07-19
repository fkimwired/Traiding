from __future__ import annotations

import ast
import json
import socket
from pathlib import Path

import pytest
from fable5_data.phase16.plan import build_family_a_point_in_time_source_plan


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    result: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.update(item.name for item in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            result.add(node.module)
    return result


def test_domain_is_database_network_environment_clock_random_and_git_free() -> None:
    root = Path("services/data/src/fable5_data/phase16")
    imports = set().union(*(_imports(path) for path in root.glob("*.py")))
    forbidden = (
        "aiohttp",
        "fastapi",
        "fable5_api",
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
        raise AssertionError("Phase 16 attempted network access")

    monkeypatch.setattr(socket, "create_connection", deny)
    monkeypatch.setattr(socket.socket, "connect", deny)

    artifact = build_family_a_point_in_time_source_plan()
    assert attempted == []
    assert artifact.external_request_performed is False
    assert artifact.external_verification_performed is False


def test_artifact_contains_no_secret_endpoint_or_observation_payload() -> None:
    rendered = json.dumps(
        build_family_a_point_in_time_source_plan().model_dump(mode="json"), sort_keys=True
    ).casefold()
    for forbidden in (
        "api_key",
        "api token",
        "authorization header",
        "secret key",
        "account number",
        "raw price",
        "provider body",
        "https://",
        "http://",
    ):
        assert forbidden not in rendered


def test_cli_sources_have_no_environment_database_transport_or_mutation_configuration() -> None:
    paths = (
        Path("scripts/generate_family_a_point_in_time_source_plan.py"),
        Path("scripts/verify_family_a_point_in_time_source_plan.py"),
    )
    source = "\n".join(path.read_text(encoding="utf-8") for path in paths)
    assert "FABLE5_" not in source
    assert "getenv" not in source
    assert "environ" not in source
    assert "database_url" not in source
    for forbidden_argument in (
        "--output",
        "--provider",
        "--url",
        "--credential",
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
