from __future__ import annotations

import ast
import json
import socket
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from uuid import UUID

import pytest
from fable5_data.phase13.adapters import DeterministicMockPointInTimeQualificationAdapter
from fable5_data.phase13.contracts import (
    PointInTimeQualificationArtifact,
    PointInTimeQualificationCreateRequest,
)
from fable5_data.phase13.workflow import PointInTimeQualificationWorkflow
from fable5_data.phase14.contracts import (
    ResearchIngestionEligibilityArtifact,
    ResearchIngestionEligibilityCreateRequest,
    ResearchIngestionEligibilityOutcome,
)
from fable5_data.phase14.workflow import (
    ResearchIngestionEligibilityWorkflow,
    ResearchIngestionEligibilityWorkflowConflict,
)
from pydantic import ValidationError


class _QualificationMemory:
    def __init__(self) -> None:
        self.by_key: dict[str, PointInTimeQualificationArtifact] = {}
        self.by_id: dict[UUID, PointInTimeQualificationArtifact] = {}

    @contextmanager
    def serialized_creation(self, key: str) -> Iterator[_QualificationMemory]:
        del key
        yield self

    def find_by_idempotency_key(self, key: str) -> PointInTimeQualificationArtifact | None:
        return self.by_key.get(key)

    def create_qualification(
        self, artifact: PointInTimeQualificationArtifact
    ) -> PointInTimeQualificationArtifact:
        self.by_key[artifact.qualification_idempotency_key] = artifact
        self.by_id[artifact.qualification_id] = artifact
        return artifact

    def get_qualification(self, qualification_id: UUID) -> PointInTimeQualificationArtifact:
        return self.by_id[qualification_id]


class _AssessmentMemory:
    def __init__(self) -> None:
        self.by_key: dict[str, ResearchIngestionEligibilityArtifact] = {}
        self.by_fingerprint: dict[str, ResearchIngestionEligibilityArtifact] = {}
        self.by_id: dict[UUID, ResearchIngestionEligibilityArtifact] = {}

    @contextmanager
    def serialized_creation(self, key: str) -> Iterator[_AssessmentMemory]:
        del key
        yield self

    def find_by_idempotency_key(self, key: str) -> ResearchIngestionEligibilityArtifact | None:
        return self.by_key.get(key)

    def find_by_request_fingerprint(
        self, request_fingerprint_sha256: str
    ) -> ResearchIngestionEligibilityArtifact | None:
        return self.by_fingerprint.get(request_fingerprint_sha256)

    def create_assessment(
        self, artifact: ResearchIngestionEligibilityArtifact
    ) -> ResearchIngestionEligibilityArtifact:
        self.by_key[artifact.assessment_idempotency_key] = artifact
        self.by_fingerprint[artifact.request_fingerprint_sha256] = artifact
        self.by_id[artifact.assessment_id] = artifact
        return artifact

    def get_assessment(self, assessment_id: UUID) -> ResearchIngestionEligibilityArtifact:
        return self.by_id[assessment_id]


def _source() -> tuple[_QualificationMemory, PointInTimeQualificationArtifact]:
    store = _QualificationMemory()
    artifact = PointInTimeQualificationWorkflow(
        adapter=DeterministicMockPointInTimeQualificationAdapter(),
        store=store,
        phase13_code_version_git_sha="1" * 40,
    ).create_qualification(
        PointInTimeQualificationCreateRequest(
            qualification_idempotency_key="phase13-phase14-security-source-v1"
        )
    )
    return store, artifact


def _request(qualification_id: UUID) -> ResearchIngestionEligibilityCreateRequest:
    return ResearchIngestionEligibilityCreateRequest(
        assessment_idempotency_key="phase14-security-proof-v1",
        qualification_id=qualification_id,
    )


def _import_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            names.add(node.module)
    return names


