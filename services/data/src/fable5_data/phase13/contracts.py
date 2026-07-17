"""Strict hash-bound contracts for Phase 13 point-in-time data qualification."""

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

from fable5_data.phase13.canonical import (
    PHASE13_ARTIFACT_HASH_DOMAIN,
    PHASE13_CAPABILITY_HASH_DOMAIN,
    PHASE13_CAPTURE_MANIFEST_HASH_DOMAIN,
    PHASE13_CHECK_HASH_DOMAIN,
    PHASE13_FIXED_ENDPOINTS,
    PHASE13_REQUEST_EVIDENCE_HASH_DOMAIN,
    PHASE13_REQUEST_HASH_DOMAIN,
    PHASE13_RUN_NAMESPACE,
    PHASE13_SAMPLE_PLAN_ID,
    PHASE13_SAMPLE_PLAN_SHA256,
    PHASE13_TRANSPORT_PROFILE_SHA256,
    TIINGO_QUALIFICATION_HOST,
    TIINGO_QUALIFICATION_PORT,
    domain_sha256,
    identity,
)

SHA256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
GitSHA = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]
Identifier = Annotated[
    str,
    StringConstraints(min_length=1, max_length=256, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:/-]*$"),
]
IdempotencyKey = Annotated[
    str,
    StringConstraints(min_length=8, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$"),
]
SanitizedValue = Annotated[str, StringConstraints(min_length=1, max_length=256)]

PHASE13_ARTIFACT_SCHEMA_VERSION: Literal["phase13-pit-qualification-v1"] = (
    "phase13-pit-qualification-v1"
)
PHASE13_CAPABILITY_SCHEMA_VERSION: Literal["phase13-pit-capability-manifest-v1"] = (
    "phase13-pit-capability-manifest-v1"
)
PHASE13_CHECK_SCHEMA_VERSION: Literal["phase13-pit-qualification-check-v1"] = (
    "phase13-pit-qualification-check-v1"
)
PHASE13_REQUEST_EVIDENCE_SCHEMA_VERSION: Literal["phase13-pit-request-evidence-v1"] = (
    "phase13-pit-request-evidence-v1"
)
PHASE13_PROVIDER_PROFILE_SCHEMA_VERSION: Literal["phase13-pit-provider-profile-v1"] = (
    "phase13-pit-provider-profile-v1"
)
PHASE13_RIGHTS_SCHEMA_VERSION: Literal["phase13-pit-rights-attestation-v1"] = (
    "phase13-pit-rights-attestation-v1"
)
PHASE13_DISCLAIMER: Literal[
    "Qualification-only sample evidence; not a research dataset, strategy result, execution "
    "authority, performance claim, or personalized investment advice."
] = (
    "Qualification-only sample evidence; not a research dataset, strategy result, execution "
    "authority, performance claim, or personalized investment advice."
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
        or "authorization" in lowered
        or "token" in lowered
        or "secret" in lowered
        or "api_key" in lowered
        or "apikey" in lowered
        or "?token=" in lowered
    ):
        raise ValueError(f"{field_name} must be sanitized")
    return value


def validate_code_git_sha(value: str | None) -> str:
    if value is None or re.fullmatch(r"[0-9a-f]{40}", value) is None:
        raise ValueError("phase13 code identity is unavailable")
    return value


class QualificationSourceKind(StrEnum):
    DETERMINISTIC_MOCK = "DETERMINISTIC_MOCK"
    TIINGO_CANDIDATE_READ_ONLY = "TIINGO_CANDIDATE_READ_ONLY"


class QualificationOutcome(StrEnum):
    MOCK_PROOF_COMPLETE = "MOCK_PROOF_COMPLETE"
    EXTERNAL_SAMPLE_QUALIFIED = "EXTERNAL_SAMPLE_QUALIFIED"
    BLOCKED = "BLOCKED"


class QualificationCheckStatus(StrEnum):
    PASS = "PASS"
    BLOCKED = "BLOCKED"
    UNCOMPUTABLE = "UNCOMPUTABLE"


class QualificationCapability(StrEnum):
    SECURITY_MASTER_STABLE_IDENTITY = "SECURITY_MASTER_STABLE_IDENTITY"
    POINT_IN_TIME_UNIVERSE_MEMBERSHIP = "POINT_IN_TIME_UNIVERSE_MEMBERSHIP"
    RAW_OHLCV_AVAILABILITY = "RAW_OHLCV_AVAILABILITY"
    CORPORATE_ACTION_ANNOUNCEMENT_REVISION = "CORPORATE_ACTION_ANNOUNCEMENT_REVISION"
    DELISTING_RETURN_SEMANTICS = "DELISTING_RETURN_SEMANTICS"
    AS_REPORTED_FUNDAMENTAL_REVISION = "AS_REPORTED_FUNDAMENTAL_REVISION"


PHASE13_CAPABILITY_ORDER: tuple[QualificationCapability, ...] = tuple(QualificationCapability)


class QualificationCheckCode(StrEnum):
    SOURCE_KIND_EXACT = "SOURCE_KIND_EXACT"
    READ_ONLY_TRANSPORT_EXACT = "READ_ONLY_TRANSPORT_EXACT"
    USE_RIGHTS_CURRENT_SUFFICIENT = "USE_RIGHTS_CURRENT_SUFFICIENT"
    SECURITY_MASTER_STABLE_IDENTITY = "SECURITY_MASTER_STABLE_IDENTITY"
    POINT_IN_TIME_UNIVERSE_MEMBERSHIP = "POINT_IN_TIME_UNIVERSE_MEMBERSHIP"
    RAW_OHLCV_AVAILABILITY = "RAW_OHLCV_AVAILABILITY"
    CORPORATE_ACTION_ANNOUNCEMENT_REVISION = "CORPORATE_ACTION_ANNOUNCEMENT_REVISION"
    DELISTING_RETURN_SEMANTICS = "DELISTING_RETURN_SEMANTICS"
    AS_REPORTED_FUNDAMENTAL_REVISION = "AS_REPORTED_FUNDAMENTAL_REVISION"
    RAW_NORMALIZED_RECONCILIATION = "RAW_NORMALIZED_RECONCILIATION"
    NULL_SENTINEL_SCHEMA_DRIFT = "NULL_SENTINEL_SCHEMA_DRIFT"
    DETERMINISTIC_CAPTURE_MANIFEST = "DETERMINISTIC_CAPTURE_MANIFEST"


PHASE13_CHECK_ORDER: tuple[QualificationCheckCode, ...] = tuple(QualificationCheckCode)


class QualificationReasonCode(StrEnum):
    CHECK_PASSED = "check_passed"
    MOCK_RIGHTS_NOT_APPLICABLE = "mock_rights_not_applicable"
    CREDENTIALS_UNAVAILABLE = "credentials_unavailable"
    RIGHTS_UNAVAILABLE = "rights_unavailable"
    RIGHTS_NOT_CURRENT = "rights_not_current"
    RIGHTS_INSUFFICIENT = "rights_insufficient"
    CAPABILITY_UNDOCUMENTED = "capability_undocumented"
    CURRENT_UNIVERSE_ONLY = "current_universe_only"
    DELISTING_RETURN_UNAVAILABLE = "delisting_return_unavailable"
    HTTP_FAILURE = "http_failure"
    TRANSPORT_FAILURE = "transport_failure"
    REDIRECT_REJECTED = "redirect_rejected"
    RESPONSE_TOO_LARGE = "response_too_large"
    MALFORMED_UTF8 = "malformed_utf8"
    MALFORMED_JSON = "malformed_json"
    DUPLICATE_JSON_KEY = "duplicate_json_key"
    NON_FINITE_NUMBER = "non_finite_number"
    SCHEMA_DRIFT = "schema_drift"
    TEMPORAL_INVALID = "temporal_invalid"
    IDENTITY_INVALID = "identity_invalid"
    ACTION_REVISION_INVALID = "action_revision_invalid"
    FUNDAMENTAL_REVISION_INVALID = "fundamental_revision_invalid"
    RAW_NORMALIZED_MISMATCH = "raw_normalized_mismatch"
    NULL_SENTINEL_DRIFT = "null_sentinel_drift"
    NONDETERMINISTIC_CAPTURE = "nondeterministic_capture"
    PRIOR_CAPABILITY_BLOCKED = "prior_capability_blocked"


class QualificationRequestCode(StrEnum):
    FUNDAMENTALS_META = "FUNDAMENTALS_META"
    EOD_PRICES = "EOD_PRICES"
    DISTRIBUTIONS = "DISTRIBUTIONS"
    SPLITS = "SPLITS"
    FUNDAMENTAL_STATEMENTS = "FUNDAMENTAL_STATEMENTS"


class QualificationRequestStatus(StrEnum):
    OBSERVED = "OBSERVED"
    BLOCKED = "BLOCKED"
    NOT_ATTEMPTED = "NOT_ATTEMPTED"


FixedTiingoTarget = Literal[
    "/tiingo/fundamentals/meta?columns=permaTicker,ticker,isActive,statementLastUpdated,dailyLastUpdated",
    "/tiingo/daily/AAPL/prices?startDate=2020-08-28&endDate=2020-09-01",
    "/tiingo/corporate-actions/AAPL/distributions?startExDate=2020-01-01&endExDate=2020-12-31",
    "/tiingo/corporate-actions/AAPL/splits?startExDate=2020-08-28&endExDate=2020-09-01",
    "/tiingo/fundamentals/AAPL/statements?startDate=2019-01-01",
]


class PointInTimeQualificationCreateRequest(StrictModel):
    qualification_idempotency_key: IdempotencyKey


class QualificationUseRightsAttestation(StrictModel):
    schema_version: Literal["phase13-pit-rights-attestation-v1"] = PHASE13_RIGHTS_SCHEMA_VERSION
    attestation_id: Identifier
    attestation_sha256: SHA256
    valid_from_utc: datetime
    expires_at_utc: datetime
    storage_allowed: bool
    non_display_allowed: bool
    derived_data_allowed: bool
    qualification_use_only: Literal[True] = True

    @field_validator("valid_from_utc", "expires_at_utc")
    @classmethod
    def normalize_times(cls, value: datetime, info: object) -> datetime:
        return _utc(value, getattr(info, "field_name", "rights time"))

    @model_validator(mode="after")
    def validate_interval(self) -> Self:
        if self.valid_from_utc >= self.expires_at_utc:
            raise ValueError("rights attestation interval must be positive")
        return self

    def is_current_and_sufficient(self, at_utc: datetime) -> bool:
        at_utc = _utc(at_utc, "rights evaluation time")
        return (
            self.valid_from_utc <= at_utc < self.expires_at_utc
            and self.storage_allowed
            and self.non_display_allowed
            and self.derived_data_allowed
        )


class QualificationProviderProfile(StrictModel):
    schema_version: Literal["phase13-pit-provider-profile-v1"] = (
        PHASE13_PROVIDER_PROFILE_SCHEMA_VERSION
    )
    source_kind: QualificationSourceKind
    provider_id: Identifier
    adapter_id: Identifier
    adapter_version: Identifier
    dataset_id: Identifier
    product_id: Identifier
    synthetic: bool
    transport_profile_sha256: SHA256 = PHASE13_TRANSPORT_PROFILE_SHA256

    @model_validator(mode="after")
    def bind_source_kind(self) -> Self:
        if self.transport_profile_sha256 != PHASE13_TRANSPORT_PROFILE_SHA256:
            raise ValueError("provider profile must bind the frozen transport profile")
        if self.source_kind is QualificationSourceKind.DETERMINISTIC_MOCK:
            if not self.synthetic:
                raise ValueError("deterministic mock profile must be synthetic")
        elif self.synthetic:
            raise ValueError("external candidate profile cannot be synthetic")
        return self


class QualificationRequestEvidence(StrictModel):
    schema_version: Literal["phase13-pit-request-evidence-v1"] = (
        PHASE13_REQUEST_EVIDENCE_SCHEMA_VERSION
    )
    ordinal: int = Field(ge=1, le=5)
    code: QualificationRequestCode
    status: QualificationRequestStatus
    method: Literal["GET"] = "GET"
    host: Literal["api.tiingo.com"] = TIINGO_QUALIFICATION_HOST
    port: Literal[443] = TIINGO_QUALIFICATION_PORT
    target: FixedTiingoTarget
    external_request_performed: bool
    request_started_at_utc: datetime | None = None
    request_completed_at_utc: datetime | None = None
    http_status: int | None = Field(default=None, ge=100, le=599)
    raw_body_sha256: SHA256 | None = None
    body_size_bytes: int | None = Field(default=None, ge=1, le=2_000_000)
    record_count: int | None = Field(default=None, ge=0, le=100_000)
    reason_code: QualificationReasonCode
    request_evidence_sha256: SHA256

    @field_validator("request_started_at_utc", "request_completed_at_utc")
    @classmethod
    def normalize_times(cls, value: datetime | None, info: object) -> datetime | None:
        return None if value is None else _utc(value, getattr(info, "field_name", "request time"))

    @model_validator(mode="after")
    def validate_evidence(self) -> Self:
        endpoint = PHASE13_FIXED_ENDPOINTS[self.ordinal - 1]
        if self.code.value != endpoint["code"] or self.target != endpoint["target"]:
            raise ValueError("request evidence must match its frozen endpoint ordinal")
        times_present = self.request_started_at_utc is not None and (
            self.request_completed_at_utc is not None
        )
        if (self.request_started_at_utc is None) is not (self.request_completed_at_utc is None):
            raise ValueError("request evidence times must be jointly present")
        if times_present and self.request_started_at_utc > self.request_completed_at_utc:  # type: ignore[operator]
            raise ValueError("request evidence chronology is invalid")
        if self.status is QualificationRequestStatus.OBSERVED:
            if not times_present or self.raw_body_sha256 is None:
                raise ValueError("observed request requires bounded time and a transient-body hash")
            if self.body_size_bytes is None or self.record_count is None:
                raise ValueError("observed request requires bounded size and count evidence")
            if self.reason_code is not QualificationReasonCode.CHECK_PASSED:
                raise ValueError("observed request must use the passing reason")
            if self.external_request_performed and self.http_status != 200:
                raise ValueError("observed external request requires HTTP 200")
            if not self.external_request_performed and self.http_status is not None:
                raise ValueError("mock request evidence cannot claim an HTTP status")
        elif self.status is QualificationRequestStatus.NOT_ATTEMPTED:
            if times_present or self.external_request_performed:
                raise ValueError("not-attempted request cannot claim transport activity")
            if any(
                value is not None
                for value in (
                    self.http_status,
                    self.raw_body_sha256,
                    self.body_size_bytes,
                    self.record_count,
                )
            ):
                raise ValueError("not-attempted request cannot claim response evidence")
            if self.reason_code is QualificationReasonCode.CHECK_PASSED:
                raise ValueError("not-attempted request cannot pass")
        else:
            if not times_present:
                raise ValueError("blocked attempted request requires bounded times")
            if self.reason_code is QualificationReasonCode.CHECK_PASSED:
                raise ValueError("blocked request cannot use the passing reason")
            if not self.external_request_performed and self.http_status is not None:
                raise ValueError("non-external blocked request cannot claim HTTP evidence")
        payload = self.model_dump(mode="python", exclude={"request_evidence_sha256"})
        if self.request_evidence_sha256 != domain_sha256(
            PHASE13_REQUEST_EVIDENCE_HASH_DOMAIN, payload
        ):
            raise ValueError("request evidence hash must bind its complete preimage")
        return self


class QualificationCapabilityManifest(StrictModel):
    schema_version: Literal["phase13-pit-capability-manifest-v1"] = (
        PHASE13_CAPABILITY_SCHEMA_VERSION
    )
    ordinal: int = Field(ge=1, le=6)
    capability: QualificationCapability
    status: QualificationCheckStatus
    reason_code: QualificationReasonCode
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
    request_evidence: tuple[QualificationRequestEvidence, ...] = ()
    capability_manifest_sha256: SHA256

    @field_validator(
        "decision_time_utc",
        "event_time_min_utc",
        "event_time_max_utc",
        "available_at_min_utc",
        "available_at_max_utc",
    )
    @classmethod
    def normalize_times(cls, value: datetime | None, info: object) -> datetime | None:
        return None if value is None else _utc(value, getattr(info, "field_name", "manifest time"))

    @model_validator(mode="after")
    def validate_manifest(self) -> Self:
        expected_ordinal = PHASE13_CAPABILITY_ORDER.index(self.capability) + 1
        if self.ordinal != expected_ordinal:
            raise ValueError("capability manifest ordinal must match the frozen registry")
        for minimum, maximum, label in (
            (self.event_time_min_utc, self.event_time_max_utc, "event"),
            (self.available_at_min_utc, self.available_at_max_utc, "availability"),
        ):
            if (minimum is None) is not (maximum is None):
                raise ValueError(f"{label} range must be jointly present")
            if minimum is not None and maximum is not None and minimum > maximum:
                raise ValueError(f"{label} range is invalid")
        if (
            self.available_at_max_utc is not None
            and self.available_at_max_utc > self.decision_time_utc
        ):
            raise ValueError("qualification evidence cannot be available after its decision time")
        request_ordinals = [item.ordinal for item in self.request_evidence]
        if request_ordinals != sorted(set(request_ordinals)):
            raise ValueError("request evidence must have unique canonical ordinals")
        if any(
            PHASE13_FIXED_ENDPOINTS[item.ordinal - 1]["capability"] != self.capability.value
            for item in self.request_evidence
        ):
            raise ValueError("request evidence must belong to its frozen capability")
        if self.status is QualificationCheckStatus.PASS:
            if self.reason_code is not QualificationReasonCode.CHECK_PASSED:
                raise ValueError("passing capability must use the passing reason")
            if self.record_count < 1:
                raise ValueError("passing capability requires at least one bounded record")
            if any(
                value is None
                for value in (
                    self.raw_evidence_sha256,
                    self.normalized_evidence_sha256,
                    self.schema_identity_sha256,
                )
            ):
                raise ValueError("passing capability requires complete hash evidence")
        elif self.reason_code is QualificationReasonCode.CHECK_PASSED:
            raise ValueError("nonpassing capability cannot use the passing reason")
        payload = self.model_dump(mode="python", exclude={"capability_manifest_sha256"})
        if self.capability_manifest_sha256 != domain_sha256(
            PHASE13_CAPABILITY_HASH_DOMAIN, payload
        ):
            raise ValueError("capability manifest hash must bind its complete preimage")
        return self


class QualificationCheck(StrictModel):
    schema_version: Literal["phase13-pit-qualification-check-v1"] = PHASE13_CHECK_SCHEMA_VERSION
    ordinal: int = Field(ge=1, le=12)
    code: QualificationCheckCode
    status: QualificationCheckStatus
    reason_code: QualificationReasonCode
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
        expected_ordinal = PHASE13_CHECK_ORDER.index(self.code) + 1
        if self.ordinal != expected_ordinal:
            raise ValueError("qualification check ordinal must match the frozen registry")
        if tuple(sorted(set(self.evidence_sha256s))) != self.evidence_sha256s:
            raise ValueError("qualification check evidence hashes must be unique and sorted")
        if not self.evidence_sha256s:
            raise ValueError("qualification check requires hash-bound evidence")
        if self.status is QualificationCheckStatus.PASS:
            if self.reason_code not in {
                QualificationReasonCode.CHECK_PASSED,
                QualificationReasonCode.MOCK_RIGHTS_NOT_APPLICABLE,
            }:
                raise ValueError("passing check has an invalid reason")
        elif self.reason_code in {
            QualificationReasonCode.CHECK_PASSED,
            QualificationReasonCode.MOCK_RIGHTS_NOT_APPLICABLE,
        }:
            raise ValueError("nonpassing check cannot use a passing reason")
        payload = self.model_dump(mode="python", exclude={"check_sha256"})
        if self.check_sha256 != domain_sha256(PHASE13_CHECK_HASH_DOMAIN, payload):
            raise ValueError("qualification check hash must bind its complete preimage")
        return self


def qualification_request_fingerprint(
    *,
    request: PointInTimeQualificationCreateRequest,
    provider_profile: QualificationProviderProfile,
    code_version_git_sha: str,
) -> str:
    """Bind the complete server-owned request/profile/plan/code preimage."""

    return domain_sha256(
        PHASE13_REQUEST_HASH_DOMAIN,
        {
            "schema_version": PHASE13_ARTIFACT_SCHEMA_VERSION,
            "qualification_idempotency_key": request.qualification_idempotency_key,
            "source_kind": provider_profile.source_kind,
            "provider_profile": provider_profile,
            "sample_plan_id": PHASE13_SAMPLE_PLAN_ID,
            "sample_plan_sha256": PHASE13_SAMPLE_PLAN_SHA256,
            "transport_profile_sha256": PHASE13_TRANSPORT_PROFILE_SHA256,
            "code_version_git_sha": validate_code_git_sha(code_version_git_sha),
        },
    )


def qualification_capture_manifest_sha256(
    *,
    provider_profile: QualificationProviderProfile,
    rights_attestation: QualificationUseRightsAttestation | None,
    capability_manifests: tuple[QualificationCapabilityManifest, ...],
) -> str:
    return domain_sha256(
        PHASE13_CAPTURE_MANIFEST_HASH_DOMAIN,
        {
            "provider_profile": provider_profile,
            "rights_attestation": rights_attestation,
            "sample_plan_id": PHASE13_SAMPLE_PLAN_ID,
            "sample_plan_sha256": PHASE13_SAMPLE_PLAN_SHA256,
            "capability_manifest_sha256s": tuple(
                item.capability_manifest_sha256 for item in capability_manifests
            ),
        },
    )


class PointInTimeQualificationArtifact(StrictModel):
    schema_version: Literal["phase13-pit-qualification-v1"]
    qualification_id: UUID
    qualification_idempotency_key: IdempotencyKey
    request_fingerprint_sha256: SHA256
    artifact_sha256: SHA256
    source_kind: QualificationSourceKind
    outcome: QualificationOutcome
    provider_profile: QualificationProviderProfile
    rights_attestation: QualificationUseRightsAttestation | None = None
    sample_plan_id: Literal["phase13-family-a-qualification-sample-v1"]
    sample_plan_sha256: SHA256
    transport_profile_sha256: SHA256
    capture_manifest_sha256: SHA256
    started_at_utc: datetime
    completed_at_utc: datetime
    code_version_git_sha: GitSHA
    capability_manifests: tuple[QualificationCapabilityManifest, ...]
    checks: tuple[QualificationCheck, ...]
    research_data_eligible: Literal[False]
    strategy_promotion_authorized: Literal[False]
    strategy_execution_eligible: Literal[False]
    execution_authorized: Literal[False]
    order_submission_authorized: Literal[False]
    live_path_absent: Literal[True]
    no_personalized_investment_advice: Literal[True]
    no_real_performance_claimed: Literal[True]
    disclaimer: Literal[
        "Qualification-only sample evidence; not a research dataset, strategy result, execution "
        "authority, performance claim, or personalized investment advice."
    ]

    @field_validator("started_at_utc", "completed_at_utc")
    @classmethod
    def normalize_times(cls, value: datetime, info: object) -> datetime:
        return _utc(value, getattr(info, "field_name", "artifact time"))

    @model_validator(mode="after")
    def validate_artifact(self) -> Self:
        if self.started_at_utc > self.completed_at_utc:
            raise ValueError("qualification chronology is invalid")
        if self.qualification_id != identity(
            PHASE13_RUN_NAMESPACE, self.request_fingerprint_sha256
        ):
            raise ValueError("qualification identity must derive from the request fingerprint")
        if self.source_kind is not self.provider_profile.source_kind:
            raise ValueError("artifact source kind must match its provider profile")
        if self.sample_plan_sha256 != PHASE13_SAMPLE_PLAN_SHA256:
            raise ValueError("artifact must bind the frozen sample plan")
        if self.transport_profile_sha256 != PHASE13_TRANSPORT_PROFILE_SHA256:
            raise ValueError("artifact must bind the frozen transport profile")
        if tuple(item.capability for item in self.capability_manifests) != (
            PHASE13_CAPABILITY_ORDER
        ):
            raise ValueError("artifact must contain the exact ordered capability registry")
        if tuple(item.code for item in self.checks) != PHASE13_CHECK_ORDER:
            raise ValueError("artifact must contain the exact ordered check registry")
        expected_capture = qualification_capture_manifest_sha256(
            provider_profile=self.provider_profile,
            rights_attestation=self.rights_attestation,
            capability_manifests=self.capability_manifests,
        )
        if self.capture_manifest_sha256 != expected_capture:
            raise ValueError("capture manifest hash must bind all capability evidence")
        all_checks_pass = all(item.status is QualificationCheckStatus.PASS for item in self.checks)
        all_capabilities_pass = all(
            item.status is QualificationCheckStatus.PASS for item in self.capability_manifests
        )
        all_pass = all_checks_pass and all_capabilities_pass
        if self.source_kind is QualificationSourceKind.DETERMINISTIC_MOCK:
            if self.rights_attestation is not None:
                raise ValueError("mock qualification cannot claim external rights")
            if any(
                evidence.external_request_performed
                for manifest in self.capability_manifests
                for evidence in manifest.request_evidence
            ):
                raise ValueError("mock qualification cannot claim external requests")
            expected_outcome = (
                QualificationOutcome.MOCK_PROOF_COMPLETE
                if all_pass
                else QualificationOutcome.BLOCKED
            )
        else:
            if self.rights_attestation is None:
                raise ValueError("external qualification requires rights evidence")
            expected_outcome = (
                QualificationOutcome.EXTERNAL_SAMPLE_QUALIFIED
                if all_pass
                else QualificationOutcome.BLOCKED
            )
            if self.outcome is QualificationOutcome.EXTERNAL_SAMPLE_QUALIFIED:
                if not self.rights_attestation.is_current_and_sufficient(self.completed_at_utc):
                    raise ValueError("external qualification requires current sufficient rights")
                performed = {
                    evidence.code
                    for manifest in self.capability_manifests
                    for evidence in manifest.request_evidence
                    if evidence.external_request_performed
                    and evidence.status is QualificationRequestStatus.OBSERVED
                }
                if performed != set(QualificationRequestCode):
                    raise ValueError("external qualification requires all fixed GET observations")
        if self.outcome is not expected_outcome:
            raise ValueError("qualification outcome does not follow closed source/check semantics")
        payload = self.model_dump(mode="python", exclude={"artifact_sha256"})
        if self.artifact_sha256 != domain_sha256(PHASE13_ARTIFACT_HASH_DOMAIN, payload):
            raise ValueError("qualification artifact hash must bind its complete preimage")
        return self


__all__ = [
    "PHASE13_ARTIFACT_SCHEMA_VERSION",
    "PHASE13_CAPABILITY_ORDER",
    "PHASE13_CAPABILITY_SCHEMA_VERSION",
    "PHASE13_CHECK_ORDER",
    "PHASE13_CHECK_SCHEMA_VERSION",
    "PHASE13_DISCLAIMER",
    "PHASE13_PROVIDER_PROFILE_SCHEMA_VERSION",
    "PHASE13_REQUEST_EVIDENCE_SCHEMA_VERSION",
    "PHASE13_RIGHTS_SCHEMA_VERSION",
    "SHA256",
    "GitSHA",
    "IdempotencyKey",
    "PointInTimeQualificationArtifact",
    "PointInTimeQualificationCreateRequest",
    "QualificationCapability",
    "QualificationCapabilityManifest",
    "QualificationCheck",
    "QualificationCheckCode",
    "QualificationCheckStatus",
    "QualificationOutcome",
    "QualificationProviderProfile",
    "QualificationReasonCode",
    "QualificationRequestCode",
    "QualificationRequestEvidence",
    "QualificationRequestStatus",
    "QualificationSourceKind",
    "QualificationUseRightsAttestation",
    "StrictModel",
    "qualification_capture_manifest_sha256",
    "qualification_request_fingerprint",
    "validate_code_git_sha",
]
