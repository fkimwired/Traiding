from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from uuid import UUID

import pytest
from fable5_data.phase13.adapters import (
    DeterministicMockPointInTimeQualificationAdapter,
    MockQualificationScenario,
)
from fable5_data.phase13.contracts import (
    PointInTimeQualificationArtifact,
    PointInTimeQualificationCreateRequest,
)
from fable5_data.phase13.workflow import (
    PointInTimeQualificationNotFound,
    PointInTimeQualificationWorkflow,
)
from fable5_data.phase14.contracts import (
    PHASE14_CHECK_ORDER,
    ResearchIngestionEligibilityArtifact,
    ResearchIngestionEligibilityCheckCode,
    ResearchIngestionEligibilityCheckStatus,
    ResearchIngestionEligibilityCreateRequest,
    ResearchIngestionEligibilityOutcome,
    ResearchIngestionEligibilityReasonCode,
)
from fable5_data.phase14.workflow import (
    ResearchIngestionEligibilityNotFound,
    ResearchIngestionEligibilityWorkflow,
    ResearchIngestionEligibilityWorkflowConflict,
)


class _Phase13Memory:
    def __init__(self) -> None:
        self.by_key: dict[str, PointInTimeQualificationArtifact] = {}
        self.by_id: dict[UUID, PointInTimeQualificationArtifact] = {}

    @contextmanager
    def serialized_creation(self, key: str) -> Iterator[_Phase13Memory]:
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
        try:
            return self.by_id[qualification_id]
        except KeyError as exc:
            raise PointInTimeQualificationNotFound from exc


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
        if artifact.request_fingerprint_sha256 in self.by_fingerprint:
            raise ResearchIngestionEligibilityWorkflowConflict("duplicate semantic fingerprint")
        self.by_key[artifact.assessment_idempotency_key] = artifact
        self.by_fingerprint[artifact.request_fingerprint_sha256] = artifact
        self.by_id[artifact.assessment_id] = artifact
        return artifact

    def get_assessment(self, assessment_id: UUID) -> ResearchIngestionEligibilityArtifact:
        try:
            return self.by_id[assessment_id]
        except KeyError as exc:
            raise ResearchIngestionEligibilityNotFound from exc


class _CountingSource:
    def __init__(self, delegate: _Phase13Memory) -> None:
        self.delegate = delegate
        self.reads = 0

    def get_qualification(self, qualification_id: UUID) -> PointInTimeQualificationArtifact:
        self.reads += 1
        return self.delegate.get_qualification(qualification_id)


def _qualification(
    scenario: MockQualificationScenario = MockQualificationScenario.COMPLETE,
    *,
    key: str = "phase13-phase14-source-v1",
) -> tuple[_Phase13Memory, PointInTimeQualificationArtifact]:
    store = _Phase13Memory()
    artifact = PointInTimeQualificationWorkflow(
        adapter=DeterministicMockPointInTimeQualificationAdapter(scenario),
        store=store,
        phase13_code_version_git_sha="1" * 40,
    ).create_qualification(PointInTimeQualificationCreateRequest(qualification_idempotency_key=key))
    return store, artifact


def _request(
    qualification_id: UUID,
    *,
    key: str = "phase14-eligibility-proof-v1",
) -> ResearchIngestionEligibilityCreateRequest:
    return ResearchIngestionEligibilityCreateRequest(
        assessment_idempotency_key=key,
        qualification_id=qualification_id,
    )


def _workflow(
    source: object,
    store: _AssessmentMemory | None = None,
    *,
    code_sha: str | None = "2" * 40,
) -> ResearchIngestionEligibilityWorkflow:
    return ResearchIngestionEligibilityWorkflow(
        qualification_source=source,  # type: ignore[arg-type]
        store=store or _AssessmentMemory(),
        phase14_code_version_git_sha=code_sha,
    )


def test_complete_mock_builds_exact_closed_evidence_bundle() -> None:
    source, qualification = _qualification()

    artifact = _workflow(source).create_assessment(_request(qualification.qualification_id))

    assert artifact.outcome is ResearchIngestionEligibilityOutcome.MOCK_PROOF_COMPLETE
    assert len(artifact.payloads) == 6
    assert len(artifact.checks) == 12
    assert tuple(item.code for item in artifact.checks) == PHASE14_CHECK_ORDER
    assert all(
        item.status is ResearchIngestionEligibilityCheckStatus.PASS for item in artifact.checks
    )
    for code in (
        ResearchIngestionEligibilityCheckCode.EXTERNAL_REQUEST_EVIDENCE_COMPLETE_OR_MOCK,
        ResearchIngestionEligibilityCheckCode.INDEPENDENT_RIGHTS_REFERENCE_PRESENT_OR_MOCK,
        ResearchIngestionEligibilityCheckCode.USE_RIGHTS_CURRENT_OR_MOCK,
        ResearchIngestionEligibilityCheckCode.USE_RIGHTS_SCOPE_SUFFICIENT_OR_MOCK,
    ):
        check = next(item for item in artifact.checks if item.code is code)
        assert check.reason_code is ResearchIngestionEligibilityReasonCode.MOCK_NOT_APPLICABLE
    assert artifact.research_ingestion_authorized is False
    assert artifact.research_data_eligible is False
    assert artifact.pass_research_granted is False
    assert artifact.strategy_execution_eligible is False
    assert artifact.order_submission_authorized is False
    assert artifact.live_path_absent is True


