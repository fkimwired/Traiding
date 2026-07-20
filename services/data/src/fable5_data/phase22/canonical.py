"""Canonical constants for the Phase 22 macro-vintage inventory amendment."""

from __future__ import annotations

from types import MappingProxyType
from typing import Final
from uuid import UUID

from fable5_data.canonical import canonical_json_bytes as canonical_json_bytes
from fable5_data.canonical import canonicalize as canonicalize
from fable5_data.canonical import domain_sha256 as domain_sha256
from fable5_data.canonical import uuid_from_sha256

PHASE22_ARTIFACT_SCHEMA_VERSION: Final = (
    "phase22-family-a-macro-vintage-candidate-inventory-amendment-v1"
)
PHASE22_SOURCE_SCHEMA_VERSION: Final = "phase22-family-a-official-source-citation-v1"
PHASE22_GROUP_SCHEMA_VERSION: Final = "phase22-family-a-candidate-group-amendment-v1"
PHASE22_PRODUCT_SCHEMA_VERSION: Final = "phase22-family-a-macro-vintage-candidate-product-v1"
PHASE22_REQUIREMENT_SCHEMA_VERSION: Final = "phase22-family-a-future-review-requirement-v1"

PHASE22_ARTIFACT_HASH_DOMAIN: Final = PHASE22_ARTIFACT_SCHEMA_VERSION
PHASE22_SOURCE_HASH_DOMAIN: Final = PHASE22_SOURCE_SCHEMA_VERSION
PHASE22_GROUP_HASH_DOMAIN: Final = PHASE22_GROUP_SCHEMA_VERSION
PHASE22_PRODUCT_HASH_DOMAIN: Final = PHASE22_PRODUCT_SCHEMA_VERSION
PHASE22_REQUIREMENT_HASH_DOMAIN: Final = PHASE22_REQUIREMENT_SCHEMA_VERSION
PHASE22_SOURCES_MANIFEST_HASH_DOMAIN: Final = "phase22-official-sources-manifest-v1"
PHASE22_GROUPS_MANIFEST_HASH_DOMAIN: Final = "phase22-candidate-groups-amendment-manifest-v1"
PHASE22_PRODUCTS_MANIFEST_HASH_DOMAIN: Final = "phase22-candidate-products-amendment-manifest-v1"
PHASE22_REQUIREMENTS_MANIFEST_HASH_DOMAIN: Final = "phase22-future-review-requirements-manifest-v1"

PHASE22_POLICY_ID: Final = "phase22-family-a-macro-vintage-candidate-inventory-amendment-policy-v1"
PHASE22_POLICY_HASH_DOMAIN: Final = PHASE22_POLICY_ID
PHASE22_ARTIFACT_NAMESPACE: Final = UUID("105305b7-a755-57d0-a5e0-9d3594b68db3")

