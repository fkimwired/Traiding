from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from threading import Barrier
from typing import Any, cast
from uuid import UUID, uuid4

import fable5_paper.repository as repository_module
import pytest
from fable5_paper.canonical import (
    PHASE10_ARTIFACT_HASH_DOMAIN,
    PHASE10_CHECK_HASH_DOMAIN,
    PHASE10_CONFIGURATION_HASH_DOMAIN,
    PHASE10_CONFIGURATION_NAMESPACE,
    PHASE10_LEDGER_HASH_DOMAIN,
    PHASE10_LEDGER_NAMESPACE,
    PHASE10_RUN_NAMESPACE,
    domain_sha256,
    identity,
)
from fable5_paper.contracts import (
    PAPER_CHECK_ORDER,
    PaperCheckStatus,
    PaperSimulationArtifact,
    PaperSimulationCheck,
    PaperSimulationCreateRequest,
    PaperSimulationLedgerEntry,
    PaperSimulationOutcome,
    PaperSimulationSummary,
    build_transition_revalidation_proof,
    paper_currentness_sha256,
    paper_request_fingerprint,
)
from fable5_paper.fixtures import build_simulation_ledger
from fable5_paper.repository import PaperRepository, PaperRepositoryConflict
from fable5_paper.workflow import (
    PaperSimulationStore,
    PaperSimulationWorkflow,
    PostgresPaperEvidenceGateway,
)
from fable5_research.contracts import ResearchRunArtifact
from fable5_research.repository import ResearchRepository
from fable5_risk.canonical import PHASE7_SCOPE_HASH_DOMAIN, PHASE7_SCOPE_NAMESPACE
from fable5_risk.contracts import (
    ApprovalAssessmentArtifact,
    ApprovalAssessmentCreateRequest,
    ApprovalAssessmentOutcome,
    ApprovalScope,
)
from fable5_risk.fixtures import (
    build_approval_policy,
    build_approval_risk_input,
    build_approval_scope,
    build_human_authorization,
    phase6_lineage_from_research_artifact,
)
from fable5_risk.repository import RiskRepository
from fable5_risk.workflow import ApprovalWorkflow, Phase6ResearchStoreAdapter
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import DBAPIError

DATABASE_URL = os.environ.get("FABLE5_TEST_DATABASE_URL")
CODE_VERSION_GIT_SHA = os.environ.get("FABLE5_CODE_VERSION_GIT_SHA")
APPEND_ONLY_ERROR = "Phase 10 local paper simulation artifacts are append-only"


class _CandidateStore:
    """Return the workflow candidate without persisting it."""

    def find_by_idempotency_key(self, key: str) -> PaperSimulationArtifact | None:
        del key
        return None

    def create_simulation(self, artifact: PaperSimulationArtifact) -> PaperSimulationArtifact:
        return artifact

    def get_simulation(self, simulation_run_id: UUID) -> PaperSimulationArtifact:
        raise AssertionError(f"unexpected read for {simulation_run_id}")

    def list_simulations(
        self,
        *,
        source_assessment_id: UUID | None,
        limit: int,
    ) -> list[PaperSimulationSummary]:
        raise AssertionError(f"unexpected list for {source_assessment_id=} {limit=}")


def test_paper_repository_structurally_implements_the_workflow_store() -> None:
    repository = PaperRepository("sqlite+pysqlite:///:memory:")
    try:
        store: PaperSimulationStore = repository
        assert store is repository
        for method in (
            "find_by_idempotency_key",
            "create_simulation",
            "get_simulation",
            "list_simulations",
        ):
            assert callable(getattr(repository, method))
        with pytest.raises(ValueError, match="between 1 and 100"):
            repository.list_simulations(source_assessment_id=None, limit=0)
    finally:
        repository.dispose()


def _require_postgres() -> None:
    if DATABASE_URL is None or CODE_VERSION_GIT_SHA is None:
        pytest.skip(
            "set FABLE5_TEST_DATABASE_URL and FABLE5_CODE_VERSION_GIT_SHA after "
            "creating Phase 6 acceptance runs"
        )
        raise AssertionError("pytest.skip unexpectedly returned")
    assert len(CODE_VERSION_GIT_SHA) == 40
    assert all(character in "0123456789abcdef" for character in CODE_VERSION_GIT_SHA)


def _research_artifact(repository: ResearchRepository) -> ResearchRunArtifact:
    for summary in repository.list_runs(limit=100):
        if summary.configuration_id.value == "phase6-a-pass-v2":
            return repository.get_run(summary.run_id)
    raise AssertionError("the accepted phase6-a-pass-v2 artifact is required")


