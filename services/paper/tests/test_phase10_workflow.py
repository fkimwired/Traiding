from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from threading import Lock
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fable5_backtester.contracts import PromotionState
from fable5_mapping.models import CanonicalFamily
from fable5_paper.canonical import (
    PHASE10_ARTIFACT_HASH_DOMAIN,
    PHASE10_LEDGER_HASH_DOMAIN,
    PHASE10_LEDGER_NAMESPACE,
    domain_sha256,
    identity,
)
from fable5_paper.contracts import (
    PAPER_CHECK_ORDER,
    PaperCheckCode,
    PaperCheckStatus,
    PaperSimulationArtifact,
    PaperSimulationConfiguration,
    PaperSimulationCreateRequest,
    PaperSimulationLedgerEntry,
    PaperSimulationOutcome,
    PaperSimulationSummary,
)
from fable5_paper.workflow import (
    PaperEvidenceNotFound,
    PaperSimulationWorkflow,
    PaperWorkflowConflict,
)
from fable5_research.contracts import ResearchConfigurationId, ResearchRunStatus
from fable5_risk.contracts import (
    ApprovalAssessmentArtifact,
    ApprovalAssessmentCreateRequest,
    ApprovalAssessmentOutcome,
    ApprovalAssessmentSummary,
    AuthorizationRevocationArtifact,
    AuthorizationRevocationSummary,
    Phase6ApprovalLineage,
)
from fable5_risk.fixtures import (
    SYNTHETIC_ASSESSMENT_TIME_UTC,
    ApprovalEvidenceBundle,
    build_approval_policy,
    build_nominal_evidence_bundle,
    build_synthetic_phase6_lineage,
)
from fable5_risk.workflow import ApprovalWorkflow
from pydantic import ValidationError

CODE_SHA = "a" * 40


class MemoryResearchStore:
    def __init__(self, lineage: Phase6ApprovalLineage) -> None:
        self.lineage = lineage

    def get_approval_lineage(self, research_run_id: UUID) -> Phase6ApprovalLineage:
        if research_run_id != self.lineage.research_run_id:
            raise LookupError(research_run_id)
        return self.lineage


class MemoryRiskStore:
    def __init__(self, bundle: ApprovalEvidenceBundle) -> None:
        self.bundle = bundle
        self.policies = {bundle.policy.approval_policy_version_id: bundle.policy}
        self.scopes = {bundle.scope.approval_scope_version_id: bundle.scope}
        self.assessments: dict[UUID, ApprovalAssessmentArtifact] = {}

    def get_approval_policy(self, approval_policy_version_id: UUID):
        try:
            return self.policies[approval_policy_version_id]
        except KeyError as exc:
            raise LookupError(approval_policy_version_id) from exc

    def get_approval_scope(self, approval_scope_version_id: UUID):
        try:
            return self.scopes[approval_scope_version_id]
        except KeyError as exc:
            raise LookupError(approval_scope_version_id) from exc

    def get_human_authorization_evidence(self, human_authorization_evidence_id: UUID):
        if (
            human_authorization_evidence_id
            != self.bundle.authorization.human_authorization_evidence_id
        ):
            raise LookupError(human_authorization_evidence_id)
        return self.bundle.authorization

    def get_risk_input(self, risk_input_id: UUID):
        if risk_input_id != self.bundle.risk_input.risk_input_id:
            raise LookupError(risk_input_id)
        return self.bundle.risk_input

    def find_authorization_revocations(
        self, human_authorization_evidence_id: UUID
    ) -> list[AuthorizationRevocationArtifact]:
        return []

    def create_assessment(self, artifact: ApprovalAssessmentArtifact) -> ApprovalAssessmentArtifact:
        return self.assessments.setdefault(artifact.assessment_id, artifact)

    def get_assessment(self, assessment_id: UUID) -> ApprovalAssessmentArtifact:
        return self.assessments[assessment_id]

    def list_assessments(self, *, limit: int) -> list[ApprovalAssessmentSummary]:
        return []

    def create_revocation(
        self, artifact: AuthorizationRevocationArtifact
    ) -> AuthorizationRevocationArtifact:
        raise AssertionError("revocations are not created in this fixture")

    def get_revocation(self, revocation_id: UUID) -> AuthorizationRevocationArtifact:
        raise LookupError(revocation_id)

    def list_revocations(
        self,
        *,
        human_authorization_evidence_id: UUID | None,
        limit: int,
    ) -> list[AuthorizationRevocationSummary]:
        return []