PHASE22_ACCEPTED_PHASE21_COMMIT_SHA: Final = "a25ffb5cb68014c301a588c0e8cf7c7f18914e0a"
PHASE22_ACCEPTED_PHASE21_TREE_SHA: Final = "8744604b486dd7398cd8c5a003fe7c7b083fde86"
PHASE22_PHASE21_ARTIFACT_ID: Final = "50086eea-4598-5e6b-b168-616321c7a068"
PHASE22_PHASE21_ARTIFACT_SHA256: Final = (
    "44b5c4541febe6f6e389480102346b802bb4627b81e8d38cab4110cb2eab6a6e"
)
PHASE22_PHASE21_POLICY_SHA256: Final = (
    "22773ad7e58c4baa2c2f7d84bb68c7992d343676f93dc780374ce8e1125f99cf"
)
PHASE22_PHASE21_CANDIDATE_GROUPS_MANIFEST_SHA256: Final = (
    "cab4f26a8ea1da3442048fac20dc9c9896ca557687d144ebb49414d6a68f854f"
)
PHASE22_PHASE21_PRODUCT_RIGHTS_MANIFEST_SHA256: Final = (
    "c44f58b14c9cd9922dcd87792e5ef4fd4d36e62a85313307884ce7d3b402bf19"
)
PHASE22_PHASE21_CAPABILITIES_MANIFEST_SHA256: Final = (
    "fe06d66e62e0c30368deb1af49c878d3a8a916381a7dd4b07c87474b279a0163"
)
PHASE22_PHASE21_DECISION_FIELDS_MANIFEST_SHA256: Final = (
    "cdfd17ee7b77941e205a9c08fdc4f3ca72f71fa62112c2e4647727b2c5694227"
)
PHASE22_PHASE21_GATES_MANIFEST_SHA256: Final = (
    "cf5a3235fc4f2106114d7b6384dc667b09f58ff09dd78bce212aaf612d28186a"
)
PHASE22_PHASE21_RULES_MANIFEST_SHA256: Final = (
    "0626c8f647c8203beb4ba6fcdde0ac51d9d333b201cfdcccb0ebffac42aec7f5"
)
PHASE22_PHASE21_AGGREGATE_CONCLUSION: Final = (
    "BLOCKED_AWAITING_EXPLICIT_OPERATIONAL_SOURCE_PRODUCT_COMPOSITION"
)
PHASE22_PHASE21_BASE_CANDIDATE_GROUP_COUNT: Final = 6
PHASE22_PHASE21_BASE_PRODUCT_COUNT: Final = 9
PHASE22_OFFICIAL_SOURCE_COUNT: Final = 3
PHASE22_CANDIDATE_GROUP_AMENDMENT_COUNT: Final = 1
PHASE22_CANDIDATE_PRODUCT_COUNT: Final = 1
PHASE22_FUTURE_REVIEW_REQUIREMENT_COUNT: Final = 4

PHASE22_INHERITED_FRED_PRODUCT_CODE: Final = "FRED_REALTIME_AND_VINTAGE_WEB_SERVICE"
PHASE22_INHERITED_FRED_PRODUCT_SHA256: Final = (
    "dce1fbcdf188230ce03862a61b723d7ed63ffab76dc851294c027902de50ffcc"
)
PHASE22_INHERITED_FRED_RIGHTS_FINDING_SHA256: Final = (
    "7e286484a11ea083479e3a032d0b74ebbaf76bc0c4061298e746b73a09e2828d"
)
PHASE22_INHERITED_FRED_RIGHTS_CONCLUSION: Final = (
    "INELIGIBLE_CURRENT_TERMS_PROHIBIT_PERSISTENCE_AND_SOFTWARE_MODEL_USE"
)

PHASE22_FAMILY: Final = "A_CROSS_SECTIONAL_EQUITY_RANKING"
PHASE22_FROZEN_AT_UTC: Final = "2026-07-20T18:00:00.000000Z"
PHASE22_REVIEWED_ON: Final = "2026-07-20"
PHASE22_OUTCOME: Final = "BLOCKED"
PHASE22_AMENDMENT_STATE: Final = "CANDIDATE_INVENTORY_AMENDMENT_FROZEN"
PHASE22_AGGREGATE_CONCLUSION: Final = (
    "BLOCKED_AWAITING_CURRENT_RIGHTS_FITNESS_REVIEW_AND_EXPLICIT_OPERATIONAL_COMPOSITION"
)
PHASE22_BLOCK_REASON: Final = (
    "The amendment adds one metadata-only Philadelphia Fed RTDSM candidate for later review; "
    "storage, model, derived-data, retention, exact release-time, schema, coverage, fitness, "
    "current-rights, and operational-composition evidence remain absent."
)

