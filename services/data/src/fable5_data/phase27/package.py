"""Pure deterministic Phase 27 metadata-evidence evaluator."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from fable5_data.phase25 import canonical as phase25_c
from fable5_data.phase25.contracts import VerificationStatus
from fable5_data.phase25.package import build_phase25_package
from fable5_data.phase27 import canonical as c
from fable5_data.phase27.contracts import (
    AuthorityEvidenceRecord,
    CRSPRightsEntitlementIntake,
    Determination,
    EvidenceState,
    Phase27EvidenceIntake,
    Phase27RightsEntitlementEvidencePackage,
    RequirementAnswerInput,
    RequirementEvaluation,
    RTDSMPhase25EvaluationBinding,
    SanitizedRightsResponseIntake,
    SECPolicyDocument,
    SECPolicyRevalidationIntake,
    SelectedProductEvidenceEvaluation,
    authority_is_current,
    authority_is_verified,
    authority_manifest_sha256,
    build_requirement_evaluations,
    phase25_evaluator_intake,
    products_manifest_sha256,
    requirements_manifest_sha256,
    sec_documents_manifest_sha256,
)


def _validated[ModelT: BaseModel](
    model: type[ModelT], payload: dict[str, Any], hash_field: str, domain: str
) -> ModelT:
    return model.model_validate({**payload, hash_field: c.domain_sha256(domain, payload)})


def _empty_intake() -> Phase27EvidenceIntake:
    fixed_at = datetime.fromisoformat(c.FIXED_AT_UTC.replace("Z", "+00:00"))
    return Phase27EvidenceIntake(
        schema_version=c.INTAKE_SCHEMA,
        evaluated_at_utc=fixed_at,
        recorded_at_utc=fixed_at,
        crsp=CRSPRightsEntitlementIntake(
            schema_version=c.CRSP_INTAKE_SCHEMA,
            response_received=False,
        ),
        rtdsm=SanitizedRightsResponseIntake(
            schema_version=phase25_c.PHASE25_INTAKE_SCHEMA_VERSION,
            response_received=False,
        ),
        sec=SECPolicyRevalidationIntake(
            schema_version=c.SEC_INTAKE_SCHEMA,
            review_performed=False,
        ),
    )


def _authority_records(intake: Phase27EvidenceIntake) -> tuple[AuthorityEvidenceRecord, ...]:
    records = []
    for row in intake.crsp.authority_evidence:
        effective = (
            row.response_date_utc <= intake.evaluated_at_utc
            and row.effective_date_utc <= intake.evaluated_at_utc
        )
        payload = {
            **row.model_dump(mode="python"),
            "schema_version": c.AUTHORITY_SCHEMA,
            "product_code": c.CRSP_PRODUCT,
            "authority_verified": authority_is_verified(row),
            "effective_at_evaluation": effective,
            "current_at_evaluation": authority_is_current(row, intake.evaluated_at_utc),
        }
        records.append(
            _validated(
                AuthorityEvidenceRecord,
                payload,
                "record_sha256",
                c.AUTHORITY_DOMAIN,
            )
        )
    return tuple(records)


def _sec_documents(intake: Phase27EvidenceIntake) -> tuple[SECPolicyDocument, ...]:
    documents = []
    for row in intake.sec.policy_documents:
        current = (
            row.effective_at_utc <= intake.evaluated_at_utc
            and row.retrieved_at_utc <= intake.evaluated_at_utc < row.revalidation_due_at_utc
        )
        payload = {
            **row.model_dump(mode="python"),
            "schema_version": c.SEC_DOCUMENT_SCHEMA,
            "official_first_party": True,
            "current_at_evaluation": current,
            "independently_verified": (
                row.independent_verification_status is VerificationStatus.VERIFIED
            ),
        }
        documents.append(
            _validated(
                SECPolicyDocument,
                payload,
                "document_sha256",
                c.SEC_DOCUMENT_DOMAIN,
            )
        )
    return tuple(documents)


def _requirements(
    product: str,
    answers: tuple[RequirementAnswerInput, ...],
    verified_evidence_ids: frozenset[str],
) -> tuple[RequirementEvaluation, ...]:
    return build_requirement_evaluations(product, answers, verified_evidence_ids)


def _rtdsm_binding(intake: Phase27EvidenceIntake) -> RTDSMPhase25EvaluationBinding:
    package = build_phase25_package(phase25_evaluator_intake(intake.rtdsm))
    authority_current = bool(intake.rtdsm.authority_evidence) and all(
        authority_is_current(row, intake.evaluated_at_utc)
        for row in intake.rtdsm.authority_evidence
    )
    scopes = {row.code.value: row for row in package.scope_evaluations}
    selected_scope_bound = (
        scopes["REQUESTED_SERIES"].satisfied
        and scopes["REQUESTED_SERIES"].normalized_determination == c.RTDSM_REQUESTED_SERIES
        and scopes["PCPI_AND_BLS_ORIGIN"].satisfied
        and scopes["PCPI_AND_BLS_ORIGIN"].normalized_determination == c.RTDSM_PCPI_BLS_ORIGIN
        and scopes["DELIVERY_METHOD_AND_SURFACE"].satisfied
        and scopes["DELIVERY_METHOD_AND_SURFACE"].normalized_determination == c.DELIVERY_IDS[3]
    )
    rights_verified = package.rights_verified and authority_current and selected_scope_bound
    determination = (
        "RIGHTS_RESPONSE_VERIFIED_REQUIRES_SEPARATE_ACQUISITION_AUTHORITY"
        if rights_verified
        else (
            "RIGHTS_RESPONSE_BLOCKED"
            if intake.rtdsm.response_received
            else "RIGHTS_RESPONSE_EVIDENCE_MISSING"
        )
    )
    payload = {
        "schema_version": c.RTDSM_BINDING_SCHEMA,
        "phase25_artifact_id": package.artifact_id,
        "phase25_artifact_sha256": package.artifact_sha256,
        "phase25_evidence_snapshot_id": package.evidence_snapshot_id,
        "phase25_evidence_snapshot_sha256": package.evidence_snapshot_sha256,
        "phase25_authority_manifest_sha256": package.authority_manifest_sha256,
        "phase25_questions_manifest_sha256": package.questions_manifest_sha256,
        "phase25_scope_manifest_sha256": package.scope_manifest_sha256,
        "response_received": package.response_received,
        "question_count": len(package.question_evaluations),
        "scope_count": len(package.scope_evaluations),
        "satisfied_question_count": sum(row.satisfied for row in package.question_evaluations),
        "satisfied_scope_count": sum(row.satisfied for row in package.scope_evaluations),
        "mutual_consistency_verified": package.mutual_consistency_verified,
        "selected_scope_bound": selected_scope_bound,
        "rights_verified": rights_verified,
        "current_at_evaluation": authority_current,
        "determination": determination,
    }
    return _validated(
        RTDSMPhase25EvaluationBinding,
        payload,
        "binding_sha256",
        c.RTDSM_BINDING_DOMAIN,
    )


def _product(
    ordinal: int,
    *,
    required_count: int,
    satisfied_count: int,
    requirements_manifest: str,
    evidence_present: bool,
    independently_verified: bool,
    current_at_evaluation: bool,
) -> SelectedProductEvidenceEvaluation:
    row = c.PRODUCT_ROWS[ordinal - 1]
    verified = (
        satisfied_count == required_count
        and evidence_present
        and independently_verified
        and current_at_evaluation
    )
    state = (
        EvidenceState.VERIFIED_EVIDENCE_RECORDED
        if verified
        else EvidenceState.BLOCKED
        if evidence_present
        else EvidenceState.MISSING
    )
    payload = {
        "schema_version": c.PRODUCT_SCHEMA,
        "ordinal": ordinal,
        "product_code": row[0],
        "delivery_ids": row[1],
        "phase26_selected_product_sha256": row[2],
        "state": state,
        "required_count": required_count,
        "satisfied_count": satisfied_count,
        "requirements_manifest_sha256": requirements_manifest,
        "evidence_present": evidence_present,
        "independently_verified": independently_verified,
        "current_at_evaluation": current_at_evaluation,
    }
    return _validated(
        SelectedProductEvidenceEvaluation,
        payload,
        "product_evaluation_sha256",
        c.PRODUCT_DOMAIN,
    )


def build_phase27_package(
    intake: Phase27EvidenceIntake | None = None,
) -> Phase27RightsEntitlementEvidencePackage:
    source = intake or _empty_intake()
    evaluated = Phase27EvidenceIntake.model_validate(source.model_dump(mode="python"), strict=True)
    authority = _authority_records(evaluated)
    verified_crsp_ids = frozenset(
        row.immutable_evidence_id
        for row in authority
        if row.authority_verified and row.current_at_evaluation
    )
    crsp_requirements = _requirements(
        c.CRSP_PRODUCT, evaluated.crsp.requirement_answers, verified_crsp_ids
    )
    sec_documents = _sec_documents(evaluated)
    verified_sec_ids = frozenset(
        row.evidence_id
        for row in sec_documents
        if row.official_first_party and row.independently_verified and row.current_at_evaluation
    )
    sec_requirements = _requirements(
        c.SEC_PRODUCT, evaluated.sec.requirement_answers, verified_sec_ids
    )
    rtdsm_binding = _rtdsm_binding(evaluated)

    crsp_consistency = (
        evaluated.crsp.mutual_consistency_status is VerificationStatus.VERIFIED
        and bool(evaluated.crsp.mutual_consistency_evidence_ids)
        and set(evaluated.crsp.mutual_consistency_evidence_ids) <= verified_crsp_ids
    )
    sec_consistency = (
        evaluated.sec.mutual_consistency_status is VerificationStatus.VERIFIED
        and bool(evaluated.sec.mutual_consistency_evidence_ids)
        and set(evaluated.sec.mutual_consistency_evidence_ids) <= verified_sec_ids
    )
    crsp_exact_scope = (
        evaluated.crsp.licensed_party_identity_sha256 is not None
        and evaluated.crsp.executed_agreement_sha256 is not None
        and evaluated.crsp.order_form_or_product_schedule_sha256 is not None
        and evaluated.crsp.product_code == c.CRSP_PRODUCT
        and evaluated.crsp.product_sku_sha256 is not None
        and evaluated.crsp.delivery_id == c.DELIVERY_IDS[0]
        and evaluated.crsp.selected_capability_codes == c.CRSP_CAPABILITY_CODES
        and bool(evaluated.crsp.third_party_rights_evidence_ids)
        and set(evaluated.crsp.third_party_rights_evidence_ids) <= verified_crsp_ids
    )
    sec_source_set_bound = {row.source_code for row in sec_documents} == {
        row[0] for row in c.SEC_ACCEPTED_SOURCE_ROWS
    }
    crsp_manifest = requirements_manifest_sha256(c.CRSP_PRODUCT, crsp_requirements)
    sec_manifest = requirements_manifest_sha256(c.SEC_PRODUCT, sec_requirements)
    rtdsm_manifest = c.domain_sha256(
        c.RTDSM_REQUIREMENTS_MANIFEST_DOMAIN,
        {
            "questions": rtdsm_binding.phase25_questions_manifest_sha256,
            "scope": rtdsm_binding.phase25_scope_manifest_sha256,
        },
    )
    products = (
        _product(
            1,
            required_count=len(c.CRSP_REQUIREMENT_ROWS),
            satisfied_count=sum(row.satisfied for row in crsp_requirements),
            requirements_manifest=crsp_manifest,
            evidence_present=(
                evaluated.crsp.response_received
                or bool(evaluated.crsp.authority_evidence)
                or bool(evaluated.crsp.requirement_answers)
            ),
            independently_verified=(
                bool(authority)
                and all(row.authority_verified for row in authority)
                and crsp_consistency
                and crsp_exact_scope
            ),
            current_at_evaluation=(
                bool(authority) and all(row.current_at_evaluation for row in authority)
            ),
        ),
        _product(
            2,
            required_count=len(c.SEC_REQUIREMENT_ROWS),
            satisfied_count=sum(row.satisfied for row in sec_requirements),
            requirements_manifest=sec_manifest,
            evidence_present=(
                evaluated.sec.review_performed
                or bool(evaluated.sec.policy_documents)
                or bool(evaluated.sec.requirement_answers)
            ),
            independently_verified=(
                bool(sec_documents)
                and all(row.independently_verified for row in sec_documents)
                and sec_consistency
                and sec_source_set_bound
            ),
            current_at_evaluation=(
                bool(sec_documents) and all(row.current_at_evaluation for row in sec_documents)
            ),
        ),
        _product(
            3,
            required_count=29,
            satisfied_count=(
                rtdsm_binding.satisfied_question_count + rtdsm_binding.satisfied_scope_count
            ),
            requirements_manifest=rtdsm_manifest,
            evidence_present=(
                evaluated.rtdsm.response_received
                or bool(evaluated.rtdsm.authority_evidence)
                or bool(evaluated.rtdsm.question_answers)
                or bool(evaluated.rtdsm.scope_answers)
            ),
            independently_verified=rtdsm_binding.rights_verified,
            current_at_evaluation=rtdsm_binding.current_at_evaluation,
        ),
    )
    all_verified_ids = set(verified_crsp_ids) | set(verified_sec_ids)
    verified_rtdsm_ids = {
        row.immutable_evidence_id
        for row in evaluated.rtdsm.authority_evidence
        if authority_is_verified(row) and authority_is_current(row, evaluated.evaluated_at_utc)
    }
    all_verified_ids |= verified_rtdsm_ids
    composition_consistent = (
        evaluated.composition_consistency_status is VerificationStatus.VERIFIED
        and bool(evaluated.composition_consistency_evidence_ids)
        and set(evaluated.composition_consistency_evidence_ids) <= all_verified_ids
        and bool(set(evaluated.composition_consistency_evidence_ids) & set(verified_crsp_ids))
        and bool(set(evaluated.composition_consistency_evidence_ids) & set(verified_sec_ids))
        and bool(set(evaluated.composition_consistency_evidence_ids) & verified_rtdsm_ids)
    )
    verified = (
        all(row.state is EvidenceState.VERIFIED_EVIDENCE_RECORDED for row in products)
        and composition_consistent
    )
    any_evidence = any(row.evidence_present for row in products)
    determination = (
        Determination.VERIFIED_EVIDENCE_RECORDED_REQUIRES_SEPARATE_ACQUISITION_AUTHORITY
        if verified
        else (
            Determination.COMPOSITION_RIGHTS_ENTITLEMENT_EVIDENCE_BLOCKED
            if any_evidence
            else Determination.COMPOSITION_RIGHTS_ENTITLEMENT_EVIDENCE_MISSING
        )
    )
    authority_manifest = authority_manifest_sha256(authority)
    sec_document_manifest = sec_documents_manifest_sha256(sec_documents)
    evidence_payload = {
        "intake": evaluated,
        "authority_manifest_sha256": authority_manifest,
        "crsp_requirements_manifest_sha256": crsp_manifest,
        "rtdsm_binding_sha256": rtdsm_binding.binding_sha256,
        "sec_policy_documents_manifest_sha256": sec_document_manifest,
        "sec_requirements_manifest_sha256": sec_manifest,
    }
    evidence_bundle_sha256 = c.domain_sha256(c.EVIDENCE_BUNDLE_DOMAIN, evidence_payload)
    payload: dict[str, Any] = {
        "schema_version": c.ARTIFACT_SCHEMA,
        "config_sha256": c.POLICY_SHA256,
        "policy_id": c.POLICY_ID,
        "policy_sha256": c.POLICY_SHA256,
        "accepted_phase26_commit_sha": c.BASELINE_COMMIT_SHA,
        "accepted_phase26_tree_sha": c.BASELINE_TREE_SHA,
        "phase26_artifact_id": c.PHASE26_ARTIFACT_ID,
        "phase26_artifact_sha256": c.PHASE26_ARTIFACT_SHA256,
        "phase26_artifact_file_sha256": c.PHASE26_ARTIFACT_FILE_SHA256,
        "phase26_policy_sha256": c.PHASE26_POLICY_SHA256,
        "phase26_selection_evidence_sha256": c.PHASE26_SELECTION_EVIDENCE_SHA256,
        "phase26_source_snapshot_id": c.PHASE26_SOURCE_SNAPSHOT_ID,
        "phase26_source_snapshot_sha256": c.PHASE26_SOURCE_SNAPSHOT_SHA256,
        "generation_git_sha": c.GENERATION_GIT_SHA,
        "random_seed": c.RANDOM_SEED,
        "trial_count": c.TRIAL_COUNT,
        "generated_at_utc": evaluated.recorded_at_utc,
        "family": c.FAMILY,
        "composition_id": c.COMPOSITION_ID,
        "product_ids": c.PRODUCT_IDS,
        "delivery_ids": c.DELIVERY_IDS,
        "intake": evaluated,
        "evidence_bundle_id": c.uuid_from_sha256(
            c.EVIDENCE_BUNDLE_NAMESPACE, evidence_bundle_sha256
        ),
        "evidence_bundle_sha256": evidence_bundle_sha256,
        "authority_evidence": authority,
        "authority_manifest_sha256": authority_manifest,
        "crsp_requirement_evaluations": crsp_requirements,
        "crsp_requirements_manifest_sha256": crsp_manifest,
        "rtdsm_phase25_binding": rtdsm_binding,
        "sec_policy_documents": sec_documents,
        "sec_policy_documents_manifest_sha256": sec_document_manifest,
        "sec_requirement_evaluations": sec_requirements,
        "sec_requirements_manifest_sha256": sec_manifest,
        "product_evaluations": products,
        "product_evaluations_manifest_sha256": products_manifest_sha256(products),
        "outcome": "BLOCKED",
        "determination": determination,
        "block_reason": (c.VERIFIED_BLOCK_REASON if verified else c.INCOMPLETE_BLOCK_REASON),
        "verified_evidence_recorded": verified,
        "current_rights_evidence_for_exact_composition": verified,
        **c.BOUNDARY_VALUES,
        "disclaimer": c.DISCLAIMER,
    }
    artifact_hash = c.domain_sha256(c.ARTIFACT_DOMAIN, payload)
    return Phase27RightsEntitlementEvidencePackage.model_validate(
        {
            **payload,
            "artifact_id": c.uuid_from_sha256(c.ARTIFACT_NAMESPACE, artifact_hash),
            "artifact_sha256": artifact_hash,
        }
    )


def canonical_phase27_package_bytes(intake: Phase27EvidenceIntake | None = None) -> bytes:
    return c.canonical_json_bytes(build_phase27_package(intake)) + b"\n"


__all__ = ["build_phase27_package", "canonical_phase27_package_bytes"]
