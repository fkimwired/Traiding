"""Immutable audit artifacts for Phase 5 evaluation requests that fail closed."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal, Self
from uuid import UUID

from fable5_data.contracts import SnapshotBundle
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from fable5_backtester.canonical import domain_sha256, identity
from fable5_backtester.contracts import (
    EvaluationRunCreateRequest,
    FrozenEvaluationPolicy,
    PromotionState,
    SyntheticEvaluationFixture,
)

PHASE5_BLOCKED_SUBMISSION_HASH_DOMAIN = "phase5-evaluation-blocked-submission-v1"
PHASE5_BLOCKED_OUTCOME_IDEMPOTENCY_HASH_DOMAIN = "phase5-evaluation-blocked-outcome-idempotency-v1"
PHASE5_BLOCKED_OUTCOME_HASH_DOMAIN = "phase5-evaluation-blocked-outcome-v1"
PHASE5_BLOCKED_OUTCOME_NAMESPACE = UUID("f275c74d-bdbb-5a1c-984b-51a2ca19e7e2")
BLOCKED_OUTCOME_MESSAGE: Literal[
    "Phase 5 evaluation stopped because required evidence was unavailable."
] = "Phase 5 evaluation stopped because required evidence was unavailable."


class EvaluationOutcomeNotFound(LookupError):
    """The requested immutable blocked evaluation outcome does not exist."""


class BlockedFailureStage(StrEnum):
    PRECHECK = "precheck"
    POLICY_RESOLUTION = "policy_resolution"
    FIXTURE_RESOLUTION = "fixture_resolution"
    SNAPSHOT_RESOLUTION = "snapshot_resolution"
    SNAPSHOT_LINEAGE = "snapshot_lineage"
    ENGINE_COMPUTATION = "engine_computation"


class _StrictOutcomeModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ResolvedSnapshotEvidence(_StrictOutcomeModel):
    snapshot_id: UUID
    snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    mapping_id: UUID
    mapping_version: int = Field(ge=1)
    mapping_input_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class BlockedEvaluationOutcome(_StrictOutcomeModel):
    outcome_id: UUID
    outcome_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    artifact_type: Literal["blocked_synthetic_research_evaluation"] = (
        "blocked_synthetic_research_evaluation"
    )
    schema_version: Literal["phase5-blocked-evaluation-outcome-v1"] = (
        "phase5-blocked-evaluation-outcome-v1"
    )
    submission_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    idempotency_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    policy_id: UUID
    policy_version: int = Field(ge=1)
    mapping_id: UUID
    snapshot_ids: tuple[UUID, ...] = Field(min_length=1)
    fixture_id: str = Field(min_length=1, max_length=256)
    resolved_policy_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    resolved_fixture_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    resolved_fixture_random_seed: int | None = Field(default=None, ge=0)
    resolved_raw_trial_count: int | None = Field(default=None, ge=1)
    resolved_snapshots: tuple[ResolvedSnapshotEvidence, ...] = ()
    code_version_git_sha: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    failure_stage: BlockedFailureStage
    status: Literal["blocked"] = "blocked"
    promotion_state: Literal[
        PromotionState.BLOCKED_MISSING_POLICY,
        PromotionState.BLOCKED_UNCOMPUTABLE,
    ]
    reason_codes: tuple[str, ...] = Field(min_length=1)
    sanitized_message: Literal[
        "Phase 5 evaluation stopped because required evidence was unavailable."
    ] = BLOCKED_OUTCOME_MESSAGE
    synthetic: Literal[True] = True
    no_real_performance_claimed: Literal[True] = True
    created_at_utc: datetime

    @field_validator("fixture_id")
    @classmethod
    def validate_fixture_id(cls, value: str) -> str:
        if value != value.strip():
            raise ValueError("fixture_id must be trimmed")
        return value

    @field_validator("reason_codes")
    @classmethod
    def validate_reason_codes(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not item or item != item.strip() for item in value):
            raise ValueError("blocked outcome reason codes must be nonblank and trimmed")
        if len(value) != len(set(value)):
            raise ValueError("blocked outcome reason codes must be unique")
        return value

    @field_validator("created_at_utc")
    @classmethod
    def normalize_created_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created_at_utc must be timezone-aware")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_immutable_identity(self) -> Self:
        if len(self.snapshot_ids) != len(set(self.snapshot_ids)):
            raise ValueError("blocked outcome snapshot identities must be unique")
        resolved_ids = tuple(item.snapshot_id for item in self.resolved_snapshots)
        if len(resolved_ids) != len(set(resolved_ids)):
            raise ValueError("resolved blocked-outcome snapshots must be unique")
        if any(snapshot_id not in self.snapshot_ids for snapshot_id in resolved_ids):
            raise ValueError("resolved snapshot evidence must belong to the submitted request")
        if (self.resolved_fixture_sha256 is None) != (self.resolved_fixture_random_seed is None):
            raise ValueError("resolved fixture hash and random seed must be recorded together")
        if (self.resolved_fixture_sha256 is None) != (self.resolved_raw_trial_count is None):
            raise ValueError("resolved fixture hash and raw trial count must be recorded together")

        request = evaluation_request_from_outcome(self)
        expected_submission = domain_sha256(
            PHASE5_BLOCKED_SUBMISSION_HASH_DOMAIN,
            request.model_dump(mode="python"),
        )
        if self.submission_sha256 != expected_submission:
            raise ValueError("blocked outcome submission hash does not match request identities")
        expected_idempotency = domain_sha256(
            PHASE5_BLOCKED_OUTCOME_IDEMPOTENCY_HASH_DOMAIN,
            blocked_outcome_idempotency_payload(self),
        )
        if self.idempotency_sha256 != expected_idempotency:
            raise ValueError("blocked outcome idempotency hash does not match semantic evidence")
        expected_outcome = domain_sha256(
            PHASE5_BLOCKED_OUTCOME_HASH_DOMAIN,
            blocked_outcome_hash_payload(self),
        )
        if self.outcome_sha256 != expected_outcome:
            raise ValueError("blocked outcome hash does not match its immutable payload")
        if self.outcome_id != identity(PHASE5_BLOCKED_OUTCOME_NAMESPACE, expected_outcome):
            raise ValueError("blocked outcome identity does not match its immutable hash")
        return self


def evaluation_request_from_outcome(
    outcome: BlockedEvaluationOutcome,
) -> EvaluationRunCreateRequest:
    return EvaluationRunCreateRequest(
        policy_id=outcome.policy_id,
        policy_version=outcome.policy_version,
        mapping_id=outcome.mapping_id,
        snapshot_ids=outcome.snapshot_ids,
        fixture_id=outcome.fixture_id,
    )


def blocked_outcome_idempotency_payload(
    outcome: BlockedEvaluationOutcome,
) -> dict[str, object]:
    return {
        "artifact_type": outcome.artifact_type,
        "schema_version": outcome.schema_version,
        "submission_sha256": outcome.submission_sha256,
        "request": evaluation_request_from_outcome(outcome).model_dump(mode="python"),
        "resolved_policy_sha256": outcome.resolved_policy_sha256,
        "resolved_fixture_sha256": outcome.resolved_fixture_sha256,
        "resolved_fixture_random_seed": outcome.resolved_fixture_random_seed,
        "resolved_raw_trial_count": outcome.resolved_raw_trial_count,
        "resolved_snapshots": tuple(
            item.model_dump(mode="python") for item in outcome.resolved_snapshots
        ),
        "code_version_git_sha": outcome.code_version_git_sha,
        "failure_stage": outcome.failure_stage,
        "status": outcome.status,
        "promotion_state": outcome.promotion_state,
        "reason_codes": outcome.reason_codes,
        "sanitized_message": outcome.sanitized_message,
        "synthetic": outcome.synthetic,
        "no_real_performance_claimed": outcome.no_real_performance_claimed,
    }


def blocked_outcome_hash_payload(outcome: BlockedEvaluationOutcome) -> dict[str, object]:
    return {
        **blocked_outcome_idempotency_payload(outcome),
        "idempotency_sha256": outcome.idempotency_sha256,
        "created_at_utc": outcome.created_at_utc,
    }


def resolved_snapshot_evidence(
    snapshots: tuple[SnapshotBundle, ...],
) -> tuple[ResolvedSnapshotEvidence, ...]:
    return tuple(
        ResolvedSnapshotEvidence(
            snapshot_id=bundle.snapshot.snapshot_id,
            snapshot_sha256=bundle.snapshot.snapshot_sha256,
            mapping_id=bundle.snapshot.manifest.payload.mapping.mapping_id,
            mapping_version=bundle.snapshot.manifest.payload.mapping.mapping_version,
            mapping_input_sha256=(bundle.snapshot.manifest.payload.mapping.mapping_input_sha256),
        )
        for bundle in snapshots
    )


def build_blocked_evaluation_outcome(
    *,
    request: EvaluationRunCreateRequest,
    promotion_state: PromotionState,
    reason_codes: tuple[str, ...],
    failure_stage: BlockedFailureStage,
    code_version_git_sha: str | None,
    policy: FrozenEvaluationPolicy | None = None,
    fixture: SyntheticEvaluationFixture | None = None,
    snapshots: tuple[SnapshotBundle, ...] = (),
    created_at_utc: datetime | None = None,
) -> BlockedEvaluationOutcome:
    if promotion_state not in {
        PromotionState.BLOCKED_MISSING_POLICY,
        PromotionState.BLOCKED_UNCOMPUTABLE,
    }:
        raise ValueError("blocked evaluation outcomes require a blocked promotion state")
    submission_sha256 = domain_sha256(
        PHASE5_BLOCKED_SUBMISSION_HASH_DOMAIN,
        request.model_dump(mode="python"),
    )
    created_at = created_at_utc or datetime.now(UTC)
    if created_at.tzinfo is None or created_at.utcoffset() is None:
        raise ValueError("created_at_utc must be timezone-aware")
    created_at = created_at.astimezone(UTC)
    provisional = BlockedEvaluationOutcome.model_construct(
        outcome_id=UUID(int=0),
        outcome_sha256="0" * 64,
        submission_sha256=submission_sha256,
        policy_id=request.policy_id,
        policy_version=request.policy_version,
        mapping_id=request.mapping_id,
        snapshot_ids=request.snapshot_ids,
        fixture_id=request.fixture_id,
        resolved_policy_sha256=(policy.policy_sha256 if policy is not None else None),
        resolved_fixture_sha256=(fixture.fixture_sha256 if fixture is not None else None),
        resolved_fixture_random_seed=(fixture.random_seed if fixture is not None else None),
        resolved_raw_trial_count=(len(fixture.trials) if fixture is not None else None),
        resolved_snapshots=resolved_snapshot_evidence(snapshots),
        code_version_git_sha=code_version_git_sha,
        failure_stage=failure_stage,
        promotion_state=promotion_state,
        reason_codes=reason_codes,
        created_at_utc=created_at,
    )
    idempotency_sha256 = domain_sha256(
        PHASE5_BLOCKED_OUTCOME_IDEMPOTENCY_HASH_DOMAIN,
        blocked_outcome_idempotency_payload(provisional),
    )
    provisional = provisional.model_copy(update={"idempotency_sha256": idempotency_sha256})
    outcome_sha256 = domain_sha256(
        PHASE5_BLOCKED_OUTCOME_HASH_DOMAIN,
        blocked_outcome_hash_payload(provisional),
    )
    return BlockedEvaluationOutcome.model_validate(
        {
            **provisional.model_dump(mode="python"),
            "outcome_id": identity(PHASE5_BLOCKED_OUTCOME_NAMESPACE, outcome_sha256),
            "outcome_sha256": outcome_sha256,
        }
    )


__all__ = [
    "BLOCKED_OUTCOME_MESSAGE",
    "PHASE5_BLOCKED_OUTCOME_HASH_DOMAIN",
    "PHASE5_BLOCKED_OUTCOME_IDEMPOTENCY_HASH_DOMAIN",
    "PHASE5_BLOCKED_OUTCOME_NAMESPACE",
    "PHASE5_BLOCKED_SUBMISSION_HASH_DOMAIN",
    "BlockedEvaluationOutcome",
    "BlockedFailureStage",
    "EvaluationOutcomeNotFound",
    "ResolvedSnapshotEvidence",
    "blocked_outcome_hash_payload",
    "blocked_outcome_idempotency_payload",
    "build_blocked_evaluation_outcome",
    "evaluation_request_from_outcome",
]
