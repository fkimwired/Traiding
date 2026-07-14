"""Strict public and persistence contracts for Phase 6 research-only pipelines."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Literal, Self
from uuid import UUID

from fable5_backtester.contracts import GateCode, PromotionState, TrialStatus
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
    PHASE6_COMPARISON_NAMESPACE,
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
    PHASE6_REQUEST_HASH_DOMAIN,
    PHASE6_RUN_NAMESPACE,
    PHASE6_SCORE_HASH_DOMAIN,
    PHASE6_SCORE_NAMESPACE,
    PHASE6_SNAPSHOT_BINDING_HASH_DOMAIN,
    PHASE6_SPECIFICATION_HASH_DOMAIN,
    PHASE6_TEXT_EXTRACTION_HASH_DOMAIN,
    PHASE6_TRANSFORM_FIT_HASH_DOMAIN,
    PHASE6_TRIAL_SET_HASH_DOMAIN,
    domain_sha256,
    identity,
)

SHA256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
Identifier = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")]
GitSHA = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]

PHASE6_ARTIFACT_SCHEMA_VERSION = "phase6-research-artifact-v1"
PHASE6_SPECIFICATION_SCHEMA_VERSION = "phase6-research-specification-v1"
PHASE6_FEATURE_ROW_SCHEMA_VERSION = "phase6-research-feature-row-v1"
PHASE6_SCORE_SCHEMA_VERSION = "phase6-research-score-output-v1"
PHASE6_TEXT_EXTRACTION_SCHEMA_VERSION = "phase6-text-feature-extraction-v1"
PHASE6_RESEARCH_FIXTURE_VERSION = "phase6-deterministic-research-fixtures-v1"


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


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ResearchConfigurationId(StrEnum):
    A_PASS = "phase6-a-pass-v1"
    A_FAIL = "phase6-a-fail-cost-v1"
    B_PASS = "phase6-b-pass-v1"
    B_FAIL = "phase6-b-fail-crash-v1"
    C_PASS = "phase6-c-pass-v1"
    C_FAIL = "phase6-c-fail-corroboration-v1"


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
    snapshot_ids: tuple[UUID, ...] = Field(min_length=1)
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
    schema_version: Literal["phase6-research-specification-v1"] = "phase6-research-specification-v1"
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


class ResearchTransformFit(StrictModel):
    fit_id: UUID
    fold_id: UUID
    transform_id: Identifier
    feature_name: Identifier
    sector_id: Identifier | None
    train_sample_ids: tuple[Identifier, ...] = Field(min_length=2)
    train_entity_ids: tuple[UUID, ...] = Field(min_length=2)
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
        if set(self.train_sample_ids) & set(self.prohibited_sample_ids):
            raise ValueError("transform fit cannot contain test, purged, or confirmation ids")
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
        return Decimal("-0.35") if values["quality"] >= 0 else Decimal("-0.15")
    return Decimal("0.35") if values["volatility"] >= 0 else Decimal("0.15")


class CrossSectionRankMember(StrictModel):
    entity_id: Identifier
    instrument_id: UUID
    listing_id: UUID
    sector_id: Identifier
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
        content = self.model_dump(mode="python", exclude={"evidence_sha256"})
        if self.evidence_sha256 != domain_sha256(PHASE6_CROSS_SECTION_RANK_HASH_DOMAIN, content):
            raise ValueError("cross-section rank hash must bind its complete preimage")
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
    candidate_output_sha256: SHA256
    baseline_output_sha256: SHA256
    label_sha256: SHA256
    outcome: BaselineOutcome
    reason_codes: tuple[Identifier, ...]

    @model_validator(mode="after")
    def validate_comparison(self) -> Self:
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
    nonlinear_model_id: Literal["frozen-depth-two-tree-v1"] = "frozen-depth-two-tree-v1"
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
    regime_results: tuple[RegimeResult, ...] = Field(min_length=3)
    crash_evidence_complete: bool
    crash_concentration: Decimal | None = Field(default=None, ge=0, le=1)
    crash_concentration_limit: Decimal = Field(gt=0, le=1)
    no_image_candlestick_or_named_pattern_classifier: Literal[True] = True

    @model_validator(mode="after")
    def validate_b(self) -> Self:
        if self.lag_windows != (1, 5, 20, 63, 126, 252):
            raise ValueError("Family B lag windows are frozen")
        if self.crash_evidence_complete and not any(
            item.crash_window for item in self.regime_results
        ):
            raise ValueError("Family B must report a predeclared crash window")
        if self.crash_evidence_complete != (self.crash_concentration is not None):
            raise ValueError("Family B crash concentration requires complete crash evidence")
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


class PreparedResearchPipeline(StrictModel):
    schema_version: Literal["phase6-prepared-research-pipeline-v1"] = (
        "phase6-prepared-research-pipeline-v1"
    )
    configuration_id: ResearchConfigurationId
    family: CanonicalFamily
    specification: ResearchPipelineSpecification
    snapshot_bindings: tuple[ResearchSnapshotBinding, ...] = Field(min_length=1)
    feature_rows: tuple[ResearchFeatureRow, ...] = Field(min_length=1)
    scores: tuple[ResearchScoreOutput, ...] = Field(min_length=1)
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
        if isinstance(self.family_inputs, PreparedFamilyAInputs):
            fit_ids = {item.fit_id for item in self.family_inputs.train_only_sector_fits}
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
        elif isinstance(self.family_inputs, PreparedFamilyBInputs):
            if any(
                value.train_fit_id is not None
                for row in self.feature_rows
                for value in row.features
            ):
                raise ValueError("Family B cannot disguise nominal/adjusted formulas as fits")
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
    artifact_schema_version: Literal["phase6-research-artifact-v1"] = "phase6-research-artifact-v1"
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
    snapshot_bundle_sha256: SHA256
    feature_rows: tuple[ResearchFeatureRow, ...] = Field(min_length=1)
    feature_lineage_sha256: SHA256
    scores: tuple[ResearchScoreOutput, ...] = Field(min_length=1)
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
