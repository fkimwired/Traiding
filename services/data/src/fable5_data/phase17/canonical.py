"""Canonical constants and hash domains for the Phase 17 candidate-product inventory."""

from __future__ import annotations

from datetime import UTC, datetime
from types import MappingProxyType
from typing import Final
from uuid import UUID

from fable5_data.canonical import canonical_json_bytes as canonical_json_bytes
from fable5_data.canonical import canonicalize as canonicalize
from fable5_data.canonical import domain_sha256 as domain_sha256
from fable5_data.canonical import uuid_from_sha256

PHASE17_ARTIFACT_SCHEMA_VERSION: Final = "phase17-family-a-candidate-product-inventory-v1"
PHASE17_ARTIFACT_HASH_DOMAIN: Final = PHASE17_ARTIFACT_SCHEMA_VERSION
PHASE17_POLICY_ID: Final = "phase17-family-a-candidate-product-inventory-policy-v1"
PHASE17_POLICY_HASH_DOMAIN: Final = PHASE17_POLICY_ID
PHASE17_PRODUCT_SCHEMA_VERSION: Final = "phase17-family-a-candidate-product-v1"
PHASE17_PRODUCT_HASH_DOMAIN: Final = PHASE17_PRODUCT_SCHEMA_VERSION
PHASE17_CANDIDATE_SCHEMA_VERSION: Final = "phase17-family-a-candidate-product-group-v1"
PHASE17_CANDIDATE_HASH_DOMAIN: Final = PHASE17_CANDIDATE_SCHEMA_VERSION
PHASE17_STEP_SCHEMA_VERSION: Final = "phase17-family-a-source-plan-step-evidence-v1"
PHASE17_STEP_HASH_DOMAIN: Final = PHASE17_STEP_SCHEMA_VERSION
PHASE17_OUTPUT_SCHEMA_VERSION: Final = "phase17-family-a-source-plan-output-v1"
PHASE17_OUTPUT_HASH_DOMAIN: Final = PHASE17_OUTPUT_SCHEMA_VERSION
PHASE17_PRODUCTS_MANIFEST_HASH_DOMAIN: Final = "phase17-candidate-products-manifest-v1"
PHASE17_CANDIDATES_MANIFEST_HASH_DOMAIN: Final = "phase17-candidate-groups-manifest-v1"
PHASE17_STEPS_MANIFEST_HASH_DOMAIN: Final = "phase17-source-plan-steps-manifest-v1"
PHASE17_ARTIFACT_NAMESPACE: Final = UUID("d987843d-6474-5e17-a00d-bf1bf73fb7a8")

PHASE17_ACCEPTED_PHASE16_COMMIT_SHA: Final = "7c4df26733b4ad13c49c455ea5f28f627012ee44"
PHASE17_ACCEPTED_PHASE16_TREE_SHA: Final = "c69b4a60237ae3588f8544272b75becbf0a763e8"
PHASE17_PHASE16_ARTIFACT_ID: Final = "e106a766-5cfe-5a1c-94f6-ee1c2ac68652"
PHASE17_PHASE16_ARTIFACT_SHA256: Final = (
    "74ddf4a51d722b494fd494241e2e5927bff6fde034f6932dcfd791bb3a0706bb"
)
PHASE17_PHASE16_POLICY_SHA256: Final = (
    "57cfcfd09f2d4a87d9562fd536228b9f05693bb71b7e9d1867618a35da7d4efd"
)
PHASE17_PHASE16_REQUIREMENTS_MANIFEST_SHA256: Final = (
    "cc48b8c45112665517c2e525267610b34025aa06a3dc490f27409d569fa72089"
)
PHASE17_PHASE16_CAPABILITIES_MANIFEST_SHA256: Final = (
    "469426253bad297c0db73e152305f97dbaf29126b0ea8c4d49bb047ef1eba47f"
)
PHASE17_PHASE16_CANDIDATES_MANIFEST_SHA256: Final = (
    "75f0197965d8b9c75cba3b292aa4b8e9942896039deb295511c44ab88c837ccd"
)
PHASE17_PHASE16_STEPS_MANIFEST_SHA256: Final = (
    "92e65795b453a63cb1c6b44b4522629226580f90d681caf0032dfd787b94725d"
)
PHASE17_PHASE16_STEP1_SHA256: Final = (
    "b91451d90ea1ae672ccab878df742b91b62d1b33902f9be05a0b6e1395502ec1"
)
PHASE17_PHASE16_GAP_BINDINGS_MANIFEST_SHA256: Final = (
    "c6df8bcc7d98b682b880484aef028d411f196aaaf414d01949912c969ac9e26d"
)
PHASE17_FAMILY: Final = "A_CROSS_SECTIONAL_EQUITY_RANKING"
PHASE17_FROZEN_AT_UTC: Final = datetime(2026, 7, 19, tzinfo=UTC)

