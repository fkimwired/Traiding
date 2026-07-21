from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DOMAIN = ROOT / "services/data/src/fable5_data/phase25"


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".", 1)[0])
    return imported


def test_phase25_domain_has_no_transport_database_vendor_or_runtime_discovery_imports() -> None:
    imported = set().union(*(_imports(path) for path in DOMAIN.glob("*.py")))
    assert not imported & {
        "aiohttp",
        "asyncio",
        "fastapi",
        "httpx",
        "openbb",
        "os",
        "psycopg",
        "requests",
        "socket",
        "sqlalchemy",
        "subprocess",
        "tradingagents",
        "urllib",
        "yfinance",
    }


def test_phase25_contains_no_adapter_execution_observation_or_live_surface() -> None:
    source = "\n".join(path.read_text(encoding="utf-8") for path in DOMAIN.glob("*.py"))
    for forbidden in (
        "datetime.now",
        "datetime.utcnow",
        "getenv(",
        "environ[",
        "uuid4(",
        "create_engine(",
        "requests.get(",
        "httpx.",
        "submit_order",
        "place_order",
        "create_order",
    ):
        assert forbidden not in source


def test_phase25_vendor_sdks_are_absent_from_dependency_and_production_surfaces() -> None:
    dependency_text = "\n".join(
        (ROOT / path).read_text(encoding="utf-8").casefold()
        for path in ("pyproject.toml", "requirements.lock", "package.json", "package-lock.json")
    )
    assert "yfinance" not in dependency_text
    production_roots = (
        ROOT / "services/api/src",
        ROOT / "services/backtester/src",
        ROOT / "services/data/src",
        ROOT / "services/jobs/src",
        ROOT / "services/paper/src",
        ROOT / "services/research/src",
    )
    for root in production_roots:
        for path in root.rglob("*.py"):
            if DOMAIN in path.parents:
                continue
            imports = _imports(path)
            assert not imports & {"openbb", "tradingagents", "yfinance"}
