"""Strict hash-bound contracts for Phase 14 eligibility assessment evidence."""

from __future__ import annotations

import re
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

from fable5_data.phase13.canonical import PHASE13_RUN_NAMESPACE
from fable5_data.phase13.contracts import (
    PHASE13_CAPABILITY_ORDER,
    PHASE13_CHECK_ORDER,
    IdempotencyKey,
    QualificationCapability,
    QualificationCheckStatus,
    QualificationOutcome,
    QualificationReasonCode,
    QualificationSourceKind,
)
from fable5_data.phase14.canonical import (
    PHASE14_ARTIFACT_HASH_DOMAIN,
    PHASE14_ASSESSMENT_NAMESPACE,
    PHASE14_CHECK_HASH_DOMAIN,
    PHASE14_PAYLOAD_HASH_DOMAIN,
    PHASE14_PAYLOAD_MANIFEST_HASH_DOMAIN,
    PHASE14_POLICY_ID,
    PHASE14_POLICY_SHA256,
    PHASE14_REQUEST_HASH_DOMAIN,
    domain_sha256,
    identity,
)

SHA256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
GitSHA = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]
Identifier = Annotated[
    str,
    StringConstraints(min_length=1, max_length=256, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:/-]*$"),
]
SanitizedValue = Annotated[str, StringConstraints(min_length=1, max_length=256)]

