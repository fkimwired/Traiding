"""Server-authoritative Phase 5 policy registration and synthetic evaluation workflow."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import NoReturn, Protocol
from uuid import UUID

from fable5_data.contracts import SnapshotBundle
from fable5_data.repository import SnapshotAuthorization, SnapshotLineage, SnapshotNotFound

from fable5_backtester.contracts import (
    EvaluationPolicyCreateRequest,
    EvaluationReport,
    EvaluationReportSummary,
    EvaluationRunCreateRequest,
    FrozenEvaluationPolicy,
    PromotionState,
    SyntheticEvaluationFixture,
)
from fable5_backtester.engine import EvaluationEngineBlocked, evaluate_synthetic_fixture
from fable5_backtester.outcomes import (
    BlockedEvaluationOutcome,
    BlockedFailureStage,
    build_blocked_evaluation_outcome,
)


class EvaluationPolicyNotFound(LookupError):
    """The requested frozen evaluation policy has not been registered."""


class EvaluationReportNotFound(LookupError):
    """The requested immutable evaluation report does not exist."""


class EvaluationWorkflowConflict(RuntimeError):
    """Persisted evaluation lineage conflicts with deterministic server output."""


class EvaluationWorkflowBlocked(RuntimeError):
    """A typed fail-closed Phase 5 result produced before a report can be persisted."""

    def __init__(
        self,
        state: PromotionState,
        reason_codes: tuple[str, ...],
        *,
        outcome: BlockedEvaluationOutcome | None = None,
    ) -> None:
        super().__init__(", ".join(reason_codes))
        self.state = state
        self.reason_codes = reason_codes
        self.outcome = outcome


class EvaluationStore(Protocol):
    def create_policy(self, policy: FrozenEvaluationPolicy) -> FrozenEvaluationPolicy: ...

    def get_policy(self, policy_id: UUID, policy_version: int) -> FrozenEvaluationPolicy: ...

    def list_policies(self, *, limit: int) -> list[FrozenEvaluationPolicy]: ...

    def create_report(self, report: EvaluationReport) -> EvaluationReport: ...

    def get_report(self, artifact_id: UUID) -> EvaluationReport: ...

    def list_reports(self, *, limit: int) -> list[EvaluationReportSummary]: ...

    def create_outcome(
        self,
        outcome: BlockedEvaluationOutcome,
    ) -> BlockedEvaluationOutcome: ...

    def get_outcome(self, outcome_id: UUID) -> BlockedEvaluationOutcome: ...

    def list_outcomes(self, *, limit: int) -> list[BlockedEvaluationOutcome]: ...


class SnapshotStore(Protocol):
    def get_snapshot(self, snapshot_id: UUID) -> SnapshotBundle: ...


PolicyResolver = Callable[[UUID, int], FrozenEvaluationPolicy | None]
FixtureResolver = Callable[[str], SyntheticEvaluationFixture | None]


class EvaluationWorkflow:
    """Resolve all authoritative inputs on the server and persist immutable results."""

    def __init__(
        self,
        *,
        repository: EvaluationStore,
        snapshot_repository: SnapshotStore,
        code_version_git_sha: str | None,
        policy_resolver: PolicyResolver,
        fixture_resolver: FixtureResolver,
        outcome_clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.repository = repository
        self.snapshot_repository = snapshot_repository
        self.code_version_git_sha = code_version_git_sha
        self.policy_resolver = policy_resolver
        self.fixture_resolver = fixture_resolver
        self.outcome_clock = outcome_clock or (lambda: datetime.now(UTC))

    def _raise_blocked_report_outcome(
        self,
        *,
        request: EvaluationRunCreateRequest,
        state: PromotionState,
        reason_codes: tuple[str, ...],
        failure_stage: BlockedFailureStage,
        policy: FrozenEvaluationPolicy | None = None,
        fixture: SyntheticEvaluationFixture | None = None,
        snapshots: tuple[SnapshotBundle, ...] = (),
    ) -> NoReturn:
        outcome = build_blocked_evaluation_outcome(
            request=request,
            promotion_state=state,
            reason_codes=reason_codes,
            failure_stage=failure_stage,
            code_version_git_sha=self.code_version_git_sha,
            policy=policy,
            fixture=fixture,
            snapshots=snapshots,
            created_at_utc=self.outcome_clock(),
        )
        stored = self.repository.create_outcome(outcome)
        raise EvaluationWorkflowBlocked(state, reason_codes, outcome=stored)

    def create_policy(self, request: EvaluationPolicyCreateRequest) -> FrozenEvaluationPolicy:
        policy = self.policy_resolver(request.policy_id, request.policy_version)
        if policy is None:
            raise EvaluationWorkflowBlocked(
                PromotionState.BLOCKED_MISSING_POLICY,
                ("registered_evaluation_policy_missing",),
            )
        return self.repository.create_policy(policy)

    def get_policy(self, policy_id: UUID, policy_version: int) -> FrozenEvaluationPolicy:
        return self.repository.get_policy(policy_id, policy_version)

    def list_policies(self, *, limit: int) -> list[FrozenEvaluationPolicy]:
        return self.repository.list_policies(limit=limit)

    def create_report(self, request: EvaluationRunCreateRequest) -> EvaluationReport:
        if self.code_version_git_sha is None:
            self._raise_blocked_report_outcome(
                request=request,
                state=PromotionState.BLOCKED_MISSING_POLICY,
                reason_codes=("code_version_git_sha_missing",),
                failure_stage=BlockedFailureStage.PRECHECK,
            )
        try:
            policy = self.repository.get_policy(request.policy_id, request.policy_version)
        except EvaluationPolicyNotFound as exc:
            try:
                self._raise_blocked_report_outcome(
                    request=request,
                    state=PromotionState.BLOCKED_MISSING_POLICY,
                    reason_codes=("frozen_evaluation_policy_not_registered",),
                    failure_stage=BlockedFailureStage.POLICY_RESOLUTION,
                )
            except EvaluationWorkflowBlocked as blocked:
                raise blocked from exc
        fixture = self.fixture_resolver(request.fixture_id)
        if fixture is None:
            self._raise_blocked_report_outcome(
                request=request,
                state=PromotionState.BLOCKED_MISSING_POLICY,
                reason_codes=("registered_synthetic_fixture_missing",),
                failure_stage=BlockedFailureStage.FIXTURE_RESOLUTION,
                policy=policy,
            )

        resolved_snapshots: list[SnapshotBundle] = []
        try:
            for snapshot_id in request.snapshot_ids:
                resolved_snapshots.append(self.snapshot_repository.get_snapshot(snapshot_id))
        except SnapshotNotFound as exc:
            try:
                self._raise_blocked_report_outcome(
                    request=request,
                    state=PromotionState.BLOCKED_UNCOMPUTABLE,
                    reason_codes=("required_snapshot_missing",),
                    failure_stage=BlockedFailureStage.SNAPSHOT_RESOLUTION,
                    policy=policy,
                    fixture=fixture,
                    snapshots=tuple(resolved_snapshots),
                )
            except EvaluationWorkflowBlocked as blocked:
                raise blocked from exc
        except SnapshotAuthorization as exc:
            try:
                self._raise_blocked_report_outcome(
                    request=request,
                    state=PromotionState.BLOCKED_MISSING_POLICY,
                    reason_codes=("snapshot_capability_not_authorized",),
                    failure_stage=BlockedFailureStage.SNAPSHOT_RESOLUTION,
                    policy=policy,
                    fixture=fixture,
                    snapshots=tuple(resolved_snapshots),
                )
            except EvaluationWorkflowBlocked as blocked:
                raise blocked from exc
        except SnapshotLineage as exc:
            try:
                self._raise_blocked_report_outcome(
                    request=request,
                    state=PromotionState.BLOCKED_UNCOMPUTABLE,
                    reason_codes=("snapshot_lineage_invalid",),
                    failure_stage=BlockedFailureStage.SNAPSHOT_RESOLUTION,
                    policy=policy,
                    fixture=fixture,
                    snapshots=tuple(resolved_snapshots),
                )
            except EvaluationWorkflowBlocked as blocked:
                raise blocked from exc
        snapshots = tuple(resolved_snapshots)
        mappings = tuple(snapshot.snapshot.manifest.payload.mapping for snapshot in snapshots)
        if not mappings or any(mapping.mapping_id != request.mapping_id for mapping in mappings):
            self._raise_blocked_report_outcome(
                request=request,
                state=PromotionState.BLOCKED_UNCOMPUTABLE,
                reason_codes=("snapshot_mapping_request_mismatch",),
                failure_stage=BlockedFailureStage.SNAPSHOT_LINEAGE,
                policy=policy,
                fixture=fixture,
                snapshots=snapshots,
            )
        if any(mapping != mappings[0] for mapping in mappings[1:]):
            self._raise_blocked_report_outcome(
                request=request,
                state=PromotionState.BLOCKED_UNCOMPUTABLE,
                reason_codes=("snapshot_mapping_lineage_mismatch",),
                failure_stage=BlockedFailureStage.SNAPSHOT_LINEAGE,
                policy=policy,
                fixture=fixture,
                snapshots=snapshots,
            )
        try:
            report = evaluate_synthetic_fixture(
                policy=policy,
                fixture=fixture,
                mapping=mappings[0],
                snapshots=snapshots,
                code_version_git_sha=self.code_version_git_sha,
            )
        except EvaluationEngineBlocked as exc:
            try:
                self._raise_blocked_report_outcome(
                    request=request,
                    state=exc.state,
                    reason_codes=exc.reason_codes,
                    failure_stage=BlockedFailureStage.ENGINE_COMPUTATION,
                    policy=policy,
                    fixture=fixture,
                    snapshots=snapshots,
                )
            except EvaluationWorkflowBlocked as blocked:
                raise blocked from exc
        return self.repository.create_report(report)

    def get_report(self, artifact_id: UUID) -> EvaluationReport:
        return self.repository.get_report(artifact_id)

    def list_reports(self, *, limit: int) -> list[EvaluationReportSummary]:
        return self.repository.list_reports(limit=limit)

    def get_outcome(self, outcome_id: UUID) -> BlockedEvaluationOutcome:
        return self.repository.get_outcome(outcome_id)

    def list_outcomes(self, *, limit: int) -> list[BlockedEvaluationOutcome]:
        return self.repository.list_outcomes(limit=limit)


__all__ = [
    "EvaluationPolicyNotFound",
    "EvaluationReportNotFound",
    "EvaluationStore",
    "EvaluationWorkflow",
    "EvaluationWorkflowBlocked",
    "EvaluationWorkflowConflict",
    "FixtureResolver",
    "PolicyResolver",
    "SnapshotStore",
]
