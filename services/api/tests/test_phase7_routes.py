from __future__ import annotations

from unittest.mock import MagicMock
from uuid import UUID

import fable5_api.approvals as approvals_module
import pytest
from fable5_api.approvals import (
    approval_validation_error_handler,
    assessment_router,
    default_approval_workflow_factory,
    revocation_router,
)
from fable5_api.config import Settings
from fable5_risk.contracts import (
    ApprovalAssessmentArtifact,
    ApprovalAssessmentCreateRequest,
    ApprovalAssessmentEvidenceTimeline,
    ApprovalAssessmentSummary,
    ApprovalRevocationCreateRequest,
    ApprovalRiskInput,
    AuthorizationRevocationArtifact,
    AuthorizationRevocationSummary,
    Phase6ApprovalLineage,
)
from fable5_risk.fixtures import (
    DEFAULT_REVOCATION_EVIDENCE_PROFILE,
    SYNTHETIC_ASSESSMENT_TIME_UTC,
    SYNTHETIC_PHASE7_CODE_VERSION_GIT_SHA,
    ApprovalEvidenceBundle,
    build_nominal_evidence_bundle,
    build_synthetic_phase6_lineage,
)
from fable5_risk.workflow import (
    ApprovalEvidenceNotFound,
    ApprovalWorkflow,
    ApprovalWorkflowConflict,
)
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient

MISSING_ID = UUID("ffffffff-ffff-5fff-8fff-ffffffffffff")


def test_default_workflow_factory_does_not_pin_synthetic_assessment_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    research_repository = object()
    research_store = object()
    risk_store = object()
    workflow = object()
    research_repository_factory = MagicMock(return_value=research_repository)
    research_store_factory = MagicMock(return_value=research_store)
    risk_store_factory = MagicMock(return_value=risk_store)
    workflow_factory = MagicMock(return_value=workflow)
    monkeypatch.setattr(approvals_module, "ResearchRepository", research_repository_factory)
    monkeypatch.setattr(approvals_module, "Phase6ResearchStoreAdapter", research_store_factory)
    monkeypatch.setattr(approvals_module, "RiskRepository", risk_store_factory)
    monkeypatch.setattr(approvals_module, "ApprovalWorkflow", workflow_factory)
    settings = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://phase7-clock-test",
        code_version_git_sha=SYNTHETIC_PHASE7_CODE_VERSION_GIT_SHA,
    )

    created = default_approval_workflow_factory(settings)

    assert created is workflow
    research_repository_factory.assert_called_once_with(settings.database_url)
    research_store_factory.assert_called_once_with(research_repository)
    risk_store_factory.assert_called_once_with(settings.database_url)
    workflow_factory.assert_called_once_with(
        research_store=research_store,
        risk_store=risk_store,
        phase7_code_version_git_sha=SYNTHETIC_PHASE7_CODE_VERSION_GIT_SHA,
    )


class _MemoryResearchStore:
    def __init__(self, lineage: Phase6ApprovalLineage) -> None:
        self.lineage = lineage

    def get_approval_lineage(self, research_run_id: UUID) -> Phase6ApprovalLineage:
        if research_run_id != self.lineage.research_run_id:
            raise ApprovalEvidenceNotFound("research run not found")
        return self.lineage


class _MemoryRiskStore:
    def __init__(self, bundle: ApprovalEvidenceBundle) -> None:
        self.bundle = bundle
        self.assessments: dict[UUID, ApprovalAssessmentArtifact] = {}
        self.revocations: dict[UUID, AuthorizationRevocationArtifact] = {}

    def get_approval_policy(self, approval_policy_version_id: UUID):
        if approval_policy_version_id != self.bundle.policy.approval_policy_version_id:
            raise ApprovalEvidenceNotFound("policy not found")
        return self.bundle.policy

    def get_approval_scope(self, approval_scope_version_id: UUID):
        if approval_scope_version_id != self.bundle.scope.approval_scope_version_id:
            raise ApprovalEvidenceNotFound("scope not found")
        return self.bundle.scope

    def get_human_authorization_evidence(self, human_authorization_evidence_id: UUID):
        if (
            human_authorization_evidence_id
            != self.bundle.authorization.human_authorization_evidence_id
        ):
            raise ApprovalEvidenceNotFound("authorization not found")
        return self.bundle.authorization

    def get_risk_input(self, risk_input_id: UUID) -> ApprovalRiskInput:
        if risk_input_id != self.bundle.risk_input.risk_input_id:
            raise ApprovalEvidenceNotFound("risk input not found")
        return self.bundle.risk_input

    def find_authorization_revocations(
        self,
        human_authorization_evidence_id: UUID,
    ) -> list[AuthorizationRevocationArtifact]:
        return [
            item
            for item in self.revocations.values()
            if item.human_authorization_evidence_id == human_authorization_evidence_id
        ]

    def create_assessment(
        self,
        artifact: ApprovalAssessmentArtifact,
    ) -> ApprovalAssessmentArtifact:
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
        self,
        artifact: AuthorizationRevocationArtifact,
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
        matches = [
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
            for item in matches[:limit]
        ]


