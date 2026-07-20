from __future__ import annotations

import operator
from types import MappingProxyType
from uuid import UUID

import pytest
from fable5_data.phase22 import canonical as c
from fable5_data.phase22.contracts import (
    AmendmentConclusion,
    AmendmentOutcome,
    AmendmentState,
    CandidateGroupAmendment,
    FamilyAMacroVintageCandidateInventoryAmendment,
    FutureReviewRequirement,
    MacroVintageCandidateProduct,
    OfficialSourceCitation,
)
from fable5_data.phase22.inventory_amendment import (
    build_family_a_macro_vintage_candidate_inventory_amendment,
)
from pydantic import ValidationError


def _rehash_artifact(payload: dict[str, object]) -> dict[str, object]:
    preimage = {key: value for key, value in payload.items() if key != "artifact_sha256"}
    payload["artifact_sha256"] = c.domain_sha256(c.PHASE22_ARTIFACT_HASH_DOMAIN, preimage)
    return payload


def _rehash_row(payload: dict[str, object], hash_field: str, domain: str) -> dict[str, object]:
    preimage = {key: value for key, value in payload.items() if key != hash_field}
    payload[hash_field] = c.domain_sha256(domain, preimage)
    return payload


def test_exact_identity_and_closed_blocked_vocabulary() -> None:
    artifact = build_family_a_macro_vintage_candidate_inventory_amendment()

    assert str(artifact.artifact_id) == "9d763c2d-af50-5403-9646-50a88c962bd7"
    assert artifact.artifact_sha256 == (
        "6f6079b69838cdd292f3d426c0b1e23deeec35eaeed9f4129aa129585913abe1"
    )
    assert artifact.amendment_policy_sha256 == (
        "dbd7f77b646d3386d17e889cd81a3a25aed099bfc3451c37844d02d87404ba5f"
    )
    assert tuple(AmendmentOutcome) == (AmendmentOutcome.BLOCKED,)
    assert tuple(AmendmentState) == (AmendmentState.CANDIDATE_INVENTORY_AMENDMENT_FROZEN,)
    assert tuple(AmendmentConclusion) == (
        AmendmentConclusion.BLOCKED_AWAITING_CURRENT_RIGHTS_FITNESS_REVIEW_AND_EXPLICIT_OPERATIONAL_COMPOSITION,
    )


@pytest.mark.parametrize(
    ("constant_name", "replacement"),
    [
        ("PHASE22_POLICY_ID", "phase22-mutated-policy-v2"),
        ("PHASE22_POLICY_HASH_DOMAIN", "phase22-mutated-policy-domain-v2"),
        ("PHASE22_ARTIFACT_HASH_DOMAIN", "phase22-mutated-artifact-domain-v2"),
        ("PHASE22_ARTIFACT_NAMESPACE", UUID("00000000-0000-5000-8000-000000000001")),
        ("PHASE22_ACCEPTED_PHASE21_COMMIT_SHA", "0" * 40),
        ("PHASE22_PHASE21_ARTIFACT_SHA256", "0" * 64),
        ("PHASE22_PHASE21_BASE_PRODUCT_COUNT", 10),
        ("PHASE22_OFFICIAL_SOURCE_COUNT", 4),
        ("PHASE22_CANDIDATE_PRODUCT_COUNT", 2),
        ("PHASE22_AGGREGATE_CONCLUSION", "MUTATED_CONCLUSION"),
        ("PHASE22_BLOCK_REASON", "Mutated block reason."),
        (
            "PHASE22_SOURCE_INVARIANTS",
            MappingProxyType(
                {
                    "official_source": True,
                    "citation_inert": False,
                    "remote_body_included": False,
                }
            ),
        ),
        (
            "PHASE22_PRODUCT_INVARIANTS",
            MappingProxyType(
                {
                    **dict(c.PHASE22_PRODUCT_INVARIANTS),
                    "operationally_selected": True,
                }
            ),
        ),
    ],
)
def test_policy_identity_binds_lineage_domains_counts_and_invariants(
    monkeypatch: pytest.MonkeyPatch,
    constant_name: str,
    replacement: object,
) -> None:
    accepted_sha = c.PHASE22_POLICY_SHA256
    accepted_identity = c.identity(accepted_sha)
    monkeypatch.setattr(c, constant_name, replacement)

    mutated_sha = c.domain_sha256(c.PHASE22_POLICY_HASH_DOMAIN, c._policy_payload())

    assert mutated_sha != accepted_sha
    assert c.identity(mutated_sha) != accepted_identity


