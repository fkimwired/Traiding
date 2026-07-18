"""Strict portable contracts for the Phase 15 Family A admission specification."""

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

from fable5_data.phase15.canonical import (
    PHASE15_ACCEPTED_PHASE14_COMMIT_SHA,
    PHASE15_ACCEPTED_PHASE14_TREE_SHA,
    PHASE15_ARTIFACT_HASH_DOMAIN,
    PHASE15_ARTIFACT_SCHEMA_VERSION,
    PHASE15_DISCLAIMER,
    PHASE15_FAMILY,
    PHASE15_FROZEN_AT_UTC,
    PHASE15_GAP_EVIDENCE_REFS,
    PHASE15_GAP_HASH_DOMAIN,
    PHASE15_GAP_SCHEMA_VERSION,
    PHASE15_GAP_STATES,
    PHASE15_GAP_SUMMARIES,
    PHASE15_GAPS_MANIFEST_HASH_DOMAIN,
    PHASE15_PHASE6_SPECIFICATION_ID,
    PHASE15_PHASE6_SPECIFICATION_SHA256,
    PHASE15_PHASE6_SPECIFICATION_VERSION,
    PHASE15_POLICY_ID,
    PHASE15_POLICY_SHA256,
    PHASE15_REQUIREMENT_DEFINITIONS,
    PHASE15_REQUIREMENT_HASH_DOMAIN,
    PHASE15_REQUIREMENT_SCHEMA_VERSION,
    PHASE15_REQUIREMENTS_MANIFEST_HASH_DOMAIN,
    domain_sha256,
    identity,
)

SHA256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
GitSHA = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]
ClosedText = Annotated[str, StringConstraints(min_length=1, max_length=700)]
EvidenceReference = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=256,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._/#-]*$",
    ),
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")


class FamilyAResearchAdmissionOutcome(StrEnum):
    REQUIREMENTS_FROZEN = "REQUIREMENTS_FROZEN"
    BLOCKED = "BLOCKED"


class FamilyAResearchAdmissionRequirementStatus(StrEnum):
    PASS = "PASS"
    BLOCKED = "BLOCKED"
    UNCOMPUTABLE = "UNCOMPUTABLE"


class FamilyAResearchAdmissionRequirementReason(StrEnum):
    FROZEN_REPOSITORY_REQUIREMENT = "frozen_repository_requirement"
    REQUIREMENT_BLOCKED = "requirement_blocked"
    REQUIREMENT_UNCOMPUTABLE = "requirement_uncomputable"


class FamilyAResearchAdmissionRequirementCode(StrEnum):
    FAMILY_A_SPECIFICATION_IDENTITY_BOUND = "FAMILY_A_SPECIFICATION_IDENTITY_BOUND"
    SIGNAL_ACTION_AND_HORIZON_REQUIREMENTS_BOUND = "SIGNAL_ACTION_AND_HORIZON_REQUIREMENTS_BOUND"
    POINT_IN_TIME_CAPABILITY_REQUIREMENTS_FROZEN = "POINT_IN_TIME_CAPABILITY_REQUIREMENTS_FROZEN"
    INSTRUMENT_IDENTITY_AVAILABILITY_POLICY_FROZEN = (
        "INSTRUMENT_IDENTITY_AVAILABILITY_POLICY_FROZEN"
    )
    UNIVERSE_DELISTING_CORPORATE_ACTION_POLICY_FROZEN = (
        "UNIVERSE_DELISTING_CORPORATE_ACTION_POLICY_FROZEN"
    )
    FUNDAMENTAL_REVISION_LAG_POLICY_FROZEN = "FUNDAMENTAL_REVISION_LAG_POLICY_FROZEN"
    MACRO_SECTOR_LIQUIDITY_REQUIREMENTS_FROZEN = "MACRO_SECTOR_LIQUIDITY_REQUIREMENTS_FROZEN"
    FULL_HISTORY_SAMPLE_BOUNDARIES_FROZEN = "FULL_HISTORY_SAMPLE_BOUNDARIES_FROZEN"
    SNAPSHOT_CANONICALIZATION_AUDIT_POLICY_FROZEN = "SNAPSHOT_CANONICALIZATION_AUDIT_POLICY_FROZEN"
    USE_RIGHTS_RETENTION_DERIVED_DATA_POLICY_FROZEN = (
        "USE_RIGHTS_RETENTION_DERIVED_DATA_POLICY_FROZEN"
    )
    WALK_FORWARD_PURGE_EMBARGO_HOLDOUT_POLICY_FROZEN = (
        "WALK_FORWARD_PURGE_EMBARGO_HOLDOUT_POLICY_FROZEN"
    )
    TRIAL_ACCOUNTING_DSR_PBO_LEAKAGE_POLICY_FROZEN = (
        "TRIAL_ACCOUNTING_DSR_PBO_LEAKAGE_POLICY_FROZEN"
    )
    COST_SLIPPAGE_STRESS_REGIME_POLICY_FROZEN = "COST_SLIPPAGE_STRESS_REGIME_POLICY_FROZEN"
    RISK_REPRODUCIBILITY_POLICY_FROZEN = "RISK_REPRODUCIBILITY_POLICY_FROZEN"
    INGESTION_RESEARCH_PROMOTION_EXECUTION_AUTHORITY_ABSENT = (
        "INGESTION_RESEARCH_PROMOTION_EXECUTION_AUTHORITY_ABSENT"
    )


