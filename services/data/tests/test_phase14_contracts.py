from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from uuid import UUID

import pytest
from fable5_data.phase13.adapters import DeterministicMockPointInTimeQualificationAdapter
from fable5_data.phase13.contracts import (
    PointInTimeQualificationArtifact,
    PointInTimeQualificationCreateRequest,
)
from fable5_data.phase13.workflow import PointInTimeQualificationWorkflow
from fable5_data.phase14.canonical import (
    PHASE14_ARTIFACT_HASH_DOMAIN,
    PHASE14_CHECK_HASH_DOMAIN,
    PHASE14_POLICY_ID,
    PHASE14_POLICY_SHA256,
    domain_sha256,
)
from fable5_data.phase14.contracts import (
    PHASE14_CHECK_ORDER,
    ResearchIngestionEligibilityArtifact,
    ResearchIngestionEligibilityCheckCode,
    ResearchIngestionEligibilityCheckStatus,
    ResearchIngestionEligibilityCreateRequest,
    ResearchIngestionEligibilityOutcome,
    ResearchIngestionEligibilityReasonCode,
    research_ingestion_eligibility_request_fingerprint,
)
from fable5_data.phase14.workflow import ResearchIngestionEligibilityWorkflow
from pydantic import ValidationError


class _QualificationMemory:
    def __init__(self) -> None:
        self.by_key: dict[str, PointInTimeQualificationArtifact] = {}
        self.by_id: dict[UUID, PointInTimeQualificationArtifact] = {}

    @contextmanager
    def serialized_creation(self, key: str) -> Iterator[_QualificationMemory]:
        del key
        yield self

    def find_by_idempotency_key(self, key: str) -> PointInTimeQualificationArtifact | None:
        return self.by_key.get(key)

    def create_qualification(
        self, artifact: PointInTimeQualificationArtifact
    ) -> PointInTimeQualificationArtifact:
        self.by_key[artifact.qualification_idempotency_key] = artifact
        self.by_id[artifact.qualification_id] = artifact
        return artifact

    def get_qualification(self, qualification_id: UUID) -> PointInTimeQualificationArtifact:
        return self.by_id[qualification_id]


class _AssessmentMemory:
    def __init__(self) -> None:
        self.by_key: dict[str, ResearchIngestionEligibilityArtifact] = {}
        self.by_fingerprint: dict[str, ResearchIngestionEligibilityArtifact] = {}
        self.by_id: dict[UUID, ResearchIngestionEligibilityArtifact] = {}

    @contextmanager
    def serialized_creation(self, key: str) -> Iterator[_AssessmentMemory]:
        del key
        yield self

    def find_by_idempotency_key(self, key: str) -> ResearchIngestionEligibilityArtifact | None:
        return self.by_key.get(key)

    def find_by_request_fingerprint(
        self, request_fingerprint_sha256: str
    ) -> ResearchIngestionEligibilityArtifact | None:
        return self.by_fingerprint.get(request_fingerprint_sha256)

    def create_assessment(
        self, artifact: ResearchIngestionEligibilityArtifact
    ) -> ResearchIngestionEligibilityArtifact:
        self.by_key[artifact.assessment_idempotency_key] = artifact
        self.by_fingerprint[artifact.request_fingerprint_sha256] = artifact
        self.by_id[artifact.assessment_id] = artifact
        return artifact

    def get_assessment(self, assessment_id: UUID) -> ResearchIngestionEligibilityArtifact:
        return self.by_id[assessment_id]


def _artifact() -> ResearchIngestionEligibilityArtifact:
    source = _QualificationMemory()
    qualification = PointInTimeQualificationWorkflow(
        adapter=DeterministicMockPointInTimeQualificationAdapter(),
        store=source,
        phase13_code_version_git_sha="1" * 40,
    ).create_qualification(
        PointInTimeQualificationCreateRequest(
            qualification_idempotency_key="phase13-phase14-contract-source-v1"
        )
    )
    return ResearchIngestionEligibilityWorkflow(
        qualification_source=source,
        store=_AssessmentMemory(),
        phase14_code_version_git_sha="2" * 40,
    ).create_assessment(
        ResearchIngestionEligibilityCreateRequest(
            assessment_idempotency_key="phase14-contract-proof-v1",
            qualification_id=qualification.qualification_id,
        )
    )


