"""Canonical constants and hash domains for the Phase 19 prerequisite assessment."""

from __future__ import annotations

from types import MappingProxyType
from typing import Final
from uuid import UUID

from fable5_data.canonical import canonical_json_bytes as canonical_json_bytes
from fable5_data.canonical import canonicalize as canonicalize
from fable5_data.canonical import domain_sha256 as domain_sha256
from fable5_data.canonical import uuid_from_sha256

PHASE19_ARTIFACT_SCHEMA_VERSION: Final = "phase19-family-a-step3-prerequisite-assessment-v1"
PHASE19_ARTIFACT_HASH_DOMAIN: Final = PHASE19_ARTIFACT_SCHEMA_VERSION
PHASE19_ASSESSMENT_POLICY_ID: Final = "phase19-family-a-step3-prerequisite-assessment-policy-v1"
PHASE19_ASSESSMENT_POLICY_HASH_DOMAIN: Final = PHASE19_ASSESSMENT_POLICY_ID
PHASE19_PREREQUISITE_SCHEMA_VERSION: Final = "phase19-family-a-step3-prerequisite-v1"
PHASE19_PREREQUISITE_HASH_DOMAIN: Final = PHASE19_PREREQUISITE_SCHEMA_VERSION
PHASE19_REQUIRED_EVIDENCE_SCHEMA_VERSION: Final = (
    "phase19-family-a-step3-required-prior-evidence-v1"
)
PHASE19_REQUIRED_EVIDENCE_HASH_DOMAIN: Final = PHASE19_REQUIRED_EVIDENCE_SCHEMA_VERSION
PHASE19_GAP_BINDING_SCHEMA_VERSION: Final = "phase19-family-a-phase15-gap-binding-v1"
PHASE19_GAP_BINDING_HASH_DOMAIN: Final = PHASE19_GAP_BINDING_SCHEMA_VERSION
PHASE19_STEP_SCHEMA_VERSION: Final = "phase19-family-a-source-plan-step-evidence-v1"
PHASE19_STEP_HASH_DOMAIN: Final = PHASE19_STEP_SCHEMA_VERSION
PHASE19_OUTPUT_SCHEMA_VERSION: Final = "phase19-family-a-source-plan-output-v1"
PHASE19_OUTPUT_HASH_DOMAIN: Final = PHASE19_OUTPUT_SCHEMA_VERSION
PHASE19_PREREQUISITES_MANIFEST_HASH_DOMAIN: Final = "phase19-step3-prerequisites-manifest-v1"
PHASE19_REQUIRED_EVIDENCE_MANIFEST_HASH_DOMAIN: Final = (
    "phase19-step3-required-prior-evidence-manifest-v1"
)
PHASE19_GAPS_MANIFEST_HASH_DOMAIN: Final = "phase19-phase15-gap-bindings-manifest-v1"
PHASE19_STEPS_MANIFEST_HASH_DOMAIN: Final = "phase19-source-plan-steps-manifest-v1"
PHASE19_ARTIFACT_NAMESPACE: Final = UUID("2c232226-c183-5f60-bbd0-35837b0b9ed1")

