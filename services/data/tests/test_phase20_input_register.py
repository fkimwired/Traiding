from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from fable5_data.phase19.assessment import build_family_a_step3_prerequisite_assessment
from fable5_data.phase20 import canonical as c
from fable5_data.phase20.contracts import (
    construction_gates_manifest_sha256,
    dependency_groups_manifest_sha256,
    forbidden_substitutes_manifest_sha256,
    gap_bindings_manifest_sha256,
    inherited_prerequisites_manifest_sha256,
    input_requirements_manifest_sha256,
    required_evidence_manifest_sha256,
    step_bindings_manifest_sha256,
    transition_rules_manifest_sha256,
)
from fable5_data.phase20.input_register import (
    build_family_a_evaluation_holdout_input_register,
    canonical_evaluation_holdout_input_register_bytes,
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


def test_builder_is_byte_deterministic_and_binds_accepted_phase19() -> None:
    first = build_family_a_evaluation_holdout_input_register()
    second = build_family_a_evaluation_holdout_input_register()
    phase19 = build_family_a_step3_prerequisite_assessment()

    assert first == second
    assert canonical_evaluation_holdout_input_register_bytes() == (
        canonical_evaluation_holdout_input_register_bytes()
    )
    assert canonical_evaluation_holdout_input_register_bytes().endswith(b"\n")
    assert canonical_evaluation_holdout_input_register_bytes().count(b"\n") == 1
    assert str(first.phase19_artifact_id) == str(phase19.artifact_id)
    assert first.phase19_artifact_sha256 == phase19.artifact_sha256
    assert first.phase19_policy_sha256 == phase19.assessment_policy_sha256
    assert first.phase19_prerequisites_manifest_sha256 == phase19.prerequisites_manifest_sha256
    assert first.phase19_required_evidence_manifest_sha256 == (
        phase19.required_prior_evidence_manifest_sha256
    )
    assert first.phase19_gap_bindings_manifest_sha256 == (
        phase19.phase15_gap_bindings_manifest_sha256
    )
    assert first.phase19_steps_manifest_sha256 == phase19.steps_manifest_sha256
    assert first.phase19_aggregate_conclusion == phase19.aggregate_conclusion.value


def test_all_manifests_recompute_from_exact_rows() -> None:
    artifact = build_family_a_evaluation_holdout_input_register()

    assert artifact.inherited_phase19_prerequisites_manifest_sha256 == (
        inherited_prerequisites_manifest_sha256(artifact.inherited_phase19_prerequisites)
    )
    assert artifact.input_requirements_manifest_sha256 == input_requirements_manifest_sha256(
        artifact.input_requirements
    )
    assert artifact.required_prior_evidence_manifest_sha256 == required_evidence_manifest_sha256(
        artifact.required_prior_evidence
    )
    assert artifact.transition_rules_manifest_sha256 == transition_rules_manifest_sha256(
        artifact.transition_rules
    )
    assert artifact.construction_dependency_groups_manifest_sha256 == (
        dependency_groups_manifest_sha256(artifact.construction_dependency_groups)
    )
    assert artifact.construction_gates_manifest_sha256 == construction_gates_manifest_sha256(
        artifact.construction_gates
    )
    assert artifact.forbidden_substitutes_manifest_sha256 == forbidden_substitutes_manifest_sha256(
        artifact.forbidden_substitutes
    )
    assert artifact.phase15_gap_bindings_manifest_sha256 == gap_bindings_manifest_sha256(
        artifact.phase15_gap_bindings
    )
    assert artifact.source_plan_steps_manifest_sha256 == step_bindings_manifest_sha256(
        artifact.source_plan_steps
    )


def test_twenty_input_requirements_are_exact_and_value_absent() -> None:
    artifact = build_family_a_evaluation_holdout_input_register()

    actual = tuple(
        (
            item.category.value,
            item.code.value,
            item.definition,
            item.evidence_state.value,
            item.requirement_satisfied,
            item.required_field_names,
            tuple(code.value for code in item.related_phase19_prerequisite_codes),
            tuple(code.value for code in item.related_phase15_gap_codes),
            item.reason_code,
        )
        for item in artifact.input_requirements
    )
    assert actual == c.PHASE20_INPUT_REQUIREMENT_ROWS
    assert sum(item.requirement_satisfied for item in artifact.input_requirements) == 1
    assert artifact.input_requirements[15].code.value == "REPRODUCIBILITY_AUDIT_SCHEMA"
    assert all(not item.input_value_present for item in artifact.input_requirements)
    assert all(not item.resolves_reserved_evidence for item in artifact.input_requirements)
    assert all(item.related_phase19_prerequisite_codes for item in artifact.input_requirements)
    assert all(item.related_phase15_gap_codes for item in artifact.input_requirements)


def test_input_relation_mappings_are_exact_and_conservative() -> None:
    artifact = build_family_a_evaluation_holdout_input_register()

    actual = tuple(
        (
            tuple(code.value for code in item.related_phase19_prerequisite_codes),
            tuple(code.value for code in item.related_phase15_gap_codes),
        )
        for item in artifact.input_requirements
    )
    assert actual == c.PHASE20_INPUT_RELATION_ROWS
    audit = artifact.input_requirements[15]
    assert tuple(code.value for code in audit.related_phase19_prerequisite_codes) == (
        "REPRODUCIBILITY_AUDIT_SCHEMA",
    )
    assert tuple(code.value for code in audit.related_phase15_gap_codes) == (
        "IMMUTABLE_AUDIT_SCHEMA",
    )
    approval = artifact.input_requirements[19]
    assert tuple(code.value for code in approval.related_phase19_prerequisite_codes) == (
        "NON_SYNTHETIC_EVALUATION_POLICY",
        "UNTOUCHED_CONFIRMATION_HOLDOUT_DEFINITION",
    )


def test_ten_transition_rules_are_exact_future_only_and_unapplied() -> None:
    artifact = build_family_a_evaluation_holdout_input_register()

    actual = tuple(
        (item.code.value, item.definition, item.reason_code) for item in artifact.transition_rules
    )
    assert actual == c.PHASE20_TRANSITION_RULE_ROWS
    assert all(item.future_only for item in artifact.transition_rules)
    assert all(not item.applied for item in artifact.transition_rules)
    assert all(not item.external_action_authorized for item in artifact.transition_rules)


def test_exact_two_required_evidence_rows_are_missing_and_named_once() -> None:
    artifact = build_family_a_evaluation_holdout_input_register()
    rendered = canonical_evaluation_holdout_input_register_bytes()

    actual = tuple(
        (item.name.value, item.state.value, item.produced, item.reason_code)
        for item in artifact.required_prior_evidence
    )
    assert actual == c.PHASE20_FUTURE_EVIDENCE_ROWS
    keys = _all_mapping_keys(artifact.model_dump(mode="python"))
    for name, _state, _produced, _reason in c.PHASE20_FUTURE_EVIDENCE_ROWS:
        assert name not in keys
        assert rendered.count(name.encode("ascii")) == 1
    assert b"qualification_artifact_set_sha256" not in rendered


def test_phase19_prerequisites_are_preserved_separately_without_upgrade() -> None:
    artifact = build_family_a_evaluation_holdout_input_register()
    actual = tuple(
        (
            item.category.value,
            item.code.value,
            item.evidence_state.value,
            item.requirement_satisfied,
            item.inherited_phase19_prerequisite_sha256,
        )
        for item in artifact.inherited_phase19_prerequisites
    )

    assert actual == c.PHASE20_INHERITED_PREREQUISITE_ROWS
    assert all(item.unchanged for item in artifact.inherited_phase19_prerequisites)


def test_all_phase15_gaps_and_source_plan_steps_are_unchanged() -> None:
    artifact = build_family_a_evaluation_holdout_input_register()

    assert tuple(item.code.value for item in artifact.phase15_gap_bindings) == c.PHASE20_GAP_CODES
    assert tuple(item.state.value for item in artifact.phase15_gap_bindings) == c.PHASE20_GAP_STATES
    assert all(not item.changed_in_phase20 for item in artifact.phase15_gap_bindings)
    assert tuple(item.code.value for item in artifact.source_plan_steps) == c.PHASE20_STEP_CODES
    assert tuple(item.state.value for item in artifact.source_plan_steps) == c.PHASE20_STEP_STATES
    assert all(not item.changed_in_phase20 for item in artifact.source_plan_steps)
    assert all(not item.external_action_authorized for item in artifact.source_plan_steps)
    assert artifact.source_plan_steps[0].state.value == "OUTPUT_FROZEN"
    assert artifact.source_plan_steps[1].state.value == "OUTPUT_FROZEN"
    assert all(item.state.value == "NOT_STARTED" for item in artifact.source_plan_steps[2:])


def test_dependency_groups_gates_and_substitutes_fail_closed() -> None:
    artifact = build_family_a_evaluation_holdout_input_register()

    assert len(artifact.construction_dependency_groups) == 6
    assert len(artifact.construction_gates) == 6
    assert len(artifact.forbidden_substitutes) == 8
    assert all(item.state.value == "BLOCKED" for item in artifact.construction_dependency_groups)
    assert all(item.state.value == "BLOCKED" for item in artifact.construction_gates)
    assert all(not item.passed for item in artifact.construction_gates)
    assert all(item.required_before_observation for item in artifact.construction_gates)
    assert all(item.forbidden for item in artifact.forbidden_substitutes)


def test_every_authority_and_persistence_boundary_remains_closed() -> None:
    rendered = build_family_a_evaluation_holdout_input_register().model_dump(mode="python")
    for field, expected in c.PHASE20_BOUNDARY_VALUES.items():
        assert rendered[field] is expected


def test_committed_artifact_has_exact_generated_bytes() -> None:
    path = Path("docs/PHASE_20_FAMILY_A_EVALUATION_HOLDOUT_INPUT_REGISTER.json")
    assert path.read_bytes() == canonical_evaluation_holdout_input_register_bytes()
