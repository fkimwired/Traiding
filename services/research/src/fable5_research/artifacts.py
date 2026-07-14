"""Bind prepared Phase 6 research inputs to the unchanged Phase 5 report."""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Final, Literal

from fable5_backtester.contracts import (
    EvaluationReport,
    GateCode,
    GateOutcome,
    PromotionState,
    TrialStatus,
)
from fable5_data.contracts import AuthorizedMappingIdentity

from fable5_research.canonical import (
    PHASE6_ARTIFACT_HASH_DOMAIN,
    PHASE6_ATTEMPT_HASH_DOMAIN,
    PHASE6_FEATURE_LINEAGE_HASH_DOMAIN,
    PHASE6_REQUEST_HASH_DOMAIN,
    PHASE6_RUN_NAMESPACE,
    PHASE6_TRIAL_SET_HASH_DOMAIN,
    domain_sha256,
    identity,
)
from fable5_research.contracts import (
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
)
from fable5_research.phase5 import configuration_family, configuration_is_crash_failure
from fable5_research.preparation import prepare_research_pipeline
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
    crash_sample_ids: set[str] = set()
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
        crash_window = regime_id.startswith("crisis:")
        if crash_window:
            crash_sample_ids.update(sample_ids)
        regime_results.append(
            RegimeResult(
                regime_id=regime_id,
                observation_count=len(sample_ids),
                net_return=Decimal(str(net_return)),
                crash_window=crash_window,
            )
        )
    oos_returns = {
        item.sample_id: item.baseline_net_return
        for item in report.oos_ledger
        if item.baseline_net_return is not None
    }
    total_absolute_return = sum((abs(item) for item in oos_returns.values()), Decimal("0"))
    crash_absolute_return = sum(
        (abs(oos_returns[item]) for item in crash_sample_ids if item in oos_returns),
        Decimal("0"),
    )
    complete = (
        regime_gate.outcome is GateOutcome.PASS
        and bool(crash_sample_ids)
        and total_absolute_return > 0
    )
    concentration = crash_absolute_return / total_absolute_return if complete else None
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
        crash_evidence_complete=complete,
        crash_concentration=concentration,
        crash_concentration_limit=Decimal("0.50"),
    )


def _family_evidence(
    prepared: PreparedResearchPipeline,
    report: EvaluationReport,
) -> FamilyAEvidence | FamilyBEvidence | FamilyCEvidence:
    inputs = prepared.family_inputs
    comparison_ids = tuple(item.comparison_id for item in prepared.baseline_comparisons)
    if isinstance(inputs, PreparedFamilyAInputs):
        return FamilyAEvidence(
            universe=inputs.universe,
            train_only_sector_fits=inputs.train_only_sector_fits,
            cross_section_ranks=inputs.cross_section_ranks,
            frozen_feature_names=_A_FEATURE_NAMES,
            baseline_comparison_ids=comparison_ids,
            capacity=inputs.capacity,
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
    payload = {
        "artifact_schema_version": "phase6-research-artifact-v1",
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
        "snapshot_bundle_sha256": report.snapshot_bundle_sha256,
        "feature_rows": rows,
        "feature_lineage_sha256": feature_lineage_sha256,
        "scores": prepared.scores,
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
