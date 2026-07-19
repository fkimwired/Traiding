from __future__ import annotations

from fable5_data.phase17.inventory import build_family_a_candidate_product_inventory
from fable5_data.phase18.canonical import (
    PHASE18_BOUNDARY_VALUES,
    PHASE18_FROZEN_AT_UTC,
    PHASE18_PHASE17_INVENTORY_SHA256,
    PHASE18_PRODUCT_ROWS,
    PHASE18_SOURCE_ROWS,
)
from fable5_data.phase18.contracts import (
    independent_rights_review_sha256,
    rights_currentness_sha256,
    steps_manifest_sha256,
    terms_sources_manifest_sha256,
)
from fable5_data.phase18.rights_review import (
    build_family_a_current_use_rights_review,
    canonical_current_use_rights_review_bytes,
)


def test_builder_is_byte_deterministic_and_matches_accepted_inventory_lineage() -> None:
    first = build_family_a_current_use_rights_review()
    second = build_family_a_current_use_rights_review()
    phase17 = build_family_a_candidate_product_inventory()

    assert first == second
    assert canonical_current_use_rights_review_bytes() == (
        canonical_current_use_rights_review_bytes()
    )
    assert canonical_current_use_rights_review_bytes().endswith(b"\n")
    assert canonical_current_use_rights_review_bytes().count(b"\n") == 1
    assert first.phase17_candidate_product_inventory_sha256 == (
        phase17.candidate_product_inventory_sha256
    )
    assert first.phase17_candidate_product_inventory_sha256 == PHASE18_PHASE17_INVENTORY_SHA256
    assert first.frozen_at_utc == PHASE18_FROZEN_AT_UTC


def test_all_review_manifests_are_recomputed_from_the_frozen_rows() -> None:
    artifact = build_family_a_current_use_rights_review()
    sources_manifest = terms_sources_manifest_sha256(artifact.terms_sources)

    assert artifact.terms_sources_manifest_sha256 == sources_manifest
    assert artifact.independent_rights_review_sha256 == independent_rights_review_sha256(
        sources_manifest,
        artifact.product_rights_findings,
    )
    assert artifact.rights_currentness_sha256 == rights_currentness_sha256(sources_manifest)
    assert artifact.steps_manifest_sha256 == steps_manifest_sha256(artifact.source_plan_steps)


def test_official_source_catalog_is_exactly_frozen_and_inert() -> None:
    artifact = build_family_a_current_use_rights_review()

    assert (
        tuple(
            (
                item.code.value,
                item.official_title,
                item.publisher,
                item.official_url,
                tuple(code.value for code in item.applies_to_product_codes),
                item.publisher_last_updated,
                item.locator,
                item.conservative_fact,
                item.reviewed_at_utc,
            )
            for item in artifact.terms_sources
        )
        == PHASE18_SOURCE_ROWS
    )
    assert all(item.public_metadata_only for item in artifact.terms_sources)
    assert all(item.official_https_citation for item in artifact.terms_sources)
    assert all(item.revalidation_required for item in artifact.terms_sources)
    assert all(not item.terms_body_persisted for item in artifact.terms_sources)
    assert all(not item.remote_source_response_body_persisted for item in artifact.terms_sources)
    assert all(not item.source_content_bytes_captured for item in artifact.terms_sources)
    assert all(not item.content_byte_authenticity_proven for item in artifact.terms_sources)
    assert all(not item.account_specific for item in artifact.terms_sources)


def test_every_product_finding_matches_its_frozen_source_links_and_conclusion() -> None:
    artifact = build_family_a_current_use_rights_review()

    assert tuple(
        (
            item.product_code.value,
            item.phase17_product_sha256,
            tuple(code.value for code in item.source_codes),
            item.storage.value,
            item.non_display_internal_use.value,
            item.derived_data.value,
            item.retention.value,
            item.redistribution.value,
            item.revocation_currentness.value,
            item.delivery.value,
            item.entitlement.value,
            item.conclusion.value,
            item.conservative_finding,
        )
        for item in artifact.product_rights_findings
    ) == tuple(row[:13] for row in PHASE18_PRODUCT_ROWS)
    source_codes = {item.code for item in artifact.terms_sources}
    assert all(
        set(item.source_codes).issubset(source_codes) for item in artifact.product_rights_findings
    )
    assert all(not item.operational_use_cleared for item in artifact.product_rights_findings)
    assert all(not item.entitlement_verified for item in artifact.product_rights_findings)
    assert all(not item.executed_license_reviewed for item in artifact.product_rights_findings)
    assert all(not item.legal_opinion_obtained for item in artifact.product_rights_findings)
    assert all(item.revalidation_required for item in artifact.product_rights_findings)


