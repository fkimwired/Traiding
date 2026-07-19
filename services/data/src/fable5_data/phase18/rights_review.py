"""Pure deterministic builder for the Phase 18 current-use rights review."""

from __future__ import annotations

from fable5_data.phase18.canonical import (
    PHASE18_ACCEPTED_PHASE17_COMMIT_SHA,
    PHASE18_ACCEPTED_PHASE17_TREE_SHA,
    PHASE18_AGGREGATE_CONCLUSION,
    PHASE18_ARTIFACT_HASH_DOMAIN,
    PHASE18_ARTIFACT_SCHEMA_VERSION,
    PHASE18_BLOCK_REASON,
    PHASE18_BOUNDARY_VALUES,
    PHASE18_DISCLAIMER,
    PHASE18_FAMILY,
    PHASE18_FINDING_HASH_DOMAIN,
    PHASE18_FINDING_SCHEMA_VERSION,
    PHASE18_FROZEN_AT_UTC,
    PHASE18_OUTPUT_HASH_DOMAIN,
    PHASE18_OUTPUT_SCHEMA_VERSION,
    PHASE18_PHASE16_STEP2_SHA256,
    PHASE18_PHASE17_ARTIFACT_ID,
    PHASE18_PHASE17_ARTIFACT_SHA256,
    PHASE18_PHASE17_CANDIDATE_GROUPS_MANIFEST_SHA256,
    PHASE18_PHASE17_INVENTORY_SHA256,
    PHASE18_PHASE17_POLICY_SHA256,
    PHASE18_PHASE17_STEPS_MANIFEST_SHA256,
    PHASE18_POLICY_ID,
    PHASE18_POLICY_SHA256,
    PHASE18_PRODUCT_ROWS,
    PHASE18_SOURCE_HASH_DOMAIN,
    PHASE18_SOURCE_ROWS,
    PHASE18_SOURCE_SCHEMA_VERSION,
    PHASE18_STEP_CODES,
    PHASE18_STEP_HASH_DOMAIN,
    PHASE18_STEP_PREREQUISITES,
    PHASE18_STEP_REASONS,
    PHASE18_STEP_REQUIRED_OUTPUTS,
    PHASE18_STEP_REQUIRED_PRIOR_EVIDENCE,
    PHASE18_STEP_SCHEMA_VERSION,
    PHASE18_STEP_STATES,
    canonical_json_bytes,
    domain_sha256,
    identity,
)
from fable5_data.phase18.contracts import (
    FamilyACurrentUseRightsReview,
    FamilyARightsReviewOutput,
    FamilyASourcePlanStepEvidence,
    ProductRightsFinding,
    PublicTermsSource,
    independent_rights_review_sha256,
    rights_currentness_sha256,
    steps_manifest_sha256,
    terms_sources_manifest_sha256,
)


def _terms_sources() -> tuple[PublicTermsSource, ...]:
    sources: list[PublicTermsSource] = []
    for ordinal, row in enumerate(PHASE18_SOURCE_ROWS, start=1):
        payload = {
            "schema_version": PHASE18_SOURCE_SCHEMA_VERSION,
            "ordinal": ordinal,
            "code": row[0],
            "official_title": row[1],
            "publisher": row[2],
            "official_url": row[3],
            "applies_to_product_codes": row[4],
            "publisher_last_updated": row[5],
            "locator": row[6],
            "conservative_fact": row[7],
            "reviewed_at_utc": row[8],
            "public_metadata_only": True,
            "official_https_citation": True,
            "terms_body_persisted": False,
            "remote_source_response_body_persisted": False,
            "source_content_bytes_captured": False,
            "content_byte_authenticity_proven": False,
            "account_specific": False,
            "revalidation_required": True,
        }
        sources.append(
            PublicTermsSource.model_validate(
                {
                    **payload,
                    "source_sha256": domain_sha256(PHASE18_SOURCE_HASH_DOMAIN, payload),
                }
            )
        )
    return tuple(sources)


def _product_findings() -> tuple[ProductRightsFinding, ...]:
    findings: list[ProductRightsFinding] = []
    for ordinal, row in enumerate(PHASE18_PRODUCT_ROWS, start=1):
        payload = {
            "schema_version": PHASE18_FINDING_SCHEMA_VERSION,
            "ordinal": ordinal,
            "product_code": row[0],
            "phase17_product_sha256": row[1],
            "source_codes": row[2],
            "storage": row[3],
            "non_display_internal_use": row[4],
            "derived_data": row[5],
            "retention": row[6],
            "redistribution": row[7],
            "revocation_currentness": row[8],
            "delivery": row[9],
            "entitlement": row[10],
            "conclusion": row[11],
            "conservative_finding": row[12],
            "public_metadata_review_only": True,
            "operational_use_cleared": False,
            "entitlement_verified": False,
            "executed_license_reviewed": False,
            "legal_opinion_obtained": False,
            "revalidation_required": True,
        }
        findings.append(
            ProductRightsFinding.model_validate(
                {
                    **payload,
                    "finding_sha256": domain_sha256(PHASE18_FINDING_HASH_DOMAIN, payload),
                }
            )
        )
    return tuple(findings)


