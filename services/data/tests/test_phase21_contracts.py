from __future__ import annotations

import operator
from uuid import UUID

import pytest
from fable5_data.phase21 import canonical as c
from fable5_data.phase21.contracts import (
    FamilyACandidateGroupBinding,
    FamilyACapabilityAssignment,
    FamilyACompositionDecisionGate,
    FamilyADecisionFieldRequirement,
    FamilyAForbiddenSubstitute,
    FamilyAFutureCompositionRule,
    FamilyAOperationalCompositionDecisionRequirements,
    FamilyAPostSelectionDependency,
    FamilyAProductRightsBinding,
    RequirementsConclusion,
    RequirementsOutcome,
    RequirementsState,
)
from fable5_data.phase21.decision_requirements import (
    build_family_a_operational_composition_decision_requirements,
)
from pydantic import ValidationError


def _rehash_artifact(payload: dict[str, object]) -> dict[str, object]:
    preimage = {key: value for key, value in payload.items() if key != "artifact_sha256"}
    payload["artifact_sha256"] = c.domain_sha256(c.PHASE21_ARTIFACT_HASH_DOMAIN, preimage)
    return payload


def _rehash_row(payload: dict[str, object], hash_field: str, domain: str) -> dict[str, object]:
    preimage = {key: value for key, value in payload.items() if key != hash_field}
    payload[hash_field] = c.domain_sha256(domain, preimage)
    return payload


def test_exact_identity_and_closed_blocked_vocabulary() -> None:
    artifact = build_family_a_operational_composition_decision_requirements()

    assert str(artifact.artifact_id) == "50086eea-4598-5e6b-b168-616321c7a068"
    assert artifact.artifact_sha256 == (
        "44b5c4541febe6f6e389480102346b802bb4627b81e8d38cab4110cb2eab6a6e"
    )
    assert artifact.decision_requirements_policy_sha256 == (
        "22773ad7e58c4baa2c2f7d84bb68c7992d343676f93dc780374ce8e1125f99cf"
    )
    assert tuple(RequirementsOutcome) == (RequirementsOutcome.BLOCKED,)
    assert tuple(RequirementsState) == (RequirementsState.DECISION_REQUIREMENTS_FROZEN,)
    assert tuple(RequirementsConclusion) == (
        RequirementsConclusion.BLOCKED_AWAITING_EXPLICIT_OPERATIONAL_SOURCE_PRODUCT_COMPOSITION,
    )
    assert artifact.frozen_at_utc == "2026-07-20T09:30:00.000000Z"


@pytest.mark.parametrize(
    ("constant_name", "replacement"),
    [
        ("PHASE21_ARTIFACT_NAMESPACE", UUID("00000000-0000-5000-8000-000000000001")),
        ("PHASE21_ARTIFACT_SCHEMA_VERSION", "phase21-mutated-artifact-v2"),
        ("PHASE21_CANDIDATE_GROUP_SCHEMA_VERSION", "phase21-mutated-group-v2"),
        ("PHASE21_CANDIDATE_GROUP_HASH_DOMAIN", "phase21-mutated-group-domain-v2"),
        ("PHASE21_CANDIDATE_GROUPS_MANIFEST_HASH_DOMAIN", "phase21-mutated-manifest-v2"),
        ("PHASE21_PHASE20_ARTIFACT_ID", "00000000-0000-5000-8000-000000000002"),
        ("PHASE21_PHASE20_INPUTS_MANIFEST_SHA256", "0" * 64),
        ("PHASE21_PHASE17_PRODUCT_INVENTORY_SHA256", "1" * 64),
        ("PHASE21_PHASE18_AGGREGATE_CONCLUSION", "MUTATED_CONCLUSION"),
        ("PHASE21_PHASE16_CAPABILITIES_MANIFEST_SHA256", "2" * 64),
        ("PHASE21_FAMILY", "MUTATED_FAMILY"),
        ("PHASE21_BLOCK_REASON", "Mutated block reason."),
        ("PHASE21_DISCLAIMER", "Mutated disclaimer."),
    ],
)
def test_policy_identity_binds_lineage_schema_domains_and_text(
    monkeypatch: pytest.MonkeyPatch,
    constant_name: str,
    replacement: object,
) -> None:
    accepted_sha = c.PHASE21_POLICY_SHA256
    accepted_identity = c.identity(accepted_sha)
    monkeypatch.setattr(c, constant_name, replacement)

    mutated_sha = c.domain_sha256(c.PHASE21_POLICY_HASH_DOMAIN, c._policy_payload())

    assert mutated_sha != accepted_sha
    assert c.identity(mutated_sha) != accepted_identity


def test_policy_identity_binds_exact_row_content(monkeypatch: pytest.MonkeyPatch) -> None:
    accepted_sha = c.PHASE21_POLICY_SHA256
    rows = list(c.PHASE21_GATE_ROWS)
    rows[0] = (rows[0][0], "Mutated immutable gate definition.")
    monkeypatch.setattr(c, "PHASE21_GATE_ROWS", tuple(rows))

    mutated_sha = c.domain_sha256(c.PHASE21_POLICY_HASH_DOMAIN, c._policy_payload())

    assert mutated_sha != accepted_sha
    assert c.identity(mutated_sha) != c.identity(accepted_sha)


