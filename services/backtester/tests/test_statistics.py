from __future__ import annotations

import math
from dataclasses import replace

import pytest
from fable5_backtester.statistics import (
    DSR_NUMERIC_TOLERANCE,
    LAG1_EFFECTIVE_SAMPLE_METHOD,
    DeflatedSharpeInputs,
    MissingStatisticPolicyError,
    PBOInputs,
    PBOSelectionMetric,
    PBOTiePolicy,
    UncomputableStatisticError,
    compute_deflated_sharpe,
    compute_pbo,
    lag1_effective_sample_sensitivity,
)


def test_serial_correlation_sensitivity_reduces_effective_sample_length() -> None:
    values = (1.0, 2.0, 3.0, 1.0, 2.0, 3.0, 4.0, 2.0, 3.0, 4.0, 5.0, 3.0, 4.0, 5.0)

    result = lag1_effective_sample_sensitivity(values, LAG1_EFFECTIVE_SAMPLE_METHOD)

    assert result.lag1_autocorrelation == pytest.approx(0.4130434782608695, abs=1e-12)
    assert result.nominal_sample_length == 14
    assert result.raw_effective_sample_length == pytest.approx(5.815384615384615, abs=1e-12)
    assert result.effective_sample_length == 5


@pytest.mark.parametrize("method", [None, "unapproved-method"])
def test_serial_correlation_sensitivity_requires_frozen_supported_policy(
    method: str | None,
) -> None:
    with pytest.raises(MissingStatisticPolicyError, match="serial_correlation_method"):
        lag1_effective_sample_sensitivity((1.0, 2.0, 1.0), method)


def _published_dsr_inputs(effective_trials: float) -> DeflatedSharpeInputs:
    return DeflatedSharpeInputs.from_annualized(
        annualized_sharpe=2.5,
        annualized_sharpe_variance=0.5,
        periods_per_year=250,
        sample_length=1250,
        skew=-3.0,
        ordinary_kurtosis=10.0,
        effective_trials=effective_trials,
        minimum_probability=0.95,
    )


@pytest.mark.parametrize(
    ("effective_trials", "expected_benchmark", "expected_probability", "passes"),
    [
        (100.0, 0.11317200186513214, 0.9003968344493904, False),
        (46.0, 0.10036237061765357, 0.9505017068755786, True),
    ],
)
def test_dsr_reproduces_published_bailey_lopez_de_prado_oracle(
    effective_trials: float,
    expected_benchmark: float,
    expected_probability: float,
    passes: bool,
) -> None:
    result = compute_deflated_sharpe(_published_dsr_inputs(effective_trials))

    assert result.expected_maximum_sharpe == pytest.approx(
        expected_benchmark,
        abs=DSR_NUMERIC_TOLERANCE,
        rel=DSR_NUMERIC_TOLERANCE,
    )
    assert result.probability == pytest.approx(
        expected_probability,
        abs=DSR_NUMERIC_TOLERANCE,
        rel=DSR_NUMERIC_TOLERANCE,
    )
    assert result.passes is passes


def test_dsr_matches_published_four_decimal_result() -> None:
    result = compute_deflated_sharpe(_published_dsr_inputs(46.0))
    assert round(result.probability, 4) == 0.9505


@pytest.mark.parametrize(
    "inputs,error_type,error",
    [
        (
            replace(_published_dsr_inputs(46.0), minimum_probability=None),
            MissingStatisticPolicyError,
            "minimum_probability",
        ),
        (
            replace(_published_dsr_inputs(46.0), sharpe_variance=None),
            UncomputableStatisticError,
            "sharpe_variance",
        ),
        (
            replace(_published_dsr_inputs(46.0), sharpe_variance=0.0),
            UncomputableStatisticError,
            "must be positive",
        ),
        (
            replace(_published_dsr_inputs(46.0), effective_trials=1.0),
            UncomputableStatisticError,
            "greater than one",
        ),
        (
            replace(_published_dsr_inputs(46.0), sample_length=1),
            UncomputableStatisticError,
            "at least two",
        ),
    ],
)
def test_dsr_fails_closed_on_missing_policy_or_uncomputable_inputs(
    inputs: DeflatedSharpeInputs,
    error_type: type[ValueError],
    error: str,
) -> None:
    with pytest.raises(error_type, match=error):
        compute_deflated_sharpe(inputs)


def _pbo_oracle_inputs() -> PBOInputs:
    config_a = (7.0, 4.0, -5.0, -6.0)
    config_b = (0.0, 0.0, 0.0, 0.0)
    return PBOInputs(
        matrix=tuple(zip(config_a, config_b, strict=True)),
        configuration_ids=("configuration-a", "configuration-b"),
        block_count=4,
        selection_metric=PBOSelectionMetric.MEAN_RETURN,
        tie_policy=PBOTiePolicy.FAIL,
        maximum_probability=0.5,
    )


