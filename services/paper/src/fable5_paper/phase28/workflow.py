"""Deterministic, single-flight Phase 28 observation workflow."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from fable5_paper.phase28.adapters import (
    ObservationInspection,
    ObservationOnlyAdapter,
    TransientAsset,
    TransientBar,
    TransientBars,
    TransientQuote,
    TransientQuotes,
    TransientSnapshot,
    TransientSnapshots,
    build_inspection,
)
from fable5_paper.phase28.canonical import (
    PHASE28_BAR_SNAPSHOT_ROLLOVER_TOLERANCE_SECONDS,
    PHASE28_CONFIG_SHA256,
    PHASE28_CURRENCY,
    PHASE28_EXACT_USE_REVIEW_EXPIRES_AT_UTC,
    PHASE28_EXACT_USE_REVIEW_SHA256,
    PHASE28_FEED,
    PHASE28_FRESHNESS_TTL_SECONDS,
    PHASE28_NOTICE,
    PHASE28_QUOTE_SNAPSHOT_TOLERANCE_SECONDS,
    PHASE28_SIGNAL_REGISTRY_SHA256,
    PHASE28_TRANSPORT_PROFILE_SHA256,
    PHASE28_UNIVERSE,
    PHASE28_UNIVERSE_SHA256,
    domain_sha256,
    evidence_id,
    observation_snapshot_id,
)
from fable5_paper.phase28.contracts import (
    AlpacaIexObservationEvidence,
    InspectionCode,
    InspectionStatus,
    ObservationAuthority,
    ObservationOutcome,
    PredicateCode,
    PredicateEvidence,
    PredicateStatus,
    SymbolObservationEvidence,
    validate_code_git_sha,
)


class Phase28ObservationConflict(RuntimeError):
    """A sanitized fail-closed workflow error."""


def _system_utc_now() -> datetime:
    return datetime.now(UTC)


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise Phase28ObservationConflict("observation timestamp is invalid")
    return value.astimezone(UTC)


def _age_is_fresh(event_time: datetime, observed_at: datetime) -> bool:
    age = (observed_at - _utc(event_time)).total_seconds()
    return 0 <= age <= PHASE28_FRESHNESS_TTL_SECONDS


def _valid_bar(value: TransientBar | None) -> bool:
    return bool(
        value is not None
        and value.open_price.is_finite()
        and value.close_price.is_finite()
        and value.open_price > 0
        and value.close_price > 0
    )


def _valid_quote(value: TransientQuote | None) -> bool:
    return bool(
        value is not None
        and value.bid_price.is_finite()
        and value.ask_price.is_finite()
        and value.bid_price > 0
        and value.ask_price > 0
        and value.ask_price >= value.bid_price
    )


def _predicate(
    *,
    ordinal: int,
    code: PredicateCode,
    status: PredicateStatus,
    reason_code: str,
) -> PredicateEvidence:
    payload = {
        "schema_version": "phase28-observation-predicate-v1",
        "ordinal": ordinal,
        "code": code,
        "status": status,
        "reason_code": reason_code,
    }
    return PredicateEvidence.model_validate(
        {
            **payload,
            "predicate_sha256": domain_sha256("phase28-observation-predicate-v1", payload),
        }
    )


def _state(value: bool | None) -> PredicateStatus:
    if value is None:
        return PredicateStatus.INSUFFICIENT_DATA
    return PredicateStatus.MATCH if value else PredicateStatus.NO_MATCH


def _quality(value: bool | None) -> PredicateStatus:
    return PredicateStatus.MATCH if value is True else PredicateStatus.INSUFFICIENT_DATA


def _symbol_evidence(
    *,
    symbol: str,
    observed_at: datetime,
    asset: TransientAsset | None,
    bar: TransientBar | None,
    quote: TransientQuote | None,
    snapshot: TransientSnapshot | None,
) -> SymbolObservationEvidence:
    asset_present = asset is not None and asset.symbol == symbol
    if asset_present and asset is not None:
        asset_active = asset.active and asset.status == "active"
        asset_tradable = asset.tradable
    else:
        asset_active = None
        asset_tradable = None

    bar_valid = _valid_bar(bar)
    bar_fresh = bar_valid and bar is not None and _age_is_fresh(bar.event_time_utc, observed_at)
    bar_state = bar_fresh if bar_valid else None

    quote_valid = _valid_quote(quote)
    quote_fresh = (
        quote_valid and quote is not None and _age_is_fresh(quote.event_time_utc, observed_at)
    )
    quote_state = quote_fresh if quote_valid else None

    snapshot_complete = bool(
        snapshot is not None
        and snapshot.latest_trade_time_utc is not None
        and _valid_quote(snapshot.latest_quote)
        and _valid_bar(snapshot.minute_bar)
        and _valid_bar(snapshot.daily_bar)
        and _valid_bar(snapshot.previous_daily_bar)
    )
    snapshot_fresh = bool(
        snapshot_complete
        and snapshot is not None
        and snapshot.latest_trade_time_utc is not None
        and snapshot.latest_quote is not None
        and snapshot.minute_bar is not None
        and _age_is_fresh(snapshot.latest_trade_time_utc, observed_at)
        and _age_is_fresh(snapshot.latest_quote.event_time_utc, observed_at)
        and _age_is_fresh(snapshot.minute_bar.event_time_utc, observed_at)
    )
    snapshot_state = snapshot_fresh if snapshot_complete else None

    coherent: bool | None = None
    if (
        bar_state
        and quote_state
        and snapshot_state
        and bar is not None
        and quote is not None
        and snapshot is not None
        and snapshot.minute_bar is not None
        and snapshot.latest_quote is not None
    ):
        bar_gap = abs(
            (_utc(bar.event_time_utc) - _utc(snapshot.minute_bar.event_time_utc)).total_seconds()
        )
        quote_gap = abs(
            (
                _utc(quote.event_time_utc) - _utc(snapshot.latest_quote.event_time_utc)
            ).total_seconds()
        )
        coherent = (
            bar_gap <= PHASE28_BAR_SNAPSHOT_ROLLOVER_TOLERANCE_SECONDS
            and quote_gap <= PHASE28_QUOTE_SNAPSHOT_TOLERANCE_SECONDS
        )

    session_positive: bool | None = None
    intraday_positive: bool | None = None
    if snapshot_complete and snapshot is not None:
        assert (
            snapshot.daily_bar is not None
            and snapshot.previous_daily_bar is not None
            and snapshot.minute_bar is not None
        )
        session_positive = snapshot.daily_bar.close_price > snapshot.previous_daily_bar.close_price
        intraday_positive = snapshot.minute_bar.close_price > snapshot.daily_bar.open_price

    states = (
        (PredicateCode.ASSET_ACTIVE, _state(asset_active), "asset_active"),
        (PredicateCode.ASSET_TRADABLE, _state(asset_tradable), "asset_tradable"),
        (
            PredicateCode.LATEST_BAR_VALID_AND_FRESH,
            _quality(bar_state),
            "latest_bar_valid_and_fresh",
        ),
        (
            PredicateCode.LATEST_QUOTE_VALID_AND_FRESH,
            _quality(quote_state),
            "latest_quote_valid_and_fresh",
        ),
        (
            PredicateCode.SNAPSHOT_COMPLETE_AND_FRESH,
            _quality(snapshot_state),
            "snapshot_complete_and_fresh",
        ),
        (
            PredicateCode.CROSS_ENDPOINT_COHERENT,
            _quality(coherent),
            "cross_endpoint_coherent",
        ),
        (
            PredicateCode.SESSION_DIRECTION_POSITIVE,
            _state(session_positive),
            "session_direction_positive",
        ),
        (
            PredicateCode.INTRADAY_DIRECTION_POSITIVE,
            _state(intraday_positive),
            "intraday_direction_positive",
        ),
    )
    predicates = tuple(
        _predicate(ordinal=ordinal, code=code, status=status, reason_code=reason)
        for ordinal, (code, status, reason) in enumerate(states, start=1)
    )
    statuses = {item.status for item in predicates}
    outcome = (
        ObservationOutcome.INSUFFICIENT_DATA
        if PredicateStatus.INSUFFICIENT_DATA in statuses
        else (
            ObservationOutcome.MATCH
            if statuses == {PredicateStatus.MATCH}
            else ObservationOutcome.NO_MATCH
        )
    )
    payload = {
        "schema_version": "phase28-symbol-observation-v1",
        "symbol": symbol,
        "outcome": outcome,
        "predicates": predicates,
    }
    return SymbolObservationEvidence.model_validate(
        {
            **payload,
            "symbol_observation_sha256": domain_sha256("phase28-symbol-observation-v1", payload),
        }
    )


class Phase28ObservationWorkflow:
    """Evaluate fixed observation predicates; it has no storage or execution dependency."""

    def __init__(
        self,
        *,
        adapter: ObservationOnlyAdapter,
        code_version_git_sha: str | None,
        clock: Callable[[], datetime] = _system_utc_now,
    ) -> None:
        self._adapter = adapter
        self._code_version_git_sha = code_version_git_sha
        self._clock = clock

    def _inspections(self) -> tuple[ObservationInspection, ...]:
        methods = (
            self._adapter.inspect_asset_aapl,
            self._adapter.inspect_asset_msft,
            self._adapter.inspect_asset_spy,
            self._adapter.inspect_latest_bars,
            self._adapter.inspect_latest_quotes,
            self._adapter.inspect_snapshots,
        )
        results: list[ObservationInspection] = []
        blocked = False
        for ordinal, (code, method) in enumerate(
            zip(InspectionCode, methods, strict=True), start=1
        ):
            if blocked:
                now = _utc(self._clock())
                results.append(
                    build_inspection(
                        ordinal=ordinal,
                        code=code,
                        status=InspectionStatus.NOT_ATTEMPTED,
                        external_request_performed=False,
                        started_at_utc=now,
                        completed_at_utc=now,
                        payload=None,
                        failure_reason="prior_inspection_blocked",
                    )
                )
                continue
            try:
                result = method()
            except Exception:
                raise Phase28ObservationConflict(
                    "observation adapter violated its sanitized contract"
                ) from None
            if (
                not isinstance(result, ObservationInspection)
                or result.evidence.ordinal != ordinal
                or result.evidence.code is not code
                or result.evidence.status is InspectionStatus.NOT_ATTEMPTED
            ):
                raise Phase28ObservationConflict("inspection registry changed")
            results.append(result)
            blocked = result.evidence.status is InspectionStatus.BLOCKED
        return tuple(results)

    def run(self) -> AlpacaIexObservationEvidence:
        code_sha = validate_code_git_sha(self._code_version_git_sha)
        if self._adapter.transport_profile_sha256 != PHASE28_TRANSPORT_PROFILE_SHA256:
            raise Phase28ObservationConflict("transport profile changed")
        inspections = self._inspections()
        observed_at = _utc(self._clock())

        assets: dict[str, TransientAsset] = {}
        for result in inspections[:3]:
            if isinstance(result.payload, TransientAsset):
                assets[result.payload.symbol] = result.payload
        bars = (
            inspections[3].payload.values
            if isinstance(inspections[3].payload, TransientBars)
            else {}
        )
        quotes = (
            inspections[4].payload.values
            if isinstance(inspections[4].payload, TransientQuotes)
            else {}
        )
        snapshots = (
            inspections[5].payload.values
            if isinstance(inspections[5].payload, TransientSnapshots)
            else {}
        )
        symbols = tuple(
            _symbol_evidence(
                symbol=symbol,
                observed_at=observed_at,
                asset=assets.get(symbol),
                bar=bars.get(symbol),
                quote=quotes.get(symbol),
                snapshot=snapshots.get(symbol),
            )
            for symbol in PHASE28_UNIVERSE
        )
        payload = {
            "schema_version": "phase28-alpaca-iex-observation-evidence-v1",
            "observation_snapshot_kind": "SANITIZED_OBSERVATION_METADATA_ONLY",
            "source_kind": self._adapter.source_kind,
            "feed": PHASE28_FEED,
            "currency": PHASE28_CURRENCY,
            "universe": PHASE28_UNIVERSE,
            "config_sha256": PHASE28_CONFIG_SHA256,
            "universe_sha256": PHASE28_UNIVERSE_SHA256,
            "signal_registry_sha256": PHASE28_SIGNAL_REGISTRY_SHA256,
            "transport_profile_sha256": PHASE28_TRANSPORT_PROFILE_SHA256,
            "code_version_git_sha": code_sha,
            "random_seed": 0,
            "trial_count": 0,
            "forecast_horizon": "NONE_OBSERVATION_ONLY",
            "exact_use_review_confirmed_for_external_run": (
                self._adapter.exact_use_review_confirmed_for_external_run
            ),
            "exact_use_review_sha256": PHASE28_EXACT_USE_REVIEW_SHA256,
            "exact_use_review_revalidation_deadline_utc": (PHASE28_EXACT_USE_REVIEW_EXPIRES_AT_UTC),
            "observed_at_utc": observed_at,
            "inspections": tuple(item.evidence for item in inspections),
            "symbols": symbols,
            "authority": ObservationAuthority(
                provider_payload_persisted=False,
                raw_price_persisted=False,
                research_qualified=False,
                strategy_execution_eligible=False,
                order_submission_authorized=False,
                live_path_absent=True,
                simulated_paper_only=True,
                no_personalized_investment_advice=True,
                no_real_performance_claimed=True,
            ),
            "notice": PHASE28_NOTICE,
        }
        snapshot_payload = {
            "source_kind": self._adapter.source_kind,
            "observed_at_utc": observed_at,
            "inspection_sha256s": tuple(item.evidence.inspection_sha256 for item in inspections),
            "config_sha256": PHASE28_CONFIG_SHA256,
        }
        snapshot_hash = domain_sha256("phase28-sanitized-observation-snapshot-v1", snapshot_payload)
        payload["observation_snapshot_sha256"] = snapshot_hash
        payload["observation_snapshot_id"] = observation_snapshot_id(snapshot_hash)
        digest = domain_sha256("phase28-alpaca-iex-evidence-v1", payload)
        return AlpacaIexObservationEvidence.model_validate(
            {**payload, "evidence_id": evidence_id(digest), "evidence_sha256": digest}
        )


__all__ = ["Phase28ObservationConflict", "Phase28ObservationWorkflow"]
