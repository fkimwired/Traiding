from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier
from typing import cast
from uuid import UUID, uuid4

import pytest
from fable5_research.contracts import ResearchRunArtifact
from fable5_research.repository import ResearchRepository
from fable5_risk.canonical import (
    PHASE7_ASSESSMENT_ARTIFACT_HASH_DOMAIN,
    PHASE7_ASSESSMENT_NAMESPACE,
    PHASE7_ASSESSMENT_REQUEST_HASH_DOMAIN,
    PHASE7_CURRENTNESS_HASH_DOMAIN,
    PHASE7_REVOCATION_SET_HASH_DOMAIN,
    domain_sha256,
    identity,
)
from fable5_risk.contracts import (
    APPROVAL_CHECK_ORDER,
    ApprovalAssessmentArtifact,
    ApprovalAssessmentCreateRequest,
    ApprovalAssessmentOutcome,
    ApprovalRevocationCreateRequest,
    AuthorizationRevocationArtifact,
    Phase6ApprovalLineage,
    assessment_request_fingerprint,
)
from fable5_risk.fixtures import (
    DEFAULT_REVOCATION_EVIDENCE_PROFILE,
    ApprovalEvidenceBundle,
    build_approval_policy,
    build_approval_risk_input,
    build_approval_scope,
    build_breach_evidence_bundle,
    build_expired_evidence_bundle,
    build_human_authorization,
    build_stale_evidence_bundle,
    build_uncomputable_evidence_bundle,
    phase6_lineage_from_research_artifact,
)
from fable5_risk.repository import (
    RiskRepository,
    RiskRepositoryConflict,
)
from fable5_risk.workflow import (
    ApprovalWorkflow,
    Phase6ResearchStoreAdapter,
    RiskStore,
)
from sqlalchemy import bindparam, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import Connection
from sqlalchemy.exc import DBAPIError

DATABASE_URL = os.environ.get("FABLE5_TEST_DATABASE_URL")
CODE_VERSION_GIT_SHA = os.environ.get("FABLE5_CODE_VERSION_GIT_SHA")

PHASE7_TABLES = (
    "approval_policies",
    "approval_scopes",
    "approval_authorizations",
    "approval_revocations",
    "approval_risk_inputs",
    "approval_assessments",
    "approval_checks",
)
APPEND_ONLY_ERROR = "Phase 7 approval and risk artifacts are append-only"


def test_risk_repository_structurally_implements_the_workflow_store() -> None:
    repository = RiskRepository("sqlite+pysqlite:///:memory:")
    try:
        store: RiskStore = repository
        assert store is repository
        for method in (
            "get_approval_policy",
            "get_approval_scope",
            "get_human_authorization_evidence",
            "get_risk_input",
            "find_authorization_revocations",
            "create_assessment",
            "get_assessment",
            "list_assessments",
            "create_revocation",
            "get_revocation",
            "list_revocations",
        ):
            assert callable(getattr(repository, method))
    finally:
        repository.dispose()


def _repository() -> RiskRepository:
    assert DATABASE_URL is not None
    return RiskRepository(DATABASE_URL)


def _require_postgres() -> None:
    database_url = DATABASE_URL
    code_version_git_sha = CODE_VERSION_GIT_SHA
    if database_url is None or code_version_git_sha is None:
        pytest.skip(
            "set FABLE5_TEST_DATABASE_URL and FABLE5_CODE_VERSION_GIT_SHA after "
            "creating Phase 6 acceptance runs"
        )
        raise AssertionError("pytest.skip unexpectedly returned")
    assert len(code_version_git_sha) == 40
    assert all(character in "0123456789abcdef" for character in code_version_git_sha)


def _research_artifact(configuration_id: str) -> ResearchRunArtifact:
    assert DATABASE_URL is not None
    repository = ResearchRepository(DATABASE_URL)
    try:
        for summary in repository.list_runs(limit=100):
            if summary.configuration_id.value == configuration_id:
                return repository.get_run(summary.run_id)
    finally:
        repository.dispose()
    raise AssertionError(f"Phase 6 artifact {configuration_id} was not persisted")


def _workflow(repository: RiskRepository) -> ApprovalWorkflow:
    assert DATABASE_URL is not None
    assert CODE_VERSION_GIT_SHA is not None
    return ApprovalWorkflow(
        research_store=Phase6ResearchStoreAdapter(ResearchRepository(DATABASE_URL)),
        risk_store=repository,
        phase7_code_version_git_sha=CODE_VERSION_GIT_SHA,
    )


def _request(
    lineage: Phase6ApprovalLineage,
    bundle: ApprovalEvidenceBundle,
    *,
    risk_input_id: UUID | None = None,
) -> ApprovalAssessmentCreateRequest:
    return ApprovalAssessmentCreateRequest(
        research_run_id=lineage.research_run_id,
        approval_policy_version_id=bundle.policy.approval_policy_version_id,
        approval_scope_version_id=bundle.scope.approval_scope_version_id,
        human_authorization_evidence_id=(bundle.authorization.human_authorization_evidence_id),
        risk_input_id=risk_input_id or bundle.risk_input.risk_input_id,
    )


