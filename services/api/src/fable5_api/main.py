from collections.abc import Callable

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from fable5_api import __version__
from fable5_api.config import Settings, get_settings
from fable5_api.readiness import check_dependencies
from fable5_api.schemas import DependencyStatus, HealthResponse, ReadinessResponse


def create_app(
    settings_factory: Callable[[], Settings] = get_settings,
    dependency_checker: Callable[[Settings], DependencyStatus] = check_dependencies,
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
        allow_methods=["GET", "OPTIONS"],
        allow_headers=["*"],
    )

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
