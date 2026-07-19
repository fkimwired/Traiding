from __future__ import annotations

import operator

import pytest
from fable5_data.phase19.assessment import build_family_a_step3_prerequisite_assessment
from fable5_data.phase19.canonical import (
    PHASE19_ARTIFACT_HASH_DOMAIN,
    PHASE19_ASSESSMENT_POLICY_SHA256,
    PHASE19_BOUNDARY_VALUES,
    PHASE19_GAP_BINDING_HASH_DOMAIN,
    PHASE19_PHASE16_ORIGINAL_STEP3_SHA256,
    PHASE19_PHASE18_INHERITED_STEP3_EVIDENCE_SHA256,
    PHASE19_PREREQUISITE_HASH_DOMAIN,
    PHASE19_REQUIRED_EVIDENCE_HASH_DOMAIN,
    PHASE19_STEP_HASH_DOMAIN,
    domain_sha256,
)
from fable5_data.phase19.contracts import (
    EvidenceState,
    FamilyAPhase15GapBinding,
    FamilyARequiredPriorEvidence,
    FamilyASourcePlanStepEvidence,
    FamilyAStep3Prerequisite,
    FamilyAStep3PrerequisiteAssessment,
    RequiredEvidenceState,
)
from pydantic import ValidationError


def _rehash_artifact(payload: dict[str, object]) -> dict[str, object]:
    preimage = {key: value for key, value in payload.items() if key != "artifact_sha256"}
    payload["artifact_sha256"] = domain_sha256(PHASE19_ARTIFACT_HASH_DOMAIN, preimage)
    return payload


def test_exact_frozen_identity_and_blocked_conclusion() -> None:
    artifact = build_family_a_step3_prerequisite_assessment()

    assert str(artifact.artifact_id) == "0b3f9153-71cc-5052-9b47-f714ed17bb99"
    assert artifact.artifact_sha256 == (
        "ed738badfb6e95feb4d7969d299bdc6186ef13ebf0f036134518e147803c72df"
    )
    assert PHASE19_ASSESSMENT_POLICY_SHA256 == (
        "78485a93a2fda0d81ea7d2d7fb179f60ef2aee97616f3981fadabfd72ca02438"
    )
    assert artifact.outcome.value == "BLOCKED"
    assert artifact.assessment_state.value == "OUTPUT_FROZEN"
    assert artifact.aggregate_conclusion.value == ("BLOCKED_MISSING_EVALUATION_POLICY_AND_HOLDOUT")
    assert artifact.frozen_at_utc == "2026-07-19T20:01:39.9672350Z"
    assert len(artifact.prerequisites) == 19
    assert len(artifact.required_prior_evidence) == 2
    assert len(artifact.phase15_gap_bindings) == 19
    assert len(artifact.source_plan_steps) == 7


def test_phase16_and_phase18_step3_hashes_are_bound_distinctly() -> None:
    artifact = build_family_a_step3_prerequisite_assessment()

    assert artifact.phase16_original_step3_sha256 == PHASE19_PHASE16_ORIGINAL_STEP3_SHA256
    assert (
        artifact.phase18_inherited_step3_evidence_sha256
        == PHASE19_PHASE18_INHERITED_STEP3_EVIDENCE_SHA256
    )
    assert artifact.phase16_original_step3_sha256 != (
        artifact.phase18_inherited_step3_evidence_sha256
    )


def test_evidence_state_vocabulary_is_exactly_closed() -> None:
    assert {item.value for item in EvidenceState} == {
        "PRESENT",
        "MOCK_ONLY",
        "STALE",
        "MISSING",
        "UNPROVEN",
    }
    assert {item.value for item in RequiredEvidenceState} == {"MISSING"}


def test_required_evidence_contract_has_no_value_or_evidence_hash_field() -> None:
    schema = FamilyARequiredPriorEvidence.model_json_schema()
    properties = set(schema["properties"])
    assert properties == {
        "schema_version",
        "ordinal",
        "name",
        "state",
        "produced",
        "reason_code",
        "record_sha256",
    }
    row = build_family_a_step3_prerequisite_assessment().required_prior_evidence[0]
    payload = row.model_dump(mode="python")
    payload["value"] = "0" * 64
    with pytest.raises(ValidationError):
        FamilyARequiredPriorEvidence.model_validate(payload)