PHASE17_PRODUCT_ROWS: Final = (
    (
        "TIINGO_END_OF_DAY",
        "TIINGO_PHASE13_BOUNDED_CANDIDATE",
        "Tiingo End-of-Day Stock Price API",
        "https://www.tiingo.com/documentation/end-of-day",
        (
            "The official documentation names end-of-day metadata and historical price surfaces "
            "with raw and adjusted OHLCV plus dividend-cash and split-factor fields."
        ),
        ("security_master", "ohlcv", "corporate_actions"),
        "DOCUMENTED_WEB_API_SURFACE",
    ),
    (
        "TIINGO_US_FUNDAMENTALS",
        "TIINGO_PHASE13_BOUNDED_CANDIDATE",
        "Tiingo U.S. Fundamental Data API",
        "https://www.tiingo.com/documentation/fundamentals",
        (
            "The official documentation names fundamental definitions, statements, daily, and "
            "metadata surfaces and identifies ticker and stable permaTicker request identities."
        ),
        ("as_reported_fundamentals",),
        "DOCUMENTED_WEB_API_SURFACE",
    ),
    (
        "TIINGO_DIVIDEND_CORPORATE_ACTIONS",
        "TIINGO_PHASE13_BOUNDED_CANDIDATE",
        "Tiingo Stock, ETF, and Mutual Fund Dividend API",
        "https://www.tiingo.com/documentation/corporate-actions/dividends",
        (
            "The official documentation names batch and per-ticker distribution surfaces with "
            "ex-date, payment, record, declaration, amount, and frequency metadata."
        ),
        ("corporate_actions",),
        "DOCUMENTED_WEB_API_SURFACE",
    ),
    (
        "TIINGO_SPLIT_CORPORATE_ACTIONS",
        "TIINGO_PHASE13_BOUNDED_CANDIDATE",
        "Tiingo Stock, ETF, and Mutual Fund Split API",
        "https://www.tiingo.com/documentation/corporate-actions/splits",
        (
            "The official documentation names batch and per-ticker split surfaces with ex-date, "
            "split-from, split-to, split-factor, and status metadata."
        ),
        ("corporate_actions",),
        "DOCUMENTED_WEB_API_SURFACE",
    ),
    (
        "MORNINGSTAR_CRSP_US_STOCK_DATABASES",
        "MORNINGSTAR_CRSP_US_STOCK_DATABASES_CANDIDATE",
        "Morningstar CRSP U.S. Stock Databases",
        "https://indexes.morningstar.com/research-data-products/crsp-us-stock-databases",
        (
            "The official Morningstar page names CRSP U.S. Stock Databases, active and inactive "
            "securities, market data, corporate actions, and permanent PERMNO and PERMCO identity."
        ),
        (
            "security_master",
            "universe_membership",
            "ohlcv",
            "corporate_actions",
            "delistings",
            "sector_classification_history",
        ),
        "UNPROVEN",
    ),
    (
        "MORNINGSTAR_CRSP_COMPUSTAT_MERGED",
        "MORNINGSTAR_CRSP_COMPUSTAT_MERGED_DATABASE_CANDIDATE",
        "Morningstar CRSP/Compustat Merged Database",
        "https://indexes.morningstar.com/research-data-products/crsp-compustat-merged-database",
        (
            "The official Morningstar page names the CRSP/Compustat Merged Database and CRSPLink "
            "mapping over time; this inventory does not infer a delivery variant or fitness."
        ),
        ("security_master", "as_reported_fundamentals"),
        "UNPROVEN",
    ),
    (
        "SEC_EDGAR_SUBMISSIONS_AND_XBRL_DATA_APIS",
        "SEC_EDGAR_SUBMISSIONS_XBRL_CANDIDATE",
        "SEC EDGAR Submissions and XBRL Data APIs with nightly bulk archives",
        "https://www.sec.gov/search-filings/edgar-application-programming-interfaces",
        (
            "The official SEC page names the Submissions API, XBRL Companyfacts API, and nightly "
            "recompiled submissions and companyfacts bulk archives."
        ),
        ("security_master", "as_reported_fundamentals"),
        "DOCUMENTED_WEB_API_SURFACE",
    ),
    (
        "FRED_REALTIME_AND_VINTAGE_WEB_SERVICE",
        "FEDERAL_RESERVE_ALFRED_VINTAGES_CANDIDATE",
        "FRED API real-time periods and series vintage dates",
        "https://fred.stlouisfed.org/docs/api/fred/overview.html",
        (
            "The official FRED documentation defines real-time periods for when facts were known "
            "and a series vintagedates surface for revision or release dates."
        ),
        ("macro_regime_inputs",),
        "DOCUMENTED_WEB_API_SURFACE",
    ),
    (
        "LSEG_TICK_HISTORY_INSTRUMENT_AND_VENUE_WEB_API",
        "HISTORICAL_LIQUIDITY_PRODUCT_UNSELECTED",
        "LSEG Tick History Instrument and Venue Access via Web/API",
        "https://www.lseg.com/en/data-analytics/market-data/data-feeds/tick-history",
        (
            "The official LSEG page documents Web/API instrument and venue access, more than 580 "
            "venues, and Level 1 and Level 2 history reaching back as far as January 1996."
        ),
        ("historical_liquidity_depth",),
        "DOCUMENTED_WEB_API_SURFACE",
    ),
)

