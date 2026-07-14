from __future__ import annotations

from decimal import Decimal
from uuid import UUID

import pytest
from fable5_backtester.contracts import (
    EvaluationRunCreateRequest,
    LabelSpecification,
    ResearchReturnStatus,
    SyntheticTrial,
    TrialStatus,
)
from fable5_backtester.synthetic import (
    REGISTERED_FIXTURE,
    REGISTERED_POLICY,
    build_synthetic_fixture,
    build_synthetic_policy,
    resolve_fixture,
    resolve_policy,
)
from fable5_data.contracts import (
    ConstituentDisposition,
    DataCapability,
    OhlcvBarPayload,
    UniverseMembershipPayload,
)
from fable5_data.synthetic import SyntheticPointInTimeAdapter
from pydantic import ValidationError


def _request_payload() -> dict[str, object]:
    return {
        "policy_id": REGISTERED_POLICY.policy_id,
        "policy_version": REGISTERED_POLICY.policy_version,
        "mapping_id": UUID("aaaaaaaa-aaaa-5aaa-8aaa-aaaaaaaaaaaa"),
        "snapshot_ids": (UUID("bbbbbbbb-bbbb-5bbb-8bbb-bbbbbbbbbbbb"),),
        "fixture_id": REGISTERED_FIXTURE.fixture_id,
    }


def test_registered_policy_and_fixture_rebuild_byte_identically() -> None:
    rebuilt_policy = build_synthetic_policy()
    rebuilt_fixture = build_synthetic_fixture()

    assert rebuilt_policy == REGISTERED_POLICY
    assert rebuilt_policy.model_dump_json().encode() == REGISTERED_POLICY.model_dump_json().encode()
    assert rebuilt_policy.policy_sha256 == REGISTERED_POLICY.policy_sha256
    assert rebuilt_policy.policy_canonical_json == REGISTERED_POLICY.policy_canonical_json
    assert rebuilt_fixture == REGISTERED_FIXTURE
    assert (
        rebuilt_fixture.model_dump_json().encode() == REGISTERED_FIXTURE.model_dump_json().encode()
    )
    assert rebuilt_fixture.fixture_sha256 == REGISTERED_FIXTURE.fixture_sha256


def test_resolvers_fail_closed_for_missing_policy_or_fixture() -> None:
    assert (
        resolve_policy(REGISTERED_POLICY.policy_id, REGISTERED_POLICY.policy_version)
        is REGISTERED_POLICY
    )
    assert resolve_fixture(REGISTERED_FIXTURE.fixture_id) is REGISTERED_FIXTURE
    assert resolve_policy(UUID("ffffffff-ffff-5fff-8fff-ffffffffffff"), 1) is None
    assert resolve_policy(REGISTERED_POLICY.policy_id, REGISTERED_POLICY.policy_version + 1) is None
    assert resolve_fixture("unregistered-phase5-fixture") is None


@pytest.mark.parametrize("missing_field", ["policy_id", "policy_version", "fixture_id"])
def test_run_request_requires_server_resolvable_policy_and_fixture_identities(
    missing_field: str,
) -> None:
    payload = _request_payload()
    payload.pop(missing_field)
    with pytest.raises(ValidationError) as raised:
        EvaluationRunCreateRequest.model_validate(payload)
    assert raised.value.errors()[0]["type"] == "missing"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("metrics", {"sharpe": "9.9"}),
        ("results", {"promotion": "pass"}),
        ("artifact_sha256", "f" * 64),
        ("thresholds", {"dsr_min": "0"}),
        ("created_at_utc", "2026-07-13T00:00:00Z"),
        ("research_allocation_units", "100"),
        ("promotion_state", "PASS_RESEARCH"),
    ],
)
def test_run_request_refuses_client_authoritative_fields(field: str, value: object) -> None:
    payload = {**_request_payload(), field: value}
    with pytest.raises(ValidationError) as raised:
        EvaluationRunCreateRequest.model_validate(payload)

    error = raised.value.errors()[0]
    assert error["type"] == "extra_forbidden"
    assert error["loc"] == (field,)


def test_registered_artifacts_are_synthetic_only_and_complete() -> None:
    assert REGISTERED_POLICY.synthetic_fixture_policy is True
    assert REGISTERED_POLICY.signal_specification.llm_generated is False
    assert REGISTERED_POLICY.signal_specification.output_semantics == "research_score_only"
    assert REGISTERED_POLICY.required_snapshot_capabilities
    assert REGISTERED_POLICY.audit.required_fields
    assert REGISTERED_FIXTURE.synthetic is True
    assert REGISTERED_FIXTURE.no_real_performance_claimed is True
    assert REGISTERED_FIXTURE.samples and REGISTERED_FIXTURE.trials
    assert any("not real performance" in warning for warning in REGISTERED_FIXTURE.warnings)


