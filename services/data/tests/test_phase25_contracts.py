from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from fable5_data.phase25 import canonical as c
from fable5_data.phase25.contracts import (
    AuthorityEvidenceInput,
    EvaluationState,
    Phase25Package,
    ProvenanceType,
    QuestionAnswerInput,
    RightsResponseConditionInput,
    RightsResponseIntake,
    ScopeAnswerInput,
    ScopeCode,
    VerificationStatus,
)
from fable5_data.phase25.package import build_phase25_package
from pydantic import ValidationError

EVIDENCE_ID = "RTDSM-RIGHTS-2026-07"


def _authority(**overrides: object) -> AuthorityEvidenceInput:
    payload: dict[str, object] = {
        "responder_organization": "Synthetic Rights Holder",
        "responder_stable_identity": "synthetic-responder-01",
        "responder_role": "Authorized licensing officer",
        "authority_basis": "Synthetic executed delegation covering the exact RTDSM scope.",
        "rights_holding_legal_entity": "Synthetic Rights Holder LLC",
        "response_date_utc": datetime(2026, 7, 21, 14, 0, tzinfo=UTC),
        "effective_date_utc": datetime(2026, 7, 21, 0, 0, tzinfo=UTC),
        "expiry_date_utc": None,
        "expiry_not_applicable_reason": "Synthetic perpetual test record.",
        "governing_agreement": "Synthetic RTDSM Rights Agreement",
        "governing_terms_version": "synthetic-v1",
        "immutable_evidence_id": EVIDENCE_ID,
        "immutable_evidence_sha256": "1" * 64,
        "authenticated_provenance": ProvenanceType.RIGHTS_HOLDER_RECORD,
        "provenance_locator_sha256": "2" * 64,
        "independent_verification_status": VerificationStatus.VERIFIED,
        "independent_verifier_identity_sha256": "3" * 64,
        "responder_identity_authenticated": True,
        "authority_basis_verified": True,
    }
    payload.update(overrides)
    return AuthorityEvidenceInput.model_validate(payload)


def _positive_intake(
    *,
    authority: AuthorityEvidenceInput | None = None,
    conditional_question: bool = False,
    condition_satisfied: bool = True,
    omit_scope: ScopeCode | None = None,
    consistency_status: VerificationStatus = VerificationStatus.VERIFIED,
) -> RightsResponseIntake:
    questions = []
    for code, _field, _question in c.PHASE25_QUESTION_ROWS:
        conditions = ()
        state = EvaluationState.PASS
        if conditional_question and not questions:
            state = EvaluationState.CONDITIONAL
            conditions = (
                RightsResponseConditionInput(
                    condition_id="COND-001",
                    normalized_condition="Synthetic access ceiling must be enforced.",
                    control_id="CONTROL-001" if condition_satisfied else None,
                    acceptance_test_id="TEST-001" if condition_satisfied else None,
                    enforceable=condition_satisfied,
                    acceptance_test_passed=condition_satisfied,
                ),
            )
        questions.append(
            QuestionAnswerInput(
                code=code,
                state=state,
                normalized_finding="Synthetic exact-scope evidence permits this use.",
                evidence_ids=(EVIDENCE_ID,),
                conditions=conditions,
            )
        )
    scope = []
    for code_value, _requirement in c.PHASE25_SCOPE_ROWS:
        code = ScopeCode(code_value)
        if code is omit_scope:
            continue
        determination = "SYNTHETIC_EXACT_SCOPE"
        if code is ScopeCode.PRODUCT:
            determination = c.PHASE25_PRODUCT_NAME
        elif code is ScopeCode.LICENSED_PARTY:
            determination = "INDIVIDUAL_ACCOUNT_HOLDER"
        elif code is ScopeCode.ACCOUNT_OR_ENTITLEMENT:
            determination = "SANITIZED_HASH_ONLY"
        scope.append(
            ScopeAnswerInput(
                code=code,
                state=EvaluationState.PASS,
                normalized_determination=determination,
                normalized_value_sha256=c.domain_sha256(
                    c.PHASE25_NORMALIZED_VALUE_HASH_DOMAIN, determination
                ),
                evidence_ids=(EVIDENCE_ID,),
            )
        )
    return RightsResponseIntake(
        schema_version=c.PHASE25_INTAKE_SCHEMA_VERSION,
        response_received=True,
        authority_evidence=(authority or _authority(),),
        question_answers=tuple(questions),
        scope_answers=tuple(scope),
        mutual_consistency_status=consistency_status,
        mutual_consistency_evidence_ids=(EVIDENCE_ID,),
    )


