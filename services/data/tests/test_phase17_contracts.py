from __future__ import annotations

import operator

import pytest
from fable5_data.phase17.canonical import (
    PHASE17_ARTIFACT_HASH_DOMAIN,
    PHASE17_BOUNDARY_VALUES,
    PHASE17_CANDIDATE_HASH_DOMAIN,
    PHASE17_OUTPUT_HASH_DOMAIN,
    PHASE17_PHASE16_STEP1_SHA256,
    PHASE17_POLICY_SHA256,
    PHASE17_PRODUCT_HASH_DOMAIN,
    PHASE17_STEP_HASH_DOMAIN,
    domain_sha256,
)
from fable5_data.phase17.contracts import (
    FamilyACandidateProduct,
    FamilyACandidateProductGroup,
    FamilyACandidateProductInventory,
    FamilyAInventoryOutput,
    FamilyASourcePlanStepEvidence,
)
from fable5_data.phase17.inventory import build_family_a_candidate_product_inventory
from pydantic import ValidationError


def _rehash_artifact(payload: dict[str, object]) -> dict[str, object]:
    preimage = {key: value for key, value in payload.items() if key != "artifact_sha256"}
    payload["artifact_sha256"] = domain_sha256(PHASE17_ARTIFACT_HASH_DOMAIN, preimage)
    return payload


def test_exact_frozen_identity_registries_and_blocked_outcome() -> None:
    artifact = build_family_a_candidate_product_inventory()

    assert str(artifact.artifact_id) == "19d213d5-ec44-53fc-a146-f4f77a06102d"
    assert artifact.artifact_sha256 == (
        "48584cf614c7713b05417a6d9333ca400f2d1c19fb0d3f047ced42e9ef4eb8f4"
    )
    assert PHASE17_POLICY_SHA256 == (
        "0a36f01630a40c55d20139117641abcc8313e5f8b5a0be5fce15fd4c8ad2b3cf"
    )
    assert artifact.candidate_product_inventory_sha256 == (
        "070f36391093385ccd0e7feafc54d18c08e71cc8aa145bd30acea07abbffc76c"
    )
    assert artifact.phase16_step1_sha256 == PHASE17_PHASE16_STEP1_SHA256
    assert artifact.outcome.value == "BLOCKED"
    assert len(artifact.products) == 9
    assert len(artifact.candidate_groups) == 6
    assert len(artifact.source_plan_steps) == 7
    assert tuple(item.code.value for item in artifact.products) == (
        "TIINGO_END_OF_DAY",
        "TIINGO_US_FUNDAMENTALS",
        "TIINGO_DIVIDEND_CORPORATE_ACTIONS",
        "TIINGO_SPLIT_CORPORATE_ACTIONS",
        "MORNINGSTAR_CRSP_US_STOCK_DATABASES",
        "MORNINGSTAR_CRSP_COMPUSTAT_MERGED",
        "SEC_EDGAR_SUBMISSIONS_AND_XBRL_DATA_APIS",
        "FRED_REALTIME_AND_VINTAGE_WEB_SERVICE",
        "LSEG_TICK_HISTORY_INSTRUMENT_AND_VENUE_WEB_API",
    )
    assert tuple(item.state.value for item in artifact.source_plan_steps) == (
        "OUTPUT_FROZEN",
        "NOT_STARTED",
        "NOT_STARTED",
        "NOT_STARTED",
        "NOT_STARTED",
        "NOT_STARTED",
        "NOT_STARTED",
    )


