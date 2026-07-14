"""Bind prepared Phase 6 research inputs to the unchanged Phase 5 report."""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Final, Literal

from fable5_backtester.contracts import (
    CostLedgerEntry,
    CostScenario,
    EvaluationReport,
    GateCode,
    GateOutcome,
    PromotionState,
    TrialStatus,
)
from fable5_data.contracts import AuthorizedMappingIdentity, SnapshotBundle

from fable5_research.canonical import (
    PHASE6_ARTIFACT_HASH_DOMAIN,
    PHASE6_ATTEMPT_HASH_DOMAIN,
    PHASE6_FEATURE_LINEAGE_HASH_DOMAIN,
    PHASE6_REQUEST_HASH_DOMAIN,
    PHASE6_RUN_NAMESPACE,
    PHASE6_TRIAL_ALLOCATION_HASH_DOMAIN,
    PHASE6_TRIAL_COST_SET_HASH_DOMAIN,
    PHASE6_TRIAL_ECONOMICS_HASH_DOMAIN,
    PHASE6_TRIAL_SET_HASH_DOMAIN,
    domain_sha256,
    identity,
)
from fable5_research.contracts import (
    CapacityEvidence,
    FamilyAEvidence,
    FamilyBEvidence,
    FamilyCEvidence,
    Phase5EvaluationLink,
    PreparedFamilyAInputs,
    PreparedFamilyBInputs,
    PreparedFamilyCInputs,
    PreparedResearchPipeline,
    RegimeResult,
    ResearchAttempt,
    ResearchAttemptStatus,
    ResearchConfigurationId,
    ResearchRunArtifact,
    ResearchRunStatus,
    ResearchTrialEconomics,
    ResearchTrialSampleEconomics,
)
from fable5_research.phase5 import configuration_family, configuration_is_crash_failure
from fable5_research.preparation import prepare_research_pipeline
from fable5_research.reproduction import verify_prepared_pipeline_reproduction
from fable5_research.specification import build_specification

_AFeatureName = Literal[
    "liquidity",
    "momentum",
    "quality",
    "turnover",
    "value",
    "volatility",
]
_A_FEATURE_NAMES: Final[tuple[_AFeatureName, ...]] = (
    "liquidity",
    "momentum",
    "quality",
    "turnover",
    "value",
    "volatility",
)


def _attempts(report: EvaluationReport) -> tuple[ResearchAttempt, ...]:
    attempts: list[ResearchAttempt] = []
    for ordinal, trial in enumerate(report.trials, start=1):
        status = ResearchAttemptStatus(trial.status.value)
        failure_reason = trial.failure_reason
        if trial.status is TrialStatus.NO_RETURN and failure_reason is None:
            failure_reason = "Phase 5 trial retained no computable return series"
        content = {
            "ordinal": ordinal,
            "phase5_trial_id": trial.trial_id,
            "phase5_trial_key": trial.trial_key,
            "status": status,
            "configuration_sha256": trial.config_sha256,
            "failure_reason": failure_reason,
        }
        attempts.append(
            ResearchAttempt.model_validate(
                {
                    **content,
                    "attempt_sha256": domain_sha256(PHASE6_ATTEMPT_HASH_DOMAIN, content),
                }
            )
        )
    return tuple(attempts)


def _phase5_trial_set_sha256(report: EvaluationReport) -> str:
    trial_set = tuple(
        sorted(
            (
                (trial.trial_id, trial.trial_key, trial.status, trial.config_sha256)
                for trial in report.trials
            ),
            key=lambda item: (str(item[0]), str(item[1])),
        )
    )
    return domain_sha256(PHASE6_TRIAL_SET_HASH_DOMAIN, trial_set)


