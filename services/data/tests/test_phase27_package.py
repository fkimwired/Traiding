from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from fable5_data.phase25 import canonical as phase25_c
from fable5_data.phase25.contracts import (
    EvaluationState,
    ProvenanceType,
    ScopeCode,
    VerificationStatus,
)
from fable5_data.phase27 import canonical as c
from fable5_data.phase27.contracts import (
    CRSPRightsEntitlementIntake,
    Phase27EvidenceIntake,
    Phase27RightsEntitlementEvidencePackage,
    RequirementAnswerInput,
    SanitizedAuthorityEvidenceInput,
    SanitizedQuestionAnswerInput,
    SanitizedRightsResponseIntake,
    SanitizedScopeAnswerInput,
    SECPolicyDocumentInput,
    SECPolicyRevalidationIntake,
)
from fable5_data.phase27.package import (
    build_phase27_package,
    canonical_phase27_package_bytes,
)
from pydantic import ValidationError

EVALUATED = datetime(2026, 7, 22, 19, 35, tzinfo=UTC)


def _authority(evidence_id: str, provenance: ProvenanceType) -> SanitizedAuthorityEvidenceInput:
    return SanitizedAuthorityEvidenceInput(
        responder_organization="SYNTHETIC_RIGHTS_HOLDER",
        responder_stable_identity="4" * 64,
        responder_role="AUTHORIZED_LICENSING_OFFICER",
        authority_basis=f"{provenance.value}{c.PRIVATE_AUTHORITY_BASIS_SUFFIX}",
        rights_holding_legal_entity="SYNTHETIC_RIGHTS_HOLDER_LLC",
        response_date_utc=datetime(2026, 7, 22, 18, 0, tzinfo=UTC),
        effective_date_utc=datetime(2026, 7, 1, 0, 0, tzinfo=UTC),
        expiry_date_utc=datetime(2026, 8, 1, 0, 0, tzinfo=UTC),
        governing_agreement="5" * 64,
        governing_terms_version="SYNTHETIC_V1",
        immutable_evidence_id=evidence_id,
        immutable_evidence_sha256="1" * 64,
        authenticated_provenance=provenance,
        provenance_locator_sha256="2" * 64,
        independent_verification_status=VerificationStatus.VERIFIED,
        independent_verifier_identity_sha256="3" * 64,
        responder_identity_authenticated=True,
        authority_basis_verified=True,
    )


def _answer(code: str, evidence_id: str | tuple[str, ...]) -> RequirementAnswerInput:
    finding = f"SYNTHETIC_VERIFIED_{code}"
    evidence_ids = (evidence_id,) if isinstance(evidence_id, str) else evidence_id
    return RequirementAnswerInput(
        code=code,
        state=EvaluationState.PASS,
        normalized_finding=finding,
        normalized_value_sha256=c.domain_sha256(c.NORMALIZED_VALUE_DOMAIN, finding),
        evidence_ids=evidence_ids,
    )


def _rtdsm_intake(
    *,
    requested_series: str = c.RTDSM_REQUESTED_SERIES,
    pcpi_bls_origin: str = c.RTDSM_PCPI_BLS_ORIGIN,
    delivery: str = c.DELIVERY_IDS[3],
) -> SanitizedRightsResponseIntake:
    evidence_id = "RTDSM-RIGHTS-001"
    questions = tuple(
        SanitizedQuestionAnswerInput(
            code=code,
            state=EvaluationState.PASS,
            normalized_finding="SYNTHETIC_VERIFIED_EXACT_SCOPE_FINDING",
            evidence_ids=(evidence_id,),
        )
        for code, _field, _question in phase25_c.PHASE25_QUESTION_ROWS
    )
    scopes = []
    for code_value, _requirement in phase25_c.PHASE25_SCOPE_ROWS:
        code = ScopeCode(code_value)
        determination = "SYNTHETIC_EXACT_SCOPE"
        if code is ScopeCode.PRODUCT:
            determination = c.RTDSM_PRODUCT
        elif code is ScopeCode.LICENSED_PARTY:
            determination = "INDIVIDUAL_ACCOUNT_HOLDER"
        elif code is ScopeCode.ACCOUNT_OR_ENTITLEMENT:
            determination = "SANITIZED_HASH_ONLY"
        elif code is ScopeCode.REQUESTED_SERIES:
            determination = requested_series
        elif code is ScopeCode.PCPI_AND_BLS_ORIGIN:
            determination = pcpi_bls_origin
        elif code is ScopeCode.DELIVERY_METHOD_AND_SURFACE:
            determination = delivery
        scopes.append(
            SanitizedScopeAnswerInput(
                code=code,
                state=EvaluationState.PASS,
                normalized_determination=determination,
                normalized_value_sha256=(
                    "f" * 64
                    if code is ScopeCode.ACCOUNT_OR_ENTITLEMENT
                    else phase25_c.domain_sha256(
                        phase25_c.PHASE25_NORMALIZED_VALUE_HASH_DOMAIN, determination
                    )
                ),
                evidence_ids=(evidence_id,),
            )
        )
    return SanitizedRightsResponseIntake(
        schema_version=phase25_c.PHASE25_INTAKE_SCHEMA_VERSION,
        response_received=True,
        authority_evidence=(_authority(evidence_id, ProvenanceType.RIGHTS_HOLDER_RECORD),),
        question_answers=questions,
        scope_answers=tuple(scopes),
        mutual_consistency_status=VerificationStatus.VERIFIED,
        mutual_consistency_evidence_ids=(evidence_id,),
    )


