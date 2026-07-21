"""Strict contracts for Phase 24 RTDSM rights-clarification requirements."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from fable5_data.phase24 import canonical as c

SHA256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
GitSHA = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]
ClosedText = Annotated[str, StringConstraints(min_length=1, max_length=1600)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")


class Outcome(StrEnum):
    BLOCKED = "BLOCKED"


class RequirementsState(StrEnum):
    RIGHTS_CLARIFICATION_REQUIREMENTS_FROZEN = "RIGHTS_CLARIFICATION_REQUIREMENTS_FROZEN"


class AggregateConclusion(StrEnum):
    BLOCKED_AWAITING_INDEPENDENT_CURRENT_USE_RIGHTS_CLARIFICATION = (
        "BLOCKED_AWAITING_INDEPENDENT_CURRENT_USE_RIGHTS_CLARIFICATION"
    )


class DisclosureStatus(StrEnum):
    PROPOSED_NOT_AUTHORIZED = "PROPOSED_NOT_AUTHORIZED"


class QuestionState(StrEnum):
    UNANSWERED = "UNANSWERED"


class RequiredAnswer(StrEnum):
    EXPLICIT_PRODUCT_SPECIFIC_YES_NO_OR_CONDITIONS = (
        "EXPLICIT_PRODUCT_SPECIFIC_YES_NO_OR_CONDITIONS"
    )


class EvidenceState(StrEnum):
    MISSING = "MISSING"


class DisclosureCode(StrEnum):
    PURPOSE_AND_ENVIRONMENT = "PURPOSE_AND_ENVIRONMENT"
    PRODUCT_AND_SERIES_SCOPE = "PRODUCT_AND_SERIES_SCOPE"
    AUTOMATED_ACCESS_PATTERN = "AUTOMATED_ACCESS_PATTERN"
    PERSISTENT_STORAGE_AND_BACKUPS = "PERSISTENT_STORAGE_AND_BACKUPS"
    AUTOMATED_MODEL_PROCESSING = "AUTOMATED_MODEL_PROCESSING"
    DERIVED_OUTPUTS = "DERIVED_OUTPUTS"
    DISPLAY_AND_REDISTRIBUTION = "DISPLAY_AND_REDISTRIBUTION"
    RETENTION_DELETION_AND_REVOCATION = "RETENTION_DELETION_AND_REVOCATION"


class QuestionCode(StrEnum):
    PERSISTENT_STORAGE = "PERSISTENT_STORAGE"
    AUTOMATED_MODEL_INTERNAL_USE = "AUTOMATED_MODEL_INTERNAL_USE"
    DERIVED_DATA_AND_MODEL_ARTIFACTS = "DERIVED_DATA_AND_MODEL_ARTIFACTS"
    RETENTION_DELETION = "RETENTION_DELETION"
    REDISTRIBUTION_AND_DISPLAY = "REDISTRIBUTION_AND_DISPLAY"
    ATTRIBUTION = "ATTRIBUTION"
    THIRD_PARTY_BLS_CONTENT = "THIRD_PARTY_BLS_CONTENT"
    AUTOMATED_ACCESS_AND_LOAD = "AUTOMATED_ACCESS_AND_LOAD"
    REVOCATION_AND_CURRENTNESS = "REVOCATION_AND_CURRENTNESS"
    AUTHORITY_AND_PRODUCT_SCOPE = "AUTHORITY_AND_PRODUCT_SCOPE"


class EvidenceCode(StrEnum):
    AUTHENTICATED_RIGHTS_HOLDER_IDENTITY = "AUTHENTICATED_RIGHTS_HOLDER_IDENTITY"
    EXACT_PRODUCT_SERIES_DELIVERY_SCOPE = "EXACT_PRODUCT_SERIES_DELIVERY_SCOPE"
    EXPLICIT_INTENDED_USE_COVERAGE = "EXPLICIT_INTENDED_USE_COVERAGE"
    EFFECTIVE_TERMS_AND_CURRENTNESS = "EFFECTIVE_TERMS_AND_CURRENTNESS"
    THIRD_PARTY_RIGHTS_COVERAGE = "THIRD_PARTY_RIGHTS_COVERAGE"
    REVOCATION_RETENTION_AND_DELETION = "REVOCATION_RETENTION_AND_DELETION"


class RuleCode(StrEnum):
    UNANSWERED_TO_EVIDENCE_PRESENT_UNVERIFIED = "UNANSWERED_TO_EVIDENCE_PRESENT_UNVERIFIED"
    INDEPENDENT_VERIFICATION_REQUIRED = "INDEPENDENT_VERIFICATION_REQUIRED"
    ALL_QUESTIONS_REQUIRED = "ALL_QUESTIONS_REQUIRED"
    CONDITIONS_MUST_BE_ENFORCEABLE = "CONDITIONS_MUST_BE_ENFORCEABLE"
    PROHIBITED_OR_AMBIGUOUS_FAILS_CLOSED = "PROHIBITED_OR_AMBIGUOUS_FAILS_CLOSED"
    CHANGE_REQUIRES_REVALIDATION = "CHANGE_REQUIRES_REVALIDATION"
    PUBLICATION_IS_NOT_AUTHORITY = "PUBLICATION_IS_NOT_AUTHORITY"


def _manifest(domain: str, rows: tuple[BaseModel, ...], field: str) -> str:
    return c.domain_sha256(domain, tuple(getattr(row, field) for row in rows))


class ProposedUseDisclosure(StrictModel):
    schema_version: str
    ordinal: Annotated[int, Field(ge=1, le=8)]
    code: DisclosureCode
    disclosure: ClosedText
    status: DisclosureStatus
    external_action_authorized: bool
    satisfied: bool
    disclosure_sha256: SHA256

    @model_validator(mode="after")
    def validate_frozen_row(self) -> Self:
        row = c.PHASE24_DISCLOSURE_ROWS[self.ordinal - 1]
        expected = {
            "schema_version": c.PHASE24_DISCLOSURE_SCHEMA_VERSION,
            "ordinal": self.ordinal,
            "code": row[0],
            "disclosure": row[1],
            "status": "PROPOSED_NOT_AUTHORIZED",
            **dict(c.PHASE24_ROW_INVARIANTS),
        }
        if c.canonicalize(
            self.model_dump(mode="python", exclude={"disclosure_sha256"})
        ) != c.canonicalize(expected):
            raise ValueError("proposed-use disclosure drifted")
        if self.disclosure_sha256 != c.domain_sha256(c.PHASE24_DISCLOSURE_HASH_DOMAIN, expected):
            raise ValueError("proposed-use disclosure hash mismatch")
        return self


class RightsClarificationQuestion(StrictModel):
    schema_version: str
    ordinal: Annotated[int, Field(ge=1, le=10)]
    code: QuestionCode
    phase23_rights_field: str
    question: ClosedText
    required_answer: RequiredAnswer
    state: QuestionState
    answer_evidence_present: bool
    independently_verified: bool
    external_action_authorized: bool
    satisfied: bool
    question_sha256: SHA256

    @model_validator(mode="after")
    def validate_frozen_row(self) -> Self:
        row = c.PHASE24_QUESTION_ROWS[self.ordinal - 1]
        expected = {
            "schema_version": c.PHASE24_QUESTION_SCHEMA_VERSION,
            "ordinal": self.ordinal,
            "code": row[0],
            "phase23_rights_field": row[1],
            "question": row[2],
            "required_answer": "EXPLICIT_PRODUCT_SPECIFIC_YES_NO_OR_CONDITIONS",
            "state": "UNANSWERED",
            "answer_evidence_present": False,
            "independently_verified": False,
            **dict(c.PHASE24_ROW_INVARIANTS),
        }
        if c.canonicalize(
            self.model_dump(mode="python", exclude={"question_sha256"})
        ) != c.canonicalize(expected):
            raise ValueError("rights-clarification question drifted")
        if self.question_sha256 != c.domain_sha256(c.PHASE24_QUESTION_HASH_DOMAIN, expected):
            raise ValueError("rights-clarification question hash mismatch")
        return self


class RightsEvidenceRequirement(StrictModel):
    schema_version: str
    ordinal: Annotated[int, Field(ge=1, le=6)]
    code: EvidenceCode
    requirement: ClosedText
    acceptable_evidence: ClosedText
    state: EvidenceState
    evidence_present: bool
    independently_verified: bool
    external_action_authorized: bool
    satisfied: bool
    evidence_requirement_sha256: SHA256

    @model_validator(mode="after")
    def validate_frozen_row(self) -> Self:
        row = c.PHASE24_EVIDENCE_ROWS[self.ordinal - 1]
        expected = {
            "schema_version": c.PHASE24_EVIDENCE_SCHEMA_VERSION,
            "ordinal": self.ordinal,
            "code": row[0],
            "requirement": row[1],
            "acceptable_evidence": row[2],
            "state": "MISSING",
            "evidence_present": False,
            "independently_verified": False,
            **dict(c.PHASE24_ROW_INVARIANTS),
        }
        if c.canonicalize(
            self.model_dump(mode="python", exclude={"evidence_requirement_sha256"})
        ) != c.canonicalize(expected):
            raise ValueError("rights-evidence requirement drifted")
        if self.evidence_requirement_sha256 != c.domain_sha256(
            c.PHASE24_EVIDENCE_HASH_DOMAIN, expected
        ):
            raise ValueError("rights-evidence requirement hash mismatch")
        return self


class RightsAnswerTransitionRule(StrictModel):
    schema_version: str
    ordinal: Annotated[int, Field(ge=1, le=7)]
    code: RuleCode
    rule: ClosedText
    applied: bool
    external_action_authorized: bool
    satisfied: bool
    rule_sha256: SHA256

    @model_validator(mode="after")
    def validate_frozen_row(self) -> Self:
        row = c.PHASE24_RULE_ROWS[self.ordinal - 1]
        expected = {
            "schema_version": c.PHASE24_RULE_SCHEMA_VERSION,
            "ordinal": self.ordinal,
            "code": row[0],
            "rule": row[1],
            "applied": False,
            **dict(c.PHASE24_ROW_INVARIANTS),
        }
        if c.canonicalize(
            self.model_dump(mode="python", exclude={"rule_sha256"})
        ) != c.canonicalize(expected):
            raise ValueError("rights-answer transition rule drifted")
        if self.rule_sha256 != c.domain_sha256(c.PHASE24_RULE_HASH_DOMAIN, expected):
            raise ValueError("rights-answer transition rule hash mismatch")
        return self


def disclosures_manifest_sha256(rows: tuple[ProposedUseDisclosure, ...]) -> str:
    return _manifest(c.PHASE24_DISCLOSURES_MANIFEST_HASH_DOMAIN, rows, "disclosure_sha256")


def questions_manifest_sha256(rows: tuple[RightsClarificationQuestion, ...]) -> str:
    return _manifest(c.PHASE24_QUESTIONS_MANIFEST_HASH_DOMAIN, rows, "question_sha256")


def evidence_manifest_sha256(rows: tuple[RightsEvidenceRequirement, ...]) -> str:
    return _manifest(c.PHASE24_EVIDENCE_MANIFEST_HASH_DOMAIN, rows, "evidence_requirement_sha256")


def rules_manifest_sha256(rows: tuple[RightsAnswerTransitionRule, ...]) -> str:
    return _manifest(c.PHASE24_RULES_MANIFEST_HASH_DOMAIN, rows, "rule_sha256")


class FamilyARTDSMRightsClarificationRequirements(StrictModel):
    schema_version: str
    artifact_id: UUID
    artifact_sha256: SHA256
    policy_id: str
    policy_sha256: SHA256
    accepted_phase23_commit_sha: GitSHA
    accepted_phase23_tree_sha: GitSHA
    phase23_merge_commit_sha: GitSHA
    phase23_artifact_id: UUID
    phase23_artifact_sha256: SHA256
    phase23_policy_sha256: SHA256
    phase23_findings_manifest_sha256: SHA256
    phase23_requirements_manifest_sha256: SHA256
    product_code: str
    phase22_product_sha256: SHA256
    family: str
    frozen_at_utc: datetime
    outcome: Outcome
    requirements_state: RequirementsState
    aggregate_conclusion: AggregateConclusion
    block_reason: ClosedText
    proposed_use_disclosures_manifest_sha256: SHA256
    clarification_questions_manifest_sha256: SHA256
    evidence_requirements_manifest_sha256: SHA256
    transition_rules_manifest_sha256: SHA256
    proposed_use_disclosures: tuple[ProposedUseDisclosure, ...]
    clarification_questions: tuple[RightsClarificationQuestion, ...]
    evidence_requirements: tuple[RightsEvidenceRequirement, ...]
    transition_rules: tuple[RightsAnswerTransitionRule, ...]
    requirements_only: bool
    runtime_network_disabled: bool
    phase23_artifact_unchanged: bool
    phase23_review_inherited: bool
    clarification_requirements_frozen: bool
    provider_contact_performed: bool
    counsel_contact_performed: bool
    clarification_request_sent: bool
    clarification_response_received: bool
    clarification_evidence_present: bool
    clarification_verified: bool
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
    operational_source_product_composition_selected: bool
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
        scalar_names = (
            "schema_version",
            "policy_id",
            "policy_sha256",
            "accepted_phase23_commit_sha",
            "accepted_phase23_tree_sha",
            "phase23_merge_commit_sha",
            "phase23_artifact_id",
            "phase23_artifact_sha256",
            "phase23_policy_sha256",
            "phase23_findings_manifest_sha256",
            "phase23_requirements_manifest_sha256",
            "product_code",
            "phase22_product_sha256",
            "family",
            "frozen_at_utc",
            "outcome",
            "requirements_state",
            "aggregate_conclusion",
            "block_reason",
            "disclaimer",
        )
        for name in scalar_names:
            constant = "PHASE24_" + name.upper()
            if name == "schema_version":
                constant = "PHASE24_ARTIFACT_SCHEMA_VERSION"
            if name == "artifact_id":
                continue
            expected = getattr(c, constant)
            if c.canonicalize(dumped[name]) != c.canonicalize(expected):
                raise ValueError(f"artifact scalar drifted: {name}")
        if self.artifact_id != c.identity():
            raise ValueError("artifact identity drifted")
        if tuple(row.code.value for row in self.proposed_use_disclosures) != tuple(
            row[0] for row in c.PHASE24_DISCLOSURE_ROWS
        ) or self.proposed_use_disclosures_manifest_sha256 != disclosures_manifest_sha256(
            self.proposed_use_disclosures
        ):
            raise ValueError("proposed-use disclosure registry drifted")
        if tuple(row.code.value for row in self.clarification_questions) != tuple(
            row[0] for row in c.PHASE24_QUESTION_ROWS
        ) or self.clarification_questions_manifest_sha256 != questions_manifest_sha256(
            self.clarification_questions
        ):
            raise ValueError("clarification-question registry drifted")
        if tuple(row.code.value for row in self.evidence_requirements) != tuple(
            row[0] for row in c.PHASE24_EVIDENCE_ROWS
        ) or self.evidence_requirements_manifest_sha256 != evidence_manifest_sha256(
            self.evidence_requirements
        ):
            raise ValueError("evidence-requirement registry drifted")
        if tuple(row.code.value for row in self.transition_rules) != tuple(
            row[0] for row in c.PHASE24_RULE_ROWS
        ) or self.transition_rules_manifest_sha256 != rules_manifest_sha256(self.transition_rules):
            raise ValueError("transition-rule registry drifted")
        for field, expected in c.PHASE24_BOUNDARY_VALUES.items():
            if dumped[field] is not expected:
                raise ValueError(f"artifact boundary drifted: {field}")
        unhashed = self.model_dump(mode="python", exclude={"artifact_sha256"})
        if self.artifact_sha256 != c.domain_sha256(c.PHASE24_ARTIFACT_HASH_DOMAIN, unhashed):
            raise ValueError("artifact hash mismatch")
        return self


__all__ = [
    "FamilyARTDSMRightsClarificationRequirements",
    "ProposedUseDisclosure",
    "RightsAnswerTransitionRule",
    "RightsClarificationQuestion",
    "RightsEvidenceRequirement",
    "disclosures_manifest_sha256",
    "evidence_manifest_sha256",
    "questions_manifest_sha256",
    "rules_manifest_sha256",
]
