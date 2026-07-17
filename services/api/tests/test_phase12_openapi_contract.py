from __future__ import annotations

import json
from typing import Any, cast
from unittest.mock import MagicMock

from fable5_api.main import app as full_app
from fable5_api.paper_shadow_readiness import router
from fable5_paper.phase12.repository import PaperShadowReadinessRepository
from fastapi import FastAPI

METHODS = {"get", "post", "put", "patch", "delete"}
READINESS_PATH = "/v1/paper-shadow-readiness/{readiness_assessment_id}"
EXPECTED_SURFACE = {READINESS_PATH: {"get"}}


def _openapi() -> dict[str, Any]:
    app = FastAPI()
    app.state.paper_shadow_readiness_repository = MagicMock(spec=PaperShadowReadinessRepository)
    app.include_router(router)
    return app.openapi()


def _response_schema(operation: dict[str, Any], status_code: str) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        operation["responses"][status_code]["content"]["application/json"]["schema"],
    )


def _phase12_surface(schema: dict[str, Any]) -> dict[str, set[str]]:
    surface: dict[str, set[str]] = {}
    for path, operations in schema["paths"].items():
        tags = {
            tag
            for method, operation in operations.items()
            if method in METHODS and isinstance(operation, dict)
            for tag in operation.get("tags", [])
        }
        if path == READINESS_PATH or "paper-shadow-readiness" in tags:
            surface[path] = set(operations).intersection(METHODS)
    return surface


def test_phase12_openapi_surface_is_exactly_one_historical_get() -> None:
    schema = _openapi()
    assert {path: set(item) for path, item in schema["paths"].items()} == EXPECTED_SURFACE
    assert _phase12_surface(full_app.openapi()) == EXPECTED_SURFACE

    operation = schema["paths"][READINESS_PATH]["get"]
    assert "requestBody" not in operation
    assert operation["tags"] == ["paper-shadow-readiness"]
    assert operation["parameters"] == [
        {
            "in": "path",
            "name": "readiness_assessment_id",
            "required": True,
            "schema": {
                "format": "uuid",
                "title": "Readiness Assessment Id",
                "type": "string",
            },
        }
    ]
    assert _response_schema(operation, "200") == {
        "$ref": "#/components/schemas/PaperShadowReadinessArtifact"
    }
    assert _response_schema(operation, "404") == {
        "$ref": "#/components/schemas/PaperShadowReadinessNotFoundErrorResponse"
    }
    assert _response_schema(operation, "409") == {
        "$ref": "#/components/schemas/PaperShadowReadinessConflictErrorResponse"
    }
    assert _response_schema(operation, "422") == {
        "$ref": "#/components/schemas/PaperShadowReadinessValidationErrorResponse"
    }


def test_phase12_artifact_contract_preserves_non_execution_literals() -> None:
    components = _openapi()["components"]["schemas"]
    artifact = components["PaperShadowReadinessArtifact"]
    properties = artifact["properties"]
    assert artifact["additionalProperties"] is False
    assert {
        "outcome",
        "order_submission_authorized",
        "strategy_execution_eligible",
        "live_path_absent",
        "no_personalized_investment_advice",
        "no_real_performance_claimed",
        "disclaimer",
    } <= set(artifact["required"])
    outcome_name = properties["outcome"]["$ref"].rsplit("/", 1)[-1]
    assert components[outcome_name]["enum"] == [
        "MOCK_PROOF_COMPLETE",
        "SHADOW_READY",
        "BLOCKED",
    ]
    assert properties["order_submission_authorized"]["const"] is False
    assert properties["strategy_execution_eligible"]["const"] is False
    assert properties["live_path_absent"]["const"] is True
    assert properties["no_personalized_investment_advice"]["const"] is True
    assert properties["no_real_performance_claimed"]["const"] is True


def test_phase12_generated_surface_contains_no_secret_or_order_contract() -> None:
    schema = _openapi()
    assert set(schema["paths"][READINESS_PATH]) == {"get"}
    rendered = json.dumps(schema, sort_keys=True).casefold()
    for forbidden in (
        "api_key",
        "api-key",
        "credential",
        "authorization_header",
        "account_number",
        "client_order",
        "filled_qty",
        "limit_price",
        "order_submission_request",
        "secret_key",
        "stop_price",
    ):
        assert forbidden not in rendered
