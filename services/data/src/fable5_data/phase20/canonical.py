"""Canonical constants and hash domains for the Phase 20 input register."""

from __future__ import annotations

from types import MappingProxyType
from typing import Final
from uuid import UUID

from fable5_data.canonical import canonical_json_bytes as canonical_json_bytes
from fable5_data.canonical import canonicalize as canonicalize
from fable5_data.canonical import domain_sha256 as domain_sha256
from fable5_data.canonical import uuid_from_sha256
from fable5_data.phase19.canonical import (
    PHASE19_GAP_CODES,
    PHASE19_GAP_STATES,
    PHASE19_PREREQUISITE_ROWS,
    PHASE19_SOURCE_GAP_SHA256S,
    PHASE19_STEP_CODES,
    PHASE19_STEP_REASONS,
    PHASE19_STEP_STATES,
)

PHASE20_ARTIFACT_SCHEMA_VERSION: Final = "phase20-family-a-evaluation-holdout-input-register-v1"
PHASE20_ARTIFACT_HASH_DOMAIN: Final = PHASE20_ARTIFACT_SCHEMA_VERSION
PHASE20_INHERITED_PREREQUISITE_SCHEMA_VERSION: Final = (
    "phase20-family-a-inherited-phase19-prerequisite-v1"
)
PHASE20_INHERITED_PREREQUISITE_HASH_DOMAIN: Final = PHASE20_INHERITED_PREREQUISITE_SCHEMA_VERSION
PHASE20_INPUT_REQUIREMENT_SCHEMA_VERSION: Final = (
    "phase20-family-a-evaluation-holdout-input-requirement-v1"
)
PHASE20_INPUT_REQUIREMENT_HASH_DOMAIN: Final = PHASE20_INPUT_REQUIREMENT_SCHEMA_VERSION
PHASE20_FUTURE_EVIDENCE_SCHEMA_VERSION: Final = "phase20-family-a-missing-future-evidence-v1"
PHASE20_FUTURE_EVIDENCE_HASH_DOMAIN: Final = PHASE20_FUTURE_EVIDENCE_SCHEMA_VERSION
PHASE20_TRANSITION_RULE_SCHEMA_VERSION: Final = (
    "phase20-family-a-future-evidence-transition-rule-v1"
)
PHASE20_TRANSITION_RULE_HASH_DOMAIN: Final = PHASE20_TRANSITION_RULE_SCHEMA_VERSION
PHASE20_DEPENDENCY_GROUP_SCHEMA_VERSION: Final = "phase20-family-a-construction-dependency-group-v1"
PHASE20_DEPENDENCY_GROUP_HASH_DOMAIN: Final = PHASE20_DEPENDENCY_GROUP_SCHEMA_VERSION
PHASE20_CONSTRUCTION_GATE_SCHEMA_VERSION: Final = (
    "phase20-family-a-evaluation-holdout-construction-gate-v1"
)
PHASE20_CONSTRUCTION_GATE_HASH_DOMAIN: Final = PHASE20_CONSTRUCTION_GATE_SCHEMA_VERSION
PHASE20_FORBIDDEN_SUBSTITUTE_SCHEMA_VERSION: Final = "phase20-family-a-forbidden-substitute-v1"
PHASE20_FORBIDDEN_SUBSTITUTE_HASH_DOMAIN: Final = PHASE20_FORBIDDEN_SUBSTITUTE_SCHEMA_VERSION
PHASE20_GAP_BINDING_SCHEMA_VERSION: Final = "phase20-family-a-phase15-gap-binding-v1"
PHASE20_GAP_BINDING_HASH_DOMAIN: Final = PHASE20_GAP_BINDING_SCHEMA_VERSION
PHASE20_STEP_BINDING_SCHEMA_VERSION: Final = "phase20-family-a-source-plan-step-binding-v1"
PHASE20_STEP_BINDING_HASH_DOMAIN: Final = PHASE20_STEP_BINDING_SCHEMA_VERSION

PHASE20_INHERITED_PREREQUISITES_MANIFEST_HASH_DOMAIN: Final = (
    "phase20-inherited-phase19-prerequisites-manifest-v1"
)
PHASE20_INPUT_REQUIREMENTS_MANIFEST_HASH_DOMAIN: Final = (
    "phase20-evaluation-holdout-input-requirements-manifest-v1"
)
PHASE20_FUTURE_EVIDENCE_MANIFEST_HASH_DOMAIN: Final = "phase20-missing-future-evidence-manifest-v1"
PHASE20_TRANSITION_RULES_MANIFEST_HASH_DOMAIN: Final = (
    "phase20-future-evidence-transition-rules-manifest-v1"
)
PHASE20_DEPENDENCY_GROUPS_MANIFEST_HASH_DOMAIN: Final = (
    "phase20-construction-dependency-groups-manifest-v1"
)
PHASE20_CONSTRUCTION_GATES_MANIFEST_HASH_DOMAIN: Final = (
    "phase20-evaluation-holdout-construction-gates-manifest-v1"
)
PHASE20_FORBIDDEN_SUBSTITUTES_MANIFEST_HASH_DOMAIN: Final = (
    "phase20-forbidden-substitutes-manifest-v1"
)
PHASE20_GAP_BINDINGS_MANIFEST_HASH_DOMAIN: Final = "phase20-phase15-gap-bindings-manifest-v1"
PHASE20_STEP_BINDINGS_MANIFEST_HASH_DOMAIN: Final = "phase20-source-plan-step-bindings-manifest-v1"
PHASE20_REGISTER_POLICY_ID: Final = "phase20-family-a-evaluation-holdout-input-register-policy-v1"
PHASE20_REGISTER_POLICY_HASH_DOMAIN: Final = PHASE20_REGISTER_POLICY_ID
PHASE20_ARTIFACT_NAMESPACE: Final = UUID("775d108f-97b8-5f38-8a5a-7d6014e57b45")

