from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from enum import StrEnum
from itertools import combinations
from statistics import NormalDist
from typing import Final

DSR_NUMERIC_TOLERANCE: Final = 1e-12
DSR_FORMULA_VERSION: Final = "bailey-lopez-de-prado-dsr-2014-eq2-v1"
PBO_FORMULA_VERSION: Final = "bailey-et-al-cscv-2014-algorithm-2.3-v1"
PBO_MATRIX_HASH_VERSION: Final = "phase5-pbo-matrix-v1"
LAG1_EFFECTIVE_SAMPLE_METHOD: Final = "lag1-effective-sample-size-sensitivity-v1"
EULER_MASCHERONI: Final = 0.5772156649015329


class StatisticInputError(ValueError):
    """Base class for evaluation-statistic inputs that must fail closed."""


class MissingStatisticPolicyError(StatisticInputError):
    """A required frozen policy field was not supplied."""


class UncomputableStatisticError(StatisticInputError):
    """The requested statistic cannot be computed reliably from its inputs."""


@dataclass(frozen=True, slots=True)
class SerialCorrelationSensitivity:
    method: str
    lag1_autocorrelation: float
    nominal_sample_length: int
    raw_effective_sample_length: float
    effective_sample_length: int


def lag1_effective_sample_sensitivity(
    values: tuple[float, ...],
    method: str | None,
) -> SerialCorrelationSensitivity:
    """Return the frozen lag-1 effective-sample sensitivity for a return series."""

    if method is None:
        raise MissingStatisticPolicyError("serial_correlation_method must be frozen")
    if method != LAG1_EFFECTIVE_SAMPLE_METHOD:
        raise MissingStatisticPolicyError("unsupported serial_correlation_method")
    if len(values) < 3 or any(not math.isfinite(value) for value in values):
        raise UncomputableStatisticError(
            "serial-correlation sensitivity requires at least three finite returns"
        )
    left = values[:-1]
    right = values[1:]
    left_mean = math.fsum(left) / len(left)
    right_mean = math.fsum(right) / len(right)
    numerator = math.fsum(
        (left_value - left_mean) * (right_value - right_mean)
        for left_value, right_value in zip(left, right, strict=True)
    )
    left_sum = math.fsum((value - left_mean) ** 2 for value in left)
    right_sum = math.fsum((value - right_mean) ** 2 for value in right)
    denominator = math.sqrt(left_sum * right_sum)
    if denominator <= 0 or not math.isfinite(denominator):
        raise UncomputableStatisticError("lag-1 autocorrelation is uncomputable")
    autocorrelation = numerator / denominator
    if not -1 < autocorrelation < 1:
        raise UncomputableStatisticError("lag-1 autocorrelation is singular")
    nominal = len(values)
    raw_effective = nominal * (1.0 - autocorrelation) / (1.0 + autocorrelation)
    if not math.isfinite(raw_effective) or raw_effective < 2:
        raise UncomputableStatisticError("serial correlation leaves inadequate effective samples")
    effective = min(nominal, math.floor(raw_effective))
    return SerialCorrelationSensitivity(
        method=method,
        lag1_autocorrelation=autocorrelation,
        nominal_sample_length=nominal,
        raw_effective_sample_length=raw_effective,
        effective_sample_length=effective,
    )


def _finite_number(name: str, value: float | None) -> float:
    if value is None:
        raise UncomputableStatisticError(f"{name} is required")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise UncomputableStatisticError(f"{name} must be a finite number")
    normalized = float(value)
    if not math.isfinite(normalized):
        raise UncomputableStatisticError(f"{name} must be a finite number")
    return normalized


def _probability_policy(name: str, value: float | None) -> float:
    if value is None:
        raise MissingStatisticPolicyError(f"{name} must be frozen before calculation")
    try:
        normalized = _finite_number(name, value)
    except UncomputableStatisticError as exc:
        raise MissingStatisticPolicyError(f"{name} must be a finite probability") from exc
    if not 0.0 <= normalized <= 1.0:
        raise MissingStatisticPolicyError(f"{name} must be between zero and one")
    return normalized


