"""Strict contracts for Phase 27 metadata-only evidence intake."""

from __future__ import annotations

import re
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Annotated, Self
from uuid import UUID

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from fable5_data.phase25 import canonical as phase25_c
from fable5_data.phase25.contracts import (
    VERIFIABLE_PROVENANCE,
    AuthorityEvidenceInput,
    EvaluationState,
    QuestionAnswerInput,
    RightsResponseConditionInput,
    RightsResponseIntake,
    ScopeAnswerInput,
    ScopeCode,
    VerificationStatus,
)
from fable5_data.phase27 import canonical as c

_SENSITIVE_CODE_PARTS = (
    "APIKEY",
    "API_KEY",
    "AUTHORIZATION",
    "BEARER",
    "COOKIE",
    "CREDENTIAL",
    "PASSWORD",
    "PRIVATE_KEY",
    "SECRET",
    "SESSION_TOKEN",
    "TOKEN",
)
_OPAQUE_CREDENTIAL_SEGMENT = re.compile(
    r"(?=[A-Z0-9]{20,})(?=[A-Z0-9]*[A-Z])(?=[A-Z0-9]*[0-9])[A-Z0-9]+"
)


def _reject_sensitive_code(value: str) -> str:
    upper = value.upper()
    if any(part in upper for part in _SENSITIVE_CODE_PARTS):
        raise ValueError("sensitive credential-shaped metadata is prohibited")
    if any(_OPAQUE_CREDENTIAL_SEGMENT.fullmatch(part) for part in re.split(r"[._:-]", upper)):
        raise ValueError("opaque credential-shaped metadata is prohibited")
    return value


SHA256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
GitSHA = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]
EvidenceId = Annotated[
    str,
    StringConstraints(pattern=r"^[A-Z0-9][A-Z0-9._:-]{2,127}$"),
    AfterValidator(_reject_sensitive_code),
]
Code = Annotated[
    str,
    StringConstraints(pattern=r"^[A-Z][A-Z0-9_]{2,127}$"),
    AfterValidator(_reject_sensitive_code),
]
Capability = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]{2,63}$")]
ClosedText = Annotated[str, StringConstraints(min_length=1, max_length=2400)]
ShortText = Annotated[str, StringConstraints(min_length=1, max_length=512)]

_SEC_URL = re.compile(r"^https://(?:www\.|data\.)?sec\.gov(?:/|$)", re.IGNORECASE)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")


class Outcome(StrEnum):
    BLOCKED = "BLOCKED"


class Determination(StrEnum):
    COMPOSITION_RIGHTS_ENTITLEMENT_EVIDENCE_MISSING = (
        "COMPOSITION_RIGHTS_ENTITLEMENT_EVIDENCE_MISSING"
    )
    COMPOSITION_RIGHTS_ENTITLEMENT_EVIDENCE_BLOCKED = (
        "COMPOSITION_RIGHTS_ENTITLEMENT_EVIDENCE_BLOCKED"
    )
    VERIFIED_EVIDENCE_RECORDED_REQUIRES_SEPARATE_ACQUISITION_AUTHORITY = (
        "VERIFIED_EVIDENCE_RECORDED_REQUIRES_SEPARATE_ACQUISITION_AUTHORITY"
    )


class EvidenceState(StrEnum):
    MISSING = "MISSING"
    BLOCKED = "BLOCKED"
    VERIFIED_EVIDENCE_RECORDED = "VERIFIED_EVIDENCE_RECORDED"


def _require_utc(value: datetime, name: str) -> None:
    if value.utcoffset() is None or value.astimezone(UTC) != value:
        raise ValueError(f"{name} must be UTC")


NormalizedSummary = Annotated[
    str,
    StringConstraints(pattern=rf"^[A-Z][A-Z0-9_]{{2,{c.NORMALIZED_SUMMARY_MAX_LENGTH - 1}}}$"),
    AfterValidator(_reject_sensitive_code),
]


class SanitizedAuthorityEvidenceInput(AuthorityEvidenceInput):
    """Phase 27 private-authority metadata with no free-text identity or agreement fields."""

    responder_organization: Code
    responder_stable_identity: SHA256
    responder_role: Code
    authority_basis: Code
    rights_holding_legal_entity: Code
    expiry_not_applicable_reason: Code | None = None
    governing_agreement: SHA256
    governing_terms_version: Code
    immutable_evidence_id: EvidenceId

    @model_validator(mode="after")
    def validate_sanitized_authority(self) -> Self:
        expected_basis = f"{self.authenticated_provenance.value}{c.PRIVATE_AUTHORITY_BASIS_SUFFIX}"
        if self.authority_basis != expected_basis:
            raise ValueError("authority basis does not match authenticated provenance")
        return self


class SanitizedRightsResponseConditionInput(RightsResponseConditionInput):
    condition_id: EvidenceId
    normalized_condition: NormalizedSummary
    control_id: EvidenceId | None = None
    acceptance_test_id: EvidenceId | None = None


class SanitizedQuestionAnswerInput(QuestionAnswerInput):
    normalized_finding: NormalizedSummary
    evidence_ids: tuple[EvidenceId, ...] = ()
    conditions: tuple[SanitizedRightsResponseConditionInput, ...] = ()


class SanitizedScopeAnswerInput(ScopeAnswerInput):
    normalized_determination: NormalizedSummary
    evidence_ids: tuple[EvidenceId, ...] = ()
    conditions: tuple[SanitizedRightsResponseConditionInput, ...] = ()

    @model_validator(mode="after")
    def validate_sanitized_scope(self) -> Self:
        label_hash = phase25_c.domain_sha256(
            phase25_c.PHASE25_NORMALIZED_VALUE_HASH_DOMAIN, self.normalized_determination
        )
        if self.code is ScopeCode.ACCOUNT_OR_ENTITLEMENT:
            if self.normalized_value_sha256 == label_hash:
                raise ValueError(
                    "RTDSM account or entitlement requires a distinct hash-only identity"
                )
        elif self.normalized_value_sha256 != label_hash:
            raise ValueError("RTDSM normalized scope hash mismatch")
        if (
            self.code is ScopeCode.PRODUCT
            and self.state in {EvaluationState.PASS, EvaluationState.CONDITIONAL}
            and self.normalized_determination != c.RTDSM_PRODUCT
        ):
            raise ValueError("RTDSM product scope code mismatch")
        return self


