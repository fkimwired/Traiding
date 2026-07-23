"""Canonical policy and registries for the Phase 27 evidence-only intake."""

from __future__ import annotations

from typing import Final
from uuid import UUID

from fable5_data.canonical import canonical_json_bytes as canonical_json_bytes
from fable5_data.canonical import canonicalize as canonicalize
from fable5_data.canonical import domain_sha256 as domain_sha256
from fable5_data.canonical import uuid_from_sha256 as uuid_from_sha256

ARTIFACT_SCHEMA: Final = "phase27-family-a-composition-rights-entitlement-evidence-v1"
INTAKE_SCHEMA: Final = "phase27-composition-evidence-intake-v1"
CRSP_INTAKE_SCHEMA: Final = "phase27-crsp-rights-entitlement-intake-v1"
SEC_INTAKE_SCHEMA: Final = "phase27-sec-policy-revalidation-intake-v1"
AUTHORITY_SCHEMA: Final = "phase27-authority-evidence-record-v1"
SEC_DOCUMENT_SCHEMA: Final = "phase27-sec-policy-document-v1"
CONDITION_SCHEMA: Final = "phase27-evidence-condition-v1"
REQUIREMENT_SCHEMA: Final = "phase27-requirement-evaluation-v1"
RTDSM_BINDING_SCHEMA: Final = "phase27-rtdsm-phase25-binding-v1"
PRODUCT_SCHEMA: Final = "phase27-selected-product-evidence-evaluation-v1"

ARTIFACT_DOMAIN: Final = ARTIFACT_SCHEMA
AUTHORITY_DOMAIN: Final = AUTHORITY_SCHEMA
SEC_DOCUMENT_DOMAIN: Final = SEC_DOCUMENT_SCHEMA
CONDITION_DOMAIN: Final = CONDITION_SCHEMA
REQUIREMENT_DOMAIN: Final = REQUIREMENT_SCHEMA
RTDSM_BINDING_DOMAIN: Final = RTDSM_BINDING_SCHEMA
PRODUCT_DOMAIN: Final = PRODUCT_SCHEMA
AUTHORITY_MANIFEST_DOMAIN: Final = "phase27-authority-evidence-manifest-v1"
SEC_DOCUMENTS_MANIFEST_DOMAIN: Final = "phase27-sec-policy-documents-manifest-v1"
CRSP_REQUIREMENTS_MANIFEST_DOMAIN: Final = "phase27-crsp-requirements-manifest-v1"
RTDSM_REQUIREMENTS_MANIFEST_DOMAIN: Final = "phase27-rtdsm-requirements-manifest-v1"
SEC_REQUIREMENTS_MANIFEST_DOMAIN: Final = "phase27-sec-requirements-manifest-v1"
PRODUCTS_MANIFEST_DOMAIN: Final = "phase27-product-evaluations-manifest-v1"
EVIDENCE_BUNDLE_DOMAIN: Final = "phase27-evidence-bundle-v1"
NORMALIZED_VALUE_DOMAIN: Final = "phase27-normalized-evidence-value-v1"
PRIVATE_AUTHORITY_BASIS_SUFFIX: Final = "_AUTHORITY_BASIS"
NORMALIZED_SUMMARY_MAX_LENGTH: Final = 128
POLICY_ID: Final = "phase27-family-a-composition-rights-entitlement-policy-v1"
POLICY_DOMAIN: Final = POLICY_ID

ARTIFACT_NAMESPACE: Final = UUID("dc04200f-2487-532c-9279-fe47fbc0eb91")
EVIDENCE_BUNDLE_NAMESPACE: Final = UUID("e54c6a89-bcba-544c-9a33-095ab0de1974")

BASELINE_COMMIT_SHA: Final = "b1ad522c666f472f02ad5995d8fa52e3413c2cac"
BASELINE_TREE_SHA: Final = "d1b74532704708e97047e4abf704532102ba510a"
PHASE26_ARTIFACT_ID: Final = "3697996f-5ff7-5c14-b0af-db105b83ec30"
PHASE26_ARTIFACT_SHA256: Final = "ffa06ce79fa249c8d6e46f730c737160d052ee2a02a74465ba34a9b4aa8775a9"
PHASE26_ARTIFACT_FILE_SHA256: Final = (
    "366206d2d0122e28ad95056765f840e3e12087ab1b29f17956f206ba27840175"
)
PHASE26_POLICY_SHA256: Final = "ead7fce5ee1a261277d49803f40e2a84983da8da7e83992441780817f83c4613"
PHASE26_SELECTION_EVIDENCE_SHA256: Final = (
    "6930d8525abafc66b68394de6b6b8ba3d79209916b3e4dee10d3e8a64beee98e"
)
PHASE26_SOURCE_SNAPSHOT_ID: Final = "e81356c5-4833-57a8-9051-cfcfbb181a6d"
PHASE26_SOURCE_SNAPSHOT_SHA256: Final = (
    "c8f7d475deb8be880e61524c1ed1de24b2b0083dedf3d981e550b13eca0a101a"
)
FAMILY: Final = "A_CROSS_SECTIONAL_EQUITY_RANKING"
COMPOSITION_ID: Final = "FAMILY_A_CRSP_SEC_RTDSM_V1"
FIXED_AT_UTC: Final = "2026-07-22T19:35:00.000000Z"
GENERATION_GIT_SHA: Final = BASELINE_COMMIT_SHA
RANDOM_SEED: Final = 0
TRIAL_COUNT: Final = 0

