from __future__ import annotations

import json

from fable5_data.phase23 import canonical as c
from fable5_data.phase23.rights_review import (
    build_family_a_rtdsm_current_use_rights_review,
    canonical_rtdsm_current_use_rights_review_bytes,
)


def test_phase23_builder_is_deterministic_and_canonical() -> None:
    first = canonical_rtdsm_current_use_rights_review_bytes()
    second = canonical_rtdsm_current_use_rights_review_bytes()
    assert first == second
    assert first.endswith(b"\n")
    assert b"\r" not in first
    assert (
        json.dumps(json.loads(first), sort_keys=True, separators=(",", ":")).encode() + b"\n"
        == first
    )


def test_phase23_finding_is_truthfully_blocked() -> None:
    artifact = build_family_a_rtdsm_current_use_rights_review()
    finding = artifact.rights_findings[0]
    assert finding.product_code == c.PHASE23_PRODUCT_CODE
    assert finding.research_purpose.value == "EXPRESSLY_PERMITTED_RESEARCH_PURPOSE_ONLY"
    for field in (
        "persistent_storage",
        "automated_model_internal_use",
        "derived_data",
        "retention_deletion",
        "redistribution",
        "attribution",
    ):
        assert getattr(finding, field).value == "NOT_EXPRESSLY_ADDRESSED"
    assert finding.third_party_content.value == "OWNER_PERMISSION_REQUIRED_WHEN_COPYRIGHTED"
    assert finding.revocation_currentness.value == "CHANGE_WITHOUT_NOTICE_REVALIDATION_REQUIRED"
    assert finding.operational_use_cleared is False
    assert finding.legal_opinion_obtained is False


def test_phase23_only_projects_the_first_requirement_to_blocked_output() -> None:
    artifact = build_family_a_rtdsm_current_use_rights_review()
    states = [row.state.value for row in artifact.future_requirements]
    assert states == ["OUTPUT_FROZEN_BLOCKED", "NOT_STARTED", "NOT_STARTED", "BLOCKED"]
    assert [row.review_output_produced for row in artifact.future_requirements] == [
        True,
        False,
        False,
        False,
    ]
    assert all(not row.satisfied for row in artifact.future_requirements)
    assert all(not row.external_action_authorized for row in artifact.future_requirements)


def test_phase23_preserves_all_false_authority_boundaries() -> None:
    artifact = build_family_a_rtdsm_current_use_rights_review()
    dumped = artifact.model_dump(mode="python")
    for field, expected in c.PHASE23_BOUNDARY_VALUES.items():
        assert dumped[field] is expected
