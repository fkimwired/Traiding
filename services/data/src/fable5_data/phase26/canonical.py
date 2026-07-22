"""Canonical constants for the Phase 26 operational data-composition decision."""

from __future__ import annotations

from typing import Final
from uuid import UUID

from fable5_data.canonical import canonical_json_bytes as canonical_json_bytes
from fable5_data.canonical import domain_sha256 as domain_sha256
from fable5_data.canonical import uuid_from_sha256 as uuid_from_sha256

ARTIFACT_SCHEMA: Final = "phase26-family-a-operational-data-composition-decision-v1"
PRODUCT_SCHEMA: Final = "phase26-selected-product-v1"
ASSIGNMENT_SCHEMA: Final = "phase26-capability-assignment-v1"
DEPENDENCY_SCHEMA: Final = "phase26-post-selection-dependency-v1"
GATE_SCHEMA: Final = "phase26-decision-gate-v1"
ARTIFACT_DOMAIN: Final = ARTIFACT_SCHEMA
PRODUCT_DOMAIN: Final = PRODUCT_SCHEMA
ASSIGNMENT_DOMAIN: Final = ASSIGNMENT_SCHEMA
DEPENDENCY_DOMAIN: Final = DEPENDENCY_SCHEMA
GATE_DOMAIN: Final = GATE_SCHEMA
PRODUCTS_MANIFEST_DOMAIN: Final = "phase26-selected-products-manifest-v1"
ASSIGNMENTS_MANIFEST_DOMAIN: Final = "phase26-capability-assignments-manifest-v1"
DEPENDENCIES_MANIFEST_DOMAIN: Final = "phase26-post-selection-dependencies-manifest-v1"
GATES_MANIFEST_DOMAIN: Final = "phase26-decision-gates-manifest-v1"
POLICY_ID: Final = "phase26-family-a-operational-data-composition-policy-v1"
POLICY_DOMAIN: Final = POLICY_ID
SELECTION_EVIDENCE_DOMAIN: Final = "phase26-explicit-human-composition-evidence-v1"
SOURCE_SNAPSHOT_DOMAIN: Final = "phase26-source-snapshot-v1"
ARTIFACT_NAMESPACE: Final = UUID("aaea66b4-3480-5a41-9746-18c67cb1c09d")
SOURCE_SNAPSHOT_NAMESPACE: Final = UUID("5c463853-88cc-57d8-a57d-fcbd7db2f639")

BASELINE_COMMIT_SHA: Final = "4d70b823947fd61d0ea17df14c9f1ff9f93fd45b"
BASELINE_TREE_SHA: Final = "84426ba04f4dbb686878852357410880327b5713"
PHASE25_ARTIFACT_ID: Final = "6f825560-680f-5d53-ac40-3327121e46e0"
PHASE25_ARTIFACT_SHA256: Final = "5bc60a4067b3b802ea9ab3063c42d71143dabc3d303d0cff40c05d813b698a9c"
PHASE25_ARTIFACT_FILE_SHA256: Final = (
    "56939ffdb1c30453518279d20782de2c8e8625cdd30e04c0de0dce8016aab7ee"
)
PHASE21_ARTIFACT_SHA256: Final = "44b5c4541febe6f6e389480102346b802bb4627b81e8d38cab4110cb2eab6a6e"
PHASE22_PRODUCT_SHA256: Final = "59a206777d9f48737c11c557ffdabd5a80c66159822356a7726ed314436da067"
FAMILY: Final = "A_CROSS_SECTIONAL_EQUITY_RANKING"
COMPOSITION_ID: Final = "FAMILY_A_CRSP_SEC_RTDSM_V1"
SELECTED_AT_UTC: Final = "2026-07-21T20:00:00.000000Z"
SELECTED_BY: Final = "REQUESTING_REPOSITORY_OWNER"
GENERATION_GIT_SHA: Final = BASELINE_COMMIT_SHA
RANDOM_SEED: Final = 0
TRIAL_COUNT: Final = 0

