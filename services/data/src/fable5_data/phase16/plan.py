"""Pure deterministic builder for the Phase 16 Family A source plan."""

from __future__ import annotations

from fable5_data.phase16.canonical import (
    PHASE16_ACCEPTED_PHASE15_COMMIT_SHA,
    PHASE16_ACCEPTED_PHASE15_TREE_SHA,
    PHASE16_ARTIFACT_HASH_DOMAIN,
    PHASE16_ARTIFACT_SCHEMA_VERSION,
    PHASE16_BOUNDARY_VALUES,
    PHASE16_CANDIDATE_HASH_DOMAIN,
    PHASE16_CANDIDATE_SCHEMA_VERSION,
    PHASE16_CAPABILITY_HASH_DOMAIN,
    PHASE16_CAPABILITY_SCHEMA_VERSION,
    PHASE16_DISCLAIMER,
    PHASE16_EVIDENCE_HASH_DOMAIN,
    PHASE16_FAMILY,
    PHASE16_FROZEN_AT_UTC,
    PHASE16_GAP_BINDING_HASH_DOMAIN,
    PHASE16_GAP_BINDING_SCHEMA_VERSION,
    PHASE16_PHASE6_SPECIFICATION_ID,
    PHASE16_PHASE6_SPECIFICATION_SHA256,
    PHASE16_PHASE6_SPECIFICATION_VERSION,
    PHASE16_PHASE15_ARTIFACT_ID,
    PHASE16_PHASE15_ARTIFACT_SHA256,
    PHASE16_PHASE15_GAP_SHA256S,
    PHASE16_PHASE15_GAPS_MANIFEST_SHA256,
    PHASE16_PHASE15_POLICY_SHA256,
    PHASE16_PHASE15_REQUIREMENTS_MANIFEST_SHA256,
    PHASE16_POLICY_ID,
    PHASE16_POLICY_SHA256,
    PHASE16_REQUIREMENT_DEFINITIONS,
    PHASE16_REQUIREMENT_HASH_DOMAIN,
    PHASE16_REQUIREMENT_SCHEMA_VERSION,
    PHASE16_STEP_DEFINITIONS,
    PHASE16_STEP_HASH_DOMAIN,
    PHASE16_STEP_PREREQUISITES,
    PHASE16_STEP_REQUIRED_OUTPUTS,
    PHASE16_STEP_REQUIRED_PRIOR_EVIDENCE,
    PHASE16_STEP_SCHEMA_VERSION,
    canonical_json_bytes,
    domain_sha256,
    identity,
)
from fable5_data.phase16.contracts import (
    PHASE16_CANDIDATE_ORDER,
    PHASE16_CAPABILITY_ORDER,
    PHASE16_EXPECTED_CANDIDATE_STATES,
    PHASE16_EXPECTED_GAP_STATES,
    PHASE16_GAP_ORDER,
    PHASE16_REQUIREMENT_ORDER,
    PHASE16_STEP_ORDER,
    FamilyAPointInTimeSourcePlan,
    FamilyASourceCandidate,
    FamilyASourceCapability,
    FamilyASourcePlanOutcome,
    FamilyASourcePlanRequirement,
    FamilyASourcePlanRequirementReason,
    FamilyASourcePlanRequirementStatus,
    FamilyASourcePlanStep,
    Phase15GapBinding,
    candidates_manifest_sha256,
    capabilities_manifest_sha256,
    gap_bindings_manifest_sha256,
    requirements_manifest_sha256,
    steps_manifest_sha256,
)


def _evidence_sha256(*, kind: str, code: str) -> str:
    return domain_sha256(
        PHASE16_EVIDENCE_HASH_DOMAIN,
        {
            "kind": kind,
            "code": code,
            "accepted_phase15_commit_sha": PHASE16_ACCEPTED_PHASE15_COMMIT_SHA,
            "accepted_phase15_tree_sha": PHASE16_ACCEPTED_PHASE15_TREE_SHA,
            "phase15_artifact_sha256": PHASE16_PHASE15_ARTIFACT_SHA256,
            "phase15_gaps_manifest_sha256": PHASE16_PHASE15_GAPS_MANIFEST_SHA256,
        },
    )