def _complete_intake(
    crsp_provenance: ProvenanceType = ProvenanceType.EXECUTED_AGREEMENT,
) -> Phase27EvidenceIntake:
    crsp_id = "CRSP-RIGHTS-001"
    sec_id = "SEC-POLICY-001"
    return Phase27EvidenceIntake(
        schema_version=c.INTAKE_SCHEMA,
        evaluated_at_utc=EVALUATED,
        recorded_at_utc=EVALUATED,
        crsp=CRSPRightsEntitlementIntake(
            schema_version=c.CRSP_INTAKE_SCHEMA,
            response_received=True,
            licensed_party_identity_sha256="7" * 64,
            executed_agreement_sha256="8" * 64,
            order_form_or_product_schedule_sha256="9" * 64,
            product_code=c.CRSP_PRODUCT,
            product_sku_sha256="a" * 64,
            delivery_id=c.DELIVERY_IDS[0],
            selected_capability_codes=c.CRSP_CAPABILITY_CODES,
            third_party_rights_evidence_ids=(crsp_id,),
            authority_evidence=(_authority(crsp_id, crsp_provenance),),
            requirement_answers=tuple(
                _answer(code, crsp_id) for code, _requirement in c.CRSP_REQUIREMENT_ROWS
            ),
            mutual_consistency_status=VerificationStatus.VERIFIED,
            mutual_consistency_evidence_ids=(crsp_id,),
        ),
        rtdsm=_rtdsm_intake(),
        sec=SECPolicyRevalidationIntake(
            schema_version=c.SEC_INTAKE_SCHEMA,
            review_performed=True,
            policy_documents=tuple(
                SECPolicyDocumentInput(
                    evidence_id=f"SEC-POLICY-{ordinal:03d}",
                    source_code=row[0],
                    source_url=row[3],
                    official_title=row[1],
                    publisher=row[2],
                    publisher_stated_date="2025-03-10",
                    retrieved_at_utc=datetime(2026, 7, 22, 18, 0, tzinfo=UTC),
                    effective_at_utc=datetime(2026, 7, 1, 0, 0, tzinfo=UTC),
                    revalidation_due_at_utc=datetime(2026, 8, 1, 0, 0, tzinfo=UTC),
                    policy_version="SYNTHETIC_V1",
                    clause_locator=f"SYNTHETIC_CLAUSE_LOCATOR_{ordinal}",
                    content_sha256=f"{ordinal + 3:x}" * 64,
                    phase18_source_sha256=row[4],
                    provenance_locator_sha256=f"{ordinal + 8:x}" * 64,
                    normalized_finding="SYNTHETIC_CURRENT_POLICY_FINDING",
                    normalized_delta="NO_MATERIAL_CHANGE_IDENTIFIED",
                    independent_verification_status=VerificationStatus.VERIFIED,
                    independent_verifier_identity_sha256="e" * 64,
                )
                for ordinal, row in enumerate(c.SEC_ACCEPTED_SOURCE_ROWS, 1)
            ),
            requirement_answers=tuple(
                _answer(
                    code,
                    tuple(f"SEC-POLICY-{ordinal:03d}" for ordinal in range(1, 6)),
                )
                for code, _requirement in c.SEC_REQUIREMENT_ROWS
            ),
            mutual_consistency_status=VerificationStatus.VERIFIED,
            mutual_consistency_evidence_ids=tuple(
                f"SEC-POLICY-{ordinal:03d}" for ordinal in range(1, 6)
            ),
        ),
        composition_consistency_status=VerificationStatus.VERIFIED,
        composition_consistency_evidence_ids=(crsp_id, "RTDSM-RIGHTS-001", sec_id),
    )


