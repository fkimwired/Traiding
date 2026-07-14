from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from fable5_api.data_snapshots import router
from fable5_data.contracts import (
    AdapterUnavailableReason,
    AdapterUnavailableResult,
    AuthorizedMappingIdentity,
    DataCapability,
    SnapshotRequestParameters,
)
from fable5_data.quality import (
    QualityAcceptedResult,
    QualityReferenceCatalog,
    run_mandatory_data_quality,
)
from fable5_data.repository import SnapshotAuthorization, SnapshotConflict, SnapshotNotFound
from fable5_data.snapshots import SnapshotCandidate, build_snapshot_candidate
from fable5_data.synthetic import (
    SYNTHETIC_MOCK_CONFIGURATION,
    SyntheticPointInTimeAdapter,
)
from fable5_data.workflow import SnapshotAdapterUnavailable, SnapshotWorkflow
from fable5_mapping.models import CanonicalFamily, ResearchVerdict
from fastapi import FastAPI
from fastapi.testclient import TestClient

MAPPING_ID = UUID("aaaaaaaa-aaaa-5aaa-8aaa-aaaaaaaaaaaa")
SNAPSHOT_ID = UUID("bbbbbbbb-bbbb-5bbb-8bbb-bbbbbbbbbbbb")
AS_OF = datetime(2021, 1, 1, tzinfo=UTC)


def _mapping() -> AuthorizedMappingIdentity:
    return AuthorizedMappingIdentity(
        mapping_id=MAPPING_ID,
        mapping_version=1,
        mapping_input_sha256="1" * 64,
        mapper_rule_set_version="phase3-test-rules",
        mapper_rule_set_sha256="2" * 64,
        canonical_family=CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING,
        verdict=ResearchVerdict.BUILD_RESEARCH,
    )


def _bundle():
    adapter = SyntheticPointInTimeAdapter()
    mapping = _mapping()
    request = SnapshotRequestParameters(
        mapping=mapping,
        as_of_utc=AS_OF,
        capability=DataCapability.OHLCV,
        mock_configuration_id=SYNTHETIC_MOCK_CONFIGURATION.configuration_id,
    )
    adapter_result = adapter.fetch(DataCapability.OHLCV)
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
    )
    assert isinstance(candidate, SnapshotCandidate)
    return candidate.bundle


def _client(workflow: SnapshotWorkflow) -> TestClient:
    app = FastAPI()
    app.state.snapshot_workflow = workflow
    app.include_router(router)
    return TestClient(app)


def _payload() -> dict[str, str]:
    return {
        "mapping_id": str(MAPPING_ID),
        "as_of_utc": AS_OF.isoformat(),
        "capability": "ohlcv",
        "mock_configuration_id": SYNTHETIC_MOCK_CONFIGURATION.configuration_id,
    }


def test_create_accepts_only_server_resolvable_request_fields() -> None:
    bundle = _bundle()
    workflow = MagicMock(spec=SnapshotWorkflow)
    workflow.create_snapshot.return_value = bundle
    client = _client(workflow)

    response = client.post("/v1/data-snapshots", json=_payload())

    assert response.status_code == 201
    assert response.json()["snapshot"]["snapshot_id"] == str(bundle.snapshot.snapshot_id)
    request = workflow.create_snapshot.call_args.args[0]
    assert request.mapping_id == MAPPING_ID
    assert request.capability is DataCapability.OHLCV

    forbidden = {
        **_payload(),
        "canonical_family": "A_CROSS_SECTIONAL_EQUITY_RANKING",
        "observations": [],
        "snapshot_sha256": "0" * 64,
    }
    rejected = client.post("/v1/data-snapshots", json=forbidden)
    assert rejected.status_code == 422
    assert workflow.create_snapshot.call_count == 1


def test_get_and_list_delegate_only_immutable_read_parameters() -> None:
    bundle = _bundle()
    workflow = MagicMock(spec=SnapshotWorkflow)
    workflow.get_snapshot.return_value = bundle
    workflow.list_snapshots.return_value = [bundle.snapshot]
    client = _client(workflow)

    detail = client.get(f"/v1/data-snapshots/{bundle.snapshot.snapshot_id}")
    listing = client.get(f"/v1/data-snapshots?mapping_id={MAPPING_ID}&limit=7")

    assert detail.status_code == 200
    assert listing.status_code == 200
    assert listing.json()[0]["snapshot_sha256"] == bundle.snapshot.snapshot_sha256
    workflow.get_snapshot.assert_called_once_with(bundle.snapshot.snapshot_id)
    workflow.list_snapshots.assert_called_once_with(mapping_id=MAPPING_ID, limit=7)


def test_typed_unavailability_is_sanitized_and_uses_no_error_detail_wrapper() -> None:
    adapter = SyntheticPointInTimeAdapter()
    profile = adapter.profile
    result = AdapterUnavailableResult(
        reason_code=AdapterUnavailableReason.CREDENTIALS_UNAVAILABLE,
        capability=DataCapability.OHLCV,
        provider_id=profile.provider_id,
        adapter_id=profile.adapter_id,
        adapter_version=profile.adapter_version,
        dataset_id=profile.dataset_id,
        product_id=profile.product_id,
        entitlement_id=profile.use_rights.entitlement_id,
        use_rights_id=profile.use_rights.use_rights_id,
        sanitized_message="credentials unavailable before transport initialization",
    )
    workflow = MagicMock(spec=SnapshotWorkflow)
    workflow.create_snapshot.side_effect = SnapshotAdapterUnavailable(result)

    response = _client(workflow).post("/v1/data-snapshots", json=_payload())

    assert response.status_code == 503
    assert response.json() == result.model_dump(mode="json")
    assert "detail" not in response.json()


@pytest.mark.parametrize(
    ("error", "status_code", "detail"),
    [
        (
            SnapshotNotFound("secret database row"),
            404,
            "The requested immutable Phase 4 resource was not found.",
        ),
        (
            SnapshotAuthorization("secret rejected family"),
            422,
            "The persisted mapping does not authorize this Phase 4 data capability.",
        ),
        (
            SnapshotConflict("secret nondeterministic output"),
            409,
            "The immutable snapshot request conflicts with persisted lineage.",
        ),
    ],
)
def test_domain_errors_are_sanitized(
    error: Exception,
    status_code: int,
    detail: str,
) -> None:
    workflow = MagicMock(spec=SnapshotWorkflow)
    workflow.get_snapshot.side_effect = error

    response = _client(workflow).get(f"/v1/data-snapshots/{SNAPSHOT_ID}")

    assert response.status_code == status_code
    assert response.json() == {"detail": detail}
    assert "secret" not in response.text


@pytest.mark.parametrize("method", ["put", "patch", "delete"])
def test_snapshot_mutation_methods_are_absent(method: str) -> None:
    workflow = MagicMock(spec=SnapshotWorkflow)
    client = _client(workflow)

    assert client.request(method, f"/v1/data-snapshots/{SNAPSHOT_ID}").status_code == 405


def test_snapshot_openapi_surface_is_exact_create_read_list() -> None:
    workflow = MagicMock(spec=SnapshotWorkflow)
    schema = _client(workflow).get("/openapi.json").json()
    paths = {path: set(operations) for path, operations in schema["paths"].items()}

    assert paths == {
        "/v1/data-snapshots": {"get", "post"},
        "/v1/data-snapshots/{snapshot_id}": {"get"},
    }
    request_schema = schema["components"]["schemas"]["SnapshotCreateRequest"]
    assert set(request_schema["properties"]) == {
        "mapping_id",
        "as_of_utc",
        "capability",
        "mock_configuration_id",
    }
