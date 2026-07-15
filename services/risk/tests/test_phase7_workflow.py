from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fable5_backtester.contracts import PromotionState
from fable5_mapping.models import CanonicalFamily
from fable5_risk.contracts import (
    APPROVAL_CHECK_ORDER,
    ApprovalAssessmentArtifact,
    ApprovalAssessmentCreateRequest,
    ApprovalAssessmentEvidenceTimeline,
    ApprovalAssessmentOutcome,
    ApprovalAssessmentSummary,
    ApprovalCheckCode,
    ApprovalRevocationCreateRequest,
    ApprovalRiskInput,
    AuthorizationRevocationArtifact,
    AuthorizationRevocationSummary,
    CheckStatus,
    Phase6ApprovalLineage,
)
from fable5_risk.fixtures import (
    DEFAULT_REVOCATION_EVIDENCE_PROFILE,
    SYNTHETIC_ASSESSMENT_TIME_UTC,
    SYNTHETIC_PHASE7_CODE_VERSION_GIT_SHA,
    ApprovalEvidenceBundle,
    build_approval_policy,
    build_approval_risk_input,
    build_approval_scope,
    build_breach_evidence_bundle,
    build_conflicting_evidence_bundle,
    build_expired_evidence_bundle,
    build_human_authorization,
    build_nominal_evidence_bundle,
    build_stale_evidence_bundle,
    build_synthetic_phase6_lineage,
    build_uncomputable_evidence_bundle,
)
from fable5_risk.workflow import (
    ApprovalEvidenceNotFound,
    ApprovalWorkflow,
    ApprovalWorkflowConflict,
)
from pydantic import ValidationError


class MemoryResearchStore:
    def __init__(self, *lineages: Phase6ApprovalLineage) -> None:
        self.lineages = {item.research_run_id: item for item in lineages}

    def get_approval_lineage(self, research_run_id: UUID) -> Phase6ApprovalLineage:
        try:
            return self.lineages[research_run_id]
        except KeyError as exc:
            raise ApprovalEvidenceNotFound("research run not found") from exc


class MemoryRiskStore:
    def __init__(self, *bundles: ApprovalEvidenceBundle) -> None:
        self.policies = {item.policy.approval_policy_version_id: item.policy for item in bundles}
        self.scopes = {item.scope.approval_scope_version_id: item.scope for item in bundles}
        self.authorizations = {
            item.authorization.human_authorization_evidence_id: item.authorization
            for item in bundles
        }
        self.risk_inputs = {item.risk_input.risk_input_id: item.risk_input for item in bundles}
        self.assessments: dict[UUID, ApprovalAssessmentArtifact] = {}
        self.revocations: dict[UUID, AuthorizationRevocationArtifact] = {}

    def get_approval_policy(self, approval_policy_version_id: UUID):
        try:
            return self.policies[approval_policy_version_id]
        except KeyError as exc:
            raise ApprovalEvidenceNotFound("policy not found") from exc

    def get_approval_scope(self, approval_scope_version_id: UUID):
        try:
            return self.scopes[approval_scope_version_id]
        except KeyError as exc:
            raise ApprovalEvidenceNotFound("scope not found") from exc

    def get_human_authorization_evidence(self, human_authorization_evidence_id: UUID):
        try:
            return self.authorizations[human_authorization_evidence_id]
        except KeyError as exc:
            raise ApprovalEvidenceNotFound("authorization not found") from exc

    def get_risk_input(self, risk_input_id: UUID) -> ApprovalRiskInput:
        try:
            return self.risk_inputs[risk_input_id]
        except KeyError as exc:
            raise ApprovalEvidenceNotFound("risk input not found") from exc

    def find_authorization_revocations(
        self, human_authorization_evidence_id: UUID
    ) -> list[AuthorizationRevocationArtifact]:
        return [
            item
            for item in self.revocations.values()
            if item.human_authorization_evidence_id == human_authorization_evidence_id
        ]

    def create_assessment(self, artifact: ApprovalAssessmentArtifact) -> ApprovalAssessmentArtifact:
        return self.assessments.setdefault(artifact.assessment_id, artifact)

    def get_assessment(self, assessment_id: UUID) -> ApprovalAssessmentArtifact:
        return self.assessments[assessment_id]

    def list_assessments(self, *, limit: int) -> list[ApprovalAssessmentSummary]:
        return [
            ApprovalAssessmentSummary(
                assessment_id=item.assessment_id,
                artifact_sha256=item.artifact_sha256,
                research_run_id=item.research_run_id,
                research_configuration_id=item.phase6_lineage.research_configuration_id,
                outcome=item.outcome,
                reason_codes=item.reason_codes,
                created_at_utc=item.created_at_utc,
            )
            for item in list(self.assessments.values())[:limit]
        ]

    def create_revocation(
        self, artifact: AuthorizationRevocationArtifact
    ) -> AuthorizationRevocationArtifact:
        return self.revocations.setdefault(artifact.revocation_id, artifact)

    def get_revocation(self, revocation_id: UUID) -> AuthorizationRevocationArtifact:
        return self.revocations[revocation_id]

    def list_revocations(
        self,
        *,
        human_authorization_evidence_id: UUID | None,
        limit: int,
    ) -> list[AuthorizationRevocationSummary]:
        values = [
            item
            for item in self.revocations.values()
            if human_authorization_evidence_id is None
            or item.human_authorization_evidence_id == human_authorization_evidence_id
        ]
        return [
            AuthorizationRevocationSummary(
                revocation_id=item.revocation_id,
                artifact_sha256=item.artifact_sha256,
                human_authorization_evidence_id=item.human_authorization_evidence_id,
                revocation_evidence_id=item.revocation_evidence_id,
                effective_at_utc=item.effective_at_utc,
                created_at_utc=item.created_at_utc,
            )
            for item in values[:limit]
        ]


