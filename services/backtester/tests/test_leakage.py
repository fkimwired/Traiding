from __future__ import annotations

import json
from datetime import timedelta
from decimal import Decimal
from uuid import UUID

import fable5_backtester.leakage as leakage_module
import pytest
from fable5_backtester.canonical import (
    PHASE5_FIT_HASH_DOMAIN,
    PHASE5_FIT_NAMESPACE,
    PHASE5_LEAKAGE_EVIDENCE_HASH_DOMAIN,
    PHASE5_TRAIN_ONLY_FIT_HASH_DOMAIN,
    canonical_json_text,
    domain_sha256,
    identity,
)
from fable5_backtester.contracts import (
    FundamentalRevisionEvidence,
    L01PriceBasisEvidence,
    L02FundamentalRevisionEvidence,
    L03FeatureAvailabilityEvidence,
    L03SourceInformationIntervalEvidence,
    L04DependencyScanEvidence,
    L05MembershipReconstructionEvidence,
    L06TrainOnlyFitEvidence,
    LeakageCode,
    PreprocessingFitRecord,
    ResolvedSourceObservation,
    SourceObservationKey,
    SyntheticSample,
)
from fable5_backtester.engine import _build_preprocessing_fits
from fable5_backtester.evaluation_geometry import build_evaluation_geometry
from fable5_backtester.leakage import LeakageFinding, evaluate_leakage, pit_blocking_sample_ids
from fable5_backtester.synthetic import REGISTERED_FIXTURE, REGISTERED_POLICY
from fable5_data.contracts import (
    ConstituentDisposition,
    DataCapability,
    NormalizedObservation,
)
from fable5_data.synthetic import SyntheticPointInTimeAdapter
from pydantic import ValidationError

GEOMETRY = build_evaluation_geometry(
    policy=REGISTERED_POLICY,
    walk_forward=REGISTERED_POLICY.walk_forward,
    fixture=REGISTERED_FIXTURE,
)
FOLDS = GEOMETRY.folds
FITS = _build_preprocessing_fits(FOLDS, REGISTERED_FIXTURE)
SOURCE_EXPECTATION = next(
    item
    for item in REGISTERED_FIXTURE.source_observation_expectations
    if str(item.key.capability) == "ohlcv"
)
SOURCE_OBSERVATIONS = tuple(
    ResolvedSourceObservation(
        key=expectation.key,
        normalized_observation=NormalizedObservation.model_validate(
            {
                **expectation.normalized_observation.model_dump(mode="python"),
                "snapshot_id": UUID(
                    "bbbbbbbb-bbbb-5bbb-8bbb-bbbbbbbbbbbb"
                    if expectation is SOURCE_EXPECTATION
                    else "cccccccc-cccc-5ccc-8ccc-cccccccccccc"
                ),
                "snapshot_sha256": "b" * 64 if expectation is SOURCE_EXPECTATION else "c" * 64,
            }
        ),
        disposition=expectation.required_disposition,
    )
    for expectation in REGISTERED_FIXTURE.source_observation_expectations
)


def _findings(
    samples: tuple[SyntheticSample, ...],
    *,
    fits: tuple[PreprocessingFitRecord, ...] = FITS,
    sources: tuple[ResolvedSourceObservation, ...] = SOURCE_OBSERVATIONS,
) -> dict[LeakageCode, LeakageFinding]:
    return {
        finding.code: finding
        for finding in evaluate_leakage(
            samples,
            FOLDS,
            fits,
            sources,
            feature_specification=REGISTERED_POLICY.feature_specification,
            label_specification=REGISTERED_POLICY.label_specification,
        )
    }


def _single_sample_mutation(mutated: SyntheticSample) -> tuple[SyntheticSample, ...]:
    return (mutated, *REGISTERED_FIXTURE.samples[1:])


