"""Strict portable contracts for the Phase 16 Family A source plan."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from fable5_data.phase16.canonical import (
    PHASE16_ACCEPTED_PHASE15_COMMIT_SHA,
    PHASE16_ACCEPTED_PHASE15_TREE_SHA,
    PHASE16_ARTIFACT_HASH_DOMAIN,
    PHASE16_ARTIFACT_SCHEMA_VERSION,
    PHASE16_BOUNDARY_VALUES,
    PHASE16_CANDIDATE_HASH_DOMAIN,
    PHASE16_CANDIDATE_SCHEMA_VERSION,
    PHASE16_CANDIDATE_STATES,
    PHASE16_CANDIDATES_MANIFEST_HASH_DOMAIN,
    PHASE16_CAPABILITIES_MANIFEST_HASH_DOMAIN,
    PHASE16_CAPABILITY_HASH_DOMAIN,
    PHASE16_CAPABILITY_SCHEMA_VERSION,
    PHASE16_DISCLAIMER,
    PHASE16_FAMILY,
    PHASE16_FROZEN_AT_UTC,
    PHASE16_GAP_BINDING_HASH_DOMAIN,
    PHASE16_GAP_BINDING_SCHEMA_VERSION,
    PHASE16_GAPS_MANIFEST_HASH_DOMAIN,
    PHASE16_PHASE6_SPECIFICATION_ID,
    PHASE16_PHASE6_SPECIFICATION_SHA256,
    PHASE16_PHASE6_SPECIFICATION_VERSION,
    PHASE16_PHASE15_ARTIFACT_ID,
    PHASE16_PHASE15_ARTIFACT_SHA256,
    PHASE16_PHASE15_GAP_SHA256S,
    PHASE16_PHASE15_GAP_STATES,
    PHASE16_PHASE15_GAPS_MANIFEST_SHA256,
    PHASE16_PHASE15_POLICY_SHA256,
    PHASE16_PHASE15_REQUIREMENTS_MANIFEST_SHA256,
    PHASE16_POLICY_ID,
    PHASE16_POLICY_SHA256,
    PHASE16_REQUIREMENT_DEFINITIONS,
    PHASE16_REQUIREMENT_HASH_DOMAIN,
    PHASE16_REQUIREMENT_SCHEMA_VERSION,
    PHASE16_REQUIREMENTS_MANIFEST_HASH_DOMAIN,
    PHASE16_STEP_DEFINITIONS,
    PHASE16_STEP_HASH_DOMAIN,
    PHASE16_STEP_PREREQUISITES,
    PHASE16_STEP_REQUIRED_OUTPUTS,
    PHASE16_STEP_REQUIRED_PRIOR_EVIDENCE,
    PHASE16_STEP_SCHEMA_VERSION,
    PHASE16_STEPS_MANIFEST_HASH_DOMAIN,
    domain_sha256,
    identity,
)

SHA256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
GitSHA = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]
ClosedText = Annotated[str, StringConstraints(min_length=1, max_length=700)]
Identifier = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]{0,127}$")]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")


class FamilyASourcePlanOutcome(StrEnum):
    PLAN_FROZEN = "PLAN_FROZEN"
    BLOCKED = "BLOCKED"


class FamilyASourcePlanRequirementStatus(StrEnum):
    PASS = "PASS"
    BLOCKED = "BLOCKED"
    UNCOMPUTABLE = "UNCOMPUTABLE"


class FamilyASourcePlanRequirementReason(StrEnum):
    FROZEN_SOURCE_PLAN_REQUIREMENT = "frozen_source_plan_requirement"
    REQUIREMENT_BLOCKED = "requirement_blocked"
    REQUIREMENT_UNCOMPUTABLE = "requirement_uncomputable"


class FamilyASourcePlanRequirementCode(StrEnum):
    PHASE15_ADMISSION_SPECIFICATION_BOUND = "PHASE15_ADMISSION_SPECIFICATION_BOUND"
    FAMILY_A_CAPABILITY_SET_BOUND = "FAMILY_A_CAPABILITY_SET_BOUND"
    SECURITY_MASTER_IDENTITY_HISTORY_REQUIRED = "SECURITY_MASTER_IDENTITY_HISTORY_REQUIRED"
    UNIVERSE_MEMBERSHIP_DELISTING_HISTORY_REQUIRED = (
        "UNIVERSE_MEMBERSHIP_DELISTING_HISTORY_REQUIRED"
    )
    RAW_OHLCV_CORPORATE_ACTION_HISTORY_REQUIRED = "RAW_OHLCV_CORPORATE_ACTION_HISTORY_REQUIRED"
    AS_REPORTED_FUNDAMENTAL_VINTAGES_REQUIRED = "AS_REPORTED_FUNDAMENTAL_VINTAGES_REQUIRED"
    SECTOR_LIQUIDITY_HISTORY_REQUIRED = "SECTOR_LIQUIDITY_HISTORY_REQUIRED"
    MACRO_VINTAGE_RELEASE_HISTORY_REQUIRED = "MACRO_VINTAGE_RELEASE_HISTORY_REQUIRED"
    TEMPORAL_REVISION_COVERAGE_MANIFEST_REQUIRED = "TEMPORAL_REVISION_COVERAGE_MANIFEST_REQUIRED"
    INDEPENDENT_RIGHTS_CURRENTNESS_REVIEW_REQUIRED = (
        "INDEPENDENT_RIGHTS_CURRENTNESS_REVIEW_REQUIRED"
    )
    QUARANTINE_CANONICALIZATION_RECONCILIATION_REQUIRED = (
        "QUARANTINE_CANONICALIZATION_RECONCILIATION_REQUIRED"
    )
    CAPTURE_INGESTION_RESEARCH_EXECUTION_AUTHORITY_ABSENT = (
        "CAPTURE_INGESTION_RESEARCH_EXECUTION_AUTHORITY_ABSENT"
    )


PHASE16_REQUIREMENT_ORDER = tuple(FamilyASourcePlanRequirementCode)


class FamilyASourceCapabilityCode(StrEnum):
    SECURITY_MASTER = "security_master"
    UNIVERSE_MEMBERSHIP = "universe_membership"
    OHLCV = "ohlcv"
    CORPORATE_ACTIONS = "corporate_actions"
    DELISTINGS = "delistings"
    AS_REPORTED_FUNDAMENTALS = "as_reported_fundamentals"
    MACRO_REGIME_INPUTS = "macro_regime_inputs"


PHASE16_CAPABILITY_ORDER = tuple(FamilyASourceCapabilityCode)


class FamilyASourceCandidateCode(StrEnum):
    TIINGO_PHASE13_BOUNDED_CANDIDATE = "TIINGO_PHASE13_BOUNDED_CANDIDATE"
    MORNINGSTAR_CRSP_US_STOCK_DATABASES_CANDIDATE = "MORNINGSTAR_CRSP_US_STOCK_DATABASES_CANDIDATE"
    MORNINGSTAR_CRSP_COMPUSTAT_MERGED_DATABASE_CANDIDATE = (
        "MORNINGSTAR_CRSP_COMPUSTAT_MERGED_DATABASE_CANDIDATE"
    )
    SEC_EDGAR_SUBMISSIONS_XBRL_CANDIDATE = "SEC_EDGAR_SUBMISSIONS_XBRL_CANDIDATE"
    FEDERAL_RESERVE_ALFRED_VINTAGES_CANDIDATE = "FEDERAL_RESERVE_ALFRED_VINTAGES_CANDIDATE"
    HISTORICAL_LIQUIDITY_PRODUCT_UNSELECTED = "HISTORICAL_LIQUIDITY_PRODUCT_UNSELECTED"


class FamilyASourceCandidateState(StrEnum):
    UNPROVEN = "UNPROVEN"
    MISSING = "MISSING"


PHASE16_CANDIDATE_ORDER = tuple(FamilyASourceCandidateCode)
PHASE16_EXPECTED_CANDIDATE_STATES = tuple(
    FamilyASourceCandidateState(value) for value in PHASE16_CANDIDATE_STATES
)


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


PHASE16_STEP_ORDER = tuple(FamilyASourcePlanStepCode)


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


class Phase15GapState(StrEnum):
    PRESENT = "PRESENT"
    MOCK_ONLY = "MOCK_ONLY"
    STALE = "STALE"
    MISSING = "MISSING"
    UNPROVEN = "UNPROVEN"


PHASE16_GAP_ORDER = tuple(Phase15GapCode)
PHASE16_EXPECTED_GAP_STATES = tuple(Phase15GapState(value) for value in PHASE16_PHASE15_GAP_STATES)


class FamilyASourcePlanRequirement(StrictModel):
    schema_version: Literal["phase16-family-a-point-in-time-source-plan-requirement-v1"] = (
        PHASE16_REQUIREMENT_SCHEMA_VERSION
    )
    ordinal: int = Field(ge=1, le=12)
    code: FamilyASourcePlanRequirementCode
    definition: ClosedText
    status: FamilyASourcePlanRequirementStatus
    reason_code: FamilyASourcePlanRequirementReason
    evidence_sha256s: tuple[SHA256, ...]
    requirement_sha256: SHA256

    @model_validator(mode="after")
    def validate_requirement(self) -> Self:
        if self.ordinal != PHASE16_REQUIREMENT_ORDER.index(self.code) + 1:
            raise ValueError("requirement ordinal must match the frozen registry")
        if self.definition != PHASE16_REQUIREMENT_DEFINITIONS[self.ordinal - 1]:
            raise ValueError("requirement definition must match the frozen registry")
        if (
            tuple(sorted(set(self.evidence_sha256s))) != self.evidence_sha256s
            or not self.evidence_sha256s
        ):
            raise ValueError("requirement evidence hashes must be nonempty, unique, and sorted")
        expected_reason = {
            FamilyASourcePlanRequirementStatus.PASS: (
                FamilyASourcePlanRequirementReason.FROZEN_SOURCE_PLAN_REQUIREMENT
            ),
            FamilyASourcePlanRequirementStatus.BLOCKED: (
                FamilyASourcePlanRequirementReason.REQUIREMENT_BLOCKED
            ),
            FamilyASourcePlanRequirementStatus.UNCOMPUTABLE: (
                FamilyASourcePlanRequirementReason.REQUIREMENT_UNCOMPUTABLE
            ),
        }[self.status]
        if self.reason_code is not expected_reason:
            raise ValueError("requirement status and reason conflict")
        payload = self.model_dump(mode="python", exclude={"requirement_sha256"})
        if self.requirement_sha256 != domain_sha256(PHASE16_REQUIREMENT_HASH_DOMAIN, payload):
            raise ValueError("requirement hash mismatch")
        return self


class FamilyASourceCapability(StrictModel):
    schema_version: Literal["phase16-family-a-point-in-time-source-plan-capability-v1"] = (
        PHASE16_CAPABILITY_SCHEMA_VERSION
    )
    ordinal: int = Field(ge=1, le=7)
    code: FamilyASourceCapabilityCode
    required: Literal[True] = True
    source_selected: Literal[False] = False
    capability_sha256: SHA256

    @model_validator(mode="after")
    def validate_capability(self) -> Self:
        if self.ordinal != PHASE16_CAPABILITY_ORDER.index(self.code) + 1:
            raise ValueError("capability ordinal must match the frozen registry")
        payload = self.model_dump(mode="python", exclude={"capability_sha256"})
        if self.capability_sha256 != domain_sha256(PHASE16_CAPABILITY_HASH_DOMAIN, payload):
            raise ValueError("capability hash mismatch")
        return self


class FamilyASourceCandidate(StrictModel):
    schema_version: Literal["phase16-family-a-point-in-time-source-plan-candidate-v1"] = (
        PHASE16_CANDIDATE_SCHEMA_VERSION
    )
    ordinal: int = Field(ge=1, le=6)
    code: FamilyASourceCandidateCode
    state: FamilyASourceCandidateState
    candidate_only: Literal[True] = True
    selected: Literal[False] = False
    rights_verified: Literal[False] = False
    external_verification_performed: Literal[False] = False
    candidate_sha256: SHA256

    @model_validator(mode="after")
    def validate_candidate(self) -> Self:
        if self.ordinal != PHASE16_CANDIDATE_ORDER.index(self.code) + 1:
            raise ValueError("candidate ordinal must match the frozen registry")
        if self.state is not PHASE16_EXPECTED_CANDIDATE_STATES[self.ordinal - 1]:
            raise ValueError("candidate state must match the frozen assessment")
        payload = self.model_dump(mode="python", exclude={"candidate_sha256"})
        if self.candidate_sha256 != domain_sha256(PHASE16_CANDIDATE_HASH_DOMAIN, payload):
            raise ValueError("candidate hash mismatch")
        return self


class FamilyASourcePlanStep(StrictModel):
    schema_version: Literal["phase16-family-a-point-in-time-source-plan-step-v1"] = (
        PHASE16_STEP_SCHEMA_VERSION
    )
    ordinal: int = Field(ge=1, le=7)
    code: FamilyASourcePlanStepCode
    definition: ClosedText
    state: Literal["NOT_STARTED"] = "NOT_STARTED"
    prerequisite_codes: tuple[FamilyASourcePlanStepCode, ...]
    required_prior_evidence: tuple[Identifier, ...]
    required_outputs: tuple[Identifier, ...]
    external_action_authorized: Literal[False] = False
    step_sha256: SHA256

    @model_validator(mode="after")
    def validate_step(self) -> Self:
        if self.ordinal != PHASE16_STEP_ORDER.index(self.code) + 1:
            raise ValueError("step ordinal must match the frozen registry")
        index = self.ordinal - 1
        if self.definition != PHASE16_STEP_DEFINITIONS[index]:
            raise ValueError("step definition must match the frozen registry")
        if (
            tuple(item.value for item in self.prerequisite_codes)
            != PHASE16_STEP_PREREQUISITES[index]
        ):
            raise ValueError("step prerequisites must match the frozen registry")
        if self.required_prior_evidence != PHASE16_STEP_REQUIRED_PRIOR_EVIDENCE[index]:
            raise ValueError("step prior evidence must match the frozen registry")
        if self.required_outputs != PHASE16_STEP_REQUIRED_OUTPUTS[index]:
            raise ValueError("step outputs must match the frozen registry")
        payload = self.model_dump(mode="python", exclude={"step_sha256"})
        if self.step_sha256 != domain_sha256(PHASE16_STEP_HASH_DOMAIN, payload):
            raise ValueError("step hash mismatch")
        return self


class Phase15GapBinding(StrictModel):
    schema_version: Literal["phase16-family-a-point-in-time-source-plan-gap-binding-v1"] = (
        PHASE16_GAP_BINDING_SCHEMA_VERSION
    )
    ordinal: int = Field(ge=1, le=19)
    code: Phase15GapCode
    state: Phase15GapState
    source_gap_sha256: SHA256
    binding_sha256: SHA256

    @model_validator(mode="after")
    def validate_binding(self) -> Self:
        index = self.ordinal - 1
        if self.ordinal != PHASE16_GAP_ORDER.index(self.code) + 1:
            raise ValueError("gap ordinal must match Phase 15")
        if self.state is not PHASE16_EXPECTED_GAP_STATES[index]:
            raise ValueError("gap state must remain unchanged from Phase 15")
        if self.source_gap_sha256 != PHASE16_PHASE15_GAP_SHA256S[index]:
            raise ValueError("gap source hash must remain unchanged from Phase 15")
        payload = self.model_dump(mode="python", exclude={"binding_sha256"})
        if self.binding_sha256 != domain_sha256(PHASE16_GAP_BINDING_HASH_DOMAIN, payload):
            raise ValueError("gap binding hash mismatch")
        return self


def _manifest(domain: str, schema: str, hashes: tuple[str, ...]) -> str:
    return domain_sha256(domain, {"schema_version": schema, "sha256s": hashes})


def requirements_manifest_sha256(items: tuple[FamilyASourcePlanRequirement, ...]) -> str:
    return _manifest(
        PHASE16_REQUIREMENTS_MANIFEST_HASH_DOMAIN,
        PHASE16_REQUIREMENT_SCHEMA_VERSION,
        tuple(item.requirement_sha256 for item in items),
    )


def capabilities_manifest_sha256(items: tuple[FamilyASourceCapability, ...]) -> str:
    return _manifest(
        PHASE16_CAPABILITIES_MANIFEST_HASH_DOMAIN,
        PHASE16_CAPABILITY_SCHEMA_VERSION,
        tuple(item.capability_sha256 for item in items),
    )


def candidates_manifest_sha256(items: tuple[FamilyASourceCandidate, ...]) -> str:
    return _manifest(
        PHASE16_CANDIDATES_MANIFEST_HASH_DOMAIN,
        PHASE16_CANDIDATE_SCHEMA_VERSION,
        tuple(item.candidate_sha256 for item in items),
    )


def steps_manifest_sha256(items: tuple[FamilyASourcePlanStep, ...]) -> str:
    return _manifest(
        PHASE16_STEPS_MANIFEST_HASH_DOMAIN,
        PHASE16_STEP_SCHEMA_VERSION,
        tuple(item.step_sha256 for item in items),
    )


def gap_bindings_manifest_sha256(items: tuple[Phase15GapBinding, ...]) -> str:
    return _manifest(
        PHASE16_GAPS_MANIFEST_HASH_DOMAIN,
        PHASE16_GAP_BINDING_SCHEMA_VERSION,
        tuple(item.binding_sha256 for item in items),
    )


class FamilyAPointInTimeSourcePlan(StrictModel):
    schema_version: Literal["phase16-family-a-point-in-time-source-plan-v1"]
    artifact_id: UUID
    artifact_sha256: SHA256
    policy_id: Literal["phase16-family-a-point-in-time-source-plan-policy-v1"]
    policy_sha256: SHA256
    accepted_phase15_commit_sha: GitSHA
    accepted_phase15_tree_sha: GitSHA
    phase15_artifact_id: UUID
    phase15_artifact_sha256: SHA256
    phase15_policy_sha256: SHA256
    phase15_requirements_manifest_sha256: SHA256
    phase15_gaps_manifest_sha256: SHA256
    family: Literal["A_CROSS_SECTIONAL_EQUITY_RANKING"]
    phase6_specification_id: Literal["phase6-a_cross_sectional_equity_ranking-research-pipeline"]
    phase6_specification_version: Literal["v2"]
    phase6_specification_sha256: SHA256
    frozen_at_utc: datetime
    outcome: FamilyASourcePlanOutcome
    requirements_manifest_sha256: SHA256
    capabilities_manifest_sha256: SHA256
    candidates_manifest_sha256: SHA256
    steps_manifest_sha256: SHA256
    gap_bindings_manifest_sha256: SHA256
    requirements: tuple[FamilyASourcePlanRequirement, ...]
    capabilities: tuple[FamilyASourceCapability, ...]
    candidates: tuple[FamilyASourceCandidate, ...]
    future_steps: tuple[FamilyASourcePlanStep, ...]
    phase15_gap_bindings: tuple[Phase15GapBinding, ...]
    external_request_performed: Literal[False]
    external_verification_performed: Literal[False]
    source_selected: Literal[False]
    provider_selected: Literal[False]
    product_selected: Literal[False]
    credentials_loaded: Literal[False]
    rights_verified: Literal[False]
    rights_granted: Literal[False]
    external_data_capture_authorized: Literal[False]
    provider_payload_persisted: Literal[False]
    licensed_data_persisted: Literal[False]
    research_ingestion_authorized: Literal[False]
    research_snapshot_created: Literal[False]
    research_data_eligible: Literal[False]
    evaluation_policy_approved: Literal[False]
    confirmation_holdout_defined: Literal[False]
    confirmation_holdout_opened: Literal[False]
    research_run_created: Literal[False]
    research_run_authorized: Literal[False]
    research_executed: Literal[False]
    performance_computed: Literal[False]
    pass_research_granted: Literal[False]
    strategy_promotion_authorized: Literal[False]
    paper_approval_granted: Literal[False]
    risk_clearance_granted: Literal[False]
    strategy_execution_eligible: Literal[False]
    execution_authorized: Literal[False]
    order_submission_authorized: Literal[False]
    live_path_absent: Literal[True]
    no_personalized_investment_advice: Literal[True]
    no_real_performance_claimed: Literal[True]
    disclaimer: Literal[
        "Source-plan evidence only; no source or product selection, rights verification, "
        "external request, data capture, persistence, ingestion, snapshot, evaluation "
        "policy, holdout, research result, promotion, risk clearance, execution authority, "
        "order, or personalized advice."
    ]

    @field_validator("frozen_at_utc")
    @classmethod
    def normalize_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("frozen_at_utc must be timezone-aware")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_plan(self) -> Self:
        expected = (
            self.schema_version == PHASE16_ARTIFACT_SCHEMA_VERSION
            and self.policy_id == PHASE16_POLICY_ID
            and self.policy_sha256 == PHASE16_POLICY_SHA256
            and self.accepted_phase15_commit_sha == PHASE16_ACCEPTED_PHASE15_COMMIT_SHA
            and self.accepted_phase15_tree_sha == PHASE16_ACCEPTED_PHASE15_TREE_SHA
            and str(self.phase15_artifact_id) == PHASE16_PHASE15_ARTIFACT_ID
            and self.phase15_artifact_sha256 == PHASE16_PHASE15_ARTIFACT_SHA256
            and self.phase15_policy_sha256 == PHASE16_PHASE15_POLICY_SHA256
            and self.phase15_requirements_manifest_sha256
            == PHASE16_PHASE15_REQUIREMENTS_MANIFEST_SHA256
            and self.phase15_gaps_manifest_sha256 == PHASE16_PHASE15_GAPS_MANIFEST_SHA256
            and self.family == PHASE16_FAMILY
            and self.phase6_specification_id == PHASE16_PHASE6_SPECIFICATION_ID
            and self.phase6_specification_version == PHASE16_PHASE6_SPECIFICATION_VERSION
            and self.phase6_specification_sha256 == PHASE16_PHASE6_SPECIFICATION_SHA256
            and self.frozen_at_utc == PHASE16_FROZEN_AT_UTC
            and self.disclaimer == PHASE16_DISCLAIMER
        )
        if not expected or self.artifact_id != identity(self.policy_sha256):
            raise ValueError("plan conflicts with the frozen policy identity")
        if tuple(item.code for item in self.requirements) != PHASE16_REQUIREMENT_ORDER:
            raise ValueError("plan requires all ordered requirements")
        if tuple(item.code for item in self.capabilities) != PHASE16_CAPABILITY_ORDER:
            raise ValueError("plan requires all ordered capabilities")
        if tuple(item.code for item in self.candidates) != PHASE16_CANDIDATE_ORDER:
            raise ValueError("plan requires all ordered candidates")
        if tuple(item.code for item in self.future_steps) != PHASE16_STEP_ORDER:
            raise ValueError("plan requires all ordered future steps")
        if tuple(item.code for item in self.phase15_gap_bindings) != PHASE16_GAP_ORDER:
            raise ValueError("plan requires all unchanged Phase 15 gaps")
        manifests = (
            self.requirements_manifest_sha256 == requirements_manifest_sha256(self.requirements)
            and self.capabilities_manifest_sha256 == capabilities_manifest_sha256(self.capabilities)
            and self.candidates_manifest_sha256 == candidates_manifest_sha256(self.candidates)
            and self.steps_manifest_sha256 == steps_manifest_sha256(self.future_steps)
            and self.gap_bindings_manifest_sha256
            == gap_bindings_manifest_sha256(self.phase15_gap_bindings)
        )
        if not manifests:
            raise ValueError("plan manifest hash mismatch")
        expected_outcome = (
            FamilyASourcePlanOutcome.PLAN_FROZEN
            if all(
                item.status is FamilyASourcePlanRequirementStatus.PASS for item in self.requirements
            )
            else FamilyASourcePlanOutcome.BLOCKED
        )
        if self.outcome is not expected_outcome:
            raise ValueError("outcome conflicts with requirement statuses")
        payload = self.model_dump(mode="python", exclude={"artifact_sha256"})
        if self.artifact_sha256 != domain_sha256(PHASE16_ARTIFACT_HASH_DOMAIN, payload):
            raise ValueError("artifact hash mismatch")
        for field, expected_value in PHASE16_BOUNDARY_VALUES.items():
            if getattr(self, field) is not expected_value:
                raise ValueError("authority boundary drift")
        return self


__all__ = [
    name for name in globals() if name.startswith("FamilyA") or name.startswith("PHASE16_")
] + [
    "Phase15GapBinding",
    "Phase15GapCode",
    "Phase15GapState",
    "capabilities_manifest_sha256",
    "candidates_manifest_sha256",
    "gap_bindings_manifest_sha256",
    "requirements_manifest_sha256",
    "steps_manifest_sha256",
]