def _request(lineage: Phase6ApprovalLineage, bundle: ApprovalEvidenceBundle):
    return ApprovalAssessmentCreateRequest(
        research_run_id=lineage.research_run_id,
        approval_policy_version_id=bundle.policy.approval_policy_version_id,
        approval_scope_version_id=bundle.scope.approval_scope_version_id,
        human_authorization_evidence_id=(bundle.authorization.human_authorization_evidence_id),
        risk_input_id=bundle.risk_input.risk_input_id,
    )


def _workflow(
    lineage: Phase6ApprovalLineage,
    bundle: ApprovalEvidenceBundle,
    *,
    assessment_time=SYNTHETIC_ASSESSMENT_TIME_UTC,
) -> tuple[ApprovalWorkflow, MemoryRiskStore]:
    store = MemoryRiskStore(bundle)
    workflow = ApprovalWorkflow(
        research_store=MemoryResearchStore(lineage),
        risk_store=store,
        assessment_time_utc=assessment_time,
        phase7_code_version_git_sha=SYNTHETIC_PHASE7_CODE_VERSION_GIT_SHA,
    )
    return workflow, store


def _check(artifact: ApprovalAssessmentArtifact, code: ApprovalCheckCode):
    return next(item for item in artifact.checks if item.code is code)


def test_request_contract_accepts_exactly_five_references() -> None:
    fields = set(ApprovalAssessmentCreateRequest.model_fields)
    assert fields == {
        "research_run_id",
        "approval_policy_version_id",
        "approval_scope_version_id",
        "human_authorization_evidence_id",
        "risk_input_id",
    }
    with pytest.raises(ValidationError):
        ApprovalAssessmentCreateRequest(
            research_run_id=uuid4(),
            approval_policy_version_id=uuid4(),
            approval_scope_version_id=uuid4(),
            human_authorization_evidence_id=uuid4(),
            risk_input_id=uuid4(),
            outcome="APPROVED_PAPER",  # type: ignore[call-arg]
        )


def test_policy_fixtures_can_model_independent_immutable_versions() -> None:
    first = build_approval_policy(policy_id="phase7-policy-a", policy_version=1)
    second = build_approval_policy(policy_id="phase7-policy-b", policy_version=2)

    assert first.policy_id == "phase7-policy-a"
    assert first.policy_version == 1
    assert second.policy_id == "phase7-policy-b"
    assert second.policy_version == 2
    assert first.approval_policy_version_id != second.approval_policy_version_id