class SanitizedRightsResponseIntake(RightsResponseIntake):
    """The accepted Phase 25 intake shape with Phase 27 private-metadata restrictions."""

    authority_evidence: tuple[SanitizedAuthorityEvidenceInput, ...] = ()
    question_answers: tuple[SanitizedQuestionAnswerInput, ...] = ()
    scope_answers: tuple[SanitizedScopeAnswerInput, ...] = ()
    mutual_consistency_evidence_ids: tuple[EvidenceId, ...] = ()


def phase25_evaluator_intake(intake: SanitizedRightsResponseIntake) -> RightsResponseIntake:
    """Translate the frozen product code only in memory for the accepted Phase 25 evaluator."""

    payload = intake.model_dump(mode="python")
    translated_scopes = []
    for row in intake.scope_answers:
        scope = row.model_dump(mode="python")
        if row.code is ScopeCode.PRODUCT and row.normalized_determination == c.RTDSM_PRODUCT:
            scope["normalized_determination"] = phase25_c.PHASE25_PRODUCT_NAME
            scope["normalized_value_sha256"] = phase25_c.domain_sha256(
                phase25_c.PHASE25_NORMALIZED_VALUE_HASH_DOMAIN,
                phase25_c.PHASE25_PRODUCT_NAME,
            )
        translated_scopes.append(scope)
    payload["scope_answers"] = tuple(translated_scopes)
    return RightsResponseIntake.model_validate(payload, strict=True)


def authority_is_verified(row: AuthorityEvidenceInput) -> bool:
    return (
        row.authenticated_provenance in VERIFIABLE_PROVENANCE
        and row.independent_verification_status is VerificationStatus.VERIFIED
        and row.responder_identity_authenticated
        and row.authority_basis_verified
    )


def authority_is_current(row: AuthorityEvidenceInput, evaluated_at_utc: datetime) -> bool:
    return (
        row.response_date_utc <= evaluated_at_utc
        and row.effective_date_utc <= evaluated_at_utc
        and (row.expiry_date_utc is None or evaluated_at_utc < row.expiry_date_utc)
    )


class RequirementAnswerInput(StrictModel):
    code: Code
    state: EvaluationState
    normalized_finding: NormalizedSummary
    normalized_value_sha256: SHA256
    evidence_ids: tuple[EvidenceId, ...] = ()
    conditions: tuple[SanitizedRightsResponseConditionInput, ...] = ()

    @model_validator(mode="after")
    def validate_normalized_value_hash(self) -> Self:
        expected = c.domain_sha256(c.NORMALIZED_VALUE_DOMAIN, self.normalized_finding)
        if self.normalized_value_sha256 != expected:
            raise ValueError("normalized finding hash mismatch")
        return self


class CRSPRightsEntitlementIntake(StrictModel):
    schema_version: str
    response_received: bool
    licensed_party_identity_sha256: SHA256 | None = None
    executed_agreement_sha256: SHA256 | None = None
    order_form_or_product_schedule_sha256: SHA256 | None = None
    product_code: Code | None = None
    product_sku_sha256: SHA256 | None = None
    delivery_id: Code | None = None
    selected_capability_codes: tuple[Capability, ...] = ()
    third_party_rights_evidence_ids: tuple[EvidenceId, ...] = ()
    authority_evidence: tuple[SanitizedAuthorityEvidenceInput, ...] = ()
    requirement_answers: tuple[RequirementAnswerInput, ...] = ()
    mutual_consistency_status: VerificationStatus = VerificationStatus.UNVERIFIED
    mutual_consistency_evidence_ids: tuple[EvidenceId, ...] = ()

    @model_validator(mode="after")
    def validate_intake(self) -> Self:
        if self.schema_version != c.CRSP_INTAKE_SCHEMA:
            raise ValueError("CRSP intake schema mismatch")
        allowed = {row[0] for row in c.CRSP_REQUIREMENT_ROWS}
        codes = [row.code for row in self.requirement_answers]
        if len(codes) != len(set(codes)) or not set(codes) <= allowed:
            raise ValueError("CRSP requirement answer registry mismatch")
        evidence_ids = [row.immutable_evidence_id for row in self.authority_evidence]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("duplicate CRSP evidence id")
        if len(self.selected_capability_codes) != len(set(self.selected_capability_codes)):
            raise ValueError("duplicate CRSP capability code")
        if not set(self.selected_capability_codes) <= set(c.CRSP_CAPABILITY_CODES):
            raise ValueError("CRSP capability is outside the selected composition")
        if not self.response_received and (
            self.licensed_party_identity_sha256
            or self.executed_agreement_sha256
            or self.order_form_or_product_schedule_sha256
            or self.product_code
            or self.product_sku_sha256
            or self.delivery_id
            or self.selected_capability_codes
            or self.third_party_rights_evidence_ids
            or self.authority_evidence
            or self.requirement_answers
            or self.mutual_consistency_status is not VerificationStatus.UNVERIFIED
            or self.mutual_consistency_evidence_ids
        ):
            raise ValueError("CRSP metadata requires response_received")
        if self.mutual_consistency_status is VerificationStatus.UNVERIFIED:
            if self.mutual_consistency_evidence_ids:
                raise ValueError("unverified CRSP consistency cannot cite evidence")
        elif not self.mutual_consistency_evidence_ids:
            raise ValueError("evaluated CRSP consistency requires evidence")
        return self


