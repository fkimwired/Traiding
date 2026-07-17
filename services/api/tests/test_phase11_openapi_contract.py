from __future__ import annotations

from typing import Any, cast
from unittest.mock import MagicMock

from fable5_api.local_simulations import evidence_router
from fable5_api.main import app as full_app
from fable5_paper.workflow import PaperSimulationWorkflow
from fastapi import FastAPI

METHODS = {"get", "post", "put", "patch", "delete"}
EVIDENCE_PATH = "/v1/local-simulations/{simulation_run_id}/evidence-bundle"
EXPECTED_SURFACE = {EVIDENCE_PATH: {"get"}}


def _openapi() -> dict[str, Any]:
    app = FastAPI()
    app.state.paper_simulation_workflow = MagicMock(spec=PaperSimulationWorkflow)
    app.include_router(evidence_router)
    return app.openapi()


def _response_schema(operation: dict[str, Any], status_code: str) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        operation["responses"][status_code]["content"]["application/json"]["schema"],
    )


def _phase11_surface(schema: dict[str, Any]) -> dict[str, set[str]]:
    surface: dict[str, set[str]] = {}
    for path, operations in schema["paths"].items():
        tags = {
            tag
            for method, operation in operations.items()
            if method in METHODS and isinstance(operation, dict)
            for tag in operation.get("tags", [])
        }
        if path == EVIDENCE_PATH or "local-simulation-evidence" in tags:
            surface[path] = set(operations).intersection(METHODS)
    return surface


def test_phase11_openapi_surface_is_exactly_one_get() -> None:
    schema = _openapi()
    assert {path: set(item) for path, item in schema["paths"].items()} == EXPECTED_SURFACE
    assert _phase11_surface(full_app.openapi()) == EXPECTED_SURFACE

    operation = schema["paths"][EVIDENCE_PATH]["get"]
    assert "requestBody" not in operation
    assert operation["tags"] == ["local-simulation-evidence"]
    assert operation["parameters"] == [
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
    assert _response_schema(operation, "200") == {
        "$ref": "#/components/schemas/LocalSimulationEvidenceBundle"
    }
    assert _response_schema(operation, "404") == {
        "$ref": "#/components/schemas/PaperSimulationNotFoundErrorResponse"
    }
    assert _response_schema(operation, "409") == {
        "$ref": "#/components/schemas/PaperSimulationConflictErrorResponse"
    }
    assert _response_schema(operation, "422") == {
        "$ref": "#/components/schemas/PaperSimulationValidationErrorResponse"
    }


def test_phase11_bundle_schema_has_exactly_five_required_hash_bound_fields() -> None:
    bundle = _openapi()["components"]["schemas"]["LocalSimulationEvidenceBundle"]
    expected_fields = {
        "bundle_schema_version",
        "bundle_sha256",
        "simulation_run_id",
        "simulation_artifact_sha256",
        "simulation",
    }

    assert bundle["additionalProperties"] is False
    assert set(bundle["properties"]) == expected_fields
    assert set(bundle["required"]) == expected_fields
    assert bundle["properties"]["bundle_schema_version"] == {
        "const": "phase11-local-simulation-evidence-bundle-v1",
        "title": "Bundle Schema Version",
        "type": "string",
    }
    assert bundle["properties"]["bundle_sha256"]["pattern"] == r"^[0-9a-f]{64}$"
    assert bundle["properties"]["simulation_run_id"]["format"] == "uuid"
    assert bundle["properties"]["simulation_artifact_sha256"]["pattern"] == (r"^[0-9a-f]{64}$")
    assert bundle["properties"]["simulation"] == {
        "$ref": "#/components/schemas/PaperSimulationArtifact"
    }


def test_phase11_nested_artifact_preserves_all_non_execution_literals() -> None:
    artifact = _openapi()["components"]["schemas"]["PaperSimulationArtifact"]
    properties = artifact["properties"]
    assert properties["synthetic"]["const"] is True
    assert properties["simulated_paper_only"]["const"] is True
    assert properties["local_mock_only"]["const"] is True
    assert properties["external_submission"]["const"] is False
    assert properties["external_routing_absent"]["const"] is True
    assert properties["live_path_absent"]["const"] is True
    assert properties["no_personalized_investment_advice"]["const"] is True
    assert properties["no_real_performance_claimed"]["const"] is True


def test_phase11_surface_has_no_mutation_download_or_external_route() -> None:
    schema = _openapi()
    assert set(schema["paths"][EVIDENCE_PATH]) == {"get"}
    rendered = " ".join(schema["paths"]).casefold()
    for forbidden in (
        "account",
        "broker",
        "credential",
        "download",
        "execute",
        "file",
        "live",
        "order",
        "provider",
        "refresh",
        "submit",
    ):
        assert forbidden not in rendered
