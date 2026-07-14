"""Strict public and persistence contracts for Phase 6 research-only pipelines."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Literal, Self
from uuid import UUID

from fable5_backtester.contracts import (
    CostLedgerEntry,
    CostScenario,
    GateCode,
    PromotionState,
    ResearchReturnStatus,
    TrialStatus,
)
from fable5_data.contracts import DataCapability
from fable5_mapping.models import CanonicalFamily
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from fable5_research.canonical import (
    PHASE6_ARTIFACT_HASH_DOMAIN,
    PHASE6_ATTEMPT_HASH_DOMAIN,
    PHASE6_BASELINE_HASH_DOMAIN,
    PHASE6_BOUNDARY_EXCLUSION_HASH_DOMAIN,
    PHASE6_BOUNDARY_EXCLUSION_NAMESPACE,
    PHASE6_COMPARISON_NAMESPACE,
    PHASE6_CONFIRMATION_INTERVAL_HASH_DOMAIN,
    PHASE6_CONFIRMATION_NAMESPACE,
    PHASE6_CORROBORATION_HASH_DOMAIN,
    PHASE6_CORROBORATION_NAMESPACE,
    PHASE6_CROSS_SECTION_MEMBER_HASH_DOMAIN,
    PHASE6_CROSS_SECTION_RANK_HASH_DOMAIN,
    PHASE6_EXTRACTION_NAMESPACE,
    PHASE6_FEATURE_LINEAGE_HASH_DOMAIN,
    PHASE6_FEATURE_ROW_HASH_DOMAIN,
    PHASE6_FEATURE_ROW_NAMESPACE,
    PHASE6_FIT_NAMESPACE,
    PHASE6_LABEL_SET_HASH_DOMAIN,
    PHASE6_LAGGED_OHLCV_BASELINE_HASH_DOMAIN,
    PHASE6_LIFECYCLE_TEST_HASH_DOMAIN,
    PHASE6_MODEL_OUTPUT_SET_HASH_DOMAIN,
    PHASE6_PIPELINE_INPUT_HASH_DOMAIN,
    PHASE6_REGIME_EVIDENCE_HASH_DOMAIN,
    PHASE6_REPRODUCTION_AUDIT_HASH_DOMAIN,
    PHASE6_REPRODUCTION_AUDIT_NAMESPACE,
    PHASE6_REPRODUCTION_SNAPSHOT_SET_HASH_DOMAIN,
    PHASE6_REQUEST_HASH_DOMAIN,
    PHASE6_RUN_NAMESPACE,
    PHASE6_SCORE_HASH_DOMAIN,
    PHASE6_SCORE_NAMESPACE,
    PHASE6_SNAPSHOT_BINDING_HASH_DOMAIN,
    PHASE6_SPECIFICATION_HASH_DOMAIN,
    PHASE6_TEXT_EXTRACTION_HASH_DOMAIN,
    PHASE6_TRANSFORM_FIT_HASH_DOMAIN,
    PHASE6_TRIAL_ALLOCATION_HASH_DOMAIN,
    PHASE6_TRIAL_COST_SET_HASH_DOMAIN,
    PHASE6_TRIAL_ECONOMICS_HASH_DOMAIN,
    PHASE6_TRIAL_SET_HASH_DOMAIN,
    domain_sha256,
    identity,
)

SHA256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
Identifier = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")]
GitSHA = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]

PHASE6_ARTIFACT_SCHEMA_VERSION = "phase6-research-artifact-v2"
PHASE6_SPECIFICATION_SCHEMA_VERSION = "phase6-research-specification-v2"
PHASE6_FEATURE_ROW_SCHEMA_VERSION = "phase6-research-feature-row-v1"
PHASE6_SCORE_SCHEMA_VERSION = "phase6-research-score-output-v1"
PHASE6_TEXT_EXTRACTION_SCHEMA_VERSION = "phase6-text-feature-extraction-v1"
PHASE6_RESEARCH_FIXTURE_VERSION = "phase6-deterministic-research-fixtures-v2"
PHASE6_MODEL_OUTPUT_SET_NAMESPACE = UUID("5d4d79be-eaa1-5d41-912c-407d5837bcc1")
PHASE6_LEDGER_CELL_NAMESPACE = UUID("7f6f32a5-7a42-5b3b-b61b-8deded858289")
_PHASE6_NUMERIC_QUANTUM = Decimal("0.000000000001")


def _utc(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value.astimezone(UTC)


def _ordered_unique(values: tuple[object, ...], field_name: str) -> None:
    rendered = tuple(str(value) for value in values)
    if rendered != tuple(sorted(rendered)):
        raise ValueError(f"{field_name} must be canonically sorted")
    if len(rendered) != len(set(rendered)):
        raise ValueError(f"{field_name} must be unique")


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(_PHASE6_NUMERIC_QUANTUM)


def _fit_statistics(values: tuple[Decimal, ...]) -> tuple[Decimal, Decimal]:
    if not values:
        raise ValueError("transform fit requires raw training values")
    exact_mean = sum(values, Decimal("0")) / Decimal(len(values))
    variance = sum(
        ((item - exact_mean) ** 2 for item in values),
        Decimal("0"),
    ) / Decimal(len(values))
    standard_deviation = variance.sqrt()
    return (
        _quantize(exact_mean),
        (_quantize(standard_deviation) if standard_deviation > 0 else Decimal("1.000000000000")),
    )


def _standardized_value(raw_value: Decimal, mean: Decimal, standard_deviation: Decimal) -> Decimal:
    standardized = _quantize((raw_value - mean) / standard_deviation)
    return min(Decimal("3"), max(Decimal("-3"), standardized))


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ResearchConfigurationId(StrEnum):
    A_PASS = "phase6-a-pass-v2"
    A_FAIL = "phase6-a-fail-cost-v2"
    B_PASS = "phase6-b-pass-v2"
    B_FAIL = "phase6-b-fail-crash-v2"
    C_PASS = "phase6-c-pass-v2"
    C_FAIL = "phase6-c-fail-corroboration-v2"


class ResearchRunStatus(StrEnum):
    COMPLETED = "completed"
    BLOCKED = "blocked"


class ResearchAttemptStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"
    ABANDONED = "abandoned"
    NO_RETURN = "no_return"
    BLOCKED = "blocked"


class BaselineOutcome(StrEnum):
    SURVIVES = "survives"
    REJECTED = "rejected"


class ResearchRunCreateRequest(StrictModel):
    mapping_id: UUID
    snapshot_ids: tuple[UUID, ...] = Field(min_length=1, max_length=len(DataCapability))
    research_configuration_id: ResearchConfigurationId

    @model_validator(mode="after")
    def validate_snapshot_ids(self) -> Self:
        _ordered_unique(self.snapshot_ids, "snapshot_ids")
        return self


class PolicyDeclaration(StrictModel):
    name: Identifier
    value: Decimal
    units: Identifier


class WalkForwardDeclaration(StrictModel):
    train_mode: Literal["expanding_past_only", "rolling_past_only"]
    outer_fold_count: int = Field(ge=2)
    inner_fold_count: int = Field(ge=2)
    purge_rule: Literal["label_interval_intersection_v1"] = "label_interval_intersection_v1"
    embargo_rule: None = None
    final_confirmation_rule: Literal["reserved_nonempty_untouched_interval_v1"] = (
        "reserved_nonempty_untouched_interval_v1"
    )


class ResearchPipelineSpecification(StrictModel):
    schema_version: Literal["phase6-research-specification-v2"] = "phase6-research-specification-v2"
    specification_id: Identifier
    specification_version: Identifier
    specification_sha256: SHA256
    family: CanonicalFamily
    signal_definition: str = Field(min_length=1, max_length=3000)
    score_semantics: Literal["research_score_only"] = "research_score_only"
    target_forecast_horizon: str = Field(min_length=1, max_length=256)
    required_capabilities: tuple[DataCapability, ...] = Field(min_length=1)
    feature_names: tuple[Identifier, ...] = Field(min_length=1)
    label_interval_rule: str = Field(min_length=1, max_length=1000)
    transaction_cost_model_id: Identifier
    slippage_model_id: Identifier
    walk_forward: WalkForwardDeclaration
    risk_limits: tuple[PolicyDeclaration, ...] = Field(min_length=1)
    required_audit_fields: tuple[Identifier, ...] = Field(min_length=10)
    llm_role: Literal["absent", "structured_text_extraction_only"]
    no_image_or_chart_pattern_classifier: Literal[True] = True
    pass_research_is_not_paper_approval: Literal[True] = True
    no_real_performance_claimed: Literal[True] = True

    @model_validator(mode="after")
    def validate_specification(self) -> Self:
        _ordered_unique(self.required_capabilities, "required_capabilities")
        _ordered_unique(self.feature_names, "feature_names")
        if len({item.name for item in self.risk_limits}) != len(self.risk_limits):
            raise ValueError("risk limit names must be unique")
        if len(self.required_audit_fields) != len(set(self.required_audit_fields)):
            raise ValueError("required audit fields must be unique")
        if self.family is CanonicalFamily.C_OFFICIAL_EVENT_TEXT_OVERLAY:
            if self.llm_role != "structured_text_extraction_only":
                raise ValueError("Family C must freeze the extraction-only LLM boundary")
        elif self.llm_role != "absent":
            raise ValueError("Families A/B cannot use an LLM")
        content = self.model_dump(
            mode="python",
            exclude={"specification_sha256"},
        )
        if self.specification_sha256 != domain_sha256(
            PHASE6_SPECIFICATION_HASH_DOMAIN,
            content,
        ):
            raise ValueError("research specification hash must match its complete preimage")
        return self


class ResearchSourceReference(StrictModel):
    capability: DataCapability
    snapshot_id: UUID
    snapshot_sha256: SHA256
    raw_observation_id: UUID
    observation_revision_id: UUID
    normalized_observation_id: UUID
    raw_payload_sha256: SHA256
    normalized_content_sha256: SHA256
    record_type: Identifier
    source_record_id: Identifier
    instrument_id: UUID | None
    listing_id: UUID | None
    available_at_utc: datetime
    valid_from_utc: datetime
    valid_to_utc: datetime | None

    @field_validator("available_at_utc", "valid_from_utc", "valid_to_utc")
    @classmethod
    def normalize_times(cls, value: datetime | None, info: object) -> datetime | None:
        if value is None:
            return None
        return _utc(value, getattr(info, "field_name", "source time"))


class PreparedRateRegimeObservation(StrictModel):
    series_id: Identifier
    vintage_id: Identifier
    released_at_utc: datetime
    rate_value: Decimal
    previous_rate_value: Decimal
    rate_change: Decimal
    source_reference: ResearchSourceReference

    @field_validator("released_at_utc")
    @classmethod
    def normalize_released_at(cls, value: datetime) -> datetime:
        return _utc(value, "released_at_utc")

    @model_validator(mode="after")
    def validate_rate_observation(self) -> Self:
        if self.source_reference.record_type != "macro_rate_observation":
            raise ValueError("rate regime observations require an exact macro source")
        if self.source_reference.available_at_utc != self.released_at_utc:
            raise ValueError("rate release time must match immutable source availability")
        if self.rate_change != self.rate_value - self.previous_rate_value:
            raise ValueError("rate change must equal current minus previous value")
        return self


class PreparedCrisisWindow(StrictModel):
    crisis_window_id: Identifier
    definition_method_id: Identifier
    declared_at_utc: datetime
    window_start_utc: datetime
    window_end_utc: datetime
    source_reference: ResearchSourceReference

    @field_validator("declared_at_utc", "window_start_utc", "window_end_utc")
    @classmethod
    def normalize_window_time(cls, value: datetime, info: object) -> datetime:
        return _utc(value, getattr(info, "field_name", "crisis window time"))

    @model_validator(mode="after")
    def validate_window(self) -> Self:
        if self.source_reference.record_type != "crisis_window_definition":
            raise ValueError("crisis windows require an exact definition source")
        if self.window_end_utc <= self.window_start_utc:
            raise ValueError("crisis window must be positive")
        if self.declared_at_utc >= self.window_start_utc:
            raise ValueError("crisis geometry must be declared before the window begins")
        if self.source_reference.available_at_utc != self.declared_at_utc:
            raise ValueError("crisis declaration time must match immutable source availability")
        return self


class PreparedRegimeEvidence(StrictModel):
    schema_version: Literal["phase6-prepared-regime-evidence-v2"] = (
        "phase6-prepared-regime-evidence-v2"
    )
    evidence_state: Literal["available", "unavailable"]
    rate_definition_id: Identifier
    rate_observations: tuple[PreparedRateRegimeObservation, ...] = ()
    crisis_definition_id: Identifier
    crisis_windows: tuple[PreparedCrisisWindow, ...] = ()
    unavailable_reason: Identifier | None = None
    evidence_sha256: SHA256

    @model_validator(mode="after")
    def validate_regime_evidence(self) -> Self:
        rate_keys = tuple(
            (item.released_at_utc, item.series_id, item.vintage_id)
            for item in self.rate_observations
        )
        crisis_keys = tuple(item.crisis_window_id for item in self.crisis_windows)
        if rate_keys != tuple(sorted(rate_keys)) or len(rate_keys) != len(set(rate_keys)):
            raise ValueError("rate observations must be unique and chronological")
        if crisis_keys != tuple(sorted(crisis_keys)) or len(crisis_keys) != len(set(crisis_keys)):
            raise ValueError("crisis windows must be unique and sorted")
        if self.evidence_state == "available":
            if (
                len(self.rate_observations) < 2
                or not self.crisis_windows
                or self.unavailable_reason is not None
                or not any(item.rate_change > 0 for item in self.rate_observations)
                or not any(item.rate_change < 0 for item in self.rate_observations)
            ):
                raise ValueError(
                    "available regime evidence requires both rate directions and crisis geometry"
                )
        elif self.rate_observations or self.crisis_windows or self.unavailable_reason is None:
            raise ValueError("unavailable regime evidence cannot contain invented observations")
        content = self.model_dump(mode="python", exclude={"evidence_sha256"})
        if self.evidence_sha256 != domain_sha256(PHASE6_REGIME_EVIDENCE_HASH_DOMAIN, content):
            raise ValueError("prepared regime evidence hash must bind its complete preimage")
        return self


class ResearchConfirmationInterval(StrictModel):
    schema_version: Literal["phase6-label-blind-confirmation-interval-v1"] = (
        "phase6-label-blind-confirmation-interval-v1"
    )
    confirmation_id: UUID
    confirmation_sha256: SHA256
    sample_id: Identifier
    interval_start_utc: datetime
    interval_end_utc: datetime
    opening_rule: Literal["reserved-before-design-label-remains-unopened-v1"] = (
        "reserved-before-design-label-remains-unopened-v1"
    )
    source_references: tuple[ResearchSourceReference, ...] = Field(min_length=1)
    label_value: None = None
    label_source_references: tuple[()] = ()
    label_opened: Literal[False] = False

    @field_validator("interval_start_utc", "interval_end_utc")
    @classmethod
    def normalize_interval_time(cls, value: datetime, info: object) -> datetime:
        return _utc(value, getattr(info, "field_name", "confirmation time"))

    @model_validator(mode="after")
    def validate_confirmation(self) -> Self:
        if self.interval_end_utc <= self.interval_start_utc:
            raise ValueError("confirmation interval must be positive")
        keys = tuple(
            (
                str(item.capability),
                str(item.snapshot_id),
                str(item.normalized_observation_id),
            )
            for item in self.source_references
        )
        if keys != tuple(sorted(keys)) or len(keys) != len(set(keys)):
            raise ValueError("confirmation sources must be exact, unique, and sorted")
        if any(item.available_at_utc > self.interval_start_utc for item in self.source_references):
            raise ValueError("confirmation geometry sources must be available before opening")
        content = self.model_dump(
            mode="python",
            exclude={"confirmation_id", "confirmation_sha256"},
        )
        expected = domain_sha256(PHASE6_CONFIRMATION_INTERVAL_HASH_DOMAIN, content)
        if self.confirmation_sha256 != expected or self.confirmation_id != identity(
            PHASE6_CONFIRMATION_NAMESPACE,
            expected,
        ):
            raise ValueError("confirmation identity must bind its label-blind preimage")
        return self


class ResearchBoundaryExclusion(StrictModel):
    schema_version: Literal["phase6-confirmation-boundary-exclusion-v1"] = (
        "phase6-confirmation-boundary-exclusion-v1"
    )
    exclusion_id: UUID
    exclusion_sha256: SHA256
    sample_id: Identifier
    decision_time_utc: datetime
    label_t0_utc: datetime
    label_t1_utc: datetime
    exclusion_rule: Literal["label-interval-intersects-confirmation-v1"] = (
        "label-interval-intersects-confirmation-v1"
    )
    label_value: None = None
    label_source_references: tuple[()] = ()
    label_opened: Literal[False] = False

    @field_validator("decision_time_utc", "label_t0_utc", "label_t1_utc")
    @classmethod
    def normalize_exclusion_time(cls, value: datetime, info: object) -> datetime:
        return _utc(value, getattr(info, "field_name", "boundary exclusion time"))

    @model_validator(mode="after")
    def validate_exclusion(self) -> Self:
        if self.label_t0_utc < self.decision_time_utc or self.label_t1_utc < self.label_t0_utc:
            raise ValueError("boundary exclusion interval must be ordered")
        content = self.model_dump(mode="python", exclude={"exclusion_id", "exclusion_sha256"})
        expected = domain_sha256(PHASE6_BOUNDARY_EXCLUSION_HASH_DOMAIN, content)
        if self.exclusion_sha256 != expected or self.exclusion_id != identity(
            PHASE6_BOUNDARY_EXCLUSION_NAMESPACE,
            expected,
        ):
            raise ValueError("boundary exclusion identity must bind its label-blind preimage")
        return self


class ResearchSnapshotBinding(StrictModel):
    ordinal: int = Field(ge=1)
    snapshot_id: UUID
    snapshot_sha256: SHA256
    capability: DataCapability
    binding_sha256: SHA256
    mapping_id: UUID
    mapping_input_sha256: SHA256
    as_of_utc: datetime
    quality_status: Identifier

    @field_validator("as_of_utc")
    @classmethod
    def normalize_as_of(cls, value: datetime) -> datetime:
        return _utc(value, "as_of_utc")

    @model_validator(mode="after")
    def validate_binding_hash(self) -> Self:
        content = self.model_dump(mode="python", exclude={"binding_sha256"})
        if self.binding_sha256 != domain_sha256(
            PHASE6_SNAPSHOT_BINDING_HASH_DOMAIN,
            content,
        ):
            raise ValueError("snapshot binding hash must match its complete preimage")
        return self


class ResearchFeatureValue(StrictModel):
    feature_name: Identifier
    formula_id: Identifier
    raw_value: Decimal
    transformed_value: Decimal
    contribution: Decimal
    source_references: tuple[ResearchSourceReference, ...] = Field(min_length=1)
    train_fit_id: UUID | None

    @model_validator(mode="after")
    def validate_source_order(self) -> Self:
        keys = tuple(
            (
                str(item.capability),
                str(item.snapshot_id),
                str(item.normalized_observation_id),
            )
            for item in self.source_references
        )
        if keys != tuple(sorted(keys)) or len(keys) != len(set(keys)):
            raise ValueError("feature source references must be unique and sorted")
        return self


class ResearchFeatureRow(StrictModel):
    schema_version: Literal["phase6-research-feature-row-v1"] = "phase6-research-feature-row-v1"
    ordinal: int = Field(ge=1)
    row_id: UUID
    row_sha256: SHA256
    sample_id: Identifier
    entity_id: Identifier
    sector_id: Identifier | None
    decision_time_utc: datetime
    label_t0_utc: datetime
    label_t1_utc: datetime
    label_value: Decimal
    label_source_references: tuple[ResearchSourceReference, ...] = Field(min_length=1)
    features: tuple[ResearchFeatureValue, ...] = Field(min_length=1)
    composite_score: Decimal
    score_semantics: Literal["research_score_only"] = "research_score_only"
    source_lineage_sha256: SHA256

    @field_validator("decision_time_utc", "label_t0_utc", "label_t1_utc")
    @classmethod
    def normalize_times(cls, value: datetime, info: object) -> datetime:
        return _utc(value, getattr(info, "field_name", "feature row time"))

    @model_validator(mode="after")
    def validate_row(self) -> Self:
        if self.label_t0_utc < self.decision_time_utc or self.label_t1_utc < self.label_t0_utc:
            raise ValueError("label interval must begin no earlier than the decision")
        names = tuple(item.feature_name for item in self.features)
        if names != tuple(sorted(names)) or len(names) != len(set(names)):
            raise ValueError("feature values must be unique and sorted")
        label_keys = tuple(
            (
                str(item.capability),
                str(item.snapshot_id),
                str(item.normalized_observation_id),
            )
            for item in self.label_source_references
        )
        if label_keys != tuple(sorted(label_keys)) or len(label_keys) != len(set(label_keys)):
            raise ValueError("label source references must be unique and sorted")
        feature_references = tuple(
            reference for feature in self.features for reference in feature.source_references
        )
        if any(item.available_at_utc > self.decision_time_utc for item in feature_references):
            raise ValueError("feature sources must be available by the decision time")
        if any(item.available_at_utc > self.label_t1_utc for item in self.label_source_references):
            raise ValueError("label sources must be available by the label interval end")
        if not any(
            item.available_at_utc > self.decision_time_utc for item in self.label_source_references
        ):
            raise ValueError("label evidence must contain a later observation")
        expected_lineage = domain_sha256(
            PHASE6_FEATURE_LINEAGE_HASH_DOMAIN,
            {
                "feature_source_references": tuple(
                    item.source_references for item in self.features
                ),
                "label_source_references": self.label_source_references,
            },
        )
        if self.source_lineage_sha256 != expected_lineage:
            raise ValueError("feature row source-lineage hash must match exact references")
        content = self.model_dump(mode="python", exclude={"row_id", "row_sha256"})
        expected = domain_sha256(PHASE6_FEATURE_ROW_HASH_DOMAIN, content)
        if self.row_sha256 != expected or self.row_id != identity(
            PHASE6_FEATURE_ROW_NAMESPACE,
            expected,
        ):
            raise ValueError("feature row identity must derive from its complete preimage")
        if sum((item.contribution for item in self.features), Decimal("0")) != self.composite_score:
            raise ValueError("composite score must equal exact feature contributions")
        return self


class ResearchScoreOutput(StrictModel):
    schema_version: Literal["phase6-research-score-output-v1"] = "phase6-research-score-output-v1"
    ordinal: int = Field(ge=1)
    score_id: UUID
    output_sha256: SHA256
    sample_id: Identifier
    entity_id: Identifier
    model_id: Identifier
    research_score: Decimal
    score_semantics: Literal["research_score_only"] = "research_score_only"
    explanation: str = Field(min_length=1, max_length=4000)
    explanation_sha256: SHA256
    feature_row_id: UUID

    @model_validator(mode="after")
    def validate_output(self) -> Self:
        expected_explanation = domain_sha256("phase6-research-explanation-v1", self.explanation)
        if self.explanation_sha256 != expected_explanation:
            raise ValueError("explanation hash must match exact explanation text")
        content = self.model_dump(mode="python", exclude={"score_id", "output_sha256"})
        expected = domain_sha256(PHASE6_SCORE_HASH_DOMAIN, content)
        if self.output_sha256 != expected or self.score_id != identity(
            PHASE6_SCORE_NAMESPACE,
            expected,
        ):
            raise ValueError("score output identity must derive from its complete preimage")
        return self


class ResearchTransformTrainingSample(StrictModel):
    ordinal: int = Field(ge=1)
    sample_id: Identifier
    entity_id: UUID
    information_time_utc: datetime
    raw_value: Decimal
    source_references: tuple[ResearchSourceReference, ...] = Field(min_length=1)

    @field_validator("information_time_utc")
    @classmethod
    def normalize_information_time(cls, value: datetime) -> datetime:
        return _utc(value, "transform training sample information time")

    @model_validator(mode="after")
    def validate_training_sample(self) -> Self:
        reference_keys = tuple(
            (
                str(item.capability),
                str(item.snapshot_id),
                str(item.normalized_observation_id),
            )
            for item in self.source_references
        )
        if reference_keys != tuple(sorted(reference_keys)) or len(reference_keys) != len(
            set(reference_keys)
        ):
            raise ValueError("transform training sample sources must be unique and sorted")
        if not any(item.listing_id == self.entity_id for item in self.source_references):
            raise ValueError("transform training sample sources must bind its exact entity")
        if any(
            item.available_at_utc > self.information_time_utc for item in self.source_references
        ):
            raise ValueError(
                "transform training sample sources must be available by its information time"
            )
        return self


class ResearchTransformFit(StrictModel):
    fit_id: UUID
    fold_id: UUID
    transform_id: Identifier
    feature_name: Identifier
    sector_id: Identifier | None
    train_sample_ids: tuple[Identifier, ...] = Field(min_length=2)
    train_entity_ids: tuple[UUID, ...] = Field(min_length=2)
    train_samples: tuple[ResearchTransformTrainingSample, ...] = Field(min_length=2)
    prohibited_sample_ids: tuple[Identifier, ...] = ()
    mean: Decimal
    standard_deviation: Decimal = Field(gt=0)
    source_references: tuple[ResearchSourceReference, ...] = Field(min_length=1)
    statistic_sha256: SHA256

    @model_validator(mode="after")
    def validate_train_only(self) -> Self:
        if len(self.train_sample_ids) != len(set(self.train_sample_ids)):
            raise ValueError("transform fit train ids must be unique")
        _ordered_unique(self.train_entity_ids, "transform fit train entity ids")
        if tuple(item.ordinal for item in self.train_samples) != tuple(
            range(1, len(self.train_samples) + 1)
        ):
            raise ValueError("transform fit training sample ordinals must be contiguous")
        if tuple(item.sample_id for item in self.train_samples) != self.train_sample_ids:
            raise ValueError("transform fit train ids must match ordered raw sample evidence")
        if {item.entity_id for item in self.train_samples} != set(self.train_entity_ids):
            raise ValueError("transform fit entities must match ordered raw sample evidence")
        if set(self.train_sample_ids) & set(self.prohibited_sample_ids):
            raise ValueError("transform fit cannot contain test, purged, or confirmation ids")
        expected_mean, expected_standard_deviation = _fit_statistics(
            tuple(item.raw_value for item in self.train_samples)
        )
        if self.mean != expected_mean or self.standard_deviation != expected_standard_deviation:
            raise ValueError("transform fit statistics must derive from ordered raw train values")
        sample_references = {
            item.normalized_observation_id: item
            for sample in self.train_samples
            for item in sample.source_references
        }
        expected_references = tuple(
            sorted(
                sample_references.values(),
                key=lambda item: (
                    str(item.capability),
                    str(item.snapshot_id),
                    str(item.normalized_observation_id),
                ),
            )
        )
        if self.source_references != expected_references:
            raise ValueError("transform fit sources must equal its ordered raw sample evidence")
        referenced_listing_ids = {
            item.listing_id for item in self.source_references if item.listing_id is not None
        }
        if referenced_listing_ids != set(self.train_entity_ids):
            raise ValueError(
                "transform fit source evidence must cover exactly its distinct train entities"
            )
        reference_keys = tuple(
            (
                str(item.capability),
                str(item.snapshot_id),
                str(item.normalized_observation_id),
            )
            for item in self.source_references
        )
        if reference_keys != tuple(sorted(reference_keys)) or len(reference_keys) != len(
            set(reference_keys)
        ):
            raise ValueError("transform fit source references must be unique and sorted")
        content = self.model_dump(mode="python", exclude={"fit_id", "statistic_sha256"})
        expected = domain_sha256(PHASE6_TRANSFORM_FIT_HASH_DOMAIN, content)
        if self.statistic_sha256 != expected or self.fit_id != identity(
            PHASE6_FIT_NAMESPACE,
            expected,
        ):
            raise ValueError("transform fit identity must derive from exact train-only inputs")
        return self


def frozen_depth_two_tree_score(features: tuple[ResearchFeatureValue, ...]) -> Decimal:
    """Return the frozen nonlinear comparison score from declared Phase 6 features."""

    values = {item.feature_name: item.transformed_value for item in features}
    required = {"momentum", "quality", "volatility"}
    if not required.issubset(values):
        raise ValueError("frozen nonlinear comparison requires momentum, quality, and volatility")
    if values["momentum"] >= 0:
        return (
            Decimal("0.35") if values["momentum"] >= Decimal("1.545611434791") else Decimal("-0.35")
        )
    return Decimal("0.35") if values["volatility"] >= 0 else Decimal("0.15")


def _hash_control_weight(*, salt: str, sample_id: str) -> Decimal:
    digest = hashlib.sha256(f"{salt}:{sample_id}".encode()).hexdigest()
    return Decimal(int(digest, 16) % 2)


def frozen_trial_allocation(
    *,
    trial_key: str,
    model_id: str,
    sample_id: str,
    model_output: Decimal,
) -> tuple[Decimal, str]:
    """Return one frozen, label-independent synthetic long/flat allocation rule."""

    threshold_rules: dict[str, tuple[Decimal, str]] = {
        "sector-relative-rank-linear-v1": (
            Decimal("0"),
            "phase6-a-score-positive-long-flat-v1",
        ),
        "frozen-depth-two-tree-v2": (
            Decimal("0"),
            "phase6-a-tree-score-positive-long-flat-v1",
        ),
        "lagged-trend-linear-v1": (
            Decimal("0.002119768628"),
            "phase6-b-score-ge-0.002119768628-long-flat-v1",
        ),
        "lagged-return-only-v1": (
            Decimal("0.132423292369"),
            "phase6-b-score-ge-0.132423292369-long-flat-v1",
        ),
        "conventional-linear-text-overlay-v1": (
            Decimal("0.2"),
            "phase6-c-score-ge-0.2-long-flat-v1",
        ),
        "non-text-event-baseline-v1": (
            Decimal("-0.06"),
            "phase6-c-score-ge-minus-0.06-long-flat-v1",
        ),
    }
    threshold_rule = threshold_rules.get(model_id)
    if threshold_rule is not None:
        threshold, rule_id = threshold_rule
        comparator_passes = (
            model_output > threshold if threshold == 0 else model_output >= threshold
        )
        return Decimal("1") if comparator_passes else Decimal("0"), rule_id
    control_rules: dict[str, tuple[str, str]] = {
        "zero-information-rank-v1": (
            "baseline-14",
            "phase6-a-hash-parity-baseline-control-v14",
        ),
        "zero-information-time-series-v1": (
            "control-1424",
            "phase6-b-hash-parity-zero-control-v1424",
        ),
        "event-tag-only-baseline-v1": (
            "zero-6",
            "phase6-c-hash-parity-event-control-v6",
        ),
    }
    control_rule = control_rules.get(model_id)
    if control_rule is None and model_id == "negative-control-v1":
        if sample_id.startswith("phase6-a-"):
            control_rule = (
                "negative-35",
                "phase6-a-hash-parity-negative-control-v35",
            )
        elif sample_id.startswith("phase6-b-"):
            control_rule = (
                "control-20",
                "phase6-b-hash-parity-negative-control-v20",
            )
        elif sample_id.startswith("phase6-c-"):
            control_rule = (
                "negative-2",
                "phase6-c-hash-parity-negative-control-v2",
            )
    if control_rule is None:
        raise ValueError("model has no frozen synthetic long-or-flat allocation rule")
    salt, rule_id = control_rule
    return _hash_control_weight(salt=salt, sample_id=sample_id), rule_id


class CrossSectionRankMember(StrictModel):
    entity_id: Identifier
    instrument_id: UUID
    listing_id: UUID
    sector_id: Identifier
    membership_universe_id: Identifier
    membership_status: Literal["included"] = "included"
    membership_source_reference: ResearchSourceReference
    features: tuple[ResearchFeatureValue, ...] = Field(min_length=6, max_length=6)
    linear_score: Decimal
    linear_rank: int = Field(ge=1)
    nonlinear_score: Decimal
    label_t0_utc: datetime
    label_t1_utc: datetime
    label_value: Decimal
    label_source_references: tuple[ResearchSourceReference, ...] = Field(min_length=1)
    label_sha256: SHA256
    source_lineage_sha256: SHA256
    member_sha256: SHA256

    @field_validator("label_t0_utc", "label_t1_utc")
    @classmethod
    def normalize_label_time(cls, value: datetime, info: object) -> datetime:
        return _utc(value, getattr(info, "field_name", "cross-section label time"))

    @model_validator(mode="after")
    def validate_member(self) -> Self:
        if self.label_t1_utc < self.label_t0_utc:
            raise ValueError("cross-section member label interval must be ordered")
        membership = self.membership_source_reference
        if (
            membership.capability is not DataCapability.UNIVERSE_MEMBERSHIP
            or membership.record_type != "universe_membership"
            or membership.instrument_id != self.instrument_id
            or membership.listing_id != self.listing_id
        ):
            raise ValueError("cross-section membership must bind the exact member identity")
        if (
            membership.available_at_utc > self.label_t0_utc
            or membership.valid_from_utc > self.label_t0_utc
            or (
                membership.valid_to_utc is not None and self.label_t0_utc >= membership.valid_to_utc
            )
        ):
            raise ValueError("cross-section member requires an exact PIT included interval")
        names = tuple(item.feature_name for item in self.features)
        if names != (
            "liquidity",
            "momentum",
            "quality",
            "turnover",
            "value",
            "volatility",
        ):
            raise ValueError("cross-section members require the six frozen sorted features")
        if sum((item.contribution for item in self.features), Decimal("0")) != self.linear_score:
            raise ValueError("cross-section linear score must equal exact feature contributions")
        if self.nonlinear_score != frozen_depth_two_tree_score(self.features):
            raise ValueError("cross-section nonlinear score must use the frozen depth-two tree")
        label_keys = tuple(
            (
                str(item.capability),
                str(item.snapshot_id),
                str(item.normalized_observation_id),
            )
            for item in self.label_source_references
        )
        if label_keys != tuple(sorted(label_keys)) or len(label_keys) != len(set(label_keys)):
            raise ValueError("cross-section label sources must be unique and sorted")
        expected_label = domain_sha256(
            PHASE6_LABEL_SET_HASH_DOMAIN,
            (
                self.entity_id,
                self.label_value,
                self.label_t0_utc,
                self.label_t1_utc,
                self.label_source_references,
            ),
        )
        if self.label_sha256 != expected_label:
            raise ValueError("cross-section label hash must bind exact forward evidence")
        expected_lineage = domain_sha256(
            PHASE6_FEATURE_LINEAGE_HASH_DOMAIN,
            tuple(item.source_references for item in self.features),
        )
        if self.source_lineage_sha256 != expected_lineage:
            raise ValueError("cross-section member lineage must bind every feature source")
        content = self.model_dump(mode="python", exclude={"member_sha256"})
        if self.member_sha256 != domain_sha256(PHASE6_CROSS_SECTION_MEMBER_HASH_DOMAIN, content):
            raise ValueError("cross-section member hash must bind its complete preimage")
        return self


class CrossSectionRankEvidence(StrictModel):
    ordinal: int = Field(ge=1)
    decision_time_utc: datetime
    selected_entity_id: Identifier
    selected_linear_rank: int = Field(ge=1)
    selected_nonlinear_score: Decimal
    eligible_members: tuple[CrossSectionRankMember, ...] = Field(min_length=2)
    nonlinear_formula_id: Literal["frozen-depth-two-tree-momentum-quality-volatility-v1"] = (
        "frozen-depth-two-tree-momentum-quality-volatility-v1"
    )
    evidence_sha256: SHA256

    @field_validator("decision_time_utc")
    @classmethod
    def normalize_decision_time(cls, value: datetime) -> datetime:
        return _utc(value, "decision_time_utc")

    @model_validator(mode="after")
    def validate_cross_section(self) -> Self:
        entity_ids = tuple(item.entity_id for item in self.eligible_members)
        if entity_ids != tuple(sorted(entity_ids)) or len(entity_ids) != len(set(entity_ids)):
            raise ValueError("cross-section members must be unique and canonically sorted")
        ranks = tuple(sorted(item.linear_rank for item in self.eligible_members))
        if ranks != tuple(range(1, len(self.eligible_members) + 1)):
            raise ValueError("cross-section linear ranks must be contiguous")
        selected = next(
            (item for item in self.eligible_members if item.entity_id == self.selected_entity_id),
            None,
        )
        if (
            selected is None
            or selected.linear_rank != self.selected_linear_rank
            or selected.nonlinear_score != self.selected_nonlinear_score
        ):
            raise ValueError("selected cross-section rank must match its exact member")
        if self.selected_linear_rank != 1:
            raise ValueError("selected cross-section member must have linear rank one")
        content = self.model_dump(mode="python", exclude={"evidence_sha256"})
        if self.evidence_sha256 != domain_sha256(PHASE6_CROSS_SECTION_RANK_HASH_DOMAIN, content):
            raise ValueError("cross-section rank hash must bind its complete preimage")
        return self


class ResearchModelOutput(StrictModel):
    ordinal: int = Field(ge=1)
    sample_id: Identifier
    output_value: Decimal


class ResearchLedgerCell(StrictModel):
    schema_version: Literal["phase6-research-ledger-cell-v2"] = "phase6-research-ledger-cell-v2"
    ordinal: int = Field(ge=1)
    cell_id: UUID
    cell_sha256: SHA256
    trial_key: Identifier
    model_id: Identifier
    sample_id: Identifier
    model_output: Decimal
    model_output_sha256: SHA256
    synthetic_research_weight: Decimal = Field(ge=Decimal("0"), le=Decimal("1"))
    allocation_rule_id: Literal[
        "phase6-a-score-positive-long-flat-v1",
        "phase6-a-tree-score-positive-long-flat-v1",
        "phase6-a-hash-parity-baseline-control-v14",
        "phase6-a-hash-parity-negative-control-v35",
        "phase6-b-score-ge-0.002119768628-long-flat-v1",
        "phase6-b-score-ge-0.132423292369-long-flat-v1",
        "phase6-b-hash-parity-zero-control-v1424",
        "phase6-b-hash-parity-negative-control-v20",
        "phase6-c-score-ge-0.2-long-flat-v1",
        "phase6-c-score-ge-minus-0.06-long-flat-v1",
        "phase6-c-hash-parity-event-control-v6",
        "phase6-c-hash-parity-negative-control-v2",
    ]
    return_status: ResearchReturnStatus
    label_t0_utc: datetime
    label_t1_utc: datetime
    label_value: Decimal
    label_source_references: tuple[ResearchSourceReference, ...] = Field(min_length=1)
    label_sha256: SHA256
    payoff_formula_id: Literal["phase6-long-flat-weight-times-label-quantized-v1"] = (
        "phase6-long-flat-weight-times-label-quantized-v1"
    )
    synthetic_gross_return: Decimal

    @field_validator("label_t0_utc", "label_t1_utc")
    @classmethod
    def normalize_ledger_times(cls, value: datetime, info: object) -> datetime:
        return _utc(value, getattr(info, "field_name", "research ledger time"))

    @model_validator(mode="after")
    def validate_ledger_cell(self) -> Self:
        if self.label_t1_utc < self.label_t0_utc:
            raise ValueError("research ledger label interval must be ordered")
        label_content = (
            self.sample_id,
            self.label_value,
            self.label_t0_utc,
            self.label_t1_utc,
            self.label_source_references,
        )
        if self.label_sha256 != domain_sha256(
            "phase6-research-ledger-label-v1",
            label_content,
        ):
            raise ValueError("research ledger label hash must bind exact persisted evidence")
        expected_weight, expected_rule = frozen_trial_allocation(
            trial_key=self.trial_key,
            model_id=self.model_id,
            sample_id=self.sample_id,
            model_output=self.model_output,
        )
        if self.allocation_rule_id != expected_rule:
            raise ValueError("research allocation rule must match its frozen trial role")
        if self.synthetic_research_weight != expected_weight:
            raise ValueError("research weight must derive from the frozen long-or-flat rule")
        expected_status = (
            ResearchReturnStatus.OBSERVED
            if self.synthetic_research_weight == 1
            else ResearchReturnStatus.NO_TRADE
        )
        if self.return_status is not expected_status:
            raise ValueError("research return status must match its long-or-flat weight")
        if self.synthetic_gross_return != _quantize(
            self.synthetic_research_weight * self.label_value
        ):
            raise ValueError("research ledger gross return must use the frozen payoff formula")
        content = self.model_dump(mode="python", exclude={"cell_id", "cell_sha256"})
        expected = domain_sha256("phase6-research-ledger-cell-v2", content)
        if self.cell_sha256 != expected or self.cell_id != identity(
            PHASE6_LEDGER_CELL_NAMESPACE,
            expected,
        ):
            raise ValueError("research ledger cell identity must bind its complete preimage")
        return self


class ResearchModelOutputSet(StrictModel):
    schema_version: Literal["phase6-phase5-model-output-set-v2"] = (
        "phase6-phase5-model-output-set-v2"
    )
    ordinal: int = Field(ge=1)
    output_set_id: UUID
    output_set_sha256: SHA256
    model_output_sha256: SHA256
    trial_key: Identifier
    model_id: Identifier
    output_semantics: Literal["synthetic_research_model_output"] = "synthetic_research_model_output"
    outputs: tuple[ResearchModelOutput, ...] = Field(min_length=1)
    ledger_cells: tuple[ResearchLedgerCell, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_output_set(self) -> Self:
        if tuple(item.ordinal for item in self.outputs) != tuple(range(1, len(self.outputs) + 1)):
            raise ValueError("model output set ordinals must be contiguous")
        sample_ids = tuple(item.sample_id for item in self.outputs)
        if len(sample_ids) != len(set(sample_ids)):
            raise ValueError("model output set sample ids must be unique")
        values = tuple(
            (item.sample_id, item.output_value)
            for item in sorted(self.outputs, key=lambda item: item.sample_id)
        )
        if self.model_output_sha256 != domain_sha256(
            PHASE6_MODEL_OUTPUT_SET_HASH_DOMAIN,
            values,
        ):
            raise ValueError("model output hash must bind exact persisted label-independent cells")
        if tuple(item.ordinal for item in self.ledger_cells) != tuple(
            range(1, len(self.ledger_cells) + 1)
        ) or tuple((item.sample_id, item.model_output) for item in self.ledger_cells) != tuple(
            (item.sample_id, item.output_value) for item in self.outputs
        ):
            raise ValueError("research ledger cells must cover exact model outputs in order")
        if any(
            item.trial_key != self.trial_key
            or item.model_id != self.model_id
            or item.model_output_sha256 != self.model_output_sha256
            for item in self.ledger_cells
        ):
            raise ValueError("research ledger cells must bind their exact model output set")
        content = self.model_dump(
            mode="python",
            exclude={"output_set_id", "output_set_sha256"},
        )
        expected = domain_sha256("phase6-phase5-model-output-registry-entry-v2", content)
        if self.output_set_sha256 != expected or self.output_set_id != identity(
            PHASE6_MODEL_OUTPUT_SET_NAMESPACE,
            expected,
        ):
            raise ValueError("model output set identity must bind its complete preimage")
        return self


class ResearchTrialSampleEconomics(StrictModel):
    schema_version: Literal["phase6-trial-sample-economics-v1"] = "phase6-trial-sample-economics-v1"
    ordinal: int = Field(ge=1)
    sample_id: Identifier
    model_output: Decimal
    synthetic_research_weight: Decimal = Field(ge=Decimal("0"), le=Decimal("1"))
    return_status: ResearchReturnStatus
    synthetic_gross_return: Decimal
    cost_entries: tuple[CostLedgerEntry, ...] = Field(min_length=3, max_length=3)
    evidence_sha256: SHA256

    @model_validator(mode="after")
    def validate_sample_economics(self) -> Self:
        if self.synthetic_research_weight not in {Decimal("0"), Decimal("1")}:
            raise ValueError("synthetic research weight must be exactly zero or one")
        if tuple(item.scenario for item in self.cost_entries) != tuple(CostScenario):
            raise ValueError("trial sample economics requires every cost scenario in order")
        if any(
            item.sample_id != self.sample_id or item.gross_return != self.synthetic_gross_return
            for item in self.cost_entries
        ):
            raise ValueError("trial costs must bind the exact sample and gross return")
        expected_status = (
            ResearchReturnStatus.OBSERVED
            if self.synthetic_research_weight == 1
            else ResearchReturnStatus.NO_TRADE
        )
        if self.return_status is not expected_status:
            raise ValueError("trial sample status must match its synthetic research weight")
        if self.return_status is ResearchReturnStatus.NO_TRADE and any(
            item.total_cost != 0
            or item.net_return != 0
            or item.requested_quantity != 0
            or item.filled_quantity != 0
            or item.participation_rate != 0
            for item in self.cost_entries
        ):
            raise ValueError("no-trade sample economics must have an exact zero footprint")
        content = self.model_dump(mode="python", exclude={"evidence_sha256"})
        if self.evidence_sha256 != domain_sha256(PHASE6_TRIAL_ALLOCATION_HASH_DOMAIN, content):
            raise ValueError("trial sample economics hash must bind every cost component")
        return self


class ResearchTrialEconomics(StrictModel):
    schema_version: Literal["phase6-trial-economics-v1"] = "phase6-trial-economics-v1"
    ordinal: int = Field(ge=1)
    trial_key: Identifier
    model_id: Identifier
    output_set_sha256: SHA256
    sample_economics: tuple[ResearchTrialSampleEconomics, ...] = Field(min_length=1)
    cost_set_sha256: SHA256
    economics_sha256: SHA256

    @model_validator(mode="after")
    def validate_trial_economics(self) -> Self:
        if tuple(item.ordinal for item in self.sample_economics) != tuple(
            range(1, len(self.sample_economics) + 1)
        ):
            raise ValueError("trial sample economics ordinals must be contiguous")
        sample_ids = tuple(item.sample_id for item in self.sample_economics)
        if sample_ids != tuple(sorted(sample_ids)) or len(sample_ids) != len(set(sample_ids)):
            raise ValueError("trial sample economics must be unique and canonically sorted")
        cost_entries = tuple(
            sorted(
                (entry for item in self.sample_economics for entry in item.cost_entries),
                key=lambda entry: entry.ordinal,
            )
        )
        if tuple(item.ordinal for item in cost_entries) != tuple(range(len(cost_entries))):
            raise ValueError("trial cost entries must retain the complete canonical ledger order")
        expected = domain_sha256(
            PHASE6_TRIAL_COST_SET_HASH_DOMAIN,
            tuple(
                (entry.sample_id, entry.scenario, entry.cost_entry_sha256) for entry in cost_entries
            ),
        )
        if self.cost_set_sha256 != expected:
            raise ValueError("trial cost-set hash must bind every sample allocation and cost")
        content = self.model_dump(mode="python", exclude={"economics_sha256"})
        if self.economics_sha256 != domain_sha256(PHASE6_TRIAL_ECONOMICS_HASH_DOMAIN, content):
            raise ValueError("trial economics hash must bind its complete preimage")
        return self


class PreparedPipelineReproductionAudit(StrictModel):
    """Hash-bound proof that immutable snapshots reproduce the prepared payload."""

    schema_version: Literal["phase6-prepared-source-reproduction-audit-v1"] = (
        "phase6-prepared-source-reproduction-audit-v1"
    )
    audit_id: UUID
    audit_sha256: SHA256
    configuration_id: ResearchConfigurationId
    snapshot_bindings: tuple[ResearchSnapshotBinding, ...] = Field(min_length=1)
    snapshot_set_sha256: SHA256
    supplied_pipeline_input_sha256: SHA256
    reproduced_pipeline_input_sha256: SHA256
    supplied_payload_sha256: SHA256
    reproduced_payload_sha256: SHA256
    exact_match: Literal[True] = True

    @model_validator(mode="after")
    def validate_reproduction_audit(self) -> Self:
        binding_keys = tuple(
            (str(item.snapshot_id), item.snapshot_sha256) for item in self.snapshot_bindings
        )
        if binding_keys != tuple(sorted(binding_keys)) or len(binding_keys) != len(
            set(binding_keys)
        ):
            raise ValueError("reproduction snapshot bindings must be unique and sorted")
        if self.snapshot_set_sha256 != domain_sha256(
            PHASE6_REPRODUCTION_SNAPSHOT_SET_HASH_DOMAIN,
            self.snapshot_bindings,
        ):
            raise ValueError("reproduction snapshot-set hash must bind every immutable snapshot")
        if (
            self.supplied_pipeline_input_sha256 != self.reproduced_pipeline_input_sha256
            or self.supplied_payload_sha256 != self.reproduced_payload_sha256
        ):
            raise ValueError("successful reproduction audit requires exact prepared-payload hashes")
        content = self.model_dump(mode="python", exclude={"audit_id", "audit_sha256"})
        expected = domain_sha256(PHASE6_REPRODUCTION_AUDIT_HASH_DOMAIN, content)
        if self.audit_sha256 != expected or self.audit_id != identity(
            PHASE6_REPRODUCTION_AUDIT_NAMESPACE,
            expected,
        ):
            raise ValueError("reproduction audit identity must bind its complete preimage")
        return self


class ResearchBaselineComparison(StrictModel):
    ordinal: int = Field(ge=1)
    comparison_id: UUID
    comparison_sha256: SHA256
    candidate_model_id: Identifier
    baseline_model_id: Identifier
    evaluation_scope: Literal["descriptive_all_prepared_rows_not_used_for_selection"] = (
        "descriptive_all_prepared_rows_not_used_for_selection"
    )
    used_for_selection: Literal[False] = False
    metric_id: Identifier
    candidate_metric: Decimal
    baseline_metric: Decimal
    candidate_outputs: tuple[ResearchModelOutput, ...] = Field(min_length=1)
    baseline_outputs: tuple[ResearchModelOutput, ...] = Field(min_length=1)
    candidate_output_sha256: SHA256
    baseline_output_sha256: SHA256
    label_sha256: SHA256
    outcome: BaselineOutcome
    reason_codes: tuple[Identifier, ...]

    @model_validator(mode="after")
    def validate_comparison(self) -> Self:
        for outputs, field_name in (
            (self.candidate_outputs, "candidate"),
            (self.baseline_outputs, "baseline"),
        ):
            if tuple(item.ordinal for item in outputs) != tuple(range(1, len(outputs) + 1)):
                raise ValueError(f"{field_name} model output ordinals must be contiguous")
            sample_ids = tuple(item.sample_id for item in outputs)
            if len(sample_ids) != len(set(sample_ids)):
                raise ValueError(f"{field_name} model output sample ids must be unique")
        if tuple(item.sample_id for item in self.candidate_outputs) != tuple(
            item.sample_id for item in self.baseline_outputs
        ):
            raise ValueError("candidate and baseline outputs must cover the exact same samples")
        candidate_values = tuple(
            (item.sample_id, item.output_value) for item in self.candidate_outputs
        )
        baseline_values = tuple(
            (item.sample_id, item.output_value) for item in self.baseline_outputs
        )
        if self.candidate_output_sha256 != domain_sha256(
            PHASE6_MODEL_OUTPUT_SET_HASH_DOMAIN,
            candidate_values,
        ) or self.baseline_output_sha256 != domain_sha256(
            PHASE6_MODEL_OUTPUT_SET_HASH_DOMAIN,
            baseline_values,
        ):
            raise ValueError("baseline comparison output hashes must bind exact persisted values")
        expected_outcome = (
            BaselineOutcome.SURVIVES
            if self.candidate_metric > self.baseline_metric
            else BaselineOutcome.REJECTED
        )
        if self.outcome is not expected_outcome:
            raise ValueError("baseline outcome must derive from frozen comparison metrics")
        content = self.model_dump(
            mode="python",
            exclude={"comparison_id", "comparison_sha256"},
        )
        expected = domain_sha256(PHASE6_BASELINE_HASH_DOMAIN, content)
        if self.comparison_sha256 != expected or self.comparison_id != identity(
            PHASE6_COMPARISON_NAMESPACE,
            expected,
        ):
            raise ValueError("baseline comparison identity must derive from its preimage")
        return self


class ResearchAttempt(StrictModel):
    ordinal: int = Field(ge=1)
    attempt_sha256: SHA256
    phase5_trial_id: UUID | None
    phase5_trial_key: Identifier | None
    status: ResearchAttemptStatus
    configuration_sha256: SHA256
    failure_reason: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_attempt(self) -> Self:
        is_report_trial = self.status is not ResearchAttemptStatus.BLOCKED
        if is_report_trial != (
            self.phase5_trial_id is not None and self.phase5_trial_key is not None
        ):
            raise ValueError("report attempts require an exact Phase 5 trial ID and key")
        if (
            self.status
            in {
                ResearchAttemptStatus.FAILED,
                ResearchAttemptStatus.ABANDONED,
                ResearchAttemptStatus.NO_RETURN,
                ResearchAttemptStatus.BLOCKED,
            }
            and not self.failure_reason
        ):
            raise ValueError("incomplete attempts require a failure or abandonment reason")
        content = self.model_dump(mode="python", exclude={"attempt_sha256"})
        if self.attempt_sha256 != domain_sha256(PHASE6_ATTEMPT_HASH_DOMAIN, content):
            raise ValueError("attempt hash must match its complete preimage")
        return self


class UniverseSecurityEvidence(StrictModel):
    instrument_id: UUID
    listing_id: UUID
    sector_id: Identifier
    membership_known_at_decision: Literal[True] = True
    listing_status: Literal["active", "inactive", "delisted"]
    delisting_return_handled: bool
    source_references: tuple[ResearchSourceReference, ...] = Field(min_length=3)


class CapacityEvidence(StrictModel):
    turnover: Decimal = Field(ge=0)
    adv_participation: Decimal = Field(ge=0, le=1)
    capacity_units: Decimal = Field(gt=0)
    concentration: Decimal = Field(ge=0, le=1)
    capacity_limit_breached: bool


class FamilyAEvidence(StrictModel):
    family: Literal[CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING] = (
        CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING
    )
    universe: tuple[UniverseSecurityEvidence, ...] = Field(min_length=3)
    train_only_sector_fits: tuple[ResearchTransformFit, ...] = Field(min_length=1)
    cross_section_ranks: tuple[CrossSectionRankEvidence, ...] = Field(min_length=1)
    frozen_feature_names: tuple[
        Literal[
            "liquidity",
            "momentum",
            "quality",
            "turnover",
            "value",
            "volatility",
        ],
        ...,
    ] = Field(min_length=6, max_length=6)
    transparent_model_id: Literal["sector-relative-rank-linear-v1"] = (
        "sector-relative-rank-linear-v1"
    )
    nonlinear_model_id: Literal["frozen-depth-two-tree-v2"] = "frozen-depth-two-tree-v2"
    baseline_comparison_ids: tuple[UUID, ...] = Field(min_length=2)
    capacity: CapacityEvidence

    @model_validator(mode="after")
    def validate_a(self) -> Self:
        if tuple(self.frozen_feature_names) != tuple(sorted(self.frozen_feature_names)):
            raise ValueError("Family A feature set must remain frozen and sorted")
        statuses = {item.listing_status for item in self.universe}
        if "active" not in statuses or not statuses & {"inactive", "delisted"}:
            raise ValueError("Family A universe must include active and inactive/delisted evidence")
        if any(
            item.listing_status == "delisted" and not item.delisting_return_handled
            for item in self.universe
        ):
            raise ValueError("Family A delisting outcomes must be explicitly handled")
        if tuple(item.ordinal for item in self.cross_section_ranks) != tuple(
            range(1, len(self.cross_section_ranks) + 1)
        ):
            raise ValueError("Family A cross-section evidence ordinals must be contiguous")
        return self


class LifecycleEvidence(StrictModel):
    instrument_id: UUID
    listing_id: UUID
    inception_at_utc: datetime
    termination_at_utc: datetime | None
    known_at_decision: Literal[True] = True
    source_references: tuple[ResearchSourceReference, ...] = Field(min_length=1)

    @field_validator("inception_at_utc", "termination_at_utc")
    @classmethod
    def normalize_lifecycle_time(
        cls,
        value: datetime | None,
        info: object,
    ) -> datetime | None:
        if value is None:
            return None
        return _utc(value, getattr(info, "field_name", "lifecycle time"))


class LifecycleTestEvidence(StrictModel):
    instrument_id: UUID
    listing_id: UUID
    listing_status: Literal["active", "inactive", "delisted"]
    inception_at_utc: datetime
    termination_at_utc: datetime | None
    delisting_return_handled: bool | None
    used_as_feature: Literal[False] = False
    source_references: tuple[ResearchSourceReference, ...] = Field(min_length=2)
    evidence_sha256: SHA256

    @field_validator("inception_at_utc", "termination_at_utc")
    @classmethod
    def normalize_test_time(
        cls,
        value: datetime | None,
        info: object,
    ) -> datetime | None:
        if value is None:
            return None
        return _utc(value, getattr(info, "field_name", "lifecycle test time"))

    @model_validator(mode="after")
    def validate_lifecycle_test(self) -> Self:
        if (self.listing_status == "active") != (self.termination_at_utc is None):
            raise ValueError("only active lifecycle tests may omit a termination timestamp")
        if self.listing_status == "delisted":
            if self.delisting_return_handled is not True:
                raise ValueError("delisted lifecycle tests require explicit return handling")
        elif self.delisting_return_handled is not None:
            raise ValueError("non-delisted lifecycle tests cannot invent delisting handling")
        keys = tuple(
            (
                str(item.capability),
                str(item.snapshot_id),
                str(item.normalized_observation_id),
            )
            for item in self.source_references
        )
        if keys != tuple(sorted(keys)) or len(keys) != len(set(keys)):
            raise ValueError("lifecycle test sources must be unique and canonically sorted")
        content = self.model_dump(mode="python", exclude={"evidence_sha256"})
        if self.evidence_sha256 != domain_sha256(PHASE6_LIFECYCLE_TEST_HASH_DOMAIN, content):
            raise ValueError("lifecycle test hash must bind its complete preimage")
        return self


class RegimeResult(StrictModel):
    regime_id: Identifier
    observation_count: int = Field(ge=1)
    net_return: Decimal
    crash_window: bool


class FamilyBEvidence(StrictModel):
    family: Literal[CanonicalFamily.B_TIME_SERIES_MOMENTUM_REGIME] = (
        CanonicalFamily.B_TIME_SERIES_MOMENTUM_REGIME
    )
    lag_windows: tuple[Literal[1, 5, 20, 63, 126, 252], ...] = Field(
        min_length=6,
        max_length=6,
    )
    raw_nominal_bar_count: int = Field(ge=253)
    adjusted_return_observation_count: int = Field(ge=252)
    adjusted_return_formula_id: Literal["phase6-action-and-delisting-aware-return-v1"] = (
        "phase6-action-and-delisting-aware-return-v1"
    )
    nominal_feature_price_basis: Literal["raw_unadjusted"] = "raw_unadjusted"
    trend_strength_formula_id: Identifier
    realized_volatility_formula_id: Identifier
    drawdown_formula_id: Identifier
    lifecycle: LifecycleEvidence
    lifecycle_tests: tuple[LifecycleTestEvidence, ...] = Field(min_length=3)
    corporate_action_source_references: tuple[ResearchSourceReference, ...] = Field(min_length=1)
    regime_results: tuple[RegimeResult, ...] = Field(min_length=1)
    rate_evidence_available: Literal[False] = False
    rate_evidence_reason: Literal["rate_regime_source_unavailable"] = (
        "rate_regime_source_unavailable"
    )
    crisis_geometry_available: Literal[False] = False
    crisis_evidence_reason: Literal["crisis_window_geometry_unavailable"] = (
        "crisis_window_geometry_unavailable"
    )
    crash_evidence_complete: Literal[False] = False
    crash_concentration: None = None
    crash_concentration_limit: None = None
    no_image_candlestick_or_named_pattern_classifier: Literal[True] = True

    @model_validator(mode="after")
    def validate_b(self) -> Self:
        if self.lag_windows != (1, 5, 20, 63, 126, 252):
            raise ValueError("Family B lag windows are frozen")
        if any(
            not item.regime_id.startswith("volatility:") or item.crash_window
            for item in self.regime_results
        ):
            raise ValueError(
                "Family B may report only source-derived volatility regimes while rates and "
                "crisis geometry are unavailable"
            )
        if {item.listing_status for item in self.lifecycle_tests} != {
            "active",
            "inactive",
            "delisted",
        }:
            raise ValueError("Family B lifecycle tests must cover active, inactive, and delisted")
        return self


class StructuredTextFeatures(StrictModel):
    novelty: Decimal = Field(ge=-1, le=1)
    direction: Decimal = Field(ge=-1, le=1)
    uncertainty: Decimal = Field(ge=0, le=1)
    risk_change: Decimal = Field(ge=-1, le=1)
    event_tags: tuple[Identifier, ...] = Field(min_length=1)

    @field_validator("event_tags")
    @classmethod
    def validate_tags(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        _ordered_unique(value, "event_tags")
        return value


class TextFeatureExtraction(StrictModel):
    schema_version: Literal["phase6-text-feature-extraction-v1"] = (
        "phase6-text-feature-extraction-v1"
    )
    ordinal: int = Field(ge=1)
    extraction_id: UUID
    extraction_sha256: SHA256
    official_source_version_id: UUID
    official_document_id: Identifier
    document_content_sha256: SHA256
    available_at_utc: datetime
    corrected_at_utc: datetime | None
    correction_sequence: int = Field(ge=0)
    extractor_kind: Literal["deterministic_mock", "llm"]
    extractor_id: Identifier
    extractor_version: Identifier
    model_id: Identifier
    prompt_version: Identifier
    prompt_sha256: SHA256
    extraction_schema_version: Identifier
    entity_id: Identifier
    entity_resolution_method: Identifier
    features: StructuredTextFeatures
    output_boundary: Literal["structured_features_only"] = "structured_features_only"

    @field_validator("available_at_utc", "corrected_at_utc")
    @classmethod
    def normalize_text_times(
        cls,
        value: datetime | None,
        info: object,
    ) -> datetime | None:
        if value is None:
            return None
        return _utc(value, getattr(info, "field_name", "text time"))

    @model_validator(mode="after")
    def validate_extraction(self) -> Self:
        if (self.correction_sequence == 0) != (self.corrected_at_utc is None):
            raise ValueError("correction sequence and timestamp must agree")
        if self.corrected_at_utc is not None and self.corrected_at_utc > self.available_at_utc:
            raise ValueError("correction cannot be extracted before it is available")
        content = self.model_dump(
            mode="python",
            exclude={"extraction_id", "extraction_sha256"},
        )
        expected = domain_sha256(PHASE6_TEXT_EXTRACTION_HASH_DOMAIN, content)
        if self.extraction_sha256 != expected or self.extraction_id != identity(
            PHASE6_EXTRACTION_NAMESPACE,
            expected,
        ):
            raise ValueError("text extraction identity must derive from its complete preimage")
        return self


class SocialOfficialCorroboration(StrictModel):
    ordinal: int = Field(ge=1)
    corroboration_id: UUID
    corroboration_sha256: SHA256
    social_attention_record_id: Identifier
    official_source_version_id: UUID
    official_document_sha256: SHA256
    social_source_reference: ResearchSourceReference
    official_source_reference: ResearchSourceReference
    exact_match: Literal[True] = True
    contributes_standalone: Literal[False] = False

    @model_validator(mode="after")
    def validate_corroboration(self) -> Self:
        if self.social_source_reference.record_type != "social_attention":
            raise ValueError("social corroboration must bind an exact social-attention record")
        if self.official_source_reference.record_type != "official_document_content":
            raise ValueError("social corroboration must bind exact official document content")
        if (
            self.official_source_reference.normalized_content_sha256
            == self.social_source_reference.normalized_content_sha256
        ):
            raise ValueError("social and official evidence must remain separate observations")
        content = self.model_dump(
            mode="python",
            exclude={"corroboration_id", "corroboration_sha256"},
        )
        expected = domain_sha256(PHASE6_CORROBORATION_HASH_DOMAIN, content)
        if self.corroboration_sha256 != expected or self.corroboration_id != identity(
            PHASE6_CORROBORATION_NAMESPACE,
            expected,
        ):
            raise ValueError("corroboration identity must derive from its complete preimage")
        return self


class LaggedOhlcvBaselineEvidence(StrictModel):
    ordinal: int = Field(ge=1)
    sample_id: Identifier
    entity_id: Identifier
    decision_time_utc: datetime
    model_id: Literal["lagged-return-range-linear-baseline-v1"] = (
        "lagged-return-range-linear-baseline-v1"
    )
    formula_id: Literal["one-session-raw-return-minus-intraday-range-v1"] = (
        "one-session-raw-return-minus-intraday-range-v1"
    )
    lagged_return: Decimal
    intraday_range: Decimal = Field(ge=0)
    baseline_output: Decimal
    source_references: tuple[ResearchSourceReference, ...] = Field(
        min_length=2,
        max_length=2,
    )
    used_for_selection: Literal[False] = False
    evidence_sha256: SHA256

    @field_validator("decision_time_utc")
    @classmethod
    def normalize_decision_time(cls, value: datetime) -> datetime:
        return _utc(value, "decision_time_utc")

    @model_validator(mode="after")
    def validate_baseline(self) -> Self:
        if self.baseline_output != (self.lagged_return - self.intraday_range).quantize(
            Decimal("0.000000000001")
        ):
            raise ValueError("non-text baseline output must derive from its frozen OHLCV formula")
        if any(
            reference.capability is not DataCapability.OHLCV
            or reference.record_type != "ohlcv_bar"
            or reference.available_at_utc > self.decision_time_utc
            for reference in self.source_references
        ):
            raise ValueError("non-text baseline requires exact PIT OHLCV source lineage")
        instruments = {item.instrument_id for item in self.source_references}
        listings = {item.listing_id for item in self.source_references}
        if None in instruments or None in listings or len(instruments) != 1 or len(listings) != 1:
            raise ValueError("non-text baseline OHLCV sources must resolve to one exact entity")
        if tuple(item.available_at_utc for item in self.source_references) != tuple(
            sorted(item.available_at_utc for item in self.source_references)
        ):
            raise ValueError("non-text baseline OHLCV sources must be chronological")
        content = self.model_dump(mode="python", exclude={"evidence_sha256"})
        if self.evidence_sha256 != domain_sha256(
            PHASE6_LAGGED_OHLCV_BASELINE_HASH_DOMAIN,
            content,
        ):
            raise ValueError("non-text baseline hash must bind its complete preimage")
        return self


class FamilyCEvidence(StrictModel):
    family: Literal[CanonicalFamily.C_OFFICIAL_EVENT_TEXT_OVERLAY] = (
        CanonicalFamily.C_OFFICIAL_EVENT_TEXT_OVERLAY
    )
    extractions: tuple[TextFeatureExtraction, ...] = Field(min_length=2)
    corroborations: tuple[SocialOfficialCorroboration, ...] = Field(min_length=1)
    non_text_baseline: tuple[LaggedOhlcvBaselineEvidence, ...] = Field(min_length=1)
    baseline_comparison_ids: tuple[UUID, ...] = Field(min_length=1)
    conventional_downstream_model_id: Identifier
    non_text_baseline_model_id: Identifier
    prompt_model_drift_visible: Literal[True] = True
    corrections_are_later_observations: Literal[True] = True
    llm_is_extraction_only: Literal[True] = True

    @model_validator(mode="after")
    def validate_c(self) -> Self:
        official_ids = {item.official_source_version_id for item in self.extractions}
        if any(item.official_source_version_id not in official_ids for item in self.corroborations):
            raise ValueError("every social record must match an exact official extraction")
        correction_sequences = tuple(item.correction_sequence for item in self.extractions)
        if 0 not in correction_sequences or not any(value > 0 for value in correction_sequences):
            raise ValueError("Family C must preserve an original and a later correction")
        original_available_at = min(
            item.available_at_utc for item in self.extractions if item.correction_sequence == 0
        )
        if any(
            item.available_at_utc <= original_available_at
            for item in self.extractions
            if item.correction_sequence > 0
        ):
            raise ValueError("official corrections must remain strictly later observations")
        if tuple(item.ordinal for item in self.non_text_baseline) != tuple(
            range(1, len(self.non_text_baseline) + 1)
        ) or len({item.sample_id for item in self.non_text_baseline}) != len(
            self.non_text_baseline
        ):
            raise ValueError("Family C non-text baseline evidence must be complete and unique")
        if self.non_text_baseline_model_id != "lagged-return-range-linear-baseline-v1":
            raise ValueError("Family C non-text baseline model must be frozen")
        return self


class PreparedFamilyAInputs(StrictModel):
    family: Literal[CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING] = (
        CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING
    )
    universe: tuple[UniverseSecurityEvidence, ...] = Field(min_length=3)
    train_only_sector_fits: tuple[ResearchTransformFit, ...] = Field(min_length=6)
    cross_section_ranks: tuple[CrossSectionRankEvidence, ...] = Field(min_length=1)
    capacity: CapacityEvidence


class PreparedFamilyBInputs(StrictModel):
    family: Literal[CanonicalFamily.B_TIME_SERIES_MOMENTUM_REGIME] = (
        CanonicalFamily.B_TIME_SERIES_MOMENTUM_REGIME
    )
    lag_windows: tuple[Literal[1, 5, 20, 63, 126, 252], ...] = Field(
        min_length=6,
        max_length=6,
    )
    raw_nominal_bar_count: int = Field(ge=253)
    adjusted_return_observation_count: int = Field(ge=252)
    lifecycle: LifecycleEvidence
    lifecycle_tests: tuple[LifecycleTestEvidence, ...] = Field(min_length=3)
    corporate_action_source_references: tuple[ResearchSourceReference, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_lag_windows(self) -> Self:
        if self.lag_windows != (1, 5, 20, 63, 126, 252):
            raise ValueError("prepared Family B lag windows are frozen")
        if {item.listing_status for item in self.lifecycle_tests} != {
            "active",
            "inactive",
            "delisted",
        }:
            raise ValueError("prepared Family B lifecycle tests require all terminal states")
        return self


class PreparedFamilyCInputs(StrictModel):
    family: Literal[CanonicalFamily.C_OFFICIAL_EVENT_TEXT_OVERLAY] = (
        CanonicalFamily.C_OFFICIAL_EVENT_TEXT_OVERLAY
    )
    extractions: tuple[TextFeatureExtraction, ...] = Field(min_length=2)
    corroborations: tuple[SocialOfficialCorroboration, ...] = Field(min_length=1)
    non_text_baseline: tuple[LaggedOhlcvBaselineEvidence, ...] = Field(min_length=1)


PreparedFamilyInputs = Annotated[
    PreparedFamilyAInputs | PreparedFamilyBInputs | PreparedFamilyCInputs,
    Field(discriminator="family"),
]


def _phase5_trial_model_ids(family: CanonicalFamily) -> tuple[Identifier, ...]:
    if family is CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING:
        return (
            "sector-relative-rank-linear-v1",
            "zero-information-rank-v1",
            "frozen-depth-two-tree-v2",
            "negative-control-v1",
        )
    if family is CanonicalFamily.B_TIME_SERIES_MOMENTUM_REGIME:
        return (
            "lagged-trend-linear-v1",
            "lagged-return-only-v1",
            "zero-information-time-series-v1",
            "negative-control-v1",
        )
    return (
        "conventional-linear-text-overlay-v1",
        "non-text-event-baseline-v1",
        "event-tag-only-baseline-v1",
        "negative-control-v1",
    )


def _expected_research_model_outputs(
    *,
    family: CanonicalFamily,
    feature_rows: tuple[ResearchFeatureRow, ...],
    scores: tuple[ResearchScoreOutput, ...],
    family_context: object,
) -> tuple[tuple[tuple[Identifier, Decimal], ...], ...]:
    candidate = tuple(
        (item.sample_id, item.research_score)
        for item in sorted(scores, key=lambda item: item.ordinal)
    )
    if tuple(item.sample_id for item in feature_rows) != tuple(
        sample_id for sample_id, _value in candidate
    ):
        raise ValueError("research model outputs require one ordered score per feature row")
    zero = tuple((sample_id, Decimal("0")) for sample_id, _value in candidate)
    negative = tuple((sample_id, -value) for sample_id, value in candidate)
    if family is CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING:
        if not isinstance(family_context, (PreparedFamilyAInputs, FamilyAEvidence)):
            raise ValueError("Family A model outputs require cross-section evidence")
        nonlinear = tuple(
            (
                row.sample_id,
                next(
                    member.nonlinear_score
                    for member in section.eligible_members
                    if member.entity_id == section.selected_entity_id
                ),
            )
            for row, section in zip(
                feature_rows,
                family_context.cross_section_ranks,
                strict=True,
            )
        )
        return candidate, zero, nonlinear, negative
    if family is CanonicalFamily.B_TIME_SERIES_MOMENTUM_REGIME:
        baseline = tuple(
            (
                row.sample_id,
                next(
                    item.raw_value for item in row.features if item.feature_name == "lagged_return"
                ),
            )
            for row in feature_rows
        )
        return candidate, baseline, zero, negative
    if not isinstance(family_context, (PreparedFamilyCInputs, FamilyCEvidence)):
        raise ValueError("Family C model outputs require non-text baseline evidence")
    non_text_by_sample = {
        item.sample_id: item.baseline_output for item in family_context.non_text_baseline
    }
    non_text = tuple((row.sample_id, non_text_by_sample[row.sample_id]) for row in feature_rows)
    event_tag = tuple(
        (
            row.sample_id,
            next(item.raw_value for item in row.features if item.feature_name == "event_tag"),
        )
        for row in feature_rows
    )
    return candidate, non_text, event_tag, negative


def _validate_research_model_output_sets(
    *,
    family: CanonicalFamily,
    feature_rows: tuple[ResearchFeatureRow, ...],
    scores: tuple[ResearchScoreOutput, ...],
    model_output_sets: tuple[ResearchModelOutputSet, ...],
    family_context: object,
) -> None:
    if tuple(item.ordinal for item in model_output_sets) != (1, 2, 3, 4):
        raise ValueError("research model output registry requires exactly four ordered sets")
    expected_trial_keys = (
        "prepared-primary",
        "prepared-baseline",
        "prepared-nonlinear",
        "negative-reference",
    )
    if tuple(item.trial_key for item in model_output_sets) != expected_trial_keys or tuple(
        item.model_id for item in model_output_sets
    ) != _phase5_trial_model_ids(family):
        raise ValueError("research model output registry must use the frozen trial models")
    expected_variants = _expected_research_model_outputs(
        family=family,
        feature_rows=feature_rows,
        scores=scores,
        family_context=family_context,
    )
    for output_set, expected in zip(model_output_sets, expected_variants, strict=True):
        actual = tuple((item.sample_id, item.output_value) for item in output_set.outputs)
        if actual != expected:
            raise ValueError(
                "research model output registry must persist every exact label-independent cell"
            )
        for row, cell in zip(feature_rows, output_set.ledger_cells, strict=True):
            if (
                cell.sample_id != row.sample_id
                or cell.label_t0_utc != row.label_t0_utc
                or cell.label_t1_utc != row.label_t1_utc
                or cell.label_value != row.label_value
                or cell.label_source_references != row.label_source_references
            ):
                raise ValueError("research ledger cells must bind the exact prepared labels")


class PreparedResearchPipeline(StrictModel):
    schema_version: Literal["phase6-prepared-research-pipeline-v2"] = (
        "phase6-prepared-research-pipeline-v2"
    )
    configuration_id: ResearchConfigurationId
    family: CanonicalFamily
    specification: ResearchPipelineSpecification
    snapshot_bindings: tuple[ResearchSnapshotBinding, ...] = Field(min_length=1)
    calendar_source_references: tuple[ResearchSourceReference, ...] = ()
    regime_evidence: PreparedRegimeEvidence
    confirmation_interval: ResearchConfirmationInterval
    boundary_exclusions: tuple[ResearchBoundaryExclusion, ...] = Field(min_length=1)
    feature_rows: tuple[ResearchFeatureRow, ...] = Field(min_length=1)
    scores: tuple[ResearchScoreOutput, ...] = Field(min_length=1)
    model_output_sets: tuple[ResearchModelOutputSet, ...] = Field(min_length=4, max_length=4)
    baseline_comparisons: tuple[ResearchBaselineComparison, ...] = Field(min_length=1)
    family_inputs: PreparedFamilyInputs
    pipeline_input_sha256: SHA256

    @model_validator(mode="after")
    def validate_prepared_pipeline(self) -> Self:
        family_by_configuration = {
            ResearchConfigurationId.A_PASS: CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING,
            ResearchConfigurationId.A_FAIL: CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING,
            ResearchConfigurationId.B_PASS: CanonicalFamily.B_TIME_SERIES_MOMENTUM_REGIME,
            ResearchConfigurationId.B_FAIL: CanonicalFamily.B_TIME_SERIES_MOMENTUM_REGIME,
            ResearchConfigurationId.C_PASS: CanonicalFamily.C_OFFICIAL_EVENT_TEXT_OVERLAY,
            ResearchConfigurationId.C_FAIL: CanonicalFamily.C_OFFICIAL_EVENT_TEXT_OVERLAY,
        }
        if (
            family_by_configuration[self.configuration_id] is not self.family
            or self.specification.family is not self.family
            or self.family_inputs.family is not self.family
        ):
            raise ValueError("prepared configuration, specification, and family inputs must agree")
        if tuple(item.ordinal for item in self.snapshot_bindings) != tuple(
            range(1, len(self.snapshot_bindings) + 1)
        ):
            raise ValueError("prepared snapshot binding ordinals must be contiguous")
        if tuple(item.capability for item in self.snapshot_bindings) != (
            self.specification.required_capabilities
        ):
            raise ValueError("prepared snapshots must exactly match required capabilities")
        calendar_keys = tuple(
            (
                str(item.snapshot_id),
                str(item.normalized_observation_id),
            )
            for item in self.calendar_source_references
        )
        if (
            calendar_keys != tuple(sorted(calendar_keys))
            or len(calendar_keys) != len(set(calendar_keys))
            or any(
                item.capability is not DataCapability.TRADING_CALENDAR
                or item.record_type != "calendar_session"
                for item in self.calendar_source_references
            )
        ):
            raise ValueError("prepared calendar evidence must be exact, unique, and sorted")
        if (DataCapability.TRADING_CALENDAR in self.specification.required_capabilities) != bool(
            self.calendar_source_references
        ):
            raise ValueError("prepared calendar evidence must match the required capability set")
        macro_required = DataCapability.MACRO_REGIME_INPUTS in (
            self.specification.required_capabilities
        )
        if macro_required != (self.regime_evidence.evidence_state == "available"):
            raise ValueError("prepared regime evidence must match the required capability set")
        confirmation = self.confirmation_interval
        exclusion_ids = tuple(item.sample_id for item in self.boundary_exclusions)
        if exclusion_ids != tuple(sorted(exclusion_ids)) or len(exclusion_ids) != len(
            set(exclusion_ids)
        ):
            raise ValueError("confirmation boundary exclusions must be unique and sorted")
        if any(
            item.label_t0_utc > confirmation.interval_end_utc
            or item.label_t1_utc < confirmation.interval_start_utc
            for item in self.boundary_exclusions
        ):
            raise ValueError("every boundary exclusion must intersect the confirmation interval")
        if any(row.label_t1_utc >= confirmation.interval_start_utc for row in self.feature_rows):
            raise ValueError("prepared research labels cannot overlap the confirmation interval")
        forbidden_ids = {confirmation.sample_id, *exclusion_ids}
        if any(row.sample_id in forbidden_ids for row in self.feature_rows):
            raise ValueError("confirmation or boundary rows cannot enter prepared research rows")
        if tuple(item.ordinal for item in self.feature_rows) != tuple(
            range(1, len(self.feature_rows) + 1)
        ):
            raise ValueError("prepared feature row ordinals must be contiguous")
        row_ids = {item.row_id for item in self.feature_rows}
        if (
            len(self.scores) != len(row_ids)
            or {item.feature_row_id for item in self.scores} != row_ids
        ):
            raise ValueError("prepared scores must cover every feature row exactly once")
        _validate_research_model_output_sets(
            family=self.family,
            feature_rows=self.feature_rows,
            scores=self.scores,
            model_output_sets=self.model_output_sets,
            family_context=self.family_inputs,
        )
        if isinstance(self.family_inputs, PreparedFamilyAInputs):
            fit_ids = {item.fit_id for item in self.family_inputs.train_only_sector_fits}
            fits_by_key = {
                (item.sector_id, item.feature_name): item
                for item in self.family_inputs.train_only_sector_fits
            }
            if len(fits_by_key) != len(self.family_inputs.train_only_sector_fits):
                raise ValueError("Family A train fits must be unique by sector and feature")
            sectors = {item.sector_id for item in self.family_inputs.universe}
            expected_features = {
                "liquidity",
                "momentum",
                "quality",
                "turnover",
                "value",
                "volatility",
            }
            for sector_id in sectors:
                sector_fits = tuple(
                    item
                    for item in self.family_inputs.train_only_sector_fits
                    if item.sector_id == sector_id
                )
                sector_entities = {
                    item.listing_id
                    for item in self.family_inputs.universe
                    if item.sector_id == sector_id
                }
                if len(sector_entities) < 2:
                    raise ValueError(
                        "every Family A sector fit requires at least two distinct securities"
                    )
                if {item.feature_name for item in sector_fits} != expected_features:
                    raise ValueError("every Family A sector requires all six frozen train fits")
                if any(set(item.train_entity_ids) != sector_entities for item in sector_fits):
                    raise ValueError(
                        "every Family A sector fit must pool all distinct PIT universe securities"
                    )
            if any(
                value.train_fit_id is None or value.train_fit_id not in fit_ids
                for row in self.feature_rows
                for value in row.features
            ):
                raise ValueError("every Family A feature must bind its train-only sector fit")
            if len(self.family_inputs.cross_section_ranks) != len(self.feature_rows):
                raise ValueError("every Family A row requires one fixed-time cross-section")
            for row, section in zip(
                self.feature_rows,
                self.family_inputs.cross_section_ranks,
                strict=True,
            ):
                selected = next(
                    item
                    for item in section.eligible_members
                    if item.entity_id == section.selected_entity_id
                )
                if (
                    section.ordinal != row.ordinal
                    or section.decision_time_utc != row.decision_time_utc
                    or section.selected_entity_id != row.entity_id
                    or selected.features != row.features
                    or selected.label_value != row.label_value
                    or selected.label_t0_utc != row.label_t0_utc
                    or selected.label_t1_utc != row.label_t1_utc
                    or selected.label_source_references != row.label_source_references
                ):
                    raise ValueError(
                        "Family A selected row must match exact cross-section evidence"
                    )
                membership_universes = {
                    item.membership_universe_id for item in section.eligible_members
                }
                if len(membership_universes) != 1:
                    raise ValueError("Family A cross-section members must share one PIT universe")
                for member in section.eligible_members:
                    for value in member.features:
                        fit = fits_by_key.get((member.sector_id, value.feature_name))
                        if fit is None or value.train_fit_id != fit.fit_id:
                            raise ValueError(
                                "every Family A feature must bind its exact sector-feature fit"
                            )
                        if value.transformed_value != _standardized_value(
                            value.raw_value,
                            fit.mean,
                            fit.standard_deviation,
                        ):
                            raise ValueError(
                                "every Family A transformed value must derive from its train fit"
                            )
            linear = tuple(
                (
                    f"cross-section-{section.ordinal:02d}:{member.entity_id}",
                    member.linear_score,
                )
                for section in self.family_inputs.cross_section_ranks
                for member in section.eligible_members
            )
            nonlinear = tuple(
                (
                    f"cross-section-{section.ordinal:02d}:{member.entity_id}",
                    member.nonlinear_score,
                )
                for section in self.family_inputs.cross_section_ranks
                for member in section.eligible_members
            )
            control = tuple((sample_id, Decimal("0")) for sample_id, _value in linear)
            comparison_by_models = {
                (item.candidate_model_id, item.baseline_model_id): item
                for item in self.baseline_comparisons
            }
            expected_comparisons = (
                (
                    ("sector-relative-rank-linear-v1", "zero-information-rank-v1"),
                    linear,
                    control,
                ),
                (
                    ("frozen-depth-two-tree-v2", "sector-relative-rank-linear-v1"),
                    nonlinear,
                    linear,
                ),
            )
            for model_key, expected_candidate, expected_baseline in expected_comparisons:
                comparison = comparison_by_models.get(model_key)
                if (
                    comparison is None
                    or tuple(
                        (item.sample_id, item.output_value) for item in comparison.candidate_outputs
                    )
                    != expected_candidate
                    or tuple(
                        (item.sample_id, item.output_value) for item in comparison.baseline_outputs
                    )
                    != expected_baseline
                ):
                    raise ValueError(
                        "Family A comparisons must persist exact linear, nonlinear, "
                        "and control outputs"
                    )
        elif isinstance(self.family_inputs, PreparedFamilyBInputs):
            if any(
                value.train_fit_id is not None
                for row in self.feature_rows
                for value in row.features
            ):
                raise ValueError("Family B cannot disguise nominal/adjusted formulas as fits")
            candidate = tuple(
                (item.sample_id, item.research_score)
                for item in sorted(self.scores, key=lambda item: item.ordinal)
            )
            baseline = tuple(
                (
                    row.sample_id,
                    next(
                        item.raw_value
                        for item in row.features
                        if item.feature_name == "lagged_return"
                    ),
                )
                for row in self.feature_rows
            )
            comparison = self.baseline_comparisons[0]
            if (
                tuple((item.sample_id, item.output_value) for item in comparison.candidate_outputs)
                != candidate
                or tuple(
                    (item.sample_id, item.output_value) for item in comparison.baseline_outputs
                )
                != baseline
            ):
                raise ValueError(
                    "Family B comparison must persist exact candidate and baseline outputs"
                )
        elif isinstance(self.family_inputs, PreparedFamilyCInputs):
            if any(
                value.train_fit_id is not None
                or any(
                    reference.record_type != "official_document_content"
                    for reference in value.source_references
                )
                for row in self.feature_rows
                for value in row.features
            ):
                raise ValueError("Family C rows must remain extraction-only official text features")
            if tuple(
                (item.ordinal, item.sample_id, item.entity_id, item.decision_time_utc)
                for item in self.family_inputs.non_text_baseline
            ) != tuple(
                (item.ordinal, item.sample_id, item.entity_id, item.decision_time_utc)
                for item in self.feature_rows
            ):
                raise ValueError("Family C non-text baseline must cover every prepared row exactly")
            baseline_comparison = next(
                (
                    item
                    for item in self.baseline_comparisons
                    if item.baseline_model_id == "lagged-return-range-linear-baseline-v1"
                ),
                None,
            )
            expected_output_sha256 = domain_sha256(
                PHASE6_MODEL_OUTPUT_SET_HASH_DOMAIN,
                tuple(
                    (item.sample_id, item.baseline_output)
                    for item in self.family_inputs.non_text_baseline
                ),
            )
            if (
                baseline_comparison is None
                or baseline_comparison.used_for_selection is not False
                or baseline_comparison.baseline_output_sha256 != expected_output_sha256
                or tuple(
                    (item.sample_id, item.output_value)
                    for item in baseline_comparison.candidate_outputs
                )
                != tuple(
                    (item.sample_id, item.research_score)
                    for item in sorted(self.scores, key=lambda item: item.ordinal)
                )
                or tuple(
                    (item.sample_id, item.output_value)
                    for item in baseline_comparison.baseline_outputs
                )
                != tuple(
                    (item.sample_id, item.baseline_output)
                    for item in self.family_inputs.non_text_baseline
                )
            ):
                raise ValueError("Family C comparison must bind the descriptive non-text baseline")
        content = self.model_dump(mode="python", exclude={"pipeline_input_sha256"})
        if self.pipeline_input_sha256 != domain_sha256(
            PHASE6_PIPELINE_INPUT_HASH_DOMAIN,
            content,
        ):
            raise ValueError("pipeline input hash must bind all pre-evaluation inputs")
        return self


FamilyEvidence = Annotated[
    FamilyAEvidence | FamilyBEvidence | FamilyCEvidence,
    Field(discriminator="family"),
]


class Phase5EvaluationLink(StrictModel):
    policy_id: UUID
    policy_version: int = Field(ge=1)
    policy_sha256: SHA256
    fixture_id: Identifier
    fixture_sha256: SHA256
    config_hash: SHA256
    snapshot_bundle_sha256: SHA256
    evaluation_report_id: UUID | None
    evaluation_report_sha256: SHA256 | None
    evaluation_outcome_id: UUID | None
    promotion_state: PromotionState
    gate_codes: tuple[GateCode, ...]
    raw_trial_count: int = Field(ge=0)
    effective_trial_count: Decimal = Field(ge=0)
    phase5_trial_set_sha256: SHA256 | None

    @model_validator(mode="after")
    def validate_link(self) -> Self:
        if (self.evaluation_report_id is None) == (self.evaluation_outcome_id is None):
            raise ValueError("exactly one Phase 5 report or blocked outcome must be linked")
        if self.evaluation_report_id is None:
            if (
                self.evaluation_report_sha256 is not None
                or self.phase5_trial_set_sha256 is not None
                or self.gate_codes
            ):
                raise ValueError("blocked pre-report outcomes cannot invent report evidence")
        else:
            if self.evaluation_report_sha256 is None or self.phase5_trial_set_sha256 is None:
                raise ValueError("evaluation reports require their exact artifact hash")
            if self.gate_codes != tuple(GateCode):
                raise ValueError("Phase 6 report links must preserve all Phase 5 gates in order")
        return self


class ResearchRunArtifact(StrictModel):
    run_id: UUID
    artifact_schema_version: Literal["phase6-research-artifact-v2"] = "phase6-research-artifact-v2"
    artifact_sha256: SHA256
    request_fingerprint_sha256: SHA256
    pipeline_input_sha256: SHA256
    configuration_id: ResearchConfigurationId
    configuration_sha256: SHA256
    mapping_id: UUID
    mapping_version: int = Field(ge=1)
    mapping_input_sha256: SHA256
    family: CanonicalFamily
    specification: ResearchPipelineSpecification
    snapshot_bindings: tuple[ResearchSnapshotBinding, ...] = Field(min_length=1)
    calendar_source_references: tuple[ResearchSourceReference, ...] = ()
    regime_evidence: PreparedRegimeEvidence
    confirmation_interval: ResearchConfirmationInterval
    boundary_exclusions: tuple[ResearchBoundaryExclusion, ...] = Field(min_length=1)
    source_reproduction_audit: PreparedPipelineReproductionAudit
    snapshot_bundle_sha256: SHA256
    feature_rows: tuple[ResearchFeatureRow, ...] = Field(min_length=1)
    feature_lineage_sha256: SHA256
    scores: tuple[ResearchScoreOutput, ...] = Field(min_length=1)
    model_output_sets: tuple[ResearchModelOutputSet, ...] = Field(min_length=4, max_length=4)
    trial_economics: tuple[ResearchTrialEconomics, ...] = Field(min_length=4, max_length=4)
    attempts: tuple[ResearchAttempt, ...] = Field(min_length=1)
    baseline_comparisons: tuple[ResearchBaselineComparison, ...] = Field(min_length=1)
    family_evidence: FamilyEvidence
    phase5_evaluation: Phase5EvaluationLink
    code_version_git_sha: GitSHA
    random_seed: int = Field(ge=0)
    created_at_utc: datetime
    status: ResearchRunStatus
    reason_codes: tuple[Identifier, ...]
    warnings: tuple[str, ...]
    synthetic: Literal[True] = True
    no_real_performance_claimed: Literal[True] = True
    pass_research_is_not_paper_approval: Literal[True] = True
    paper_approval_granted: Literal[False] = False
    disclaimer: Literal["Synthetic research only; no real performance or investment advice."] = (
        "Synthetic research only; no real performance or investment advice."
    )

    @field_validator("created_at_utc")
    @classmethod
    def normalize_created_at(cls, value: datetime) -> datetime:
        return _utc(value, "created_at_utc")

    @model_validator(mode="after")
    def validate_artifact(self) -> Self:
        if self.family != self.specification.family or self.family != self.family_evidence.family:
            raise ValueError("mapping, specification, and family evidence must agree")
        if self.configuration_sha256 != self.phase5_evaluation.config_hash:
            raise ValueError("research configuration must bind the exact Phase 5 config hash")
        binding_ordinals = tuple(item.ordinal for item in self.snapshot_bindings)
        if binding_ordinals != tuple(range(1, len(binding_ordinals) + 1)):
            raise ValueError("snapshot binding ordinals must be contiguous")
        if tuple(item.capability for item in self.snapshot_bindings) != (
            self.specification.required_capabilities
        ):
            raise ValueError("snapshot capabilities must exactly match the frozen specification")
        audit_bindings = {
            (item.snapshot_id, item.snapshot_sha256, item.binding_sha256)
            for item in self.source_reproduction_audit.snapshot_bindings
        }
        artifact_bindings = {
            (item.snapshot_id, item.snapshot_sha256, item.binding_sha256)
            for item in self.snapshot_bindings
        }
        if (
            self.source_reproduction_audit.configuration_id is not self.configuration_id
            or audit_bindings != artifact_bindings
            or self.source_reproduction_audit.supplied_pipeline_input_sha256
            != self.pipeline_input_sha256
        ):
            raise ValueError("source reproduction audit must bind this exact artifact input")
        calendar_keys = tuple(
            (str(item.snapshot_id), str(item.normalized_observation_id))
            for item in self.calendar_source_references
        )
        if (
            calendar_keys != tuple(sorted(calendar_keys))
            or len(calendar_keys) != len(set(calendar_keys))
            or any(
                item.capability is not DataCapability.TRADING_CALENDAR
                or item.record_type != "calendar_session"
                for item in self.calendar_source_references
            )
        ):
            raise ValueError("artifact calendar evidence must be exact, unique, and sorted")
        if (DataCapability.TRADING_CALENDAR in self.specification.required_capabilities) != bool(
            self.calendar_source_references
        ):
            raise ValueError("artifact calendar evidence must match the required capability set")
        if (DataCapability.MACRO_REGIME_INPUTS in self.specification.required_capabilities) != (
            self.regime_evidence.evidence_state == "available"
        ):
            raise ValueError("artifact regime evidence must match required capabilities")
        if any(
            row.label_t1_utc >= self.confirmation_interval.interval_start_utc
            for row in self.feature_rows
        ):
            raise ValueError("artifact research labels cannot overlap final confirmation")
        forbidden_ids = {
            self.confirmation_interval.sample_id,
            *(item.sample_id for item in self.boundary_exclusions),
        }
        if any(row.sample_id in forbidden_ids for row in self.feature_rows):
            raise ValueError("artifact cannot persist confirmation rows as research evidence")
        if self.snapshot_bundle_sha256 != self.phase5_evaluation.snapshot_bundle_sha256:
            raise ValueError("snapshot bundle must be the exact Phase 5 engine input hash")
        if tuple(item.ordinal for item in self.feature_rows) != tuple(
            range(1, len(self.feature_rows) + 1)
        ):
            raise ValueError("feature row ordinals must be contiguous")
        expected_lineage = domain_sha256(
            PHASE6_FEATURE_LINEAGE_HASH_DOMAIN,
            tuple(
                (item.row_id, item.row_sha256, item.source_lineage_sha256)
                for item in self.feature_rows
            ),
        )
        if self.feature_lineage_sha256 != expected_lineage:
            raise ValueError("feature lineage hash must bind every feature row")
        feature_ids = {item.row_id for item in self.feature_rows}
        if (
            len(self.scores) != len(feature_ids)
            or {item.feature_row_id for item in self.scores} != feature_ids
        ):
            raise ValueError("every feature row must have exactly one explainable score")
        if tuple(item.ordinal for item in self.trial_economics) != (1, 2, 3, 4):
            raise ValueError("artifact trial economics requires four ordered completed trials")
        economics_by_key = {item.trial_key: item for item in self.trial_economics}
        if len(economics_by_key) != 4:
            raise ValueError("artifact trial economics keys must be unique")
        for output_set in self.model_output_sets:
            economics = economics_by_key.get(output_set.trial_key)
            cells = {item.sample_id: item for item in output_set.ledger_cells}
            if (
                economics is None
                or economics.model_id != output_set.model_id
                or economics.output_set_sha256 != output_set.output_set_sha256
                or tuple(item.sample_id for item in economics.sample_economics)
                != tuple(sorted(cells))
            ):
                raise ValueError("trial economics must bind its exact model-output set")
            for item in economics.sample_economics:
                cell = cells[item.sample_id]
                if (
                    item.model_output != cell.model_output
                    or item.synthetic_research_weight != cell.synthetic_research_weight
                    or item.return_status is not cell.return_status
                    or item.synthetic_gross_return != cell.synthetic_gross_return
                ):
                    raise ValueError("trial economics must reconcile every research ledger cell")
        _validate_research_model_output_sets(
            family=self.family,
            feature_rows=self.feature_rows,
            scores=self.scores,
            model_output_sets=self.model_output_sets,
            family_context=self.family_evidence,
        )
        for values, field_name in (
            (self.scores, "scores"),
            (self.attempts, "attempts"),
            (self.baseline_comparisons, "baseline_comparisons"),
        ):
            ordinals = tuple(item.ordinal for item in values)
            if ordinals != tuple(range(1, len(ordinals) + 1)):
                raise ValueError(f"{field_name} ordinals must be contiguous")
        if self.phase5_evaluation.evaluation_report_id is not None:
            if len(self.attempts) != self.phase5_evaluation.raw_trial_count:
                raise ValueError("attempt count must equal the Phase 5 raw trial count")
            trial_ids = tuple(item.phase5_trial_id for item in self.attempts)
            trial_keys = tuple(item.phase5_trial_key for item in self.attempts)
            if (
                None in trial_ids
                or None in trial_keys
                or len(set(trial_ids)) != len(trial_ids)
                or len(set(trial_keys)) != len(trial_keys)
            ):
                raise ValueError("attempts must preserve unique exact Phase 5 trial IDs and keys")
            trial_set = tuple(
                sorted(
                    (
                        (
                            item.phase5_trial_id,
                            item.phase5_trial_key,
                            TrialStatus(item.status.value),
                            item.configuration_sha256,
                        )
                        for item in self.attempts
                    ),
                    key=lambda item: (str(item[0]), str(item[1])),
                )
            )
            if self.phase5_evaluation.phase5_trial_set_sha256 != domain_sha256(
                PHASE6_TRIAL_SET_HASH_DOMAIN,
                trial_set,
            ):
                raise ValueError("attempt set hash must bind every exact Phase 5 trial")
        expected_status = (
            ResearchRunStatus.BLOCKED
            if self.phase5_evaluation.evaluation_outcome_id is not None
            else ResearchRunStatus.COMPLETED
        )
        if self.status is not expected_status:
            raise ValueError("run status must derive from the Phase 5 artifact kind")
        comparison_ids = {item.comparison_id for item in self.baseline_comparisons}
        if isinstance(self.family_evidence, (FamilyAEvidence, FamilyCEvidence)) and not set(
            self.family_evidence.baseline_comparison_ids
        ).issubset(comparison_ids):
            raise ValueError("family evidence must reference persisted baseline comparisons")
        if (
            isinstance(self.family_evidence, FamilyBEvidence)
            and (
                not self.family_evidence.crash_evidence_complete
                or (
                    self.family_evidence.crash_concentration is not None
                    and self.family_evidence.crash_concentration
                    > self.family_evidence.crash_concentration_limit
                )
            )
            and self.phase5_evaluation.promotion_state is PromotionState.PASS_RESEARCH
        ):
            raise ValueError("crash-concentrated Family B evidence cannot pass research")
        if isinstance(self.family_evidence, FamilyAEvidence):
            if len(self.family_evidence.cross_section_ranks) != len(self.feature_rows):
                raise ValueError("Family A artifact must persist every fixed-time cross-section")
            fits_by_key = {
                (item.sector_id, item.feature_name): item
                for item in self.family_evidence.train_only_sector_fits
            }
            if len(fits_by_key) != len(self.family_evidence.train_only_sector_fits):
                raise ValueError("Family A artifact train fits must be unique")
            for row, section in zip(
                self.feature_rows,
                self.family_evidence.cross_section_ranks,
                strict=True,
            ):
                if (
                    section.ordinal != row.ordinal
                    or section.decision_time_utc != row.decision_time_utc
                    or section.selected_entity_id != row.entity_id
                ):
                    raise ValueError("Family A artifact cross-section lineage is incomplete")
                for member in section.eligible_members:
                    for value in member.features:
                        fit = fits_by_key.get((member.sector_id, value.feature_name))
                        if (
                            fit is None
                            or value.train_fit_id != fit.fit_id
                            or value.transformed_value
                            != _standardized_value(
                                value.raw_value,
                                fit.mean,
                                fit.standard_deviation,
                            )
                        ):
                            raise ValueError(
                                "Family A artifact features must derive from exact train fits"
                            )
            linear = tuple(
                (
                    f"cross-section-{section.ordinal:02d}:{member.entity_id}",
                    member.linear_score,
                )
                for section in self.family_evidence.cross_section_ranks
                for member in section.eligible_members
            )
            nonlinear = tuple(
                (
                    f"cross-section-{section.ordinal:02d}:{member.entity_id}",
                    member.nonlinear_score,
                )
                for section in self.family_evidence.cross_section_ranks
                for member in section.eligible_members
            )
            control = tuple((sample_id, Decimal("0")) for sample_id, _value in linear)
            comparisons = {
                (item.candidate_model_id, item.baseline_model_id): item
                for item in self.baseline_comparisons
            }
            for model_key, expected_candidate, expected_baseline in (
                (
                    ("sector-relative-rank-linear-v1", "zero-information-rank-v1"),
                    linear,
                    control,
                ),
                (
                    ("frozen-depth-two-tree-v2", "sector-relative-rank-linear-v1"),
                    nonlinear,
                    linear,
                ),
            ):
                comparison = comparisons.get(model_key)
                if (
                    comparison is None
                    or tuple(
                        (item.sample_id, item.output_value) for item in comparison.candidate_outputs
                    )
                    != expected_candidate
                    or tuple(
                        (item.sample_id, item.output_value) for item in comparison.baseline_outputs
                    )
                    != expected_baseline
                ):
                    raise ValueError("Family A artifact model outputs are incomplete")
        elif isinstance(self.family_evidence, FamilyBEvidence):
            candidate = tuple(
                (item.sample_id, item.research_score)
                for item in sorted(self.scores, key=lambda item: item.ordinal)
            )
            baseline = tuple(
                (
                    row.sample_id,
                    next(
                        item.raw_value
                        for item in row.features
                        if item.feature_name == "lagged_return"
                    ),
                )
                for row in self.feature_rows
            )
            comparison = self.baseline_comparisons[0]
            if (
                tuple((item.sample_id, item.output_value) for item in comparison.candidate_outputs)
                != candidate
                or tuple(
                    (item.sample_id, item.output_value) for item in comparison.baseline_outputs
                )
                != baseline
            ):
                raise ValueError("Family B artifact model outputs are incomplete")
        elif isinstance(self.family_evidence, FamilyCEvidence):
            baseline_comparison = next(
                (
                    item
                    for item in self.baseline_comparisons
                    if item.baseline_model_id == self.family_evidence.non_text_baseline_model_id
                ),
                None,
            )
            expected_output_sha256 = domain_sha256(
                PHASE6_MODEL_OUTPUT_SET_HASH_DOMAIN,
                tuple(
                    (item.sample_id, item.baseline_output)
                    for item in self.family_evidence.non_text_baseline
                ),
            )
            if (
                baseline_comparison is None
                or baseline_comparison.used_for_selection is not False
                or baseline_comparison.baseline_output_sha256 != expected_output_sha256
                or tuple(
                    (item.sample_id, item.output_value)
                    for item in baseline_comparison.candidate_outputs
                )
                != tuple(
                    (item.sample_id, item.research_score)
                    for item in sorted(self.scores, key=lambda item: item.ordinal)
                )
                or tuple(
                    (item.sample_id, item.output_value)
                    for item in baseline_comparison.baseline_outputs
                )
                != tuple(
                    (item.sample_id, item.baseline_output)
                    for item in self.family_evidence.non_text_baseline
                )
            ):
                raise ValueError("Family C artifact must preserve its descriptive OHLCV baseline")
        request_payload = {
            "mapping_id": self.mapping_id,
            "mapping_version": self.mapping_version,
            "mapping_input_sha256": self.mapping_input_sha256,
            "snapshot_bundle_sha256": self.snapshot_bundle_sha256,
            "configuration_id": self.configuration_id,
            "configuration_sha256": self.configuration_sha256,
            "specification_sha256": self.specification.specification_sha256,
            "code_version_git_sha": self.code_version_git_sha,
            "random_seed": self.random_seed,
            "pipeline_input_sha256": self.pipeline_input_sha256,
        }
        expected_request = domain_sha256(PHASE6_REQUEST_HASH_DOMAIN, request_payload)
        if self.request_fingerprint_sha256 != expected_request or self.run_id != identity(
            PHASE6_RUN_NAMESPACE,
            expected_request,
        ):
            raise ValueError("run identity must derive from server-resolved immutable inputs")
        artifact_payload = self.model_dump(
            mode="python",
            exclude={"run_id", "artifact_sha256", "created_at_utc"},
        )
        if self.artifact_sha256 != domain_sha256(
            PHASE6_ARTIFACT_HASH_DOMAIN,
            artifact_payload,
        ):
            raise ValueError("research artifact hash must match its complete preimage")
        return self


class ResearchRunSummary(StrictModel):
    run_id: UUID
    artifact_sha256: SHA256
    configuration_id: ResearchConfigurationId
    family: CanonicalFamily
    promotion_state: PromotionState
    status: ResearchRunStatus
    synthetic: Literal[True] = True
    no_real_performance_claimed: Literal[True] = True
    pass_research_is_not_paper_approval: Literal[True] = True
    created_at_utc: datetime
    reason_codes: tuple[Identifier, ...]

    @field_validator("created_at_utc")
    @classmethod
    def normalize_summary_time(cls, value: datetime) -> datetime:
        return _utc(value, "created_at_utc")


__all__ = [name for name in globals() if not name.startswith("_")]
