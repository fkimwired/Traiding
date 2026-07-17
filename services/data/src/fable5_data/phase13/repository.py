"""PostgreSQL persistence for immutable Phase 13 qualification evidence."""

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
from fable5_data.phase13.canonical import (
    PHASE13_ARTIFACT_HASH_DOMAIN,
    PHASE13_CAPABILITY_HASH_DOMAIN,
    PHASE13_CHECK_HASH_DOMAIN,
    domain_sha256,
)
from fable5_data.phase13.contracts import (
    PointInTimeQualificationArtifact,
    QualificationCapabilityManifest,
    QualificationCheck,
)


class PointInTimeQualificationNotFound(LookupError):
    """The requested immutable Phase 13 qualification does not exist."""


class PointInTimeQualificationRepositoryConflict(RuntimeError):
    """Persisted Phase 13 qualification evidence conflicts with its artifact."""


_WORKFLOW_LOCK_PREFIX = "phase13-qualification-workflow:"
_ROOT_TABLE = "point_in_time_qualification_runs"
_ROOT_IDENTITIES = frozenset(
    {
        "qualification_id",
        "qualification_idempotency_key",
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
        raise PointInTimeQualificationRepositoryConflict(
            "immutable Phase 13 qualification payload must be an object"
        )
    return cast(dict[str, Any], normalized)


def _same(left: object, right: object) -> bool:
    return bool(canonical_json_bytes(left) == canonical_json_bytes(right))


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise PointInTimeQualificationRepositoryConflict(message)


def _lock(connection: Connection, value: UUID | str) -> None:
    connection.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:identity, 0))"),
        {"identity": str(value)},
    )


def _workflow_lock_identity(key: str) -> str:
    return f"{_WORKFLOW_LOCK_PREFIX}{key}"


def _artifact_payload(artifact: PointInTimeQualificationArtifact) -> dict[str, Any]:
    payload = _normalized_object(artifact.model_dump(mode="python", exclude={"artifact_sha256"}))
    _require(
        domain_sha256(PHASE13_ARTIFACT_HASH_DOMAIN, payload) == artifact.artifact_sha256,
        "Phase 13 qualification artifact hash does not match its payload",
    )
    return payload


def _manifest_payload(manifest: QualificationCapabilityManifest) -> dict[str, Any]:
    payload = _normalized_object(manifest.model_dump(mode="python"))
    preimage = {key: value for key, value in payload.items() if key != "capability_manifest_sha256"}
    _require(
        domain_sha256(PHASE13_CAPABILITY_HASH_DOMAIN, preimage)
        == manifest.capability_manifest_sha256,
        "Phase 13 capability manifest hash does not match its payload",
    )
    return payload


def _check_payload(check: QualificationCheck) -> dict[str, Any]:
    payload = _normalized_object(check.model_dump(mode="python"))
    preimage = {key: value for key, value in payload.items() if key != "check_sha256"}
    _require(
        domain_sha256(PHASE13_CHECK_HASH_DOMAIN, preimage) == check.check_sha256,
        "Phase 13 qualification check hash does not match its payload",
    )
    return payload


def _row_by_identity(
    connection: Connection,
    *,
    column: str,
    value: object,
) -> RowMapping | None:
    _require(column in _ROOT_IDENTITIES, "Phase 13 root lookup column is not allowed")
    return (
        connection.execute(
            text(f"SELECT * FROM {_ROOT_TABLE} WHERE {column} = :value"),
            {"value": value},
        )
        .mappings()
        .one_or_none()
    )


