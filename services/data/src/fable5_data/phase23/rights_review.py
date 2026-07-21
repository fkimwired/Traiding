"""Pure deterministic builder for the Phase 23 RTDSM rights review."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from fable5_data.phase23 import canonical as c
from fable5_data.phase23.contracts import (
    FamilyARTDSMCurrentUseRightsReview,
    FutureRequirementStatus,
    PublicTermsSource,
    RTDSMRightsFinding,
    findings_manifest_sha256,
    requirements_manifest_sha256,
    sources_manifest_sha256,
)


def _validated[ModelT: BaseModel](
    model: type[ModelT], payload: dict[str, Any], hash_field: str, domain: str
) -> ModelT:
    return model.model_validate({**payload, hash_field: c.domain_sha256(domain, payload)})


def _sources() -> tuple[PublicTermsSource, ...]:
    return tuple(
        _validated(
            PublicTermsSource,
            {
                "schema_version": c.PHASE23_SOURCE_SCHEMA_VERSION,
                "ordinal": ordinal,
                "code": row[0],
                "title": row[1],
                "publisher": row[2],
                "url": row[3],
                "publisher_last_updated": row[4],
                "locator": row[5],
                "conservative_fact": row[6],
                "reviewed_on": c.PHASE23_REVIEWED_ON,
                **dict(c.PHASE23_SOURCE_INVARIANTS),
            },
            "source_sha256",
            c.PHASE23_SOURCE_HASH_DOMAIN,
        )
        for ordinal, row in enumerate(c.PHASE23_SOURCE_ROWS, 1)
    )


def _findings() -> tuple[RTDSMRightsFinding, ...]:
    payload = {
        "schema_version": c.PHASE23_FINDING_SCHEMA_VERSION,
        "ordinal": 1,
        "product_code": c.PHASE23_PRODUCT_CODE,
        "phase22_product_sha256": c.PHASE23_PHASE22_PRODUCT_SHA256,
        "source_codes": tuple(row[0] for row in c.PHASE23_SOURCE_ROWS),
        **dict(c.PHASE23_FINDING_VALUES),
    }
    return (
        _validated(
            RTDSMRightsFinding,
            payload,
            "finding_sha256",
            c.PHASE23_FINDING_HASH_DOMAIN,
        ),
    )


def _requirements() -> tuple[FutureRequirementStatus, ...]:
    return tuple(
        _validated(
            FutureRequirementStatus,
            {
                "schema_version": c.PHASE23_REQUIREMENT_SCHEMA_VERSION,
                "ordinal": ordinal,
                "code": row[0],
                "phase22_requirement_sha256": row[1],
                "state": row[2],
                "definition": row[3],
                "review_output_produced": row[4],
                **dict(c.PHASE23_REQUIREMENT_INVARIANTS),
            },
            "requirement_sha256",
            c.PHASE23_REQUIREMENT_HASH_DOMAIN,
        )
        for ordinal, row in enumerate(c.PHASE23_REQUIREMENT_ROWS, 1)
    )


def build_family_a_rtdsm_current_use_rights_review() -> FamilyARTDSMCurrentUseRightsReview:
    """Build the sole blocked public-terms review without runtime I/O."""

    sources = _sources()
    findings = _findings()
    requirements = _requirements()
    payload = {
        "schema_version": c.PHASE23_ARTIFACT_SCHEMA_VERSION,
        "artifact_id": c.identity(),
        "policy_id": c.PHASE23_POLICY_ID,
        "policy_sha256": c.PHASE23_POLICY_SHA256,
        "accepted_phase22_commit_sha": c.PHASE23_ACCEPTED_PHASE22_COMMIT_SHA,
        "accepted_phase22_tree_sha": c.PHASE23_ACCEPTED_PHASE22_TREE_SHA,
        "phase22_merge_commit_sha": c.PHASE23_PHASE22_MERGE_COMMIT_SHA,
        "phase22_artifact_id": c.PHASE23_PHASE22_ARTIFACT_ID,
        "phase22_artifact_sha256": c.PHASE23_PHASE22_ARTIFACT_SHA256,
        "phase22_policy_sha256": c.PHASE23_PHASE22_POLICY_SHA256,
        "phase22_sources_manifest_sha256": c.PHASE23_PHASE22_SOURCES_MANIFEST_SHA256,
        "phase22_products_manifest_sha256": c.PHASE23_PHASE22_PRODUCTS_MANIFEST_SHA256,
        "phase22_requirements_manifest_sha256": c.PHASE23_PHASE22_REQUIREMENTS_MANIFEST_SHA256,
        "product_code": c.PHASE23_PRODUCT_CODE,
        "phase22_product_sha256": c.PHASE23_PHASE22_PRODUCT_SHA256,
        "family": c.PHASE23_FAMILY,
        "frozen_at_utc": c.PHASE23_FROZEN_AT_UTC,
        "reviewed_on": c.PHASE23_REVIEWED_ON,
        "outcome": c.PHASE23_OUTCOME,
        "review_state": c.PHASE23_REVIEW_STATE,
        "aggregate_conclusion": c.PHASE23_AGGREGATE_CONCLUSION,
        "block_reason": c.PHASE23_BLOCK_REASON,
        "public_terms_sources_manifest_sha256": sources_manifest_sha256(sources),
        "rights_findings_manifest_sha256": findings_manifest_sha256(findings),
        "future_requirements_manifest_sha256": requirements_manifest_sha256(requirements),
        "public_terms_sources": sources,
        "rights_findings": findings,
        "future_requirements": requirements,
        **dict(c.PHASE23_BOUNDARY_VALUES),
        "disclaimer": c.PHASE23_DISCLAIMER,
    }
    return FamilyARTDSMCurrentUseRightsReview.model_validate(
        {**payload, "artifact_sha256": c.domain_sha256(c.PHASE23_ARTIFACT_HASH_DOMAIN, payload)}
    )


def canonical_rtdsm_current_use_rights_review_bytes() -> bytes:
    return c.canonical_json_bytes(build_family_a_rtdsm_current_use_rights_review()) + b"\n"


__all__ = [
    "build_family_a_rtdsm_current_use_rights_review",
    "canonical_rtdsm_current_use_rights_review_bytes",
]
