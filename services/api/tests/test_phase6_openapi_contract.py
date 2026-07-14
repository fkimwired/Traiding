from __future__ import annotations

import re
from typing import Any, cast
from unittest.mock import MagicMock

from fable5_api.research import router
from fable5_research.workflow import ResearchWorkflow
from fastapi import FastAPI


def _openapi() -> dict[str, Any]:
    app = FastAPI()
    app.state.research_workflow = MagicMock(spec=ResearchWorkflow)
    app.include_router(router)
    return app.openapi()


def _response_schema(operation: dict[str, Any], status_code: str) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        operation["responses"][status_code]["content"]["application/json"]["schema"],
    )


def test_phase6_openapi_surface_is_exact_create_read_list() -> None:
    schema = _openapi()
    paths = schema["paths"]

    assert {path: set(item) for path, item in paths.items()} == {
        "/v1/research-runs": {"get", "post"},
        "/v1/research-runs/{run_id}": {"get"},
    }
    collection = paths["/v1/research-runs"]
    detail = paths["/v1/research-runs/{run_id}"]
    assert collection["post"]["requestBody"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ResearchRunCreateRequest"
    }
    assert _response_schema(collection["post"], "201") == {
        "$ref": "#/components/schemas/ResearchRunArtifact"
    }
    assert _response_schema(detail["get"], "200") == {
        "$ref": "#/components/schemas/ResearchRunArtifact"
    }
    listing = _response_schema(collection["get"], "200")
    assert listing == {
        "items": {"$ref": "#/components/schemas/ResearchRunSummary"},
        "title": "Response List Research Runs V1 Research Runs Get",
        "type": "array",
    }
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


def test_phase6_create_contract_is_strict_and_server_authoritative() -> None:
    components = _openapi()["components"]["schemas"]
    request = components["ResearchRunCreateRequest"]

    assert request["additionalProperties"] is False
    assert set(request["properties"]) == {
        "mapping_id",
        "snapshot_ids",
        "research_configuration_id",
    }
    assert set(request["required"]) == set(request["properties"])
    assert not set(request["properties"]).intersection(
        {
            "metrics",
            "hashes",
            "thresholds",
            "timestamps",
            "trial_results",
            "promotion_state",
            "verdict",
        }
    )
    assert set(components["ResearchConfigurationId"]["enum"]) == {
        "phase6-a-pass-v1",
        "phase6-a-fail-cost-v1",
        "phase6-b-pass-v1",
        "phase6-b-fail-crash-v1",
        "phase6-c-pass-v1",
        "phase6-c-fail-corroboration-v1",
    }

    blocked = components["ResearchRunBlockedResponse"]
    assert blocked["additionalProperties"] is False
    assert set(blocked["properties"]) == {
        "promotion_state",
        "reason_codes",
        "sanitized_message",
    }
    assert set(blocked["required"]) == set(blocked["properties"])
    unprocessable = _response_schema(_openapi()["paths"]["/v1/research-runs"]["post"], "422")
    assert unprocessable["anyOf"] == [
        {"$ref": "#/components/schemas/ResearchRunBlockedResponse"},
        {"$ref": "#/components/schemas/ResearchValidationErrorResponse"},
    ]


def test_phase6_artifact_exposes_complete_explainability_and_research_only_flags() -> None:
    components = _openapi()["components"]["schemas"]
    artifact = components["ResearchRunArtifact"]
    properties = artifact["properties"]

    assert artifact["additionalProperties"] is False
    assert {
        "specification",
        "snapshot_bindings",
        "feature_rows",
        "scores",
        "attempts",
        "baseline_comparisons",
        "family_evidence",
        "phase5_evaluation",
        "feature_lineage_sha256",
        "snapshot_bundle_sha256",
        "pipeline_input_sha256",
        "configuration_sha256",
        "code_version_git_sha",
        "random_seed",
        "reason_codes",
        "warnings",
    } <= set(properties)
    assert properties["synthetic"]["const"] is True
    assert properties["no_real_performance_claimed"]["const"] is True
    assert properties["pass_research_is_not_paper_approval"]["const"] is True
    assert properties["paper_approval_granted"]["const"] is False
    assert properties["disclaimer"]["const"] == (
        "Synthetic research only; no real performance or investment advice."
    )
    for field in (
        "snapshot_bindings",
        "feature_rows",
        "scores",
        "attempts",
        "baseline_comparisons",
    ):
        assert properties[field]["minItems"] >= 1

    feature_row = components["ResearchFeatureRow"]["properties"]
    assert {"label_value", "label_source_references"} <= set(feature_row)
    assert feature_row["label_source_references"]["minItems"] >= 1

    comparison = components["ResearchBaselineComparison"]["properties"]
    assert {
        "candidate_output_sha256",
        "baseline_output_sha256",
        "label_sha256",
        "evaluation_scope",
        "used_for_selection",
    } <= set(comparison)
    assert comparison["evaluation_scope"]["const"] == (
        "descriptive_all_prepared_rows_not_used_for_selection"
    )
    assert comparison["used_for_selection"]["const"] is False

    non_text = components["LaggedOhlcvBaselineEvidence"]
    assert non_text["additionalProperties"] is False
    assert {
        "sample_id",
        "decision_time_utc",
        "lagged_return",
        "intraday_range",
        "baseline_output",
        "source_references",
        "used_for_selection",
        "evidence_sha256",
    } <= set(non_text["properties"])
    assert non_text["properties"]["source_references"]["minItems"] == 2
    assert non_text["properties"]["source_references"]["maxItems"] == 2
    assert non_text["properties"]["used_for_selection"]["const"] is False