PHASE20_ACCEPTED_PHASE19_COMMIT_SHA: Final = "86ddcafacff43b42fe56346745d7e6f08eaf3a52"
PHASE20_ACCEPTED_PHASE19_TREE_SHA: Final = "6b6c2693a969e80cac9013d441ba607565d8914a"
PHASE20_PHASE19_ARTIFACT_ID: Final = "0b3f9153-71cc-5052-9b47-f714ed17bb99"
PHASE20_PHASE19_ARTIFACT_SHA256: Final = (
    "ed738badfb6e95feb4d7969d299bdc6186ef13ebf0f036134518e147803c72df"
)
PHASE20_PHASE19_POLICY_SHA256: Final = (
    "78485a93a2fda0d81ea7d2d7fb179f60ef2aee97616f3981fadabfd72ca02438"
)
PHASE20_PHASE19_PREREQUISITES_MANIFEST_SHA256: Final = (
    "3ca1af1c887a0621b4d66433d9d84028832377b3e97fc85cea0178e8c963982d"
)
PHASE20_PHASE19_REQUIRED_EVIDENCE_MANIFEST_SHA256: Final = (
    "6afd447016cb69561d5d7914541c9addd8781fea70283430c6897577bfc416df"
)
PHASE20_PHASE19_GAP_BINDINGS_MANIFEST_SHA256: Final = (
    "d60c4aecd7e86daef1e5e6d1faee0e4db6283a40666ad65de9612b7b259f4958"
)
PHASE20_PHASE19_STEPS_MANIFEST_SHA256: Final = (
    "4d54c4ad55e77c8793b04d2213b95092504f3b8aa2268736de4144385eb04c0c"
)
PHASE20_PHASE19_AGGREGATE_CONCLUSION: Final = "BLOCKED_MISSING_EVALUATION_POLICY_AND_HOLDOUT"
PHASE20_PHASE15_GAPS_MANIFEST_SHA256: Final = (
    "9c70f11f85eb66dad6eed15a0a4907dec3fa4edc7b0da3d6adbad768b88b2f86"
)

PHASE20_FAMILY: Final = "A_CROSS_SECTIONAL_EQUITY_RANKING"
PHASE20_FROZEN_AT_UTC: Final = "2026-07-20T00:47:38.1976088Z"
PHASE20_OUTCOME: Final = "BLOCKED"
PHASE20_REGISTER_STATE: Final = "INPUTS_FROZEN"
PHASE20_AGGREGATE_CONCLUSION: Final = "BLOCKED_MISSING_OPERATIONAL_AND_DATA_SPECIFIC_INPUTS"

PHASE20_PHASE19_PREREQUISITE_SHA256S: Final = (
    "db3d26d26bb9287aefbaf2d9be1ea4b75b40ca916f13476214a4b97f05f52415",
    "2c597729a92a03ff0fcf4faa67c0be63deaaf13413ed1afe4d8cc58a5d0e911e",
    "0e537980f82c9c187ce38ac287938d5a9585510fd8ca524b01942c9fb3e6e288",
    "ae3e369abb27c8aa341391cc816ebd8b6eccdaa6cac9b6fabf57f434da3e6b1b",
    "b3df0e259e9cd1c4c11b7a32187cfae59d6954ac2abde5777c811baf687cad0e",
    "6ae23eda15ab7999798de72ac61eb0345dd83094b2b2aad9a1e3ddc9f88a0298",
    "e088e45f5e890a0c6a13bbd7501fd75bca2c4cf13951f4d3ad14b1f6c3c1e791",
    "595016128f9cc0ca5b3fd4280cb4310556d244d1292a38896bec83e8bb838fe6",
    "98a894b38efa7b6c8fc643f70f6948e657d92f34354790bdb631e7f7a8d190cf",
    "ae74e765a8b2010b4a55af83410b3f5732c216340dc03d258a13c1076fe0cf48",
    "e9329073fd9aa59b6839436e75dcae4ea8700c7337b695cdf980bd7e574c46bf",
    "4eb89b66e8cde3e53c1e142b71d64b6bc53dc3561aaf23f52ed55650ad67c12c",
    "c433bed678bf8dfd29bf666fbfe7c4146b2f5b7a6a4e1027d2fb1fae17dfc528",
    "04f9a48d5ec680f0153db701349d6bd5a6ca9fadc10e4f307a07e5108b0831dd",
    "790fe773f16412b9255537c46c603acca672ed1bf2a819c99c1201558235142b",
    "7b72d32499c54ce392a5dd71a4e209a290d3dbb5791c6819cce81d378bf05b33",
    "175708192c35a7453fbf28f31eef6008486d91751c6bf8fd96bd969f8fa91801",
    "b28548806136197adddbeea27ff2b9e2c2c953b0a0e5778f7610b3f2c3f42638",
    "a6847ee2be3409f0c61190d84c1d8e819cc042f0edf79cf10779dfacb7b65bfa",
)
PHASE20_INHERITED_PREREQUISITE_ROWS: Final = tuple(
    (row[0], row[1], row[3], row[4], inherited_sha256)
    for row, inherited_sha256 in zip(
        PHASE19_PREREQUISITE_ROWS,
        PHASE20_PHASE19_PREREQUISITE_SHA256S,
        strict=True,
    )
)

