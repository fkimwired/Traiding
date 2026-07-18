"""Read-only API projection for immutable Phase 14 eligibility evidence."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, Literal
from uuid import UUID

from fable5_data.phase14.contracts import ResearchIngestionEligibilityArtifact
from fable5_data.phase14.repository import (
    ResearchIngestionEligibilityNotFound,
    ResearchIngestionEligibilityRepository,
    ResearchIngestionEligibilityRepositoryConflict,
)
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ConfigDict
from starlette.responses import JSONResponse, Response

from fable5_api.config import Settings
from fable5_api.data_qualifications import (
    point_in_time_qualification_validation_error_handler,
)

ELIGIBILITY_NOT_FOUND_DETAIL = (
    "The requested immutable Phase 14 research-ingestion eligibility evidence was not found."
)
ELIGIBILITY_CONFLICT_DETAIL = (
    "Immutable Phase 14 research-ingestion eligibility evidence conflicts with persisted lineage."
)


class ResearchIngestionEligibilityValidationIssue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    loc: list[str | int]
    msg: str
    type: str


class ResearchIngestionEligibilityValidationErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    detail: list[ResearchIngestionEligibilityValidationIssue]


class ResearchIngestionEligibilityNotFoundErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    detail: Literal[
        "The requested immutable Phase 14 research-ingestion eligibility evidence was not found."
    ]


class ResearchIngestionEligibilityConflictErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    detail: Literal[
        "Immutable Phase 14 research-ingestion eligibility evidence conflicts with persisted "
        "lineage."
    ]


def default_research_ingestion_eligibility_repository_factory(
    settings: Settings,
) -> ResearchIngestionEligibilityRepository:
    return ResearchIngestionEligibilityRepository(settings.database_url)


def get_research_ingestion_eligibility_repository(
    request: Request,
) -> ResearchIngestionEligibilityRepository:
    return request.app.state.research_ingestion_eligibility_repository  # type: ignore[no-any-return]


ResearchIngestionEligibilityRepositoryDependency = Annotated[
    ResearchIngestionEligibilityRepository,
    Depends(get_research_ingestion_eligibility_repository),
]

router = APIRouter(
    prefix="/v1/research-ingestion-eligibility",
    tags=["research-ingestion-eligibility"],
)


async def research_ingestion_eligibility_validation_error_handler(
    request: Request,
    exc: Exception,
) -> Response:
    if not isinstance(exc, RequestValidationError):
        raise exc
    if not request.url.path.startswith("/v1/research-ingestion-eligibility"):
        return await point_in_time_qualification_validation_error_handler(request, exc)
    response = ResearchIngestionEligibilityValidationErrorResponse(
        detail=[
            ResearchIngestionEligibilityValidationIssue(
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


@router.get(
    "/{assessment_id}",
    response_model=ResearchIngestionEligibilityArtifact,
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ResearchIngestionEligibilityNotFoundErrorResponse},
        status.HTTP_409_CONFLICT: {"model": ResearchIngestionEligibilityConflictErrorResponse},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ResearchIngestionEligibilityValidationErrorResponse
        },
    },
)
def get_research_ingestion_eligibility(
    assessment_id: UUID,
    repository: ResearchIngestionEligibilityRepositoryDependency,
) -> ResearchIngestionEligibilityArtifact:
    try:
        return repository.get_assessment(assessment_id)
    except ResearchIngestionEligibilityNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ELIGIBILITY_NOT_FOUND_DETAIL,
        ) from exc
    except ResearchIngestionEligibilityRepositoryConflict as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ELIGIBILITY_CONFLICT_DETAIL,
        ) from exc


ResearchIngestionEligibilityRepositoryFactory = Callable[
    [Settings],
    ResearchIngestionEligibilityRepository,
]

__all__ = [
    "ResearchIngestionEligibilityConflictErrorResponse",
    "ResearchIngestionEligibilityNotFoundErrorResponse",
    "ResearchIngestionEligibilityRepositoryFactory",
    "ResearchIngestionEligibilityValidationErrorResponse",
    "default_research_ingestion_eligibility_repository_factory",
    "research_ingestion_eligibility_validation_error_handler",
    "router",
]
