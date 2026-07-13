from fable5_api.config import Settings
from fable5_api.main import create_app
from fable5_api.schemas import DependencyStatus
from fastapi.testclient import TestClient


def settings_factory() -> Settings:
    return Settings(_env_file=None)


def test_health_is_stable_liveness_contract() -> None:
    app = create_app(settings_factory, lambda _: DependencyStatus())
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {
        "status": "ok",
        "service": "api",
        "mode": "research-paper-only",
    }


def test_ready_reports_dependency_success() -> None:
    app = create_app(settings_factory, lambda _: DependencyStatus())
    response = TestClient(app).get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "service": "api",
        "dependencies": {"postgres": "ok", "redis": "ok"},
    }


def test_ready_fails_closed_without_exposing_internal_error() -> None:
    def unavailable(_: Settings) -> DependencyStatus:
        raise RuntimeError("connection secret must not leak")

    app = create_app(settings_factory, unavailable)
    response = TestClient(app).get("/ready")

    assert response.status_code == 503
    assert response.json() == {"detail": "A required platform dependency is unavailable."}
