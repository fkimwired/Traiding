"""Strict contracts for the Phase 22 macro-vintage inventory amendment."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from fable5_data.phase22 import canonical as c

SHA256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
GitSHA = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]
ClosedText = Annotated[str, StringConstraints(min_length=1, max_length=1000)]
HttpsCitation = Annotated[str, StringConstraints(pattern=r"^https://[^\s]+$", max_length=600)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")


class AmendmentOutcome(StrEnum):
    BLOCKED = "BLOCKED"


class AmendmentState(StrEnum):
    CANDIDATE_INVENTORY_AMENDMENT_FROZEN = "CANDIDATE_INVENTORY_AMENDMENT_FROZEN"


class AmendmentConclusion(StrEnum):
    BLOCKED_AWAITING_CURRENT_RIGHTS_FITNESS_REVIEW_AND_EXPLICIT_OPERATIONAL_COMPOSITION = (
        "BLOCKED_AWAITING_CURRENT_RIGHTS_FITNESS_REVIEW_AND_EXPLICIT_OPERATIONAL_COMPOSITION"
    )


class OfficialSourceCode(StrEnum):
    PHILADELPHIA_FED_RTDSM_OVERVIEW = "PHILADELPHIA_FED_RTDSM_OVERVIEW"
    PHILADELPHIA_FED_RTDSM_PCPI = "PHILADELPHIA_FED_RTDSM_PCPI"
    PHILADELPHIA_FED_ONLINE_TERMS = "PHILADELPHIA_FED_ONLINE_TERMS"


class CandidateGroupCode(StrEnum):
    PHILADELPHIA_FED_RTDSM_MACRO_VINTAGES_CANDIDATE = (
        "PHILADELPHIA_FED_RTDSM_MACRO_VINTAGES_CANDIDATE"
    )


class CandidateProductCode(StrEnum):
    PHILADELPHIA_FED_REAL_TIME_DATA_SET_FOR_MACROECONOMISTS = (
        "PHILADELPHIA_FED_REAL_TIME_DATA_SET_FOR_MACROECONOMISTS"
    )


class CapabilityCode(StrEnum):
    MACRO_REGIME_INPUTS = "macro_regime_inputs"


class ReviewRoutingState(StrEnum):
    NAMED_FOR_INDEPENDENT_CURRENT_RIGHTS_AND_FITNESS_REVIEW = (
        "NAMED_FOR_INDEPENDENT_CURRENT_RIGHTS_AND_FITNESS_REVIEW"
    )


class EvidenceState(StrEnum):
    UNPROVEN = "UNPROVEN"
    NOT_REVIEWED = "NOT_REVIEWED"


class DeliverySurfaceState(StrEnum):
    DOCUMENTED_DOWNLOAD_SURFACE = "DOCUMENTED_DOWNLOAD_SURFACE"


class FutureRequirementCode(StrEnum):
    INDEPENDENT_CURRENT_USE_RIGHTS_AND_REVOCATION = "INDEPENDENT_CURRENT_USE_RIGHTS_AND_REVOCATION"
    EXACT_SERIES_DELIVERY_SCHEMA_COVERAGE_AND_AVAILABILITY = (
        "EXACT_SERIES_DELIVERY_SCHEMA_COVERAGE_AND_AVAILABILITY"
    )
    BLS_RELEASE_ARCHIVE_RECONCILIATION = "BLS_RELEASE_ARCHIVE_RECONCILIATION"
    EXPLICIT_OPERATIONAL_SOURCE_PRODUCT_COMPOSITION = (
        "EXPLICIT_OPERATIONAL_SOURCE_PRODUCT_COMPOSITION"
    )


class FutureRequirementState(StrEnum):
    NOT_STARTED = "NOT_STARTED"
    BLOCKED = "BLOCKED"


def _manifest(domain: str, rows: tuple[BaseModel, ...], hash_field: str) -> str:
    return c.domain_sha256(domain, tuple(getattr(row, hash_field) for row in rows))


class OfficialSourceCitation(StrictModel):
    schema_version: str
    ordinal: Annotated[int, Field(ge=1, le=3)]
    source_code: OfficialSourceCode
    title: ClosedText
    publisher: ClosedText
    url: HttpsCitation
    fact_scope: ClosedText
    reviewed_on: date
    official_source: bool
    citation_inert: bool
    remote_body_included: bool
    source_sha256: SHA256

    @model_validator(mode="after")
    def validate_frozen_source(self) -> Self:
        row = c.PHASE22_SOURCE_ROWS[self.ordinal - 1]
        expected = {
            "schema_version": c.PHASE22_SOURCE_SCHEMA_VERSION,
            "ordinal": self.ordinal,
            "source_code": row[0],
            "title": row[1],
            "publisher": row[2],
            "url": row[3],
            "fact_scope": row[4],
            "reviewed_on": c.PHASE22_REVIEWED_ON,
            **dict(c.PHASE22_SOURCE_INVARIANTS),
        }
        actual = self.model_dump(mode="python", exclude={"source_sha256"})
        if c.canonicalize(actual) != c.canonicalize(expected):
            raise ValueError("official source does not match its frozen row")
        if self.source_sha256 != c.domain_sha256(c.PHASE22_SOURCE_HASH_DOMAIN, expected):
            raise ValueError("official-source hash mismatch")
        return self


class CandidateGroupAmendment(StrictModel):
    schema_version: str
    ordinal: Annotated[int, Field(ge=1, le=1)]
    candidate_group_code: CandidateGroupCode
    product_codes: tuple[CandidateProductCode, ...]
    candidate_only: bool
    operationally_selected: bool
    ranked: bool
    group_sha256: SHA256

    @model_validator(mode="after")
    def validate_frozen_group(self) -> Self:
        row = c.PHASE22_CANDIDATE_GROUP_ROWS[self.ordinal - 1]
        expected = {
            "schema_version": c.PHASE22_GROUP_SCHEMA_VERSION,
            "ordinal": self.ordinal,
            "candidate_group_code": row[0],
            "product_codes": row[1],
            **dict(c.PHASE22_GROUP_INVARIANTS),
        }
        actual = self.model_dump(mode="python", exclude={"group_sha256"})
        if c.canonicalize(actual) != c.canonicalize(expected):
            raise ValueError("candidate group does not match its frozen amendment row")
        if self.group_sha256 != c.domain_sha256(c.PHASE22_GROUP_HASH_DOMAIN, expected):
            raise ValueError("candidate-group hash mismatch")
        return self


class MacroVintageCandidateProduct(StrictModel):
    schema_version: str
    ordinal: Annotated[int, Field(ge=1, le=1)]
    product_code: CandidateProductCode
    candidate_group_code: CandidateGroupCode
    official_name: ClosedText
    official_documentation_url: HttpsCitation
    official_fact: ClosedText
    capability_codes: tuple[CapabilityCode, ...]
    delivery_surface_state: DeliverySurfaceState
    source_codes: tuple[OfficialSourceCode, ...]
    candidate_only: bool
    review_routing_state: ReviewRoutingState
    operationally_selected: bool
    ranked: bool
    public_research_use_stated: bool
    entitlement_state: EvidenceState
    rights_state: EvidenceState
    fitness_state: EvidenceState
    persistent_storage_model_derived_retention_rights_reviewed: bool
    month_vintage_labels_are_exact_release_timestamps: bool
    bls_release_archive_reconciliation_required: bool
    coverage_proven: bool
    schema_proven: bool
    current_availability_proven: bool
    external_sample_qualified: bool
    product_sha256: SHA256

    @model_validator(mode="after")
    def validate_frozen_product(self) -> Self:
        row = c.PHASE22_PRODUCT_ROWS[self.ordinal - 1]
        expected = {
            "schema_version": c.PHASE22_PRODUCT_SCHEMA_VERSION,
            "ordinal": self.ordinal,
            "product_code": row[0],
            "candidate_group_code": row[1],
            "official_name": row[2],
            "official_documentation_url": row[3],
            "official_fact": row[4],
            "capability_codes": row[5],
            "delivery_surface_state": row[6],
            "source_codes": row[7],
            **dict(c.PHASE22_PRODUCT_INVARIANTS),
        }
        actual = self.model_dump(mode="python", exclude={"product_sha256"})
        if c.canonicalize(actual) != c.canonicalize(expected):
            raise ValueError("candidate product does not match its frozen amendment row")
        if self.product_sha256 != c.domain_sha256(c.PHASE22_PRODUCT_HASH_DOMAIN, expected):
            raise ValueError("candidate-product hash mismatch")
        return self


class FutureReviewRequirement(StrictModel):
    schema_version: str
    ordinal: Annotated[int, Field(ge=1, le=4)]
    code: FutureRequirementCode
    state: FutureRequirementState
    definition: ClosedText
    external_action_authorized: bool
    satisfied: bool
    requirement_sha256: SHA256

    @model_validator(mode="after")
    def validate_frozen_requirement(self) -> Self:
        row = c.PHASE22_REQUIREMENT_ROWS[self.ordinal - 1]
        expected = {
            "schema_version": c.PHASE22_REQUIREMENT_SCHEMA_VERSION,
            "ordinal": self.ordinal,
            "code": row[0],
            "state": row[1],
            "definition": row[2],
            **dict(c.PHASE22_REQUIREMENT_INVARIANTS),
        }
        actual = self.model_dump(mode="python", exclude={"requirement_sha256"})
        if c.canonicalize(actual) != c.canonicalize(expected):
            raise ValueError("future requirement does not match its frozen row")
        if self.requirement_sha256 != c.domain_sha256(c.PHASE22_REQUIREMENT_HASH_DOMAIN, expected):
            raise ValueError("future-requirement hash mismatch")
        return self


def sources_manifest_sha256(rows: tuple[OfficialSourceCitation, ...]) -> str:
    return _manifest(c.PHASE22_SOURCES_MANIFEST_HASH_DOMAIN, rows, "source_sha256")


def groups_manifest_sha256(rows: tuple[CandidateGroupAmendment, ...]) -> str:
    return _manifest(c.PHASE22_GROUPS_MANIFEST_HASH_DOMAIN, rows, "group_sha256")


def products_manifest_sha256(rows: tuple[MacroVintageCandidateProduct, ...]) -> str:
    return _manifest(c.PHASE22_PRODUCTS_MANIFEST_HASH_DOMAIN, rows, "product_sha256")


def requirements_manifest_sha256(rows: tuple[FutureReviewRequirement, ...]) -> str:
    return _manifest(c.PHASE22_REQUIREMENTS_MANIFEST_HASH_DOMAIN, rows, "requirement_sha256")


class FamilyAMacroVintageCandidateInventoryAmendment(StrictModel):
    schema_version: str
    artifact_id: UUID
    artifact_sha256: SHA256
    amendment_policy_id: str
    amendment_policy_sha256: SHA256
    accepted_phase21_commit_sha: GitSHA
    accepted_phase21_tree_sha: GitSHA
    phase21_artifact_id: UUID
    phase21_artifact_sha256: SHA256
    phase21_policy_sha256: SHA256
    phase21_candidate_groups_manifest_sha256: SHA256
    phase21_product_rights_manifest_sha256: SHA256
    phase21_capabilities_manifest_sha256: SHA256
    phase21_decision_fields_manifest_sha256: SHA256
    phase21_gates_manifest_sha256: SHA256
    phase21_rules_manifest_sha256: SHA256
    phase21_aggregate_conclusion: str
    phase21_base_candidate_group_count: Annotated[int, Field(ge=6, le=6)]
    phase21_base_product_count: Annotated[int, Field(ge=9, le=9)]
    inherited_fred_product_code: str
    inherited_fred_product_sha256: SHA256
    inherited_fred_rights_finding_sha256: SHA256
    inherited_fred_rights_conclusion: str
    family: str
    frozen_at_utc: datetime
    reviewed_on: date
    outcome: AmendmentOutcome
    amendment_state: AmendmentState
    aggregate_conclusion: AmendmentConclusion
    block_reason: ClosedText
    official_sources_manifest_sha256: SHA256
    candidate_groups_amendment_manifest_sha256: SHA256
    candidate_products_amendment_manifest_sha256: SHA256
    future_review_requirements_manifest_sha256: SHA256
    official_sources: tuple[OfficialSourceCitation, ...]
    candidate_group_amendments: tuple[CandidateGroupAmendment, ...]
    candidate_products: tuple[MacroVintageCandidateProduct, ...]
    future_review_requirements: tuple[FutureReviewRequirement, ...]
    metadata_only: bool
    candidate_inventory_amendment_only: bool
    runtime_network_disabled: bool
    official_public_documentation_review_performed: bool
    prior_candidate_inventory_unchanged: bool
    prior_rights_findings_unchanged: bool
    phase21_decision_requirements_unchanged: bool
    inherited_fred_finding_unchanged: bool
    composition_ranked: bool
    operational_source_product_composition_selected: bool
    selection_evidence_produced: bool
    source_selected: bool
    provider_selected: bool
    product_selected: bool
    delivery_selected: bool
    rights_review_performed: bool
    rights_granted: bool
    rights_verified: bool
    rights_currentness_guaranteed: bool
    credentials_loaded: bool
    account_verified: bool
    operational_external_request_performed: bool
    external_data_capture_authorized: bool
    provider_payload_persisted: bool
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
        expected_scalars = {
            "schema_version": c.PHASE22_ARTIFACT_SCHEMA_VERSION,
            "artifact_id": c.identity(),
            "amendment_policy_id": c.PHASE22_POLICY_ID,
            "amendment_policy_sha256": c.PHASE22_POLICY_SHA256,
            "accepted_phase21_commit_sha": c.PHASE22_ACCEPTED_PHASE21_COMMIT_SHA,
            "accepted_phase21_tree_sha": c.PHASE22_ACCEPTED_PHASE21_TREE_SHA,
            "phase21_artifact_id": c.PHASE22_PHASE21_ARTIFACT_ID,
            "phase21_artifact_sha256": c.PHASE22_PHASE21_ARTIFACT_SHA256,
            "phase21_policy_sha256": c.PHASE22_PHASE21_POLICY_SHA256,
            "phase21_candidate_groups_manifest_sha256": (
                c.PHASE22_PHASE21_CANDIDATE_GROUPS_MANIFEST_SHA256
            ),
            "phase21_product_rights_manifest_sha256": (
                c.PHASE22_PHASE21_PRODUCT_RIGHTS_MANIFEST_SHA256
            ),
            "phase21_capabilities_manifest_sha256": (
                c.PHASE22_PHASE21_CAPABILITIES_MANIFEST_SHA256
            ),
            "phase21_decision_fields_manifest_sha256": (
                c.PHASE22_PHASE21_DECISION_FIELDS_MANIFEST_SHA256
            ),
            "phase21_gates_manifest_sha256": c.PHASE22_PHASE21_GATES_MANIFEST_SHA256,
            "phase21_rules_manifest_sha256": c.PHASE22_PHASE21_RULES_MANIFEST_SHA256,
            "phase21_aggregate_conclusion": c.PHASE22_PHASE21_AGGREGATE_CONCLUSION,
            "phase21_base_candidate_group_count": c.PHASE22_PHASE21_BASE_CANDIDATE_GROUP_COUNT,
            "phase21_base_product_count": c.PHASE22_PHASE21_BASE_PRODUCT_COUNT,
            "inherited_fred_product_code": c.PHASE22_INHERITED_FRED_PRODUCT_CODE,
            "inherited_fred_product_sha256": c.PHASE22_INHERITED_FRED_PRODUCT_SHA256,
            "inherited_fred_rights_finding_sha256": (
                c.PHASE22_INHERITED_FRED_RIGHTS_FINDING_SHA256
            ),
            "inherited_fred_rights_conclusion": c.PHASE22_INHERITED_FRED_RIGHTS_CONCLUSION,
            "family": c.PHASE22_FAMILY,
            "frozen_at_utc": c.PHASE22_FROZEN_AT_UTC,
            "reviewed_on": c.PHASE22_REVIEWED_ON,
            "outcome": c.PHASE22_OUTCOME,
            "amendment_state": c.PHASE22_AMENDMENT_STATE,
            "aggregate_conclusion": c.PHASE22_AGGREGATE_CONCLUSION,
            "block_reason": c.PHASE22_BLOCK_REASON,
            "disclaimer": c.PHASE22_DISCLAIMER,
        }
        dumped = self.model_dump(mode="python")
        for field, expected in expected_scalars.items():
            if c.canonicalize(dumped[field]) != c.canonicalize(expected):
                raise ValueError(f"artifact scalar drifted: {field}")
        if tuple(row.source_code.value for row in self.official_sources) != tuple(
            row[0] for row in c.PHASE22_SOURCE_ROWS
        ):
            raise ValueError("official-source order drifted")
        if len(self.official_sources) != c.PHASE22_OFFICIAL_SOURCE_COUNT:
            raise ValueError("official-source count drifted")
        if tuple(
            row.candidate_group_code.value for row in self.candidate_group_amendments
        ) != tuple(row[0] for row in c.PHASE22_CANDIDATE_GROUP_ROWS):
            raise ValueError("candidate-group order drifted")
        if len(self.candidate_group_amendments) != c.PHASE22_CANDIDATE_GROUP_AMENDMENT_COUNT:
            raise ValueError("candidate-group amendment count drifted")
        if tuple(row.product_code.value for row in self.candidate_products) != tuple(
            row[0] for row in c.PHASE22_PRODUCT_ROWS
        ):
            raise ValueError("candidate-product order drifted")
        if len(self.candidate_products) != c.PHASE22_CANDIDATE_PRODUCT_COUNT:
            raise ValueError("candidate-product count drifted")
        if tuple(row.code.value for row in self.future_review_requirements) != tuple(
            row[0] for row in c.PHASE22_REQUIREMENT_ROWS
        ):
            raise ValueError("future-requirement order drifted")
        if len(self.future_review_requirements) != c.PHASE22_FUTURE_REVIEW_REQUIREMENT_COUNT:
            raise ValueError("future-review requirement count drifted")
        if self.official_sources_manifest_sha256 != sources_manifest_sha256(self.official_sources):
            raise ValueError("official-sources manifest mismatch")
        if self.candidate_groups_amendment_manifest_sha256 != groups_manifest_sha256(
            self.candidate_group_amendments
        ):
            raise ValueError("candidate-groups manifest mismatch")
        if self.candidate_products_amendment_manifest_sha256 != products_manifest_sha256(
            self.candidate_products
        ):
            raise ValueError("candidate-products manifest mismatch")
        if self.future_review_requirements_manifest_sha256 != requirements_manifest_sha256(
            self.future_review_requirements
        ):
            raise ValueError("future-requirements manifest mismatch")
        for field, expected in c.PHASE22_BOUNDARY_VALUES.items():
            if dumped[field] is not expected:
                raise ValueError(f"artifact boundary drifted: {field}")
        unhashed = self.model_dump(mode="python", exclude={"artifact_sha256"})
        if self.artifact_sha256 != c.domain_sha256(c.PHASE22_ARTIFACT_HASH_DOMAIN, unhashed):
            raise ValueError("artifact hash mismatch")
        return self


__all__ = [
    "AmendmentConclusion",
    "AmendmentOutcome",
    "AmendmentState",
    "CandidateGroupAmendment",
    "FamilyAMacroVintageCandidateInventoryAmendment",
    "FutureReviewRequirement",
    "MacroVintageCandidateProduct",
    "OfficialSourceCitation",
    "groups_manifest_sha256",
    "products_manifest_sha256",
    "requirements_manifest_sha256",
    "sources_manifest_sha256",
]
