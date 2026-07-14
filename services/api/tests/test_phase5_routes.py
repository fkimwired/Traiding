from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from fable5_api.evaluations import outcome_router, policy_router, report_router
from fable5_backtester.contracts import (
    EvaluationPolicyCreateRequest,
    EvaluationReport,
    EvaluationReportSummary,
    EvaluationRunCreateRequest,
    PromotionState,
)
from fable5_backtester.engine import evaluate_synthetic_fixture
from fable5_backtester.outcomes import (
    BlockedEvaluationOutcome,
    BlockedFailureStage,
    EvaluationOutcomeNotFound,
    build_blocked_evaluation_outcome,
)
from fable5_backtester.synthetic import REGISTERED_FIXTURE, REGISTERED_POLICY
from fable5_backtester.workflow import (
    EvaluationPolicyNotFound,
    EvaluationReportNotFound,
    EvaluationWorkflow,
    EvaluationWorkflowBlocked,
    EvaluationWorkflowConflict,
)
from fable5_data.contracts import (
    AuthorizedMappingIdentity,
    DataCapability,
    SnapshotRequestParameters,
)
from fable5_data.quality import (
    QualityAcceptedResult,
    QualityReferenceCatalog,
    run_mandatory_data_quality,
)
from fable5_data.repository import SnapshotLineage, SnapshotNotFound
from fable5_data.snapshots import SnapshotCandidate, build_snapshot_candidate
from fable5_data.synthetic import (
    SYNTHETIC_MOCK_CONFIGURATION,
    SyntheticPointInTimeAdapter,
)
from fable5_mapping.models import CanonicalFamily, ResearchVerdict
from fastapi import FastAPI
from fastapi.testclient import TestClient

MAPPING_ID = UUID("aaaaaaaa-aaaa-5aaa-8aaa-aaaaaaaaaaaa")
OHLCV_SNAPSHOT_ID = UUID("bbbbbbbb-bbbb-5bbb-8bbb-bbbbbbbbbbbb")
MEMBERSHIP_SNAPSHOT_ID = UUID("cccccccc-cccc-5ccc-8ccc-cccccccccccc")
SNAPSHOT_IDS = (OHLCV_SNAPSHOT_ID, MEMBERSHIP_SNAPSHOT_ID)
MISSING_ID = UUID("ffffffff-ffff-5fff-8fff-ffffffffffff")
AS_OF = datetime(2026, 7, 12, tzinfo=UTC)
CREATED_AT = datetime(2026, 7, 13, 20, 30, tzinfo=UTC)
CODE_VERSION = "a" * 40
MEMBERSHIP_OBSERVATION_ID = "62b27683-7bac-5713-81db-6ea3a0aeb40e"


def _client(workflow: EvaluationWorkflow) -> TestClient:
    app = FastAPI()
    app.state.evaluation_workflow = workflow
    app.include_router(policy_router)
    app.include_router(report_router)
    app.include_router(outcome_router)
    return TestClient(app)


def _policy_payload() -> dict[str, object]:
    return {
        "policy_id": str(REGISTERED_POLICY.policy_id),
        "policy_version": REGISTERED_POLICY.policy_version,
    }


def _report_payload() -> dict[str, object]:
    return {
        "policy_id": str(REGISTERED_POLICY.policy_id),
        "policy_version": REGISTERED_POLICY.policy_version,
        "mapping_id": str(MAPPING_ID),
        "snapshot_ids": [str(snapshot_id) for snapshot_id in SNAPSHOT_IDS],
        "fixture_id": REGISTERED_FIXTURE.fixture_id,
    }


def _blocked_outcome() -> BlockedEvaluationOutcome:
    return build_blocked_evaluation_outcome(
        request=EvaluationRunCreateRequest.model_validate(_report_payload()),
        promotion_state=PromotionState.BLOCKED_UNCOMPUTABLE,
        reason_codes=("required_snapshot_missing",),
        failure_stage=BlockedFailureStage.SNAPSHOT_RESOLUTION,
        code_version_git_sha=CODE_VERSION,
        policy=REGISTERED_POLICY,
        fixture=REGISTERED_FIXTURE,
        created_at_utc=CREATED_AT,
    )