def test_closed_vocabulary_and_exact_registry_are_frozen() -> None:
    assert tuple(item.value for item in ResearchIngestionEligibilityOutcome) == (
        "MOCK_PROOF_COMPLETE",
        "BLOCKED",
    )
    assert tuple(item.value for item in ResearchIngestionEligibilityCheckStatus) == (
        "PASS",
        "BLOCKED",
        "UNCOMPUTABLE",
    )
    assert len(PHASE14_CHECK_ORDER) == 12
    assert PHASE14_POLICY_ID == "phase14-research-ingestion-eligibility-policy-v1"
    assert PHASE14_POLICY_SHA256 == (
        "6952c310bd84cdbcf7fe96dd3c3d58efa1161b6c3f76d52e0fc174a6328a3c1c"
    )
    assert ResearchIngestionEligibilityReasonCode.MOCK_NOT_APPLICABLE.value == (
        "mock_not_applicable"
    )


def test_create_request_is_strict_and_has_no_operator_owned_policy_input() -> None:
    qualification_id = UUID("00000000-0000-0000-0000-000000000013")
    request = ResearchIngestionEligibilityCreateRequest(
        assessment_idempotency_key="phase14-request-proof-v1",
        qualification_id=qualification_id,
    )

    assert set(request.model_dump()) == {"assessment_idempotency_key", "qualification_id"}
    with pytest.raises(ValidationError):
        ResearchIngestionEligibilityCreateRequest.model_validate(
            {
                **request.model_dump(),
                "provider": "forbidden",
            }
        )
    with pytest.raises(ValidationError):
        ResearchIngestionEligibilityCreateRequest.model_validate(
            {
                **request.model_dump(),
                "research_data_eligible": True,
            }
        )


def test_semantic_fingerprint_excludes_idempotency_key_but_binds_code_and_source() -> None:
    qualification_id = UUID("00000000-0000-0000-0000-000000000013")
    first = ResearchIngestionEligibilityCreateRequest(
        assessment_idempotency_key="phase14-first-key-v1",
        qualification_id=qualification_id,
    )
    second = ResearchIngestionEligibilityCreateRequest(
        assessment_idempotency_key="phase14-second-key-v1",
        qualification_id=qualification_id,
    )

    first_hash = research_ingestion_eligibility_request_fingerprint(
        request=first,
        code_version_git_sha="2" * 40,
    )
    assert first_hash == research_ingestion_eligibility_request_fingerprint(
        request=second,
        code_version_git_sha="2" * 40,
    )
    assert first_hash != research_ingestion_eligibility_request_fingerprint(
        request=first,
        code_version_git_sha="3" * 40,
    )


def test_complete_artifact_round_trips_and_binds_all_phase13_lineage() -> None:
    artifact = _artifact()

    assert (
        ResearchIngestionEligibilityArtifact.model_validate_json(artifact.model_dump_json())
        == artifact
    )
    assert artifact.qualification_capability_manifest_sha256s == tuple(
        item.source_capability_manifest_sha256 for item in artifact.payloads
    )
    assert len(artifact.qualification_capability_manifest_sha256s) == 6
    assert len(artifact.qualification_check_sha256s) == 12
    assert artifact.qualification_rights_attestation_id is None
    assert artifact.qualification_rights_attestation_sha256 is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("research_data_eligible", True),
        ("research_ingestion_authorized", True),
        ("strategy_promotion_authorized", True),
        ("paper_approval_granted", True),
        ("order_submission_authorized", True),
        ("live_path_absent", False),
        ("no_real_performance_claimed", False),
    ],
)
def test_authority_and_data_boundary_tamper_is_rejected(field: str, value: bool) -> None:
    artifact = _artifact().model_dump(mode="python")
    artifact[field] = value

    with pytest.raises(ValidationError):
        ResearchIngestionEligibilityArtifact.model_validate(artifact)


def test_payload_hash_and_registry_tamper_are_rejected() -> None:
    artifact = _artifact()
    tampered_payload = artifact.payloads[0].model_dump(mode="python")
    tampered_payload["record_count"] += 1

    with pytest.raises(ValidationError, match="payload hash"):
        type(artifact.payloads[0]).model_validate(tampered_payload)

    reordered = artifact.model_dump(mode="python")
    reordered["payloads"] = tuple(reversed(artifact.payloads))
    with pytest.raises(ValidationError):
        ResearchIngestionEligibilityArtifact.model_validate(reordered)


