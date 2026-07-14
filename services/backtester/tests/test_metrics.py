from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from fable5_backtester.contracts import (
    CostLedgerEntry,
    CostScenario,
    FoldKind,
    FoldRecord,
    SyntheticSample,
)
from fable5_backtester.costs import (
    CostScenarioSummary,
    build_cost_ledger,
    summarize_cost_scenario,
)
from fable5_backtester.metrics import (
    CORE_METRIC_IDS,
    COST_COMPONENT_FIELDS,
    SCENARIO_OUTCOMES,
    STRESS_SENSITIVITY_OUTCOMES,
    EvaluationMetricDiagnostics,
    MetricInputError,
    build_evaluation_metrics,
)
from fable5_backtester.synthetic import REGISTERED_FIXTURE, REGISTERED_POLICY
from pydantic import ValidationError


def _samples() -> tuple[SyntheticSample, ...]:
    gross_returns = (Decimal("0.10"), Decimal("-0.05"), Decimal("0.20"), Decimal("-0.10"))
    turnovers = (Decimal("0.10"), Decimal("0.20"), Decimal("0.30"), Decimal("0.40"))
    gross_exposures = (Decimal("0.10"), Decimal("0.20"), Decimal("0.30"), Decimal("0.40"))
    net_exposures = (Decimal("0.10"), Decimal("-0.10"), Decimal("0"), Decimal("0.20"))
    sector_exposures = (Decimal("0.05"), Decimal("0.10"), Decimal("0.20"), Decimal("0.40"))
    allocation_units = (Decimal("100"), Decimal("200"), Decimal("300"), Decimal("400"))
    daily_adv = (Decimal("10000"), Decimal("10000"), Decimal("10000"), Decimal("1000"))
    decision_origin = datetime(2026, 1, 30, 16, tzinfo=UTC)
    samples: list[SyntheticSample] = []
    for index, base in enumerate(REGISTERED_FIXTURE.samples[:4]):
        decision = decision_origin + timedelta(days=index)
        content = base.model_dump(mode="python")
        content.update(
            {
                "decision_time_utc": decision,
                "feature_available_at_utc": decision - timedelta(hours=1),
                "label_t0_utc": decision,
                "label_t1_utc": decision + timedelta(days=2),
                "gross_return": gross_returns[index],
                "research_allocation_units": allocation_units[index],
                "reference_price": Decimal("1"),
                "daily_adv_units": daily_adv[index],
                "daily_volatility": (Decimal("0.015") if index < 3 else Decimal("0.025")),
                "independent_event_id": ("event-shared" if index < 2 else f"event-{index}"),
                "regime_id": "low-vol" if index < 3 else "high-vol",
                "rate_available_at_utc": decision - timedelta(hours=2),
                "rate_change": Decimal("0.01") if index % 2 == 0 else Decimal("-0.01"),
                "crisis_window_ids": (
                    (REGISTERED_POLICY.regimes.crisis_windows[0],) if index == 3 else ()
                ),
                "gross_exposure": gross_exposures[index],
                "net_exposure": net_exposures[index],
                "sector_exposure": sector_exposures[index],
                "turnover": turnovers[index],
            }
        )
        samples.append(SyntheticSample.model_validate(content))
    return tuple(samples)


def _fold(
    ordinal: int,
    sample_ids: tuple[str, ...],
    start: datetime,
) -> FoldRecord:
    digit = str(ordinal + 1)
    return FoldRecord(
        fold_id=UUID(f"00000000-0000-5000-8000-00000000000{ordinal + 1}"),
        ordinal=ordinal,
        fold_sha256=digit * 64,
        fold_kind=FoldKind.OUTER,
        parent_fold_id=None,
        train_start_utc=start - timedelta(days=10),
        train_end_utc=start - timedelta(days=2),
        test_start_utc=start,
        test_end_utc=start + timedelta(days=max(len(sample_ids) - 1, 0)),
        train_sample_ids=(f"train-{ordinal}",),
        purged_sample_ids=(),
        test_sample_ids=sample_ids,
        embargoed_sample_ids=(),
        embargo_duration_seconds=0,
        embargo_applied=False,
    )


def _folds(samples: tuple[SyntheticSample, ...]) -> tuple[FoldRecord, ...]:
    return (
        _fold(
            0,
            tuple(sample.sample_id for sample in samples[:3]),
            samples[0].decision_time_utc,
        ),
        _fold(1, (samples[3].sample_id,), samples[3].decision_time_utc),
    )


