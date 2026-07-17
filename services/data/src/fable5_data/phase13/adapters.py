"""Vendor-neutral qualification adapter boundary and deterministic Phase 13 mock."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Protocol, runtime_checkable

from fable5_data.phase13.canonical import (
    PHASE13_CAPABILITY_HASH_DOMAIN,
    PHASE13_FIXED_ENDPOINTS,
    PHASE13_NORMALIZED_EVIDENCE_HASH_DOMAIN,
    PHASE13_REQUEST_EVIDENCE_HASH_DOMAIN,
    PHASE13_SCHEMA_IDENTITY_HASH_DOMAIN,
    PHASE13_TRANSPORT_PROFILE_SHA256,
    domain_sha256,
)
from fable5_data.phase13.contracts import (
    PHASE13_CAPABILITY_ORDER,
    QualificationCapability,
    QualificationCapabilityManifest,
    QualificationCheckStatus,
    QualificationProviderProfile,
    QualificationReasonCode,
    QualificationRequestCode,
    QualificationRequestEvidence,
    QualificationRequestStatus,
    QualificationSourceKind,
    QualificationUseRightsAttestation,
)


@runtime_checkable
class PointInTimeQualificationAdapter(Protocol):
    """Complete read-only boundary: six frozen inspections and no generic transport method."""

    @property
    def source_kind(self) -> QualificationSourceKind: ...

    @property
    def profile(self) -> QualificationProviderProfile: ...

    @property
    def rights_attestation(self) -> QualificationUseRightsAttestation | None: ...

    def inspect_capability(
        self, capability: QualificationCapability
    ) -> QualificationCapabilityManifest: ...


def build_request_evidence(
    *,
    ordinal: int,
    code: QualificationRequestCode,
    target: str,
    status: QualificationRequestStatus,
    external_request_performed: bool,
    request_started_at_utc: datetime | None,
    request_completed_at_utc: datetime | None,
    reason_code: QualificationReasonCode,
    http_status: int | None = None,
    raw_body_sha256: str | None = None,
    body_size_bytes: int | None = None,
    record_count: int | None = None,
) -> QualificationRequestEvidence:
    payload = {
        "schema_version": "phase13-pit-request-evidence-v1",
        "ordinal": ordinal,
        "code": code,
        "status": status,
        "method": "GET",
        "host": "api.tiingo.com",
        "port": 443,
        "target": target,
        "external_request_performed": external_request_performed,
        "request_started_at_utc": request_started_at_utc,
        "request_completed_at_utc": request_completed_at_utc,
        "http_status": http_status,
        "raw_body_sha256": raw_body_sha256,
        "body_size_bytes": body_size_bytes,
        "record_count": record_count,
        "reason_code": reason_code,
    }
    return QualificationRequestEvidence.model_validate(
        {
            **payload,
            "request_evidence_sha256": domain_sha256(PHASE13_REQUEST_EVIDENCE_HASH_DOMAIN, payload),
        }
    )


def build_capability_manifest(
    *,
    capability: QualificationCapability,
    status: QualificationCheckStatus,
    reason_code: QualificationReasonCode,
    decision_time_utc: datetime,
    event_time_min_utc: datetime | None,
    event_time_max_utc: datetime | None,
    available_at_min_utc: datetime | None,
    available_at_max_utc: datetime | None,
    record_count: int,
    missingness_count: int,
    revision_count: int,
    raw_evidence_sha256: str | None,
    normalized_evidence_sha256: str | None,
    schema_identity_sha256: str | None,
    request_evidence: tuple[QualificationRequestEvidence, ...] = (),
) -> QualificationCapabilityManifest:
    payload = {
        "schema_version": "phase13-pit-capability-manifest-v1",
        "ordinal": PHASE13_CAPABILITY_ORDER.index(capability) + 1,
        "capability": capability,
        "status": status,
        "reason_code": reason_code,
        "decision_time_utc": decision_time_utc,
        "event_time_min_utc": event_time_min_utc,
        "event_time_max_utc": event_time_max_utc,
        "available_at_min_utc": available_at_min_utc,
        "available_at_max_utc": available_at_max_utc,
        "record_count": record_count,
        "missingness_count": missingness_count,
        "revision_count": revision_count,
        "raw_evidence_sha256": raw_evidence_sha256,
        "normalized_evidence_sha256": normalized_evidence_sha256,
        "schema_identity_sha256": schema_identity_sha256,
        "request_evidence": request_evidence,
    }
    return QualificationCapabilityManifest.model_validate(
        {
            **payload,
            "capability_manifest_sha256": domain_sha256(PHASE13_CAPABILITY_HASH_DOMAIN, payload),
        }
    )


class MockQualificationScenario(StrEnum):
    COMPLETE = "COMPLETE"
    CURRENT_UNIVERSE_SUBSTITUTION = "CURRENT_UNIVERSE_SUBSTITUTION"
    MISSING_DELISTING_RETURN = "MISSING_DELISTING_RETURN"
    ACTION_LOOKAHEAD = "ACTION_LOOKAHEAD"
    RESTATEMENT_OVERWRITE = "RESTATEMENT_OVERWRITE"
    NULL_SENTINEL_DRIFT = "NULL_SENTINEL_DRIFT"
    SCHEMA_DRIFT = "SCHEMA_DRIFT"
    RAW_NORMALIZED_MISMATCH = "RAW_NORMALIZED_MISMATCH"
    NONDETERMINISTIC_CAPTURE = "NONDETERMINISTIC_CAPTURE"


_CAPABILITY_REASON_BY_SCENARIO = {
    MockQualificationScenario.CURRENT_UNIVERSE_SUBSTITUTION: (
        QualificationCapability.POINT_IN_TIME_UNIVERSE_MEMBERSHIP,
        QualificationReasonCode.CURRENT_UNIVERSE_ONLY,
    ),
    MockQualificationScenario.MISSING_DELISTING_RETURN: (
        QualificationCapability.DELISTING_RETURN_SEMANTICS,
        QualificationReasonCode.DELISTING_RETURN_UNAVAILABLE,
    ),
    MockQualificationScenario.ACTION_LOOKAHEAD: (
        QualificationCapability.CORPORATE_ACTION_ANNOUNCEMENT_REVISION,
        QualificationReasonCode.ACTION_REVISION_INVALID,
    ),
    MockQualificationScenario.RESTATEMENT_OVERWRITE: (
        QualificationCapability.AS_REPORTED_FUNDAMENTAL_REVISION,
        QualificationReasonCode.FUNDAMENTAL_REVISION_INVALID,
    ),
    MockQualificationScenario.NULL_SENTINEL_DRIFT: (
        QualificationCapability.RAW_OHLCV_AVAILABILITY,
        QualificationReasonCode.NULL_SENTINEL_DRIFT,
    ),
    MockQualificationScenario.SCHEMA_DRIFT: (
        QualificationCapability.SECURITY_MASTER_STABLE_IDENTITY,
        QualificationReasonCode.SCHEMA_DRIFT,
    ),
    MockQualificationScenario.RAW_NORMALIZED_MISMATCH: (
        QualificationCapability.RAW_OHLCV_AVAILABILITY,
        QualificationReasonCode.RAW_NORMALIZED_MISMATCH,
    ),
    MockQualificationScenario.NONDETERMINISTIC_CAPTURE: (
        QualificationCapability.AS_REPORTED_FUNDAMENTAL_REVISION,
        QualificationReasonCode.NONDETERMINISTIC_CAPTURE,
    ),
}


class DeterministicMockPointInTimeQualificationAdapter:
    """Frozen structural proof; it has no socket path and can never claim external qualification."""

    _BASE = datetime(2024, 1, 2, 15, 0, tzinfo=UTC)
    _PROFILE = QualificationProviderProfile(
        source_kind=QualificationSourceKind.DETERMINISTIC_MOCK,
        provider_id="phase13-deterministic-mock-provider",
        adapter_id="phase13-deterministic-pit-qualification-adapter",
        adapter_version="phase13-deterministic-pit-qualification-adapter-v1",
        dataset_id="phase13-deterministic-qualification-fixtures",
        product_id="phase13-deterministic-qualification-product",
        synthetic=True,
    )

    def __init__(
        self,
        scenario: MockQualificationScenario = MockQualificationScenario.COMPLETE,
    ) -> None:
        self._scenario = scenario

    @property
    def source_kind(self) -> QualificationSourceKind:
        return QualificationSourceKind.DETERMINISTIC_MOCK

    @property
    def profile(self) -> QualificationProviderProfile:
        return self._PROFILE

    @property
    def rights_attestation(self) -> None:
        return None

    @property
    def transport_profile_sha256(self) -> str:
        return PHASE13_TRANSPORT_PROFILE_SHA256

    def _requests_for(
        self, capability: QualificationCapability
    ) -> tuple[QualificationRequestEvidence, ...]:
        endpoints = [
            item for item in PHASE13_FIXED_ENDPOINTS if item["capability"] == capability.value
        ]
        result: list[QualificationRequestEvidence] = []
        for endpoint in endpoints:
            ordinal_value = endpoint["ordinal"]
            if not isinstance(ordinal_value, int):  # pragma: no cover - frozen constant
                raise ValueError("fixed endpoint ordinal is invalid")
            ordinal = ordinal_value
            started = self._BASE + timedelta(milliseconds=ordinal * 10)
            raw_hash = domain_sha256(
                PHASE13_REQUEST_EVIDENCE_HASH_DOMAIN,
                {
                    "fixture": "phase13-synthetic-request-evidence-v1",
                    "code": endpoint["code"],
                    "target": endpoint["target"],
                },
            )
            result.append(
                build_request_evidence(
                    ordinal=ordinal,
                    code=QualificationRequestCode(str(endpoint["code"])),
                    target=str(endpoint["target"]),
                    status=QualificationRequestStatus.OBSERVED,
                    external_request_performed=False,
                    request_started_at_utc=started,
                    request_completed_at_utc=started + timedelta(milliseconds=1),
                    reason_code=QualificationReasonCode.CHECK_PASSED,
                    raw_body_sha256=raw_hash,
                    body_size_bytes=128 + ordinal,
                    record_count=ordinal + 1,
                )
            )
        return tuple(result)

    def inspect_capability(
        self, capability: QualificationCapability
    ) -> QualificationCapabilityManifest:
        if capability not in PHASE13_CAPABILITY_ORDER:  # pragma: no cover - closed enum
            raise ValueError("capability is outside the frozen qualification registry")
        blocked = _CAPABILITY_REASON_BY_SCENARIO.get(self._scenario)
        status = QualificationCheckStatus.PASS
        reason = QualificationReasonCode.CHECK_PASSED
        if blocked is not None and blocked[0] is capability:
            status = QualificationCheckStatus.BLOCKED
            reason = blocked[1]
        ordinal = PHASE13_CAPABILITY_ORDER.index(capability) + 1
        event_min = self._BASE - timedelta(days=ordinal * 30)
        event_max = event_min + timedelta(days=2)
        available_min = event_min + timedelta(hours=1)
        available_max = event_max + timedelta(hours=1)
        structural_payload = {
            "fixture": "phase13-synthetic-capability-v1",
            "capability": capability,
            "ordinal": ordinal,
            "scenario": self._scenario,
            "status": status,
            "reason": reason,
        }
        raw_hash = domain_sha256(PHASE13_REQUEST_EVIDENCE_HASH_DOMAIN, structural_payload)
        normalized_hash = domain_sha256(PHASE13_NORMALIZED_EVIDENCE_HASH_DOMAIN, structural_payload)
        schema_hash = domain_sha256(
            PHASE13_SCHEMA_IDENTITY_HASH_DOMAIN,
            {"capability": capability, "fields": ("identity", "event_time", "available_at")},
        )
        return build_capability_manifest(
            capability=capability,
            status=status,
            reason_code=reason,
            decision_time_utc=self._BASE,
            event_time_min_utc=event_min,
            event_time_max_utc=event_max,
            available_at_min_utc=available_min,
            available_at_max_utc=available_max,
            record_count=ordinal + 1,
            missingness_count=(
                1 if capability is QualificationCapability.DELISTING_RETURN_SEMANTICS else 0
            ),
            revision_count=(
                2
                if capability
                in {
                    QualificationCapability.CORPORATE_ACTION_ANNOUNCEMENT_REVISION,
                    QualificationCapability.AS_REPORTED_FUNDAMENTAL_REVISION,
                }
                else 1
            ),
            raw_evidence_sha256=raw_hash,
            normalized_evidence_sha256=normalized_hash,
            schema_identity_sha256=schema_hash,
            request_evidence=self._requests_for(capability),
        )


__all__ = [
    "DeterministicMockPointInTimeQualificationAdapter",
    "MockQualificationScenario",
    "PointInTimeQualificationAdapter",
    "build_capability_manifest",
    "build_request_evidence",
]
