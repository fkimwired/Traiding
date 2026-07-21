"""Canonical Phase 25 rights-response and adapter-pattern research policy."""

# ruff: noqa: E501 -- exact source findings and policy text are intentionally immutable.

from __future__ import annotations

from types import MappingProxyType
from typing import Final
from uuid import UUID

from fable5_data.canonical import canonical_json_bytes as canonical_json_bytes
from fable5_data.canonical import canonicalize as canonicalize
from fable5_data.canonical import domain_sha256 as domain_sha256
from fable5_data.canonical import uuid_from_sha256 as uuid_from_sha256

PHASE25_ARTIFACT_SCHEMA_VERSION: Final = (
    "phase25-family-a-rtdsm-rights-response-adapter-patterns-v1"
)
PHASE25_AUTHORITY_SCHEMA_VERSION: Final = "phase25-rtdsm-authority-evidence-v1"
PHASE25_QUESTION_SCHEMA_VERSION: Final = "phase25-rtdsm-question-evaluation-v1"
PHASE25_SCOPE_SCHEMA_VERSION: Final = "phase25-rtdsm-scope-evaluation-v1"
PHASE25_CONDITION_SCHEMA_VERSION: Final = "phase25-rtdsm-enforceable-condition-v1"
PHASE25_SOURCE_SCHEMA_VERSION: Final = "phase25-open-source-evidence-v1"
PHASE25_PATTERN_SCHEMA_VERSION: Final = "phase25-adapter-pattern-v1"
PHASE25_RULE_SCHEMA_VERSION: Final = "phase25-fail-closed-transition-rule-v1"
PHASE25_INTAKE_SCHEMA_VERSION: Final = "phase25-rtdsm-rights-response-intake-v1"

PHASE25_ARTIFACT_HASH_DOMAIN: Final = PHASE25_ARTIFACT_SCHEMA_VERSION
PHASE25_AUTHORITY_HASH_DOMAIN: Final = PHASE25_AUTHORITY_SCHEMA_VERSION
PHASE25_QUESTION_HASH_DOMAIN: Final = PHASE25_QUESTION_SCHEMA_VERSION
PHASE25_SCOPE_HASH_DOMAIN: Final = PHASE25_SCOPE_SCHEMA_VERSION
PHASE25_CONDITION_HASH_DOMAIN: Final = PHASE25_CONDITION_SCHEMA_VERSION
PHASE25_SOURCE_HASH_DOMAIN: Final = PHASE25_SOURCE_SCHEMA_VERSION
PHASE25_PATTERN_HASH_DOMAIN: Final = PHASE25_PATTERN_SCHEMA_VERSION
PHASE25_RULE_HASH_DOMAIN: Final = PHASE25_RULE_SCHEMA_VERSION
PHASE25_QUESTIONS_MANIFEST_HASH_DOMAIN: Final = "phase25-question-evaluations-manifest-v1"
PHASE25_SCOPE_MANIFEST_HASH_DOMAIN: Final = "phase25-exact-scope-manifest-v1"
PHASE25_AUTHORITY_MANIFEST_HASH_DOMAIN: Final = "phase25-authority-evidence-manifest-v1"
PHASE25_SOURCES_MANIFEST_HASH_DOMAIN: Final = "phase25-source-evidence-manifest-v1"
PHASE25_PATTERNS_MANIFEST_HASH_DOMAIN: Final = "phase25-adapter-patterns-manifest-v1"
PHASE25_RULES_MANIFEST_HASH_DOMAIN: Final = "phase25-transition-rules-manifest-v1"
PHASE25_NORMALIZED_VALUE_HASH_DOMAIN: Final = "phase25-normalized-scope-value-v1"
PHASE25_POLICY_ID: Final = "phase25-family-a-rtdsm-rights-response-adapter-pattern-policy-v1"
PHASE25_POLICY_HASH_DOMAIN: Final = PHASE25_POLICY_ID
PHASE25_ARTIFACT_NAMESPACE: Final = UUID("aec9aa4c-8af7-5685-baa7-f19b5f69b777")
PHASE25_SOURCE_SNAPSHOT_NAMESPACE: Final = UUID("81bbf6d1-61a2-5bd8-b393-3998f1ef7305")
PHASE25_EVIDENCE_SNAPSHOT_NAMESPACE: Final = UUID("a8f24083-8415-5eec-a872-46681cac97f8")

