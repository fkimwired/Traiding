from __future__ import annotations

import re
from typing import Any, cast
from unittest.mock import MagicMock

from fable5_api.approvals import assessment_router, revocation_router
from fable5_api.main import app as full_app
from fable5_risk.workflow import ApprovalWorkflow
from fastapi import FastAPI

PHASE7_METHODS = {"get", "post", "put", "patch", "delete"}
PHASE7_PATH_TERMS = (
    "approval",
    "authorization",
    "revocation",
    "risk",
    "governance",
    "pre-order",
    "pre_order",
)
EXPECTED_PHASE7_SURFACE = {
    "/v1/approval-assessments": {"get", "post"},
    "/v1/approval-assessments/{assessment_id}": {"get"},
    "/v1/approval-revocations": {"get", "post"},
    "/v1/approval-revocations/{revocation_id}": {"get"},
}


def _openapi() -> dict[str, Any]:
    app = FastAPI()
    app.state.approval_workflow = MagicMock(spec=ApprovalWorkflow)
    app.include_router(assessment_router)
    app.include_router(revocation_router)
    return app.openapi()


def _response_schema(operation: dict[str, Any], status_code: str) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        operation["responses"][status_code]["content"]["application/json"]["schema"],
    )


def _phase7_surface(schema: dict[str, Any]) -> dict[str, set[str]]:
    surface: dict[str, set[str]] = {}
    for path, operations in schema["paths"].items():
        methods = set(operations).intersection(PHASE7_METHODS)
        tags = {
            tag
            for method, operation in operations.items()
            if method in PHASE7_METHODS and isinstance(operation, dict)
            for tag in operation.get("tags", [])
        }
        if (
            path in EXPECTED_PHASE7_SURFACE
            or "approval-governance" in tags
            or any(term in path.casefold() for term in PHASE7_PATH_TERMS)
        ):
            surface[path] = methods
    return surface


def test_phase7_openapi_surface_is_exact_create_read_list() -> None:
    schema = _openapi()
    paths = schema["paths"]

    assert {path: set(item) for path, item in paths.items()} == EXPECTED_PHASE7_SURFACE
    assert _phase7_surface(full_app.openapi()) == EXPECTED_PHASE7_SURFACE
    assessment_collection = paths["/v1/approval-assessments"]
    assessment_detail = paths["/v1/approval-assessments/{assessment_id}"]
    revocation_collection = paths["/v1/approval-revocations"]
    revocation_detail = paths["/v1/approval-revocations/{revocation_id}"]

    assert assessment_collection["post"]["requestBody"]["content"]["application/json"][
        "schema"
    ] == {"$ref": "#/components/schemas/ApprovalAssessmentCreateRequest"}
    assert _response_schema(assessment_collection["post"], "201") == {
        "$ref": "#/components/schemas/ApprovalAssessmentArtifact"
    }
    assert _response_schema(assessment_collection["post"], "422") == {
        "$ref": "#/components/schemas/ApprovalValidationErrorResponse"
    }
    assert _response_schema(assessment_detail["get"], "200") == {
        "$ref": "#/components/schemas/ApprovalAssessmentArtifact"
    }
    assert _response_schema(assessment_detail["get"], "422") == {
        "$ref": "#/components/schemas/ApprovalValidationErrorResponse"
    }
    assert _response_schema(assessment_collection["get"], "200")["items"] == {
        "$ref": "#/components/schemas/ApprovalAssessmentSummary"
    }
    assert _response_schema(assessment_collection["get"], "422") == {
        "$ref": "#/components/schemas/ApprovalValidationErrorResponse"
    }

    assert revocation_collection["post"]["requestBody"]["content"]["application/json"][
        "schema"
    ] == {"$ref": "#/components/schemas/ApprovalRevocationCreateRequest"}
    assert _response_schema(revocation_collection["post"], "201") == {
        "$ref": "#/components/schemas/AuthorizationRevocationArtifact"
    }
    assert _response_schema(revocation_collection["post"], "422") == {
        "$ref": "#/components/schemas/ApprovalValidationErrorResponse"
    }
    assert _response_schema(revocation_detail["get"], "200") == {
        "$ref": "#/components/schemas/AuthorizationRevocationArtifact"
    }
    assert _response_schema(revocation_detail["get"], "422") == {
        "$ref": "#/components/schemas/ApprovalValidationErrorResponse"
    }
    assert _response_schema(revocation_collection["get"], "200")["items"] == {
        "$ref": "#/components/schemas/AuthorizationRevocationSummary"
    }
    assert _response_schema(revocation_collection["get"], "422") == {
        "$ref": "#/components/schemas/ApprovalValidationErrorResponse"
    }

    assessment_parameters = {
        item["name"]: item["schema"] for item in assessment_collection["get"]["parameters"]
    }
    assert assessment_parameters == {
        "limit": {
            "default": 100,
            "maximum": 100,
            "minimum": 1,
            "title": "Limit",
            "type": "integer",
        }
    }
    revocation_parameters = {
        item["name"]: item["schema"] for item in revocation_collection["get"]["parameters"]
    }
    assert revocation_parameters["limit"] == assessment_parameters["limit"]
    assert revocation_parameters["human_authorization_evidence_id"]["anyOf"] == [
        {"format": "uuid", "type": "string"},
        {"type": "null"},
    ]


