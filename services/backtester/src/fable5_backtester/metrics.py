"""Pure, deterministic Phase 5 metric calculation over synthetic OOS evidence."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from fable5_backtester.contracts import (
    CostLedgerEntry,
    CostScenario,
    FoldKind,
    FoldRecord,
    FrozenEvaluationPolicy,
    MetricRecord,
    ResearchReturnStatus,
    SyntheticSample,
)
from fable5_backtester.costs import CostScenarioSummary, summarize_cost_scenario

MetricInputValue = str | int | Decimal

DSR_REQUIRED_INPUTS = frozenset(
    {
        "estimated_sharpe",
        "sample_length",
        "skew",
        "ordinary_kurtosis",
        "sharpe_variance",
        "effective_trials",
    }
)
PBO_REQUIRED_INPUTS = frozenset(
    {"split_count", "configuration_count", "tie_policy", "rank_orientation"}
)

CORE_METRIC_IDS = (
    "gross_pnl",
    "net_pnl",
    "gross_sharpe",
    "net_sharpe",
    "gross_sortino",
    "net_sortino",
    "gross_calmar",
    "net_calmar",
    "gross_annualized_return",
    "net_annualized_return",
    "gross_annualized_volatility",
    "net_annualized_volatility",
    "gross_maximum_drawdown",
    "net_maximum_drawdown",
    "gross_maximum_drawdown_duration",
    "net_maximum_drawdown_duration",
    "gross_hit_ratio",
    "net_hit_ratio",
    "gross_average_win",
    "gross_average_loss",
    "net_average_win",
    "net_average_loss",
    "turnover_total",
    "turnover_mean",
    "gross_exposure_mean",
    "gross_exposure_max",
    "net_exposure_mean",
    "net_absolute_exposure_max",
    "sector_exposure_mean",
    "sector_exposure_max",
    "observation_allocation_concentration_hhi",
    "participation_mean",
    "participation_max",
    "capacity_breach_rate",
    "trial:M_raw",
    "trial:N_eff",
    "trial:V_SR",
    "selection:dsr_probability",
    "selection:pbo_probability",
    "sample:oos_count",
    "sample:independent_event_count",
    "sample:missing_return_count",
    "sample:no_trade_count",
    "gross_autocorrelation_lag1",
    "net_autocorrelation_lag1",
)

COST_COMPONENT_FIELDS = (
    ("commission", "fee_cost"),
    ("spread", "spread_cost"),
    ("impact", "impact_cost"),
    ("delay", "latency_cost"),
    ("borrow", "borrow_cost"),
    ("capacity", "capacity_cost"),
    ("total", "total_cost"),
)
SCENARIO_OUTCOMES = (
    "gross_pnl",
    "net_pnl",
    "annualized_net_return",
    "net_sharpe",
    "maximum_drawdown",
    "capacity_breach_rate",
    "fill_rate",
    "rejection_rate",
    "filled_quantity",
    "rejected_quantity",
)
STRESS_SENSITIVITY_OUTCOMES = (
    "commission_cost_delta",
    "spread_cost_delta",
    "impact_cost_delta",
    "delay_cost_delta",
    "borrow_cost_delta",
    "capacity_cost_delta",
    "total_cost_delta",
    "net_pnl_delta",
    "annualized_net_return_delta",
    "net_sharpe_delta",
    "maximum_drawdown_delta",
    "capacity_breach_rate_delta",
    "fill_rate_delta",
    "rejection_rate_delta",
)


class MetricInputError(ValueError):
    """Required metric evidence is absent, inconsistent, or uncomputable."""


@dataclass(frozen=True, slots=True)
class EvaluationMetricDiagnostics:
    """Frozen selection and missing-data evidence not derivable from OOS sample rows."""

    raw_trial_count: int
    effective_trial_count: Decimal
    sharpe_variance: Decimal
    dsr_probability: Decimal
    dsr_inputs: tuple[tuple[str, MetricInputValue], ...]
    pbo_probability: Decimal
    pbo_inputs: tuple[tuple[str, MetricInputValue], ...]
    missing_return_count: int
    no_trade_count: int
    exclusions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.raw_trial_count < 1:
            raise MetricInputError("raw trial count must include at least one trial")
        if not Decimal("1") < self.effective_trial_count <= self.raw_trial_count:
            raise MetricInputError("effective trial count must be in (1, M_raw]")
        if self.sharpe_variance <= 0 or not self.sharpe_variance.is_finite():
            raise MetricInputError("Sharpe variance must be positive and finite")
        for name, probability in (
            ("DSR", self.dsr_probability),
            ("PBO", self.pbo_probability),
        ):
            if not probability.is_finite() or not Decimal("0") <= probability <= Decimal("1"):
                raise MetricInputError(f"{name} probability must be finite and in [0, 1]")
        if self.missing_return_count < 0 or self.no_trade_count < 0:
            raise MetricInputError("missing and no-trade counts cannot be negative")
        _validated_inputs("DSR", self.dsr_inputs, DSR_REQUIRED_INPUTS)
        _validated_inputs("PBO", self.pbo_inputs, PBO_REQUIRED_INPUTS)


@dataclass(frozen=True, slots=True)
class _SeriesStatistics:
    aggregate_return: Decimal
    annualized_return: Decimal
    annualized_volatility: Decimal
    sharpe: Decimal
    sortino: Decimal
    calmar: Decimal
    maximum_drawdown: Decimal
    maximum_drawdown_duration: int
    hit_ratio: Decimal
    average_win: Decimal
    average_loss: Decimal
    lag1_autocorrelation: Decimal


def _validated_inputs(
    name: str,
    values: tuple[tuple[str, MetricInputValue], ...],
    required: frozenset[str],
) -> dict[str, MetricInputValue]:
    result: dict[str, MetricInputValue] = {}
    for key, value in values:
        if not key or key in result:
            raise MetricInputError(f"{name} inputs require unique nonblank keys")
        if isinstance(value, bool):
            raise MetricInputError(f"{name} inputs do not accept boolean numeric substitutes")
        if isinstance(value, Decimal) and not value.is_finite():
            raise MetricInputError(f"{name} inputs must be finite")
        result[key] = value
    missing = required - result.keys()
    if missing:
        raise MetricInputError(f"{name} inputs are incomplete: {', '.join(sorted(missing))}")
    return result


def _mean(values: tuple[Decimal, ...]) -> Decimal:
    if not values:
        raise MetricInputError("a metric denominator is empty")
    return sum(values, Decimal("0")) / Decimal(len(values))


def _sample_standard_deviation(values: tuple[Decimal, ...]) -> Decimal:
    if len(values) < 2:
        raise MetricInputError("sample standard deviation requires at least two observations")
    mean = _mean(values)
    variance = sum(((value - mean) ** 2 for value in values), Decimal("0")) / Decimal(
        len(values) - 1
    )
    if variance <= 0:
        raise MetricInputError("return variance is zero or negative")
    return variance.sqrt()


def _drawdown(values: tuple[Decimal, ...]) -> tuple[Decimal, int]:
    wealth = Decimal("1")
    peak = wealth
    maximum = Decimal("0")
    duration = 0
    maximum_duration = 0
    for value in values:
        if value <= Decimal("-1"):
            raise MetricInputError("returns at or below -100% make drawdown uncomputable")
        wealth *= Decimal("1") + value
        if wealth >= peak:
            peak = wealth
            duration = 0
        else:
            duration += 1
            maximum_duration = max(maximum_duration, duration)
            maximum = max(maximum, (peak - wealth) / peak)
    if maximum <= 0:
        raise MetricInputError("Calmar ratio requires a positive observed drawdown")
    return maximum, maximum_duration


def _lag1_autocorrelation(values: tuple[Decimal, ...]) -> Decimal:
    if len(values) < 3:
        raise MetricInputError("lag-1 autocorrelation requires at least three observations")
    left = values[:-1]
    right = values[1:]
    left_mean = _mean(left)
    right_mean = _mean(right)
    numerator = sum(
        (
            (first - left_mean) * (second - right_mean)
            for first, second in zip(left, right, strict=True)
        ),
        Decimal("0"),
    )
    left_square = sum(((value - left_mean) ** 2 for value in left), Decimal("0"))
    right_square = sum(((value - right_mean) ** 2 for value in right), Decimal("0"))
    denominator = (left_square * right_square).sqrt()
    if denominator <= 0:
        raise MetricInputError("lag-1 autocorrelation denominator is zero")
    return numerator / denominator


def _series_statistics(
    values: tuple[Decimal, ...],
    annualization_factor: int,
) -> _SeriesStatistics:
    if len(values) < 3 or any(not value.is_finite() for value in values):
        raise MetricInputError("performance metrics require at least three finite returns")
    mean = _mean(values)
    standard_deviation = _sample_standard_deviation(values)
    annualizer = Decimal(annualization_factor)
    annualized_return = mean * annualizer
    annualized_volatility = standard_deviation * annualizer.sqrt()
    downside_deviation = (
        sum((min(value, Decimal("0")) ** 2 for value in values), Decimal("0"))
        / Decimal(len(values))
    ).sqrt()
    if downside_deviation <= 0:
        raise MetricInputError("Sortino ratio requires a nonzero downside deviation")
    maximum_drawdown, maximum_duration = _drawdown(values)
    wins = tuple(value for value in values if value > 0)
    losses = tuple(value for value in values if value < 0)
    if not wins or not losses:
        raise MetricInputError("average win/loss requires both positive and negative returns")
    return _SeriesStatistics(
        aggregate_return=sum(values, Decimal("0")),
        annualized_return=annualized_return,
        annualized_volatility=annualized_volatility,
        sharpe=mean / standard_deviation * annualizer.sqrt(),
        sortino=mean / downside_deviation * annualizer.sqrt(),
        calmar=annualized_return / maximum_drawdown,
        maximum_drawdown=maximum_drawdown,
        maximum_drawdown_duration=maximum_duration,
        hit_ratio=Decimal(len(wins)) / Decimal(len(values)),
        average_win=_mean(wins),
        average_loss=_mean(losses),
        lag1_autocorrelation=_lag1_autocorrelation(values),
    )


def _metric(
    policy: FrozenEvaluationPolicy,
    *,
    metric_id: str,
    formula_version: str,
    value: Decimal,
    units: str,
    population: str,
    exclusions: tuple[str, ...],
    denominator: str,
    inputs: dict[str, MetricInputValue],
) -> MetricRecord:
    if not value.is_finite():
        raise MetricInputError(f"metric {metric_id} is non-finite")
    return MetricRecord(
        metric_id=metric_id,
        formula_version=formula_version,
        value=value,
        units=units,
        frequency=policy.selection.return_frequency,
        annualization_factor=policy.selection.annualization_factor,
        calendar=policy.walk_forward.decision_calendar,
        population=population,
        exclusions=exclusions,
        denominator=denominator,
        inputs=inputs,
    )


def _validate_and_index_costs(
    samples: tuple[SyntheticSample, ...],
    cost_ledger: tuple[CostLedgerEntry, ...],
    summaries: tuple[CostScenarioSummary, ...],
    policy: FrozenEvaluationPolicy,
) -> tuple[
    dict[tuple[CostScenario, str], CostLedgerEntry],
    dict[CostScenario, CostScenarioSummary],
]:
    sample_by_id = {sample.sample_id: sample for sample in samples}
    expected_keys = {
        (scenario, sample.sample_id) for scenario in CostScenario for sample in samples
    }
    indexed: dict[tuple[CostScenario, str], CostLedgerEntry] = {}
    for entry in cost_ledger:
        key = (entry.scenario, entry.sample_id)
        if key in indexed:
            raise MetricInputError("cost ledger has duplicate sample/scenario rows")
        sample = sample_by_id.get(entry.sample_id)
        if sample is None:
            raise MetricInputError("cost ledger contains an unknown OOS sample")
        if entry.return_status is not sample.return_status:
            raise MetricInputError("cost return status does not match its OOS sample")
        if sample.return_status is ResearchReturnStatus.MISSING:
            raise MetricInputError("missing OOS returns cannot enter metric calculation")
        if sample.return_status is ResearchReturnStatus.NO_TRADE:
            expected_gross_return = Decimal("0")
        else:
            if sample.gross_return is None:  # pragma: no cover - guarded by sample contract
                raise MetricInputError("non-missing OOS return lacks a value")
            expected_gross_return = (
                sample.gross_return * entry.filled_quantity / entry.requested_quantity
            )
        if entry.gross_return != expected_gross_return:
            raise MetricInputError("cost ledger gross return does not match its executed fill")
        component_total = (
            entry.fee_cost
            + entry.spread_cost
            + entry.impact_cost
            + entry.latency_cost
            + entry.borrow_cost
            + entry.capacity_cost
        )
        if (
            entry.total_cost != component_total
            or entry.net_return != entry.gross_return - component_total
        ):
            raise MetricInputError("cost ledger component arithmetic is inconsistent")
        if entry.capacity_breached != (
            entry.participation_rate > policy.costs.baseline_max_participation
        ):
            raise MetricInputError("capacity status is inconsistent with the frozen policy")
        indexed[key] = entry
    if indexed.keys() != expected_keys:
        raise MetricInputError("every OOS sample requires one row in every cost scenario")
    for sample in samples:
        hashes = {
            indexed[(scenario, sample.sample_id)].allocation_input_sha256
            for scenario in CostScenario
        }
        if len(hashes) != 1:
            raise MetricInputError("stress scenarios changed the frozen allocation input")

    summary_by_scenario = {summary.scenario: summary for summary in summaries}
    if len(summary_by_scenario) != len(summaries) or set(summary_by_scenario) != set(CostScenario):
        raise MetricInputError("every cost scenario requires exactly one summary")
    for scenario in CostScenario:
        ordered_entries = tuple(indexed[(scenario, sample.sample_id)] for sample in samples)
        expected = summarize_cost_scenario(
            ordered_entries,
            scenario,
            policy.selection.annualization_factor,
        )
        if summary_by_scenario[scenario] != expected:
            raise MetricInputError("cost scenario summary does not reproduce its ledger rows")
    return indexed, summary_by_scenario


def _outer_fold_groups(
    samples: tuple[SyntheticSample, ...],
    folds: tuple[FoldRecord, ...],
    expected_fold_count: int,
) -> tuple[tuple[FoldRecord, tuple[SyntheticSample, ...]], ...]:
    sample_by_id = {sample.sample_id: sample for sample in samples}
    outer = tuple(
        sorted(
            (fold for fold in folds if fold.fold_kind is FoldKind.OUTER),
            key=lambda item: item.ordinal,
        )
    )
    if len(outer) != expected_fold_count:
        raise MetricInputError("outer-fold count does not match the frozen policy")
    owned: set[str] = set()
    result: list[tuple[FoldRecord, tuple[SyntheticSample, ...]]] = []
    for fold in outer:
        if not fold.test_sample_ids:
            raise MetricInputError("outer folds require OOS test rows")
        group: list[SyntheticSample] = []
        for sample_id in fold.test_sample_ids:
            if sample_id not in sample_by_id or sample_id in owned:
                raise MetricInputError("outer-fold OOS ownership is missing or duplicated")
            owned.add(sample_id)
            group.append(sample_by_id[sample_id])
        result.append((fold, tuple(group)))
    if owned != sample_by_id.keys():
        raise MetricInputError("outer folds must own every OOS sample exactly once")
    return tuple(result)


def _append_series_metrics(
    metrics: list[MetricRecord],
    policy: FrozenEvaluationPolicy,
    gross: _SeriesStatistics,
    net: _SeriesStatistics,
    *,
    population: str,
    exclusions: tuple[str, ...],
    observation_count: int,
) -> None:
    inputs: dict[str, MetricInputValue] = {"observation_count": observation_count}
    denominator = "all chronological synthetic OOS observations with explicit returns"
    values = (
        ("gross_pnl", gross.aggregate_return, "decimal_return_sum", "phase5-return-sum-v1"),
        ("net_pnl", net.aggregate_return, "decimal_return_sum", "phase5-return-sum-v1"),
        ("gross_sharpe", gross.sharpe, "ratio", "phase5-sample-sharpe-v1"),
        ("net_sharpe", net.sharpe, "ratio", "phase5-sample-sharpe-v1"),
        ("gross_sortino", gross.sortino, "ratio", "phase5-sortino-zero-mar-v1"),
        ("net_sortino", net.sortino, "ratio", "phase5-sortino-zero-mar-v1"),
        ("gross_calmar", gross.calmar, "ratio", "phase5-calmar-arithmetic-v1"),
        ("net_calmar", net.calmar, "ratio", "phase5-calmar-arithmetic-v1"),
        (
            "gross_annualized_return",
            gross.annualized_return,
            "decimal_return_per_year",
            "phase5-arithmetic-annualized-return-v1",
        ),
        (
            "net_annualized_return",
            net.annualized_return,
            "decimal_return_per_year",
            "phase5-arithmetic-annualized-return-v1",
        ),
        (
            "gross_annualized_volatility",
            gross.annualized_volatility,
            "decimal_volatility_per_year",
            "phase5-sample-volatility-v1",
        ),
        (
            "net_annualized_volatility",
            net.annualized_volatility,
            "decimal_volatility_per_year",
            "phase5-sample-volatility-v1",
        ),
        (
            "gross_maximum_drawdown",
            gross.maximum_drawdown,
            "decimal_fraction",
            "phase5-compounded-maximum-drawdown-v1",
        ),
        (
            "net_maximum_drawdown",
            net.maximum_drawdown,
            "decimal_fraction",
            "phase5-compounded-maximum-drawdown-v1",
        ),
        (
            "gross_maximum_drawdown_duration",
            Decimal(gross.maximum_drawdown_duration),
            "observation_count",
            "phase5-drawdown-duration-observations-v1",
        ),
        (
            "net_maximum_drawdown_duration",
            Decimal(net.maximum_drawdown_duration),
            "observation_count",
            "phase5-drawdown-duration-observations-v1",
        ),
        ("gross_hit_ratio", gross.hit_ratio, "decimal_fraction", "phase5-positive-hit-ratio-v1"),
        ("net_hit_ratio", net.hit_ratio, "decimal_fraction", "phase5-positive-hit-ratio-v1"),
        (
            "gross_average_win",
            gross.average_win,
            "decimal_return_per_observation",
            "phase5-conditional-mean-return-v1",
        ),
        (
            "gross_average_loss",
            gross.average_loss,
            "decimal_return_per_observation",
            "phase5-conditional-mean-return-v1",
        ),
        (
            "net_average_win",
            net.average_win,
            "decimal_return_per_observation",
            "phase5-conditional-mean-return-v1",
        ),
        (
            "net_average_loss",
            net.average_loss,
            "decimal_return_per_observation",
            "phase5-conditional-mean-return-v1",
        ),
        (
            "gross_autocorrelation_lag1",
            gross.lag1_autocorrelation,
            "correlation",
            "phase5-pearson-lag1-autocorrelation-v1",
        ),
        (
            "net_autocorrelation_lag1",
            net.lag1_autocorrelation,
            "correlation",
            "phase5-pearson-lag1-autocorrelation-v1",
        ),
    )
    for metric_id, value, units, formula in values:
        metrics.append(
            _metric(
                policy,
                metric_id=metric_id,
                formula_version=formula,
                value=value,
                units=units,
                population=population,
                exclusions=exclusions,
                denominator=denominator,
                inputs=dict(inputs),
            )
        )


def _stress_inputs(
    policy: FrozenEvaluationPolicy,
    scenario: CostScenario,
) -> dict[str, MetricInputValue]:
    result: dict[str, MetricInputValue] = {"scenario": scenario.value}
    if scenario is not CostScenario.BASELINE:
        result.update(
            {
                "all_cost_multiplier": policy.stress.all_cost_multiplier,
                "spread_multiplier": policy.stress.spread_multiplier,
                "volatility_multiplier": policy.stress.volatility_multiplier,
                "adv_multiplier": policy.stress.adv_multiplier,
                "impact_coefficient_multiplier": policy.stress.impact_coefficient_multiplier,
                "latency_multiplier": policy.stress.latency_multiplier,
                "borrow_multiplier": policy.stress.borrow_multiplier,
            }
        )
    return result


def _append_regime_dimension(
    metrics: list[MetricRecord],
    policy: FrozenEvaluationPolicy,
    *,
    dimension: str,
    groups: dict[str, list[SyntheticSample]],
    baseline_by_sample: dict[str, CostLedgerEntry],
    population: str,
    exclusions: tuple[str, ...],
    definition_inputs: dict[str, MetricInputValue],
) -> None:
    for group_id, group_list in sorted(groups.items()):
        group = tuple(group_list)
        group_costs = tuple(baseline_by_sample[item.sample_id] for item in group)
        inputs: dict[str, MetricInputValue] = {
            "dimension": dimension,
            "group_id": group_id,
            "observation_count": len(group),
            **definition_inputs,
        }
        values = (
            (
                "pnl",
                "gross",
                sum((item.gross_return for item in group_costs), Decimal("0")),
            ),
            ("pnl", "net", sum((item.net_return for item in group_costs), Decimal("0"))),
            ("turnover", "mean", _mean(tuple(item.turnover for item in group))),
            (
                "participation",
                "mean",
                _mean(tuple(item.participation_rate for item in group_costs)),
            ),
            (
                "capacity",
                "breach_rate",
                Decimal(sum(item.capacity_breached for item in group_costs))
                / Decimal(len(group_costs)),
            ),
        )
        for category, label, value in values:
            units = (
                "decimal_return_sum"
                if category == "pnl"
                else "decimal_turnover_per_observation"
                if category == "turnover"
                else "decimal_fraction"
            )
            metrics.append(
                _metric(
                    policy,
                    metric_id=f"{category}:{dimension}:{group_id}:{label}",
                    formula_version="phase5-regime-observation-weighted-v1",
                    value=value,
                    units=units,
                    population=population,
                    exclusions=exclusions,
                    denominator=("row-level OOS observations in this predeclared reporting group"),
                    inputs=dict(inputs),
                )
            )


def build_evaluation_metrics(
    *,
    samples: tuple[SyntheticSample, ...],
    folds: tuple[FoldRecord, ...],
    cost_ledger: tuple[CostLedgerEntry, ...],
    scenario_summaries: tuple[CostScenarioSummary, ...],
    policy: FrozenEvaluationPolicy,
    diagnostics: EvaluationMetricDiagnostics,
) -> tuple[MetricRecord, ...]:
    """Return immutable, fully described metrics for deterministic synthetic OOS rows."""

    if len(samples) < 3:
        raise MetricInputError("metrics require at least three synthetic OOS samples")
    if len({sample.sample_id for sample in samples}) != len(samples):
        raise MetricInputError("OOS sample identities must be unique")
    ordered = tuple(sorted(samples, key=lambda item: (item.decision_time_utc, item.sample_id)))
    if ordered != samples:
        raise MetricInputError("OOS samples must be supplied in chronological order")
    actual_missing_return_count = sum(
        sample.return_status is ResearchReturnStatus.MISSING for sample in ordered
    )
    actual_no_trade_count = sum(
        sample.return_status is ResearchReturnStatus.NO_TRADE for sample in ordered
    )
    if diagnostics.missing_return_count != actual_missing_return_count:
        raise MetricInputError("missing-return diagnostic count disagrees with OOS rows")
    if diagnostics.no_trade_count != actual_no_trade_count:
        raise MetricInputError("no-trade diagnostic count disagrees with OOS rows")
    dsr_inputs = _validated_inputs("DSR", diagnostics.dsr_inputs, DSR_REQUIRED_INPUTS)
    pbo_inputs = _validated_inputs("PBO", diagnostics.pbo_inputs, PBO_REQUIRED_INPUTS)
    if dsr_inputs["sharpe_variance"] != diagnostics.sharpe_variance:
        raise MetricInputError("DSR Sharpe variance disagrees with V_SR")
    if dsr_inputs["effective_trials"] != diagnostics.effective_trial_count:
        raise MetricInputError("DSR effective trials disagree with N_eff")

    indexed_costs, summaries = _validate_and_index_costs(
        ordered,
        cost_ledger,
        scenario_summaries,
        policy,
    )
    fold_groups = _outer_fold_groups(
        ordered,
        folds,
        policy.walk_forward.outer_fold_count,
    )
    baseline_entries = tuple(
        indexed_costs[(CostScenario.BASELINE, sample.sample_id)] for sample in ordered
    )
    baseline_by_sample = {entry.sample_id: entry for entry in baseline_entries}
    gross_returns = tuple(entry.gross_return for entry in baseline_entries)
    net_returns = tuple(entry.net_return for entry in baseline_entries)
    gross = _series_statistics(gross_returns, policy.selection.annualization_factor)
    net = _series_statistics(net_returns, policy.selection.annualization_factor)
    population = "deterministic synthetic outer-fold OOS observations"
    exclusions = diagnostics.exclusions
    metrics: list[MetricRecord] = []
    _append_series_metrics(
        metrics,
        policy,
        gross,
        net,
        population=population,
        exclusions=exclusions,
        observation_count=len(ordered),
    )

    count = Decimal(len(ordered))
    turnover = tuple(sample.turnover for sample in ordered)
    gross_exposure = tuple(sample.gross_exposure for sample in ordered)
    net_exposure = tuple(sample.net_exposure for sample in ordered)
    sector_exposure = tuple(sample.sector_exposure for sample in ordered)
    notionals = tuple(
        sample.research_allocation_units * sample.reference_price for sample in ordered
    )
    total_notional = sum(notionals, Decimal("0"))
    if total_notional <= 0:
        raise MetricInputError("allocation concentration requires positive synthetic notional")
    concentration = sum(((notional / total_notional) ** 2 for notional in notionals), Decimal("0"))
    participations = tuple(entry.participation_rate for entry in baseline_entries)
    capacity_breaches = sum(entry.capacity_breached for entry in baseline_entries)
    scalar_metrics = (
        ("turnover_total", sum(turnover, Decimal("0")), "decimal_turnover_sum"),
        ("turnover_mean", _mean(turnover), "decimal_turnover_per_observation"),
        ("gross_exposure_mean", _mean(gross_exposure), "decimal_exposure"),
        ("gross_exposure_max", max(gross_exposure), "decimal_exposure"),
        ("net_exposure_mean", _mean(net_exposure), "decimal_exposure"),
        (
            "net_absolute_exposure_max",
            max(abs(value) for value in net_exposure),
            "decimal_exposure",
        ),
        ("sector_exposure_mean", _mean(sector_exposure), "decimal_exposure"),
        ("sector_exposure_max", max(sector_exposure), "decimal_exposure"),
        ("observation_allocation_concentration_hhi", concentration, "decimal_hhi"),
        ("participation_mean", _mean(participations), "decimal_fraction"),
        ("participation_max", max(participations), "decimal_fraction"),
        (
            "capacity_breach_rate",
            Decimal(capacity_breaches) / count,
            "decimal_fraction",
        ),
    )
    for metric_id, value, units in scalar_metrics:
        metrics.append(
            _metric(
                policy,
                metric_id=metric_id,
                formula_version="phase5-observation-weighted-aggregate-v1",
                value=value,
                units=units,
                population=population,
                exclusions=exclusions,
                denominator="individual synthetic OOS observations, never group-level ratios",
                inputs={
                    "observation_count": len(ordered),
                    "baseline_max_participation": policy.costs.baseline_max_participation,
                },
            )
        )

    for fold, group in fold_groups:
        group_ids = {sample.sample_id for sample in group}
        net_group = tuple(
            entry.net_return for entry in baseline_entries if entry.sample_id in group_ids
        )
        for label, value in (
            (
                "gross",
                sum(
                    (baseline_by_sample[sample.sample_id].gross_return for sample in group),
                    Decimal("0"),
                ),
            ),
            ("net", sum(net_group, Decimal("0"))),
        ):
            metrics.append(
                _metric(
                    policy,
                    metric_id=f"pnl:outer_fold:{fold.ordinal}:{label}",
                    formula_version="phase5-group-return-sum-v1",
                    value=value,
                    units="decimal_return_sum",
                    population=population,
                    exclusions=exclusions,
                    denominator="all OOS observations owned by this exact outer fold",
                    inputs={
                        "fold_id": str(fold.fold_id),
                        "fold_ordinal": fold.ordinal,
                        "observation_count": len(group),
                    },
                )
            )

    calendar_groups: dict[str, list[SyntheticSample]] = defaultdict(list)
    regime_groups: dict[str, list[SyntheticSample]] = defaultdict(list)
    volatility_groups: dict[str, list[SyntheticSample]] = defaultdict(list)
    rate_groups: dict[str, list[SyntheticSample]] = defaultdict(list)
    crisis_groups: dict[str, list[SyntheticSample]] = defaultdict(list)
    predeclared_crises = set(policy.regimes.crisis_windows)
    for sample in ordered:
        calendar_groups[sample.decision_time_utc.strftime("%Y-%m")].append(sample)
        regime_groups[sample.regime_id].append(sample)
        volatility_band = (
            "low" if sample.daily_volatility < policy.regimes.volatility_cut else "high"
        )
        volatility_groups[volatility_band].append(sample)
        if sample.rate_available_at_utc > sample.decision_time_utc:
            raise MetricInputError("rate-regime reporting requires vintage-aware availability")
        rate_direction = (
            "rising"
            if sample.rate_change > policy.regimes.rate_cut
            else "falling"
            if sample.rate_change < policy.regimes.rate_cut
            else "flat"
        )
        rate_groups[rate_direction].append(sample)
        unknown_crises = set(sample.crisis_window_ids) - predeclared_crises
        if unknown_crises:
            raise MetricInputError("OOS rows contain an undeclared crisis-window identity")
        for crisis_window_id in sample.crisis_window_ids:
            crisis_groups[crisis_window_id].append(sample)
    for period, group_list in sorted(calendar_groups.items()):
        group = tuple(group_list)
        for label, value in (
            (
                "gross",
                sum(
                    (baseline_by_sample[item.sample_id].gross_return for item in group),
                    Decimal("0"),
                ),
            ),
            (
                "net",
                sum(
                    (baseline_by_sample[item.sample_id].net_return for item in group),
                    Decimal("0"),
                ),
            ),
        ):
            metrics.append(
                _metric(
                    policy,
                    metric_id=f"pnl:calendar_month:{period}:{label}",
                    formula_version="phase5-group-return-sum-v1",
                    value=value,
                    units="decimal_return_sum",
                    population=population,
                    exclusions=exclusions,
                    denominator="all OOS observations in the UTC calendar month",
                    inputs={"calendar_month": period, "observation_count": len(group)},
                )
            )

    _append_regime_dimension(
        metrics,
        policy,
        dimension="regime",
        groups=regime_groups,
        baseline_by_sample=baseline_by_sample,
        population=population,
        exclusions=exclusions,
        definition_inputs={
            "dependency_rule": policy.regimes.dependency_rule,
            "predeclared_crisis_window_count": len(policy.regimes.crisis_windows),
        },
    )
    _append_regime_dimension(
        metrics,
        policy,
        dimension="volatility",
        groups=volatility_groups,
        baseline_by_sample=baseline_by_sample,
        population=population,
        exclusions=exclusions,
        definition_inputs={
            "volatility_definition": policy.regimes.volatility_definition,
            "volatility_cut": policy.regimes.volatility_cut,
            "cut_convention": "low_below_cut_high_at_or_above_cut",
        },
    )
    _append_regime_dimension(
        metrics,
        policy,
        dimension="rate",
        groups=rate_groups,
        baseline_by_sample=baseline_by_sample,
        population=population,
        exclusions=exclusions,
        definition_inputs={
            "rate_definition": policy.regimes.rate_definition,
            "rate_cut": policy.regimes.rate_cut,
            "availability_rule": "rate_available_at_or_before_decision",
        },
    )
    _append_regime_dimension(
        metrics,
        policy,
        dimension="crisis",
        groups=crisis_groups,
        baseline_by_sample=baseline_by_sample,
        population=population,
        exclusions=exclusions,
        definition_inputs={
            "predeclared_crisis_window_count": len(policy.regimes.crisis_windows),
            "window_selection": "frozen_before_results",
        },
    )

    component_totals: dict[tuple[CostScenario, str], Decimal] = {}
    for scenario in CostScenario:
        entries = tuple(indexed_costs[(scenario, sample.sample_id)] for sample in ordered)
        scenario_inputs = _stress_inputs(policy, scenario)
        scenario_inputs["observation_count"] = len(entries)
        for display_name, field_name in COST_COMPONENT_FIELDS:
            total = sum((getattr(entry, field_name) for entry in entries), Decimal("0"))
            component_totals[(scenario, display_name)] = total
            metrics.append(
                _metric(
                    policy,
                    metric_id=f"cost:{scenario.value}:{display_name}",
                    formula_version="phase5-component-cost-attribution-v1",
                    value=total,
                    units="decimal_return_sum",
                    population=population,
                    exclusions=exclusions,
                    denominator="all OOS cost-ledger rows in this scenario",
                    inputs={**scenario_inputs, "source_component": field_name},
                )
            )
        summary = summaries[scenario]
        outcomes = (
            ("gross_pnl", summary.aggregate_gross_return, "decimal_return_sum"),
            ("net_pnl", summary.aggregate_net_return, "decimal_return_sum"),
            (
                "annualized_net_return",
                summary.annualized_net_return,
                "decimal_return_per_year",
            ),
            ("net_sharpe", summary.net_sharpe, "ratio"),
            ("maximum_drawdown", summary.maximum_drawdown, "decimal_fraction"),
            ("capacity_breach_rate", summary.capacity_breach_rate, "decimal_fraction"),
            ("fill_rate", summary.fill_rate, "decimal_fraction"),
            ("rejection_rate", summary.rejection_rate, "decimal_fraction"),
            ("filled_quantity", summary.filled_quantity, "quantity_units"),
            ("rejected_quantity", summary.rejected_quantity, "quantity_units"),
        )
        for outcome, value, units in outcomes:
            metrics.append(
                _metric(
                    policy,
                    metric_id=f"scenario:{scenario.value}:{outcome}",
                    formula_version="phase5-cost-scenario-summary-v1",
                    value=value,
                    units=units,
                    population=population,
                    exclusions=exclusions,
                    denominator="all chronological OOS cost-ledger rows in this scenario",
                    inputs=dict(scenario_inputs),
                )
            )

    baseline_summary = summaries[CostScenario.BASELINE]
    for scenario in (CostScenario.ALL_COST_STRESS, CostScenario.LIQUIDITY_STRESS):
        summary = summaries[scenario]
        stress_values = {
            "commission_cost_delta": (
                component_totals[(scenario, "commission")]
                - component_totals[(CostScenario.BASELINE, "commission")]
            ),
            "spread_cost_delta": (
                component_totals[(scenario, "spread")]
                - component_totals[(CostScenario.BASELINE, "spread")]
            ),
            "impact_cost_delta": (
                component_totals[(scenario, "impact")]
                - component_totals[(CostScenario.BASELINE, "impact")]
            ),
            "delay_cost_delta": (
                component_totals[(scenario, "delay")]
                - component_totals[(CostScenario.BASELINE, "delay")]
            ),
            "borrow_cost_delta": (
                component_totals[(scenario, "borrow")]
                - component_totals[(CostScenario.BASELINE, "borrow")]
            ),
            "capacity_cost_delta": (
                component_totals[(scenario, "capacity")]
                - component_totals[(CostScenario.BASELINE, "capacity")]
            ),
            "total_cost_delta": (
                summary.aggregate_total_cost - baseline_summary.aggregate_total_cost
            ),
            "net_pnl_delta": summary.aggregate_net_return - baseline_summary.aggregate_net_return,
            "annualized_net_return_delta": (
                summary.annualized_net_return - baseline_summary.annualized_net_return
            ),
            "net_sharpe_delta": summary.net_sharpe - baseline_summary.net_sharpe,
            "maximum_drawdown_delta": (
                summary.maximum_drawdown - baseline_summary.maximum_drawdown
            ),
            "capacity_breach_rate_delta": (
                summary.capacity_breach_rate - baseline_summary.capacity_breach_rate
            ),
            "fill_rate_delta": summary.fill_rate - baseline_summary.fill_rate,
            "rejection_rate_delta": (summary.rejection_rate - baseline_summary.rejection_rate),
        }
        for outcome in STRESS_SENSITIVITY_OUTCOMES:
            units = (
                "ratio_difference"
                if outcome == "net_sharpe_delta"
                else "decimal_return_per_year"
                if outcome == "annualized_net_return_delta"
                else "decimal_fraction"
                if outcome
                in {
                    "maximum_drawdown_delta",
                    "capacity_breach_rate_delta",
                    "fill_rate_delta",
                    "rejection_rate_delta",
                }
                else "decimal_return_sum"
            )
            metrics.append(
                _metric(
                    policy,
                    metric_id=f"stress:{scenario.value}:{outcome}",
                    formula_version="phase5-stress-minus-baseline-v1",
                    value=stress_values[outcome],
                    units=units,
                    population=population,
                    exclusions=exclusions,
                    denominator="same frozen OOS allocation under stress minus baseline",
                    inputs={**_stress_inputs(policy, scenario), "observation_count": len(ordered)},
                )
            )

    diagnostic_values: tuple[
        tuple[str, Decimal, str, str, dict[str, MetricInputValue], str], ...
    ] = (
        (
            "trial:M_raw",
            Decimal(diagnostics.raw_trial_count),
            "trial_count",
            "phase5-complete-raw-trial-count-v1",
            {"failed_and_abandoned_included": "yes"},
            "all append-only trials that influenced selection",
        ),
        (
            "trial:N_eff",
            diagnostics.effective_trial_count,
            "effective_trial_count",
            policy.selection.effective_trial_method,
            {"raw_trial_count": diagnostics.raw_trial_count},
            "complete raw trial registry under the frozen dependence method",
        ),
        (
            "trial:V_SR",
            diagnostics.sharpe_variance,
            "sharpe_variance",
            "phase5-cross-trial-sample-variance-v1",
            {"raw_trial_count": diagnostics.raw_trial_count},
            "completed synchronized trial Sharpe estimates minus one",
        ),
        (
            "selection:dsr_probability",
            diagnostics.dsr_probability,
            "probability",
            "bailey-lopez-de-prado-dsr-2014-eq2-v1",
            dsr_inputs,
            "selected completed trial OOS return observations",
        ),
        (
            "selection:pbo_probability",
            diagnostics.pbo_probability,
            "probability",
            "bailey-et-al-cscv-2014-algorithm-2.3-v1",
            pbo_inputs,
            "all symmetric CSCV splits and synchronized completed configurations",
        ),
        (
            "sample:oos_count",
            Decimal(len(ordered)),
            "observation_count",
            "phase5-exact-row-count-v1",
            {"outer_fold_count": len(fold_groups)},
            "all exact outer-fold OOS sample identities",
        ),
        (
            "sample:independent_event_count",
            Decimal(len({sample.independent_event_id for sample in ordered})),
            "event_count",
            "phase5-distinct-independent-event-count-v1",
            {"observation_count": len(ordered)},
            "distinct predeclared independent-event identities in OOS",
        ),
        (
            "sample:missing_return_count",
            Decimal(diagnostics.missing_return_count),
            "observation_count",
            "phase5-missing-return-count-v1",
            {
                "expected_oos_count": len(ordered),
                "missing_return_policy": policy.sample_adequacy.missing_return_policy.value,
            },
            "all expected OOS outcomes before missing-return exclusion",
        ),
        (
            "sample:no_trade_count",
            Decimal(diagnostics.no_trade_count),
            "observation_count",
            "phase5-explicit-no-trade-count-v1",
            {
                "expected_oos_count": len(ordered),
                "no_trade_return_policy": policy.sample_adequacy.no_trade_return_policy.value,
            },
            "all expected OOS outcomes under the frozen no-trade policy",
        ),
    )
    for metric_id, value, units, formula, inputs, denominator in diagnostic_values:
        metrics.append(
            _metric(
                policy,
                metric_id=metric_id,
                formula_version=formula,
                value=value,
                units=units,
                population=population,
                exclusions=exclusions,
                denominator=denominator,
                inputs=dict(inputs),
            )
        )

    if not set(CORE_METRIC_IDS) <= {metric.metric_id for metric in metrics}:
        raise MetricInputError("required Phase 5 metric vocabulary is incomplete")
    return tuple(metrics)


__all__ = [
    "CORE_METRIC_IDS",
    "COST_COMPONENT_FIELDS",
    "DSR_REQUIRED_INPUTS",
    "PBO_REQUIRED_INPUTS",
    "SCENARIO_OUTCOMES",
    "STRESS_SENSITIVITY_OUTCOMES",
    "EvaluationMetricDiagnostics",
    "MetricInputError",
    "build_evaluation_metrics",
]
