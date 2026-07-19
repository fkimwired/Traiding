"""Pure deterministic builder for the Phase 17 candidate-product inventory."""

from __future__ import annotations

from fable5_data.phase17.canonical import (
    PHASE17_ACCEPTED_PHASE16_COMMIT_SHA,
    PHASE17_ACCEPTED_PHASE16_TREE_SHA,
    PHASE17_ARTIFACT_HASH_DOMAIN,
    PHASE17_ARTIFACT_SCHEMA_VERSION,
    PHASE17_BLOCK_REASON,
    PHASE17_BOUNDARY_VALUES,
    PHASE17_CANDIDATE_GROUP_ROWS,
    PHASE17_CANDIDATE_HASH_DOMAIN,
    PHASE17_CANDIDATE_SCHEMA_VERSION,
    PHASE17_DISCLAIMER,
    PHASE17_FAMILY,
    PHASE17_FROZEN_AT_UTC,
    PHASE17_OUTPUT_HASH_DOMAIN,
    PHASE17_OUTPUT_SCHEMA_VERSION,
    PHASE17_PHASE16_ARTIFACT_ID,
    PHASE17_PHASE16_ARTIFACT_SHA256,
    PHASE17_PHASE16_CANDIDATES_MANIFEST_SHA256,
    PHASE17_PHASE16_CAPABILITIES_MANIFEST_SHA256,
    PHASE17_PHASE16_GAP_BINDINGS_MANIFEST_SHA256,
    PHASE17_PHASE16_POLICY_SHA256,
    PHASE17_PHASE16_REQUIREMENTS_MANIFEST_SHA256,
    PHASE17_PHASE16_STEP1_SHA256,
    PHASE17_PHASE16_STEPS_MANIFEST_SHA256,
    PHASE17_POLICY_ID,
    PHASE17_POLICY_SHA256,
    PHASE17_PRODUCT_HASH_DOMAIN,
    PHASE17_PRODUCT_ROWS,
    PHASE17_PRODUCT_SCHEMA_VERSION,
    PHASE17_STEP_CODES,
    PHASE17_STEP_HASH_DOMAIN,
    PHASE17_STEP_PREREQUISITES,
    PHASE17_STEP_REQUIRED_OUTPUTS,
    PHASE17_STEP_REQUIRED_PRIOR_EVIDENCE,
    PHASE17_STEP_SCHEMA_VERSION,
    PHASE17_STEP_STATES,
    canonical_json_bytes,
    domain_sha256,
    identity,
)
from fable5_data.phase17.contracts import (
    FamilyACandidateProduct,
    FamilyACandidateProductGroup,
    FamilyACandidateProductInventory,
    FamilyAInventoryOutput,
    FamilyASourcePlanStepEvidence,
    candidate_groups_manifest_sha256,
    products_manifest_sha256,
    steps_manifest_sha256,
)


def _products() -> tuple[FamilyACandidateProduct, ...]:
    products: list[FamilyACandidateProduct] = []
    for ordinal, row in enumerate(PHASE17_PRODUCT_ROWS, start=1):
        payload = {
            "schema_version": PHASE17_PRODUCT_SCHEMA_VERSION,
            "ordinal": ordinal,
            "code": row[0],
            "phase16_candidate_code": row[1],
            "official_name": row[2],
            "official_documentation_url": row[3],
            "official_fact": row[4],
            "capability_codes": row[5],
            "selected_for_independent_rights_review": True,
            "operational_provider_selected": False,
            "operational_product_selected": False,
            "operational_source_selected": False,
            "entitlement_state": "UNPROVEN",
            "rights_state": "UNPROVEN",
            "fitness_state": "UNPROVEN",
            "coverage_proven": False,
            "schema_proven": False,
            "current_availability_proven": False,
            "external_sample_qualified": False,
            "delivery_variant_state": row[6],
        }
        products.append(
            FamilyACandidateProduct.model_validate(
                {
                    **payload,
                    "product_sha256": domain_sha256(PHASE17_PRODUCT_HASH_DOMAIN, payload),
                }
            )
        )
    return tuple(products)


def _candidate_groups() -> tuple[FamilyACandidateProductGroup, ...]:
    groups: list[FamilyACandidateProductGroup] = []
    for ordinal, row in enumerate(PHASE17_CANDIDATE_GROUP_ROWS, start=1):
        payload = {
            "schema_version": PHASE17_CANDIDATE_SCHEMA_VERSION,
            "ordinal": ordinal,
            "phase16_candidate_code": row[0],
            "product_codes": row[1],
            "selected_for_independent_rights_review": True,
            "selection_state": "NAMED_FOR_INDEPENDENT_RIGHTS_REVIEW",
            "single_operational_selection": False,
        }
        groups.append(
            FamilyACandidateProductGroup.model_validate(
                {
                    **payload,
                    "candidate_group_sha256": domain_sha256(PHASE17_CANDIDATE_HASH_DOMAIN, payload),
                }
            )
        )
    return tuple(groups)


