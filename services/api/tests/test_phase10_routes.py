from __future__ import annotations

from typing import cast
from unittest.mock import MagicMock
from uuid import UUID

import fable5_api.local_simulations as simulations_module
import pytest
from fable5_api.config import Settings
from fable5_api.local_simulations import (
    PaperSimulationConflictErrorResponse,
    PaperSimulationNotFoundErrorResponse,
    create_local_simulation,
    default_paper_simulation_workflow_factory,
    get_local_simulation,
    list_local_simulations,
    paper_simulation_validation_error_handler,
    router,
)
from fable5_paper.contracts import (
    PaperSimulationArtifact,
    PaperSimulationCreateRequest,
    PaperSimulationSummary,
)
from fable5_paper.repository import PaperArtifactNotFound, PaperRepositoryConflict
from fable5_paper.workflow import (
    PaperEvidenceNotFound,
    PaperSimulationWorkflow,
    PaperWorkflowConflict,
)
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient

ASSESSMENT_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
SIMULATION_ID = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
VALID_REQUEST = PaperSimulationCreateRequest(
    approval_assessment_id=ASSESSMENT_ID,
    simulation_idempotency_key="phase10-api-route-key",
)


def _client(workflow: PaperSimulationWorkflow) -> TestClient:
    app = FastAPI()
    app.state.paper_simulation_workflow = workflow
    app.add_exception_handler(RequestValidationError, paper_simulation_validation_error_handler)
    app.include_router(router)
    return TestClient(app)


def test_default_factory_uses_exact_phase6_phase7_and_paper_repositories(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        database_url="postgresql+psycopg://phase10:phase10@localhost/phase10",
        code_version_git_sha="a" * 40,
    )
    research_repository = object()
    risk_repository = object()
    paper_repository = object()
    evidence_gateway = object()
    workflow = object()
    research_factory = MagicMock(return_value=research_repository)
    risk_factory = MagicMock(return_value=risk_repository)
    paper_factory = MagicMock(return_value=paper_repository)
    gateway_factory = MagicMock(return_value=evidence_gateway)
    workflow_factory = MagicMock(return_value=workflow)
    monkeypatch.setattr(simulations_module, "ResearchRepository", research_factory)
    monkeypatch.setattr(simulations_module, "RiskRepository", risk_factory)
    monkeypatch.setattr(simulations_module, "PaperRepository", paper_factory)
    monkeypatch.setattr(simulations_module, "PostgresPaperEvidenceGateway", gateway_factory)
    monkeypatch.setattr(simulations_module, "PaperSimulationWorkflow", workflow_factory)

    created = default_paper_simulation_workflow_factory(settings)

    assert created is workflow
    research_factory.assert_called_once_with(settings.database_url)
    risk_factory.assert_called_once_with(settings.database_url)
    paper_factory.assert_called_once_with(settings.database_url)
    gateway_factory.assert_called_once_with(research_repository, risk_repository)
    workflow_factory.assert_called_once_with(
        evidence=evidence_gateway,
        simulations=paper_repository,
        phase10_code_version_git_sha="a" * 40,
    )


def test_endpoints_delegate_only_typed_reference_idempotency_and_filters() -> None:
    artifact = cast(PaperSimulationArtifact, object())
    summary = cast(PaperSimulationSummary, object())
    workflow = MagicMock(spec=PaperSimulationWorkflow)
    workflow.create_simulation.return_value = artifact
    workflow.get_simulation.return_value = artifact
    workflow.list_simulations.return_value = [summary]

    created = create_local_simulation(VALID_REQUEST, workflow)
    found = get_local_simulation(SIMULATION_ID, workflow)
    listed = list_local_simulations(
        workflow,
        approval_assessment_id=ASSESSMENT_ID,
        limit=7,
    )

    assert created is artifact
    assert found is artifact
    assert listed == [summary]
    workflow.create_simulation.assert_called_once_with(VALID_REQUEST)
    workflow.get_simulation.assert_called_once_with(SIMULATION_ID)
    workflow.list_simulations.assert_called_once_with(
        source_assessment_id=ASSESSMENT_ID,
        limit=7,
    )


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("artifact_sha256", "0" * 64),
        ("checks", []),
        ("created_at_utc", "2026-07-16T00:00:00Z"),
        ("decision_time_utc", "2026-07-16T00:00:00Z"),
        ("ledger_entries", []),
        ("outcome", "SIMULATED_COMPLETE"),
        ("price", "100"),
        ("quantity", "5"),
        ("reason_codes", []),
        ("risk_override", True),
        ("side", "secret-buy-authority"),
        ("signal", "secret-client-signal"),
        ("symbol", "SECRET"),
    ),
)
def test_create_rejects_client_authority_with_sanitized_typed_422(
    field: str,
    value: object,
) -> None:
    workflow = MagicMock(spec=PaperSimulationWorkflow)
    payload = {**VALID_REQUEST.model_dump(mode="json"), field: value}

    response = _client(workflow).post("/v1/local-simulations", json=payload)

    assert response.status_code == 422
    assert set(response.json()) == {"detail"}
    assert response.json()["detail"]
    assert all(set(issue) == {"loc", "msg", "type"} for issue in response.json()["detail"])
    assert response.json()["detail"][0]["loc"][-1] == field
    assert "secret-buy-authority" not in response.text
    assert "secret-client-signal" not in response.text
    workflow.create_simulation.assert_not_called()