@dataclass(frozen=True, slots=True)
class DeflatedSharpeInputs:
    estimated_sharpe: float | None
    sample_length: int | None
    skew: float | None
    ordinary_kurtosis: float | None
    sharpe_variance: float | None
    effective_trials: float | None
    minimum_probability: float | None

    @classmethod
    def from_annualized(
        cls,
        *,
        annualized_sharpe: float | None,
        annualized_sharpe_variance: float | None,
        periods_per_year: int | None,
        sample_length: int | None,
        skew: float | None,
        ordinary_kurtosis: float | None,
        effective_trials: float | None,
        minimum_probability: float | None,
    ) -> DeflatedSharpeInputs:
        """Explicitly convert annualized Sharpe inputs to the per-period formula domain."""

        sharpe = _finite_number("annualized_sharpe", annualized_sharpe)
        variance = _finite_number("annualized_sharpe_variance", annualized_sharpe_variance)
        if periods_per_year is None:
            raise UncomputableStatisticError("periods_per_year is required")
        if isinstance(periods_per_year, bool) or not isinstance(periods_per_year, int):
            raise UncomputableStatisticError("periods_per_year must be a positive integer")
        if periods_per_year <= 0:
            raise UncomputableStatisticError("periods_per_year must be a positive integer")
        return cls(
            estimated_sharpe=sharpe / math.sqrt(periods_per_year),
            sample_length=sample_length,
            skew=skew,
            ordinary_kurtosis=ordinary_kurtosis,
            sharpe_variance=variance / periods_per_year,
            effective_trials=effective_trials,
            minimum_probability=minimum_probability,
        )


@dataclass(frozen=True, slots=True)
class DeflatedSharpeResult:
    formula_version: str
    estimated_sharpe: float
    expected_maximum_sharpe: float
    z_score: float
    probability: float
    minimum_probability: float
    passes: bool
    sample_length: int
    skew: float
    ordinary_kurtosis: float
    sharpe_variance: float
    effective_trials: float


def compute_deflated_sharpe(inputs: DeflatedSharpeInputs) -> DeflatedSharpeResult:
    """Compute DSR in one per-period frequency domain, failing closed on invalid inputs."""

    estimated_sharpe = _finite_number("estimated_sharpe", inputs.estimated_sharpe)
    skew = _finite_number("skew", inputs.skew)
    kurtosis = _finite_number("ordinary_kurtosis", inputs.ordinary_kurtosis)
    variance = _finite_number("sharpe_variance", inputs.sharpe_variance)
    effective_trials = _finite_number("effective_trials", inputs.effective_trials)
    minimum_probability = _probability_policy("minimum_probability", inputs.minimum_probability)

    sample_length = inputs.sample_length
    if sample_length is None:
        raise UncomputableStatisticError("sample_length is required")
    if isinstance(sample_length, bool) or not isinstance(sample_length, int):
        raise UncomputableStatisticError("sample_length must be an integer")
    if sample_length < 2:
        raise UncomputableStatisticError("sample_length must be at least two")
    if variance <= 0.0:
        raise UncomputableStatisticError("sharpe_variance must be positive")
    if effective_trials <= 1.0:
        raise UncomputableStatisticError("effective_trials must be greater than one")
    if kurtosis < 1.0:
        raise UncomputableStatisticError("ordinary_kurtosis cannot be below one")

    first_quantile_probability = 1.0 - (1.0 / effective_trials)
    second_quantile_probability = 1.0 - (1.0 / (effective_trials * math.e))
    if not (0.0 < first_quantile_probability < 1.0 and 0.0 < second_quantile_probability < 1.0):
        raise UncomputableStatisticError("effective_trials is outside numeric precision")

    normal = NormalDist()
    expected_maximum = math.sqrt(variance) * (
        (1.0 - EULER_MASCHERONI) * normal.inv_cdf(first_quantile_probability)
        + EULER_MASCHERONI * normal.inv_cdf(second_quantile_probability)
    )
    denominator_squared = (
        1.0 - skew * estimated_sharpe + ((kurtosis - 1.0) / 4.0) * estimated_sharpe**2
    )
    if not math.isfinite(denominator_squared) or denominator_squared <= 0.0:
        raise UncomputableStatisticError("DSR denominator is not positive and finite")

    z_score = ((estimated_sharpe - expected_maximum) * math.sqrt(sample_length - 1)) / math.sqrt(
        denominator_squared
    )
    probability = normal.cdf(z_score)
    if not math.isfinite(probability):
        raise UncomputableStatisticError("DSR probability is not finite")

    return DeflatedSharpeResult(
        formula_version=DSR_FORMULA_VERSION,
        estimated_sharpe=estimated_sharpe,
        expected_maximum_sharpe=expected_maximum,
        z_score=z_score,
        probability=probability,
        minimum_probability=minimum_probability,
        passes=probability >= minimum_probability,
        sample_length=sample_length,
        skew=skew,
        ordinary_kurtosis=kurtosis,
        sharpe_variance=variance,
        effective_trials=effective_trials,
    )