def _evaluation_report() -> EvaluationReport:
    mapping = AuthorizedMappingIdentity(
        mapping_id=MAPPING_ID,
        mapping_version=1,
        mapping_input_sha256="1" * 64,
        mapper_rule_set_version="phase3-test-rules-v1",
        mapper_rule_set_sha256="2" * 64,
        canonical_family=CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING,
        verdict=ResearchVerdict.BUILD_RESEARCH,
    )
    adapter = SyntheticPointInTimeAdapter.for_mapping(mapping)
    snapshots = []
    for capability in REGISTERED_POLICY.required_snapshot_capabilities:
        request = SnapshotRequestParameters(
            mapping=mapping,
            as_of_utc=AS_OF,
            capability=capability,
            mock_configuration_id=SYNTHETIC_MOCK_CONFIGURATION.configuration_id,
        )
        adapter_result = adapter.fetch(capability)
        quality = run_mandatory_data_quality(
            request=request,
            result=adapter_result,
            configuration=SYNTHETIC_MOCK_CONFIGURATION,
            catalog=QualityReferenceCatalog.from_results(adapter.all_results()),
        )
        assert isinstance(quality, QualityAcceptedResult)
        candidate = build_snapshot_candidate(
            mapping=mapping,
            request=request,
            profile=adapter_result.profile,
            configuration=SYNTHETIC_MOCK_CONFIGURATION,
            batch=quality.batch,
            created_at_utc=CREATED_AT,
        )
        assert isinstance(candidate, SnapshotCandidate)
        snapshots.append(candidate.bundle)
    report = evaluate_synthetic_fixture(
        policy=REGISTERED_POLICY,
        fixture=REGISTERED_FIXTURE,
        mapping=mapping,
        snapshots=tuple(snapshots),
        code_version_git_sha=CODE_VERSION,
        created_at_utc=CREATED_AT,
    )
    assert len(report.gates) == 12
    assert tuple(item.capability for item in report.data_snapshots) == (
        DataCapability.OHLCV,
        DataCapability.UNIVERSE_MEMBERSHIP,
    )
    assert len(report.source_observations) == 2
    assert all(len(item.source_observation_refs) == 2 for item in report.sample_lineage)
    return report


@pytest.fixture(scope="module")
def report() -> EvaluationReport:
    return _evaluation_report()


def _summary(report: EvaluationReport) -> EvaluationReportSummary:
    return EvaluationReportSummary(
        artifact_id=report.artifact_id,
        artifact_sha256=report.artifact_sha256,
        fixture_id=report.fixture_id,
        promotion_state=report.promotion_state,
        synthetic=True,
        no_real_performance_claimed=True,
        created_at_utc=report.created_at_utc,
        warning_count=len(report.warnings),
        reason_codes=report.reason_codes,
    )


