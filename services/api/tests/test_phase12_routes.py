from __future__ import annotations

import socket
from contextlib import AbstractContextManager
from unittest.mock import MagicMock, call

import pytest
from fable5_api.paper_shadow_readiness import (
    get_paper_shadow_readiness,
    paper_shadow_readiness_validation_error_handler,
    router,
)
from fable5_paper.phase12.adapters import DeterministicMockPaperBrokerAdapter
from fable5_paper.phase12.contracts import (
    PaperShadowReadinessArtifact,
    PaperShadowReadinessCreateRequest,
)
from fable5_paper.phase12.repository import (
    PaperShadowReadinessNotFound,
    PaperShadowReadinessRepository,
    PaperShadowReadinessRepositoryConflict,
)
from fable5_paper.phase12.workflow import PaperShadowReadinessWorkflow
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient

CODE_SHA = "a" * 40
IDEMPOTENCY_KEY = "phase12-api-route-proof"


def _artifact() -> PaperShadowReadinessArtifact:
    creation = MagicMock()
    creation.find_by_idempotency_key.return_value = None
    creation.create_readiness.side_effect = lambda artifact: artifact
    serialized = MagicMock(spec=AbstractContextManager)
    serialized.__enter__.return_value = creation
    store = MagicMock()
    store.serialized_creation.return_value = serialized
    workflow = PaperShadowReadinessWorkflow(
        adapter=DeterministicMockPaperBrokerAdapter(),
        store=store,
        phase12_code_version_git_sha=CODE_SHA,
    )
    return workflow.create_readiness(
        PaperShadowReadinessCreateRequest(readiness_idempotency_key=IDEMPOTENCY_KEY)
    )


def _client(repository: PaperShadowReadinessRepository) -> TestClient:
    app = FastAPI()
    app.state.paper_shadow_readiness_repository = repository
    app.add_exception_handler(
        RequestValidationError,
        paper_shadow_readiness_validation_error_handler,
    )
    app.include_router(router)
    return TestClient(app)


def test_readiness_route_delegates_only_the_historical_identity() -> None:
    artifact = _artifact()
    repository = MagicMock(spec=PaperShadowReadinessRepository)
    repository.get_readiness.return_value = artifact

    direct = get_paper_shadow_readiness(artifact.readiness_assessment_id, repository)
    response = _client(repository).get(
        f"/v1/paper-shadow-readiness/{artifact.readiness_assessment_id}"
    )

    assert direct is artifact
    assert response.status_code == 200
    assert response.json() == artifact.model_dump(mode="json")
    assert repository.get_readiness.call_args_list == [
        call(artifact.readiness_assessment_id),
        call(artifact.readiness_assessment_id),
    ]
    repository.create_readiness.assert_not_called()
    repository.find_by_idempotency_key.assert_not_called()


@pytest.mark.parametrize(
    ("error", "status_code", "detail"),
    (
        (
            PaperShadowReadinessNotFound("secret missing evidence"),
            404,
            "The requested immutable Phase 12 paper shadow-readiness evidence was not found.",
        ),
        (
            PaperShadowReadinessRepositoryConflict("secret persisted hash conflict"),
            409,
            "Immutable Phase 12 paper shadow-readiness evidence conflicts with persisted lineage.",
        ),
    ),
)
def test_readiness_route_maps_sanitized_closed_errors(
    error: Exception,
    status_code: int,
    detail: str,
) -> None:
    repository = MagicMock(spec=PaperShadowReadinessRepository)
    repository.get_readiness.side_effect = error

    response = _client(repository).get(
        "/v1/paper-shadow-readiness/84433420-4725-4ceb-a575-662107009a6d"
    )

    assert response.status_code == status_code
    assert response.json() == {"detail": detail}
    assert "secret" not in response.text
    repository.create_readiness.assert_not_called()


def test_malformed_readiness_identity_uses_the_sanitized_typed_422() -> None:
    repository = MagicMock(spec=PaperShadowReadinessRepository)

    response = _client(repository).get("/v1/paper-shadow-readiness/not-a-secret-uuid")

    assert response.status_code == 422
    assert set(response.json()) == {"detail"}
    assert response.json()["detail"]
    assert all(set(issue) == {"loc", "msg", "type"} for issue in response.json()["detail"])
    assert "not-a-secret-uuid" not in response.text
    repository.get_readiness.assert_not_called()
    repository.create_readiness.assert_not_called()


def test_readiness_route_is_get_only_and_has_no_action_variant() -> None:
    repository = MagicMock(spec=PaperShadowReadinessRepository)
    client = _client(repository)
    path = "/v1/paper-shadow-readiness/84433420-4725-4ceb-a575-662107009a6d"

    for method in (client.post, client.put, client.patch, client.delete):
        assert method(path).status_code == 405
    for action in ("download", "refresh", "submit", "order"):
        assert client.post(f"{path}/{action}").status_code == 404
    repository.get_readiness.assert_not_called()
    repository.create_readiness.assert_not_called()


def test_api_path_performs_no_transport_or_database_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def deny_socket(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise AssertionError("Phase 12 historical GET attempted network access")

    monkeypatch.setattr(socket, "create_connection", deny_socket)
    artifact = _artifact()
    repository = MagicMock(spec=PaperShadowReadinessRepository)
    repository.get_readiness.return_value = artifact

    response = _client(repository).get(
        f"/v1/paper-shadow-readiness/{artifact.readiness_assessment_id}"
    )

    assert response.status_code == 200
    assert repository.method_calls == [call.get_readiness(artifact.readiness_assessment_id)]
