"""Strict portable contracts for the Phase 18 current-use rights review."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from fable5_data.phase18.canonical import (
    PHASE18_ACCEPTED_PHASE17_COMMIT_SHA,
    PHASE18_ACCEPTED_PHASE17_TREE_SHA,
    PHASE18_AGGREGATE_CONCLUSION,
    PHASE18_ARTIFACT_HASH_DOMAIN,
    PHASE18_ARTIFACT_SCHEMA_VERSION,
    PHASE18_BLOCK_REASON,
    PHASE18_BOUNDARY_VALUES,
    PHASE18_CURRENTNESS_HASH_DOMAIN,
    PHASE18_DISCLAIMER,
    PHASE18_FAMILY,
    PHASE18_FINDING_HASH_DOMAIN,
    PHASE18_FINDING_SCHEMA_VERSION,
    PHASE18_FROZEN_AT_UTC,
    PHASE18_OUTPUT_HASH_DOMAIN,
    PHASE18_OUTPUT_SCHEMA_VERSION,
    PHASE18_PHASE16_STEP2_SHA256,
    PHASE18_PHASE17_ARTIFACT_ID,
    PHASE18_PHASE17_ARTIFACT_SHA256,
    PHASE18_PHASE17_CANDIDATE_GROUPS_MANIFEST_SHA256,
    PHASE18_PHASE17_INVENTORY_SHA256,
    PHASE18_PHASE17_POLICY_SHA256,
    PHASE18_PHASE17_STEPS_MANIFEST_SHA256,
    PHASE18_POLICY_ID,
    PHASE18_POLICY_SHA256,
    PHASE18_PRODUCT_ROWS,
    PHASE18_REVIEW_MANIFEST_HASH_DOMAIN,
    PHASE18_SOURCE_HASH_DOMAIN,
    PHASE18_SOURCE_ROWS,
    PHASE18_SOURCE_SCHEMA_VERSION,
    PHASE18_SOURCES_MANIFEST_HASH_DOMAIN,
    PHASE18_STEP_CODES,
    PHASE18_STEP_HASH_DOMAIN,
    PHASE18_STEP_PREREQUISITES,
    PHASE18_STEP_REASONS,
    PHASE18_STEP_REQUIRED_OUTPUTS,
    PHASE18_STEP_REQUIRED_PRIOR_EVIDENCE,
    PHASE18_STEP_SCHEMA_VERSION,
    PHASE18_STEP_STATES,
    PHASE18_STEPS_MANIFEST_HASH_DOMAIN,
    canonicalize,
    domain_sha256,
    identity,
)

SHA256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
GitSHA = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]
ClosedText = Annotated[str, StringConstraints(min_length=1, max_length=1200)]
Identifier = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]{0,127}$")]
HttpsCitation = Annotated[str, StringConstraints(pattern=r"^https://[^\s]+$", max_length=500)]
ReviewTimestamp = Annotated[
    str,
    StringConstraints(pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{7}Z$"),
]
PublisherDate = Annotated[str, StringConstraints(pattern=r"^(?:UNSTATED|\d{4}-\d{2}-\d{2})$")]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")


class FamilyARightsReviewOutcome(StrEnum):
    BLOCKED = "BLOCKED"


class AggregateRightsConclusion(StrEnum):
    BLOCKED_NO_OPERATIONAL_SELECTION = "BLOCKED_NO_OPERATIONAL_SELECTION"


class RightsStatus(StrEnum):
    ALLOWED_PUBLIC = "ALLOWED_PUBLIC"
    CONDITIONAL_ACCOUNT_LICENSE = "CONDITIONAL_ACCOUNT_LICENSE"
    PRIVATE_LICENSE_REQUIRED = "PRIVATE_LICENSE_REQUIRED"
    PROHIBITED_PUBLIC_TERMS = "PROHIBITED_PUBLIC_TERMS"
    UNPROVEN = "UNPROVEN"


class ProductRightsConclusion(StrEnum):
    BLOCKED_STANDARD_TERMS_DO_NOT_GRANT_PERSISTENT_DATABASE_RIGHTS = (
        "BLOCKED_STANDARD_TERMS_DO_NOT_GRANT_PERSISTENT_DATABASE_RIGHTS"
    )
    BLOCKED_ADDON_THIRD_PARTY_AND_PERSISTENCE_RIGHTS_UNPROVEN = (
        "BLOCKED_ADDON_THIRD_PARTY_AND_PERSISTENCE_RIGHTS_UNPROVEN"
    )
    BLOCKED_ENTITLEMENT_CONFLICT_AND_PERSISTENCE_RIGHTS_UNPROVEN = (
        "BLOCKED_ENTITLEMENT_CONFLICT_AND_PERSISTENCE_RIGHTS_UNPROVEN"
    )
    BLOCKED_PRODUCT_LICENSE_RIGHTS_UNAVAILABLE = "BLOCKED_PRODUCT_LICENSE_RIGHTS_UNAVAILABLE"
    BLOCKED_DUAL_PRODUCT_LICENSE_RIGHTS_UNAVAILABLE = (
        "BLOCKED_DUAL_PRODUCT_LICENSE_RIGHTS_UNAVAILABLE"
    )
    RIGHTS_SUPPORTED_PUBLIC_POLICY_FITNESS_UNPROVEN = (
        "RIGHTS_SUPPORTED_PUBLIC_POLICY_FITNESS_UNPROVEN"
    )
    INELIGIBLE_CURRENT_TERMS_PROHIBIT_PERSISTENCE_AND_SOFTWARE_MODEL_USE = (
        "INELIGIBLE_CURRENT_TERMS_PROHIBIT_PERSISTENCE_AND_SOFTWARE_MODEL_USE"
    )
    BLOCKED_PRODUCT_VENUE_AND_NONDISPLAY_RIGHTS_UNAVAILABLE = (
        "BLOCKED_PRODUCT_VENUE_AND_NONDISPLAY_RIGHTS_UNAVAILABLE"
    )


class FamilyAProductCode(StrEnum):
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


PHASE18_PRODUCT_ORDER = tuple(FamilyAProductCode)


class PublicTermsSourceCode(StrEnum):
    TIINGO_TERMS_OF_USE = "TIINGO_TERMS_OF_USE"
    TIINGO_GENERAL_API_DOCUMENTATION = "TIINGO_GENERAL_API_DOCUMENTATION"
    TIINGO_API_PRICING = "TIINGO_API_PRICING"
    TIINGO_EOD_DOCUMENTATION = "TIINGO_EOD_DOCUMENTATION"
    TIINGO_FUNDAMENTALS_DOCUMENTATION = "TIINGO_FUNDAMENTALS_DOCUMENTATION"
    TIINGO_DIVIDEND_DOCUMENTATION = "TIINGO_DIVIDEND_DOCUMENTATION"
    TIINGO_SPLIT_DOCUMENTATION = "TIINGO_SPLIT_DOCUMENTATION"
    MORNINGSTAR_WEBSITE_TERMS = "MORNINGSTAR_WEBSITE_TERMS"
    MORNINGSTAR_CRSP_DATA_ACCESS = "MORNINGSTAR_CRSP_DATA_ACCESS"
    MORNINGSTAR_CRSP_US_STOCK_PRODUCT = "MORNINGSTAR_CRSP_US_STOCK_PRODUCT"
    MORNINGSTAR_CCM_PRODUCT = "MORNINGSTAR_CCM_PRODUCT"
    SEC_PRIVACY_AND_DISSEMINATION = "SEC_PRIVACY_AND_DISSEMINATION"
    SEC_WEBMASTER_REUSE_FAQ = "SEC_WEBMASTER_REUSE_FAQ"
    SEC_EDGAR_APIS = "SEC_EDGAR_APIS"
    SEC_DEVELOPER_RESOURCES = "SEC_DEVELOPER_RESOURCES"
    SEC_ACCESSING_EDGAR = "SEC_ACCESSING_EDGAR"
    FRED_TERMS = "FRED_TERMS"
    FRED_API_OVERVIEW = "FRED_API_OVERVIEW"
    FRED_REALTIME_PERIODS = "FRED_REALTIME_PERIODS"
    FRED_SERIES_VINTAGE_DATES = "FRED_SERIES_VINTAGE_DATES"
    LSEG_TICK_HISTORY = "LSEG_TICK_HISTORY"
    LSEG_DATA_REDISTRIBUTION = "LSEG_DATA_REDISTRIBUTION"
    LSEG_WEBSITE_TERMS = "LSEG_WEBSITE_TERMS"
    LSEG_NONDISPLAY_DERIVED_GUIDANCE = "LSEG_NONDISPLAY_DERIVED_GUIDANCE"


PHASE18_SOURCE_ORDER = tuple(PublicTermsSourceCode)


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


PHASE18_STEP_ORDER = tuple(FamilyASourcePlanStepCode)


class FamilyASourcePlanStepState(StrEnum):
    OUTPUT_FROZEN = "OUTPUT_FROZEN"
    NOT_STARTED = "NOT_STARTED"


class FamilyASourcePlanStepReason(StrEnum):
    INVENTORY_OUTPUT_INHERITED_AND_FROZEN = "inventory_output_inherited_and_frozen"
    BLOCKING_RIGHTS_REVIEW_OUTPUTS_FROZEN_NO_OPERATIONAL_CLEARANCE = (
        "blocking_rights_review_outputs_frozen_no_operational_clearance"
    )
    PREREQUISITE_NOT_SATISFIED = "prerequisite_not_satisfied"


class PublicTermsSource(StrictModel):
    schema_version: str
    ordinal: Annotated[int, Field(ge=1, le=24)]
    code: PublicTermsSourceCode
    official_title: ClosedText
    publisher: ClosedText
    official_url: HttpsCitation
    applies_to_product_codes: tuple[FamilyAProductCode, ...]
    publisher_last_updated: PublisherDate
    locator: ClosedText
    conservative_fact: ClosedText
    reviewed_at_utc: ReviewTimestamp
    public_metadata_only: bool
    official_https_citation: bool
    terms_body_persisted: bool
    remote_source_response_body_persisted: bool
    source_content_bytes_captured: bool
    content_byte_authenticity_proven: bool
    account_specific: bool
    revalidation_required: bool
    source_sha256: SHA256

    @model_validator(mode="after")
    def validate_frozen_source(self) -> Self:
        row = PHASE18_SOURCE_ROWS[self.ordinal - 1]
        expected_payload = {
            "schema_version": PHASE18_SOURCE_SCHEMA_VERSION,
            "ordinal": self.ordinal,
            "code": row[0],
            "official_title": row[1],
            "publisher": row[2],
            "official_url": row[3],
            "applies_to_product_codes": row[4],
            "publisher_last_updated": row[5],
            "locator": row[6],
            "conservative_fact": row[7],
            "reviewed_at_utc": row[8],
            "public_metadata_only": True,
            "official_https_citation": True,
            "terms_body_persisted": False,
            "remote_source_response_body_persisted": False,
            "source_content_bytes_captured": False,
            "content_byte_authenticity_proven": False,
            "account_specific": False,
            "revalidation_required": True,
        }
        actual = self.model_dump(mode="python", exclude={"source_sha256"})
        if canonicalize(actual) != canonicalize(expected_payload):
            raise ValueError("public-terms source does not match the frozen review catalog")
        if self.source_sha256 != domain_sha256(PHASE18_SOURCE_HASH_DOMAIN, expected_payload):
            raise ValueError("public-terms source hash mismatch")
        return self


class ProductRightsFinding(StrictModel):
    schema_version: str
    ordinal: Annotated[int, Field(ge=1, le=9)]
    product_code: FamilyAProductCode
    phase17_product_sha256: SHA256
    source_codes: tuple[PublicTermsSourceCode, ...]
    storage: RightsStatus
    non_display_internal_use: RightsStatus
    derived_data: RightsStatus
    retention: RightsStatus
    redistribution: RightsStatus
    revocation_currentness: RightsStatus
    delivery: RightsStatus
    entitlement: RightsStatus
    conclusion: ProductRightsConclusion
    conservative_finding: ClosedText
    public_metadata_review_only: bool
    operational_use_cleared: bool
    entitlement_verified: bool
    executed_license_reviewed: bool
    legal_opinion_obtained: bool
    revalidation_required: bool
    finding_sha256: SHA256

    @model_validator(mode="after")
    def validate_frozen_finding(self) -> Self:
        row = PHASE18_PRODUCT_ROWS[self.ordinal - 1]
        expected_payload = {
            "schema_version": PHASE18_FINDING_SCHEMA_VERSION,
            "ordinal": self.ordinal,
            "product_code": row[0],
            "phase17_product_sha256": row[1],
            "source_codes": row[2],
            "storage": row[3],
            "non_display_internal_use": row[4],
            "derived_data": row[5],
            "retention": row[6],
            "redistribution": row[7],
            "revocation_currentness": row[8],
            "delivery": row[9],
            "entitlement": row[10],
            "conclusion": row[11],
            "conservative_finding": row[12],
            "public_metadata_review_only": True,
            "operational_use_cleared": False,
            "entitlement_verified": False,
            "executed_license_reviewed": False,
            "legal_opinion_obtained": False,
            "revalidation_required": True,
        }
        actual = self.model_dump(mode="python", exclude={"finding_sha256"})
        if canonicalize(actual) != canonicalize(expected_payload):
            raise ValueError("product rights finding drifted from the frozen review")
        if self.finding_sha256 != domain_sha256(PHASE18_FINDING_HASH_DOMAIN, expected_payload):
            raise ValueError("product rights finding hash mismatch")
        return self


class FamilyARightsReviewOutput(StrictModel):
    schema_version: str
    name: Identifier
    sha256: SHA256
    output_sha256: SHA256

    @model_validator(mode="after")
    def validate_output_hash(self) -> Self:
        payload = self.model_dump(mode="python", exclude={"output_sha256"})
        if self.schema_version != PHASE18_OUTPUT_SCHEMA_VERSION:
            raise ValueError("output schema mismatch")
        if self.output_sha256 != domain_sha256(PHASE18_OUTPUT_HASH_DOMAIN, payload):
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
    produced_outputs: tuple[FamilyARightsReviewOutput, ...]
    external_action_authorized: bool
    step_sha256: SHA256

    @model_validator(mode="after")
    def validate_frozen_step(self) -> Self:
        index = self.ordinal - 1
        expected_payload = {
            "schema_version": PHASE18_STEP_SCHEMA_VERSION,
            "ordinal": self.ordinal,
            "code": PHASE18_STEP_CODES[index],
            "state": PHASE18_STEP_STATES[index],
            "reason_code": PHASE18_STEP_REASONS[index],
            "prerequisite_codes": PHASE18_STEP_PREREQUISITES[index],
            "required_prior_evidence": PHASE18_STEP_REQUIRED_PRIOR_EVIDENCE[index],
            "required_outputs": PHASE18_STEP_REQUIRED_OUTPUTS[index],
            "produced_outputs": self.produced_outputs,
            "external_action_authorized": False,
        }
        names = tuple(item.name for item in self.produced_outputs)
        if index == 0 and names != ("candidate_product_inventory_sha256",):
            raise ValueError("Step 1 must retain the sole inherited inventory output")
        if index == 1 and names != (
            "independent_rights_review_sha256",
            "rights_currentness_sha256",
        ):
            raise ValueError("Step 2 must freeze exactly its two required review outputs")
        if index > 1 and self.produced_outputs:
            raise ValueError("unstarted later steps cannot contain output evidence")
        actual = self.model_dump(mode="python", exclude={"step_sha256"})
        if canonicalize(actual) != canonicalize(expected_payload):
            raise ValueError("source-plan step evidence drifted")
        if self.step_sha256 != domain_sha256(PHASE18_STEP_HASH_DOMAIN, expected_payload):
            raise ValueError("source-plan step hash mismatch")
        return self


def terms_sources_manifest_sha256(sources: tuple[PublicTermsSource, ...]) -> str:
    return domain_sha256(
        PHASE18_SOURCES_MANIFEST_HASH_DOMAIN,
        tuple(item.source_sha256 for item in sources),
    )


def independent_rights_review_sha256(
    sources_manifest_sha256: str,
    findings: tuple[ProductRightsFinding, ...],
) -> str:
    return domain_sha256(
        PHASE18_REVIEW_MANIFEST_HASH_DOMAIN,
        {
            "terms_sources_manifest_sha256": sources_manifest_sha256,
            "finding_sha256s": tuple(item.finding_sha256 for item in findings),
        },
    )


def rights_currentness_sha256(sources_manifest_sha256: str) -> str:
    return domain_sha256(
        PHASE18_CURRENTNESS_HASH_DOMAIN,
        {
            "terms_sources_manifest_sha256": sources_manifest_sha256,
            "reviewed_at_utc": PHASE18_FROZEN_AT_UTC,
            "currentness": "REVIEW_SNAPSHOT_ONLY",
            "rights_currentness_guaranteed": False,
            "operational_use_cleared": False,
            "revalidation_required_before_external_action": True,
        },
    )


def steps_manifest_sha256(steps: tuple[FamilyASourcePlanStepEvidence, ...]) -> str:
    return domain_sha256(
        PHASE18_STEPS_MANIFEST_HASH_DOMAIN,
        tuple(item.step_sha256 for item in steps),
    )


class FamilyACurrentUseRightsReview(StrictModel):
    schema_version: str
    artifact_id: UUID
    artifact_sha256: SHA256
    policy_id: str
    policy_sha256: SHA256
    accepted_phase17_commit_sha: GitSHA
    accepted_phase17_tree_sha: GitSHA
    phase17_artifact_id: UUID
    phase17_artifact_sha256: SHA256
    phase17_policy_sha256: SHA256
    phase17_candidate_product_inventory_sha256: SHA256
    phase17_candidate_groups_manifest_sha256: SHA256
    phase17_steps_manifest_sha256: SHA256
    phase16_step2_sha256: SHA256
    family: str
    frozen_at_utc: ReviewTimestamp
    outcome: FamilyARightsReviewOutcome
    aggregate_conclusion: AggregateRightsConclusion
    block_reason: ClosedText
    terms_sources_manifest_sha256: SHA256
    independent_rights_review_sha256: SHA256
    rights_currentness_sha256: SHA256
    steps_manifest_sha256: SHA256
    terms_sources: tuple[PublicTermsSource, ...]
    product_rights_findings: tuple[ProductRightsFinding, ...]
    source_plan_steps: tuple[FamilyASourcePlanStepEvidence, ...]
    metadata_only: bool
    official_public_terms_review_performed: bool
    official_public_documentation_access_performed: bool
    independent_technical_rights_review_performed: bool
    official_citations_inert: bool
    review_snapshot_only: bool
    runtime_network_disabled: bool
    revalidation_required_before_external_action: bool
    legal_opinion_obtained: bool
    independent_legal_counsel_reviewed: bool
    provider_or_counsel_attestation_obtained: bool
    executed_license_reviewed: bool
    account_specific_terms_reviewed: bool
    terms_body_persisted: bool
    external_document_persisted: bool
    rights_currentness_guaranteed: bool
    operational_use_cleared: bool
    storage_rights_cleared: bool
    non_display_rights_cleared: bool
    derived_data_rights_cleared: bool
    retention_rights_cleared: bool
    redistribution_rights_cleared: bool
    delivery_rights_cleared: bool
    entitlement_rights_cleared: bool
    revocation_status_verified: bool
    operational_external_request_performed: bool
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
    def validate_closed_review(self) -> Self:
        identity_values = (
            self.schema_version == PHASE18_ARTIFACT_SCHEMA_VERSION,
            self.artifact_id == identity(PHASE18_POLICY_SHA256),
            self.policy_id == PHASE18_POLICY_ID,
            self.policy_sha256 == PHASE18_POLICY_SHA256,
            self.accepted_phase17_commit_sha == PHASE18_ACCEPTED_PHASE17_COMMIT_SHA,
            self.accepted_phase17_tree_sha == PHASE18_ACCEPTED_PHASE17_TREE_SHA,
            str(self.phase17_artifact_id) == PHASE18_PHASE17_ARTIFACT_ID,
            self.phase17_artifact_sha256 == PHASE18_PHASE17_ARTIFACT_SHA256,
            self.phase17_policy_sha256 == PHASE18_PHASE17_POLICY_SHA256,
            self.phase17_candidate_product_inventory_sha256 == PHASE18_PHASE17_INVENTORY_SHA256,
            self.phase17_candidate_groups_manifest_sha256
            == PHASE18_PHASE17_CANDIDATE_GROUPS_MANIFEST_SHA256,
            self.phase17_steps_manifest_sha256 == PHASE18_PHASE17_STEPS_MANIFEST_SHA256,
            self.phase16_step2_sha256 == PHASE18_PHASE16_STEP2_SHA256,
            self.family == PHASE18_FAMILY,
            self.frozen_at_utc == PHASE18_FROZEN_AT_UTC,
            self.outcome is FamilyARightsReviewOutcome.BLOCKED,
            self.aggregate_conclusion.value == PHASE18_AGGREGATE_CONCLUSION,
            self.block_reason == PHASE18_BLOCK_REASON,
            self.disclaimer == PHASE18_DISCLAIMER,
        )
        if not all(identity_values):
            raise ValueError("rights review identity or blocked boundary drifted")
        if tuple(item.code for item in self.terms_sources) != PHASE18_SOURCE_ORDER:
            raise ValueError("public-terms source registry or order drifted")
        if (
            tuple(item.product_code for item in self.product_rights_findings)
            != PHASE18_PRODUCT_ORDER
        ):
            raise ValueError("product rights registry or order drifted")
        if tuple(item.code for item in self.source_plan_steps) != PHASE18_STEP_ORDER:
            raise ValueError("source-plan step registry or order drifted")
        sources_manifest = terms_sources_manifest_sha256(self.terms_sources)
        if self.terms_sources_manifest_sha256 != sources_manifest:
            raise ValueError("public-terms sources manifest mismatch")
        review_hash = independent_rights_review_sha256(
            sources_manifest,
            self.product_rights_findings,
        )
        if self.independent_rights_review_sha256 != review_hash:
            raise ValueError("independent rights review manifest mismatch")
        currentness_hash = rights_currentness_sha256(sources_manifest)
        if self.rights_currentness_sha256 != currentness_hash:
            raise ValueError("rights currentness snapshot mismatch")
        if self.steps_manifest_sha256 != steps_manifest_sha256(self.source_plan_steps):
            raise ValueError("source-plan steps manifest mismatch")
        first_outputs = self.source_plan_steps[0].produced_outputs
        second_outputs = self.source_plan_steps[1].produced_outputs
        if len(first_outputs) != 1 or first_outputs[0].sha256 != PHASE18_PHASE17_INVENTORY_SHA256:
            raise ValueError("Step 1 no longer binds the accepted Phase 17 inventory")
        if len(second_outputs) != 2 or tuple(item.sha256 for item in second_outputs) != (
            review_hash,
            currentness_hash,
        ):
            raise ValueError("Step 2 outputs do not bind the rights review and currentness hashes")
        if any(item.produced_outputs for item in self.source_plan_steps[2:]):
            raise ValueError("later source-plan step unexpectedly produced output evidence")
        rendered = self.model_dump(mode="python")
        for field, expected in PHASE18_BOUNDARY_VALUES.items():
            if rendered[field] is not expected:
                raise ValueError(f"rights review unexpectedly changed {field}")
        preimage = self.model_dump(mode="python", exclude={"artifact_sha256"})
        if self.artifact_sha256 != domain_sha256(PHASE18_ARTIFACT_HASH_DOMAIN, preimage):
            raise ValueError("rights review artifact hash mismatch")
        return self


__all__ = [
    "PHASE18_PRODUCT_ORDER",
    "PHASE18_SOURCE_ORDER",
    "PHASE18_STEP_ORDER",
    "AggregateRightsConclusion",
    "FamilyACurrentUseRightsReview",
    "FamilyAProductCode",
    "FamilyARightsReviewOutcome",
    "FamilyARightsReviewOutput",
    "FamilyASourcePlanStepCode",
    "FamilyASourcePlanStepEvidence",
    "FamilyASourcePlanStepReason",
    "FamilyASourcePlanStepState",
    "ProductRightsConclusion",
    "ProductRightsFinding",
    "PublicTermsSource",
    "PublicTermsSourceCode",
    "RightsStatus",
    "independent_rights_review_sha256",
    "rights_currentness_sha256",
    "steps_manifest_sha256",
    "terms_sources_manifest_sha256",
]
