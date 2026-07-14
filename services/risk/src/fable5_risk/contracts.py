"""Strict contracts for Phase 7 approval and pre-order risk assessment."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Literal, Self
from uuid import UUID

from fable5_backtester.contracts import GateCode, PromotionState
from fable5_data.contracts import DataCapability
from fable5_mapping.models import CanonicalFamily
from fable5_research.canonical import PHASE6_SNAPSHOT_BINDING_HASH_DOMAIN
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from fable5_risk.canonical import (
    PHASE7_ASSESSMENT_ARTIFACT_HASH_DOMAIN,
    PHASE7_ASSESSMENT_NAMESPACE,
    PHASE7_ASSESSMENT_REQUEST_HASH_DOMAIN,
    PHASE7_AUTHORIZATION_HASH_DOMAIN,
    PHASE7_AUTHORIZATION_NAMESPACE,
    PHASE7_CHECK_HASH_DOMAIN,
    PHASE7_LINEAGE_HASH_DOMAIN,
    PHASE7_POLICY_HASH_DOMAIN,
    PHASE7_POLICY_NAMESPACE,
    PHASE7_REVOCATION_ARTIFACT_HASH_DOMAIN,
    PHASE7_REVOCATION_EVIDENCE_HASH_DOMAIN,
    PHASE7_REVOCATION_EVIDENCE_NAMESPACE,
    PHASE7_REVOCATION_NAMESPACE,
    PHASE7_REVOCATION_REQUEST_HASH_DOMAIN,
    PHASE7_RISK_INPUT_HASH_DOMAIN,
    PHASE7_RISK_INPUT_NAMESPACE,
    PHASE7_SCOPE_HASH_DOMAIN,
    PHASE7_SCOPE_NAMESPACE,
    domain_sha256,
    identity,
)

SHA256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
GitSHA = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]
Identifier = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")]

PHASE7_APPROVAL_POLICY_SCHEMA_VERSION: Literal["phase7-approval-policy-v1"] = (
    "phase7-approval-policy-v1"
)
PHASE7_APPROVAL_SCOPE_SCHEMA_VERSION: Literal["phase7-approval-scope-v1"] = (
    "phase7-approval-scope-v1"
)
PHASE7_AUTHORIZATION_SCHEMA_VERSION: Literal["phase7-human-authorization-evidence-v1"] = (
    "phase7-human-authorization-evidence-v1"
)
PHASE7_RISK_INPUT_SCHEMA_VERSION: Literal["phase7-approval-risk-input-v1"] = (
    "phase7-approval-risk-input-v1"
)
PHASE7_LINEAGE_SCHEMA_VERSION: Literal["phase7-phase6-approval-lineage-v1"] = (
    "phase7-phase6-approval-lineage-v1"
)
PHASE7_ASSESSMENT_SCHEMA_VERSION: Literal["phase7-approval-assessment-v1"] = (
    "phase7-approval-assessment-v1"
)
PHASE7_REVOCATION_EVIDENCE_SCHEMA_VERSION: Literal["phase7-revocation-evidence-profile-v1"] = (
    "phase7-revocation-evidence-profile-v1"
)
PHASE7_REVOCATION_SCHEMA_VERSION: Literal["phase7-authorization-revocation-v1"] = (
    "phase7-authorization-revocation-v1"
)
PHASE7_DISCLAIMER: Literal[
    "Synthetic simulated-paper governance evidence only; no order, execution readiness, "
    "real performance claim, or investment advice."
] = (
    "Synthetic simulated-paper governance evidence only; no order, execution readiness, real "
    "performance claim, or investment advice."
)


def _utc(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value.astimezone(UTC)


def _finite(value: Decimal | None, field_name: str) -> Decimal | None:
    if value is not None and not value.is_finite():
        raise ValueError(f"{field_name} must be finite")
    return value


def _sorted_unique(values: tuple[object, ...], field_name: str) -> None:
    rendered = tuple(str(value) for value in values)
    if rendered != tuple(sorted(rendered)):
        raise ValueError(f"{field_name} must be canonically sorted")
    if len(rendered) != len(set(rendered)):
        raise ValueError(f"{field_name} must be unique")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")


class ApprovalAssessmentOutcome(StrEnum):
    APPROVED_PAPER = "APPROVED_PAPER"
    FAIL_REJECT = "FAIL_REJECT"


class CheckStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNCOMPUTABLE = "UNCOMPUTABLE"
    BLOCKED = "BLOCKED"


class ApprovalCheckCode(StrEnum):
    RESEARCH_PASS = "RESEARCH_PASS"
    PHASE6_LINEAGE_COMPLETE = "PHASE6_LINEAGE_COMPLETE"
    POLICY_CURRENT = "POLICY_CURRENT"
    POLICY_MATCH = "POLICY_MATCH"
    SCOPE_CURRENT = "SCOPE_CURRENT"
    SCOPE_MATCH = "SCOPE_MATCH"
    AUTHORIZATION_CURRENT = "AUTHORIZATION_CURRENT"
    AUTHORIZATION_MATCH = "AUTHORIZATION_MATCH"
    REVOCATION_CLEAR = "REVOCATION_CLEAR"
    RISK_INPUT_FRESH = "RISK_INPUT_FRESH"
    GLOBAL_CONTROL_CLEAR = "GLOBAL_CONTROL_CLEAR"
    STRATEGY_CONTROL_CLEAR = "STRATEGY_CONTROL_CLEAR"
    DATA_QUALITY_CONTROL_CLEAR = "DATA_QUALITY_CONTROL_CLEAR"
    MARKET_CALENDAR_OPEN = "MARKET_CALENDAR_OPEN"
    DUPLICATE_CONTEXT_CLEAR = "DUPLICATE_CONTEXT_CLEAR"
    NOTIONAL_LIMIT = "NOTIONAL_LIMIT"
    GROSS_EXPOSURE_LIMIT = "GROSS_EXPOSURE_LIMIT"
    NET_EXPOSURE_LIMIT = "NET_EXPOSURE_LIMIT"
    SECTOR_EXPOSURE_LIMIT = "SECTOR_EXPOSURE_LIMIT"
    CONCENTRATION_LIMIT = "CONCENTRATION_LIMIT"
    LIQUIDITY_MINIMUM = "LIQUIDITY_MINIMUM"
    TURNOVER_LIMIT = "TURNOVER_LIMIT"
    VOLATILITY_LIMIT = "VOLATILITY_LIMIT"
    DAILY_LOSS_LIMIT = "DAILY_LOSS_LIMIT"
    DRAWDOWN_LIMIT = "DRAWDOWN_LIMIT"


APPROVAL_CHECK_ORDER: tuple[ApprovalCheckCode, ...] = tuple(ApprovalCheckCode)


class ApprovalAssessmentCreateRequest(StrictModel):
    research_run_id: UUID
    approval_policy_version_id: UUID
    approval_scope_version_id: UUID
    human_authorization_evidence_id: UUID
    risk_input_id: UUID


class ApprovalRevocationCreateRequest(StrictModel):
    human_authorization_evidence_id: UUID
    revocation_evidence_id: UUID


class ApprovalPolicy(StrictModel):
    approval_policy_version_id: UUID
    schema_version: Literal["phase7-approval-policy-v1"] = PHASE7_APPROVAL_POLICY_SCHEMA_VERSION
    policy_id: Identifier
    policy_version: int = Field(ge=1)
    policy_sha256: SHA256
    valid_from_utc: datetime
    expires_at_utc: datetime
    authorization_max_age_seconds: int = Field(ge=1)
    risk_input_max_age_seconds: int = Field(ge=1)
    required_check_codes: tuple[ApprovalCheckCode, ...] = APPROVAL_CHECK_ORDER
    max_notional: Decimal = Field(ge=0)
    max_gross_exposure: Decimal = Field(ge=0)
    max_abs_net_exposure: Decimal = Field(ge=0)
    max_sector_exposure: Decimal = Field(ge=0)
    max_concentration: Decimal = Field(ge=0)
    min_liquidity: Decimal = Field(ge=0)
    max_turnover: Decimal = Field(ge=0)
    max_volatility: Decimal = Field(ge=0)
    max_daily_loss: Decimal = Field(ge=0)
    max_drawdown: Decimal = Field(ge=0)
    synthetic: Literal[True] = True

    @field_validator("valid_from_utc", "expires_at_utc")
    @classmethod
    def normalize_times(cls, value: datetime, info: object) -> datetime:
        return _utc(value, getattr(info, "field_name", "policy time"))

    @model_validator(mode="after")
    def validate_policy(self) -> Self:
        if self.valid_from_utc >= self.expires_at_utc:
            raise ValueError("approval policy interval must be nonempty")
        if self.required_check_codes != APPROVAL_CHECK_ORDER:
            raise ValueError("approval policy must require the exact ordered Phase 7 checks")
        payload = self.model_dump(
            mode="python", exclude={"approval_policy_version_id", "policy_sha256"}
        )
        expected = domain_sha256(PHASE7_POLICY_HASH_DOMAIN, payload)
        if self.policy_sha256 != expected or self.approval_policy_version_id != identity(
            PHASE7_POLICY_NAMESPACE, expected
        ):
            raise ValueError("approval policy identity must bind its complete immutable payload")
        return self


class ApprovalScope(StrictModel):
    approval_scope_version_id: UUID
    schema_version: Literal["phase7-approval-scope-v1"] = PHASE7_APPROVAL_SCOPE_SCHEMA_VERSION
    scope_id: Identifier
    scope_version: int = Field(ge=1)
    scope_sha256: SHA256
    research_run_id: UUID
    research_artifact_sha256: SHA256
    approval_policy_version_id: UUID
    permitted_universe_ids: tuple[Identifier, ...] = Field(min_length=1)
    max_notional: Decimal = Field(ge=0)
    valid_from_utc: datetime
    expires_at_utc: datetime
    synthetic: Literal[True] = True

    @field_validator("valid_from_utc", "expires_at_utc")
    @classmethod
    def normalize_times(cls, value: datetime, info: object) -> datetime:
        return _utc(value, getattr(info, "field_name", "scope time"))

    @model_validator(mode="after")
    def validate_scope(self) -> Self:
        if self.valid_from_utc >= self.expires_at_utc:
            raise ValueError("approval scope interval must be nonempty")
        _sorted_unique(self.permitted_universe_ids, "permitted universe ids")
        payload = self.model_dump(
            mode="python", exclude={"approval_scope_version_id", "scope_sha256"}
        )
        expected = domain_sha256(PHASE7_SCOPE_HASH_DOMAIN, payload)
        if self.scope_sha256 != expected or self.approval_scope_version_id != identity(
            PHASE7_SCOPE_NAMESPACE, expected
        ):
            raise ValueError("approval scope identity must bind its complete immutable payload")
        return self


class HumanAuthorizationEvidence(StrictModel):
    human_authorization_evidence_id: UUID
    schema_version: Literal["phase7-human-authorization-evidence-v1"] = (
        PHASE7_AUTHORIZATION_SCHEMA_VERSION
    )
    authorization_sha256: SHA256
    research_run_id: UUID
    research_artifact_sha256: SHA256
    approval_policy_version_id: UUID
    approval_scope_version_id: UUID
    authorized_by: Identifier
    authorized_role: Literal["paper_risk_reviewer"] = "paper_risk_reviewer"
    rationale: str = Field(min_length=1, max_length=2000)
    authorized_at_utc: datetime
    review_at_utc: datetime
    expires_at_utc: datetime
    human_controlled: Literal[True] = True
    synthetic: Literal[True] = True

    @field_validator("authorized_at_utc", "review_at_utc", "expires_at_utc")
    @classmethod
    def normalize_times(cls, value: datetime, info: object) -> datetime:
        return _utc(value, getattr(info, "field_name", "authorization time"))

    @model_validator(mode="after")
    def validate_authorization(self) -> Self:
        if not (self.authorized_at_utc < self.review_at_utc <= self.expires_at_utc):
            raise ValueError("authorization review and expiry interval must be ordered")
        payload = self.model_dump(
            mode="python",
            exclude={"human_authorization_evidence_id", "authorization_sha256"},
        )
        expected = domain_sha256(PHASE7_AUTHORIZATION_HASH_DOMAIN, payload)
        if (
            self.authorization_sha256 != expected
            or self.human_authorization_evidence_id
            != identity(PHASE7_AUTHORIZATION_NAMESPACE, expected)
        ):
            raise ValueError("authorization identity must bind its complete immutable payload")
        return self


class ApprovalRiskInput(StrictModel):
    risk_input_id: UUID
    schema_version: Literal["phase7-approval-risk-input-v1"] = PHASE7_RISK_INPUT_SCHEMA_VERSION
    risk_input_sha256: SHA256
    research_run_id: UUID
    research_artifact_sha256: SHA256
    approval_policy_version_id: UUID
    approval_scope_version_id: UUID
    universe_id: Identifier
    observed_at_utc: datetime
    global_control_clear: bool | None
    strategy_control_clear: bool | None
    data_quality_control_clear: bool | None
    market_calendar_open: bool | None
    duplicate_context_clear: bool | None
    proposed_notional: Decimal | None = Field(default=None, ge=0)
    gross_exposure: Decimal | None = Field(default=None, ge=0)
    net_exposure: Decimal | None = None
    sector_exposure: Decimal | None = Field(default=None, ge=0)
    concentration: Decimal | None = Field(default=None, ge=0)
    available_liquidity: Decimal | None = Field(default=None, ge=0)
    turnover: Decimal | None = Field(default=None, ge=0)
    volatility: Decimal | None = Field(default=None, ge=0)
    daily_loss: Decimal | None = Field(default=None, ge=0)
    drawdown: Decimal | None = Field(default=None, ge=0)
    synthetic: Literal[True] = True

    @field_validator("observed_at_utc")
    @classmethod
    def normalize_observed_at(cls, value: datetime) -> datetime:
        return _utc(value, "observed_at_utc")

    @field_validator(
        "proposed_notional",
        "gross_exposure",
        "net_exposure",
        "sector_exposure",
        "concentration",
        "available_liquidity",
        "turnover",
        "volatility",
        "daily_loss",
        "drawdown",
    )
    @classmethod
    def validate_finite(cls, value: Decimal | None, info: object) -> Decimal | None:
        return _finite(value, getattr(info, "field_name", "risk input"))

    @model_validator(mode="after")
    def validate_risk_input(self) -> Self:
        payload = self.model_dump(mode="python", exclude={"risk_input_id", "risk_input_sha256"})
        expected = domain_sha256(PHASE7_RISK_INPUT_HASH_DOMAIN, payload)
        if self.risk_input_sha256 != expected or self.risk_input_id != identity(
            PHASE7_RISK_INPUT_NAMESPACE, expected
        ):
            raise ValueError("risk input identity must bind its complete immutable payload")
        return self


class RevocationEvidenceProfile(StrictModel):
    revocation_evidence_id: UUID
    schema_version: Literal["phase7-revocation-evidence-profile-v1"] = (
        PHASE7_REVOCATION_EVIDENCE_SCHEMA_VERSION
    )
    revocation_evidence_sha256: SHA256
    revoked_by: Identifier
    reason: str = Field(min_length=1, max_length=2000)
    effective_at_utc: datetime
    human_controlled: Literal[True] = True
    synthetic: Literal[True] = True

    @field_validator("effective_at_utc")
    @classmethod
    def normalize_effective_at(cls, value: datetime) -> datetime:
        return _utc(value, "effective_at_utc")

    @model_validator(mode="after")
    def validate_profile(self) -> Self:
        payload = self.model_dump(
            mode="python", exclude={"revocation_evidence_id", "revocation_evidence_sha256"}
        )
        expected = domain_sha256(PHASE7_REVOCATION_EVIDENCE_HASH_DOMAIN, payload)
        if self.revocation_evidence_sha256 != expected or self.revocation_evidence_id != identity(
            PHASE7_REVOCATION_EVIDENCE_NAMESPACE, expected
        ):
            raise ValueError("revocation evidence identity must bind its immutable profile")
        return self


class Phase6SnapshotBindingLineage(StrictModel):
    ordinal: int = Field(ge=1)
    snapshot_id: UUID
    snapshot_sha256: SHA256
    capability: DataCapability
    binding_sha256: SHA256
    mapping_id: UUID
    mapping_input_sha256: SHA256
    as_of_utc: datetime
    quality_status: Identifier

    @field_validator("as_of_utc")
    @classmethod
    def normalize_as_of(cls, value: datetime) -> datetime:
        return _utc(value, "as_of_utc")

    @model_validator(mode="after")
    def validate_binding(self) -> Self:
        payload = self.model_dump(mode="python", exclude={"binding_sha256"})
        if self.binding_sha256 != domain_sha256(PHASE6_SNAPSHOT_BINDING_HASH_DOMAIN, payload):
            raise ValueError("Phase 6 snapshot binding hash must match its exact preimage")
        return self


class Phase6ApprovalLineage(StrictModel):
    schema_version: Literal["phase7-phase6-approval-lineage-v1"] = PHASE7_LINEAGE_SCHEMA_VERSION
    lineage_sha256: SHA256
    research_run_id: UUID
    research_artifact_sha256: SHA256
    research_request_fingerprint_sha256: SHA256
    research_configuration_id: Identifier
    research_configuration_sha256: SHA256
    research_status: Literal["completed", "blocked"]
    promotion_state: PromotionState
    mapping_id: UUID
    mapping_version: int = Field(ge=1)
    mapping_input_sha256: SHA256
    canonical_family: CanonicalFamily
    specification_sha256: SHA256
    research_pipeline_input_sha256: SHA256
    feature_lineage_sha256: SHA256
    snapshot_bundle_sha256: SHA256
    source_reproduction_audit_sha256: SHA256
    snapshot_bindings: tuple[Phase6SnapshotBindingLineage, ...] = Field(min_length=1)
    phase5_policy_id: UUID
    phase5_policy_version: int = Field(ge=1)
    phase5_policy_sha256: SHA256
    phase5_fixture_id: Identifier
    phase5_fixture_sha256: SHA256
    evaluation_report_id: UUID | None
    evaluation_report_sha256: SHA256 | None
    phase5_trial_set_sha256: SHA256 | None
    gate_codes: tuple[GateCode, ...]
    code_version_git_sha: GitSHA
    random_seed: int = Field(ge=0)
    raw_trial_count: int = Field(ge=0)
    effective_trial_count: Decimal = Field(ge=0)

    @model_validator(mode="after")
    def validate_lineage(self) -> Self:
        expected_ordinals = tuple(range(1, len(self.snapshot_bindings) + 1))
        if tuple(item.ordinal for item in self.snapshot_bindings) != expected_ordinals:
            raise ValueError("Phase 6 snapshot binding ordinals must be contiguous")
        if any(
            item.mapping_id != self.mapping_id
            or item.mapping_input_sha256 != self.mapping_input_sha256
            for item in self.snapshot_bindings
        ):
            raise ValueError("Phase 6 snapshot bindings must preserve mapping lineage")
        if self.research_status == "completed":
            if self.promotion_state in {
                PromotionState.BLOCKED_MISSING_POLICY,
                PromotionState.BLOCKED_UNCOMPUTABLE,
            }:
                raise ValueError("completed Phase 6 lineage cannot carry a blocked state")
            if self.gate_codes != tuple(GateCode):
                raise ValueError(
                    "completed Phase 6 lineage must preserve all Phase 5 gates in order"
                )
            if (
                self.evaluation_report_id is None
                or self.evaluation_report_sha256 is None
                or self.phase5_trial_set_sha256 is None
            ):
                raise ValueError("completed Phase 6 lineage requires exact Phase 5 report evidence")
        elif (
            self.gate_codes
            or self.evaluation_report_id is not None
            or self.evaluation_report_sha256 is not None
            or self.phase5_trial_set_sha256 is not None
        ):
            raise ValueError("blocked Phase 6 lineage cannot invent report or gate evidence")
        elif self.promotion_state not in {
            PromotionState.BLOCKED_MISSING_POLICY,
            PromotionState.BLOCKED_UNCOMPUTABLE,
        }:
            raise ValueError("blocked Phase 6 lineage must preserve a blocked promotion state")
        payload = self.model_dump(mode="python", exclude={"lineage_sha256"})
        if self.lineage_sha256 != domain_sha256(PHASE7_LINEAGE_HASH_DOMAIN, payload):
            raise ValueError("Phase 6 approval lineage hash must bind every copied field")
        return self


class ApprovalCheckResult(StrictModel):
    ordinal: int = Field(ge=1)
    code: ApprovalCheckCode
    status: CheckStatus
    reason_code: Identifier
    observed_value: str | None = Field(default=None, max_length=500)
    threshold_value: str | None = Field(default=None, max_length=500)
    evidence_sha256s: tuple[SHA256, ...] = Field(min_length=1)
    check_sha256: SHA256

    @model_validator(mode="after")
    def validate_check(self) -> Self:
        _sorted_unique(self.evidence_sha256s, "check evidence hashes")
        payload = self.model_dump(mode="python", exclude={"check_sha256"})
        if self.check_sha256 != domain_sha256(PHASE7_CHECK_HASH_DOMAIN, payload):
            raise ValueError("approval check hash must bind its complete evidence")
        return self


def assessment_request_fingerprint(
    *,
    request: ApprovalAssessmentCreateRequest,
    lineage_sha256: str,
    policy_sha256: str,
    scope_sha256: str,
    authorization_sha256: str,
    risk_input_sha256: str,
    revocation_set_sha256: str,
    currentness_state_sha256: str,
    phase7_code_version_git_sha: str,
) -> str:
    payload = {
        "request": request,
        "lineage_sha256": lineage_sha256,
        "policy_sha256": policy_sha256,
        "scope_sha256": scope_sha256,
        "authorization_sha256": authorization_sha256,
        "risk_input_sha256": risk_input_sha256,
        "revocation_set_sha256": revocation_set_sha256,
        "currentness_state_sha256": currentness_state_sha256,
        "phase7_code_version_git_sha": phase7_code_version_git_sha,
    }
    return domain_sha256(PHASE7_ASSESSMENT_REQUEST_HASH_DOMAIN, payload)


class ApprovalAssessmentArtifact(StrictModel):
    assessment_id: UUID
    artifact_schema_version: Literal["phase7-approval-assessment-v1"] = (
        PHASE7_ASSESSMENT_SCHEMA_VERSION
    )
    artifact_sha256: SHA256
    request_fingerprint_sha256: SHA256
    currentness_state_sha256: SHA256
    revocation_set_sha256: SHA256
    research_run_id: UUID
    approval_policy_version_id: UUID
    approval_scope_version_id: UUID
    human_authorization_evidence_id: UUID
    risk_input_id: UUID
    phase6_lineage: Phase6ApprovalLineage
    approval_policy_sha256: SHA256
    approval_scope_sha256: SHA256
    authorization_sha256: SHA256
    risk_input_sha256: SHA256
    revocation_ids: tuple[UUID, ...]
    checks: tuple[ApprovalCheckResult, ...] = Field(min_length=len(APPROVAL_CHECK_ORDER))
    outcome: ApprovalAssessmentOutcome
    reason_codes: tuple[Identifier, ...] = Field(min_length=1)
    phase7_code_version_git_sha: GitSHA
    created_at_utc: datetime
    synthetic: Literal[True] = True
    simulated_paper_only: Literal[True] = True
    execution_authorized: Literal[False] = False
    execution_ready: Literal[False] = False
    no_personalized_investment_advice: Literal[True] = True
    no_real_performance_claimed: Literal[True] = True
    disclaimer: Literal[
        "Synthetic simulated-paper governance evidence only; no order, execution readiness, "
        "real performance claim, or investment advice."
    ] = PHASE7_DISCLAIMER

    @field_validator("created_at_utc")
    @classmethod
    def normalize_created_at(cls, value: datetime) -> datetime:
        return _utc(value, "created_at_utc")

    @model_validator(mode="after")
    def validate_artifact(self) -> Self:
        request = ApprovalAssessmentCreateRequest(
            research_run_id=self.research_run_id,
            approval_policy_version_id=self.approval_policy_version_id,
            approval_scope_version_id=self.approval_scope_version_id,
            human_authorization_evidence_id=self.human_authorization_evidence_id,
            risk_input_id=self.risk_input_id,
        )
        expected_fingerprint = assessment_request_fingerprint(
            request=request,
            lineage_sha256=self.phase6_lineage.lineage_sha256,
            policy_sha256=self.approval_policy_sha256,
            scope_sha256=self.approval_scope_sha256,
            authorization_sha256=self.authorization_sha256,
            risk_input_sha256=self.risk_input_sha256,
            revocation_set_sha256=self.revocation_set_sha256,
            currentness_state_sha256=self.currentness_state_sha256,
            phase7_code_version_git_sha=self.phase7_code_version_git_sha,
        )
        if (
            self.request_fingerprint_sha256 != expected_fingerprint
            or self.assessment_id != identity(PHASE7_ASSESSMENT_NAMESPACE, expected_fingerprint)
        ):
            raise ValueError("assessment identity must derive from resolved immutable evidence")
        if (
            tuple(item.ordinal for item in self.checks)
            != tuple(range(1, len(APPROVAL_CHECK_ORDER) + 1))
            or tuple(item.code for item in self.checks) != APPROVAL_CHECK_ORDER
        ):
            raise ValueError("assessment must persist the exact ordered Phase 7 check set")
        all_pass = all(item.status is CheckStatus.PASS for item in self.checks)
        if (self.outcome is ApprovalAssessmentOutcome.APPROVED_PAPER) is not all_pass:
            raise ValueError("positive approval requires every check to pass")
        expected_reasons = (
            ("all_approval_and_risk_checks_passed",)
            if all_pass
            else tuple(
                sorted(
                    {
                        item.reason_code
                        for item in self.checks
                        if item.status is not CheckStatus.PASS
                    }
                )
            )
        )
        if self.reason_codes != expected_reasons:
            raise ValueError("assessment reason codes must derive from non-passing checks")
        _sorted_unique(self.revocation_ids, "revocation ids")
        payload = self.model_dump(
            mode="python", exclude={"assessment_id", "artifact_sha256", "created_at_utc"}
        )
        if self.artifact_sha256 != domain_sha256(PHASE7_ASSESSMENT_ARTIFACT_HASH_DOMAIN, payload):
            raise ValueError("assessment artifact hash must bind its complete timeless payload")
        return self


class ApprovalAssessmentSummary(StrictModel):
    assessment_id: UUID
    artifact_sha256: SHA256
    research_run_id: UUID
    research_configuration_id: Identifier
    outcome: ApprovalAssessmentOutcome
    reason_codes: tuple[Identifier, ...]
    created_at_utc: datetime
    synthetic: Literal[True] = True
    simulated_paper_only: Literal[True] = True
    execution_authorized: Literal[False] = False
    execution_ready: Literal[False] = False
    no_personalized_investment_advice: Literal[True] = True
    no_real_performance_claimed: Literal[True] = True

    @field_validator("created_at_utc")
    @classmethod
    def normalize_created_at(cls, value: datetime) -> datetime:
        return _utc(value, "created_at_utc")


def revocation_request_fingerprint(
    *,
    request: ApprovalRevocationCreateRequest,
    authorization_sha256: str,
    revocation_evidence_sha256: str,
    phase7_code_version_git_sha: str,
) -> str:
    return domain_sha256(
        PHASE7_REVOCATION_REQUEST_HASH_DOMAIN,
        {
            "request": request,
            "authorization_sha256": authorization_sha256,
            "revocation_evidence_sha256": revocation_evidence_sha256,
            "phase7_code_version_git_sha": phase7_code_version_git_sha,
        },
    )


class AuthorizationRevocationArtifact(StrictModel):
    revocation_id: UUID
    artifact_schema_version: Literal["phase7-authorization-revocation-v1"] = (
        PHASE7_REVOCATION_SCHEMA_VERSION
    )
    artifact_sha256: SHA256
    request_fingerprint_sha256: SHA256
    human_authorization_evidence_id: UUID
    authorization_sha256: SHA256
    revocation_evidence_id: UUID
    revocation_evidence_sha256: SHA256
    revoked_by: Identifier
    reason: str = Field(min_length=1, max_length=2000)
    effective_at_utc: datetime
    phase7_code_version_git_sha: GitSHA
    created_at_utc: datetime
    synthetic: Literal[True] = True
    simulated_paper_only: Literal[True] = True
    execution_authorized: Literal[False] = False
    execution_ready: Literal[False] = False
    no_personalized_investment_advice: Literal[True] = True
    no_real_performance_claimed: Literal[True] = True

    @field_validator("effective_at_utc", "created_at_utc")
    @classmethod
    def normalize_times(cls, value: datetime, info: object) -> datetime:
        return _utc(value, getattr(info, "field_name", "revocation time"))

    @model_validator(mode="after")
    def validate_revocation(self) -> Self:
        request = ApprovalRevocationCreateRequest(
            human_authorization_evidence_id=self.human_authorization_evidence_id,
            revocation_evidence_id=self.revocation_evidence_id,
        )
        expected_fingerprint = revocation_request_fingerprint(
            request=request,
            authorization_sha256=self.authorization_sha256,
            revocation_evidence_sha256=self.revocation_evidence_sha256,
            phase7_code_version_git_sha=self.phase7_code_version_git_sha,
        )
        if (
            self.request_fingerprint_sha256 != expected_fingerprint
            or self.revocation_id != identity(PHASE7_REVOCATION_NAMESPACE, expected_fingerprint)
        ):
            raise ValueError(
                "revocation identity must derive from authorization and server evidence"
            )
        payload = self.model_dump(
            mode="python", exclude={"revocation_id", "artifact_sha256", "created_at_utc"}
        )
        if self.artifact_sha256 != domain_sha256(PHASE7_REVOCATION_ARTIFACT_HASH_DOMAIN, payload):
            raise ValueError("revocation artifact hash must bind its complete timeless payload")
        return self


class AuthorizationRevocationSummary(StrictModel):
    revocation_id: UUID
    artifact_sha256: SHA256
    human_authorization_evidence_id: UUID
    revocation_evidence_id: UUID
    effective_at_utc: datetime
    created_at_utc: datetime
    synthetic: Literal[True] = True
    simulated_paper_only: Literal[True] = True
    execution_authorized: Literal[False] = False
    execution_ready: Literal[False] = False

    @field_validator("effective_at_utc", "created_at_utc")
    @classmethod
    def normalize_times(cls, value: datetime, info: object) -> datetime:
        return _utc(value, getattr(info, "field_name", "revocation time"))


__all__ = [name for name in globals() if not name.startswith("_")]