def _rehash_evidence_bundle_and_artifact(payload: dict[str, object]) -> None:
    evidence_payload = {
        "intake": payload["intake"],
        "authority_manifest_sha256": payload["authority_manifest_sha256"],
        "crsp_requirements_manifest_sha256": payload["crsp_requirements_manifest_sha256"],
        "rtdsm_binding_sha256": payload["rtdsm_phase25_binding"]["binding_sha256"],  # type: ignore[index]
        "sec_policy_documents_manifest_sha256": payload["sec_policy_documents_manifest_sha256"],
        "sec_requirements_manifest_sha256": payload["sec_requirements_manifest_sha256"],
    }
    bundle_hash = c.domain_sha256(c.EVIDENCE_BUNDLE_DOMAIN, evidence_payload)
    payload["evidence_bundle_sha256"] = bundle_hash
    payload["evidence_bundle_id"] = c.uuid_from_sha256(c.EVIDENCE_BUNDLE_NAMESPACE, bundle_hash)
    artifact_payload = {
        key: value
        for key, value in payload.items()
        if key not in {"artifact_id", "artifact_sha256"}
    }
    artifact_hash = c.domain_sha256(c.ARTIFACT_DOMAIN, artifact_payload)
    payload["artifact_sha256"] = artifact_hash
    payload["artifact_id"] = c.uuid_from_sha256(c.ARTIFACT_NAMESPACE, artifact_hash)


def test_phase27_default_builder_is_deterministic_canonical_and_missing() -> None:
    first = canonical_phase27_package_bytes()
    assert first == canonical_phase27_package_bytes()
    assert first.endswith(b"\n") and b"\r" not in first
    assert (
        json.dumps(json.loads(first), sort_keys=True, separators=(",", ":")).encode() + b"\n"
        == first
    )
    artifact = build_phase27_package()
    assert artifact.outcome.value == "BLOCKED"
    assert artifact.determination.value == "COMPOSITION_RIGHTS_ENTITLEMENT_EVIDENCE_MISSING"
    assert [row.state.value for row in artifact.product_evaluations] == [
        "MISSING",
        "MISSING",
        "MISSING",
    ]


def test_phase27_complete_synthetic_evidence_records_only_nonoperational_verification() -> None:
    artifact = build_phase27_package(_complete_intake())
    assert artifact.verified_evidence_recorded
    assert artifact.current_rights_evidence_for_exact_composition
    assert artifact.determination.value == (
        "VERIFIED_EVIDENCE_RECORDED_REQUIRES_SEPARATE_ACQUISITION_AUTHORITY"
    )
    assert artifact.outcome.value == "BLOCKED"
    assert all(
        row.state.value == "VERIFIED_EVIDENCE_RECORDED" for row in artifact.product_evaluations
    )
    for field in (
        "acquisition_authorized",
        "external_data_capture_authorized",
        "research_ingestion_authorized",
        "execution_authorized",
        "order_submission_authorized",
    ):
        assert getattr(artifact, field) is False
    rendered = artifact.model_dump_json()
    assert "@" not in rendered
    assert "Synthetic rights agreement" not in rendered
    for row in (*artifact.authority_evidence, *artifact.intake.rtdsm.authority_evidence):
        assert len(row.responder_stable_identity) == 64
        assert len(row.governing_agreement) == 64
        assert " " not in row.responder_role


def test_phase27_weak_public_provenance_never_verifies_private_authority() -> None:
    artifact = build_phase27_package(_complete_intake(ProvenanceType.PUBLIC_WEBPAGE_ONLY))
    crsp = artifact.product_evaluations[0]
    assert crsp.state.value == "BLOCKED"
    assert not crsp.independently_verified
    assert not artifact.verified_evidence_recorded
    assert artifact.determination.value == "COMPOSITION_RIGHTS_ENTITLEMENT_EVIDENCE_BLOCKED"
    assert all(
        row.state is EvaluationState.MISSING for row in artifact.crsp_requirement_evaluations
    )