class SECPolicyDocumentInput(StrictModel):
    evidence_id: EvidenceId
    source_code: Code
    source_url: ClosedText
    official_title: ClosedText
    publisher: ClosedText
    publisher_stated_date: date
    retrieved_at_utc: datetime
    effective_at_utc: datetime
    revalidation_due_at_utc: datetime
    policy_version: Code | SHA256
    clause_locator: NormalizedSummary
    content_sha256: SHA256
    phase18_source_sha256: SHA256
    provenance_locator_sha256: SHA256
    normalized_finding: NormalizedSummary
    normalized_delta: NormalizedSummary
    independent_verification_status: VerificationStatus
    independent_verifier_identity_sha256: SHA256

    @field_validator("source_url")
    @classmethod
    def official_sec_url(cls, value: str) -> str:
        if _SEC_URL.match(value) is None:
            raise ValueError("SEC policy source must be an official first-party HTTPS URL")
        return value

    @field_validator("publisher_stated_date", mode="before")
    @classmethod
    def strict_publisher_date(cls, value: object) -> date:
        if isinstance(value, datetime):
            raise ValueError("publisher stated date must be an ISO calendar date")
        if isinstance(value, date):
            return value
        if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            try:
                return date.fromisoformat(value)
            except ValueError as exc:
                raise ValueError("publisher stated date must be an ISO calendar date") from exc
        raise ValueError("publisher stated date must be an ISO calendar date")

    @model_validator(mode="after")
    def validate_dates(self) -> Self:
        accepted = c.sec_source_row(self.source_code)
        if (
            self.official_title != accepted[1]
            or self.publisher != accepted[2]
            or self.source_url != accepted[3]
            or self.phase18_source_sha256 != accepted[4]
        ):
            raise ValueError("SEC policy document drifted from accepted Phase 18 source binding")
        for name in ("retrieved_at_utc", "effective_at_utc", "revalidation_due_at_utc"):
            _require_utc(getattr(self, name), name)
        if self.publisher_stated_date > self.retrieved_at_utc.date():
            raise ValueError("SEC publisher stated date cannot follow retrieval")
        if self.revalidation_due_at_utc <= self.retrieved_at_utc:
            raise ValueError("SEC revalidation must follow retrieval")
        return self


class SECPolicyRevalidationIntake(StrictModel):
    schema_version: str
    review_performed: bool
    policy_documents: tuple[SECPolicyDocumentInput, ...] = ()
    requirement_answers: tuple[RequirementAnswerInput, ...] = ()
    mutual_consistency_status: VerificationStatus = VerificationStatus.UNVERIFIED
    mutual_consistency_evidence_ids: tuple[EvidenceId, ...] = ()

    @model_validator(mode="after")
    def validate_intake(self) -> Self:
        if self.schema_version != c.SEC_INTAKE_SCHEMA:
            raise ValueError("SEC intake schema mismatch")
        allowed = {row[0] for row in c.SEC_REQUIREMENT_ROWS}
        codes = [row.code for row in self.requirement_answers]
        if len(codes) != len(set(codes)) or not set(codes) <= allowed:
            raise ValueError("SEC requirement answer registry mismatch")
        evidence_ids = [row.evidence_id for row in self.policy_documents]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("duplicate SEC evidence id")
        if not self.review_performed and (
            self.policy_documents
            or self.requirement_answers
            or self.mutual_consistency_status is not VerificationStatus.UNVERIFIED
            or self.mutual_consistency_evidence_ids
        ):
            raise ValueError("SEC metadata requires review_performed")
        if self.mutual_consistency_status is VerificationStatus.UNVERIFIED:
            if self.mutual_consistency_evidence_ids:
                raise ValueError("unverified SEC consistency cannot cite evidence")
        elif not self.mutual_consistency_evidence_ids:
            raise ValueError("evaluated SEC consistency requires evidence")
        return self


class Phase27EvidenceIntake(StrictModel):
    schema_version: str
    evaluated_at_utc: datetime
    recorded_at_utc: datetime
    crsp: CRSPRightsEntitlementIntake
    rtdsm: SanitizedRightsResponseIntake
    sec: SECPolicyRevalidationIntake
    composition_consistency_status: VerificationStatus = VerificationStatus.UNVERIFIED
    composition_consistency_evidence_ids: tuple[EvidenceId, ...] = ()

    @model_validator(mode="after")
    def validate_intake(self) -> Self:
        if self.schema_version != c.INTAKE_SCHEMA:
            raise ValueError("Phase 27 intake schema mismatch")
        _require_utc(self.evaluated_at_utc, "evaluated_at_utc")
        _require_utc(self.recorded_at_utc, "recorded_at_utc")
        if self.recorded_at_utc < self.evaluated_at_utc:
            raise ValueError("recorded time cannot precede evaluation")
        if self.composition_consistency_status is VerificationStatus.UNVERIFIED:
            if self.composition_consistency_evidence_ids:
                raise ValueError("unverified composition consistency cannot cite evidence")
        elif not self.composition_consistency_evidence_ids:
            raise ValueError("evaluated composition consistency requires evidence")
        all_ids = [row.immutable_evidence_id for row in self.crsp.authority_evidence]
        all_ids.extend(row.immutable_evidence_id for row in self.rtdsm.authority_evidence)
        all_ids.extend(row.evidence_id for row in self.sec.policy_documents)
        if len(all_ids) != len(set(all_ids)):
            raise ValueError("evidence ids must be globally unique")
        return self


class EvidenceCondition(StrictModel):
    schema_version: str
    condition_id: EvidenceId
    normalized_condition: NormalizedSummary
    control_id: EvidenceId | None = None
    acceptance_test_id: EvidenceId | None = None
    enforceable: bool
    acceptance_test_passed: bool
    condition_sha256: SHA256

    @model_validator(mode="after")
    def validate_condition(self) -> Self:
        payload = self.model_dump(mode="python", exclude={"condition_sha256"})
        if self.schema_version != c.CONDITION_SCHEMA:
            raise ValueError("condition schema mismatch")
        if self.condition_sha256 != c.domain_sha256(c.CONDITION_DOMAIN, payload):
            raise ValueError("condition hash mismatch")
        return self


def conditions_satisfied(rows: tuple[EvidenceCondition, ...]) -> bool:
    return bool(rows) and all(
        row.control_id is not None
        and row.acceptance_test_id is not None
        and row.enforceable
        and row.acceptance_test_passed
        for row in rows
    )


def _evidence_condition(row: SanitizedRightsResponseConditionInput) -> EvidenceCondition:
    payload = {
        "schema_version": c.CONDITION_SCHEMA,
        **row.model_dump(mode="python"),
    }
    return EvidenceCondition.model_validate(
        {
            **payload,
            "condition_sha256": c.domain_sha256(c.CONDITION_DOMAIN, payload),
        }
    )