def _unique_bundle(
    lineage: Phase6ApprovalLineage, *, deterministic_tag: int
) -> ApprovalEvidenceBundle:
    now = datetime.now(UTC)
    policy = build_approval_policy(
        policy_id=f"phase7-postgres-policy-{deterministic_tag}",
        valid_from_utc=now - timedelta(days=7),
        expires_at_utc=now + timedelta(days=7),
    )
    scope = build_approval_scope(
        lineage,
        policy,
        scope_id=f"phase7-postgres-scope-{deterministic_tag}:{lineage.research_run_id}",
        valid_from_utc=now - timedelta(days=2),
        expires_at_utc=now + timedelta(days=2),
    )
    authorization = build_human_authorization(
        lineage,
        policy,
        scope,
        authorized_at_utc=(now - timedelta(hours=1) + timedelta(microseconds=deterministic_tag)),
        review_at_utc=now + timedelta(hours=12),
        expires_at_utc=now + timedelta(days=1),
    )
    risk_input = build_approval_risk_input(
        lineage,
        policy,
        scope,
        observed_at_utc=now - timedelta(minutes=5),
    )
    return ApprovalEvidenceBundle(
        policy,
        scope,
        authorization,
        risk_input,
    )


def test_postgres_provisioning_and_positive_roundtrip_preserve_exact_children() -> None:
    _require_postgres()
    research = _research_artifact("phase6-a-pass-v2")
    lineage = phase6_lineage_from_research_artifact(research)
    bundle = _unique_bundle(lineage, deterministic_tag=101)
    repository = _repository()
    try:
        first = repository.provision_evidence(
            bundle.policy,
            bundle.scope,
            bundle.authorization,
            bundle.risk_input,
        )
        repeated = repository.provision_evidence(
            bundle.policy,
            bundle.scope,
            bundle.authorization,
            bundle.risk_input,
        )
        assert (
            first
            == repeated
            == (
                bundle.policy,
                bundle.scope,
                bundle.authorization,
                bundle.risk_input,
            )
        )

        workflow = _workflow(repository)
        artifact = workflow.create_assessment(_request(lineage, bundle))
        assert artifact.outcome is ApprovalAssessmentOutcome.APPROVED_PAPER
        assert artifact.execution_authorized is False
        assert artifact.execution_ready is False
        assert tuple(item.code for item in artifact.checks) == APPROVAL_CHECK_ORDER
        assert repository.get_assessment(artifact.assessment_id) == artifact
        assert artifact.assessment_id in {
            item.assessment_id for item in repository.list_assessments(limit=100)
        }
        timeline = workflow.get_assessment_evidence_timeline(artifact.assessment_id)
        assert timeline.assessment_id == artifact.assessment_id
        assert timeline.assessment_created_at_utc == artifact.created_at_utc
        assert (
            timeline.policy.approval_policy_version_id == bundle.policy.approval_policy_version_id
        )
        assert timeline.policy.policy_sha256 == bundle.policy.policy_sha256
        assert timeline.policy.valid_from_utc == bundle.policy.valid_from_utc
        assert timeline.policy.expires_at_utc == bundle.policy.expires_at_utc
        assert timeline.scope.approval_scope_version_id == bundle.scope.approval_scope_version_id
        assert timeline.scope.scope_sha256 == bundle.scope.scope_sha256
        assert timeline.scope.valid_from_utc == bundle.scope.valid_from_utc
        assert timeline.scope.expires_at_utc == bundle.scope.expires_at_utc
        assert (
            timeline.authorization.human_authorization_evidence_id
            == bundle.authorization.human_authorization_evidence_id
        )
        assert (
            timeline.authorization.authorization_sha256 == bundle.authorization.authorization_sha256
        )
        assert timeline.authorization.authorized_at_utc == bundle.authorization.authorized_at_utc
        assert timeline.authorization.review_at_utc == bundle.authorization.review_at_utc
        assert timeline.authorization.expires_at_utc == bundle.authorization.expires_at_utc
        assert timeline.risk_input.risk_input_id == bundle.risk_input.risk_input_id
        assert timeline.risk_input.risk_input_sha256 == bundle.risk_input.risk_input_sha256
        assert timeline.risk_input.observed_at_utc == bundle.risk_input.observed_at_utc

        with repository.engine.connect() as connection:
            persisted = connection.execute(
                text(
                    "SELECT ordinal, code, payload FROM approval_checks "
                    "WHERE assessment_id = :assessment_id ORDER BY ordinal"
                ),
                {"assessment_id": artifact.assessment_id},
            ).mappings()
            rows = list(persisted)
        assert [row["ordinal"] for row in rows] == list(range(1, 26))
        assert tuple(row["code"] for row in rows) == tuple(
            code.value for code in APPROVAL_CHECK_ORDER
        )
        assert tuple(row["payload"] for row in rows) == tuple(
            item.model_dump(mode="json") for item in artifact.checks
        )
    finally:
        repository.dispose()


def _insert_approved_clone(
    repository: RiskRepository, artifact: ApprovalAssessmentArtifact
) -> None:
    with repository.engine.begin() as connection:
        row = dict(
            connection.execute(
                text("SELECT * FROM approval_assessments WHERE assessment_id = :assessment_id"),
                {"assessment_id": artifact.assessment_id},
            )
            .mappings()
            .one()
        )
        row.pop("created_at_utc")
        row["assessment_id"] = uuid4()
        row["artifact_sha256"] = "a" * 64
        row["request_fingerprint_sha256"] = "b" * 64
        row["outcome"] = "APPROVED_PAPER"
        payload = dict(row["artifact_payload"])
        payload["request_fingerprint_sha256"] = row["request_fingerprint_sha256"]
        payload["outcome"] = "APPROVED_PAPER"
        row["artifact_payload"] = payload
        columns = tuple(row)
        statement = text(
            f"INSERT INTO approval_assessments ({', '.join(columns)}) VALUES "
            f"({', '.join(f':{column}' for column in columns)})"
        ).bindparams(
            bindparam("revocation_ids", type_=postgresql.JSONB()),
            bindparam("reason_codes", type_=postgresql.JSONB()),
            bindparam("artifact_payload", type_=postgresql.JSONB()),
        )
        connection.execute(statement, row)


