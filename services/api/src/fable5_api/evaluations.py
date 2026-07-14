"""Create/read/list API for immutable synthetic Phase 5 evaluation artifacts."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fable5_backtester.contracts import (
    EvaluationBlockedResult,
    EvaluationPolicyCreateRequest,
    EvaluationReport,
    EvaluationReportSummary,
    EvaluationRunCreateRequest,
    FrozenEvaluationPolicy,
)
from fable5_backtester.outcomes import (
    BlockedEvaluationOutcome,
    EvaluationOutcomeNotFound,
)
from fable5_backtester.repository import EvaluationRepository
from fable5_backtester.synthetic import resolve_fixture, resolve_policy
from fable5_backtester.workflow import (
    EvaluationPolicyNotFound,
    EvaluationReportNotFound,
    EvaluationWorkflow,
    EvaluationWorkflowBlocked,
    EvaluationWorkflowConflict,
)
from fable5_data.repository import (
    SnapshotAuthorization,
    SnapshotLineage,
    SnapshotNotFound,
    SnapshotRepository,
)
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from fable5_api.config import Settings


def default_evaluation_workflow_factory(settings: Settings) -> EvaluationWorkflow:
    return EvaluationWorkflow(
        repository=EvaluationRepository(settings.database_url),
        snapshot_repository=SnapshotRepository(settings.database_url),
        code_version_git_sha=settings.code_version_git_sha,
        policy_resolver=resolve_policy,
        fixture_resolver=resolve_fixture,
    )


def get_evaluation_workflow(request: Request) -> EvaluationWorkflow:
    return request.app.state.evaluation_workflow  # type: ignore[no-any-return]


EvaluationWorkflowDependency = Annotated[
    EvaluationWorkflow,
    Depends(get_evaluation_workflow),
]
Limit = Annotated[int, Query(ge=1, le=100)]

policy_router = APIRouter(prefix="/v1/evaluation-policies", tags=["evaluation"])
report_router = APIRouter(prefix="/v1/evaluation-reports", tags=["evaluation"])
outcome_router = APIRouter(prefix="/v1/evaluation-outcomes", tags=["evaluation"])


class EvaluationValidationIssue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    loc: list[str | int]
    msg: str
    type: str


class EvaluationValidationErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    detail: list[EvaluationValidationIssue]


EvaluationPolicyUnprocessableResponse = EvaluationBlockedResult | EvaluationValidationErrorResponse
EvaluationReportUnprocessableResponse = BlockedEvaluationOutcome | EvaluationValidationErrorResponse


def _blocked_response(exc: EvaluationWorkflowBlocked) -> JSONResponse:
    if exc.outcome is not None:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=jsonable_encoder(exc.outcome),
        )
    result = EvaluationBlockedResult.model_validate(
        {
            "promotion_state": exc.state,
            "reason_codes": exc.reason_codes,
            "sanitized_message": (
                "Phase 5 evaluation stopped because required evidence was unavailable."
            ),
        }
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=jsonable_encoder(result),
    )


def _domain_error(exc: Exception) -> HTTPException:
    if isinstance(
        exc,
        (
            EvaluationOutcomeNotFound,
            EvaluationPolicyNotFound,
            EvaluationReportNotFound,
            SnapshotNotFound,
        ),
    ):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The requested immutable evaluation resource was not found.",
        )
    if isinstance(exc, SnapshotAuthorization):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The persisted mapping does not authorize the required snapshot capability.",
        )
    if isinstance(exc, (EvaluationWorkflowConflict, SnapshotLineage)):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Immutable Phase 5 evaluation lineage conflicts with persisted evidence.",
        )
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="The immutable Phase 5 evaluation request could not be completed.",
    )


@policy_router.post(
    "",
    response_model=FrozenEvaluationPolicy,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": EvaluationPolicyUnprocessableResponse,
        },
    },
)
def create_evaluation_policy(
    payload: EvaluationPolicyCreateRequest,
    workflow: EvaluationWorkflowDependency,
) -> FrozenEvaluationPolicy | JSONResponse:
    try:
        return workflow.create_policy(payload)
    except EvaluationWorkflowBlocked as exc:
        return _blocked_response(exc)
    except EvaluationWorkflowConflict as exc:
        raise _domain_error(exc) from exc


@policy_router.get("", response_model=list[FrozenEvaluationPolicy])
def list_evaluation_policies(
    workflow: EvaluationWorkflowDependency,
    limit: Limit = 100,
) -> list[FrozenEvaluationPolicy]:
    return workflow.list_policies(limit=limit)


@policy_router.get(
    "/{policy_id}/versions/{policy_version}",
    response_model=FrozenEvaluationPolicy,
)
def get_evaluation_policy(
    policy_id: UUID,
    policy_version: int,
    workflow: EvaluationWorkflowDependency,
) -> FrozenEvaluationPolicy:
    try:
        return workflow.get_policy(policy_id, policy_version)
    except (EvaluationPolicyNotFound, EvaluationWorkflowConflict) as exc:
        raise _domain_error(exc) from exc


@report_router.post(
    "",
    response_model=EvaluationReport,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": EvaluationReportUnprocessableResponse,
        },
    },
)
def create_evaluation_report(
    payload: EvaluationRunCreateRequest,
    workflow: EvaluationWorkflowDependency,
) -> EvaluationReport | JSONResponse:
    try:
        return workflow.create_report(payload)
    except EvaluationWorkflowBlocked as exc:
        if exc.outcome is None:
            raise _domain_error(
                EvaluationWorkflowConflict("blocked report workflow omitted its immutable outcome")
            ) from exc
        return _blocked_response(exc)
    except (
        EvaluationPolicyNotFound,
        EvaluationReportNotFound,
        EvaluationWorkflowConflict,
        SnapshotAuthorization,
        SnapshotLineage,
        SnapshotNotFound,
    ) as exc:
        raise _domain_error(exc) from exc


@report_router.get("", response_model=list[EvaluationReportSummary])
def list_evaluation_reports(
    workflow: EvaluationWorkflowDependency,
    limit: Limit = 100,
) -> list[EvaluationReportSummary]:
    return workflow.list_reports(limit=limit)


@report_router.get("/{artifact_id}", response_model=EvaluationReport)
def get_evaluation_report(
    artifact_id: UUID,
    workflow: EvaluationWorkflowDependency,
) -> EvaluationReport:
    try:
        return workflow.get_report(artifact_id)
    except (EvaluationReportNotFound, EvaluationWorkflowConflict) as exc:
        raise _domain_error(exc) from exc


@outcome_router.get("", response_model=list[BlockedEvaluationOutcome])
def list_evaluation_outcomes(
    workflow: EvaluationWorkflowDependency,
    limit: Limit = 100,
) -> list[BlockedEvaluationOutcome]:
    return workflow.list_outcomes(limit=limit)


@outcome_router.get("/{outcome_id}", response_model=BlockedEvaluationOutcome)
def get_evaluation_outcome(
    outcome_id: UUID,
    workflow: EvaluationWorkflowDependency,
) -> BlockedEvaluationOutcome:
    try:
        return workflow.get_outcome(outcome_id)
    except EvaluationOutcomeNotFound as exc:
        raise _domain_error(exc) from exc


EvaluationWorkflowFactory = Callable[[Settings], EvaluationWorkflow]

__all__ = [
    "EvaluationWorkflowFactory",
    "default_evaluation_workflow_factory",
    "outcome_router",
    "policy_router",
    "report_router",
]
