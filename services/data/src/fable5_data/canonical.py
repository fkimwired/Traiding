from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence, Set
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from typing import Final
from uuid import UUID, uuid5

from pydantic import BaseModel

CANONICAL_JSON_VERSION: Final = "phase4-canonical-json-v1"
SNAPSHOT_HASH_DOMAIN: Final = "phase4-data-snapshot-v1"
RAW_OBSERVATION_HASH_DOMAIN: Final = "phase4-raw-observation-content-v1"
REVISION_CONTENT_HASH_DOMAIN: Final = "phase4-observation-revision-content-v1"
NORMALIZED_OBSERVATION_HASH_DOMAIN: Final = "phase4-normalized-observation-v1"
QUALITY_FINDING_HASH_DOMAIN: Final = "phase4-data-quality-finding-v1"
LOGICAL_RECORD_KEY_HASH_DOMAIN: Final = "phase4-logical-record-key-v1"
REQUEST_FINGERPRINT_HASH_DOMAIN: Final = "phase4-request-fingerprint-v1"
CONFIGURATION_HASH_DOMAIN: Final = "phase4-mock-configuration-v1"
PHASE4_SNAPSHOT_NAMESPACE = UUID("db56962d-1bf7-5e22-a173-6629d0ff31f0")
PHASE4_OBSERVATION_NAMESPACE = UUID("48c250b4-35ca-5b1c-a1fe-d9202aa009c7")
PHASE4_NORMALIZED_OBSERVATION_NAMESPACE = PHASE4_OBSERVATION_NAMESPACE
PHASE4_RAW_OBSERVATION_NAMESPACE = UUID("8087752b-5116-5683-bf09-341279373b14")
PHASE4_REVISION_NAMESPACE = UUID("bfbf0883-d241-5098-aef3-f737096bfb09")
PHASE4_QUALITY_FINDING_NAMESPACE = UUID("c972a3e0-1991-590c-823d-b1bd73567457")
PHASE4_LOGICAL_RECORD_NAMESPACE = UUID("29e71b4c-a922-5c9c-8465-1dbfb43810a8")
PHASE4_REQUEST_NAMESPACE = UUID("05238487-b285-5d41-8276-b09b65b020ff")

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _canonical_decimal(value: Decimal) -> str:
    if not value.is_finite():
        raise ValueError("canonical JSON does not support non-finite decimals")
    if value == 0:
        return "0"
    rendered = format(value.normalize(), "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered


def _canonical_datetime(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("canonical JSON requires timezone-aware datetimes")
    return value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def canonicalize(value: object) -> object:
    """Convert supported values to the frozen Phase 4 canonical JSON value space."""

    if isinstance(value, BaseModel):
        return canonicalize(value.model_dump(mode="python", exclude_none=False))
    if isinstance(value, Enum):
        return canonicalize(value.value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return _canonical_datetime(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return _canonical_decimal(value)
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        raise TypeError("canonical JSON forbids binary floating-point values; use Decimal")
    if isinstance(value, (bytes, bytearray, memoryview)):
        raise TypeError("canonical JSON forbids raw bytes; hash bytes before serialization")
    if isinstance(value, Mapping):
        result: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("canonical JSON object keys must be strings")
            result[key] = canonicalize(item)
        return result
    if isinstance(value, Set):
        normalized = [canonicalize(item) for item in value]
        return sorted(
            normalized,
            key=lambda item: json.dumps(
                item,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ),
        )
    if isinstance(value, Sequence):
        return [canonicalize(item) for item in value]
    raise TypeError(f"unsupported canonical JSON value: {type(value).__name__}")


def canonical_json_bytes(value: object) -> bytes:
    normalized = canonicalize(value)
    return json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def domain_sha256(domain: str, value: object) -> str:
    if not domain or domain != domain.strip() or "\x00" in domain:
        raise ValueError("hash domain must be a nonblank trimmed string without NUL")
    try:
        prefix = domain.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ValueError("hash domain must be ASCII") from exc
    return hashlib.sha256(prefix + b"\x00" + canonical_json_bytes(value)).hexdigest()


def raw_payload_sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def uuid_from_sha256(namespace: UUID, sha256: str) -> UUID:
    if _SHA256.fullmatch(sha256) is None:
        raise ValueError("sha256 must be 64 lowercase hexadecimal characters")
    return uuid5(namespace, sha256)


def snapshot_id_from_sha256(sha256: str) -> UUID:
    return uuid_from_sha256(PHASE4_SNAPSHOT_NAMESPACE, sha256)


def observation_id_from_sha256(sha256: str) -> UUID:
    return normalized_observation_id_from_sha256(sha256)


def raw_observation_id_from_sha256(sha256: str) -> UUID:
    return uuid_from_sha256(PHASE4_RAW_OBSERVATION_NAMESPACE, sha256)


def revision_id_from_sha256(sha256: str) -> UUID:
    return uuid_from_sha256(PHASE4_REVISION_NAMESPACE, sha256)


def normalized_observation_id_from_sha256(sha256: str) -> UUID:
    return uuid_from_sha256(PHASE4_NORMALIZED_OBSERVATION_NAMESPACE, sha256)


def quality_finding_id_from_sha256(sha256: str) -> UUID:
    return uuid_from_sha256(PHASE4_QUALITY_FINDING_NAMESPACE, sha256)


def logical_record_id_from_sha256(sha256: str) -> UUID:
    return uuid_from_sha256(PHASE4_LOGICAL_RECORD_NAMESPACE, sha256)


def request_id_from_sha256(sha256: str) -> UUID:
    return uuid_from_sha256(PHASE4_REQUEST_NAMESPACE, sha256)


def raw_observation_content_sha256(value: object) -> str:
    return domain_sha256(RAW_OBSERVATION_HASH_DOMAIN, value)


def revision_content_sha256(value: object) -> str:
    return domain_sha256(REVISION_CONTENT_HASH_DOMAIN, value)


def normalized_observation_content_sha256(value: object) -> str:
    return domain_sha256(NORMALIZED_OBSERVATION_HASH_DOMAIN, value)


def quality_finding_sha256(value: object) -> str:
    return domain_sha256(QUALITY_FINDING_HASH_DOMAIN, value)


def logical_record_key_sha256(value: object) -> str:
    return domain_sha256(LOGICAL_RECORD_KEY_HASH_DOMAIN, value)


def request_fingerprint_sha256(value: object) -> str:
    return domain_sha256(REQUEST_FINGERPRINT_HASH_DOMAIN, value)


__all__ = [
    "CANONICAL_JSON_VERSION",
    "CONFIGURATION_HASH_DOMAIN",
    "LOGICAL_RECORD_KEY_HASH_DOMAIN",
    "NORMALIZED_OBSERVATION_HASH_DOMAIN",
    "PHASE4_LOGICAL_RECORD_NAMESPACE",
    "PHASE4_NORMALIZED_OBSERVATION_NAMESPACE",
    "PHASE4_OBSERVATION_NAMESPACE",
    "PHASE4_QUALITY_FINDING_NAMESPACE",
    "PHASE4_RAW_OBSERVATION_NAMESPACE",
    "PHASE4_REQUEST_NAMESPACE",
    "PHASE4_REVISION_NAMESPACE",
    "PHASE4_SNAPSHOT_NAMESPACE",
    "QUALITY_FINDING_HASH_DOMAIN",
    "RAW_OBSERVATION_HASH_DOMAIN",
    "REQUEST_FINGERPRINT_HASH_DOMAIN",
    "REVISION_CONTENT_HASH_DOMAIN",
    "SNAPSHOT_HASH_DOMAIN",
    "canonical_json_bytes",
    "canonicalize",
    "domain_sha256",
    "logical_record_id_from_sha256",
    "logical_record_key_sha256",
    "normalized_observation_content_sha256",
    "normalized_observation_id_from_sha256",
    "observation_id_from_sha256",
    "quality_finding_id_from_sha256",
    "quality_finding_sha256",
    "raw_observation_content_sha256",
    "raw_observation_id_from_sha256",
    "raw_payload_sha256",
    "request_fingerprint_sha256",
    "request_id_from_sha256",
    "revision_content_sha256",
    "revision_id_from_sha256",
    "snapshot_id_from_sha256",
    "uuid_from_sha256",
]
