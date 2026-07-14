from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

import pytest
from fable5_backtester.contracts import (
    EvaluationPolicyCreateRequest,
    EvaluationReport,
    EvaluationReportSummary,
    EvaluationRunCreateRequest,
    FrozenEvaluationPolicy,
    PromotionState,
    SyntheticEvaluationFixture,
)
from fable5_backtester.engine import EvaluationEngineBlocked
from fable5_backtester.outcomes import (
    BlockedEvaluationOutcome,
    BlockedFailureStage,
    EvaluationOutcomeNotFound,
)
from fable5_backtester.synthetic import (
    REGISTERED_FIXTURE,
    REGISTERED_POLICY,
    resolve_fixture,
    resolve_policy,
)
from fable5_backtester.workflow import (
    EvaluationPolicyNotFound,
    EvaluationReportNotFound,
    EvaluationWorkflow,
    EvaluationWorkflowBlocked,
    FixtureResolver,
    PolicyResolver,
)
from fable5_data.contracts import (
    AuthorizedMappingIdentity,
    DataCapability,
    SnapshotBundle,
    SnapshotRequestParameters,
)
from fable5_data.quality import (
    QualityAcceptedResult,
    QualityReferenceCatalog,
    run_mandatory_data_quality,
)
from fable5_data.repository import SnapshotNotFound
from fable5_data.snapshots import SnapshotCandidate, build_snapshot_candidate
from fable5_data.synthetic import (
    SYNTHETIC_MOCK_CONFIGURATION,
    SyntheticPointInTimeAdapter,
)
from fable5_mapping.models import CanonicalFamily, ResearchVerdict
from pydantic import ValidationError

MAPPING_ID = UUID("aaaaaaaa-aaaa-5aaa-8aaa-aaaaaaaaaaaa")
OTHER_MAPPING_ID = UUID("bbbbbbbb-bbbb-5bbb-8bbb-bbbbbbbbbbbb")
MISSING_ID = UUID("ffffffff-ffff-5fff-8fff-ffffffffffff")
AS_OF = datetime(2026, 7, 12, tzinfo=UTC)
CREATED_AT = datetime(2026, 7, 13, 20, 30, tzinfo=UTC)
CODE_VERSION = "a" * 40


