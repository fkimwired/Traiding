"""Frozen identities for the Phase 28 observation-only pilot."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Final, NamedTuple
from uuid import UUID

from fable5_data.canonical import canonical_json_bytes as canonical_json_bytes
from fable5_data.canonical import domain_sha256 as domain_sha256
from fable5_data.canonical import uuid_from_sha256

PHASE28_UNIVERSE: Final = ("AAPL", "MSFT", "SPY")
PHASE28_FEED: Final = "iex"
PHASE28_CURRENCY: Final = "USD"
PHASE28_PAPER_HOST: Final = "paper-api.alpaca.markets"
PHASE28_DATA_HOST: Final = "data.alpaca.markets"
PHASE28_FRESHNESS_TTL_SECONDS: Final = 120
PHASE28_BAR_SNAPSHOT_ROLLOVER_TOLERANCE_SECONDS: Final = 60
PHASE28_QUOTE_SNAPSHOT_TOLERANCE_SECONDS: Final = 30


class FixedEndpoint(NamedTuple):
    ordinal: int
    code: str
    method: str
    host: str
    port: int
    target: str


class FixedPredicate(NamedTuple):
    ordinal: int
    code: str
    definition: str


PHASE28_FIXED_ENDPOINTS: Final = (
    FixedEndpoint(1, "ASSET_AAPL", "GET", PHASE28_PAPER_HOST, 443, "/v2/assets/AAPL"),
    FixedEndpoint(2, "ASSET_MSFT", "GET", PHASE28_PAPER_HOST, 443, "/v2/assets/MSFT"),
    FixedEndpoint(3, "ASSET_SPY", "GET", PHASE28_PAPER_HOST, 443, "/v2/assets/SPY"),
    FixedEndpoint(
        4,
        "LATEST_BARS",
        "GET",
        PHASE28_DATA_HOST,
        443,
        "/v2/stocks/bars/latest?symbols=AAPL%2CMSFT%2CSPY&feed=iex&currency=USD",
    ),
    FixedEndpoint(
        5,
        "LATEST_QUOTES",
        "GET",
        PHASE28_DATA_HOST,
        443,
        "/v2/stocks/quotes/latest?symbols=AAPL%2CMSFT%2CSPY&feed=iex&currency=USD",
    ),
    FixedEndpoint(
        6,
        "SNAPSHOTS",
        "GET",
        PHASE28_DATA_HOST,
        443,
        "/v2/stocks/snapshots?symbols=AAPL%2CMSFT%2CSPY&feed=iex&currency=USD",
    ),
)

PHASE28_SIGNAL_DEFINITIONS: Final = (
    FixedPredicate(1, "ASSET_ACTIVE", "asset status is exactly active"),
    FixedPredicate(2, "ASSET_TRADABLE", "asset reports tradable true"),
    FixedPredicate(
        3,
        "LATEST_BAR_VALID_AND_FRESH",
        "latest IEX bar is valid and its age is within 120 seconds",
    ),
    FixedPredicate(
        4,
        "LATEST_QUOTE_VALID_AND_FRESH",
        "latest IEX quote is fresh, positive, and non-crossed",
    ),
    FixedPredicate(
        5,
        "SNAPSHOT_COMPLETE_AND_FRESH",
        "snapshot has a trade, quote, minute, daily, and prior daily bar and is fresh",
    ),
    FixedPredicate(
        6,
        "CROSS_ENDPOINT_COHERENT",
        "bar-to-minute-bar agrees within 60 seconds and quote-to-quote within 30 seconds",
    ),
    FixedPredicate(
        7,
        "SESSION_DIRECTION_POSITIVE",
        "snapshot daily close is greater than prior daily close",
    ),
    FixedPredicate(
        8,
        "INTRADAY_DIRECTION_POSITIVE",
        "snapshot minute close is greater than daily open",
    ),
)

PHASE28_UNIVERSE_SHA256: Final = domain_sha256(
    "phase28-alpaca-iex-universe-v1", {"symbols": PHASE28_UNIVERSE}
)
PHASE28_SIGNAL_REGISTRY_SHA256: Final = domain_sha256(
    "phase28-alpaca-iex-signal-registry-v1",
    {"signals": PHASE28_SIGNAL_DEFINITIONS},
)
PHASE28_TRANSPORT_PROFILE_SHA256: Final = domain_sha256(
    "phase28-alpaca-iex-transport-profile-v1",
    {
        "endpoints": PHASE28_FIXED_ENDPOINTS,
        "redirects": False,
        "proxies": False,
        "retry_count": 0,
    },
)
PHASE28_EXACT_USE_REVIEW_EXPIRES_AT_UTC: Final = datetime(2026, 8, 1, 0, 0, tzinfo=UTC)
PHASE28_EXACT_USE_REVIEW_SOURCE_URLS: Final = (
    "https://files.alpaca.markets/disclosures/library/TermsAndConditions.pdf",
    "https://files.alpaca.markets/disclosures/library/AcctAppMarginAndCustAgmt.pdf",
    "https://alpaca.markets/support/redistribute-alpaca-api",
    "https://docs.alpaca.markets/us/docs/market-data-faq",
)
PHASE28_EXACT_USE_REVIEW_SHA256: Final = domain_sha256(
    "phase28-alpaca-exact-use-technical-review-v1",
    {
        "reviewed_on": "2026-07-24",
        "revalidation_deadline_utc": PHASE28_EXACT_USE_REVIEW_EXPIRES_AT_UTC,
        "permitted_use": (
            "personal",
            "noncommercial",
            "transient_in_process_observation",
            "sanitized_derived_classification_only",
        ),
        "prohibited_use": (
            "raw_persistence",
            "display",
            "redistribution",
            "research_dataset",
            "commercial_or_public_application",
            "execution_authority",
        ),
        "source_urls": PHASE28_EXACT_USE_REVIEW_SOURCE_URLS,
    },
)
PHASE28_CONFIG_SHA256: Final = domain_sha256(
    "phase28-alpaca-iex-config-v1",
    {
        "universe_sha256": PHASE28_UNIVERSE_SHA256,
        "signal_registry_sha256": PHASE28_SIGNAL_REGISTRY_SHA256,
        "transport_profile_sha256": PHASE28_TRANSPORT_PROFILE_SHA256,
        "feed": PHASE28_FEED,
        "currency": PHASE28_CURRENCY,
        "freshness_ttl_seconds": PHASE28_FRESHNESS_TTL_SECONDS,
        "bar_snapshot_rollover_tolerance_seconds": (
            PHASE28_BAR_SNAPSHOT_ROLLOVER_TOLERANCE_SECONDS
        ),
        "quote_snapshot_tolerance_seconds": (PHASE28_QUOTE_SNAPSHOT_TOLERANCE_SECONDS),
        "exact_use_review_sha256": PHASE28_EXACT_USE_REVIEW_SHA256,
        "exact_use_review_revalidation_deadline_utc": (PHASE28_EXACT_USE_REVIEW_EXPIRES_AT_UTC),
    },
)
PHASE28_EVIDENCE_NAMESPACE: Final = UUID("c723ffbd-5d4d-50e4-87fa-ee2d88367b3b")
PHASE28_OBSERVATION_SNAPSHOT_NAMESPACE: Final = UUID("56d518de-06b2-59cc-ae09-89f66883e9b3")
PHASE28_NOTICE: Final = (
    "IEX is a partial-market feed and does not represent the consolidated U.S. market. "
    "This observation is for paper-only testing. It is not research-qualified, not a trade "
    "signal, and not investment advice."
)


def raw_response_sha256(payload: bytes) -> str:
    """Hash a transient body without retaining it."""

    return hashlib.sha256(payload).hexdigest()


def evidence_id(evidence_sha256: str) -> UUID:
    """Derive the stable opaque evidence identifier."""

    return uuid_from_sha256(PHASE28_EVIDENCE_NAMESPACE, evidence_sha256)


def observation_snapshot_id(snapshot_sha256: str) -> UUID:
    """Derive an opaque identifier for sanitized observation metadata."""

    return uuid_from_sha256(PHASE28_OBSERVATION_SNAPSHOT_NAMESPACE, snapshot_sha256)


__all__ = [name for name in globals() if name.startswith("PHASE28_")] + [
    "canonical_json_bytes",
    "domain_sha256",
    "evidence_id",
    "observation_snapshot_id",
    "raw_response_sha256",
]
