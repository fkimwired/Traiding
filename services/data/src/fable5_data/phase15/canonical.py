"""Canonical constants and hash domains for the Phase 15 portable specification."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Final
from uuid import UUID

from fable5_data.canonical import canonical_json_bytes as canonical_json_bytes
from fable5_data.canonical import canonicalize as canonicalize
from fable5_data.canonical import domain_sha256 as domain_sha256
from fable5_data.canonical import uuid_from_sha256

PHASE15_ARTIFACT_SCHEMA_VERSION: Final = "phase15-family-a-research-admission-specification-v1"
PHASE15_ARTIFACT_HASH_DOMAIN: Final = PHASE15_ARTIFACT_SCHEMA_VERSION
PHASE15_REQUIREMENT_SCHEMA_VERSION: Final = "phase15-family-a-research-admission-requirement-v1"
PHASE15_REQUIREMENT_HASH_DOMAIN: Final = PHASE15_REQUIREMENT_SCHEMA_VERSION
PHASE15_GAP_SCHEMA_VERSION: Final = "phase15-family-a-research-admission-gap-v1"
PHASE15_GAP_HASH_DOMAIN: Final = PHASE15_GAP_SCHEMA_VERSION
PHASE15_POLICY_ID: Final = "phase15-family-a-research-admission-policy-v1"
PHASE15_POLICY_HASH_DOMAIN: Final = PHASE15_POLICY_ID
PHASE15_REQUIREMENTS_MANIFEST_HASH_DOMAIN: Final = (
    "phase15-family-a-research-admission-requirements-manifest-v1"
)
PHASE15_GAPS_MANIFEST_HASH_DOMAIN: Final = "phase15-family-a-research-admission-gaps-manifest-v1"
PHASE15_EVIDENCE_HASH_DOMAIN: Final = "phase15-family-a-research-admission-evidence-v1"
PHASE15_ARTIFACT_NAMESPACE: Final = UUID("e681ce4e-94fa-5b7a-bb12-ce17b509037b")

PHASE15_ACCEPTED_PHASE14_COMMIT_SHA: Final = "513fdfd515599e59db6911441aadf1cc30f7352c"
PHASE15_ACCEPTED_PHASE14_TREE_SHA: Final = "5870fd4c112b7c7bee05f6240c5cbd950eeaff04"
PHASE15_FAMILY: Final = "A_CROSS_SECTIONAL_EQUITY_RANKING"
PHASE15_PHASE6_SPECIFICATION_ID: Final = "phase6-a_cross_sectional_equity_ranking-research-pipeline"
PHASE15_PHASE6_SPECIFICATION_VERSION: Final = "v2"
PHASE15_PHASE6_SPECIFICATION_SHA256: Final = (
    "3967b3c0dffd6a27c4ac8012773621090b828e8bdc2f242611c34d81420b37bc"
)
PHASE15_FROZEN_AT_UTC: Final = datetime(2026, 7, 18, tzinfo=UTC)

PHASE15_REQUIREMENT_CODES: Final = (
    "FAMILY_A_SPECIFICATION_IDENTITY_BOUND",
    "SIGNAL_ACTION_AND_HORIZON_REQUIREMENTS_BOUND",
    "POINT_IN_TIME_CAPABILITY_REQUIREMENTS_FROZEN",
    "INSTRUMENT_IDENTITY_AVAILABILITY_POLICY_FROZEN",
    "UNIVERSE_DELISTING_CORPORATE_ACTION_POLICY_FROZEN",
    "FUNDAMENTAL_REVISION_LAG_POLICY_FROZEN",
    "MACRO_SECTOR_LIQUIDITY_REQUIREMENTS_FROZEN",
    "FULL_HISTORY_SAMPLE_BOUNDARIES_FROZEN",
    "SNAPSHOT_CANONICALIZATION_AUDIT_POLICY_FROZEN",
    "USE_RIGHTS_RETENTION_DERIVED_DATA_POLICY_FROZEN",
    "WALK_FORWARD_PURGE_EMBARGO_HOLDOUT_POLICY_FROZEN",
    "TRIAL_ACCOUNTING_DSR_PBO_LEAKAGE_POLICY_FROZEN",
    "COST_SLIPPAGE_STRESS_REGIME_POLICY_FROZEN",
    "RISK_REPRODUCIBILITY_POLICY_FROZEN",
    "INGESTION_RESEARCH_PROMOTION_EXECUTION_AUTHORITY_ABSENT",
)

PHASE15_REQUIREMENT_DEFINITIONS: Final = (
    "Bind the immutable Family A specification identity, version, hash, and canonical family.",
    (
        "Freeze the deterministic research-score rule, server-owned action semantics, and "
        "two-session forecast horizon without creating a trade instruction."
    ),
    (
        "Require the complete seven-capability Family A point-in-time input registry before "
        "any non-synthetic research run."
    ),
    (
        "Require stable instrument, listing, ticker, exchange, sector, and availability "
        "histories with explicit validity intervals."
    ),
    (
        "Require historical universe membership, inactive and delisted coverage, "
        "delisting-return semantics, and announcement-time corporate-action revisions."
    ),
    (
        "Require as-reported fundamental vintages with release or accepted timestamps and "
        "no retroactive restatement overwrite."
    ),
    (
        "Require point-in-time macro vintages, sector history, liquidity depth, and explicit "
        "missingness before dataset admission."
    ),
    (
        "Require predeclared full-history coverage, sample boundaries, decision calendar, "
        "and computable sample-adequacy thresholds."
    ),
    (
        "Require immutable raw and normalized lineage, canonical snapshot hashes, source "
        "versions, availability times, and audit identities."
    ),
    (
        "Require independently reviewed current storage, retention, non-display, and "
        "derived-data rights with revocation semantics."
    ),
    (
        "Freeze nested past-only walk-forward geometry, label-interval purge, explicit "
        "embargo applicability, and an untouched confirmation holdout."
    ),
    (
        "Require complete trial accounting plus computable DSR, PBO, leakage, and "
        "promotion-gate inputs under a frozen policy."
    ),
    (
        "Require market-calibrated baseline and stressed transaction-cost, slippage, "
        "liquidity, and regime policies before promotion."
    ),
    (
        "Require computable risk limits and complete reproducibility fields including config "
        "hash, snapshot identity, git SHA, seed, trial count, and UTC time."
    ),
    (
        "Keep ingestion, research execution, performance, promotion, approval, risk "
        "clearance, execution, and order authority absent from Phase 15."
    ),
)

PHASE15_GAP_CODES: Final = (
    "FAMILY_A_SIGNAL_AND_HORIZON",
    "FULL_POINT_IN_TIME_DATASET",
    "EXTERNAL_CANDIDATE_QUALIFICATION",
    "HISTORICAL_MEMBERSHIP_AND_DELISTING",
    "SECTOR_LIQUIDITY_MACRO_HISTORY",
    "INDEPENDENT_CURRENT_USE_RIGHTS",
    "NON_SYNTHETIC_SNAPSHOT_PERSISTENCE",
    "NON_SYNTHETIC_EVALUATION_POLICY",
    "NON_SYNTHETIC_EVALUATION_PATH",
    "PURGED_WALK_FORWARD_MECHANICS",
    "EMBARGO_APPLICABILITY_DECISION",
    "LEAKAGE_FREE_RESULT",
    "MARKET_CALIBRATED_COST_SLIPPAGE",
    "DSR_PBO_PROMOTION_GATES",
    "PHASE_15_IMPLEMENTATION_AUTHORITY",
    "DATA_RIGHTS_AND_RESEARCH_AUTHORITY",
    "RIGHTS_CURRENTNESS_REVOCATION",
    "PRE_ORDER_RISK",
    "IMMUTABLE_AUDIT_SCHEMA",
)

PHASE15_GAP_STATES: Final = (
    "MOCK_ONLY",
    "MISSING",
    "UNPROVEN",
    "UNPROVEN",
    "MISSING",
    "MISSING",
    "MISSING",
    "MISSING",
    "MISSING",
    "MOCK_ONLY",
    "UNPROVEN",
    "MOCK_ONLY",
    "MOCK_ONLY",
    "MOCK_ONLY",
    "PRESENT",
    "MISSING",
    "MISSING",
    "MOCK_ONLY",
    "PRESENT",
)

PHASE15_GAP_SUMMARIES: Final = (
    (
        "Family A has a deterministic mock research-score definition and two-session "
        "horizon, but no externally validated action rule."
    ),
    "No complete licensed non-synthetic point-in-time Family A dataset is present.",
    "The fixed external candidate has not produced an authorized complete qualification artifact.",
    "Historical membership and delisting-return coverage remain unproven for an external dataset.",
    "Complete sector, liquidity-depth, and point-in-time macro history is missing.",
    "No independently authenticated current use-rights decision is present.",
    (
        "The accepted snapshot persistence path is synthetic-only and has no non-synthetic "
        "admission path."
    ),
    "No approved non-synthetic evaluation policy freezes data-specific coverage and thresholds.",
    "No non-synthetic dataset-to-evaluation workflow exists.",
    "Purged nested walk-forward mechanics are proven only with deterministic mock evidence.",
    (
        "Embargo is documented as inapplicable to strict past-only folds, but no "
        "non-synthetic policy decision is approved."
    ),
    "Leakage-free results exist only for deterministic mock research evidence.",
    (
        "Cost and slippage realism is calibrated only for deterministic mock evidence, not "
        "an external market dataset."
    ),
    "DSR and PBO gates are mechanically proven only on deterministic mock research artifacts.",
    "The user has explicitly authorized implementation through Phase 15.",
    "Data-rights evidence does not grant research ingestion or research-run authority.",
    "No current rights-revocation and revalidation evidence exists for a non-synthetic dataset.",
    "Pre-order risk mechanics are mock-only and cannot authorize ingestion, research, or an order.",
    "The repository has immutable hash-bound audit schemas that Phase 15 must preserve.",
)

PHASE15_GAP_EVIDENCE_REFS: Final = (
    ("services/research/src/fable5_research/specification.py#family-a",),
    ("docs/PHASE_14_RESEARCH_INGESTION_ELIGIBILITY_DECISIONS.md#decision",),
    ("docs/PHASE_13_POINT_IN_TIME_DATA_QUALIFICATION_DECISIONS.md#acceptance-and-stop-condition",),
    (
        "docs/PHASE_13_POINT_IN_TIME_DATA_QUALIFICATION_DECISIONS.md#frozen-family-a-qualification-profile",
    ),
    ("docs/PHASE_14_RESEARCH_INGESTION_ELIGIBILITY_DECISIONS.md#decision",),
    ("docs/PHASE_14_RESEARCH_INGESTION_ELIGIBILITY_DECISIONS.md#decision",),
    ("services/data/src/fable5_data/snapshots.py#synthetic-only",),
    ("docs/PHASE_14_RESEARCH_INGESTION_ELIGIBILITY_DECISIONS.md#decision",),
    ("docs/PHASE_06_RESEARCH_DECISIONS.md#scope",),
    ("docs/EVALS.md#nested-chronological-evaluation",),
    ("docs/EVALS.md#embargo-semantics",),
    ("docs/PHASE_06_RESEARCH_DECISIONS.md#phase-5-bridge",),
    ("docs/PHASE_06_RESEARCH_DECISIONS.md#family-a-cross-sectional-ranking",),
    ("docs/PHASE_06_RESEARCH_DECISIONS.md#phase-5-bridge",),
    (
        "docs/PHASE_15_FAMILY_A_RESEARCH_ADMISSION_SPECIFICATION_DECISIONS.md"
        "#accepted-baseline-and-authority",
    ),
    ("docs/PHASE_14_RESEARCH_INGESTION_ELIGIBILITY_DECISIONS.md#authority-and-data-invariants",),
    ("docs/PHASE_14_RESEARCH_INGESTION_ELIGIBILITY_DECISIONS.md#decision",),
    ("docs/RISK_POLICY.md#approval-and-pre-order-risk-assessment-phase-7",),
    ("docs/EVALS.md#reproducibility-artifact",),
)

PHASE15_BOUNDARY_VALUES: Final = {
    "external_request_performed": False,
    "external_data_capture_authorized": False,
    "provider_payload_persisted": False,
    "licensed_data_persisted": False,
    "research_ingestion_authorized": False,
    "research_snapshot_created": False,
    "research_data_eligible": False,
    "research_run_created": False,
    "research_run_authorized": False,
    "research_executed": False,
    "performance_computed": False,
    "pass_research_granted": False,
    "strategy_promotion_authorized": False,
    "paper_approval_granted": False,
    "risk_clearance_granted": False,
    "strategy_execution_eligible": False,
    "execution_authorized": False,
    "order_submission_authorized": False,
    "live_path_absent": True,
    "no_personalized_investment_advice": True,
    "no_real_performance_claimed": True,
}

PHASE15_DISCLAIMER: Final = (
    "Requirements-only evidence; no external capture, data ingestion, research dataset, "
    "research authorization, performance result, promotion, risk clearance, execution "
    "authority, order, or personalized investment advice."
)

PHASE15_POLICY_SHA256: Final = domain_sha256(
    PHASE15_POLICY_HASH_DOMAIN,
    {
        "policy_id": PHASE15_POLICY_ID,
        "artifact_schema_version": PHASE15_ARTIFACT_SCHEMA_VERSION,
        "requirement_schema_version": PHASE15_REQUIREMENT_SCHEMA_VERSION,
        "gap_schema_version": PHASE15_GAP_SCHEMA_VERSION,
        "accepted_phase14_commit_sha": PHASE15_ACCEPTED_PHASE14_COMMIT_SHA,
        "accepted_phase14_tree_sha": PHASE15_ACCEPTED_PHASE14_TREE_SHA,
        "family": PHASE15_FAMILY,
        "phase6_specification_id": PHASE15_PHASE6_SPECIFICATION_ID,
        "phase6_specification_version": PHASE15_PHASE6_SPECIFICATION_VERSION,
        "phase6_specification_sha256": PHASE15_PHASE6_SPECIFICATION_SHA256,
        "frozen_at_utc": PHASE15_FROZEN_AT_UTC,
        "outcomes": ("REQUIREMENTS_FROZEN", "BLOCKED"),
        "requirement_statuses": ("PASS", "BLOCKED", "UNCOMPUTABLE"),
        "requirement_codes": PHASE15_REQUIREMENT_CODES,
        "requirement_definitions": PHASE15_REQUIREMENT_DEFINITIONS,
        "gap_states": ("PRESENT", "MOCK_ONLY", "STALE", "MISSING", "UNPROVEN"),
        "gaps": tuple(
            zip(
                PHASE15_GAP_CODES,
                PHASE15_GAP_STATES,
                PHASE15_GAP_SUMMARIES,
                PHASE15_GAP_EVIDENCE_REFS,
                strict=True,
            )
        ),
        "boundary_values": PHASE15_BOUNDARY_VALUES,
        "disclaimer": PHASE15_DISCLAIMER,
    },
)


def identity(sha256: str) -> UUID:
    """Derive the sole portable artifact identity from its frozen policy hash."""

    return uuid_from_sha256(PHASE15_ARTIFACT_NAMESPACE, sha256)


__all__ = [name for name in globals() if name.startswith("PHASE15_")] + [
    "canonical_json_bytes",
    "canonicalize",
    "domain_sha256",
    "identity",
]