def _client(workflow: ApprovalWorkflow) -> TestClient:
    app = FastAPI()
    app.state.approval_workflow = workflow
    app.add_exception_handler(RequestValidationError, approval_validation_error_handler)
    app.include_router(assessment_router)
    app.include_router(revocation_router)
    return TestClient(app)


@pytest.fixture(scope="module")
def phase7_artifacts() -> tuple[
    ApprovalAssessmentCreateRequest,
    ApprovalAssessmentArtifact,
    ApprovalRevocationCreateRequest,
    AuthorizationRevocationArtifact,
]:
    lineage = build_synthetic_phase6_lineage()
    bundle = build_nominal_evidence_bundle(lineage)
    store = _MemoryRiskStore(bundle)
    workflow = ApprovalWorkflow(
        research_store=_MemoryResearchStore(lineage),
        risk_store=store,
        assessment_time_utc=SYNTHETIC_ASSESSMENT_TIME_UTC,
        phase7_code_version_git_sha=SYNTHETIC_PHASE7_CODE_VERSION_GIT_SHA,
    )
    assessment_request = ApprovalAssessmentCreateRequest(
        research_run_id=lineage.research_run_id,
        approval_policy_version_id=bundle.policy.approval_policy_version_id,
        approval_scope_version_id=bundle.scope.approval_scope_version_id,
        human_authorization_evidence_id=(bundle.authorization.human_authorization_evidence_id),
        risk_input_id=bundle.risk_input.risk_input_id,
    )
    assessment = workflow.create_assessment(assessment_request)
    revocation_request = ApprovalRevocationCreateRequest(
        human_authorization_evidence_id=(bundle.authorization.human_authorization_evidence_id),
        revocation_evidence_id=(DEFAULT_REVOCATION_EVIDENCE_PROFILE.revocation_evidence_id),
    )
    revocation = workflow.create_revocation(revocation_request)
    return assessment_request, assessment, revocation_request, revocation


def test_create_routes_accept_only_typed_references_and_return_non_executable_artifacts(
    phase7_artifacts: tuple[
        ApprovalAssessmentCreateRequest,
        ApprovalAssessmentArtifact,
        ApprovalRevocationCreateRequest,
        AuthorizationRevocationArtifact,
    ],
) -> None:
    assessment_request, assessment, revocation_request, revocation = phase7_artifacts
    workflow = MagicMock(spec=ApprovalWorkflow)
    workflow.create_assessment.return_value = assessment
    workflow.create_revocation.return_value = revocation
    client = _client(workflow)

    assessment_response = client.post(
        "/v1/approval-assessments",
        json=assessment_request.model_dump(mode="json"),
    )
    revocation_response = client.post(
        "/v1/approval-revocations",
        json=revocation_request.model_dump(mode="json"),
    )

    assert assessment_response.status_code == 201
    assert revocation_response.status_code == 201
    for body in (assessment_response.json(), revocation_response.json()):
        assert body["synthetic"] is True
        assert body["simulated_paper_only"] is True
        assert body["execution_authorized"] is False
        assert body["execution_ready"] is False
        assert body["no_personalized_investment_advice"] is True
        assert body["no_real_performance_claimed"] is True
    assert assessment_response.json()["outcome"] == "APPROVED_PAPER"
    assert len(assessment_response.json()["checks"]) == 25
    workflow.create_assessment.assert_called_once_with(assessment_request)
    workflow.create_revocation.assert_called_once_with(revocation_request)


