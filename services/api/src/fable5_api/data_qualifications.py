"""Read-only API projection for immutable Phase 13 qualification evidence."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, Literal
from uuid import UUID

from fable5_data.phase13.contracts import PointInTimeQualificationArtifact
from fable5_data.phase13.repository import (
    PointInTimeQualificationNotFound,
    PointInTimeQualificationRepository,
    PointInTimeQualificationRepositoryConflict,
)
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ConfigDict
from starlette.responses import JSONResponse, Response

from fable5_api.config import Settings
from fable5_api.paper_shadow_readiness import (
    paper_shadow_readiness_validation_error_handler,
)

QUALIFICATION_NOT_FOUND_DETAIL = (
    "The requested immutable Phase 13 point-in-time qualification evidence was not found."
)
QUALIFICATION_CONFLICT_DETAIL = (
    "Immutable Phase 13 point-in-time qualification evidence conflicts with persisted lineage."
)


class PointInTimeQualificationValidationIssue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    loc: list[str | int]
    msg: str
    type: str


class PointInTimeQualificationValidationErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    detail: list[PointInTimeQualificationValidationIssue]


class PointInTimeQualificationNotFoundErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    detail: Literal[
        "The requested immutable Phase 13 point-in-time qualification evidence was not found."
    ]


class PointInTimeQualificationConflictErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    detail: Literal[
        "Immutable Phase 13 point-in-time qualification evidence conflicts with persisted lineage."
    ]


def default_point_in_time_qualification_repository_factory(
    settings: Settings,
) -> PointInTimeQualificationRepository:
    return PointInTimeQualificationRepository(settings.database_url)


def get_point_in_time_qualification_repository(
    request: Request,
) -> PointInTimeQualificationRepository:
    return request.app.state.point_in_time_qualification_repository  # type: ignore[no-any-return]


PointInTimeQualificationRepositoryDependency = Annotated[
    PointInTimeQualificationRepository,
    Depends(get_point_in_time_qualification_repository),
]

router = APIRouter(
    prefix="/v1/point-in-time-data-qualifications",
    tags=["point-in-time-data-qualifications"],
)


async def point_in_time_qualification_validation_error_handler(
    request: Request,
    exc: Exception,
) -> Response:
    if not isinstance(exc, RequestValidationError):
        raise exc
    if not request.url.path.startswith("/v1/point-in-time-data-qualifications"):
        return await paper_shadow_readiness_validation_error_handler(request, exc)
    response = PointInTimeQualificationValidationErrorResponse(
        detail=[
            PointInTimeQualificationValidationIssue(
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
    "/{qualification_id}",
    response_model=PointInTimeQualificationArtifact,
    responses={
        status.HTTP_404_NOT_FOUND: {"model": PointInTimeQualificationNotFoundErrorResponse},
        status.HTTP_409_CONFLICT: {"model": PointInTimeQualificationConflictErrorResponse},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": PointInTimeQualificationValidationErrorResponse
        },
    },
)
def get_point_in_time_qualification(
    qualification_id: UUID,
    repository: PointInTimeQualificationRepositoryDependency,
) -> PointInTimeQualificationArtifact:
    try:
        return repository.get_qualification(qualification_id)
    except PointInTimeQualificationNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=QUALIFICATION_NOT_FOUND_DETAIL,
        ) from exc
    except PointInTimeQualificationRepositoryConflict as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=QUALIFICATION_CONFLICT_DETAIL,
        ) from exc


PointInTimeQualificationRepositoryFactory = Callable[
    [Settings],
    PointInTimeQualificationRepository,
]

__all__ = [
    "PointInTimeQualificationConflictErrorResponse",
    "PointInTimeQualificationNotFoundErrorResponse",
    "PointInTimeQualificationRepositoryFactory",
    "PointInTimeQualificationValidationErrorResponse",
    "default_point_in_time_qualification_repository_factory",
    "point_in_time_qualification_validation_error_handler",
    "router",
]
