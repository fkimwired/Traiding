"""PostgreSQL persistence for immutable Phase 10 local paper simulations."""

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

from fable5_paper.canonical import (
    PHASE10_ARTIFACT_HASH_DOMAIN,
    PHASE10_CHECK_HASH_DOMAIN,
    PHASE10_LEDGER_HASH_DOMAIN,
    domain_sha256,
)
from fable5_paper.contracts import (
    PaperSimulationArtifact,
    PaperSimulationCheck,
    PaperSimulationLedgerEntry,
    PaperSimulationSummary,
)


class PaperArtifactNotFound(LookupError):
    """The requested immutable Phase 10 artifact does not exist."""


class PaperRepositoryConflict(RuntimeError):
    """Persisted Phase 10 evidence conflicts with its canonical artifact."""


_WORKFLOW_LOCK_PREFIX = "phase10-workflow:"


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
        raise PaperRepositoryConflict("immutable Phase 10 payload must be an object")
    return cast(dict[str, Any], normalized)


def _same(left: object, right: object) -> bool:
    return bool(canonical_json_bytes(left) == canonical_json_bytes(right))


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise PaperRepositoryConflict(message)


def _lock(connection: Connection, value: UUID | str) -> None:
    connection.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:identity, 0))"),
        {"identity": str(value)},
    )


def _workflow_lock_identity(key: str) -> str:
    return f"{_WORKFLOW_LOCK_PREFIX}{key}"


def _artifact_payload(artifact: PaperSimulationArtifact) -> dict[str, Any]:
    payload = _normalized_object(
        artifact.model_dump(
            mode="python",
            exclude={"simulation_run_id", "artifact_sha256", "created_at_utc"},
        )
    )
    _require(
        domain_sha256(PHASE10_ARTIFACT_HASH_DOMAIN, payload) == artifact.artifact_sha256,
        "Phase 10 artifact hash does not match its timeless payload",
    )
    return payload


def _check_payload(check: PaperSimulationCheck) -> dict[str, Any]:
    payload = _normalized_object(check.model_dump(mode="python"))
    preimage = {key: value for key, value in payload.items() if key != "check_sha256"}
    _require(
        domain_sha256(PHASE10_CHECK_HASH_DOMAIN, preimage) == check.check_sha256,
        "Phase 10 check hash does not match its payload",
    )
    return payload


def _ledger_payload(entry: PaperSimulationLedgerEntry) -> dict[str, Any]:
    payload = _normalized_object(entry.model_dump(mode="python"))
    preimage = {
        key: value
        for key, value in payload.items()
        if key not in {"ledger_entry_id", "ledger_entry_sha256"}
    }
    _require(
        domain_sha256(PHASE10_LEDGER_HASH_DOMAIN, preimage) == entry.ledger_entry_sha256,
        "Phase 10 ledger hash does not match its payload",
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
            text(f"SELECT * FROM paper_simulation_runs WHERE {column} = :value"),
            {"value": value},
        )
        .mappings()
        .one_or_none()
    )


def _validate_check_row(row: RowMapping) -> PaperSimulationCheck:
    payload = dict(row["payload"])
    check = PaperSimulationCheck.model_validate(payload)
    _require(
        row["ordinal"] == check.ordinal
        and row["schema_version"] == check.schema_version
        and row["code"] == check.code.value
        and row["status"] == check.status.value
        and row["reason_code"] == check.reason_code
        and row["observed_value"] == check.observed_value
        and row["threshold_value"] == check.threshold_value
        and _same(row["evidence_sha256s"], check.evidence_sha256s)
        and row["check_sha256"] == check.check_sha256,
        "persisted Phase 10 check columns conflict with payload",
    )
    _check_payload(check)
    return check


