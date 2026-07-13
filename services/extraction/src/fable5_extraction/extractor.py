from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol, Self
from uuid import UUID, uuid4

from pydantic import Field, model_validator

from fable5_extraction.models import (
    EXTRACTION_SCHEMA_VERSION,
    ActionRuleEvidence,
    AmbiguityFlag,
    AssetClass,
    AssetClassEvidence,
    ContentState,
    ContributionStatus,
    CorroborationStatus,
    EvidenceState,
    ExecutionStyle,
    ExecutionStyleEvidence,
    ExtractionProfile,
    ExtractionRequestRecord,
    ExtractorKind,
    ForecastHorizon,
    ForecastHorizonEvidence,
    InfraRisk,
    QuotedClaim,
    RequiredData,
    RequiredDataEvidence,
    RiskAssumption,
    RiskAssumptionsEvidence,
    SignalFamily,
    SignalFamilyEvidence,
    SourceAuthority,
    SourceSpan,
    SourceType,
    SourceVersion,
    StrictModel,
    TestabilityReason,
    TestabilityStatus,
    TradingIdeaCard,
)


class Segment(StrictModel):
    segment_id: str
    start_byte: int = Field(ge=0)
    end_byte: int = Field(gt=0)
    text_sha256: str


class _DraftTextEvidenceBase[ValueT: StrEnum](StrictModel):
    state: EvidenceState
    value: ValueT | None
    segment_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_state(self) -> Self:
        if self.state is EvidenceState.SOURCE_SUPPORTED:
            if self.value is None or not self.segment_ids:
                raise ValueError("supported draft evidence needs a value and segment")
        elif self.state is EvidenceState.AMBIGUOUS:
            if self.value is not None or not self.segment_ids:
                raise ValueError("ambiguous draft evidence needs segments and no value")
        elif self.value is not None or self.segment_ids:
            raise ValueError("missing draft evidence cannot carry value or segments")
        return self


class DraftAssetClassEvidence(_DraftTextEvidenceBase[AssetClass]):
    pass


class DraftForecastHorizonEvidence(_DraftTextEvidenceBase[ForecastHorizon]):
    pass


class DraftSignalFamilyEvidence(_DraftTextEvidenceBase[SignalFamily]):
    pass


class DraftExecutionStyleEvidence(_DraftTextEvidenceBase[ExecutionStyle]):
    pass


class _DraftListEvidenceBase[ValueT: StrEnum](StrictModel):
    state: EvidenceState
    values: list[ValueT] = Field(default_factory=list)
    segment_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_state(self) -> Self:
        if self.state is EvidenceState.SOURCE_SUPPORTED:
            if not self.values or not self.segment_ids:
                raise ValueError("supported draft list needs values and segments")
        elif self.state is EvidenceState.AMBIGUOUS:
            if self.values or not self.segment_ids:
                raise ValueError("ambiguous draft list needs segments and no values")
        elif self.values or self.segment_ids:
            raise ValueError("missing draft list cannot carry values or segments")
        return self


class DraftRequiredDataEvidence(_DraftListEvidenceBase[RequiredData]):
    pass


class DraftRiskAssumptionsEvidence(_DraftListEvidenceBase[RiskAssumption]):
    pass


class DraftActionRule(StrictModel):
    state: EvidenceState
    segment_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_state(self) -> Self:
        if self.state in {EvidenceState.SOURCE_SUPPORTED, EvidenceState.AMBIGUOUS}:
            if not self.segment_ids:
                raise ValueError("supported/ambiguous rule needs source segments")
        elif self.segment_ids:
            raise ValueError("missing rule cannot cite segments")
        return self


class ExtractionDraft(StrictModel):
    quoted_claim_segment_ids: list[str]
    asset_class: DraftAssetClassEvidence
    forecast_horizon: DraftForecastHorizonEvidence
    signal_family: DraftSignalFamilyEvidence
    execution_style: DraftExecutionStyleEvidence
    required_data: DraftRequiredDataEvidence
    action_rule: DraftActionRule
    risk_assumptions: DraftRiskAssumptionsEvidence
    infra_risk: InfraRisk
    social_manipulation_risk: bool


class Extractor(Protocol):
    profile: ExtractionProfile

    def extract(self, source: SourceVersion, segments: list[Segment]) -> ExtractionDraft: ...


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_sha256(payload: object) -> str:
    rendered = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return _sha256(rendered.encode("utf-8"))