def test_policy_create_read_and_list_delegate_typed_identities() -> None:
    workflow = MagicMock(spec=EvaluationWorkflow)
    workflow.create_policy.return_value = REGISTERED_POLICY
    workflow.get_policy.return_value = REGISTERED_POLICY
    workflow.list_policies.return_value = [REGISTERED_POLICY]
    client = _client(workflow)

    created = client.post("/v1/evaluation-policies", json=_policy_payload())
    detail = client.get(
        f"/v1/evaluation-policies/{REGISTERED_POLICY.policy_id}"
        f"/versions/{REGISTERED_POLICY.policy_version}"
    )
    listing = client.get("/v1/evaluation-policies?limit=7")

    assert created.status_code == 201
    assert detail.status_code == 200
    assert listing.status_code == 200
    assert created.json()["policy_sha256"] == REGISTERED_POLICY.policy_sha256
    assert created.json()["strategy_family"] == "A_CROSS_SECTIONAL_EQUITY_RANKING"
    assert created.json()["required_snapshot_capabilities"] == [
        "ohlcv",
        "universe_membership",
    ]
    assert created.json()["label_specification"]["missing_return_policy"] == (
        "block_missing_return_v1"
    )
    assert created.json()["label_specification"]["no_trade_return_policy"] == (
        "explicit_zero_research_observation_v1"
    )
    assert created.json()["sample_adequacy"]["missing_return_policy"] == ("block_missing_return_v1")
    assert created.json()["sample_adequacy"]["no_trade_return_policy"] == (
        "explicit_zero_research_observation_v1"
    )
    assert detail.json()["policy_id"] == str(REGISTERED_POLICY.policy_id)
    assert [item["policy_version"] for item in listing.json()] == [REGISTERED_POLICY.policy_version]
    create_request = workflow.create_policy.call_args.args[0]
    assert isinstance(create_request, EvaluationPolicyCreateRequest)
    assert create_request == EvaluationPolicyCreateRequest(
        policy_id=REGISTERED_POLICY.policy_id,
        policy_version=REGISTERED_POLICY.policy_version,
    )
    workflow.get_policy.assert_called_once_with(
        REGISTERED_POLICY.policy_id,
        REGISTERED_POLICY.policy_version,
    )
    workflow.list_policies.assert_called_once_with(limit=7)


def test_report_create_read_and_list_delegate_server_resolvable_identities(
    report: EvaluationReport,
) -> None:
    workflow = MagicMock(spec=EvaluationWorkflow)
    workflow.create_report.return_value = report
    workflow.get_report.return_value = report
    workflow.list_reports.return_value = [_summary(report)]
    client = _client(workflow)

    created = client.post("/v1/evaluation-reports", json=_report_payload())
    detail = client.get(f"/v1/evaluation-reports/{report.artifact_id}")
    listing = client.get("/v1/evaluation-reports?limit=11")

    assert created.status_code == 201
    assert detail.status_code == 200
    assert listing.status_code == 200
    assert created.json()["artifact_sha256"] == report.artifact_sha256
    assert created.json()["synthetic"] is True
    assert created.json()["no_real_performance_claimed"] is True
    assert len(created.json()["gates"]) == 12
    assert all(
        len(trial["net_returns"])
        == len(trial["return_statuses"])
        == len(trial["return_timestamps_utc"])
        for trial in created.json()["trials"]
    )
    assert {
        status for trial in created.json()["trials"] for status in trial["return_statuses"]
    } == {"observed"}
    assert {entry["return_status"] for entry in created.json()["oos_ledger"]} == {"observed"}
    assert {entry["return_status"] for entry in created.json()["cost_ledger"]} == {"observed"}
    assert [item["capability"] for item in created.json()["data_snapshots"]] == [
        "ohlcv",
        "universe_membership",
    ]
    sources_by_capability = {
        item["key"]["capability"]: item for item in created.json()["source_observations"]
    }
    assert set(sources_by_capability) == {"ohlcv", "universe_membership"}
    membership = sources_by_capability["universe_membership"]
    membership_observation = membership["normalized_observation"]
    assert membership["key"]["normalized_observation_id"] == MEMBERSHIP_OBSERVATION_ID
    assert membership["disposition"] == "included_as_of"
    assert membership_observation["source_record_id"] == "synthetic-membership-2019"
    assert membership_observation["instrument_id"] == "11111111-1111-5111-8111-111111111111"
    assert membership_observation["listing_id"] == "22222222-2222-5222-8222-222222222222"
    assert membership_observation["payload"] == {
        "record_type": "universe_membership",
        "universe_id": "synthetic-us-equity",
        "status": "included",
    }
    for lineage in created.json()["sample_lineage"]:
        assert lineage["membership_source_observation_key"] == {
            "capability": "universe_membership",
            "normalized_observation_id": MEMBERSHIP_OBSERVATION_ID,
        }
        assert {item["capability"] for item in lineage["source_observation_refs"]} == {
            "ohlcv",
            "universe_membership",
        }
        assert len(lineage["source_observation_refs"]) == 2
    assert detail.json()["artifact_id"] == str(report.artifact_id)
    assert listing.json() == [_summary(report).model_dump(mode="json")]
    create_request = workflow.create_report.call_args.args[0]
    assert isinstance(create_request, EvaluationRunCreateRequest)
    assert create_request == EvaluationRunCreateRequest(
        policy_id=REGISTERED_POLICY.policy_id,
        policy_version=REGISTERED_POLICY.policy_version,
        mapping_id=MAPPING_ID,
        snapshot_ids=SNAPSHOT_IDS,
        fixture_id=REGISTERED_FIXTURE.fixture_id,
    )
    workflow.get_report.assert_called_once_with(report.artifact_id)
    workflow.list_reports.assert_called_once_with(limit=11)