def test_prerequisite_tamper_is_rejected_even_when_rehashed() -> None:
    row = build_family_a_step3_prerequisite_assessment().prerequisites[0]
    payload = row.model_dump(mode="python")
    payload["evidence_state"] = "PRESENT"
    payload["requirement_satisfied"] = True
    payload["prerequisite_sha256"] = domain_sha256(
        PHASE19_PREREQUISITE_HASH_DOMAIN,
        {key: item for key, item in payload.items() if key != "prerequisite_sha256"},
    )
    with pytest.raises(ValidationError):
        FamilyAStep3Prerequisite.model_validate(payload)


def test_required_evidence_production_tamper_is_rejected_when_rehashed() -> None:
    row = build_family_a_step3_prerequisite_assessment().required_prior_evidence[0]
    payload = row.model_dump(mode="python")
    payload["produced"] = True
    payload["record_sha256"] = domain_sha256(
        PHASE19_REQUIRED_EVIDENCE_HASH_DOMAIN,
        {key: item for key, item in payload.items() if key != "record_sha256"},
    )
    with pytest.raises(ValidationError):
        FamilyARequiredPriorEvidence.model_validate(payload)


def test_inherited_gap_upgrade_is_rejected_even_when_rehashed() -> None:
    gap = build_family_a_step3_prerequisite_assessment().phase15_gap_bindings[1]
    payload = gap.model_dump(mode="python")
    payload["state"] = "PRESENT"
    payload["binding_sha256"] = domain_sha256(
        PHASE19_GAP_BINDING_HASH_DOMAIN,
        {key: item for key, item in payload.items() if key != "binding_sha256"},
    )
    with pytest.raises(ValidationError):
        FamilyAPhase15GapBinding.model_validate(payload)


def test_step3_start_or_output_tamper_is_rejected_when_rehashed() -> None:
    step = build_family_a_step3_prerequisite_assessment().source_plan_steps[2]
    payload = step.model_dump(mode="python")
    payload["state"] = "OUTPUT_FROZEN"
    payload["external_action_authorized"] = True
    payload["step_sha256"] = domain_sha256(
        PHASE19_STEP_HASH_DOMAIN,
        {key: item for key, item in payload.items() if key != "step_sha256"},
    )
    with pytest.raises(ValidationError):
        FamilyASourcePlanStepEvidence.model_validate(payload)


@pytest.mark.parametrize(
    "field",
    [
        "operational_source_product_composition_selected",
        "credentials_loaded",
        "rights_verified",
        "non_synthetic_evaluation_policy_created",
        "non_synthetic_evaluation_policy_approved",
        "confirmation_holdout_definition_created",
        "confirmation_holdout_defined",
        "step3_required_prior_evidence_complete",
        "step3_eligible",
        "step3_external_action_authorized",
        "research_ingestion_authorized",
        "research_executed",
        "execution_authorized",
        "order_submission_authorized",
    ],
)
def test_false_authority_tamper_is_rejected_even_when_artifact_rehashed(field: str) -> None:
    payload = build_family_a_step3_prerequisite_assessment().model_dump(mode="python")
    payload[field] = True
    with pytest.raises(ValidationError):
        FamilyAStep3PrerequisiteAssessment.model_validate(_rehash_artifact(payload))


def test_boundary_registry_is_required_and_immutable() -> None:
    required = set(FamilyAStep3PrerequisiteAssessment.model_json_schema()["required"])
    assert set(PHASE19_BOUNDARY_VALUES) <= required
    with pytest.raises(TypeError):
        operator.setitem(  # type: ignore[call-overload]
            PHASE19_BOUNDARY_VALUES,
            "step3_eligible",
            True,
        )

    detached = dict(PHASE19_BOUNDARY_VALUES)
    detached["step3_eligible"] = True
    artifact = build_family_a_step3_prerequisite_assessment()
    assert artifact.step3_eligible is False
    assert artifact.order_submission_authorized is False
