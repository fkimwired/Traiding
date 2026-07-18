from __future__ import annotations

import socket
from contextlib import AbstractContextManager
from unittest.mock import MagicMock, call

import pytest
from fable5_api.research_ingestion_eligibility import (
    get_research_ingestion_eligibility,
    research_ingestion_eligibility_validation_error_handler,
    router,
)
from fable5_data.phase13.adapters import DeterministicMockPointInTimeQualificationAdapter
from fable5_data.phase13.contracts import (
    PointInTimeQualificationArtifact,
    PointInTimeQualificationCreateRequest,
)
from fable5_data.phase13.workflow import PointInTimeQualificationWorkflow
from fable5_data.phase14.contracts import (
    ResearchIngestionEligibilityArtifact,
    ResearchIngestionEligibilityCreateRequest,
)
from fable5_data.phase14.repository import (
    ResearchIngestionEligibilityNotFound,
    ResearchIngestionEligibilityRepository,
    ResearchIngestionEligibilityRepositoryConflict,
)
from fable5_data.phase14.workflow import ResearchIngestionEligibilityWorkflow
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient

CODE_SHA = "a" * 40


def _phase13_artifact() -> PointInTimeQualificationArtifact:
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
        PointInTimeQualificationCreateRequest(
            qualification_idempotency_key="phase14-api-source-proof"
        )
    )


def _artifact() -> ResearchIngestionEligibilityArtifact:
    source_artifact = _phase13_artifact()
    source = MagicMock()
    source.get_qualification.return_value = source_artifact
    creation = MagicMock()
    creation.find_by_idempotency_key.return_value = None
    creation.find_by_request_fingerprint.return_value = None
    creation.create_assessment.side_effect = lambda artifact: artifact
    serialized = MagicMock(spec=AbstractContextManager)
    serialized.__enter__.return_value = creation
    store = MagicMock()
    store.serialized_creation.return_value = serialized
    workflow = ResearchIngestionEligibilityWorkflow(
        qualification_source=source,
        store=store,
        phase14_code_version_git_sha=CODE_SHA,
    )
    return workflow.create_assessment(
        ResearchIngestionEligibilityCreateRequest(
            assessment_idempotency_key="phase14-api-route-proof",
            qualification_id=source_artifact.qualification_id,
        )
    )


def _client(repository: ResearchIngestionEligibilityRepository) -> TestClient:
    app = FastAPI()
    app.state.research_ingestion_eligibility_repository = repository
    app.add_exception_handler(
        RequestValidationError,
        research_ingestion_eligibility_validation_error_handler,
    )
    app.include_router(router)
    return TestClient(app)


def test_eligibility_route_delegates_only_the_historical_identity() -> None:
    artifact = _artifact()
    repository = MagicMock(spec=ResearchIngestionEligibilityRepository)
    repository.get_assessment.return_value = artifact

    direct = get_research_ingestion_eligibility(artifact.assessment_id, repository)
    response = _client(repository).get(
        f"/v1/research-ingestion-eligibility/{artifact.assessment_id}"
    )

    assert direct is artifact
    assert response.status_code == 200
    assert response.json() == artifact.model_dump(mode="json")
    assert repository.get_assessment.call_args_list == [
        call(artifact.assessment_id),
        call(artifact.assessment_id),
    ]
    repository.create_assessment.assert_not_called()
    repository.find_by_idempotency_key.assert_not_called()


@pytest.mark.parametrize(
    ("error", "status_code", "detail"),
    (
        (
            ResearchIngestionEligibilityNotFound("secret missing evidence"),
            404,
            "The requested immutable Phase 14 research-ingestion eligibility evidence was not "
            "found.",
        ),
        (
            ResearchIngestionEligibilityRepositoryConflict("secret persisted hash conflict"),
            409,
            "Immutable Phase 14 research-ingestion eligibility evidence conflicts with persisted "
            "lineage.",
        ),
    ),
)
def test_eligibility_route_maps_sanitized_closed_errors(
    error: Exception,
    status_code: int,
    detail: str,
) -> None:
    repository = MagicMock(spec=ResearchIngestionEligibilityRepository)
    repository.get_assessment.side_effect = error

    response = _client(repository).get(
        "/v1/research-ingestion-eligibility/84433420-4725-4ceb-a575-662107009a6d"
    )

    assert response.status_code == status_code
    assert response.json() == {"detail": detail}
    assert "secret" not in response.text
    repository.create_assessment.assert_not_called()


def test_malformed_eligibility_identity_uses_the_sanitized_typed_422() -> None:
    repository = MagicMock(spec=ResearchIngestionEligibilityRepository)

    response = _client(repository).get("/v1/research-ingestion-eligibility/not-a-secret-uuid")

    assert response.status_code == 422
    assert set(response.json()) == {"detail"}
    assert response.json()["detail"]
    assert all(set(issue) == {"loc", "msg", "type"} for issue in response.json()["detail"])
    assert "not-a-secret-uuid" not in response.text
    repository.get_assessment.assert_not_called()
    repository.create_assessment.assert_not_called()


def test_eligibility_route_is_get_only_and_has_no_action_variant() -> None:
    repository = MagicMock(spec=ResearchIngestionEligibilityRepository)
    client = _client(repository)
    path = "/v1/research-ingestion-eligibility/84433420-4725-4ceb-a575-662107009a6d"

    for method in (client.post, client.put, client.patch, client.delete):
        assert method(path).status_code == 405
    for action in ("download", "refresh", "assess", "ingest", "promote", "submit", "order"):
        assert client.post(f"{path}/{action}").status_code == 404
    repository.get_assessment.assert_not_called()
    repository.create_assessment.assert_not_called()


def test_api_path_performs_no_transport_or_database_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def deny_socket(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise AssertionError("Phase 14 historical GET attempted network access")

    monkeypatch.setattr(socket, "create_connection", deny_socket)
    artifact = _artifact()
    repository = MagicMock(spec=ResearchIngestionEligibilityRepository)
    repository.get_assessment.return_value = artifact

    response = _client(repository).get(
        f"/v1/research-ingestion-eligibility/{artifact.assessment_id}"
    )

    assert response.status_code == 200
    assert repository.method_calls == [call.get_assessment(artifact.assessment_id)]
