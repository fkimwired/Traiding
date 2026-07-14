from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from fable5_api.research import router
from fable5_backtester.contracts import PromotionState
from fable5_backtester.engine import evaluate_synthetic_fixture
from fable5_data.contracts import (
    AUTHORIZED_CAPABILITIES,
    AuthorizedMappingIdentity,
    SnapshotBundle,
    SnapshotRequestParameters,
)
from fable5_data.phase6_synthetic import (
    PHASE6_SYNTHETIC_MOCK_CONFIGURATION,
    resolve_phase6_synthetic_adapter,
)
from fable5_data.quality import QualityAcceptedResult, run_mandatory_data_quality
from fable5_data.snapshots import SnapshotCandidate, build_snapshot_candidate
from fable5_mapping.models import CanonicalFamily, ResearchVerdict
from fable5_research.artifacts import build_research_artifact
from fable5_research.contracts import (
    ResearchConfigurationId,
    ResearchRunArtifact,
    ResearchRunCreateRequest,
)
from fable5_research.phase5 import build_phase5_inputs
from fable5_research.preparation import prepare_research_pipeline
from fable5_research.repository import ResearchRunNotFound
from fable5_research.workflow import ResearchWorkflow, ResearchWorkflowBlocked
from fastapi import FastAPI
from fastapi.testclient import TestClient

MAPPING_ID = UUID("aaaaaaaa-aaaa-5aaa-8aaa-aaaaaaaaaaaa")
SNAPSHOT_ID = UUID("bbbbbbbb-bbbb-5bbb-8bbb-bbbbbbbbbbbb")
MISSING_ID = UUID("ffffffff-ffff-5fff-8fff-ffffffffffff")
OFFICIAL_SOURCE_VERSION_ID = UUID("cccccccc-cccc-5ccc-8ccc-cccccccccccc")
AS_OF = datetime(2026, 7, 14, tzinfo=UTC)
CODE_VERSION = "a" * 40


def _client(workflow: ResearchWorkflow) -> TestClient:
    app = FastAPI()
    app.state.research_workflow = workflow
    app.include_router(router)
    return TestClient(app)


def _payload() -> dict[str, object]:
    return {
        "mapping_id": str(MAPPING_ID),
        "snapshot_ids": [str(SNAPSHOT_ID)],
        "research_configuration_id": ResearchConfigurationId.C_FAIL.value,
    }


@pytest.fixture(scope="module")
def completed_artifact() -> ResearchRunArtifact:
    mapping = AuthorizedMappingIdentity(
        mapping_id=MAPPING_ID,
        mapping_version=1,
        mapping_input_sha256="1" * 64,
        mapper_rule_set_version="phase6-api-test-rules-v1",
        mapper_rule_set_sha256="2" * 64,
        canonical_family=CanonicalFamily.C_OFFICIAL_EVENT_TEXT_OVERLAY,
        verdict=ResearchVerdict.BUILD_RESEARCH,
        official_corroboration_source_version_ids=(OFFICIAL_SOURCE_VERSION_ID,),
    )
    adapter, quality_catalog = resolve_phase6_synthetic_adapter(mapping)
    snapshots: list[SnapshotBundle] = []
    for capability in sorted(AUTHORIZED_CAPABILITIES[mapping.canonical_family], key=str):
        request = SnapshotRequestParameters(
            mapping=mapping,
            as_of_utc=AS_OF,
            capability=capability,
            mock_configuration_id=PHASE6_SYNTHETIC_MOCK_CONFIGURATION.configuration_id,
        )
        result = adapter.fetch(request.capability)
        quality = run_mandatory_data_quality(
            request=request,
            result=result,
            configuration=PHASE6_SYNTHETIC_MOCK_CONFIGURATION,
            catalog=quality_catalog,
        )
        assert isinstance(quality, QualityAcceptedResult)
        candidate = build_snapshot_candidate(
            mapping=mapping,
            request=request,
            profile=result.profile,
            configuration=PHASE6_SYNTHETIC_MOCK_CONFIGURATION,
            batch=quality.batch,
            created_at_utc=AS_OF,
        )
        assert isinstance(candidate, SnapshotCandidate)
        snapshots.append(candidate.bundle)
    snapshot_tuple = tuple(snapshots)
    prepared = prepare_research_pipeline(ResearchConfigurationId.C_PASS, snapshot_tuple)
    policy, fixture = build_phase5_inputs(
        configuration_id=ResearchConfigurationId.C_PASS,
        prepared=prepared,
        snapshots=snapshot_tuple,
    )
    report = evaluate_synthetic_fixture(
        policy=policy,
        fixture=fixture,
        mapping=mapping,
        snapshots=snapshot_tuple,
        code_version_git_sha=CODE_VERSION,
        created_at_utc=AS_OF,
    )
    return build_research_artifact(
        configuration_id=ResearchConfigurationId.C_PASS,
        mapping=mapping,
        prepared=prepared,
        report=report,
    )


