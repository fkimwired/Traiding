"""Strict portable contracts for the Phase 19 Step-3 prerequisite assessment."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

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
    PHASE19_GAPS_MANIFEST_HASH_DOMAIN,
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
    PHASE19_PREREQUISITES_MANIFEST_HASH_DOMAIN,
    PHASE19_REQUIRED_EVIDENCE_HASH_DOMAIN,
    PHASE19_REQUIRED_EVIDENCE_MANIFEST_HASH_DOMAIN,
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
    PHASE19_STEPS_MANIFEST_HASH_DOMAIN,
    canonicalize,
    domain_sha256,
    identity,
)

SHA256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
GitSHA = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]
ClosedText = Annotated[str, StringConstraints(min_length=1, max_length=1200)]
Identifier = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]{0,127}$")]
FrozenTimestamp = Annotated[
    str,
    StringConstraints(pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{7}Z$"),
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")


class FamilyAStep3AssessmentOutcome(StrEnum):
    BLOCKED = "BLOCKED"


class FamilyAStep3AssessmentState(StrEnum):
    OUTPUT_FROZEN = "OUTPUT_FROZEN"


class FamilyAStep3Conclusion(StrEnum):
    BLOCKED_MISSING_EVALUATION_POLICY_AND_HOLDOUT = "BLOCKED_MISSING_EVALUATION_POLICY_AND_HOLDOUT"


class EvidenceState(StrEnum):
    PRESENT = "PRESENT"
    MOCK_ONLY = "MOCK_ONLY"
    STALE = "STALE"
    MISSING = "MISSING"
    UNPROVEN = "UNPROVEN"


class RequiredEvidenceState(StrEnum):
    MISSING = "MISSING"


class PrerequisiteCategory(StrEnum):
    EVALUATION_POLICY = "EVALUATION_POLICY"
    CONFIRMATION_HOLDOUT = "CONFIRMATION_HOLDOUT"


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


PHASE19_GAP_ORDER = tuple(Phase15GapCode)


class PrerequisiteCode(StrEnum):
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


PHASE19_PREREQUISITE_ORDER = tuple(PrerequisiteCode)


class RequiredEvidenceName(StrEnum):
    NON_SYNTHETIC_EVALUATION_POLICY_SHA256 = "non_synthetic_evaluation_policy_sha256"
    CONFIRMATION_HOLDOUT_DEFINITION_SHA256 = "confirmation_holdout_definition_sha256"


PHASE19_REQUIRED_EVIDENCE_ORDER = tuple(RequiredEvidenceName)


class FamilyASourcePlanStepCode(StrEnum):
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


PHASE19_STEP_ORDER = tuple(FamilyASourcePlanStepCode)


class FamilyASourcePlanStepState(StrEnum):
    OUTPUT_FROZEN = "OUTPUT_FROZEN"
    NOT_STARTED = "NOT_STARTED"


class FamilyASourcePlanStepReason(StrEnum):
    INVENTORY_OUTPUT_INHERITED_AND_FROZEN = "inventory_output_inherited_and_frozen"
    BLOCKING_RIGHTS_REVIEW_OUTPUTS_INHERITED_NO_OPERATIONAL_CLEARANCE = (
        "blocking_rights_review_outputs_inherited_no_operational_clearance"
    )
    REQUIRED_PRIOR_EVIDENCE_MISSING = "required_prior_evidence_missing"
    PREREQUISITE_NOT_SATISFIED = "prerequisite_not_satisfied"


class FamilyAStep3Prerequisite(StrictModel):
    schema_version: str
    ordinal: Annotated[int, Field(ge=1, le=19)]
    category: PrerequisiteCategory
    code: PrerequisiteCode
    definition: ClosedText
    evidence_state: EvidenceState
    requirement_satisfied: bool
    reason_code: Identifier
    related_phase15_gap_codes: tuple[Phase15GapCode, ...]
    prerequisite_sha256: SHA256

    @model_validator(mode="after")
    def validate_frozen_prerequisite(self) -> Self:
        row = PHASE19_PREREQUISITE_ROWS[self.ordinal - 1]
        expected_payload = {
            "schema_version": PHASE19_PREREQUISITE_SCHEMA_VERSION,
            "ordinal": self.ordinal,
            "category": row[0],
            "code": row[1],
            "definition": row[2],
            "evidence_state": row[3],
            "requirement_satisfied": row[4],
            "reason_code": row[5],
            "related_phase15_gap_codes": row[6],
        }
        actual = self.model_dump(mode="python", exclude={"prerequisite_sha256"})
        if canonicalize(actual) != canonicalize(expected_payload):
            raise ValueError("Step-3 prerequisite drifted from the frozen assessment")
        if self.prerequisite_sha256 != domain_sha256(
            PHASE19_PREREQUISITE_HASH_DOMAIN,
            expected_payload,
        ):
            raise ValueError("Step-3 prerequisite hash mismatch")
        return self


class FamilyARequiredPriorEvidence(StrictModel):
    schema_version: str
    ordinal: Annotated[int, Field(ge=1, le=2)]
    name: RequiredEvidenceName
    state: RequiredEvidenceState
    produced: bool
    reason_code: Identifier
    record_sha256: SHA256

    @model_validator(mode="after")
    def validate_missing_evidence(self) -> Self:
        row = PHASE19_REQUIRED_EVIDENCE_ROWS[self.ordinal - 1]
        expected_payload = {
            "schema_version": PHASE19_REQUIRED_EVIDENCE_SCHEMA_VERSION,
            "ordinal": self.ordinal,
            "name": row[0],
            "state": row[1],
            "produced": row[2],
            "reason_code": row[3],
        }
        actual = self.model_dump(mode="python", exclude={"record_sha256"})
        if canonicalize(actual) != canonicalize(expected_payload):
            raise ValueError("required prior-evidence status drifted")
        if self.record_sha256 != domain_sha256(
            PHASE19_REQUIRED_EVIDENCE_HASH_DOMAIN,
            expected_payload,
        ):
            raise ValueError("required prior-evidence record hash mismatch")
        return self


class FamilyAPhase15GapBinding(StrictModel):
    schema_version: str
    ordinal: Annotated[int, Field(ge=1, le=19)]
    code: Phase15GapCode
    state: EvidenceState
    source_gap_sha256: SHA256
    binding_sha256: SHA256

    @model_validator(mode="after")
    def validate_unchanged_gap(self) -> Self:
        index = self.ordinal - 1
        expected_payload = {
            "schema_version": PHASE19_GAP_BINDING_SCHEMA_VERSION,
            "ordinal": self.ordinal,
            "code": PHASE19_GAP_CODES[index],
            "state": PHASE19_GAP_STATES[index],
            "source_gap_sha256": PHASE19_SOURCE_GAP_SHA256S[index],
        }
        actual = self.model_dump(mode="python", exclude={"binding_sha256"})
        if canonicalize(actual) != canonicalize(expected_payload):
            raise ValueError("inherited Phase 15 gap drifted")
        if self.binding_sha256 != domain_sha256(
            PHASE19_GAP_BINDING_HASH_DOMAIN,
            expected_payload,
        ):
            raise ValueError("Phase 15 gap binding hash mismatch")
        return self


class FamilyASourcePlanOutput(StrictModel):
    schema_version: str
    name: Identifier
    sha256: SHA256
    output_sha256: SHA256

    @model_validator(mode="after")
    def validate_output_hash(self) -> Self:
        payload = self.model_dump(mode="python", exclude={"output_sha256"})
        if self.schema_version != PHASE19_OUTPUT_SCHEMA_VERSION:
            raise ValueError("source-plan output schema mismatch")
        if self.output_sha256 != domain_sha256(PHASE19_OUTPUT_HASH_DOMAIN, payload):
            raise ValueError("source-plan output hash mismatch")
        return self


class FamilyASourcePlanStepEvidence(StrictModel):
    schema_version: str
    ordinal: Annotated[int, Field(ge=1, le=7)]
    code: FamilyASourcePlanStepCode
    state: FamilyASourcePlanStepState
    reason_code: FamilyASourcePlanStepReason
    prerequisite_codes: tuple[FamilyASourcePlanStepCode, ...]
    required_prior_evidence: tuple[RequiredEvidenceName, ...]
    required_outputs: tuple[Identifier, ...]
    produced_outputs: tuple[FamilyASourcePlanOutput, ...]
    external_action_authorized: bool
    step_sha256: SHA256

    @model_validator(mode="after")
    def validate_frozen_step(self) -> Self:
        index = self.ordinal - 1
        expected_payload = {
            "schema_version": PHASE19_STEP_SCHEMA_VERSION,
            "ordinal": self.ordinal,
            "code": PHASE19_STEP_CODES[index],
            "state": PHASE19_STEP_STATES[index],
            "reason_code": PHASE19_STEP_REASONS[index],
            "prerequisite_codes": PHASE19_STEP_PREREQUISITES[index],
            "required_prior_evidence": PHASE19_STEP_REQUIRED_PRIOR_EVIDENCE[index],
            "required_outputs": PHASE19_STEP_REQUIRED_OUTPUTS[index],
            "produced_outputs": self.produced_outputs,
            "external_action_authorized": False,
        }
        names = tuple(item.name for item in self.produced_outputs)
        if index == 0 and names != ("candidate_product_inventory_sha256",):
            raise ValueError("Step 1 must retain the inherited inventory output")
        if index == 1 and names != (
            "independent_rights_review_sha256",
            "rights_currentness_sha256",
        ):
            raise ValueError("Step 2 must retain the blocked rights-review outputs")
        if index > 1 and self.produced_outputs:
            raise ValueError("Steps 3-7 cannot contain produced output evidence")
        actual = self.model_dump(mode="python", exclude={"step_sha256"})
        if canonicalize(actual) != canonicalize(expected_payload):
            raise ValueError("source-plan step evidence drifted")
        if self.step_sha256 != domain_sha256(PHASE19_STEP_HASH_DOMAIN, expected_payload):
            raise ValueError("source-plan step hash mismatch")
        return self


def prerequisites_manifest_sha256(
    prerequisites: tuple[FamilyAStep3Prerequisite, ...],
) -> str:
    return domain_sha256(
        PHASE19_PREREQUISITES_MANIFEST_HASH_DOMAIN,
        tuple(item.prerequisite_sha256 for item in prerequisites),
    )


def required_evidence_manifest_sha256(
    required_evidence: tuple[FamilyARequiredPriorEvidence, ...],
) -> str:
    return domain_sha256(
        PHASE19_REQUIRED_EVIDENCE_MANIFEST_HASH_DOMAIN,
        tuple(item.record_sha256 for item in required_evidence),
    )


def gap_bindings_manifest_sha256(gaps: tuple[FamilyAPhase15GapBinding, ...]) -> str:
    return domain_sha256(
        PHASE19_GAPS_MANIFEST_HASH_DOMAIN,
        tuple(item.binding_sha256 for item in gaps),
    )


def steps_manifest_sha256(steps: tuple[FamilyASourcePlanStepEvidence, ...]) -> str:
    return domain_sha256(
        PHASE19_STEPS_MANIFEST_HASH_DOMAIN,
        tuple(item.step_sha256 for item in steps),
    )


class FamilyAStep3PrerequisiteAssessment(StrictModel):
    schema_version: str
    artifact_id: UUID
    artifact_sha256: SHA256
    assessment_policy_id: str
    assessment_policy_sha256: SHA256
    accepted_phase18_commit_sha: GitSHA
    accepted_phase18_tree_sha: GitSHA
    phase18_artifact_id: UUID
    phase18_artifact_sha256: SHA256
    phase18_policy_sha256: SHA256
    phase18_independent_rights_review_sha256: SHA256
    phase18_rights_currentness_sha256: SHA256
    phase18_steps_manifest_sha256: SHA256
    phase18_aggregate_conclusion: str
    phase16_original_step3_sha256: SHA256
    phase18_inherited_step3_evidence_sha256: SHA256
    phase15_gaps_manifest_sha256: SHA256
    phase6_specification_id: str
    phase6_specification_version: str
    phase6_specification_sha256: SHA256
    family: str
    frozen_at_utc: FrozenTimestamp
    outcome: FamilyAStep3AssessmentOutcome
    assessment_state: FamilyAStep3AssessmentState
    aggregate_conclusion: FamilyAStep3Conclusion
    block_reason: ClosedText
    prerequisites_manifest_sha256: SHA256
    required_prior_evidence_manifest_sha256: SHA256
    phase15_gap_bindings_manifest_sha256: SHA256
    steps_manifest_sha256: SHA256
    prerequisites: tuple[FamilyAStep3Prerequisite, ...]
    required_prior_evidence: tuple[FamilyARequiredPriorEvidence, ...]
    phase15_gap_bindings: tuple[FamilyAPhase15GapBinding, ...]
    source_plan_steps: tuple[FamilyASourcePlanStepEvidence, ...]
    metadata_only: bool
    requirements_only: bool
    runtime_network_disabled: bool
    revalidation_required_before_external_action: bool
    inherited_phase15_gaps_unchanged: bool
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
    def validate_closed_assessment(self) -> Self:
        identity_values = (
            self.schema_version == PHASE19_ARTIFACT_SCHEMA_VERSION,
            self.artifact_id == identity(PHASE19_ASSESSMENT_POLICY_SHA256),
            self.assessment_policy_id == PHASE19_ASSESSMENT_POLICY_ID,
            self.assessment_policy_sha256 == PHASE19_ASSESSMENT_POLICY_SHA256,
            self.accepted_phase18_commit_sha == PHASE19_ACCEPTED_PHASE18_COMMIT_SHA,
            self.accepted_phase18_tree_sha == PHASE19_ACCEPTED_PHASE18_TREE_SHA,
            str(self.phase18_artifact_id) == PHASE19_PHASE18_ARTIFACT_ID,
            self.phase18_artifact_sha256 == PHASE19_PHASE18_ARTIFACT_SHA256,
            self.phase18_policy_sha256 == PHASE19_PHASE18_POLICY_SHA256,
            self.phase18_independent_rights_review_sha256
            == PHASE19_PHASE18_INDEPENDENT_RIGHTS_REVIEW_SHA256,
            self.phase18_rights_currentness_sha256 == PHASE19_PHASE18_RIGHTS_CURRENTNESS_SHA256,
            self.phase18_steps_manifest_sha256 == PHASE19_PHASE18_STEPS_MANIFEST_SHA256,
            self.phase18_aggregate_conclusion == "BLOCKED_NO_OPERATIONAL_SELECTION",
            self.phase16_original_step3_sha256 == PHASE19_PHASE16_ORIGINAL_STEP3_SHA256,
            self.phase18_inherited_step3_evidence_sha256
            == PHASE19_PHASE18_INHERITED_STEP3_EVIDENCE_SHA256,
            self.phase16_original_step3_sha256 != self.phase18_inherited_step3_evidence_sha256,
            self.phase15_gaps_manifest_sha256 == PHASE19_PHASE15_GAPS_MANIFEST_SHA256,
            self.phase6_specification_id == PHASE19_PHASE6_SPECIFICATION_ID,
            self.phase6_specification_version == PHASE19_PHASE6_SPECIFICATION_VERSION,
            self.phase6_specification_sha256 == PHASE19_PHASE6_SPECIFICATION_SHA256,
            self.family == PHASE19_FAMILY,
            self.frozen_at_utc == PHASE19_FROZEN_AT_UTC,
            self.outcome.value == PHASE19_OUTCOME,
            self.assessment_state.value == PHASE19_ASSESSMENT_STATE,
            self.aggregate_conclusion.value == PHASE19_AGGREGATE_CONCLUSION,
            self.block_reason == PHASE19_BLOCK_REASON,
            self.disclaimer == PHASE19_DISCLAIMER,
        )
        if not all(identity_values):
            raise ValueError("Step-3 assessment identity or blocked boundary drifted")
        if tuple(item.code for item in self.prerequisites) != PHASE19_PREREQUISITE_ORDER:
            raise ValueError("Step-3 prerequisite registry or order drifted")
        if (
            tuple(item.name for item in self.required_prior_evidence)
            != PHASE19_REQUIRED_EVIDENCE_ORDER
        ):
            raise ValueError("required prior-evidence registry or order drifted")
        if tuple(item.code for item in self.phase15_gap_bindings) != PHASE19_GAP_ORDER:
            raise ValueError("inherited Phase 15 gap registry or order drifted")
        if tuple(item.code for item in self.source_plan_steps) != PHASE19_STEP_ORDER:
            raise ValueError("source-plan step registry or order drifted")
        if self.prerequisites_manifest_sha256 != prerequisites_manifest_sha256(self.prerequisites):
            raise ValueError("Step-3 prerequisites manifest mismatch")
        if self.required_prior_evidence_manifest_sha256 != required_evidence_manifest_sha256(
            self.required_prior_evidence
        ):
            raise ValueError("required prior-evidence manifest mismatch")
        if self.phase15_gap_bindings_manifest_sha256 != gap_bindings_manifest_sha256(
            self.phase15_gap_bindings
        ):
            raise ValueError("Phase 15 gap-bindings manifest mismatch")
        if self.steps_manifest_sha256 != steps_manifest_sha256(self.source_plan_steps):
            raise ValueError("source-plan steps manifest mismatch")
        if any(
            item.produced or item.state is not RequiredEvidenceState.MISSING
            for item in self.required_prior_evidence
        ):
            raise ValueError("required prior evidence must remain missing and unproduced")
        first_outputs = self.source_plan_steps[0].produced_outputs
        second_outputs = self.source_plan_steps[1].produced_outputs
        if len(first_outputs) != 1 or first_outputs[0].sha256 != PHASE19_PHASE18_INVENTORY_SHA256:
            raise ValueError("Step 1 no longer binds the accepted inventory")
        if len(second_outputs) != 2 or tuple(item.sha256 for item in second_outputs) != (
            PHASE19_PHASE18_INDEPENDENT_RIGHTS_REVIEW_SHA256,
            PHASE19_PHASE18_RIGHTS_CURRENTNESS_SHA256,
        ):
            raise ValueError("Step 2 no longer binds the blocked Phase 18 outputs")
        if any(item.produced_outputs for item in self.source_plan_steps[2:]):
            raise ValueError("Steps 3-7 unexpectedly produced output evidence")
        rendered = self.model_dump(mode="python")
        for field, expected in PHASE19_BOUNDARY_VALUES.items():
            if rendered[field] is not expected:
                raise ValueError(f"Step-3 assessment unexpectedly changed {field}")
        preimage = self.model_dump(mode="python", exclude={"artifact_sha256"})
        if self.artifact_sha256 != domain_sha256(PHASE19_ARTIFACT_HASH_DOMAIN, preimage):
            raise ValueError("Step-3 prerequisite-assessment artifact hash mismatch")
        return self


__all__ = [
    "PHASE19_GAP_ORDER",
    "PHASE19_PREREQUISITE_ORDER",
    "PHASE19_REQUIRED_EVIDENCE_ORDER",
    "PHASE19_STEP_ORDER",
    "EvidenceState",
    "FamilyAPhase15GapBinding",
    "FamilyARequiredPriorEvidence",
    "FamilyASourcePlanOutput",
    "FamilyASourcePlanStepCode",
    "FamilyASourcePlanStepEvidence",
    "FamilyASourcePlanStepReason",
    "FamilyASourcePlanStepState",
    "FamilyAStep3AssessmentOutcome",
    "FamilyAStep3AssessmentState",
    "FamilyAStep3Conclusion",
    "FamilyAStep3Prerequisite",
    "FamilyAStep3PrerequisiteAssessment",
    "Phase15GapCode",
    "PrerequisiteCategory",
    "PrerequisiteCode",
    "RequiredEvidenceName",
    "RequiredEvidenceState",
    "gap_bindings_manifest_sha256",
    "prerequisites_manifest_sha256",
    "required_evidence_manifest_sha256",
    "steps_manifest_sha256",
]