@dataclass
class MemoryEvaluationStore:
    policies: dict[tuple[UUID, int], FrozenEvaluationPolicy] = field(default_factory=dict)
    reports: dict[UUID, EvaluationReport] = field(default_factory=dict)
    create_policy_inputs: list[FrozenEvaluationPolicy] = field(default_factory=list)
    get_policy_inputs: list[tuple[UUID, int]] = field(default_factory=list)
    list_policy_limits: list[int] = field(default_factory=list)
    create_report_inputs: list[EvaluationReport] = field(default_factory=list)
    get_report_inputs: list[UUID] = field(default_factory=list)
    list_report_limits: list[int] = field(default_factory=list)
    outcomes: dict[UUID, BlockedEvaluationOutcome] = field(default_factory=dict)
    create_outcome_inputs: list[BlockedEvaluationOutcome] = field(default_factory=list)
    get_outcome_inputs: list[UUID] = field(default_factory=list)
    list_outcome_limits: list[int] = field(default_factory=list)

    def create_policy(self, policy: FrozenEvaluationPolicy) -> FrozenEvaluationPolicy:
        self.create_policy_inputs.append(policy)
        key = (policy.policy_id, policy.policy_version)
        existing = self.policies.setdefault(key, policy)
        if existing != policy:
            raise AssertionError("test store received conflicting immutable policy content")
        return existing

    def get_policy(self, policy_id: UUID, policy_version: int) -> FrozenEvaluationPolicy:
        self.get_policy_inputs.append((policy_id, policy_version))
        try:
            return self.policies[(policy_id, policy_version)]
        except KeyError as exc:
            raise EvaluationPolicyNotFound from exc

    def list_policies(self, *, limit: int) -> list[FrozenEvaluationPolicy]:
        self.list_policy_limits.append(limit)
        return list(self.policies.values())[:limit]

    def create_report(self, report: EvaluationReport) -> EvaluationReport:
        self.create_report_inputs.append(report)
        existing = self.reports.setdefault(report.artifact_id, report)
        if existing != report:
            raise AssertionError("test store received conflicting immutable report content")
        return existing

    def get_report(self, artifact_id: UUID) -> EvaluationReport:
        self.get_report_inputs.append(artifact_id)
        try:
            return self.reports[artifact_id]
        except KeyError as exc:
            raise EvaluationReportNotFound from exc

    def list_reports(self, *, limit: int) -> list[EvaluationReportSummary]:
        self.list_report_limits.append(limit)
        reports = list(self.reports.values())[:limit]
        return [
            EvaluationReportSummary(
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
            for report in reports
        ]

    def create_outcome(
        self,
        outcome: BlockedEvaluationOutcome,
    ) -> BlockedEvaluationOutcome:
        self.create_outcome_inputs.append(outcome)
        existing = next(
            (
                item
                for item in self.outcomes.values()
                if item.idempotency_sha256 == outcome.idempotency_sha256
            ),
            None,
        )
        if existing is not None:
            return existing
        self.outcomes[outcome.outcome_id] = outcome
        return outcome

    def get_outcome(self, outcome_id: UUID) -> BlockedEvaluationOutcome:
        self.get_outcome_inputs.append(outcome_id)
        try:
            return self.outcomes[outcome_id]
        except KeyError as exc:
            raise EvaluationOutcomeNotFound from exc

    def list_outcomes(self, *, limit: int) -> list[BlockedEvaluationOutcome]:
        self.list_outcome_limits.append(limit)
        return list(self.outcomes.values())[:limit]


@dataclass
class MemorySnapshotStore:
    snapshots: dict[UUID, SnapshotBundle] = field(default_factory=dict)
    get_inputs: list[UUID] = field(default_factory=list)

    def get_snapshot(self, snapshot_id: UUID) -> SnapshotBundle:
        self.get_inputs.append(snapshot_id)
        try:
            return self.snapshots[snapshot_id]
        except KeyError as exc:
            raise SnapshotNotFound(f"snapshot {snapshot_id} was not found") from exc


def _mapping(
    *,
    mapping_id: UUID = MAPPING_ID,
    mapping_version: int = 1,
    input_hash: str = "1" * 64,
) -> AuthorizedMappingIdentity:
    return AuthorizedMappingIdentity(
        mapping_id=mapping_id,
        mapping_version=mapping_version,
        mapping_input_sha256=input_hash,
        mapper_rule_set_version="phase3-test-rules-v1",
        mapper_rule_set_sha256="2" * 64,
        canonical_family=CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING,
        verdict=ResearchVerdict.BUILD_RESEARCH,
    )


def _snapshot(
    mapping: AuthorizedMappingIdentity,
    capability: DataCapability = DataCapability.OHLCV,
) -> SnapshotBundle:
    adapter = SyntheticPointInTimeAdapter.for_mapping(mapping)
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
    return candidate.bundle


def _required_snapshots(mapping: AuthorizedMappingIdentity) -> tuple[SnapshotBundle, ...]:
    return tuple(
        _snapshot(mapping, capability)
        for capability in REGISTERED_POLICY.required_snapshot_capabilities
    )


def _request(
    snapshot_ids: tuple[UUID, ...],
    *,
    mapping_id: UUID = MAPPING_ID,
    fixture_id: str = REGISTERED_FIXTURE.fixture_id,
) -> EvaluationRunCreateRequest:
    return EvaluationRunCreateRequest(
        policy_id=REGISTERED_POLICY.policy_id,
        policy_version=REGISTERED_POLICY.policy_version,
        mapping_id=mapping_id,
        snapshot_ids=snapshot_ids,
        fixture_id=fixture_id,
    )


def _store_with_registered_policy() -> MemoryEvaluationStore:
    return MemoryEvaluationStore(
        policies={
            (REGISTERED_POLICY.policy_id, REGISTERED_POLICY.policy_version): REGISTERED_POLICY
        }
    )


def _workflow(
    *,
    repository: MemoryEvaluationStore,
    snapshots: MemorySnapshotStore | None = None,
    code_version_git_sha: str | None = CODE_VERSION,
    policy_resolver: PolicyResolver = resolve_policy,
    fixture_resolver: FixtureResolver = resolve_fixture,
    outcome_clock: Callable[[], datetime] | None = None,
) -> EvaluationWorkflow:
    return EvaluationWorkflow(
        repository=repository,
        snapshot_repository=snapshots or MemorySnapshotStore(),
        code_version_git_sha=code_version_git_sha,
        policy_resolver=policy_resolver,
        fixture_resolver=fixture_resolver,
        outcome_clock=outcome_clock or (lambda: CREATED_AT),
    )


def test_registered_policy_creation_delegates_idempotently() -> None:
    repository = MemoryEvaluationStore()
    resolver_calls: list[tuple[UUID, int]] = []

    def recording_resolver(policy_id: UUID, policy_version: int) -> FrozenEvaluationPolicy | None:
        resolver_calls.append((policy_id, policy_version))
        return resolve_policy(policy_id, policy_version)

    workflow = _workflow(repository=repository, policy_resolver=recording_resolver)
    request = EvaluationPolicyCreateRequest(
        policy_id=REGISTERED_POLICY.policy_id,
        policy_version=REGISTERED_POLICY.policy_version,
    )

    first = workflow.create_policy(request)
    second = workflow.create_policy(request)

    assert first is REGISTERED_POLICY
    assert second is first
    assert resolver_calls == [
        (REGISTERED_POLICY.policy_id, REGISTERED_POLICY.policy_version),
        (REGISTERED_POLICY.policy_id, REGISTERED_POLICY.policy_version),
    ]
    assert repository.create_policy_inputs == [REGISTERED_POLICY, REGISTERED_POLICY]
    assert repository.policies == {
        (REGISTERED_POLICY.policy_id, REGISTERED_POLICY.policy_version): REGISTERED_POLICY
    }


def test_unknown_policy_registration_fails_closed_without_persistence() -> None:
    repository = MemoryEvaluationStore()
    workflow = _workflow(repository=repository)
    request = EvaluationPolicyCreateRequest(policy_id=MISSING_ID, policy_version=1)

    with pytest.raises(EvaluationWorkflowBlocked) as raised:
        workflow.create_policy(request)

    assert raised.value.state is PromotionState.BLOCKED_MISSING_POLICY
    assert raised.value.reason_codes == ("registered_evaluation_policy_missing",)
    assert repository.create_policy_inputs == []
    assert repository.policies == {}


def test_missing_server_code_sha_fails_closed_before_any_repository_read() -> None:
    repository = _store_with_registered_policy()
    snapshots = MemorySnapshotStore()
    workflow = _workflow(
        repository=repository,
        snapshots=snapshots,
        code_version_git_sha=None,
    )

    with pytest.raises(EvaluationWorkflowBlocked) as raised:
        workflow.create_report(_request((MISSING_ID,)))

    assert raised.value.state is PromotionState.BLOCKED_MISSING_POLICY
    assert raised.value.reason_codes == ("code_version_git_sha_missing",)
    assert repository.get_policy_inputs == []
    assert snapshots.get_inputs == []
    assert repository.create_report_inputs == []
    assert raised.value.outcome is repository.create_outcome_inputs[0]
    assert raised.value.outcome.failure_stage is BlockedFailureStage.PRECHECK
    assert raised.value.outcome.code_version_git_sha is None
    assert raised.value.outcome.resolved_policy_sha256 is None


def test_evaluation_requires_the_frozen_policy_to_be_persisted() -> None:
    repository = MemoryEvaluationStore()
    snapshots = MemorySnapshotStore()
    workflow = _workflow(repository=repository, snapshots=snapshots)

    with pytest.raises(EvaluationWorkflowBlocked) as raised:
        workflow.create_report(_request((MISSING_ID,)))

    assert raised.value.state is PromotionState.BLOCKED_MISSING_POLICY
    assert raised.value.reason_codes == ("frozen_evaluation_policy_not_registered",)
    assert repository.get_policy_inputs == [
        (REGISTERED_POLICY.policy_id, REGISTERED_POLICY.policy_version)
    ]
    assert snapshots.get_inputs == []
    assert repository.create_report_inputs == []
    assert raised.value.outcome is repository.create_outcome_inputs[0]
    assert raised.value.outcome.failure_stage is BlockedFailureStage.POLICY_RESOLUTION


def test_unknown_fixture_fails_closed_before_snapshot_reads() -> None:
    repository = _store_with_registered_policy()
    snapshots = MemorySnapshotStore()
    fixture_calls: list[str] = []

    def missing_fixture(fixture_id: str) -> SyntheticEvaluationFixture | None:
        fixture_calls.append(fixture_id)
        return None

    workflow = _workflow(
        repository=repository,
        snapshots=snapshots,
        fixture_resolver=missing_fixture,
    )
    request = _request((MISSING_ID,), fixture_id="missing-phase5-fixture")

    with pytest.raises(EvaluationWorkflowBlocked) as raised:
        workflow.create_report(request)

    assert raised.value.state is PromotionState.BLOCKED_MISSING_POLICY
    assert raised.value.reason_codes == ("registered_synthetic_fixture_missing",)
    assert fixture_calls == ["missing-phase5-fixture"]
    assert snapshots.get_inputs == []
    assert repository.create_report_inputs == []
    assert raised.value.outcome is repository.create_outcome_inputs[0]
    assert raised.value.outcome.failure_stage is BlockedFailureStage.FIXTURE_RESOLUTION
    assert raised.value.outcome.resolved_policy_sha256 == REGISTERED_POLICY.policy_sha256


def test_snapshot_mapping_must_match_the_requested_mapping() -> None:
    snapshot = _snapshot(_mapping(mapping_id=OTHER_MAPPING_ID))
    snapshot_id = snapshot.snapshot.snapshot_id
    snapshots = MemorySnapshotStore({snapshot_id: snapshot})
    repository = _store_with_registered_policy()
    workflow = _workflow(repository=repository, snapshots=snapshots)

    with pytest.raises(EvaluationWorkflowBlocked) as raised:
        workflow.create_report(_request((snapshot_id,), mapping_id=MAPPING_ID))

    assert raised.value.state is PromotionState.BLOCKED_UNCOMPUTABLE
    assert raised.value.reason_codes == ("snapshot_mapping_request_mismatch",)
    assert snapshots.get_inputs == [snapshot_id]
    assert repository.create_report_inputs == []
    assert raised.value.outcome is repository.create_outcome_inputs[0]
    assert raised.value.outcome.failure_stage is BlockedFailureStage.SNAPSHOT_LINEAGE
    assert tuple(item.snapshot_id for item in raised.value.outcome.resolved_snapshots) == (
        snapshot_id,
    )


def test_all_snapshots_must_share_one_immutable_mapping_lineage() -> None:
    first = _snapshot(_mapping())
    second = _snapshot(_mapping(mapping_version=2, input_hash="3" * 64))
    first_id = first.snapshot.snapshot_id
    second_id = second.snapshot.snapshot_id
    snapshots = MemorySnapshotStore({first_id: first, second_id: second})
    repository = _store_with_registered_policy()
    workflow = _workflow(repository=repository, snapshots=snapshots)

    with pytest.raises(EvaluationWorkflowBlocked) as raised:
        workflow.create_report(_request((first_id, second_id)))

    assert raised.value.state is PromotionState.BLOCKED_UNCOMPUTABLE
    assert raised.value.reason_codes == ("snapshot_mapping_lineage_mismatch",)
    assert snapshots.get_inputs == [first_id, second_id]
    assert repository.create_report_inputs == []
    assert raised.value.outcome is repository.create_outcome_inputs[0]
    assert raised.value.outcome.failure_stage is BlockedFailureStage.SNAPSHOT_LINEAGE
    assert len(raised.value.outcome.resolved_snapshots) == 2


def test_snapshot_not_found_persists_a_sanitized_blocked_outcome() -> None:
    repository = _store_with_registered_policy()
    snapshots = MemorySnapshotStore()
    workflow = _workflow(repository=repository, snapshots=snapshots)

    with pytest.raises(EvaluationWorkflowBlocked) as raised:
        workflow.create_report(_request((MISSING_ID,)))

    assert raised.value.state is PromotionState.BLOCKED_UNCOMPUTABLE
    assert raised.value.reason_codes == ("required_snapshot_missing",)
    assert raised.value.outcome is repository.create_outcome_inputs[0]
    assert raised.value.outcome.failure_stage is BlockedFailureStage.SNAPSHOT_RESOLUTION
    assert raised.value.outcome.resolved_snapshots == ()
    assert snapshots.get_inputs == [MISSING_ID]
    assert repository.create_report_inputs == []


def test_identical_blocked_requests_are_idempotent() -> None:
    repository = _store_with_registered_policy()
    timestamps = iter((CREATED_AT, CREATED_AT.replace(second=CREATED_AT.second + 1)))
    workflow = _workflow(
        repository=repository,
        snapshots=MemorySnapshotStore(),
        outcome_clock=lambda: next(timestamps),
    )
    request = _request((MISSING_ID,))

    outcomes: list[BlockedEvaluationOutcome] = []
    for _ in range(2):
        with pytest.raises(EvaluationWorkflowBlocked) as raised:
            workflow.create_report(request)
        assert raised.value.outcome is not None
        outcomes.append(raised.value.outcome)

    assert outcomes[0] is outcomes[1]
    assert len(repository.outcomes) == 1
    assert len(repository.create_outcome_inputs) == 2
    assert repository.create_outcome_inputs[0].idempotency_sha256 == (
        repository.create_outcome_inputs[1].idempotency_sha256
    )
    assert repository.create_outcome_inputs[0].outcome_sha256 != (
        repository.create_outcome_inputs[1].outcome_sha256
    )


def test_engine_blocker_is_persisted_with_all_resolved_input_hashes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mapping = _mapping()
    snapshot = _snapshot(mapping)
    snapshot_id = snapshot.snapshot.snapshot_id
    repository = _store_with_registered_policy()
    workflow = _workflow(
        repository=repository,
        snapshots=MemorySnapshotStore({snapshot_id: snapshot}),
    )

    def blocked_engine(**_: object) -> EvaluationReport:
        raise EvaluationEngineBlocked(
            PromotionState.BLOCKED_UNCOMPUTABLE,
            ("pbo_matrix_uncomputable",),
        )

    monkeypatch.setattr(
        "fable5_backtester.workflow.evaluate_synthetic_fixture",
        blocked_engine,
    )

    with pytest.raises(EvaluationWorkflowBlocked) as raised:
        workflow.create_report(_request((snapshot_id,)))

    outcome = raised.value.outcome
    assert outcome is not None
    assert outcome.failure_stage is BlockedFailureStage.ENGINE_COMPUTATION
    assert outcome.reason_codes == ("pbo_matrix_uncomputable",)
    assert outcome.resolved_policy_sha256 == REGISTERED_POLICY.policy_sha256
    assert outcome.resolved_fixture_sha256 == REGISTERED_FIXTURE.fixture_sha256
    assert outcome.resolved_fixture_random_seed == REGISTERED_FIXTURE.random_seed
    assert outcome.resolved_raw_trial_count == len(REGISTERED_FIXTURE.trials)
    assert tuple(item.snapshot_sha256 for item in outcome.resolved_snapshots) == (
        snapshot.snapshot.snapshot_sha256,
    )
    assert repository.create_report_inputs == []


def test_successful_report_is_computed_and_persisted_from_server_authorities() -> None:
    mapping = _mapping()
    snapshot_bundles = _required_snapshots(mapping)
    snapshot_ids = tuple(item.snapshot.snapshot_id for item in snapshot_bundles)
    snapshots = MemorySnapshotStore({item.snapshot.snapshot_id: item for item in snapshot_bundles})
    repository = _store_with_registered_policy()
    workflow = _workflow(repository=repository, snapshots=snapshots)
    request = _request(snapshot_ids)

    report = workflow.create_report(request)

    assert repository.get_policy_inputs == [
        (REGISTERED_POLICY.policy_id, REGISTERED_POLICY.policy_version)
    ]
    assert snapshots.get_inputs == list(snapshot_ids)
    assert repository.create_report_inputs == [report]
    assert repository.reports == {report.artifact_id: report}
    assert report.evaluation_policy_sha256 == REGISTERED_POLICY.policy_sha256
    assert report.fixture_sha256 == REGISTERED_FIXTURE.fixture_sha256
    assert report.mapping_id == mapping.mapping_id
    assert report.mapping_version == mapping.mapping_version
    assert tuple(item.snapshot_id for item in report.data_snapshots) == snapshot_ids
    assert report.code_version_git_sha == CODE_VERSION
    assert report.synthetic is True
    assert report.no_real_performance_claimed is True
    assert report.metrics and report.gates
    assert repository.outcomes == {}


def test_policy_and_report_reads_and_lists_delegate_to_the_store() -> None:
    mapping = _mapping()
    snapshot_bundles = _required_snapshots(mapping)
    snapshot_ids = tuple(item.snapshot.snapshot_id for item in snapshot_bundles)
    repository = _store_with_registered_policy()
    workflow = _workflow(
        repository=repository,
        snapshots=MemorySnapshotStore(
            {item.snapshot.snapshot_id: item for item in snapshot_bundles}
        ),
    )
    report = workflow.create_report(_request(snapshot_ids))

    assert (
        workflow.get_policy(REGISTERED_POLICY.policy_id, REGISTERED_POLICY.policy_version)
        is REGISTERED_POLICY
    )
    assert workflow.list_policies(limit=7) == [REGISTERED_POLICY]
    assert workflow.get_report(report.artifact_id) is report
    summaries = workflow.list_reports(limit=11)

    assert [item.artifact_id for item in summaries] == [report.artifact_id]
    assert repository.get_policy_inputs[-1] == (
        REGISTERED_POLICY.policy_id,
        REGISTERED_POLICY.policy_version,
    )
    assert repository.list_policy_limits == [7]
    assert repository.get_report_inputs == [report.artifact_id]
    assert repository.list_report_limits == [11]

    blocked_request = _request((MISSING_ID,))
    with pytest.raises(EvaluationWorkflowBlocked) as raised:
        workflow.create_report(blocked_request)
    outcome = raised.value.outcome
    assert outcome is not None
    assert workflow.get_outcome(outcome.outcome_id) is outcome
    assert workflow.list_outcomes(limit=13) == [outcome]
    assert repository.get_outcome_inputs == [outcome.outcome_id]
    assert repository.list_outcome_limits == [13]


@pytest.mark.parametrize("field", ["metrics", "results"])
def test_run_request_refuses_client_supplied_authoritative_outputs(field: str) -> None:
    payload = {
        "policy_id": REGISTERED_POLICY.policy_id,
        "policy_version": REGISTERED_POLICY.policy_version,
        "mapping_id": MAPPING_ID,
        "snapshot_ids": (MISSING_ID,),
        "fixture_id": REGISTERED_FIXTURE.fixture_id,
        field: {"client_supplied": "forbidden"},
    }

    with pytest.raises(ValidationError) as raised:
        EvaluationRunCreateRequest.model_validate(payload)

    error = raised.value.errors()[0]
    assert error["type"] == "extra_forbidden"
    assert error["loc"] == (field,)
    assert set(EvaluationRunCreateRequest.model_fields) == {
        "policy_id",
        "policy_version",
        "mapping_id",
        "snapshot_ids",
        "fixture_id",
    }