def test_blocked_outcome_read_and_list_delegate_immutable_identity() -> None:
    outcome = _blocked_outcome()
    workflow = MagicMock(spec=EvaluationWorkflow)
    workflow.get_outcome.return_value = outcome
    workflow.list_outcomes.return_value = [outcome]
    client = _client(workflow)

    detail = client.get(f"/v1/evaluation-outcomes/{outcome.outcome_id}")
    listing = client.get("/v1/evaluation-outcomes?limit=9")

    assert detail.status_code == 200
    assert listing.status_code == 200
    assert detail.json() == outcome.model_dump(mode="json")
    assert listing.json() == [outcome.model_dump(mode="json")]
    workflow.get_outcome.assert_called_once_with(outcome.outcome_id)
    workflow.list_outcomes.assert_called_once_with(limit=9)


@pytest.mark.parametrize(
    ("path", "workflow_method", "state", "reason_codes", "payload"),
    [
        (
            "/v1/evaluation-policies",
            "create_policy",
            PromotionState.BLOCKED_MISSING_POLICY,
            ("registered_evaluation_policy_missing",),
            _policy_payload(),
        ),
        (
            "/v1/evaluation-reports",
            "create_report",
            PromotionState.BLOCKED_UNCOMPUTABLE,
            ("required_snapshot_missing",),
            _report_payload(),
        ),
    ],
)
def test_create_returns_typed_sanitized_blocked_result(
    path: str,
    workflow_method: str,
    state: PromotionState,
    reason_codes: tuple[str, ...],
    payload: dict[str, object],
) -> None:
    workflow = MagicMock(spec=EvaluationWorkflow)
    outcome = _blocked_outcome() if workflow_method == "create_report" else None
    getattr(workflow, workflow_method).side_effect = EvaluationWorkflowBlocked(
        state,
        reason_codes,
        outcome=outcome,
    )

    response = _client(workflow).post(path, json=payload)

    assert response.status_code == 422
    expected = (
        outcome.model_dump(mode="json")
        if outcome is not None
        else {
            "status": "blocked",
            "promotion_state": state.value,
            "reason_codes": list(reason_codes),
            "sanitized_message": (
                "Phase 5 evaluation stopped because required evidence was unavailable."
            ),
        }
    )
    assert response.json() == expected
    assert "detail" not in response.json()


def test_report_blocker_without_persisted_outcome_is_an_invariant_conflict() -> None:
    workflow = MagicMock(spec=EvaluationWorkflow)
    workflow.create_report.side_effect = EvaluationWorkflowBlocked(
        PromotionState.BLOCKED_UNCOMPUTABLE,
        ("required_snapshot_missing",),
    )

    response = _client(workflow).post("/v1/evaluation-reports", json=_report_payload())

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Immutable Phase 5 evaluation lineage conflicts with persisted evidence."
    }


