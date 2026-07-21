"""Canonical constants for the Phase 23 RTDSM current-use-rights review."""

from __future__ import annotations

from types import MappingProxyType
from typing import Final
from uuid import UUID

from fable5_data.canonical import canonical_json_bytes as canonical_json_bytes
from fable5_data.canonical import canonicalize as canonicalize
from fable5_data.canonical import domain_sha256 as domain_sha256
from fable5_data.canonical import uuid_from_sha256

PHASE23_ARTIFACT_SCHEMA_VERSION: Final = "phase23-family-a-rtdsm-current-use-rights-review-v1"
PHASE23_SOURCE_SCHEMA_VERSION: Final = "phase23-family-a-rtdsm-public-terms-source-v1"
PHASE23_FINDING_SCHEMA_VERSION: Final = "phase23-family-a-rtdsm-rights-finding-v1"
PHASE23_REQUIREMENT_SCHEMA_VERSION: Final = "phase23-family-a-future-requirement-status-v1"

PHASE23_ARTIFACT_HASH_DOMAIN: Final = PHASE23_ARTIFACT_SCHEMA_VERSION
PHASE23_SOURCE_HASH_DOMAIN: Final = PHASE23_SOURCE_SCHEMA_VERSION
PHASE23_FINDING_HASH_DOMAIN: Final = PHASE23_FINDING_SCHEMA_VERSION
PHASE23_REQUIREMENT_HASH_DOMAIN: Final = PHASE23_REQUIREMENT_SCHEMA_VERSION
PHASE23_SOURCES_MANIFEST_HASH_DOMAIN: Final = "phase23-rtdsm-public-terms-sources-manifest-v1"
PHASE23_FINDINGS_MANIFEST_HASH_DOMAIN: Final = "phase23-rtdsm-rights-findings-manifest-v1"
PHASE23_REQUIREMENTS_MANIFEST_HASH_DOMAIN: Final = "phase23-rtdsm-future-requirements-manifest-v1"
PHASE23_POLICY_ID: Final = "phase23-family-a-rtdsm-current-use-rights-review-policy-v1"
PHASE23_POLICY_HASH_DOMAIN: Final = PHASE23_POLICY_ID
PHASE23_ARTIFACT_NAMESPACE: Final = UUID("94ac57dc-a239-5b13-b76e-32fb57ba1e3e")

PHASE23_ACCEPTED_PHASE22_COMMIT_SHA: Final = "1c07fbe8e23950e8c9f910b30473c900c0bf3e21"
PHASE23_ACCEPTED_PHASE22_TREE_SHA: Final = "1261f5a9da883e14a894b33e583068681f8cf459"
PHASE23_PHASE22_MERGE_COMMIT_SHA: Final = "7f3bf3df029a894660f0e47dda1056bd32dca297"
PHASE23_PHASE22_ARTIFACT_ID: Final = "9d763c2d-af50-5403-9646-50a88c962bd7"
PHASE23_PHASE22_ARTIFACT_SHA256: Final = (
    "6f6079b69838cdd292f3d426c0b1e23deeec35eaeed9f4129aa129585913abe1"
)
PHASE23_PHASE22_POLICY_SHA256: Final = (
    "dbd7f77b646d3386d17e889cd81a3a25aed099bfc3451c37844d02d87404ba5f"
)
PHASE23_PHASE22_SOURCES_MANIFEST_SHA256: Final = (
    "870a238d76b5dc09630eee32c74f12d0e284b43ef6afee048b28817d62e7308a"
)
PHASE23_PHASE22_PRODUCTS_MANIFEST_SHA256: Final = (
    "138d492ed2e0975fe30534ab92724d822e4765e1a76137324f837272c0278796"
)
PHASE23_PHASE22_REQUIREMENTS_MANIFEST_SHA256: Final = (
    "109f4681e68ccc045c3e96eb662fb6023d4ef42f30d07a6339a696571d0d4d27"
)
PHASE23_PRODUCT_CODE: Final = "PHILADELPHIA_FED_REAL_TIME_DATA_SET_FOR_MACROECONOMISTS"
PHASE23_PHASE22_PRODUCT_SHA256: Final = (
    "59a206777d9f48737c11c557ffdabd5a80c66159822356a7726ed314436da067"
)
PHASE23_FAMILY: Final = "A_CROSS_SECTIONAL_EQUITY_RANKING"
PHASE23_FROZEN_AT_UTC: Final = "2026-07-21T00:30:00.000000Z"
PHASE23_REVIEWED_ON: Final = "2026-07-20"
PHASE23_OUTCOME: Final = "BLOCKED"
PHASE23_REVIEW_STATE: Final = "PUBLIC_TERMS_RIGHTS_REVIEW_FROZEN"
PHASE23_AGGREGATE_CONCLUSION: Final = (
    "BLOCKED_PUBLIC_TERMS_INSUFFICIENT_FOR_PERSISTENT_AUTOMATED_MODEL_USE"
)
PHASE23_BLOCK_REASON: Final = (
    "The official pages state research-purpose use, but they do not expressly resolve persistent "
    "storage, automated model integration, derived data, retention or deletion, attribution, or "
    "third-party content for Fable5's exact intended use; the terms can change without notice."
)

