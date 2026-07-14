from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from math import sqrt

import pytest
from fable5_backtester.contracts import (
    CostLedgerEntry,
    CostScenario,
    ResearchReturnStatus,
    SyntheticSample,
)
from fable5_backtester.costs import (
    CostInputError,
    CostScenarioSummary,
    build_cost_ledger,
    summarize_cost_scenario,
)
from fable5_backtester.synthetic import REGISTERED_FIXTURE, REGISTERED_POLICY


@pytest.fixture(scope="module")
def cost_ledger() -> tuple[CostLedgerEntry, ...]:
    return build_cost_ledger(
        REGISTERED_FIXTURE.samples,
        REGISTERED_POLICY.costs,
        REGISTERED_POLICY.stress,
    )


def _by_scenario_and_sample(
    entries: tuple[CostLedgerEntry, ...],
) -> dict[CostScenario, dict[str, CostLedgerEntry]]:
    return {
        scenario: {entry.sample_id: entry for entry in entries if entry.scenario is scenario}
        for scenario in CostScenario
    }


def _component_total(entry: CostLedgerEntry) -> Decimal:
    return (
        entry.fee_cost
        + entry.spread_cost
        + entry.impact_cost
        + entry.latency_cost
        + entry.borrow_cost
        + entry.capacity_cost
    )


def _has_universally_positive_stressed_edge(summary: CostScenarioSummary) -> bool:
    """Apply only the documented universal zero boundary, not fixture policy thresholds."""

    return (
        summary.aggregate_net_return > 0
        and summary.annualized_net_return > 0
        and summary.net_sharpe > 0
    )


def _no_trade_sample(index: int = 0) -> SyntheticSample:
    return REGISTERED_FIXTURE.samples[index].model_copy(
        update={
            "return_status": ResearchReturnStatus.NO_TRADE,
            "gross_return": Decimal("0"),
            "research_allocation_units": Decimal("0"),
            "gross_exposure": Decimal("0"),
            "net_exposure": Decimal("0"),
            "sector_exposure": Decimal("0"),
            "turnover": Decimal("0"),
            "borrow_applicable": False,
        }
    )


def test_registered_fixture_has_all_required_cost_scenarios_and_stress_floor(
    cost_ledger: tuple[CostLedgerEntry, ...],
) -> None:
    assert REGISTERED_FIXTURE.synthetic is True
    assert REGISTERED_FIXTURE.no_real_performance_claimed is True
    assert REGISTERED_POLICY.stress.all_cost_multiplier >= Decimal("2")
    assert len(cost_ledger) == len(REGISTERED_FIXTURE.samples) * len(CostScenario)
    assert {entry.scenario for entry in cost_ledger} == set(CostScenario)


def test_all_scenarios_preserve_exact_allocation_inputs_and_gross_research_returns(
    cost_ledger: tuple[CostLedgerEntry, ...],
) -> None:
    rows = _by_scenario_and_sample(cost_ledger)
    sample_ids = tuple(sample.sample_id for sample in REGISTERED_FIXTURE.samples)
    baseline = rows[CostScenario.BASELINE]
    for scenario in CostScenario:
        assert tuple(rows[scenario]) == sample_ids
        for sample_id in sample_ids:
            candidate = rows[scenario][sample_id]
            assert candidate.allocation_input_sha256 == baseline[sample_id].allocation_input_sha256
            assert candidate.gross_return == baseline[sample_id].gross_return

    summaries = {
        scenario: summarize_cost_scenario(
            cost_ledger,
            scenario,
            REGISTERED_POLICY.selection.annualization_factor,
        )
        for scenario in CostScenario
    }
    assert (
        summaries[CostScenario.BASELINE].allocation_input_sha256s
        == summaries[CostScenario.ALL_COST_STRESS].allocation_input_sha256s
        == summaries[CostScenario.LIQUIDITY_STRESS].allocation_input_sha256s
    )


def test_all_cost_stress_multiplies_every_applicable_component(
    cost_ledger: tuple[CostLedgerEntry, ...],
) -> None:
    rows = _by_scenario_and_sample(cost_ledger)
    multiplier = REGISTERED_POLICY.stress.all_cost_multiplier
    for sample in REGISTERED_FIXTURE.samples:
        baseline = rows[CostScenario.BASELINE][sample.sample_id]
        stressed = rows[CostScenario.ALL_COST_STRESS][sample.sample_id]

        assert stressed.fee_cost == baseline.fee_cost * multiplier
        assert stressed.spread_cost == baseline.spread_cost * multiplier
        assert stressed.impact_cost == baseline.impact_cost * multiplier
        assert stressed.latency_cost == baseline.latency_cost * multiplier
        assert stressed.borrow_cost == baseline.borrow_cost * multiplier
        if sample.borrow_applicable:
            assert baseline.borrow_cost > 0
        else:
            assert baseline.borrow_cost == stressed.borrow_cost == 0
        assert stressed.participation_rate == baseline.participation_rate
        assert stressed.capacity_breached is baseline.capacity_breached
        assert stressed.total_cost == _component_total(stressed)
        assert stressed.net_return == stressed.gross_return - stressed.total_cost