class AuthorityEvidenceRecord(SanitizedAuthorityEvidenceInput):
    schema_version: str
    product_code: Code
    authority_verified: bool
    effective_at_evaluation: bool
    current_at_evaluation: bool
    record_sha256: SHA256

    @model_validator(mode="after")
    def validate_record(self) -> Self:
        payload = self.model_dump(mode="python", exclude={"record_sha256"})
        if self.schema_version != c.AUTHORITY_SCHEMA or self.product_code != c.CRSP_PRODUCT:
            raise ValueError("authority record scope mismatch")
        if self.authority_verified is not authority_is_verified(self):
            raise ValueError("private authority verification mismatch")
        if self.record_sha256 != c.domain_sha256(c.AUTHORITY_DOMAIN, payload):
            raise ValueError("authority record hash mismatch")
        return self


class SECPolicyDocument(SECPolicyDocumentInput):
    schema_version: str
    official_first_party: bool
    current_at_evaluation: bool
    independently_verified: bool
    document_sha256: SHA256

    @model_validator(mode="after")
    def validate_document(self) -> Self:
        payload = self.model_dump(mode="python", exclude={"document_sha256"})
        expected_verified = self.independent_verification_status is VerificationStatus.VERIFIED
        if self.schema_version != c.SEC_DOCUMENT_SCHEMA or not self.official_first_party:
            raise ValueError("SEC document scope mismatch")
        if self.independently_verified is not expected_verified:
            raise ValueError("SEC document verification mismatch")
        if self.document_sha256 != c.domain_sha256(c.SEC_DOCUMENT_DOMAIN, payload):
            raise ValueError("SEC document hash mismatch")
        return self


class RequirementEvaluation(StrictModel):
    schema_version: str
    ordinal: Annotated[int, Field(ge=1, le=32)]
    product_code: Code
    code: Code
    requirement: ClosedText
    state: EvaluationState
    normalized_finding: NormalizedSummary
    normalized_value_sha256: SHA256
    evidence_ids: tuple[EvidenceId, ...]
    independently_verified: bool
    conditions: tuple[EvidenceCondition, ...]
    satisfied: bool
    evaluation_sha256: SHA256

    @model_validator(mode="after")
    def validate_evaluation(self) -> Self:
        rows = c.requirement_rows(self.product_code)
        if self.ordinal > len(rows) or (self.code, self.requirement) != rows[self.ordinal - 1]:
            raise ValueError("requirement registry mismatch")
        if self.schema_version != c.REQUIREMENT_SCHEMA:
            raise ValueError("requirement schema mismatch")
        if self.normalized_value_sha256 != c.domain_sha256(
            c.NORMALIZED_VALUE_DOMAIN, self.normalized_finding
        ):
            raise ValueError("normalized finding hash mismatch")
        if self.state is EvaluationState.MISSING:
            expected = (
                not self.evidence_ids and not self.independently_verified and not self.conditions
            )
            expected_satisfied = False
        elif self.state is EvaluationState.FAIL:
            expected = (
                bool(self.evidence_ids) and self.independently_verified and not self.conditions
            )
            expected_satisfied = False
        elif self.state is EvaluationState.PASS:
            expected = (
                bool(self.evidence_ids) and self.independently_verified and not self.conditions
            )
            expected_satisfied = True
        else:
            expected = (
                bool(self.evidence_ids) and self.independently_verified and bool(self.conditions)
            )
            expected_satisfied = conditions_satisfied(self.conditions)
        if not expected or self.satisfied is not expected_satisfied:
            raise ValueError("requirement evaluation is not fail-closed")
        payload = self.model_dump(mode="python", exclude={"evaluation_sha256"})
        if self.evaluation_sha256 != c.domain_sha256(c.REQUIREMENT_DOMAIN, payload):
            raise ValueError("requirement evaluation hash mismatch")
        return self


def build_requirement_evaluations(
    product: str,
    answers: tuple[RequirementAnswerInput, ...],
    verified_evidence_ids: frozenset[str],
) -> tuple[RequirementEvaluation, ...]:
    """Derive the only valid requirement evaluations from one sanitized intake."""

    by_code = {row.code: row for row in answers}
    evaluations = []
    for ordinal, (code, requirement) in enumerate(c.requirement_rows(product), 1):
        answer = by_code.get(code)
        if answer is None or answer.state is EvaluationState.MISSING:
            state = EvaluationState.MISSING
            finding = c.MISSING_FINDING if answer is None else answer.normalized_finding
            value_sha256 = c.domain_sha256(c.NORMALIZED_VALUE_DOMAIN, finding)
            evidence_ids: tuple[str, ...] = ()
            conditions: tuple[EvidenceCondition, ...] = ()
            independently_verified = False
        else:
            evidence_ids = tuple(answer.evidence_ids)
            independently_verified = bool(evidence_ids) and (
                set(evidence_ids) <= verified_evidence_ids
            )
            if not independently_verified:
                state = EvaluationState.MISSING
                finding = f"CLAIMED_{answer.state.value}_EVIDENCE_NOT_VERIFIED_FOR_PRODUCT"
                value_sha256 = c.domain_sha256(c.NORMALIZED_VALUE_DOMAIN, finding)
                evidence_ids = ()
                conditions = ()
            else:
                state = answer.state
                finding = answer.normalized_finding
                value_sha256 = answer.normalized_value_sha256
                conditions = tuple(_evidence_condition(row) for row in answer.conditions)
        satisfied = state is EvaluationState.PASS or (
            state is EvaluationState.CONDITIONAL and conditions_satisfied(conditions)
        )
        payload = {
            "schema_version": c.REQUIREMENT_SCHEMA,
            "ordinal": ordinal,
            "product_code": product,
            "code": code,
            "requirement": requirement,
            "state": state,
            "normalized_finding": finding,
            "normalized_value_sha256": value_sha256,
            "evidence_ids": evidence_ids,
            "independently_verified": independently_verified
            if state is not EvaluationState.MISSING
            else False,
            "conditions": conditions,
            "satisfied": satisfied,
        }
        evaluations.append(
            RequirementEvaluation.model_validate(
                {
                    **payload,
                    "evaluation_sha256": c.domain_sha256(c.REQUIREMENT_DOMAIN, payload),
                }
            )
        )
    return tuple(evaluations)


