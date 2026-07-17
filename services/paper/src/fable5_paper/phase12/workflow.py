"""Single-flight orchestration for synchronous Phase 12 shadow-readiness evidence."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import UUID

from pydantic import ValidationError

from fable5_paper.phase12.adapters import PaperBrokerAdapter, PaperBrokerInspection
from fable5_paper.phase12.canonical import (
    PHASE12_ARTIFACT_HASH_DOMAIN,
    PHASE12_CHECK_HASH_DOMAIN,
    PHASE12_OBSERVATION_HASH_DOMAIN,
    PHASE12_RUN_NAMESPACE,
    PHASE12_TRANSPORT_PROFILE_SHA256,
    domain_sha256,
    identity,
)
from fable5_paper.phase12.contracts import (
    PHASE12_ARTIFACT_SCHEMA_VERSION,
    PHASE12_CHECK_ORDER,
    PHASE12_DISCLAIMER,
    PHASE12_INSPECTION_ORDER,
    PHASE12_READINESS_TTL_SECONDS,
    PaperAccountObservation,
    PaperClockObservation,
    PaperInstrumentObservation,
    PaperInventoryObservation,
    PaperQuoteObservation,
    PaperShadowReadinessArtifact,
    PaperShadowReadinessCheck,
    PaperShadowReadinessCreateRequest,
    ReadinessCheckCode,
    ReadinessCheckStatus,
    ReadinessInspectionEvidence,
    ReadinessInspectionStatus,
    ReadinessObservation,
    ReadinessOutcome,
    ReadinessSourceKind,
    readiness_request_fingerprint,
    validate_code_git_sha,
)


class PaperShadowReadinessNotFound(LookupError):
    pass


class PaperShadowReadinessWorkflowConflict(RuntimeError):
    pass


class PaperShadowReadinessCreation(Protocol):
    def find_by_idempotency_key(self, key: str) -> PaperShadowReadinessArtifact | None: ...

    def create_readiness(
        self, artifact: PaperShadowReadinessArtifact
    ) -> PaperShadowReadinessArtifact: ...


class PaperShadowReadinessStore(PaperShadowReadinessCreation, Protocol):
    def serialized_creation(
        self, key: str
    ) -> AbstractContextManager[PaperShadowReadinessCreation]: ...

    def get_readiness(self, readiness_assessment_id: UUID) -> PaperShadowReadinessArtifact: ...


def _system_utc_now() -> datetime:
    return datetime.now(UTC)


def _check(
    *,
    ordinal: int,
    code: ReadinessCheckCode,
    status: ReadinessCheckStatus,
    reason_code: str,
    evidence_sha256s: tuple[str, ...],
    observed_value: str | None,
    threshold_value: str | None,
) -> PaperShadowReadinessCheck:
    payload = {
        "schema_version": "phase12-paper-shadow-readiness-check-v1",
        "ordinal": ordinal,
        "code": code,
        "status": status,
        "reason_code": reason_code,
        "observed_value": observed_value,
        "threshold_value": threshold_value,
        "evidence_sha256s": tuple(sorted(set(evidence_sha256s))),
    }
    return PaperShadowReadinessCheck.model_validate(
        {**payload, "check_sha256": domain_sha256(PHASE12_CHECK_HASH_DOMAIN, payload)}
    )


def _status(
    observation: ReadinessObservation | None,
    passed: bool,
) -> ReadinessCheckStatus:
    if observation is None:
        return ReadinessCheckStatus.UNCOMPUTABLE
    return ReadinessCheckStatus.PASS if passed else ReadinessCheckStatus.BLOCKED


class PaperShadowReadinessWorkflow:
    def __init__(
        self,
        *,
        adapter: PaperBrokerAdapter,
        store: PaperShadowReadinessStore,
        phase12_code_version_git_sha: str | None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.adapter = adapter
        self.store = store
        self.phase12_code_version_git_sha = phase12_code_version_git_sha
        self.clock = clock or _system_utc_now

    def _require_code_sha(self) -> str:
        try:
            return validate_code_git_sha(self.phase12_code_version_git_sha)
        except ValueError as exc:
            raise PaperShadowReadinessWorkflowConflict(
                "phase12 code identity is unavailable"
            ) from exc

    def _run_inspections(
        self,
    ) -> tuple[
        tuple[ReadinessInspectionEvidence, ...],
        tuple[ReadinessObservation | None, ...],
    ]:
        methods = (
            self.adapter.inspect_account,
            self.adapter.inspect_clock,
            self.adapter.inspect_instrument,
            self.adapter.inspect_positions,
            self.adapter.inspect_open_orders,
            self.adapter.inspect_latest_quote,
        )
        evidences: list[ReadinessInspectionEvidence] = []
        observations: list[ReadinessObservation | None] = []
        blocked = False
        for ordinal, (code, method) in enumerate(
            zip(PHASE12_INSPECTION_ORDER, methods, strict=True), start=1
        ):
            if blocked:
                from fable5_paper.phase12.adapters import build_inspection_evidence

                evidences.append(
                    build_inspection_evidence(
                        ordinal=ordinal,
                        code=code,
                        status=ReadinessInspectionStatus.NOT_ATTEMPTED,
                        external_request_performed=False,
                        request_started_at_utc=None,
                        request_completed_at_utc=None,
                        failure_reason="prior_inspection_blocked",
                    )
                )
                observations.append(None)
                continue
            try:
                result = method()
            except Exception as exc:
                raise PaperShadowReadinessWorkflowConflict(
                    "paper-readiness adapter violated its sanitized contract"
                ) from exc
            if not isinstance(result, PaperBrokerInspection):
                raise PaperShadowReadinessWorkflowConflict(
                    "paper-readiness adapter returned an invalid inspection"
                )
            if result.evidence.ordinal != ordinal or result.evidence.code is not code:
                raise PaperShadowReadinessWorkflowConflict(
                    "paper-readiness adapter changed the frozen inspection registry"
                )
            if result.evidence.status is ReadinessInspectionStatus.NOT_ATTEMPTED:
                raise PaperShadowReadinessWorkflowConflict(
                    "invoked adapter method claimed it was not attempted"
                )
            evidences.append(result.evidence)
            observations.append(result.observation)
            blocked = result.evidence.status is ReadinessInspectionStatus.BLOCKED
        return tuple(evidences), tuple(observations)

    @staticmethod
    def _build_checks(
        *,
        source_kind: ReadinessSourceKind,
        inspections: tuple[ReadinessInspectionEvidence, ...],
        account: PaperAccountObservation | None,
        clock: PaperClockObservation | None,
        instrument: PaperInstrumentObservation | None,
        positions: PaperInventoryObservation | None,
        open_orders: PaperInventoryObservation | None,
        quote: PaperQuoteObservation | None,
    ) -> tuple[PaperShadowReadinessCheck, ...]:
        source_sha = domain_sha256(PHASE12_OBSERVATION_HASH_DOMAIN, {"source_kind": source_kind})
        account_pass = account is not None and (
            account.status == "ACTIVE"
            and not account.account_blocked
            and not account.trading_blocked
            and not account.trade_suspended_by_user
        )
        account_is_blocked = account is not None and (
            account.account_blocked or account.trading_blocked or account.trade_suspended_by_user
        )
        clock_pass = clock is not None and clock.is_open
        instrument_pass = instrument is not None and (
            instrument.active and instrument.tradable and instrument.status.casefold() == "active"
        )
        positions_pass = positions is not None and positions.item_count == 0
        orders_pass = open_orders is not None and open_orders.item_count == 0
        quote_pass = quote is not None and (
            quote.fresh
            and quote.bid_price_valid
            and quote.ask_price_valid
            and quote.non_crossed
            and quote.feed == "iex"
        )

        def evidence(ordinal: int, observation: ReadinessObservation | None) -> tuple[str, ...]:
            values = [inspections[ordinal - 1].inspection_sha256]
            if observation is not None:
                values.append(observation.observation_sha256)
            return tuple(values)

        entries = (
            _check(
                ordinal=1,
                code=ReadinessCheckCode.SOURCE_KIND_EXACT,
                status=ReadinessCheckStatus.PASS,
                reason_code="source_kind_explicit",
                evidence_sha256s=(source_sha,),
                observed_value=source_kind.value,
                threshold_value="DETERMINISTIC_MOCK|ALPACA_PAPER_READ_ONLY",
            ),
            _check(
                ordinal=2,
                code=ReadinessCheckCode.READ_ONLY_TRANSPORT_EXACT,
                status=ReadinessCheckStatus.PASS,
                reason_code="read_only_transport_exact",
                evidence_sha256s=(PHASE12_TRANSPORT_PROFILE_SHA256,),
                observed_value=PHASE12_TRANSPORT_PROFILE_SHA256,
                threshold_value=PHASE12_TRANSPORT_PROFILE_SHA256,
            ),
            _check(
                ordinal=3,
                code=ReadinessCheckCode.ACCOUNT_READY,
                status=_status(account, account_pass),
                reason_code=(
                    "account_ready"
                    if account_pass
                    else "account_observation_unavailable"
                    if account is None
                    else "account_not_ready"
                ),
                evidence_sha256s=evidence(1, account),
                observed_value=(
                    None
                    if account is None
                    else (f"status={account.status};blocked={account_is_blocked}")
                ),
                threshold_value="status=ACTIVE;blocked=false",
            ),
            _check(
                ordinal=4,
                code=ReadinessCheckCode.MARKET_CLOCK_OPEN,
                status=_status(clock, clock_pass),
                reason_code=(
                    "market_clock_open"
                    if clock_pass
                    else "clock_observation_unavailable"
                    if clock is None
                    else "market_clock_closed"
                ),
                evidence_sha256s=evidence(2, clock),
                observed_value=None if clock is None else str(clock.is_open).lower(),
                threshold_value="true",
            ),
            _check(
                ordinal=5,
                code=ReadinessCheckCode.INSTRUMENT_ACTIVE_TRADABLE,
                status=_status(instrument, instrument_pass),
                reason_code=(
                    "instrument_active_tradable"
                    if instrument_pass
                    else "instrument_observation_unavailable"
                    if instrument is None
                    else "instrument_not_active_tradable"
                ),
                evidence_sha256s=evidence(3, instrument),
                observed_value=(
                    None
                    if instrument is None
                    else f"active={instrument.active};tradable={instrument.tradable}"
                ),
                threshold_value="active=true;tradable=true",
            ),
            _check(
                ordinal=6,
                code=ReadinessCheckCode.POSITIONS_EMPTY,
                status=_status(positions, positions_pass),
                reason_code=(
                    "positions_empty"
                    if positions_pass
                    else "positions_observation_unavailable"
                    if positions is None
                    else "positions_not_empty"
                ),
                evidence_sha256s=evidence(4, positions),
                observed_value=None if positions is None else str(positions.item_count),
                threshold_value="0",
            ),
            _check(
                ordinal=7,
                code=ReadinessCheckCode.OPEN_ORDERS_EMPTY,
                status=_status(open_orders, orders_pass),
                reason_code=(
                    "open_orders_empty"
                    if orders_pass
                    else "open_orders_observation_unavailable"
                    if open_orders is None
                    else "open_orders_not_empty"
                ),
                evidence_sha256s=evidence(5, open_orders),
                observed_value=None if open_orders is None else str(open_orders.item_count),
                threshold_value="0",
            ),
            _check(
                ordinal=8,
                code=ReadinessCheckCode.IEX_QUOTE_FRESH_VALID,
                status=_status(quote, quote_pass),
                reason_code=(
                    "iex_quote_fresh_valid"
                    if quote_pass
                    else "quote_observation_unavailable"
                    if quote is None
                    else "iex_quote_stale_or_invalid"
                ),
                evidence_sha256s=evidence(6, quote),
                observed_value=(
                    None
                    if quote is None
                    else (
                        f"fresh={quote.fresh};valid="
                        f"{quote.bid_price_valid and quote.ask_price_valid and quote.non_crossed}"
                    )
                ),
                threshold_value="feed=iex;fresh=true;valid=true",
            ),
        )
        if tuple(item.code for item in entries) != PHASE12_CHECK_ORDER:
            raise AssertionError("Phase 12 check construction order drifted")
        return entries

    def _create_serialized(
        self,
        request: PaperShadowReadinessCreateRequest,
        creation: PaperShadowReadinessCreation,
        *,
        code_sha: str,
        request_fingerprint_sha256: str,
    ) -> PaperShadowReadinessArtifact:
        existing = creation.find_by_idempotency_key(request.readiness_idempotency_key)
        if existing is not None:
            if existing.request_fingerprint_sha256 != request_fingerprint_sha256:
                raise PaperShadowReadinessWorkflowConflict(
                    "readiness idempotency key is bound to a different fingerprint"
                )
            return existing

        inspections, observations = self._run_inspections()
        account, clock, instrument, positions, open_orders, quote = observations
        if account is not None and not isinstance(account, PaperAccountObservation):
            raise PaperShadowReadinessWorkflowConflict("account observation type is invalid")
        if clock is not None and not isinstance(clock, PaperClockObservation):
            raise PaperShadowReadinessWorkflowConflict("clock observation type is invalid")
        if instrument is not None and not isinstance(instrument, PaperInstrumentObservation):
            raise PaperShadowReadinessWorkflowConflict("instrument observation type is invalid")
        if positions is not None and not isinstance(positions, PaperInventoryObservation):
            raise PaperShadowReadinessWorkflowConflict("positions observation type is invalid")
        if open_orders is not None and not isinstance(open_orders, PaperInventoryObservation):
            raise PaperShadowReadinessWorkflowConflict("open-order observation type is invalid")
        if quote is not None and not isinstance(quote, PaperQuoteObservation):
            raise PaperShadowReadinessWorkflowConflict("quote observation type is invalid")

        checks = self._build_checks(
            source_kind=self.adapter.source_kind,
            inspections=inspections,
            account=account,
            clock=clock,
            instrument=instrument,
            positions=positions,
            open_orders=open_orders,
            quote=quote,
        )
        all_pass = all(item.status is ReadinessCheckStatus.PASS for item in checks)
        reason_codes: tuple[str, ...]
        if all_pass:
            outcome = (
                ReadinessOutcome.SHADOW_READY
                if self.adapter.source_kind is ReadinessSourceKind.ALPACA_PAPER_READ_ONLY
                else ReadinessOutcome.MOCK_PROOF_COMPLETE
            )
            reason_codes = (
                ("all_external_shadow_readiness_checks_passed",)
                if outcome is ReadinessOutcome.SHADOW_READY
                else ("all_mock_readiness_checks_passed",)
            )
        else:
            outcome = ReadinessOutcome.BLOCKED
            reason_codes = tuple(
                sorted(
                    {
                        item.reason_code
                        for item in checks
                        if item.status is not ReadinessCheckStatus.PASS
                    }
                )
            )
        attempted_times = [
            value
            for inspection in inspections
            for value in (
                inspection.request_started_at_utc,
                inspection.request_completed_at_utc,
            )
            if value is not None
        ]
        if not attempted_times:
            raise PaperShadowReadinessWorkflowConflict("assessment produced no bounded inspection")
        started = min(attempted_times)
        completed = max(attempted_times)
        payload = {
            "artifact_schema_version": PHASE12_ARTIFACT_SCHEMA_VERSION,
            "request_fingerprint_sha256": request_fingerprint_sha256,
            "readiness_idempotency_key": request.readiness_idempotency_key,
            "source_kind": self.adapter.source_kind,
            "transport_profile_sha256": self.adapter.transport_profile_sha256,
            "inspections": inspections,
            "account": account,
            "clock": clock,
            "instrument": instrument,
            "positions": positions,
            "open_orders": open_orders,
            "latest_quote": quote,
            "checks": checks,
            "outcome": outcome,
            "reason_codes": reason_codes,
            "phase12_code_version_git_sha": code_sha,
            "assessment_started_at_utc": started,
            "assessment_completed_at_utc": completed,
            "expires_at_utc": completed + timedelta(seconds=PHASE12_READINESS_TTL_SECONDS),
            "order_submission_authorized": False,
            "strategy_execution_eligible": False,
            "live_path_absent": True,
            "no_personalized_investment_advice": True,
            "no_real_performance_claimed": True,
            "disclaimer": PHASE12_DISCLAIMER,
        }
        candidate = PaperShadowReadinessArtifact.model_validate(
            {
                **payload,
                "readiness_assessment_id": identity(
                    PHASE12_RUN_NAMESPACE, request_fingerprint_sha256
                ),
                "artifact_sha256": domain_sha256(PHASE12_ARTIFACT_HASH_DOMAIN, payload),
            }
        )
        try:
            persisted = creation.create_readiness(candidate)
        except (TypeError, ValueError, ValidationError) as exc:
            raise PaperShadowReadinessWorkflowConflict(
                "immutable readiness evidence could not be persisted"
            ) from exc
        if persisted != candidate:
            raise PaperShadowReadinessWorkflowConflict(
                "persisted readiness evidence changed immutable content"
            )
        return persisted

    def create_readiness(
        self, request: PaperShadowReadinessCreateRequest
    ) -> PaperShadowReadinessArtifact:
        code_sha = self._require_code_sha()
        if self.adapter.transport_profile_sha256 != PHASE12_TRANSPORT_PROFILE_SHA256:
            raise PaperShadowReadinessWorkflowConflict(
                "adapter transport profile is not the frozen read-only profile"
            )
        if not isinstance(self.adapter.source_kind, ReadinessSourceKind):
            raise PaperShadowReadinessWorkflowConflict("adapter source kind is invalid")
        fingerprint = readiness_request_fingerprint(
            request=request,
            source_kind=self.adapter.source_kind,
            transport_profile_sha256=self.adapter.transport_profile_sha256,
            phase12_code_version_git_sha=code_sha,
        )
        with self.store.serialized_creation(request.readiness_idempotency_key) as creation:
            return self._create_serialized(
                request,
                creation,
                code_sha=code_sha,
                request_fingerprint_sha256=fingerprint,
            )

    def get_readiness(self, readiness_assessment_id: UUID) -> PaperShadowReadinessArtifact:
        return self.store.get_readiness(readiness_assessment_id)


__all__ = [
    "PaperShadowReadinessCreation",
    "PaperShadowReadinessNotFound",
    "PaperShadowReadinessStore",
    "PaperShadowReadinessWorkflow",
    "PaperShadowReadinessWorkflowConflict",
]