def test_nominal_path_requires_all_exact_checks_and_remains_non_executable() -> None:
    lineage = build_synthetic_phase6_lineage()
    bundle = build_nominal_evidence_bundle(lineage)
    workflow, _ = _workflow(lineage, bundle)

    artifact = workflow.create_assessment(_request(lineage, bundle))

    assert artifact.outcome is ApprovalAssessmentOutcome.APPROVED_PAPER
    assert tuple(item.code for item in artifact.checks) == APPROVAL_CHECK_ORDER
    assert all(item.status is CheckStatus.PASS for item in artifact.checks)
    assert artifact.synthetic is True
    assert artifact.simulated_paper_only is True
    assert artifact.execution_authorized is False
    assert artifact.execution_ready is False
    assert artifact.no_personalized_investment_advice is True
    assert artifact.no_real_performance_claimed is True


def test_evidence_bundle_timestamps_follow_supplied_assessment_time() -> None:
    lineage = build_synthetic_phase6_lineage()
    assessment_time = SYNTHETIC_ASSESSMENT_TIME_UTC + timedelta(days=30, minutes=17)

    assert build_nominal_evidence_bundle(lineage) == build_nominal_evidence_bundle(
        lineage,
        assessment_time_utc=SYNTHETIC_ASSESSMENT_TIME_UTC,
    )

    bundle = build_nominal_evidence_bundle(
        lineage,
        assessment_time_utc=assessment_time,
    )

    assert bundle.policy.valid_from_utc == assessment_time - timedelta(days=7)
    assert bundle.policy.expires_at_utc == assessment_time + timedelta(days=7)
    assert bundle.scope.valid_from_utc == assessment_time - timedelta(days=2)
    assert bundle.scope.expires_at_utc == assessment_time + timedelta(days=2)
    assert bundle.authorization.authorized_at_utc == assessment_time - timedelta(hours=1)
    assert bundle.authorization.review_at_utc == assessment_time + timedelta(hours=12)
    assert bundle.authorization.expires_at_utc == assessment_time + timedelta(days=1)
    assert bundle.risk_input.observed_at_utc == assessment_time - timedelta(minutes=5)


@pytest.mark.parametrize(
    ("builder", "check_code", "expected_status"),
    (
        (
            build_expired_evidence_bundle,
            ApprovalCheckCode.AUTHORIZATION_CURRENT,
            CheckStatus.BLOCKED,
        ),
        (build_stale_evidence_bundle, ApprovalCheckCode.RISK_INPUT_FRESH, CheckStatus.BLOCKED),
        (
            build_uncomputable_evidence_bundle,
            ApprovalCheckCode.NOTIONAL_LIMIT,
            CheckStatus.UNCOMPUTABLE,
        ),
        (build_breach_evidence_bundle, ApprovalCheckCode.NOTIONAL_LIMIT, CheckStatus.FAIL),
    ),
)
def test_scenario_bundles_remain_targeted_at_supplied_assessment_time(
    builder: Callable[..., ApprovalEvidenceBundle],
    check_code: ApprovalCheckCode,
    expected_status: CheckStatus,
) -> None:
    lineage = build_synthetic_phase6_lineage()
    assessment_time = SYNTHETIC_ASSESSMENT_TIME_UTC + timedelta(days=30, minutes=17)
    bundle = builder(lineage, assessment_time_utc=assessment_time)
    workflow, _ = _workflow(lineage, bundle, assessment_time=assessment_time)

    artifact = workflow.create_assessment(_request(lineage, bundle))

    assert artifact.outcome is ApprovalAssessmentOutcome.FAIL_REJECT
    assert _check(artifact, check_code).status is expected_status
    if builder in {build_uncomputable_evidence_bundle, build_breach_evidence_bundle}:
        assert _check(artifact, ApprovalCheckCode.RISK_INPUT_FRESH).status is CheckStatus.PASS