def _all_mapping_keys(value: object) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        keys.update(str(key) for key in value)
        for child in value.values():
            keys.update(_all_mapping_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.update(_all_mapping_keys(child))
    return keys


def test_domain_modules_import_no_transport_provider_or_execution_component() -> None:
    root = Path("services/data/src/fable5_data/phase14")
    imports = set().union(
        *(_import_names(root / name) for name in ("canonical.py", "contracts.py", "workflow.py"))
    )
    forbidden = (
        "aiohttp",
        "asyncio",
        "fable5_backtester",
        "fable5_paper",
        "fable5_research",
        "http",
        "httpx",
        "requests",
        "rq",
        "socket",
        "ssl",
        "urllib",
        "websockets",
        "fable5_data.phase13.adapters",
        "fable5_data.phase13.tiingo",
    )

    assert not {
        imported
        for imported in imports
        if any(imported == item or imported.startswith(f"{item}.") for item in forbidden)
    }


def test_complete_assessment_succeeds_with_active_network_denial(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source, qualification = _source()
    attempted: list[str] = []

    def deny_network(*args: object, **kwargs: object) -> None:
        del args, kwargs
        attempted.append("network")
        raise AssertionError("Phase 14 attempted network access")

    monkeypatch.setattr(socket, "create_connection", deny_network)
    monkeypatch.setattr(socket.socket, "connect", deny_network)

    artifact = ResearchIngestionEligibilityWorkflow(
        qualification_source=source,
        store=_AssessmentMemory(),
        phase14_code_version_git_sha="2" * 40,
    ).create_assessment(_request(qualification.qualification_id))

    assert artifact.outcome is ResearchIngestionEligibilityOutcome.MOCK_PROOF_COMPLETE
    assert attempted == []
    assert artifact.external_request_performed is False


def test_source_failure_is_sanitized_and_leaves_no_evidence() -> None:
    canary = "phase14-secret-canary-do-not-emit"

    class FailingSource:
        def get_qualification(self, qualification_id: UUID) -> PointInTimeQualificationArtifact:
            del qualification_id
            raise RuntimeError(canary)

    store = _AssessmentMemory()
    request = _request(UUID("00000000-0000-0000-0000-000000000013"))

    with pytest.raises(ResearchIngestionEligibilityWorkflowConflict) as captured:
        ResearchIngestionEligibilityWorkflow(
            qualification_source=FailingSource(),
            store=store,
            phase14_code_version_git_sha="2" * 40,
        ).create_assessment(request)

    assert canary not in str(captured.value)
    assert store.by_key == {}
    assert store.by_fingerprint == {}
    assert store.by_id == {}


def test_persisted_projection_contains_no_request_target_or_provider_observation() -> None:
    source, qualification = _source()
    artifact = ResearchIngestionEligibilityWorkflow(
        qualification_source=source,
        store=_AssessmentMemory(),
        phase14_code_version_git_sha="2" * 40,
    ).create_assessment(_request(qualification.qualification_id))
    encoded = json.loads(artifact.model_dump_json())
    keys = _all_mapping_keys(encoded)

    assert {
        "target",
        "host",
        "port",
        "method",
        "http_status",
        "raw_body_sha256",
        "body_size_bytes",
        "provider_profile",
        "rights_attestation",
    }.isdisjoint(keys)


@pytest.mark.parametrize(
    "field",
    [
        "provider",
        "url",
        "host",
        "credential",
        "data_file",
        "strategy",
        "signal",
        "quantity",
        "broker",
        "order",
        "retry",
        "ingestion",
        "promotion",
    ],
)
def test_create_request_rejects_external_data_research_and_execution_inputs(field: str) -> None:
    payload: dict[str, object] = {
        "assessment_idempotency_key": "phase14-security-input-v1",
        "qualification_id": "00000000-0000-0000-0000-000000000013",
        field: "forbidden",
    }

    with pytest.raises(ValidationError):
        ResearchIngestionEligibilityCreateRequest.model_validate(payload)


def test_outcome_contract_has_no_positive_research_or_execution_vocabulary() -> None:
    values = {item.value for item in ResearchIngestionEligibilityOutcome}

    assert values == {"MOCK_PROOF_COMPLETE", "BLOCKED"}
    assert not any(
        term in value
        for value in values
        for term in ("ELIGIBLE", "PASS_RESEARCH", "APPROVED", "EXECUTE", "ORDER")
    )
