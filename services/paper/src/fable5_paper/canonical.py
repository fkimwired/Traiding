"""Canonical hashes and deterministic identities for Phase 10."""

from __future__ import annotations

from uuid import UUID

from fable5_data.canonical import canonical_json_bytes as canonical_json_bytes
from fable5_data.canonical import domain_sha256 as domain_sha256
from fable5_data.canonical import uuid_from_sha256 as uuid_from_sha256

PHASE10_CONFIGURATION_HASH_DOMAIN = "phase10-local-simulation-configuration-v1"
PHASE10_CHECK_HASH_DOMAIN = "phase10-local-simulation-check-v1"
PHASE10_LEDGER_HASH_DOMAIN = "phase10-local-simulation-ledger-v1"
PHASE10_REVALIDATION_HASH_DOMAIN = "phase10-local-simulation-revalidation-v1"
PHASE10_CURRENTNESS_HASH_DOMAIN = "phase10-local-simulation-currentness-v1"
PHASE10_REQUEST_HASH_DOMAIN = "phase10-local-simulation-request-v1"
PHASE10_ARTIFACT_HASH_DOMAIN = "phase10-local-simulation-artifact-v1"
PHASE10_MOCK_SNAPSHOT_HASH_DOMAIN = "phase10-local-mock-snapshot-v1"
PHASE10_MOCK_OBSERVATION_HASH_DOMAIN = "phase10-local-mock-observation-v1"

PHASE10_RUN_NAMESPACE = UUID("94855828-a04c-54f9-ae66-dd00ef7a1010")
PHASE10_CONFIGURATION_NAMESPACE = UUID("156cc8af-3b68-508b-b7f2-8bb1818f1010")
PHASE10_SNAPSHOT_NAMESPACE = UUID("2e684f7f-1de2-52fc-8639-b614b2441010")
PHASE10_OBSERVATION_NAMESPACE = UUID("0d5dfb4a-bb6a-5558-a138-1c05d8581010")
PHASE10_LEDGER_NAMESPACE = UUID("052c40b0-7781-57d9-942a-651518c41010")
PHASE10_REVALIDATION_NAMESPACE = UUID("ce090e4f-afab-55ef-a6c3-ec4292ec1010")


def identity(namespace: UUID, sha256: str) -> UUID:
    """Return a deterministic UUID for a validated lowercase SHA-256 value."""

    return uuid_from_sha256(namespace, sha256)


__all__ = [name for name in globals() if name.startswith("PHASE10_")] + [
    "canonical_json_bytes",
    "domain_sha256",
    "identity",
]
