from __future__ import annotations

import json

import pytest
from fable5_data.phase25 import canonical as phase25_c
from fable5_data.phase25.contracts import EvaluationState
from fable5_data.phase27 import canonical as c
from fable5_data.phase27.contracts import (
    EvidenceCondition,
    Phase27EvidenceIntake,
    Phase27RightsEntitlementEvidencePackage,
    RequirementAnswerInput,
    RequirementEvaluation,
    SanitizedAuthorityEvidenceInput,
    SanitizedQuestionAnswerInput,
    SanitizedRightsResponseConditionInput,
    SanitizedRightsResponseIntake,
    SanitizedScopeAnswerInput,
    SECPolicyDocumentInput,
)
from fable5_data.phase27.package import build_phase27_package
from pydantic import ValidationError


def test_phase27_contract_is_closed_hash_bound_and_canonically_blocked() -> None:
    artifact = build_phase27_package()
    assert artifact.outcome.value == "BLOCKED"
    assert artifact.determination.value == "COMPOSITION_RIGHTS_ENTITLEMENT_EVIDENCE_MISSING"
    assert not artifact.verified_evidence_recorded
    assert not artifact.current_rights_evidence_for_exact_composition
    assert (
        len(artifact.crsp_requirement_evaluations),
        len(artifact.sec_requirement_evaluations),
    ) == (
        18,
        12,
    )
    assert artifact.rtdsm_phase25_binding.question_count == 10
    assert artifact.rtdsm_phase25_binding.scope_count == 19
    with pytest.raises(ValidationError):
        Phase27RightsEntitlementEvidencePackage.model_validate(
            {**artifact.model_dump(mode="json"), "unknown": True}
        )
    with pytest.raises(ValidationError):
        artifact.acquisition_authorized = True  # type: ignore[misc]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("acquisition_authorized", True),
        ("external_data_capture_authorized", True),
        ("research_ingestion_authorized", True),
        ("execution_authorized", True),
        ("order_submission_authorized", True),
        ("live_path_absent", False),
    ],
)
def test_phase27_contract_rejects_operational_authority_tampering(
    field: str, value: object
) -> None:
    payload = json.loads(build_phase27_package().model_dump_json())
    payload[field] = value
    with pytest.raises(ValidationError):
        Phase27RightsEntitlementEvidencePackage.model_validate(payload)


def test_phase27_intake_is_strict_and_requires_official_sec_https() -> None:
    intake = build_phase27_package().intake
    with pytest.raises(ValidationError):
        Phase27EvidenceIntake.model_validate({**intake.model_dump(mode="json"), "unknown": True})
    with pytest.raises(ValidationError):
        SECPolicyDocumentInput(
            evidence_id="SEC-POLICY-001",
            source_code="SEC_DEVELOPER_RESOURCES",
            source_url="https://sec.gov.evil.example/policy",
            official_title="SEC.gov | Developer Resources",
            publisher="U.S. Securities and Exchange Commission",
            publisher_stated_date="2025-03-10",
            retrieved_at_utc="2026-07-22T18:00:00Z",
            effective_at_utc="2026-07-01T00:00:00Z",
            revalidation_due_at_utc="2026-08-01T00:00:00Z",
            policy_version="SYNTHETIC_V1",
            clause_locator="FAIR_ACCESS_REQUEST_RATE_GUIDANCE",
            content_sha256="1" * 64,
            phase18_source_sha256="83513446683733fc70b93accbcdd9edac2be72f55ae5a01ba3d0688e6cd8b684",
            provenance_locator_sha256="2" * 64,
            normalized_finding="SYNTHETIC_CURRENT_POLICY_FINDING",
            normalized_delta="NO_MATERIAL_CHANGE_IDENTIFIED",
            independent_verification_status="VERIFIED",
            independent_verifier_identity_sha256="3" * 64,
        )


def test_phase27_empty_rtdsm_intake_reuses_exact_phase25_schema() -> None:
    empty = SanitizedRightsResponseIntake(
        schema_version=phase25_c.PHASE25_INTAKE_SCHEMA_VERSION,
        response_received=False,
    )
    artifact = build_phase27_package(
        build_phase27_package().intake.model_copy(update={"rtdsm": empty})
    )
    assert artifact.rtdsm_phase25_binding.determination == "RIGHTS_RESPONSE_EVIDENCE_MISSING"
    assert artifact.phase26_artifact_sha256 == c.PHASE26_ARTIFACT_SHA256


