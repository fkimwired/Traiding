from __future__ import annotations

from fable5_data.phase15.canonical import (
    PHASE15_ACCEPTED_PHASE14_COMMIT_SHA,
    PHASE15_ACCEPTED_PHASE14_TREE_SHA,
    PHASE15_FAMILY,
    PHASE15_FROZEN_AT_UTC,
    PHASE15_GAP_EVIDENCE_REFS,
    PHASE15_GAP_STATES,
    PHASE15_GAP_SUMMARIES,
    PHASE15_PHASE6_SPECIFICATION_ID,
    PHASE15_PHASE6_SPECIFICATION_SHA256,
    PHASE15_PHASE6_SPECIFICATION_VERSION,
    PHASE15_REQUIREMENT_DEFINITIONS,
)
from fable5_data.phase15.specification import (
    build_family_a_research_admission_specification,
    canonical_specification_bytes,
)
from fable5_mapping.models import CanonicalFamily
from fable5_research.specification import build_specification


def test_builder_is_byte_deterministic_and_ambient_state_free() -> None:
    first = build_family_a_research_admission_specification()
    second = build_family_a_research_admission_specification()

    assert first == second
    assert canonical_specification_bytes() == canonical_specification_bytes()
    assert canonical_specification_bytes().endswith(b"\n")
    assert canonical_specification_bytes().count(b"\n") == 1
    assert first.frozen_at_utc == PHASE15_FROZEN_AT_UTC


def test_specification_binds_accepted_phase14_and_exact_phase6_family_a_identity() -> None:
    artifact = build_family_a_research_admission_specification()
    source = build_specification(CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING)

    assert artifact.accepted_phase14_commit_sha == PHASE15_ACCEPTED_PHASE14_COMMIT_SHA
    assert artifact.accepted_phase14_tree_sha == PHASE15_ACCEPTED_PHASE14_TREE_SHA
    assert artifact.family == PHASE15_FAMILY
    assert (
        source.specification_id,
        source.specification_version,
        source.specification_sha256,
    ) == (
        PHASE15_PHASE6_SPECIFICATION_ID,
        PHASE15_PHASE6_SPECIFICATION_VERSION,
        PHASE15_PHASE6_SPECIFICATION_SHA256,
    )


def test_rows_contain_closed_human_reviewable_definitions_and_evidence() -> None:
    artifact = build_family_a_research_admission_specification()

    assert tuple(item.definition for item in artifact.requirements) == (
        PHASE15_REQUIREMENT_DEFINITIONS
    )
    assert tuple(item.summary for item in artifact.gaps) == PHASE15_GAP_SUMMARIES
    assert tuple(item.evidence_refs for item in artifact.gaps) == PHASE15_GAP_EVIDENCE_REFS
    assert tuple(item.state.value for item in artifact.gaps) == PHASE15_GAP_STATES
    assert all(item.definition.endswith(".") for item in artifact.requirements)
    assert all(item.summary.endswith(".") for item in artifact.gaps)
    assert all(item.evidence_refs for item in artifact.gaps)


def test_gap_ledger_truthfully_preserves_missing_and_mock_only_dependencies() -> None:
    states = {
        item.code.value: item.state.value
        for item in build_family_a_research_admission_specification().gaps
    }

    assert states["PHASE_15_IMPLEMENTATION_AUTHORITY"] == "PRESENT"
    assert states["IMMUTABLE_AUDIT_SCHEMA"] == "PRESENT"
    assert states["FULL_POINT_IN_TIME_DATASET"] == "MISSING"
    assert states["INDEPENDENT_CURRENT_USE_RIGHTS"] == "MISSING"
    assert states["PURGED_WALK_FORWARD_MECHANICS"] == "MOCK_ONLY"
    assert states["EXTERNAL_CANDIDATE_QUALIFICATION"] == "UNPROVEN"
