"""Append-only PostgreSQL persistence for Phase 6 research artifacts."""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

from fable5_data.canonical import canonical_json_bytes, canonicalize, domain_sha256
from pydantic import BaseModel
from sqlalchemy import Engine, bindparam, create_engine, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import Connection, RowMapping
from sqlalchemy.exc import DBAPIError

from fable5_research.canonical import PHASE6_ARTIFACT_HASH_DOMAIN
from fable5_research.contracts import (
    FamilyCEvidence,
    ResearchAttempt,
    ResearchBaselineComparison,
    ResearchFeatureRow,
    ResearchRunArtifact,
    ResearchRunSummary,
    ResearchScoreOutput,
    ResearchSnapshotBinding,
    SocialOfficialCorroboration,
    TextFeatureExtraction,
)


class ResearchRunNotFound(LookupError):
    """The requested immutable Phase 6 research run does not exist."""


class ResearchRepositoryConflict(RuntimeError):
    """Persisted Phase 6 evidence conflicts with its canonical artifact."""


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


def _normalized_object(value: object) -> dict[str, Any]:
    normalized = canonicalize(value)
    if not isinstance(normalized, dict):
        raise ResearchRepositoryConflict("immutable Phase 6 payload must be an object")
    return cast(dict[str, Any], normalized)


def _model_payload(model: BaseModel) -> dict[str, Any]:
    return _normalized_object(model.model_dump(mode="python"))


def _artifact_payload(artifact: ResearchRunArtifact) -> dict[str, Any]:
    payload = artifact.model_dump(
        mode="python",
        exclude={"run_id", "artifact_sha256", "created_at_utc"},
    )
    if domain_sha256(PHASE6_ARTIFACT_HASH_DOMAIN, payload) != artifact.artifact_sha256:
        raise ResearchRepositoryConflict("immutable Phase 6 artifact hash does not match payload")
    return _normalized_object(payload)


def _same(left: object, right: object) -> bool:
    return canonical_json_bytes(left) == canonical_json_bytes(right)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ResearchRepositoryConflict(message)


def _load_child_payloads(
    connection: Connection,
    *,
    table: str,
    run_id: UUID,
) -> list[RowMapping]:
    return list(
        connection.execute(
            text(f"SELECT * FROM {table} WHERE run_id = :run_id ORDER BY ordinal"),
            {"run_id": run_id},
        ).mappings()
    )


def _validate_binding_row(row: RowMapping) -> ResearchSnapshotBinding:
    item = ResearchSnapshotBinding.model_validate(dict(row["payload"]))
    _require(
        row["ordinal"] == item.ordinal
        and row["snapshot_id"] == item.snapshot_id
        and row["snapshot_sha256"] == item.snapshot_sha256
        and row["capability"] == item.capability.value
        and row["binding_sha256"] == item.binding_sha256,
        "persisted Phase 6 snapshot binding columns conflict with payload",
    )
    return item


def _validate_attempt_row(
    row: RowMapping,
    *,
    phase5_report_id: UUID | None,
) -> ResearchAttempt:
    item = ResearchAttempt.model_validate(dict(row["payload"]))
    _require(
        row["ordinal"] == item.ordinal
        and row["phase5_report_id"] == phase5_report_id
        and row["phase5_trial_id"] == item.phase5_trial_id
        and row["phase5_trial_key"] == item.phase5_trial_key
        and row["status"] == item.status.value
        and row["config_sha256"] == item.configuration_sha256
        and row["failure_reason"] == item.failure_reason
        and row["attempt_sha256"] == item.attempt_sha256,
        "persisted Phase 6 attempt columns conflict with payload",
    )
    return item


