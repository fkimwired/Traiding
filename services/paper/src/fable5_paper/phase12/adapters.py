"""Vendor-neutral read-only adapter boundary and deterministic Phase 12 mock."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from typing import Protocol, runtime_checkable
from uuid import UUID

from fable5_paper.phase12.canonical import (
    PHASE12_INSPECTION_HASH_DOMAIN,
    PHASE12_OBSERVATION_HASH_DOMAIN,
    PHASE12_TRANSPORT_PROFILE_SHA256,
    domain_sha256,
)
from fable5_paper.phase12.contracts import (
    PaperAccountObservation,
    PaperClockObservation,
    PaperInstrumentObservation,
    PaperInventoryObservation,
    PaperQuoteObservation,
    ReadinessInspectionCode,
    ReadinessInspectionEvidence,
    ReadinessInspectionStatus,
    ReadinessObservation,
    ReadinessSourceKind,
)


@dataclass(frozen=True, slots=True)
class PaperBrokerInspection:
    evidence: ReadinessInspectionEvidence
    observation: ReadinessObservation | None


@runtime_checkable
class PaperBrokerAdapter(Protocol):
    """The complete broker boundary: six inspections and no mutation method."""

    @property
    def source_kind(self) -> ReadinessSourceKind: ...

    @property
    def transport_profile_sha256(self) -> str: ...

    def inspect_account(self) -> PaperBrokerInspection: ...

    def inspect_clock(self) -> PaperBrokerInspection: ...

    def inspect_instrument(self) -> PaperBrokerInspection: ...

    def inspect_positions(self) -> PaperBrokerInspection: ...

    def inspect_open_orders(self) -> PaperBrokerInspection: ...

    def inspect_latest_quote(self) -> PaperBrokerInspection: ...


def _hashed_observation_payload(payload: dict[str, object]) -> dict[str, object]:
    return {
        **payload,
        "observation_sha256": domain_sha256(PHASE12_OBSERVATION_HASH_DOMAIN, payload),
    }


def build_account_observation(
    *,
    status: str,
    account_blocked: bool,
    trading_blocked: bool,
    trade_suspended_by_user: bool,
) -> PaperAccountObservation:
    return PaperAccountObservation.model_validate(
        _hashed_observation_payload(
            {
                "schema_version": "phase12-paper-account-observation-v1",
                "status": status,
                "account_blocked": account_blocked,
                "trading_blocked": trading_blocked,
                "trade_suspended_by_user": trade_suspended_by_user,
            }
        )
    )


def build_clock_observation(
    *,
    is_open: bool,
    provider_timestamp_utc: datetime,
    next_open_utc: datetime,
    next_close_utc: datetime,
) -> PaperClockObservation:
    return PaperClockObservation.model_validate(
        _hashed_observation_payload(
            {
                "schema_version": "phase12-paper-clock-observation-v1",
                "is_open": is_open,
                "provider_timestamp_utc": provider_timestamp_utc,
                "next_open_utc": next_open_utc,
                "next_close_utc": next_close_utc,
            }
        )
    )


def build_instrument_observation(
    *,
    asset_id: UUID,
    exchange: str,
    status: str,
    active: bool,
    tradable: bool,
) -> PaperInstrumentObservation:
    return PaperInstrumentObservation.model_validate(
        _hashed_observation_payload(
            {
                "schema_version": "phase12-paper-instrument-observation-v1",
                "asset_id": asset_id,
                "symbol": "AAPL",
                "exchange": exchange,
                "status": status,
                "active": active,
                "tradable": tradable,
            }
        )
    )


def build_inventory_observation(
    *, inventory_kind: str, item_count: int, inventory_sha256: str
) -> PaperInventoryObservation:
    return PaperInventoryObservation.model_validate(
        _hashed_observation_payload(
            {
                "schema_version": "phase12-paper-inventory-observation-v1",
                "inventory_kind": inventory_kind,
                "item_count": item_count,
                "inventory_sha256": inventory_sha256,
            }
        )
    )


def build_quote_observation(
    *,
    event_time_utc: datetime,
    received_at_utc: datetime,
    bid_price_valid: bool,
    ask_price_valid: bool,
    non_crossed: bool,
) -> PaperQuoteObservation:
    age_seconds = Decimal(str((received_at_utc - event_time_utc).total_seconds()))
    return PaperQuoteObservation.model_validate(
        _hashed_observation_payload(
            {
                "schema_version": "phase12-paper-quote-observation-v1",
                "symbol": "AAPL",
                "feed": "iex",
                "event_time_utc": event_time_utc,
                "received_at_utc": received_at_utc,
                "age_seconds": age_seconds,
                "freshness_ttl_seconds": 60,
                "fresh": age_seconds <= Decimal("60"),
                "bid_price_valid": bid_price_valid,
                "ask_price_valid": ask_price_valid,
                "non_crossed": non_crossed,
            }
        )
    )


def build_inspection_evidence(
    *,
    ordinal: int,
    code: ReadinessInspectionCode,
    status: ReadinessInspectionStatus,
    external_request_performed: bool,
    request_started_at_utc: datetime | None,
    request_completed_at_utc: datetime | None,
    http_status: int | None = None,
    request_id: str | None = None,
    response_sha256: str | None = None,
    observation_sha256: str | None = None,
    failure_reason: str | None = None,
) -> ReadinessInspectionEvidence:
    payload = {
        "schema_version": "phase12-paper-shadow-inspection-v1",
        "ordinal": ordinal,
        "code": code,
        "status": status,
        "method": "GET",
        "external_request_performed": external_request_performed,
        "request_started_at_utc": request_started_at_utc,
        "request_completed_at_utc": request_completed_at_utc,
        "http_status": http_status,
        "request_id": request_id,
        "response_sha256": response_sha256,
        "observation_sha256": observation_sha256,
        "failure_reason": failure_reason,
    }
    return ReadinessInspectionEvidence.model_validate(
        {
            **payload,
            "inspection_sha256": domain_sha256(PHASE12_INSPECTION_HASH_DOMAIN, payload),
        }
    )


class MockReadinessScenario(StrEnum):
    READY = "READY"
    ACCOUNT_BLOCKED = "ACCOUNT_BLOCKED"
    CLOCK_CLOSED = "CLOCK_CLOSED"
    INSTRUMENT_INACTIVE = "INSTRUMENT_INACTIVE"
    POSITIONS_NONEMPTY = "POSITIONS_NONEMPTY"
    OPEN_ORDERS_NONEMPTY = "OPEN_ORDERS_NONEMPTY"
    QUOTE_STALE = "QUOTE_STALE"


class DeterministicMockPaperBrokerAdapter:
    """Frozen read-only proof adapter; it can never produce external readiness."""

    _BASE = datetime(2024, 1, 2, 15, 0, tzinfo=UTC)

    def __init__(self, scenario: MockReadinessScenario = MockReadinessScenario.READY) -> None:
        self._scenario = scenario

    @property
    def source_kind(self) -> ReadinessSourceKind:
        return ReadinessSourceKind.DETERMINISTIC_MOCK

    @property
    def transport_profile_sha256(self) -> str:
        return PHASE12_TRANSPORT_PROFILE_SHA256

    def _result(
        self,
        ordinal: int,
        code: ReadinessInspectionCode,
        observation: ReadinessObservation,
    ) -> PaperBrokerInspection:
        started = self._BASE + timedelta(milliseconds=ordinal * 10)
        completed = started + timedelta(milliseconds=1)
        evidence = build_inspection_evidence(
            ordinal=ordinal,
            code=code,
            status=ReadinessInspectionStatus.OBSERVED,
            external_request_performed=False,
            request_started_at_utc=started,
            request_completed_at_utc=completed,
            observation_sha256=observation.observation_sha256,
        )
        return PaperBrokerInspection(evidence=evidence, observation=observation)

    def inspect_account(self) -> PaperBrokerInspection:
        blocked = self._scenario is MockReadinessScenario.ACCOUNT_BLOCKED
        observation = build_account_observation(
            status="ACTIVE",
            account_blocked=blocked,
            trading_blocked=blocked,
            trade_suspended_by_user=False,
        )
        return self._result(1, ReadinessInspectionCode.ACCOUNT, observation)

    def inspect_clock(self) -> PaperBrokerInspection:
        observation = build_clock_observation(
            is_open=self._scenario is not MockReadinessScenario.CLOCK_CLOSED,
            provider_timestamp_utc=self._BASE,
            next_open_utc=self._BASE + timedelta(hours=17, minutes=30),
            next_close_utc=self._BASE + timedelta(hours=6),
        )
        return self._result(2, ReadinessInspectionCode.CLOCK, observation)

    def inspect_instrument(self) -> PaperBrokerInspection:
        active = self._scenario is not MockReadinessScenario.INSTRUMENT_INACTIVE
        observation = build_instrument_observation(
            asset_id=UUID("b0b6dd9d-8b9b-52ba-a39b-36bd3d5b2024"),
            exchange="NASDAQ",
            status="active" if active else "inactive",
            active=active,
            tradable=active,
        )
        return self._result(3, ReadinessInspectionCode.INSTRUMENT, observation)

    def inspect_positions(self) -> PaperBrokerInspection:
        count = 1 if self._scenario is MockReadinessScenario.POSITIONS_NONEMPTY else 0
        digest = domain_sha256(
            PHASE12_OBSERVATION_HASH_DOMAIN, {"inventory_kind": "POSITIONS", "count": count}
        )
        observation = build_inventory_observation(
            inventory_kind="POSITIONS", item_count=count, inventory_sha256=digest
        )
        return self._result(4, ReadinessInspectionCode.POSITIONS, observation)

    def inspect_open_orders(self) -> PaperBrokerInspection:
        count = 1 if self._scenario is MockReadinessScenario.OPEN_ORDERS_NONEMPTY else 0
        digest = domain_sha256(
            PHASE12_OBSERVATION_HASH_DOMAIN, {"inventory_kind": "OPEN_ORDERS", "count": count}
        )
        observation = build_inventory_observation(
            inventory_kind="OPEN_ORDERS", item_count=count, inventory_sha256=digest
        )
        return self._result(5, ReadinessInspectionCode.OPEN_ORDERS, observation)

    def inspect_latest_quote(self) -> PaperBrokerInspection:
        age = 61 if self._scenario is MockReadinessScenario.QUOTE_STALE else 1
        observation = build_quote_observation(
            event_time_utc=self._BASE - timedelta(seconds=age),
            received_at_utc=self._BASE,
            bid_price_valid=True,
            ask_price_valid=True,
            non_crossed=True,
        )
        return self._result(6, ReadinessInspectionCode.LATEST_QUOTE, observation)


__all__ = [
    "DeterministicMockPaperBrokerAdapter",
    "MockReadinessScenario",
    "PaperBrokerAdapter",
    "PaperBrokerInspection",
    "build_account_observation",
    "build_clock_observation",
    "build_inspection_evidence",
    "build_instrument_observation",
    "build_inventory_observation",
    "build_quote_observation",
]
