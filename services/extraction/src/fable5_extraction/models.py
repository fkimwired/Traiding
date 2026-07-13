from __future__ import annotations

import hashlib
from collections.abc import Mapping
from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Literal, Self
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)
from pydantic.json_schema import SkipJsonSchema

EXTRACTION_SCHEMA_VERSION = "phase2-trading-idea-card-v2"
TESTABILITY_METHOD = "phase2-testability-v1"
SHA256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


def _require_utc(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value.astimezone(UTC)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourceType(StrEnum):
    PASTED_CAPTION = "pasted_caption"
    TRANSCRIPT = "transcript"
    MANUAL_NOTES = "manual_notes"
    SCREENSHOT_TRANSCRIPT = "screenshot_transcript"
    URL_PROVENANCE = "url_provenance"
    SYNTHETIC_FIXTURE = "synthetic_fixture"


class SourceAuthority(StrEnum):
    OFFICIAL = "official"
    SOCIAL = "social"
    NEWS = "news"
    OTHER = "other"
    UNKNOWN = "unknown"


class AuthorityVerificationMethod(StrEnum):
    MANUAL_USER_ATTESTATION = "manual_user_attestation"
    SYNTHETIC_FIXTURE = "synthetic_fixture"


class ContentState(StrEnum):
    SUPPLIED_TEXT = "supplied_text"
    RETRIEVED_TEXT = "retrieved_text"
    URL_ONLY_UNRETRIEVED = "url_only_unretrieved"


class EvidenceState(StrEnum):
    SOURCE_SUPPORTED = "source_supported"
    NOT_STATED = "not_stated"
    AMBIGUOUS = "ambiguous"
    NOT_APPLICABLE = "not_applicable"


class AssetClass(StrEnum):
    EQUITY = "equity"
    ETF = "etf"
    FUTURES = "futures"
    OPTIONS = "options"
    MULTI_ASSET = "multi_asset"


class ForecastHorizon(StrEnum):
    SUB_MINUTE = "sub_minute"
    INTRADAY = "intraday"
    NEXT_DAY = "next_day"
    MULTI_DAY = "multi_day"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class SignalFamily(StrEnum):
    CROSS_SECTIONAL_RANKING_CLAIM = "cross_sectional_ranking_claim"
    TREND_OR_PATTERN_CLAIM = "trend_or_pattern_claim"
    SOCIAL_OR_NEWS_CLAIM = "social_or_news_claim"
    PAIRS_OR_DIVERGENCE_CLAIM = "pairs_or_divergence_claim"
    ORDER_FLOW_CLAIM = "order_flow_claim"
    UNUSUAL_OPTIONS_CLAIM = "unusual_options_claim"


class ExecutionStyle(StrEnum):
    HIGH_FREQUENCY_CLAIM = "high_frequency_claim"
    INTRADAY_CLAIM = "intraday_claim"
    PERIODIC_RESEARCH_CLAIM = "periodic_research_claim"
    READ_ONLY_ANALYTICS_CLAIM = "read_only_analytics_claim"


class RequiredData(StrEnum):
    POINT_IN_TIME_UNIVERSE = "point_in_time_universe"
    DELISTING_AWARE_RETURNS = "delisting_aware_returns"
    OHLCV = "ohlcv"
    OFFICIAL_TEXT = "official_text"
    SOCIAL_TEXT = "social_text"
    BORROW_AVAILABILITY = "borrow_availability"
    FULL_DEPTH_ORDER_BOOK = "full_depth_order_book"
    OPTIONS_QUOTES_AND_TRADES = "options_quotes_and_trades"


class RiskAssumption(StrEnum):
    LIQUIDITY = "liquidity"
    LOW_LATENCY = "low_latency"
    BORROW_AVAILABLE = "borrow_available"
    OFFICIAL_CORROBORATION = "official_corroboration"
    VOLATILITY_STABILITY = "volatility_stability"


class ExtractorKind(StrEnum):
    DETERMINISTIC_MOCK = "deterministic_mock"
    LLM = "llm"


class InfraRisk(StrEnum):
    UNKNOWN = "unknown"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TestabilityStatus(StrEnum):
    TESTABLE = "testable"
    NON_TESTABLE = "non_testable"


class TestabilityReason(StrEnum):
    MISSING_RAW_TEXT = "missing_raw_text"
    MISSING_ACTION_RULE = "missing_action_rule"
    AMBIGUOUS_ACTION_RULE = "ambiguous_action_rule"
    MISSING_FORECAST_HORIZON = "missing_forecast_horizon"
    AMBIGUOUS_FORECAST_HORIZON = "ambiguous_forecast_horizon"


class CorroborationStatus(StrEnum):
    NOT_REQUIRED = "not_required"
    MISSING = "missing"
    LINKED_UNVERIFIED = "linked_unverified"
    VERIFIED = "verified"


class ContributionStatus(StrEnum):
    NOT_BLOCKED_BY_CORROBORATION = "not_blocked_by_corroboration"
    BLOCKED_OFFICIAL_CORROBORATION_REQUIRED = "blocked_official_corroboration_required"


class AmbiguityFlag(StrEnum):
    SYNTHETIC_FIXTURE = "synthetic_fixture"
    SOURCE_URL_NOT_RETRIEVED = "source_url_not_retrieved"
    SOCIAL_MANIPULATION_RISK = "social_manipulation_risk"
    OFFICIAL_CORROBORATION_REQUIRED = "official_corroboration_required"
    MISSING_ACTION_RULE = "missing_action_rule"
    AMBIGUOUS_ACTION_RULE = "ambiguous_action_rule"
    MISSING_FORECAST_HORIZON = "missing_forecast_horizon"
    AMBIGUOUS_FORECAST_HORIZON = "ambiguous_forecast_horizon"
    MISSING_RAW_TEXT = "missing_raw_text"


class ExtractionEventType(StrEnum):
    REQUESTED = "requested"
    QUEUED = "queued"
    ENQUEUE_FAILED = "enqueue_failed"
    STARTED = "started"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class _TextEvidenceBase[ValueT: StrEnum](StrictModel):
    state: EvidenceState
    value: ValueT | None
    claim_ids: list[str]

    @model_validator(mode="after")
    def validate_state(self) -> Self:
        if self.state is EvidenceState.SOURCE_SUPPORTED:
            if self.value is None or not self.claim_ids:
                raise ValueError("source_supported text needs a value and claim evidence")
        elif self.state is EvidenceState.AMBIGUOUS:
            if self.value is not None or not self.claim_ids:
                raise ValueError("ambiguous text needs evidence and no normalized value")
        elif self.value is not None or self.claim_ids:
            raise ValueError("missing/not-applicable text cannot carry value or evidence")
        return self


class AssetClassEvidence(_TextEvidenceBase[AssetClass]):
    pass


class ForecastHorizonEvidence(_TextEvidenceBase[ForecastHorizon]):
    pass


class SignalFamilyEvidence(_TextEvidenceBase[SignalFamily]):
    pass


class ExecutionStyleEvidence(_TextEvidenceBase[ExecutionStyle]):
    pass


class _ListEvidenceBase[ValueT: StrEnum](StrictModel):
    state: EvidenceState
    values: list[ValueT]
    claim_ids: list[str]

    @model_validator(mode="after")
    def validate_state(self) -> Self:
        if self.state is EvidenceState.SOURCE_SUPPORTED:
            if not self.values or not self.claim_ids:
                raise ValueError("source_supported list needs values and claim evidence")
        elif self.state is EvidenceState.AMBIGUOUS:
            if self.values or not self.claim_ids:
                raise ValueError("ambiguous list needs evidence and no normalized values")
        elif self.values or self.claim_ids:
            raise ValueError("missing/not-applicable list cannot carry values or evidence")
        return self


class RequiredDataEvidence(_ListEvidenceBase[RequiredData]):
    pass


class RiskAssumptionsEvidence(_ListEvidenceBase[RiskAssumption]):
    pass


class ActionRuleEvidence(StrictModel):
    state: EvidenceState
    claim_ids: list[str]

    @model_validator(mode="after")
    def validate_state(self) -> Self:
        if self.state in {EvidenceState.SOURCE_SUPPORTED, EvidenceState.AMBIGUOUS}:
            if not self.claim_ids:
                raise ValueError("supported/ambiguous action rule needs claim evidence")
        elif self.claim_ids:
            raise ValueError("missing/not-applicable action rule cannot cite evidence")
        return self


class SourceSpan(StrictModel):
    segment_id: str
    start_byte: int = Field(ge=0)
    end_byte: int = Field(gt=0)
    text_sha256: SHA256

    @model_validator(mode="after")
    def validate_bounds(self) -> Self:
        if self.end_byte <= self.start_byte:
            raise ValueError("source span must be non-empty and half-open")
        return self


class QuotedClaim(StrictModel):
    claim_id: str
    kind: str
    span: SourceSpan
    exact_text: str


class SourceIntakeRequest(StrictModel):
    source_type: SourceType
    source_authority: SourceAuthority = SourceAuthority.UNKNOWN
    source_url: str | None = None
    raw_text: str | SkipJsonSchema[None] = None
    retrieved_at_utc: datetime | None = None
    authority_verification_method: AuthorityVerificationMethod | None = None
    official_corroboration_source_version_ids: list[UUID] = Field(default_factory=list)
    ingest_idempotency_key: str | None = Field(default=None, min_length=8, max_length=128)

    @model_validator(mode="before")
    @classmethod
    def require_omitted_raw_text_for_url_only(cls, value: object) -> object:
        if isinstance(value, Mapping) and "raw_text" in value and value["raw_text"] is None:
            raise ValueError("URL-only intake must omit raw_text instead of sending null")
        return value

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("source_url must be an absolute HTTP(S) provenance URL")
        return value

    @field_validator("raw_text")
    @classmethod
    def validate_raw_text(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("raw_text must contain non-whitespace source text")
        return value

    @model_validator(mode="after")
    def validate_input(self) -> Self:
        if self.raw_text is None and self.source_url is None:
            raise ValueError("raw_text or source_url is required")
        if self.raw_text is None and self.retrieved_at_utc is not None:
            raise ValueError("URL-only intake cannot claim a retrieval timestamp without text")
        if self.retrieved_at_utc is not None:
            self.retrieved_at_utc = _require_utc(self.retrieved_at_utc, "retrieved_at_utc")
        if (
            self.authority_verification_method
            and self.source_authority is not SourceAuthority.OFFICIAL
        ):
            raise ValueError("only official sources may carry an authority verification method")
        if (
            self.authority_verification_method is AuthorityVerificationMethod.SYNTHETIC_FIXTURE
            and self.source_type is not SourceType.SYNTHETIC_FIXTURE
        ):
            raise ValueError("synthetic verification is limited to synthetic fixtures")
        return self


class SourceCorrectionRequest(SourceIntakeRequest):
    pass


class SourceRecord(StrictModel):
    source_id: UUID
    created_at_utc: datetime

    @model_validator(mode="after")
    def normalize_time(self) -> Self:
        self.created_at_utc = _require_utc(self.created_at_utc, "created_at_utc")
        return self


class SourceVersion(StrictModel):
    source_version_id: UUID
    source_id: UUID
    source_version: int = Field(ge=1)
    parent_source_version_id: UUID | None
    source_type: SourceType
    source_authority: SourceAuthority
    source_url: str | None
    content_state: ContentState
    raw_text: str | None
    content_sha256: SHA256
    supplied_at_utc: datetime
    retrieved_at_utc: datetime | None
    authority_verification_method: AuthorityVerificationMethod | None
    official_corroboration_source_version_ids: list[UUID] = Field(default_factory=list)
    created_at_utc: datetime

    @model_validator(mode="after")
    def normalize_times(self) -> Self:
        if self.source_url is not None:
            parsed = urlsplit(self.source_url)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname:
                raise ValueError("source_url must be an absolute HTTP(S) provenance URL")
        if self.raw_text is None:
            if (
                self.content_state is not ContentState.URL_ONLY_UNRETRIEVED
                or self.source_url is None
            ):
                raise ValueError("source versions without text must be URL-only provenance")
            if self.retrieved_at_utc is not None:
                raise ValueError("URL-only source versions cannot carry retrieved_at_utc")
            expected_content = b""
        else:
            if not self.raw_text.strip():
                raise ValueError("source-version text must contain non-whitespace content")
            expected_state = (
                ContentState.RETRIEVED_TEXT
                if self.retrieved_at_utc is not None
                else ContentState.SUPPLIED_TEXT
            )
            if self.content_state is not expected_state:
                raise ValueError("source-version content state conflicts with its text provenance")
            expected_content = self.raw_text.encode("utf-8")
        if hashlib.sha256(expected_content).hexdigest() != self.content_sha256:
            raise ValueError("source-version content hash does not match immutable raw text")
        if (
            self.authority_verification_method is not None
            and self.source_authority is not SourceAuthority.OFFICIAL
        ):
            raise ValueError("only official source versions may be verified")
        if (
            self.authority_verification_method is AuthorityVerificationMethod.SYNTHETIC_FIXTURE
            and self.source_type is not SourceType.SYNTHETIC_FIXTURE
        ):
            raise ValueError("synthetic verification is limited to synthetic fixtures")
        self.supplied_at_utc = _require_utc(self.supplied_at_utc, "supplied_at_utc")
        if self.retrieved_at_utc is not None:
            self.retrieved_at_utc = _require_utc(self.retrieved_at_utc, "retrieved_at_utc")
        self.created_at_utc = _require_utc(self.created_at_utc, "created_at_utc")
        return self


class ExtractionProfile(StrictModel):
    extractor_kind: ExtractorKind = ExtractorKind.DETERMINISTIC_MOCK
    extractor_id: str = "fable5-deterministic-extractor"
    extractor_version: str = "1"
    extraction_model_id: str | None = None
    extraction_model_revision: str | None = None
    extraction_prompt_version: str | None = None
    extraction_prompt_sha256: SHA256 | None = None
    extraction_schema_version: str = EXTRACTION_SCHEMA_VERSION
    extraction_config_sha256: SHA256

    @model_validator(mode="after")
    def validate_provenance(self) -> Self:
        llm_fields = (
            self.extraction_model_id,
            self.extraction_model_revision,
            self.extraction_prompt_version,
            self.extraction_prompt_sha256,
        )
        if self.extractor_kind is ExtractorKind.LLM:
            if any(value is None for value in llm_fields):
                raise ValueError("LLM extraction requires model and prompt provenance")
        elif any(value is not None for value in llm_fields):
            raise ValueError("deterministic extraction must not fabricate LLM provenance")
        return self


class ExtractionRequestRecord(ExtractionProfile):
    extraction_request_id: UUID
    source_version_id: UUID
    request_fingerprint: SHA256
    rq_job_id: str
    latest_event: ExtractionEventType
    requested_at_utc: datetime

    @model_validator(mode="after")
    def normalize_time(self) -> Self:
        self.requested_at_utc = _require_utc(self.requested_at_utc, "requested_at_utc")
        return self


class TradingIdeaCard(StrictModel):
    card_id: UUID
    extraction_request_id: UUID
    source_id: UUID
    source_version_id: UUID
    source_authority: SourceAuthority
    source_url: str | None
    source_version: int = Field(ge=1)
    raw_text: str | None
    quoted_claims: list[QuotedClaim]
    paraphrased_claim: str | None
    asset_class: AssetClassEvidence
    forecast_horizon: ForecastHorizonEvidence
    signal_family: SignalFamilyEvidence
    execution_style: ExecutionStyleEvidence
    required_data: RequiredDataEvidence
    action_rule: ActionRuleEvidence
    risk_assumptions: RiskAssumptionsEvidence
    ambiguity_flags: list[AmbiguityFlag]
    testability_status: TestabilityStatus
    testability_reason_codes: list[TestabilityReason]
    testability_score: float = Field(ge=0.0, le=1.0)
    testability_score_method: Literal["phase2-testability-v1"] = "phase2-testability-v1"
    infra_risk: InfraRisk
    research_priority_score: None
    corroboration_status: CorroborationStatus
    contribution_status: ContributionStatus
    official_corroboration_source_ids: list[UUID]
    official_corroboration_source_version_ids: list[UUID]
    extractor_kind: ExtractorKind
    extractor_id: str
    extractor_version: str
    extraction_model_id: str | None
    extraction_model_revision: str | None
    extraction_prompt_version: str | None
    extraction_prompt_sha256: SHA256 | None
    extraction_schema_version: str
    extraction_config_sha256: SHA256
    synthetic_fixture: bool = False
    created_at_utc: datetime

    @model_validator(mode="after")
    def enforce_gates(self) -> Self:
        supported_action = self.action_rule.state is EvidenceState.SOURCE_SUPPORTED
        supported_horizon = self.forecast_horizon.state is EvidenceState.SOURCE_SUPPORTED
        expected_score = (float(supported_action) + float(supported_horizon)) / 2.0
        expected_status = (
            TestabilityStatus.TESTABLE
            if supported_action and supported_horizon
            else TestabilityStatus.NON_TESTABLE
        )
        if self.testability_status is not expected_status:
            raise ValueError("testability status conflicts with source evidence")
        if self.testability_score != expected_score:
            raise ValueError("testability score conflicts with phase2-testability-v1")
        if expected_status is TestabilityStatus.TESTABLE and self.testability_reason_codes:
            raise ValueError("testable cards cannot carry testability blockers")
        if expected_status is TestabilityStatus.NON_TESTABLE and not self.testability_reason_codes:
            raise ValueError("non-testable cards require reason codes")

        expected_reasons: set[TestabilityReason] = set()
        if not self.raw_text:
            expected_reasons.add(TestabilityReason.MISSING_RAW_TEXT)
        if self.action_rule.state is EvidenceState.NOT_STATED:
            expected_reasons.add(TestabilityReason.MISSING_ACTION_RULE)
        elif self.action_rule.state is EvidenceState.AMBIGUOUS:
            expected_reasons.add(TestabilityReason.AMBIGUOUS_ACTION_RULE)
        if self.forecast_horizon.state is EvidenceState.NOT_STATED:
            expected_reasons.add(TestabilityReason.MISSING_FORECAST_HORIZON)
        elif self.forecast_horizon.state is EvidenceState.AMBIGUOUS:
            expected_reasons.add(TestabilityReason.AMBIGUOUS_FORECAST_HORIZON)
        if set(self.testability_reason_codes) != expected_reasons:
            raise ValueError("testability reason codes conflict with source evidence")

        claim_ids = [claim.claim_id for claim in self.quoted_claims]
        if len(claim_ids) != len(set(claim_ids)):
            raise ValueError("quoted claim IDs must be unique")
        known_claims = set(claim_ids)
        evidence_claims = {
            *self.asset_class.claim_ids,
            *self.forecast_horizon.claim_ids,
            *self.signal_family.claim_ids,
            *self.execution_style.claim_ids,
            *self.required_data.claim_ids,
            *self.action_rule.claim_ids,
            *self.risk_assumptions.claim_ids,
        }
        if not evidence_claims <= known_claims:
            raise ValueError("field evidence must reference a reconstructed quoted claim")
        raw_bytes = b"" if self.raw_text is None else self.raw_text.encode("utf-8")
        for claim in self.quoted_claims:
            span = claim.span
            if span.end_byte > len(raw_bytes):
                raise ValueError("quoted claim span exceeds immutable raw text")
            exact_bytes = raw_bytes[span.start_byte : span.end_byte]
            if exact_bytes.decode("utf-8") != claim.exact_text:
                raise ValueError("quoted claim text does not match its immutable source span")
            if hashlib.sha256(exact_bytes).hexdigest() != span.text_sha256:
                raise ValueError("quoted claim hash does not match its immutable source span")

        has_social_flag = AmbiguityFlag.SOCIAL_MANIPULATION_RISK in self.ambiguity_flags
        if self.source_authority is SourceAuthority.SOCIAL and not has_social_flag:
            raise ValueError("social cards must retain the manipulation-risk flag")
        if has_social_flag:
            if self.corroboration_status is CorroborationStatus.NOT_REQUIRED:
                raise ValueError("manipulation-prone social claims require corroboration state")
            verified = self.corroboration_status is CorroborationStatus.VERIFIED
            expected_contribution = (
                ContributionStatus.NOT_BLOCKED_BY_CORROBORATION
                if verified
                else ContributionStatus.BLOCKED_OFFICIAL_CORROBORATION_REQUIRED
            )
            if self.contribution_status is not expected_contribution:
                raise ValueError("social contribution gate conflicts with corroboration state")
            if self.corroboration_status is CorroborationStatus.MISSING:
                if self.official_corroboration_source_version_ids:
                    raise ValueError("missing corroboration cannot carry official version IDs")
            elif not self.official_corroboration_source_version_ids:
                raise ValueError("linked/verified corroboration needs exact source-version IDs")
        elif self.corroboration_status is not CorroborationStatus.NOT_REQUIRED:
            raise ValueError("cards without social-risk evidence cannot require corroboration")
        elif self.contribution_status is not ContributionStatus.NOT_BLOCKED_BY_CORROBORATION:
            raise ValueError("non-social cards cannot be blocked by the social corroboration gate")
        self.created_at_utc = _require_utc(self.created_at_utc, "created_at_utc")
        return self


class ResearchMemo(StrictModel):
    memo_id: UUID
    card_id: UUID
    template_version: Literal["phase2-memo-v1"] = "phase2-memo-v1"
    markdown: str
    content_sha256: SHA256
    created_at_utc: datetime

    @model_validator(mode="after")
    def normalize_time(self) -> Self:
        self.created_at_utc = _require_utc(self.created_at_utc, "created_at_utc")
        return self


class SourceCreateResponse(StrictModel):
    source: SourceRecord
    source_version: SourceVersion
    extraction: ExtractionRequestRecord | None


class SourceDetailResponse(StrictModel):
    source: SourceRecord
    versions: list[SourceVersion]


class CardWithMemo(StrictModel):
    card: TradingIdeaCard
    memo: ResearchMemo
