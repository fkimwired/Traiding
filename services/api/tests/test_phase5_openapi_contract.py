from __future__ import annotations

import re
from typing import Any, cast
from unittest.mock import MagicMock

from fable5_api.evaluations import outcome_router, policy_router, report_router
from fable5_backtester.workflow import EvaluationWorkflow
from fastapi import FastAPI


def _openapi() -> dict[str, Any]:
    app = FastAPI()
    app.state.evaluation_workflow = MagicMock(spec=EvaluationWorkflow)
    app.include_router(policy_router)
    app.include_router(report_router)
    app.include_router(outcome_router)
    return app.openapi()


def _response_schema(operation: dict[str, Any], status_code: str) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        operation["responses"][status_code]["content"]["application/json"]["schema"],
    )


def test_phase5_openapi_surface_is_exact_create_read_list() -> None:
    schema = _openapi()
    paths = schema["paths"]

    assert {path: set(item) for path, item in paths.items()} == {
        "/v1/evaluation-policies": {"get", "post"},
        "/v1/evaluation-policies/{policy_id}/versions/{policy_version}": {"get"},
        "/v1/evaluation-reports": {"get", "post"},
        "/v1/evaluation-reports/{artifact_id}": {"get"},
        "/v1/evaluation-outcomes": {"get"},
        "/v1/evaluation-outcomes/{outcome_id}": {"get"},
    }

    policy_collection = paths["/v1/evaluation-policies"]
    policy_detail = paths["/v1/evaluation-policies/{policy_id}/versions/{policy_version}"]
    report_collection = paths["/v1/evaluation-reports"]
    report_detail = paths["/v1/evaluation-reports/{artifact_id}"]
    outcome_collection = paths["/v1/evaluation-outcomes"]
    outcome_detail = paths["/v1/evaluation-outcomes/{outcome_id}"]

    assert policy_collection["post"]["requestBody"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/EvaluationPolicyCreateRequest"
    }
    assert report_collection["post"]["requestBody"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/EvaluationRunCreateRequest"
    }
    assert _response_schema(policy_collection["post"], "201") == {
        "$ref": "#/components/schemas/FrozenEvaluationPolicy"
    }
    assert _response_schema(report_collection["post"], "201") == {
        "$ref": "#/components/schemas/EvaluationReport"
    }
    expected_policy_422 = [
        {"$ref": "#/components/schemas/EvaluationBlockedResult"},
        {"$ref": "#/components/schemas/EvaluationValidationErrorResponse"},
    ]
    expected_report_422 = [
        {"$ref": "#/components/schemas/BlockedEvaluationOutcome"},
        {"$ref": "#/components/schemas/EvaluationValidationErrorResponse"},
    ]
    assert _response_schema(policy_collection["post"], "422")["anyOf"] == (expected_policy_422)
    assert _response_schema(report_collection["post"], "422")["anyOf"] == (expected_report_422)

    policy_list = _response_schema(policy_collection["get"], "200")
    report_list = _response_schema(report_collection["get"], "200")
    assert policy_list["type"] == "array"
    assert policy_list["items"] == {"$ref": "#/components/schemas/FrozenEvaluationPolicy"}
    assert report_list["type"] == "array"
    assert report_list["items"] == {"$ref": "#/components/schemas/EvaluationReportSummary"}
    outcome_list = _response_schema(outcome_collection["get"], "200")
    assert outcome_list["type"] == "array"
    assert outcome_list["items"] == {"$ref": "#/components/schemas/BlockedEvaluationOutcome"}
    assert _response_schema(policy_detail["get"], "200") == {
        "$ref": "#/components/schemas/FrozenEvaluationPolicy"
    }
    assert _response_schema(report_detail["get"], "200") == {
        "$ref": "#/components/schemas/EvaluationReport"
    }
    assert _response_schema(outcome_detail["get"], "200") == {
        "$ref": "#/components/schemas/BlockedEvaluationOutcome"
    }

    for collection in (policy_collection, report_collection, outcome_collection):
        limit = collection["get"]["parameters"][0]
        assert limit["name"] == "limit"
        assert limit["required"] is False
        assert limit["schema"] == {
            "default": 100,
            "maximum": 100,
            "minimum": 1,
            "title": "Limit",
            "type": "integer",
        }