def _late_fundamental_update(original: SyntheticSample) -> dict[str, object]:
    dependency = "phase4-as-reported-fundamental.revenue"
    dependencies = tuple(sorted((*original.feature_dependency_ids, dependency)))
    revision_id = "synthetic-late-fundamental-revision"
    return {
        "feature_dependency_ids": dependencies,
        "fundamental_revision": FundamentalRevisionEvidence(
            dependency_ids=(dependency,),
            revision_id=revision_id,
            accepted_at_utc=original.decision_time_utc - timedelta(microseconds=1),
            available_at_utc=original.decision_time_utc + timedelta(microseconds=1),
            revision_trace_ids=("synthetic-parent-fundamental-revision", revision_id),
        ),
    }


def _contaminated_fits() -> tuple[tuple[PreprocessingFitRecord, ...], str]:
    fold = FOLDS[0]
    fit_index = next(index for index, fit in enumerate(FITS) if fit.fold_id == fold.fold_id)
    fit = FITS[fit_index]
    unexpected_sample_id = fold.test_sample_ids[0]
    contaminated = fit.model_copy(
        update={"train_sample_ids": tuple(sorted((*fit.train_sample_ids, unexpected_sample_id)))}
    )
    return (*FITS[:fit_index], contaminated, *FITS[fit_index + 1 :]), unexpected_sample_id


def test_registered_fixture_has_complete_clean_immutable_evidence_for_all_six_checks() -> None:
    findings = evaluate_leakage(
        REGISTERED_FIXTURE.samples,
        FOLDS,
        FITS,
        SOURCE_OBSERVATIONS,
        feature_specification=REGISTERED_POLICY.feature_specification,
        label_specification=REGISTERED_POLICY.label_specification,
    )

    assert tuple(finding.code for finding in findings) == tuple(LeakageCode)
    assert all(finding.blocked is False for finding in findings)
    assert all(finding.affected_sample_ids == () for finding in findings)
    assert all(finding.evidence_records for finding in findings)
    assert all(
        record.passed and not record.reason_codes
        for finding in findings
        for record in finding.evidence_records
    )
    assert pit_blocking_sample_ids(REGISTERED_FIXTURE.samples, findings) == ()

    l01 = findings[0].evidence_records[0]
    assert isinstance(l01, L01PriceBasisEvidence)
    assert l01.source_snapshot_id == SOURCE_OBSERVATIONS[0].normalized_observation.snapshot_id
    assert l01.source_price == l01.effective_price == REGISTERED_FIXTURE.samples[0].reference_price
    assert l01.source_adjustment_basis == "as_of_adjusted"
    assert l01.effective_price_basis == "adjusted_for_corporate_action"
    assert l01.action_as_of_values_match is True

    l02 = findings[1].evidence_records[0]
    assert isinstance(l02, L02FundamentalRevisionEvidence)
    assert l02.applicable is False
    assert l02.non_applicability_reason == "no_fundamental_dependency"
    assert l02.fundamental_dependency_ids == l02.evidence_dependency_ids == ()

    l03 = findings[2].evidence_records[0]
    assert isinstance(l03, L03FeatureAvailabilityEvidence)
    assert l03.feature_available_at_utc <= l03.decision_time_utc
    assert tuple(item.source_observation_key for item in l03.source_information_intervals) == (
        REGISTERED_FIXTURE.samples[0].source_observation_keys
    )
    for interval in l03.source_information_intervals:
        assert isinstance(interval, L03SourceInformationIntervalEvidence)
        source = next(
            item for item in SOURCE_OBSERVATIONS if item.key == interval.source_observation_key
        )
        assert interval.declared_reference_count == interval.source_resolution_count == 1
        assert interval.declared_source_observation_ref == source.reference()
        assert interval.resolved_source_observation_ref == source.reference()
        assert interval.source_event_time_utc == source.normalized_observation.event_time
        assert interval.source_available_at_utc == source.normalized_observation.available_at
        assert interval.source_event_time_utc <= l03.feature_available_at_utc
        assert interval.source_available_at_utc <= l03.feature_available_at_utc
        assert interval.exact_reference_matches is True

    l04 = findings[3].evidence_records[0]
    assert isinstance(l04, L04DependencyScanEvidence)
    assert l04.baseline_overlap_ids == ()
    assert l04.adversarial_review.review_complete is True
    assert len(l04.adversarial_review.review_sha256) == 64
    assert all(probe.caught for probe in l04.adversarial_review.probes)

    l05 = findings[4].evidence_records[0]
    assert isinstance(l05, L05MembershipReconstructionEvidence)
    assert l05.as_of_known_at_decision is True
    assert l05.interval_contains_decision is True
    assert l05.reconstructed_included is True

    assert all(
        isinstance(record, L06TrainOnlyFitEvidence)
        and record.exact_one_fit
        and record.expected_train_sample_ids == record.observed_fit_train_sample_ids
        for record in findings[5].evidence_records
    )