def _approved_source(
    research_repository: ResearchRepository,
    risk_repository: RiskRepository,
    *,
    tag: str,
) -> ApprovalAssessmentArtifact:
    now = datetime.now(UTC)
    lineage = phase6_lineage_from_research_artifact(_research_artifact(research_repository))
    identity_tag = f"phase10-postgres-{tag}-{uuid4().hex}"
    policy = build_approval_policy(
        policy_id=f"{identity_tag}-policy",
        valid_from_utc=now - timedelta(days=1),
        expires_at_utc=now + timedelta(days=1),
    )
    scope = build_approval_scope(
        lineage,
        policy,
        scope_id=f"{identity_tag}-scope",
        valid_from_utc=now - timedelta(days=1),
        expires_at_utc=now + timedelta(days=1),
    )
    authorization = build_human_authorization(
        lineage,
        policy,
        scope,
        authorized_at_utc=now - timedelta(minutes=5),
        review_at_utc=now + timedelta(hours=12),
        expires_at_utc=now + timedelta(days=1),
    )
    risk_input = build_approval_risk_input(
        lineage,
        policy,
        scope,
        observed_at_utc=now - timedelta(minutes=1),
    )
    risk_repository.provision_evidence(policy, scope, authorization, risk_input)
    workflow = ApprovalWorkflow(
        research_store=Phase6ResearchStoreAdapter(research_repository),
        risk_store=risk_repository,
        assessment_time_utc=now,
        phase7_code_version_git_sha=cast(str, CODE_VERSION_GIT_SHA),
    )
    source = workflow.create_assessment(
        ApprovalAssessmentCreateRequest(
            research_run_id=lineage.research_run_id,
            approval_policy_version_id=policy.approval_policy_version_id,
            approval_scope_version_id=scope.approval_scope_version_id,
            human_authorization_evidence_id=authorization.human_authorization_evidence_id,
            risk_input_id=risk_input.risk_input_id,
        )
    )
    assert source.outcome is ApprovalAssessmentOutcome.APPROVED_PAPER
    return source


def _workflow(
    research_repository: ResearchRepository,
    risk_repository: RiskRepository,
    simulations: PaperSimulationStore,
) -> PaperSimulationWorkflow:
    return PaperSimulationWorkflow(
        evidence=PostgresPaperEvidenceGateway(research_repository, risk_repository),
        simulations=simulations,
        phase10_code_version_git_sha=cast(str, CODE_VERSION_GIT_SHA),
    )


def _request(source: ApprovalAssessmentArtifact, tag: str) -> PaperSimulationCreateRequest:
    return PaperSimulationCreateRequest(
        approval_assessment_id=source.assessment_id,
        simulation_idempotency_key=f"phase10-postgres-{tag}-{uuid4().hex}",
    )


def test_postgres_roundtrip_preserves_exact_hash_bound_children() -> None:
    _require_postgres()
    assert DATABASE_URL is not None
    research_repository = ResearchRepository(DATABASE_URL)
    risk_repository = RiskRepository(DATABASE_URL)
    repository = PaperRepository(DATABASE_URL)
    try:
        source = _approved_source(research_repository, risk_repository, tag="roundtrip")
        request = _request(source, "roundtrip")
        workflow = _workflow(research_repository, risk_repository, repository)
        artifact = workflow.create_simulation(request)
        repeated = workflow.create_simulation(request)

        assert repeated == artifact
        assert artifact.outcome is PaperSimulationOutcome.SIMULATED_COMPLETE
        assert tuple(check.code for check in artifact.checks) == PAPER_CHECK_ORDER
        assert all(check.status is PaperCheckStatus.PASS for check in artifact.checks)
        assert len(artifact.ledger_entries) == 1
        assert artifact.transition_revalidation_proof.revalidation_proof_id != source.assessment_id
        assert (
            artifact.transition_revalidation_proof.revalidation_proof_sha256
            in artifact.checks[1].evidence_sha256s
        )
        assert repository.get_simulation(artifact.simulation_run_id) == artifact
        assert repository.find_by_idempotency_key(request.simulation_idempotency_key) == artifact
        summaries = repository.list_simulations(
            source_assessment_id=source.assessment_id,
            limit=100,
        )
        assert [summary.simulation_run_id for summary in summaries] == [artifact.simulation_run_id]
        with repository.engine.connect() as connection:
            assert connection.scalar(
                text(
                    "SELECT count(*) FROM paper_simulation_checks WHERE simulation_run_id = :run_id"
                ),
                {"run_id": artifact.simulation_run_id},
            ) == len(PAPER_CHECK_ORDER)
            assert (
                connection.scalar(
                    text(
                        "SELECT count(*) FROM paper_simulation_ledger_entries "
                        "WHERE simulation_run_id = :run_id"
                    ),
                    {"run_id": artifact.simulation_run_id},
                )
                == 1
            )
    finally:
        repository.dispose()
        risk_repository.dispose()
        research_repository.dispose()


