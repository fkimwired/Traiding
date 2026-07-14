from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fable5_backtester.chronology import (
    EMBARGO_BOUNDARY_RULE,
    ChronologyInputError,
    ClosedLabelInterval,
    InformationInterval,
    build_purged_split_with_embargo,
    build_strict_past_only_split,
    purge_overlapping_labels,
)
from fable5_backtester.chronology import (
    TestInterval as EvaluationTestInterval,
)


def _at(day: int, hour: int = 16) -> datetime:
    return datetime(2026, 1, day, hour, tzinfo=UTC)


def _sample(sample_id: str, decision_day: int, label_end_day: int) -> InformationInterval:
    return InformationInterval(
        sample_id=sample_id,
        decision_time=_at(decision_day),
        label_start=_at(decision_day),
        label_end=_at(label_end_day),
    )


def _test_interval(
    fold_id: str,
    decision_start_day: int,
    decision_end_day: int,
    *label_intervals: tuple[int, int],
) -> EvaluationTestInterval:
    return EvaluationTestInterval(
        fold_id,
        _at(decision_start_day),
        _at(decision_end_day),
        tuple(ClosedLabelInterval(_at(start), _at(end)) for start, end in label_intervals),
    )


def test_past_only_purge_uses_exact_label_interval_boundary() -> None:
    test_interval = _test_interval("outer-1", 5, 7, (5, 6), (7, 8))
    samples = (
        _sample("keep-before", 1, 4),
        _sample("purge-equality", 2, 5),
        _sample("purge-overlap", 4, 6),
        _sample("test-start", 5, 6),
        _sample("test-end", 7, 8),
        _sample("future", 8, 9),
    )

    split = build_strict_past_only_split(samples, test_interval)

    assert split.train_ids == ("keep-before",)
    assert split.purged_ids == ("purge-equality", "purge-overlap")
    assert split.test_ids == ("test-start", "test-end")
    assert split.excluded_future_ids == ("future",)
    assert split.embargoed_ids == ()
    assert split.embargo_rule is None


def test_closed_interval_purge_finds_only_actual_intersections() -> None:
    interval = _test_interval("cpcv-1", 10, 12, (10, 11), (14, 15))
    samples = (
        _sample("before", 1, 9),
        _sample("touch-start", 2, 10),
        _sample("inside", 10, 11),
        _sample("between-union-members", 12, 13),
        _sample("touch-last-end", 13, 15),
        _sample("after", 16, 17),
    )
    assert purge_overlapping_labels(samples, interval) == (
        "touch-start",
        "inside",
        "touch-last-end",
    )


def test_embargo_applies_only_to_later_training_rows_with_frozen_boundary() -> None:
    test_interval = _test_interval("cpcv-1", 10, 12, (10, 13), (12, 15))
    samples = (
        _sample("pre-train", 1, 9),
        _sample("pre-overlap", 9, 10),
        _sample("test-row", 10, 13),
        _sample("test-last", 12, 15),
        _sample("post-decision-overlap", 13, 15),
        _sample("embargo-one-day", 16, 17),
        _sample("embargo-endpoint", 17, 18),
        _sample("post-embargo", 18, 19),
    )

    split = build_purged_split_with_embargo(
        samples,
        test_interval,
        embargo_duration=timedelta(days=2),
    )

    assert split.train_ids == ("pre-train", "post-embargo")
    assert split.test_ids == ("test-row", "test-last")
    assert split.purged_ids == ("pre-overlap", "post-decision-overlap")
    assert split.embargoed_ids == ("embargo-one-day", "embargo-endpoint")
    assert split.excluded_future_ids == ()
    assert split.embargo_rule == EMBARGO_BOUNDARY_RULE
    assert split.embargo_end == _at(17)


def test_zero_embargo_leaves_nonoverlapping_later_rows_eligible() -> None:
    interval = _test_interval("cpcv-zero", 10, 12, (10, 14))
    split = build_purged_split_with_embargo(
        (
            _sample("before", 1, 9),
            _sample("test-row", 10, 14),
            _sample("touch-label-end", 13, 14),
            _sample("later", 15, 16),
        ),
        interval,
        embargo_duration=timedelta(0),
    )
    assert split.train_ids == ("before", "later")
    assert split.purged_ids == ("touch-label-end",)
    assert split.embargoed_ids == ()


def test_split_rejects_an_incomplete_test_label_union() -> None:
    samples = (
        _sample("test-first", 10, 12),
        _sample("test-last", 12, 15),
        _sample("later", 16, 17),
    )
    incomplete = _test_interval("cpcv-incomplete", 10, 12, (10, 12))

    with pytest.raises(ChronologyInputError, match="complete ordered test-label union"):
        build_purged_split_with_embargo(
            samples,
            incomplete,
            embargo_duration=timedelta(days=1),
        )


def test_chronology_rejects_naive_time_and_duplicate_ids() -> None:
    with pytest.raises(ChronologyInputError, match="timezone-aware"):
        InformationInterval(
            sample_id="naive",
            decision_time=datetime(2026, 1, 1),
            label_start=datetime(2026, 1, 1),
            label_end=datetime(2026, 1, 2),
        )

    duplicate = _sample("duplicate", 1, 2)
    with pytest.raises(ChronologyInputError, match="duplicate sample_id"):
        build_strict_past_only_split(
            (duplicate, duplicate),
            _test_interval("outer-duplicate", 5, 6, (5, 7)),
        )
