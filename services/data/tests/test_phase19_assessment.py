from __future__ import annotations

from collections.abc import Mapping

from fable5_data.phase18.rights_review import build_family_a_current_use_rights_review
from fable5_data.phase19.assessment import (
    build_family_a_step3_prerequisite_assessment,
    canonical_step3_prerequisite_assessment_bytes,
)
from fable5_data.phase19.canonical import (
    PHASE19_BOUNDARY_VALUES,
    PHASE19_GAP_CODES,
    PHASE19_GAP_STATES,
    PHASE19_PHASE16_ORIGINAL_STEP3_SHA256,
    PHASE19_PHASE18_INHERITED_STEP3_EVIDENCE_SHA256,
    PHASE19_PREREQUISITE_ROWS,
    PHASE19_REQUIRED_EVIDENCE_ROWS,
    PHASE19_SOURCE_GAP_SHA256S,
)
from fable5_data.phase19.contracts import (
    gap_bindings_manifest_sha256,
    prerequisites_manifest_sha256,
    required_evidence_manifest_sha256,
    steps_manifest_sha256,
)


def _all_mapping_keys(value: object) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            keys.add(str(key))
            keys.update(_all_mapping_keys(item))
    elif isinstance(value, (tuple, list)):
        for item in value:
            keys.update(_all_mapping_keys(item))
    return keys


def test_builder_is_byte_deterministic_and_binds_accepted_phase18_lineage() -> None:
    first = build_family_a_step3_prerequisite_assessment()
    second = build_family_a_step3_prerequisite_assessment()
    phase18 = build_family_a_current_use_rights_review()

    assert first == second
    assert canonical_step3_prerequisite_assessment_bytes() == (
        canonical_step3_prerequisite_assessment_bytes()
    )
    assert canonical_step3_prerequisite_assessment_bytes().endswith(b"\n")
    assert canonical_step3_prerequisite_assessment_bytes().count(b"\n") == 1
    assert first.phase18_artifact_id == phase18.artifact_id
    assert first.phase18_artifact_sha256 == phase18.artifact_sha256
    assert first.phase18_policy_sha256 == phase18.policy_sha256
    assert (
        first.phase18_independent_rights_review_sha256 == phase18.independent_rights_review_sha256
    )
    assert first.phase18_rights_currentness_sha256 == phase18.rights_currentness_sha256
    assert first.phase18_steps_manifest_sha256 == phase18.steps_manifest_sha256
    assert first.phase18_aggregate_conclusion == phase18.aggregate_conclusion.value


def test_all_manifests_recompute_from_frozen_rows() -> None:
    artifact = build_family_a_step3_prerequisite_assessment()

    assert artifact.prerequisites_manifest_sha256 == prerequisites_manifest_sha256(
        artifact.prerequisites
    )
    assert artifact.required_prior_evidence_manifest_sha256 == (
        required_evidence_manifest_sha256(artifact.required_prior_evidence)
    )
    assert artifact.phase15_gap_bindings_manifest_sha256 == gap_bindings_manifest_sha256(
        artifact.phase15_gap_bindings
    )
    assert artifact.steps_manifest_sha256 == steps_manifest_sha256(artifact.source_plan_steps)


def test_prerequisite_registry_is_exact_and_never_claims_step3_readiness() -> None:
    artifact = build_family_a_step3_prerequisite_assessment()

    assert (
        tuple(
            (
                item.category.value,
                item.code.value,
                item.definition,
                item.evidence_state.value,
                item.requirement_satisfied,
                item.reason_code,
                tuple(code.value for code in item.related_phase15_gap_codes),
            )
            for item in artifact.prerequisites
        )
        == PHASE19_PREREQUISITE_ROWS
    )
    assert sum(item.requirement_satisfied for item in artifact.prerequisites) == 1
    assert artifact.step3_required_prior_evidence_complete is False
    assert artifact.step3_eligible is False
    assert artifact.step3_external_action_authorized is False


def test_exact_two_required_evidence_rows_remain_missing_without_values() -> None:
    artifact = build_family_a_step3_prerequisite_assessment()

    assert (
        tuple(
            (item.name.value, item.state.value, item.produced, item.reason_code)
            for item in artifact.required_prior_evidence
        )
        == PHASE19_REQUIRED_EVIDENCE_ROWS
    )
    keys = _all_mapping_keys(artifact.model_dump(mode="python"))
    assert "non_synthetic_evaluation_policy_sha256" not in keys
    assert "confirmation_holdout_definition_sha256" not in keys
    assert "qualification_artifact_set_sha256" not in keys


def test_all_nineteen_phase15_gaps_are_unchanged() -> None:
    artifact = build_family_a_step3_prerequisite_assessment()

    assert tuple(item.code.value for item in artifact.phase15_gap_bindings) == PHASE19_GAP_CODES
    assert tuple(item.state.value for item in artifact.phase15_gap_bindings) == PHASE19_GAP_STATES
    assert tuple(item.source_gap_sha256 for item in artifact.phase15_gap_bindings) == (
        PHASE19_SOURCE_GAP_SHA256S
    )
    assert artifact.inherited_phase15_gaps_unchanged is True


def test_steps_one_and_two_are_frozen_and_steps_three_through_seven_are_unstarted() -> None:
    artifact = build_family_a_step3_prerequisite_assessment()
    inventory, rights_review, step3, *later = artifact.source_plan_steps

    assert inventory.state.value == "OUTPUT_FROZEN"
    assert tuple(item.name for item in inventory.produced_outputs) == (
        "candidate_product_inventory_sha256",
    )
    assert rights_review.state.value == "OUTPUT_FROZEN"
    assert tuple(item.name for item in rights_review.produced_outputs) == (
        "independent_rights_review_sha256",
        "rights_currentness_sha256",
    )
    assert step3.state.value == "NOT_STARTED"
    assert tuple(item.value for item in step3.required_prior_evidence) == (
        "non_synthetic_evaluation_policy_sha256",
        "confirmation_holdout_definition_sha256",
    )
    assert step3.produced_outputs == ()
    assert all(item.state.value == "NOT_STARTED" for item in later)
    assert all(not item.produced_outputs for item in later)
    assert all(not item.external_action_authorized for item in artifact.source_plan_steps)
    assert artifact.phase16_original_step3_sha256 == PHASE19_PHASE16_ORIGINAL_STEP3_SHA256
    assert (
        artifact.phase18_inherited_step3_evidence_sha256
        == PHASE19_PHASE18_INHERITED_STEP3_EVIDENCE_SHA256
    )


def test_every_authority_and_persistence_boundary_remains_closed() -> None:
    rendered = build_family_a_step3_prerequisite_assessment().model_dump(mode="python")
    for field, expected in PHASE19_BOUNDARY_VALUES.items():
        assert rendered[field] is expected