def _trial_economics(
    prepared: PreparedResearchPipeline,
    report: EvaluationReport,
) -> tuple[ResearchTrialEconomics, ...]:
    completed = {
        item.trial_key: item for item in report.trials if item.status is TrialStatus.COMPLETED
    }
    result: list[ResearchTrialEconomics] = []
    scenario_ordinal = {scenario: ordinal for ordinal, scenario in enumerate(CostScenario)}
    for output_set in prepared.model_output_sets:
        trial = completed.get(output_set.trial_key)
        if trial is None:
            raise ValueError("every prepared model output requires one completed Phase 5 trial")
        serialized = trial.configuration.get("phase6_trial_cost_ledger_json")
        configured_cost_set_sha256 = trial.configuration.get("phase6_trial_cost_set_sha256")
        if serialized is None or configured_cost_set_sha256 is None:
            raise ValueError("completed Phase 6 trials require exact component-cost evidence")
        decoded = json.loads(serialized)
        if not isinstance(decoded, list):
            raise ValueError("trial component-cost evidence must be a JSON array")
        entries = tuple(CostLedgerEntry.model_validate(item) for item in decoded)
        expected_cost_set_sha256 = domain_sha256(
            PHASE6_TRIAL_COST_SET_HASH_DOMAIN,
            tuple((item.sample_id, item.scenario, item.cost_entry_sha256) for item in entries),
        )
        if configured_cost_set_sha256 != expected_cost_set_sha256:
            raise ValueError("trial component-cost evidence does not match its frozen hash")
        entries_by_sample: dict[str, list[CostLedgerEntry]] = {}
        for entry in entries:
            entries_by_sample.setdefault(entry.sample_id, []).append(entry)
        cells = {item.sample_id: item for item in output_set.ledger_cells}
        if set(entries_by_sample) != set(cells):
            raise ValueError("trial costs must cover every research ledger cell exactly")
        sample_economics: list[ResearchTrialSampleEconomics] = []
        for ordinal, sample_id in enumerate(sorted(cells), start=1):
            cell = cells[sample_id]
            sample_entries = tuple(
                sorted(
                    entries_by_sample[sample_id], key=lambda item: scenario_ordinal[item.scenario]
                )
            )
            content = {
                "schema_version": "phase6-trial-sample-economics-v1",
                "ordinal": ordinal,
                "sample_id": sample_id,
                "model_output": cell.model_output,
                "synthetic_research_weight": cell.synthetic_research_weight,
                "return_status": cell.return_status,
                "synthetic_gross_return": cell.synthetic_gross_return,
                "cost_entries": sample_entries,
            }
            sample_economics.append(
                ResearchTrialSampleEconomics.model_validate(
                    {
                        **content,
                        "evidence_sha256": domain_sha256(
                            PHASE6_TRIAL_ALLOCATION_HASH_DOMAIN,
                            content,
                        ),
                    }
                )
            )
        economics_content = {
            "schema_version": "phase6-trial-economics-v1",
            "ordinal": output_set.ordinal,
            "trial_key": output_set.trial_key,
            "model_id": output_set.model_id,
            "output_set_sha256": output_set.output_set_sha256,
            "sample_economics": tuple(sample_economics),
            "cost_set_sha256": expected_cost_set_sha256,
        }
        result.append(
            ResearchTrialEconomics.model_validate(
                {
                    **economics_content,
                    "economics_sha256": domain_sha256(
                        PHASE6_TRIAL_ECONOMICS_HASH_DOMAIN,
                        economics_content,
                    ),
                }
            )
        )
    return tuple(result)


def _family_b_evidence(
    inputs: PreparedFamilyBInputs,
    report: EvaluationReport,
) -> FamilyBEvidence:
    regime_gate = next(
        (item for item in report.gates if item.gate_code is GateCode.REGIME),
        None,
    )
    if regime_gate is None:
        raise ValueError("Family B lacks the exact Phase 5 regime gate")
    serialized = regime_gate.results.get("regime_breakdowns_json")
    if not isinstance(serialized, str):
        raise ValueError("Family B regime evidence is not computable")
    decoded = json.loads(serialized)
    if not isinstance(decoded, list):
        raise ValueError("Family B regime evidence has an invalid shape")
    regime_results: list[RegimeResult] = []
    for raw in decoded:
        if not isinstance(raw, dict):
            raise ValueError("Family B regime evidence has an invalid row")
        regime_id = raw.get("regime")
        sample_ids = raw.get("sample_ids")
        net_return = raw.get("baseline_net_pnl")
        if (
            not isinstance(regime_id, str)
            or not isinstance(sample_ids, list)
            or not sample_ids
            or any(not isinstance(item, str) for item in sample_ids)
            or not isinstance(net_return, str | int | float)
        ):
            raise ValueError("Family B regime evidence is incomplete")
        if not regime_id.startswith("volatility:"):
            # The unchanged Phase 5 engine necessarily renders the explicit zero
            # compatibility projection as `rate:flat`. It is not observed evidence
            # and must not be promoted into the Phase 6 family artifact.
            continue
        regime_results.append(
            RegimeResult(
                regime_id=regime_id,
                observation_count=len(sample_ids),
                net_return=Decimal(str(net_return)),
                crash_window=False,
            )
        )
    if not regime_results:
        raise ValueError("Family B lacks source-derived volatility regime evidence")
    if regime_gate.outcome is not GateOutcome.RESEARCH_ONLY or not {
        "rate_regime_coverage_missing",
        "crisis_window_coverage_missing",
    }.issubset(regime_gate.reason_codes):
        raise ValueError("Family B missing regime inputs must remain research-only")
    return FamilyBEvidence(
        lag_windows=inputs.lag_windows,
        raw_nominal_bar_count=inputs.raw_nominal_bar_count,
        adjusted_return_observation_count=inputs.adjusted_return_observation_count,
        trend_strength_formula_id="raw-nominal-252-session-ols-trend-strength-v1",
        realized_volatility_formula_id="action-aware-252-session-realized-volatility-v1",
        drawdown_formula_id="raw-nominal-252-session-drawdown-v1",
        lifecycle=inputs.lifecycle,
        lifecycle_tests=inputs.lifecycle_tests,
        corporate_action_source_references=inputs.corporate_action_source_references,
        regime_results=tuple(regime_results),
        rate_evidence_available=False,
        rate_evidence_reason="rate_regime_source_unavailable",
        crisis_geometry_available=False,
        crisis_evidence_reason="crisis_window_geometry_unavailable",
        crash_evidence_complete=False,
        crash_concentration=None,
        crash_concentration_limit=None,
    )