# source code, title, publisher, URL, narrow fact scope
PHASE22_SOURCE_ROWS: Final = (
    (
        "PHILADELPHIA_FED_RTDSM_OVERVIEW",
        "Real-Time Data Set for Macroeconomists",
        "Federal Reserve Bank of Philadelphia",
        "https://www.philadelphiafed.org/surveys-and-data/real-time-data-research/real-time-data-set-for-macroeconomists",
        (
            "The official page describes vintages or snapshots of major macroeconomic time "
            "series, complete per-vintage history downloads, research and forecasting uses, "
            "and month-end updates."
        ),
    ),
    (
        "PHILADELPHIA_FED_RTDSM_PCPI",
        "Data Files - Real-Time Data Set (PCPI)",
        "Federal Reserve Bank of Philadelphia",
        "https://www.philadelphiafed.org/surveys-and-data/real-time-data-research/pcpi",
        (
            "The official PCPI page documents Consumer Price Index monthly vintages from "
            "1998:M11 to present and states that each vintage column contains its complete "
            "time-series history."
        ),
    ),
    (
        "PHILADELPHIA_FED_ONLINE_TERMS",
        "Online Terms of Use and Privacy Notice",
        "Federal Reserve Bank of Philadelphia",
        "https://www.philadelphiafed.org/about-us/privacy-notice",
        (
            "The official terms allow website content for informational, educational, and "
            "research purposes while warning that some content may be copyrighted and use "
            "permission may be required."
        ),
    ),
)

# candidate group code, ordered product codes
PHASE22_CANDIDATE_GROUP_ROWS: Final = (
    (
        "PHILADELPHIA_FED_RTDSM_MACRO_VINTAGES_CANDIDATE",
        ("PHILADELPHIA_FED_REAL_TIME_DATA_SET_FOR_MACROECONOMISTS",),
    ),
)

# product code, group code, official name, URL, fact, capabilities, delivery state, source codes
PHASE22_PRODUCT_ROWS: Final = (
    (
        "PHILADELPHIA_FED_REAL_TIME_DATA_SET_FOR_MACROECONOMISTS",
        "PHILADELPHIA_FED_RTDSM_MACRO_VINTAGES_CANDIDATE",
        "Federal Reserve Bank of Philadelphia Real-Time Data Set for Macroeconomists (RTDSM)",
        "https://www.philadelphiafed.org/surveys-and-data/real-time-data-research/real-time-data-set-for-macroeconomists",
        (
            "The official RTDSM surface documents downloadable macroeconomic vintages; its PCPI "
            "component documents monthly vintage labels from 1998:M11, but those labels are not "
            "treated as exact statistical release timestamps and require later BLS "
            "release-archive reconciliation."
        ),
        ("macro_regime_inputs",),
        "DOCUMENTED_DOWNLOAD_SURFACE",
        (
            "PHILADELPHIA_FED_RTDSM_OVERVIEW",
            "PHILADELPHIA_FED_RTDSM_PCPI",
            "PHILADELPHIA_FED_ONLINE_TERMS",
        ),
    ),
)

# requirement code, state, definition
PHASE22_REQUIREMENT_ROWS: Final = (
    (
        "INDEPENDENT_CURRENT_USE_RIGHTS_AND_REVOCATION",
        "NOT_STARTED",
        (
            "Review current storage, model, derived-data, retention, attribution, third-party, "
            "revocation, and deletion terms for the exact intended use."
        ),
    ),
    (
        "EXACT_SERIES_DELIVERY_SCHEMA_COVERAGE_AND_AVAILABILITY",
        "NOT_STARTED",
        (
            "Verify the exact selected series, delivery bytes, schema, historical boundaries, "
            "missingness, revision behavior, and current availability."
        ),
    ),
    (
        "BLS_RELEASE_ARCHIVE_RECONCILIATION",
        "NOT_STARTED",
        (
            "Reconcile RTDSM month-vintage labels to exact BLS CPI release timestamps before any "
            "point-in-time research use."
        ),
    ),
    (
        "EXPLICIT_OPERATIONAL_SOURCE_PRODUCT_COMPOSITION",
        "BLOCKED",
        (
            "Require the separate complete human composition decision and evidence defined "
            "by Phase 21."
        ),
    ),
)