def _insert_duplicate_with_scalar_forgery(
    repository: RiskRepository,
    *,
    table: str,
    where: dict[str, object],
    forged_column: str,
    forged_value: object,
) -> None:
    predicates = " AND ".join(f"{column} = :where_{column}" for column in where)
    parameters = {f"where_{column}": value for column, value in where.items()}
    with repository.engine.begin() as connection:
        row = dict(
            connection.execute(
                text(f"SELECT * FROM {table} WHERE {predicates}"),
                parameters,
            )
            .mappings()
            .one()
        )
        row.pop("created_at_utc")
        row[forged_column] = forged_value
        columns = tuple(row)
        statement = text(
            f"INSERT INTO {table} ({', '.join(columns)}) VALUES "
            f"({', '.join(f':{column}' for column in columns)})"
        )
        json_columns = {
            "required_check_codes",
            "permitted_universe_ids",
            "revocation_ids",
            "reason_codes",
            "evidence_sha256s",
            "payload",
            "artifact_payload",
        }
        for column in json_columns.intersection(row):
            statement = statement.bindparams(bindparam(column, type_=postgresql.JSONB()))
        connection.execute(statement, row)


def _insert_mapping(
    connection: Connection,
    *,
    table: str,
    row: dict[str, object],
    json_columns: frozenset[str],
) -> None:
    columns = tuple(row)
    statement = text(
        f"INSERT INTO {table} ({', '.join(columns)}) VALUES "
        f"({', '.join(f':{column}' for column in columns)})"
    )
    for column in json_columns.intersection(row):
        statement = statement.bindparams(bindparam(column, type_=postgresql.JSONB()))
    connection.execute(statement, row)


def _currentness_hash(
    artifact: ApprovalAssessmentArtifact,
    *,
    lineage_sha256: str | None = None,
    revocation_set_sha256: str | None = None,
) -> str:
    return domain_sha256(
        PHASE7_CURRENTNESS_HASH_DOMAIN,
        {
            "lineage_sha256": lineage_sha256 or artifact.phase6_lineage.lineage_sha256,
            "policy_sha256": artifact.approval_policy_sha256,
            "scope_sha256": artifact.approval_scope_sha256,
            "authorization_sha256": artifact.authorization_sha256,
            "risk_input_sha256": artifact.risk_input_sha256,
            "revocation_set_sha256": (revocation_set_sha256 or artifact.revocation_set_sha256),
            "states": tuple(
                {"code": check.code, "status": check.status} for check in artifact.checks[:10]
            ),
        },
    )


def _rehashed_assessment_clone(
    artifact: ApprovalAssessmentArtifact,
    *,
    currentness_state_sha256: str,
    revocation_set_sha256: str | None = None,
) -> ApprovalAssessmentArtifact:
    effective_revocation_hash = revocation_set_sha256 or artifact.revocation_set_sha256
    payload = artifact.model_dump(
        mode="python",
        exclude={"assessment_id", "artifact_sha256", "created_at_utc"},
    )
    payload["currentness_state_sha256"] = currentness_state_sha256
    payload["revocation_set_sha256"] = effective_revocation_hash
    request = ApprovalAssessmentCreateRequest(
        research_run_id=artifact.research_run_id,
        approval_policy_version_id=artifact.approval_policy_version_id,
        approval_scope_version_id=artifact.approval_scope_version_id,
        human_authorization_evidence_id=artifact.human_authorization_evidence_id,
        risk_input_id=artifact.risk_input_id,
    )
    fingerprint = assessment_request_fingerprint(
        request=request,
        lineage_sha256=artifact.phase6_lineage.lineage_sha256,
        policy_sha256=artifact.approval_policy_sha256,
        scope_sha256=artifact.approval_scope_sha256,
        authorization_sha256=artifact.authorization_sha256,
        risk_input_sha256=artifact.risk_input_sha256,
        revocation_set_sha256=effective_revocation_hash,
        currentness_state_sha256=currentness_state_sha256,
        phase7_code_version_git_sha=artifact.phase7_code_version_git_sha,
    )
    payload["request_fingerprint_sha256"] = fingerprint
    return ApprovalAssessmentArtifact.model_validate(
        {
            "assessment_id": identity(PHASE7_ASSESSMENT_NAMESPACE, fingerprint),
            "artifact_sha256": domain_sha256(PHASE7_ASSESSMENT_ARTIFACT_HASH_DOMAIN, payload),
            "created_at_utc": artifact.created_at_utc,
            **payload,
        }
    )


