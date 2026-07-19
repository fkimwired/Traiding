"""Portable Phase 17 Family A candidate-product inventory."""

from fable5_data.phase17.contracts import (
    CandidateDeliveryVariantState,
    CandidateEvidenceState,
    CandidateReviewSelectionState,
    FamilyACandidateInventoryOutcome,
    FamilyACandidateProduct,
    FamilyACandidateProductCode,
    FamilyACandidateProductGroup,
    FamilyACandidateProductInventory,
    FamilyAInventoryCapabilityCode,
    FamilyAInventoryOutput,
    FamilyASourcePlanStepCode,
    FamilyASourcePlanStepEvidence,
    FamilyASourcePlanStepReason,
    FamilyASourcePlanStepState,
    Phase16CandidateCode,
)
from fable5_data.phase17.inventory import (
    build_family_a_candidate_product_inventory,
    canonical_candidate_product_inventory_bytes,
)

__all__ = [
    "CandidateDeliveryVariantState",
    "CandidateEvidenceState",
    "CandidateReviewSelectionState",
    "FamilyACandidateInventoryOutcome",
    "FamilyACandidateProduct",
    "FamilyACandidateProductCode",
    "FamilyACandidateProductGroup",
    "FamilyACandidateProductInventory",
    "FamilyAInventoryCapabilityCode",
    "FamilyAInventoryOutput",
    "FamilyASourcePlanStepCode",
    "FamilyASourcePlanStepEvidence",
    "FamilyASourcePlanStepReason",
    "FamilyASourcePlanStepState",
    "Phase16CandidateCode",
    "build_family_a_candidate_product_inventory",
    "canonical_candidate_product_inventory_bytes",
]
