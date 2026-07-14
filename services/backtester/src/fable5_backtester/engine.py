"""Deterministic synthetic-only Phase 5 evaluation engine."""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from math import sqrt
from statistics import fmean, stdev
from uuid import UUID

from fable5_data.contracts import AuthorizedMappingIdentity, SnapshotBundle

from fable5_backtester.canonical import (
    PHASE5_ARTIFACT_HASH_DOMAIN,
    PHASE5_ARTIFACT_NAMESPACE,
    PHASE5_CONFIG_HASH_DOMAIN,
    PHASE5_GATE_HASH_DOMAIN,
    PHASE5_GATE_NAMESPACE,
    PHASE5_LEDGER_HASH_DOMAIN,
    PHASE5_LEDGER_NAMESPACE,
    PHASE5_REQUEST_HASH_DOMAIN,
    PHASE5_SNAPSHOT_BUNDLE_HASH_DOMAIN,
    PHASE5_TRIAL_HASH_DOMAIN,
    PHASE5_TRIAL_NAMESPACE,
    canonical_json_text,
    domain_sha256,
    identity,
)
from fable5_backtester.contracts import (
    CostScenario,
    EvaluationReport,
    FoldKind,
    FoldRecord,
    FrozenEvaluationPolicy,
    GateCode,
    GateOutcome,
    GateResult,
    LeakageCode,
    LeakageFindingEvidence,
    LeakageGateEvidence,
    MetricRecord,
    MissingReturnPolicy,
    NoTradeReturnPolicy,
    OosLedgerEntry,
    PreprocessingFitRecord,
    PreprocessingFitSampleValue,
    PromotionState,
    ResearchReturnStatus,
    SnapshotEvidence,
    SyntheticEvaluationFixture,
    SyntheticSample,
    SyntheticTrial,
    TrialRecord,
    TrialStatus,
)
from fable5_backtester.costs import CostInputError, build_cost_ledger, summarize_cost_scenario
from fable5_backtester.evaluation_geometry import build_evaluation_geometry
from fable5_backtester.leakage import evaluate_leakage, pit_blocking_sample_ids
from fable5_backtester.metrics import (
    EvaluationMetricDiagnostics,
    MetricInputError,
    build_evaluation_metrics,
)
from fable5_backtester.source_lineage import (
    SourceLineageInputError,
    SourceLineagePolicyError,
    resolve_source_lineage,
    sample_sha256,
)
from fable5_backtester.statistics import (
    DeflatedSharpeInputs,
    MissingStatisticPolicyError,
    PBOInputs,
    PBOSelectionMetric,
    PBOTiePolicy,
    StatisticInputError,
    compute_deflated_sharpe,
    compute_pbo,
    lag1_effective_sample_sensitivity,
)


class EvaluationEngineError(RuntimeError):
    """Base error for a Phase 5 evaluation that cannot safely complete."""


class EvaluationEngineBlocked(EvaluationEngineError):
    def __init__(self, state: PromotionState, reason_codes: tuple[str, ...]) -> None:
        super().__init__(", ".join(reason_codes))
        self.state = state
        self.reason_codes = reason_codes


@dataclass(frozen=True, slots=True)
class TrialAccounting:
    records: tuple[TrialRecord, ...]
    effective_count: float
    sharpe_variance: float
    completed_sharpes: tuple[float, ...]
    common_calendar: tuple[datetime, ...]


_INNER_VALIDATION_GROSS_RETURNS_KEY = "inner_validation_gross_returns_json"
_INNER_VALIDATION_RETURN_STATUSES_KEY = "inner_validation_return_statuses_json"
_OUTER_GROSS_RETURNS_KEY = "outer_gross_returns_json"
_PBO_RETURN_STATUS_MATRIX_HASH_DOMAIN = "phase5-pbo-return-status-matrix-v1"


_REPORT_HASH_EXCLUDED_FIELDS = {
    "artifact_id",
    "artifact_type",
    "artifact_schema_version",
    "artifact_sha256",
    "request_fingerprint_version",
    "effective_trial_method",
    "created_at_utc",
    "decision_time_utc",
    "fixture_version",
    "synthetic",
    "no_real_performance_claimed",
    "disclaimer",
    "pass_research_is_not_paper_approval",
}


def evaluation_request_payload_from_report(report: EvaluationReport) -> dict[str, object]:
    """Return the exact canonical preimage for a persisted run fingerprint/config hash."""

    return {
        "policy_id": report.evaluation_policy_id,
        "policy_version": report.evaluation_policy_version,
        "policy_sha256": report.evaluation_policy_sha256,
        "mapping_id": report.mapping_id,
        "mapping_version": report.mapping_version,
        "mapping_input_sha256": report.mapping_input_sha256,
        "snapshot_bundle_sha256": report.snapshot_bundle_sha256,
        "sample_lineage_sha256": report.sample_lineage_sha256,
        "fixture_id": report.fixture_id,
        "fixture_sha256": report.fixture_sha256,
        "code_version_git_sha": report.code_version_git_sha,
        "random_seed": report.random_seed,
    }


def evaluation_report_hash_payload(report: EvaluationReport) -> dict[str, object]:
    """Return the exact canonical preimage bound by ``artifact_sha256``."""

    return report.model_dump(mode="python", exclude=_REPORT_HASH_EXCLUDED_FIELDS)


def _decimal(value: float) -> Decimal:
    return Decimal(str(value))


def _validate_return_policy(policy: FrozenEvaluationPolicy) -> None:
    label = policy.label_specification
    adequacy = policy.sample_adequacy
    if (
        label.missing_return_policy is not MissingReturnPolicy.BLOCK
        or adequacy.missing_return_policy is not MissingReturnPolicy.BLOCK
        or label.no_trade_return_policy is not NoTradeReturnPolicy.EXPLICIT_ZERO
        or adequacy.no_trade_return_policy is not NoTradeReturnPolicy.EXPLICIT_ZERO
        or label.missing_return_policy is not adequacy.missing_return_policy
        or label.no_trade_return_policy is not adequacy.no_trade_return_policy
    ):
        raise EvaluationEngineBlocked(
            PromotionState.BLOCKED_MISSING_POLICY,
            ("return_policy_missing_or_mismatch",),
        )


def _required_return_value(
    status: ResearchReturnStatus,
    value: Decimal | None,
    *,
    reason_code: str,
) -> Decimal:
    if status is ResearchReturnStatus.MISSING or value is None:
        raise EvaluationEngineBlocked(
            PromotionState.BLOCKED_UNCOMPUTABLE,
            (reason_code,),
        )
    return value


def _sample_sharpe(values: tuple[float, ...]) -> float:
    if len(values) < 2:
        raise EvaluationEngineBlocked(
            PromotionState.BLOCKED_UNCOMPUTABLE,
            ("trial_return_series_too_short",),
        )
    deviation = stdev(values)
    if deviation <= 0:
        raise EvaluationEngineBlocked(
            PromotionState.BLOCKED_UNCOMPUTABLE,
            ("trial_sharpe_variance_zero",),
        )
    return fmean(values) / deviation


