from __future__ import annotations

import pytest
from fable5_data.phase16.canonical import (
    PHASE16_ARTIFACT_HASH_DOMAIN,
    PHASE16_BOUNDARY_VALUES,
    PHASE16_CANDIDATE_CODES,
    PHASE16_CANDIDATE_HASH_DOMAIN,
    PHASE16_CANDIDATE_STATES,
    PHASE16_CAPABILITY_CODES,
    PHASE16_GAP_BINDING_HASH_DOMAIN,
    PHASE16_PHASE15_GAP_CODES,
    PHASE16_PHASE15_GAP_STATES,
    PHASE16_POLICY_SHA256,
    PHASE16_REQUIREMENT_CODES,
    PHASE16_REQUIREMENT_HASH_DOMAIN,
    PHASE16_STEP_CODES,
    PHASE16_STEP_HASH_DOMAIN,
    domain_sha256,
)
from fable5_data.phase16.contracts import (
    FamilyAPointInTimeSourcePlan,
    FamilyASourceCandidate,
    FamilyASourcePlanOutcome,
    FamilyASourcePlanRequirement,
    FamilyASourcePlanRequirementReason,
    FamilyASourcePlanRequirementStatus,
    FamilyASourcePlanStep,
    Phase15GapBinding,
    requirements_manifest_sha256,
)
from fable5_data.phase16.plan import build_family_a_point_in_time_source_plan
from pydantic import ValidationError


def _rehash_artifact(payload: dict[str, object]) -> dict[str, object]:
    preimage = {key: value for key, value in payload.items() if key != "artifact_sha256"}
    payload["artifact_sha256"] = domain_sha256(PHASE16_ARTIFACT_HASH_DOMAIN, preimage)
    return payload


def test_exact_closed_registries_and_outcomes() -> None:
    artifact = build_family_a_point_in_time_source_plan()

    assert PHASE16_POLICY_SHA256 == (
        "57cfcfd09f2d4a87d9562fd536228b9f05693bb71b7e9d1867618a35da7d4efd"
    )
    assert str(artifact.artifact_id) == "e106a766-5cfe-5a1c-94f6-ee1c2ac68652"
    assert tuple(item.value for item in FamilyASourcePlanOutcome) == ("PLAN_FROZEN", "BLOCKED")
    assert tuple(item.value for item in FamilyASourcePlanRequirementStatus) == (
        "PASS",
        "BLOCKED",
        "UNCOMPUTABLE",
    )
    assert tuple(item.code.value for item in artifact.requirements) == PHASE16_REQUIREMENT_CODES
    assert tuple(item.code.value for item in artifact.capabilities) == PHASE16_CAPABILITY_CODES
    assert tuple(item.code.value for item in artifact.candidates) == PHASE16_CANDIDATE_CODES
    assert tuple(item.state.value for item in artifact.candidates) == PHASE16_CANDIDATE_STATES
    assert tuple(item.code.value for item in artifact.future_steps) == PHASE16_STEP_CODES
    assert {item.state for item in artifact.future_steps} == {"NOT_STARTED"}
    assert (
        tuple(item.code.value for item in artifact.phase15_gap_bindings)
        == PHASE16_PHASE15_GAP_CODES
    )
    assert (
        tuple(item.state.value for item in artifact.phase15_gap_bindings)
        == PHASE16_PHASE15_GAP_STATES
    )


@pytest.mark.parametrize(
    "field",
    [
        "external_request_performed",
        "provider_selected",
        "credentials_loaded",
        "rights_verified",
        "licensed_data_persisted",
        "research_ingestion_authorized",
        "evaluation_policy_approved",
        "confirmation_holdout_opened",
        "research_executed",
        "performance_computed",
        "risk_clearance_granted",
        "order_submission_authorized",
    ],
)
def test_false_authority_boundary_tamper_is_rejected(field: str) -> None:
    payload = build_family_a_point_in_time_source_plan().model_dump(mode="python")
    payload[field] = True
    with pytest.raises(ValidationError):
        FamilyAPointInTimeSourcePlan.model_validate(_rehash_artifact(payload))


