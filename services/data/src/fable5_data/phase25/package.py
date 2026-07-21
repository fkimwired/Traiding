"""Pure, deterministic Phase 25 evidence evaluator and package builder."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from fable5_data.phase25 import canonical as c
from fable5_data.phase25.contracts import (
    AdapterPattern,
    AuthorityEvidence,
    AuthorityEvidenceInput,
    EnforceableCondition,
    EvaluationState,
    Phase25Package,
    QuestionAnswerInput,
    QuestionCode,
    QuestionEvaluation,
    RightsResponseConditionInput,
    RightsResponseIntake,
    ScopeAnswerInput,
    ScopeCode,
    ScopeEvaluation,
    SourceEvidence,
    TransitionRule,
    VerificationStatus,
    authority_manifest_sha256,
    patterns_manifest_sha256,
    questions_manifest_sha256,
    rules_manifest_sha256,
    scope_manifest_sha256,
    sources_manifest_sha256,
)


def _validated[ModelT: BaseModel](
    model: type[ModelT], payload: dict[str, Any], hash_field: str, domain: str
) -> ModelT:
    return model.model_validate({**payload, hash_field: c.domain_sha256(domain, payload)})


def _condition(row: RightsResponseConditionInput) -> EnforceableCondition:
    payload = {
        "schema_version": c.PHASE25_CONDITION_SCHEMA_VERSION,
        **row.model_dump(mode="python"),
    }
    return _validated(
        EnforceableCondition,
        payload,
        "condition_sha256",
        c.PHASE25_CONDITION_HASH_DOMAIN,
    )


def _authority(row: AuthorityEvidenceInput) -> AuthorityEvidence:
    verified = (
        row.authenticated_provenance.value
        in {
            "EXECUTED_AGREEMENT",
            "AUTHENTICATED_PROVIDER_PORTAL",
            "CRYPTOGRAPHICALLY_SIGNED_RESPONSE",
            "RIGHTS_HOLDER_RECORD",
        }
        and row.independent_verification_status.value == "VERIFIED"
        and row.responder_identity_authenticated
        and row.authority_basis_verified
    )
    payload = {
        "schema_version": c.PHASE25_AUTHORITY_SCHEMA_VERSION,
        **row.model_dump(mode="python"),
        "authority_verified": verified,
    }
    return _validated(
        AuthorityEvidence,
        payload,
        "authority_record_sha256",
        c.PHASE25_AUTHORITY_HASH_DOMAIN,
    )


def _question_payload(
    ordinal: int,
    answer: QuestionAnswerInput | None,
    verified_evidence_ids: frozenset[str],
) -> dict[str, Any]:
    row = c.PHASE25_QUESTION_ROWS[ordinal - 1]
    if answer is None:
        state = EvaluationState.MISSING
        finding = c.PHASE25_MISSING_FINDING
        evidence_ids: tuple[str, ...] = ()
        conditions: tuple[EnforceableCondition, ...] = ()
        independently_verified = False
    else:
        evidence_ids = tuple(answer.evidence_ids)
        independently_verified = bool(evidence_ids) and set(evidence_ids) <= verified_evidence_ids
        conditions = tuple(_condition(item) for item in answer.conditions)
        if answer.state is not EvaluationState.MISSING and not independently_verified:
            state = EvaluationState.MISSING
            finding = (
                f"Claimed {answer.state.value}, but cited evidence was not independently verified."
            )
            evidence_ids = ()
            conditions = ()
        else:
            state = answer.state
            finding = answer.normalized_finding
    satisfied = state is EvaluationState.PASS or (
        state is EvaluationState.CONDITIONAL
        and bool(conditions)
        and all(
            condition.control_id is not None
            and condition.acceptance_test_id is not None
            and condition.enforceable
            and condition.acceptance_test_passed
            for condition in conditions
        )
    )
    return {
        "schema_version": c.PHASE25_QUESTION_SCHEMA_VERSION,
        "ordinal": ordinal,
        "code": row[0],
        "phase24_rights_field": row[1],
        "question": row[2],
        "state": state,
        "normalized_finding": finding,
        "evidence_ids": evidence_ids,
        "independently_verified": independently_verified
        if state is not EvaluationState.MISSING
        else False,
        "conditions": conditions,
        "satisfied": satisfied,
    }


def _scope_payload(
    ordinal: int,
    answer: ScopeAnswerInput | None,
    verified_evidence_ids: frozenset[str],
) -> dict[str, Any]:
    row = c.PHASE25_SCOPE_ROWS[ordinal - 1]
    if answer is None:
        state = EvaluationState.MISSING
        determination = c.PHASE25_MISSING_FINDING
        value_sha256 = c.domain_sha256(c.PHASE25_NORMALIZED_VALUE_HASH_DOMAIN, determination)
        evidence_ids: tuple[str, ...] = ()
        conditions: tuple[EnforceableCondition, ...] = ()
        independently_verified = False
    else:
        state = answer.state
        determination = answer.normalized_determination
        value_sha256 = answer.normalized_value_sha256
        evidence_ids = tuple(answer.evidence_ids)
        independently_verified = bool(evidence_ids) and set(evidence_ids) <= verified_evidence_ids
        conditions = tuple(_condition(item) for item in answer.conditions)
        if state is not EvaluationState.MISSING and not independently_verified:
            state = EvaluationState.MISSING
            determination = (
                f"Claimed {answer.state.value}, but cited evidence was not independently verified."
            )
            value_sha256 = c.domain_sha256(c.PHASE25_NORMALIZED_VALUE_HASH_DOMAIN, determination)
            evidence_ids = ()
            conditions = ()
        elif state in {EvaluationState.PASS, EvaluationState.CONDITIONAL}:
            code = ScopeCode(row[0])
            if code is ScopeCode.PRODUCT and determination != c.PHASE25_PRODUCT_NAME:
                state = EvaluationState.FAIL
                conditions = ()
            elif code is ScopeCode.LICENSED_PARTY and determination != "INDIVIDUAL_ACCOUNT_HOLDER":
                state = EvaluationState.FAIL
                conditions = ()
    satisfied = state is EvaluationState.PASS or (
        state is EvaluationState.CONDITIONAL
        and bool(conditions)
        and all(
            condition.control_id is not None
            and condition.acceptance_test_id is not None
            and condition.enforceable
            and condition.acceptance_test_passed
            for condition in conditions
        )
    )
    return {
        "schema_version": c.PHASE25_SCOPE_SCHEMA_VERSION,
        "ordinal": ordinal,
        "code": row[0],
        "requirement": row[1],
        "state": state,
        "normalized_determination": determination,
        "normalized_value_sha256": value_sha256,
        "evidence_ids": evidence_ids,
        "independently_verified": independently_verified
        if state is not EvaluationState.MISSING
        else False,
        "conditions": conditions,
        "satisfied": satisfied,
    }


def _sources() -> tuple[SourceEvidence, ...]:
    return tuple(
        _validated(
            SourceEvidence,
            {
                "schema_version": c.PHASE25_SOURCE_SCHEMA_VERSION,
                "ordinal": ordinal,
                **dict(row),
            },
            "source_sha256",
            c.PHASE25_SOURCE_HASH_DOMAIN,
        )
        for ordinal, row in enumerate(c.PHASE25_SOURCE_ROWS, 1)
    )


def _patterns() -> tuple[AdapterPattern, ...]:
    return tuple(
        _validated(
            AdapterPattern,
            {
                "schema_version": c.PHASE25_PATTERN_SCHEMA_VERSION,
                "ordinal": ordinal,
                "code": row[0],
                "definition": row[1],
                "source_codes": row[2],
                "adaptation_policy": row[3],
                "status": row[4],
            },
            "pattern_sha256",
            c.PHASE25_PATTERN_HASH_DOMAIN,
        )
        for ordinal, row in enumerate(c.PHASE25_PATTERN_ROWS, 1)
    )


def _rules() -> tuple[TransitionRule, ...]:
    return tuple(
        _validated(
            TransitionRule,
            {
                "schema_version": c.PHASE25_RULE_SCHEMA_VERSION,
                "ordinal": ordinal,
                "code": row[0],
                "rule": row[1],
            },
            "rule_sha256",
            c.PHASE25_RULE_HASH_DOMAIN,
        )
        for ordinal, row in enumerate(c.PHASE25_RULE_ROWS, 1)
    )


def build_phase25_package(intake: RightsResponseIntake | None = None) -> Phase25Package:
    """Evaluate sanitized response metadata and build the hash-bound Phase 25 package."""

    response_received = intake.response_received if intake is not None else False
    authority = tuple(_authority(row) for row in (intake.authority_evidence if intake else ()))
    verified_ids = frozenset(
        row.immutable_evidence_id for row in authority if row.authority_verified
    )
    consistency_status = (
        intake.mutual_consistency_status if intake else VerificationStatus.UNVERIFIED
    )
    consistency_evidence_ids = tuple(intake.mutual_consistency_evidence_ids) if intake else ()
    consistency_verified = (
        consistency_status is VerificationStatus.VERIFIED
        and bool(consistency_evidence_ids)
        and set(consistency_evidence_ids) <= verified_ids
    )
    question_inputs = {row.code: row for row in (intake.question_answers if intake else ())}
    scope_inputs = {row.code: row for row in (intake.scope_answers if intake else ())}
    questions = tuple(
        _validated(
            QuestionEvaluation,
            _question_payload(
                ordinal,
                question_inputs.get(QuestionCode(row[0])),
                verified_ids,
            ),
            "evaluation_sha256",
            c.PHASE25_QUESTION_HASH_DOMAIN,
        )
        for ordinal, row in enumerate(c.PHASE25_QUESTION_ROWS, 1)
    )
    scope = tuple(
        _validated(
            ScopeEvaluation,
            _scope_payload(ordinal, scope_inputs.get(ScopeCode(row[0])), verified_ids),
            "scope_sha256",
            c.PHASE25_SCOPE_HASH_DOMAIN,
        )
        for ordinal, row in enumerate(c.PHASE25_SCOPE_ROWS, 1)
    )
    sources = _sources()
    patterns = _patterns()
    rules = _rules()
    authority_manifest = authority_manifest_sha256(authority)
    question_manifest = questions_manifest_sha256(questions)
    scope_manifest = scope_manifest_sha256(scope)
    source_manifest = sources_manifest_sha256(sources)
    pattern_manifest = patterns_manifest_sha256(patterns)
    rule_manifest = rules_manifest_sha256(rules)
    evidence_snapshot_sha256 = c.domain_sha256(
        c.PHASE25_AUTHORITY_MANIFEST_HASH_DOMAIN,
        {
            "authority": authority_manifest,
            "questions": question_manifest,
            "scope": scope_manifest,
            "mutual_consistency_status": consistency_status,
            "mutual_consistency_evidence_ids": consistency_evidence_ids,
        },
    )
    positive = (
        response_received
        and bool(authority)
        and all(row.authority_verified for row in authority)
        and all(row.satisfied for row in questions)
        and all(row.satisfied for row in scope)
        and consistency_verified
    )
    determination = (
        "RIGHTS_RESPONSE_VERIFIED_REQUIRES_SEPARATE_ACQUISITION_AUTHORITY"
        if positive
        else (
            "RIGHTS_RESPONSE_EVIDENCE_MISSING"
            if not response_received
            else "RIGHTS_RESPONSE_BLOCKED"
        )
    )
    block_reason = (
        (
            "Rights evidence passed; Phase 25 still does not authorize acquisition or adapter "
            "activation."
        )
        if positive
        else (
            c.PHASE25_BLOCK_REASON
            if not response_received
            else (
                "One or more authority, question, exact-scope, evidence, or "
                "enforceable-condition gates did not pass."
            )
        )
    )
    identity_sha = c.domain_sha256(
        "phase25-artifact-identity-v1",
        {"policy": c.PHASE25_POLICY_SHA256, "evidence": evidence_snapshot_sha256},
    )
    payload = {
        "schema_version": c.PHASE25_ARTIFACT_SCHEMA_VERSION,
        "artifact_id": c.identity(identity_sha),
        "config_sha256": c.PHASE25_POLICY_SHA256,
        "policy_id": c.PHASE25_POLICY_ID,
        "policy_sha256": c.PHASE25_POLICY_SHA256,
        "phase24_merge_commit_sha": c.PHASE25_PHASE24_MERGE_COMMIT_SHA,
        "phase24_merge_tree_sha": c.PHASE25_PHASE24_MERGE_TREE_SHA,
        "accepted_phase24_commit_sha": c.PHASE25_ACCEPTED_PHASE24_COMMIT_SHA,
        "accepted_phase24_tree_sha": c.PHASE25_ACCEPTED_PHASE24_TREE_SHA,
        "phase24_artifact_id": c.PHASE25_PHASE24_ARTIFACT_ID,
        "phase24_artifact_sha256": c.PHASE25_PHASE24_ARTIFACT_SHA256,
        "phase24_artifact_file_sha256": c.PHASE25_PHASE24_ARTIFACT_FILE_SHA256,
        "phase24_policy_sha256": c.PHASE25_PHASE24_POLICY_SHA256,
        "phase24_questions_manifest_sha256": c.PHASE25_PHASE24_QUESTIONS_MANIFEST_SHA256,
        "product_code": c.PHASE25_PRODUCT_CODE,
        "product_name": c.PHASE25_PRODUCT_NAME,
        "family": c.PHASE25_FAMILY,
        "generated_at_utc": c.PHASE25_GENERATED_AT_UTC,
        "source_research_at_utc": c.PHASE25_SOURCE_RESEARCH_AT_UTC,
        "generation_git_sha": c.PHASE25_GENERATION_GIT_SHA,
        "random_seed": c.PHASE25_RANDOM_SEED,
        "trial_count": c.PHASE25_TRIAL_COUNT,
        "source_snapshot_id": c.uuid_from_sha256(
            c.PHASE25_SOURCE_SNAPSHOT_NAMESPACE, source_manifest
        ),
        "source_snapshot_sha256": source_manifest,
        "evidence_snapshot_id": c.uuid_from_sha256(
            c.PHASE25_EVIDENCE_SNAPSHOT_NAMESPACE, evidence_snapshot_sha256
        ),
        "evidence_snapshot_sha256": evidence_snapshot_sha256,
        "authority_manifest_sha256": authority_manifest,
        "questions_manifest_sha256": question_manifest,
        "scope_manifest_sha256": scope_manifest,
        "patterns_manifest_sha256": pattern_manifest,
        "rules_manifest_sha256": rule_manifest,
        "outcome": "PASS" if positive else "BLOCKED",
        "determination": determination,
        "block_reason": block_reason,
        "authority_evidence": authority,
        "question_evaluations": questions,
        "scope_evaluations": scope,
        "source_evidence": sources,
        "adapter_patterns": patterns,
        "transition_rules": rules,
        "mutual_consistency_status": consistency_status,
        "mutual_consistency_evidence_ids": consistency_evidence_ids,
        "mutual_consistency_verified": consistency_verified,
        **dict(c.PHASE25_BOUNDARY_VALUES),
        "response_received": response_received,
        "authority_evidence_present": bool(authority),
        "rights_verified": positive,
        "disclaimer": c.PHASE25_DISCLAIMER,
    }
    return Phase25Package.model_validate(
        {**payload, "artifact_sha256": c.domain_sha256(c.PHASE25_ARTIFACT_HASH_DOMAIN, payload)}
    )


def canonical_phase25_package_bytes(intake: RightsResponseIntake | None = None) -> bytes:
    return c.canonical_json_bytes(build_phase25_package(intake)) + b"\n"


__all__ = ["build_phase25_package", "canonical_phase25_package_bytes"]