def default_extraction_profile() -> ExtractionProfile:
    config_hash = _canonical_sha256(
        {
            "extractor": "fable5-deterministic-extractor",
            "version": "2",
            "schema": EXTRACTION_SCHEMA_VERSION,
            "testability": "phase2-testability-v1",
        }
    )
    return ExtractionProfile(
        extractor_kind=ExtractorKind.DETERMINISTIC_MOCK,
        extractor_id="fable5-deterministic-extractor",
        extractor_version="2",
        extraction_config_sha256=config_hash,
    )


def extraction_fingerprint(source: SourceVersion, profile: ExtractionProfile) -> str:
    return _canonical_sha256(
        {
            "source_version_id": str(source.source_version_id),
            "content_sha256": source.content_sha256,
            **profile.model_dump(mode="json"),
        }
    )


def segment_source(raw_text: str | None) -> list[Segment]:
    if raw_text is None or raw_text == "":
        return []

    segments: list[Segment] = []
    cursor = 0
    while cursor < len(raw_text):
        while cursor < len(raw_text) and raw_text[cursor].isspace():
            cursor += 1
        if cursor >= len(raw_text):
            break
        start_char = cursor
        end_char = len(raw_text)
        while cursor < len(raw_text):
            character = raw_text[cursor]
            if character in ".!?" and (
                cursor + 1 == len(raw_text) or raw_text[cursor + 1].isspace()
            ):
                end_char = cursor + 1
                cursor = end_char
                break
            if character in "\r\n":
                end_char = cursor
                cursor += 1
                if character == "\r" and cursor < len(raw_text) and raw_text[cursor] == "\n":
                    cursor += 1
                break
            cursor += 1
        while end_char > start_char and raw_text[end_char - 1].isspace():
            end_char -= 1
        exact = raw_text[start_char:end_char]
        if not exact:
            continue
        start_byte = len(raw_text[:start_char].encode("utf-8"))
        exact_bytes = exact.encode("utf-8")
        segments.append(
            Segment(
                segment_id=f"segment-{len(segments) + 1:03d}",
                start_byte=start_byte,
                end_byte=start_byte + len(exact_bytes),
                text_sha256=_sha256(exact_bytes),
            )
        )
    return segments


def reconstruct_segment(raw_text: str, segment: Segment) -> str:
    raw_bytes = raw_text.encode("utf-8")
    if segment.end_byte > len(raw_bytes):
        raise ValueError("source segment exceeds immutable raw text")
    exact_bytes = raw_bytes[segment.start_byte : segment.end_byte]
    try:
        exact = exact_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("source segment does not align to UTF-8 boundaries") from exc
    if _sha256(exact_bytes) != segment.text_sha256:
        raise ValueError("source segment hash does not match immutable raw text")
    return exact


def _matching_segments(raw_text: str, segments: list[Segment], terms: Iterable[str]) -> list[str]:
    patterns = tuple(
        re.compile(rf"(?<!\w){re.escape(term.strip().lower())}(?!\w)")
        for term in terms
        if term.strip()
    )
    matched: list[str] = []
    for segment in segments:
        text = reconstruct_segment(raw_text, segment).lower()
        if any(pattern.search(text) for pattern in patterns):
            matched.append(segment.segment_id)
    return matched


def _draft_text[
    EnumT: StrEnum,
    DraftTextT: StrictModel,
](evidence_type: type[DraftTextT], matches: Mapping[EnumT, list[str]]) -> DraftTextT:
    populated = [(value, ids) for value, ids in matches.items() if ids]
    if not populated:
        return evidence_type.model_validate(
            {"state": EvidenceState.NOT_STATED, "value": None, "segment_ids": []}
        )
    if len(populated) > 1:
        return evidence_type.model_validate(
            {
                "state": EvidenceState.AMBIGUOUS,
                "value": None,
                "segment_ids": sorted({item for _, ids in populated for item in ids}),
            }
        )
    value, ids = populated[0]
    return evidence_type.model_validate(
        {"state": EvidenceState.SOURCE_SUPPORTED, "value": value, "segment_ids": ids}
    )


