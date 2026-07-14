"""Prepared Phase 6 evidence for the unchanged Phase 5 evaluation engine.

The objects in this module are deterministic synthetic research evidence. They carry no
action, allocation, approval, paper-execution, or live-execution semantics.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal, localcontext
from uuid import UUID, uuid5

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
    PHASE5_SYNTHETIC_LEDGER_VALUE_RULE,
    PHASE6_SOURCE_FEATURE_DERIVATION_FORMULA,
    PHASE6_SOURCE_FEATURE_DERIVATION_HASH_DOMAIN,
    PHASE6_SOURCE_FEATURE_DERIVATION_SCHEMA_VERSION,
    CostScenario,
    FeatureSpecification,
    FoldKind,
    FrozenEvaluationPolicy,
    FundamentalRevisionEvidence,
    LabelSpecification,
    ResearchReturnStatus,
    SignalSpecification,
    SourceFeatureDerivation,
    SourceObservationKey,
    SourceValueBinding,
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
from fable5_backtester.evaluation_geometry import build_evaluation_geometry
from fable5_backtester.synthetic import REGISTERED_POLICY
from fable5_data.contracts import (
    AsReportedFundamentalPayload,
    ConstituentDisposition,
    DataCapability,
    NormalizedObservation,
    NormalizedObservationDraft,
    OhlcvBarPayload,
    SnapshotBundle,
    UniverseMembershipPayload,
)
from fable5_mapping.models import CanonicalFamily

from fable5_research.contracts import (
    PreparedResearchPipeline,
    ResearchConfigurationId,
    ResearchFeatureRow,
    ResearchSourceReference,
)

_POLICY_NAMESPACE = UUID("14f0fdb7-5ae6-5d7d-a1d7-8f651862574f")
_TRIAL_PENALTIES = (
    Decimal("0"),
    Decimal("0.0005"),
    Decimal("0.0010"),
    Decimal("0.0015"),
)
_DERIVATION_MULTIPLIER_QUANTUM = Decimal("1e-24")


def configuration_family(configuration_id: ResearchConfigurationId) -> CanonicalFamily:
    """Return the one frozen family selected by a server-owned fixture id."""

    if configuration_id in {ResearchConfigurationId.A_PASS, ResearchConfigurationId.A_FAIL}:
        return CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING
    if configuration_id in {ResearchConfigurationId.B_PASS, ResearchConfigurationId.B_FAIL}:
        return CanonicalFamily.B_TIME_SERIES_MOMENTUM_REGIME
    return CanonicalFamily.C_OFFICIAL_EVENT_TEXT_OVERLAY


def configuration_is_cost_failure(configuration_id: ResearchConfigurationId) -> bool:
    return configuration_id is ResearchConfigurationId.A_FAIL


def configuration_is_crash_failure(configuration_id: ResearchConfigurationId) -> bool:
    return configuration_id is ResearchConfigurationId.B_FAIL


def _draft(observation: NormalizedObservation) -> NormalizedObservationDraft:
    values = {
        field_name: getattr(observation, field_name)
        for field_name in NormalizedObservationDraft.model_fields
    }
    return NormalizedObservationDraft.model_validate(values)


def _feature_specification() -> FeatureSpecification:
    content = {
        "schema_version": "phase5-feature-specification-v1",
        "version": "phase6-prepared-score-anchor-contract-v1",
        "formula_id": PHASE6_SOURCE_FEATURE_DERIVATION_FORMULA,
        "source_fields": ("ohlcv.open",),
        "lookback_rule": (
            "prepared Phase 6 features plus an exact same-entity raw OHLCV audit anchor"
        ),
        "availability_rule": "every input available_at is no later than decision_time",
        "source_observation_binding_rule": "phase5-exact-snapshot-constituent-value-v1",
        "preprocessing_rules": ("phase5-train-only-standardizer-v1",),
        "imputation_policy": "block-missing-feature-no-imputation-v1",
        "encoding_policy": "numeric-identity-no-categorical-encoding-v1",
        "feature_selection_policy": "frozen-phase6-family-feature-list-v1",
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


def _label_specification(family: CanonicalFamily) -> LabelSpecification:
    content = {
        "schema_version": "phase5-label-specification-v1",
        "version": "phase6-prepared-forward-label-contract-v1",
        "formula_id": f"phase6-{family.value.lower()}-forward-two-session-return-v1",
        "forecast_horizon": "two UTC research decision sessions",
        "information_interval_rule": "closed interval from decision time through horizon end",
        "missing_return_policy": "block_missing_return_v1",
        "no_trade_return_policy": "explicit_zero_research_observation_v1",
        "delisting_return_policy": "require-explicit-action-and-delisting-aware-outcome-v1",
    }
    digest = domain_sha256(PHASE5_LABEL_HASH_DOMAIN, content)
    return LabelSpecification.model_validate(
        {
            **content,
            "label_specification_id": identity(PHASE5_LABEL_NAMESPACE, digest),
            "content_sha256": digest,
        }
    )


def build_phase5_policy(
    *,
    configuration_id: ResearchConfigurationId,
    capabilities: tuple[DataCapability, ...],
    origin: datetime,
    confirmation_start_utc: datetime | None = None,
    confirmation_end_utc: datetime | None = None,
    pipeline_input_sha256: str | None = None,
) -> FrozenEvaluationPolicy:
    """Generalize family lineage while leaving every Phase 5 gate implementation unchanged."""

    family = configuration_family(configuration_id)
    feature = _feature_specification()
    label = _label_specification(family)
    base = REGISTERED_POLICY.model_dump(
        mode="python",
        exclude={"policy_sha256", "policy_canonical_json"},
    )
    pipeline_hash = pipeline_input_sha256 or "0" * 64
    policy_id = uuid5(
        _POLICY_NAMESPACE,
        f"{configuration_id.value}:{pipeline_hash}:{origin.isoformat()}",
    )
    stress = REGISTERED_POLICY.stress.model_copy(
        update={
            "min_stressed_net_pnl": (
                Decimal("1")
                if configuration_is_cost_failure(configuration_id)
                else Decimal("0.000001")
            )
        }
    )
    confirmation_start = confirmation_start_utc or origin + timedelta(days=20)
    confirmation_end = confirmation_end_utc or origin + timedelta(days=22)
    policy_content = {
        **base,
        "policy_id": policy_id,
        "strategy_family": family,
        "selection_scope": f"{configuration_id.value}-prepared-nested-phase5-only",
        "signal_specification": SignalSpecification(
            specification_id=f"{configuration_id.value}-prepared-score-specification",
            version="v1",
            definition=(
                "A deterministic explainable prepared research score evaluated by the complete "
                "Phase 5 engine; it has no instruction, allocation, approval, or execution "
                "semantics."
            ),
            deterministic_formula_id=f"{configuration_id.value}-prepared-research-score-v1",
            forecast_horizon="two UTC research decision sessions",
            executable_decision_lag="one minute after every required source is available",
            universe_eligibility_rule="authorized immutable Phase 4 point-in-time evidence only",
            universe_exclusion_rule=(
                "exclude missing PIT, delisting, correction, capability, or leakage evidence"
            ),
            rebalance_rule="one deterministic synthetic research observation per UTC session",
            holding_rule="two-session label interval with no execution semantics",
            overlap_rule="overlapping labels are purged from every applicable training fold",
        ),
        "required_snapshot_capabilities": capabilities,
        "feature_specification": feature,
        "label_specification": label,
        "walk_forward": WalkForwardPolicy(
            decision_calendar="phase6-synthetic-utc-session-calendar-v1",
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
            final_confirmation_start_utc=confirmation_start,
            final_confirmation_end_utc=confirmation_end,
            final_confirmation_opening_rule=(
                "reserved-nonempty-untouched-phase6-prepared-interval-v1"
            ),
        ),
        "stress": stress,
        "approved_by": "phase6-deterministic-fixture-policy-owner",
    }
    digest = domain_sha256(PHASE5_POLICY_HASH_DOMAIN, policy_content)
    return FrozenEvaluationPolicy.model_validate(
        {
            **policy_content,
            "policy_sha256": digest,
            "policy_canonical_json": canonical_json_text(policy_content),
        }
    )


SourceEntry = tuple[DataCapability, NormalizedObservation, ConstituentDisposition]


def _source_index(
    snapshots: tuple[SnapshotBundle, ...],
) -> dict[tuple[DataCapability, UUID], SourceEntry]:
    indexed: dict[tuple[DataCapability, UUID], SourceEntry] = {}
    for bundle in snapshots:
        capability = bundle.snapshot.manifest.payload.request.capability
        dispositions = {
            item.normalized_observation_id: item.disposition for item in bundle.constituents
        }
        for observation in bundle.normalized_observations:
            disposition = dispositions.get(observation.normalized_observation_id)
            if disposition is None:
                continue
            key = (capability, observation.normalized_observation_id)
            if key in indexed:
                raise ValueError("Phase 6 source observation identity is ambiguous")
            indexed[key] = (capability, observation, disposition)
    return indexed


def _entry_for_reference(
    reference: ResearchSourceReference,
    indexed: dict[tuple[DataCapability, UUID], SourceEntry],
) -> SourceEntry:
    entry = indexed.get((reference.capability, reference.normalized_observation_id))
    if entry is None:
        raise ValueError("prepared source reference is absent from its exact snapshot")
    _capability, observation, _disposition = entry
    if (
        observation.snapshot_id != reference.snapshot_id
        or observation.snapshot_sha256 != reference.snapshot_sha256
        or observation.raw_observation_id != reference.raw_observation_id
        or observation.observation_revision_id != reference.observation_revision_id
        or observation.raw_payload_sha256 != reference.raw_payload_sha256
        or observation.normalized_content_sha256 != reference.normalized_content_sha256
    ):
        raise ValueError("prepared source reference conflicts with immutable Phase 4 lineage")
    return entry


def _available_at_decision(observation: NormalizedObservation, decision: datetime) -> bool:
    return (
        observation.event_time <= decision
        and observation.available_at <= decision
        and observation.valid_from <= decision
        and (observation.valid_to is None or decision < observation.valid_to)
    )


def _same_identity(
    observation: NormalizedObservation,
    anchor: NormalizedObservation,
) -> bool:
    return (
        observation.instrument_id == anchor.instrument_id
        and observation.listing_id == anchor.listing_id
    )


def _row_entries(
    row: ResearchFeatureRow,
    indexed: dict[tuple[DataCapability, UUID], SourceEntry],
) -> tuple[SourceEntry, ...]:
    references = tuple(
        reference for feature in row.features for reference in feature.source_references
    )
    entries = {
        (reference.capability, reference.normalized_observation_id): _entry_for_reference(
            reference,
            indexed,
        )
        for reference in references
    }
    return tuple(
        entries[key] for key in sorted(entries, key=lambda item: (str(item[0]), str(item[1])))
    )


def _select_anchor(
    row: ResearchFeatureRow,
    row_entries: tuple[SourceEntry, ...],
    indexed: dict[tuple[DataCapability, UUID], SourceEntry],
) -> SourceEntry:
    matches = tuple(
        entry
        for entry in row_entries
        if entry[0] is DataCapability.OHLCV
        and isinstance(entry[1].payload, OhlcvBarPayload)
        and entry[1].payload.adjustment_basis.value == "raw_unadjusted"
        and _available_at_decision(entry[1], row.decision_time_utc)
    )
    if not matches:
        identities = {
            (entry[1].instrument_id, entry[1].listing_id)
            for entry in row_entries
            if entry[1].instrument_id is not None and entry[1].listing_id is not None
        }
        if len(identities) != 1:
            raise ValueError("prepared row lacks one exact feature-source entity identity")
        instrument_id, listing_id = next(iter(identities))
        matches = tuple(
            entry
            for entry in indexed.values()
            if entry[0] is DataCapability.OHLCV
            and isinstance(entry[1].payload, OhlcvBarPayload)
            and entry[1].payload.adjustment_basis.value == "raw_unadjusted"
            and entry[1].instrument_id == instrument_id
            and entry[1].listing_id == listing_id
            and _available_at_decision(entry[1], row.decision_time_utc)
        )
    if not matches:
        raise ValueError("prepared row lacks an exact same-identity PIT OHLCV audit anchor")
    return max(matches, key=lambda item: (item[1].available_at, item[1].source_record_id))


def _select_membership(
    *,
    row: ResearchFeatureRow,
    anchor: NormalizedObservation,
    indexed: dict[tuple[DataCapability, UUID], SourceEntry],
) -> SourceEntry:
    matches = tuple(
        entry
        for entry in indexed.values()
        if entry[0] is DataCapability.UNIVERSE_MEMBERSHIP
        and isinstance(entry[1].payload, UniverseMembershipPayload)
        and entry[1].payload.status.value == "included"
        and _same_identity(entry[1], anchor)
        and _available_at_decision(entry[1], row.decision_time_utc)
    )
    if len(matches) != 1:
        raise ValueError("prepared row requires exactly one included PIT membership interval")
    return matches[0]


def _select_capability_entry(
    *,
    capability: DataCapability,
    row: ResearchFeatureRow,
    anchor: NormalizedObservation,
    row_entries: tuple[SourceEntry, ...],
    indexed: dict[tuple[DataCapability, UUID], SourceEntry],
) -> SourceEntry | None:
    row_matches = tuple(
        entry
        for entry in row_entries
        if entry[0] is capability and _available_at_decision(entry[1], row.decision_time_utc)
    )
    same_identity_global_matches = tuple(
        entry
        for entry in indexed.values()
        if entry[0] is capability
        and _same_identity(entry[1], anchor)
        and _available_at_decision(entry[1], row.decision_time_utc)
    )
    candidates = row_matches or same_identity_global_matches
    if not candidates:
        return None
    if any(
        entry[1].instrument_id is not None and not _same_identity(entry[1], anchor)
        for entry in candidates
    ):
        raise ValueError("prepared feature source crosses its sample entity boundary")
    return max(candidates, key=lambda item: (item[1].available_at, item[1].source_record_id))


def _sample_sources(
    *,
    row: ResearchFeatureRow,
    required_capabilities: tuple[DataCapability, ...],
    indexed: dict[tuple[DataCapability, UUID], SourceEntry],
) -> tuple[SourceEntry, tuple[SourceEntry, ...]]:
    row_entries = _row_entries(row, indexed)
    anchor_entry = _select_anchor(row, row_entries, indexed)
    anchor = anchor_entry[1]
    selected: dict[tuple[DataCapability, UUID], SourceEntry] = {
        (anchor_entry[0], anchor.normalized_observation_id): anchor_entry,
    }
    for entry in row_entries:
        if not _available_at_decision(entry[1], row.decision_time_utc):
            continue
        if entry[0] is DataCapability.AS_REPORTED_FUNDAMENTALS:
            # Unchanged L02 requires one unambiguous declared vintage per sample. The
            # remaining exact concept observations stay in the report-wide expectation
            # graph and in the prepared feature-row lineage.
            continue
        if entry[1].instrument_id is not None and not _same_identity(entry[1], anchor):
            raise ValueError("prepared feature source crosses its sample entity boundary")
        selected[(entry[0], entry[1].normalized_observation_id)] = entry
    membership = _select_membership(row=row, anchor=anchor, indexed=indexed)
    selected[(membership[0], membership[1].normalized_observation_id)] = membership
    for capability in required_capabilities:
        if capability in {DataCapability.OHLCV, DataCapability.UNIVERSE_MEMBERSHIP}:
            continue
        chosen: SourceEntry | None
        if capability is DataCapability.AS_REPORTED_FUNDAMENTALS:
            fundamentals = tuple(
                entry
                for entry in row_entries
                if entry[0] is capability
                and isinstance(entry[1].payload, AsReportedFundamentalPayload)
                and _same_identity(entry[1], anchor)
                and _available_at_decision(entry[1], row.decision_time_utc)
            )
            if not fundamentals:
                raise ValueError("prepared Family A row lacks as-reported evidence")
            chosen = fundamentals[(row.ordinal - 1) % len(fundamentals)]
        else:
            chosen = _select_capability_entry(
                capability=capability,
                row=row,
                anchor=anchor,
                row_entries=row_entries,
                indexed=indexed,
            )
        if chosen is None:
            continue
        selected[(chosen[0], chosen[1].normalized_observation_id)] = chosen

    if DataCapability.OFFICIAL_DOCUMENT_EVENT_METADATA in required_capabilities:
        social = tuple(
            entry
            for entry in indexed.values()
            if entry[0] is DataCapability.OFFICIAL_DOCUMENT_EVENT_METADATA
            and entry[1].payload.record_type == "social_attention"
            and _same_identity(entry[1], anchor)
            and _available_at_decision(entry[1], row.decision_time_utc)
        )
        for entry in social:
            selected[(entry[0], entry[1].normalized_observation_id)] = entry

    ordered = tuple(
        selected[key] for key in sorted(selected, key=lambda item: (str(item[0]), str(item[1])))
    )
    return anchor_entry, ordered


def _fundamental_evidence(
    selected: tuple[SourceEntry, ...],
) -> FundamentalRevisionEvidence | None:
    fundamentals = tuple(
        observation
        for capability, observation, _disposition in selected
        if capability is DataCapability.AS_REPORTED_FUNDAMENTALS
        and isinstance(observation.payload, AsReportedFundamentalPayload)
    )
    if not fundamentals:
        return None
    observation = min(
        fundamentals,
        key=lambda item: (
            item.available_at,
            item.payload.concept_id
            if isinstance(item.payload, AsReportedFundamentalPayload)
            else "",
            item.revision_id,
        ),
    )
    payload = observation.payload
    if not isinstance(payload, AsReportedFundamentalPayload):
        raise ValueError("fundamental evidence payload is invalid")
    revision_trace = (
        *((payload.restates_revision_id,) if payload.restates_revision_id else ()),
        observation.revision_id,
    )
    return FundamentalRevisionEvidence(
        dependency_ids=(f"phase4-as-reported-fundamentals.{payload.concept_id}",),
        revision_id=observation.revision_id,
        accepted_at_utc=payload.filing_accepted_at,
        available_at_utc=observation.available_at,
        revision_trace_ids=revision_trace,
    )


def _samples_and_expectations(
    *,
    prepared: PreparedResearchPipeline,
    policy: FrozenEvaluationPolicy,
    snapshots: tuple[SnapshotBundle, ...],
) -> tuple[tuple[SyntheticSample, ...], tuple[SyntheticSourceObservationExpectation, ...]]:
    indexed = _source_index(snapshots)
    score_by_sample = {item.sample_id: item for item in prepared.scores}
    expectation_entries: dict[tuple[DataCapability, UUID], SourceEntry] = {}
    anchor_keys: set[tuple[DataCapability, UUID]] = set()
    samples: list[SyntheticSample] = []
    for index, row in enumerate(prepared.feature_rows):
        score = score_by_sample.get(row.sample_id)
        if score is None or score.research_score != row.composite_score:
            raise ValueError("prepared score output does not match its exact feature row")
        anchor_entry, selected = _sample_sources(
            row=row,
            required_capabilities=policy.required_snapshot_capabilities,
            indexed=indexed,
        )
        _anchor_capability, anchor, _anchor_disposition = anchor_entry
        anchor_payload = anchor.payload
        if not isinstance(anchor_payload, OhlcvBarPayload) or anchor_payload.open == 0:
            raise ValueError("prepared Phase 5 anchor must be a nonzero raw OHLCV open")
        anchor_key = (DataCapability.OHLCV, anchor.normalized_observation_id)
        anchor_keys.add(anchor_key)
        for entry in selected:
            expectation_entries[(entry[0], entry[1].normalized_observation_id)] = entry
        for entry in _row_entries(row, indexed):
            if entry[0] is DataCapability.AS_REPORTED_FUNDAMENTALS:
                expectation_entries[(entry[0], entry[1].normalized_observation_id)] = entry
        feature_available = max(
            max(observation.event_time, observation.available_at)
            for _capability, observation, _disposition in selected
        )
        if feature_available > row.decision_time_utc:
            raise ValueError("prepared sample source is unavailable at its decision")
        with localcontext() as decimal_context:
            decimal_context.prec = 80
            multiplier = (row.composite_score / anchor_payload.open).quantize(
                _DERIVATION_MULTIPLIER_QUANTUM
            )
        derivation_content = {
            "schema_version": PHASE6_SOURCE_FEATURE_DERIVATION_SCHEMA_VERSION,
            "formula_id": PHASE6_SOURCE_FEATURE_DERIVATION_FORMULA,
            "source_observation_key": SourceObservationKey(
                capability=DataCapability.OHLCV,
                normalized_observation_id=anchor.normalized_observation_id,
            ),
            "source_payload_field": "open",
            "multiplier": multiplier,
            "derived_feature_value": row.composite_score,
        }
        membership_entry = next(
            entry for entry in selected if entry[0] is DataCapability.UNIVERSE_MEMBERSHIP
        )
        membership_observation = membership_entry[1]
        membership_payload = membership_observation.payload
        if not isinstance(membership_payload, UniverseMembershipPayload):
            raise ValueError("prepared membership payload is invalid")
        source_keys = tuple(
            sorted(
                (
                    SourceObservationKey(
                        capability=capability,
                        normalized_observation_id=observation.normalized_observation_id,
                    )
                    for capability, observation, _disposition in selected
                ),
                key=lambda item: (str(item.capability), str(item.normalized_observation_id)),
            )
        )
        high_volatility = index >= len(prepared.feature_rows) - 4
        crash_window = index >= len(prepared.feature_rows) - 2
        samples.append(
            SyntheticSample(
                sample_id=row.sample_id,
                source_observation_keys=source_keys,
                feature_derivation=SourceFeatureDerivation.model_validate(
                    {
                        **derivation_content,
                        "derivation_sha256": domain_sha256(
                            PHASE6_SOURCE_FEATURE_DERIVATION_HASH_DOMAIN,
                            derivation_content,
                        ),
                    }
                ),
                synthetic_ledger_value_rule=PHASE5_SYNTHETIC_LEDGER_VALUE_RULE,
                decision_time_utc=row.decision_time_utc,
                feature_available_at_utc=feature_available,
                label_t0_utc=row.label_t0_utc,
                label_t1_utc=row.label_t1_utc,
                feature_value=row.composite_score,
                predicted_value=score.research_score,
                gross_return=row.label_value,
                # Keep Phase 6's synthetic participation rate exactly representable by
                # Phase 5's immutable NUMERIC(38,30) persistence contract.  Binding the
                # allocation to ADV at one basis point of one percent yields 0.00001
                # without rounding or weakening any Phase 5 validator.
                research_allocation_units=(
                    anchor_payload.volume * Decimal("0.1") * Decimal("0.00001")
                ),
                reference_price=anchor_payload.open,
                daily_adv_units=anchor_payload.volume * Decimal("0.1"),
                daily_volatility=(Decimal("0.025") if high_volatility else Decimal("0.015")),
                fee_rate=Decimal("0.00005"),
                half_spread_rate=Decimal("0.00010"),
                impact_coefficient=Decimal("0.05"),
                latency_rate=Decimal("0.00005"),
                borrow_rate=Decimal("0.00002"),
                borrow_applicable=index % 2 == 0,
                hard_to_borrow_available=True,
                independent_event_id=f"{row.sample_id}-prepared-event",
                regime_id=("synthetic-high-vol" if high_volatility else "synthetic-low-vol"),
                rate_available_at_utc=row.decision_time_utc - timedelta(hours=1),
                rate_change=Decimal("0.01") if index % 2 == 0 else Decimal("-0.01"),
                crisis_window_ids=(
                    ()
                    if configuration_is_crash_failure(prepared.configuration_id)
                    else (("synthetic-stress-window-v1",) if crash_window else ())
                ),
                gross_exposure=Decimal("0.05"),
                net_exposure=Decimal("0.05"),
                sector_exposure=Decimal("0.05"),
                turnover=Decimal("0.10"),
                price_adjustment_basis="raw_unadjusted",
                adjustment_action_as_of_utc=anchor_payload.adjustment_as_of,
                fundamental_revision=_fundamental_evidence(selected),
                feature_dependency_ids=(
                    source_feature_dependency_id(DataCapability.OHLCV, "open"),
                ),
                target_dependency_ids=(label_dependency_id(policy.label_specification),),
                universe_membership=UniverseMembershipEvidence(
                    membership_id=str(membership_observation.normalized_observation_id),
                    universe_id=membership_payload.universe_id,
                    membership_status=membership_payload.status.value,
                    as_of_utc=membership_observation.available_at,
                    valid_from_utc=membership_observation.valid_from,
                    valid_to_utc=membership_observation.valid_to,
                ),
            )
        )

    covered_capabilities = {capability for capability, _observation_id in expectation_entries}
    for capability in policy.required_snapshot_capabilities:
        if capability in covered_capabilities:
            continue
        witnesses = tuple(entry for entry in indexed.values() if entry[0] is capability)
        if not witnesses:
            raise ValueError(f"prepared Phase 5 capability witness is missing: {capability.value}")
        witness = min(
            witnesses,
            key=lambda item: (
                item[1].available_at,
                item[1].source_record_id,
                str(item[1].normalized_observation_id),
            ),
        )
        expectation_entries[(witness[0], witness[1].normalized_observation_id)] = witness

    covered_capabilities = {capability for capability, _observation_id in expectation_entries}
    required_capabilities = set(policy.required_snapshot_capabilities)
    if covered_capabilities != required_capabilities:
        missing = sorted(item.value for item in required_capabilities - covered_capabilities)
        extra = sorted(item.value for item in covered_capabilities - required_capabilities)
        raise ValueError(
            "prepared Phase 5 source coverage does not match policy: "
            f"missing={missing}; extra={extra}"
        )

    expectations: list[SyntheticSourceObservationExpectation] = []
    for key in sorted(expectation_entries, key=lambda item: (str(item[0]), str(item[1]))):
        capability, observation, disposition = expectation_entries[key]
        bindings: tuple[SourceValueBinding, ...] = ()
        if key in anchor_keys:
            bindings = (
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
            )
        expectations.append(
            SyntheticSourceObservationExpectation(
                key=SourceObservationKey(
                    capability=capability,
                    normalized_observation_id=observation.normalized_observation_id,
                ),
                normalized_observation=_draft(observation),
                required_disposition=disposition,
                value_bindings=bindings,
            )
        )
    return tuple(samples), tuple(expectations)


def _fixture(
    *,
    fixture_id: str,
    expectations: tuple[SyntheticSourceObservationExpectation, ...],
    samples: tuple[SyntheticSample, ...],
    trials: tuple[SyntheticTrial, ...],
) -> SyntheticEvaluationFixture:
    content = {
        "fixture_id": fixture_id,
        "fixture_version": "phase5-synthetic-evaluation-fixtures-v1",
        "random_seed": 6012026,
        "synthetic": True,
        "no_real_performance_claimed": True,
        "source_observation_expectations": expectations,
        "samples": samples,
        "trials": trials,
        "warnings": (
            "All labels, scores, and returns are deterministic synthetic research evidence, "
            "not real performance.",
            "Every Phase 5 sample is bound to its exact prepared Phase 6 row and immutable "
            "Phase 4 source evidence.",
            "PASS_RESEARCH is a research result and is not paper approval.",
        ),
    }
    digest = domain_sha256(PHASE5_FIXTURE_HASH_DOMAIN, content)
    return SyntheticEvaluationFixture.model_validate({**content, "fixture_sha256": digest})


def _provisional_trials(pipeline_input_sha256: str) -> tuple[SyntheticTrial, ...]:
    return tuple(
        SyntheticTrial(
            trial_key=f"geometry-placeholder-{ordinal}",
            status=TrialStatus.FAILED,
            configuration={
                "model": "geometry-placeholder",
                "phase6_pipeline_input_sha256": pipeline_input_sha256,
                "variant": str(ordinal),
            },
            net_returns=(),
            return_statuses=(),
            return_timestamps_utc=(),
            initiated_by="phase6-prepared-trial-registry",
            initiated_at_utc=datetime(2026, 1, 1, 0, ordinal, tzinfo=UTC),
            failure_reason="geometry-only placeholder never persisted",
        )
        for ordinal in (1, 2)
    )


def _trial_model_ids(family: CanonicalFamily) -> tuple[str, str, str, str]:
    if family is CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING:
        return (
            "sector-relative-rank-linear-v1",
            "zero-information-rank-v1",
            "frozen-depth-two-tree-v1",
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


def _trials(
    *,
    prepared: PreparedResearchPipeline,
    policy: FrozenEvaluationPolicy,
    fixture_id: str,
    expectations: tuple[SyntheticSourceObservationExpectation, ...],
    samples: tuple[SyntheticSample, ...],
) -> tuple[SyntheticTrial, ...]:
    provisional = _fixture(
        fixture_id=fixture_id,
        expectations=expectations,
        samples=samples,
        trials=_provisional_trials(prepared.pipeline_input_sha256),
    )
    geometry = build_evaluation_geometry(
        policy=policy,
        walk_forward=policy.walk_forward,
        fixture=provisional,
    )
    if not geometry.validation.passed:
        raise ValueError(
            "prepared Phase 6 rows cannot produce complete Phase 5 geometry: "
            + ",".join(geometry.validation.reason_codes)
        )
    outer_folds = tuple(
        fold for fold in geometry.folds if fold.fold_kind in {FoldKind.OUTER, FoldKind.CPCV}
    )
    outer_ids = tuple(sample_id for fold in outer_folds for sample_id in fold.test_sample_ids)
    inner_ids = tuple(
        dict.fromkeys(
            sample_id
            for fold in geometry.folds
            if fold.fold_kind is FoldKind.INNER
            for sample_id in fold.test_sample_ids
        )
    )
    samples_by_id = {item.sample_id: item for item in samples}
    rows_by_id = {item.sample_id: item for item in prepared.feature_rows}
    scores_by_id = {item.sample_id: item for item in prepared.scores}
    primary = {
        sample_id: (
            -abs(row.label_value) * Decimal("0.10")
            if row.ordinal % 4 == 2
            else (
                row.label_value if scores_by_id[sample_id].research_score >= 0 else -row.label_value
            )
        )
        for sample_id, row in rows_by_id.items()
    }
    variants = (
        primary,
        {sample_id: value - _TRIAL_PENALTIES[1] for sample_id, value in primary.items()},
        {sample_id: value - _TRIAL_PENALTIES[2] for sample_id, value in primary.items()},
        {sample_id: value - _TRIAL_PENALTIES[3] for sample_id, value in primary.items()},
    )
    baseline_cost_by_sample = {
        item.sample_id: item.total_cost
        for item in build_cost_ledger(samples, policy.costs, policy.stress)
        if item.scenario is CostScenario.BASELINE
    }
    model_ids = _trial_model_ids(prepared.family)
    common_calendar = tuple(samples_by_id[sample_id].decision_time_utc for sample_id in outer_ids)

    completed: list[SyntheticTrial] = []
    trial_keys = (
        "prepared-primary",
        "prepared-baseline",
        "prepared-nonlinear",
        "negative-reference",
    )
    for ordinal, (trial_key, model_id, outputs) in enumerate(
        zip(trial_keys, model_ids, variants, strict=True),
        start=1,
    ):
        inner_evidence = {sample_id: outputs[sample_id] for sample_id in inner_ids}
        outer_evidence = {sample_id: outputs[sample_id] for sample_id in outer_ids}
        statuses = {sample_id: ResearchReturnStatus.OBSERVED for sample_id in inner_ids}
        output_sha256 = domain_sha256(
            "phase6-phase5-model-output-set-v1",
            tuple((sample_id, outputs[sample_id]) for sample_id in sorted(outputs)),
        )
        completed.append(
            SyntheticTrial(
                trial_key=trial_key,
                status=TrialStatus.COMPLETED,
                configuration={
                    "model": model_id,
                    "variant": str(ordinal),
                    "phase6_pipeline_input_sha256": prepared.pipeline_input_sha256,
                    "phase6_model_output_sha256": output_sha256,
                    "phase6_label_sha256": domain_sha256(
                        "phase6-phase5-label-set-v1",
                        tuple(
                            (row.sample_id, row.label_value, row.label_t0_utc, row.label_t1_utc)
                            for row in prepared.feature_rows
                        ),
                    ),
                    "inner_validation_gross_returns_json": canonical_json_text(inner_evidence),
                    "inner_validation_return_statuses_json": canonical_json_text(statuses),
                    "outer_gross_returns_json": canonical_json_text(outer_evidence),
                },
                net_returns=tuple(
                    outer_evidence[sample_id] - baseline_cost_by_sample[sample_id]
                    for sample_id in outer_ids
                ),
                return_statuses=tuple(ResearchReturnStatus.OBSERVED for _ in outer_ids),
                return_timestamps_utc=common_calendar,
                initiated_by="phase6-prepared-trial-registry",
                initiated_at_utc=datetime(2026, 1, 1, 0, ordinal, tzinfo=UTC),
            )
        )
    incomplete = (
        SyntheticTrial(
            trial_key="failed-variant",
            status=TrialStatus.FAILED,
            configuration={
                "model": "prepared-failed",
                "phase6_pipeline_input_sha256": prepared.pipeline_input_sha256,
                "variant": "5",
            },
            net_returns=(),
            return_statuses=(),
            return_timestamps_utc=(),
            initiated_by="phase6-prepared-trial-registry",
            initiated_at_utc=datetime(2026, 1, 1, 0, 5, tzinfo=UTC),
            failure_reason="deterministic fixture failure retained in raw trial count",
        ),
        SyntheticTrial(
            trial_key="abandoned-variant",
            status=TrialStatus.ABANDONED,
            configuration={
                "model": "prepared-abandoned",
                "phase6_pipeline_input_sha256": prepared.pipeline_input_sha256,
                "variant": "6",
            },
            net_returns=(),
            return_statuses=(),
            return_timestamps_utc=(),
            initiated_by="phase6-prepared-trial-registry",
            initiated_at_utc=datetime(2026, 1, 1, 0, 6, tzinfo=UTC),
            failure_reason="deterministic fixture abandonment retained in raw trial count",
        ),
    )
    return (*completed, *incomplete)


def _validate_prepared_snapshots(
    prepared: PreparedResearchPipeline,
    snapshots: tuple[SnapshotBundle, ...],
) -> None:
    actual = tuple(
        sorted(
            (
                (
                    bundle.snapshot.manifest.payload.request.capability,
                    bundle.snapshot.snapshot_id,
                    bundle.snapshot.snapshot_sha256,
                )
                for bundle in snapshots
            ),
            key=lambda item: str(item[0]),
        )
    )
    expected = tuple(
        (item.capability, item.snapshot_id, item.snapshot_sha256)
        for item in prepared.snapshot_bindings
    )
    if actual != expected:
        raise ValueError("prepared pipeline snapshot bindings changed before Phase 5")


def build_phase5_inputs(
    *,
    configuration_id: ResearchConfigurationId,
    prepared: PreparedResearchPipeline,
    snapshots: tuple[SnapshotBundle, ...],
) -> tuple[FrozenEvaluationPolicy, SyntheticEvaluationFixture]:
    """Build exact Phase 5 evidence from one immutable prepared Phase 6 pipeline."""

    if (
        prepared.configuration_id is not configuration_id
        or prepared.family is not configuration_family(configuration_id)
    ):
        raise ValueError("prepared pipeline does not match the requested configuration")
    _validate_prepared_snapshots(prepared, snapshots)
    confirmation_start = prepared.feature_rows[-1].decision_time_utc + timedelta(microseconds=1)
    confirmation_end = max(item.label_t1_utc for item in prepared.feature_rows) + timedelta(
        seconds=1
    )
    policy = build_phase5_policy(
        configuration_id=configuration_id,
        capabilities=prepared.specification.required_capabilities,
        origin=prepared.feature_rows[0].decision_time_utc,
        confirmation_start_utc=confirmation_start,
        confirmation_end_utc=confirmation_end,
        pipeline_input_sha256=prepared.pipeline_input_sha256,
    )
    samples, expectations = _samples_and_expectations(
        prepared=prepared,
        policy=policy,
        snapshots=snapshots,
    )
    fixture_id = f"{configuration_id.value}-{prepared.pipeline_input_sha256[:24]}"
    trials = _trials(
        prepared=prepared,
        policy=policy,
        fixture_id=fixture_id,
        expectations=expectations,
        samples=samples,
    )
    return policy, _fixture(
        fixture_id=fixture_id,
        expectations=expectations,
        samples=samples,
        trials=trials,
    )


__all__ = [
    "build_phase5_inputs",
    "build_phase5_policy",
    "configuration_family",
    "configuration_is_cost_failure",
    "configuration_is_crash_failure",
]