def test_create_returns_complete_explainable_research_artifact(
    completed_artifact: ResearchRunArtifact,
) -> None:
    workflow = MagicMock(spec=ResearchWorkflow)
    workflow.create_run.return_value = completed_artifact
    payload = {
        **_payload(),
        "research_configuration_id": ResearchConfigurationId.C_PASS.value,
    }

    response = _client(workflow).post("/v1/research-runs", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["run_id"] == str(completed_artifact.run_id)
    assert body["artifact_sha256"] == completed_artifact.artifact_sha256
    assert body["phase5_evaluation"]["promotion_state"] == "PASS_RESEARCH"
    assert body["family_evidence"]["llm_is_extraction_only"] is True
    corroboration = body["family_evidence"]["corroborations"][0]
    assert corroboration["exact_match"] is True
    assert corroboration["contributes_standalone"] is False
    assert corroboration["social_source_reference"]["record_type"] == "social_attention"
    assert corroboration["official_source_reference"]["record_type"] == "official_document_content"
    assert body["paper_approval_granted"] is False
    assert body["no_real_performance_claimed"] is True
    forbidden_extraction_fields = {
        "label",
        "signal",
        "model_decision",
        "buy_sell_call",
        "allocation",
        "position_size",
        "promotion_outcome",
        "execution_instruction",
    }
    for extraction in body["family_evidence"]["extractions"]:
        assert not forbidden_extraction_fields.intersection(extraction)


def test_create_delegates_only_typed_server_resolvable_identities() -> None:
    workflow = MagicMock(spec=ResearchWorkflow)
    workflow.create_run.side_effect = ResearchWorkflowBlocked(
        PromotionState.BLOCKED_MISSING_POLICY,
        ("official_corroboration_required",),
    )

    response = _client(workflow).post("/v1/research-runs", json=_payload())

    assert response.status_code == 422
    assert response.json() == {
        "promotion_state": "BLOCKED_MISSING_POLICY",
        "reason_codes": ["official_corroboration_required"],
        "sanitized_message": (
            "Phase 6 research stopped because authoritative immutable evidence was unavailable."
        ),
    }
    request = workflow.create_run.call_args.args[0]
    assert request == ResearchRunCreateRequest(
        mapping_id=MAPPING_ID,
        snapshot_ids=(SNAPSHOT_ID,),
        research_configuration_id=ResearchConfigurationId.C_FAIL,
    )


def test_create_rejects_client_supplied_metrics_hashes_thresholds_times_and_verdicts() -> None:
    workflow = MagicMock(spec=ResearchWorkflow)
    payload = {
        **_payload(),
        "metrics": {},
        "artifact_sha256": "0" * 64,
        "thresholds": {},
        "created_at_utc": "2026-07-14T00:00:00Z",
        "trials": [],
        "trial_results": [],
        "promotion_state": "PASS_RESEARCH",
        "verdict": "BUILD_RESEARCH",
    }

    response = _client(workflow).post("/v1/research-runs", json=payload)

    assert response.status_code == 422
    workflow.create_run.assert_not_called()


def test_get_missing_run_is_sanitized_404_and_list_is_read_only() -> None:
    workflow = MagicMock(spec=ResearchWorkflow)
    workflow.get_run.side_effect = ResearchRunNotFound("internal identity details")
    workflow.list_runs.return_value = []
    client = _client(workflow)

    detail = client.get(f"/v1/research-runs/{MISSING_ID}")
    listing = client.get("/v1/research-runs?limit=7")

    assert detail.status_code == 404
    assert detail.json() == {
        "detail": "The requested immutable Phase 6 research run was not found."
    }
    assert "internal identity details" not in detail.text
    assert listing.status_code == 200
    assert listing.json() == []
    workflow.get_run.assert_called_once_with(MISSING_ID)
    workflow.list_runs.assert_called_once_with(limit=7)


def test_research_api_exposes_no_update_delete_or_execution_method() -> None:
    workflow = MagicMock(spec=ResearchWorkflow)
    client = _client(workflow)

    for path in ("/v1/research-runs", f"/v1/research-runs/{MISSING_ID}"):
        for method in (client.put, client.patch, client.delete):
            assert method(path).status_code == 405
    assert client.post("/v1/research-runs/live", json={}).status_code in {404, 405, 422}
    workflow.create_run.assert_not_called()
