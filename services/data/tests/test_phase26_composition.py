from __future__ import annotations

import pytest
from fable5_data.phase26 import canonical as c
from fable5_data.phase26.composition import build_phase26_decision
from fable5_data.phase26.contracts import Phase26Decision
from pydantic import ValidationError


def test_phase26_selects_one_closed_complete_composition_but_not_acquisition() -> None:
    artifact = build_phase26_decision()
    assert artifact.decision_state.value == "OPERATIONAL_COMPOSITION_SELECTED"
    assert artifact.operational_source_product_composition_selected
    assert artifact.capability_product_composition_id == c.COMPOSITION_ID
    assert artifact.product_ids == c.PRODUCT_IDS
    assert artifact.source_ids == c.SOURCE_IDS
    assert artifact.delivery_ids == c.DELIVERY_IDS
    assert len(artifact.selected_products) == 3
    assert len(artifact.capability_assignments) == 7
    assert {row.capability_code for row in artifact.capability_assignments} == {
        row[0] for row in c.CAPABILITY_ROWS
    }
    assert all(row.operationally_selected for row in artifact.selected_products)
    assert not artifact.acquisition_authorized
    assert not artifact.production_adapter_activated
    assert not artifact.provider_observations_downloaded
    assert not artifact.provider_observations_persisted
    assert artifact.paper_only and artifact.live_path_absent


def test_phase26_keeps_rights_schema_and_pit_dependencies_blocked() -> None:
    artifact = build_phase26_decision()
    assert artifact.outcome.value == "BLOCKED"
    assert all(not row.satisfied for row in artifact.post_selection_dependencies)
    gates = {row.code: row.passed for row in artifact.decision_gates}
    assert gates["EXPLICIT_HUMAN_COMPOSITION_DECISION"]
    assert gates["SINGLE_CLOSED_COMPOSITION"]
    assert gates["COMPLETE_CAPABILITY_ASSIGNMENT"]
    assert gates["INDEPENDENT_DECISION_EVIDENCE"]
    assert not gates["CURRENT_RIGHTS_FOR_EXACT_COMPOSITION"]
    assert not gates["POST_SELECTION_REVALIDATION"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("acquisition_authorized", True),
        ("production_adapter_activated", True),
        ("live_path_absent", False),
        ("paper_only", False),
        ("selection_evidence_sha256", "0" * 64),
    ],
)
def test_phase26_rejects_authority_and_identity_tampering(field: str, value: object) -> None:
    payload = build_phase26_decision().model_dump(mode="json")
    payload[field] = value
    with pytest.raises(ValidationError):
        Phase26Decision.model_validate(payload)


def test_phase26_contract_is_extra_forbid_and_frozen() -> None:
    artifact = build_phase26_decision()
    with pytest.raises(ValidationError):
        Phase26Decision.model_validate({**artifact.model_dump(mode="json"), "unknown": True})
    with pytest.raises(ValidationError):
        artifact.acquisition_authorized = True  # type: ignore[misc]
