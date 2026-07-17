from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fable5_data.phase13.adapters import (
    DeterministicMockPointInTimeQualificationAdapter,
    build_capability_manifest,
)
from fable5_data.phase13.canonical import (
    PHASE13_ARTIFACT_HASH_DOMAIN,
    PHASE13_CAPABILITY_VALUES,
    PHASE13_CHECK_VALUES,
    domain_sha256,
)
from fable5_data.phase13.contracts import (
    PHASE13_ARTIFACT_SCHEMA_VERSION,
    PHASE13_CAPABILITY_ORDER,
    PHASE13_CAPABILITY_SCHEMA_VERSION,
    PHASE13_CHECK_ORDER,
    PHASE13_CHECK_SCHEMA_VERSION,
    PointInTimeQualificationArtifact,
    PointInTimeQualificationCreateRequest,
    QualificationCapability,
    QualificationCheckStatus,
    QualificationOutcome,
    QualificationReasonCode,
    qualification_request_fingerprint,
)
from pydantic import ValidationError


def test_phase13_closed_registries_and_schema_versions_are_exact() -> None:
    assert tuple(item.value for item in PHASE13_CAPABILITY_ORDER) == PHASE13_CAPABILITY_VALUES
    assert tuple(item.value for item in PHASE13_CHECK_ORDER) == PHASE13_CHECK_VALUES
    assert PHASE13_ARTIFACT_SCHEMA_VERSION == "phase13-pit-qualification-v1"
    assert PHASE13_CAPABILITY_SCHEMA_VERSION == "phase13-pit-capability-manifest-v1"
    assert PHASE13_CHECK_SCHEMA_VERSION == "phase13-pit-qualification-check-v1"


def test_request_is_strict_and_fingerprint_binds_code_profile_and_key() -> None:
    request = PointInTimeQualificationCreateRequest(
        qualification_idempotency_key="phase13-contract-proof-v1"
    )
    adapter = DeterministicMockPointInTimeQualificationAdapter()
    first = qualification_request_fingerprint(
        request=request,
        provider_profile=adapter.profile,
        code_version_git_sha="a" * 40,
    )
    repeated = qualification_request_fingerprint(
        request=request,
        provider_profile=adapter.profile,
        code_version_git_sha="a" * 40,
    )
    changed = qualification_request_fingerprint(
        request=request,
        provider_profile=adapter.profile,
        code_version_git_sha="b" * 40,
    )
    assert first == repeated
    assert first != changed
    with pytest.raises(ValidationError):
        PointInTimeQualificationCreateRequest.model_validate(
            {
                "qualification_idempotency_key": "phase13-contract-proof-v1",
                "provider": "tiingo",
            }
        )


def test_capability_manifest_rejects_future_availability_and_hash_tampering() -> None:
    adapter = DeterministicMockPointInTimeQualificationAdapter()
    manifest = adapter.inspect_capability(QualificationCapability.RAW_OHLCV_AVAILABILITY)
    payload = manifest.model_dump(mode="python")
    payload["available_at_max_utc"] = manifest.decision_time_utc + timedelta(seconds=1)
    with pytest.raises(ValidationError, match="available after"):
        type(manifest).model_validate(payload)

    payload = manifest.model_dump(mode="python")
    payload["record_count"] = manifest.record_count + 1
    with pytest.raises(ValidationError, match="hash"):
        type(manifest).model_validate(payload)


def test_passing_capability_requires_records_and_complete_hash_evidence() -> None:
    decision = datetime(2024, 1, 2, tzinfo=UTC)
    with pytest.raises(ValidationError, match="at least one"):
        build_capability_manifest(
            capability=QualificationCapability.SECURITY_MASTER_STABLE_IDENTITY,
            status=QualificationCheckStatus.PASS,
            reason_code=QualificationReasonCode.CHECK_PASSED,
            decision_time_utc=decision,
            event_time_min_utc=None,
            event_time_max_utc=None,
            available_at_min_utc=None,
            available_at_max_utc=None,
            record_count=0,
            missingness_count=0,
            revision_count=0,
            raw_evidence_sha256=None,
            normalized_evidence_sha256=None,
            schema_identity_sha256=None,
        )


def test_mock_artifact_cannot_be_relabelled_as_external_qualification(
    complete_mock_artifact: PointInTimeQualificationArtifact,
) -> None:
    payload = complete_mock_artifact.model_dump(mode="python")
    payload["outcome"] = QualificationOutcome.EXTERNAL_SAMPLE_QUALIFIED
    payload.pop("artifact_sha256")
    payload["artifact_sha256"] = domain_sha256(PHASE13_ARTIFACT_HASH_DOMAIN, payload)
    with pytest.raises(ValidationError, match="outcome"):
        PointInTimeQualificationArtifact.model_validate(payload)


def test_artifact_authority_fields_are_hard_false(
    complete_mock_artifact: PointInTimeQualificationArtifact,
) -> None:
    artifact = complete_mock_artifact
    assert artifact.research_data_eligible is False
    assert artifact.strategy_promotion_authorized is False
    assert artifact.strategy_execution_eligible is False
    assert artifact.execution_authorized is False
    assert artifact.order_submission_authorized is False
    assert artifact.live_path_absent is True
    assert artifact.no_personalized_investment_advice is True
    assert artifact.no_real_performance_claimed is True


@pytest.fixture
def complete_mock_artifact() -> PointInTimeQualificationArtifact:
    # Imported lazily to keep contract tests focused while exercising full model revalidation.
    from collections.abc import Iterator
    from contextlib import contextmanager

    from fable5_data.phase13.workflow import PointInTimeQualificationWorkflow

    class Store:
        def __init__(self) -> None:
            self.artifact: PointInTimeQualificationArtifact | None = None

        @contextmanager
        def serialized_creation(self, key: str) -> Iterator[Store]:
            del key
            yield self

        def find_by_idempotency_key(self, key: str) -> PointInTimeQualificationArtifact | None:
            if self.artifact is not None and self.artifact.qualification_idempotency_key == key:
                return self.artifact
            return None

        def create_qualification(
            self, artifact: PointInTimeQualificationArtifact
        ) -> PointInTimeQualificationArtifact:
            self.artifact = artifact
            return artifact

        def get_qualification(self, qualification_id: object) -> PointInTimeQualificationArtifact:
            del qualification_id
            assert self.artifact is not None
            return self.artifact

    workflow = PointInTimeQualificationWorkflow(
        adapter=DeterministicMockPointInTimeQualificationAdapter(),
        store=Store(),  # type: ignore[arg-type]
        phase13_code_version_git_sha="a" * 40,
    )
    return workflow.create_qualification(
        PointInTimeQualificationCreateRequest(
            qualification_idempotency_key="phase13-contract-artifact-v1"
        )
    )
