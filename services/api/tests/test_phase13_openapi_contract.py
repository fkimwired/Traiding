from __future__ import annotations

from typing import Any, cast
from unittest.mock import MagicMock

from fable5_api.data_qualifications import router
from fable5_api.main import app as full_app
from fable5_data.phase13.repository import PointInTimeQualificationRepository
from fastapi import FastAPI

METHODS = {"get", "post", "put", "patch", "delete"}
QUALIFICATION_PATH = "/v1/point-in-time-data-qualifications/{qualification_id}"
EXPECTED_SURFACE = {QUALIFICATION_PATH: {"get"}}


def _openapi() -> dict[str, Any]:
    app = FastAPI()
    app.state.point_in_time_qualification_repository = MagicMock(
        spec=PointInTimeQualificationRepository
    )
    app.include_router(router)
    return app.openapi()


def _response_schema(operation: dict[str, Any], status_code: str) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        operation["responses"][status_code]["content"]["application/json"]["schema"],
    )


def _phase13_surface(schema: dict[str, Any]) -> dict[str, set[str]]:
    surface: dict[str, set[str]] = {}
    for path, operations in schema["paths"].items():
        tags = {
            tag
            for method, operation in operations.items()
            if method in METHODS and isinstance(operation, dict)
            for tag in operation.get("tags", [])
        }
        if path == QUALIFICATION_PATH or "point-in-time-data-qualifications" in tags:
            surface[path] = set(operations).intersection(METHODS)
    return surface


def test_phase13_openapi_surface_is_exactly_one_historical_get() -> None:
    schema = _openapi()
    assert {path: set(item) for path, item in schema["paths"].items()} == EXPECTED_SURFACE
    assert _phase13_surface(full_app.openapi()) == EXPECTED_SURFACE

    operation = schema["paths"][QUALIFICATION_PATH]["get"]
    assert "requestBody" not in operation
    assert operation["tags"] == ["point-in-time-data-qualifications"]
    assert operation["parameters"] == [
        {
            "in": "path",
            "name": "qualification_id",
            "required": True,
            "schema": {
                "format": "uuid",
                "title": "Qualification Id",
                "type": "string",
            },
        }
    ]
    assert _response_schema(operation, "200") == {
        "$ref": "#/components/schemas/PointInTimeQualificationArtifact"
    }
    assert _response_schema(operation, "404") == {
        "$ref": "#/components/schemas/PointInTimeQualificationNotFoundErrorResponse"
    }
    assert _response_schema(operation, "409") == {
        "$ref": "#/components/schemas/PointInTimeQualificationConflictErrorResponse"
    }
    assert _response_schema(operation, "422") == {
        "$ref": "#/components/schemas/PointInTimeQualificationValidationErrorResponse"
    }


def test_phase13_artifact_contract_preserves_qualification_only_literals() -> None:
    components = _openapi()["components"]["schemas"]
    artifact = components["PointInTimeQualificationArtifact"]
    properties = artifact["properties"]
    assert artifact["additionalProperties"] is False
    assert {
        "research_data_eligible",
        "strategy_promotion_authorized",
        "strategy_execution_eligible",
        "execution_authorized",
        "order_submission_authorized",
        "live_path_absent",
        "no_personalized_investment_advice",
        "no_real_performance_claimed",
        "disclaimer",
    } <= set(artifact["required"])
    outcome_name = properties["outcome"]["$ref"].rsplit("/", 1)[-1]
    assert components[outcome_name]["enum"] == [
        "MOCK_PROOF_COMPLETE",
        "EXTERNAL_SAMPLE_QUALIFIED",
        "BLOCKED",
    ]
    for field in (
        "research_data_eligible",
        "strategy_promotion_authorized",
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


def test_phase13_generated_surface_contains_no_secret_data_or_execution_contract() -> None:
    schema = _openapi()
    assert set(schema["paths"][QUALIFICATION_PATH]) == {"get"}
    property_names = {
        property_name.casefold()
        for component in schema["components"]["schemas"].values()
        if isinstance(component, dict)
        for property_name in (
            component.get("properties", {}) if isinstance(component.get("properties"), dict) else {}
        )
    }
    forbidden_properties = {
        "api_token",
        "authorization_header",
        "credential",
        "raw_body",
        "raw_response",
        "raw_price",
        "statement_value",
        "trade_instruction",
        "order_submission_request",
        "client_order",
        "filled_qty",
    }
    assert property_names.isdisjoint(forbidden_properties)
