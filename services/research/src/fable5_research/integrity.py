"""Fail-closed reconciliation for the Phase 6 to Phase 5 research bridge.

The Phase 5 engine remains byte-frozen.  This module validates the richer Phase 6
feature, label, model-output, and confirmation graph both before and after that engine
runs.  It deliberately has no execution, allocation-decision, or approval semantics.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from uuid import UUID

from fable5_backtester.canonical import canonical_json_text
from fable5_backtester.contracts import (
    CostLedgerEntry,
    CostScenario,
    EvaluationReport,
    FoldKind,
    FrozenEvaluationPolicy,
    ResearchReturnStatus,
    SyntheticEvaluationFixture,
    TrialStatus,
)
from fable5_backtester.costs import build_cost_ledger
from fable5_mapping.models import CanonicalFamily
from pydantic import BaseModel

from fable5_research.canonical import PHASE6_TRIAL_COST_SET_HASH_DOMAIN, domain_sha256
from fable5_research.contracts import (
    PreparedFamilyAInputs,
    PreparedResearchPipeline,
    ResearchLedgerCell,
    ResearchModelOutputSet,
    ResearchSourceReference,
)
from fable5_research.specification import (
    FAMILY_B_COST_VOLATILITY_PROJECTION_ID,
    FAMILY_B_COST_VOLATILITY_QUANTUM,
    FAMILY_B_COST_VOLATILITY_QUANTUM_TEXT,
    FAMILY_B_TRANSACTION_COST_MODEL_ID,
)
from fable5_research.trial_costs import (
    build_long_flat_overlay,
    build_long_flat_trial_costs,
)


class Phase6IntegrityError(ValueError):
    """One stable fail-closed bridge error with an externally auditable reason code."""

    def __init__(self, reason_code: str) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code


def _source_key(value: ResearchSourceReference) -> tuple[str, str]:
    return str(value.capability), str(value.normalized_observation_id)


def _collect_source_keys(value: object) -> set[tuple[str, str]]:
    """Collect every exact Phase 4 reference from a nested immutable Phase 6 model."""

    if isinstance(value, ResearchSourceReference):
        return {_source_key(value)}
    if isinstance(value, BaseModel):
        result: set[tuple[str, str]] = set()
        for field_name in type(value).model_fields:
            result.update(_collect_source_keys(getattr(value, field_name)))
        return result
    if isinstance(value, Mapping):
        result = set()
        for item in value.values():
            result.update(_collect_source_keys(item))
        return result
    if isinstance(value, tuple | list | set | frozenset):
        result = set()
        for item in value:
            result.update(_collect_source_keys(item))
        return result
    return set()


def _decimal_map(encoded: str, reason_code: str) -> dict[str, Decimal]:
    try:
        decoded: object = json.loads(encoded)
        if not isinstance(decoded, dict):
            raise TypeError
        result = {
            key: Decimal(value)
            for key, value in decoded.items()
            if isinstance(key, str) and isinstance(value, str)
        }
    except (ArithmeticError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise Phase6IntegrityError(reason_code) from exc
    if (
        len(result) != len(decoded)
        or any(not item.is_finite() for item in result.values())
        or encoded != canonical_json_text(result)
    ):
        raise Phase6IntegrityError(reason_code)
    return result


def _status_map(encoded: str, reason_code: str) -> dict[str, ResearchReturnStatus]:
    try:
        decoded: object = json.loads(encoded)
        if not isinstance(decoded, dict):
            raise TypeError
        result = {
            key: ResearchReturnStatus(value)
            for key, value in decoded.items()
            if isinstance(key, str) and isinstance(value, str)
        }
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise Phase6IntegrityError(reason_code) from exc
    if len(result) != len(decoded) or encoded != canonical_json_text(result):
        raise Phase6IntegrityError(reason_code)
    return result


def _string_map(encoded: str, reason_code: str) -> dict[str, str]:
    try:
        decoded: object = json.loads(encoded)
        if not isinstance(decoded, dict):
            raise TypeError
        result = {
            key: value
            for key, value in decoded.items()
            if isinstance(key, str) and isinstance(value, str)
        }
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise Phase6IntegrityError(reason_code) from exc
    if len(result) != len(decoded) or encoded != canonical_json_text(result):
        raise Phase6IntegrityError(reason_code)
    return result


def _cost_ledger_entries(encoded: str, reason_code: str) -> tuple[CostLedgerEntry, ...]:
    try:
        decoded: object = json.loads(encoded)
        if not isinstance(decoded, list) or not decoded:
            raise TypeError
        result = tuple(CostLedgerEntry.model_validate(item) for item in decoded)
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise Phase6IntegrityError(reason_code) from exc
    if encoded != canonical_json_text(result):
        raise Phase6IntegrityError(reason_code)
    return result


def _cost_economics(entry: CostLedgerEntry) -> dict[str, object]:
    return entry.model_dump(
        mode="python",
        exclude={"cost_entry_id", "cost_entry_sha256", "ordinal"},
    )


def _is_exact_no_trade_cost(entry: CostLedgerEntry) -> bool:
    return (
        entry.return_status is ResearchReturnStatus.NO_TRADE
        and entry.fill_status == "no_trade"
        and not entry.capacity_breached
        and all(
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
    )


def _cells_by_sample(output_set: ResearchModelOutputSet) -> dict[str, ResearchLedgerCell]:
    return {item.sample_id: item for item in output_set.ledger_cells}


def _validate_confirmation_geometry(
    *,
    policy: FrozenEvaluationPolicy,
    fixture: SyntheticEvaluationFixture,
    prepared: PreparedResearchPipeline,
    report: EvaluationReport,
) -> tuple[set[str], set[str]]:
    start = policy.walk_forward.final_confirmation_start_utc
    end = policy.walk_forward.final_confirmation_end_utc
    confirmation = prepared.confirmation_interval
    if start != confirmation.interval_start_utc or end != confirmation.interval_end_utc:
        raise Phase6IntegrityError("phase6_final_confirmation_policy_mismatch")
    confirmation_ids = {confirmation.sample_id}
    boundary_purged_ids = {item.sample_id for item in prepared.boundary_exclusions}
    expected_fixture_ids = {row.sample_id for row in prepared.feature_rows} | confirmation_ids
    fixture_ids = {item.sample_id for item in fixture.samples}
    if fixture_ids != expected_fixture_ids:
        raise Phase6IntegrityError("phase6_confirmation_boundary_purge_mismatch")
    if any(row.label_t1_utc >= start for row in prepared.feature_rows):
        raise Phase6IntegrityError("phase6_research_label_overlaps_confirmation")
    confirmation_sample = next(
        (item for item in fixture.samples if item.sample_id == confirmation.sample_id),
        None,
    )
    if (
        confirmation_sample is None
        or confirmation_sample.decision_time_utc != start
        or confirmation_sample.label_t0_utc != start
        or confirmation_sample.label_t1_utc != end
        or confirmation_sample.return_status is not ResearchReturnStatus.NO_TRADE
        or confirmation_sample.gross_return != 0
        or confirmation_sample.predicted_value != 0
        or confirmation_sample.research_allocation_units != 0
        or confirmation_sample.gross_exposure != 0
        or confirmation_sample.net_exposure != 0
        or confirmation_sample.sector_exposure != 0
        or confirmation_sample.turnover != 0
        or confirmation_sample.borrow_applicable
    ):
        raise Phase6IntegrityError("phase6_confirmation_not_label_blind")

    forbidden_ids = confirmation_ids | boundary_purged_ids
    fold_ids = {
        sample_id
        for fold in report.folds
        for sample_id in (
            *fold.train_sample_ids,
            *fold.test_sample_ids,
            *fold.purged_sample_ids,
            *fold.embargoed_sample_ids,
        )
    }
    fit_ids = {sample_id for fit in report.preprocessing_fits for sample_id in fit.train_sample_ids}
    oos_ids = {item.sample_id for item in report.oos_ledger}
    if forbidden_ids & (fold_ids | fit_ids | oos_ids):
        raise Phase6IntegrityError("phase6_confirmation_entered_research_artifact")
    return confirmation_ids, boundary_purged_ids


def _validate_source_graph(
    *,
    fixture: SyntheticEvaluationFixture,
    prepared: PreparedResearchPipeline,
) -> None:
    prepared_keys = _collect_source_keys(prepared)
    declared_keys = {
        (str(item.key.capability), str(item.key.normalized_observation_id))
        for item in fixture.source_observation_expectations
    }
    sample_keys = {
        (str(key.capability), str(key.normalized_observation_id))
        for sample in fixture.samples
        for key in sample.source_observation_keys
    }
    scope_keys = {
        (str(key.capability), str(key.normalized_observation_id))
        for evidence in fixture.report_scope_source_evidence
        for key in evidence.source_observation_keys
    }
    if not prepared_keys.issubset(declared_keys):
        raise Phase6IntegrityError("phase6_prepared_source_missing_from_fixture")
    if scope_keys != prepared_keys - sample_keys:
        raise Phase6IntegrityError("phase6_report_scope_source_graph_mismatch")
    if declared_keys != sample_keys | scope_keys or sample_keys & scope_keys:
        raise Phase6IntegrityError("phase6_fixture_source_graph_not_exact")
    if not fixture.report_scope_source_evidence or any(
        item.prepared_pipeline_input_sha256 != prepared.pipeline_input_sha256
        for item in fixture.report_scope_source_evidence
    ):
        raise Phase6IntegrityError("phase6_report_scope_pipeline_hash_mismatch")


def _validate_regime_projections(
    *,
    fixture: SyntheticEvaluationFixture,
    prepared: PreparedResearchPipeline,
) -> None:
    evidence = fixture.phase6_regime_evidence
    if (
        evidence is None
        or evidence.prepared_pipeline_input_sha256 != prepared.pipeline_input_sha256
    ):
        raise Phase6IntegrityError("phase6_regime_evidence_missing")
    prepared_evidence = prepared.regime_evidence
    available = prepared_evidence.evidence_state == "available"
    if (
        evidence.rate_evidence_available is not available
        or evidence.crisis_geometry_available is not available
        or evidence.rate_definition_id
        != (prepared_evidence.rate_definition_id if available else None)
        or evidence.crisis_definition_id
        != (prepared_evidence.crisis_definition_id if available else None)
        or evidence.crisis_window_ids
        != tuple(item.crisis_window_id for item in prepared_evidence.crisis_windows)
    ):
        raise Phase6IntegrityError("phase6_regime_evidence_projection_mismatch")
    if available:
        for sample in fixture.samples:
            rates = tuple(
                item
                for item in prepared_evidence.rate_observations
                if item.released_at_utc <= sample.decision_time_utc
            )
            if not rates:
                raise Phase6IntegrityError("phase6_rate_evidence_unavailable_at_decision")
            rate = max(rates, key=lambda item: (item.released_at_utc, item.vintage_id))
            expected_crises = tuple(
                item.crisis_window_id
                for item in prepared_evidence.crisis_windows
                if item.window_start_utc <= sample.decision_time_utc <= item.window_end_utc
            )
            if (
                sample.rate_available_at_utc != rate.released_at_utc
                or sample.rate_change != rate.rate_change
                or sample.crisis_window_ids != expected_crises
            ):
                raise Phase6IntegrityError("phase6_observed_regime_projection_mismatch")
    elif any(
        sample.rate_change != 0
        or sample.rate_available_at_utc != sample.decision_time_utc
        or sample.crisis_window_ids
        for sample in fixture.samples
    ):
        raise Phase6IntegrityError("phase6_unavailable_regime_evidence_claimed")
    if prepared.family is CanonicalFamily.B_TIME_SERIES_MOMENTUM_REGIME:
        rows = {item.sample_id: item for item in prepared.feature_rows}
        for sample in fixture.samples:
            if sample.sample_id == prepared.confirmation_interval.sample_id:
                continue
            feature = next(
                (
                    item
                    for item in rows[sample.sample_id].features
                    if item.feature_name == "realized_volatility"
                ),
                None,
            )
            if (
                feature is None
                or feature.formula_id != "action-aware-252-session-realized-volatility-v1"
                or feature.raw_value <= 0
            ):
                raise Phase6IntegrityError("phase6_volatility_regime_source_mismatch")
            with localcontext() as decimal_context:
                decimal_context.prec = 80
                expected_cost_volatility = feature.raw_value.quantize(
                    FAMILY_B_COST_VOLATILITY_QUANTUM,
                    rounding=ROUND_HALF_EVEN,
                )
            if sample.daily_volatility != expected_cost_volatility:
                raise Phase6IntegrityError("phase6_volatility_regime_source_mismatch")


def _validate_capacity_projection(
    *,
    fixture: SyntheticEvaluationFixture,
    prepared: PreparedResearchPipeline,
    report: EvaluationReport,
) -> None:
    inputs = prepared.family_inputs
    if not isinstance(inputs, PreparedFamilyAInputs):
        return
    expected = inputs.capacity.adv_participation
    baseline = tuple(item for item in report.cost_ledger if item.scenario is CostScenario.BASELINE)
    selected_statuses = {item.sample_id: item.return_status for item in report.oos_ledger}
    fixture_by_id = {item.sample_id: item for item in fixture.samples}
    if (
        not baseline
        or len(selected_statuses) != len(report.oos_ledger)
        or len(baseline) != len(report.oos_ledger)
        or {item.sample_id for item in baseline} != set(selected_statuses)
        or any(sample_id not in fixture_by_id for sample_id in selected_statuses)
    ):
        raise Phase6IntegrityError("phase6_capacity_participation_ledger_mismatch")
    if any(
        status is not ResearchReturnStatus.NO_TRADE
        and fixture_by_id[sample_id].research_allocation_units
        / fixture_by_id[sample_id].daily_adv_units
        != expected
        for sample_id, status in selected_statuses.items()
    ):
        raise Phase6IntegrityError("phase6_capacity_participation_input_mismatch")
    for item in baseline:
        if item.return_status is not selected_statuses[item.sample_id]:
            raise Phase6IntegrityError("phase6_capacity_participation_ledger_mismatch")
        if item.return_status is ResearchReturnStatus.NO_TRADE:
            if not _is_exact_no_trade_cost(item):
                raise Phase6IntegrityError("phase6_capacity_flat_economics_mismatch")
        elif item.participation_rate != expected:
            raise Phase6IntegrityError("phase6_capacity_participation_ledger_mismatch")


def _validate_trial_and_oos_ledgers(
    *,
    policy: FrozenEvaluationPolicy,
    fixture: SyntheticEvaluationFixture,
    prepared: PreparedResearchPipeline,
    report: EvaluationReport,
    forbidden_ids: set[str],
) -> None:
    if (
        policy.selection.primary_selection_metric != "mean_net_return"
        or policy.selection.pbo_tie_policy != "reject_ties"
    ):
        raise Phase6IntegrityError("phase6_inner_selection_policy_mismatch")
    output_sets = {item.trial_key: item for item in prepared.model_output_sets}
    if len(output_sets) != len(prepared.model_output_sets):
        raise Phase6IntegrityError("phase6_trial_model_registry_mismatch")
    completed_records = tuple(
        item for item in report.trials if item.status is TrialStatus.COMPLETED
    )
    completed = {item.trial_key: item for item in completed_records}
    if len(completed) != len(completed_records) or set(completed) != set(output_sets):
        raise Phase6IntegrityError("phase6_trial_model_registry_mismatch")

    outer_folds = tuple(
        fold for fold in report.folds if fold.fold_kind in {FoldKind.OUTER, FoldKind.CPCV}
    )
    inner_ids = tuple(
        dict.fromkeys(
            sample_id
            for fold in report.folds
            if fold.fold_kind is FoldKind.INNER
            for sample_id in fold.test_sample_ids
        )
    )
    outer_ids = tuple(sample_id for fold in outer_folds for sample_id in fold.test_sample_ids)
    if forbidden_ids & (set(inner_ids) | set(outer_ids)):
        raise Phase6IntegrityError("phase6_confirmation_entered_trial_calendar")
    if tuple(item.sample_id for item in report.oos_ledger) != outer_ids:
        raise Phase6IntegrityError("phase6_oos_outer_calendar_mismatch")

    sample_by_id = {item.sample_id: item for item in fixture.samples}
    if any(sample_id not in sample_by_id for sample_id in (*inner_ids, *outer_ids)):
        raise Phase6IntegrityError("phase6_trial_calendar_lineage_mismatch")
    prepared_sample_ids = tuple(item.sample_id for item in prepared.feature_rows)
    if (
        prepared_sample_ids != tuple(sorted(prepared_sample_ids))
        or len(prepared_sample_ids) != len(set(prepared_sample_ids))
        or any(sample_id not in sample_by_id for sample_id in prepared_sample_ids)
    ):
        raise Phase6IntegrityError("phase6_trial_cost_sample_lineage_mismatch")
    base_research_samples = tuple(sample_by_id[sample_id] for sample_id in prepared_sample_ids)
    outer_timestamps = tuple(sample_by_id[sample_id].decision_time_utc for sample_id in outer_ids)
    label_sha256 = domain_sha256(
        "phase6-phase5-label-set-v2",
        tuple(
            (row.sample_id, row.label_value, row.label_t0_utc, row.label_t1_utc)
            for row in prepared.feature_rows
        ),
    )
    completed_by_id = {item.trial_id: item for item in completed_records}
    if len(completed_by_id) != len(completed_records):
        raise Phase6IntegrityError("phase6_trial_model_registry_mismatch")
    baseline_by_trial: dict[str, dict[str, CostLedgerEntry]] = {}
    costs_by_trial: dict[str, dict[tuple[str, CostScenario], CostLedgerEntry]] = {}
    for trial_key, output_set in output_sets.items():
        trial = completed[trial_key]
        ledger_set_sha256 = domain_sha256(
            "phase6-phase5-ledger-cell-set-v2",
            tuple((item.cell_id, item.cell_sha256) for item in output_set.ledger_cells),
        )
        expected_bindings = {
            "model": output_set.model_id,
            "variant": str(output_set.ordinal),
            "phase6_pipeline_input_sha256": prepared.pipeline_input_sha256,
            "phase6_model_output_sha256": output_set.model_output_sha256,
            "phase6_output_set_sha256": output_set.output_set_sha256,
            "phase6_label_sha256": label_sha256,
            "phase6_ledger_cell_set_sha256": ledger_set_sha256,
            "phase6_payoff_formula_id": "phase6-long-flat-weight-times-label-quantized-v1",
        }
        if prepared.family is CanonicalFamily.B_TIME_SERIES_MOMENTUM_REGIME:
            if (
                prepared.specification.transaction_cost_model_id
                != FAMILY_B_TRANSACTION_COST_MODEL_ID
            ):
                raise Phase6IntegrityError("phase6_cost_volatility_projection_mismatch")
            expected_bindings.update(
                {
                    "phase6_cost_volatility_projection_id": (
                        FAMILY_B_COST_VOLATILITY_PROJECTION_ID
                    ),
                    "phase6_cost_volatility_quantum": (FAMILY_B_COST_VOLATILITY_QUANTUM_TEXT),
                }
            )
        evidence_keys = {
            "phase6_allocation_rules_json",
            "phase6_trial_weights_json",
            "phase6_trial_cost_ledger_json",
            "phase6_trial_cost_set_sha256",
            "inner_validation_gross_returns_json",
            "inner_validation_return_statuses_json",
            "outer_gross_returns_json",
        }
        if set(trial.configuration) != set(expected_bindings) | evidence_keys or any(
            trial.configuration.get(key) != value for key, value in expected_bindings.items()
        ):
            raise Phase6IntegrityError("phase6_trial_configuration_lineage_mismatch")
        cells = _cells_by_sample(output_set)
        if set(cells) != set(prepared_sample_ids):
            raise Phase6IntegrityError("phase6_trial_cost_sample_lineage_mismatch")
        weights = _decimal_map(
            trial.configuration.get("phase6_trial_weights_json", ""),
            "phase6_trial_weight_evidence_invalid",
        )
        allocation_rules = _string_map(
            trial.configuration.get("phase6_allocation_rules_json", ""),
            "phase6_trial_allocation_rule_evidence_invalid",
        )
        if weights != {
            sample_id: cell.synthetic_research_weight for sample_id, cell in cells.items()
        } or allocation_rules != {
            sample_id: cell.allocation_rule_id for sample_id, cell in cells.items()
        }:
            raise Phase6IntegrityError("phase6_trial_allocation_lineage_mismatch")
        configured_costs = _cost_ledger_entries(
            trial.configuration.get("phase6_trial_cost_ledger_json", ""),
            "phase6_trial_cost_ledger_evidence_invalid",
        )
        configured_cost_set_sha256 = domain_sha256(
            PHASE6_TRIAL_COST_SET_HASH_DOMAIN,
            tuple(
                (item.sample_id, item.scenario, item.cost_entry_sha256) for item in configured_costs
            ),
        )
        if trial.configuration.get("phase6_trial_cost_set_sha256") != configured_cost_set_sha256:
            raise Phase6IntegrityError("phase6_trial_cost_set_hash_mismatch")
        try:
            expected_trial_costs = build_long_flat_trial_costs(
                base_research_samples,
                weights=weights,
                label_returns={sample_id: cell.label_value for sample_id, cell in cells.items()},
                cost_policy=policy.costs,
                stress_policy=policy.stress,
            ).cost_ledger
        except (ArithmeticError, ValueError) as exc:
            raise Phase6IntegrityError("phase6_trial_cost_reproduction_failed") from exc
        if configured_costs != expected_trial_costs:
            raise Phase6IntegrityError("phase6_trial_cost_component_mismatch")
        costs_by_key = {(item.sample_id, item.scenario): item for item in configured_costs}
        if len(costs_by_key) != len(configured_costs):
            raise Phase6IntegrityError("phase6_trial_cost_ledger_evidence_invalid")
        costs_by_trial[trial_key] = costs_by_key
        baseline_by_trial[trial_key] = {
            sample_id: costs_by_key[(sample_id, CostScenario.BASELINE)]
            for sample_id in prepared_sample_ids
        }
        inner = _decimal_map(
            trial.configuration.get("inner_validation_gross_returns_json", ""),
            "phase6_inner_return_evidence_invalid",
        )
        outer = _decimal_map(
            trial.configuration.get("outer_gross_returns_json", ""),
            "phase6_outer_return_evidence_invalid",
        )
        statuses = _status_map(
            trial.configuration.get("inner_validation_return_statuses_json", ""),
            "phase6_inner_return_status_evidence_invalid",
        )
        if (
            inner != {sample_id: cells[sample_id].synthetic_gross_return for sample_id in inner_ids}
            or outer
            != {sample_id: cells[sample_id].synthetic_gross_return for sample_id in outer_ids}
            or statuses != {sample_id: cells[sample_id].return_status for sample_id in inner_ids}
        ):
            raise Phase6IntegrityError("phase6_trial_return_cell_mismatch")
        expected_outer_statuses = tuple(cells[sample_id].return_status for sample_id in outer_ids)
        if (
            trial.return_timestamps_utc != outer_timestamps
            or trial.return_statuses != expected_outer_statuses
        ):
            raise Phase6IntegrityError("phase6_trial_calendar_lineage_mismatch")
        expected_net_returns = tuple(
            baseline_by_trial[trial_key][sample_id].net_return for sample_id in outer_ids
        )
        if trial.net_returns != expected_net_returns:
            raise Phase6IntegrityError("phase6_trial_net_return_lineage_mismatch")

    expected_winner_by_fold: dict[UUID, str] = {}
    selected_trial_by_sample: dict[str, str] = {}
    for outer_fold in outer_folds:
        inner_folds = tuple(
            fold
            for fold in report.folds
            if fold.fold_kind is FoldKind.INNER and fold.parent_fold_id == outer_fold.fold_id
        )
        if len(inner_folds) != policy.walk_forward.inner_fold_count:
            raise Phase6IntegrityError("phase6_inner_selection_geometry_mismatch")
        validation_ids = tuple(
            sample_id for fold in inner_folds for sample_id in fold.test_sample_ids
        )
        if not validation_ids or any(
            sample_id not in baseline_by_trial[trial_key]
            for trial_key in baseline_by_trial
            for sample_id in validation_ids
        ):
            raise Phase6IntegrityError("phase6_inner_selection_cost_evidence_missing")
        scores = {
            trial_key: sum(
                (returns[sample_id].net_return for sample_id in validation_ids),
                Decimal("0"),
            )
            / Decimal(len(validation_ids))
            for trial_key, returns in baseline_by_trial.items()
        }
        best_score = max(scores.values())
        winners = tuple(trial_key for trial_key, score in scores.items() if score == best_score)
        if len(winners) != 1:
            raise Phase6IntegrityError("phase6_inner_selection_not_unique")
        expected_winner_by_fold[outer_fold.fold_id] = winners[0]
        selected_trial_by_sample.update(
            {sample_id: winners[0] for sample_id in outer_fold.test_sample_ids}
        )

        fold_entries = tuple(
            item for item in report.oos_ledger if item.fold_id == outer_fold.fold_id
        )
        if tuple(item.sample_id for item in fold_entries) != outer_fold.test_sample_ids:
            raise Phase6IntegrityError("phase6_oos_outer_calendar_mismatch")
        if any(
            completed_by_id.get(item.trial_id) is None
            or completed_by_id[item.trial_id].trial_key != winners[0]
            for item in fold_entries
        ):
            raise Phase6IntegrityError("phase6_oos_selected_trial_selection_mismatch")

    try:
        selected_oos_samples = tuple(
            build_long_flat_overlay(
                sample_by_id[sample_id],
                weight=_cells_by_sample(output_sets[selected_trial_by_sample[sample_id]])[
                    sample_id
                ].synthetic_research_weight,
                label_return=_cells_by_sample(output_sets[selected_trial_by_sample[sample_id]])[
                    sample_id
                ].label_value,
            )
            for sample_id in outer_ids
        )
        expected_report_costs = build_cost_ledger(
            selected_oos_samples,
            policy.costs,
            policy.stress,
        )
    except (ArithmeticError, KeyError, ValueError) as exc:
        raise Phase6IntegrityError("phase6_oos_cost_reproduction_failed") from exc
    if tuple(report.cost_ledger) != expected_report_costs:
        raise Phase6IntegrityError("phase6_oos_component_cost_ledger_mismatch")
    report_cost_by_key = {(item.sample_id, item.scenario): item for item in report.cost_ledger}
    if len(report_cost_by_key) != len(report.cost_ledger):
        raise Phase6IntegrityError("phase6_oos_component_cost_ledger_mismatch")
    for sample_id, trial_key in selected_trial_by_sample.items():
        for scenario in CostScenario:
            report_cost = report_cost_by_key.get((sample_id, scenario))
            trial_cost = costs_by_trial[trial_key].get((sample_id, scenario))
            if (
                report_cost is None
                or trial_cost is None
                or _cost_economics(report_cost) != _cost_economics(trial_cost)
            ):
                raise Phase6IntegrityError("phase6_oos_selected_trial_cost_mismatch")
    report_baseline_cost = {
        sample_id: report_cost_by_key[(sample_id, CostScenario.BASELINE)] for sample_id in outer_ids
    }

    for entry in report.oos_ledger:
        selected_trial = completed_by_id.get(entry.trial_id)
        if selected_trial is None or selected_trial.trial_key not in output_sets:
            raise Phase6IntegrityError("phase6_oos_selected_trial_missing")
        if expected_winner_by_fold.get(entry.fold_id) != selected_trial.trial_key:
            raise Phase6IntegrityError("phase6_oos_selected_trial_selection_mismatch")
        cell = _cells_by_sample(output_sets[selected_trial.trial_key]).get(entry.sample_id)
        if (
            cell is None
            or entry.predicted_value != cell.model_output
            or entry.gross_return != cell.synthetic_gross_return
            or entry.return_status is not cell.return_status
        ):
            raise Phase6IntegrityError("phase6_oos_model_output_or_return_mismatch")
        cost = report_baseline_cost.get(entry.sample_id)
        if cost is None or entry.baseline_net_return != cost.net_return:
            raise Phase6IntegrityError("phase6_oos_cost_lineage_mismatch")
        if entry.return_status is ResearchReturnStatus.NO_TRADE and (
            entry.gross_return != 0
            or entry.baseline_net_return != 0
            or not _is_exact_no_trade_cost(cost)
        ):
            raise Phase6IntegrityError("phase6_oos_no_trade_economics_mismatch")


def validate_phase6_evaluation_bridge(
    *,
    policy: FrozenEvaluationPolicy,
    fixture: SyntheticEvaluationFixture,
    prepared: PreparedResearchPipeline,
    report: EvaluationReport,
) -> None:
    """Reconcile every richer Phase 6 cell with the unchanged Phase 5 report."""

    if (
        report.evaluation_policy_id != policy.policy_id
        or report.evaluation_policy_sha256 != policy.policy_sha256
        or report.fixture_id != fixture.fixture_id
        or report.fixture_sha256 != fixture.fixture_sha256
    ):
        raise Phase6IntegrityError("phase6_phase5_artifact_identity_mismatch")
    _validate_source_graph(fixture=fixture, prepared=prepared)
    confirmation_ids, boundary_ids = _validate_confirmation_geometry(
        policy=policy,
        fixture=fixture,
        prepared=prepared,
        report=report,
    )
    _validate_regime_projections(fixture=fixture, prepared=prepared)
    _validate_capacity_projection(fixture=fixture, prepared=prepared, report=report)
    _validate_trial_and_oos_ledgers(
        policy=policy,
        fixture=fixture,
        prepared=prepared,
        report=report,
        forbidden_ids=confirmation_ids | boundary_ids,
    )


__all__ = ["Phase6IntegrityError", "validate_phase6_evaluation_bridge"]