# code, title, publisher, URL, publisher last update, locator, conservative fact
PHASE23_SOURCE_ROWS: Final = (
    (
        "PHILADELPHIA_FED_ONLINE_TERMS",
        "Online Terms of Use and Privacy Notice",
        "Federal Reserve Bank of Philadelphia",
        "https://www.philadelphiafed.org/about-us/privacy-notice",
        "2026-04-01",
        "Online Terms of Use: Introduction and Scope; Appropriate Use; Disclaimer",
        (
            "The terms limit content use to informational, educational, and research purposes; "
            "require owner permission for copyrighted material; prohibit excessive access; "
            "disclaim noninfringement; and may change without notice."
        ),
    ),
    (
        "PHILADELPHIA_FED_RTDSM_OVERVIEW",
        "Real-Time Data Set for Macroeconomists",
        "Federal Reserve Bank of Philadelphia",
        "https://www.philadelphiafed.org/surveys-and-data/real-time-data-research/real-time-data-set-for-macroeconomists",
        "2026-06-29",
        "Real-Time Data Set for Macroeconomists; Historical Data",
        (
            "The page states that RTDSM may be used by macroeconomic researchers to verify "
            "empirical results, analyze policy, or forecast and documents complete-vintage-history "
            "downloads."
        ),
    ),
    (
        "PHILADELPHIA_FED_RTDSM_CHANGES",
        "Changes to the Real-Time Data Set",
        "Federal Reserve Bank of Philadelphia",
        "https://www.philadelphiafed.org/surveys-and-data/real-time-data-research/changes-to-the-real-time-data-set",
        "2025-03-28",
        "Summary of March 12, 2012 changes",
        (
            "The page identifies PCPI and related price-index series as originating from the "
            "Bureau of Labor Statistics, so third-party content clearance cannot be inferred from "
            "the Philadelphia Fed research-purpose statement alone."
        ),
    ),
)

# code, phase22 requirement hash, projected state, definition, review output produced
PHASE23_REQUIREMENT_ROWS: Final = (
    (
        "INDEPENDENT_CURRENT_USE_RIGHTS_AND_REVOCATION",
        "a323aff4e30a39eec5f4bb64a039413472abfb2e9e84392b74cbbecffbb97b1e",
        "OUTPUT_FROZEN_BLOCKED",
        "Freeze the public-terms technical review without treating it as a rights grant.",
        True,
    ),
    (
        "EXACT_SERIES_DELIVERY_SCHEMA_COVERAGE_AND_AVAILABILITY",
        "fafc67982b30b2e2d922a0e8671756b8cdf2fd195cfc4e7fa681eb072e019fd5",
        "NOT_STARTED",
        "Exact bytes, schema, coverage, missingness, and availability remain uninspected.",
        False,
    ),
    (
        "BLS_RELEASE_ARCHIVE_RECONCILIATION",
        "bfe2f2264ed6389f3bbf82d5928ebb23b5edc5c9870427a9fd63ba748c5e489e",
        "NOT_STARTED",
        "No RTDSM vintage label has been reconciled to an exact BLS release timestamp.",
        False,
    ),
    (
        "EXPLICIT_OPERATIONAL_SOURCE_PRODUCT_COMPOSITION",
        "c6bb0e0b86f0dea8d012db35047f3e4df5b646311e5ba489925627584e2a473c",
        "BLOCKED",
        "The complete human operational-composition decision remains absent.",
        False,
    ),
)

