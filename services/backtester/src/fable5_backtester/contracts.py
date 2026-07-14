"""Immutable Phase 5 policy, ledger, gate, and report contracts.

These contracts describe evaluation of deterministic synthetic research evidence.  They do
not define a strategy, action, allocation instruction, approval, or execution capability.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal, localcontext
from enum import StrEnum
from typing import Annotated, Literal, Protocol, Self
from uuid import UUID

from fable5_data.contracts import (
    ConstituentDisposition,
    DataCapability,
    NormalizedObservation,
    NormalizedObservationDraft,
    UniverseMembershipPayload,
)
from fable5_mapping.models import CanonicalFamily
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from fable5_backtester.canonical import (
    PHASE5_ARTIFACT_HASH_DOMAIN,
    PHASE5_ARTIFACT_NAMESPACE,
    PHASE5_DEPENDENCY_GRAPH_HASH_DOMAIN,
    PHASE5_FIT_HASH_DOMAIN,
    PHASE5_FIT_NAMESPACE,
    PHASE5_GATE_HASH_DOMAIN,
    PHASE5_GATE_NAMESPACE,
    PHASE5_LEAKAGE_EVIDENCE_HASH_DOMAIN,
    PHASE5_SAMPLE_LINEAGE_HASH_DOMAIN,
    PHASE5_TRAIN_IDS_HASH_DOMAIN,
    PHASE5_TRAIN_ONLY_FIT_HASH_DOMAIN,
    canonical_json_text,
    domain_sha256,
    identity,
)

PHASE5_POLICY_SCHEMA_VERSION = "phase5-evaluation-policy-v1"
PHASE5_FEATURE_SCHEMA_VERSION = "phase5-feature-specification-v1"
PHASE5_LABEL_SCHEMA_VERSION = "phase5-label-specification-v1"
PHASE5_ARTIFACT_SCHEMA_VERSION = "phase5-evaluation-report-v1"
PHASE5_REQUEST_FINGERPRINT_VERSION = "phase5-evaluation-request-v1"
PHASE5_SYNTHETIC_FIXTURE_VERSION = "phase5-synthetic-evaluation-fixtures-v1"
PHASE5_DSR_FORMULA_VERSION = "bailey-lopez-de-prado-dsr-2014-eq2-v1"
PHASE5_PBO_FORMULA_VERSION = "bailey-et-al-cscv-2014-algorithm-2.3-v1"
PHASE5_EFFECTIVE_TRIAL_METHOD = "bailey-average-correlation-interpolation-v1"
PHASE5_PREPROCESSING_VERSION = "phase5-train-only-standardizer-v1"
PHASE5_COST_MODEL_VERSION = "phase5-component-cost-model-v1"
PHASE5_SOURCE_OBSERVATION_BINDING_RULE = "phase5-exact-snapshot-constituent-value-v1"
PHASE5_SOURCE_FEATURE_DERIVATION_SCHEMA_VERSION = "phase5-source-feature-derivation-v1"
PHASE5_SOURCE_FEATURE_DERIVATION_HASH_DOMAIN = "phase5-source-feature-derivation-v1"
PHASE5_SOURCE_FEATURE_DERIVATION_FORMULA = "source-decimal-times-frozen-multiplier-v1"
PHASE5_ADVERSARIAL_DEPENDENCY_REVIEW_VERSION = "phase5-adversarial-dependency-review-v1"
PHASE5_ADVERSARIAL_DEPENDENCY_REVIEW_HASH_DOMAIN = "phase5-adversarial-dependency-review-v1"
PHASE5_DECIMAL_QUANTUM = Decimal("1e-24")
PHASE5_REPORT_HASH_EXCLUDED_FIELDS = frozenset(
    {
        "artifact_id",
        "artifact_type",
        "artifact_schema_version",
        "artifact_sha256",
        "request_fingerprint_version",
        "effective_trial_method",
        "created_at_utc",
        "decision_time_utc",
        "fixture_version",
        "synthetic",
        "no_real_performance_claimed",
        "disclaimer",
        "pass_research_is_not_paper_approval",
    }
)
PHASE5_SYNTHETIC_LEDGER_VALUE_RULE: Literal["deterministic-synthetic-research-ledger-input-v1"] = (
    "deterministic-synthetic-research-ledger-input-v1"
)

SHA256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
GitSHA = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]
Identifier = Annotated[
    str,
    StringConstraints(min_length=1, max_length=256, pattern=r"^[A-Za-z0-9_.:-]+$"),
]


def _utc(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value.astimezone(UTC)


def _gate_decimal(value: str | int | Decimal | bool | None, field_name: str) -> Decimal:
    """Decode a Decimal gate value after canonical JSON has represented it as text."""

    if value is None or isinstance(value, bool):
        raise ValueError(f"{field_name} must be a decimal value")
    try:
        decoded = Decimal(value)
    except Exception as exc:
        raise ValueError(f"{field_name} must be a decimal value") from exc
    if not decoded.is_finite():
        raise ValueError(f"{field_name} must be finite")
    return decoded


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")


class PromotionState(StrEnum):
    PASS_RESEARCH = "PASS_RESEARCH"
    FAIL_REJECT = "FAIL_REJECT"
    BLOCKED_MISSING_POLICY = "BLOCKED_MISSING_POLICY"
    BLOCKED_UNCOMPUTABLE = "BLOCKED_UNCOMPUTABLE"
    RESEARCH_ONLY_REGIME_DEPENDENT = "RESEARCH_ONLY_REGIME_DEPENDENT"


class GateCode(StrEnum):
    DATA_PIT = "DATA_PIT"
    CV_CHRONOLOGY = "CV_CHRONOLOGY"
    PREPROCESSING = "PREPROCESSING"
    TRIAL_REGISTRY = "TRIAL_REGISTRY"
    DSR = "DSR"
    PBO = "PBO"
    COST_STRESS = "COST_STRESS"
    LEAKAGE = "LEAKAGE"
    SAMPLE_ADEQUACY = "SAMPLE_ADEQUACY"
    REGIME = "REGIME"
    RISK_LIMITS = "RISK_LIMITS"
    REPRODUCIBILITY = "REPRODUCIBILITY"


class GateOutcome(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    BLOCKED_MISSING_POLICY = "blocked_missing_policy"
    BLOCKED_UNCOMPUTABLE = "blocked_uncomputable"
    RESEARCH_ONLY = "research_only"


class LeakageCode(StrEnum):
    L01 = "L01"
    L02 = "L02"
    L03 = "L03"
    L04 = "L04"
    L05 = "L05"
    L06 = "L06"


class TrialStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"
    ABANDONED = "abandoned"
    NO_RETURN = "no_return"


class ResearchReturnStatus(StrEnum):
    OBSERVED = "observed"
    NO_TRADE = "no_trade"
    DELISTED = "delisted"
    MISSING = "missing"


class MissingReturnPolicy(StrEnum):
    BLOCK = "block_missing_return_v1"


class NoTradeReturnPolicy(StrEnum):
    EXPLICIT_ZERO = "explicit_zero_research_observation_v1"


class CostScenario(StrEnum):
    BASELINE = "baseline"
    ALL_COST_STRESS = "all_cost_stress"
    LIQUIDITY_STRESS = "liquidity_stress"


class FoldKind(StrEnum):
    OUTER = "outer"
    INNER = "inner"
    CPCV = "cpcv"


class TrainMode(StrEnum):
    EXPANDING_PAST_ONLY = "expanding_past_only"
    ROLLING_PAST_ONLY = "rolling_past_only"
    PURGED_COMBINATORIAL = "purged_combinatorial"


class SignalSpecification(StrictModel):
    specification_id: Identifier
    version: Identifier
    definition: str = Field(min_length=1, max_length=2000)
    deterministic_formula_id: Identifier
    forecast_horizon: str = Field(min_length=1, max_length=256)
    executable_decision_lag: str = Field(min_length=1, max_length=256)
    universe_eligibility_rule: str = Field(min_length=1, max_length=1000)
    universe_exclusion_rule: str = Field(min_length=1, max_length=1000)
    rebalance_rule: str = Field(min_length=1, max_length=1000)
    holding_rule: str = Field(min_length=1, max_length=1000)
    overlap_rule: str = Field(min_length=1, max_length=1000)
    output_semantics: Literal["research_score_only"] = "research_score_only"
    llm_generated: Literal[False] = False


class FeatureSpecification(StrictModel):
    feature_specification_id: UUID
    schema_version: Literal["phase5-feature-specification-v1"] = "phase5-feature-specification-v1"
    version: Identifier
    formula_id: Identifier
    source_fields: tuple[Identifier, ...] = Field(min_length=1)
    lookback_rule: str = Field(min_length=1, max_length=1000)
    availability_rule: str = Field(min_length=1, max_length=1000)
    source_observation_binding_rule: Literal["phase5-exact-snapshot-constituent-value-v1"]
    preprocessing_rules: tuple[Identifier, ...] = Field(min_length=1)
    imputation_policy: Identifier
    encoding_policy: Identifier
    feature_selection_policy: Identifier
    hyperparameter_policy: Identifier
    content_sha256: SHA256


class LabelSpecification(StrictModel):
    label_specification_id: UUID
    schema_version: Literal["phase5-label-specification-v1"] = "phase5-label-specification-v1"
    version: Identifier
    formula_id: Identifier
    forecast_horizon: str = Field(min_length=1, max_length=256)
    information_interval_rule: str = Field(min_length=1, max_length=1000)
    missing_return_policy: MissingReturnPolicy
    no_trade_return_policy: NoTradeReturnPolicy
    delisting_return_policy: Identifier
    content_sha256: SHA256


class WalkForwardPolicy(StrictModel):
    decision_timezone: Literal["UTC"] = "UTC"
    decision_calendar: Identifier
    outer_fold_count: int = Field(ge=2)
    inner_fold_count: int = Field(ge=2)
    minimum_train_observations: int = Field(ge=2)
    outer_test_observations: int = Field(ge=1)
    inner_test_observations: int = Field(ge=1)
    rolling_train_observations: int | None = Field(default=None, ge=2)
    train_mode: TrainMode
    purge_rule: Literal["label_interval_intersection_v1"] = "label_interval_intersection_v1"
    embargo_rule: Identifier | None
    embargo_seconds: int | None = Field(default=None, ge=1)
    final_confirmation_start_utc: datetime
    final_confirmation_end_utc: datetime
    final_confirmation_opening_rule: Identifier

    @field_validator("final_confirmation_start_utc", "final_confirmation_end_utc")
    @classmethod
    def normalize_times(cls, value: datetime, info: object) -> datetime:
        field_name = getattr(info, "field_name", "confirmation time")
        return _utc(value, field_name)

    @model_validator(mode="after")
    def validate_geometry(self) -> Self:
        if self.final_confirmation_end_utc <= self.final_confirmation_start_utc:
            raise ValueError("final confirmation interval must be positive")
        if (self.embargo_rule is None) != (self.embargo_seconds is None):
            raise ValueError("embargo rule and duration must be supplied together")
        if self.train_mode is not TrainMode.PURGED_COMBINATORIAL and self.embargo_rule is not None:
            raise ValueError("past-only folds cannot declare a post-test embargo")
        if (self.train_mode is TrainMode.ROLLING_PAST_ONLY) != (
            self.rolling_train_observations is not None
        ):
            raise ValueError("rolling mode requires an explicit rolling training window")
        if (
            self.rolling_train_observations is not None
            and self.rolling_train_observations < self.minimum_train_observations
        ):
            raise ValueError("rolling training window cannot be below the minimum train size")
        return self


class SampleAdequacyPolicy(StrictModel):
    min_oos_observations: int = Field(ge=2)
    min_independent_events: int = Field(ge=2)
    min_synchronized_trials: int = Field(ge=2)
    missing_return_policy: MissingReturnPolicy
    no_trade_return_policy: NoTradeReturnPolicy


class SelectionPolicy(StrictModel):
    primary_selection_metric: Literal["mean_net_return"] = "mean_net_return"
    raw_trial_definition: Identifier
    effective_trial_method: Literal["bailey-average-correlation-interpolation-v1"] = (
        "bailey-average-correlation-interpolation-v1"
    )
    dsr_min_probability: Decimal = Field(ge=Decimal("0"), le=Decimal("1"))
    cscv_block_count: int = Field(ge=2)
    pbo_tie_policy: Literal["reject_ties"] = "reject_ties"
    pbo_rank_orientation: Literal["worst_is_one"] = "worst_is_one"
    pbo_max: Decimal = Field(ge=Decimal("0"), le=Decimal("1"))
    return_frequency: Identifier
    annualization_factor: int = Field(ge=1)
    serial_correlation_method: Identifier

    @field_validator("cscv_block_count")
    @classmethod
    def require_even_blocks(cls, value: int) -> int:
        if value % 2:
            raise ValueError("CSCV block count must be even")
        return value


class CostPolicy(StrictModel):
    fee_schedule_id: Identifier
    fee_schedule_effective_date: str
    spread_source: Identifier
    spread_fallback_rule: Identifier
    impact_model_id: Identifier
    impact_model_version: Identifier
    impact_calibration_id: Identifier
    latency_rule: Identifier
    slippage_model_id: Identifier
    borrow_source: Identifier
    hard_to_borrow_rule: Identifier
    baseline_max_participation: Decimal = Field(gt=Decimal("0"), le=Decimal("1"))
    capacity_rule: Identifier


class StressPolicy(StrictModel):
    all_cost_multiplier: Decimal = Field(ge=Decimal("2"))
    spread_multiplier: Decimal = Field(ge=Decimal("1"))
    volatility_multiplier: Decimal = Field(ge=Decimal("1"))
    adv_multiplier: Decimal = Field(gt=Decimal("0"), le=Decimal("1"))
    impact_coefficient_multiplier: Decimal = Field(ge=Decimal("1"))
    latency_multiplier: Decimal = Field(ge=Decimal("1"))
    borrow_multiplier: Decimal = Field(ge=Decimal("1"))
    min_stressed_net_pnl: Decimal = Field(gt=Decimal("0"))
    min_stressed_annual_return: Decimal = Field(gt=Decimal("0"))
    min_stressed_sharpe: Decimal = Field(gt=Decimal("0"))
    max_stressed_drawdown: Decimal = Field(gt=Decimal("0"), le=Decimal("1"))
    max_capacity_breach_rate: Decimal = Field(ge=Decimal("0"), le=Decimal("1"))


class RegimePolicy(StrictModel):
    volatility_definition: Identifier
    volatility_cut: Decimal
    rate_definition: Identifier
    rate_cut: Decimal
    crisis_windows: tuple[Identifier, ...] = Field(min_length=1)
    dependency_rule: Identifier


class RiskPolicy(StrictModel):
    max_single_observation_exposure: Decimal = Field(gt=Decimal("0"))
    max_gross_exposure: Decimal = Field(gt=Decimal("0"))
    max_net_exposure: Decimal = Field(gt=Decimal("0"))
    max_sector_exposure: Decimal = Field(gt=Decimal("0"))
    max_turnover: Decimal = Field(gt=Decimal("0"))
    max_volatility: Decimal = Field(gt=Decimal("0"))
    max_loss: Decimal = Field(gt=Decimal("0"))
    max_drawdown: Decimal = Field(gt=Decimal("0"), le=Decimal("1"))


class AuditPolicy(StrictModel):
    required_fields: tuple[Identifier, ...] = Field(min_length=10)
    numeric_metadata_rule: Identifier
    append_only_rule: Identifier


class FrozenEvaluationPolicy(StrictModel):
    policy_id: UUID
    policy_version: int = Field(ge=1)
    schema_version: Literal["phase5-evaluation-policy-v1"] = "phase5-evaluation-policy-v1"
    policy_sha256: SHA256
    policy_canonical_json: str = Field(min_length=2)
    strategy_family: CanonicalFamily
    selection_scope: Identifier
    created_at_utc: datetime
    approved_by: Identifier
    synthetic_fixture_policy: Literal[True] = True
    signal_specification: SignalSpecification
    required_snapshot_capabilities: tuple[DataCapability, ...] = Field(min_length=1)
    feature_specification: FeatureSpecification
    label_specification: LabelSpecification
    walk_forward: WalkForwardPolicy
    sample_adequacy: SampleAdequacyPolicy
    selection: SelectionPolicy
    costs: CostPolicy
    stress: StressPolicy
    regimes: RegimePolicy
    risk: RiskPolicy
    audit: AuditPolicy

    @field_validator("created_at_utc")
    @classmethod
    def normalize_created_at(cls, value: datetime) -> datetime:
        return _utc(value, "created_at_utc")

    @model_validator(mode="after")
    def validate_family_and_capabilities(self) -> Self:
        allowed = {
            CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING,
            CanonicalFamily.B_TIME_SERIES_MOMENTUM_REGIME,
            CanonicalFamily.C_OFFICIAL_EVENT_TEXT_OVERLAY,
        }
        if self.strategy_family not in allowed:
            raise ValueError(
                "Phase 5 policies are limited to persisted BUILD_RESEARCH families A/B/C"
            )
        if len(self.required_snapshot_capabilities) != len(
            set(self.required_snapshot_capabilities)
        ):
            raise ValueError("required snapshot capabilities must be unique")
        if tuple(sorted(self.required_snapshot_capabilities, key=str)) != (
            self.required_snapshot_capabilities
        ):
            raise ValueError("required snapshot capabilities must be canonically sorted")
        if (
            self.label_specification.missing_return_policy
            is not self.sample_adequacy.missing_return_policy
            or self.label_specification.no_trade_return_policy
            is not self.sample_adequacy.no_trade_return_policy
        ):
            raise ValueError("label and sample-adequacy return policies must match")
        return self


class EvaluationPolicyCreateRequest(StrictModel):
    policy_id: UUID
    policy_version: int = Field(ge=1)


class EvaluationRunCreateRequest(StrictModel):
    policy_id: UUID
    policy_version: int = Field(ge=1)
    mapping_id: UUID
    snapshot_ids: tuple[UUID, ...] = Field(min_length=1)
    fixture_id: Identifier

    @model_validator(mode="after")
    def validate_snapshot_references(self) -> Self:
        if len(self.snapshot_ids) != len(set(self.snapshot_ids)):
            raise ValueError("snapshot identities must be unique")
        return self


class SourceObservationKey(StrictModel):
    capability: DataCapability
    normalized_observation_id: UUID


def source_feature_dependency_id(capability: DataCapability, payload_field: str) -> str:
    """Return the only canonical id for one exact Phase 4 feature field."""

    return f"phase4-{capability.value}.{payload_field}"


def label_dependency_id(label: LabelSpecification) -> str:
    """Return the canonical dependency id for the frozen label formula."""

    return f"label.{label.formula_id}"


class SourceFeatureDependencyNode(StrictModel):
    node_kind: Literal["source_feature"] = "source_feature"
    dependency_id: Identifier
    source_observation_key: SourceObservationKey
    source_payload_field: Literal["open", "volume"]
    feature_specification_sha256: SHA256

    @model_validator(mode="after")
    def validate_dependency_id(self) -> Self:
        expected = source_feature_dependency_id(
            self.source_observation_key.capability,
            self.source_payload_field,
        )
        if self.dependency_id != expected:
            raise ValueError("source feature dependency id must derive from its exact source field")
        return self


class LabelDependencyNode(StrictModel):
    node_kind: Literal["label", "future_label"]
    dependency_id: Identifier
    label_specification_sha256: SHA256
    label_formula_id: Identifier

    @model_validator(mode="after")
    def validate_dependency_id(self) -> Self:
        expected = (
            f"label.{self.label_formula_id}"
            if self.node_kind == "label"
            else f"future.label.{self.label_formula_id}"
        )
        if self.dependency_id != expected:
            raise ValueError("label dependency id must derive from its frozen label formula")
        return self


class DerivedDependencyGraph(StrictModel):
    schema_version: Literal["phase5-derived-dependency-graph-v1"] = (
        "phase5-derived-dependency-graph-v1"
    )
    sample_id: Identifier
    feature_nodes: tuple[SourceFeatureDependencyNode, ...] = Field(min_length=1)
    label_nodes: tuple[LabelDependencyNode, ...] = Field(min_length=1)
    graph_sha256: SHA256

    @model_validator(mode="after")
    def validate_graph(self) -> Self:
        feature_ids = tuple(node.dependency_id for node in self.feature_nodes)
        label_ids = tuple(node.dependency_id for node in self.label_nodes)
        if feature_ids != tuple(sorted(feature_ids)) or len(feature_ids) != len(set(feature_ids)):
            raise ValueError("derived feature dependency nodes must be unique and sorted")
        if label_ids != tuple(sorted(label_ids)) or len(label_ids) != len(set(label_ids)):
            raise ValueError("derived label dependency nodes must be unique and sorted")
        content = self.model_dump(mode="python", exclude={"graph_sha256"})
        if self.graph_sha256 != domain_sha256(PHASE5_DEPENDENCY_GRAPH_HASH_DOMAIN, content):
            raise ValueError("derived dependency graph hash must match its complete preimage")
        return self


class SourceFeatureDerivation(StrictModel):
    """Frozen preimage proving one feature value came from exact Phase 4 evidence."""

    schema_version: Literal["phase5-source-feature-derivation-v1"] = (
        "phase5-source-feature-derivation-v1"
    )
    formula_id: Literal["source-decimal-times-frozen-multiplier-v1"] = (
        "source-decimal-times-frozen-multiplier-v1"
    )
    source_observation_key: SourceObservationKey
    source_payload_field: Literal["open", "volume"]
    multiplier: Decimal
    derived_feature_value: Decimal
    derivation_sha256: SHA256

    @field_validator("multiplier", "derived_feature_value")
    @classmethod
    def validate_finite_derivation_value(cls, value: Decimal, info: object) -> Decimal:
        if not value.is_finite():
            raise ValueError(f"{getattr(info, 'field_name', 'derivation value')} must be finite")
        return value

    @model_validator(mode="after")
    def validate_derivation_hash(self) -> Self:
        content = self.model_dump(mode="python", exclude={"derivation_sha256"})
        if self.derivation_sha256 != domain_sha256(
            PHASE5_SOURCE_FEATURE_DERIVATION_HASH_DOMAIN,
            content,
        ):
            raise ValueError("feature derivation hash must match its complete frozen preimage")
        return self


class SourceValueBinding(StrictModel):
    source_payload_field: Literal["open", "volume"]
    sample_field: Literal["reference_price", "daily_adv_units"]
    multiplier: Decimal = Field(gt=Decimal("0"))


class SyntheticSourceObservationExpectation(StrictModel):
    schema_version: Literal["phase5-source-observation-expectation-v1"] = (
        "phase5-source-observation-expectation-v1"
    )
    key: SourceObservationKey
    normalized_observation: NormalizedObservationDraft
    required_disposition: ConstituentDisposition
    value_bindings: tuple[SourceValueBinding, ...] = ()

    @model_validator(mode="after")
    def validate_expectation(self) -> Self:
        if (
            self.key.normalized_observation_id
            != self.normalized_observation.normalized_observation_id
        ):
            raise ValueError("source expectation key must match normalized observation identity")
        binding_keys = tuple(
            (
                binding.source_payload_field,
                binding.sample_field,
                binding.multiplier,
            )
            for binding in self.value_bindings
        )
        if binding_keys != tuple(sorted(binding_keys)):
            raise ValueError("source value bindings must be canonically sorted")
        if len(binding_keys) != len(set(binding_keys)):
            raise ValueError("source value bindings must be unique")
        payload = self.normalized_observation.payload
        if isinstance(payload, UniverseMembershipPayload):
            if self.key.capability is not DataCapability.UNIVERSE_MEMBERSHIP:
                raise ValueError("membership expectation must use membership capability")
            if self.value_bindings:
                raise ValueError("membership expectation cannot use numeric sample bindings")
        elif not self.value_bindings:
            raise ValueError("numeric source expectations require at least one value binding")
        return self


class ResolvedSourceObservationRef(StrictModel):
    capability: DataCapability
    snapshot_id: UUID
    snapshot_sha256: SHA256
    raw_observation_id: UUID
    observation_revision_id: UUID
    normalized_observation_id: UUID
    raw_payload_sha256: SHA256
    normalized_content_sha256: SHA256


class ResolvedSourceObservation(StrictModel):
    schema_version: Literal["phase5-resolved-source-observation-v1"] = (
        "phase5-resolved-source-observation-v1"
    )
    key: SourceObservationKey
    normalized_observation: NormalizedObservation
    disposition: ConstituentDisposition

    @model_validator(mode="after")
    def validate_resolved_identity(self) -> Self:
        if (
            self.key.normalized_observation_id
            != self.normalized_observation.normalized_observation_id
        ):
            raise ValueError("resolved source key must match normalized observation identity")
        return self

    def reference(self) -> ResolvedSourceObservationRef:
        observation = self.normalized_observation
        return ResolvedSourceObservationRef(
            capability=self.key.capability,
            snapshot_id=observation.snapshot_id,
            snapshot_sha256=observation.snapshot_sha256,
            raw_observation_id=observation.raw_observation_id,
            observation_revision_id=observation.observation_revision_id,
            normalized_observation_id=observation.normalized_observation_id,
            raw_payload_sha256=observation.raw_payload_sha256,
            normalized_content_sha256=observation.normalized_content_sha256,
        )


class FundamentalRevisionEvidence(StrictModel):
    dependency_ids: tuple[Identifier, ...] = Field(min_length=1)
    revision_id: Identifier
    accepted_at_utc: datetime
    available_at_utc: datetime
    revision_trace_ids: tuple[Identifier, ...] = Field(min_length=1)

    @field_validator("accepted_at_utc", "available_at_utc")
    @classmethod
    def normalize_revision_time(cls, value: datetime, info: object) -> datetime:
        return _utc(value, getattr(info, "field_name", "fundamental revision time"))

    @model_validator(mode="after")
    def validate_revision_trace(self) -> Self:
        if self.dependency_ids != tuple(sorted(self.dependency_ids)):
            raise ValueError("fundamental dependency ids must be canonically sorted")
        if len(self.dependency_ids) != len(set(self.dependency_ids)):
            raise ValueError("fundamental dependency ids must be unique")
        if len(self.revision_trace_ids) != len(set(self.revision_trace_ids)):
            raise ValueError("fundamental revision trace ids must be unique")
        if self.revision_trace_ids[-1] != self.revision_id:
            raise ValueError("fundamental revision trace must end at the accepted revision")
        if self.accepted_at_utc > self.available_at_utc:
            raise ValueError("fundamental acceptance cannot follow availability")
        return self


class UniverseMembershipEvidence(StrictModel):
    membership_id: Identifier
    universe_id: Identifier
    membership_status: Literal["included", "excluded"]
    as_of_utc: datetime
    valid_from_utc: datetime
    valid_to_utc: datetime | None

    @field_validator("as_of_utc", "valid_from_utc", "valid_to_utc")
    @classmethod
    def normalize_membership_times(
        cls,
        value: datetime | None,
        info: object,
    ) -> datetime | None:
        if value is None:
            return None
        return _utc(value, getattr(info, "field_name", "membership time"))


class LeakageEvidenceBase(StrictModel):
    passed: bool
    reason_codes: tuple[Identifier, ...]
    evidence_sha256: SHA256

    @model_validator(mode="after")
    def validate_outcome(self) -> Self:
        if self.reason_codes != tuple(sorted(self.reason_codes)):
            raise ValueError("leakage evidence reason codes must be canonically sorted")
        if len(self.reason_codes) != len(set(self.reason_codes)):
            raise ValueError("leakage evidence reason codes must be unique")
        if self.passed == bool(self.reason_codes):
            raise ValueError("leakage evidence pass state must match reason-code absence")
        content = self.model_dump(mode="python", exclude={"evidence_sha256"})
        if self.evidence_sha256 != domain_sha256(PHASE5_LEAKAGE_EVIDENCE_HASH_DOMAIN, content):
            raise ValueError("leakage evidence hash must match its complete semantic preimage")
        return self


def _validate_evidence_reasons(
    evidence: LeakageEvidenceBase,
    expected_reasons: tuple[str, ...],
) -> None:
    expected = tuple(sorted(set(expected_reasons)))
    if evidence.reason_codes != expected or evidence.passed is bool(expected):
        raise ValueError("leakage evidence outcome must derive from its raw evidence fields")


class L01PriceBasisEvidence(LeakageEvidenceBase):
    schema_version: Literal["phase5-leakage-l01-evidence-v1"] = "phase5-leakage-l01-evidence-v1"
    code: Literal[LeakageCode.L01] = LeakageCode.L01
    sample_id: Identifier
    source_observation_key: SourceObservationKey | None
    source_snapshot_id: UUID | None
    source_snapshot_sha256: SHA256 | None
    source_payload_field: Literal["open"] | None
    source_price: Decimal | None
    source_adjustment_basis: Literal["raw_unadjusted", "as_of_adjusted"] | None
    source_adjustment_as_of_utc: datetime | None
    source_corporate_action_revision_ids: tuple[Identifier, ...]
    source_event_time_utc: datetime | None
    source_available_at_utc: datetime | None
    effective_price: Decimal
    effective_price_basis: Literal["raw_unadjusted", "adjusted_for_corporate_action"] | None
    effective_adjustment_as_of_utc: datetime | None
    decision_time_utc: datetime
    price_values_match: bool
    price_bases_match: bool
    action_as_of_values_match: bool

    @field_validator(
        "source_adjustment_as_of_utc",
        "source_event_time_utc",
        "source_available_at_utc",
        "effective_adjustment_as_of_utc",
        "decision_time_utc",
    )
    @classmethod
    def normalize_l01_times(
        cls,
        value: datetime | None,
        info: object,
    ) -> datetime | None:
        if value is None:
            return None
        return _utc(value, getattr(info, "field_name", "L01 evidence time"))

    @model_validator(mode="after")
    def validate_l01_semantics(self) -> Self:
        reasons: list[str] = []
        if self.source_snapshot_id is None:
            reasons.append("l01_source_observation_missing")
        elif self.source_price is None or self.source_adjustment_basis is None:
            reasons.append("l01_source_payload_not_ohlcv")
        if self.source_payload_field != "open":
            reasons.append("l01_source_price_field_not_open")
        if self.effective_price_basis is None:
            reasons.append("l01_effective_price_basis_missing")
        if self.source_price is not None and not self.price_values_match:
            reasons.append("l01_source_effective_price_mismatch")
        if self.source_adjustment_basis is not None and not self.price_bases_match:
            reasons.append("l01_source_effective_basis_mismatch")
        if self.source_adjustment_basis is not None and not self.action_as_of_values_match:
            reasons.append("l01_source_effective_action_as_of_mismatch")
        if (
            self.source_adjustment_as_of_utc is not None
            and self.source_adjustment_as_of_utc > self.decision_time_utc
        ) or (
            self.effective_adjustment_as_of_utc is not None
            and self.effective_adjustment_as_of_utc > self.decision_time_utc
        ):
            reasons.append("l01_adjustment_action_future")
        if (
            self.source_event_time_utc is not None
            and self.source_event_time_utc > self.decision_time_utc
        ) or (
            self.source_available_at_utc is not None
            and self.source_available_at_utc > self.decision_time_utc
        ):
            reasons.append("l01_source_timestamp_future")
        if (
            self.source_adjustment_basis == "as_of_adjusted"
            and not self.source_corporate_action_revision_ids
        ):
            reasons.append("l01_adjustment_revision_trace_missing")
        expected_price_match = (
            self.source_price is not None and self.source_price == self.effective_price
        )
        expected_basis = (
            "raw_unadjusted"
            if self.source_adjustment_basis == "raw_unadjusted"
            else "adjusted_for_corporate_action"
            if self.source_adjustment_basis == "as_of_adjusted"
            else None
        )
        if self.price_values_match is not expected_price_match:
            raise ValueError("L01 price-match flag must derive from source and effective price")
        if self.price_bases_match is not (
            expected_basis is not None and self.effective_price_basis == expected_basis
        ):
            raise ValueError("L01 basis-match flag must derive from source and effective basis")
        if self.action_as_of_values_match is not (
            self.source_adjustment_basis is not None
            and self.source_adjustment_as_of_utc == self.effective_adjustment_as_of_utc
        ):
            raise ValueError("L01 action-as-of flag must derive from source and effective evidence")
        _validate_evidence_reasons(self, tuple(reasons))
        return self


class L02FundamentalRevisionEvidence(LeakageEvidenceBase):
    schema_version: Literal["phase5-leakage-l02-evidence-v1"] = "phase5-leakage-l02-evidence-v1"
    code: Literal[LeakageCode.L02] = LeakageCode.L02
    sample_id: Identifier
    fundamental_dependency_ids: tuple[Identifier, ...]
    applicable: bool
    non_applicability_reason: Literal["no_fundamental_dependency"] | None
    source_observation_refs: tuple[ResolvedSourceObservationRef, ...]
    evidence_dependency_ids: tuple[Identifier, ...]
    revision_id: Identifier | None
    accepted_at_utc: datetime | None
    available_at_utc: datetime | None
    revision_trace_ids: tuple[Identifier, ...]
    decision_time_utc: datetime
    declared_revision_evidence_present: bool
    declared_revision_matches_source: bool

    @field_validator("accepted_at_utc", "available_at_utc", "decision_time_utc")
    @classmethod
    def normalize_l02_times(
        cls,
        value: datetime | None,
        info: object,
    ) -> datetime | None:
        if value is None:
            return None
        return _utc(value, getattr(info, "field_name", "L02 evidence time"))

    @model_validator(mode="after")
    def validate_l02_semantics(self) -> Self:
        reasons: list[str] = []
        expected_applicable = bool(self.source_observation_refs)
        if self.applicable is not expected_applicable:
            raise ValueError("L02 applicability must derive from a resolved fundamental source")
        expected_nonapplicable = None if expected_applicable else "no_fundamental_dependency"
        if self.non_applicability_reason != expected_nonapplicable:
            raise ValueError("L02 non-applicability must derive from resolved source capabilities")
        if not expected_applicable:
            if self.fundamental_dependency_ids or self.evidence_dependency_ids:
                reasons.append("l02_unresolved_fundamental_dependency")
            if self.declared_revision_evidence_present:
                reasons.append("l02_unscoped_fundamental_evidence")
            if (
                any(
                    value is not None
                    for value in (self.revision_id, self.accepted_at_utc, self.available_at_utc)
                )
                or self.revision_trace_ids
            ):
                reasons.append("l02_unresolved_fundamental_source_fields")
        else:
            if len(self.source_observation_refs) != 1:
                reasons.append("l02_fundamental_source_ambiguous")
            if not self.fundamental_dependency_ids:
                reasons.append("l02_fundamental_dependency_evidence_missing")
            if self.evidence_dependency_ids != self.fundamental_dependency_ids:
                reasons.append("l02_fundamental_dependency_trace_mismatch")
            if (
                self.revision_id is None
                or not self.revision_trace_ids
                or self.revision_trace_ids[-1] != self.revision_id
                or len(self.revision_trace_ids) != len(set(self.revision_trace_ids))
            ):
                reasons.append("l02_fundamental_revision_trace_invalid")
            if self.accepted_at_utc is None or self.available_at_utc is None:
                reasons.append("l02_fundamental_timestamp_evidence_missing")
            else:
                if self.accepted_at_utc > self.available_at_utc:
                    reasons.append("l02_fundamental_timestamp_order_invalid")
                if self.accepted_at_utc > self.decision_time_utc:
                    reasons.append("l02_fundamental_acceptance_future")
                if self.available_at_utc > self.decision_time_utc:
                    reasons.append("l02_fundamental_availability_future")
            if (
                self.declared_revision_evidence_present
                and not self.declared_revision_matches_source
            ):
                reasons.append("l02_declared_revision_evidence_mismatch")
        if not self.declared_revision_evidence_present and self.declared_revision_matches_source:
            raise ValueError("L02 absent declared evidence cannot be marked source-matched")
        _validate_evidence_reasons(self, tuple(reasons))
        return self


class L03SourceInformationIntervalEvidence(StrictModel):
    schema_version: Literal["phase5-leakage-l03-source-interval-v1"] = (
        "phase5-leakage-l03-source-interval-v1"
    )
    source_observation_key: SourceObservationKey
    declared_source_observation_ref: ResolvedSourceObservationRef | None
    declared_reference_count: int = Field(ge=0)
    resolved_source_observation_ref: ResolvedSourceObservationRef | None
    source_resolution_count: int = Field(ge=0)
    source_event_time_utc: datetime | None
    source_available_at_utc: datetime | None
    exact_reference_matches: bool

    @field_validator("source_event_time_utc", "source_available_at_utc")
    @classmethod
    def normalize_l03_source_times(
        cls,
        value: datetime | None,
        info: object,
    ) -> datetime | None:
        if value is None:
            return None
        return _utc(value, getattr(info, "field_name", "L03 source evidence time"))

    @model_validator(mode="after")
    def validate_l03_source_identity(self) -> Self:
        key = (
            self.source_observation_key.capability,
            self.source_observation_key.normalized_observation_id,
        )
        declared_key = (
            (
                self.declared_source_observation_ref.capability,
                self.declared_source_observation_ref.normalized_observation_id,
            )
            if self.declared_source_observation_ref is not None
            else None
        )
        resolved_key = (
            (
                self.resolved_source_observation_ref.capability,
                self.resolved_source_observation_ref.normalized_observation_id,
            )
            if self.resolved_source_observation_ref is not None
            else None
        )
        expected_match = bool(
            self.source_resolution_count == 1
            and self.declared_reference_count == 1
            and self.declared_source_observation_ref is not None
            and self.resolved_source_observation_ref is not None
            and declared_key == key
            and resolved_key == key
            and self.declared_source_observation_ref == self.resolved_source_observation_ref
        )
        if self.exact_reference_matches is not expected_match:
            raise ValueError(
                "L03 exact-reference flag must derive from declared and resolved source evidence"
            )
        return self


class L03FeatureAvailabilityEvidence(LeakageEvidenceBase):
    schema_version: Literal["phase5-leakage-l03-evidence-v2"] = "phase5-leakage-l03-evidence-v2"
    code: Literal[LeakageCode.L03] = LeakageCode.L03
    sample_id: Identifier
    assertion: Literal[
        "source_event_time_utc<=feature_available_at_utc;"
        "source_available_at_utc<=feature_available_at_utc<=decision_time_utc"
    ] = (
        "source_event_time_utc<=feature_available_at_utc;"
        "source_available_at_utc<=feature_available_at_utc<=decision_time_utc"
    )
    source_information_intervals: tuple[L03SourceInformationIntervalEvidence, ...]
    feature_available_at_utc: datetime
    decision_time_utc: datetime

    @field_validator("feature_available_at_utc", "decision_time_utc")
    @classmethod
    def normalize_l03_times(cls, value: datetime, info: object) -> datetime:
        return _utc(value, getattr(info, "field_name", "L03 evidence time"))

    @model_validator(mode="after")
    def validate_l03_semantics(self) -> Self:
        source_keys = tuple(
            (
                str(item.source_observation_key.capability),
                str(item.source_observation_key.normalized_observation_id),
            )
            for item in self.source_information_intervals
        )
        if source_keys != tuple(sorted(source_keys)):
            raise ValueError("L03 source information intervals must be canonically sorted")
        if len(source_keys) != len(set(source_keys)):
            raise ValueError("L03 source information intervals must be unique")

        reasons: list[str] = []
        if not self.source_information_intervals:
            reasons.append("l03_source_observation_keys_missing")
        if self.feature_available_at_utc > self.decision_time_utc:
            reasons.append("l03_feature_available_after_decision")
        for interval in self.source_information_intervals:
            if (
                interval.source_resolution_count != 1
                or interval.resolved_source_observation_ref is None
            ):
                reasons.append("l03_source_observation_missing_or_ambiguous")
            elif not interval.exact_reference_matches:
                reasons.append("l03_source_observation_ref_mismatch")
            if interval.source_event_time_utc is None or interval.source_available_at_utc is None:
                reasons.append("l03_source_timestamp_evidence_missing")
                continue
            if interval.source_event_time_utc > self.feature_available_at_utc:
                reasons.append("l03_source_event_after_feature_available")
            if interval.source_available_at_utc > self.feature_available_at_utc:
                reasons.append("l03_source_available_after_feature_available")
        _validate_evidence_reasons(self, tuple(reasons))
        return self


class AdversarialDependencyProbe(StrictModel):
    candidate_dependency_id: Identifier
    injected_feature_dependency_ids: tuple[Identifier, ...]
    detected_overlap_ids: tuple[Identifier, ...]
    scanner_succeeded: bool
    caught: bool

    @model_validator(mode="after")
    def validate_probe(self) -> Self:
        if self.candidate_dependency_id not in self.injected_feature_dependency_ids:
            raise ValueError("adversarial dependency probe must inject its candidate")
        expected_detected = (self.candidate_dependency_id,) if self.scanner_succeeded else ()
        if self.detected_overlap_ids != expected_detected:
            raise ValueError("adversarial dependency probe result must come from the scanner")
        if self.caught is not (
            self.scanner_succeeded and self.candidate_dependency_id in self.detected_overlap_ids
        ):
            raise ValueError("adversarial dependency caught flag must derive from scanner evidence")
        return self


class AdversarialDependencyReview(StrictModel):
    schema_version: Literal["phase5-adversarial-dependency-review-v1"] = (
        "phase5-adversarial-dependency-review-v1"
    )
    sample_id: Identifier
    dependency_graph_sha256: SHA256
    baseline_feature_dependency_ids: tuple[Identifier, ...]
    adversarial_candidate_dependency_ids: tuple[Identifier, ...]
    probes: tuple[AdversarialDependencyProbe, ...]
    review_complete: bool
    review_sha256: SHA256

    @model_validator(mode="after")
    def validate_review(self) -> Self:
        if self.baseline_feature_dependency_ids != tuple(
            sorted(self.baseline_feature_dependency_ids)
        ):
            raise ValueError("review feature dependency ids must be canonically sorted")
        if self.adversarial_candidate_dependency_ids != tuple(
            sorted(self.adversarial_candidate_dependency_ids)
        ):
            raise ValueError("review candidate dependency ids must be canonically sorted")
        if tuple(probe.candidate_dependency_id for probe in self.probes) != (
            self.adversarial_candidate_dependency_ids
        ):
            raise ValueError("adversarial probes must cover every target dependency in order")
        expected_complete = bool(self.adversarial_candidate_dependency_ids) and all(
            probe.caught for probe in self.probes
        )
        if self.review_complete is not expected_complete:
            raise ValueError("adversarial review completeness must derive from every probe")
        content = self.model_dump(mode="python", exclude={"review_sha256"})
        if self.review_sha256 != domain_sha256(
            PHASE5_ADVERSARIAL_DEPENDENCY_REVIEW_HASH_DOMAIN,
            content,
        ):
            raise ValueError("adversarial dependency review hash must match its preimage")
        return self


class L04DependencyScanEvidence(LeakageEvidenceBase):
    schema_version: Literal["phase5-leakage-l04-evidence-v1"] = "phase5-leakage-l04-evidence-v1"
    code: Literal[LeakageCode.L04] = LeakageCode.L04
    sample_id: Identifier
    dependency_graph: DerivedDependencyGraph
    declared_feature_dependency_ids: tuple[Identifier, ...]
    declared_target_dependency_ids: tuple[Identifier, ...]
    derived_feature_dependency_ids: tuple[Identifier, ...]
    derived_target_dependency_ids: tuple[Identifier, ...]
    feature_specification_matches_graph: bool
    label_specification_matches_graph: bool
    baseline_overlap_ids: tuple[Identifier, ...]
    adversarial_review: AdversarialDependencyReview

    @model_validator(mode="after")
    def validate_l04_semantics(self) -> Self:
        graph_feature_ids = tuple(
            node.dependency_id for node in self.dependency_graph.feature_nodes
        )
        graph_target_ids = tuple(
            node.dependency_id
            for node in self.dependency_graph.label_nodes
            if node.node_kind == "label"
        )
        if self.derived_feature_dependency_ids != graph_feature_ids:
            raise ValueError("L04 derived feature ids must come from the frozen dependency graph")
        if self.derived_target_dependency_ids != graph_target_ids:
            raise ValueError("L04 derived target ids must come from the frozen dependency graph")
        expected_overlap = tuple(sorted(set(graph_feature_ids) & set(graph_target_ids)))
        if self.baseline_overlap_ids != expected_overlap:
            raise ValueError("L04 overlap must derive from the frozen dependency graph")
        if self.adversarial_review.dependency_graph_sha256 != self.dependency_graph.graph_sha256:
            raise ValueError("L04 adversarial review must bind the exact dependency graph")
        reasons: list[str] = []
        if self.declared_feature_dependency_ids != graph_feature_ids:
            reasons.append("l04_feature_dependency_graph_mismatch")
        if self.declared_target_dependency_ids != graph_target_ids:
            reasons.append("l04_target_dependency_graph_mismatch")
        if not self.feature_specification_matches_graph:
            reasons.append("l04_feature_specification_graph_mismatch")
        if not self.label_specification_matches_graph:
            reasons.append("l04_label_specification_graph_mismatch")
        if expected_overlap:
            reasons.append("l04_target_or_future_proxy_detected")
        if not self.adversarial_review.review_complete:
            reasons.append("l04_adversarial_review_incomplete")
        _validate_evidence_reasons(self, tuple(reasons))
        return self


class L05MembershipReconstructionEvidence(LeakageEvidenceBase):
    schema_version: Literal["phase5-leakage-l05-evidence-v1"] = "phase5-leakage-l05-evidence-v1"
    code: Literal[LeakageCode.L05] = LeakageCode.L05
    sample_id: Identifier
    source_observation_ref: ResolvedSourceObservationRef | None
    membership_id: Identifier | None
    universe_id: Identifier | None
    membership_status: Literal["included", "excluded"] | None
    as_of_utc: datetime | None
    valid_from_utc: datetime | None
    valid_to_utc: datetime | None
    decision_time_utc: datetime
    as_of_known_at_decision: bool
    interval_contains_decision: bool
    reconstructed_included: bool
    feature_source_identity_matches: bool
    declared_membership_matches_source: bool

    @field_validator("as_of_utc", "valid_from_utc", "valid_to_utc", "decision_time_utc")
    @classmethod
    def normalize_l05_times(
        cls,
        value: datetime | None,
        info: object,
    ) -> datetime | None:
        if value is None:
            return None
        return _utc(value, getattr(info, "field_name", "L05 evidence time"))

    @model_validator(mode="after")
    def validate_l05_semantics(self) -> Self:
        source_present = self.source_observation_ref is not None
        expected_as_of_known = (
            source_present
            and self.as_of_utc is not None
            and self.as_of_utc <= self.decision_time_utc
        )
        expected_interval = (
            source_present
            and self.valid_from_utc is not None
            and self.valid_from_utc <= self.decision_time_utc
            and (self.valid_to_utc is None or self.decision_time_utc < self.valid_to_utc)
        )
        expected_included = (
            self.membership_status == "included"
            and expected_as_of_known
            and expected_interval
            and self.feature_source_identity_matches
            and self.declared_membership_matches_source
        )
        if self.as_of_known_at_decision is not expected_as_of_known:
            raise ValueError("L05 as-of flag must derive from resolved membership availability")
        if self.interval_contains_decision is not expected_interval:
            raise ValueError("L05 interval flag must derive from resolved membership validity")
        if self.reconstructed_included is not expected_included:
            raise ValueError(
                "L05 included flag must derive from exact resolved membership evidence"
            )
        reasons: list[str] = []
        if not source_present:
            reasons.append("l05_membership_source_missing_or_ambiguous")
        else:
            if not expected_as_of_known:
                reasons.append("l05_membership_as_of_future")
            if self.valid_from_utc is None or self.valid_from_utc > self.decision_time_utc:
                reasons.append("l05_membership_valid_from_future")
            if self.valid_to_utc is not None and self.decision_time_utc >= self.valid_to_utc:
                reasons.append("l05_membership_validity_expired")
            if (
                self.valid_from_utc is not None
                and self.valid_to_utc is not None
                and self.valid_to_utc <= self.valid_from_utc
            ):
                reasons.append("l05_membership_interval_invalid")
            if self.membership_status != "included":
                reasons.append("l05_membership_not_included")
            if not self.feature_source_identity_matches:
                reasons.append("l05_membership_feature_identity_mismatch")
            if not self.declared_membership_matches_source:
                reasons.append("l05_declared_membership_mismatch")
        _validate_evidence_reasons(self, tuple(reasons))
        return self


class L06TrainOnlyFitEvidence(LeakageEvidenceBase):
    schema_version: Literal["phase5-leakage-l06-evidence-v1"] = "phase5-leakage-l06-evidence-v1"
    code: Literal[LeakageCode.L06] = LeakageCode.L06
    fold_id: UUID | None
    fold_sha256: SHA256 | None
    fit_ids: tuple[UUID, ...]
    fit_sha256s: tuple[SHA256, ...]
    expected_train_sample_ids: tuple[Identifier, ...]
    observed_fit_train_sample_ids: tuple[Identifier, ...]
    missing_train_sample_ids: tuple[Identifier, ...]
    unexpected_train_sample_ids: tuple[Identifier, ...]
    disallowed_train_sample_ids: tuple[Identifier, ...]
    invalid_fit_ids: tuple[UUID, ...]
    exact_one_fit: bool
    fold_hashes_match: bool
    fit_statistics_match_source_values: bool

    @model_validator(mode="after")
    def validate_l06_semantics(self) -> Self:
        expected_missing = tuple(
            sorted(set(self.expected_train_sample_ids) - set(self.observed_fit_train_sample_ids))
        )
        expected_unexpected = tuple(
            sorted(set(self.observed_fit_train_sample_ids) - set(self.expected_train_sample_ids))
        )
        if self.missing_train_sample_ids != expected_missing:
            raise ValueError("L06 missing train ids must derive from expected and observed ids")
        if self.unexpected_train_sample_ids != expected_unexpected:
            raise ValueError("L06 unexpected train ids must derive from expected and observed ids")
        if self.exact_one_fit is not (len(self.fit_ids) == 1):
            raise ValueError("L06 exact-one-fit flag must derive from fit identities")
        if len(self.fit_ids) != len(self.fit_sha256s):
            raise ValueError("L06 fit identities and hashes must remain aligned")
        reasons: list[str] = []
        if self.fold_id is None:
            reasons.append("l06_fold_evidence_missing")
        elif self.fold_sha256 is None:
            reasons.append("l06_fit_references_unknown_fold")
        elif not self.exact_one_fit:
            reasons.append("l06_exactly_one_fold_fit_required")
        if expected_missing or expected_unexpected:
            reasons.append("l06_fit_train_ids_mismatch")
        if self.disallowed_train_sample_ids:
            reasons.append("l06_disallowed_fold_partition_ids")
        if self.fold_sha256 is not None and not self.fold_hashes_match:
            reasons.append("l06_fit_fold_hash_mismatch")
        if self.invalid_fit_ids or not self.fit_statistics_match_source_values:
            reasons.append("l06_fit_semantic_preimage_mismatch")
        _validate_evidence_reasons(self, tuple(reasons))
        return self


LeakageEvidenceRecord = (
    L01PriceBasisEvidence
    | L02FundamentalRevisionEvidence
    | L03FeatureAvailabilityEvidence
    | L04DependencyScanEvidence
    | L05MembershipReconstructionEvidence
    | L06TrainOnlyFitEvidence
)


class LeakageFindingEvidence(StrictModel):
    code: LeakageCode
    blocked: bool
    affected_sample_ids: tuple[Identifier, ...]
    evidence_rule: str = Field(min_length=1, max_length=2000)
    evidence_records: tuple[LeakageEvidenceRecord, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_finding(self) -> Self:
        if any(record.code is not self.code for record in self.evidence_records):
            raise ValueError("leakage finding records must match their check code")
        expected_blocked = any(not record.passed for record in self.evidence_records)
        if self.blocked is not expected_blocked:
            raise ValueError("leakage finding blocked state must derive from its evidence")
        affected: set[str] = set()
        for record in self.evidence_records:
            if record.passed:
                continue
            if isinstance(record, L06TrainOnlyFitEvidence):
                record_affected = set(record.missing_train_sample_ids)
                record_affected.update(record.unexpected_train_sample_ids)
                record_affected.update(record.disallowed_train_sample_ids)
                if not record_affected and record.expected_train_sample_ids:
                    record_affected.update(record.expected_train_sample_ids)
                affected.update(record_affected)
            else:
                affected.add(record.sample_id)
        if set(self.affected_sample_ids) != affected or len(self.affected_sample_ids) != len(
            affected
        ):
            raise ValueError("leakage finding affected ids must derive from failed records")
        return self


class LeakageGateEvidence(StrictModel):
    schema_version: Literal["phase5-leakage-gate-evidence-v1"] = "phase5-leakage-gate-evidence-v1"
    findings: tuple[LeakageFindingEvidence, ...] = Field(min_length=6, max_length=6)

    @model_validator(mode="after")
    def validate_exact_check_set(self) -> Self:
        if tuple(finding.code for finding in self.findings) != tuple(LeakageCode):
            raise ValueError("leakage gate evidence must contain L01-L06 exactly once in order")
        return self


class SyntheticSample(StrictModel):
    sample_id: Identifier
    source_observation_keys: tuple[SourceObservationKey, ...] = Field(min_length=1)
    feature_derivation: SourceFeatureDerivation
    synthetic_ledger_value_rule: Literal["deterministic-synthetic-research-ledger-input-v1"] = (
        "deterministic-synthetic-research-ledger-input-v1"
    )
    decision_time_utc: datetime
    feature_available_at_utc: datetime
    label_t0_utc: datetime
    label_t1_utc: datetime
    feature_value: Decimal
    predicted_value: Decimal
    return_status: ResearchReturnStatus = ResearchReturnStatus.OBSERVED
    gross_return: Decimal | None
    research_allocation_units: Decimal = Field(ge=Decimal("0"))
    reference_price: Decimal = Field(gt=Decimal("0"))
    daily_adv_units: Decimal = Field(gt=Decimal("0"))
    daily_volatility: Decimal = Field(gt=Decimal("0"))
    fee_rate: Decimal = Field(ge=Decimal("0"))
    half_spread_rate: Decimal = Field(ge=Decimal("0"))
    impact_coefficient: Decimal = Field(ge=Decimal("0"))
    latency_rate: Decimal = Field(ge=Decimal("0"))
    borrow_rate: Decimal = Field(ge=Decimal("0"))
    borrow_applicable: bool
    hard_to_borrow_available: bool
    independent_event_id: Identifier
    regime_id: Identifier
    rate_available_at_utc: datetime
    rate_change: Decimal
    crisis_window_ids: tuple[Identifier, ...]
    gross_exposure: Decimal = Field(ge=Decimal("0"))
    net_exposure: Decimal
    sector_exposure: Decimal = Field(ge=Decimal("0"))
    turnover: Decimal = Field(ge=Decimal("0"))
    price_adjustment_basis: Literal["raw_unadjusted", "adjusted_for_corporate_action"] | None
    adjustment_action_as_of_utc: datetime | None
    fundamental_revision: FundamentalRevisionEvidence | None
    feature_dependency_ids: tuple[Identifier, ...]
    target_dependency_ids: tuple[Identifier, ...]
    universe_membership: UniverseMembershipEvidence | None
    delisting_return_handled: bool = True

    @field_validator(
        "decision_time_utc",
        "feature_available_at_utc",
        "label_t0_utc",
        "label_t1_utc",
        "rate_available_at_utc",
    )
    @classmethod
    def normalize_sample_times(cls, value: datetime, info: object) -> datetime:
        return _utc(value, getattr(info, "field_name", "sample time"))

    @field_validator("adjustment_action_as_of_utc")
    @classmethod
    def normalize_optional_action_time(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return _utc(value, "adjustment_action_as_of_utc")

    @model_validator(mode="after")
    def validate_interval(self) -> Self:
        if self.label_t1_utc < self.label_t0_utc:
            raise ValueError("label interval must be ordered")
        if len(self.crisis_window_ids) != len(set(self.crisis_window_ids)):
            raise ValueError("crisis-window identities must be unique")
        for field_name, dependency_ids in (
            ("feature_dependency_ids", self.feature_dependency_ids),
            ("target_dependency_ids", self.target_dependency_ids),
        ):
            if dependency_ids != tuple(sorted(dependency_ids)):
                raise ValueError(f"{field_name} must be canonically sorted")
            if len(dependency_ids) != len(set(dependency_ids)):
                raise ValueError(f"{field_name} must be unique")
        source_keys = tuple(
            (str(key.capability), str(key.normalized_observation_id))
            for key in self.source_observation_keys
        )
        if source_keys != tuple(sorted(source_keys)):
            raise ValueError("sample source-observation keys must be canonically sorted")
        if len(source_keys) != len(set(source_keys)):
            raise ValueError("sample source-observation keys must be unique")
        derivation_key = (
            str(self.feature_derivation.source_observation_key.capability),
            str(self.feature_derivation.source_observation_key.normalized_observation_id),
        )
        if derivation_key not in set(source_keys):
            raise ValueError(
                "feature derivation must reference a declared sample source observation"
            )
        if self.feature_derivation.derived_feature_value != self.feature_value:
            raise ValueError("sample feature value must match its frozen source derivation")
        if self.return_status is ResearchReturnStatus.MISSING:
            if self.gross_return is not None:
                raise ValueError("missing return status requires a null gross return")
        elif self.gross_return is None or not self.gross_return.is_finite():
            raise ValueError("non-missing return status requires a finite gross return")
        if self.return_status is ResearchReturnStatus.NO_TRADE:
            if self.gross_return != 0:
                raise ValueError("no-trade observations require an explicit zero gross return")
            if any(
                value != 0
                for value in (
                    self.research_allocation_units,
                    self.gross_exposure,
                    self.net_exposure,
                    self.sector_exposure,
                    self.turnover,
                )
            ):
                raise ValueError("no-trade observations require zero synthetic allocation state")
            if self.borrow_applicable:
                raise ValueError("no-trade observations cannot incur borrow")
        elif self.return_status is not ResearchReturnStatus.MISSING:
            if self.research_allocation_units <= 0:
                raise ValueError("observed and delisted returns require positive allocation")
        return self


class LeakageSampleAuditInput(Protocol):
    """Minimum frozen sample preimage needed to reproduce leakage checks L01-L05."""

    sample_id: str

    @property
    def source_observation_keys(self) -> tuple[SourceObservationKey, ...]: ...

    feature_derivation: SourceFeatureDerivation
    decision_time_utc: datetime
    feature_available_at_utc: datetime
    reference_price: Decimal
    price_adjustment_basis: Literal["raw_unadjusted", "adjusted_for_corporate_action"] | None
    adjustment_action_as_of_utc: datetime | None
    fundamental_revision: FundamentalRevisionEvidence | None
    feature_dependency_ids: tuple[str, ...]
    target_dependency_ids: tuple[str, ...]
    universe_membership: UniverseMembershipEvidence | None


def derive_dependency_graph(
    sample: LeakageSampleAuditInput,
    feature_specification: FeatureSpecification,
    label_specification: LabelSpecification,
) -> DerivedDependencyGraph:
    """Build the only authoritative feature/label graph from frozen contracts."""

    derivation = sample.feature_derivation
    feature_node = SourceFeatureDependencyNode(
        dependency_id=source_feature_dependency_id(
            derivation.source_observation_key.capability,
            derivation.source_payload_field,
        ),
        source_observation_key=derivation.source_observation_key,
        source_payload_field=derivation.source_payload_field,
        feature_specification_sha256=feature_specification.content_sha256,
    )
    label_node = LabelDependencyNode(
        node_kind="label",
        dependency_id=label_dependency_id(label_specification),
        label_specification_sha256=label_specification.content_sha256,
        label_formula_id=label_specification.formula_id,
    )
    future_node = LabelDependencyNode(
        node_kind="future_label",
        dependency_id=f"future.label.{label_specification.formula_id}",
        label_specification_sha256=label_specification.content_sha256,
        label_formula_id=label_specification.formula_id,
    )
    content = {
        "schema_version": "phase5-derived-dependency-graph-v1",
        "sample_id": sample.sample_id,
        "feature_nodes": (feature_node,),
        "label_nodes": tuple(
            sorted((label_node, future_node), key=lambda node: node.dependency_id)
        ),
    }
    return DerivedDependencyGraph.model_validate(
        {
            **content,
            "graph_sha256": domain_sha256(PHASE5_DEPENDENCY_GRAPH_HASH_DOMAIN, content),
        }
    )


class SyntheticTrial(StrictModel):
    trial_key: Identifier
    status: TrialStatus
    configuration: dict[str, str]
    net_returns: tuple[Decimal | None, ...]
    return_statuses: tuple[ResearchReturnStatus, ...]
    return_timestamps_utc: tuple[datetime, ...]
    initiated_by: Identifier
    initiated_at_utc: datetime
    parent_trial_keys: tuple[Identifier, ...] = ()
    failure_reason: str | None = Field(default=None, max_length=1000)

    @field_validator("return_timestamps_utc")
    @classmethod
    def normalize_return_timestamps(cls, value: tuple[datetime, ...]) -> tuple[datetime, ...]:
        return tuple(_utc(item, "return_timestamps_utc") for item in value)

    @field_validator("initiated_at_utc")
    @classmethod
    def normalize_initiated_at(cls, value: datetime) -> datetime:
        return _utc(value, "initiated_at_utc")

    @model_validator(mode="after")
    def validate_status(self) -> Self:
        if not (
            len(self.return_timestamps_utc) == len(self.net_returns) == len(self.return_statuses)
        ):
            raise ValueError("trial returns require aligned values, statuses, and timestamps")
        if tuple(sorted(set(self.return_timestamps_utc))) != self.return_timestamps_utc:
            raise ValueError("trial return timestamps must be unique and chronological")
        for status, value in zip(self.return_statuses, self.net_returns, strict=True):
            if status is ResearchReturnStatus.MISSING:
                if value is not None:
                    raise ValueError("missing trial return status requires a null value")
            elif value is None or not value.is_finite():
                raise ValueError("non-missing trial return status requires a finite value")
            if status is ResearchReturnStatus.NO_TRADE and value != 0:
                raise ValueError("no-trade trial returns must be explicit zeros")
        if self.status is TrialStatus.COMPLETED:
            if len(self.net_returns) < 2:
                raise ValueError("completed trials require a return series")
        elif self.status in {TrialStatus.FAILED, TrialStatus.ABANDONED}:
            if self.net_returns or self.return_statuses or self.return_timestamps_utc:
                raise ValueError("failed and abandoned trials cannot fabricate returns")
            if not self.failure_reason:
                raise ValueError("failed and abandoned trials require a reason")
        else:
            if len(self.net_returns) < 2 or any(
                status is not ResearchReturnStatus.MISSING for status in self.return_statuses
            ):
                raise ValueError("no-return trials require a missing common-calendar series")
            if not self.failure_reason:
                raise ValueError("no-return trials require a reason")
        return self


class SyntheticEvaluationFixture(StrictModel):
    fixture_id: Identifier
    fixture_version: Literal["phase5-synthetic-evaluation-fixtures-v1"] = (
        "phase5-synthetic-evaluation-fixtures-v1"
    )
    fixture_sha256: SHA256
    random_seed: int = Field(ge=0)
    synthetic: Literal[True] = True
    no_real_performance_claimed: Literal[True] = True
    source_observation_expectations: tuple[SyntheticSourceObservationExpectation, ...] = Field(
        min_length=1
    )
    samples: tuple[SyntheticSample, ...] = Field(min_length=4)
    trials: tuple[SyntheticTrial, ...] = Field(min_length=2)
    warnings: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_source_observation_graph(self) -> Self:
        expectation_keys = tuple(
            (
                str(expectation.key.capability),
                str(expectation.key.normalized_observation_id),
            )
            for expectation in self.source_observation_expectations
        )
        if expectation_keys != tuple(sorted(expectation_keys)):
            raise ValueError("source-observation expectations must be canonically sorted")
        if len(expectation_keys) != len(set(expectation_keys)):
            raise ValueError("source-observation expectations must be unique")

        sample_ids = tuple(sample.sample_id for sample in self.samples)
        if sample_ids != tuple(sorted(sample_ids)) or len(sample_ids) != len(set(sample_ids)):
            raise ValueError("synthetic sample identities must be unique and canonically sorted")
        declared = set(expectation_keys)
        used: set[tuple[str, str]] = set()
        for sample in self.samples:
            keys = {
                (str(key.capability), str(key.normalized_observation_id))
                for key in sample.source_observation_keys
            }
            if not keys.issubset(declared):
                raise ValueError("every sample source observation must be declared by the fixture")
            used.update(keys)
        if used != declared:
            raise ValueError("every fixture source-observation expectation must be used")
        return self


class SampleSourceLineage(StrictModel):
    sample_id: Identifier
    sample_sha256: SHA256
    decision_time_utc: datetime
    feature_available_at_utc: datetime
    feature_derivation: SourceFeatureDerivation
    reference_price: Decimal = Field(gt=Decimal("0"))
    price_adjustment_basis: Literal["raw_unadjusted", "adjusted_for_corporate_action"] | None
    adjustment_action_as_of_utc: datetime | None
    fundamental_revision: FundamentalRevisionEvidence | None
    feature_dependency_ids: tuple[Identifier, ...]
    target_dependency_ids: tuple[Identifier, ...]
    universe_membership: UniverseMembershipEvidence | None
    membership_source_observation_key: SourceObservationKey
    dependency_graph: DerivedDependencyGraph
    synthetic_ledger_value_rule: Literal["deterministic-synthetic-research-ledger-input-v1"] = (
        "deterministic-synthetic-research-ledger-input-v1"
    )
    source_observation_refs: tuple[ResolvedSourceObservationRef, ...] = Field(min_length=1)

    @field_validator(
        "decision_time_utc",
        "feature_available_at_utc",
        "adjustment_action_as_of_utc",
    )
    @classmethod
    def normalize_leakage_audit_time(
        cls,
        value: datetime | None,
        info: object,
    ) -> datetime | None:
        if value is None:
            return None
        return _utc(value, getattr(info, "field_name", "sample leakage audit time"))

    @model_validator(mode="after")
    def validate_source_refs(self) -> Self:
        ref_keys = tuple(
            (
                str(ref.capability),
                str(ref.snapshot_id),
                str(ref.normalized_observation_id),
            )
            for ref in self.source_observation_refs
        )
        if ref_keys != tuple(sorted(ref_keys)):
            raise ValueError("resolved source-observation refs must be canonically sorted")
        if len(ref_keys) != len(set(ref_keys)):
            raise ValueError("resolved source-observation refs must be unique")
        derivation_ref_key = (
            str(self.feature_derivation.source_observation_key.capability),
            str(self.feature_derivation.source_observation_key.normalized_observation_id),
        )
        if derivation_ref_key not in {
            (str(ref.capability), str(ref.normalized_observation_id))
            for ref in self.source_observation_refs
        }:
            raise ValueError("feature derivation must resolve to sample source lineage")
        membership_ref_key = (
            str(self.membership_source_observation_key.capability),
            str(self.membership_source_observation_key.normalized_observation_id),
        )
        if (
            self.membership_source_observation_key.capability
            is not DataCapability.UNIVERSE_MEMBERSHIP
        ):
            raise ValueError("sample membership role must reference universe-membership evidence")
        if membership_ref_key not in {
            (str(ref.capability), str(ref.normalized_observation_id))
            for ref in self.source_observation_refs
        }:
            raise ValueError("membership source must resolve to sample source lineage")
        if self.dependency_graph.sample_id != self.sample_id:
            raise ValueError("sample dependency graph must match sample identity")
        for field_name, dependency_ids in (
            ("feature_dependency_ids", self.feature_dependency_ids),
            ("target_dependency_ids", self.target_dependency_ids),
        ):
            if dependency_ids != tuple(sorted(dependency_ids)):
                raise ValueError(f"sample lineage {field_name} must be canonically sorted")
            if len(dependency_ids) != len(set(dependency_ids)):
                raise ValueError(f"sample lineage {field_name} must be unique")
        return self

    @property
    def source_observation_keys(self) -> tuple[SourceObservationKey, ...]:
        """Recreate the exact capability/observation keys consumed by L01-L05."""

        return tuple(
            SourceObservationKey(
                capability=ref.capability,
                normalized_observation_id=ref.normalized_observation_id,
            )
            for ref in self.source_observation_refs
        )


class SnapshotEvidence(StrictModel):
    snapshot_id: UUID
    snapshot_sha256: SHA256
    capability: DataCapability
    provider_id: Identifier
    adapter_id: Identifier
    adapter_version: Identifier
    dataset_id: Identifier
    product_id: Identifier
    dataset_schema_versions: tuple[Identifier, ...]
    quality_status: Identifier
    fixture_set_version: Identifier
    as_of_utc: datetime

    @field_validator("as_of_utc")
    @classmethod
    def normalize_as_of(cls, value: datetime) -> datetime:
        return _utc(value, "as_of_utc")


class TrialRecord(StrictModel):
    trial_id: UUID
    ordinal: int = Field(ge=0)
    trial_sha256: SHA256
    trial_key: Identifier
    config_sha256: SHA256
    config_preimage: dict[str, object]
    configuration: dict[str, str]
    policy_sha256: SHA256
    strategy_family: CanonicalFamily
    selection_scope: Identifier
    signal_specification_sha256: SHA256
    feature_specification_sha256: SHA256
    label_specification_sha256: SHA256
    selection_policy_sha256: SHA256
    cost_policy_sha256: SHA256
    stress_policy_sha256: SHA256
    risk_policy_sha256: SHA256
    status: TrialStatus
    counts_toward_raw: Literal[True] = True
    effective_trial_contribution: Decimal = Field(ge=Decimal("0"))
    selection_metric: Identifier
    sharpe_convention: Identifier
    oos_return_state: Identifier
    net_returns: tuple[Decimal | None, ...]
    return_statuses: tuple[ResearchReturnStatus, ...]
    return_timestamps_utc: tuple[datetime, ...]
    initiated_by: Identifier
    initiated_at_utc: datetime
    parent_trial_ids: tuple[UUID, ...] = ()
    failure_reason: str | None = None

    @field_validator("return_timestamps_utc")
    @classmethod
    def normalize_trial_record_timestamps(cls, value: tuple[datetime, ...]) -> tuple[datetime, ...]:
        return tuple(_utc(item, "return_timestamps_utc") for item in value)

    @field_validator("initiated_at_utc")
    @classmethod
    def normalize_trial_initiated_at(cls, value: datetime) -> datetime:
        return _utc(value, "initiated_at_utc")

    @model_validator(mode="after")
    def validate_return_calendar(self) -> Self:
        if not (
            len(self.return_timestamps_utc) == len(self.net_returns) == len(self.return_statuses)
        ):
            raise ValueError("trial record values, statuses, and timestamps must have equal length")
        if tuple(sorted(set(self.return_timestamps_utc))) != self.return_timestamps_utc:
            raise ValueError("trial record timestamps must be unique and chronological")
        for status, value in zip(self.return_statuses, self.net_returns, strict=True):
            if status is ResearchReturnStatus.MISSING:
                if value is not None:
                    raise ValueError("missing trial record status requires a null value")
            elif value is None or not value.is_finite():
                raise ValueError("non-missing trial record status requires a finite value")
            if status is ResearchReturnStatus.NO_TRADE and value != 0:
                raise ValueError("no-trade trial record returns must be explicit zeros")
        if self.status is TrialStatus.COMPLETED and len(self.net_returns) < 2:
            raise ValueError("completed trial records require a return series")
        if self.status in {TrialStatus.FAILED, TrialStatus.ABANDONED} and (
            self.net_returns or self.return_statuses or self.return_timestamps_utc
        ):
            raise ValueError("failed and abandoned trial records cannot retain returns")
        if self.status is TrialStatus.NO_RETURN and (
            len(self.net_returns) < 2
            or any(status is not ResearchReturnStatus.MISSING for status in self.return_statuses)
        ):
            raise ValueError("no-return trial records require a missing common-calendar series")
        return self


class FoldRecord(StrictModel):
    fold_id: UUID
    ordinal: int = Field(ge=0)
    fold_sha256: SHA256
    fold_kind: FoldKind
    parent_fold_id: UUID | None
    train_start_utc: datetime
    train_end_utc: datetime
    test_start_utc: datetime
    test_end_utc: datetime
    train_sample_ids: tuple[Identifier, ...]
    purged_sample_ids: tuple[Identifier, ...]
    test_sample_ids: tuple[Identifier, ...]
    embargoed_sample_ids: tuple[Identifier, ...]
    embargo_duration_seconds: int = Field(ge=0)
    embargo_applied: bool

    @field_validator("train_start_utc", "train_end_utc", "test_start_utc", "test_end_utc")
    @classmethod
    def normalize_fold_times(cls, value: datetime, info: object) -> datetime:
        return _utc(value, getattr(info, "field_name", "fold time"))

    @model_validator(mode="after")
    def validate_parent_and_embargo(self) -> Self:
        if (self.fold_kind is FoldKind.INNER) != (self.parent_fold_id is not None):
            raise ValueError("only inner folds require a parent outer fold")
        if self.embargo_applied != (self.embargo_duration_seconds > 0):
            raise ValueError("embargo application must match its recorded duration")
        if not self.embargo_applied and self.embargoed_sample_ids:
            raise ValueError("non-applied embargo cannot contain embargoed rows")
        return self


class PreprocessingFitSampleValue(StrictModel):
    sample_id: Identifier
    sample_sha256: SHA256
    value: Decimal

    @field_validator("value")
    @classmethod
    def validate_fit_value(cls, value: Decimal) -> Decimal:
        if not value.is_finite():
            raise ValueError("preprocessing fit values must be finite")
        return value


def _preprocessing_statistics(
    values: tuple[PreprocessingFitSampleValue, ...],
    ddof: int,
) -> tuple[Decimal, Decimal]:
    if len(values) <= ddof:
        raise ValueError("preprocessing fit has insufficient train values")
    with localcontext() as context:
        context.prec = 60
        count = Decimal(len(values))
        mean = (sum((item.value for item in values), Decimal("0")) / count).quantize(
            PHASE5_DECIMAL_QUANTUM
        )
        variance = sum(
            ((item.value - mean) ** 2 for item in values),
            Decimal("0"),
        ) / Decimal(len(values) - ddof)
        standard_deviation = variance.sqrt().quantize(PHASE5_DECIMAL_QUANTUM)
    if standard_deviation <= 0:
        raise ValueError("preprocessing fit standard deviation must be positive")
    return mean, standard_deviation


class PreprocessingFitRecord(StrictModel):
    fit_id: UUID
    fit_sha256: SHA256
    fold_id: UUID
    fold_sha256: SHA256
    transformer_id: Identifier
    transformer_version: Literal["phase5-train-only-standardizer-v1"] = (
        "phase5-train-only-standardizer-v1"
    )
    train_sample_values: tuple[PreprocessingFitSampleValue, ...] = Field(min_length=2)
    train_sample_ids: tuple[Identifier, ...] = Field(min_length=1)
    train_sample_ids_canonical_json: str = Field(min_length=2)
    train_sample_ids_sha256: SHA256
    mean: Decimal
    standard_deviation: Decimal = Field(gt=Decimal("0"))
    ddof: Literal[1] = 1
    fit_preimage_canonical_json: str = Field(min_length=2)
    statistics_sha256: SHA256

    @classmethod
    def derive(
        cls,
        *,
        fold_id: UUID,
        fold_sha256: str,
        train_sample_values: tuple[PreprocessingFitSampleValue, ...],
    ) -> PreprocessingFitRecord:
        ordered = tuple(sorted(train_sample_values, key=lambda item: item.sample_id))
        train_ids = tuple(item.sample_id for item in ordered)
        train_ids_json = canonical_json_text(train_ids)
        train_ids_sha256 = domain_sha256(PHASE5_TRAIN_IDS_HASH_DOMAIN, train_ids)
        mean, standard_deviation = _preprocessing_statistics(ordered, 1)
        preimage = {
            "fold_id": fold_id,
            "fold_sha256": fold_sha256,
            "transformer_id": "train-only-standardizer",
            "transformer_version": PHASE5_PREPROCESSING_VERSION,
            "train_sample_values": ordered,
            "train_sample_ids": train_ids,
            "train_sample_ids_sha256": train_ids_sha256,
            "mean": mean,
            "standard_deviation": standard_deviation,
            "ddof": 1,
        }
        fit_sha256 = domain_sha256(PHASE5_TRAIN_ONLY_FIT_HASH_DOMAIN, preimage)
        statistics_sha256 = domain_sha256(
            PHASE5_FIT_HASH_DOMAIN,
            {
                "fit_sha256": fit_sha256,
                "mean": mean,
                "standard_deviation": standard_deviation,
                "ddof": 1,
            },
        )
        return cls.model_validate(
            {
                **preimage,
                "fit_id": identity(PHASE5_FIT_NAMESPACE, fit_sha256),
                "fit_sha256": fit_sha256,
                "train_sample_ids_canonical_json": train_ids_json,
                "fit_preimage_canonical_json": canonical_json_text(preimage),
                "statistics_sha256": statistics_sha256,
            }
        )

    @model_validator(mode="after")
    def validate_complete_fit_preimage(self) -> Self:
        ordered = tuple(sorted(self.train_sample_values, key=lambda item: item.sample_id))
        if self.train_sample_values != ordered:
            raise ValueError("preprocessing fit sample values must be canonically sorted")
        train_ids = tuple(item.sample_id for item in ordered)
        if len(train_ids) != len(set(train_ids)):
            raise ValueError("preprocessing fit sample identities must be unique")
        if self.train_sample_ids != train_ids:
            raise ValueError("preprocessing fit train ids must match its exact value preimage")
        if self.train_sample_ids_canonical_json != canonical_json_text(train_ids):
            raise ValueError("preprocessing train-id canonical JSON must match the exact ids")
        if self.train_sample_ids_sha256 != domain_sha256(PHASE5_TRAIN_IDS_HASH_DOMAIN, train_ids):
            raise ValueError("preprocessing train-id hash must match the exact ids")
        mean, standard_deviation = _preprocessing_statistics(ordered, self.ddof)
        if self.mean != mean or self.standard_deviation != standard_deviation:
            raise ValueError("preprocessing statistics must be recomputed from exact train values")
        preimage = {
            "fold_id": self.fold_id,
            "fold_sha256": self.fold_sha256,
            "transformer_id": self.transformer_id,
            "transformer_version": self.transformer_version,
            "train_sample_values": self.train_sample_values,
            "train_sample_ids": self.train_sample_ids,
            "train_sample_ids_sha256": self.train_sample_ids_sha256,
            "mean": self.mean,
            "standard_deviation": self.standard_deviation,
            "ddof": self.ddof,
        }
        if self.fit_preimage_canonical_json != canonical_json_text(preimage):
            raise ValueError("preprocessing fit canonical preimage must match every fit field")
        expected_fit_sha256 = domain_sha256(PHASE5_TRAIN_ONLY_FIT_HASH_DOMAIN, preimage)
        if self.fit_sha256 != expected_fit_sha256:
            raise ValueError("preprocessing fit hash must match its exact source-bound preimage")
        if self.fit_id != identity(PHASE5_FIT_NAMESPACE, expected_fit_sha256):
            raise ValueError("preprocessing fit identity must derive from its exact hash")
        expected_statistics_sha256 = domain_sha256(
            PHASE5_FIT_HASH_DOMAIN,
            {
                "fit_sha256": self.fit_sha256,
                "mean": self.mean,
                "standard_deviation": self.standard_deviation,
                "ddof": self.ddof,
            },
        )
        if self.statistics_sha256 != expected_statistics_sha256:
            raise ValueError("preprocessing statistics hash must match its exact preimage")
        return self


class OosLedgerEntry(StrictModel):
    ledger_entry_id: UUID
    ledger_entry_sha256: SHA256
    ordinal: int = Field(ge=0)
    trial_id: UUID
    fold_id: UUID
    sample_id: Identifier
    sample_sha256: SHA256
    source_observation_refs: tuple[ResolvedSourceObservationRef, ...] = Field(min_length=1)
    information_start_utc: datetime
    information_end_utc: datetime
    decision_time_utc: datetime
    label_t0_utc: datetime
    label_t1_utc: datetime
    predicted_value: Decimal
    gross_return: Decimal | None
    baseline_net_return: Decimal | None
    return_status: ResearchReturnStatus = ResearchReturnStatus.OBSERVED
    delisting_return_handled: Literal[True] = True

    @field_validator(
        "information_start_utc",
        "information_end_utc",
        "decision_time_utc",
        "label_t0_utc",
        "label_t1_utc",
    )
    @classmethod
    def normalize_ledger_times(cls, value: datetime, info: object) -> datetime:
        return _utc(value, getattr(info, "field_name", "ledger time"))

    @model_validator(mode="after")
    def validate_information_intervals(self) -> Self:
        if not (
            self.information_start_utc
            <= self.information_end_utc
            <= self.decision_time_utc
            <= self.label_t0_utc
            < self.label_t1_utc
        ):
            raise ValueError("OOS information and label intervals must be chronological")
        ref_keys = tuple(
            (
                str(ref.capability),
                str(ref.snapshot_id),
                str(ref.normalized_observation_id),
            )
            for ref in self.source_observation_refs
        )
        if ref_keys != tuple(sorted(ref_keys)) or len(ref_keys) != len(set(ref_keys)):
            raise ValueError("OOS source-observation refs must be unique and canonically sorted")
        if self.return_status is ResearchReturnStatus.MISSING:
            if self.gross_return is not None or self.baseline_net_return is not None:
                raise ValueError("missing OOS returns must remain null")
        else:
            if self.gross_return is None or self.baseline_net_return is None:
                raise ValueError("non-missing OOS returns require gross and baseline-net values")
            if not self.gross_return.is_finite() or not self.baseline_net_return.is_finite():
                raise ValueError("OOS return values must be finite")
        if self.return_status is ResearchReturnStatus.NO_TRADE and (
            self.gross_return != 0 or self.baseline_net_return != 0
        ):
            raise ValueError("no-trade OOS returns must be explicit zeros")
        return self


class CostLedgerEntry(StrictModel):
    cost_entry_id: UUID
    cost_entry_sha256: SHA256
    scenario: CostScenario
    ordinal: int = Field(ge=0)
    sample_id: Identifier
    allocation_input_sha256: SHA256
    return_status: ResearchReturnStatus
    requested_quantity: Decimal = Field(ge=Decimal("0"))
    filled_quantity: Decimal = Field(ge=Decimal("0"))
    rejected_quantity: Decimal = Field(ge=Decimal("0"))
    unfilled_quantity: Decimal = Field(ge=Decimal("0"))
    fill_status: Literal["filled", "capacity_rejected", "no_trade"]
    hard_to_borrow_available: bool
    gross_return: Decimal
    fee_cost: Decimal = Field(ge=Decimal("0"))
    spread_cost: Decimal = Field(ge=Decimal("0"))
    impact_cost: Decimal = Field(ge=Decimal("0"))
    latency_cost: Decimal = Field(ge=Decimal("0"))
    borrow_cost: Decimal = Field(ge=Decimal("0"))
    capacity_cost: Decimal = Field(ge=Decimal("0"))
    total_cost: Decimal = Field(ge=Decimal("0"))
    net_return: Decimal
    participation_rate: Decimal = Field(ge=Decimal("0"))
    capacity_breached: bool

    @model_validator(mode="after")
    def validate_fill_accounting(self) -> Self:
        if self.return_status is ResearchReturnStatus.MISSING:
            raise ValueError("missing returns cannot enter the cost ledger")
        if self.filled_quantity + self.unfilled_quantity != self.requested_quantity:
            raise ValueError("filled and unfilled quantities must reconcile to requested quantity")
        if self.rejected_quantity != self.unfilled_quantity:
            raise ValueError("rejected quantity must equal the modeled unfilled quantity")
        if self.return_status is ResearchReturnStatus.NO_TRADE:
            if self.fill_status != "no_trade" or self.capacity_breached:
                raise ValueError("no-trade cost rows require explicit no-trade fill state")
            if any(
                value != 0
                for value in (
                    self.requested_quantity,
                    self.filled_quantity,
                    self.rejected_quantity,
                    self.unfilled_quantity,
                    self.gross_return,
                    self.fee_cost,
                    self.spread_cost,
                    self.impact_cost,
                    self.latency_cost,
                    self.borrow_cost,
                    self.capacity_cost,
                    self.total_cost,
                    self.net_return,
                    self.participation_rate,
                )
            ):
                raise ValueError("no-trade cost rows must preserve exact zero economics")
            return self
        if self.requested_quantity <= 0:
            raise ValueError("traded cost rows require positive requested quantity")
        expected_status = "capacity_rejected" if self.capacity_breached else "filled"
        if self.fill_status != expected_status:
            raise ValueError("fill status must match capacity state")
        if self.capacity_breached != (self.unfilled_quantity > 0):
            raise ValueError("capacity state must match unfilled quantity")
        if self.fill_status == "capacity_rejected" and any(
            value != 0
            for value in (
                self.gross_return,
                self.fee_cost,
                self.spread_cost,
                self.impact_cost,
                self.latency_cost,
                self.borrow_cost,
                self.capacity_cost,
                self.total_cost,
                self.net_return,
            )
        ):
            raise ValueError("capacity-rejected rows cannot retain return or cost economics")
        if self.total_cost != (
            self.fee_cost
            + self.spread_cost
            + self.impact_cost
            + self.latency_cost
            + self.borrow_cost
            + self.capacity_cost
        ):
            raise ValueError("component costs must sum exactly to total cost")
        if self.net_return != self.gross_return - self.total_cost:
            raise ValueError("net return must equal gross return minus total cost")
        return self


class MetricRecord(StrictModel):
    metric_id: Identifier
    formula_version: Identifier
    value: Decimal
    units: Identifier
    frequency: Identifier
    annualization_factor: int = Field(ge=1)
    timezone: Literal["UTC"] = "UTC"
    calendar: Identifier
    population: str = Field(min_length=1, max_length=1000)
    exclusions: tuple[str, ...]
    denominator: str = Field(min_length=1, max_length=1000)
    inputs: dict[str, str | int | Decimal]


class GateResult(StrictModel):
    gate_result_id: UUID
    ordinal: int = Field(ge=0)
    gate_result_sha256: SHA256
    config_hash: SHA256
    gate_code: GateCode
    outcome: GateOutcome
    reason_codes: tuple[Identifier, ...]
    inputs: dict[str, str | int | Decimal | bool]
    thresholds: dict[str, str | int | Decimal | bool]
    results: dict[str, str | int | Decimal | bool]
    warnings: tuple[str, ...]

    @model_validator(mode="after")
    def validate_gate_identity(self) -> Self:
        payload = self.model_dump(
            mode="python",
            exclude={"gate_result_id", "gate_result_sha256"},
        )
        expected = domain_sha256(PHASE5_GATE_HASH_DOMAIN, payload)
        if self.gate_result_sha256 != expected:
            raise ValueError("gate-result hash must match its complete preimage")
        if self.gate_result_id != identity(PHASE5_GATE_NAMESPACE, expected):
            raise ValueError("gate-result identity must derive from its hash")
        return self


class EvaluationReport(StrictModel):
    artifact_id: UUID
    artifact_type: Literal["synthetic_research_evaluation"] = "synthetic_research_evaluation"
    artifact_schema_version: Literal["phase5-evaluation-report-v1"] = "phase5-evaluation-report-v1"
    artifact_sha256: SHA256
    request_fingerprint_sha256: SHA256
    request_fingerprint_version: Literal["phase5-evaluation-request-v1"] = (
        "phase5-evaluation-request-v1"
    )
    config_hash: SHA256
    evaluation_policy_id: UUID
    evaluation_policy_version: int = Field(ge=1)
    evaluation_policy_sha256: SHA256
    mapping_id: UUID
    mapping_version: int = Field(ge=1)
    mapping_input_sha256: SHA256
    snapshot_bundle_sha256: SHA256
    data_snapshots: tuple[SnapshotEvidence, ...] = Field(min_length=1)
    source_observations: tuple[ResolvedSourceObservation, ...] = Field(min_length=1)
    sample_lineage_sha256: SHA256
    sample_lineage: tuple[SampleSourceLineage, ...] = Field(min_length=4)
    provider_source_versions: tuple[Identifier, ...] = Field(min_length=1)
    code_version_git_sha: GitSHA
    random_seed: int = Field(ge=0)
    raw_trial_count: int = Field(ge=1)
    effective_trial_count: Decimal = Field(gt=Decimal("1"))
    effective_trial_method: Literal["bailey-average-correlation-interpolation-v1"] = (
        "bailey-average-correlation-interpolation-v1"
    )
    created_at_utc: datetime
    decision_time_utc: datetime
    parent_artifact_ids: tuple[UUID, ...]
    fixture_id: Identifier
    fixture_version: Literal["phase5-synthetic-evaluation-fixtures-v1"] = (
        "phase5-synthetic-evaluation-fixtures-v1"
    )
    fixture_sha256: SHA256
    synthetic: Literal[True] = True
    no_real_performance_claimed: Literal[True] = True
    disclaimer: Literal["Synthetic research only; no real performance or investment advice."] = (
        "Synthetic research only; no real performance or investment advice."
    )
    promotion_state: PromotionState
    pass_research_is_not_paper_approval: Literal[True] = True
    feature_specification: FeatureSpecification
    label_specification: LabelSpecification
    trials: tuple[TrialRecord, ...] = Field(min_length=1)
    folds: tuple[FoldRecord, ...] = Field(min_length=1)
    preprocessing_fits: tuple[PreprocessingFitRecord, ...] = Field(min_length=1)
    oos_ledger: tuple[OosLedgerEntry, ...] = Field(min_length=1)
    cost_ledger: tuple[CostLedgerEntry, ...] = Field(min_length=1)
    metrics: tuple[MetricRecord, ...] = Field(min_length=1)
    gates: tuple[GateResult, ...] = Field(min_length=12)
    warnings: tuple[str, ...]
    reason_codes: tuple[Identifier, ...]

    @field_validator("created_at_utc", "decision_time_utc")
    @classmethod
    def normalize_report_times(cls, value: datetime, info: object) -> datetime:
        return _utc(value, getattr(info, "field_name", "report time"))

    @model_validator(mode="after")
    def validate_complete_report(self) -> Self:
        if self.raw_trial_count != len(self.trials):
            raise ValueError("raw trial count must include every persisted trial")
        if {item.gate_code for item in self.gates} != set(GateCode):
            raise ValueError("evaluation report must contain every required gate")
        capabilities = tuple(sorted((item.capability for item in self.data_snapshots), key=str))
        if capabilities != tuple(item.capability for item in self.data_snapshots):
            raise ValueError("snapshot evidence must be ordered by capability")
        source_refs = tuple(item.reference() for item in self.source_observations)
        source_ref_keys = tuple(
            (
                str(ref.capability),
                str(ref.snapshot_id),
                str(ref.normalized_observation_id),
            )
            for ref in source_refs
        )
        if source_ref_keys != tuple(sorted(source_ref_keys)):
            raise ValueError("resolved source observations must be canonically sorted")
        if len(source_ref_keys) != len(set(source_ref_keys)):
            raise ValueError("resolved source observations must be unique")
        snapshot_bindings = {
            (item.snapshot_id, item.snapshot_sha256) for item in self.data_snapshots
        }
        if any(
            (ref.snapshot_id, ref.snapshot_sha256) not in snapshot_bindings for ref in source_refs
        ):
            raise ValueError("source observations must belong to a report snapshot")

        lineage_ids = tuple(item.sample_id for item in self.sample_lineage)
        if lineage_ids != tuple(sorted(lineage_ids)) or len(lineage_ids) != len(set(lineage_ids)):
            raise ValueError("sample lineage must be unique and canonically sorted")
        if self.sample_lineage_sha256 != domain_sha256(
            PHASE5_SAMPLE_LINEAGE_HASH_DOMAIN,
            self.sample_lineage,
        ):
            raise ValueError("sample lineage hash must match the complete lineage graph")
        source_ref_key_set = set(source_ref_keys)
        used_source_refs: set[tuple[str, str, str]] = set()
        lineage_by_sample = {item.sample_id: item for item in self.sample_lineage}
        for lineage in self.sample_lineage:
            lineage_ref_keys = {
                (
                    str(ref.capability),
                    str(ref.snapshot_id),
                    str(ref.normalized_observation_id),
                )
                for ref in lineage.source_observation_refs
            }
            if not lineage_ref_keys.issubset(source_ref_key_set):
                raise ValueError("sample lineage cannot reference an unknown source observation")
            used_source_refs.update(lineage_ref_keys)
            derivation = lineage.feature_derivation
            source = next(
                (
                    item
                    for item in self.source_observations
                    if item.key == derivation.source_observation_key
                ),
                None,
            )
            if source is None:
                raise ValueError("sample feature derivation source must be present in the report")
            source_value = getattr(
                source.normalized_observation.payload,
                derivation.source_payload_field,
                None,
            )
            if (
                not isinstance(source_value, Decimal)
                or source_value * derivation.multiplier != derivation.derived_feature_value
            ):
                raise ValueError(
                    "sample feature derivation must reproduce from persisted source evidence"
                )
            if lineage.dependency_graph != derive_dependency_graph(
                lineage,
                self.feature_specification,
                self.label_specification,
            ):
                raise ValueError(
                    "sample dependency graph must derive from source lineage and "
                    "frozen specifications"
                )
        if used_source_refs != source_ref_key_set:
            raise ValueError("every resolved source observation must be used by sample lineage")
        for entry in self.oos_ledger:
            entry_lineage = lineage_by_sample.get(entry.sample_id)
            if entry_lineage is None:
                raise ValueError("every OOS row must reference complete sample lineage")
            if (
                entry.sample_sha256 != entry_lineage.sample_sha256
                or entry.source_observation_refs != entry_lineage.source_observation_refs
                or entry.decision_time_utc != entry_lineage.decision_time_utc
            ):
                raise ValueError("OOS row lineage must exactly match its synthetic sample")

        for fit in self.preprocessing_fits:
            for fit_value in fit.train_sample_values:
                fit_lineage = lineage_by_sample.get(fit_value.sample_id)
                if fit_lineage is None:
                    raise ValueError("preprocessing fit references unknown sample lineage")
                if (
                    fit_value.sample_sha256 != fit_lineage.sample_sha256
                    or fit_value.value != fit_lineage.feature_derivation.derived_feature_value
                ):
                    raise ValueError(
                        "preprocessing fit values must match source-bound sample lineage"
                    )

        gates_by_code = {gate.gate_code: gate for gate in self.gates}
        leakage_gate = gates_by_code[GateCode.LEAKAGE]
        serialized_leakage = leakage_gate.inputs.get("per_check_evidence_json")
        if not isinstance(serialized_leakage, str):
            raise ValueError("LEAKAGE gate must persist canonical typed evidence")
        try:
            raw_findings = json.loads(serialized_leakage)
            typed_leakage = LeakageGateEvidence.model_validate({"findings": raw_findings})
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError("LEAKAGE gate evidence is invalid") from exc
        if serialized_leakage != canonical_json_text(typed_leakage.findings):
            raise ValueError("LEAKAGE gate evidence must use canonical JSON")
        from fable5_backtester.leakage import evaluate_leakage_context

        expected_context_findings = tuple(
            LeakageFindingEvidence.model_validate(
                {
                    "code": finding.code,
                    "blocked": finding.blocked,
                    "affected_sample_ids": finding.affected_sample_ids,
                    "evidence_rule": finding.evidence_rule,
                    "evidence_records": finding.evidence_records,
                }
            )
            for finding in evaluate_leakage_context(
                self.sample_lineage,
                self.source_observations,
                feature_specification=self.feature_specification,
                label_specification=self.label_specification,
            )
        )
        if typed_leakage.findings[:5] != expected_context_findings:
            raise ValueError(
                "LEAKAGE L01-L05 evidence must reproduce from exact report source lineage"
            )
        blocking_findings = tuple(finding for finding in typed_leakage.findings if finding.blocked)
        expected_leakage_reasons = tuple(
            f"leakage_{finding.code.lower()}" for finding in blocking_findings
        )
        expected_leakage_outcome = GateOutcome.FAIL if blocking_findings else GateOutcome.PASS
        blocking_check_rate = _gate_decimal(
            leakage_gate.results.get("blocking_check_rate"),
            "LEAKAGE blocking_check_rate",
        )
        if (
            leakage_gate.outcome is not expected_leakage_outcome
            or leakage_gate.reason_codes != expected_leakage_reasons
            or leakage_gate.inputs.get("check_count") != len(LeakageCode)
            or leakage_gate.results.get("blocking_check_count") != len(blocking_findings)
            or blocking_check_rate != Decimal(len(blocking_findings)) / Decimal(len(LeakageCode))
        ):
            raise ValueError("LEAKAGE gate outcome must reconcile with exact typed evidence")

        l06 = next(finding for finding in typed_leakage.findings if finding.code is LeakageCode.L06)
        l06_records = tuple(
            record for record in l06.evidence_records if isinstance(record, L06TrainOnlyFitEvidence)
        )
        fits_by_fold: dict[UUID, list[PreprocessingFitRecord]] = {}
        for fit in self.preprocessing_fits:
            fits_by_fold.setdefault(fit.fold_id, []).append(fit)
        records_by_fold = {record.fold_id: record for record in l06_records}
        if len(records_by_fold) != len(l06_records):
            raise ValueError("L06 evidence must contain one record per known or unknown fold")
        for fold in self.folds:
            record = records_by_fold.get(fold.fold_id)
            if record is None:
                raise ValueError("L06 evidence is missing a persisted fold")
            fold_fits = fits_by_fold.get(fold.fold_id, [])
            observed = tuple(
                sorted({sample_id for fit in fold_fits for sample_id in fit.train_sample_ids})
            )
            disallowed = tuple(
                sorted(
                    set(observed)
                    & set(
                        (*fold.test_sample_ids, *fold.purged_sample_ids, *fold.embargoed_sample_ids)
                    )
                )
            )
            if (
                record.fold_sha256 != fold.fold_sha256
                or record.expected_train_sample_ids != tuple(sorted(fold.train_sample_ids))
                or record.observed_fit_train_sample_ids != observed
                or record.disallowed_train_sample_ids != disallowed
                or record.fit_ids
                != tuple(fit.fit_id for fit in sorted(fold_fits, key=lambda item: str(item.fit_id)))
                or record.fit_sha256s
                != tuple(
                    fit.fit_sha256 for fit in sorted(fold_fits, key=lambda item: str(item.fit_id))
                )
            ):
                raise ValueError("L06 evidence must reconcile with fold and fit artifacts")
        unknown_fit_fold_ids = set(fits_by_fold) - {fold.fold_id for fold in self.folds}
        if unknown_fit_fold_ids != {
            record.fold_id
            for record in l06_records
            if record.fold_id is not None and record.fold_sha256 is None
        }:
            raise ValueError("L06 evidence must capture every fit referencing an unknown fold")

        preprocessing_gate = gates_by_code[GateCode.PREPROCESSING]
        expected_preprocessing_outcome = GateOutcome.FAIL if l06.blocked else GateOutcome.PASS
        expected_preprocessing_reasons = (
            ("preprocessing_train_only_violation",) if l06.blocked else ()
        )
        if (
            preprocessing_gate.outcome is not expected_preprocessing_outcome
            or preprocessing_gate.reason_codes != expected_preprocessing_reasons
            or preprocessing_gate.inputs.get("fit_count") != len(self.preprocessing_fits)
            or preprocessing_gate.results.get("all_fit_ids_train_only") is not (not l06.blocked)
        ):
            raise ValueError("PREPROCESSING gate must derive from exact L06 evidence")
        trials_by_id = {trial.trial_id: trial for trial in self.trials}
        oos_by_sample = {entry.sample_id: entry for entry in self.oos_ledger}
        if len(oos_by_sample) != len(self.oos_ledger):
            raise ValueError("OOS sample identities must be unique")
        for entry in self.oos_ledger:
            trial = trials_by_id.get(entry.trial_id)
            if trial is None:
                raise ValueError("every OOS row must reference a persisted trial")
            try:
                trial_index = trial.return_timestamps_utc.index(entry.decision_time_utc)
            except ValueError as exc:
                raise ValueError(
                    "OOS decision time must exist on the selected trial calendar"
                ) from exc
            if (
                trial.return_statuses[trial_index] is not entry.return_status
                or trial.net_returns[trial_index] != entry.baseline_net_return
            ):
                raise ValueError("selected trial return status and value must match the OOS row")
        cost_keys = {(entry.sample_id, entry.scenario) for entry in self.cost_ledger}
        expected_cost_keys = {
            (entry.sample_id, scenario) for entry in self.oos_ledger for scenario in CostScenario
        }
        if cost_keys != expected_cost_keys or len(cost_keys) != len(self.cost_ledger):
            raise ValueError("cost ledger must contain every OOS sample and scenario exactly once")
        for cost in self.cost_ledger:
            oos_entry = oos_by_sample.get(cost.sample_id)
            if oos_entry is None or cost.return_status is not oos_entry.return_status:
                raise ValueError("cost return status must match its OOS row")
            if cost.scenario is CostScenario.BASELINE:
                if cost.net_return != oos_entry.baseline_net_return:
                    raise ValueError("baseline cost return must match the OOS baseline-net return")
                if cost.fill_status == "filled" and cost.gross_return != oos_entry.gross_return:
                    raise ValueError("filled baseline cost gross return must match the OOS row")
        if self.promotion_state is PromotionState.PASS_RESEARCH and any(
            gate.outcome is not GateOutcome.PASS for gate in self.gates
        ):
            raise ValueError("PASS_RESEARCH requires every gate to pass")
        report_payload = self.model_dump(
            mode="python",
            exclude=set(PHASE5_REPORT_HASH_EXCLUDED_FIELDS),
        )
        expected_artifact_sha256 = domain_sha256(PHASE5_ARTIFACT_HASH_DOMAIN, report_payload)
        if self.artifact_sha256 != expected_artifact_sha256:
            raise ValueError("evaluation report hash must match its complete artifact preimage")
        if self.artifact_id != identity(PHASE5_ARTIFACT_NAMESPACE, expected_artifact_sha256):
            raise ValueError("evaluation report identity must derive from its artifact hash")
        return self


class EvaluationReportSummary(StrictModel):
    artifact_id: UUID
    artifact_sha256: SHA256
    fixture_id: Identifier
    promotion_state: PromotionState
    synthetic: Literal[True] = True
    no_real_performance_claimed: Literal[True] = True
    created_at_utc: datetime
    warning_count: int = Field(ge=0)
    reason_codes: tuple[Identifier, ...]

    @field_validator("created_at_utc")
    @classmethod
    def normalize_summary_time(cls, value: datetime) -> datetime:
        return _utc(value, "created_at_utc")


class EvaluationBlockedResult(StrictModel):
    status: Literal["blocked"] = "blocked"
    promotion_state: Literal[
        PromotionState.BLOCKED_MISSING_POLICY,
        PromotionState.BLOCKED_UNCOMPUTABLE,
    ]
    reason_codes: tuple[Identifier, ...] = Field(min_length=1)
    sanitized_message: str = Field(min_length=1, max_length=500)


__all__ = [name for name in globals() if not name.startswith("_")]
