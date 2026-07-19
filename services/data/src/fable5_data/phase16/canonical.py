"""Canonical constants and hash domains for the Phase 16 source plan."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Final
from uuid import UUID

from fable5_data.canonical import canonical_json_bytes as canonical_json_bytes
from fable5_data.canonical import canonicalize as canonicalize
from fable5_data.canonical import domain_sha256 as domain_sha256
from fable5_data.canonical import uuid_from_sha256

PHASE16_ARTIFACT_SCHEMA_VERSION: Final = "phase16-family-a-point-in-time-source-plan-v1"
PHASE16_ARTIFACT_HASH_DOMAIN: Final = PHASE16_ARTIFACT_SCHEMA_VERSION
PHASE16_POLICY_ID: Final = "phase16-family-a-point-in-time-source-plan-policy-v1"
PHASE16_POLICY_HASH_DOMAIN: Final = PHASE16_POLICY_ID
PHASE16_REQUIREMENT_SCHEMA_VERSION: Final = (
    "phase16-family-a-point-in-time-source-plan-requirement-v1"
)
PHASE16_REQUIREMENT_HASH_DOMAIN: Final = PHASE16_REQUIREMENT_SCHEMA_VERSION
PHASE16_CAPABILITY_SCHEMA_VERSION: Final = (
    "phase16-family-a-point-in-time-source-plan-capability-v1"
)
PHASE16_CAPABILITY_HASH_DOMAIN: Final = PHASE16_CAPABILITY_SCHEMA_VERSION
PHASE16_CANDIDATE_SCHEMA_VERSION: Final = "phase16-family-a-point-in-time-source-plan-candidate-v1"
PHASE16_CANDIDATE_HASH_DOMAIN: Final = PHASE16_CANDIDATE_SCHEMA_VERSION
PHASE16_STEP_SCHEMA_VERSION: Final = "phase16-family-a-point-in-time-source-plan-step-v1"
PHASE16_STEP_HASH_DOMAIN: Final = PHASE16_STEP_SCHEMA_VERSION
PHASE16_GAP_BINDING_SCHEMA_VERSION: Final = (
    "phase16-family-a-point-in-time-source-plan-gap-binding-v1"
)
PHASE16_GAP_BINDING_HASH_DOMAIN: Final = PHASE16_GAP_BINDING_SCHEMA_VERSION
PHASE16_REQUIREMENTS_MANIFEST_HASH_DOMAIN: Final = "phase16-source-plan-requirements-manifest-v1"
PHASE16_CAPABILITIES_MANIFEST_HASH_DOMAIN: Final = "phase16-source-plan-capabilities-manifest-v1"
PHASE16_CANDIDATES_MANIFEST_HASH_DOMAIN: Final = "phase16-source-plan-candidates-manifest-v1"
PHASE16_STEPS_MANIFEST_HASH_DOMAIN: Final = "phase16-source-plan-steps-manifest-v1"
PHASE16_GAPS_MANIFEST_HASH_DOMAIN: Final = "phase16-source-plan-gap-bindings-manifest-v1"
PHASE16_EVIDENCE_HASH_DOMAIN: Final = "phase16-source-plan-evidence-v1"
PHASE16_ARTIFACT_NAMESPACE: Final = UUID("657156b0-345e-5d6e-ae1b-1f27e32b40ac")

PHASE16_ACCEPTED_PHASE15_COMMIT_SHA: Final = "5b3052eb8f020d77cc3750b34190b4b2fa5fc16c"
PHASE16_ACCEPTED_PHASE15_TREE_SHA: Final = "7fab5a2b2eb2f8f821b969d9cb031c806e064d28"
PHASE16_PHASE15_ARTIFACT_ID: Final = "c29b8139-da80-556b-b150-a5ca9603d265"
PHASE16_PHASE15_ARTIFACT_SHA256: Final = (
    "575ce4c51e9102790d75edc4a330c3e9f1d9eb505eb33ccf22d8a9c9e50200d6"
)
PHASE16_PHASE15_POLICY_SHA256: Final = (
    "ba4603caaffe90d561f3beaa566746b1f3b900e2cf7d5e24b2cd94537597821b"
)
PHASE16_PHASE15_REQUIREMENTS_MANIFEST_SHA256: Final = (
    "7743721c6fe46bc0847bb189c4db7dedc4325b4cc05aa6007c7921eb348f73b6"
)
PHASE16_PHASE15_GAPS_MANIFEST_SHA256: Final = (
    "9c70f11f85eb66dad6eed15a0a4907dec3fa4edc7b0da3d6adbad768b88b2f86"
)
PHASE16_FAMILY: Final = "A_CROSS_SECTIONAL_EQUITY_RANKING"
PHASE16_PHASE6_SPECIFICATION_ID: Final = "phase6-a_cross_sectional_equity_ranking-research-pipeline"
PHASE16_PHASE6_SPECIFICATION_VERSION: Final = "v2"
PHASE16_PHASE6_SPECIFICATION_SHA256: Final = (
    "3967b3c0dffd6a27c4ac8012773621090b828e8bdc2f242611c34d81420b37bc"
)
PHASE16_FROZEN_AT_UTC: Final = datetime(2026, 7, 18, tzinfo=UTC)

PHASE16_REQUIREMENT_CODES: Final = (
    "PHASE15_ADMISSION_SPECIFICATION_BOUND",
    "FAMILY_A_CAPABILITY_SET_BOUND",
    "SECURITY_MASTER_IDENTITY_HISTORY_REQUIRED",
    "UNIVERSE_MEMBERSHIP_DELISTING_HISTORY_REQUIRED",
    "RAW_OHLCV_CORPORATE_ACTION_HISTORY_REQUIRED",
    "AS_REPORTED_FUNDAMENTAL_VINTAGES_REQUIRED",
    "SECTOR_LIQUIDITY_HISTORY_REQUIRED",
    "MACRO_VINTAGE_RELEASE_HISTORY_REQUIRED",
    "TEMPORAL_REVISION_COVERAGE_MANIFEST_REQUIRED",
    "INDEPENDENT_RIGHTS_CURRENTNESS_REVIEW_REQUIRED",
    "QUARANTINE_CANONICALIZATION_RECONCILIATION_REQUIRED",
    "CAPTURE_INGESTION_RESEARCH_EXECUTION_AUTHORITY_ABSENT",
)
PHASE16_REQUIREMENT_DEFINITIONS: Final = (
    "Bind the accepted Phase 15 admission specification and its complete unchanged gap ledger.",
    "Bind the exact seven Family A point-in-time capabilities without selecting a source.",
    "Require stable security, listing, ticker, exchange, and sector identity histories.",
    "Require point-in-time membership, inactive coverage, delisting events, and delisting returns.",
    "Require raw OHLCV plus separately auditable announcement-time corporate-action history.",
    "Require as-reported fundamental vintages, release timestamps, amendments, and revisions.",
    "Require point-in-time sector classification and market-calibrated liquidity-depth history.",
    "Require macro vintages with release availability and revision history.",
    "Require full-history boundaries, temporal fields, revision semantics, and coverage manifests.",
    "Require independently reviewed current rights, retention scope, and revocation evidence.",
    "Require local quarantine, deterministic canonicalization, lineage, and reconciliation design.",
    (
        "Keep source selection, capture, ingestion, research, promotion, risk, execution, "
        "and orders absent."
    ),
)

PHASE16_CAPABILITY_CODES: Final = (
    "security_master",
    "universe_membership",
    "ohlcv",
    "corporate_actions",
    "delistings",
    "as_reported_fundamentals",
    "macro_regime_inputs",
)

PHASE16_CANDIDATE_CODES: Final = (
    "TIINGO_PHASE13_BOUNDED_CANDIDATE",
    "MORNINGSTAR_CRSP_US_STOCK_DATABASES_CANDIDATE",
    "MORNINGSTAR_CRSP_COMPUSTAT_MERGED_DATABASE_CANDIDATE",
    "SEC_EDGAR_SUBMISSIONS_XBRL_CANDIDATE",
    "FEDERAL_RESERVE_ALFRED_VINTAGES_CANDIDATE",
    "HISTORICAL_LIQUIDITY_PRODUCT_UNSELECTED",
)
PHASE16_CANDIDATE_STATES: Final = (
    "UNPROVEN",
    "UNPROVEN",
    "UNPROVEN",
    "UNPROVEN",
    "UNPROVEN",
    "MISSING",
)

PHASE16_STEP_CODES: Final = (
    "SELECT_CANDIDATE_PRODUCTS",
    "REVIEW_CURRENT_USE_RIGHTS",
    "QUALIFY_BOUNDED_READ_ONLY_SAMPLES",
    "PRODUCE_FULL_HISTORY_COVERAGE_MANIFEST",
    "RECONCILE_TEMPORAL_IDENTITY_REVISION_SEMANTICS",
    "DESIGN_LOCAL_QUARANTINE_AND_CANONICAL_SNAPSHOT",
    "REQUEST_SEPARATE_INGESTION_AUTHORITY",
)
PHASE16_STEP_DEFINITIONS: Final = (
    (
        "Select exact candidate products only after separately authorized current "
        "documentation review."
    ),
    (
        "Obtain independent current storage, non-display, derived-data, retention, and "
        "revocation review."
    ),
    (
        "Only after a complete non-synthetic evaluation policy and untouched confirmation "
        "holdout definition are hash-frozen, run separately authorized bounded read-only "
        "qualification without treating a sample as a dataset."
    ),
    (
        "Produce a complete point-in-time history and missingness manifest for every "
        "required capability."
    ),
    "Reconcile stable identity, availability, revision, corporate-action, and delisting semantics.",
    "Design rights-gated local quarantine and canonical snapshot behavior before any ingestion.",
    "Request separate authority only after every prior evidence output is complete and current.",
)
PHASE16_STEP_PREREQUISITES: Final = (
    (),
    ("SELECT_CANDIDATE_PRODUCTS",),
    ("SELECT_CANDIDATE_PRODUCTS", "REVIEW_CURRENT_USE_RIGHTS"),
    ("QUALIFY_BOUNDED_READ_ONLY_SAMPLES",),
    ("PRODUCE_FULL_HISTORY_COVERAGE_MANIFEST",),
    (
        "REVIEW_CURRENT_USE_RIGHTS",
        "RECONCILE_TEMPORAL_IDENTITY_REVISION_SEMANTICS",
    ),
    ("DESIGN_LOCAL_QUARANTINE_AND_CANONICAL_SNAPSHOT",),
)
PHASE16_STEP_REQUIRED_PRIOR_EVIDENCE: Final = (
    (),
    (),
    (
        "non_synthetic_evaluation_policy_sha256",
        "confirmation_holdout_definition_sha256",
    ),
    (),
    (),
    (),
    (),
)
PHASE16_STEP_REQUIRED_OUTPUTS: Final = (
    ("candidate_product_inventory_sha256",),
    ("independent_rights_review_sha256", "rights_currentness_sha256"),
    ("qualification_artifact_set_sha256",),
    ("full_history_coverage_manifest_sha256",),
    ("temporal_identity_revision_reconciliation_sha256",),
    ("quarantine_canonical_snapshot_design_sha256",),
    ("separate_ingestion_authority_evidence_sha256",),
)

PHASE16_PHASE15_GAP_CODES: Final = (
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
PHASE16_PHASE15_GAP_STATES: Final = (
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
PHASE16_PHASE15_GAP_SHA256S: Final = (
    "29c8594ba865b97d5421c381647bc91773ca3ef48388e65d563a5eaa085319d5",
    "4ddf94cbdadd7b61f51b97b9105e6adea6a590cc622271e002356a9352c7a49a",
    "9c110da463f048a8c577ebb16b65fdf4654aec2a93826ab2b5bfd0f1b936d580",
    "441afc30e509ebfedfbcb888a77537408e3c2d530d32470c98d2c1035636be61",
    "f36ddc92e8deffcf57bf1e98eeb9c2d0be91807ed0abdbc5690dda22ec97e801",
    "0472fddba255153f3e7cf3dabc0bc025c05714897762e2912cf3a887e48738ff",
    "3d0b7e6a74afe8fe70beb8cfa2cc4ae8d15c6a647ba43e45daa1b1c2f14b3c7b",
    "9a484c0596b92e7f659fac58198a707e9b8c8e372ace7af6f419cb15d31d81bb",
    "6fdcae7db872a98e629a1e93df9aa6ac75f83ed5902771b7efbce5b08a04102a",
    "233a469add2a3b0b0a216780f6c4a259e9d2cd9a81dbd0138be91b7fa81dd13a",
    "352dffce8463b24ae2e4eaba65a207c21d8ab4f53592619061f7e8180c38a73c",
    "bee9a7ac0ec623281bbc5b0293e349d0f926db5bf59ecf86af6888d0dcae726d",
    "041d3fdff4a5fc3f8b6f337de729890d3569ec9e619a70c2f06c342ecad53be4",
    "006adff9e34c540b58c641f84218bfcbbb66323c833da3de800e1e8029a8bf98",
    "27e71e37a9991fd04e25d61e005f5eeb167804be7adb5d5ef473089f077e0d8f",
    "f3d4a2625fcedf362a392ab761056a7e75257f9eb2fb51b1d11038060187868d",
    "870786a3addaf720aca5bbe20ec585643794bb46b78c64003f1a81df7875260a",
    "9afe4ae29601ccf3891f52719e2b0a7db5573f9ee96d3db7c8878f428dcf4fba",
    "617881a4d22da3e7e72e6f335519d66e6593c3607fdcfe398d91c28ef9810b20",
)

PHASE16_BOUNDARY_VALUES: Final = {
    "external_request_performed": False,
    "external_verification_performed": False,
    "source_selected": False,
    "provider_selected": False,
    "product_selected": False,
    "credentials_loaded": False,
    "rights_verified": False,
    "rights_granted": False,
    "external_data_capture_authorized": False,
    "provider_payload_persisted": False,
    "licensed_data_persisted": False,
    "research_ingestion_authorized": False,
    "research_snapshot_created": False,
    "research_data_eligible": False,
    "evaluation_policy_approved": False,
    "confirmation_holdout_defined": False,
    "confirmation_holdout_opened": False,
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
PHASE16_DISCLAIMER: Final = (
    "Source-plan evidence only; no source or product selection, rights verification, external "
    "request, data capture, persistence, ingestion, snapshot, evaluation policy, holdout, research "
    "result, promotion, risk clearance, execution authority, order, or personalized advice."
)

PHASE16_POLICY_SHA256: Final = domain_sha256(
    PHASE16_POLICY_HASH_DOMAIN,
    {
        "policy_id": PHASE16_POLICY_ID,
        "artifact_uuid_namespace": str(PHASE16_ARTIFACT_NAMESPACE),
        "schema_and_hash_domains": (
            ("artifact", PHASE16_ARTIFACT_SCHEMA_VERSION, PHASE16_ARTIFACT_HASH_DOMAIN),
            (
                "requirement",
                PHASE16_REQUIREMENT_SCHEMA_VERSION,
                PHASE16_REQUIREMENT_HASH_DOMAIN,
            ),
            (
                "capability",
                PHASE16_CAPABILITY_SCHEMA_VERSION,
                PHASE16_CAPABILITY_HASH_DOMAIN,
            ),
            ("candidate", PHASE16_CANDIDATE_SCHEMA_VERSION, PHASE16_CANDIDATE_HASH_DOMAIN),
            ("step", PHASE16_STEP_SCHEMA_VERSION, PHASE16_STEP_HASH_DOMAIN),
            (
                "gap_binding",
                PHASE16_GAP_BINDING_SCHEMA_VERSION,
                PHASE16_GAP_BINDING_HASH_DOMAIN,
            ),
        ),
        "manifest_hash_domains": (
            PHASE16_REQUIREMENTS_MANIFEST_HASH_DOMAIN,
            PHASE16_CAPABILITIES_MANIFEST_HASH_DOMAIN,
            PHASE16_CANDIDATES_MANIFEST_HASH_DOMAIN,
            PHASE16_STEPS_MANIFEST_HASH_DOMAIN,
            PHASE16_GAPS_MANIFEST_HASH_DOMAIN,
        ),
        "evidence_hash_domain": PHASE16_EVIDENCE_HASH_DOMAIN,
        "accepted_phase15_commit_sha": PHASE16_ACCEPTED_PHASE15_COMMIT_SHA,
        "accepted_phase15_tree_sha": PHASE16_ACCEPTED_PHASE15_TREE_SHA,
        "phase15_artifact_sha256": PHASE16_PHASE15_ARTIFACT_SHA256,
        "phase15_policy_sha256": PHASE16_PHASE15_POLICY_SHA256,
        "phase15_requirements_manifest_sha256": PHASE16_PHASE15_REQUIREMENTS_MANIFEST_SHA256,
        "phase15_gaps_manifest_sha256": PHASE16_PHASE15_GAPS_MANIFEST_SHA256,
        "family": PHASE16_FAMILY,
        "phase6_specification_sha256": PHASE16_PHASE6_SPECIFICATION_SHA256,
        "frozen_at_utc": PHASE16_FROZEN_AT_UTC,
        "outcomes": ("PLAN_FROZEN", "BLOCKED"),
        "requirement_statuses": ("PASS", "BLOCKED", "UNCOMPUTABLE"),
        "requirement_reason_by_status": (
            ("PASS", "frozen_source_plan_requirement"),
            ("BLOCKED", "requirement_blocked"),
            ("UNCOMPUTABLE", "requirement_uncomputable"),
        ),
        "requirements": tuple(
            zip(PHASE16_REQUIREMENT_CODES, PHASE16_REQUIREMENT_DEFINITIONS, strict=True)
        ),
        "capabilities": PHASE16_CAPABILITY_CODES,
        "capability_invariants": (("required", True), ("source_selected", False)),
        "candidates": tuple(zip(PHASE16_CANDIDATE_CODES, PHASE16_CANDIDATE_STATES, strict=True)),
        "candidate_states": ("UNPROVEN", "MISSING"),
        "candidate_invariants": (
            ("candidate_only", True),
            ("selected", False),
            ("rights_verified", False),
            ("external_verification_performed", False),
        ),
        "step_invariants": (("state", "NOT_STARTED"), ("external_action_authorized", False)),
        "steps": tuple(
            zip(
                PHASE16_STEP_CODES,
                PHASE16_STEP_DEFINITIONS,
                PHASE16_STEP_PREREQUISITES,
                PHASE16_STEP_REQUIRED_PRIOR_EVIDENCE,
                PHASE16_STEP_REQUIRED_OUTPUTS,
                strict=True,
            )
        ),
        "gap_states": ("PRESENT", "MOCK_ONLY", "STALE", "MISSING", "UNPROVEN"),
        "phase15_gaps": tuple(
            zip(
                PHASE16_PHASE15_GAP_CODES,
                PHASE16_PHASE15_GAP_STATES,
                PHASE16_PHASE15_GAP_SHA256S,
                strict=True,
            )
        ),
        "boundary_values": PHASE16_BOUNDARY_VALUES,
        "disclaimer": PHASE16_DISCLAIMER,
    },
)


def identity(sha256: str) -> UUID:
    return uuid_from_sha256(PHASE16_ARTIFACT_NAMESPACE, sha256)


__all__ = [name for name in globals() if name.startswith("PHASE16_")] + [
    "canonical_json_bytes",
    "canonicalize",
    "domain_sha256",
    "identity",
]
