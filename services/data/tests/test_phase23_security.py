from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DOMAIN = ROOT / "services/data/src/fable5_data/phase23"


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".", 1)[0])
    return imported


def test_phase23_domain_has_no_transport_database_or_runtime_discovery_imports() -> None:
    imported = set().union(*(_imports(path) for path in DOMAIN.glob("*.py")))
    assert not imported & {
        "aiohttp",
        "asyncio",
        "fastapi",
        "httpx",
        "os",
        "psycopg",
        "random",
        "redis",
        "requests",
        "rq",
        "secrets",
        "socket",
        "sqlalchemy",
        "sqlite3",
        "ssl",
        "subprocess",
        "time",
        "urllib",
    }


def test_phase23_domain_contains_no_execution_or_live_surface() -> None:
    source = "\n".join(path.read_text(encoding="utf-8") for path in DOMAIN.glob("*.py"))
    for forbidden in (
        "datetime.now",
        "datetime.utcnow",
        "getenv(",
        "environ[",
        "uuid4(",
        "create_engine(",
        "FastAPI(",
        "submit_order",
        "place_order",
        "create_order",
    ):
        assert forbidden not in source