def _inventory_output(inventory_sha256: str) -> FamilyAInventoryOutput:
    payload = {
        "schema_version": PHASE17_OUTPUT_SCHEMA_VERSION,
        "name": "candidate_product_inventory_sha256",
        "sha256": inventory_sha256,
    }
    return FamilyAInventoryOutput.model_validate(
        {
            **payload,
            "output_sha256": domain_sha256(PHASE17_OUTPUT_HASH_DOMAIN, payload),
        }
    )


def _source_plan_steps(inventory_sha256: str) -> tuple[FamilyASourcePlanStepEvidence, ...]:
    steps: list[FamilyASourcePlanStepEvidence] = []
    inventory_output = _inventory_output(inventory_sha256)
    for ordinal, code in enumerate(PHASE17_STEP_CODES, start=1):
        index = ordinal - 1
        payload = {
            "schema_version": PHASE17_STEP_SCHEMA_VERSION,
            "ordinal": ordinal,
            "code": code,
            "state": PHASE17_STEP_STATES[index],
            "reason_code": (
                "inventory_output_frozen_downstream_rights_review_required"
                if index == 0
                else "prerequisite_not_satisfied"
            ),
            "prerequisite_codes": PHASE17_STEP_PREREQUISITES[index],
            "required_prior_evidence": PHASE17_STEP_REQUIRED_PRIOR_EVIDENCE[index],
            "required_outputs": PHASE17_STEP_REQUIRED_OUTPUTS[index],
            "produced_outputs": (inventory_output,) if index == 0 else (),
            "external_action_authorized": False,
        }
        steps.append(
            FamilyASourcePlanStepEvidence.model_validate(
                {
                    **payload,
                    "step_sha256": domain_sha256(PHASE17_STEP_HASH_DOMAIN, payload),
                }
            )
        )
    return tuple(steps)


def build_family_a_candidate_product_inventory() -> FamilyACandidateProductInventory:
    """Build the sole blocked metadata inventory without I/O or ambient state."""

    products = _products()
    candidate_groups = _candidate_groups()
    inventory_sha256 = products_manifest_sha256(products)
    source_plan_steps = _source_plan_steps(inventory_sha256)
    payload = {
        "schema_version": PHASE17_ARTIFACT_SCHEMA_VERSION,
        "artifact_id": identity(PHASE17_POLICY_SHA256),
        "policy_id": PHASE17_POLICY_ID,
        "policy_sha256": PHASE17_POLICY_SHA256,
        "accepted_phase16_commit_sha": PHASE17_ACCEPTED_PHASE16_COMMIT_SHA,
        "accepted_phase16_tree_sha": PHASE17_ACCEPTED_PHASE16_TREE_SHA,
        "phase16_artifact_id": PHASE17_PHASE16_ARTIFACT_ID,
        "phase16_artifact_sha256": PHASE17_PHASE16_ARTIFACT_SHA256,
        "phase16_policy_sha256": PHASE17_PHASE16_POLICY_SHA256,
        "phase16_requirements_manifest_sha256": PHASE17_PHASE16_REQUIREMENTS_MANIFEST_SHA256,
        "phase16_capabilities_manifest_sha256": PHASE17_PHASE16_CAPABILITIES_MANIFEST_SHA256,
        "phase16_candidates_manifest_sha256": PHASE17_PHASE16_CANDIDATES_MANIFEST_SHA256,
        "phase16_steps_manifest_sha256": PHASE17_PHASE16_STEPS_MANIFEST_SHA256,
        "phase16_step1_sha256": PHASE17_PHASE16_STEP1_SHA256,
        "phase16_gap_bindings_manifest_sha256": PHASE17_PHASE16_GAP_BINDINGS_MANIFEST_SHA256,
        "family": PHASE17_FAMILY,
        "frozen_at_utc": PHASE17_FROZEN_AT_UTC,
        "outcome": "BLOCKED",
        "block_reason": PHASE17_BLOCK_REASON,
        "candidate_product_inventory_sha256": inventory_sha256,
        "candidate_groups_manifest_sha256": candidate_groups_manifest_sha256(candidate_groups),
        "steps_manifest_sha256": steps_manifest_sha256(source_plan_steps),
        "products": products,
        "candidate_groups": candidate_groups,
        "source_plan_steps": source_plan_steps,
        **PHASE17_BOUNDARY_VALUES,
        "disclaimer": PHASE17_DISCLAIMER,
    }
    return FamilyACandidateProductInventory.model_validate(
        {
            **payload,
            "artifact_sha256": domain_sha256(PHASE17_ARTIFACT_HASH_DOMAIN, payload),
        }
    )


def canonical_candidate_product_inventory_bytes() -> bytes:
    return canonical_json_bytes(build_family_a_candidate_product_inventory()) + b"\n"


__all__ = [
    "build_family_a_candidate_product_inventory",
    "canonical_candidate_product_inventory_bytes",
]
