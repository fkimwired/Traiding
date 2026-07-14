"""Frozen Phase 6 research-pipeline declarations shared before and after evaluation."""

from __future__ import annotations

from decimal import Decimal

from fable5_data.contracts import AUTHORIZED_CAPABILITIES
from fable5_mapping.models import CanonicalFamily

from fable5_research.canonical import PHASE6_SPECIFICATION_HASH_DOMAIN, domain_sha256
from fable5_research.contracts import (
    PolicyDeclaration,
    ResearchPipelineSpecification,
    WalkForwardDeclaration,
)

_AUDIT_FIELDS = (
    "artifact_sha256",
    "attempts",
    "code_version_git_sha",
    "configuration_sha256",
    "created_at_utc",
    "feature_lineage_sha256",
    "mapping_id",
    "phase5_evaluation",
    "pipeline_input_sha256",
    "random_seed",
    "reason_codes",
    "snapshot_bundle_sha256",
    "snapshot_ids",
    "specification_sha256",
    "warnings",
)

FAMILY_B_COST_VOLATILITY_PROJECTION_ID = "phase6-family-b-cost-volatility-1e-8-half-even-v1"
FAMILY_B_COST_VOLATILITY_QUANTUM_TEXT = "0.00000001"
FAMILY_B_COST_VOLATILITY_QUANTUM = Decimal(FAMILY_B_COST_VOLATILITY_QUANTUM_TEXT)
FAMILY_B_TRANSACTION_COST_MODEL_ID = (
    "phase5-component-cost-model-v1-with-" + FAMILY_B_COST_VOLATILITY_PROJECTION_ID
)


def _specification_content(family: CanonicalFamily) -> dict[str, object]:
    required_capabilities = tuple(sorted(AUTHORIZED_CAPABILITIES[family], key=str))
    common: dict[str, object] = {
        "schema_version": "phase6-research-specification-v2",
        "specification_id": f"phase6-{family.value.lower()}-research-pipeline",
        "specification_version": "v2",
        "family": family,
        "score_semantics": "research_score_only",
        "required_capabilities": required_capabilities,
        "label_interval_rule": "decision time through two later UTC research sessions",
        "transaction_cost_model_id": "phase5-component-cost-model-v1",
        "slippage_model_id": "component-separated-slippage-v1",
        "walk_forward": WalkForwardDeclaration(
            train_mode="expanding_past_only",
            outer_fold_count=2,
            inner_fold_count=2,
        ),
        "risk_limits": (
            PolicyDeclaration(name="max_drawdown", value=Decimal("0.25"), units="ratio"),
            PolicyDeclaration(name="max_turnover", value=Decimal("1.00"), units="ratio"),
            PolicyDeclaration(
                name="max_single_observation_exposure",
                value=Decimal("0.10"),
                units="ratio",
            ),
        ),
        "required_audit_fields": _AUDIT_FIELDS,
        "pass_research_is_not_paper_approval": True,
        "no_real_performance_claimed": True,
    }
    if family is CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING:
        return {
            **common,
            "signal_definition": (
                "Sector-history-relative cross-sectional rank and frozen linear composite of "
                "six point-in-time features; output is an explainable research score only."
            ),
            "target_forecast_horizon": "two UTC research sessions",
            "feature_names": (
                "liquidity",
                "momentum",
                "quality",
                "turnover",
                "value",
                "volatility",
            ),
            "llm_role": "absent",
            "no_image_or_chart_pattern_classifier": True,
        }
    if family is CanonicalFamily.B_TIME_SERIES_MOMENTUM_REGIME:
        return {
            **common,
            "transaction_cost_model_id": FAMILY_B_TRANSACTION_COST_MODEL_ID,
            "signal_definition": (
                "Corporate-action-aware lagged-return and realized-volatility inputs kept "
                "separate from raw nominal trend-strength and drawdown controls; output is a "
                "research score only."
            ),
            "target_forecast_horizon": "two UTC research sessions",
            "feature_names": (
                "drawdown",
                "lagged_return",
                "realized_volatility",
                "trend_strength",
            ),
            "llm_role": "absent",
            "no_image_or_chart_pattern_classifier": True,
        }
    return {
        **common,
        "signal_definition": (
            "Versioned structured official-event text features supplied to a conventional "
            "downstream model and compared with a non-text baseline; research score only."
        ),
        "target_forecast_horizon": "two UTC research sessions after document availability",
        "feature_names": (
            "direction",
            "event_tag",
            "novelty",
            "risk_change",
            "uncertainty",
        ),
        "llm_role": "structured_text_extraction_only",
        "no_image_or_chart_pattern_classifier": True,
    }


def build_specification(family: CanonicalFamily) -> ResearchPipelineSpecification:
    content = _specification_content(family)
    return ResearchPipelineSpecification.model_validate(
        {
            **content,
            "specification_sha256": domain_sha256(PHASE6_SPECIFICATION_HASH_DOMAIN, content),
        }
    )


__all__ = [
    "FAMILY_B_COST_VOLATILITY_PROJECTION_ID",
    "FAMILY_B_COST_VOLATILITY_QUANTUM",
    "FAMILY_B_COST_VOLATILITY_QUANTUM_TEXT",
    "FAMILY_B_TRANSACTION_COST_MODEL_ID",
    "build_specification",
]
