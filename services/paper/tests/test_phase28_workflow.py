from __future__ import annotations

import traceback
from datetime import UTC, datetime, timedelta

import pytest
from fable5_paper.phase28.adapters import (
    DeterministicMockObservationAdapter,
    TransientBar,
    TransientBars,
    TransientQuote,
    TransientQuotes,
    TransientSnapshot,
    TransientSnapshots,
    build_inspection,
)
from fable5_paper.phase28.contracts import (
    InspectionCode,
    InspectionStatus,
    ObservationOutcome,
    PredicateCode,
    PredicateStatus,
)
from fable5_paper.phase28.workflow import (
    Phase28ObservationConflict,
    Phase28ObservationWorkflow,
)

GIT_SHA = "e9f4d99d8c1bc5c5b4ac615cf3592d5f0ae3113e"
BASE = datetime(2024, 1, 2, 15, 0, tzinfo=UTC)
OBSERVED_AT = BASE + timedelta(seconds=1)


def _run(adapter: DeterministicMockObservationAdapter):
    return Phase28ObservationWorkflow(
        adapter=adapter,
        code_version_git_sha=GIT_SHA,
        clock=lambda: OBSERVED_AT,
    ).run()


class _StaleBarAdapter(DeterministicMockObservationAdapter):
    def inspect_latest_bars(self):
        original = super().inspect_latest_bars()
        assert isinstance(original.payload, TransientBars)
        values = {
            symbol: TransientBar(
                event_time_utc=BASE - timedelta(seconds=121),
                open_price=value.open_price,
                close_price=value.close_price,
            )
            for symbol, value in original.payload.values.items()
        }
        return build_inspection(
            ordinal=4,
            code=InspectionCode.LATEST_BARS,
            status=InspectionStatus.OBSERVED,
            external_request_performed=False,
            started_at_utc=original.evidence.request_started_at_utc,
            completed_at_utc=original.evidence.request_completed_at_utc,
            payload=TransientBars(values),
        )


class _IncoherentQuoteAdapter(DeterministicMockObservationAdapter):
    quote_age_seconds = 90

    def inspect_latest_quotes(self):
        original = super().inspect_latest_quotes()
        assert isinstance(original.payload, TransientQuotes)
        values = {
            symbol: TransientQuote(
                event_time_utc=BASE - timedelta(seconds=self.quote_age_seconds),
                bid_price=value.bid_price,
                ask_price=value.ask_price,
            )
            for symbol, value in original.payload.values.items()
        }
        return build_inspection(
            ordinal=5,
            code=InspectionCode.LATEST_QUOTES,
            status=InspectionStatus.OBSERVED,
            external_request_performed=False,
            started_at_utc=original.evidence.request_started_at_utc,
            completed_at_utc=original.evidence.request_completed_at_utc,
            payload=TransientQuotes(values),
        )


class _QuoteBoundaryAdapter(_IncoherentQuoteAdapter):
    quote_age_seconds = 34


class _QuoteOverBoundaryAdapter(_IncoherentQuoteAdapter):
    quote_age_seconds = 35


class _BarBoundaryAdapter(DeterministicMockObservationAdapter):
    bar_age_seconds = 70

    def inspect_latest_bars(self):
        original = super().inspect_latest_bars()
        assert isinstance(original.payload, TransientBars)
        values = {
            symbol: TransientBar(
                event_time_utc=BASE - timedelta(seconds=self.bar_age_seconds),
                open_price=value.open_price,
                close_price=value.close_price,
            )
            for symbol, value in original.payload.values.items()
        }
        return build_inspection(
            ordinal=4,
            code=InspectionCode.LATEST_BARS,
            status=InspectionStatus.OBSERVED,
            external_request_performed=False,
            started_at_utc=original.evidence.request_started_at_utc,
            completed_at_utc=original.evidence.request_completed_at_utc,
            payload=TransientBars(values),
        )


class _BarOverBoundaryAdapter(_BarBoundaryAdapter):
    bar_age_seconds = 71