@pytest.mark.parametrize(
    ("configuration_id", "promotion_state", "family"),
    [
        (
            "phase6-a-fail-cost-v2",
            PromotionState.FAIL_REJECT,
            CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING,
        ),
        (
            "phase6-b-pass-v2",
            PromotionState.FAIL_REJECT,
            CanonicalFamily.B_TIME_SERIES_MOMENTUM_REGIME,
        ),
        (
            "phase6-b-fail-crash-v2",
            PromotionState.FAIL_REJECT,
            CanonicalFamily.B_TIME_SERIES_MOMENTUM_REGIME,
        ),
        (
            "phase6-c-pass-v2",
            PromotionState.FAIL_REJECT,
            CanonicalFamily.C_OFFICIAL_EVENT_TEXT_OVERLAY,
        ),
    ],
)
def test_configuration_identity_never_overrides_phase6_promotion_state(
    configuration_id: str,
    promotion_state: PromotionState,
    family: CanonicalFamily,
) -> None:
    lineage = build_synthetic_phase6_lineage(
        configuration_id=configuration_id,
        promotion_state=promotion_state,
        family=family,
    )
    bundle = build_nominal_evidence_bundle(lineage)
    workflow, _ = _workflow(lineage, bundle)

    artifact = workflow.create_assessment(_request(lineage, bundle))

    assert artifact.outcome is ApprovalAssessmentOutcome.FAIL_REJECT
    assert _check(artifact, ApprovalCheckCode.RESEARCH_PASS).status is CheckStatus.FAIL


def test_missing_phase6_or_independent_evidence_fails_closed() -> None:
    lineage = build_synthetic_phase6_lineage()
    bundle = build_nominal_evidence_bundle(lineage)
    store = MemoryRiskStore(bundle)
    workflow = ApprovalWorkflow(
        research_store=MemoryResearchStore(),
        risk_store=store,
        assessment_time_utc=SYNTHETIC_ASSESSMENT_TIME_UTC,
        phase7_code_version_git_sha=SYNTHETIC_PHASE7_CODE_VERSION_GIT_SHA,
    )
    with pytest.raises(ApprovalEvidenceNotFound):
        workflow.create_assessment(_request(lineage, bundle))

    del store.authorizations[bundle.authorization.human_authorization_evidence_id]
    workflow = ApprovalWorkflow(
        research_store=MemoryResearchStore(lineage),
        risk_store=store,
        assessment_time_utc=SYNTHETIC_ASSESSMENT_TIME_UTC,
        phase7_code_version_git_sha=SYNTHETIC_PHASE7_CODE_VERSION_GIT_SHA,
    )
    with pytest.raises(ApprovalEvidenceNotFound):
        workflow.create_assessment(_request(lineage, bundle))


def test_assessment_evidence_timeline_resolves_exact_hash_bound_timestamps() -> None:
    lineage = build_synthetic_phase6_lineage()
    bundle = build_nominal_evidence_bundle(lineage)
    workflow, store = _workflow(lineage, bundle)
    assessment = workflow.create_assessment(_request(lineage, bundle))

    def unexpected_clock() -> datetime:
        raise AssertionError("timeline reads must not reassess currentness")

    read_workflow = ApprovalWorkflow(
        research_store=MemoryResearchStore(lineage),
        risk_store=store,
        clock=unexpected_clock,
        phase7_code_version_git_sha=SYNTHETIC_PHASE7_CODE_VERSION_GIT_SHA,
    )
    timeline = read_workflow.get_assessment_evidence_timeline(assessment.assessment_id)

    assert isinstance(timeline, ApprovalAssessmentEvidenceTimeline)
    assert timeline.assessment_id == assessment.assessment_id
    assert timeline.assessment_created_at_utc == assessment.created_at_utc
    assert timeline.policy.approval_policy_version_id == assessment.approval_policy_version_id
    assert timeline.policy.policy_sha256 == assessment.approval_policy_sha256
    assert timeline.policy.valid_from_utc == bundle.policy.valid_from_utc
    assert timeline.policy.expires_at_utc == bundle.policy.expires_at_utc
    assert timeline.scope.approval_scope_version_id == assessment.approval_scope_version_id
    assert timeline.scope.scope_sha256 == assessment.approval_scope_sha256
    assert timeline.scope.valid_from_utc == bundle.scope.valid_from_utc
    assert timeline.scope.expires_at_utc == bundle.scope.expires_at_utc
    assert (
        timeline.authorization.human_authorization_evidence_id
        == assessment.human_authorization_evidence_id
    )
    assert timeline.authorization.authorization_sha256 == assessment.authorization_sha256
    assert timeline.authorization.authorized_at_utc == bundle.authorization.authorized_at_utc
    assert timeline.authorization.review_at_utc == bundle.authorization.review_at_utc
    assert timeline.authorization.expires_at_utc == bundle.authorization.expires_at_utc
    assert timeline.risk_input.risk_input_id == assessment.risk_input_id
    assert timeline.risk_input.risk_input_sha256 == assessment.risk_input_sha256
    assert timeline.risk_input.observed_at_utc == bundle.risk_input.observed_at_utc


