"""Prepared Phase 6 evidence for the unchanged Phase 5 evaluation engine.

The objects in this module are deterministic synthetic research evidence. They carry no
action, allocation, approval, paper-execution, or live-execution semantics.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
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
    PHASE6_REGIME_EVIDENCE_HASH_DOMAIN,
    PHASE6_REPORT_SCOPE_SOURCE_EVIDENCE_HASH_DOMAIN,
    PHASE6_SOURCE_FEATURE_DERIVATION_FORMULA,
    PHASE6_SOURCE_FEATURE_DERIVATION_HASH_DOMAIN,
    PHASE6_SOURCE_FEATURE_DERIVATION_SCHEMA_VERSION,
    CostScenario,
    FeatureSpecification,
    FoldKind,
    FrozenEvaluationPolicy,
    FundamentalRevisionEvidence,
    LabelSpecification,
    Phase6RegimeEvidenceAvailability,
    ReportScopeSourceEvidence,
    ReportScopeSourceRole,
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
from pydantic import BaseModel

from fable5_research.canonical import PHASE6_TRIAL_COST_SET_HASH_DOMAIN
from fable5_research.contracts import (
    PreparedFamilyAInputs,
    PreparedResearchPipeline,
    ResearchConfigurationId,
    ResearchFeatureRow,
    ResearchSourceReference,
)
from fable5_research.reproduction import verify_prepared_pipeline_reproduction
from fable5_research.specification import (
    FAMILY_B_COST_VOLATILITY_PROJECTION_ID,
    FAMILY_B_COST_VOLATILITY_QUANTUM,
    FAMILY_B_COST_VOLATILITY_QUANTUM_TEXT,
)
from fable5_research.trial_costs import build_long_flat_trial_costs

_POLICY_NAMESPACE = UUID("14f0fdb7-5ae6-5d7d-a1d7-8f651862574f")
_DERIVATION_MULTIPLIER_QUANTUM = Decimal("1e-24")
_DEFAULT_SYNTHETIC_PARTICIPATION = Decimal("0.00001")
_FAMILY_B_RATE_UNAVAILABLE_DEFINITION = "unavailable-no-authorized-pit-rate-source-v1"
_FAMILY_B_CRISIS_UNAVAILABLE_WINDOW = "unavailable-no-frozen-crisis-window-geometry-v1"
_FAMILY_B_REGIME_DEPENDENCY_RULE = "missing-rate-or-crisis-evidence-is-research-only-v1"


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
) -> FrozenEvaluationPolicy:
    """Generalize family lineage while leaving every Phase 5 gate implementation unchanged."""

    family = configuration_family(configuration_id)
    feature = _feature_specification()
    label = _label_specification(family)
    base = REGISTERED_POLICY.model_dump(
        mode="python",
        exclude={"policy_sha256", "policy_canonical_json"},
    )
    confirmation_start = confirmation_start_utc or origin + timedelta(days=20)
    confirmation_end = confirmation_end_utc or origin + timedelta(days=22)
    policy_id = uuid5(
        _POLICY_NAMESPACE,
        (
            f"{configuration_id.value}:{origin.isoformat()}:"
            f"{confirmation_start.isoformat()}:{confirmation_end.isoformat()}"
        ),
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
    regime_updates: dict[str, object]
    if family is CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING:
        regime_updates = {
            "volatility_definition": "prepared-pit-daily-volatility-cut-v1",
            "rate_definition": "pit-vintage-rate-change-at-release-v1",
            "crisis_windows": ("synthetic-predeclared-stress-2020-01",),
            "dependency_rule": "all-predeclared-regime-evidence-required-v1",
        }
    else:
        regime_updates = {
            "rate_definition": _FAMILY_B_RATE_UNAVAILABLE_DEFINITION,
            "crisis_windows": (_FAMILY_B_CRISIS_UNAVAILABLE_WINDOW,),
            "dependency_rule": _FAMILY_B_REGIME_DEPENDENCY_RULE,
        }
    if family is CanonicalFamily.B_TIME_SERIES_MOMENTUM_REGIME:
        regime_updates["volatility_definition"] = (
            "prepared-action-aware-252-session-realized-volatility-v1"
        )
    regimes = REGISTERED_POLICY.regimes.model_copy(update=regime_updates)
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
        "regimes": regimes,
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
    capability, observation, _disposition = entry
    expected_reference = ResearchSourceReference(
        capability=capability,
        snapshot_id=observation.snapshot_id,
        snapshot_sha256=observation.snapshot_sha256,
        raw_observation_id=observation.raw_observation_id,
        observation_revision_id=observation.observation_revision_id,
        normalized_observation_id=observation.normalized_observation_id,
        raw_payload_sha256=observation.raw_payload_sha256,
        normalized_content_sha256=observation.normalized_content_sha256,
        record_type=observation.payload.record_type,
        source_record_id=observation.source_record_id,
        instrument_id=observation.instrument_id,
        listing_id=observation.listing_id,
        available_at_utc=observation.available_at,
        valid_from_utc=observation.valid_from,
        valid_to_utc=observation.valid_to,
    )
    if reference != expected_reference:
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
        if capability is DataCapability.MACRO_REGIME_INPUTS:
            macro_entries = tuple(
                entry
                for entry in indexed.values()
                if entry[0] is capability
                and entry[1].instrument_id is None
                and _available_at_decision(entry[1], row.decision_time_utc)
            )
            if not macro_entries:
                raise ValueError("prepared Family A row lacks PIT macro regime evidence")
            for entry in macro_entries:
                selected[(entry[0], entry[1].normalized_observation_id)] = entry
            continue
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


def _prepared_source_references(value: object) -> tuple[ResearchSourceReference, ...]:
    """Return every exact Phase 4 source reference in a prepared Phase 6 graph."""

    references: dict[tuple[str, str, str], ResearchSourceReference] = {}

    def collect(item: object) -> None:
        if isinstance(item, ResearchSourceReference):
            key = (
                str(item.capability),
                str(item.snapshot_id),
                str(item.normalized_observation_id),
            )
            existing = references.get(key)
            if existing is not None and existing != item:
                raise ValueError("prepared source identity resolves to conflicting lineage")
            references[key] = item
            return
        if isinstance(item, BaseModel):
            for field_name in type(item).model_fields:
                collect(getattr(item, field_name))
            return
        if isinstance(item, dict):
            for nested in item.values():
                collect(nested)
            return
        if isinstance(item, tuple | list | set | frozenset):
            for nested in item:
                collect(nested)

    collect(value)
    return tuple(references[key] for key in sorted(references))


def _phase5_rows_with_real_confirmation(
    prepared: PreparedResearchPipeline,
) -> tuple[tuple[ResearchFeatureRow, ...], tuple[str, ...], tuple[str, ...]]:
    """Return research rows plus exact predeclared, label-blind exclusion identities."""

    rows = prepared.feature_rows
    confirmation = prepared.confirmation_interval
    boundary_ids = tuple(item.sample_id for item in prepared.boundary_exclusions)
    if not rows or any(item.label_t1_utc >= confirmation.interval_start_utc for item in rows):
        raise ValueError("prepared research labels overlap the final confirmation interval")
    if confirmation.label_opened or any(item.label_opened for item in prepared.boundary_exclusions):
        raise ValueError("Phase 6 confirmation labels must remain unopened")
    return rows, (confirmation.sample_id,), boundary_ids


def _family_b_daily_volatility(row: ResearchFeatureRow) -> Decimal:
    features = tuple(item for item in row.features if item.feature_name == "realized_volatility")
    if len(features) != 1:
        raise ValueError("Family B requires one prepared realized-volatility feature per sample")
    feature = features[0]
    if feature.formula_id != "action-aware-252-session-realized-volatility-v1":
        raise ValueError("Family B realized-volatility formula differs from the frozen contract")
    if feature.raw_value <= 0:
        raise ValueError("Family B source-derived realized volatility must be positive")
    # Preserve the exact PIT feature above, but project the separate compatibility
    # input consumed by the frozen Phase 5 cost model onto its persisted numeric
    # contract.  Eight decimals is the finest predeclared quantum that keeps all
    # component, total, and net cost values exactly representable at scale 30.
    with localcontext() as decimal_context:
        decimal_context.prec = 80
        projected = feature.raw_value.quantize(
            FAMILY_B_COST_VOLATILITY_QUANTUM,
            rounding=ROUND_HALF_EVEN,
        )
    if projected <= 0:
        raise ValueError("Family B cost-volatility projection must remain positive")
    return projected


def _research_participation(prepared: PreparedResearchPipeline) -> Decimal:
    inputs = prepared.family_inputs
    if isinstance(inputs, PreparedFamilyAInputs):
        participation = inputs.capacity.adv_participation
        if participation <= 0:
            raise ValueError("Family A declared ADV participation must be positive")
        return participation
    return _DEFAULT_SYNTHETIC_PARTICIPATION


def _regime_projection(
    prepared: PreparedResearchPipeline,
    decision_time_utc: datetime,
) -> tuple[datetime, Decimal, tuple[str, ...]]:
    evidence = prepared.regime_evidence
    if evidence.evidence_state == "unavailable":
        return decision_time_utc, Decimal("0"), ()
    available_rates = tuple(
        item for item in evidence.rate_observations if item.released_at_utc <= decision_time_utc
    )
    if not available_rates:
        raise ValueError("no vintage-aware rate observation is available at the decision")
    rate = max(available_rates, key=lambda item: (item.released_at_utc, item.vintage_id))
    crisis_window_ids = tuple(
        item.crisis_window_id
        for item in evidence.crisis_windows
        if item.window_start_utc <= decision_time_utc <= item.window_end_utc
    )
    return rate.released_at_utc, rate.rate_change, crisis_window_ids


def _confirmation_sample(
    *,
    prepared: PreparedResearchPipeline,
    policy: FrozenEvaluationPolicy,
    indexed: dict[tuple[DataCapability, UUID], SourceEntry],
) -> tuple[SyntheticSample, tuple[SourceEntry, ...], tuple[DataCapability, UUID]]:
    confirmation = prepared.confirmation_interval
    reference_entries = tuple(
        _entry_for_reference(reference, indexed) for reference in confirmation.source_references
    )
    anchors = tuple(
        entry
        for entry in reference_entries
        if entry[0] is DataCapability.OHLCV
        and isinstance(entry[1].payload, OhlcvBarPayload)
        and entry[1].payload.adjustment_basis.value == "raw_unadjusted"
        and _available_at_decision(entry[1], confirmation.interval_start_utc)
    )
    if not anchors:
        raise ValueError("label-blind confirmation geometry lacks a PIT OHLCV audit anchor")
    anchor_entry = max(
        anchors,
        key=lambda item: (item[1].available_at, item[1].source_record_id),
    )
    anchor = anchor_entry[1]
    anchor_payload = anchor.payload
    if not isinstance(anchor_payload, OhlcvBarPayload) or anchor_payload.open == 0:
        raise ValueError("confirmation audit anchor must be a nonzero raw OHLCV observation")
    selected: dict[tuple[DataCapability, UUID], SourceEntry] = {
        (entry[0], entry[1].normalized_observation_id): entry
        for entry in reference_entries
        if _available_at_decision(entry[1], confirmation.interval_start_utc)
        and entry[0] is not DataCapability.AS_REPORTED_FUNDAMENTALS
        and (entry[1].instrument_id is None or _same_identity(entry[1], anchor))
    }
    fundamental_entries = tuple(
        entry
        for entry in reference_entries
        if entry[0] is DataCapability.AS_REPORTED_FUNDAMENTALS
        and _same_identity(entry[1], anchor)
        and _available_at_decision(entry[1], confirmation.interval_start_utc)
    )
    if DataCapability.AS_REPORTED_FUNDAMENTALS in policy.required_snapshot_capabilities:
        if not fundamental_entries:
            raise ValueError("confirmation audit anchor lacks as-reported evidence")
        fundamental = min(
            fundamental_entries,
            key=lambda entry: (entry[1].available_at, entry[1].source_record_id),
        )
        selected[(fundamental[0], fundamental[1].normalized_observation_id)] = fundamental
    membership_matches = tuple(
        entry
        for entry in indexed.values()
        if entry[0] is DataCapability.UNIVERSE_MEMBERSHIP
        and isinstance(entry[1].payload, UniverseMembershipPayload)
        and entry[1].payload.status.value == "included"
        and _same_identity(entry[1], anchor)
        and _available_at_decision(entry[1], confirmation.interval_start_utc)
    )
    if len(membership_matches) != 1:
        raise ValueError("confirmation audit anchor requires one exact PIT universe membership")
    membership_entry = membership_matches[0]
    selected[(membership_entry[0], membership_entry[1].normalized_observation_id)] = (
        membership_entry
    )
    if DataCapability.MACRO_REGIME_INPUTS in policy.required_snapshot_capabilities:
        macro_entries = tuple(
            entry
            for entry in indexed.values()
            if entry[0] is DataCapability.MACRO_REGIME_INPUTS
            and _available_at_decision(entry[1], confirmation.interval_start_utc)
        )
        if not macro_entries:
            raise ValueError("confirmation geometry lacks available macro regime evidence")
        for entry in macro_entries:
            selected[(entry[0], entry[1].normalized_observation_id)] = entry
    ordered = tuple(
        selected[key] for key in sorted(selected, key=lambda item: (str(item[0]), str(item[1])))
    )
    feature_available = max(max(item[1].event_time, item[1].available_at) for item in ordered)
    membership_observation = membership_entry[1]
    membership_payload = membership_observation.payload
    if not isinstance(membership_payload, UniverseMembershipPayload):
        raise ValueError("confirmation membership payload is invalid")
    derivation_content = {
        "schema_version": PHASE6_SOURCE_FEATURE_DERIVATION_SCHEMA_VERSION,
        "formula_id": PHASE6_SOURCE_FEATURE_DERIVATION_FORMULA,
        "source_observation_key": SourceObservationKey(
            capability=DataCapability.OHLCV,
            normalized_observation_id=anchor.normalized_observation_id,
        ),
        "source_payload_field": "open",
        "multiplier": Decimal("0"),
        "derived_feature_value": Decimal("0"),
    }
    rate_available_at, rate_change, crisis_window_ids = _regime_projection(
        prepared,
        confirmation.interval_start_utc,
    )
    daily_adv_units = anchor_payload.volume * Decimal("0.1")
    sample = SyntheticSample(
        sample_id=confirmation.sample_id,
        source_observation_keys=tuple(
            SourceObservationKey(
                capability=capability,
                normalized_observation_id=observation.normalized_observation_id,
            )
            for capability, observation, _disposition in ordered
        ),
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
        decision_time_utc=confirmation.interval_start_utc,
        feature_available_at_utc=feature_available,
        label_t0_utc=confirmation.interval_start_utc,
        label_t1_utc=confirmation.interval_end_utc,
        feature_value=Decimal("0"),
        predicted_value=Decimal("0"),
        return_status=ResearchReturnStatus.NO_TRADE,
        gross_return=Decimal("0"),
        research_allocation_units=Decimal("0"),
        reference_price=anchor_payload.open,
        daily_adv_units=daily_adv_units,
        daily_volatility=Decimal("0.015"),
        fee_rate=Decimal("0.00005"),
        half_spread_rate=Decimal("0.00010"),
        impact_coefficient=Decimal("0.005"),
        latency_rate=Decimal("0.00005"),
        borrow_rate=Decimal("0.00002"),
        borrow_applicable=False,
        hard_to_borrow_available=True,
        independent_event_id=f"{confirmation.sample_id}-sealed-event",
        regime_id="sealed-label-blind-confirmation",
        rate_available_at_utc=rate_available_at,
        rate_change=rate_change,
        crisis_window_ids=crisis_window_ids,
        gross_exposure=Decimal("0"),
        net_exposure=Decimal("0"),
        sector_exposure=Decimal("0"),
        turnover=Decimal("0"),
        price_adjustment_basis="raw_unadjusted",
        adjustment_action_as_of_utc=anchor_payload.adjustment_as_of,
        fundamental_revision=_fundamental_evidence(ordered),
        feature_dependency_ids=(source_feature_dependency_id(DataCapability.OHLCV, "open"),),
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
    return sample, ordered, (DataCapability.OHLCV, anchor.normalized_observation_id)


def _samples_and_expectations(
    *,
    prepared: PreparedResearchPipeline,
    policy: FrozenEvaluationPolicy,
    snapshots: tuple[SnapshotBundle, ...],
    rows: tuple[ResearchFeatureRow, ...] | None = None,
) -> tuple[tuple[SyntheticSample, ...], tuple[SyntheticSourceObservationExpectation, ...]]:
    indexed = _source_index(snapshots)
    score_by_sample = {item.sample_id: item for item in prepared.scores}
    primary_output = next(
        (item for item in prepared.model_output_sets if item.trial_key == "prepared-primary"),
        None,
    )
    if primary_output is None:
        raise ValueError("prepared pipeline lacks its primary model-output registry")
    primary_cells = {item.sample_id: item for item in primary_output.ledger_cells}
    expectation_entries: dict[tuple[DataCapability, UUID], SourceEntry] = {}
    anchor_keys: set[tuple[DataCapability, UUID]] = set()
    samples: list[SyntheticSample] = []
    selected_rows = prepared.feature_rows if rows is None else rows
    participation = _research_participation(prepared)
    if participation > policy.costs.baseline_max_participation:
        raise ValueError("prepared participation exceeds the frozen Phase 5 capacity limit")
    for index, row in enumerate(selected_rows):
        score = score_by_sample.get(row.sample_id)
        if score is None or score.research_score != row.composite_score:
            raise ValueError("prepared score output does not match its exact feature row")
        primary_cell = primary_cells.get(row.sample_id)
        if primary_cell is None or primary_cell.model_output != score.research_score:
            raise ValueError("prepared primary output does not match its exact score row")
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
        family_b = prepared.family is CanonicalFamily.B_TIME_SERIES_MOMENTUM_REGIME
        high_volatility = index >= len(selected_rows) - 4
        daily_volatility = (
            _family_b_daily_volatility(row)
            if family_b
            else (Decimal("0.025") if high_volatility else Decimal("0.015"))
        )
        daily_adv_units = anchor_payload.volume * Decimal("0.1")
        rate_available_at, rate_change, crisis_window_ids = _regime_projection(
            prepared,
            row.decision_time_utc,
        )
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
                predicted_value=primary_cell.model_output,
                gross_return=primary_cell.synthetic_gross_return,
                # Family A's declared capacity evidence is a one-percent ADV research
                # assumption, so its Phase 5 cost ledger must evaluate that exact same
                # participation. Other families retain the smaller legacy QA input.
                research_allocation_units=daily_adv_units * participation,
                reference_price=anchor_payload.open,
                daily_adv_units=daily_adv_units,
                daily_volatility=daily_volatility,
                fee_rate=Decimal("0.00005"),
                half_spread_rate=Decimal("0.00010"),
                impact_coefficient=Decimal("0.005"),
                latency_rate=Decimal("0.00005"),
                borrow_rate=Decimal("0.00002"),
                borrow_applicable=False,
                hard_to_borrow_available=True,
                independent_event_id=f"{row.sample_id}-prepared-event",
                regime_id=(
                    "source-derived-volatility-rate-and-crisis-unavailable"
                    if family_b
                    else (
                        "synthetic-high-vol-pit-rate-and-crisis"
                        if high_volatility
                        else "synthetic-low-vol-pit-rate-and-crisis"
                    )
                ),
                rate_available_at_utc=rate_available_at,
                rate_change=rate_change,
                crisis_window_ids=crisis_window_ids,
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

    confirmation_sample, confirmation_entries, confirmation_anchor_key = _confirmation_sample(
        prepared=prepared,
        policy=policy,
        indexed=indexed,
    )
    samples.append(confirmation_sample)
    anchor_keys.add(confirmation_anchor_key)
    for entry in confirmation_entries:
        expectation_entries[(entry[0], entry[1].normalized_observation_id)] = entry

    for reference in _prepared_source_references(prepared):
        entry = _entry_for_reference(reference, indexed)
        expectation_entries[(entry[0], entry[1].normalized_observation_id)] = entry

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


def _report_scope_source_evidence(
    *,
    prepared: PreparedResearchPipeline,
    samples: tuple[SyntheticSample, ...],
    expectations: tuple[SyntheticSourceObservationExpectation, ...],
) -> tuple[ReportScopeSourceEvidence, ...]:
    def reference_key(reference: ResearchSourceReference) -> tuple[DataCapability, UUID]:
        return reference.capability, reference.normalized_observation_id

    consumed = {
        (item.capability, item.normalized_observation_id)
        for sample in samples
        for item in sample.source_observation_keys
    }
    unused = tuple(
        item
        for item in expectations
        if (item.key.capability, item.key.normalized_observation_id) not in consumed
    )
    references = {reference_key(item): item for item in _prepared_source_references(prepared)}
    label_keys = {
        reference_key(reference)
        for row in prepared.feature_rows
        for reference in row.label_source_references
    } | {
        reference_key(reference)
        for output_set in prepared.model_output_sets
        for cell in output_set.ledger_cells
        for reference in cell.label_source_references
    }
    fit_keys: set[tuple[DataCapability, UUID]] = set()
    if isinstance(prepared.family_inputs, PreparedFamilyAInputs):
        fit_keys = {
            reference_key(reference)
            for fit in prepared.family_inputs.train_only_sector_fits
            for reference in fit.source_references
        }
        label_keys.update(
            reference_key(reference)
            for section in prepared.family_inputs.cross_section_ranks
            for member in section.eligible_members
            for reference in member.label_source_references
        )
    by_role: dict[ReportScopeSourceRole, list[SourceObservationKey]] = {}
    for expectation in unused:
        key = (expectation.key.capability, expectation.key.normalized_observation_id)
        reference = references.get(key)
        if reference is None:
            raise ValueError("report-scope expectation is absent from the prepared source graph")
        if key in fit_keys:
            role = ReportScopeSourceRole.TRAIN_ONLY_TRANSFORM
        elif key in label_keys:
            role = ReportScopeSourceRole.PREPARED_LABEL_GRAPH
        elif reference.record_type == "calendar_session":
            role = ReportScopeSourceRole.PREPARED_LABEL_GRAPH
        elif reference.record_type in {
            "official_document_content",
            "official_event_metadata",
            "social_attention",
        }:
            role = ReportScopeSourceRole.OFFICIAL_CORROBORATION
        elif reference.record_type in {
            "corporate_action",
            "delisting_event",
            "security_master",
            "universe_membership",
        }:
            role = ReportScopeSourceRole.LIFECYCLE_TEST
        else:
            role = ReportScopeSourceRole.PREPARED_FEATURE_GRAPH
        by_role.setdefault(role, []).append(expectation.key)

    evidence: list[ReportScopeSourceEvidence] = []
    for role in sorted(by_role, key=str):
        keys = tuple(
            sorted(
                by_role[role],
                key=lambda item: (str(item.capability), str(item.normalized_observation_id)),
            )
        )
        content = {
            "schema_version": "phase6-report-scope-source-evidence-v1",
            "role": role,
            "prepared_pipeline_input_sha256": prepared.pipeline_input_sha256,
            "source_observation_keys": keys,
        }
        evidence.append(
            ReportScopeSourceEvidence.model_validate(
                {
                    **content,
                    "evidence_sha256": domain_sha256(
                        PHASE6_REPORT_SCOPE_SOURCE_EVIDENCE_HASH_DOMAIN,
                        content,
                    ),
                }
            )
        )
    return tuple(evidence)


def _phase6_regime_evidence(
    prepared: PreparedResearchPipeline,
) -> Phase6RegimeEvidenceAvailability:
    evidence = prepared.regime_evidence
    available = evidence.evidence_state == "available"
    content = {
        "schema_version": "phase6-regime-evidence-v2",
        "prepared_pipeline_input_sha256": prepared.pipeline_input_sha256,
        "rate_evidence_available": available,
        "rate_evidence_reason": None if available else "rate_regime_source_unavailable",
        "rate_compatibility_projection": (
            None if available else "zero-at-decision-not-observed-v1"
        ),
        "rate_definition_id": evidence.rate_definition_id if available else None,
        "rate_source_observation_keys": tuple(
            sorted(
                (
                    SourceObservationKey(
                        capability=item.source_reference.capability,
                        normalized_observation_id=(item.source_reference.normalized_observation_id),
                    )
                    for item in evidence.rate_observations
                ),
                key=lambda item: (str(item.capability), str(item.normalized_observation_id)),
            )
        ),
        "crisis_geometry_available": available,
        "crisis_evidence_reason": None if available else "crisis_window_geometry_unavailable",
        "crisis_compatibility_projection": (
            None if available else "empty-membership-not-observed-v1"
        ),
        "crisis_definition_id": evidence.crisis_definition_id if available else None,
        "crisis_window_ids": tuple(item.crisis_window_id for item in evidence.crisis_windows),
        "crisis_source_observation_keys": tuple(
            sorted(
                (
                    SourceObservationKey(
                        capability=item.source_reference.capability,
                        normalized_observation_id=(item.source_reference.normalized_observation_id),
                    )
                    for item in evidence.crisis_windows
                ),
                key=lambda item: (str(item.capability), str(item.normalized_observation_id)),
            )
        ),
    }
    return Phase6RegimeEvidenceAvailability.model_validate(
        {
            **content,
            "evidence_sha256": domain_sha256(
                PHASE6_REGIME_EVIDENCE_HASH_DOMAIN,
                content,
            ),
        }
    )


def _fixture(
    *,
    fixture_id: str,
    expectations: tuple[SyntheticSourceObservationExpectation, ...],
    report_scope_source_evidence: tuple[ReportScopeSourceEvidence, ...],
    phase6_regime_evidence: Phase6RegimeEvidenceAvailability,
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
        "report_scope_source_evidence": report_scope_source_evidence,
        "phase6_regime_evidence": phase6_regime_evidence,
        "samples": samples,
        "trials": trials,
        "warnings": (
            "All labels, scores, and returns are deterministic synthetic research evidence, "
            "not real performance.",
            "Every Phase 5 sample is bound to its exact prepared Phase 6 row and immutable "
            "Phase 4 source evidence.",
            "The final confirmation interval is a label-blind no-trade geometry placeholder; "
            "its label value and sources remain unopened and crossing rows are excluded.",
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


def _trials(
    *,
    prepared: PreparedResearchPipeline,
    policy: FrozenEvaluationPolicy,
    fixture_id: str,
    expectations: tuple[SyntheticSourceObservationExpectation, ...],
    report_scope_source_evidence: tuple[ReportScopeSourceEvidence, ...],
    phase6_regime_evidence: Phase6RegimeEvidenceAvailability,
    samples: tuple[SyntheticSample, ...],
) -> tuple[tuple[SyntheticTrial, ...], dict[str, Decimal]]:
    provisional = _fixture(
        fixture_id=fixture_id,
        expectations=expectations,
        report_scope_source_evidence=report_scope_source_evidence,
        phase6_regime_evidence=phase6_regime_evidence,
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
    common_calendar = tuple(samples_by_id[sample_id].decision_time_utc for sample_id in outer_ids)
    label_sha256 = domain_sha256(
        "phase6-phase5-label-set-v2",
        tuple(
            (row.sample_id, row.label_value, row.label_t0_utc, row.label_t1_utc)
            for row in prepared.feature_rows
        ),
    )

    completed: list[SyntheticTrial] = []
    gross_by_trial: dict[str, dict[str, Decimal]] = {}
    net_by_trial: dict[str, dict[str, Decimal]] = {}
    output_by_trial: dict[str, dict[str, Decimal]] = {}
    research_samples = tuple(samples_by_id[row.sample_id] for row in prepared.feature_rows)
    for output_set in prepared.model_output_sets:
        cells = {item.sample_id: item for item in output_set.ledger_cells}
        outputs = {item.sample_id: item.output_value for item in output_set.outputs}
        required_ids = set(inner_ids) | set(outer_ids)
        if not required_ids.issubset(cells) or set(cells) != set(outputs):
            raise ValueError("prepared model-output registry does not cover Phase 5 geometry")
        inner_evidence = {
            sample_id: cells[sample_id].synthetic_gross_return for sample_id in inner_ids
        }
        outer_evidence = {
            sample_id: cells[sample_id].synthetic_gross_return for sample_id in outer_ids
        }
        weights = {sample_id: cell.synthetic_research_weight for sample_id, cell in cells.items()}
        allocation_rules = {sample_id: cell.allocation_rule_id for sample_id, cell in cells.items()}
        labels = {sample_id: cell.label_value for sample_id, cell in cells.items()}
        trial_costs = build_long_flat_trial_costs(
            research_samples,
            weights=weights,
            label_returns=labels,
            cost_policy=policy.costs,
            stress_policy=policy.stress,
        )
        baseline_entries = {
            item.sample_id: item
            for item in trial_costs.cost_ledger
            if item.scenario is CostScenario.BASELINE
        }
        statuses = {sample_id: cells[sample_id].return_status for sample_id in inner_ids}
        outer_statuses = {sample_id: cells[sample_id].return_status for sample_id in outer_ids}
        net_returns_by_sample = {
            sample_id: baseline_entries[sample_id].net_return
            for sample_id in set(inner_ids) | set(outer_ids)
        }
        cost_set_sha256 = domain_sha256(
            PHASE6_TRIAL_COST_SET_HASH_DOMAIN,
            tuple(
                (item.sample_id, item.scenario, item.cost_entry_sha256)
                for item in trial_costs.cost_ledger
            ),
        )
        ledger_set_sha256 = domain_sha256(
            "phase6-phase5-ledger-cell-set-v2",
            tuple((item.cell_id, item.cell_sha256) for item in output_set.ledger_cells),
        )
        gross_by_trial[output_set.trial_key] = {
            item.sample_id: item.synthetic_gross_return for item in output_set.ledger_cells
        }
        net_by_trial[output_set.trial_key] = net_returns_by_sample
        output_by_trial[output_set.trial_key] = outputs
        trial_configuration = {
            "model": output_set.model_id,
            "variant": str(output_set.ordinal),
            "phase6_pipeline_input_sha256": prepared.pipeline_input_sha256,
            "phase6_model_output_sha256": output_set.model_output_sha256,
            "phase6_output_set_sha256": output_set.output_set_sha256,
            "phase6_label_sha256": label_sha256,
            "phase6_ledger_cell_set_sha256": ledger_set_sha256,
            "phase6_payoff_formula_id": ("phase6-long-flat-weight-times-label-quantized-v1"),
            "phase6_allocation_rules_json": canonical_json_text(allocation_rules),
            "phase6_trial_weights_json": canonical_json_text(weights),
            "phase6_trial_cost_ledger_json": canonical_json_text(trial_costs.cost_ledger),
            "phase6_trial_cost_set_sha256": cost_set_sha256,
            "inner_validation_gross_returns_json": canonical_json_text(inner_evidence),
            "inner_validation_return_statuses_json": canonical_json_text(statuses),
            "outer_gross_returns_json": canonical_json_text(outer_evidence),
        }
        if prepared.family is CanonicalFamily.B_TIME_SERIES_MOMENTUM_REGIME:
            trial_configuration.update(
                {
                    "phase6_cost_volatility_projection_id": (
                        FAMILY_B_COST_VOLATILITY_PROJECTION_ID
                    ),
                    "phase6_cost_volatility_quantum": (FAMILY_B_COST_VOLATILITY_QUANTUM_TEXT),
                }
            )
        completed.append(
            SyntheticTrial(
                trial_key=output_set.trial_key,
                status=TrialStatus.COMPLETED,
                configuration=trial_configuration,
                net_returns=tuple(net_returns_by_sample[sample_id] for sample_id in outer_ids),
                return_statuses=tuple(outer_statuses[sample_id] for sample_id in outer_ids),
                return_timestamps_utc=common_calendar,
                initiated_by="phase6-prepared-trial-registry",
                initiated_at_utc=datetime(
                    2026,
                    1,
                    1,
                    0,
                    output_set.ordinal,
                    tzinfo=UTC,
                ),
            )
        )

    selected_predictions: dict[str, Decimal] = {}
    for outer_fold in outer_folds:
        validation_ids = tuple(
            sample_id
            for fold in geometry.folds
            if fold.fold_kind is FoldKind.INNER and fold.parent_fold_id == outer_fold.fold_id
            for sample_id in fold.test_sample_ids
        )
        if not validation_ids:
            raise ValueError("prepared model selection lacks inner validation evidence")
        selection_scores = {
            trial_key: sum(
                (net_by_trial[trial_key][sample_id] for sample_id in validation_ids),
                Decimal("0"),
            )
            / Decimal(len(validation_ids))
            for trial_key in gross_by_trial
        }
        best = max(selection_scores.values())
        winners = tuple(trial_key for trial_key, value in selection_scores.items() if value == best)
        if len(winners) != 1:
            raise ValueError("prepared inner validation model selection is tied")
        selected_key = winners[0]
        for sample_id in outer_fold.test_sample_ids:
            selected_predictions[sample_id] = output_by_trial[selected_key][sample_id]
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
    return (*completed, *incomplete), selected_predictions


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
    verify_prepared_pipeline_reproduction(configuration_id, snapshots, prepared)
    _validate_prepared_snapshots(prepared, snapshots)
    evaluation_rows, confirmation_ids, boundary_purged_ids = _phase5_rows_with_real_confirmation(
        prepared
    )
    confirmation_start = prepared.confirmation_interval.interval_start_utc
    confirmation_end = prepared.confirmation_interval.interval_end_utc
    policy = build_phase5_policy(
        configuration_id=configuration_id,
        capabilities=prepared.specification.required_capabilities,
        origin=prepared.feature_rows[0].decision_time_utc,
        confirmation_start_utc=confirmation_start,
        confirmation_end_utc=confirmation_end,
    )
    samples, expectations = _samples_and_expectations(
        prepared=prepared,
        policy=policy,
        snapshots=snapshots,
        rows=evaluation_rows,
    )
    report_scope_source_evidence = _report_scope_source_evidence(
        prepared=prepared,
        samples=samples,
        expectations=expectations,
    )
    regime_evidence = _phase6_regime_evidence(prepared)
    fixture_id = f"{configuration_id.value}-{prepared.pipeline_input_sha256[:24]}"
    trials, selected_predictions = _trials(
        prepared=prepared,
        policy=policy,
        fixture_id=fixture_id,
        expectations=expectations,
        report_scope_source_evidence=report_scope_source_evidence,
        phase6_regime_evidence=regime_evidence,
        samples=samples,
    )
    samples = tuple(
        sample.model_copy(update={"predicted_value": selected_predictions[sample.sample_id]})
        if sample.sample_id in selected_predictions
        else sample
        for sample in samples
    )
    fixture = _fixture(
        fixture_id=fixture_id,
        expectations=expectations,
        report_scope_source_evidence=report_scope_source_evidence,
        phase6_regime_evidence=regime_evidence,
        samples=samples,
        trials=trials,
    )
    geometry = build_evaluation_geometry(
        policy=policy,
        walk_forward=policy.walk_forward,
        fixture=fixture,
    )
    if not geometry.validation.passed:
        raise ValueError(
            "prepared Phase 6 rows cannot produce complete Phase 5 geometry: "
            + ",".join(geometry.validation.reason_codes)
        )
    if geometry.confirmation_sample_ids != confirmation_ids:
        raise ValueError("Phase 6 final confirmation interval contains no exact prepared sample")
    selected_ids = {
        sample_id
        for fold in geometry.folds
        for sample_id in (
            *fold.train_sample_ids,
            *fold.test_sample_ids,
            *fold.purged_sample_ids,
            *fold.embargoed_sample_ids,
        )
    }
    if selected_ids & set(confirmation_ids):
        raise ValueError("Phase 6 final confirmation sample entered Phase 5 selection")
    fixture_ids = {sample.sample_id for sample in fixture.samples}
    if fixture_ids & set(boundary_purged_ids):
        raise ValueError("Phase 6 confirmation-boundary labels entered the Phase 5 fixture")
    confirmation_times = {
        sample.decision_time_utc
        for sample in fixture.samples
        if sample.sample_id in set(confirmation_ids)
    }
    if any(
        timestamp in confirmation_times
        for trial in fixture.trials
        if trial.status is TrialStatus.COMPLETED
        for timestamp in trial.return_timestamps_utc
    ):
        raise ValueError("Phase 6 final confirmation sample entered a completed trial calendar")
    return policy, fixture


__all__ = [
    "build_phase5_inputs",
    "build_phase5_policy",
    "configuration_family",
    "configuration_is_cost_failure",
    "configuration_is_crash_failure",
]
