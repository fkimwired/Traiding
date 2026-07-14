from collections.abc import Callable

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from fable5_api import __version__
from fable5_api.config import Settings, get_settings
from fable5_api.data_snapshots import (
    SnapshotWorkflowFactory,
    default_snapshot_workflow_factory,
)
from fable5_api.data_snapshots import router as data_snapshot_router
from fable5_api.evaluations import (
    EvaluationWorkflowFactory,
    default_evaluation_workflow_factory,
)
from fable5_api.evaluations import (
    outcome_router as evaluation_outcome_router,
)
from fable5_api.evaluations import (
    policy_router as evaluation_policy_router,
)
from fable5_api.evaluations import (
    report_router as evaluation_report_router,
)
from fable5_api.idea_intake import WorkflowFactory, default_workflow_factory, router
from fable5_api.mappings import (
    MappingWorkflowFactory,
    default_mapping_workflow_factory,
)
from fable5_api.mappings import (
    router as mapping_router,
)
from fable5_api.readiness import check_dependencies
from fable5_api.research import (
    ResearchWorkflowFactory,
    default_research_workflow_factory,
)
from fable5_api.research import router as research_router
from fable5_api.schemas import DependencyStatus, HealthResponse, ReadinessResponse


def create_app(
    settings_factory: Callable[[], Settings] = get_settings,
    dependency_checker: Callable[[Settings], DependencyStatus] = check_dependencies,
    workflow_factory: WorkflowFactory = default_workflow_factory,
    mapping_workflow_factory: MappingWorkflowFactory = default_mapping_workflow_factory,
    snapshot_workflow_factory: SnapshotWorkflowFactory = default_snapshot_workflow_factory,
    evaluation_workflow_factory: EvaluationWorkflowFactory = (default_evaluation_workflow_factory),
    research_workflow_factory: ResearchWorkflowFactory = default_research_workflow_factory,
) -> FastAPI:
    settings = settings_factory()
    app = FastAPI(
        title="Fable5 Research API",
        version=__version__,
        description="Research-to-paper-trading platform API. No live execution path exists.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )
    app.state.idea_intake_workflow = workflow_factory(settings)
    app.state.mapping_workflow = mapping_workflow_factory(settings)
    app.state.snapshot_workflow = snapshot_workflow_factory(settings)
    app.state.evaluation_workflow = evaluation_workflow_factory(settings)
    app.state.research_workflow = research_workflow_factory(settings)
    app.include_router(router)
    app.include_router(mapping_router)
    app.include_router(data_snapshot_router)
    app.include_router(evaluation_policy_router)
    app.include_router(evaluation_report_router)
    app.include_router(evaluation_outcome_router)
    app.include_router(research_router)

    @app.get("/health", response_model=HealthResponse, tags=["system"])
    def health() -> HealthResponse:
        return HealthResponse()

    @app.get(
        "/ready",
        response_model=ReadinessResponse,
        tags=["system"],
        responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Dependency unavailable"}},
    )
    def ready() -> ReadinessResponse:
        try:
            dependencies = dependency_checker(settings)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="A required platform dependency is unavailable.",
            ) from exc
        return ReadinessResponse(dependencies=dependencies)

    return app


app = create_app()
