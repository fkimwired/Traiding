from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from uuid import UUID

import pytest
from fable5_data.phase13.adapters import (
    DeterministicMockPointInTimeQualificationAdapter,
    MockQualificationScenario,
    PointInTimeQualificationAdapter,
)
from fable5_data.phase13.contracts import (
    PHASE13_CAPABILITY_ORDER,
    PHASE13_CHECK_ORDER,
    PointInTimeQualificationArtifact,
    PointInTimeQualificationCreateRequest,
    QualificationCapability,
    QualificationCapabilityManifest,
    QualificationCheckCode,
    QualificationCheckStatus,
    QualificationOutcome,
    QualificationProviderProfile,
    QualificationReasonCode,
    QualificationSourceKind,
    QualificationUseRightsAttestation,
)
from fable5_data.phase13.workflow import (
    PointInTimeQualificationNotFound,
    PointInTimeQualificationWorkflow,
    PointInTimeQualificationWorkflowConflict,
)


class _MemoryStore:
    def __init__(self) -> None:
        self.by_key: dict[str, PointInTimeQualificationArtifact] = {}
        self.by_id: dict[UUID, PointInTimeQualificationArtifact] = {}

    @contextmanager
    def serialized_creation(self, key: str) -> Iterator[_MemoryStore]:
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


class _CountingAdapter:
    def __init__(self, delegate: PointInTimeQualificationAdapter) -> None:
        self.delegate = delegate
        self.inspections = 0

    @property
    def source_kind(self) -> QualificationSourceKind:
        return self.delegate.source_kind

    @property
    def profile(self) -> QualificationProviderProfile:
        return self.delegate.profile

    @property
    def rights_attestation(self) -> QualificationUseRightsAttestation | None:
        return self.delegate.rights_attestation

    def inspect_capability(
        self, capability: QualificationCapability
    ) -> QualificationCapabilityManifest:
        self.inspections += 1
        return self.delegate.inspect_capability(capability)


def _request(key: str = "phase13-workflow-proof-v1") -> PointInTimeQualificationCreateRequest:
    return PointInTimeQualificationCreateRequest(qualification_idempotency_key=key)


def _workflow(
    adapter: PointInTimeQualificationAdapter,
    store: _MemoryStore | None = None,
    *,
    code_sha: str | None = "a" * 40,
) -> PointInTimeQualificationWorkflow:
    return PointInTimeQualificationWorkflow(
        adapter=adapter,
        store=store or _MemoryStore(),
        phase13_code_version_git_sha=code_sha,
    )


def test_complete_mock_builds_exact_closed_evidence_bundle() -> None:
    artifact = _workflow(DeterministicMockPointInTimeQualificationAdapter()).create_qualification(
        _request()
    )

    assert artifact.outcome is QualificationOutcome.MOCK_PROOF_COMPLETE
    assert artifact.source_kind is QualificationSourceKind.DETERMINISTIC_MOCK
    assert tuple(item.capability for item in artifact.capability_manifests) == (
        PHASE13_CAPABILITY_ORDER
    )
    assert tuple(item.code for item in artifact.checks) == PHASE13_CHECK_ORDER
    assert all(item.status is QualificationCheckStatus.PASS for item in artifact.checks)
    assert artifact.research_data_eligible is False
    assert artifact.strategy_promotion_authorized is False
    assert artifact.strategy_execution_eligible is False
    assert artifact.execution_authorized is False
    assert artifact.order_submission_authorized is False
    assert artifact.live_path_absent is True