def test_phase6_family_contracts_cover_a_b_c_without_execution_semantics() -> None:
    components = _openapi()["components"]["schemas"]

    family_a = components["FamilyAEvidence"]["properties"]
    assert {
        "universe",
        "train_only_sector_fits",
        "cross_section_ranks",
        "frozen_feature_names",
        "transparent_model_id",
        "nonlinear_model_id",
        "baseline_comparison_ids",
        "capacity",
    } <= set(family_a)
    transform_fit = components["ResearchTransformFit"]["properties"]
    assert {
        "mean",
        "standard_deviation",
        "train_entity_ids",
        "source_references",
    } <= set(transform_fit)
    assert transform_fit["train_entity_ids"]["minItems"] == 2
    assert transform_fit["source_references"]["minItems"] >= 1
    assert family_a["cross_section_ranks"]["minItems"] >= 1
    cross_section_rank = components["CrossSectionRankEvidence"]["properties"]
    assert {
        "decision_time_utc",
        "eligible_members",
        "selected_entity_id",
        "selected_linear_rank",
        "selected_nonlinear_score",
        "evidence_sha256",
    } <= set(cross_section_rank)
    assert cross_section_rank["eligible_members"]["minItems"] >= 2

    family_b = components["FamilyBEvidence"]["properties"]
    assert family_b["lag_windows"]["minItems"] == 6
    assert family_b["lag_windows"]["maxItems"] == 6
    assert family_b["raw_nominal_bar_count"]["minimum"] == 253
    assert family_b["adjusted_return_observation_count"]["minimum"] == 252
    assert family_b["lifecycle_tests"]["minItems"] >= 3
    lifecycle_test = components["LifecycleTestEvidence"]["properties"]
    assert lifecycle_test["used_as_feature"]["const"] is False
    assert family_b["nominal_feature_price_basis"]["const"] == "raw_unadjusted"
    assert family_b["adjusted_return_formula_id"]["const"] == (
        "phase6-action-and-delisting-aware-return-v1"
    )
    assert family_b["no_image_candlestick_or_named_pattern_classifier"]["const"] is True

    family_c = components["FamilyCEvidence"]["properties"]
    assert family_c["prompt_model_drift_visible"]["const"] is True
    assert family_c["corrections_are_later_observations"]["const"] is True
    assert family_c["llm_is_extraction_only"]["const"] is True
    corroboration = components["SocialOfficialCorroboration"]["properties"]
    assert {"social_source_reference", "official_source_reference"} <= set(corroboration)
    assert corroboration["exact_match"]["const"] is True
    assert corroboration["contributes_standalone"]["const"] is False
    structured = components["StructuredTextFeatures"]
    assert set(structured["properties"]) == {
        "novelty",
        "direction",
        "uncertainty",
        "risk_change",
        "event_tags",
    }
    extraction = components["TextFeatureExtraction"]["properties"]
    assert extraction["output_boundary"]["const"] == "structured_features_only"
    for forbidden in (
        "label",
        "signal",
        "model_decision",
        "buy_sell_call",
        "allocation",
        "position_size",
        "promotion_outcome",
        "execution_instruction",
    ):
        assert forbidden not in extraction


def test_phase6_schema_has_no_phase7_execution_path_or_type() -> None:
    schema = _openapi()
    forbidden_path_terms = (
        "approval",
        "broker",
        "execution",
        "live",
        "order",
        "paper-trad",
        "position",
        "pre-order",
        "pre_order",
    )
    for path, operations in schema["paths"].items():
        assert not any(token in path.casefold() for token in forbidden_path_terms)
        assert set(operations) <= {"get", "post"}

    forbidden_type_tokens = {
        "approval",
        "broker",
        "execution",
        "live",
        "order",
        "position",
        "preorder",
    }
    for component_name in schema["components"]["schemas"]:
        name_tokens = {
            token.casefold()
            for token in re.findall(r"[A-Z]+(?=[A-Z]|$)|[A-Z]?[a-z]+|\d+", component_name)
        }
        assert not name_tokens.intersection(forbidden_type_tokens)
    promotion_values = set(schema["components"]["schemas"]["PromotionState"]["enum"])
    assert not {"APPROVED_PAPER", "PAPER_APPROVED", "LIVE"}.intersection(promotion_values)