def _correlation(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    left_mean = fmean(left)
    right_mean = fmean(right)
    numerator = sum((x - left_mean) * (y - right_mean) for x, y in zip(left, right, strict=True))
    left_scale = sqrt(sum((value - left_mean) ** 2 for value in left))
    right_scale = sqrt(sum((value - right_mean) ** 2 for value in right))
    if left_scale == 0 or right_scale == 0:
        raise EvaluationEngineBlocked(
            PromotionState.BLOCKED_UNCOMPUTABLE,
            ("effective_trial_correlation_uncomputable",),
        )
    return numerator / (left_scale * right_scale)


def _trial_accounting(
    policy: FrozenEvaluationPolicy,
    fixture: SyntheticEvaluationFixture,
) -> TrialAccounting:
    if any(trial.status is TrialStatus.NO_RETURN for trial in fixture.trials):
        raise EvaluationEngineBlocked(
            PromotionState.BLOCKED_UNCOMPUTABLE,
            ("required_trial_return_missing",),
        )
    completed = tuple(trial for trial in fixture.trials if trial.status is TrialStatus.COMPLETED)
    if len(completed) < policy.sample_adequacy.min_synchronized_trials:
        raise EvaluationEngineBlocked(
            PromotionState.BLOCKED_UNCOMPUTABLE,
            ("insufficient_synchronized_trials",),
        )
    lengths = {len(trial.net_returns) for trial in completed}
    if len(lengths) != 1:
        raise EvaluationEngineBlocked(
            PromotionState.BLOCKED_UNCOMPUTABLE,
            ("trial_common_calendar_missing",),
        )
    calendars = {trial.return_timestamps_utc for trial in completed}
    if len(calendars) != 1:
        raise EvaluationEngineBlocked(
            PromotionState.BLOCKED_UNCOMPUTABLE,
            ("trial_common_calendar_mismatch",),
        )
    common_calendar = next(iter(calendars))
    completed_decimal_returns = tuple(
        tuple(
            _required_return_value(
                status,
                value,
                reason_code="required_trial_return_missing",
            )
            for status, value in zip(
                trial.return_statuses,
                trial.net_returns,
                strict=True,
            )
        )
        for trial in completed
    )
    completed_returns = tuple(
        tuple(float(value) for value in values) for values in completed_decimal_returns
    )
    sharpes = tuple(_sample_sharpe(values) for values in completed_returns)
    if len(set(sharpes)) < 2:
        raise EvaluationEngineBlocked(
            PromotionState.BLOCKED_UNCOMPUTABLE,
            ("cross_trial_sharpe_variance_zero",),
        )
    sharpe_variance = stdev(sharpes) ** 2
    correlations = tuple(
        _correlation(completed_returns[left], completed_returns[right])
        for left in range(len(completed_returns))
        for right in range(left + 1, len(completed_returns))
    )
    average_correlation = min(1.0, max(0.0, fmean(correlations)))
    completed_effective = average_correlation + (1.0 - average_correlation) * len(completed)
    incomplete_count = len(fixture.trials) - len(completed)
    effective_count = completed_effective + incomplete_count
    if effective_count <= 1:
        raise EvaluationEngineBlocked(
            PromotionState.BLOCKED_UNCOMPUTABLE,
            ("effective_trial_count_not_supported",),
        )
    target_effective_count = _decimal(effective_count)
    completed_contribution_total = target_effective_count - Decimal(incomplete_count)
    completed_contribution = completed_contribution_total / Decimal(len(completed))
    completed_contribution_assigned = Decimal("0")
    completed_seen = 0
    component_hashes = {
        "signal_specification_sha256": domain_sha256(
            PHASE5_CONFIG_HASH_DOMAIN,
            policy.signal_specification,
        ),
        "feature_specification_sha256": policy.feature_specification.content_sha256,
        "label_specification_sha256": policy.label_specification.content_sha256,
        "selection_policy_sha256": domain_sha256(
            PHASE5_CONFIG_HASH_DOMAIN,
            policy.selection,
        ),
        "cost_policy_sha256": domain_sha256(PHASE5_CONFIG_HASH_DOMAIN, policy.costs),
        "stress_policy_sha256": domain_sha256(PHASE5_CONFIG_HASH_DOMAIN, policy.stress),
        "risk_policy_sha256": domain_sha256(PHASE5_CONFIG_HASH_DOMAIN, policy.risk),
    }
    records: list[TrialRecord] = []
    key_to_id: dict[str, UUID] = {}
    for ordinal, trial in enumerate(fixture.trials):
        config_preimage = {
            "configuration": trial.configuration,
            "strategy_family": policy.strategy_family,
            "selection_scope": policy.selection_scope,
            **component_hashes,
        }
        config_hash = domain_sha256(PHASE5_CONFIG_HASH_DOMAIN, config_preimage)
        try:
            parent_trial_ids = tuple(key_to_id[key] for key in trial.parent_trial_keys)
        except KeyError as exc:
            raise EvaluationEngineBlocked(
                PromotionState.BLOCKED_UNCOMPUTABLE,
                ("trial_parent_lineage_missing_or_not_prior",),
            ) from exc
        if trial.status is TrialStatus.COMPLETED:
            completed_seen += 1
            trial_contribution = (
                completed_contribution_total - completed_contribution_assigned
                if completed_seen == len(completed)
                else completed_contribution
            )
            completed_contribution_assigned += trial_contribution
        else:
            trial_contribution = Decimal("1")
        payload = {
            "ordinal": ordinal,
            "trial_key": trial.trial_key,
            "config_sha256": config_hash,
            "config_preimage": config_preimage,
            "configuration": trial.configuration,
            "policy_sha256": policy.policy_sha256,
            "strategy_family": policy.strategy_family,
            "selection_scope": policy.selection_scope,
            **component_hashes,
            "status": trial.status,
            "counts_toward_raw": True,
            "effective_trial_contribution": trial_contribution,
            "selection_metric": policy.selection.primary_selection_metric,
            "sharpe_convention": "per_period_sample_standard_deviation_v1",
            "oos_return_state": (
                "complete_common_calendar" if trial.net_returns else trial.status.value
            ),
            "net_returns": trial.net_returns,
            "return_statuses": trial.return_statuses,
            "return_timestamps_utc": trial.return_timestamps_utc,
            "initiated_by": trial.initiated_by,
            "initiated_at_utc": trial.initiated_at_utc,
            "parent_trial_ids": parent_trial_ids,
            "failure_reason": trial.failure_reason,
        }
        digest = domain_sha256(PHASE5_TRIAL_HASH_DOMAIN, payload)
        trial_id = identity(PHASE5_TRIAL_NAMESPACE, digest)
        key_to_id[trial.trial_key] = trial_id
        records.append(
            TrialRecord.model_validate({**payload, "trial_id": trial_id, "trial_sha256": digest})
        )
    if policy.selection.primary_selection_metric != "mean_net_return":
        raise EvaluationEngineBlocked(
            PromotionState.BLOCKED_MISSING_POLICY,
            ("unsupported_primary_selection_metric",),
        )
    return TrialAccounting(
        records=tuple(records),
        effective_count=effective_count,
        sharpe_variance=sharpe_variance,
        completed_sharpes=sharpes,
        common_calendar=common_calendar,
    )


def _configuration_return_evidence(
    trial: SyntheticTrial,
    *,
    configuration_key: str,
    required_sample_ids: tuple[str, ...],
    reason_code: str,
) -> dict[str, Decimal]:
    encoded = trial.configuration.get(configuration_key)
    if encoded is None:
        raise EvaluationEngineBlocked(PromotionState.BLOCKED_UNCOMPUTABLE, (reason_code,))
    try:
        decoded: object = json.loads(encoded)
    except (json.JSONDecodeError, TypeError) as exc:
        raise EvaluationEngineBlocked(
            PromotionState.BLOCKED_UNCOMPUTABLE,
            (reason_code,),
        ) from exc
    if not isinstance(decoded, dict):
        raise EvaluationEngineBlocked(PromotionState.BLOCKED_UNCOMPUTABLE, (reason_code,))
    values: dict[str, Decimal] = {}
    try:
        for sample_id, value in decoded.items():
            if not isinstance(sample_id, str) or not isinstance(value, str):
                raise ValueError
            parsed = Decimal(value)
            if not parsed.is_finite():
                raise ValueError
            values[sample_id] = parsed
    except (ArithmeticError, ValueError) as exc:
        raise EvaluationEngineBlocked(
            PromotionState.BLOCKED_UNCOMPUTABLE,
            (reason_code,),
        ) from exc
    if set(values) != set(required_sample_ids):
        raise EvaluationEngineBlocked(PromotionState.BLOCKED_UNCOMPUTABLE, (reason_code,))
    return values


def _configuration_status_evidence(
    trial: SyntheticTrial,
    *,
    configuration_key: str,
    required_sample_ids: tuple[str, ...],
    reason_code: str,
) -> dict[str, ResearchReturnStatus]:
    encoded = trial.configuration.get(configuration_key)
    if encoded is None:
        raise EvaluationEngineBlocked(PromotionState.BLOCKED_UNCOMPUTABLE, (reason_code,))
    try:
        decoded: object = json.loads(encoded)
    except (json.JSONDecodeError, TypeError) as exc:
        raise EvaluationEngineBlocked(
            PromotionState.BLOCKED_UNCOMPUTABLE,
            (reason_code,),
        ) from exc
    if not isinstance(decoded, dict):
        raise EvaluationEngineBlocked(PromotionState.BLOCKED_UNCOMPUTABLE, (reason_code,))
    statuses: dict[str, ResearchReturnStatus] = {}
    try:
        for sample_id, value in decoded.items():
            if not isinstance(sample_id, str) or not isinstance(value, str):
                raise ValueError
            statuses[sample_id] = ResearchReturnStatus(value)
    except ValueError as exc:
        raise EvaluationEngineBlocked(
            PromotionState.BLOCKED_UNCOMPUTABLE,
            (reason_code,),
        ) from exc
    if set(statuses) != set(required_sample_ids):
        raise EvaluationEngineBlocked(PromotionState.BLOCKED_UNCOMPUTABLE, (reason_code,))
    return statuses


def _select_trials_from_inner_validation(
    *,
    policy: FrozenEvaluationPolicy,
    fixture: SyntheticEvaluationFixture,
    accounting: TrialAccounting,
    folds: tuple[FoldRecord, ...],
    outer_folds: tuple[FoldRecord, ...],
    baseline_cost_by_sample: Mapping[str, Decimal],
) -> tuple[dict[UUID, TrialRecord], tuple[dict[str, object], ...]]:
    if policy.selection.primary_selection_metric != "mean_net_return":
        raise EvaluationEngineBlocked(
            PromotionState.BLOCKED_MISSING_POLICY,
            ("unsupported_primary_selection_metric",),
        )
    completed_trials = tuple(
        trial for trial in fixture.trials if trial.status is TrialStatus.COMPLETED
    )
    records_by_key = {
        record.trial_key: record
        for record in accounting.records
        if record.status is TrialStatus.COMPLETED
    }
    required_inner_sample_ids = tuple(
        dict.fromkeys(
            sample_id
            for fold in folds
            if fold.fold_kind is FoldKind.INNER
            for sample_id in fold.test_sample_ids
        )
    )
    gross_evidence_by_key = {
        trial.trial_key: _configuration_return_evidence(
            trial,
            configuration_key=_INNER_VALIDATION_GROSS_RETURNS_KEY,
            required_sample_ids=required_inner_sample_ids,
            reason_code="inner_validation_return_evidence_missing_or_invalid",
        )
        for trial in completed_trials
    }
    status_evidence_by_key = {
        trial.trial_key: _configuration_status_evidence(
            trial,
            configuration_key=_INNER_VALIDATION_RETURN_STATUSES_KEY,
            required_sample_ids=required_inner_sample_ids,
            reason_code="inner_validation_return_status_evidence_missing_or_invalid",
        )
        for trial in completed_trials
    }
    if any(
        status is ResearchReturnStatus.MISSING
        for statuses in status_evidence_by_key.values()
        for status in statuses.values()
    ):
        raise EvaluationEngineBlocked(
            PromotionState.BLOCKED_UNCOMPUTABLE,
            ("required_inner_return_missing",),
        )

    selected_by_outer_fold: dict[UUID, TrialRecord] = {}
    audit_rows: list[dict[str, object]] = []
    for outer_fold in outer_folds:
        inner_folds = tuple(
            fold
            for fold in folds
            if fold.fold_kind is FoldKind.INNER and fold.parent_fold_id == outer_fold.fold_id
        )
        if len(inner_folds) != policy.walk_forward.inner_fold_count:
            raise EvaluationEngineBlocked(
                PromotionState.BLOCKED_UNCOMPUTABLE,
                ("inner_validation_geometry_missing",),
            )
        validation_sample_ids = tuple(
            sample_id for fold in inner_folds for sample_id in fold.test_sample_ids
        )
        if not validation_sample_ids or any(
            sample_id not in baseline_cost_by_sample for sample_id in validation_sample_ids
        ):
            raise EvaluationEngineBlocked(
                PromotionState.BLOCKED_UNCOMPUTABLE,
                ("inner_validation_cost_evidence_missing",),
            )
        scores: dict[str, Decimal] = {}
        for trial in completed_trials:
            score_total = Decimal("0")
            for sample_id in validation_sample_ids:
                status = status_evidence_by_key[trial.trial_key][sample_id]
                gross_return = gross_evidence_by_key[trial.trial_key][sample_id]
                if status is ResearchReturnStatus.NO_TRADE:
                    if gross_return != 0:
                        raise EvaluationEngineBlocked(
                            PromotionState.BLOCKED_UNCOMPUTABLE,
                            ("inner_no_trade_return_nonzero",),
                        )
                    net_return = Decimal("0")
                else:
                    net_return = gross_return - baseline_cost_by_sample[sample_id]
                score_total += net_return
            scores[trial.trial_key] = score_total / Decimal(len(validation_sample_ids))
        best_score = max(scores.values())
        winners = tuple(key for key, score in scores.items() if score == best_score)
        if len(winners) != 1:
            raise EvaluationEngineBlocked(
                PromotionState.BLOCKED_UNCOMPUTABLE,
                ("inner_validation_selection_tie",),
            )
        selected_key = winners[0]
        selected_record = records_by_key[selected_key]
        selected_by_outer_fold[outer_fold.fold_id] = selected_record
        audit_rows.append(
            {
                "outer_fold_id": outer_fold.fold_id,
                "inner_fold_ids": tuple(fold.fold_id for fold in inner_folds),
                "inner_validation_sample_ids": validation_sample_ids,
                "selected_trial_id": selected_record.trial_id,
                "selected_trial_key": selected_key,
                "selection_metric": policy.selection.primary_selection_metric,
                "selected_score": best_score,
                "score_basis": "inner_validation_baseline_cost_net_return",
            }
        )
    return selected_by_outer_fold, tuple(audit_rows)


def _validate_outer_trial_cost_lineage(
    *,
    fixture: SyntheticEvaluationFixture,
    accounting: TrialAccounting,
    oos_sample_ids: tuple[str, ...],
    baseline_cost_by_sample: Mapping[str, Decimal],
) -> dict[str, dict[str, Decimal]]:
    completed_trials = tuple(
        trial for trial in fixture.trials if trial.status is TrialStatus.COMPLETED
    )
    records_by_key = {
        record.trial_key: record
        for record in accounting.records
        if record.status is TrialStatus.COMPLETED
    }
    evidence_by_key: dict[str, dict[str, Decimal]] = {}
    for trial in completed_trials:
        evidence = _configuration_return_evidence(
            trial,
            configuration_key=_OUTER_GROSS_RETURNS_KEY,
            required_sample_ids=oos_sample_ids,
            reason_code="outer_return_evidence_missing_or_invalid",
        )
        record = records_by_key[trial.trial_key]
        expected_net_returns: list[Decimal] = []
        for sample_id, status in zip(
            oos_sample_ids,
            record.return_statuses,
            strict=True,
        ):
            if status is ResearchReturnStatus.MISSING:
                raise EvaluationEngineBlocked(
                    PromotionState.BLOCKED_UNCOMPUTABLE,
                    ("required_trial_return_missing",),
                )
            if status is ResearchReturnStatus.NO_TRADE:
                if evidence[sample_id] != 0:
                    raise EvaluationEngineBlocked(
                        PromotionState.BLOCKED_UNCOMPUTABLE,
                        ("outer_no_trade_return_nonzero",),
                    )
                expected_net_returns.append(Decimal("0"))
            else:
                expected_net_returns.append(
                    evidence[sample_id] - baseline_cost_by_sample[sample_id]
                )
        if record.net_returns != tuple(expected_net_returns):
            raise EvaluationEngineBlocked(
                PromotionState.BLOCKED_UNCOMPUTABLE,
                ("trial_baseline_net_return_lineage_mismatch",),
            )
        evidence_by_key[trial.trial_key] = evidence
    return evidence_by_key


def _build_preprocessing_fits(
    folds: tuple[FoldRecord, ...], fixture: SyntheticEvaluationFixture
) -> tuple[PreprocessingFitRecord, ...]:
    samples = {sample.sample_id: sample for sample in fixture.samples}
    records: list[PreprocessingFitRecord] = []
    for fold in folds:
        records.append(
            PreprocessingFitRecord.derive(
                fold_id=fold.fold_id,
                fold_sha256=fold.fold_sha256,
                train_sample_values=tuple(
                    PreprocessingFitSampleValue(
                        sample_id=sample_id,
                        sample_sha256=sample_sha256(samples[sample_id]),
                        value=samples[sample_id].feature_value,
                    )
                    for sample_id in fold.train_sample_ids
                ),
            )
        )
    return tuple(records)


def _moments(values: tuple[float, ...]) -> tuple[float, float]:
    mean = fmean(values)
    second = fmean((value - mean) ** 2 for value in values)
    if second <= 0:
        raise EvaluationEngineBlocked(
            PromotionState.BLOCKED_UNCOMPUTABLE,
            ("return_moments_uncomputable",),
        )
    third = fmean((value - mean) ** 3 for value in values)
    fourth = fmean((value - mean) ** 4 for value in values)
    return third / (second**1.5), fourth / (second**2)


def _snapshot_evidence(
    mapping: AuthorizedMappingIdentity,
    snapshots: tuple[SnapshotBundle, ...],
    policy: FrozenEvaluationPolicy,
) -> tuple[SnapshotEvidence, ...]:
    if not snapshots:
        raise EvaluationEngineBlocked(
            PromotionState.BLOCKED_UNCOMPUTABLE,
            ("required_snapshot_missing",),
        )
    evidence: list[SnapshotEvidence] = []
    for bundle in snapshots:
        manifest = bundle.snapshot.manifest.payload
        if manifest.mapping != mapping or manifest.request.mapping != mapping:
            raise EvaluationEngineBlocked(
                PromotionState.BLOCKED_UNCOMPUTABLE,
                ("snapshot_mapping_lineage_mismatch",),
            )
        if not manifest.adapter.synthetic or not manifest.use_rights.storage_allowed:
            raise EvaluationEngineBlocked(
                PromotionState.BLOCKED_UNCOMPUTABLE,
                ("non_synthetic_snapshot_rejected",),
            )
        schema_versions = tuple(
            f"{item.dataset_schema_id}:{item.dataset_schema_version}"
            for item in manifest.schema_bindings
        )
        evidence.append(
            SnapshotEvidence(
                snapshot_id=bundle.snapshot.snapshot_id,
                snapshot_sha256=bundle.snapshot.snapshot_sha256,
                capability=manifest.request.capability,
                provider_id=manifest.adapter.provider_id,
                adapter_id=manifest.adapter.adapter_id,
                adapter_version=manifest.adapter.adapter_version,
                dataset_id=manifest.adapter.dataset_id,
                product_id=manifest.adapter.product_id,
                dataset_schema_versions=schema_versions,
                quality_status=bundle.snapshot.quality_status,
                fixture_set_version=manifest.configuration.fixture_set_version,
                as_of_utc=manifest.request.as_of_utc,
            )
        )
    ordered = tuple(sorted(evidence, key=lambda item: str(item.capability)))
    if tuple(item.capability for item in ordered) != policy.required_snapshot_capabilities:
        raise EvaluationEngineBlocked(
            PromotionState.BLOCKED_MISSING_POLICY,
            ("required_snapshot_capability_set_mismatch",),
        )
    return ordered


def _gate(
    config_hash: str,
    ordinal: int,
    code: GateCode,
    outcome: GateOutcome,
    *,
    reasons: tuple[str, ...] = (),
    inputs: Mapping[str, str | int | Decimal | bool] | None = None,
    thresholds: Mapping[str, str | int | Decimal | bool] | None = None,
    results: Mapping[str, str | int | Decimal | bool] | None = None,
    warnings: tuple[str, ...] = (),
) -> GateResult:
    gate_inputs = dict(inputs or {})
    gate_thresholds = dict(thresholds or {})
    gate_results = dict(results or {})
    payload = {
        "config_hash": config_hash,
        "ordinal": ordinal,
        "gate_code": code,
        "outcome": outcome,
        "reason_codes": reasons,
        "inputs": gate_inputs,
        "thresholds": gate_thresholds,
        "results": gate_results,
        "warnings": warnings,
    }
    digest = domain_sha256(PHASE5_GATE_HASH_DOMAIN, payload)
    return GateResult(
        gate_result_id=identity(PHASE5_GATE_NAMESPACE, digest),
        gate_result_sha256=digest,
        ordinal=ordinal,
        config_hash=config_hash,
        gate_code=code,
        outcome=outcome,
        reason_codes=reasons,
        inputs=gate_inputs,
        thresholds=gate_thresholds,
        results=gate_results,
        warnings=warnings,
    )


def _promotion_state(gates: tuple[GateResult, ...]) -> PromotionState:
    if any(gate.outcome is GateOutcome.BLOCKED_MISSING_POLICY for gate in gates):
        return PromotionState.BLOCKED_MISSING_POLICY
    if any(gate.outcome is GateOutcome.BLOCKED_UNCOMPUTABLE for gate in gates):
        return PromotionState.BLOCKED_UNCOMPUTABLE
    if any(gate.outcome is GateOutcome.FAIL for gate in gates):
        return PromotionState.FAIL_REJECT
    if any(gate.outcome is GateOutcome.RESEARCH_ONLY for gate in gates):
        return PromotionState.RESEARCH_ONLY_REGIME_DEPENDENT
    return PromotionState.PASS_RESEARCH


def _metric(
    metric_id: str,
    formula_version: str,
    value: Decimal,
    units: str,
    policy: FrozenEvaluationPolicy,
    inputs: dict[str, str | int | Decimal],
    denominator: str,
) -> MetricRecord:
    return MetricRecord(
        metric_id=metric_id,
        formula_version=formula_version,
        value=value,
        units=units,
        frequency=policy.selection.return_frequency,
        annualization_factor=policy.selection.annualization_factor,
        calendar=policy.walk_forward.decision_calendar,
        population="stitched synthetic outer-fold OOS research observations",
        exclusions=("reserved final confirmation interval",),
        denominator=denominator,
        inputs=inputs,
    )


def evaluate_synthetic_fixture(
    *,
    policy: FrozenEvaluationPolicy,
    fixture: SyntheticEvaluationFixture,
    mapping: AuthorizedMappingIdentity,
    snapshots: tuple[SnapshotBundle, ...],
    code_version_git_sha: str,
    created_at_utc: datetime | None = None,
) -> EvaluationReport:
    """Evaluate one registered synthetic ledger and return an immutable research report."""

    _validate_return_policy(policy)
    if mapping.canonical_family is not policy.strategy_family:
        raise EvaluationEngineBlocked(
            PromotionState.BLOCKED_MISSING_POLICY,
            ("policy_mapping_family_mismatch",),
        )
    evidence = _snapshot_evidence(mapping, snapshots, policy)
    try:
        source_lineage = resolve_source_lineage(
            policy=policy,
            fixture=fixture,
            snapshots=snapshots,
        )
    except SourceLineagePolicyError as exc:
        raise EvaluationEngineBlocked(
            PromotionState.BLOCKED_MISSING_POLICY,
            (exc.reason_code,),
        ) from exc
    except SourceLineageInputError as exc:
        raise EvaluationEngineBlocked(
            PromotionState.BLOCKED_UNCOMPUTABLE,
            (exc.reason_code,),
        ) from exc
    snapshot_bundle_hash = domain_sha256(
        PHASE5_SNAPSHOT_BUNDLE_HASH_DOMAIN,
        tuple(item.model_dump(mode="python") for item in evidence),
    )
    request_payload = {
        "policy_id": policy.policy_id,
        "policy_version": policy.policy_version,
        "policy_sha256": policy.policy_sha256,
        "mapping_id": mapping.mapping_id,
        "mapping_version": mapping.mapping_version,
        "mapping_input_sha256": mapping.mapping_input_sha256,
        "snapshot_bundle_sha256": snapshot_bundle_hash,
        "sample_lineage_sha256": source_lineage.sample_lineage_sha256,
        "fixture_id": fixture.fixture_id,
        "fixture_sha256": fixture.fixture_sha256,
        "code_version_git_sha": code_version_git_sha,
        "random_seed": fixture.random_seed,
    }
    request_hash = domain_sha256(PHASE5_REQUEST_HASH_DOMAIN, request_payload)
    config_hash = domain_sha256(PHASE5_CONFIG_HASH_DOMAIN, request_payload)

    geometry = build_evaluation_geometry(
        policy=policy,
        walk_forward=policy.walk_forward,
        fixture=fixture,
    )
    if not geometry.validation.passed:
        state = (
            PromotionState.BLOCKED_MISSING_POLICY
            if geometry.validation.outcome is GateOutcome.BLOCKED_MISSING_POLICY
            else PromotionState.BLOCKED_UNCOMPUTABLE
        )
        raise EvaluationEngineBlocked(state, geometry.validation.reason_codes)
    folds = geometry.folds
    fits = _build_preprocessing_fits(folds, fixture)
    outer_folds = tuple(fold for fold in folds if fold.fold_kind in {FoldKind.OUTER, FoldKind.CPCV})
    oos_sample_ids = tuple(sample_id for fold in outer_folds for sample_id in fold.test_sample_ids)
    samples_by_id = {sample.sample_id: sample for sample in fixture.samples}
    oos_samples = tuple(samples_by_id[sample_id] for sample_id in oos_sample_ids)
    if len(oos_samples) < policy.sample_adequacy.min_oos_observations:
        raise EvaluationEngineBlocked(
            PromotionState.BLOCKED_UNCOMPUTABLE,
            ("insufficient_outer_oos_observations",),
        )
    if any(sample.return_status is ResearchReturnStatus.MISSING for sample in oos_samples):
        raise EvaluationEngineBlocked(
            PromotionState.BLOCKED_UNCOMPUTABLE,
            ("required_selected_oos_return_missing",),
        )

    accounting = _trial_accounting(policy, fixture)
    if accounting.common_calendar != tuple(sample.decision_time_utc for sample in oos_samples):
        raise EvaluationEngineBlocked(
            PromotionState.BLOCKED_UNCOMPUTABLE,
            ("trial_calendar_does_not_match_outer_oos_calendar",),
        )
    try:
        inner_sample_ids = tuple(
            dict.fromkeys(
                sample_id
                for fold in folds
                if fold.fold_kind is FoldKind.INNER
                for sample_id in fold.test_sample_ids
            )
        )
        inner_cost_ledger = build_cost_ledger(
            tuple(samples_by_id[sample_id] for sample_id in inner_sample_ids),
            policy.costs,
            policy.stress,
        )
        inner_baseline_cost_by_sample = {
            item.sample_id: item.total_cost
            for item in inner_cost_ledger
            if item.scenario is CostScenario.BASELINE
        }
        provisional_outer_cost_ledger = build_cost_ledger(
            oos_samples,
            policy.costs,
            policy.stress,
        )
        outer_baseline_cost_by_sample = {
            item.sample_id: item.total_cost
            for item in provisional_outer_cost_ledger
            if item.scenario is CostScenario.BASELINE
        }
        selected_records_by_fold, selection_audit = _select_trials_from_inner_validation(
            policy=policy,
            fixture=fixture,
            accounting=accounting,
            folds=folds,
            outer_folds=outer_folds,
            baseline_cost_by_sample=inner_baseline_cost_by_sample,
        )
        outer_gross_evidence_by_key = _validate_outer_trial_cost_lineage(
            fixture=fixture,
            accounting=accounting,
            oos_sample_ids=oos_sample_ids,
            baseline_cost_by_sample=outer_baseline_cost_by_sample,
        )
        fold_by_sample = {
            sample_id: fold for fold in outer_folds for sample_id in fold.test_sample_ids
        }
        selected_oos_samples: list[SyntheticSample] = []
        for sample in oos_samples:
            selected_record = selected_records_by_fold[fold_by_sample[sample.sample_id].fold_id]
            calendar_index = accounting.common_calendar.index(sample.decision_time_utc)
            return_status = selected_record.return_statuses[calendar_index]
            if return_status is ResearchReturnStatus.MISSING:
                raise EvaluationEngineBlocked(
                    PromotionState.BLOCKED_UNCOMPUTABLE,
                    ("required_selected_oos_return_missing",),
                )
            gross_return = outer_gross_evidence_by_key[selected_record.trial_key][sample.sample_id]
            update: dict[str, object] = {
                "gross_return": gross_return,
                "return_status": return_status,
            }
            if return_status is ResearchReturnStatus.NO_TRADE:
                update.update(
                    {
                        "research_allocation_units": Decimal("0"),
                        "gross_exposure": Decimal("0"),
                        "net_exposure": Decimal("0"),
                        "sector_exposure": Decimal("0"),
                        "turnover": Decimal("0"),
                        "borrow_applicable": False,
                    }
                )
            selected_oos_samples.append(sample.model_copy(update=update))
        oos_samples = tuple(selected_oos_samples)
        cost_ledger = build_cost_ledger(oos_samples, policy.costs, policy.stress)
        summaries = {
            scenario: summarize_cost_scenario(
                cost_ledger, scenario, policy.selection.annualization_factor
            )
            for scenario in CostScenario
        }
    except CostInputError as exc:
        raise EvaluationEngineBlocked(
            PromotionState.BLOCKED_UNCOMPUTABLE,
            ("cost_stress_uncomputable",),
        ) from exc
    baseline_entries = {
        item.sample_id: item for item in cost_ledger if item.scenario is CostScenario.BASELINE
    }
    for sample in oos_samples:
        selected_record = selected_records_by_fold[fold_by_sample[sample.sample_id].fold_id]
        calendar_index = accounting.common_calendar.index(sample.decision_time_utc)
        selected_return = _required_return_value(
            selected_record.return_statuses[calendar_index],
            selected_record.net_returns[calendar_index],
            reason_code="required_selected_oos_return_missing",
        )
        if selected_return != baseline_entries[sample.sample_id].net_return:
            raise EvaluationEngineBlocked(
                PromotionState.BLOCKED_UNCOMPUTABLE,
                ("selected_trial_baseline_net_lineage_mismatch",),
            )
    selected_returns = tuple(
        float(baseline_entries[sample.sample_id].net_return) for sample in oos_samples
    )
    estimated_sharpe = _sample_sharpe(selected_returns)
    skew, kurtosis = _moments(selected_returns)
    try:
        serial_sensitivity = lag1_effective_sample_sensitivity(
            selected_returns,
            policy.selection.serial_correlation_method,
        )
        naive_dsr = compute_deflated_sharpe(
            DeflatedSharpeInputs(
                estimated_sharpe=estimated_sharpe,
                sample_length=len(selected_returns),
                skew=skew,
                ordinary_kurtosis=kurtosis,
                sharpe_variance=accounting.sharpe_variance,
                effective_trials=accounting.effective_count,
                minimum_probability=float(policy.selection.dsr_min_probability),
            )
        )
        dsr = compute_deflated_sharpe(
            DeflatedSharpeInputs(
                estimated_sharpe=estimated_sharpe,
                sample_length=serial_sensitivity.effective_sample_length,
                skew=skew,
                ordinary_kurtosis=kurtosis,
                sharpe_variance=accounting.sharpe_variance,
                effective_trials=accounting.effective_count,
                minimum_probability=float(policy.selection.dsr_min_probability),
            )
        )
        completed_records = tuple(
            record for record in accounting.records if record.status is TrialStatus.COMPLETED
        )
        pbo_matrix = tuple(
            tuple(
                float(
                    _required_return_value(
                        record.return_statuses[row],
                        record.net_returns[row],
                        reason_code="required_trial_return_missing",
                    )
                )
                for record in completed_records
            )
            for row in range(len(completed_records[0].net_returns))
        )
        pbo_status_matrix = tuple(
            tuple(record.return_statuses[row] for record in completed_records)
            for row in range(len(completed_records[0].return_statuses))
        )
        pbo_status_matrix_sha256 = domain_sha256(
            _PBO_RETURN_STATUS_MATRIX_HASH_DOMAIN,
            {
                "configuration_ids": tuple(record.trial_key for record in completed_records),
                "observation_timestamps_utc": accounting.common_calendar,
                "return_status_matrix": pbo_status_matrix,
            },
        )
        pbo_missing_return_count = sum(
            status is ResearchReturnStatus.MISSING for row in pbo_status_matrix for status in row
        )
        pbo_no_trade_count = sum(
            status is ResearchReturnStatus.NO_TRADE for row in pbo_status_matrix for status in row
        )
        pbo = compute_pbo(
            PBOInputs(
                matrix=pbo_matrix,
                configuration_ids=tuple(record.trial_key for record in completed_records),
                block_count=policy.selection.cscv_block_count,
                selection_metric=PBOSelectionMetric.MEAN_RETURN,
                tie_policy=PBOTiePolicy.FAIL,
                maximum_probability=float(policy.selection.pbo_max),
            )
        )
    except MissingStatisticPolicyError as exc:
        raise EvaluationEngineBlocked(
            PromotionState.BLOCKED_MISSING_POLICY,
            ("statistic_threshold_missing",),
        ) from exc
    except StatisticInputError as exc:
        raise EvaluationEngineBlocked(
            PromotionState.BLOCKED_UNCOMPUTABLE,
            ("required_statistic_uncomputable",),
        ) from exc

    allocation_sets = tuple(summary.allocation_input_sha256s for summary in summaries.values())
    allocations_preserved = len(set(allocation_sets)) == 1
    stressed = (summaries[CostScenario.ALL_COST_STRESS], summaries[CostScenario.LIQUIDITY_STRESS])
    cost_pass = allocations_preserved and all(
        item.aggregate_net_return >= policy.stress.min_stressed_net_pnl
        and item.annualized_net_return >= policy.stress.min_stressed_annual_return
        and item.net_sharpe >= policy.stress.min_stressed_sharpe
        and item.maximum_drawdown <= policy.stress.max_stressed_drawdown
        and item.capacity_breach_rate <= policy.stress.max_capacity_breach_rate
        for item in stressed
    )

    oos_ledger: list[OosLedgerEntry] = []
    for ordinal, sample in enumerate(oos_samples):
        cost = baseline_entries[sample.sample_id]
        selected_record = selected_records_by_fold[fold_by_sample[sample.sample_id].fold_id]
        sample_lineage = source_lineage.lineage_for(sample.sample_id)
        payload = {
            "ordinal": ordinal,
            "trial_id": selected_record.trial_id,
            "fold_id": fold_by_sample[sample.sample_id].fold_id,
            "sample_id": sample.sample_id,
            "sample_sha256": sample_lineage.sample_sha256,
            "source_observation_refs": sample_lineage.source_observation_refs,
            "information_start_utc": sample.feature_available_at_utc,
            "information_end_utc": sample.feature_available_at_utc,
            "decision_time_utc": sample.decision_time_utc,
            "label_t0_utc": sample.label_t0_utc,
            "label_t1_utc": sample.label_t1_utc,
            "predicted_value": sample.predicted_value,
            "gross_return": sample.gross_return,
            "baseline_net_return": cost.net_return,
            "return_status": sample.return_status,
            "delisting_return_handled": sample.delisting_return_handled,
        }
        digest = domain_sha256(PHASE5_LEDGER_HASH_DOMAIN, payload)
        oos_ledger.append(
            OosLedgerEntry.model_validate(
                {
                    **payload,
                    "ledger_entry_id": identity(PHASE5_LEDGER_NAMESPACE, digest),
                    "ledger_entry_sha256": digest,
                }
            )
        )

    missing_return_count = sum(
        entry.return_status is ResearchReturnStatus.MISSING for entry in oos_ledger
    )
    no_trade_count = sum(
        entry.return_status is ResearchReturnStatus.NO_TRADE for entry in oos_ledger
    )

    leakage = evaluate_leakage(
        fixture.samples,
        folds,
        fits,
        source_lineage.source_observations,
        feature_specification=policy.feature_specification,
        label_specification=policy.label_specification,
    )
    leakage_hits = tuple(item for item in leakage if item.blocked)
    pit_hits = pit_blocking_sample_ids(fixture.samples, leakage)
    independent_events = len({sample.independent_event_id for sample in oos_samples})
    volatility_labels = {
        sample.sample_id: (
            "low" if sample.daily_volatility < policy.regimes.volatility_cut else "high"
        )
        for sample in oos_samples
    }
    rate_labels = {
        sample.sample_id: (
            "rising"
            if sample.rate_change > policy.regimes.rate_cut
            else "falling"
            if sample.rate_change < policy.regimes.rate_cut
            else "flat"
        )
        for sample in oos_samples
    }
    observed_crisis_windows = {
        window for sample in oos_samples for window in sample.crisis_window_ids
    }
    missing_regime_evidence: list[str] = []
    if set(volatility_labels.values()) != {"low", "high"}:
        missing_regime_evidence.append("volatility_regime_coverage_missing")
    if set(rate_labels.values()) != {"rising", "falling"}:
        missing_regime_evidence.append("rate_regime_coverage_missing")
    if not set(policy.regimes.crisis_windows).issubset(observed_crisis_windows):
        missing_regime_evidence.append("crisis_window_coverage_missing")
    regime_members: dict[str, list[SyntheticSample]] = defaultdict(list)
    for sample in oos_samples:
        regime_members[f"volatility:{volatility_labels[sample.sample_id]}"].append(sample)
        regime_members[f"rate:{rate_labels[sample.sample_id]}"].append(sample)
        for crisis_window in sample.crisis_window_ids:
            regime_members[f"crisis:{crisis_window}"].append(sample)
    regime_breakdowns = tuple(
        {
            "regime": regime,
            "sample_ids": tuple(sample.sample_id for sample in members),
            "gross_pnl": sum(
                (
                    _required_return_value(
                        sample.return_status,
                        sample.gross_return,
                        reason_code="required_selected_oos_return_missing",
                    )
                    for sample in members
                ),
                Decimal("0"),
            ),
            "baseline_net_pnl": sum(
                (baseline_entries[sample.sample_id].net_return for sample in members),
                Decimal("0"),
            ),
            "turnover": sum((sample.turnover for sample in members), Decimal("0")),
            "capacity_breach_rate": (
                Decimal(
                    sum(baseline_entries[sample.sample_id].capacity_breached for sample in members)
                )
                / Decimal(len(members))
            ),
        }
        for regime, members in sorted(regime_members.items())
    )
    leakage_evidence = LeakageGateEvidence(
        findings=tuple(
            LeakageFindingEvidence(
                code=finding.code,
                blocked=finding.blocked,
                affected_sample_ids=finding.affected_sample_ids,
                evidence_rule=finding.evidence_rule,
                evidence_records=finding.evidence_records,
            )
            for finding in leakage
        )
    )
    leakage_details_json = canonical_json_text(leakage_evidence.findings)
    quality_findings_json = canonical_json_text(
        {
            "duplicate_grain_count": len(fixture.samples)
            - len({sample.sample_id for sample in fixture.samples}),
            "future_feature_or_rate_count": sum(
                sample.feature_available_at_utc > sample.decision_time_utc
                or sample.rate_available_at_utc > sample.decision_time_utc
                for sample in fixture.samples
            ),
            "unhandled_delisting_count": sum(
                not sample.delisting_return_handled for sample in fixture.samples
            ),
            "late_revision_count": sum(
                len(finding.affected_sample_ids)
                for finding in leakage
                if finding.code is LeakageCode.L02
            ),
            "snapshot_quality_statuses": tuple(item.quality_status for item in evidence),
        }
    )
    baseline = summaries[CostScenario.BASELINE]
    risk_failure_ids = {
        sample.sample_id
        for sample in oos_samples
        if sample.gross_exposure > policy.risk.max_gross_exposure
        or abs(sample.net_exposure) > policy.risk.max_net_exposure
        or sample.sector_exposure > policy.risk.max_sector_exposure
        or sample.turnover > policy.risk.max_turnover
        or sample.daily_volatility > policy.risk.max_volatility
        or sample.gross_exposure > policy.risk.max_single_observation_exposure
        or baseline_entries[sample.sample_id].net_return < -policy.risk.max_loss
    }
    risk_drawdown_breach = baseline.maximum_drawdown > policy.risk.max_drawdown
    all_cost = summaries[CostScenario.ALL_COST_STRESS]
    liquidity = summaries[CostScenario.LIQUIDITY_STRESS]
    pbo_blocks_json = canonical_json_text(
        tuple(
            {
                "block_index": block.block_index,
                "row_start": block.row_start,
                "row_stop": block.row_stop,
            }
            for block in pbo.blocks
        )
    )
    pbo_split_details_json = canonical_json_text(
        tuple(
            {
                "train_blocks": split.train_blocks,
                "test_blocks": split.test_blocks,
                "train_row_indices": split.train_row_indices,
                "test_row_indices": split.test_row_indices,
                "in_sample_scores": tuple(_decimal(value) for value in split.in_sample_scores),
                "out_of_sample_scores": tuple(
                    _decimal(value) for value in split.out_of_sample_scores
                ),
                "selected_configuration_index": split.selected_configuration_index,
                "selected_configuration_id": split.selected_configuration_id,
                "out_of_sample_ranks": split.out_of_sample_ranks,
                "selected_out_of_sample_rank": split.selected_out_of_sample_rank,
                "normalized_rank": _decimal(split.normalized_rank),
                "logit": _decimal(split.logit),
            }
            for split in pbo.splits
        )
    )
    gates = (
        _gate(
            config_hash,
            0,
            GateCode.DATA_PIT,
            GateOutcome.PASS if not pit_hits else GateOutcome.FAIL,
            reasons=() if not pit_hits else ("pit_or_delisting_defect",),
            inputs={
                "snapshot_count": len(evidence),
                "sample_count": len(fixture.samples),
                "source_observation_count": len(source_lineage.source_observations),
                "sample_lineage_sha256": source_lineage.sample_lineage_sha256,
                "feature_value_binding_rule": (
                    policy.feature_specification.source_observation_binding_rule
                ),
                "feature_derivation_formula": (policy.feature_specification.formula_id),
                "synthetic_ledger_value_rule": fixture.samples[0].synthetic_ledger_value_rule,
                "minimum_decision_time_utc": min(
                    sample.decision_time_utc for sample in fixture.samples
                ).isoformat(),
                "maximum_decision_time_utc": max(
                    sample.decision_time_utc for sample in fixture.samples
                ).isoformat(),
                "quality_findings_json": quality_findings_json,
            },
            results={
                "blocking_sample_count": len(pit_hits),
                "blocking_sample_rate": Decimal(len(pit_hits)) / Decimal(len(fixture.samples)),
                "blocking_sample_ids_json": canonical_json_text(pit_hits),
                "lineage_bound_sample_count": len(source_lineage.sample_lineage),
                "source_derived_feature_count": len(source_lineage.sample_lineage),
                "source_derived_feature_bindings_verified": True,
                "predictions_and_returns_are_synthetic_ledger_inputs": True,
                "oos_lineage_bound_count": len(oos_ledger),
            },
        ),
        _gate(
            config_hash,
            1,
            GateCode.CV_CHRONOLOGY,
            geometry.validation.outcome,
            reasons=geometry.validation.reason_codes,
            inputs={
                **geometry.validation.gate_inputs(),
                "expected_outer_oos_observation_count": (
                    policy.walk_forward.outer_fold_count
                    * policy.walk_forward.outer_test_observations
                ),
            },
            thresholds={
                **geometry.validation.gate_thresholds(),
                "minimum_oos_observations": policy.sample_adequacy.min_oos_observations,
            },
            results={
                **geometry.validation.gate_results(),
                "observed_outer_oos_observation_count": len(oos_samples),
            },
        ),
        _gate(
            config_hash,
            2,
            GateCode.PREPROCESSING,
            GateOutcome.FAIL
            if next(item for item in leakage if item.code is LeakageCode.L06).blocked
            else GateOutcome.PASS,
            reasons=(
                ("preprocessing_train_only_violation",)
                if next(item for item in leakage if item.code is LeakageCode.L06).blocked
                else ()
            ),
            inputs={"fit_count": len(fits)},
            results={
                "all_fit_ids_train_only": not next(
                    item for item in leakage if item.code is LeakageCode.L06
                ).blocked
            },
        ),
        _gate(
            config_hash,
            3,
            GateCode.TRIAL_REGISTRY,
            GateOutcome.PASS,
            inputs={
                "raw_trial_count": len(accounting.records),
                "selection_evidence_scope": "nested_inner_validation_only",
                "missing_return_policy": policy.sample_adequacy.missing_return_policy.value,
                "no_trade_return_policy": policy.sample_adequacy.no_trade_return_policy.value,
            },
            results={
                "failed_count": sum(
                    item.status is TrialStatus.FAILED for item in accounting.records
                ),
                "abandoned_count": sum(
                    item.status is TrialStatus.ABANDONED for item in accounting.records
                ),
                "no_return_trial_count": sum(
                    item.status is TrialStatus.NO_RETURN for item in accounting.records
                ),
                "completed_missing_return_count": sum(
                    status is ResearchReturnStatus.MISSING
                    for item in accounting.records
                    if item.status is TrialStatus.COMPLETED
                    for status in item.return_statuses
                ),
                "completed_no_trade_count": sum(
                    status is ResearchReturnStatus.NO_TRADE
                    for item in accounting.records
                    if item.status is TrialStatus.COMPLETED
                    for status in item.return_statuses
                ),
                "effective_trial_count": _decimal(accounting.effective_count),
                "outer_fold_selection_json": canonical_json_text(selection_audit),
            },
        ),
        _gate(
            config_hash,
            4,
            GateCode.DSR,
            GateOutcome.PASS if dsr.passes else GateOutcome.FAIL,
            reasons=() if dsr.passes else ("dsr_below_frozen_threshold",),
            inputs={
                "formula_version": dsr.formula_version,
                "estimator": "per_period_mean_over_sample_standard_deviation_ddof_1",
                "return_frequency": policy.selection.return_frequency,
                "annualization_factor": policy.selection.annualization_factor,
                "estimated_sharpe": _decimal(dsr.estimated_sharpe),
                "T": dsr.sample_length,
                "T_nominal": serial_sensitivity.nominal_sample_length,
                "T_effective": serial_sensitivity.effective_sample_length,
                "T_effective_raw": _decimal(serial_sensitivity.raw_effective_sample_length),
                "serial_correlation_method": serial_sensitivity.method,
                "lag1_autocorrelation": _decimal(serial_sensitivity.lag1_autocorrelation),
                "skew": _decimal(dsr.skew),
                "ordinary_kurtosis": _decimal(dsr.ordinary_kurtosis),
                "V_SR": _decimal(dsr.sharpe_variance),
                "M_raw": len(accounting.records),
                "N_eff": _decimal(dsr.effective_trials),
            },
            thresholds={"dsr_min_probability": policy.selection.dsr_min_probability},
            results={
                "expected_maximum_sharpe": _decimal(dsr.expected_maximum_sharpe),
                "z_score": _decimal(dsr.z_score),
                "dsr_probability": _decimal(dsr.probability),
                "naive_dsr_probability": _decimal(naive_dsr.probability),
                "passes": dsr.passes,
            },
        ),
        _gate(
            config_hash,
            5,
            GateCode.PBO,
            GateOutcome.PASS if pbo.passes else GateOutcome.FAIL,
            reasons=() if pbo.passes else ("pbo_above_frozen_threshold",),
            inputs={
                "formula_version": pbo.formula_version,
                "matrix_hash_version": pbo.matrix_hash_version,
                "matrix_sha256": pbo.matrix_sha256,
                "return_status_matrix_hash_version": _PBO_RETURN_STATUS_MATRIX_HASH_DOMAIN,
                "return_status_matrix_sha256": pbo_status_matrix_sha256,
                "matrix_missing_return_count": pbo_missing_return_count,
                "matrix_no_trade_count": pbo_no_trade_count,
                "configuration_count": len(pbo.configuration_ids),
                "configuration_order_json": canonical_json_text(pbo.configuration_ids),
                "observation_timestamps_utc_json": canonical_json_text(accounting.common_calendar),
                "matrix_row_count": len(pbo_matrix),
                "block_count": len(pbo.blocks),
                "blocks_json": pbo_blocks_json,
                "split_count": len(pbo.splits),
                "selection_metric": pbo.selection_metric.value,
                "tie_policy": pbo.tie_policy.value,
                "return_basis": "synchronous_baseline_cost_net_returns",
                "trial_ledger_lineage_verified": True,
                "missing_return_policy": policy.sample_adequacy.missing_return_policy.value,
                "no_trade_return_policy": policy.sample_adequacy.no_trade_return_policy.value,
            },
            thresholds={"pbo_max": policy.selection.pbo_max},
            results={
                "pbo_probability": _decimal(pbo.probability),
                "passes": pbo.passes,
                "split_details_json": pbo_split_details_json,
            },
        ),
        _gate(
            config_hash,
            6,
            GateCode.COST_STRESS,
            GateOutcome.PASS if cost_pass else GateOutcome.FAIL,
            reasons=() if cost_pass else ("stressed_edge_non_positive_or_policy_limit",),
            inputs={
                "allocation_inputs_preserved": allocations_preserved,
                "all_cost_multiplier": policy.stress.all_cost_multiplier,
                "component_count": 5,
            },
            thresholds={
                "min_stressed_net_pnl": policy.stress.min_stressed_net_pnl,
                "min_stressed_annual_return": policy.stress.min_stressed_annual_return,
                "min_stressed_sharpe": policy.stress.min_stressed_sharpe,
                "max_stressed_drawdown": policy.stress.max_stressed_drawdown,
                "max_capacity_breach_rate": policy.stress.max_capacity_breach_rate,
            },
            results={
                "all_cost_net_return": all_cost.aggregate_net_return,
                "all_cost_annualized_net_return": all_cost.annualized_net_return,
                "all_cost_net_sharpe": all_cost.net_sharpe,
                "all_cost_maximum_drawdown": all_cost.maximum_drawdown,
                "all_cost_capacity_breach_rate": all_cost.capacity_breach_rate,
                "all_cost_fill_rate": all_cost.fill_rate,
                "all_cost_rejection_rate": all_cost.rejection_rate,
                "all_cost_requested_quantity": all_cost.requested_quantity,
                "all_cost_filled_quantity": all_cost.filled_quantity,
                "all_cost_rejected_quantity": all_cost.rejected_quantity,
                "liquidity_net_return": liquidity.aggregate_net_return,
                "liquidity_annualized_net_return": liquidity.annualized_net_return,
                "liquidity_net_sharpe": liquidity.net_sharpe,
                "liquidity_maximum_drawdown": liquidity.maximum_drawdown,
                "liquidity_capacity_breach_rate": liquidity.capacity_breach_rate,
                "liquidity_fill_rate": liquidity.fill_rate,
                "liquidity_rejection_rate": liquidity.rejection_rate,
                "liquidity_requested_quantity": liquidity.requested_quantity,
                "liquidity_filled_quantity": liquidity.filled_quantity,
                "liquidity_rejected_quantity": liquidity.rejected_quantity,
            },
        ),
        _gate(
            config_hash,
            7,
            GateCode.LEAKAGE,
            GateOutcome.PASS if not leakage_hits else GateOutcome.FAIL,
            reasons=tuple(f"leakage_{item.code.lower()}" for item in leakage_hits),
            inputs={
                "check_count": len(leakage),
                "per_check_evidence_json": leakage_details_json,
            },
            results={
                "blocking_check_count": len(leakage_hits),
                "blocking_check_rate": Decimal(len(leakage_hits)) / Decimal(len(leakage)),
            },
        ),
        _gate(
            config_hash,
            8,
            GateCode.SAMPLE_ADEQUACY,
            (
                GateOutcome.PASS
                if len(oos_samples) >= policy.sample_adequacy.min_oos_observations
                and independent_events >= policy.sample_adequacy.min_independent_events
                else GateOutcome.FAIL
            ),
            reasons=(
                ()
                if len(oos_samples) >= policy.sample_adequacy.min_oos_observations
                and independent_events >= policy.sample_adequacy.min_independent_events
                else ("sample_adequacy_below_frozen_minimum",)
            ),
            inputs={
                "oos_observations": len(oos_samples),
                "observed_or_delisted_return_count": (
                    len(oos_samples) - missing_return_count - no_trade_count
                ),
                "missing_return_count": missing_return_count,
                "no_trade_count": no_trade_count,
                "missing_return_policy": policy.sample_adequacy.missing_return_policy.value,
                "no_trade_return_policy": policy.sample_adequacy.no_trade_return_policy.value,
                "independent_events": independent_events,
            },
            thresholds={
                "min_oos_observations": policy.sample_adequacy.min_oos_observations,
                "min_independent_events": policy.sample_adequacy.min_independent_events,
            },
            results={
                "oos_observation_shortfall": max(
                    0,
                    policy.sample_adequacy.min_oos_observations - len(oos_samples),
                ),
                "independent_event_shortfall": max(
                    0,
                    policy.sample_adequacy.min_independent_events - independent_events,
                ),
            },
        ),
        _gate(
            config_hash,
            9,
            GateCode.REGIME,
            GateOutcome.PASS if not missing_regime_evidence else GateOutcome.RESEARCH_ONLY,
            reasons=tuple(missing_regime_evidence),
            inputs={
                "volatility_definition": policy.regimes.volatility_definition,
                "volatility_cut": policy.regimes.volatility_cut,
                "rate_definition": policy.regimes.rate_definition,
                "rate_cut": policy.regimes.rate_cut,
                "dependency_rule": policy.regimes.dependency_rule,
                "predeclared_crisis_windows_json": canonical_json_text(
                    policy.regimes.crisis_windows
                ),
            },
            results={
                "observed_volatility_regimes_json": canonical_json_text(
                    tuple(sorted(set(volatility_labels.values())))
                ),
                "observed_rate_regimes_json": canonical_json_text(
                    tuple(sorted(set(rate_labels.values())))
                ),
                "observed_crisis_windows_json": canonical_json_text(
                    tuple(sorted(observed_crisis_windows))
                ),
                "regime_breakdowns_json": canonical_json_text(regime_breakdowns),
                "missing_required_regime_count": len(missing_regime_evidence),
            },
            warnings=("Synthetic regimes are QA evidence, not market findings.",),
        ),
        _gate(
            config_hash,
            10,
            GateCode.RISK_LIMITS,
            (
                GateOutcome.PASS
                if not risk_failure_ids and not risk_drawdown_breach
                else GateOutcome.FAIL
            ),
            reasons=(
                ()
                if not risk_failure_ids and not risk_drawdown_breach
                else ("research_risk_limit_breach",)
            ),
            inputs={"evaluated_sample_count": len(oos_samples)},
            thresholds={
                "max_single_observation_exposure": (policy.risk.max_single_observation_exposure),
                "max_gross_exposure": policy.risk.max_gross_exposure,
                "max_net_exposure": policy.risk.max_net_exposure,
                "max_sector_exposure": policy.risk.max_sector_exposure,
                "max_turnover": policy.risk.max_turnover,
                "max_volatility": policy.risk.max_volatility,
                "max_loss": policy.risk.max_loss,
                "max_drawdown": policy.risk.max_drawdown,
            },
            results={
                "observation_breach_count": len(risk_failure_ids),
                "drawdown_breached": risk_drawdown_breach,
                "baseline_maximum_drawdown": baseline.maximum_drawdown,
            },
        ),
        _gate(
            config_hash,
            11,
            GateCode.REPRODUCIBILITY,
            GateOutcome.PASS,
            inputs={
                "config_hash": config_hash,
                "snapshot_bundle_sha256": snapshot_bundle_hash,
                "sample_lineage_sha256": source_lineage.sample_lineage_sha256,
                "fixture_sha256": fixture.fixture_sha256,
                "git_sha": code_version_git_sha,
                "random_seed": fixture.random_seed,
                "feature_derivation_formula": policy.feature_specification.formula_id,
                "synthetic_ledger_value_rule": fixture.samples[0].synthetic_ledger_value_rule,
            },
            results={
                "complete_audit_fields": True,
                "source_derived_feature_bindings_verified": True,
                "synthetic_ledger_inputs_explicit": True,
            },
        ),
    )
    state = _promotion_state(gates)
    autocorrelation = serial_sensitivity.lag1_autocorrelation
    try:
        metrics = build_evaluation_metrics(
            samples=oos_samples,
            folds=folds,
            cost_ledger=cost_ledger,
            scenario_summaries=tuple(summaries[scenario] for scenario in CostScenario),
            policy=policy,
            diagnostics=EvaluationMetricDiagnostics(
                raw_trial_count=len(accounting.records),
                effective_trial_count=_decimal(accounting.effective_count),
                sharpe_variance=_decimal(accounting.sharpe_variance),
                dsr_probability=_decimal(dsr.probability),
                dsr_inputs=(
                    ("estimated_sharpe", _decimal(dsr.estimated_sharpe)),
                    ("sample_length", dsr.sample_length),
                    ("skew", _decimal(dsr.skew)),
                    ("ordinary_kurtosis", _decimal(dsr.ordinary_kurtosis)),
                    ("sharpe_variance", _decimal(dsr.sharpe_variance)),
                    ("effective_trials", _decimal(dsr.effective_trials)),
                    ("lag1_autocorrelation", _decimal(autocorrelation)),
                    ("serial_correlation_method", serial_sensitivity.method),
                ),
                pbo_probability=_decimal(pbo.probability),
                pbo_inputs=(
                    ("split_count", len(pbo.splits)),
                    ("configuration_count", len(pbo.configuration_ids)),
                    ("tie_policy", pbo.tie_policy.value),
                    ("rank_orientation", policy.selection.pbo_rank_orientation),
                    ("matrix_sha256", pbo.matrix_sha256),
                    ("return_status_matrix_sha256", pbo_status_matrix_sha256),
                    ("matrix_missing_return_count", pbo_missing_return_count),
                    ("matrix_no_trade_count", pbo_no_trade_count),
                ),
                missing_return_count=missing_return_count,
                no_trade_count=no_trade_count,
                exclusions=("reserved final confirmation interval",),
            ),
        )
    except MetricInputError as exc:
        raise EvaluationEngineBlocked(
            PromotionState.BLOCKED_UNCOMPUTABLE,
            ("required_metric_uncomputable",),
        ) from exc
    reason_codes = tuple(reason for gate in gates for reason in gate.reason_codes)
    provider_versions = tuple(
        f"{item.provider_id}:{item.adapter_version}:{item.capability}" for item in evidence
    )
    created = (created_at_utc or datetime.now(UTC)).astimezone(UTC)
    report_content = {
        "request_fingerprint_sha256": request_hash,
        "config_hash": config_hash,
        "evaluation_policy_id": policy.policy_id,
        "evaluation_policy_version": policy.policy_version,
        "evaluation_policy_sha256": policy.policy_sha256,
        "mapping_id": mapping.mapping_id,
        "mapping_version": mapping.mapping_version,
        "mapping_input_sha256": mapping.mapping_input_sha256,
        "snapshot_bundle_sha256": snapshot_bundle_hash,
        "data_snapshots": evidence,
        "source_observations": source_lineage.source_observations,
        "sample_lineage_sha256": source_lineage.sample_lineage_sha256,
        "sample_lineage": source_lineage.sample_lineage,
        "provider_source_versions": provider_versions,
        "code_version_git_sha": code_version_git_sha,
        "random_seed": fixture.random_seed,
        "raw_trial_count": len(accounting.records),
        "effective_trial_count": _decimal(accounting.effective_count),
        "parent_artifact_ids": (),
        "fixture_id": fixture.fixture_id,
        "fixture_sha256": fixture.fixture_sha256,
        "promotion_state": state,
        "feature_specification": policy.feature_specification,
        "label_specification": policy.label_specification,
        "trials": accounting.records,
        "folds": folds,
        "preprocessing_fits": fits,
        "oos_ledger": tuple(oos_ledger),
        "cost_ledger": cost_ledger,
        "metrics": metrics,
        "gates": gates,
        "warnings": fixture.warnings,
        "reason_codes": reason_codes,
    }
    artifact_hash = domain_sha256(PHASE5_ARTIFACT_HASH_DOMAIN, report_content)
    return EvaluationReport.model_validate(
        {
            **report_content,
            "artifact_id": identity(PHASE5_ARTIFACT_NAMESPACE, artifact_hash),
            "artifact_sha256": artifact_hash,
            "created_at_utc": created,
            "decision_time_utc": max(sample.decision_time_utc for sample in oos_samples),
        }
    )


__all__ = [
    "EvaluationEngineBlocked",
    "EvaluationEngineError",
    "TrialAccounting",
    "evaluate_synthetic_fixture",
    "evaluation_report_hash_payload",
    "evaluation_request_payload_from_report",
]