PHASE19_ACCEPTED_PHASE18_COMMIT_SHA: Final = "16aac187fc3dbd6015306603c18be6e08cea8e4e"
PHASE19_ACCEPTED_PHASE18_TREE_SHA: Final = "b36ae615f13f39d0e661f18d1cc61e009b1aacf7"
PHASE19_PHASE18_ARTIFACT_ID: Final = "7008240c-e7a2-5d4b-9345-8c40d2d4c359"
PHASE19_PHASE18_ARTIFACT_SHA256: Final = (
    "2def399ee8c57d7c6d80f5282e856eda1acf34a8504058fbfc8ea2dea4aa30ae"
)
PHASE19_PHASE18_POLICY_SHA256: Final = (
    "e175f9b70333899b8c9626e459f091ea5c440494e006c2684448fa15fe0a4fbb"
)
PHASE19_PHASE18_INDEPENDENT_RIGHTS_REVIEW_SHA256: Final = (
    "a0c8808e865931cc88d9f71c578b42edcfb6e279e2426b4b30534d6c4626023b"
)
PHASE19_PHASE18_RIGHTS_CURRENTNESS_SHA256: Final = (
    "91b3b711e3c0b1b3b313e8ea45d9b73f96746ed4bd74478a7f6e7553510cdf63"
)
PHASE19_PHASE18_STEPS_MANIFEST_SHA256: Final = (
    "581ff73113eff3c2d54728106df556734084c053f8e52f0f4a9e6928d7478167"
)
PHASE19_PHASE18_INVENTORY_SHA256: Final = (
    "070f36391093385ccd0e7feafc54d18c08e71cc8aa145bd30acea07abbffc76c"
)
PHASE19_PHASE16_ORIGINAL_STEP3_SHA256: Final = (
    "331fafa9aa1d2e12871222257562eff7311435dad8e492fc4af58e5de4d28cec"
)
PHASE19_PHASE18_INHERITED_STEP3_EVIDENCE_SHA256: Final = (
    "0b7d8e73aebb70cba4144a2864b98cae58aefa06b3b0db5c16472bcbe1a37548"
)
PHASE19_PHASE15_GAPS_MANIFEST_SHA256: Final = (
    "9c70f11f85eb66dad6eed15a0a4907dec3fa4edc7b0da3d6adbad768b88b2f86"
)
PHASE19_PHASE6_SPECIFICATION_ID: Final = "phase6-a_cross_sectional_equity_ranking-research-pipeline"
PHASE19_PHASE6_SPECIFICATION_VERSION: Final = "v2"
PHASE19_PHASE6_SPECIFICATION_SHA256: Final = (
    "3967b3c0dffd6a27c4ac8012773621090b828e8bdc2f242611c34d81420b37bc"
)
PHASE19_FAMILY: Final = "A_CROSS_SECTIONAL_EQUITY_RANKING"
PHASE19_FROZEN_AT_UTC: Final = "2026-07-19T20:01:39.9672350Z"
PHASE19_OUTCOME: Final = "BLOCKED"
PHASE19_ASSESSMENT_STATE: Final = "OUTPUT_FROZEN"
PHASE19_AGGREGATE_CONCLUSION: Final = "BLOCKED_MISSING_EVALUATION_POLICY_AND_HOLDOUT"

