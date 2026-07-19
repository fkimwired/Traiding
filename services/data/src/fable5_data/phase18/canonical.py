"""Canonical constants and hash domains for the Phase 18 rights review."""

from __future__ import annotations

from types import MappingProxyType
from typing import Final
from uuid import UUID

from fable5_data.canonical import canonical_json_bytes as canonical_json_bytes
from fable5_data.canonical import canonicalize as canonicalize
from fable5_data.canonical import domain_sha256 as domain_sha256
from fable5_data.canonical import uuid_from_sha256

PHASE18_ARTIFACT_SCHEMA_VERSION: Final = "phase18-family-a-current-use-rights-review-v1"
PHASE18_ARTIFACT_HASH_DOMAIN: Final = PHASE18_ARTIFACT_SCHEMA_VERSION
PHASE18_POLICY_ID: Final = "phase18-family-a-current-use-rights-review-policy-v1"
PHASE18_POLICY_HASH_DOMAIN: Final = PHASE18_POLICY_ID
PHASE18_SOURCE_SCHEMA_VERSION: Final = "phase18-family-a-public-terms-source-v1"
PHASE18_SOURCE_HASH_DOMAIN: Final = PHASE18_SOURCE_SCHEMA_VERSION
PHASE18_FINDING_SCHEMA_VERSION: Final = "phase18-family-a-product-rights-finding-v1"
PHASE18_FINDING_HASH_DOMAIN: Final = PHASE18_FINDING_SCHEMA_VERSION
PHASE18_STEP_SCHEMA_VERSION: Final = "phase18-family-a-source-plan-step-evidence-v1"
PHASE18_STEP_HASH_DOMAIN: Final = PHASE18_STEP_SCHEMA_VERSION
PHASE18_OUTPUT_SCHEMA_VERSION: Final = "phase18-family-a-source-plan-output-v1"
PHASE18_OUTPUT_HASH_DOMAIN: Final = PHASE18_OUTPUT_SCHEMA_VERSION
PHASE18_SOURCES_MANIFEST_HASH_DOMAIN: Final = "phase18-public-terms-sources-manifest-v1"
PHASE18_REVIEW_MANIFEST_HASH_DOMAIN: Final = "phase18-independent-rights-review-manifest-v1"
PHASE18_CURRENTNESS_HASH_DOMAIN: Final = "phase18-rights-currentness-review-snapshot-v1"
PHASE18_STEPS_MANIFEST_HASH_DOMAIN: Final = "phase18-source-plan-steps-manifest-v1"
PHASE18_ARTIFACT_NAMESPACE: Final = UUID("50f38b59-85dc-5a38-be19-e9e035ed9284")

PHASE18_ACCEPTED_PHASE17_COMMIT_SHA: Final = "fd89d3905e9c2ea12223e30b5822a0fdda795a26"
PHASE18_ACCEPTED_PHASE17_TREE_SHA: Final = "f2eb791785dd10cc9316d174505b65eda919fe71"
PHASE18_PHASE17_ARTIFACT_ID: Final = "19d213d5-ec44-53fc-a146-f4f77a06102d"
PHASE18_PHASE17_ARTIFACT_SHA256: Final = (
    "48584cf614c7713b05417a6d9333ca400f2d1c19fb0d3f047ced42e9ef4eb8f4"
)
PHASE18_PHASE17_POLICY_SHA256: Final = (
    "0a36f01630a40c55d20139117641abcc8313e5f8b5a0be5fce15fd4c8ad2b3cf"
)
PHASE18_PHASE17_INVENTORY_SHA256: Final = (
    "070f36391093385ccd0e7feafc54d18c08e71cc8aa145bd30acea07abbffc76c"
)
PHASE18_PHASE17_CANDIDATE_GROUPS_MANIFEST_SHA256: Final = (
    "8416991d72e5da5ec83025090e167c2d03a52766fd173be86676f307ec53e623"
)
PHASE18_PHASE17_STEPS_MANIFEST_SHA256: Final = (
    "f762a287ac7488dbe33aed32c220f4ebd0fef66bff685f353f2e798d54d34015"
)
PHASE18_PHASE16_STEP2_SHA256: Final = (
    "82fc821a86ec52c575e83bc6a6adf6bd5fc7471beba72b49eb13ac96d8d88dfe"
)
PHASE18_FAMILY: Final = "A_CROSS_SECTIONAL_EQUITY_RANKING"
PHASE18_FROZEN_AT_UTC: Final = "2026-07-19T15:58:18.5305832Z"
PHASE18_AGGREGATE_CONCLUSION: Final = "BLOCKED_NO_OPERATIONAL_SELECTION"
PHASE18_RIGHTS_STATUS_VALUES: Final = (
    "ALLOWED_PUBLIC",
    "CONDITIONAL_ACCOUNT_LICENSE",
    "PRIVATE_LICENSE_REQUIRED",
    "PROHIBITED_PUBLIC_TERMS",
    "UNPROVEN",
)

