from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Literal, Self
from uuid import UUID

from fable5_extraction.models import (
    ContributionStatus,
    CorroborationStatus,
    EvidenceState,
    ExecutionStyle,
    ExtractorKind,
    ForecastHorizon,
    InfraRisk,
    RequiredData,
    SignalFamily,
    TestabilityReason,
    TestabilityStatus,
)
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

SHA256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


def _utc(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value.astimezone(UTC)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CanonicalFamily(StrEnum):
    A_CROSS_SECTIONAL_EQUITY_RANKING = "A_CROSS_SECTIONAL_EQUITY_RANKING"
    B_TIME_SERIES_MOMENTUM_REGIME = "B_TIME_SERIES_MOMENTUM_REGIME"
    C_OFFICIAL_EVENT_TEXT_OVERLAY = "C_OFFICIAL_EVENT_TEXT_OVERLAY"
    D_PAIRS_STATISTICAL_ARBITRAGE = "D_PAIRS_STATISTICAL_ARBITRAGE"
    E_ORDER_BOOK_MICROSTRUCTURE = "E_ORDER_BOOK_MICROSTRUCTURE"
    F_OPTIONS_FLOW_IV_RV_ANALYTICS = "F_OPTIONS_FLOW_IV_RV_ANALYTICS"


class ResearchVerdict(StrEnum):
    BUILD_RESEARCH = "BUILD_RESEARCH"
    DEFER = "DEFER"
    DEFER_READ_ONLY = "DEFER_READ_ONLY"
    REJECT_PLATFORM = "REJECT_PLATFORM"
    NON_TESTABLE = "NON_TESTABLE"


class MappingRuleId(StrEnum):
    NON_TESTABLE_PRECEDENCE = "P3-001-NON-TESTABLE-PRECEDENCE"
    PLATFORM_MISMATCH_PRECEDENCE = "P3-002-PLATFORM-MISMATCH"
    SOCIAL_CORROBORATION_PRECEDENCE = "P3-003-SOCIAL-CORROBORATION"
    PAIRS_REQUIREMENTS_PRECEDENCE = "P3-004-PAIRS-REQUIREMENTS"
    OPTIONS_READ_ONLY_PRECEDENCE = "P3-005-OPTIONS-READ-ONLY"
    CANON_A = "P3-CANON-A"
    CANON_B = "P3-CANON-B"
    CANON_C = "P3-CANON-C"
    CANON_D = "P3-CANON-D"
    CANON_E = "P3-CANON-E"
    CANON_F = "P3-CANON-F"


class MappingReasonCode(StrEnum):
    MISSING_RAW_TEXT = "missing_raw_text"
    MISSING_ACTION_RULE = "missing_action_rule"
    AMBIGUOUS_ACTION_RULE = "ambiguous_action_rule"
    MISSING_FORECAST_HORIZON = "missing_forecast_horizon"
    AMBIGUOUS_FORECAST_HORIZON = "ambiguous_forecast_horizon"
    MISSING_CANONICAL_FAMILY = "MISSING_CANONICAL_FAMILY"
    AMBIGUOUS_CANONICAL_FAMILY = "AMBIGUOUS_CANONICAL_FAMILY"
    PLATFORM_INFRASTRUCTURE_MISMATCH = "PLATFORM_INFRASTRUCTURE_MISMATCH"
    OFFICIAL_CORROBORATION_REQUIRED = "OFFICIAL_CORROBORATION_REQUIRED"
    BORROW_AND_BREAK_REQUIREMENTS = "BORROW_AND_BREAK_REQUIREMENTS"
    READ_ONLY_ANALYTICS_ONLY = "READ_ONLY_ANALYTICS_ONLY"
    CANON_A_RULE_MATCHED = "CANON_A_RULE_MATCHED"
    CANON_B_RULE_MATCHED = "CANON_B_RULE_MATCHED"
    CANON_C_RULE_MATCHED = "CANON_C_RULE_MATCHED"


class _ScalarEvidence[ValueT: StrEnum](StrictModel):
    state: EvidenceState
    value: ValueT | None
    claim_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_state(self) -> Self:
        if self.state is EvidenceState.SOURCE_SUPPORTED:
            if self.value is None or not self.claim_ids:
                raise ValueError("source_supported mapping evidence needs a value and claims")
        elif self.state is EvidenceState.AMBIGUOUS:
            if self.value is not None or not self.claim_ids:
                raise ValueError("ambiguous mapping evidence needs claims and no value")
        elif self.value is not None or self.claim_ids:
            raise ValueError("missing mapping evidence cannot carry a value or claims")
        return self


class MappingSignalFamilyEvidence(_ScalarEvidence[SignalFamily]):
    pass


class MappingForecastHorizonEvidence(_ScalarEvidence[ForecastHorizon]):
    pass


class MappingExecutionStyleEvidence(_ScalarEvidence[ExecutionStyle]):
    pass


class MappingActionRuleEvidence(StrictModel):
    state: EvidenceState
    claim_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_state(self) -> Self:
        if self.state in {EvidenceState.SOURCE_SUPPORTED, EvidenceState.AMBIGUOUS}:
            if not self.claim_ids:
                raise ValueError("supported/ambiguous action evidence needs claims")
        elif self.claim_ids:
            raise ValueError("missing action evidence cannot carry claims")
        return self


class MappingRequiredDataEvidence(StrictModel):
    state: EvidenceState
    values: tuple[RequiredData, ...] = ()
    claim_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_state(self) -> Self:
        if self.state is EvidenceState.SOURCE_SUPPORTED:
            if not self.values or not self.claim_ids:
                raise ValueError("source_supported required-data evidence needs values and claims")
        elif self.state is EvidenceState.AMBIGUOUS:
            if self.values or not self.claim_ids:
                raise ValueError("ambiguous required-data evidence needs claims and no values")
        elif self.values or self.claim_ids:
            raise ValueError("missing required-data evidence cannot carry values or claims")
        return self


class MappingEvidenceReference(StrictModel):
    phase2_field: Literal[
        "signal_family",
        "forecast_horizon",
        "execution_style",
        "required_data",
        "testability",
        "infra_risk",
        "contribution_status",
        "corroboration_status",
    ]
    state: EvidenceState | None = None
    value: str | None = None
    claim_ids: tuple[str, ...] = ()


class MappingInput(StrictModel):
    card_id: UUID
    card_sha256: SHA256
    extraction_request_id: UUID
    extraction_request_fingerprint: SHA256
    source_id: UUID
    source_version_id: UUID
    source_version: int = Field(ge=1)
    source_content_sha256: SHA256
    official_corroboration_source_version_ids: tuple[UUID, ...] = ()
    extractor_kind: ExtractorKind
    extractor_id: str
    extractor_version: str
    extraction_model_id: str | None = None
    extraction_model_revision: str | None = None
    extraction_prompt_version: str | None = None
    extraction_prompt_sha256: SHA256 | None = None
    extraction_schema_version: str
    extraction_config_sha256: SHA256
    signal_family: MappingSignalFamilyEvidence
    forecast_horizon: MappingForecastHorizonEvidence
    action_rule: MappingActionRuleEvidence
    execution_style: MappingExecutionStyleEvidence
    required_data: MappingRequiredDataEvidence
    testability_status: TestabilityStatus
    testability_reason_codes: tuple[TestabilityReason, ...] = ()
    infra_risk: InfraRisk
    corroboration_status: CorroborationStatus
    contribution_status: ContributionStatus
    source_claim_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_persisted_contract(self) -> Self:
        llm_fields = (
            self.extraction_model_id,
            self.extraction_model_revision,
            self.extraction_prompt_version,
            self.extraction_prompt_sha256,
        )
        if self.extractor_kind is ExtractorKind.LLM:
            if any(value is None for value in llm_fields):
                raise ValueError("LLM mapping input requires exact model and prompt identity")
        elif any(value is not None for value in llm_fields):
            raise ValueError("deterministic mapping input cannot carry fabricated LLM identity")

        if len(self.official_corroboration_source_version_ids) != len(
            set(self.official_corroboration_source_version_ids)
        ):
            raise ValueError("official corroboration version identities must be unique")
        if len(self.source_claim_ids) != len(set(self.source_claim_ids)):
            raise ValueError("source claim identities must be unique")
        cited_claims = {
            *self.signal_family.claim_ids,
            *self.forecast_horizon.claim_ids,
            *self.action_rule.claim_ids,
            *self.execution_style.claim_ids,
            *self.required_data.claim_ids,
        }
        if not cited_claims <= set(self.source_claim_ids):
            raise ValueError("mapping evidence must reference persisted Phase 2 source claims")

        supported_action = self.action_rule.state is EvidenceState.SOURCE_SUPPORTED
        supported_horizon = self.forecast_horizon.state is EvidenceState.SOURCE_SUPPORTED
        expected_status = (
            TestabilityStatus.TESTABLE
            if supported_action and supported_horizon
            else TestabilityStatus.NON_TESTABLE
        )
        if self.testability_status is not expected_status:
            raise ValueError("mapping testability input conflicts with Phase 2 field evidence")
        expected_reasons: set[TestabilityReason] = set()
        if self.action_rule.state is EvidenceState.NOT_STATED:
            expected_reasons.add(TestabilityReason.MISSING_ACTION_RULE)
        elif self.action_rule.state is EvidenceState.AMBIGUOUS:
            expected_reasons.add(TestabilityReason.AMBIGUOUS_ACTION_RULE)
        if self.forecast_horizon.state is EvidenceState.NOT_STATED:
            expected_reasons.add(TestabilityReason.MISSING_FORECAST_HORIZON)
        elif self.forecast_horizon.state is EvidenceState.AMBIGUOUS:
            expected_reasons.add(TestabilityReason.AMBIGUOUS_FORECAST_HORIZON)
        if TestabilityReason.MISSING_RAW_TEXT in self.testability_reason_codes:
            expected_reasons.add(TestabilityReason.MISSING_RAW_TEXT)
        if set(self.testability_reason_codes) != expected_reasons:
            raise ValueError("mapping testability reasons conflict with Phase 2 evidence")
        if expected_status is TestabilityStatus.TESTABLE and self.testability_reason_codes:
            raise ValueError("testable mapping input cannot carry Phase 2 blockers")
        return self


class MappingDecision(StrictModel):
    canonical_family: CanonicalFamily | None
    verdict: ResearchVerdict
    matched_rule_ids: tuple[MappingRuleId, ...]
    reason_codes: tuple[MappingReasonCode, ...]
    mapper_rule_set_version: str
    mapper_rule_set_sha256: SHA256
    source_evidence: tuple[MappingEvidenceReference, ...]
    rationale_template_version: str
    input_sha256: SHA256

    @model_validator(mode="after")
    def validate_decision(self) -> Self:
        if not self.matched_rule_ids or not self.reason_codes:
            raise ValueError("mapping decisions require rule and reason evidence")
        if self.canonical_family is None:
            if self.verdict is not ResearchVerdict.NON_TESTABLE:
                raise ValueError("only NON_TESTABLE may leave canonical family unresolved")
            unresolved = {
                MappingReasonCode.MISSING_CANONICAL_FAMILY,
                MappingReasonCode.AMBIGUOUS_CANONICAL_FAMILY,
            }
            if not unresolved.intersection(self.reason_codes):
                raise ValueError("unresolved family requires an explicit mapping reason")
        if self.verdict is ResearchVerdict.BUILD_RESEARCH and self.canonical_family not in {
            CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING,
            CanonicalFamily.B_TIME_SERIES_MOMENTUM_REGIME,
            CanonicalFamily.C_OFFICIAL_EVENT_TEXT_OVERLAY,
        }:
            raise ValueError("BUILD_RESEARCH is limited to canonical families A, B, and C")
        return self


class ResearchMapping(StrictModel):
    mapping_id: UUID
    mapping_version: int = Field(ge=1)
    card_id: UUID
    card_sha256: SHA256
    mapping_input_sha256: SHA256
    extraction_request_id: UUID
    extraction_request_fingerprint: SHA256
    source_id: UUID
    source_version_id: UUID
    source_version: int = Field(ge=1)
    source_content_sha256: SHA256
    official_corroboration_source_version_ids: tuple[UUID, ...] = ()
    extractor_kind: ExtractorKind
    extractor_id: str
    extractor_version: str
    extraction_model_id: str | None = None
    extraction_model_revision: str | None = None
    extraction_prompt_version: str | None = None
    extraction_prompt_sha256: SHA256 | None = None
    extraction_schema_version: str
    extraction_config_sha256: SHA256
    canonical_family: CanonicalFamily | None
    verdict: ResearchVerdict
    matched_rule_ids: tuple[MappingRuleId, ...]
    reason_codes: tuple[MappingReasonCode, ...]
    mapper_rule_set_version: str
    mapper_rule_set_sha256: SHA256
    source_evidence: tuple[MappingEvidenceReference, ...]
    rationale_template_version: str
    created_at_utc: datetime

    @model_validator(mode="after")
    def normalize_and_validate(self) -> Self:
        self.created_at_utc = _utc(self.created_at_utc, "created_at_utc")
        MappingDecision(
            canonical_family=self.canonical_family,
            verdict=self.verdict,
            matched_rule_ids=self.matched_rule_ids,
            reason_codes=self.reason_codes,
            mapper_rule_set_version=self.mapper_rule_set_version,
            mapper_rule_set_sha256=self.mapper_rule_set_sha256,
            source_evidence=self.source_evidence,
            rationale_template_version=self.rationale_template_version,
            input_sha256=self.mapping_input_sha256,
        )
        return self


class MappingRationale(StrictModel):
    rationale_id: UUID
    mapping_id: UUID
    template_version: str
    markdown: str
    content_sha256: SHA256
    created_at_utc: datetime

    @model_validator(mode="after")
    def normalize_time(self) -> Self:
        if not self.markdown.strip():
            raise ValueError("mapping rationale cannot be blank")
        self.created_at_utc = _utc(self.created_at_utc, "created_at_utc")
        return self


class MappingWithRationale(StrictModel):
    mapping: ResearchMapping
    rationale: MappingRationale

    @model_validator(mode="after")
    def validate_lineage(self) -> Self:
        if self.rationale.mapping_id != self.mapping.mapping_id:
            raise ValueError("mapping rationale lineage does not match its mapping")
        if self.rationale.template_version != self.mapping.rationale_template_version:
            raise ValueError("mapping rationale template does not match its mapping")
        return self
