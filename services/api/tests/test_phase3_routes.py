from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from fable5_api.mappings import router
from fable5_mapping.models import MappingWithRationale
from fable5_mapping.repository import (
    MappingConflictError,
    MappingLineageError,
    MappingNotFoundError,
)
from fable5_mapping.workflow import MappingWorkflow
from fastapi import FastAPI
from fastapi.testclient import TestClient

CARD_ID = UUID("10000000-0000-0000-0000-000000000001")
EXTRACTION_ID = UUID("20000000-0000-0000-0000-000000000001")
SOURCE_ID = UUID("30000000-0000-0000-0000-000000000001")
SOURCE_VERSION_ID = UUID("40000000-0000-0000-0000-000000000001")
MAPPING_ID = UUID("50000000-0000-0000-0000-000000000001")
SECOND_MAPPING_ID = UUID("50000000-0000-0000-0000-000000000002")
RATIONALE_ID = UUID("60000000-0000-0000-0000-000000000001")
SECOND_RATIONALE_ID = UUID("60000000-0000-0000-0000-000000000002")
NOW = datetime(2026, 7, 13, 22, 0, tzinfo=UTC)


def mapping_result(
    mapping_id: UUID = MAPPING_ID,
    rationale_id: UUID = RATIONALE_ID,
    mapping_version: int = 1,
) -> MappingWithRationale:
    return MappingWithRationale.model_validate(
        {
            "mapping": {
                "mapping_id": mapping_id,
                "mapping_version": mapping_version,
                "card_id": CARD_ID,
                "card_sha256": "a" * 64,
                "mapping_input_sha256": "b" * 64,
                "extraction_request_id": EXTRACTION_ID,
                "extraction_request_fingerprint": "c" * 64,
                "source_id": SOURCE_ID,
                "source_version_id": SOURCE_VERSION_ID,
                "source_version": 1,
                "source_content_sha256": "d" * 64,
                "official_corroboration_source_version_ids": [],
                "extractor_kind": "deterministic_mock",
                "extractor_id": "phase2-deterministic-extractor",
                "extractor_version": "1",
                "extraction_model_id": None,
                "extraction_model_revision": None,
                "extraction_prompt_version": None,
                "extraction_prompt_sha256": None,
                "extraction_schema_version": "phase2-trading-idea-card-v2",
                "extraction_config_sha256": "e" * 64,
                "canonical_family": "A_CROSS_SECTIONAL_EQUITY_RANKING",
                "verdict": "BUILD_RESEARCH",
                "matched_rule_ids": ["P3-CANON-A"],
                "reason_codes": ["CANON_A_RULE_MATCHED"],
                "mapper_rule_set_version": "phase3-canon-v1",
                "mapper_rule_set_sha256": "f" * 64,
                "source_evidence": [
                    {
                        "phase2_field": "signal_family",
                        "state": "source_supported",
                        "value": "cross_sectional_ranking_claim",
                        "claim_ids": ["claim-ranking"],
                    }
                ],
                "rationale_template_version": "phase3-rationale-v1",
                "created_at_utc": NOW,
            },
            "rationale": {
                "rationale_id": rationale_id,
                "mapping_id": mapping_id,
                "template_version": "phase3-rationale-v1",
                "markdown": "Deterministic research rationale. Not investment advice.",
                "content_sha256": "0" * 64,
                "created_at_utc": NOW,
            },
        }
    )


def make_client(workflow: MappingWorkflow) -> TestClient:
    app = FastAPI()
    app.state.mapping_workflow = workflow
    app.include_router(router)
    return TestClient(app)


def test_create_mapping_has_no_request_body_and_passes_only_card_id() -> None:
    workflow = MagicMock(spec=MappingWorkflow)
    workflow.create_mapping.return_value = mapping_result()
    client = make_client(workflow)

    response = client.post(f"/v1/cards/{CARD_ID}/mappings")

    assert response.status_code == 201
    assert response.json()["mapping"]["mapping_id"] == str(MAPPING_ID)
    workflow.create_mapping.assert_called_once_with(CARD_ID)
    operation = client.get("/openapi.json").json()["paths"]["/v1/cards/{card_id}/mappings"]["post"]
    assert "requestBody" not in operation


def test_list_mapping_filter_limit_and_order_are_delegated() -> None:
    first = mapping_result()
    second = mapping_result(SECOND_MAPPING_ID, SECOND_RATIONALE_ID, 2)
    workflow = MagicMock(spec=MappingWorkflow)
    workflow.list_mappings.return_value = [second, first]
    client = make_client(workflow)

    response = client.get(f"/v1/mappings?card_id={CARD_ID}&limit=20")

    assert response.status_code == 200
    assert [item["mapping"]["mapping_id"] for item in response.json()] == [
        str(SECOND_MAPPING_ID),
        str(MAPPING_ID),
    ]
    workflow.list_mappings.assert_called_once_with(card_id=CARD_ID, limit=20)


def test_get_mapping_delegates_exact_mapping_identity() -> None:
    workflow = MagicMock(spec=MappingWorkflow)
    workflow.get_mapping.return_value = mapping_result()
    client = make_client(workflow)

    response = client.get(f"/v1/mappings/{MAPPING_ID}")

    assert response.status_code == 200
    assert response.json()["rationale"]["mapping_id"] == str(MAPPING_ID)
    workflow.get_mapping.assert_called_once_with(MAPPING_ID)


def test_mapping_not_found_error_is_sanitized() -> None:
    workflow = MagicMock(spec=MappingWorkflow)
    workflow.get_mapping.side_effect = MappingNotFoundError("secret database identity")
    client = make_client(workflow)

    response = client.get(f"/v1/mappings/{MAPPING_ID}")

    assert response.status_code == 404
    assert response.json() == {"detail": "The requested immutable mapping record was not found."}
    assert "secret" not in response.text


@pytest.mark.parametrize("error_type", [MappingLineageError, MappingConflictError])
def test_mapping_conflicts_are_sanitized(error_type: type[Exception]) -> None:
    workflow = MagicMock(spec=MappingWorkflow)
    workflow.create_mapping.side_effect = error_type("secret immutable lineage details")
    client = make_client(workflow)

    response = client.post(f"/v1/cards/{CARD_ID}/mappings")

    assert response.status_code == 409
    assert response.json() == {
        "detail": "The mapping request conflicts with persisted immutable research lineage."
    }
    assert "secret" not in response.text


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("put", f"/v1/mappings/{MAPPING_ID}"),
        ("patch", f"/v1/mappings/{MAPPING_ID}"),
        ("delete", f"/v1/mappings/{MAPPING_ID}"),
        ("put", f"/v1/cards/{CARD_ID}/mappings"),
        ("patch", f"/v1/cards/{CARD_ID}/mappings"),
        ("delete", f"/v1/cards/{CARD_ID}/mappings"),
    ],
)
def test_mapping_mutation_methods_are_absent(method: str, path: str) -> None:
    workflow = MagicMock(spec=MappingWorkflow)
    client = make_client(workflow)

    response = client.request(method, path)

    assert response.status_code == 405


def test_mapping_openapi_surface_is_exactly_create_read_list() -> None:
    workflow = MagicMock(spec=MappingWorkflow)
    client = make_client(workflow)
    paths = client.get("/openapi.json").json()["paths"]
    mapping_paths = {path: set(operations) for path, operations in paths.items()}

    assert mapping_paths == {
        "/v1/cards/{card_id}/mappings": {"post"},
        "/v1/mappings": {"get"},
        "/v1/mappings/{mapping_id}": {"get"},
    }