PHASE25_PHASE24_MERGE_COMMIT_SHA: Final = "145f67f188befae46443d061d029c243858841b4"
PHASE25_PHASE24_MERGE_TREE_SHA: Final = "27392b6eb3239e01e533d07d42d164124fb7aa18"
PHASE25_ACCEPTED_PHASE24_COMMIT_SHA: Final = "c1dad09f08b18a5a7d527579ca677633b49184fb"
PHASE25_ACCEPTED_PHASE24_TREE_SHA: Final = PHASE25_PHASE24_MERGE_TREE_SHA
PHASE25_PHASE24_ARTIFACT_ID: Final = "c7653056-2f58-5137-bc7a-29ea0e7b85a9"
PHASE25_PHASE24_ARTIFACT_SHA256: Final = (
    "936abe1205d9cc9fb956f7ae1577275062daa544b2a1361f9891b47029e93a52"
)
PHASE25_PHASE24_ARTIFACT_FILE_SHA256: Final = (
    "5ad6b7b8e5c60fa1b2e76445b11ef0428d68515dd97439e6b21fc487aea91417"
)
PHASE25_PHASE24_POLICY_SHA256: Final = (
    "6a966cc1cd2f24df62d66939923bf44e623430932d81a1f5f7e5078f84ab22dd"
)
PHASE25_PHASE24_QUESTIONS_MANIFEST_SHA256: Final = (
    "14fbf92713f68c77a36b1b7f330de95021bc0b8347497bcbf1ff86f4fd363afb"
)
PHASE25_PRODUCT_CODE: Final = "PHILADELPHIA_FED_REAL_TIME_DATA_SET_FOR_MACROECONOMISTS"
PHASE25_PRODUCT_NAME: Final = (
    "Federal Reserve Bank of Philadelphia Real-Time Data Set for Macroeconomists (RTDSM)"
)
PHASE25_FAMILY: Final = "A_CROSS_SECTIONAL_EQUITY_RANKING"
PHASE25_GENERATED_AT_UTC: Final = "2026-07-21T15:00:00.000000Z"
PHASE25_SOURCE_RESEARCH_AT_UTC: Final = "2026-07-21T14:20:00.000000Z"
PHASE25_GENERATION_GIT_SHA: Final = PHASE25_PHASE24_MERGE_COMMIT_SHA
PHASE25_RANDOM_SEED: Final = 0
PHASE25_TRIAL_COUNT: Final = 0
PHASE25_OUTCOME: Final = "BLOCKED"
PHASE25_DETERMINATION: Final = "RIGHTS_RESPONSE_EVIDENCE_MISSING"
PHASE25_BLOCK_REASON: Final = "No authenticated RTDSM rights-clarification response or independently verified authority and exact-scope evidence was supplied."
PHASE25_MISSING_FINDING: Final = "No independently verified exact-scope evidence was supplied."

# Exact Phase 24 question order is inherited byte-for-byte as semantic lineage.
PHASE25_QUESTION_ROWS: Final = (
    (
        "PERSISTENT_STORAGE",
        "persistent_storage",
        "May Fable5 persist exact RTDSM delivery bytes and normalized point-in-time snapshots, including reproducibility copies and backups?",
    ),
    (
        "AUTOMATED_MODEL_INTERNAL_USE",
        "automated_model_internal_use",
        "May Fable5 use RTDSM data in automated internal feature generation, statistical modeling, backtesting, and simulated paper-trading research?",
    ),
    (
        "DERIVED_DATA_AND_MODEL_ARTIFACTS",
        "derived_data",
        "May Fable5 retain and use derived features, aggregates, diagnostics, model parameters, and audit hashes after processing RTDSM data?",
    ),
    (
        "RETENTION_DELETION",
        "retention_deletion",
        "What retention limits, deletion deadlines, backup handling, and post-termination obligations apply to raw and derived artifacts?",
    ),
    (
        "REDISTRIBUTION_AND_DISPLAY",
        "redistribution",
        "What internal sharing, user display, export, publication, and redistribution restrictions apply to raw values and derived outputs?",
    ),
    (
        "ATTRIBUTION",
        "attribution",
        "What source labels, notices, citations, or attribution text are required for stored data and derived outputs?",
    ),
    (
        "THIRD_PARTY_BLS_CONTENT",
        "third_party_content",
        "Does the permission cover BLS-originated PCPI content for the exact proposed uses, or is separate rights-holder permission required?",
    ),
    (
        "AUTOMATED_ACCESS_AND_LOAD",
        "access_load",
        "Which delivery method, automated access pattern, frequency, concurrency, and rate or bulk-download limits are authorized?",
    ),
    (
        "REVOCATION_AND_CURRENTNESS",
        "revocation_currentness",
        "What effective date, term version, change notice, revocation trigger, cure period, and revalidation cadence govern the permission?",
    ),
    (
        "AUTHORITY_AND_PRODUCT_SCOPE",
        "operational_use_cleared",
        "Which rights-holding entity and authorized representative can bind the exact product, series, delivery, account, users, and proposed use?",
    ),
)