def assessment_request(
    lineage: Phase6ApprovalLineage, bundle: ApprovalEvidenceBundle
) -> ApprovalAssessmentCreateRequest:
    return ApprovalAssessmentCreateRequest(
        research_run_id=lineage.research_run_id,
        approval_policy_version_id=bundle.policy.approval_policy_version_id,
        approval_scope_version_id=bundle.scope.approval_scope_version_id,
        human_authorization_evidence_id=bundle.authorization.human_authorization_evidence_id,
        risk_input_id=bundle.risk_input.risk_input_id,
    )


def build_assessments() -> tuple[
    Phase6ApprovalLineage,
    ApprovalEvidenceBundle,
    ApprovalAssessmentArtifact,
    ApprovalAssessmentArtifact,
]:
    lineage = build_synthetic_phase6_lineage()
    bundle = build_nominal_evidence_bundle(lineage)
    risk_store = MemoryRiskStore(bundle)
    source = ApprovalWorkflow(
        research_store=MemoryResearchStore(lineage),
        risk_store=risk_store,
        assessment_time_utc=SYNTHETIC_ASSESSMENT_TIME_UTC,
        phase7_code_version_git_sha=CODE_SHA,
    ).create_assessment(assessment_request(lineage, bundle))
    expired = ApprovalWorkflow(
        research_store=MemoryResearchStore(lineage),
        risk_store=risk_store,
        assessment_time_utc=SYNTHETIC_ASSESSMENT_TIME_UTC + timedelta(days=3),
        phase7_code_version_git_sha=CODE_SHA,
    ).create_assessment(assessment_request(lineage, bundle))
    return lineage, bundle, source, expired


def research_artifact(lineage: Phase6ApprovalLineage) -> SimpleNamespace:
    specification = SimpleNamespace(
        specification_sha256=lineage.specification_sha256,
        signal_definition="Rank the synthetic PIT cross-section with the frozen linear model.",
        target_forecast_horizon="two synthetic sessions",
        required_capabilities=tuple(item.capability for item in lineage.snapshot_bindings),
        transaction_cost_model_id="phase5-transparent-cost-v1",
        slippage_model_id="phase5-transparent-slippage-v1",
        walk_forward=SimpleNamespace(outer_fold_count=3, inner_fold_count=2),
        risk_limits=(SimpleNamespace(name="max_notional"),),
        required_audit_fields=tuple(f"audit_field_{index}" for index in range(12)),
    )
    return SimpleNamespace(
        run_id=lineage.research_run_id,
        artifact_sha256=lineage.research_artifact_sha256,
        configuration_id=ResearchConfigurationId.A_PASS,
        configuration_sha256=lineage.research_configuration_sha256,
        specification=specification,
        snapshot_bundle_sha256=lineage.snapshot_bundle_sha256,
        snapshot_bindings=lineage.snapshot_bindings,
        family=CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING,
        model_output_sets=(SimpleNamespace(model_id="sector-relative-rank-linear-v1"),),
        status=ResearchRunStatus.COMPLETED,
        phase5_evaluation=SimpleNamespace(
            promotion_state=PromotionState.PASS_RESEARCH,
            evaluation_report_sha256=lineage.evaluation_report_sha256,
            policy_sha256=lineage.phase5_policy_sha256,
        ),
    )


@dataclass
class MemoryEvidenceGateway:
    source: ApprovalAssessmentArtifact
    transition: ApprovalAssessmentArtifact
    research: SimpleNamespace
    risk_input: object

    def get_assessment(self, assessment_id: UUID) -> ApprovalAssessmentArtifact:
        if assessment_id != self.source.assessment_id:
            raise LookupError(assessment_id)
        return self.source

    def get_research_run(self, run_id: UUID):
        if run_id != self.source.research_run_id:
            raise LookupError(run_id)
        return self.research

    def get_risk_input(self, risk_input_id: UUID):
        if risk_input_id != self.source.risk_input_id:
            raise LookupError(risk_input_id)
        return self.risk_input

    def revalidate_assessment(
        self,
        source: ApprovalAssessmentArtifact,
        *,
        decision_time_utc,
        code_version_git_sha: str,
    ) -> ApprovalAssessmentArtifact:
        assert source == self.source
        assert code_version_git_sha == CODE_SHA
        return self.transition