PHASE17_CANDIDATE_GROUP_ROWS: Final = (
    (
        "TIINGO_PHASE13_BOUNDED_CANDIDATE",
        (
            "TIINGO_END_OF_DAY",
            "TIINGO_US_FUNDAMENTALS",
            "TIINGO_DIVIDEND_CORPORATE_ACTIONS",
            "TIINGO_SPLIT_CORPORATE_ACTIONS",
        ),
    ),
    (
        "MORNINGSTAR_CRSP_US_STOCK_DATABASES_CANDIDATE",
        ("MORNINGSTAR_CRSP_US_STOCK_DATABASES",),
    ),
    (
        "MORNINGSTAR_CRSP_COMPUSTAT_MERGED_DATABASE_CANDIDATE",
        ("MORNINGSTAR_CRSP_COMPUSTAT_MERGED",),
    ),
    (
        "SEC_EDGAR_SUBMISSIONS_XBRL_CANDIDATE",
        ("SEC_EDGAR_SUBMISSIONS_AND_XBRL_DATA_APIS",),
    ),
    (
        "FEDERAL_RESERVE_ALFRED_VINTAGES_CANDIDATE",
        ("FRED_REALTIME_AND_VINTAGE_WEB_SERVICE",),
    ),
    (
        "HISTORICAL_LIQUIDITY_PRODUCT_UNSELECTED",
        ("LSEG_TICK_HISTORY_INSTRUMENT_AND_VENUE_WEB_API",),
    ),
)

