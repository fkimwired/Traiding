from __future__ import annotations

from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fable5_mapping.models import MappingWithRationale
from fable5_mapping.repository import (
    MappingConflictError,
    MappingLineageError,
    MappingNotFoundError,
    MappingRepository,
)
from fable5_mapping.workflow import MappingWorkflow
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from fable5_api.config import Settings


def default_mapping_workflow_factory(settings: Settings) -> MappingWorkflow:
    return MappingWorkflow(MappingRepository(settings.database_url))


def get_mapping_workflow(request: Request) -> MappingWorkflow:
    return request.app.state.mapping_workflow  # type: ignore[no-any-return]


MappingWorkflowDependency = Annotated[MappingWorkflow, Depends(get_mapping_workflow)]
Limit = Annotated[int, Query(ge=1, le=100)]
OptionalCardId = Annotated[UUID | None, Query()]

router = APIRouter(prefix="/v1", tags=["canon-mapping"])


def _translate_mapping_error(exc: Exception) -> HTTPException:
    if isinstance(exc, MappingNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The requested immutable mapping record was not found.",
        )
    if isinstance(exc, (MappingLineageError, MappingConflictError)):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The mapping request conflicts with persisted immutable research lineage.",
        )
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="The immutable mapping request could not be completed.",
    )


@router.post(
    "/cards/{card_id}/mappings",
    response_model=MappingWithRationale,
    status_code=status.HTTP_201_CREATED,
)
def create_mapping(
    card_id: UUID,
    workflow: MappingWorkflowDependency,
) -> MappingWithRationale:
    try:
        return workflow.create_mapping(card_id)
    except (MappingNotFoundError, MappingLineageError, MappingConflictError) as exc:
        raise _translate_mapping_error(exc) from exc


@router.get("/mappings", response_model=list[MappingWithRationale])
def list_mappings(
    workflow: MappingWorkflowDependency,
    card_id: OptionalCardId = None,
    limit: Limit = 100,
) -> list[MappingWithRationale]:
    try:
        return workflow.list_mappings(card_id=card_id, limit=limit)
    except (MappingNotFoundError, MappingLineageError, MappingConflictError) as exc:
        raise _translate_mapping_error(exc) from exc


@router.get("/mappings/{mapping_id}", response_model=MappingWithRationale)
def get_mapping(
    mapping_id: UUID,
    workflow: MappingWorkflowDependency,
) -> MappingWithRationale:
    try:
        return workflow.get_mapping(mapping_id)
    except (MappingNotFoundError, MappingLineageError, MappingConflictError) as exc:
        raise _translate_mapping_error(exc) from exc


MappingWorkflowFactory = Callable[[Settings], MappingWorkflow]
