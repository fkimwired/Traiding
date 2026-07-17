"""Server-owned deterministic Phase 10 mock configuration and ledger builders."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from fable5_research.contracts import ResearchRunArtifact, frozen_trial_allocation
from fable5_risk.contracts import ApprovalRiskInput, Phase6ApprovalLineage

from fable5_paper.canonical import (
    PHASE10_CONFIGURATION_HASH_DOMAIN,
    PHASE10_CONFIGURATION_NAMESPACE,
    PHASE10_LEDGER_HASH_DOMAIN,
    PHASE10_LEDGER_NAMESPACE,
    PHASE10_MOCK_OBSERVATION_HASH_DOMAIN,
    PHASE10_MOCK_SNAPSHOT_HASH_DOMAIN,
    PHASE10_OBSERVATION_NAMESPACE,
    PHASE10_SNAPSHOT_NAMESPACE,
    domain_sha256,
    identity,
)
from fable5_paper.contracts import (
    PHASE10_CONFIGURATION_ID,
    PaperSimulationConfiguration,
    PaperSimulationLedgerEntry,
    PaperSourceSnapshotReference,
)

REFERENCE_PRICE = Decimal("100.00")
AVERAGE_DAILY_VOLUME = Decimal("100000")
SYNTHETIC_VOLATILITY = Decimal("0.20")
SYNTHETIC_MODEL_OUTPUT = Decimal("0.25")
STARTING_CASH = Decimal("1000000.00")


def build_simulation_configuration(
    *,
    research: ResearchRunArtifact,
    lineage: Phase6ApprovalLineage,
    risk_input: ApprovalRiskInput,
    decision_time_utc: object,
) -> PaperSimulationConfiguration:
    """Resolve the sole local fixture from immutable research and risk evidence."""

    from datetime import datetime

    if not isinstance(decision_time_utc, datetime):
        raise TypeError("decision_time_utc must be a datetime")
    observed_at_utc = decision_time_utc - timedelta(seconds=2)
    available_at_utc = decision_time_utc - timedelta(seconds=1)
    snapshot_payload = {
        "configuration_id": PHASE10_CONFIGURATION_ID,
        "research_run_id": research.run_id,
        "research_artifact_sha256": research.artifact_sha256,
        "observed_at_utc": observed_at_utc,
        "available_at_utc": available_at_utc,
        "entity_id": "SYNTHETIC-ASSET-001",
        "universe_id": risk_input.universe_id,
        "reference_price": REFERENCE_PRICE,
        "average_daily_volume": AVERAGE_DAILY_VOLUME,
        "volatility": SYNTHETIC_VOLATILITY,
        "synthetic": True,
        "local_mock_only": True,
    }
    mock_snapshot_sha256 = domain_sha256(PHASE10_MOCK_SNAPSHOT_HASH_DOMAIN, snapshot_payload)
    mock_snapshot_id = identity(PHASE10_SNAPSHOT_NAMESPACE, mock_snapshot_sha256)
    observation_payload = {
        **snapshot_payload,
        "mock_snapshot_id": mock_snapshot_id,
        "mock_snapshot_sha256": mock_snapshot_sha256,
        "synthetic_model_output": SYNTHETIC_MODEL_OUTPUT,
    }
    mock_observation_sha256 = domain_sha256(
        PHASE10_MOCK_OBSERVATION_HASH_DOMAIN, observation_payload
    )
    mock_observation_id = identity(PHASE10_OBSERVATION_NAMESPACE, mock_observation_sha256)
    proposed_notional = risk_input.proposed_notional
    requested_quantity = None if proposed_notional is None else proposed_notional / REFERENCE_PRICE
    source_snapshots = tuple(
        PaperSourceSnapshotReference(
            ordinal=item.ordinal,
            snapshot_id=item.snapshot_id,
            snapshot_sha256=item.snapshot_sha256,
            binding_sha256=item.binding_sha256,
            capability=item.capability.value,
        )
        for item in research.snapshot_bindings
    )
    payload = {
        "schema_version": "phase10-local-simulation-configuration-v1",
        "configuration_id": PHASE10_CONFIGURATION_ID,
        "research_run_id": research.run_id,
        "research_artifact_sha256": research.artifact_sha256,
        "research_configuration_id": research.configuration_id.value,
        "research_configuration_sha256": research.configuration_sha256,
        "research_specification_sha256": research.specification.specification_sha256,
        "research_snapshot_bundle_sha256": research.snapshot_bundle_sha256,
        "source_snapshot_bindings": source_snapshots,
        "canonical_family": research.family.value,
        "model_id": "sector-relative-rank-linear-v1",
        "signal_rule_id": "phase6-a-score-positive-long-flat-v1",
        "signal_definition_sha256": domain_sha256(
            "phase10-source-signal-definition-v1", research.specification.signal_definition
        ),
        "target_forecast_horizon": research.specification.target_forecast_horizon,
        "required_capabilities": tuple(
            item.value for item in research.specification.required_capabilities
        ),
        "required_audit_fields": research.specification.required_audit_fields,
        "source_transaction_cost_model_id": (research.specification.transaction_cost_model_id),
        "source_slippage_model_id": research.specification.slippage_model_id,
        "local_cost_model_id": "phase10-local-transparent-cost-v1",
        "local_slippage_model_id": "phase10-local-transparent-slippage-v1",
        "mock_snapshot_id": mock_snapshot_id,
        "mock_snapshot_sha256": mock_snapshot_sha256,
        "mock_observation_id": mock_observation_id,
        "mock_observation_sha256": mock_observation_sha256,
        "mock_entity_id": "SYNTHETIC-ASSET-001",
        "mock_universe_id": risk_input.universe_id,
        "observed_at_utc": observed_at_utc,
        "available_at_utc": available_at_utc,
        "decision_time_utc": decision_time_utc,
        "synthetic_model_output": SYNTHETIC_MODEL_OUTPUT,
        "reference_price": REFERENCE_PRICE,
        "average_daily_volume": AVERAGE_DAILY_VOLUME,
        "volatility": SYNTHETIC_VOLATILITY,
        "approved_proposed_notional": proposed_notional,
        "requested_quantity": requested_quantity,
        "starting_cash": STARTING_CASH,
        "random_seed": lineage.random_seed,
        "raw_trial_count": lineage.raw_trial_count,
        "effective_trial_count": lineage.effective_trial_count,
        "synthetic": True,
        "local_mock_only": True,
        "external_routing_absent": True,
        "live_path_absent": True,
        "llm_decision_role_absent": True,
    }
    configuration_sha256 = domain_sha256(PHASE10_CONFIGURATION_HASH_DOMAIN, payload)
    return PaperSimulationConfiguration.model_validate(
        {
            **payload,
            "configuration_instance_id": identity(
                PHASE10_CONFIGURATION_NAMESPACE, configuration_sha256
            ),
            "configuration_sha256": configuration_sha256,
        }
    )


def build_simulation_ledger(
    *,
    simulation_run_id: object,
    configuration: PaperSimulationConfiguration,
) -> PaperSimulationLedgerEntry:
    """Build the single transparent local fill and exact cash/position reconciliation."""

    from uuid import UUID

    if not isinstance(simulation_run_id, UUID):
        raise TypeError("simulation_run_id must be a UUID")
    if configuration.approved_proposed_notional is None or configuration.requested_quantity is None:
        raise ValueError("a local ledger requires a computable approved notional")
    allocation, rule_id = frozen_trial_allocation(
        trial_key="candidate",
        model_id=configuration.model_id,
        sample_id="phase10-local-mock-observation-v1",
        model_output=configuration.synthetic_model_output,
    )
    if allocation != Decimal("1") or rule_id != configuration.signal_rule_id:
        raise ValueError("the frozen research allocation rule did not resolve the long fixture")
    quantity = configuration.requested_quantity
    spread_cost = quantity * Decimal("0.02")
    impact_cost = quantity * Decimal("0.01")
    latency_cost = quantity * Decimal("0.01")
    commission_cost = quantity * Decimal("0.01")
    regulatory_fee_cost = Decimal("0")
    borrow_cost = Decimal("0")
    capacity_cost = Decimal("0")
    total_cost = (
        commission_cost
        + regulatory_fee_cost
        + spread_cost
        + impact_cost
        + latency_cost
        + borrow_cost
        + capacity_cost
    )
    payload = {
        "schema_version": "phase10-local-simulation-ledger-v1",
        "simulation_run_id": simulation_run_id,
        "ordinal": 1,
        "mock_snapshot_id": configuration.mock_snapshot_id,
        "mock_snapshot_sha256": configuration.mock_snapshot_sha256,
        "mock_observation_id": configuration.mock_observation_id,
        "mock_observation_sha256": configuration.mock_observation_sha256,
        "entity_id": configuration.mock_entity_id,
        "universe_id": configuration.mock_universe_id,
        "observed_at_utc": configuration.observed_at_utc,
        "available_at_utc": configuration.available_at_utc,
        "decision_time_utc": configuration.decision_time_utc,
        "model_id": configuration.model_id,
        "signal_rule_id": configuration.signal_rule_id,
        "signal_value": configuration.synthetic_model_output,
        "signal_state": "LONG",
        "simulated_side": "BUY",
        "fill_status": "SIMULATED_FILLED",
        "approved_proposed_notional": configuration.approved_proposed_notional,
        "requested_quantity": quantity,
        "filled_quantity": quantity,
        "rejected_quantity": Decimal("0"),
        "unfilled_quantity": Decimal("0"),
        "reference_price": configuration.reference_price,
        "simulated_fill_price": configuration.reference_price + Decimal("0.04"),
        "average_daily_volume": configuration.average_daily_volume,
        "volatility": configuration.volatility,
        "participation_rate": quantity / configuration.average_daily_volume,
        "commission_cost": commission_cost,
        "regulatory_fee_cost": regulatory_fee_cost,
        "spread_cost": spread_cost,
        "impact_cost": impact_cost,
        "latency_cost": latency_cost,
        "borrow_cost": borrow_cost,
        "capacity_cost": capacity_cost,
        "total_cost": total_cost,
        "position_quantity_before": Decimal("0"),
        "position_quantity_after": quantity,
        "cash_before": configuration.starting_cash,
        "cash_after": (
            configuration.starting_cash - configuration.approved_proposed_notional - total_cost
        ),
        "source_transaction_cost_model_id": (configuration.source_transaction_cost_model_id),
        "source_slippage_model_id": configuration.source_slippage_model_id,
        "local_cost_model_id": configuration.local_cost_model_id,
        "local_slippage_model_id": configuration.local_slippage_model_id,
        "synthetic": True,
        "simulated_paper_only": True,
        "local_mock_only": True,
        "external_submission": False,
        "live_path_absent": True,
    }
    ledger_sha256 = domain_sha256(PHASE10_LEDGER_HASH_DOMAIN, payload)
    return PaperSimulationLedgerEntry.model_validate(
        {
            **payload,
            "ledger_entry_id": identity(PHASE10_LEDGER_NAMESPACE, ledger_sha256),
            "ledger_entry_sha256": ledger_sha256,
        }
    )


__all__ = ["build_simulation_configuration", "build_simulation_ledger"]