PHASE17_STEP_CODES: Final = (
    "SELECT_CANDIDATE_PRODUCTS",
    "REVIEW_CURRENT_USE_RIGHTS",
    "QUALIFY_BOUNDED_READ_ONLY_SAMPLES",
    "PRODUCE_FULL_HISTORY_COVERAGE_MANIFEST",
    "RECONCILE_TEMPORAL_IDENTITY_REVISION_SEMANTICS",
    "DESIGN_LOCAL_QUARANTINE_AND_CANONICAL_SNAPSHOT",
    "REQUEST_SEPARATE_INGESTION_AUTHORITY",
)
PHASE17_STEP_STATES: Final = (
    "OUTPUT_FROZEN",
    "NOT_STARTED",
    "NOT_STARTED",
    "NOT_STARTED",
    "NOT_STARTED",
    "NOT_STARTED",
    "NOT_STARTED",
)
PHASE17_STEP_PREREQUISITES: Final = (
    (),
    ("SELECT_CANDIDATE_PRODUCTS",),
    ("SELECT_CANDIDATE_PRODUCTS", "REVIEW_CURRENT_USE_RIGHTS"),
    ("QUALIFY_BOUNDED_READ_ONLY_SAMPLES",),
    ("PRODUCE_FULL_HISTORY_COVERAGE_MANIFEST",),
    ("REVIEW_CURRENT_USE_RIGHTS", "RECONCILE_TEMPORAL_IDENTITY_REVISION_SEMANTICS"),
    ("DESIGN_LOCAL_QUARANTINE_AND_CANONICAL_SNAPSHOT",),
)
PHASE17_STEP_REQUIRED_PRIOR_EVIDENCE: Final = (
    (),
    (),
    ("non_synthetic_evaluation_policy_sha256", "confirmation_holdout_definition_sha256"),
    (),
    (),
    (),
    (),
)
PHASE17_STEP_REQUIRED_OUTPUTS: Final = (
    ("candidate_product_inventory_sha256",),
    ("independent_rights_review_sha256", "rights_currentness_sha256"),
    ("qualification_artifact_set_sha256",),
    ("full_history_coverage_manifest_sha256",),
    ("temporal_identity_revision_reconciliation_sha256",),
    ("quarantine_canonical_snapshot_design_sha256",),
    ("separate_ingestion_authority_evidence_sha256",),
)

PHASE17_BOUNDARY_VALUES: Final = MappingProxyType(
    {
        "metadata_only": True,
        "official_public_documentation_review_performed": True,
        "official_documentation_citations_inert": True,
        "runtime_network_disabled": True,
        "external_request_performed": False,
        "provider_data_request_performed": False,
        "provider_account_verification_performed": False,
        "entitlement_verification_performed": False,
        "provider_selected": False,
        "product_selected": False,
        "source_selected": False,
        "credentials_loaded": False,
        "entitlement_verified": False,
        "rights_verified": False,
        "rights_granted": False,
        "fitness_verified": False,
        "coverage_proven": False,
        "schema_proven": False,
        "current_availability_proven": False,
        "external_sample_qualified": False,
        "external_data_capture_authorized": False,
        "provider_payload_persisted": False,
        "licensed_data_persisted": False,
        "research_ingestion_authorized": False,
        "research_snapshot_created": False,
        "research_data_eligible": False,
        "evaluation_policy_approved": False,
        "confirmation_holdout_defined": False,
        "confirmation_holdout_opened": False,
        "research_run_created": False,
        "research_run_authorized": False,
        "research_executed": False,
        "performance_computed": False,
        "pass_research_granted": False,
        "strategy_promotion_authorized": False,
        "paper_approval_granted": False,
        "risk_clearance_granted": False,
        "strategy_execution_eligible": False,
        "execution_authorized": False,
        "order_submission_authorized": False,
        "live_path_absent": True,
        "no_personalized_investment_advice": True,
        "no_real_performance_claimed": True,
    }
)
PHASE17_BLOCK_REASON: Final = (
    "Independent current-use rights, entitlement, exact coverage, schema, availability, delivery "
    "variant where applicable, bounded qualification, fitness, and every later prerequisite remain "
    "unproven."
)
PHASE17_DISCLAIMER: Final = (
    "Metadata-only candidate-product inventory; naming a product for independent rights review is "
    "not provider, product, or source selection and grants no entitlement, right, fitness, data, "
    "ingestion, research, promotion, risk, execution, order, or personalized-advice authority."
)