def test_malformed_references_keys_and_list_bounds_are_sanitized() -> None:
    workflow = MagicMock(spec=PaperSimulationWorkflow)
    client = _client(workflow)
    responses = (
        client.post(
            "/v1/local-simulations",
            json={
                "approval_assessment_id": "not-a-uuid",
                "simulation_idempotency_key": "q7x9z",
            },
        ),
        client.get("/v1/local-simulations/not-a-uuid"),
        client.get("/v1/local-simulations?approval_assessment_id=not-a-uuid"),
        client.get("/v1/local-simulations?limit=0"),
        client.get("/v1/local-simulations?limit=101"),
    )

    for response in responses:
        assert response.status_code == 422
        assert set(response.json()) == {"detail"}
        assert response.json()["detail"]
        assert all(set(issue) == {"loc", "msg", "type"} for issue in response.json()["detail"])
        assert "not-a-uuid" not in response.text
        assert "q7x9z" not in response.text
    workflow.create_simulation.assert_not_called()
    workflow.get_simulation.assert_not_called()
    workflow.list_simulations.assert_not_called()


def test_missing_and_conflicting_requests_return_sanitized_closed_errors() -> None:
    workflow = MagicMock(spec=PaperSimulationWorkflow)
    workflow.create_simulation.side_effect = PaperEvidenceNotFound("secret missing source identity")
    workflow.get_simulation.side_effect = PaperArtifactNotFound(
        "secret missing simulation identity"
    )
    client = _client(workflow)

    missing_source = client.post(
        "/v1/local-simulations",
        json=VALID_REQUEST.model_dump(mode="json"),
    )
    missing_simulation = client.get(f"/v1/local-simulations/{SIMULATION_ID}")
    workflow.list_simulations.side_effect = PaperRepositoryConflict(
        "secret persisted list conflict"
    )
    conflict = client.get("/v1/local-simulations")

    assert missing_source.status_code == 404
    assert missing_source.json() == {
        "detail": "The requested immutable Phase 10 simulation evidence was not found."
    }
    assert missing_simulation.status_code == 404
    assert missing_simulation.json() == missing_source.json()
    assert conflict.status_code == 409
    assert conflict.json() == {
        "detail": "Immutable Phase 10 simulation evidence conflicts with persisted lineage."
    }
    assert PaperSimulationNotFoundErrorResponse.model_validate(missing_source.json()).detail == (
        "The requested immutable Phase 10 simulation evidence was not found."
    )
    assert PaperSimulationConflictErrorResponse.model_validate(conflict.json()).detail == (
        "Immutable Phase 10 simulation evidence conflicts with persisted lineage."
    )
    combined = missing_source.text + missing_simulation.text + conflict.text
    assert "secret missing source identity" not in combined
    assert "secret missing simulation identity" not in combined
    assert "secret persisted list conflict" not in combined


def test_idempotency_or_lineage_conflict_is_sanitized_and_not_misreported_as_success() -> None:
    workflow = MagicMock(spec=PaperSimulationWorkflow)
    workflow.create_simulation.side_effect = PaperWorkflowConflict(
        "secret idempotency key belongs to different evidence"
    )

    response = _client(workflow).post(
        "/v1/local-simulations",
        json=VALID_REQUEST.model_dump(mode="json"),
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Immutable Phase 10 simulation evidence conflicts with persisted lineage."
    }
    assert "secret idempotency key" not in response.text


def test_phase10_api_exposes_no_update_delete_or_action_route() -> None:
    workflow = MagicMock(spec=PaperSimulationWorkflow)
    client = _client(workflow)
    paths = (
        "/v1/local-simulations",
        f"/v1/local-simulations/{SIMULATION_ID}",
    )

    for path in paths:
        for method in (client.put, client.patch, client.delete):
            assert method(path).status_code == 405
    for action in ("cancel", "execute", "submit"):
        assert client.post(f"/v1/local-simulations/{SIMULATION_ID}/{action}").status_code == 404