def _validate_manifest_row(row: RowMapping) -> QualificationCapabilityManifest:
    payload = dict(row["payload"])
    preimage = {key: value for key, value in payload.items() if key != "capability_manifest_sha256"}
    _require(
        domain_sha256(PHASE13_CAPABILITY_HASH_DOMAIN, preimage)
        == row["capability_manifest_sha256"],
        "persisted Phase 13 capability manifest failed hash revalidation",
    )
    manifest = QualificationCapabilityManifest.model_validate(payload)
    column_values: dict[str, object] = {
        "schema_version": manifest.schema_version,
        "ordinal": manifest.ordinal,
        "capability": manifest.capability.value,
        "status": manifest.status.value,
        "reason_code": manifest.reason_code.value,
        "decision_time_utc": manifest.decision_time_utc,
        "event_time_min_utc": manifest.event_time_min_utc,
        "event_time_max_utc": manifest.event_time_max_utc,
        "available_at_min_utc": manifest.available_at_min_utc,
        "available_at_max_utc": manifest.available_at_max_utc,
        "record_count": manifest.record_count,
        "missingness_count": manifest.missingness_count,
        "revision_count": manifest.revision_count,
        "raw_evidence_sha256": manifest.raw_evidence_sha256,
        "normalized_evidence_sha256": manifest.normalized_evidence_sha256,
        "schema_identity_sha256": manifest.schema_identity_sha256,
        "capability_manifest_sha256": manifest.capability_manifest_sha256,
    }
    for column, expected in column_values.items():
        _require(
            row[column] == expected,
            f"persisted Phase 13 capability column {column} conflicts",
        )
    _require(
        _same(row["request_evidence"], manifest.request_evidence),
        "persisted Phase 13 capability request evidence conflicts",
    )
    return manifest


def _validate_check_row(row: RowMapping) -> QualificationCheck:
    payload = dict(row["payload"])
    preimage = {key: value for key, value in payload.items() if key != "check_sha256"}
    _require(
        domain_sha256(PHASE13_CHECK_HASH_DOMAIN, preimage) == row["check_sha256"],
        "persisted Phase 13 qualification check failed hash revalidation",
    )
    check = QualificationCheck.model_validate(payload)
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
            f"persisted Phase 13 qualification check column {column} conflicts",
        )
    _require(
        _same(row["evidence_sha256s"], check.evidence_sha256s),
        "persisted Phase 13 qualification check evidence hashes conflict",
    )
    return check


class _ConnectionBoundCreation:
    """Find or create one qualification in a serialized transaction."""

    def __init__(
        self,
        repository: PointInTimeQualificationRepository,
        connection: Connection,
        key: str,
    ) -> None:
        self._repository = repository
        self._connection = connection
        self._key = key

    def find_by_idempotency_key(self, key: str) -> PointInTimeQualificationArtifact | None:
        _require(key == self._key, "serialized Phase 13 qualification key changed during lookup")
        try:
            return self._repository._find_by_idempotency_key(self._connection, key)
        except (PointInTimeQualificationNotFound, PointInTimeQualificationRepositoryConflict):
            raise
        except (TypeError, ValueError, ValidationError) as exc:
            raise PointInTimeQualificationRepositoryConflict(
                "persisted Phase 13 qualification artifact is invalid"
            ) from exc

    def create_qualification(
        self, artifact: PointInTimeQualificationArtifact
    ) -> PointInTimeQualificationArtifact:
        _require(
            artifact.qualification_idempotency_key == self._key,
            "serialized Phase 13 qualification key changed before persistence",
        )
        try:
            return self._repository._create_qualification(self._connection, artifact)
        except (PointInTimeQualificationNotFound, PointInTimeQualificationRepositoryConflict):
            raise
        except (TypeError, ValueError, ValidationError) as exc:
            raise PointInTimeQualificationRepositoryConflict(
                "immutable Phase 13 qualification failed canonical validation"
            ) from exc


