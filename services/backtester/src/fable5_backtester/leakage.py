"""Automatic Phase 5 point-in-time and six-defect leakage checks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, cast
from uuid import UUID

from fable5_data.contracts import (
    AdjustmentBasis,
    AsReportedFundamentalPayload,
    DataCapability,
    OhlcvBarPayload,
    UniverseMembershipPayload,
)

from fable5_backtester.canonical import (
    PHASE5_LEAKAGE_EVIDENCE_HASH_DOMAIN,
    PHASE5_SAMPLE_HASH_DOMAIN,
    domain_sha256,
)
from fable5_backtester.contracts import (
    PHASE5_ADVERSARIAL_DEPENDENCY_REVIEW_HASH_DOMAIN,
    AdversarialDependencyProbe,
    AdversarialDependencyReview,
    FeatureSpecification,
    FoldRecord,
    L01PriceBasisEvidence,
    L02FundamentalRevisionEvidence,
    L03FeatureAvailabilityEvidence,
    L03SourceInformationIntervalEvidence,
    L04DependencyScanEvidence,
    L05MembershipReconstructionEvidence,
    L06TrainOnlyFitEvidence,
    LabelSpecification,
    LeakageCode,
    LeakageEvidenceBase,
    LeakageEvidenceRecord,
    LeakageSampleAuditInput,
    PreprocessingFitRecord,
    ResolvedSourceObservation,
    ResolvedSourceObservationRef,
    SourceObservationKey,
    SyntheticSample,
    derive_dependency_graph,
)


@dataclass(frozen=True, slots=True)
class LeakageFinding:
    code: LeakageCode
    blocked: bool
    affected_sample_ids: tuple[str, ...]
    evidence_rule: str
    evidence_records: tuple[LeakageEvidenceRecord, ...]


def _reasons(*values: str) -> tuple[str, ...]:
    return tuple(sorted({value for value in values if value}))


def _evidence[T: LeakageEvidenceBase](model_type: type[T], **content: object) -> T:
    draft = model_type.model_construct(
        **cast(dict[str, Any], content),
        evidence_sha256="0" * 64,
    )
    complete_content = draft.model_dump(mode="python", exclude={"evidence_sha256"})
    return model_type.model_validate(
        {
            **complete_content,
            "evidence_sha256": domain_sha256(
                PHASE5_LEAKAGE_EVIDENCE_HASH_DOMAIN,
                complete_content,
            ),
        }
    )


def _key_tuple(key: SourceObservationKey) -> tuple[str, str]:
    return str(key.capability), str(key.normalized_observation_id)


def _ordered_sample_ids(
    samples: tuple[LeakageSampleAuditInput, ...],
    affected: set[str],
) -> tuple[str, ...]:
    fixture_order = tuple(sample.sample_id for sample in samples if sample.sample_id in affected)
    fixture_ids = set(fixture_order)
    return (*fixture_order, *sorted(affected - fixture_ids))


def _finding(
    *,
    code: LeakageCode,
    samples: tuple[LeakageSampleAuditInput, ...],
    affected: set[str],
    evidence_rule: str,
    evidence_records: tuple[LeakageEvidenceRecord, ...],
) -> LeakageFinding:
    return LeakageFinding(
        code=code,
        blocked=any(not record.passed for record in evidence_records),
        affected_sample_ids=_ordered_sample_ids(samples, affected),
        evidence_rule=evidence_rule,
        evidence_records=evidence_records,
    )


def _l01_price_basis_finding(
    samples: tuple[LeakageSampleAuditInput, ...],
    source_observations: tuple[ResolvedSourceObservation, ...],
) -> LeakageFinding:
    sources = {_key_tuple(item.key): item for item in source_observations}
    affected: set[str] = set()
    records: list[L01PriceBasisEvidence] = []
    for sample in samples:
        source_key = sample.feature_derivation.source_observation_key
        source = sources.get(_key_tuple(source_key))
        payload = (
            source.normalized_observation.payload
            if source is not None
            and isinstance(source.normalized_observation.payload, OhlcvBarPayload)
            else None
        )
        reason_values: list[str] = []
        if source is None:
            reason_values.append("l01_source_observation_missing")
        elif payload is None:
            reason_values.append("l01_source_payload_not_ohlcv")
        if sample.feature_derivation.source_payload_field != "open":
            reason_values.append("l01_source_price_field_not_open")
        if sample.price_adjustment_basis is None:
            reason_values.append("l01_effective_price_basis_missing")

        source_basis: Literal["raw_unadjusted", "as_of_adjusted"] | None = (
            "raw_unadjusted"
            if payload is not None and payload.adjustment_basis is AdjustmentBasis.RAW_UNADJUSTED
            else "as_of_adjusted"
            if payload is not None
            else None
        )
        source_action_as_of = payload.adjustment_as_of if payload is not None else None
        source_price = payload.open if payload is not None else None
        expected_effective_basis = (
            "raw_unadjusted"
            if source_basis == AdjustmentBasis.RAW_UNADJUSTED.value
            else "adjusted_for_corporate_action"
            if source_basis == AdjustmentBasis.AS_OF_ADJUSTED.value
            else None
        )
        price_values_match = (
            source_price == sample.reference_price if source_price is not None else False
        )
        price_bases_match = (
            expected_effective_basis is not None
            and sample.price_adjustment_basis == expected_effective_basis
        )
        action_as_of_values_match = (
            payload is not None and source_action_as_of == sample.adjustment_action_as_of_utc
        )
        if payload is not None and not price_values_match:
            reason_values.append("l01_source_effective_price_mismatch")
        if payload is not None and not price_bases_match:
            reason_values.append("l01_source_effective_basis_mismatch")
        if payload is not None and not action_as_of_values_match:
            reason_values.append("l01_source_effective_action_as_of_mismatch")
        if (source_action_as_of is not None and source_action_as_of > sample.decision_time_utc) or (
            sample.adjustment_action_as_of_utc is not None
            and sample.adjustment_action_as_of_utc > sample.decision_time_utc
        ):
            reason_values.append("l01_adjustment_action_future")
        if source is not None and (
            source.normalized_observation.event_time > sample.decision_time_utc
            or source.normalized_observation.available_at > sample.decision_time_utc
        ):
            reason_values.append("l01_source_timestamp_future")
        if (
            payload is not None
            and payload.adjustment_basis is AdjustmentBasis.AS_OF_ADJUSTED
            and not payload.corporate_action_revision_ids
        ):
            reason_values.append("l01_adjustment_revision_trace_missing")

        reasons = _reasons(*reason_values)
        if reasons:
            affected.add(sample.sample_id)
        observation = source.normalized_observation if source is not None else None
        records.append(
            _evidence(
                L01PriceBasisEvidence,
                sample_id=sample.sample_id,
                source_observation_key=source_key,
                source_snapshot_id=(observation.snapshot_id if observation is not None else None),
                source_snapshot_sha256=(
                    observation.snapshot_sha256 if observation is not None else None
                ),
                source_payload_field=(
                    "open" if sample.feature_derivation.source_payload_field == "open" else None
                ),
                source_price=source_price,
                source_adjustment_basis=source_basis,
                source_adjustment_as_of_utc=source_action_as_of,
                source_corporate_action_revision_ids=(
                    payload.corporate_action_revision_ids if payload is not None else ()
                ),
                source_event_time_utc=(observation.event_time if observation is not None else None),
                source_available_at_utc=(
                    observation.available_at if observation is not None else None
                ),
                effective_price=sample.reference_price,
                effective_price_basis=sample.price_adjustment_basis,
                effective_adjustment_as_of_utc=sample.adjustment_action_as_of_utc,
                decision_time_utc=sample.decision_time_utc,
                price_values_match=price_values_match,
                price_bases_match=price_bases_match,
                action_as_of_values_match=action_as_of_values_match,
                passed=not reasons,
                reason_codes=reasons,
            )
        )
    return _finding(
        code=LeakageCode.L01,
        samples=samples,
        affected=affected,
        evidence_rule=(
            "resolved Phase 4 OHLCV price, price basis, action revision trace, and action as_of "
            "must exactly match effective sample evidence available by decision time"
        ),
        evidence_records=tuple(records),
    )


def _l02_fundamental_finding(
    samples: tuple[LeakageSampleAuditInput, ...],
    source_observations: tuple[ResolvedSourceObservation, ...],
) -> LeakageFinding:
    sources = {_key_tuple(item.key): item for item in source_observations}
    affected: set[str] = set()
    records: list[L02FundamentalRevisionEvidence] = []
    for sample in samples:
        resolved_fundamentals = tuple(
            source
            for key in sample.source_observation_keys
            if key.capability is DataCapability.AS_REPORTED_FUNDAMENTALS
            and (source := sources.get(_key_tuple(key))) is not None
            and isinstance(source.normalized_observation.payload, AsReportedFundamentalPayload)
        )
        source = resolved_fundamentals[0] if resolved_fundamentals else None
        observation = source.normalized_observation if source is not None else None
        payload = (
            observation.payload
            if observation is not None
            and isinstance(observation.payload, AsReportedFundamentalPayload)
            else None
        )
        dependencies = (
            (f"phase4-as-reported-fundamentals.{payload.concept_id}",)
            if payload is not None
            else ()
        )
        revision_id = observation.revision_id if observation is not None else None
        revision_trace = (
            (
                *((payload.restates_revision_id,) if payload.restates_revision_id else ()),
                revision_id,
            )
            if payload is not None and revision_id is not None
            else ()
        )
        declared = sample.fundamental_revision
        declared_matches = bool(
            declared is not None
            and payload is not None
            and observation is not None
            and declared.dependency_ids == dependencies
            and declared.revision_id == revision_id
            and declared.accepted_at_utc == payload.filing_accepted_at
            and declared.available_at_utc == observation.available_at
            and declared.revision_trace_ids == revision_trace
        )
        reason_values: list[str] = []
        applicable = bool(resolved_fundamentals)
        if len(resolved_fundamentals) > 1:
            reason_values.append("l02_fundamental_source_ambiguous")
        if not applicable and declared is not None:
            reason_values.append("l02_unscoped_fundamental_evidence")
        if applicable and not dependencies:
            reason_values.append("l02_fundamental_dependency_evidence_missing")
        if payload is not None and observation is not None:
            if payload.filing_accepted_at > observation.available_at:
                reason_values.append("l02_fundamental_timestamp_order_invalid")
            if payload.filing_accepted_at > sample.decision_time_utc:
                reason_values.append("l02_fundamental_acceptance_future")
            if observation.available_at > sample.decision_time_utc:
                reason_values.append("l02_fundamental_availability_future")
            if declared is not None and not declared_matches:
                reason_values.append("l02_declared_revision_evidence_mismatch")

        reasons = _reasons(*reason_values)
        if reasons:
            affected.add(sample.sample_id)
        records.append(
            _evidence(
                L02FundamentalRevisionEvidence,
                sample_id=sample.sample_id,
                fundamental_dependency_ids=dependencies,
                applicable=applicable,
                non_applicability_reason=("no_fundamental_dependency" if not applicable else None),
                source_observation_refs=tuple(item.reference() for item in resolved_fundamentals),
                evidence_dependency_ids=dependencies,
                revision_id=revision_id,
                accepted_at_utc=(payload.filing_accepted_at if payload is not None else None),
                available_at_utc=(observation.available_at if observation is not None else None),
                revision_trace_ids=revision_trace,
                decision_time_utc=sample.decision_time_utc,
                declared_revision_evidence_present=declared is not None,
                declared_revision_matches_source=declared_matches,
                passed=not reasons,
                reason_codes=reasons,
            )
        )
    return _finding(
        code=LeakageCode.L02,
        samples=samples,
        affected=affected,
        evidence_rule=(
            "fundamental dependencies require accepted/available timestamps and a complete "
            "revision trace; non-applicability requires no fundamental dependency"
        ),
        evidence_records=tuple(records),
    )


def _l03_feature_availability_finding(
    samples: tuple[LeakageSampleAuditInput, ...],
    source_observations: tuple[ResolvedSourceObservation, ...],
) -> LeakageFinding:
    sources_by_key: dict[tuple[str, str], list[ResolvedSourceObservation]] = {}
    for source in source_observations:
        sources_by_key.setdefault(_key_tuple(source.key), []).append(source)

    affected: set[str] = set()
    records: list[L03FeatureAvailabilityEvidence] = []
    for sample in samples:
        declared_refs = tuple(getattr(sample, "source_observation_refs", ()))
        declared_refs_by_key: dict[tuple[str, str], list[ResolvedSourceObservationRef]] = {}
        for ref in declared_refs:
            declared_refs_by_key.setdefault(
                (str(ref.capability), str(ref.normalized_observation_id)),
                [],
            ).append(ref)

        unique_keys = {_key_tuple(key): key for key in sample.source_observation_keys}
        source_intervals: list[L03SourceInformationIntervalEvidence] = []
        for key_tuple in sorted(unique_keys):
            source_key = unique_keys[key_tuple]
            source_matches = sources_by_key.get(key_tuple, [])
            resolved_source = source_matches[0] if len(source_matches) == 1 else None
            resolved_ref = resolved_source.reference() if resolved_source is not None else None
            if declared_refs:
                declared_matches = declared_refs_by_key.get(key_tuple, [])
                declared_ref = declared_matches[0] if len(declared_matches) == 1 else None
                declared_count = len(declared_matches)
            else:
                declared_ref = resolved_ref
                declared_count = 1 if resolved_ref is not None else 0
            exact_reference_matches = bool(
                len(source_matches) == 1
                and declared_count == 1
                and declared_ref is not None
                and resolved_ref is not None
                and declared_ref == resolved_ref
            )
            source_intervals.append(
                L03SourceInformationIntervalEvidence(
                    source_observation_key=source_key,
                    declared_source_observation_ref=declared_ref,
                    declared_reference_count=declared_count,
                    resolved_source_observation_ref=resolved_ref,
                    source_resolution_count=len(source_matches),
                    source_event_time_utc=(
                        resolved_source.normalized_observation.event_time
                        if resolved_source is not None
                        else None
                    ),
                    source_available_at_utc=(
                        resolved_source.normalized_observation.available_at
                        if resolved_source is not None
                        else None
                    ),
                    exact_reference_matches=exact_reference_matches,
                )
            )

        reason_values: list[str] = []
        if not source_intervals:
            reason_values.append("l03_source_observation_keys_missing")
        if sample.feature_available_at_utc > sample.decision_time_utc:
            reason_values.append("l03_feature_available_after_decision")
        for interval in source_intervals:
            if (
                interval.source_resolution_count != 1
                or interval.resolved_source_observation_ref is None
            ):
                reason_values.append("l03_source_observation_missing_or_ambiguous")
            elif not interval.exact_reference_matches:
                reason_values.append("l03_source_observation_ref_mismatch")
            if interval.source_event_time_utc is None or interval.source_available_at_utc is None:
                reason_values.append("l03_source_timestamp_evidence_missing")
                continue
            if interval.source_event_time_utc > sample.feature_available_at_utc:
                reason_values.append("l03_source_event_after_feature_available")
            if interval.source_available_at_utc > sample.feature_available_at_utc:
                reason_values.append("l03_source_available_after_feature_available")
        reasons = _reasons(*reason_values)
        passed = not reasons
        if reasons:
            affected.add(sample.sample_id)
        records.append(
            _evidence(
                L03FeatureAvailabilityEvidence,
                sample_id=sample.sample_id,
                source_information_intervals=tuple(source_intervals),
                feature_available_at_utc=sample.feature_available_at_utc,
                decision_time_utc=sample.decision_time_utc,
                passed=passed,
                reason_codes=reasons,
            )
        )
    return _finding(
        code=LeakageCode.L03,
        samples=samples,
        affected=affected,
        evidence_rule=(
            "every exact source event/availability timestamp must be at or before the frozen "
            "feature availability timestamp, which must be at or before decision time"
        ),
        evidence_records=tuple(records),
    )


def _dependency_overlap(
    feature_dependency_ids: tuple[str, ...],
    target_dependency_ids: tuple[str, ...],
) -> tuple[str, ...]:
    return tuple(sorted(set(feature_dependency_ids) & set(target_dependency_ids)))


def _adversarial_overlap_scan(
    injected_feature_dependency_ids: tuple[str, ...],
    candidate_dependency_id: str,
) -> tuple[str, ...]:
    """Run the production overlap scanner against one injected derived node."""

    return _dependency_overlap(injected_feature_dependency_ids, (candidate_dependency_id,))


def run_adversarial_dependency_review(
    sample: LeakageSampleAuditInput,
    feature_specification: FeatureSpecification,
    label_specification: LabelSpecification,
) -> AdversarialDependencyReview:
    graph = derive_dependency_graph(sample, feature_specification, label_specification)
    feature_ids = tuple(node.dependency_id for node in graph.feature_nodes)
    candidates = tuple(node.dependency_id for node in graph.label_nodes)
    probes: list[AdversarialDependencyProbe] = []
    for candidate in candidates:
        injected = tuple(sorted({*feature_ids, candidate}))
        try:
            detected = _adversarial_overlap_scan(injected, candidate)
            scanner_succeeded = detected == (candidate,)
        except Exception:  # pragma: no cover - defensive fail-closed artifact path
            detected = ()
            scanner_succeeded = False
        probes.append(
            AdversarialDependencyProbe(
                candidate_dependency_id=candidate,
                injected_feature_dependency_ids=injected,
                detected_overlap_ids=detected,
                scanner_succeeded=scanner_succeeded,
                caught=candidate in detected,
            )
        )
    content = {
        "schema_version": "phase5-adversarial-dependency-review-v1",
        "sample_id": sample.sample_id,
        "dependency_graph_sha256": graph.graph_sha256,
        "baseline_feature_dependency_ids": feature_ids,
        "adversarial_candidate_dependency_ids": candidates,
        "probes": tuple(probes),
        "review_complete": bool(candidates) and all(probe.caught for probe in probes),
    }
    return AdversarialDependencyReview.model_validate(
        {
            **content,
            "review_sha256": domain_sha256(
                PHASE5_ADVERSARIAL_DEPENDENCY_REVIEW_HASH_DOMAIN,
                content,
            ),
        }
    )


def _l04_dependency_finding(
    samples: tuple[LeakageSampleAuditInput, ...],
    feature_specification: FeatureSpecification,
    label_specification: LabelSpecification,
) -> LeakageFinding:
    affected: set[str] = set()
    records: list[L04DependencyScanEvidence] = []
    for sample in samples:
        graph = derive_dependency_graph(sample, feature_specification, label_specification)
        feature_ids = tuple(node.dependency_id for node in graph.feature_nodes)
        target_ids = tuple(
            node.dependency_id for node in graph.label_nodes if node.node_kind == "label"
        )
        baseline_overlap = _dependency_overlap(feature_ids, target_ids)
        review = run_adversarial_dependency_review(
            sample,
            feature_specification,
            label_specification,
        )
        expected_source_fields = tuple(
            f"{node.source_observation_key.capability.value}.{node.source_payload_field}"
            for node in graph.feature_nodes
        )
        feature_spec_matches = (
            feature_specification.source_fields == expected_source_fields
            and feature_specification.formula_id == sample.feature_derivation.formula_id
        )
        label_spec_matches = all(
            node.label_formula_id == label_specification.formula_id
            and node.label_specification_sha256 == label_specification.content_sha256
            for node in graph.label_nodes
        )
        reason_values: list[str] = []
        if sample.feature_dependency_ids != feature_ids:
            reason_values.append("l04_feature_dependency_graph_mismatch")
        if sample.target_dependency_ids != target_ids:
            reason_values.append("l04_target_dependency_graph_mismatch")
        if not feature_spec_matches:
            reason_values.append("l04_feature_specification_graph_mismatch")
        if not label_spec_matches:
            reason_values.append("l04_label_specification_graph_mismatch")
        if baseline_overlap:
            reason_values.append("l04_target_or_future_proxy_detected")
        if not review.review_complete:
            reason_values.append("l04_adversarial_review_incomplete")
        reasons = _reasons(*reason_values)
        if reasons:
            affected.add(sample.sample_id)
        records.append(
            _evidence(
                L04DependencyScanEvidence,
                sample_id=sample.sample_id,
                dependency_graph=graph,
                declared_feature_dependency_ids=sample.feature_dependency_ids,
                declared_target_dependency_ids=sample.target_dependency_ids,
                derived_feature_dependency_ids=feature_ids,
                derived_target_dependency_ids=target_ids,
                feature_specification_matches_graph=feature_spec_matches,
                label_specification_matches_graph=label_spec_matches,
                baseline_overlap_ids=baseline_overlap,
                adversarial_review=review,
                passed=not reasons,
                reason_codes=reasons,
            )
        )
    return _finding(
        code=LeakageCode.L04,
        samples=samples,
        affected=affected,
        evidence_rule=(
            "feature/target dependencies must be disjoint and every independently injected "
            "target dependency must be detected by the deterministic adversarial review"
        ),
        evidence_records=tuple(records),
    )


def _l05_membership_finding(
    samples: tuple[LeakageSampleAuditInput, ...],
    source_observations: tuple[ResolvedSourceObservation, ...],
) -> LeakageFinding:
    sources = {_key_tuple(item.key): item for item in source_observations}
    affected: set[str] = set()
    records: list[L05MembershipReconstructionEvidence] = []
    for sample in samples:
        membership_sources = tuple(
            source
            for key in sample.source_observation_keys
            if key.capability is DataCapability.UNIVERSE_MEMBERSHIP
            and (source := sources.get(_key_tuple(key))) is not None
            and isinstance(source.normalized_observation.payload, UniverseMembershipPayload)
        )
        source = membership_sources[0] if len(membership_sources) == 1 else None
        observation = source.normalized_observation if source is not None else None
        payload = (
            observation.payload
            if observation is not None
            and isinstance(observation.payload, UniverseMembershipPayload)
            else None
        )
        feature_source = sources.get(_key_tuple(sample.feature_derivation.source_observation_key))
        feature_observation = (
            feature_source.normalized_observation if feature_source is not None else None
        )
        identity_matches = bool(
            observation is not None
            and feature_observation is not None
            and observation.instrument_id == feature_observation.instrument_id
            and observation.listing_id == feature_observation.listing_id
        )
        declared = sample.universe_membership
        membership_id = (
            str(observation.normalized_observation_id) if observation is not None else None
        )
        status = payload.status.value if payload is not None else None
        declared_matches = bool(
            declared is not None
            and observation is not None
            and payload is not None
            and declared.membership_id == membership_id
            and declared.universe_id == payload.universe_id
            and declared.membership_status == status
            and declared.as_of_utc == observation.available_at
            and declared.valid_from_utc == observation.valid_from
            and declared.valid_to_utc == observation.valid_to
        )
        reason_values: list[str] = []
        if source is None or observation is None or payload is None:
            as_of_known = False
            interval_contains = False
            reconstructed_included = False
            reason_values.append("l05_membership_source_missing_or_ambiguous")
        else:
            as_of_known = observation.available_at <= sample.decision_time_utc
            interval_contains = observation.valid_from <= sample.decision_time_utc and (
                observation.valid_to is None or sample.decision_time_utc < observation.valid_to
            )
            reconstructed_included = (
                status == "included"
                and as_of_known
                and interval_contains
                and identity_matches
                and declared_matches
            )
            if not as_of_known:
                reason_values.append("l05_membership_as_of_future")
            if observation.valid_from > sample.decision_time_utc:
                reason_values.append("l05_membership_valid_from_future")
            if (
                observation.valid_to is not None
                and sample.decision_time_utc >= observation.valid_to
            ):
                reason_values.append("l05_membership_validity_expired")
            if observation.valid_to is not None and observation.valid_to <= observation.valid_from:
                reason_values.append("l05_membership_interval_invalid")
            if status != "included":
                reason_values.append("l05_membership_not_included")
            if not identity_matches:
                reason_values.append("l05_membership_feature_identity_mismatch")
            if not declared_matches:
                reason_values.append("l05_declared_membership_mismatch")

        reasons = _reasons(*reason_values)
        if reasons:
            affected.add(sample.sample_id)
        records.append(
            _evidence(
                L05MembershipReconstructionEvidence,
                sample_id=sample.sample_id,
                source_observation_ref=(source.reference() if source is not None else None),
                membership_id=membership_id,
                universe_id=(payload.universe_id if payload is not None else None),
                membership_status=status,
                as_of_utc=(observation.available_at if observation is not None else None),
                valid_from_utc=(observation.valid_from if observation is not None else None),
                valid_to_utc=(observation.valid_to if observation is not None else None),
                decision_time_utc=sample.decision_time_utc,
                as_of_known_at_decision=as_of_known,
                interval_contains_decision=interval_contains,
                reconstructed_included=reconstructed_included,
                feature_source_identity_matches=identity_matches,
                declared_membership_matches_source=declared_matches,
                passed=not reasons,
                reason_codes=reasons,
            )
        )
    return _finding(
        code=LeakageCode.L05,
        samples=samples,
        affected=affected,
        evidence_rule=(
            "reconstruct included membership as known by decision time within "
            "[valid_from, valid_to)"
        ),
        evidence_records=tuple(records),
    )


def _l06_preprocessing_finding(
    samples: tuple[SyntheticSample, ...],
    folds: tuple[FoldRecord, ...],
    preprocessing_fits: tuple[PreprocessingFitRecord, ...],
) -> LeakageFinding:
    samples_by_id = {sample.sample_id: sample for sample in samples}

    def invalid_fit_ids(
        fold_fits: list[PreprocessingFitRecord],
    ) -> tuple[UUID, ...]:
        invalid: list[UUID] = []
        for fit in fold_fits:
            try:
                PreprocessingFitRecord.model_validate(fit.model_dump(mode="python"))
            except ValueError:
                invalid.append(fit.fit_id)
                continue
            if any(
                (sample := samples_by_id.get(item.sample_id)) is None
                or item.sample_sha256 != domain_sha256(PHASE5_SAMPLE_HASH_DOMAIN, sample)
                or item.value != sample.feature_value
                for item in fit.train_sample_values
            ):
                invalid.append(fit.fit_id)
        return tuple(invalid)

    affected: set[str] = set()
    records: list[L06TrainOnlyFitEvidence] = []
    fits_by_fold: dict[object, list[PreprocessingFitRecord]] = {}
    for fit in preprocessing_fits:
        fits_by_fold.setdefault(fit.fold_id, []).append(fit)

    if not folds:
        records.append(
            _evidence(
                L06TrainOnlyFitEvidence,
                fold_id=None,
                fold_sha256=None,
                fit_ids=(),
                fit_sha256s=(),
                expected_train_sample_ids=(),
                observed_fit_train_sample_ids=(),
                missing_train_sample_ids=(),
                unexpected_train_sample_ids=(),
                disallowed_train_sample_ids=(),
                invalid_fit_ids=(),
                exact_one_fit=False,
                fold_hashes_match=False,
                fit_statistics_match_source_values=True,
                passed=False,
                reason_codes=("l06_fold_evidence_missing",),
            )
        )

    fold_ids = {fold.fold_id for fold in folds}
    for fold in folds:
        expected = set(fold.train_sample_ids)
        fold_fits = sorted(fits_by_fold.get(fold.fold_id, []), key=lambda item: str(item.fit_id))
        observed = set().union(*(set(fit.train_sample_ids) for fit in fold_fits))
        missing = expected - observed
        unexpected = observed - expected
        disallowed = observed & set(
            (*fold.test_sample_ids, *fold.purged_sample_ids, *fold.embargoed_sample_ids)
        )
        invalid_ids = invalid_fit_ids(fold_fits)
        fold_hashes_match = bool(fold_fits) and all(
            fit.fold_sha256 == fold.fold_sha256 for fit in fold_fits
        )
        reason_values: list[str] = []
        if len(fold_fits) != 1:
            reason_values.append("l06_exactly_one_fold_fit_required")
        if missing or unexpected:
            reason_values.append("l06_fit_train_ids_mismatch")
        if disallowed:
            reason_values.append("l06_disallowed_fold_partition_ids")
        if not fold_hashes_match:
            reason_values.append("l06_fit_fold_hash_mismatch")
        if invalid_ids:
            reason_values.append("l06_fit_semantic_preimage_mismatch")
        reasons = _reasons(*reason_values)
        if reasons:
            affected.update(missing)
            affected.update(unexpected)
            affected.update(disallowed)
            if not missing and not unexpected and not disallowed:
                affected.update(expected)
        records.append(
            _evidence(
                L06TrainOnlyFitEvidence,
                fold_id=fold.fold_id,
                fold_sha256=fold.fold_sha256,
                fit_ids=tuple(fit.fit_id for fit in fold_fits),
                fit_sha256s=tuple(fit.fit_sha256 for fit in fold_fits),
                expected_train_sample_ids=tuple(sorted(expected)),
                observed_fit_train_sample_ids=tuple(sorted(observed)),
                missing_train_sample_ids=tuple(sorted(missing)),
                unexpected_train_sample_ids=tuple(sorted(unexpected)),
                disallowed_train_sample_ids=tuple(sorted(disallowed)),
                invalid_fit_ids=invalid_ids,
                exact_one_fit=len(fold_fits) == 1,
                fold_hashes_match=fold_hashes_match,
                fit_statistics_match_source_values=not invalid_ids,
                passed=not reasons,
                reason_codes=reasons,
            )
        )

    for fit in sorted(preprocessing_fits, key=lambda item: (str(item.fold_id), str(item.fit_id))):
        if fit.fold_id in fold_ids:
            continue
        unknown_observed = tuple(sorted(set(fit.train_sample_ids)))
        unknown_invalid_ids = invalid_fit_ids([fit])
        unknown_reasons = [
            "l06_fit_references_unknown_fold",
            "l06_fit_train_ids_mismatch",
        ]
        if unknown_invalid_ids:
            unknown_reasons.append("l06_fit_semantic_preimage_mismatch")
        affected.update(unknown_observed)
        records.append(
            _evidence(
                L06TrainOnlyFitEvidence,
                fold_id=fit.fold_id,
                fold_sha256=None,
                fit_ids=(fit.fit_id,),
                fit_sha256s=(fit.fit_sha256,),
                expected_train_sample_ids=(),
                observed_fit_train_sample_ids=unknown_observed,
                missing_train_sample_ids=(),
                unexpected_train_sample_ids=unknown_observed,
                disallowed_train_sample_ids=(),
                invalid_fit_ids=unknown_invalid_ids,
                exact_one_fit=True,
                fold_hashes_match=False,
                fit_statistics_match_source_values=not unknown_invalid_ids,
                passed=False,
                reason_codes=tuple(sorted(unknown_reasons)),
            )
        )

    return _finding(
        code=LeakageCode.L06,
        samples=samples,
        affected=affected,
        evidence_rule=(
            "every fold has exactly one fit whose immutable fit id/hash and train ids exactly "
            "match the fold train ids"
        ),
        evidence_records=tuple(records),
    )


def evaluate_leakage_context(
    samples: tuple[LeakageSampleAuditInput, ...],
    source_observations: tuple[ResolvedSourceObservation, ...] = (),
    *,
    feature_specification: FeatureSpecification,
    label_specification: LabelSpecification,
) -> tuple[LeakageFinding, LeakageFinding, LeakageFinding, LeakageFinding, LeakageFinding]:
    """Reproduce L01-L05 from the exact sample/source audit preimage."""

    return (
        _l01_price_basis_finding(samples, source_observations),
        _l02_fundamental_finding(samples, source_observations),
        _l03_feature_availability_finding(samples, source_observations),
        _l04_dependency_finding(samples, feature_specification, label_specification),
        _l05_membership_finding(samples, source_observations),
    )


def evaluate_leakage(
    samples: tuple[SyntheticSample, ...],
    folds: tuple[FoldRecord, ...] = (),
    preprocessing_fits: tuple[PreprocessingFitRecord, ...] = (),
    source_observations: tuple[ResolvedSourceObservation, ...] = (),
    *,
    feature_specification: FeatureSpecification,
    label_specification: LabelSpecification,
) -> tuple[LeakageFinding, ...]:
    """Derive every leakage finding from complete concrete immutable evidence."""

    return (
        *evaluate_leakage_context(
            samples,
            source_observations,
            feature_specification=feature_specification,
            label_specification=label_specification,
        ),
        _l06_preprocessing_finding(samples, folds, preprocessing_fits),
    )


def pit_blocking_sample_ids(
    samples: tuple[SyntheticSample, ...],
    findings: tuple[LeakageFinding, ...] | None = None,
) -> tuple[str, ...]:
    if findings is None:
        raise ValueError("point-in-time blockers require complete derived leakage findings")
    derived = findings
    affected = {
        sample_id
        for finding in derived
        if finding.code in {LeakageCode.L01, LeakageCode.L02, LeakageCode.L03, LeakageCode.L05}
        for sample_id in finding.affected_sample_ids
    }
    affected.update(
        sample.sample_id
        for sample in samples
        if sample.rate_available_at_utc > sample.decision_time_utc
        or not sample.delisting_return_handled
    )
    return _ordered_sample_ids(samples, affected)


__all__ = [
    "LeakageFinding",
    "evaluate_leakage",
    "evaluate_leakage_context",
    "pit_blocking_sample_ids",
    "run_adversarial_dependency_review",
]