class RTDSMPhase25EvaluationBinding(StrictModel):
    schema_version: str
    phase25_artifact_id: UUID
    phase25_artifact_sha256: SHA256
    phase25_evidence_snapshot_id: UUID
    phase25_evidence_snapshot_sha256: SHA256
    phase25_authority_manifest_sha256: SHA256
    phase25_questions_manifest_sha256: SHA256
    phase25_scope_manifest_sha256: SHA256
    response_received: bool
    question_count: Annotated[int, Field(ge=0, le=10)]
    scope_count: Annotated[int, Field(ge=0, le=19)]
    satisfied_question_count: Annotated[int, Field(ge=0, le=10)]
    satisfied_scope_count: Annotated[int, Field(ge=0, le=19)]
    mutual_consistency_verified: bool
    selected_scope_bound: bool
    rights_verified: bool
    current_at_evaluation: bool
    determination: str
    binding_sha256: SHA256

    @model_validator(mode="after")
    def validate_binding(self) -> Self:
        payload = self.model_dump(mode="python", exclude={"binding_sha256"})
        if self.schema_version != c.RTDSM_BINDING_SCHEMA:
            raise ValueError("RTDSM binding schema mismatch")
        if self.question_count != 10 or self.scope_count != 19:
            raise ValueError("RTDSM Phase 25 registry count mismatch")
        if self.binding_sha256 != c.domain_sha256(c.RTDSM_BINDING_DOMAIN, payload):
            raise ValueError("RTDSM binding hash mismatch")
        return self


class SelectedProductEvidenceEvaluation(StrictModel):
    schema_version: str
    ordinal: Annotated[int, Field(ge=1, le=3)]
    product_code: Code
    delivery_ids: tuple[Code, ...]
    phase26_selected_product_sha256: SHA256
    state: EvidenceState
    required_count: Annotated[int, Field(ge=1, le=32)]
    satisfied_count: Annotated[int, Field(ge=0, le=32)]
    requirements_manifest_sha256: SHA256
    evidence_present: bool
    independently_verified: bool
    current_at_evaluation: bool
    product_evaluation_sha256: SHA256

    @model_validator(mode="after")
    def validate_product(self) -> Self:
        row = c.PRODUCT_ROWS[self.ordinal - 1]
        if (
            self.schema_version != c.PRODUCT_SCHEMA
            or self.product_code != row[0]
            or self.delivery_ids != row[1]
            or self.phase26_selected_product_sha256 != row[2]
        ):
            raise ValueError("selected product lineage mismatch")
        expected_verified = (
            self.satisfied_count == self.required_count
            and self.evidence_present
            and self.independently_verified
            and self.current_at_evaluation
        )
        expected_state = (
            EvidenceState.VERIFIED_EVIDENCE_RECORDED
            if expected_verified
            else EvidenceState.BLOCKED
            if self.evidence_present
            else EvidenceState.MISSING
        )
        if self.state is not expected_state:
            raise ValueError("selected product evidence state mismatch")
        payload = self.model_dump(mode="python", exclude={"product_evaluation_sha256"})
        if self.product_evaluation_sha256 != c.domain_sha256(c.PRODUCT_DOMAIN, payload):
            raise ValueError("selected product evaluation hash mismatch")
        return self


def _manifest(domain: str, rows: tuple[BaseModel, ...], field: str) -> str:
    return c.domain_sha256(domain, tuple(getattr(row, field) for row in rows))


def authority_manifest_sha256(rows: tuple[AuthorityEvidenceRecord, ...]) -> str:
    return _manifest(c.AUTHORITY_MANIFEST_DOMAIN, rows, "record_sha256")


def sec_documents_manifest_sha256(rows: tuple[SECPolicyDocument, ...]) -> str:
    return _manifest(c.SEC_DOCUMENTS_MANIFEST_DOMAIN, rows, "document_sha256")


def requirements_manifest_sha256(product: str, rows: tuple[RequirementEvaluation, ...]) -> str:
    domain = (
        c.CRSP_REQUIREMENTS_MANIFEST_DOMAIN
        if product == c.CRSP_PRODUCT
        else c.SEC_REQUIREMENTS_MANIFEST_DOMAIN
    )
    return _manifest(domain, rows, "evaluation_sha256")


def products_manifest_sha256(rows: tuple[SelectedProductEvidenceEvaluation, ...]) -> str:
    return _manifest(c.PRODUCTS_MANIFEST_DOMAIN, rows, "product_evaluation_sha256")


