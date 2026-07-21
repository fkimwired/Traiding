from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from fable5_data.phase21.decision_requirements import (
    build_family_a_operational_composition_decision_requirements,
)
from fable5_data.phase22 import canonical as c
from fable5_data.phase22.contracts import (
    groups_manifest_sha256,
    products_manifest_sha256,
    requirements_manifest_sha256,
    sources_manifest_sha256,
)
from fable5_data.phase22.inventory_amendment import (
    build_family_a_macro_vintage_candidate_inventory_amendment,
    canonical_macro_vintage_candidate_inventory_amendment_bytes,
)


def _all_mapping_keys(value: object) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            keys.add(str(key))
            keys.update(_all_mapping_keys(item))
    elif isinstance(value, (tuple, list)):
        for item in value:
            keys.update(_all_mapping_keys(item))
    return keys


def test_builder_is_byte_deterministic_and_binds_accepted_phase21() -> None:
    first = build_family_a_macro_vintage_candidate_inventory_amendment()
    second = build_family_a_macro_vintage_candidate_inventory_amendment()
    phase21 = build_family_a_operational_composition_decision_requirements()

    assert first == second
    assert canonical_macro_vintage_candidate_inventory_amendment_bytes() == (
        canonical_macro_vintage_candidate_inventory_amendment_bytes()
    )
    assert canonical_macro_vintage_candidate_inventory_amendment_bytes().count(b"\n") == 1
    assert str(first.phase21_artifact_id) == str(phase21.artifact_id)
    assert first.phase21_artifact_sha256 == phase21.artifact_sha256
    assert first.phase21_policy_sha256 == phase21.decision_requirements_policy_sha256
    assert first.phase21_candidate_groups_manifest_sha256 == (
        phase21.candidate_groups_manifest_sha256
    )
    assert first.phase21_product_rights_manifest_sha256 == (
        phase21.product_rights_bindings_manifest_sha256
    )
    assert first.phase21_capabilities_manifest_sha256 == (
        phase21.capability_assignments_manifest_sha256
    )
    assert first.phase21_decision_fields_manifest_sha256 == (
        phase21.decision_fields_manifest_sha256
    )
    assert first.phase21_gates_manifest_sha256 == phase21.decision_gates_manifest_sha256
    assert first.phase21_rules_manifest_sha256 == phase21.future_rules_manifest_sha256
    assert first.phase21_aggregate_conclusion == phase21.aggregate_conclusion.value


def test_exact_single_candidate_and_official_fact_scope() -> None:
    artifact = build_family_a_macro_vintage_candidate_inventory_amendment()

    assert len(artifact.official_sources) == 3
    assert len(artifact.candidate_group_amendments) == 1
    assert len(artifact.candidate_products) == 1
    assert len(artifact.future_review_requirements) == 4
    group = artifact.candidate_group_amendments[0]
    product = artifact.candidate_products[0]
    assert group.candidate_group_code.value == ("PHILADELPHIA_FED_RTDSM_MACRO_VINTAGES_CANDIDATE")
    assert tuple(code.value for code in group.product_codes) == (
        "PHILADELPHIA_FED_REAL_TIME_DATA_SET_FOR_MACROECONOMISTS",
    )
    assert product.product_code.value == ("PHILADELPHIA_FED_REAL_TIME_DATA_SET_FOR_MACROECONOMISTS")
    assert tuple(code.value for code in product.capability_codes) == ("macro_regime_inputs",)
    assert "1998:M11" in product.official_fact
    assert product.month_vintage_labels_are_exact_release_timestamps is False
    assert product.bls_release_archive_reconciliation_required is True
    assert all(
        source.official_source and source.citation_inert and not source.remote_body_included
        for source in artifact.official_sources
    )


def test_candidate_rights_fitness_coverage_and_selection_remain_unproven() -> None:
    artifact = build_family_a_macro_vintage_candidate_inventory_amendment()
    group = artifact.candidate_group_amendments[0]
    product = artifact.candidate_products[0]

    assert group.candidate_only and not group.operationally_selected and not group.ranked
    assert product.candidate_only and not product.operationally_selected and not product.ranked
    assert product.review_routing_state.value == (
        "NAMED_FOR_INDEPENDENT_CURRENT_RIGHTS_AND_FITNESS_REVIEW"
    )
    assert product.entitlement_state.value == "UNPROVEN"
    assert product.rights_state.value == "NOT_REVIEWED"
    assert product.fitness_state.value == "UNPROVEN"
    assert product.public_research_use_stated is True
    assert product.persistent_storage_model_derived_retention_rights_reviewed is False
    assert product.coverage_proven is False
    assert product.schema_proven is False
    assert product.current_availability_proven is False
    assert product.external_sample_qualified is False
    assert all(
        not row.external_action_authorized and not row.satisfied
        for row in artifact.future_review_requirements
    )


def test_all_manifests_recompute_from_exact_rows() -> None:
    artifact = build_family_a_macro_vintage_candidate_inventory_amendment()

    assert artifact.official_sources_manifest_sha256 == sources_manifest_sha256(
        artifact.official_sources
    )
    assert artifact.candidate_groups_amendment_manifest_sha256 == groups_manifest_sha256(
        artifact.candidate_group_amendments
    )
    assert artifact.candidate_products_amendment_manifest_sha256 == products_manifest_sha256(
        artifact.candidate_products
    )
    assert artifact.future_review_requirements_manifest_sha256 == (
        requirements_manifest_sha256(artifact.future_review_requirements)
    )


def test_inherited_fred_adverse_finding_is_unchanged() -> None:
    artifact = build_family_a_macro_vintage_candidate_inventory_amendment()

    assert artifact.inherited_fred_product_code == c.PHASE22_INHERITED_FRED_PRODUCT_CODE
    assert artifact.inherited_fred_product_sha256 == c.PHASE22_INHERITED_FRED_PRODUCT_SHA256
    assert artifact.inherited_fred_rights_finding_sha256 == (
        c.PHASE22_INHERITED_FRED_RIGHTS_FINDING_SHA256
    )
    assert artifact.inherited_fred_rights_conclusion == (
        "INELIGIBLE_CURRENT_TERMS_PROHIBIT_PERSISTENCE_AND_SOFTWARE_MODEL_USE"
    )
    assert artifact.inherited_fred_finding_unchanged is True


def test_no_selection_rights_payload_capture_or_operational_value_exists() -> None:
    artifact = build_family_a_macro_vintage_candidate_inventory_amendment()
    keys = _all_mapping_keys(artifact.model_dump(mode="python"))
    rendered = canonical_macro_vintage_candidate_inventory_amendment_bytes().lower()

    for forbidden_key in (
        "selection_evidence_sha256",
        "operational_source_product_composition_sha256",
        "provider_payload",
        "remote_body",
        "credential",
        "account_id",
    ):
        assert forbidden_key not in keys
    for forbidden_value in (b"api_key", b"authorization header", b"raw provider body"):
        assert forbidden_value not in rendered


def test_every_authority_and_persistence_boundary_remains_closed() -> None:
    rendered = build_family_a_macro_vintage_candidate_inventory_amendment().model_dump(
        mode="python"
    )
    for field, expected in c.PHASE22_BOUNDARY_VALUES.items():
        assert rendered[field] is expected


def test_committed_artifact_has_exact_generated_bytes() -> None:
    path = Path("docs/PHASE_22_FAMILY_A_MACRO_VINTAGE_CANDIDATE_INVENTORY_AMENDMENT.json")
    assert path.read_bytes() == canonical_macro_vintage_candidate_inventory_amendment_bytes()