def test_read_and_list_routes_delegate_typed_identities_and_filters(
    phase7_artifacts: tuple[
        ApprovalAssessmentCreateRequest,
        ApprovalAssessmentArtifact,
        ApprovalRevocationCreateRequest,
        AuthorizationRevocationArtifact,
    ],
) -> None:
    _, assessment, _, revocation = phase7_artifacts
    bundle = build_nominal_evidence_bundle(assessment.phase6_lineage)
    timeline = ApprovalAssessmentEvidenceTimeline.model_validate(
        {
            "assessment_id": assessment.assessment_id,
            "assessment_created_at_utc": assessment.created_at_utc,
            "policy": {
                "approval_policy_version_id": bundle.policy.approval_policy_version_id,
                "policy_sha256": bundle.policy.policy_sha256,
                "valid_from_utc": bundle.policy.valid_from_utc,
                "expires_at_utc": bundle.policy.expires_at_utc,
            },
            "scope": {
                "approval_scope_version_id": bundle.scope.approval_scope_version_id,
                "scope_sha256": bundle.scope.scope_sha256,
                "valid_from_utc": bundle.scope.valid_from_utc,
                "expires_at_utc": bundle.scope.expires_at_utc,
            },
            "authorization": {
                "human_authorization_evidence_id": (
                    bundle.authorization.human_authorization_evidence_id
                ),
                "authorization_sha256": bundle.authorization.authorization_sha256,
                "authorized_at_utc": bundle.authorization.authorized_at_utc,
                "review_at_utc": bundle.authorization.review_at_utc,
                "expires_at_utc": bundle.authorization.expires_at_utc,
            },
            "risk_input": {
                "risk_input_id": bundle.risk_input.risk_input_id,
                "risk_input_sha256": bundle.risk_input.risk_input_sha256,
                "observed_at_utc": bundle.risk_input.observed_at_utc,
            },
        }
    )
    assessment_summary = ApprovalAssessmentSummary(
        assessment_id=assessment.assessment_id,
        artifact_sha256=assessment.artifact_sha256,
        research_run_id=assessment.research_run_id,
        research_configuration_id=assessment.phase6_lineage.research_configuration_id,
        outcome=assessment.outcome,
        reason_codes=assessment.reason_codes,
        created_at_utc=assessment.created_at_utc,
    )
    revocation_summary = AuthorizationRevocationSummary(
        revocation_id=revocation.revocation_id,
        artifact_sha256=revocation.artifact_sha256,
        human_authorization_evidence_id=revocation.human_authorization_evidence_id,
        revocation_evidence_id=revocation.revocation_evidence_id,
        effective_at_utc=revocation.effective_at_utc,
        created_at_utc=revocation.created_at_utc,
    )
    workflow = MagicMock(spec=ApprovalWorkflow)
    workflow.get_assessment.return_value = assessment
    workflow.get_assessment_evidence_timeline.return_value = timeline
    workflow.list_assessments.return_value = [assessment_summary]
    workflow.get_revocation.return_value = revocation
    workflow.list_revocations.return_value = [revocation_summary]
    client = _client(workflow)

    assessment_detail = client.get(f"/v1/approval-assessments/{assessment.assessment_id}")
    assessment_timeline = client.get(
        f"/v1/approval-assessments/{assessment.assessment_id}/evidence-timeline"
    )
    assessment_list = client.get("/v1/approval-assessments?limit=7")
    revocation_detail = client.get(f"/v1/approval-revocations/{revocation.revocation_id}")
    revocation_list = client.get(
        "/v1/approval-revocations",
        params={
            "human_authorization_evidence_id": str(revocation.human_authorization_evidence_id),
            "limit": 9,
        },
    )

    assert assessment_detail.status_code == 200
    assert assessment_timeline.status_code == 200
    assert assessment_list.status_code == 200
    assert revocation_detail.status_code == 200
    assert revocation_list.status_code == 200
    assert assessment_list.json()[0]["execution_authorized"] is False
    assert assessment_timeline.json() == timeline.model_dump(mode="json")
    assert revocation_list.json()[0]["execution_ready"] is False
    workflow.get_assessment.assert_called_once_with(assessment.assessment_id)
    workflow.get_assessment_evidence_timeline.assert_called_once_with(assessment.assessment_id)
    workflow.list_assessments.assert_called_once_with(limit=7)
    workflow.get_revocation.assert_called_once_with(revocation.revocation_id)
    workflow.list_revocations.assert_called_once_with(
        human_authorization_evidence_id=revocation.human_authorization_evidence_id,
        limit=9,
    )


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("approval", "APPROVED_PAPER"),
        ("outcome", "APPROVED_PAPER"),
        ("verdict", "secret-client-verdict"),
        ("promotion_state", "PASS_RESEARCH"),
        ("artifact_sha256", "0" * 64),
        ("request_fingerprint_sha256", "1" * 64),
        ("hashes", {}),
        ("thresholds", {}),
        ("created_at_utc", "2026-07-14T00:00:00Z"),
        ("timestamps", {}),
        ("risk_results", []),
        ("checks", []),
        ("expires_at_utc", "2026-07-15T00:00:00Z"),
        ("revoked", True),
        ("revocation_state", "clear"),
        ("metrics", {}),
        ("phase6_metrics", {}),
    ),
)
def test_assessment_create_rejects_client_authority_with_sanitized_typed_422(
    phase7_artifacts: tuple[
        ApprovalAssessmentCreateRequest,
        ApprovalAssessmentArtifact,
        ApprovalRevocationCreateRequest,
        AuthorizationRevocationArtifact,
    ],
    field: str,
    value: object,
) -> None:
    assessment_request, _, _, _ = phase7_artifacts
    workflow = MagicMock(spec=ApprovalWorkflow)
    payload = {**assessment_request.model_dump(mode="json"), field: value}

    response = _client(workflow).post("/v1/approval-assessments", json=payload)

    assert response.status_code == 422
    body = response.json()
    assert set(body) == {"detail"}
    assert body["detail"]
    assert all(set(issue) == {"loc", "msg", "type"} for issue in body["detail"])
    assert body["detail"][0]["loc"][-1] == field
    assert "secret-client-verdict" not in response.text
    workflow.create_assessment.assert_not_called()


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("approval", "APPROVED_PAPER"),
        ("artifact_sha256", "0" * 64),
        ("authorization_sha256", "1" * 64),
        ("thresholds", {}),
        ("created_at_utc", "2026-07-14T00:00:00Z"),
        ("effective_at_utc", "2026-07-14T00:00:00Z"),
        ("risk_results", []),
        ("expires_at_utc", "2026-07-15T00:00:00Z"),
        ("revoked", True),
        ("revocation_state", "active"),
        ("phase6_metrics", {}),
    ),
)
def test_revocation_create_rejects_client_authority_with_sanitized_typed_422(
    phase7_artifacts: tuple[
        ApprovalAssessmentCreateRequest,
        ApprovalAssessmentArtifact,
        ApprovalRevocationCreateRequest,
        AuthorizationRevocationArtifact,
    ],
    field: str,
    value: object,
) -> None:
    _, _, revocation_request, _ = phase7_artifacts
    workflow = MagicMock(spec=ApprovalWorkflow)
    payload = {**revocation_request.model_dump(mode="json"), field: value}

    response = _client(workflow).post("/v1/approval-revocations", json=payload)

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"][-1] == field
    assert all(set(issue) == {"loc", "msg", "type"} for issue in response.json()["detail"])
    workflow.create_revocation.assert_not_called()


