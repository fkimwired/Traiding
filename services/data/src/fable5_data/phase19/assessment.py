"""Pure deterministic builder for the Phase 19 Step-3 prerequisite assessment."""

from __future__ import annotations

from fable5_data.phase19.canonical import (
    PHASE19_ACCEPTED_PHASE18_COMMIT_SHA,
    PHASE19_ACCEPTED_PHASE18_TREE_SHA,
    PHASE19_AGGREGATE_CONCLUSION,
    PHASE19_ARTIFACT_HASH_DOMAIN,
    PHASE19_ARTIFACT_SCHEMA_VERSION,
    PHASE19_ASSESSMENT_POLICY_ID,
    PHASE19_ASSESSMENT_POLICY_SHA256,
    PHASE19_ASSESSMENT_STATE,
    PHASE19_BLOCK_REASON,
    PHASE19_BOUNDARY_VALUES,
    PHASE19_DISCLAIMER,
    PHASE19_FAMILY,
    PHASE19_FROZEN_AT_UTC,
    PHASE19_GAP_BINDING_HASH_DOMAIN,
    PHASE19_GAP_BINDING_SCHEMA_VERSION,
    PHASE19_GAP_CODES,
    PHASE19_GAP_STATES,
    PHASE19_OUTCOME,
    PHASE19_OUTPUT_HASH_DOMAIN,
    PHASE19_OUTPUT_SCHEMA_VERSION,
    PHASE19_PHASE6_SPECIFICATION_ID,
    PHASE19_PHASE6_SPECIFICATION_SHA256,
    PHASE19_PHASE6_SPECIFICATION_VERSION,
    PHASE19_PHASE15_GAPS_MANIFEST_SHA256,
    PHASE19_PHASE16_ORIGINAL_STEP3_SHA256,
    PHASE19_PHASE18_ARTIFACT_ID,
    PHASE19_PHASE18_ARTIFACT_SHA256,
    PHASE19_PHASE18_INDEPENDENT_RIGHTS_REVIEW_SHA256,
    PHASE19_PHASE18_INHERITED_STEP3_EVIDENCE_SHA256,
    PHASE19_PHASE18_INVENTORY_SHA256,
    PHASE19_PHASE18_POLICY_SHA256,
    PHASE19_PHASE18_RIGHTS_CURRENTNESS_SHA256,
    PHASE19_PHASE18_STEPS_MANIFEST_SHA256,
    PHASE19_PREREQUISITE_HASH_DOMAIN,
    PHASE19_PREREQUISITE_ROWS,
    PHASE19_PREREQUISITE_SCHEMA_VERSION,
    PHASE19_REQUIRED_EVIDENCE_HASH_DOMAIN,
    PHASE19_REQUIRED_EVIDENCE_ROWS,
    PHASE19_REQUIRED_EVIDENCE_SCHEMA_VERSION,
    PHASE19_SOURCE_GAP_SHA256S,
    PHASE19_STEP_CODES,
    PHASE19_STEP_HASH_DOMAIN,
    PHASE19_STEP_PREREQUISITES,
    PHASE19_STEP_REASONS,
    PHASE19_STEP_REQUIRED_OUTPUTS,
    PHASE19_STEP_REQUIRED_PRIOR_EVIDENCE,
    PHASE19_STEP_SCHEMA_VERSION,
    PHASE19_STEP_STATES,
    canonical_json_bytes,
    domain_sha256,
    identity,
)
from fable5_data.phase19.contracts import (
    FamilyAPhase15GapBinding,
    FamilyARequiredPriorEvidence,
    FamilyASourcePlanOutput,
    FamilyASourcePlanStepEvidence,
    FamilyAStep3Prerequisite,
    FamilyAStep3PrerequisiteAssessment,
    gap_bindings_manifest_sha256,
    prerequisites_manifest_sha256,
    required_evidence_manifest_sha256,
    steps_manifest_sha256,
)