SOURCE_IDS: Final = (
    "MORNINGSTAR_CRSP",
    "US_SEC_EDGAR",
    "FEDERAL_RESERVE_BANK_OF_PHILADELPHIA_RTDSM",
)
PRODUCT_IDS: Final = (
    "MORNINGSTAR_CRSP_US_STOCK_DATABASES",
    "SEC_EDGAR_SUBMISSIONS_AND_XBRL_DATA_APIS",
    "PHILADELPHIA_FED_REAL_TIME_DATA_SET_FOR_MACROECONOMISTS",
)
DELIVERY_IDS: Final = (
    "MORNINGSTAR_CRSP_US_STOCK_DATABASES_LINUX_FLAT_FILE",
    "SEC_EDGAR_NIGHTLY_SUBMISSIONS_BULK_ARCHIVE",
    "SEC_EDGAR_NIGHTLY_COMPANYFACTS_BULK_ARCHIVE",
    "PHILADELPHIA_FED_RTDSM_PCPI_MONTHLY_VINTAGE_WORKBOOK",
)
SELECTION_SCOPE: Final = (
    "U.S.-listed common-equity point-in-time research: CRSP supplies permanent security identity, "
    "historical universe membership, daily OHLCV, corporate actions, and delistings; SEC EDGAR "
    "nightly bulk submissions and companyfacts supply filing-availability-lagged as-filed "
    "fundamentals; Philadelphia Fed RTDSM PCPI monthly vintages supply the macro-regime input "
    "after "
    "BLS release-time reconciliation. Use is internal research and simulated paper trading only."
)

# code, provider, source ids, delivery ids, capabilities, accepted candidate hash, rights state
PRODUCT_ROWS: Final = (
    (
        PRODUCT_IDS[0],
        "Morningstar/CRSP",
        (SOURCE_IDS[0],),
        (DELIVERY_IDS[0],),
        ("security_master", "universe_membership", "ohlcv", "corporate_actions", "delistings"),
        "8105f5bd41edf32701fdaa5c425d067ab0e37ff25d84f2c755971cf21e535fb0",
        "PRIVATE_LICENSE_AND_EXACT_DELIVERY_ENTITLEMENT_REQUIRED",
    ),
    (
        PRODUCT_IDS[1],
        "U.S. Securities and Exchange Commission",
        (SOURCE_IDS[1],),
        (DELIVERY_IDS[1], DELIVERY_IDS[2]),
        ("as_reported_fundamentals",),
        "13fc0294503de17f2f5661d48b9c74d746cdf148ab8b1509d752770f64972459",
        "PUBLIC_REUSE_SUPPORTED_CURRENT_POLICY_AND_FITNESS_REVALIDATION_REQUIRED",
    ),
    (
        PRODUCT_IDS[2],
        "Federal Reserve Bank of Philadelphia",
        (SOURCE_IDS[2],),
        (DELIVERY_IDS[3],),
        ("macro_regime_inputs",),
        PHASE22_PRODUCT_SHA256,
        "BLOCKED_PENDING_AUTHENTICATED_EXACT_SCOPE_RIGHTS_RESPONSE",
    ),
)

CAPABILITY_ROWS: Final = (
    ("security_master", PRODUCT_IDS[0]),
    ("universe_membership", PRODUCT_IDS[0]),
    ("ohlcv", PRODUCT_IDS[0]),
    ("corporate_actions", PRODUCT_IDS[0]),
    ("delistings", PRODUCT_IDS[0]),
    ("as_reported_fundamentals", PRODUCT_IDS[1]),
    ("macro_regime_inputs", PRODUCT_IDS[2]),
)