def test_phase7_surface_classifier_rejects_noncanonical_governance_or_risk_paths() -> None:
    schema = _openapi()
    schema["paths"]["/v1/risk-inputs"] = {
        "get": {"tags": ["approval-governance"]},
    }

    assert _phase7_surface(schema) != EXPECTED_PHASE7_SURFACE


def test_phase7_create_contracts_are_strict_reference_only_requests() -> None:
    components = _openapi()["components"]["schemas"]
    assessment = components["ApprovalAssessmentCreateRequest"]
    revocation = components["ApprovalRevocationCreateRequest"]

    assert assessment["additionalProperties"] is False
    assert set(assessment["properties"]) == {
        "research_run_id",
        "approval_policy_version_id",
        "approval_scope_version_id",
        "human_authorization_evidence_id",
        "risk_input_id",
    }
    assert set(assessment["required"]) == set(assessment["properties"])

    assert revocation["additionalProperties"] is False
    assert set(revocation["properties"]) == {
        "human_authorization_evidence_id",
        "revocation_evidence_id",
    }
    assert set(revocation["required"]) == set(revocation["properties"])

    forbidden_client_authority = {
        "approval",
        "approval_id",
        "approved",
        "outcome",
        "verdict",
        "promotion_state",
        "artifact_sha256",
        "request_fingerprint_sha256",
        "hashes",
        "thresholds",
        "created_at_utc",
        "timestamps",
        "risk_results",
        "checks",
        "expires_at_utc",
        "revoked",
        "revocation_state",
        "effective_at_utc",
        "metrics",
        "phase6_metrics",
    }
    assert not forbidden_client_authority.intersection(assessment["properties"])
    assert not forbidden_client_authority.intersection(revocation["properties"])


def test_phase7_response_contracts_are_synthetic_governance_only_and_non_executable() -> None:
    components = _openapi()["components"]["schemas"]
    assessment = components["ApprovalAssessmentArtifact"]
    assessment_summary = components["ApprovalAssessmentSummary"]
    revocation = components["AuthorizationRevocationArtifact"]
    revocation_summary = components["AuthorizationRevocationSummary"]

    for schema in (assessment, assessment_summary, revocation, revocation_summary):
        assert schema["additionalProperties"] is False
        properties = schema["properties"]
        assert properties["synthetic"]["const"] is True
        assert properties["simulated_paper_only"]["const"] is True
        assert properties["execution_authorized"]["const"] is False
        assert properties["execution_ready"]["const"] is False

    for schema in (assessment, assessment_summary, revocation):
        properties = schema["properties"]
        assert properties["no_personalized_investment_advice"]["const"] is True
        assert properties["no_real_performance_claimed"]["const"] is True

    assert set(components["ApprovalAssessmentOutcome"]["enum"]) == {
        "APPROVED_PAPER",
        "FAIL_REJECT",
    }
    assert "APPROVED_PAPER" not in set(components["PromotionState"]["enum"])
    assert assessment["properties"]["checks"]["minItems"] == 25
    assert assessment["properties"]["phase6_lineage"] == {
        "$ref": "#/components/schemas/Phase6ApprovalLineage"
    }


def test_phase7_schema_contains_no_broker_or_execution_resource_type() -> None:
    schema = _openapi()
    forbidden_path_terms = (
        "broker",
        "order",
        "position",
        "fill",
        "intent",
        "execution",
        "live",
        "paper-trad",
    )
    for path, operations in schema["paths"].items():
        assert not any(token in path.casefold() for token in forbidden_path_terms)
        assert set(operations) <= {"get", "post"}

    forbidden_type_tokens = {
        "broker",
        "order",
        "position",
        "fill",
        "intent",
        "execution",
        "live",
    }
    for component_name in schema["components"]["schemas"]:
        name_tokens = {
            token.casefold()
            for token in re.findall(r"[A-Z]+(?=[A-Z]|$)|[A-Z]?[a-z]+|\d+", component_name)
        }
        assert not name_tokens.intersection(forbidden_type_tokens)