def _prerequisites() -> tuple[FamilyAStep3Prerequisite, ...]:
    prerequisites: list[FamilyAStep3Prerequisite] = []
    for ordinal, row in enumerate(PHASE19_PREREQUISITE_ROWS, start=1):
        payload = {
            "schema_version": PHASE19_PREREQUISITE_SCHEMA_VERSION,
            "ordinal": ordinal,
            "category": row[0],
            "code": row[1],
            "definition": row[2],
            "evidence_state": row[3],
            "requirement_satisfied": row[4],
            "reason_code": row[5],
            "related_phase15_gap_codes": row[6],
        }
        prerequisites.append(
            FamilyAStep3Prerequisite.model_validate(
                {
                    **payload,
                    "prerequisite_sha256": domain_sha256(
                        PHASE19_PREREQUISITE_HASH_DOMAIN,
                        payload,
                    ),
                }
            )
        )
    return tuple(prerequisites)


def _required_prior_evidence() -> tuple[FamilyARequiredPriorEvidence, ...]:
    records: list[FamilyARequiredPriorEvidence] = []
    for ordinal, row in enumerate(PHASE19_REQUIRED_EVIDENCE_ROWS, start=1):
        payload = {
            "schema_version": PHASE19_REQUIRED_EVIDENCE_SCHEMA_VERSION,
            "ordinal": ordinal,
            "name": row[0],
            "state": row[1],
            "produced": row[2],
            "reason_code": row[3],
        }
        records.append(
            FamilyARequiredPriorEvidence.model_validate(
                {
                    **payload,
                    "record_sha256": domain_sha256(
                        PHASE19_REQUIRED_EVIDENCE_HASH_DOMAIN,
                        payload,
                    ),
                }
            )
        )
    return tuple(records)


def _phase15_gap_bindings() -> tuple[FamilyAPhase15GapBinding, ...]:
    gaps: list[FamilyAPhase15GapBinding] = []
    for ordinal, (code, state, source_sha256) in enumerate(
        zip(
            PHASE19_GAP_CODES,
            PHASE19_GAP_STATES,
            PHASE19_SOURCE_GAP_SHA256S,
            strict=True,
        ),
        start=1,
    ):
        payload = {
            "schema_version": PHASE19_GAP_BINDING_SCHEMA_VERSION,
            "ordinal": ordinal,
            "code": code,
            "state": state,
            "source_gap_sha256": source_sha256,
        }
        gaps.append(
            FamilyAPhase15GapBinding.model_validate(
                {
                    **payload,
                    "binding_sha256": domain_sha256(PHASE19_GAP_BINDING_HASH_DOMAIN, payload),
                }
            )
        )
    return tuple(gaps)


def _output(name: str, sha256: str) -> FamilyASourcePlanOutput:
    payload = {
        "schema_version": PHASE19_OUTPUT_SCHEMA_VERSION,
        "name": name,
        "sha256": sha256,
    }
    return FamilyASourcePlanOutput.model_validate(
        {
            **payload,
            "output_sha256": domain_sha256(PHASE19_OUTPUT_HASH_DOMAIN, payload),
        }
    )


def _source_plan_steps() -> tuple[FamilyASourcePlanStepEvidence, ...]:
    output_sets: tuple[tuple[FamilyASourcePlanOutput, ...], ...] = (
        (_output("candidate_product_inventory_sha256", PHASE19_PHASE18_INVENTORY_SHA256),),
        (
            _output(
                "independent_rights_review_sha256",
                PHASE19_PHASE18_INDEPENDENT_RIGHTS_REVIEW_SHA256,
            ),
            _output(
                "rights_currentness_sha256",
                PHASE19_PHASE18_RIGHTS_CURRENTNESS_SHA256,
            ),
        ),
        (),
        (),
        (),
        (),
        (),
    )
    steps: list[FamilyASourcePlanStepEvidence] = []
    for ordinal, code in enumerate(PHASE19_STEP_CODES, start=1):
        index = ordinal - 1
        payload = {
            "schema_version": PHASE19_STEP_SCHEMA_VERSION,
            "ordinal": ordinal,
            "code": code,
            "state": PHASE19_STEP_STATES[index],
            "reason_code": PHASE19_STEP_REASONS[index],
            "prerequisite_codes": PHASE19_STEP_PREREQUISITES[index],
            "required_prior_evidence": PHASE19_STEP_REQUIRED_PRIOR_EVIDENCE[index],
            "required_outputs": PHASE19_STEP_REQUIRED_OUTPUTS[index],
            "produced_outputs": output_sets[index],
            "external_action_authorized": False,
        }
        steps.append(
            FamilyASourcePlanStepEvidence.model_validate(
                {
                    **payload,
                    "step_sha256": domain_sha256(PHASE19_STEP_HASH_DOMAIN, payload),
                }
            )
        )
    return tuple(steps)