def _draft_list[
    EnumT: StrEnum,
    DraftListT: StrictModel,
](evidence_type: type[DraftListT], matches: Mapping[EnumT, list[str]]) -> DraftListT:
    values = [value for value, ids in matches.items() if ids]
    ids = sorted({item for items in matches.values() for item in items})
    if not values:
        return evidence_type.model_validate(
            {"state": EvidenceState.NOT_STATED, "values": [], "segment_ids": []}
        )
    return evidence_type.model_validate(
        {"state": EvidenceState.SOURCE_SUPPORTED, "values": values, "segment_ids": ids}
    )


class DeterministicMockExtractor:
    """Closed-vocabulary extractor for local/CI behavior; it never authors a rule."""

    profile = default_extraction_profile()

    def extract(self, source: SourceVersion, segments: list[Segment]) -> ExtractionDraft:
        if source.raw_text is None or not segments:
            return ExtractionDraft(
                quoted_claim_segment_ids=[],
                asset_class=DraftAssetClassEvidence(
                    state=EvidenceState.NOT_STATED, value=None, segment_ids=[]
                ),
                forecast_horizon=DraftForecastHorizonEvidence(
                    state=EvidenceState.NOT_STATED, value=None, segment_ids=[]
                ),
                signal_family=DraftSignalFamilyEvidence(
                    state=EvidenceState.NOT_STATED, value=None, segment_ids=[]
                ),
                execution_style=DraftExecutionStyleEvidence(
                    state=EvidenceState.NOT_STATED, value=None, segment_ids=[]
                ),
                required_data=DraftRequiredDataEvidence(
                    state=EvidenceState.NOT_STATED, values=[], segment_ids=[]
                ),
                action_rule=DraftActionRule(state=EvidenceState.NOT_STATED, segment_ids=[]),
                risk_assumptions=DraftRiskAssumptionsEvidence(
                    state=EvidenceState.NOT_STATED, values=[], segment_ids=[]
                ),
                infra_risk=InfraRisk.UNKNOWN,
                social_manipulation_risk=source.source_authority is SourceAuthority.SOCIAL,
            )

        raw_text = source.raw_text

        def match(terms: Iterable[str]) -> list[str]:
            return _matching_segments(raw_text, segments, terms)

        asset_class = _draft_text(
            DraftAssetClassEvidence,
            {
                AssetClass.EQUITY: match(["stock", "stocks", "equity", "equities", "shares"]),
                AssetClass.ETF: match([" etf", "etfs"]),
                AssetClass.FUTURES: match(["future", "futures"]),
                AssetClass.OPTIONS: match(["option", "options", "implied volatility"]),
            },
        )
        sub_minute_ids = match(["sub-second", "millisecond", "microsecond", "sub-minute"])
        intraday_ids = [
            segment_id
            for segment_id in match(["intraday", "same day", "hour", "minute"])
            if segment_id not in sub_minute_ids
        ]
        horizon = _draft_text(
            DraftForecastHorizonEvidence,
            {
                ForecastHorizon.SUB_MINUTE: sub_minute_ids,
                ForecastHorizon.INTRADAY: intraday_ids,
                ForecastHorizon.NEXT_DAY: match(["next day", "tomorrow", "one day", "1 day"]),
                ForecastHorizon.MULTI_DAY: match(["multi-day", "several days", "5 day"]),
                ForecastHorizon.WEEKLY: match(["weekly", "one week", "1 week"]),
                ForecastHorizon.MONTHLY: match(["monthly", "one month", "1 month"]),
            },
        )
        signal_family = _draft_text(
            DraftSignalFamilyEvidence,
            {
                SignalFamily.CROSS_SECTIONAL_RANKING_CLAIM: match(
                    ["rank stocks", "rank equities", "cross-sectional", "top-ranked"]
                ),
                SignalFamily.TREND_OR_PATTERN_CLAIM: match(
                    ["trend", "breakout", "chart pattern", "moving average"]
                ),
                SignalFamily.SOCIAL_OR_NEWS_CLAIM: match(
                    ["social", "reddit", "twitter", "news sentiment", "filing"]
                ),
                SignalFamily.PAIRS_OR_DIVERGENCE_CLAIM: match(
                    ["pair", "pairs", "divergence", "cointegration", "reconverge"]
                ),
                SignalFamily.ORDER_FLOW_CLAIM: match(
                    ["order flow", "order-flow", "order book", "order-book", "scalp"]
                ),
                SignalFamily.UNUSUAL_OPTIONS_CLAIM: match(
                    ["unusual options", "options flow", "iv versus rv", "iv-vs-rv"]
                ),
            },
        )
        high_frequency_ids = match(
            [
                "hft",
                "sub-second",
                "sub-minute",
                "millisecond",
                "microsecond",
                "order book",
                "order-book",
                "scalp",
                "scalping",
            ]
        )
        read_only_ids = match(["read-only", "analytics only", "diagnostic only"])
        periodic_ids = match(["weekly", "monthly", "rebalance", "periodic"])
        execution_style = _draft_text(
            DraftExecutionStyleEvidence,
            {
                ExecutionStyle.HIGH_FREQUENCY_CLAIM: high_frequency_ids,
                ExecutionStyle.READ_ONLY_ANALYTICS_CLAIM: read_only_ids,
                ExecutionStyle.PERIODIC_RESEARCH_CLAIM: periodic_ids,
            },
        )
        required_data = _draft_list(
            DraftRequiredDataEvidence,
            {
                RequiredData.POINT_IN_TIME_UNIVERSE: match(
                    ["point-in-time", "historical universe"]
                ),
                RequiredData.DELISTING_AWARE_RETURNS: match(["delisting", "delisted"]),
                RequiredData.OHLCV: match(["ohlcv", "price", "volume"]),
                RequiredData.OFFICIAL_TEXT: match(["official source", "filing", "issuer release"]),
                RequiredData.SOCIAL_TEXT: match(["social", "reddit", "twitter"]),
                RequiredData.BORROW_AVAILABILITY: match(["borrow", "hard-to-borrow", "locate"]),
                RequiredData.FULL_DEPTH_ORDER_BOOK: match(
                    ["full-depth", "order book", "order-book", "l2", "l3"]
                ),
                RequiredData.OPTIONS_QUOTES_AND_TRADES: match(
                    ["options chain", "options quotes", "opra", "options flow"]
                ),
            },
        )
        action_ids = match(
            [
                " when ",
                "when ",
                " if ",
                "if ",
                "rank stocks",
                "top-ranked",
                "select the",
                "crosses",
                "crossover",
                "diverges",
                "reconverge",
                "entry rule",
                "exit rule",
            ]
        )
        action_rule = DraftActionRule(
            state=EvidenceState.SOURCE_SUPPORTED if action_ids else EvidenceState.NOT_STATED,
            segment_ids=action_ids,
        )
        risk_assumptions = _draft_list(
            DraftRiskAssumptionsEvidence,
            {
                RiskAssumption.LIQUIDITY: match(["liquid", "liquidity", "adv"]),
                RiskAssumption.LOW_LATENCY: match(["low latency", "sub-second", "millisecond"]),
                RiskAssumption.BORROW_AVAILABLE: match(["borrow", "locate"]),
                RiskAssumption.OFFICIAL_CORROBORATION: match(
                    ["official corroboration", "official source"]
                ),
                RiskAssumption.VOLATILITY_STABILITY: match(["volatility", "stable regime"]),
            },
        )
        social_risk = source.source_authority is SourceAuthority.SOCIAL or bool(
            match(["social", "reddit", "twitter", "instagram"])
        )
        quoted_ids = sorted(
            {
                *action_ids,
                *asset_class.segment_ids,
                *horizon.segment_ids,
                *signal_family.segment_ids,
                *execution_style.segment_ids,
                *required_data.segment_ids,
                *risk_assumptions.segment_ids,
            }
        )
        if not quoted_ids:
            quoted_ids = [segment.segment_id for segment in segments]
        return ExtractionDraft(
            quoted_claim_segment_ids=quoted_ids,
            asset_class=asset_class,
            forecast_horizon=horizon,
            signal_family=signal_family,
            execution_style=execution_style,
            required_data=required_data,
            action_rule=action_rule,
            risk_assumptions=risk_assumptions,
            infra_risk=InfraRisk.HIGH if high_frequency_ids else InfraRisk.UNKNOWN,
            social_manipulation_risk=social_risk,
        )


