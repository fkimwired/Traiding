from __future__ import annotations

import json

import pytest
from fable5_data.phase23 import canonical as c
from fable5_data.phase23.contracts import FamilyARTDSMCurrentUseRightsReview
from fable5_data.phase23.rights_review import build_family_a_rtdsm_current_use_rights_review
from pydantic import ValidationError


def test_phase23_contract_is_closed_frozen_and_hash_bound() -> None:
    artifact = build_family_a_rtdsm_current_use_rights_review()
    assert artifact.outcome.value == "BLOCKED"
    assert artifact.review_state.value == "PUBLIC_TERMS_RIGHTS_REVIEW_FROZEN"
    assert artifact.aggregate_conclusion.value == c.PHASE23_AGGREGATE_CONCLUSION
    assert len(artifact.public_terms_sources) == 3
    assert len(artifact.rights_findings) == 1
    assert len(artifact.future_requirements) == 4
    with pytest.raises(ValidationError):
        FamilyARTDSMCurrentUseRightsReview.model_validate(
            {**artifact.model_dump(mode="json"), "unknown": True}
        )
    with pytest.raises(ValidationError):
        artifact.outcome = "PASS"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("rights_findings", 0, "persistent_storage"), "EXPRESSLY_PERMITTED_RESEARCH_PURPOSE_ONLY"),
        (("rights_findings", 0, "operational_use_cleared"), True),
        (("future_requirements", 0, "satisfied"), True),
        (("future_requirements", 1, "state"), "OUTPUT_FROZEN_BLOCKED"),
        (("rights_granted",), True),
        (("external_data_capture_authorized",), True),
    ],
)
def test_phase23_contract_rejects_authority_and_evidence_upgrades(
    path: tuple[object, ...], value: object
) -> None:
    payload = json.loads(build_family_a_rtdsm_current_use_rights_review().model_dump_json())
    target: object = payload
    for segment in path[:-1]:
        target = target[segment]  # type: ignore[index]
    target[path[-1]] = value  # type: ignore[index]
    with pytest.raises(ValidationError):
        FamilyARTDSMCurrentUseRightsReview.model_validate(payload)


def test_phase23_contract_rejects_source_and_lineage_drift() -> None:
    artifact = build_family_a_rtdsm_current_use_rights_review()
    payload = json.loads(artifact.model_dump_json())
    payload["accepted_phase22_commit_sha"] = "0" * 40
    with pytest.raises(ValidationError):
        FamilyARTDSMCurrentUseRightsReview.model_validate(payload)
    payload = json.loads(artifact.model_dump_json())
    payload["public_terms_sources"][0]["url"] = "https://example.invalid/terms"
    with pytest.raises(ValidationError):
        FamilyARTDSMCurrentUseRightsReview.model_validate(payload)


def test_phase23_hash_domains_are_distinct() -> None:
    domains = {
        c.PHASE23_ARTIFACT_HASH_DOMAIN,
        c.PHASE23_SOURCE_HASH_DOMAIN,
        c.PHASE23_FINDING_HASH_DOMAIN,
        c.PHASE23_REQUIREMENT_HASH_DOMAIN,
        c.PHASE23_SOURCES_MANIFEST_HASH_DOMAIN,
        c.PHASE23_FINDINGS_MANIFEST_HASH_DOMAIN,
        c.PHASE23_REQUIREMENTS_MANIFEST_HASH_DOMAIN,
        c.PHASE23_POLICY_HASH_DOMAIN,
    }
    assert len(domains) == 8
