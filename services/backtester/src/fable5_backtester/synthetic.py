"""Registered deterministic Phase 5 policy and synthetic evaluation fixture."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from fable5_data.contracts import (
    ConstituentDisposition,
    DataCapability,
    OhlcvBarPayload,
    UniverseMembershipPayload,
)
from fable5_data.synthetic import SyntheticPointInTimeAdapter
from fable5_mapping.models import CanonicalFamily

from fable5_backtester.canonical import (
    PHASE5_FEATURE_HASH_DOMAIN,
    PHASE5_FEATURE_NAMESPACE,
    PHASE5_FIXTURE_HASH_DOMAIN,
    PHASE5_LABEL_HASH_DOMAIN,
    PHASE5_LABEL_NAMESPACE,
    PHASE5_POLICY_HASH_DOMAIN,
    canonical_json_text,
    domain_sha256,
    identity,
)
from fable5_backtester.contracts import (
    PHASE5_SOURCE_FEATURE_DERIVATION_FORMULA,
    PHASE5_SOURCE_FEATURE_DERIVATION_HASH_DOMAIN,
    PHASE5_SYNTHETIC_LEDGER_VALUE_RULE,
    AuditPolicy,
    CostPolicy,
    CostScenario,
    FeatureSpecification,
    FrozenEvaluationPolicy,
    LabelSpecification,
    MissingReturnPolicy,
    NoTradeReturnPolicy,
    RegimePolicy,
    ResearchReturnStatus,
    RiskPolicy,
    SampleAdequacyPolicy,
    SelectionPolicy,
    SignalSpecification,
    SourceFeatureDerivation,
    SourceObservationKey,
    SourceValueBinding,
    StressPolicy,
    SyntheticEvaluationFixture,
    SyntheticSample,
    SyntheticSourceObservationExpectation,
    SyntheticTrial,
    TrainMode,
    TrialStatus,
    UniverseMembershipEvidence,
    WalkForwardPolicy,
    label_dependency_id,
    source_feature_dependency_id,
)
from fable5_backtester.costs import build_cost_ledger

SYNTHETIC_POLICY_ID = UUID("b4e2146e-f1da-5c15-ada2-01bfd61ead9e")
SYNTHETIC_POLICY_VERSION = 1
SYNTHETIC_FIXTURE_ID = "phase5-deterministic-research-ledger-v1"


def _feature_specification() -> FeatureSpecification:
    content = {
        "schema_version": "phase5-feature-specification-v1",
        "version": "phase5-synthetic-feature-contract-v1",
        "formula_id": "source-decimal-times-frozen-multiplier-v1",
        "source_fields": ("ohlcv.open",),
        "lookback_rule": "exact frozen Phase 4 observation referenced by each synthetic sample",
        "availability_rule": "every input available_at must be at or before decision_time",
        "source_observation_binding_rule": ("phase5-exact-snapshot-constituent-value-v1"),
        "preprocessing_rules": ("phase5-train-only-standardizer-v1",),
        "imputation_policy": "block-missing-feature-no-imputation-v1",
        "encoding_policy": "numeric-identity-no-categorical-encoding-v1",
        "feature_selection_policy": "frozen-feature-list-no-selection-v1",
        "hyperparameter_policy": "nested-train-only-frozen-grid-v1",
    }
    digest = domain_sha256(PHASE5_FEATURE_HASH_DOMAIN, content)
    return FeatureSpecification.model_validate(
        {
            **content,
            "feature_specification_id": identity(PHASE5_FEATURE_NAMESPACE, digest),
            "content_sha256": digest,
        }
    )


def _label_specification() -> LabelSpecification:
    content = {
        "schema_version": "phase5-label-specification-v1",
        "version": "phase5-synthetic-label-contract-v1",
        "formula_id": "synthetic-forward-two-session-return-v1",
        "forecast_horizon": "two UTC decision sessions",
        "information_interval_rule": "closed interval from decision time through horizon end",
        "missing_return_policy": "block_missing_return_v1",
        "no_trade_return_policy": "explicit_zero_research_observation_v1",
        "delisting_return_policy": "require_explicit_delisting_outcome_v1",
    }
    digest = domain_sha256(PHASE5_LABEL_HASH_DOMAIN, content)
    return LabelSpecification.model_validate(
        {
            **content,
            "label_specification_id": identity(PHASE5_LABEL_NAMESPACE, digest),
            "content_sha256": digest,
        }
    )


def build_synthetic_policy() -> FrozenEvaluationPolicy:
    """Return the only registered Phase 5 policy; its thresholds are test-fixture values."""

    feature = _feature_specification()
    label = _label_specification()
    policy_content = {
        "policy_id": SYNTHETIC_POLICY_ID,
        "policy_version": SYNTHETIC_POLICY_VERSION,
        "schema_version": "phase5-evaluation-policy-v1",
        "strategy_family": CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING,
        "selection_scope": "synthetic_family_a_fixture_only",
        "created_at_utc": datetime(2026, 1, 1, tzinfo=UTC),
        "approved_by": "synthetic-fixture-policy-owner",
        "synthetic_fixture_policy": True,
        "signal_specification": SignalSpecification(
            specification_id="phase5-synthetic-score-specification",
            version="v1",
            definition=(
                "A deterministic fixture score supplied only to exercise evaluation mechanics; "
                "it has no action or execution semantics."
            ),
            deterministic_formula_id="synthetic-score-identity-v1",
            forecast_horizon="two UTC decision sessions",
            executable_decision_lag="one hour after all source availability timestamps",
            universe_eligibility_rule=(
                "only identifiers present in the authorized point-in-time synthetic universe"
            ),
            universe_exclusion_rule=(
                "exclude identifiers without delisting-aware outcomes or required PIT fields"
            ),
            rebalance_rule="one deterministic research observation per UTC decision session",
            holding_rule="two-session label interval with no execution semantics",
            overlap_rule="overlapping labels are purged from every applicable training fold",
        ),
        "required_snapshot_capabilities": (
            DataCapability.OHLCV,
            DataCapability.UNIVERSE_MEMBERSHIP,
        ),
        "feature_specification": feature,
        "label_specification": label,
        "walk_forward": WalkForwardPolicy(
            decision_calendar="synthetic-utc-daily-calendar-v1",
            outer_fold_count=2,
            inner_fold_count=2,
            minimum_train_observations=6,
            outer_test_observations=4,
            inner_test_observations=1,
            rolling_train_observations=None,
            train_mode=TrainMode.EXPANDING_PAST_ONLY,
            purge_rule="label_interval_intersection_v1",
            embargo_rule=None,
            embargo_seconds=None,
            final_confirmation_start_utc=datetime(2020, 2, 10, tzinfo=UTC),
            final_confirmation_end_utc=datetime(2020, 2, 12, tzinfo=UTC),
            final_confirmation_opening_rule="single_use_future_interval_v1",
        ),
        "sample_adequacy": SampleAdequacyPolicy(
            min_oos_observations=8,
            min_independent_events=8,
            min_synchronized_trials=4,
            missing_return_policy=MissingReturnPolicy.BLOCK,
            no_trade_return_policy=NoTradeReturnPolicy.EXPLICIT_ZERO,
        ),
        "selection": SelectionPolicy(
            raw_trial_definition="all_selection_influencing_configurations_v1",
            dsr_min_probability=Decimal("0.50"),
            cscv_block_count=4,
            pbo_max=Decimal("0.25"),
            return_frequency="synthetic_daily",
            annualization_factor=250,
            serial_correlation_method="lag1-effective-sample-size-sensitivity-v1",
        ),
        "costs": CostPolicy(
            fee_schedule_id="synthetic-fee-schedule-v1",
            fee_schedule_effective_date="2026-01-01",
            spread_source="synthetic-quote-half-spread-v1",
            spread_fallback_rule="block_when_missing-v1",
            impact_model_id="square-root-impact-research-proxy",
            impact_model_version="phase5-square-root-impact-v1",
            impact_calibration_id="synthetic-calibration-v1",
            latency_rule="synthetic-delay-cost-v1",
            slippage_model_id="component-separated-slippage-v1",
            borrow_source="synthetic-borrow-state-v1",
            hard_to_borrow_rule="unavailable-when-missing-v1",
            baseline_max_participation=Decimal("0.05"),
            capacity_rule="research-allocation-over-adv-v1",
        ),
        "stress": StressPolicy(
            all_cost_multiplier=Decimal("2"),
            spread_multiplier=Decimal("2.5"),
            volatility_multiplier=Decimal("1.5"),
            adv_multiplier=Decimal("0.5"),
            impact_coefficient_multiplier=Decimal("1.5"),
            latency_multiplier=Decimal("2"),
            borrow_multiplier=Decimal("2"),
            min_stressed_net_pnl=Decimal("0.000001"),
            min_stressed_annual_return=Decimal("0.000001"),
            min_stressed_sharpe=Decimal("0.000001"),
            max_stressed_drawdown=Decimal("0.25"),
            max_capacity_breach_rate=Decimal("0"),
        ),
        "regimes": RegimePolicy(
            volatility_definition="synthetic-observable-volatility-v1",
            volatility_cut=Decimal("0.02"),
            rate_definition="synthetic-vintage-rate-direction-v1",
            rate_cut=Decimal("0"),
            crisis_windows=("synthetic-stress-window-v1",),
            dependency_rule="all-predeclared-regimes-reported-v1",
        ),
        "risk": RiskPolicy(
            max_single_observation_exposure=Decimal("0.10"),
            max_gross_exposure=Decimal("1.00"),
            max_net_exposure=Decimal("1.00"),
            max_sector_exposure=Decimal("0.50"),
            max_turnover=Decimal("1.00"),
            max_volatility=Decimal("0.10"),
            max_loss=Decimal("0.10"),
            max_drawdown=Decimal("0.25"),
        ),
        "audit": AuditPolicy(
            required_fields=(
                "artifact_id",
                "artifact_type",
                "config_hash",
                "evaluation_policy_id",
                "evaluation_policy_hash",
                "data_snapshot_id",
                "code_version_git_sha",
                "random_seed",
                "raw_trial_count",
                "effective_trial_count",
                "created_at_utc",
                "parent_artifact_ids",
            ),
            numeric_metadata_rule="phase5-complete-metric-metadata-v1",
            append_only_rule="phase5-immutable-artifact-graph-v1",
        ),
    }
    digest = domain_sha256(PHASE5_POLICY_HASH_DOMAIN, policy_content)
    return FrozenEvaluationPolicy.model_validate(
        {
            **policy_content,
            "policy_sha256": digest,
            "policy_canonical_json": canonical_json_text(policy_content),
        }
    )


def _source_observation_expectations() -> tuple[SyntheticSourceObservationExpectation, ...]:
    adapter = SyntheticPointInTimeAdapter()
    ohlcv_batch = adapter.fetch(DataCapability.OHLCV).batch
    membership_batch = adapter.fetch(DataCapability.UNIVERSE_MEMBERSHIP).batch
    if len(ohlcv_batch.normalized_observations) != 1:
        raise ValueError("registered Phase 5 fixture requires exactly one Phase 4 OHLCV source")
    observation = ohlcv_batch.normalized_observations[0]
    membership_matches = tuple(
        item
        for item in membership_batch.normalized_observations
        if item.source_record_id == "synthetic-membership-2019"
    )
    if len(membership_matches) != 1:
        raise ValueError("registered Phase 5 fixture requires exact historical membership source")
    membership = membership_matches[0]
    key = SourceObservationKey(
        capability=DataCapability.OHLCV,
        normalized_observation_id=observation.normalized_observation_id,
    )
    membership_key = SourceObservationKey(
        capability=DataCapability.UNIVERSE_MEMBERSHIP,
        normalized_observation_id=membership.normalized_observation_id,
    )
    return tuple(
        sorted(
            (
                SyntheticSourceObservationExpectation(
                    key=key,
                    normalized_observation=observation,
                    required_disposition=ConstituentDisposition.INCLUDED_AS_OF,
                    value_bindings=(
                        SourceValueBinding(
                            source_payload_field="open",
                            sample_field="reference_price",
                            multiplier=Decimal("1"),
                        ),
                        SourceValueBinding(
                            source_payload_field="volume",
                            sample_field="daily_adv_units",
                            multiplier=Decimal("0.1"),
                        ),
                    ),
                ),
                SyntheticSourceObservationExpectation(
                    key=membership_key,
                    normalized_observation=membership,
                    required_disposition=ConstituentDisposition.INCLUDED_AS_OF,
                    value_bindings=(),
                ),
            ),
            key=lambda item: (
                str(item.key.capability),
                str(item.key.normalized_observation_id),
            ),
        )
    )


def _samples(
    source_expectations: tuple[SyntheticSourceObservationExpectation, ...],
    policy: FrozenEvaluationPolicy,
) -> tuple[SyntheticSample, ...]:
    gross_returns = (
        "0.0058",
        "0.0061",
        "0.0059",
        "0.0063",
        "0.0060",
        "0.0064",
        "0.0060",
        "0.0065",
        "0.0055",
        "0.0070",
        "0.0062",
        "0.0068",
        "0.0080",
        "-0.0010",
        "0.0090",
        "0.0070",
        "0.0100",
        "-0.0005",
        "0.0080",
        "0.0070",
    )
    samples: list[SyntheticSample] = []
    origin = datetime(2020, 1, 21, 16, tzinfo=UTC)
    expectations_by_capability = {item.key.capability: item for item in source_expectations}
    source_expectation = expectations_by_capability[DataCapability.OHLCV]
    membership_expectation = expectations_by_capability[DataCapability.UNIVERSE_MEMBERSHIP]
    source_key = source_expectation.key
    membership_key = membership_expectation.key
    source_payload = source_expectation.normalized_observation.payload
    membership_payload = membership_expectation.normalized_observation.payload
    if not isinstance(source_payload, OhlcvBarPayload):
        raise ValueError("registered Phase 5 feature source must be an OHLCV bar")
    if not isinstance(membership_payload, UniverseMembershipPayload):
        raise ValueError("registered Phase 5 membership source must be universe membership")
    source_open = source_payload.open
    for index, raw_return in enumerate(gross_returns):
        decision = origin + timedelta(days=index)
        feature_value = Decimal(index + 1) / Decimal("10")
        derivation_content = {
            "schema_version": "phase5-source-feature-derivation-v1",
            "formula_id": PHASE5_SOURCE_FEATURE_DERIVATION_FORMULA,
            "source_observation_key": source_key,
            "source_payload_field": "open",
            "multiplier": feature_value / source_open,
            "derived_feature_value": feature_value,
        }
        samples.append(
            SyntheticSample(
                sample_id=f"synthetic-sample-{index + 1:02d}",
                source_observation_keys=tuple(
                    sorted(
                        (source_key, membership_key),
                        key=lambda item: (
                            str(item.capability),
                            str(item.normalized_observation_id),
                        ),
                    )
                ),
                feature_derivation=SourceFeatureDerivation.model_validate(
                    {
                        **derivation_content,
                        "derivation_sha256": domain_sha256(
                            PHASE5_SOURCE_FEATURE_DERIVATION_HASH_DOMAIN,
                            derivation_content,
                        ),
                    }
                ),
                synthetic_ledger_value_rule=PHASE5_SYNTHETIC_LEDGER_VALUE_RULE,
                decision_time_utc=decision,
                feature_available_at_utc=decision - timedelta(hours=1),
                label_t0_utc=decision,
                label_t1_utc=decision + timedelta(days=2),
                feature_value=feature_value,
                predicted_value=Decimal(index + 2) / Decimal("100"),
                gross_return=Decimal(raw_return),
                research_allocation_units=Decimal("100"),
                reference_price=Decimal("50"),
                daily_adv_units=Decimal("100000"),
                daily_volatility=(Decimal("0.015") if index < 16 else Decimal("0.025")),
                fee_rate=Decimal("0.00005"),
                half_spread_rate=Decimal("0.00010"),
                impact_coefficient=Decimal("0.05"),
                latency_rate=Decimal("0.00005"),
                borrow_rate=Decimal("0.00002"),
                borrow_applicable=index % 2 == 0,
                hard_to_borrow_available=True,
                independent_event_id=f"synthetic-event-{index + 1:02d}",
                regime_id=("synthetic-low-vol" if index < 16 else "synthetic-high-vol"),
                rate_available_at_utc=decision - timedelta(hours=2),
                rate_change=(Decimal("0.01") if index % 2 == 0 else Decimal("-0.01")),
                crisis_window_ids=(("synthetic-stress-window-v1",) if index >= 18 else ()),
                gross_exposure=Decimal("0.05"),
                net_exposure=Decimal("0.05"),
                sector_exposure=Decimal("0.05"),
                turnover=Decimal("0.10"),
                price_adjustment_basis=(
                    "raw_unadjusted"
                    if source_payload.adjustment_basis.value == "raw_unadjusted"
                    else "adjusted_for_corporate_action"
                ),
                adjustment_action_as_of_utc=source_payload.adjustment_as_of,
                fundamental_revision=None,
                feature_dependency_ids=(
                    source_feature_dependency_id(DataCapability.OHLCV, "open"),
                ),
                target_dependency_ids=(label_dependency_id(policy.label_specification),),
                universe_membership=UniverseMembershipEvidence(
                    membership_id=str(membership_key.normalized_observation_id),
                    universe_id=membership_payload.universe_id,
                    membership_status=membership_payload.status.value,
                    as_of_utc=membership_expectation.normalized_observation.available_at,
                    valid_from_utc=membership_expectation.normalized_observation.valid_from,
                    valid_to_utc=membership_expectation.normalized_observation.valid_to,
                ),
            )
        )
    return tuple(samples)


def _trials(
    samples: tuple[SyntheticSample, ...],
    policy: FrozenEvaluationPolicy,
) -> tuple[SyntheticTrial, ...]:
    outer_samples = samples[-8:]
    inner_sample_ids = (
        "synthetic-sample-09",
        "synthetic-sample-10",
        "synthetic-sample-13",
        "synthetic-sample-14",
    )
    baseline_cost_by_sample = {
        item.sample_id: item.total_cost
        for item in build_cost_ledger(samples, policy.costs, policy.stress)
        if item.scenario is CostScenario.BASELINE
    }
    common_calendar = tuple(sample.decision_time_utc for sample in outer_samples)
    outer_sample_ids = tuple(sample.sample_id for sample in outer_samples)

    def completed_trial(
        *,
        trial_key: str,
        model: str,
        variant: str,
        inner_gross_returns: tuple[str, ...],
        outer_gross_returns: tuple[str, ...],
        initiated_minute: int,
    ) -> SyntheticTrial:
        inner_evidence = {
            sample_id: Decimal(value)
            for sample_id, value in zip(
                inner_sample_ids,
                inner_gross_returns,
                strict=True,
            )
        }
        outer_evidence = {
            sample_id: Decimal(value)
            for sample_id, value in zip(
                outer_sample_ids,
                outer_gross_returns,
                strict=True,
            )
        }
        inner_statuses = {
            sample_id: ResearchReturnStatus.OBSERVED for sample_id in inner_sample_ids
        }
        outer_statuses = tuple(ResearchReturnStatus.OBSERVED for _sample_id in outer_sample_ids)
        return SyntheticTrial(
            trial_key=trial_key,
            status=TrialStatus.COMPLETED,
            configuration={
                "model": model,
                "variant": variant,
                "inner_validation_gross_returns_json": canonical_json_text(inner_evidence),
                "inner_validation_return_statuses_json": canonical_json_text(inner_statuses),
                "outer_gross_returns_json": canonical_json_text(outer_evidence),
            },
            net_returns=tuple(
                outer_evidence[sample_id] - baseline_cost_by_sample[sample_id]
                for sample_id in outer_sample_ids
            ),
            return_statuses=outer_statuses,
            return_timestamps_utc=common_calendar,
            initiated_by="phase5-synthetic-registry",
            initiated_at_utc=datetime(2026, 1, 1, 0, initiated_minute, tzinfo=UTC),
        )

    return (
        completed_trial(
            trial_key="stable-primary",
            model="synthetic-baseline-a",
            variant="1",
            inner_gross_returns=(".0055", ".007", ".008", "-.001"),
            outer_gross_returns=(
                ".008",
                "-.001",
                ".009",
                ".007",
                ".010",
                "-.0005",
                ".008",
                ".007",
            ),
            initiated_minute=1,
        ),
        completed_trial(
            trial_key="stable-secondary",
            model="synthetic-baseline-b",
            variant="2",
            inner_gross_returns=(".004", ".0045", ".006", "-.0015"),
            outer_gross_returns=(
                ".006",
                "-.0015",
                ".0065",
                ".005",
                ".007",
                "-.001",
                ".006",
                ".005",
            ),
            initiated_minute=2,
        ),
        completed_trial(
            trial_key="stable-tertiary",
            model="synthetic-baseline-c",
            variant="3",
            inner_gross_returns=(".003", ".0035", ".004", "-.002"),
            outer_gross_returns=(
                ".004",
                "-.002",
                ".0045",
                ".003",
                ".005",
                "-.0015",
                ".004",
                ".003",
            ),
            initiated_minute=3,
        ),
        completed_trial(
            trial_key="negative-reference",
            model="synthetic-negative-control",
            variant="4",
            inner_gross_returns=("-.001", "-.003", "-.001", "-.004"),
            outer_gross_returns=(
                "-.001",
                "-.004",
                "-.0005",
                "-.002",
                "0",
                "-.0035",
                "-.001",
                "-.002",
            ),
            initiated_minute=4,
        ),
        SyntheticTrial(
            trial_key="failed-variant",
            status=TrialStatus.FAILED,
            configuration={"model": "synthetic-failed", "variant": "5"},
            net_returns=(),
            return_statuses=(),
            return_timestamps_utc=(),
            initiated_by="phase5-synthetic-registry",
            initiated_at_utc=datetime(2026, 1, 1, 0, 5, tzinfo=UTC),
            failure_reason="deterministic fixture failure retained in raw trial count",
        ),
        SyntheticTrial(
            trial_key="abandoned-variant",
            status=TrialStatus.ABANDONED,
            configuration={"model": "synthetic-abandoned", "variant": "6"},
            net_returns=(),
            return_statuses=(),
            return_timestamps_utc=(),
            initiated_by="phase5-synthetic-registry",
            initiated_at_utc=datetime(2026, 1, 1, 0, 6, tzinfo=UTC),
            failure_reason="deterministic fixture abandonment retained in raw trial count",
        ),
    )


def build_synthetic_fixture(
    policy: FrozenEvaluationPolicy | None = None,
) -> SyntheticEvaluationFixture:
    resolved_policy = policy or build_synthetic_policy()
    source_observation_expectations = _source_observation_expectations()
    samples = _samples(source_observation_expectations, resolved_policy)
    content = {
        "fixture_id": SYNTHETIC_FIXTURE_ID,
        "fixture_version": "phase5-synthetic-evaluation-fixtures-v1",
        "random_seed": 5012026,
        "synthetic": True,
        "no_real_performance_claimed": True,
        "source_observation_expectations": source_observation_expectations,
        "samples": samples,
        "trials": _trials(samples, resolved_policy),
        "warnings": (
            "Predictions and returns are deterministic synthetic research-ledger inputs "
            "and are not real performance.",
            "Feature and cost-reference values are bound to exact Phase 4 synthetic "
            "source evidence.",
            "PASS_RESEARCH, if reached, is a research result and is not paper approval.",
        ),
    }
    digest = domain_sha256(PHASE5_FIXTURE_HASH_DOMAIN, content)
    return SyntheticEvaluationFixture.model_validate({**content, "fixture_sha256": digest})


REGISTERED_POLICY = build_synthetic_policy()
REGISTERED_FIXTURE = build_synthetic_fixture(REGISTERED_POLICY)


def resolve_policy(policy_id: UUID, policy_version: int) -> FrozenEvaluationPolicy | None:
    if (policy_id, policy_version) == (
        REGISTERED_POLICY.policy_id,
        REGISTERED_POLICY.policy_version,
    ):
        return REGISTERED_POLICY
    return None


def resolve_fixture(fixture_id: str) -> SyntheticEvaluationFixture | None:
    if fixture_id == REGISTERED_FIXTURE.fixture_id:
        return REGISTERED_FIXTURE
    return None


__all__ = [
    "REGISTERED_FIXTURE",
    "REGISTERED_POLICY",
    "SYNTHETIC_FIXTURE_ID",
    "SYNTHETIC_POLICY_ID",
    "SYNTHETIC_POLICY_VERSION",
    "build_synthetic_fixture",
    "build_synthetic_policy",
    "resolve_fixture",
    "resolve_policy",
]