def _claims_from_segments(
    raw_text: str | None, segments: list[Segment], selected_ids: list[str]
) -> list[QuotedClaim]:
    if raw_text is None:
        return []
    by_id = {segment.segment_id: segment for segment in segments}
    claims: list[QuotedClaim] = []
    for segment_id in selected_ids:
        segment = by_id.get(segment_id)
        if segment is None:
            raise ValueError("extraction cited a segment outside the immutable source version")
        claims.append(
            QuotedClaim(
                claim_id=segment_id,
                kind="source_claim",
                span=SourceSpan(**segment.model_dump()),
                exact_text=reconstruct_segment(raw_text, segment),
            )
        )
    return claims


def _public_asset_class(draft: DraftAssetClassEvidence) -> AssetClassEvidence:
    return AssetClassEvidence(
        state=draft.state,
        value=draft.value,
        claim_ids=draft.segment_ids,
    )


def _public_forecast_horizon(
    draft: DraftForecastHorizonEvidence,
) -> ForecastHorizonEvidence:
    return ForecastHorizonEvidence(
        state=draft.state,
        value=draft.value,
        claim_ids=draft.segment_ids,
    )


def _public_signal_family(draft: DraftSignalFamilyEvidence) -> SignalFamilyEvidence:
    return SignalFamilyEvidence(
        state=draft.state,
        value=draft.value,
        claim_ids=draft.segment_ids,
    )


