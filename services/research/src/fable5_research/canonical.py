"""Canonical identities for immutable Phase 6 research artifacts."""

from __future__ import annotations

from uuid import UUID, uuid5

from fable5_data.canonical import (
    canonical_json_bytes as canonical_json_bytes,
)
from fable5_data.canonical import (
    domain_sha256 as domain_sha256,
)

PHASE6_SPECIFICATION_HASH_DOMAIN = "phase6-research-specification-v2"
PHASE6_CONFIGURATION_HASH_DOMAIN = "phase6-research-configuration-v2"
PHASE6_FEATURE_ROW_HASH_DOMAIN = "phase6-research-feature-row-v1"
PHASE6_FEATURE_LINEAGE_HASH_DOMAIN = "phase6-research-feature-lineage-v1"
PHASE6_SCORE_HASH_DOMAIN = "phase6-research-score-output-v1"
PHASE6_EXPLANATION_HASH_DOMAIN = "phase6-research-explanation-v1"
PHASE6_BASELINE_HASH_DOMAIN = "phase6-research-baseline-comparison-v1"
PHASE6_TEXT_EXTRACTION_HASH_DOMAIN = "phase6-text-feature-extraction-v1"
PHASE6_CORROBORATION_HASH_DOMAIN = "phase6-social-official-corroboration-v1"
PHASE6_SNAPSHOT_BINDING_HASH_DOMAIN = "phase6-research-snapshot-binding-v1"
PHASE6_ATTEMPT_HASH_DOMAIN = "phase6-research-attempt-v1"
PHASE6_TRIAL_SET_HASH_DOMAIN = "phase6-phase5-trial-set-v1"
PHASE6_REQUEST_HASH_DOMAIN = "phase6-research-request-v2"
PHASE6_ARTIFACT_HASH_DOMAIN = "phase6-research-artifact-v2"
PHASE6_PIPELINE_INPUT_HASH_DOMAIN = "phase6-prepared-pipeline-input-v2"
PHASE6_TRANSFORM_FIT_HASH_DOMAIN = "phase6-train-only-transform-fit-v1"
PHASE6_MODEL_OUTPUT_SET_HASH_DOMAIN = "phase6-model-output-set-v2"
PHASE6_LABEL_SET_HASH_DOMAIN = "phase6-label-set-v1"
PHASE6_CROSS_SECTION_MEMBER_HASH_DOMAIN = "phase6-cross-section-rank-member-v1"
PHASE6_CROSS_SECTION_RANK_HASH_DOMAIN = "phase6-cross-section-rank-evidence-v1"
PHASE6_LIFECYCLE_TEST_HASH_DOMAIN = "phase6-lifecycle-test-evidence-v1"
PHASE6_LAGGED_OHLCV_BASELINE_HASH_DOMAIN = "phase6-lagged-ohlcv-baseline-evidence-v1"
PHASE6_REGIME_EVIDENCE_HASH_DOMAIN = "phase6-prepared-regime-evidence-v2"
PHASE6_CONFIRMATION_INTERVAL_HASH_DOMAIN = "phase6-label-blind-confirmation-interval-v1"
PHASE6_BOUNDARY_EXCLUSION_HASH_DOMAIN = "phase6-confirmation-boundary-exclusion-v1"
PHASE6_TRIAL_ALLOCATION_HASH_DOMAIN = "phase6-trial-allocation-evidence-v1"
PHASE6_TRIAL_COST_SET_HASH_DOMAIN = "phase6-trial-cost-ledger-set-v1"
PHASE6_TRIAL_ECONOMICS_HASH_DOMAIN = "phase6-trial-economics-v1"
PHASE6_REPRODUCTION_AUDIT_HASH_DOMAIN = "phase6-prepared-source-reproduction-audit-v1"
PHASE6_REPRODUCTION_PAYLOAD_HASH_DOMAIN = "phase6-prepared-source-reproduction-payload-v1"
PHASE6_REPRODUCTION_SNAPSHOT_SET_HASH_DOMAIN = "phase6-prepared-source-reproduction-snapshot-set-v1"

PHASE6_RUN_NAMESPACE = UUID("09972cb7-9a87-543c-a70a-3835ee8e593c")
PHASE6_FEATURE_ROW_NAMESPACE = UUID("5b7df50c-9da2-5f51-9b71-39187e491ce7")
PHASE6_SCORE_NAMESPACE = UUID("e52726b7-d313-57d4-85f9-49c96816cf4e")
PHASE6_COMPARISON_NAMESPACE = UUID("4b2f565f-b0bc-53dd-9097-da44e2cf6d88")
PHASE6_EXTRACTION_NAMESPACE = UUID("aa25921e-a1a6-59e2-ae53-424560158b4c")
PHASE6_CORROBORATION_NAMESPACE = UUID("573eeb0a-15fe-531a-9e60-e9972c535ba0")
PHASE6_FIT_NAMESPACE = UUID("e1371e3a-5a6d-5f54-ab34-c413ab3cb707")
PHASE6_CONFIRMATION_NAMESPACE = UUID("e1f51308-3ab0-56d3-9ad8-26258a3b97bd")
PHASE6_BOUNDARY_EXCLUSION_NAMESPACE = UUID("622404af-e922-599f-98dd-2d7ccb32176c")
PHASE6_REPRODUCTION_AUDIT_NAMESPACE = UUID("2c2b48ec-b10c-5de8-8e77-f32455baa214")


def identity(namespace: UUID, sha256: str) -> UUID:
    """Return a deterministic UUID for a validated lowercase SHA-256 value."""

    if len(sha256) != 64 or any(character not in "0123456789abcdef" for character in sha256):
        raise ValueError("sha256 must contain 64 lowercase hexadecimal characters")
    return uuid5(namespace, sha256)


__all__ = [name for name in globals() if name.startswith("PHASE6_")] + [
    "canonical_json_bytes",
    "domain_sha256",
    "identity",
]
