"""Deterministic component-level research cost and stress calculations."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from math import sqrt

from fable5_backtester.canonical import (
    PHASE5_CONFIG_HASH_DOMAIN,
    PHASE5_COST_HASH_DOMAIN,
    PHASE5_COST_NAMESPACE,
    domain_sha256,
    identity,
)
from fable5_backtester.contracts import (
    CostLedgerEntry,
    CostPolicy,
    CostScenario,
    ResearchReturnStatus,
    StressPolicy,
    SyntheticSample,
)


class CostInputError(ValueError):
    """Required cost evidence is missing or invalid."""


@dataclass(frozen=True, slots=True)
class CostScenarioSummary:
    scenario: CostScenario
    allocation_input_sha256s: tuple[str, ...]
    aggregate_gross_return: Decimal
    aggregate_total_cost: Decimal
    aggregate_net_return: Decimal
    annualized_net_return: Decimal
    net_sharpe: Decimal
    maximum_drawdown: Decimal
    capacity_breach_rate: Decimal
    fill_rate: Decimal
    rejection_rate: Decimal
    requested_quantity: Decimal
    filled_quantity: Decimal
    rejected_quantity: Decimal


def _allocation_payload(sample: SyntheticSample) -> dict[str, object]:
    return {
        "sample_id": sample.sample_id,
        "research_allocation_units": sample.research_allocation_units,
        "reference_price": sample.reference_price,
        "return_status": sample.return_status,
        "gross_return": sample.gross_return,
        "borrow_applicable": sample.borrow_applicable,
        "hard_to_borrow_available": sample.hard_to_borrow_available,
    }


def _components(
    sample: SyntheticSample,
    scenario: CostScenario,
    stress: StressPolicy,
) -> tuple[Decimal, Decimal, Decimal, Decimal, Decimal, Decimal]:
    participation = sample.research_allocation_units / sample.daily_adv_units
    impact = (
        Decimal(str(sqrt(float(participation))))
        * sample.daily_volatility
        * sample.impact_coefficient
    )
    fee = sample.fee_rate
    spread = sample.half_spread_rate
    latency = sample.latency_rate
    borrow = sample.borrow_rate if sample.borrow_applicable else Decimal("0")
    if scenario is CostScenario.ALL_COST_STRESS:
        multiplier = stress.all_cost_multiplier
        return (
            fee * multiplier,
            spread * multiplier,
            impact * multiplier,
            latency * multiplier,
            borrow * multiplier,
            participation,
        )
    if scenario is CostScenario.LIQUIDITY_STRESS:
        stressed_participation = participation / stress.adv_multiplier
        stressed_impact = (
            Decimal(str(sqrt(float(stressed_participation))))
            * sample.daily_volatility
            * stress.volatility_multiplier
            * sample.impact_coefficient
            * stress.impact_coefficient_multiplier
        )
        return (
            fee,
            spread * stress.spread_multiplier,
            stressed_impact,
            latency * stress.latency_multiplier,
            borrow * stress.borrow_multiplier,
            stressed_participation,
        )
    return fee, spread, impact, latency, borrow, participation


def build_cost_ledger(
    samples: tuple[SyntheticSample, ...],
    cost_policy: CostPolicy,
    stress: StressPolicy,
) -> tuple[CostLedgerEntry, ...]:
    if not samples:
        raise CostInputError("cost evaluation requires synthetic ledger rows")
    entries: list[CostLedgerEntry] = []
    ordinal = 0
    for scenario in CostScenario:
        for sample in samples:
            if sample.return_status is ResearchReturnStatus.MISSING:
                raise CostInputError(f"missing return cannot be costed: {sample.sample_id}")
            if sample.gross_return is None:  # pragma: no cover - guarded by sample contract
                raise CostInputError(f"non-missing return lacks a value: {sample.sample_id}")
            allocation_hash = domain_sha256(PHASE5_CONFIG_HASH_DOMAIN, _allocation_payload(sample))
            if sample.return_status is ResearchReturnStatus.NO_TRADE:
                payload = {
                    "scenario": scenario,
                    "ordinal": ordinal,
                    "sample_id": sample.sample_id,
                    "allocation_input_sha256": allocation_hash,
                    "return_status": sample.return_status,
                    "requested_quantity": Decimal("0"),
                    "filled_quantity": Decimal("0"),
                    "rejected_quantity": Decimal("0"),
                    "unfilled_quantity": Decimal("0"),
                    "fill_status": "no_trade",
                    "hard_to_borrow_available": sample.hard_to_borrow_available,
                    "gross_return": Decimal("0"),
                    "fee_cost": Decimal("0"),
                    "spread_cost": Decimal("0"),
                    "impact_cost": Decimal("0"),
                    "latency_cost": Decimal("0"),
                    "borrow_cost": Decimal("0"),
                    "capacity_cost": Decimal("0"),
                    "total_cost": Decimal("0"),
                    "net_return": Decimal("0"),
                    "participation_rate": Decimal("0"),
                    "capacity_breached": False,
                }
                digest = domain_sha256(PHASE5_COST_HASH_DOMAIN, payload)
                entries.append(
                    CostLedgerEntry.model_validate(
                        {
                            **payload,
                            "cost_entry_id": identity(PHASE5_COST_NAMESPACE, digest),
                            "cost_entry_sha256": digest,
                        }
                    )
                )
                ordinal += 1
                continue
            if sample.borrow_applicable and not sample.hard_to_borrow_available:
                raise CostInputError(
                    f"hard-to-borrow state makes sample unavailable: {sample.sample_id}"
                )
            fee, spread, impact, latency, borrow, participation = _components(
                sample, scenario, stress
            )
            capacity_breached = participation > cost_policy.baseline_max_participation
            requested_quantity = sample.research_allocation_units
            filled_quantity = Decimal("0") if capacity_breached else requested_quantity
            unfilled_quantity = requested_quantity - filled_quantity
            fill_fraction = filled_quantity / requested_quantity
            executed_gross_return = sample.gross_return * fill_fraction
            fee *= fill_fraction
            spread *= fill_fraction
            impact *= fill_fraction
            latency *= fill_fraction
            borrow *= fill_fraction
            capacity_cost = Decimal("0")
            total = fee + spread + impact + latency + borrow + capacity_cost
            payload = {
                "scenario": scenario,
                "ordinal": ordinal,
                "sample_id": sample.sample_id,
                "allocation_input_sha256": allocation_hash,
                "return_status": sample.return_status,
                "requested_quantity": requested_quantity,
                "filled_quantity": filled_quantity,
                "rejected_quantity": unfilled_quantity,
                "unfilled_quantity": unfilled_quantity,
                "fill_status": "capacity_rejected" if capacity_breached else "filled",
                "hard_to_borrow_available": sample.hard_to_borrow_available,
                "gross_return": executed_gross_return,
                "fee_cost": fee,
                "spread_cost": spread,
                "impact_cost": impact,
                "latency_cost": latency,
                "borrow_cost": borrow,
                "capacity_cost": capacity_cost,
                "total_cost": total,
                "net_return": executed_gross_return - total,
                "participation_rate": participation,
                "capacity_breached": capacity_breached,
            }
            digest = domain_sha256(PHASE5_COST_HASH_DOMAIN, payload)
            entries.append(
                CostLedgerEntry.model_validate(
                    {
                        **payload,
                        "cost_entry_id": identity(PHASE5_COST_NAMESPACE, digest),
                        "cost_entry_sha256": digest,
                    }
                )
            )
            ordinal += 1
    return tuple(entries)


def _maximum_drawdown(returns: tuple[Decimal, ...]) -> Decimal:
    wealth = Decimal("1")
    peak = wealth
    maximum = Decimal("0")
    for value in returns:
        wealth *= Decimal("1") + value
        peak = max(peak, wealth)
        maximum = max(maximum, (peak - wealth) / peak)
    return maximum


def summarize_cost_scenario(
    entries: tuple[CostLedgerEntry, ...],
    scenario: CostScenario,
    annualization_factor: int,
) -> CostScenarioSummary:
    selected = tuple(item for item in entries if item.scenario is scenario)
    if len(selected) < 2:
        raise CostInputError("cost scenario requires at least two rows")
    returns = tuple(item.net_return for item in selected)
    count = Decimal(len(returns))
    mean = sum(returns, Decimal("0")) / count
    variance = sum((value - mean) ** 2 for value in returns) / Decimal(len(returns) - 1)
    if variance <= 0:
        raise CostInputError("cost scenario net Sharpe is uncomputable")
    sharpe = mean / variance.sqrt() * Decimal(annualization_factor).sqrt()
    requested_quantity = sum((item.requested_quantity for item in selected), Decimal("0"))
    filled_quantity = sum((item.filled_quantity for item in selected), Decimal("0"))
    rejected_quantity = sum((item.rejected_quantity for item in selected), Decimal("0"))
    traded = tuple(
        item for item in selected if item.return_status is not ResearchReturnStatus.NO_TRADE
    )
    if requested_quantity <= 0 or not traded:
        raise CostInputError("cost scenario requires at least one traded observation")
    return CostScenarioSummary(
        scenario=scenario,
        allocation_input_sha256s=tuple(item.allocation_input_sha256 for item in selected),
        aggregate_gross_return=sum((item.gross_return for item in selected), Decimal("0")),
        aggregate_total_cost=sum((item.total_cost for item in selected), Decimal("0")),
        aggregate_net_return=sum(returns, Decimal("0")),
        annualized_net_return=mean * Decimal(annualization_factor),
        net_sharpe=sharpe,
        maximum_drawdown=_maximum_drawdown(returns),
        capacity_breach_rate=(
            Decimal(sum(item.capacity_breached for item in traded)) / Decimal(len(traded))
        ),
        fill_rate=filled_quantity / requested_quantity,
        rejection_rate=rejected_quantity / requested_quantity,
        requested_quantity=requested_quantity,
        filled_quantity=filled_quantity,
        rejected_quantity=rejected_quantity,
    )


__all__ = [
    "CostInputError",
    "CostScenarioSummary",
    "build_cost_ledger",
    "summarize_cost_scenario",
]
