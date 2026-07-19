from __future__ import annotations

import operator

import pytest
from fable5_data.phase18.canonical import (
    PHASE18_ARTIFACT_HASH_DOMAIN,
    PHASE18_BOUNDARY_VALUES,
    PHASE18_FINDING_HASH_DOMAIN,
    PHASE18_OUTPUT_HASH_DOMAIN,
    PHASE18_PHASE16_STEP2_SHA256,
    PHASE18_POLICY_SHA256,
    PHASE18_SOURCE_HASH_DOMAIN,
    PHASE18_STEP_HASH_DOMAIN,
    domain_sha256,
)
from fable5_data.phase18.contracts import (
    FamilyACurrentUseRightsReview,
    FamilyARightsReviewOutput,
    FamilyASourcePlanStepEvidence,
    ProductRightsFinding,
    PublicTermsSource,
    RightsStatus,
)
from fable5_data.phase18.rights_review import build_family_a_current_use_rights_review
from pydantic import ValidationError


def _rehash_artifact(payload: dict[str, object]) -> dict[str, object]:
    preimage = {key: value for key, value in payload.items() if key != "artifact_sha256"}
    payload["artifact_sha256"] = domain_sha256(PHASE18_ARTIFACT_HASH_DOMAIN, preimage)
    return payload


def test_exact_frozen_identity_and_blocked_conclusion() -> None:
    artifact = build_family_a_current_use_rights_review()

    assert str(artifact.artifact_id) == "7008240c-e7a2-5d4b-9345-8c40d2d4c359"
    assert artifact.artifact_sha256 == (
        "2def399ee8c57d7c6d80f5282e856eda1acf34a8504058fbfc8ea2dea4aa30ae"
    )
    assert PHASE18_POLICY_SHA256 == (
        "e175f9b70333899b8c9626e459f091ea5c440494e006c2684448fa15fe0a4fbb"
    )
    assert artifact.independent_rights_review_sha256 == (
        "a0c8808e865931cc88d9f71c578b42edcfb6e279e2426b4b30534d6c4626023b"
    )
    assert artifact.rights_currentness_sha256 == (
        "91b3b711e3c0b1b3b313e8ea45d9b73f96746ed4bd74478a7f6e7553510cdf63"
    )
    assert artifact.phase16_step2_sha256 == PHASE18_PHASE16_STEP2_SHA256
    assert artifact.outcome.value == "BLOCKED"
    assert artifact.aggregate_conclusion.value == "BLOCKED_NO_OPERATIONAL_SELECTION"
    assert artifact.frozen_at_utc == "2026-07-19T15:58:18.5305832Z"
    assert len(artifact.terms_sources) == 24
    assert len(artifact.product_rights_findings) == 9
    assert len(artifact.source_plan_steps) == 7


def test_rights_status_vocabulary_is_exactly_closed() -> None:
    assert {item.value for item in RightsStatus} == {
        "ALLOWED_PUBLIC",
        "CONDITIONAL_ACCOUNT_LICENSE",
        "PRIVATE_LICENSE_REQUIRED",
        "PROHIBITED_PUBLIC_TERMS",
        "UNPROVEN",
    }


def test_exact_eight_dimension_matrix_is_frozen() -> None:
    artifact = build_family_a_current_use_rights_review()
    actual = tuple(
        (
            item.storage.value,
            item.non_display_internal_use.value,
            item.derived_data.value,
            item.retention.value,
            item.redistribution.value,
            item.revocation_currentness.value,
            item.delivery.value,
            item.entitlement.value,
        )
        for item in artifact.product_rights_findings
    )
    tiingo_base = (
        "PROHIBITED_PUBLIC_TERMS",
        "CONDITIONAL_ACCOUNT_LICENSE",
        "PROHIBITED_PUBLIC_TERMS",
        "UNPROVEN",
        "PRIVATE_LICENSE_REQUIRED",
        "CONDITIONAL_ACCOUNT_LICENSE",
        "CONDITIONAL_ACCOUNT_LICENSE",
        "UNPROVEN",
    )
    crsp = (
        "PRIVATE_LICENSE_REQUIRED",
        "PRIVATE_LICENSE_REQUIRED",
        "PRIVATE_LICENSE_REQUIRED",
        "UNPROVEN",
        "PRIVATE_LICENSE_REQUIRED",
        "UNPROVEN",
        "CONDITIONAL_ACCOUNT_LICENSE",
        "PRIVATE_LICENSE_REQUIRED",
    )
    assert actual == (
        tiingo_base,
        (*tiingo_base[:-1], "PRIVATE_LICENSE_REQUIRED"),
        tiingo_base,
        tiingo_base,
        crsp,
        crsp,
        (
            "ALLOWED_PUBLIC",
            "ALLOWED_PUBLIC",
            "ALLOWED_PUBLIC",
            "ALLOWED_PUBLIC",
            "ALLOWED_PUBLIC",
            "UNPROVEN",
            "ALLOWED_PUBLIC",
            "ALLOWED_PUBLIC",
        ),
        (
            "PROHIBITED_PUBLIC_TERMS",
            "PROHIBITED_PUBLIC_TERMS",
            "PROHIBITED_PUBLIC_TERMS",
            "PROHIBITED_PUBLIC_TERMS",
            "PROHIBITED_PUBLIC_TERMS",
            "CONDITIONAL_ACCOUNT_LICENSE",
            "CONDITIONAL_ACCOUNT_LICENSE",
            "UNPROVEN",
        ),
        crsp,
    )


