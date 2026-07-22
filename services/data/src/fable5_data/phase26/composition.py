"""Pure deterministic Phase 26 composition builder."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from fable5_data.phase26 import canonical as c
from fable5_data.phase26.contracts import (
    CapabilityAssignment,
    DecisionGate,
    Phase26Decision,
    PostSelectionDependency,
    SelectedProduct,
)


def _validated[ModelT: BaseModel](
    model: type[ModelT], payload: dict[str, Any], hash_field: str, domain: str
) -> ModelT:
    return model.model_validate({**payload, hash_field: c.domain_sha256(domain, payload)})


def _products() -> tuple[SelectedProduct, ...]:
    return tuple(
        _validated(
            SelectedProduct,
            {
                "schema_version": c.PRODUCT_SCHEMA,
                "ordinal": ordinal,
                "product_code": row[0],
                "provider": row[1],
                "source_ids": row[2],
                "delivery_ids": row[3],
                "assigned_capabilities": row[4],
                "accepted_candidate_product_sha256": row[5],
                "current_rights_state": row[6],
                "operationally_selected": True,
                "acquisition_authorized": False,
            },
            "product_sha256",
            c.PRODUCT_DOMAIN,
        )
        for ordinal, row in enumerate(c.PRODUCT_ROWS, 1)
    )


def _assignments() -> tuple[CapabilityAssignment, ...]:
    return tuple(
        _validated(
            CapabilityAssignment,
            {
                "schema_version": c.ASSIGNMENT_SCHEMA,
                "ordinal": ordinal,
                "capability_code": row[0],
                "assigned_product_code": row[1],
                "assignment_state": "ASSIGNED",
            },
            "assignment_sha256",
            c.ASSIGNMENT_DOMAIN,
        )
        for ordinal, row in enumerate(c.CAPABILITY_ROWS, 1)
    )


def _dependencies() -> tuple[PostSelectionDependency, ...]:
    return tuple(
        _validated(
            PostSelectionDependency,
            {
                "schema_version": c.DEPENDENCY_SCHEMA,
                "ordinal": ordinal,
                "code": row[0],
                "state": row[1],
                "definition": row[2],
                "satisfied": False,
            },
            "dependency_sha256",
            c.DEPENDENCY_DOMAIN,
        )
        for ordinal, row in enumerate(c.DEPENDENCY_ROWS, 1)
    )


def _gates() -> tuple[DecisionGate, ...]:
    return tuple(
        _validated(
            DecisionGate,
            {
                "schema_version": c.GATE_SCHEMA,
                "ordinal": ordinal,
                "code": row[0],
                "state": row[1],
                "passed": row[2],
            },
            "gate_sha256",
            c.GATE_DOMAIN,
        )
        for ordinal, row in enumerate(c.GATE_ROWS, 1)
    )


def build_phase26_decision() -> Phase26Decision:
    products = _products()
    assignments = _assignments()
    dependencies = _dependencies()
    gates = _gates()
    payload: dict[str, Any] = {
        "schema_version": c.ARTIFACT_SCHEMA,
        "policy_id": c.POLICY_ID,
        "policy_sha256": c.POLICY_SHA256,
        "source_snapshot_id": c.SOURCE_SNAPSHOT_ID,
        "source_snapshot_sha256": c.SOURCE_SNAPSHOT_SHA256,
        "generation_git_sha": c.GENERATION_GIT_SHA,
        "random_seed": c.RANDOM_SEED,
        "trial_count": c.TRIAL_COUNT,
        "generated_at_utc": c.SELECTED_AT_UTC,
        "accepted_phase25_commit_sha": c.BASELINE_COMMIT_SHA,
        "accepted_phase25_tree_sha": c.BASELINE_TREE_SHA,
        "phase25_artifact_id": c.PHASE25_ARTIFACT_ID,
        "phase25_artifact_sha256": c.PHASE25_ARTIFACT_SHA256,
        "phase25_artifact_file_sha256": c.PHASE25_ARTIFACT_FILE_SHA256,
        "phase21_artifact_sha256": c.PHASE21_ARTIFACT_SHA256,
        "phase22_product_sha256": c.PHASE22_PRODUCT_SHA256,
        "family": c.FAMILY,
        "outcome": "BLOCKED",
        "decision_state": "OPERATIONAL_COMPOSITION_SELECTED",
        "aggregate_conclusion": (
            "COMPOSITION_SELECTED_ACQUISITION_BLOCKED_PENDING_RIGHTS_AND_QUALIFICATION"
        ),
        "block_reason": (
            "The exact composition is selected, but CRSP entitlement, authenticated RTDSM "
            "exact-scope rights, SEC policy revalidation, exact schemas, and point-in-time "
            "qualification remain "
            "mandatory before any provider observation may be acquired."
        ),
        "capability_product_composition_id": c.COMPOSITION_ID,
        "source_ids": c.SOURCE_IDS,
        "product_ids": c.PRODUCT_IDS,
        "delivery_ids": c.DELIVERY_IDS,
        "selection_scope": c.SELECTION_SCOPE,
        "selected_at_utc": c.SELECTED_AT_UTC,
        "selected_by": c.SELECTED_BY,
        "selection_evidence_sha256": c.SELECTION_EVIDENCE_SHA256,
        "explicit_human_decision": True,
        "single_closed_composition": True,
        "operational_source_product_composition_selected": True,
        "selected_products": products,
        "selected_products_manifest_sha256": c.domain_sha256(c.PRODUCTS_MANIFEST_DOMAIN, products),
        "capability_assignments": assignments,
        "capability_assignments_manifest_sha256": c.domain_sha256(
            c.ASSIGNMENTS_MANIFEST_DOMAIN, assignments
        ),
        "post_selection_dependencies": dependencies,
        "post_selection_dependencies_manifest_sha256": c.domain_sha256(
            c.DEPENDENCIES_MANIFEST_DOMAIN, dependencies
        ),
        "decision_gates": gates,
        "decision_gates_manifest_sha256": c.domain_sha256(c.GATES_MANIFEST_DOMAIN, gates),
        **c.BOUNDARY_VALUES,
    }
    artifact_hash = c.domain_sha256(c.ARTIFACT_DOMAIN, payload)
    return Phase26Decision.model_validate(
        {
            **payload,
            "artifact_id": c.uuid_from_sha256(c.ARTIFACT_NAMESPACE, artifact_hash),
            "artifact_sha256": artifact_hash,
        }
    )


def canonical_phase26_decision_bytes() -> bytes:
    return c.canonical_json_bytes(build_phase26_decision()) + b"\n"