# code, requirement. Every row must be independently evidenced for a positive result.
PHASE25_SCOPE_ROWS: Final = (
    ("PRODUCT", "Bind the response to the Federal Reserve Bank of Philadelphia RTDSM product."),
    ("REQUESTED_SERIES", "List every requested RTDSM series exactly."),
    ("PCPI_AND_BLS_ORIGIN", "State whether PCPI and any other BLS-originated content are covered."),
    (
        "DELIVERY_METHOD_AND_SURFACE",
        "Bind the permission to the exact delivery method and file or API surface.",
    ),
    (
        "LICENSED_PARTY",
        "Identify the licensed party as the individual account holder, not PwC or another employer.",
    ),
    (
        "ACCOUNT_OR_ENTITLEMENT",
        "Record the account or entitlement identifier only as a sanitized SHA-256.",
    ),
    ("PERMITTED_USERS_AND_DEVICES", "Specify every permitted user and device boundary."),
    ("ENVIRONMENTS", "Cover local development, test, and simulated paper-trading environments."),
    ("AUTOMATED_ACCESS_LIMITS", "Specify frequency, concurrency, rate, and bulk-access limits."),
    (
        "RAW_PAYLOAD_STORAGE",
        "Resolve storage of exact delivery bytes without storing them in this artifact.",
    ),
    ("IMMUTABLE_SNAPSHOT_STORAGE", "Resolve immutable point-in-time snapshot storage."),
    ("BACKUPS_AND_REPRODUCIBILITY", "Resolve backups and reproducibility copies."),
    ("NORMALIZATION_AND_POINT_IN_TIME", "Resolve normalization and point-in-time transformation."),
    (
        "INTERNAL_RESEARCH_USES",
        "Resolve feature generation, statistical modeling, backtesting, and simulated paper trading.",
    ),
    (
        "DERIVED_ARTIFACTS",
        "Resolve derived features, diagnostics, model parameters, and audit hashes.",
    ),
    (
        "DISPLAY_EXPORT_SHARING_PUBLICATION_REDISTRIBUTION",
        "Resolve display, export, sharing, publication, and redistribution separately.",
    ),
    ("ATTRIBUTION", "Specify required source labels, notices, and citations."),
    (
        "RETENTION_DELETION_TERMINATION",
        "Specify retention, deletion, termination, and backup handling.",
    ),
    (
        "REVOCATION_AND_REVALIDATION",
        "Specify revocation triggers, notice, cessation, expiry, and revalidation cadence.",
    ),
)


def _source(**values: object) -> MappingProxyType[str, object]:
    return MappingProxyType(values)


