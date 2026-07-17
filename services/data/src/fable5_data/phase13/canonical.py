"""Canonical identities and the frozen Phase 13 qualification transport profile."""

from __future__ import annotations

import hashlib
from typing import Final
from uuid import UUID

from fable5_data.canonical import canonical_json_bytes as canonical_json_bytes
from fable5_data.canonical import canonicalize as canonicalize
from fable5_data.canonical import domain_sha256 as domain_sha256
from fable5_data.canonical import uuid_from_sha256

PHASE13_REQUEST_HASH_DOMAIN: Final = "phase13-pit-qualification-request-v1"
PHASE13_REQUEST_EVIDENCE_HASH_DOMAIN: Final = "phase13-pit-request-evidence-v1"
PHASE13_CAPABILITY_HASH_DOMAIN: Final = "phase13-pit-capability-manifest-v1"
PHASE13_CHECK_HASH_DOMAIN: Final = "phase13-pit-qualification-check-v1"
PHASE13_CAPTURE_MANIFEST_HASH_DOMAIN: Final = "phase13-pit-capture-manifest-v1"
PHASE13_ARTIFACT_HASH_DOMAIN: Final = "phase13-pit-qualification-artifact-v1"
PHASE13_TRANSPORT_PROFILE_HASH_DOMAIN: Final = "phase13-tiingo-transport-profile-v1"
PHASE13_SAMPLE_PLAN_HASH_DOMAIN: Final = "phase13-family-a-sample-plan-v1"
PHASE13_SCHEMA_IDENTITY_HASH_DOMAIN: Final = "phase13-observed-schema-identity-v1"
PHASE13_NORMALIZED_EVIDENCE_HASH_DOMAIN: Final = "phase13-normalized-evidence-v1"

PHASE13_RUN_NAMESPACE: Final = UUID("298dd99c-ab11-5c8b-98aa-866ebbb91313")

TIINGO_QUALIFICATION_HOST: Final = "api.tiingo.com"
TIINGO_QUALIFICATION_PORT: Final = 443

PHASE13_CAPABILITY_VALUES: Final = (
    "SECURITY_MASTER_STABLE_IDENTITY",
    "POINT_IN_TIME_UNIVERSE_MEMBERSHIP",
    "RAW_OHLCV_AVAILABILITY",
    "CORPORATE_ACTION_ANNOUNCEMENT_REVISION",
    "DELISTING_RETURN_SEMANTICS",
    "AS_REPORTED_FUNDAMENTAL_REVISION",
)

PHASE13_CHECK_VALUES: Final = (
    "SOURCE_KIND_EXACT",
    "READ_ONLY_TRANSPORT_EXACT",
    "USE_RIGHTS_CURRENT_SUFFICIENT",
    "SECURITY_MASTER_STABLE_IDENTITY",
    "POINT_IN_TIME_UNIVERSE_MEMBERSHIP",
    "RAW_OHLCV_AVAILABILITY",
    "CORPORATE_ACTION_ANNOUNCEMENT_REVISION",
    "DELISTING_RETURN_SEMANTICS",
    "AS_REPORTED_FUNDAMENTAL_REVISION",
    "RAW_NORMALIZED_RECONCILIATION",
    "NULL_SENTINEL_SCHEMA_DRIFT",
    "DETERMINISTIC_CAPTURE_MANIFEST",
)

PHASE13_FIXED_ENDPOINTS: Final = (
    {
        "ordinal": 1,
        "code": "FUNDAMENTALS_META",
        "capability": "SECURITY_MASTER_STABLE_IDENTITY",
        "method": "GET",
        "host": TIINGO_QUALIFICATION_HOST,
        "port": TIINGO_QUALIFICATION_PORT,
        "target": (
            "/tiingo/fundamentals/meta?columns="
            "permaTicker,ticker,isActive,statementLastUpdated,dailyLastUpdated"
        ),
    },
    {
        "ordinal": 2,
        "code": "EOD_PRICES",
        "capability": "RAW_OHLCV_AVAILABILITY",
        "method": "GET",
        "host": TIINGO_QUALIFICATION_HOST,
        "port": TIINGO_QUALIFICATION_PORT,
        "target": "/tiingo/daily/AAPL/prices?startDate=2020-08-28&endDate=2020-09-01",
    },
    {
        "ordinal": 3,
        "code": "DISTRIBUTIONS",
        "capability": "CORPORATE_ACTION_ANNOUNCEMENT_REVISION",
        "method": "GET",
        "host": TIINGO_QUALIFICATION_HOST,
        "port": TIINGO_QUALIFICATION_PORT,
        "target": (
            "/tiingo/corporate-actions/AAPL/distributions?"
            "startExDate=2020-01-01&endExDate=2020-12-31"
        ),
    },
    {
        "ordinal": 4,
        "code": "SPLITS",
        "capability": "CORPORATE_ACTION_ANNOUNCEMENT_REVISION",
        "method": "GET",
        "host": TIINGO_QUALIFICATION_HOST,
        "port": TIINGO_QUALIFICATION_PORT,
        "target": (
            "/tiingo/corporate-actions/AAPL/splits?startExDate=2020-08-28&endExDate=2020-09-01"
        ),
    },
    {
        "ordinal": 5,
        "code": "FUNDAMENTAL_STATEMENTS",
        "capability": "AS_REPORTED_FUNDAMENTAL_REVISION",
        "method": "GET",
        "host": TIINGO_QUALIFICATION_HOST,
        "port": TIINGO_QUALIFICATION_PORT,
        "target": "/tiingo/fundamentals/AAPL/statements?startDate=2019-01-01",
    },
)

PHASE13_TRANSPORT_PROFILE_SHA256: Final = domain_sha256(
    PHASE13_TRANSPORT_PROFILE_HASH_DOMAIN,
    {
        "endpoints": PHASE13_FIXED_ENDPOINTS,
        "attempts": 1,
        "https_only": True,
        "redirects": False,
        "proxies": False,
        "tls_hostname_verification": True,
    },
)

PHASE13_SAMPLE_PLAN_ID: Final = "phase13-family-a-qualification-sample-v1"
PHASE13_SAMPLE_PLAN_SHA256: Final = domain_sha256(
    PHASE13_SAMPLE_PLAN_HASH_DOMAIN,
    {
        "sample_plan_id": PHASE13_SAMPLE_PLAN_ID,
        "capabilities": PHASE13_CAPABILITY_VALUES,
        "checks": PHASE13_CHECK_VALUES,
        "endpoints": PHASE13_FIXED_ENDPOINTS,
        "qualification_probe_symbol": "AAPL",
        "historical_membership_endpoint_documented": False,
        "delisting_return_endpoint_documented": False,
    },
)


def identity(namespace: UUID, sha256: str) -> UUID:
    """Derive a deterministic UUID from a validated lowercase SHA-256 value."""

    return uuid_from_sha256(namespace, sha256)


def raw_response_sha256(payload: bytes) -> str:
    """Hash a transient response body without retaining it in an artifact."""

    return hashlib.sha256(payload).hexdigest()


__all__ = [name for name in globals() if name.startswith(("PHASE13_", "TIINGO_"))] + [
    "canonical_json_bytes",
    "canonicalize",
    "domain_sha256",
    "identity",
    "raw_response_sha256",
]
