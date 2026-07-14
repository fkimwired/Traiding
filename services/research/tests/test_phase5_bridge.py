from __future__ import annotations

import inspect
from datetime import UTC, datetime
from decimal import Decimal, localcontext
from uuid import UUID

import pytest
from fable5_backtester.canonical import domain_sha256
from fable5_backtester.contracts import (
    PHASE6_SOURCE_FEATURE_DERIVATION_FORMULA,
    PHASE6_SOURCE_FEATURE_DERIVATION_HASH_DOMAIN,
    PHASE6_SOURCE_FEATURE_DERIVATION_SCHEMA_VERSION,
    GateCode,
    SourceFeatureDerivation,
    SourceObservationKey,
)
from fable5_backtester.synthetic import REGISTERED_POLICY
from fable5_data.canonical import canonicalize
from fable5_data.contracts import AUTHORIZED_CAPABILITIES, DataCapability
from fable5_mapping.models import CanonicalFamily
from fable5_research import phase5 as phase5_module
from fable5_research.contracts import ResearchConfigurationId
from fable5_research.phase5 import (
    build_phase5_policy,
    configuration_family,
    configuration_is_cost_failure,
    configuration_is_crash_failure,
)

ORIGIN = datetime(2024, 1, 3, tzinfo=UTC)
CAPABILITIES = {
    family: tuple(sorted(capabilities, key=str))
    for family, capabilities in AUTHORIZED_CAPABILITIES.items()
}


@pytest.mark.parametrize("configuration_id", tuple(ResearchConfigurationId))
def test_every_phase6_fixture_builds_a_complete_frozen_phase5_policy(
    configuration_id: ResearchConfigurationId,
) -> None:
    family = configuration_family(configuration_id)
    policy = build_phase5_policy(
        configuration_id=configuration_id,
        capabilities=CAPABILITIES[family],
        origin=ORIGIN,
    )

    assert policy.strategy_family is family
    assert policy.required_snapshot_capabilities == CAPABILITIES[family]
    assert policy.signal_specification.definition
    assert policy.signal_specification.forecast_horizon
    assert policy.feature_specification.source_fields
    assert policy.label_specification.forecast_horizon
    assert policy.costs.fee_schedule_id
    assert policy.costs.slippage_model_id
    assert policy.walk_forward.outer_fold_count >= 2
    assert policy.walk_forward.inner_fold_count >= 2
    assert policy.walk_forward.purge_rule == "label_interval_intersection_v1"
    assert policy.walk_forward.final_confirmation_start_utc < (
        policy.walk_forward.final_confirmation_end_utc
    )
    assert policy.risk.max_gross_exposure > Decimal("0")
    assert policy.audit.required_fields
    assert policy.synthetic_fixture_policy is True
    assert policy.policy_sha256 != REGISTERED_POLICY.policy_sha256


def test_phase6_failure_variants_are_server_owned_and_do_not_change_gate_vocabulary() -> None:
    assert tuple(GateCode) == (
        GateCode.DATA_PIT,
        GateCode.CV_CHRONOLOGY,
        GateCode.PREPROCESSING,
        GateCode.TRIAL_REGISTRY,
        GateCode.DSR,
        GateCode.PBO,
        GateCode.COST_STRESS,
        GateCode.LEAKAGE,
        GateCode.SAMPLE_ADEQUACY,
        GateCode.REGIME,
        GateCode.RISK_LIMITS,
        GateCode.REPRODUCIBILITY,
    )
    assert {item for item in ResearchConfigurationId if configuration_is_cost_failure(item)} == {
        ResearchConfigurationId.A_FAIL,
    }
    assert {item for item in ResearchConfigurationId if configuration_is_crash_failure(item)} == {
        ResearchConfigurationId.B_FAIL
    }

    pass_policy = build_phase5_policy(
        configuration_id=ResearchConfigurationId.A_PASS,
        capabilities=CAPABILITIES[CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING],
        origin=ORIGIN,
    )
    fail_policy = build_phase5_policy(
        configuration_id=ResearchConfigurationId.A_FAIL,
        capabilities=CAPABILITIES[CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING],
        origin=ORIGIN,
    )
    assert fail_policy.stress.min_stressed_net_pnl > pass_policy.stress.min_stressed_net_pnl


def test_family_c_phase5_bridge_uses_an_exact_numeric_source_anchor() -> None:
    policy = build_phase5_policy(
        configuration_id=ResearchConfigurationId.C_PASS,
        capabilities=CAPABILITIES[CanonicalFamily.C_OFFICIAL_EVENT_TEXT_OVERLAY],
        origin=ORIGIN,
    )

    assert policy.feature_specification.source_fields == ("ohlcv.open",)
    assert policy.feature_specification.encoding_policy == (
        "numeric-identity-no-categorical-encoding-v1"
    )
    rendered = policy.model_dump_json()
    for forbidden in (
        '"buy_sell_call"',
        '"position_size"',
        '"promotion_outcome"',
        '"execution_instruction"',
    ):
        assert forbidden not in rendered


def test_descriptive_baseline_comparisons_are_absent_from_phase5_selection() -> None:
    selection_source = inspect.getsource(phase5_module._trials)
    assert "baseline_comparisons" not in selection_source
    assert "inner_evidence" in selection_source
    assert "outer_evidence" in selection_source


def test_phase6_numeric_source_derivation_survives_jsonb_canonical_round_trip() -> None:
    source_value = Decimal("31.2345")
    derived_value = Decimal("0.123456789012")
    with localcontext() as context:
        context.prec = 80
        multiplier = (derived_value / source_value).quantize(Decimal("1e-24"))
    content = {
        "schema_version": PHASE6_SOURCE_FEATURE_DERIVATION_SCHEMA_VERSION,
        "formula_id": PHASE6_SOURCE_FEATURE_DERIVATION_FORMULA,
        "source_observation_key": SourceObservationKey(
            capability=DataCapability.OHLCV,
            normalized_observation_id=UUID("77777777-7777-5777-8777-777777777777"),
        ),
        "source_payload_field": "open",
        "multiplier": multiplier,
        "derived_feature_value": derived_value,
    }
    derivation = SourceFeatureDerivation.model_validate(
        {
            **content,
            "derivation_sha256": domain_sha256(
                PHASE6_SOURCE_FEATURE_DERIVATION_HASH_DOMAIN,
                content,
            ),
        }
    )

    reloaded = SourceFeatureDerivation.model_validate(canonicalize(derivation))

    assert reloaded == derivation
    assert reloaded.derive_from_source_value(source_value) == derived_value