def test_l01_compares_resolved_phase4_price_basis_and_action_as_of() -> None:
    original = REGISTERED_FIXTURE.samples[0]
    mutated = original.model_copy(
        update={
            "price_adjustment_basis": "raw_unadjusted",
            "adjustment_action_as_of_utc": original.decision_time_utc + timedelta(microseconds=1),
        }
    )
    finding = _findings(_single_sample_mutation(mutated))[LeakageCode.L01]
    record = finding.evidence_records[0]

    assert isinstance(record, L01PriceBasisEvidence)
    assert finding.affected_sample_ids == (original.sample_id,)
    assert record.source_adjustment_as_of_utc != record.effective_adjustment_as_of_utc
    assert record.action_as_of_values_match is False
    assert record.price_bases_match is False
    assert set(record.reason_codes) == {
        "l01_adjustment_action_future",
        "l01_source_effective_action_as_of_mismatch",
        "l01_source_effective_basis_mismatch",
    }


def test_l02_rejects_invented_fundamental_revision_without_resolved_source() -> None:
    original = REGISTERED_FIXTURE.samples[0]
    mutated = original.model_copy(update=_late_fundamental_update(original))
    finding = _findings(_single_sample_mutation(mutated))[LeakageCode.L02]
    record = finding.evidence_records[0]

    assert isinstance(record, L02FundamentalRevisionEvidence)
    assert finding.affected_sample_ids == (original.sample_id,)
    assert record.applicable is False
    assert record.source_observation_refs == ()
    assert record.declared_revision_evidence_present is True
    assert record.declared_revision_matches_source is False
    assert record.reason_codes == ("l02_unscoped_fundamental_evidence",)


def test_l02_applicability_and_late_revision_are_derived_from_exact_resolved_source() -> None:
    original = REGISTERED_FIXTURE.samples[0]
    draft = (
        SyntheticPointInTimeAdapter()
        .fetch(DataCapability.AS_REPORTED_FUNDAMENTALS)
        .batch.normalized_observations[0]
    )
    key = SourceObservationKey(
        capability=DataCapability.AS_REPORTED_FUNDAMENTALS,
        normalized_observation_id=draft.normalized_observation_id,
    )
    resolved = ResolvedSourceObservation(
        key=key,
        normalized_observation=NormalizedObservation.model_validate(
            {
                **draft.model_dump(mode="python"),
                "snapshot_id": UUID("dddddddd-dddd-5ddd-8ddd-dddddddddddd"),
                "snapshot_sha256": "d" * 64,
            }
        ),
        disposition=ConstituentDisposition.INCLUDED_AS_OF,
    )
    dependency = f"phase4-as-reported-fundamentals.{draft.payload.concept_id}"
    declared = FundamentalRevisionEvidence(
        dependency_ids=(dependency,),
        revision_id=draft.revision_id,
        accepted_at_utc=draft.payload.filing_accepted_at,
        available_at_utc=draft.available_at,
        revision_trace_ids=(draft.revision_id,),
    )
    mutated = original.model_copy(
        update={
            "source_observation_keys": tuple(
                sorted(
                    (*original.source_observation_keys, key),
                    key=lambda item: (str(item.capability), str(item.normalized_observation_id)),
                )
            ),
            "fundamental_revision": declared,
        }
    )
    finding = _findings(
        _single_sample_mutation(mutated),
        sources=(*SOURCE_OBSERVATIONS, resolved),
    )[LeakageCode.L02]
    record = finding.evidence_records[0]

    assert isinstance(record, L02FundamentalRevisionEvidence)
    assert record.applicable is True
    assert record.source_observation_refs == (resolved.reference(),)
    assert record.fundamental_dependency_ids == (dependency,)
    assert record.declared_revision_matches_source is True
    assert set(record.reason_codes) == {
        "l02_fundamental_acceptance_future",
        "l02_fundamental_availability_future",
    }