class MemorySimulationStore:
    def __init__(self) -> None:
        self.by_id: dict[UUID, PaperSimulationArtifact] = {}
        self.by_key: dict[str, PaperSimulationArtifact] = {}
        self._creation_locks: dict[str, Lock] = {}
        self._creation_locks_guard = Lock()

    @contextmanager
    def serialized_creation(self, key: str) -> Iterator[MemorySimulationStore]:
        with self._creation_locks_guard:
            lock = self._creation_locks.setdefault(key, Lock())
        with lock:
            yield self

    def find_by_idempotency_key(self, key: str) -> PaperSimulationArtifact | None:
        return self.by_key.get(key)

    def create_simulation(self, artifact: PaperSimulationArtifact) -> PaperSimulationArtifact:
        existing = self.by_key.get(artifact.simulation_idempotency_key)
        if existing is not None:
            if existing.source_assessment_id != artifact.source_assessment_id:
                raise PaperWorkflowConflict("idempotency conflict")
            return existing
        self.by_id[artifact.simulation_run_id] = artifact
        self.by_key[artifact.simulation_idempotency_key] = artifact
        return artifact

    def get_simulation(self, simulation_run_id: UUID) -> PaperSimulationArtifact:
        return self.by_id[simulation_run_id]

    def list_simulations(
        self,
        *,
        source_assessment_id: UUID | None,
        limit: int,
    ) -> list[PaperSimulationSummary]:
        artifacts = list(self.by_id.values())
        if source_assessment_id is not None:
            artifacts = [
                item for item in artifacts if item.source_assessment_id == source_assessment_id
            ]
        return [
            PaperSimulationSummary(
                simulation_run_id=item.simulation_run_id,
                artifact_sha256=item.artifact_sha256,
                source_assessment_id=item.source_assessment_id,
                transition_assessment_id=item.transition_assessment_id,
                outcome=item.outcome,
                reason_codes=item.reason_codes,
                decision_time_utc=item.decision_time_utc,
                created_at_utc=item.created_at_utc,
            )
            for item in artifacts[:limit]
        ]


def workflow(
    *, transition: ApprovalAssessmentArtifact | None = None
) -> tuple[PaperSimulationWorkflow, MemorySimulationStore, ApprovalAssessmentArtifact]:
    lineage, bundle, source, _expired = build_assessments()
    store = MemorySimulationStore()
    return (
        PaperSimulationWorkflow(
            evidence=MemoryEvidenceGateway(
                source=source,
                transition=transition or source,
                research=research_artifact(lineage),
                risk_input=bundle.risk_input,
            ),
            simulations=store,
            phase10_code_version_git_sha=CODE_SHA,
            clock=lambda: SYNTHETIC_ASSESSMENT_TIME_UTC,
        ),
        store,
        source,
    )


def test_completed_simulation_is_reference_only_deterministic_and_reconciled() -> None:
    service, store, source = workflow()
    request = PaperSimulationCreateRequest(
        approval_assessment_id=source.assessment_id,
        simulation_idempotency_key="phase10-unit-complete-001",
    )

    first = service.create_simulation(request)
    second = service.create_simulation(request)

    assert second == first
    assert len(store.by_id) == 1
    assert first.outcome is PaperSimulationOutcome.SIMULATED_COMPLETE
    assert tuple(item.code for item in first.checks) == PAPER_CHECK_ORDER
    assert all(item.status is PaperCheckStatus.PASS for item in first.checks)
    assert len(first.ledger_entries) == 1
    ledger = first.ledger_entries[0]
    assert ledger.approved_proposed_notional == ledger.requested_quantity * ledger.reference_price
    assert ledger.total_cost == (
        ledger.commission_cost
        + ledger.regulatory_fee_cost
        + ledger.spread_cost
        + ledger.impact_cost
        + ledger.latency_cost
        + ledger.borrow_cost
        + ledger.capacity_cost
    )
    assert (
        ledger.cash_after
        == ledger.cash_before - ledger.approved_proposed_notional - ledger.total_cost
    )
    assert first.external_submission is False
    assert first.live_path_absent is True
    assert first.no_personalized_investment_advice is True
    proof = first.transition_revalidation_proof
    assert first.transition_assessment_id == source.assessment_id
    assert proof.revalidation_proof_id != source.assessment_id
    assert proof.decision_time_utc == SYNTHETIC_ASSESSMENT_TIME_UTC
    transition_check = first.checks[1]
    assert proof.revalidation_proof_sha256 in transition_check.evidence_sha256s
    assert service.get_simulation(first.simulation_run_id) == first
    assert (
        service.list_simulations(source_assessment_id=source.assessment_id, limit=10)[
            0
        ].artifact_sha256
        == first.artifact_sha256
    )


