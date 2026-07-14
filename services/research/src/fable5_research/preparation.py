"""Deterministic pre-evaluation preparation from immutable Phase 4 snapshots."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Final
from uuid import UUID

from fable5_data.contracts import (
    AUTHORIZED_CAPABILITIES,
    AdjustmentBasis,
    AsReportedFundamentalPayload,
    CorporateActionPayload,
    CorporateActionType,
    DataCapability,
    DelistingEventPayload,
    DelistingReturnInclusion,
    ListingIdentityPayload,
    NormalizedObservation,
    OfficialDocumentContentPayload,
    OhlcvBarPayload,
    SectorClassificationPayload,
    SnapshotBundle,
    SocialAttentionPayload,
    UniverseMembershipPayload,
    VolatilityReturnInputPayload,
)
from fable5_mapping.models import CanonicalFamily

from fable5_research.canonical import (
    PHASE6_BASELINE_HASH_DOMAIN,
    PHASE6_COMPARISON_NAMESPACE,
    PHASE6_CORROBORATION_HASH_DOMAIN,
    PHASE6_CORROBORATION_NAMESPACE,
    PHASE6_CROSS_SECTION_MEMBER_HASH_DOMAIN,
    PHASE6_CROSS_SECTION_RANK_HASH_DOMAIN,
    PHASE6_EXPLANATION_HASH_DOMAIN,
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
    PHASE6_SCORE_HASH_DOMAIN,
    PHASE6_SCORE_NAMESPACE,
    PHASE6_SNAPSHOT_BINDING_HASH_DOMAIN,
    PHASE6_TEXT_EXTRACTION_HASH_DOMAIN,
    PHASE6_TRANSFORM_FIT_HASH_DOMAIN,
    domain_sha256,
    identity,
)
from fable5_research.contracts import (
    BaselineOutcome,
    CapacityEvidence,
    CrossSectionRankEvidence,
    CrossSectionRankMember,
    LaggedOhlcvBaselineEvidence,
    LifecycleEvidence,
    LifecycleTestEvidence,
    PreparedFamilyAInputs,
    PreparedFamilyBInputs,
    PreparedFamilyCInputs,
    PreparedResearchPipeline,
    ResearchBaselineComparison,
    ResearchConfigurationId,
    ResearchFeatureRow,
    ResearchFeatureValue,
    ResearchScoreOutput,
    ResearchSnapshotBinding,
    ResearchSourceReference,
    ResearchTransformFit,
    SocialOfficialCorroboration,
    StructuredTextFeatures,
    TextFeatureExtraction,
    UniverseSecurityEvidence,
    frozen_depth_two_tree_score,
)
from fable5_research.specification import build_specification

_A_FEATURES: Final = (
    "liquidity",
    "momentum",
    "quality",
    "turnover",
    "value",
    "volatility",
)
_B_WINDOWS: Final = (1, 5, 20, 63, 126, 252)
_Q: Final = Decimal("0.000000000001")


def _q(value: Decimal) -> Decimal:
    return value.quantize(_Q)


def _family(configuration_id: ResearchConfigurationId) -> CanonicalFamily:
    if configuration_id in {ResearchConfigurationId.A_PASS, ResearchConfigurationId.A_FAIL}:
        return CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING
    if configuration_id in {ResearchConfigurationId.B_PASS, ResearchConfigurationId.B_FAIL}:
        return CanonicalFamily.B_TIME_SERIES_MOMENTUM_REGIME
    return CanonicalFamily.C_OFFICIAL_EVENT_TEXT_OVERLAY


def _observations(snapshots: tuple[SnapshotBundle, ...]) -> tuple[NormalizedObservation, ...]:
    return tuple(
        observation for bundle in snapshots for observation in bundle.normalized_observations
    )


def _reference(
    observation: NormalizedObservation,
    capability_by_snapshot: dict[UUID, DataCapability],
) -> ResearchSourceReference:
    return ResearchSourceReference(
        capability=capability_by_snapshot[observation.snapshot_id],
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


def _reference_key(item: ResearchSourceReference) -> tuple[str, str, str]:
    return str(item.capability), str(item.snapshot_id), str(item.normalized_observation_id)


def _refs(
    values: tuple[NormalizedObservation, ...] | list[NormalizedObservation],
    capability_by_snapshot: dict[UUID, DataCapability],
) -> tuple[ResearchSourceReference, ...]:
    unique = {
        item.normalized_observation_id: _reference(item, capability_by_snapshot) for item in values
    }
    return tuple(sorted(unique.values(), key=_reference_key))


def _bindings(snapshots: tuple[SnapshotBundle, ...]) -> tuple[ResearchSnapshotBinding, ...]:
    result: list[ResearchSnapshotBinding] = []
    ordered = sorted(
        snapshots,
        key=lambda item: str(item.snapshot.manifest.payload.request.capability),
    )
    for ordinal, bundle in enumerate(ordered, start=1):
        snapshot = bundle.snapshot
        manifest = snapshot.manifest.payload
        content = {
            "ordinal": ordinal,
            "snapshot_id": snapshot.snapshot_id,
            "snapshot_sha256": snapshot.snapshot_sha256,
            "capability": manifest.request.capability,
            "mapping_id": manifest.mapping.mapping_id,
            "mapping_input_sha256": manifest.mapping.mapping_input_sha256,
            "as_of_utc": manifest.request.as_of_utc,
            "quality_status": snapshot.quality_status.value,
        }
        result.append(
            ResearchSnapshotBinding.model_validate(
                {
                    **content,
                    "binding_sha256": domain_sha256(
                        PHASE6_SNAPSHOT_BINDING_HASH_DOMAIN,
                        content,
                    ),
                }
            )
        )
    return tuple(result)


def _validated_inputs(
    configuration_id: ResearchConfigurationId,
    snapshots: tuple[SnapshotBundle, ...],
) -> tuple[
    CanonicalFamily,
    tuple[ResearchSnapshotBinding, ...],
    tuple[NormalizedObservation, ...],
    dict[UUID, DataCapability],
]:
    family = _family(configuration_id)
    if not snapshots:
        raise ValueError("prepared research requires immutable snapshots")
    capabilities = tuple(
        sorted(
            (item.snapshot.manifest.payload.request.capability for item in snapshots),
            key=str,
        )
    )
    expected = tuple(sorted(AUTHORIZED_CAPABILITIES[family], key=str))
    if capabilities != expected or len(capabilities) != len(set(capabilities)):
        raise ValueError("prepared research requires the exact authorized capability set")
    mappings = {item.snapshot.manifest.payload.mapping for item in snapshots}
    if len(mappings) != 1 or next(iter(mappings)).canonical_family is not family:
        raise ValueError("prepared snapshots must share the authorized family mapping")
    capability_by_snapshot = {
        item.snapshot.snapshot_id: item.snapshot.manifest.payload.request.capability
        for item in snapshots
    }
    return family, _bindings(snapshots), _observations(snapshots), capability_by_snapshot


def _bars(
    observations: tuple[NormalizedObservation, ...],
    instrument_id: UUID,
) -> tuple[NormalizedObservation, ...]:
    values = tuple(
        item
        for item in observations
        if item.instrument_id == instrument_id
        and isinstance(item.payload, OhlcvBarPayload)
        and item.payload.adjustment_basis is AdjustmentBasis.RAW_UNADJUSTED
    )
    return tuple(sorted(values, key=lambda item: _bar_payload(item).bar_end))


def _actions(
    observations: tuple[NormalizedObservation, ...],
    instrument_id: UUID,
) -> tuple[NormalizedObservation, ...]:
    return tuple(
        sorted(
            (
                item
                for item in observations
                if item.instrument_id == instrument_id
                and isinstance(item.payload, CorporateActionPayload)
            ),
            key=lambda item: _action_payload(item).effective_at,
        )
    )


def _bar_payload(observation: NormalizedObservation) -> OhlcvBarPayload:
    payload = observation.payload
    if not isinstance(payload, OhlcvBarPayload):
        raise ValueError("expected an OHLCV observation")
    return payload


def _action_payload(observation: NormalizedObservation) -> CorporateActionPayload:
    payload = observation.payload
    if not isinstance(payload, CorporateActionPayload):
        raise ValueError("expected a corporate-action observation")
    return payload


def _listing_payload(observation: NormalizedObservation) -> ListingIdentityPayload:
    payload = observation.payload
    if not isinstance(payload, ListingIdentityPayload):
        raise ValueError("expected a listing observation")
    return payload


def _social_payload(observation: NormalizedObservation) -> SocialAttentionPayload:
    payload = observation.payload
    if not isinstance(payload, SocialAttentionPayload):
        raise ValueError("expected a social-attention observation")
    return payload


def _adjusted_return(
    start: NormalizedObservation,
    end: NormalizedObservation,
    actions: tuple[NormalizedObservation, ...],
) -> Decimal:
    start_payload = _bar_payload(start)
    end_payload = _bar_payload(end)
    terminal_value = end_payload.close
    for observation in actions:
        payload = observation.payload
        if not isinstance(payload, CorporateActionPayload):
            raise ValueError("expected a corporate-action observation")
        if start_payload.bar_end < payload.effective_at <= end_payload.bar_end:
            if payload.action_type is CorporateActionType.SPLIT:
                if payload.split_ratio is None:
                    raise ValueError("split return is not computable")
                terminal_value *= payload.split_ratio
            elif payload.action_type is CorporateActionType.CASH_DIVIDEND:
                if payload.cash_amount is None:
                    raise ValueError("dividend return is not computable")
                terminal_value += payload.cash_amount
    return _q(terminal_value / start_payload.close - Decimal("1"))


def _period_action_observations(
    start: NormalizedObservation,
    end: NormalizedObservation,
    actions: tuple[NormalizedObservation, ...],
) -> tuple[NormalizedObservation, ...]:
    start_time = _bar_payload(start).bar_end
    end_time = _bar_payload(end).bar_end
    return tuple(
        item
        for item in actions
        if isinstance(item.payload, CorporateActionPayload)
        and start_time < item.payload.effective_at <= end_time
    )


def _mean(values: tuple[Decimal, ...]) -> Decimal:
    if not values:
        raise ValueError("cannot calculate an empty mean")
    return _q(sum(values, Decimal("0")) / Decimal(len(values)))


def _standard_deviation(values: tuple[Decimal, ...]) -> Decimal:
    average = sum(values, Decimal("0")) / Decimal(len(values))
    variance = sum(((item - average) ** 2 for item in values), Decimal("0")) / Decimal(len(values))
    result = variance.sqrt()
    return _q(result) if result > 0 else Decimal("1.000000000000")


def _row(
    *,
    ordinal: int,
    sample_id: str,
    entity_id: str,
    sector_id: str | None,
    decision_time: datetime,
    label_t0: datetime,
    label_t1: datetime,
    label_value: Decimal,
    label_references: tuple[ResearchSourceReference, ...],
    features: tuple[ResearchFeatureValue, ...],
) -> ResearchFeatureRow:
    lineage = domain_sha256(
        PHASE6_FEATURE_LINEAGE_HASH_DOMAIN,
        {
            "feature_source_references": tuple(item.source_references for item in features),
            "label_source_references": label_references,
        },
    )
    content = {
        "schema_version": "phase6-research-feature-row-v1",
        "ordinal": ordinal,
        "sample_id": sample_id,
        "entity_id": entity_id,
        "sector_id": sector_id,
        "decision_time_utc": decision_time,
        "label_t0_utc": label_t0,
        "label_t1_utc": label_t1,
        "label_value": _q(label_value),
        "label_source_references": label_references,
        "features": features,
        "composite_score": _q(sum((item.contribution for item in features), Decimal("0"))),
        "score_semantics": "research_score_only",
        "source_lineage_sha256": lineage,
    }
    digest = domain_sha256(PHASE6_FEATURE_ROW_HASH_DOMAIN, content)
    return ResearchFeatureRow.model_validate(
        {
            **content,
            "row_id": identity(PHASE6_FEATURE_ROW_NAMESPACE, digest),
            "row_sha256": digest,
        }
    )


def _scores(
    family: CanonicalFamily,
    rows: tuple[ResearchFeatureRow, ...],
) -> tuple[ResearchScoreOutput, ...]:
    model_id = {
        CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING: "sector-relative-rank-linear-v1",
        CanonicalFamily.B_TIME_SERIES_MOMENTUM_REGIME: "lagged-trend-linear-v1",
        CanonicalFamily.C_OFFICIAL_EVENT_TEXT_OVERLAY: "conventional-linear-text-overlay-v1",
    }[family]
    result: list[ResearchScoreOutput] = []
    for ordinal, row in enumerate(rows, start=1):
        details = ", ".join(f"{item.feature_name}={item.contribution}" for item in row.features)
        explanation = (
            f"Synthetic explainable research score; exact contributions: {details}. "
            "No action, allocation, approval, or execution meaning."
        )
        content = {
            "schema_version": "phase6-research-score-output-v1",
            "ordinal": ordinal,
            "sample_id": row.sample_id,
            "entity_id": row.entity_id,
            "model_id": model_id,
            "research_score": row.composite_score,
            "score_semantics": "research_score_only",
            "explanation": explanation,
            "explanation_sha256": domain_sha256(
                PHASE6_EXPLANATION_HASH_DOMAIN,
                explanation,
            ),
            "feature_row_id": row.row_id,
        }
        digest = domain_sha256(PHASE6_SCORE_HASH_DOMAIN, content)
        result.append(
            ResearchScoreOutput.model_validate(
                {
                    **content,
                    "score_id": identity(PHASE6_SCORE_NAMESPACE, digest),
                    "output_sha256": digest,
                }
            )
        )
    return tuple(result)


def _output_hash(values: tuple[tuple[str, Decimal], ...]) -> str:
    return domain_sha256(PHASE6_MODEL_OUTPUT_SET_HASH_DOMAIN, values)


def _label_hash(rows: tuple[ResearchFeatureRow, ...]) -> str:
    return domain_sha256(
        PHASE6_LABEL_SET_HASH_DOMAIN,
        tuple((item.sample_id, item.label_value, item.label_source_references) for item in rows),
    )


def _comparison(
    *,
    ordinal: int,
    candidate_model_id: str,
    baseline_model_id: str,
    metric_id: str,
    candidate_outputs: tuple[tuple[str, Decimal], ...],
    baseline_outputs: tuple[tuple[str, Decimal], ...],
    rows: tuple[ResearchFeatureRow, ...],
    candidate_metric: Decimal,
    baseline_metric: Decimal,
    reason_codes: tuple[str, ...],
    label_sha256: str | None = None,
) -> ResearchBaselineComparison:
    outcome = (
        BaselineOutcome.SURVIVES if candidate_metric > baseline_metric else BaselineOutcome.REJECTED
    )
    content = {
        "ordinal": ordinal,
        "candidate_model_id": candidate_model_id,
        "baseline_model_id": baseline_model_id,
        "evaluation_scope": "descriptive_all_prepared_rows_not_used_for_selection",
        "used_for_selection": False,
        "metric_id": metric_id,
        "candidate_metric": _q(candidate_metric),
        "baseline_metric": _q(baseline_metric),
        "candidate_output_sha256": _output_hash(candidate_outputs),
        "baseline_output_sha256": _output_hash(baseline_outputs),
        "label_sha256": label_sha256 or _label_hash(rows),
        "outcome": outcome,
        "reason_codes": reason_codes,
    }
    digest = domain_sha256(PHASE6_BASELINE_HASH_DOMAIN, content)
    return ResearchBaselineComparison.model_validate(
        {
            **content,
            "comparison_id": identity(PHASE6_COMPARISON_NAMESPACE, digest),
            "comparison_sha256": digest,
        }
    )


def _cross_section_output_key(ordinal: int, entity_id: str) -> str:
    return f"cross-section-{ordinal:02d}:{entity_id}"


def _cross_section_outputs(
    cross_sections: tuple[CrossSectionRankEvidence, ...],
    field_name: str,
) -> tuple[tuple[str, Decimal], ...]:
    return tuple(
        (
            _cross_section_output_key(section.ordinal, member.entity_id),
            getattr(member, field_name),
        )
        for section in cross_sections
        for member in section.eligible_members
    )


def _cross_section_label_hash(
    cross_sections: tuple[CrossSectionRankEvidence, ...],
) -> str:
    return domain_sha256(
        PHASE6_LABEL_SET_HASH_DOMAIN,
        tuple(
            (
                section.ordinal,
                member.entity_id,
                member.label_sha256,
            )
            for section in cross_sections
            for member in section.eligible_members
        ),
    )


def _cross_section_concordance(
    outputs: tuple[tuple[str, Decimal], ...],
    cross_sections: tuple[CrossSectionRankEvidence, ...],
) -> Decimal:
    values = dict(outputs)
    points = Decimal("0")
    pairs = 0
    for section in cross_sections:
        members = section.eligible_members
        for index, left in enumerate(members):
            for right in members[index + 1 :]:
                pairs += 1
                score_delta = (
                    values[_cross_section_output_key(section.ordinal, left.entity_id)]
                    - values[_cross_section_output_key(section.ordinal, right.entity_id)]
                )
                label_delta = left.label_value - right.label_value
                if score_delta == 0 or label_delta == 0:
                    points += Decimal("0.5")
                elif (score_delta > 0) == (label_delta > 0):
                    points += Decimal("1")
    return _q(points / Decimal(pairs)) if pairs else Decimal("0")


def _directional_accuracy(
    outputs: tuple[tuple[str, Decimal], ...],
    rows: tuple[ResearchFeatureRow, ...],
) -> Decimal:
    labels = {item.sample_id: item.label_value for item in rows}
    correct = sum(
        1
        for sample_id, value in outputs
        if value != 0 and labels[sample_id] != 0 and (value > 0) == (labels[sample_id] > 0)
    )
    return _q(Decimal(correct) / Decimal(len(outputs)))


def _raw_a_feature_values(
    *,
    bars: tuple[NormalizedObservation, ...],
    index: int,
    actions: tuple[NormalizedObservation, ...],
    fundamentals: dict[str, NormalizedObservation],
    capability_by_snapshot: dict[UUID, DataCapability],
) -> dict[str, tuple[Decimal, tuple[ResearchSourceReference, ...]]]:
    if index < 20:
        raise ValueError("Family A requires at least 20 historical sessions")
    window = bars[index - 20 : index + 1]
    current = bars[index]
    current_payload = _bar_payload(current)
    returns = tuple(
        _adjusted_return(window[position - 1], window[position], actions)
        for position in range(1, len(window))
    )
    action_window = _period_action_observations(window[0], current, actions)
    market_refs = _refs(list(window) + list(action_window), capability_by_snapshot)
    close_volume = tuple(
        _bar_payload(item).close * _bar_payload(item).volume for item in window[1:]
    )
    volume = tuple(_bar_payload(item).volume for item in window[1:])
    required = {"net_income", "book_equity", "shares_outstanding"}
    if not required.issubset(fundamentals):
        raise ValueError("Family A as-reported quality/value inputs are incomplete")
    net_income = fundamentals["net_income"]
    book_equity = fundamentals["book_equity"]
    shares = fundamentals["shares_outstanding"]
    typed_fundamentals: dict[str, Decimal] = {}
    for name, observation in (
        ("net_income", net_income),
        ("book_equity", book_equity),
        ("shares_outstanding", shares),
    ):
        payload = observation.payload
        if not isinstance(payload, AsReportedFundamentalPayload) or payload.value is None:
            raise ValueError(f"Family A {name} is not computable")
        typed_fundamentals[name] = payload.value
    if typed_fundamentals["book_equity"] == 0 or typed_fundamentals["shares_outstanding"] <= 0:
        raise ValueError("Family A fundamental denominator is not computable")
    quality_refs = _refs([net_income, book_equity], capability_by_snapshot)
    value_refs = _refs([book_equity, shares, current], capability_by_snapshot)
    turnover_refs = _refs([*list(window[1:]), shares], capability_by_snapshot)
    return {
        "liquidity": (_mean(close_volume), market_refs),
        "momentum": (_adjusted_return(window[0], current, actions), market_refs),
        "quality": (
            _q(typed_fundamentals["net_income"] / typed_fundamentals["book_equity"]),
            quality_refs,
        ),
        "turnover": (
            _q(_mean(volume) / typed_fundamentals["shares_outstanding"]),
            turnover_refs,
        ),
        "value": (
            _q(
                typed_fundamentals["book_equity"]
                / (current_payload.close * typed_fundamentals["shares_outstanding"])
            ),
            value_refs,
        ),
        "volatility": (_standard_deviation(returns), market_refs),
    }


def _latest_listing(
    observations: tuple[NormalizedObservation, ...],
    listing_id: UUID,
) -> NormalizedObservation:
    candidates = tuple(
        item
        for item in observations
        if item.listing_id == listing_id and isinstance(item.payload, ListingIdentityPayload)
    )
    if not candidates:
        raise ValueError("listing lifecycle evidence is missing")
    return max(candidates, key=lambda item: (item.valid_from, item.available_at))


@dataclass(frozen=True, slots=True)
class _AFamilyContext:
    ordinal: int
    instrument_id: UUID
    listing_id: UUID
    sector_id: str
    bars: tuple[NormalizedObservation, ...]
    actions: tuple[NormalizedObservation, ...]
    fundamentals: dict[str, NormalizedObservation]
    fits: dict[str, ResearchTransformFit]


@dataclass(frozen=True, slots=True)
class _AFamilyTrainingContext:
    ordinal: int
    instrument_id: UUID
    listing_id: UUID
    sector_id: str
    sector_observation: NormalizedObservation
    bars: tuple[NormalizedObservation, ...]
    actions: tuple[NormalizedObservation, ...]
    fundamentals: dict[str, NormalizedObservation]
    training: tuple[
        dict[str, tuple[Decimal, tuple[ResearchSourceReference, ...]]],
        ...,
    ]


def _a_label(
    *,
    observations: tuple[NormalizedObservation, ...],
    context: _AFamilyContext,
    current_index: int,
    capability_by_snapshot: dict[UUID, DataCapability],
) -> tuple[Decimal, datetime, tuple[ResearchSourceReference, ...]]:
    current = context.bars[current_index]
    later = context.bars[current_index + 1 : current_index + 3]
    delistings = tuple(
        item
        for item in observations
        if item.instrument_id == context.instrument_id
        and isinstance(item.payload, DelistingEventPayload)
        and item.available_at > current.available_at
    )
    if len(later) >= 2:
        return (
            _adjusted_return(current, later[1], context.actions),
            later[1].available_at,
            _refs([current, *later], capability_by_snapshot),
        )
    if len(later) != 1 or not delistings:
        raise ValueError("Family A two-session or terminal label is incomplete")
    payload = delistings[0].payload
    if not isinstance(payload, DelistingEventPayload):
        raise ValueError("Family A terminal label payload is invalid")
    result = _adjusted_return(current, later[0], context.actions)
    if payload.return_inclusion is DelistingReturnInclusion.SEPARATE_RETURN_REQUIRED:
        if payload.delisting_return is None:
            raise ValueError("Family A terminal return is not computable")
        result = (Decimal("1") + result) * (Decimal("1") + payload.delisting_return) - Decimal("1")
    return (
        _q(result),
        delistings[0].available_at,
        _refs([current, later[0], delistings[0]], capability_by_snapshot),
    )


def _prepare_a(
    observations: tuple[NormalizedObservation, ...],
    capability_by_snapshot: dict[UUID, DataCapability],
) -> tuple[
    tuple[ResearchFeatureRow, ...],
    tuple[ResearchTransformFit, ...],
    tuple[UniverseSecurityEvidence, ...],
    tuple[CrossSectionRankEvidence, ...],
    CapacityEvidence,
]:
    initial_listings = tuple(
        sorted(
            (
                item
                for item in observations
                if isinstance(item.payload, ListingIdentityPayload)
                and item.payload.status.value == "active"
            ),
            key=lambda item: str(item.listing_id),
        )
    )
    if len(initial_listings) < 3:
        raise ValueError("Family A requires three point-in-time security histories")
    delisted_listing = next(
        (
            item
            for item in initial_listings
            if item.listing_id is not None
            and _listing_payload(_latest_listing(observations, item.listing_id)).status.value
            == "delisted"
        ),
        None,
    )
    if delisted_listing is None or delisted_listing.instrument_id is None:
        raise ValueError("Family A delisted history is missing")
    terminal_bars = _bars(observations, delisted_listing.instrument_id)
    active_listing = next(
        item
        for item in initial_listings
        if item.instrument_id is not None
        and item.listing_id is not None
        and _listing_payload(_latest_listing(observations, item.listing_id)).status.value
        != "delisted"
    )
    if active_listing.instrument_id is None:
        raise ValueError("Family A active listing has no stable instrument identity")
    active_bars = _bars(observations, active_listing.instrument_id)
    pre_terminal = terminal_bars[-16:-1]
    post_terminal = tuple(
        item
        for item in active_bars
        if _bar_payload(item).bar_end > _bar_payload(terminal_bars[-1]).bar_end
    )[:5]
    decision_bars = (*pre_terminal, *post_terminal)
    if len(decision_bars) != 20:
        raise ValueError("Family A requires 20 PIT decisions spanning delisting")
    decision_ends = tuple(_bar_payload(item).bar_end for item in decision_bars)

    fits: list[ResearchTransformFit] = []
    universe: list[UniverseSecurityEvidence] = []
    training_contexts: list[_AFamilyTrainingContext] = []
    average_volumes: list[Decimal] = []
    for security_ordinal, listing in enumerate(initial_listings[:3], start=1):
        if listing.instrument_id is None or listing.listing_id is None:
            raise ValueError("Family A stable identifiers are missing")
        instrument_id = listing.instrument_id
        listing_id = listing.listing_id
        bars = _bars(observations, instrument_id)
        earliest_index = next(
            (
                index
                for index, item in enumerate(bars)
                if _bar_payload(item).bar_end == decision_ends[0]
            ),
            None,
        )
        if earliest_index is None or earliest_index < 64:
            raise ValueError("Family A pre-decision train history is incomplete")
        actions = _actions(observations, instrument_id)
        fundamentals = {
            item.payload.concept_id: item
            for item in observations
            if item.instrument_id == instrument_id
            and isinstance(item.payload, AsReportedFundamentalPayload)
            and item.available_at <= bars[earliest_index].available_at
        }
        sector_observation = next(
            (
                item
                for item in observations
                if item.instrument_id == instrument_id
                and isinstance(item.payload, SectorClassificationPayload)
                and item.available_at <= bars[earliest_index].available_at
            ),
            None,
        )
        if sector_observation is None or not isinstance(
            sector_observation.payload,
            SectorClassificationPayload,
        ):
            raise ValueError("Family A sector history is missing")
        sector_id = sector_observation.payload.sector_id
        training_indices = (earliest_index - 63, earliest_index - 42, earliest_index - 21)
        training = tuple(
            _raw_a_feature_values(
                bars=bars,
                index=index,
                actions=actions,
                fundamentals=fundamentals,
                capability_by_snapshot=capability_by_snapshot,
            )
            for index in training_indices
        )
        training_contexts.append(
            _AFamilyTrainingContext(
                ordinal=security_ordinal,
                instrument_id=instrument_id,
                listing_id=listing_id,
                sector_id=sector_id,
                sector_observation=sector_observation,
                bars=bars,
                actions=actions,
                fundamentals=fundamentals,
                training=training,
            )
        )
        latest_payload = _listing_payload(_latest_listing(observations, listing_id))
        related = tuple(
            item
            for item in observations
            if item.instrument_id == instrument_id
            and isinstance(
                item.payload,
                (
                    ListingIdentityPayload,
                    SectorClassificationPayload,
                    UniverseMembershipPayload,
                    DelistingEventPayload,
                ),
            )
        )
        delisting_handled = latest_payload.status.value != "delisted" or any(
            isinstance(item.payload, DelistingEventPayload)
            and (
                item.payload.delisting_return is not None
                or item.payload.return_inclusion
                is DelistingReturnInclusion.PROVIDER_TOTAL_RETURN_INCLUDES
            )
            for item in related
        )
        universe.append(
            UniverseSecurityEvidence(
                instrument_id=instrument_id,
                listing_id=listing_id,
                sector_id=sector_id,
                listing_status=latest_payload.status.value,
                delisting_return_handled=delisting_handled,
                source_references=_refs(list(related), capability_by_snapshot),
            )
        )

    contexts: list[_AFamilyContext] = []
    prohibited = tuple(f"phase6-a-sample-{ordinal:02d}" for ordinal in range(1, 21))
    sectors = tuple(sorted({item.sector_id for item in training_contexts}))
    for sector_id in sectors:
        sector_contexts = tuple(item for item in training_contexts if item.sector_id == sector_id)
        train_entity_ids = tuple(sorted((item.listing_id for item in sector_contexts), key=str))
        if len(train_entity_ids) < 2 or len(train_entity_ids) != len(set(train_entity_ids)):
            raise ValueError("Family A sector fit requires at least two distinct securities")
        train_ids = tuple(
            f"phase6-a-train-{item.ordinal:02d}-{position:02d}"
            for item in sector_contexts
            for position in range(1, len(item.training) + 1)
        )
        fit_by_feature: dict[str, ResearchTransformFit] = {}
        for feature_name in _A_FEATURES:
            train_values = tuple(
                training_point[feature_name][0]
                for item in sector_contexts
                for training_point in item.training
            )
            combined_references = (
                *(
                    reference
                    for item in sector_contexts
                    for training_point in item.training
                    for reference in training_point[feature_name][1]
                ),
                *(
                    _reference(item.sector_observation, capability_by_snapshot)
                    for item in sector_contexts
                ),
            )
            source_references = tuple(
                sorted(
                    {item.normalized_observation_id: item for item in combined_references}.values(),
                    key=_reference_key,
                )
            )
            content = {
                "fold_id": identity(
                    PHASE6_FIT_NAMESPACE,
                    domain_sha256(
                        "phase6-train-only-within-sector-pooled-fold-v2",
                        (sector_id, feature_name, train_entity_ids, train_ids),
                    ),
                ),
                "transform_id": "phase6-within-sector-pooled-standardizer-clipped-3-v2",
                "feature_name": feature_name,
                "sector_id": sector_id,
                "train_sample_ids": train_ids,
                "train_entity_ids": train_entity_ids,
                "prohibited_sample_ids": prohibited,
                "mean": _mean(train_values),
                "standard_deviation": _standard_deviation(train_values),
                "source_references": source_references,
            }
            digest = domain_sha256(PHASE6_TRANSFORM_FIT_HASH_DOMAIN, content)
            fit = ResearchTransformFit.model_validate(
                {
                    **content,
                    "fit_id": identity(PHASE6_FIT_NAMESPACE, digest),
                    "statistic_sha256": digest,
                }
            )
            fit_by_feature[feature_name] = fit
            fits.append(fit)
        contexts.extend(
            _AFamilyContext(
                ordinal=item.ordinal,
                instrument_id=item.instrument_id,
                listing_id=item.listing_id,
                sector_id=item.sector_id,
                bars=item.bars,
                actions=item.actions,
                fundamentals=item.fundamentals,
                fits=fit_by_feature,
            )
            for item in sector_contexts
        )

    rows: list[ResearchFeatureRow] = []
    cross_sections: list[CrossSectionRankEvidence] = []
    weights = {
        "liquidity": Decimal("0.10"),
        "momentum": Decimal("0.40"),
        "quality": Decimal("0.20"),
        "turnover": Decimal("-0.10"),
        "value": Decimal("0.10"),
        "volatility": Decimal("-0.10"),
    }
    formula_ids = {
        "liquidity": "mean-20-session-raw-dollar-volume-v1",
        "momentum": "split-aware-20-session-total-return-v1",
        "quality": "as-reported-return-on-book-equity-v1",
        "turnover": "mean-20-session-share-turnover-v1",
        "value": "as-reported-book-to-raw-market-value-v1",
        "volatility": "split-aware-20-session-realized-volatility-v1",
    }
    terminal_end = _bar_payload(terminal_bars[-1]).bar_end
    for ordinal, decision_end in enumerate(decision_ends, start=1):
        eligible_contexts = tuple(
            context
            for context in contexts
            if any(_bar_payload(item).bar_end == decision_end for item in context.bars)
        )
        if decision_end > terminal_end:
            eligible_contexts = tuple(
                context
                for context in eligible_contexts
                if context.instrument_id != delisted_listing.instrument_id
            )
        if not eligible_contexts:
            raise ValueError("Family A decision has no PIT-eligible listed security")
        values_by_entity: dict[str, tuple[ResearchFeatureValue, ...]] = {}
        index_by_entity: dict[str, int] = {}
        context_by_entity: dict[str, _AFamilyContext] = {}
        for eligible_context in eligible_contexts:
            entity_id = str(eligible_context.listing_id)
            eligible_index = next(
                index
                for index, item in enumerate(eligible_context.bars)
                if _bar_payload(item).bar_end == decision_end
            )
            raw = _raw_a_feature_values(
                bars=eligible_context.bars,
                index=eligible_index,
                actions=eligible_context.actions,
                fundamentals=eligible_context.fundamentals,
                capability_by_snapshot=capability_by_snapshot,
            )
            built_values: list[ResearchFeatureValue] = []
            for feature_name in _A_FEATURES:
                fit = eligible_context.fits[feature_name]
                standardized = _q((raw[feature_name][0] - fit.mean) / fit.standard_deviation)
                transformed = min(Decimal("3"), max(Decimal("-3"), standardized))
                built_values.append(
                    ResearchFeatureValue(
                        feature_name=feature_name,
                        formula_id=formula_ids[feature_name],
                        raw_value=raw[feature_name][0],
                        transformed_value=transformed,
                        contribution=_q(transformed * weights[feature_name]),
                        source_references=raw[feature_name][1],
                        train_fit_id=fit.fit_id,
                    )
                )
            values_by_entity[entity_id] = tuple(built_values)
            index_by_entity[entity_id] = eligible_index
            context_by_entity[entity_id] = eligible_context

        ranked_entities = tuple(
            sorted(
                values_by_entity,
                key=lambda entity_id: (
                    -sum(
                        (item.contribution for item in values_by_entity[entity_id]),
                        Decimal("0"),
                    ),
                    entity_id,
                ),
            )
        )
        rank_by_entity = {
            entity_id: rank for rank, entity_id in enumerate(ranked_entities, start=1)
        }
        context = eligible_contexts[(ordinal - 1) % len(eligible_contexts)]
        selected_entity_id = str(context.listing_id)
        current_index = index_by_entity[selected_entity_id]
        values = values_by_entity[selected_entity_id]
        current = context.bars[current_index]
        decision = current.available_at + timedelta(minutes=1)

        members: list[CrossSectionRankMember] = []
        for entity_id in sorted(values_by_entity):
            member_context = context_by_entity[entity_id]
            member_values = values_by_entity[entity_id]
            member_index = index_by_entity[entity_id]
            member_current = member_context.bars[member_index]
            member_decision = member_current.available_at + timedelta(minutes=1)
            if member_decision != decision:
                raise ValueError("Family A cross-section members must share one decision time")
            member_label, member_label_t1, member_label_references = _a_label(
                observations=observations,
                context=member_context,
                current_index=member_index,
                capability_by_snapshot=capability_by_snapshot,
            )
            member_content = {
                "entity_id": entity_id,
                "instrument_id": member_context.instrument_id,
                "listing_id": member_context.listing_id,
                "sector_id": member_context.sector_id,
                "features": member_values,
                "linear_score": sum(
                    (item.contribution for item in member_values),
                    Decimal("0"),
                ),
                "linear_rank": rank_by_entity[entity_id],
                "nonlinear_score": frozen_depth_two_tree_score(member_values),
                "label_t0_utc": decision,
                "label_t1_utc": member_label_t1,
                "label_value": member_label,
                "label_source_references": member_label_references,
                "label_sha256": domain_sha256(
                    PHASE6_LABEL_SET_HASH_DOMAIN,
                    (
                        entity_id,
                        member_label,
                        decision,
                        member_label_t1,
                        member_label_references,
                    ),
                ),
                "source_lineage_sha256": domain_sha256(
                    PHASE6_FEATURE_LINEAGE_HASH_DOMAIN,
                    tuple(item.source_references for item in member_values),
                ),
            }
            members.append(
                CrossSectionRankMember.model_validate(
                    {
                        **member_content,
                        "member_sha256": domain_sha256(
                            PHASE6_CROSS_SECTION_MEMBER_HASH_DOMAIN,
                            member_content,
                        ),
                    }
                )
            )
        selected_member = next(item for item in members if item.entity_id == selected_entity_id)
        cross_section_content = {
            "ordinal": ordinal,
            "decision_time_utc": decision,
            "selected_entity_id": selected_entity_id,
            "selected_linear_rank": selected_member.linear_rank,
            "selected_nonlinear_score": selected_member.nonlinear_score,
            "eligible_members": tuple(members),
            "nonlinear_formula_id": "frozen-depth-two-tree-momentum-quality-volatility-v1",
        }
        cross_sections.append(
            CrossSectionRankEvidence.model_validate(
                {
                    **cross_section_content,
                    "evidence_sha256": domain_sha256(
                        PHASE6_CROSS_SECTION_RANK_HASH_DOMAIN,
                        cross_section_content,
                    ),
                }
            )
        )
        rows.append(
            _row(
                ordinal=ordinal,
                sample_id=f"phase6-a-sample-{ordinal:02d}",
                entity_id=str(context.listing_id),
                sector_id=context.sector_id,
                decision_time=decision,
                label_t0=decision,
                label_t1=selected_member.label_t1_utc,
                label_value=selected_member.label_value,
                label_references=selected_member.label_source_references,
                features=values,
            )
        )
        volume_window = context.bars[current_index - 19 : current_index + 1]
        average_volumes.append(_mean(tuple(_bar_payload(item).volume for item in volume_window)))
    score_values = tuple(abs(item.composite_score) for item in rows)
    total_score = sum(score_values, Decimal("0"))
    concentration = (
        max(score_values) / total_score
        if total_score > 0
        else Decimal("1") / Decimal(len(score_values))
    )
    capacity = CapacityEvidence(
        turnover=Decimal("1"),
        adv_participation=Decimal("0.01"),
        capacity_units=_q(min(average_volumes) * Decimal("0.01")),
        concentration=_q(concentration),
        capacity_limit_breached=False,
    )
    return tuple(rows), tuple(fits), tuple(universe), tuple(cross_sections), capacity


def _prepare_b(
    observations: tuple[NormalizedObservation, ...],
    capability_by_snapshot: dict[UUID, DataCapability],
) -> tuple[tuple[ResearchFeatureRow, ...], PreparedFamilyBInputs]:
    initial_listings = tuple(
        sorted(
            (
                item
                for item in observations
                if isinstance(item.payload, ListingIdentityPayload)
                and item.payload.status.value == "active"
                and item.instrument_id is not None
                and item.listing_id is not None
            ),
            key=lambda item: str(item.listing_id),
        )
    )
    lifecycle_tests: list[LifecycleTestEvidence] = []
    for initial in initial_listings:
        if initial.instrument_id is None or initial.listing_id is None:
            raise ValueError("Family B lifecycle test identifiers are missing")
        latest = _latest_listing(observations, initial.listing_id)
        latest_payload = _listing_payload(latest)
        status = latest_payload.status.value
        volatility_rows = tuple(
            item
            for item in observations
            if item.instrument_id == initial.instrument_id
            and isinstance(item.payload, VolatilityReturnInputPayload)
        )
        if len(volatility_rows) != 1:
            raise ValueError("Family B lifecycle tests require one exact return-input bundle")
        delisting_rows = tuple(
            item
            for item in observations
            if item.instrument_id == initial.instrument_id
            and isinstance(item.payload, DelistingEventPayload)
        )
        delisting_handled: bool | None = None
        if status == "delisted":
            volatility_payload = volatility_rows[0].payload
            if (
                not isinstance(volatility_payload, VolatilityReturnInputPayload)
                or not volatility_payload.delisting_observation_ids
                or not delisting_rows
            ):
                raise ValueError("Family B delisted lifecycle test lacks delisting inputs")
            delisting_handled = any(
                isinstance(item.payload, DelistingEventPayload)
                and (
                    item.payload.delisting_return is not None
                    or item.payload.return_inclusion
                    is DelistingReturnInclusion.PROVIDER_TOTAL_RETURN_INCLUDES
                )
                for item in delisting_rows
            )
        sources = _refs(
            [
                item
                for item in observations
                if item.instrument_id == initial.instrument_id
                and isinstance(
                    item.payload,
                    (
                        ListingIdentityPayload,
                        UniverseMembershipPayload,
                        VolatilityReturnInputPayload,
                        DelistingEventPayload,
                    ),
                )
            ],
            capability_by_snapshot,
        )
        lifecycle_content = {
            "instrument_id": initial.instrument_id,
            "listing_id": initial.listing_id,
            "listing_status": status,
            "inception_at_utc": initial.valid_from,
            "termination_at_utc": None if status == "active" else latest.valid_from,
            "delisting_return_handled": delisting_handled,
            "used_as_feature": False,
            "source_references": sources,
        }
        lifecycle_tests.append(
            LifecycleTestEvidence.model_validate(
                {
                    **lifecycle_content,
                    "evidence_sha256": domain_sha256(
                        PHASE6_LIFECYCLE_TEST_HASH_DOMAIN,
                        lifecycle_content,
                    ),
                }
            )
        )
    if {item.listing_status for item in lifecycle_tests} != {
        "active",
        "inactive",
        "delisted",
    }:
        raise ValueError("Family B lifecycle tests require active, inactive, and delisted series")

    action = next(
        (item for item in observations if isinstance(item.payload, CorporateActionPayload)),
        None,
    )
    if action is None or action.instrument_id is None:
        raise ValueError("Family B requires explicit corporate-action evidence")
    instrument_id = action.instrument_id
    security_bars = _bars(observations, instrument_id)
    if len(security_bars) < 255:
        raise ValueError("Family B requires at least 253 raw bars plus later labels")
    security_actions = _actions(observations, instrument_id)
    volatility_input = next(
        (
            item
            for item in observations
            if item.instrument_id == instrument_id
            and isinstance(item.payload, VolatilityReturnInputPayload)
        ),
        None,
    )
    if volatility_input is None:
        raise ValueError("Family B action-aware return input bundle is missing")
    volatility_payload = volatility_input.payload
    if not isinstance(volatility_payload, VolatilityReturnInputPayload):
        raise ValueError("Family B volatility input payload is invalid")
    input_end = volatility_payload.window_end
    decision_candidates = tuple(
        index
        for index, item in enumerate(security_bars)
        if index >= 252
        and _bar_payload(item).bar_end > input_end
        and index + 2 < len(security_bars)
    )
    if len(decision_candidates) < 20:
        raise ValueError("Family B requires 20 post-input-window decisions and labels")
    rows: list[ResearchFeatureRow] = []
    for ordinal, current_index in enumerate(decision_candidates[:20], start=1):
        current = security_bars[current_index]
        window = security_bars[current_index - 252 : current_index + 1]
        if len(window) != 253:
            raise ValueError("Family B exact 252-session history is incomplete")
        one_day_returns = tuple(
            _adjusted_return(window[index - 1], window[index], security_actions)
            for index in range(1, len(window))
        )
        lag_returns = tuple(
            _adjusted_return(security_bars[current_index - lag], current, security_actions)
            for lag in _B_WINDOWS
        )
        adjusted_refs = _refs(
            list(window)
            + list(_period_action_observations(window[0], current, security_actions))
            + [volatility_input],
            capability_by_snapshot,
        )
        raw_refs = _refs(list(window), capability_by_snapshot)
        closes = tuple(_bar_payload(item).close for item in window)
        x_mean = Decimal(len(closes) - 1) / Decimal("2")
        y_mean = sum(closes, Decimal("0")) / Decimal(len(closes))
        numerator = sum(
            ((Decimal(index) - x_mean) * (value - y_mean) for index, value in enumerate(closes)),
            Decimal("0"),
        )
        denominator = sum(
            ((Decimal(index) - x_mean) ** 2 for index in range(len(closes))),
            Decimal("0"),
        )
        if denominator == 0 or y_mean == 0:
            raise ValueError("Family B trend strength is not computable")
        feature_data = {
            "drawdown": (
                _q(closes[-1] / max(closes) - Decimal("1")),
                raw_refs,
                Decimal("0.10"),
                "raw-nominal-252-session-drawdown-v1",
            ),
            "lagged_return": (
                _mean(lag_returns),
                adjusted_refs,
                Decimal("0.40"),
                "action-aware-mean-lagged-return-1-5-20-63-126-252-v1",
            ),
            "realized_volatility": (
                _standard_deviation(one_day_returns),
                adjusted_refs,
                Decimal("-0.20"),
                "action-aware-252-session-realized-volatility-v1",
            ),
            "trend_strength": (
                _q((numerator / denominator) / y_mean),
                raw_refs,
                Decimal("0.30"),
                "raw-nominal-252-session-ols-trend-strength-v1",
            ),
        }
        features = tuple(
            ResearchFeatureValue(
                feature_name=name,
                formula_id=values[3],
                raw_value=values[0],
                transformed_value=values[0],
                contribution=_q(values[0] * values[2]),
                source_references=values[1],
                train_fit_id=None,
            )
            for name, values in sorted(feature_data.items())
        )
        label_end = security_bars[current_index + 2]
        label_value = _adjusted_return(current, label_end, security_actions)
        label_sources = _refs(
            list(security_bars[current_index : current_index + 3])
            + list(_period_action_observations(current, label_end, security_actions)),
            capability_by_snapshot,
        )
        decision = current.available_at + timedelta(minutes=1)
        rows.append(
            _row(
                ordinal=ordinal,
                sample_id=f"phase6-b-sample-{ordinal:02d}",
                entity_id=str(current.listing_id),
                sector_id=None,
                decision_time=decision,
                label_t0=decision,
                label_t1=label_end.available_at,
                label_value=label_value,
                label_references=label_sources,
                features=features,
            )
        )
    listing = next(
        (
            item
            for item in observations
            if item.instrument_id == instrument_id
            and isinstance(item.payload, ListingIdentityPayload)
            and item.payload.status.value == "active"
        ),
        None,
    )
    if listing is None or listing.listing_id is None:
        raise ValueError("Family B lifecycle evidence is missing")
    lifecycle_refs = _refs(
        [
            item
            for item in observations
            if item.instrument_id == instrument_id
            and isinstance(item.payload, (ListingIdentityPayload, UniverseMembershipPayload))
        ],
        capability_by_snapshot,
    )
    family_inputs = PreparedFamilyBInputs(
        lag_windows=_B_WINDOWS,
        raw_nominal_bar_count=len(security_bars),
        adjusted_return_observation_count=len(security_bars) - 1,
        lifecycle=LifecycleEvidence(
            instrument_id=instrument_id,
            listing_id=listing.listing_id,
            inception_at_utc=listing.valid_from,
            termination_at_utc=listing.valid_to,
            source_references=lifecycle_refs,
        ),
        lifecycle_tests=tuple(lifecycle_tests),
        corporate_action_source_references=_refs(
            list(security_actions),
            capability_by_snapshot,
        ),
    )
    return tuple(rows), family_inputs


def _tokens(text: str) -> frozenset[str]:
    return frozenset(re.findall(r"[a-z0-9]+", text.lower()))


def _extract_text_features(
    payload: OfficialDocumentContentPayload,
    previous: OfficialDocumentContentPayload | None,
) -> StructuredTextFeatures:
    tokens = _tokens(payload.document_text)
    if not tokens:
        raise ValueError("official document text cannot produce structured features")
    if previous is None:
        novelty = Decimal("1")
    else:
        prior = _tokens(previous.document_text)
        union = tokens | prior
        novelty = Decimal("1") - Decimal(len(tokens & prior)) / Decimal(len(union))
    positive = {"growth", "improved", "increase", "strong"}
    negative = {"decline", "decrease", "loss", "weak"}
    uncertainty = {"may", "might", "uncertain", "could"}
    risk_up = {"risk", "adverse", "warning"}
    risk_down = {"resolved", "reduced", "mitigated"}
    size = Decimal(len(tokens))
    tags = ("official_correction",) if payload.correction_sequence else ("official_original",)
    return StructuredTextFeatures(
        novelty=_q(novelty),
        direction=_q(Decimal(len(tokens & positive) - len(tokens & negative)) / size),
        uncertainty=_q(Decimal(len(tokens & uncertainty)) / size),
        risk_change=_q(Decimal(len(tokens & risk_up) - len(tokens & risk_down)) / size),
        event_tags=tags,
    )


def _prepare_c_two_row_legacy(
    observations: tuple[NormalizedObservation, ...],
    capability_by_snapshot: dict[UUID, DataCapability],
) -> tuple[
    tuple[ResearchFeatureRow, ...],
    tuple[TextFeatureExtraction, ...],
    tuple[SocialOfficialCorroboration, ...],
]:
    documents = tuple(
        sorted(
            (
                item
                for item in observations
                if isinstance(item.payload, OfficialDocumentContentPayload)
            ),
            key=lambda item: (item.available_at, item.source_record_id),
        )
    )
    if len(documents) < 2:
        raise ValueError("Family C requires original and corrected official documents")
    prompt_sha256 = domain_sha256(
        "phase6-deterministic-extractor-prompt-v1",
        "Extract novelty, direction, uncertainty, risk change, and event tags only.",
    )
    prior_by_source: dict[UUID, OfficialDocumentContentPayload] = {}
    extractions: list[TextFeatureExtraction] = []
    rows: list[ResearchFeatureRow] = []
    for ordinal, document in enumerate(documents, start=1):
        payload = document.payload
        if not isinstance(payload, OfficialDocumentContentPayload):
            raise ValueError("Family C official content payload is invalid")
        previous = prior_by_source.get(payload.official_source_version_id)
        structured = _extract_text_features(payload, previous)
        prior_by_source[payload.official_source_version_id] = payload
        entity_id = (
            str(document.instrument_id)
            if document.instrument_id is not None
            else payload.official_document_id
        )
        content = {
            "schema_version": "phase6-text-feature-extraction-v1",
            "ordinal": ordinal,
            "official_source_version_id": payload.official_source_version_id,
            "official_document_id": payload.official_document_id,
            "document_content_sha256": payload.document_content_sha256,
            "available_at_utc": document.available_at,
            "corrected_at_utc": payload.corrected_at,
            "correction_sequence": payload.correction_sequence,
            "extractor_kind": "deterministic_mock",
            "extractor_id": "phase6-structured-official-event-extractor",
            "extractor_version": "v1",
            "model_id": "deterministic-mock-no-provider-credentials",
            "prompt_version": "v1",
            "prompt_sha256": prompt_sha256,
            "extraction_schema_version": "phase6-structured-text-features-v1",
            "entity_id": entity_id,
            "entity_resolution_method": "exact-phase4-instrument-or-document-id-v1",
            "features": structured,
            "output_boundary": "structured_features_only",
        }
        digest = domain_sha256(PHASE6_TEXT_EXTRACTION_HASH_DOMAIN, content)
        extraction = TextFeatureExtraction.model_validate(
            {
                **content,
                "extraction_id": identity(PHASE6_EXTRACTION_NAMESPACE, digest),
                "extraction_sha256": digest,
            }
        )
        extractions.append(extraction)
        if document.instrument_id is None:
            raise ValueError("Family C entity-resolved market label is missing")
        market_bars = _bars(observations, document.instrument_id)
        future = tuple(item for item in market_bars if item.available_at > document.available_at)
        if len(future) < 2:
            raise ValueError("Family C two-session label is incomplete")
        label_start, label_end = future[:2]
        label_value = _adjusted_return(label_start, label_end, ())
        document_ref = _refs([document], capability_by_snapshot)
        raw_values = {
            "direction": structured.direction,
            "event_tag": Decimal(len(structured.event_tags)),
            "novelty": structured.novelty,
            "risk_change": structured.risk_change,
            "uncertainty": structured.uncertainty,
        }
        features = tuple(
            ResearchFeatureValue(
                feature_name=name,
                formula_id="event-tag-count-from-versioned-extraction-v1"
                if name == "event_tag"
                else f"{name}-from-versioned-extraction-v1",
                raw_value=value,
                transformed_value=value,
                contribution=_q(value / Decimal(len(raw_values))),
                source_references=document_ref,
                train_fit_id=None,
            )
            for name, value in sorted(raw_values.items())
        )
        decision = document.available_at + timedelta(minutes=1)
        rows.append(
            _row(
                ordinal=ordinal,
                sample_id=f"phase6-c-sample-{ordinal:02d}",
                entity_id=entity_id,
                sector_id=None,
                decision_time=decision,
                label_t0=label_start.available_at,
                label_t1=label_end.available_at,
                label_value=label_value,
                label_references=_refs([label_start, label_end], capability_by_snapshot),
                features=features,
            )
        )
    extraction_by_source = {item.official_source_version_id: item for item in extractions}
    document_by_hash = {
        item.payload.document_content_sha256: item
        for item in documents
        if isinstance(item.payload, OfficialDocumentContentPayload)
    }
    social_rows = tuple(
        item for item in observations if isinstance(item.payload, SocialAttentionPayload)
    )
    corroborations: list[SocialOfficialCorroboration] = []
    for ordinal, social in enumerate(
        sorted(social_rows, key=lambda item: _social_payload(item).social_attention_record_id),
        start=1,
    ):
        payload = social.payload
        if not isinstance(payload, SocialAttentionPayload):
            raise ValueError("Family C social payload is invalid")
        matched_extraction = extraction_by_source.get(payload.claimed_official_source_version_id)
        if matched_extraction is None or matched_extraction.entity_id != payload.entity_id:
            raise ValueError("social attention lacks exact official entity corroboration")
        official = document_by_hash.get(matched_extraction.document_content_sha256)
        if official is None or official.available_at > social.available_at:
            raise ValueError("social attention precedes its claimed official evidence")
        content = {
            "ordinal": ordinal,
            "social_attention_record_id": payload.social_attention_record_id,
            "official_source_version_id": matched_extraction.official_source_version_id,
            "official_document_sha256": matched_extraction.document_content_sha256,
            "social_source_reference": _reference(social, capability_by_snapshot),
            "official_source_reference": _reference(official, capability_by_snapshot),
            "exact_match": True,
            "contributes_standalone": False,
        }
        digest = domain_sha256(PHASE6_CORROBORATION_HASH_DOMAIN, content)
        corroborations.append(
            SocialOfficialCorroboration.model_validate(
                {
                    **content,
                    "corroboration_id": identity(PHASE6_CORROBORATION_NAMESPACE, digest),
                    "corroboration_sha256": digest,
                }
            )
        )
    if not corroborations:
        raise ValueError("Family C requires official corroboration for social attention")
    return tuple(rows), tuple(extractions), tuple(corroborations)


def _prepare_c(
    observations: tuple[NormalizedObservation, ...],
    capability_by_snapshot: dict[UUID, DataCapability],
) -> tuple[
    tuple[ResearchFeatureRow, ...],
    tuple[TextFeatureExtraction, ...],
    tuple[SocialOfficialCorroboration, ...],
    tuple[LaggedOhlcvBaselineEvidence, ...],
]:
    _, extractions, corroborations = _prepare_c_two_row_legacy(
        observations,
        capability_by_snapshot,
    )
    documents = tuple(
        sorted(
            (
                item
                for item in observations
                if isinstance(item.payload, OfficialDocumentContentPayload)
            ),
            key=lambda item: (item.available_at, item.source_record_id),
        )
    )
    if not documents or documents[0].instrument_id is None:
        raise ValueError("Family C market-label entity is missing")
    market_bars = _bars(observations, documents[0].instrument_id)
    candidates = tuple(
        (index, bar)
        for index, bar in enumerate(market_bars)
        if index >= 1
        and index + 2 < len(market_bars)
        and any(document.available_at <= bar.available_at for document in documents)
    )
    if len(candidates) < 20:
        raise ValueError("Family C requires 20 unique post-document research sessions")
    extraction_by_hash = {item.document_content_sha256: item for item in extractions}
    rows: list[ResearchFeatureRow] = []
    non_text_baseline: list[LaggedOhlcvBaselineEvidence] = []
    for ordinal, (bar_index, decision_bar) in enumerate(candidates[:20], start=1):
        available_documents = tuple(
            item for item in documents if item.available_at <= decision_bar.available_at
        )
        document = max(available_documents, key=lambda item: item.available_at)
        payload = document.payload
        if not isinstance(payload, OfficialDocumentContentPayload):
            raise ValueError("Family C document payload is invalid")
        extraction = extraction_by_hash.get(payload.document_content_sha256)
        if extraction is None:
            raise ValueError("Family C session lacks its latest versioned extraction")
        structured = extraction.features
        raw_values = {
            "direction": structured.direction,
            "event_tag": Decimal(len(structured.event_tags)),
            "novelty": structured.novelty,
            "risk_change": structured.risk_change,
            "uncertainty": structured.uncertainty,
        }
        document_reference = _refs([document], capability_by_snapshot)
        features = tuple(
            ResearchFeatureValue(
                feature_name=name,
                formula_id="event-tag-count-from-versioned-extraction-v1"
                if name == "event_tag"
                else f"{name}-from-versioned-extraction-v1",
                raw_value=value,
                transformed_value=value,
                contribution=_q(value / Decimal(len(raw_values))),
                source_references=document_reference,
                train_fit_id=None,
            )
            for name, value in sorted(raw_values.items())
        )
        label_end = market_bars[bar_index + 2]
        label_references = _refs(
            list(market_bars[bar_index : bar_index + 3]),
            capability_by_snapshot,
        )
        decision = decision_bar.available_at + timedelta(minutes=1)
        previous_bar = market_bars[bar_index - 1]
        previous_payload = _bar_payload(previous_bar)
        decision_payload = _bar_payload(decision_bar)
        lagged_return = _q(decision_payload.close / previous_payload.close - Decimal("1"))
        intraday_range = _q((decision_payload.high - decision_payload.low) / decision_payload.close)
        baseline_content = {
            "ordinal": ordinal,
            "sample_id": f"phase6-c-sample-{ordinal:02d}",
            "entity_id": extraction.entity_id,
            "decision_time_utc": decision,
            "model_id": "lagged-return-range-linear-baseline-v1",
            "formula_id": "one-session-raw-return-minus-intraday-range-v1",
            "lagged_return": lagged_return,
            "intraday_range": intraday_range,
            "baseline_output": _q(lagged_return - intraday_range),
            "source_references": (
                _reference(previous_bar, capability_by_snapshot),
                _reference(decision_bar, capability_by_snapshot),
            ),
            "used_for_selection": False,
        }
        non_text_baseline.append(
            LaggedOhlcvBaselineEvidence.model_validate(
                {
                    **baseline_content,
                    "evidence_sha256": domain_sha256(
                        PHASE6_LAGGED_OHLCV_BASELINE_HASH_DOMAIN,
                        baseline_content,
                    ),
                }
            )
        )
        rows.append(
            _row(
                ordinal=ordinal,
                sample_id=f"phase6-c-sample-{ordinal:02d}",
                entity_id=extraction.entity_id,
                sector_id=None,
                decision_time=decision,
                label_t0=decision,
                label_t1=label_end.available_at,
                label_value=_adjusted_return(decision_bar, label_end, ()),
                label_references=label_references,
                features=features,
            )
        )
    return tuple(rows), extractions, corroborations, tuple(non_text_baseline)


def _comparisons(
    family: CanonicalFamily,
    rows: tuple[ResearchFeatureRow, ...],
    scores: tuple[ResearchScoreOutput, ...],
    cross_sections: tuple[CrossSectionRankEvidence, ...] = (),
    non_text_baseline: tuple[LaggedOhlcvBaselineEvidence, ...] = (),
) -> tuple[ResearchBaselineComparison, ...]:
    candidate = tuple((item.sample_id, item.research_score) for item in scores)
    if family is CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING:
        if len(cross_sections) != len(rows):
            raise ValueError("Family A comparison requires every fixed-time cross-section")
        linear = _cross_section_outputs(cross_sections, "linear_score")
        nonlinear = _cross_section_outputs(cross_sections, "nonlinear_score")
        cross_section_zero = tuple((key, Decimal("0")) for key, _value in linear)
        linear_metric = _cross_section_concordance(linear, cross_sections)
        labels_sha256 = _cross_section_label_hash(cross_sections)
        return (
            _comparison(
                ordinal=1,
                candidate_model_id="sector-relative-rank-linear-v1",
                baseline_model_id="zero-information-rank-v1",
                metric_id="pairwise-label-concordance-v1",
                candidate_outputs=linear,
                baseline_outputs=cross_section_zero,
                rows=rows,
                candidate_metric=linear_metric,
                baseline_metric=_cross_section_concordance(
                    cross_section_zero,
                    cross_sections,
                ),
                reason_codes=("descriptive_fixed_time_cross_section_audit",),
                label_sha256=labels_sha256,
            ),
            _comparison(
                ordinal=2,
                candidate_model_id="frozen-depth-two-tree-v1",
                baseline_model_id="sector-relative-rank-linear-v1",
                metric_id="pairwise-label-concordance-v1",
                candidate_outputs=nonlinear,
                baseline_outputs=linear,
                rows=rows,
                candidate_metric=_cross_section_concordance(nonlinear, cross_sections),
                baseline_metric=linear_metric,
                reason_codes=("descriptive_frozen_tree_cross_section_audit",),
                label_sha256=labels_sha256,
            ),
        )
    if family is CanonicalFamily.B_TIME_SERIES_MOMENTUM_REGIME:
        lagged = tuple(
            (
                row.sample_id,
                next(
                    item.raw_value for item in row.features if item.feature_name == "lagged_return"
                ),
            )
            for row in rows
        )
        return (
            _comparison(
                ordinal=1,
                candidate_model_id="lagged-trend-linear-v1",
                baseline_model_id="lagged-return-only-v1",
                metric_id="two-session-directional-accuracy-v1",
                candidate_outputs=candidate,
                baseline_outputs=lagged,
                rows=rows,
                candidate_metric=_directional_accuracy(candidate, rows),
                baseline_metric=_directional_accuracy(lagged, rows),
                reason_codes=("time_series_comparison_derived_from_prepared_labels",),
            ),
        )
    if len(non_text_baseline) != len(rows):
        raise ValueError("Family C comparison requires every lagged OHLCV baseline output")
    baseline_outputs = tuple((item.sample_id, item.baseline_output) for item in non_text_baseline)
    return (
        _comparison(
            ordinal=1,
            candidate_model_id="conventional-linear-text-overlay-v1",
            baseline_model_id="lagged-return-range-linear-baseline-v1",
            metric_id="two-session-directional-accuracy-v1",
            candidate_outputs=candidate,
            baseline_outputs=baseline_outputs,
            rows=rows,
            candidate_metric=_directional_accuracy(candidate, rows),
            baseline_metric=_directional_accuracy(baseline_outputs, rows),
            reason_codes=("descriptive_text_overlay_vs_pit_lagged_ohlcv_not_used_for_selection",),
        ),
    )


def prepare_research_pipeline(
    configuration_id: ResearchConfigurationId,
    snapshots: tuple[SnapshotBundle, ...],
) -> PreparedResearchPipeline:
    """Compute every research input before Phase 5 can inspect any outer OOS result."""

    family, bindings, observations, capability_by_snapshot = _validated_inputs(
        configuration_id,
        snapshots,
    )
    specification = build_specification(family)
    if family is CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING:
        rows, fits, universe, cross_sections, capacity = _prepare_a(
            observations,
            capability_by_snapshot,
        )
        family_inputs: PreparedFamilyAInputs | PreparedFamilyBInputs | PreparedFamilyCInputs = (
            PreparedFamilyAInputs(
                universe=universe,
                train_only_sector_fits=fits,
                cross_section_ranks=cross_sections,
                capacity=capacity,
            )
        )
    elif family is CanonicalFamily.B_TIME_SERIES_MOMENTUM_REGIME:
        rows, family_inputs = _prepare_b(observations, capability_by_snapshot)
    else:
        rows, extractions, corroborations, non_text_baseline = _prepare_c(
            observations,
            capability_by_snapshot,
        )
        family_inputs = PreparedFamilyCInputs(
            extractions=extractions,
            corroborations=corroborations,
            non_text_baseline=non_text_baseline,
        )
    scores = _scores(family, rows)
    comparison_cross_sections = (
        family_inputs.cross_section_ranks
        if isinstance(family_inputs, PreparedFamilyAInputs)
        else ()
    )
    comparisons = _comparisons(
        family,
        rows,
        scores,
        comparison_cross_sections,
        (
            family_inputs.non_text_baseline
            if isinstance(family_inputs, PreparedFamilyCInputs)
            else ()
        ),
    )
    content = {
        "schema_version": "phase6-prepared-research-pipeline-v1",
        "configuration_id": configuration_id,
        "family": family,
        "specification": specification,
        "snapshot_bindings": bindings,
        "feature_rows": rows,
        "scores": scores,
        "baseline_comparisons": comparisons,
        "family_inputs": family_inputs,
    }
    return PreparedResearchPipeline.model_validate(
        {
            **content,
            "pipeline_input_sha256": domain_sha256(
                PHASE6_PIPELINE_INPUT_HASH_DOMAIN,
                content,
            ),
        }
    )


__all__ = ["prepare_research_pipeline"]