class PointInTimeQualificationRepository:
    """Persist complete immutable point-in-time qualification bundles."""

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
    ) -> PointInTimeQualificationArtifact | None:
        row = _row_by_identity(
            connection,
            column="qualification_idempotency_key",
            value=key,
        )
        if row is None:
            return None
        return cls._load_qualification(connection, row["qualification_id"], root_row=row)

    @staticmethod
    def _load_qualification(
        connection: Connection,
        qualification_id: UUID,
        *,
        root_row: RowMapping | None = None,
    ) -> PointInTimeQualificationArtifact:
        row = root_row
        if row is None:
            row = _row_by_identity(
                connection,
                column="qualification_id",
                value=qualification_id,
            )
        if row is None:
            raise PointInTimeQualificationNotFound(
                f"point-in-time qualification {qualification_id} was not found"
            )
        payload = dict(row["artifact_payload"])
        _require(
            domain_sha256(PHASE13_ARTIFACT_HASH_DOMAIN, payload) == row["artifact_sha256"],
            "persisted Phase 13 qualification artifact failed hash revalidation",
        )
        manifest_rows = list(
            connection.execute(
                text(
                    "SELECT * FROM point_in_time_qualification_payloads "
                    "WHERE qualification_id = :qualification_id ORDER BY ordinal"
                ),
                {"qualification_id": qualification_id},
            ).mappings()
        )
        check_rows = list(
            connection.execute(
                text(
                    "SELECT * FROM point_in_time_qualification_checks "
                    "WHERE qualification_id = :qualification_id ORDER BY ordinal"
                ),
                {"qualification_id": qualification_id},
            ).mappings()
        )
        for child_row in (*manifest_rows, *check_rows):
            _require(
                child_row["qualification_artifact_sha256"] == row["artifact_sha256"],
                "persisted Phase 13 qualification child lost artifact lineage",
            )
        manifests = tuple(_validate_manifest_row(item) for item in manifest_rows)
        checks = tuple(_validate_check_row(item) for item in check_rows)
        _require(
            _same(payload.get("capability_manifests"), manifests),
            "persisted Phase 13 capability manifests conflict with the root artifact",
        )
        _require(
            _same(payload.get("checks"), checks),
            "persisted Phase 13 qualification checks conflict with the root artifact",
        )
        payload["capability_manifests"] = manifests
        payload["checks"] = checks
        artifact = PointInTimeQualificationArtifact.model_validate(
            {**payload, "artifact_sha256": row["artifact_sha256"]}
        )
        profile = artifact.provider_profile
        rights = artifact.rights_attestation
        column_values: dict[str, object] = {
            "qualification_id": artifact.qualification_id,
            "schema_version": artifact.schema_version,
            "request_fingerprint_sha256": artifact.request_fingerprint_sha256,
            "qualification_idempotency_key": artifact.qualification_idempotency_key,
            "source_kind": artifact.source_kind.value,
            "outcome": artifact.outcome.value,
            "provider_id": profile.provider_id,
            "adapter_id": profile.adapter_id,
            "adapter_version": profile.adapter_version,
            "dataset_id": profile.dataset_id,
            "product_id": profile.product_id,
            "provider_synthetic": profile.synthetic,
            "transport_profile_sha256": artifact.transport_profile_sha256,
            "rights_attestation_id": None if rights is None else rights.attestation_id,
            "rights_attestation_sha256": None if rights is None else rights.attestation_sha256,
            "rights_valid_from_utc": None if rights is None else rights.valid_from_utc,
            "rights_expires_at_utc": None if rights is None else rights.expires_at_utc,
            "rights_storage_allowed": None if rights is None else rights.storage_allowed,
            "rights_non_display_allowed": None if rights is None else rights.non_display_allowed,
            "rights_derived_data_allowed": None if rights is None else rights.derived_data_allowed,
            "sample_plan_id": artifact.sample_plan_id,
            "sample_plan_sha256": artifact.sample_plan_sha256,
            "capture_manifest_sha256": artifact.capture_manifest_sha256,
            "started_at_utc": artifact.started_at_utc,
            "completed_at_utc": artifact.completed_at_utc,
            "code_version_git_sha": artifact.code_version_git_sha,
            "research_data_eligible": artifact.research_data_eligible,
            "strategy_promotion_authorized": artifact.strategy_promotion_authorized,
            "strategy_execution_eligible": artifact.strategy_execution_eligible,
            "execution_authorized": artifact.execution_authorized,
            "order_submission_authorized": artifact.order_submission_authorized,
            "live_path_absent": artifact.live_path_absent,
            "no_personalized_investment_advice": artifact.no_personalized_investment_advice,
            "no_real_performance_claimed": artifact.no_real_performance_claimed,
        }
        for column, expected in column_values.items():
            _require(
                row[column] == expected,
                f"persisted Phase 13 qualification root column {column} conflicts",
            )
        return artifact

    @staticmethod
    def _insert_qualification(
        connection: Connection,
        artifact: PointInTimeQualificationArtifact,
    ) -> None:
        profile = artifact.provider_profile
        rights = artifact.rights_attestation
        _insert_row(
            connection,
            _ROOT_TABLE,
            {
                "qualification_id": artifact.qualification_id,
                "schema_version": artifact.schema_version,
                "artifact_sha256": artifact.artifact_sha256,
                "request_fingerprint_sha256": artifact.request_fingerprint_sha256,
                "qualification_idempotency_key": artifact.qualification_idempotency_key,
                "source_kind": artifact.source_kind.value,
                "outcome": artifact.outcome.value,
                "provider_id": profile.provider_id,
                "adapter_id": profile.adapter_id,
                "adapter_version": profile.adapter_version,
                "dataset_id": profile.dataset_id,
                "product_id": profile.product_id,
                "provider_synthetic": profile.synthetic,
                "transport_profile_sha256": artifact.transport_profile_sha256,
                "rights_attestation_id": None if rights is None else rights.attestation_id,
                "rights_attestation_sha256": None if rights is None else rights.attestation_sha256,
                "rights_valid_from_utc": None if rights is None else rights.valid_from_utc,
                "rights_expires_at_utc": None if rights is None else rights.expires_at_utc,
                "rights_storage_allowed": None if rights is None else rights.storage_allowed,
                "rights_non_display_allowed": (
                    None if rights is None else rights.non_display_allowed
                ),
                "rights_derived_data_allowed": (
                    None if rights is None else rights.derived_data_allowed
                ),
                "sample_plan_id": artifact.sample_plan_id,
                "sample_plan_sha256": artifact.sample_plan_sha256,
                "capture_manifest_sha256": artifact.capture_manifest_sha256,
                "started_at_utc": artifact.started_at_utc,
                "completed_at_utc": artifact.completed_at_utc,
                "code_version_git_sha": artifact.code_version_git_sha,
                "research_data_eligible": artifact.research_data_eligible,
                "strategy_promotion_authorized": artifact.strategy_promotion_authorized,
                "strategy_execution_eligible": artifact.strategy_execution_eligible,
                "execution_authorized": artifact.execution_authorized,
                "order_submission_authorized": artifact.order_submission_authorized,
                "live_path_absent": artifact.live_path_absent,
                "no_personalized_investment_advice": artifact.no_personalized_investment_advice,
                "no_real_performance_claimed": artifact.no_real_performance_claimed,
                "artifact_payload": _artifact_payload(artifact),
            },
            json_columns=frozenset({"artifact_payload"}),
        )
        for manifest in artifact.capability_manifests:
            _insert_row(
                connection,
                "point_in_time_qualification_payloads",
                {
                    "qualification_id": artifact.qualification_id,
                    "qualification_artifact_sha256": artifact.artifact_sha256,
                    "schema_version": manifest.schema_version,
                    "ordinal": manifest.ordinal,
                    "capability": manifest.capability.value,
                    "status": manifest.status.value,
                    "reason_code": manifest.reason_code.value,
                    "decision_time_utc": manifest.decision_time_utc,
                    "event_time_min_utc": manifest.event_time_min_utc,
                    "event_time_max_utc": manifest.event_time_max_utc,
                    "available_at_min_utc": manifest.available_at_min_utc,
                    "available_at_max_utc": manifest.available_at_max_utc,
                    "record_count": manifest.record_count,
                    "missingness_count": manifest.missingness_count,
                    "revision_count": manifest.revision_count,
                    "raw_evidence_sha256": manifest.raw_evidence_sha256,
                    "normalized_evidence_sha256": manifest.normalized_evidence_sha256,
                    "schema_identity_sha256": manifest.schema_identity_sha256,
                    "request_evidence": canonicalize(manifest.request_evidence),
                    "capability_manifest_sha256": manifest.capability_manifest_sha256,
                    "payload": _manifest_payload(manifest),
                },
                json_columns=frozenset({"request_evidence", "payload"}),
            )
        for check in artifact.checks:
            _insert_row(
                connection,
                "point_in_time_qualification_checks",
                {
                    "qualification_id": artifact.qualification_id,
                    "qualification_artifact_sha256": artifact.artifact_sha256,
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

    def find_by_idempotency_key(self, key: str) -> PointInTimeQualificationArtifact | None:
        try:
            with self.engine.connect() as connection:
                return self._find_by_idempotency_key(connection, key)
        except (PointInTimeQualificationNotFound, PointInTimeQualificationRepositoryConflict):
            raise
        except (TypeError, ValueError, ValidationError) as exc:
            raise PointInTimeQualificationRepositoryConflict(
                "persisted Phase 13 qualification artifact is invalid"
            ) from exc
        except DBAPIError as exc:
            raise PointInTimeQualificationRepositoryConflict(
                "Phase 13 qualification artifact could not be loaded"
            ) from exc

    def _create_qualification(
        self,
        connection: Connection,
        artifact: PointInTimeQualificationArtifact,
    ) -> PointInTimeQualificationArtifact:
        _lock(connection, _workflow_lock_identity(artifact.qualification_idempotency_key))
        existing = _row_by_identity(
            connection,
            column="qualification_idempotency_key",
            value=artifact.qualification_idempotency_key,
        )
        if existing is not None:
            if existing["request_fingerprint_sha256"] != artifact.request_fingerprint_sha256:
                raise PointInTimeQualificationRepositoryConflict(
                    "qualification idempotency key is bound to a different request fingerprint"
                )
            return self._load_qualification(
                connection, existing["qualification_id"], root_row=existing
            )
        fingerprint_row = _row_by_identity(
            connection,
            column="request_fingerprint_sha256",
            value=artifact.request_fingerprint_sha256,
        )
        if fingerprint_row is not None:
            raise PointInTimeQualificationRepositoryConflict(
                "qualification request fingerprint is bound to another idempotency key"
            )
        self._insert_qualification(connection, artifact)
        return self._load_qualification(connection, artifact.qualification_id)

    @contextmanager
    def serialized_creation(self, key: str) -> Iterator[_ConnectionBoundCreation]:
        try:
            with self.engine.begin() as connection:
                _lock(connection, _workflow_lock_identity(key))
                yield _ConnectionBoundCreation(self, connection, key)
        except (PointInTimeQualificationNotFound, PointInTimeQualificationRepositoryConflict):
            raise
        except DBAPIError as exc:
            raise PointInTimeQualificationRepositoryConflict(
                "immutable Phase 13 serialized qualification could not be stored"
            ) from exc

    def create_qualification(
        self, artifact: PointInTimeQualificationArtifact
    ) -> PointInTimeQualificationArtifact:
        try:
            with self.engine.begin() as connection:
                return self._create_qualification(connection, artifact)
        except (PointInTimeQualificationNotFound, PointInTimeQualificationRepositoryConflict):
            raise
        except (TypeError, ValueError, ValidationError) as exc:
            raise PointInTimeQualificationRepositoryConflict(
                "immutable Phase 13 qualification failed canonical validation"
            ) from exc
        except DBAPIError as exc:
            raise PointInTimeQualificationRepositoryConflict(
                "immutable Phase 13 qualification could not be stored"
            ) from exc

    def get_qualification(self, qualification_id: UUID) -> PointInTimeQualificationArtifact:
        try:
            with self.engine.connect() as connection:
                return self._load_qualification(connection, qualification_id)
        except (PointInTimeQualificationNotFound, PointInTimeQualificationRepositoryConflict):
            raise
        except (TypeError, ValueError, ValidationError) as exc:
            raise PointInTimeQualificationRepositoryConflict(
                "persisted Phase 13 qualification artifact is invalid"
            ) from exc
        except DBAPIError as exc:
            raise PointInTimeQualificationRepositoryConflict(
                "Phase 13 qualification artifact could not be loaded"
            ) from exc


__all__ = [
    "PointInTimeQualificationNotFound",
    "PointInTimeQualificationRepository",
    "PointInTimeQualificationRepositoryConflict",
]