def _output(name: str, sha256: str) -> FamilyARightsReviewOutput:
    payload = {
        "schema_version": PHASE18_OUTPUT_SCHEMA_VERSION,
        "name": name,
        "sha256": sha256,
    }
    return FamilyARightsReviewOutput.model_validate(
        {
            **payload,
            "output_sha256": domain_sha256(PHASE18_OUTPUT_HASH_DOMAIN, payload),
        }
    )


def _source_plan_steps(
    review_sha256: str,
    currentness_sha256: str,
) -> tuple[FamilyASourcePlanStepEvidence, ...]:
    output_sets: tuple[tuple[FamilyARightsReviewOutput, ...], ...] = (
        (_output("candidate_product_inventory_sha256", PHASE18_PHASE17_INVENTORY_SHA256),),
        (
            _output("independent_rights_review_sha256", review_sha256),
            _output("rights_currentness_sha256", currentness_sha256),
        ),
        (),
        (),
        (),
        (),
        (),
    )
    steps: list[FamilyASourcePlanStepEvidence] = []
    for ordinal, code in enumerate(PHASE18_STEP_CODES, start=1):
        index = ordinal - 1
        payload = {
            "schema_version": PHASE18_STEP_SCHEMA_VERSION,
            "ordinal": ordinal,
            "code": code,
            "state": PHASE18_STEP_STATES[index],
            "reason_code": PHASE18_STEP_REASONS[index],
            "prerequisite_codes": PHASE18_STEP_PREREQUISITES[index],
            "required_prior_evidence": PHASE18_STEP_REQUIRED_PRIOR_EVIDENCE[index],
            "required_outputs": PHASE18_STEP_REQUIRED_OUTPUTS[index],
            "produced_outputs": output_sets[index],
            "external_action_authorized": False,
        }
        steps.append(
            FamilyASourcePlanStepEvidence.model_validate(
                {
                    **payload,
                    "step_sha256": domain_sha256(PHASE18_STEP_HASH_DOMAIN, payload),
                }
            )
        )
    return tuple(steps)


def build_family_a_current_use_rights_review() -> FamilyACurrentUseRightsReview:
    """Build the sole blocking rights-review snapshot without runtime I/O."""

    sources = _terms_sources()
    findings = _product_findings()
    sources_manifest = terms_sources_manifest_sha256(sources)
    review_hash = independent_rights_review_sha256(sources_manifest, findings)
    currentness_hash = rights_currentness_sha256(sources_manifest)
    steps = _source_plan_steps(review_hash, currentness_hash)
    payload = {
        "schema_version": PHASE18_ARTIFACT_SCHEMA_VERSION,
        "artifact_id": identity(PHASE18_POLICY_SHA256),
        "policy_id": PHASE18_POLICY_ID,
        "policy_sha256": PHASE18_POLICY_SHA256,
        "accepted_phase17_commit_sha": PHASE18_ACCEPTED_PHASE17_COMMIT_SHA,
        "accepted_phase17_tree_sha": PHASE18_ACCEPTED_PHASE17_TREE_SHA,
        "phase17_artifact_id": PHASE18_PHASE17_ARTIFACT_ID,
        "phase17_artifact_sha256": PHASE18_PHASE17_ARTIFACT_SHA256,
        "phase17_policy_sha256": PHASE18_PHASE17_POLICY_SHA256,
        "phase17_candidate_product_inventory_sha256": PHASE18_PHASE17_INVENTORY_SHA256,
        "phase17_candidate_groups_manifest_sha256": (
            PHASE18_PHASE17_CANDIDATE_GROUPS_MANIFEST_SHA256
        ),
        "phase17_steps_manifest_sha256": PHASE18_PHASE17_STEPS_MANIFEST_SHA256,
        "phase16_step2_sha256": PHASE18_PHASE16_STEP2_SHA256,
        "family": PHASE18_FAMILY,
        "frozen_at_utc": PHASE18_FROZEN_AT_UTC,
        "outcome": "BLOCKED",
        "aggregate_conclusion": PHASE18_AGGREGATE_CONCLUSION,
        "block_reason": PHASE18_BLOCK_REASON,
        "terms_sources_manifest_sha256": sources_manifest,
        "independent_rights_review_sha256": review_hash,
        "rights_currentness_sha256": currentness_hash,
        "steps_manifest_sha256": steps_manifest_sha256(steps),
        "terms_sources": sources,
        "product_rights_findings": findings,
        "source_plan_steps": steps,
        **dict(PHASE18_BOUNDARY_VALUES),
        "disclaimer": PHASE18_DISCLAIMER,
    }
    return FamilyACurrentUseRightsReview.model_validate(
        {
            **payload,
            "artifact_sha256": domain_sha256(PHASE18_ARTIFACT_HASH_DOMAIN, payload),
        }
    )


def canonical_current_use_rights_review_bytes() -> bytes:
    return canonical_json_bytes(build_family_a_current_use_rights_review()) + b"\n"


__all__ = [
    "build_family_a_current_use_rights_review",
    "canonical_current_use_rights_review_bytes",
]