def _requirements() -> tuple[FamilyASourcePlanRequirement, ...]:
    result: list[FamilyASourcePlanRequirement] = []
    for ordinal, code in enumerate(PHASE16_REQUIREMENT_ORDER, start=1):
        payload = {
            "schema_version": PHASE16_REQUIREMENT_SCHEMA_VERSION,
            "ordinal": ordinal,
            "code": code,
            "definition": PHASE16_REQUIREMENT_DEFINITIONS[ordinal - 1],
            "status": FamilyASourcePlanRequirementStatus.PASS,
            "reason_code": FamilyASourcePlanRequirementReason.FROZEN_SOURCE_PLAN_REQUIREMENT,
            "evidence_sha256s": (_evidence_sha256(kind="requirement", code=code.value),),
        }
        result.append(
            FamilyASourcePlanRequirement.model_validate(
                {
                    **payload,
                    "requirement_sha256": domain_sha256(
                        PHASE16_REQUIREMENT_HASH_DOMAIN,
                        payload,
                    ),
                }
            )
        )
    return tuple(result)


def _capabilities() -> tuple[FamilyASourceCapability, ...]:
    result: list[FamilyASourceCapability] = []
    for ordinal, code in enumerate(PHASE16_CAPABILITY_ORDER, start=1):
        payload = {
            "schema_version": PHASE16_CAPABILITY_SCHEMA_VERSION,
            "ordinal": ordinal,
            "code": code,
            "required": True,
            "source_selected": False,
        }
        result.append(
            FamilyASourceCapability.model_validate(
                {
                    **payload,
                    "capability_sha256": domain_sha256(
                        PHASE16_CAPABILITY_HASH_DOMAIN,
                        payload,
                    ),
                }
            )
        )
    return tuple(result)


def _candidates() -> tuple[FamilyASourceCandidate, ...]:
    result: list[FamilyASourceCandidate] = []
    for ordinal, (code, state) in enumerate(
        zip(PHASE16_CANDIDATE_ORDER, PHASE16_EXPECTED_CANDIDATE_STATES, strict=True),
        start=1,
    ):
        payload = {
            "schema_version": PHASE16_CANDIDATE_SCHEMA_VERSION,
            "ordinal": ordinal,
            "code": code,
            "state": state,
            "candidate_only": True,
            "selected": False,
            "rights_verified": False,
            "external_verification_performed": False,
        }
        result.append(
            FamilyASourceCandidate.model_validate(
                {
                    **payload,
                    "candidate_sha256": domain_sha256(
                        PHASE16_CANDIDATE_HASH_DOMAIN,
                        payload,
                    ),
                }
            )
        )
    return tuple(result)


def _future_steps() -> tuple[FamilyASourcePlanStep, ...]:
    result: list[FamilyASourcePlanStep] = []
    for ordinal, code in enumerate(PHASE16_STEP_ORDER, start=1):
        payload = {
            "schema_version": PHASE16_STEP_SCHEMA_VERSION,
            "ordinal": ordinal,
            "code": code,
            "definition": PHASE16_STEP_DEFINITIONS[ordinal - 1],
            "state": "NOT_STARTED",
            "prerequisite_codes": PHASE16_STEP_PREREQUISITES[ordinal - 1],
            "required_prior_evidence": PHASE16_STEP_REQUIRED_PRIOR_EVIDENCE[ordinal - 1],
            "required_outputs": PHASE16_STEP_REQUIRED_OUTPUTS[ordinal - 1],
            "external_action_authorized": False,
        }
        result.append(
            FamilyASourcePlanStep.model_validate(
                {
                    **payload,
                    "step_sha256": domain_sha256(PHASE16_STEP_HASH_DOMAIN, payload),
                }
            )
        )
    return tuple(result)