@pytest.mark.parametrize(
    ("store_attribute", "bundle_attribute", "assessment_id_attribute"),
    (
        ("policies", "policy", "approval_policy_version_id"),
        ("scopes", "scope", "approval_scope_version_id"),
        ("authorizations", "authorization", "human_authorization_evidence_id"),
        ("risk_inputs", "risk_input", "risk_input_id"),
    ),
)
def test_assessment_evidence_timeline_fails_closed_on_each_missing_reference(
    store_attribute: str,
    bundle_attribute: str,
    assessment_id_attribute: str,
) -> None:
    lineage = build_synthetic_phase6_lineage()
    bundle = build_nominal_evidence_bundle(lineage)
    workflow, store = _workflow(lineage, bundle)
    assessment = workflow.create_assessment(_request(lineage, bundle))

    evidence = getattr(bundle, bundle_attribute)
    evidence_id = getattr(assessment, assessment_id_attribute)
    assert getattr(evidence, assessment_id_attribute) == evidence_id
    del getattr(store, store_attribute)[evidence_id]

    with pytest.raises(ApprovalEvidenceNotFound):
        workflow.get_assessment_evidence_timeline(assessment.assessment_id)


@pytest.mark.parametrize(
    (
        "store_attribute",
        "bundle_attribute",
        "assessment_id_attribute",
        "hash_attribute",
    ),
    (
        ("policies", "policy", "approval_policy_version_id", "policy_sha256"),
        ("scopes", "scope", "approval_scope_version_id", "scope_sha256"),
        (
            "authorizations",
            "authorization",
            "human_authorization_evidence_id",
            "authorization_sha256",
        ),
        ("risk_inputs", "risk_input", "risk_input_id", "risk_input_sha256"),
    ),
)
def test_assessment_evidence_timeline_rejects_each_invalid_canonical_hash(
    store_attribute: str,
    bundle_attribute: str,
    assessment_id_attribute: str,
    hash_attribute: str,
) -> None:
    lineage = build_synthetic_phase6_lineage()
    bundle = build_nominal_evidence_bundle(lineage)
    workflow, store = _workflow(lineage, bundle)
    assessment = workflow.create_assessment(_request(lineage, bundle))

    evidence = getattr(bundle, bundle_attribute)
    evidence_id = getattr(assessment, assessment_id_attribute)
    invalid_payload = evidence.model_dump(mode="python")
    invalid_payload[hash_attribute] = "0" * 64
    getattr(store, store_attribute)[evidence_id] = type(evidence).model_construct(**invalid_payload)

    with pytest.raises(ApprovalWorkflowConflict, match="timeline evidence is invalid"):
        workflow.get_assessment_evidence_timeline(assessment.assessment_id)


@pytest.mark.parametrize("evidence_kind", ("policy", "scope", "authorization", "risk_input"))
def test_assessment_evidence_timeline_rejects_each_wrong_identity_and_hash(
    evidence_kind: str,
) -> None:
    lineage = build_synthetic_phase6_lineage()
    bundle = build_nominal_evidence_bundle(lineage)
    workflow, store = _workflow(lineage, bundle)
    assessment = workflow.create_assessment(_request(lineage, bundle))

    if evidence_kind == "policy":
        store.policies[assessment.approval_policy_version_id] = build_approval_policy(
            policy_id="phase7-conflicting-timeline-policy"
        )
    elif evidence_kind == "scope":
        store.scopes[assessment.approval_scope_version_id] = build_approval_scope(
            lineage,
            bundle.policy,
            scope_id="phase7-conflicting-timeline-scope",
        )
    elif evidence_kind == "authorization":
        store.authorizations[assessment.human_authorization_evidence_id] = (
            build_human_authorization(
                lineage,
                bundle.policy,
                bundle.scope,
                authorized_at_utc=bundle.authorization.authorized_at_utc - timedelta(minutes=1),
            )
        )
    else:
        store.risk_inputs[assessment.risk_input_id] = build_approval_risk_input(
            lineage,
            bundle.policy,
            bundle.scope,
            observed_at_utc=bundle.risk_input.observed_at_utc - timedelta(minutes=1),
        )

    with pytest.raises(
        ApprovalWorkflowConflict,
        match="timeline evidence conflicts with persisted references",
    ):
        workflow.get_assessment_evidence_timeline(assessment.assessment_id)


