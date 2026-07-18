from __future__ import annotations

import pytest
from fable5_data.phase15.canonical import (
    PHASE15_ARTIFACT_HASH_DOMAIN,
    PHASE15_GAP_CODES,
    PHASE15_GAP_HASH_DOMAIN,
    PHASE15_GAP_STATES,
    PHASE15_POLICY_ID,
    PHASE15_POLICY_SHA256,
    PHASE15_REQUIREMENT_CODES,
    PHASE15_REQUIREMENT_HASH_DOMAIN,
    domain_sha256,
)
from fable5_data.phase15.contracts import (
    FamilyAResearchAdmissionGap,
    FamilyAResearchAdmissionGapCode,
    FamilyAResearchAdmissionGapState,
    FamilyAResearchAdmissionOutcome,
    FamilyAResearchAdmissionRequirement,
    FamilyAResearchAdmissionRequirementCode,
    FamilyAResearchAdmissionRequirementReason,
    FamilyAResearchAdmissionRequirementStatus,
    FamilyAResearchAdmissionSpecification,
    gaps_manifest_sha256,
    requirements_manifest_sha256,
)
from fable5_data.phase15.specification import (
    build_family_a_research_admission_specification,
)
from pydantic import ValidationError


def _rehash_artifact(payload: dict[str, object]) -> dict[str, object]:
    preimage = {key: value for key, value in payload.items() if key != "artifact_sha256"}
    payload["artifact_sha256"] = domain_sha256(PHASE15_ARTIFACT_HASH_DOMAIN, preimage)
    return payload


def test_closed_vocabularies_and_exact_registries_are_frozen() -> None:
    assert tuple(item.value for item in FamilyAResearchAdmissionOutcome) == (
        "REQUIREMENTS_FROZEN",
        "BLOCKED",
    )
    assert tuple(item.value for item in FamilyAResearchAdmissionRequirementStatus) == (
        "PASS",
        "BLOCKED",
        "UNCOMPUTABLE",
    )
    assert tuple(item.value for item in FamilyAResearchAdmissionGapState) == (
        "PRESENT",
        "MOCK_ONLY",
        "STALE",
        "MISSING",
        "UNPROVEN",
    )
    assert tuple(item.value for item in FamilyAResearchAdmissionRequirementCode) == (
        PHASE15_REQUIREMENT_CODES
    )
    assert tuple(item.value for item in FamilyAResearchAdmissionGapCode) == PHASE15_GAP_CODES
    assert PHASE15_POLICY_ID == "phase15-family-a-research-admission-policy-v1"
    assert len(PHASE15_REQUIREMENT_CODES) == 15
    assert len(PHASE15_GAP_CODES) == len(PHASE15_GAP_STATES) == 19


def test_complete_specification_round_trips_strictly_and_is_hash_bound() -> None:
    artifact = build_family_a_research_admission_specification()

    assert artifact.outcome is FamilyAResearchAdmissionOutcome.REQUIREMENTS_FROZEN
    assert len(artifact.requirements) == 15
    assert len(artifact.gaps) == 19
    assert all(
        item.status is FamilyAResearchAdmissionRequirementStatus.PASS
        for item in artifact.requirements
    )
    assert (
        FamilyAResearchAdmissionSpecification.model_validate_json(
            artifact.model_dump_json(), strict=True
        )
        == artifact
    )
    assert artifact.policy_sha256 == PHASE15_POLICY_SHA256


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("external_data_capture_authorized", True),
        ("licensed_data_persisted", True),
        ("research_data_eligible", True),
        ("research_executed", True),
        ("performance_computed", True),
        ("strategy_promotion_authorized", True),
        ("risk_clearance_granted", True),
        ("order_submission_authorized", True),
        ("live_path_absent", False),
        ("no_real_performance_claimed", False),
    ],
)
def test_authority_and_safety_boundary_tamper_is_rejected(field: str, value: bool) -> None:
    payload = build_family_a_research_admission_specification().model_dump(mode="python")
    payload[field] = value
    _rehash_artifact(payload)

    with pytest.raises(ValidationError):
        FamilyAResearchAdmissionSpecification.model_validate(payload)