def _public_execution_style(draft: DraftExecutionStyleEvidence) -> ExecutionStyleEvidence:
    return ExecutionStyleEvidence(
        state=draft.state,
        value=draft.value,
        claim_ids=draft.segment_ids,
    )


def _public_required_data(draft: DraftRequiredDataEvidence) -> RequiredDataEvidence:
    return RequiredDataEvidence(
        state=draft.state,
        values=draft.values,
        claim_ids=draft.segment_ids,
    )


def _public_risk_assumptions(
    draft: DraftRiskAssumptionsEvidence,
) -> RiskAssumptionsEvidence:
    return RiskAssumptionsEvidence(
        state=draft.state,
        values=draft.values,
        claim_ids=draft.segment_ids,
    )


def _testability_reasons(source: SourceVersion, draft: ExtractionDraft) -> list[TestabilityReason]:
    reasons: list[TestabilityReason] = []
    if source.content_state is ContentState.URL_ONLY_UNRETRIEVED or not source.raw_text:
        reasons.append(TestabilityReason.MISSING_RAW_TEXT)
    if draft.action_rule.state is EvidenceState.NOT_STATED:
        reasons.append(TestabilityReason.MISSING_ACTION_RULE)
    elif draft.action_rule.state is EvidenceState.AMBIGUOUS:
        reasons.append(TestabilityReason.AMBIGUOUS_ACTION_RULE)
    if draft.forecast_horizon.state is EvidenceState.NOT_STATED:
        reasons.append(TestabilityReason.MISSING_FORECAST_HORIZON)
    elif draft.forecast_horizon.state is EvidenceState.AMBIGUOUS:
        reasons.append(TestabilityReason.AMBIGUOUS_FORECAST_HORIZON)
    return reasons


def _neutral_paraphrase(draft: ExtractionDraft) -> str | None:
    family = draft.signal_family.value
    if family is None:
        return None
    horizon = draft.forecast_horizon.value
    if horizon is None:
        return f"The supplied source presents an unverified {family}; its horizon is not stated."
    return f"The supplied source presents an unverified {family} with a {horizon} horizon."