PHASE18_PRODUCT_ROWS: Final = (
    (
        "TIINGO_END_OF_DAY",
        "823f95259d3a9132a8c3e8cd58ed850e5a958c9ecf11c3777252a34b772c0bac",
        (
            "TIINGO_TERMS_OF_USE",
            "TIINGO_GENERAL_API_DOCUMENTATION",
            "TIINGO_API_PRICING",
            "TIINGO_EOD_DOCUMENTATION",
        ),
        "PROHIBITED_PUBLIC_TERMS",
        "CONDITIONAL_ACCOUNT_LICENSE",
        "PROHIBITED_PUBLIC_TERMS",
        "UNPROVEN",
        "PRIVATE_LICENSE_REQUIRED",
        "CONDITIONAL_ACCOUNT_LICENSE",
        "CONDITIONAL_ACCOUNT_LICENSE",
        "UNPROVEN",
        "BLOCKED_STANDARD_TERMS_DO_NOT_GRANT_PERSISTENT_DATABASE_RIGHTS",
        (
            "Public Tiingo terms describe internal consumption, but no Fable5 account, plan, "
            "supplemental terms, or written permission proves storage, derived-data, retention, "
            "or redistribution rights for this product."
        ),
    ),
    (
        "TIINGO_US_FUNDAMENTALS",
        "0c89b810f92394b4b026f85464040280b01aca28126f864fd163d19bcef7cfbe",
        (
            "TIINGO_TERMS_OF_USE",
            "TIINGO_GENERAL_API_DOCUMENTATION",
            "TIINGO_API_PRICING",
            "TIINGO_FUNDAMENTALS_DOCUMENTATION",
        ),
        "PROHIBITED_PUBLIC_TERMS",
        "CONDITIONAL_ACCOUNT_LICENSE",
        "PROHIBITED_PUBLIC_TERMS",
        "UNPROVEN",
        "PRIVATE_LICENSE_REQUIRED",
        "CONDITIONAL_ACCOUNT_LICENSE",
        "CONDITIONAL_ACCOUNT_LICENSE",
        "PRIVATE_LICENSE_REQUIRED",
        "BLOCKED_ADDON_THIRD_PARTY_AND_PERSISTENCE_RIGHTS_UNPROVEN",
        (
            "The fundamentals surface can involve supplemental or third-party terms; no Fable5 "
            "account, add-on, plan, or written permission was reviewed, so every operational use "
            "right remains uncleared."
        ),
    ),
    (
        "TIINGO_DIVIDEND_CORPORATE_ACTIONS",
        "6ae798d2ae751ae61b1eff8af98c74ad99896f667d0c45e40827b4d874272356",
        (
            "TIINGO_TERMS_OF_USE",
            "TIINGO_GENERAL_API_DOCUMENTATION",
            "TIINGO_API_PRICING",
            "TIINGO_DIVIDEND_DOCUMENTATION",
        ),
        "PROHIBITED_PUBLIC_TERMS",
        "CONDITIONAL_ACCOUNT_LICENSE",
        "PROHIBITED_PUBLIC_TERMS",
        "UNPROVEN",
        "PRIVATE_LICENSE_REQUIRED",
        "CONDITIONAL_ACCOUNT_LICENSE",
        "CONDITIONAL_ACCOUNT_LICENSE",
        "UNPROVEN",
        "BLOCKED_ENTITLEMENT_CONFLICT_AND_PERSISTENCE_RIGHTS_UNPROVEN",
        (
            "Public internal-use language does not establish account-specific storage, "
            "derived-data, retention, or redistribution rights for dividend data."
        ),
    ),
    (
        "TIINGO_SPLIT_CORPORATE_ACTIONS",
        "17889785e819be747e861513b4abbf5b0618806f16fc88148edab2d2b8127953",
        (
            "TIINGO_TERMS_OF_USE",
            "TIINGO_GENERAL_API_DOCUMENTATION",
            "TIINGO_API_PRICING",
            "TIINGO_SPLIT_DOCUMENTATION",
        ),
        "PROHIBITED_PUBLIC_TERMS",
        "CONDITIONAL_ACCOUNT_LICENSE",
        "PROHIBITED_PUBLIC_TERMS",
        "UNPROVEN",
        "PRIVATE_LICENSE_REQUIRED",
        "CONDITIONAL_ACCOUNT_LICENSE",
        "CONDITIONAL_ACCOUNT_LICENSE",
        "UNPROVEN",
        "BLOCKED_ENTITLEMENT_CONFLICT_AND_PERSISTENCE_RIGHTS_UNPROVEN",
        (
            "Public internal-use language does not establish account-specific storage, "
            "derived-data, retention, or redistribution rights for split data."
        ),
    ),
    (
        "MORNINGSTAR_CRSP_US_STOCK_DATABASES",
        "8105f5bd41edf32701fdaa5c425d067ab0e37ff25d84f2c755971cf21e535fb0",
        (
            "MORNINGSTAR_WEBSITE_TERMS",
            "MORNINGSTAR_CRSP_DATA_ACCESS",
            "MORNINGSTAR_CRSP_US_STOCK_PRODUCT",
        ),
        "PRIVATE_LICENSE_REQUIRED",
        "PRIVATE_LICENSE_REQUIRED",
        "PRIVATE_LICENSE_REQUIRED",
        "UNPROVEN",
        "PRIVATE_LICENSE_REQUIRED",
        "UNPROVEN",
        "CONDITIONAL_ACCOUNT_LICENSE",
        "PRIVATE_LICENSE_REQUIRED",
        "BLOCKED_PRODUCT_LICENSE_RIGHTS_UNAVAILABLE",
        (
            "Morningstar describes CRSP research products as delivered to licensees, but no "
            "executed Fable5 license, subscriber entitlement, delivery variant, or revocation "
            "terms were reviewed."
        ),
    ),
    (
        "MORNINGSTAR_CRSP_COMPUSTAT_MERGED",
        "0867bcf338a5763d78a1c5acb77b58a829c65b4981bbdf78ccbb1af5ea16c190",
        (
            "MORNINGSTAR_WEBSITE_TERMS",
            "MORNINGSTAR_CRSP_DATA_ACCESS",
            "MORNINGSTAR_CCM_PRODUCT",
        ),
        "PRIVATE_LICENSE_REQUIRED",
        "PRIVATE_LICENSE_REQUIRED",
        "PRIVATE_LICENSE_REQUIRED",
        "UNPROVEN",
        "PRIVATE_LICENSE_REQUIRED",
        "UNPROVEN",
        "CONDITIONAL_ACCOUNT_LICENSE",
        "PRIVATE_LICENSE_REQUIRED",
        "BLOCKED_DUAL_PRODUCT_LICENSE_RIGHTS_UNAVAILABLE",
        (
            "The merged database depends on licensed CRSP and Compustat products; no executed "
            "Fable5 licenses, subscriber entitlements, delivery variant, or revocation terms "
            "were reviewed."
        ),
    ),
    (
        "SEC_EDGAR_SUBMISSIONS_AND_XBRL_DATA_APIS",
        "13fc0294503de17f2f5661d48b9c74d746cdf148ab8b1509d752770f64972459",
        (
            "SEC_PRIVACY_AND_DISSEMINATION",
            "SEC_WEBMASTER_REUSE_FAQ",
            "SEC_EDGAR_APIS",
            "SEC_DEVELOPER_RESOURCES",
            "SEC_ACCESSING_EDGAR",
        ),
        "ALLOWED_PUBLIC",
        "ALLOWED_PUBLIC",
        "ALLOWED_PUBLIC",
        "ALLOWED_PUBLIC",
        "ALLOWED_PUBLIC",
        "UNPROVEN",
        "ALLOWED_PUBLIC",
        "ALLOWED_PUBLIC",
        "RIGHTS_SUPPORTED_PUBLIC_POLICY_FITNESS_UNPROVEN",
        (
            "The SEC states that Government-created content and EDGAR public filing content are "
            "free to access and reuse, but this public guidance does not prove point-in-time "
            "fitness, exact content scope, current access compliance, or data-capture authority."
        ),
    ),
    (
        "FRED_REALTIME_AND_VINTAGE_WEB_SERVICE",
        "dce1fbcdf188230ce03862a61b723d7ed63ffab76dc851294c027902de50ffcc",
        (
            "FRED_TERMS",
            "FRED_API_OVERVIEW",
            "FRED_REALTIME_PERIODS",
            "FRED_SERIES_VINTAGE_DATES",
        ),
        "PROHIBITED_PUBLIC_TERMS",
        "PROHIBITED_PUBLIC_TERMS",
        "PROHIBITED_PUBLIC_TERMS",
        "PROHIBITED_PUBLIC_TERMS",
        "PROHIBITED_PUBLIC_TERMS",
        "CONDITIONAL_ACCOUNT_LICENSE",
        "CONDITIONAL_ACCOUNT_LICENSE",
        "UNPROVEN",
        "INELIGIBLE_CURRENT_TERMS_PROHIBIT_PERSISTENCE_AND_SOFTWARE_MODEL_USE",
        (
            "Current public FRED terms prohibit storing, caching, or archiving FRED content and "
            "incorporating it in a database or other medium, and prohibit using FRED services or "
            "API content for software or system development or training, including machine-"
            "learning use; third-party series restrictions and termination rights add "
            "independent blockers."
        ),
    ),
    (
        "LSEG_TICK_HISTORY_INSTRUMENT_AND_VENUE_WEB_API",
        "3f0ea8d981c3b445eff65ea7174acf35aeccde48d42b278494d08eb2f86986a1",
        (
            "LSEG_TICK_HISTORY",
            "LSEG_DATA_REDISTRIBUTION",
            "LSEG_WEBSITE_TERMS",
            "LSEG_NONDISPLAY_DERIVED_GUIDANCE",
        ),
        "PRIVATE_LICENSE_REQUIRED",
        "PRIVATE_LICENSE_REQUIRED",
        "PRIVATE_LICENSE_REQUIRED",
        "UNPROVEN",
        "PRIVATE_LICENSE_REQUIRED",
        "UNPROVEN",
        "CONDITIONAL_ACCOUNT_LICENSE",
        "PRIVATE_LICENSE_REQUIRED",
        "BLOCKED_PRODUCT_VENUE_AND_NONDISPLAY_RIGHTS_UNAVAILABLE",
        (
            "The product page describes Tick History capabilities but grants no product-data "
            "license; the website terms allow only narrow personal, non-professional website use, "
            "and no Fable5 product contract was reviewed."
        ),
    ),
)