def test_phase5_create_and_unprocessable_contracts_are_strict_and_server_authoritative() -> None:
    components = _openapi()["components"]["schemas"]
    policy_request = components["EvaluationPolicyCreateRequest"]
    run_request = components["EvaluationRunCreateRequest"]

    assert policy_request["additionalProperties"] is False
    assert set(policy_request["properties"]) == {"policy_id", "policy_version"}
    assert set(policy_request["required"]) == set(policy_request["properties"])
    assert run_request["additionalProperties"] is False
    assert set(run_request["properties"]) == {
        "policy_id",
        "policy_version",
        "mapping_id",
        "snapshot_ids",
        "fixture_id",
    }
    assert set(run_request["required"]) == set(run_request["properties"])
    assert not set(run_request["properties"]).intersection(
        {
            "metrics",
            "results",
            "hashes",
            "thresholds",
            "timestamps",
            "orders",
            "positions",
            "promotion_state",
        }
    )

    blocked = components["EvaluationBlockedResult"]
    assert blocked["additionalProperties"] is False
    assert set(blocked["properties"]) == {
        "status",
        "promotion_state",
        "reason_codes",
        "sanitized_message",
    }
    assert blocked["properties"]["status"]["const"] == "blocked"
    assert blocked["properties"]["promotion_state"]["enum"] == [
        "BLOCKED_MISSING_POLICY",
        "BLOCKED_UNCOMPUTABLE",
    ]

    validation = components["EvaluationValidationErrorResponse"]
    issue = components["EvaluationValidationIssue"]
    assert validation["additionalProperties"] is False
    assert set(validation["properties"]) == {"detail"}
    assert validation["required"] == ["detail"]
    assert validation["properties"]["detail"]["items"] == {
        "$ref": "#/components/schemas/EvaluationValidationIssue"
    }
    assert issue["additionalProperties"] is False
    assert set(issue["properties"]) == {"loc", "msg", "type"}
    assert set(issue["required"]) == set(issue["properties"])


def test_evaluation_report_schema_is_complete_and_exposes_all_gate_families() -> None:
    components = _openapi()["components"]["schemas"]
    report = components["EvaluationReport"]
    expected_properties = {
        "artifact_id",
        "artifact_type",
        "artifact_schema_version",
        "artifact_sha256",
        "request_fingerprint_sha256",
        "request_fingerprint_version",
        "config_hash",
        "evaluation_policy_id",
        "evaluation_policy_version",
        "evaluation_policy_sha256",
        "mapping_id",
        "mapping_version",
        "mapping_input_sha256",
        "snapshot_bundle_sha256",
        "data_snapshots",
        "source_observations",
        "sample_lineage",
        "sample_lineage_sha256",
        "provider_source_versions",
        "code_version_git_sha",
        "random_seed",
        "raw_trial_count",
        "effective_trial_count",
        "effective_trial_method",
        "created_at_utc",
        "decision_time_utc",
        "parent_artifact_ids",
        "fixture_id",
        "fixture_version",
        "fixture_sha256",
        "synthetic",
        "no_real_performance_claimed",
        "disclaimer",
        "promotion_state",
        "pass_research_is_not_paper_approval",
        "feature_specification",
        "label_specification",
        "trials",
        "folds",
        "preprocessing_fits",
        "oos_ledger",
        "cost_ledger",
        "metrics",
        "gates",
        "warnings",
        "reason_codes",
    }
    defaulted_properties = {
        "artifact_type",
        "artifact_schema_version",
        "request_fingerprint_version",
        "effective_trial_method",
        "fixture_version",
        "synthetic",
        "no_real_performance_claimed",
        "disclaimer",
        "pass_research_is_not_paper_approval",
    }

    assert report["additionalProperties"] is False
    assert set(report["properties"]) == expected_properties
    assert set(report["required"]) == expected_properties - defaulted_properties
    properties = report["properties"]
    assert properties["artifact_type"]["const"] == "synthetic_research_evaluation"
    assert properties["synthetic"]["const"] is True
    assert properties["no_real_performance_claimed"]["const"] is True
    assert properties["pass_research_is_not_paper_approval"]["const"] is True
    assert properties["disclaimer"]["const"] == (
        "Synthetic research only; no real performance or investment advice."
    )
    assert properties["gates"] == {
        "items": {"$ref": "#/components/schemas/GateResult"},
        "minItems": 12,
        "title": "Gates",
        "type": "array",
    }

    artifact_arrays = {
        "data_snapshots": "SnapshotEvidence",
        "trials": "TrialRecord",
        "folds": "FoldRecord",
        "preprocessing_fits": "PreprocessingFitRecord",
        "oos_ledger": "OosLedgerEntry",
        "cost_ledger": "CostLedgerEntry",
        "metrics": "MetricRecord",
        "gates": "GateResult",
    }
    for property_name, component_name in artifact_arrays.items():
        assert properties[property_name]["items"] == {
            "$ref": f"#/components/schemas/{component_name}"
        }
        assert properties[property_name]["minItems"] >= 1

    assert components["GateCode"]["enum"] == [
        "DATA_PIT",
        "CV_CHRONOLOGY",
        "PREPROCESSING",
        "TRIAL_REGISTRY",
        "DSR",
        "PBO",
        "COST_STRESS",
        "LEAKAGE",
        "SAMPLE_ADEQUACY",
        "REGIME",
        "RISK_LIMITS",
        "REPRODUCIBILITY",
    ]
    gate = components["GateResult"]
    assert gate["additionalProperties"] is False
    assert set(gate["required"]) == set(gate["properties"])

    assert components["PromotionState"]["enum"] == [
        "PASS_RESEARCH",
        "FAIL_REJECT",
        "BLOCKED_MISSING_POLICY",
        "BLOCKED_UNCOMPUTABLE",
        "RESEARCH_ONLY_REGIME_DEPENDENT",
    ]


