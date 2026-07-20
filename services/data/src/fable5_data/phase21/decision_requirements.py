"""Pure deterministic builder for Phase 21 composition decision requirements."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from fable5_data.phase21 import canonical as c
from fable5_data.phase21.contracts import (
    FamilyACandidateGroupBinding,
    FamilyACapabilityAssignment,
    FamilyACompositionDecisionGate,
    FamilyADecisionFieldRequirement,
    FamilyAForbiddenSubstitute,
    FamilyAFutureCompositionRule,
    FamilyAInheritedPhase20Input,
    FamilyAOperationalCompositionDecisionRequirements,
    FamilyAPhase15GapBinding,
    FamilyAPostSelectionDependency,
    FamilyAProductRightsBinding,
    FamilyARequiredPriorEvidenceBinding,
    FamilyASourcePlanStepBinding,
    candidate_groups_manifest_sha256,
    capabilities_manifest_sha256,
    decision_fields_manifest_sha256,
    dependencies_manifest_sha256,
    evidence_manifest_sha256,
    gaps_manifest_sha256,
    gates_manifest_sha256,
    inputs_manifest_sha256,
    product_rights_manifest_sha256,
    rules_manifest_sha256,
    steps_manifest_sha256,
    substitutes_manifest_sha256,
)


def _validated[ModelT: BaseModel](
    model: type[ModelT], payload: dict[str, Any], hash_field: str, domain: str
) -> ModelT:
    return model.model_validate({**payload, hash_field: c.domain_sha256(domain, payload)})


def _candidate_groups() -> tuple[FamilyACandidateGroupBinding, ...]:
    return tuple(
        _validated(
            FamilyACandidateGroupBinding,
            {
                "schema_version": c.PHASE21_CANDIDATE_GROUP_SCHEMA_VERSION,
                "ordinal": ordinal,
                "candidate_group_code": row[0],
                "product_codes": row[1],
                "phase17_candidate_group_sha256": row[2],
                "candidate_only": True,
                "operationally_selected": False,
                "ranked": False,
            },
            "binding_sha256",
            c.PHASE21_CANDIDATE_GROUP_HASH_DOMAIN,
        )
        for ordinal, row in enumerate(c.PHASE21_CANDIDATE_GROUP_ROWS, 1)
    )


def _product_rights() -> tuple[FamilyAProductRightsBinding, ...]:
    return tuple(
        _validated(
            FamilyAProductRightsBinding,
            {
                "schema_version": c.PHASE21_PRODUCT_RIGHTS_SCHEMA_VERSION,
                "ordinal": ordinal,
                "product_code": row[0],
                "phase17_product_sha256": row[1],
                "phase18_rights_finding_sha256": row[2],
                "operationally_selected": False,
                "current_rights_verified": False,
            },
            "binding_sha256",
            c.PHASE21_PRODUCT_RIGHTS_HASH_DOMAIN,
        )
        for ordinal, row in enumerate(c.PHASE21_PRODUCT_RIGHTS_ROWS, 1)
    )


def _capabilities() -> tuple[FamilyACapabilityAssignment, ...]:
    return tuple(
        _validated(
            FamilyACapabilityAssignment,
            {
                "schema_version": c.PHASE21_CAPABILITY_SCHEMA_VERSION,
                "ordinal": ordinal,
                "capability_code": row[0],
                "phase16_capability_sha256": row[1],
                "assignment_state": "UNASSIGNED",
                "assigned_product_codes": (),
                "assignment_value_present": False,
            },
            "assignment_sha256",
            c.PHASE21_CAPABILITY_HASH_DOMAIN,
        )
        for ordinal, row in enumerate(c.PHASE21_CAPABILITY_ROWS, 1)
    )


def _decision_fields() -> tuple[FamilyADecisionFieldRequirement, ...]:
    return tuple(
        _validated(
            FamilyADecisionFieldRequirement,
            {
                "schema_version": c.PHASE21_DECISION_FIELD_SCHEMA_VERSION,
                "ordinal": ordinal,
                "field_name": row[0],
                "definition": row[1],
                "required": True,
                "value_present": False,
                "evidence_produced": False,
            },
            "requirement_sha256",
            c.PHASE21_DECISION_FIELD_HASH_DOMAIN,
        )
        for ordinal, row in enumerate(c.PHASE21_DECISION_FIELD_ROWS, 1)
    )


def _dependencies() -> tuple[FamilyAPostSelectionDependency, ...]:
    return tuple(
        _validated(
            FamilyAPostSelectionDependency,
            {
                "schema_version": c.PHASE21_DEPENDENCY_SCHEMA_VERSION,
                "ordinal": ordinal,
                "code": row[0],
                "definition": row[1],
                "state": "BLOCKED_BY_MISSING_COMPOSITION",
                "satisfied": False,
            },
            "dependency_sha256",
            c.PHASE21_DEPENDENCY_HASH_DOMAIN,
        )
        for ordinal, row in enumerate(c.PHASE21_POST_SELECTION_DEPENDENCY_ROWS, 1)
    )


def _gates() -> tuple[FamilyACompositionDecisionGate, ...]:
    return tuple(
        _validated(
            FamilyACompositionDecisionGate,
            {
                "schema_version": c.PHASE21_GATE_SCHEMA_VERSION,
                "ordinal": ordinal,
                "code": row[0],
                "definition": row[1],
                "state": "BLOCKED",
                "passed": False,
            },
            "gate_sha256",
            c.PHASE21_GATE_HASH_DOMAIN,
        )
        for ordinal, row in enumerate(c.PHASE21_GATE_ROWS, 1)
    )


def _rules() -> tuple[FamilyAFutureCompositionRule, ...]:
    return tuple(
        _validated(
            FamilyAFutureCompositionRule,
            {
                "schema_version": c.PHASE21_RULE_SCHEMA_VERSION,
                "ordinal": ordinal,
                "code": row[0],
                "definition": row[1],
                "future_only": True,
                "applied": False,
                "external_action_authorized": False,
            },
            "rule_sha256",
            c.PHASE21_RULE_HASH_DOMAIN,
        )
        for ordinal, row in enumerate(c.PHASE21_FUTURE_RULE_ROWS, 1)
    )


def _substitutes() -> tuple[FamilyAForbiddenSubstitute, ...]:
    return tuple(
        _validated(
            FamilyAForbiddenSubstitute,
            {
                "schema_version": c.PHASE21_SUBSTITUTE_SCHEMA_VERSION,
                "ordinal": ordinal,
                "code": row[0],
                "definition": row[1],
                "forbidden": True,
            },
            "substitute_sha256",
            c.PHASE21_SUBSTITUTE_HASH_DOMAIN,
        )
        for ordinal, row in enumerate(c.PHASE21_FORBIDDEN_SUBSTITUTE_ROWS, 1)
    )


def _inputs() -> tuple[FamilyAInheritedPhase20Input, ...]:
    result: list[FamilyAInheritedPhase20Input] = []
    for ordinal, row in enumerate(c.PHASE20_INPUT_REQUIREMENT_ROWS, 1):
        payload = {
            "schema_version": c.PHASE21_INPUT_BINDING_SCHEMA_VERSION,
            "ordinal": ordinal,
            "category": row[0],
            "code": row[1],
            "definition": row[2],
            "evidence_state": row[3],
            "requirement_satisfied": row[4],
            "required_field_names": row[5],
            "related_phase19_prerequisite_codes": row[6],
            "related_phase15_gap_codes": row[7],
            "reason_code": row[8],
            "source_phase20_requirement_sha256": c.PHASE21_PHASE20_INPUT_SHA256S[ordinal - 1],
            "unchanged": True,
        }
        result.append(
            _validated(
                FamilyAInheritedPhase20Input,
                payload,
                "binding_sha256",
                c.PHASE21_INPUT_BINDING_HASH_DOMAIN,
            )
        )
    return tuple(result)


def _evidence() -> tuple[FamilyARequiredPriorEvidenceBinding, ...]:
    result: list[FamilyARequiredPriorEvidenceBinding] = []
    for ordinal, row in enumerate(c.PHASE20_FUTURE_EVIDENCE_ROWS, 1):
        payload = {
            "schema_version": c.PHASE21_EVIDENCE_BINDING_SCHEMA_VERSION,
            "ordinal": ordinal,
            "name": row[0],
            "state": row[1],
            "produced": row[2],
            "reason_code": row[3],
            "source_phase20_record_sha256": c.PHASE21_PHASE20_EVIDENCE_SHA256S[ordinal - 1],
            "unchanged": True,
        }
        result.append(
            _validated(
                FamilyARequiredPriorEvidenceBinding,
                payload,
                "binding_sha256",
                c.PHASE21_EVIDENCE_BINDING_HASH_DOMAIN,
            )
        )
    return tuple(result)


def _gaps() -> tuple[FamilyAPhase15GapBinding, ...]:
    result: list[FamilyAPhase15GapBinding] = []
    rows = zip(
        c.PHASE20_GAP_CODES,
        c.PHASE20_GAP_STATES,
        c.PHASE20_SOURCE_GAP_SHA256S,
        c.PHASE21_PHASE20_GAP_BINDING_SHA256S,
        strict=True,
    )
    for ordinal, row in enumerate(rows, 1):
        payload = {
            "schema_version": c.PHASE21_GAP_BINDING_SCHEMA_VERSION,
            "ordinal": ordinal,
            "code": row[0],
            "state": row[1],
            "source_gap_sha256": row[2],
            "source_phase20_binding_sha256": row[3],
            "changed_in_phase21": False,
        }
        result.append(
            _validated(
                FamilyAPhase15GapBinding,
                payload,
                "binding_sha256",
                c.PHASE21_GAP_BINDING_HASH_DOMAIN,
            )
        )
    return tuple(result)


def _steps() -> tuple[FamilyASourcePlanStepBinding, ...]:
    result: list[FamilyASourcePlanStepBinding] = []
    rows = zip(
        c.PHASE20_STEP_CODES,
        c.PHASE20_STEP_STATES,
        c.PHASE20_STEP_REASONS,
        c.PHASE21_PHASE20_STEP_BINDING_SHA256S,
        strict=True,
    )
    for ordinal, row in enumerate(rows, 1):
        payload = {
            "schema_version": c.PHASE21_STEP_BINDING_SCHEMA_VERSION,
            "ordinal": ordinal,
            "code": row[0],
            "state": row[1],
            "inherited_reason_code": row[2],
            "source_phase20_binding_sha256": row[3],
            "changed_in_phase21": False,
            "external_action_authorized": False,
        }
        result.append(
            _validated(
                FamilyASourcePlanStepBinding,
                payload,
                "binding_sha256",
                c.PHASE21_STEP_BINDING_HASH_DOMAIN,
            )
        )
    return tuple(result)


def build_family_a_operational_composition_decision_requirements() -> (
    FamilyAOperationalCompositionDecisionRequirements
):
    """Build the sole blocked, value-absent Phase 21 requirements artifact."""

    groups = _candidate_groups()
    products = _product_rights()
    capabilities = _capabilities()
    fields = _decision_fields()
    dependencies = _dependencies()
    gates = _gates()
    rules = _rules()
    substitutes = _substitutes()
    inputs = _inputs()
    evidence = _evidence()
    gaps = _gaps()
    steps = _steps()
    payload = {
        "schema_version": c.PHASE21_ARTIFACT_SCHEMA_VERSION,
        "artifact_id": c.identity(),
        "decision_requirements_policy_id": c.PHASE21_POLICY_ID,
        "decision_requirements_policy_sha256": c.PHASE21_POLICY_SHA256,
        "accepted_phase20_commit_sha": c.PHASE21_ACCEPTED_PHASE20_COMMIT_SHA,
        "accepted_phase20_tree_sha": c.PHASE21_ACCEPTED_PHASE20_TREE_SHA,
        "phase20_artifact_id": c.PHASE21_PHASE20_ARTIFACT_ID,
        "phase20_artifact_sha256": c.PHASE21_PHASE20_ARTIFACT_SHA256,
        "phase20_policy_sha256": c.PHASE21_PHASE20_POLICY_SHA256,
        "phase20_input_requirements_manifest_sha256": c.PHASE21_PHASE20_INPUTS_MANIFEST_SHA256,
        "phase20_required_prior_evidence_manifest_sha256": (
            c.PHASE21_PHASE20_EVIDENCE_MANIFEST_SHA256
        ),
        "phase20_gap_bindings_manifest_sha256": c.PHASE21_PHASE20_GAPS_MANIFEST_SHA256,
        "phase20_steps_manifest_sha256": c.PHASE21_PHASE20_STEPS_MANIFEST_SHA256,
        "phase20_aggregate_conclusion": c.PHASE21_PHASE20_AGGREGATE_CONCLUSION,
        "phase17_artifact_id": c.PHASE21_PHASE17_ARTIFACT_ID,
        "phase17_artifact_sha256": c.PHASE21_PHASE17_ARTIFACT_SHA256,
        "phase17_policy_sha256": c.PHASE21_PHASE17_POLICY_SHA256,
        "phase18_artifact_id": c.PHASE21_PHASE18_ARTIFACT_ID,
        "phase18_artifact_sha256": c.PHASE21_PHASE18_ARTIFACT_SHA256,
        "phase18_policy_sha256": c.PHASE21_PHASE18_POLICY_SHA256,
        "phase16_artifact_id": c.PHASE21_PHASE16_ARTIFACT_ID,
        "phase16_artifact_sha256": c.PHASE21_PHASE16_ARTIFACT_SHA256,
        "family": c.PHASE21_FAMILY,
        "frozen_at_utc": c.PHASE21_FROZEN_AT_UTC,
        "outcome": c.PHASE21_OUTCOME,
        "requirements_state": c.PHASE21_REQUIREMENTS_STATE,
        "aggregate_conclusion": c.PHASE21_AGGREGATE_CONCLUSION,
        "block_reason": c.PHASE21_BLOCK_REASON,
        "candidate_groups_manifest_sha256": candidate_groups_manifest_sha256(groups),
        "product_rights_bindings_manifest_sha256": product_rights_manifest_sha256(products),
        "capability_assignments_manifest_sha256": capabilities_manifest_sha256(capabilities),
        "decision_fields_manifest_sha256": decision_fields_manifest_sha256(fields),
        "post_selection_dependencies_manifest_sha256": dependencies_manifest_sha256(dependencies),
        "decision_gates_manifest_sha256": gates_manifest_sha256(gates),
        "future_rules_manifest_sha256": rules_manifest_sha256(rules),
        "forbidden_substitutes_manifest_sha256": substitutes_manifest_sha256(substitutes),
        "inherited_phase20_inputs_manifest_sha256": inputs_manifest_sha256(inputs),
        "required_prior_evidence_manifest_sha256": evidence_manifest_sha256(evidence),
        "phase15_gap_bindings_manifest_sha256": gaps_manifest_sha256(gaps),
        "source_plan_steps_manifest_sha256": steps_manifest_sha256(steps),
        "candidate_group_bindings": groups,
        "product_rights_bindings": products,
        "capability_assignments": capabilities,
        "decision_fields": fields,
        "post_selection_dependencies": dependencies,
        "decision_gates": gates,
        "future_rules": rules,
        "forbidden_substitutes": substitutes,
        "inherited_phase20_input_requirements": inputs,
        "required_prior_evidence": evidence,
        "phase15_gap_bindings": gaps,
        "source_plan_steps": steps,
        **dict(c.PHASE21_BOUNDARY_VALUES),
        "disclaimer": c.PHASE21_DISCLAIMER,
    }
    return FamilyAOperationalCompositionDecisionRequirements.model_validate(
        {
            **payload,
            "artifact_sha256": c.domain_sha256(c.PHASE21_ARTIFACT_HASH_DOMAIN, payload),
        }
    )


def canonical_operational_composition_decision_requirements_bytes() -> bytes:
    return (
        c.canonical_json_bytes(build_family_a_operational_composition_decision_requirements())
        + b"\n"
    )


__all__ = [
    "build_family_a_operational_composition_decision_requirements",
    "canonical_operational_composition_decision_requirements_bytes",
]