PHASE22_SOURCE_INVARIANTS: Final = MappingProxyType(
    {
        "official_source": True,
        "citation_inert": True,
        "remote_body_included": False,
    }
)
PHASE22_GROUP_INVARIANTS: Final = MappingProxyType(
    {
        "candidate_only": True,
        "operationally_selected": False,
        "ranked": False,
    }
)
PHASE22_PRODUCT_INVARIANTS: Final = MappingProxyType(
    {
        "candidate_only": True,
        "review_routing_state": ("NAMED_FOR_INDEPENDENT_CURRENT_RIGHTS_AND_FITNESS_REVIEW"),
        "operationally_selected": False,
        "ranked": False,
        "public_research_use_stated": True,
        "entitlement_state": "UNPROVEN",
        "rights_state": "NOT_REVIEWED",
        "fitness_state": "UNPROVEN",
        "persistent_storage_model_derived_retention_rights_reviewed": False,
        "month_vintage_labels_are_exact_release_timestamps": False,
        "bls_release_archive_reconciliation_required": True,
        "coverage_proven": False,
        "schema_proven": False,
        "current_availability_proven": False,
        "external_sample_qualified": False,
    }
)
PHASE22_REQUIREMENT_INVARIANTS: Final = MappingProxyType(
    {
        "external_action_authorized": False,
        "satisfied": False,
    }
)

