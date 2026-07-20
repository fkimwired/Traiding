"""Strict contracts for Phase 21 operational-composition decision requirements."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from fable5_data.phase21 import canonical as c

SHA256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
GitSHA = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]
ClosedText = Annotated[str, StringConstraints(min_length=1, max_length=2400)]
FrozenTimestamp = Annotated[
    str,
    StringConstraints(pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$"),
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")


class RequirementsOutcome(StrEnum):
    BLOCKED = "BLOCKED"


class RequirementsState(StrEnum):
    DECISION_REQUIREMENTS_FROZEN = "DECISION_REQUIREMENTS_FROZEN"


class RequirementsConclusion(StrEnum):
    BLOCKED_AWAITING_EXPLICIT_OPERATIONAL_SOURCE_PRODUCT_COMPOSITION = (
        "BLOCKED_AWAITING_EXPLICIT_OPERATIONAL_SOURCE_PRODUCT_COMPOSITION"
    )


class BlockedState(StrEnum):
    BLOCKED_BY_MISSING_COMPOSITION = "BLOCKED_BY_MISSING_COMPOSITION"
    BLOCKED = "BLOCKED"


class CapabilityAssignmentState(StrEnum):
    UNASSIGNED = "UNASSIGNED"


def _check_exact(
    model: StrictModel,
    expected: dict[str, object],
    hash_field: str,
    domain: str,
    message: str,
) -> None:
    actual = model.model_dump(mode="python", exclude={hash_field})
    if c.canonicalize(actual) != c.canonicalize(expected):
        raise ValueError(message)
    if getattr(model, hash_field) != c.domain_sha256(domain, expected):
        raise ValueError(f"{message} hash mismatch")


class FamilyACandidateGroupBinding(StrictModel):
    schema_version: str
    ordinal: Annotated[int, Field(ge=1, le=6)]
    candidate_group_code: ClosedText
    product_codes: Annotated[tuple[ClosedText, ...], Field(min_length=1, max_length=4)]
    phase17_candidate_group_sha256: SHA256
    candidate_only: bool
    operationally_selected: bool
    ranked: bool
    binding_sha256: SHA256

    @model_validator(mode="after")
    def validate_binding(self) -> Self:
        row = c.PHASE21_CANDIDATE_GROUP_ROWS[self.ordinal - 1]
        expected = {
            "schema_version": c.PHASE21_CANDIDATE_GROUP_SCHEMA_VERSION,
            "ordinal": self.ordinal,
            "candidate_group_code": row[0],
            "product_codes": row[1],
            "phase17_candidate_group_sha256": row[2],
            "candidate_only": True,
            "operationally_selected": False,
            "ranked": False,
        }
        _check_exact(
            self,
            expected,
            "binding_sha256",
            c.PHASE21_CANDIDATE_GROUP_HASH_DOMAIN,
            "candidate-group binding drifted",
        )
        return self


class FamilyAProductRightsBinding(StrictModel):
    schema_version: str
    ordinal: Annotated[int, Field(ge=1, le=9)]
    product_code: ClosedText
    phase17_product_sha256: SHA256
    phase18_rights_finding_sha256: SHA256
    operationally_selected: bool
    current_rights_verified: bool
    binding_sha256: SHA256

    @model_validator(mode="after")
    def validate_binding(self) -> Self:
        row = c.PHASE21_PRODUCT_RIGHTS_ROWS[self.ordinal - 1]
        expected = {
            "schema_version": c.PHASE21_PRODUCT_RIGHTS_SCHEMA_VERSION,
            "ordinal": self.ordinal,
            "product_code": row[0],
            "phase17_product_sha256": row[1],
            "phase18_rights_finding_sha256": row[2],
            "operationally_selected": False,
            "current_rights_verified": False,
        }
        _check_exact(
            self,
            expected,
            "binding_sha256",
            c.PHASE21_PRODUCT_RIGHTS_HASH_DOMAIN,
            "product-rights binding drifted",
        )
        return self


class FamilyACapabilityAssignment(StrictModel):
    schema_version: str
    ordinal: Annotated[int, Field(ge=1, le=7)]
    capability_code: ClosedText
    phase16_capability_sha256: SHA256
    assignment_state: CapabilityAssignmentState
    assigned_product_codes: tuple[ClosedText, ...]
    assignment_value_present: bool
    assignment_sha256: SHA256

    @model_validator(mode="after")
    def validate_assignment(self) -> Self:
        row = c.PHASE21_CAPABILITY_ROWS[self.ordinal - 1]
        expected = {
            "schema_version": c.PHASE21_CAPABILITY_SCHEMA_VERSION,
            "ordinal": self.ordinal,
            "capability_code": row[0],
            "phase16_capability_sha256": row[1],
            "assignment_state": "UNASSIGNED",
            "assigned_product_codes": (),
            "assignment_value_present": False,
        }
        _check_exact(
            self,
            expected,
            "assignment_sha256",
            c.PHASE21_CAPABILITY_HASH_DOMAIN,
            "capability assignment drifted",
        )
        return self


class FamilyADecisionFieldRequirement(StrictModel):
    schema_version: str
    ordinal: Annotated[int, Field(ge=1, le=8)]
    field_name: ClosedText
    definition: ClosedText
    required: bool
    value_present: bool
    evidence_produced: bool
    requirement_sha256: SHA256

    @model_validator(mode="after")
    def validate_requirement(self) -> Self:
        row = c.PHASE21_DECISION_FIELD_ROWS[self.ordinal - 1]
        expected = {
            "schema_version": c.PHASE21_DECISION_FIELD_SCHEMA_VERSION,
            "ordinal": self.ordinal,
            "field_name": row[0],
            "definition": row[1],
            "required": True,
            "value_present": False,
            "evidence_produced": False,
        }
        _check_exact(
            self,
            expected,
            "requirement_sha256",
            c.PHASE21_DECISION_FIELD_HASH_DOMAIN,
            "decision-field requirement drifted",
        )
        return self


class FamilyAPostSelectionDependency(StrictModel):
    schema_version: str
    ordinal: Annotated[int, Field(ge=1, le=3)]
    code: ClosedText
    definition: ClosedText
    state: BlockedState
    satisfied: bool
    dependency_sha256: SHA256

    @model_validator(mode="after")
    def validate_dependency(self) -> Self:
        row = c.PHASE21_POST_SELECTION_DEPENDENCY_ROWS[self.ordinal - 1]
        expected = {
            "schema_version": c.PHASE21_DEPENDENCY_SCHEMA_VERSION,
            "ordinal": self.ordinal,
            "code": row[0],
            "definition": row[1],
            "state": "BLOCKED_BY_MISSING_COMPOSITION",
            "satisfied": False,
        }
        _check_exact(
            self,
            expected,
            "dependency_sha256",
            c.PHASE21_DEPENDENCY_HASH_DOMAIN,
            "post-selection dependency drifted",
        )
        return self


class FamilyACompositionDecisionGate(StrictModel):
    schema_version: str
    ordinal: Annotated[int, Field(ge=1, le=6)]
    code: ClosedText
    definition: ClosedText
    state: BlockedState
    passed: bool
    gate_sha256: SHA256

    @model_validator(mode="after")
    def validate_gate(self) -> Self:
        row = c.PHASE21_GATE_ROWS[self.ordinal - 1]
        expected = {
            "schema_version": c.PHASE21_GATE_SCHEMA_VERSION,
            "ordinal": self.ordinal,
            "code": row[0],
            "definition": row[1],
            "state": "BLOCKED",
            "passed": False,
        }
        _check_exact(
            self, expected, "gate_sha256", c.PHASE21_GATE_HASH_DOMAIN, "composition gate drifted"
        )
        return self


class FamilyAFutureCompositionRule(StrictModel):
    schema_version: str
    ordinal: Annotated[int, Field(ge=1, le=8)]
    code: ClosedText
    definition: ClosedText
    future_only: bool
    applied: bool
    external_action_authorized: bool
    rule_sha256: SHA256

    @model_validator(mode="after")
    def validate_rule(self) -> Self:
        row = c.PHASE21_FUTURE_RULE_ROWS[self.ordinal - 1]
        expected = {
            "schema_version": c.PHASE21_RULE_SCHEMA_VERSION,
            "ordinal": self.ordinal,
            "code": row[0],
            "definition": row[1],
            "future_only": True,
            "applied": False,
            "external_action_authorized": False,
        }
        _check_exact(
            self,
            expected,
            "rule_sha256",
            c.PHASE21_RULE_HASH_DOMAIN,
            "future composition rule drifted",
        )
        return self


class FamilyAForbiddenSubstitute(StrictModel):
    schema_version: str
    ordinal: Annotated[int, Field(ge=1, le=10)]
    code: ClosedText
    definition: ClosedText
    forbidden: bool
    substitute_sha256: SHA256

    @model_validator(mode="after")
    def validate_substitute(self) -> Self:
        row = c.PHASE21_FORBIDDEN_SUBSTITUTE_ROWS[self.ordinal - 1]
        expected = {
            "schema_version": c.PHASE21_SUBSTITUTE_SCHEMA_VERSION,
            "ordinal": self.ordinal,
            "code": row[0],
            "definition": row[1],
            "forbidden": True,
        }
        _check_exact(
            self,
            expected,
            "substitute_sha256",
            c.PHASE21_SUBSTITUTE_HASH_DOMAIN,
            "forbidden substitute drifted",
        )
        return self


class FamilyAInheritedPhase20Input(StrictModel):
    schema_version: str
    ordinal: Annotated[int, Field(ge=1, le=20)]
    category: ClosedText
    code: ClosedText
    definition: ClosedText
    evidence_state: ClosedText
    requirement_satisfied: bool
    required_field_names: Annotated[tuple[ClosedText, ...], Field(min_length=1, max_length=32)]
    related_phase19_prerequisite_codes: Annotated[
        tuple[ClosedText, ...], Field(min_length=1, max_length=8)
    ]
    related_phase15_gap_codes: Annotated[tuple[ClosedText, ...], Field(min_length=1, max_length=8)]
    reason_code: ClosedText
    source_phase20_requirement_sha256: SHA256
    unchanged: bool
    binding_sha256: SHA256

    @model_validator(mode="after")
    def validate_binding(self) -> Self:
        row = c.PHASE20_INPUT_REQUIREMENT_ROWS[self.ordinal - 1]
        expected = {
            "schema_version": c.PHASE21_INPUT_BINDING_SCHEMA_VERSION,
            "ordinal": self.ordinal,
            "category": row[0],
            "code": row[1],
            "definition": row[2],
            "evidence_state": row[3],
            "requirement_satisfied": row[4],
            "required_field_names": row[5],
            "related_phase19_prerequisite_codes": row[6],
            "related_phase15_gap_codes": row[7],
            "reason_code": row[8],
            "source_phase20_requirement_sha256": c.PHASE21_PHASE20_INPUT_SHA256S[self.ordinal - 1],
            "unchanged": True,
        }
        _check_exact(
            self,
            expected,
            "binding_sha256",
            c.PHASE21_INPUT_BINDING_HASH_DOMAIN,
            "inherited Phase 20 input drifted",
        )
        return self


class FamilyARequiredPriorEvidenceBinding(StrictModel):
    schema_version: str
    ordinal: Annotated[int, Field(ge=1, le=2)]
    name: ClosedText
    state: ClosedText
    produced: bool
    reason_code: ClosedText
    source_phase20_record_sha256: SHA256
    unchanged: bool
    binding_sha256: SHA256

    @model_validator(mode="after")
    def validate_binding(self) -> Self:
        row = c.PHASE20_FUTURE_EVIDENCE_ROWS[self.ordinal - 1]
        expected = {
            "schema_version": c.PHASE21_EVIDENCE_BINDING_SCHEMA_VERSION,
            "ordinal": self.ordinal,
            "name": row[0],
            "state": row[1],
            "produced": row[2],
            "reason_code": row[3],
            "source_phase20_record_sha256": c.PHASE21_PHASE20_EVIDENCE_SHA256S[self.ordinal - 1],
            "unchanged": True,
        }
        _check_exact(
            self,
            expected,
            "binding_sha256",
            c.PHASE21_EVIDENCE_BINDING_HASH_DOMAIN,
            "required-prior-evidence binding drifted",
        )
        return self


class FamilyAPhase15GapBinding(StrictModel):
    schema_version: str
    ordinal: Annotated[int, Field(ge=1, le=19)]
    code: ClosedText
    state: ClosedText
    source_gap_sha256: SHA256
    source_phase20_binding_sha256: SHA256
    changed_in_phase21: bool
    binding_sha256: SHA256

    @model_validator(mode="after")
    def validate_binding(self) -> Self:
        i = self.ordinal - 1
        expected = {
            "schema_version": c.PHASE21_GAP_BINDING_SCHEMA_VERSION,
            "ordinal": self.ordinal,
            "code": c.PHASE20_GAP_CODES[i],
            "state": c.PHASE20_GAP_STATES[i],
            "source_gap_sha256": c.PHASE20_SOURCE_GAP_SHA256S[i],
            "source_phase20_binding_sha256": c.PHASE21_PHASE20_GAP_BINDING_SHA256S[i],
            "changed_in_phase21": False,
        }
        _check_exact(
            self,
            expected,
            "binding_sha256",
            c.PHASE21_GAP_BINDING_HASH_DOMAIN,
            "Phase 15 gap binding drifted",
        )
        return self


class FamilyASourcePlanStepBinding(StrictModel):
    schema_version: str
    ordinal: Annotated[int, Field(ge=1, le=7)]
    code: ClosedText
    state: ClosedText
    inherited_reason_code: ClosedText
    source_phase20_binding_sha256: SHA256
    changed_in_phase21: bool
    external_action_authorized: bool
    binding_sha256: SHA256

    @model_validator(mode="after")
    def validate_binding(self) -> Self:
        i = self.ordinal - 1
        expected = {
            "schema_version": c.PHASE21_STEP_BINDING_SCHEMA_VERSION,
            "ordinal": self.ordinal,
            "code": c.PHASE20_STEP_CODES[i],
            "state": c.PHASE20_STEP_STATES[i],
            "inherited_reason_code": c.PHASE20_STEP_REASONS[i],
            "source_phase20_binding_sha256": c.PHASE21_PHASE20_STEP_BINDING_SHA256S[i],
            "changed_in_phase21": False,
            "external_action_authorized": False,
        }
        _check_exact(
            self,
            expected,
            "binding_sha256",
            c.PHASE21_STEP_BINDING_HASH_DOMAIN,
            "source-plan step binding drifted",
        )
        return self


def _manifest(domain: str, rows: tuple[StrictModel, ...], hash_field: str) -> str:
    return c.domain_sha256(domain, tuple(getattr(row, hash_field) for row in rows))


def candidate_groups_manifest_sha256(rows: tuple[FamilyACandidateGroupBinding, ...]) -> str:
    return _manifest(c.PHASE21_CANDIDATE_GROUPS_MANIFEST_HASH_DOMAIN, rows, "binding_sha256")


def product_rights_manifest_sha256(rows: tuple[FamilyAProductRightsBinding, ...]) -> str:
    return _manifest(c.PHASE21_PRODUCT_RIGHTS_MANIFEST_HASH_DOMAIN, rows, "binding_sha256")


def capabilities_manifest_sha256(rows: tuple[FamilyACapabilityAssignment, ...]) -> str:
    return _manifest(c.PHASE21_CAPABILITIES_MANIFEST_HASH_DOMAIN, rows, "assignment_sha256")


def decision_fields_manifest_sha256(rows: tuple[FamilyADecisionFieldRequirement, ...]) -> str:
    return _manifest(c.PHASE21_DECISION_FIELDS_MANIFEST_HASH_DOMAIN, rows, "requirement_sha256")


def dependencies_manifest_sha256(rows: tuple[FamilyAPostSelectionDependency, ...]) -> str:
    return _manifest(c.PHASE21_DEPENDENCIES_MANIFEST_HASH_DOMAIN, rows, "dependency_sha256")


def gates_manifest_sha256(rows: tuple[FamilyACompositionDecisionGate, ...]) -> str:
    return _manifest(c.PHASE21_GATES_MANIFEST_HASH_DOMAIN, rows, "gate_sha256")


def rules_manifest_sha256(rows: tuple[FamilyAFutureCompositionRule, ...]) -> str:
    return _manifest(c.PHASE21_RULES_MANIFEST_HASH_DOMAIN, rows, "rule_sha256")


def substitutes_manifest_sha256(rows: tuple[FamilyAForbiddenSubstitute, ...]) -> str:
    return _manifest(c.PHASE21_SUBSTITUTES_MANIFEST_HASH_DOMAIN, rows, "substitute_sha256")


def inputs_manifest_sha256(rows: tuple[FamilyAInheritedPhase20Input, ...]) -> str:
    return _manifest(c.PHASE21_INPUTS_MANIFEST_HASH_DOMAIN, rows, "binding_sha256")


def evidence_manifest_sha256(rows: tuple[FamilyARequiredPriorEvidenceBinding, ...]) -> str:
    return _manifest(c.PHASE21_EVIDENCE_MANIFEST_HASH_DOMAIN, rows, "binding_sha256")


def gaps_manifest_sha256(rows: tuple[FamilyAPhase15GapBinding, ...]) -> str:
    return _manifest(c.PHASE21_GAPS_MANIFEST_HASH_DOMAIN, rows, "binding_sha256")


def steps_manifest_sha256(rows: tuple[FamilyASourcePlanStepBinding, ...]) -> str:
    return _manifest(c.PHASE21_STEPS_MANIFEST_HASH_DOMAIN, rows, "binding_sha256")


class FamilyAOperationalCompositionDecisionRequirements(StrictModel):
    schema_version: str
    artifact_id: UUID
    artifact_sha256: SHA256
    decision_requirements_policy_id: str
    decision_requirements_policy_sha256: SHA256
    accepted_phase20_commit_sha: GitSHA
    accepted_phase20_tree_sha: GitSHA
    phase20_artifact_id: UUID
    phase20_artifact_sha256: SHA256
    phase20_policy_sha256: SHA256
    phase20_input_requirements_manifest_sha256: SHA256
    phase20_required_prior_evidence_manifest_sha256: SHA256
    phase20_gap_bindings_manifest_sha256: SHA256
    phase20_steps_manifest_sha256: SHA256
    phase20_aggregate_conclusion: str
    phase17_artifact_id: UUID
    phase17_artifact_sha256: SHA256
    phase17_policy_sha256: SHA256
    phase18_artifact_id: UUID
    phase18_artifact_sha256: SHA256
    phase18_policy_sha256: SHA256
    phase16_artifact_id: UUID
    phase16_artifact_sha256: SHA256
    family: str
    frozen_at_utc: FrozenTimestamp
    outcome: RequirementsOutcome
    requirements_state: RequirementsState
    aggregate_conclusion: RequirementsConclusion
    block_reason: ClosedText
    candidate_groups_manifest_sha256: SHA256
    product_rights_bindings_manifest_sha256: SHA256
    capability_assignments_manifest_sha256: SHA256
    decision_fields_manifest_sha256: SHA256
    post_selection_dependencies_manifest_sha256: SHA256
    decision_gates_manifest_sha256: SHA256
    future_rules_manifest_sha256: SHA256
    forbidden_substitutes_manifest_sha256: SHA256
    inherited_phase20_inputs_manifest_sha256: SHA256
    required_prior_evidence_manifest_sha256: SHA256
    phase15_gap_bindings_manifest_sha256: SHA256
    source_plan_steps_manifest_sha256: SHA256
    candidate_group_bindings: Annotated[
        tuple[FamilyACandidateGroupBinding, ...], Field(min_length=6, max_length=6)
    ]
    product_rights_bindings: Annotated[
        tuple[FamilyAProductRightsBinding, ...], Field(min_length=9, max_length=9)
    ]
    capability_assignments: Annotated[
        tuple[FamilyACapabilityAssignment, ...], Field(min_length=7, max_length=7)
    ]
    decision_fields: Annotated[
        tuple[FamilyADecisionFieldRequirement, ...], Field(min_length=8, max_length=8)
    ]
    post_selection_dependencies: Annotated[
        tuple[FamilyAPostSelectionDependency, ...], Field(min_length=3, max_length=3)
    ]
    decision_gates: Annotated[
        tuple[FamilyACompositionDecisionGate, ...], Field(min_length=6, max_length=6)
    ]
    future_rules: Annotated[
        tuple[FamilyAFutureCompositionRule, ...], Field(min_length=8, max_length=8)
    ]
    forbidden_substitutes: Annotated[
        tuple[FamilyAForbiddenSubstitute, ...], Field(min_length=10, max_length=10)
    ]
    inherited_phase20_input_requirements: Annotated[
        tuple[FamilyAInheritedPhase20Input, ...], Field(min_length=20, max_length=20)
    ]
    required_prior_evidence: Annotated[
        tuple[FamilyARequiredPriorEvidenceBinding, ...], Field(min_length=2, max_length=2)
    ]
    phase15_gap_bindings: Annotated[
        tuple[FamilyAPhase15GapBinding, ...], Field(min_length=19, max_length=19)
    ]
    source_plan_steps: Annotated[
        tuple[FamilyASourcePlanStepBinding, ...], Field(min_length=7, max_length=7)
    ]
    metadata_only: bool
    requirements_only: bool
    decision_requirements_only: bool
    runtime_network_disabled: bool
    phase20_inputs_unchanged: bool
    inherited_phase15_gaps_unchanged: bool
    source_plan_steps_unchanged: bool
    candidate_groups_candidate_only: bool
    operational_source_product_composition_selected: bool
    composition_ranked: bool
    composition_value_present: bool
    selection_evidence_produced: bool
    operational_composition_output_produced: bool
    provider_selected: bool
    product_selected: bool
    source_selected: bool
    delivery_selected: bool
    credentials_loaded: bool
    account_verified: bool
    rights_currentness_guaranteed: bool
    rights_verified: bool
    rights_granted: bool
    operational_use_cleared: bool
    operational_external_request_performed: bool
    provider_data_request_performed: bool
    external_data_capture_authorized: bool
    provider_payload_persisted: bool
    licensed_data_persisted: bool
    research_ingestion_authorized: bool
    research_executed: bool
    performance_computed: bool
    execution_authorized: bool
    order_submission_authorized: bool
    pull_request_identity_used: bool
    tag_identity_used: bool
    release_identity_used: bool
    publication_identity_used: bool
    deployment_identity_used: bool
    live_path_absent: bool
    no_personalized_investment_advice: bool
    no_real_performance_claimed: bool
    disclaimer: ClosedText

    @model_validator(mode="after")
    def validate_artifact(self) -> Self:
        identities = (
            self.schema_version == c.PHASE21_ARTIFACT_SCHEMA_VERSION,
            self.artifact_id == c.identity(),
            self.decision_requirements_policy_id == c.PHASE21_POLICY_ID,
            self.decision_requirements_policy_sha256 == c.PHASE21_POLICY_SHA256,
            self.accepted_phase20_commit_sha == c.PHASE21_ACCEPTED_PHASE20_COMMIT_SHA,
            self.accepted_phase20_tree_sha == c.PHASE21_ACCEPTED_PHASE20_TREE_SHA,
            str(self.phase20_artifact_id) == c.PHASE21_PHASE20_ARTIFACT_ID,
            self.phase20_artifact_sha256 == c.PHASE21_PHASE20_ARTIFACT_SHA256,
            self.phase20_policy_sha256 == c.PHASE21_PHASE20_POLICY_SHA256,
            self.phase20_input_requirements_manifest_sha256
            == c.PHASE21_PHASE20_INPUTS_MANIFEST_SHA256,
            self.phase20_required_prior_evidence_manifest_sha256
            == c.PHASE21_PHASE20_EVIDENCE_MANIFEST_SHA256,
            self.phase20_gap_bindings_manifest_sha256 == c.PHASE21_PHASE20_GAPS_MANIFEST_SHA256,
            self.phase20_steps_manifest_sha256 == c.PHASE21_PHASE20_STEPS_MANIFEST_SHA256,
            self.phase20_aggregate_conclusion == c.PHASE21_PHASE20_AGGREGATE_CONCLUSION,
            str(self.phase17_artifact_id) == c.PHASE21_PHASE17_ARTIFACT_ID,
            self.phase17_artifact_sha256 == c.PHASE21_PHASE17_ARTIFACT_SHA256,
            self.phase17_policy_sha256 == c.PHASE21_PHASE17_POLICY_SHA256,
            str(self.phase18_artifact_id) == c.PHASE21_PHASE18_ARTIFACT_ID,
            self.phase18_artifact_sha256 == c.PHASE21_PHASE18_ARTIFACT_SHA256,
            self.phase18_policy_sha256 == c.PHASE21_PHASE18_POLICY_SHA256,
            str(self.phase16_artifact_id) == c.PHASE21_PHASE16_ARTIFACT_ID,
            self.phase16_artifact_sha256 == c.PHASE21_PHASE16_ARTIFACT_SHA256,
            self.family == c.PHASE21_FAMILY,
            self.frozen_at_utc == c.PHASE21_FROZEN_AT_UTC,
            self.outcome.value == c.PHASE21_OUTCOME,
            self.requirements_state.value == c.PHASE21_REQUIREMENTS_STATE,
            self.aggregate_conclusion.value == c.PHASE21_AGGREGATE_CONCLUSION,
            self.block_reason == c.PHASE21_BLOCK_REASON,
            self.disclaimer == c.PHASE21_DISCLAIMER,
        )
        if not all(identities):
            raise ValueError("decision-requirements identity or blocked boundary drifted")
        orders = (
            tuple(x.candidate_group_code for x in self.candidate_group_bindings)
            == tuple(x[0] for x in c.PHASE21_CANDIDATE_GROUP_ROWS),
            tuple(x.product_code for x in self.product_rights_bindings)
            == tuple(x[0] for x in c.PHASE21_PRODUCT_RIGHTS_ROWS),
            tuple(x.capability_code for x in self.capability_assignments)
            == tuple(x[0] for x in c.PHASE21_CAPABILITY_ROWS),
            tuple(x.field_name for x in self.decision_fields)
            == tuple(x[0] for x in c.PHASE21_DECISION_FIELD_ROWS),
            tuple(x.code for x in self.post_selection_dependencies)
            == tuple(x[0] for x in c.PHASE21_POST_SELECTION_DEPENDENCY_ROWS),
            tuple(x.code for x in self.decision_gates) == tuple(x[0] for x in c.PHASE21_GATE_ROWS),
            tuple(x.code for x in self.future_rules)
            == tuple(x[0] for x in c.PHASE21_FUTURE_RULE_ROWS),
            tuple(x.code for x in self.forbidden_substitutes)
            == tuple(x[0] for x in c.PHASE21_FORBIDDEN_SUBSTITUTE_ROWS),
            tuple(x.code for x in self.inherited_phase20_input_requirements)
            == tuple(x[1] for x in c.PHASE20_INPUT_REQUIREMENT_ROWS),
            tuple(x.name for x in self.required_prior_evidence)
            == tuple(x[0] for x in c.PHASE20_FUTURE_EVIDENCE_ROWS),
            tuple(x.code for x in self.phase15_gap_bindings) == c.PHASE20_GAP_CODES,
            tuple(x.code for x in self.source_plan_steps) == c.PHASE20_STEP_CODES,
        )
        if not all(orders):
            raise ValueError("decision-requirements registry or order drifted")
        manifests = (
            self.candidate_groups_manifest_sha256
            == candidate_groups_manifest_sha256(self.candidate_group_bindings),
            self.product_rights_bindings_manifest_sha256
            == product_rights_manifest_sha256(self.product_rights_bindings),
            self.capability_assignments_manifest_sha256
            == capabilities_manifest_sha256(self.capability_assignments),
            self.decision_fields_manifest_sha256
            == decision_fields_manifest_sha256(self.decision_fields),
            self.post_selection_dependencies_manifest_sha256
            == dependencies_manifest_sha256(self.post_selection_dependencies),
            self.decision_gates_manifest_sha256 == gates_manifest_sha256(self.decision_gates),
            self.future_rules_manifest_sha256 == rules_manifest_sha256(self.future_rules),
            self.forbidden_substitutes_manifest_sha256
            == substitutes_manifest_sha256(self.forbidden_substitutes),
            self.inherited_phase20_inputs_manifest_sha256
            == inputs_manifest_sha256(self.inherited_phase20_input_requirements),
            self.required_prior_evidence_manifest_sha256
            == evidence_manifest_sha256(self.required_prior_evidence),
            self.phase15_gap_bindings_manifest_sha256
            == gaps_manifest_sha256(self.phase15_gap_bindings),
            self.source_plan_steps_manifest_sha256 == steps_manifest_sha256(self.source_plan_steps),
        )
        if not all(manifests):
            raise ValueError("decision-requirements manifest mismatch")
        rendered = self.model_dump(mode="python")
        if any(
            rendered[field] is not expected for field, expected in c.PHASE21_BOUNDARY_VALUES.items()
        ):
            raise ValueError("decision-requirements authority boundary drifted")
        if any(x.value_present or x.evidence_produced for x in self.decision_fields):
            raise ValueError("decision fields cannot carry values or evidence")
        if any(x.operationally_selected or x.ranked for x in self.candidate_group_bindings):
            raise ValueError("candidate groups must remain unselected and unranked")
        if any(
            x.operationally_selected or x.current_rights_verified
            for x in self.product_rights_bindings
        ):
            raise ValueError("product rights must remain unselected and unverified")
        if any(
            x.assignment_state is not CapabilityAssignmentState.UNASSIGNED
            or x.assignment_value_present
            for x in self.capability_assignments
        ):
            raise ValueError("capabilities must remain unassigned")
        if any(
            x.applied or not x.future_only or x.external_action_authorized
            for x in self.future_rules
        ):
            raise ValueError("future rules must remain future-only and unapplied")
        if any(not x.forbidden for x in self.forbidden_substitutes):
            raise ValueError("substitute registry must remain fail-closed")
        preimage = self.model_dump(mode="python", exclude={"artifact_sha256"})
        if self.artifact_sha256 != c.domain_sha256(c.PHASE21_ARTIFACT_HASH_DOMAIN, preimage):
            raise ValueError("decision-requirements artifact hash mismatch")
        return self


__all__ = [
    "FamilyACandidateGroupBinding",
    "FamilyACapabilityAssignment",
    "FamilyACompositionDecisionGate",
    "FamilyADecisionFieldRequirement",
    "FamilyAForbiddenSubstitute",
    "FamilyAFutureCompositionRule",
    "FamilyAInheritedPhase20Input",
    "FamilyAOperationalCompositionDecisionRequirements",
    "FamilyAPhase15GapBinding",
    "FamilyAPostSelectionDependency",
    "FamilyAProductRightsBinding",
    "FamilyARequiredPriorEvidenceBinding",
    "FamilyASourcePlanStepBinding",
    "RequirementsConclusion",
    "RequirementsOutcome",
    "RequirementsState",
    "candidate_groups_manifest_sha256",
    "capabilities_manifest_sha256",
    "decision_fields_manifest_sha256",
    "dependencies_manifest_sha256",
    "evidence_manifest_sha256",
    "gaps_manifest_sha256",
    "gates_manifest_sha256",
    "inputs_manifest_sha256",
    "product_rights_manifest_sha256",
    "rules_manifest_sha256",
    "steps_manifest_sha256",
    "substitutes_manifest_sha256",
]