def _family_evidence(
    prepared: PreparedResearchPipeline,
    report: EvaluationReport,
) -> FamilyAEvidence | FamilyBEvidence | FamilyCEvidence:
    inputs = prepared.family_inputs
    comparison_ids = tuple(item.comparison_id for item in prepared.baseline_comparisons)
    if isinstance(inputs, PreparedFamilyAInputs):
        baseline_costs = tuple(
            item for item in report.cost_ledger if item.scenario is CostScenario.BASELINE
        )
        active_costs = tuple(
            item for item in baseline_costs if item.return_status.value != "no_trade"
        )
        flat_costs = tuple(
            item for item in baseline_costs if item.return_status.value == "no_trade"
        )
        if not active_costs or any(item.participation_rate <= 0 for item in active_costs):
            raise ValueError("Family A lacks authoritative baseline capacity ledger evidence")
        if any(
            item.participation_rate != 0 or item.requested_quantity != 0 or item.total_cost != 0
            for item in flat_costs
        ):
            raise ValueError("Family A no-trade capacity evidence must have a zero footprint")
        participation = {item.participation_rate for item in active_costs}
        if participation != {inputs.capacity.adv_participation}:
            raise ValueError("Family A capacity participation differs from its Phase 5 ledger")
        authoritative_capacity = CapacityEvidence(
            turnover=inputs.capacity.turnover,
            adv_participation=next(iter(participation)),
            capacity_units=min(item.requested_quantity for item in active_costs),
            concentration=inputs.capacity.concentration,
            capacity_limit_breached=any(item.capacity_breached for item in baseline_costs),
        )
        return FamilyAEvidence(
            universe=inputs.universe,
            train_only_sector_fits=inputs.train_only_sector_fits,
            cross_section_ranks=inputs.cross_section_ranks,
            frozen_feature_names=_A_FEATURE_NAMES,
            baseline_comparison_ids=comparison_ids,
            capacity=authoritative_capacity,
        )
    if isinstance(inputs, PreparedFamilyBInputs):
        return _family_b_evidence(inputs, report)
    if isinstance(inputs, PreparedFamilyCInputs):
        return FamilyCEvidence(
            extractions=inputs.extractions,
            corroborations=inputs.corroborations,
            non_text_baseline=inputs.non_text_baseline,
            baseline_comparison_ids=comparison_ids,
            conventional_downstream_model_id="conventional-linear-text-overlay-v1",
            non_text_baseline_model_id="lagged-return-range-linear-baseline-v1",
        )
    raise ValueError("prepared family inputs have an unsupported type")


