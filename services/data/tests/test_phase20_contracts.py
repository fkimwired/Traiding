from __future__ import annotations

import operator

import pytest
from fable5_data.phase20 import canonical as c
from fable5_data.phase20.contracts import (
    EvidenceState,
    FamilyAConstructionGate,
    FamilyAEvaluationHoldoutInputRegister,
    FamilyAEvaluationHoldoutInputRequirement,
    FamilyAForbiddenSubstitute,
    FamilyAFutureEvidenceTransitionRule,
    FamilyAMissingRequiredPriorEvidence,
    FamilyAPhase15GapBinding,
    FamilyASourcePlanStepBinding,
)
from fable5_data.phase20.input_register import build_family_a_evaluation_holdout_input_register
from pydantic import ValidationError


def _rehash_artifact(payload: dict[str, object]) -> dict[str, object]:
    preimage = {key: value for key, value in payload.items() if key != "artifact_sha256"}
    payload["artifact_sha256"] = c.domain_sha256(c.PHASE20_ARTIFACT_HASH_DOMAIN, preimage)
    return payload


def _rehash_row(payload: dict[str, object], hash_field: str, domain: str) -> dict[str, object]:
    preimage = {key: value for key, value in payload.items() if key != hash_field}
    payload[hash_field] = c.domain_sha256(domain, preimage)
    return payload


def test_exact_identity_and_blocked_register_conclusion() -> None:
    artifact = build_family_a_evaluation_holdout_input_register()

    assert str(artifact.artifact_id) == "e501d4f8-bebe-5e68-9457-56f6a589f478"
    assert artifact.artifact_sha256 == (
        "902fca99d4fec1943403cbed406259f86c0eee05c41cb835b6daf7d165db340b"
    )
    assert artifact.input_register_policy_sha256 == (
        "e6be914218dc8b16b2c019ff8d72338dcf495b7cf375cd95281651b89939a31a"
    )
    assert artifact.outcome.value == "BLOCKED"
    assert artifact.register_state.value == "INPUTS_FROZEN"
    assert artifact.aggregate_conclusion.value == (
        "BLOCKED_MISSING_OPERATIONAL_AND_DATA_SPECIFIC_INPUTS"
    )
    assert artifact.frozen_at_utc == "2026-07-20T00:47:38.1976088Z"
    assert len(artifact.inherited_phase19_prerequisites) == 19
    assert len(artifact.input_requirements) == 20
    assert len(artifact.required_prior_evidence) == 2
    assert len(artifact.transition_rules) == 10


def test_evidence_state_vocabulary_is_closed() -> None:
    assert {item.value for item in EvidenceState} == {
        "PRESENT",
        "MOCK_ONLY",
        "STALE",
        "MISSING",
        "UNPROVEN",
    }


def test_input_and_required_evidence_contracts_have_no_value_field() -> None:
    input_properties = set(
        FamilyAEvaluationHoldoutInputRequirement.model_json_schema()["properties"]
    )
    assert "value" not in input_properties
    assert "input_value" not in input_properties
    assert "input_value_present" in input_properties
    assert "related_phase19_prerequisite_codes" in input_properties
    assert "related_phase15_gap_codes" in input_properties

    evidence_properties = set(FamilyAMissingRequiredPriorEvidence.model_json_schema()["properties"])
    assert evidence_properties == {
        "schema_version",
        "ordinal",
        "name",
        "state",
        "produced",
        "reason_code",
        "record_sha256",
    }
    payload = (
        build_family_a_evaluation_holdout_input_register()
        .required_prior_evidence[0]
        .model_dump(mode="python")
    )
    payload["value"] = "0" * 64
    with pytest.raises(ValidationError):
        FamilyAMissingRequiredPriorEvidence.model_validate(payload)


@pytest.mark.parametrize("field", ["input_value_present", "resolves_reserved_evidence"])
def test_input_value_or_resolution_tamper_is_rejected_when_rehashed(field: str) -> None:
    payload = (
        build_family_a_evaluation_holdout_input_register()
        .input_requirements[0]
        .model_dump(mode="python")
    )
    payload[field] = True
    with pytest.raises(ValidationError):
        FamilyAEvaluationHoldoutInputRequirement.model_validate(
            _rehash_row(payload, "requirement_sha256", c.PHASE20_INPUT_REQUIREMENT_HASH_DOMAIN)
        )


def test_input_state_upgrade_is_rejected_when_rehashed() -> None:
    payload = (
        build_family_a_evaluation_holdout_input_register()
        .input_requirements[0]
        .model_dump(mode="python")
    )
    payload["evidence_state"] = "PRESENT"
    payload["requirement_satisfied"] = True
    with pytest.raises(ValidationError):
        FamilyAEvaluationHoldoutInputRequirement.model_validate(
            _rehash_row(payload, "requirement_sha256", c.PHASE20_INPUT_REQUIREMENT_HASH_DOMAIN)
        )


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("related_phase19_prerequisite_codes", []),
        ("related_phase15_gap_codes", ["UNKNOWN_GAP"]),
    ],
)
def test_input_relation_empty_or_unknown_is_rejected_when_rehashed(
    field: str,
    replacement: list[str],
) -> None:
    payload = (
        build_family_a_evaluation_holdout_input_register()
        .input_requirements[3]
        .model_dump(mode="python")
    )
    payload[field] = replacement
    with pytest.raises(ValidationError):
        FamilyAEvaluationHoldoutInputRequirement.model_validate(
            _rehash_row(payload, "requirement_sha256", c.PHASE20_INPUT_REQUIREMENT_HASH_DOMAIN)
        )


