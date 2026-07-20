from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from fable5_data.phase16.plan import build_family_a_point_in_time_source_plan
from fable5_data.phase17.inventory import build_family_a_candidate_product_inventory
from fable5_data.phase18.rights_review import build_family_a_current_use_rights_review
from fable5_data.phase20.input_register import build_family_a_evaluation_holdout_input_register
from fable5_data.phase21 import canonical as c
from fable5_data.phase21.contracts import (
    candidate_groups_manifest_sha256,
    capabilities_manifest_sha256,
    decision_fields_manifest_sha256,
    dependencies_manifest_sha256,
    evidence_manifest_sha256,
    gaps_manifest_sha256,
    gates_manifest_sha256,
    inputs_manifest_sha256,
    product_rights_manifest_sha256,
    rules_manifest_sha256,
    steps_manifest_sha256,
    substitutes_manifest_sha256,
)
from fable5_data.phase21.decision_requirements import (
    build_family_a_operational_composition_decision_requirements,
    canonical_operational_composition_decision_requirements_bytes,
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


def test_builder_is_byte_deterministic_and_binds_accepted_phase20() -> None:
    first = build_family_a_operational_composition_decision_requirements()
    second = build_family_a_operational_composition_decision_requirements()
    phase20 = build_family_a_evaluation_holdout_input_register()

    assert first == second
    assert canonical_operational_composition_decision_requirements_bytes() == (
        canonical_operational_composition_decision_requirements_bytes()
    )
    assert canonical_operational_composition_decision_requirements_bytes().count(b"\n") == 1
    assert str(first.phase20_artifact_id) == str(phase20.artifact_id)
    assert first.phase20_artifact_sha256 == phase20.artifact_sha256
    assert first.phase20_policy_sha256 == phase20.input_register_policy_sha256
    assert first.phase20_input_requirements_manifest_sha256 == (
        phase20.input_requirements_manifest_sha256
    )


def test_source_candidate_rights_and_capability_hashes_are_exact() -> None:
    artifact = build_family_a_operational_composition_decision_requirements()
    phase16 = build_family_a_point_in_time_source_plan()
    phase17 = build_family_a_candidate_product_inventory()
    phase18 = build_family_a_current_use_rights_review()

    assert tuple(
        (x.candidate_group_code, x.product_codes, x.phase17_candidate_group_sha256)
        for x in artifact.candidate_group_bindings
    ) == tuple(
        (
            x.phase16_candidate_code.value,
            tuple(code.value for code in x.product_codes),
            x.candidate_group_sha256,
        )
        for x in phase17.candidate_groups
    )
    assert tuple(
        (x.product_code, x.phase17_product_sha256, x.phase18_rights_finding_sha256)
        for x in artifact.product_rights_bindings
    ) == tuple(
        (product.code.value, product.product_sha256, finding.finding_sha256)
        for product, finding in zip(phase17.products, phase18.product_rights_findings, strict=True)
    )
    assert tuple(
        (x.capability_code, x.phase16_capability_sha256) for x in artifact.capability_assignments
    ) == tuple((x.code.value, x.capability_sha256) for x in phase16.capabilities)


def test_policy_source_identity_tuples_match_accepted_builders_exactly() -> None:
    phase16 = build_family_a_point_in_time_source_plan()
    phase17 = build_family_a_candidate_product_inventory()
    phase18 = build_family_a_current_use_rights_review()
    phase20 = build_family_a_evaluation_holdout_input_register()
    policy = c._policy_payload()

    assert policy["accepted_phase20_identity"] == (
        "01ed1ff17b91ba6961e02cdf1df3aa3e6be4859a",
        "b7a68998f1c99ed8b19ab08ae8a725726f04c423",
        str(phase20.artifact_id),
        phase20.artifact_sha256,
        phase20.input_register_policy_sha256,
        phase20.inherited_phase19_prerequisites_manifest_sha256,
        phase20.input_requirements_manifest_sha256,
        phase20.required_prior_evidence_manifest_sha256,
        phase20.transition_rules_manifest_sha256,
        phase20.construction_dependency_groups_manifest_sha256,
        phase20.construction_gates_manifest_sha256,
        phase20.forbidden_substitutes_manifest_sha256,
        phase20.phase15_gap_bindings_manifest_sha256,
        phase20.source_plan_steps_manifest_sha256,
        phase20.aggregate_conclusion.value,
    )
    assert policy["phase17_source_identity"] == (
        str(phase17.artifact_id),
        phase17.artifact_sha256,
        phase17.policy_sha256,
        phase17.candidate_product_inventory_sha256,
        phase17.candidate_groups_manifest_sha256,
        phase17.steps_manifest_sha256,
        phase17.outcome.value,
    )
    assert policy["phase18_source_identity"] == (
        str(phase18.artifact_id),
        phase18.artifact_sha256,
        phase18.policy_sha256,
        phase18.terms_sources_manifest_sha256,
        phase18.independent_rights_review_sha256,
        phase18.rights_currentness_sha256,
        phase18.steps_manifest_sha256,
        phase18.outcome.value,
        phase18.aggregate_conclusion.value,
    )
    assert policy["phase16_source_identity"] == (
        str(phase16.artifact_id),
        phase16.artifact_sha256,
        phase16.policy_sha256,
        phase16.requirements_manifest_sha256,
        phase16.capabilities_manifest_sha256,
        phase16.candidates_manifest_sha256,
        phase16.steps_manifest_sha256,
        phase16.gap_bindings_manifest_sha256,
        phase16.outcome.value,
    )


def test_exact_required_counts_and_fail_closed_states() -> None:
    artifact = build_family_a_operational_composition_decision_requirements()

    assert len(artifact.candidate_group_bindings) == 6
    assert len(artifact.product_rights_bindings) == 9
    assert len(artifact.capability_assignments) == 7
    assert len(artifact.decision_fields) == 8
    assert len(artifact.post_selection_dependencies) == 3
    assert len(artifact.decision_gates) == 6
    assert len(artifact.future_rules) == 8
    assert len(artifact.forbidden_substitutes) == 10
    assert all(
        x.candidate_only and not x.operationally_selected and not x.ranked
        for x in artifact.candidate_group_bindings
    )
    assert all(
        not x.operationally_selected and not x.current_rights_verified
        for x in artifact.product_rights_bindings
    )
    assert all(
        x.assignment_state.value == "UNASSIGNED" and not x.assignment_value_present
        for x in artifact.capability_assignments
    )
    assert all(
        x.required and not x.value_present and not x.evidence_produced
        for x in artifact.decision_fields
    )
    assert all(
        x.state.value == "BLOCKED_BY_MISSING_COMPOSITION" and not x.satisfied
        for x in artifact.post_selection_dependencies
    )
    assert all(x.state.value == "BLOCKED" and not x.passed for x in artifact.decision_gates)
    assert all(
        x.future_only and not x.applied and not x.external_action_authorized
        for x in artifact.future_rules
    )
    assert all(x.forbidden for x in artifact.forbidden_substitutes)


def test_all_manifests_recompute_from_exact_rows() -> None:
    a = build_family_a_operational_composition_decision_requirements()
    assert a.candidate_groups_manifest_sha256 == candidate_groups_manifest_sha256(
        a.candidate_group_bindings
    )
    assert a.product_rights_bindings_manifest_sha256 == product_rights_manifest_sha256(
        a.product_rights_bindings
    )
    assert a.capability_assignments_manifest_sha256 == capabilities_manifest_sha256(
        a.capability_assignments
    )
    assert a.decision_fields_manifest_sha256 == decision_fields_manifest_sha256(a.decision_fields)
    assert a.post_selection_dependencies_manifest_sha256 == dependencies_manifest_sha256(
        a.post_selection_dependencies
    )
    assert a.decision_gates_manifest_sha256 == gates_manifest_sha256(a.decision_gates)
    assert a.future_rules_manifest_sha256 == rules_manifest_sha256(a.future_rules)
    assert a.forbidden_substitutes_manifest_sha256 == substitutes_manifest_sha256(
        a.forbidden_substitutes
    )
    assert a.inherited_phase20_inputs_manifest_sha256 == inputs_manifest_sha256(
        a.inherited_phase20_input_requirements
    )
    assert a.required_prior_evidence_manifest_sha256 == evidence_manifest_sha256(
        a.required_prior_evidence
    )
    assert a.phase15_gap_bindings_manifest_sha256 == gaps_manifest_sha256(a.phase15_gap_bindings)
    assert a.source_plan_steps_manifest_sha256 == steps_manifest_sha256(a.source_plan_steps)


def test_all_phase20_inputs_evidence_gaps_and_steps_are_unchanged() -> None:
    artifact = build_family_a_operational_composition_decision_requirements()
    assert len(artifact.inherited_phase20_input_requirements) == 20
    assert all(x.unchanged for x in artifact.inherited_phase20_input_requirements)
    assert (
        tuple(
            x.source_phase20_requirement_sha256
            for x in artifact.inherited_phase20_input_requirements
        )
        == c.PHASE21_PHASE20_INPUT_SHA256S
    )
    assert len(artifact.required_prior_evidence) == 2
    assert all(
        x.unchanged and not x.produced and x.state == "MISSING"
        for x in artifact.required_prior_evidence
    )
    assert tuple(x.code for x in artifact.phase15_gap_bindings) == c.PHASE20_GAP_CODES
    assert tuple(x.state for x in artifact.phase15_gap_bindings) == c.PHASE20_GAP_STATES
    assert all(not x.changed_in_phase21 for x in artifact.phase15_gap_bindings)
    assert tuple(x.code for x in artifact.source_plan_steps) == c.PHASE20_STEP_CODES
    assert tuple(x.state for x in artifact.source_plan_steps) == c.PHASE20_STEP_STATES
    assert all(
        not x.changed_in_phase21 and not x.external_action_authorized
        for x in artifact.source_plan_steps
    )


def test_no_selection_evidence_or_operational_composition_output_value_exists() -> None:
    artifact = build_family_a_operational_composition_decision_requirements()
    keys = _all_mapping_keys(artifact.model_dump(mode="python"))
    rendered = canonical_operational_composition_decision_requirements_bytes()
    assert "selection_evidence_sha256" not in keys
    assert "operational_source_product_composition_sha256" not in keys
    assert "operational_composition_output_sha256" not in keys
    assert b'"field_name":"selection_evidence_sha256"' in rendered


def test_every_authority_and_persistence_boundary_remains_closed() -> None:
    rendered = build_family_a_operational_composition_decision_requirements().model_dump(
        mode="python"
    )
    for field, expected in c.PHASE21_BOUNDARY_VALUES.items():
        assert rendered[field] is expected


def test_committed_artifact_has_exact_generated_bytes() -> None:
    path = Path("docs/PHASE_21_FAMILY_A_OPERATIONAL_COMPOSITION_DECISION_REQUIREMENTS.json")
    assert path.read_bytes() == canonical_operational_composition_decision_requirements_bytes()
