"""Fail-closed orchestration for one-shot local paper simulations."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from fable5_backtester.contracts import PromotionState
from fable5_data.canonical import canonical_json_bytes
from fable5_mapping.models import CanonicalFamily
from fable5_research.contracts import ResearchRunArtifact, ResearchRunStatus
from fable5_research.repository import (
    ResearchRepository,
    ResearchRepositoryConflict,
    ResearchRunNotFound,
)
from fable5_risk.contracts import (
    ApprovalAssessmentArtifact,
    ApprovalAssessmentCreateRequest,
    ApprovalAssessmentOutcome,
    ApprovalRiskInput,
    CheckStatus,
)
from fable5_risk.repository import RiskArtifactNotFound, RiskRepository, RiskRepositoryConflict
from fable5_risk.workflow import (
    ApprovalEvidenceNotFound,
    ApprovalWorkflow,
    ApprovalWorkflowConflict,
    Phase6ResearchStoreAdapter,
)
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from fable5_paper.canonical import (
    PHASE10_ARTIFACT_HASH_DOMAIN,
    PHASE10_CHECK_HASH_DOMAIN,
    PHASE10_RUN_NAMESPACE,
    domain_sha256,
    identity,
)
from fable5_paper.contracts import (
    PHASE10_DISCLAIMER,
    PaperCheckCode,
    PaperCheckStatus,
    PaperSimulationArtifact,
    PaperSimulationCheck,
    PaperSimulationCreateRequest,
    PaperSimulationOutcome,
    PaperSimulationSummary,
    build_transition_revalidation_proof,
    paper_currentness_sha256,
    paper_request_fingerprint,
    validate_code_git_sha,
)
from fable5_paper.evidence import (
    LocalSimulationEvidenceBundle,
    build_local_simulation_evidence_bundle,
)
from fable5_paper.fixtures import build_simulation_configuration, build_simulation_ledger


class PaperEvidenceNotFound(LookupError):
    """A required immutable Phase 6 or Phase 7 artifact is absent."""


class PaperWorkflowConflict(RuntimeError):
    """Resolved or persisted simulation evidence is internally inconsistent."""


class PaperSimulationCreation(Protocol):
    def find_by_idempotency_key(self, key: str) -> PaperSimulationArtifact | None: ...

    def create_simulation(self, artifact: PaperSimulationArtifact) -> PaperSimulationArtifact: ...


class PaperSimulationStore(PaperSimulationCreation, Protocol):
    def serialized_creation(
        self,
        key: str,
    ) -> AbstractContextManager[PaperSimulationCreation]: ...

    def get_simulation(self, simulation_run_id: UUID) -> PaperSimulationArtifact: ...

    def list_simulations(
        self,
        *,
        source_assessment_id: UUID | None,
        limit: int,
    ) -> list[PaperSimulationSummary]: ...


class PaperEvidenceGateway(Protocol):
    def get_assessment(self, assessment_id: UUID) -> ApprovalAssessmentArtifact: ...

    def get_research_run(self, run_id: UUID) -> ResearchRunArtifact: ...

    def get_risk_input(self, risk_input_id: UUID) -> ApprovalRiskInput: ...

    def revalidate_assessment(
        self,
        source: ApprovalAssessmentArtifact,
        *,
        decision_time_utc: datetime,
        code_version_git_sha: str,
    ) -> ApprovalAssessmentArtifact: ...


class PostgresPaperEvidenceGateway:
    """Reuse the exact Phase 6/7 repositories and Phase 7 evaluator."""

    def __init__(
        self,
        research_repository: ResearchRepository,
        risk_repository: RiskRepository,
    ) -> None:
        self.research_repository = research_repository
        self.risk_repository = risk_repository

    def get_assessment(self, assessment_id: UUID) -> ApprovalAssessmentArtifact:
        return self.risk_repository.get_assessment(assessment_id)

    def get_research_run(self, run_id: UUID) -> ResearchRunArtifact:
        return self.research_repository.get_run(run_id)

    def get_risk_input(self, risk_input_id: UUID) -> ApprovalRiskInput:
        return self.risk_repository.get_risk_input(risk_input_id)

    def _resolve_current_authority_versions(
        self,
        source: ApprovalAssessmentArtifact,
        *,
        decision_time_utc: datetime,
    ) -> tuple[UUID, UUID]:
        """Resolve the newest valid policy and scope in the source authority families.

        The historical source assessment remains immutable.  Only the transition
        assessment uses these decision-time versions, while retaining the source
        authorization and risk-input references.  A supersession therefore
        resolves to an explicit Phase 7 rejection instead of silently adopting
        new human or risk authority.
        """

        statement = text(
            """
            SELECT
                COALESCE(
                    (
                        SELECT candidate.approval_policy_version_id
                        FROM approval_policies AS candidate
                        WHERE candidate.policy_id = (
                            SELECT source.policy_id
                            FROM approval_policies AS source
                            WHERE source.approval_policy_version_id = :source_policy_id
                        )
                          AND candidate.valid_from_utc <= :decision_time_utc
                          AND :decision_time_utc < candidate.expires_at_utc
                        ORDER BY candidate.policy_version DESC,
                                 candidate.approval_policy_version_id DESC
                        LIMIT 1
                    ),
                    CAST(:source_policy_id AS uuid)
                ) AS approval_policy_version_id,
                COALESCE(
                    (
                        SELECT candidate.approval_scope_version_id
                        FROM approval_scopes AS candidate
                        WHERE candidate.scope_id = (
                            SELECT source.scope_id
                            FROM approval_scopes AS source
                            WHERE source.approval_scope_version_id = :source_scope_id
                        )
                          AND candidate.valid_from_utc <= :decision_time_utc
                          AND :decision_time_utc < candidate.expires_at_utc
                        ORDER BY candidate.scope_version DESC,
                                 candidate.approval_scope_version_id DESC
                        LIMIT 1
                    ),
                    CAST(:source_scope_id AS uuid)
                ) AS approval_scope_version_id
            """
        )
        try:
            with self.risk_repository.engine.connect() as connection:
                row = (
                    connection.execute(
                        statement,
                        {
                            "source_policy_id": source.approval_policy_version_id,
                            "source_scope_id": source.approval_scope_version_id,
                            "decision_time_utc": decision_time_utc,
                        },
                    )
                    .mappings()
                    .one()
                )
        except DBAPIError as exc:
            raise RiskRepositoryConflict(
                "Phase 10 decision-time authority versions could not be resolved"
            ) from exc
        return (
            UUID(str(row["approval_policy_version_id"])),
            UUID(str(row["approval_scope_version_id"])),
        )

    def revalidate_assessment(
        self,
        source: ApprovalAssessmentArtifact,
        *,
        decision_time_utc: datetime,
        code_version_git_sha: str,
    ) -> ApprovalAssessmentArtifact:
        policy_version_id, scope_version_id = self._resolve_current_authority_versions(
            source,
            decision_time_utc=decision_time_utc,
        )
        workflow = ApprovalWorkflow(
            research_store=Phase6ResearchStoreAdapter(self.research_repository),
            risk_store=self.risk_repository,
            assessment_time_utc=decision_time_utc,
            phase7_code_version_git_sha=code_version_git_sha,
        )
        return workflow.create_assessment(
            ApprovalAssessmentCreateRequest(
                research_run_id=source.research_run_id,
                approval_policy_version_id=policy_version_id,
                approval_scope_version_id=scope_version_id,
                human_authorization_evidence_id=source.human_authorization_evidence_id,
                risk_input_id=source.risk_input_id,
            )
        )


def _system_utc_now() -> datetime:
    return datetime.now(UTC)


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("decision_time_utc must be timezone-aware")
    return value.astimezone(UTC)


def _same_timeless_content(left: object, right: object) -> bool:
    excluded = {"created_at_utc"}
    left_payload = left.model_dump(mode="python", exclude=excluded)  # type: ignore[attr-defined]
    right_payload = right.model_dump(mode="python", exclude=excluded)  # type: ignore[attr-defined]
    return bool(canonical_json_bytes(left_payload) == canonical_json_bytes(right_payload))


def _check(
    *,
    ordinal: int,
    code: PaperCheckCode,
    status: PaperCheckStatus,
    reason_code: str,
    evidence_sha256s: tuple[str, ...],
    observed_value: str | None = None,
    threshold_value: str | None = None,
) -> PaperSimulationCheck:
    payload = {
        "schema_version": "phase10-local-simulation-check-v1",
        "ordinal": ordinal,
        "code": code,
        "status": status,
        "reason_code": reason_code,
        "observed_value": observed_value,
        "threshold_value": threshold_value,
        "evidence_sha256s": tuple(sorted(set(evidence_sha256s))),
    }
    return PaperSimulationCheck.model_validate(
        {
            **payload,
            "check_sha256": domain_sha256(PHASE10_CHECK_HASH_DOMAIN, payload),
        }
    )


class PaperSimulationWorkflow:
    """Freshly revalidate governance, calculate one local fixture, and persist atomically."""

    def __init__(
        self,
        *,
        evidence: PaperEvidenceGateway,
        simulations: PaperSimulationStore,
        phase10_code_version_git_sha: str | None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.evidence = evidence
        self.simulations = simulations
        self.phase10_code_version_git_sha = phase10_code_version_git_sha
        self.clock = clock or _system_utc_now

    def _require_code_sha(self) -> str:
        try:
            return validate_code_git_sha(self.phase10_code_version_git_sha)
        except ValueError as exc:
            raise PaperEvidenceNotFound("phase10_code_version_git_sha_missing") from exc

    @staticmethod
    def _build_checks(
        *,
        source: ApprovalAssessmentArtifact,
        transition: ApprovalAssessmentArtifact,
        research: ResearchRunArtifact,
        risk_input: ApprovalRiskInput,
        configuration_sha256: str,
        configuration: object,
        code_version_git_sha: str,
        revalidation_proof_sha256: str,
    ) -> tuple[PaperSimulationCheck, ...]:
        from fable5_paper.contracts import PaperSimulationConfiguration

        if not isinstance(configuration, PaperSimulationConfiguration):
            raise TypeError("configuration must be a PaperSimulationConfiguration")
        source_pass = source.outcome is ApprovalAssessmentOutcome.APPROVED_PAPER and all(
            item.status is CheckStatus.PASS for item in source.checks
        )
        transition_same_refs = (
            transition.research_run_id == source.research_run_id
            and transition.approval_policy_version_id == source.approval_policy_version_id
            and transition.approval_scope_version_id == source.approval_scope_version_id
            and transition.human_authorization_evidence_id == source.human_authorization_evidence_id
            and transition.risk_input_id == source.risk_input_id
        )
        transition_pass = (
            transition_same_refs
            and transition.outcome is ApprovalAssessmentOutcome.APPROVED_PAPER
            and all(item.status is CheckStatus.PASS for item in transition.checks)
        )
        specification = research.specification
        research_pass = (
            research.run_id == source.research_run_id
            and research.artifact_sha256 == source.phase6_lineage.research_artifact_sha256
            and research.status is ResearchRunStatus.COMPLETED
            and research.phase5_evaluation.promotion_state is PromotionState.PASS_RESEARCH
            and bool(specification.signal_definition.strip())
            and bool(specification.target_forecast_horizon.strip())
            and bool(specification.required_capabilities)
            and bool(specification.transaction_cost_model_id)
            and bool(specification.slippage_model_id)
            and specification.walk_forward.outer_fold_count >= 2
            and specification.walk_forward.inner_fold_count >= 2
            and bool(specification.risk_limits)
            and len(specification.required_audit_fields) >= 10
        )
        model_ids = {item.model_id for item in research.model_output_sets}
        configuration_pass = (
            research.family is CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING
            and research.configuration_id.value == "phase6-a-pass-v2"
            and configuration.model_id in model_ids
            and configuration.research_specification_sha256 == specification.specification_sha256
            and configuration.available_at_utc <= configuration.decision_time_utc
        )
        risk_computable = (
            risk_input.proposed_notional is not None
            and risk_input.proposed_notional > 0
            and configuration.requested_quantity is not None
        )
        if configuration.requested_quantity is None or risk_input.proposed_notional is None:
            risk_exact = False
        else:
            risk_exact = (
                risk_computable
                and risk_input.universe_id == configuration.mock_universe_id
                and risk_input.proposed_notional == configuration.approved_proposed_notional
                and configuration.requested_quantity * configuration.reference_price
                == risk_input.proposed_notional
            )
        costs_complete = (
            bool(specification.transaction_cost_model_id)
            and bool(specification.slippage_model_id)
            and configuration.source_transaction_cost_model_id
            == specification.transaction_cost_model_id
            and configuration.source_slippage_model_id == specification.slippage_model_id
            and configuration.local_cost_model_id == "phase10-local-transparent-cost-v1"
            and configuration.local_slippage_model_id == "phase10-local-transparent-slippage-v1"
        )
        boundary_pass = (
            configuration.synthetic
            and configuration.local_mock_only
            and configuration.external_routing_absent
            and configuration.live_path_absent
            and configuration.llm_decision_role_absent
        )
        code_evidence = domain_sha256("phase10-code-version-evidence-v1", code_version_git_sha)
        entries = (
            (
                PaperCheckCode.SOURCE_APPROVAL_EXACT,
                PaperCheckStatus.PASS if source_pass else PaperCheckStatus.FAIL,
                "source_approval_exact" if source_pass else "source_approval_not_positive",
                (source.artifact_sha256, source.phase6_lineage.lineage_sha256),
                source.outcome.value,
                ApprovalAssessmentOutcome.APPROVED_PAPER.value,
            ),
            (
                PaperCheckCode.TRANSITION_APPROVAL_FRESH,
                PaperCheckStatus.PASS if transition_pass else PaperCheckStatus.BLOCKED,
                (
                    "transition_approval_fresh"
                    if transition_pass
                    else "transition_approval_not_fresh"
                ),
                (
                    transition.artifact_sha256,
                    transition.currentness_state_sha256,
                    transition.revocation_set_sha256,
                    revalidation_proof_sha256,
                ),
                transition.outcome.value,
                ApprovalAssessmentOutcome.APPROVED_PAPER.value,
            ),
            (
                PaperCheckCode.RESEARCH_PREREQUISITES_COMPLETE,
                PaperCheckStatus.PASS if research_pass else PaperCheckStatus.FAIL,
                (
                    "research_prerequisites_complete"
                    if research_pass
                    else "research_prerequisites_incomplete"
                ),
                (
                    research.artifact_sha256,
                    specification.specification_sha256,
                    research.phase5_evaluation.evaluation_report_sha256
                    or research.phase5_evaluation.policy_sha256,
                ),
                research.phase5_evaluation.promotion_state.value,
                PromotionState.PASS_RESEARCH.value,
            ),
            (
                PaperCheckCode.SIMULATION_CONFIGURATION_EXACT,
                PaperCheckStatus.PASS if configuration_pass else PaperCheckStatus.FAIL,
                (
                    "simulation_configuration_exact"
                    if configuration_pass
                    else "simulation_configuration_ineligible"
                ),
                (configuration_sha256, research.artifact_sha256),
                configuration.configuration_id,
                "phase10-a-local-mock-qa-v1",
            ),
            (
                PaperCheckCode.RISK_CONTEXT_EXACT,
                (
                    PaperCheckStatus.PASS
                    if risk_exact
                    else (
                        PaperCheckStatus.UNCOMPUTABLE
                        if not risk_computable
                        else PaperCheckStatus.FAIL
                    )
                ),
                (
                    "risk_context_exact"
                    if risk_exact
                    else (
                        "risk_context_uncomputable"
                        if not risk_computable
                        else "risk_context_mismatch"
                    )
                ),
                (risk_input.risk_input_sha256, configuration_sha256),
                (
                    "uncomputable"
                    if risk_input.proposed_notional is None
                    else str(risk_input.proposed_notional)
                ),
                (
                    "uncomputable"
                    if configuration.approved_proposed_notional is None
                    else str(configuration.approved_proposed_notional)
                ),
            ),
            (
                PaperCheckCode.COST_SLIPPAGE_COMPLETE,
                PaperCheckStatus.PASS if costs_complete else PaperCheckStatus.FAIL,
                ("cost_slippage_complete" if costs_complete else "cost_slippage_incomplete"),
                (specification.specification_sha256, configuration_sha256),
                (
                    f"{configuration.source_transaction_cost_model_id}:"
                    f"{configuration.source_slippage_model_id}"
                ),
                "complete_source_and_local_models",
            ),
            (
                PaperCheckCode.LOCAL_BOUNDARY_ENFORCED,
                PaperCheckStatus.PASS if boundary_pass else PaperCheckStatus.FAIL,
                ("local_boundary_enforced" if boundary_pass else "local_boundary_violated"),
                (configuration_sha256, code_evidence),
                "local_mock_no_external_routing_no_live_path",
                "local_mock_no_external_routing_no_live_path",
            ),
        )
        return tuple(
            _check(
                ordinal=ordinal,
                code=code,
                status=status,
                reason_code=reason,
                evidence_sha256s=evidence,
                observed_value=observed,
                threshold_value=threshold,
            )
            for ordinal, (code, status, reason, evidence, observed, threshold) in enumerate(
                entries, start=1
            )
        )

    def _create_serialized(
        self,
        request: PaperSimulationCreateRequest,
        simulations: PaperSimulationCreation,
    ) -> PaperSimulationArtifact:
        existing = simulations.find_by_idempotency_key(request.simulation_idempotency_key)
        if existing is not None:
            if existing.source_assessment_id != request.approval_assessment_id:
                raise PaperWorkflowConflict(
                    "simulation idempotency key belongs to another approval assessment"
                )
            return existing
        code_sha = self._require_code_sha()
        decision_time = _utc(self.clock())
        try:
            source = self.evidence.get_assessment(request.approval_assessment_id)
            research = self.evidence.get_research_run(source.research_run_id)
            risk_input = self.evidence.get_risk_input(source.risk_input_id)
            transition = self.evidence.revalidate_assessment(
                source,
                decision_time_utc=decision_time,
                code_version_git_sha=code_sha,
            )
        except (ResearchRunNotFound, RiskArtifactNotFound, ApprovalEvidenceNotFound) as exc:
            raise PaperEvidenceNotFound(
                "required immutable simulation evidence was not found"
            ) from exc
        except (
            ResearchRepositoryConflict,
            RiskRepositoryConflict,
            ApprovalWorkflowConflict,
        ) as exc:
            raise PaperWorkflowConflict("immutable simulation evidence conflicts") from exc
        if (
            source.phase6_lineage.research_run_id != research.run_id
            or source.phase6_lineage.research_artifact_sha256 != research.artifact_sha256
            or risk_input.research_run_id != research.run_id
            or risk_input.research_artifact_sha256 != research.artifact_sha256
        ):
            raise PaperWorkflowConflict("source assessment lost exact research/risk lineage")
        configuration = build_simulation_configuration(
            research=research,
            lineage=source.phase6_lineage,
            risk_input=risk_input,
            decision_time_utc=decision_time,
        )
        revalidation_proof = build_transition_revalidation_proof(
            request=request,
            source_assessment_artifact_sha256=source.artifact_sha256,
            transition_assessment_id=transition.assessment_id,
            transition_assessment_artifact_sha256=transition.artifact_sha256,
            transition_currentness_state_sha256=transition.currentness_state_sha256,
            transition_revocation_set_sha256=transition.revocation_set_sha256,
            decision_time_utc=decision_time,
            phase10_code_version_git_sha=code_sha,
        )
        checks = self._build_checks(
            source=source,
            transition=transition,
            research=research,
            risk_input=risk_input,
            configuration_sha256=configuration.configuration_sha256,
            configuration=configuration,
            code_version_git_sha=code_sha,
            revalidation_proof_sha256=revalidation_proof.revalidation_proof_sha256,
        )
        currentness_sha256 = paper_currentness_sha256(
            source_assessment_sha256=source.artifact_sha256,
            transition_assessment_sha256=transition.artifact_sha256,
            transition_currentness_state_sha256=transition.currentness_state_sha256,
            transition_revocation_set_sha256=transition.revocation_set_sha256,
            revalidation_proof_sha256=revalidation_proof.revalidation_proof_sha256,
        )
        request_fingerprint_sha256 = paper_request_fingerprint(
            request=request,
            source_assessment_sha256=source.artifact_sha256,
            transition_assessment_sha256=transition.artifact_sha256,
            currentness_state_sha256=currentness_sha256,
            revalidation_proof_sha256=revalidation_proof.revalidation_proof_sha256,
            configuration_sha256=configuration.configuration_sha256,
            phase10_code_version_git_sha=code_sha,
        )
        simulation_run_id = identity(PHASE10_RUN_NAMESPACE, request_fingerprint_sha256)
        all_pass = all(item.status is PaperCheckStatus.PASS for item in checks)
        outcome = (
            PaperSimulationOutcome.SIMULATED_COMPLETE
            if all_pass
            else PaperSimulationOutcome.BLOCKED
        )
        ledger_entries = (
            (
                build_simulation_ledger(
                    simulation_run_id=simulation_run_id,
                    configuration=configuration,
                ),
            )
            if all_pass
            else ()
        )
        reason_codes = (
            ("all_simulation_checks_passed",)
            if all_pass
            else tuple(
                sorted(
                    {
                        item.reason_code
                        for item in checks
                        if item.status is not PaperCheckStatus.PASS
                    }
                )
            )
        )
        payload = {
            "artifact_schema_version": "phase10-local-paper-simulation-v1",
            "request_fingerprint_sha256": request_fingerprint_sha256,
            "currentness_state_sha256": currentness_sha256,
            "simulation_idempotency_key": request.simulation_idempotency_key,
            "source_assessment_id": source.assessment_id,
            "source_assessment_artifact_sha256": source.artifact_sha256,
            "transition_assessment_id": transition.assessment_id,
            "transition_assessment_artifact_sha256": transition.artifact_sha256,
            "transition_currentness_state_sha256": transition.currentness_state_sha256,
            "transition_revocation_set_sha256": transition.revocation_set_sha256,
            "transition_revalidation_proof": revalidation_proof,
            "research_run_id": research.run_id,
            "research_artifact_sha256": research.artifact_sha256,
            "phase6_lineage_sha256": source.phase6_lineage.lineage_sha256,
            "approval_policy_version_id": transition.approval_policy_version_id,
            "approval_policy_sha256": transition.approval_policy_sha256,
            "approval_scope_version_id": transition.approval_scope_version_id,
            "approval_scope_sha256": transition.approval_scope_sha256,
            "human_authorization_evidence_id": (transition.human_authorization_evidence_id),
            "authorization_sha256": transition.authorization_sha256,
            "risk_input_id": transition.risk_input_id,
            "risk_input_sha256": transition.risk_input_sha256,
            "configuration": configuration,
            "checks": checks,
            "ledger_entries": ledger_entries,
            "outcome": outcome,
            "reason_codes": reason_codes,
            "phase10_code_version_git_sha": code_sha,
            "random_seed": configuration.random_seed,
            "raw_trial_count": configuration.raw_trial_count,
            "effective_trial_count": configuration.effective_trial_count,
            "decision_time_utc": decision_time,
            "synthetic": True,
            "simulated_paper_only": True,
            "local_mock_only": True,
            "external_submission": False,
            "external_routing_absent": True,
            "live_path_absent": True,
            "no_personalized_investment_advice": True,
            "no_real_performance_claimed": True,
            "disclaimer": PHASE10_DISCLAIMER,
        }
        candidate = PaperSimulationArtifact.model_validate(
            {
                **payload,
                "simulation_run_id": simulation_run_id,
                "artifact_sha256": domain_sha256(PHASE10_ARTIFACT_HASH_DOMAIN, payload),
                "created_at_utc": decision_time,
            }
        )
        persisted = simulations.create_simulation(candidate)
        if persisted.source_assessment_id != request.approval_assessment_id or (
            persisted.simulation_idempotency_key != request.simulation_idempotency_key
        ):
            raise PaperWorkflowConflict("persisted idempotent simulation changed its request")
        same_identity_changed = (
            persisted.simulation_run_id == candidate.simulation_run_id
            and not _same_timeless_content(persisted, candidate)
        )
        if same_identity_changed:
            raise PaperWorkflowConflict("persisted simulation changed immutable evidence")
        return persisted

    def create_simulation(self, request: PaperSimulationCreateRequest) -> PaperSimulationArtifact:
        with self.simulations.serialized_creation(
            request.simulation_idempotency_key
        ) as simulations:
            return self._create_serialized(request, simulations)

    def get_simulation(self, simulation_run_id: UUID) -> PaperSimulationArtifact:
        return self.simulations.get_simulation(simulation_run_id)

    def get_simulation_evidence_bundle(
        self,
        simulation_run_id: UUID,
    ) -> LocalSimulationEvidenceBundle:
        simulation = self.simulations.get_simulation(simulation_run_id)
        try:
            return build_local_simulation_evidence_bundle(simulation)
        except (AttributeError, TypeError, ValueError, ValidationError) as exc:
            raise PaperWorkflowConflict(
                "persisted Phase 10 simulation cannot be projected as Phase 11 evidence"
            ) from exc

    def list_simulations(
        self,
        *,
        source_assessment_id: UUID | None,
        limit: int,
    ) -> list[PaperSimulationSummary]:
        return self.simulations.list_simulations(
            source_assessment_id=source_assessment_id,
            limit=limit,
        )


__all__ = [
    "PaperEvidenceGateway",
    "PaperEvidenceNotFound",
    "PaperSimulationCreation",
    "PaperSimulationStore",
    "PaperSimulationWorkflow",
    "PaperWorkflowConflict",
    "PostgresPaperEvidenceGateway",
]