PHASE25_SOURCE_ROWS: Final = (
    _source(
        code="YFINANCE",
        kind="OPEN_SOURCE_REPOSITORY",
        url="https://github.com/ranaroussi/yfinance",
        inspected_revision="38c73ce33fb1ee77d37a0998c95c06e60356298e",
        revision_kind="COMMIT",
        software_license="Apache-2.0",
        license_file="LICENSE.txt",
        license_blob_oid="d645695673349e3947e8e5ae42332d0ac3164cd7",
        inspected_paths=(
            "README.md",
            "yfinance/data.py",
            "yfinance/scrapers/history.py",
            "yfinance/multi.py",
            "yfinance/cache.py",
            "tests/test_cache.py",
            "tests/test_data.py",
        ),
        provider_abstraction="Central YfData singleton and call-level Ticker/history facades; useful as a session-ownership reference, not a provider-neutral contract.",
        request_session_ownership="One shared session/cookie/crumb owner across threads, with caller session validation and locks.",
        timeout_retry_backoff_rate_limit="Per-call timeout defaults to 10 seconds; explicit rate-limit exception; transient request retry exists, while project README does not grant Yahoo data rights.",
        schema_validation_normalization="DataFrame parsing, metadata checks, empty/error classification, optional repair, and multi-ticker alignment; not a strict point-in-time schema contract.",
        timestamp_timezone="Parses exchange timezone, converts Unix timestamps through UTC, and optionally strips timezone on combined daily data.",
        corporate_action_revision="Can return dividends, splits, and capital gains; repair logic may alter results and must not be adopted as authoritative revision semantics.",
        caching_persistence="SQLite caches for timezone/cookie/ISIN metadata and in-memory response caching; persistent market-data rights remain separate.",
        error_sanitization="Typed errors exist, but upstream bodies and ticker-specific details may reach logs unless independently bounded.",
        deterministic_testing="Temporary cache directories, singleton reset, immutable-argument cache tests, and unit tests; some upstream tests access live services.",
        rights_warning="README says yfinance is unaffiliated with Yahoo, points to Yahoo terms, and states the Finance API is intended for personal use only. Apache-2.0 covers software, not Yahoo data.",
        unresolved_limitations="Yahoo product scope, continuing availability, point-in-time fitness, accuracy, storage, and intended-use rights remain RIGHTS_UNVERIFIED.",
    ),
    _source(
        code="OPENBB",
        kind="OPEN_SOURCE_REPOSITORY",
        url="https://github.com/OpenBB-finance/OpenBB",
        inspected_revision="3e071fcc2cd9f891cac6040ae60296dba76dab46",
        revision_kind="COMMIT",
        software_license="AGPL-3.0-only",
        license_file="LICENSE",
        license_blob_oid="e07622137b2bcebcec8df47529dba2317a3f5a82",
        inspected_paths=(
            "openbb_platform/core/openbb_core/provider/abstract/fetcher.py",
            "openbb_platform/core/openbb_core/provider/query_executor.py",
            "openbb_platform/providers/yfinance/openbb_yfinance/models/equity_historical.py",
            "openbb_platform/providers/yfinance/openbb_yfinance/utils/helpers.py",
            "openbb_platform/providers/yfinance/tests/test_yfinance_fetchers.py",
        ),
        provider_abstraction="Strong provider registry plus transform_query/extract_data/transform_data fetcher lifecycle and standard models.",
        request_session_ownership="Provider helpers own transport details; query executor filters SecretStr credentials before dispatch.",
        timeout_retry_backoff_rate_limit="Behavior is provider-specific rather than uniformly guaranteed; the pattern requires an explicit neutral transport policy before reuse.",
        schema_validation_normalization="Pydantic query/result models and model_validate at the provider boundary are directly reusable as an independently implemented pattern.",
        timestamp_timezone="Provider adapters normalize dates/timezones; the inspected Yahoo helper can remove timezone information, which is unsuitable for an audit source of truth without preserving raw timestamps.",
        corporate_action_revision="Historical fetcher exposes optional actions, but no general authoritative revision/delisting guarantee follows from the abstraction.",
        caching_persistence="Test recordings and provider behavior vary; persistence policy is not a substitute for provider rights.",
        error_sanitization="VCR configuration scrubs cookies, crumbs, headers, dates, and response fragments; useful as a test-sanitization reference.",
        deterministic_testing="Provider contract tests and scrubbed VCR recordings demonstrate bounded fixture-driven testing, subject to license and data-rights review.",
        rights_warning="AGPL software rights do not grant rights to any connected provider data; adaptations must be independently implemented or comply with AGPL obligations.",
        unresolved_limitations="No inspected abstraction establishes RTDSM or Yahoo rights, source authority, or point-in-time fitness.",
    ),
    _source(
        code="FINROBOT",
        kind="OPEN_SOURCE_REPOSITORY",
        url="https://github.com/AI4Finance-Foundation/FinRobot",
        inspected_revision="297a8d28d099be328c8a8eb658b4f782b93f3651",
        revision_kind="COMMIT",
        software_license="Apache-2.0",
        license_file="LICENSE",
        license_blob_oid="6cc0d28c44e482825bba73c84761e3d65f138f42",
        inspected_paths=(
            "finrobot/data_source/yfinance_utils.py",
            "finrobot/data_source/finnhub_utils.py",
            "finrobot/data_source/fmp_utils.py",
            "finrobot/data_source/sec_utils.py",
        ),
        provider_abstraction="Utility classes group vendor calls, but clients and credentials are often global and not provider-neutral.",
        request_session_ownership="Mostly implicit library/global clients; direct requests calls do not demonstrate bounded session ownership.",
        timeout_retry_backoff_rate_limit="Inspected direct requests calls generally omit explicit timeout, retry, backoff, and rate-limit controls.",
        schema_validation_normalization="Returns DataFrames, strings, and dictionaries without a shared strict boundary schema.",
        timestamp_timezone="Date parameters exist, but no uniform UTC availability-time contract is evident in the inspected utilities.",
        corporate_action_revision="Thin yfinance dividend access and filing helpers do not establish revision or corporate-action authority.",
        caching_persistence="SEC helper writes a local text cache; this is an anti-pattern until rights, keys, provenance, and retention are explicit.",
        error_sanitization="Some errors and URLs can include provider context; credential-bearing URLs and broad exception strings are patterns to reject.",
        deterministic_testing="The inspected data utilities lack a comprehensive synthetic transport contract suite.",
        rights_warning="Software license does not grant vendor-data rights; project data utilities must not be treated as evidence of lawful or accurate access.",
        unresolved_limitations="Use only as an anti-pattern inventory for globals, unbounded requests, credential-bearing URLs, and mixed return schemas.",
    ),
    _source(
        code="TRADINGAGENTS",
        kind="OPEN_SOURCE_REPOSITORY",
        url="https://github.com/TauricResearch/TradingAgents",
        inspected_revision="a33fd4c0f134485a43553a2c23a63cb14adbd88f",
        revision_kind="COMMIT",
        software_license="Apache-2.0",
        license_file="LICENSE",
        license_blob_oid="261eeb9e9f8b2b4b0d119366dda99c6fd7d35c64",
        inspected_paths=(
            "tradingagents/dataflows/interface.py",
            "tradingagents/dataflows/errors.py",
            "tradingagents/dataflows/stockstats_utils.py",
            "tradingagents/dataflows/market_data_validator.py",
            "tests/test_ohlcv_cache_freshness.py",
        ),
        provider_abstraction="Category/tool registry routes to vendor implementations with typed behavioral errors and fallback chains.",
        request_session_ownership="Vendor modules own calls; no single neutral session contract is enforced across providers.",
        timeout_retry_backoff_rate_limit="Explicit Alpha Vantage timeout, typed rate-limit errors, and yfinance exponential backoff; retry lacks jitter and sleeps synchronously.",
        schema_validation_normalization="OHLCV cleanup, stale-data rejection, symbol normalization, and error taxonomy are useful plumbing references, not authoritative data schemas.",
        timestamp_timezone="Filters rows to the requested date but sometimes strips timezone; a future adapter must preserve UTC availability and source timezone metadata.",
        corporate_action_revision="Yahoo plumbing does not establish authoritative corporate-action or vintage revision handling.",
        caching_persistence="Per-symbol CSV cache with a same-day TTL and stale-cache tests; historical immutability assumptions must not be copied blindly.",
        error_sanitization="Typed error classes are reusable conceptually, but some functions return or print exception text and must not be copied.",
        deterministic_testing="Synthetic monkeypatch tests cover cache freshness, stale rows, routing, and configuration isolation.",
        rights_warning="Study data-access plumbing only. Do not copy any LLM trade-decision, position-size, or order design. Yahoo rights remain unverified.",
        unresolved_limitations="Fallback retrieval is not proof of lawful use, accuracy, point-in-time fitness, or provider continuity.",
    ),
    _source(
        code="PHILADELPHIA_FED_RTDSM_PAGE",
        kind="OFFICIAL_DOCUMENT",
        url="https://www.philadelphiafed.org/surveys-and-data/real-time-data-research/real-time-data-set-for-macroeconomists",
        inspected_revision="fd2215999b11ecd106ea634a511261e61a8451082fee5bbb74ce779e84ba7cb6",
        revision_kind="CONTENT_SHA256",
        software_license="UNSPECIFIED_PROVIDER_CONTENT",
        license_file="",
        license_blob_oid="",
        inspected_paths=(),
        provider_abstraction="Official product description and file-download surface.",
        request_session_ownership="Not documented as an API/session contract.",
        timeout_retry_backoff_rate_limit="Not documented for automated access.",
        schema_validation_normalization="Describes vintage columns and release-value files, not an application schema.",
        timestamp_timezone="Monthly update cadence is described; exact availability timestamps are not granted as an API contract.",
        corporate_action_revision="Documents macro vintages and revisions.",
        caching_persistence="Persistent storage rights are not resolved.",
        error_sanitization="Not applicable.",
        deterministic_testing="Documentation only.",
        rights_warning="Public availability and research examples do not resolve persistent automated-model rights.",
        unresolved_limitations="Authority, exact series/delivery/account scope, storage, derived use, retention, and revocation remain unresolved.",
    ),
    _source(
        code="PHILADELPHIA_FED_ONLINE_TERMS",
        kind="OFFICIAL_DOCUMENT",
        url="https://www.philadelphiafed.org/about-us/privacy-notice",
        inspected_revision="acde615dcde889dd1f848242a982c816ceaf92344f6afeba33bf356d33813a98",
        revision_kind="CONTENT_SHA256",
        software_license="UNSPECIFIED_PROVIDER_CONTENT",
        license_file="",
        license_blob_oid="",
        inspected_paths=(),
        provider_abstraction="Official online terms snapshot.",
        request_session_ownership="Excessive or disruptive access may be restricted.",
        timeout_retry_backoff_rate_limit="No exact automated access limits are specified.",
        schema_validation_normalization="Not applicable.",
        timestamp_timezone="Page states last update 2026-04-01; snapshot captured in UTC.",
        corporate_action_revision="Not applicable.",
        caching_persistence="Research use is stated, but copyrighted third-party content may require owner permission.",
        error_sanitization="Not applicable.",
        deterministic_testing="Content SHA-256 preserves the inspected snapshot identity.",
        rights_warning="Informational, educational, and research use language is not an authenticated exact-scope grant for RTDSM automation or storage.",
        unresolved_limitations="Provider authority and BLS-originated content rights remain unresolved.",
    ),
    _source(
        code="PHILADELPHIA_FED_PCPI_DOCUMENTATION",
        kind="OFFICIAL_DOCUMENT",
        url="https://www.philadelphiafed.org/-/media/FRBP/Assets/Surveys-And-Data/real-time-data/data-files/PCPI/Specific_Documentation_PCPI.pdf",
        inspected_revision="e843206d329ff0913580f5fe2161089a593b1b4cd4f0612dbaa852b2dc67acde",
        revision_kind="CONTENT_SHA256",
        software_license="UNSPECIFIED_PROVIDER_CONTENT",
        license_file="",
        license_blob_oid="",
        inspected_paths=(),
        provider_abstraction="Official metadata documentation for RTDSM PCPI.",
        request_session_ownership="Not applicable.",
        timeout_retry_backoff_rate_limit="Not applicable.",
        schema_validation_normalization="Identifies PCPI as seasonally adjusted CPI and documents revisions.",
        timestamp_timezone="Describes monthly vintages; no entitlement timing contract.",
        corporate_action_revision="Documents BLS seasonal-factor revisions incorporated into February vintages.",
        caching_persistence="No storage permission is stated.",
        error_sanitization="Not applicable.",
        deterministic_testing="Content SHA-256 identifies the inspected PDF.",
        rights_warning="Confirms BLS origin but does not establish upstream rights coverage.",
        unresolved_limitations="Separate BLS/rightsholder permission question remains open.",
    ),
    _source(
        code="PHILADELPHIA_FED_RELEASE_VALUES_DOCUMENTATION",
        kind="OFFICIAL_DOCUMENT",
        url="https://www.philadelphiafed.org/-/media/frbp/assets/surveys-and-data/real-time-data/data-files/documentation/documentation_first_second_third_release_values.pdf",
        inspected_revision="306460c8403545c57761e2c88d0957b2e78ae42bb5187bd20d4cf8d388b1be7f",
        revision_kind="CONTENT_SHA256",
        software_license="UNSPECIFIED_PROVIDER_CONTENT",
        license_file="",
        license_blob_oid="",
        inspected_paths=(),
        provider_abstraction="Official RTDSM first/second/third-release methodology documentation.",
        request_session_ownership="Not applicable.",
        timeout_retry_backoff_rate_limit="Not applicable.",
        schema_validation_normalization="Documents vintage layout, transformations, and caveats.",
        timestamp_timezone="Uses dated vintages; no automated availability API contract.",
        corporate_action_revision="Revision methodology is central and explicitly documented.",
        caching_persistence="No storage rights are stated.",
        error_sanitization="Not applicable.",
        deterministic_testing="Content SHA-256 identifies the inspected PDF.",
        rights_warning="Methodology and research suitability do not grant operational rights.",
        unresolved_limitations="Exact requested-series scope and current rights remain unresolved.",
    ),
    _source(
        code="YAHOO_API_TERMS",
        kind="OFFICIAL_DOCUMENT",
        url="https://legal.yahoo.com/us/en/yahoo/terms/product-atos/apiforydn/index.html",
        inspected_revision="f88226275015c97165d3856db07402eb45f5f86d63e4e95a18e5c5248c1c2f1b",
        revision_kind="CONTENT_SHA256",
        software_license="PROPRIETARY_TERMS",
        license_file="",
        license_blob_oid="",
        inspected_paths=(),
        provider_abstraction="General Yahoo API terms, not a confirmed Yahoo Finance market-data product entitlement.",
        request_session_ownership="Terms require applicable account/API documents and permit discretionary rate limits.",
        timeout_retry_backoff_rate_limit="Rate limits may be imposed at Yahoo's discretion; no yfinance-specific limits are established.",
        schema_validation_normalization="No market-data schema fitness guarantee.",
        timestamp_timezone="Terms can change by posting; currentness must be revalidated.",
        corporate_action_revision="No authoritative market-history or corporate-action guarantee.",
        caching_persistence="Storage/use provisions do not resolve yfinance's exact Finance data surface for this project.",
        error_sanitization="Not applicable.",
        deterministic_testing="Content SHA-256 identifies the inspected terms snapshot.",
        rights_warning="Revocable general API terms and software/API access rights do not grant rights to all Yahoo Finance data.",
        unresolved_limitations="Exact current Yahoo Finance terms, product scope, and intended-use rights remain RIGHTS_UNVERIFIED.",
    ),
    _source(
        code="YAHOO_GENERAL_TERMS",
        kind="OFFICIAL_DOCUMENT",
        url="https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html",
        inspected_revision="8e2e79ccae307771e43be015f98965e28561a9066cd23d3c70057513babc5c54",
        revision_kind="CONTENT_SHA256",
        software_license="PROPRIETARY_TERMS",
        license_file="",
        license_blob_oid="",
        inspected_paths=(),
        provider_abstraction="General Yahoo service terms.",
        request_session_ownership="Personal, revocable service/API license subject to product-specific terms.",
        timeout_retry_backoff_rate_limit="High-volume activity may require prior written consent.",
        schema_validation_normalization="No data accuracy or point-in-time fitness guarantee.",
        timestamp_timezone="Terms snapshot is current only as of the research timestamp.",
        corporate_action_revision="No guarantee.",
        caching_persistence="Ownership/reuse restrictions require exact product terms or written permission.",
        error_sanitization="Not applicable.",
        deterministic_testing="Content SHA-256 identifies the inspected terms snapshot.",
        rights_warning="General terms do not prove that yfinance retrieval is authorized for storage, modeling, backtesting, or redistribution.",
        unresolved_limitations="Yahoo remains disabled and RIGHTS_UNVERIFIED.",
    ),
)

