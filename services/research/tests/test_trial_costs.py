from __future__ import annotations

from decimal import Decimal

import pytest
from fable5_backtester.contracts import CostScenario, ResearchReturnStatus, SyntheticSample
from fable5_backtester.costs import build_cost_ledger
from fable5_backtester.synthetic import REGISTERED_FIXTURE, REGISTERED_POLICY
from fable5_research.trial_costs import (
    TRIAL_RETURN_QUANTUM,
    TrialCostBridgeError,
    build_long_flat_overlay,
    build_long_flat_trial_costs,
)


def _long_templates() -> tuple[SyntheticSample, SyntheticSample]:
    samples = tuple(item for item in REGISTERED_FIXTURE.samples if not item.borrow_applicable)
    return samples[0], samples[1]


def test_active_weight_builds_observed_fixed_long_overlay() -> None:
    base, _ = _long_templates()
    overlay = build_long_flat_overlay(
        base,
        weight=Decimal("1"),
        label_return=Decimal("0.0123456789017"),
    )

    assert overlay.return_status is ResearchReturnStatus.OBSERVED
    assert overlay.predicted_value == Decimal("1")
    assert overlay.gross_return == Decimal("0.012345678902")
    assert overlay.research_allocation_units == base.research_allocation_units
    assert overlay.gross_exposure == base.gross_exposure
    assert overlay.net_exposure == base.net_exposure
    assert overlay.sector_exposure == base.sector_exposure
    assert overlay.turnover == base.turnover
    assert overlay.borrow_applicable is False


def test_zero_weight_builds_exact_no_trade_overlay() -> None:
    base, _ = _long_templates()
    overlay = build_long_flat_overlay(
        base,
        weight=Decimal("0"),
        label_return=Decimal("0.75"),
    )

    assert overlay.return_status is ResearchReturnStatus.NO_TRADE
    assert overlay.predicted_value == 0
    assert overlay.gross_return == 0
    assert overlay.research_allocation_units == 0
    assert overlay.gross_exposure == 0
    assert overlay.net_exposure == 0
    assert overlay.sector_exposure == 0
    assert overlay.turnover == 0
    assert overlay.borrow_applicable is False


@pytest.mark.parametrize("weight", [Decimal("-1"), Decimal("0.5"), Decimal("2")])
def test_continuous_or_negative_weights_fail_closed(weight: Decimal) -> None:
    base, _ = _long_templates()
    with pytest.raises(TrialCostBridgeError, match="exactly zero or one"):
        build_long_flat_overlay(base, weight=weight, label_return=Decimal("0.01"))


def test_invalid_long_template_fails_closed() -> None:
    borrowed = next(item for item in REGISTERED_FIXTURE.samples if item.borrow_applicable)
    with pytest.raises(TrialCostBridgeError, match="cannot incur borrow"):
        build_long_flat_overlay(
            borrowed,
            weight=Decimal("1"),
            label_return=Decimal("0.01"),
        )


def test_trial_costs_are_exact_phase5_component_ledgers() -> None:
    active, flat = _long_templates()
    samples = tuple(sorted((active, flat), key=lambda item: item.sample_id))
    weights = {samples[0].sample_id: Decimal("1"), samples[1].sample_id: Decimal("0")}
    labels = {samples[0].sample_id: Decimal("0.02"), samples[1].sample_id: Decimal("-0.03")}

    result = build_long_flat_trial_costs(
        samples,
        weights=weights,
        label_returns=labels,
        cost_policy=REGISTERED_POLICY.costs,
        stress_policy=REGISTERED_POLICY.stress,
    )

    assert result.cost_ledger == build_cost_ledger(
        result.samples,
        REGISTERED_POLICY.costs,
        REGISTERED_POLICY.stress,
    )
    assert len(result.cost_ledger) == len(samples) * len(CostScenario)
    active_id = samples[0].sample_id
    flat_id = samples[1].sample_id
    active_entries = tuple(item for item in result.cost_ledger if item.sample_id == active_id)
    flat_entries = tuple(item for item in result.cost_ledger if item.sample_id == flat_id)
    assert {item.scenario for item in active_entries} == set(CostScenario)
    assert len({item.allocation_input_sha256 for item in active_entries}) == 1
    assert all(
        item.total_cost
        == item.fee_cost
        + item.spread_cost
        + item.impact_cost
        + item.latency_cost
        + item.borrow_cost
        + item.capacity_cost
        for item in active_entries
    )
    assert all(item.net_return == item.gross_return - item.total_cost for item in active_entries)
    assert all(item.return_status is ResearchReturnStatus.NO_TRADE for item in flat_entries)
    assert all(
        value == 0
        for item in flat_entries
        for value in (
            item.requested_quantity,
            item.filled_quantity,
            item.gross_return,
            item.fee_cost,
            item.spread_cost,
            item.impact_cost,
            item.latency_cost,
            item.borrow_cost,
            item.total_cost,
            item.net_return,
            item.participation_rate,
        )
    )


def test_trial_costs_are_deterministic_and_require_exact_sample_coverage() -> None:
    first, second = _long_templates()
    samples = tuple(sorted((first, second), key=lambda item: item.sample_id))
    weights = {item.sample_id: Decimal("1") for item in samples}
    labels = {
        item.sample_id: Decimal(index) / Decimal("100") for index, item in enumerate(samples, 1)
    }
    first_result = build_long_flat_trial_costs(
        samples,
        weights=weights,
        label_returns=labels,
        cost_policy=REGISTERED_POLICY.costs,
        stress_policy=REGISTERED_POLICY.stress,
    )
    assert (
        build_long_flat_trial_costs(
            samples,
            weights=weights,
            label_returns=labels,
            cost_policy=REGISTERED_POLICY.costs,
            stress_policy=REGISTERED_POLICY.stress,
        )
        == first_result
    )
    with pytest.raises(TrialCostBridgeError, match="cover every sample exactly"):
        build_long_flat_trial_costs(
            samples,
            weights={samples[0].sample_id: Decimal("1")},
            label_returns=labels,
            cost_policy=REGISTERED_POLICY.costs,
            stress_policy=REGISTERED_POLICY.stress,
        )
    with pytest.raises(TrialCostBridgeError, match="canonically sorted"):
        build_long_flat_trial_costs(
            tuple(reversed(samples)),
            weights=weights,
            label_returns=labels,
            cost_policy=REGISTERED_POLICY.costs,
            stress_policy=REGISTERED_POLICY.stress,
        )


def test_all_flat_trial_still_generates_three_zero_cost_scenarios() -> None:
    base, _ = _long_templates()
    result = build_long_flat_trial_costs(
        (base,),
        weights={base.sample_id: Decimal("0")},
        label_returns={base.sample_id: Decimal("0.5")},
        cost_policy=REGISTERED_POLICY.costs,
        stress_policy=REGISTERED_POLICY.stress,
    )

    assert len(result.cost_ledger) == len(CostScenario)
    assert all(item.return_status is ResearchReturnStatus.NO_TRADE for item in result.cost_ledger)
    assert all(item.total_cost == 0 and item.net_return == 0 for item in result.cost_ledger)
    assert result.samples[0].gross_return == Decimal("0").quantize(TRIAL_RETURN_QUANTUM)
