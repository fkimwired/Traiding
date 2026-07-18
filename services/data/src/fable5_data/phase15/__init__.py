"""Phase 15 portable Family A research-admission specification."""

from fable5_data.phase15.canonical import (
    PHASE15_ACCEPTED_PHASE14_COMMIT_SHA,
    PHASE15_ACCEPTED_PHASE14_TREE_SHA,
    PHASE15_ARTIFACT_SCHEMA_VERSION,
    PHASE15_DISCLAIMER,
    PHASE15_GAP_SCHEMA_VERSION,
    PHASE15_POLICY_ID,
    PHASE15_POLICY_SHA256,
    PHASE15_REQUIREMENT_SCHEMA_VERSION,
)
from fable5_data.phase15.contracts import (
    PHASE15_EXPECTED_GAP_STATES,
    PHASE15_GAP_ORDER,
    PHASE15_REQUIREMENT_ORDER,
    FamilyAResearchAdmissionGap,
    FamilyAResearchAdmissionGapCode,
    FamilyAResearchAdmissionGapState,
    FamilyAResearchAdmissionOutcome,
    FamilyAResearchAdmissionRequirement,
    FamilyAResearchAdmissionRequirementCode,
    FamilyAResearchAdmissionRequirementReason,
    FamilyAResearchAdmissionRequirementStatus,
    FamilyAResearchAdmissionSpecification,
    gaps_manifest_sha256,
    requirements_manifest_sha256,
)
from fable5_data.phase15.specification import (
    build_family_a_research_admission_specification,
    canonical_specification_bytes,
)

__all__ = [
    "PHASE15_ACCEPTED_PHASE14_COMMIT_SHA",
    "PHASE15_ACCEPTED_PHASE14_TREE_SHA",
    "PHASE15_ARTIFACT_SCHEMA_VERSION",
    "PHASE15_DISCLAIMER",
    "PHASE15_EXPECTED_GAP_STATES",
    "PHASE15_GAP_ORDER",
    "PHASE15_GAP_SCHEMA_VERSION",
    "PHASE15_POLICY_ID",
    "PHASE15_POLICY_SHA256",
    "PHASE15_REQUIREMENT_ORDER",
    "PHASE15_REQUIREMENT_SCHEMA_VERSION",
    "FamilyAResearchAdmissionGap",
    "FamilyAResearchAdmissionGapCode",
    "FamilyAResearchAdmissionGapState",
    "FamilyAResearchAdmissionOutcome",
    "FamilyAResearchAdmissionRequirement",
    "FamilyAResearchAdmissionRequirementCode",
    "FamilyAResearchAdmissionRequirementReason",
    "FamilyAResearchAdmissionRequirementStatus",
    "FamilyAResearchAdmissionSpecification",
    "build_family_a_research_admission_specification",
    "canonical_specification_bytes",
    "gaps_manifest_sha256",
    "requirements_manifest_sha256",
]