@pytest.mark.parametrize("dimension", ("policy", "scope"))
def test_postgres_preexisting_authority_supersession_persists_blocked_without_ledger(
    dimension: str,
) -> None:
    _require_postgres()
    assert DATABASE_URL is not None
    research_repository = ResearchRepository(DATABASE_URL)
    risk_repository = RiskRepository(DATABASE_URL)
    repository = PaperRepository(DATABASE_URL)
    try:
        source = _approved_source(research_repository, risk_repository, tag="superseded")
        source_policy = risk_repository.get_policy(source.approval_policy_version_id)
        source_scope = risk_repository.get_scope(source.approval_scope_version_id)
        expected_policy_id = source.approval_policy_version_id
        expected_scope_id = source.approval_scope_version_id
        with risk_repository.engine.begin() as connection:
            if dimension == "policy":
                later_policy = build_approval_policy(
                    policy_id=source_policy.policy_id,
                    policy_version=source_policy.policy_version + 1,
                    valid_from_utc=datetime.now(UTC) - timedelta(minutes=1),
                    expires_at_utc=datetime.now(UTC) + timedelta(days=1),
                )
                RiskRepository._insert_policy(connection, later_policy)
                expected_policy_id = later_policy.approval_policy_version_id
            else:
                later_scope_payload = source_scope.model_dump(
                    mode="python",
                    exclude={"approval_scope_version_id", "scope_sha256"},
                )
                later_scope_payload.update(
                    {
                        "scope_version": source_scope.scope_version + 1,
                        "valid_from_utc": datetime.now(UTC) - timedelta(minutes=1),
                        "expires_at_utc": datetime.now(UTC) + timedelta(days=1),
                    }
                )
                later_scope_sha256 = domain_sha256(
                    PHASE7_SCOPE_HASH_DOMAIN,
                    later_scope_payload,
                )
                later_scope = ApprovalScope.model_validate(
                    {
                        **later_scope_payload,
                        "approval_scope_version_id": identity(
                            PHASE7_SCOPE_NAMESPACE,
                            later_scope_sha256,
                        ),
                        "scope_sha256": later_scope_sha256,
                    }
                )
                RiskRepository._insert_scope(connection, later_scope)
                expected_scope_id = later_scope.approval_scope_version_id

        artifact = _workflow(
            research_repository,
            risk_repository,
            repository,
        ).create_simulation(_request(source, "superseded"))
        transition = risk_repository.get_assessment(artifact.transition_assessment_id)

        assert artifact.source_assessment_id == source.assessment_id
        assert artifact.source_assessment_artifact_sha256 == source.artifact_sha256
        assert source.approval_policy_version_id == source_policy.approval_policy_version_id
        assert source.approval_scope_version_id == source_scope.approval_scope_version_id
        assert transition.outcome is ApprovalAssessmentOutcome.FAIL_REJECT
        assert transition.approval_policy_version_id == expected_policy_id
        assert transition.approval_scope_version_id == expected_scope_id
        assert transition.human_authorization_evidence_id == (
            source.human_authorization_evidence_id
        )
        assert transition.risk_input_id == source.risk_input_id
        assert artifact.approval_policy_version_id == expected_policy_id
        assert artifact.approval_scope_version_id == expected_scope_id
        assert artifact.transition_revalidation_proof.transition_assessment_id == (
            transition.assessment_id
        )
        assert artifact.outcome is PaperSimulationOutcome.BLOCKED
        assert artifact.checks[1].status is PaperCheckStatus.BLOCKED
        assert artifact.ledger_entries == ()
        assert repository.get_simulation(artifact.simulation_run_id) == artifact
        with repository.engine.connect() as connection:
            assert (
                connection.scalar(
                    text(
                        "SELECT count(*) FROM paper_simulation_ledger_entries "
                        "WHERE simulation_run_id = :run_id"
                    ),
                    {"run_id": artifact.simulation_run_id},
                )
                == 0
            )
    finally:
        repository.dispose()
        risk_repository.dispose()
        research_repository.dispose()


