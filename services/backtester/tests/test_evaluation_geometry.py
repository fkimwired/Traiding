from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fable5_backtester.contracts import (
    FoldKind,
    FrozenEvaluationPolicy,
    GateCode,
    GateOutcome,
    SyntheticEvaluationFixture,
    TrainMode,
    WalkForwardPolicy,
)
from fable5_backtester.evaluation_geometry import (
    EvaluationGeometry,
    build_evaluation_geometry,
)
from fable5_backtester.synthetic import REGISTERED_FIXTURE, REGISTERED_POLICY


def _with_geometry(walk_forward: WalkForwardPolicy) -> FrozenEvaluationPolicy:
    return REGISTERED_POLICY.model_copy(update={"walk_forward": walk_forward})


def _registered_geometry() -> EvaluationGeometry:
    return build_evaluation_geometry(
        policy=REGISTERED_POLICY,
        walk_forward=REGISTERED_POLICY.walk_forward,
        fixture=REGISTERED_FIXTURE,
    )


def test_registered_geometry_has_exact_outer_inner_and_purge_boundaries() -> None:
    geometry = _registered_geometry()

    assert geometry.validation.passed is True
    assert geometry.validation.gate_code is GateCode.CV_CHRONOLOGY
    assert geometry.validation.outcome is GateOutcome.PASS
    assert geometry.validation.reason_codes == ()
    assert geometry.validation.observed_outer_fold_count == 2
    assert geometry.validation.observed_inner_fold_count == 4
    assert geometry.validation.gate_thresholds() == {
        "expected_outer_fold_count": 2,
        "expected_inner_folds_per_outer": 2,
        "minimum_train_observations": 6,
        "past_only_requires_zero_embargo": True,
    }
    assert len(geometry.folds) == 6
    assert tuple(fold.ordinal for fold in geometry.folds) == tuple(range(6))
    assert all(len(fold.fold_sha256) == 64 for fold in geometry.folds)

    outer_one, inner_one, inner_two, outer_two, inner_three, inner_four = geometry.folds
    assert outer_one.fold_kind is FoldKind.OUTER
    assert outer_one.test_sample_ids == tuple(
        f"synthetic-sample-{index:02d}" for index in range(13, 17)
    )
    assert outer_one.train_sample_ids == tuple(
        f"synthetic-sample-{index:02d}" for index in range(1, 11)
    )
    assert outer_one.purged_sample_ids == (
        "synthetic-sample-11",
        "synthetic-sample-12",
    )
    assert outer_one.test_start_utc == datetime(2020, 2, 2, 16, tzinfo=UTC)
    assert outer_one.test_end_utc == datetime(2020, 2, 5, 16, tzinfo=UTC)

    assert inner_one.parent_fold_id == outer_one.fold_id
    assert inner_two.parent_fold_id == outer_one.fold_id
    assert inner_one.test_sample_ids == ("synthetic-sample-09",)
    assert inner_one.purged_sample_ids == (
        "synthetic-sample-07",
        "synthetic-sample-08",
    )
    assert inner_one.train_sample_ids == tuple(
        f"synthetic-sample-{index:02d}" for index in range(1, 7)
    )
    assert inner_two.test_sample_ids == ("synthetic-sample-10",)
    assert inner_two.purged_sample_ids == (
        "synthetic-sample-08",
        "synthetic-sample-09",
    )

    assert outer_two.fold_kind is FoldKind.OUTER
    assert outer_two.test_sample_ids == tuple(
        f"synthetic-sample-{index:02d}" for index in range(17, 21)
    )
    assert outer_two.purged_sample_ids == (
        "synthetic-sample-15",
        "synthetic-sample-16",
    )
    assert inner_three.parent_fold_id == outer_two.fold_id
    assert inner_four.parent_fold_id == outer_two.fold_id
    assert inner_three.test_sample_ids == ("synthetic-sample-13",)
    assert inner_four.test_sample_ids == ("synthetic-sample-14",)