@pytest.mark.parametrize("evidence_kind", ("scope", "authorization", "risk_input"))
def test_assessment_evidence_timeline_rejects_each_cross_lineage_reference(
    evidence_kind: str,
) -> None:
    lineage = build_synthetic_phase6_lineage()
    other_lineage = build_synthetic_phase6_lineage(
        configuration_id="phase6-cross-lineage-timeline-evidence"
    )
    bundle = build_nominal_evidence_bundle(lineage)
    workflow, store = _workflow(lineage, bundle)
    assessment = workflow.create_assessment(_request(lineage, bundle))

    if evidence_kind == "scope":
        store.scopes[assessment.approval_scope_version_id] = build_approval_scope(
            other_lineage,
            bundle.policy,
            scope_id="phase7-cross-lineage-timeline-scope",
        )
    elif evidence_kind == "authorization":
        store.authorizations[assessment.human_authorization_evidence_id] = (
            build_human_authorization(
                other_lineage,
                bundle.policy,
                bundle.scope,
            )
        )
    else:
        store.risk_inputs[assessment.risk_input_id] = build_approval_risk_input(
            other_lineage,
            bundle.policy,
            bundle.scope,
        )

    with pytest.raises(
        ApprovalWorkflowConflict,
        match="timeline evidence conflicts with persisted references",
    ):
        workflow.get_assessment_evidence_timeline(assessment.assessment_id)


def test_missing_server_git_sha_fails_closed_without_persisting() -> None:
    lineage = build_synthetic_phase6_lineage()
    bundle = build_nominal_evidence_bundle(lineage)
    store = MemoryRiskStore(bundle)
    workflow = ApprovalWorkflow(
        research_store=MemoryResearchStore(lineage),
        risk_store=store,
        assessment_time_utc=SYNTHETIC_ASSESSMENT_TIME_UTC,
        phase7_code_version_git_sha=None,
    )

    with pytest.raises(ApprovalEvidenceNotFound, match="phase7_code_version_git_sha_missing"):
        workflow.create_assessment(_request(lineage, bundle))
    assert not store.assessments


def test_resolved_blocked_phase6_lineage_still_fails_closed() -> None:
    lineage = build_synthetic_phase6_lineage(
        configuration_id="phase6-c-fail-corroboration-v2",
        promotion_state=PromotionState.BLOCKED_MISSING_POLICY,
        family=CanonicalFamily.C_OFFICIAL_EVENT_TEXT_OVERLAY,
    )
    bundle = build_nominal_evidence_bundle(lineage)
    workflow, _ = _workflow(lineage, bundle)

    artifact = workflow.create_assessment(_request(lineage, bundle))

    assert artifact.outcome is ApprovalAssessmentOutcome.FAIL_REJECT
    assert _check(artifact, ApprovalCheckCode.RESEARCH_PASS).status is CheckStatus.BLOCKED
    assert _check(artifact, ApprovalCheckCode.PHASE6_LINEAGE_COMPLETE).status is CheckStatus.BLOCKED


def test_conflicting_evidence_persists_fail_reject() -> None:
    lineage = build_synthetic_phase6_lineage()
    bundle = build_conflicting_evidence_bundle(lineage)
    workflow, store = _workflow(lineage, bundle)

    artifact = workflow.create_assessment(_request(lineage, bundle))

    assert artifact.outcome is ApprovalAssessmentOutcome.FAIL_REJECT
    assert _check(artifact, ApprovalCheckCode.SCOPE_MATCH).status is CheckStatus.FAIL
    assert store.assessments[artifact.assessment_id] == artifact


