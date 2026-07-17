"""Create/read/list API for deterministic local mock-only paper simulations."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, Literal
from uuid import UUID

from fable5_paper.contracts import (
    PaperSimulationArtifact,
    PaperSimulationCreateRequest,
    PaperSimulationSummary,
)
from fable5_paper.repository import (
    PaperArtifactNotFound,
    PaperRepository,
    PaperRepositoryConflict,
)
from fable5_paper.workflow import (
    PaperEvidenceNotFound,
    PaperSimulationWorkflow,
    PaperWorkflowConflict,
    PostgresPaperEvidenceGateway,
)
from fable5_research.repository import ResearchRepository, ResearchRepositoryConflict
from fable5_risk.repository import RiskRepository, RiskRepositoryConflict
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ConfigDict
from starlette.responses import JSONResponse, Response

from fable5_api.approvals import approval_validation_error_handler
from fable5_api.config import Settings


def default_paper_simulation_workflow_factory(settings: Settings) -> PaperSimulationWorkflow:
    research_repository = ResearchRepository(settings.database_url)
    risk_repository = RiskRepository(settings.database_url)
    return PaperSimulationWorkflow(
        evidence=PostgresPaperEvidenceGateway(research_repository, risk_repository),
        simulations=PaperRepository(settings.database_url),
        phase10_code_version_git_sha=settings.code_version_git_sha,
    )


def get_paper_simulation_workflow(request: Request) -> PaperSimulationWorkflow:
    return request.app.state.paper_simulation_workflow  # type: ignore[no-any-return]


PaperSimulationWorkflowDependency = Annotated[
    PaperSimulationWorkflow,
    Depends(get_paper_simulation_workflow),
]
Limit = Annotated[int, Query(ge=1, le=100)]
ApprovalAssessmentFilter = Annotated[UUID | None, Query()]

router = APIRouter(prefix="/v1/local-simulations", tags=["paper-simulation"])

PAPER_SIMULATION_NOT_FOUND_DETAIL = (
    "The requested immutable Phase 10 simulation evidence was not found."
)
PAPER_SIMULATION_CONFLICT_DETAIL = (
    "Immutable Phase 10 simulation evidence conflicts with persisted lineage."
)
PAPER_SIMULATION_REQUEST_CONFLICT_DETAIL = (
    "The immutable Phase 10 simulation request could not be completed."
)


class PaperSimulationValidationIssue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    loc: list[str | int]
    msg: str
    type: str


class PaperSimulationValidationErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    detail: list[PaperSimulationValidationIssue]


class PaperSimulationNotFoundErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    detail: Literal["The requested immutable Phase 10 simulation evidence was not found."]


class PaperSimulationConflictErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    detail: Literal[
        "Immutable Phase 10 simulation evidence conflicts with persisted lineage.",
        "The immutable Phase 10 simulation request could not be completed.",
    ]


async def paper_simulation_validation_error_handler(
    request: Request,
    exc: Exception,
) -> Response:
    if not isinstance(exc, RequestValidationError):
        raise exc
    if not request.url.path.startswith("/v1/local-simulations"):
        return await approval_validation_error_handler(request, exc)
    response = PaperSimulationValidationErrorResponse(
        detail=[
            PaperSimulationValidationIssue(
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
    if isinstance(exc, (PaperArtifactNotFound, PaperEvidenceNotFound)):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=PAPER_SIMULATION_NOT_FOUND_DETAIL,
        )
    if isinstance(
        exc,
        (
            PaperRepositoryConflict,
            PaperWorkflowConflict,
            ResearchRepositoryConflict,
            RiskRepositoryConflict,
        ),
    ):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=PAPER_SIMULATION_CONFLICT_DETAIL,
        )
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=PAPER_SIMULATION_REQUEST_CONFLICT_DETAIL,
    )


@router.post(
    "",
    response_model=PaperSimulationArtifact,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": PaperSimulationNotFoundErrorResponse,
        },
        status.HTTP_409_CONFLICT: {
            "model": PaperSimulationConflictErrorResponse,
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": PaperSimulationValidationErrorResponse,
        },
    },
)
def create_local_simulation(
    payload: PaperSimulationCreateRequest,
    workflow: PaperSimulationWorkflowDependency,
) -> PaperSimulationArtifact:
    try:
        return workflow.create_simulation(payload)
    except (
        PaperArtifactNotFound,
        PaperEvidenceNotFound,
        PaperRepositoryConflict,
        PaperWorkflowConflict,
        ResearchRepositoryConflict,
        RiskRepositoryConflict,
    ) as exc:
        raise _domain_error(exc) from exc


@router.get(
    "",
    response_model=list[PaperSimulationSummary],
    responses={
        status.HTTP_409_CONFLICT: {
            "model": PaperSimulationConflictErrorResponse,
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": PaperSimulationValidationErrorResponse,
        },
    },
)
def list_local_simulations(
    workflow: PaperSimulationWorkflowDependency,
    approval_assessment_id: ApprovalAssessmentFilter = None,
    limit: Limit = 100,
) -> list[PaperSimulationSummary]:
    try:
        return workflow.list_simulations(
            source_assessment_id=approval_assessment_id,
            limit=limit,
        )
    except (PaperRepositoryConflict, PaperWorkflowConflict) as exc:
        raise _domain_error(exc) from exc


@router.get(
    "/{simulation_run_id}",
    response_model=PaperSimulationArtifact,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": PaperSimulationNotFoundErrorResponse,
        },
        status.HTTP_409_CONFLICT: {
            "model": PaperSimulationConflictErrorResponse,
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": PaperSimulationValidationErrorResponse,
        },
    },
)
def get_local_simulation(
    simulation_run_id: UUID,
    workflow: PaperSimulationWorkflowDependency,
) -> PaperSimulationArtifact:
    try:
        return workflow.get_simulation(simulation_run_id)
    except (
        PaperArtifactNotFound,
        PaperRepositoryConflict,
        PaperWorkflowConflict,
    ) as exc:
        raise _domain_error(exc) from exc


PaperSimulationWorkflowFactory = Callable[[Settings], PaperSimulationWorkflow]

__all__ = [
    "PaperSimulationConflictErrorResponse",
    "PaperSimulationNotFoundErrorResponse",
    "PaperSimulationWorkflowFactory",
    "default_paper_simulation_workflow_factory",
    "paper_simulation_validation_error_handler",
    "router",
]
