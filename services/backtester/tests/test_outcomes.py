from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from fable5_backtester.canonical import domain_sha256, identity
from fable5_backtester.contracts import EvaluationRunCreateRequest, PromotionState
from fable5_backtester.outcomes import (
    PHASE5_BLOCKED_OUTCOME_HASH_DOMAIN,
    PHASE5_BLOCKED_OUTCOME_IDEMPOTENCY_HASH_DOMAIN,
    PHASE5_BLOCKED_OUTCOME_NAMESPACE,
    PHASE5_BLOCKED_SUBMISSION_HASH_DOMAIN,
    BlockedEvaluationOutcome,
    BlockedFailureStage,
    blocked_outcome_hash_payload,
    blocked_outcome_idempotency_payload,
    build_blocked_evaluation_outcome,
)
from pydantic import ValidationError

CREATED = datetime(2026, 7, 14, 1, 30, tzinfo=UTC)


def _request() -> EvaluationRunCreateRequest:
    return EvaluationRunCreateRequest(
        policy_id=UUID("aaaaaaaa-aaaa-5aaa-8aaa-aaaaaaaaaaaa"),
        policy_version=1,
        mapping_id=UUID("bbbbbbbb-bbbb-5bbb-8bbb-bbbbbbbbbbbb"),
        snapshot_ids=(UUID("cccccccc-cccc-5ccc-8ccc-cccccccccccc"),),
        fixture_id="phase5-missing-fixture",
    )


def _outcome(*, created_at: datetime = CREATED) -> BlockedEvaluationOutcome:
    return build_blocked_evaluation_outcome(
        request=_request(),
        promotion_state=PromotionState.BLOCKED_MISSING_POLICY,
        reason_codes=("registered_synthetic_fixture_missing",),
        failure_stage=BlockedFailureStage.FIXTURE_RESOLUTION,
        code_version_git_sha="a" * 40,
        created_at_utc=created_at,
    )


def test_blocked_outcome_has_deterministic_server_authoritative_identity() -> None:
    first = _outcome()
    retry = _outcome(created_at=CREATED + timedelta(seconds=30))

    assert first.idempotency_sha256 == retry.idempotency_sha256
    assert first.outcome_id != retry.outcome_id
    assert first.outcome_sha256 != retry.outcome_sha256
    assert first.created_at_utc != retry.created_at_utc
    assert first.submission_sha256 == domain_sha256(
        PHASE5_BLOCKED_SUBMISSION_HASH_DOMAIN,
        _request().model_dump(mode="python"),
    )
    assert first.outcome_sha256 == domain_sha256(
        PHASE5_BLOCKED_OUTCOME_HASH_DOMAIN,
        blocked_outcome_hash_payload(first),
    )
    assert first.idempotency_sha256 == domain_sha256(
        PHASE5_BLOCKED_OUTCOME_IDEMPOTENCY_HASH_DOMAIN,
        blocked_outcome_idempotency_payload(first),
    )
    assert first.outcome_id == identity(
        PHASE5_BLOCKED_OUTCOME_NAMESPACE,
        first.outcome_sha256,
    )
    assert first.synthetic is True
    assert first.no_real_performance_claimed is True


@pytest.mark.parametrize(
    ("field", "value", "error"),
    (
        ("outcome_sha256", "0" * 64, "outcome hash"),
        ("idempotency_sha256", "0" * 64, "idempotency hash"),
        ("submission_sha256", "0" * 64, "submission hash"),
        ("outcome_id", UUID(int=0), "outcome identity"),
        ("reason_codes", ("",), "reason codes"),
        ("created_at_utc", CREATED + timedelta(seconds=1), "outcome hash"),
    ),
)
def test_blocked_outcome_rejects_tampered_server_fields(
    field: str,
    value: object,
    error: str,
) -> None:
    with pytest.raises(ValidationError, match=error):
        BlockedEvaluationOutcome.model_validate(
            {**_outcome().model_dump(mode="python"), field: value}
        )


def test_nonblocked_state_cannot_create_a_blocked_outcome() -> None:
    with pytest.raises(ValueError, match="blocked promotion state"):
        build_blocked_evaluation_outcome(
            request=_request(),
            promotion_state=PromotionState.PASS_RESEARCH,
            reason_codes=("invalid",),
            failure_stage=BlockedFailureStage.PRECHECK,
            code_version_git_sha="a" * 40,
        )