CRSP_PRODUCT: Final = "MORNINGSTAR_CRSP_US_STOCK_DATABASES"
SEC_PRODUCT: Final = "SEC_EDGAR_SUBMISSIONS_AND_XBRL_DATA_APIS"
RTDSM_PRODUCT: Final = "PHILADELPHIA_FED_REAL_TIME_DATA_SET_FOR_MACROECONOMISTS"
PRODUCT_IDS: Final = (CRSP_PRODUCT, SEC_PRODUCT, RTDSM_PRODUCT)
DELIVERY_IDS: Final = (
    "MORNINGSTAR_CRSP_US_STOCK_DATABASES_LINUX_FLAT_FILE",
    "SEC_EDGAR_NIGHTLY_SUBMISSIONS_BULK_ARCHIVE",
    "SEC_EDGAR_NIGHTLY_COMPANYFACTS_BULK_ARCHIVE",
    "PHILADELPHIA_FED_RTDSM_PCPI_MONTHLY_VINTAGE_WORKBOOK",
)

# product, exact deliveries, Phase 26 selected-product hash
PRODUCT_ROWS: Final = (
    (
        CRSP_PRODUCT,
        (DELIVERY_IDS[0],),
        "95e86bae994c7940f71a16178971d920c9e3bfc6db25cdeafbd5777206f992e1",
    ),
    (
        SEC_PRODUCT,
        (DELIVERY_IDS[1], DELIVERY_IDS[2]),
        "5e41c32563d27f090a61bb407b41dcba462056699b37c51b20e1e6f29dd7ce13",
    ),
    (
        RTDSM_PRODUCT,
        (DELIVERY_IDS[3],),
        "bf5fce524dd86ef7c467300d6085a288f4eb7e5753a8b7186504370b5fbe2924",
    ),
)

# code, requirement
CRSP_REQUIREMENT_ROWS: Final = (
    (
        "CRSP_RIGHTS_HOLDER_AND_LICENSEE",
        "Identify the exact rights-holding and licensed legal entities and authorized signers.",
    ),
    (
        "CRSP_EXECUTED_AGREEMENT",
        "Bind an executed agreement, order form, product schedule, and governing terms version.",
    ),
    (
        "CRSP_PRODUCT_AND_SKU",
        "Bind the entitlement to the exact selected CRSP U.S. Stock Databases product and SKU.",
    ),
    (
        "CRSP_LINUX_FLAT_FILE_ENTITLEMENT",
        "Prove the exact selected CRSP Linux flat-file delivery entitlement.",
    ),
    (
        "CRSP_CAPABILITY_SCOPE",
        "Cover security master, historical universe, OHLCV, corporate actions, and delistings.",
    ),
    (
        "CRSP_TERRITORY_USERS_DEVICES",
        "Specify territory, every permitted user, and device or installation limits.",
    ),
    (
        "CRSP_ENVIRONMENTS",
        "Cover local development, test, research, backtest, and simulated paper environments.",
    ),
    (
        "CRSP_AUTOMATED_ACCESS_AND_LOAD",
        "Specify delivery, update, frequency, concurrency, rate, and bulk-access constraints.",
    ),
    (
        "CRSP_EXACT_BYTES_AND_SNAPSHOT_STORAGE",
        "Resolve exact delivery-byte storage, immutable snapshots, and reproducibility copies.",
    ),
    (
        "CRSP_BACKUPS_RETENTION_DELETION",
        "Specify backup handling, retention, deletion, and post-termination obligations.",
    ),
    (
        "CRSP_NORMALIZATION_AND_POINT_IN_TIME",
        "Resolve normalization, identifier history, adjustments, revisions, and PIT transforms.",
    ),
    (
        "CRSP_NONDISPLAY_INTERNAL_RESEARCH",
        "Resolve feature generation, modeling, backtesting, and simulated paper research.",
    ),
    (
        "CRSP_DERIVED_ARTIFACTS",
        "Resolve derived features, aggregates, diagnostics, model parameters, and audit hashes.",
    ),
    (
        "CRSP_DISPLAY_EXPORT_SHARING_REDISTRIBUTION",
        "Resolve display, export, sharing, publication, and redistribution separately for raw "
        "and derived data.",
    ),
    (
        "CRSP_ATTRIBUTION_AND_NOTICES",
        "Record source labels, notices, citations, and permitted use of names or marks.",
    ),
    (
        "CRSP_THIRD_PARTY_RIGHTS",
        "Establish exchange, contributor, and other upstream rights for exact fields and uses.",
    ),
    (
        "CRSP_AUDIT_AND_COMPLIANCE",
        "Specify audit, reporting, usage-measurement, and compliance-control obligations.",
    ),
    (
        "CRSP_TERMINATION_REVOCATION_CURRENTNESS",
        "Specify term, renewal, suspension, revocation, cure, cessation, and revalidation.",
    ),
)