def test_l03_records_row_level_feature_availability_assertion() -> None:
    original = REGISTERED_FIXTURE.samples[0]
    mutated = original.model_copy(
        update={"feature_available_at_utc": original.decision_time_utc + timedelta(microseconds=1)}
    )
    samples = _single_sample_mutation(mutated)
    findings = _findings(samples)
    record = findings[LeakageCode.L03].evidence_records[0]

    assert isinstance(record, L03FeatureAvailabilityEvidence)
    assert record.assertion == (
        "source_event_time_utc<=feature_available_at_utc;"
        "source_available_at_utc<=feature_available_at_utc<=decision_time_utc"
    )
    assert record.reason_codes == ("l03_feature_available_after_decision",)
    assert pit_blocking_sample_ids(samples, tuple(findings.values())) == (original.sample_id,)


def test_l03_blocks_feature_timestamp_one_microsecond_before_bound_source_availability() -> None:
    original = REGISTERED_FIXTURE.samples[0]
    source = next(
        item for item in SOURCE_OBSERVATIONS if item.key.capability is DataCapability.OHLCV
    )
    mutated = original.model_copy(
        update={
            "feature_available_at_utc": (
                source.normalized_observation.available_at - timedelta(microseconds=1)
            )
        }
    )
    findings = _findings(_single_sample_mutation(mutated))
    record = findings[LeakageCode.L03].evidence_records[0]

    assert isinstance(record, L03FeatureAvailabilityEvidence)
    assert record.reason_codes == ("l03_source_available_after_feature_available",)
    interval = next(
        item
        for item in record.source_information_intervals
        if item.source_observation_key == source.key
    )
    assert interval.source_event_time_utc <= record.feature_available_at_utc
    assert interval.source_available_at_utc > record.feature_available_at_utc
    assert findings[LeakageCode.L03].affected_sample_ids == (original.sample_id,)


def test_l03_blocks_source_event_and_availability_after_frozen_feature_timestamp() -> None:
    original = REGISTERED_FIXTURE.samples[0]
    source = next(
        item for item in SOURCE_OBSERVATIONS if item.key.capability is DataCapability.OHLCV
    )
    mutated = original.model_copy(
        update={
            "feature_available_at_utc": (
                source.normalized_observation.event_time - timedelta(microseconds=1)
            )
        }
    )
    record = _findings(_single_sample_mutation(mutated))[LeakageCode.L03].evidence_records[0]

    assert isinstance(record, L03FeatureAvailabilityEvidence)
    assert record.reason_codes == (
        "l03_source_available_after_feature_available",
        "l03_source_event_after_feature_available",
    )


def test_l03_missing_exact_source_evidence_fails_closed() -> None:
    original = REGISTERED_FIXTURE.samples[0]
    sources = tuple(
        item for item in SOURCE_OBSERVATIONS if item.key.capability is not DataCapability.OHLCV
    )
    record = _findings(
        _single_sample_mutation(original),
        sources=sources,
    )[LeakageCode.L03].evidence_records[0]

    assert isinstance(record, L03FeatureAvailabilityEvidence)
    assert record.reason_codes == (
        "l03_source_observation_missing_or_ambiguous",
        "l03_source_timestamp_evidence_missing",
    )