def _insert_fully_rehashed_lineage_forgery(
    repository: RiskRepository, artifact: ApprovalAssessmentArtifact
) -> None:
    with repository.engine.begin() as connection:
        row = dict(
            connection.execute(
                text("SELECT * FROM approval_assessments WHERE assessment_id = :assessment_id"),
                {"assessment_id": artifact.assessment_id},
            )
            .mappings()
            .one()
        )
        check_rows = [
            dict(item)
            for item in connection.execute(
                text(
                    "SELECT * FROM approval_checks "
                    "WHERE assessment_id = :assessment_id ORDER BY ordinal"
                ),
                {"assessment_id": artifact.assessment_id},
            ).mappings()
        ]
        row.pop("created_at_utc")
        forged_lineage_sha256 = "e" * 64
        payload = dict(row["artifact_payload"])
        lineage_payload = dict(payload["phase6_lineage"])
        lineage_payload["lineage_sha256"] = forged_lineage_sha256
        payload["phase6_lineage"] = lineage_payload
        forged_currentness_sha256 = _currentness_hash(
            artifact, lineage_sha256=forged_lineage_sha256
        )
        request = ApprovalAssessmentCreateRequest(
            research_run_id=artifact.research_run_id,
            approval_policy_version_id=artifact.approval_policy_version_id,
            approval_scope_version_id=artifact.approval_scope_version_id,
            human_authorization_evidence_id=artifact.human_authorization_evidence_id,
            risk_input_id=artifact.risk_input_id,
        )
        fingerprint = assessment_request_fingerprint(
            request=request,
            lineage_sha256=forged_lineage_sha256,
            policy_sha256=artifact.approval_policy_sha256,
            scope_sha256=artifact.approval_scope_sha256,
            authorization_sha256=artifact.authorization_sha256,
            risk_input_sha256=artifact.risk_input_sha256,
            revocation_set_sha256=artifact.revocation_set_sha256,
            currentness_state_sha256=forged_currentness_sha256,
            phase7_code_version_git_sha=artifact.phase7_code_version_git_sha,
        )
        assessment_id = identity(PHASE7_ASSESSMENT_NAMESPACE, fingerprint)
        payload["currentness_state_sha256"] = forged_currentness_sha256
        payload["request_fingerprint_sha256"] = fingerprint
        artifact_sha256 = domain_sha256(PHASE7_ASSESSMENT_ARTIFACT_HASH_DOMAIN, payload)
        row.update(
            {
                "assessment_id": assessment_id,
                "artifact_sha256": artifact_sha256,
                "request_fingerprint_sha256": fingerprint,
                "currentness_state_sha256": forged_currentness_sha256,
                "phase6_lineage_sha256": forged_lineage_sha256,
                "artifact_payload": payload,
            }
        )
        _insert_mapping(
            connection,
            table="approval_assessments",
            row=row,
            json_columns=frozenset({"revocation_ids", "reason_codes", "artifact_payload"}),
        )
        for check_row in check_rows:
            check_row.pop("created_at_utc")
            check_row["assessment_id"] = assessment_id
            check_row["assessment_artifact_sha256"] = artifact_sha256
            _insert_mapping(
                connection,
                table="approval_checks",
                row=check_row,
                json_columns=frozenset({"evidence_sha256s", "payload"}),
            )


def _insert_fully_rehashed_request_forgery(
    repository: RiskRepository, artifact: ApprovalAssessmentArtifact
) -> None:
    with repository.engine.begin() as connection:
        row = dict(
            connection.execute(
                text("SELECT * FROM approval_assessments WHERE assessment_id = :assessment_id"),
                {"assessment_id": artifact.assessment_id},
            )
            .mappings()
            .one()
        )
        check_rows = [
            dict(item)
            for item in connection.execute(
                text(
                    "SELECT * FROM approval_checks "
                    "WHERE assessment_id = :assessment_id ORDER BY ordinal"
                ),
                {"assessment_id": artifact.assessment_id},
            ).mappings()
        ]
        row.pop("created_at_utc")
        forged_fingerprint = domain_sha256(
            PHASE7_ASSESSMENT_REQUEST_HASH_DOMAIN,
            {"forged_request_preimage": True},
        )
        assessment_id = identity(PHASE7_ASSESSMENT_NAMESPACE, forged_fingerprint)
        payload = dict(row["artifact_payload"])
        payload["request_fingerprint_sha256"] = forged_fingerprint
        artifact_sha256 = domain_sha256(PHASE7_ASSESSMENT_ARTIFACT_HASH_DOMAIN, payload)
        row.update(
            {
                "assessment_id": assessment_id,
                "artifact_sha256": artifact_sha256,
                "request_fingerprint_sha256": forged_fingerprint,
                "artifact_payload": payload,
            }
        )
        _insert_mapping(
            connection,
            table="approval_assessments",
            row=row,
            json_columns=frozenset({"revocation_ids", "reason_codes", "artifact_payload"}),
        )
        for check_row in check_rows:
            check_row.pop("created_at_utc")
            check_row["assessment_id"] = assessment_id
            check_row["assessment_artifact_sha256"] = artifact_sha256
            _insert_mapping(
                connection,
                table="approval_checks",
                row=check_row,
                json_columns=frozenset({"evidence_sha256s", "payload"}),
            )