def test_independent_liquidity_stress_applies_each_frozen_component_rule(
    cost_ledger: tuple[CostLedgerEntry, ...],
) -> None:
    rows = _by_scenario_and_sample(cost_ledger)
    stress = REGISTERED_POLICY.stress
    capacity_limit = REGISTERED_POLICY.costs.baseline_max_participation
    for sample in REGISTERED_FIXTURE.samples:
        baseline = rows[CostScenario.BASELINE][sample.sample_id]
        liquidity = rows[CostScenario.LIQUIDITY_STRESS][sample.sample_id]
        expected_participation = baseline.participation_rate / stress.adv_multiplier
        expected_impact = (
            Decimal(str(sqrt(float(expected_participation))))
            * sample.daily_volatility
            * stress.volatility_multiplier
            * sample.impact_coefficient
            * stress.impact_coefficient_multiplier
        )

        assert liquidity.fee_cost == baseline.fee_cost
        assert liquidity.spread_cost == baseline.spread_cost * stress.spread_multiplier
        assert liquidity.participation_rate == expected_participation
        assert liquidity.impact_cost == expected_impact
        assert liquidity.impact_cost > baseline.impact_cost
        assert liquidity.latency_cost == baseline.latency_cost * stress.latency_multiplier
        assert liquidity.borrow_cost == baseline.borrow_cost * stress.borrow_multiplier
        assert liquidity.capacity_breached is (expected_participation > capacity_limit)
        assert isinstance(liquidity.capacity_breached, bool)
        assert liquidity.total_cost == _component_total(liquidity)
        assert liquidity.net_return == liquidity.gross_return - liquidity.total_cost


def test_capacity_state_and_summary_rate_remain_explicit_under_each_scenario(
    cost_ledger: tuple[CostLedgerEntry, ...],
) -> None:
    for scenario in CostScenario:
        selected = tuple(entry for entry in cost_ledger if entry.scenario is scenario)
        expected_rate = Decimal(sum(entry.capacity_breached for entry in selected)) / Decimal(
            len(selected)
        )
        summary = summarize_cost_scenario(
            cost_ledger,
            scenario,
            REGISTERED_POLICY.selection.annualization_factor,
        )
        assert all(entry.participation_rate >= 0 for entry in selected)
        assert all(isinstance(entry.capacity_breached, bool) for entry in selected)
        assert summary.capacity_breach_rate == expected_rate
        assert summary.fill_rate + summary.rejection_rate == 1
        assert summary.filled_quantity + summary.rejected_quantity == (summary.requested_quantity)


def test_capacity_breach_records_exact_rejected_and_unfilled_quantity() -> None:
    sample = REGISTERED_FIXTURE.samples[0].model_copy(update={"daily_adv_units": Decimal("100")})
    ledger = build_cost_ledger((sample,), REGISTERED_POLICY.costs, REGISTERED_POLICY.stress)

    assert all(entry.capacity_breached for entry in ledger)
    assert all(entry.fill_status == "capacity_rejected" for entry in ledger)
    assert all(entry.requested_quantity == Decimal("100") for entry in ledger)
    assert all(entry.filled_quantity == 0 for entry in ledger)
    assert all(entry.rejected_quantity == entry.unfilled_quantity == 100 for entry in ledger)
    assert all(entry.gross_return == 0 for entry in ledger)
    assert all(entry.total_cost == 0 for entry in ledger)
    assert all(entry.net_return == 0 for entry in ledger)

    invalid = ledger[0].model_dump(mode="python")
    invalid["gross_return"] = Decimal("0.01")
    invalid["net_return"] = Decimal("0.01")
    with pytest.raises(ValueError, match="capacity-rejected"):
        CostLedgerEntry.model_validate(invalid)


def test_liquidity_stress_can_reject_a_baseline_filled_allocation_without_retaining_pnl() -> None:
    sample = REGISTERED_FIXTURE.samples[0].model_copy(update={"daily_adv_units": Decimal("2500")})
    ledger = build_cost_ledger((sample,), REGISTERED_POLICY.costs, REGISTERED_POLICY.stress)
    by_scenario = {entry.scenario: entry for entry in ledger}

    assert by_scenario[CostScenario.BASELINE].fill_status == "filled"
    assert by_scenario[CostScenario.ALL_COST_STRESS].fill_status == "filled"
    liquidity = by_scenario[CostScenario.LIQUIDITY_STRESS]
    assert liquidity.fill_status == "capacity_rejected"
    assert liquidity.participation_rate > by_scenario[CostScenario.BASELINE].participation_rate
    assert liquidity.gross_return == liquidity.total_cost == liquidity.net_return == 0