def test_l04_records_dependency_scan_and_each_adversarial_injection_probe() -> None:
    original = REGISTERED_FIXTURE.samples[0]
    overlapping_dependency = original.feature_dependency_ids[0]
    mutated = original.model_copy(
        update={
            "target_dependency_ids": tuple(
                sorted((*original.target_dependency_ids, overlapping_dependency))
            )
        }
    )
    finding = _findings(_single_sample_mutation(mutated))[LeakageCode.L04]
    record = finding.evidence_records[0]

    assert isinstance(record, L04DependencyScanEvidence)
    assert finding.affected_sample_ids == (original.sample_id,)
    assert record.baseline_overlap_ids == ()
    assert record.declared_target_dependency_ids != record.derived_target_dependency_ids
    assert record.reason_codes == ("l04_target_dependency_graph_mismatch",)
    assert tuple(
        probe.candidate_dependency_id for probe in record.adversarial_review.probes
    ) == tuple(node.dependency_id for node in record.dependency_graph.label_nodes)
    assert all(probe.caught for probe in record.adversarial_review.probes)


def test_l04_independent_adversarial_review_failure_blocks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(leakage_module, "_adversarial_overlap_scan", lambda *_: ())
    finding = _findings(REGISTERED_FIXTURE.samples)[LeakageCode.L04]

    assert finding.blocked is True
    assert finding.affected_sample_ids == tuple(
        sample.sample_id for sample in REGISTERED_FIXTURE.samples
    )
    assert all(
        isinstance(record, L04DependencyScanEvidence)
        and not record.adversarial_review.review_complete
        and record.reason_codes == ("l04_adversarial_review_incomplete",)
        for record in finding.evidence_records
    )


@pytest.mark.parametrize(
    "update",
    [
        "future_as_of",
        "expired_validity",
        "excluded",
    ],
)
def test_l05_rejects_forged_membership_declaration(update: str) -> None:
    original = REGISTERED_FIXTURE.samples[0]
    membership = original.universe_membership
    assert membership is not None
    membership_update: dict[str, object]
    if update == "future_as_of":
        membership_update = {"as_of_utc": original.decision_time_utc + timedelta(microseconds=1)}
    elif update == "expired_validity":
        membership_update = {"valid_to_utc": original.decision_time_utc}
    else:
        membership_update = {"membership_status": "excluded"}
    mutated = original.model_copy(
        update={"universe_membership": membership.model_copy(update=membership_update)}
    )
    samples = _single_sample_mutation(mutated)
    findings = _findings(samples)
    record = findings[LeakageCode.L05].evidence_records[0]

    assert isinstance(record, L05MembershipReconstructionEvidence)
    assert record.reconstructed_included is False
    assert record.as_of_known_at_decision is True
    assert record.interval_contains_decision is True
    assert record.feature_source_identity_matches is True
    assert record.reason_codes == ("l05_declared_membership_mismatch",)
    assert pit_blocking_sample_ids(samples, tuple(findings.values())) == (original.sample_id,)


def test_l05_rejects_exact_phase4_excluded_future_membership_source() -> None:
    original = REGISTERED_FIXTURE.samples[0]
    included_key = next(
        key
        for key in original.source_observation_keys
        if key.capability is DataCapability.UNIVERSE_MEMBERSHIP
    )
    excluded_draft = (
        SyntheticPointInTimeAdapter()
        .fetch(DataCapability.UNIVERSE_MEMBERSHIP)
        .batch.normalized_observations[1]
    )
    excluded_key = SourceObservationKey(
        capability=DataCapability.UNIVERSE_MEMBERSHIP,
        normalized_observation_id=excluded_draft.normalized_observation_id,
    )
    excluded_source = ResolvedSourceObservation(
        key=excluded_key,
        normalized_observation=NormalizedObservation.model_validate(
            {
                **excluded_draft.model_dump(mode="python"),
                "snapshot_id": UUID("eeeeeeee-eeee-5eee-8eee-eeeeeeeeeeee"),
                "snapshot_sha256": "e" * 64,
            }
        ),
        disposition=ConstituentDisposition.INCLUDED_AS_OF,
    )
    mutated = original.model_copy(
        update={
            "source_observation_keys": tuple(
                sorted(
                    (
                        *(key for key in original.source_observation_keys if key != included_key),
                        excluded_key,
                    ),
                    key=lambda item: (str(item.capability), str(item.normalized_observation_id)),
                )
            )
        }
    )
    sources = (
        *(
            source
            for source in SOURCE_OBSERVATIONS
            if source.key.capability is not DataCapability.UNIVERSE_MEMBERSHIP
        ),
        excluded_source,
    )
    finding = _findings(_single_sample_mutation(mutated), sources=sources)[LeakageCode.L05]
    record = finding.evidence_records[0]

    assert isinstance(record, L05MembershipReconstructionEvidence)
    assert record.source_observation_ref == excluded_source.reference()
    assert record.membership_status == "excluded"
    assert record.as_of_known_at_decision is False
    assert record.interval_contains_decision is False
    assert record.reconstructed_included is False
    assert set(record.reason_codes) == {
        "l05_declared_membership_mismatch",
        "l05_membership_as_of_future",
        "l05_membership_not_included",
        "l05_membership_valid_from_future",
    }


