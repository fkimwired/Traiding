"""Server-resolved Phase 6 orchestration through the unchanged Phase 5 engine."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from fable5_backtester.contracts import EvaluationReport, FrozenEvaluationPolicy, PromotionState
from fable5_backtester.engine import EvaluationEngineBlocked, evaluate_synthetic_fixture
from fable5_backtester.workflow import EvaluationWorkflowConflict
from fable5_data.canonical import canonical_json_bytes
from fable5_data.contracts import (
    AUTHORIZED_CAPABILITIES,
    PHASE6_SYNTHETIC_FIXTURE_SET_VERSION,
    NormalizedObservation,
    OfficialDocumentContentPayload,
    SnapshotBundle,
    SocialAttentionPayload,
)
from fable5_data.repository import (
    SnapshotAuthorization,
    SnapshotLineage,
    SnapshotNotFound,
)

from fable5_research.artifacts import build_research_artifact
from fable5_research.contracts import (
    ResearchConfigurationId,
    ResearchRunArtifact,
    ResearchRunCreateRequest,
    ResearchRunSummary,
)
from fable5_research.integrity import validate_phase6_evaluation_bridge
from fable5_research.phase5 import build_phase5_inputs, configuration_family
from fable5_research.preparation import prepare_research_pipeline
from fable5_research.repository import (
    ResearchRepositoryConflict,
    ResearchRunNotFound,
)


class ResearchWorkflowConflict(RuntimeError):
    """Immutable Phase 6 lineage or idempotency evidence conflicts."""


class ResearchWorkflowBlocked(RuntimeError):
    """A required policy, source, or computable Phase 5 input is unavailable."""

    def __init__(
        self,
        promotion_state: PromotionState,
        reason_codes: tuple[str, ...],
    ) -> None:
        super().__init__(", ".join(reason_codes))
        self.promotion_state = promotion_state
        self.reason_codes = reason_codes


class ResearchStore(Protocol):
    def create_run(self, artifact: ResearchRunArtifact) -> ResearchRunArtifact: ...

    def get_run(self, run_id: UUID) -> ResearchRunArtifact: ...

    def list_runs(self, *, limit: int) -> list[ResearchRunSummary]: ...


class EvaluationStore(Protocol):
    def create_policy(self, policy: FrozenEvaluationPolicy) -> FrozenEvaluationPolicy: ...

    def create_report(self, report: EvaluationReport) -> EvaluationReport: ...


class SnapshotStore(Protocol):
    def get_snapshot(self, snapshot_id: UUID) -> SnapshotBundle: ...


def _same_evaluation_report_content(
    persisted: EvaluationReport,
    candidate: EvaluationReport,
) -> bool:
    """Compare immutable report evidence while letting the first server timestamp win."""

    excluded = {"created_at_utc"}
    return canonical_json_bytes(
        persisted.model_dump(mode="python", exclude=excluded)
    ) == canonical_json_bytes(candidate.model_dump(mode="python", exclude=excluded))


_C_FAIL_REQUIRED_OFFICIAL_SOURCE_VERSION_ID = UUID("ffffffff-ffff-5fff-8fff-fffffffffff6")


def missing_official_corroboration_source_ids(
    configuration_id: ResearchConfigurationId,
    snapshots: tuple[SnapshotBundle, ...],
) -> tuple[UUID, ...]:
    """Resolve missing exact official/social pairs from immutable snapshot evidence."""

    if configuration_family(configuration_id).value != "C_OFFICIAL_EVENT_TEXT_OVERLAY":
        return ()
    mappings = tuple(item.snapshot.manifest.payload.mapping for item in snapshots)
    if not mappings or any(item != mappings[0] for item in mappings[1:]):
        return (_C_FAIL_REQUIRED_OFFICIAL_SOURCE_VERSION_ID,)
    required = set(mappings[0].official_corroboration_source_version_ids)
    if configuration_id is ResearchConfigurationId.C_FAIL:
        required.add(_C_FAIL_REQUIRED_OFFICIAL_SOURCE_VERSION_ID)
    observations = tuple(
        observation for snapshot in snapshots for observation in snapshot.normalized_observations
    )
    documents: list[tuple[NormalizedObservation, OfficialDocumentContentPayload]] = []
    socials: list[tuple[NormalizedObservation, SocialAttentionPayload]] = []
    for observation in observations:
        if isinstance(observation.payload, OfficialDocumentContentPayload):
            documents.append((observation, observation.payload))
        elif isinstance(observation.payload, SocialAttentionPayload):
            socials.append((observation, observation.payload))
    missing = []
    for source_version_id in sorted(required, key=str):
        matched = any(
            document_payload.official_source_version_id == source_version_id
            and social_payload.claimed_official_source_version_id == source_version_id
            and document.instrument_id == social.instrument_id
            and document.listing_id == social.listing_id
            and document.available_at <= social.available_at
            for document, document_payload in documents
            for social, social_payload in socials
        )
        if not matched:
            missing.append(source_version_id)
    return tuple(missing)


class ResearchWorkflow:
    """Create immutable research runs using server-owned policies, fixtures, and verdicts."""

    def __init__(
        self,
        *,
        repository: ResearchStore,
        evaluation_repository: EvaluationStore,
        snapshot_repository: SnapshotStore,
        code_version_git_sha: str | None,
    ) -> None:
        self.repository = repository
        self.evaluation_repository = evaluation_repository
        self.snapshot_repository = snapshot_repository
        self.code_version_git_sha = code_version_git_sha

    def _resolve_snapshots(
        self,
        request: ResearchRunCreateRequest,
    ) -> tuple[SnapshotBundle, ...]:
        resolved: list[SnapshotBundle] = []
        try:
            for snapshot_id in request.snapshot_ids:
                resolved.append(self.snapshot_repository.get_snapshot(snapshot_id))
        except SnapshotNotFound as exc:
            raise ResearchWorkflowBlocked(
                PromotionState.BLOCKED_UNCOMPUTABLE,
                ("required_phase4_snapshot_missing",),
            ) from exc
        except SnapshotLineage as exc:
            raise ResearchWorkflowBlocked(
                PromotionState.BLOCKED_UNCOMPUTABLE,
                ("phase4_snapshot_lineage_invalid",),
            ) from exc
        except SnapshotAuthorization as exc:
            raise ResearchWorkflowBlocked(
                PromotionState.BLOCKED_MISSING_POLICY,
                ("snapshot_capability_not_authorized",),
            ) from exc
        snapshots = tuple(resolved)
        mappings = tuple(item.snapshot.manifest.payload.mapping for item in snapshots)
        if not mappings or any(item.mapping_id != request.mapping_id for item in mappings):
            raise ResearchWorkflowBlocked(
                PromotionState.BLOCKED_UNCOMPUTABLE,
                ("snapshot_mapping_request_mismatch",),
            )
        if any(item != mappings[0] for item in mappings[1:]):
            raise ResearchWorkflowBlocked(
                PromotionState.BLOCKED_UNCOMPUTABLE,
                ("snapshot_mapping_lineage_mismatch",),
            )
        family = configuration_family(request.research_configuration_id)
        if mappings[0].canonical_family is not family:
            raise ResearchWorkflowBlocked(
                PromotionState.BLOCKED_MISSING_POLICY,
                ("research_configuration_mapping_family_mismatch",),
            )
        capabilities = tuple(
            sorted(
                (item.snapshot.manifest.payload.request.capability for item in snapshots),
                key=str,
            )
        )
        required = tuple(sorted(AUTHORIZED_CAPABILITIES[family], key=str))
        if capabilities != required:
            raise ResearchWorkflowBlocked(
                PromotionState.BLOCKED_MISSING_POLICY,
                ("research_required_capability_set_mismatch",),
            )
        if any(
            not item.snapshot.manifest.payload.adapter.synthetic
            or item.snapshot.manifest.payload.configuration.fixture_set_version
            != PHASE6_SYNTHETIC_FIXTURE_SET_VERSION
            for item in snapshots
        ):
            raise ResearchWorkflowBlocked(
                PromotionState.BLOCKED_UNCOMPUTABLE,
                ("authorized_phase6_synthetic_snapshot_required",),
            )
        return snapshots

    def create_run(self, request: ResearchRunCreateRequest) -> ResearchRunArtifact:
        if self.code_version_git_sha is None:
            raise ResearchWorkflowBlocked(
                PromotionState.BLOCKED_MISSING_POLICY,
                ("code_version_git_sha_missing",),
            )
        snapshots = self._resolve_snapshots(request)
        if missing_official_corroboration_source_ids(
            request.research_configuration_id,
            snapshots,
        ):
            raise ResearchWorkflowBlocked(
                PromotionState.BLOCKED_MISSING_POLICY,
                ("official_corroboration_required",),
            )
        mapping = snapshots[0].snapshot.manifest.payload.mapping
        try:
            prepared = prepare_research_pipeline(
                request.research_configuration_id,
                snapshots,
            )
            policy, fixture = build_phase5_inputs(
                configuration_id=request.research_configuration_id,
                prepared=prepared,
                snapshots=snapshots,
            )
            stored_policy = self.evaluation_repository.create_policy(policy)
            if stored_policy != policy:
                raise ResearchWorkflowConflict("persisted Phase 5 policy changed")
            report = evaluate_synthetic_fixture(
                policy=policy,
                fixture=fixture,
                mapping=mapping,
                snapshots=snapshots,
                code_version_git_sha=self.code_version_git_sha,
            )
            validate_phase6_evaluation_bridge(
                policy=policy,
                fixture=fixture,
                prepared=prepared,
                report=report,
            )
            stored_report = self.evaluation_repository.create_report(report)
            if not _same_evaluation_report_content(stored_report, report):
                raise ResearchWorkflowConflict("persisted Phase 5 report changed")
            artifact = build_research_artifact(
                configuration_id=request.research_configuration_id,
                mapping=mapping,
                prepared=prepared,
                report=stored_report,
                snapshots=snapshots,
            )
            return self.repository.create_run(artifact)
        except EvaluationEngineBlocked as exc:
            raise ResearchWorkflowBlocked(exc.state, exc.reason_codes) from exc
        except (EvaluationWorkflowConflict, ResearchRepositoryConflict) as exc:
            raise ResearchWorkflowConflict("immutable Phase 6 lineage conflicts") from exc
        except ValueError as exc:
            raise ResearchWorkflowBlocked(
                PromotionState.BLOCKED_UNCOMPUTABLE,
                ("phase6_research_evidence_invalid",),
            ) from exc

    def get_run(self, run_id: UUID) -> ResearchRunArtifact:
        return self.repository.get_run(run_id)

    def list_runs(self, *, limit: int) -> list[ResearchRunSummary]:
        return self.repository.list_runs(limit=limit)


__all__ = [
    "ResearchRunNotFound",
    "ResearchWorkflow",
    "ResearchWorkflowBlocked",
    "ResearchWorkflowConflict",
    "missing_official_corroboration_source_ids",
]