class Phase27RightsEntitlementEvidencePackage(StrictModel):
    schema_version: str
    artifact_id: UUID
    artifact_sha256: SHA256
    config_sha256: SHA256
    policy_id: str
    policy_sha256: SHA256
    accepted_phase26_commit_sha: GitSHA
    accepted_phase26_tree_sha: GitSHA
    phase26_artifact_id: UUID
    phase26_artifact_sha256: SHA256
    phase26_artifact_file_sha256: SHA256
    phase26_policy_sha256: SHA256
    phase26_selection_evidence_sha256: SHA256
    phase26_source_snapshot_id: UUID
    phase26_source_snapshot_sha256: SHA256
    generation_git_sha: GitSHA
    random_seed: Annotated[int, Field(ge=0)]
    trial_count: Annotated[int, Field(ge=0)]
    generated_at_utc: datetime
    family: str
    composition_id: Code
    product_ids: tuple[Code, ...]
    delivery_ids: tuple[Code, ...]
    intake: Phase27EvidenceIntake
    evidence_bundle_id: UUID
    evidence_bundle_sha256: SHA256
    authority_evidence: tuple[AuthorityEvidenceRecord, ...]
    authority_manifest_sha256: SHA256
    crsp_requirement_evaluations: tuple[RequirementEvaluation, ...]
    crsp_requirements_manifest_sha256: SHA256
    rtdsm_phase25_binding: RTDSMPhase25EvaluationBinding
    sec_policy_documents: tuple[SECPolicyDocument, ...]
    sec_policy_documents_manifest_sha256: SHA256
    sec_requirement_evaluations: tuple[RequirementEvaluation, ...]
    sec_requirements_manifest_sha256: SHA256
    product_evaluations: tuple[SelectedProductEvidenceEvaluation, ...]
    product_evaluations_manifest_sha256: SHA256
    outcome: Outcome
    determination: Determination
    block_reason: ClosedText
    verified_evidence_recorded: bool
    current_rights_evidence_for_exact_composition: bool
    metadata_only: bool
    runtime_network_disabled: bool
    generation_network_disabled: bool
    verification_network_disabled: bool
    paper_only: bool
    live_path_absent: bool
    no_personalized_investment_advice: bool
    no_real_performance_claimed: bool
    llm_trade_decisions_prohibited: bool
    provider_contact_performed: bool
    credentials_loaded: bool
    acquisition_authorized: bool
    external_data_capture_authorized: bool
    provider_observations_downloaded: bool
    provider_observations_persisted: bool
    production_adapter_activated: bool
    data_snapshot_created: bool
    exact_schema_qualified: bool
    point_in_time_qualified: bool
    research_ingestion_authorized: bool
    research_executed: bool
    performance_computed: bool
    strategy_promotion_authorized: bool
    risk_limits_changed: bool
    execution_authorized: bool
    paper_order_submitted: bool
    order_submission_authorized: bool
    database_changed: bool
    api_changed: bool
    disclaimer: ClosedText

    @model_validator(mode="after")
    def validate_package(self) -> Self:
        fixed = {
            "schema_version": c.ARTIFACT_SCHEMA,
            "config_sha256": c.POLICY_SHA256,
            "policy_id": c.POLICY_ID,
            "policy_sha256": c.POLICY_SHA256,
            "accepted_phase26_commit_sha": c.BASELINE_COMMIT_SHA,
            "accepted_phase26_tree_sha": c.BASELINE_TREE_SHA,
            "phase26_artifact_id": c.PHASE26_ARTIFACT_ID,
            "phase26_artifact_sha256": c.PHASE26_ARTIFACT_SHA256,
            "phase26_artifact_file_sha256": c.PHASE26_ARTIFACT_FILE_SHA256,
            "phase26_policy_sha256": c.PHASE26_POLICY_SHA256,
            "phase26_selection_evidence_sha256": c.PHASE26_SELECTION_EVIDENCE_SHA256,
            "phase26_source_snapshot_id": c.PHASE26_SOURCE_SNAPSHOT_ID,
            "phase26_source_snapshot_sha256": c.PHASE26_SOURCE_SNAPSHOT_SHA256,
            "generation_git_sha": c.GENERATION_GIT_SHA,
            "random_seed": c.RANDOM_SEED,
            "trial_count": c.TRIAL_COUNT,
            "family": c.FAMILY,
            "composition_id": c.COMPOSITION_ID,
            "product_ids": c.PRODUCT_IDS,
            "delivery_ids": c.DELIVERY_IDS,
            "outcome": "BLOCKED",
            "disclaimer": c.DISCLAIMER,
        }
        dumped = self.model_dump(mode="python")
        for name, expected in fixed.items():
            if c.canonicalize(dumped[name]) != c.canonicalize(expected):
                raise ValueError(f"package scalar drifted: {name}")
        if (
            self.generated_at_utc != self.intake.recorded_at_utc
            or self.generated_at_utc < self.intake.evaluated_at_utc
        ):
            raise ValueError("package generation chronology mismatch")
        for name, expected in c.BOUNDARY_VALUES.items():
            if dumped[name] is not expected:
                raise ValueError(f"operational authority drifted: {name}")
        if self.authority_manifest_sha256 != authority_manifest_sha256(self.authority_evidence):
            raise ValueError("authority manifest mismatch")
        if self.crsp_requirements_manifest_sha256 != requirements_manifest_sha256(
            c.CRSP_PRODUCT, self.crsp_requirement_evaluations
        ):
            raise ValueError("CRSP requirements manifest mismatch")
        if self.sec_policy_documents_manifest_sha256 != sec_documents_manifest_sha256(
            self.sec_policy_documents
        ):
            raise ValueError("SEC document manifest mismatch")
        if self.sec_requirements_manifest_sha256 != requirements_manifest_sha256(
            c.SEC_PRODUCT, self.sec_requirement_evaluations
        ):
            raise ValueError("SEC requirements manifest mismatch")
        if self.product_evaluations_manifest_sha256 != products_manifest_sha256(
            self.product_evaluations
        ):
            raise ValueError("product evaluations manifest mismatch")
        if tuple(row.code for row in self.crsp_requirement_evaluations) != tuple(
            row[0] for row in c.CRSP_REQUIREMENT_ROWS
        ) or tuple(row.code for row in self.sec_requirement_evaluations) != tuple(
            row[0] for row in c.SEC_REQUIREMENT_ROWS
        ):
            raise ValueError("requirement order mismatch")
        if tuple(row.product_code for row in self.product_evaluations) != c.PRODUCT_IDS:
            raise ValueError("product evaluation order mismatch")
        if len(self.authority_evidence) != len(self.intake.crsp.authority_evidence):
            raise ValueError("CRSP authority evidence count mismatch")
        for authority_record, authority_source in zip(
            self.authority_evidence, self.intake.crsp.authority_evidence, strict=True
        ):
            source_fields = set(type(authority_source).model_fields)
            if c.canonicalize(
                authority_record.model_dump(mode="python", include=source_fields)
            ) != c.canonicalize(authority_source.model_dump(mode="python")):
                raise ValueError("CRSP authority evidence input drifted")
            expected_current = authority_is_current(authority_source, self.intake.evaluated_at_utc)
            expected_effective = (
                authority_source.response_date_utc <= self.intake.evaluated_at_utc
                and authority_source.effective_date_utc <= self.intake.evaluated_at_utc
            )
            if (
                authority_record.effective_at_evaluation is not expected_effective
                or authority_record.current_at_evaluation is not expected_current
            ):
                raise ValueError("CRSP authority currentness mismatch")
        if len(self.sec_policy_documents) != len(self.intake.sec.policy_documents):
            raise ValueError("SEC policy evidence count mismatch")
        for sec_record, sec_source in zip(
            self.sec_policy_documents, self.intake.sec.policy_documents, strict=True
        ):
            source_fields = set(type(sec_source).model_fields)
            if c.canonicalize(
                sec_record.model_dump(mode="python", include=source_fields)
            ) != c.canonicalize(sec_source.model_dump(mode="python")):
                raise ValueError("SEC policy evidence input drifted")
            expected_current = (
                sec_source.effective_at_utc <= self.intake.evaluated_at_utc
                and sec_source.retrieved_at_utc
                <= self.intake.evaluated_at_utc
                < sec_source.revalidation_due_at_utc
            )
            if sec_record.current_at_evaluation is not expected_current:
                raise ValueError("SEC policy currentness mismatch")
        crsp_verified_ids = {
            row.immutable_evidence_id
            for row in self.authority_evidence
            if row.authority_verified and row.current_at_evaluation
        }
        sec_verified_ids = {
            row.evidence_id
            for row in self.sec_policy_documents
            if row.independently_verified and row.current_at_evaluation
        }
        expected_crsp_requirements = build_requirement_evaluations(
            c.CRSP_PRODUCT,
            self.intake.crsp.requirement_answers,
            frozenset(crsp_verified_ids),
        )
        if self.crsp_requirement_evaluations != expected_crsp_requirements:
            raise ValueError("CRSP requirement evaluations drifted from intake")
        expected_sec_requirements = build_requirement_evaluations(
            c.SEC_PRODUCT,
            self.intake.sec.requirement_answers,
            frozenset(sec_verified_ids),
        )
        if self.sec_requirement_evaluations != expected_sec_requirements:
            raise ValueError("SEC requirement evaluations drifted from intake")
        for row in self.crsp_requirement_evaluations:
            if row.independently_verified and not set(row.evidence_ids) <= crsp_verified_ids:
                raise ValueError("CRSP requirement cites unverified evidence")
        for row in self.sec_requirement_evaluations:
            if row.independently_verified and not set(row.evidence_ids) <= sec_verified_ids:
                raise ValueError("SEC requirement cites unverified evidence")
        from fable5_data.phase25.package import build_phase25_package

        phase25 = build_phase25_package(phase25_evaluator_intake(self.intake.rtdsm))
        rtdsm_current = bool(self.intake.rtdsm.authority_evidence) and all(
            authority_is_current(row, self.intake.evaluated_at_utc)
            for row in self.intake.rtdsm.authority_evidence
        )
        scopes = {row.code.value: row for row in phase25.scope_evaluations}
        selected_scope_bound = (
            scopes["REQUESTED_SERIES"].satisfied
            and scopes["REQUESTED_SERIES"].normalized_determination == c.RTDSM_REQUESTED_SERIES
            and scopes["PCPI_AND_BLS_ORIGIN"].satisfied
            and scopes["PCPI_AND_BLS_ORIGIN"].normalized_determination == c.RTDSM_PCPI_BLS_ORIGIN
            and scopes["DELIVERY_METHOD_AND_SURFACE"].satisfied
            and scopes["DELIVERY_METHOD_AND_SURFACE"].normalized_determination == c.DELIVERY_IDS[3]
        )
        rtdsm_verified = phase25.rights_verified and rtdsm_current and selected_scope_bound
        expected_rtdsm = {
            "schema_version": c.RTDSM_BINDING_SCHEMA,
            "phase25_artifact_id": phase25.artifact_id,
            "phase25_artifact_sha256": phase25.artifact_sha256,
            "phase25_evidence_snapshot_id": phase25.evidence_snapshot_id,
            "phase25_evidence_snapshot_sha256": phase25.evidence_snapshot_sha256,
            "phase25_authority_manifest_sha256": phase25.authority_manifest_sha256,
            "phase25_questions_manifest_sha256": phase25.questions_manifest_sha256,
            "phase25_scope_manifest_sha256": phase25.scope_manifest_sha256,
            "response_received": phase25.response_received,
            "question_count": 10,
            "scope_count": 19,
            "satisfied_question_count": sum(row.satisfied for row in phase25.question_evaluations),
            "satisfied_scope_count": sum(row.satisfied for row in phase25.scope_evaluations),
            "mutual_consistency_verified": phase25.mutual_consistency_verified,
            "selected_scope_bound": selected_scope_bound,
            "rights_verified": rtdsm_verified,
            "current_at_evaluation": rtdsm_current,
            "determination": (
                "RIGHTS_RESPONSE_VERIFIED_REQUIRES_SEPARATE_ACQUISITION_AUTHORITY"
                if rtdsm_verified
                else (
                    "RIGHTS_RESPONSE_BLOCKED"
                    if self.intake.rtdsm.response_received
                    else "RIGHTS_RESPONSE_EVIDENCE_MISSING"
                )
            ),
        }
        if c.canonicalize(
            self.rtdsm_phase25_binding.model_dump(mode="python", exclude={"binding_sha256"})
        ) != c.canonicalize(expected_rtdsm):
            raise ValueError("RTDSM Phase 25 evaluation binding mismatch")
        crsp_consistency = (
            self.intake.crsp.mutual_consistency_status is VerificationStatus.VERIFIED
            and bool(self.intake.crsp.mutual_consistency_evidence_ids)
            and set(self.intake.crsp.mutual_consistency_evidence_ids) <= crsp_verified_ids
        )
        sec_consistency = (
            self.intake.sec.mutual_consistency_status is VerificationStatus.VERIFIED
            and bool(self.intake.sec.mutual_consistency_evidence_ids)
            and set(self.intake.sec.mutual_consistency_evidence_ids) <= sec_verified_ids
        )
        crsp_exact_scope = (
            self.intake.crsp.licensed_party_identity_sha256 is not None
            and self.intake.crsp.executed_agreement_sha256 is not None
            and self.intake.crsp.order_form_or_product_schedule_sha256 is not None
            and self.intake.crsp.product_code == c.CRSP_PRODUCT
            and self.intake.crsp.product_sku_sha256 is not None
            and self.intake.crsp.delivery_id == c.DELIVERY_IDS[0]
            and self.intake.crsp.selected_capability_codes == c.CRSP_CAPABILITY_CODES
            and bool(self.intake.crsp.third_party_rights_evidence_ids)
            and set(self.intake.crsp.third_party_rights_evidence_ids) <= crsp_verified_ids
        )
        sec_source_set_bound = {row.source_code for row in self.sec_policy_documents} == {
            row[0] for row in c.SEC_ACCEPTED_SOURCE_ROWS
        }
        expected_product_facts = (
            (
                len(c.CRSP_REQUIREMENT_ROWS),
                sum(row.satisfied for row in self.crsp_requirement_evaluations),
                self.intake.crsp.response_received,
                bool(self.authority_evidence)
                and all(row.authority_verified for row in self.authority_evidence)
                and crsp_consistency
                and crsp_exact_scope,
                bool(self.authority_evidence)
                and all(row.current_at_evaluation for row in self.authority_evidence),
            ),
            (
                len(c.SEC_REQUIREMENT_ROWS),
                sum(row.satisfied for row in self.sec_requirement_evaluations),
                self.intake.sec.review_performed,
                bool(self.sec_policy_documents)
                and all(row.independently_verified for row in self.sec_policy_documents)
                and sec_consistency
                and sec_source_set_bound,
                bool(self.sec_policy_documents)
                and all(row.current_at_evaluation for row in self.sec_policy_documents),
            ),
            (
                29,
                self.rtdsm_phase25_binding.satisfied_question_count
                + self.rtdsm_phase25_binding.satisfied_scope_count,
                self.intake.rtdsm.response_received,
                rtdsm_verified,
                rtdsm_current,
            ),
        )
        expected_product_manifests = (
            self.crsp_requirements_manifest_sha256,
            self.sec_requirements_manifest_sha256,
            c.domain_sha256(
                c.RTDSM_REQUIREMENTS_MANIFEST_DOMAIN,
                {
                    "questions": self.rtdsm_phase25_binding.phase25_questions_manifest_sha256,
                    "scope": self.rtdsm_phase25_binding.phase25_scope_manifest_sha256,
                },
            ),
        )
        for product, facts, expected_manifest in zip(
            self.product_evaluations,
            expected_product_facts,
            expected_product_manifests,
            strict=True,
        ):
            required, satisfied, present, independent, current = facts
            if (
                product.required_count != required
                or product.satisfied_count != satisfied
                or product.requirements_manifest_sha256 != expected_manifest
                or product.evidence_present is not present
                or product.independently_verified is not independent
                or product.current_at_evaluation is not current
            ):
                raise ValueError("selected product aggregate mismatch")
        rtdsm_verified_ids = {
            row.immutable_evidence_id
            for row in self.intake.rtdsm.authority_evidence
            if authority_is_verified(row)
            and authority_is_current(row, self.intake.evaluated_at_utc)
        }
        composition_ids = set(self.intake.composition_consistency_evidence_ids)
        composition_consistent = (
            self.intake.composition_consistency_status is VerificationStatus.VERIFIED
            and bool(composition_ids)
            and composition_ids <= crsp_verified_ids | sec_verified_ids | rtdsm_verified_ids
            and bool(composition_ids & crsp_verified_ids)
            and bool(composition_ids & sec_verified_ids)
            and bool(composition_ids & rtdsm_verified_ids)
        )
        expected_verified = (
            all(
                row.state is EvidenceState.VERIFIED_EVIDENCE_RECORDED
                for row in self.product_evaluations
            )
            and composition_consistent
        )
        if self.verified_evidence_recorded is not expected_verified:
            raise ValueError("verified evidence aggregate mismatch")
        if self.current_rights_evidence_for_exact_composition is not expected_verified:
            raise ValueError("current rights evidence aggregate mismatch")
        any_evidence = any(row.evidence_present for row in self.product_evaluations)
        expected_determination = (
            Determination.VERIFIED_EVIDENCE_RECORDED_REQUIRES_SEPARATE_ACQUISITION_AUTHORITY
            if expected_verified
            else (
                Determination.COMPOSITION_RIGHTS_ENTITLEMENT_EVIDENCE_BLOCKED
                if any_evidence
                else Determination.COMPOSITION_RIGHTS_ENTITLEMENT_EVIDENCE_MISSING
            )
        )
        if self.determination is not expected_determination:
            raise ValueError("aggregate determination mismatch")
        expected_block_reason = (
            c.VERIFIED_BLOCK_REASON if expected_verified else c.INCOMPLETE_BLOCK_REASON
        )
        if self.block_reason != expected_block_reason:
            raise ValueError("aggregate block reason mismatch")
        evidence_payload = {
            "intake": self.intake,
            "authority_manifest_sha256": self.authority_manifest_sha256,
            "crsp_requirements_manifest_sha256": self.crsp_requirements_manifest_sha256,
            "rtdsm_binding_sha256": self.rtdsm_phase25_binding.binding_sha256,
            "sec_policy_documents_manifest_sha256": self.sec_policy_documents_manifest_sha256,
            "sec_requirements_manifest_sha256": self.sec_requirements_manifest_sha256,
        }
        expected_bundle = c.domain_sha256(c.EVIDENCE_BUNDLE_DOMAIN, evidence_payload)
        if self.evidence_bundle_sha256 != expected_bundle or self.evidence_bundle_id != (
            c.uuid_from_sha256(c.EVIDENCE_BUNDLE_NAMESPACE, expected_bundle)
        ):
            raise ValueError("evidence bundle identity mismatch")
        payload = self.model_dump(mode="python", exclude={"artifact_id", "artifact_sha256"})
        expected_hash = c.domain_sha256(c.ARTIFACT_DOMAIN, payload)
        if self.artifact_sha256 != expected_hash or self.artifact_id != c.uuid_from_sha256(
            c.ARTIFACT_NAMESPACE, expected_hash
        ):
            raise ValueError("artifact identity mismatch")
        return self


__all__ = [
    "AuthorityEvidenceRecord",
    "CRSPRightsEntitlementIntake",
    "Determination",
    "EvidenceCondition",
    "EvidenceState",
    "Outcome",
    "Phase27EvidenceIntake",
    "Phase27RightsEntitlementEvidencePackage",
    "RTDSMPhase25EvaluationBinding",
    "RequirementAnswerInput",
    "RequirementEvaluation",
    "SECPolicyDocument",
    "SECPolicyDocumentInput",
    "SECPolicyRevalidationIntake",
    "SanitizedAuthorityEvidenceInput",
    "SanitizedQuestionAnswerInput",
    "SanitizedRightsResponseConditionInput",
    "SanitizedRightsResponseIntake",
    "SanitizedScopeAnswerInput",
    "SelectedProductEvidenceEvaluation",
    "authority_is_current",
    "authority_is_verified",
    "authority_manifest_sha256",
    "build_requirement_evaluations",
    "phase25_evaluator_intake",
    "products_manifest_sha256",
    "requirements_manifest_sha256",
    "sec_documents_manifest_sha256",
]
