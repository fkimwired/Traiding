from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

import pytest
from fable5_data.canonical import (
    PHASE4_OBSERVATION_NAMESPACE,
    PHASE4_SNAPSHOT_NAMESPACE,
    canonical_json_bytes,
    domain_sha256,
    observation_id_from_sha256,
    raw_payload_sha256,
    snapshot_id_from_sha256,
)
from fable5_data.contracts import DataCapability


def test_canonical_json_freezes_decimal_time_uuid_enum_order_and_unicode() -> None:
    payload = {
        "z_decimal": Decimal("1.2300"),
        "a_time": datetime(
            2026,
            7,
            13,
            12,
            34,
            56,
            123456,
            tzinfo=timezone(-timedelta(hours=4)),
        ),
        "uuid": UUID("30000000-0000-0000-0000-000000000001"),
        "capability": DataCapability.OHLCV,
        "set": frozenset({"\u03b2", "a"}),
        "zero": Decimal("-0.000"),
        "none": None,
    }
    expected = (
        '{"a_time":"2026-07-13T16:34:56.123456Z",'
        '"capability":"ohlcv","none":null,"set":["a","\u03b2"],'
        '"uuid":"30000000-0000-0000-0000-000000000001",'
        '"z_decimal":"1.23","zero":"0"}'
    ).encode()
    assert canonical_json_bytes(payload) == expected
    assert canonical_json_bytes(dict(reversed(tuple(payload.items())))) == expected


@pytest.mark.parametrize(
    "value, error",
    [
        ({"float": 1.25}, "binary floating-point"),
        ({"bytes": b"raw"}, "raw bytes"),
        ({1: "non-string-key"}, "keys must be strings"),
        ({"naive": datetime(2026, 7, 13)}, "timezone-aware"),
        ({"infinite": Decimal("Infinity")}, "non-finite"),
    ],
)
def test_canonical_json_rejects_ambiguous_values(value: object, error: str) -> None:
    with pytest.raises((TypeError, ValueError), match=error):
        canonical_json_bytes(value)


def test_domain_hashing_and_uuid_namespaces_are_frozen() -> None:
    payload = {
        "as_of_utc": datetime(2026, 7, 13, 20, tzinfo=UTC),
        "value": Decimal("2.50"),
    }
    snapshot_hash = domain_sha256("phase4-data-snapshot-v1", payload)
    other_hash = domain_sha256("phase4-normalized-observation-v1", payload)

    assert PHASE4_SNAPSHOT_NAMESPACE == UUID("db56962d-1bf7-5e22-a173-6629d0ff31f0")
    assert PHASE4_OBSERVATION_NAMESPACE == UUID("48c250b4-35ca-5b1c-a1fe-d9202aa009c7")
    assert snapshot_hash == "aa431d83106bd74ba82ffa4461f9a76cb56f5d8f9cd562e8791147f51fd58193"
    assert other_hash == "99f19fd2d30ce7b215c1beae9da8d4a3c613237fe6803a5eb4916602e01b0f35"
    assert snapshot_hash != other_hash
    assert snapshot_id_from_sha256(snapshot_hash) == UUID("2b21b46e-86b4-557c-b8a9-dbecb32c2748")
    assert observation_id_from_sha256(snapshot_hash) == UUID("6ba27293-b2fa-56ae-9d36-94f8e0318f9b")


def test_raw_payload_hash_is_exact_bytes_not_canonical_json() -> None:
    assert raw_payload_sha256(b'{"a":1}') == (
        "015abd7f5cc57a2dd94b7590f04ad8084273905ee33ec5cebeae62276a97f862"
    )
    assert raw_payload_sha256(b'{ "a": 1 }') != raw_payload_sha256(b'{"a":1}')
