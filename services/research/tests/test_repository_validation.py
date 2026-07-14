from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

import pytest
from fable5_data.canonical import domain_sha256
from fable5_research.canonical import PHASE6_ATTEMPT_HASH_DOMAIN
from fable5_research.contracts import ResearchAttempt, ResearchAttemptStatus
from fable5_research.repository import (
    ResearchRepositoryConflict,
    _summary_from_row,
    _validate_attempt_row,
)
from sqlalchemy.engine import RowMapping


def _attempt() -> ResearchAttempt:
    content = {
        "ordinal": 1,
        "phase5_trial_id": UUID("11111111-1111-5111-8111-111111111111"),
        "phase5_trial_key": "prepared-primary",
        "status": ResearchAttemptStatus.COMPLETED,
        "configuration_sha256": "2" * 64,
        "failure_reason": None,
    }
    return ResearchAttempt.model_validate(
        {
            **content,
            "attempt_sha256": domain_sha256(PHASE6_ATTEMPT_HASH_DOMAIN, content),
        }
    )


def test_repository_reconstruction_rejects_trial_key_column_tampering() -> None:
    attempt = _attempt()
    report_id = UUID("33333333-3333-5333-8333-333333333333")
    row: dict[str, Any] = {
        "ordinal": attempt.ordinal,
        "phase5_report_id": report_id,
        "phase5_trial_id": attempt.phase5_trial_id,
        "phase5_trial_key": "tampered-trial-key",
        "status": attempt.status.value,
        "config_sha256": attempt.configuration_sha256,
        "failure_reason": attempt.failure_reason,
        "attempt_sha256": attempt.attempt_sha256,
        "payload": attempt.model_dump(mode="json"),
    }

    with pytest.raises(
        ResearchRepositoryConflict,
        match="attempt columns conflict with payload",
    ):
        _validate_attempt_row(cast(RowMapping, row), phase5_report_id=report_id)


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    (
        ("synthetic", False),
        ("no_real_performance_claimed", False),
        ("pass_research_is_not_paper_approval", False),
        ("paper_approval_granted", True),
    ),
)
def test_repository_summary_rejects_any_research_only_boundary_violation(
    field: str,
    invalid_value: bool,
) -> None:
    row: dict[str, Any] = {
        "id": UUID("11111111-1111-5111-8111-111111111111"),
        "artifact_sha256": "2" * 64,
        "configuration_id": "phase6-a-pass-v2",
        "canonical_family": "A_CROSS_SECTIONAL_EQUITY_RANKING",
        "promotion_state": "PASS_RESEARCH",
        "status": "completed",
        "synthetic": True,
        "no_real_performance_claimed": True,
        "pass_research_is_not_paper_approval": True,
        "paper_approval_granted": False,
        "created_at_utc": datetime(2026, 1, 1, tzinfo=UTC),
        "reason_codes": [],
    }
    row[field] = invalid_value

    with pytest.raises(
        ResearchRepositoryConflict,
        match="summary exceeded its research-only boundary",
    ):
        _summary_from_row(cast(RowMapping, row))