def build_family_a_step3_prerequisite_assessment() -> FamilyAStep3PrerequisiteAssessment:
    """Build the sole blocked Step-3 prerequisite assessment without runtime I/O."""

    prerequisites = _prerequisites()
    required_evidence = _required_prior_evidence()
    gap_bindings = _phase15_gap_bindings()
    steps = _source_plan_steps()
    payload = {
        "schema_version": PHASE19_ARTIFACT_SCHEMA_VERSION,
        "artifact_id": identity(PHASE19_ASSESSMENT_POLICY_SHA256),
        "assessment_policy_id": PHASE19_ASSESSMENT_POLICY_ID,
        "assessment_policy_sha256": PHASE19_ASSESSMENT_POLICY_SHA256,
        "accepted_phase18_commit_sha": PHASE19_ACCEPTED_PHASE18_COMMIT_SHA,
        "accepted_phase18_tree_sha": PHASE19_ACCEPTED_PHASE18_TREE_SHA,
        "phase18_artifact_id": PHASE19_PHASE18_ARTIFACT_ID,
        "phase18_artifact_sha256": PHASE19_PHASE18_ARTIFACT_SHA256,
        "phase18_policy_sha256": PHASE19_PHASE18_POLICY_SHA256,
        "phase18_independent_rights_review_sha256": (
            PHASE19_PHASE18_INDEPENDENT_RIGHTS_REVIEW_SHA256
        ),
        "phase18_rights_currentness_sha256": PHASE19_PHASE18_RIGHTS_CURRENTNESS_SHA256,
        "phase18_steps_manifest_sha256": PHASE19_PHASE18_STEPS_MANIFEST_SHA256,
        "phase18_aggregate_conclusion": "BLOCKED_NO_OPERATIONAL_SELECTION",
        "phase16_original_step3_sha256": PHASE19_PHASE16_ORIGINAL_STEP3_SHA256,
        "phase18_inherited_step3_evidence_sha256": (
            PHASE19_PHASE18_INHERITED_STEP3_EVIDENCE_SHA256
        ),
        "phase15_gaps_manifest_sha256": PHASE19_PHASE15_GAPS_MANIFEST_SHA256,
        "phase6_specification_id": PHASE19_PHASE6_SPECIFICATION_ID,
        "phase6_specification_version": PHASE19_PHASE6_SPECIFICATION_VERSION,
        "phase6_specification_sha256": PHASE19_PHASE6_SPECIFICATION_SHA256,
        "family": PHASE19_FAMILY,
        "frozen_at_utc": PHASE19_FROZEN_AT_UTC,
        "outcome": PHASE19_OUTCOME,
        "assessment_state": PHASE19_ASSESSMENT_STATE,
        "aggregate_conclusion": PHASE19_AGGREGATE_CONCLUSION,
        "block_reason": PHASE19_BLOCK_REASON,
        "prerequisites_manifest_sha256": prerequisites_manifest_sha256(prerequisites),
        "required_prior_evidence_manifest_sha256": required_evidence_manifest_sha256(
            required_evidence
        ),
        "phase15_gap_bindings_manifest_sha256": gap_bindings_manifest_sha256(gap_bindings),
        "steps_manifest_sha256": steps_manifest_sha256(steps),
        "prerequisites": prerequisites,
        "required_prior_evidence": required_evidence,
        "phase15_gap_bindings": gap_bindings,
        "source_plan_steps": steps,
        **dict(PHASE19_BOUNDARY_VALUES),
        "disclaimer": PHASE19_DISCLAIMER,
    }
    return FamilyAStep3PrerequisiteAssessment.model_validate(
        {
            **payload,
            "artifact_sha256": domain_sha256(PHASE19_ARTIFACT_HASH_DOMAIN, payload),
        }
    )


def canonical_step3_prerequisite_assessment_bytes() -> bytes:
    return canonical_json_bytes(build_family_a_step3_prerequisite_assessment()) + b"\n"


__all__ = [
    "build_family_a_step3_prerequisite_assessment",
    "canonical_step3_prerequisite_assessment_bytes",
]