SEC_REQUIREMENT_ROWS: Final = (
    (
        "OFFICIAL_FIRST_PARTY_POLICY_PROVENANCE",
        "Policy evidence is from an exact official first-party SEC HTTPS source.",
    ),
    (
        "EXACT_SELECTED_BULK_PRODUCTS_AND_SURFACES",
        "The review covers nightly submissions and companyfacts bulk archives.",
    ),
    (
        "POLICY_VERSION_EFFECTIVE_DATE_AND_CURRENTNESS",
        "Policy version, effective date, retrieval time, and revalidation horizon are explicit.",
    ),
    ("FAIR_ACCESS_AGGREGATE_RATE", "The current aggregate fair-access rate is recorded."),
    (
        "DECLARED_USER_AGENT_AND_ADMIN_CONTACT",
        "The declared User-Agent and administrative-contact requirement is recorded.",
    ),
    ("AUTOMATED_BULK_RETRIEVAL", "Automated bulk retrieval constraints are recorded."),
    (
        "PERSISTENT_STORAGE_BACKUPS_AND_INTERNAL_USE",
        "Storage, backups, and internal-use treatment are recorded.",
    ),
    (
        "NORMALIZATION_DERIVED_OUTPUTS_AND_NON_DISPLAY_USE",
        "Normalization, derived outputs, and non-display treatment are recorded.",
    ),
    (
        "ATTRIBUTION_DISPLAY_AND_REDISTRIBUTION",
        "Attribution, display, and redistribution treatment are recorded.",
    ),
    (
        "RETENTION_REVOCATION_AND_CHANGE_MONITORING",
        "Retention, revocation, currentness, and policy-change monitoring are recorded.",
    ),
    (
        "CITATION_SEAL_LOGO_AND_NONAFFILIATION",
        "SEC citation, seal and logo restrictions, and non-affiliation language are recorded.",
    ),
    (
        "THIRD_PARTY_AND_CONTENT_SPECIFIC_EXCEPTIONS",
        "Third-party and content-specific exceptions for the selected archives are resolved.",
    ),
)

# source code, exact official title, publisher, URL, accepted Phase 18 source hash
SEC_ACCEPTED_SOURCE_ROWS: Final = (
    (
        "SEC_PRIVACY_AND_DISSEMINATION",
        "SEC.gov | Privacy Information",
        "U.S. Securities and Exchange Commission",
        "https://www.sec.gov/about/privacy-information",
        "0984a4c7658634d6403eb1ec4f36b8626977732bda583349d3021fb9335a9c0c",
    ),
    (
        "SEC_WEBMASTER_REUSE_FAQ",
        "SEC.gov | Webmaster Frequently Asked Questions",
        "U.S. Securities and Exchange Commission",
        "https://www.sec.gov/about/webmaster-frequently-asked-questions",
        "71960ed3481d9dfdb5bf05bb01f1c99d9a33eb1fd210c1d4f78e66c4da72a425",
    ),
    (
        "SEC_EDGAR_APIS",
        "SEC.gov | EDGAR Application Programming Interfaces (APIs)",
        "U.S. Securities and Exchange Commission",
        "https://www.sec.gov/search-filings/edgar-application-programming-interfaces",
        "dbf6644b4a354746fae64019244f8290e3e2d93f20ade509b5b09612bb84f098",
    ),
    (
        "SEC_DEVELOPER_RESOURCES",
        "SEC.gov | Developer Resources",
        "U.S. Securities and Exchange Commission",
        "https://www.sec.gov/about/developer-resources",
        "83513446683733fc70b93accbcdd9edac2be72f55ae5a01ba3d0688e6cd8b684",
    ),
    (
        "SEC_ACCESSING_EDGAR",
        "SEC.gov | Accessing EDGAR Data",
        "U.S. Securities and Exchange Commission",
        "https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data",
        "b4826d9200b61932d49804a10c5252bcc066675385db3069a5b3401378fb4442",
    ),
)