def test_postgres_hash_valid_payload_cannot_diverge_from_any_scalar_column() -> None:
    _require_postgres()
    lineage = phase6_lineage_from_research_artifact(_research_artifact("phase6-a-pass-v2"))
    bundle = _unique_bundle(lineage, deterministic_tag=151)
    repository = _repository()
    try:
        repository.provision_evidence(
            bundle.policy,
            bundle.scope,
            bundle.authorization,
            bundle.risk_input,
        )
        workflow = _workflow(repository)
        assessment = workflow.create_assessment(_request(lineage, bundle))
        cases: tuple[tuple[str, dict[str, object], str, object, str], ...] = (
            (
                "approval_policies",
                {"approval_policy_version_id": bundle.policy.approval_policy_version_id},
                "max_notional",
                bundle.policy.max_notional + 1,
                "Phase 7 policy payload mismatch",
            ),
            (
                "approval_scopes",
                {"approval_scope_version_id": bundle.scope.approval_scope_version_id},
                "max_notional",
                bundle.scope.max_notional + 1,
                "Phase 7 scope payload mismatch",
            ),
            (
                "approval_authorizations",
                {
                    "human_authorization_evidence_id": (
                        bundle.authorization.human_authorization_evidence_id
                    )
                },
                "authorized_by",
                f"{bundle.authorization.authorized_by}-forged",
                "Phase 7 authorization payload mismatch",
            ),
            (
                "approval_risk_inputs",
                {"risk_input_id": bundle.risk_input.risk_input_id},
                "global_control_clear",
                False,
                "Phase 7 risk-input payload mismatch",
            ),
            (
                "approval_assessments",
                {"assessment_id": assessment.assessment_id},
                "execution_ready",
                True,
                "Phase 7 assessment payload mismatch",
            ),
            (
                "approval_checks",
                {"assessment_id": assessment.assessment_id, "ordinal": 1},
                "status",
                "FAIL",
                "Phase 7 check payload mismatch",
            ),
        )
        for table, where, column, value, expected in cases:
            with pytest.raises(DBAPIError) as error:
                _insert_duplicate_with_scalar_forgery(
                    repository,
                    table=table,
                    where=where,
                    forged_column=column,
                    forged_value=value,
                )
            assert expected in str(error.value)

        revocation = workflow.create_revocation(
            ApprovalRevocationCreateRequest(
                human_authorization_evidence_id=(
                    bundle.authorization.human_authorization_evidence_id
                ),
                revocation_evidence_id=(DEFAULT_REVOCATION_EVIDENCE_PROFILE.revocation_evidence_id),
            )
        )
        with pytest.raises(DBAPIError) as error:
            _insert_duplicate_with_scalar_forgery(
                repository,
                table="approval_revocations",
                where={"revocation_id": revocation.revocation_id},
                forged_column="reason",
                forged_value=f"{revocation.reason} forged",
            )
        assert "Phase 7 revocation payload mismatch" in str(error.value)
    finally:
        repository.dispose()


def test_postgres_nonpass_research_persists_rejection_but_cannot_be_positive() -> None:
    _require_postgres()
    research = _research_artifact("phase6-a-fail-cost-v2")
    lineage = phase6_lineage_from_research_artifact(research)
    bundle = _unique_bundle(lineage, deterministic_tag=201)
    repository = _repository()
    try:
        repository.provision_evidence(
            bundle.policy,
            bundle.scope,
            bundle.authorization,
            bundle.risk_input,
        )
        artifact = _workflow(repository).create_assessment(_request(lineage, bundle))
        assert artifact.outcome is ApprovalAssessmentOutcome.FAIL_REJECT
        assert "phase6_research_not_eligible" in artifact.reason_codes
        with pytest.raises(DBAPIError) as error:
            _insert_approved_clone(repository, artifact)
        assert "positive approval requires exact eligible" in str(error.value)
    finally:
        repository.dispose()


def test_postgres_cross_run_conflict_persists_rejection_but_cannot_be_positive() -> None:
    _require_postgres()
    pass_lineage = phase6_lineage_from_research_artifact(_research_artifact("phase6-a-pass-v2"))
    fail_lineage = phase6_lineage_from_research_artifact(
        _research_artifact("phase6-a-fail-cost-v2")
    )
    pass_bundle = _unique_bundle(pass_lineage, deterministic_tag=301)
    fail_bundle = _unique_bundle(fail_lineage, deterministic_tag=302)
    repository = _repository()
    try:
        repository.provision_evidence(
            pass_bundle.policy,
            pass_bundle.scope,
            pass_bundle.authorization,
            pass_bundle.risk_input,
        )
        repository.provision_evidence(
            fail_bundle.policy,
            fail_bundle.scope,
            fail_bundle.authorization,
            fail_bundle.risk_input,
        )
        artifact = _workflow(repository).create_assessment(
            _request(
                pass_lineage,
                pass_bundle,
                risk_input_id=fail_bundle.risk_input.risk_input_id,
            )
        )
        assert artifact.outcome is ApprovalAssessmentOutcome.FAIL_REJECT
        assert "approval_scope_mismatch" in artifact.reason_codes
        with pytest.raises(DBAPIError) as error:
            _insert_approved_clone(repository, artifact)
        assert "assessment evidence lineage mismatch" in str(error.value)
    finally:
        repository.dispose()


def test_postgres_positive_semantics_are_rederived_from_independent_evidence() -> None:
    _require_postgres()
    lineage = phase6_lineage_from_research_artifact(_research_artifact("phase6-a-pass-v2"))
    repository = _repository()
    try:
        assessment_time = datetime.now(UTC)
        scenario_scope_id = f"phase7-postgres-scope-351:{lineage.research_run_id}"
        bundles = (
            build_expired_evidence_bundle(
                lineage,
                assessment_time_utc=assessment_time,
                policy_id="phase7-postgres-policy-351",
                scope_id=scenario_scope_id,
            ),
            build_stale_evidence_bundle(
                lineage,
                assessment_time_utc=assessment_time,
                policy_id="phase7-postgres-policy-351",
                scope_id=scenario_scope_id,
            ),
            build_uncomputable_evidence_bundle(
                lineage,
                assessment_time_utc=assessment_time,
                policy_id="phase7-postgres-policy-351",
                scope_id=scenario_scope_id,
            ),
            build_breach_evidence_bundle(
                lineage,
                assessment_time_utc=assessment_time,
                policy_id="phase7-postgres-policy-351",
                scope_id=scenario_scope_id,
            ),
        )
        for bundle in bundles:
            repository.provision_evidence(
                bundle.policy,
                bundle.scope,
                bundle.authorization,
                bundle.risk_input,
            )
            artifact = _workflow(repository).create_assessment(_request(lineage, bundle))
            assert artifact.outcome is ApprovalAssessmentOutcome.FAIL_REJECT
            with pytest.raises(DBAPIError) as error:
                _insert_approved_clone(repository, artifact)
            assert "positive approval evidence is stale" in str(error.value)
    finally:
        repository.dispose()