def test_review_metadata_never_becomes_operational_selection_or_rights() -> None:
    artifact = build_family_a_candidate_product_inventory()

    assert all(item.selected_for_independent_rights_review for item in artifact.products)
    assert all(
        not item.operational_provider_selected
        and not item.operational_product_selected
        and not item.operational_source_selected
        and not item.coverage_proven
        and not item.schema_proven
        and not item.current_availability_proven
        and not item.external_sample_qualified
        for item in artifact.products
    )
    assert {item.entitlement_state.value for item in artifact.products} == {"UNPROVEN"}
    assert {item.rights_state.value for item in artifact.products} == {"UNPROVEN"}
    assert {item.fitness_state.value for item in artifact.products} == {"UNPROVEN"}
    assert artifact.products[4].delivery_variant_state.value == "UNPROVEN"
    assert artifact.products[5].delivery_variant_state.value == "UNPROVEN"
    assert artifact.provider_selected is False
    assert artifact.product_selected is False
    assert artifact.source_selected is False
    assert artifact.rights_verified is False
    assert artifact.entitlement_verified is False
    assert artifact.fitness_verified is False
    assert artifact.official_public_documentation_review_performed is True
    assert artifact.provider_data_request_performed is False
    assert artifact.provider_account_verification_performed is False
    assert artifact.entitlement_verification_performed is False


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("official_name", "forged product"),
        ("official_documentation_url", "https://example.invalid/forged"),
        ("official_fact", "forged fact"),
        ("operational_product_selected", True),
        ("rights_state", "PROVEN"),
    ],
)
def test_product_tamper_is_rejected_even_when_rehashed(field: str, value: object) -> None:
    payload = build_family_a_candidate_product_inventory().products[0].model_dump(mode="python")
    payload[field] = value
    payload["product_sha256"] = domain_sha256(
        PHASE17_PRODUCT_HASH_DOMAIN,
        {key: item for key, item in payload.items() if key != "product_sha256"},
    )
    with pytest.raises(ValidationError):
        FamilyACandidateProduct.model_validate(payload)


def test_candidate_group_mapping_and_operational_selection_tamper_are_rejected() -> None:
    group = (
        build_family_a_candidate_product_inventory().candidate_groups[-1].model_dump(mode="python")
    )
    group["single_operational_selection"] = True
    group["candidate_group_sha256"] = domain_sha256(
        PHASE17_CANDIDATE_HASH_DOMAIN,
        {key: item for key, item in group.items() if key != "candidate_group_sha256"},
    )
    with pytest.raises(ValidationError):
        FamilyACandidateProductGroup.model_validate(group)


def test_step_and_output_tamper_are_rejected_even_when_rehashed() -> None:
    artifact = build_family_a_candidate_product_inventory()
    output = artifact.source_plan_steps[0].produced_outputs[0].model_dump(mode="python")
    output["name"] = "rights_currentness_sha256"
    output["output_sha256"] = domain_sha256(
        PHASE17_OUTPUT_HASH_DOMAIN,
        {key: item for key, item in output.items() if key != "output_sha256"},
    )
    forged_output = FamilyAInventoryOutput.model_validate(output)

    step = artifact.source_plan_steps[0].model_dump(mode="python")
    step["produced_outputs"] = (forged_output,)
    step["step_sha256"] = domain_sha256(
        PHASE17_STEP_HASH_DOMAIN,
        {key: item for key, item in step.items() if key != "step_sha256"},
    )
    with pytest.raises(ValidationError):
        FamilyASourcePlanStepEvidence.model_validate(step)

    step = artifact.source_plan_steps[0].model_dump(mode="python")
    step["state"] = "NOT_STARTED"
    step["step_sha256"] = domain_sha256(
        PHASE17_STEP_HASH_DOMAIN,
        {key: item for key, item in step.items() if key != "step_sha256"},
    )
    with pytest.raises(ValidationError):
        FamilyASourcePlanStepEvidence.model_validate(step)


@pytest.mark.parametrize(
    "field",
    [
        "provider_selected",
        "product_selected",
        "source_selected",
        "credentials_loaded",
        "rights_verified",
        "provider_data_request_performed",
        "research_ingestion_authorized",
        "performance_computed",
        "execution_authorized",
        "order_submission_authorized",
    ],
)
def test_false_authority_field_tamper_is_rejected_even_when_artifact_rehashed(field: str) -> None:
    payload = build_family_a_candidate_product_inventory().model_dump(mode="python")
    payload[field] = True
    with pytest.raises(ValidationError):
        FamilyACandidateProductInventory.model_validate(_rehash_artifact(payload))


def test_every_boundary_field_is_required() -> None:
    required = set(FamilyACandidateProductInventory.model_json_schema()["required"])
    assert set(PHASE17_BOUNDARY_VALUES) <= required


def test_boundary_registry_is_immutable_and_cannot_inflate_authority() -> None:
    with pytest.raises(TypeError):
        operator.setitem(
            PHASE17_BOUNDARY_VALUES,
            "execution_authorized",
            True,
        )

    detached = dict(PHASE17_BOUNDARY_VALUES)
    detached["execution_authorized"] = True
    detached["order_submission_authorized"] = True
    artifact = build_family_a_candidate_product_inventory()
    assert artifact.execution_authorized is False
    assert artifact.order_submission_authorized is False
    assert artifact.policy_sha256 == PHASE17_POLICY_SHA256