@pytest.mark.parametrize(
    ("http_method", "path", "workflow_method", "error", "payload"),
    [
        (
            "get",
            f"/v1/evaluation-policies/{MISSING_ID}/versions/1",
            "get_policy",
            EvaluationPolicyNotFound("secret policy row"),
            None,
        ),
        (
            "get",
            f"/v1/evaluation-reports/{MISSING_ID}",
            "get_report",
            EvaluationReportNotFound("secret report row"),
            None,
        ),
        (
            "get",
            f"/v1/evaluation-outcomes/{MISSING_ID}",
            "get_outcome",
            EvaluationOutcomeNotFound("secret outcome row"),
            None,
        ),
        (
            "post",
            "/v1/evaluation-reports",
            "create_report",
            SnapshotNotFound("secret snapshot row"),
            _report_payload(),
        ),
    ],
)
def test_not_found_errors_map_to_sanitized_404(
    http_method: str,
    path: str,
    workflow_method: str,
    error: Exception,
    payload: dict[str, object] | None,
) -> None:
    workflow = MagicMock(spec=EvaluationWorkflow)
    getattr(workflow, workflow_method).side_effect = error

    response = _client(workflow).request(http_method, path, json=payload)

    assert response.status_code == 404
    assert response.json() == {
        "detail": "The requested immutable evaluation resource was not found."
    }
    assert "secret" not in response.text


@pytest.mark.parametrize(
    ("http_method", "path", "workflow_method", "error", "payload"),
    [
        (
            "post",
            "/v1/evaluation-policies",
            "create_policy",
            EvaluationWorkflowConflict("secret policy conflict"),
            _policy_payload(),
        ),
        (
            "post",
            "/v1/evaluation-reports",
            "create_report",
            SnapshotLineage("secret snapshot lineage"),
            _report_payload(),
        ),
        (
            "get",
            f"/v1/evaluation-reports/{MISSING_ID}",
            "get_report",
            EvaluationWorkflowConflict("secret report conflict"),
            None,
        ),
    ],
)
def test_lineage_errors_map_to_sanitized_409(
    http_method: str,
    path: str,
    workflow_method: str,
    error: Exception,
    payload: dict[str, object] | None,
) -> None:
    workflow = MagicMock(spec=EvaluationWorkflow)
    getattr(workflow, workflow_method).side_effect = error

    response = _client(workflow).request(http_method, path, json=payload)

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Immutable Phase 5 evaluation lineage conflicts with persisted evidence."
    }
    assert "secret" not in response.text


def test_create_requests_reject_client_authoritative_policy_and_report_fields() -> None:
    workflow = MagicMock(spec=EvaluationWorkflow)
    client = _client(workflow)
    report_fields = {
        "metrics": [],
        "results": {},
        "artifact_sha256": "0" * 64,
        "thresholds": {},
        "created_at_utc": CREATED_AT.isoformat(),
        "positions": [],
        "promotion_state": "PASS_RESEARCH",
    }
    policy_fields = {
        "policy_sha256": "0" * 64,
        "thresholds": {},
        "approved_by": "client",
    }

    for field_name, value in report_fields.items():
        response = client.post(
            "/v1/evaluation-reports",
            json={**_report_payload(), field_name: value},
        )
        assert response.status_code == 422
        assert response.json()["detail"][0]["type"] == "extra_forbidden"
        assert response.json()["detail"][0]["loc"][-1] == field_name

    for field_name, value in policy_fields.items():
        response = client.post(
            "/v1/evaluation-policies",
            json={**_policy_payload(), field_name: value},
        )
        assert response.status_code == 422
        assert response.json()["detail"][0]["type"] == "extra_forbidden"
        assert response.json()["detail"][0]["loc"][-1] == field_name

    workflow.create_report.assert_not_called()
    workflow.create_policy.assert_not_called()


def test_update_and_delete_methods_are_absent() -> None:
    workflow = MagicMock(spec=EvaluationWorkflow)
    client = _client(workflow)
    paths = (
        "/v1/evaluation-policies",
        f"/v1/evaluation-policies/{REGISTERED_POLICY.policy_id}"
        f"/versions/{REGISTERED_POLICY.policy_version}",
        "/v1/evaluation-reports",
        f"/v1/evaluation-reports/{MISSING_ID}",
        "/v1/evaluation-outcomes",
        f"/v1/evaluation-outcomes/{MISSING_ID}",
    )

    for method in ("put", "patch", "delete"):
        for path in paths:
            assert client.request(method, path).status_code == 405