class _StaleSnapshotTradeAdapter(DeterministicMockObservationAdapter):
    def inspect_snapshots(self):
        original = super().inspect_snapshots()
        assert isinstance(original.payload, TransientSnapshots)
        values = {
            symbol: TransientSnapshot(
                latest_trade_time_utc=BASE - timedelta(seconds=121),
                latest_quote=value.latest_quote,
                minute_bar=value.minute_bar,
                daily_bar=value.daily_bar,
                previous_daily_bar=value.previous_daily_bar,
            )
            for symbol, value in original.payload.values.items()
        }
        return build_inspection(
            ordinal=6,
            code=InspectionCode.SNAPSHOTS,
            status=InspectionStatus.OBSERVED,
            external_request_performed=False,
            started_at_utc=original.evidence.request_started_at_utc,
            completed_at_utc=original.evidence.request_completed_at_utc,
            payload=TransientSnapshots(values),
        )


def test_stale_market_observation_is_insufficient_not_no_match() -> None:
    artifact = _run(_StaleBarAdapter())

    for symbol in artifact.symbols:
        predicate = next(
            item
            for item in symbol.predicates
            if item.code is PredicateCode.LATEST_BAR_VALID_AND_FRESH
        )
        assert predicate.status is PredicateStatus.INSUFFICIENT_DATA
        assert symbol.outcome is ObservationOutcome.INSUFFICIENT_DATA


def test_cross_endpoint_incoherence_is_insufficient_not_no_match() -> None:
    artifact = _run(_IncoherentQuoteAdapter())

    for symbol in artifact.symbols[:2]:
        predicate = next(
            item for item in symbol.predicates if item.code is PredicateCode.CROSS_ENDPOINT_COHERENT
        )
        assert predicate.status is PredicateStatus.INSUFFICIENT_DATA
        assert symbol.outcome is ObservationOutcome.INSUFFICIENT_DATA


@pytest.mark.parametrize(
    ("adapter", "expected"),
    [
        (_QuoteBoundaryAdapter(), PredicateStatus.MATCH),
        (_QuoteOverBoundaryAdapter(), PredicateStatus.INSUFFICIENT_DATA),
        (_BarBoundaryAdapter(), PredicateStatus.MATCH),
        (_BarOverBoundaryAdapter(), PredicateStatus.INSUFFICIENT_DATA),
    ],
)
def test_like_for_like_coherence_boundaries(
    adapter: DeterministicMockObservationAdapter,
    expected: PredicateStatus,
) -> None:
    artifact = _run(adapter)
    predicate = next(
        item
        for item in artifact.symbols[0].predicates
        if item.code is PredicateCode.CROSS_ENDPOINT_COHERENT
    )

    assert predicate.status is expected


def test_stale_snapshot_trade_is_insufficient_data() -> None:
    artifact = _run(_StaleSnapshotTradeAdapter())

    for symbol in artifact.symbols:
        predicate = next(
            item
            for item in symbol.predicates
            if item.code is PredicateCode.SNAPSHOT_COMPLETE_AND_FRESH
        )
        assert predicate.status is PredicateStatus.INSUFFICIENT_DATA
        assert symbol.outcome is ObservationOutcome.INSUFFICIENT_DATA


def test_valid_negative_direction_is_no_match() -> None:
    artifact = _run(DeterministicMockObservationAdapter())
    msft = artifact.symbols[1]
    predicate = next(
        item for item in msft.predicates if item.code is PredicateCode.SESSION_DIRECTION_POSITIVE
    )

    assert predicate.status is PredicateStatus.NO_MATCH
    assert msft.outcome is ObservationOutcome.NO_MATCH


class _CanaryFailureAdapter(DeterministicMockObservationAdapter):
    def inspect_asset_aapl(self):
        raise RuntimeError("SECRET_OR_RAW_PRICE_CANARY_193.77")


def test_adapter_exception_chain_and_rendered_traceback_are_sanitized() -> None:
    with pytest.raises(Phase28ObservationConflict) as caught:
        _run(_CanaryFailureAdapter())

    assert caught.value.__cause__ is None
    rendered = "".join(
        traceback.format_exception(type(caught.value), caught.value, caught.value.__traceback__)
    )
    assert "SECRET_OR_RAW_PRICE_CANARY_193.77" not in rendered


def test_mock_never_constructs_a_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    def blocked(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise AssertionError("socket construction is forbidden")

    monkeypatch.setattr("http.client.HTTPSConnection", blocked)
    artifact = _run(DeterministicMockObservationAdapter())

    assert all(not item.external_request_performed for item in artifact.inspections)
