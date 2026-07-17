"""Read-only API projection for immutable Phase 12 shadow-readiness evidence."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, Literal
from uuid import UUID

from fable5_paper.phase12.contracts import PaperShadowReadinessArtifact
from fable5_paper.phase12.repository import (
    PaperShadowReadinessNotFound,
    PaperShadowReadinessRepository,
    PaperShadowReadinessRepositoryConflict,
)
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ConfigDict
from starlette.responses import JSONResponse, Response

from fable5_api.config import Settings
from fable5_api.local_simulations import paper_simulation_validation_error_handler

READINESS_NOT_FOUND_DETAIL = (
    "The requested immutable Phase 12 paper shadow-readiness evidence was not found."
)
READINESS_CONFLICT_DETAIL = (
    "Immutable Phase 12 paper shadow-readiness evidence conflicts with persisted lineage."
)


class PaperShadowReadinessValidationIssue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    loc: list[str | int]
    msg: str
    type: str


class PaperShadowReadinessValidationErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    detail: list[PaperShadowReadinessValidationIssue]


class PaperShadowReadinessNotFoundErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    detail: Literal[
        "The requested immutable Phase 12 paper shadow-readiness evidence was not found."
    ]


class PaperShadowReadinessConflictErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    detail: Literal[
        "Immutable Phase 12 paper shadow-readiness evidence conflicts with persisted lineage."
    ]


def default_paper_shadow_readiness_repository_factory(
    settings: Settings,
) -> PaperShadowReadinessRepository:
    return PaperShadowReadinessRepository(settings.database_url)


def get_paper_shadow_readiness_repository(request: Request) -> PaperShadowReadinessRepository:
    return request.app.state.paper_shadow_readiness_repository  # type: ignore[no-any-return]


PaperShadowReadinessRepositoryDependency = Annotated[
    PaperShadowReadinessRepository,
    Depends(get_paper_shadow_readiness_repository),
]

router = APIRouter(prefix="/v1/paper-shadow-readiness", tags=["paper-shadow-readiness"])


async def paper_shadow_readiness_validation_error_handler(
    request: Request,
    exc: Exception,
) -> Response:
    if not isinstance(exc, RequestValidationError):
        raise exc
    if not request.url.path.startswith("/v1/paper-shadow-readiness"):
        return await paper_simulation_validation_error_handler(request, exc)
    response = PaperShadowReadinessValidationErrorResponse(
        detail=[
            PaperShadowReadinessValidationIssue(
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
    "/{readiness_assessment_id}",
    response_model=PaperShadowReadinessArtifact,
    responses={
        status.HTTP_404_NOT_FOUND: {"model": PaperShadowReadinessNotFoundErrorResponse},
        status.HTTP_409_CONFLICT: {"model": PaperShadowReadinessConflictErrorResponse},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": PaperShadowReadinessValidationErrorResponse
        },
    },
)
def get_paper_shadow_readiness(
    readiness_assessment_id: UUID,
    repository: PaperShadowReadinessRepositoryDependency,
) -> PaperShadowReadinessArtifact:
    try:
        return repository.get_readiness(readiness_assessment_id)
    except PaperShadowReadinessNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=READINESS_NOT_FOUND_DETAIL,
        ) from exc
    except PaperShadowReadinessRepositoryConflict as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=READINESS_CONFLICT_DETAIL,
        ) from exc


PaperShadowReadinessRepositoryFactory = Callable[
    [Settings],
    PaperShadowReadinessRepository,
]

__all__ = [
    "PaperShadowReadinessConflictErrorResponse",
    "PaperShadowReadinessNotFoundErrorResponse",
    "PaperShadowReadinessRepositoryFactory",
    "PaperShadowReadinessValidationErrorResponse",
    "default_paper_shadow_readiness_repository_factory",
    "paper_shadow_readiness_validation_error_handler",
    "router",
]
