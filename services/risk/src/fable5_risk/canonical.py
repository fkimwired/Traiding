"""Canonical identities for immutable Phase 7 approval and risk artifacts."""

from __future__ import annotations

from uuid import UUID

from fable5_data.canonical import canonical_json_bytes as canonical_json_bytes
from fable5_data.canonical import domain_sha256 as domain_sha256
from fable5_data.canonical import uuid_from_sha256 as uuid_from_sha256

PHASE7_POLICY_HASH_DOMAIN = "phase7-approval-policy-v1"
PHASE7_SCOPE_HASH_DOMAIN = "phase7-approval-scope-v1"
PHASE7_AUTHORIZATION_HASH_DOMAIN = "phase7-human-authorization-evidence-v1"
PHASE7_RISK_INPUT_HASH_DOMAIN = "phase7-approval-risk-input-v1"
PHASE7_LINEAGE_HASH_DOMAIN = "phase7-phase6-approval-lineage-v1"
PHASE7_CHECK_HASH_DOMAIN = "phase7-approval-check-v1"
PHASE7_REVOCATION_EVIDENCE_HASH_DOMAIN = "phase7-revocation-evidence-profile-v1"
PHASE7_REVOCATION_REQUEST_HASH_DOMAIN = "phase7-authorization-revocation-request-v1"
PHASE7_REVOCATION_ARTIFACT_HASH_DOMAIN = "phase7-authorization-revocation-v1"
PHASE7_REVOCATION_SET_HASH_DOMAIN = "phase7-authorization-revocation-set-v1"
PHASE7_CURRENTNESS_HASH_DOMAIN = "phase7-approval-currentness-state-v1"
PHASE7_ASSESSMENT_REQUEST_HASH_DOMAIN = "phase7-approval-assessment-request-v1"
PHASE7_ASSESSMENT_ARTIFACT_HASH_DOMAIN = "phase7-approval-assessment-v1"

PHASE7_POLICY_NAMESPACE = UUID("5e62ae67-7d9f-5f07-9883-b0f8d00cd33a")
PHASE7_SCOPE_NAMESPACE = UUID("13294abe-cf1d-5601-8d3d-a598a1c84d80")
PHASE7_AUTHORIZATION_NAMESPACE = UUID("fa3bb88d-4b5f-5b59-a2ae-e2c18a2b052f")
PHASE7_RISK_INPUT_NAMESPACE = UUID("b7bc3b85-b2d7-55ad-8ca1-89bb8e16577f")
PHASE7_REVOCATION_EVIDENCE_NAMESPACE = UUID("8dfd305f-0903-586d-8d85-8277544fe064")
PHASE7_REVOCATION_NAMESPACE = UUID("971fe2ca-64c3-5c53-ac30-2c38a5ab04b8")
PHASE7_ASSESSMENT_NAMESPACE = UUID("88a24af5-ac54-5843-9280-c67cda6750fe")


def identity(namespace: UUID, sha256: str) -> UUID:
    """Return a deterministic UUID for a validated lowercase SHA-256 value."""

    return uuid_from_sha256(namespace, sha256)


__all__ = [name for name in globals() if name.startswith("PHASE7_")] + [
    "canonical_json_bytes",
    "domain_sha256",
    "identity",
]
