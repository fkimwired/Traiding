"""Strict hash-bound contracts for deterministic local paper simulation."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from fable5_paper.canonical import (
    PHASE10_ARTIFACT_HASH_DOMAIN,
    PHASE10_CHECK_HASH_DOMAIN,
    PHASE10_CONFIGURATION_HASH_DOMAIN,
    PHASE10_CONFIGURATION_NAMESPACE,
    PHASE10_CURRENTNESS_HASH_DOMAIN,
    PHASE10_LEDGER_HASH_DOMAIN,
    PHASE10_LEDGER_NAMESPACE,
    PHASE10_MOCK_OBSERVATION_HASH_DOMAIN,
    PHASE10_MOCK_SNAPSHOT_HASH_DOMAIN,
    PHASE10_OBSERVATION_NAMESPACE,
    PHASE10_REQUEST_HASH_DOMAIN,
    PHASE10_REVALIDATION_HASH_DOMAIN,
    PHASE10_REVALIDATION_NAMESPACE,
    PHASE10_RUN_NAMESPACE,
    PHASE10_SNAPSHOT_NAMESPACE,
    domain_sha256,
    identity,
)

SHA256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
GitSHA = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]
Identifier = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=256,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:/-]*$",
    ),
]
IdempotencyKey = Annotated[
    str,
    StringConstraints(
        min_length=8,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
    ),
]

PHASE10_CONFIGURATION_ID: Literal["phase10-a-local-mock-qa-v1"] = "phase10-a-local-mock-qa-v1"
PHASE10_CONFIGURATION_SCHEMA_VERSION: Literal["phase10-local-simulation-configuration-v1"] = (
    "phase10-local-simulation-configuration-v1"
)
PHASE10_CHECK_SCHEMA_VERSION: Literal["phase10-local-simulation-check-v1"] = (
    "phase10-local-simulation-check-v1"
)
PHASE10_LEDGER_SCHEMA_VERSION: Literal["phase10-local-simulation-ledger-v1"] = (
    "phase10-local-simulation-ledger-v1"
)
PHASE10_REVALIDATION_SCHEMA_VERSION: Literal["phase10-local-simulation-revalidation-v1"] = (
    "phase10-local-simulation-revalidation-v1"
)
PHASE10_ARTIFACT_SCHEMA_VERSION: Literal["phase10-local-paper-simulation-v1"] = (
    "phase10-local-paper-simulation-v1"
)
PHASE10_DISCLAIMER: Literal[
    "Deterministic synthetic local paper simulation only; no external routing, live trading, "
    "real performance claim, or personalized investment advice."
] = (
    "Deterministic synthetic local paper simulation only; no external routing, live trading, "
    "real performance claim, or personalized investment advice."
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")


def _utc(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value.astimezone(UTC)


def _finite(*values: Decimal | None) -> bool:
    return all(value is None or value.is_finite() for value in values)


def _ordered_unique(values: tuple[object, ...], field_name: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{field_name} must be unique and ordered")


class PaperSimulationOutcome(StrEnum):
    SIMULATED_COMPLETE = "SIMULATED_COMPLETE"
    BLOCKED = "BLOCKED"


class PaperCheckStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"
    UNCOMPUTABLE = "UNCOMPUTABLE"


class PaperCheckCode(StrEnum):
    SOURCE_APPROVAL_EXACT = "SOURCE_APPROVAL_EXACT"
    TRANSITION_APPROVAL_FRESH = "TRANSITION_APPROVAL_FRESH"
    RESEARCH_PREREQUISITES_COMPLETE = "RESEARCH_PREREQUISITES_COMPLETE"
    SIMULATION_CONFIGURATION_EXACT = "SIMULATION_CONFIGURATION_EXACT"
    RISK_CONTEXT_EXACT = "RISK_CONTEXT_EXACT"
    COST_SLIPPAGE_COMPLETE = "COST_SLIPPAGE_COMPLETE"
    LOCAL_BOUNDARY_ENFORCED = "LOCAL_BOUNDARY_ENFORCED"


PAPER_CHECK_ORDER: tuple[PaperCheckCode, ...] = tuple(PaperCheckCode)


class PaperSimulationCreateRequest(StrictModel):
    approval_assessment_id: UUID
    simulation_idempotency_key: IdempotencyKey


class PaperTransitionRevalidationProof(StrictModel):
    """Decision-time-bound proof of the fresh Phase 10 authority evaluation."""

    schema_version: Literal["phase10-local-simulation-revalidation-v1"] = (
        PHASE10_REVALIDATION_SCHEMA_VERSION
    )
    revalidation_proof_id: UUID
    revalidation_proof_sha256: SHA256
    simulation_idempotency_key: IdempotencyKey
    source_assessment_id: UUID
    source_assessment_artifact_sha256: SHA256
    transition_assessment_id: UUID
    transition_assessment_artifact_sha256: SHA256
    transition_currentness_state_sha256: SHA256
    transition_revocation_set_sha256: SHA256
    decision_time_utc: datetime
    phase10_code_version_git_sha: GitSHA

    @field_validator("decision_time_utc")
    @classmethod
    def normalize_decision_time(cls, value: datetime) -> datetime:
        return _utc(value, "revalidation decision time")

    @model_validator(mode="after")
    def validate_revalidation_proof(self) -> Self:
        payload = self.model_dump(
            mode="python",
            exclude={"revalidation_proof_id", "revalidation_proof_sha256"},
        )
        expected_hash = domain_sha256(PHASE10_REVALIDATION_HASH_DOMAIN, payload)
        if (
            self.revalidation_proof_sha256 != expected_hash
            or self.revalidation_proof_id != identity(PHASE10_REVALIDATION_NAMESPACE, expected_hash)
        ):
            raise ValueError("revalidation proof identity must bind its complete preimage")
        return self


def build_transition_revalidation_proof(
    *,
    request: PaperSimulationCreateRequest,
    source_assessment_artifact_sha256: str,
    transition_assessment_id: UUID,
    transition_assessment_artifact_sha256: str,
    transition_currentness_state_sha256: str,
    transition_revocation_set_sha256: str,
    decision_time_utc: datetime,
    phase10_code_version_git_sha: str,
) -> PaperTransitionRevalidationProof:
    payload = {
        "schema_version": PHASE10_REVALIDATION_SCHEMA_VERSION,
        "simulation_idempotency_key": request.simulation_idempotency_key,
        "source_assessment_id": request.approval_assessment_id,
        "source_assessment_artifact_sha256": source_assessment_artifact_sha256,
        "transition_assessment_id": transition_assessment_id,
        "transition_assessment_artifact_sha256": transition_assessment_artifact_sha256,
        "transition_currentness_state_sha256": transition_currentness_state_sha256,
        "transition_revocation_set_sha256": transition_revocation_set_sha256,
        "decision_time_utc": _utc(decision_time_utc, "revalidation decision time"),
        "phase10_code_version_git_sha": phase10_code_version_git_sha,
    }
    proof_sha256 = domain_sha256(PHASE10_REVALIDATION_HASH_DOMAIN, payload)
    return PaperTransitionRevalidationProof.model_validate(
        {
            **payload,
            "revalidation_proof_id": identity(PHASE10_REVALIDATION_NAMESPACE, proof_sha256),
            "revalidation_proof_sha256": proof_sha256,
        }
    )


class PaperSourceSnapshotReference(StrictModel):
    ordinal: int = Field(ge=1)
    snapshot_id: UUID
    snapshot_sha256: SHA256
    binding_sha256: SHA256
    capability: Identifier


class PaperSimulationConfiguration(StrictModel):
    schema_version: Literal["phase10-local-simulation-configuration-v1"] = (
        PHASE10_CONFIGURATION_SCHEMA_VERSION
    )
    configuration_id: Literal["phase10-a-local-mock-qa-v1"] = PHASE10_CONFIGURATION_ID
    configuration_instance_id: UUID
    configuration_sha256: SHA256
    research_run_id: UUID
    research_artifact_sha256: SHA256
    research_configuration_id: Identifier
    research_configuration_sha256: SHA256
    research_specification_sha256: SHA256
    research_snapshot_bundle_sha256: SHA256
    source_snapshot_bindings: tuple[PaperSourceSnapshotReference, ...] = Field(min_length=1)
    canonical_family: Identifier
    model_id: Literal["sector-relative-rank-linear-v1"] = "sector-relative-rank-linear-v1"
    signal_rule_id: Literal["phase6-a-score-positive-long-flat-v1"] = (
        "phase6-a-score-positive-long-flat-v1"
    )
    signal_definition_sha256: SHA256
    target_forecast_horizon: str = Field(min_length=1, max_length=256)
    required_capabilities: tuple[Identifier, ...] = Field(min_length=1)
    required_audit_fields: tuple[Identifier, ...] = Field(min_length=10)
    source_transaction_cost_model_id: Identifier
    source_slippage_model_id: Identifier
    local_cost_model_id: Literal["phase10-local-transparent-cost-v1"] = (
        "phase10-local-transparent-cost-v1"
    )
    local_slippage_model_id: Literal["phase10-local-transparent-slippage-v1"] = (
        "phase10-local-transparent-slippage-v1"
    )
    mock_snapshot_id: UUID
    mock_snapshot_sha256: SHA256
    mock_observation_id: UUID
    mock_observation_sha256: SHA256
    mock_entity_id: Literal["SYNTHETIC-ASSET-001"] = "SYNTHETIC-ASSET-001"
    mock_universe_id: Identifier
    observed_at_utc: datetime
    available_at_utc: datetime
    decision_time_utc: datetime
    synthetic_model_output: Decimal
    reference_price: Decimal = Field(gt=Decimal("0"))
    average_daily_volume: Decimal = Field(gt=Decimal("0"))
    volatility: Decimal = Field(ge=Decimal("0"))
    approved_proposed_notional: Decimal | None = Field(default=None, ge=Decimal("0"))
    requested_quantity: Decimal | None = Field(default=None, ge=Decimal("0"))
    starting_cash: Decimal = Field(gt=Decimal("0"))
    random_seed: int = Field(ge=0)
    raw_trial_count: int = Field(ge=0)
    effective_trial_count: Decimal = Field(ge=Decimal("0"))
    synthetic: Literal[True] = True
    local_mock_only: Literal[True] = True
    external_routing_absent: Literal[True] = True
    live_path_absent: Literal[True] = True
    llm_decision_role_absent: Literal[True] = True

    @field_validator("observed_at_utc", "available_at_utc", "decision_time_utc")
    @classmethod
    def normalize_times(cls, value: datetime, info: object) -> datetime:
        return _utc(value, getattr(info, "field_name", "configuration time"))

    @model_validator(mode="after")
    def validate_configuration(self) -> Self:
        if not _finite(
            self.synthetic_model_output,
            self.reference_price,
            self.average_daily_volume,
            self.volatility,
            self.approved_proposed_notional,
            self.requested_quantity,
            self.starting_cash,
            self.effective_trial_count,
        ):
            raise ValueError("simulation configuration decimals must be finite")
        if not self.observed_at_utc <= self.available_at_utc <= self.decision_time_utc:
            raise ValueError("mock data must be point-in-time available before the decision")
        if self.observed_at_utc != self.decision_time_utc - timedelta(seconds=2) or (
            self.available_at_utc != self.decision_time_utc - timedelta(seconds=1)
        ):
            raise ValueError("mock observation timing must match the sole Phase 10 fixture")
        if (
            self.research_configuration_id != "phase6-a-pass-v2"
            or self.canonical_family != "A_CROSS_SECTIONAL_EQUITY_RANKING"
            or self.synthetic_model_output != Decimal("0.25")
            or self.reference_price != Decimal("100.00")
            or self.average_daily_volume != Decimal("100000")
            or self.volatility != Decimal("0.20")
            or self.starting_cash != Decimal("1000000.00")
        ):
            raise ValueError("simulation configuration must match the sole server-owned fixture")
        if tuple(item.ordinal for item in self.source_snapshot_bindings) != tuple(
            range(1, len(self.source_snapshot_bindings) + 1)
        ):
            raise ValueError("source snapshot bindings must be contiguous")
        _ordered_unique(
            tuple(item.snapshot_id for item in self.source_snapshot_bindings), "snapshots"
        )
        _ordered_unique(self.required_capabilities, "required capabilities")
        _ordered_unique(self.required_audit_fields, "required audit fields")
        if (self.approved_proposed_notional is None) is not (self.requested_quantity is None):
            raise ValueError("risk notional and requested quantity must be jointly computable")
        if self.requested_quantity is not None and (
            self.requested_quantity * self.reference_price != self.approved_proposed_notional
        ):
            raise ValueError("requested quantity must exactly reconcile to approved risk notional")
        snapshot_payload = {
            "configuration_id": self.configuration_id,
            "research_run_id": self.research_run_id,
            "research_artifact_sha256": self.research_artifact_sha256,
            "observed_at_utc": self.observed_at_utc,
            "available_at_utc": self.available_at_utc,
            "entity_id": self.mock_entity_id,
            "universe_id": self.mock_universe_id,
            "reference_price": self.reference_price,
            "average_daily_volume": self.average_daily_volume,
            "volatility": self.volatility,
            "synthetic": True,
            "local_mock_only": True,
        }
        expected_snapshot_hash = domain_sha256(PHASE10_MOCK_SNAPSHOT_HASH_DOMAIN, snapshot_payload)
        observation_payload = {
            **snapshot_payload,
            "mock_snapshot_id": self.mock_snapshot_id,
            "mock_snapshot_sha256": self.mock_snapshot_sha256,
            "synthetic_model_output": self.synthetic_model_output,
        }
        expected_observation_hash = domain_sha256(
            PHASE10_MOCK_OBSERVATION_HASH_DOMAIN, observation_payload
        )
        if (
            self.mock_snapshot_sha256 != expected_snapshot_hash
            or self.mock_snapshot_id != identity(PHASE10_SNAPSHOT_NAMESPACE, expected_snapshot_hash)
            or self.mock_observation_sha256 != expected_observation_hash
            or self.mock_observation_id
            != identity(PHASE10_OBSERVATION_NAMESPACE, expected_observation_hash)
        ):
            raise ValueError("mock snapshot and observation must bind the exact local fixture")
        payload = self.model_dump(
            mode="python", exclude={"configuration_instance_id", "configuration_sha256"}
        )
        expected_hash = domain_sha256(PHASE10_CONFIGURATION_HASH_DOMAIN, payload)
        if self.configuration_sha256 != expected_hash or self.configuration_instance_id != identity(
            PHASE10_CONFIGURATION_NAMESPACE, expected_hash
        ):
            raise ValueError("simulation configuration identity must bind its complete preimage")
        return self


class PaperSimulationCheck(StrictModel):
    schema_version: Literal["phase10-local-simulation-check-v1"] = PHASE10_CHECK_SCHEMA_VERSION
    ordinal: int = Field(ge=1)
    code: PaperCheckCode
    status: PaperCheckStatus
    reason_code: Identifier
    observed_value: str | None = Field(default=None, max_length=500)
    threshold_value: str | None = Field(default=None, max_length=500)
    evidence_sha256s: tuple[SHA256, ...] = Field(min_length=1)
    check_sha256: SHA256

    @model_validator(mode="after")
    def validate_check(self) -> Self:
        if self.evidence_sha256s != tuple(sorted(set(self.evidence_sha256s))):
            raise ValueError("check evidence hashes must be sorted and unique")
        payload = self.model_dump(mode="python", exclude={"check_sha256"})
        if self.check_sha256 != domain_sha256(PHASE10_CHECK_HASH_DOMAIN, payload):
            raise ValueError("simulation check hash must bind its complete preimage")
        return self


class PaperSimulationLedgerEntry(StrictModel):
    schema_version: Literal["phase10-local-simulation-ledger-v1"] = PHASE10_LEDGER_SCHEMA_VERSION
    simulation_run_id: UUID
    ordinal: Literal[1] = 1
    ledger_entry_id: UUID
    ledger_entry_sha256: SHA256
    mock_snapshot_id: UUID
    mock_snapshot_sha256: SHA256
    mock_observation_id: UUID
    mock_observation_sha256: SHA256
    entity_id: Literal["SYNTHETIC-ASSET-001"] = "SYNTHETIC-ASSET-001"
    universe_id: Identifier
    observed_at_utc: datetime
    available_at_utc: datetime
    decision_time_utc: datetime
    model_id: Literal["sector-relative-rank-linear-v1"] = "sector-relative-rank-linear-v1"
    signal_rule_id: Literal["phase6-a-score-positive-long-flat-v1"] = (
        "phase6-a-score-positive-long-flat-v1"
    )
    signal_value: Decimal
    signal_state: Literal["LONG"] = "LONG"
    simulated_side: Literal["BUY"] = "BUY"
    fill_status: Literal["SIMULATED_FILLED"] = "SIMULATED_FILLED"
    approved_proposed_notional: Decimal = Field(gt=Decimal("0"))
    requested_quantity: Decimal = Field(gt=Decimal("0"))
    filled_quantity: Decimal = Field(gt=Decimal("0"))
    rejected_quantity: Decimal = Field(ge=Decimal("0"))
    unfilled_quantity: Decimal = Field(ge=Decimal("0"))
    reference_price: Decimal = Field(gt=Decimal("0"))
    simulated_fill_price: Decimal = Field(gt=Decimal("0"))
    average_daily_volume: Decimal = Field(gt=Decimal("0"))
    volatility: Decimal = Field(ge=Decimal("0"))
    participation_rate: Decimal = Field(gt=Decimal("0"), le=Decimal("1"))
    commission_cost: Decimal = Field(ge=Decimal("0"))
    regulatory_fee_cost: Decimal = Field(ge=Decimal("0"))
    spread_cost: Decimal = Field(ge=Decimal("0"))
    impact_cost: Decimal = Field(ge=Decimal("0"))
    latency_cost: Decimal = Field(ge=Decimal("0"))
    borrow_cost: Decimal = Field(ge=Decimal("0"))
    capacity_cost: Decimal = Field(ge=Decimal("0"))
    total_cost: Decimal = Field(ge=Decimal("0"))
    position_quantity_before: Decimal = Field(ge=Decimal("0"))
    position_quantity_after: Decimal = Field(ge=Decimal("0"))
    cash_before: Decimal = Field(ge=Decimal("0"))
    cash_after: Decimal = Field(ge=Decimal("0"))
    source_transaction_cost_model_id: Identifier
    source_slippage_model_id: Identifier
    local_cost_model_id: Literal["phase10-local-transparent-cost-v1"] = (
        "phase10-local-transparent-cost-v1"
    )
    local_slippage_model_id: Literal["phase10-local-transparent-slippage-v1"] = (
        "phase10-local-transparent-slippage-v1"
    )
    synthetic: Literal[True] = True
    simulated_paper_only: Literal[True] = True
    local_mock_only: Literal[True] = True
    external_submission: Literal[False] = False
    live_path_absent: Literal[True] = True

    @field_validator("observed_at_utc", "available_at_utc", "decision_time_utc")
    @classmethod
    def normalize_times(cls, value: datetime, info: object) -> datetime:
        return _utc(value, getattr(info, "field_name", "ledger time"))

    @model_validator(mode="after")
    def validate_ledger(self) -> Self:
        decimals = tuple(
            value
            for name, value in self.__dict__.items()
            if isinstance(value, Decimal) and name != "ledger_entry_sha256"
        )
        if not all(value.is_finite() for value in decimals):
            raise ValueError("ledger decimals must be finite")
        if not self.observed_at_utc <= self.available_at_utc <= self.decision_time_utc:
            raise ValueError("ledger mock observation is not point-in-time safe")
        if self.filled_quantity + self.unfilled_quantity != self.requested_quantity:
            raise ValueError("filled and unfilled quantities must reconcile")
        if self.rejected_quantity != self.unfilled_quantity or self.unfilled_quantity != 0:
            raise ValueError("the Phase 10 filled fixture cannot retain rejected quantity")
        if self.approved_proposed_notional != self.requested_quantity * self.reference_price:
            raise ValueError("ledger notional must exactly match the approved risk context")
        if self.participation_rate != self.filled_quantity / self.average_daily_volume:
            raise ValueError("participation must derive from the deterministic mock volume")
        if self.position_quantity_after != self.position_quantity_before + self.filled_quantity:
            raise ValueError("simulated position quantity does not reconcile")
        if (
            self.signal_value != Decimal("0.25")
            or self.simulated_fill_price != self.reference_price + Decimal("0.04")
            or self.commission_cost != self.filled_quantity * Decimal("0.01")
            or self.regulatory_fee_cost != 0
            or self.spread_cost != self.filled_quantity * Decimal("0.02")
            or self.impact_cost != self.filled_quantity * Decimal("0.01")
            or self.latency_cost != self.filled_quantity * Decimal("0.01")
            or self.borrow_cost != 0
            or self.capacity_cost != 0
            or self.position_quantity_before != 0
        ):
            raise ValueError("ledger economics must match the sole deterministic local fixture")
        slippage_cost = self.spread_cost + self.impact_cost + self.latency_cost
        if (
            self.simulated_fill_price - self.reference_price
        ) * self.filled_quantity != slippage_cost:
            raise ValueError("fill-price slippage must reconcile to its exact components")
        expected_total = (
            self.commission_cost
            + self.regulatory_fee_cost
            + self.spread_cost
            + self.impact_cost
            + self.latency_cost
            + self.borrow_cost
            + self.capacity_cost
        )
        if self.total_cost != expected_total:
            raise ValueError("component costs must sum exactly to total cost")
        if self.cash_after != self.cash_before - self.approved_proposed_notional - self.total_cost:
            raise ValueError("simulated cash does not reconcile")
        payload = self.model_dump(mode="python", exclude={"ledger_entry_id", "ledger_entry_sha256"})
        expected_hash = domain_sha256(PHASE10_LEDGER_HASH_DOMAIN, payload)
        if self.ledger_entry_sha256 != expected_hash or self.ledger_entry_id != identity(
            PHASE10_LEDGER_NAMESPACE, expected_hash
        ):
            raise ValueError("ledger identity must bind its complete preimage")
        return self


def paper_currentness_sha256(
    *,
    source_assessment_sha256: str,
    transition_assessment_sha256: str,
    transition_currentness_state_sha256: str,
    transition_revocation_set_sha256: str,
    revalidation_proof_sha256: str,
) -> str:
    return domain_sha256(
        PHASE10_CURRENTNESS_HASH_DOMAIN,
        {
            "source_assessment_sha256": source_assessment_sha256,
            "transition_assessment_sha256": transition_assessment_sha256,
            "transition_currentness_state_sha256": transition_currentness_state_sha256,
            "transition_revocation_set_sha256": transition_revocation_set_sha256,
            "revalidation_proof_sha256": revalidation_proof_sha256,
        },
    )


def paper_request_fingerprint(
    *,
    request: PaperSimulationCreateRequest,
    source_assessment_sha256: str,
    transition_assessment_sha256: str,
    currentness_state_sha256: str,
    revalidation_proof_sha256: str,
    configuration_sha256: str,
    phase10_code_version_git_sha: str,
) -> str:
    return domain_sha256(
        PHASE10_REQUEST_HASH_DOMAIN,
        {
            "request": request,
            "source_assessment_sha256": source_assessment_sha256,
            "transition_assessment_sha256": transition_assessment_sha256,
            "currentness_state_sha256": currentness_state_sha256,
            "revalidation_proof_sha256": revalidation_proof_sha256,
            "configuration_sha256": configuration_sha256,
            "phase10_code_version_git_sha": phase10_code_version_git_sha,
        },
    )


class PaperSimulationArtifact(StrictModel):
    simulation_run_id: UUID
    artifact_schema_version: Literal["phase10-local-paper-simulation-v1"] = (
        PHASE10_ARTIFACT_SCHEMA_VERSION
    )
    artifact_sha256: SHA256
    request_fingerprint_sha256: SHA256
    currentness_state_sha256: SHA256
    simulation_idempotency_key: IdempotencyKey
    source_assessment_id: UUID
    source_assessment_artifact_sha256: SHA256
    transition_assessment_id: UUID
    transition_assessment_artifact_sha256: SHA256
    transition_currentness_state_sha256: SHA256
    transition_revocation_set_sha256: SHA256
    transition_revalidation_proof: PaperTransitionRevalidationProof
    research_run_id: UUID
    research_artifact_sha256: SHA256
    phase6_lineage_sha256: SHA256
    approval_policy_version_id: UUID
    approval_policy_sha256: SHA256
    approval_scope_version_id: UUID
    approval_scope_sha256: SHA256
    human_authorization_evidence_id: UUID
    authorization_sha256: SHA256
    risk_input_id: UUID
    risk_input_sha256: SHA256
    configuration: PaperSimulationConfiguration
    checks: tuple[PaperSimulationCheck, ...] = Field(min_length=len(PAPER_CHECK_ORDER))
    ledger_entries: tuple[PaperSimulationLedgerEntry, ...] = Field(max_length=1)
    outcome: PaperSimulationOutcome
    reason_codes: tuple[Identifier, ...] = Field(min_length=1)
    phase10_code_version_git_sha: GitSHA
    random_seed: int = Field(ge=0)
    raw_trial_count: int = Field(ge=0)
    effective_trial_count: Decimal = Field(ge=Decimal("0"))
    decision_time_utc: datetime
    created_at_utc: datetime
    synthetic: Literal[True] = True
    simulated_paper_only: Literal[True] = True
    local_mock_only: Literal[True] = True
    external_submission: Literal[False] = False
    external_routing_absent: Literal[True] = True
    live_path_absent: Literal[True] = True
    no_personalized_investment_advice: Literal[True] = True
    no_real_performance_claimed: Literal[True] = True
    disclaimer: Literal[
        "Deterministic synthetic local paper simulation only; no external routing, live trading, "
        "real performance claim, or personalized investment advice."
    ] = PHASE10_DISCLAIMER

    @field_validator("decision_time_utc", "created_at_utc")
    @classmethod
    def normalize_times(cls, value: datetime, info: object) -> datetime:
        return _utc(value, getattr(info, "field_name", "artifact time"))

    @model_validator(mode="after")
    def validate_artifact(self) -> Self:
        if not self.effective_trial_count.is_finite():
            raise ValueError("effective trial count must be finite")
        if self.configuration.research_run_id != self.research_run_id or (
            self.configuration.research_artifact_sha256 != self.research_artifact_sha256
        ):
            raise ValueError("simulation configuration must bind the exact research artifact")
        if (
            self.random_seed != self.configuration.random_seed
            or self.raw_trial_count != self.configuration.raw_trial_count
            or self.effective_trial_count != self.configuration.effective_trial_count
            or self.decision_time_utc != self.configuration.decision_time_utc
        ):
            raise ValueError("top-level audit fields must match the configuration")
        expected_currentness = paper_currentness_sha256(
            source_assessment_sha256=self.source_assessment_artifact_sha256,
            transition_assessment_sha256=self.transition_assessment_artifact_sha256,
            transition_currentness_state_sha256=self.transition_currentness_state_sha256,
            transition_revocation_set_sha256=self.transition_revocation_set_sha256,
            revalidation_proof_sha256=(
                self.transition_revalidation_proof.revalidation_proof_sha256
            ),
        )
        if self.currentness_state_sha256 != expected_currentness:
            raise ValueError("currentness hash must bind both approval states")
        proof = self.transition_revalidation_proof
        if (
            proof.simulation_idempotency_key != self.simulation_idempotency_key
            or proof.source_assessment_id != self.source_assessment_id
            or proof.source_assessment_artifact_sha256 != self.source_assessment_artifact_sha256
            or proof.transition_assessment_id != self.transition_assessment_id
            or proof.transition_assessment_artifact_sha256
            != self.transition_assessment_artifact_sha256
            or proof.transition_currentness_state_sha256 != self.transition_currentness_state_sha256
            or proof.transition_revocation_set_sha256 != self.transition_revocation_set_sha256
            or proof.decision_time_utc != self.decision_time_utc
            or proof.phase10_code_version_git_sha != self.phase10_code_version_git_sha
        ):
            raise ValueError("revalidation proof must bind the resolved Phase 10 decision")
        request = PaperSimulationCreateRequest(
            approval_assessment_id=self.source_assessment_id,
            simulation_idempotency_key=self.simulation_idempotency_key,
        )
        expected_fingerprint = paper_request_fingerprint(
            request=request,
            source_assessment_sha256=self.source_assessment_artifact_sha256,
            transition_assessment_sha256=self.transition_assessment_artifact_sha256,
            currentness_state_sha256=self.currentness_state_sha256,
            revalidation_proof_sha256=proof.revalidation_proof_sha256,
            configuration_sha256=self.configuration.configuration_sha256,
            phase10_code_version_git_sha=self.phase10_code_version_git_sha,
        )
        if (
            self.request_fingerprint_sha256 != expected_fingerprint
            or self.simulation_run_id != identity(PHASE10_RUN_NAMESPACE, expected_fingerprint)
        ):
            raise ValueError("simulation identity must derive from the resolved immutable request")
        if (
            tuple(item.ordinal for item in self.checks)
            != tuple(range(1, len(PAPER_CHECK_ORDER) + 1))
            or tuple(item.code for item in self.checks) != PAPER_CHECK_ORDER
        ):
            raise ValueError("simulation must persist the exact ordered Phase 10 checks")
        if proof.revalidation_proof_sha256 not in self.checks[1].evidence_sha256s:
            raise ValueError("fresh-transition check must bind the revalidation proof")
        all_pass = all(item.status is PaperCheckStatus.PASS for item in self.checks)
        if self.outcome is PaperSimulationOutcome.SIMULATED_COMPLETE:
            if not all_pass or len(self.ledger_entries) != 1:
                raise ValueError("completed simulation requires all checks and one ledger entry")
            if self.reason_codes != ("all_simulation_checks_passed",):
                raise ValueError("completed simulation reason code is not canonical")
        else:
            if all_pass or self.ledger_entries:
                raise ValueError("blocked simulation requires a non-pass check and no ledger")
            expected_reasons = tuple(
                sorted(
                    {
                        item.reason_code
                        for item in self.checks
                        if item.status is not PaperCheckStatus.PASS
                    }
                )
            )
            if self.reason_codes != expected_reasons:
                raise ValueError("blocked reason codes must derive from non-passing checks")
        configuration = self.configuration
        for item in self.ledger_entries:
            if item.simulation_run_id != self.simulation_run_id:
                raise ValueError("ledger entries must bind the simulation identity")
            if (
                item.mock_snapshot_id != configuration.mock_snapshot_id
                or item.mock_snapshot_sha256 != configuration.mock_snapshot_sha256
                or item.mock_observation_id != configuration.mock_observation_id
                or item.mock_observation_sha256 != configuration.mock_observation_sha256
                or item.entity_id != configuration.mock_entity_id
                or item.universe_id != configuration.mock_universe_id
                or item.observed_at_utc != configuration.observed_at_utc
                or item.available_at_utc != configuration.available_at_utc
                or item.decision_time_utc != configuration.decision_time_utc
                or item.model_id != configuration.model_id
                or item.signal_rule_id != configuration.signal_rule_id
                or item.signal_value != configuration.synthetic_model_output
                or item.approved_proposed_notional != configuration.approved_proposed_notional
                or item.requested_quantity != configuration.requested_quantity
                or item.reference_price != configuration.reference_price
                or item.average_daily_volume != configuration.average_daily_volume
                or item.volatility != configuration.volatility
                or item.cash_before != configuration.starting_cash
                or item.source_transaction_cost_model_id
                != configuration.source_transaction_cost_model_id
                or item.source_slippage_model_id != configuration.source_slippage_model_id
                or item.local_cost_model_id != configuration.local_cost_model_id
                or item.local_slippage_model_id != configuration.local_slippage_model_id
            ):
                raise ValueError("ledger must bind the exact simulation configuration and risk")
        payload = self.model_dump(
            mode="python",
            exclude={"simulation_run_id", "artifact_sha256", "created_at_utc"},
        )
        if self.artifact_sha256 != domain_sha256(PHASE10_ARTIFACT_HASH_DOMAIN, payload):
            raise ValueError("simulation artifact hash must bind its complete timeless payload")
        return self


class PaperSimulationSummary(StrictModel):
    simulation_run_id: UUID
    artifact_sha256: SHA256
    source_assessment_id: UUID
    transition_assessment_id: UUID
    configuration_id: Literal["phase10-a-local-mock-qa-v1"] = PHASE10_CONFIGURATION_ID
    outcome: PaperSimulationOutcome
    reason_codes: tuple[Identifier, ...]
    decision_time_utc: datetime
    created_at_utc: datetime
    synthetic: Literal[True] = True
    simulated_paper_only: Literal[True] = True
    local_mock_only: Literal[True] = True
    external_submission: Literal[False] = False
    live_path_absent: Literal[True] = True
    no_personalized_investment_advice: Literal[True] = True
    no_real_performance_claimed: Literal[True] = True

    @field_validator("decision_time_utc", "created_at_utc")
    @classmethod
    def normalize_times(cls, value: datetime, info: object) -> datetime:
        return _utc(value, getattr(info, "field_name", "summary time"))


def validate_code_git_sha(value: str | None) -> str:
    if value is None or re.fullmatch(r"[0-9a-f]{40}", value) is None:
        raise ValueError("phase10_code_version_git_sha must be a lowercase 40-character git SHA")
    return value


__all__ = [
    "PAPER_CHECK_ORDER",
    "PHASE10_ARTIFACT_SCHEMA_VERSION",
    "PHASE10_CONFIGURATION_ID",
    "PHASE10_DISCLAIMER",
    "PaperCheckCode",
    "PaperCheckStatus",
    "PaperSimulationArtifact",
    "PaperSimulationCheck",
    "PaperSimulationConfiguration",
    "PaperSimulationCreateRequest",
    "PaperSimulationLedgerEntry",
    "PaperSimulationOutcome",
    "PaperSimulationSummary",
    "PaperSourceSnapshotReference",
    "PaperTransitionRevalidationProof",
    "build_transition_revalidation_proof",
    "paper_currentness_sha256",
    "paper_request_fingerprint",
    "validate_code_git_sha",
]