def _validate_ledger_row(row: RowMapping) -> PaperSimulationLedgerEntry:
    payload = dict(row["payload"])
    entry = PaperSimulationLedgerEntry.model_validate(payload)
    compared_fields = (
        "simulation_run_id",
        "ordinal",
        "schema_version",
        "ledger_entry_id",
        "ledger_entry_sha256",
        "mock_snapshot_id",
        "mock_snapshot_sha256",
        "mock_observation_id",
        "mock_observation_sha256",
        "entity_id",
        "universe_id",
        "observed_at_utc",
        "available_at_utc",
        "decision_time_utc",
        "model_id",
        "signal_rule_id",
        "signal_value",
        "signal_state",
        "simulated_side",
        "fill_status",
        "approved_proposed_notional",
        "requested_quantity",
        "filled_quantity",
        "rejected_quantity",
        "unfilled_quantity",
        "reference_price",
        "simulated_fill_price",
        "average_daily_volume",
        "volatility",
        "participation_rate",
        "commission_cost",
        "regulatory_fee_cost",
        "spread_cost",
        "impact_cost",
        "latency_cost",
        "borrow_cost",
        "capacity_cost",
        "total_cost",
        "position_quantity_before",
        "position_quantity_after",
        "cash_before",
        "cash_after",
        "source_transaction_cost_model_id",
        "source_slippage_model_id",
        "local_cost_model_id",
        "local_slippage_model_id",
        "synthetic",
        "simulated_paper_only",
        "local_mock_only",
        "external_submission",
        "live_path_absent",
    )
    for field in compared_fields:
        expected = getattr(entry, field)
        observed = row[field]
        if hasattr(expected, "value"):
            expected = expected.value
        _require(observed == expected, f"persisted Phase 10 ledger column {field} conflicts")
    _ledger_payload(entry)
    return entry


class _ConnectionBoundCreation:
    """Find or create one simulation without leaving its serialized transaction."""

    def __init__(
        self,
        repository: PaperRepository,
        connection: Connection,
        key: str,
    ) -> None:
        self._repository = repository
        self._connection = connection
        self._key = key

    def find_by_idempotency_key(self, key: str) -> PaperSimulationArtifact | None:
        _require(key == self._key, "serialized Phase 10 creation key changed during lookup")
        try:
            return self._repository._find_by_idempotency_key(self._connection, key)
        except (PaperArtifactNotFound, PaperRepositoryConflict):
            raise
        except (TypeError, ValueError, ValidationError) as exc:
            raise PaperRepositoryConflict("persisted Phase 10 simulation is invalid") from exc

    def create_simulation(self, artifact: PaperSimulationArtifact) -> PaperSimulationArtifact:
        _require(
            artifact.simulation_idempotency_key == self._key,
            "serialized Phase 10 creation key changed before persistence",
        )
        try:
            return self._repository._create_simulation(self._connection, artifact)
        except (PaperArtifactNotFound, PaperRepositoryConflict):
            raise
        except (TypeError, ValueError, ValidationError) as exc:
            raise PaperRepositoryConflict(
                "immutable Phase 10 simulation failed canonical validation"
            ) from exc


