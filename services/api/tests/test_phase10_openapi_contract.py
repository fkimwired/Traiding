from __future__ import annotations

from typing import Any, cast
from unittest.mock import MagicMock

from fable5_api.local_simulations import router
from fable5_api.main import app as full_app
from fable5_paper.workflow import PaperSimulationWorkflow
from fastapi import FastAPI

PHASE10_METHODS = {"get", "post", "put", "patch", "delete"}
EXPECTED_PHASE10_SURFACE = {
    "/v1/local-simulations": {"get", "post"},
    "/v1/local-simulations/{simulation_run_id}": {"get"},
}


def _openapi() -> dict[str, Any]:
    app = FastAPI()
    app.state.paper_simulation_workflow = MagicMock(spec=PaperSimulationWorkflow)
    app.include_router(router)
    return app.openapi()


def _response_schema(operation: dict[str, Any], status_code: str) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        operation["responses"][status_code]["content"]["application/json"]["schema"],
    )


def _phase10_surface(schema: dict[str, Any]) -> dict[str, set[str]]:
    surface: dict[str, set[str]] = {}
    for path, operations in schema["paths"].items():
        methods = set(operations).intersection(PHASE10_METHODS)
        tags = {
            tag
            for method, operation in operations.items()
            if method in PHASE10_METHODS and isinstance(operation, dict)
            for tag in operation.get("tags", [])
        }
        if path in EXPECTED_PHASE10_SURFACE or "paper-simulation" in tags:
            surface[path] = methods
    return surface


def test_phase10_openapi_surface_is_exact_create_read_list() -> None:
    schema = _openapi()
    paths = schema["paths"]

    assert {path: set(item) for path, item in paths.items()} == EXPECTED_PHASE10_SURFACE
    assert _phase10_surface(full_app.openapi()) == EXPECTED_PHASE10_SURFACE

    collection = paths["/v1/local-simulations"]
    detail = paths["/v1/local-simulations/{simulation_run_id}"]
    assert collection["post"]["requestBody"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/PaperSimulationCreateRequest"
    }
    assert _response_schema(collection["post"], "201") == {
        "$ref": "#/components/schemas/PaperSimulationArtifact"
    }
    assert _response_schema(collection["post"], "404") == {
        "$ref": "#/components/schemas/PaperSimulationNotFoundErrorResponse"
    }
    assert _response_schema(collection["post"], "409") == {
        "$ref": "#/components/schemas/PaperSimulationConflictErrorResponse"
    }
    assert _response_schema(collection["post"], "422") == {
        "$ref": "#/components/schemas/PaperSimulationValidationErrorResponse"
    }
    assert _response_schema(collection["get"], "200")["items"] == {
        "$ref": "#/components/schemas/PaperSimulationSummary"
    }
    assert _response_schema(collection["get"], "409") == {
        "$ref": "#/components/schemas/PaperSimulationConflictErrorResponse"
    }
    assert _response_schema(collection["get"], "422") == {
        "$ref": "#/components/schemas/PaperSimulationValidationErrorResponse"
    }
    assert _response_schema(detail["get"], "200") == {
        "$ref": "#/components/schemas/PaperSimulationArtifact"
    }
    assert _response_schema(detail["get"], "404") == {
        "$ref": "#/components/schemas/PaperSimulationNotFoundErrorResponse"
    }
    assert _response_schema(detail["get"], "409") == {
        "$ref": "#/components/schemas/PaperSimulationConflictErrorResponse"
    }
    assert _response_schema(detail["get"], "422") == {
        "$ref": "#/components/schemas/PaperSimulationValidationErrorResponse"
    }

    list_parameters = {item["name"]: item["schema"] for item in collection["get"]["parameters"]}
    assert list_parameters["limit"] == {
        "default": 100,
        "maximum": 100,
        "minimum": 1,
        "title": "Limit",
        "type": "integer",
    }
    assert list_parameters["approval_assessment_id"]["anyOf"] == [
        {"format": "uuid", "type": "string"},
        {"type": "null"},
    ]
    assert detail["get"]["parameters"] == [
        {
            "in": "path",
            "name": "simulation_run_id",
            "required": True,
            "schema": {
                "format": "uuid",
                "title": "Simulation Run Id",
                "type": "string",
            },
        }
    ]

    components = schema["components"]["schemas"]
    assert components["PaperSimulationNotFoundErrorResponse"] == {
        "additionalProperties": False,
        "properties": {
            "detail": {
                "const": "The requested immutable Phase 10 simulation evidence was not found.",
                "title": "Detail",
                "type": "string",
            }
        },
        "required": ["detail"],
        "title": "PaperSimulationNotFoundErrorResponse",
        "type": "object",
    }
    conflict_detail = components["PaperSimulationConflictErrorResponse"]["properties"]["detail"]
    assert conflict_detail["enum"] == [
        "Immutable Phase 10 simulation evidence conflicts with persisted lineage.",
        "The immutable Phase 10 simulation request could not be completed.",
    ]
    assert components["PaperSimulationConflictErrorResponse"]["required"] == ["detail"]