def test_l06_records_exact_fold_fit_ids_hashes_and_train_only_sets() -> None:
    fits, unexpected_sample_id = _contaminated_fits()
    finding = _findings(REGISTERED_FIXTURE.samples, fits=fits)[LeakageCode.L06]
    record = next(
        item
        for item in finding.evidence_records
        if isinstance(item, L06TrainOnlyFitEvidence)
        and unexpected_sample_id in item.unexpected_train_sample_ids
    )

    assert finding.affected_sample_ids == (unexpected_sample_id,)
    assert len(record.fit_ids) == len(record.fit_sha256s) == 1
    assert record.exact_one_fit is True
    assert record.missing_train_sample_ids == ()
    assert record.unexpected_train_sample_ids == (unexpected_sample_id,)
    assert set(record.reason_codes) == {
        "l06_disallowed_fold_partition_ids",
        "l06_fit_semantic_preimage_mismatch",
        "l06_fit_train_ids_mismatch",
    }
    assert record.invalid_fit_ids == record.fit_ids


def test_missing_or_inconsistent_evidence_blocks_as_findings() -> None:
    original = REGISTERED_FIXTURE.samples[0]
    dependency = "phase4-as-reported-fundamental.revenue"
    mutated = original.model_copy(
        update={
            "price_adjustment_basis": None,
            "feature_dependency_ids": tuple(sorted((*original.feature_dependency_ids, dependency))),
            "fundamental_revision": None,
            "target_dependency_ids": (),
            "universe_membership": None,
        }
    )
    findings = _findings(_single_sample_mutation(mutated), sources=())

    assert findings[LeakageCode.L01].blocked
    assert "l01_source_observation_missing" in (
        findings[LeakageCode.L01].evidence_records[0].reason_codes
    )
    l02 = findings[LeakageCode.L02].evidence_records[0]
    assert isinstance(l02, L02FundamentalRevisionEvidence)
    assert l02.applicable is False
    assert l02.reason_codes == ()
    assert findings[LeakageCode.L04].blocked
    assert "l04_target_dependency_graph_mismatch" in (
        findings[LeakageCode.L04].evidence_records[0].reason_codes
    )
    assert findings[LeakageCode.L05].evidence_records[0].reason_codes == (
        "l05_membership_source_missing_or_ambiguous",
    )


def test_one_fixture_catches_all_six_concrete_defects() -> None:
    original = REGISTERED_FIXTURE.samples[0]
    membership = original.universe_membership
    assert membership is not None
    update = _late_fundamental_update(original)
    update.update(
        {
            "adjustment_action_as_of_utc": original.decision_time_utc + timedelta(microseconds=1),
            "feature_available_at_utc": original.decision_time_utc + timedelta(microseconds=1),
            "target_dependency_ids": tuple(
                sorted((*original.target_dependency_ids, original.feature_dependency_ids[0]))
            ),
            "universe_membership": membership.model_copy(
                update={"as_of_utc": original.decision_time_utc + timedelta(microseconds=1)}
            ),
        }
    )
    mutated = original.model_copy(update=update)
    fits, _ = _contaminated_fits()
    findings = _findings(_single_sample_mutation(mutated), fits=fits)

    assert tuple(code for code, finding in findings.items() if finding.blocked) == tuple(
        LeakageCode
    )
    assert all(finding.evidence_records for finding in findings.values())


