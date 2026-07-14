"""Create/read/list API for immutable Phase 6 research-only artifacts."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fable5_backtester.contracts import PromotionState
from fable5_backtester.repository import EvaluationRepository
from fable5_data.repository import SnapshotRepository
from fable5_research.contracts import (
    ResearchRunArtifact,
    ResearchRunCreateRequest,
    ResearchRunSummary,
)
from fable5_research.repository import (
    ResearchRepository,
    ResearchRepositoryConflict,
    ResearchRunNotFound,
)
from fable5_research.workflow import (
    ResearchWorkflow,
    ResearchWorkflowBlocked,
    ResearchWorkflowConflict,
)
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from fable5_api.config import Settings


def default_research_workflow_factory(settings: Settings) -> ResearchWorkflow:
    return ResearchWorkflow(
        repository=ResearchRepository(settings.database_url),
        evaluation_repository=EvaluationRepository(settings.database_url),
        snapshot_repository=SnapshotRepository(settings.database_url),
        code_version_git_sha=settings.code_version_git_sha,
    )


def get_research_workflow(request: Request) -> ResearchWorkflow:
    return request.app.state.research_workflow  # type: ignore[no-any-return]


ResearchWorkflowDependency = Annotated[ResearchWorkflow, Depends(get_research_workflow)]
Limit = Annotated[int, Query(ge=1, le=100)]

router = APIRouter(prefix="/v1/research-runs", tags=["research-pipelines"])


class ResearchRunBlockedResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    promotion_state: PromotionState
    reason_codes: tuple[str, ...]
    sanitized_message: str


class ResearchValidationIssue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    loc: list[str | int]
    msg: str
    type: str


class ResearchValidationErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    detail: list[ResearchValidationIssue]


ResearchRunUnprocessableResponse = ResearchRunBlockedResponse | ResearchValidationErrorResponse


def _blocked_response(exc: ResearchWorkflowBlocked) -> JSONResponse:
    result = ResearchRunBlockedResponse(
        promotion_state=exc.promotion_state,
        reason_codes=exc.reason_codes,
        sanitized_message=(
            "Phase 6 research stopped because authoritative immutable evidence was unavailable."
        ),
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=jsonable_encoder(result),
    )


def _domain_error(exc: Exception) -> HTTPException:
    if isinstance(exc, ResearchRunNotFound):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The requested immutable Phase 6 research run was not found.",
        )
    if isinstance(exc, (ResearchRepositoryConflict, ResearchWorkflowConflict)):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Immutable Phase 6 research lineage conflicts with persisted evidence.",
        )
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="The immutable Phase 6 research request could not be completed.",
    )


@router.post(
    "",
    response_model=ResearchRunArtifact,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ResearchRunUnprocessableResponse,
        },
    },
)
def create_research_run(
    payload: ResearchRunCreateRequest,
    workflow: ResearchWorkflowDependency,
) -> ResearchRunArtifact | JSONResponse:
    try:
        return workflow.create_run(payload)
    except ResearchWorkflowBlocked as exc:
        return _blocked_response(exc)
    except (ResearchRepositoryConflict, ResearchRunNotFound, ResearchWorkflowConflict) as exc:
        raise _domain_error(exc) from exc


@router.get("", response_model=list[ResearchRunSummary])
def list_research_runs(
    workflow: ResearchWorkflowDependency,
    limit: Limit = 100,
) -> list[ResearchRunSummary]:
    try:
        return workflow.list_runs(limit=limit)
    except (ResearchRepositoryConflict, ResearchWorkflowConflict) as exc:
        raise _domain_error(exc) from exc


@router.get("/{run_id}", response_model=ResearchRunArtifact)
def get_research_run(
    run_id: UUID,
    workflow: ResearchWorkflowDependency,
) -> ResearchRunArtifact:
    try:
        return workflow.get_run(run_id)
    except (ResearchRepositoryConflict, ResearchRunNotFound, ResearchWorkflowConflict) as exc:
        raise _domain_error(exc) from exc


ResearchWorkflowFactory = Callable[[Settings], ResearchWorkflow]

__all__ = [
    "ResearchWorkflowFactory",
    "default_research_workflow_factory",
    "router",
]