def test_postgres_two_writers_are_idempotent_and_store_one_complete_bundle() -> None:
    _require_postgres()
    assert DATABASE_URL is not None
    research_repository = ResearchRepository(DATABASE_URL)
    risk_repository = RiskRepository(DATABASE_URL)
    repository = PaperRepository(DATABASE_URL)
    try:
        source = _approved_source(research_repository, risk_repository, tag="concurrency")
        request = _request(source, "concurrency")
        barrier = Barrier(2)

        class BarrierStore:
            def find_by_idempotency_key(self, key: str) -> PaperSimulationArtifact | None:
                existing = repository.find_by_idempotency_key(key)
                barrier.wait(timeout=30)
                return existing

            def create_simulation(
                self, artifact: PaperSimulationArtifact
            ) -> PaperSimulationArtifact:
                return repository.create_simulation(artifact)

            def get_simulation(self, simulation_run_id: UUID) -> PaperSimulationArtifact:
                return repository.get_simulation(simulation_run_id)

            def list_simulations(
                self,
                *,
                source_assessment_id: UUID | None,
                limit: int,
            ) -> list[PaperSimulationSummary]:
                return repository.list_simulations(
                    source_assessment_id=source_assessment_id,
                    limit=limit,
                )

        workflows = (
            _workflow(research_repository, risk_repository, BarrierStore()),
            _workflow(research_repository, risk_repository, BarrierStore()),
        )

        def create(workflow: PaperSimulationWorkflow) -> PaperSimulationArtifact:
            return workflow.create_simulation(request)

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = tuple(executor.map(create, workflows))
        assert results[0] == results[1]
        with repository.engine.connect() as connection:
            assert (
                connection.scalar(
                    text(
                        "SELECT count(*) FROM paper_simulation_runs "
                        "WHERE simulation_idempotency_key = :key"
                    ),
                    {"key": request.simulation_idempotency_key},
                )
                == 1
            )
            assert connection.scalar(
                text(
                    "SELECT count(*) FROM paper_simulation_checks WHERE simulation_run_id = :run_id"
                ),
                {"run_id": results[0].simulation_run_id},
            ) == len(PAPER_CHECK_ORDER)
    finally:
        repository.dispose()
        risk_repository.dispose()
        research_repository.dispose()


def test_postgres_rejects_a_forged_check_payload_before_persistence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _require_postgres()
    assert DATABASE_URL is not None
    research_repository = ResearchRepository(DATABASE_URL)
    risk_repository = RiskRepository(DATABASE_URL)
    repository = PaperRepository(DATABASE_URL)
    try:
        source = _approved_source(research_repository, risk_repository, tag="forged-check")
        candidate = _workflow(
            research_repository,
            risk_repository,
            cast(PaperSimulationStore, _CandidateStore()),
        ).create_simulation(_request(source, "forged-check"))
        original_insert = repository_module._insert_row

        def forged_insert(
            connection: Connection,
            table: str,
            row: dict[str, Any],
            *,
            json_columns: frozenset[str] = frozenset(),
        ) -> None:
            changed = dict(row)
            if table == "paper_simulation_checks" and changed.get("ordinal") == 1:
                payload = dict(changed["payload"])
                payload["reason_code"] = "forged_payload_reason"
                changed["payload"] = payload
            original_insert(connection, table, changed, json_columns=json_columns)

        monkeypatch.setattr(repository_module, "_insert_row", forged_insert)
        with pytest.raises(DBAPIError) as error:
            with repository.engine.begin() as connection:
                PaperRepository._insert_simulation(connection, candidate)
        assert "Phase 10 simulation check payload mismatch" in str(error.value)
        assert repository.find_by_idempotency_key(candidate.simulation_idempotency_key) is None
    finally:
        repository.dispose()
        risk_repository.dispose()
        research_repository.dispose()