PHASE19_GAP_CODES: Final = (
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
PHASE19_GAP_STATES: Final = (
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
PHASE19_SOURCE_GAP_SHA256S: Final = (
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

# category, code, definition, evidence state, satisfied, reason, related Phase 15 gaps
PHASE19_PREREQUISITE_ROWS: Final = (
    (
        "EVALUATION_POLICY",
        "OPERATIONAL_SOURCE_PRODUCT_COMPOSITION",
        "Require one exact operational source and product composition before policy approval.",
        "MISSING",
        False,
        "phase18_no_operational_selection",
        ("FULL_POINT_IN_TIME_DATASET", "INDEPENDENT_CURRENT_USE_RIGHTS"),
    ),
    (
        "EVALUATION_POLICY",
        "CURRENT_EXECUTED_USE_RIGHTS_AND_REVOCATION",
        "Require current executed rights, entitlement, retention, and revocation evidence.",
        "MISSING",
        False,
        "phase18_rights_review_blocked",
        ("INDEPENDENT_CURRENT_USE_RIGHTS", "RIGHTS_CURRENTNESS_REVOCATION"),
    ),
    (
        "EVALUATION_POLICY",
        "EXACT_DELIVERY_AND_SCHEMA_VERSIONS",
        "Require exact selected delivery methods and versioned schemas for every capability.",
        "UNPROVEN",
        False,
        "delivery_and_schema_unproven",
        ("EXTERNAL_CANDIDATE_QUALIFICATION",),
    ),
    (
        "EVALUATION_POLICY",
        "FULL_POINT_IN_TIME_COVERAGE_AND_MISSINGNESS",
        "Require complete point-in-time history, coverage boundaries, and missingness semantics.",
        "MISSING",
        False,
        "non_synthetic_dataset_missing",
        (
            "FULL_POINT_IN_TIME_DATASET",
            "HISTORICAL_MEMBERSHIP_AND_DELISTING",
            "SECTOR_LIQUIDITY_MACRO_HISTORY",
        ),
    ),
    (
        "EVALUATION_POLICY",
        "SIGNAL_ACTION_LABEL_AND_HORIZON",
        "Require an externally valid deterministic action rule, label interval, and horizon.",
        "MOCK_ONLY",
        False,
        "signal_and_horizon_mock_only",
        ("FAMILY_A_SIGNAL_AND_HORIZON",),
    ),
    (
        "EVALUATION_POLICY",
        "DECISION_CALENDAR_SAMPLE_BOUNDARIES_AND_ADEQUACY",
        "Require the source-specific decision calendar, sample boundaries, and adequacy gates.",
        "MISSING",
        False,
        "data_specific_geometry_missing",
        ("NON_SYNTHETIC_EVALUATION_POLICY",),
    ),
    (
        "EVALUATION_POLICY",
        "PURGED_WALK_FORWARD_MECHANICS",
        "Require approved non-synthetic nested chronology and label-interval purge mechanics.",
        "MOCK_ONLY",
        False,
        "walk_forward_mechanics_mock_only",
        ("PURGED_WALK_FORWARD_MECHANICS",),
    ),
    (
        "EVALUATION_POLICY",
        "EMBARGO_APPLICABILITY",
        "Require a source-specific embargo applicability decision before a holdout is defined.",
        "UNPROVEN",
        False,
        "embargo_applicability_unproven",
        ("EMBARGO_APPLICABILITY_DECISION",),
    ),
    (
        "EVALUATION_POLICY",
        "COMPLETE_TRIAL_ACCOUNTING_DSR_PBO_POLICY",
        "Require complete trial accounting and approved computable DSR and PBO methods and gates.",
        "MOCK_ONLY",
        False,
        "trial_dsr_pbo_policy_mock_only",
        ("DSR_PBO_PROMOTION_GATES",),
    ),
    (
        "EVALUATION_POLICY",
        "LEAKAGE_AND_DATA_QUALITY_GATES",
        "Require non-synthetic leakage and data-quality gates over exact selected schemas.",
        "MOCK_ONLY",
        False,
        "leakage_gates_mock_only",
        ("LEAKAGE_FREE_RESULT",),
    ),
    (
        "EVALUATION_POLICY",
        "MARKET_CALIBRATED_COST_SLIPPAGE_CAPACITY",
        "Require market-calibrated fees, spread, impact, delay, borrow, and capacity inputs.",
        "MOCK_ONLY",
        False,
        "cost_slippage_calibration_mock_only",
        ("MARKET_CALIBRATED_COST_SLIPPAGE",),
    ),
    (
        "EVALUATION_POLICY",
        "STRESS_REGIME_CRISIS_THRESHOLDS",
        "Require approved data-specific stress gates, regimes, and predeclared crisis windows.",
        "MOCK_ONLY",
        False,
        "stress_and_regime_policy_mock_only",
        ("SECTOR_LIQUIDITY_MACRO_HISTORY", "MARKET_CALIBRATED_COST_SLIPPAGE"),
    ),
    (
        "EVALUATION_POLICY",
        "COMPUTABLE_DATA_SPECIFIC_RISK_LIMITS",
        "Require computable limits appropriate to the selected data and strategy policy.",
        "MOCK_ONLY",
        False,
        "risk_limits_mock_only",
        ("PRE_ORDER_RISK",),
    ),
    (
        "EVALUATION_POLICY",
        "REPRODUCIBILITY_AUDIT_SCHEMA",
        "Require immutable config, snapshot, Git, seed, trial-count, and UTC audit fields.",
        "PRESENT",
        True,
        "audit_schema_present_only",
        ("IMMUTABLE_AUDIT_SCHEMA",),
    ),
    (
        "EVALUATION_POLICY",
        "NON_SYNTHETIC_EVALUATION_POLICY",
        "Require a complete approved source-specific policy hash before Step 3 can start.",
        "MISSING",
        False,
        "evaluation_policy_hash_missing",
        ("NON_SYNTHETIC_EVALUATION_POLICY",),
    ),
    (
        "CONFIRMATION_HOLDOUT",
        "SOURCE_BOUND_CONTIGUOUS_CONFIRMATION_INTERVAL",
        "Require a source-bound contiguous confirmation interval fixed before observation.",
        "MISSING",
        False,
        "confirmation_interval_missing",
        ("NON_SYNTHETIC_EVALUATION_POLICY",),
    ),
    (
        "CONFIRMATION_HOLDOUT",
        "HOLDOUT_DECISION_CALENDAR_AND_LABEL_BOUNDARIES",
        "Require exact decision-calendar and label-interval boundaries for the holdout.",
        "MISSING",
        False,
        "holdout_calendar_and_boundaries_missing",
        ("FULL_POINT_IN_TIME_DATASET", "NON_SYNTHETIC_EVALUATION_POLICY"),
    ),
    (
        "CONFIRMATION_HOLDOUT",
        "HOLDOUT_EXCLUSION_CONSUMPTION_AND_REPLACEMENT_RULES",
        "Require source-specific exclusion, opening, consumption, and replacement rules.",
        "MOCK_ONLY",
        False,
        "holdout_rules_mock_only",
        ("NON_SYNTHETIC_EVALUATION_PATH",),
    ),
    (
        "CONFIRMATION_HOLDOUT",
        "UNTOUCHED_CONFIRMATION_HOLDOUT_DEFINITION",
        "Require one unopened immutable holdout-definition hash before Step 3 can start.",
        "MISSING",
        False,
        "confirmation_holdout_hash_missing",
        ("NON_SYNTHETIC_EVALUATION_POLICY", "NON_SYNTHETIC_EVALUATION_PATH"),
    ),
)

# name, state, produced, reason. A value/hash field is deliberately absent from this schema.
PHASE19_REQUIRED_EVIDENCE_ROWS: Final = (
    (
        "non_synthetic_evaluation_policy_sha256",
        "MISSING",
        False,
        "complete_non_synthetic_evaluation_policy_not_created",
    ),
    (
        "confirmation_holdout_definition_sha256",
        "MISSING",
        False,
        "untouched_confirmation_holdout_definition_not_created",
    ),
)

PHASE19_STEP_CODES: Final = (
    "SELECT_CANDIDATE_PRODUCTS",
    "REVIEW_CURRENT_USE_RIGHTS",
    "QUALIFY_BOUNDED_READ_ONLY_SAMPLES",
    "PRODUCE_FULL_HISTORY_COVERAGE_MANIFEST",
    "RECONCILE_TEMPORAL_IDENTITY_REVISION_SEMANTICS",
    "DESIGN_LOCAL_QUARANTINE_AND_CANONICAL_SNAPSHOT",
    "REQUEST_SEPARATE_INGESTION_AUTHORITY",
)
PHASE19_STEP_STATES: Final = (
    "OUTPUT_FROZEN",
    "OUTPUT_FROZEN",
    "NOT_STARTED",
    "NOT_STARTED",
    "NOT_STARTED",
    "NOT_STARTED",
    "NOT_STARTED",
)
PHASE19_STEP_REASONS: Final = (
    "inventory_output_inherited_and_frozen",
    "blocking_rights_review_outputs_inherited_no_operational_clearance",
    "required_prior_evidence_missing",
    "prerequisite_not_satisfied",
    "prerequisite_not_satisfied",
    "prerequisite_not_satisfied",
    "prerequisite_not_satisfied",
)
PHASE19_STEP_PREREQUISITES: Final = (
    (),
    ("SELECT_CANDIDATE_PRODUCTS",),
    ("SELECT_CANDIDATE_PRODUCTS", "REVIEW_CURRENT_USE_RIGHTS"),
    ("QUALIFY_BOUNDED_READ_ONLY_SAMPLES",),
    ("PRODUCE_FULL_HISTORY_COVERAGE_MANIFEST",),
    ("REVIEW_CURRENT_USE_RIGHTS", "RECONCILE_TEMPORAL_IDENTITY_REVISION_SEMANTICS"),
    ("DESIGN_LOCAL_QUARANTINE_AND_CANONICAL_SNAPSHOT",),
)
PHASE19_STEP_REQUIRED_PRIOR_EVIDENCE: Final = (
    (),
    (),
    ("non_synthetic_evaluation_policy_sha256", "confirmation_holdout_definition_sha256"),
    (),
    (),
    (),
    (),
)
PHASE19_STEP_REQUIRED_OUTPUTS: Final = (
    ("candidate_product_inventory_sha256",),
    ("independent_rights_review_sha256", "rights_currentness_sha256"),
    ("qualification_artifact_set_sha256",),
    ("full_history_coverage_manifest_sha256",),
    ("temporal_identity_revision_reconciliation_sha256",),
    ("quarantine_canonical_snapshot_design_sha256",),
    ("separate_ingestion_authority_evidence_sha256",),
)

PHASE19_BOUNDARY_VALUES: Final = MappingProxyType(
    {
        "metadata_only": True,
        "requirements_only": True,
        "runtime_network_disabled": True,
        "revalidation_required_before_external_action": True,
        "inherited_phase15_gaps_unchanged": True,
        "provider_selected": False,
        "product_selected": False,
        "source_selected": False,
        "operational_source_product_composition_selected": False,
        "credentials_loaded": False,
        "account_verified": False,
        "subscription_verified": False,
        "entitlement_verified": False,
        "executed_license_reviewed": False,
        "rights_currentness_guaranteed": False,
        "rights_verified": False,
        "rights_granted": False,
        "operational_use_cleared": False,
        "legal_opinion_obtained": False,
        "independent_legal_counsel_reviewed": False,
        "provider_or_counsel_attestation_obtained": False,
        "delivery_proven": False,
        "schema_proven": False,
        "coverage_proven": False,
        "fitness_verified": False,
        "current_availability_proven": False,
        "operational_external_request_performed": False,
        "provider_data_request_performed": False,
        "provider_account_verification_performed": False,
        "entitlement_verification_performed": False,
        "external_sample_qualification_authorized": False,
        "external_sample_qualified": False,
        "external_data_capture_authorized": False,
        "provider_payload_persisted": False,
        "licensed_data_persisted": False,
        "research_ingestion_authorized": False,
        "research_snapshot_created": False,
        "research_data_eligible": False,
        "non_synthetic_evaluation_policy_created": False,
        "non_synthetic_evaluation_policy_approved": False,
        "evaluation_policy_approved": False,
        "confirmation_holdout_definition_created": False,
        "confirmation_holdout_defined": False,
        "confirmation_holdout_opened": False,
        "confirmation_holdout_consumed": False,
        "step3_required_prior_evidence_complete": False,
        "step3_eligible": False,
        "step3_external_action_authorized": False,
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
)

PHASE19_BLOCK_REASON: Final = (
    "Phase 18 produced a blocked public-terms review with no operational source or product "
    "selection; exact delivery, schemas, complete point-in-time coverage, approved non-synthetic "
    "evaluation policy, and untouched confirmation holdout definition remain missing or unproven."
)
PHASE19_DISCLAIMER: Final = (
    "Portable prerequisite assessment only. OUTPUT_FROZEN means the blocked gap assessment is "
    "deterministic; it is not an evaluation policy, holdout definition, qualification, data right, "
    "research authorization, performance result, execution clearance, or order authority."
)

PHASE19_ASSESSMENT_POLICY_SHA256: Final = domain_sha256(
    PHASE19_ASSESSMENT_POLICY_HASH_DOMAIN,
    {
        "assessment_policy_id": PHASE19_ASSESSMENT_POLICY_ID,
        "artifact_uuid_namespace": str(PHASE19_ARTIFACT_NAMESPACE),
        "schemas_and_hash_domains": (
            (PHASE19_ARTIFACT_SCHEMA_VERSION, PHASE19_ARTIFACT_HASH_DOMAIN),
            (PHASE19_PREREQUISITE_SCHEMA_VERSION, PHASE19_PREREQUISITE_HASH_DOMAIN),
            (
                PHASE19_REQUIRED_EVIDENCE_SCHEMA_VERSION,
                PHASE19_REQUIRED_EVIDENCE_HASH_DOMAIN,
            ),
            (PHASE19_GAP_BINDING_SCHEMA_VERSION, PHASE19_GAP_BINDING_HASH_DOMAIN),
            (PHASE19_STEP_SCHEMA_VERSION, PHASE19_STEP_HASH_DOMAIN),
            (PHASE19_OUTPUT_SCHEMA_VERSION, PHASE19_OUTPUT_HASH_DOMAIN),
            PHASE19_PREREQUISITES_MANIFEST_HASH_DOMAIN,
            PHASE19_REQUIRED_EVIDENCE_MANIFEST_HASH_DOMAIN,
            PHASE19_GAPS_MANIFEST_HASH_DOMAIN,
            PHASE19_STEPS_MANIFEST_HASH_DOMAIN,
        ),
        "accepted_phase18_identity": (
            PHASE19_ACCEPTED_PHASE18_COMMIT_SHA,
            PHASE19_ACCEPTED_PHASE18_TREE_SHA,
            PHASE19_PHASE18_ARTIFACT_ID,
            PHASE19_PHASE18_ARTIFACT_SHA256,
            PHASE19_PHASE18_POLICY_SHA256,
            PHASE19_PHASE18_INDEPENDENT_RIGHTS_REVIEW_SHA256,
            PHASE19_PHASE18_RIGHTS_CURRENTNESS_SHA256,
            PHASE19_PHASE18_STEPS_MANIFEST_SHA256,
        ),
        "step3_identities": (
            PHASE19_PHASE16_ORIGINAL_STEP3_SHA256,
            PHASE19_PHASE18_INHERITED_STEP3_EVIDENCE_SHA256,
        ),
        "phase15_gaps_manifest_sha256": PHASE19_PHASE15_GAPS_MANIFEST_SHA256,
        "phase6_specification": (
            PHASE19_PHASE6_SPECIFICATION_ID,
            PHASE19_PHASE6_SPECIFICATION_VERSION,
            PHASE19_PHASE6_SPECIFICATION_SHA256,
        ),
        "family": PHASE19_FAMILY,
        "frozen_at_utc": PHASE19_FROZEN_AT_UTC,
        "outcome": PHASE19_OUTCOME,
        "assessment_state": PHASE19_ASSESSMENT_STATE,
        "aggregate_conclusion": PHASE19_AGGREGATE_CONCLUSION,
        "phase15_gap_rows": tuple(
            zip(
                PHASE19_GAP_CODES,
                PHASE19_GAP_STATES,
                PHASE19_SOURCE_GAP_SHA256S,
                strict=True,
            )
        ),
        "prerequisite_rows": PHASE19_PREREQUISITE_ROWS,
        "required_evidence_rows": PHASE19_REQUIRED_EVIDENCE_ROWS,
        "steps": tuple(
            zip(
                PHASE19_STEP_CODES,
                PHASE19_STEP_STATES,
                PHASE19_STEP_REASONS,
                PHASE19_STEP_PREREQUISITES,
                PHASE19_STEP_REQUIRED_PRIOR_EVIDENCE,
                PHASE19_STEP_REQUIRED_OUTPUTS,
                strict=True,
            )
        ),
        "boundary_values": PHASE19_BOUNDARY_VALUES,
        "block_reason": PHASE19_BLOCK_REASON,
        "disclaimer": PHASE19_DISCLAIMER,
    },
)


def identity(sha256: str) -> UUID:
    return uuid_from_sha256(PHASE19_ARTIFACT_NAMESPACE, sha256)


__all__ = [name for name in globals() if name.startswith("PHASE19_")] + [
    "canonical_json_bytes",
    "canonicalize",
    "domain_sha256",
    "identity",
]