CRSP_CAPABILITY_CODES: Final = (
    "security_master",
    "universe_membership",
    "ohlcv",
    "corporate_actions",
    "delistings",
)
RTDSM_REQUESTED_SERIES: Final = "PCPI"
RTDSM_PCPI_BLS_ORIGIN: Final = "PCPI_BLS_ORIGIN_EXPLICITLY_COVERED"

MISSING_FINDING: Final = "NO_INDEPENDENTLY_VERIFIED_EXACT_SCOPE_EVIDENCE_SUPPLIED"
VERIFIED_BLOCK_REASON: Final = (
    "Verified metadata evidence was recorded, but acquisition, schema, point-in-time, "
    "research, and execution authority remain separate and blocked."
)
INCOMPLETE_BLOCK_REASON: Final = (
    "The exact selected composition lacks complete, current, independently verified rights and "
    "entitlement evidence."
)
DISCLAIMER: Final = (
    "Metadata-only evidence intake; not legal advice, a rights grant, acquisition authority, "
    "provider access, a data snapshot, schema or point-in-time qualification, research, "
    "performance, strategy, risk approval, execution, an order, or investment advice."
)

BOUNDARY_VALUES: Final = {
    "metadata_only": True,
    "runtime_network_disabled": True,
    "generation_network_disabled": True,
    "verification_network_disabled": True,
    "paper_only": True,
    "live_path_absent": True,
    "no_personalized_investment_advice": True,
    "no_real_performance_claimed": True,
    "llm_trade_decisions_prohibited": True,
    "provider_contact_performed": False,
    "credentials_loaded": False,
    "acquisition_authorized": False,
    "external_data_capture_authorized": False,
    "provider_observations_downloaded": False,
    "provider_observations_persisted": False,
    "production_adapter_activated": False,
    "data_snapshot_created": False,
    "exact_schema_qualified": False,
    "point_in_time_qualified": False,
    "research_ingestion_authorized": False,
    "research_executed": False,
    "performance_computed": False,
    "strategy_promotion_authorized": False,
    "risk_limits_changed": False,
    "execution_authorized": False,
    "paper_order_submitted": False,
    "order_submission_authorized": False,
    "database_changed": False,
    "api_changed": False,
}

POLICY_PAYLOAD: Final = {
    "accepted_phase26_artifact_sha256": PHASE26_ARTIFACT_SHA256,
    "accepted_phase26_policy_sha256": PHASE26_POLICY_SHA256,
    "all_operator_descriptive_fields_sanitized": True,
    "block_reason_closed": True,
    "composition_id": COMPOSITION_ID,
    "crsp_requirement_codes": tuple(row[0] for row in CRSP_REQUIREMENT_ROWS),
    "evidence_only": True,
    "normalized_requirement_hash_bound": True,
    "operational_authority": False,
    "operator_descriptive_value_contract": "UPPERCASE_LETTER_LED_CODE_V1",
    "phase25_product_display_translation_in_memory": True,
    "private_authority_basis_suffix": PRIVATE_AUTHORITY_BASIS_SUFFIX,
    "private_authority_metadata_sanitized": True,
    "product_ids": PRODUCT_IDS,
    "sec_accepted_source_codes": tuple(row[0] for row in SEC_ACCEPTED_SOURCE_ROWS),
    "sec_policy_version_contract": "UPPERCASE_CODE_OR_SHA256_V1",
    "sec_publisher_date_contract": "STRICT_ISO_CALENDAR_DATE_V1",
    "missing_finding_code": MISSING_FINDING,
    "normalized_summary_max_length": NORMALIZED_SUMMARY_MAX_LENGTH,
    "rtdsm_product_scope_code": RTDSM_PRODUCT,
    "sec_requirement_codes": tuple(row[0] for row in SEC_REQUIREMENT_ROWS),
}
POLICY_SHA256: Final = domain_sha256(POLICY_DOMAIN, POLICY_PAYLOAD)


def requirement_rows(product_code: str) -> tuple[tuple[str, str], ...]:
    if product_code == CRSP_PRODUCT:
        return CRSP_REQUIREMENT_ROWS
    if product_code == SEC_PRODUCT:
        return SEC_REQUIREMENT_ROWS
    raise ValueError("product does not have a Phase 27 requirement registry")


def sec_source_row(source_code: str) -> tuple[str, str, str, str, str]:
    for row in SEC_ACCEPTED_SOURCE_ROWS:
        if row[0] == source_code:
            return row
    raise ValueError("SEC source code is outside the accepted Phase 18 source set")
