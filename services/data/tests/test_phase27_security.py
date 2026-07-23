from __future__ import annotations

import ast
from pathlib import Path

from fable5_data.phase27 import canonical as c
from fable5_data.phase27.package import build_phase27_package

ROOT = Path(__file__).resolve().parents[3]
DOMAIN = ROOT / "services/data/src/fable5_data/phase27"


def test_phase27_domain_has_no_network_provider_database_or_runtime_surface() -> None:
    imported: set[str] = set()
    combined = ""
    for path in DOMAIN.glob("*.py"):
        source = path.read_text(encoding="utf-8")
        combined += source
        tree = ast.parse(source, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".", 1)[0])
    assert not imported & {
        "aiohttp",
        "fastapi",
        "httpx",
        "psycopg",
        "requests",
        "socket",
        "sqlalchemy",
        "subprocess",
        "urllib",
    }
    for forbidden in (
        "submit_order(",
        "place_order(",
        "cancel_order(",
        "replace_order(",
        "close_position(",
        "execute_order(",
        "liquidate(",
        "liquidate_position(",
        "datetime.now(",
        "datetime.utcnow(",
        "create_all(",
    ):
        assert forbidden not in combined


def test_phase27_every_operational_authority_boundary_is_false() -> None:
    artifact = build_phase27_package()
    for field, expected in c.BOUNDARY_VALUES.items():
        assert getattr(artifact, field) is expected
    assert not artifact.acquisition_authorized
    assert not artifact.execution_authorized
    assert not artifact.order_submission_authorized
    assert artifact.paper_only and artifact.live_path_absent
    for prohibited_surface in (
        "candidate_screen_output",
        "strategy_output",
        "risk_promotion_authorized",
        "cancellation_authorized",
        "liquidation_authorized",
        "live_execution_mode",
    ):
        assert not hasattr(artifact, prohibited_surface)


def test_phase27_artifact_is_metadata_only_and_contains_no_observation_values() -> None:
    rendered = build_phase27_package().model_dump_json().casefold()
    for forbidden in (
        '"price"',
        '"quote"',
        '"position"',
        '"quantity"',
        '"order_side"',
        '"raw_body"',
        '"credential"',
        '"secret"',
    ):
        assert forbidden not in rendered