def test_phase27_crsp_missing_explicit_third_party_binding_remains_blocked() -> None:
    base = _complete_intake()
    crsp = base.crsp.model_copy(update={"third_party_rights_evidence_ids": ()})
    artifact = build_phase27_package(base.model_copy(update={"crsp": crsp}))
    assert artifact.product_evaluations[0].state.value == "BLOCKED"
    assert not artifact.verified_evidence_recorded


def test_phase27_sec_requires_all_five_accepted_phase18_sources() -> None:
    base = _complete_intake()
    sec = base.sec.model_copy(update={"policy_documents": base.sec.policy_documents[:-1]})
    artifact = build_phase27_package(base.model_copy(update={"sec": sec}))
    assert artifact.product_evaluations[1].state.value == "BLOCKED"
    assert not artifact.verified_evidence_recorded


def test_phase27_sec_document_rejects_phase18_source_binding_drift() -> None:
    source = _complete_intake().sec.policy_documents[0]
    payload = source.model_dump(mode="python")
    payload["phase18_source_sha256"] = "0" * 64
    with pytest.raises(ValidationError):
        SECPolicyDocumentInput.model_validate(payload)


def test_phase27_mislabeled_rtdsm_selected_scope_remains_blocked() -> None:
    base = _complete_intake()
    for rtdsm in (
        _rtdsm_intake(requested_series="GDP"),
        _rtdsm_intake(pcpi_bls_origin="BLS_ORIGIN_UNRESOLVED"),
        _rtdsm_intake(delivery="GENERIC_RTDSM_DOWNLOAD"),
    ):
        artifact = build_phase27_package(base.model_copy(update={"rtdsm": rtdsm}))
        assert not artifact.rtdsm_phase25_binding.selected_scope_bound
        assert not artifact.rtdsm_phase25_binding.rights_verified
        assert artifact.product_evaluations[2].state.value == "BLOCKED"
        assert not artifact.verified_evidence_recorded


def test_phase27_rtdsm_scope_hash_mismatch_cannot_produce_a_verified_result() -> None:
    base = _complete_intake()
    scopes = list(base.rtdsm.scope_answers)
    index = next(i for i, row in enumerate(scopes) if row.code is ScopeCode.ENVIRONMENTS)
    scopes[index] = scopes[index].model_copy(update={"normalized_value_sha256": "0" * 64})
    rtdsm = base.rtdsm.model_copy(update={"scope_answers": tuple(scopes)})
    with pytest.raises(ValidationError, match="RTDSM normalized scope hash mismatch"):
        build_phase27_package(base.model_copy(update={"rtdsm": rtdsm}))


@pytest.mark.parametrize("provider", ["crsp", "sec"])
def test_phase27_rejects_rehashed_requirement_evaluation_that_drifted_from_intake(
    provider: str,
) -> None:
    payload = build_phase27_package(_complete_intake()).model_dump(mode="python")
    intake = payload["intake"]
    intake[provider]["requirement_answers"][0]["state"] = "FAIL"
    _rehash_evidence_bundle_and_artifact(payload)
    with pytest.raises(
        ValidationError, match=f"{provider.upper()} requirement evaluations drifted"
    ):
        Phase27RightsEntitlementEvidencePackage.model_validate(payload)


def test_phase27_generation_time_is_bound_to_recorded_intake_time() -> None:
    base = build_phase27_package().intake
    future = datetime(2030, 1, 1, tzinfo=UTC)
    artifact = build_phase27_package(
        base.model_copy(update={"evaluated_at_utc": future, "recorded_at_utc": future})
    )
    assert artifact.generated_at_utc == artifact.intake.recorded_at_utc == future

    payload = artifact.model_dump(mode="python")
    payload["generated_at_utc"] = EVALUATED
    artifact_payload = {
        key: value
        for key, value in payload.items()
        if key not in {"artifact_id", "artifact_sha256"}
    }
    replacement_hash = c.domain_sha256(c.ARTIFACT_DOMAIN, artifact_payload)
    payload["artifact_sha256"] = replacement_hash
    payload["artifact_id"] = c.uuid_from_sha256(c.ARTIFACT_NAMESPACE, replacement_hash)
    with pytest.raises(ValidationError, match="generation chronology"):
        Phase27RightsEntitlementEvidencePackage.model_validate(payload)
