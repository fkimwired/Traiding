"""Append-only PostgreSQL persistence for Phase 7 approval evidence."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from decimal import Decimal
from typing import Any, TypeVar, cast
from uuid import UUID

from fable5_data.canonical import canonical_json_bytes, canonicalize, domain_sha256
from pydantic import BaseModel
from sqlalchemy import Engine, bindparam, create_engine, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import Connection, RowMapping
from sqlalchemy.exc import DBAPIError

from fable5_risk.canonical import (
    PHASE7_ASSESSMENT_ARTIFACT_HASH_DOMAIN,
    PHASE7_AUTHORIZATION_HASH_DOMAIN,
    PHASE7_POLICY_HASH_DOMAIN,
    PHASE7_REVOCATION_ARTIFACT_HASH_DOMAIN,
    PHASE7_RISK_INPUT_HASH_DOMAIN,
    PHASE7_SCOPE_HASH_DOMAIN,
)
from fable5_risk.contracts import (
    ApprovalAssessmentArtifact,
    ApprovalAssessmentSummary,
    ApprovalCheckResult,
    ApprovalPolicy,
    ApprovalRiskInput,
    ApprovalScope,
    AuthorizationRevocationArtifact,
    AuthorizationRevocationSummary,
    HumanAuthorizationEvidence,
)


class RiskArtifactNotFound(LookupError):
    """The requested immutable Phase 7 artifact does not exist."""


class RiskRepositoryConflict(RuntimeError):
    """Persisted Phase 7 evidence conflicts with its canonical artifact."""


TModel = TypeVar("TModel", bound=BaseModel)


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
        raise RiskRepositoryConflict("immutable Phase 7 payload must be an object")
    return cast(dict[str, Any], normalized)


def _model_payload(model: BaseModel, *, exclude: set[str]) -> dict[str, Any]:
    return _normalized_object(model.model_dump(mode="python", exclude=exclude))


def _same(left: object, right: object) -> bool:
    return bool(canonical_json_bytes(left) == canonical_json_bytes(right))


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RiskRepositoryConflict(message)


def _lock(connection: Connection, value: UUID | str) -> None:
    connection.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:identity, 0))"),
        {"identity": str(value)},
    )


def _evidence_payload(model: BaseModel, id_field: str, hash_field: str) -> dict[str, Any]:
    return _model_payload(model, exclude={id_field, hash_field})


def _assessment_payload(artifact: ApprovalAssessmentArtifact) -> dict[str, Any]:
    payload = _model_payload(
        artifact,
        exclude={"assessment_id", "artifact_sha256", "created_at_utc"},
    )
    if domain_sha256(PHASE7_ASSESSMENT_ARTIFACT_HASH_DOMAIN, payload) != artifact.artifact_sha256:
        raise RiskRepositoryConflict("Phase 7 assessment artifact hash does not match payload")
    return payload


def _revocation_payload(artifact: AuthorizationRevocationArtifact) -> dict[str, Any]:
    payload = _model_payload(
        artifact,
        exclude={"revocation_id", "artifact_sha256", "created_at_utc"},
    )
    if domain_sha256(PHASE7_REVOCATION_ARTIFACT_HASH_DOMAIN, payload) != artifact.artifact_sha256:
        raise RiskRepositoryConflict("Phase 7 revocation artifact hash does not match payload")
    return payload


def _row_by_identity(
    connection: Connection,
    *,
    table: str,
    id_column: str,
    identity: UUID,
) -> RowMapping | None:
    return (
        connection.execute(
            text(f"SELECT * FROM {table} WHERE {id_column} = :identity"),
            {"identity": identity},
        )
        .mappings()
        .one_or_none()
    )


def _validate_policy_row(row: RowMapping) -> ApprovalPolicy:
    payload = dict(row["payload"])
    _require(
        domain_sha256(PHASE7_POLICY_HASH_DOMAIN, payload) == row["policy_sha256"],
        "persisted Phase 7 policy failed hash revalidation",
    )
    policy = ApprovalPolicy.model_validate(
        {
            **payload,
            "approval_policy_version_id": row["approval_policy_version_id"],
            "policy_sha256": row["policy_sha256"],
        }
    )
    _require(
        row["schema_version"] == policy.schema_version
        and row["policy_id"] == policy.policy_id
        and row["policy_version"] == policy.policy_version
        and row["valid_from_utc"] == policy.valid_from_utc
        and row["expires_at_utc"] == policy.expires_at_utc
        and row["authorization_max_age_seconds"] == policy.authorization_max_age_seconds
        and row["risk_input_max_age_seconds"] == policy.risk_input_max_age_seconds
        and _same(row["required_check_codes"], policy.required_check_codes)
        and Decimal(row["max_notional"]) == policy.max_notional
        and Decimal(row["max_gross_exposure"]) == policy.max_gross_exposure
        and Decimal(row["max_abs_net_exposure"]) == policy.max_abs_net_exposure
        and Decimal(row["max_sector_exposure"]) == policy.max_sector_exposure
        and Decimal(row["max_concentration"]) == policy.max_concentration
        and Decimal(row["min_liquidity"]) == policy.min_liquidity
        and Decimal(row["max_turnover"]) == policy.max_turnover
        and Decimal(row["max_volatility"]) == policy.max_volatility
        and Decimal(row["max_daily_loss"]) == policy.max_daily_loss
        and Decimal(row["max_drawdown"]) == policy.max_drawdown
        and row["synthetic"] is True,
        "persisted Phase 7 policy columns conflict with payload",
    )
    return policy


def _validate_scope_row(row: RowMapping) -> ApprovalScope:
    payload = dict(row["payload"])
    _require(
        domain_sha256(PHASE7_SCOPE_HASH_DOMAIN, payload) == row["scope_sha256"],
        "persisted Phase 7 scope failed hash revalidation",
    )
    scope = ApprovalScope.model_validate(
        {
            **payload,
            "approval_scope_version_id": row["approval_scope_version_id"],
            "scope_sha256": row["scope_sha256"],
        }
    )
    _require(
        row["schema_version"] == scope.schema_version
        and row["scope_id"] == scope.scope_id
        and row["scope_version"] == scope.scope_version
        and row["research_run_id"] == scope.research_run_id
        and row["research_artifact_sha256"] == scope.research_artifact_sha256
        and row["approval_policy_version_id"] == scope.approval_policy_version_id
        and _same(row["permitted_universe_ids"], scope.permitted_universe_ids)
        and Decimal(row["max_notional"]) == scope.max_notional
        and row["valid_from_utc"] == scope.valid_from_utc
        and row["expires_at_utc"] == scope.expires_at_utc
        and row["synthetic"] is True,
        "persisted Phase 7 scope columns conflict with payload",
    )
    return scope


def _validate_authorization_row(row: RowMapping) -> HumanAuthorizationEvidence:
    payload = dict(row["payload"])
    _require(
        domain_sha256(PHASE7_AUTHORIZATION_HASH_DOMAIN, payload) == row["authorization_sha256"],
        "persisted Phase 7 authorization failed hash revalidation",
    )
    authorization = HumanAuthorizationEvidence.model_validate(
        {
            **payload,
            "human_authorization_evidence_id": row["human_authorization_evidence_id"],
            "authorization_sha256": row["authorization_sha256"],
        }
    )
    _require(
        row["schema_version"] == authorization.schema_version
        and row["research_run_id"] == authorization.research_run_id
        and row["research_artifact_sha256"] == authorization.research_artifact_sha256
        and row["approval_policy_version_id"] == authorization.approval_policy_version_id
        and row["approval_scope_version_id"] == authorization.approval_scope_version_id
        and row["authorized_by"] == authorization.authorized_by
        and row["authorized_role"] == authorization.authorized_role
        and row["rationale"] == authorization.rationale
        and row["authorized_at_utc"] == authorization.authorized_at_utc
        and row["review_at_utc"] == authorization.review_at_utc
        and row["expires_at_utc"] == authorization.expires_at_utc
        and row["human_controlled"] is True
        and row["synthetic"] is True,
        "persisted Phase 7 authorization columns conflict with payload",
    )
    return authorization


def _validate_risk_input_row(row: RowMapping) -> ApprovalRiskInput:
    payload = dict(row["payload"])
    _require(
        domain_sha256(PHASE7_RISK_INPUT_HASH_DOMAIN, payload) == row["risk_input_sha256"],
        "persisted Phase 7 risk input failed hash revalidation",
    )
    risk_input = ApprovalRiskInput.model_validate(
        {
            **payload,
            "risk_input_id": row["risk_input_id"],
            "risk_input_sha256": row["risk_input_sha256"],
        }
    )
    scalar_fields = (
        "global_control_clear",
        "strategy_control_clear",
        "data_quality_control_clear",
        "market_calendar_open",
        "duplicate_context_clear",
    )
    decimal_fields = (
        "proposed_notional",
        "gross_exposure",
        "net_exposure",
        "sector_exposure",
        "concentration",
        "available_liquidity",
        "turnover",
        "volatility",
        "daily_loss",
        "drawdown",
    )
    _require(
        row["schema_version"] == risk_input.schema_version
        and row["research_run_id"] == risk_input.research_run_id
        and row["research_artifact_sha256"] == risk_input.research_artifact_sha256
        and row["approval_policy_version_id"] == risk_input.approval_policy_version_id
        and row["approval_scope_version_id"] == risk_input.approval_scope_version_id
        and row["universe_id"] == risk_input.universe_id
        and row["observed_at_utc"] == risk_input.observed_at_utc
        and all(row[field] is getattr(risk_input, field) for field in scalar_fields)
        and all(
            (row[field] is None and getattr(risk_input, field) is None)
            or (
                row[field] is not None
                and getattr(risk_input, field) is not None
                and Decimal(row[field]) == getattr(risk_input, field)
            )
            for field in decimal_fields
        )
        and row["synthetic"] is True,
        "persisted Phase 7 risk-input columns conflict with payload",
    )
    return risk_input


class RiskRepository:
    """Persist independent evidence and immutable Phase 7 decisions."""

    def __init__(self, database_url: str | None = None, *, engine: Engine | None = None) -> None:
        if database_url is None and engine is None:
            raise ValueError("database_url or engine is required")
        self.engine = engine or create_engine(str(database_url), pool_pre_ping=True)
        self._owns_engine = engine is None

    def dispose(self) -> None:
        if self._owns_engine:
            self.engine.dispose()

    @staticmethod
    def _insert_policy(connection: Connection, policy: ApprovalPolicy) -> None:
        _insert_row(
            connection,
            "approval_policies",
            {
                "approval_policy_version_id": policy.approval_policy_version_id,
                "schema_version": policy.schema_version,
                "policy_id": policy.policy_id,
                "policy_version": policy.policy_version,
                "policy_sha256": policy.policy_sha256,
                "valid_from_utc": policy.valid_from_utc,
                "expires_at_utc": policy.expires_at_utc,
                "risk_input_max_age_seconds": policy.risk_input_max_age_seconds,
                "authorization_max_age_seconds": policy.authorization_max_age_seconds,
                "required_check_codes": canonicalize(policy.required_check_codes),
                "max_notional": policy.max_notional,
                "max_gross_exposure": policy.max_gross_exposure,
                "max_abs_net_exposure": policy.max_abs_net_exposure,
                "max_sector_exposure": policy.max_sector_exposure,
                "max_concentration": policy.max_concentration,
                "min_liquidity": policy.min_liquidity,
                "max_turnover": policy.max_turnover,
                "max_volatility": policy.max_volatility,
                "max_daily_loss": policy.max_daily_loss,
                "max_drawdown": policy.max_drawdown,
                "synthetic": policy.synthetic,
                "payload": _evidence_payload(policy, "approval_policy_version_id", "policy_sha256"),
            },
            json_columns=frozenset({"required_check_codes", "payload"}),
        )

    @staticmethod
    def _insert_scope(connection: Connection, scope: ApprovalScope) -> None:
        _insert_row(
            connection,
            "approval_scopes",
            {
                "approval_scope_version_id": scope.approval_scope_version_id,
                "schema_version": scope.schema_version,
                "scope_id": scope.scope_id,
                "scope_version": scope.scope_version,
                "scope_sha256": scope.scope_sha256,
                "research_run_id": scope.research_run_id,
                "research_artifact_sha256": scope.research_artifact_sha256,
                "approval_policy_version_id": scope.approval_policy_version_id,
                "permitted_universe_ids": canonicalize(scope.permitted_universe_ids),
                "max_notional": scope.max_notional,
                "valid_from_utc": scope.valid_from_utc,
                "expires_at_utc": scope.expires_at_utc,
                "synthetic": scope.synthetic,
                "payload": _evidence_payload(scope, "approval_scope_version_id", "scope_sha256"),
            },
            json_columns=frozenset({"permitted_universe_ids", "payload"}),
        )

    @staticmethod
    def _insert_authorization(
        connection: Connection, authorization: HumanAuthorizationEvidence
    ) -> None:
        _insert_row(
            connection,
            "approval_authorizations",
            {
                "human_authorization_evidence_id": (authorization.human_authorization_evidence_id),
                "schema_version": authorization.schema_version,
                "authorization_sha256": authorization.authorization_sha256,
                "research_run_id": authorization.research_run_id,
                "research_artifact_sha256": authorization.research_artifact_sha256,
                "approval_policy_version_id": authorization.approval_policy_version_id,
                "approval_scope_version_id": authorization.approval_scope_version_id,
                "authorized_by": authorization.authorized_by,
                "authorized_role": authorization.authorized_role,
                "rationale": authorization.rationale,
                "authorized_at_utc": authorization.authorized_at_utc,
                "review_at_utc": authorization.review_at_utc,
                "expires_at_utc": authorization.expires_at_utc,
                "human_controlled": authorization.human_controlled,
                "synthetic": authorization.synthetic,
                "payload": _evidence_payload(
                    authorization,
                    "human_authorization_evidence_id",
                    "authorization_sha256",
                ),
            },
            json_columns=frozenset({"payload"}),
        )

    @staticmethod
    def _insert_risk_input(connection: Connection, risk_input: ApprovalRiskInput) -> None:
        row = {
            "risk_input_id": risk_input.risk_input_id,
            "schema_version": risk_input.schema_version,
            "risk_input_sha256": risk_input.risk_input_sha256,
            "research_run_id": risk_input.research_run_id,
            "research_artifact_sha256": risk_input.research_artifact_sha256,
            "approval_policy_version_id": risk_input.approval_policy_version_id,
            "approval_scope_version_id": risk_input.approval_scope_version_id,
            "universe_id": risk_input.universe_id,
            "observed_at_utc": risk_input.observed_at_utc,
            "global_control_clear": risk_input.global_control_clear,
            "strategy_control_clear": risk_input.strategy_control_clear,
            "data_quality_control_clear": risk_input.data_quality_control_clear,
            "market_calendar_open": risk_input.market_calendar_open,
            "duplicate_context_clear": risk_input.duplicate_context_clear,
            "proposed_notional": risk_input.proposed_notional,
            "gross_exposure": risk_input.gross_exposure,
            "net_exposure": risk_input.net_exposure,
            "sector_exposure": risk_input.sector_exposure,
            "concentration": risk_input.concentration,
            "available_liquidity": risk_input.available_liquidity,
            "turnover": risk_input.turnover,
            "volatility": risk_input.volatility,
            "daily_loss": risk_input.daily_loss,
            "drawdown": risk_input.drawdown,
            "synthetic": risk_input.synthetic,
            "payload": _evidence_payload(risk_input, "risk_input_id", "risk_input_sha256"),
        }
        _insert_row(
            connection,
            "approval_risk_inputs",
            row,
            json_columns=frozenset({"payload"}),
        )

    @staticmethod
    def _ensure_evidence(
        connection: Connection,
        *,
        table: str,
        id_column: str,
        identity: UUID,
        expected: TModel,
        validator: Any,
        inserter: Any,
    ) -> TModel:
        row = _row_by_identity(
            connection,
            table=table,
            id_column=id_column,
            identity=identity,
        )
        if row is None:
            inserter(connection, expected)
            row = _row_by_identity(
                connection,
                table=table,
                id_column=id_column,
                identity=identity,
            )
        if row is None:
            raise RiskRepositoryConflict("Phase 7 evidence insert was not observable")
        loaded = validator(row)
        if not _same(loaded, expected):
            raise RiskRepositoryConflict(
                "Phase 7 evidence identity is bound to different immutable content"
            )
        return cast(TModel, loaded)

    def provision_evidence(
        self,
        policy: ApprovalPolicy,
        scope: ApprovalScope,
        authorization: HumanAuthorizationEvidence,
        risk_input: ApprovalRiskInput,
    ) -> tuple[ApprovalPolicy, ApprovalScope, HumanAuthorizationEvidence, ApprovalRiskInput]:
        """Atomically provision independently constructed, server-owned evidence.

        This is deliberately not part of the public workflow.  Tests and the
        acceptance verifier call it before assessment creation to model the
        separate policy, reviewer, scope, and risk evidence authorities.
        """

        try:
            with self.engine.begin() as connection:
                for identity in sorted(
                    (
                        policy.policy_sha256,
                        scope.scope_sha256,
                        authorization.authorization_sha256,
                        risk_input.risk_input_sha256,
                    )
                ):
                    _lock(connection, identity)
                loaded_policy = self._ensure_evidence(
                    connection,
                    table="approval_policies",
                    id_column="approval_policy_version_id",
                    identity=policy.approval_policy_version_id,
                    expected=policy,
                    validator=_validate_policy_row,
                    inserter=self._insert_policy,
                )
                loaded_scope = self._ensure_evidence(
                    connection,
                    table="approval_scopes",
                    id_column="approval_scope_version_id",
                    identity=scope.approval_scope_version_id,
                    expected=scope,
                    validator=_validate_scope_row,
                    inserter=self._insert_scope,
                )
                loaded_authorization = self._ensure_evidence(
                    connection,
                    table="approval_authorizations",
                    id_column="human_authorization_evidence_id",
                    identity=authorization.human_authorization_evidence_id,
                    expected=authorization,
                    validator=_validate_authorization_row,
                    inserter=self._insert_authorization,
                )
                loaded_risk = self._ensure_evidence(
                    connection,
                    table="approval_risk_inputs",
                    id_column="risk_input_id",
                    identity=risk_input.risk_input_id,
                    expected=risk_input,
                    validator=_validate_risk_input_row,
                    inserter=self._insert_risk_input,
                )
                return (
                    loaded_policy,
                    loaded_scope,
                    loaded_authorization,
                    loaded_risk,
                )
        except RiskRepositoryConflict:
            raise
        except (TypeError, ValueError) as exc:
            raise RiskRepositoryConflict(
                "immutable Phase 7 evidence failed canonical validation"
            ) from exc
        except DBAPIError as exc:
            raise RiskRepositoryConflict(
                "immutable Phase 7 evidence could not be provisioned"
            ) from exc

    def get_policy(self, version_id: UUID) -> ApprovalPolicy:
        return self._get_evidence(
            table="approval_policies",
            id_column="approval_policy_version_id",
            identity=version_id,
            validator=_validate_policy_row,
            kind="approval policy",
        )

    def get_scope(self, version_id: UUID) -> ApprovalScope:
        return self._get_evidence(
            table="approval_scopes",
            id_column="approval_scope_version_id",
            identity=version_id,
            validator=_validate_scope_row,
            kind="approval scope",
        )

    def get_authorization(self, evidence_id: UUID) -> HumanAuthorizationEvidence:
        return self._get_evidence(
            table="approval_authorizations",
            id_column="human_authorization_evidence_id",
            identity=evidence_id,
            validator=_validate_authorization_row,
            kind="human authorization evidence",
        )

    def get_risk_input(self, risk_input_id: UUID) -> ApprovalRiskInput:
        return self._get_evidence(
            table="approval_risk_inputs",
            id_column="risk_input_id",
            identity=risk_input_id,
            validator=_validate_risk_input_row,
            kind="approval risk input",
        )

    def _get_evidence(
        self,
        *,
        table: str,
        id_column: str,
        identity: UUID,
        validator: Callable[[RowMapping], TModel],
        kind: str,
    ) -> TModel:
        try:
            with self.engine.connect() as connection:
                row = _row_by_identity(
                    connection,
                    table=table,
                    id_column=id_column,
                    identity=identity,
                )
                if row is None:
                    raise RiskArtifactNotFound(f"{kind} {identity} was not found")
                return validator(row)
        except (RiskArtifactNotFound, RiskRepositoryConflict):
            raise
        except (TypeError, ValueError) as exc:
            raise RiskRepositoryConflict(f"persisted {kind} is invalid") from exc
        except DBAPIError as exc:
            raise RiskRepositoryConflict(f"persisted {kind} could not be loaded") from exc

    @staticmethod
    def _assessment_row(connection: Connection, assessment_id: UUID) -> RowMapping | None:
        return _row_by_identity(
            connection,
            table="approval_assessments",
            id_column="assessment_id",
            identity=assessment_id,
        )

    @staticmethod
    def _assessment_by_fingerprint(connection: Connection, fingerprint: str) -> RowMapping | None:
        return (
            connection.execute(
                text(
                    "SELECT * FROM approval_assessments "
                    "WHERE request_fingerprint_sha256 = :fingerprint"
                ),
                {"fingerprint": fingerprint},
            )
            .mappings()
            .one_or_none()
        )

    @classmethod
    def _load_assessment(
        cls,
        connection: Connection,
        assessment_id: UUID,
        *,
        root_row: RowMapping | None = None,
    ) -> ApprovalAssessmentArtifact:
        row = root_row or cls._assessment_row(connection, assessment_id)
        if row is None:
            raise RiskArtifactNotFound(f"approval assessment {assessment_id} was not found")
        payload = dict(row["artifact_payload"])
        _require(
            domain_sha256(PHASE7_ASSESSMENT_ARTIFACT_HASH_DOMAIN, payload)
            == row["artifact_sha256"],
            "persisted Phase 7 assessment payload failed hash revalidation",
        )
        artifact = ApprovalAssessmentArtifact.model_validate(
            {
                **payload,
                "assessment_id": row["assessment_id"],
                "artifact_sha256": row["artifact_sha256"],
                "created_at_utc": row["created_at_utc"],
            }
        )
        _require(
            row["artifact_schema_version"] == artifact.artifact_schema_version
            and row["request_fingerprint_sha256"] == artifact.request_fingerprint_sha256
            and row["currentness_state_sha256"] == artifact.currentness_state_sha256
            and row["revocation_set_sha256"] == artifact.revocation_set_sha256
            and row["research_run_id"] == artifact.research_run_id
            and row["research_artifact_sha256"] == artifact.phase6_lineage.research_artifact_sha256
            and row["approval_policy_version_id"] == artifact.approval_policy_version_id
            and row["approval_policy_sha256"] == artifact.approval_policy_sha256
            and row["approval_scope_version_id"] == artifact.approval_scope_version_id
            and row["approval_scope_sha256"] == artifact.approval_scope_sha256
            and row["human_authorization_evidence_id"] == artifact.human_authorization_evidence_id
            and row["authorization_sha256"] == artifact.authorization_sha256
            and row["risk_input_id"] == artifact.risk_input_id
            and row["risk_input_sha256"] == artifact.risk_input_sha256
            and row["phase6_lineage_sha256"] == artifact.phase6_lineage.lineage_sha256
            and _same(row["revocation_ids"], artifact.revocation_ids)
            and row["outcome"] == artifact.outcome.value
            and _same(row["reason_codes"], artifact.reason_codes)
            and row["phase7_code_version_git_sha"] == artifact.phase7_code_version_git_sha
            and row["synthetic"] is True
            and row["simulated_paper_only"] is True
            and row["execution_authorized"] is False
            and row["execution_ready"] is False
            and row["no_personalized_investment_advice"] is True
            and row["no_real_performance_claimed"] is True,
            "persisted Phase 7 assessment columns conflict with payload",
        )
        check_rows = list(
            connection.execute(
                text(
                    "SELECT * FROM approval_checks WHERE assessment_id = :assessment_id "
                    "ORDER BY ordinal"
                ),
                {"assessment_id": assessment_id},
            ).mappings()
        )
        checks: list[ApprovalCheckResult] = []
        for check_row in check_rows:
            check = ApprovalCheckResult.model_validate(dict(check_row["payload"]))
            _require(
                check_row["assessment_artifact_sha256"] == artifact.artifact_sha256
                and check_row["ordinal"] == check.ordinal
                and check_row["code"] == check.code.value
                and check_row["status"] == check.status.value
                and check_row["reason_code"] == check.reason_code
                and check_row["observed_value"] == check.observed_value
                and check_row["threshold_value"] == check.threshold_value
                and _same(check_row["evidence_sha256s"], check.evidence_sha256s)
                and check_row["check_sha256"] == check.check_sha256,
                "persisted Phase 7 check columns conflict with payload",
            )
            checks.append(check)
        _require(
            _same(tuple(checks), artifact.checks),
            "persisted Phase 7 assessment has an incomplete check registry",
        )
        return artifact

    @staticmethod
    def _current_revocation_rows(
        connection: Connection, authorization_id: UUID
    ) -> list[RowMapping]:
        return list(
            connection.execute(
                text(
                    "SELECT * FROM approval_revocations "
                    "WHERE human_authorization_evidence_id = :authorization_id "
                    "ORDER BY revocation_id::text"
                ),
                {"authorization_id": authorization_id},
            ).mappings()
        )

    @staticmethod
    def _insert_assessment(connection: Connection, artifact: ApprovalAssessmentArtifact) -> None:
        _insert_row(
            connection,
            "approval_assessments",
            {
                "assessment_id": artifact.assessment_id,
                "artifact_schema_version": artifact.artifact_schema_version,
                "artifact_sha256": artifact.artifact_sha256,
                "request_fingerprint_sha256": artifact.request_fingerprint_sha256,
                "currentness_state_sha256": artifact.currentness_state_sha256,
                "revocation_set_sha256": artifact.revocation_set_sha256,
                "research_run_id": artifact.research_run_id,
                "research_artifact_sha256": (artifact.phase6_lineage.research_artifact_sha256),
                "approval_policy_version_id": artifact.approval_policy_version_id,
                "approval_policy_sha256": artifact.approval_policy_sha256,
                "approval_scope_version_id": artifact.approval_scope_version_id,
                "approval_scope_sha256": artifact.approval_scope_sha256,
                "human_authorization_evidence_id": (artifact.human_authorization_evidence_id),
                "authorization_sha256": artifact.authorization_sha256,
                "risk_input_id": artifact.risk_input_id,
                "risk_input_sha256": artifact.risk_input_sha256,
                "phase6_lineage_sha256": artifact.phase6_lineage.lineage_sha256,
                "revocation_ids": canonicalize(artifact.revocation_ids),
                "outcome": artifact.outcome.value,
                "reason_codes": canonicalize(artifact.reason_codes),
                "phase7_code_version_git_sha": artifact.phase7_code_version_git_sha,
                "synthetic": artifact.synthetic,
                "simulated_paper_only": artifact.simulated_paper_only,
                "execution_authorized": artifact.execution_authorized,
                "execution_ready": artifact.execution_ready,
                "no_personalized_investment_advice": (artifact.no_personalized_investment_advice),
                "no_real_performance_claimed": artifact.no_real_performance_claimed,
                "artifact_payload": _assessment_payload(artifact),
            },
            json_columns=frozenset({"revocation_ids", "reason_codes", "artifact_payload"}),
        )
        for check in artifact.checks:
            _insert_row(
                connection,
                "approval_checks",
                {
                    "assessment_id": artifact.assessment_id,
                    "assessment_artifact_sha256": artifact.artifact_sha256,
                    "ordinal": check.ordinal,
                    "code": check.code.value,
                    "status": check.status.value,
                    "reason_code": check.reason_code,
                    "observed_value": check.observed_value,
                    "threshold_value": check.threshold_value,
                    "evidence_sha256s": canonicalize(check.evidence_sha256s),
                    "check_sha256": check.check_sha256,
                    "payload": _normalized_object(check.model_dump(mode="python")),
                },
                json_columns=frozenset({"evidence_sha256s", "payload"}),
            )

    def create_assessment(self, artifact: ApprovalAssessmentArtifact) -> ApprovalAssessmentArtifact:
        try:
            with self.engine.begin() as connection:
                # Both creation paths take the authorization lock first.  A
                # revocation that wins this race changes the immutable set and
                # makes a stale assessment artifact ineligible for insertion.
                _lock(connection, artifact.human_authorization_evidence_id)
                _lock(connection, artifact.request_fingerprint_sha256)
                current_rows = self._current_revocation_rows(
                    connection, artifact.human_authorization_evidence_id
                )
                current_ids = tuple(row["revocation_id"] for row in current_rows)
                if current_ids != artifact.revocation_ids:
                    raise RiskRepositoryConflict(
                        "authorization revocation set changed before assessment persistence"
                    )
                existing = self._assessment_by_fingerprint(
                    connection, artifact.request_fingerprint_sha256
                )
                if existing is not None:
                    loaded = self._load_assessment(
                        connection, existing["assessment_id"], root_row=existing
                    )
                    if loaded.artifact_sha256 != artifact.artifact_sha256 or not _same(
                        _assessment_payload(loaded), _assessment_payload(artifact)
                    ):
                        raise RiskRepositoryConflict(
                            "assessment request fingerprint is bound to different evidence"
                        )
                    return loaded
                self._insert_assessment(connection, artifact)
                return self._load_assessment(connection, artifact.assessment_id)
        except (RiskArtifactNotFound, RiskRepositoryConflict):
            raise
        except (TypeError, ValueError) as exc:
            raise RiskRepositoryConflict(
                "immutable Phase 7 assessment failed canonical validation"
            ) from exc
        except DBAPIError as exc:
            raise RiskRepositoryConflict(
                "immutable Phase 7 assessment could not be stored"
            ) from exc

    def get_assessment(self, assessment_id: UUID) -> ApprovalAssessmentArtifact:
        try:
            with self.engine.connect() as connection:
                return self._load_assessment(connection, assessment_id)
        except (RiskArtifactNotFound, RiskRepositoryConflict):
            raise
        except (TypeError, ValueError) as exc:
            raise RiskRepositoryConflict("persisted Phase 7 assessment is invalid") from exc
        except DBAPIError as exc:
            raise RiskRepositoryConflict("Phase 7 assessment could not be loaded") from exc

    def list_assessments(self, *, limit: int = 100) -> list[ApprovalAssessmentSummary]:
        if limit < 1 or limit > 100:
            raise ValueError("limit must be between 1 and 100")
        try:
            with self.engine.connect() as connection:
                rows = connection.execute(
                    text(
                        "SELECT assessment_id, artifact_sha256, research_run_id, outcome, "
                        "reason_codes, created_at_utc, "
                        "artifact_payload#>>'{phase6_lineage,research_configuration_id}' "
                        "AS research_configuration_id, synthetic, simulated_paper_only, "
                        "execution_authorized, execution_ready, "
                        "no_personalized_investment_advice, no_real_performance_claimed "
                        "FROM approval_assessments "
                        "ORDER BY created_at_utc DESC, assessment_id DESC LIMIT :limit"
                    ),
                    {"limit": limit},
                ).mappings()
                return [ApprovalAssessmentSummary.model_validate(dict(row)) for row in rows]
        except (TypeError, ValueError) as exc:
            raise RiskRepositoryConflict("Phase 7 assessment summary is invalid") from exc
        except DBAPIError as exc:
            raise RiskRepositoryConflict("Phase 7 assessments could not be listed") from exc

    @staticmethod
    def _revocation_row(connection: Connection, revocation_id: UUID) -> RowMapping | None:
        return _row_by_identity(
            connection,
            table="approval_revocations",
            id_column="revocation_id",
            identity=revocation_id,
        )

    @staticmethod
    def _revocation_by_fingerprint(connection: Connection, fingerprint: str) -> RowMapping | None:
        return (
            connection.execute(
                text(
                    "SELECT * FROM approval_revocations "
                    "WHERE request_fingerprint_sha256 = :fingerprint"
                ),
                {"fingerprint": fingerprint},
            )
            .mappings()
            .one_or_none()
        )

    @classmethod
    def _load_revocation(
        cls,
        connection: Connection,
        revocation_id: UUID,
        *,
        root_row: RowMapping | None = None,
    ) -> AuthorizationRevocationArtifact:
        row = root_row or cls._revocation_row(connection, revocation_id)
        if row is None:
            raise RiskArtifactNotFound(f"authorization revocation {revocation_id} was not found")
        payload = dict(row["artifact_payload"])
        _require(
            domain_sha256(PHASE7_REVOCATION_ARTIFACT_HASH_DOMAIN, payload)
            == row["artifact_sha256"],
            "persisted Phase 7 revocation payload failed hash revalidation",
        )
        artifact = AuthorizationRevocationArtifact.model_validate(
            {
                **payload,
                "revocation_id": row["revocation_id"],
                "artifact_sha256": row["artifact_sha256"],
                "created_at_utc": row["created_at_utc"],
            }
        )
        _require(
            row["artifact_schema_version"] == artifact.artifact_schema_version
            and row["request_fingerprint_sha256"] == artifact.request_fingerprint_sha256
            and row["human_authorization_evidence_id"] == artifact.human_authorization_evidence_id
            and row["authorization_sha256"] == artifact.authorization_sha256
            and row["revocation_evidence_id"] == artifact.revocation_evidence_id
            and row["revocation_evidence_sha256"] == artifact.revocation_evidence_sha256
            and row["revoked_by"] == artifact.revoked_by
            and row["reason"] == artifact.reason
            and row["effective_at_utc"] == artifact.effective_at_utc
            and row["phase7_code_version_git_sha"] == artifact.phase7_code_version_git_sha
            and row["synthetic"] is True
            and row["simulated_paper_only"] is True
            and row["execution_authorized"] is False
            and row["execution_ready"] is False
            and row["no_personalized_investment_advice"] is True
            and row["no_real_performance_claimed"] is True,
            "persisted Phase 7 revocation columns conflict with payload",
        )
        return artifact

    @staticmethod
    def _insert_revocation(
        connection: Connection, artifact: AuthorizationRevocationArtifact
    ) -> None:
        _insert_row(
            connection,
            "approval_revocations",
            {
                "revocation_id": artifact.revocation_id,
                "artifact_schema_version": artifact.artifact_schema_version,
                "artifact_sha256": artifact.artifact_sha256,
                "request_fingerprint_sha256": artifact.request_fingerprint_sha256,
                "human_authorization_evidence_id": (artifact.human_authorization_evidence_id),
                "authorization_sha256": artifact.authorization_sha256,
                "revocation_evidence_id": artifact.revocation_evidence_id,
                "revocation_evidence_sha256": artifact.revocation_evidence_sha256,
                "revoked_by": artifact.revoked_by,
                "reason": artifact.reason,
                "effective_at_utc": artifact.effective_at_utc,
                "phase7_code_version_git_sha": artifact.phase7_code_version_git_sha,
                "synthetic": artifact.synthetic,
                "simulated_paper_only": artifact.simulated_paper_only,
                "execution_authorized": artifact.execution_authorized,
                "execution_ready": artifact.execution_ready,
                "no_personalized_investment_advice": (artifact.no_personalized_investment_advice),
                "no_real_performance_claimed": artifact.no_real_performance_claimed,
                "artifact_payload": _revocation_payload(artifact),
            },
            json_columns=frozenset({"artifact_payload"}),
        )

    def create_revocation(
        self, artifact: AuthorizationRevocationArtifact
    ) -> AuthorizationRevocationArtifact:
        try:
            with self.engine.begin() as connection:
                _lock(connection, artifact.human_authorization_evidence_id)
                _lock(connection, artifact.request_fingerprint_sha256)
                authorization = _row_by_identity(
                    connection,
                    table="approval_authorizations",
                    id_column="human_authorization_evidence_id",
                    identity=artifact.human_authorization_evidence_id,
                )
                if authorization is None:
                    raise RiskArtifactNotFound(
                        "human authorization evidence "
                        f"{artifact.human_authorization_evidence_id} was not found"
                    )
                _require(
                    authorization["authorization_sha256"] == artifact.authorization_sha256,
                    "revocation authorization hash mismatch",
                )
                existing = self._revocation_by_fingerprint(
                    connection, artifact.request_fingerprint_sha256
                )
                if existing is not None:
                    loaded = self._load_revocation(
                        connection, existing["revocation_id"], root_row=existing
                    )
                    if loaded.artifact_sha256 != artifact.artifact_sha256 or not _same(
                        _revocation_payload(loaded), _revocation_payload(artifact)
                    ):
                        raise RiskRepositoryConflict(
                            "revocation request fingerprint is bound to different evidence"
                        )
                    return loaded
                self._insert_revocation(connection, artifact)
                return self._load_revocation(connection, artifact.revocation_id)
        except (RiskArtifactNotFound, RiskRepositoryConflict):
            raise
        except (TypeError, ValueError) as exc:
            raise RiskRepositoryConflict(
                "immutable Phase 7 revocation failed canonical validation"
            ) from exc
        except DBAPIError as exc:
            raise RiskRepositoryConflict(
                "immutable Phase 7 revocation could not be stored"
            ) from exc

    def list_revocations_for_authorization(
        self, authorization_id: UUID
    ) -> list[AuthorizationRevocationArtifact]:
        try:
            with self.engine.connect() as connection:
                return [
                    self._load_revocation(connection, row["revocation_id"], root_row=row)
                    for row in self._current_revocation_rows(connection, authorization_id)
                ]
        except (RiskArtifactNotFound, RiskRepositoryConflict):
            raise
        except (TypeError, ValueError) as exc:
            raise RiskRepositoryConflict("persisted Phase 7 revocation is invalid") from exc
        except DBAPIError as exc:
            raise RiskRepositoryConflict("Phase 7 revocations could not be loaded") from exc

    def get_revocation(self, revocation_id: UUID) -> AuthorizationRevocationArtifact:
        try:
            with self.engine.connect() as connection:
                return self._load_revocation(connection, revocation_id)
        except (RiskArtifactNotFound, RiskRepositoryConflict):
            raise
        except (TypeError, ValueError) as exc:
            raise RiskRepositoryConflict("persisted Phase 7 revocation is invalid") from exc
        except DBAPIError as exc:
            raise RiskRepositoryConflict("Phase 7 revocation could not be loaded") from exc

    def list_revocations(
        self,
        *,
        human_authorization_evidence_id: UUID | None = None,
        limit: int = 100,
    ) -> list[AuthorizationRevocationSummary]:
        if limit < 1 or limit > 100:
            raise ValueError("limit must be between 1 and 100")
        try:
            with self.engine.connect() as connection:
                where = (
                    "WHERE human_authorization_evidence_id = :authorization_id "
                    if human_authorization_evidence_id is not None
                    else ""
                )
                rows = connection.execute(
                    text(
                        "SELECT revocation_id, artifact_sha256, "
                        "human_authorization_evidence_id, revocation_evidence_id, "
                        "effective_at_utc, created_at_utc, synthetic, "
                        "simulated_paper_only, execution_authorized, execution_ready "
                        "FROM approval_revocations "
                        f"{where}"
                        "ORDER BY created_at_utc DESC, revocation_id DESC LIMIT :limit"
                    ),
                    {
                        "authorization_id": human_authorization_evidence_id,
                        "limit": limit,
                    },
                ).mappings()
                return [AuthorizationRevocationSummary.model_validate(dict(row)) for row in rows]
        except (TypeError, ValueError) as exc:
            raise RiskRepositoryConflict("Phase 7 revocation summary is invalid") from exc
        except DBAPIError as exc:
            raise RiskRepositoryConflict("Phase 7 revocations could not be listed") from exc

    # Explicit aliases keep the persistence object readable as a RiskStore
    # without duplicating any authority or bypassing validation.
    get_approval_policy = get_policy
    get_approval_scope = get_scope
    get_human_authorization_evidence = get_authorization
    find_authorization_revocations = list_revocations_for_authorization


__all__ = [
    "RiskArtifactNotFound",
    "RiskRepository",
    "RiskRepositoryConflict",
]