def test_public_source_rows_are_review_snapshots_not_remote_byte_attestations() -> None:
    artifact = build_family_a_current_use_rights_review()

    assert all(item.reviewed_at_utc == artifact.frozen_at_utc for item in artifact.terms_sources)
    assert all(item.official_url.startswith("https://") for item in artifact.terms_sources)
    assert all(item.public_metadata_only for item in artifact.terms_sources)
    assert all(item.official_https_citation for item in artifact.terms_sources)
    assert all(item.revalidation_required for item in artifact.terms_sources)
    assert all(not item.terms_body_persisted for item in artifact.terms_sources)
    assert all(not item.remote_source_response_body_persisted for item in artifact.terms_sources)
    assert all(not item.source_content_bytes_captured for item in artifact.terms_sources)
    assert all(not item.content_byte_authenticity_proven for item in artifact.terms_sources)
    assert all(not item.account_specific for item in artifact.terms_sources)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("official_title", "forged title"),
        ("publisher", "forged publisher"),
        ("official_url", "https://example.invalid/terms"),
        ("publisher_last_updated", "2099-01-01"),
        ("locator", "forged locator"),
        ("conservative_fact", "forged fact"),
        ("reviewed_at_utc", "2099-01-01T00:00:00.0000000Z"),
        ("terms_body_persisted", True),
        ("remote_source_response_body_persisted", True),
        ("content_byte_authenticity_proven", True),
        ("revalidation_required", False),
    ],
)
def test_source_tamper_is_rejected_even_when_rehashed(field: str, value: object) -> None:
    source = build_family_a_current_use_rights_review().terms_sources[0]
    payload = source.model_dump(mode="python")
    payload[field] = value
    payload["source_sha256"] = domain_sha256(
        PHASE18_SOURCE_HASH_DOMAIN,
        {key: item for key, item in payload.items() if key != "source_sha256"},
    )
    with pytest.raises(ValidationError):
        PublicTermsSource.model_validate(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("storage", "ALLOWED_PUBLIC"),
        ("derived_data", "ALLOWED_PUBLIC"),
        ("retention", "ALLOWED_PUBLIC"),
        ("redistribution", "ALLOWED_PUBLIC"),
        ("delivery", "ALLOWED_PUBLIC"),
        ("entitlement", "ALLOWED_PUBLIC"),
        ("operational_use_cleared", True),
        ("entitlement_verified", True),
        ("executed_license_reviewed", True),
        ("legal_opinion_obtained", True),
        ("revalidation_required", False),
    ],
)
def test_finding_tamper_is_rejected_even_when_rehashed(field: str, value: object) -> None:
    finding = build_family_a_current_use_rights_review().product_rights_findings[0]
    payload = finding.model_dump(mode="python")
    payload[field] = value
    payload["finding_sha256"] = domain_sha256(
        PHASE18_FINDING_HASH_DOMAIN,
        {key: item for key, item in payload.items() if key != "finding_sha256"},
    )
    with pytest.raises(ValidationError):
        ProductRightsFinding.model_validate(payload)


def test_step2_output_and_later_step_tamper_are_rejected_when_rehashed() -> None:
    artifact = build_family_a_current_use_rights_review()
    output = artifact.source_plan_steps[1].produced_outputs[0].model_dump(mode="python")
    output["name"] = "forged_rights_sha256"
    output["output_sha256"] = domain_sha256(
        PHASE18_OUTPUT_HASH_DOMAIN,
        {key: item for key, item in output.items() if key != "output_sha256"},
    )
    forged = FamilyARightsReviewOutput.model_validate(output)

    step = artifact.source_plan_steps[1].model_dump(mode="python")
    step["produced_outputs"] = (forged, step["produced_outputs"][1])
    step["step_sha256"] = domain_sha256(
        PHASE18_STEP_HASH_DOMAIN,
        {key: item for key, item in step.items() if key != "step_sha256"},
    )
    with pytest.raises(ValidationError):
        FamilyASourcePlanStepEvidence.model_validate(step)

    later = artifact.source_plan_steps[2].model_dump(mode="python")
    later["state"] = "OUTPUT_FROZEN"
    later["step_sha256"] = domain_sha256(
        PHASE18_STEP_HASH_DOMAIN,
        {key: item for key, item in later.items() if key != "step_sha256"},
    )
    with pytest.raises(ValidationError):
        FamilyASourcePlanStepEvidence.model_validate(later)


@pytest.mark.parametrize(
    "field",
    [
        "operational_use_cleared",
        "rights_currentness_guaranteed",
        "provider_selected",
        "product_selected",
        "source_selected",
        "credentials_loaded",
        "rights_verified",
        "rights_granted",
        "research_ingestion_authorized",
        "research_executed",
        "execution_authorized",
        "order_submission_authorized",
    ],
)
def test_false_authority_tamper_is_rejected_even_when_artifact_rehashed(field: str) -> None:
    payload = build_family_a_current_use_rights_review().model_dump(mode="python")
    payload[field] = True
    with pytest.raises(ValidationError):
        FamilyACurrentUseRightsReview.model_validate(_rehash_artifact(payload))


def test_boundary_registry_is_required_and_immutable() -> None:
    required = set(FamilyACurrentUseRightsReview.model_json_schema()["required"])
    assert set(PHASE18_BOUNDARY_VALUES) <= required
    with pytest.raises(TypeError):
        operator.setitem(PHASE18_BOUNDARY_VALUES, "execution_authorized", True)

    detached = dict(PHASE18_BOUNDARY_VALUES)
    detached["rights_granted"] = True
    artifact = build_family_a_current_use_rights_review()
    assert artifact.rights_granted is False
    assert artifact.execution_authorized is False
    assert artifact.policy_sha256 == PHASE18_POLICY_SHA256
