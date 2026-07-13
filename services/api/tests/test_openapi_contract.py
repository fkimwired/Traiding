import json
from pathlib import Path

from fable5_api.main import app


def test_committed_openapi_matches_fastapi_schema() -> None:
    root = Path(__file__).resolve().parents[3]
    committed = json.loads((root / "packages/contracts/openapi.json").read_text(encoding="utf-8"))

    assert committed == app.openapi()


def test_phase2_contract_uses_field_specific_evidence_and_output_only_supply_time() -> None:
    schema = app.openapi()
    components = schema["components"]["schemas"]
    card_properties = components["TradingIdeaCard"]["properties"]
    expected_refs = {
        "asset_class": "AssetClassEvidence",
        "forecast_horizon": "ForecastHorizonEvidence",
        "signal_family": "SignalFamilyEvidence",
        "execution_style": "ExecutionStyleEvidence",
        "required_data": "RequiredDataEvidence",
        "risk_assumptions": "RiskAssumptionsEvidence",
    }
    for field, component in expected_refs.items():
        assert card_properties[field] == {"$ref": f"#/components/schemas/{component}"}

    assert "TextEvidence" not in components
    assert "ListEvidence" not in components
    for request_schema in ("SourceIntakeRequest", "SourceCorrectionRequest"):
        properties = components[request_schema]["properties"]
        assert "supplied_at_utc" not in properties
        assert properties["raw_text"]["type"] == "string"
        assert "anyOf" not in properties["raw_text"]

    source_version = components["SourceVersion"]
    assert "supplied_at_utc" in source_version["properties"]
    assert "supplied_at_utc" in source_version["required"]
