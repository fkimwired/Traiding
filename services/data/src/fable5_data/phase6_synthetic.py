"""Deterministic Phase 6 source evidence built on the immutable Phase 4 envelope.

The fixtures are deliberately small, synthetic, and provider-fact-free.  They supply
point-in-time source records only; they do not contain labels, signals, model decisions,
performance claims, allocations, promotion outcomes, or execution instructions.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Final, Literal, TypedDict
from uuid import UUID

from fable5_mapping.models import CanonicalFamily

from fable5_data.canonical import canonical_json_bytes, raw_payload_sha256
from fable5_data.contracts import (
    PHASE6_SYNTHETIC_FIXTURE_SET_VERSION,
    AuthorizedMappingIdentity,
    DataCapability,
    official_document_content_sha256,
)
from fable5_data.quality import QualityReferenceCatalog
from fable5_data.synthetic import (
    PHASE6_SYNTHETIC_ADAPTER_PROFILE,
    PHASE6_SYNTHETIC_MOCK_CONFIGURATION,
    SyntheticPointInTimeAdapter,
)

PHASE6_FIXTURE_RETRIEVED_AT: Final = datetime(2024, 1, 2, 12, tzinfo=UTC)
PHASE6_PLACEHOLDER_OFFICIAL_SOURCE_VERSION_ID: Final = UUID("cccccccc-cccc-5ccc-8ccc-cccccccccccc")


class _SecurityFixture(TypedDict):
    instrument_id: str
    listing_id: str
    symbol: str
    issuer_id: str
    legal_name: str
    sector_id: str
    sector_name: str
    terminal_status: Literal["active", "inactive", "delisted"]
    terminal_at: str | None
    prices: tuple[str, ...]
    volumes: tuple[str, ...]
    fundamentals: dict[str, tuple[str, str]]


_SECURITIES: Final[tuple[_SecurityFixture, ...]] = (
    {
        "instrument_id": "11111111-1111-5111-8111-111111111111",
        "listing_id": "22222222-2222-5222-8222-222222222222",
        "symbol": "SYN_A",
        "issuer_id": "issuer-synthetic-a",
        "legal_name": "Synthetic Active Corporation",
        "sector_id": "synthetic-diversified",
        "sector_name": "Synthetic Diversified",
        "terminal_status": "active",
        "terminal_at": None,
        "prices": ("40", "41", "42", "43", "44", "22", "23", "24"),
        "volumes": (
            "900000",
            "950000",
            "1000000",
            "1100000",
            "1200000",
            "1800000",
            "1600000",
            "1500000",
        ),
        "fundamentals": {
            "revenue": ("100000000", "USD"),
            "net_income": ("10000000", "USD"),
            "book_equity": ("50000000", "USD"),
            "shares_outstanding": ("10000000", "shares"),
        },
    },
    {
        "instrument_id": "33333333-3333-5333-8333-333333333333",
        "listing_id": "44444444-4444-5444-8444-444444444444",
        "symbol": "SYN_B",
        "issuer_id": "issuer-synthetic-b",
        "legal_name": "Synthetic Inactive Industries",
        "sector_id": "synthetic-diversified",
        "sector_name": "Synthetic Diversified",
        "terminal_status": "inactive",
        "terminal_at": "2021-06-01T00:00:00Z",
        "prices": ("30", "30.5", "30", "29", "28.5", "28", "27.5", "27"),
        "volumes": ("500000", "520000", "540000", "560000", "580000", "600000", "620000", "640000"),
        "fundamentals": {
            "revenue": ("80000000", "USD"),
            "net_income": ("4000000", "USD"),
            "book_equity": ("40000000", "USD"),
            "shares_outstanding": ("8000000", "shares"),
        },
    },
    {
        "instrument_id": "55555555-5555-5555-8555-555555555555",
        "listing_id": "66666666-6666-5666-8666-666666666666",
        "symbol": "SYN_C",
        "issuer_id": "issuer-synthetic-c",
        "legal_name": "Synthetic Delisted Holdings",
        "sector_id": "synthetic-diversified",
        "sector_name": "Synthetic Diversified",
        "terminal_status": "delisted",
        "terminal_at": "2020-02-04T00:00:00Z",
        "prices": ("15", "15.5", "14.5", "14", "13", "12", "10", "8"),
        "volumes": ("300000", "320000", "350000", "400000", "450000", "500000", "700000", "900000"),
        "fundamentals": {
            "revenue": ("60000000", "USD"),
            "net_income": ("-5000000", "USD"),
            "book_equity": ("20000000", "USD"),
            "shares_outstanding": ("6000000", "shares"),
        },
    },
)


def _weekday_dates(start: date, end: date) -> tuple[str, ...]:
    days: list[str] = []
    current = start
    while current <= end:
        if current.weekday() < 5:
            days.append(current.isoformat())
        current += timedelta(days=1)
    return tuple(days)


_BAR_DATES: Final = _weekday_dates(date(2019, 3, 1), date(2020, 4, 30))
_VOLATILITY_INPUT_END_DATE: Final = "2020-03-31"
_ACTIVE_PRICE_CYCLE: Final[tuple[Decimal, ...]] = (
    Decimal("0"),
    Decimal("0.20"),
    Decimal("-0.15"),
    Decimal("0.10"),
    Decimal("-0.20"),
    Decimal("0.15"),
)


def _security_bar_dates(security: _SecurityFixture) -> tuple[str, ...]:
    if security["terminal_status"] != "delisted":
        return _BAR_DATES
    return tuple(day for day in _BAR_DATES if day <= "2020-02-03")


def _synthetic_market_point(
    security_index: int,
    bar_index: int,
    day: str,
) -> tuple[Decimal, Decimal]:
    """Return deterministic raw nominal close and volume for one mock session."""

    index = Decimal(bar_index - 1)
    if security_index == 1:
        if day < "2020-01-09":
            trend_close = Decimal("28") + index * Decimal("0.045")
        else:
            split_index = Decimal(_BAR_DATES.index("2020-01-09"))
            pre_split = Decimal("28") + split_index * Decimal("0.045")
            trend_close = pre_split / Decimal("2") + (index - split_index) * Decimal("0.035")
        # The immutable synthetic path deliberately contains a deterministic cycle.
        # This gives B/C research labels both signs without deriving any model output
        # from a future label or manufacturing a return inside the evaluation bridge.
        close = trend_close + _ACTIVE_PRICE_CYCLE[(bar_index - 1) % len(_ACTIVE_PRICE_CYCLE)]
        volume = Decimal("900000") + (index % Decimal("17")) * Decimal("25000")
    elif security_index == 2:
        close = Decimal("36") - index * Decimal("0.025")
        volume = Decimal("500000") + (index % Decimal("13")) * Decimal("18000")
    else:
        close = Decimal("24") - index * Decimal("0.045")
        volume = Decimal("300000") + (index % Decimal("11")) * Decimal("30000")
    if close <= Decimal("1"):
        raise ValueError("Phase 6 synthetic nominal prices must remain positive")
    return close.quantize(Decimal("0.0001")), volume


def _decimal_text(value: Decimal) -> str:
    """Render fixture decimals in the frozen canonical value representation."""

    if not value.is_finite():
        raise ValueError("Phase 6 synthetic fixture decimals must be finite")
    if value == 0:
        return "0"
    rendered = format(value.normalize(), "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered


def _record(
    *,
    alias: str,
    capability: DataCapability,
    record_type: str,
    logical_key: dict[str, object],
    instrument_id: str | None,
    listing_id: str | None,
    event_time: str,
    available_at: str,
    valid_from: str,
    valid_to: str | None,
    unit: str,
    currency: str | None,
    payload: dict[str, object],
) -> dict[str, object]:
    return {
        "alias": alias,
        "capability": capability.value,
        "record_type": record_type,
        "source_record_id": f"phase6-{alias}",
        "logical_key": logical_key,
        "instrument_id": instrument_id,
        "listing_id": listing_id,
        "event_time": event_time,
        "available_at": available_at,
        "valid_from": valid_from,
        "valid_to": valid_to,
        "revision_id": f"{alias}-r1",
        "vintage_id": f"{alias}-v1",
        "revision_sequence": 1,
        "source_timezone": "America/New_York",
        "calendar_id": "XNYS",
        "unit": unit,
        "currency": currency,
        "availability_precision": "timestamp",
        "payload": payload,
    }


def _identity_records() -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for index, security in enumerate(_SECURITIES, start=1):
        instrument_id = str(security["instrument_id"])
        listing_id = str(security["listing_id"])
        symbol = str(security["symbol"])
        terminal_at = security["terminal_at"]
        records.append(
            _record(
                alias=f"instrument_{index}",
                capability=DataCapability.SECURITY_MASTER,
                record_type="instrument_identity",
                logical_key={"instrument_id": instrument_id, "valid_from": "2018-01-01T00:00:00Z"},
                instrument_id=instrument_id,
                listing_id=None,
                event_time="2018-01-01T00:00:00Z",
                available_at="2018-01-02T00:00:00Z",
                valid_from="2018-01-01T00:00:00Z",
                valid_to=None,
                unit="security",
                currency="USD",
                payload={
                    "record_type": "instrument_identity",
                    "instrument_type": "common_stock",
                    "issuer_id": security["issuer_id"],
                    "legal_name": security["legal_name"],
                    "country_code": "US",
                    "share_class_id": "class-a",
                },
            )
        )
        records.append(
            _record(
                alias=f"listing_{index}_active",
                capability=DataCapability.SECURITY_MASTER,
                record_type="listing_identity",
                logical_key={"listing_id": listing_id, "valid_from": "2018-01-01T00:00:00Z"},
                instrument_id=instrument_id,
                listing_id=listing_id,
                event_time="2018-01-01T00:00:00Z",
                available_at="2018-01-02T00:00:00Z",
                valid_from="2018-01-01T00:00:00Z",
                valid_to=None if terminal_at is None else str(terminal_at),
                unit="security",
                currency="USD",
                payload={
                    "record_type": "listing_identity",
                    "symbol": symbol,
                    "exchange_mic": "XNYS",
                    "status": "active",
                    "primary_listing": True,
                },
            )
        )
        if terminal_at is not None:
            records.append(
                _record(
                    alias=f"listing_{index}_{security['terminal_status']}",
                    capability=DataCapability.SECURITY_MASTER,
                    record_type="listing_identity",
                    logical_key={"listing_id": listing_id, "valid_from": terminal_at},
                    instrument_id=instrument_id,
                    listing_id=listing_id,
                    event_time=str(terminal_at),
                    available_at=str(terminal_at),
                    valid_from=str(terminal_at),
                    valid_to=None,
                    unit="security",
                    currency="USD",
                    payload={
                        "record_type": "listing_identity",
                        "symbol": symbol,
                        "exchange_mic": "XNYS",
                        "status": security["terminal_status"],
                        "primary_listing": True,
                    },
                )
            )
        records.append(
            _record(
                alias=f"sector_{index}",
                capability=DataCapability.SECURITY_MASTER,
                record_type="sector_classification",
                logical_key={
                    "instrument_id": instrument_id,
                    "classification_scheme_id": "synthetic-sector-scheme",
                    "valid_from": "2018-01-01T00:00:00Z",
                },
                instrument_id=instrument_id,
                listing_id=None,
                event_time="2018-01-01T00:00:00Z",
                available_at="2018-01-03T00:00:00Z",
                valid_from="2018-01-01T00:00:00Z",
                valid_to=None,
                unit="classification",
                currency=None,
                payload={
                    "record_type": "sector_classification",
                    "classification_scheme_id": "synthetic-sector-scheme",
                    "classification_scheme_version": "v1",
                    "sector_id": security["sector_id"],
                    "sector_name": security["sector_name"],
                },
            )
        )
    return records


def _membership_records() -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for index, security in enumerate(_SECURITIES, start=1):
        instrument_id = str(security["instrument_id"])
        listing_id = str(security["listing_id"])
        terminal_at = security["terminal_at"]
        records.append(
            _record(
                alias=f"membership_{index}_included",
                capability=DataCapability.UNIVERSE_MEMBERSHIP,
                record_type="universe_membership",
                logical_key={
                    "listing_id": listing_id,
                    "universe_id": "phase6-synthetic-us-equity",
                    "valid_from": "2018-01-01T00:00:00Z",
                },
                instrument_id=instrument_id,
                listing_id=listing_id,
                event_time="2018-01-01T00:00:00Z",
                available_at="2018-01-03T00:00:00Z",
                valid_from="2018-01-01T00:00:00Z",
                valid_to=None if terminal_at is None else str(terminal_at),
                unit="membership",
                currency=None,
                payload={
                    "record_type": "universe_membership",
                    "universe_id": "phase6-synthetic-us-equity",
                    "status": "included",
                },
            )
        )
        if terminal_at is not None:
            records.append(
                _record(
                    alias=f"membership_{index}_excluded",
                    capability=DataCapability.UNIVERSE_MEMBERSHIP,
                    record_type="universe_membership",
                    logical_key={
                        "listing_id": listing_id,
                        "universe_id": "phase6-synthetic-us-equity",
                        "valid_from": terminal_at,
                    },
                    instrument_id=instrument_id,
                    listing_id=listing_id,
                    event_time=str(terminal_at),
                    available_at=str(terminal_at),
                    valid_from=str(terminal_at),
                    valid_to=None,
                    unit="membership",
                    currency=None,
                    payload={
                        "record_type": "universe_membership",
                        "universe_id": "phase6-synthetic-us-equity",
                        "status": "excluded",
                    },
                )
            )
    return records


def _calendar_records() -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for day in _BAR_DATES:
        alias_day = day.replace("-", "")
        records.append(
            _record(
                alias=f"calendar_{alias_day}",
                capability=DataCapability.TRADING_CALENDAR,
                record_type="calendar_session",
                logical_key={"calendar_id": "XNYS", "session_date": day},
                instrument_id=None,
                listing_id=None,
                event_time=f"{day}T00:00:00Z",
                available_at="2019-12-01T00:00:00Z",
                valid_from="2019-12-01T00:00:00Z",
                valid_to=None,
                unit="session",
                currency=None,
                payload={
                    "record_type": "calendar_session",
                    "session_date": day,
                    "status": "open",
                    "open_at": f"{day}T14:30:00Z",
                    "close_at": f"{day}T21:00:00Z",
                    "early_close": False,
                },
            )
        )
    return records


def _macro_regime_records() -> list[dict[str, object]]:
    """Return predeclared PIT rate and stress-window evidence for the positive A fixture."""

    return [
        _record(
            alias="macro_rate_202001",
            capability=DataCapability.MACRO_REGIME_INPUTS,
            record_type="macro_rate_observation",
            logical_key={
                "series_id": "synthetic-policy-rate",
                "observation_period_end": "2019-12-31",
                "vintage_id": "synthetic-rate-vintage-2020-01",
            },
            instrument_id=None,
            listing_id=None,
            event_time="2019-12-31T23:59:59Z",
            available_at="2020-01-02T13:00:00Z",
            valid_from="2020-01-02T13:00:00Z",
            valid_to="2020-02-03T13:00:00Z",
            unit="percentage-points",
            currency=None,
            payload={
                "record_type": "macro_rate_observation",
                "series_id": "synthetic-policy-rate",
                "observation_period_end": "2019-12-31",
                "released_at": "2020-01-02T13:00:00Z",
                "vintage_id": "synthetic-rate-vintage-2020-01",
                "rate_value": "1.60",
                "previous_rate_value": "1.50",
                "rate_change": "0.10",
            },
        ),
        _record(
            alias="macro_rate_202002",
            capability=DataCapability.MACRO_REGIME_INPUTS,
            record_type="macro_rate_observation",
            logical_key={
                "series_id": "synthetic-policy-rate",
                "observation_period_end": "2020-01-31",
                "vintage_id": "synthetic-rate-vintage-2020-02",
            },
            instrument_id=None,
            listing_id=None,
            event_time="2020-01-31T23:59:59Z",
            available_at="2020-02-03T13:00:00Z",
            valid_from="2020-02-03T13:00:00Z",
            valid_to=None,
            unit="percentage-points",
            currency=None,
            payload={
                "record_type": "macro_rate_observation",
                "series_id": "synthetic-policy-rate",
                "observation_period_end": "2020-01-31",
                "released_at": "2020-02-03T13:00:00Z",
                "vintage_id": "synthetic-rate-vintage-2020-02",
                "rate_value": "1.40",
                "previous_rate_value": "1.60",
                "rate_change": "-0.20",
            },
        ),
        _record(
            alias="crisis_window_20200129",
            capability=DataCapability.MACRO_REGIME_INPUTS,
            record_type="crisis_window_definition",
            logical_key={"crisis_window_id": "synthetic-predeclared-stress-2020-01"},
            instrument_id=None,
            listing_id=None,
            event_time="2019-12-01T00:00:00Z",
            available_at="2019-12-01T00:00:00Z",
            valid_from="2019-12-01T00:00:00Z",
            valid_to=None,
            unit="utc-interval",
            currency=None,
            payload={
                "record_type": "crisis_window_definition",
                "crisis_window_id": "synthetic-predeclared-stress-2020-01",
                "definition_method_id": "synthetic-predeclared-calendar-window-v1",
                "declared_at": "2019-12-01T00:00:00Z",
                "window_start": "2020-01-29T00:00:00Z",
                "window_end": "2020-02-04T00:00:00Z",
            },
        ),
    ]


def _market_records() -> list[dict[str, object]]:
    records: list[dict[str, object]] = [
        _record(
            alias="action_1_split",
            capability=DataCapability.CORPORATE_ACTIONS,
            record_type="corporate_action",
            logical_key={"corporate_action_id": "phase6-synthetic-a-split"},
            instrument_id=str(_SECURITIES[0]["instrument_id"]),
            listing_id=str(_SECURITIES[0]["listing_id"]),
            event_time="2020-01-07T13:00:00Z",
            available_at="2020-01-07T13:05:00Z",
            valid_from="2020-01-07T13:00:00Z",
            valid_to=None,
            unit="ratio",
            currency=None,
            payload={
                "record_type": "corporate_action",
                "corporate_action_id": "phase6-synthetic-a-split",
                "action_type": "split",
                "announcement_at": "2020-01-07T13:00:00Z",
                "effective_at": "2020-01-09T14:30:00Z",
                "split_ratio": "2",
                "cash_amount": None,
                "target_instrument_id": None,
            },
        )
    ]
    for security_index, security in enumerate(_SECURITIES, start=1):
        for bar_index, day in enumerate(_security_bar_dates(security), start=1):
            close, volume = _synthetic_market_point(security_index, bar_index, day)
            open_price = close - Decimal("0.25")
            records.append(
                _record(
                    alias=f"bar_{security_index}_{bar_index}",
                    capability=DataCapability.OHLCV,
                    record_type="ohlcv_bar",
                    logical_key={
                        "listing_id": security["listing_id"],
                        "bar_interval": "P1D",
                        "bar_start": f"{day}T14:30:00Z",
                        "adjustment_basis": "raw_unadjusted",
                    },
                    instrument_id=str(security["instrument_id"]),
                    listing_id=str(security["listing_id"]),
                    event_time=f"{day}T21:00:00Z",
                    available_at=f"{day}T21:05:00Z",
                    valid_from=f"{day}T21:00:00Z",
                    valid_to=None,
                    unit="USD-per-share",
                    currency="USD",
                    payload={
                        "record_type": "ohlcv_bar",
                        "bar_interval": "P1D",
                        "bar_start": f"{day}T14:30:00Z",
                        "bar_end": f"{day}T21:00:00Z",
                        "open": _decimal_text(open_price),
                        "high": _decimal_text(close + Decimal("0.5")),
                        "low": _decimal_text(open_price - Decimal("0.5")),
                        "close": _decimal_text(close),
                        "volume": _decimal_text(volume),
                        "volume_unit": "shares",
                        "adjustment_basis": "raw_unadjusted",
                        "adjustment_as_of": None,
                        "corporate_action_revision_aliases": [],
                    },
                )
            )
    records.append(
        _record(
            alias="delisting_3",
            capability=DataCapability.DELISTINGS,
            record_type="delisting_event",
            logical_key={"delisting_event_id": "phase6-synthetic-c-delisting"},
            instrument_id=str(_SECURITIES[2]["instrument_id"]),
            listing_id=str(_SECURITIES[2]["listing_id"]),
            event_time="2020-02-04T00:00:00Z",
            available_at="2020-02-04T00:05:00Z",
            valid_from="2020-02-04T00:00:00Z",
            valid_to=None,
            unit="decimal-return",
            currency="USD",
            payload={
                "record_type": "delisting_event",
                "delisting_event_id": "phase6-synthetic-c-delisting",
                "delisting_type": "exchange_removal",
                "last_trade_at": "2020-02-03T21:00:00Z",
                "effective_at": "2020-02-04T00:00:00Z",
                "return_inclusion": "separate_return_required",
                "delisting_return": "-0.35",
            },
        )
    )
    return records


def _fundamental_records() -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for security_index, security in enumerate(_SECURITIES, start=1):
        for concept, (value, unit) in security["fundamentals"].items():
            alias = f"fundamental_{security_index}_{concept}"
            records.append(
                _record(
                    alias=alias,
                    capability=DataCapability.AS_REPORTED_FUNDAMENTALS,
                    record_type="as_reported_fundamental",
                    logical_key={
                        "instrument_id": security["instrument_id"],
                        "concept_id": concept,
                        "fiscal_period_end": "2018-12-31",
                        "fiscal_period_type": "year",
                    },
                    instrument_id=str(security["instrument_id"]),
                    listing_id=str(security["listing_id"]),
                    event_time="2019-03-01T15:00:00Z",
                    available_at="2019-03-01T15:00:00Z",
                    valid_from="2019-03-01T15:00:00Z",
                    valid_to=None,
                    unit=str(unit),
                    currency="USD",
                    payload={
                        "record_type": "as_reported_fundamental",
                        "concept_id": concept,
                        "fiscal_period_start": "2018-01-01",
                        "fiscal_period_end": "2018-12-31",
                        "fiscal_period_type": "year",
                        "official_document_id": f"phase6-synthetic-{security_index}-10k-2018",
                        "filing_accepted_at": "2019-03-01T15:00:00Z",
                        "as_reported": True,
                        "amendment_sequence": 0,
                        "restates_revision_id": None,
                        "value": value,
                    },
                )
            )
    return records


def _official_records(source_version_ids: tuple[UUID, ...]) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    security = _SECURITIES[0]
    for source_version_id in source_version_ids:
        suffix = source_version_id.hex
        event_id = f"phase6-official-event-{suffix}"
        original_id = f"phase6-official-document-{suffix}-original"
        correction_id = f"phase6-official-document-{suffix}-correction-1"
        original_accession = f"phase6-accession-{suffix}-original"
        correction_accession = f"phase6-accession-{suffix}-correction-1"
        original_text = f"Synthetic official filing for source version {source_version_id}."
        correction_text = (
            f"Corrected synthetic official filing for source version {source_version_id}."
        )
        for sequence, values in enumerate(
            (
                (
                    original_id,
                    original_accession,
                    original_text,
                    "2020-03-01T14:55:00Z",
                    "2020-03-01T15:00:00Z",
                    None,
                    None,
                ),
                (
                    correction_id,
                    correction_accession,
                    correction_text,
                    "2020-03-05T14:55:00Z",
                    "2020-03-05T15:00:00Z",
                    "2020-03-05T14:57:00Z",
                    original_id,
                ),
            )
        ):
            (
                document_id,
                accession_id,
                document_text,
                published_at,
                accepted_at,
                corrected_at,
                amendment_of,
            ) = values
            content_hash = official_document_content_sha256(document_text)
            common_payload: dict[str, object] = {
                "official_document_id": document_id,
                "official_event_id": event_id,
                "official_source_version_id": str(source_version_id),
                "document_type": "regulatory_filing",
                "event_type": "filing",
                "accession_id": accession_id,
                "published_at": published_at,
                "accepted_at": accepted_at,
                "document_content_sha256": content_hash,
                "amendment_of_document_id": amendment_of,
            }
            metadata_alias = f"official_metadata_{suffix}_{sequence}"
            content_alias = f"official_content_{suffix}_{sequence}"
            records.append(
                _record(
                    alias=metadata_alias,
                    capability=DataCapability.OFFICIAL_DOCUMENT_EVENT_METADATA,
                    record_type="official_document_event",
                    logical_key={
                        "record_type": "official_document_event",
                        "official_document_id": document_id,
                        "official_source_version_id": str(source_version_id),
                    },
                    instrument_id=str(security["instrument_id"]),
                    listing_id=str(security["listing_id"]),
                    event_time=accepted_at,
                    available_at=accepted_at,
                    valid_from=accepted_at,
                    valid_to=None,
                    unit="document-metadata",
                    currency=None,
                    payload={"record_type": "official_document_event", **common_payload},
                )
            )
            records.append(
                _record(
                    alias=content_alias,
                    capability=DataCapability.OFFICIAL_DOCUMENT_EVENT_METADATA,
                    record_type="official_document_content",
                    logical_key={
                        "record_type": "official_document_content",
                        "official_document_id": document_id,
                        "official_source_version_id": str(source_version_id),
                    },
                    instrument_id=str(security["instrument_id"]),
                    listing_id=str(security["listing_id"]),
                    event_time=accepted_at,
                    available_at=accepted_at,
                    valid_from=accepted_at,
                    valid_to=None,
                    unit="document-content",
                    currency=None,
                    payload={
                        "record_type": "official_document_content",
                        **common_payload,
                        "corrected_at": corrected_at,
                        "correction_sequence": sequence,
                        "document_text": document_text,
                    },
                )
            )
        social_record_id = f"phase6-social-attention-{suffix}"
        social_content = (
            f"Synthetic attention record referencing official source {source_version_id}."
        )
        records.append(
            _record(
                alias=f"social_attention_{suffix}",
                capability=DataCapability.OFFICIAL_DOCUMENT_EVENT_METADATA,
                record_type="social_attention",
                logical_key={
                    "record_type": "social_attention",
                    "social_attention_record_id": social_record_id,
                },
                instrument_id=str(security["instrument_id"]),
                listing_id=str(security["listing_id"]),
                event_time="2020-03-05T15:05:00Z",
                available_at="2020-03-05T15:06:00Z",
                valid_from="2020-03-05T15:06:00Z",
                valid_to=None,
                unit="attention-record",
                currency=None,
                payload={
                    "record_type": "social_attention",
                    "social_attention_record_id": social_record_id,
                    "platform_id": "synthetic-social-platform",
                    "observed_at": "2020-03-05T15:05:00Z",
                    "social_content_sha256": raw_payload_sha256(social_content.encode("utf-8")),
                    "entity_id": str(security["instrument_id"]),
                    "claimed_official_source_version_id": str(source_version_id),
                    "manipulation_prone": True,
                    "contributes_standalone": False,
                },
            )
        )
    return records


def _volatility_input_records() -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for security_index, security in enumerate(_SECURITIES, start=1):
        is_delisted = security["terminal_status"] == "delisted"
        security_days = _security_bar_dates(security)
        input_days = (
            security_days
            if is_delisted
            else tuple(day for day in security_days if day <= _VOLATILITY_INPUT_END_DATE)
        )
        available_at = "2020-02-04T00:06:00Z" if is_delisted else f"{input_days[-1]}T21:06:00Z"
        window_end = "2020-02-04T00:00:00Z" if is_delisted else f"{input_days[-1]}T21:00:00Z"
        records.append(
            _record(
                alias=f"volatility_input_{security_index}",
                capability=DataCapability.VOLATILITY_RETURN_INPUTS,
                record_type="volatility_return_input",
                logical_key={
                    "listing_id": security["listing_id"],
                    "window_start": f"{security_days[0]}T14:30:00Z",
                    "window_end": window_end,
                },
                instrument_id=str(security["instrument_id"]),
                listing_id=str(security["listing_id"]),
                event_time=available_at,
                available_at=available_at,
                valid_from=available_at,
                valid_to=None,
                unit="decimal-return-input",
                currency="USD",
                payload={
                    "record_type": "volatility_return_input",
                    "window_start": f"{security_days[0]}T14:30:00Z",
                    "window_end": window_end,
                    "bar_observation_aliases": [
                        f"bar_{security_index}_{bar_index}"
                        for bar_index in range(1, len(input_days) + 1)
                    ],
                    "corporate_action_observation_aliases": (
                        ["action_1_split"] if security_index == 1 else []
                    ),
                    "delisting_observation_aliases": (["delisting_3"] if is_delisted else []),
                    "calendar_observation_aliases": [
                        f"calendar_{day.replace('-', '')}" for day in input_days
                    ],
                },
            )
        )
    return records


def load_phase6_fixture_records(
    mapping: AuthorizedMappingIdentity | None = None,
) -> tuple[dict[str, object], ...]:
    """Return a defensive copy of complete deterministic A/B/C source records."""

    if (
        mapping is not None
        and mapping.canonical_family is CanonicalFamily.C_OFFICIAL_EVENT_TEXT_OVERLAY
    ):
        official_ids = mapping.official_corroboration_source_version_ids
    else:
        official_ids = (PHASE6_PLACEHOLDER_OFFICIAL_SOURCE_VERSION_ID,)
    records = [
        *_identity_records(),
        *_membership_records(),
        *_calendar_records(),
        *_macro_regime_records(),
        *_market_records(),
        *_fundamental_records(),
        *_official_records(official_ids),
        *_volatility_input_records(),
    ]
    return tuple(deepcopy(records))


def phase6_fixture_set_sha256(
    mapping: AuthorizedMappingIdentity | None = None,
) -> str:
    payload = canonical_json_bytes(
        {
            "fixture_set_version": PHASE6_SYNTHETIC_FIXTURE_SET_VERSION,
            "records": load_phase6_fixture_records(mapping),
        }
    )
    return raw_payload_sha256(payload)


class Phase6SyntheticPointInTimeAdapter(SyntheticPointInTimeAdapter):
    """Complete, mapping-bound Phase 6 mock source adapter."""

    def __init__(self, mapping: AuthorizedMappingIdentity | None = None) -> None:
        super().__init__(
            load_phase6_fixture_records(mapping),
            profile=PHASE6_SYNTHETIC_ADAPTER_PROFILE,
            fixture_set_version=PHASE6_SYNTHETIC_FIXTURE_SET_VERSION,
            retrieved_at=PHASE6_FIXTURE_RETRIEVED_AT,
        )

    @classmethod
    def for_mapping(
        cls,
        mapping: AuthorizedMappingIdentity,
    ) -> Phase6SyntheticPointInTimeAdapter:
        return cls(mapping)


def resolve_phase6_synthetic_adapter(
    mapping: AuthorizedMappingIdentity,
) -> tuple[Phase6SyntheticPointInTimeAdapter, QualityReferenceCatalog]:
    """Resolve mapping-bound content plus the exact cross-capability quality catalog."""

    adapter = Phase6SyntheticPointInTimeAdapter.for_mapping(mapping)
    return adapter, QualityReferenceCatalog.from_results(adapter.all_results())


__all__ = [
    "PHASE6_FIXTURE_RETRIEVED_AT",
    "PHASE6_PLACEHOLDER_OFFICIAL_SOURCE_VERSION_ID",
    "PHASE6_SYNTHETIC_ADAPTER_PROFILE",
    "PHASE6_SYNTHETIC_MOCK_CONFIGURATION",
    "Phase6SyntheticPointInTimeAdapter",
    "load_phase6_fixture_records",
    "phase6_fixture_set_sha256",
    "resolve_phase6_synthetic_adapter",
]