# category, code, definition, evidence state, satisfied, required field names, reason
_PHASE20_INPUT_REQUIREMENT_BASE_ROWS: Final = (
    (
        "UPSTREAM_CONTEXT",
        "OPERATIONAL_SOURCE_PRODUCT_COMPOSITION",
        (
            "Require one independently approved operational capability-to-source/product "
            "composition before any policy or holdout can be complete."
        ),
        "MISSING",
        False,
        (
            "capability_product_composition_id",
            "source_ids",
            "product_ids",
            "delivery_ids",
            "selection_scope",
            "selected_at_utc",
            "selected_by",
            "selection_evidence_sha256",
        ),
        "phase18_no_operational_selection",
    ),
    (
        "UPSTREAM_CONTEXT",
        "CURRENT_EXECUTED_USE_RIGHTS_AND_REVOCATION",
        (
            "Require current executed agreement and revocation evidence for the exact selected "
            "legal entity, products, delivery, and intended use."
        ),
        "MISSING",
        False,
        (
            "legal_entity_id",
            "executed_agreement_id",
            "product_schedule_ids",
            "storage_right",
            "non_display_internal_use_right",
            "derived_data_right",
            "retention_deletion_rule",
            "redistribution_right",
            "third_party_rights",
            "effective_at_utc",
            "expires_at_utc",
            "revocation_currentness_rule",
            "reviewed_at_utc",
            "reviewed_by",
            "rights_evidence_sha256",
        ),
        "phase18_blocked_review_not_executed_rights",
    ),
    (
        "UPSTREAM_CONTEXT",
        "EXACT_DELIVERY_AND_SCHEMA_VERSIONS",
        (
            "Require exact selected delivery and schema versions plus temporal and "
            "instrument-identity field mappings."
        ),
        "UNPROVEN",
        False,
        (
            "delivery_method_ids",
            "schema_ids",
            "schema_versions",
            "schema_effective_at_utc",
            "schema_field_manifest_sha256",
            "temporal_field_mapping_sha256",
            "instrument_identity_mapping_sha256",
        ),
        "delivery_and_schema_unproven",
    ),
    (
        "UPSTREAM_CONTEXT",
        "DECLARED_PIT_COVERAGE_CALENDAR_AVAILABILITY_MISSINGNESS",
        (
            "Require pre-observation target history, calendar, availability, revision, validity, "
            "and missingness conventions."
        ),
        "MISSING",
        False,
        (
            "target_history_start_utc",
            "target_history_end_utc",
            "decision_timezone",
            "decision_calendar_id",
            "decision_calendar_version",
            "event_time_rule",
            "available_at_rule",
            "ingested_at_rule",
            "validity_interval_rule",
            "revision_rule",
            "missingness_rule",
            "date_only_availability_rule",
            "coverage_requirement_sha256",
        ),
        "data_specific_preobservation_contract_missing",
    ),
    (
        "EVALUATION_POLICY_INPUT",
        "SIGNAL_ACTION_LABEL_AND_HORIZON",
        (
            "Require a non-synthetic deterministic research-score, action/portfolio semantics, "
            "label, lag, and horizon specification."
        ),
        "MOCK_ONLY",
        False,
        (
            "signal_specification_id",
            "signal_version",
            "deterministic_formula_id",
            "output_semantics",
            "forecast_horizon",
            "executable_decision_lag",
            "label_formula_id",
            "label_information_interval_rule",
            "universe_eligibility_rule",
            "universe_exclusion_rule",
            "rebalance_rule",
            "holding_rule",
            "overlap_rule",
            "no_trade_rule",
        ),
        "signal_and_horizon_mock_only",
    ),
    (
        "EVALUATION_POLICY_INPUT",
        "FEATURE_LINEAGE_LOOKBACK_AND_PREPROCESSING",
        (
            "Require exact feature lineage, lookbacks, availability, and train-only "
            "preprocessing rules."
        ),
        "MOCK_ONLY",
        False,
        (
            "feature_specification_id",
            "feature_version",
            "feature_formula_ids",
            "source_field_ids",
            "lookback_rules",
            "availability_rules",
            "source_observation_binding_rule",
            "preprocessing_rules",
            "imputation_policy",
            "encoding_policy",
            "feature_selection_policy",
            "hyperparameter_policy",
        ),
        "feature_policy_mock_only",
    ),
    (
        "EVALUATION_POLICY_INPUT",
        "WALK_FORWARD_FOLD_GEOMETRY_AND_PURGE",
        (
            "Require data-specific nested chronological fold geometry and actual-label-interval "
            "purge rules."
        ),
        "MOCK_ONLY",
        False,
        (
            "decision_timezone",
            "decision_calendar_id",
            "outer_fold_count",
            "inner_fold_count",
            "minimum_train_observations",
            "outer_test_observations",
            "inner_test_observations",
            "rolling_train_observations",
            "train_mode",
            "purge_rule",
        ),
        "walk_forward_geometry_mock_only",
    ),
    (
        "EVALUATION_POLICY_INPUT",
        "EMBARGO_APPLICABILITY_AND_DURATION",
        (
            "Require an explicit geometry-dependent embargo applicability decision and duration "
            "only when applicable."
        ),
        "UNPROVEN",
        False,
        (
            "train_mode",
            "embargo_applicability",
            "embargo_rule",
            "embargo_duration",
            "embargo_decision_rationale",
        ),
        "embargo_applicability_unproven",
    ),
    (
        "EVALUATION_POLICY_INPUT",
        "SAMPLE_ADEQUACY_AND_RETURN_HANDLING",
        "Require approved sample-adequacy thresholds and missing/no-trade return handling.",
        "MOCK_ONLY",
        False,
        (
            "min_oos_observations",
            "min_independent_events",
            "min_synchronized_trials",
            "missing_return_policy",
            "no_trade_return_policy",
            "sample_adequacy_approval_id",
        ),
        "sample_adequacy_mock_only",
    ),
    (
        "EVALUATION_POLICY_INPUT",
        "TRIAL_ACCOUNTING_DSR_PBO_SELECTION",
        (
            "Require complete trial accounting and approved selection, DSR, PBO, frequency, and "
            "serial-correlation conventions."
        ),
        "MOCK_ONLY",
        False,
        (
            "primary_selection_metric",
            "raw_trial_definition",
            "effective_trial_method",
            "dsr_min_probability",
            "cscv_block_count",
            "pbo_tie_policy",
            "pbo_rank_orientation",
            "pbo_max",
            "return_frequency",
            "annualization_factor",
            "serial_correlation_method",
        ),
        "trial_dsr_pbo_policy_mock_only",
    ),
    (
        "EVALUATION_POLICY_INPUT",
        "LEAKAGE_AND_DATA_QUALITY_BLOCKS",
        "Require approved L01-L06 and point-in-time data-quality blocking rules.",
        "MOCK_ONLY",
        False,
        (
            "leakage_check_ids",
            "duplicate_grain_rule",
            "future_timestamp_rule",
            "revision_backfill_rule",
            "identifier_break_rule",
            "join_integrity_rule",
            "delisting_outcome_rule",
            "stale_partition_rule",
            "schema_drift_rule",
            "data_quality_severity_rule",
        ),
        "leakage_gates_mock_only",
    ),
    (
        "EVALUATION_POLICY_INPUT",
        "MARKET_CALIBRATED_COST_SLIPPAGE_CAPACITY",
        (
            "Require market-calibrated baseline fee, spread, impact, delay, borrow, "
            "participation, and capacity inputs with vintages."
        ),
        "MOCK_ONLY",
        False,
        (
            "fee_schedule_id",
            "fee_schedule_effective_date",
            "spread_source",
            "spread_fallback_rule",
            "impact_model_id",
            "impact_model_version",
            "impact_calibration_id",
            "impact_calibration_vintage",
            "latency_rule",
            "slippage_model_id",
            "borrow_source",
            "hard_to_borrow_rule",
            "baseline_max_participation",
            "capacity_rule",
        ),
        "cost_slippage_calibration_mock_only",
    ),
    (
        "EVALUATION_POLICY_INPUT",
        "STRESS_VECTOR_AND_PROMOTION_GATES",
        "Require predeclared all-cost and liquidity stress vectors plus promotion-blocking gates.",
        "MOCK_ONLY",
        False,
        (
            "all_cost_multiplier",
            "spread_multiplier",
            "volatility_multiplier",
            "adv_multiplier",
            "impact_coefficient_multiplier",
            "latency_multiplier",
            "borrow_multiplier",
            "min_stressed_net_pnl",
            "min_stressed_annual_return",
            "min_stressed_sharpe",
            "max_stressed_drawdown",
            "max_capacity_breach_rate",
        ),
        "stress_gate_policy_mock_only",
    ),
    (
        "EVALUATION_POLICY_INPUT",
        "REGIME_AND_CRISIS_DEFINITIONS",
        "Require predeclared volatility, rate, crisis, and regime-dependency definitions.",
        "MOCK_ONLY",
        False,
        (
            "volatility_definition",
            "volatility_cut",
            "rate_definition",
            "rate_cut",
            "crisis_window_ids",
            "crisis_declaration_times",
            "dependency_rule",
        ),
        "regime_policy_mock_only",
    ),
    (
        "EVALUATION_POLICY_INPUT",
        "COMPUTABLE_DATA_SPECIFIC_RISK_LIMITS",
        (
            "Require approved computable position, exposure, turnover, volatility, loss, and "
            "drawdown limits."
        ),
        "MOCK_ONLY",
        False,
        (
            "max_single_observation_exposure",
            "max_gross_exposure",
            "max_net_exposure",
            "max_sector_exposure",
            "max_turnover",
            "max_volatility",
            "max_loss",
            "max_drawdown",
            "risk_policy_approval_id",
        ),
        "risk_limits_mock_only",
    ),
    (
        "EVALUATION_POLICY_INPUT",
        "REPRODUCIBILITY_AUDIT_SCHEMA",
        (
            "Preserve the present immutable audit schema without treating it as policy or "
            "holdout evidence."
        ),
        "PRESENT",
        True,
        (
            "artifact_id",
            "artifact_type",
            "config_hash",
            "evaluation_policy_id",
            "evaluation_policy_sha256",
            "data_snapshot_id",
            "source_versions",
            "code_version_git_sha",
            "random_seed",
            "raw_trial_count",
            "effective_trial_count",
            "effective_trial_method",
            "created_at_utc",
            "decision_time_utc",
            "parent_artifact_ids",
            "numeric_metadata_rule",
            "append_only_rule",
        ),
        "audit_schema_present_only",
    ),
    (
        "CONFIRMATION_HOLDOUT_INPUT",
        "SOURCE_BOUND_CONTIGUOUS_INTERVAL",
        (
            "Require one selected-source/schema/calendar-bound contiguous unopened confirmation "
            "interval."
        ),
        "MISSING",
        False,
        (
            "holdout_definition_id",
            "source_product_composition_sha256",
            "delivery_schema_manifest_sha256",
            "decision_calendar_id",
            "decision_calendar_version",
            "interval_start_utc",
            "interval_end_utc",
            "research_generation_id",
            "frozen_at_utc",
        ),
        "confirmation_interval_missing",
    ),
    (
        "CONFIRMATION_HOLDOUT_INPUT",
        "DECISION_CALENDAR_LABEL_BOUNDARY_AND_EXCLUSIONS",
        (
            "Require exact label-information boundaries and exclusion/purge rules around the "
            "confirmation interval."
        ),
        "MISSING",
        False,
        (
            "label_information_interval_rule",
            "boundary_exclusion_rule",
            "purge_intersection_rule",
            "confirmation_sample_eligibility_rule",
            "decision_timezone",
            "decision_calendar_id",
        ),
        "holdout_calendar_and_boundaries_missing",
    ),
    (
        "CONFIRMATION_HOLDOUT_INPUT",
        "LABEL_BLIND_CONSUMPTION_REPLACEMENT_GOVERNANCE",
        (
            "Require label-blind exclusion, custodian, single-use consumption, and "
            "replacement/new-generation governance."
        ),
        "MOCK_ONLY",
        False,
        (
            "label_blind_exclusion_rule",
            "feature_design_exclusion",
            "model_selection_exclusion",
            "threshold_selection_exclusion",
            "narrative_selection_exclusion",
            "label_access_prohibited",
            "opening_rule",
            "single_use_rule",
            "consumption_rule",
            "replacement_rule",
            "custodian_id",
        ),
        "holdout_rules_mock_only",
    ),
    (
        "APPROVAL_INPUT",
        "INDEPENDENT_POLICY_AND_HOLDOUT_APPROVAL_RECORD",
        (
            "Require independent immutable approval records for the complete policy and unopened "
            "holdout definition."
        ),
        "MISSING",
        False,
        (
            "policy_approval_id",
            "policy_approved_by",
            "policy_approved_at_utc",
            "holdout_approval_id",
            "holdout_approved_by",
            "holdout_approved_at_utc",
            "approval_scope",
            "approval_version",
            "approval_evidence_sha256",
        ),
        "independent_approval_missing",
    ),
)