def test_input_relation_reordering_is_rejected_when_rehashed() -> None:
    payload = (
        build_family_a_evaluation_holdout_input_register()
        .input_requirements[3]
        .model_dump(mode="python")
    )
    related = list(payload["related_phase19_prerequisite_codes"])
    payload["related_phase19_prerequisite_codes"] = tuple(reversed(related))
    with pytest.raises(ValidationError):
        FamilyAEvaluationHoldoutInputRequirement.model_validate(
            _rehash_row(payload, "requirement_sha256", c.PHASE20_INPUT_REQUIREMENT_HASH_DOMAIN)
        )


def test_transition_application_is_rejected_when_rehashed() -> None:
    payload = (
        build_family_a_evaluation_holdout_input_register()
        .transition_rules[0]
        .model_dump(mode="python")
    )
    payload["applied"] = True
    with pytest.raises(ValidationError):
        FamilyAFutureEvidenceTransitionRule.model_validate(
            _rehash_row(payload, "rule_sha256", c.PHASE20_TRANSITION_RULE_HASH_DOMAIN)
        )


def test_construction_gate_pass_is_rejected_when_rehashed() -> None:
    payload = (
        build_family_a_evaluation_holdout_input_register()
        .construction_gates[0]
        .model_dump(mode="python")
    )
    payload["state"] = "BLOCKED"
    payload["passed"] = True
    with pytest.raises(ValidationError):
        FamilyAConstructionGate.model_validate(
            _rehash_row(payload, "gate_sha256", c.PHASE20_CONSTRUCTION_GATE_HASH_DOMAIN)
        )


def test_forbidden_substitute_clearance_is_rejected_when_rehashed() -> None:
    payload = (
        build_family_a_evaluation_holdout_input_register()
        .forbidden_substitutes[0]
        .model_dump(mode="python")
    )
    payload["forbidden"] = False
    with pytest.raises(ValidationError):
        FamilyAForbiddenSubstitute.model_validate(
            _rehash_row(payload, "substitute_sha256", c.PHASE20_FORBIDDEN_SUBSTITUTE_HASH_DOMAIN)
        )


def test_inherited_gap_upgrade_is_rejected_when_rehashed() -> None:
    payload = (
        build_family_a_evaluation_holdout_input_register()
        .phase15_gap_bindings[1]
        .model_dump(mode="python")
    )
    payload["state"] = "PRESENT"
    payload["changed_in_phase20"] = True
    with pytest.raises(ValidationError):
        FamilyAPhase15GapBinding.model_validate(
            _rehash_row(payload, "binding_sha256", c.PHASE20_GAP_BINDING_HASH_DOMAIN)
        )


def test_step3_start_is_rejected_when_rehashed() -> None:
    payload = (
        build_family_a_evaluation_holdout_input_register()
        .source_plan_steps[2]
        .model_dump(mode="python")
    )
    payload["state"] = "OUTPUT_FROZEN"
    payload["changed_in_phase20"] = True
    payload["external_action_authorized"] = True
    with pytest.raises(ValidationError):
        FamilyASourcePlanStepBinding.model_validate(
            _rehash_row(payload, "binding_sha256", c.PHASE20_STEP_BINDING_HASH_DOMAIN)
        )


@pytest.mark.parametrize(
    "field",
    [
        "operational_source_product_composition_selected",
        "credentials_loaded",
        "rights_verified",
        "external_sample_qualification_authorized",
        "non_synthetic_evaluation_policy_created",
        "non_synthetic_evaluation_policy_approved",
        "confirmation_holdout_definition_created",
        "confirmation_holdout_defined",
        "confirmation_holdout_opened",
        "step3_required_prior_evidence_complete",
        "step3_eligible",
        "step3_external_action_authorized",
        "research_ingestion_authorized",
        "research_executed",
        "execution_authorized",
        "order_submission_authorized",
    ],
)
def test_false_authority_tamper_is_rejected_when_artifact_rehashed(field: str) -> None:
    payload = build_family_a_evaluation_holdout_input_register().model_dump(mode="python")
    payload[field] = True
    with pytest.raises(ValidationError):
        FamilyAEvaluationHoldoutInputRegister.model_validate(_rehash_artifact(payload))


def test_boundary_registry_is_required_and_immutable() -> None:
    required = set(FamilyAEvaluationHoldoutInputRegister.model_json_schema()["required"])
    assert set(c.PHASE20_BOUNDARY_VALUES) <= required
    with pytest.raises(TypeError):
        operator.setitem(  # type: ignore[call-overload]
            c.PHASE20_BOUNDARY_VALUES,
            "step3_eligible",
            True,
        )
