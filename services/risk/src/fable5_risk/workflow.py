"""Fail-closed Phase 7 approval and pre-order risk orchestration."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from fable5_backtester.contracts import GateCode, PromotionState
from fable5_data.canonical import canonical_json_bytes
from fable5_research.contracts import ResearchRunArtifact
from pydantic import ValidationError

from fable5_risk.canonical import (
    PHASE7_ASSESSMENT_ARTIFACT_HASH_DOMAIN,
    PHASE7_ASSESSMENT_NAMESPACE,
    PHASE7_CHECK_HASH_DOMAIN,
    PHASE7_CURRENTNESS_HASH_DOMAIN,
    PHASE7_REVOCATION_ARTIFACT_HASH_DOMAIN,
    PHASE7_REVOCATION_NAMESPACE,
    PHASE7_REVOCATION_SET_HASH_DOMAIN,
    domain_sha256,
    identity,
)
from fable5_risk.contracts import (
    APPROVAL_CHECK_ORDER,
    PHASE7_ASSESSMENT_SCHEMA_VERSION,
    PHASE7_REVOCATION_SCHEMA_VERSION,
    ApprovalAssessmentArtifact,
    ApprovalAssessmentCreateRequest,
    ApprovalAssessmentEvidenceTimeline,
    ApprovalAssessmentOutcome,
    ApprovalAssessmentSummary,
    ApprovalCheckCode,
    ApprovalCheckResult,
    ApprovalPolicy,
    ApprovalPolicyTimelineEvidence,
    ApprovalRevocationCreateRequest,
    ApprovalRiskInput,
    ApprovalRiskInputTimelineEvidence,
    ApprovalScope,
    ApprovalScopeTimelineEvidence,
    AuthorizationRevocationArtifact,
    AuthorizationRevocationSummary,
    CheckStatus,
    HumanAuthorizationEvidence,
    HumanAuthorizationTimelineEvidence,
    Phase6ApprovalLineage,
    assessment_request_fingerprint,
    revocation_request_fingerprint,
)
from fable5_risk.fixtures import (
    phase6_lineage_from_research_artifact,
    resolve_revocation_evidence,
)


class ApprovalEvidenceNotFound(LookupError):
    """A referenced immutable research, policy, authorization, or risk artifact is absent."""


class ApprovalWorkflowConflict(RuntimeError):
    """Persisted Phase 7 evidence conflicts with the deterministic candidate."""


def _system_utc_now() -> datetime:
    return datetime.now(UTC)


class ResearchStore(Protocol):
    def get_approval_lineage(self, research_run_id: UUID) -> Phase6ApprovalLineage: ...


class ResearchArtifactStore(Protocol):
    def get_run(self, run_id: UUID) -> ResearchRunArtifact: ...


class Phase6ResearchStoreAdapter:
    """Adapt the existing immutable Phase 6 repository to approval-lineage reads."""

    def __init__(self, repository: ResearchArtifactStore) -> None:
        self.repository = repository

    def get_approval_lineage(self, research_run_id: UUID) -> Phase6ApprovalLineage:
        return phase6_lineage_from_research_artifact(self.repository.get_run(research_run_id))


class RiskStore(Protocol):
    def get_approval_policy(self, approval_policy_version_id: UUID) -> ApprovalPolicy: ...

    def get_approval_scope(self, approval_scope_version_id: UUID) -> ApprovalScope: ...

    def get_human_authorization_evidence(
        self, human_authorization_evidence_id: UUID
    ) -> HumanAuthorizationEvidence: ...

    def get_risk_input(self, risk_input_id: UUID) -> ApprovalRiskInput: ...

    def find_authorization_revocations(
        self, human_authorization_evidence_id: UUID
    ) -> list[AuthorizationRevocationArtifact]: ...

    def create_assessment(
        self, artifact: ApprovalAssessmentArtifact
    ) -> ApprovalAssessmentArtifact: ...

    def get_assessment(self, assessment_id: UUID) -> ApprovalAssessmentArtifact: ...

    def list_assessments(self, *, limit: int) -> list[ApprovalAssessmentSummary]: ...

    def create_revocation(
        self, artifact: AuthorizationRevocationArtifact
    ) -> AuthorizationRevocationArtifact: ...

    def get_revocation(self, revocation_id: UUID) -> AuthorizationRevocationArtifact: ...

    def list_revocations(
        self,
        *,
        human_authorization_evidence_id: UUID | None,
        limit: int,
    ) -> list[AuthorizationRevocationSummary]: ...


def _utc(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value.astimezone(UTC)


def _same_timeless_content(left: object, right: object) -> bool:
    excluded = {"created_at_utc"}
    left_payload = left.model_dump(mode="python", exclude=excluded)  # type: ignore[attr-defined]
    right_payload = right.model_dump(mode="python", exclude=excluded)  # type: ignore[attr-defined]
    return bool(canonical_json_bytes(left_payload) == canonical_json_bytes(right_payload))


def _check(
    *,
    code: ApprovalCheckCode,
    status: CheckStatus,
    reason_code: str,
    evidence_sha256s: tuple[str, ...],
    observed_value: str | None = None,
    threshold_value: str | None = None,
) -> ApprovalCheckResult:
    ordinal = APPROVAL_CHECK_ORDER.index(code) + 1
    evidence = tuple(sorted(set(evidence_sha256s)))
    payload = {
        "ordinal": ordinal,
        "code": code,
        "status": status,
        "reason_code": reason_code,
        "observed_value": observed_value,
        "threshold_value": threshold_value,
        "evidence_sha256s": evidence,
    }
    return ApprovalCheckResult.model_validate(
        {
            "check_sha256": domain_sha256(PHASE7_CHECK_HASH_DOMAIN, payload),
            **payload,
        }
    )


def _boolean_check(
    *,
    code: ApprovalCheckCode,
    value: bool | None,
    evidence_sha256s: tuple[str, ...],
) -> ApprovalCheckResult:
    if value is None:
        return _check(
            code=code,
            status=CheckStatus.UNCOMPUTABLE,
            reason_code=f"{code.value.lower()}_uncomputable",
            observed_value="missing",
            threshold_value="true",
            evidence_sha256s=evidence_sha256s,
        )
    return _check(
        code=code,
        status=CheckStatus.PASS if value else CheckStatus.FAIL,
        reason_code=(f"{code.value.lower()}_verified" if value else f"{code.value.lower()}_failed"),
        observed_value=str(value).lower(),
        threshold_value="true",
        evidence_sha256s=evidence_sha256s,
    )


def _maximum_check(
    *,
    code: ApprovalCheckCode,
    value: Decimal | None,
    maximum: Decimal,
    evidence_sha256s: tuple[str, ...],
    absolute: bool = False,
) -> ApprovalCheckResult:
    if value is None:
        return _check(
            code=code,
            status=CheckStatus.UNCOMPUTABLE,
            reason_code=f"{code.value.lower()}_uncomputable",
            observed_value="missing",
            threshold_value=str(maximum),
            evidence_sha256s=evidence_sha256s,
        )
    evaluated = abs(value) if absolute else value
    passed = evaluated <= maximum
    return _check(
        code=code,
        status=CheckStatus.PASS if passed else CheckStatus.FAIL,
        reason_code=f"{code.value.lower()}_{'verified' if passed else 'breached'}",
        observed_value=str(evaluated),
        threshold_value=str(maximum),
        evidence_sha256s=evidence_sha256s,
    )


def _minimum_check(
    *,
    code: ApprovalCheckCode,
    value: Decimal | None,
    minimum: Decimal,
    evidence_sha256s: tuple[str, ...],
) -> ApprovalCheckResult:
    if value is None:
        return _check(
            code=code,
            status=CheckStatus.UNCOMPUTABLE,
            reason_code=f"{code.value.lower()}_uncomputable",
            observed_value="missing",
            threshold_value=str(minimum),
            evidence_sha256s=evidence_sha256s,
        )
    passed = value >= minimum
    return _check(
        code=code,
        status=CheckStatus.PASS if passed else CheckStatus.FAIL,
        reason_code=f"{code.value.lower()}_{'verified' if passed else 'breached'}",
        observed_value=str(value),
        threshold_value=str(minimum),
        evidence_sha256s=evidence_sha256s,
    )


def _lineage_is_complete(lineage: Phase6ApprovalLineage) -> bool:
    try:
        validated = Phase6ApprovalLineage.model_validate(lineage.model_dump(mode="python"))
    except (AttributeError, TypeError, ValueError, ValidationError):
        return False
    return (
        validated.research_status == "completed"
        and validated.evaluation_report_id is not None
        and validated.evaluation_report_sha256 is not None
        and validated.phase5_trial_set_sha256 is not None
        and validated.gate_codes == tuple(GateCode)
        and bool(validated.snapshot_bindings)
    )


class ApprovalWorkflow:
    """Resolve immutable evidence, evaluate every gate, and persist one audit artifact."""

    def __init__(
        self,
        *,
        research_store: ResearchStore,
        risk_store: RiskStore,
        assessment_time_utc: datetime | None = None,
        clock: Callable[[], datetime] | None = None,
        phase7_code_version_git_sha: str | None,
    ) -> None:
        self.research_store = research_store
        self.risk_store = risk_store
        self._fixed_assessment_time_utc = (
            None
            if assessment_time_utc is None
            else _utc(assessment_time_utc, "assessment_time_utc")
        )
        self._clock = clock or _system_utc_now
        if phase7_code_version_git_sha is not None and (
            len(phase7_code_version_git_sha) != 40
            or any(character not in "0123456789abcdef" for character in phase7_code_version_git_sha)
        ):
            raise ValueError("phase7_code_version_git_sha must be a lowercase 40-character git SHA")
        self.phase7_code_version_git_sha = phase7_code_version_git_sha

    def _capture_assessment_time_utc(self) -> datetime:
        if self._fixed_assessment_time_utc is not None:
            return self._fixed_assessment_time_utc
        return _utc(self._clock(), "assessment_time_utc")

    def _require_code_version_git_sha(self) -> str:
        if self.phase7_code_version_git_sha is None:
            raise ApprovalEvidenceNotFound("phase7_code_version_git_sha_missing")
        return self.phase7_code_version_git_sha

    def _resolve_assessment_evidence(
        self, request: ApprovalAssessmentCreateRequest
    ) -> tuple[
        Phase6ApprovalLineage,
        ApprovalPolicy,
        ApprovalScope,
        HumanAuthorizationEvidence,
        ApprovalRiskInput,
        list[AuthorizationRevocationArtifact],
    ]:
        try:
            lineage = self.research_store.get_approval_lineage(request.research_run_id)
            policy = self.risk_store.get_approval_policy(request.approval_policy_version_id)
            scope = self.risk_store.get_approval_scope(request.approval_scope_version_id)
            authorization = self.risk_store.get_human_authorization_evidence(
                request.human_authorization_evidence_id
            )
            risk_input = self.risk_store.get_risk_input(request.risk_input_id)
            revocations = self.risk_store.find_authorization_revocations(
                request.human_authorization_evidence_id
            )
        except ApprovalEvidenceNotFound:
            raise
        except LookupError as exc:
            raise ApprovalEvidenceNotFound("required Phase 7 evidence is missing") from exc
        return lineage, policy, scope, authorization, risk_input, revocations

    def _build_checks(
        self,
        *,
        assessment_time_utc: datetime,
        request: ApprovalAssessmentCreateRequest,
        lineage: Phase6ApprovalLineage,
        policy: ApprovalPolicy,
        scope: ApprovalScope,
        authorization: HumanAuthorizationEvidence,
        risk_input: ApprovalRiskInput,
        revocations: list[AuthorizationRevocationArtifact],
    ) -> tuple[ApprovalCheckResult, ...]:
        now = assessment_time_utc
        lineage_hash = lineage.lineage_sha256
        policy_hash = policy.policy_sha256
        scope_hash = scope.scope_sha256
        authorization_hash = authorization.authorization_sha256
        risk_hash = risk_input.risk_input_sha256
        active_revocations = tuple(item for item in revocations if item.effective_at_utc <= now)

        research_pass = (
            lineage.research_status == "completed"
            and lineage.promotion_state is PromotionState.PASS_RESEARCH
        )
        research_status = (
            CheckStatus.PASS
            if research_pass
            else (CheckStatus.BLOCKED if lineage.research_status == "blocked" else CheckStatus.FAIL)
        )
        lineage_complete = _lineage_is_complete(lineage)
        policy_current = policy.valid_from_utc <= now < policy.expires_at_utc
        policy_match = (
            policy.approval_policy_version_id == request.approval_policy_version_id
            and scope.approval_policy_version_id == policy.approval_policy_version_id
            and authorization.approval_policy_version_id == policy.approval_policy_version_id
            and risk_input.approval_policy_version_id == policy.approval_policy_version_id
        )
        scope_current = scope.valid_from_utc <= now < scope.expires_at_utc
        scope_match = (
            scope.approval_scope_version_id == request.approval_scope_version_id
            and scope.research_run_id == lineage.research_run_id == request.research_run_id
            and scope.research_artifact_sha256 == lineage.research_artifact_sha256
            and authorization.approval_scope_version_id == scope.approval_scope_version_id
            and risk_input.approval_scope_version_id == scope.approval_scope_version_id
            and risk_input.research_run_id == lineage.research_run_id
            and risk_input.research_artifact_sha256 == lineage.research_artifact_sha256
            and risk_input.universe_id in scope.permitted_universe_ids
        )
        authorization_age_seconds = Decimal(
            str((now - authorization.authorized_at_utc).total_seconds())
        )
        authorization_current = (
            authorization.authorized_at_utc <= now < authorization.review_at_utc
            and now < authorization.expires_at_utc
            and authorization_age_seconds >= 0
            and authorization_age_seconds <= policy.authorization_max_age_seconds
        )
        authorization_match = (
            authorization.human_authorization_evidence_id == request.human_authorization_evidence_id
            and authorization.research_run_id == lineage.research_run_id
            and authorization.research_artifact_sha256 == lineage.research_artifact_sha256
            and authorization.approval_policy_version_id == policy.approval_policy_version_id
            and authorization.approval_scope_version_id == scope.approval_scope_version_id
            and authorization.human_controlled
            and authorization.authorized_role == "paper_risk_reviewer"
        )
        risk_age_seconds = Decimal(str((now - risk_input.observed_at_utc).total_seconds()))
        risk_fresh = (
            risk_input.risk_input_id == request.risk_input_id
            and risk_age_seconds >= 0
            and risk_age_seconds <= policy.risk_input_max_age_seconds
        )

        checks = [
            _check(
                code=ApprovalCheckCode.RESEARCH_PASS,
                status=research_status,
                reason_code=(
                    "phase6_pass_research_verified"
                    if research_pass
                    else "phase6_research_not_eligible"
                ),
                observed_value=lineage.promotion_state.value,
                threshold_value=PromotionState.PASS_RESEARCH.value,
                evidence_sha256s=(lineage_hash,),
            ),
            _check(
                code=ApprovalCheckCode.PHASE6_LINEAGE_COMPLETE,
                status=CheckStatus.PASS if lineage_complete else CheckStatus.BLOCKED,
                reason_code=(
                    "phase6_lineage_complete_verified"
                    if lineage_complete
                    else "phase6_lineage_incomplete"
                ),
                observed_value=str(lineage_complete).lower(),
                threshold_value="true",
                evidence_sha256s=(lineage_hash,),
            ),
            _check(
                code=ApprovalCheckCode.POLICY_CURRENT,
                status=CheckStatus.PASS if policy_current else CheckStatus.BLOCKED,
                reason_code="approval_policy_current_verified"
                if policy_current
                else "approval_policy_not_current",
                observed_value=str(policy_current).lower(),
                threshold_value="true",
                evidence_sha256s=(policy_hash,),
            ),
            _check(
                code=ApprovalCheckCode.POLICY_MATCH,
                status=CheckStatus.PASS if policy_match else CheckStatus.FAIL,
                reason_code="approval_policy_match_verified"
                if policy_match
                else "approval_policy_mismatch",
                observed_value=str(policy_match).lower(),
                threshold_value="true",
                evidence_sha256s=(policy_hash, scope_hash, authorization_hash, risk_hash),
            ),
            _check(
                code=ApprovalCheckCode.SCOPE_CURRENT,
                status=CheckStatus.PASS if scope_current else CheckStatus.BLOCKED,
                reason_code="approval_scope_current_verified"
                if scope_current
                else "approval_scope_not_current",
                observed_value=str(scope_current).lower(),
                threshold_value="true",
                evidence_sha256s=(scope_hash,),
            ),
            _check(
                code=ApprovalCheckCode.SCOPE_MATCH,
                status=CheckStatus.PASS if scope_match else CheckStatus.FAIL,
                reason_code="approval_scope_match_verified"
                if scope_match
                else "approval_scope_mismatch",
                observed_value=str(scope_match).lower(),
                threshold_value="true",
                evidence_sha256s=(lineage_hash, scope_hash, authorization_hash, risk_hash),
            ),
            _check(
                code=ApprovalCheckCode.AUTHORIZATION_CURRENT,
                status=CheckStatus.PASS if authorization_current else CheckStatus.BLOCKED,
                reason_code="human_authorization_current_verified"
                if authorization_current
                else "human_authorization_not_current",
                observed_value=str(authorization_current).lower(),
                threshold_value=str(policy.authorization_max_age_seconds),
                evidence_sha256s=(authorization_hash, policy_hash),
            ),
            _check(
                code=ApprovalCheckCode.AUTHORIZATION_MATCH,
                status=CheckStatus.PASS if authorization_match else CheckStatus.FAIL,
                reason_code="human_authorization_match_verified"
                if authorization_match
                else "human_authorization_mismatch",
                observed_value=str(authorization_match).lower(),
                threshold_value="true",
                evidence_sha256s=(lineage_hash, policy_hash, scope_hash, authorization_hash),
            ),
            _check(
                code=ApprovalCheckCode.REVOCATION_CLEAR,
                status=CheckStatus.PASS if not active_revocations else CheckStatus.BLOCKED,
                reason_code="authorization_revocation_clear_verified"
                if not active_revocations
                else "authorization_revoked",
                observed_value=str(len(active_revocations)),
                threshold_value="0",
                evidence_sha256s=(
                    (authorization_hash,)
                    if not revocations
                    else tuple(item.artifact_sha256 for item in revocations)
                ),
            ),
            _check(
                code=ApprovalCheckCode.RISK_INPUT_FRESH,
                status=CheckStatus.PASS if risk_fresh else CheckStatus.BLOCKED,
                reason_code="risk_input_fresh_verified" if risk_fresh else "risk_input_stale",
                observed_value=(
                    "fresh" if risk_fresh else ("future" if risk_age_seconds < 0 else "stale")
                ),
                threshold_value=str(policy.risk_input_max_age_seconds),
                evidence_sha256s=(policy_hash, risk_hash),
            ),
            _boolean_check(
                code=ApprovalCheckCode.GLOBAL_CONTROL_CLEAR,
                value=risk_input.global_control_clear,
                evidence_sha256s=(risk_hash,),
            ),
            _boolean_check(
                code=ApprovalCheckCode.STRATEGY_CONTROL_CLEAR,
                value=risk_input.strategy_control_clear,
                evidence_sha256s=(risk_hash,),
            ),
            _boolean_check(
                code=ApprovalCheckCode.DATA_QUALITY_CONTROL_CLEAR,
                value=risk_input.data_quality_control_clear,
                evidence_sha256s=(risk_hash,),
            ),
            _boolean_check(
                code=ApprovalCheckCode.MARKET_CALENDAR_OPEN,
                value=risk_input.market_calendar_open,
                evidence_sha256s=(risk_hash,),
            ),
            _boolean_check(
                code=ApprovalCheckCode.DUPLICATE_CONTEXT_CLEAR,
                value=risk_input.duplicate_context_clear,
                evidence_sha256s=(risk_hash,),
            ),
            _maximum_check(
                code=ApprovalCheckCode.NOTIONAL_LIMIT,
                value=risk_input.proposed_notional,
                maximum=min(policy.max_notional, scope.max_notional),
                evidence_sha256s=(policy_hash, scope_hash, risk_hash),
            ),
            _maximum_check(
                code=ApprovalCheckCode.GROSS_EXPOSURE_LIMIT,
                value=risk_input.gross_exposure,
                maximum=policy.max_gross_exposure,
                evidence_sha256s=(policy_hash, risk_hash),
            ),
            _maximum_check(
                code=ApprovalCheckCode.NET_EXPOSURE_LIMIT,
                value=risk_input.net_exposure,
                maximum=policy.max_abs_net_exposure,
                evidence_sha256s=(policy_hash, risk_hash),
                absolute=True,
            ),
            _maximum_check(
                code=ApprovalCheckCode.SECTOR_EXPOSURE_LIMIT,
                value=risk_input.sector_exposure,
                maximum=policy.max_sector_exposure,
                evidence_sha256s=(policy_hash, risk_hash),
            ),
            _maximum_check(
                code=ApprovalCheckCode.CONCENTRATION_LIMIT,
                value=risk_input.concentration,
                maximum=policy.max_concentration,
                evidence_sha256s=(policy_hash, risk_hash),
            ),
            _minimum_check(
                code=ApprovalCheckCode.LIQUIDITY_MINIMUM,
                value=risk_input.available_liquidity,
                minimum=policy.min_liquidity,
                evidence_sha256s=(policy_hash, risk_hash),
            ),
            _maximum_check(
                code=ApprovalCheckCode.TURNOVER_LIMIT,
                value=risk_input.turnover,
                maximum=policy.max_turnover,
                evidence_sha256s=(policy_hash, risk_hash),
            ),
            _maximum_check(
                code=ApprovalCheckCode.VOLATILITY_LIMIT,
                value=risk_input.volatility,
                maximum=policy.max_volatility,
                evidence_sha256s=(policy_hash, risk_hash),
            ),
            _maximum_check(
                code=ApprovalCheckCode.DAILY_LOSS_LIMIT,
                value=risk_input.daily_loss,
                maximum=policy.max_daily_loss,
                evidence_sha256s=(policy_hash, risk_hash),
            ),
            _maximum_check(
                code=ApprovalCheckCode.DRAWDOWN_LIMIT,
                value=risk_input.drawdown,
                maximum=policy.max_drawdown,
                evidence_sha256s=(policy_hash, risk_hash),
            ),
        ]
        return tuple(checks)

    def create_assessment(
        self, request: ApprovalAssessmentCreateRequest
    ) -> ApprovalAssessmentArtifact:
        assessment_time_utc = self._capture_assessment_time_utc()
        code_version_git_sha = self._require_code_version_git_sha()
        lineage, policy, scope, authorization, risk_input, revocations = (
            self._resolve_assessment_evidence(request)
        )
        checks = self._build_checks(
            assessment_time_utc=assessment_time_utc,
            request=request,
            lineage=lineage,
            policy=policy,
            scope=scope,
            authorization=authorization,
            risk_input=risk_input,
            revocations=revocations,
        )
        revocations = sorted(revocations, key=lambda item: str(item.revocation_id))
        revocation_set_sha256 = domain_sha256(
            PHASE7_REVOCATION_SET_HASH_DOMAIN,
            tuple(
                {
                    "revocation_id": item.revocation_id,
                    "artifact_sha256": item.artifact_sha256,
                    "effective_at_utc": item.effective_at_utc,
                }
                for item in revocations
            ),
        )
        currentness_codes = {
            ApprovalCheckCode.RESEARCH_PASS,
            ApprovalCheckCode.PHASE6_LINEAGE_COMPLETE,
            ApprovalCheckCode.POLICY_CURRENT,
            ApprovalCheckCode.POLICY_MATCH,
            ApprovalCheckCode.SCOPE_CURRENT,
            ApprovalCheckCode.SCOPE_MATCH,
            ApprovalCheckCode.AUTHORIZATION_CURRENT,
            ApprovalCheckCode.AUTHORIZATION_MATCH,
            ApprovalCheckCode.REVOCATION_CLEAR,
            ApprovalCheckCode.RISK_INPUT_FRESH,
        }
        currentness_state_sha256 = domain_sha256(
            PHASE7_CURRENTNESS_HASH_DOMAIN,
            {
                "lineage_sha256": lineage.lineage_sha256,
                "policy_sha256": policy.policy_sha256,
                "scope_sha256": scope.scope_sha256,
                "authorization_sha256": authorization.authorization_sha256,
                "risk_input_sha256": risk_input.risk_input_sha256,
                "revocation_set_sha256": revocation_set_sha256,
                "states": tuple(
                    {"code": item.code, "status": item.status}
                    for item in checks
                    if item.code in currentness_codes
                ),
            },
        )
        request_fingerprint_sha256 = assessment_request_fingerprint(
            request=request,
            lineage_sha256=lineage.lineage_sha256,
            policy_sha256=policy.policy_sha256,
            scope_sha256=scope.scope_sha256,
            authorization_sha256=authorization.authorization_sha256,
            risk_input_sha256=risk_input.risk_input_sha256,
            revocation_set_sha256=revocation_set_sha256,
            currentness_state_sha256=currentness_state_sha256,
            phase7_code_version_git_sha=code_version_git_sha,
        )
        assessment_id = identity(PHASE7_ASSESSMENT_NAMESPACE, request_fingerprint_sha256)
        all_pass = all(item.status is CheckStatus.PASS for item in checks)
        outcome = (
            ApprovalAssessmentOutcome.APPROVED_PAPER
            if all_pass
            else ApprovalAssessmentOutcome.FAIL_REJECT
        )
        reason_codes = (
            ("all_approval_and_risk_checks_passed",)
            if all_pass
            else tuple(
                sorted({item.reason_code for item in checks if item.status is not CheckStatus.PASS})
            )
        )
        payload = {
            "artifact_schema_version": PHASE7_ASSESSMENT_SCHEMA_VERSION,
            "request_fingerprint_sha256": request_fingerprint_sha256,
            "currentness_state_sha256": currentness_state_sha256,
            "revocation_set_sha256": revocation_set_sha256,
            "research_run_id": request.research_run_id,
            "approval_policy_version_id": request.approval_policy_version_id,
            "approval_scope_version_id": request.approval_scope_version_id,
            "human_authorization_evidence_id": request.human_authorization_evidence_id,
            "risk_input_id": request.risk_input_id,
            "phase6_lineage": lineage,
            "approval_policy_sha256": policy.policy_sha256,
            "approval_scope_sha256": scope.scope_sha256,
            "authorization_sha256": authorization.authorization_sha256,
            "risk_input_sha256": risk_input.risk_input_sha256,
            "revocation_ids": tuple(item.revocation_id for item in revocations),
            "checks": checks,
            "outcome": outcome,
            "reason_codes": reason_codes,
            "phase7_code_version_git_sha": code_version_git_sha,
            "synthetic": True,
            "simulated_paper_only": True,
            "execution_authorized": False,
            "execution_ready": False,
            "no_personalized_investment_advice": True,
            "no_real_performance_claimed": True,
            "disclaimer": (
                "Synthetic simulated-paper governance evidence only; no order, execution "
                "readiness, real performance claim, or investment advice."
            ),
        }
        candidate = ApprovalAssessmentArtifact.model_validate(
            {
                "assessment_id": assessment_id,
                "artifact_sha256": domain_sha256(PHASE7_ASSESSMENT_ARTIFACT_HASH_DOMAIN, payload),
                "created_at_utc": assessment_time_utc,
                **payload,
            }
        )
        persisted = self.risk_store.create_assessment(candidate)
        if not _same_timeless_content(persisted, candidate):
            raise ApprovalWorkflowConflict(
                "persisted approval assessment changed immutable evidence"
            )
        return persisted

    def get_assessment(self, assessment_id: UUID) -> ApprovalAssessmentArtifact:
        return self.risk_store.get_assessment(assessment_id)

    def get_assessment_evidence_timeline(
        self,
        assessment_id: UUID,
    ) -> ApprovalAssessmentEvidenceTimeline:
        try:
            assessment = self.risk_store.get_assessment(assessment_id)
            policy = self.risk_store.get_approval_policy(assessment.approval_policy_version_id)
            scope = self.risk_store.get_approval_scope(assessment.approval_scope_version_id)
            authorization = self.risk_store.get_human_authorization_evidence(
                assessment.human_authorization_evidence_id
            )
            risk_input = self.risk_store.get_risk_input(assessment.risk_input_id)
        except ApprovalEvidenceNotFound:
            raise
        except LookupError as exc:
            raise ApprovalEvidenceNotFound(
                "required Phase 7 assessment timeline evidence is missing"
            ) from exc

        try:
            assessment = ApprovalAssessmentArtifact.model_validate(
                assessment.model_dump(mode="python")
            )
            policy = ApprovalPolicy.model_validate(policy.model_dump(mode="python"))
            scope = ApprovalScope.model_validate(scope.model_dump(mode="python"))
            authorization = HumanAuthorizationEvidence.model_validate(
                authorization.model_dump(mode="python")
            )
            risk_input = ApprovalRiskInput.model_validate(risk_input.model_dump(mode="python"))
        except (AttributeError, TypeError, ValueError, ValidationError) as exc:
            raise ApprovalWorkflowConflict(
                "persisted Phase 7 assessment timeline evidence is invalid"
            ) from exc

        exact_references_match = (
            assessment.assessment_id == assessment_id
            and assessment.research_run_id == assessment.phase6_lineage.research_run_id
            and policy.approval_policy_version_id == assessment.approval_policy_version_id
            and policy.policy_sha256 == assessment.approval_policy_sha256
            and scope.approval_scope_version_id == assessment.approval_scope_version_id
            and scope.scope_sha256 == assessment.approval_scope_sha256
            and scope.research_run_id == assessment.research_run_id
            and scope.research_artifact_sha256 == assessment.phase6_lineage.research_artifact_sha256
            and scope.approval_policy_version_id == assessment.approval_policy_version_id
            and authorization.human_authorization_evidence_id
            == assessment.human_authorization_evidence_id
            and authorization.authorization_sha256 == assessment.authorization_sha256
            and authorization.research_run_id == assessment.research_run_id
            and authorization.research_artifact_sha256
            == assessment.phase6_lineage.research_artifact_sha256
            and authorization.approval_policy_version_id == assessment.approval_policy_version_id
            and authorization.approval_scope_version_id == assessment.approval_scope_version_id
            and risk_input.risk_input_id == assessment.risk_input_id
            and risk_input.risk_input_sha256 == assessment.risk_input_sha256
            and risk_input.research_run_id == assessment.research_run_id
            and risk_input.research_artifact_sha256
            == assessment.phase6_lineage.research_artifact_sha256
            and risk_input.approval_policy_version_id == assessment.approval_policy_version_id
            and risk_input.approval_scope_version_id == assessment.approval_scope_version_id
        )
        if not exact_references_match:
            raise ApprovalWorkflowConflict(
                "assessment timeline evidence conflicts with persisted references"
            )

        return ApprovalAssessmentEvidenceTimeline(
            assessment_id=assessment.assessment_id,
            assessment_created_at_utc=assessment.created_at_utc,
            policy=ApprovalPolicyTimelineEvidence(
                approval_policy_version_id=policy.approval_policy_version_id,
                policy_sha256=policy.policy_sha256,
                valid_from_utc=policy.valid_from_utc,
                expires_at_utc=policy.expires_at_utc,
            ),
            scope=ApprovalScopeTimelineEvidence(
                approval_scope_version_id=scope.approval_scope_version_id,
                scope_sha256=scope.scope_sha256,
                valid_from_utc=scope.valid_from_utc,
                expires_at_utc=scope.expires_at_utc,
            ),
            authorization=HumanAuthorizationTimelineEvidence(
                human_authorization_evidence_id=authorization.human_authorization_evidence_id,
                authorization_sha256=authorization.authorization_sha256,
                authorized_at_utc=authorization.authorized_at_utc,
                review_at_utc=authorization.review_at_utc,
                expires_at_utc=authorization.expires_at_utc,
            ),
            risk_input=ApprovalRiskInputTimelineEvidence(
                risk_input_id=risk_input.risk_input_id,
                risk_input_sha256=risk_input.risk_input_sha256,
                observed_at_utc=risk_input.observed_at_utc,
            ),
        )

    def list_assessments(self, *, limit: int) -> list[ApprovalAssessmentSummary]:
        return self.risk_store.list_assessments(limit=limit)

    def create_revocation(
        self, request: ApprovalRevocationCreateRequest
    ) -> AuthorizationRevocationArtifact:
        assessment_time_utc = self._capture_assessment_time_utc()
        code_version_git_sha = self._require_code_version_git_sha()
        try:
            authorization = self.risk_store.get_human_authorization_evidence(
                request.human_authorization_evidence_id
            )
            revocation_evidence = resolve_revocation_evidence(request.revocation_evidence_id)
        except ApprovalEvidenceNotFound:
            raise
        except LookupError as exc:
            raise ApprovalEvidenceNotFound("required revocation evidence is missing") from exc
        if authorization.human_authorization_evidence_id != request.human_authorization_evidence_id:
            raise ApprovalWorkflowConflict("authorization evidence identity conflicts")
        if revocation_evidence.effective_at_utc > assessment_time_utc:
            raise ApprovalWorkflowConflict("revocation evidence is not yet effective")
        request_fingerprint_sha256 = revocation_request_fingerprint(
            request=request,
            authorization_sha256=authorization.authorization_sha256,
            revocation_evidence_sha256=revocation_evidence.revocation_evidence_sha256,
            phase7_code_version_git_sha=code_version_git_sha,
        )
        payload = {
            "artifact_schema_version": PHASE7_REVOCATION_SCHEMA_VERSION,
            "request_fingerprint_sha256": request_fingerprint_sha256,
            "human_authorization_evidence_id": authorization.human_authorization_evidence_id,
            "authorization_sha256": authorization.authorization_sha256,
            "revocation_evidence_id": revocation_evidence.revocation_evidence_id,
            "revocation_evidence_sha256": revocation_evidence.revocation_evidence_sha256,
            "revoked_by": revocation_evidence.revoked_by,
            "reason": revocation_evidence.reason,
            "effective_at_utc": revocation_evidence.effective_at_utc,
            "phase7_code_version_git_sha": code_version_git_sha,
            "synthetic": True,
            "simulated_paper_only": True,
            "execution_authorized": False,
            "execution_ready": False,
            "no_personalized_investment_advice": True,
            "no_real_performance_claimed": True,
        }
        candidate = AuthorizationRevocationArtifact.model_validate(
            {
                "revocation_id": identity(PHASE7_REVOCATION_NAMESPACE, request_fingerprint_sha256),
                "artifact_sha256": domain_sha256(PHASE7_REVOCATION_ARTIFACT_HASH_DOMAIN, payload),
                "created_at_utc": assessment_time_utc,
                **payload,
            }
        )
        persisted = self.risk_store.create_revocation(candidate)
        if not _same_timeless_content(persisted, candidate):
            raise ApprovalWorkflowConflict("persisted authorization revocation changed evidence")
        return persisted

    def get_revocation(self, revocation_id: UUID) -> AuthorizationRevocationArtifact:
        return self.risk_store.get_revocation(revocation_id)

    def list_revocations(
        self,
        *,
        human_authorization_evidence_id: UUID | None,
        limit: int,
    ) -> list[AuthorizationRevocationSummary]:
        return self.risk_store.list_revocations(
            human_authorization_evidence_id=human_authorization_evidence_id,
            limit=limit,
        )


__all__ = [
    "ApprovalEvidenceNotFound",
    "ApprovalWorkflow",
    "ApprovalWorkflowConflict",
    "Phase6ResearchStoreAdapter",
    "ResearchArtifactStore",
    "ResearchStore",
    "RiskStore",
]