def test_pbo_exact_synthetic_oracle_enumerates_all_splits_and_full_evidence() -> None:
    result = compute_pbo(_pbo_oracle_inputs())

    assert result.probability == 1.0
    assert result.passes is False
    assert len(result.blocks) == 4
    assert len(result.splits) == math.comb(4, 2) == 6
    assert len(result.matrix_sha256) == 64
    assert all(
        split.logit == pytest.approx(-math.log(2.0), abs=1e-12, rel=1e-12)
        for split in result.splits
    )
    for split in result.splits:
        assert split.selected_out_of_sample_rank == 1
        assert split.normalized_rank == pytest.approx(1.0 / 3.0)
        assert split.test_blocks == tuple(
            block for block in range(4) if block not in split.train_blocks
        )
        assert set(split.train_row_indices).isdisjoint(split.test_row_indices)
        assert sorted(split.train_row_indices + split.test_row_indices) == list(range(4))


def test_pbo_reproduces_published_three_configuration_ranking_example() -> None:
    """Reproduce Bailey et al. section 2.1's numeric IS/OOS rank example.

    The published score vectors are IS=(0.5, 1.1, 0.7) and
    OOS=(0.6, 0.7, 1.3). With one row per symmetric block, the published
    IS winner is configuration 2 and its OOS rank is exactly 2 of 3.
    """

    inputs = PBOInputs(
        matrix=((0.5, 1.1, 0.7), (0.6, 0.7, 1.3)),
        configuration_ids=("configuration-1", "configuration-2", "configuration-3"),
        block_count=2,
        selection_metric=PBOSelectionMetric.MEAN_RETURN,
        tie_policy=PBOTiePolicy.FAIL,
        maximum_probability=1.0,
    )

    result = compute_pbo(inputs)

    published_direction = next(split for split in result.splits if split.train_blocks == (0,))
    assert published_direction.selected_configuration_id == "configuration-2"
    assert published_direction.in_sample_scores == pytest.approx((0.5, 1.1, 0.7))
    assert published_direction.out_of_sample_scores == pytest.approx((0.6, 0.7, 1.3))
    assert published_direction.selected_out_of_sample_rank == 2
    assert published_direction.normalized_rank == pytest.approx(0.5, abs=1e-12)
    assert published_direction.logit == pytest.approx(0.0, abs=1e-12)
    assert result.probability == pytest.approx(0.0, abs=1e-12)


def test_pbo_matrix_hash_is_deterministic_and_binds_configuration_order() -> None:
    first = compute_pbo(_pbo_oracle_inputs())
    second = compute_pbo(_pbo_oracle_inputs())
    reversed_ids = replace(
        _pbo_oracle_inputs(),
        configuration_ids=("configuration-b", "configuration-a"),
    )

    assert first.matrix_sha256 == second.matrix_sha256
    assert first.matrix_sha256 != compute_pbo(reversed_ids).matrix_sha256


def test_pbo_lowest_index_tie_policy_is_deterministic() -> None:
    tied = PBOInputs(
        matrix=((1.0, 1.0), (1.0, 1.0), (1.0, 1.0), (1.0, 1.0)),
        configuration_ids=("first", "second"),
        block_count=4,
        selection_metric=PBOSelectionMetric.MEAN_RETURN,
        tie_policy=PBOTiePolicy.LOWEST_INDEX,
        maximum_probability=1.0,
    )
    result = compute_pbo(tied)

    assert {split.selected_configuration_id for split in result.splits} == {"first"}
    assert {split.selected_out_of_sample_rank for split in result.splits} == {2}
    assert result.probability == 0.0


@pytest.mark.parametrize(
    "inputs,error_type,error",
    [
        (
            replace(_pbo_oracle_inputs(), maximum_probability=None),
            MissingStatisticPolicyError,
            "maximum_probability",
        ),
        (
            replace(_pbo_oracle_inputs(), block_count=3),
            MissingStatisticPolicyError,
            "even integer",
        ),
        (
            replace(_pbo_oracle_inputs(), matrix=((7.0, 0.0), (None, 0.0))),
            UncomputableStatisticError,
            "cannot contain missing",
        ),
        (
            PBOInputs(
                matrix=((1.0, 1.0), (1.0, 1.0)),
                configuration_ids=("first", "second"),
                block_count=2,
                selection_metric=PBOSelectionMetric.MEAN_RETURN,
                tie_policy=PBOTiePolicy.FAIL,
                maximum_probability=1.0,
            ),
            UncomputableStatisticError,
            "contains a tie",
        ),
    ],
)
def test_pbo_fails_closed_on_missing_policy_or_uncomputable_inputs(
    inputs: PBOInputs,
    error_type: type[ValueError],
    error: str,
) -> None:
    with pytest.raises(error_type, match=error):
        compute_pbo(inputs)