_TIINGO_PRODUCTS: Final = tuple(row[0] for row in PHASE18_PRODUCT_ROWS[:4])
_MORNINGSTAR_PRODUCTS: Final = tuple(row[0] for row in PHASE18_PRODUCT_ROWS[4:6])

PHASE18_SOURCE_ROWS: Final = (
    (
        "TIINGO_TERMS_OF_USE",
        "Tiingo™ Terms of Use",
        "Tiingo Inc.",
        "https://app.tiingo.com/tos/",
        _TIINGO_PRODUCTS,
        "2026-02-18",
        "Introductory change notice; §§1,1.4,5.3,7.3",
        (
            "Standard terms limit use to personal or internal consumption, prohibit derivative "
            "works and systematic retrieval to build a database, and require separate permission "
            "and fees for redistribution; supplemental terms may control."
        ),
        PHASE18_FROZEN_AT_UTC,
    ),
    (
        "TIINGO_GENERAL_API_DOCUMENTATION",
        "Stock Market Tools | Tiingo",
        "Tiingo Inc.",
        "https://www.tiingo.com/documentation/general",
        _TIINGO_PRODUCTS,
        "UNSTATED",
        "§§1.1.2,1.1.3,1.1.4,1.1.6",
        (
            "Documents token-based API use and plan or licensing distinctions; it is technical "
            "public guidance, not Fable5 entitlement or persistent-use authority."
        ),
        PHASE18_FROZEN_AT_UTC,
    ),
    (
        "TIINGO_API_PRICING",
        "Tiingo API Pricing | Tiingo",
        "Tiingo Inc.",
        "https://www.tiingo.com/about/pricing",
        _TIINGO_PRODUCTS,
        "UNSTATED",
        "Plans, commercial use, redistribution",
        (
            "Public plans describe access tiers and separate redistribution licensing but prove "
            "no current Fable5 plan or entitlement."
        ),
        PHASE18_FROZEN_AT_UTC,
    ),
    (
        "TIINGO_EOD_DOCUMENTATION",
        "End-of-Day (EOD) Stock Price API Documentation | Tiingo",
        "Tiingo Inc.",
        "https://www.tiingo.com/documentation/end-of-day",
        ("TIINGO_END_OF_DAY",),
        "UNSTATED",
        "EOD product overview and authentication/request documentation",
        (
            "Identifies the EOD product and API surface; it does not grant persistent storage, "
            "derived, retention, redistribution, or Fable5 account rights."
        ),
        PHASE18_FROZEN_AT_UTC,
    ),
    (
        "TIINGO_FUNDAMENTALS_DOCUMENTATION",
        "U.S. Fundamental Data API Documentation | Tiingo",
        "Tiingo Inc.",
        "https://www.tiingo.com/documentation/fundamentals",
        ("TIINGO_US_FUNDAMENTALS",),
        "UNSTATED",
        "Overview, access/add-on, third-party provider disclosure",
        (
            "Describes an add-on coordinated with an unnamed third-party provider; documentation "
            "and a DOW30 evaluation do not establish entitlement or use rights."
        ),
        PHASE18_FROZEN_AT_UTC,
    ),
    (
        "TIINGO_DIVIDEND_DOCUMENTATION",
        "Stock, ETF, and Mutual Fund Dividend API Documentation | Tiingo",
        "Tiingo Inc.",
        "https://www.tiingo.com/documentation/corporate-actions/dividends",
        ("TIINGO_DIVIDEND_CORPORATE_ACTIONS",),
        "UNSTATED",
        "Overview, beta/early-release and EOD-entitlement statements",
        (
            "Documents the dividend surface but contains ambiguous entitlement language; it does "
            "not prove a current Fable5 entitlement or persistence rights."
        ),
        PHASE18_FROZEN_AT_UTC,
    ),
    (
        "TIINGO_SPLIT_DOCUMENTATION",
        "Stock, ETF, and Mutual Fund Split API Documentation | Tiingo",
        "Tiingo Inc.",
        "https://www.tiingo.com/documentation/corporate-actions/splits",
        ("TIINGO_SPLIT_CORPORATE_ACTIONS",),
        "UNSTATED",
        "Overview, beta/early-release and EOD-entitlement statements",
        (
            "Documents the split surface but contains ambiguous entitlement language; it does not "
            "prove a current Fable5 entitlement or persistence rights."
        ),
        PHASE18_FROZEN_AT_UTC,
    ),
    (
        "MORNINGSTAR_WEBSITE_TERMS",
        "Legal Notices | Morningstar (H1 Terms and Conditions)",
        "Morningstar",
        "https://www.morningstar.com/company/terms-and-conditions",
        _MORNINGSTAR_PRODUCTS,
        "UNSTATED",
        "Website license/use and third-party content provisions",
        (
            "General website terms are not a product-data license and do not establish Fable5 "
            "research-product rights."
        ),
        PHASE18_FROZEN_AT_UTC,
    ),
    (
        "MORNINGSTAR_CRSP_DATA_ACCESS",
        "Research Data Products | Morningstar Indexes",
        "Morningstar",
        "https://indexes.morningstar.com/research-data-products",
        _MORNINGSTAR_PRODUCTS,
        "UNSTATED",
        "Research Data Products; Data Access Options",
        (
            "Documents licensee delivery options including flat files, command-line tools, "
            "libraries, Snowflake, WRDS, MOVEit, and CHASS; exact Fable5 delivery and entitlement "
            "remain unproven."
        ),
        PHASE18_FROZEN_AT_UTC,
    ),
    (
        "MORNINGSTAR_CRSP_US_STOCK_PRODUCT",
        "CRSP US Stock Databases | Morningstar Indexes",
        "Morningstar",
        "https://indexes.morningstar.com/research-data-products/crsp-us-stock-databases",
        ("MORNINGSTAR_CRSP_US_STOCK_DATABASES",),
        "UNSTATED",
        "Product overview, coverage, identifiers, subscription access",
        (
            "Identifies a licensed product with active and inactive securities and PERMNO or "
            "PERMCO, but no public product-specific grant covers storage, non-display, derived, "
            "retention, redistribution, delivery, or Fable5 entitlement."
        ),
        PHASE18_FROZEN_AT_UTC,
    ),
    (
        "MORNINGSTAR_CCM_PRODUCT",
        "CRSP/Compustat Merged Database | Morningstar Indexes",
        "Morningstar",
        "https://indexes.morningstar.com/research-data-products/crsp-compustat-merged-database",
        ("MORNINGSTAR_CRSP_COMPUSTAT_MERGED",),
        "UNSTATED",
        "Product overview; subscription requirements",
        (
            "The merged database expressly requires both a CRSP US Stock subscription and a "
            "separate Compustat Xpressfeed license; neither Fable5 license nor rights scope was "
            "reviewed."
        ),
        PHASE18_FROZEN_AT_UTC,
    ),
    (
        "SEC_PRIVACY_AND_DISSEMINATION",
        "SEC.gov | Privacy Information",
        "U.S. Securities and Exchange Commission",
        "https://www.sec.gov/about/privacy-information",
        ("SEC_EDGAR_SUBMISSIONS_AND_XBRL_DATA_APIS",),
        "2023-11-29",
        "Website Dissemination",
        (
            "SEC-created website information is public and may be copied or further distributed "
            "without permission; reuse should cite the SEC and must not use seals or logos or "
            "imply affiliation."
        ),
        PHASE18_FROZEN_AT_UTC,
    ),
    (
        "SEC_WEBMASTER_REUSE_FAQ",
        "SEC.gov | Webmaster Frequently Asked Questions",
        "U.S. Securities and Exchange Commission",
        "https://www.sec.gov/about/webmaster-frequently-asked-questions",
        ("SEC_EDGAR_SUBMISSIONS_AND_XBRL_DATA_APIS",),
        "2024-08-23",
        "Is content on sec.gov free? Do I need permission to reuse EDGAR content?",
        (
            "Government-created sec.gov content and EDGAR public-filing content are free to access "
            "and reuse; this does not establish dataset fitness."
        ),
        PHASE18_FROZEN_AT_UTC,
    ),
    (
        "SEC_EDGAR_APIS",
        "SEC.gov | EDGAR Application Programming Interfaces (APIs)",
        "U.S. Securities and Exchange Commission",
        "https://www.sec.gov/search-filings/edgar-application-programming-interfaces",
        ("SEC_EDGAR_SUBMISSIONS_AND_XBRL_DATA_APIS",),
        "2025-04-08",
        "Submissions API, Companyfacts API, bulk ZIP archives",
        (
            "Documents unauthenticated JSON APIs and nightly bulk archives; no key is required, "
            "but technical access is not operational selection or point-in-time-fitness proof."
        ),
        PHASE18_FROZEN_AT_UTC,
    ),
    (
        "SEC_DEVELOPER_RESOURCES",
        "SEC.gov | Developer Resources",
        "U.S. Securities and Exchange Commission",
        "https://www.sec.gov/about/developer-resources",
        ("SEC_EDGAR_SUBMISSIONS_AND_XBRL_DATA_APIS",),
        "2025-03-10",
        "Fair-access/security policy and request-rate guidance",
        (
            "Documents current security and fair-access expectations, including an aggregate "
            "request rate at or below ten requests per second; policy must be revalidated before "
            "any later external request."
        ),
        PHASE18_FROZEN_AT_UTC,
    ),
    (
        "SEC_ACCESSING_EDGAR",
        "SEC.gov | Accessing EDGAR Data",
        "U.S. Securities and Exchange Commission",
        "https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data",
        ("SEC_EDGAR_SUBMISSIONS_AND_XBRL_DATA_APIS",),
        "2024-06-26",
        "Automated access, client identification, and bulk data guidance",
        (
            "Automated clients must declare a descriptive User-Agent and company contact, make "
            "efficient requests, download only needed content, and follow the current fair-access "
            "policy."
        ),
        PHASE18_FROZEN_AT_UTC,
    ),
    (
        "FRED_TERMS",
        "Legal Notices, Information and Disclaimers | FRED | St. Louis Fed",
        "Federal Reserve Bank of St. Louis",
        "https://fred.stlouisfed.org/legal/terms/",
        ("FRED_REALTIME_AND_VINTAGE_WEB_SERVICE",),
        "UNSTATED",
        (
            "Property Rights and Licenses; general prohibitions (p)-(r); Additional API Terms "
            "prohibitions (k)-(m); Term and Termination"
        ),
        (
            "Current terms prohibit API storage, caching, archiving, database incorporation, and "
            "derivative works, and prohibit using FRED services or API content for software or "
            "system development or training, including machine-learning use; they require "
            "destruction on termination, preserve third-party-series owner rights, and allow "
            "changes or termination."
        ),
        PHASE18_FROZEN_AT_UTC,
    ),
    (
        "FRED_API_OVERVIEW",
        "St. Louis Fed Web Services: FRED® API Overview",
        "Federal Reserve Bank of St. Louis",
        "https://fred.stlouisfed.org/docs/api/fred/overview.html",
        ("FRED_REALTIME_AND_VINTAGE_WEB_SERVICE",),
        "UNSTATED",
        "Overview and API-key requirement",
        (
            "Documents FRED web services and a registered API-key requirement; technical "
            "availability does not override legal restrictions."
        ),
        PHASE18_FROZEN_AT_UTC,
    ),
    (
        "FRED_REALTIME_PERIODS",
        "St. Louis Fed Web Services: FRED® API Real-Time Periods",
        "Federal Reserve Bank of St. Louis",
        "https://fred.stlouisfed.org/docs/api/fred/realtime_period.html",
        ("FRED_REALTIME_AND_VINTAGE_WEB_SERVICE",),
        "UNSTATED",
        "Real-time start/end and vintage semantics",
        (
            "Documents real-time period semantics; it does not grant persistence or "
            "third-party-series rights."
        ),
        PHASE18_FROZEN_AT_UTC,
    ),
    (
        "FRED_SERIES_VINTAGE_DATES",
        "St. Louis Fed Web Services: fred/series/vintagedates",
        "Federal Reserve Bank of St. Louis",
        "https://fred.stlouisfed.org/docs/api/fred/series_vintagedates.html",
        ("FRED_REALTIME_AND_VINTAGE_WEB_SERVICE",),
        "UNSTATED",
        "Endpoint parameters and vintage-date response",
        (
            "Documents vintage-date retrieval; it does not authorize an immutable canonical "
            "snapshot."
        ),
        PHASE18_FROZEN_AT_UTC,
    ),
    (
        "LSEG_TICK_HISTORY",
        "Tick History Data | Data Analytics",
        "LSEG",
        "https://www.lseg.com/en/data-analytics/market-data/data-feeds/tick-history",
        ("LSEG_TICK_HISTORY_INSTRUMENT_AND_VENUE_WEB_API",),
        "UNSTATED",
        "Overview; Instrument & Venue; Web/API delivery; FAQs",
        (
            "Documents technical Tick History Web or API delivery and capabilities, but exact "
            "product, venue or contributor, field, delivery, entitlement, and use rights require "
            "a product license."
        ),
        PHASE18_FROZEN_AT_UTC,
    ),
    (
        "LSEG_DATA_REDISTRIBUTION",
        "Data Redistribution Solutions for Market Data | Data Analytics",
        "LSEG",
        "https://www.lseg.com/en/data-analytics/market-data/data-redistribution",
        ("LSEG_TICK_HISTORY_INSTRUMENT_AND_VENUE_WEB_API",),
        "UNSTATED",
        "Redistribution and derived-data licensing",
        (
            "Public material says derived and redistribution uses operate inside licensing "
            "frameworks; it grants no Fable5 right."
        ),
        PHASE18_FROZEN_AT_UTC,
    ),
    (
        "LSEG_WEBSITE_TERMS",
        "Website Terms of Use | LSEG",
        "London Stock Exchange Group plc",
        "https://www.lseg.com/en/policies/website-terms-of-use",
        ("LSEG_TICK_HISTORY_INSTRUMENT_AND_VENUE_WEB_API",),
        "UNSTATED",
        (
            "Website information license, personal or non-professional use, intellectual-property "
            "and changes provisions"
        ),
        (
            "General website terms permit only narrow personal or non-professional temporary use "
            "and are not a Tick History product license."
        ),
        PHASE18_FROZEN_AT_UTC,
    ),
    (
        "LSEG_NONDISPLAY_DERIVED_GUIDANCE",
        "How to optimise financial data for AI",
        "LSEG Academy",
        (
            "https://www.lseg.com/content/dam/lseg/learning-centre/documents/"
            "how-to-optimise-financial-data-for-ai-presentation-slides.pdf"
        ),
        ("LSEG_TICK_HISTORY_INSTRUMENT_AND_VENUE_WEB_API",),
        "UNSTATED",
        "Non-display, derived-data, redistribution/application-use licensing slides",
        (
            "Official educational material warns non-display, derived, and application uses may "
            "require additional licensing; executed contracts control and none was reviewed."
        ),
        PHASE18_FROZEN_AT_UTC,
    ),
)
PHASE18_STEP_CODES: Final = (
    "SELECT_CANDIDATE_PRODUCTS",
    "REVIEW_CURRENT_USE_RIGHTS",
    "QUALIFY_BOUNDED_READ_ONLY_SAMPLES",
    "PRODUCE_FULL_HISTORY_COVERAGE_MANIFEST",
    "RECONCILE_TEMPORAL_IDENTITY_REVISION_SEMANTICS",
    "DESIGN_LOCAL_QUARANTINE_AND_CANONICAL_SNAPSHOT",
    "REQUEST_SEPARATE_INGESTION_AUTHORITY",
)
PHASE18_STEP_STATES: Final = (
    "OUTPUT_FROZEN",
    "OUTPUT_FROZEN",
    "NOT_STARTED",
    "NOT_STARTED",
    "NOT_STARTED",
    "NOT_STARTED",
    "NOT_STARTED",
)
PHASE18_STEP_REASONS: Final = (
    "inventory_output_inherited_and_frozen",
    "blocking_rights_review_outputs_frozen_no_operational_clearance",
    "prerequisite_not_satisfied",
    "prerequisite_not_satisfied",
    "prerequisite_not_satisfied",
    "prerequisite_not_satisfied",
    "prerequisite_not_satisfied",
)
PHASE18_STEP_PREREQUISITES: Final = (
    (),
    ("SELECT_CANDIDATE_PRODUCTS",),
    ("SELECT_CANDIDATE_PRODUCTS", "REVIEW_CURRENT_USE_RIGHTS"),
    ("QUALIFY_BOUNDED_READ_ONLY_SAMPLES",),
    ("PRODUCE_FULL_HISTORY_COVERAGE_MANIFEST",),
    ("REVIEW_CURRENT_USE_RIGHTS", "RECONCILE_TEMPORAL_IDENTITY_REVISION_SEMANTICS"),
    ("DESIGN_LOCAL_QUARANTINE_AND_CANONICAL_SNAPSHOT",),
)
PHASE18_STEP_REQUIRED_PRIOR_EVIDENCE: Final = (
    (),
    (),
    ("non_synthetic_evaluation_policy_sha256", "confirmation_holdout_definition_sha256"),
    (),
    (),
    (),
    (),
)
PHASE18_STEP_REQUIRED_OUTPUTS: Final = (
    ("candidate_product_inventory_sha256",),
    ("independent_rights_review_sha256", "rights_currentness_sha256"),
    ("qualification_artifact_set_sha256",),
    ("full_history_coverage_manifest_sha256",),
    ("temporal_identity_revision_reconciliation_sha256",),
    ("quarantine_canonical_snapshot_design_sha256",),
    ("separate_ingestion_authority_evidence_sha256",),
)