def _diagnostics() -> EvaluationMetricDiagnostics:
    return EvaluationMetricDiagnostics(
        raw_trial_count=6,
        effective_trial_count=Decimal("3"),
        sharpe_variance=Decimal("0.25"),
        dsr_probability=Decimal("0.80"),
        dsr_inputs=(
            ("estimated_sharpe", Decimal("1.25")),
            ("sample_length", 4),
            ("skew", Decimal("0.1")),
            ("ordinary_kurtosis", Decimal("3.2")),
            ("sharpe_variance", Decimal("0.25")),
            ("effective_trials", Decimal("3")),
        ),
        pbo_probability=Decimal("0.20"),
        pbo_inputs=(
            ("split_count", 6),
            ("configuration_count", 4),
            ("tie_policy", "reject_ties"),
            ("rank_orientation", "worst_is_one"),
        ),
        missing_return_count=0,
        no_trade_count=0,
        exclusions=("reserved final confirmation interval",),
    )


def _evidence() -> tuple[
    tuple[SyntheticSample, ...],
    tuple[FoldRecord, ...],
    tuple[CostLedgerEntry, ...],
    tuple[CostScenarioSummary, ...],
]:
    samples = _samples()
    folds = _folds(samples)
    costs = build_cost_ledger(samples, REGISTERED_POLICY.costs, REGISTERED_POLICY.stress)
    summaries = tuple(
        summarize_cost_scenario(
            costs,
            scenario,
            REGISTERED_POLICY.selection.annualization_factor,
        )
        for scenario in CostScenario
    )
    return samples, folds, costs, summaries


def test_metrics_use_exact_row_weights_and_complete_metadata() -> None:
    samples, folds, costs, summaries = _evidence()
    metrics = build_evaluation_metrics(
        samples=samples,
        folds=folds,
        cost_ledger=costs,
        scenario_summaries=summaries,
        policy=REGISTERED_POLICY,
        diagnostics=_diagnostics(),
    )
    by_id = {metric.metric_id: metric for metric in metrics}

    baseline = next(item for item in summaries if item.scenario is CostScenario.BASELINE)
    assert by_id["gross_pnl"].value == baseline.aggregate_gross_return == Decimal("0.25")
    assert by_id["net_pnl"].value == baseline.aggregate_net_return
    assert by_id["gross_hit_ratio"].value == Decimal("0.5")
    assert by_id["gross_average_win"].value == Decimal("0.15")
    assert by_id["gross_average_loss"].value == Decimal("-0.05")
    assert by_id["turnover_total"].value == Decimal("1.00")
    assert by_id["turnover_mean"].value == Decimal("0.25")
    assert by_id["observation_allocation_concentration_hhi"].value == Decimal("0.30")
    assert by_id["participation_mean"].value == Decimal("0.115")
    assert by_id["capacity_breach_rate"].value == Decimal("0.25")

    assert by_id["pnl:outer_fold:0:gross"].value == Decimal("0.25")
    assert by_id["pnl:outer_fold:1:gross"].value == Decimal("0")
    assert by_id["pnl:calendar_month:2026-01:gross"].value == Decimal("0.05")
    assert by_id["pnl:calendar_month:2026-02:gross"].value == Decimal("0.20")
    assert by_id["pnl:regime:low-vol:gross"].value == Decimal("0.25")
    assert by_id["turnover:regime:low-vol:mean"].value == Decimal("0.20")
    assert by_id["turnover:regime:high-vol:mean"].value == Decimal("0.40")
    assert by_id["capacity:regime:low-vol:breach_rate"].value == Decimal("0")
    assert by_id["capacity:regime:high-vol:breach_rate"].value == Decimal("1")
    assert by_id["pnl:volatility:low:gross"].value == Decimal("0.25")
    assert by_id["pnl:volatility:high:gross"].value == Decimal("0")
    assert by_id["pnl:rate:rising:gross"].value == Decimal("0.30")
    assert by_id["pnl:rate:falling:gross"].value == Decimal("-0.05")
    crisis = REGISTERED_POLICY.regimes.crisis_windows[0]
    assert by_id[f"pnl:crisis:{crisis}:gross"].value == Decimal("0")

    baseline_costs = tuple(item for item in costs if item.scenario is CostScenario.BASELINE)
    baseline_commission = sum((item.fee_cost for item in baseline_costs), Decimal("0"))
    assert by_id["cost:baseline:commission"].value == baseline_commission
    assert by_id["cost:all_cost_stress:commission"].value == baseline_commission * 2
    assert by_id["stress:all_cost_stress:commission_cost_delta"].value == (baseline_commission)
    stressed = next(item for item in summaries if item.scenario is CostScenario.ALL_COST_STRESS)
    assert by_id["stress:all_cost_stress:net_pnl_delta"].value == (
        stressed.aggregate_net_return - baseline.aggregate_net_return
    )

    assert by_id["trial:M_raw"].value == Decimal("6")
    assert by_id["trial:N_eff"].value == Decimal("3")
    assert by_id["trial:V_SR"].value == Decimal("0.25")
    assert by_id["sample:oos_count"].value == Decimal("4")
    assert by_id["sample:independent_event_count"].value == Decimal("3")
    assert by_id["sample:missing_return_count"].value == Decimal("0")
    assert by_id["sample:no_trade_count"].value == Decimal("0")

    assert isinstance(metrics, tuple)
    assert len(by_id) == len(metrics)
    assert set(CORE_METRIC_IDS) <= by_id.keys()
    for metric in metrics:
        assert metric.formula_version
        assert metric.units
        assert metric.frequency == REGISTERED_POLICY.selection.return_frequency
        assert metric.annualization_factor == REGISTERED_POLICY.selection.annualization_factor
        assert metric.timezone == "UTC"
        assert metric.calendar == REGISTERED_POLICY.walk_forward.decision_calendar
        assert metric.population
        assert metric.exclusions == ("reserved final confirmation interval",)
        assert metric.denominator
        assert metric.inputs
    with pytest.raises(ValidationError, match="frozen"):
        metrics[0].value = Decimal("999")