PHASE15_REQUIREMENT_ORDER: tuple[FamilyAResearchAdmissionRequirementCode, ...] = tuple(
    FamilyAResearchAdmissionRequirementCode
)


class FamilyAResearchAdmissionGapState(StrEnum):
    PRESENT = "PRESENT"
    MOCK_ONLY = "MOCK_ONLY"
    STALE = "STALE"
    MISSING = "MISSING"
    UNPROVEN = "UNPROVEN"


class FamilyAResearchAdmissionGapCode(StrEnum):
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


PHASE15_GAP_ORDER: tuple[FamilyAResearchAdmissionGapCode, ...] = tuple(
    FamilyAResearchAdmissionGapCode
)
PHASE15_EXPECTED_GAP_STATES: tuple[FamilyAResearchAdmissionGapState, ...] = tuple(
    FamilyAResearchAdmissionGapState(value) for value in PHASE15_GAP_STATES
)


class FamilyAResearchAdmissionRequirement(StrictModel):
    schema_version: Literal["phase15-family-a-research-admission-requirement-v1"] = (
        PHASE15_REQUIREMENT_SCHEMA_VERSION
    )
    ordinal: int = Field(ge=1, le=15)
    code: FamilyAResearchAdmissionRequirementCode
    definition: ClosedText
    status: FamilyAResearchAdmissionRequirementStatus
    reason_code: FamilyAResearchAdmissionRequirementReason
    evidence_sha256s: tuple[SHA256, ...]
    requirement_sha256: SHA256

    @model_validator(mode="after")
    def validate_requirement(self) -> Self:
        if self.ordinal != PHASE15_REQUIREMENT_ORDER.index(self.code) + 1:
            raise ValueError("requirement ordinal must match the frozen registry")
        if self.definition != PHASE15_REQUIREMENT_DEFINITIONS[self.ordinal - 1]:
            raise ValueError("requirement definition must match the frozen registry")
        if tuple(sorted(set(self.evidence_sha256s))) != self.evidence_sha256s:
            raise ValueError("requirement evidence hashes must be unique and sorted")
        if not self.evidence_sha256s:
            raise ValueError("requirement must bind immutable evidence")
        expected_reason = {
            FamilyAResearchAdmissionRequirementStatus.PASS: (
                FamilyAResearchAdmissionRequirementReason.FROZEN_REPOSITORY_REQUIREMENT
            ),
            FamilyAResearchAdmissionRequirementStatus.BLOCKED: (
                FamilyAResearchAdmissionRequirementReason.REQUIREMENT_BLOCKED
            ),
            FamilyAResearchAdmissionRequirementStatus.UNCOMPUTABLE: (
                FamilyAResearchAdmissionRequirementReason.REQUIREMENT_UNCOMPUTABLE
            ),
        }[self.status]
        if self.reason_code is not expected_reason:
            raise ValueError("requirement status and reason conflict")
        payload = self.model_dump(mode="python", exclude={"requirement_sha256"})
        if self.requirement_sha256 != domain_sha256(PHASE15_REQUIREMENT_HASH_DOMAIN, payload):
            raise ValueError("requirement hash does not bind its complete preimage")
        return self