def test_steps_one_and_two_are_frozen_and_steps_three_through_seven_are_unstarted() -> None:
    artifact = build_family_a_current_use_rights_review()
    inventory, rights_review, *later = artifact.source_plan_steps

    assert inventory.state.value == "OUTPUT_FROZEN"
    assert tuple(item.name for item in inventory.produced_outputs) == (
        "candidate_product_inventory_sha256",
    )
    assert (
        inventory.produced_outputs[0].sha256 == artifact.phase17_candidate_product_inventory_sha256
    )
    assert rights_review.state.value == "OUTPUT_FROZEN"
    assert tuple(item.name for item in rights_review.produced_outputs) == (
        "independent_rights_review_sha256",
        "rights_currentness_sha256",
    )
    assert tuple(item.sha256 for item in rights_review.produced_outputs) == (
        artifact.independent_rights_review_sha256,
        artifact.rights_currentness_sha256,
    )
    assert all(item.state.value == "NOT_STARTED" for item in later)
    assert all(not item.produced_outputs for item in later)
    assert all(not item.external_action_authorized for item in artifact.source_plan_steps)


def test_public_document_review_does_not_create_operational_selection_or_authority() -> None:
    artifact = build_family_a_current_use_rights_review()

    assert artifact.official_public_terms_review_performed is True
    assert artifact.official_public_documentation_access_performed is True
    assert artifact.independent_technical_rights_review_performed is True
    assert artifact.review_snapshot_only is True
    assert artifact.runtime_network_disabled is True
    assert artifact.revalidation_required_before_external_action is True
    assert artifact.operational_external_request_performed is False
    assert artifact.provider_data_request_performed is False
    assert artifact.provider_account_verification_performed is False
    assert artifact.provider_selected is False
    assert artifact.product_selected is False
    assert artifact.source_selected is False


def test_public_sec_rights_do_not_override_fitness_currentness_or_execution_gates() -> None:
    artifact = build_family_a_current_use_rights_review()
    sec = artifact.product_rights_findings[6]
    fred = artifact.product_rights_findings[7]

    assert sec.product_code.value == "SEC_EDGAR_SUBMISSIONS_AND_XBRL_DATA_APIS"
    assert sec.storage.value == "ALLOWED_PUBLIC"
    assert sec.entitlement.value == "ALLOWED_PUBLIC"
    assert sec.revocation_currentness.value == "UNPROVEN"
    assert sec.conclusion.value == "RIGHTS_SUPPORTED_PUBLIC_POLICY_FITNESS_UNPROVEN"
    assert fred.storage.value == "PROHIBITED_PUBLIC_TERMS"
    assert fred.non_display_internal_use.value == "PROHIBITED_PUBLIC_TERMS"
    assert fred.retention.value == "PROHIBITED_PUBLIC_TERMS"
    assert fred.conclusion.value == (
        "INELIGIBLE_CURRENT_TERMS_PROHIBIT_PERSISTENCE_AND_SOFTWARE_MODEL_USE"
    )
    assert artifact.fitness_verified is False
    assert artifact.current_availability_proven is False
    assert artifact.external_sample_qualified is False
    assert artifact.external_data_capture_authorized is False
    assert artifact.execution_authorized is False
    assert artifact.order_submission_authorized is False


def test_every_authority_and_persistence_boundary_remains_closed() -> None:
    rendered = build_family_a_current_use_rights_review().model_dump(mode="python")
    for field, expected in PHASE18_BOUNDARY_VALUES.items():
        assert rendered[field] is expected