PHASE25_PATTERN_ROWS: Final = (
    (
        "PROVIDER_NEUTRAL_FETCHER_LIFECYCLE",
        "Separate validated query transformation, transport extraction, and normalized result transformation behind a provider-neutral port.",
        ("OPENBB",),
        "INDEPENDENT_REIMPLEMENTATION",
        "DOCUMENTED_NOT_IMPLEMENTED",
    ),
    (
        "CALL_SCOPED_TRANSPORT_OWNER",
        "One adapter-owned session per bounded call or adapter instance; never a strategy-owned SDK client or ambient global credential.",
        ("YFINANCE", "OPENBB"),
        "INDEPENDENT_REIMPLEMENTATION",
        "DOCUMENTED_NOT_IMPLEMENTED",
    ),
    (
        "BOUNDED_TIMEOUT_RETRY_AND_RATE_LIMIT",
        "Require finite connect/read timeouts, typed rate-limit errors, capped exponential backoff with deterministic test hooks, and no retry around access controls.",
        ("YFINANCE", "TRADINGAGENTS"),
        "INDEPENDENT_REIMPLEMENTATION",
        "DOCUMENTED_NOT_IMPLEMENTED",
    ),
    (
        "STRICT_BOUNDARY_SCHEMA",
        "Validate provider query and normalized result objects with strict Pydantic models; reject unknown fields and empty/stale results.",
        ("OPENBB", "TRADINGAGENTS"),
        "INDEPENDENT_REIMPLEMENTATION",
        "DOCUMENTED_NOT_IMPLEMENTED",
    ),
    (
        "UTC_AVAILABILITY_AND_SOURCE_TIME",
        "Preserve source timezone and raw timestamp metadata while deriving explicit UTC availability timestamps; never silently strip provenance.",
        ("YFINANCE", "OPENBB", "TRADINGAGENTS"),
        "INDEPENDENT_REIMPLEMENTATION",
        "DOCUMENTED_NOT_IMPLEMENTED",
    ),
    (
        "RAW_NORMALIZED_REVISION_SEPARATION",
        "Keep delivery evidence, normalized point-in-time values, revisions, and corporate actions in separate typed channels only after rights authorize storage.",
        ("PHILADELPHIA_FED_RELEASE_VALUES_DOCUMENTATION",),
        "INDEPENDENT_REIMPLEMENTATION",
        "DOCUMENTED_NOT_IMPLEMENTED",
    ),
    (
        "RIGHTS_GATED_CACHE_AND_SNAPSHOT",
        "No cache or immutable snapshot is created until exact storage, backup, retention, and deletion rights pass; cache keys bind provider, request, entitlement hash, and source version.",
        ("YFINANCE", "TRADINGAGENTS", "PHILADELPHIA_FED_ONLINE_TERMS"),
        "INDEPENDENT_REIMPLEMENTATION",
        "DOCUMENTED_NOT_IMPLEMENTED",
    ),
    (
        "SANITIZED_ERROR_AND_EVIDENCE_BOUNDARY",
        "Allowlisted metadata and hashes may cross the boundary; credentials, account identifiers, provider bodies, cookies, crumbs, URLs with secrets, and raw response excerpts may not enter artifacts, logs, or exceptions.",
        ("OPENBB", "FINROBOT"),
        "INDEPENDENT_REIMPLEMENTATION",
        "DOCUMENTED_NOT_IMPLEMENTED",
    ),
    (
        "OFFLINE_SYNTHETIC_CONTRACT_TESTS",
        "Use deterministic synthetic HTTP metadata and scrubbed fixtures to test timeouts, retries, rate limits, schema drift, revisions, redaction, and fail-closed rights gates without provider observations.",
        ("OPENBB", "TRADINGAGENTS"),
        "INDEPENDENT_REIMPLEMENTATION",
        "DOCUMENTED_NOT_IMPLEMENTED",
    ),
    (
        "LLM_NON_ALPHA_BOUNDARY",
        "Data-access plumbing may emit typed observations or text features only; no LLM-originated trade decision, position size, order, or execution path is permitted.",
        ("FINROBOT", "TRADINGAGENTS"),
        "REJECT_UPSTREAM_TRADING_DESIGN",
        "DOCUMENTED_NOT_IMPLEMENTED",
    ),
    (
        "YAHOO_DISABLED_UNTIL_VERIFIED",
        "Keep Yahoo/yfinance absent from dependencies and runtime until exact current terms, product scope, intended use, storage, attribution, and retention rights independently verify.",
        ("YFINANCE", "YAHOO_API_TERMS", "YAHOO_GENERAL_TERMS"),
        "RIGHTS_GATE_ONLY",
        "DOCUMENTED_NOT_IMPLEMENTED",
    ),
)