def test_postgres_rejects_a_hash_valid_ledger_not_bound_to_configuration() -> None:
    _require_postgres()
    assert DATABASE_URL is not None
    research_repository = ResearchRepository(DATABASE_URL)
    risk_repository = RiskRepository(DATABASE_URL)
    repository = PaperRepository(DATABASE_URL)
    try:
        source = _approved_source(research_repository, risk_repository, tag="ledger-binding")
        candidate = _workflow(
            research_repository,
            risk_repository,
            cast(PaperSimulationStore, _CandidateStore()),
        ).create_simulation(_request(source, "ledger-binding"))
        ledger_payload = candidate.ledger_entries[0].model_dump(
            mode="python", exclude={"ledger_entry_id", "ledger_entry_sha256"}
        )
        ledger_payload.update(
            {
                "approved_proposed_notional": Decimal("100"),
                "requested_quantity": Decimal("1"),
                "filled_quantity": Decimal("1"),
                "participation_rate": Decimal("0.00001"),
                "commission_cost": Decimal("0.01"),
                "spread_cost": Decimal("0.02"),
                "impact_cost": Decimal("0.01"),
                "latency_cost": Decimal("0.01"),
                "total_cost": Decimal("0.05"),
                "position_quantity_after": Decimal("1"),
                "cash_after": Decimal("999899.95"),
            }
        )
        ledger_sha256 = domain_sha256(PHASE10_LEDGER_HASH_DOMAIN, ledger_payload)
        forged_ledger = PaperSimulationLedgerEntry.model_validate(
            {
                **ledger_payload,
                "ledger_entry_id": identity(PHASE10_LEDGER_NAMESPACE, ledger_sha256),
                "ledger_entry_sha256": ledger_sha256,
            }
        )
        forged = candidate.model_copy(update={"ledger_entries": (forged_ledger,)})
        forged_payload = forged.model_dump(
            mode="python", exclude={"simulation_run_id", "artifact_sha256", "created_at_utc"}
        )
        forged = forged.model_copy(
            update={"artifact_sha256": domain_sha256(PHASE10_ARTIFACT_HASH_DOMAIN, forged_payload)}
        )
        with pytest.raises(DBAPIError) as error:
            with repository.engine.begin() as connection:
                PaperRepository._insert_simulation(connection, forged)
        assert "Phase 10 simulation ledger payload mismatch" in str(error.value)
        assert repository.find_by_idempotency_key(candidate.simulation_idempotency_key) is None
    finally:
        repository.dispose()
        risk_repository.dispose()
        research_repository.dispose()


def test_postgres_rejects_self_hashed_configuration_not_bound_to_phase6() -> None:
    _require_postgres()
    assert DATABASE_URL is not None
    research_repository = ResearchRepository(DATABASE_URL)
    risk_repository = RiskRepository(DATABASE_URL)
    repository = PaperRepository(DATABASE_URL)
    try:
        source = _approved_source(research_repository, risk_repository, tag="config-binding")
        request = _request(source, "config-binding")
        candidate = _workflow(
            research_repository,
            risk_repository,
            cast(PaperSimulationStore, _CandidateStore()),
        ).create_simulation(request)
        configuration_payload = candidate.configuration.model_dump(
            mode="python",
            exclude={"configuration_instance_id", "configuration_sha256"},
        )
        configuration_payload["research_configuration_sha256"] = "f" * 64
        configuration_sha256 = domain_sha256(
            PHASE10_CONFIGURATION_HASH_DOMAIN, configuration_payload
        )
        forged_configuration = candidate.configuration.model_copy(
            update={
                "research_configuration_sha256": "f" * 64,
                "configuration_instance_id": identity(
                    PHASE10_CONFIGURATION_NAMESPACE, configuration_sha256
                ),
                "configuration_sha256": configuration_sha256,
            }
        )
        request_fingerprint_sha256 = paper_request_fingerprint(
            request=request,
            source_assessment_sha256=candidate.source_assessment_artifact_sha256,
            transition_assessment_sha256=(candidate.transition_assessment_artifact_sha256),
            currentness_state_sha256=candidate.currentness_state_sha256,
            revalidation_proof_sha256=(
                candidate.transition_revalidation_proof.revalidation_proof_sha256
            ),
            configuration_sha256=configuration_sha256,
            phase10_code_version_git_sha=candidate.phase10_code_version_git_sha,
        )
        forged = candidate.model_copy(
            update={
                "configuration": forged_configuration,
                "request_fingerprint_sha256": request_fingerprint_sha256,
                "simulation_run_id": identity(PHASE10_RUN_NAMESPACE, request_fingerprint_sha256),
            }
        )
        forged_payload = forged.model_dump(
            mode="python", exclude={"simulation_run_id", "artifact_sha256", "created_at_utc"}
        )
        forged = forged.model_copy(
            update={"artifact_sha256": domain_sha256(PHASE10_ARTIFACT_HASH_DOMAIN, forged_payload)}
        )
        with pytest.raises(DBAPIError) as error:
            with repository.engine.begin() as connection:
                PaperRepository._insert_simulation(connection, forged)
        assert "Phase 10 source and transition lineage mismatch" in str(error.value)
        assert repository.find_by_idempotency_key(candidate.simulation_idempotency_key) is None
    finally:
        repository.dispose()
        risk_repository.dispose()
        research_repository.dispose()


