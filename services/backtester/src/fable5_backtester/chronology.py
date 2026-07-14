from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Final

PAST_ONLY_PURGE_RULE: Final = "phase5-past-only-label-end-before-test-start-v1"
INTERVAL_PURGE_RULE: Final = "phase5-closed-information-interval-intersection-v1"
EMBARGO_BOUNDARY_RULE: Final = "phase5-open-test-end-closed-embargo-end-v1"


class ChronologyInputError(ValueError):
    """A chronological split cannot be built safely from the supplied geometry."""


def _require_aware(name: str, value: datetime) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ChronologyInputError(f"{name} must be timezone-aware")


def _require_identifier(name: str, value: str) -> None:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ChronologyInputError(f"{name} must be a nonblank trimmed string")


@dataclass(frozen=True, slots=True)
class InformationInterval:
    sample_id: str
    decision_time: datetime
    label_start: datetime
    label_end: datetime

    def __post_init__(self) -> None:
        _require_identifier("sample_id", self.sample_id)
        _require_aware("decision_time", self.decision_time)
        _require_aware("label_start", self.label_start)
        _require_aware("label_end", self.label_end)
        if self.label_start < self.decision_time:
            raise ChronologyInputError("label_start cannot precede decision_time")
        if self.label_end < self.label_start:
            raise ChronologyInputError("label_end cannot precede label_start")


@dataclass(frozen=True, slots=True)
class ClosedLabelInterval:
    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        _require_aware("test label start", self.start)
        _require_aware("test label end", self.end)
        if self.end < self.start:
            raise ChronologyInputError("test label end cannot precede test label start")


@dataclass(frozen=True, slots=True)
class TestInterval:
    fold_id: str
    start: datetime
    end: datetime
    label_intervals: tuple[ClosedLabelInterval, ...]

    def __post_init__(self) -> None:
        _require_identifier("fold_id", self.fold_id)
        _require_aware("test start", self.start)
        _require_aware("test end", self.end)
        if self.end < self.start:
            raise ChronologyInputError("test end cannot precede test start")
        if not self.label_intervals:
            raise ChronologyInputError("test label intervals cannot be empty")

    @property
    def label_end(self) -> datetime:
        """Return the final endpoint of the complete closed test-label union."""

        return max(interval.end for interval in self.label_intervals)


@dataclass(frozen=True, slots=True)
class ChronologicalSplit:
    fold_id: str
    mode: str
    train_ids: tuple[str, ...]
    test_ids: tuple[str, ...]
    purged_ids: tuple[str, ...]
    embargoed_ids: tuple[str, ...]
    excluded_future_ids: tuple[str, ...]
    purge_rule: str
    embargo_rule: str | None
    embargo_end: datetime | None


def _ordered_unique(
    samples: tuple[InformationInterval, ...],
) -> tuple[InformationInterval, ...]:
    seen: set[str] = set()
    for sample in samples:
        if sample.sample_id in seen:
            raise ChronologyInputError(f"duplicate sample_id: {sample.sample_id}")
        seen.add(sample.sample_id)
    return tuple(sorted(samples, key=lambda item: (item.decision_time, item.sample_id)))


def _require_complete_test_label_union(
    ordered: tuple[InformationInterval, ...], test_interval: TestInterval
) -> None:
    expected = tuple(
        ClosedLabelInterval(start=sample.label_start, end=sample.label_end)
        for sample in ordered
        if test_interval.start <= sample.decision_time <= test_interval.end
    )
    if not expected:
        raise ChronologyInputError("test decision interval does not contain any samples")
    if test_interval.label_intervals != expected:
        raise ChronologyInputError(
            "test label intervals must exactly equal the complete ordered test-label union"
        )


def information_intervals_overlap(sample: InformationInterval, test_interval: TestInterval) -> bool:
    """Return whether a sample intersects any closed test-label interval."""

    return any(
        sample.label_start <= interval.end and sample.label_end >= interval.start
        for interval in test_interval.label_intervals
    )


def purge_overlapping_labels(
    samples: tuple[InformationInterval, ...], test_interval: TestInterval
) -> tuple[str, ...]:
    ordered = _ordered_unique(samples)
    return tuple(
        sample.sample_id
        for sample in ordered
        if information_intervals_overlap(sample, test_interval)
    )


def build_strict_past_only_split(
    samples: tuple[InformationInterval, ...], test_interval: TestInterval
) -> ChronologicalSplit:
    """Build a past-only split; no row at/after test start can enter training."""

    ordered = _ordered_unique(samples)
    _require_complete_test_label_union(ordered, test_interval)
    train: list[str] = []
    test: list[str] = []
    purged: list[str] = []
    future: list[str] = []
    for sample in ordered:
        if sample.decision_time < test_interval.start:
            # For a past-only fold, every label must be completely known before test starts.
            if sample.label_end >= test_interval.start:
                purged.append(sample.sample_id)
            else:
                train.append(sample.sample_id)
        elif sample.decision_time <= test_interval.end:
            test.append(sample.sample_id)
        else:
            future.append(sample.sample_id)
    return ChronologicalSplit(
        fold_id=test_interval.fold_id,
        mode="strict_past_only",
        train_ids=tuple(train),
        test_ids=tuple(test),
        purged_ids=tuple(purged),
        embargoed_ids=(),
        excluded_future_ids=tuple(future),
        purge_rule=PAST_ONLY_PURGE_RULE,
        embargo_rule=None,
        embargo_end=None,
    )


def build_purged_split_with_embargo(
    samples: tuple[InformationInterval, ...],
    test_interval: TestInterval,
    *,
    embargo_duration: timedelta,
) -> ChronologicalSplit:
    """Build a purged split where later rows may train after an explicit embargo."""

    if not isinstance(embargo_duration, timedelta):
        raise ChronologyInputError("embargo_duration must be a timedelta")
    if embargo_duration < timedelta(0):
        raise ChronologyInputError("embargo_duration cannot be negative")
    ordered = _ordered_unique(samples)
    _require_complete_test_label_union(ordered, test_interval)
    embargo_end = test_interval.label_end + embargo_duration
    train: list[str] = []
    test: list[str] = []
    purged: list[str] = []
    embargoed: list[str] = []
    for sample in ordered:
        if test_interval.start <= sample.decision_time <= test_interval.end:
            test.append(sample.sample_id)
        elif information_intervals_overlap(sample, test_interval):
            purged.append(sample.sample_id)
        elif (
            embargo_duration > timedelta(0)
            and test_interval.label_end < sample.decision_time <= embargo_end
        ):
            embargoed.append(sample.sample_id)
        else:
            train.append(sample.sample_id)
    return ChronologicalSplit(
        fold_id=test_interval.fold_id,
        mode="purged_with_later_training",
        train_ids=tuple(train),
        test_ids=tuple(test),
        purged_ids=tuple(purged),
        embargoed_ids=tuple(embargoed),
        excluded_future_ids=(),
        purge_rule=INTERVAL_PURGE_RULE,
        embargo_rule=EMBARGO_BOUNDARY_RULE,
        embargo_end=embargo_end,
    )