PHASE17_POLICY_SHA256: Final = domain_sha256(
    PHASE17_POLICY_HASH_DOMAIN,
    {
        "policy_id": PHASE17_POLICY_ID,
        "artifact_uuid_namespace": str(PHASE17_ARTIFACT_NAMESPACE),
        "schemas_and_hash_domains": (
            (PHASE17_ARTIFACT_SCHEMA_VERSION, PHASE17_ARTIFACT_HASH_DOMAIN),
            (PHASE17_PRODUCT_SCHEMA_VERSION, PHASE17_PRODUCT_HASH_DOMAIN),
            (PHASE17_CANDIDATE_SCHEMA_VERSION, PHASE17_CANDIDATE_HASH_DOMAIN),
            (PHASE17_STEP_SCHEMA_VERSION, PHASE17_STEP_HASH_DOMAIN),
            (PHASE17_OUTPUT_SCHEMA_VERSION, PHASE17_OUTPUT_HASH_DOMAIN),
            PHASE17_PRODUCTS_MANIFEST_HASH_DOMAIN,
            PHASE17_CANDIDATES_MANIFEST_HASH_DOMAIN,
            PHASE17_STEPS_MANIFEST_HASH_DOMAIN,
        ),
        "accepted_phase16_commit_sha": PHASE17_ACCEPTED_PHASE16_COMMIT_SHA,
        "accepted_phase16_tree_sha": PHASE17_ACCEPTED_PHASE16_TREE_SHA,
        "phase16_identities": (
            PHASE17_PHASE16_ARTIFACT_ID,
            PHASE17_PHASE16_ARTIFACT_SHA256,
            PHASE17_PHASE16_POLICY_SHA256,
            PHASE17_PHASE16_REQUIREMENTS_MANIFEST_SHA256,
            PHASE17_PHASE16_CAPABILITIES_MANIFEST_SHA256,
            PHASE17_PHASE16_CANDIDATES_MANIFEST_SHA256,
            PHASE17_PHASE16_STEPS_MANIFEST_SHA256,
            PHASE17_PHASE16_STEP1_SHA256,
            PHASE17_PHASE16_GAP_BINDINGS_MANIFEST_SHA256,
        ),
        "family": PHASE17_FAMILY,
        "frozen_at_utc": PHASE17_FROZEN_AT_UTC,
        "outcome": "BLOCKED",
        "product_rows": PHASE17_PRODUCT_ROWS,
        "product_invariants": (
            ("selected_for_independent_rights_review", True),
            ("operational_provider_selected", False),
            ("operational_product_selected", False),
            ("operational_source_selected", False),
            ("entitlement_state", "UNPROVEN"),
            ("rights_state", "UNPROVEN"),
            ("fitness_state", "UNPROVEN"),
            ("coverage_proven", False),
            ("schema_proven", False),
            ("current_availability_proven", False),
            ("external_sample_qualified", False),
        ),
        "candidate_groups": PHASE17_CANDIDATE_GROUP_ROWS,
        "candidate_group_invariants": (
            ("selection_state", "NAMED_FOR_INDEPENDENT_RIGHTS_REVIEW"),
            ("single_operational_selection", False),
        ),
        "steps": tuple(
            zip(
                PHASE17_STEP_CODES,
                PHASE17_STEP_STATES,
                PHASE17_STEP_PREREQUISITES,
                PHASE17_STEP_REQUIRED_PRIOR_EVIDENCE,
                PHASE17_STEP_REQUIRED_OUTPUTS,
                strict=True,
            )
        ),
        "boundary_values": PHASE17_BOUNDARY_VALUES,
        "block_reason": PHASE17_BLOCK_REASON,
        "disclaimer": PHASE17_DISCLAIMER,
    },
)


def identity(sha256: str) -> UUID:
    return uuid_from_sha256(PHASE17_ARTIFACT_NAMESPACE, sha256)


__all__ = [name for name in globals() if name.startswith("PHASE17_")] + [
    "canonical_json_bytes",
    "canonicalize",
    "domain_sha256",
    "identity",
]