PHASE25_RULE_ROWS: Final = (
    (
        "MISSING_AUTHORITY_BLOCKS",
        "Missing or ambiguous responder identity, role, authority basis, rights-holding entity, authenticated provenance, or independent verification keeps the aggregate blocked.",
    ),
    (
        "ALL_TEN_QUESTIONS_REQUIRED",
        "Every Phase 24 question must have mutually consistent PASS or enforceable CONDITIONAL evidence before rights can verify.",
    ),
    (
        "ALL_SCOPE_ELEMENTS_REQUIRED",
        "Every exact product, series, delivery, party, account, user, environment, access, storage, use, output, attribution, retention, and revocation scope element must satisfy.",
    ),
    (
        "CONDITIONS_REQUIRE_CONTROLS",
        "CONDITIONAL satisfies only when every condition has an enforceable fail-closed control, a portable acceptance test identifier, and a passed test.",
    ),
    (
        "FAIL_OR_MISSING_BLOCKS",
        "Any FAIL or MISSING question or scope element keeps acquisition, storage, ingestion, research, and operational composition blocked.",
    ),
    (
        "EVIDENCE_REFERENCES_MUST_VERIFY",
        "Every cited evidence identifier must resolve to an independently verified metadata record with an immutable SHA-256 and authenticated provenance.",
    ),
    (
        "CHANGE_INVALIDATES_VERIFICATION",
        "A change to terms, product, series, delivery, licensed party, entitlement, users, use, rights holder, expiry, or revocation state requires full revalidation.",
    ),
    (
        "REPOSITORY_AUTHORITY_IS_IRRELEVANT",
        "Requester identity, employer, title, repository ownership, commit, PR approval, credential possession, or successful retrieval is never provider-rights evidence.",
    ),
    (
        "POSITIVE_RESULT_ONLY_ENABLES_LATER_REQUEST",
        "A verified response may only support a separately authorized acquisition decision; Phase 25 never activates an adapter or fetches observations.",
    ),
)