def test_phase27_rejects_rehashed_semantic_block_reason_tampering() -> None:
    artifact = build_phase27_package()
    payload = artifact.model_dump(mode="python")
    payload["block_reason"] = "Acquisition and live execution are authorized."
    unhashed = {
        key: value
        for key, value in payload.items()
        if key not in {"artifact_id", "artifact_sha256"}
    }
    replacement_hash = c.domain_sha256(c.ARTIFACT_DOMAIN, unhashed)
    payload["artifact_sha256"] = replacement_hash
    payload["artifact_id"] = c.uuid_from_sha256(c.ARTIFACT_NAMESPACE, replacement_hash)
    with pytest.raises(ValidationError, match="block reason"):
        Phase27RightsEntitlementEvidencePackage.model_validate(payload)


@pytest.mark.parametrize("product_index", [0, 1, 2])
def test_phase27_rejects_rehashed_product_requirement_manifest_tampering(
    product_index: int,
) -> None:
    payload = build_phase27_package().model_dump(mode="python")
    product = payload["product_evaluations"][product_index]
    product["requirements_manifest_sha256"] = "0" * 64
    product_unhashed = {
        key: value for key, value in product.items() if key != "product_evaluation_sha256"
    }
    product["product_evaluation_sha256"] = c.domain_sha256(c.PRODUCT_DOMAIN, product_unhashed)
    payload["product_evaluations_manifest_sha256"] = c.domain_sha256(
        c.PRODUCTS_MANIFEST_DOMAIN,
        tuple(row["product_evaluation_sha256"] for row in payload["product_evaluations"]),
    )
    artifact_unhashed = {
        key: value
        for key, value in payload.items()
        if key not in {"artifact_id", "artifact_sha256"}
    }
    replacement_hash = c.domain_sha256(c.ARTIFACT_DOMAIN, artifact_unhashed)
    payload["artifact_sha256"] = replacement_hash
    payload["artifact_id"] = c.uuid_from_sha256(c.ARTIFACT_NAMESPACE, replacement_hash)
    with pytest.raises(ValidationError, match="selected product aggregate mismatch"):
        Phase27RightsEntitlementEvidencePackage.model_validate(payload)


def test_phase27_normalized_finding_hash_is_bound_in_input_and_output() -> None:
    with pytest.raises(ValidationError, match="normalized finding hash"):
        RequirementAnswerInput(
            code="CRSP_EXECUTED_AGREEMENT",
            state=EvaluationState.PASS,
            normalized_finding="CONCISE_INDEPENDENTLY_VERIFIED_FINDING",
            normalized_value_sha256="0" * 64,
            evidence_ids=("CRSP-RIGHTS-001",),
        )

    row = build_phase27_package().crsp_requirement_evaluations[0]
    payload = row.model_dump(mode="python")
    payload["normalized_value_sha256"] = "0" * 64
    unhashed = {key: value for key, value in payload.items() if key != "evaluation_sha256"}
    payload["evaluation_sha256"] = c.domain_sha256(c.REQUIREMENT_DOMAIN, unhashed)
    with pytest.raises(ValidationError, match="normalized finding hash"):
        RequirementEvaluation.model_validate(payload)


def test_phase27_question_and_condition_inputs_expose_no_unbound_caller_hash() -> None:
    assert "normalized_value_sha256" not in SanitizedQuestionAnswerInput.model_fields
    assert "condition_sha256" not in SanitizedRightsResponseConditionInput.model_fields
    condition_payload = {
        "schema_version": c.CONDITION_SCHEMA,
        "condition_id": "CONDITION-001",
        "normalized_condition": "SYNTHETIC_ENFORCEABLE_CONDITION",
        "control_id": "CONTROL-001",
        "acceptance_test_id": "ACCEPTANCE-TEST-001",
        "enforceable": True,
        "acceptance_test_passed": True,
        "condition_sha256": "0" * 64,
    }
    with pytest.raises(ValidationError, match="condition hash mismatch"):
        EvidenceCondition.model_validate(condition_payload)