def test_future_rate_and_unhandled_delisting_remain_exact_pit_blockers() -> None:
    first = REGISTERED_FIXTURE.samples[0]
    second = REGISTERED_FIXTURE.samples[1]
    future_rate = first.model_copy(
        update={"rate_available_at_utc": first.decision_time_utc + timedelta(microseconds=1)}
    )
    unhandled = second.model_copy(update={"delisting_return_handled": False})
    samples = (future_rate, unhandled, *REGISTERED_FIXTURE.samples[2:])
    findings = tuple(_findings(samples).values())

    assert all(
        finding.blocked is False for finding in findings if finding.code is not LeakageCode.L06
    )
    assert next(finding for finding in findings if finding.code is LeakageCode.L06).blocked
    assert pit_blocking_sample_ids(samples, findings) == (first.sample_id, second.sample_id)


@pytest.mark.parametrize("mutation", ("boolean", "reason", "raw"))
def test_leakage_evidence_rejects_semantic_tamper_after_hash_recomputation(
    mutation: str,
) -> None:
    clean = _findings(REGISTERED_FIXTURE.samples)[LeakageCode.L01].evidence_records[0]
    assert isinstance(clean, L01PriceBasisEvidence)
    content = clean.model_dump(mode="python", exclude={"evidence_sha256"})
    if mutation == "boolean":
        content["price_values_match"] = False
    elif mutation == "reason":
        content["passed"] = False
        content["reason_codes"] = ("l01_source_effective_price_mismatch",)
    else:
        assert clean.source_price is not None
        content["source_price"] = clean.source_price + Decimal("1")
    payload = {
        **content,
        "evidence_sha256": domain_sha256(
            PHASE5_LEAKAGE_EVIDENCE_HASH_DOMAIN,
            content,
        ),
    }

    with pytest.raises(ValidationError, match=r"L01|evidence outcome"):
        L01PriceBasisEvidence.model_validate(payload)


def test_preprocessing_fit_rejects_mean_tamper_after_all_hashes_are_recomputed() -> None:
    fit = FITS[0]
    payload = fit.model_dump(mode="python")
    payload["mean"] = fit.mean + Decimal("0.01")
    preimage = {
        "fold_id": payload["fold_id"],
        "fold_sha256": payload["fold_sha256"],
        "transformer_id": payload["transformer_id"],
        "transformer_version": payload["transformer_version"],
        "train_sample_values": payload["train_sample_values"],
        "train_sample_ids": payload["train_sample_ids"],
        "train_sample_ids_sha256": payload["train_sample_ids_sha256"],
        "mean": payload["mean"],
        "standard_deviation": payload["standard_deviation"],
        "ddof": payload["ddof"],
    }
    payload["fit_preimage_canonical_json"] = canonical_json_text(preimage)
    payload["fit_sha256"] = domain_sha256(PHASE5_TRAIN_ONLY_FIT_HASH_DOMAIN, preimage)
    payload["fit_id"] = identity(PHASE5_FIT_NAMESPACE, payload["fit_sha256"])
    payload["statistics_sha256"] = domain_sha256(
        PHASE5_FIT_HASH_DOMAIN,
        {
            "fit_sha256": payload["fit_sha256"],
            "mean": payload["mean"],
            "standard_deviation": payload["standard_deviation"],
            "ddof": payload["ddof"],
        },
    )

    with pytest.raises(
        ValidationError,
        match="statistics must be recomputed from exact train values",
    ):
        PreprocessingFitRecord.model_validate(payload)


def test_preprocessing_fit_canonical_json_round_trip_preserves_exact_statistics() -> None:
    fit = FITS[0]
    serialized = canonical_json_text(fit.model_dump(mode="python"))

    rehydrated = PreprocessingFitRecord.model_validate(json.loads(serialized))

    assert rehydrated.mean == fit.mean
    assert rehydrated.standard_deviation == fit.standard_deviation
    assert rehydrated.fit_preimage_canonical_json == fit.fit_preimage_canonical_json
    assert canonical_json_text(rehydrated.model_dump(mode="python")) == serialized