# Related Phase 19 prerequisite codes and Phase 15 gap codes, in accepted registry order.
PHASE20_INPUT_RELATION_ROWS: Final = (
    (
        ("OPERATIONAL_SOURCE_PRODUCT_COMPOSITION",),
        ("FULL_POINT_IN_TIME_DATASET", "INDEPENDENT_CURRENT_USE_RIGHTS"),
    ),
    (
        ("CURRENT_EXECUTED_USE_RIGHTS_AND_REVOCATION",),
        (
            "INDEPENDENT_CURRENT_USE_RIGHTS",
            "DATA_RIGHTS_AND_RESEARCH_AUTHORITY",
            "RIGHTS_CURRENTNESS_REVOCATION",
        ),
    ),
    (
        ("EXACT_DELIVERY_AND_SCHEMA_VERSIONS",),
        ("EXTERNAL_CANDIDATE_QUALIFICATION",),
    ),
    (
        (
            "FULL_POINT_IN_TIME_COVERAGE_AND_MISSINGNESS",
            "DECISION_CALENDAR_SAMPLE_BOUNDARIES_AND_ADEQUACY",
        ),
        (
            "FULL_POINT_IN_TIME_DATASET",
            "HISTORICAL_MEMBERSHIP_AND_DELISTING",
            "SECTOR_LIQUIDITY_MACRO_HISTORY",
            "NON_SYNTHETIC_EVALUATION_POLICY",
        ),
    ),
    (
        ("SIGNAL_ACTION_LABEL_AND_HORIZON",),
        ("FAMILY_A_SIGNAL_AND_HORIZON",),
    ),
    (
        ("SIGNAL_ACTION_LABEL_AND_HORIZON", "LEAKAGE_AND_DATA_QUALITY_GATES"),
        ("NON_SYNTHETIC_EVALUATION_POLICY", "LEAKAGE_FREE_RESULT"),
    ),
    (
        ("PURGED_WALK_FORWARD_MECHANICS",),
        ("PURGED_WALK_FORWARD_MECHANICS",),
    ),
    (
        ("EMBARGO_APPLICABILITY",),
        ("EMBARGO_APPLICABILITY_DECISION",),
    ),
    (
        ("DECISION_CALENDAR_SAMPLE_BOUNDARIES_AND_ADEQUACY",),
        ("NON_SYNTHETIC_EVALUATION_POLICY",),
    ),
    (
        ("COMPLETE_TRIAL_ACCOUNTING_DSR_PBO_POLICY",),
        ("DSR_PBO_PROMOTION_GATES",),
    ),
    (
        ("LEAKAGE_AND_DATA_QUALITY_GATES",),
        ("LEAKAGE_FREE_RESULT",),
    ),
    (
        ("MARKET_CALIBRATED_COST_SLIPPAGE_CAPACITY",),
        ("MARKET_CALIBRATED_COST_SLIPPAGE",),
    ),
    (
        ("STRESS_REGIME_CRISIS_THRESHOLDS",),
        ("SECTOR_LIQUIDITY_MACRO_HISTORY", "MARKET_CALIBRATED_COST_SLIPPAGE"),
    ),
    (
        ("STRESS_REGIME_CRISIS_THRESHOLDS",),
        ("SECTOR_LIQUIDITY_MACRO_HISTORY", "MARKET_CALIBRATED_COST_SLIPPAGE"),
    ),
    (
        ("COMPUTABLE_DATA_SPECIFIC_RISK_LIMITS",),
        ("PRE_ORDER_RISK",),
    ),
    (
        ("REPRODUCIBILITY_AUDIT_SCHEMA",),
        ("IMMUTABLE_AUDIT_SCHEMA",),
    ),
    (
        ("SOURCE_BOUND_CONTIGUOUS_CONFIRMATION_INTERVAL",),
        ("NON_SYNTHETIC_EVALUATION_POLICY",),
    ),
    (
        ("HOLDOUT_DECISION_CALENDAR_AND_LABEL_BOUNDARIES",),
        ("FULL_POINT_IN_TIME_DATASET", "NON_SYNTHETIC_EVALUATION_POLICY"),
    ),
    (
        ("HOLDOUT_EXCLUSION_CONSUMPTION_AND_REPLACEMENT_RULES",),
        ("NON_SYNTHETIC_EVALUATION_PATH",),
    ),
    (
        (
            "NON_SYNTHETIC_EVALUATION_POLICY",
            "UNTOUCHED_CONFIRMATION_HOLDOUT_DEFINITION",
        ),
        (
            "NON_SYNTHETIC_EVALUATION_POLICY",
            "NON_SYNTHETIC_EVALUATION_PATH",
            "DATA_RIGHTS_AND_RESEARCH_AUTHORITY",
        ),
    ),
)