class PBOSelectionMetric(StrEnum):
    MEAN_RETURN = "mean_return"


class PBOTiePolicy(StrEnum):
    FAIL = "fail"
    LOWEST_INDEX = "lowest_index"


@dataclass(frozen=True, slots=True)
class PBOInputs:
    matrix: tuple[tuple[float | None, ...], ...]
    configuration_ids: tuple[str, ...]
    block_count: int | None
    selection_metric: PBOSelectionMetric | None
    tie_policy: PBOTiePolicy | None
    maximum_probability: float | None


@dataclass(frozen=True, slots=True)
class PBOBlock:
    block_index: int
    row_start: int
    row_stop: int


@dataclass(frozen=True, slots=True)
class PBOSplitResult:
    train_blocks: tuple[int, ...]
    test_blocks: tuple[int, ...]
    train_row_indices: tuple[int, ...]
    test_row_indices: tuple[int, ...]
    in_sample_scores: tuple[float, ...]
    out_of_sample_scores: tuple[float, ...]
    selected_configuration_index: int
    selected_configuration_id: str
    out_of_sample_ranks: tuple[int, ...]
    selected_out_of_sample_rank: int
    normalized_rank: float
    logit: float


@dataclass(frozen=True, slots=True)
class PBOResult:
    formula_version: str
    matrix_hash_version: str
    matrix_sha256: str
    configuration_ids: tuple[str, ...]
    blocks: tuple[PBOBlock, ...]
    splits: tuple[PBOSplitResult, ...]
    probability: float
    maximum_probability: float
    passes: bool
    selection_metric: PBOSelectionMetric
    tie_policy: PBOTiePolicy


def _normalize_matrix(inputs: PBOInputs) -> tuple[tuple[float, ...], ...]:
    if not inputs.matrix:
        raise UncomputableStatisticError("PBO matrix is required")
    width = len(inputs.matrix[0])
    if width < 2:
        raise UncomputableStatisticError("PBO requires at least two configurations")
    normalized_rows: list[tuple[float, ...]] = []
    for row_index, row in enumerate(inputs.matrix):
        if len(row) != width:
            raise UncomputableStatisticError("PBO matrix must be rectangular")
        normalized_row: list[float] = []
        for column_index, value in enumerate(row):
            try:
                normalized = _finite_number(f"matrix[{row_index}][{column_index}]", value)
            except UncomputableStatisticError as exc:
                raise UncomputableStatisticError(
                    "PBO matrix cannot contain missing or non-finite returns"
                ) from exc
            normalized_row.append(normalized)
        normalized_rows.append(tuple(normalized_row))
    return tuple(normalized_rows)


