"""Strict hash-bound contracts for Phase 12 external-paper shadow readiness."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from fable5_paper.phase12.canonical import (
    PHASE12_ARTIFACT_HASH_DOMAIN,
    PHASE12_CHECK_HASH_DOMAIN,
    PHASE12_INSPECTION_HASH_DOMAIN,
    PHASE12_OBSERVATION_HASH_DOMAIN,
    PHASE12_REQUEST_HASH_DOMAIN,
    PHASE12_RUN_NAMESPACE,
    PHASE12_TRANSPORT_PROFILE_SHA256,
    domain_sha256,
    identity,
)

SHA256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
GitSHA = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]
Identifier = Annotated[
    str,
    StringConstraints(min_length=1, max_length=256, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:/-]*$"),
]
IdempotencyKey = Annotated[
    str,
    StringConstraints(min_length=8, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$"),
]
RequestId = Annotated[
    str,
    StringConstraints(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$"),
]

PHASE12_ARTIFACT_SCHEMA_VERSION: Literal["phase12-paper-shadow-readiness-v1"] = (
    "phase12-paper-shadow-readiness-v1"
)
PHASE12_CHECK_SCHEMA_VERSION: Literal["phase12-paper-shadow-readiness-check-v1"] = (
    "phase12-paper-shadow-readiness-check-v1"
)
PHASE12_INSPECTION_SCHEMA_VERSION: Literal["phase12-paper-shadow-inspection-v1"] = (
    "phase12-paper-shadow-inspection-v1"
)
PHASE12_READINESS_TTL_SECONDS: Literal[60] = 60
PHASE12_DISCLAIMER: Literal[
    "PAPER ONLY shadow-readiness evidence; no order submission, strategy execution, real "
    "performance claim, or personalized investment advice."
] = (
    "PAPER ONLY shadow-readiness evidence; no order submission, strategy execution, real "
    "performance claim, or personalized investment advice."
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")


def _utc(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value.astimezone(UTC)


def _observation_hash(payload: dict[str, object]) -> str:
    return domain_sha256(PHASE12_OBSERVATION_HASH_DOMAIN, payload)


class ReadinessSourceKind(StrEnum):
    DETERMINISTIC_MOCK = "DETERMINISTIC_MOCK"
    ALPACA_PAPER_READ_ONLY = "ALPACA_PAPER_READ_ONLY"


class ReadinessOutcome(StrEnum):
    MOCK_PROOF_COMPLETE = "MOCK_PROOF_COMPLETE"
    SHADOW_READY = "SHADOW_READY"
    BLOCKED = "BLOCKED"


class ReadinessCheckStatus(StrEnum):
    PASS = "PASS"
    BLOCKED = "BLOCKED"
    UNCOMPUTABLE = "UNCOMPUTABLE"


class ReadinessCheckCode(StrEnum):
    SOURCE_KIND_EXACT = "SOURCE_KIND_EXACT"
    READ_ONLY_TRANSPORT_EXACT = "READ_ONLY_TRANSPORT_EXACT"
    ACCOUNT_READY = "ACCOUNT_READY"
    MARKET_CLOCK_OPEN = "MARKET_CLOCK_OPEN"
    INSTRUMENT_ACTIVE_TRADABLE = "INSTRUMENT_ACTIVE_TRADABLE"
    POSITIONS_EMPTY = "POSITIONS_EMPTY"
    OPEN_ORDERS_EMPTY = "OPEN_ORDERS_EMPTY"
    IEX_QUOTE_FRESH_VALID = "IEX_QUOTE_FRESH_VALID"


PHASE12_CHECK_ORDER: tuple[ReadinessCheckCode, ...] = tuple(ReadinessCheckCode)


class ReadinessInspectionCode(StrEnum):
    ACCOUNT = "ACCOUNT"
    CLOCK = "CLOCK"
    INSTRUMENT = "INSTRUMENT"
    POSITIONS = "POSITIONS"
    OPEN_ORDERS = "OPEN_ORDERS"
    LATEST_QUOTE = "LATEST_QUOTE"


PHASE12_INSPECTION_ORDER: tuple[ReadinessInspectionCode, ...] = tuple(ReadinessInspectionCode)


class ReadinessInspectionStatus(StrEnum):
    OBSERVED = "OBSERVED"
    BLOCKED = "BLOCKED"
    NOT_ATTEMPTED = "NOT_ATTEMPTED"


class PaperShadowReadinessCreateRequest(StrictModel):
    readiness_idempotency_key: IdempotencyKey


class ReadinessInspectionEvidence(StrictModel):
    schema_version: Literal["phase12-paper-shadow-inspection-v1"] = (
        PHASE12_INSPECTION_SCHEMA_VERSION
    )
    ordinal: int = Field(ge=1, le=6)
    code: ReadinessInspectionCode
    status: ReadinessInspectionStatus
    method: Literal["GET"] = "GET"
    external_request_performed: bool
    request_started_at_utc: datetime | None = None
    request_completed_at_utc: datetime | None = None
    http_status: int | None = Field(default=None, ge=100, le=599)
    request_id: RequestId | None = None
    response_sha256: SHA256 | None = None
    observation_sha256: SHA256 | None = None
    failure_reason: Identifier | None = None
    inspection_sha256: SHA256

    @field_validator("request_started_at_utc", "request_completed_at_utc")
    @classmethod
    def normalize_times(cls, value: datetime | None, info: object) -> datetime | None:
        return (
            None if value is None else _utc(value, getattr(info, "field_name", "inspection time"))
        )

    @model_validator(mode="after")
    def validate_inspection(self) -> Self:
        times_present = self.request_started_at_utc is not None and (
            self.request_completed_at_utc is not None
        )
        if (self.request_started_at_utc is None) is not (self.request_completed_at_utc is None):
            raise ValueError("inspection request times must be jointly present")
        if times_present and self.request_started_at_utc > self.request_completed_at_utc:  # type: ignore[operator]
            raise ValueError("inspection request chronology is invalid")
        if self.status is ReadinessInspectionStatus.NOT_ATTEMPTED:
            if (
                times_present
                or self.external_request_performed
                or any(
                    value is not None
                    for value in (
                        self.http_status,
                        self.request_id,
                        self.response_sha256,
                        self.observation_sha256,
                    )
                )
            ):
                raise ValueError("not-attempted inspection cannot claim request evidence")
            if self.failure_reason is None:
                raise ValueError("not-attempted inspection requires a sanitized reason")
        else:
            if not times_present:
                raise ValueError("attempted inspection requires bounded request times")
            if self.status is ReadinessInspectionStatus.OBSERVED:
                if self.observation_sha256 is None or self.failure_reason is not None:
                    raise ValueError("observed inspection requires one observation and no failure")
            elif self.failure_reason is None or self.observation_sha256 is not None:
                raise ValueError(
                    "blocked inspection requires one sanitized failure and no observation"
                )
        if self.external_request_performed:
            if self.status is ReadinessInspectionStatus.OBSERVED and (
                self.http_status != 200 or self.response_sha256 is None
            ):
                raise ValueError("observed external inspection requires a hashed HTTP 200 response")
        elif any(
            value is not None for value in (self.http_status, self.request_id, self.response_sha256)
        ):
            raise ValueError("non-external inspection cannot claim HTTP evidence")
        payload = self.model_dump(mode="python", exclude={"inspection_sha256"})
        if self.inspection_sha256 != domain_sha256(PHASE12_INSPECTION_HASH_DOMAIN, payload):
            raise ValueError("inspection hash must bind its complete preimage")
        return self


class PaperAccountObservation(StrictModel):
    schema_version: Literal["phase12-paper-account-observation-v1"] = (
        "phase12-paper-account-observation-v1"
    )
    observation_sha256: SHA256
    status: Identifier
    account_blocked: bool
    trading_blocked: bool
    trade_suspended_by_user: bool

    @model_validator(mode="after")
    def validate_hash(self) -> Self:
        payload = self.model_dump(mode="python", exclude={"observation_sha256"})
        if self.observation_sha256 != _observation_hash(payload):
            raise ValueError("account observation hash must bind its complete preimage")
        return self


class PaperClockObservation(StrictModel):
    schema_version: Literal["phase12-paper-clock-observation-v1"] = (
        "phase12-paper-clock-observation-v1"
    )
    observation_sha256: SHA256
    is_open: bool
    provider_timestamp_utc: datetime
    next_open_utc: datetime
    next_close_utc: datetime

    @field_validator("provider_timestamp_utc", "next_open_utc", "next_close_utc")
    @classmethod
    def normalize_times(cls, value: datetime, info: object) -> datetime:
        return _utc(value, getattr(info, "field_name", "clock time"))

    @model_validator(mode="after")
    def validate_observation(self) -> Self:
        if self.next_open_utc == self.next_close_utc:
            raise ValueError("market clock boundaries must differ")
        payload = self.model_dump(mode="python", exclude={"observation_sha256"})
        if self.observation_sha256 != _observation_hash(payload):
            raise ValueError("clock observation hash must bind its complete preimage")
        return self


class PaperInstrumentObservation(StrictModel):
    schema_version: Literal["phase12-paper-instrument-observation-v1"] = (
        "phase12-paper-instrument-observation-v1"
    )
    observation_sha256: SHA256
    asset_id: UUID
    symbol: Literal["AAPL"] = "AAPL"
    exchange: Identifier
    status: Identifier
    active: bool
    tradable: bool

    @model_validator(mode="after")
    def validate_hash(self) -> Self:
        payload = self.model_dump(mode="python", exclude={"observation_sha256"})
        if self.observation_sha256 != _observation_hash(payload):
            raise ValueError("instrument observation hash must bind its complete preimage")
        return self


class PaperInventoryObservation(StrictModel):
    schema_version: Literal["phase12-paper-inventory-observation-v1"] = (
        "phase12-paper-inventory-observation-v1"
    )
    observation_sha256: SHA256
    inventory_kind: Literal["POSITIONS", "OPEN_ORDERS"]
    item_count: int = Field(ge=0, le=100_000)
    inventory_sha256: SHA256

    @model_validator(mode="after")
    def validate_hash(self) -> Self:
        payload = self.model_dump(mode="python", exclude={"observation_sha256"})
        if self.observation_sha256 != _observation_hash(payload):
            raise ValueError("inventory observation hash must bind its complete preimage")
        return self


class PaperQuoteObservation(StrictModel):
    schema_version: Literal["phase12-paper-quote-observation-v1"] = (
        "phase12-paper-quote-observation-v1"
    )
    observation_sha256: SHA256
    symbol: Literal["AAPL"] = "AAPL"
    feed: Literal["iex"] = "iex"
    event_time_utc: datetime
    received_at_utc: datetime
    age_seconds: Decimal = Field(ge=Decimal("0"), le=Decimal("86400"))
    freshness_ttl_seconds: Literal[60] = 60
    fresh: bool
    bid_price_valid: bool
    ask_price_valid: bool
    non_crossed: bool

    @field_validator("event_time_utc", "received_at_utc")
    @classmethod
    def normalize_times(cls, value: datetime, info: object) -> datetime:
        return _utc(value, getattr(info, "field_name", "quote time"))

    @model_validator(mode="after")
    def validate_observation(self) -> Self:
        if not self.age_seconds.is_finite():
            raise ValueError("quote age must be finite")
        expected_age = Decimal(str((self.received_at_utc - self.event_time_utc).total_seconds()))
        if self.age_seconds != expected_age:
            raise ValueError("quote age must exactly bind provider and receipt timestamps")
        if self.fresh is not (self.age_seconds <= Decimal(PHASE12_READINESS_TTL_SECONDS)):
            raise ValueError("quote freshness must use the frozen Phase 12 TTL")
        payload = self.model_dump(mode="python", exclude={"observation_sha256"})
        if self.observation_sha256 != _observation_hash(payload):
            raise ValueError("quote observation hash must bind its complete preimage")
        return self


ReadinessObservation = (
    PaperAccountObservation
    | PaperClockObservation
    | PaperInstrumentObservation
    | PaperInventoryObservation
    | PaperQuoteObservation
)


class PaperShadowReadinessCheck(StrictModel):
    schema_version: Literal["phase12-paper-shadow-readiness-check-v1"] = (
        PHASE12_CHECK_SCHEMA_VERSION
    )
    ordinal: int = Field(ge=1, le=len(PHASE12_CHECK_ORDER))
    code: ReadinessCheckCode
    status: ReadinessCheckStatus
    reason_code: Identifier
    observed_value: str | None = Field(default=None, max_length=500)
    threshold_value: str | None = Field(default=None, max_length=500)
    evidence_sha256s: tuple[SHA256, ...] = Field(min_length=1)
    check_sha256: SHA256

    @model_validator(mode="after")
    def validate_check(self) -> Self:
        if self.evidence_sha256s != tuple(sorted(set(self.evidence_sha256s))):
            raise ValueError("check evidence hashes must be sorted and unique")
        payload = self.model_dump(mode="python", exclude={"check_sha256"})
        if self.check_sha256 != domain_sha256(PHASE12_CHECK_HASH_DOMAIN, payload):
            raise ValueError("readiness check hash must bind its complete preimage")
        return self


def readiness_request_fingerprint(
    *,
    request: PaperShadowReadinessCreateRequest,
    source_kind: ReadinessSourceKind,
    transport_profile_sha256: str,
    phase12_code_version_git_sha: str,
) -> str:
    return domain_sha256(
        PHASE12_REQUEST_HASH_DOMAIN,
        {
            "readiness_idempotency_key": request.readiness_idempotency_key,
            "source_kind": source_kind,
            "transport_profile_sha256": transport_profile_sha256,
            "phase12_code_version_git_sha": phase12_code_version_git_sha,
        },
    )


class PaperShadowReadinessArtifact(StrictModel):
    readiness_assessment_id: UUID
    artifact_schema_version: Literal["phase12-paper-shadow-readiness-v1"]
    artifact_sha256: SHA256
    request_fingerprint_sha256: SHA256
    readiness_idempotency_key: IdempotencyKey
    source_kind: ReadinessSourceKind
    transport_profile_sha256: SHA256
    inspections: tuple[ReadinessInspectionEvidence, ...] = Field(min_length=6, max_length=6)
    account: PaperAccountObservation | None
    clock: PaperClockObservation | None
    instrument: PaperInstrumentObservation | None
    positions: PaperInventoryObservation | None
    open_orders: PaperInventoryObservation | None
    latest_quote: PaperQuoteObservation | None
    checks: tuple[PaperShadowReadinessCheck, ...] = Field(
        min_length=len(PHASE12_CHECK_ORDER), max_length=len(PHASE12_CHECK_ORDER)
    )
    outcome: ReadinessOutcome
    reason_codes: tuple[Identifier, ...] = Field(min_length=1)
    phase12_code_version_git_sha: GitSHA
    assessment_started_at_utc: datetime
    assessment_completed_at_utc: datetime
    expires_at_utc: datetime
    order_submission_authorized: Literal[False]
    strategy_execution_eligible: Literal[False]
    live_path_absent: Literal[True]
    no_personalized_investment_advice: Literal[True]
    no_real_performance_claimed: Literal[True]
    disclaimer: Literal[
        "PAPER ONLY shadow-readiness evidence; no order submission, strategy execution, real "
        "performance claim, or personalized investment advice."
    ]

    @field_validator("assessment_started_at_utc", "assessment_completed_at_utc", "expires_at_utc")
    @classmethod
    def normalize_times(cls, value: datetime, info: object) -> datetime:
        return _utc(value, getattr(info, "field_name", "assessment time"))

    @model_validator(mode="after")
    def validate_artifact(self) -> Self:
        if self.transport_profile_sha256 != PHASE12_TRANSPORT_PROFILE_SHA256:
            raise ValueError("transport profile must be the sole frozen Phase 12 profile")
        if self.assessment_started_at_utc > self.assessment_completed_at_utc:
            raise ValueError("assessment chronology is invalid")
        if self.expires_at_utc != self.assessment_completed_at_utc + timedelta(
            seconds=PHASE12_READINESS_TTL_SECONDS
        ):
            raise ValueError("readiness expiry must use the exact frozen TTL")
        if (
            tuple(item.ordinal for item in self.inspections) != tuple(range(1, 7))
            or tuple(item.code for item in self.inspections) != PHASE12_INSPECTION_ORDER
        ):
            raise ValueError("artifact must bind the exact ordered inspection registry")
        if (
            tuple(item.ordinal for item in self.checks)
            != tuple(range(1, len(PHASE12_CHECK_ORDER) + 1))
            or tuple(item.code for item in self.checks) != PHASE12_CHECK_ORDER
        ):
            raise ValueError("artifact must bind the exact ordered readiness checks")

        observations: tuple[ReadinessObservation | None, ...] = (
            self.account,
            self.clock,
            self.instrument,
            self.positions,
            self.open_orders,
            self.latest_quote,
        )
        for inspection, observation in zip(self.inspections, observations, strict=True):
            if inspection.status is ReadinessInspectionStatus.OBSERVED:
                if observation is None or inspection.observation_sha256 != (
                    observation.observation_sha256
                ):
                    raise ValueError("observed inspection must bind its exact typed observation")
            elif observation is not None:
                raise ValueError("unobserved inspection cannot retain a typed observation")
        if self.positions is not None and self.positions.inventory_kind != "POSITIONS":
            raise ValueError("positions observation has the wrong inventory kind")
        if self.open_orders is not None and self.open_orders.inventory_kind != "OPEN_ORDERS":
            raise ValueError("open-order observation has the wrong inventory kind")

        external = self.source_kind is ReadinessSourceKind.ALPACA_PAPER_READ_ONLY
        for inspection in self.inspections:
            if inspection.status is not ReadinessInspectionStatus.NOT_ATTEMPTED and (
                inspection.external_request_performed is not external
            ):
                raise ValueError("inspection transport claim conflicts with its source kind")

        all_pass = all(item.status is ReadinessCheckStatus.PASS for item in self.checks)
        expected_reasons: tuple[str, ...]
        if all_pass:
            expected_outcome = (
                ReadinessOutcome.SHADOW_READY if external else ReadinessOutcome.MOCK_PROOF_COMPLETE
            )
            expected_reasons = (
                ("all_external_shadow_readiness_checks_passed",)
                if external
                else ("all_mock_readiness_checks_passed",)
            )
        else:
            expected_outcome = ReadinessOutcome.BLOCKED
            expected_reasons = tuple(
                sorted(
                    {
                        item.reason_code
                        for item in self.checks
                        if item.status is not ReadinessCheckStatus.PASS
                    }
                )
            )
        if self.outcome is not expected_outcome or self.reason_codes != expected_reasons:
            raise ValueError("outcome and reasons must derive from source and ordered checks")

        request = PaperShadowReadinessCreateRequest(
            readiness_idempotency_key=self.readiness_idempotency_key
        )
        expected_fingerprint = readiness_request_fingerprint(
            request=request,
            source_kind=self.source_kind,
            transport_profile_sha256=self.transport_profile_sha256,
            phase12_code_version_git_sha=self.phase12_code_version_git_sha,
        )
        if self.request_fingerprint_sha256 != expected_fingerprint or (
            self.readiness_assessment_id != identity(PHASE12_RUN_NAMESPACE, expected_fingerprint)
        ):
            raise ValueError("readiness identity must derive from its immutable request")
        payload = self.model_dump(
            mode="python", exclude={"readiness_assessment_id", "artifact_sha256"}
        )
        if self.artifact_sha256 != domain_sha256(PHASE12_ARTIFACT_HASH_DOMAIN, payload):
            raise ValueError("readiness artifact hash must bind its complete timeless payload")
        return self


def validate_code_git_sha(value: str | None) -> str:
    if value is None or re.fullmatch(r"[0-9a-f]{40}", value) is None:
        raise ValueError("phase12_code_version_git_sha must be a lowercase 40-character git SHA")
    return value


__all__ = [
    "PHASE12_ARTIFACT_SCHEMA_VERSION",
    "PHASE12_CHECK_ORDER",
    "PHASE12_CHECK_SCHEMA_VERSION",
    "PHASE12_DISCLAIMER",
    "PHASE12_INSPECTION_ORDER",
    "PHASE12_INSPECTION_SCHEMA_VERSION",
    "PHASE12_READINESS_TTL_SECONDS",
    "PaperAccountObservation",
    "PaperClockObservation",
    "PaperInstrumentObservation",
    "PaperInventoryObservation",
    "PaperQuoteObservation",
    "PaperShadowReadinessArtifact",
    "PaperShadowReadinessCheck",
    "PaperShadowReadinessCreateRequest",
    "ReadinessCheckCode",
    "ReadinessCheckStatus",
    "ReadinessInspectionCode",
    "ReadinessInspectionEvidence",
    "ReadinessInspectionStatus",
    "ReadinessObservation",
    "ReadinessOutcome",
    "ReadinessSourceKind",
    "readiness_request_fingerprint",
    "validate_code_git_sha",
]