def test_expanding_and_rolling_past_only_geometry_never_apply_embargo() -> None:
    expanding = _registered_geometry()
    assert all(not fold.embargo_applied for fold in expanding.folds)
    assert all(fold.embargoed_sample_ids == () for fold in expanding.folds)

    walk_forward = REGISTERED_POLICY.walk_forward.model_copy(
        update={
            "train_mode": TrainMode.ROLLING_PAST_ONLY,
            "rolling_train_observations": 10,
        }
    )
    rolling = build_evaluation_geometry(
        policy=_with_geometry(walk_forward),
        walk_forward=walk_forward,
        fixture=REGISTERED_FIXTURE,
    )

    assert rolling.validation.passed is True
    outer_folds = tuple(fold for fold in rolling.folds if fold.fold_kind is FoldKind.OUTER)
    assert tuple(len(fold.train_sample_ids) for fold in outer_folds) == (10, 10)
    samples = {sample.sample_id: sample for sample in REGISTERED_FIXTURE.samples}
    for fold in rolling.folds:
        assert all(
            samples[sample_id].decision_time_utc < fold.test_start_utc
            for sample_id in fold.train_sample_ids
        )
        assert fold.embargo_applied is False
        assert fold.embargo_duration_seconds == 0
        assert fold.embargoed_sample_ids == ()


def test_cpcv_applies_exact_embargo_only_where_later_training_rows_exist() -> None:
    walk_forward = REGISTERED_POLICY.walk_forward.model_copy(
        update={
            "train_mode": TrainMode.PURGED_COMBINATORIAL,
            "embargo_rule": "phase5-one-day-post-test-embargo-v1",
            "embargo_seconds": 86_400,
        }
    )
    geometry = build_evaluation_geometry(
        policy=_with_geometry(walk_forward),
        walk_forward=walk_forward,
        fixture=REGISTERED_FIXTURE,
    )

    assert geometry.validation.passed is True
    assert geometry.validation.configured_embargo_seconds == 86_400
    assert geometry.validation.purged_sample_count == 13
    assert geometry.validation.embargoed_sample_count == 1
    outer_one, inner_one, inner_two, outer_two, inner_three, inner_four = geometry.folds
    assert outer_one.fold_kind is FoldKind.CPCV
    assert outer_one.purged_sample_ids == (
        "synthetic-sample-11",
        "synthetic-sample-12",
        "synthetic-sample-17",
        "synthetic-sample-18",
    )
    assert outer_one.embargoed_sample_ids == ("synthetic-sample-19",)
    assert outer_one.embargo_duration_seconds == 86_400
    assert outer_one.embargo_applied is True
    assert inner_one.test_sample_ids == ("synthetic-sample-10",)
    assert inner_one.purged_sample_ids == (
        "synthetic-sample-08",
        "synthetic-sample-09",
    )
    assert inner_one.embargoed_sample_ids == ()
    assert inner_one.embargo_duration_seconds == 86_400
    assert inner_one.embargo_applied is True
    assert inner_two.test_sample_ids == ("synthetic-sample-20",)
    assert inner_two.embargoed_sample_ids == ()
    assert inner_two.embargo_applied is False
    assert outer_two.fold_kind is FoldKind.CPCV
    assert outer_two.embargoed_sample_ids == ()
    assert outer_two.embargo_duration_seconds == 0
    assert outer_two.embargo_applied is False
    assert inner_three.purged_sample_ids == (
        "synthetic-sample-11",
        "synthetic-sample-12",
        "synthetic-sample-14",
    )
    assert inner_three.embargoed_sample_ids == ()
    assert inner_three.embargo_applied is False
    assert inner_four.embargoed_sample_ids == ()
    assert inner_four.embargo_applied is False


@pytest.mark.parametrize(
    ("policy", "walk_forward", "fixture", "outcome", "reason_code"),
    (
        (
            None,
            REGISTERED_POLICY.walk_forward,
            REGISTERED_FIXTURE,
            GateOutcome.BLOCKED_MISSING_POLICY,
            "missing_frozen_evaluation_policy",
        ),
        (
            REGISTERED_POLICY,
            None,
            REGISTERED_FIXTURE,
            GateOutcome.BLOCKED_MISSING_POLICY,
            "missing_walk_forward_policy",
        ),
        (
            REGISTERED_POLICY,
            REGISTERED_POLICY.walk_forward,
            None,
            GateOutcome.BLOCKED_UNCOMPUTABLE,
            "missing_synthetic_evaluation_fixture",
        ),
    ),
)
def test_missing_geometry_inputs_fail_closed_without_partial_folds(
    policy: FrozenEvaluationPolicy | None,
    walk_forward: WalkForwardPolicy | None,
    fixture: SyntheticEvaluationFixture | None,
    outcome: GateOutcome,
    reason_code: str,
) -> None:
    geometry = build_evaluation_geometry(
        policy=policy,
        walk_forward=walk_forward,
        fixture=fixture,
    )

    assert geometry.folds == ()
    assert geometry.validation.passed is False
    assert geometry.validation.outcome is outcome
    assert geometry.validation.reason_codes == (reason_code,)


