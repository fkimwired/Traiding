"""PostgreSQL persistence for immutable Phase 14 eligibility assessments."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from typing import Any, cast
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import Engine, bindparam, create_engine, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import Connection, RowMapping
from sqlalchemy.exc import DBAPIError

from fable5_data.canonical import canonical_json_bytes, canonicalize
from fable5_data.phase13.contracts import PointInTimeQualificationArtifact
from fable5_data.phase13.repository import PointInTimeQualificationRepository
from fable5_data.phase14.canonical import (
    PHASE14_ARTIFACT_HASH_DOMAIN,
    PHASE14_CHECK_HASH_DOMAIN,
    PHASE14_PAYLOAD_HASH_DOMAIN,
    domain_sha256,
)
from fable5_data.phase14.contracts import (
    ResearchIngestionEligibilityArtifact,
    ResearchIngestionEligibilityCheck,
    ResearchIngestionEligibilityPayload,
)


class ResearchIngestionEligibilityNotFound(LookupError):
    """The requested immutable Phase 14 assessment does not exist."""


class ResearchIngestionEligibilityRepositoryConflict(RuntimeError):
    """Persisted Phase 14 evidence conflicts with its canonical artifact."""


_WORKFLOW_LOCK_PREFIX = "phase14-eligibility-workflow:"
_ROOT_TABLE = "research_ingestion_eligibility_assessments"
_ROOT_IDENTITIES = frozenset(
    {
        "assessment_id",
        "assessment_idempotency_key",
        "request_fingerprint_sha256",
    }
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
    connection.execute(
        _json_statement(
            f"INSERT INTO {table} ({', '.join(columns)}) VALUES "
            f"({', '.join(f':{column}' for column in columns)})",
            *json_columns,
        ),
        dict(row),
    )


def _normalized_object(value: object) -> dict[str, Any]:
    normalized = canonicalize(value)
    if not isinstance(normalized, dict):
        raise ResearchIngestionEligibilityRepositoryConflict(
            "immutable Phase 14 eligibility payload must be an object"
        )
    return cast(dict[str, Any], normalized)


def _same(left: object, right: object) -> bool:
    return bool(canonical_json_bytes(left) == canonical_json_bytes(right))


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ResearchIngestionEligibilityRepositoryConflict(message)


def _lock(connection: Connection, value: UUID | str) -> None:
    connection.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:identity, 0))"),
        {"identity": str(value)},
    )


def _workflow_lock_identity(key: str) -> str:
    return f"{_WORKFLOW_LOCK_PREFIX}{key}"


def _artifact_payload(artifact: ResearchIngestionEligibilityArtifact) -> dict[str, Any]:
    payload = _normalized_object(artifact.model_dump(mode="python", exclude={"artifact_sha256"}))
    _require(
        domain_sha256(PHASE14_ARTIFACT_HASH_DOMAIN, payload) == artifact.artifact_sha256,
        "Phase 14 eligibility artifact hash does not match its payload",
    )
    return payload


def _eligibility_payload(payload: ResearchIngestionEligibilityPayload) -> dict[str, Any]:
    body = _normalized_object(payload.model_dump(mode="python"))
    preimage = {key: value for key, value in body.items() if key != "payload_sha256"}
    _require(
        domain_sha256(PHASE14_PAYLOAD_HASH_DOMAIN, preimage) == payload.payload_sha256,
        "Phase 14 eligibility payload hash does not match its preimage",
    )
    return body


def _check_payload(check: ResearchIngestionEligibilityCheck) -> dict[str, Any]:
    body = _normalized_object(check.model_dump(mode="python"))
    preimage = {key: value for key, value in body.items() if key != "check_sha256"}
    _require(
        domain_sha256(PHASE14_CHECK_HASH_DOMAIN, preimage) == check.check_sha256,
        "Phase 14 eligibility check hash does not match its preimage",
    )
    return body


def _row_by_identity(
    connection: Connection,
    *,
    column: str,
    value: object,
) -> RowMapping | None:
    _require(column in _ROOT_IDENTITIES, "Phase 14 root lookup column is not allowed")
    return (
        connection.execute(
            text(f"SELECT * FROM {_ROOT_TABLE} WHERE {column} = :value"),
            {"value": value},
        )
        .mappings()
        .one_or_none()
    )


def _validate_payload_row(row: RowMapping) -> ResearchIngestionEligibilityPayload:
    body = dict(row["payload"])
    preimage = {key: value for key, value in body.items() if key != "payload_sha256"}
    _require(
        domain_sha256(PHASE14_PAYLOAD_HASH_DOMAIN, preimage) == row["payload_sha256"],
        "persisted Phase 14 eligibility payload failed hash revalidation",
    )
    payload = ResearchIngestionEligibilityPayload.model_validate(body)
    column_values: dict[str, object] = {
        "schema_version": payload.schema_version,
        "ordinal": payload.ordinal,
        "capability": payload.capability.value,
        "source_status": payload.source_status.value,
        "source_reason_code": payload.source_reason_code.value,
        "decision_time_utc": payload.decision_time_utc,
        "event_time_min_utc": payload.event_time_min_utc,
        "event_time_max_utc": payload.event_time_max_utc,
        "available_at_min_utc": payload.available_at_min_utc,
        "available_at_max_utc": payload.available_at_max_utc,
        "record_count": payload.record_count,
        "missingness_count": payload.missingness_count,
        "revision_count": payload.revision_count,
        "raw_evidence_sha256": payload.raw_evidence_sha256,
        "normalized_evidence_sha256": payload.normalized_evidence_sha256,
        "schema_identity_sha256": payload.schema_identity_sha256,
        "request_evidence_count": payload.request_evidence_count,
        "source_capability_manifest_sha256": payload.source_capability_manifest_sha256,
        "payload_sha256": payload.payload_sha256,
    }
    for column, expected in column_values.items():
        _require(
            row[column] == expected,
            f"persisted Phase 14 eligibility payload column {column} conflicts",
        )
    _require(
        _same(row["request_evidence_sha256s"], payload.request_evidence_sha256s),
        "persisted Phase 14 request evidence hashes conflict",
    )
    return payload


def _validate_check_row(row: RowMapping) -> ResearchIngestionEligibilityCheck:
    body = dict(row["payload"])
    preimage = {key: value for key, value in body.items() if key != "check_sha256"}
    _require(
        domain_sha256(PHASE14_CHECK_HASH_DOMAIN, preimage) == row["check_sha256"],
        "persisted Phase 14 eligibility check failed hash revalidation",
    )
    check = ResearchIngestionEligibilityCheck.model_validate(body)
    column_values: dict[str, object] = {
        "schema_version": check.schema_version,
        "ordinal": check.ordinal,
        "code": check.code.value,
        "status": check.status.value,
        "reason_code": check.reason_code.value,
        "observed_value": check.observed_value,
        "threshold_value": check.threshold_value,
        "check_sha256": check.check_sha256,
    }
    for column, expected in column_values.items():
        _require(
            row[column] == expected,
            f"persisted Phase 14 eligibility check column {column} conflicts",
        )
    _require(
        _same(row["evidence_sha256s"], check.evidence_sha256s),
        "persisted Phase 14 eligibility check evidence hashes conflict",
    )
    return check


def _validate_source(
    connection: Connection,
    artifact: ResearchIngestionEligibilityArtifact,
) -> PointInTimeQualificationArtifact:
    source = PointInTimeQualificationRepository._load_qualification(
        connection, artifact.qualification_id
    )
    rights = source.rights_attestation
    comparisons: tuple[tuple[object, object, str], ...] = (
        (
            artifact.qualification_request_fingerprint_sha256,
            source.request_fingerprint_sha256,
            "request fingerprint",
        ),
        (
            artifact.qualification_artifact_sha256,
            source.artifact_sha256,
            "artifact hash",
        ),
        (
            artifact.qualification_capture_manifest_sha256,
            source.capture_manifest_sha256,
            "capture manifest",
        ),
        (artifact.qualification_source_kind, source.source_kind, "source kind"),
        (artifact.qualification_outcome, source.outcome, "outcome"),
        (
            artifact.qualification_rights_attestation_id,
            None if rights is None else rights.attestation_id,
            "rights identity",
        ),
        (
            artifact.qualification_rights_attestation_sha256,
            None if rights is None else rights.attestation_sha256,
            "rights hash",
        ),
        (
            artifact.qualification_code_version_git_sha,
            source.code_version_git_sha,
            "code identity",
        ),
        (
            artifact.qualification_capability_manifest_sha256s,
            tuple(item.capability_manifest_sha256 for item in source.capability_manifests),
            "capability lineage",
        ),
        (
            artifact.qualification_check_sha256s,
            tuple(item.check_sha256 for item in source.checks),
            "check lineage",
        ),
    )
    for actual, expected, label in comparisons:
        _require(actual == expected, f"Phase 14 qualification {label} conflicts")
    _require(
        len(artifact.payloads) == len(source.capability_manifests),
        "Phase 14 projected capability count conflicts",
    )
    for projected, manifest in zip(artifact.payloads, source.capability_manifests, strict=True):
        expected_request_hashes = tuple(
            sorted(item.request_evidence_sha256 for item in manifest.request_evidence)
        )
        projected_values = (
            projected.ordinal,
            projected.capability,
            projected.source_status,
            projected.source_reason_code,
            projected.decision_time_utc,
            projected.event_time_min_utc,
            projected.event_time_max_utc,
            projected.available_at_min_utc,
            projected.available_at_max_utc,
            projected.record_count,
            projected.missingness_count,
            projected.revision_count,
            projected.raw_evidence_sha256,
            projected.normalized_evidence_sha256,
            projected.schema_identity_sha256,
            projected.request_evidence_count,
            projected.request_evidence_sha256s,
            projected.source_capability_manifest_sha256,
        )
        source_values = (
            manifest.ordinal,
            manifest.capability,
            manifest.status,
            manifest.reason_code,
            manifest.decision_time_utc,
            manifest.event_time_min_utc,
            manifest.event_time_max_utc,
            manifest.available_at_min_utc,
            manifest.available_at_max_utc,
            manifest.record_count,
            manifest.missingness_count,
            manifest.revision_count,
            manifest.raw_evidence_sha256,
            manifest.normalized_evidence_sha256,
            manifest.schema_identity_sha256,
            len(expected_request_hashes),
            expected_request_hashes,
            manifest.capability_manifest_sha256,
        )
        _require(
            projected_values == source_values,
            "Phase 14 projected capability conflicts with the Phase 13 source",
        )
    return source


class _ConnectionBoundCreation:
    """Find or create one assessment in a serialized transaction."""

    def __init__(
        self,
        repository: ResearchIngestionEligibilityRepository,
        connection: Connection,
        key: str,
    ) -> None:
        self._repository = repository
        self._connection = connection
        self._key = key

    def find_by_idempotency_key(self, key: str) -> ResearchIngestionEligibilityArtifact | None:
        _require(key == self._key, "serialized Phase 14 assessment key changed during lookup")
        return self._repository._find_by_idempotency_key(self._connection, key)

    def find_by_request_fingerprint(
        self, fingerprint: str
    ) -> ResearchIngestionEligibilityArtifact | None:
        return self._repository._find_by_request_fingerprint(self._connection, fingerprint)

    def create_assessment(
        self, artifact: ResearchIngestionEligibilityArtifact
    ) -> ResearchIngestionEligibilityArtifact:
        _require(
            artifact.assessment_idempotency_key == self._key,
            "serialized Phase 14 assessment key changed before persistence",
        )
        return self._repository._create_assessment(self._connection, artifact)


class ResearchIngestionEligibilityRepository:
    """Persist complete immutable research-ingestion eligibility bundles."""

    def __init__(self, dsn: str | None = None, *, engine: Engine | None = None) -> None:
        if dsn is None and engine is None:
            raise ValueError("dsn or engine is required")
        self.engine = engine or create_engine(str(dsn), pool_pre_ping=True)
        self._owns_engine = engine is None

    def dispose(self) -> None:
        if self._owns_engine:
            self.engine.dispose()

    @classmethod
    def _find_by_idempotency_key(
        cls,
        connection: Connection,
        key: str,
    ) -> ResearchIngestionEligibilityArtifact | None:
        row = _row_by_identity(
            connection,
            column="assessment_idempotency_key",
            value=key,
        )
        if row is None:
            return None
        return cls._load_assessment(connection, row["assessment_id"], root_row=row)

    @classmethod
    def _find_by_request_fingerprint(
        cls,
        connection: Connection,
        fingerprint: str,
    ) -> ResearchIngestionEligibilityArtifact | None:
        row = _row_by_identity(
            connection,
            column="request_fingerprint_sha256",
            value=fingerprint,
        )
        if row is None:
            return None
        return cls._load_assessment(connection, row["assessment_id"], root_row=row)

    @staticmethod
    def _load_assessment(
        connection: Connection,
        assessment_id: UUID,
        *,
        root_row: RowMapping | None = None,
    ) -> ResearchIngestionEligibilityArtifact:
        row = root_row
        if row is None:
            row = _row_by_identity(
                connection,
                column="assessment_id",
                value=assessment_id,
            )
        if row is None:
            raise ResearchIngestionEligibilityNotFound(
                f"research-ingestion eligibility assessment {assessment_id} was not found"
            )
        body = dict(row["artifact_payload"])
        _require(
            domain_sha256(PHASE14_ARTIFACT_HASH_DOMAIN, body) == row["artifact_sha256"],
            "persisted Phase 14 eligibility artifact failed hash revalidation",
        )
        payload_rows = list(
            connection.execute(
                text(
                    "SELECT * FROM research_ingestion_eligibility_payloads "
                    "WHERE assessment_id = :assessment_id ORDER BY ordinal"
                ),
                {"assessment_id": assessment_id},
            ).mappings()
        )
        check_rows = list(
            connection.execute(
                text(
                    "SELECT * FROM research_ingestion_eligibility_checks "
                    "WHERE assessment_id = :assessment_id ORDER BY ordinal"
                ),
                {"assessment_id": assessment_id},
            ).mappings()
        )
        for child_row in (*payload_rows, *check_rows):
            _require(
                child_row["assessment_artifact_sha256"] == row["artifact_sha256"],
                "persisted Phase 14 eligibility child lost artifact lineage",
            )
        payloads = tuple(_validate_payload_row(item) for item in payload_rows)
        checks = tuple(_validate_check_row(item) for item in check_rows)
        _require(
            _same(body.get("payloads"), payloads),
            "persisted Phase 14 payloads conflict with the root artifact",
        )
        _require(
            _same(body.get("checks"), checks),
            "persisted Phase 14 checks conflict with the root artifact",
        )
        body["payloads"] = payloads
        body["checks"] = checks
        artifact = ResearchIngestionEligibilityArtifact.model_validate(
            {**body, "artifact_sha256": row["artifact_sha256"]}
        )
        column_values: dict[str, object] = {
            "assessment_id": artifact.assessment_id,
            "schema_version": artifact.schema_version,
            "request_fingerprint_sha256": artifact.request_fingerprint_sha256,
            "assessment_idempotency_key": artifact.assessment_idempotency_key,
            "policy_id": artifact.policy_id,
            "policy_sha256": artifact.policy_sha256,
            "qualification_id": artifact.qualification_id,
            "qualification_request_fingerprint_sha256": (
                artifact.qualification_request_fingerprint_sha256
            ),
            "qualification_artifact_sha256": artifact.qualification_artifact_sha256,
            "qualification_capture_manifest_sha256": (
                artifact.qualification_capture_manifest_sha256
            ),
            "qualification_source_kind": artifact.qualification_source_kind.value,
            "qualification_outcome": artifact.qualification_outcome.value,
            "qualification_rights_attestation_id": (artifact.qualification_rights_attestation_id),
            "qualification_rights_attestation_sha256": (
                artifact.qualification_rights_attestation_sha256
            ),
            "qualification_code_version_git_sha": artifact.qualification_code_version_git_sha,
            "payload_manifest_sha256": artifact.payload_manifest_sha256,
            "started_at_utc": artifact.started_at_utc,
            "completed_at_utc": artifact.completed_at_utc,
            "code_version_git_sha": artifact.code_version_git_sha,
            "outcome": artifact.outcome.value,
            "external_request_performed": artifact.external_request_performed,
            "provider_payload_persisted": artifact.provider_payload_persisted,
            "research_ingestion_authorized": artifact.research_ingestion_authorized,
            "research_snapshot_created": artifact.research_snapshot_created,
            "research_data_eligible": artifact.research_data_eligible,
            "research_run_created": artifact.research_run_created,
            "research_run_authorized": artifact.research_run_authorized,
            "research_executed": artifact.research_executed,
            "performance_computed": artifact.performance_computed,
            "pass_research_granted": artifact.pass_research_granted,
            "strategy_promotion_authorized": artifact.strategy_promotion_authorized,
            "paper_approval_granted": artifact.paper_approval_granted,
            "strategy_execution_eligible": artifact.strategy_execution_eligible,
            "execution_authorized": artifact.execution_authorized,
            "order_submission_authorized": artifact.order_submission_authorized,
            "live_path_absent": artifact.live_path_absent,
            "no_personalized_investment_advice": (artifact.no_personalized_investment_advice),
            "no_real_performance_claimed": artifact.no_real_performance_claimed,
        }
        for column, expected in column_values.items():
            _require(
                row[column] == expected,
                f"persisted Phase 14 eligibility root column {column} conflicts",
            )
        _require(
            _same(
                row["qualification_capability_manifest_sha256s"],
                artifact.qualification_capability_manifest_sha256s,
            ),
            "persisted Phase 14 capability lineage columns conflict",
        )
        _require(
            _same(
                row["qualification_check_sha256s"],
                artifact.qualification_check_sha256s,
            ),
            "persisted Phase 14 check lineage columns conflict",
        )
        _validate_source(connection, artifact)
        return artifact

    @staticmethod
    def _insert_assessment(
        connection: Connection,
        artifact: ResearchIngestionEligibilityArtifact,
    ) -> None:
        _validate_source(connection, artifact)
        _insert_row(
            connection,
            _ROOT_TABLE,
            {
                "assessment_id": artifact.assessment_id,
                "schema_version": artifact.schema_version,
                "artifact_sha256": artifact.artifact_sha256,
                "request_fingerprint_sha256": artifact.request_fingerprint_sha256,
                "assessment_idempotency_key": artifact.assessment_idempotency_key,
                "policy_id": artifact.policy_id,
                "policy_sha256": artifact.policy_sha256,
                "qualification_id": artifact.qualification_id,
                "qualification_request_fingerprint_sha256": (
                    artifact.qualification_request_fingerprint_sha256
                ),
                "qualification_artifact_sha256": artifact.qualification_artifact_sha256,
                "qualification_capture_manifest_sha256": (
                    artifact.qualification_capture_manifest_sha256
                ),
                "qualification_source_kind": artifact.qualification_source_kind.value,
                "qualification_outcome": artifact.qualification_outcome.value,
                "qualification_rights_attestation_id": (
                    artifact.qualification_rights_attestation_id
                ),
                "qualification_rights_attestation_sha256": (
                    artifact.qualification_rights_attestation_sha256
                ),
                "qualification_code_version_git_sha": (artifact.qualification_code_version_git_sha),
                "qualification_capability_manifest_sha256s": canonicalize(
                    artifact.qualification_capability_manifest_sha256s
                ),
                "qualification_check_sha256s": canonicalize(artifact.qualification_check_sha256s),
                "payload_manifest_sha256": artifact.payload_manifest_sha256,
                "started_at_utc": artifact.started_at_utc,
                "completed_at_utc": artifact.completed_at_utc,
                "code_version_git_sha": artifact.code_version_git_sha,
                "outcome": artifact.outcome.value,
                "external_request_performed": artifact.external_request_performed,
                "provider_payload_persisted": artifact.provider_payload_persisted,
                "research_ingestion_authorized": artifact.research_ingestion_authorized,
                "research_snapshot_created": artifact.research_snapshot_created,
                "research_data_eligible": artifact.research_data_eligible,
                "research_run_created": artifact.research_run_created,
                "research_run_authorized": artifact.research_run_authorized,
                "research_executed": artifact.research_executed,
                "performance_computed": artifact.performance_computed,
                "pass_research_granted": artifact.pass_research_granted,
                "strategy_promotion_authorized": artifact.strategy_promotion_authorized,
                "paper_approval_granted": artifact.paper_approval_granted,
                "strategy_execution_eligible": artifact.strategy_execution_eligible,
                "execution_authorized": artifact.execution_authorized,
                "order_submission_authorized": artifact.order_submission_authorized,
                "live_path_absent": artifact.live_path_absent,
                "no_personalized_investment_advice": (artifact.no_personalized_investment_advice),
                "no_real_performance_claimed": artifact.no_real_performance_claimed,
                "artifact_payload": _artifact_payload(artifact),
            },
            json_columns=frozenset(
                {
                    "qualification_capability_manifest_sha256s",
                    "qualification_check_sha256s",
                    "artifact_payload",
                }
            ),
        )
        for payload in artifact.payloads:
            _insert_row(
                connection,
                "research_ingestion_eligibility_payloads",
                {
                    "assessment_id": artifact.assessment_id,
                    "assessment_artifact_sha256": artifact.artifact_sha256,
                    "schema_version": payload.schema_version,
                    "ordinal": payload.ordinal,
                    "capability": payload.capability.value,
                    "source_status": payload.source_status.value,
                    "source_reason_code": payload.source_reason_code.value,
                    "decision_time_utc": payload.decision_time_utc,
                    "event_time_min_utc": payload.event_time_min_utc,
                    "event_time_max_utc": payload.event_time_max_utc,
                    "available_at_min_utc": payload.available_at_min_utc,
                    "available_at_max_utc": payload.available_at_max_utc,
                    "record_count": payload.record_count,
                    "missingness_count": payload.missingness_count,
                    "revision_count": payload.revision_count,
                    "raw_evidence_sha256": payload.raw_evidence_sha256,
                    "normalized_evidence_sha256": payload.normalized_evidence_sha256,
                    "schema_identity_sha256": payload.schema_identity_sha256,
                    "request_evidence_count": payload.request_evidence_count,
                    "request_evidence_sha256s": canonicalize(payload.request_evidence_sha256s),
                    "source_capability_manifest_sha256": (
                        payload.source_capability_manifest_sha256
                    ),
                    "payload_sha256": payload.payload_sha256,
                    "payload": _eligibility_payload(payload),
                },
                json_columns=frozenset({"request_evidence_sha256s", "payload"}),
            )
        for check in artifact.checks:
            _insert_row(
                connection,
                "research_ingestion_eligibility_checks",
                {
                    "assessment_id": artifact.assessment_id,
                    "assessment_artifact_sha256": artifact.artifact_sha256,
                    "schema_version": check.schema_version,
                    "ordinal": check.ordinal,
                    "code": check.code.value,
                    "status": check.status.value,
                    "reason_code": check.reason_code.value,
                    "observed_value": check.observed_value,
                    "threshold_value": check.threshold_value,
                    "evidence_sha256s": canonicalize(check.evidence_sha256s),
                    "check_sha256": check.check_sha256,
                    "payload": _check_payload(check),
                },
                json_columns=frozenset({"evidence_sha256s", "payload"}),
            )

    def find_by_idempotency_key(self, key: str) -> ResearchIngestionEligibilityArtifact | None:
        try:
            with self.engine.connect() as connection:
                return self._find_by_idempotency_key(connection, key)
        except (
            ResearchIngestionEligibilityNotFound,
            ResearchIngestionEligibilityRepositoryConflict,
        ):
            raise
        except (TypeError, ValueError, ValidationError) as exc:
            raise ResearchIngestionEligibilityRepositoryConflict(
                "persisted Phase 14 eligibility artifact is invalid"
            ) from exc
        except DBAPIError as exc:
            raise ResearchIngestionEligibilityRepositoryConflict(
                "Phase 14 eligibility artifact could not be loaded"
            ) from exc

    def find_by_request_fingerprint(
        self, fingerprint: str
    ) -> ResearchIngestionEligibilityArtifact | None:
        try:
            with self.engine.connect() as connection:
                return self._find_by_request_fingerprint(connection, fingerprint)
        except (
            ResearchIngestionEligibilityNotFound,
            ResearchIngestionEligibilityRepositoryConflict,
        ):
            raise
        except (TypeError, ValueError, ValidationError) as exc:
            raise ResearchIngestionEligibilityRepositoryConflict(
                "persisted Phase 14 eligibility artifact is invalid"
            ) from exc
        except DBAPIError as exc:
            raise ResearchIngestionEligibilityRepositoryConflict(
                "Phase 14 eligibility artifact could not be loaded"
            ) from exc

    def _create_assessment(
        self,
        connection: Connection,
        artifact: ResearchIngestionEligibilityArtifact,
    ) -> ResearchIngestionEligibilityArtifact:
        _lock(connection, _workflow_lock_identity(artifact.assessment_idempotency_key))
        existing = _row_by_identity(
            connection,
            column="assessment_idempotency_key",
            value=artifact.assessment_idempotency_key,
        )
        if existing is not None:
            if existing["request_fingerprint_sha256"] != artifact.request_fingerprint_sha256:
                raise ResearchIngestionEligibilityRepositoryConflict(
                    "assessment idempotency key is bound to a different request fingerprint"
                )
            return self._load_assessment(connection, existing["assessment_id"], root_row=existing)
        fingerprint_row = _row_by_identity(
            connection,
            column="request_fingerprint_sha256",
            value=artifact.request_fingerprint_sha256,
        )
        if fingerprint_row is not None:
            raise ResearchIngestionEligibilityRepositoryConflict(
                "assessment request fingerprint is bound to another idempotency key"
            )
        self._insert_assessment(connection, artifact)
        return self._load_assessment(connection, artifact.assessment_id)

    @contextmanager
    def serialized_creation(self, key: str) -> Iterator[_ConnectionBoundCreation]:
        try:
            with self.engine.begin() as connection:
                _lock(connection, _workflow_lock_identity(key))
                yield _ConnectionBoundCreation(self, connection, key)
        except (
            ResearchIngestionEligibilityNotFound,
            ResearchIngestionEligibilityRepositoryConflict,
        ):
            raise
        except DBAPIError as exc:
            raise ResearchIngestionEligibilityRepositoryConflict(
                "immutable Phase 14 serialized assessment could not be stored"
            ) from exc

    def create_assessment(
        self, artifact: ResearchIngestionEligibilityArtifact
    ) -> ResearchIngestionEligibilityArtifact:
        try:
            with self.engine.begin() as connection:
                return self._create_assessment(connection, artifact)
        except (
            ResearchIngestionEligibilityNotFound,
            ResearchIngestionEligibilityRepositoryConflict,
        ):
            raise
        except (TypeError, ValueError, ValidationError) as exc:
            raise ResearchIngestionEligibilityRepositoryConflict(
                "immutable Phase 14 eligibility assessment failed canonical validation"
            ) from exc
        except DBAPIError as exc:
            raise ResearchIngestionEligibilityRepositoryConflict(
                "immutable Phase 14 eligibility assessment could not be stored"
            ) from exc

    def get_assessment(self, assessment_id: UUID) -> ResearchIngestionEligibilityArtifact:
        try:
            with self.engine.connect() as connection:
                return self._load_assessment(connection, assessment_id)
        except (
            ResearchIngestionEligibilityNotFound,
            ResearchIngestionEligibilityRepositoryConflict,
        ):
            raise
        except (TypeError, ValueError, ValidationError) as exc:
            raise ResearchIngestionEligibilityRepositoryConflict(
                "persisted Phase 14 eligibility artifact is invalid"
            ) from exc
        except DBAPIError as exc:
            raise ResearchIngestionEligibilityRepositoryConflict(
                "Phase 14 eligibility artifact could not be loaded"
            ) from exc


__all__ = [
    "ResearchIngestionEligibilityNotFound",
    "ResearchIngestionEligibilityRepository",
    "ResearchIngestionEligibilityRepositoryConflict",
]