def test_blocked_qualification_produces_only_blocked_assessment() -> None:
    source, qualification = _qualification(MockQualificationScenario.MISSING_DELISTING_RETURN)

    artifact = _workflow(source).create_assessment(_request(qualification.qualification_id))

    assert artifact.outcome is ResearchIngestionEligibilityOutcome.BLOCKED
    checks = {item.code: item for item in artifact.checks}
    assert (
        checks[ResearchIngestionEligibilityCheckCode.QUALIFICATION_OUTCOME_ELIGIBLE_OR_MOCK].status
        is ResearchIngestionEligibilityCheckStatus.BLOCKED
    )
    assert (
        checks[ResearchIngestionEligibilityCheckCode.CAPABILITY_MANIFEST_COMPLETE_PASSING].status
        is ResearchIngestionEligibilityCheckStatus.BLOCKED
    )
    assert (
        checks[ResearchIngestionEligibilityCheckCode.QUALIFICATION_CHECKS_COMPLETE_PASSING].status
        is ResearchIngestionEligibilityCheckStatus.BLOCKED
    )


def test_same_key_replay_is_byte_identical_without_second_source_read() -> None:
    source_store, qualification = _qualification()
    source = _CountingSource(source_store)
    store = _AssessmentMemory()
    workflow = _workflow(source, store)
    request = _request(qualification.qualification_id)

    first = workflow.create_assessment(request)
    second = workflow.create_assessment(request)

    assert first == second
    assert first.artifact_sha256 == second.artifact_sha256
    assert source.reads == 1


def test_conflicting_key_reuse_fails_before_source_resolution() -> None:
    source_store, qualification = _qualification()
    store = _AssessmentMemory()
    _workflow(source_store, store, code_sha="2" * 40).create_assessment(
        _request(qualification.qualification_id)
    )
    second_source = _CountingSource(source_store)

    with pytest.raises(ResearchIngestionEligibilityWorkflowConflict, match="idempotency"):
        _workflow(second_source, store, code_sha="3" * 40).create_assessment(
            _request(qualification.qualification_id)
        )

    assert second_source.reads == 0
    assert len(store.by_id) == 1


def test_same_semantic_fingerprint_under_different_key_fails_before_source_read() -> None:
    source_store, qualification = _qualification()
    store = _AssessmentMemory()
    _workflow(source_store, store).create_assessment(_request(qualification.qualification_id))
    second_source = _CountingSource(source_store)

    with pytest.raises(ResearchIngestionEligibilityWorkflowConflict, match="semantic fingerprint"):
        _workflow(second_source, store).create_assessment(
            _request(qualification.qualification_id, key="phase14-different-key-v1")
        )

    assert second_source.reads == 0
    assert len(store.by_id) == 1


@pytest.mark.parametrize("code_sha", [None, "", "A" * 40, "2" * 39])
def test_missing_code_identity_fails_before_source_resolution(code_sha: str | None) -> None:
    source_store, qualification = _qualification()
    source = _CountingSource(source_store)

    with pytest.raises(ResearchIngestionEligibilityWorkflowConflict, match="code identity"):
        _workflow(source, code_sha=code_sha).create_assessment(
            _request(qualification.qualification_id)
        )

    assert source.reads == 0


def test_missing_or_corrupt_source_leaves_no_partial_assessment() -> None:
    missing_source = _Phase13Memory()
    store = _AssessmentMemory()
    missing_id = UUID("00000000-0000-0000-0000-000000000014")

    with pytest.raises(ResearchIngestionEligibilityWorkflowConflict, match="source evidence"):
        _workflow(missing_source, store).create_assessment(_request(missing_id))

    source_store, qualification = _qualification()
    tampered = {
        name: getattr(qualification, name) for name in PointInTimeQualificationArtifact.model_fields
    }
    tampered["artifact_sha256"] = "0" * 64
    source_store.by_id[qualification.qualification_id] = (
        PointInTimeQualificationArtifact.model_construct(**tampered)
    )
    with pytest.raises(ResearchIngestionEligibilityWorkflowConflict, match="source evidence"):
        _workflow(source_store, store).create_assessment(_request(qualification.qualification_id))

    assert store.by_key == {}
    assert store.by_fingerprint == {}
    assert store.by_id == {}


def test_get_returns_persisted_artifact_and_propagates_not_found() -> None:
    source, qualification = _qualification()
    store = _AssessmentMemory()
    workflow = _workflow(source, store)
    created = workflow.create_assessment(_request(qualification.qualification_id))

    assert workflow.get_assessment(created.assessment_id) == created
    with pytest.raises(ResearchIngestionEligibilityNotFound):
        workflow.get_assessment(UUID("00000000-0000-0000-0000-000000000000"))