def test_postgres_rejects_cross_assessment_transition_lineage() -> None:
    _require_postgres()
    assert DATABASE_URL is not None
    research_repository = ResearchRepository(DATABASE_URL)
    risk_repository = RiskRepository(DATABASE_URL)
    repository = PaperRepository(DATABASE_URL)
    try:
        source = _approved_source(research_repository, risk_repository, tag="lineage-source")
        other_source = _approved_source(
            research_repository,
            risk_repository,
            tag="lineage-transition",
        )
        request = _request(source, "lineage-source")
        candidate_store = cast(PaperSimulationStore, _CandidateStore())
        source_candidate = _workflow(
            research_repository,
            risk_repository,
            candidate_store,
        ).create_simulation(request)
        transition_candidate = _workflow(
            research_repository,
            risk_repository,
            candidate_store,
        ).create_simulation(_request(other_source, "lineage-transition"))
        revalidation_proof = build_transition_revalidation_proof(
            request=request,
            source_assessment_artifact_sha256=(source_candidate.source_assessment_artifact_sha256),
            transition_assessment_id=transition_candidate.transition_assessment_id,
            transition_assessment_artifact_sha256=(
                transition_candidate.transition_assessment_artifact_sha256
            ),
            transition_currentness_state_sha256=(
                transition_candidate.transition_currentness_state_sha256
            ),
            transition_revocation_set_sha256=(
                transition_candidate.transition_revocation_set_sha256
            ),
            decision_time_utc=source_candidate.decision_time_utc,
            phase10_code_version_git_sha=source_candidate.phase10_code_version_git_sha,
        )
        currentness_sha256 = paper_currentness_sha256(
            source_assessment_sha256=source_candidate.source_assessment_artifact_sha256,
            transition_assessment_sha256=(
                transition_candidate.transition_assessment_artifact_sha256
            ),
            transition_currentness_state_sha256=(
                transition_candidate.transition_currentness_state_sha256
            ),
            transition_revocation_set_sha256=(
                transition_candidate.transition_revocation_set_sha256
            ),
            revalidation_proof_sha256=revalidation_proof.revalidation_proof_sha256,
        )
        request_fingerprint_sha256 = paper_request_fingerprint(
            request=request,
            source_assessment_sha256=source_candidate.source_assessment_artifact_sha256,
            transition_assessment_sha256=(
                transition_candidate.transition_assessment_artifact_sha256
            ),
            currentness_state_sha256=currentness_sha256,
            revalidation_proof_sha256=revalidation_proof.revalidation_proof_sha256,
            configuration_sha256=source_candidate.configuration.configuration_sha256,
            phase10_code_version_git_sha=source_candidate.phase10_code_version_git_sha,
        )
        simulation_run_id = identity(PHASE10_RUN_NAMESPACE, request_fingerprint_sha256)
        ledger = build_simulation_ledger(
            simulation_run_id=simulation_run_id,
            configuration=source_candidate.configuration,
        )
        transition_check_payload = transition_candidate.checks[1].model_dump(
            mode="python", exclude={"check_sha256"}
        )
        transition_check_payload["evidence_sha256s"] = tuple(
            sorted(
                {
                    *transition_candidate.checks[1].evidence_sha256s,
                    revalidation_proof.revalidation_proof_sha256,
                }
                - {transition_candidate.transition_revalidation_proof.revalidation_proof_sha256}
            )
        )
        transition_check = PaperSimulationCheck.model_validate(
            {
                **transition_check_payload,
                "check_sha256": domain_sha256(PHASE10_CHECK_HASH_DOMAIN, transition_check_payload),
            }
        )
        checks = list(source_candidate.checks)
        checks[1] = transition_check
        payload = source_candidate.model_dump(
            mode="python",
            exclude={"simulation_run_id", "artifact_sha256", "created_at_utc"},
        )
        payload.update(
            {
                "currentness_state_sha256": currentness_sha256,
                "request_fingerprint_sha256": request_fingerprint_sha256,
                "transition_assessment_id": transition_candidate.transition_assessment_id,
                "transition_assessment_artifact_sha256": (
                    transition_candidate.transition_assessment_artifact_sha256
                ),
                "transition_currentness_state_sha256": (
                    transition_candidate.transition_currentness_state_sha256
                ),
                "transition_revocation_set_sha256": (
                    transition_candidate.transition_revocation_set_sha256
                ),
                "transition_revalidation_proof": revalidation_proof,
                "checks": tuple(checks),
                "ledger_entries": (ledger,),
            }
        )
        forged = PaperSimulationArtifact.model_validate(
            {
                **payload,
                "simulation_run_id": simulation_run_id,
                "artifact_sha256": domain_sha256(PHASE10_ARTIFACT_HASH_DOMAIN, payload),
                "created_at_utc": source_candidate.created_at_utc,
            }
        )
        with pytest.raises(PaperRepositoryConflict) as error:
            repository.create_simulation(forged)
        assert "could not be stored" in str(error.value)
        assert repository.find_by_idempotency_key(request.simulation_idempotency_key) is None
    finally:
        repository.dispose()
        risk_repository.dispose()
        research_repository.dispose()