def test_phase10_request_is_strict_reference_and_idempotency_only() -> None:
    request = _openapi()["components"]["schemas"]["PaperSimulationCreateRequest"]

    assert request["additionalProperties"] is False
    assert set(request["properties"]) == {
        "approval_assessment_id",
        "simulation_idempotency_key",
    }
    assert set(request["required"]) == set(request["properties"])
    assert request["properties"]["approval_assessment_id"] == {
        "format": "uuid",
        "title": "Approval Assessment Id",
        "type": "string",
    }
    idempotency = request["properties"]["simulation_idempotency_key"]
    assert idempotency["minLength"] == 8
    assert idempotency["maxLength"] == 128
    assert idempotency["pattern"] == r"^[A-Za-z0-9][A-Za-z0-9._:-]*$"

    forbidden_client_authority = {
        "artifact_sha256",
        "checks",
        "created_at_utc",
        "decision_time_utc",
        "entity_id",
        "fill_price",
        "ledger_entries",
        "notional",
        "outcome",
        "position",
        "price",
        "quantity",
        "reason_codes",
        "risk_override",
        "side",
        "signal",
        "symbol",
    }
    assert not forbidden_client_authority.intersection(request["properties"])


def test_phase10_responses_freeze_the_local_mock_and_no_live_boundaries() -> None:
    components = _openapi()["components"]["schemas"]
    artifact = components["PaperSimulationArtifact"]
    summary = components["PaperSimulationSummary"]

    for schema in (artifact, summary):
        assert schema["additionalProperties"] is False
        properties = schema["properties"]
        assert properties["synthetic"]["const"] is True
        assert properties["simulated_paper_only"]["const"] is True
        assert properties["local_mock_only"]["const"] is True
        assert properties["external_submission"]["const"] is False
        assert properties["live_path_absent"]["const"] is True
        assert properties["no_personalized_investment_advice"]["const"] is True
        assert properties["no_real_performance_claimed"]["const"] is True

    assert artifact["properties"]["external_routing_absent"]["const"] is True
    assert artifact["properties"]["ledger_entries"]["maxItems"] == 1
    assert artifact["properties"]["checks"]["minItems"] == 7
    assert set(components["PaperSimulationOutcome"]["enum"]) == {
        "BLOCKED",
        "SIMULATED_COMPLETE",
    }


def test_phase10_surface_has_no_action_or_external_resource_route() -> None:
    schema = _openapi()
    forbidden_path_terms = (
        "broker",
        "cancel",
        "credential",
        "execute",
        "fill",
        "live",
        "order",
        "position",
        "provider",
        "submit",
    )
    for path, operations in schema["paths"].items():
        assert not any(token in path.casefold() for token in forbidden_path_terms)
        assert set(operations) <= {"get", "post"}


def test_phase10_surface_classifier_rejects_an_extra_simulation_action() -> None:
    schema = _openapi()
    schema["paths"]["/v1/local-simulations/{simulation_run_id}/cancel"] = {
        "post": {"tags": ["paper-simulation"]}
    }

    assert _phase10_surface(schema) != EXPECTED_PHASE10_SURFACE