PHASE23_FINDING_VALUES: Final = MappingProxyType(
    {
        "research_purpose": "EXPRESSLY_PERMITTED_RESEARCH_PURPOSE_ONLY",
        "persistent_storage": "NOT_EXPRESSLY_ADDRESSED",
        "automated_model_internal_use": "NOT_EXPRESSLY_ADDRESSED",
        "derived_data": "NOT_EXPRESSLY_ADDRESSED",
        "retention_deletion": "NOT_EXPRESSLY_ADDRESSED",
        "redistribution": "NOT_EXPRESSLY_ADDRESSED",
        "attribution": "NOT_EXPRESSLY_ADDRESSED",
        "third_party_content": "OWNER_PERMISSION_REQUIRED_WHEN_COPYRIGHTED",
        "revocation_currentness": "CHANGE_WITHOUT_NOTICE_REVALIDATION_REQUIRED",
        "access_load": "EXCESSIVE_ACCESS_PROHIBITED",
        "conclusion": PHASE23_AGGREGATE_CONCLUSION,
        "conservative_finding": PHASE23_BLOCK_REASON,
        "public_metadata_review_only": True,
        "operational_use_cleared": False,
        "entitlement_verified": False,
        "executed_license_reviewed": False,
        "legal_opinion_obtained": False,
        "revalidation_required": True,
    }
)
PHASE23_SOURCE_INVARIANTS: Final = MappingProxyType(
    {
        "official_source": True,
        "citation_inert": True,
        "terms_body_persisted": False,
        "remote_response_body_persisted": False,
        "source_content_bytes_captured": False,
        "revalidation_required": True,
    }
)
PHASE23_REQUIREMENT_INVARIANTS: Final = MappingProxyType(
    {"external_action_authorized": False, "satisfied": False}
)
PHASE23_BOUNDARY_VALUES: Final = MappingProxyType(
    {
        "metadata_only": True,
        "public_terms_review_only": True,
        "runtime_network_disabled": True,
        "official_public_documentation_review_performed": True,
        "phase22_artifact_unchanged": True,
        "phase22_candidate_unchanged": True,
        "technical_rights_review_performed": True,
        "legal_opinion_obtained": False,
        "rights_granted": False,
        "rights_verified": False,
        "rights_currentness_guaranteed": False,
        "product_selected": False,
        "delivery_selected": False,
        "credentials_loaded": False,
        "account_verified": False,
        "operational_external_request_performed": False,
        "external_data_capture_authorized": False,
        "provider_payload_persisted": False,
        "data_fitness_review_performed": False,
        "bls_reconciliation_performed": False,
        "research_ingestion_authorized": False,
        "research_executed": False,
        "performance_computed": False,
        "strategy_promotion_authorized": False,
        "execution_authorized": False,
        "order_submission_authorized": False,
        "live_path_absent": True,
        "no_personalized_investment_advice": True,
        "no_real_performance_claimed": True,
    }
)
PHASE23_DISCLAIMER: Final = (
    "Public-terms technical review only; not legal advice, a rights grant, currentness guarantee, "
    "data qualification, product selection, research result, execution authority, order, or "
    "investment advice."
)