def test_policy_preimage_covers_every_schema_manifest_and_source_identity() -> None:
    payload = c._policy_payload()

    assert len(payload["schemas_and_hash_domains"]) == 13
    assert len(payload["manifest_hash_domains"]) == 12
    assert len(payload["accepted_phase20_identity"]) == 15
    assert len(payload["phase17_source_identity"]) == 7
    assert len(payload["phase18_source_identity"]) == 9
    assert len(payload["phase16_source_identity"]) == 9
    assert payload["artifact_uuid_namespace"] == str(c.PHASE21_ARTIFACT_NAMESPACE)
    assert payload["family"] == c.PHASE21_FAMILY
    assert payload["block_reason"] == c.PHASE21_BLOCK_REASON
    assert payload["disclaimer"] == c.PHASE21_DISCLAIMER


@pytest.mark.parametrize(
    ("collection", "index", "field", "replacement", "model", "hash_field", "domain"),
    [
        (
            "candidate_group_bindings",
            0,
            "operationally_selected",
            True,
            FamilyACandidateGroupBinding,
            "binding_sha256",
            c.PHASE21_CANDIDATE_GROUP_HASH_DOMAIN,
        ),
        (
            "candidate_group_bindings",
            0,
            "ranked",
            True,
            FamilyACandidateGroupBinding,
            "binding_sha256",
            c.PHASE21_CANDIDATE_GROUP_HASH_DOMAIN,
        ),
        (
            "product_rights_bindings",
            0,
            "current_rights_verified",
            True,
            FamilyAProductRightsBinding,
            "binding_sha256",
            c.PHASE21_PRODUCT_RIGHTS_HASH_DOMAIN,
        ),
        (
            "capability_assignments",
            0,
            "assignment_value_present",
            True,
            FamilyACapabilityAssignment,
            "assignment_sha256",
            c.PHASE21_CAPABILITY_HASH_DOMAIN,
        ),
        (
            "decision_fields",
            0,
            "value_present",
            True,
            FamilyADecisionFieldRequirement,
            "requirement_sha256",
            c.PHASE21_DECISION_FIELD_HASH_DOMAIN,
        ),
        (
            "decision_fields",
            0,
            "evidence_produced",
            True,
            FamilyADecisionFieldRequirement,
            "requirement_sha256",
            c.PHASE21_DECISION_FIELD_HASH_DOMAIN,
        ),
        (
            "post_selection_dependencies",
            0,
            "satisfied",
            True,
            FamilyAPostSelectionDependency,
            "dependency_sha256",
            c.PHASE21_DEPENDENCY_HASH_DOMAIN,
        ),
        (
            "decision_gates",
            0,
            "passed",
            True,
            FamilyACompositionDecisionGate,
            "gate_sha256",
            c.PHASE21_GATE_HASH_DOMAIN,
        ),
        (
            "future_rules",
            0,
            "applied",
            True,
            FamilyAFutureCompositionRule,
            "rule_sha256",
            c.PHASE21_RULE_HASH_DOMAIN,
        ),
        (
            "forbidden_substitutes",
            0,
            "forbidden",
            False,
            FamilyAForbiddenSubstitute,
            "substitute_sha256",
            c.PHASE21_SUBSTITUTE_HASH_DOMAIN,
        ),
    ],
)
def test_closed_row_tamper_is_rejected_even_when_rehashed(
    collection: str,
    index: int,
    field: str,
    replacement: object,
    model: type[object],
    hash_field: str,
    domain: str,
) -> None:
    artifact = build_family_a_operational_composition_decision_requirements()
    row = getattr(artifact, collection)[index].model_dump(mode="python")
    row[field] = replacement
    with pytest.raises(ValidationError):
        model.model_validate(_rehash_row(row, hash_field, domain))  # type: ignore[attr-defined]


@pytest.mark.parametrize("field", tuple(c.PHASE21_BOUNDARY_VALUES))
def test_artifact_boundary_tamper_is_rejected_when_rehashed(field: str) -> None:
    payload = build_family_a_operational_composition_decision_requirements().model_dump(
        mode="python"
    )
    payload[field] = not bool(payload[field])
    with pytest.raises(ValidationError):
        FamilyAOperationalCompositionDecisionRequirements.model_validate(_rehash_artifact(payload))


def test_decision_field_contract_has_no_value_or_evidence_payload() -> None:
    properties = set(FamilyADecisionFieldRequirement.model_json_schema()["properties"])
    assert "value" not in properties
    assert "evidence" not in properties
    assert {"value_present", "evidence_produced"} <= properties


def test_boundary_registry_is_required_and_immutable() -> None:
    required = set(
        FamilyAOperationalCompositionDecisionRequirements.model_json_schema()["required"]
    )
    assert set(c.PHASE21_BOUNDARY_VALUES) <= required
    with pytest.raises(TypeError):
        operator.setitem(  # type: ignore[call-overload]
            c.PHASE21_BOUNDARY_VALUES,
            "operational_source_product_composition_selected",
            True,
        )
