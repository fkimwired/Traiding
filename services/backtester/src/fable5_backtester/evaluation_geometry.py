"""Policy-driven, fail-closed Phase 5 evaluation geometry.

This module turns a frozen evaluation policy and a deterministic synthetic fixture into
immutable fold artifacts.  It defines evaluation mechanics only: there are no strategy,
allocation, action, approval, or execution semantics here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Final
from uuid import UUID

from pydantic import ValidationError

from fable5_backtester.canonical import (
    PHASE5_FOLD_HASH_DOMAIN,
    PHASE5_FOLD_NAMESPACE,
    domain_sha256,
    identity,
)
from fable5_backtester.chronology import (
    ChronologicalSplit,
    ChronologyInputError,
    ClosedLabelInterval,
    InformationInterval,
    TestInterval,
    build_purged_split_with_embargo,
    build_strict_past_only_split,
)
from fable5_backtester.contracts import (
    FoldKind,
    FoldRecord,
    FrozenEvaluationPolicy,
    GateCode,
    GateOutcome,
    SyntheticEvaluationFixture,
    TrainMode,
    WalkForwardPolicy,
)

GEOMETRY_VERSION: Final = "phase5-policy-driven-walk-forward-geometry-v1"


class GeometryInputError(ValueError):
    """The frozen policy and fixture cannot produce valid evaluation geometry."""

    def __init__(self, reason_code: str, message: str) -> None:
        super().__init__(message)
        self.reason_code = reason_code


@dataclass(frozen=True, slots=True)
class GeometryValidationResult:
    """Immutable evidence that maps directly onto the ``CV_CHRONOLOGY`` gate."""

    outcome: GateOutcome
    reason_codes: tuple[str, ...]
    message: str
    train_mode: TrainMode | None
    expected_outer_fold_count: int
    expected_inner_folds_per_outer: int
    observed_outer_fold_count: int
    observed_inner_fold_count: int
    minimum_train_observations: int
    research_sample_count: int
    confirmation_sample_count: int
    post_confirmation_sample_count: int
    purged_sample_count: int
    embargoed_sample_count: int
    configured_embargo_seconds: int

    @property
    def gate_code(self) -> GateCode:
        return GateCode.CV_CHRONOLOGY

    @property
    def passed(self) -> bool:
        return self.outcome is GateOutcome.PASS

    def gate_inputs(self) -> dict[str, str | int | bool]:
        """Return scalar inputs accepted by :class:`GateResult`."""

        return {
            "geometry_version": GEOMETRY_VERSION,
            "train_mode": self.train_mode.value if self.train_mode is not None else "missing",
            "research_sample_count": self.research_sample_count,
            "confirmation_sample_count": self.confirmation_sample_count,
            "post_confirmation_sample_count": self.post_confirmation_sample_count,
            "configured_embargo_seconds": self.configured_embargo_seconds,
        }

    def gate_thresholds(self) -> dict[str, str | int | bool]:
        """Return frozen geometry thresholds accepted by :class:`GateResult`."""

        return {
            "expected_outer_fold_count": self.expected_outer_fold_count,
            "expected_inner_folds_per_outer": self.expected_inner_folds_per_outer,
            "minimum_train_observations": self.minimum_train_observations,
            "past_only_requires_zero_embargo": True,
        }

    def gate_results(self) -> dict[str, str | int | bool]:
        """Return computed geometry results accepted by :class:`GateResult`."""

        return {
            "observed_outer_fold_count": self.observed_outer_fold_count,
            "observed_inner_fold_count": self.observed_inner_fold_count,
            "purged_sample_count": self.purged_sample_count,
            "embargoed_sample_count": self.embargoed_sample_count,
            "valid": self.passed,
        }


@dataclass(frozen=True, slots=True)
class EvaluationGeometry:
    """Complete immutable fold geometry or an empty, fail-closed result."""

    folds: tuple[FoldRecord, ...]
    research_sample_ids: tuple[str, ...]
    confirmation_sample_ids: tuple[str, ...]
    post_confirmation_sample_ids: tuple[str, ...]
    validation: GeometryValidationResult


def _empty_validation(
    *,
    outcome: GateOutcome,
    reason_code: str,
    message: str,
    walk_forward: WalkForwardPolicy | None,
    research_sample_count: int = 0,
    confirmation_sample_count: int = 0,
    post_confirmation_sample_count: int = 0,
) -> GeometryValidationResult:
    return GeometryValidationResult(
        outcome=outcome,
        reason_codes=(reason_code,),
        message=message,
        train_mode=walk_forward.train_mode if walk_forward is not None else None,
        expected_outer_fold_count=(walk_forward.outer_fold_count if walk_forward else 0),
        expected_inner_folds_per_outer=(walk_forward.inner_fold_count if walk_forward else 0),
        observed_outer_fold_count=0,
        observed_inner_fold_count=0,
        minimum_train_observations=(walk_forward.minimum_train_observations if walk_forward else 0),
        research_sample_count=research_sample_count,
        confirmation_sample_count=confirmation_sample_count,
        post_confirmation_sample_count=post_confirmation_sample_count,
        purged_sample_count=0,
        embargoed_sample_count=0,
        configured_embargo_seconds=(walk_forward.embargo_seconds or 0 if walk_forward else 0),
    )


def _fail_closed(
    *,
    outcome: GateOutcome,
    reason_code: str,
    message: str,
    walk_forward: WalkForwardPolicy | None,
    research_sample_ids: tuple[str, ...] = (),
    confirmation_sample_ids: tuple[str, ...] = (),
    post_confirmation_sample_ids: tuple[str, ...] = (),
) -> EvaluationGeometry:
    return EvaluationGeometry(
        folds=(),
        research_sample_ids=research_sample_ids,
        confirmation_sample_ids=confirmation_sample_ids,
        post_confirmation_sample_ids=post_confirmation_sample_ids,
        validation=_empty_validation(
            outcome=outcome,
            reason_code=reason_code,
            message=message,
            walk_forward=walk_forward,
            research_sample_count=len(research_sample_ids),
            confirmation_sample_count=len(confirmation_sample_ids),
            post_confirmation_sample_count=len(post_confirmation_sample_ids),
        ),
    )


def _validate_policy_geometry(walk_forward: WalkForwardPolicy) -> None:
    if walk_forward.outer_fold_count < 2 or walk_forward.inner_fold_count < 2:
        raise GeometryInputError(
            "invalid_fold_count",
            "outer and inner fold counts must each be at least two",
        )
    if walk_forward.minimum_train_observations < 2:
        raise GeometryInputError(
            "invalid_minimum_train_observations",
            "minimum training observations must be at least two",
        )
    if walk_forward.outer_test_observations < 1 or walk_forward.inner_test_observations < 1:
        raise GeometryInputError(
            "invalid_test_observation_count",
            "outer and inner test windows must each contain at least one observation",
        )
    if walk_forward.final_confirmation_end_utc <= walk_forward.final_confirmation_start_utc:
        raise GeometryInputError(
            "invalid_final_confirmation_interval",
            "the final confirmation interval must be positive",
        )
    if (walk_forward.embargo_rule is None) != (walk_forward.embargo_seconds is None):
        raise GeometryInputError(
            "incomplete_embargo_policy",
            "embargo rule and duration must be frozen together",
        )
    if (
        walk_forward.train_mode is not TrainMode.PURGED_COMBINATORIAL
        and walk_forward.embargo_seconds is not None
    ):
        raise GeometryInputError(
            "past_only_embargo_forbidden",
            "standard past-only geometry cannot apply a post-test embargo",
        )
    if walk_forward.train_mode is TrainMode.ROLLING_PAST_ONLY:
        if walk_forward.rolling_train_observations is None:
            raise GeometryInputError(
                "missing_rolling_training_window",
                "rolling past-only geometry requires a frozen training window",
            )
        if walk_forward.rolling_train_observations < walk_forward.minimum_train_observations:
            raise GeometryInputError(
                "rolling_window_below_minimum_train",
                "rolling training window is smaller than the minimum training requirement",
            )
    elif walk_forward.rolling_train_observations is not None:
        raise GeometryInputError(
            "unexpected_rolling_training_window",
            "only rolling past-only geometry may define a rolling training window",
        )


def _information_intervals(
    fixture: SyntheticEvaluationFixture,
) -> tuple[InformationInterval, ...]:
    intervals = tuple(
        InformationInterval(
            sample_id=sample.sample_id,
            decision_time=sample.decision_time_utc,
            label_start=sample.label_t0_utc,
            label_end=sample.label_t1_utc,
        )
        for sample in fixture.samples
    )
    ordered = tuple(sorted(intervals, key=lambda item: (item.decision_time, item.sample_id)))
    sample_ids = tuple(item.sample_id for item in ordered)
    if len(sample_ids) != len(set(sample_ids)):
        raise GeometryInputError("duplicate_sample_id", "fixture sample identities must be unique")
    decision_times = tuple(item.decision_time for item in ordered)
    if len(decision_times) != len(set(decision_times)):
        raise GeometryInputError(
            "duplicate_decision_time",
            "deterministic fixture geometry requires one observation per decision timestamp",
        )
    return ordered


def _partition_confirmation(
    intervals: tuple[InformationInterval, ...],
    walk_forward: WalkForwardPolicy,
) -> tuple[
    tuple[InformationInterval, ...],
    tuple[InformationInterval, ...],
    tuple[InformationInterval, ...],
]:
    research = tuple(
        item for item in intervals if item.decision_time < walk_forward.final_confirmation_start_utc
    )
    confirmation = tuple(
        item
        for item in intervals
        if walk_forward.final_confirmation_start_utc
        <= item.decision_time
        <= walk_forward.final_confirmation_end_utc
    )
    post_confirmation = tuple(
        item for item in intervals if item.decision_time > walk_forward.final_confirmation_end_utc
    )
    return research, confirmation, post_confirmation


def _trim_rolling_train(
    split: ChronologicalSplit,
    walk_forward: WalkForwardPolicy,
) -> ChronologicalSplit:
    if walk_forward.train_mode is not TrainMode.ROLLING_PAST_ONLY:
        return split
    window = walk_forward.rolling_train_observations
    if window is None:  # guarded before construction; retained for fail-closed typing
        raise GeometryInputError(
            "missing_rolling_training_window",
            "rolling past-only geometry requires a frozen training window",
        )
    return ChronologicalSplit(
        fold_id=split.fold_id,
        mode="rolling_past_only",
        train_ids=split.train_ids[-window:],
        test_ids=split.test_ids,
        purged_ids=split.purged_ids,
        embargoed_ids=(),
        excluded_future_ids=split.excluded_future_ids,
        purge_rule=split.purge_rule,
        embargo_rule=None,
        embargo_end=None,
    )


def _split(
    intervals: tuple[InformationInterval, ...],
    test_interval: TestInterval,
    walk_forward: WalkForwardPolicy,
) -> tuple[ChronologicalSplit, int]:
    if walk_forward.train_mode is not TrainMode.PURGED_COMBINATORIAL:
        split = build_strict_past_only_split(intervals, test_interval)
        return _trim_rolling_train(split, walk_forward), 0

    later_training_exists = any(item.decision_time > test_interval.label_end for item in intervals)
    embargo_seconds = (walk_forward.embargo_seconds or 0) if later_training_exists else 0
    split = build_purged_split_with_embargo(
        intervals,
        test_interval,
        embargo_duration=timedelta(seconds=embargo_seconds),
    )
    return split, embargo_seconds


def _make_fold_record(
    *,
    ordinal: int,
    fold_kind: FoldKind,
    parent_fold_id: UUID | None,
    test_interval: TestInterval,
    split: ChronologicalSplit,
    samples_by_id: dict[str, InformationInterval],
    minimum_train_observations: int,
    expected_test_observations: int,
    embargo_duration_seconds: int,
) -> FoldRecord:
    if len(split.train_ids) < minimum_train_observations:
        raise GeometryInputError(
            "insufficient_permitted_training_observations",
            f"fold {test_interval.fold_id} has {len(split.train_ids)} permitted training rows; "
            f"policy requires {minimum_train_observations}",
        )
    if len(split.test_ids) != expected_test_observations:
        raise GeometryInputError(
            "test_window_observation_count_mismatch",
            f"fold {test_interval.fold_id} resolved {len(split.test_ids)} test rows; "
            f"policy requires {expected_test_observations}",
        )
    train_times = tuple(samples_by_id[sample_id].decision_time for sample_id in split.train_ids)
    payload = {
        "ordinal": ordinal,
        "fold_kind": fold_kind,
        "parent_fold_id": parent_fold_id,
        "train_start_utc": min(train_times),
        "train_end_utc": max(train_times),
        "test_start_utc": test_interval.start,
        "test_end_utc": test_interval.end,
        "train_sample_ids": split.train_ids,
        "purged_sample_ids": split.purged_ids,
        "test_sample_ids": split.test_ids,
        "embargoed_sample_ids": split.embargoed_ids,
        "embargo_duration_seconds": embargo_duration_seconds,
        "embargo_applied": embargo_duration_seconds > 0,
    }
    digest = domain_sha256(PHASE5_FOLD_HASH_DOMAIN, payload)
    return FoldRecord.model_validate(
        {
            "fold_id": identity(PHASE5_FOLD_NAMESPACE, digest),
            "fold_sha256": digest,
            **payload,
        }
    )


def _test_windows(
    intervals: tuple[InformationInterval, ...],
    *,
    count: int,
    observations_per_window: int,
    prefix: str,
) -> tuple[TestInterval, ...]:
    required = count * observations_per_window
    if len(intervals) < required:
        raise GeometryInputError(
            "insufficient_observations_for_test_windows",
            f"{prefix} geometry requires {required} test observations; only "
            f"{len(intervals)} are available",
        )
    test_rows = intervals[-required:]
    windows: list[TestInterval] = []
    for index in range(count):
        start_index = index * observations_per_window
        rows = test_rows[start_index : start_index + observations_per_window]
        windows.append(
            TestInterval(
                fold_id=f"{prefix}-{index + 1:03d}",
                start=rows[0].decision_time,
                end=rows[-1].decision_time,
                label_intervals=tuple(
                    ClosedLabelInterval(start=row.label_start, end=row.label_end) for row in rows
                ),
            )
        )
    return tuple(windows)


def _build_fold_records(
    research: tuple[InformationInterval, ...],
    walk_forward: WalkForwardPolicy,
) -> tuple[FoldRecord, ...]:
    minimum_required = (
        walk_forward.minimum_train_observations
        + walk_forward.outer_fold_count * walk_forward.outer_test_observations
    )
    if len(research) < minimum_required:
        raise GeometryInputError(
            "insufficient_research_observations",
            f"policy requires at least {minimum_required} pre-confirmation observations; "
            f"only {len(research)} are available",
        )

    outer_windows = _test_windows(
        research,
        count=walk_forward.outer_fold_count,
        observations_per_window=walk_forward.outer_test_observations,
        prefix="outer",
    )
    samples_by_id = {item.sample_id: item for item in research}
    records: list[FoldRecord] = []
    ordinal = 0
    for outer_window in outer_windows:
        outer_split, outer_embargo_seconds = _split(research, outer_window, walk_forward)
        outer_kind = (
            FoldKind.CPCV
            if walk_forward.train_mode is TrainMode.PURGED_COMBINATORIAL
            else FoldKind.OUTER
        )
        outer_record = _make_fold_record(
            ordinal=ordinal,
            fold_kind=outer_kind,
            parent_fold_id=None,
            test_interval=outer_window,
            split=outer_split,
            samples_by_id=samples_by_id,
            minimum_train_observations=walk_forward.minimum_train_observations,
            expected_test_observations=walk_forward.outer_test_observations,
            embargo_duration_seconds=outer_embargo_seconds,
        )
        records.append(outer_record)
        ordinal += 1

        outer_train = tuple(samples_by_id[sample_id] for sample_id in outer_record.train_sample_ids)
        inner_windows = _test_windows(
            outer_train,
            count=walk_forward.inner_fold_count,
            observations_per_window=walk_forward.inner_test_observations,
            prefix=f"{outer_window.fold_id}-inner",
        )
        for inner_window in inner_windows:
            inner_split, inner_embargo_seconds = _split(
                outer_train,
                inner_window,
                walk_forward,
            )
            records.append(
                _make_fold_record(
                    ordinal=ordinal,
                    fold_kind=FoldKind.INNER,
                    parent_fold_id=outer_record.fold_id,
                    test_interval=inner_window,
                    split=inner_split,
                    samples_by_id=samples_by_id,
                    minimum_train_observations=walk_forward.minimum_train_observations,
                    expected_test_observations=walk_forward.inner_test_observations,
                    embargo_duration_seconds=inner_embargo_seconds,
                )
            )
            ordinal += 1
    return tuple(records)


def _validate_records(
    folds: tuple[FoldRecord, ...],
    walk_forward: WalkForwardPolicy,
    samples_by_id: dict[str, InformationInterval],
) -> None:
    outer = tuple(fold for fold in folds if fold.fold_kind in {FoldKind.OUTER, FoldKind.CPCV})
    inner = tuple(fold for fold in folds if fold.fold_kind is FoldKind.INNER)
    if len(outer) != walk_forward.outer_fold_count:
        raise GeometryInputError(
            "outer_fold_count_mismatch",
            "constructed outer fold count does not match the frozen policy",
        )
    if len(inner) != walk_forward.outer_fold_count * walk_forward.inner_fold_count:
        raise GeometryInputError(
            "inner_fold_count_mismatch",
            "constructed inner fold count does not match the frozen policy",
        )
    for fold in folds:
        if len(fold.train_sample_ids) < walk_forward.minimum_train_observations:
            raise GeometryInputError(
                "minimum_train_observations_not_met",
                f"fold {fold.fold_id} violates the frozen minimum training size",
            )
        if walk_forward.train_mode is not TrainMode.PURGED_COMBINATORIAL:
            if fold.embargo_applied or fold.embargoed_sample_ids:
                raise GeometryInputError(
                    "past_only_embargo_applied",
                    "a standard past-only fold recorded embargo evidence",
                )
            if any(
                samples_by_id[sample_id].decision_time >= fold.test_start_utc
                for sample_id in fold.train_sample_ids
            ):
                raise GeometryInputError(
                    "past_only_training_not_strictly_before_test",
                    "a past-only fold contains a row at or after its test boundary",
                )
        elif fold.embargo_applied and not any(
            samples_by_id[sample_id].decision_time > fold.test_end_utc
            for sample_id in (*fold.train_sample_ids, *fold.embargoed_sample_ids)
        ):
            raise GeometryInputError(
                "embargo_without_later_training_geometry",
                "CPCV embargo was recorded where no later training geometry exists",
            )


def build_evaluation_geometry(
    *,
    policy: FrozenEvaluationPolicy | None,
    walk_forward: WalkForwardPolicy | None,
    fixture: SyntheticEvaluationFixture | None,
) -> EvaluationGeometry:
    """Build policy-driven nested geometry, returning a fail-closed validation result.

    ``walk_forward`` is supplied separately and must be byte-equivalent to the geometry frozen
    inside ``policy``.  This explicit comparison prevents callers from silently substituting
    folds after the policy hash has been fixed.
    """

    if policy is None:
        return _fail_closed(
            outcome=GateOutcome.BLOCKED_MISSING_POLICY,
            reason_code="missing_frozen_evaluation_policy",
            message="a frozen evaluation policy is required before geometry can be built",
            walk_forward=walk_forward,
        )
    if walk_forward is None:
        return _fail_closed(
            outcome=GateOutcome.BLOCKED_MISSING_POLICY,
            reason_code="missing_walk_forward_policy",
            message="explicit frozen walk-forward geometry is required",
            walk_forward=None,
        )
    if fixture is None:
        return _fail_closed(
            outcome=GateOutcome.BLOCKED_UNCOMPUTABLE,
            reason_code="missing_synthetic_evaluation_fixture",
            message="information intervals cannot be computed without a fixture",
            walk_forward=walk_forward,
        )
    if walk_forward != policy.walk_forward:
        return _fail_closed(
            outcome=GateOutcome.BLOCKED_UNCOMPUTABLE,
            reason_code="walk_forward_policy_mismatch",
            message="supplied walk-forward geometry differs from the frozen policy",
            walk_forward=walk_forward,
        )

    research_ids: tuple[str, ...] = ()
    confirmation_ids: tuple[str, ...] = ()
    post_confirmation_ids: tuple[str, ...] = ()
    try:
        _validate_policy_geometry(walk_forward)
        intervals = _information_intervals(fixture)
        research, confirmation, post_confirmation = _partition_confirmation(
            intervals,
            walk_forward,
        )
        research_ids = tuple(item.sample_id for item in research)
        confirmation_ids = tuple(item.sample_id for item in confirmation)
        post_confirmation_ids = tuple(item.sample_id for item in post_confirmation)
        folds = _build_fold_records(research, walk_forward)
        samples_by_id = {item.sample_id: item for item in research}
        _validate_records(folds, walk_forward, samples_by_id)
    except GeometryInputError as exc:
        return _fail_closed(
            outcome=GateOutcome.BLOCKED_UNCOMPUTABLE,
            reason_code=exc.reason_code,
            message=str(exc),
            walk_forward=walk_forward,
            research_sample_ids=research_ids,
            confirmation_sample_ids=confirmation_ids,
            post_confirmation_sample_ids=post_confirmation_ids,
        )
    except (ChronologyInputError, ValidationError) as exc:
        return _fail_closed(
            outcome=GateOutcome.BLOCKED_UNCOMPUTABLE,
            reason_code="invalid_information_interval_geometry",
            message=str(exc),
            walk_forward=walk_forward,
            research_sample_ids=research_ids,
            confirmation_sample_ids=confirmation_ids,
            post_confirmation_sample_ids=post_confirmation_ids,
        )

    outer_count = sum(fold.fold_kind in {FoldKind.OUTER, FoldKind.CPCV} for fold in folds)
    inner_count = sum(fold.fold_kind is FoldKind.INNER for fold in folds)
    validation = GeometryValidationResult(
        outcome=GateOutcome.PASS,
        reason_codes=(),
        message="frozen nested geometry is chronological, purged, and confirmation-reserved",
        train_mode=walk_forward.train_mode,
        expected_outer_fold_count=walk_forward.outer_fold_count,
        expected_inner_folds_per_outer=walk_forward.inner_fold_count,
        observed_outer_fold_count=outer_count,
        observed_inner_fold_count=inner_count,
        minimum_train_observations=walk_forward.minimum_train_observations,
        research_sample_count=len(research_ids),
        confirmation_sample_count=len(confirmation_ids),
        post_confirmation_sample_count=len(post_confirmation_ids),
        purged_sample_count=sum(len(fold.purged_sample_ids) for fold in folds),
        embargoed_sample_count=sum(len(fold.embargoed_sample_ids) for fold in folds),
        configured_embargo_seconds=walk_forward.embargo_seconds or 0,
    )
    return EvaluationGeometry(
        folds=folds,
        research_sample_ids=research_ids,
        confirmation_sample_ids=confirmation_ids,
        post_confirmation_sample_ids=post_confirmation_ids,
        validation=validation,
    )


__all__ = [
    "GEOMETRY_VERSION",
    "EvaluationGeometry",
    "GeometryInputError",
    "GeometryValidationResult",
    "build_evaluation_geometry",
]