def test_phase27_private_authority_requires_hashes_codes_and_matching_basis() -> None:
    valid = {
        "responder_organization": "SYNTHETIC_RIGHTS_HOLDER",
        "responder_stable_identity": "1" * 64,
        "responder_role": "AUTHORIZED_LICENSING_OFFICER",
        "authority_basis": "EXECUTED_AGREEMENT_AUTHORITY_BASIS",
        "rights_holding_legal_entity": "SYNTHETIC_RIGHTS_HOLDER_LLC",
        "response_date_utc": "2026-07-22T18:00:00Z",
        "effective_date_utc": "2026-07-01T00:00:00Z",
        "expiry_date_utc": "2026-08-01T00:00:00Z",
        "governing_agreement": "2" * 64,
        "governing_terms_version": "SYNTHETIC_V1",
        "immutable_evidence_id": "CRSP-RIGHTS-001",
        "immutable_evidence_sha256": "3" * 64,
        "authenticated_provenance": "EXECUTED_AGREEMENT",
        "provenance_locator_sha256": "4" * 64,
        "independent_verification_status": "VERIFIED",
        "independent_verifier_identity_sha256": "5" * 64,
        "responder_identity_authenticated": True,
        "authority_basis_verified": True,
    }
    SanitizedAuthorityEvidenceInput.model_validate(valid)
    for field, unsafe in (
        ("responder_stable_identity", "alice@example.com"),
        ("governing_agreement", "BEGIN RAW AGREEMENT TEXT"),
        ("responder_role", "Authorized licensing officer"),
        ("responder_organization", "PKABCDEFGHIJKLMNOPQRSTUVWXYZ123456"),
        ("immutable_evidence_id", "AKIAIOSFODNN7EXAMPLE"),
    ):
        with pytest.raises(ValidationError):
            SanitizedAuthorityEvidenceInput.model_validate({**valid, field: unsafe})
    with pytest.raises(ValidationError, match="does not match authenticated provenance"):
        SanitizedAuthorityEvidenceInput.model_validate(
            {**valid, "authority_basis": "RIGHTS_HOLDER_RECORD_AUTHORITY_BASIS"}
        )


@pytest.mark.parametrize(
    ("field", "unsafe"),
    [
        ("normalized_finding", "First line\nraw page body"),
        ("normalized_delta", "<html><body>remote document</body></html>"),
        ("clause_locator", '{"raw_response":"remote body"}'),
        ("normalized_finding", "Contact alice@example.com for the response."),
        ("normalized_finding", "Bearer DO_NOT_PERSIST_THIS_SECRET"),
    ],
)
def test_phase27_sec_metadata_accepts_concise_summaries_and_rejects_body_like_content(
    field: str, unsafe: str
) -> None:
    row = c.SEC_ACCEPTED_SOURCE_ROWS[3]
    valid = {
        "evidence_id": "SEC-POLICY-001",
        "source_code": row[0],
        "source_url": row[3],
        "official_title": row[1],
        "publisher": row[2],
        "publisher_stated_date": "2025-03-10",
        "retrieved_at_utc": "2026-07-22T18:00:00Z",
        "effective_at_utc": "2026-07-01T00:00:00Z",
        "revalidation_due_at_utc": "2026-08-01T00:00:00Z",
        "policy_version": "SYNTHETIC_V1",
        "clause_locator": "FAIR_ACCESS_REQUEST_RATE_GUIDANCE",
        "content_sha256": "1" * 64,
        "phase18_source_sha256": row[4],
        "provenance_locator_sha256": "2" * 64,
        "normalized_finding": "CURRENT_POLICY_INDEPENDENTLY_REVIEWED",
        "normalized_delta": "NO_MATERIAL_CHANGE_IDENTIFIED",
        "independent_verification_status": "VERIFIED",
        "independent_verifier_identity_sha256": "3" * 64,
    }
    SECPolicyDocumentInput.model_validate(valid)
    with pytest.raises(ValidationError):
        SECPolicyDocumentInput.model_validate({**valid, field: unsafe})


