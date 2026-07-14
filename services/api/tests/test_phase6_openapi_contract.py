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
    assert request["properties"]["snapshot_ids"]["minItems"] == 1
    assert request["properties"]["snapshot_ids"]["maxItems"] == 10
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
        "phase6-a-pass-v2",
        "phase6-a-fail-cost-v2",
        "phase6-b-pass-v2",
        "phase6-b-fail-crash-v2",
        "phase6-c-pass-v2",
        "phase6-c-fail-corroboration-v2",
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
        "model_output_sets",
        "trial_economics",
        "attempts",
        "baseline_comparisons",
        "family_evidence",
        "phase5_evaluation",
        "regime_evidence",
        "confirmation_interval",
        "boundary_exclusions",
        "source_reproduction_audit",
        "feature_lineage_sha256",
        "snapshot_bundle_sha256",
        "pipeline_input_sha256",
        "configuration_sha256",
        "code_version_git_sha",
        "random_seed",
        "reason_codes",
        "warnings",
        "calendar_source_references",
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
        "model_output_sets",
        "trial_economics",
        "attempts",
        "baseline_comparisons",
    ):
        assert properties[field]["minItems"] >= 1

    assert properties["model_output_sets"]["minItems"] == 4
    assert properties["model_output_sets"]["maxItems"] == 4
    assert properties["trial_economics"]["minItems"] == 4
    assert properties["trial_economics"]["maxItems"] == 4
    assert properties["boundary_exclusions"]["minItems"] == 1
    assert properties["calendar_source_references"]["type"] == "array"

    output_set = components["ResearchModelOutputSet"]
    assert output_set["additionalProperties"] is False
    assert {
        "output_set_id",
        "output_set_sha256",
        "model_output_sha256",
        "trial_key",
        "model_id",
        "outputs",
        "ledger_cells",
    } <= set(output_set["properties"])
    assert output_set["properties"]["outputs"]["minItems"] >= 1
    assert output_set["properties"]["ledger_cells"]["minItems"] >= 1

    ledger_cell = components["ResearchLedgerCell"]
    assert ledger_cell["additionalProperties"] is False
    assert ledger_cell["properties"]["payoff_formula_id"]["const"] == (
        "phase6-long-flat-weight-times-label-quantized-v1"
    )
    assert {
        "model_output",
        "model_output_sha256",
        "synthetic_research_weight",
        "allocation_rule_id",
        "return_status",
        "label_t0_utc",
        "label_t1_utc",
        "label_value",
        "label_source_references",
        "label_sha256",
        "synthetic_gross_return",
    } <= set(ledger_cell["properties"])

    trial_economics = components["ResearchTrialEconomics"]
    assert trial_economics["additionalProperties"] is False
    assert {
        "schema_version",
        "ordinal",
        "trial_key",
        "model_id",
        "output_set_sha256",
        "sample_economics",
        "cost_set_sha256",
        "economics_sha256",
    } == set(trial_economics["properties"])
    assert trial_economics["properties"]["sample_economics"]["minItems"] == 1
    sample_economics = components["ResearchTrialSampleEconomics"]
    assert sample_economics["additionalProperties"] is False
    assert sample_economics["properties"]["cost_entries"]["minItems"] == 3
    assert sample_economics["properties"]["cost_entries"]["maxItems"] == 3

    confirmation = components["ResearchConfirmationInterval"]
    assert confirmation["additionalProperties"] is False
    assert confirmation["properties"]["label_value"]["type"] == "null"
    assert confirmation["properties"]["label_source_references"]["maxItems"] == 0
    assert confirmation["properties"]["label_opened"]["const"] is False
    boundary = components["ResearchBoundaryExclusion"]
    assert boundary["properties"]["label_value"]["type"] == "null"
    assert boundary["properties"]["label_source_references"]["maxItems"] == 0
    assert boundary["properties"]["label_opened"]["const"] is False

    reproduction = components["PreparedPipelineReproductionAudit"]
    assert reproduction["additionalProperties"] is False
    assert reproduction["properties"]["exact_match"]["const"] is True
    assert {
        "snapshot_set_sha256",
        "supplied_pipeline_input_sha256",
        "reproduced_pipeline_input_sha256",
        "supplied_payload_sha256",
        "reproduced_payload_sha256",
    } <= set(reproduction["properties"])

    regime = components["PreparedRegimeEvidence"]
    assert regime["additionalProperties"] is False
    assert set(regime["properties"]["evidence_state"]["enum"]) == {
        "available",
        "unavailable",
    }

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
        "train_samples",
        "source_references",
    } <= set(transform_fit)
    assert transform_fit["train_entity_ids"]["minItems"] == 2
    assert transform_fit["source_references"]["minItems"] >= 1
    assert transform_fit["train_samples"]["minItems"] >= 2
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
    assert family_b["rate_evidence_available"]["const"] is False
    assert family_b["rate_evidence_reason"]["const"] == "rate_regime_source_unavailable"
    assert family_b["crisis_geometry_available"]["const"] is False
    assert family_b["crisis_evidence_reason"]["const"] == ("crisis_window_geometry_unavailable")
    assert family_b["crash_evidence_complete"]["const"] is False
    assert family_b["crash_concentration"]["type"] == "null"
    assert family_b["crash_concentration_limit"]["type"] == "null"

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