@pytest.mark.parametrize(
    ("scenario", "check_code", "reason"),
    [
        (
            MockQualificationScenario.CURRENT_UNIVERSE_SUBSTITUTION,
            QualificationCheckCode.POINT_IN_TIME_UNIVERSE_MEMBERSHIP,
            QualificationReasonCode.CURRENT_UNIVERSE_ONLY,
        ),
        (
            MockQualificationScenario.MISSING_DELISTING_RETURN,
            QualificationCheckCode.DELISTING_RETURN_SEMANTICS,
            QualificationReasonCode.DELISTING_RETURN_UNAVAILABLE,
        ),
        (
            MockQualificationScenario.ACTION_LOOKAHEAD,
            QualificationCheckCode.CORPORATE_ACTION_ANNOUNCEMENT_REVISION,
            QualificationReasonCode.ACTION_REVISION_INVALID,
        ),
        (
            MockQualificationScenario.RESTATEMENT_OVERWRITE,
            QualificationCheckCode.AS_REPORTED_FUNDAMENTAL_REVISION,
            QualificationReasonCode.FUNDAMENTAL_REVISION_INVALID,
        ),
        (
            MockQualificationScenario.RAW_NORMALIZED_MISMATCH,
            QualificationCheckCode.RAW_NORMALIZED_RECONCILIATION,
            QualificationReasonCode.RAW_NORMALIZED_MISMATCH,
        ),
        (
            MockQualificationScenario.NULL_SENTINEL_DRIFT,
            QualificationCheckCode.NULL_SENTINEL_SCHEMA_DRIFT,
            QualificationReasonCode.NULL_SENTINEL_DRIFT,
        ),
        (
            MockQualificationScenario.SCHEMA_DRIFT,
            QualificationCheckCode.NULL_SENTINEL_SCHEMA_DRIFT,
            QualificationReasonCode.SCHEMA_DRIFT,
        ),
        (
            MockQualificationScenario.NONDETERMINISTIC_CAPTURE,
            QualificationCheckCode.DETERMINISTIC_CAPTURE_MANIFEST,
            QualificationReasonCode.NONDETERMINISTIC_CAPTURE,
        ),
    ],
)
def test_adversarial_mock_scenarios_block_exact_checks(
    scenario: MockQualificationScenario,
    check_code: QualificationCheckCode,
    reason: QualificationReasonCode,
) -> None:
    artifact = _workflow(
        DeterministicMockPointInTimeQualificationAdapter(scenario)
    ).create_qualification(_request(f"phase13-{scenario.value.lower()}-v1"))

    assert artifact.outcome is QualificationOutcome.BLOCKED
    check = next(item for item in artifact.checks if item.code is check_code)
    assert check.status is QualificationCheckStatus.BLOCKED
    assert check.reason_code is reason


def test_idempotent_replay_returns_same_artifact_without_second_inspection() -> None:
    store = _MemoryStore()
    adapter = _CountingAdapter(DeterministicMockPointInTimeQualificationAdapter())
    workflow = _workflow(adapter, store)

    first = workflow.create_qualification(_request())
    second = workflow.create_qualification(_request())

    assert second == first
    assert second.artifact_sha256 == first.artifact_sha256
    assert adapter.inspections == len(PHASE13_CAPABILITY_ORDER)


def test_idempotency_conflict_fails_before_adapter_inspection() -> None:
    store = _MemoryStore()
    first_adapter = _CountingAdapter(DeterministicMockPointInTimeQualificationAdapter())
    _workflow(first_adapter, store, code_sha="a" * 40).create_qualification(_request())
    second_adapter = _CountingAdapter(DeterministicMockPointInTimeQualificationAdapter())

    with pytest.raises(PointInTimeQualificationWorkflowConflict, match="idempotency"):
        _workflow(second_adapter, store, code_sha="b" * 40).create_qualification(_request())

    assert first_adapter.inspections == len(PHASE13_CAPABILITY_ORDER)
    assert second_adapter.inspections == 0


@pytest.mark.parametrize("code_sha", [None, "", "A" * 40, "a" * 39])
def test_missing_or_invalid_code_identity_fails_before_adapter_activity(
    code_sha: str | None,
) -> None:
    adapter = _CountingAdapter(DeterministicMockPointInTimeQualificationAdapter())

    with pytest.raises(PointInTimeQualificationWorkflowConflict, match="code identity"):
        _workflow(adapter, code_sha=code_sha).create_qualification(_request())

    assert adapter.inspections == 0


def test_adapter_registry_violation_fails_closed_without_persistence() -> None:
    class WrongRegistryAdapter(_CountingAdapter):
        def inspect_capability(
            self, capability: QualificationCapability
        ) -> QualificationCapabilityManifest:
            del capability
            return super().inspect_capability(PHASE13_CAPABILITY_ORDER[0])

    store = _MemoryStore()
    adapter = WrongRegistryAdapter(DeterministicMockPointInTimeQualificationAdapter())

    with pytest.raises(PointInTimeQualificationWorkflowConflict, match="registry"):
        _workflow(adapter, store).create_qualification(_request())

    assert store.by_key == {}
    assert store.by_id == {}


def test_get_returns_persisted_artifact_and_propagates_not_found() -> None:
    store = _MemoryStore()
    workflow = _workflow(DeterministicMockPointInTimeQualificationAdapter(), store)
    created = workflow.create_qualification(_request())

    assert workflow.get_qualification(created.qualification_id) == created
    with pytest.raises(PointInTimeQualificationNotFound):
        workflow.get_qualification(UUID("00000000-0000-0000-0000-000000000000"))