def test_missing_conflicting_and_malformed_requests_are_sanitized(
    phase7_artifacts: tuple[
        ApprovalAssessmentCreateRequest,
        ApprovalAssessmentArtifact,
        ApprovalRevocationCreateRequest,
        AuthorizationRevocationArtifact,
    ],
) -> None:
    _, _, revocation_request, _ = phase7_artifacts
    workflow = MagicMock(spec=ApprovalWorkflow)
    workflow.get_assessment.side_effect = ApprovalEvidenceNotFound(
        "secret missing evidence identity"
    )
    workflow.get_assessment_evidence_timeline.side_effect = ApprovalEvidenceNotFound(
        "secret missing timeline evidence identity"
    )
    workflow.create_revocation.side_effect = ApprovalWorkflowConflict(
        "secret persisted hash conflict"
    )
    client = _client(workflow)

    missing = client.get(f"/v1/approval-assessments/{MISSING_ID}")
    missing_timeline = client.get(f"/v1/approval-assessments/{MISSING_ID}/evidence-timeline")
    workflow.get_assessment_evidence_timeline.side_effect = ApprovalWorkflowConflict(
        "secret timeline hash conflict"
    )
    conflicting_timeline = client.get(f"/v1/approval-assessments/{MISSING_ID}/evidence-timeline")
    conflict = client.post(
        "/v1/approval-revocations",
        json=revocation_request.model_dump(mode="json"),
    )
    malformed = client.get("/v1/approval-assessments/not-a-uuid")

    assert missing.status_code == 404
    assert missing.json() == {
        "detail": "The requested immutable Phase 7 approval evidence was not found."
    }
    assert missing_timeline.status_code == 404
    assert missing_timeline.json() == missing.json()
    assert conflicting_timeline.status_code == 409
    assert conflicting_timeline.json() == {
        "detail": "Immutable Phase 7 approval evidence conflicts with persisted lineage."
    }
    assert conflict.status_code == 409
    assert conflict.json() == {
        "detail": "Immutable Phase 7 approval evidence conflicts with persisted lineage."
    }
    assert malformed.status_code == 422
    assert all(set(issue) == {"loc", "msg", "type"} for issue in malformed.json()["detail"])
    combined = (
        missing.text
        + missing_timeline.text
        + conflicting_timeline.text
        + conflict.text
        + malformed.text
    )
    assert "secret missing evidence identity" not in combined
    assert "secret missing timeline evidence identity" not in combined
    assert "secret timeline hash conflict" not in combined
    assert "secret persisted hash conflict" not in combined
    assert "not-a-uuid" not in malformed.text


