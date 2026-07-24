from __future__ import annotations

import json
from copy import deepcopy
from datetime import UTC, datetime

import pytest
from fable5_paper.phase28.adapters import DeterministicMockObservationAdapter
from fable5_paper.phase28.canonical import (
    PHASE28_EXACT_USE_REVIEW_SHA256,
    PHASE28_NOTICE,
    PHASE28_UNIVERSE,
    domain_sha256,
    evidence_id,
    observation_snapshot_id,
)
from fable5_paper.phase28.contracts import (
    AlpacaIexObservationEvidence,
    InspectionStatus,
    ObservationInspectionEvidence,
    ObservationSourceKind,
)
from fable5_paper.phase28.workflow import Phase28ObservationWorkflow
from pydantic import ValidationError

GIT_SHA = "e9f4d99d8c1bc5c5b4ac615cf3592d5f0ae3113e"
OBSERVED_AT = datetime(2024, 1, 2, 15, 0, 1, tzinfo=UTC)


def _artifact() -> AlpacaIexObservationEvidence:
    return Phase28ObservationWorkflow(
        adapter=DeterministicMockObservationAdapter(),
        code_version_git_sha=GIT_SHA,
        clock=lambda: OBSERVED_AT,
    ).run()


def _rehash_artifact_payload(payload: dict[str, object]) -> dict[str, object]:
    inspections = payload["inspections"]
    assert isinstance(inspections, (list, tuple))
    for inspection in inspections:
        assert isinstance(inspection, dict)
        inspection_payload = {
            key: value for key, value in inspection.items() if key != "inspection_sha256"
        }
        inspection["inspection_sha256"] = domain_sha256(
            "phase28-alpaca-iex-inspection-v1", inspection_payload
        )
    snapshot_payload = {
        "source_kind": payload["source_kind"],
        "observed_at_utc": payload["observed_at_utc"],
        "inspection_sha256s": tuple(inspection["inspection_sha256"] for inspection in inspections),
        "config_sha256": payload["config_sha256"],
    }
    snapshot_hash = domain_sha256("phase28-sanitized-observation-snapshot-v1", snapshot_payload)
    payload["observation_snapshot_sha256"] = snapshot_hash
    payload["observation_snapshot_id"] = observation_snapshot_id(snapshot_hash)
    evidence_payload = {
        key: value
        for key, value in payload.items()
        if key not in {"evidence_id", "evidence_sha256"}
    }
    digest = domain_sha256("phase28-alpaca-iex-evidence-v1", evidence_payload)
    payload["evidence_sha256"] = digest
    payload["evidence_id"] = evidence_id(digest)
    return payload


def test_deterministic_artifact_has_all_three_outcomes_and_required_authority() -> None:
    artifact = _artifact()

    assert artifact.universe == PHASE28_UNIVERSE
    assert [(item.symbol, item.outcome.value) for item in artifact.symbols] == [
        ("AAPL", "MATCH"),
        ("MSFT", "NO_MATCH"),
        ("SPY", "INSUFFICIENT_DATA"),
    ]
    assert artifact.forecast_horizon == "NONE_OBSERVATION_ONLY"
    assert artifact.notice == PHASE28_NOTICE
    assert artifact.exact_use_review_sha256 == PHASE28_EXACT_USE_REVIEW_SHA256
    assert artifact.observation_snapshot_kind == "SANITIZED_OBSERVATION_METADATA_ONLY"
    assert artifact.authority.model_dump() == {
        "provider_payload_persisted": False,
        "raw_price_persisted": False,
        "research_qualified": False,
        "strategy_execution_eligible": False,
        "order_submission_authorized": False,
        "live_path_absent": True,
        "simulated_paper_only": True,
        "no_personalized_investment_advice": True,
        "no_real_performance_claimed": True,
    }


def test_deterministic_artifact_is_byte_stable_and_contains_no_raw_market_fields() -> None:
    first = _artifact().model_dump(mode="json")
    second = _artifact().model_dump(mode="json")
    rendered = json.dumps(first, sort_keys=True, separators=(",", ":"))

    assert first == second
    for forbidden_key in (
        '"ap":',
        '"bp":',
        '"ask_price":',
        '"bid_price":',
        '"open_price":',
        '"close_price":',
        '"provider_body":',
        '"headers":',
        '"request_id":',
    ):
        assert forbidden_key not in rendered


