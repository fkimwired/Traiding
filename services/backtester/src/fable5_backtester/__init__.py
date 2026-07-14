"""Fail-closed Phase 5 evaluation contracts and synthetic research engine."""

from fable5_backtester.contracts import (
    PHASE5_ARTIFACT_SCHEMA_VERSION,
    PHASE5_POLICY_SCHEMA_VERSION,
    EvaluationReport,
    EvaluationRunCreateRequest,
    FrozenEvaluationPolicy,
    PromotionState,
)

__all__ = [
    "PHASE5_ARTIFACT_SCHEMA_VERSION",
    "PHASE5_POLICY_SCHEMA_VERSION",
    "EvaluationReport",
    "EvaluationRunCreateRequest",
    "FrozenEvaluationPolicy",
    "PromotionState",
]
