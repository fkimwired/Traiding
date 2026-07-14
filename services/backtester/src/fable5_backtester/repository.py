"""Append-only PostgreSQL persistence for immutable Phase 5 evaluation artifacts."""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

from fable5_data.canonical import canonicalize
from sqlalchemy import Engine, bindparam, create_engine, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import Connection, RowMapping
from sqlalchemy.exc import DBAPIError, IntegrityError

from fable5_backtester.canonical import (
    PHASE5_ARTIFACT_HASH_DOMAIN,
    PHASE5_CONFIG_HASH_DOMAIN,
    PHASE5_COST_HASH_DOMAIN,
    PHASE5_FEATURE_HASH_DOMAIN,
    PHASE5_FIT_HASH_DOMAIN,
    PHASE5_FOLD_HASH_DOMAIN,
    PHASE5_GATE_HASH_DOMAIN,
    PHASE5_LABEL_HASH_DOMAIN,
    PHASE5_LEDGER_HASH_DOMAIN,
    PHASE5_POLICY_HASH_DOMAIN,
    PHASE5_REPORT_SNAPSHOT_HASH_DOMAIN,
    PHASE5_REPORT_SNAPSHOT_NAMESPACE,
    PHASE5_REQUEST_HASH_DOMAIN,
    PHASE5_SAMPLE_LINEAGE_HASH_DOMAIN,
    PHASE5_SNAPSHOT_BUNDLE_HASH_DOMAIN,
    PHASE5_TRIAL_HASH_DOMAIN,
    canonical_json_text,
    domain_sha256,
    identity,
)
from fable5_backtester.contracts import (
    CostScenario,
    EvaluationReport,
    EvaluationReportSummary,
    FrozenEvaluationPolicy,
    GateOutcome,
    ResearchReturnStatus,
)
from fable5_backtester.engine import (
    evaluation_report_hash_payload,
    evaluation_request_payload_from_report,
)
from fable5_backtester.outcomes import (
    PHASE5_BLOCKED_OUTCOME_HASH_DOMAIN,
    PHASE5_BLOCKED_OUTCOME_IDEMPOTENCY_HASH_DOMAIN,
    PHASE5_BLOCKED_SUBMISSION_HASH_DOMAIN,
    BlockedEvaluationOutcome,
    EvaluationOutcomeNotFound,
    blocked_outcome_hash_payload,
    blocked_outcome_idempotency_payload,
    evaluation_request_from_outcome,
)
from fable5_backtester.workflow import (
    EvaluationPolicyNotFound,
    EvaluationReportNotFound,
    EvaluationWorkflowConflict,
)


def _json_statement(sql: str, *json_columns: str) -> Any:
    statement = text(sql)
    for column in json_columns:
        statement = statement.bindparams(
            bindparam(column, type_=postgresql.JSONB(astext_type=postgresql.TEXT()))
        )
    return statement


def _insert_row(
    connection: Connection,
    table: str,
    row: Mapping[str, Any],
    *,
    json_columns: frozenset[str] = frozenset(),
) -> None:
    columns = tuple(row)
    statement = _json_statement(
        f"INSERT INTO {table} ({', '.join(columns)}) VALUES "
        f"({', '.join(f':{column}' for column in columns)})",
        *json_columns,
    )
    connection.execute(statement, dict(row))


def _artifact_payload(
    domain: str,
    payload: object,
    expected_sha256: str,
) -> tuple[str, dict[str, Any]]:
    canonical_json = canonical_json_text(payload)
    if domain_sha256(domain, payload) != expected_sha256:
        raise EvaluationWorkflowConflict("immutable Phase 5 artifact hash does not match payload")
    normalized = canonicalize(payload)
    if not isinstance(normalized, dict):
        raise EvaluationWorkflowConflict("immutable Phase 5 artifact payload must be an object")
    return canonical_json, cast(dict[str, Any], normalized)


def _policy_payload(policy: FrozenEvaluationPolicy) -> dict[str, Any]:
    payload = policy.model_dump(
        mode="python",
        exclude={"policy_sha256", "policy_canonical_json"},
    )
    if canonical_json_text(payload) != policy.policy_canonical_json:
        raise EvaluationWorkflowConflict("frozen policy canonical JSON is inconsistent")
    return payload


def _feature_payload(policy: FrozenEvaluationPolicy) -> dict[str, Any]:
    return policy.feature_specification.model_dump(
        mode="python",
        exclude={"feature_specification_id", "content_sha256"},
    )


def _label_payload(policy: FrozenEvaluationPolicy) -> dict[str, Any]:
    return policy.label_specification.model_dump(
        mode="python",
        exclude={"label_specification_id", "content_sha256"},
    )


def _load_policy_row(row: RowMapping) -> FrozenEvaluationPolicy:
    payload = dict(row["payload"])
    policy = FrozenEvaluationPolicy.model_validate(
        {
            **payload,
            "policy_sha256": row["policy_sha256"],
            "policy_canonical_json": row["canonical_json"],
        }
    )
    _artifact_payload(PHASE5_POLICY_HASH_DOMAIN, _policy_payload(policy), policy.policy_sha256)
    return policy