PHASE20_INPUT_REQUIREMENT_ROWS: Final = tuple(
    (*base_row[:6], related_phase19, related_phase15, base_row[6])
    for base_row, (related_phase19, related_phase15) in zip(
        _PHASE20_INPUT_REQUIREMENT_BASE_ROWS,
        PHASE20_INPUT_RELATION_ROWS,
        strict=True,
    )
)

# name, state, produced, reason. No value/hash field exists in the record schema.
PHASE20_FUTURE_EVIDENCE_ROWS: Final = (
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

# code, definition, reason. Every rule is future-only, unapplied, and grants no authority.
PHASE20_TRANSITION_RULE_ROWS: Final = (
    (
        "NO_PLAN_OR_ARTIFACT_HASH_UPGRADE",
        (
            "A requirements, plan, artifact, manifest, record, or file hash proves integrity only "
            "and cannot upgrade an input or satisfy reserved evidence."
        ),
        "integrity_hash_is_not_substantive_evidence",
    ),
    (
        "MOCK_ONLY_TO_PRESENT_REQUIRES_APPROVED_NON_SYNTHETIC_EVIDENCE",
        (
            "MOCK_ONLY becomes PRESENT only through approved non-synthetic evidence for every "
            "required field."
        ),
        "approved_non_synthetic_evidence_required",
    ),
    (
        "MISSING_TO_PRESENT_REQUIRES_COMPLETE_REQUIRED_EVIDENCE",
        (
            "MISSING becomes PRESENT only through one complete, strictly validated "
            "required-evidence set."
        ),
        "complete_required_evidence_required",
    ),
    (
        "UNPROVEN_TO_PRESENT_REQUIRES_INDEPENDENT_VERIFICATION",
        (
            "UNPROVEN becomes PRESENT only after independent verification of the exact "
            "operational scope."
        ),
        "independent_verification_required",
    ),
    (
        "STALE_TO_PRESENT_REQUIRES_FRESH_REVALIDATION",
        "STALE becomes PRESENT only after fresh currentness and version revalidation.",
        "fresh_revalidation_required",
    ),
    (
        "PRESENT_TO_STALE_ON_CURRENTNESS_OR_VERSION_DRIFT",
        (
            "PRESENT degrades to STALE when currentness lapses or a bound source, product, schema, "
            "policy, or rights version changes."
        ),
        "currentness_or_version_drift_requires_stale",
    ),
    (
        "HOLDOUT_DEFINITION_REQUIRES_SOURCE_CALENDAR_BINDING_AND_ZERO_OBSERVATION_LABEL_ACCESS",
        (
            "A holdout definition requires exact source/schema/calendar binding while observation "
            "access, label access, opening, and consumption remain false."
        ),
        "holdout_must_be_bound_and_unobserved",
    ),
    (
        "POLICY_COMPLETION_REQUIRES_ALL_POLICY_INPUTS_AND_UNOPENED_HOLDOUT_REFERENCE",
        (
            "A complete policy requires every applicable policy input and a reference to the "
            "separately frozen unopened holdout definition."
        ),
        "complete_policy_requires_all_inputs_and_holdout",
    ),
    (
        "STEP3_REQUIRES_BOTH_RESERVED_HASHES_AND_SEPARATE_EXTERNAL_ACTION_AUTHORITY",
        (
            "Step 3 remains ineligible until both reserved hashes exist and a separate "
            "bounded-external-action authorization is current."
        ),
        "step3_requires_evidence_and_separate_authority",
    ),
    (
        "LATER_SOURCE_PLAN_STEPS_CANNOT_SKIP_OR_IMPLY_PREDECESSORS",
        (
            "A later source-plan step cannot start, complete, or grant authority while any "
            "predecessor is incomplete."
        ),
        "ordered_plan_predecessors_are_mandatory",
    ),
)

# code, definition, input codes, prerequisite group codes, state, reason
PHASE20_DEPENDENCY_GROUP_ROWS: Final = (
    (
        "OPERATIONAL_COMPOSITION_AND_RIGHTS",
        "Require operational composition, delivery, schemas, and current executed use rights.",
        tuple(row[1] for row in PHASE20_INPUT_REQUIREMENT_ROWS[0:3]),
        (),
        "BLOCKED",
        "operational_composition_delivery_and_rights_incomplete",
    ),
    (
        "SOURCE_COVERAGE_AND_CALENDAR",
        (
            "Require declared point-in-time coverage, calendar, availability, and missingness "
            "semantics."
        ),
        (PHASE20_INPUT_REQUIREMENT_ROWS[3][1],),
        ("OPERATIONAL_COMPOSITION_AND_RIGHTS",),
        "BLOCKED",
        "source_specific_coverage_and_calendar_incomplete",
    ),
    (
        "EVALUATION_METHODOLOGY",
        (
            "Require complete non-synthetic signal, feature, chronology, selection, leakage, and "
            "quality inputs."
        ),
        tuple(row[1] for row in PHASE20_INPUT_REQUIREMENT_ROWS[4:11]),
        ("SOURCE_COVERAGE_AND_CALENDAR",),
        "BLOCKED",
        "evaluation_methodology_inputs_incomplete",
    ),
    (
        "COST_STRESS_REGIME_AND_RISK",
        "Require market-calibrated costs, stress, regimes, promotion gates, and risk limits.",
        tuple(row[1] for row in PHASE20_INPUT_REQUIREMENT_ROWS[11:15]),
        ("SOURCE_COVERAGE_AND_CALENDAR",),
        "BLOCKED",
        "calibration_stress_regime_and_risk_inputs_incomplete",
    ),
    (
        "AUDIT_AND_HOLDOUT_GOVERNANCE",
        "Preserve the audit schema and require exact source-bound label-blind holdout governance.",
        tuple(row[1] for row in PHASE20_INPUT_REQUIREMENT_ROWS[15:19]),
        (
            "SOURCE_COVERAGE_AND_CALENDAR",
            "EVALUATION_METHODOLOGY",
            "COST_STRESS_REGIME_AND_RISK",
        ),
        "BLOCKED",
        "holdout_inputs_and_governance_incomplete",
    ),
    (
        "INDEPENDENT_JOINT_APPROVAL",
        (
            "Require an independent joint policy-and-holdout approval record after all inputs "
            "complete."
        ),
        (PHASE20_INPUT_REQUIREMENT_ROWS[19][1],),
        (
            "OPERATIONAL_COMPOSITION_AND_RIGHTS",
            "SOURCE_COVERAGE_AND_CALENDAR",
            "EVALUATION_METHODOLOGY",
            "COST_STRESS_REGIME_AND_RISK",
            "AUDIT_AND_HOLDOUT_GOVERNANCE",
        ),
        "BLOCKED",
        "independent_joint_approval_absent",
    ),
)

# code, definition, required groups, state, passed, before-observation, reason
PHASE20_CONSTRUCTION_GATE_ROWS: Final = (
    (
        "OPERATIONAL_COMPOSITION_CURRENT_RIGHTS_GATE",
        (
            "Block until operational composition, exact delivery, and current executed rights "
            "are evidenced."
        ),
        ("OPERATIONAL_COMPOSITION_AND_RIGHTS",),
        "BLOCKED",
        False,
        True,
        "operational_and_rights_inputs_incomplete",
    ),
    (
        "SOURCE_COVERAGE_CALENDAR_GATE",
        "Block until point-in-time coverage, calendar, availability, and missingness are frozen.",
        ("SOURCE_COVERAGE_AND_CALENDAR",),
        "BLOCKED",
        False,
        True,
        "coverage_calendar_inputs_incomplete",
    ),
    (
        "NON_SYNTHETIC_METHODOLOGY_GATE",
        "Block until evaluation methodology inputs are complete and approved as non-synthetic.",
        ("EVALUATION_METHODOLOGY",),
        "BLOCKED",
        False,
        True,
        "methodology_inputs_incomplete",
    ),
    (
        "MARKET_CALIBRATION_STRESS_RISK_GATE",
        "Block until market calibration, stress, regime, promotion, and risk inputs are complete.",
        ("COST_STRESS_REGIME_AND_RISK",),
        "BLOCKED",
        False,
        True,
        "calibration_stress_regime_risk_inputs_incomplete",
    ),
    (
        "UNTOUCHED_HOLDOUT_GOVERNANCE_GATE",
        (
            "Block until source-bound label-blind holdout governance is frozen before observation "
            "access."
        ),
        ("AUDIT_AND_HOLDOUT_GOVERNANCE",),
        "BLOCKED",
        False,
        True,
        "holdout_governance_inputs_incomplete",
    ),
    (
        "INDEPENDENT_JOINT_APPROVAL_GATE",
        (
            "Block until an independent joint approval record exists after every predecessor "
            "gate passes."
        ),
        ("INDEPENDENT_JOINT_APPROVAL",),
        "BLOCKED",
        False,
        True,
        "independent_joint_approval_absent",
    ),
)

# code, definition, target classes, forbidden, reason
PHASE20_FORBIDDEN_SUBSTITUTE_ROWS: Final = (
    (
        "PHASE15_REQUIREMENTS_HASH",
        "A requirements hash proves specification integrity only.",
        ("EVALUATION_POLICY_OUTPUT", "CONFIRMATION_HOLDOUT_OUTPUT"),
        True,
        "requirements_are_not_completed_source_specific_evidence",
    ),
    (
        "PHASE19_ASSESSMENT_HASH",
        "A blocked-assessment hash proves only assessment integrity.",
        ("EVALUATION_POLICY_OUTPUT", "CONFIRMATION_HOLDOUT_OUTPUT"),
        True,
        "assessment_integrity_is_not_missing_evidence",
    ),
    (
        "SYNTHETIC_POLICY_OR_RESULT_HASH",
        "Synthetic dates, thresholds, calibrations, and results cannot be relabeled.",
        ("EVALUATION_POLICY_OUTPUT", "CONFIRMATION_HOLDOUT_OUTPUT"),
        True,
        "synthetic_fixture_values_are_not_non_synthetic_evidence",
    ),
    (
        "PUBLIC_DOCUMENTATION_OR_RIGHTS_REVIEW_HASH",
        "Public metadata and blocked rights findings do not grant operational use.",
        ("EVALUATION_POLICY_OUTPUT", "CONFIRMATION_HOLDOUT_OUTPUT"),
        True,
        "public_review_does_not_supply_operational_inputs",
    ),
    (
        "CANDIDATE_INVENTORY_HASH",
        "Candidate inventory selection is review routing, not operational composition.",
        ("EVALUATION_POLICY_OUTPUT", "CONFIRMATION_HOLDOUT_OUTPUT"),
        True,
        "candidate_inventory_is_not_operational_selection",
    ),
    (
        "PROTOCOL_OR_TEMPLATE_HASH",
        "A protocol or template cannot substitute for a completed source-bound instance.",
        ("EVALUATION_POLICY_OUTPUT", "CONFIRMATION_HOLDOUT_OUTPUT"),
        True,
        "template_integrity_is_not_instance_evidence",
    ),
    (
        "PLACEHOLDER_OR_ALL_ZERO_HASH",
        "Placeholder and all-zero values are never valid evidence.",
        ("EVALUATION_POLICY_OUTPUT", "CONFIRMATION_HOLDOUT_OUTPUT"),
        True,
        "placeholder_evidence_is_forbidden",
    ),
    (
        "OPERATOR_OVERRIDE_OR_ARBITRARY_HASH",
        "No operator override or arbitrary expected hash can bypass construction gates.",
        ("EVALUATION_POLICY_OUTPUT", "CONFIRMATION_HOLDOUT_OUTPUT"),
        True,
        "override_and_arbitrary_hashes_are_forbidden",
    ),
)

PHASE20_PHASE19_GAP_BINDING_SHA256S: Final = (
    "e60796b58f1e52d68c3485ef00c10ac1aff6eb1c3556bef9a252c7c8675da63d",
    "4c678c16ae46a9be04c10a040eec9ba90ae711bc94aa1e972284a1d2dad48d17",
    "a87b7a5524c2095bca995a9d0e10be170e089eeece5e26a6f408139697a7c765",
    "65bfb37a10abdaa857fc8f9e827ec005c9a0919fc6eeda75c926cac3e06bd672",
    "11fda880615f2c1968396cb28dcd5279fb241ba3747d777819c5e87a3c4966a4",
    "531506ca694497f767a65ce49bde5769c19a720c6641506d21c6b21c7d29f55e",
    "66b0f9975f420b64acab67fda182bdcc176583af1246bed17a91d23204e4c998",
    "277c6afd99e425a985347065763b95031e67bf5277abefca0d4ff643fbc56511",
    "311edd632136e17e9474400dcb970c0b2059fa46f9e66f321745d0c767bef16f",
    "f90fcdb6cf3f7750e7d0d186b9c78648d82cec487b1f045e78507cce4a877357",
    "fc3ba493bf1833fbcbacf8335cabbaaad6998c05d48f59a2496ee5a463046b60",
    "33dd7ca0d6b6dc25e1709fd03b72ca6c31538a70d1d1fcfcfca275724ca039ab",
    "9e8fad940a59dbef6edc84046749cbd6caf6c69df85018b914e9e60ce2b152a0",
    "eeb53785881045418704253e2cb899071dcde24db1799fdbf70f8d1fde350d27",
    "3d688dee7d7a0f71dce36e9da213a133d0bd653e4a06d5c1d70b0e5bebfe46be",
    "4124681a492ae515c6a87a9106bd599fb517990ec71efe75c2f5b2035586a8da",
    "7d917ea6fc630aedf300b4dd0870b3256969fc5fc5eb190ca40e4d97b319d797",
    "7bee5820065435986c7bc072f2347302f4a080a5165d3c8d94063ffe38eeae40",
    "a35ab52d579bfa395dc52e7f0cb812ca720c7c9465a7f641fe33cbc57199bfd7",
)
PHASE20_PHASE19_STEP_SHA256S: Final = (
    "3fe2faf3c6acae985ec53f873b8c08743963dfaaa7ef7bd0127528960e002f12",
    "01124b3fabaacd4b053707a0aafc7a2e8e7a69c9b97f331b750f3b7e59352610",
    "ece8fa3a5f95b0016fb04002934c883b3a1eebfc8728effe4b0197000198e1b2",
    "250f5efe4730f8080b41f535057c31267f3b696cb720f03009909ee1c0f45114",
    "f90f83c4281dc6cbf49f429435df7685653e8b7a6f35efe9fff00f7e9f50c5d8",
    "ed2c2b7da12a5370d98f38713118b8036e186c879c833b85fe4cc4f03fc9352a",
    "6c25c4599d9c9429cf008a07071fae0ba7759c5e30f28caa2705be8cd8038c34",
)

PHASE20_BOUNDARY_VALUES: Final = MappingProxyType(
    {
        "metadata_only": True,
        "requirements_only": True,
        "input_register_only": True,
        "runtime_network_disabled": True,
        "phase19_prerequisites_unchanged": True,
        "inherited_phase15_gaps_unchanged": True,
        "source_plan_steps_unchanged": True,
        "revalidation_required_before_external_action": True,
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

PHASE20_BLOCK_REASON: Final = (
    "No incomplete Phase 19 prerequisite can be upgraded: operational composition, current "
    "executed rights, exact schemas, coverage, decision-calendar geometry, market calibration, "
    "data-specific policy inputs, and a source-bound untouched holdout remain absent or unproven."
)
PHASE20_DISCLAIMER: Final = (
    "Portable input register only. INPUTS_FROZEN proves deterministic requirements and transition "
    "rules; it is not an operational selection, policy, holdout definition, qualification, data "
    "right, research authorization, performance result, execution clearance, or order authority."
)

# Stable aliases consumed by the phase verifier and static acceptance integration.
PHASE20_INPUT_REGISTER_POLICY_ID: Final = PHASE20_REGISTER_POLICY_ID
PHASE20_INPUT_ROWS: Final = PHASE20_INPUT_REQUIREMENT_ROWS
PHASE20_REQUIRED_EVIDENCE_ROWS: Final = PHASE20_FUTURE_EVIDENCE_ROWS
PHASE20_GAP_CODES: Final = PHASE19_GAP_CODES
PHASE20_GAP_STATES: Final = PHASE19_GAP_STATES
PHASE20_SOURCE_GAP_SHA256S: Final = PHASE19_SOURCE_GAP_SHA256S
PHASE20_STEP_CODES: Final = PHASE19_STEP_CODES
PHASE20_STEP_STATES: Final = PHASE19_STEP_STATES
PHASE20_STEP_REASONS: Final = PHASE19_STEP_REASONS

PHASE20_REGISTER_POLICY_SHA256: Final = domain_sha256(
    PHASE20_REGISTER_POLICY_HASH_DOMAIN,
    {
        "register_policy_id": PHASE20_REGISTER_POLICY_ID,
        "artifact_uuid_namespace": str(PHASE20_ARTIFACT_NAMESPACE),
        "schemas_and_hash_domains": (
            (PHASE20_ARTIFACT_SCHEMA_VERSION, PHASE20_ARTIFACT_HASH_DOMAIN),
            (
                PHASE20_INHERITED_PREREQUISITE_SCHEMA_VERSION,
                PHASE20_INHERITED_PREREQUISITE_HASH_DOMAIN,
            ),
            (PHASE20_INPUT_REQUIREMENT_SCHEMA_VERSION, PHASE20_INPUT_REQUIREMENT_HASH_DOMAIN),
            (PHASE20_FUTURE_EVIDENCE_SCHEMA_VERSION, PHASE20_FUTURE_EVIDENCE_HASH_DOMAIN),
            (PHASE20_TRANSITION_RULE_SCHEMA_VERSION, PHASE20_TRANSITION_RULE_HASH_DOMAIN),
            (PHASE20_DEPENDENCY_GROUP_SCHEMA_VERSION, PHASE20_DEPENDENCY_GROUP_HASH_DOMAIN),
            (PHASE20_CONSTRUCTION_GATE_SCHEMA_VERSION, PHASE20_CONSTRUCTION_GATE_HASH_DOMAIN),
            (PHASE20_FORBIDDEN_SUBSTITUTE_SCHEMA_VERSION, PHASE20_FORBIDDEN_SUBSTITUTE_HASH_DOMAIN),
            (PHASE20_GAP_BINDING_SCHEMA_VERSION, PHASE20_GAP_BINDING_HASH_DOMAIN),
            (PHASE20_STEP_BINDING_SCHEMA_VERSION, PHASE20_STEP_BINDING_HASH_DOMAIN),
            PHASE20_INHERITED_PREREQUISITES_MANIFEST_HASH_DOMAIN,
            PHASE20_INPUT_REQUIREMENTS_MANIFEST_HASH_DOMAIN,
            PHASE20_FUTURE_EVIDENCE_MANIFEST_HASH_DOMAIN,
            PHASE20_TRANSITION_RULES_MANIFEST_HASH_DOMAIN,
            PHASE20_DEPENDENCY_GROUPS_MANIFEST_HASH_DOMAIN,
            PHASE20_CONSTRUCTION_GATES_MANIFEST_HASH_DOMAIN,
            PHASE20_FORBIDDEN_SUBSTITUTES_MANIFEST_HASH_DOMAIN,
            PHASE20_GAP_BINDINGS_MANIFEST_HASH_DOMAIN,
            PHASE20_STEP_BINDINGS_MANIFEST_HASH_DOMAIN,
        ),
        "accepted_phase19_identity": (
            PHASE20_ACCEPTED_PHASE19_COMMIT_SHA,
            PHASE20_ACCEPTED_PHASE19_TREE_SHA,
            PHASE20_PHASE19_ARTIFACT_ID,
            PHASE20_PHASE19_ARTIFACT_SHA256,
            PHASE20_PHASE19_POLICY_SHA256,
            PHASE20_PHASE19_PREREQUISITES_MANIFEST_SHA256,
            PHASE20_PHASE19_REQUIRED_EVIDENCE_MANIFEST_SHA256,
            PHASE20_PHASE19_GAP_BINDINGS_MANIFEST_SHA256,
            PHASE20_PHASE19_STEPS_MANIFEST_SHA256,
            PHASE20_PHASE19_AGGREGATE_CONCLUSION,
        ),
        "family": PHASE20_FAMILY,
        "frozen_at_utc": PHASE20_FROZEN_AT_UTC,
        "outcome": PHASE20_OUTCOME,
        "register_state": PHASE20_REGISTER_STATE,
        "aggregate_conclusion": PHASE20_AGGREGATE_CONCLUSION,
        "inherited_prerequisites": PHASE20_INHERITED_PREREQUISITE_ROWS,
        "input_requirements": PHASE20_INPUT_REQUIREMENT_ROWS,
        "future_evidence": PHASE20_FUTURE_EVIDENCE_ROWS,
        "transition_rules": PHASE20_TRANSITION_RULE_ROWS,
        "dependency_groups": PHASE20_DEPENDENCY_GROUP_ROWS,
        "construction_gates": PHASE20_CONSTRUCTION_GATE_ROWS,
        "forbidden_substitutes": PHASE20_FORBIDDEN_SUBSTITUTE_ROWS,
        "phase15_gaps": tuple(
            zip(
                PHASE19_GAP_CODES,
                PHASE19_GAP_STATES,
                PHASE19_SOURCE_GAP_SHA256S,
                PHASE20_PHASE19_GAP_BINDING_SHA256S,
                strict=True,
            )
        ),
        "source_plan_steps": tuple(
            zip(
                PHASE19_STEP_CODES,
                PHASE19_STEP_STATES,
                PHASE19_STEP_REASONS,
                PHASE20_PHASE19_STEP_SHA256S,
                strict=True,
            )
        ),
        "boundary_values": PHASE20_BOUNDARY_VALUES,
        "block_reason": PHASE20_BLOCK_REASON,
        "disclaimer": PHASE20_DISCLAIMER,
    },
)


def identity(sha256: str) -> UUID:
    return uuid_from_sha256(PHASE20_ARTIFACT_NAMESPACE, sha256)


__all__ = [name for name in globals() if name.startswith("PHASE20_")] + [
    "canonical_json_bytes",
    "canonicalize",
    "domain_sha256",
    "identity",
]