def test_phase27_sec_publisher_date_and_policy_version_are_strict_tokens() -> None:
    row = c.SEC_ACCEPTED_SOURCE_ROWS[3]
    valid = {
        "evidence_id": "SEC-POLICY-001",
        "source_code": row[0],
        "source_url": row[3],
        "official_title": row[1],
        "publisher": row[2],
        "publisher_stated_date": "2025-03-10",
        "retrieved_at_utc": "2026-07-22T18:00:00Z",
        "effective_at_utc": "2026-07-01T00:00:00Z",
        "revalidation_due_at_utc": "2026-08-01T00:00:00Z",
        "policy_version": "POLICY_V1",
        "clause_locator": "FAIR_ACCESS_REQUEST_RATE_GUIDANCE",
        "content_sha256": "1" * 64,
        "phase18_source_sha256": row[4],
        "provenance_locator_sha256": "2" * 64,
        "normalized_finding": "CURRENT_POLICY_INDEPENDENTLY_REVIEWED",
        "normalized_delta": "NO_MATERIAL_CHANGE_IDENTIFIED",
        "independent_verification_status": "VERIFIED",
        "independent_verifier_identity_sha256": "3" * 64,
    }
    for policy_version in ("POLICY_V1", "a" * 64):
        document = SECPolicyDocumentInput.model_validate(
            {**valid, "policy_version": policy_version}
        )
        assert document.publisher_stated_date.isoformat() == "2025-03-10"
        assert document.policy_version == policy_version
    for field, unsafe in (
        ("publisher_stated_date", "123-45-6789"),
        ("publisher_stated_date", "2025-02-30"),
        ("publisher_stated_date", "2099-12-31"),
        ("policy_version", "212-555-0199"),
        ("policy_version", "PKABCDEFGHIJKLMNOPQRSTUVWXYZ123456"),
    ):
        with pytest.raises(ValidationError):
            SECPolicyDocumentInput.model_validate({**valid, field: unsafe})


@pytest.mark.parametrize(
    "unsafe",
    [
        "alice@example.com",
        "123-45-6789",
        "+1 (212) 555-0199",
        "Response body from provider",
        "First line\nraw response body",
        '{"provider_payload":"raw document"}',
        "Bearer DO_NOT_PERSIST_THIS_SECRET",
        "PKABCDEFGHIJKLMNOPQRSTUVWXYZ123456",
    ],
)
def test_phase27_all_operator_descriptive_fields_reject_unsafe_text(unsafe: str) -> None:
    finding_hash = c.domain_sha256(c.NORMALIZED_VALUE_DOMAIN, unsafe)
    with pytest.raises(ValidationError):
        RequirementAnswerInput(
            code="CRSP_EXECUTED_AGREEMENT",
            state=EvaluationState.MISSING,
            normalized_finding=unsafe,
            normalized_value_sha256=finding_hash,
        )
    evaluation = build_phase27_package().crsp_requirement_evaluations[0]
    evaluation_payload = evaluation.model_dump(mode="python")
    evaluation_payload["normalized_finding"] = unsafe
    evaluation_payload["normalized_value_sha256"] = finding_hash
    unhashed_evaluation = {
        key: value for key, value in evaluation_payload.items() if key != "evaluation_sha256"
    }
    evaluation_payload["evaluation_sha256"] = c.domain_sha256(
        c.REQUIREMENT_DOMAIN, unhashed_evaluation
    )
    with pytest.raises(ValidationError):
        RequirementEvaluation.model_validate(evaluation_payload)
    with pytest.raises(ValidationError):
        SanitizedQuestionAnswerInput(
            code="PERSISTENT_STORAGE",
            state=EvaluationState.MISSING,
            normalized_finding=unsafe,
        )
    with pytest.raises(ValidationError):
        SanitizedScopeAnswerInput(
            code="ENVIRONMENTS",
            state=EvaluationState.MISSING,
            normalized_determination=unsafe,
            normalized_value_sha256="0" * 64,
        )
    with pytest.raises(ValidationError):
        SanitizedRightsResponseConditionInput(
            condition_id="CONDITION-001",
            normalized_condition=unsafe,
        )
    condition_payload = {
        "schema_version": c.CONDITION_SCHEMA,
        "condition_id": "CONDITION-001",
        "normalized_condition": unsafe,
        "control_id": None,
        "acceptance_test_id": None,
        "enforceable": False,
        "acceptance_test_passed": False,
    }
    with pytest.raises(ValidationError):
        EvidenceCondition.model_validate(
            {
                **condition_payload,
                "condition_sha256": c.domain_sha256(c.CONDITION_DOMAIN, condition_payload),
            }
        )


