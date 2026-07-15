"""Create/read/list API for immutable Phase 7 approval and risk assessments."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fable5_research.repository import ResearchRepository, ResearchRepositoryConflict
from fable5_risk.contracts import (
    ApprovalAssessmentArtifact,
    ApprovalAssessmentCreateRequest,
    ApprovalAssessmentEvidenceTimeline,
    ApprovalAssessmentSummary,
    ApprovalRevocationCreateRequest,
    AuthorizationRevocationArtifact,
    AuthorizationRevocationSummary,
)
from fable5_risk.repository import (
    RiskArtifactNotFound,
    RiskRepository,
    RiskRepositoryConflict,
)
from fable5_risk.workflow import (
    ApprovalEvidenceNotFound,
    ApprovalWorkflow,
    ApprovalWorkflowConflict,
    Phase6ResearchStoreAdapter,
)
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ConfigDict
from starlette.responses import JSONResponse, Response

from fable5_api.config import Settings


def default_approval_workflow_factory(settings: Settings) -> ApprovalWorkflow:
    return ApprovalWorkflow(
        research_store=Phase6ResearchStoreAdapter(ResearchRepository(settings.database_url)),
        risk_store=RiskRepository(settings.database_url),
        phase7_code_version_git_sha=settings.code_version_git_sha,
    )


def get_approval_workflow(request: Request) -> ApprovalWorkflow:
    return request.app.state.approval_workflow  # type: ignore[no-any-return]


ApprovalWorkflowDependency = Annotated[ApprovalWorkflow, Depends(get_approval_workflow)]
Limit = Annotated[int, Query(ge=1, le=100)]
AuthorizationEvidenceFilter = Annotated[UUID | None, Query()]

assessment_router = APIRouter(prefix="/v1/approval-assessments", tags=["approval-governance"])
revocation_router = APIRouter(prefix="/v1/approval-revocations", tags=["approval-governance"])


class ApprovalValidationIssue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    loc: list[str | int]
    msg: str
    type: str


class ApprovalValidationErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    detail: list[ApprovalValidationIssue]


async def approval_validation_error_handler(
    request: Request,
    exc: Exception,
) -> Response:
    if not isinstance(exc, RequestValidationError):
        raise exc
    if not request.url.path.startswith(("/v1/approval-assessments", "/v1/approval-revocations")):
        return await request_validation_exception_handler(request, exc)
    response = ApprovalValidationErrorResponse(
        detail=[
            ApprovalValidationIssue(
                loc=list(error["loc"]),
                msg=str(error["msg"]),
                type=str(error["type"]),
            )
            for error in exc.errors()
        ]
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=response.model_dump(mode="json"),
    )


def _domain_error(exc: Exception) -> HTTPException:
    if isinstance(exc, (ApprovalEvidenceNotFound, RiskArtifactNotFound)):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The requested immutable Phase 7 approval evidence was not found.",
        )
    if isinstance(
        exc,
        (ApprovalWorkflowConflict, ResearchRepositoryConflict, RiskRepositoryConflict),
    ):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Immutable Phase 7 approval evidence conflicts with persisted lineage.",
        )
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="The immutable Phase 7 approval request could not be completed.",
    )


@assessment_router.post(
    "",
    response_model=ApprovalAssessmentArtifact,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ApprovalValidationErrorResponse,
        },
    },
)
def create_approval_assessment(
    payload: ApprovalAssessmentCreateRequest,
    workflow: ApprovalWorkflowDependency,
) -> ApprovalAssessmentArtifact:
    try:
        return workflow.create_assessment(payload)
    except (
        ApprovalEvidenceNotFound,
        ApprovalWorkflowConflict,
        ResearchRepositoryConflict,
        RiskArtifactNotFound,
        RiskRepositoryConflict,
    ) as exc:
        raise _domain_error(exc) from exc


@assessment_router.get(
    "",
    response_model=list[ApprovalAssessmentSummary],
    responses={
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ApprovalValidationErrorResponse,
        },
    },
)
def list_approval_assessments(
    workflow: ApprovalWorkflowDependency,
    limit: Limit = 100,
) -> list[ApprovalAssessmentSummary]:
    try:
        return workflow.list_assessments(limit=limit)
    except (ApprovalWorkflowConflict, ResearchRepositoryConflict, RiskRepositoryConflict) as exc:
        raise _domain_error(exc) from exc


@assessment_router.get(
    "/{assessment_id}",
    response_model=ApprovalAssessmentArtifact,
    responses={
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ApprovalValidationErrorResponse,
        },
    },
)
def get_approval_assessment(
    assessment_id: UUID,
    workflow: ApprovalWorkflowDependency,
) -> ApprovalAssessmentArtifact:
    try:
        return workflow.get_assessment(assessment_id)
    except (
        ApprovalEvidenceNotFound,
        ApprovalWorkflowConflict,
        ResearchRepositoryConflict,
        RiskArtifactNotFound,
        RiskRepositoryConflict,
    ) as exc:
        raise _domain_error(exc) from exc


@assessment_router.get(
    "/{assessment_id}/evidence-timeline",
    response_model=ApprovalAssessmentEvidenceTimeline,
    responses={
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ApprovalValidationErrorResponse,
        },
    },
)
def get_approval_assessment_evidence_timeline(
    assessment_id: UUID,
    workflow: ApprovalWorkflowDependency,
) -> ApprovalAssessmentEvidenceTimeline:
    try:
        return workflow.get_assessment_evidence_timeline(assessment_id)
    except (
        ApprovalEvidenceNotFound,
        ApprovalWorkflowConflict,
        ResearchRepositoryConflict,
        RiskArtifactNotFound,
        RiskRepositoryConflict,
    ) as exc:
        raise _domain_error(exc) from exc


@revocation_router.post(
    "",
    response_model=AuthorizationRevocationArtifact,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ApprovalValidationErrorResponse,
        },
    },
)
def create_approval_revocation(
    payload: ApprovalRevocationCreateRequest,
    workflow: ApprovalWorkflowDependency,
) -> AuthorizationRevocationArtifact:
    try:
        return workflow.create_revocation(payload)
    except (
        ApprovalEvidenceNotFound,
        ApprovalWorkflowConflict,
        ResearchRepositoryConflict,
        RiskArtifactNotFound,
        RiskRepositoryConflict,
    ) as exc:
        raise _domain_error(exc) from exc


@revocation_router.get(
    "",
    response_model=list[AuthorizationRevocationSummary],
    responses={
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ApprovalValidationErrorResponse,
        },
    },
)
def list_approval_revocations(
    workflow: ApprovalWorkflowDependency,
    human_authorization_evidence_id: AuthorizationEvidenceFilter = None,
    limit: Limit = 100,
) -> list[AuthorizationRevocationSummary]:
    try:
        return workflow.list_revocations(
            human_authorization_evidence_id=human_authorization_evidence_id,
            limit=limit,
        )
    except (ApprovalWorkflowConflict, ResearchRepositoryConflict, RiskRepositoryConflict) as exc:
        raise _domain_error(exc) from exc


@revocation_router.get(
    "/{revocation_id}",
    response_model=AuthorizationRevocationArtifact,
    responses={
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ApprovalValidationErrorResponse,
        },
    },
)
def get_approval_revocation(
    revocation_id: UUID,
    workflow: ApprovalWorkflowDependency,
) -> AuthorizationRevocationArtifact:
    try:
        return workflow.get_revocation(revocation_id)
    except (
        ApprovalEvidenceNotFound,
        ApprovalWorkflowConflict,
        ResearchRepositoryConflict,
        RiskArtifactNotFound,
        RiskRepositoryConflict,
    ) as exc:
        raise _domain_error(exc) from exc


ApprovalWorkflowFactory = Callable[[Settings], ApprovalWorkflow]

__all__ = [
    "ApprovalWorkflowFactory",
    "approval_validation_error_handler",
    "assessment_router",
    "default_approval_workflow_factory",
    "revocation_router",
]