def test_revalidation_proof_is_decision_time_bound_when_phase7_deduplicates() -> None:
    first_service, _first_store, source = workflow()
    request = PaperSimulationCreateRequest(
        approval_assessment_id=source.assessment_id,
        simulation_idempotency_key="phase10-unit-proof-time-001",
    )
    first = first_service.create_simulation(request)
    second_service, _second_store, _ = workflow()
    second_service.clock = lambda: SYNTHETIC_ASSESSMENT_TIME_UTC + timedelta(seconds=1)
    second = second_service.create_simulation(request)

    assert first.transition_assessment_id == second.transition_assessment_id == source.assessment_id
    assert (
        first.transition_revalidation_proof.revalidation_proof_sha256
        != second.transition_revalidation_proof.revalidation_proof_sha256
    )
    assert (
        first.transition_revalidation_proof.revalidation_proof_id
        != second.transition_revalidation_proof.revalidation_proof_id
    )
    assert first.currentness_state_sha256 != second.currentness_state_sha256
    assert first.request_fingerprint_sha256 != second.request_fingerprint_sha256


def test_configuration_rejects_any_noncanonical_fixture_economics() -> None:
    service, _store, source = workflow()
    artifact = service.create_simulation(
        PaperSimulationCreateRequest(
            approval_assessment_id=source.assessment_id,
            simulation_idempotency_key="phase10-unit-config-exact-001",
        )
    )
    changed = artifact.configuration.model_dump(mode="python")
    changed["reference_price"] = Decimal("101")
    with pytest.raises(ValidationError, match="sole server-owned fixture"):
        PaperSimulationConfiguration.model_validate(changed)


def test_artifact_rejects_an_internally_valid_ledger_from_another_universe() -> None:
    service, _store, source = workflow()
    artifact = service.create_simulation(
        PaperSimulationCreateRequest(
            approval_assessment_id=source.assessment_id,
            simulation_idempotency_key="phase10-unit-ledger-binding-001",
        )
    )
    ledger_payload = artifact.ledger_entries[0].model_dump(
        mode="python", exclude={"ledger_entry_id", "ledger_entry_sha256"}
    )
    ledger_payload["universe_id"] = "SYNTHETIC-OTHER-UNIVERSE"
    ledger_sha256 = domain_sha256(PHASE10_LEDGER_HASH_DOMAIN, ledger_payload)
    forged_ledger = PaperSimulationLedgerEntry.model_validate(
        {
            **ledger_payload,
            "ledger_entry_id": identity(PHASE10_LEDGER_NAMESPACE, ledger_sha256),
            "ledger_entry_sha256": ledger_sha256,
        }
    )
    artifact_payload = artifact.model_dump(
        mode="python", exclude={"simulation_run_id", "artifact_sha256", "created_at_utc"}
    )
    artifact_payload["ledger_entries"] = (forged_ledger,)
    with pytest.raises(ValidationError, match="exact simulation configuration and risk"):
        PaperSimulationArtifact.model_validate(
            {
                **artifact_payload,
                "simulation_run_id": artifact.simulation_run_id,
                "artifact_sha256": domain_sha256(PHASE10_ARTIFACT_HASH_DOMAIN, artifact_payload),
                "created_at_utc": artifact.created_at_utc,
            }
        )


def test_expired_transition_persists_blocked_without_a_ledger() -> None:
    _lineage, _bundle, _source, expired = build_assessments()
    service, _store, source = workflow(transition=expired)

    artifact = service.create_simulation(
        PaperSimulationCreateRequest(
            approval_assessment_id=source.assessment_id,
            simulation_idempotency_key="phase10-unit-blocked-001",
        )
    )

    assert artifact.outcome is PaperSimulationOutcome.BLOCKED
    assert artifact.ledger_entries == ()
    transition_check = next(
        item for item in artifact.checks if item.code is PaperCheckCode.TRANSITION_APPROVAL_FRESH
    )
    assert transition_check.status is PaperCheckStatus.BLOCKED
    assert transition_check.reason_code == "transition_approval_not_fresh"