def test_substituted_or_internally_inconsistent_geometry_fails_closed() -> None:
    substituted = REGISTERED_POLICY.walk_forward.model_copy(update={"outer_test_observations": 3})
    mismatch = build_evaluation_geometry(
        policy=REGISTERED_POLICY,
        walk_forward=substituted,
        fixture=REGISTERED_FIXTURE,
    )
    assert mismatch.folds == ()
    assert mismatch.validation.reason_codes == ("walk_forward_policy_mismatch",)

    invalid_embargo = REGISTERED_POLICY.walk_forward.model_copy(
        update={
            "embargo_rule": "invalid-past-only-embargo-v1",
            "embargo_seconds": 86_400,
        }
    )
    inconsistent = build_evaluation_geometry(
        policy=_with_geometry(invalid_embargo),
        walk_forward=invalid_embargo,
        fixture=REGISTERED_FIXTURE,
    )
    assert inconsistent.folds == ()
    assert inconsistent.validation.outcome is GateOutcome.BLOCKED_UNCOMPUTABLE
    assert inconsistent.validation.reason_codes == ("past_only_embargo_forbidden",)


def test_inadequate_or_ambiguous_fixture_geometry_fails_closed() -> None:
    inadequate_fixture = REGISTERED_FIXTURE.model_copy(
        update={"samples": REGISTERED_FIXTURE.samples[:10]}
    )
    inadequate = build_evaluation_geometry(
        policy=REGISTERED_POLICY,
        walk_forward=REGISTERED_POLICY.walk_forward,
        fixture=inadequate_fixture,
    )
    assert inadequate.folds == ()
    assert inadequate.validation.reason_codes == ("insufficient_research_observations",)

    duplicate_time_sample = REGISTERED_FIXTURE.samples[1].model_copy(
        update={
            "decision_time_utc": REGISTERED_FIXTURE.samples[0].decision_time_utc,
        }
    )
    duplicate_time_fixture = REGISTERED_FIXTURE.model_copy(
        update={
            "samples": (
                REGISTERED_FIXTURE.samples[0],
                duplicate_time_sample,
                *REGISTERED_FIXTURE.samples[2:],
            )
        }
    )
    ambiguous = build_evaluation_geometry(
        policy=REGISTERED_POLICY,
        walk_forward=REGISTERED_POLICY.walk_forward,
        fixture=duplicate_time_fixture,
    )
    assert ambiguous.folds == ()
    assert ambiguous.validation.reason_codes == ("duplicate_decision_time",)


def test_confirmation_rows_are_reserved_and_never_enter_any_fold() -> None:
    confirmation_time = datetime(2020, 2, 11, 16, tzinfo=UTC)
    confirmation_sample = REGISTERED_FIXTURE.samples[-1].model_copy(
        update={
            "decision_time_utc": confirmation_time,
            "feature_available_at_utc": datetime(2020, 2, 11, 15, tzinfo=UTC),
            "label_t0_utc": confirmation_time,
            "label_t1_utc": datetime(2020, 2, 13, 16, tzinfo=UTC),
        }
    )
    fixture = REGISTERED_FIXTURE.model_copy(
        update={"samples": (*REGISTERED_FIXTURE.samples[:-1], confirmation_sample)}
    )
    walk_forward = REGISTERED_POLICY.walk_forward.model_copy(
        update={"minimum_train_observations": 5}
    )
    geometry = build_evaluation_geometry(
        policy=_with_geometry(walk_forward),
        walk_forward=walk_forward,
        fixture=fixture,
    )

    assert geometry.validation.passed is True
    assert geometry.confirmation_sample_ids == ("synthetic-sample-20",)
    assert geometry.validation.confirmation_sample_count == 1
    used_ids = {
        sample_id
        for fold in geometry.folds
        for sample_id in (
            *fold.train_sample_ids,
            *fold.purged_sample_ids,
            *fold.test_sample_ids,
            *fold.embargoed_sample_ids,
        )
    }
    assert "synthetic-sample-20" not in used_ids
    assert all(
        fold.test_end_utc < walk_forward.final_confirmation_start_utc for fold in geometry.folds
    )