def test_phase5_return_status_contract_is_explicit_nullable_and_policy_frozen() -> None:
    components = _openapi()["components"]["schemas"]

    assert components["ResearchReturnStatus"]["enum"] == [
        "observed",
        "no_trade",
        "delisted",
        "missing",
    ]
    assert components["MissingReturnPolicy"]["enum"] == ["block_missing_return_v1"]
    assert components["NoTradeReturnPolicy"]["enum"] == ["explicit_zero_research_observation_v1"]
    for schema_name in ("LabelSpecification", "SampleAdequacyPolicy"):
        properties = components[schema_name]["properties"]
        assert properties["missing_return_policy"] == {
            "$ref": "#/components/schemas/MissingReturnPolicy"
        }
        assert properties["no_trade_return_policy"] == {
            "$ref": "#/components/schemas/NoTradeReturnPolicy"
        }

    trial = components["TrialRecord"]["properties"]
    assert trial["return_statuses"]["items"] == {
        "$ref": "#/components/schemas/ResearchReturnStatus"
    }
    assert {"type": "null"} in trial["net_returns"]["items"]["anyOf"]
    assert trial["return_timestamps_utc"]["items"]["format"] == "date-time"

    oos = components["OosLedgerEntry"]["properties"]
    assert oos["return_status"]["$ref"] == ("#/components/schemas/ResearchReturnStatus")
    assert {"type": "null"} in oos["gross_return"]["anyOf"]
    assert {"type": "null"} in oos["baseline_net_return"]["anyOf"]

    cost = components["CostLedgerEntry"]["properties"]
    assert cost["return_status"] == {"$ref": "#/components/schemas/ResearchReturnStatus"}
    assert cost["fill_status"]["enum"] == [
        "filled",
        "capacity_rejected",
        "no_trade",
    ]


def test_phase5_source_lineage_contract_carries_snapshot_and_membership_identity() -> None:
    components = _openapi()["components"]["schemas"]

    policy = components["FrozenEvaluationPolicy"]
    assert policy["properties"]["strategy_family"] == {
        "$ref": "#/components/schemas/CanonicalFamily"
    }
    assert policy["properties"]["required_snapshot_capabilities"] == {
        "items": {"$ref": "#/components/schemas/DataCapability"},
        "minItems": 1,
        "title": "Required Snapshot Capabilities",
        "type": "array",
    }

    source = components["ResolvedSourceObservation"]
    assert source["additionalProperties"] is False
    assert set(source["required"]) == {"key", "normalized_observation", "disposition"}
    assert source["properties"]["key"] == {"$ref": "#/components/schemas/SourceObservationKey"}
    assert source["properties"]["normalized_observation"] == {
        "$ref": "#/components/schemas/NormalizedObservation"
    }

    source_ref = components["ResolvedSourceObservationRef"]
    assert source_ref["additionalProperties"] is False
    assert set(source_ref["required"]) == set(source_ref["properties"])
    assert {
        "capability",
        "snapshot_id",
        "snapshot_sha256",
        "raw_observation_id",
        "observation_revision_id",
        "normalized_observation_id",
        "raw_payload_sha256",
        "normalized_content_sha256",
    } == set(source_ref["properties"])

    lineage = components["SampleSourceLineage"]
    assert lineage["additionalProperties"] is False
    assert "membership_source_observation_key" in lineage["required"]
    assert lineage["properties"]["membership_source_observation_key"] == {
        "$ref": "#/components/schemas/SourceObservationKey"
    }
    assert lineage["properties"]["source_observation_refs"] == {
        "items": {"$ref": "#/components/schemas/ResolvedSourceObservationRef"},
        "minItems": 1,
        "title": "Source Observation Refs",
        "type": "array",
    }


def test_phase5_schema_has_no_paper_live_order_or_position_paths_or_types() -> None:
    schema = _openapi()
    forbidden = ("paper", "live", "order", "position")

    for path, operations in schema["paths"].items():
        assert not any(token in path.lower() for token in forbidden)
        assert set(operations).issubset({"get", "post"})

    for component_name, component in schema["components"]["schemas"].items():
        name_tokens = {
            token.lower()
            for token in re.findall(r"[A-Z]+(?=[A-Z]|$)|[A-Z]?[a-z]+|\d+", component_name)
        }
        assert not name_tokens.intersection(forbidden)
        properties = component.get("properties", {})
        assert not {"paper_approval", "live", "orders", "positions"}.intersection(properties)

    promotion_values = set(schema["components"]["schemas"]["PromotionState"]["enum"])
    assert "APPROVED_PAPER" not in promotion_values
    assert "PAPER_APPROVED" not in promotion_values
    assert "LIVE" not in promotion_values