def test_rehashed_requirement_definition_tamper_is_rejected() -> None:
    artifact = build_family_a_research_admission_specification()
    requirement = artifact.requirements[0].model_dump(mode="python")
    requirement["definition"] = "forged definition"
    requirement["requirement_sha256"] = domain_sha256(
        PHASE15_REQUIREMENT_HASH_DOMAIN,
        {key: value for key, value in requirement.items() if key != "requirement_sha256"},
    )

    with pytest.raises(ValidationError, match="definition"):
        FamilyAResearchAdmissionRequirement.model_validate(requirement)


@pytest.mark.parametrize("field", ["state", "summary", "evidence_refs"])
def test_rehashed_gap_semantic_tamper_is_rejected(field: str) -> None:
    artifact = build_family_a_research_admission_specification()
    gap = artifact.gaps[0].model_dump(mode="python")
    gap[field] = {
        "state": FamilyAResearchAdmissionGapState.PRESENT,
        "summary": "forged summary",
        "evidence_refs": ("docs/forged.md#forged",),
    }[field]
    gap["gap_sha256"] = domain_sha256(
        PHASE15_GAP_HASH_DOMAIN,
        {key: value for key, value in gap.items() if key != "gap_sha256"},
    )

    with pytest.raises(ValidationError):
        FamilyAResearchAdmissionGap.model_validate(gap)


def test_nonpassing_requirement_can_only_produce_blocked_artifact() -> None:
    original = build_family_a_research_admission_specification()
    first = original.requirements[0].model_dump(mode="python")
    first["status"] = FamilyAResearchAdmissionRequirementStatus.BLOCKED
    first["reason_code"] = FamilyAResearchAdmissionRequirementReason.REQUIREMENT_BLOCKED
    first["requirement_sha256"] = domain_sha256(
        PHASE15_REQUIREMENT_HASH_DOMAIN,
        {key: value for key, value in first.items() if key != "requirement_sha256"},
    )
    requirements = (
        FamilyAResearchAdmissionRequirement.model_validate(first),
        *original.requirements[1:],
    )
    payload = original.model_dump(mode="python")
    payload["requirements"] = requirements
    payload["requirements_manifest_sha256"] = requirements_manifest_sha256(requirements)
    payload["gaps_manifest_sha256"] = gaps_manifest_sha256(original.gaps)
    payload["outcome"] = FamilyAResearchAdmissionOutcome.BLOCKED
    blocked = FamilyAResearchAdmissionSpecification.model_validate(_rehash_artifact(payload))

    assert blocked.outcome is FamilyAResearchAdmissionOutcome.BLOCKED

    payload = blocked.model_dump(mode="python")
    payload["outcome"] = FamilyAResearchAdmissionOutcome.REQUIREMENTS_FROZEN
    with pytest.raises(ValidationError, match="outcome"):
        FamilyAResearchAdmissionSpecification.model_validate(_rehash_artifact(payload))


def test_every_authority_boundary_field_is_required_by_schema() -> None:
    required = set(FamilyAResearchAdmissionSpecification.model_json_schema()["required"])
    assert {
        "external_request_performed",
        "external_data_capture_authorized",
        "provider_payload_persisted",
        "licensed_data_persisted",
        "research_ingestion_authorized",
        "research_snapshot_created",
        "research_data_eligible",
        "research_run_created",
        "research_run_authorized",
        "research_executed",
        "performance_computed",
        "pass_research_granted",
        "strategy_promotion_authorized",
        "paper_approval_granted",
        "risk_clearance_granted",
        "strategy_execution_eligible",
        "execution_authorized",
        "order_submission_authorized",
        "live_path_absent",
        "no_personalized_investment_advice",
        "no_real_performance_claimed",
    } <= required