def _validate_feature_row(row: RowMapping) -> ResearchFeatureRow:
    item = ResearchFeatureRow.model_validate(dict(row["payload"]))
    _require(
        row["ordinal"] == item.ordinal
        and row["row_id"] == item.row_id
        and row["sample_id"] == item.sample_id
        and row["entity_id"] == item.entity_id
        and row["decision_time_utc"] == item.decision_time_utc
        and row["row_sha256"] == item.row_sha256,
        "persisted Phase 6 feature-row columns conflict with payload",
    )
    return item


def _validate_score_row(row: RowMapping) -> ResearchScoreOutput:
    item = ResearchScoreOutput.model_validate(dict(row["payload"]))
    _require(
        row["ordinal"] == item.ordinal
        and row["score_id"] == item.score_id
        and row["sample_id"] == item.sample_id
        and row["model_id"] == item.model_id
        and Decimal(row["research_score"]) == item.research_score
        and row["explanation_sha256"] == item.explanation_sha256
        and row["output_sha256"] == item.output_sha256,
        "persisted Phase 6 score columns conflict with payload",
    )
    return item


def _validate_comparison_row(row: RowMapping) -> ResearchBaselineComparison:
    item = ResearchBaselineComparison.model_validate(dict(row["payload"]))
    _require(
        row["ordinal"] == item.ordinal
        and row["comparison_id"] == item.comparison_id
        and row["candidate_model_id"] == item.candidate_model_id
        and row["baseline_model_id"] == item.baseline_model_id
        and row["outcome"] == item.outcome.value
        and row["comparison_sha256"] == item.comparison_sha256,
        "persisted Phase 6 baseline-comparison columns conflict with payload",
    )
    return item


def _validate_extraction_row(row: RowMapping) -> TextFeatureExtraction:
    item = TextFeatureExtraction.model_validate(dict(row["payload"]))
    _require(
        row["ordinal"] == item.ordinal
        and row["extraction_id"] == item.extraction_id
        and row["source_version_id"] == item.official_source_version_id
        and row["document_sha256"] == item.document_content_sha256
        and row["extractor_id"] == item.extractor_id
        and row["extractor_version"] == item.extractor_version
        and row["model_id"] == item.model_id
        and row["prompt_version"] == item.prompt_version
        and row["schema_version"] == item.schema_version
        and row["extraction_sha256"] == item.extraction_sha256,
        "persisted Phase 6 text-extraction columns conflict with payload",
    )
    return item


def _validate_corroboration_row(row: RowMapping) -> SocialOfficialCorroboration:
    item = SocialOfficialCorroboration.model_validate(dict(row["payload"]))
    _require(
        row["ordinal"] == item.ordinal
        and row["corroboration_id"] == item.corroboration_id
        and row["social_record_id"] == item.social_attention_record_id
        and row["official_source_version_id"] == item.official_source_version_id
        and row["official_document_sha256"] == item.official_document_sha256
        and row["corroboration_sha256"] == item.corroboration_sha256,
        "persisted Phase 6 corroboration columns conflict with payload",
    )
    return item


def _validate_root_columns(row: RowMapping, artifact: ResearchRunArtifact) -> None:
    evaluation = artifact.phase5_evaluation
    _require(
        row["schema_version"] == artifact.artifact_schema_version
        and row["request_fingerprint_sha256"] == artifact.request_fingerprint_sha256
        and row["artifact_sha256"] == artifact.artifact_sha256
        and row["configuration_id"] == artifact.configuration_id.value
        and row["configuration_sha256"] == artifact.configuration_sha256
        and row["mapping_id"] == artifact.mapping_id
        and row["canonical_family"] == artifact.family.value
        and row["specification_sha256"] == artifact.specification.specification_sha256
        and row["feature_lineage_sha256"] == artifact.feature_lineage_sha256
        and row["snapshot_bundle_sha256"] == artifact.snapshot_bundle_sha256
        and row["phase5_policy_id"] == evaluation.policy_id
        and row["phase5_policy_version"] == evaluation.policy_version
        and row["phase5_policy_sha256"] == evaluation.policy_sha256
        and row["phase5_fixture_id"] == evaluation.fixture_id
        and row["phase5_fixture_sha256"] == evaluation.fixture_sha256
        and row["evaluation_report_id"] == evaluation.evaluation_report_id
        and row["evaluation_outcome_id"] == evaluation.evaluation_outcome_id
        and row["promotion_state"] == evaluation.promotion_state.value
        and row["status"] == artifact.status.value
        and _same(row["reason_codes"], artifact.reason_codes)
        and _same(row["warnings"], artifact.warnings)
        and row["no_real_performance_claimed"] is artifact.no_real_performance_claimed
        and row["paper_approval_granted"] is artifact.paper_approval_granted,
        "persisted Phase 6 run columns conflict with canonical artifact payload",
    )


