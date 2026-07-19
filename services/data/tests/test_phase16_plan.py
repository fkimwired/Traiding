from __future__ import annotations

from fable5_data.phase15.specification import build_family_a_research_admission_specification
from fable5_data.phase16.canonical import (
    PHASE16_ACCEPTED_PHASE15_COMMIT_SHA,
    PHASE16_ACCEPTED_PHASE15_TREE_SHA,
    PHASE16_BOUNDARY_VALUES,
    PHASE16_FROZEN_AT_UTC,
    PHASE16_PHASE15_ARTIFACT_SHA256,
    PHASE16_PHASE15_GAP_SHA256S,
)
from fable5_data.phase16.plan import (
    build_family_a_point_in_time_source_plan,
    canonical_source_plan_bytes,
)


def test_builder_is_byte_deterministic_and_ambient_free() -> None:
    first = build_family_a_point_in_time_source_plan()
    second = build_family_a_point_in_time_source_plan()

    assert first == second
    assert canonical_source_plan_bytes() == canonical_source_plan_bytes()
    assert canonical_source_plan_bytes().endswith(b"\n")
    assert canonical_source_plan_bytes().count(b"\n") == 1
    assert first.frozen_at_utc == PHASE16_FROZEN_AT_UTC


def test_plan_binds_accepted_phase15_and_its_exact_unchanged_gap_rows() -> None:
    source = build_family_a_research_admission_specification()
    plan = build_family_a_point_in_time_source_plan()

    assert plan.accepted_phase15_commit_sha == PHASE16_ACCEPTED_PHASE15_COMMIT_SHA
    assert plan.accepted_phase15_tree_sha == PHASE16_ACCEPTED_PHASE15_TREE_SHA
    assert source.artifact_sha256 == plan.phase15_artifact_sha256 == PHASE16_PHASE15_ARTIFACT_SHA256
    assert tuple(item.gap_sha256 for item in source.gaps) == PHASE16_PHASE15_GAP_SHA256S
    assert tuple(item.code.value for item in source.gaps) == tuple(
        item.code.value for item in plan.phase15_gap_bindings
    )
    assert tuple(item.state.value for item in source.gaps) == tuple(
        item.state.value for item in plan.phase15_gap_bindings
    )


def test_plan_selects_no_candidate_and_starts_no_future_step() -> None:
    plan = build_family_a_point_in_time_source_plan()

    assert all(item.required and not item.source_selected for item in plan.capabilities)
    assert all(
        item.candidate_only
        and not item.selected
        and not item.rights_verified
        and not item.external_verification_performed
        for item in plan.candidates
    )
    assert all(item.state == "NOT_STARTED" for item in plan.future_steps)
    assert all(not item.external_action_authorized for item in plan.future_steps)
    assert plan.future_steps[2].required_prior_evidence == (
        "non_synthetic_evaluation_policy_sha256",
        "confirmation_holdout_definition_sha256",
    )


def test_plan_keeps_every_data_authority_and_action_boundary_closed() -> None:
    rendered = build_family_a_point_in_time_source_plan().model_dump(mode="python")
    for field, expected in PHASE16_BOUNDARY_VALUES.items():
        assert rendered[field] is expected