def build_card(
    *,
    source: SourceVersion,
    request: ExtractionRequestRecord,
    draft: ExtractionDraft,
    segments: list[Segment],
    corroborating_versions: list[SourceVersion],
    card_id: UUID | None = None,
    created_at_utc: datetime | None = None,
) -> TradingIdeaCard:
    if (
        source.raw_text is not None
        and _sha256(source.raw_text.encode("utf-8")) != source.content_sha256
    ):
        raise ValueError("immutable source content hash mismatch")

    claims = _claims_from_segments(source.raw_text, segments, draft.quoted_claim_segment_ids)
    reasons = _testability_reasons(source, draft)
    supported_action = draft.action_rule.state is EvidenceState.SOURCE_SUPPORTED
    supported_horizon = draft.forecast_horizon.state is EvidenceState.SOURCE_SUPPORTED
    score = (float(supported_action) + float(supported_horizon)) / 2.0
    testability = (
        TestabilityStatus.TESTABLE
        if supported_action and supported_horizon
        else TestabilityStatus.NON_TESTABLE
    )

    verified = [
        version
        for version in corroborating_versions
        if version.source_authority is SourceAuthority.OFFICIAL
        and version.authority_verification_method is not None
    ]
    official_links = [
        version
        for version in corroborating_versions
        if version.source_authority is SourceAuthority.OFFICIAL
    ]
    if draft.social_manipulation_risk:
        if verified:
            corroboration = CorroborationStatus.VERIFIED
            contribution = ContributionStatus.NOT_BLOCKED_BY_CORROBORATION
        elif official_links:
            corroboration = CorroborationStatus.LINKED_UNVERIFIED
            contribution = ContributionStatus.BLOCKED_OFFICIAL_CORROBORATION_REQUIRED
        else:
            corroboration = CorroborationStatus.MISSING
            contribution = ContributionStatus.BLOCKED_OFFICIAL_CORROBORATION_REQUIRED
    else:
        corroboration = CorroborationStatus.NOT_REQUIRED
        contribution = ContributionStatus.NOT_BLOCKED_BY_CORROBORATION

    flags: list[AmbiguityFlag] = []
    if source.source_type is SourceType.SYNTHETIC_FIXTURE:
        flags.append(AmbiguityFlag.SYNTHETIC_FIXTURE)
    if source.content_state is ContentState.URL_ONLY_UNRETRIEVED:
        flags.append(AmbiguityFlag.SOURCE_URL_NOT_RETRIEVED)
    if draft.social_manipulation_risk:
        flags.append(AmbiguityFlag.SOCIAL_MANIPULATION_RISK)
        if corroboration is not CorroborationStatus.VERIFIED:
            flags.append(AmbiguityFlag.OFFICIAL_CORROBORATION_REQUIRED)
    reason_to_flag = {
        TestabilityReason.MISSING_RAW_TEXT: AmbiguityFlag.MISSING_RAW_TEXT,
        TestabilityReason.MISSING_ACTION_RULE: AmbiguityFlag.MISSING_ACTION_RULE,
        TestabilityReason.AMBIGUOUS_ACTION_RULE: AmbiguityFlag.AMBIGUOUS_ACTION_RULE,
        TestabilityReason.MISSING_FORECAST_HORIZON: AmbiguityFlag.MISSING_FORECAST_HORIZON,
        TestabilityReason.AMBIGUOUS_FORECAST_HORIZON: AmbiguityFlag.AMBIGUOUS_FORECAST_HORIZON,
    }
    flags.extend(reason_to_flag[reason] for reason in reasons)

    return TradingIdeaCard(
        card_id=card_id or uuid4(),
        extraction_request_id=request.extraction_request_id,
        source_id=source.source_id,
        source_version_id=source.source_version_id,
        source_authority=source.source_authority,
        source_url=source.source_url,
        source_version=source.source_version,
        raw_text=source.raw_text,
        quoted_claims=claims,
        paraphrased_claim=_neutral_paraphrase(draft),
        asset_class=_public_asset_class(draft.asset_class),
        forecast_horizon=_public_forecast_horizon(draft.forecast_horizon),
        signal_family=_public_signal_family(draft.signal_family),
        execution_style=_public_execution_style(draft.execution_style),
        required_data=_public_required_data(draft.required_data),
        action_rule=ActionRuleEvidence(
            state=draft.action_rule.state,
            claim_ids=draft.action_rule.segment_ids,
        ),
        risk_assumptions=_public_risk_assumptions(draft.risk_assumptions),
        ambiguity_flags=list(dict.fromkeys(flags)),
        testability_status=testability,
        testability_reason_codes=reasons,
        testability_score=score,
        infra_risk=draft.infra_risk,
        research_priority_score=None,
        corroboration_status=corroboration,
        contribution_status=contribution,
        official_corroboration_source_ids=list(
            dict.fromkeys(version.source_id for version in official_links)
        ),
        official_corroboration_source_version_ids=list(
            dict.fromkeys(version.source_version_id for version in official_links)
        ),
        extractor_kind=request.extractor_kind,
        extractor_id=request.extractor_id,
        extractor_version=request.extractor_version,
        extraction_model_id=request.extraction_model_id,
        extraction_model_revision=request.extraction_model_revision,
        extraction_prompt_version=request.extraction_prompt_version,
        extraction_prompt_sha256=request.extraction_prompt_sha256,
        extraction_schema_version=request.extraction_schema_version,
        extraction_config_sha256=request.extraction_config_sha256,
        synthetic_fixture=source.source_type is SourceType.SYNTHETIC_FIXTURE,
        created_at_utc=created_at_utc or datetime.now(UTC),
    )
