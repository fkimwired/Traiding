"""Strict Phase 25 contracts for rights-response evaluation and source research."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from fable5_data.phase25 import canonical as c

SHA256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
GitSHA = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]
EvidenceId = Annotated[str, StringConstraints(pattern=r"^[A-Z0-9][A-Z0-9._:-]{2,127}$")]
ClosedText = Annotated[str, StringConstraints(min_length=1, max_length=2400)]
ShortText = Annotated[str, StringConstraints(min_length=1, max_length=512)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")


class EvaluationState(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    CONDITIONAL = "CONDITIONAL"
    MISSING = "MISSING"


class AggregateOutcome(StrEnum):
    PASS = "PASS"
    BLOCKED = "BLOCKED"


class Determination(StrEnum):
    RIGHTS_RESPONSE_EVIDENCE_MISSING = "RIGHTS_RESPONSE_EVIDENCE_MISSING"
    RIGHTS_RESPONSE_BLOCKED = "RIGHTS_RESPONSE_BLOCKED"
    RIGHTS_RESPONSE_VERIFIED_REQUIRES_SEPARATE_ACQUISITION_AUTHORITY = (
        "RIGHTS_RESPONSE_VERIFIED_REQUIRES_SEPARATE_ACQUISITION_AUTHORITY"
    )


class VerificationStatus(StrEnum):
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    UNVERIFIED = "UNVERIFIED"


class ProvenanceType(StrEnum):
    EXECUTED_AGREEMENT = "EXECUTED_AGREEMENT"
    AUTHENTICATED_PROVIDER_PORTAL = "AUTHENTICATED_PROVIDER_PORTAL"
    CRYPTOGRAPHICALLY_SIGNED_RESPONSE = "CRYPTOGRAPHICALLY_SIGNED_RESPONSE"
    RIGHTS_HOLDER_RECORD = "RIGHTS_HOLDER_RECORD"
    EMAIL_ONLY = "EMAIL_ONLY"
    PUBLIC_WEBPAGE_ONLY = "PUBLIC_WEBPAGE_ONLY"
    VERBAL_STATEMENT = "VERBAL_STATEMENT"
    SCREENSHOT_ONLY = "SCREENSHOT_ONLY"


VERIFIABLE_PROVENANCE = frozenset(
    {
        ProvenanceType.EXECUTED_AGREEMENT,
        ProvenanceType.AUTHENTICATED_PROVIDER_PORTAL,
        ProvenanceType.CRYPTOGRAPHICALLY_SIGNED_RESPONSE,
        ProvenanceType.RIGHTS_HOLDER_RECORD,
    }
)


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


class ScopeCode(StrEnum):
    PRODUCT = "PRODUCT"
    REQUESTED_SERIES = "REQUESTED_SERIES"
    PCPI_AND_BLS_ORIGIN = "PCPI_AND_BLS_ORIGIN"
    DELIVERY_METHOD_AND_SURFACE = "DELIVERY_METHOD_AND_SURFACE"
    LICENSED_PARTY = "LICENSED_PARTY"
    ACCOUNT_OR_ENTITLEMENT = "ACCOUNT_OR_ENTITLEMENT"
    PERMITTED_USERS_AND_DEVICES = "PERMITTED_USERS_AND_DEVICES"
    ENVIRONMENTS = "ENVIRONMENTS"
    AUTOMATED_ACCESS_LIMITS = "AUTOMATED_ACCESS_LIMITS"
    RAW_PAYLOAD_STORAGE = "RAW_PAYLOAD_STORAGE"
    IMMUTABLE_SNAPSHOT_STORAGE = "IMMUTABLE_SNAPSHOT_STORAGE"
    BACKUPS_AND_REPRODUCIBILITY = "BACKUPS_AND_REPRODUCIBILITY"
    NORMALIZATION_AND_POINT_IN_TIME = "NORMALIZATION_AND_POINT_IN_TIME"
    INTERNAL_RESEARCH_USES = "INTERNAL_RESEARCH_USES"
    DERIVED_ARTIFACTS = "DERIVED_ARTIFACTS"
    DISPLAY_EXPORT_SHARING_PUBLICATION_REDISTRIBUTION = (
        "DISPLAY_EXPORT_SHARING_PUBLICATION_REDISTRIBUTION"
    )
    ATTRIBUTION = "ATTRIBUTION"
    RETENTION_DELETION_TERMINATION = "RETENTION_DELETION_TERMINATION"
    REVOCATION_AND_REVALIDATION = "REVOCATION_AND_REVALIDATION"


class SourceKind(StrEnum):
    OPEN_SOURCE_REPOSITORY = "OPEN_SOURCE_REPOSITORY"
    OFFICIAL_DOCUMENT = "OFFICIAL_DOCUMENT"


class RevisionKind(StrEnum):
    COMMIT = "COMMIT"
    CONTENT_SHA256 = "CONTENT_SHA256"


class PatternStatus(StrEnum):
    DOCUMENTED_NOT_IMPLEMENTED = "DOCUMENTED_NOT_IMPLEMENTED"


class RightsResponseConditionInput(StrictModel):
    condition_id: EvidenceId
    normalized_condition: ClosedText
    control_id: EvidenceId | None = None
    acceptance_test_id: EvidenceId | None = None
    enforceable: bool = False
    acceptance_test_passed: bool = False


class EnforceableCondition(RightsResponseConditionInput):
    schema_version: str
    condition_sha256: SHA256

    @model_validator(mode="after")
    def validate_hash(self) -> Self:
        payload = self.model_dump(mode="python", exclude={"condition_sha256"})
        if self.schema_version != c.PHASE25_CONDITION_SCHEMA_VERSION:
            raise ValueError("condition schema mismatch")
        if self.condition_sha256 != c.domain_sha256(c.PHASE25_CONDITION_HASH_DOMAIN, payload):
            raise ValueError("condition hash mismatch")
        return self


class AuthorityEvidenceInput(StrictModel):
    responder_organization: ShortText
    responder_stable_identity: ShortText
    responder_role: ShortText
    authority_basis: ClosedText
    rights_holding_legal_entity: ShortText
    response_date_utc: datetime
    effective_date_utc: datetime
    expiry_date_utc: datetime | None = None
    expiry_not_applicable_reason: ShortText | None = None
    governing_agreement: ShortText
    governing_terms_version: ShortText
    immutable_evidence_id: EvidenceId
    immutable_evidence_sha256: SHA256
    authenticated_provenance: ProvenanceType
    provenance_locator_sha256: SHA256
    independent_verification_status: VerificationStatus
    independent_verifier_identity_sha256: SHA256
    responder_identity_authenticated: bool
    authority_basis_verified: bool

    @model_validator(mode="after")
    def validate_dates_and_expiry(self) -> Self:
        for value in (self.response_date_utc, self.effective_date_utc, self.expiry_date_utc):
            if value is not None and (value.utcoffset() is None or value.astimezone(UTC) != value):
                raise ValueError("authority dates must be UTC")
        if (self.expiry_date_utc is None) == (self.expiry_not_applicable_reason is None):
            raise ValueError("record exactly one expiry date or no-expiry explanation")
        return self


class AuthorityEvidence(AuthorityEvidenceInput):
    schema_version: str
    authority_verified: bool
    authority_record_sha256: SHA256

    @model_validator(mode="after")
    def validate_authority(self) -> Self:
        expected_verified = (
            self.authenticated_provenance in VERIFIABLE_PROVENANCE
            and self.independent_verification_status is VerificationStatus.VERIFIED
            and self.responder_identity_authenticated
            and self.authority_basis_verified
        )
        if self.authority_verified is not expected_verified:
            raise ValueError("authority verification state mismatch")
        payload = self.model_dump(mode="python", exclude={"authority_record_sha256"})
        if self.schema_version != c.PHASE25_AUTHORITY_SCHEMA_VERSION:
            raise ValueError("authority schema mismatch")
        if self.authority_record_sha256 != c.domain_sha256(
            c.PHASE25_AUTHORITY_HASH_DOMAIN, payload
        ):
            raise ValueError("authority record hash mismatch")
        return self


class QuestionAnswerInput(StrictModel):
    code: QuestionCode
    state: EvaluationState
    normalized_finding: ClosedText
    evidence_ids: tuple[EvidenceId, ...] = ()
    conditions: tuple[RightsResponseConditionInput, ...] = ()


class ScopeAnswerInput(StrictModel):
    code: ScopeCode
    state: EvaluationState
    normalized_determination: ClosedText
    normalized_value_sha256: SHA256
    evidence_ids: tuple[EvidenceId, ...] = ()
    conditions: tuple[RightsResponseConditionInput, ...] = ()

    @model_validator(mode="after")
    def prohibit_raw_account_identifier(self) -> Self:
        if (
            self.code is ScopeCode.ACCOUNT_OR_ENTITLEMENT
            and self.normalized_determination != "SANITIZED_HASH_ONLY"
        ):
            raise ValueError("account or entitlement must be represented only by a hash")
        return self


class RightsResponseIntake(StrictModel):
    schema_version: str
    response_received: bool
    authority_evidence: tuple[AuthorityEvidenceInput, ...] = ()
    question_answers: tuple[QuestionAnswerInput, ...] = ()
    scope_answers: tuple[ScopeAnswerInput, ...] = ()
    mutual_consistency_status: VerificationStatus = VerificationStatus.UNVERIFIED
    mutual_consistency_evidence_ids: tuple[EvidenceId, ...] = ()

    @model_validator(mode="after")
    def validate_intake(self) -> Self:
        if self.schema_version != c.PHASE25_INTAKE_SCHEMA_VERSION:
            raise ValueError("intake schema mismatch")
        if not self.response_received and (
            self.authority_evidence
            or self.question_answers
            or self.scope_answers
            or self.mutual_consistency_status is not VerificationStatus.UNVERIFIED
            or self.mutual_consistency_evidence_ids
        ):
            raise ValueError("response metadata requires response_received")
        if self.mutual_consistency_status is VerificationStatus.UNVERIFIED:
            if self.mutual_consistency_evidence_ids:
                raise ValueError("unverified consistency cannot cite evidence")
        elif not self.mutual_consistency_evidence_ids:
            raise ValueError("verified or failed consistency requires evidence")
        if len({row.code for row in self.question_answers}) != len(self.question_answers):
            raise ValueError("duplicate question answer")
        if len({row.code for row in self.scope_answers}) != len(self.scope_answers):
            raise ValueError("duplicate scope answer")
        if len({row.immutable_evidence_id for row in self.authority_evidence}) != len(
            self.authority_evidence
        ):
            raise ValueError("duplicate authority evidence id")
        return self


def _conditions_satisfied(conditions: tuple[EnforceableCondition, ...]) -> bool:
    return bool(conditions) and all(
        row.control_id is not None
        and row.acceptance_test_id is not None
        and row.enforceable
        and row.acceptance_test_passed
        for row in conditions
    )


class QuestionEvaluation(StrictModel):
    schema_version: str
    ordinal: Annotated[int, Field(ge=1, le=10)]
    code: QuestionCode
    phase24_rights_field: str
    question: ClosedText
    state: EvaluationState
    normalized_finding: ClosedText
    evidence_ids: tuple[EvidenceId, ...]
    independently_verified: bool
    conditions: tuple[EnforceableCondition, ...]
    satisfied: bool
    evaluation_sha256: SHA256

    @model_validator(mode="after")
    def validate_evaluation(self) -> Self:
        expected_row = c.PHASE25_QUESTION_ROWS[self.ordinal - 1]
        if (self.code.value, self.phase24_rights_field, self.question) != expected_row:
            raise ValueError("question lineage drifted")
        if self.schema_version != c.PHASE25_QUESTION_SCHEMA_VERSION:
            raise ValueError("question schema mismatch")
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
            expected_satisfied = _conditions_satisfied(self.conditions)
        if not expected or self.satisfied is not expected_satisfied:
            raise ValueError("question state is not fail-closed")
        payload = self.model_dump(mode="python", exclude={"evaluation_sha256"})
        if self.evaluation_sha256 != c.domain_sha256(c.PHASE25_QUESTION_HASH_DOMAIN, payload):
            raise ValueError("question evaluation hash mismatch")
        return self


class ScopeEvaluation(StrictModel):
    schema_version: str
    ordinal: Annotated[int, Field(ge=1, le=19)]
    code: ScopeCode
    requirement: ClosedText
    state: EvaluationState
    normalized_determination: ClosedText
    normalized_value_sha256: SHA256
    evidence_ids: tuple[EvidenceId, ...]
    independently_verified: bool
    conditions: tuple[EnforceableCondition, ...]
    satisfied: bool
    scope_sha256: SHA256

    @model_validator(mode="after")
    def validate_scope(self) -> Self:
        expected_row = c.PHASE25_SCOPE_ROWS[self.ordinal - 1]
        if (self.code.value, self.requirement) != expected_row:
            raise ValueError("scope registry drifted")
        if self.schema_version != c.PHASE25_SCOPE_SCHEMA_VERSION:
            raise ValueError("scope schema mismatch")
        if (
            self.code is ScopeCode.PRODUCT
            and self.state
            in {
                EvaluationState.PASS,
                EvaluationState.CONDITIONAL,
            }
            and self.normalized_determination != c.PHASE25_PRODUCT_NAME
        ):
            raise ValueError("product scope is not exact")
        if (
            self.code is ScopeCode.LICENSED_PARTY
            and self.state
            in {
                EvaluationState.PASS,
                EvaluationState.CONDITIONAL,
            }
            and self.normalized_determination != "INDIVIDUAL_ACCOUNT_HOLDER"
        ):
            raise ValueError("licensed party must be the individual account holder")
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
            expected_satisfied = _conditions_satisfied(self.conditions)
        if not expected or self.satisfied is not expected_satisfied:
            raise ValueError("scope state is not fail-closed")
        payload = self.model_dump(mode="python", exclude={"scope_sha256"})
        if self.scope_sha256 != c.domain_sha256(c.PHASE25_SCOPE_HASH_DOMAIN, payload):
            raise ValueError("scope hash mismatch")
        return self


class SourceEvidence(StrictModel):
    schema_version: str
    ordinal: Annotated[int, Field(ge=1, le=10)]
    code: str
    kind: SourceKind
    url: str
    inspected_revision: str
    revision_kind: RevisionKind
    software_license: str
    license_file: str
    license_blob_oid: str
    inspected_paths: tuple[str, ...]
    provider_abstraction: ClosedText
    request_session_ownership: ClosedText
    timeout_retry_backoff_rate_limit: ClosedText
    schema_validation_normalization: ClosedText
    timestamp_timezone: ClosedText
    corporate_action_revision: ClosedText
    caching_persistence: ClosedText
    error_sanitization: ClosedText
    deterministic_testing: ClosedText
    rights_warning: ClosedText
    unresolved_limitations: ClosedText
    source_sha256: SHA256

    @model_validator(mode="after")
    def validate_source(self) -> Self:
        expected = {
            "schema_version": c.PHASE25_SOURCE_SCHEMA_VERSION,
            "ordinal": self.ordinal,
            **dict(c.PHASE25_SOURCE_ROWS[self.ordinal - 1]),
        }
        if c.canonicalize(
            self.model_dump(mode="python", exclude={"source_sha256"})
        ) != c.canonicalize(expected):
            raise ValueError("source evidence drifted")
        if self.source_sha256 != c.domain_sha256(c.PHASE25_SOURCE_HASH_DOMAIN, expected):
            raise ValueError("source evidence hash mismatch")
        return self


class AdapterPattern(StrictModel):
    schema_version: str
    ordinal: Annotated[int, Field(ge=1, le=11)]
    code: str
    definition: ClosedText
    source_codes: tuple[str, ...]
    adaptation_policy: str
    status: PatternStatus
    pattern_sha256: SHA256

    @model_validator(mode="after")
    def validate_pattern(self) -> Self:
        row = c.PHASE25_PATTERN_ROWS[self.ordinal - 1]
        expected = {
            "schema_version": c.PHASE25_PATTERN_SCHEMA_VERSION,
            "ordinal": self.ordinal,
            "code": row[0],
            "definition": row[1],
            "source_codes": row[2],
            "adaptation_policy": row[3],
            "status": row[4],
        }
        if c.canonicalize(
            self.model_dump(mode="python", exclude={"pattern_sha256"})
        ) != c.canonicalize(expected):
            raise ValueError("adapter pattern drifted")
        if self.pattern_sha256 != c.domain_sha256(c.PHASE25_PATTERN_HASH_DOMAIN, expected):
            raise ValueError("adapter pattern hash mismatch")
        return self


class TransitionRule(StrictModel):
    schema_version: str
    ordinal: Annotated[int, Field(ge=1, le=9)]
    code: str
    rule: ClosedText
    rule_sha256: SHA256

    @model_validator(mode="after")
    def validate_rule(self) -> Self:
        row = c.PHASE25_RULE_ROWS[self.ordinal - 1]
        expected = {
            "schema_version": c.PHASE25_RULE_SCHEMA_VERSION,
            "ordinal": self.ordinal,
            "code": row[0],
            "rule": row[1],
        }
        if c.canonicalize(
            self.model_dump(mode="python", exclude={"rule_sha256"})
        ) != c.canonicalize(expected):
            raise ValueError("transition rule drifted")
        if self.rule_sha256 != c.domain_sha256(c.PHASE25_RULE_HASH_DOMAIN, expected):
            raise ValueError("transition rule hash mismatch")
        return self


def _manifest(domain: str, rows: tuple[BaseModel, ...], field: str) -> str:
    return c.domain_sha256(domain, tuple(getattr(row, field) for row in rows))


def authority_manifest_sha256(rows: tuple[AuthorityEvidence, ...]) -> str:
    return _manifest(c.PHASE25_AUTHORITY_MANIFEST_HASH_DOMAIN, rows, "authority_record_sha256")


def questions_manifest_sha256(rows: tuple[QuestionEvaluation, ...]) -> str:
    return _manifest(c.PHASE25_QUESTIONS_MANIFEST_HASH_DOMAIN, rows, "evaluation_sha256")


def scope_manifest_sha256(rows: tuple[ScopeEvaluation, ...]) -> str:
    return _manifest(c.PHASE25_SCOPE_MANIFEST_HASH_DOMAIN, rows, "scope_sha256")


def sources_manifest_sha256(rows: tuple[SourceEvidence, ...]) -> str:
    return _manifest(c.PHASE25_SOURCES_MANIFEST_HASH_DOMAIN, rows, "source_sha256")


def patterns_manifest_sha256(rows: tuple[AdapterPattern, ...]) -> str:
    return _manifest(c.PHASE25_PATTERNS_MANIFEST_HASH_DOMAIN, rows, "pattern_sha256")


def rules_manifest_sha256(rows: tuple[TransitionRule, ...]) -> str:
    return _manifest(c.PHASE25_RULES_MANIFEST_HASH_DOMAIN, rows, "rule_sha256")


class Phase25Package(StrictModel):
    schema_version: str
    artifact_id: UUID
    artifact_sha256: SHA256
    config_sha256: SHA256
    policy_id: str
    policy_sha256: SHA256
    phase24_merge_commit_sha: GitSHA
    phase24_merge_tree_sha: GitSHA
    accepted_phase24_commit_sha: GitSHA
    accepted_phase24_tree_sha: GitSHA
    phase24_artifact_id: UUID
    phase24_artifact_sha256: SHA256
    phase24_artifact_file_sha256: SHA256
    phase24_policy_sha256: SHA256
    phase24_questions_manifest_sha256: SHA256
    product_code: str
    product_name: str
    family: str
    generated_at_utc: datetime
    source_research_at_utc: datetime
    generation_git_sha: GitSHA
    random_seed: Annotated[int, Field(ge=0)]
    trial_count: Annotated[int, Field(ge=0)]
    source_snapshot_id: UUID
    source_snapshot_sha256: SHA256
    evidence_snapshot_id: UUID
    evidence_snapshot_sha256: SHA256
    authority_manifest_sha256: SHA256
    questions_manifest_sha256: SHA256
    scope_manifest_sha256: SHA256
    patterns_manifest_sha256: SHA256
    rules_manifest_sha256: SHA256
    outcome: AggregateOutcome
    determination: Determination
    block_reason: ClosedText
    authority_evidence: tuple[AuthorityEvidence, ...]
    question_evaluations: tuple[QuestionEvaluation, ...]
    scope_evaluations: tuple[ScopeEvaluation, ...]
    source_evidence: tuple[SourceEvidence, ...]
    adapter_patterns: tuple[AdapterPattern, ...]
    transition_rules: tuple[TransitionRule, ...]
    mutual_consistency_status: VerificationStatus
    mutual_consistency_evidence_ids: tuple[EvidenceId, ...]
    mutual_consistency_verified: bool
    phase24_artifact_unchanged: bool
    phase24_merge_is_ancestor: bool
    response_received: bool
    authority_evidence_present: bool
    rights_verified: bool
    provider_contact_performed: bool
    provider_observations_downloaded: bool
    provider_observations_persisted: bool
    credentials_loaded: bool
    production_adapter_activated: bool
    operational_provider_selected: bool
    yfinance_dependency_added: bool
    yahoo_rights_state: str
    runtime_network_disabled: bool
    generation_network_disabled: bool
    verification_network_disabled: bool
    synthetic_tests_only: bool
    database_changed: bool
    api_changed: bool
    research_run_executed: bool
    performance_computed: bool
    strategy_promoted: bool
    risk_limits_changed: bool
    paper_order_submitted: bool
    execution_authorized: bool
    live_path_absent: bool
    llm_trade_decisions_prohibited: bool
    disclaimer: ClosedText

    @model_validator(mode="after")
    def validate_package(self) -> Self:
        fixed = {
            "schema_version": c.PHASE25_ARTIFACT_SCHEMA_VERSION,
            "config_sha256": c.PHASE25_POLICY_SHA256,
            "policy_id": c.PHASE25_POLICY_ID,
            "policy_sha256": c.PHASE25_POLICY_SHA256,
            "phase24_merge_commit_sha": c.PHASE25_PHASE24_MERGE_COMMIT_SHA,
            "phase24_merge_tree_sha": c.PHASE25_PHASE24_MERGE_TREE_SHA,
            "accepted_phase24_commit_sha": c.PHASE25_ACCEPTED_PHASE24_COMMIT_SHA,
            "accepted_phase24_tree_sha": c.PHASE25_ACCEPTED_PHASE24_TREE_SHA,
            "phase24_artifact_id": c.PHASE25_PHASE24_ARTIFACT_ID,
            "phase24_artifact_sha256": c.PHASE25_PHASE24_ARTIFACT_SHA256,
            "phase24_artifact_file_sha256": c.PHASE25_PHASE24_ARTIFACT_FILE_SHA256,
            "phase24_policy_sha256": c.PHASE25_PHASE24_POLICY_SHA256,
            "phase24_questions_manifest_sha256": c.PHASE25_PHASE24_QUESTIONS_MANIFEST_SHA256,
            "product_code": c.PHASE25_PRODUCT_CODE,
            "product_name": c.PHASE25_PRODUCT_NAME,
            "family": c.PHASE25_FAMILY,
            "generated_at_utc": c.PHASE25_GENERATED_AT_UTC,
            "source_research_at_utc": c.PHASE25_SOURCE_RESEARCH_AT_UTC,
            "generation_git_sha": c.PHASE25_GENERATION_GIT_SHA,
            "random_seed": c.PHASE25_RANDOM_SEED,
            "trial_count": c.PHASE25_TRIAL_COUNT,
            "disclaimer": c.PHASE25_DISCLAIMER,
        }
        dumped = self.model_dump(mode="python")
        for name, expected in fixed.items():
            if c.canonicalize(dumped[name]) != c.canonicalize(expected):
                raise ValueError(f"package scalar drifted: {name}")
        if tuple(row.code.value for row in self.question_evaluations) != tuple(
            row[0] for row in c.PHASE25_QUESTION_ROWS
        ) or self.questions_manifest_sha256 != questions_manifest_sha256(self.question_evaluations):
            raise ValueError("question registry mismatch")
        if tuple(row.code.value for row in self.scope_evaluations) != tuple(
            row[0] for row in c.PHASE25_SCOPE_ROWS
        ) or self.scope_manifest_sha256 != scope_manifest_sha256(self.scope_evaluations):
            raise ValueError("scope registry mismatch")
        if tuple(row.code for row in self.source_evidence) != tuple(
            str(row["code"]) for row in c.PHASE25_SOURCE_ROWS
        ) or self.source_snapshot_sha256 != sources_manifest_sha256(self.source_evidence):
            raise ValueError("source registry mismatch")
        if tuple(row.code for row in self.adapter_patterns) != tuple(
            row[0] for row in c.PHASE25_PATTERN_ROWS
        ) or self.patterns_manifest_sha256 != patterns_manifest_sha256(self.adapter_patterns):
            raise ValueError("pattern registry mismatch")
        if tuple(row.code for row in self.transition_rules) != tuple(
            row[0] for row in c.PHASE25_RULE_ROWS
        ) or self.rules_manifest_sha256 != rules_manifest_sha256(self.transition_rules):
            raise ValueError("transition-rule registry mismatch")
        if self.authority_manifest_sha256 != authority_manifest_sha256(self.authority_evidence):
            raise ValueError("authority manifest mismatch")
        evidence_ids = {row.immutable_evidence_id for row in self.authority_evidence}
        verified_ids = {
            row.immutable_evidence_id for row in self.authority_evidence if row.authority_verified
        }
        for question in self.question_evaluations:
            if not set(question.evidence_ids) <= evidence_ids:
                raise ValueError("evaluation cites missing evidence")
            if question.independently_verified and not set(question.evidence_ids) <= verified_ids:
                raise ValueError("evaluation cites unverified evidence")
        for scope in self.scope_evaluations:
            if not set(scope.evidence_ids) <= evidence_ids:
                raise ValueError("evaluation cites missing evidence")
            if scope.independently_verified and not set(scope.evidence_ids) <= verified_ids:
                raise ValueError("evaluation cites unverified evidence")
        if not set(self.mutual_consistency_evidence_ids) <= evidence_ids:
            raise ValueError("consistency evaluation cites missing evidence")
        expected_consistency_verified = (
            self.mutual_consistency_status is VerificationStatus.VERIFIED
            and bool(self.mutual_consistency_evidence_ids)
            and set(self.mutual_consistency_evidence_ids) <= verified_ids
        )
        if self.mutual_consistency_verified is not expected_consistency_verified:
            raise ValueError("mutual consistency is not independently verified")
        authority_ok = bool(self.authority_evidence) and all(
            row.authority_verified for row in self.authority_evidence
        )
        questions_ok = all(row.satisfied for row in self.question_evaluations)
        scope_ok = all(row.satisfied for row in self.scope_evaluations)
        positive = (
            self.response_received
            and authority_ok
            and questions_ok
            and scope_ok
            and self.mutual_consistency_verified
        )
        if self.authority_evidence_present is not bool(self.authority_evidence):
            raise ValueError("authority evidence presence mismatch")
        if self.rights_verified is not positive:
            raise ValueError("rights determination is not fail-closed")
        expected_outcome = AggregateOutcome.PASS if positive else AggregateOutcome.BLOCKED
        if self.outcome is not expected_outcome:
            raise ValueError("aggregate outcome mismatch")
        expected_determination = (
            Determination.RIGHTS_RESPONSE_VERIFIED_REQUIRES_SEPARATE_ACQUISITION_AUTHORITY
            if positive
            else (
                Determination.RIGHTS_RESPONSE_EVIDENCE_MISSING
                if not self.response_received
                else Determination.RIGHTS_RESPONSE_BLOCKED
            )
        )
        if self.determination is not expected_determination:
            raise ValueError("aggregate determination mismatch")
        fixed_boundaries = {
            name: value
            for name, value in c.PHASE25_BOUNDARY_VALUES.items()
            if name not in {"response_received", "authority_evidence_present", "rights_verified"}
        }
        for name, expected in fixed_boundaries.items():
            if dumped[name] != expected:
                raise ValueError(f"operational boundary drifted: {name}")
        if self.source_snapshot_id != c.uuid_from_sha256(
            c.PHASE25_SOURCE_SNAPSHOT_NAMESPACE, self.source_snapshot_sha256
        ):
            raise ValueError("source snapshot identity mismatch")
        if self.evidence_snapshot_sha256 != c.domain_sha256(
            c.PHASE25_AUTHORITY_MANIFEST_HASH_DOMAIN,
            {
                "authority": self.authority_manifest_sha256,
                "questions": self.questions_manifest_sha256,
                "scope": self.scope_manifest_sha256,
                "mutual_consistency_status": self.mutual_consistency_status,
                "mutual_consistency_evidence_ids": self.mutual_consistency_evidence_ids,
            },
        ) or self.evidence_snapshot_id != c.uuid_from_sha256(
            c.PHASE25_EVIDENCE_SNAPSHOT_NAMESPACE, self.evidence_snapshot_sha256
        ):
            raise ValueError("evidence snapshot identity mismatch")
        identity_sha = c.domain_sha256(
            "phase25-artifact-identity-v1",
            {"policy": self.policy_sha256, "evidence": self.evidence_snapshot_sha256},
        )
        if self.artifact_id != c.identity(identity_sha):
            raise ValueError("artifact identity mismatch")
        unhashed = self.model_dump(mode="python", exclude={"artifact_sha256"})
        if self.artifact_sha256 != c.domain_sha256(c.PHASE25_ARTIFACT_HASH_DOMAIN, unhashed):
            raise ValueError("artifact hash mismatch")
        return self


__all__ = [
    "AdapterPattern",
    "AuthorityEvidence",
    "AuthorityEvidenceInput",
    "EnforceableCondition",
    "EvaluationState",
    "Phase25Package",
    "QuestionAnswerInput",
    "QuestionEvaluation",
    "RightsResponseConditionInput",
    "RightsResponseIntake",
    "ScopeAnswerInput",
    "ScopeEvaluation",
    "SourceEvidence",
    "TransitionRule",
    "authority_manifest_sha256",
    "patterns_manifest_sha256",
    "questions_manifest_sha256",
    "rules_manifest_sha256",
    "scope_manifest_sha256",
    "sources_manifest_sha256",
]
