"""Canonical identities and frozen policy material for Phase 14."""

from __future__ import annotations

from typing import Final
from uuid import UUID

from fable5_data.canonical import canonical_json_bytes as canonical_json_bytes
from fable5_data.canonical import canonicalize as canonicalize
from fable5_data.canonical import domain_sha256 as domain_sha256
from fable5_data.canonical import uuid_from_sha256

PHASE14_REQUEST_HASH_DOMAIN: Final = "phase14-research-ingestion-eligibility-request-v1"
PHASE14_PAYLOAD_HASH_DOMAIN: Final = "phase14-research-ingestion-eligibility-payload-v1"
PHASE14_PAYLOAD_MANIFEST_HASH_DOMAIN: Final = (
    "phase14-research-ingestion-eligibility-payload-manifest-v1"
)
PHASE14_CHECK_HASH_DOMAIN: Final = "phase14-research-ingestion-eligibility-check-v1"
PHASE14_ARTIFACT_HASH_DOMAIN: Final = "phase14-research-ingestion-eligibility-artifact-v1"
PHASE14_POLICY_HASH_DOMAIN: Final = "phase14-research-ingestion-eligibility-policy-v1"

PHASE14_ASSESSMENT_NAMESPACE: Final = UUID("7eb85ca3-2d66-5e1e-b291-784b9352fe59")
PHASE14_POLICY_ID: Final = "phase14-research-ingestion-eligibility-policy-v1"

PHASE14_CAPABILITY_VALUES: Final = (
    "SECURITY_MASTER_STABLE_IDENTITY",
    "POINT_IN_TIME_UNIVERSE_MEMBERSHIP",
    "RAW_OHLCV_AVAILABILITY",
    "CORPORATE_ACTION_ANNOUNCEMENT_REVISION",
    "DELISTING_RETURN_SEMANTICS",
    "AS_REPORTED_FUNDAMENTAL_REVISION",
)

PHASE14_CHECK_VALUES: Final = (
    "QUALIFICATION_IDENTITY_INTEGRITY",
    "QUALIFICATION_SOURCE_KIND_ALLOWED",
    "QUALIFICATION_OUTCOME_ELIGIBLE_OR_MOCK",
    "CAPABILITY_MANIFEST_COMPLETE_PASSING",
    "QUALIFICATION_CHECKS_COMPLETE_PASSING",
    "EXTERNAL_REQUEST_EVIDENCE_COMPLETE_OR_MOCK",
    "INDEPENDENT_RIGHTS_REFERENCE_PRESENT_OR_MOCK",
    "USE_RIGHTS_CURRENT_OR_MOCK",
    "USE_RIGHTS_SCOPE_SUFFICIENT_OR_MOCK",
    "LICENSED_PAYLOAD_ABSENT",
    "RESEARCH_SNAPSHOT_ABSENT",
    "PROMOTION_EXECUTION_AUTHORITY_ABSENT",
)

PHASE14_BOUNDARY_VALUES: Final = {
    "external_request_performed": False,
    "provider_payload_persisted": False,
    "research_ingestion_authorized": False,
    "research_snapshot_created": False,
    "research_data_eligible": False,
    "research_run_created": False,
    "research_run_authorized": False,
    "research_executed": False,
    "performance_computed": False,
    "pass_research_granted": False,
    "strategy_promotion_authorized": False,
    "paper_approval_granted": False,
    "strategy_execution_eligible": False,
    "execution_authorized": False,
    "order_submission_authorized": False,
    "live_path_absent": True,
    "no_personalized_investment_advice": True,
    "no_real_performance_claimed": True,
}

PHASE14_POLICY_SHA256: Final = domain_sha256(
    PHASE14_POLICY_HASH_DOMAIN,
    {
        "policy_id": PHASE14_POLICY_ID,
        "source_artifact_schema_version": "phase13-pit-qualification-v1",
        "capabilities": PHASE14_CAPABILITY_VALUES,
        "checks": PHASE14_CHECK_VALUES,
        "outcomes": ("MOCK_PROOF_COMPLETE", "BLOCKED"),
        "statuses": ("PASS", "BLOCKED", "UNCOMPUTABLE"),
        "mock_only_positive_outcome": True,
        "boundary_values": PHASE14_BOUNDARY_VALUES,
    },
)


def identity(namespace: UUID, sha256: str) -> UUID:
    """Derive a deterministic UUID from a validated lowercase SHA-256 value."""

    return uuid_from_sha256(namespace, sha256)


__all__ = [name for name in globals() if name.startswith("PHASE14_")] + [
    "canonical_json_bytes",
    "canonicalize",
    "domain_sha256",
    "identity",
]