def _load_report_row(row: RowMapping) -> EvaluationReport:
    report = EvaluationReport.model_validate(
        {
            **dict(row["payload"]),
            "artifact_id": row["report_id"],
            "artifact_sha256": row["report_sha256"],
            "created_at_utc": row["created_at_utc"],
            "decision_time_utc": row["decision_time_utc"],
        }
    )
    _artifact_payload(
        PHASE5_ARTIFACT_HASH_DOMAIN,
        evaluation_report_hash_payload(report),
        report.artifact_sha256,
    )
    request_payload = evaluation_request_payload_from_report(report)
    if domain_sha256(PHASE5_REQUEST_HASH_DOMAIN, request_payload) != (
        report.request_fingerprint_sha256
    ):
        raise EvaluationWorkflowConflict("persisted run fingerprint failed revalidation")
    if domain_sha256(PHASE5_CONFIG_HASH_DOMAIN, request_payload) != report.config_hash:
        raise EvaluationWorkflowConflict("persisted configuration hash failed revalidation")
    return report


def _load_outcome_row(row: RowMapping) -> BlockedEvaluationOutcome:
    payload = dict(row["payload"])
    request_payload = dict(row["submission_payload"])
    payload.pop("request", None)
    outcome = BlockedEvaluationOutcome.model_validate(
        {
            **payload,
            **request_payload,
            "outcome_id": row["outcome_id"],
            "outcome_sha256": row["outcome_sha256"],
            "created_at_utc": row["created_at_utc"],
        }
    )
    _artifact_payload(
        PHASE5_BLOCKED_OUTCOME_HASH_DOMAIN,
        blocked_outcome_hash_payload(outcome),
        outcome.outcome_sha256,
    )
    idempotency_json, idempotency_payload = _artifact_payload(
        PHASE5_BLOCKED_OUTCOME_IDEMPOTENCY_HASH_DOMAIN,
        blocked_outcome_idempotency_payload(outcome),
        outcome.idempotency_sha256,
    )
    if outcome.idempotency_sha256 != row["idempotency_sha256"]:
        raise EvaluationWorkflowConflict(
            "persisted blocked outcome idempotency hash failed revalidation"
        )
    if idempotency_json != row["idempotency_canonical_json"] or (
        idempotency_payload != row["idempotency_payload"]
    ):
        raise EvaluationWorkflowConflict(
            "persisted blocked outcome idempotency payload failed revalidation"
        )
    request = evaluation_request_from_outcome(outcome)
    if (
        domain_sha256(
            PHASE5_BLOCKED_SUBMISSION_HASH_DOMAIN,
            request.model_dump(mode="python"),
        )
        != outcome.submission_sha256
    ):
        raise EvaluationWorkflowConflict("persisted blocked submission hash failed revalidation")
    if canonical_json_text(request.model_dump(mode="python")) != row["submission_canonical_json"]:
        raise EvaluationWorkflowConflict(
            "persisted blocked submission canonical JSON failed revalidation"
        )
    return outcome


