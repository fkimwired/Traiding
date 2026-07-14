from __future__ import annotations

from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fable5_data.adapters import Phase4DataAdapter
from fable5_data.contracts import (
    AdapterUnavailableResult,
    AuthorizedMappingIdentity,
    DataSnapshot,
    SnapshotBuildBlockedResult,
    SnapshotBundle,
    SnapshotCreateRequest,
)
from fable5_data.quality import QualityReferenceCatalog
from fable5_data.repository import (
    MappingNotFound,
    SnapshotAuthorization,
    SnapshotConflict,
    SnapshotLineage,
    SnapshotNotFound,
    SnapshotRepository,
)
from fable5_data.synthetic import (
    SYNTHETIC_MOCK_CONFIGURATION,
    SyntheticPointInTimeAdapter,
)
from fable5_data.workflow import (
    SnapshotAdapterUnavailable,
    SnapshotQualityBlocked,
    SnapshotWorkflow,
)
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from fable5_api.config import Settings


def default_snapshot_workflow_factory(settings: Settings) -> SnapshotWorkflow:
    adapter = SyntheticPointInTimeAdapter()

    def resolve_adapter(
        mapping: AuthorizedMappingIdentity,
    ) -> tuple[Phase4DataAdapter, QualityReferenceCatalog]:
        resolved = SyntheticPointInTimeAdapter.for_mapping(mapping)
        return resolved, QualityReferenceCatalog.from_results(resolved.all_results())

    return SnapshotWorkflow(
        repository=SnapshotRepository(settings.database_url),
        adapter=adapter,
        configuration=SYNTHETIC_MOCK_CONFIGURATION,
        quality_catalog=QualityReferenceCatalog.from_results(adapter.all_results()),
        adapter_resolver=resolve_adapter,
    )


def get_snapshot_workflow(request: Request) -> SnapshotWorkflow:
    return request.app.state.snapshot_workflow  # type: ignore[no-any-return]


SnapshotWorkflowDependency = Annotated[SnapshotWorkflow, Depends(get_snapshot_workflow)]
Limit = Annotated[int, Query(ge=1, le=100)]
OptionalMappingId = Annotated[UUID | None, Query()]

router = APIRouter(prefix="/v1/data-snapshots", tags=["point-in-time-data"])


class SnapshotRequestError(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    detail: str


class SnapshotValidationIssue(BaseModel):
    loc: list[str | int]
    msg: str
    type: str


class SnapshotValidationErrorResponse(BaseModel):
    detail: list[SnapshotValidationIssue]


SnapshotUnprocessableResponse = (
    SnapshotBuildBlockedResult | SnapshotRequestError | SnapshotValidationErrorResponse
)


def _domain_http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, (MappingNotFound, SnapshotNotFound)):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The requested immutable Phase 4 resource was not found.",
        )
    if isinstance(exc, SnapshotAuthorization):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The persisted mapping does not authorize this Phase 4 data capability.",
        )
    if isinstance(exc, (SnapshotConflict, SnapshotLineage)):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The immutable snapshot request conflicts with persisted lineage.",
        )
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="The immutable snapshot request could not be completed.",
    )


@router.post(
    "",
    response_model=SnapshotBundle,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": SnapshotUnprocessableResponse,
            "description": (
                "Request validation, mapping authorization, or mandatory data-quality failure"
            ),
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": AdapterUnavailableResult,
            "description": "Typed, sanitized adapter/configuration unavailability",
        },
    },
)
def create_data_snapshot(
    payload: SnapshotCreateRequest,
    workflow: SnapshotWorkflowDependency,
) -> SnapshotBundle | JSONResponse:
    try:
        return workflow.create_snapshot(payload)
    except SnapshotQualityBlocked as exc:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=jsonable_encoder(exc.result),
        )
    except SnapshotAdapterUnavailable as exc:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=jsonable_encoder(exc.result),
        )
    except (
        MappingNotFound,
        SnapshotAuthorization,
        SnapshotConflict,
        SnapshotLineage,
    ) as exc:
        raise _domain_http_error(exc) from exc


@router.get("", response_model=list[DataSnapshot])
def list_data_snapshots(
    workflow: SnapshotWorkflowDependency,
    mapping_id: OptionalMappingId = None,
    limit: Limit = 100,
) -> list[DataSnapshot]:
    try:
        return workflow.list_snapshots(mapping_id=mapping_id, limit=limit)
    except (MappingNotFound, SnapshotAuthorization, SnapshotConflict, SnapshotLineage) as exc:
        raise _domain_http_error(exc) from exc


@router.get("/{snapshot_id}", response_model=SnapshotBundle)
def get_data_snapshot(
    snapshot_id: UUID,
    workflow: SnapshotWorkflowDependency,
) -> SnapshotBundle:
    try:
        return workflow.get_snapshot(snapshot_id)
    except (
        MappingNotFound,
        SnapshotNotFound,
        SnapshotAuthorization,
        SnapshotConflict,
        SnapshotLineage,
    ) as exc:
        raise _domain_http_error(exc) from exc


SnapshotWorkflowFactory = Callable[[Settings], SnapshotWorkflow]


__all__ = [
    "SnapshotWorkflowFactory",
    "default_snapshot_workflow_factory",
    "router",
]