@pytest.mark.parametrize("field", ["official_title", "publisher"])
def test_phase27_sec_title_and_publisher_share_the_sanitized_summary_boundary(field: str) -> None:
    row = c.SEC_ACCEPTED_SOURCE_ROWS[3]
    payload = {
        "evidence_id": "SEC-POLICY-001",
        "source_code": row[0],
        "source_url": row[3],
        "official_title": row[1],
        "publisher": row[2],
        "publisher_stated_date": "2025-03-10",
        "retrieved_at_utc": "2026-07-22T18:00:00Z",
        "effective_at_utc": "2026-07-01T00:00:00Z",
        "revalidation_due_at_utc": "2026-08-01T00:00:00Z",
        "policy_version": "SYNTHETIC_V1",
        "clause_locator": "FAIR_ACCESS_REQUEST_RATE_GUIDANCE",
        "content_sha256": "1" * 64,
        "phase18_source_sha256": row[4],
        "provenance_locator_sha256": "2" * 64,
        "normalized_finding": "CURRENT_POLICY_INDEPENDENTLY_REVIEWED",
        "normalized_delta": "NO_MATERIAL_CHANGE_IDENTIFIED",
        "independent_verification_status": "VERIFIED",
        "independent_verifier_identity_sha256": "3" * 64,
    }
    with pytest.raises(ValidationError, match="drifted from accepted Phase 18 source binding"):
        SECPolicyDocumentInput.model_validate({**payload, field: "alice@example.com"})


def test_phase27_rtdsm_account_scope_requires_a_distinct_hash_only_identity() -> None:
    label = "SANITIZED_HASH_ONLY"
    label_hash = phase25_c.domain_sha256(phase25_c.PHASE25_NORMALIZED_VALUE_HASH_DOMAIN, label)
    payload = {
        "code": "ACCOUNT_OR_ENTITLEMENT",
        "state": EvaluationState.PASS,
        "normalized_determination": label,
        "normalized_value_sha256": label_hash,
        "evidence_ids": ("RTDSM-RIGHTS-001",),
    }
    with pytest.raises(ValidationError, match="distinct hash-only identity"):
        SanitizedScopeAnswerInput.model_validate(payload)
    accepted = SanitizedScopeAnswerInput.model_validate(
        {**payload, "normalized_value_sha256": "f" * 64}
    )
    assert accepted.normalized_determination == label
    assert accepted.normalized_value_sha256 != label_hash


def test_phase27_product_state_is_exactly_derived_even_after_rehashing() -> None:
    payload = build_phase27_package().model_dump(mode="python")
    product = payload["product_evaluations"][0]
    product["state"] = "BLOCKED"
    product["product_evaluation_sha256"] = c.domain_sha256(
        c.PRODUCT_DOMAIN,
        {key: value for key, value in product.items() if key != "product_evaluation_sha256"},
    )
    payload["product_evaluations_manifest_sha256"] = c.domain_sha256(
        c.PRODUCTS_MANIFEST_DOMAIN,
        tuple(row["product_evaluation_sha256"] for row in payload["product_evaluations"]),
    )
    unhashed = {
        key: value
        for key, value in payload.items()
        if key not in {"artifact_id", "artifact_sha256"}
    }
    replacement_hash = c.domain_sha256(c.ARTIFACT_DOMAIN, unhashed)
    payload["artifact_sha256"] = replacement_hash
    payload["artifact_id"] = c.uuid_from_sha256(c.ARTIFACT_NAMESPACE, replacement_hash)
    with pytest.raises(ValidationError, match="selected product evidence state mismatch"):
        Phase27RightsEntitlementEvidencePackage.model_validate(payload)


@pytest.mark.parametrize(
    "field",
    [
        "credential",
        "provider_fetch_url",
        "raw_provider_body",
        "raw_agreement",
        "personal_identifier",
        "entitlement_token",
        "data_file",
        "schema_sample",
        "research_output",
        "candidate_screen_output",
        "strategy_output",
        "performance_result",
        "risk_promotion",
        "order_submission",
        "execution",
        "cancellation",
        "liquidation",
        "live_path",
    ],
)
def test_phase27_intake_rejects_every_literal_prohibited_capability_field(field: str) -> None:
    payload = build_phase27_package().intake.model_dump(mode="json")
    payload[field] = "PROHIBITED"
    with pytest.raises(ValidationError):
        Phase27EvidenceIntake.model_validate(payload)
