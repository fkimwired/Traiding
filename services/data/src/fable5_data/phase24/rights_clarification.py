"""Pure deterministic builder for Phase 24 rights-clarification requirements."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from fable5_data.phase24 import canonical as c
from fable5_data.phase24.contracts import (
    FamilyARTDSMRightsClarificationRequirements,
    ProposedUseDisclosure,
    RightsAnswerTransitionRule,
    RightsClarificationQuestion,
    RightsEvidenceRequirement,
    disclosures_manifest_sha256,
    evidence_manifest_sha256,
    questions_manifest_sha256,
    rules_manifest_sha256,
)


def _validated[ModelT: BaseModel](
    model: type[ModelT], payload: dict[str, Any], hash_field: str, domain: str
) -> ModelT:
    return model.model_validate({**payload, hash_field: c.domain_sha256(domain, payload)})


def _disclosures() -> tuple[ProposedUseDisclosure, ...]:
    return tuple(
        _validated(
            ProposedUseDisclosure,
            {
                "schema_version": c.PHASE24_DISCLOSURE_SCHEMA_VERSION,
                "ordinal": ordinal,
                "code": row[0],
                "disclosure": row[1],
                "status": "PROPOSED_NOT_AUTHORIZED",
                **dict(c.PHASE24_ROW_INVARIANTS),
            },
            "disclosure_sha256",
            c.PHASE24_DISCLOSURE_HASH_DOMAIN,
        )
        for ordinal, row in enumerate(c.PHASE24_DISCLOSURE_ROWS, 1)
    )


def _questions() -> tuple[RightsClarificationQuestion, ...]:
    return tuple(
        _validated(
            RightsClarificationQuestion,
            {
                "schema_version": c.PHASE24_QUESTION_SCHEMA_VERSION,
                "ordinal": ordinal,
                "code": row[0],
                "phase23_rights_field": row[1],
                "question": row[2],
                "required_answer": "EXPLICIT_PRODUCT_SPECIFIC_YES_NO_OR_CONDITIONS",
                "state": "UNANSWERED",
                "answer_evidence_present": False,
                "independently_verified": False,
                **dict(c.PHASE24_ROW_INVARIANTS),
            },
            "question_sha256",
            c.PHASE24_QUESTION_HASH_DOMAIN,
        )
        for ordinal, row in enumerate(c.PHASE24_QUESTION_ROWS, 1)
    )


def _evidence() -> tuple[RightsEvidenceRequirement, ...]:
    return tuple(
        _validated(
            RightsEvidenceRequirement,
            {
                "schema_version": c.PHASE24_EVIDENCE_SCHEMA_VERSION,
                "ordinal": ordinal,
                "code": row[0],
                "requirement": row[1],
                "acceptable_evidence": row[2],
                "state": "MISSING",
                "evidence_present": False,
                "independently_verified": False,
                **dict(c.PHASE24_ROW_INVARIANTS),
            },
            "evidence_requirement_sha256",
            c.PHASE24_EVIDENCE_HASH_DOMAIN,
        )
        for ordinal, row in enumerate(c.PHASE24_EVIDENCE_ROWS, 1)
    )


def _rules() -> tuple[RightsAnswerTransitionRule, ...]:
    return tuple(
        _validated(
            RightsAnswerTransitionRule,
            {
                "schema_version": c.PHASE24_RULE_SCHEMA_VERSION,
                "ordinal": ordinal,
                "code": row[0],
                "rule": row[1],
                "applied": False,
                **dict(c.PHASE24_ROW_INVARIANTS),
            },
            "rule_sha256",
            c.PHASE24_RULE_HASH_DOMAIN,
        )
        for ordinal, row in enumerate(c.PHASE24_RULE_ROWS, 1)
    )


def build_family_a_rtdsm_rights_clarification_requirements() -> (
    FamilyARTDSMRightsClarificationRequirements
):
    """Build the sole blocked, requirements-only Phase 24 artifact without runtime I/O."""

    disclosures = _disclosures()
    questions = _questions()
    evidence = _evidence()
    rules = _rules()
    payload = {
        "schema_version": c.PHASE24_ARTIFACT_SCHEMA_VERSION,
        "artifact_id": c.identity(),
        "policy_id": c.PHASE24_POLICY_ID,
        "policy_sha256": c.PHASE24_POLICY_SHA256,
        "accepted_phase23_commit_sha": c.PHASE24_ACCEPTED_PHASE23_COMMIT_SHA,
        "accepted_phase23_tree_sha": c.PHASE24_ACCEPTED_PHASE23_TREE_SHA,
        "phase23_merge_commit_sha": c.PHASE24_PHASE23_MERGE_COMMIT_SHA,
        "phase23_artifact_id": c.PHASE24_PHASE23_ARTIFACT_ID,
        "phase23_artifact_sha256": c.PHASE24_PHASE23_ARTIFACT_SHA256,
        "phase23_policy_sha256": c.PHASE24_PHASE23_POLICY_SHA256,
        "phase23_findings_manifest_sha256": c.PHASE24_PHASE23_FINDINGS_MANIFEST_SHA256,
        "phase23_requirements_manifest_sha256": c.PHASE24_PHASE23_REQUIREMENTS_MANIFEST_SHA256,
        "product_code": c.PHASE24_PRODUCT_CODE,
        "phase22_product_sha256": c.PHASE24_PHASE22_PRODUCT_SHA256,
        "family": c.PHASE24_FAMILY,
        "frozen_at_utc": c.PHASE24_FROZEN_AT_UTC,
        "outcome": c.PHASE24_OUTCOME,
        "requirements_state": c.PHASE24_REQUIREMENTS_STATE,
        "aggregate_conclusion": c.PHASE24_AGGREGATE_CONCLUSION,
        "block_reason": c.PHASE24_BLOCK_REASON,
        "proposed_use_disclosures_manifest_sha256": disclosures_manifest_sha256(disclosures),
        "clarification_questions_manifest_sha256": questions_manifest_sha256(questions),
        "evidence_requirements_manifest_sha256": evidence_manifest_sha256(evidence),
        "transition_rules_manifest_sha256": rules_manifest_sha256(rules),
        "proposed_use_disclosures": disclosures,
        "clarification_questions": questions,
        "evidence_requirements": evidence,
        "transition_rules": rules,
        **dict(c.PHASE24_BOUNDARY_VALUES),
        "disclaimer": c.PHASE24_DISCLAIMER,
    }
    return FamilyARTDSMRightsClarificationRequirements.model_validate(
        {**payload, "artifact_sha256": c.domain_sha256(c.PHASE24_ARTIFACT_HASH_DOMAIN, payload)}
    )


def canonical_rtdsm_rights_clarification_requirements_bytes() -> bytes:
    return c.canonical_json_bytes(build_family_a_rtdsm_rights_clarification_requirements()) + b"\n"


__all__ = [
    "build_family_a_rtdsm_rights_clarification_requirements",
    "canonical_rtdsm_rights_clarification_requirements_bytes",
]