@pytest.mark.parametrize(
    ("path", "replacement"),
    [
        (("inspections", 0, "endpoint_sha256"), "0" * 64),
        (("inspections", 0, "inspection_sha256"), "0" * 64),
        (("symbols", 0, "predicates", 0, "predicate_sha256"), "0" * 64),
        (("symbols", 0, "symbol_observation_sha256"), "0" * 64),
        (("observation_snapshot_sha256",), "0" * 64),
        (("evidence_sha256",), "0" * 64),
    ],
)
def test_every_nested_identity_rejects_tampering(
    path: tuple[str | int, ...], replacement: str
) -> None:
    payload: object = deepcopy(_artifact().model_dump(mode="python"))
    target = payload
    for key in path[:-1]:
        target = target[key]  # type: ignore[index]
    target[path[-1]] = replacement  # type: ignore[index]

    with pytest.raises(ValidationError):
        AlpacaIexObservationEvidence.model_validate(payload)


def test_contract_rejects_trade_instruction_shaped_extra_fields() -> None:
    payload = _artifact().model_dump(mode="python")
    payload["side"] = "BUY"
    payload["qty"] = "10"

    with pytest.raises(ValidationError):
        AlpacaIexObservationEvidence.model_validate(payload)


def test_artifact_timeline_cannot_precede_an_inspection() -> None:
    payload = _artifact().model_dump(mode="python")
    payload["observed_at_utc"] = datetime(2024, 1, 2, 14, 59, tzinfo=UTC)

    with pytest.raises(ValidationError):
        AlpacaIexObservationEvidence.model_validate(payload)


def test_external_inspection_cannot_start_after_exact_use_review_expiry() -> None:
    inspection = _artifact().inspections[0].model_dump(mode="python")
    inspection["external_request_performed"] = True
    inspection["request_started_at_utc"] = datetime(2026, 8, 1, tzinfo=UTC)
    inspection["request_completed_at_utc"] = datetime(2026, 8, 1, tzinfo=UTC)
    inspection_payload = {
        key: value for key, value in inspection.items() if key != "inspection_sha256"
    }
    inspection["inspection_sha256"] = domain_sha256(
        "phase28-alpaca-iex-inspection-v1", inspection_payload
    )

    with pytest.raises(ValidationError, match="started after exact-use review expiry"):
        ObservationInspectionEvidence.model_validate(inspection)


def test_non_observed_inspection_cannot_retain_sanitized_observation_hash() -> None:
    inspection = _artifact().inspections[0].model_dump(mode="python")
    inspection["status"] = InspectionStatus.BLOCKED
    inspection["failure_reason"] = "response_schema_blocked"
    inspection_payload = {
        key: value for key, value in inspection.items() if key != "inspection_sha256"
    }
    inspection["inspection_sha256"] = domain_sha256(
        "phase28-alpaca-iex-inspection-v1", inspection_payload
    )

    with pytest.raises(ValidationError, match="cannot carry an observation hash"):
        ObservationInspectionEvidence.model_validate(inspection)


def test_external_not_attempted_sequence_requires_a_prior_block() -> None:
    payload = _artifact().model_dump(mode="python")
    payload["source_kind"] = ObservationSourceKind.ALPACA_IEX_READ_ONLY
    payload["exact_use_review_confirmed_for_external_run"] = True
    for inspection in payload["inspections"]:
        inspection["status"] = InspectionStatus.NOT_ATTEMPTED
        inspection["external_request_performed"] = False
        inspection["http_status"] = None
        inspection["request_id_sha256"] = None
        inspection["response_sha256"] = None
        inspection["sanitized_observation_sha256"] = None
        inspection["failure_reason"] = "prior_inspection_blocked"

    with pytest.raises(ValidationError, match="unattempted before a block"):
        AlpacaIexObservationEvidence.model_validate(_rehash_artifact_payload(payload))


def test_external_classifications_require_observed_dependencies() -> None:
    payload = _artifact().model_dump(mode="python")
    payload["source_kind"] = ObservationSourceKind.ALPACA_IEX_READ_ONLY
    payload["exact_use_review_confirmed_for_external_run"] = True
    for index, inspection in enumerate(payload["inspections"]):
        inspection["status"] = (
            InspectionStatus.BLOCKED if index == 0 else InspectionStatus.NOT_ATTEMPTED
        )
        inspection["external_request_performed"] = False
        inspection["http_status"] = None
        inspection["request_id_sha256"] = None
        inspection["response_sha256"] = None
        inspection["sanitized_observation_sha256"] = None
        inspection["failure_reason"] = (
            "transport_unavailable" if index == 0 else "prior_inspection_blocked"
        )

    with pytest.raises(ValidationError, match="lacks an observed dependency"):
        AlpacaIexObservationEvidence.model_validate(_rehash_artifact_payload(payload))
