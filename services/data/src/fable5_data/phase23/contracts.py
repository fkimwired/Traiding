"""Strict contracts for the Phase 23 RTDSM current-use-rights review."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from fable5_data.phase23 import canonical as c

SHA256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
GitSHA = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]
ClosedText = Annotated[str, StringConstraints(min_length=1, max_length=1200)]
HttpsCitation = Annotated[str, StringConstraints(pattern=r"^https://[^\s]+$", max_length=600)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")


class ReviewOutcome(StrEnum):
    BLOCKED = "BLOCKED"


class ReviewState(StrEnum):
    PUBLIC_TERMS_RIGHTS_REVIEW_FROZEN = "PUBLIC_TERMS_RIGHTS_REVIEW_FROZEN"


class RightsConclusion(StrEnum):
    BLOCKED_PUBLIC_TERMS_INSUFFICIENT_FOR_PERSISTENT_AUTOMATED_MODEL_USE = (
        "BLOCKED_PUBLIC_TERMS_INSUFFICIENT_FOR_PERSISTENT_AUTOMATED_MODEL_USE"
    )


class SourceCode(StrEnum):
    PHILADELPHIA_FED_ONLINE_TERMS = "PHILADELPHIA_FED_ONLINE_TERMS"
    PHILADELPHIA_FED_RTDSM_OVERVIEW = "PHILADELPHIA_FED_RTDSM_OVERVIEW"
    PHILADELPHIA_FED_RTDSM_CHANGES = "PHILADELPHIA_FED_RTDSM_CHANGES"


class RightsStatus(StrEnum):
    EXPRESSLY_PERMITTED_RESEARCH_PURPOSE_ONLY = "EXPRESSLY_PERMITTED_RESEARCH_PURPOSE_ONLY"
    NOT_EXPRESSLY_ADDRESSED = "NOT_EXPRESSLY_ADDRESSED"
    OWNER_PERMISSION_REQUIRED_WHEN_COPYRIGHTED = "OWNER_PERMISSION_REQUIRED_WHEN_COPYRIGHTED"
    CHANGE_WITHOUT_NOTICE_REVALIDATION_REQUIRED = "CHANGE_WITHOUT_NOTICE_REVALIDATION_REQUIRED"
    EXCESSIVE_ACCESS_PROHIBITED = "EXCESSIVE_ACCESS_PROHIBITED"


class RequirementCode(StrEnum):
    INDEPENDENT_CURRENT_USE_RIGHTS_AND_REVOCATION = "INDEPENDENT_CURRENT_USE_RIGHTS_AND_REVOCATION"
    EXACT_SERIES_DELIVERY_SCHEMA_COVERAGE_AND_AVAILABILITY = (
        "EXACT_SERIES_DELIVERY_SCHEMA_COVERAGE_AND_AVAILABILITY"
    )
    BLS_RELEASE_ARCHIVE_RECONCILIATION = "BLS_RELEASE_ARCHIVE_RECONCILIATION"
    EXPLICIT_OPERATIONAL_SOURCE_PRODUCT_COMPOSITION = (
        "EXPLICIT_OPERATIONAL_SOURCE_PRODUCT_COMPOSITION"
    )


class RequirementState(StrEnum):
    OUTPUT_FROZEN_BLOCKED = "OUTPUT_FROZEN_BLOCKED"
    NOT_STARTED = "NOT_STARTED"
    BLOCKED = "BLOCKED"


def _manifest(domain: str, rows: tuple[BaseModel, ...], field: str) -> str:
    return c.domain_sha256(domain, tuple(getattr(row, field) for row in rows))


class PublicTermsSource(StrictModel):
    schema_version: str
    ordinal: Annotated[int, Field(ge=1, le=3)]
    code: SourceCode
    title: ClosedText
    publisher: ClosedText
    url: HttpsCitation
    publisher_last_updated: date
    locator: ClosedText
    conservative_fact: ClosedText
    reviewed_on: date
    official_source: bool
    citation_inert: bool
    terms_body_persisted: bool
    remote_response_body_persisted: bool
    source_content_bytes_captured: bool
    revalidation_required: bool
    source_sha256: SHA256

    @model_validator(mode="after")
    def validate_frozen_source(self) -> Self:
        row = c.PHASE23_SOURCE_ROWS[self.ordinal - 1]
        expected = {
            "schema_version": c.PHASE23_SOURCE_SCHEMA_VERSION,
            "ordinal": self.ordinal,
            "code": row[0],
            "title": row[1],
            "publisher": row[2],
            "url": row[3],
            "publisher_last_updated": row[4],
            "locator": row[5],
            "conservative_fact": row[6],
            "reviewed_on": c.PHASE23_REVIEWED_ON,
            **dict(c.PHASE23_SOURCE_INVARIANTS),
        }
        actual = self.model_dump(mode="python", exclude={"source_sha256"})
        if c.canonicalize(actual) != c.canonicalize(expected):
            raise ValueError("public terms source drifted")
        if self.source_sha256 != c.domain_sha256(c.PHASE23_SOURCE_HASH_DOMAIN, expected):
            raise ValueError("public terms source hash mismatch")
        return self


class RTDSMRightsFinding(StrictModel):
    schema_version: str
    ordinal: Annotated[int, Field(ge=1, le=1)]
    product_code: str
    phase22_product_sha256: SHA256
    source_codes: tuple[SourceCode, ...]
    research_purpose: RightsStatus
    persistent_storage: RightsStatus
    automated_model_internal_use: RightsStatus
    derived_data: RightsStatus
    retention_deletion: RightsStatus
    redistribution: RightsStatus
    attribution: RightsStatus
    third_party_content: RightsStatus
    revocation_currentness: RightsStatus
    access_load: RightsStatus
    conclusion: RightsConclusion
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
        expected = {
            "schema_version": c.PHASE23_FINDING_SCHEMA_VERSION,
            "ordinal": 1,
            "product_code": c.PHASE23_PRODUCT_CODE,
            "phase22_product_sha256": c.PHASE23_PHASE22_PRODUCT_SHA256,
            "source_codes": tuple(row[0] for row in c.PHASE23_SOURCE_ROWS),
            **dict(c.PHASE23_FINDING_VALUES),
        }
        actual = self.model_dump(mode="python", exclude={"finding_sha256"})
        if c.canonicalize(actual) != c.canonicalize(expected):
            raise ValueError("RTDSM rights finding drifted")
        if self.finding_sha256 != c.domain_sha256(c.PHASE23_FINDING_HASH_DOMAIN, expected):
            raise ValueError("RTDSM rights finding hash mismatch")
        return self


class FutureRequirementStatus(StrictModel):
    schema_version: str
    ordinal: Annotated[int, Field(ge=1, le=4)]
    code: RequirementCode
    phase22_requirement_sha256: SHA256
    state: RequirementState
    definition: ClosedText
    review_output_produced: bool
    external_action_authorized: bool
    satisfied: bool
    requirement_sha256: SHA256

    @model_validator(mode="after")
    def validate_frozen_requirement(self) -> Self:
        row = c.PHASE23_REQUIREMENT_ROWS[self.ordinal - 1]
        expected = {
            "schema_version": c.PHASE23_REQUIREMENT_SCHEMA_VERSION,
            "ordinal": self.ordinal,
            "code": row[0],
            "phase22_requirement_sha256": row[1],
            "state": row[2],
            "definition": row[3],
            "review_output_produced": row[4],
            **dict(c.PHASE23_REQUIREMENT_INVARIANTS),
        }
        actual = self.model_dump(mode="python", exclude={"requirement_sha256"})
        if c.canonicalize(actual) != c.canonicalize(expected):
            raise ValueError("future requirement status drifted")
        if self.requirement_sha256 != c.domain_sha256(c.PHASE23_REQUIREMENT_HASH_DOMAIN, expected):
            raise ValueError("future requirement status hash mismatch")
        return self


def sources_manifest_sha256(rows: tuple[PublicTermsSource, ...]) -> str:
    return _manifest(c.PHASE23_SOURCES_MANIFEST_HASH_DOMAIN, rows, "source_sha256")


def findings_manifest_sha256(rows: tuple[RTDSMRightsFinding, ...]) -> str:
    return _manifest(c.PHASE23_FINDINGS_MANIFEST_HASH_DOMAIN, rows, "finding_sha256")


def requirements_manifest_sha256(rows: tuple[FutureRequirementStatus, ...]) -> str:
    return _manifest(c.PHASE23_REQUIREMENTS_MANIFEST_HASH_DOMAIN, rows, "requirement_sha256")


class FamilyARTDSMCurrentUseRightsReview(StrictModel):
    schema_version: str
    artifact_id: UUID
    artifact_sha256: SHA256
    policy_id: str
    policy_sha256: SHA256
    accepted_phase22_commit_sha: GitSHA
    accepted_phase22_tree_sha: GitSHA
    phase22_merge_commit_sha: GitSHA
    phase22_artifact_id: UUID
    phase22_artifact_sha256: SHA256
    phase22_policy_sha256: SHA256
    phase22_sources_manifest_sha256: SHA256
    phase22_products_manifest_sha256: SHA256
    phase22_requirements_manifest_sha256: SHA256
    product_code: str
    phase22_product_sha256: SHA256
    family: str
    frozen_at_utc: datetime
    reviewed_on: date
    outcome: ReviewOutcome
    review_state: ReviewState
    aggregate_conclusion: RightsConclusion
    block_reason: ClosedText
    public_terms_sources_manifest_sha256: SHA256
    rights_findings_manifest_sha256: SHA256
    future_requirements_manifest_sha256: SHA256
    public_terms_sources: tuple[PublicTermsSource, ...]
    rights_findings: tuple[RTDSMRightsFinding, ...]
    future_requirements: tuple[FutureRequirementStatus, ...]
    metadata_only: bool
    public_terms_review_only: bool
    runtime_network_disabled: bool
    official_public_documentation_review_performed: bool
    phase22_artifact_unchanged: bool
    phase22_candidate_unchanged: bool
    technical_rights_review_performed: bool
    legal_opinion_obtained: bool
    rights_granted: bool
    rights_verified: bool
    rights_currentness_guaranteed: bool
    product_selected: bool
    delivery_selected: bool
    credentials_loaded: bool
    account_verified: bool
    operational_external_request_performed: bool
    external_data_capture_authorized: bool
    provider_payload_persisted: bool
    data_fitness_review_performed: bool
    bls_reconciliation_performed: bool
    research_ingestion_authorized: bool
    research_executed: bool
    performance_computed: bool
    strategy_promotion_authorized: bool
    execution_authorized: bool
    order_submission_authorized: bool
    live_path_absent: bool
    no_personalized_investment_advice: bool
    no_real_performance_claimed: bool
    disclaimer: ClosedText

    @model_validator(mode="after")
    def validate_frozen_artifact(self) -> Self:
        dumped = self.model_dump(mode="python")
        expected_scalars = {
            "schema_version": c.PHASE23_ARTIFACT_SCHEMA_VERSION,
            "artifact_id": c.identity(),
            "policy_id": c.PHASE23_POLICY_ID,
            "policy_sha256": c.PHASE23_POLICY_SHA256,
            "accepted_phase22_commit_sha": c.PHASE23_ACCEPTED_PHASE22_COMMIT_SHA,
            "accepted_phase22_tree_sha": c.PHASE23_ACCEPTED_PHASE22_TREE_SHA,
            "phase22_merge_commit_sha": c.PHASE23_PHASE22_MERGE_COMMIT_SHA,
            "phase22_artifact_id": c.PHASE23_PHASE22_ARTIFACT_ID,
            "phase22_artifact_sha256": c.PHASE23_PHASE22_ARTIFACT_SHA256,
            "phase22_policy_sha256": c.PHASE23_PHASE22_POLICY_SHA256,
            "phase22_sources_manifest_sha256": c.PHASE23_PHASE22_SOURCES_MANIFEST_SHA256,
            "phase22_products_manifest_sha256": c.PHASE23_PHASE22_PRODUCTS_MANIFEST_SHA256,
            "phase22_requirements_manifest_sha256": c.PHASE23_PHASE22_REQUIREMENTS_MANIFEST_SHA256,
            "product_code": c.PHASE23_PRODUCT_CODE,
            "phase22_product_sha256": c.PHASE23_PHASE22_PRODUCT_SHA256,
            "family": c.PHASE23_FAMILY,
            "frozen_at_utc": c.PHASE23_FROZEN_AT_UTC,
            "reviewed_on": c.PHASE23_REVIEWED_ON,
            "outcome": c.PHASE23_OUTCOME,
            "review_state": c.PHASE23_REVIEW_STATE,
            "aggregate_conclusion": c.PHASE23_AGGREGATE_CONCLUSION,
            "block_reason": c.PHASE23_BLOCK_REASON,
            "disclaimer": c.PHASE23_DISCLAIMER,
        }
        for field, expected in expected_scalars.items():
            if c.canonicalize(dumped[field]) != c.canonicalize(expected):
                raise ValueError(f"artifact scalar drifted: {field}")
        if tuple(row.code.value for row in self.public_terms_sources) != tuple(
            row[0] for row in c.PHASE23_SOURCE_ROWS
        ):
            raise ValueError("public terms source order drifted")
        if len(self.public_terms_sources) != 3 or len(self.rights_findings) != 1:
            raise ValueError("Phase 23 source or finding count drifted")
        if tuple(row.code.value for row in self.future_requirements) != tuple(
            row[0] for row in c.PHASE23_REQUIREMENT_ROWS
        ):
            raise ValueError("future requirement order drifted")
        if len(self.future_requirements) != 4:
            raise ValueError("future requirement count drifted")
        if self.public_terms_sources_manifest_sha256 != sources_manifest_sha256(
            self.public_terms_sources
        ):
            raise ValueError("public terms sources manifest mismatch")
        if self.rights_findings_manifest_sha256 != findings_manifest_sha256(self.rights_findings):
            raise ValueError("rights findings manifest mismatch")
        if self.future_requirements_manifest_sha256 != requirements_manifest_sha256(
            self.future_requirements
        ):
            raise ValueError("future requirements manifest mismatch")
        for field, expected in c.PHASE23_BOUNDARY_VALUES.items():
            if dumped[field] is not expected:
                raise ValueError(f"artifact boundary drifted: {field}")
        unhashed = self.model_dump(mode="python", exclude={"artifact_sha256"})
        if self.artifact_sha256 != c.domain_sha256(c.PHASE23_ARTIFACT_HASH_DOMAIN, unhashed):
            raise ValueError("artifact hash mismatch")
        return self


__all__ = [
    "FamilyARTDSMCurrentUseRightsReview",
    "FutureRequirementStatus",
    "PublicTermsSource",
    "RTDSMRightsFinding",
    "findings_manifest_sha256",
    "requirements_manifest_sha256",
    "sources_manifest_sha256",
]