def _gap_bindings() -> tuple[Phase15GapBinding, ...]:
    result: list[Phase15GapBinding] = []
    for ordinal, (code, state, source_sha256) in enumerate(
        zip(
            PHASE16_GAP_ORDER,
            PHASE16_EXPECTED_GAP_STATES,
            PHASE16_PHASE15_GAP_SHA256S,
            strict=True,
        ),
        start=1,
    ):
        payload = {
            "schema_version": PHASE16_GAP_BINDING_SCHEMA_VERSION,
            "ordinal": ordinal,
            "code": code,
            "state": state,
            "source_gap_sha256": source_sha256,
        }
        result.append(
            Phase15GapBinding.model_validate(
                {
                    **payload,
                    "binding_sha256": domain_sha256(
                        PHASE16_GAP_BINDING_HASH_DOMAIN,
                        payload,
                    ),
                }
            )
        )
    return tuple(result)


def build_family_a_point_in_time_source_plan() -> FamilyAPointInTimeSourcePlan:
    """Build the sole source-plan artifact without I/O or ambient state."""

    requirements = _requirements()
    capabilities = _capabilities()
    candidates = _candidates()
    future_steps = _future_steps()
    gap_bindings = _gap_bindings()
    payload = {
        "schema_version": PHASE16_ARTIFACT_SCHEMA_VERSION,
        "artifact_id": identity(PHASE16_POLICY_SHA256),
        "policy_id": PHASE16_POLICY_ID,
        "policy_sha256": PHASE16_POLICY_SHA256,
        "accepted_phase15_commit_sha": PHASE16_ACCEPTED_PHASE15_COMMIT_SHA,
        "accepted_phase15_tree_sha": PHASE16_ACCEPTED_PHASE15_TREE_SHA,
        "phase15_artifact_id": PHASE16_PHASE15_ARTIFACT_ID,
        "phase15_artifact_sha256": PHASE16_PHASE15_ARTIFACT_SHA256,
        "phase15_policy_sha256": PHASE16_PHASE15_POLICY_SHA256,
        "phase15_requirements_manifest_sha256": PHASE16_PHASE15_REQUIREMENTS_MANIFEST_SHA256,
        "phase15_gaps_manifest_sha256": PHASE16_PHASE15_GAPS_MANIFEST_SHA256,
        "family": PHASE16_FAMILY,
        "phase6_specification_id": PHASE16_PHASE6_SPECIFICATION_ID,
        "phase6_specification_version": PHASE16_PHASE6_SPECIFICATION_VERSION,
        "phase6_specification_sha256": PHASE16_PHASE6_SPECIFICATION_SHA256,
        "frozen_at_utc": PHASE16_FROZEN_AT_UTC,
        "outcome": FamilyASourcePlanOutcome.PLAN_FROZEN,
        "requirements_manifest_sha256": requirements_manifest_sha256(requirements),
        "capabilities_manifest_sha256": capabilities_manifest_sha256(capabilities),
        "candidates_manifest_sha256": candidates_manifest_sha256(candidates),
        "steps_manifest_sha256": steps_manifest_sha256(future_steps),
        "gap_bindings_manifest_sha256": gap_bindings_manifest_sha256(gap_bindings),
        "requirements": requirements,
        "capabilities": capabilities,
        "candidates": candidates,
        "future_steps": future_steps,
        "phase15_gap_bindings": gap_bindings,
        **PHASE16_BOUNDARY_VALUES,
        "disclaimer": PHASE16_DISCLAIMER,
    }
    return FamilyAPointInTimeSourcePlan.model_validate(
        {
            **payload,
            "artifact_sha256": domain_sha256(PHASE16_ARTIFACT_HASH_DOMAIN, payload),
        }
    )


def canonical_source_plan_bytes() -> bytes:
    return canonical_json_bytes(build_family_a_point_in_time_source_plan()) + b"\n"


__all__ = ["build_family_a_point_in_time_source_plan", "canonical_source_plan_bytes"]
