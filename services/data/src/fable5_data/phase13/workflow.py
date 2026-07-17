"""Single-flight synchronous orchestration for Phase 13 qualification evidence."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import UUID

from fable5_data.phase13.adapters import PointInTimeQualificationAdapter
from fable5_data.phase13.canonical import (
    PHASE13_ARTIFACT_HASH_DOMAIN,
    PHASE13_CHECK_HASH_DOMAIN,
    PHASE13_RUN_NAMESPACE,
    PHASE13_SAMPLE_PLAN_ID,
    PHASE13_SAMPLE_PLAN_SHA256,
    PHASE13_TRANSPORT_PROFILE_SHA256,
    domain_sha256,
    identity,
)
from fable5_data.phase13.contracts import (
    PHASE13_ARTIFACT_SCHEMA_VERSION,
    PHASE13_CAPABILITY_ORDER,
    PHASE13_CHECK_ORDER,
    PHASE13_DISCLAIMER,
    PointInTimeQualificationArtifact,
    PointInTimeQualificationCreateRequest,
    QualificationCapability,
    QualificationCapabilityManifest,
    QualificationCheck,
    QualificationCheckCode,
    QualificationCheckStatus,
    QualificationOutcome,
    QualificationReasonCode,
    QualificationSourceKind,
    qualification_capture_manifest_sha256,
    qualification_request_fingerprint,
    validate_code_git_sha,
)


class PointInTimeQualificationNotFound(LookupError):
    pass


class PointInTimeQualificationWorkflowConflict(RuntimeError):
    pass


class PointInTimeQualificationCreation(Protocol):
    def find_by_idempotency_key(self, key: str) -> PointInTimeQualificationArtifact | None: ...

    def create_qualification(
        self, artifact: PointInTimeQualificationArtifact
    ) -> PointInTimeQualificationArtifact: ...


class PointInTimeQualificationStore(PointInTimeQualificationCreation, Protocol):
    def serialized_creation(
        self, key: str
    ) -> AbstractContextManager[PointInTimeQualificationCreation]: ...

    def get_qualification(self, qualification_id: UUID) -> PointInTimeQualificationArtifact: ...


def _system_utc_now() -> datetime:
    return datetime.now(UTC)


def _check(
    *,
    code: QualificationCheckCode,
    status: QualificationCheckStatus,
    reason_code: QualificationReasonCode,
    evidence_sha256s: tuple[str, ...],
    observed_value: str | None,
    threshold_value: str | None,
) -> QualificationCheck:
    payload = {
        "schema_version": "phase13-pit-qualification-check-v1",
        "ordinal": PHASE13_CHECK_ORDER.index(code) + 1,
        "code": code,
        "status": status,
        "reason_code": reason_code,
        "observed_value": observed_value,
        "threshold_value": threshold_value,
        "evidence_sha256s": tuple(sorted(set(evidence_sha256s))),
    }
    return QualificationCheck.model_validate(
        {**payload, "check_sha256": domain_sha256(PHASE13_CHECK_HASH_DOMAIN, payload)}
    )


_CAPABILITY_CHECKS = {
    QualificationCapability.SECURITY_MASTER_STABLE_IDENTITY: (
        QualificationCheckCode.SECURITY_MASTER_STABLE_IDENTITY
    ),
    QualificationCapability.POINT_IN_TIME_UNIVERSE_MEMBERSHIP: (
        QualificationCheckCode.POINT_IN_TIME_UNIVERSE_MEMBERSHIP
    ),
    QualificationCapability.RAW_OHLCV_AVAILABILITY: (QualificationCheckCode.RAW_OHLCV_AVAILABILITY),
    QualificationCapability.CORPORATE_ACTION_ANNOUNCEMENT_REVISION: (
        QualificationCheckCode.CORPORATE_ACTION_ANNOUNCEMENT_REVISION
    ),
    QualificationCapability.DELISTING_RETURN_SEMANTICS: (
        QualificationCheckCode.DELISTING_RETURN_SEMANTICS
    ),
    QualificationCapability.AS_REPORTED_FUNDAMENTAL_REVISION: (
        QualificationCheckCode.AS_REPORTED_FUNDAMENTAL_REVISION
    ),
}


def _derived_status(
    manifests: tuple[QualificationCapabilityManifest, ...],
    blocking_reasons: set[QualificationReasonCode],
) -> tuple[QualificationCheckStatus, QualificationReasonCode]:
    matching = next(
        (item.reason_code for item in manifests if item.reason_code in blocking_reasons),
        None,
    )
    if matching is not None:
        return QualificationCheckStatus.BLOCKED, matching
    if all(item.status is QualificationCheckStatus.PASS for item in manifests):
        return QualificationCheckStatus.PASS, QualificationReasonCode.CHECK_PASSED
    return QualificationCheckStatus.UNCOMPUTABLE, QualificationReasonCode.PRIOR_CAPABILITY_BLOCKED


def _build_checks(
    *,
    adapter: PointInTimeQualificationAdapter,
    manifests: tuple[QualificationCapabilityManifest, ...],
    completed_at_utc: datetime,
    request_fingerprint_sha256: str,
    capture_manifest_sha256: str,
) -> tuple[QualificationCheck, ...]:
    checks: list[QualificationCheck] = [
        _check(
            code=QualificationCheckCode.SOURCE_KIND_EXACT,
            status=QualificationCheckStatus.PASS,
            reason_code=QualificationReasonCode.CHECK_PASSED,
            evidence_sha256s=(request_fingerprint_sha256,),
            observed_value=adapter.source_kind.value,
            threshold_value="DETERMINISTIC_MOCK|TIINGO_CANDIDATE_READ_ONLY",
        ),
        _check(
            code=QualificationCheckCode.READ_ONLY_TRANSPORT_EXACT,
            status=QualificationCheckStatus.PASS,
            reason_code=QualificationReasonCode.CHECK_PASSED,
            evidence_sha256s=(PHASE13_TRANSPORT_PROFILE_SHA256,),
            observed_value=PHASE13_TRANSPORT_PROFILE_SHA256,
            threshold_value=PHASE13_TRANSPORT_PROFILE_SHA256,
        ),
    ]
    rights = adapter.rights_attestation
    if adapter.source_kind is QualificationSourceKind.DETERMINISTIC_MOCK:
        rights_status = QualificationCheckStatus.PASS
        rights_reason = QualificationReasonCode.MOCK_RIGHTS_NOT_APPLICABLE
        rights_evidence = (request_fingerprint_sha256,)
        rights_observed = "mock-not-applicable"
    elif rights is not None and rights.is_current_and_sufficient(completed_at_utc):
        rights_status = QualificationCheckStatus.PASS
        rights_reason = QualificationReasonCode.CHECK_PASSED
        rights_evidence = (rights.attestation_sha256,)
        rights_observed = "current-and-sufficient"
    else:
        rights_status = QualificationCheckStatus.BLOCKED
        rights_reason = QualificationReasonCode.RIGHTS_NOT_CURRENT
        rights_evidence = (request_fingerprint_sha256,)
        rights_observed = "unavailable-or-insufficient"
    checks.append(
        _check(
            code=QualificationCheckCode.USE_RIGHTS_CURRENT_SUFFICIENT,
            status=rights_status,
            reason_code=rights_reason,
            evidence_sha256s=rights_evidence,
            observed_value=rights_observed,
            threshold_value="current-storage-nondisplay-derived",
        )
    )
    for manifest in manifests:
        checks.append(
            _check(
                code=_CAPABILITY_CHECKS[manifest.capability],
                status=manifest.status,
                reason_code=manifest.reason_code,
                evidence_sha256s=(manifest.capability_manifest_sha256,),
                observed_value=manifest.status.value,
                threshold_value="PASS",
            )
        )
    reconciliation_status, reconciliation_reason = _derived_status(
        manifests,
        {QualificationReasonCode.RAW_NORMALIZED_MISMATCH},
    )
    checks.append(
        _check(
            code=QualificationCheckCode.RAW_NORMALIZED_RECONCILIATION,
            status=reconciliation_status,
            reason_code=reconciliation_reason,
            evidence_sha256s=tuple(item.capability_manifest_sha256 for item in manifests),
            observed_value=reconciliation_status.value,
            threshold_value="PASS",
        )
    )
    schema_status, schema_reason = _derived_status(
        manifests,
        {
            QualificationReasonCode.NULL_SENTINEL_DRIFT,
            QualificationReasonCode.SCHEMA_DRIFT,
        },
    )
    checks.append(
        _check(
            code=QualificationCheckCode.NULL_SENTINEL_SCHEMA_DRIFT,
            status=schema_status,
            reason_code=schema_reason,
            evidence_sha256s=tuple(item.capability_manifest_sha256 for item in manifests),
            observed_value=schema_status.value,
            threshold_value="PASS",
        )
    )
    nondeterministic = any(
        item.reason_code is QualificationReasonCode.NONDETERMINISTIC_CAPTURE for item in manifests
    )
    checks.append(
        _check(
            code=QualificationCheckCode.DETERMINISTIC_CAPTURE_MANIFEST,
            status=(
                QualificationCheckStatus.BLOCKED
                if nondeterministic
                else QualificationCheckStatus.PASS
            ),
            reason_code=(
                QualificationReasonCode.NONDETERMINISTIC_CAPTURE
                if nondeterministic
                else QualificationReasonCode.CHECK_PASSED
            ),
            evidence_sha256s=(capture_manifest_sha256,),
            observed_value="mismatch" if nondeterministic else "deterministic",
            threshold_value="deterministic",
        )
    )
    return tuple(checks)


class PointInTimeQualificationWorkflow:
    def __init__(
        self,
        *,
        adapter: PointInTimeQualificationAdapter,
        store: PointInTimeQualificationStore,
        phase13_code_version_git_sha: str | None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.adapter = adapter
        self.store = store
        self.phase13_code_version_git_sha = phase13_code_version_git_sha
        self.clock = clock or _system_utc_now

    def _require_code_sha(self) -> str:
        try:
            return validate_code_git_sha(self.phase13_code_version_git_sha)
        except ValueError as exc:
            raise PointInTimeQualificationWorkflowConflict(
                "phase13 code identity is unavailable"
            ) from exc

    def _build_artifact(
        self,
        *,
        request: PointInTimeQualificationCreateRequest,
        request_fingerprint_sha256: str,
        code_version_git_sha: str,
    ) -> PointInTimeQualificationArtifact:
        if self.adapter.source_kind is QualificationSourceKind.DETERMINISTIC_MOCK:
            started = datetime(2024, 1, 2, 15, 0, tzinfo=UTC)
        else:
            started = self.clock().astimezone(UTC)
        try:
            manifests = tuple(
                self.adapter.inspect_capability(capability)
                for capability in PHASE13_CAPABILITY_ORDER
            )
        except Exception as exc:
            raise PointInTimeQualificationWorkflowConflict(
                "qualification adapter violated its sanitized contract"
            ) from exc
        if tuple(item.capability for item in manifests) != PHASE13_CAPABILITY_ORDER:
            raise PointInTimeQualificationWorkflowConflict(
                "qualification adapter changed the frozen capability registry"
            )
        completed = (
            started + timedelta(seconds=1)
            if self.adapter.source_kind is QualificationSourceKind.DETERMINISTIC_MOCK
            else self.clock().astimezone(UTC)
        )
        capture_hash = qualification_capture_manifest_sha256(
            provider_profile=self.adapter.profile,
            rights_attestation=self.adapter.rights_attestation,
            capability_manifests=manifests,
        )
        checks = _build_checks(
            adapter=self.adapter,
            manifests=manifests,
            completed_at_utc=completed,
            request_fingerprint_sha256=request_fingerprint_sha256,
            capture_manifest_sha256=capture_hash,
        )
        all_pass = all(item.status is QualificationCheckStatus.PASS for item in manifests) and all(
            item.status is QualificationCheckStatus.PASS for item in checks
        )
        if self.adapter.source_kind is QualificationSourceKind.DETERMINISTIC_MOCK:
            outcome = (
                QualificationOutcome.MOCK_PROOF_COMPLETE
                if all_pass
                else QualificationOutcome.BLOCKED
            )
        else:
            outcome = (
                QualificationOutcome.EXTERNAL_SAMPLE_QUALIFIED
                if all_pass
                else QualificationOutcome.BLOCKED
            )
        payload = {
            "schema_version": PHASE13_ARTIFACT_SCHEMA_VERSION,
            "qualification_id": identity(PHASE13_RUN_NAMESPACE, request_fingerprint_sha256),
            "qualification_idempotency_key": request.qualification_idempotency_key,
            "request_fingerprint_sha256": request_fingerprint_sha256,
            "source_kind": self.adapter.source_kind,
            "outcome": outcome,
            "provider_profile": self.adapter.profile,
            "rights_attestation": self.adapter.rights_attestation,
            "sample_plan_id": PHASE13_SAMPLE_PLAN_ID,
            "sample_plan_sha256": PHASE13_SAMPLE_PLAN_SHA256,
            "transport_profile_sha256": PHASE13_TRANSPORT_PROFILE_SHA256,
            "capture_manifest_sha256": capture_hash,
            "started_at_utc": started,
            "completed_at_utc": completed,
            "code_version_git_sha": code_version_git_sha,
            "capability_manifests": manifests,
            "checks": checks,
            "research_data_eligible": False,
            "strategy_promotion_authorized": False,
            "strategy_execution_eligible": False,
            "execution_authorized": False,
            "order_submission_authorized": False,
            "live_path_absent": True,
            "no_personalized_investment_advice": True,
            "no_real_performance_claimed": True,
            "disclaimer": PHASE13_DISCLAIMER,
        }
        return PointInTimeQualificationArtifact.model_validate(
            {
                **payload,
                "artifact_sha256": domain_sha256(PHASE13_ARTIFACT_HASH_DOMAIN, payload),
            }
        )

    def create_qualification(
        self, request: PointInTimeQualificationCreateRequest
    ) -> PointInTimeQualificationArtifact:
        code_sha = self._require_code_sha()
        fingerprint = qualification_request_fingerprint(
            request=request,
            provider_profile=self.adapter.profile,
            code_version_git_sha=code_sha,
        )
        with self.store.serialized_creation(request.qualification_idempotency_key) as creation:
            existing = creation.find_by_idempotency_key(request.qualification_idempotency_key)
            if existing is not None:
                if existing.request_fingerprint_sha256 != fingerprint:
                    raise PointInTimeQualificationWorkflowConflict(
                        "qualification idempotency key conflicts with immutable lineage"
                    )
                return existing
            artifact = self._build_artifact(
                request=request,
                request_fingerprint_sha256=fingerprint,
                code_version_git_sha=code_sha,
            )
            persisted = creation.create_qualification(artifact)
            if persisted.artifact_sha256 != artifact.artifact_sha256:
                raise PointInTimeQualificationWorkflowConflict(
                    "persisted qualification differs from the canonical artifact"
                )
            return persisted

    def get_qualification(self, qualification_id: UUID) -> PointInTimeQualificationArtifact:
        return self.store.get_qualification(qualification_id)


__all__ = [
    "PointInTimeQualificationCreation",
    "PointInTimeQualificationNotFound",
    "PointInTimeQualificationStore",
    "PointInTimeQualificationWorkflow",
    "PointInTimeQualificationWorkflowConflict",
]