PHASE25_BOUNDARY_VALUES: Final = MappingProxyType(
    {
        "phase24_artifact_unchanged": True,
        "phase24_merge_is_ancestor": True,
        "response_received": False,
        "authority_evidence_present": False,
        "rights_verified": False,
        "provider_contact_performed": False,
        "provider_observations_downloaded": False,
        "provider_observations_persisted": False,
        "credentials_loaded": False,
        "production_adapter_activated": False,
        "operational_provider_selected": False,
        "yfinance_dependency_added": False,
        "yahoo_rights_state": "RIGHTS_UNVERIFIED",
        "runtime_network_disabled": True,
        "generation_network_disabled": True,
        "verification_network_disabled": True,
        "synthetic_tests_only": True,
        "database_changed": False,
        "api_changed": False,
        "research_run_executed": False,
        "performance_computed": False,
        "strategy_promoted": False,
        "risk_limits_changed": False,
        "paper_order_submitted": False,
        "execution_authorized": False,
        "live_path_absent": True,
        "llm_trade_decisions_prohibited": True,
    }
)

PHASE25_DISCLAIMER: Final = "Evidence-intake and open-source feasibility only; not legal advice, a rights grant, provider selection, data acquisition, ingestion, research, performance, strategy, risk approval, execution authority, an order, or investment advice. Requester authority is personal and does not represent PwC or any provider rights holder."


