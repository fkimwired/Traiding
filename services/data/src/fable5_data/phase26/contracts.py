"""Strict hash-bound contracts for Phase 26."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from fable5_data.phase26 import canonical as c

SHA256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
GitSHA = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]
Code = Annotated[str, StringConstraints(pattern=r"^[A-Z0-9][A-Z0-9_]{2,127}$")]
Capability = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]{2,63}$")]
ClosedText = Annotated[str, StringConstraints(min_length=1, max_length=2400)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")


class Outcome(StrEnum):
    BLOCKED = "BLOCKED"


class DecisionState(StrEnum):
    OPERATIONAL_COMPOSITION_SELECTED = "OPERATIONAL_COMPOSITION_SELECTED"


class SelectedProduct(StrictModel):
    schema_version: str
    ordinal: int = Field(ge=1, le=3)
    product_code: Code
    provider: ClosedText
    source_ids: tuple[Code, ...]
    delivery_ids: tuple[Code, ...]
    assigned_capabilities: tuple[Capability, ...]
    accepted_candidate_product_sha256: SHA256
    current_rights_state: Code
    operationally_selected: bool
    acquisition_authorized: bool
    product_sha256: SHA256

    @model_validator(mode="after")
    def validate_row(self) -> Self:
        payload = self.model_dump(mode="python", exclude={"product_sha256"})
        if self.schema_version != c.PRODUCT_SCHEMA:
            raise ValueError("product schema mismatch")
        if self.product_sha256 != c.domain_sha256(c.PRODUCT_DOMAIN, payload):
            raise ValueError("product hash mismatch")
        if not self.operationally_selected or self.acquisition_authorized:
            raise ValueError("product selection boundary mismatch")
        return self


class CapabilityAssignment(StrictModel):
    schema_version: str
    ordinal: int = Field(ge=1, le=7)
    capability_code: Capability
    assigned_product_code: Code
    assignment_state: str
    assignment_sha256: SHA256

    @model_validator(mode="after")
    def validate_row(self) -> Self:
        payload = self.model_dump(mode="python", exclude={"assignment_sha256"})
        if self.schema_version != c.ASSIGNMENT_SCHEMA or self.assignment_state != "ASSIGNED":
            raise ValueError("assignment contract mismatch")
        if self.assignment_sha256 != c.domain_sha256(c.ASSIGNMENT_DOMAIN, payload):
            raise ValueError("assignment hash mismatch")
        return self


class PostSelectionDependency(StrictModel):
    schema_version: str
    ordinal: int = Field(ge=1, le=3)
    code: Code
    state: Code
    definition: ClosedText
    satisfied: bool
    dependency_sha256: SHA256

    @model_validator(mode="after")
    def validate_row(self) -> Self:
        payload = self.model_dump(mode="python", exclude={"dependency_sha256"})
        if self.schema_version != c.DEPENDENCY_SCHEMA or self.satisfied:
            raise ValueError("dependency contract mismatch")
        if self.dependency_sha256 != c.domain_sha256(c.DEPENDENCY_DOMAIN, payload):
            raise ValueError("dependency hash mismatch")
        return self


class DecisionGate(StrictModel):
    schema_version: str
    ordinal: int = Field(ge=1, le=6)
    code: Code
    state: str
    passed: bool
    gate_sha256: SHA256

    @model_validator(mode="after")
    def validate_row(self) -> Self:
        payload = self.model_dump(mode="python", exclude={"gate_sha256"})
        if self.schema_version != c.GATE_SCHEMA or self.state not in {"PASS", "BLOCKED"}:
            raise ValueError("gate contract mismatch")
        if (self.state == "PASS") is not self.passed:
            raise ValueError("gate state mismatch")
        if self.gate_sha256 != c.domain_sha256(c.GATE_DOMAIN, payload):
            raise ValueError("gate hash mismatch")
        return self


class Phase26Decision(StrictModel):
    schema_version: str
    artifact_id: UUID
    artifact_sha256: SHA256
    policy_id: str
    policy_sha256: SHA256
    source_snapshot_id: UUID
    source_snapshot_sha256: SHA256
    generation_git_sha: GitSHA
    random_seed: int
    trial_count: int
    generated_at_utc: datetime
    accepted_phase25_commit_sha: GitSHA
    accepted_phase25_tree_sha: GitSHA
    phase25_artifact_id: UUID
    phase25_artifact_sha256: SHA256
    phase25_artifact_file_sha256: SHA256
    phase21_artifact_sha256: SHA256
    phase22_product_sha256: SHA256
    family: str
    outcome: Outcome
    decision_state: DecisionState
    aggregate_conclusion: str
    block_reason: ClosedText
    capability_product_composition_id: Code
    source_ids: tuple[Code, ...]
    product_ids: tuple[Code, ...]
    delivery_ids: tuple[Code, ...]
    selection_scope: ClosedText
    selected_at_utc: datetime
    selected_by: Code
    selection_evidence_sha256: SHA256
    explicit_human_decision: bool
    single_closed_composition: bool
    operational_source_product_composition_selected: bool
    selected_products: tuple[SelectedProduct, ...]
    selected_products_manifest_sha256: SHA256
    capability_assignments: tuple[CapabilityAssignment, ...]
    capability_assignments_manifest_sha256: SHA256
    post_selection_dependencies: tuple[PostSelectionDependency, ...]
    post_selection_dependencies_manifest_sha256: SHA256
    decision_gates: tuple[DecisionGate, ...]
    decision_gates_manifest_sha256: SHA256
    acquisition_authorized: bool
    credentials_loaded: bool
    external_data_capture_authorized: bool
    live_path_absent: bool
    no_personalized_investment_advice: bool
    no_real_performance_claimed: bool
    order_submission_authorized: bool
    paper_only: bool
    performance_computed: bool
    production_adapter_activated: bool
    provider_observations_downloaded: bool
    provider_observations_persisted: bool
    research_executed: bool
    research_ingestion_authorized: bool
    runtime_network_disabled: bool
    strategy_promotion_authorized: bool

    @model_validator(mode="after")
    def validate_decision(self) -> Self:
        if self.schema_version != c.ARTIFACT_SCHEMA:
            raise ValueError("artifact schema mismatch")
        if self.policy_id != c.POLICY_ID or self.policy_sha256 != c.POLICY_SHA256:
            raise ValueError("policy mismatch")
        if tuple(row.product_code for row in self.selected_products) != c.PRODUCT_IDS:
            raise ValueError("selected products mismatch")
        expected_assignments = tuple(
            (row.capability_code, row.assigned_product_code) for row in self.capability_assignments
        )
        if expected_assignments != c.CAPABILITY_ROWS:
            raise ValueError("capability assignments mismatch")
        if self.source_ids != c.SOURCE_IDS or self.product_ids != c.PRODUCT_IDS:
            raise ValueError("composition identifiers mismatch")
        if self.delivery_ids != c.DELIVERY_IDS or self.selection_scope != c.SELECTION_SCOPE:
            raise ValueError("delivery or selection scope mismatch")
        dumped = self.model_dump(mode="python")
        for field, value in c.BOUNDARY_VALUES.items():
            if dumped[field] != value:
                raise ValueError(f"boundary mismatch: {field}")
        payload = self.model_dump(mode="python", exclude={"artifact_id", "artifact_sha256"})
        expected_hash = c.domain_sha256(c.ARTIFACT_DOMAIN, payload)
        if self.artifact_sha256 != expected_hash:
            raise ValueError("artifact hash mismatch")
        if self.artifact_id != c.uuid_from_sha256(c.ARTIFACT_NAMESPACE, expected_hash):
            raise ValueError("artifact id mismatch")
        return self
