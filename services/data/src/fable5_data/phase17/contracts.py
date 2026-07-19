"""Strict portable contracts for the Phase 17 candidate-product inventory."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from fable5_data.phase17.canonical import (
    PHASE17_ACCEPTED_PHASE16_COMMIT_SHA,
    PHASE17_ACCEPTED_PHASE16_TREE_SHA,
    PHASE17_ARTIFACT_HASH_DOMAIN,
    PHASE17_ARTIFACT_SCHEMA_VERSION,
    PHASE17_BLOCK_REASON,
    PHASE17_BOUNDARY_VALUES,
    PHASE17_CANDIDATE_GROUP_ROWS,
    PHASE17_CANDIDATE_HASH_DOMAIN,
    PHASE17_CANDIDATE_SCHEMA_VERSION,
    PHASE17_CANDIDATES_MANIFEST_HASH_DOMAIN,
    PHASE17_DISCLAIMER,
    PHASE17_FAMILY,
    PHASE17_FROZEN_AT_UTC,
    PHASE17_OUTPUT_HASH_DOMAIN,
    PHASE17_OUTPUT_SCHEMA_VERSION,
    PHASE17_PHASE16_ARTIFACT_ID,
    PHASE17_PHASE16_ARTIFACT_SHA256,
    PHASE17_PHASE16_CANDIDATES_MANIFEST_SHA256,
    PHASE17_PHASE16_CAPABILITIES_MANIFEST_SHA256,
    PHASE17_PHASE16_GAP_BINDINGS_MANIFEST_SHA256,
    PHASE17_PHASE16_POLICY_SHA256,
    PHASE17_PHASE16_REQUIREMENTS_MANIFEST_SHA256,
    PHASE17_PHASE16_STEP1_SHA256,
    PHASE17_PHASE16_STEPS_MANIFEST_SHA256,
    PHASE17_POLICY_ID,
    PHASE17_POLICY_SHA256,
    PHASE17_PRODUCT_HASH_DOMAIN,
    PHASE17_PRODUCT_ROWS,
    PHASE17_PRODUCT_SCHEMA_VERSION,
    PHASE17_PRODUCTS_MANIFEST_HASH_DOMAIN,
    PHASE17_STEP_CODES,
    PHASE17_STEP_HASH_DOMAIN,
    PHASE17_STEP_PREREQUISITES,
    PHASE17_STEP_REQUIRED_OUTPUTS,
    PHASE17_STEP_REQUIRED_PRIOR_EVIDENCE,
    PHASE17_STEP_SCHEMA_VERSION,
    PHASE17_STEP_STATES,
    PHASE17_STEPS_MANIFEST_HASH_DOMAIN,
    canonicalize,
    domain_sha256,
    identity,
)

SHA256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
GitSHA = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]
ClosedText = Annotated[str, StringConstraints(min_length=1, max_length=900)]
Identifier = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]{0,127}$")]
HttpsCitation = Annotated[str, StringConstraints(pattern=r"^https://[^\s]+$", max_length=500)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")


class FamilyACandidateInventoryOutcome(StrEnum):
    BLOCKED = "BLOCKED"


class FamilyACandidateProductCode(StrEnum):
    TIINGO_END_OF_DAY = "TIINGO_END_OF_DAY"
    TIINGO_US_FUNDAMENTALS = "TIINGO_US_FUNDAMENTALS"
    TIINGO_DIVIDEND_CORPORATE_ACTIONS = "TIINGO_DIVIDEND_CORPORATE_ACTIONS"
    TIINGO_SPLIT_CORPORATE_ACTIONS = "TIINGO_SPLIT_CORPORATE_ACTIONS"
    MORNINGSTAR_CRSP_US_STOCK_DATABASES = "MORNINGSTAR_CRSP_US_STOCK_DATABASES"
    MORNINGSTAR_CRSP_COMPUSTAT_MERGED = "MORNINGSTAR_CRSP_COMPUSTAT_MERGED"
    SEC_EDGAR_SUBMISSIONS_AND_XBRL_DATA_APIS = "SEC_EDGAR_SUBMISSIONS_AND_XBRL_DATA_APIS"
    FRED_REALTIME_AND_VINTAGE_WEB_SERVICE = "FRED_REALTIME_AND_VINTAGE_WEB_SERVICE"
    LSEG_TICK_HISTORY_INSTRUMENT_AND_VENUE_WEB_API = (
        "LSEG_TICK_HISTORY_INSTRUMENT_AND_VENUE_WEB_API"
    )


PHASE17_PRODUCT_ORDER = tuple(FamilyACandidateProductCode)


class Phase16CandidateCode(StrEnum):
    TIINGO_PHASE13_BOUNDED_CANDIDATE = "TIINGO_PHASE13_BOUNDED_CANDIDATE"
    MORNINGSTAR_CRSP_US_STOCK_DATABASES_CANDIDATE = "MORNINGSTAR_CRSP_US_STOCK_DATABASES_CANDIDATE"
    MORNINGSTAR_CRSP_COMPUSTAT_MERGED_DATABASE_CANDIDATE = (
        "MORNINGSTAR_CRSP_COMPUSTAT_MERGED_DATABASE_CANDIDATE"
    )
    SEC_EDGAR_SUBMISSIONS_XBRL_CANDIDATE = "SEC_EDGAR_SUBMISSIONS_XBRL_CANDIDATE"
    FEDERAL_RESERVE_ALFRED_VINTAGES_CANDIDATE = "FEDERAL_RESERVE_ALFRED_VINTAGES_CANDIDATE"
    HISTORICAL_LIQUIDITY_PRODUCT_UNSELECTED = "HISTORICAL_LIQUIDITY_PRODUCT_UNSELECTED"


PHASE17_CANDIDATE_ORDER = tuple(Phase16CandidateCode)


class FamilyAInventoryCapabilityCode(StrEnum):
    SECURITY_MASTER = "security_master"
    UNIVERSE_MEMBERSHIP = "universe_membership"
    OHLCV = "ohlcv"
    CORPORATE_ACTIONS = "corporate_actions"
    DELISTINGS = "delistings"
    AS_REPORTED_FUNDAMENTALS = "as_reported_fundamentals"
    MACRO_REGIME_INPUTS = "macro_regime_inputs"
    SECTOR_CLASSIFICATION_HISTORY = "sector_classification_history"
    HISTORICAL_LIQUIDITY_DEPTH = "historical_liquidity_depth"


class CandidateEvidenceState(StrEnum):
    UNPROVEN = "UNPROVEN"


class CandidateDeliveryVariantState(StrEnum):
    DOCUMENTED_WEB_API_SURFACE = "DOCUMENTED_WEB_API_SURFACE"
    UNPROVEN = "UNPROVEN"


class CandidateReviewSelectionState(StrEnum):
    NAMED_FOR_INDEPENDENT_RIGHTS_REVIEW = "NAMED_FOR_INDEPENDENT_RIGHTS_REVIEW"


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


PHASE17_STEP_ORDER = tuple(FamilyASourcePlanStepCode)


class FamilyASourcePlanStepState(StrEnum):
    OUTPUT_FROZEN = "OUTPUT_FROZEN"
    NOT_STARTED = "NOT_STARTED"


class FamilyASourcePlanStepReason(StrEnum):
    INVENTORY_OUTPUT_FROZEN_DOWNSTREAM_RIGHTS_REVIEW_REQUIRED = (
        "inventory_output_frozen_downstream_rights_review_required"
    )
    PREREQUISITE_NOT_SATISFIED = "prerequisite_not_satisfied"


class FamilyACandidateProduct(StrictModel):
    schema_version: str
    ordinal: Annotated[int, Field(ge=1, le=9)]
    code: FamilyACandidateProductCode
    phase16_candidate_code: Phase16CandidateCode
    official_name: ClosedText
    official_documentation_url: HttpsCitation
    official_fact: ClosedText
    capability_codes: tuple[FamilyAInventoryCapabilityCode, ...]
    selected_for_independent_rights_review: bool
    operational_provider_selected: bool
    operational_product_selected: bool
    operational_source_selected: bool
    entitlement_state: CandidateEvidenceState
    rights_state: CandidateEvidenceState
    fitness_state: CandidateEvidenceState
    coverage_proven: bool
    schema_proven: bool
    current_availability_proven: bool
    external_sample_qualified: bool
    delivery_variant_state: CandidateDeliveryVariantState
    product_sha256: SHA256

    @model_validator(mode="after")
    def validate_frozen_product(self) -> Self:
        expected = PHASE17_PRODUCT_ROWS[self.ordinal - 1]
        expected_payload = {
            "schema_version": PHASE17_PRODUCT_SCHEMA_VERSION,
            "ordinal": self.ordinal,
            "code": expected[0],
            "phase16_candidate_code": expected[1],
            "official_name": expected[2],
            "official_documentation_url": expected[3],
            "official_fact": expected[4],
            "capability_codes": expected[5],
            "selected_for_independent_rights_review": True,
            "operational_provider_selected": False,
            "operational_product_selected": False,
            "operational_source_selected": False,
            "entitlement_state": "UNPROVEN",
            "rights_state": "UNPROVEN",
            "fitness_state": "UNPROVEN",
            "coverage_proven": False,
            "schema_proven": False,
            "current_availability_proven": False,
            "external_sample_qualified": False,
            "delivery_variant_state": expected[6],
        }
        actual_payload = self.model_dump(mode="python", exclude={"product_sha256"})
        if canonicalize(actual_payload) != canonicalize(expected_payload):
            raise ValueError("candidate product does not match its frozen official metadata row")
        if self.product_sha256 != domain_sha256(PHASE17_PRODUCT_HASH_DOMAIN, expected_payload):
            raise ValueError("candidate-product hash mismatch")
        return self


class FamilyACandidateProductGroup(StrictModel):
    schema_version: str
    ordinal: Annotated[int, Field(ge=1, le=6)]
    phase16_candidate_code: Phase16CandidateCode
    product_codes: tuple[FamilyACandidateProductCode, ...]
    selected_for_independent_rights_review: bool
    selection_state: CandidateReviewSelectionState
    single_operational_selection: bool
    candidate_group_sha256: SHA256

    @model_validator(mode="after")
    def validate_frozen_candidate_group(self) -> Self:
        expected = PHASE17_CANDIDATE_GROUP_ROWS[self.ordinal - 1]
        expected_payload = {
            "schema_version": PHASE17_CANDIDATE_SCHEMA_VERSION,
            "ordinal": self.ordinal,
            "phase16_candidate_code": expected[0],
            "product_codes": expected[1],
            "selected_for_independent_rights_review": True,
            "selection_state": "NAMED_FOR_INDEPENDENT_RIGHTS_REVIEW",
            "single_operational_selection": False,
        }
        actual_payload = self.model_dump(mode="python", exclude={"candidate_group_sha256"})
        if canonicalize(actual_payload) != canonicalize(expected_payload):
            raise ValueError("candidate group does not match its frozen review-only mapping")
        if self.candidate_group_sha256 != domain_sha256(
            PHASE17_CANDIDATE_HASH_DOMAIN, expected_payload
        ):
            raise ValueError("candidate-group hash mismatch")
        return self


class FamilyAInventoryOutput(StrictModel):
    schema_version: str
    name: Identifier
    sha256: SHA256
    output_sha256: SHA256

    @model_validator(mode="after")
    def validate_output_hash(self) -> Self:
        payload = self.model_dump(mode="python", exclude={"output_sha256"})
        if self.schema_version != PHASE17_OUTPUT_SCHEMA_VERSION:
            raise ValueError("output schema mismatch")
        if self.output_sha256 != domain_sha256(PHASE17_OUTPUT_HASH_DOMAIN, payload):
            raise ValueError("output hash mismatch")
        return self


class FamilyASourcePlanStepEvidence(StrictModel):
    schema_version: str
    ordinal: Annotated[int, Field(ge=1, le=7)]
    code: FamilyASourcePlanStepCode
    state: FamilyASourcePlanStepState
    reason_code: FamilyASourcePlanStepReason
    prerequisite_codes: tuple[FamilyASourcePlanStepCode, ...]
    required_prior_evidence: tuple[Identifier, ...]
    required_outputs: tuple[Identifier, ...]
    produced_outputs: tuple[FamilyAInventoryOutput, ...]
    external_action_authorized: bool
    step_sha256: SHA256

    @model_validator(mode="after")
    def validate_frozen_step(self) -> Self:
        index = self.ordinal - 1
        expected_state = PHASE17_STEP_STATES[index]
        expected_reason = (
            "inventory_output_frozen_downstream_rights_review_required"
            if index == 0
            else "prerequisite_not_satisfied"
        )
        expected_payload = {
            "schema_version": PHASE17_STEP_SCHEMA_VERSION,
            "ordinal": self.ordinal,
            "code": PHASE17_STEP_CODES[index],
            "state": expected_state,
            "reason_code": expected_reason,
            "prerequisite_codes": PHASE17_STEP_PREREQUISITES[index],
            "required_prior_evidence": PHASE17_STEP_REQUIRED_PRIOR_EVIDENCE[index],
            "required_outputs": PHASE17_STEP_REQUIRED_OUTPUTS[index],
            "produced_outputs": self.produced_outputs,
            "external_action_authorized": False,
        }
        if index == 0:
            if (
                len(self.produced_outputs) != 1
                or self.produced_outputs[0].name != "candidate_product_inventory_sha256"
            ):
                raise ValueError("the frozen inventory step requires its sole named output")
        elif self.produced_outputs:
            raise ValueError("unstarted source-plan steps cannot contain produced output evidence")
        actual_payload = self.model_dump(mode="python", exclude={"step_sha256"})
        if canonicalize(actual_payload) != canonicalize(expected_payload):
            raise ValueError("source-plan step evidence drifted")
        if self.step_sha256 != domain_sha256(PHASE17_STEP_HASH_DOMAIN, expected_payload):
            raise ValueError("source-plan step hash mismatch")
        return self


def products_manifest_sha256(products: tuple[FamilyACandidateProduct, ...]) -> str:
    return domain_sha256(
        PHASE17_PRODUCTS_MANIFEST_HASH_DOMAIN,
        tuple(item.product_sha256 for item in products),
    )


def candidate_groups_manifest_sha256(groups: tuple[FamilyACandidateProductGroup, ...]) -> str:
    return domain_sha256(
        PHASE17_CANDIDATES_MANIFEST_HASH_DOMAIN,
        tuple(item.candidate_group_sha256 for item in groups),
    )


def steps_manifest_sha256(steps: tuple[FamilyASourcePlanStepEvidence, ...]) -> str:
    return domain_sha256(
        PHASE17_STEPS_MANIFEST_HASH_DOMAIN,
        tuple(item.step_sha256 for item in steps),
    )


class FamilyACandidateProductInventory(StrictModel):
    schema_version: str
    artifact_id: UUID
    artifact_sha256: SHA256
    policy_id: str
    policy_sha256: SHA256
    accepted_phase16_commit_sha: GitSHA
    accepted_phase16_tree_sha: GitSHA
    phase16_artifact_id: UUID
    phase16_artifact_sha256: SHA256
    phase16_policy_sha256: SHA256
    phase16_requirements_manifest_sha256: SHA256
    phase16_capabilities_manifest_sha256: SHA256
    phase16_candidates_manifest_sha256: SHA256
    phase16_steps_manifest_sha256: SHA256
    phase16_step1_sha256: SHA256
    phase16_gap_bindings_manifest_sha256: SHA256
    family: str
    frozen_at_utc: datetime
    outcome: FamilyACandidateInventoryOutcome
    block_reason: ClosedText
    candidate_product_inventory_sha256: SHA256
    candidate_groups_manifest_sha256: SHA256
    steps_manifest_sha256: SHA256
    products: tuple[FamilyACandidateProduct, ...]
    candidate_groups: tuple[FamilyACandidateProductGroup, ...]
    source_plan_steps: tuple[FamilyASourcePlanStepEvidence, ...]
    metadata_only: bool
    official_public_documentation_review_performed: bool
    official_documentation_citations_inert: bool
    runtime_network_disabled: bool
    external_request_performed: bool
    provider_data_request_performed: bool
    provider_account_verification_performed: bool
    entitlement_verification_performed: bool
    provider_selected: bool
    product_selected: bool
    source_selected: bool
    credentials_loaded: bool
    entitlement_verified: bool
    rights_verified: bool
    rights_granted: bool
    fitness_verified: bool
    coverage_proven: bool
    schema_proven: bool
    current_availability_proven: bool
    external_sample_qualified: bool
    external_data_capture_authorized: bool
    provider_payload_persisted: bool
    licensed_data_persisted: bool
    research_ingestion_authorized: bool
    research_snapshot_created: bool
    research_data_eligible: bool
    evaluation_policy_approved: bool
    confirmation_holdout_defined: bool
    confirmation_holdout_opened: bool
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
    def validate_closed_inventory(self) -> Self:
        identity_values = (
            self.schema_version == PHASE17_ARTIFACT_SCHEMA_VERSION,
            self.artifact_id == identity(PHASE17_POLICY_SHA256),
            self.policy_id == PHASE17_POLICY_ID,
            self.policy_sha256 == PHASE17_POLICY_SHA256,
            self.accepted_phase16_commit_sha == PHASE17_ACCEPTED_PHASE16_COMMIT_SHA,
            self.accepted_phase16_tree_sha == PHASE17_ACCEPTED_PHASE16_TREE_SHA,
            str(self.phase16_artifact_id) == PHASE17_PHASE16_ARTIFACT_ID,
            self.phase16_artifact_sha256 == PHASE17_PHASE16_ARTIFACT_SHA256,
            self.phase16_policy_sha256 == PHASE17_PHASE16_POLICY_SHA256,
            self.phase16_requirements_manifest_sha256
            == PHASE17_PHASE16_REQUIREMENTS_MANIFEST_SHA256,
            self.phase16_capabilities_manifest_sha256
            == PHASE17_PHASE16_CAPABILITIES_MANIFEST_SHA256,
            self.phase16_candidates_manifest_sha256 == PHASE17_PHASE16_CANDIDATES_MANIFEST_SHA256,
            self.phase16_steps_manifest_sha256 == PHASE17_PHASE16_STEPS_MANIFEST_SHA256,
            self.phase16_step1_sha256 == PHASE17_PHASE16_STEP1_SHA256,
            self.phase16_gap_bindings_manifest_sha256
            == PHASE17_PHASE16_GAP_BINDINGS_MANIFEST_SHA256,
            self.family == PHASE17_FAMILY,
            self.frozen_at_utc.astimezone(UTC) == PHASE17_FROZEN_AT_UTC,
            self.outcome is FamilyACandidateInventoryOutcome.BLOCKED,
            self.block_reason == PHASE17_BLOCK_REASON,
            self.disclaimer == PHASE17_DISCLAIMER,
        )
        if not all(identity_values):
            raise ValueError("candidate-product inventory identity or blocked boundary drifted")
        if tuple(item.code for item in self.products) != PHASE17_PRODUCT_ORDER:
            raise ValueError("candidate-product registry or order drifted")
        if tuple(item.phase16_candidate_code for item in self.candidate_groups) != (
            PHASE17_CANDIDATE_ORDER
        ):
            raise ValueError("Phase 16 candidate-group registry or order drifted")
        if tuple(item.code for item in self.source_plan_steps) != PHASE17_STEP_ORDER:
            raise ValueError("source-plan step registry or order drifted")
        product_manifest = products_manifest_sha256(self.products)
        if self.candidate_product_inventory_sha256 != product_manifest:
            raise ValueError("candidate-product inventory manifest mismatch")
        if self.candidate_groups_manifest_sha256 != candidate_groups_manifest_sha256(
            self.candidate_groups
        ):
            raise ValueError("candidate-group manifest mismatch")
        if self.steps_manifest_sha256 != steps_manifest_sha256(self.source_plan_steps):
            raise ValueError("source-plan steps manifest mismatch")
        first_outputs = self.source_plan_steps[0].produced_outputs
        if len(first_outputs) != 1 or first_outputs[0].sha256 != product_manifest:
            raise ValueError("inventory step output does not bind the product manifest")
        rendered = self.model_dump(mode="python")
        for field, expected in PHASE17_BOUNDARY_VALUES.items():
            if rendered[field] is not expected:
                raise ValueError(f"candidate-product inventory unexpectedly changed {field}")
        preimage = self.model_dump(mode="python", exclude={"artifact_sha256"})
        if self.artifact_sha256 != domain_sha256(PHASE17_ARTIFACT_HASH_DOMAIN, preimage):
            raise ValueError("candidate-product inventory artifact hash mismatch")
        return self


__all__ = [
    "PHASE17_CANDIDATE_ORDER",
    "PHASE17_PRODUCT_ORDER",
    "PHASE17_STEP_ORDER",
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
    "candidate_groups_manifest_sha256",
    "products_manifest_sha256",
    "steps_manifest_sha256",
]
