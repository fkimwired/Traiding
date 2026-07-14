"""Phase 6 long/flat trial overlays using the frozen Phase 5 cost model.

The Phase 5 engine has one allocation footprint per sample and one genuine per-trial
allocation switch: ``NO_TRADE``.  This helper therefore supports only a fixed active
long footprint (weight one) or an exact flat footprint (weight zero).  Continuous and
negative weights fail closed instead of being projected onto incompatible economics.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from fable5_backtester.contracts import (
    CostLedgerEntry,
    CostPolicy,
    CostScenario,
    ResearchReturnStatus,
    StressPolicy,
    SyntheticSample,
)
from fable5_backtester.costs import build_cost_ledger

LONG_FLAT_ALLOCATION_RULE = "phase6-fixed-long-or-flat-v1"
ACTIVE_LONG_WEIGHT = Decimal("1")
NO_TRADE_WEIGHT = Decimal("0")
TRIAL_RETURN_QUANTUM = Decimal("0.000000000001")


class TrialCostBridgeError(ValueError):
    """The requested trial economics cannot be represented by the frozen engine."""


@dataclass(frozen=True, slots=True)
class LongFlatTrialCostResult:
    """Exact sample overlays and component-level Phase 5 cost entries for one trial."""

    samples: tuple[SyntheticSample, ...]
    cost_ledger: tuple[CostLedgerEntry, ...]

    def entries_for(self, scenario: CostScenario) -> tuple[CostLedgerEntry, ...]:
        return tuple(item for item in self.cost_ledger if item.scenario is scenario)


def _require_finite_decimal(value: Decimal, field_name: str) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise TrialCostBridgeError(f"{field_name} must be a finite Decimal")
    return value


def _require_active_long_template(sample: SyntheticSample) -> None:
    if sample.return_status is not ResearchReturnStatus.OBSERVED:
        raise TrialCostBridgeError("active long template must have observed return status")
    if sample.borrow_applicable:
        raise TrialCostBridgeError("fixed long-only trial templates cannot incur borrow")
    if (
        sample.research_allocation_units <= 0
        or sample.gross_exposure <= 0
        or sample.net_exposure <= 0
        or sample.sector_exposure <= 0
        or sample.turnover <= 0
    ):
        raise TrialCostBridgeError("active long template requires a positive allocation footprint")
    if sample.net_exposure != sample.gross_exposure:
        raise TrialCostBridgeError("active long template requires equal gross and net exposure")
    if sample.sector_exposure > sample.gross_exposure:
        raise TrialCostBridgeError("sector exposure cannot exceed active gross exposure")


def build_long_flat_overlay(
    base_sample: SyntheticSample,
    *,
    weight: Decimal,
    label_return: Decimal,
) -> SyntheticSample:
    """Return one validated active-long or exact no-trade Phase 5 sample overlay."""

    _require_active_long_template(base_sample)
    normalized_weight = _require_finite_decimal(weight, "weight")
    normalized_label = _require_finite_decimal(label_return, "label_return")
    if normalized_weight not in {NO_TRADE_WEIGHT, ACTIVE_LONG_WEIGHT}:
        raise TrialCostBridgeError("weight must be exactly zero or one")
    try:
        gross_return = (normalized_weight * normalized_label).quantize(TRIAL_RETURN_QUANTUM)
    except InvalidOperation as exc:
        raise TrialCostBridgeError("weighted label return is not quantizable") from exc

    updates: dict[str, object] = {
        "predicted_value": normalized_weight,
        "gross_return": gross_return,
    }
    if normalized_weight == NO_TRADE_WEIGHT:
        updates.update(
            {
                "return_status": ResearchReturnStatus.NO_TRADE,
                "research_allocation_units": Decimal("0"),
                "gross_exposure": Decimal("0"),
                "net_exposure": Decimal("0"),
                "sector_exposure": Decimal("0"),
                "turnover": Decimal("0"),
                "borrow_applicable": False,
            }
        )
    else:
        updates.update(
            {
                "return_status": ResearchReturnStatus.OBSERVED,
                "borrow_applicable": False,
            }
        )
    return SyntheticSample.model_validate(
        {
            **base_sample.model_dump(mode="python"),
            **updates,
        }
    )


def build_long_flat_trial_costs(
    base_samples: tuple[SyntheticSample, ...],
    *,
    weights: Mapping[str, Decimal],
    label_returns: Mapping[str, Decimal],
    cost_policy: CostPolicy,
    stress_policy: StressPolicy,
) -> LongFlatTrialCostResult:
    """Build deterministic overlays and all Phase 5 cost scenarios for one trial."""

    if not base_samples:
        raise TrialCostBridgeError("trial cost bridge requires at least one sample")
    sample_ids = tuple(item.sample_id for item in base_samples)
    if sample_ids != tuple(sorted(sample_ids)) or len(sample_ids) != len(set(sample_ids)):
        raise TrialCostBridgeError("base sample ids must be unique and canonically sorted")
    expected_ids = set(sample_ids)
    if set(weights) != expected_ids or set(label_returns) != expected_ids:
        raise TrialCostBridgeError("weights and label returns must cover every sample exactly")

    overlays = tuple(
        build_long_flat_overlay(
            sample,
            weight=weights[sample.sample_id],
            label_return=label_returns[sample.sample_id],
        )
        for sample in base_samples
    )
    ledger = build_cost_ledger(overlays, cost_policy, stress_policy)
    expected_keys = {(sample_id, scenario) for scenario in CostScenario for sample_id in sample_ids}
    actual_keys = {(item.sample_id, item.scenario) for item in ledger}
    if actual_keys != expected_keys or len(ledger) != len(expected_keys):
        raise TrialCostBridgeError("cost ledger must cover every sample and scenario exactly")
    return LongFlatTrialCostResult(samples=overlays, cost_ledger=ledger)


__all__ = [
    "ACTIVE_LONG_WEIGHT",
    "LONG_FLAT_ALLOCATION_RULE",
    "NO_TRADE_WEIGHT",
    "TRIAL_RETURN_QUANTUM",
    "LongFlatTrialCostResult",
    "TrialCostBridgeError",
    "build_long_flat_overlay",
    "build_long_flat_trial_costs",
]
