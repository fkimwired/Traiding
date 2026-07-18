from __future__ import annotations

from typing import Any, cast
from unittest.mock import MagicMock

from fable5_api.main import app as full_app
from fable5_api.research_ingestion_eligibility import router
from fable5_data.phase14.repository import ResearchIngestionEligibilityRepository
from fastapi import FastAPI

METHODS = {"get", "post", "put", "patch", "delete"}
ELIGIBILITY_PATH = "/v1/research-ingestion-eligibility/{assessment_id}"
EXPECTED_SURFACE = {ELIGIBILITY_PATH: {"get"}}


def _openapi() -> dict[str, Any]:
    app = FastAPI()
    app.state.research_ingestion_eligibility_repository = MagicMock(
        spec=ResearchIngestionEligibilityRepository
    )
    app.include_router(router)
    return app.openapi()


def _response_schema(operation: dict[str, Any], status_code: str) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        operation["responses"][status_code]["content"]["application/json"]["schema"],
    )


def _phase14_surface(schema: dict[str, Any]) -> dict[str, set[str]]:
    surface: dict[str, set[str]] = {}
    for path, operations in schema["paths"].items():
        tags = {
            tag
            for method, operation in operations.items()
            if method in METHODS and isinstance(operation, dict)
            for tag in operation.get("tags", [])
        }
        if path == ELIGIBILITY_PATH or "research-ingestion-eligibility" in tags:
            surface[path] = set(operations).intersection(METHODS)
    return surface


def test_phase14_openapi_surface_is_exactly_one_historical_get() -> None:
    schema = _openapi()
    assert {path: set(item) for path, item in schema["paths"].items()} == EXPECTED_SURFACE
    assert _phase14_surface(full_app.openapi()) == EXPECTED_SURFACE

    operation = schema["paths"][ELIGIBILITY_PATH]["get"]
    assert "requestBody" not in operation
    assert operation["tags"] == ["research-ingestion-eligibility"]
    assert operation["parameters"] == [
        {
            "in": "path",
            "name": "assessment_id",
            "required": True,
            "schema": {
                "format": "uuid",
                "title": "Assessment Id",
                "type": "string",
            },
        }
    ]
    assert _response_schema(operation, "200") == {
        "$ref": "#/components/schemas/ResearchIngestionEligibilityArtifact"
    }
    assert _response_schema(operation, "404") == {
        "$ref": "#/components/schemas/ResearchIngestionEligibilityNotFoundErrorResponse"
    }
    assert _response_schema(operation, "409") == {
        "$ref": "#/components/schemas/ResearchIngestionEligibilityConflictErrorResponse"
    }
    assert _response_schema(operation, "422") == {
        "$ref": "#/components/schemas/ResearchIngestionEligibilityValidationErrorResponse"
    }


def test_phase14_artifact_contract_preserves_closed_false_authority() -> None:
    components = _openapi()["components"]["schemas"]
    artifact = components["ResearchIngestionEligibilityArtifact"]
    properties = artifact["properties"]
    assert artifact["additionalProperties"] is False
    outcome_name = properties["outcome"]["$ref"].rsplit("/", 1)[-1]
    assert components[outcome_name]["enum"] == ["MOCK_PROOF_COMPLETE", "BLOCKED"]
    for field in (
        "external_request_performed",
        "provider_payload_persisted",
        "research_ingestion_authorized",
        "research_snapshot_created",
        "research_data_eligible",
        "research_run_created",
        "research_run_authorized",
        "research_executed",
        "performance_computed",
        "pass_research_granted",
        "strategy_promotion_authorized",
        "paper_approval_granted",
        "strategy_execution_eligible",
        "execution_authorized",
        "order_submission_authorized",
    ):
        assert properties[field]["const"] is False
    for field in (
        "live_path_absent",
        "no_personalized_investment_advice",
        "no_real_performance_claimed",
    ):
        assert properties[field]["const"] is True


def test_phase14_generated_surface_contains_no_data_execution_or_secret_contract() -> None:
    schema = _openapi()
    assert set(schema["paths"][ELIGIBILITY_PATH]) == {"get"}
    property_names = {
        property_name.casefold()
        for component in schema["components"]["schemas"].values()
        if isinstance(component, dict)
        for property_name in (
            component.get("properties", {}) if isinstance(component.get("properties"), dict) else {}
        )
    }
    assert property_names.isdisjoint(
        {
            "api_token",
            "authorization_header",
            "credential",
            "raw_body",
            "raw_response",
            "observation_value",
            "return_value",
            "performance_metric",
            "trade_instruction",
            "order_submission_request",
            "client_order",
            "filled_qty",
        }
    )