def test_postgres_rejects_blocked_transition_from_unrelated_authority_families() -> None:
    _require_postgres()
    assert DATABASE_URL is not None
    research_repository = ResearchRepository(DATABASE_URL)
    risk_repository = RiskRepository(DATABASE_URL)
    repository = PaperRepository(DATABASE_URL)
    try:
        source = _approved_source(
            research_repository,
            risk_repository,
            tag="unrelated-transition-source",
        )
        research = research_repository.get_run(source.research_run_id)
        lineage = phase6_lineage_from_research_artifact(research)
        decision_time = datetime.now(UTC)
        unrelated_policy = build_approval_policy(
            policy_id=f"phase10-unrelated-policy-{uuid4().hex}",
            valid_from_utc=decision_time - timedelta(days=1),
            expires_at_utc=decision_time + timedelta(days=1),
        )
        unrelated_scope = build_approval_scope(
            lineage,
            unrelated_policy,
            scope_id=f"phase10-unrelated-scope-{uuid4().hex}",
            valid_from_utc=decision_time - timedelta(days=1),
            expires_at_utc=decision_time + timedelta(days=1),
        )
        with risk_repository.engine.begin() as connection:
            RiskRepository._insert_policy(connection, unrelated_policy)
            RiskRepository._insert_scope(connection, unrelated_scope)
        transition = ApprovalWorkflow(
            research_store=Phase6ResearchStoreAdapter(research_repository),
            risk_store=risk_repository,
            assessment_time_utc=decision_time,
            phase7_code_version_git_sha=cast(str, CODE_VERSION_GIT_SHA),
        ).create_assessment(
            ApprovalAssessmentCreateRequest(
                research_run_id=source.research_run_id,
                approval_policy_version_id=unrelated_policy.approval_policy_version_id,
                approval_scope_version_id=unrelated_scope.approval_scope_version_id,
                human_authorization_evidence_id=(source.human_authorization_evidence_id),
                risk_input_id=source.risk_input_id,
            )
        )
        assert transition.outcome is ApprovalAssessmentOutcome.FAIL_REJECT

        class FixedEvidenceGateway:
            def get_assessment(self, assessment_id: UUID) -> ApprovalAssessmentArtifact:
                assert assessment_id == source.assessment_id
                return source

            def get_research_run(self, run_id: UUID) -> ResearchRunArtifact:
                assert run_id == research.run_id
                return research

            def get_risk_input(self, risk_input_id: UUID):
                return risk_repository.get_risk_input(risk_input_id)

            def revalidate_assessment(
                self,
                selected_source: ApprovalAssessmentArtifact,
                *,
                decision_time_utc: datetime,
                code_version_git_sha: str,
            ) -> ApprovalAssessmentArtifact:
                assert selected_source == source
                assert decision_time_utc == decision_time
                assert code_version_git_sha == CODE_VERSION_GIT_SHA
                return transition

        request = _request(source, "unrelated-transition")
        candidate = PaperSimulationWorkflow(
            evidence=FixedEvidenceGateway(),
            simulations=cast(PaperSimulationStore, _CandidateStore()),
            phase10_code_version_git_sha=cast(str, CODE_VERSION_GIT_SHA),
            clock=lambda: decision_time,
        ).create_simulation(request)
        assert candidate.outcome is PaperSimulationOutcome.BLOCKED
        with pytest.raises(PaperRepositoryConflict, match="could not be stored"):
            repository.create_simulation(candidate)
        assert repository.find_by_idempotency_key(request.simulation_idempotency_key) is None
    finally:
        repository.dispose()
        risk_repository.dispose()
        research_repository.dispose()


def test_postgres_deferred_completeness_rejects_a_missing_ledger_bundle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _require_postgres()
    assert DATABASE_URL is not None
    research_repository = ResearchRepository(DATABASE_URL)
    risk_repository = RiskRepository(DATABASE_URL)
    repository = PaperRepository(DATABASE_URL)
    try:
        source = _approved_source(research_repository, risk_repository, tag="incomplete")
        candidate = _workflow(
            research_repository,
            risk_repository,
            cast(PaperSimulationStore, _CandidateStore()),
        ).create_simulation(_request(source, "incomplete"))
        original_insert = repository_module._insert_row

        def incomplete_insert(
            connection: Connection,
            table: str,
            row: dict[str, Any],
            *,
            json_columns: frozenset[str] = frozenset(),
        ) -> None:
            if table != "paper_simulation_ledger_entries":
                original_insert(connection, table, row, json_columns=json_columns)

        monkeypatch.setattr(repository_module, "_insert_row", incomplete_insert)
        with pytest.raises(DBAPIError) as error:
            with repository.engine.begin() as connection:
                PaperRepository._insert_simulation(connection, candidate)
        assert "Phase 10 simulation requires exact complete checks and ledger" in str(error.value)
        assert repository.find_by_idempotency_key(candidate.simulation_idempotency_key) is None
    finally:
        repository.dispose()
        risk_repository.dispose()
        research_repository.dispose()