def _summary_from_row(row: RowMapping) -> ResearchRunSummary:
    _require(
        row["synthetic"] is True
        and row["no_real_performance_claimed"] is True
        and row["pass_research_is_not_paper_approval"] is True
        and row["paper_approval_granted"] is False,
        "persisted Phase 6 run summary exceeded its research-only boundary",
    )
    return ResearchRunSummary.model_validate(
        {
            "run_id": row["id"],
            "artifact_sha256": row["artifact_sha256"],
            "configuration_id": row["configuration_id"],
            "family": row["canonical_family"],
            "promotion_state": row["promotion_state"],
            "status": row["status"],
            "synthetic": row["synthetic"],
            "no_real_performance_claimed": row["no_real_performance_claimed"],
            "pass_research_is_not_paper_approval": row["pass_research_is_not_paper_approval"],
            "created_at_utc": row["created_at_utc"],
            "reason_codes": row["reason_codes"],
        }
    )


class ResearchRepository:
    """Persist and reconstruct complete immutable Phase 6 research runs."""

    def __init__(self, database_url: str | None = None, *, engine: Engine | None = None) -> None:
        if database_url is None and engine is None:
            raise ValueError("database_url or engine is required")
        self.engine = engine or create_engine(str(database_url), pool_pre_ping=True)
        self._owns_engine = engine is None

    def dispose(self) -> None:
        if self._owns_engine:
            self.engine.dispose()

    @staticmethod
    def _run_row(connection: Connection, run_id: UUID) -> RowMapping | None:
        return (
            connection.execute(
                text("SELECT * FROM research_pipeline_runs WHERE id = :run_id"),
                {"run_id": run_id},
            )
            .mappings()
            .one_or_none()
        )

    @staticmethod
    def _run_by_fingerprint(
        connection: Connection,
        request_fingerprint_sha256: str,
    ) -> RowMapping | None:
        return (
            connection.execute(
                text(
                    "SELECT * FROM research_pipeline_runs "
                    "WHERE request_fingerprint_sha256 = :request_fingerprint_sha256"
                ),
                {"request_fingerprint_sha256": request_fingerprint_sha256},
            )
            .mappings()
            .one_or_none()
        )

    @classmethod
    def _load_run(
        cls,
        connection: Connection,
        run_id: UUID,
        *,
        root_row: RowMapping | None = None,
    ) -> ResearchRunArtifact:
        row = root_row or cls._run_row(connection, run_id)
        if row is None:
            raise ResearchRunNotFound(f"research run {run_id} was not found")
        payload = dict(row["artifact_payload"])
        _require(
            domain_sha256(PHASE6_ARTIFACT_HASH_DOMAIN, payload) == row["artifact_sha256"],
            "persisted Phase 6 artifact payload failed hash revalidation",
        )
        artifact = ResearchRunArtifact.model_validate(
            {
                **payload,
                "run_id": row["id"],
                "artifact_sha256": row["artifact_sha256"],
                "created_at_utc": row["created_at_utc"],
            }
        )
        _validate_root_columns(row, artifact)

        bindings = tuple(
            _validate_binding_row(item)
            for item in _load_child_payloads(
                connection,
                table="research_pipeline_snapshot_bindings",
                run_id=artifact.run_id,
            )
        )
        attempts = tuple(
            _validate_attempt_row(
                item,
                phase5_report_id=artifact.phase5_evaluation.evaluation_report_id,
            )
            for item in _load_child_payloads(
                connection,
                table="research_pipeline_attempts",
                run_id=artifact.run_id,
            )
        )
        features = tuple(
            _validate_feature_row(item)
            for item in _load_child_payloads(
                connection,
                table="research_feature_rows",
                run_id=artifact.run_id,
            )
        )
        scores = tuple(
            _validate_score_row(item)
            for item in _load_child_payloads(
                connection,
                table="research_score_outputs",
                run_id=artifact.run_id,
            )
        )
        comparisons = tuple(
            _validate_comparison_row(item)
            for item in _load_child_payloads(
                connection,
                table="research_baseline_comparisons",
                run_id=artifact.run_id,
            )
        )
        extractions = tuple(
            _validate_extraction_row(item)
            for item in _load_child_payloads(
                connection,
                table="research_text_extractions",
                run_id=artifact.run_id,
            )
        )
        corroborations = tuple(
            _validate_corroboration_row(item)
            for item in _load_child_payloads(
                connection,
                table="research_text_corroborations",
                run_id=artifact.run_id,
            )
        )

        _require(_same(bindings, artifact.snapshot_bindings), "snapshot binding set is incomplete")
        _require(_same(attempts, artifact.attempts), "attempt registry is incomplete")
        _require(_same(features, artifact.feature_rows), "feature-row registry is incomplete")
        _require(_same(scores, artifact.scores), "score-output registry is incomplete")
        _require(
            _same(comparisons, artifact.baseline_comparisons),
            "baseline-comparison registry is incomplete",
        )
        if isinstance(artifact.family_evidence, FamilyCEvidence):
            _require(
                _same(extractions, artifact.family_evidence.extractions),
                "text-extraction registry is incomplete",
            )
            _require(
                _same(corroborations, artifact.family_evidence.corroborations),
                "official-corroboration registry is incomplete",
            )
        else:
            _require(not extractions and not corroborations, "non-text family has text artifacts")
        return artifact

    @staticmethod
    def _insert_run(connection: Connection, artifact: ResearchRunArtifact) -> None:
        evaluation = artifact.phase5_evaluation
        _insert_row(
            connection,
            "research_pipeline_runs",
            {
                "id": artifact.run_id,
                "schema_version": artifact.artifact_schema_version,
                "request_fingerprint_sha256": artifact.request_fingerprint_sha256,
                "artifact_sha256": artifact.artifact_sha256,
                "configuration_id": artifact.configuration_id.value,
                "configuration_sha256": artifact.configuration_sha256,
                "mapping_id": artifact.mapping_id,
                "canonical_family": artifact.family.value,
                "specification_sha256": artifact.specification.specification_sha256,
                "feature_lineage_sha256": artifact.feature_lineage_sha256,
                "snapshot_bundle_sha256": artifact.snapshot_bundle_sha256,
                "phase5_policy_id": evaluation.policy_id,
                "phase5_policy_version": evaluation.policy_version,
                "phase5_policy_sha256": evaluation.policy_sha256,
                "phase5_fixture_id": evaluation.fixture_id,
                "phase5_fixture_sha256": evaluation.fixture_sha256,
                "evaluation_report_id": evaluation.evaluation_report_id,
                "evaluation_outcome_id": evaluation.evaluation_outcome_id,
                "promotion_state": evaluation.promotion_state.value,
                "status": artifact.status.value,
                "artifact_payload": _artifact_payload(artifact),
                "reason_codes": canonicalize(artifact.reason_codes),
                "warnings": canonicalize(artifact.warnings),
                "no_real_performance_claimed": artifact.no_real_performance_claimed,
                "paper_approval_granted": artifact.paper_approval_granted,
            },
            json_columns=frozenset({"artifact_payload", "reason_codes", "warnings"}),
        )

        for binding in artifact.snapshot_bindings:
            _insert_row(
                connection,
                "research_pipeline_snapshot_bindings",
                {
                    "run_id": artifact.run_id,
                    "ordinal": binding.ordinal,
                    "snapshot_id": binding.snapshot_id,
                    "snapshot_sha256": binding.snapshot_sha256,
                    "capability": binding.capability.value,
                    "binding_sha256": binding.binding_sha256,
                    "payload": _model_payload(binding),
                },
                json_columns=frozenset({"payload"}),
            )
        for attempt in artifact.attempts:
            _insert_row(
                connection,
                "research_pipeline_attempts",
                {
                    "run_id": artifact.run_id,
                    "ordinal": attempt.ordinal,
                    "phase5_report_id": evaluation.evaluation_report_id,
                    "phase5_trial_id": attempt.phase5_trial_id,
                    "phase5_trial_key": attempt.phase5_trial_key,
                    "status": attempt.status.value,
                    "config_sha256": attempt.configuration_sha256,
                    "failure_reason": attempt.failure_reason,
                    "payload": _model_payload(attempt),
                    "attempt_sha256": attempt.attempt_sha256,
                },
                json_columns=frozenset({"payload"}),
            )
        for feature in artifact.feature_rows:
            _insert_row(
                connection,
                "research_feature_rows",
                {
                    "run_id": artifact.run_id,
                    "ordinal": feature.ordinal,
                    "row_id": feature.row_id,
                    "sample_id": feature.sample_id,
                    "entity_id": feature.entity_id,
                    "decision_time_utc": feature.decision_time_utc,
                    "row_sha256": feature.row_sha256,
                    "payload": _model_payload(feature),
                },
                json_columns=frozenset({"payload"}),
            )
        for score in artifact.scores:
            _insert_row(
                connection,
                "research_score_outputs",
                {
                    "run_id": artifact.run_id,
                    "ordinal": score.ordinal,
                    "score_id": score.score_id,
                    "sample_id": score.sample_id,
                    "model_id": score.model_id,
                    "research_score": score.research_score,
                    "explanation_sha256": score.explanation_sha256,
                    "output_sha256": score.output_sha256,
                    "payload": _model_payload(score),
                },
                json_columns=frozenset({"payload"}),
            )
        for comparison in artifact.baseline_comparisons:
            _insert_row(
                connection,
                "research_baseline_comparisons",
                {
                    "run_id": artifact.run_id,
                    "ordinal": comparison.ordinal,
                    "comparison_id": comparison.comparison_id,
                    "candidate_model_id": comparison.candidate_model_id,
                    "baseline_model_id": comparison.baseline_model_id,
                    "outcome": comparison.outcome.value,
                    "comparison_sha256": comparison.comparison_sha256,
                    "payload": _model_payload(comparison),
                },
                json_columns=frozenset({"payload"}),
            )
        if isinstance(artifact.family_evidence, FamilyCEvidence):
            for extraction in artifact.family_evidence.extractions:
                _insert_row(
                    connection,
                    "research_text_extractions",
                    {
                        "run_id": artifact.run_id,
                        "ordinal": extraction.ordinal,
                        "extraction_id": extraction.extraction_id,
                        "source_version_id": extraction.official_source_version_id,
                        "document_sha256": extraction.document_content_sha256,
                        "extractor_id": extraction.extractor_id,
                        "extractor_version": extraction.extractor_version,
                        "model_id": extraction.model_id,
                        "prompt_version": extraction.prompt_version,
                        "schema_version": extraction.schema_version,
                        "extraction_sha256": extraction.extraction_sha256,
                        "payload": _model_payload(extraction),
                    },
                    json_columns=frozenset({"payload"}),
                )
            for corroboration in artifact.family_evidence.corroborations:
                _insert_row(
                    connection,
                    "research_text_corroborations",
                    {
                        "run_id": artifact.run_id,
                        "ordinal": corroboration.ordinal,
                        "corroboration_id": corroboration.corroboration_id,
                        "social_record_id": corroboration.social_attention_record_id,
                        "official_source_version_id": corroboration.official_source_version_id,
                        "official_document_sha256": corroboration.official_document_sha256,
                        "corroboration_sha256": corroboration.corroboration_sha256,
                        "payload": _model_payload(corroboration),
                    },
                    json_columns=frozenset({"payload"}),
                )

    def create_run(self, artifact: ResearchRunArtifact) -> ResearchRunArtifact:
        try:
            with self.engine.begin() as connection:
                connection.execute(
                    text("SELECT pg_advisory_xact_lock(hashtextextended(:hash, 0))"),
                    {"hash": artifact.request_fingerprint_sha256},
                )
                existing = self._run_by_fingerprint(
                    connection,
                    artifact.request_fingerprint_sha256,
                )
                if existing is not None:
                    loaded = self._load_run(
                        connection,
                        existing["id"],
                        root_row=existing,
                    )
                    if loaded.artifact_sha256 != artifact.artifact_sha256 or not _same(
                        _artifact_payload(loaded),
                        _artifact_payload(artifact),
                    ):
                        raise ResearchRepositoryConflict(
                            "research request fingerprint is bound to different evidence"
                        )
                    return loaded
                self._insert_run(connection, artifact)
                return self._load_run(connection, artifact.run_id)
        except (ResearchRepositoryConflict, ResearchRunNotFound):
            raise
        except (TypeError, ValueError) as exc:
            raise ResearchRepositoryConflict(
                "immutable Phase 6 research run failed canonical validation"
            ) from exc
        except DBAPIError as exc:
            raise ResearchRepositoryConflict(
                "immutable Phase 6 research run could not be stored"
            ) from exc

    def get_run(self, run_id: UUID) -> ResearchRunArtifact:
        try:
            with self.engine.connect() as connection:
                return self._load_run(connection, run_id)
        except (ResearchRepositoryConflict, ResearchRunNotFound):
            raise
        except (TypeError, ValueError) as exc:
            raise ResearchRepositoryConflict(
                "immutable Phase 6 research run failed canonical validation"
            ) from exc
        except DBAPIError as exc:
            raise ResearchRepositoryConflict(
                "immutable Phase 6 research run could not be read"
            ) from exc

    def list_runs(self, *, limit: int) -> list[ResearchRunSummary]:
        if limit < 1 or limit > 100:
            raise ValueError("research run list limit must be between 1 and 100")
        try:
            with self.engine.connect() as connection:
                rows = list(
                    connection.execute(
                        text(
                            "SELECT id, artifact_sha256, configuration_id, "
                            "canonical_family, promotion_state, status, "
                            "(artifact_payload->>'synthetic')::boolean AS synthetic, "
                            "no_real_performance_claimed, paper_approval_granted, "
                            "(artifact_payload->>"
                            "'pass_research_is_not_paper_approval')::boolean AS "
                            "pass_research_is_not_paper_approval, "
                            "created_at_utc, reason_codes "
                            "FROM research_pipeline_runs "
                            "ORDER BY created_at_utc DESC, id DESC LIMIT :limit"
                        ),
                        {"limit": limit},
                    ).mappings()
                )
                return [_summary_from_row(row) for row in rows]
        except ResearchRepositoryConflict:
            raise
        except (TypeError, ValueError) as exc:
            raise ResearchRepositoryConflict(
                "immutable Phase 6 research run failed canonical validation"
            ) from exc
        except DBAPIError as exc:
            raise ResearchRepositoryConflict(
                "immutable Phase 6 research runs could not be listed"
            ) from exc


__all__ = [
    "ResearchRepository",
    "ResearchRepositoryConflict",
    "ResearchRunNotFound",
]
