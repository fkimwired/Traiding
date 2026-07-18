"""Database-only synchronous orchestration for Phase 14 eligibility evidence."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import UUID

from fable5_data.phase13.contracts import (
    PointInTimeQualificationArtifact,
    QualificationCapabilityManifest,
    QualificationCheckStatus,
    QualificationOutcome,
    QualificationRequestCode,
    QualificationRequestStatus,
    QualificationSourceKind,
)
from fable5_data.phase14.canonical import (
    PHASE14_ARTIFACT_HASH_DOMAIN,
    PHASE14_ASSESSMENT_NAMESPACE,
    PHASE14_CHECK_HASH_DOMAIN,
    PHASE14_PAYLOAD_HASH_DOMAIN,
    PHASE14_POLICY_ID,
    PHASE14_POLICY_SHA256,
    domain_sha256,
    identity,
)
from fable5_data.phase14.contracts import (
    PHASE14_ARTIFACT_SCHEMA_VERSION,
    PHASE14_CHECK_ORDER,
    PHASE14_CHECK_SCHEMA_VERSION,
    PHASE14_DISCLAIMER,
    PHASE14_PAYLOAD_SCHEMA_VERSION,
    ResearchIngestionEligibilityArtifact,
    ResearchIngestionEligibilityCheck,
    ResearchIngestionEligibilityCheckCode,
    ResearchIngestionEligibilityCheckStatus,
    ResearchIngestionEligibilityCreateRequest,
    ResearchIngestionEligibilityOutcome,
    ResearchIngestionEligibilityPayload,
    ResearchIngestionEligibilityReasonCode,
    research_ingestion_eligibility_payload_manifest_sha256,
    research_ingestion_eligibility_request_fingerprint,
    validate_code_git_sha,
)


class ResearchIngestionEligibilityNotFound(LookupError):
    pass


class ResearchIngestionEligibilityWorkflowConflict(RuntimeError):
    pass


class PointInTimeQualificationSource(Protocol):
    def get_qualification(self, qualification_id: UUID) -> PointInTimeQualificationArtifact: ...


class ResearchIngestionEligibilityCreation(Protocol):
    def find_by_idempotency_key(self, key: str) -> ResearchIngestionEligibilityArtifact | None: ...

    def find_by_request_fingerprint(
        self, request_fingerprint_sha256: str
    ) -> ResearchIngestionEligibilityArtifact | None: ...

    def create_assessment(
        self, artifact: ResearchIngestionEligibilityArtifact
    ) -> ResearchIngestionEligibilityArtifact: ...


class ResearchIngestionEligibilityStore(ResearchIngestionEligibilityCreation, Protocol):
    def serialized_creation(
        self, key: str
    ) -> AbstractContextManager[ResearchIngestionEligibilityCreation]: ...

    def get_assessment(self, assessment_id: UUID) -> ResearchIngestionEligibilityArtifact: ...


def _system_utc_now() -> datetime:
    return datetime.now(UTC)


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("assessment clock must be timezone-aware")
    return value.astimezone(UTC)


def _payload(source: QualificationCapabilityManifest) -> ResearchIngestionEligibilityPayload:
    manifest = source
    request_hashes = tuple(
        sorted(item.request_evidence_sha256 for item in manifest.request_evidence)
    )
    payload = {
        "schema_version": PHASE14_PAYLOAD_SCHEMA_VERSION,
        "ordinal": manifest.ordinal,
        "capability": manifest.capability,
        "source_status": manifest.status,
        "source_reason_code": manifest.reason_code,
        "decision_time_utc": manifest.decision_time_utc,
        "event_time_min_utc": manifest.event_time_min_utc,
        "event_time_max_utc": manifest.event_time_max_utc,
        "available_at_min_utc": manifest.available_at_min_utc,
        "available_at_max_utc": manifest.available_at_max_utc,
        "record_count": manifest.record_count,
        "missingness_count": manifest.missingness_count,
        "revision_count": manifest.revision_count,
        "raw_evidence_sha256": manifest.raw_evidence_sha256,
        "normalized_evidence_sha256": manifest.normalized_evidence_sha256,
        "schema_identity_sha256": manifest.schema_identity_sha256,
        "request_evidence_count": len(request_hashes),
        "request_evidence_sha256s": request_hashes,
        "source_capability_manifest_sha256": manifest.capability_manifest_sha256,
    }
    return ResearchIngestionEligibilityPayload.model_validate(
        {**payload, "payload_sha256": domain_sha256(PHASE14_PAYLOAD_HASH_DOMAIN, payload)}
    )


def _check(
    *,
    code: ResearchIngestionEligibilityCheckCode,
    status: ResearchIngestionEligibilityCheckStatus,
    reason_code: ResearchIngestionEligibilityReasonCode,
    evidence_sha256s: tuple[str, ...],
    observed_value: str,
    threshold_value: str,
) -> ResearchIngestionEligibilityCheck:
    payload = {
        "schema_version": PHASE14_CHECK_SCHEMA_VERSION,
        "ordinal": PHASE14_CHECK_ORDER.index(code) + 1,
        "code": code,
        "status": status,
        "reason_code": reason_code,
        "observed_value": observed_value,
        "threshold_value": threshold_value,
        "evidence_sha256s": tuple(sorted(set(evidence_sha256s))),
    }
    return ResearchIngestionEligibilityCheck.model_validate(
        {**payload, "check_sha256": domain_sha256(PHASE14_CHECK_HASH_DOMAIN, payload)}
    )


def _passing_check(
    *,
    code: ResearchIngestionEligibilityCheckCode,
    evidence_sha256s: tuple[str, ...],
    observed_value: str,
    threshold_value: str,
) -> ResearchIngestionEligibilityCheck:
    return _check(
        code=code,
        status=ResearchIngestionEligibilityCheckStatus.PASS,
        reason_code=ResearchIngestionEligibilityReasonCode.CHECK_PASSED,
        evidence_sha256s=evidence_sha256s,
        observed_value=observed_value,
        threshold_value=threshold_value,
    )


def _mock_not_applicable_check(
    *,
    code: ResearchIngestionEligibilityCheckCode,
    evidence_sha256s: tuple[str, ...],
) -> ResearchIngestionEligibilityCheck:
    return _check(
        code=code,
        status=ResearchIngestionEligibilityCheckStatus.PASS,
        reason_code=ResearchIngestionEligibilityReasonCode.MOCK_NOT_APPLICABLE,
        evidence_sha256s=evidence_sha256s,
        observed_value="mock-not-applicable",
        threshold_value="mock-not-applicable",
    )


def _build_checks(
    *,
    source: PointInTimeQualificationArtifact,
    payloads: tuple[ResearchIngestionEligibilityPayload, ...],
    payload_manifest_sha256: str,
    completed_at_utc: datetime,
) -> tuple[ResearchIngestionEligibilityCheck, ...]:
    source_identity_evidence = (
        source.request_fingerprint_sha256,
        source.artifact_sha256,
        source.capture_manifest_sha256,
    )
    checks: list[ResearchIngestionEligibilityCheck] = [
        _passing_check(
            code=ResearchIngestionEligibilityCheckCode.QUALIFICATION_IDENTITY_INTEGRITY,
            evidence_sha256s=source_identity_evidence,
            observed_value="valid",
            threshold_value="valid",
        )
    ]
    is_mock = source.source_kind is QualificationSourceKind.DETERMINISTIC_MOCK
    checks.append(
        _check(
            code=ResearchIngestionEligibilityCheckCode.QUALIFICATION_SOURCE_KIND_ALLOWED,
            status=(
                ResearchIngestionEligibilityCheckStatus.PASS
                if is_mock
                else ResearchIngestionEligibilityCheckStatus.BLOCKED
            ),
            reason_code=(
                ResearchIngestionEligibilityReasonCode.CHECK_PASSED
                if is_mock
                else ResearchIngestionEligibilityReasonCode.SOURCE_KIND_NOT_ALLOWED
            ),
            evidence_sha256s=(source.artifact_sha256, source.request_fingerprint_sha256),
            observed_value=source.source_kind.value,
            threshold_value=QualificationSourceKind.DETERMINISTIC_MOCK.value,
        )
    )
    source_mock_complete = is_mock and source.outcome is QualificationOutcome.MOCK_PROOF_COMPLETE
    checks.append(
        _check(
            code=ResearchIngestionEligibilityCheckCode.QUALIFICATION_OUTCOME_ELIGIBLE_OR_MOCK,
            status=(
                ResearchIngestionEligibilityCheckStatus.PASS
                if source_mock_complete
                else ResearchIngestionEligibilityCheckStatus.BLOCKED
            ),
            reason_code=(
                ResearchIngestionEligibilityReasonCode.CHECK_PASSED
                if source_mock_complete
                else ResearchIngestionEligibilityReasonCode.QUALIFICATION_OUTCOME_NOT_ELIGIBLE
            ),
            evidence_sha256s=(source.artifact_sha256,),
            observed_value=source.outcome.value,
            threshold_value=QualificationOutcome.MOCK_PROOF_COMPLETE.value,
        )
    )
    capabilities_pass = all(
        item.source_status is QualificationCheckStatus.PASS for item in payloads
    )
    checks.append(
        _check(
            code=ResearchIngestionEligibilityCheckCode.CAPABILITY_MANIFEST_COMPLETE_PASSING,
            status=(
                ResearchIngestionEligibilityCheckStatus.PASS
                if capabilities_pass
                else ResearchIngestionEligibilityCheckStatus.BLOCKED
            ),
            reason_code=(
                ResearchIngestionEligibilityReasonCode.CHECK_PASSED
                if capabilities_pass
                else ResearchIngestionEligibilityReasonCode.CAPABILITY_MANIFEST_NOT_PASSING
            ),
            evidence_sha256s=tuple(item.source_capability_manifest_sha256 for item in payloads),
            observed_value=("6-of-6" if capabilities_pass else "fewer-than-6-passing"),
            threshold_value="6-of-6",
        )
    )
    qualification_checks_pass = all(
        item.status is QualificationCheckStatus.PASS for item in source.checks
    )
    checks.append(
        _check(
            code=ResearchIngestionEligibilityCheckCode.QUALIFICATION_CHECKS_COMPLETE_PASSING,
            status=(
                ResearchIngestionEligibilityCheckStatus.PASS
                if qualification_checks_pass
                else ResearchIngestionEligibilityCheckStatus.BLOCKED
            ),
            reason_code=(
                ResearchIngestionEligibilityReasonCode.CHECK_PASSED
                if qualification_checks_pass
                else ResearchIngestionEligibilityReasonCode.QUALIFICATION_CHECKS_NOT_PASSING
            ),
            evidence_sha256s=tuple(item.check_sha256 for item in source.checks),
            observed_value=("12-of-12" if qualification_checks_pass else "fewer-than-12-passing"),
            threshold_value="12-of-12",
        )
    )

    request_evidence = tuple(
        evidence
        for manifest in source.capability_manifests
        for evidence in manifest.request_evidence
    )
    request_evidence_hashes = tuple(item.request_evidence_sha256 for item in request_evidence)
    if is_mock:
        checks.append(
            _mock_not_applicable_check(
                code=(
                    ResearchIngestionEligibilityCheckCode.EXTERNAL_REQUEST_EVIDENCE_COMPLETE_OR_MOCK
                ),
                evidence_sha256s=(source.artifact_sha256, source.capture_manifest_sha256),
            )
        )
    else:
        performed_codes = {
            item.code
            for item in request_evidence
            if item.external_request_performed
            and item.status is QualificationRequestStatus.OBSERVED
        }
        external_complete = performed_codes == set(QualificationRequestCode)
        checks.append(
            _check(
                code=(
                    ResearchIngestionEligibilityCheckCode.EXTERNAL_REQUEST_EVIDENCE_COMPLETE_OR_MOCK
                ),
                status=(
                    ResearchIngestionEligibilityCheckStatus.PASS
                    if external_complete
                    else ResearchIngestionEligibilityCheckStatus.UNCOMPUTABLE
                ),
                reason_code=(
                    ResearchIngestionEligibilityReasonCode.CHECK_PASSED
                    if external_complete
                    else ResearchIngestionEligibilityReasonCode.EXTERNAL_REQUEST_EVIDENCE_INCOMPLETE
                ),
                evidence_sha256s=request_evidence_hashes or (source.artifact_sha256,),
                observed_value=(
                    "complete-read-only-evidence"
                    if external_complete
                    else "incomplete-or-unverified"
                ),
                threshold_value="5-of-5-observed",
            )
        )

    rights = source.rights_attestation
    if is_mock:
        for code in (
            ResearchIngestionEligibilityCheckCode.INDEPENDENT_RIGHTS_REFERENCE_PRESENT_OR_MOCK,
            ResearchIngestionEligibilityCheckCode.USE_RIGHTS_CURRENT_OR_MOCK,
            ResearchIngestionEligibilityCheckCode.USE_RIGHTS_SCOPE_SUFFICIENT_OR_MOCK,
        ):
            checks.append(
                _mock_not_applicable_check(
                    code=code,
                    evidence_sha256s=(source.artifact_sha256,),
                )
            )
    else:
        rights_evidence = (
            (rights.attestation_sha256,) if rights is not None else (source.artifact_sha256,)
        )
        checks.append(
            _check(
                code=(
                    ResearchIngestionEligibilityCheckCode.INDEPENDENT_RIGHTS_REFERENCE_PRESENT_OR_MOCK
                ),
                status=ResearchIngestionEligibilityCheckStatus.UNCOMPUTABLE,
                reason_code=(
                    ResearchIngestionEligibilityReasonCode.INDEPENDENT_RIGHTS_REFERENCE_UNVERIFIED
                    if rights is not None
                    else ResearchIngestionEligibilityReasonCode.RIGHTS_REFERENCE_MISSING
                ),
                evidence_sha256s=rights_evidence,
                observed_value="unverified",
                threshold_value="independently-authenticated",
            )
        )
        rights_current = rights is not None and (
            rights.valid_from_utc <= completed_at_utc < rights.expires_at_utc
        )
        checks.append(
            _check(
                code=ResearchIngestionEligibilityCheckCode.USE_RIGHTS_CURRENT_OR_MOCK,
                status=(
                    ResearchIngestionEligibilityCheckStatus.BLOCKED
                    if rights is not None and not rights_current
                    else ResearchIngestionEligibilityCheckStatus.UNCOMPUTABLE
                ),
                reason_code=(
                    ResearchIngestionEligibilityReasonCode.RIGHTS_REFERENCE_MISSING
                    if rights is None
                    else (
                        ResearchIngestionEligibilityReasonCode.RIGHTS_NOT_CURRENT
                        if not rights_current
                        else (
                            ResearchIngestionEligibilityReasonCode.INDEPENDENT_RIGHTS_REFERENCE_UNVERIFIED
                        )
                    )
                ),
                evidence_sha256s=rights_evidence,
                observed_value=("current-but-unverified" if rights_current else "missing-or-stale"),
                threshold_value="independently-verified-current",
            )
        )
        rights_sufficient = rights is not None and all(
            (rights.storage_allowed, rights.non_display_allowed, rights.derived_data_allowed)
        )
        checks.append(
            _check(
                code=ResearchIngestionEligibilityCheckCode.USE_RIGHTS_SCOPE_SUFFICIENT_OR_MOCK,
                status=(
                    ResearchIngestionEligibilityCheckStatus.BLOCKED
                    if rights is not None and not rights_sufficient
                    else ResearchIngestionEligibilityCheckStatus.UNCOMPUTABLE
                ),
                reason_code=(
                    ResearchIngestionEligibilityReasonCode.RIGHTS_REFERENCE_MISSING
                    if rights is None
                    else (
                        ResearchIngestionEligibilityReasonCode.RIGHTS_SCOPE_INSUFFICIENT
                        if not rights_sufficient
                        else (
                            ResearchIngestionEligibilityReasonCode.INDEPENDENT_RIGHTS_REFERENCE_UNVERIFIED
                        )
                    )
                ),
                evidence_sha256s=rights_evidence,
                observed_value=(
                    "sufficient-but-unverified" if rights_sufficient else "missing-or-insufficient"
                ),
                threshold_value="independently-verified-storage-nondisplay-derived",
            )
        )

    checks.extend(
        (
            _passing_check(
                code=ResearchIngestionEligibilityCheckCode.LICENSED_PAYLOAD_ABSENT,
                evidence_sha256s=(source.artifact_sha256, payload_manifest_sha256),
                observed_value="absent",
                threshold_value="absent",
            ),
            _passing_check(
                code=ResearchIngestionEligibilityCheckCode.RESEARCH_SNAPSHOT_ABSENT,
                evidence_sha256s=(source.artifact_sha256,),
                observed_value="absent",
                threshold_value="absent",
            ),
        )
    )
    source_authority_absent = all(
        (
            source.research_data_eligible is False,
            source.strategy_promotion_authorized is False,
            source.strategy_execution_eligible is False,
            source.execution_authorized is False,
            source.order_submission_authorized is False,
            source.live_path_absent is True,
            source.no_personalized_investment_advice is True,
            source.no_real_performance_claimed is True,
        )
    )
    checks.append(
        _check(
            code=ResearchIngestionEligibilityCheckCode.PROMOTION_EXECUTION_AUTHORITY_ABSENT,
            status=(
                ResearchIngestionEligibilityCheckStatus.PASS
                if source_authority_absent
                else ResearchIngestionEligibilityCheckStatus.BLOCKED
            ),
            reason_code=(
                ResearchIngestionEligibilityReasonCode.CHECK_PASSED
                if source_authority_absent
                else ResearchIngestionEligibilityReasonCode.AUTHORITY_BOUNDARY_VIOLATION
            ),
            evidence_sha256s=tuple(item.check_sha256 for item in source.checks),
            observed_value=("absent" if source_authority_absent else "present"),
            threshold_value="absent",
        )
    )
    return tuple(checks)


class ResearchIngestionEligibilityWorkflow:
    def __init__(
        self,
        *,
        qualification_source: PointInTimeQualificationSource,
        store: ResearchIngestionEligibilityStore,
        phase14_code_version_git_sha: str | None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.qualification_source = qualification_source
        self.store = store
        self.phase14_code_version_git_sha = phase14_code_version_git_sha
        self.clock = clock or _system_utc_now

    def _require_code_sha(self) -> str:
        try:
            return validate_code_git_sha(self.phase14_code_version_git_sha)
        except ValueError as exc:
            raise ResearchIngestionEligibilityWorkflowConflict(
                "phase14 code identity is unavailable"
            ) from exc

    def _load_source(self, qualification_id: UUID) -> PointInTimeQualificationArtifact:
        try:
            source = self.qualification_source.get_qualification(qualification_id)
            validated = PointInTimeQualificationArtifact.model_validate(
                source.model_dump(mode="python")
            )
        except Exception as exc:
            raise ResearchIngestionEligibilityWorkflowConflict(
                "qualification source evidence is unavailable or invalid"
            ) from exc
        if validated.qualification_id != qualification_id:
            raise ResearchIngestionEligibilityWorkflowConflict(
                "qualification source evidence has conflicting lineage"
            )
        return validated

    def _build_artifact(
        self,
        *,
        request: ResearchIngestionEligibilityCreateRequest,
        request_fingerprint_sha256: str,
        code_version_git_sha: str,
    ) -> ResearchIngestionEligibilityArtifact:
        source = self._load_source(request.qualification_id)
        payloads = tuple(_payload(item) for item in source.capability_manifests)
        payload_manifest_sha256 = research_ingestion_eligibility_payload_manifest_sha256(payloads)
        if source.source_kind is QualificationSourceKind.DETERMINISTIC_MOCK:
            started_at_utc = source.completed_at_utc + timedelta(seconds=1)
        else:
            try:
                started_at_utc = _utc(self.clock())
            except ValueError as exc:
                raise ResearchIngestionEligibilityWorkflowConflict(
                    "phase14 assessment clock is unavailable"
                ) from exc
        completed_at_utc = started_at_utc
        checks = _build_checks(
            source=source,
            payloads=payloads,
            payload_manifest_sha256=payload_manifest_sha256,
            completed_at_utc=completed_at_utc,
        )
        all_checks_pass = all(
            item.status is ResearchIngestionEligibilityCheckStatus.PASS for item in checks
        )
        outcome = (
            ResearchIngestionEligibilityOutcome.MOCK_PROOF_COMPLETE
            if source.source_kind is QualificationSourceKind.DETERMINISTIC_MOCK
            and source.outcome is QualificationOutcome.MOCK_PROOF_COMPLETE
            and all_checks_pass
            else ResearchIngestionEligibilityOutcome.BLOCKED
        )
        rights = source.rights_attestation
        artifact_payload = {
            "schema_version": PHASE14_ARTIFACT_SCHEMA_VERSION,
            "assessment_id": identity(PHASE14_ASSESSMENT_NAMESPACE, request_fingerprint_sha256),
            "assessment_idempotency_key": request.assessment_idempotency_key,
            "request_fingerprint_sha256": request_fingerprint_sha256,
            "policy_id": PHASE14_POLICY_ID,
            "policy_sha256": PHASE14_POLICY_SHA256,
            "qualification_id": source.qualification_id,
            "qualification_request_fingerprint_sha256": source.request_fingerprint_sha256,
            "qualification_artifact_sha256": source.artifact_sha256,
            "qualification_capture_manifest_sha256": source.capture_manifest_sha256,
            "qualification_source_kind": source.source_kind,
            "qualification_outcome": source.outcome,
            "qualification_rights_attestation_id": (
                None if rights is None else rights.attestation_id
            ),
            "qualification_rights_attestation_sha256": (
                None if rights is None else rights.attestation_sha256
            ),
            "qualification_code_version_git_sha": source.code_version_git_sha,
            "qualification_capability_manifest_sha256s": tuple(
                item.capability_manifest_sha256 for item in source.capability_manifests
            ),
            "qualification_check_sha256s": tuple(item.check_sha256 for item in source.checks),
            "payload_manifest_sha256": payload_manifest_sha256,
            "started_at_utc": started_at_utc,
            "completed_at_utc": completed_at_utc,
            "code_version_git_sha": code_version_git_sha,
            "outcome": outcome,
            "payloads": payloads,
            "checks": checks,
            "external_request_performed": False,
            "provider_payload_persisted": False,
            "research_ingestion_authorized": False,
            "research_snapshot_created": False,
            "research_data_eligible": False,
            "research_run_created": False,
            "research_run_authorized": False,
            "research_executed": False,
            "performance_computed": False,
            "pass_research_granted": False,
            "strategy_promotion_authorized": False,
            "paper_approval_granted": False,
            "strategy_execution_eligible": False,
            "execution_authorized": False,
            "order_submission_authorized": False,
            "live_path_absent": True,
            "no_personalized_investment_advice": True,
            "no_real_performance_claimed": True,
            "disclaimer": PHASE14_DISCLAIMER,
        }
        return ResearchIngestionEligibilityArtifact.model_validate(
            {
                **artifact_payload,
                "artifact_sha256": domain_sha256(PHASE14_ARTIFACT_HASH_DOMAIN, artifact_payload),
            }
        )

    def create_assessment(
        self, request: ResearchIngestionEligibilityCreateRequest
    ) -> ResearchIngestionEligibilityArtifact:
        code_sha = self._require_code_sha()
        fingerprint = research_ingestion_eligibility_request_fingerprint(
            request=request,
            code_version_git_sha=code_sha,
        )
        with self.store.serialized_creation(request.assessment_idempotency_key) as creation:
            existing = creation.find_by_idempotency_key(request.assessment_idempotency_key)
            if existing is not None:
                if existing.request_fingerprint_sha256 != fingerprint:
                    raise ResearchIngestionEligibilityWorkflowConflict(
                        "assessment idempotency key conflicts with immutable lineage"
                    )
                try:
                    return ResearchIngestionEligibilityArtifact.model_validate(
                        existing.model_dump(mode="python")
                    )
                except Exception as exc:
                    raise ResearchIngestionEligibilityWorkflowConflict(
                        "persisted assessment evidence is invalid"
                    ) from exc
            semantic_match = creation.find_by_request_fingerprint(fingerprint)
            if semantic_match is not None:
                raise ResearchIngestionEligibilityWorkflowConflict(
                    "assessment semantic fingerprint already has a different idempotency key"
                )
            artifact = self._build_artifact(
                request=request,
                request_fingerprint_sha256=fingerprint,
                code_version_git_sha=code_sha,
            )
            persisted = creation.create_assessment(artifact)
            if persisted.artifact_sha256 != artifact.artifact_sha256:
                raise ResearchIngestionEligibilityWorkflowConflict(
                    "persisted assessment differs from the canonical artifact"
                )
            return persisted

    def get_assessment(self, assessment_id: UUID) -> ResearchIngestionEligibilityArtifact:
        return self.store.get_assessment(assessment_id)


__all__ = [
    "PointInTimeQualificationSource",
    "ResearchIngestionEligibilityCreation",
    "ResearchIngestionEligibilityNotFound",
    "ResearchIngestionEligibilityStore",
    "ResearchIngestionEligibilityWorkflow",
    "ResearchIngestionEligibilityWorkflowConflict",
]