def _policy_payload() -> dict[str, object]:
    return {
        name: value
        for name, value in globals().items()
        if name.startswith("PHASE25_")
        and name
        not in {
            "PHASE25_POLICY_SHA256",
            "PHASE25_ARTIFACT_NAMESPACE",
            "PHASE25_SOURCE_SNAPSHOT_NAMESPACE",
            "PHASE25_EVIDENCE_SNAPSHOT_NAMESPACE",
        }
    } | {
        "artifact_uuid_namespace": str(PHASE25_ARTIFACT_NAMESPACE),
        "source_snapshot_namespace": str(PHASE25_SOURCE_SNAPSHOT_NAMESPACE),
        "evidence_snapshot_namespace": str(PHASE25_EVIDENCE_SNAPSHOT_NAMESPACE),
    }


PHASE25_POLICY_SHA256: Final = domain_sha256(PHASE25_POLICY_HASH_DOMAIN, _policy_payload())


def identity(policy_sha256: str = PHASE25_POLICY_SHA256) -> UUID:
    return uuid_from_sha256(PHASE25_ARTIFACT_NAMESPACE, policy_sha256)


__all__ = [name for name in globals() if name.startswith("PHASE25_")] + [
    "canonical_json_bytes",
    "canonicalize",
    "domain_sha256",
    "identity",
]
