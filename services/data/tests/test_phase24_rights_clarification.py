from __future__ import annotations

import json

from fable5_data.phase24 import canonical as c
from fable5_data.phase24.rights_clarification import (
    build_family_a_rtdsm_rights_clarification_requirements,
    canonical_rtdsm_rights_clarification_requirements_bytes,
)


def test_phase24_builder_is_deterministic_and_canonical() -> None:
    first = canonical_rtdsm_rights_clarification_requirements_bytes()
    assert first == canonical_rtdsm_rights_clarification_requirements_bytes()
    assert first.endswith(b"\n") and b"\r" not in first
    assert (
        json.dumps(json.loads(first), sort_keys=True, separators=(",", ":")).encode() + b"\n"
        == first
    )


def test_phase24_questions_and_evidence_are_truthfully_unresolved() -> None:
    artifact = build_family_a_rtdsm_rights_clarification_requirements()
    assert [row.code.value for row in artifact.clarification_questions] == [
        row[0] for row in c.PHASE24_QUESTION_ROWS
    ]
    assert all(row.state.value == "UNANSWERED" for row in artifact.clarification_questions)
    assert all(
        not row.answer_evidence_present and not row.independently_verified and not row.satisfied
        for row in artifact.clarification_questions
    )
    assert all(
        row.state.value == "MISSING" and not row.evidence_present and not row.satisfied
        for row in artifact.evidence_requirements
    )
    assert all(not row.applied for row in artifact.transition_rules)


def test_phase24_preserves_all_false_authority_boundaries() -> None:
    dumped = build_family_a_rtdsm_rights_clarification_requirements().model_dump(mode="python")
    for field, expected in c.PHASE24_BOUNDARY_VALUES.items():
        assert dumped[field] is expected