def test_superseded_authority_persists_a_resolved_blocked_transition() -> None:
    lineage, bundle, source, _expired = build_assessments()
    risk_store = MemoryRiskStore(bundle)
    later_policy = build_approval_policy(
        policy_id=bundle.policy.policy_id,
        policy_version=bundle.policy.policy_version + 1,
        valid_from_utc=SYNTHETIC_ASSESSMENT_TIME_UTC - timedelta(minutes=1),
        expires_at_utc=SYNTHETIC_ASSESSMENT_TIME_UTC + timedelta(days=1),
    )
    risk_store.policies[later_policy.approval_policy_version_id] = later_policy
    transition = ApprovalWorkflow(
        research_store=MemoryResearchStore(lineage),
        risk_store=risk_store,
        assessment_time_utc=SYNTHETIC_ASSESSMENT_TIME_UTC,
        phase7_code_version_git_sha=CODE_SHA,
    ).create_assessment(
        ApprovalAssessmentCreateRequest(
            research_run_id=lineage.research_run_id,
            approval_policy_version_id=later_policy.approval_policy_version_id,
            approval_scope_version_id=bundle.scope.approval_scope_version_id,
            human_authorization_evidence_id=(bundle.authorization.human_authorization_evidence_id),
            risk_input_id=bundle.risk_input.risk_input_id,
        )
    )
    assert transition.outcome is ApprovalAssessmentOutcome.FAIL_REJECT

    store = MemorySimulationStore()
    service = PaperSimulationWorkflow(
        evidence=MemoryEvidenceGateway(
            source=source,
            transition=transition,
            research=research_artifact(lineage),
            risk_input=bundle.risk_input,
        ),
        simulations=store,
        phase10_code_version_git_sha=CODE_SHA,
        clock=lambda: SYNTHETIC_ASSESSMENT_TIME_UTC,
    )
    artifact = service.create_simulation(
        PaperSimulationCreateRequest(
            approval_assessment_id=source.assessment_id,
            simulation_idempotency_key="phase10-unit-superseded-001",
        )
    )

    assert source.approval_policy_version_id == bundle.policy.approval_policy_version_id
    assert artifact.source_assessment_id == source.assessment_id
    assert artifact.source_assessment_artifact_sha256 == source.artifact_sha256
    assert artifact.transition_assessment_id == transition.assessment_id
    assert artifact.approval_policy_version_id == later_policy.approval_policy_version_id
    assert (
        artifact.transition_revalidation_proof.transition_assessment_id == transition.assessment_id
    )
    assert artifact.outcome is PaperSimulationOutcome.BLOCKED
    assert artifact.checks[1].status is PaperCheckStatus.BLOCKED
    assert "transition_approval_not_fresh" in artifact.reason_codes
    assert artifact.ledger_entries == ()
    assert store.get_simulation(artifact.simulation_run_id) == artifact


def test_create_contract_rejects_every_client_authoritative_simulation_field() -> None:
    _, _, source = workflow()
    base = {
        "approval_assessment_id": source.assessment_id,
        "simulation_idempotency_key": "phase10-unit-contract-001",
    }
    for field, value in (
        ("simulated_side", "BUY"),
        ("quantity", "500"),
        ("price", "100"),
        ("model_id", "client-model"),
        ("outcome", "SIMULATED_COMPLETE"),
        ("endpoint", "https://example.invalid"),
        ("live", False),
    ):
        with pytest.raises(ValidationError):
            PaperSimulationCreateRequest.model_validate({**base, field: value})


def test_missing_code_sha_fails_before_evidence_or_persistence() -> None:
    service, store, source = workflow()
    service.phase10_code_version_git_sha = None
    with pytest.raises(PaperEvidenceNotFound, match="phase10_code_version_git_sha_missing"):
        service.create_simulation(
            PaperSimulationCreateRequest(
                approval_assessment_id=source.assessment_id,
                simulation_idempotency_key="phase10-unit-missing-sha",
            )
        )
    assert store.by_id == {}


def test_same_idempotency_key_cannot_cross_assessment_identity() -> None:
    service, store, source = workflow()
    key = "phase10-unit-idempotency-001"
    service.create_simulation(
        PaperSimulationCreateRequest(
            approval_assessment_id=source.assessment_id,
            simulation_idempotency_key=key,
        )
    )
    conflicting = PaperSimulationWorkflow(
        evidence=service.evidence,
        simulations=store,
        phase10_code_version_git_sha=CODE_SHA,
        clock=lambda: SYNTHETIC_ASSESSMENT_TIME_UTC,
    )
    with pytest.raises(PaperWorkflowConflict, match="another approval assessment"):
        conflicting.create_simulation(
            PaperSimulationCreateRequest(
                approval_assessment_id=uuid4(),
                simulation_idempotency_key=key,
            )
        )