def test_unavailable_hard_to_borrow_state_fails_closed() -> None:
    sample = next(item for item in REGISTERED_FIXTURE.samples if item.borrow_applicable)
    unavailable = sample.model_copy(update={"hard_to_borrow_available": False})

    with pytest.raises(CostInputError, match="hard-to-borrow"):
        build_cost_ledger((unavailable,), REGISTERED_POLICY.costs, REGISTERED_POLICY.stress)


def test_no_trade_emits_one_exact_zero_cost_row_per_scenario() -> None:
    sample = _no_trade_sample()
    ledger = build_cost_ledger((sample,), REGISTERED_POLICY.costs, REGISTERED_POLICY.stress)

    assert len(ledger) == len(CostScenario)
    assert {entry.scenario for entry in ledger} == set(CostScenario)
    assert len({entry.allocation_input_sha256 for entry in ledger}) == 1
    for entry in ledger:
        assert entry.return_status is ResearchReturnStatus.NO_TRADE
        assert entry.fill_status == "no_trade"
        assert entry.capacity_breached is False
        assert all(
            value == 0
            for value in (
                entry.requested_quantity,
                entry.filled_quantity,
                entry.rejected_quantity,
                entry.unfilled_quantity,
                entry.gross_return,
                entry.fee_cost,
                entry.spread_cost,
                entry.impact_cost,
                entry.latency_cost,
                entry.borrow_cost,
                entry.capacity_cost,
                entry.total_cost,
                entry.net_return,
                entry.participation_rate,
            )
        )


def test_observed_zero_pays_costs_while_no_trade_zero_does_not() -> None:
    observed_zero = REGISTERED_FIXTURE.samples[0].model_copy(update={"gross_return": Decimal("0")})
    no_trade = _no_trade_sample(1)
    ledger = build_cost_ledger(
        (observed_zero, no_trade),
        REGISTERED_POLICY.costs,
        REGISTERED_POLICY.stress,
    )
    baseline = {
        entry.sample_id: entry for entry in ledger if entry.scenario is CostScenario.BASELINE
    }

    observed = baseline[observed_zero.sample_id]
    explicit_no_trade = baseline[no_trade.sample_id]
    assert observed.return_status is ResearchReturnStatus.OBSERVED
    assert observed.total_cost > 0
    assert observed.net_return < 0
    assert explicit_no_trade.total_cost == explicit_no_trade.net_return == 0


def test_missing_return_cannot_enter_cost_calculation() -> None:
    missing = REGISTERED_FIXTURE.samples[0].model_copy(
        update={
            "return_status": ResearchReturnStatus.MISSING,
            "gross_return": None,
        }
    )
    with pytest.raises(CostInputError, match="missing return"):
        build_cost_ledger((missing,), REGISTERED_POLICY.costs, REGISTERED_POLICY.stress)


def test_summaries_identify_exactly_zero_and_negative_universal_edge() -> None:
    ledger = build_cost_ledger(
        REGISTERED_FIXTURE.samples,
        REGISTERED_POLICY.costs,
        REGISTERED_POLICY.stress,
    )
    baseline = tuple(entry for entry in ledger if entry.scenario is CostScenario.BASELINE)
    zero_rows = (
        baseline[0].model_copy(update={"net_return": Decimal("0.01")}),
        baseline[1].model_copy(update={"net_return": Decimal("-0.01")}),
    )
    zero = summarize_cost_scenario(zero_rows, CostScenario.BASELINE, 250)
    assert zero.aggregate_net_return == 0
    assert zero.annualized_net_return == 0
    assert zero.net_sharpe == 0
    assert _has_universally_positive_stressed_edge(zero) is False

    negative_rows = (
        baseline[0].model_copy(update={"net_return": Decimal("-0.02")}),
        baseline[1].model_copy(update={"net_return": Decimal("0.01")}),
    )
    negative = summarize_cost_scenario(negative_rows, CostScenario.BASELINE, 250)
    assert negative.aggregate_net_return < 0
    assert negative.annualized_net_return < 0
    assert negative.net_sharpe < 0
    assert _has_universally_positive_stressed_edge(negative) is False


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("aggregate_net_return", Decimal("0")),
        ("aggregate_net_return", Decimal("-0.000001")),
        ("annualized_net_return", Decimal("0")),
        ("annualized_net_return", Decimal("-0.000001")),
        ("net_sharpe", Decimal("0")),
        ("net_sharpe", Decimal("-0.000001")),
    ],
)
def test_each_nonpositive_universal_edge_input_is_independently_identifiable(
    cost_ledger: tuple[CostLedgerEntry, ...], field: str, value: Decimal
) -> None:
    positive = summarize_cost_scenario(
        cost_ledger,
        CostScenario.ALL_COST_STRESS,
        REGISTERED_POLICY.selection.annualization_factor,
    )
    if field == "aggregate_net_return":
        candidate = replace(positive, aggregate_net_return=value)
    elif field == "annualized_net_return":
        candidate = replace(positive, annualized_net_return=value)
    else:
        assert field == "net_sharpe"
        candidate = replace(positive, net_sharpe=value)

    assert getattr(candidate, field) <= 0
    assert _has_universally_positive_stressed_edge(candidate) is False