def test_only_explicit_supported_missing_and_no_trade_policies_validate() -> None:
    payload = REGISTERED_POLICY.label_specification.model_dump(mode="python")
    payload["missing_return_policy"] = "silently_drop_missing_returns"
    with pytest.raises(ValidationError):
        LabelSpecification.model_validate(payload)

    payload = REGISTERED_POLICY.label_specification.model_dump(mode="python")
    payload["no_trade_return_policy"] = "charge_costs_on_implicit_zero"
    with pytest.raises(ValidationError):
        LabelSpecification.model_validate(payload)


def test_trial_return_statuses_are_aligned_and_value_constrained() -> None:
    original = REGISTERED_FIXTURE.trials[0]
    payload = original.model_dump(mode="python")
    payload["return_statuses"] = (
        ResearchReturnStatus.NO_TRADE,
        *original.return_statuses[1:],
    )
    with pytest.raises(ValidationError, match="no-trade trial returns must be explicit zeros"):
        SyntheticTrial.model_validate(payload)

    payload = original.model_dump(mode="python")
    payload["return_statuses"] = original.return_statuses[:-1]
    with pytest.raises(ValidationError, match="aligned values, statuses, and timestamps"):
        SyntheticTrial.model_validate(payload)


def test_no_return_trial_requires_an_explicit_missing_common_calendar_and_reason() -> None:
    original = REGISTERED_FIXTURE.trials[0]
    payload = original.model_dump(mode="python")
    payload.update(
        {
            "trial_key": "missing-reference",
            "status": TrialStatus.NO_RETURN,
            "net_returns": tuple(None for _ in original.net_returns),
            "return_statuses": tuple(
                ResearchReturnStatus.MISSING for _ in original.return_statuses
            ),
            "failure_reason": "synthetic common-calendar outcomes unavailable",
        }
    )
    validated = SyntheticTrial.model_validate(payload)
    assert validated.status is TrialStatus.NO_RETURN
    assert set(validated.return_statuses) == {ResearchReturnStatus.MISSING}

    payload["failure_reason"] = None
    with pytest.raises(ValidationError, match="no-return trials require a reason"):
        SyntheticTrial.model_validate(payload)


def test_registered_fixture_binds_every_sample_to_exact_phase4_source_evidence() -> None:
    assert (
        REGISTERED_POLICY.feature_specification.source_observation_binding_rule
        == "phase5-exact-snapshot-constituent-value-v1"
    )
    expectations = {
        item.key.capability: item for item in REGISTERED_FIXTURE.source_observation_expectations
    }
    expectation = expectations[DataCapability.OHLCV]
    membership_expectation = expectations[DataCapability.UNIVERSE_MEMBERSHIP]
    adapter = SyntheticPointInTimeAdapter()
    phase4_observations = adapter.fetch(DataCapability.OHLCV).batch.normalized_observations
    membership_observations = adapter.fetch(
        DataCapability.UNIVERSE_MEMBERSHIP
    ).batch.normalized_observations

    assert len(REGISTERED_FIXTURE.source_observation_expectations) == 2
    assert len(phase4_observations) == 1
    assert len(membership_observations) == 2
    assert expectation.normalized_observation == phase4_observations[0]
    assert membership_expectation.normalized_observation in membership_observations
    assert all(
        item.required_disposition is ConstituentDisposition.INCLUDED_AS_OF
        for item in expectations.values()
    )
    assert tuple(
        (
            binding.source_payload_field,
            binding.sample_field,
            binding.multiplier,
        )
        for binding in expectation.value_bindings
    ) == (
        ("open", "reference_price", Decimal("1")),
        ("volume", "daily_adv_units", Decimal("0.1")),
    )
    assert all(
        sample.source_observation_keys
        == tuple(item.key for item in REGISTERED_FIXTURE.source_observation_expectations)
        for sample in REGISTERED_FIXTURE.samples
    )
    source_payload = expectation.normalized_observation.payload
    assert isinstance(source_payload, OhlcvBarPayload)
    source_open = source_payload.open
    assert all(
        sample.feature_derivation.source_observation_key == expectation.key
        and sample.feature_derivation.source_payload_field == "open"
        and source_open * sample.feature_derivation.multiplier
        == sample.feature_derivation.derived_feature_value
        == sample.feature_value
        and sample.synthetic_ledger_value_rule == "deterministic-synthetic-research-ledger-input-v1"
        for sample in REGISTERED_FIXTURE.samples
    )
    membership_payload = membership_expectation.normalized_observation.payload
    assert isinstance(membership_payload, UniverseMembershipPayload)
    assert membership_payload.status.value == "included"
    assert all(
        sample.universe_membership is not None
        and sample.universe_membership.membership_id
        == str(membership_expectation.key.normalized_observation_id)
        and sample.universe_membership.universe_id == membership_payload.universe_id
        for sample in REGISTERED_FIXTURE.samples
    )


def test_sample_contract_rejects_feature_value_not_matching_frozen_derivation() -> None:
    original = REGISTERED_FIXTURE.samples[0]
    payload = original.model_dump(mode="python")
    payload["feature_value"] = original.feature_value + Decimal("0.0001")

    with pytest.raises(
        ValidationError,
        match="sample feature value must match its frozen source derivation",
    ):
        type(original).model_validate(payload)
