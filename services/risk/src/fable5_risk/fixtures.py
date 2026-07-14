"""Deterministic synthetic Phase 7 evidence builders.

The builders create independently persistable evidence.  The approval workflow only loads
the resulting records through its stores; it never calls these helpers.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid5

from fable5_backtester.contracts import GateCode, PromotionState
from fable5_data.contracts import DataCapability
from fable5_mapping.models import CanonicalFamily
from fable5_research.canonical import PHASE6_SNAPSHOT_BINDING_HASH_DOMAIN
from fable5_research.contracts import ResearchRunArtifact

from fable5_risk.canonical import (
    PHASE7_AUTHORIZATION_HASH_DOMAIN,
    PHASE7_AUTHORIZATION_NAMESPACE,
    PHASE7_LINEAGE_HASH_DOMAIN,
    PHASE7_POLICY_HASH_DOMAIN,
    PHASE7_POLICY_NAMESPACE,
    PHASE7_REVOCATION_EVIDENCE_HASH_DOMAIN,
    PHASE7_REVOCATION_EVIDENCE_NAMESPACE,
    PHASE7_RISK_INPUT_HASH_DOMAIN,
    PHASE7_RISK_INPUT_NAMESPACE,
    PHASE7_SCOPE_HASH_DOMAIN,
    PHASE7_SCOPE_NAMESPACE,
    domain_sha256,
    identity,
)
from fable5_risk.contracts import (
    APPROVAL_CHECK_ORDER,
    PHASE7_APPROVAL_POLICY_SCHEMA_VERSION,
    PHASE7_APPROVAL_SCOPE_SCHEMA_VERSION,
    PHASE7_AUTHORIZATION_SCHEMA_VERSION,
    PHASE7_LINEAGE_SCHEMA_VERSION,
    PHASE7_REVOCATION_EVIDENCE_SCHEMA_VERSION,
    PHASE7_RISK_INPUT_SCHEMA_VERSION,
    ApprovalPolicy,
    ApprovalRiskInput,
    ApprovalScope,
    HumanAuthorizationEvidence,
    Phase6ApprovalLineage,
    Phase6SnapshotBindingLineage,
    RevocationEvidenceProfile,
)

SYNTHETIC_ASSESSMENT_TIME_UTC = datetime(2026, 7, 14, 12, tzinfo=UTC)
SYNTHETIC_PHASE7_CODE_VERSION_GIT_SHA = "7" * 40
SYNTHETIC_UNIVERSE_ID = "phase7-synthetic-universe-v1"

_FIXTURE_NAMESPACE = UUID("cc218f6f-830f-5760-a99b-3a3b7d35a7e3")


def _fixture_uuid(name: str) -> UUID:
    return uuid5(_FIXTURE_NAMESPACE, name)


def _fixture_sha(name: str) -> str:
    return domain_sha256("phase7-synthetic-reference-v1", {"name": name})


def _assessment_time_utc(value: datetime | None) -> datetime:
    resolved = SYNTHETIC_ASSESSMENT_TIME_UTC if value is None else value
    if resolved.tzinfo is None or resolved.utcoffset() is None:
        raise ValueError("assessment_time_utc must be timezone-aware")
    return resolved.astimezone(UTC)


def phase6_lineage_from_research_artifact(artifact: ResearchRunArtifact) -> Phase6ApprovalLineage:
    """Copy the exact approval-relevant Phase 6 lineage from an immutable artifact."""

    evaluation = artifact.phase5_evaluation
    bindings = tuple(
        Phase6SnapshotBindingLineage(
            ordinal=item.ordinal,
            snapshot_id=item.snapshot_id,
            snapshot_sha256=item.snapshot_sha256,
            capability=item.capability,
            binding_sha256=item.binding_sha256,
            mapping_id=item.mapping_id,
            mapping_input_sha256=item.mapping_input_sha256,
            as_of_utc=item.as_of_utc,
            quality_status=item.quality_status,
        )
        for item in artifact.snapshot_bindings
    )
    payload = {
        "schema_version": PHASE7_LINEAGE_SCHEMA_VERSION,
        "research_run_id": artifact.run_id,
        "research_artifact_sha256": artifact.artifact_sha256,
        "research_request_fingerprint_sha256": artifact.request_fingerprint_sha256,
        "research_configuration_id": artifact.configuration_id.value,
        "research_configuration_sha256": artifact.configuration_sha256,
        "research_status": artifact.status.value,
        "promotion_state": evaluation.promotion_state,
        "mapping_id": artifact.mapping_id,
        "mapping_version": artifact.mapping_version,
        "mapping_input_sha256": artifact.mapping_input_sha256,
        "canonical_family": artifact.family,
        "specification_sha256": artifact.specification.specification_sha256,
        "research_pipeline_input_sha256": artifact.pipeline_input_sha256,
        "feature_lineage_sha256": artifact.feature_lineage_sha256,
        "snapshot_bundle_sha256": artifact.snapshot_bundle_sha256,
        "source_reproduction_audit_sha256": artifact.source_reproduction_audit.audit_sha256,
        "snapshot_bindings": bindings,
        "phase5_policy_id": evaluation.policy_id,
        "phase5_policy_version": evaluation.policy_version,
        "phase5_policy_sha256": evaluation.policy_sha256,
        "phase5_fixture_id": evaluation.fixture_id,
        "phase5_fixture_sha256": evaluation.fixture_sha256,
        "evaluation_report_id": evaluation.evaluation_report_id,
        "evaluation_report_sha256": evaluation.evaluation_report_sha256,
        "phase5_trial_set_sha256": evaluation.phase5_trial_set_sha256,
        "gate_codes": evaluation.gate_codes,
        "code_version_git_sha": artifact.code_version_git_sha,
        "random_seed": artifact.random_seed,
        "raw_trial_count": evaluation.raw_trial_count,
        "effective_trial_count": evaluation.effective_trial_count,
    }
    return Phase6ApprovalLineage.model_validate(
        {
            "lineage_sha256": domain_sha256(PHASE7_LINEAGE_HASH_DOMAIN, payload),
            **payload,
        }
    )


def build_synthetic_phase6_lineage(
    *,
    configuration_id: str = "phase6-a-pass-v2",
    promotion_state: PromotionState = PromotionState.PASS_RESEARCH,
    family: CanonicalFamily = CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING,
) -> Phase6ApprovalLineage:
    """Build compact but complete Phase 6 lineage for isolated domain tests."""

    mapping_id = _fixture_uuid(f"mapping:{family.value}")
    mapping_input_sha256 = _fixture_sha(f"mapping-input:{family.value}")
    capability = DataCapability.SECURITY_MASTER
    binding_payload = {
        "ordinal": 1,
        "snapshot_id": _fixture_uuid(f"snapshot:{family.value}:{capability.value}"),
        "snapshot_sha256": _fixture_sha(f"snapshot:{family.value}:{capability.value}"),
        "capability": capability,
        "mapping_id": mapping_id,
        "mapping_input_sha256": mapping_input_sha256,
        "as_of_utc": datetime(2022, 1, 1, tzinfo=UTC),
        "quality_status": "accepted",
    }
    binding = Phase6SnapshotBindingLineage.model_validate(
        {
            "binding_sha256": domain_sha256(PHASE6_SNAPSHOT_BINDING_HASH_DOMAIN, binding_payload),
            **binding_payload,
        }
    )
    completed = promotion_state in {
        PromotionState.PASS_RESEARCH,
        PromotionState.FAIL_REJECT,
        PromotionState.RESEARCH_ONLY_REGIME_DEPENDENT,
    }
    payload = {
        "schema_version": PHASE7_LINEAGE_SCHEMA_VERSION,
        "research_run_id": _fixture_uuid(f"run:{configuration_id}:{promotion_state.value}"),
        "research_artifact_sha256": _fixture_sha(
            f"research-artifact:{configuration_id}:{promotion_state.value}"
        ),
        "research_request_fingerprint_sha256": _fixture_sha(
            f"research-request:{configuration_id}:{promotion_state.value}"
        ),
        "research_configuration_id": configuration_id,
        "research_configuration_sha256": _fixture_sha(f"research-config:{configuration_id}"),
        "research_status": "completed" if completed else "blocked",
        "promotion_state": promotion_state,
        "mapping_id": mapping_id,
        "mapping_version": 1,
        "mapping_input_sha256": mapping_input_sha256,
        "canonical_family": family,
        "specification_sha256": _fixture_sha(f"specification:{family.value}"),
        "research_pipeline_input_sha256": _fixture_sha(f"pipeline-input:{configuration_id}"),
        "feature_lineage_sha256": _fixture_sha(f"feature-lineage:{configuration_id}"),
        "snapshot_bundle_sha256": _fixture_sha(f"snapshot-bundle:{family.value}"),
        "source_reproduction_audit_sha256": _fixture_sha(f"source-reproduction:{configuration_id}"),
        "snapshot_bindings": (binding,),
        "phase5_policy_id": _fixture_uuid("phase5-policy"),
        "phase5_policy_version": 1,
        "phase5_policy_sha256": _fixture_sha("phase5-policy"),
        "phase5_fixture_id": "phase5-synthetic-evaluation-fixture-v1",
        "phase5_fixture_sha256": _fixture_sha("phase5-fixture"),
        "evaluation_report_id": _fixture_uuid(f"phase5-report:{configuration_id}")
        if completed
        else None,
        "evaluation_report_sha256": _fixture_sha(f"phase5-report:{configuration_id}")
        if completed
        else None,
        "phase5_trial_set_sha256": _fixture_sha(f"phase5-trials:{configuration_id}")
        if completed
        else None,
        "gate_codes": tuple(GateCode) if completed else (),
        "code_version_git_sha": "6" * 40,
        "random_seed": 607,
        "raw_trial_count": 6 if completed else 0,
        "effective_trial_count": Decimal("4") if completed else Decimal("0"),
    }
    return Phase6ApprovalLineage.model_validate(
        {
            "lineage_sha256": domain_sha256(PHASE7_LINEAGE_HASH_DOMAIN, payload),
            **payload,
        }
    )


def build_approval_policy(
    *,
    policy_id: str = "phase7-synthetic-approval-risk-policy",
    policy_version: int = 1,
    valid_from_utc: datetime | None = None,
    expires_at_utc: datetime | None = None,
    authorization_max_age_seconds: int = 172800,
    risk_input_max_age_seconds: int = 3600,
    max_notional: Decimal = Decimal("100000"),
) -> ApprovalPolicy:
    valid_from = valid_from_utc or SYNTHETIC_ASSESSMENT_TIME_UTC - timedelta(days=7)
    expires_at = expires_at_utc or SYNTHETIC_ASSESSMENT_TIME_UTC + timedelta(days=7)
    payload = {
        "schema_version": PHASE7_APPROVAL_POLICY_SCHEMA_VERSION,
        "policy_id": policy_id,
        "policy_version": policy_version,
        "valid_from_utc": valid_from,
        "expires_at_utc": expires_at,
        "authorization_max_age_seconds": authorization_max_age_seconds,
        "risk_input_max_age_seconds": risk_input_max_age_seconds,
        "required_check_codes": APPROVAL_CHECK_ORDER,
        "max_notional": max_notional,
        "max_gross_exposure": Decimal("150000"),
        "max_abs_net_exposure": Decimal("50000"),
        "max_sector_exposure": Decimal("40000"),
        "max_concentration": Decimal("0.25"),
        "min_liquidity": Decimal("500000"),
        "max_turnover": Decimal("0.50"),
        "max_volatility": Decimal("0.40"),
        "max_daily_loss": Decimal("5000"),
        "max_drawdown": Decimal("0.20"),
        "synthetic": True,
    }
    sha256 = domain_sha256(PHASE7_POLICY_HASH_DOMAIN, payload)
    return ApprovalPolicy.model_validate(
        {
            "approval_policy_version_id": identity(PHASE7_POLICY_NAMESPACE, sha256),
            "policy_sha256": sha256,
            **payload,
        }
    )


def build_approval_scope(
    lineage: Phase6ApprovalLineage,
    policy: ApprovalPolicy,
    *,
    scope_id: str | None = None,
    valid_from_utc: datetime | None = None,
    expires_at_utc: datetime | None = None,
    max_notional: Decimal = Decimal("75000"),
) -> ApprovalScope:
    payload = {
        "schema_version": PHASE7_APPROVAL_SCOPE_SCHEMA_VERSION,
        "scope_id": scope_id or f"phase7-synthetic-scope:{lineage.research_run_id}",
        "scope_version": 1,
        "research_run_id": lineage.research_run_id,
        "research_artifact_sha256": lineage.research_artifact_sha256,
        "approval_policy_version_id": policy.approval_policy_version_id,
        "permitted_universe_ids": (SYNTHETIC_UNIVERSE_ID,),
        "max_notional": max_notional,
        "valid_from_utc": valid_from_utc or SYNTHETIC_ASSESSMENT_TIME_UTC - timedelta(days=2),
        "expires_at_utc": expires_at_utc or SYNTHETIC_ASSESSMENT_TIME_UTC + timedelta(days=2),
        "synthetic": True,
    }
    sha256 = domain_sha256(PHASE7_SCOPE_HASH_DOMAIN, payload)
    return ApprovalScope.model_validate(
        {
            "approval_scope_version_id": identity(PHASE7_SCOPE_NAMESPACE, sha256),
            "scope_sha256": sha256,
            **payload,
        }
    )


def build_human_authorization(
    lineage: Phase6ApprovalLineage,
    policy: ApprovalPolicy,
    scope: ApprovalScope,
    *,
    authorized_at_utc: datetime | None = None,
    review_at_utc: datetime | None = None,
    expires_at_utc: datetime | None = None,
) -> HumanAuthorizationEvidence:
    authorized_at = authorized_at_utc or SYNTHETIC_ASSESSMENT_TIME_UTC - timedelta(hours=1)
    review_at = review_at_utc or SYNTHETIC_ASSESSMENT_TIME_UTC + timedelta(hours=12)
    expires_at = expires_at_utc or SYNTHETIC_ASSESSMENT_TIME_UTC + timedelta(days=1)
    payload = {
        "schema_version": PHASE7_AUTHORIZATION_SCHEMA_VERSION,
        "research_run_id": lineage.research_run_id,
        "research_artifact_sha256": lineage.research_artifact_sha256,
        "approval_policy_version_id": policy.approval_policy_version_id,
        "approval_scope_version_id": scope.approval_scope_version_id,
        "authorized_by": "synthetic-human-reviewer-001",
        "authorized_role": "paper_risk_reviewer",
        "rationale": "Synthetic human-controlled authorization evidence for Phase 7 QA only.",
        "authorized_at_utc": authorized_at,
        "review_at_utc": review_at,
        "expires_at_utc": expires_at,
        "human_controlled": True,
        "synthetic": True,
    }
    sha256 = domain_sha256(PHASE7_AUTHORIZATION_HASH_DOMAIN, payload)
    return HumanAuthorizationEvidence.model_validate(
        {
            "human_authorization_evidence_id": identity(PHASE7_AUTHORIZATION_NAMESPACE, sha256),
            "authorization_sha256": sha256,
            **payload,
        }
    )


def build_approval_risk_input(
    lineage: Phase6ApprovalLineage,
    policy: ApprovalPolicy,
    scope: ApprovalScope,
    *,
    observed_at_utc: datetime | None = None,
    research_run_id: UUID | None = None,
    research_artifact_sha256: str | None = None,
    proposed_notional: Decimal | None = Decimal("50000"),
    gross_exposure: Decimal | None = Decimal("100000"),
    net_exposure: Decimal | None = Decimal("25000"),
    sector_exposure: Decimal | None = Decimal("25000"),
    concentration: Decimal | None = Decimal("0.20"),
    available_liquidity: Decimal | None = Decimal("1000000"),
    turnover: Decimal | None = Decimal("0.25"),
    volatility: Decimal | None = Decimal("0.20"),
    daily_loss: Decimal | None = Decimal("1000"),
    drawdown: Decimal | None = Decimal("0.10"),
    global_control_clear: bool | None = True,
    strategy_control_clear: bool | None = True,
    data_quality_control_clear: bool | None = True,
    market_calendar_open: bool | None = True,
    duplicate_context_clear: bool | None = True,
) -> ApprovalRiskInput:
    payload = {
        "schema_version": PHASE7_RISK_INPUT_SCHEMA_VERSION,
        "research_run_id": research_run_id or lineage.research_run_id,
        "research_artifact_sha256": research_artifact_sha256 or lineage.research_artifact_sha256,
        "approval_policy_version_id": policy.approval_policy_version_id,
        "approval_scope_version_id": scope.approval_scope_version_id,
        "universe_id": SYNTHETIC_UNIVERSE_ID,
        "observed_at_utc": observed_at_utc or SYNTHETIC_ASSESSMENT_TIME_UTC - timedelta(minutes=5),
        "global_control_clear": global_control_clear,
        "strategy_control_clear": strategy_control_clear,
        "data_quality_control_clear": data_quality_control_clear,
        "market_calendar_open": market_calendar_open,
        "duplicate_context_clear": duplicate_context_clear,
        "proposed_notional": proposed_notional,
        "gross_exposure": gross_exposure,
        "net_exposure": net_exposure,
        "sector_exposure": sector_exposure,
        "concentration": concentration,
        "available_liquidity": available_liquidity,
        "turnover": turnover,
        "volatility": volatility,
        "daily_loss": daily_loss,
        "drawdown": drawdown,
        "synthetic": True,
    }
    sha256 = domain_sha256(PHASE7_RISK_INPUT_HASH_DOMAIN, payload)
    return ApprovalRiskInput.model_validate(
        {
            "risk_input_id": identity(PHASE7_RISK_INPUT_NAMESPACE, sha256),
            "risk_input_sha256": sha256,
            **payload,
        }
    )


def build_revocation_evidence_profile(
    *, effective_at_utc: datetime | None = None
) -> RevocationEvidenceProfile:
    payload = {
        "schema_version": PHASE7_REVOCATION_EVIDENCE_SCHEMA_VERSION,
        "revoked_by": "synthetic-human-reviewer-002",
        "reason": "Synthetic human-controlled revocation evidence for Phase 7 QA only.",
        "effective_at_utc": effective_at_utc or SYNTHETIC_ASSESSMENT_TIME_UTC,
        "human_controlled": True,
        "synthetic": True,
    }
    sha256 = domain_sha256(PHASE7_REVOCATION_EVIDENCE_HASH_DOMAIN, payload)
    return RevocationEvidenceProfile.model_validate(
        {
            "revocation_evidence_id": identity(PHASE7_REVOCATION_EVIDENCE_NAMESPACE, sha256),
            "revocation_evidence_sha256": sha256,
            **payload,
        }
    )


DEFAULT_REVOCATION_EVIDENCE_PROFILE = build_revocation_evidence_profile()


def resolve_revocation_evidence(revocation_evidence_id: UUID) -> RevocationEvidenceProfile:
    """Resolve the frozen server profile without deriving evidence from client input."""

    if revocation_evidence_id != DEFAULT_REVOCATION_EVIDENCE_PROFILE.revocation_evidence_id:
        raise LookupError("server-owned revocation evidence does not exist")
    return DEFAULT_REVOCATION_EVIDENCE_PROFILE


@dataclass(frozen=True)
class ApprovalEvidenceBundle:
    policy: ApprovalPolicy
    scope: ApprovalScope
    authorization: HumanAuthorizationEvidence
    risk_input: ApprovalRiskInput


def build_nominal_evidence_bundle(
    lineage: Phase6ApprovalLineage,
    *,
    assessment_time_utc: datetime | None = None,
    policy_id: str = "phase7-synthetic-approval-risk-policy",
    policy_version: int = 1,
    scope_id: str | None = None,
) -> ApprovalEvidenceBundle:
    assessment_time = _assessment_time_utc(assessment_time_utc)
    policy = build_approval_policy(
        policy_id=policy_id,
        policy_version=policy_version,
        valid_from_utc=assessment_time - timedelta(days=7),
        expires_at_utc=assessment_time + timedelta(days=7),
    )
    scope = build_approval_scope(
        lineage,
        policy,
        scope_id=scope_id,
        valid_from_utc=assessment_time - timedelta(days=2),
        expires_at_utc=assessment_time + timedelta(days=2),
    )
    authorization = build_human_authorization(
        lineage,
        policy,
        scope,
        authorized_at_utc=assessment_time - timedelta(hours=1),
        review_at_utc=assessment_time + timedelta(hours=12),
        expires_at_utc=assessment_time + timedelta(days=1),
    )
    risk_input = build_approval_risk_input(
        lineage,
        policy,
        scope,
        observed_at_utc=assessment_time - timedelta(minutes=5),
    )
    return ApprovalEvidenceBundle(policy, scope, authorization, risk_input)


def build_expired_evidence_bundle(
    lineage: Phase6ApprovalLineage,
    *,
    assessment_time_utc: datetime | None = None,
    policy_id: str = "phase7-synthetic-approval-risk-policy",
    policy_version: int = 1,
    scope_id: str | None = None,
) -> ApprovalEvidenceBundle:
    assessment_time = _assessment_time_utc(assessment_time_utc)
    bundle = build_nominal_evidence_bundle(
        lineage,
        assessment_time_utc=assessment_time,
        policy_id=policy_id,
        policy_version=policy_version,
        scope_id=scope_id,
    )
    authorization = build_human_authorization(
        lineage,
        bundle.policy,
        bundle.scope,
        authorized_at_utc=assessment_time - timedelta(days=3),
        review_at_utc=assessment_time - timedelta(days=1, hours=1),
        expires_at_utc=assessment_time - timedelta(days=1),
    )
    return ApprovalEvidenceBundle(bundle.policy, bundle.scope, authorization, bundle.risk_input)


def build_stale_evidence_bundle(
    lineage: Phase6ApprovalLineage,
    *,
    assessment_time_utc: datetime | None = None,
    policy_id: str = "phase7-synthetic-approval-risk-policy",
    policy_version: int = 1,
    scope_id: str | None = None,
) -> ApprovalEvidenceBundle:
    assessment_time = _assessment_time_utc(assessment_time_utc)
    bundle = build_nominal_evidence_bundle(
        lineage,
        assessment_time_utc=assessment_time,
        policy_id=policy_id,
        policy_version=policy_version,
        scope_id=scope_id,
    )
    risk_input = build_approval_risk_input(
        lineage,
        bundle.policy,
        bundle.scope,
        observed_at_utc=assessment_time - timedelta(hours=2),
    )
    return ApprovalEvidenceBundle(bundle.policy, bundle.scope, bundle.authorization, risk_input)


def build_conflicting_evidence_bundle(
    lineage: Phase6ApprovalLineage,
    *,
    conflicting_lineage: Phase6ApprovalLineage | None = None,
) -> ApprovalEvidenceBundle:
    bundle = build_nominal_evidence_bundle(lineage)
    risk_input = build_approval_risk_input(
        lineage,
        bundle.policy,
        bundle.scope,
        research_run_id=(
            conflicting_lineage.research_run_id
            if conflicting_lineage is not None
            else _fixture_uuid("conflicting-run")
        ),
        research_artifact_sha256=(
            conflicting_lineage.research_artifact_sha256
            if conflicting_lineage is not None
            else _fixture_sha("conflicting-artifact")
        ),
    )
    return ApprovalEvidenceBundle(bundle.policy, bundle.scope, bundle.authorization, risk_input)


def build_uncomputable_evidence_bundle(
    lineage: Phase6ApprovalLineage,
    *,
    assessment_time_utc: datetime | None = None,
    policy_id: str = "phase7-synthetic-approval-risk-policy",
    policy_version: int = 1,
    scope_id: str | None = None,
) -> ApprovalEvidenceBundle:
    assessment_time = _assessment_time_utc(assessment_time_utc)
    bundle = build_nominal_evidence_bundle(
        lineage,
        assessment_time_utc=assessment_time,
        policy_id=policy_id,
        policy_version=policy_version,
        scope_id=scope_id,
    )
    risk_input = build_approval_risk_input(
        lineage,
        bundle.policy,
        bundle.scope,
        observed_at_utc=assessment_time - timedelta(minutes=5),
        proposed_notional=None,
    )
    return ApprovalEvidenceBundle(bundle.policy, bundle.scope, bundle.authorization, risk_input)


def build_breach_evidence_bundle(
    lineage: Phase6ApprovalLineage,
    *,
    assessment_time_utc: datetime | None = None,
    policy_id: str = "phase7-synthetic-approval-risk-policy",
    policy_version: int = 1,
    scope_id: str | None = None,
) -> ApprovalEvidenceBundle:
    assessment_time = _assessment_time_utc(assessment_time_utc)
    bundle = build_nominal_evidence_bundle(
        lineage,
        assessment_time_utc=assessment_time,
        policy_id=policy_id,
        policy_version=policy_version,
        scope_id=scope_id,
    )
    risk_input = build_approval_risk_input(
        lineage,
        bundle.policy,
        bundle.scope,
        observed_at_utc=assessment_time - timedelta(minutes=5),
        proposed_notional=Decimal("75000.01"),
    )
    return ApprovalEvidenceBundle(bundle.policy, bundle.scope, bundle.authorization, risk_input)


__all__ = [name for name in globals() if not name.startswith("_")]
