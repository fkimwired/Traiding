from __future__ import annotations

import socket
from contextlib import AbstractContextManager
from unittest.mock import MagicMock, call

import pytest
from fable5_api.data_qualifications import (
    get_point_in_time_qualification,
    point_in_time_qualification_validation_error_handler,
    router,
)
from fable5_data.phase13.adapters import DeterministicMockPointInTimeQualificationAdapter
from fable5_data.phase13.contracts import (
    PointInTimeQualificationArtifact,
    PointInTimeQualificationCreateRequest,
)
from fable5_data.phase13.repository import (
    PointInTimeQualificationNotFound,
    PointInTimeQualificationRepository,
    PointInTimeQualificationRepositoryConflict,
)
from fable5_data.phase13.workflow import PointInTimeQualificationWorkflow
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient

CODE_SHA = "a" * 40
IDEMPOTENCY_KEY = "phase13-api-route-proof"


def _artifact() -> PointInTimeQualificationArtifact:
    creation = MagicMock()
    creation.find_by_idempotency_key.return_value = None
    creation.create_qualification.side_effect = lambda artifact: artifact
    serialized = MagicMock(spec=AbstractContextManager)
    serialized.__enter__.return_value = creation
    store = MagicMock()
    store.serialized_creation.return_value = serialized
    workflow = PointInTimeQualificationWorkflow(
        adapter=DeterministicMockPointInTimeQualificationAdapter(),
        store=store,
        phase13_code_version_git_sha=CODE_SHA,
    )
    return workflow.create_qualification(
        PointInTimeQualificationCreateRequest(qualification_idempotency_key=IDEMPOTENCY_KEY)
    )


def _client(repository: PointInTimeQualificationRepository) -> TestClient:
    app = FastAPI()
    app.state.point_in_time_qualification_repository = repository
    app.add_exception_handler(
        RequestValidationError,
        point_in_time_qualification_validation_error_handler,
    )
    app.include_router(router)
    return TestClient(app)


def test_qualification_route_delegates_only_the_historical_identity() -> None:
    artifact = _artifact()
    repository = MagicMock(spec=PointInTimeQualificationRepository)
    repository.get_qualification.return_value = artifact

    direct = get_point_in_time_qualification(artifact.qualification_id, repository)
    response = _client(repository).get(
        f"/v1/point-in-time-data-qualifications/{artifact.qualification_id}"
    )

    assert direct is artifact
    assert response.status_code == 200
    assert response.json() == artifact.model_dump(mode="json")
    assert repository.get_qualification.call_args_list == [
        call(artifact.qualification_id),
        call(artifact.qualification_id),
    ]
    repository.create_qualification.assert_not_called()
    repository.find_by_idempotency_key.assert_not_called()


@pytest.mark.parametrize(
    ("error", "status_code", "detail"),
    (
        (
            PointInTimeQualificationNotFound("secret missing evidence"),
            404,
            "The requested immutable Phase 13 point-in-time qualification evidence was not found.",
        ),
        (
            PointInTimeQualificationRepositoryConflict("secret persisted hash conflict"),
            409,
            "Immutable Phase 13 point-in-time qualification evidence conflicts with persisted "
            "lineage.",
        ),
    ),
)
def test_qualification_route_maps_sanitized_closed_errors(
    error: Exception,
    status_code: int,
    detail: str,
) -> None:
    repository = MagicMock(spec=PointInTimeQualificationRepository)
    repository.get_qualification.side_effect = error

    response = _client(repository).get(
        "/v1/point-in-time-data-qualifications/84433420-4725-4ceb-a575-662107009a6d"
    )

    assert response.status_code == status_code
    assert response.json() == {"detail": detail}
    assert "secret" not in response.text
    repository.create_qualification.assert_not_called()


def test_malformed_qualification_identity_uses_the_sanitized_typed_422() -> None:
    repository = MagicMock(spec=PointInTimeQualificationRepository)

    response = _client(repository).get("/v1/point-in-time-data-qualifications/not-a-secret-uuid")

    assert response.status_code == 422
    assert set(response.json()) == {"detail"}
    assert response.json()["detail"]
    assert all(set(issue) == {"loc", "msg", "type"} for issue in response.json()["detail"])
    assert "not-a-secret-uuid" not in response.text
    repository.get_qualification.assert_not_called()
    repository.create_qualification.assert_not_called()


def test_qualification_route_is_get_only_and_has_no_action_variant() -> None:
    repository = MagicMock(spec=PointInTimeQualificationRepository)
    client = _client(repository)
    path = "/v1/point-in-time-data-qualifications/84433420-4725-4ceb-a575-662107009a6d"

    for method in (client.post, client.put, client.patch, client.delete):
        assert method(path).status_code == 405
    for action in ("download", "refresh", "capture", "submit", "order"):
        assert client.post(f"{path}/{action}").status_code == 404
    repository.get_qualification.assert_not_called()
    repository.create_qualification.assert_not_called()


def test_api_path_performs_no_transport_or_database_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def deny_socket(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise AssertionError("Phase 13 historical GET attempted network access")

    monkeypatch.setattr(socket, "create_connection", deny_socket)
    artifact = _artifact()
    repository = MagicMock(spec=PointInTimeQualificationRepository)
    repository.get_qualification.return_value = artifact

    response = _client(repository).get(
        f"/v1/point-in-time-data-qualifications/{artifact.qualification_id}"
    )

    assert response.status_code == 200
    assert repository.method_calls == [call.get_qualification(artifact.qualification_id)]
