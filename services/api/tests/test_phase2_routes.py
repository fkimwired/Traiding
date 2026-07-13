from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from fable5_api.config import Settings
from fable5_api.main import create_app
from fable5_api.schemas import DependencyStatus
from fable5_extraction.models import (
    ContentState,
    SourceCreateResponse,
    SourceRecord,
    SourceType,
    SourceVersion,
)
from fable5_extraction.repository import SourceTextUnavailableError
from fable5_extraction.workflow import IdeaIntakeWorkflow
from fastapi.testclient import TestClient

SOURCE_ID = UUID("10000000-0000-0000-0000-000000000001")
VERSION_ID = UUID("20000000-0000-0000-0000-000000000001")
NOW = datetime(2026, 7, 13, 20, 0, tzinfo=UTC)


def settings_factory() -> Settings:
    return Settings(_env_file=None)


def make_client(workflow: IdeaIntakeWorkflow) -> TestClient:
    app = create_app(
        settings_factory,
        lambda _: DependencyStatus(),
        lambda _: workflow,
    )
    return TestClient(app)


def source_response(raw_text: str | None) -> SourceCreateResponse:
    content = b"" if raw_text is None else raw_text.encode("utf-8")
    return SourceCreateResponse(
        source=SourceRecord(source_id=SOURCE_ID, created_at_utc=NOW),
        source_version=SourceVersion(
            source_version_id=VERSION_ID,
            source_id=SOURCE_ID,
            source_version=1,
            parent_source_version_id=None,
            source_type=(
                SourceType.URL_PROVENANCE if raw_text is None else SourceType.MANUAL_NOTES
            ),
            source_authority="other",
            source_url="https://example.invalid/url-only" if raw_text is None else None,
            content_state=(
                ContentState.URL_ONLY_UNRETRIEVED
                if raw_text is None
                else ContentState.SUPPLIED_TEXT
            ),
            raw_text=raw_text,
            content_sha256=hashlib.sha256(content).hexdigest(),
            supplied_at_utc=NOW,
            retrieved_at_utc=None,
            authority_verification_method=None,
            official_corroboration_source_version_ids=[],
            created_at_utc=NOW,
        ),
        extraction=None,
    )


def test_create_preserves_lossless_text_and_mutation_routes_are_absent() -> None:
    raw_text = "Line one\r\nLine two with emoji 🚦 and trailing spaces.  "
    workflow = MagicMock(spec=IdeaIntakeWorkflow)
    workflow.create_source.return_value = source_response(raw_text)
    client = make_client(workflow)

    response = client.post(
        "/v1/sources",
        json={"source_type": "manual_notes", "source_authority": "other", "raw_text": raw_text},
    )
    assert response.status_code == 201
    assert response.json()["source_version"]["raw_text"] == raw_text
    submitted = workflow.create_source.call_args.args[0]
    assert submitted.raw_text == raw_text

    assert client.put(f"/v1/sources/{SOURCE_ID}", json={}).status_code == 405
    assert client.patch(f"/v1/sources/{SOURCE_ID}", json={}).status_code == 405
    assert client.delete(f"/v1/sources/{SOURCE_ID}").status_code == 405


@pytest.mark.parametrize(
    ("path", "workflow_method"),
    [
        ("/v1/sources", "create_source"),
        (f"/v1/sources/{SOURCE_ID}/versions", "add_source_version"),
    ],
)
@pytest.mark.parametrize(
    "payload",
    [
        {"source_type": "manual_notes", "raw_text": ""},
        {"source_type": "manual_notes", "raw_text": " \t\r\n"},
        {"source_type": "manual_notes", "raw_text": "\u2003"},
        {
            "source_type": "url_provenance",
            "source_url": "https://example.invalid/url-only",
            "raw_text": None,
        },
        {
            "source_type": "manual_notes",
            "raw_text": "Exact supplied text.",
            "supplied_at_utc": "2026-07-13T20:00:00Z",
        },
    ],
)
def test_intake_contract_rejects_blank_null_and_client_timestamp(
    path: str, workflow_method: str, payload: dict[str, object]
) -> None:
    workflow = MagicMock(spec=IdeaIntakeWorkflow)
    client = make_client(workflow)

    response = client.post(path, json=payload)

    assert response.status_code == 422
    getattr(workflow, workflow_method).assert_not_called()


def test_url_only_intake_omits_raw_text_and_returns_no_extraction() -> None:
    workflow = MagicMock(spec=IdeaIntakeWorkflow)
    workflow.create_source.return_value = source_response(None)
    client = make_client(workflow)

    response = client.post(
        "/v1/sources",
        json={
            "source_type": "url_provenance",
            "source_url": "https://example.invalid/url-only",
        },
    )

    assert response.status_code == 201
    assert response.json()["source_version"]["raw_text"] is None
    assert response.json()["extraction"] is None
    submitted = workflow.create_source.call_args.args[0]
    assert submitted.raw_text is None
    assert "raw_text" not in submitted.model_fields_set


def test_list_order_is_delegated_and_unknown_ids_return_not_found() -> None:
    workflow = MagicMock(spec=IdeaIntakeWorkflow)
    workflow.list_sources.return_value = []
    client = make_client(workflow)

    response = client.get("/v1/sources?limit=20")
    assert response.status_code == 200
    assert response.json() == []
    workflow.list_sources.assert_called_once_with(20)


def test_cors_allows_post_but_not_mutation_methods() -> None:
    workflow = MagicMock(spec=IdeaIntakeWorkflow)
    client = make_client(workflow)
    origin = "http://localhost:3000"

    post = client.options(
        "/v1/sources",
        headers={"Origin": origin, "Access-Control-Request-Method": "POST"},
    )
    assert post.status_code == 200
    assert "POST" in post.headers["access-control-allow-methods"]

    delete = client.options(
        "/v1/sources",
        headers={"Origin": origin, "Access-Control-Request-Method": "DELETE"},
    )
    assert delete.status_code == 400


def test_url_only_manual_extraction_request_fails_closed() -> None:
    workflow = MagicMock(spec=IdeaIntakeWorkflow)
    workflow.request_extraction.side_effect = SourceTextUnavailableError(
        "source version has no supplied text; URL retrieval is outside Phase 2"
    )
    client = make_client(workflow)

    response = client.post(f"/v1/source-versions/{VERSION_ID}/extractions")

    assert response.status_code == 422
    assert "URL retrieval is outside Phase 2" in response.json()["detail"]


def test_openapi_contains_only_phase2_create_read_list_domain_routes() -> None:
    workflow = MagicMock(spec=IdeaIntakeWorkflow)
    client = make_client(workflow)
    schema = client.get("/openapi.json").json()
    domain_paths = {
        path: operations for path, operations in schema["paths"].items() if path.startswith("/v1/")
    }
    assert domain_paths
    for operations in domain_paths.values():
        assert set(operations) <= {"get", "post"}

    rendered_paths = " ".join(domain_paths).lower()
    for forbidden in ("signal", "backtest", "broker", "position", "order", "live"):
        assert forbidden not in rendered_paths
    card_schema = schema["components"]["schemas"]["TradingIdeaCard"]
    for required in (
        "testability_status",
        "testability_reason_codes",
        "corroboration_status",
        "contribution_status",
        "extraction_schema_version",
    ):
        assert required in card_schema["required"]
