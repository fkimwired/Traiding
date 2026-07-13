from __future__ import annotations

from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fable5_extraction.models import (
    CardWithMemo,
    ExtractionRequestRecord,
    ResearchMemo,
    SourceCorrectionRequest,
    SourceCreateResponse,
    SourceDetailResponse,
    SourceIntakeRequest,
    SourceRecord,
    SourceVersion,
    TradingIdeaCard,
)
from fable5_extraction.repository import (
    IdeaRepository,
    IdempotencyConflictError,
    InvalidCorroborationError,
    NotFoundError,
    SourceTextUnavailableError,
)
from fable5_extraction.workflow import IdeaIntakeWorkflow
from fable5_jobs import QUEUE_NAME
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from redis import Redis
from rq import Queue, Retry
from rq.exceptions import DuplicateJobError

from fable5_api.config import Settings


class RQExtractionDispatcher:
    def __init__(self, redis_url: str) -> None:
        self.connection: Redis = Redis.from_url(redis_url)
        self.queue = Queue(QUEUE_NAME, connection=self.connection)

    def enqueue(self, request: ExtractionRequestRecord) -> bool:
        try:
            self.queue.enqueue_call(
                "fable5_jobs.extraction.run_extraction",
                args=(str(request.extraction_request_id),),
                job_id=request.rq_job_id,
                retry=Retry(max=2, interval=[1, 3]),
                result_ttl=86_400,
                failure_ttl=604_800,
                unique=True,
            )
        except DuplicateJobError:
            return False
        return True


def default_workflow_factory(settings: Settings) -> IdeaIntakeWorkflow:
    return IdeaIntakeWorkflow(
        IdeaRepository(settings.database_url),
        RQExtractionDispatcher(settings.redis_url),
    )


def get_workflow(request: Request) -> IdeaIntakeWorkflow:
    return request.app.state.idea_intake_workflow  # type: ignore[no-any-return]


WorkflowDependency = Annotated[IdeaIntakeWorkflow, Depends(get_workflow)]
Limit = Annotated[int, Query(ge=1, le=100)]

router = APIRouter(prefix="/v1", tags=["idea-intake"])


def _translate_domain_error(exc: Exception) -> HTTPException:
    if isinstance(exc, NotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(
        exc,
        (InvalidCorroborationError, IdempotencyConflictError, SourceTextUnavailableError),
    ):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        )
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="The immutable research record conflicts with existing state.",
    )


@router.post("/sources", response_model=SourceCreateResponse, status_code=status.HTTP_201_CREATED)
def create_source(
    payload: SourceIntakeRequest, workflow: WorkflowDependency
) -> SourceCreateResponse:
    try:
        return workflow.create_source(payload)
    except (NotFoundError, InvalidCorroborationError, IdempotencyConflictError) as exc:
        raise _translate_domain_error(exc) from exc


@router.get("/sources", response_model=list[SourceRecord])
def list_sources(workflow: WorkflowDependency, limit: Limit = 100) -> list[SourceRecord]:
    return workflow.list_sources(limit)


@router.get("/sources/{source_id}", response_model=SourceDetailResponse)
def get_source(source_id: UUID, workflow: WorkflowDependency) -> SourceDetailResponse:
    try:
        return workflow.get_source(source_id)
    except NotFoundError as exc:
        raise _translate_domain_error(exc) from exc


@router.post(
    "/sources/{source_id}/versions",
    response_model=SourceCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_source_version(
    source_id: UUID,
    payload: SourceCorrectionRequest,
    workflow: WorkflowDependency,
) -> SourceCreateResponse:
    try:
        return workflow.add_source_version(source_id, payload)
    except (NotFoundError, InvalidCorroborationError, IdempotencyConflictError) as exc:
        raise _translate_domain_error(exc) from exc


@router.get("/source-versions/{source_version_id}", response_model=SourceVersion)
def get_source_version(source_version_id: UUID, workflow: WorkflowDependency) -> SourceVersion:
    try:
        return workflow.get_source_version(source_version_id)
    except NotFoundError as exc:
        raise _translate_domain_error(exc) from exc


@router.post(
    "/source-versions/{source_version_id}/extractions",
    response_model=ExtractionRequestRecord,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_extraction(
    source_version_id: UUID, workflow: WorkflowDependency
) -> ExtractionRequestRecord:
    try:
        return workflow.request_extraction(source_version_id)
    except (NotFoundError, SourceTextUnavailableError) as exc:
        raise _translate_domain_error(exc) from exc


@router.get("/extractions", response_model=list[ExtractionRequestRecord])
def list_extractions(
    workflow: WorkflowDependency, limit: Limit = 100
) -> list[ExtractionRequestRecord]:
    return workflow.list_extractions(limit)


@router.get("/extractions/{request_id}", response_model=ExtractionRequestRecord)
def get_extraction(request_id: UUID, workflow: WorkflowDependency) -> ExtractionRequestRecord:
    try:
        return workflow.get_extraction(request_id)
    except NotFoundError as exc:
        raise _translate_domain_error(exc) from exc


@router.get("/cards", response_model=list[TradingIdeaCard])
def list_cards(workflow: WorkflowDependency, limit: Limit = 100) -> list[TradingIdeaCard]:
    return workflow.list_cards(limit)


@router.get("/cards/{card_id}", response_model=CardWithMemo)
def get_card(card_id: UUID, workflow: WorkflowDependency) -> CardWithMemo:
    try:
        return workflow.get_card(card_id)
    except NotFoundError as exc:
        raise _translate_domain_error(exc) from exc


@router.get("/cards/{card_id}/memo", response_model=ResearchMemo)
def get_memo(card_id: UUID, workflow: WorkflowDependency) -> ResearchMemo:
    try:
        return workflow.get_memo(card_id)
    except NotFoundError as exc:
        raise _translate_domain_error(exc) from exc


WorkflowFactory = Callable[[Settings], IdeaIntakeWorkflow]