@pytest.mark.parametrize("dimension", ("policy", "scope"))
def test_postgres_serializes_concurrent_authority_supersession(dimension: str) -> None:
    _require_postgres()
    assert DATABASE_URL is not None
    research_repository = ResearchRepository(DATABASE_URL)
    risk_repository = RiskRepository(DATABASE_URL)
    repository = PaperRepository(DATABASE_URL)
    try:
        source = _approved_source(
            research_repository,
            risk_repository,
            tag=f"authority-race-{dimension}",
        )
        candidate = _workflow(
            research_repository,
            risk_repository,
            cast(PaperSimulationStore, _CandidateStore()),
        ).create_simulation(_request(source, f"authority-race-{dimension}"))
        later_evidence: Any
        insert_later: Any
        if dimension == "policy":
            current_policy = risk_repository.get_policy(source.approval_policy_version_id)
            later_evidence = build_approval_policy(
                policy_id=current_policy.policy_id,
                policy_version=current_policy.policy_version + 1,
                valid_from_utc=candidate.decision_time_utc - timedelta(seconds=1),
                expires_at_utc=candidate.decision_time_utc + timedelta(days=1),
            )
            insert_later = RiskRepository._insert_policy
        else:
            current_scope = risk_repository.get_scope(source.approval_scope_version_id)
            later_payload = current_scope.model_dump(
                mode="python",
                exclude={"approval_scope_version_id", "scope_sha256"},
            )
            later_payload.update(
                {
                    "scope_version": current_scope.scope_version + 1,
                    "valid_from_utc": candidate.decision_time_utc - timedelta(seconds=1),
                    "expires_at_utc": candidate.decision_time_utc + timedelta(days=1),
                }
            )
            later_sha256 = domain_sha256(PHASE7_SCOPE_HASH_DOMAIN, later_payload)
            later_evidence = ApprovalScope.model_validate(
                {
                    **later_payload,
                    "approval_scope_version_id": identity(PHASE7_SCOPE_NAMESPACE, later_sha256),
                    "scope_sha256": later_sha256,
                }
            )
            insert_later = RiskRepository._insert_scope

        with risk_repository.engine.connect() as authority_connection:
            authority_transaction = authority_connection.begin()
            insert_later(authority_connection, later_evidence)
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(repository.create_simulation, candidate)
                with pytest.raises(TimeoutError):
                    future.result(timeout=0.5)
                authority_transaction.commit()
                with pytest.raises(PaperRepositoryConflict, match="could not be stored"):
                    future.result(timeout=30)
        assert repository.find_by_idempotency_key(candidate.simulation_idempotency_key) is None
    finally:
        repository.dispose()
        risk_repository.dispose()
        research_repository.dispose()


def test_postgres_every_phase10_table_rejects_update_delete_and_truncate() -> None:
    _require_postgres()
    assert DATABASE_URL is not None
    research_repository = ResearchRepository(DATABASE_URL)
    risk_repository = RiskRepository(DATABASE_URL)
    repository = PaperRepository(DATABASE_URL)
    try:
        source = _approved_source(research_repository, risk_repository, tag="immutable")
        artifact = _workflow(
            research_repository,
            risk_repository,
            repository,
        ).create_simulation(_request(source, "immutable"))
        cases = (
            (
                "paper_simulation_runs",
                "simulation_run_id",
                artifact.simulation_run_id,
            ),
            (
                "paper_simulation_checks",
                "simulation_run_id",
                artifact.simulation_run_id,
            ),
            (
                "paper_simulation_ledger_entries",
                "simulation_run_id",
                artifact.simulation_run_id,
            ),
        )
        for table, key_column, key_value in cases:
            statements = (
                text(
                    f"UPDATE {table} SET created_at_utc = created_at_utc WHERE {key_column} = :key"
                ),
                text(f"DELETE FROM {table} WHERE {key_column} = :key"),
                text(f"TRUNCATE TABLE {table} CASCADE"),
            )
            for statement in statements:
                with pytest.raises(DBAPIError) as error:
                    with repository.engine.begin() as connection:
                        connection.execute(statement, {"key": key_value})
                assert APPEND_ONLY_ERROR in str(error.value)
        assert repository.get_simulation(artifact.simulation_run_id) == artifact
    finally:
        repository.dispose()
        risk_repository.dispose()
        research_repository.dispose()