class FamilyAResearchAdmissionGap(StrictModel):
    schema_version: Literal["phase15-family-a-research-admission-gap-v1"] = (
        PHASE15_GAP_SCHEMA_VERSION
    )
    ordinal: int = Field(ge=1, le=19)
    code: FamilyAResearchAdmissionGapCode
    state: FamilyAResearchAdmissionGapState
    summary: ClosedText
    evidence_refs: tuple[EvidenceReference, ...]
    evidence_sha256s: tuple[SHA256, ...]
    gap_sha256: SHA256

    @model_validator(mode="after")
    def validate_gap(self) -> Self:
        if self.ordinal != PHASE15_GAP_ORDER.index(self.code) + 1:
            raise ValueError("gap ordinal must match the frozen registry")
        if self.state is not PHASE15_EXPECTED_GAP_STATES[self.ordinal - 1]:
            raise ValueError("gap state must match the frozen repository assessment")
        if self.summary != PHASE15_GAP_SUMMARIES[self.ordinal - 1]:
            raise ValueError("gap summary must match the frozen repository assessment")
        if self.evidence_refs != PHASE15_GAP_EVIDENCE_REFS[self.ordinal - 1]:
            raise ValueError("gap evidence references must match the frozen repository assessment")
        if tuple(sorted(set(self.evidence_refs))) != self.evidence_refs:
            raise ValueError("gap evidence references must be unique and sorted")
        if tuple(sorted(set(self.evidence_sha256s))) != self.evidence_sha256s:
            raise ValueError("gap evidence hashes must be unique and sorted")
        if not self.evidence_sha256s:
            raise ValueError("gap must bind immutable evidence")
        payload = self.model_dump(mode="python", exclude={"gap_sha256"})
        if self.gap_sha256 != domain_sha256(PHASE15_GAP_HASH_DOMAIN, payload):
            raise ValueError("gap hash does not bind its complete preimage")
        return self


def requirements_manifest_sha256(
    requirements: tuple[FamilyAResearchAdmissionRequirement, ...],
) -> str:
    return domain_sha256(
        PHASE15_REQUIREMENTS_MANIFEST_HASH_DOMAIN,
        {
            "schema_version": PHASE15_REQUIREMENT_SCHEMA_VERSION,
            "requirement_sha256s": tuple(item.requirement_sha256 for item in requirements),
        },
    )


def gaps_manifest_sha256(gaps: tuple[FamilyAResearchAdmissionGap, ...]) -> str:
    return domain_sha256(
        PHASE15_GAPS_MANIFEST_HASH_DOMAIN,
        {
            "schema_version": PHASE15_GAP_SCHEMA_VERSION,
            "gap_sha256s": tuple(item.gap_sha256 for item in gaps),
        },
    )