class _CandidateStore:
    def __init__(self, repository: RiskRepository, *, hide_revocations: bool = False) -> None:
        self.repository = repository
        self.hide_revocations = hide_revocations

    def __getattr__(self, name: str) -> object:
        return getattr(self.repository, name)

    def create_assessment(self, artifact: ApprovalAssessmentArtifact) -> ApprovalAssessmentArtifact:
        return artifact

    def create_revocation(
        self, artifact: AuthorizationRevocationArtifact
    ) -> AuthorizationRevocationArtifact:
        return artifact

    def find_authorization_revocations(
        self, human_authorization_evidence_id: UUID
    ) -> list[AuthorizationRevocationArtifact]:
        if self.hide_revocations:
            return []
        return self.repository.find_authorization_revocations(human_authorization_evidence_id)


def test_postgres_uses_wall_clock_when_transaction_crosses_authorization_expiry() -> None:
    _require_postgres()
    lineage = phase6_lineage_from_research_artifact(_research_artifact("phase6-a-pass-v2"))
    assessment_time = datetime.now(UTC)
    authorization_expiry = assessment_time + timedelta(seconds=2)
    policy = build_approval_policy(
        policy_id="phase7-postgres-policy-376",
        valid_from_utc=assessment_time - timedelta(days=1),
        expires_at_utc=assessment_time + timedelta(days=1),
    )
    scope = build_approval_scope(
        lineage,
        policy,
        scope_id=f"phase7-postgres-scope-376:{lineage.research_run_id}",
        valid_from_utc=assessment_time - timedelta(days=1),
        expires_at_utc=assessment_time + timedelta(days=1),
    )
    authorization = build_human_authorization(
        lineage,
        policy,
        scope,
        authorized_at_utc=assessment_time - timedelta(hours=1),
        review_at_utc=authorization_expiry,
        expires_at_utc=authorization_expiry,
    )
    risk_input = build_approval_risk_input(
        lineage,
        policy,
        scope,
        observed_at_utc=assessment_time - timedelta(minutes=1),
    )
    bundle = ApprovalEvidenceBundle(policy, scope, authorization, risk_input)
    repository = _repository()
    assert DATABASE_URL is not None
    try:
        repository.provision_evidence(policy, scope, authorization, risk_input)
        builder = ApprovalWorkflow(
            research_store=Phase6ResearchStoreAdapter(ResearchRepository(DATABASE_URL)),
            risk_store=cast(RiskStore, _CandidateStore(repository)),
            assessment_time_utc=assessment_time,
            phase7_code_version_git_sha=cast(str, CODE_VERSION_GIT_SHA),
        )
        candidate = builder.create_assessment(_request(lineage, bundle))
        assert candidate.outcome is ApprovalAssessmentOutcome.APPROVED_PAPER

        with repository.engine.connect() as connection:
            transaction = connection.begin()
            try:
                transaction_time = connection.scalar(text("SELECT CURRENT_TIMESTAMP"))
                assert isinstance(transaction_time, datetime)
                assert transaction_time < authorization_expiry
                connection.execute(
                    text(
                        "SELECT pg_sleep(GREATEST(0.0, EXTRACT(EPOCH FROM "
                        "(CAST(:expiry AS timestamptz) - clock_timestamp()))) + 0.10)"
                    ),
                    {"expiry": authorization_expiry},
                )
                wall_clock = connection.scalar(text("SELECT clock_timestamp()"))
                assert isinstance(wall_clock, datetime)
                assert wall_clock >= authorization_expiry
                with pytest.raises(DBAPIError) as error:
                    RiskRepository._insert_assessment(connection, candidate)
                assert "positive approval evidence is stale" in str(error.value)
            finally:
                transaction.rollback()
    finally:
        repository.dispose()


