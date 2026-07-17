"""PostgreSQL persistence for immutable Phase 12 shadow-readiness evidence."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from typing import Any, cast
from uuid import UUID

from fable5_data.canonical import canonical_json_bytes, canonicalize
from pydantic import ValidationError
from sqlalchemy import Engine, bindparam, create_engine, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import Connection, RowMapping
from sqlalchemy.exc import DBAPIError

from fable5_paper.phase12.canonical import (
    PHASE12_ARTIFACT_HASH_DOMAIN,
    PHASE12_CHECK_HASH_DOMAIN,
    domain_sha256,
)
from fable5_paper.phase12.contracts import (
    PaperShadowReadinessArtifact,
    PaperShadowReadinessCheck,
)


class PaperShadowReadinessNotFound(LookupError):
    """The requested immutable Phase 12 readiness artifact does not exist."""


class PaperShadowReadinessRepositoryConflict(RuntimeError):
    """Persisted Phase 12 readiness evidence conflicts with its canonical artifact."""


_WORKFLOW_LOCK_PREFIX = "phase12-readiness-workflow:"


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
        raise PaperShadowReadinessRepositoryConflict(
            "immutable Phase 12 readiness payload must be an object"
        )
    return cast(dict[str, Any], normalized)


def _same(left: object, right: object) -> bool:
    return bool(canonical_json_bytes(left) == canonical_json_bytes(right))


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise PaperShadowReadinessRepositoryConflict(message)


def _lock(connection: Connection, value: UUID | str) -> None:
    connection.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:identity, 0))"),
        {"identity": str(value)},
    )


def _workflow_lock_identity(key: str) -> str:
    return f"{_WORKFLOW_LOCK_PREFIX}{key}"


def _artifact_payload(artifact: PaperShadowReadinessArtifact) -> dict[str, Any]:
    payload = _normalized_object(
        artifact.model_dump(
            mode="python",
            exclude={"readiness_assessment_id", "artifact_sha256"},
        )
    )
    _require(
        domain_sha256(PHASE12_ARTIFACT_HASH_DOMAIN, payload) == artifact.artifact_sha256,
        "Phase 12 readiness artifact hash does not match its timeless payload",
    )
    return payload


def _check_payload(check: PaperShadowReadinessCheck) -> dict[str, Any]:
    payload = _normalized_object(check.model_dump(mode="python"))
    preimage = {key: value for key, value in payload.items() if key != "check_sha256"}
    _require(
        domain_sha256(PHASE12_CHECK_HASH_DOMAIN, preimage) == check.check_sha256,
        "Phase 12 readiness check hash does not match its payload",
    )
    return payload


def _row_by_identity(
    connection: Connection,
    *,
    column: str,
    value: object,
) -> RowMapping | None:
    return (
        connection.execute(
            text(f"SELECT * FROM paper_shadow_readiness_runs WHERE {column} = :value"),
            {"value": value},
        )
        .mappings()
        .one_or_none()
    )


def _validate_check_row(row: RowMapping) -> PaperShadowReadinessCheck:
    payload = dict(row["payload"])
    _require(
        domain_sha256(
            PHASE12_CHECK_HASH_DOMAIN,
            {key: value for key, value in payload.items() if key != "check_sha256"},
        )
        == row["check_sha256"],
        "persisted Phase 12 readiness check failed hash revalidation",
    )
    check = PaperShadowReadinessCheck.model_validate(payload)
    column_values: dict[str, object] = {
        "schema_version": check.schema_version,
        "ordinal": check.ordinal,
        "code": check.code.value,
        "status": check.status.value,
        "reason_code": check.reason_code,
        "observed_value": check.observed_value,
        "threshold_value": check.threshold_value,
        "check_sha256": check.check_sha256,
    }
    for column, expected in column_values.items():
        _require(
            row[column] == expected,
            f"persisted Phase 12 readiness check column {column} conflicts",
        )
    _require(
        _same(row["evidence_sha256s"], check.evidence_sha256s),
        "persisted Phase 12 readiness check evidence hashes conflict",
    )
    return check


class _ConnectionBoundCreation:
    """Find or create one readiness artifact in a serialized transaction."""

    def __init__(
        self,
        repository: PaperShadowReadinessRepository,
        connection: Connection,
        key: str,
    ) -> None:
        self._repository = repository
        self._connection = connection
        self._key = key

    def find_by_idempotency_key(self, key: str) -> PaperShadowReadinessArtifact | None:
        _require(
            key == self._key,
            "serialized Phase 12 readiness key changed during lookup",
        )
        try:
            return self._repository._find_by_idempotency_key(self._connection, key)
        except (PaperShadowReadinessNotFound, PaperShadowReadinessRepositoryConflict):
            raise
        except (TypeError, ValueError, ValidationError) as exc:
            raise PaperShadowReadinessRepositoryConflict(
                "persisted Phase 12 readiness artifact is invalid"
            ) from exc

    def create_readiness(
        self,
        artifact: PaperShadowReadinessArtifact,
    ) -> PaperShadowReadinessArtifact:
        _require(
            artifact.readiness_idempotency_key == self._key,
            "serialized Phase 12 readiness key changed before persistence",
        )
        try:
            return self._repository._create_readiness(self._connection, artifact)
        except (PaperShadowReadinessNotFound, PaperShadowReadinessRepositoryConflict):
            raise
        except (TypeError, ValueError, ValidationError) as exc:
            raise PaperShadowReadinessRepositoryConflict(
                "immutable Phase 12 readiness failed canonical validation"
            ) from exc


class PaperShadowReadinessRepository:
    """Persist complete immutable paper shadow-readiness bundles."""

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
    ) -> PaperShadowReadinessArtifact | None:
        row = _row_by_identity(
            connection,
            column="readiness_idempotency_key",
            value=key,
        )
        if row is None:
            return None
        return cls._load_readiness(connection, row["readiness_assessment_id"], root_row=row)

    @staticmethod
    def _load_readiness(
        connection: Connection,
        readiness_assessment_id: UUID,
        *,
        root_row: RowMapping | None = None,
    ) -> PaperShadowReadinessArtifact:
        row = root_row
        if row is None:
            row = _row_by_identity(
                connection,
                column="readiness_assessment_id",
                value=readiness_assessment_id,
            )
        if row is None:
            raise PaperShadowReadinessNotFound(
                f"paper shadow-readiness assessment {readiness_assessment_id} was not found"
            )
        payload = dict(row["artifact_payload"])
        _require(
            domain_sha256(PHASE12_ARTIFACT_HASH_DOMAIN, payload) == row["artifact_sha256"],
            "persisted Phase 12 readiness artifact failed hash revalidation",
        )
        check_rows = list(
            connection.execute(
                text(
                    "SELECT * FROM paper_shadow_readiness_checks "
                    "WHERE readiness_assessment_id = :assessment_id ORDER BY ordinal"
                ),
                {"assessment_id": readiness_assessment_id},
            ).mappings()
        )
        for check_row in check_rows:
            _require(
                check_row["readiness_artifact_sha256"] == row["artifact_sha256"],
                "persisted Phase 12 readiness child lost artifact lineage",
            )
        checks = tuple(_validate_check_row(item) for item in check_rows)
        _require(
            _same(payload.get("checks"), checks),
            "persisted Phase 12 readiness checks conflict with the root artifact",
        )
        payload["checks"] = checks
        artifact = PaperShadowReadinessArtifact.model_validate(
            {
                **payload,
                "readiness_assessment_id": row["readiness_assessment_id"],
                "artifact_sha256": row["artifact_sha256"],
            }
        )
        column_values: dict[str, object] = {
            "artifact_schema_version": artifact.artifact_schema_version,
            "request_fingerprint_sha256": artifact.request_fingerprint_sha256,
            "readiness_idempotency_key": artifact.readiness_idempotency_key,
            "source_kind": artifact.source_kind.value,
            "transport_profile_sha256": artifact.transport_profile_sha256,
            "outcome": artifact.outcome.value,
            "phase12_code_version_git_sha": artifact.phase12_code_version_git_sha,
            "assessment_started_at_utc": artifact.assessment_started_at_utc,
            "assessment_completed_at_utc": artifact.assessment_completed_at_utc,
            "expires_at_utc": artifact.expires_at_utc,
            "order_submission_authorized": artifact.order_submission_authorized,
            "strategy_execution_eligible": artifact.strategy_execution_eligible,
            "live_path_absent": artifact.live_path_absent,
            "no_personalized_investment_advice": (artifact.no_personalized_investment_advice),
            "no_real_performance_claimed": artifact.no_real_performance_claimed,
        }
        for column, expected in column_values.items():
            _require(
                row[column] == expected,
                f"persisted Phase 12 readiness root column {column} conflicts",
            )
        _require(
            _same(row["reason_codes"], artifact.reason_codes),
            "persisted Phase 12 readiness reason codes conflict",
        )
        return artifact

    @staticmethod
    def _insert_readiness(
        connection: Connection,
        artifact: PaperShadowReadinessArtifact,
    ) -> None:
        _insert_row(
            connection,
            "paper_shadow_readiness_runs",
            {
                "readiness_assessment_id": artifact.readiness_assessment_id,
                "artifact_schema_version": artifact.artifact_schema_version,
                "artifact_sha256": artifact.artifact_sha256,
                "request_fingerprint_sha256": artifact.request_fingerprint_sha256,
                "readiness_idempotency_key": artifact.readiness_idempotency_key,
                "source_kind": artifact.source_kind.value,
                "transport_profile_sha256": artifact.transport_profile_sha256,
                "outcome": artifact.outcome.value,
                "reason_codes": canonicalize(artifact.reason_codes),
                "phase12_code_version_git_sha": artifact.phase12_code_version_git_sha,
                "assessment_started_at_utc": artifact.assessment_started_at_utc,
                "assessment_completed_at_utc": artifact.assessment_completed_at_utc,
                "expires_at_utc": artifact.expires_at_utc,
                "order_submission_authorized": artifact.order_submission_authorized,
                "strategy_execution_eligible": artifact.strategy_execution_eligible,
                "live_path_absent": artifact.live_path_absent,
                "no_personalized_investment_advice": (artifact.no_personalized_investment_advice),
                "no_real_performance_claimed": artifact.no_real_performance_claimed,
                "artifact_payload": _artifact_payload(artifact),
            },
            json_columns=frozenset({"reason_codes", "artifact_payload"}),
        )
        for check in artifact.checks:
            _insert_row(
                connection,
                "paper_shadow_readiness_checks",
                {
                    "readiness_assessment_id": artifact.readiness_assessment_id,
                    "readiness_artifact_sha256": artifact.artifact_sha256,
                    "schema_version": check.schema_version,
                    "ordinal": check.ordinal,
                    "code": check.code.value,
                    "status": check.status.value,
                    "reason_code": check.reason_code,
                    "observed_value": check.observed_value,
                    "threshold_value": check.threshold_value,
                    "evidence_sha256s": canonicalize(check.evidence_sha256s),
                    "check_sha256": check.check_sha256,
                    "payload": _check_payload(check),
                },
                json_columns=frozenset({"evidence_sha256s", "payload"}),
            )

    def find_by_idempotency_key(self, key: str) -> PaperShadowReadinessArtifact | None:
        try:
            with self.engine.connect() as connection:
                return self._find_by_idempotency_key(connection, key)
        except (PaperShadowReadinessNotFound, PaperShadowReadinessRepositoryConflict):
            raise
        except (TypeError, ValueError, ValidationError) as exc:
            raise PaperShadowReadinessRepositoryConflict(
                "persisted Phase 12 readiness artifact is invalid"
            ) from exc
        except DBAPIError as exc:
            raise PaperShadowReadinessRepositoryConflict(
                "Phase 12 readiness artifact could not be loaded"
            ) from exc

    def _create_readiness(
        self,
        connection: Connection,
        artifact: PaperShadowReadinessArtifact,
    ) -> PaperShadowReadinessArtifact:
        _lock(connection, _workflow_lock_identity(artifact.readiness_idempotency_key))
        existing = _row_by_identity(
            connection,
            column="readiness_idempotency_key",
            value=artifact.readiness_idempotency_key,
        )
        if existing is not None:
            if existing["request_fingerprint_sha256"] != artifact.request_fingerprint_sha256:
                raise PaperShadowReadinessRepositoryConflict(
                    "readiness idempotency key is bound to a different request fingerprint"
                )
            return self._load_readiness(
                connection,
                existing["readiness_assessment_id"],
                root_row=existing,
            )
        fingerprint_row = _row_by_identity(
            connection,
            column="request_fingerprint_sha256",
            value=artifact.request_fingerprint_sha256,
        )
        if fingerprint_row is not None:
            raise PaperShadowReadinessRepositoryConflict(
                "readiness request fingerprint is bound to another idempotency key"
            )
        self._insert_readiness(connection, artifact)
        return self._load_readiness(connection, artifact.readiness_assessment_id)

    @contextmanager
    def serialized_creation(self, key: str) -> Iterator[_ConnectionBoundCreation]:
        try:
            with self.engine.begin() as connection:
                _lock(connection, _workflow_lock_identity(key))
                yield _ConnectionBoundCreation(self, connection, key)
        except (PaperShadowReadinessNotFound, PaperShadowReadinessRepositoryConflict):
            raise
        except DBAPIError as exc:
            raise PaperShadowReadinessRepositoryConflict(
                "immutable Phase 12 serialized readiness could not be stored"
            ) from exc

    def create_readiness(
        self,
        artifact: PaperShadowReadinessArtifact,
    ) -> PaperShadowReadinessArtifact:
        try:
            with self.engine.begin() as connection:
                return self._create_readiness(connection, artifact)
        except (PaperShadowReadinessNotFound, PaperShadowReadinessRepositoryConflict):
            raise
        except (TypeError, ValueError, ValidationError) as exc:
            raise PaperShadowReadinessRepositoryConflict(
                "immutable Phase 12 readiness failed canonical validation"
            ) from exc
        except DBAPIError as exc:
            raise PaperShadowReadinessRepositoryConflict(
                "immutable Phase 12 readiness could not be stored"
            ) from exc

    def get_readiness(
        self,
        readiness_assessment_id: UUID,
    ) -> PaperShadowReadinessArtifact:
        try:
            with self.engine.connect() as connection:
                return self._load_readiness(connection, readiness_assessment_id)
        except (PaperShadowReadinessNotFound, PaperShadowReadinessRepositoryConflict):
            raise
        except (TypeError, ValueError, ValidationError) as exc:
            raise PaperShadowReadinessRepositoryConflict(
                "persisted Phase 12 readiness artifact is invalid"
            ) from exc
        except DBAPIError as exc:
            raise PaperShadowReadinessRepositoryConflict(
                "Phase 12 readiness artifact could not be loaded"
            ) from exc
