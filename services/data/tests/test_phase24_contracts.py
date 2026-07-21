from __future__ import annotations

import json

import pytest
from fable5_data.phase24 import canonical as c
from fable5_data.phase24.contracts import FamilyARTDSMRightsClarificationRequirements
from fable5_data.phase24.rights_clarification import (
    build_family_a_rtdsm_rights_clarification_requirements,
)
from pydantic import ValidationError


def test_phase24_contract_is_closed_frozen_and_hash_bound() -> None:
    artifact = build_family_a_rtdsm_rights_clarification_requirements()
    assert artifact.outcome.value == "BLOCKED"
    assert artifact.requirements_state.value == "RIGHTS_CLARIFICATION_REQUIREMENTS_FROZEN"
    assert artifact.aggregate_conclusion.value == c.PHASE24_AGGREGATE_CONCLUSION
    assert (
        len(artifact.proposed_use_disclosures),
        len(artifact.clarification_questions),
        len(artifact.evidence_requirements),
        len(artifact.transition_rules),
    ) == (8, 10, 6, 7)
    with pytest.raises(ValidationError):
        FamilyARTDSMRightsClarificationRequirements.model_validate(
            {**artifact.model_dump(mode="json"), "unknown": True}
        )
    with pytest.raises(ValidationError):
        artifact.outcome = "PASS"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("proposed_use_disclosures", 0, "status"), "AUTHORIZED"),
        (("clarification_questions", 0, "state"), "VERIFIED_PERMITTED"),
        (("clarification_questions", 0, "answer_evidence_present"), True),
        (("evidence_requirements", 0, "state"), "PRESENT"),
        (("transition_rules", 0, "applied"), True),
        (("rights_granted",), True),
        (("provider_contact_performed",), True),
        (("external_data_capture_authorized",), True),
    ],
)
def test_phase24_contract_rejects_authority_and_evidence_upgrades(
    path: tuple[object, ...], value: object
) -> None:
    payload = json.loads(build_family_a_rtdsm_rights_clarification_requirements().model_dump_json())
    target: object = payload
    for segment in path[:-1]:
        target = target[segment]  # type: ignore[index]
    target[path[-1]] = value  # type: ignore[index]
    with pytest.raises(ValidationError):
        FamilyARTDSMRightsClarificationRequirements.model_validate(payload)


def test_phase24_contract_rejects_lineage_and_question_drift() -> None:
    artifact = build_family_a_rtdsm_rights_clarification_requirements()
    payload = json.loads(artifact.model_dump_json())
    payload["accepted_phase23_commit_sha"] = "0" * 40
    with pytest.raises(ValidationError):
        FamilyARTDSMRightsClarificationRequirements.model_validate(payload)
    payload = json.loads(artifact.model_dump_json())
    payload["clarification_questions"][0]["question"] = "May we use it?"
    with pytest.raises(ValidationError):
        FamilyARTDSMRightsClarificationRequirements.model_validate(payload)


def test_phase24_hash_domains_are_distinct() -> None:
    domains = {
        c.PHASE24_ARTIFACT_HASH_DOMAIN,
        c.PHASE24_DISCLOSURE_HASH_DOMAIN,
        c.PHASE24_QUESTION_HASH_DOMAIN,
        c.PHASE24_EVIDENCE_HASH_DOMAIN,
        c.PHASE24_RULE_HASH_DOMAIN,
        c.PHASE24_DISCLOSURES_MANIFEST_HASH_DOMAIN,
        c.PHASE24_QUESTIONS_MANIFEST_HASH_DOMAIN,
        c.PHASE24_EVIDENCE_MANIFEST_HASH_DOMAIN,
        c.PHASE24_RULES_MANIFEST_HASH_DOMAIN,
        c.PHASE24_POLICY_HASH_DOMAIN,
    }
    assert len(domains) == 10