def build_research_artifact(
    *,
    configuration_id: ResearchConfigurationId,
    mapping: AuthorizedMappingIdentity,
    prepared: PreparedResearchPipeline,
    report: EvaluationReport,
    snapshots: tuple[SnapshotBundle, ...],
) -> ResearchRunArtifact:
    """Reuse exact prepared rows/scores and bind their hash to Phase 5 evidence."""

    family = configuration_family(configuration_id)
    if (
        mapping.canonical_family is not family
        or report.mapping_id != mapping.mapping_id
        or prepared.configuration_id is not configuration_id
        or prepared.family is not family
    ):
        raise ValueError("research configuration, mapping, prepared input, and report must agree")
    rows = prepared.feature_rows
    feature_lineage_sha256 = domain_sha256(
        PHASE6_FEATURE_LINEAGE_HASH_DOMAIN,
        tuple((item.row_id, item.row_sha256, item.source_lineage_sha256) for item in rows),
    )
    phase5_evaluation = Phase5EvaluationLink(
        policy_id=report.evaluation_policy_id,
        policy_version=report.evaluation_policy_version,
        policy_sha256=report.evaluation_policy_sha256,
        fixture_id=report.fixture_id,
        fixture_sha256=report.fixture_sha256,
        config_hash=report.config_hash,
        snapshot_bundle_sha256=report.snapshot_bundle_sha256,
        evaluation_report_id=report.artifact_id,
        evaluation_report_sha256=report.artifact_sha256,
        evaluation_outcome_id=None,
        promotion_state=report.promotion_state,
        gate_codes=tuple(item.gate_code for item in report.gates),
        raw_trial_count=report.raw_trial_count,
        effective_trial_count=report.effective_trial_count,
        phase5_trial_set_sha256=_phase5_trial_set_sha256(report),
    )
    request_payload = {
        "mapping_id": mapping.mapping_id,
        "mapping_version": mapping.mapping_version,
        "mapping_input_sha256": mapping.mapping_input_sha256,
        "snapshot_bundle_sha256": report.snapshot_bundle_sha256,
        "configuration_id": configuration_id,
        "configuration_sha256": report.config_hash,
        "specification_sha256": prepared.specification.specification_sha256,
        "code_version_git_sha": report.code_version_git_sha,
        "random_seed": report.random_seed,
        "pipeline_input_sha256": prepared.pipeline_input_sha256,
    }
    request_fingerprint = domain_sha256(PHASE6_REQUEST_HASH_DOMAIN, request_payload)
    reasons = set(report.reason_codes)
    if configuration_is_crash_failure(configuration_id):
        reasons.add("crash_regime_evidence_incomplete")
    if report.promotion_state is PromotionState.PASS_RESEARCH:
        reasons.add("research_gates_passed_not_paper_approval")
    reproduction_audit = verify_prepared_pipeline_reproduction(
        configuration_id,
        snapshots,
        prepared,
    )
    payload = {
        "artifact_schema_version": "phase6-research-artifact-v2",
        "request_fingerprint_sha256": request_fingerprint,
        "pipeline_input_sha256": prepared.pipeline_input_sha256,
        "configuration_id": configuration_id,
        "configuration_sha256": report.config_hash,
        "mapping_id": mapping.mapping_id,
        "mapping_version": mapping.mapping_version,
        "mapping_input_sha256": mapping.mapping_input_sha256,
        "family": family,
        "specification": prepared.specification,
        "snapshot_bindings": prepared.snapshot_bindings,
        "calendar_source_references": prepared.calendar_source_references,
        "regime_evidence": prepared.regime_evidence,
        "confirmation_interval": prepared.confirmation_interval,
        "boundary_exclusions": prepared.boundary_exclusions,
        "source_reproduction_audit": reproduction_audit,
        "snapshot_bundle_sha256": report.snapshot_bundle_sha256,
        "feature_rows": rows,
        "feature_lineage_sha256": feature_lineage_sha256,
        "scores": prepared.scores,
        "model_output_sets": prepared.model_output_sets,
        "trial_economics": _trial_economics(prepared, report),
        "attempts": _attempts(report),
        "baseline_comparisons": prepared.baseline_comparisons,
        "family_evidence": _family_evidence(prepared, report),
        "phase5_evaluation": phase5_evaluation,
        "code_version_git_sha": report.code_version_git_sha,
        "random_seed": report.random_seed,
        "status": ResearchRunStatus.COMPLETED,
        "reason_codes": tuple(sorted(reasons)),
        "warnings": tuple(
            dict.fromkeys(
                (
                    *report.warnings,
                    "Synthetic research only; no real performance or investment advice.",
                    "PASS_RESEARCH is not paper approval.",
                )
            )
        ),
        "synthetic": True,
        "no_real_performance_claimed": True,
        "pass_research_is_not_paper_approval": True,
        "paper_approval_granted": False,
        "disclaimer": "Synthetic research only; no real performance or investment advice.",
    }
    artifact_sha256 = domain_sha256(PHASE6_ARTIFACT_HASH_DOMAIN, payload)
    return ResearchRunArtifact.model_validate(
        {
            **payload,
            "run_id": identity(PHASE6_RUN_NAMESPACE, request_fingerprint),
            "artifact_sha256": artifact_sha256,
            "created_at_utc": report.created_at_utc,
        }
    )


__all__ = [
    "build_research_artifact",
    "build_specification",
    "prepare_research_pipeline",
]
