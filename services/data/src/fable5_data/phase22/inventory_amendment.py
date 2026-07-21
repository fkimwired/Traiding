"""Pure deterministic builder for the Phase 22 candidate-inventory amendment."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from fable5_data.phase22 import canonical as c
from fable5_data.phase22.contracts import (
    CandidateGroupAmendment,
    FamilyAMacroVintageCandidateInventoryAmendment,
    FutureReviewRequirement,
    MacroVintageCandidateProduct,
    OfficialSourceCitation,
    groups_manifest_sha256,
    products_manifest_sha256,
    requirements_manifest_sha256,
    sources_manifest_sha256,
)


def _validated[ModelT: BaseModel](
    model: type[ModelT], payload: dict[str, Any], hash_field: str, domain: str
) -> ModelT:
    return model.model_validate({**payload, hash_field: c.domain_sha256(domain, payload)})


def _official_sources() -> tuple[OfficialSourceCitation, ...]:
    return tuple(
        _validated(
            OfficialSourceCitation,
            {
                "schema_version": c.PHASE22_SOURCE_SCHEMA_VERSION,
                "ordinal": ordinal,
                "source_code": row[0],
                "title": row[1],
                "publisher": row[2],
                "url": row[3],
                "fact_scope": row[4],
                "reviewed_on": c.PHASE22_REVIEWED_ON,
                **dict(c.PHASE22_SOURCE_INVARIANTS),
            },
            "source_sha256",
            c.PHASE22_SOURCE_HASH_DOMAIN,
        )
        for ordinal, row in enumerate(c.PHASE22_SOURCE_ROWS, 1)
    )


def _candidate_group_amendments() -> tuple[CandidateGroupAmendment, ...]:
    return tuple(
        _validated(
            CandidateGroupAmendment,
            {
                "schema_version": c.PHASE22_GROUP_SCHEMA_VERSION,
                "ordinal": ordinal,
                "candidate_group_code": row[0],
                "product_codes": row[1],
                **dict(c.PHASE22_GROUP_INVARIANTS),
            },
            "group_sha256",
            c.PHASE22_GROUP_HASH_DOMAIN,
        )
        for ordinal, row in enumerate(c.PHASE22_CANDIDATE_GROUP_ROWS, 1)
    )


def _candidate_products() -> tuple[MacroVintageCandidateProduct, ...]:
    return tuple(
        _validated(
            MacroVintageCandidateProduct,
            {
                "schema_version": c.PHASE22_PRODUCT_SCHEMA_VERSION,
                "ordinal": ordinal,
                "product_code": row[0],
                "candidate_group_code": row[1],
                "official_name": row[2],
                "official_documentation_url": row[3],
                "official_fact": row[4],
                "capability_codes": row[5],
                "delivery_surface_state": row[6],
                "source_codes": row[7],
                **dict(c.PHASE22_PRODUCT_INVARIANTS),
            },
            "product_sha256",
            c.PHASE22_PRODUCT_HASH_DOMAIN,
        )
        for ordinal, row in enumerate(c.PHASE22_PRODUCT_ROWS, 1)
    )


def _future_review_requirements() -> tuple[FutureReviewRequirement, ...]:
    return tuple(
        _validated(
            FutureReviewRequirement,
            {
                "schema_version": c.PHASE22_REQUIREMENT_SCHEMA_VERSION,
                "ordinal": ordinal,
                "code": row[0],
                "state": row[1],
                "definition": row[2],
                **dict(c.PHASE22_REQUIREMENT_INVARIANTS),
            },
            "requirement_sha256",
            c.PHASE22_REQUIREMENT_HASH_DOMAIN,
        )
        for ordinal, row in enumerate(c.PHASE22_REQUIREMENT_ROWS, 1)
    )


def build_family_a_macro_vintage_candidate_inventory_amendment() -> (
    FamilyAMacroVintageCandidateInventoryAmendment
):
    """Build the sole metadata-only, blocked Phase 22 amendment artifact."""

    sources = _official_sources()
    groups = _candidate_group_amendments()
    products = _candidate_products()
    requirements = _future_review_requirements()
    payload = {
        "schema_version": c.PHASE22_ARTIFACT_SCHEMA_VERSION,
        "artifact_id": c.identity(),
        "amendment_policy_id": c.PHASE22_POLICY_ID,
        "amendment_policy_sha256": c.PHASE22_POLICY_SHA256,
        "accepted_phase21_commit_sha": c.PHASE22_ACCEPTED_PHASE21_COMMIT_SHA,
        "accepted_phase21_tree_sha": c.PHASE22_ACCEPTED_PHASE21_TREE_SHA,
        "phase21_artifact_id": c.PHASE22_PHASE21_ARTIFACT_ID,
        "phase21_artifact_sha256": c.PHASE22_PHASE21_ARTIFACT_SHA256,
        "phase21_policy_sha256": c.PHASE22_PHASE21_POLICY_SHA256,
        "phase21_candidate_groups_manifest_sha256": (
            c.PHASE22_PHASE21_CANDIDATE_GROUPS_MANIFEST_SHA256
        ),
        "phase21_product_rights_manifest_sha256": (
            c.PHASE22_PHASE21_PRODUCT_RIGHTS_MANIFEST_SHA256
        ),
        "phase21_capabilities_manifest_sha256": (c.PHASE22_PHASE21_CAPABILITIES_MANIFEST_SHA256),
        "phase21_decision_fields_manifest_sha256": (
            c.PHASE22_PHASE21_DECISION_FIELDS_MANIFEST_SHA256
        ),
        "phase21_gates_manifest_sha256": c.PHASE22_PHASE21_GATES_MANIFEST_SHA256,
        "phase21_rules_manifest_sha256": c.PHASE22_PHASE21_RULES_MANIFEST_SHA256,
        "phase21_aggregate_conclusion": c.PHASE22_PHASE21_AGGREGATE_CONCLUSION,
        "phase21_base_candidate_group_count": c.PHASE22_PHASE21_BASE_CANDIDATE_GROUP_COUNT,
        "phase21_base_product_count": c.PHASE22_PHASE21_BASE_PRODUCT_COUNT,
        "inherited_fred_product_code": c.PHASE22_INHERITED_FRED_PRODUCT_CODE,
        "inherited_fred_product_sha256": c.PHASE22_INHERITED_FRED_PRODUCT_SHA256,
        "inherited_fred_rights_finding_sha256": (c.PHASE22_INHERITED_FRED_RIGHTS_FINDING_SHA256),
        "inherited_fred_rights_conclusion": c.PHASE22_INHERITED_FRED_RIGHTS_CONCLUSION,
        "family": c.PHASE22_FAMILY,
        "frozen_at_utc": c.PHASE22_FROZEN_AT_UTC,
        "reviewed_on": c.PHASE22_REVIEWED_ON,
        "outcome": c.PHASE22_OUTCOME,
        "amendment_state": c.PHASE22_AMENDMENT_STATE,
        "aggregate_conclusion": c.PHASE22_AGGREGATE_CONCLUSION,
        "block_reason": c.PHASE22_BLOCK_REASON,
        "official_sources_manifest_sha256": sources_manifest_sha256(sources),
        "candidate_groups_amendment_manifest_sha256": groups_manifest_sha256(groups),
        "candidate_products_amendment_manifest_sha256": products_manifest_sha256(products),
        "future_review_requirements_manifest_sha256": requirements_manifest_sha256(requirements),
        "official_sources": sources,
        "candidate_group_amendments": groups,
        "candidate_products": products,
        "future_review_requirements": requirements,
        **dict(c.PHASE22_BOUNDARY_VALUES),
        "disclaimer": c.PHASE22_DISCLAIMER,
    }
    return FamilyAMacroVintageCandidateInventoryAmendment.model_validate(
        {
            **payload,
            "artifact_sha256": c.domain_sha256(c.PHASE22_ARTIFACT_HASH_DOMAIN, payload),
        }
    )


def canonical_macro_vintage_candidate_inventory_amendment_bytes() -> bytes:
    return (
        c.canonical_json_bytes(build_family_a_macro_vintage_candidate_inventory_amendment()) + b"\n"
    )


__all__ = [
    "build_family_a_macro_vintage_candidate_inventory_amendment",
    "canonical_macro_vintage_candidate_inventory_amendment_bytes",
]