@pytest.mark.parametrize(
    ("error_type", "status_code", "public_detail"),
    (
        (
            ApprovalEvidenceNotFound,
            404,
            "The requested immutable Phase 7 approval evidence was not found.",
        ),
        (
            ApprovalWorkflowConflict,
            409,
            "Immutable Phase 7 approval evidence conflicts with persisted lineage.",
        ),
    ),
)
@pytest.mark.parametrize("evidence_name", ("policy", "scope", "authorization", "risk input"))
def test_each_timeline_evidence_reference_failure_is_sanitized(
    error_type: type[ApprovalEvidenceNotFound] | type[ApprovalWorkflowConflict],
    status_code: int,
    public_detail: str,
    evidence_name: str,
) -> None:
    workflow = MagicMock(spec=ApprovalWorkflow)
    workflow.get_assessment_evidence_timeline.side_effect = error_type(
        f"secret {evidence_name} identity, hash, or lineage conflict"
    )

    response = _client(workflow).get(f"/v1/approval-assessments/{MISSING_ID}/evidence-timeline")

    assert response.status_code == status_code
    assert response.json() == {"detail": public_detail}
    assert "secret" not in response.text


def test_every_get_validation_error_uses_the_sanitized_phase7_contract() -> None:
    workflow = MagicMock(spec=ApprovalWorkflow)
    client = _client(workflow)

    responses = (
        client.get("/v1/approval-assessments?limit=0"),
        client.get("/v1/approval-assessments/not-a-uuid"),
        client.get("/v1/approval-assessments/not-a-uuid/evidence-timeline"),
        client.get("/v1/approval-revocations?limit=101"),
        client.get(
            "/v1/approval-revocations",
            params={"human_authorization_evidence_id": "not-a-uuid"},
        ),
        client.get("/v1/approval-revocations/not-a-uuid"),
    )

    for response in responses:
        assert response.status_code == 422
        body = response.json()
        assert set(body) == {"detail"}
        assert body["detail"]
        assert all(set(issue) == {"loc", "msg", "type"} for issue in body["detail"])
        assert "not-a-uuid" not in response.text
    workflow.list_assessments.assert_not_called()
    workflow.get_assessment.assert_not_called()
    workflow.get_assessment_evidence_timeline.assert_not_called()
    workflow.list_revocations.assert_not_called()
    workflow.get_revocation.assert_not_called()


def test_phase7_api_exposes_no_update_or_delete_method() -> None:
    workflow = MagicMock(spec=ApprovalWorkflow)
    client = _client(workflow)
    paths = (
        "/v1/approval-assessments",
        f"/v1/approval-assessments/{MISSING_ID}",
        f"/v1/approval-assessments/{MISSING_ID}/evidence-timeline",
        "/v1/approval-revocations",
        f"/v1/approval-revocations/{MISSING_ID}",
    )

    for path in paths:
        for method in (client.put, client.patch, client.delete):
            assert method(path).status_code == 405
    workflow.create_assessment.assert_not_called()
    workflow.create_revocation.assert_not_called()