class PaperRepository:
    """Persist complete immutable local-simulation bundles."""

    def __init__(self, database_url: str | None = None, *, engine: Engine | None = None) -> None:
        if database_url is None and engine is None:
            raise ValueError("database_url or engine is required")
        self.engine = engine or create_engine(str(database_url), pool_pre_ping=True)
        self._owns_engine = engine is None

    def dispose(self) -> None:
        if self._owns_engine:
            self.engine.dispose()

    @classmethod
    def _find_by_idempotency_key(
        cls,
        connection: Connection,
        key: str,
    ) -> PaperSimulationArtifact | None:
        row = _row_by_identity(
            connection,
            column="simulation_idempotency_key",
            value=key,
        )
        if row is None:
            return None
        return cls._load_simulation(connection, row["simulation_run_id"], root_row=row)

    @staticmethod
    def _load_simulation(
        connection: Connection,
        simulation_run_id: UUID,
        *,
        root_row: RowMapping | None = None,
    ) -> PaperSimulationArtifact:
        row = root_row
        if row is None:
            row = _row_by_identity(
                connection,
                column="simulation_run_id",
                value=simulation_run_id,
            )
        if row is None:
            raise PaperArtifactNotFound(f"paper simulation {simulation_run_id} was not found")
        payload = dict(row["artifact_payload"])
        _require(
            domain_sha256(PHASE10_ARTIFACT_HASH_DOMAIN, payload) == row["artifact_sha256"],
            "persisted Phase 10 artifact payload failed hash revalidation",
        )

        check_rows = list(
            connection.execute(
                text(
                    "SELECT * FROM paper_simulation_checks "
                    "WHERE simulation_run_id = :run_id ORDER BY ordinal"
                ),
                {"run_id": simulation_run_id},
            ).mappings()
        )
        checks = tuple(_validate_check_row(item) for item in check_rows)
        ledger_rows = list(
            connection.execute(
                text(
                    "SELECT * FROM paper_simulation_ledger_entries "
                    "WHERE simulation_run_id = :run_id ORDER BY ordinal"
                ),
                {"run_id": simulation_run_id},
            ).mappings()
        )
        ledger_entries = tuple(_validate_ledger_row(item) for item in ledger_rows)
        _require(
            _same(payload.get("checks"), checks),
            "persisted Phase 10 checks conflict with the root artifact",
        )
        _require(
            _same(payload.get("ledger_entries"), ledger_entries),
            "persisted Phase 10 ledger conflicts with the root artifact",
        )
        payload["checks"] = checks
        payload["ledger_entries"] = ledger_entries
        artifact = PaperSimulationArtifact.model_validate(
            {
                **payload,
                "simulation_run_id": row["simulation_run_id"],
                "artifact_sha256": row["artifact_sha256"],
                "created_at_utc": row["created_at_utc"],
            }
        )
        configuration = artifact.configuration
        column_values: dict[str, object] = {
            "artifact_schema_version": artifact.artifact_schema_version,
            "request_fingerprint_sha256": artifact.request_fingerprint_sha256,
            "currentness_state_sha256": artifact.currentness_state_sha256,
            "simulation_idempotency_key": artifact.simulation_idempotency_key,
            "source_assessment_id": artifact.source_assessment_id,
            "source_assessment_artifact_sha256": artifact.source_assessment_artifact_sha256,
            "transition_assessment_id": artifact.transition_assessment_id,
            "transition_assessment_artifact_sha256": (
                artifact.transition_assessment_artifact_sha256
            ),
            "transition_currentness_state_sha256": (artifact.transition_currentness_state_sha256),
            "transition_revocation_set_sha256": artifact.transition_revocation_set_sha256,
            "revalidation_proof_id": (artifact.transition_revalidation_proof.revalidation_proof_id),
            "revalidation_proof_sha256": (
                artifact.transition_revalidation_proof.revalidation_proof_sha256
            ),
            "research_run_id": artifact.research_run_id,
            "research_artifact_sha256": artifact.research_artifact_sha256,
            "phase6_lineage_sha256": artifact.phase6_lineage_sha256,
            "approval_policy_version_id": artifact.approval_policy_version_id,
            "approval_policy_sha256": artifact.approval_policy_sha256,
            "approval_scope_version_id": artifact.approval_scope_version_id,
            "approval_scope_sha256": artifact.approval_scope_sha256,
            "human_authorization_evidence_id": artifact.human_authorization_evidence_id,
            "authorization_sha256": artifact.authorization_sha256,
            "risk_input_id": artifact.risk_input_id,
            "risk_input_sha256": artifact.risk_input_sha256,
            "configuration_instance_id": configuration.configuration_instance_id,
            "configuration_sha256": configuration.configuration_sha256,
            "configuration_id": configuration.configuration_id,
            "outcome": artifact.outcome.value,
            "phase10_code_version_git_sha": artifact.phase10_code_version_git_sha,
            "random_seed": artifact.random_seed,
            "raw_trial_count": artifact.raw_trial_count,
            "effective_trial_count": artifact.effective_trial_count,
            "decision_time_utc": artifact.decision_time_utc,
            "synthetic": True,
            "simulated_paper_only": True,
            "local_mock_only": True,
            "external_submission": False,
            "external_routing_absent": True,
            "live_path_absent": True,
            "no_personalized_investment_advice": True,
            "no_real_performance_claimed": True,
        }
        for column, expected in column_values.items():
            _require(row[column] == expected, f"persisted Phase 10 root column {column} conflicts")
        _require(
            _same(row["reason_codes"], artifact.reason_codes),
            "persisted Phase 10 reason codes conflict",
        )
        return artifact

    @staticmethod
    def _insert_simulation(connection: Connection, artifact: PaperSimulationArtifact) -> None:
        configuration = artifact.configuration
        _insert_row(
            connection,
            "paper_simulation_runs",
            {
                "simulation_run_id": artifact.simulation_run_id,
                "artifact_schema_version": artifact.artifact_schema_version,
                "artifact_sha256": artifact.artifact_sha256,
                "request_fingerprint_sha256": artifact.request_fingerprint_sha256,
                "currentness_state_sha256": artifact.currentness_state_sha256,
                "simulation_idempotency_key": artifact.simulation_idempotency_key,
                "source_assessment_id": artifact.source_assessment_id,
                "source_assessment_artifact_sha256": artifact.source_assessment_artifact_sha256,
                "transition_assessment_id": artifact.transition_assessment_id,
                "transition_assessment_artifact_sha256": (
                    artifact.transition_assessment_artifact_sha256
                ),
                "transition_currentness_state_sha256": (
                    artifact.transition_currentness_state_sha256
                ),
                "transition_revocation_set_sha256": artifact.transition_revocation_set_sha256,
                "revalidation_proof_id": (
                    artifact.transition_revalidation_proof.revalidation_proof_id
                ),
                "revalidation_proof_sha256": (
                    artifact.transition_revalidation_proof.revalidation_proof_sha256
                ),
                "research_run_id": artifact.research_run_id,
                "research_artifact_sha256": artifact.research_artifact_sha256,
                "phase6_lineage_sha256": artifact.phase6_lineage_sha256,
                "approval_policy_version_id": artifact.approval_policy_version_id,
                "approval_policy_sha256": artifact.approval_policy_sha256,
                "approval_scope_version_id": artifact.approval_scope_version_id,
                "approval_scope_sha256": artifact.approval_scope_sha256,
                "human_authorization_evidence_id": artifact.human_authorization_evidence_id,
                "authorization_sha256": artifact.authorization_sha256,
                "risk_input_id": artifact.risk_input_id,
                "risk_input_sha256": artifact.risk_input_sha256,
                "configuration_instance_id": configuration.configuration_instance_id,
                "configuration_sha256": configuration.configuration_sha256,
                "configuration_id": configuration.configuration_id,
                "outcome": artifact.outcome.value,
                "reason_codes": canonicalize(artifact.reason_codes),
                "phase10_code_version_git_sha": artifact.phase10_code_version_git_sha,
                "random_seed": artifact.random_seed,
                "raw_trial_count": artifact.raw_trial_count,
                "effective_trial_count": artifact.effective_trial_count,
                "decision_time_utc": artifact.decision_time_utc,
                "synthetic": artifact.synthetic,
                "simulated_paper_only": artifact.simulated_paper_only,
                "local_mock_only": artifact.local_mock_only,
                "external_submission": artifact.external_submission,
                "external_routing_absent": artifact.external_routing_absent,
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
                "paper_simulation_checks",
                {
                    "simulation_run_id": artifact.simulation_run_id,
                    "simulation_artifact_sha256": artifact.artifact_sha256,
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
        for entry in artifact.ledger_entries:
            row = entry.model_dump(mode="python")
            row["simulation_artifact_sha256"] = artifact.artifact_sha256
            row["payload"] = _ledger_payload(entry)
            _insert_row(
                connection,
                "paper_simulation_ledger_entries",
                row,
                json_columns=frozenset({"payload"}),
            )

    def find_by_idempotency_key(self, key: str) -> PaperSimulationArtifact | None:
        try:
            with self.engine.connect() as connection:
                return self._find_by_idempotency_key(connection, key)
        except (PaperArtifactNotFound, PaperRepositoryConflict):
            raise
        except (TypeError, ValueError, ValidationError) as exc:
            raise PaperRepositoryConflict("persisted Phase 10 simulation is invalid") from exc
        except DBAPIError as exc:
            raise PaperRepositoryConflict("Phase 10 simulation could not be loaded") from exc

    def _create_simulation(
        self,
        connection: Connection,
        artifact: PaperSimulationArtifact,
    ) -> PaperSimulationArtifact:
        # Every creation path starts with the same workflow lock. A scoped
        # session already owns it on this connection, so this is a safe
        # reentrant acquisition and keeps the standalone path in the same
        # WORKFLOW -> AUTH -> KEY -> POLICY -> SCOPE order.
        _lock(connection, _workflow_lock_identity(artifact.simulation_idempotency_key))
        _lock(connection, artifact.human_authorization_evidence_id)
        _lock(connection, artifact.simulation_idempotency_key)
        transition = (
            connection.execute(
                text(
                    "SELECT revocation_ids FROM approval_assessments "
                    "WHERE assessment_id = :assessment_id "
                    "AND artifact_sha256 = :artifact_sha256"
                ),
                {
                    "assessment_id": artifact.transition_assessment_id,
                    "artifact_sha256": artifact.transition_assessment_artifact_sha256,
                },
            )
            .mappings()
            .one_or_none()
        )
        if transition is None:
            raise PaperArtifactNotFound("transition approval assessment was not found")
        current_revocations = tuple(
            str(row["revocation_id"])
            for row in connection.execute(
                text(
                    "SELECT revocation_id FROM approval_revocations "
                    "WHERE human_authorization_evidence_id = :authorization_id "
                    "ORDER BY revocation_id::text"
                ),
                {"authorization_id": artifact.human_authorization_evidence_id},
            ).mappings()
        )
        _require(
            _same(transition["revocation_ids"], current_revocations),
            "authorization revocation set changed before simulation persistence",
        )
        existing = _row_by_identity(
            connection,
            column="simulation_idempotency_key",
            value=artifact.simulation_idempotency_key,
        )
        if existing is not None:
            loaded = self._load_simulation(
                connection,
                existing["simulation_run_id"],
                root_row=existing,
            )
            if loaded.source_assessment_id != artifact.source_assessment_id:
                raise PaperRepositoryConflict(
                    "simulation idempotency key is bound to different evidence"
                )
            return loaded
        authority_dimensions = (
            connection.execute(
                text(
                    "SELECT policy.policy_id, scope.scope_id "
                    "FROM approval_policies AS policy "
                    "JOIN approval_scopes AS scope ON "
                    "scope.approval_scope_version_id = :scope_version_id "
                    "AND scope.scope_sha256 = :scope_sha256 "
                    "WHERE policy.approval_policy_version_id = :policy_version_id "
                    "AND policy.policy_sha256 = :policy_sha256"
                ),
                {
                    "policy_version_id": artifact.approval_policy_version_id,
                    "policy_sha256": artifact.approval_policy_sha256,
                    "scope_version_id": artifact.approval_scope_version_id,
                    "scope_sha256": artifact.approval_scope_sha256,
                },
            )
            .mappings()
            .one_or_none()
        )
        if authority_dimensions is None:
            raise PaperArtifactNotFound("policy or scope authority evidence was not found")
        _lock(connection, f"phase10-policy:{authority_dimensions['policy_id']}")
        _lock(connection, f"phase10-scope:{authority_dimensions['scope_id']}")
        fingerprint_row = _row_by_identity(
            connection,
            column="request_fingerprint_sha256",
            value=artifact.request_fingerprint_sha256,
        )
        if fingerprint_row is not None:
            raise PaperRepositoryConflict(
                "simulation request fingerprint is bound to another idempotency key"
            )
        self._insert_simulation(connection, artifact)
        return self._load_simulation(connection, artifact.simulation_run_id)

    @contextmanager
    def serialized_creation(self, key: str) -> Iterator[_ConnectionBoundCreation]:
        try:
            with self.engine.begin() as connection:
                _lock(connection, _workflow_lock_identity(key))
                yield _ConnectionBoundCreation(self, connection, key)
        except (PaperArtifactNotFound, PaperRepositoryConflict):
            raise
        except DBAPIError as exc:
            raise PaperRepositoryConflict(
                "immutable Phase 10 serialized creation could not be stored"
            ) from exc

    def create_simulation(self, artifact: PaperSimulationArtifact) -> PaperSimulationArtifact:
        try:
            with self.engine.begin() as connection:
                return self._create_simulation(connection, artifact)
        except (PaperArtifactNotFound, PaperRepositoryConflict):
            raise
        except (TypeError, ValueError, ValidationError) as exc:
            raise PaperRepositoryConflict(
                "immutable Phase 10 simulation failed canonical validation"
            ) from exc
        except DBAPIError as exc:
            raise PaperRepositoryConflict(
                "immutable Phase 10 simulation could not be stored"
            ) from exc

    def get_simulation(self, simulation_run_id: UUID) -> PaperSimulationArtifact:
        try:
            with self.engine.connect() as connection:
                return self._load_simulation(connection, simulation_run_id)
        except (PaperArtifactNotFound, PaperRepositoryConflict):
            raise
        except (TypeError, ValueError, ValidationError) as exc:
            raise PaperRepositoryConflict("persisted Phase 10 simulation is invalid") from exc
        except DBAPIError as exc:
            raise PaperRepositoryConflict("Phase 10 simulation could not be loaded") from exc

    def list_simulations(
        self,
        *,
        source_assessment_id: UUID | None,
        limit: int = 100,
    ) -> list[PaperSimulationSummary]:
        if limit < 1 or limit > 100:
            raise ValueError("limit must be between 1 and 100")
        where = "" if source_assessment_id is None else "WHERE source_assessment_id = :source_id "
        parameters: dict[str, object] = {"limit": limit}
        if source_assessment_id is not None:
            parameters["source_id"] = source_assessment_id
        try:
            with self.engine.connect() as connection:
                rows = connection.execute(
                    text(
                        "SELECT simulation_run_id, artifact_sha256, source_assessment_id, "
                        "transition_assessment_id, configuration_id, outcome, reason_codes, "
                        "decision_time_utc, created_at_utc, synthetic, simulated_paper_only, "
                        "local_mock_only, external_submission, live_path_absent, "
                        "no_personalized_investment_advice, no_real_performance_claimed "
                        "FROM paper_simulation_runs "
                        f"{where}ORDER BY created_at_utc DESC, simulation_run_id DESC LIMIT :limit"
                    ),
                    parameters,
                ).mappings()
                return [PaperSimulationSummary.model_validate(dict(row)) for row in rows]
        except (TypeError, ValueError, ValidationError) as exc:
            raise PaperRepositoryConflict("Phase 10 simulation summaries are invalid") from exc
        except DBAPIError as exc:
            raise PaperRepositoryConflict("Phase 10 simulations could not be listed") from exc


__all__ = [
    "PaperArtifactNotFound",
    "PaperRepository",
    "PaperRepositoryConflict",
]
