"""Pure deterministic builder for the Phase 20 evaluation/holdout input register."""

from __future__ import annotations

from fable5_data.phase20 import canonical as c
from fable5_data.phase20.contracts import (
    FamilyAConstructionDependencyGroup,
    FamilyAConstructionGate,
    FamilyAEvaluationHoldoutInputRegister,
    FamilyAEvaluationHoldoutInputRequirement,
    FamilyAForbiddenSubstitute,
    FamilyAFutureEvidenceTransitionRule,
    FamilyAInheritedPhase19Prerequisite,
    FamilyAMissingRequiredPriorEvidence,
    FamilyAPhase15GapBinding,
    FamilyASourcePlanStepBinding,
    construction_gates_manifest_sha256,
    dependency_groups_manifest_sha256,
    forbidden_substitutes_manifest_sha256,
    gap_bindings_manifest_sha256,
    inherited_prerequisites_manifest_sha256,
    input_requirements_manifest_sha256,
    required_evidence_manifest_sha256,
    step_bindings_manifest_sha256,
    transition_rules_manifest_sha256,
)


def _inherited_prerequisites() -> tuple[FamilyAInheritedPhase19Prerequisite, ...]:
    result: list[FamilyAInheritedPhase19Prerequisite] = []
    for ordinal, row in enumerate(c.PHASE20_INHERITED_PREREQUISITE_ROWS, start=1):
        payload = {
            "schema_version": c.PHASE20_INHERITED_PREREQUISITE_SCHEMA_VERSION,
            "ordinal": ordinal,
            "category": row[0],
            "code": row[1],
            "evidence_state": row[2],
            "requirement_satisfied": row[3],
            "inherited_phase19_prerequisite_sha256": row[4],
            "unchanged": True,
        }
        result.append(
            FamilyAInheritedPhase19Prerequisite.model_validate(
                {
                    **payload,
                    "binding_sha256": c.domain_sha256(
                        c.PHASE20_INHERITED_PREREQUISITE_HASH_DOMAIN, payload
                    ),
                }
            )
        )
    return tuple(result)


def _input_requirements() -> tuple[FamilyAEvaluationHoldoutInputRequirement, ...]:
    result: list[FamilyAEvaluationHoldoutInputRequirement] = []
    for ordinal, row in enumerate(c.PHASE20_INPUT_REQUIREMENT_ROWS, start=1):
        payload = {
            "schema_version": c.PHASE20_INPUT_REQUIREMENT_SCHEMA_VERSION,
            "ordinal": ordinal,
            "category": row[0],
            "code": row[1],
            "definition": row[2],
            "evidence_state": row[3],
            "requirement_satisfied": row[4],
            "required_field_names": row[5],
            "related_phase19_prerequisite_codes": row[6],
            "related_phase15_gap_codes": row[7],
            "input_value_present": False,
            "resolves_reserved_evidence": False,
            "reason_code": row[8],
        }
        result.append(
            FamilyAEvaluationHoldoutInputRequirement.model_validate(
                {
                    **payload,
                    "requirement_sha256": c.domain_sha256(
                        c.PHASE20_INPUT_REQUIREMENT_HASH_DOMAIN, payload
                    ),
                }
            )
        )
    return tuple(result)


def _required_prior_evidence() -> tuple[FamilyAMissingRequiredPriorEvidence, ...]:
    result: list[FamilyAMissingRequiredPriorEvidence] = []
    for ordinal, row in enumerate(c.PHASE20_FUTURE_EVIDENCE_ROWS, start=1):
        payload = {
            "schema_version": c.PHASE20_FUTURE_EVIDENCE_SCHEMA_VERSION,
            "ordinal": ordinal,
            "name": row[0],
            "state": row[1],
            "produced": row[2],
            "reason_code": row[3],
        }
        result.append(
            FamilyAMissingRequiredPriorEvidence.model_validate(
                {
                    **payload,
                    "record_sha256": c.domain_sha256(
                        c.PHASE20_FUTURE_EVIDENCE_HASH_DOMAIN, payload
                    ),
                }
            )
        )
    return tuple(result)


def _transition_rules() -> tuple[FamilyAFutureEvidenceTransitionRule, ...]:
    result: list[FamilyAFutureEvidenceTransitionRule] = []
    for ordinal, row in enumerate(c.PHASE20_TRANSITION_RULE_ROWS, start=1):
        payload = {
            "schema_version": c.PHASE20_TRANSITION_RULE_SCHEMA_VERSION,
            "ordinal": ordinal,
            "code": row[0],
            "definition": row[1],
            "reason_code": row[2],
            "future_only": True,
            "applied": False,
            "external_action_authorized": False,
        }
        result.append(
            FamilyAFutureEvidenceTransitionRule.model_validate(
                {
                    **payload,
                    "rule_sha256": c.domain_sha256(c.PHASE20_TRANSITION_RULE_HASH_DOMAIN, payload),
                }
            )
        )
    return tuple(result)