PHASE22_BOUNDARY_VALUES: Final = MappingProxyType(
    {
        "metadata_only": True,
        "candidate_inventory_amendment_only": True,
        "runtime_network_disabled": True,
        "official_public_documentation_review_performed": True,
        "prior_candidate_inventory_unchanged": True,
        "prior_rights_findings_unchanged": True,
        "phase21_decision_requirements_unchanged": True,
        "inherited_fred_finding_unchanged": True,
        "composition_ranked": False,
        "operational_source_product_composition_selected": False,
        "selection_evidence_produced": False,
        "source_selected": False,
        "provider_selected": False,
        "product_selected": False,
        "delivery_selected": False,
        "rights_review_performed": False,
        "rights_granted": False,
        "rights_verified": False,
        "rights_currentness_guaranteed": False,
        "credentials_loaded": False,
        "account_verified": False,
        "operational_external_request_performed": False,
        "external_data_capture_authorized": False,
        "provider_payload_persisted": False,
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

PHASE22_DISCLAIMER: Final = (
    "Metadata-only candidate-inventory amendment. It is not a product recommendation, rank, "
    "operational selection, right, entitlement, data qualification, research result, execution "
    "authority, order, or investment advice."
)


def _policy_payload() -> dict[str, object]:
    return {
        "policy_id": PHASE22_POLICY_ID,
        "policy_hash_domain": PHASE22_POLICY_HASH_DOMAIN,
        "schema_version": PHASE22_ARTIFACT_SCHEMA_VERSION,
        "artifact_hash_domain": PHASE22_ARTIFACT_HASH_DOMAIN,
        "artifact_uuid_namespace": str(PHASE22_ARTIFACT_NAMESPACE),
        "source_schema_version": PHASE22_SOURCE_SCHEMA_VERSION,
        "group_schema_version": PHASE22_GROUP_SCHEMA_VERSION,
        "product_schema_version": PHASE22_PRODUCT_SCHEMA_VERSION,
        "requirement_schema_version": PHASE22_REQUIREMENT_SCHEMA_VERSION,
        "source_hash_domain": PHASE22_SOURCE_HASH_DOMAIN,
        "group_hash_domain": PHASE22_GROUP_HASH_DOMAIN,
        "product_hash_domain": PHASE22_PRODUCT_HASH_DOMAIN,
        "requirement_hash_domain": PHASE22_REQUIREMENT_HASH_DOMAIN,
        "sources_manifest_hash_domain": PHASE22_SOURCES_MANIFEST_HASH_DOMAIN,
        "groups_manifest_hash_domain": PHASE22_GROUPS_MANIFEST_HASH_DOMAIN,
        "products_manifest_hash_domain": PHASE22_PRODUCTS_MANIFEST_HASH_DOMAIN,
        "requirements_manifest_hash_domain": PHASE22_REQUIREMENTS_MANIFEST_HASH_DOMAIN,
        "accepted_phase21_commit_sha": PHASE22_ACCEPTED_PHASE21_COMMIT_SHA,
        "accepted_phase21_tree_sha": PHASE22_ACCEPTED_PHASE21_TREE_SHA,
        "phase21_artifact_id": PHASE22_PHASE21_ARTIFACT_ID,
        "phase21_artifact_sha256": PHASE22_PHASE21_ARTIFACT_SHA256,
        "phase21_policy_sha256": PHASE22_PHASE21_POLICY_SHA256,
        "phase21_candidate_groups_manifest_sha256": (
            PHASE22_PHASE21_CANDIDATE_GROUPS_MANIFEST_SHA256
        ),
        "phase21_product_rights_manifest_sha256": PHASE22_PHASE21_PRODUCT_RIGHTS_MANIFEST_SHA256,
        "phase21_capabilities_manifest_sha256": PHASE22_PHASE21_CAPABILITIES_MANIFEST_SHA256,
        "phase21_decision_fields_manifest_sha256": PHASE22_PHASE21_DECISION_FIELDS_MANIFEST_SHA256,
        "phase21_gates_manifest_sha256": PHASE22_PHASE21_GATES_MANIFEST_SHA256,
        "phase21_rules_manifest_sha256": PHASE22_PHASE21_RULES_MANIFEST_SHA256,
        "phase21_aggregate_conclusion": PHASE22_PHASE21_AGGREGATE_CONCLUSION,
        "phase21_base_candidate_group_count": PHASE22_PHASE21_BASE_CANDIDATE_GROUP_COUNT,
        "phase21_base_product_count": PHASE22_PHASE21_BASE_PRODUCT_COUNT,
        "inherited_fred_product_code": PHASE22_INHERITED_FRED_PRODUCT_CODE,
        "inherited_fred_product_sha256": PHASE22_INHERITED_FRED_PRODUCT_SHA256,
        "inherited_fred_rights_finding_sha256": PHASE22_INHERITED_FRED_RIGHTS_FINDING_SHA256,
        "inherited_fred_rights_conclusion": PHASE22_INHERITED_FRED_RIGHTS_CONCLUSION,
        "family": PHASE22_FAMILY,
        "frozen_at_utc": PHASE22_FROZEN_AT_UTC,
        "reviewed_on": PHASE22_REVIEWED_ON,
        "outcome": PHASE22_OUTCOME,
        "amendment_state": PHASE22_AMENDMENT_STATE,
        "aggregate_conclusion": PHASE22_AGGREGATE_CONCLUSION,
        "block_reason": PHASE22_BLOCK_REASON,
        "source_rows": PHASE22_SOURCE_ROWS,
        "group_rows": PHASE22_CANDIDATE_GROUP_ROWS,
        "product_rows": PHASE22_PRODUCT_ROWS,
        "requirement_rows": PHASE22_REQUIREMENT_ROWS,
        "official_source_count": PHASE22_OFFICIAL_SOURCE_COUNT,
        "candidate_group_amendment_count": PHASE22_CANDIDATE_GROUP_AMENDMENT_COUNT,
        "candidate_product_count": PHASE22_CANDIDATE_PRODUCT_COUNT,
        "future_review_requirement_count": PHASE22_FUTURE_REVIEW_REQUIREMENT_COUNT,
        "source_invariants": dict(PHASE22_SOURCE_INVARIANTS),
        "group_invariants": dict(PHASE22_GROUP_INVARIANTS),
        "product_invariants": dict(PHASE22_PRODUCT_INVARIANTS),
        "requirement_invariants": dict(PHASE22_REQUIREMENT_INVARIANTS),
        "boundary_values": dict(PHASE22_BOUNDARY_VALUES),
        "disclaimer": PHASE22_DISCLAIMER,
    }


PHASE22_POLICY_SHA256: Final = domain_sha256(PHASE22_POLICY_HASH_DOMAIN, _policy_payload())


def identity(policy_sha256: str = PHASE22_POLICY_SHA256) -> UUID:
    return uuid_from_sha256(PHASE22_ARTIFACT_NAMESPACE, policy_sha256)


__all__ = [name for name in globals() if name.startswith("PHASE22_")] + [
    "canonical_json_bytes",
    "canonicalize",
    "domain_sha256",
    "identity",
]