def test_expired_and_age_stale_authorization_fail_closed() -> None:
    lineage = build_synthetic_phase6_lineage()
    expired = build_expired_evidence_bundle(lineage)
    workflow, _ = _workflow(lineage, expired)
    artifact = workflow.create_assessment(_request(lineage, expired))
    assert artifact.outcome is ApprovalAssessmentOutcome.FAIL_REJECT
    assert _check(artifact, ApprovalCheckCode.AUTHORIZATION_CURRENT).status is CheckStatus.BLOCKED

    policy = build_approval_policy(authorization_max_age_seconds=3600)
    scope = build_approval_scope(lineage, policy)
    authorization = build_human_authorization(
        lineage,
        policy,
        scope,
        authorized_at_utc=SYNTHETIC_ASSESSMENT_TIME_UTC - timedelta(hours=2),
        review_at_utc=SYNTHETIC_ASSESSMENT_TIME_UTC + timedelta(hours=1),
        expires_at_utc=SYNTHETIC_ASSESSMENT_TIME_UTC + timedelta(hours=2),
    )
    risk_input = build_approval_risk_input(lineage, policy, scope)
    stale_auth = ApprovalEvidenceBundle(policy, scope, authorization, risk_input)
    workflow, _ = _workflow(lineage, stale_auth)
    artifact = workflow.create_assessment(_request(lineage, stale_auth))
    assert _check(artifact, ApprovalCheckCode.AUTHORIZATION_CURRENT).status is CheckStatus.BLOCKED


def test_stale_uncomputable_and_breached_risk_inputs_are_distinct_failures() -> None:
    lineage = build_synthetic_phase6_lineage()
    cases = (
        (
            build_stale_evidence_bundle(lineage),
            ApprovalCheckCode.RISK_INPUT_FRESH,
            CheckStatus.BLOCKED,
        ),
        (
            build_uncomputable_evidence_bundle(lineage),
            ApprovalCheckCode.NOTIONAL_LIMIT,
            CheckStatus.UNCOMPUTABLE,
        ),
        (
            build_breach_evidence_bundle(lineage),
            ApprovalCheckCode.NOTIONAL_LIMIT,
            CheckStatus.FAIL,
        ),
    )
    for bundle, code, status in cases:
        workflow, _ = _workflow(lineage, bundle)
        artifact = workflow.create_assessment(_request(lineage, bundle))
        assert artifact.outcome is ApprovalAssessmentOutcome.FAIL_REJECT
        assert _check(artifact, code).status is status


def test_revocation_is_server_resolved_and_invalidates_authorization() -> None:
    lineage = build_synthetic_phase6_lineage()
    bundle = build_nominal_evidence_bundle(lineage)
    workflow, store = _workflow(lineage, bundle)
    revocation_request = ApprovalRevocationCreateRequest(
        human_authorization_evidence_id=bundle.authorization.human_authorization_evidence_id,
        revocation_evidence_id=DEFAULT_REVOCATION_EVIDENCE_PROFILE.revocation_evidence_id,
    )

    revocation = workflow.create_revocation(revocation_request)
    repeated = workflow.create_revocation(revocation_request)
    artifact = workflow.create_assessment(_request(lineage, bundle))

    assert repeated.revocation_id == revocation.revocation_id
    assert len(store.revocations) == 1
    assert artifact.outcome is ApprovalAssessmentOutcome.FAIL_REJECT
    assert _check(artifact, ApprovalCheckCode.REVOCATION_CLEAR).status is CheckStatus.BLOCKED
    assert artifact.revocation_ids == (revocation.revocation_id,)

    with pytest.raises(ApprovalEvidenceNotFound):
        workflow.create_revocation(
            ApprovalRevocationCreateRequest(
                human_authorization_evidence_id=bundle.authorization.human_authorization_evidence_id,
                revocation_evidence_id=uuid4(),
            )
        )


def test_identity_is_deterministic_within_same_currentness_state_not_wall_clock() -> None:
    lineage = build_synthetic_phase6_lineage()
    bundle = build_nominal_evidence_bundle(lineage)
    workflow, store = _workflow(lineage, bundle)
    request = _request(lineage, bundle)
    first = workflow.create_assessment(request)
    later_workflow = ApprovalWorkflow(
        research_store=MemoryResearchStore(lineage),
        risk_store=store,
        assessment_time_utc=SYNTHETIC_ASSESSMENT_TIME_UTC + timedelta(minutes=1),
        phase7_code_version_git_sha=SYNTHETIC_PHASE7_CODE_VERSION_GIT_SHA,
    )

    repeated = later_workflow.create_assessment(request)

    assert repeated.assessment_id == first.assessment_id
    assert repeated.artifact_sha256 == first.artifact_sha256
    assert len(store.assessments) == 1