PHASE14_ARTIFACT_SCHEMA_VERSION: Literal["phase14-research-ingestion-eligibility-v1"] = (
    "phase14-research-ingestion-eligibility-v1"
)
PHASE14_PAYLOAD_SCHEMA_VERSION: Literal["phase14-research-ingestion-eligibility-payload-v1"] = (
    "phase14-research-ingestion-eligibility-payload-v1"
)
PHASE14_CHECK_SCHEMA_VERSION: Literal["phase14-research-ingestion-eligibility-check-v1"] = (
    "phase14-research-ingestion-eligibility-check-v1"
)
PHASE14_DISCLAIMER: Literal[
    "Eligibility-assessment evidence only; no research dataset, research authorization, "
    "strategy result, promotion, execution authority, performance claim, or personalized "
    "investment advice."
] = (
    "Eligibility-assessment evidence only; no research dataset, research authorization, "
    "strategy result, promotion, execution authority, performance claim, or personalized "
    "investment advice."
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")


def _utc(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value.astimezone(UTC)


def _sanitized(value: str, field_name: str) -> str:
    lowered = value.casefold()
    if (
        "\n" in value
        or "\r" in value
        or "\x00" in value
        or "token" in lowered
        or "secret" in lowered
        or "api_key" in lowered
        or "apikey" in lowered
        or "?" in value
        or "=" in value
    ):
        raise ValueError(f"{field_name} must be sanitized")
    return value


def validate_code_git_sha(value: str | None) -> str:
    if value is None or re.fullmatch(r"[0-9a-f]{40}", value) is None:
        raise ValueError("phase14 code identity is unavailable")
    return value


class ResearchIngestionEligibilityOutcome(StrEnum):
    MOCK_PROOF_COMPLETE = "MOCK_PROOF_COMPLETE"
    BLOCKED = "BLOCKED"


class ResearchIngestionEligibilityCheckStatus(StrEnum):
    PASS = "PASS"
    BLOCKED = "BLOCKED"
    UNCOMPUTABLE = "UNCOMPUTABLE"


class ResearchIngestionEligibilityCheckCode(StrEnum):
    QUALIFICATION_IDENTITY_INTEGRITY = "QUALIFICATION_IDENTITY_INTEGRITY"
    QUALIFICATION_SOURCE_KIND_ALLOWED = "QUALIFICATION_SOURCE_KIND_ALLOWED"
    QUALIFICATION_OUTCOME_ELIGIBLE_OR_MOCK = "QUALIFICATION_OUTCOME_ELIGIBLE_OR_MOCK"
    CAPABILITY_MANIFEST_COMPLETE_PASSING = "CAPABILITY_MANIFEST_COMPLETE_PASSING"
    QUALIFICATION_CHECKS_COMPLETE_PASSING = "QUALIFICATION_CHECKS_COMPLETE_PASSING"
    EXTERNAL_REQUEST_EVIDENCE_COMPLETE_OR_MOCK = "EXTERNAL_REQUEST_EVIDENCE_COMPLETE_OR_MOCK"
    INDEPENDENT_RIGHTS_REFERENCE_PRESENT_OR_MOCK = "INDEPENDENT_RIGHTS_REFERENCE_PRESENT_OR_MOCK"
    USE_RIGHTS_CURRENT_OR_MOCK = "USE_RIGHTS_CURRENT_OR_MOCK"
    USE_RIGHTS_SCOPE_SUFFICIENT_OR_MOCK = "USE_RIGHTS_SCOPE_SUFFICIENT_OR_MOCK"
    LICENSED_PAYLOAD_ABSENT = "LICENSED_PAYLOAD_ABSENT"
    RESEARCH_SNAPSHOT_ABSENT = "RESEARCH_SNAPSHOT_ABSENT"
    PROMOTION_EXECUTION_AUTHORITY_ABSENT = "PROMOTION_EXECUTION_AUTHORITY_ABSENT"


PHASE14_CHECK_ORDER: tuple[ResearchIngestionEligibilityCheckCode, ...] = tuple(
    ResearchIngestionEligibilityCheckCode
)


class ResearchIngestionEligibilityReasonCode(StrEnum):
    CHECK_PASSED = "check_passed"
    MOCK_NOT_APPLICABLE = "mock_not_applicable"
    SOURCE_KIND_NOT_ALLOWED = "source_kind_not_allowed"
    QUALIFICATION_OUTCOME_NOT_ELIGIBLE = "qualification_outcome_not_eligible"
    CAPABILITY_MANIFEST_NOT_PASSING = "capability_manifest_not_passing"
    QUALIFICATION_CHECKS_NOT_PASSING = "qualification_checks_not_passing"
    EXTERNAL_REQUEST_EVIDENCE_INCOMPLETE = "external_request_evidence_incomplete"
    INDEPENDENT_RIGHTS_REFERENCE_UNVERIFIED = "independent_rights_reference_unverified"
    RIGHTS_REFERENCE_MISSING = "rights_reference_missing"
    RIGHTS_NOT_CURRENT = "rights_not_current"
    RIGHTS_SCOPE_INSUFFICIENT = "rights_scope_insufficient"
    AUTHORITY_BOUNDARY_VIOLATION = "authority_boundary_violation"


class ResearchIngestionEligibilityCreateRequest(StrictModel):
    assessment_idempotency_key: IdempotencyKey
    qualification_id: UUID


class ResearchIngestionEligibilityPayload(StrictModel):
    schema_version: Literal["phase14-research-ingestion-eligibility-payload-v1"] = (
        PHASE14_PAYLOAD_SCHEMA_VERSION
    )
    ordinal: int = Field(ge=1, le=6)
    capability: QualificationCapability
    source_status: QualificationCheckStatus
    source_reason_code: QualificationReasonCode
    decision_time_utc: datetime
    event_time_min_utc: datetime | None = None
    event_time_max_utc: datetime | None = None
    available_at_min_utc: datetime | None = None
    available_at_max_utc: datetime | None = None
    record_count: int = Field(ge=0, le=100_000)
    missingness_count: int = Field(ge=0, le=100_000)
    revision_count: int = Field(ge=0, le=100_000)
    raw_evidence_sha256: SHA256 | None = None
    normalized_evidence_sha256: SHA256 | None = None
    schema_identity_sha256: SHA256 | None = None
    request_evidence_count: int = Field(ge=0, le=5)
    request_evidence_sha256s: tuple[SHA256, ...]
    source_capability_manifest_sha256: SHA256
    payload_sha256: SHA256

    @field_validator(
        "decision_time_utc",
        "event_time_min_utc",
        "event_time_max_utc",
        "available_at_min_utc",
        "available_at_max_utc",
    )
    @classmethod
    def normalize_times(cls, value: datetime | None, info: object) -> datetime | None:
        return None if value is None else _utc(value, getattr(info, "field_name", "payload time"))

    @model_validator(mode="after")
    def validate_payload(self) -> Self:
        if self.ordinal != PHASE13_CAPABILITY_ORDER.index(self.capability) + 1:
            raise ValueError("payload ordinal must match the frozen capability registry")
        for minimum, maximum, label in (
            (self.event_time_min_utc, self.event_time_max_utc, "event"),
            (self.available_at_min_utc, self.available_at_max_utc, "availability"),
        ):
            if (minimum is None) is not (maximum is None):
                raise ValueError(f"{label} range must be jointly present")
            if minimum is not None and maximum is not None and minimum > maximum:
                raise ValueError(f"{label} range is invalid")
        if tuple(sorted(set(self.request_evidence_sha256s))) != (self.request_evidence_sha256s):
            raise ValueError("request evidence hashes must be unique and sorted")
        if self.request_evidence_count != len(self.request_evidence_sha256s):
            raise ValueError("request evidence count must match projected hashes")
        payload = self.model_dump(mode="python", exclude={"payload_sha256"})
        if self.payload_sha256 != domain_sha256(PHASE14_PAYLOAD_HASH_DOMAIN, payload):
            raise ValueError("payload hash must bind its complete preimage")
        return self


class ResearchIngestionEligibilityCheck(StrictModel):
    schema_version: Literal["phase14-research-ingestion-eligibility-check-v1"] = (
        PHASE14_CHECK_SCHEMA_VERSION
    )
    ordinal: int = Field(ge=1, le=12)
    code: ResearchIngestionEligibilityCheckCode
    status: ResearchIngestionEligibilityCheckStatus
    reason_code: ResearchIngestionEligibilityReasonCode
    observed_value: SanitizedValue | None = None
    threshold_value: SanitizedValue | None = None
    evidence_sha256s: tuple[SHA256, ...]
    check_sha256: SHA256

    @field_validator("observed_value", "threshold_value")
    @classmethod
    def sanitize_values(cls, value: str | None, info: object) -> str | None:
        return None if value is None else _sanitized(value, getattr(info, "field_name", "value"))

    @model_validator(mode="after")
    def validate_check(self) -> Self:
        if self.ordinal != PHASE14_CHECK_ORDER.index(self.code) + 1:
            raise ValueError("eligibility check ordinal must match the frozen registry")
        if tuple(sorted(set(self.evidence_sha256s))) != self.evidence_sha256s:
            raise ValueError("eligibility check evidence hashes must be unique and sorted")
        if not self.evidence_sha256s:
            raise ValueError("eligibility check requires hash-bound evidence")
        passing_reasons = {
            ResearchIngestionEligibilityReasonCode.CHECK_PASSED,
            ResearchIngestionEligibilityReasonCode.MOCK_NOT_APPLICABLE,
        }
        if self.status is ResearchIngestionEligibilityCheckStatus.PASS:
            if self.reason_code not in passing_reasons:
                raise ValueError("passing eligibility check has an invalid reason")
        elif self.reason_code in passing_reasons:
            raise ValueError("nonpassing eligibility check cannot use a passing reason")
        mock_only_codes = {
            ResearchIngestionEligibilityCheckCode.EXTERNAL_REQUEST_EVIDENCE_COMPLETE_OR_MOCK,
            ResearchIngestionEligibilityCheckCode.INDEPENDENT_RIGHTS_REFERENCE_PRESENT_OR_MOCK,
            ResearchIngestionEligibilityCheckCode.USE_RIGHTS_CURRENT_OR_MOCK,
            ResearchIngestionEligibilityCheckCode.USE_RIGHTS_SCOPE_SUFFICIENT_OR_MOCK,
        }
        if (
            self.reason_code is ResearchIngestionEligibilityReasonCode.MOCK_NOT_APPLICABLE
            and self.code not in mock_only_codes
        ):
            raise ValueError("mock-not-applicable is restricted to external or rights checks")
        payload = self.model_dump(mode="python", exclude={"check_sha256"})
        if self.check_sha256 != domain_sha256(PHASE14_CHECK_HASH_DOMAIN, payload):
            raise ValueError("eligibility check hash must bind its complete preimage")
        return self


def research_ingestion_eligibility_request_fingerprint(
    *,
    request: ResearchIngestionEligibilityCreateRequest,
    code_version_git_sha: str,
) -> str:
    """Bind semantic input, frozen policy, and code without the idempotency key."""

    return domain_sha256(
        PHASE14_REQUEST_HASH_DOMAIN,
        {
            "schema_version": PHASE14_ARTIFACT_SCHEMA_VERSION,
            "qualification_id": request.qualification_id,
            "policy_id": PHASE14_POLICY_ID,
            "policy_sha256": PHASE14_POLICY_SHA256,
            "code_version_git_sha": validate_code_git_sha(code_version_git_sha),
        },
    )


def research_ingestion_eligibility_payload_manifest_sha256(
    payloads: tuple[ResearchIngestionEligibilityPayload, ...],
) -> str:
    return domain_sha256(
        PHASE14_PAYLOAD_MANIFEST_HASH_DOMAIN,
        {
            "schema_version": PHASE14_PAYLOAD_SCHEMA_VERSION,
            "payload_sha256s": tuple(item.payload_sha256 for item in payloads),
        },
    )


class ResearchIngestionEligibilityArtifact(StrictModel):
    schema_version: Literal["phase14-research-ingestion-eligibility-v1"]
    assessment_id: UUID
    assessment_idempotency_key: IdempotencyKey
    request_fingerprint_sha256: SHA256
    artifact_sha256: SHA256
    policy_id: Literal["phase14-research-ingestion-eligibility-policy-v1"]
    policy_sha256: SHA256
    qualification_id: UUID
    qualification_request_fingerprint_sha256: SHA256
    qualification_artifact_sha256: SHA256
    qualification_capture_manifest_sha256: SHA256
    qualification_source_kind: QualificationSourceKind
    qualification_outcome: QualificationOutcome
    qualification_rights_attestation_id: Identifier | None = None
    qualification_rights_attestation_sha256: SHA256 | None = None
    qualification_code_version_git_sha: GitSHA
    qualification_capability_manifest_sha256s: tuple[SHA256, ...]
    qualification_check_sha256s: tuple[SHA256, ...]
    payload_manifest_sha256: SHA256
    started_at_utc: datetime
    completed_at_utc: datetime
    code_version_git_sha: GitSHA
    outcome: ResearchIngestionEligibilityOutcome
    payloads: tuple[ResearchIngestionEligibilityPayload, ...]
    checks: tuple[ResearchIngestionEligibilityCheck, ...]
    external_request_performed: Literal[False]
    provider_payload_persisted: Literal[False]
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
    strategy_execution_eligible: Literal[False]
    execution_authorized: Literal[False]
    order_submission_authorized: Literal[False]
    live_path_absent: Literal[True]
    no_personalized_investment_advice: Literal[True]
    no_real_performance_claimed: Literal[True]
    disclaimer: Literal[
        "Eligibility-assessment evidence only; no research dataset, research authorization, "
        "strategy result, promotion, execution authority, performance claim, or personalized "
        "investment advice."
    ]

    @field_validator("started_at_utc", "completed_at_utc")
    @classmethod
    def normalize_times(cls, value: datetime, info: object) -> datetime:
        return _utc(value, getattr(info, "field_name", "artifact time"))

    @model_validator(mode="after")
    def validate_artifact(self) -> Self:
        if self.started_at_utc > self.completed_at_utc:
            raise ValueError("eligibility assessment chronology is invalid")
        if self.assessment_id != identity(
            PHASE14_ASSESSMENT_NAMESPACE, self.request_fingerprint_sha256
        ):
            raise ValueError("assessment identity must derive from the semantic fingerprint")
        if self.policy_id != PHASE14_POLICY_ID or self.policy_sha256 != PHASE14_POLICY_SHA256:
            raise ValueError("eligibility assessment must bind the frozen policy")
        if self.qualification_id != identity(
            PHASE13_RUN_NAMESPACE, self.qualification_request_fingerprint_sha256
        ):
            raise ValueError("qualification identity must derive from its source fingerprint")
        if tuple(item.capability for item in self.payloads) != PHASE13_CAPABILITY_ORDER:
            raise ValueError("artifact must contain exactly six ordered capability payloads")
        if tuple(item.code for item in self.checks) != PHASE14_CHECK_ORDER:
            raise ValueError("artifact must contain exactly twelve ordered eligibility checks")
        if len(self.qualification_check_sha256s) != len(PHASE13_CHECK_ORDER):
            raise ValueError("artifact must bind all twelve Phase 13 checks")
        if tuple(item.source_capability_manifest_sha256 for item in self.payloads) != (
            self.qualification_capability_manifest_sha256s
        ):
            raise ValueError("artifact capability lineage must match projected payloads")
        if self.qualification_capability_manifest_sha256s != tuple(
            item.source_capability_manifest_sha256 for item in self.payloads
        ):
            raise ValueError("artifact must bind all six Phase 13 capability manifests")
        expected_payload_manifest = research_ingestion_eligibility_payload_manifest_sha256(
            self.payloads
        )
        if self.payload_manifest_sha256 != expected_payload_manifest:
            raise ValueError("payload manifest hash must bind all projected payloads")
        rights_present = self.qualification_rights_attestation_id is not None
        if rights_present is not (self.qualification_rights_attestation_sha256 is not None):
            raise ValueError("qualification rights identity and hash must be jointly present")
        if self.qualification_source_kind is QualificationSourceKind.DETERMINISTIC_MOCK:
            if rights_present:
                raise ValueError("mock qualification cannot claim external rights")
            if self.qualification_outcome not in {
                QualificationOutcome.MOCK_PROOF_COMPLETE,
                QualificationOutcome.BLOCKED,
            }:
                raise ValueError("mock qualification outcome conflicts with its source kind")
            mock_codes = {
                ResearchIngestionEligibilityCheckCode.EXTERNAL_REQUEST_EVIDENCE_COMPLETE_OR_MOCK,
                ResearchIngestionEligibilityCheckCode.INDEPENDENT_RIGHTS_REFERENCE_PRESENT_OR_MOCK,
                ResearchIngestionEligibilityCheckCode.USE_RIGHTS_CURRENT_OR_MOCK,
                ResearchIngestionEligibilityCheckCode.USE_RIGHTS_SCOPE_SUFFICIENT_OR_MOCK,
            }
            for check in self.checks:
                if check.code in mock_codes and (
                    check.status is not ResearchIngestionEligibilityCheckStatus.PASS
                    or check.reason_code
                    is not ResearchIngestionEligibilityReasonCode.MOCK_NOT_APPLICABLE
                ):
                    raise ValueError("mock external and rights checks must pass as not applicable")
        else:
            if not rights_present:
                raise ValueError("external qualification must bind its rights reference")
            if self.qualification_outcome not in {
                QualificationOutcome.EXTERNAL_SAMPLE_QUALIFIED,
                QualificationOutcome.BLOCKED,
            }:
                raise ValueError("external qualification outcome conflicts with its source kind")
            if self.outcome is not ResearchIngestionEligibilityOutcome.BLOCKED:
                raise ValueError("a non-mock qualification must remain blocked")

        checks_by_code = {item.code: item for item in self.checks}

        def canonical_evidence(*values: str) -> tuple[str, ...]:
            return tuple(sorted(set(values)))

        def require_check(
            code: ResearchIngestionEligibilityCheckCode,
            status: ResearchIngestionEligibilityCheckStatus,
            reason: ResearchIngestionEligibilityReasonCode,
            *,
            observed_value: str,
            threshold_value: str,
            evidence_sha256s: tuple[str, ...],
        ) -> None:
            check = checks_by_code[code]
            if check.status is not status or check.reason_code is not reason:
                raise ValueError(f"{code.value} does not follow the frozen policy")
            if (
                check.observed_value,
                check.threshold_value,
                check.evidence_sha256s,
            ) != (
                observed_value,
                threshold_value,
                canonical_evidence(*evidence_sha256s),
            ):
                raise ValueError(f"{code.value} does not bind exact source evidence")

        require_check(
            ResearchIngestionEligibilityCheckCode.QUALIFICATION_IDENTITY_INTEGRITY,
            ResearchIngestionEligibilityCheckStatus.PASS,
            ResearchIngestionEligibilityReasonCode.CHECK_PASSED,
            observed_value="valid",
            threshold_value="valid",
            evidence_sha256s=(
                self.qualification_request_fingerprint_sha256,
                self.qualification_artifact_sha256,
                self.qualification_capture_manifest_sha256,
            ),
        )
        is_mock = self.qualification_source_kind is QualificationSourceKind.DETERMINISTIC_MOCK
        require_check(
            ResearchIngestionEligibilityCheckCode.QUALIFICATION_SOURCE_KIND_ALLOWED,
            (
                ResearchIngestionEligibilityCheckStatus.PASS
                if is_mock
                else ResearchIngestionEligibilityCheckStatus.BLOCKED
            ),
            (
                ResearchIngestionEligibilityReasonCode.CHECK_PASSED
                if is_mock
                else ResearchIngestionEligibilityReasonCode.SOURCE_KIND_NOT_ALLOWED
            ),
            observed_value=self.qualification_source_kind.value,
            threshold_value=QualificationSourceKind.DETERMINISTIC_MOCK.value,
            evidence_sha256s=(
                self.qualification_artifact_sha256,
                self.qualification_request_fingerprint_sha256,
            ),
        )
        source_mock_complete = (
            is_mock and self.qualification_outcome is QualificationOutcome.MOCK_PROOF_COMPLETE
        )
        require_check(
            ResearchIngestionEligibilityCheckCode.QUALIFICATION_OUTCOME_ELIGIBLE_OR_MOCK,
            (
                ResearchIngestionEligibilityCheckStatus.PASS
                if source_mock_complete
                else ResearchIngestionEligibilityCheckStatus.BLOCKED
            ),
            (
                ResearchIngestionEligibilityReasonCode.CHECK_PASSED
                if source_mock_complete
                else ResearchIngestionEligibilityReasonCode.QUALIFICATION_OUTCOME_NOT_ELIGIBLE
            ),
            observed_value=self.qualification_outcome.value,
            threshold_value=QualificationOutcome.MOCK_PROOF_COMPLETE.value,
            evidence_sha256s=(self.qualification_artifact_sha256,),
        )
        capabilities_pass = all(
            item.source_status is QualificationCheckStatus.PASS for item in self.payloads
        )
        require_check(
            ResearchIngestionEligibilityCheckCode.CAPABILITY_MANIFEST_COMPLETE_PASSING,
            (
                ResearchIngestionEligibilityCheckStatus.PASS
                if capabilities_pass
                else ResearchIngestionEligibilityCheckStatus.BLOCKED
            ),
            (
                ResearchIngestionEligibilityReasonCode.CHECK_PASSED
                if capabilities_pass
                else ResearchIngestionEligibilityReasonCode.CAPABILITY_MANIFEST_NOT_PASSING
            ),
            observed_value=("6-of-6" if capabilities_pass else "fewer-than-6-passing"),
            threshold_value="6-of-6",
            evidence_sha256s=self.qualification_capability_manifest_sha256s,
        )
        qualification_checks = checks_by_code[
            ResearchIngestionEligibilityCheckCode.QUALIFICATION_CHECKS_COMPLETE_PASSING
        ]
        qualification_checks_pair = (
            qualification_checks.status,
            qualification_checks.reason_code,
        )
        passing_qualification_checks = (
            ResearchIngestionEligibilityCheckStatus.PASS,
            ResearchIngestionEligibilityReasonCode.CHECK_PASSED,
        )
        blocked_qualification_checks = (
            ResearchIngestionEligibilityCheckStatus.BLOCKED,
            ResearchIngestionEligibilityReasonCode.QUALIFICATION_CHECKS_NOT_PASSING,
        )
        if self.qualification_outcome is not QualificationOutcome.BLOCKED:
            if qualification_checks_pair != passing_qualification_checks:
                raise ValueError(
                    "QUALIFICATION_CHECKS_COMPLETE_PASSING does not follow the frozen policy"
                )
        elif qualification_checks_pair not in {
            passing_qualification_checks,
            blocked_qualification_checks,
        }:
            raise ValueError(
                "QUALIFICATION_CHECKS_COMPLETE_PASSING does not follow the frozen policy"
            )
        qualification_checks_pass = (
            qualification_checks.status is ResearchIngestionEligibilityCheckStatus.PASS
        )
        require_check(
            ResearchIngestionEligibilityCheckCode.QUALIFICATION_CHECKS_COMPLETE_PASSING,
            qualification_checks.status,
            qualification_checks.reason_code,
            observed_value=("12-of-12" if qualification_checks_pass else "fewer-than-12-passing"),
            threshold_value="12-of-12",
            evidence_sha256s=self.qualification_check_sha256s,
        )

        external_request_code = (
            ResearchIngestionEligibilityCheckCode.EXTERNAL_REQUEST_EVIDENCE_COMPLETE_OR_MOCK
        )
        rights_reference_code = (
            ResearchIngestionEligibilityCheckCode.INDEPENDENT_RIGHTS_REFERENCE_PRESENT_OR_MOCK
        )
        rights_current_code = ResearchIngestionEligibilityCheckCode.USE_RIGHTS_CURRENT_OR_MOCK
        rights_scope_code = (
            ResearchIngestionEligibilityCheckCode.USE_RIGHTS_SCOPE_SUFFICIENT_OR_MOCK
        )
        if is_mock:
            for code, evidence_sha256s in (
                (
                    external_request_code,
                    (
                        self.qualification_artifact_sha256,
                        self.qualification_capture_manifest_sha256,
                    ),
                ),
                (rights_reference_code, (self.qualification_artifact_sha256,)),
                (rights_current_code, (self.qualification_artifact_sha256,)),
                (rights_scope_code, (self.qualification_artifact_sha256,)),
            ):
                require_check(
                    code,
                    ResearchIngestionEligibilityCheckStatus.PASS,
                    ResearchIngestionEligibilityReasonCode.MOCK_NOT_APPLICABLE,
                    observed_value="mock-not-applicable",
                    threshold_value="mock-not-applicable",
                    evidence_sha256s=evidence_sha256s,
                )
        else:
            rights_sha256 = self.qualification_rights_attestation_sha256
            if rights_sha256 is None:
                raise ValueError("external qualification must bind its rights hash")
            request_evidence_sha256s = tuple(
                value for payload in self.payloads for value in payload.request_evidence_sha256s
            )
            external_request = checks_by_code[external_request_code]
            if (
                external_request.status,
                external_request.reason_code,
            ) not in {
                (
                    ResearchIngestionEligibilityCheckStatus.PASS,
                    ResearchIngestionEligibilityReasonCode.CHECK_PASSED,
                ),
                (
                    ResearchIngestionEligibilityCheckStatus.UNCOMPUTABLE,
                    ResearchIngestionEligibilityReasonCode.EXTERNAL_REQUEST_EVIDENCE_INCOMPLETE,
                ),
            }:
                raise ValueError("external request evidence does not follow the frozen policy")
            require_check(
                external_request_code,
                external_request.status,
                external_request.reason_code,
                observed_value=(
                    "complete-read-only-evidence"
                    if external_request.status is ResearchIngestionEligibilityCheckStatus.PASS
                    else "incomplete-or-unverified"
                ),
                threshold_value="5-of-5-observed",
                evidence_sha256s=(
                    request_evidence_sha256s
                    if request_evidence_sha256s
                    else (self.qualification_artifact_sha256,)
                ),
            )
            require_check(
                rights_reference_code,
                ResearchIngestionEligibilityCheckStatus.UNCOMPUTABLE,
                ResearchIngestionEligibilityReasonCode.INDEPENDENT_RIGHTS_REFERENCE_UNVERIFIED,
                observed_value="unverified",
                threshold_value="independently-authenticated",
                evidence_sha256s=(rights_sha256,),
            )
            rights_current = checks_by_code[rights_current_code]
            if (
                rights_current.status,
                rights_current.reason_code,
            ) not in {
                (
                    ResearchIngestionEligibilityCheckStatus.UNCOMPUTABLE,
                    ResearchIngestionEligibilityReasonCode.INDEPENDENT_RIGHTS_REFERENCE_UNVERIFIED,
                ),
                (
                    ResearchIngestionEligibilityCheckStatus.BLOCKED,
                    ResearchIngestionEligibilityReasonCode.RIGHTS_NOT_CURRENT,
                ),
            }:
                raise ValueError("external rights currentness does not follow the frozen policy")
            require_check(
                rights_current_code,
                rights_current.status,
                rights_current.reason_code,
                observed_value=(
                    "current-but-unverified"
                    if rights_current.status is ResearchIngestionEligibilityCheckStatus.UNCOMPUTABLE
                    else "missing-or-stale"
                ),
                threshold_value="independently-verified-current",
                evidence_sha256s=(rights_sha256,),
            )
            rights_scope = checks_by_code[rights_scope_code]
            if (
                rights_scope.status,
                rights_scope.reason_code,
            ) not in {
                (
                    ResearchIngestionEligibilityCheckStatus.UNCOMPUTABLE,
                    ResearchIngestionEligibilityReasonCode.INDEPENDENT_RIGHTS_REFERENCE_UNVERIFIED,
                ),
                (
                    ResearchIngestionEligibilityCheckStatus.BLOCKED,
                    ResearchIngestionEligibilityReasonCode.RIGHTS_SCOPE_INSUFFICIENT,
                ),
            }:
                raise ValueError("external rights scope does not follow the frozen policy")
            require_check(
                rights_scope_code,
                rights_scope.status,
                rights_scope.reason_code,
                observed_value=(
                    "sufficient-but-unverified"
                    if rights_scope.status is ResearchIngestionEligibilityCheckStatus.UNCOMPUTABLE
                    else "missing-or-insufficient"
                ),
                threshold_value="independently-verified-storage-nondisplay-derived",
                evidence_sha256s=(rights_sha256,),
            )

        require_check(
            ResearchIngestionEligibilityCheckCode.LICENSED_PAYLOAD_ABSENT,
            ResearchIngestionEligibilityCheckStatus.PASS,
            ResearchIngestionEligibilityReasonCode.CHECK_PASSED,
            observed_value="absent",
            threshold_value="absent",
            evidence_sha256s=(
                self.qualification_artifact_sha256,
                self.payload_manifest_sha256,
            ),
        )
        require_check(
            ResearchIngestionEligibilityCheckCode.RESEARCH_SNAPSHOT_ABSENT,
            ResearchIngestionEligibilityCheckStatus.PASS,
            ResearchIngestionEligibilityReasonCode.CHECK_PASSED,
            observed_value="absent",
            threshold_value="absent",
            evidence_sha256s=(self.qualification_artifact_sha256,),
        )
        require_check(
            ResearchIngestionEligibilityCheckCode.PROMOTION_EXECUTION_AUTHORITY_ABSENT,
            ResearchIngestionEligibilityCheckStatus.PASS,
            ResearchIngestionEligibilityReasonCode.CHECK_PASSED,
            observed_value="absent",
            threshold_value="absent",
            evidence_sha256s=self.qualification_check_sha256s,
        )
        all_checks_pass = all(
            item.status is ResearchIngestionEligibilityCheckStatus.PASS for item in self.checks
        )
        mock_complete = (
            self.qualification_source_kind is QualificationSourceKind.DETERMINISTIC_MOCK
            and self.qualification_outcome is QualificationOutcome.MOCK_PROOF_COMPLETE
            and all_checks_pass
        )
        expected_outcome = (
            ResearchIngestionEligibilityOutcome.MOCK_PROOF_COMPLETE
            if mock_complete
            else ResearchIngestionEligibilityOutcome.BLOCKED
        )
        if self.outcome is not expected_outcome:
            raise ValueError("eligibility outcome does not follow closed mock-only semantics")
        if self.outcome is ResearchIngestionEligibilityOutcome.BLOCKED and all_checks_pass:
            raise ValueError("blocked eligibility assessment requires a nonpassing check")
        payload = self.model_dump(mode="python", exclude={"artifact_sha256"})
        if self.artifact_sha256 != domain_sha256(PHASE14_ARTIFACT_HASH_DOMAIN, payload):
            raise ValueError("eligibility artifact hash must bind its complete preimage")
        return self


__all__ = [
    "PHASE14_ARTIFACT_SCHEMA_VERSION",
    "PHASE14_CHECK_ORDER",
    "PHASE14_CHECK_SCHEMA_VERSION",
    "PHASE14_DISCLAIMER",
    "PHASE14_PAYLOAD_SCHEMA_VERSION",
    "SHA256",
    "GitSHA",
    "ResearchIngestionEligibilityArtifact",
    "ResearchIngestionEligibilityCheck",
    "ResearchIngestionEligibilityCheckCode",
    "ResearchIngestionEligibilityCheckStatus",
    "ResearchIngestionEligibilityCreateRequest",
    "ResearchIngestionEligibilityOutcome",
    "ResearchIngestionEligibilityPayload",
    "ResearchIngestionEligibilityReasonCode",
    "StrictModel",
    "research_ingestion_eligibility_payload_manifest_sha256",
    "research_ingestion_eligibility_request_fingerprint",
    "validate_code_git_sha",
]
