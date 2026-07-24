"""Vendor-neutral, read-only Phase 28 adapter and deterministic mock."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Protocol, runtime_checkable

from fable5_paper.phase28.canonical import (
    PHASE28_FIXED_ENDPOINTS,
    PHASE28_TRANSPORT_PROFILE_SHA256,
    domain_sha256,
)
from fable5_paper.phase28.contracts import (
    InspectionCode,
    InspectionStatus,
    ObservationInspectionEvidence,
    ObservationSourceKind,
)


@dataclass(frozen=True, slots=True, repr=False)
class TransientAsset:
    symbol: str
    status: str
    active: bool
    tradable: bool


@dataclass(frozen=True, slots=True, repr=False)
class TransientBar:
    event_time_utc: datetime
    open_price: Decimal
    close_price: Decimal


@dataclass(frozen=True, slots=True, repr=False)
class TransientQuote:
    event_time_utc: datetime
    bid_price: Decimal
    ask_price: Decimal


@dataclass(frozen=True, slots=True, repr=False)
class TransientSnapshot:
    latest_trade_time_utc: datetime | None
    latest_quote: TransientQuote | None
    minute_bar: TransientBar | None
    daily_bar: TransientBar | None
    previous_daily_bar: TransientBar | None


@dataclass(frozen=True, slots=True, repr=False)
class TransientBars:
    values: dict[str, TransientBar]


@dataclass(frozen=True, slots=True, repr=False)
class TransientQuotes:
    values: dict[str, TransientQuote]


@dataclass(frozen=True, slots=True, repr=False)
class TransientSnapshots:
    values: dict[str, TransientSnapshot]


TransientPayload = TransientAsset | TransientBars | TransientQuotes | TransientSnapshots


@dataclass(frozen=True, slots=True, repr=False)
class ObservationInspection:
    evidence: ObservationInspectionEvidence
    payload: TransientPayload | None


@runtime_checkable
class ObservationOnlyAdapter(Protocol):
    """Exactly six inspection methods; mutation is not part of this boundary."""

    @property
    def source_kind(self) -> ObservationSourceKind: ...

    @property
    def transport_profile_sha256(self) -> str: ...

    @property
    def exact_use_review_confirmed_for_external_run(self) -> bool: ...

    def inspect_asset_aapl(self) -> ObservationInspection: ...

    def inspect_asset_msft(self) -> ObservationInspection: ...

    def inspect_asset_spy(self) -> ObservationInspection: ...

    def inspect_latest_bars(self) -> ObservationInspection: ...

    def inspect_latest_quotes(self) -> ObservationInspection: ...

    def inspect_snapshots(self) -> ObservationInspection: ...


def _sanitized_payload(payload: TransientPayload) -> dict[str, object]:
    if isinstance(payload, TransientAsset):
        return {
            "kind": "asset",
            "symbol": payload.symbol,
            "status": payload.status,
            "active": payload.active,
            "tradable": payload.tradable,
        }
    if isinstance(payload, TransientBars):
        return {
            "kind": "bars",
            "symbols": tuple(payload.values),
            "event_times": {
                symbol: value.event_time_utc for symbol, value in payload.values.items()
            },
            "prices_valid": {
                symbol: value.open_price > 0 and value.close_price > 0
                for symbol, value in payload.values.items()
            },
        }
    if isinstance(payload, TransientQuotes):
        return {
            "kind": "quotes",
            "symbols": tuple(payload.values),
            "event_times": {
                symbol: value.event_time_utc for symbol, value in payload.values.items()
            },
            "quotes_valid": {
                symbol: value.bid_price > 0
                and value.ask_price > 0
                and value.ask_price >= value.bid_price
                for symbol, value in payload.values.items()
            },
        }
    return {
        "kind": "snapshots",
        "symbols": tuple(payload.values),
        "complete": {
            symbol: all(
                (
                    value.latest_quote is not None,
                    value.latest_trade_time_utc is not None,
                    value.minute_bar is not None,
                    value.daily_bar is not None,
                    value.previous_daily_bar is not None,
                )
            )
            for symbol, value in payload.values.items()
        },
        "event_times": {
            symbol: (value.minute_bar.event_time_utc if value.minute_bar is not None else None)
            for symbol, value in payload.values.items()
        },
        "latest_trade_times": {
            symbol: value.latest_trade_time_utc for symbol, value in payload.values.items()
        },
    }


def build_inspection(
    *,
    ordinal: int,
    code: InspectionCode,
    status: InspectionStatus,
    external_request_performed: bool,
    started_at_utc: datetime,
    completed_at_utc: datetime,
    payload: TransientPayload | None,
    http_status: int | None = None,
    request_id_sha256: str | None = None,
    response_sha256: str | None = None,
    failure_reason: str | None = None,
) -> ObservationInspection:
    endpoint = PHASE28_FIXED_ENDPOINTS[ordinal - 1]
    observation_hash = (
        domain_sha256("phase28-sanitized-transient-observation-v1", _sanitized_payload(payload))
        if payload is not None
        else None
    )
    evidence_payload = {
        "schema_version": "phase28-alpaca-iex-inspection-v1",
        "ordinal": ordinal,
        "code": code,
        "status": status,
        "method": "GET",
        "external_request_performed": external_request_performed,
        "endpoint_sha256": domain_sha256("phase28-fixed-endpoint-v1", endpoint),
        "request_started_at_utc": started_at_utc,
        "request_completed_at_utc": completed_at_utc,
        "http_status": http_status,
        "request_id_sha256": request_id_sha256,
        "response_sha256": response_sha256,
        "sanitized_observation_sha256": observation_hash,
        "failure_reason": failure_reason,
    }
    evidence = ObservationInspectionEvidence.model_validate(
        {
            **evidence_payload,
            "inspection_sha256": domain_sha256(
                "phase28-alpaca-iex-inspection-v1", evidence_payload
            ),
        }
    )
    return ObservationInspection(evidence=evidence, payload=payload)


class DeterministicMockObservationAdapter:
    """A socket-free mock that exercises all three frozen outcome values."""

    _BASE = datetime(2024, 1, 2, 15, 0, tzinfo=UTC)

    @property
    def source_kind(self) -> ObservationSourceKind:
        return ObservationSourceKind.DETERMINISTIC_MOCK

    @property
    def transport_profile_sha256(self) -> str:
        return PHASE28_TRANSPORT_PROFILE_SHA256

    @property
    def exact_use_review_confirmed_for_external_run(self) -> bool:
        return False

    def _result(
        self, ordinal: int, code: InspectionCode, payload: TransientPayload
    ) -> ObservationInspection:
        started = self._BASE + timedelta(milliseconds=ordinal * 10)
        return build_inspection(
            ordinal=ordinal,
            code=code,
            status=InspectionStatus.OBSERVED,
            external_request_performed=False,
            started_at_utc=started,
            completed_at_utc=started + timedelta(milliseconds=1),
            payload=payload,
        )

    def _asset(self, ordinal: int, code: InspectionCode, symbol: str) -> ObservationInspection:
        return self._result(
            ordinal,
            code,
            TransientAsset(symbol=symbol, status="active", active=True, tradable=True),
        )

    def inspect_asset_aapl(self) -> ObservationInspection:
        return self._asset(1, InspectionCode.ASSET_AAPL, "AAPL")

    def inspect_asset_msft(self) -> ObservationInspection:
        return self._asset(2, InspectionCode.ASSET_MSFT, "MSFT")

    def inspect_asset_spy(self) -> ObservationInspection:
        return self._asset(3, InspectionCode.ASSET_SPY, "SPY")

    def inspect_latest_bars(self) -> ObservationInspection:
        bars = {
            symbol: TransientBar(
                event_time_utc=self._BASE - timedelta(seconds=10),
                open_price=Decimal("100"),
                close_price=Decimal("102"),
            )
            for symbol in ("AAPL", "MSFT", "SPY")
        }
        return self._result(4, InspectionCode.LATEST_BARS, TransientBars(bars))

    def inspect_latest_quotes(self) -> ObservationInspection:
        quotes = {
            "AAPL": TransientQuote(
                self._BASE - timedelta(seconds=5), Decimal("101"), Decimal("102")
            ),
            "MSFT": TransientQuote(
                self._BASE - timedelta(seconds=5), Decimal("101"), Decimal("102")
            ),
            "SPY": TransientQuote(self._BASE - timedelta(seconds=5), Decimal("0"), Decimal("102")),
        }
        return self._result(5, InspectionCode.LATEST_QUOTES, TransientQuotes(quotes))

    def inspect_snapshots(self) -> ObservationInspection:
        values: dict[str, TransientSnapshot] = {}
        for symbol in ("AAPL", "MSFT", "SPY"):
            prior_close = Decimal("103") if symbol == "MSFT" else Decimal("99")
            values[symbol] = TransientSnapshot(
                latest_trade_time_utc=self._BASE - timedelta(seconds=4),
                latest_quote=TransientQuote(
                    self._BASE - timedelta(seconds=4), Decimal("101"), Decimal("102")
                ),
                minute_bar=TransientBar(
                    self._BASE - timedelta(seconds=10), Decimal("101"), Decimal("103")
                ),
                daily_bar=TransientBar(
                    self._BASE - timedelta(hours=5), Decimal("100"), Decimal("102")
                ),
                previous_daily_bar=TransientBar(
                    self._BASE - timedelta(days=1), Decimal("98"), prior_close
                ),
            )
        return self._result(6, InspectionCode.SNAPSHOTS, TransientSnapshots(values))


__all__ = [
    "DeterministicMockObservationAdapter",
    "ObservationInspection",
    "ObservationOnlyAdapter",
    "TransientAsset",
    "TransientBar",
    "TransientBars",
    "TransientPayload",
    "TransientQuote",
    "TransientQuotes",
    "TransientSnapshot",
    "TransientSnapshots",
    "build_inspection",
]