DEPENDENCY_ROWS: Final = (
    (
        "CURRENT_EXECUTED_USE_RIGHTS_AND_REVOCATION",
        "BLOCKED_PENDING_CURRENT_RIGHTS",
        "Obtain and independently verify exact CRSP delivery entitlement and an authenticated "
        "RTDSM rights response; revalidate SEC fair-access and reuse policy.",
    ),
    (
        "EXACT_DELIVERY_AND_SCHEMA_VERSIONS",
        "BLOCKED_PENDING_SCHEMA_QUALIFICATION",
        "Qualify the selected delivery bytes and freeze exact provider schema versions.",
    ),
    (
        "DECLARED_PIT_COVERAGE_CALENDAR_AVAILABILITY_MISSINGNESS",
        "BLOCKED_PENDING_PIT_QUALIFICATION",
        "Prove coverage, filing and release availability, revisions, calendars, and missingness.",
    ),
)

GATE_ROWS: Final = (
    ("EXPLICIT_HUMAN_COMPOSITION_DECISION", "PASS", True),
    ("SINGLE_CLOSED_COMPOSITION", "PASS", True),
    ("COMPLETE_CAPABILITY_ASSIGNMENT", "PASS", True),
    ("CURRENT_RIGHTS_FOR_EXACT_COMPOSITION", "BLOCKED", False),
    ("INDEPENDENT_DECISION_EVIDENCE", "PASS", True),
    ("POST_SELECTION_REVALIDATION", "BLOCKED", False),
)

SELECTION_EVIDENCE_PAYLOAD: Final = {
    "authorization": (
        "The requesting human authorizes Phase 26 as the exact operational data-composition "
        "decision and as the immediate blocker before later live-data shadow-result phases."
    ),
    "capability_product_composition_id": COMPOSITION_ID,
    "delivery_ids": DELIVERY_IDS,
    "product_ids": PRODUCT_IDS,
    "selected_at_utc": SELECTED_AT_UTC,
    "selected_by": SELECTED_BY,
    "selection_scope": SELECTION_SCOPE,
    "source_ids": SOURCE_IDS,
}
SELECTION_EVIDENCE_SHA256: Final = domain_sha256(
    SELECTION_EVIDENCE_DOMAIN, SELECTION_EVIDENCE_PAYLOAD
)

POLICY_PAYLOAD: Final = {
    "composition_id": COMPOSITION_ID,
    "paper_only": True,
    "rights_gate_required": True,
    "schema_and_pit_qualification_required": True,
    "selected_products": PRODUCT_IDS,
}
POLICY_SHA256: Final = domain_sha256(POLICY_DOMAIN, POLICY_PAYLOAD)
SOURCE_SNAPSHOT_PAYLOAD: Final = {
    "phase21_artifact_sha256": PHASE21_ARTIFACT_SHA256,
    "phase22_product_sha256": PHASE22_PRODUCT_SHA256,
    "phase25_artifact_sha256": PHASE25_ARTIFACT_SHA256,
    "selected_candidate_product_hashes": tuple(row[5] for row in PRODUCT_ROWS),
}
SOURCE_SNAPSHOT_SHA256: Final = domain_sha256(SOURCE_SNAPSHOT_DOMAIN, SOURCE_SNAPSHOT_PAYLOAD)
SOURCE_SNAPSHOT_ID: Final = uuid_from_sha256(SOURCE_SNAPSHOT_NAMESPACE, SOURCE_SNAPSHOT_SHA256)

BOUNDARY_VALUES: Final = {
    "acquisition_authorized": False,
    "credentials_loaded": False,
    "external_data_capture_authorized": False,
    "live_path_absent": True,
    "no_personalized_investment_advice": True,
    "no_real_performance_claimed": True,
    "order_submission_authorized": False,
    "paper_only": True,
    "performance_computed": False,
    "production_adapter_activated": False,
    "provider_observations_downloaded": False,
    "provider_observations_persisted": False,
    "research_executed": False,
    "research_ingestion_authorized": False,
    "runtime_network_disabled": True,
    "strategy_promotion_authorized": False,
}