def test_currentness_transition_changes_identity_and_fails_closed() -> None:
    lineage = build_synthetic_phase6_lineage()
    bundle = build_nominal_evidence_bundle(lineage)
    workflow, store = _workflow(lineage, bundle)
    request = _request(lineage, bundle)
    current = workflow.create_assessment(request)
    expired_workflow = ApprovalWorkflow(
        research_store=MemoryResearchStore(lineage),
        risk_store=store,
        assessment_time_utc=SYNTHETIC_ASSESSMENT_TIME_UTC + timedelta(days=3),
        phase7_code_version_git_sha=SYNTHETIC_PHASE7_CODE_VERSION_GIT_SHA,
    )

    expired = expired_workflow.create_assessment(request)

    assert current.outcome is ApprovalAssessmentOutcome.APPROVED_PAPER
    assert expired.outcome is ApprovalAssessmentOutcome.FAIL_REJECT
    assert expired.assessment_id != current.assessment_id
    assert expired.currentness_state_sha256 != current.currentness_state_sha256


def test_dynamic_clock_workflow_rechecks_currentness_once_per_create() -> None:
    lineage = build_synthetic_phase6_lineage()
    bundle = build_nominal_evidence_bundle(lineage)
    store = MemoryRiskStore(bundle)
    request = _request(lineage, bundle)
    instants = iter(
        (
            SYNTHETIC_ASSESSMENT_TIME_UTC,
            SYNTHETIC_ASSESSMENT_TIME_UTC + timedelta(minutes=1),
            SYNTHETIC_ASSESSMENT_TIME_UTC + timedelta(days=3),
        )
    )
    captured: list[datetime] = []

    def advancing_clock() -> datetime:
        instant = next(instants)
        captured.append(instant)
        return instant

    workflow = ApprovalWorkflow(
        research_store=MemoryResearchStore(lineage),
        risk_store=store,
        clock=advancing_clock,
        phase7_code_version_git_sha=SYNTHETIC_PHASE7_CODE_VERSION_GIT_SHA,
    )

    current = workflow.create_assessment(request)
    same_state = workflow.create_assessment(request)
    expired = workflow.create_assessment(request)

    assert captured == [
        SYNTHETIC_ASSESSMENT_TIME_UTC,
        SYNTHETIC_ASSESSMENT_TIME_UTC + timedelta(minutes=1),
        SYNTHETIC_ASSESSMENT_TIME_UTC + timedelta(days=3),
    ]
    assert current.outcome is ApprovalAssessmentOutcome.APPROVED_PAPER
    assert same_state.assessment_id == current.assessment_id
    assert same_state.artifact_sha256 == current.artifact_sha256
    assert expired.outcome is ApprovalAssessmentOutcome.FAIL_REJECT
    assert expired.assessment_id != current.assessment_id
    assert expired.currentness_state_sha256 != current.currentness_state_sha256
    assert _check(expired, ApprovalCheckCode.SCOPE_CURRENT).status is CheckStatus.BLOCKED
    assert _check(expired, ApprovalCheckCode.AUTHORIZATION_CURRENT).status is CheckStatus.BLOCKED
    assert _check(expired, ApprovalCheckCode.RISK_INPUT_FRESH).status is CheckStatus.BLOCKED
    assert expired.created_at_utc == SYNTHETIC_ASSESSMENT_TIME_UTC + timedelta(days=3)


def test_complete_lineage_carries_all_required_phase6_audit_anchors() -> None:
    lineage = build_synthetic_phase6_lineage()

    assert lineage.research_run_id
    assert lineage.research_artifact_sha256
    assert lineage.research_request_fingerprint_sha256
    assert lineage.research_configuration_sha256
    assert lineage.mapping_id and lineage.mapping_input_sha256
    assert lineage.specification_sha256
    assert lineage.research_pipeline_input_sha256
    assert lineage.feature_lineage_sha256
    assert lineage.snapshot_bundle_sha256 and lineage.snapshot_bindings
    assert lineage.source_reproduction_audit_sha256
    assert lineage.phase5_policy_sha256 and lineage.phase5_fixture_sha256
    assert lineage.evaluation_report_sha256 and lineage.phase5_trial_set_sha256
    assert lineage.code_version_git_sha
    assert lineage.raw_trial_count == 6
    assert lineage.effective_trial_count == Decimal("4")