class EvaluationRepository:
    def __init__(self, database_url: str | None = None, *, engine: Engine | None = None) -> None:
        if database_url is None and engine is None:
            raise ValueError("database_url or engine is required")
        self.engine = engine or create_engine(str(database_url), pool_pre_ping=True)
        self._owns_engine = engine is None

    def dispose(self) -> None:
        if self._owns_engine:
            self.engine.dispose()

    @staticmethod
    def _policy_row(
        connection: Connection,
        policy_id: UUID,
        policy_version: int,
    ) -> RowMapping | None:
        return (
            connection.execute(
                text(
                    "SELECT * FROM evaluation_policies "
                    "WHERE policy_id = :policy_id AND policy_version = :policy_version"
                ),
                {"policy_id": policy_id, "policy_version": policy_version},
            )
            .mappings()
            .one_or_none()
        )

    @classmethod
    def _load_policy(
        cls,
        connection: Connection,
        policy_id: UUID,
        policy_version: int,
    ) -> FrozenEvaluationPolicy:
        row = cls._policy_row(connection, policy_id, policy_version)
        if row is None:
            raise EvaluationPolicyNotFound(
                f"evaluation policy {policy_id} version {policy_version} was not found"
            )
        return _load_policy_row(row)

    @staticmethod
    def _insert_policy(connection: Connection, policy: FrozenEvaluationPolicy) -> None:
        payload = _policy_payload(policy)
        canonical_json, normalized = _artifact_payload(
            PHASE5_POLICY_HASH_DOMAIN,
            payload,
            policy.policy_sha256,
        )
        feature = policy.feature_specification
        label = policy.label_specification
        _insert_row(
            connection,
            "evaluation_policies",
            {
                "policy_id": policy.policy_id,
                "policy_version": policy.policy_version,
                "schema_version": policy.schema_version,
                "policy_sha256": policy.policy_sha256,
                "strategy_family": policy.strategy_family.value,
                "selection_scope": policy.selection_scope,
                "approved_by": policy.approved_by,
                "synthetic_fixture_policy": policy.synthetic_fixture_policy,
                "signal_specification": canonicalize(policy.signal_specification),
                "forecast_horizon": policy.signal_specification.forecast_horizon,
                "required_snapshot_capabilities": [
                    item.value for item in policy.required_snapshot_capabilities
                ],
                "label_interval_rule": label.information_interval_rule,
                "transaction_cost_model": canonicalize(policy.costs),
                "slippage_model": policy.costs.slippage_model_id,
                "walk_forward_geometry": canonicalize(policy.walk_forward),
                "risk_limits": canonicalize(policy.risk),
                "selection_policy": canonicalize(policy.selection),
                "sample_adequacy_policy": canonicalize(policy.sample_adequacy),
                "missing_return_policy": label.missing_return_policy.value,
                "no_trade_return_policy": label.no_trade_return_policy.value,
                "regime_policy": canonicalize(policy.regimes),
                "reproducibility_policy": canonicalize(policy.audit),
                "cost_stress_multiplier": policy.stress.all_cost_multiplier,
                "expected_feature_spec_count": 1,
                "expected_label_spec_count": 1,
                "feature_spec_hashes": [feature.content_sha256],
                "label_spec_hashes": [label.content_sha256],
                "canonical_json": canonical_json,
                "payload": normalized,
            },
            json_columns=frozenset(
                {
                    "signal_specification",
                    "required_snapshot_capabilities",
                    "transaction_cost_model",
                    "walk_forward_geometry",
                    "risk_limits",
                    "selection_policy",
                    "sample_adequacy_policy",
                    "regime_policy",
                    "reproducibility_policy",
                    "feature_spec_hashes",
                    "label_spec_hashes",
                    "payload",
                }
            ),
        )

        feature_payload = _feature_payload(policy)
        feature_json, normalized_feature = _artifact_payload(
            PHASE5_FEATURE_HASH_DOMAIN,
            feature_payload,
            feature.content_sha256,
        )
        _insert_row(
            connection,
            "evaluation_feature_specs",
            {
                "feature_spec_id": feature.feature_specification_id,
                "feature_spec_sha256": feature.content_sha256,
                "policy_id": policy.policy_id,
                "policy_version": policy.policy_version,
                "policy_sha256": policy.policy_sha256,
                "ordinal": 0,
                "feature_name": feature.formula_id,
                "feature_schema_version": feature.schema_version,
                "information_interval": {
                    "lookback_rule": feature.lookback_rule,
                    "availability_rule": feature.availability_rule,
                },
                "required_capabilities": [
                    item.value for item in policy.required_snapshot_capabilities
                ],
                "canonical_json": feature_json,
                "payload": normalized_feature,
            },
            json_columns=frozenset({"information_interval", "required_capabilities", "payload"}),
        )

        label_payload = _label_payload(policy)
        label_json, normalized_label = _artifact_payload(
            PHASE5_LABEL_HASH_DOMAIN,
            label_payload,
            label.content_sha256,
        )
        _insert_row(
            connection,
            "evaluation_label_specs",
            {
                "label_spec_id": label.label_specification_id,
                "label_spec_sha256": label.content_sha256,
                "policy_id": policy.policy_id,
                "policy_version": policy.policy_version,
                "policy_sha256": policy.policy_sha256,
                "ordinal": 0,
                "label_name": label.formula_id,
                "label_schema_version": label.schema_version,
                "information_interval": {
                    "rule": label.information_interval_rule,
                    "missing_return_policy": label.missing_return_policy,
                    "no_trade_return_policy": label.no_trade_return_policy,
                    "delisting_return_policy": label.delisting_return_policy,
                },
                "forecast_horizon": {"value": label.forecast_horizon},
                "canonical_json": label_json,
                "payload": normalized_label,
            },
            json_columns=frozenset({"information_interval", "forecast_horizon", "payload"}),
        )

    def create_policy(self, policy: FrozenEvaluationPolicy) -> FrozenEvaluationPolicy:
        try:
            with self.engine.begin() as connection:
                lock_key = f"{policy.policy_id}:{policy.policy_version}"
                connection.execute(
                    text("SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"),
                    {"lock_key": lock_key},
                )
                existing = self._policy_row(
                    connection,
                    policy.policy_id,
                    policy.policy_version,
                )
                if existing is not None:
                    loaded = _load_policy_row(existing)
                    if loaded.policy_sha256 != policy.policy_sha256:
                        raise EvaluationWorkflowConflict(
                            "policy identity is already bound to different immutable content"
                        )
                    return loaded
                self._insert_policy(connection, policy)
                return self._load_policy(
                    connection,
                    policy.policy_id,
                    policy.policy_version,
                )
        except (EvaluationWorkflowConflict, EvaluationPolicyNotFound):
            raise
        except (DBAPIError, IntegrityError) as exc:
            raise EvaluationWorkflowConflict(
                "immutable evaluation policy could not be stored"
            ) from exc

    def get_policy(self, policy_id: UUID, policy_version: int) -> FrozenEvaluationPolicy:
        with self.engine.connect() as connection:
            return self._load_policy(connection, policy_id, policy_version)

    def list_policies(self, *, limit: int) -> list[FrozenEvaluationPolicy]:
        if limit < 1 or limit > 100:
            raise ValueError("policy list limit must be between 1 and 100")
        with self.engine.connect() as connection:
            rows = connection.execute(
                text(
                    "SELECT * FROM evaluation_policies "
                    "ORDER BY created_at_utc DESC, policy_id, policy_version DESC LIMIT :limit"
                ),
                {"limit": limit},
            ).mappings()
            return [_load_policy_row(row) for row in rows]

    @staticmethod
    def _report_row(connection: Connection, artifact_id: UUID) -> RowMapping | None:
        return (
            connection.execute(
                text("SELECT * FROM evaluation_reports WHERE report_id = :report_id"),
                {"report_id": artifact_id},
            )
            .mappings()
            .one_or_none()
        )

    @staticmethod
    def _report_by_fingerprint(connection: Connection, fingerprint: str) -> RowMapping | None:
        return (
            connection.execute(
                text(
                    "SELECT * FROM evaluation_reports WHERE run_fingerprint_sha256 = :fingerprint"
                ),
                {"fingerprint": fingerprint},
            )
            .mappings()
            .one_or_none()
        )

    @classmethod
    def _load_report(cls, connection: Connection, artifact_id: UUID) -> EvaluationReport:
        row = cls._report_row(connection, artifact_id)
        if row is None:
            raise EvaluationReportNotFound(f"evaluation report {artifact_id} was not found")
        return _load_report_row(row)

    @staticmethod
    def _insert_report(connection: Connection, report: EvaluationReport) -> None:
        report_payload = evaluation_report_hash_payload(report)
        report_json, normalized_report = _artifact_payload(
            PHASE5_ARTIFACT_HASH_DOMAIN,
            report_payload,
            report.artifact_sha256,
        )
        request_payload = evaluation_request_payload_from_report(report)
        request_json = canonical_json_text(request_payload)
        if domain_sha256(PHASE5_REQUEST_HASH_DOMAIN, request_payload) != (
            report.request_fingerprint_sha256
        ):
            raise EvaluationWorkflowConflict("run fingerprint does not match report")
        if domain_sha256(PHASE5_CONFIG_HASH_DOMAIN, request_payload) != report.config_hash:
            raise EvaluationWorkflowConflict("configuration hash does not match report")
        snapshot_payload = tuple(item.model_dump(mode="python") for item in report.data_snapshots)
        snapshot_json = canonical_json_text(snapshot_payload)
        if domain_sha256(PHASE5_SNAPSHOT_BUNDLE_HASH_DOMAIN, snapshot_payload) != (
            report.snapshot_bundle_sha256
        ):
            raise EvaluationWorkflowConflict("snapshot bundle hash does not match report")
        source_observations = canonicalize(report.source_observations)
        sample_lineage = canonicalize(report.sample_lineage)
        sample_lineage_json = canonical_json_text(report.sample_lineage)
        if domain_sha256(PHASE5_SAMPLE_LINEAGE_HASH_DOMAIN, report.sample_lineage) != (
            report.sample_lineage_sha256
        ):
            raise EvaluationWorkflowConflict("sample lineage hash does not match report")
        _insert_row(
            connection,
            "evaluation_reports",
            {
                "report_id": report.artifact_id,
                "report_sha256": report.artifact_sha256,
                "report_schema_version": report.artifact_schema_version,
                "run_fingerprint_sha256": report.request_fingerprint_sha256,
                "run_fingerprint_canonical_json": request_json,
                "run_fingerprint_payload": canonicalize(request_payload),
                "policy_id": report.evaluation_policy_id,
                "policy_version": report.evaluation_policy_version,
                "policy_sha256": report.evaluation_policy_sha256,
                "mapping_id": report.mapping_id,
                "mapping_version": report.mapping_version,
                "mapping_input_sha256": report.mapping_input_sha256,
                "configuration_sha256": report.config_hash,
                "fixture_id": report.fixture_id,
                "fixture_sha256": report.fixture_sha256,
                "snapshot_bundle_sha256": report.snapshot_bundle_sha256,
                "snapshot_bundle_canonical_json": snapshot_json,
                "sample_lineage_sha256": report.sample_lineage_sha256,
                "sample_lineage_canonical_json": sample_lineage_json,
                "source_observations": source_observations,
                "sample_lineage": sample_lineage,
                "git_sha": report.code_version_git_sha,
                "random_seed": report.random_seed,
                "decision_time_utc": report.decision_time_utc,
                "raw_trial_count": report.raw_trial_count,
                "effective_trial_count": report.effective_trial_count,
                "effective_trial_count_method": report.effective_trial_method,
                "synthetic": report.synthetic,
                "no_real_performance_claim": report.no_real_performance_claimed,
                "state": report.promotion_state.value,
                "expected_snapshot_count": len(report.data_snapshots),
                "expected_source_observation_count": len(report.source_observations),
                "expected_sample_lineage_count": len(report.sample_lineage),
                "expected_trial_count": len(report.trials),
                "expected_fold_count": len(report.folds),
                "expected_preprocessing_fit_count": len(report.preprocessing_fits),
                "expected_oos_ledger_count": len(report.oos_ledger),
                "expected_cost_ledger_count": len(report.cost_ledger),
                "expected_gate_result_count": len(report.gates),
                "canonical_json": report_json,
                "payload": normalized_report,
            },
            json_columns=frozenset(
                {
                    "run_fingerprint_payload",
                    "source_observations",
                    "sample_lineage",
                    "payload",
                }
            ),
        )

        for ordinal, evidence in enumerate(report.data_snapshots):
            binding_payload = {
                "report_id": report.artifact_id,
                "ordinal": ordinal,
                "snapshot_evidence": evidence,
            }
            binding_sha = domain_sha256(
                PHASE5_REPORT_SNAPSHOT_HASH_DOMAIN,
                binding_payload,
            )
            binding_json, normalized_binding = _artifact_payload(
                PHASE5_REPORT_SNAPSHOT_HASH_DOMAIN,
                binding_payload,
                binding_sha,
            )
            first_schema = evidence.dataset_schema_versions[0].split(":", maxsplit=1)
            if len(first_schema) != 2:
                raise EvaluationWorkflowConflict("snapshot schema identity is malformed")
            _insert_row(
                connection,
                "evaluation_report_snapshots",
                {
                    "report_snapshot_id": identity(
                        PHASE5_REPORT_SNAPSHOT_NAMESPACE,
                        binding_sha,
                    ),
                    "report_snapshot_sha256": binding_sha,
                    "report_id": report.artifact_id,
                    "report_sha256": report.artifact_sha256,
                    "ordinal": ordinal,
                    "snapshot_id": evidence.snapshot_id,
                    "snapshot_sha256": evidence.snapshot_sha256,
                    "capability": evidence.capability.value,
                    "as_of_utc": evidence.as_of_utc,
                    "provider_id": evidence.provider_id,
                    "adapter_id": evidence.adapter_id,
                    "adapter_version": evidence.adapter_version,
                    "dataset_id": evidence.dataset_id,
                    "product_id": evidence.product_id,
                    "dataset_schema_id": first_schema[0],
                    "dataset_schema_version": first_schema[1],
                    "dataset_schema_versions": list(evidence.dataset_schema_versions),
                    "quality_status": evidence.quality_status,
                    "fixture_set_version": evidence.fixture_set_version,
                    "canonical_json": binding_json,
                    "payload": normalized_binding,
                },
                json_columns=frozenset({"dataset_schema_versions", "payload"}),
            )

        for trial in report.trials:
            payload = trial.model_dump(mode="python", exclude={"trial_id", "trial_sha256"})
            canonical_json, normalized = _artifact_payload(
                PHASE5_TRIAL_HASH_DOMAIN,
                payload,
                trial.trial_sha256,
            )
            _insert_row(
                connection,
                "evaluation_trials",
                {
                    "trial_id": trial.trial_id,
                    "trial_sha256": trial.trial_sha256,
                    "report_id": report.artifact_id,
                    "report_sha256": report.artifact_sha256,
                    "ordinal": trial.ordinal,
                    "trial_key": trial.trial_key,
                    "strategy_family": trial.strategy_family.value,
                    "selection_scope": trial.selection_scope,
                    "initiated_by": trial.initiated_by,
                    "initiated_at_utc": trial.initiated_at_utc,
                    "status": trial.status.value,
                    "oos_return_state": trial.oos_return_state,
                    "net_returns": canonicalize(trial.net_returns),
                    "return_statuses": canonicalize(trial.return_statuses),
                    "return_timestamps_utc": canonicalize(trial.return_timestamps_utc),
                    "return_observation_count": len(trial.net_returns),
                    "missing_return_count": sum(
                        status is ResearchReturnStatus.MISSING for status in trial.return_statuses
                    ),
                    "no_trade_count": sum(
                        status is ResearchReturnStatus.NO_TRADE for status in trial.return_statuses
                    ),
                    "config_sha256": trial.config_sha256,
                    "config_canonical_json": canonical_json_text(trial.config_preimage),
                    "config_preimage": canonicalize(trial.config_preimage),
                    "configuration": canonicalize(trial.configuration),
                    "failure_reason": trial.failure_reason,
                    "canonical_json": canonical_json,
                    "payload": normalized,
                },
                json_columns=frozenset(
                    {
                        "net_returns",
                        "return_statuses",
                        "return_timestamps_utc",
                        "config_preimage",
                        "configuration",
                        "payload",
                    }
                ),
            )

        for fold in report.folds:
            payload = fold.model_dump(mode="python", exclude={"fold_id", "fold_sha256"})
            canonical_json, normalized = _artifact_payload(
                PHASE5_FOLD_HASH_DOMAIN,
                payload,
                fold.fold_sha256,
            )
            _insert_row(
                connection,
                "evaluation_folds",
                {
                    "fold_id": fold.fold_id,
                    "fold_sha256": fold.fold_sha256,
                    "report_id": report.artifact_id,
                    "report_sha256": report.artifact_sha256,
                    "ordinal": fold.ordinal,
                    "fold_kind": fold.fold_kind.value,
                    "parent_fold_id": fold.parent_fold_id,
                    "train_start_utc": fold.train_start_utc,
                    "train_end_utc": fold.train_end_utc,
                    "test_start_utc": fold.test_start_utc,
                    "test_end_utc": fold.test_end_utc,
                    "training_row_count": len(fold.train_sample_ids),
                    "test_row_count": len(fold.test_sample_ids),
                    "purged_row_count": len(fold.purged_sample_ids),
                    "embargoed_row_count": len(fold.embargoed_sample_ids),
                    "embargo_duration_seconds": fold.embargo_duration_seconds,
                    "embargo_applied": fold.embargo_applied,
                    "canonical_json": canonical_json,
                    "payload": normalized,
                },
                json_columns=frozenset({"payload"}),
            )

        for ordinal, fit in enumerate(report.preprocessing_fits):
            payload = {
                "fit_sha256": fit.fit_sha256,
                "mean": fit.mean,
                "standard_deviation": fit.standard_deviation,
                "ddof": fit.ddof,
            }
            canonical_json, normalized = _artifact_payload(
                PHASE5_FIT_HASH_DOMAIN,
                payload,
                fit.statistics_sha256,
            )
            _insert_row(
                connection,
                "evaluation_preprocessing_fits",
                {
                    "fit_id": fit.fit_id,
                    "fit_sha256": fit.fit_sha256,
                    "statistics_sha256": fit.statistics_sha256,
                    "report_id": report.artifact_id,
                    "report_sha256": report.artifact_sha256,
                    "fold_id": fit.fold_id,
                    "ordinal": ordinal,
                    "transformer_id": fit.transformer_id,
                    "transformer_version": fit.transformer_version,
                    "training_row_count": len(fit.train_sample_ids),
                    "train_sample_ids": list(fit.train_sample_ids),
                    "train_sample_ids_sha256": fit.train_sample_ids_sha256,
                    "mean": fit.mean,
                    "standard_deviation": fit.standard_deviation,
                    "ddof": fit.ddof,
                    "record_payload": canonicalize(fit),
                    "canonical_json": canonical_json,
                    "payload": normalized,
                },
                json_columns=frozenset({"train_sample_ids", "record_payload", "payload"}),
            )

        for oos_entry in report.oos_ledger:
            payload = oos_entry.model_dump(
                mode="python",
                exclude={"ledger_entry_id", "ledger_entry_sha256"},
            )
            canonical_json, normalized = _artifact_payload(
                PHASE5_LEDGER_HASH_DOMAIN,
                payload,
                oos_entry.ledger_entry_sha256,
            )
            _insert_row(
                connection,
                "evaluation_oos_ledger",
                {
                    "oos_entry_id": oos_entry.ledger_entry_id,
                    "oos_entry_sha256": oos_entry.ledger_entry_sha256,
                    "report_id": report.artifact_id,
                    "report_sha256": report.artifact_sha256,
                    "trial_id": oos_entry.trial_id,
                    "fold_id": oos_entry.fold_id,
                    "ordinal": oos_entry.ordinal,
                    "sample_id": oos_entry.sample_id,
                    "sample_sha256": oos_entry.sample_sha256,
                    "source_observation_refs": canonicalize(oos_entry.source_observation_refs),
                    "information_start_utc": oos_entry.information_start_utc,
                    "information_end_utc": oos_entry.information_end_utc,
                    "decision_time_utc": oos_entry.decision_time_utc,
                    "label_t0_utc": oos_entry.label_t0_utc,
                    "label_t1_utc": oos_entry.label_t1_utc,
                    "prediction_value": oos_entry.predicted_value,
                    "gross_return": oos_entry.gross_return,
                    "baseline_net_return": oos_entry.baseline_net_return,
                    "return_status": oos_entry.return_status.value,
                    "delisting_return_handled": oos_entry.delisting_return_handled,
                    "canonical_json": canonical_json,
                    "payload": normalized,
                },
                json_columns=frozenset({"source_observation_refs", "payload"}),
            )

        baseline = {
            item.sample_id: item
            for item in report.cost_ledger
            if item.scenario is CostScenario.BASELINE
        }
        for cost_entry in report.cost_ledger:
            payload = cost_entry.model_dump(
                mode="python",
                exclude={"cost_entry_id", "cost_entry_sha256"},
            )
            canonical_json, normalized = _artifact_payload(
                PHASE5_COST_HASH_DOMAIN,
                payload,
                cost_entry.cost_entry_sha256,
            )
            if cost_entry.scenario is CostScenario.BASELINE:
                stress_multiplier = Decimal("1")
            elif cost_entry.scenario is CostScenario.ALL_COST_STRESS:
                stress_multiplier = cast(
                    Decimal,
                    next(
                        gate.inputs["all_cost_multiplier"]
                        for gate in report.gates
                        if gate.gate_code.value == "COST_STRESS"
                    ),
                )
            else:
                base = baseline[cost_entry.sample_id]
                ratios = [
                    stressed / original
                    for stressed, original in (
                        (cost_entry.spread_cost, base.spread_cost),
                        (cost_entry.impact_cost, base.impact_cost),
                        (cost_entry.latency_cost, base.latency_cost),
                        (cost_entry.borrow_cost, base.borrow_cost),
                        (cost_entry.participation_rate, base.participation_rate),
                    )
                    if original > 0
                ]
                stress_multiplier = max(ratios, default=Decimal("1.00000001"))
            _insert_row(
                connection,
                "evaluation_cost_ledger",
                {
                    "cost_entry_id": cost_entry.cost_entry_id,
                    "cost_entry_sha256": cost_entry.cost_entry_sha256,
                    "report_id": report.artifact_id,
                    "report_sha256": report.artifact_sha256,
                    "ordinal": cost_entry.ordinal,
                    "sample_id": cost_entry.sample_id,
                    "scenario": cost_entry.scenario.value,
                    "allocation_input_sha256": cost_entry.allocation_input_sha256,
                    "return_status": cost_entry.return_status.value,
                    "stress_multiplier": stress_multiplier,
                    "requested_quantity": cost_entry.requested_quantity,
                    "filled_quantity": cost_entry.filled_quantity,
                    "rejected_quantity": cost_entry.rejected_quantity,
                    "unfilled_quantity": cost_entry.unfilled_quantity,
                    "fill_status": cost_entry.fill_status,
                    "hard_to_borrow_available": cost_entry.hard_to_borrow_available,
                    "gross_return": cost_entry.gross_return,
                    "fee_cost": cost_entry.fee_cost,
                    "spread_cost": cost_entry.spread_cost,
                    "impact_cost": cost_entry.impact_cost,
                    "latency_cost": cost_entry.latency_cost,
                    "borrow_cost": cost_entry.borrow_cost,
                    "capacity_cost": cost_entry.capacity_cost,
                    "total_cost": cost_entry.total_cost,
                    "net_return": cost_entry.net_return,
                    "participation_rate": cost_entry.participation_rate,
                    "capacity_breached": cost_entry.capacity_breached,
                    "canonical_json": canonical_json,
                    "payload": normalized,
                },
                json_columns=frozenset({"payload"}),
            )

        for gate in report.gates:
            payload = gate.model_dump(
                mode="python",
                exclude={"gate_result_id", "gate_result_sha256"},
            )
            canonical_json, normalized = _artifact_payload(
                PHASE5_GATE_HASH_DOMAIN,
                payload,
                gate.gate_result_sha256,
            )
            numerics = (
                Decimal(str(value))
                for value in gate.results.values()
                if isinstance(value, (int, Decimal)) and not isinstance(value, bool)
            )
            thresholds = (
                Decimal(str(value))
                for value in gate.thresholds.values()
                if isinstance(value, (int, Decimal)) and not isinstance(value, bool)
            )
            outcome = gate.outcome
            _insert_row(
                connection,
                "evaluation_gate_results",
                {
                    "gate_result_id": gate.gate_result_id,
                    "gate_result_sha256": gate.gate_result_sha256,
                    "report_id": report.artifact_id,
                    "report_sha256": report.artifact_sha256,
                    "ordinal": gate.ordinal,
                    "config_hash": gate.config_hash,
                    "gate_code": gate.gate_code.value,
                    "outcome": outcome.value,
                    "computable": outcome
                    not in {
                        GateOutcome.BLOCKED_MISSING_POLICY,
                        GateOutcome.BLOCKED_UNCOMPUTABLE,
                    },
                    "passed": outcome is GateOutcome.PASS,
                    "blocking": outcome
                    in {
                        GateOutcome.FAIL,
                        GateOutcome.BLOCKED_MISSING_POLICY,
                        GateOutcome.BLOCKED_UNCOMPUTABLE,
                    },
                    "reason_codes": list(gate.reason_codes),
                    "metric_value": next(numerics, None),
                    "threshold_value": next(thresholds, None),
                    "canonical_json": canonical_json,
                    "payload": normalized,
                },
                json_columns=frozenset({"reason_codes", "payload"}),
            )

    def create_report(self, report: EvaluationReport) -> EvaluationReport:
        try:
            with self.engine.begin() as connection:
                connection.execute(
                    text("SELECT pg_advisory_xact_lock(hashtextextended(:fingerprint, 0))"),
                    {"fingerprint": report.request_fingerprint_sha256},
                )
                existing = self._report_by_fingerprint(
                    connection,
                    report.request_fingerprint_sha256,
                )
                if existing is not None:
                    loaded = _load_report_row(existing)
                    if loaded.artifact_sha256 != report.artifact_sha256:
                        raise EvaluationWorkflowConflict(
                            "run fingerprint is already bound to a different immutable report"
                        )
                    return loaded
                self._insert_report(connection, report)
                return self._load_report(connection, report.artifact_id)
        except (EvaluationWorkflowConflict, EvaluationReportNotFound):
            raise
        except (DBAPIError, IntegrityError) as exc:
            raise EvaluationWorkflowConflict(
                "immutable evaluation report could not be stored"
            ) from exc

    def get_report(self, artifact_id: UUID) -> EvaluationReport:
        with self.engine.connect() as connection:
            return self._load_report(connection, artifact_id)

    def list_reports(self, *, limit: int) -> list[EvaluationReportSummary]:
        if limit < 1 or limit > 100:
            raise ValueError("report list limit must be between 1 and 100")
        with self.engine.connect() as connection:
            rows = connection.execute(
                text(
                    "SELECT * FROM evaluation_reports "
                    "ORDER BY created_at_utc DESC, report_id DESC LIMIT :limit"
                ),
                {"limit": limit},
            ).mappings()
            return [
                EvaluationReportSummary(
                    artifact_id=row["report_id"],
                    artifact_sha256=row["report_sha256"],
                    fixture_id=row["fixture_id"],
                    promotion_state=row["state"],
                    created_at_utc=row["created_at_utc"],
                    warning_count=len(row["payload"].get("warnings", [])),
                    reason_codes=tuple(row["payload"].get("reason_codes", [])),
                )
                for row in rows
            ]

    @staticmethod
    def _outcome_row(connection: Connection, outcome_id: UUID) -> RowMapping | None:
        return (
            connection.execute(
                text("SELECT * FROM evaluation_blocked_outcomes WHERE outcome_id = :outcome_id"),
                {"outcome_id": outcome_id},
            )
            .mappings()
            .one_or_none()
        )

    @staticmethod
    def _outcome_by_idempotency(
        connection: Connection,
        idempotency_sha256: str,
    ) -> RowMapping | None:
        return (
            connection.execute(
                text(
                    "SELECT * FROM evaluation_blocked_outcomes "
                    "WHERE idempotency_sha256 = :idempotency_sha256"
                ),
                {"idempotency_sha256": idempotency_sha256},
            )
            .mappings()
            .one_or_none()
        )

    @classmethod
    def _load_outcome(
        cls,
        connection: Connection,
        outcome_id: UUID,
    ) -> BlockedEvaluationOutcome:
        row = cls._outcome_row(connection, outcome_id)
        if row is None:
            raise EvaluationOutcomeNotFound(
                f"blocked evaluation outcome {outcome_id} was not found"
            )
        return _load_outcome_row(row)

    @staticmethod
    def _insert_outcome(
        connection: Connection,
        outcome: BlockedEvaluationOutcome,
    ) -> None:
        payload = blocked_outcome_hash_payload(outcome)
        canonical_json, normalized = _artifact_payload(
            PHASE5_BLOCKED_OUTCOME_HASH_DOMAIN,
            payload,
            outcome.outcome_sha256,
        )
        idempotency_payload = blocked_outcome_idempotency_payload(outcome)
        idempotency_json, normalized_idempotency = _artifact_payload(
            PHASE5_BLOCKED_OUTCOME_IDEMPOTENCY_HASH_DOMAIN,
            idempotency_payload,
            outcome.idempotency_sha256,
        )
        request = evaluation_request_from_outcome(outcome)
        request_payload = request.model_dump(mode="python")
        request_json = canonical_json_text(request_payload)
        if (
            domain_sha256(
                PHASE5_BLOCKED_SUBMISSION_HASH_DOMAIN,
                request_payload,
            )
            != outcome.submission_sha256
        ):
            raise EvaluationWorkflowConflict("blocked submission hash does not match request")
        _insert_row(
            connection,
            "evaluation_blocked_outcomes",
            {
                "outcome_id": outcome.outcome_id,
                "outcome_sha256": outcome.outcome_sha256,
                "idempotency_sha256": outcome.idempotency_sha256,
                "idempotency_canonical_json": idempotency_json,
                "idempotency_payload": normalized_idempotency,
                "schema_version": outcome.schema_version,
                "submission_sha256": outcome.submission_sha256,
                "submission_canonical_json": request_json,
                "submission_payload": canonicalize(request_payload),
                "policy_id": outcome.policy_id,
                "policy_version": outcome.policy_version,
                "mapping_id": outcome.mapping_id,
                "snapshot_ids": canonicalize(outcome.snapshot_ids),
                "fixture_id": outcome.fixture_id,
                "resolved_policy_sha256": outcome.resolved_policy_sha256,
                "resolved_fixture_sha256": outcome.resolved_fixture_sha256,
                "resolved_fixture_random_seed": outcome.resolved_fixture_random_seed,
                "resolved_raw_trial_count": outcome.resolved_raw_trial_count,
                "resolved_snapshots": canonicalize(outcome.resolved_snapshots),
                "git_sha": outcome.code_version_git_sha,
                "failure_stage": outcome.failure_stage.value,
                "state": outcome.promotion_state.value,
                "reason_codes": list(outcome.reason_codes),
                "synthetic": outcome.synthetic,
                "no_real_performance_claim": outcome.no_real_performance_claimed,
                "canonical_json": canonical_json,
                "payload": normalized,
                "created_at_utc": outcome.created_at_utc,
            },
            json_columns=frozenset(
                {
                    "idempotency_payload",
                    "submission_payload",
                    "snapshot_ids",
                    "resolved_snapshots",
                    "reason_codes",
                    "payload",
                }
            ),
        )

    def create_outcome(
        self,
        outcome: BlockedEvaluationOutcome,
    ) -> BlockedEvaluationOutcome:
        try:
            with self.engine.begin() as connection:
                connection.execute(
                    text("SELECT pg_advisory_xact_lock(hashtextextended(:hash, 0))"),
                    {"hash": outcome.idempotency_sha256},
                )
                existing = self._outcome_by_idempotency(
                    connection,
                    outcome.idempotency_sha256,
                )
                if existing is not None:
                    loaded = _load_outcome_row(existing)
                    if canonical_json_text(
                        blocked_outcome_idempotency_payload(loaded)
                    ) != canonical_json_text(blocked_outcome_idempotency_payload(outcome)):
                        raise EvaluationWorkflowConflict(
                            "blocked outcome idempotency hash is bound to different evidence"
                        )
                    return loaded
                self._insert_outcome(connection, outcome)
                return self._load_outcome(connection, outcome.outcome_id)
        except (EvaluationWorkflowConflict, EvaluationOutcomeNotFound):
            raise
        except (DBAPIError, IntegrityError) as exc:
            raise EvaluationWorkflowConflict(
                "immutable blocked evaluation outcome could not be stored"
            ) from exc

    def get_outcome(self, outcome_id: UUID) -> BlockedEvaluationOutcome:
        with self.engine.connect() as connection:
            return self._load_outcome(connection, outcome_id)

    def list_outcomes(self, *, limit: int) -> list[BlockedEvaluationOutcome]:
        if limit < 1 or limit > 100:
            raise ValueError("blocked outcome list limit must be between 1 and 100")
        with self.engine.connect() as connection:
            rows = connection.execute(
                text(
                    "SELECT * FROM evaluation_blocked_outcomes "
                    "ORDER BY created_at_utc DESC, outcome_id DESC LIMIT :limit"
                ),
                {"limit": limit},
            ).mappings()
            return [_load_outcome_row(row) for row in rows]


__all__ = ["EvaluationRepository"]