def test_postgres_recomputes_all_assessment_audit_hash_preimages() -> None:
    _require_postgres()
    lineage = phase6_lineage_from_research_artifact(_research_artifact("phase6-a-pass-v2"))
    bundle = _unique_bundle(lineage, deterministic_tag=381)
    repository = _repository()
    try:
        repository.provision_evidence(
            bundle.policy,
            bundle.scope,
            bundle.authorization,
            bundle.risk_input,
        )
        original = _workflow(repository).create_assessment(_request(lineage, bundle))
        assert original.outcome is ApprovalAssessmentOutcome.APPROVED_PAPER

        forged_currentness = _rehashed_assessment_clone(
            original,
            currentness_state_sha256="c" * 64,
        )
        forged_revocation_set = domain_sha256(
            PHASE7_REVOCATION_SET_HASH_DOMAIN,
            (
                {
                    "revocation_id": UUID("00000000-0000-0000-0000-000000000001"),
                    "artifact_sha256": "d" * 64,
                    "effective_at_utc": datetime(2026, 7, 14, tzinfo=UTC),
                },
            ),
        )
        forged_revocations = _rehashed_assessment_clone(
            original,
            revocation_set_sha256=forged_revocation_set,
            currentness_state_sha256=_currentness_hash(
                original, revocation_set_sha256=forged_revocation_set
            ),
        )
        for candidate, expected_error in (
            (forged_currentness, "currentness-state hash mismatch"),
            (forged_revocations, "revocation-set hash mismatch"),
        ):
            assert candidate.assessment_id != original.assessment_id
            assert candidate.artifact_sha256 != original.artifact_sha256
            with pytest.raises(RiskRepositoryConflict) as error:
                repository.create_assessment(candidate)
            assert error.value.__cause__ is not None
            assert expected_error in str(error.value.__cause__)

        with pytest.raises(DBAPIError) as lineage_error:
            _insert_fully_rehashed_lineage_forgery(repository, original)
        assert "complete Phase 6 lineage mismatch" in str(lineage_error.value)

        with pytest.raises(DBAPIError) as request_error:
            _insert_fully_rehashed_request_forgery(repository, original)
        assert "assessment request fingerprint mismatch" in str(request_error.value)

        with repository.engine.connect() as connection:
            matching_positive_rows = connection.scalar(
                text(
                    "SELECT count(*) FROM approval_assessments "
                    "WHERE research_run_id = :research_run_id "
                    "AND approval_policy_version_id = :policy_id "
                    "AND approval_scope_version_id = :scope_id "
                    "AND human_authorization_evidence_id = :authorization_id "
                    "AND risk_input_id = :risk_input_id "
                    "AND outcome = 'APPROVED_PAPER'"
                ),
                {
                    "research_run_id": original.research_run_id,
                    "policy_id": original.approval_policy_version_id,
                    "scope_id": original.approval_scope_version_id,
                    "authorization_id": original.human_authorization_evidence_id,
                    "risk_input_id": original.risk_input_id,
                },
            )
        assert matching_positive_rows == 1
        assert repository.get_assessment(original.assessment_id) == original
    finally:
        repository.dispose()


def test_postgres_two_writer_assessment_is_idempotent() -> None:
    _require_postgres()
    lineage = phase6_lineage_from_research_artifact(_research_artifact("phase6-a-pass-v2"))
    bundle = _unique_bundle(lineage, deterministic_tag=401)
    repository = _repository()
    assert DATABASE_URL is not None
    research_store = Phase6ResearchStoreAdapter(ResearchRepository(DATABASE_URL))
    try:
        repository.provision_evidence(
            bundle.policy,
            bundle.scope,
            bundle.authorization,
            bundle.risk_input,
        )
        builder = ApprovalWorkflow(
            research_store=research_store,
            risk_store=cast(RiskStore, _CandidateStore(repository)),
            phase7_code_version_git_sha=cast(str, CODE_VERSION_GIT_SHA),
        )
        candidate = builder.create_assessment(_request(lineage, bundle))
        barrier = Barrier(2)

        def create() -> ApprovalAssessmentArtifact:
            barrier.wait(timeout=30)
            return repository.create_assessment(candidate)

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = tuple(executor.map(lambda _: create(), range(2)))
        assert results[0] == results[1]
        assert results[0].assessment_id == candidate.assessment_id
    finally:
        repository.dispose()


def test_postgres_two_writer_identical_revocation_is_idempotent() -> None:
    _require_postgres()
    lineage = phase6_lineage_from_research_artifact(_research_artifact("phase6-a-pass-v2"))
    bundle = _unique_bundle(lineage, deterministic_tag=451)
    repository = _repository()
    assert DATABASE_URL is not None
    try:
        repository.provision_evidence(
            bundle.policy,
            bundle.scope,
            bundle.authorization,
            bundle.risk_input,
        )
        builder = ApprovalWorkflow(
            research_store=Phase6ResearchStoreAdapter(ResearchRepository(DATABASE_URL)),
            risk_store=cast(RiskStore, _CandidateStore(repository)),
            phase7_code_version_git_sha=cast(str, CODE_VERSION_GIT_SHA),
        )
        candidate = builder.create_revocation(
            ApprovalRevocationCreateRequest(
                human_authorization_evidence_id=(
                    bundle.authorization.human_authorization_evidence_id
                ),
                revocation_evidence_id=(DEFAULT_REVOCATION_EVIDENCE_PROFILE.revocation_evidence_id),
            )
        )
        barrier = Barrier(2)

        def create() -> AuthorizationRevocationArtifact:
            barrier.wait(timeout=30)
            return repository.create_revocation(candidate)

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = tuple(executor.map(lambda _: create(), range(2)))

        assert results[0] == results[1]
        assert results[0].revocation_id == candidate.revocation_id
        assert results[0].artifact_sha256 == candidate.artifact_sha256
        assert results[0].model_dump(exclude={"created_at_utc"}) == candidate.model_dump(
            exclude={"created_at_utc"}
        )
        matching = [
            item
            for item in repository.find_authorization_revocations(
                bundle.authorization.human_authorization_evidence_id
            )
            if item.revocation_id == candidate.revocation_id
        ]
        assert matching == [results[0]]
    finally:
        repository.dispose()