class FamilyAResearchAdmissionSpecification(StrictModel):
    schema_version: Literal["phase15-family-a-research-admission-specification-v1"]
    artifact_id: UUID
    artifact_sha256: SHA256
    policy_id: Literal["phase15-family-a-research-admission-policy-v1"]
    policy_sha256: SHA256
    accepted_phase14_commit_sha: GitSHA
    accepted_phase14_tree_sha: GitSHA
    family: Literal["A_CROSS_SECTIONAL_EQUITY_RANKING"]
    phase6_specification_id: Literal["phase6-a_cross_sectional_equity_ranking-research-pipeline"]
    phase6_specification_version: Literal["v2"]
    phase6_specification_sha256: SHA256
    frozen_at_utc: datetime
    outcome: FamilyAResearchAdmissionOutcome
    requirements_manifest_sha256: SHA256
    gaps_manifest_sha256: SHA256
    requirements: tuple[FamilyAResearchAdmissionRequirement, ...]
    gaps: tuple[FamilyAResearchAdmissionGap, ...]
    external_request_performed: Literal[False]
    external_data_capture_authorized: Literal[False]
    provider_payload_persisted: Literal[False]
    licensed_data_persisted: Literal[False]
    research_ingestion_authorized: Literal[False]
    research_snapshot_created: Literal[False]
    research_data_eligible: Literal[False]
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
        "Requirements-only evidence; no external capture, data ingestion, research dataset, "
        "research authorization, performance result, promotion, risk clearance, execution "
        "authority, order, or personalized investment advice."
    ]

    @field_validator("frozen_at_utc")
    @classmethod
    def normalize_frozen_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("frozen_at_utc must be timezone-aware")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_specification(self) -> Self:
        if (
            self.schema_version != PHASE15_ARTIFACT_SCHEMA_VERSION
            or self.policy_id != PHASE15_POLICY_ID
            or self.policy_sha256 != PHASE15_POLICY_SHA256
            or self.accepted_phase14_commit_sha != PHASE15_ACCEPTED_PHASE14_COMMIT_SHA
            or self.accepted_phase14_tree_sha != PHASE15_ACCEPTED_PHASE14_TREE_SHA
            or self.family != PHASE15_FAMILY
            or self.phase6_specification_id != PHASE15_PHASE6_SPECIFICATION_ID
            or self.phase6_specification_version != PHASE15_PHASE6_SPECIFICATION_VERSION
            or self.phase6_specification_sha256 != PHASE15_PHASE6_SPECIFICATION_SHA256
            or self.frozen_at_utc != PHASE15_FROZEN_AT_UTC
            or self.disclaimer != PHASE15_DISCLAIMER
        ):
            raise ValueError("specification conflicts with the frozen policy")
        if self.artifact_id != identity(self.policy_sha256):
            raise ValueError("artifact identity must derive from the frozen policy hash")
        if tuple(item.code for item in self.requirements) != PHASE15_REQUIREMENT_ORDER:
            raise ValueError("specification must contain all fifteen ordered requirements")
        if tuple(item.code for item in self.gaps) != PHASE15_GAP_ORDER:
            raise ValueError("specification must contain all nineteen ordered gaps")
        if self.requirements_manifest_sha256 != requirements_manifest_sha256(self.requirements):
            raise ValueError("requirements manifest hash mismatch")
        if self.gaps_manifest_sha256 != gaps_manifest_sha256(self.gaps):
            raise ValueError("gaps manifest hash mismatch")
        expected_outcome = (
            FamilyAResearchAdmissionOutcome.REQUIREMENTS_FROZEN
            if all(
                item.status is FamilyAResearchAdmissionRequirementStatus.PASS
                for item in self.requirements
            )
            else FamilyAResearchAdmissionOutcome.BLOCKED
        )
        if self.outcome is not expected_outcome:
            raise ValueError("outcome conflicts with requirement statuses")
        payload = self.model_dump(mode="python", exclude={"artifact_sha256"})
        if self.artifact_sha256 != domain_sha256(PHASE15_ARTIFACT_HASH_DOMAIN, payload):
            raise ValueError("artifact hash does not bind its complete preimage")
        return self


__all__ = [
    "PHASE15_EXPECTED_GAP_STATES",
    "PHASE15_GAP_ORDER",
    "PHASE15_REQUIREMENT_ORDER",
    "FamilyAResearchAdmissionGap",
    "FamilyAResearchAdmissionGapCode",
    "FamilyAResearchAdmissionGapState",
    "FamilyAResearchAdmissionOutcome",
    "FamilyAResearchAdmissionRequirement",
    "FamilyAResearchAdmissionRequirementCode",
    "FamilyAResearchAdmissionRequirementReason",
    "FamilyAResearchAdmissionRequirementStatus",
    "FamilyAResearchAdmissionSpecification",
    "gaps_manifest_sha256",
    "requirements_manifest_sha256",
]
