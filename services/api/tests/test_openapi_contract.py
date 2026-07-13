import json
from pathlib import Path

from fable5_api.main import app


def test_committed_openapi_matches_fastapi_schema() -> None:
    root = Path(__file__).resolve().parents[3]
    committed = json.loads((root / "packages/contracts/openapi.json").read_text(encoding="utf-8"))

    assert committed == app.openapi()