def _dependency_groups() -> tuple[FamilyAConstructionDependencyGroup, ...]:
    result: list[FamilyAConstructionDependencyGroup] = []
    for ordinal, row in enumerate(c.PHASE20_DEPENDENCY_GROUP_ROWS, start=1):
        payload = {
            "schema_version": c.PHASE20_DEPENDENCY_GROUP_SCHEMA_VERSION,
            "ordinal": ordinal,
            "code": row[0],
            "definition": row[1],
            "input_codes": row[2],
            "prerequisite_group_codes": row[3],
            "state": row[4],
            "reason_code": row[5],
        }
        result.append(
            FamilyAConstructionDependencyGroup.model_validate(
                {
                    **payload,
                    "group_sha256": c.domain_sha256(
                        c.PHASE20_DEPENDENCY_GROUP_HASH_DOMAIN, payload
                    ),
                }
            )
        )
    return tuple(result)


def _construction_gates() -> tuple[FamilyAConstructionGate, ...]:
    result: list[FamilyAConstructionGate] = []
    for ordinal, row in enumerate(c.PHASE20_CONSTRUCTION_GATE_ROWS, start=1):
        payload = {
            "schema_version": c.PHASE20_CONSTRUCTION_GATE_SCHEMA_VERSION,
            "ordinal": ordinal,
            "code": row[0],
            "definition": row[1],
            "required_group_codes": row[2],
            "state": row[3],
            "passed": row[4],
            "required_before_observation": row[5],
            "reason_code": row[6],
        }
        result.append(
            FamilyAConstructionGate.model_validate(
                {
                    **payload,
                    "gate_sha256": c.domain_sha256(
                        c.PHASE20_CONSTRUCTION_GATE_HASH_DOMAIN, payload
                    ),
                }
            )
        )
    return tuple(result)


def _forbidden_substitutes() -> tuple[FamilyAForbiddenSubstitute, ...]:
    result: list[FamilyAForbiddenSubstitute] = []
    for ordinal, row in enumerate(c.PHASE20_FORBIDDEN_SUBSTITUTE_ROWS, start=1):
        payload = {
            "schema_version": c.PHASE20_FORBIDDEN_SUBSTITUTE_SCHEMA_VERSION,
            "ordinal": ordinal,
            "code": row[0],
            "definition": row[1],
            "target_output_classes": row[2],
            "forbidden": row[3],
            "reason_code": row[4],
        }
        result.append(
            FamilyAForbiddenSubstitute.model_validate(
                {
                    **payload,
                    "substitute_sha256": c.domain_sha256(
                        c.PHASE20_FORBIDDEN_SUBSTITUTE_HASH_DOMAIN, payload
                    ),
                }
            )
        )
    return tuple(result)


def _phase15_gap_bindings() -> tuple[FamilyAPhase15GapBinding, ...]:
    result: list[FamilyAPhase15GapBinding] = []
    rows = zip(
        c.PHASE20_GAP_CODES,
        c.PHASE20_GAP_STATES,
        c.PHASE20_SOURCE_GAP_SHA256S,
        c.PHASE20_PHASE19_GAP_BINDING_SHA256S,
        strict=True,
    )
    for ordinal, row in enumerate(rows, start=1):
        payload = {
            "schema_version": c.PHASE20_GAP_BINDING_SCHEMA_VERSION,
            "ordinal": ordinal,
            "code": row[0],
            "state": row[1],
            "source_gap_sha256": row[2],
            "inherited_phase19_binding_sha256": row[3],
            "changed_in_phase20": False,
        }
        result.append(
            FamilyAPhase15GapBinding.model_validate(
                {
                    **payload,
                    "binding_sha256": c.domain_sha256(c.PHASE20_GAP_BINDING_HASH_DOMAIN, payload),
                }
            )
        )
    return tuple(result)


def _source_plan_steps() -> tuple[FamilyASourcePlanStepBinding, ...]:
    result: list[FamilyASourcePlanStepBinding] = []
    rows = zip(
        c.PHASE20_STEP_CODES,
        c.PHASE20_STEP_STATES,
        c.PHASE20_STEP_REASONS,
        c.PHASE20_PHASE19_STEP_SHA256S,
        strict=True,
    )
    for ordinal, row in enumerate(rows, start=1):
        payload = {
            "schema_version": c.PHASE20_STEP_BINDING_SCHEMA_VERSION,
            "ordinal": ordinal,
            "code": row[0],
            "state": row[1],
            "inherited_reason_code": row[2],
            "inherited_phase19_step_sha256": row[3],
            "changed_in_phase20": False,
            "external_action_authorized": False,
        }
        result.append(
            FamilyASourcePlanStepBinding.model_validate(
                {
                    **payload,
                    "binding_sha256": c.domain_sha256(c.PHASE20_STEP_BINDING_HASH_DOMAIN, payload),
                }
            )
        )
    return tuple(result)