def test_rehashed_policy_check_tamper_cannot_relabel_complete_mock_as_blocked() -> None:
    artifact = _artifact().model_dump(mode="python")
    first_check = dict(artifact["checks"][0])
    first_check["status"] = ResearchIngestionEligibilityCheckStatus.BLOCKED
    first_check["reason_code"] = ResearchIngestionEligibilityReasonCode.SOURCE_KIND_NOT_ALLOWED
    first_check_preimage = {
        key: value for key, value in first_check.items() if key != "check_sha256"
    }
    first_check["check_sha256"] = domain_sha256(PHASE14_CHECK_HASH_DOMAIN, first_check_preimage)
    assert (
        first_check["code"]
        is ResearchIngestionEligibilityCheckCode.QUALIFICATION_IDENTITY_INTEGRITY
    )
    artifact["checks"] = (first_check, *artifact["checks"][1:])
    artifact["outcome"] = ResearchIngestionEligibilityOutcome.BLOCKED
    artifact_preimage = {key: value for key, value in artifact.items() if key != "artifact_sha256"}
    artifact["artifact_sha256"] = domain_sha256(PHASE14_ARTIFACT_HASH_DOMAIN, artifact_preimage)

    with pytest.raises(ValidationError, match="frozen policy"):
        ResearchIngestionEligibilityArtifact.model_validate(artifact)


@pytest.mark.parametrize(
    ("code", "field", "value"),
    (
        (
            ResearchIngestionEligibilityCheckCode.QUALIFICATION_IDENTITY_INTEGRITY,
            "observed_value",
            "forged-validity",
        ),
        (
            ResearchIngestionEligibilityCheckCode.QUALIFICATION_SOURCE_KIND_ALLOWED,
            "threshold_value",
            "forged-source-kind",
        ),
        (
            ResearchIngestionEligibilityCheckCode.INDEPENDENT_RIGHTS_REFERENCE_PRESENT_OR_MOCK,
            "evidence_sha256s",
            ("e" * 64,),
        ),
        (
            ResearchIngestionEligibilityCheckCode.LICENSED_PAYLOAD_ABSENT,
            "evidence_sha256s",
            ("f" * 64,),
        ),
    ),
)
def test_rehashed_check_scalar_and_evidence_tamper_is_rejected(
    code: ResearchIngestionEligibilityCheckCode,
    field: str,
    value: object,
) -> None:
    artifact = _artifact().model_dump(mode="python")
    checks = list(artifact["checks"])
    index = PHASE14_CHECK_ORDER.index(code)
    check = dict(checks[index])
    check[field] = value
    check_preimage = {key: item for key, item in check.items() if key != "check_sha256"}
    check["check_sha256"] = domain_sha256(PHASE14_CHECK_HASH_DOMAIN, check_preimage)
    checks[index] = check
    artifact["checks"] = tuple(checks)
    artifact_preimage = {key: item for key, item in artifact.items() if key != "artifact_sha256"}
    artifact["artifact_sha256"] = domain_sha256(PHASE14_ARTIFACT_HASH_DOMAIN, artifact_preimage)

    with pytest.raises(ValidationError, match="exact source evidence"):
        ResearchIngestionEligibilityArtifact.model_validate(artifact)


def test_all_boundary_fields_are_required_in_generated_schema() -> None:
    required = set(ResearchIngestionEligibilityArtifact.model_json_schema()["required"])
    assert {
        "external_request_performed",
        "provider_payload_persisted",
        "research_ingestion_authorized",
        "research_snapshot_created",
        "research_data_eligible",
        "research_run_created",
        "research_run_authorized",
        "research_executed",
        "performance_computed",
        "pass_research_granted",
        "strategy_promotion_authorized",
        "paper_approval_granted",
        "strategy_execution_eligible",
        "execution_authorized",
        "order_submission_authorized",
        "live_path_absent",
        "no_personalized_investment_advice",
        "no_real_performance_claimed",
    } <= required
