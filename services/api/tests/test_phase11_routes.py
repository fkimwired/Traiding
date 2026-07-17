from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, call
from uuid import UUID

import pytest
from fable5_api.local_simulations import (
    evidence_router,
    get_local_simulation_evidence_bundle,
    paper_simulation_validation_error_handler,
)
from fable5_paper.contracts import PaperSimulationArtifact
from fable5_paper.evidence import build_local_simulation_evidence_bundle
from fable5_paper.repository import PaperArtifactNotFound, PaperRepositoryConflict
from fable5_paper.workflow import PaperSimulationWorkflow, PaperWorkflowConflict
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "services/frontend/e2e/fixtures/phase10-completed.json"
SIMULATION_ID = UUID("8e7775be-40ff-5c14-abdb-dca990f8a001")


def _bundle():
    artifact = PaperSimulationArtifact.model_validate(
        json.loads(FIXTURE.read_text(encoding="utf-8"))
    )
    return build_local_simulation_evidence_bundle(artifact)


def _client(workflow: PaperSimulationWorkflow) -> TestClient:
    app = FastAPI()
    app.state.paper_simulation_workflow = workflow
    app.add_exception_handler(RequestValidationError, paper_simulation_validation_error_handler)
    app.include_router(evidence_router)
    return TestClient(app)


def test_evidence_route_delegates_only_the_simulation_identity() -> None:
    bundle = _bundle()
    workflow = MagicMock(spec=PaperSimulationWorkflow)
    workflow.get_simulation_evidence_bundle.return_value = bundle

    direct = get_local_simulation_evidence_bundle(SIMULATION_ID, workflow)
    response = _client(workflow).get(f"/v1/local-simulations/{SIMULATION_ID}/evidence-bundle")

    assert direct is bundle
    assert response.status_code == 200
    assert response.json() == bundle.model_dump(mode="json")
    assert workflow.get_simulation_evidence_bundle.call_args_list == [
        call(SIMULATION_ID),
        call(SIMULATION_ID),
    ]
    workflow.create_simulation.assert_not_called()
    workflow.get_simulation.assert_not_called()
    workflow.list_simulations.assert_not_called()


@pytest.mark.parametrize(
    ("error", "status_code", "detail"),
    (
        (
            PaperArtifactNotFound("secret missing evidence"),
            404,
            "The requested immutable Phase 10 simulation evidence was not found.",
        ),
        (
            PaperRepositoryConflict("secret persisted hash conflict"),
            409,
            "Immutable Phase 10 simulation evidence conflicts with persisted lineage.",
        ),
        (
            PaperWorkflowConflict("secret projection conflict"),
            409,
            "Immutable Phase 10 simulation evidence conflicts with persisted lineage.",
        ),
    ),
)
def test_evidence_route_maps_sanitized_closed_errors(
    error: Exception,
    status_code: int,
    detail: str,
) -> None:
    workflow = MagicMock(spec=PaperSimulationWorkflow)
    workflow.get_simulation_evidence_bundle.side_effect = error

    response = _client(workflow).get(f"/v1/local-simulations/{SIMULATION_ID}/evidence-bundle")

    assert response.status_code == status_code
    assert response.json() == {"detail": detail}
    assert "secret" not in response.text


def test_malformed_evidence_identity_uses_the_sanitized_typed_422() -> None:
    workflow = MagicMock(spec=PaperSimulationWorkflow)

    response = _client(workflow).get("/v1/local-simulations/not-a-secret-uuid/evidence-bundle")

    assert response.status_code == 422
    assert set(response.json()) == {"detail"}
    assert response.json()["detail"]
    assert all(set(issue) == {"loc", "msg", "type"} for issue in response.json()["detail"])
    assert "not-a-secret-uuid" not in response.text
    workflow.get_simulation_evidence_bundle.assert_not_called()


def test_evidence_route_is_get_only_and_has_no_action_variant() -> None:
    workflow = MagicMock(spec=PaperSimulationWorkflow)
    client = _client(workflow)
    path = f"/v1/local-simulations/{SIMULATION_ID}/evidence-bundle"

    for method in (client.post, client.put, client.patch, client.delete):
        assert method(path).status_code == 405
    for action in ("download", "refresh", "submit"):
        assert client.post(f"{path}/{action}").status_code == 404
    workflow.get_simulation_evidence_bundle.assert_not_called()
