"""Pure deterministic builder for the Phase 15 portable specification."""

from __future__ import annotations

from fable5_data.phase15.canonical import (
    PHASE15_ACCEPTED_PHASE14_COMMIT_SHA,
    PHASE15_ACCEPTED_PHASE14_TREE_SHA,
    PHASE15_ARTIFACT_HASH_DOMAIN,
    PHASE15_ARTIFACT_SCHEMA_VERSION,
    PHASE15_BOUNDARY_VALUES,
    PHASE15_DISCLAIMER,
    PHASE15_EVIDENCE_HASH_DOMAIN,
    PHASE15_FAMILY,
    PHASE15_FROZEN_AT_UTC,
    PHASE15_GAP_EVIDENCE_REFS,
    PHASE15_GAP_HASH_DOMAIN,
    PHASE15_GAP_SUMMARIES,
    PHASE15_PHASE6_SPECIFICATION_ID,
    PHASE15_PHASE6_SPECIFICATION_SHA256,
    PHASE15_PHASE6_SPECIFICATION_VERSION,
    PHASE15_POLICY_ID,
    PHASE15_POLICY_SHA256,
    PHASE15_REQUIREMENT_DEFINITIONS,
    PHASE15_REQUIREMENT_HASH_DOMAIN,
    canonical_json_bytes,
    domain_sha256,
    identity,
)
from fable5_data.phase15.contracts import (
    PHASE15_EXPECTED_GAP_STATES,
    PHASE15_GAP_ORDER,
    PHASE15_REQUIREMENT_ORDER,
    FamilyAResearchAdmissionGap,
    FamilyAResearchAdmissionOutcome,
    FamilyAResearchAdmissionRequirement,
    FamilyAResearchAdmissionRequirementReason,
    FamilyAResearchAdmissionRequirementStatus,
    FamilyAResearchAdmissionSpecification,
    gaps_manifest_sha256,
    requirements_manifest_sha256,
)


def _evidence_sha256(
    *,
    kind: str,
    code: str,
    state: str,
    evidence_refs: tuple[str, ...],
) -> str:
    return domain_sha256(
        PHASE15_EVIDENCE_HASH_DOMAIN,
        {
            "kind": kind,
            "code": code,
            "state": state,
            "evidence_refs": evidence_refs,
            "accepted_phase14_commit_sha": PHASE15_ACCEPTED_PHASE14_COMMIT_SHA,
            "accepted_phase14_tree_sha": PHASE15_ACCEPTED_PHASE14_TREE_SHA,
            "phase6_specification_sha256": PHASE15_PHASE6_SPECIFICATION_SHA256,
        },
    )


def _requirements() -> tuple[FamilyAResearchAdmissionRequirement, ...]:
    requirements: list[FamilyAResearchAdmissionRequirement] = []
    for ordinal, code in enumerate(PHASE15_REQUIREMENT_ORDER, start=1):
        definition = PHASE15_REQUIREMENT_DEFINITIONS[ordinal - 1]
        payload = {
            "schema_version": "phase15-family-a-research-admission-requirement-v1",
            "ordinal": ordinal,
            "code": code,
            "definition": definition,
            "status": FamilyAResearchAdmissionRequirementStatus.PASS,
            "reason_code": (
                FamilyAResearchAdmissionRequirementReason.FROZEN_REPOSITORY_REQUIREMENT
            ),
            "evidence_sha256s": (
                _evidence_sha256(
                    kind="requirement",
                    code=code.value,
                    state="frozen",
                    evidence_refs=(
                        "docs/PHASE_14_RESEARCH_INGESTION_ELIGIBILITY_DECISIONS.md#decision",
                        "services/research/src/fable5_research/specification.py#family-a",
                    ),
                ),
            ),
        }
        requirements.append(
            FamilyAResearchAdmissionRequirement.model_validate(
                {
                    **payload,
                    "requirement_sha256": domain_sha256(PHASE15_REQUIREMENT_HASH_DOMAIN, payload),
                }
            )
        )
    return tuple(requirements)


def _gaps() -> tuple[FamilyAResearchAdmissionGap, ...]:
    gaps: list[FamilyAResearchAdmissionGap] = []
    for ordinal, (code, state) in enumerate(
        zip(PHASE15_GAP_ORDER, PHASE15_EXPECTED_GAP_STATES, strict=True),
        start=1,
    ):
        summary = PHASE15_GAP_SUMMARIES[ordinal - 1]
        evidence_refs = PHASE15_GAP_EVIDENCE_REFS[ordinal - 1]
        payload = {
            "schema_version": "phase15-family-a-research-admission-gap-v1",
            "ordinal": ordinal,
            "code": code,
            "state": state,
            "summary": summary,
            "evidence_refs": evidence_refs,
            "evidence_sha256s": (
                _evidence_sha256(
                    kind="gap",
                    code=code.value,
                    state=state.value,
                    evidence_refs=evidence_refs,
                ),
            ),
        }
        gaps.append(
            FamilyAResearchAdmissionGap.model_validate(
                {
                    **payload,
                    "gap_sha256": domain_sha256(PHASE15_GAP_HASH_DOMAIN, payload),
                }
            )
        )
    return tuple(gaps)


def build_family_a_research_admission_specification() -> FamilyAResearchAdmissionSpecification:
    """Build the sole requirements-only artifact without I/O or ambient state."""

    requirements = _requirements()
    gaps = _gaps()
    payload = {
        "schema_version": PHASE15_ARTIFACT_SCHEMA_VERSION,
        "artifact_id": identity(PHASE15_POLICY_SHA256),
        "policy_id": PHASE15_POLICY_ID,
        "policy_sha256": PHASE15_POLICY_SHA256,
        "accepted_phase14_commit_sha": PHASE15_ACCEPTED_PHASE14_COMMIT_SHA,
        "accepted_phase14_tree_sha": PHASE15_ACCEPTED_PHASE14_TREE_SHA,
        "family": PHASE15_FAMILY,
        "phase6_specification_id": PHASE15_PHASE6_SPECIFICATION_ID,
        "phase6_specification_version": PHASE15_PHASE6_SPECIFICATION_VERSION,
        "phase6_specification_sha256": PHASE15_PHASE6_SPECIFICATION_SHA256,
        "frozen_at_utc": PHASE15_FROZEN_AT_UTC,
        "outcome": FamilyAResearchAdmissionOutcome.REQUIREMENTS_FROZEN,
        "requirements_manifest_sha256": requirements_manifest_sha256(requirements),
        "gaps_manifest_sha256": gaps_manifest_sha256(gaps),
        "requirements": requirements,
        "gaps": gaps,
        **PHASE15_BOUNDARY_VALUES,
        "disclaimer": PHASE15_DISCLAIMER,
    }
    return FamilyAResearchAdmissionSpecification.model_validate(
        {
            **payload,
            "artifact_sha256": domain_sha256(PHASE15_ARTIFACT_HASH_DOMAIN, payload),
        }
    )


def canonical_specification_bytes() -> bytes:
    """Return the exact portable committed representation, including one final LF."""

    specification = build_family_a_research_admission_specification()
    return canonical_json_bytes(specification) + b"\n"


__all__ = [
    "build_family_a_research_admission_specification",
    "canonical_specification_bytes",
]