PHASE18_BOUNDARY_VALUES: Final = MappingProxyType(
    {
        "metadata_only": True,
        "official_public_terms_review_performed": True,
        "official_public_documentation_access_performed": True,
        "independent_technical_rights_review_performed": True,
        "official_citations_inert": True,
        "review_snapshot_only": True,
        "runtime_network_disabled": True,
        "revalidation_required_before_external_action": True,
        "legal_opinion_obtained": False,
        "independent_legal_counsel_reviewed": False,
        "provider_or_counsel_attestation_obtained": False,
        "executed_license_reviewed": False,
        "account_specific_terms_reviewed": False,
        "terms_body_persisted": False,
        "external_document_persisted": False,
        "rights_currentness_guaranteed": False,
        "operational_use_cleared": False,
        "storage_rights_cleared": False,
        "non_display_rights_cleared": False,
        "derived_data_rights_cleared": False,
        "retention_rights_cleared": False,
        "redistribution_rights_cleared": False,
        "delivery_rights_cleared": False,
        "entitlement_rights_cleared": False,
        "revocation_status_verified": False,
        "operational_external_request_performed": False,
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

PHASE18_BLOCK_REASON: Final = (
    "Public terms do not establish Fable5 account-specific rights for Tiingo, Morningstar/CRSP, "
    "or LSEG; current FRED terms prohibit the persistence and software or model use required by "
    "the planned research path; and SEC public reuse guidance does not itself prove operational "
    "access, content scope, point-in-time fitness, or any later-step authority."
)
PHASE18_DISCLAIMER: Final = (
    "Technical public-terms review snapshot only, not legal advice or a current rights grant; "
    "every source requires revalidation before any separately authorized external action, and "
    "this artifact grants no provider, data, ingestion, research, risk, execution, or order "
    "authority."
)

PHASE18_POLICY_SHA256: Final = domain_sha256(
    PHASE18_POLICY_HASH_DOMAIN,
    {
        "policy_id": PHASE18_POLICY_ID,
        "artifact_uuid_namespace": str(PHASE18_ARTIFACT_NAMESPACE),
        "schemas_and_hash_domains": (
            (PHASE18_ARTIFACT_SCHEMA_VERSION, PHASE18_ARTIFACT_HASH_DOMAIN),
            (PHASE18_SOURCE_SCHEMA_VERSION, PHASE18_SOURCE_HASH_DOMAIN),
            (PHASE18_FINDING_SCHEMA_VERSION, PHASE18_FINDING_HASH_DOMAIN),
            (PHASE18_STEP_SCHEMA_VERSION, PHASE18_STEP_HASH_DOMAIN),
            (PHASE18_OUTPUT_SCHEMA_VERSION, PHASE18_OUTPUT_HASH_DOMAIN),
            PHASE18_SOURCES_MANIFEST_HASH_DOMAIN,
            PHASE18_REVIEW_MANIFEST_HASH_DOMAIN,
            PHASE18_CURRENTNESS_HASH_DOMAIN,
            PHASE18_STEPS_MANIFEST_HASH_DOMAIN,
        ),
        "accepted_phase17_commit_sha": PHASE18_ACCEPTED_PHASE17_COMMIT_SHA,
        "accepted_phase17_tree_sha": PHASE18_ACCEPTED_PHASE17_TREE_SHA,
        "phase17_identities": (
            PHASE18_PHASE17_ARTIFACT_ID,
            PHASE18_PHASE17_ARTIFACT_SHA256,
            PHASE18_PHASE17_POLICY_SHA256,
            PHASE18_PHASE17_INVENTORY_SHA256,
            PHASE18_PHASE17_CANDIDATE_GROUPS_MANIFEST_SHA256,
            PHASE18_PHASE17_STEPS_MANIFEST_SHA256,
        ),
        "phase16_step2_sha256": PHASE18_PHASE16_STEP2_SHA256,
        "family": PHASE18_FAMILY,
        "frozen_at_utc": PHASE18_FROZEN_AT_UTC,
        "outcome": "BLOCKED",
        "aggregate_conclusion": PHASE18_AGGREGATE_CONCLUSION,
        "product_rights_rows": PHASE18_PRODUCT_ROWS,
        "rights_status_vocabulary": PHASE18_RIGHTS_STATUS_VALUES,
        "terms_source_rows": PHASE18_SOURCE_ROWS,
        "finding_invariants": (
            ("public_metadata_review_only", True),
            ("operational_use_cleared", False),
            ("entitlement_verified", False),
            ("executed_license_reviewed", False),
            ("legal_opinion_obtained", False),
            ("revalidation_required", True),
        ),
        "source_invariants": (
            ("official_https_citation", True),
            ("terms_body_persisted", False),
            ("source_content_bytes_captured", False),
            ("content_byte_authenticity_proven", False),
            ("account_specific", False),
            ("revalidation_required", True),
        ),
        "steps": tuple(
            zip(
                PHASE18_STEP_CODES,
                PHASE18_STEP_STATES,
                PHASE18_STEP_REASONS,
                PHASE18_STEP_PREREQUISITES,
                PHASE18_STEP_REQUIRED_PRIOR_EVIDENCE,
                PHASE18_STEP_REQUIRED_OUTPUTS,
                strict=True,
            )
        ),
        "boundary_values": PHASE18_BOUNDARY_VALUES,
        "block_reason": PHASE18_BLOCK_REASON,
        "disclaimer": PHASE18_DISCLAIMER,
    },
)


def identity(sha256: str) -> UUID:
    return uuid_from_sha256(PHASE18_ARTIFACT_NAMESPACE, sha256)


__all__ = [name for name in globals() if name.startswith("PHASE18_")] + [
    "canonical_json_bytes",
    "canonicalize",
    "domain_sha256",
    "identity",
]
