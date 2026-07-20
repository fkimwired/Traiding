"""Strict portable contracts for the Phase 20 evaluation/holdout input register."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from fable5_data.phase20 import canonical as c

SHA256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
GitSHA = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]
Identifier = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]{0,127}$")]
ClosedText = Annotated[str, StringConstraints(min_length=1, max_length=2000)]
FrozenTimestamp = Annotated[
    str,
    StringConstraints(pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{7}Z$"),
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")


class RegisterOutcome(StrEnum):
    BLOCKED = "BLOCKED"


class RegisterState(StrEnum):
    INPUTS_FROZEN = "INPUTS_FROZEN"


class RegisterConclusion(StrEnum):
    BLOCKED_MISSING_OPERATIONAL_AND_DATA_SPECIFIC_INPUTS = (
        "BLOCKED_MISSING_OPERATIONAL_AND_DATA_SPECIFIC_INPUTS"
    )


class EvidenceState(StrEnum):
    PRESENT = "PRESENT"
    MOCK_ONLY = "MOCK_ONLY"
    STALE = "STALE"
    MISSING = "MISSING"
    UNPROVEN = "UNPROVEN"


class InheritedPrerequisiteCategory(StrEnum):
    EVALUATION_POLICY = "EVALUATION_POLICY"
    CONFIRMATION_HOLDOUT = "CONFIRMATION_HOLDOUT"


class InheritedPrerequisiteCode(StrEnum):
    OPERATIONAL_SOURCE_PRODUCT_COMPOSITION = "OPERATIONAL_SOURCE_PRODUCT_COMPOSITION"
    CURRENT_EXECUTED_USE_RIGHTS_AND_REVOCATION = "CURRENT_EXECUTED_USE_RIGHTS_AND_REVOCATION"
    EXACT_DELIVERY_AND_SCHEMA_VERSIONS = "EXACT_DELIVERY_AND_SCHEMA_VERSIONS"
    FULL_POINT_IN_TIME_COVERAGE_AND_MISSINGNESS = "FULL_POINT_IN_TIME_COVERAGE_AND_MISSINGNESS"
    SIGNAL_ACTION_LABEL_AND_HORIZON = "SIGNAL_ACTION_LABEL_AND_HORIZON"
    DECISION_CALENDAR_SAMPLE_BOUNDARIES_AND_ADEQUACY = (
        "DECISION_CALENDAR_SAMPLE_BOUNDARIES_AND_ADEQUACY"
    )
    PURGED_WALK_FORWARD_MECHANICS = "PURGED_WALK_FORWARD_MECHANICS"
    EMBARGO_APPLICABILITY = "EMBARGO_APPLICABILITY"
    COMPLETE_TRIAL_ACCOUNTING_DSR_PBO_POLICY = "COMPLETE_TRIAL_ACCOUNTING_DSR_PBO_POLICY"
    LEAKAGE_AND_DATA_QUALITY_GATES = "LEAKAGE_AND_DATA_QUALITY_GATES"
    MARKET_CALIBRATED_COST_SLIPPAGE_CAPACITY = "MARKET_CALIBRATED_COST_SLIPPAGE_CAPACITY"
    STRESS_REGIME_CRISIS_THRESHOLDS = "STRESS_REGIME_CRISIS_THRESHOLDS"
    COMPUTABLE_DATA_SPECIFIC_RISK_LIMITS = "COMPUTABLE_DATA_SPECIFIC_RISK_LIMITS"
    REPRODUCIBILITY_AUDIT_SCHEMA = "REPRODUCIBILITY_AUDIT_SCHEMA"
    NON_SYNTHETIC_EVALUATION_POLICY = "NON_SYNTHETIC_EVALUATION_POLICY"
    SOURCE_BOUND_CONTIGUOUS_CONFIRMATION_INTERVAL = "SOURCE_BOUND_CONTIGUOUS_CONFIRMATION_INTERVAL"
    HOLDOUT_DECISION_CALENDAR_AND_LABEL_BOUNDARIES = (
        "HOLDOUT_DECISION_CALENDAR_AND_LABEL_BOUNDARIES"
    )
    HOLDOUT_EXCLUSION_CONSUMPTION_AND_REPLACEMENT_RULES = (
        "HOLDOUT_EXCLUSION_CONSUMPTION_AND_REPLACEMENT_RULES"
    )
    UNTOUCHED_CONFIRMATION_HOLDOUT_DEFINITION = "UNTOUCHED_CONFIRMATION_HOLDOUT_DEFINITION"


INHERITED_PREREQUISITE_ORDER = tuple(InheritedPrerequisiteCode)


class InputCategory(StrEnum):
    UPSTREAM_CONTEXT = "UPSTREAM_CONTEXT"
    EVALUATION_POLICY_INPUT = "EVALUATION_POLICY_INPUT"
    CONFIRMATION_HOLDOUT_INPUT = "CONFIRMATION_HOLDOUT_INPUT"
    APPROVAL_INPUT = "APPROVAL_INPUT"


class InputRequirementCode(StrEnum):
    OPERATIONAL_SOURCE_PRODUCT_COMPOSITION = "OPERATIONAL_SOURCE_PRODUCT_COMPOSITION"
    CURRENT_EXECUTED_USE_RIGHTS_AND_REVOCATION = "CURRENT_EXECUTED_USE_RIGHTS_AND_REVOCATION"
    EXACT_DELIVERY_AND_SCHEMA_VERSIONS = "EXACT_DELIVERY_AND_SCHEMA_VERSIONS"
    DECLARED_PIT_COVERAGE_CALENDAR_AVAILABILITY_MISSINGNESS = (
        "DECLARED_PIT_COVERAGE_CALENDAR_AVAILABILITY_MISSINGNESS"
    )
    SIGNAL_ACTION_LABEL_AND_HORIZON = "SIGNAL_ACTION_LABEL_AND_HORIZON"
    FEATURE_LINEAGE_LOOKBACK_AND_PREPROCESSING = "FEATURE_LINEAGE_LOOKBACK_AND_PREPROCESSING"
    WALK_FORWARD_FOLD_GEOMETRY_AND_PURGE = "WALK_FORWARD_FOLD_GEOMETRY_AND_PURGE"
    EMBARGO_APPLICABILITY_AND_DURATION = "EMBARGO_APPLICABILITY_AND_DURATION"
    SAMPLE_ADEQUACY_AND_RETURN_HANDLING = "SAMPLE_ADEQUACY_AND_RETURN_HANDLING"
    TRIAL_ACCOUNTING_DSR_PBO_SELECTION = "TRIAL_ACCOUNTING_DSR_PBO_SELECTION"
    LEAKAGE_AND_DATA_QUALITY_BLOCKS = "LEAKAGE_AND_DATA_QUALITY_BLOCKS"
    MARKET_CALIBRATED_COST_SLIPPAGE_CAPACITY = "MARKET_CALIBRATED_COST_SLIPPAGE_CAPACITY"
    STRESS_VECTOR_AND_PROMOTION_GATES = "STRESS_VECTOR_AND_PROMOTION_GATES"
    REGIME_AND_CRISIS_DEFINITIONS = "REGIME_AND_CRISIS_DEFINITIONS"
    COMPUTABLE_DATA_SPECIFIC_RISK_LIMITS = "COMPUTABLE_DATA_SPECIFIC_RISK_LIMITS"
    REPRODUCIBILITY_AUDIT_SCHEMA = "REPRODUCIBILITY_AUDIT_SCHEMA"
    SOURCE_BOUND_CONTIGUOUS_INTERVAL = "SOURCE_BOUND_CONTIGUOUS_INTERVAL"
    DECISION_CALENDAR_LABEL_BOUNDARY_AND_EXCLUSIONS = (
        "DECISION_CALENDAR_LABEL_BOUNDARY_AND_EXCLUSIONS"
    )
    LABEL_BLIND_CONSUMPTION_REPLACEMENT_GOVERNANCE = (
        "LABEL_BLIND_CONSUMPTION_REPLACEMENT_GOVERNANCE"
    )
    INDEPENDENT_POLICY_AND_HOLDOUT_APPROVAL_RECORD = (
        "INDEPENDENT_POLICY_AND_HOLDOUT_APPROVAL_RECORD"
    )


INPUT_REQUIREMENT_ORDER = tuple(InputRequirementCode)


class RequiredEvidenceName(StrEnum):
    NON_SYNTHETIC_EVALUATION_POLICY_SHA256 = "non_synthetic_evaluation_policy_sha256"
    CONFIRMATION_HOLDOUT_DEFINITION_SHA256 = "confirmation_holdout_definition_sha256"


REQUIRED_EVIDENCE_ORDER = tuple(RequiredEvidenceName)


class TransitionRuleCode(StrEnum):
    NO_PLAN_OR_ARTIFACT_HASH_UPGRADE = "NO_PLAN_OR_ARTIFACT_HASH_UPGRADE"
    MOCK_ONLY_TO_PRESENT_REQUIRES_APPROVED_NON_SYNTHETIC_EVIDENCE = (
        "MOCK_ONLY_TO_PRESENT_REQUIRES_APPROVED_NON_SYNTHETIC_EVIDENCE"
    )
    MISSING_TO_PRESENT_REQUIRES_COMPLETE_REQUIRED_EVIDENCE = (
        "MISSING_TO_PRESENT_REQUIRES_COMPLETE_REQUIRED_EVIDENCE"
    )
    UNPROVEN_TO_PRESENT_REQUIRES_INDEPENDENT_VERIFICATION = (
        "UNPROVEN_TO_PRESENT_REQUIRES_INDEPENDENT_VERIFICATION"
    )
    STALE_TO_PRESENT_REQUIRES_FRESH_REVALIDATION = "STALE_TO_PRESENT_REQUIRES_FRESH_REVALIDATION"
    PRESENT_TO_STALE_ON_CURRENTNESS_OR_VERSION_DRIFT = (
        "PRESENT_TO_STALE_ON_CURRENTNESS_OR_VERSION_DRIFT"
    )
    HOLDOUT_DEFINITION_REQUIRES_SOURCE_CALENDAR_BINDING_AND_ZERO_OBSERVATION_LABEL_ACCESS = (
        "HOLDOUT_DEFINITION_REQUIRES_SOURCE_CALENDAR_BINDING_AND_ZERO_OBSERVATION_LABEL_ACCESS"
    )
    POLICY_COMPLETION_REQUIRES_ALL_POLICY_INPUTS_AND_UNOPENED_HOLDOUT_REFERENCE = (
        "POLICY_COMPLETION_REQUIRES_ALL_POLICY_INPUTS_AND_UNOPENED_HOLDOUT_REFERENCE"
    )
    STEP3_REQUIRES_BOTH_RESERVED_HASHES_AND_SEPARATE_EXTERNAL_ACTION_AUTHORITY = (
        "STEP3_REQUIRES_BOTH_RESERVED_HASHES_AND_SEPARATE_EXTERNAL_ACTION_AUTHORITY"
    )
    LATER_SOURCE_PLAN_STEPS_CANNOT_SKIP_OR_IMPLY_PREDECESSORS = (
        "LATER_SOURCE_PLAN_STEPS_CANNOT_SKIP_OR_IMPLY_PREDECESSORS"
    )


TRANSITION_RULE_ORDER = tuple(TransitionRuleCode)


class DependencyGroupCode(StrEnum):
    OPERATIONAL_COMPOSITION_AND_RIGHTS = "OPERATIONAL_COMPOSITION_AND_RIGHTS"
    SOURCE_COVERAGE_AND_CALENDAR = "SOURCE_COVERAGE_AND_CALENDAR"
    EVALUATION_METHODOLOGY = "EVALUATION_METHODOLOGY"
    COST_STRESS_REGIME_AND_RISK = "COST_STRESS_REGIME_AND_RISK"
    AUDIT_AND_HOLDOUT_GOVERNANCE = "AUDIT_AND_HOLDOUT_GOVERNANCE"
    INDEPENDENT_JOINT_APPROVAL = "INDEPENDENT_JOINT_APPROVAL"


DEPENDENCY_GROUP_ORDER = tuple(DependencyGroupCode)


class ConstructionGateCode(StrEnum):
    OPERATIONAL_COMPOSITION_CURRENT_RIGHTS_GATE = "OPERATIONAL_COMPOSITION_CURRENT_RIGHTS_GATE"
    SOURCE_COVERAGE_CALENDAR_GATE = "SOURCE_COVERAGE_CALENDAR_GATE"
    NON_SYNTHETIC_METHODOLOGY_GATE = "NON_SYNTHETIC_METHODOLOGY_GATE"
    MARKET_CALIBRATION_STRESS_RISK_GATE = "MARKET_CALIBRATION_STRESS_RISK_GATE"
    UNTOUCHED_HOLDOUT_GOVERNANCE_GATE = "UNTOUCHED_HOLDOUT_GOVERNANCE_GATE"
    INDEPENDENT_JOINT_APPROVAL_GATE = "INDEPENDENT_JOINT_APPROVAL_GATE"


CONSTRUCTION_GATE_ORDER = tuple(ConstructionGateCode)


class BlockedState(StrEnum):
    BLOCKED = "BLOCKED"


class ForbiddenSubstituteCode(StrEnum):
    PHASE15_REQUIREMENTS_HASH = "PHASE15_REQUIREMENTS_HASH"
    PHASE19_ASSESSMENT_HASH = "PHASE19_ASSESSMENT_HASH"
    SYNTHETIC_POLICY_OR_RESULT_HASH = "SYNTHETIC_POLICY_OR_RESULT_HASH"
    PUBLIC_DOCUMENTATION_OR_RIGHTS_REVIEW_HASH = "PUBLIC_DOCUMENTATION_OR_RIGHTS_REVIEW_HASH"
    CANDIDATE_INVENTORY_HASH = "CANDIDATE_INVENTORY_HASH"
    PROTOCOL_OR_TEMPLATE_HASH = "PROTOCOL_OR_TEMPLATE_HASH"
    PLACEHOLDER_OR_ALL_ZERO_HASH = "PLACEHOLDER_OR_ALL_ZERO_HASH"
    OPERATOR_OVERRIDE_OR_ARBITRARY_HASH = "OPERATOR_OVERRIDE_OR_ARBITRARY_HASH"


FORBIDDEN_SUBSTITUTE_ORDER = tuple(ForbiddenSubstituteCode)


class TargetOutputClass(StrEnum):
    EVALUATION_POLICY_OUTPUT = "EVALUATION_POLICY_OUTPUT"
    CONFIRMATION_HOLDOUT_OUTPUT = "CONFIRMATION_HOLDOUT_OUTPUT"


class Phase15GapCode(StrEnum):
    FAMILY_A_SIGNAL_AND_HORIZON = "FAMILY_A_SIGNAL_AND_HORIZON"
    FULL_POINT_IN_TIME_DATASET = "FULL_POINT_IN_TIME_DATASET"
    EXTERNAL_CANDIDATE_QUALIFICATION = "EXTERNAL_CANDIDATE_QUALIFICATION"
    HISTORICAL_MEMBERSHIP_AND_DELISTING = "HISTORICAL_MEMBERSHIP_AND_DELISTING"
    SECTOR_LIQUIDITY_MACRO_HISTORY = "SECTOR_LIQUIDITY_MACRO_HISTORY"
    INDEPENDENT_CURRENT_USE_RIGHTS = "INDEPENDENT_CURRENT_USE_RIGHTS"
    NON_SYNTHETIC_SNAPSHOT_PERSISTENCE = "NON_SYNTHETIC_SNAPSHOT_PERSISTENCE"
    NON_SYNTHETIC_EVALUATION_POLICY = "NON_SYNTHETIC_EVALUATION_POLICY"
    NON_SYNTHETIC_EVALUATION_PATH = "NON_SYNTHETIC_EVALUATION_PATH"
    PURGED_WALK_FORWARD_MECHANICS = "PURGED_WALK_FORWARD_MECHANICS"
    EMBARGO_APPLICABILITY_DECISION = "EMBARGO_APPLICABILITY_DECISION"
    LEAKAGE_FREE_RESULT = "LEAKAGE_FREE_RESULT"
    MARKET_CALIBRATED_COST_SLIPPAGE = "MARKET_CALIBRATED_COST_SLIPPAGE"
    DSR_PBO_PROMOTION_GATES = "DSR_PBO_PROMOTION_GATES"
    PHASE_15_IMPLEMENTATION_AUTHORITY = "PHASE_15_IMPLEMENTATION_AUTHORITY"
    DATA_RIGHTS_AND_RESEARCH_AUTHORITY = "DATA_RIGHTS_AND_RESEARCH_AUTHORITY"
    RIGHTS_CURRENTNESS_REVOCATION = "RIGHTS_CURRENTNESS_REVOCATION"
    PRE_ORDER_RISK = "PRE_ORDER_RISK"
    IMMUTABLE_AUDIT_SCHEMA = "IMMUTABLE_AUDIT_SCHEMA"


PHASE15_GAP_ORDER = tuple(Phase15GapCode)


class SourcePlanStepCode(StrEnum):
    SELECT_CANDIDATE_PRODUCTS = "SELECT_CANDIDATE_PRODUCTS"
    REVIEW_CURRENT_USE_RIGHTS = "REVIEW_CURRENT_USE_RIGHTS"
    QUALIFY_BOUNDED_READ_ONLY_SAMPLES = "QUALIFY_BOUNDED_READ_ONLY_SAMPLES"
    PRODUCE_FULL_HISTORY_COVERAGE_MANIFEST = "PRODUCE_FULL_HISTORY_COVERAGE_MANIFEST"
    RECONCILE_TEMPORAL_IDENTITY_REVISION_SEMANTICS = (
        "RECONCILE_TEMPORAL_IDENTITY_REVISION_SEMANTICS"
    )
    DESIGN_LOCAL_QUARANTINE_AND_CANONICAL_SNAPSHOT = (
        "DESIGN_LOCAL_QUARANTINE_AND_CANONICAL_SNAPSHOT"
    )
    REQUEST_SEPARATE_INGESTION_AUTHORITY = "REQUEST_SEPARATE_INGESTION_AUTHORITY"


SOURCE_PLAN_STEP_ORDER = tuple(SourcePlanStepCode)


class SourcePlanStepState(StrEnum):
    OUTPUT_FROZEN = "OUTPUT_FROZEN"
    NOT_STARTED = "NOT_STARTED"


class FamilyAInheritedPhase19Prerequisite(StrictModel):
    schema_version: str
    ordinal: Annotated[int, Field(ge=1, le=19)]
    category: InheritedPrerequisiteCategory
    code: InheritedPrerequisiteCode
    evidence_state: EvidenceState
    requirement_satisfied: bool
    inherited_phase19_prerequisite_sha256: SHA256
    unchanged: bool
    binding_sha256: SHA256

    @model_validator(mode="after")
    def validate_binding(self) -> Self:
        row = c.PHASE20_INHERITED_PREREQUISITE_ROWS[self.ordinal - 1]
        expected = {
            "schema_version": c.PHASE20_INHERITED_PREREQUISITE_SCHEMA_VERSION,
            "ordinal": self.ordinal,
            "category": row[0],
            "code": row[1],
            "evidence_state": row[2],
            "requirement_satisfied": row[3],
            "inherited_phase19_prerequisite_sha256": row[4],
            "unchanged": True,
        }
        if c.canonicalize(self.model_dump(exclude={"binding_sha256"})) != c.canonicalize(expected):
            raise ValueError("inherited Phase 19 prerequisite drifted")
        if self.binding_sha256 != c.domain_sha256(
            c.PHASE20_INHERITED_PREREQUISITE_HASH_DOMAIN, expected
        ):
            raise ValueError("inherited prerequisite binding hash mismatch")
        return self


class FamilyAEvaluationHoldoutInputRequirement(StrictModel):
    schema_version: str
    ordinal: Annotated[int, Field(ge=1, le=20)]
    category: InputCategory
    code: InputRequirementCode
    definition: ClosedText
    evidence_state: EvidenceState
    requirement_satisfied: bool
    required_field_names: tuple[Identifier, ...]
    related_phase19_prerequisite_codes: Annotated[
        tuple[InheritedPrerequisiteCode, ...], Field(min_length=1)
    ]
    related_phase15_gap_codes: Annotated[tuple[Phase15GapCode, ...], Field(min_length=1)]
    input_value_present: bool
    resolves_reserved_evidence: bool
    reason_code: Identifier
    requirement_sha256: SHA256

    @model_validator(mode="after")
    def validate_requirement(self) -> Self:
        row = c.PHASE20_INPUT_REQUIREMENT_ROWS[self.ordinal - 1]
        expected = {
            "schema_version": c.PHASE20_INPUT_REQUIREMENT_SCHEMA_VERSION,
            "ordinal": self.ordinal,
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
        if c.canonicalize(self.model_dump(exclude={"requirement_sha256"})) != c.canonicalize(
            expected
        ):
            raise ValueError("input requirement drifted")
        if len(set(self.required_field_names)) != len(self.required_field_names):
            raise ValueError("input requirement field names must be unique")
        if not self.related_phase19_prerequisite_codes or not self.related_phase15_gap_codes:
            raise ValueError("input requirement relations must be nonempty")
        if self.requirement_sha256 != c.domain_sha256(
            c.PHASE20_INPUT_REQUIREMENT_HASH_DOMAIN, expected
        ):
            raise ValueError("input requirement hash mismatch")
        return self


class FamilyAMissingRequiredPriorEvidence(StrictModel):
    schema_version: str
    ordinal: Annotated[int, Field(ge=1, le=2)]
    name: RequiredEvidenceName
    state: EvidenceState
    produced: bool
    reason_code: Identifier
    record_sha256: SHA256

    @model_validator(mode="after")
    def validate_missing(self) -> Self:
        row = c.PHASE20_FUTURE_EVIDENCE_ROWS[self.ordinal - 1]
        expected = {
            "schema_version": c.PHASE20_FUTURE_EVIDENCE_SCHEMA_VERSION,
            "ordinal": self.ordinal,
            "name": row[0],
            "state": row[1],
            "produced": row[2],
            "reason_code": row[3],
        }
        if c.canonicalize(self.model_dump(exclude={"record_sha256"})) != c.canonicalize(expected):
            raise ValueError("required prior evidence drifted")
        if self.record_sha256 != c.domain_sha256(c.PHASE20_FUTURE_EVIDENCE_HASH_DOMAIN, expected):
            raise ValueError("required prior-evidence hash mismatch")
        return self


class FamilyAFutureEvidenceTransitionRule(StrictModel):
    schema_version: str
    ordinal: Annotated[int, Field(ge=1, le=10)]
    code: TransitionRuleCode
    definition: ClosedText
    reason_code: Identifier
    future_only: bool
    applied: bool
    external_action_authorized: bool
    rule_sha256: SHA256

    @model_validator(mode="after")
    def validate_rule(self) -> Self:
        row = c.PHASE20_TRANSITION_RULE_ROWS[self.ordinal - 1]
        expected = {
            "schema_version": c.PHASE20_TRANSITION_RULE_SCHEMA_VERSION,
            "ordinal": self.ordinal,
            "code": row[0],
            "definition": row[1],
            "reason_code": row[2],
            "future_only": True,
            "applied": False,
            "external_action_authorized": False,
        }
        if c.canonicalize(self.model_dump(exclude={"rule_sha256"})) != c.canonicalize(expected):
            raise ValueError("future transition rule drifted")
        if self.rule_sha256 != c.domain_sha256(c.PHASE20_TRANSITION_RULE_HASH_DOMAIN, expected):
            raise ValueError("transition rule hash mismatch")
        return self


class FamilyAConstructionDependencyGroup(StrictModel):
    schema_version: str
    ordinal: Annotated[int, Field(ge=1, le=6)]
    code: DependencyGroupCode
    definition: ClosedText
    input_codes: tuple[InputRequirementCode, ...]
    prerequisite_group_codes: tuple[DependencyGroupCode, ...]
    state: BlockedState
    reason_code: Identifier
    group_sha256: SHA256

    @model_validator(mode="after")
    def validate_group(self) -> Self:
        row = c.PHASE20_DEPENDENCY_GROUP_ROWS[self.ordinal - 1]
        expected = {
            "schema_version": c.PHASE20_DEPENDENCY_GROUP_SCHEMA_VERSION,
            "ordinal": self.ordinal,
            "code": row[0],
            "definition": row[1],
            "input_codes": row[2],
            "prerequisite_group_codes": row[3],
            "state": row[4],
            "reason_code": row[5],
        }
        if c.canonicalize(self.model_dump(exclude={"group_sha256"})) != c.canonicalize(expected):
            raise ValueError("dependency group drifted")
        if self.group_sha256 != c.domain_sha256(c.PHASE20_DEPENDENCY_GROUP_HASH_DOMAIN, expected):
            raise ValueError("dependency group hash mismatch")
        return self


class FamilyAConstructionGate(StrictModel):
    schema_version: str
    ordinal: Annotated[int, Field(ge=1, le=6)]
    code: ConstructionGateCode
    definition: ClosedText
    required_group_codes: tuple[DependencyGroupCode, ...]
    state: BlockedState
    passed: bool
    required_before_observation: bool
    reason_code: Identifier
    gate_sha256: SHA256

    @model_validator(mode="after")
    def validate_gate(self) -> Self:
        row = c.PHASE20_CONSTRUCTION_GATE_ROWS[self.ordinal - 1]
        expected = {
            "schema_version": c.PHASE20_CONSTRUCTION_GATE_SCHEMA_VERSION,
            "ordinal": self.ordinal,
            "code": row[0],
            "definition": row[1],
            "required_group_codes": row[2],
            "state": row[3],
            "passed": row[4],
            "required_before_observation": row[5],
            "reason_code": row[6],
        }
        if c.canonicalize(self.model_dump(exclude={"gate_sha256"})) != c.canonicalize(expected):
            raise ValueError("construction gate drifted")
        if self.gate_sha256 != c.domain_sha256(c.PHASE20_CONSTRUCTION_GATE_HASH_DOMAIN, expected):
            raise ValueError("construction gate hash mismatch")
        return self


class FamilyAForbiddenSubstitute(StrictModel):
    schema_version: str
    ordinal: Annotated[int, Field(ge=1, le=8)]
    code: ForbiddenSubstituteCode
    definition: ClosedText
    target_output_classes: tuple[TargetOutputClass, ...]
    forbidden: bool
    reason_code: Identifier
    substitute_sha256: SHA256

    @model_validator(mode="after")
    def validate_substitute(self) -> Self:
        row = c.PHASE20_FORBIDDEN_SUBSTITUTE_ROWS[self.ordinal - 1]
        expected = {
            "schema_version": c.PHASE20_FORBIDDEN_SUBSTITUTE_SCHEMA_VERSION,
            "ordinal": self.ordinal,
            "code": row[0],
            "definition": row[1],
            "target_output_classes": row[2],
            "forbidden": row[3],
            "reason_code": row[4],
        }
        if c.canonicalize(self.model_dump(exclude={"substitute_sha256"})) != c.canonicalize(
            expected
        ):
            raise ValueError("forbidden substitute drifted")
        if self.substitute_sha256 != c.domain_sha256(
            c.PHASE20_FORBIDDEN_SUBSTITUTE_HASH_DOMAIN, expected
        ):
            raise ValueError("forbidden substitute hash mismatch")
        return self


class FamilyAPhase15GapBinding(StrictModel):
    schema_version: str
    ordinal: Annotated[int, Field(ge=1, le=19)]
    code: Phase15GapCode
    state: EvidenceState
    source_gap_sha256: SHA256
    inherited_phase19_binding_sha256: SHA256
    changed_in_phase20: bool
    binding_sha256: SHA256

    @model_validator(mode="after")
    def validate_gap(self) -> Self:
        index = self.ordinal - 1
        expected = {
            "schema_version": c.PHASE20_GAP_BINDING_SCHEMA_VERSION,
            "ordinal": self.ordinal,
            "code": c.PHASE20_GAP_CODES[index],
            "state": c.PHASE20_GAP_STATES[index],
            "source_gap_sha256": c.PHASE20_SOURCE_GAP_SHA256S[index],
            "inherited_phase19_binding_sha256": c.PHASE20_PHASE19_GAP_BINDING_SHA256S[index],
            "changed_in_phase20": False,
        }
        if c.canonicalize(self.model_dump(exclude={"binding_sha256"})) != c.canonicalize(expected):
            raise ValueError("Phase 15 gap binding drifted")
        if self.binding_sha256 != c.domain_sha256(c.PHASE20_GAP_BINDING_HASH_DOMAIN, expected):
            raise ValueError("Phase 15 gap binding hash mismatch")
        return self


class FamilyASourcePlanStepBinding(StrictModel):
    schema_version: str
    ordinal: Annotated[int, Field(ge=1, le=7)]
    code: SourcePlanStepCode
    state: SourcePlanStepState
    inherited_reason_code: Identifier
    inherited_phase19_step_sha256: SHA256
    changed_in_phase20: bool
    external_action_authorized: bool
    binding_sha256: SHA256

    @model_validator(mode="after")
    def validate_step(self) -> Self:
        index = self.ordinal - 1
        expected = {
            "schema_version": c.PHASE20_STEP_BINDING_SCHEMA_VERSION,
            "ordinal": self.ordinal,
            "code": c.PHASE20_STEP_CODES[index],
            "state": c.PHASE20_STEP_STATES[index],
            "inherited_reason_code": c.PHASE20_STEP_REASONS[index],
            "inherited_phase19_step_sha256": c.PHASE20_PHASE19_STEP_SHA256S[index],
            "changed_in_phase20": False,
            "external_action_authorized": False,
        }
        if c.canonicalize(self.model_dump(exclude={"binding_sha256"})) != c.canonicalize(expected):
            raise ValueError("source-plan step binding drifted")
        if self.binding_sha256 != c.domain_sha256(c.PHASE20_STEP_BINDING_HASH_DOMAIN, expected):
            raise ValueError("source-plan step binding hash mismatch")
        return self


def _manifest(domain: str, values: tuple[str, ...]) -> str:
    return c.domain_sha256(domain, values)


def inherited_prerequisites_manifest_sha256(
    rows: tuple[FamilyAInheritedPhase19Prerequisite, ...],
) -> str:
    return _manifest(
        c.PHASE20_INHERITED_PREREQUISITES_MANIFEST_HASH_DOMAIN,
        tuple(x.binding_sha256 for x in rows),
    )


def input_requirements_manifest_sha256(
    rows: tuple[FamilyAEvaluationHoldoutInputRequirement, ...],
) -> str:
    return _manifest(
        c.PHASE20_INPUT_REQUIREMENTS_MANIFEST_HASH_DOMAIN, tuple(x.requirement_sha256 for x in rows)
    )


def required_evidence_manifest_sha256(
    rows: tuple[FamilyAMissingRequiredPriorEvidence, ...],
) -> str:
    return _manifest(
        c.PHASE20_FUTURE_EVIDENCE_MANIFEST_HASH_DOMAIN, tuple(x.record_sha256 for x in rows)
    )


def transition_rules_manifest_sha256(
    rows: tuple[FamilyAFutureEvidenceTransitionRule, ...],
) -> str:
    return _manifest(
        c.PHASE20_TRANSITION_RULES_MANIFEST_HASH_DOMAIN, tuple(x.rule_sha256 for x in rows)
    )


def dependency_groups_manifest_sha256(
    rows: tuple[FamilyAConstructionDependencyGroup, ...],
) -> str:
    return _manifest(
        c.PHASE20_DEPENDENCY_GROUPS_MANIFEST_HASH_DOMAIN, tuple(x.group_sha256 for x in rows)
    )


def construction_gates_manifest_sha256(rows: tuple[FamilyAConstructionGate, ...]) -> str:
    return _manifest(
        c.PHASE20_CONSTRUCTION_GATES_MANIFEST_HASH_DOMAIN, tuple(x.gate_sha256 for x in rows)
    )


def forbidden_substitutes_manifest_sha256(
    rows: tuple[FamilyAForbiddenSubstitute, ...],
) -> str:
    return _manifest(
        c.PHASE20_FORBIDDEN_SUBSTITUTES_MANIFEST_HASH_DOMAIN,
        tuple(x.substitute_sha256 for x in rows),
    )


def gap_bindings_manifest_sha256(rows: tuple[FamilyAPhase15GapBinding, ...]) -> str:
    return _manifest(
        c.PHASE20_GAP_BINDINGS_MANIFEST_HASH_DOMAIN, tuple(x.binding_sha256 for x in rows)
    )


def step_bindings_manifest_sha256(rows: tuple[FamilyASourcePlanStepBinding, ...]) -> str:
    return _manifest(
        c.PHASE20_STEP_BINDINGS_MANIFEST_HASH_DOMAIN, tuple(x.binding_sha256 for x in rows)
    )


class FamilyAEvaluationHoldoutInputRegister(StrictModel):
    schema_version: str
    artifact_id: UUID
    artifact_sha256: SHA256
    input_register_policy_id: str
    input_register_policy_sha256: SHA256
    accepted_phase19_commit_sha: GitSHA
    accepted_phase19_tree_sha: GitSHA
    phase19_artifact_id: UUID
    phase19_artifact_sha256: SHA256
    phase19_policy_sha256: SHA256
    phase19_prerequisites_manifest_sha256: SHA256
    phase19_required_evidence_manifest_sha256: SHA256
    phase19_gap_bindings_manifest_sha256: SHA256
    phase19_steps_manifest_sha256: SHA256
    phase19_aggregate_conclusion: str
    phase15_gaps_manifest_sha256: SHA256
    family: str
    frozen_at_utc: FrozenTimestamp
    outcome: RegisterOutcome
    register_state: RegisterState
    aggregate_conclusion: RegisterConclusion
    block_reason: ClosedText
    inherited_phase19_prerequisites_manifest_sha256: SHA256
    input_requirements_manifest_sha256: SHA256
    required_prior_evidence_manifest_sha256: SHA256
    transition_rules_manifest_sha256: SHA256
    construction_dependency_groups_manifest_sha256: SHA256
    construction_gates_manifest_sha256: SHA256
    forbidden_substitutes_manifest_sha256: SHA256
    phase15_gap_bindings_manifest_sha256: SHA256
    source_plan_steps_manifest_sha256: SHA256
    inherited_phase19_prerequisites: tuple[FamilyAInheritedPhase19Prerequisite, ...]
    input_requirements: tuple[FamilyAEvaluationHoldoutInputRequirement, ...]
    required_prior_evidence: tuple[FamilyAMissingRequiredPriorEvidence, ...]
    transition_rules: tuple[FamilyAFutureEvidenceTransitionRule, ...]
    construction_dependency_groups: tuple[FamilyAConstructionDependencyGroup, ...]
    construction_gates: tuple[FamilyAConstructionGate, ...]
    forbidden_substitutes: tuple[FamilyAForbiddenSubstitute, ...]
    phase15_gap_bindings: tuple[FamilyAPhase15GapBinding, ...]
    source_plan_steps: tuple[FamilyASourcePlanStepBinding, ...]
    metadata_only: bool
    requirements_only: bool
    input_register_only: bool
    runtime_network_disabled: bool
    phase19_prerequisites_unchanged: bool
    inherited_phase15_gaps_unchanged: bool
    source_plan_steps_unchanged: bool
    revalidation_required_before_external_action: bool
    provider_selected: bool
    product_selected: bool
    source_selected: bool
    operational_source_product_composition_selected: bool
    credentials_loaded: bool
    account_verified: bool
    subscription_verified: bool
    entitlement_verified: bool
    executed_license_reviewed: bool
    rights_currentness_guaranteed: bool
    rights_verified: bool
    rights_granted: bool
    operational_use_cleared: bool
    legal_opinion_obtained: bool
    independent_legal_counsel_reviewed: bool
    provider_or_counsel_attestation_obtained: bool
    delivery_proven: bool
    schema_proven: bool
    coverage_proven: bool
    fitness_verified: bool
    current_availability_proven: bool
    operational_external_request_performed: bool
    provider_data_request_performed: bool
    provider_account_verification_performed: bool
    entitlement_verification_performed: bool
    external_sample_qualification_authorized: bool
    external_sample_qualified: bool
    external_data_capture_authorized: bool
    provider_payload_persisted: bool
    licensed_data_persisted: bool
    research_ingestion_authorized: bool
    research_snapshot_created: bool
    research_data_eligible: bool
    non_synthetic_evaluation_policy_created: bool
    non_synthetic_evaluation_policy_approved: bool
    evaluation_policy_approved: bool
    confirmation_holdout_definition_created: bool
    confirmation_holdout_defined: bool
    confirmation_holdout_opened: bool
    confirmation_holdout_consumed: bool
    step3_required_prior_evidence_complete: bool
    step3_eligible: bool
    step3_external_action_authorized: bool
    research_run_created: bool
    research_run_authorized: bool
    research_executed: bool
    performance_computed: bool
    pass_research_granted: bool
    strategy_promotion_authorized: bool
    paper_approval_granted: bool
    risk_clearance_granted: bool
    strategy_execution_eligible: bool
    execution_authorized: bool
    order_submission_authorized: bool
    live_path_absent: bool
    no_personalized_investment_advice: bool
    no_real_performance_claimed: bool
    disclaimer: ClosedText

    @model_validator(mode="after")
    def validate_register(self) -> Self:
        identity_checks = (
            self.schema_version == c.PHASE20_ARTIFACT_SCHEMA_VERSION,
            self.artifact_id == c.identity(c.PHASE20_REGISTER_POLICY_SHA256),
            self.input_register_policy_id == c.PHASE20_INPUT_REGISTER_POLICY_ID,
            self.input_register_policy_sha256 == c.PHASE20_REGISTER_POLICY_SHA256,
            self.accepted_phase19_commit_sha == c.PHASE20_ACCEPTED_PHASE19_COMMIT_SHA,
            self.accepted_phase19_tree_sha == c.PHASE20_ACCEPTED_PHASE19_TREE_SHA,
            str(self.phase19_artifact_id) == c.PHASE20_PHASE19_ARTIFACT_ID,
            self.phase19_artifact_sha256 == c.PHASE20_PHASE19_ARTIFACT_SHA256,
            self.phase19_policy_sha256 == c.PHASE20_PHASE19_POLICY_SHA256,
            self.phase19_prerequisites_manifest_sha256
            == c.PHASE20_PHASE19_PREREQUISITES_MANIFEST_SHA256,
            self.phase19_required_evidence_manifest_sha256
            == c.PHASE20_PHASE19_REQUIRED_EVIDENCE_MANIFEST_SHA256,
            self.phase19_gap_bindings_manifest_sha256
            == c.PHASE20_PHASE19_GAP_BINDINGS_MANIFEST_SHA256,
            self.phase19_steps_manifest_sha256 == c.PHASE20_PHASE19_STEPS_MANIFEST_SHA256,
            self.phase19_aggregate_conclusion == c.PHASE20_PHASE19_AGGREGATE_CONCLUSION,
            self.phase15_gaps_manifest_sha256 == c.PHASE20_PHASE15_GAPS_MANIFEST_SHA256,
            self.family == c.PHASE20_FAMILY,
            self.frozen_at_utc == c.PHASE20_FROZEN_AT_UTC,
            self.outcome.value == c.PHASE20_OUTCOME,
            self.register_state.value == c.PHASE20_REGISTER_STATE,
            self.aggregate_conclusion.value == c.PHASE20_AGGREGATE_CONCLUSION,
            self.block_reason == c.PHASE20_BLOCK_REASON,
            self.disclaimer == c.PHASE20_DISCLAIMER,
        )
        if not all(identity_checks):
            raise ValueError("input-register identity or blocked boundary drifted")
        ordered = (
            tuple(x.code for x in self.inherited_phase19_prerequisites)
            == INHERITED_PREREQUISITE_ORDER,
            tuple(x.code for x in self.input_requirements) == INPUT_REQUIREMENT_ORDER,
            tuple(x.name for x in self.required_prior_evidence) == REQUIRED_EVIDENCE_ORDER,
            tuple(x.code for x in self.transition_rules) == TRANSITION_RULE_ORDER,
            tuple(x.code for x in self.construction_dependency_groups) == DEPENDENCY_GROUP_ORDER,
            tuple(x.code for x in self.construction_gates) == CONSTRUCTION_GATE_ORDER,
            tuple(x.code for x in self.forbidden_substitutes) == FORBIDDEN_SUBSTITUTE_ORDER,
            tuple(x.code for x in self.phase15_gap_bindings) == PHASE15_GAP_ORDER,
            tuple(x.code for x in self.source_plan_steps) == SOURCE_PLAN_STEP_ORDER,
        )
        if not all(ordered):
            raise ValueError("input-register registry or order drifted")
        manifests = (
            self.inherited_phase19_prerequisites_manifest_sha256
            == inherited_prerequisites_manifest_sha256(self.inherited_phase19_prerequisites),
            self.input_requirements_manifest_sha256
            == input_requirements_manifest_sha256(self.input_requirements),
            self.required_prior_evidence_manifest_sha256
            == required_evidence_manifest_sha256(self.required_prior_evidence),
            self.transition_rules_manifest_sha256
            == transition_rules_manifest_sha256(self.transition_rules),
            self.construction_dependency_groups_manifest_sha256
            == dependency_groups_manifest_sha256(self.construction_dependency_groups),
            self.construction_gates_manifest_sha256
            == construction_gates_manifest_sha256(self.construction_gates),
            self.forbidden_substitutes_manifest_sha256
            == forbidden_substitutes_manifest_sha256(self.forbidden_substitutes),
            self.phase15_gap_bindings_manifest_sha256
            == gap_bindings_manifest_sha256(self.phase15_gap_bindings),
            self.source_plan_steps_manifest_sha256
            == step_bindings_manifest_sha256(self.source_plan_steps),
        )
        if not all(manifests):
            raise ValueError("input-register manifest mismatch")
        if any(
            x.input_value_present or x.resolves_reserved_evidence for x in self.input_requirements
        ):
            raise ValueError("input register cannot contain values or resolve reserved evidence")
        if tuple(x.requirement_satisfied for x in self.input_requirements) != (
            *(False for _ in range(15)),
            True,
            False,
            False,
            False,
            False,
        ):
            raise ValueError("only the inherited audit-schema requirement may be satisfied")
        if any(
            x.produced or x.state is not EvidenceState.MISSING for x in self.required_prior_evidence
        ):
            raise ValueError("required prior evidence must remain missing and unproduced")
        if any(
            x.applied or not x.future_only or x.external_action_authorized
            for x in self.transition_rules
        ):
            raise ValueError("transition rules must remain future-only and unapplied")
        if any(x.state is not BlockedState.BLOCKED for x in self.construction_dependency_groups):
            raise ValueError("construction dependency groups must remain blocked")
        if any(x.state is not BlockedState.BLOCKED or x.passed for x in self.construction_gates):
            raise ValueError("construction gates must remain blocked")
        if any(not x.forbidden for x in self.forbidden_substitutes):
            raise ValueError("substitute registry must remain fail-closed")
        rendered = self.model_dump(mode="python")
        for field, expected in c.PHASE20_BOUNDARY_VALUES.items():
            if rendered[field] is not expected:
                raise ValueError(f"input register unexpectedly changed {field}")
        preimage = self.model_dump(mode="python", exclude={"artifact_sha256"})
        if self.artifact_sha256 != c.domain_sha256(c.PHASE20_ARTIFACT_HASH_DOMAIN, preimage):
            raise ValueError("input-register artifact hash mismatch")
        return self


__all__ = [
    "FamilyAConstructionDependencyGroup",
    "FamilyAConstructionGate",
    "FamilyAEvaluationHoldoutInputRegister",
    "FamilyAEvaluationHoldoutInputRequirement",
    "FamilyAForbiddenSubstitute",
    "FamilyAFutureEvidenceTransitionRule",
    "FamilyAInheritedPhase19Prerequisite",
    "FamilyAMissingRequiredPriorEvidence",
    "FamilyAPhase15GapBinding",
    "FamilyASourcePlanStepBinding",
    "RegisterConclusion",
    "RegisterOutcome",
    "RegisterState",
    "construction_gates_manifest_sha256",
    "dependency_groups_manifest_sha256",
    "forbidden_substitutes_manifest_sha256",
    "gap_bindings_manifest_sha256",
    "inherited_prerequisites_manifest_sha256",
    "input_requirements_manifest_sha256",
    "required_evidence_manifest_sha256",
    "step_bindings_manifest_sha256",
    "transition_rules_manifest_sha256",
]