def test_postgres_revocation_is_terminal_for_positive_reuse() -> None:
    _require_postgres()
    lineage = phase6_lineage_from_research_artifact(_research_artifact("phase6-a-pass-v2"))
    bundle = _unique_bundle(lineage, deterministic_tag=501)
    repository = _repository()
    try:
        repository.provision_evidence(
            bundle.policy,
            bundle.scope,
            bundle.authorization,
            bundle.risk_input,
        )
        workflow = _workflow(repository)
        request = _request(lineage, bundle)
        existing_revocations = repository.find_authorization_revocations(
            bundle.authorization.human_authorization_evidence_id
        )
        if existing_revocations:
            assert DATABASE_URL is not None
            builder = ApprovalWorkflow(
                research_store=Phase6ResearchStoreAdapter(ResearchRepository(DATABASE_URL)),
                risk_store=cast(
                    RiskStore,
                    _CandidateStore(repository, hide_revocations=True),
                ),
                phase7_code_version_git_sha=cast(str, CODE_VERSION_GIT_SHA),
            )
            positive_candidate = builder.create_assessment(request)
            positive = repository.get_assessment(positive_candidate.assessment_id)
        else:
            positive = workflow.create_assessment(request)
        revocation = workflow.create_revocation(
            ApprovalRevocationCreateRequest(
                human_authorization_evidence_id=(
                    bundle.authorization.human_authorization_evidence_id
                ),
                revocation_evidence_id=(DEFAULT_REVOCATION_EVIDENCE_PROFILE.revocation_evidence_id),
            )
        )
        rejected = workflow.create_assessment(request)
        assert rejected.outcome is ApprovalAssessmentOutcome.FAIL_REJECT
        assert rejected.revocation_ids == (revocation.revocation_id,)
        with pytest.raises(RiskRepositoryConflict, match="revocation set changed"):
            repository.create_assessment(positive)
        assert repository.get_assessment(positive.assessment_id) == positive
        assert repository.get_revocation(revocation.revocation_id) == revocation
    finally:
        repository.dispose()


def test_postgres_assessment_and_revocation_serialize_on_authorization() -> None:
    _require_postgres()
    lineage = phase6_lineage_from_research_artifact(_research_artifact("phase6-a-pass-v2"))
    bundle = _unique_bundle(lineage, deterministic_tag=701)
    repository = _repository()
    assert DATABASE_URL is not None
    try:
        repository.provision_evidence(
            bundle.policy,
            bundle.scope,
            bundle.authorization,
            bundle.risk_input,
        )
        candidate_store = cast(
            RiskStore,
            _CandidateStore(repository, hide_revocations=True),
        )
        builder = ApprovalWorkflow(
            research_store=Phase6ResearchStoreAdapter(ResearchRepository(DATABASE_URL)),
            risk_store=candidate_store,
            phase7_code_version_git_sha=cast(str, CODE_VERSION_GIT_SHA),
        )
        request = _request(lineage, bundle)
        assessment_candidate = builder.create_assessment(request)
        revocation_candidate = builder.create_revocation(
            ApprovalRevocationCreateRequest(
                human_authorization_evidence_id=(
                    bundle.authorization.human_authorization_evidence_id
                ),
                revocation_evidence_id=(DEFAULT_REVOCATION_EVIDENCE_PROFILE.revocation_evidence_id),
            )
        )
        barrier = Barrier(2)

        def persist_assessment() -> ApprovalAssessmentArtifact | RiskRepositoryConflict:
            barrier.wait(timeout=30)
            try:
                return repository.create_assessment(assessment_candidate)
            except RiskRepositoryConflict as exc:
                return exc

        def persist_revocation() -> AuthorizationRevocationArtifact:
            barrier.wait(timeout=30)
            return repository.create_revocation(revocation_candidate)

        with ThreadPoolExecutor(max_workers=2) as executor:
            assessment_future = executor.submit(persist_assessment)
            revocation_future = executor.submit(persist_revocation)
            assessment_result = assessment_future.result(timeout=60)
            revocation_result = revocation_future.result(timeout=60)

        assert revocation_result == repository.get_revocation(revocation_candidate.revocation_id)
        assert isinstance(
            assessment_result,
            (ApprovalAssessmentArtifact, RiskRepositoryConflict),
        )
        if isinstance(assessment_result, ApprovalAssessmentArtifact):
            assert repository.get_assessment(assessment_result.assessment_id) == assessment_result
        with pytest.raises(RiskRepositoryConflict, match="revocation set changed"):
            repository.create_assessment(assessment_candidate)
    finally:
        repository.dispose()


def test_postgres_all_seven_tables_reject_every_mutation_form() -> None:
    _require_postgres()
    lineage = phase6_lineage_from_research_artifact(_research_artifact("phase6-a-pass-v2"))
    bundle = _unique_bundle(lineage, deterministic_tag=601)
    repository = _repository()
    try:
        repository.provision_evidence(
            bundle.policy,
            bundle.scope,
            bundle.authorization,
            bundle.risk_input,
        )
        _workflow(repository).create_assessment(_request(lineage, bundle))
        for table in PHASE7_TABLES:
            statements = (
                f"UPDATE {table} SET created_at_utc = created_at_utc "
                f"WHERE ctid = (SELECT ctid FROM {table} LIMIT 1)",
                f"DELETE FROM {table} WHERE ctid = (SELECT ctid FROM {table} LIMIT 1)",
                f"TRUNCATE TABLE {table} CASCADE",
            )
            for statement in statements:
                with repository.engine.connect() as connection:
                    transaction = connection.begin()
                    try:
                        with pytest.raises(DBAPIError) as error:
                            connection.execute(text(statement))
                        assert APPEND_ONLY_ERROR in str(error.value)
                    finally:
                        transaction.rollback()
    finally:
        repository.dispose()