def _matrix_sha256(
    matrix: tuple[tuple[float, ...], ...], configuration_ids: tuple[str, ...]
) -> str:
    payload = {
        "configuration_ids": list(configuration_ids),
        "matrix": [[value.hex() for value in row] for row in matrix],
        "version": PBO_MATRIX_HASH_VERSION,
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(PBO_MATRIX_HASH_VERSION.encode("ascii") + b"\x00" + encoded).hexdigest()


def _mean_scores(
    matrix: tuple[tuple[float, ...], ...], row_indices: tuple[int, ...]
) -> tuple[float, ...]:
    width = len(matrix[0])
    return tuple(
        math.fsum(matrix[row_index][column_index] for row_index in row_indices) / len(row_indices)
        for column_index in range(width)
    )


def _select_best(scores: tuple[float, ...], tie_policy: PBOTiePolicy) -> int:
    maximum = max(scores)
    winners = tuple(index for index, score in enumerate(scores) if score == maximum)
    if len(winners) > 1 and tie_policy is PBOTiePolicy.FAIL:
        raise UncomputableStatisticError("PBO in-sample selection contains a tie")
    return min(winners)


def _rank_worst_to_best(scores: tuple[float, ...], tie_policy: PBOTiePolicy) -> tuple[int, ...]:
    if tie_policy is PBOTiePolicy.FAIL and len(set(scores)) != len(scores):
        raise UncomputableStatisticError("PBO out-of-sample ranking contains a tie")
    # Under LOWEST_INDEX, the lower index wins a score tie and therefore receives the higher rank.
    ordered = sorted(range(len(scores)), key=lambda index: (scores[index], -index))
    ranks = [0] * len(scores)
    for rank, configuration_index in enumerate(ordered, start=1):
        ranks[configuration_index] = rank
    return tuple(ranks)


def compute_pbo(inputs: PBOInputs) -> PBOResult:
    """Compute CSCV PBO over equal contiguous blocks and every symmetric split."""

    matrix = _normalize_matrix(inputs)
    width = len(matrix[0])
    if len(inputs.configuration_ids) != width:
        raise UncomputableStatisticError("configuration_ids must match the PBO matrix column count")
    if any(
        not isinstance(value, str) or not value or value != value.strip()
        for value in inputs.configuration_ids
    ):
        raise UncomputableStatisticError("configuration_ids must be nonblank trimmed strings")
    if len(set(inputs.configuration_ids)) != width:
        raise UncomputableStatisticError("configuration_ids must be unique")

    block_count = inputs.block_count
    if block_count is None:
        raise MissingStatisticPolicyError("block_count must be frozen before calculation")
    if isinstance(block_count, bool) or not isinstance(block_count, int):
        raise MissingStatisticPolicyError("block_count must be an even integer")
    if block_count < 2 or block_count % 2 != 0:
        raise MissingStatisticPolicyError("block_count must be an even integer of at least two")
    if len(matrix) % block_count != 0:
        raise UncomputableStatisticError(
            "PBO rows must divide exactly into equal contiguous blocks"
        )
    if not isinstance(inputs.selection_metric, PBOSelectionMetric):
        raise MissingStatisticPolicyError("selection_metric must be frozen before calculation")
    if inputs.selection_metric is not PBOSelectionMetric.MEAN_RETURN:
        raise MissingStatisticPolicyError("unsupported PBO selection_metric")
    if not isinstance(inputs.tie_policy, PBOTiePolicy):
        raise MissingStatisticPolicyError("tie_policy must be frozen before calculation")
    maximum_probability = _probability_policy("maximum_probability", inputs.maximum_probability)

    rows_per_block = len(matrix) // block_count
    blocks = tuple(
        PBOBlock(
            block_index=block_index,
            row_start=block_index * rows_per_block,
            row_stop=(block_index + 1) * rows_per_block,
        )
        for block_index in range(block_count)
    )
    split_results: list[PBOSplitResult] = []
    all_blocks = tuple(range(block_count))
    for train_blocks in combinations(all_blocks, block_count // 2):
        train_block_set = frozenset(train_blocks)
        test_blocks = tuple(index for index in all_blocks if index not in train_block_set)
        train_rows = tuple(
            row_index
            for block_index in train_blocks
            for row_index in range(blocks[block_index].row_start, blocks[block_index].row_stop)
        )
        test_rows = tuple(
            row_index
            for block_index in test_blocks
            for row_index in range(blocks[block_index].row_start, blocks[block_index].row_stop)
        )
        in_sample_scores = _mean_scores(matrix, train_rows)
        out_of_sample_scores = _mean_scores(matrix, test_rows)
        selected_index = _select_best(in_sample_scores, inputs.tie_policy)
        out_of_sample_ranks = _rank_worst_to_best(out_of_sample_scores, inputs.tie_policy)
        selected_rank = out_of_sample_ranks[selected_index]
        normalized_rank = selected_rank / (width + 1.0)
        logit = math.log(normalized_rank / (1.0 - normalized_rank))
        split_results.append(
            PBOSplitResult(
                train_blocks=tuple(train_blocks),
                test_blocks=test_blocks,
                train_row_indices=train_rows,
                test_row_indices=test_rows,
                in_sample_scores=in_sample_scores,
                out_of_sample_scores=out_of_sample_scores,
                selected_configuration_index=selected_index,
                selected_configuration_id=inputs.configuration_ids[selected_index],
                out_of_sample_ranks=out_of_sample_ranks,
                selected_out_of_sample_rank=selected_rank,
                normalized_rank=normalized_rank,
                logit=logit,
            )
        )

    probability = math.fsum(split.logit < 0.0 for split in split_results) / len(split_results)
    return PBOResult(
        formula_version=PBO_FORMULA_VERSION,
        matrix_hash_version=PBO_MATRIX_HASH_VERSION,
        matrix_sha256=_matrix_sha256(matrix, inputs.configuration_ids),
        configuration_ids=inputs.configuration_ids,
        blocks=blocks,
        splits=tuple(split_results),
        probability=probability,
        maximum_probability=maximum_probability,
        passes=probability <= maximum_probability,
        selection_metric=inputs.selection_metric,
        tie_policy=inputs.tie_policy,
    )