def test_metric_vocabulary_covers_costs_stresses_and_all_required_group_cuts() -> None:
    samples, folds, costs, summaries = _evidence()
    metrics = build_evaluation_metrics(
        samples=samples,
        folds=folds,
        cost_ledger=costs,
        scenario_summaries=summaries,
        policy=REGISTERED_POLICY,
        diagnostics=_diagnostics(),
    )
    identifiers = {metric.metric_id for metric in metrics}

    for scenario in CostScenario:
        assert {
            *(f"cost:{scenario.value}:{name}" for name, _ in COST_COMPONENT_FIELDS),
            *(f"scenario:{scenario.value}:{name}" for name in SCENARIO_OUTCOMES),
        } <= identifiers
    for scenario in (CostScenario.ALL_COST_STRESS, CostScenario.LIQUIDITY_STRESS):
        assert {
            f"stress:{scenario.value}:{outcome}" for outcome in STRESS_SENSITIVITY_OUTCOMES
        } <= identifiers

    assert sum(identifier.startswith("pnl:outer_fold:") for identifier in identifiers) == 4
    assert sum(identifier.startswith("pnl:calendar_month:") for identifier in identifiers) == 4
    assert sum(identifier.startswith("pnl:regime:") for identifier in identifiers) == 4
    assert sum(identifier.startswith("turnover:regime:") for identifier in identifiers) == 2
    assert sum(identifier.startswith("participation:regime:") for identifier in identifiers) == 2
    assert sum(identifier.startswith("capacity:regime:") for identifier in identifiers) == 2
    assert sum(identifier.startswith("pnl:volatility:") for identifier in identifiers) == 4
    assert sum(identifier.startswith("pnl:rate:") for identifier in identifiers) == 4
    assert sum(identifier.startswith("pnl:crisis:") for identifier in identifiers) == 2
    for dimension, group_count in (("volatility", 2), ("rate", 2), ("crisis", 1)):
        assert (
            sum(identifier.startswith(f"turnover:{dimension}:") for identifier in identifiers)
            == group_count
        )
        assert (
            sum(identifier.startswith(f"participation:{dimension}:") for identifier in identifiers)
            == group_count
        )
        assert (
            sum(identifier.startswith(f"capacity:{dimension}:") for identifier in identifiers)
            == group_count
        )
    rendered = " ".join(sorted(identifiers)).lower()
    for forbidden in ("buy", "sell", "order", "broker", "position", "live"):
        assert forbidden not in rendered


def test_metrics_fail_closed_on_incomplete_statistics_or_inconsistent_evidence() -> None:
    with pytest.raises(MetricInputError, match="DSR inputs are incomplete"):
        replace(
            _diagnostics(),
            dsr_inputs=(("estimated_sharpe", Decimal("1")),),
        )

    samples, folds, costs, summaries = _evidence()
    with pytest.raises(MetricInputError, match="no-trade diagnostic count disagrees"):
        build_evaluation_metrics(
            samples=samples,
            folds=folds,
            cost_ledger=costs,
            scenario_summaries=summaries,
            policy=REGISTERED_POLICY,
            diagnostics=replace(_diagnostics(), no_trade_count=1),
        )

    duplicated_owner = folds[1].model_copy(
        update={"test_sample_ids": (samples[0].sample_id, samples[3].sample_id)}
    )
    with pytest.raises(MetricInputError, match="ownership is missing or duplicated"):
        build_evaluation_metrics(
            samples=samples,
            folds=(folds[0], duplicated_owner),
            cost_ledger=costs,
            scenario_summaries=summaries,
            policy=REGISTERED_POLICY,
            diagnostics=_diagnostics(),
        )

    bad_baseline = replace(
        summaries[0],
        aggregate_net_return=summaries[0].aggregate_net_return + Decimal("0.01"),
    )
    with pytest.raises(MetricInputError, match="does not reproduce"):
        build_evaluation_metrics(
            samples=samples,
            folds=folds,
            cost_ledger=costs,
            scenario_summaries=(bad_baseline, *summaries[1:]),
            policy=REGISTERED_POLICY,
            diagnostics=_diagnostics(),
        )