def _policy_payload() -> dict[str, object]:
    return {
        "policy_id": PHASE23_POLICY_ID,
        "policy_hash_domain": PHASE23_POLICY_HASH_DOMAIN,
        "schema_version": PHASE23_ARTIFACT_SCHEMA_VERSION,
        "artifact_hash_domain": PHASE23_ARTIFACT_HASH_DOMAIN,
        "artifact_uuid_namespace": str(PHASE23_ARTIFACT_NAMESPACE),
        "source_schema_version": PHASE23_SOURCE_SCHEMA_VERSION,
        "finding_schema_version": PHASE23_FINDING_SCHEMA_VERSION,
        "requirement_schema_version": PHASE23_REQUIREMENT_SCHEMA_VERSION,
        "source_hash_domain": PHASE23_SOURCE_HASH_DOMAIN,
        "finding_hash_domain": PHASE23_FINDING_HASH_DOMAIN,
        "requirement_hash_domain": PHASE23_REQUIREMENT_HASH_DOMAIN,
        "sources_manifest_hash_domain": PHASE23_SOURCES_MANIFEST_HASH_DOMAIN,
        "findings_manifest_hash_domain": PHASE23_FINDINGS_MANIFEST_HASH_DOMAIN,
        "requirements_manifest_hash_domain": PHASE23_REQUIREMENTS_MANIFEST_HASH_DOMAIN,
        "accepted_phase22_commit_sha": PHASE23_ACCEPTED_PHASE22_COMMIT_SHA,
        "accepted_phase22_tree_sha": PHASE23_ACCEPTED_PHASE22_TREE_SHA,
        "phase22_merge_commit_sha": PHASE23_PHASE22_MERGE_COMMIT_SHA,
        "phase22_artifact_id": PHASE23_PHASE22_ARTIFACT_ID,
        "phase22_artifact_sha256": PHASE23_PHASE22_ARTIFACT_SHA256,
        "phase22_policy_sha256": PHASE23_PHASE22_POLICY_SHA256,
        "phase22_sources_manifest_sha256": PHASE23_PHASE22_SOURCES_MANIFEST_SHA256,
        "phase22_products_manifest_sha256": PHASE23_PHASE22_PRODUCTS_MANIFEST_SHA256,
        "phase22_requirements_manifest_sha256": PHASE23_PHASE22_REQUIREMENTS_MANIFEST_SHA256,
        "product_code": PHASE23_PRODUCT_CODE,
        "phase22_product_sha256": PHASE23_PHASE22_PRODUCT_SHA256,
        "family": PHASE23_FAMILY,
        "frozen_at_utc": PHASE23_FROZEN_AT_UTC,
        "reviewed_on": PHASE23_REVIEWED_ON,
        "outcome": PHASE23_OUTCOME,
        "review_state": PHASE23_REVIEW_STATE,
        "aggregate_conclusion": PHASE23_AGGREGATE_CONCLUSION,
        "block_reason": PHASE23_BLOCK_REASON,
        "source_rows": PHASE23_SOURCE_ROWS,
        "finding_values": dict(PHASE23_FINDING_VALUES),
        "requirement_rows": PHASE23_REQUIREMENT_ROWS,
        "source_invariants": dict(PHASE23_SOURCE_INVARIANTS),
        "requirement_invariants": dict(PHASE23_REQUIREMENT_INVARIANTS),
        "boundary_values": dict(PHASE23_BOUNDARY_VALUES),
        "disclaimer": PHASE23_DISCLAIMER,
    }


PHASE23_POLICY_SHA256: Final = domain_sha256(PHASE23_POLICY_HASH_DOMAIN, _policy_payload())


def identity(policy_sha256: str = PHASE23_POLICY_SHA256) -> UUID:
    return uuid_from_sha256(PHASE23_ARTIFACT_NAMESPACE, policy_sha256)


__all__ = [name for name in globals() if name.startswith("PHASE23_")] + [
    "canonical_json_bytes",
    "canonicalize",
    "domain_sha256",
    "identity",
]