def test_phase25_contract_is_closed_frozen_hash_bound_and_canonical_blocked() -> None:
    artifact = build_phase25_package()
    assert artifact.outcome.value == "BLOCKED"
    assert artifact.determination.value == "RIGHTS_RESPONSE_EVIDENCE_MISSING"
    assert (len(artifact.question_evaluations), len(artifact.scope_evaluations)) == (10, 19)
    assert (len(artifact.source_evidence), len(artifact.adapter_patterns)) == (10, 11)
    assert all(row.state is EvaluationState.MISSING for row in artifact.question_evaluations)
    assert all(row.state is EvaluationState.MISSING for row in artifact.scope_evaluations)
    with pytest.raises(ValidationError):
        Phase25Package.model_validate({**artifact.model_dump(mode="json"), "unknown": True})
    with pytest.raises(ValidationError):
        artifact.rights_verified = True  # type: ignore[misc]


def test_phase25_complete_independently_verified_synthetic_scope_can_only_pass_response() -> None:
    artifact = build_phase25_package(_positive_intake())
    assert artifact.outcome.value == "PASS"
    assert artifact.rights_verified
    assert artifact.determination.value.endswith("REQUIRES_SEPARATE_ACQUISITION_AUTHORITY")
    assert not artifact.production_adapter_activated
    assert not artifact.operational_provider_selected
    assert not artifact.execution_authorized


def test_phase25_missing_scope_and_unenforced_condition_fail_closed() -> None:
    missing = build_phase25_package(_positive_intake(omit_scope=ScopeCode.ATTRIBUTION))
    assert missing.outcome.value == "BLOCKED" and not missing.rights_verified
    conditional = build_phase25_package(
        _positive_intake(conditional_question=True, condition_satisfied=False)
    )
    assert conditional.outcome.value == "BLOCKED" and not conditional.rights_verified
    first = conditional.question_evaluations[0]
    assert first.state is EvaluationState.CONDITIONAL and not first.satisfied


def test_phase25_unverified_or_failed_mutual_consistency_fails_closed() -> None:
    artifact = build_phase25_package(_positive_intake(consistency_status=VerificationStatus.FAILED))
    assert artifact.outcome.value == "BLOCKED" and not artifact.rights_verified
    assert not artifact.mutual_consistency_verified


def test_phase25_enforceable_tested_condition_can_satisfy_only_its_field() -> None:
    artifact = build_phase25_package(
        _positive_intake(conditional_question=True, condition_satisfied=True)
    )
    assert artifact.outcome.value == "PASS"
    assert artifact.question_evaluations[0].state is EvaluationState.CONDITIONAL
    assert artifact.question_evaluations[0].satisfied


def test_phase25_email_only_or_missing_authority_never_verifies() -> None:
    email_only = _authority(authenticated_provenance=ProvenanceType.EMAIL_ONLY)
    artifact = build_phase25_package(_positive_intake(authority=email_only))
    assert artifact.outcome.value == "BLOCKED" and not artifact.rights_verified
    assert not artifact.authority_evidence[0].authority_verified
    assert all(row.state is EvaluationState.MISSING for row in artifact.question_evaluations)


def test_phase25_account_identifier_and_tampering_are_rejected() -> None:
    with pytest.raises(ValidationError):
        ScopeAnswerInput(
            code=ScopeCode.ACCOUNT_OR_ENTITLEMENT,
            state=EvaluationState.PASS,
            normalized_determination="account-12345",
            normalized_value_sha256="4" * 64,
            evidence_ids=(EVIDENCE_ID,),
        )
    payload = json.loads(build_phase25_package().model_dump_json())
    payload["question_evaluations"][0]["state"] = "PASS"
    with pytest.raises(ValidationError):
        Phase25Package.model_validate(payload)
