from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Final

TRAIN_IDS_HASH_VERSION: Final = "phase5-train-ids-v1"
STANDARDIZER_FIT_VERSION: Final = "phase5-train-only-standardizer-v1"


class PreprocessingInputError(ValueError):
    """A preprocessing fit or transform cannot be performed without leakage risk."""


def _identifier(name: str, value: str) -> None:
    if not isinstance(value, str) or not value or value != value.strip():
        raise PreprocessingInputError(f"{name} must be a nonblank trimmed string")


def _value(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PreprocessingInputError(f"{name} must be a finite number")
    normalized = float(value)
    if not math.isfinite(normalized):
        raise PreprocessingInputError(f"{name} must be a finite number")
    return normalized


def _domain_hash(domain: str, value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(domain.encode("ascii") + b"\x00" + encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class SampleValue:
    sample_id: str
    value: float

    def __post_init__(self) -> None:
        _identifier("sample_id", self.sample_id)
        _value("value", self.value)


@dataclass(frozen=True, slots=True)
class TrainOnlyFitRequest:
    fold_id: str
    train_values: tuple[SampleValue, ...]
    permitted_train_ids: tuple[str, ...]
    ddof: int


@dataclass(frozen=True, slots=True)
class TrainOnlyFitRecord:
    fit_id: str
    fit_version: str
    fold_id: str
    train_ids: tuple[str, ...]
    train_ids_sha256: str
    value_count: int
    mean: float
    standard_deviation: float
    ddof: int
    fit_sha256: str


@dataclass(frozen=True, slots=True)
class TransformedValue:
    sample_id: str
    fit_id: str
    value: float


def fit_train_only_standardizer(request: TrainOnlyFitRequest) -> TrainOnlyFitRecord:
    """Fit mean/std only when supplied ids exactly match the permitted fold train ids."""

    _identifier("fold_id", request.fold_id)
    if (
        isinstance(request.ddof, bool)
        or not isinstance(request.ddof, int)
        or request.ddof not in (0, 1)
    ):
        raise PreprocessingInputError("ddof must be exactly zero or one")
    if not request.train_values:
        raise PreprocessingInputError("train_values cannot be empty")

    permitted = request.permitted_train_ids
    if not permitted:
        raise PreprocessingInputError("permitted_train_ids cannot be empty")
    for sample_id in permitted:
        _identifier("permitted train id", sample_id)
    if len(set(permitted)) != len(permitted):
        raise PreprocessingInputError("permitted_train_ids must be unique")

    rows_by_id: dict[str, float] = {}
    for row in request.train_values:
        if row.sample_id in rows_by_id:
            raise PreprocessingInputError(f"duplicate train sample_id: {row.sample_id}")
        rows_by_id[row.sample_id] = _value("train value", row.value)

    supplied_ids = frozenset(rows_by_id)
    permitted_ids = frozenset(permitted)
    if supplied_ids != permitted_ids:
        unexpected = tuple(sorted(supplied_ids - permitted_ids))
        missing = tuple(sorted(permitted_ids - supplied_ids))
        raise PreprocessingInputError(
            f"train ids must exactly match permitted fold ids; unexpected={unexpected}, "
            f"missing={missing}"
        )

    train_ids = tuple(sorted(permitted_ids))
    if len(train_ids) <= request.ddof:
        raise PreprocessingInputError("insufficient train values for requested ddof")
    values = tuple(rows_by_id[sample_id] for sample_id in train_ids)
    mean = math.fsum(values) / len(values)
    variance = math.fsum((value - mean) ** 2 for value in values) / (len(values) - request.ddof)
    standard_deviation = math.sqrt(variance)
    if standard_deviation <= 0.0 or not math.isfinite(standard_deviation):
        raise PreprocessingInputError("training standard deviation must be positive and finite")

    train_ids_sha256 = _domain_hash(TRAIN_IDS_HASH_VERSION, list(train_ids))
    fit_payload = {
        "ddof": request.ddof,
        "fit_version": STANDARDIZER_FIT_VERSION,
        "fold_id": request.fold_id,
        "mean": mean.hex(),
        "standard_deviation": standard_deviation.hex(),
        "train_ids": list(train_ids),
        "train_ids_sha256": train_ids_sha256,
        "values": [value.hex() for value in values],
    }
    fit_sha256 = _domain_hash(STANDARDIZER_FIT_VERSION, fit_payload)
    return TrainOnlyFitRecord(
        fit_id=f"fit-{fit_sha256}",
        fit_version=STANDARDIZER_FIT_VERSION,
        fold_id=request.fold_id,
        train_ids=train_ids,
        train_ids_sha256=train_ids_sha256,
        value_count=len(values),
        mean=mean,
        standard_deviation=standard_deviation,
        ddof=request.ddof,
        fit_sha256=fit_sha256,
    )


def transform_with_fit(
    fit: TrainOnlyFitRecord, values: tuple[SampleValue, ...]
) -> tuple[TransformedValue, ...]:
    """Apply a frozen train-only fit without modifying its recorded statistics."""

    if fit.standard_deviation <= 0.0 or not math.isfinite(fit.standard_deviation):
        raise PreprocessingInputError("fit standard deviation must be positive and finite")
    seen: set[str] = set()
    transformed: list[TransformedValue] = []
    for row in values:
        if row.sample_id in seen:
            raise PreprocessingInputError(f"duplicate transform sample_id: {row.sample_id}")
        seen.add(row.sample_id)
        normalized = (_value("transform value", row.value) - fit.mean) / fit.standard_deviation
        transformed.append(
            TransformedValue(sample_id=row.sample_id, fit_id=fit.fit_id, value=normalized)
        )
    return tuple(transformed)