def build_family_a_evaluation_holdout_input_register() -> FamilyAEvaluationHoldoutInputRegister:
    """Build the sole blocked, value-absent input register without runtime I/O."""

    inherited_prerequisites = _inherited_prerequisites()
    input_requirements = _input_requirements()
    required_evidence = _required_prior_evidence()
    transition_rules = _transition_rules()
    dependency_groups = _dependency_groups()
    construction_gates = _construction_gates()
    forbidden_substitutes = _forbidden_substitutes()
    gap_bindings = _phase15_gap_bindings()
    steps = _source_plan_steps()
    payload = {
        "schema_version": c.PHASE20_ARTIFACT_SCHEMA_VERSION,
        "artifact_id": c.identity(c.PHASE20_REGISTER_POLICY_SHA256),
        "input_register_policy_id": c.PHASE20_INPUT_REGISTER_POLICY_ID,
        "input_register_policy_sha256": c.PHASE20_REGISTER_POLICY_SHA256,
        "accepted_phase19_commit_sha": c.PHASE20_ACCEPTED_PHASE19_COMMIT_SHA,
        "accepted_phase19_tree_sha": c.PHASE20_ACCEPTED_PHASE19_TREE_SHA,
        "phase19_artifact_id": c.PHASE20_PHASE19_ARTIFACT_ID,
        "phase19_artifact_sha256": c.PHASE20_PHASE19_ARTIFACT_SHA256,
        "phase19_policy_sha256": c.PHASE20_PHASE19_POLICY_SHA256,
        "phase19_prerequisites_manifest_sha256": (c.PHASE20_PHASE19_PREREQUISITES_MANIFEST_SHA256),
        "phase19_required_evidence_manifest_sha256": (
            c.PHASE20_PHASE19_REQUIRED_EVIDENCE_MANIFEST_SHA256
        ),
        "phase19_gap_bindings_manifest_sha256": (c.PHASE20_PHASE19_GAP_BINDINGS_MANIFEST_SHA256),
        "phase19_steps_manifest_sha256": c.PHASE20_PHASE19_STEPS_MANIFEST_SHA256,
        "phase19_aggregate_conclusion": c.PHASE20_PHASE19_AGGREGATE_CONCLUSION,
        "phase15_gaps_manifest_sha256": c.PHASE20_PHASE15_GAPS_MANIFEST_SHA256,
        "family": c.PHASE20_FAMILY,
        "frozen_at_utc": c.PHASE20_FROZEN_AT_UTC,
        "outcome": c.PHASE20_OUTCOME,
        "register_state": c.PHASE20_REGISTER_STATE,
        "aggregate_conclusion": c.PHASE20_AGGREGATE_CONCLUSION,
        "block_reason": c.PHASE20_BLOCK_REASON,
        "inherited_phase19_prerequisites_manifest_sha256": (
            inherited_prerequisites_manifest_sha256(inherited_prerequisites)
        ),
        "input_requirements_manifest_sha256": input_requirements_manifest_sha256(
            input_requirements
        ),
        "required_prior_evidence_manifest_sha256": required_evidence_manifest_sha256(
            required_evidence
        ),
        "transition_rules_manifest_sha256": transition_rules_manifest_sha256(transition_rules),
        "construction_dependency_groups_manifest_sha256": dependency_groups_manifest_sha256(
            dependency_groups
        ),
        "construction_gates_manifest_sha256": construction_gates_manifest_sha256(
            construction_gates
        ),
        "forbidden_substitutes_manifest_sha256": forbidden_substitutes_manifest_sha256(
            forbidden_substitutes
        ),
        "phase15_gap_bindings_manifest_sha256": gap_bindings_manifest_sha256(gap_bindings),
        "source_plan_steps_manifest_sha256": step_bindings_manifest_sha256(steps),
        "inherited_phase19_prerequisites": inherited_prerequisites,
        "input_requirements": input_requirements,
        "required_prior_evidence": required_evidence,
        "transition_rules": transition_rules,
        "construction_dependency_groups": dependency_groups,
        "construction_gates": construction_gates,
        "forbidden_substitutes": forbidden_substitutes,
        "phase15_gap_bindings": gap_bindings,
        "source_plan_steps": steps,
        **dict(c.PHASE20_BOUNDARY_VALUES),
        "disclaimer": c.PHASE20_DISCLAIMER,
    }
    return FamilyAEvaluationHoldoutInputRegister.model_validate(
        {
            **payload,
            "artifact_sha256": c.domain_sha256(c.PHASE20_ARTIFACT_HASH_DOMAIN, payload),
        }
    )


def canonical_evaluation_holdout_input_register_bytes() -> bytes:
    return c.canonical_json_bytes(build_family_a_evaluation_holdout_input_register()) + b"\n"


__all__ = [
    "build_family_a_evaluation_holdout_input_register",
    "canonical_evaluation_holdout_input_register_bytes",
]