def test_policy_identity_binds_exact_product_and_requirement_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    accepted_sha = c.PHASE22_POLICY_SHA256
    rows = list(c.PHASE22_PRODUCT_ROWS)
    row = rows[0]
    rows[0] = (*row[:4], "Mutated official fact.", *row[5:])
    monkeypatch.setattr(c, "PHASE22_PRODUCT_ROWS", tuple(rows))

    mutated_sha = c.domain_sha256(c.PHASE22_POLICY_HASH_DOMAIN, c._policy_payload())

    assert mutated_sha != accepted_sha


@pytest.mark.parametrize(
    ("collection", "field", "replacement", "model", "hash_field", "domain"),
    [
        (
            "official_sources",
            "remote_body_included",
            True,
            OfficialSourceCitation,
            "source_sha256",
            c.PHASE22_SOURCE_HASH_DOMAIN,
        ),
        (
            "candidate_group_amendments",
            "operationally_selected",
            True,
            CandidateGroupAmendment,
            "group_sha256",
            c.PHASE22_GROUP_HASH_DOMAIN,
        ),
        (
            "candidate_products",
            "rights_state",
            "UNPROVEN",
            MacroVintageCandidateProduct,
            "product_sha256",
            c.PHASE22_PRODUCT_HASH_DOMAIN,
        ),
        (
            "future_review_requirements",
            "external_action_authorized",
            True,
            FutureReviewRequirement,
            "requirement_sha256",
            c.PHASE22_REQUIREMENT_HASH_DOMAIN,
        ),
    ],
)
def test_closed_row_tamper_is_rejected_even_when_rehashed(
    collection: str,
    field: str,
    replacement: object,
    model: type[object],
    hash_field: str,
    domain: str,
) -> None:
    artifact = build_family_a_macro_vintage_candidate_inventory_amendment()
    row = getattr(artifact, collection)[0].model_dump(mode="python")
    row[field] = replacement
    with pytest.raises(ValidationError):
        model.model_validate(_rehash_row(row, hash_field, domain))  # type: ignore[attr-defined]


@pytest.mark.parametrize("field", tuple(c.PHASE22_BOUNDARY_VALUES))
def test_artifact_boundary_tamper_is_rejected_when_rehashed(field: str) -> None:
    payload = build_family_a_macro_vintage_candidate_inventory_amendment().model_dump(mode="python")
    payload[field] = not bool(payload[field])
    with pytest.raises(ValidationError):
        FamilyAMacroVintageCandidateInventoryAmendment.model_validate(_rehash_artifact(payload))


def test_extra_fields_are_rejected_at_root_and_row_levels() -> None:
    artifact = build_family_a_macro_vintage_candidate_inventory_amendment()
    root = artifact.model_dump(mode="python")
    root["selection_evidence"] = "forbidden"
    with pytest.raises(ValidationError):
        FamilyAMacroVintageCandidateInventoryAmendment.model_validate(_rehash_artifact(root))

    product = artifact.candidate_products[0].model_dump(mode="python")
    product["provider_payload"] = "forbidden"
    with pytest.raises(ValidationError):
        MacroVintageCandidateProduct.model_validate(
            _rehash_row(product, "product_sha256", c.PHASE22_PRODUCT_HASH_DOMAIN)
        )


def test_boundary_registry_is_required_and_immutable() -> None:
    required = set(FamilyAMacroVintageCandidateInventoryAmendment.model_json_schema()["required"])
    assert set(c.PHASE22_BOUNDARY_VALUES) <= required
    with pytest.raises(TypeError):
        operator.setitem(  # type: ignore[call-overload]
            c.PHASE22_BOUNDARY_VALUES,
            "operational_source_product_composition_selected",
            True,
        )
