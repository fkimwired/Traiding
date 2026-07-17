"""Canonical identities and the frozen Phase 12 read-only transport profile."""

from __future__ import annotations

import hashlib
from typing import Final
from uuid import UUID

from fable5_data.canonical import canonical_json_bytes as canonical_json_bytes
from fable5_data.canonical import canonicalize as canonicalize
from fable5_data.canonical import domain_sha256 as domain_sha256
from fable5_data.canonical import uuid_from_sha256

PHASE12_TRANSPORT_PROFILE_HASH_DOMAIN: Final = "phase12-paper-shadow-transport-profile-v1"
PHASE12_OBSERVATION_HASH_DOMAIN: Final = "phase12-paper-shadow-observation-v1"
PHASE12_INSPECTION_HASH_DOMAIN: Final = "phase12-paper-shadow-inspection-v1"
PHASE12_CHECK_HASH_DOMAIN: Final = "phase12-paper-shadow-check-v1"
PHASE12_REQUEST_HASH_DOMAIN: Final = "phase12-paper-shadow-request-v1"
PHASE12_ARTIFACT_HASH_DOMAIN: Final = "phase12-paper-shadow-artifact-v1"

PHASE12_RUN_NAMESPACE = UUID("f1195f7e-e891-5c21-9d3b-a0ced8881212")

ALPACA_PAPER_TRADING_HOST: Final = "paper-api.alpaca.markets"
ALPACA_MARKET_DATA_HOST: Final = "data.alpaca.markets"

PHASE12_FIXED_ENDPOINTS: Final = (
    {
        "ordinal": 1,
        "code": "ACCOUNT",
        "method": "GET",
        "host": ALPACA_PAPER_TRADING_HOST,
        "port": 443,
        "target": "/v2/account",
    },
    {
        "ordinal": 2,
        "code": "CLOCK",
        "method": "GET",
        "host": ALPACA_PAPER_TRADING_HOST,
        "port": 443,
        "target": "/v2/clock",
    },
    {
        "ordinal": 3,
        "code": "INSTRUMENT",
        "method": "GET",
        "host": ALPACA_PAPER_TRADING_HOST,
        "port": 443,
        "target": "/v2/assets/AAPL",
    },
    {
        "ordinal": 4,
        "code": "POSITIONS",
        "method": "GET",
        "host": ALPACA_PAPER_TRADING_HOST,
        "port": 443,
        "target": "/v2/positions",
    },
    {
        "ordinal": 5,
        "code": "OPEN_ORDERS",
        "method": "GET",
        "host": ALPACA_PAPER_TRADING_HOST,
        "port": 443,
        "target": "/v2/orders?status=open&limit=500&direction=asc",
    },
    {
        "ordinal": 6,
        "code": "LATEST_QUOTE",
        "method": "GET",
        "host": ALPACA_MARKET_DATA_HOST,
        "port": 443,
        "target": "/v2/stocks/AAPL/quotes/latest?feed=iex&currency=USD",
    },
)

PHASE12_TRANSPORT_PROFILE_SHA256: Final = domain_sha256(
    PHASE12_TRANSPORT_PROFILE_HASH_DOMAIN,
    {"endpoints": PHASE12_FIXED_ENDPOINTS, "redirects": False, "proxies": False},
)


def identity(namespace: UUID, sha256: str) -> UUID:
    """Derive one stable UUID from a validated lowercase SHA-256 value."""

    return uuid_from_sha256(namespace, sha256)


def raw_response_sha256(payload: bytes) -> str:
    """Hash a transient response without retaining its potentially sensitive body."""

    return hashlib.sha256(payload).hexdigest()


__all__ = [name for name in globals() if name.startswith(("PHASE12_", "ALPACA_"))] + [
    "canonical_json_bytes",
    "canonicalize",
    "domain_sha256",
    "identity",
    "raw_response_sha256",
]
