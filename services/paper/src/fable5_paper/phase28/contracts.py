"""Sanitized output contracts for the Phase 28 pilot."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from fable5_paper.phase28.canonical import (
    PHASE28_CONFIG_SHA256,
    PHASE28_CURRENCY,
    PHASE28_EXACT_USE_REVIEW_EXPIRES_AT_UTC,
    PHASE28_EXACT_USE_REVIEW_SHA256,
    PHASE28_FEED,
    PHASE28_FIXED_ENDPOINTS,
    PHASE28_NOTICE,
    PHASE28_SIGNAL_REGISTRY_SHA256,
    PHASE28_TRANSPORT_PROFILE_SHA256,
    PHASE28_UNIVERSE,
    PHASE28_UNIVERSE_SHA256,
    domain_sha256,
    evidence_id,
    observation_snapshot_id,
)

Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
GitSha = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]
SafeToken = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ObservationSourceKind(StrEnum):
    DETERMINISTIC_MOCK = "DETERMINISTIC_MOCK"
    ALPACA_IEX_READ_ONLY = "ALPACA_IEX_READ_ONLY"


class InspectionCode(StrEnum):
    ASSET_AAPL = "ASSET_AAPL"
    ASSET_MSFT = "ASSET_MSFT"
    ASSET_SPY = "ASSET_SPY"
    LATEST_BARS = "LATEST_BARS"
    LATEST_QUOTES = "LATEST_QUOTES"
    SNAPSHOTS = "SNAPSHOTS"


class InspectionStatus(StrEnum):
    OBSERVED = "OBSERVED"
    BLOCKED = "BLOCKED"
    NOT_ATTEMPTED = "NOT_ATTEMPTED"


class ObservationOutcome(StrEnum):
    MATCH = "MATCH"
    NO_MATCH = "NO_MATCH"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class PredicateCode(StrEnum):
    ASSET_ACTIVE = "ASSET_ACTIVE"
    ASSET_TRADABLE = "ASSET_TRADABLE"
    LATEST_BAR_VALID_AND_FRESH = "LATEST_BAR_VALID_AND_FRESH"
    LATEST_QUOTE_VALID_AND_FRESH = "LATEST_QUOTE_VALID_AND_FRESH"
    SNAPSHOT_COMPLETE_AND_FRESH = "SNAPSHOT_COMPLETE_AND_FRESH"
    CROSS_ENDPOINT_COHERENT = "CROSS_ENDPOINT_COHERENT"
    SESSION_DIRECTION_POSITIVE = "SESSION_DIRECTION_POSITIVE"
    INTRADAY_DIRECTION_POSITIVE = "INTRADAY_DIRECTION_POSITIVE"


class PredicateStatus(StrEnum):
    MATCH = "MATCH"
    NO_MATCH = "NO_MATCH"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class ObservationInspectionEvidence(_StrictModel):
    schema_version: Literal["phase28-alpaca-iex-inspection-v1"]
    ordinal: int = Field(ge=1, le=6)
    code: InspectionCode
    status: InspectionStatus
    method: Literal["GET"]
    external_request_performed: bool
    endpoint_sha256: Sha256
    request_started_at_utc: datetime
    request_completed_at_utc: datetime
    http_status: int | None = Field(default=None, ge=100, le=599)
    request_id_sha256: Sha256 | None = None
    response_sha256: Sha256 | None = None
    sanitized_observation_sha256: Sha256 | None = None
    failure_reason: SafeToken | None = None
    inspection_sha256: Sha256

    @field_validator("request_started_at_utc", "request_completed_at_utc")
    @classmethod
    def utc_only(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def internally_consistent(self) -> ObservationInspectionEvidence:
        endpoint = PHASE28_FIXED_ENDPOINTS[self.ordinal - 1]
        if (
            self.code.value != endpoint.code
            or self.method != endpoint.method
            or self.endpoint_sha256 != domain_sha256("phase28-fixed-endpoint-v1", endpoint)
        ):
            raise ValueError("inspection endpoint identity mismatch")
        if self.request_completed_at_utc < self.request_started_at_utc:
            raise ValueError("inspection timestamps are reversed")
        if (
            self.external_request_performed
            and self.request_started_at_utc >= PHASE28_EXACT_USE_REVIEW_EXPIRES_AT_UTC
        ):
            raise ValueError("external inspection started after exact-use review expiry")
        if self.status is InspectionStatus.OBSERVED and self.sanitized_observation_sha256 is None:
            raise ValueError("observed inspection lacks sanitized observation hash")
        if self.status is InspectionStatus.OBSERVED and self.failure_reason is not None:
            raise ValueError("observed inspection cannot carry a failure reason")
        if self.status is InspectionStatus.BLOCKED and self.failure_reason is None:
            raise ValueError("blocked inspection lacks failure reason")
        if (
            self.status is not InspectionStatus.OBSERVED
            and self.sanitized_observation_sha256 is not None
        ):
            raise ValueError("non-observed inspection cannot carry an observation hash")
        if self.status is InspectionStatus.NOT_ATTEMPTED:
            if self.external_request_performed:
                raise ValueError("unattempted inspection cannot claim an external request")
            if self.failure_reason != "prior_inspection_blocked":
                raise ValueError("unattempted inspection reason changed")
            if any(
                value is not None
                for value in (
                    self.http_status,
                    self.request_id_sha256,
                    self.response_sha256,
                    self.sanitized_observation_sha256,
                )
            ):
                raise ValueError("unattempted inspection cannot carry transport evidence")
        if not self.external_request_performed and any(
            value is not None
            for value in (
                self.http_status,
                self.request_id_sha256,
                self.response_sha256,
            )
        ):
            raise ValueError("local inspection cannot carry external transport evidence")
        payload = self.model_dump(mode="python", exclude={"inspection_sha256"})
        if self.inspection_sha256 != domain_sha256("phase28-alpaca-iex-inspection-v1", payload):
            raise ValueError("inspection identity mismatch")
        return self


class PredicateEvidence(_StrictModel):
    schema_version: Literal["phase28-observation-predicate-v1"]
    ordinal: int = Field(ge=1, le=8)
    code: PredicateCode
    status: PredicateStatus
    reason_code: SafeToken
    predicate_sha256: Sha256

    @model_validator(mode="after")
    def identity_is_exact(self) -> PredicateEvidence:
        payload = self.model_dump(mode="python", exclude={"predicate_sha256"})
        if self.predicate_sha256 != domain_sha256("phase28-observation-predicate-v1", payload):
            raise ValueError("predicate identity mismatch")
        return self


class SymbolObservationEvidence(_StrictModel):
    schema_version: Literal["phase28-symbol-observation-v1"]
    symbol: Literal["AAPL", "MSFT", "SPY"]
    outcome: ObservationOutcome
    predicates: tuple[PredicateEvidence, ...] = Field(min_length=8, max_length=8)
    symbol_observation_sha256: Sha256

    @model_validator(mode="after")
    def predicate_order_is_exact(self) -> SymbolObservationEvidence:
        if tuple(item.code for item in self.predicates) != tuple(PredicateCode):
            raise ValueError("predicate registry changed")
        if tuple(item.ordinal for item in self.predicates) != tuple(range(1, 9)):
            raise ValueError("predicate ordinal changed")
        statuses = {item.status for item in self.predicates}
        expected = (
            ObservationOutcome.INSUFFICIENT_DATA
            if PredicateStatus.INSUFFICIENT_DATA in statuses
            else (
                ObservationOutcome.MATCH
                if statuses == {PredicateStatus.MATCH}
                else ObservationOutcome.NO_MATCH
            )
        )
        if self.outcome is not expected:
            raise ValueError("symbol outcome does not follow the frozen rule")
        payload = self.model_dump(mode="python", exclude={"symbol_observation_sha256"})
        if self.symbol_observation_sha256 != domain_sha256(
            "phase28-symbol-observation-v1", payload
        ):
            raise ValueError("symbol observation identity mismatch")
        return self


class ObservationAuthority(_StrictModel):
    provider_payload_persisted: Literal[False]
    raw_price_persisted: Literal[False]
    research_qualified: Literal[False]
    strategy_execution_eligible: Literal[False]
    order_submission_authorized: Literal[False]
    live_path_absent: Literal[True]
    simulated_paper_only: Literal[True]
    no_personalized_investment_advice: Literal[True]
    no_real_performance_claimed: Literal[True]


class AlpacaIexObservationEvidence(_StrictModel):
    schema_version: Literal["phase28-alpaca-iex-observation-evidence-v1"]
    evidence_id: UUID
    evidence_sha256: Sha256
    observation_snapshot_id: UUID
    observation_snapshot_sha256: Sha256
    observation_snapshot_kind: Literal["SANITIZED_OBSERVATION_METADATA_ONLY"]
    source_kind: ObservationSourceKind
    feed: Literal["iex"]
    currency: Literal["USD"]
    universe: tuple[Literal["AAPL", "MSFT", "SPY"], ...] = Field(min_length=3, max_length=3)
    config_sha256: Sha256
    universe_sha256: Sha256
    signal_registry_sha256: Sha256
    transport_profile_sha256: Sha256
    code_version_git_sha: GitSha
    random_seed: Literal[0]
    trial_count: Literal[0]
    forecast_horizon: Literal["NONE_OBSERVATION_ONLY"]
    exact_use_review_confirmed_for_external_run: bool
    exact_use_review_sha256: Sha256
    exact_use_review_revalidation_deadline_utc: datetime
    observed_at_utc: datetime
    inspections: tuple[ObservationInspectionEvidence, ...] = Field(min_length=6, max_length=6)
    symbols: tuple[SymbolObservationEvidence, ...] = Field(min_length=3, max_length=3)
    authority: ObservationAuthority
    notice: str

    @field_validator("observed_at_utc")
    @classmethod
    def observed_at_is_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observation timestamp must be timezone-aware")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def registries_and_identity_are_exact(self) -> AlpacaIexObservationEvidence:
        if self.feed != PHASE28_FEED or self.currency != PHASE28_CURRENCY:
            raise ValueError("feed or currency changed")
        if (
            self.config_sha256 != PHASE28_CONFIG_SHA256
            or self.universe_sha256 != PHASE28_UNIVERSE_SHA256
            or self.signal_registry_sha256 != PHASE28_SIGNAL_REGISTRY_SHA256
            or self.transport_profile_sha256 != PHASE28_TRANSPORT_PROFILE_SHA256
            or self.exact_use_review_sha256 != PHASE28_EXACT_USE_REVIEW_SHA256
            or self.notice != PHASE28_NOTICE
        ):
            raise ValueError("frozen Phase 28 identity changed")
        if (
            self.exact_use_review_revalidation_deadline_utc
            != PHASE28_EXACT_USE_REVIEW_EXPIRES_AT_UTC
        ):
            raise ValueError("exact-use review deadline changed")
        if self.universe != PHASE28_UNIVERSE:
            raise ValueError("universe changed")
        if tuple(item.code for item in self.inspections) != tuple(InspectionCode):
            raise ValueError("inspection registry changed")
        if tuple(item.ordinal for item in self.inspections) != tuple(range(1, 7)):
            raise ValueError("inspection ordinal changed")
        if tuple(item.symbol for item in self.symbols) != PHASE28_UNIVERSE:
            raise ValueError("symbol evidence order changed")
        if any(self.observed_at_utc < item.request_completed_at_utc for item in self.inspections):
            raise ValueError("artifact predates an inspection")
        snapshot_payload = {
            "source_kind": self.source_kind,
            "observed_at_utc": self.observed_at_utc,
            "inspection_sha256s": tuple(item.inspection_sha256 for item in self.inspections),
            "config_sha256": self.config_sha256,
        }
        expected_snapshot_hash = domain_sha256(
            "phase28-sanitized-observation-snapshot-v1", snapshot_payload
        )
        if (
            self.observation_snapshot_sha256 != expected_snapshot_hash
            or self.observation_snapshot_id != observation_snapshot_id(expected_snapshot_hash)
        ):
            raise ValueError("observation snapshot identity mismatch")
        if self.source_kind is ObservationSourceKind.DETERMINISTIC_MOCK:
            if self.exact_use_review_confirmed_for_external_run:
                raise ValueError("mock evidence claimed an external exact-use attestation")
            if any(
                item.external_request_performed
                or item.http_status is not None
                or item.request_id_sha256 is not None
                or item.response_sha256 is not None
                or item.status is not InspectionStatus.OBSERVED
                for item in self.inspections
            ):
                raise ValueError("mock evidence claimed external transport")
        else:
            if not self.exact_use_review_confirmed_for_external_run:
                raise ValueError("external evidence lacks exact-use attestation")
            blocked_seen = False
            for item in self.inspections:
                if item.status is InspectionStatus.OBSERVED:
                    if blocked_seen:
                        raise ValueError("external fail-closed ordering changed")
                    if (
                        not item.external_request_performed
                        or item.http_status != 200
                        or item.response_sha256 is None
                    ):
                        raise ValueError("external observation lacks transport evidence")
                elif item.status is InspectionStatus.BLOCKED:
                    if blocked_seen:
                        raise ValueError("external fail-closed ordering changed")
                    blocked_seen = True
                elif not blocked_seen:
                    raise ValueError("external inspection was unattempted before a block")
            statuses_by_code = {item.code: item.status for item in self.inspections}
            asset_codes = {
                "AAPL": InspectionCode.ASSET_AAPL,
                "MSFT": InspectionCode.ASSET_MSFT,
                "SPY": InspectionCode.ASSET_SPY,
            }
            dependencies = {
                PredicateCode.LATEST_BAR_VALID_AND_FRESH: (InspectionCode.LATEST_BARS,),
                PredicateCode.LATEST_QUOTE_VALID_AND_FRESH: (InspectionCode.LATEST_QUOTES,),
                PredicateCode.SNAPSHOT_COMPLETE_AND_FRESH: (InspectionCode.SNAPSHOTS,),
                PredicateCode.CROSS_ENDPOINT_COHERENT: (
                    InspectionCode.LATEST_BARS,
                    InspectionCode.LATEST_QUOTES,
                    InspectionCode.SNAPSHOTS,
                ),
                PredicateCode.SESSION_DIRECTION_POSITIVE: (InspectionCode.SNAPSHOTS,),
                PredicateCode.INTRADAY_DIRECTION_POSITIVE: (InspectionCode.SNAPSHOTS,),
            }
            for symbol in self.symbols:
                predicate_dependencies = {
                    PredicateCode.ASSET_ACTIVE: (asset_codes[symbol.symbol],),
                    PredicateCode.ASSET_TRADABLE: (asset_codes[symbol.symbol],),
                    **dependencies,
                }
                for predicate in symbol.predicates:
                    if (
                        any(
                            statuses_by_code[code] is not InspectionStatus.OBSERVED
                            for code in predicate_dependencies[predicate.code]
                        )
                        and predicate.status is not PredicateStatus.INSUFFICIENT_DATA
                    ):
                        raise ValueError("predicate classification lacks an observed dependency")
        payload = self.model_dump(mode="python", exclude={"evidence_id", "evidence_sha256"})
        expected_hash = domain_sha256("phase28-alpaca-iex-evidence-v1", payload)
        if self.evidence_sha256 != expected_hash or self.evidence_id != evidence_id(expected_hash):
            raise ValueError("evidence identity mismatch")
        return self


def validate_code_git_sha(value: str | None) -> str:
    if value is None or re.fullmatch(r"[0-9a-f]{40}", value) is None:
        raise ValueError("code version identity is unavailable")
    return value


__all__ = [
    "AlpacaIexObservationEvidence",
    "InspectionCode",
    "InspectionStatus",
    "ObservationAuthority",
    "ObservationInspectionEvidence",
    "ObservationOutcome",
    "ObservationSourceKind",
    "PredicateCode",
    "PredicateEvidence",
    "PredicateStatus",
    "SymbolObservationEvidence",
    "validate_code_git_sha",
]