def test_candidate_selection_and_state_tamper_is_rejected_even_when_rehashed() -> None:
    candidate = build_family_a_point_in_time_source_plan().candidates[0].model_dump(mode="python")
    candidate["candidate_only"] = False
    candidate["candidate_sha256"] = domain_sha256(
        PHASE16_CANDIDATE_HASH_DOMAIN,
        {key: value for key, value in candidate.items() if key != "candidate_sha256"},
    )
    with pytest.raises(ValidationError):
        FamilyASourceCandidate.model_validate(candidate)

    candidate = build_family_a_point_in_time_source_plan().candidates[0].model_dump(mode="python")
    candidate["selected"] = True
    candidate["candidate_sha256"] = domain_sha256(
        PHASE16_CANDIDATE_HASH_DOMAIN,
        {key: value for key, value in candidate.items() if key != "candidate_sha256"},
    )
    with pytest.raises(ValidationError):
        FamilyASourceCandidate.model_validate(candidate)

    candidate = build_family_a_point_in_time_source_plan().candidates[0].model_dump(mode="python")
    candidate["state"] = "MISSING"
    candidate["candidate_sha256"] = domain_sha256(
        PHASE16_CANDIDATE_HASH_DOMAIN,
        {key: value for key, value in candidate.items() if key != "candidate_sha256"},
    )
    with pytest.raises(ValidationError, match="state"):
        FamilyASourceCandidate.model_validate(candidate)


def test_phase15_gap_state_tamper_is_rejected_even_when_rehashed() -> None:
    binding = (
        build_family_a_point_in_time_source_plan().phase15_gap_bindings[0].model_dump(mode="python")
    )
    binding["state"] = "PRESENT"
    binding["binding_sha256"] = domain_sha256(
        PHASE16_GAP_BINDING_HASH_DOMAIN,
        {key: value for key, value in binding.items() if key != "binding_sha256"},
    )
    with pytest.raises(ValidationError, match="unchanged"):
        Phase15GapBinding.model_validate(binding)


def test_qualification_step_requires_policy_and_holdout_evidence() -> None:
    step = build_family_a_point_in_time_source_plan().future_steps[2].model_dump(mode="python")
    assert step["required_prior_evidence"] == (
        "non_synthetic_evaluation_policy_sha256",
        "confirmation_holdout_definition_sha256",
    )
    step["required_prior_evidence"] = ()
    step["step_sha256"] = domain_sha256(
        PHASE16_STEP_HASH_DOMAIN,
        {key: value for key, value in step.items() if key != "step_sha256"},
    )
    with pytest.raises(ValidationError, match="prior evidence"):
        FamilyASourcePlanStep.model_validate(step)


def test_nonpassing_requirement_can_only_produce_blocked() -> None:
    original = build_family_a_point_in_time_source_plan()
    first = original.requirements[0].model_dump(mode="python")
    first["status"] = FamilyASourcePlanRequirementStatus.BLOCKED
    first["reason_code"] = FamilyASourcePlanRequirementReason.REQUIREMENT_BLOCKED
    first["requirement_sha256"] = domain_sha256(
        PHASE16_REQUIREMENT_HASH_DOMAIN,
        {key: value for key, value in first.items() if key != "requirement_sha256"},
    )
    requirements = (FamilyASourcePlanRequirement.model_validate(first), *original.requirements[1:])
    payload = original.model_dump(mode="python")
    payload["requirements"] = requirements
    payload["requirements_manifest_sha256"] = requirements_manifest_sha256(requirements)
    payload["outcome"] = FamilyASourcePlanOutcome.BLOCKED
    blocked = FamilyAPointInTimeSourcePlan.model_validate(_rehash_artifact(payload))
    assert blocked.outcome is FamilyASourcePlanOutcome.BLOCKED

    payload = blocked.model_dump(mode="python")
    payload["outcome"] = FamilyASourcePlanOutcome.PLAN_FROZEN
    with pytest.raises(ValidationError, match="outcome"):
        FamilyAPointInTimeSourcePlan.model_validate(_rehash_artifact(payload))


def test_every_boundary_field_is_required() -> None:
    required = set(FamilyAPointInTimeSourcePlan.model_json_schema()["required"])
    assert set(PHASE16_BOUNDARY_VALUES) <= required
    assert "credentials_loaded" in required
    assert "evaluation_policy_approved" in required
    assert "credential_loaded" not in required
    assert "non_synthetic_evaluation_policy_approved" not in required
