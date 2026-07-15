import type { components } from "@fable5/contracts";
import { render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { EvaluationReports } from "../app/research/EvaluationReports";

type EvaluationReport = components["schemas"]["EvaluationReport"];
type EvaluationReportSummary = components["schemas"]["EvaluationReportSummary"];
type BlockedEvaluationOutcome = components["schemas"]["BlockedEvaluationOutcome"];
type GateResult = components["schemas"]["GateResult"];
type ResolvedSourceObservation = components["schemas"]["ResolvedSourceObservation"];
type ResolvedSourceObservationRef = components["schemas"]["ResolvedSourceObservationRef"];
type SampleSourceLineage = components["schemas"]["SampleSourceLineage"];
type TrialRecord = components["schemas"]["TrialRecord"];

const gateCodes = [
  "DATA_PIT",
  "CV_CHRONOLOGY",
  "PREPROCESSING",
  "TRIAL_REGISTRY",
  "DSR",
  "PBO",
  "COST_STRESS",
  "LEAKAGE",
  "SAMPLE_ADEQUACY",
  "REGIME",
  "RISK_LIMITS",
  "REPRODUCIBILITY",
] as const;

const gateHeadings = [
  "Point-in-time data",
  "Walk-forward chronology",
  "Train-only preprocessing",
  "Complete trial registry",
  "Deflated Sharpe Ratio",
  "Backtest overfitting probability",
  "Cost and liquidity stress",
  "Leakage blockers",
  "Sample adequacy",
  "Regime evidence",
  "Risk limits",
  "Reproducibility",
] as const;

const artifactId = "50000000-0000-5000-8000-000000000001";
const selectedTrialId = "50000000-0000-5000-8000-000000000101";
const foldId = "50000000-0000-5000-8000-000000000201";
const fitId = "af40754f-d804-58af-a78d-d89dc0d57fd6";
const oosEntryId = "50000000-0000-5000-8000-000000000401";
const snapshotId = "50000000-0000-5000-8000-000000000002";
const membershipSnapshotId = "50000000-0000-5000-8000-000000000003";
const normalizedObservationId = "50000000-0000-5000-8000-000000000701";
const rawObservationId = "50000000-0000-5000-8000-000000000702";
const observationRevisionId = "50000000-0000-5000-8000-000000000703";
const membershipNormalizedObservationId = "50000000-0000-5000-8000-000000000711";
const membershipRawObservationId = "50000000-0000-5000-8000-000000000712";
const membershipObservationRevisionId = "50000000-0000-5000-8000-000000000713";
const outcomeId = "50000000-0000-5000-8000-000000000801";

const sourceObservationRef = {
  capability: "ohlcv",
  normalized_content_sha256: "1".repeat(64),
  normalized_observation_id: normalizedObservationId,
  observation_revision_id: observationRevisionId,
  raw_observation_id: rawObservationId,
  raw_payload_sha256: "2".repeat(64),
  snapshot_id: snapshotId,
  snapshot_sha256: "d".repeat(64),
} satisfies ResolvedSourceObservationRef;

const sourceObservation = {
  disposition: "included_as_of",
  key: {
    capability: "ohlcv",
    normalized_observation_id: normalizedObservationId,
  },
  normalized_observation: {
    adapter_id: "phase4-synthetic-pit-adapter",
    adapter_version: "phase4-synthetic-pit-adapter-v1",
    availability_convention: "source_timestamp",
    availability_precision: "timestamp",
    availability_source_date: null,
    available_at: "2026-01-14T15:00:00Z",
    calendar_id: "XNYS",
    currency: "USD",
    dataset_id: "synthetic-ohlcv",
    dataset_schema_id: "phase4-ohlcv-bar",
    dataset_schema_version: "phase4-ohlcv-bar-v1",
    entitlement_id: "synthetic-research-entitlement",
    envelope_schema_version: "phase4-normalized-observation-v1",
    event_time: "2026-01-14T14:00:00Z",
    field_missingness: [],
    instrument_id: "50000000-0000-5000-8000-000000000704",
    listing_id: "50000000-0000-5000-8000-000000000705",
    logical_record_id: "50000000-0000-5000-8000-000000000706",
    logical_record_key_sha256: "3".repeat(64),
    normalized_content_sha256: sourceObservationRef.normalized_content_sha256,
    normalized_observation_id: normalizedObservationId,
    observation_revision_id: observationRevisionId,
    payload: {
      adjustment_as_of: null,
      adjustment_basis: "raw_unadjusted",
      bar_end: "2026-01-14T21:00:00Z",
      bar_interval: "P1D",
      bar_start: "2026-01-14T14:30:00Z",
      close: "101",
      corporate_action_revision_ids: [],
      high: "102",
      low: "99",
      open: "100",
      record_type: "ohlcv_bar",
      volume: "1000000",
      volume_unit: "shares",
    },
    product_id: "synthetic-pit-product",
    provider_id: "fable5-synthetic",
    quality_flags: [],
    raw_observation_id: rawObservationId,
    raw_payload_sha256: sourceObservationRef.raw_payload_sha256,
    retrieved_at: "2026-01-14T15:01:00Z",
    revision_id: "phase4-revision-1",
    snapshot_id: snapshotId,
    snapshot_sha256: sourceObservationRef.snapshot_sha256,
    source_record_id: "synthetic-ohlcv-2026-01-14",
    source_timezone: "America/New_York",
    unit: "USD_per_share",
    use_rights_id: "synthetic-research-use-rights",
    valid_from: "2026-01-14T15:00:00Z",
    valid_to: "2026-01-15T15:00:00Z",
    vintage_id: "phase4-vintage-1",
  },
  schema_version: "phase5-resolved-source-observation-v1",
} satisfies ResolvedSourceObservation;

const membershipSourceObservationRef = {
  capability: "universe_membership",
  normalized_content_sha256: "a".repeat(64),
  normalized_observation_id: membershipNormalizedObservationId,
  observation_revision_id: membershipObservationRevisionId,
  raw_observation_id: membershipRawObservationId,
  raw_payload_sha256: "b".repeat(64),
  snapshot_id: membershipSnapshotId,
  snapshot_sha256: "c".repeat(64),
} satisfies ResolvedSourceObservationRef;

const membershipSourceObservation = {
  disposition: "included_as_of",
  key: {
    capability: "universe_membership",
    normalized_observation_id: membershipNormalizedObservationId,
  },
  normalized_observation: {
    adapter_id: "phase4-synthetic-pit-adapter",
    adapter_version: "phase4-synthetic-pit-adapter-v1",
    availability_convention: "phase4-date-only-next-day-v1",
    availability_precision: "date",
    availability_source_date: "2025-12-31",
    available_at: "2026-01-01T05:00:00Z",
    calendar_id: "XNYS",
    currency: null,
    dataset_id: "synthetic-universe-membership",
    dataset_schema_id: "phase4-universe-membership",
    dataset_schema_version: "phase4-universe-membership-v1",
    entitlement_id: "synthetic-research-entitlement",
    envelope_schema_version: "phase4-normalized-observation-v1",
    event_time: "2026-01-01T00:00:00Z",
    field_missingness: [],
    instrument_id: sourceObservation.normalized_observation.instrument_id,
    listing_id: sourceObservation.normalized_observation.listing_id,
    logical_record_id: "50000000-0000-5000-8000-000000000714",
    logical_record_key_sha256: "e".repeat(64),
    normalized_content_sha256: membershipSourceObservationRef.normalized_content_sha256,
    normalized_observation_id: membershipNormalizedObservationId,
    observation_revision_id: membershipObservationRevisionId,
    payload: {
      record_type: "universe_membership",
      status: "included",
      universe_id: "synthetic-us-equity",
    },
    product_id: "synthetic-pit-product",
    provider_id: "fable5-synthetic",
    quality_flags: ["synthetic_fixture", "date_only_convention_applied"],
    raw_observation_id: membershipRawObservationId,
    raw_payload_sha256: membershipSourceObservationRef.raw_payload_sha256,
    retrieved_at: "2026-01-01T05:01:00Z",
    revision_id: "phase4-membership-revision-1",
    snapshot_id: membershipSnapshotId,
    snapshot_sha256: membershipSourceObservationRef.snapshot_sha256,
    source_record_id: "synthetic-membership-2026",
    source_timezone: "America/New_York",
    unit: "membership",
    use_rights_id: "synthetic-research-use-rights",
    valid_from: "2026-01-01T00:00:00Z",
    valid_to: "2026-02-01T00:00:00Z",
    vintage_id: "phase4-membership-vintage-1",
  },
  schema_version: "phase5-resolved-source-observation-v1",
} satisfies ResolvedSourceObservation;

const sampleLineage = [
  "synthetic-oos-01",
  "synthetic-post-embargo-01",
  "synthetic-purged-overlap-01",
  "synthetic-train-01",
].map((sampleId, index) => {
  const featureValue = sampleId === "synthetic-post-embargo-01" ? "0.15" : "0.1";
  return {
    adjustment_action_as_of_utc: null,
    decision_time_utc: "2026-01-14T16:00:00Z",
    dependency_graph: {
      feature_nodes: [
        {
          dependency_id: "phase4-ohlcv.open",
          feature_specification_sha256: "4".repeat(64),
          node_kind: "source_feature",
          source_observation_key: sourceObservation.key,
          source_payload_field: "open",
        },
      ],
      graph_sha256: String(index + 11).repeat(64).slice(0, 64),
      label_nodes: [
        {
          dependency_id: "future.label.synthetic-forward-two-session-return-v1",
          label_formula_id: "synthetic-forward-two-session-return-v1",
          label_specification_sha256: "5".repeat(64),
          node_kind: "future_label",
        },
        {
          dependency_id: "label.synthetic-forward-two-session-return-v1",
          label_formula_id: "synthetic-forward-two-session-return-v1",
          label_specification_sha256: "5".repeat(64),
          node_kind: "label",
        },
      ],
      sample_id: sampleId,
      schema_version: "phase5-derived-dependency-graph-v1",
    },
    feature_available_at_utc: "2026-01-14T15:00:00Z",
    feature_dependency_ids: ["phase4-ohlcv.open"],
    feature_derivation: {
      derivation_sha256: String(index + 1).repeat(64).slice(0, 64),
      derived_feature_value: featureValue,
      formula_id: "source-decimal-times-frozen-multiplier-v1",
      multiplier: featureValue === "0.15" ? "0.0015" : "0.001",
      schema_version: "phase5-source-feature-derivation-v1",
      source_observation_key: sourceObservation.key,
      source_payload_field: "open",
    },
    fundamental_revision: null,
    membership_source_observation_key: membershipSourceObservation.key,
    price_adjustment_basis: "raw_unadjusted",
    reference_price: "100",
    sample_id: sampleId,
    sample_sha256: String(index + 7).repeat(64).slice(0, 64),
    source_observation_refs: [sourceObservationRef, membershipSourceObservationRef],
    synthetic_ledger_value_rule: "deterministic-synthetic-research-ledger-input-v1",
    target_dependency_ids: ["label.synthetic-forward-two-session-return-v1"],
    universe_membership: {
      as_of_utc: "2026-01-01T05:00:00Z",
      membership_id: membershipNormalizedObservationId,
      membership_status: "included",
      universe_id: "synthetic-us-equity",
      valid_from_utc: "2026-01-01T00:00:00Z",
      valid_to_utc: "2026-02-01T00:00:00Z",
    },
  };
}) satisfies SampleSourceLineage[];

const fitTrainSampleValues = [
  {
    sample_id: "synthetic-post-embargo-01",
    sample_sha256: sampleLineage[1].sample_sha256,
    value: "0.15",
  },
  {
    sample_id: "synthetic-train-01",
    sample_sha256: sampleLineage[3].sample_sha256,
    value: "0.1",
  },
] satisfies components["schemas"]["PreprocessingFitSampleValue"][];
const fitTrainSampleIds = fitTrainSampleValues.map((item) => item.sample_id);
const fitTrainSampleIdsSha256 = "0f4f4afa48c582ed5b1d9ee8f166d426ce7977970de8959f402d82874bf579b2";
const fitPreimageCanonicalJson = JSON.stringify({
  ddof: 1,
  fold_id: foldId,
  fold_sha256: "5".repeat(64),
  mean: "0.125",
  standard_deviation: "0.035355339059327376220042",
  train_sample_ids: fitTrainSampleIds,
  train_sample_ids_sha256: fitTrainSampleIdsSha256,
  train_sample_values: fitTrainSampleValues,
  transformer_id: "train-only-standardizer",
  transformer_version: "phase5-train-only-standardizer-v1",
});

function trialRecord(
  ordinal: number,
  status: TrialRecord["status"],
  overrides: Partial<TrialRecord> = {},
): TrialRecord {
  const completed = status === "completed";
  const configSha = String(ordinal + 4).repeat(64).slice(0, 64);
  return {
    config_preimage: {
      configuration: { model: `synthetic-model-${ordinal + 1}` },
      selection_scope: "synthetic_family_b_fixture_only",
    },
    config_sha256: configSha,
    configuration: {
      model: `synthetic-model-${ordinal + 1}`,
      variant: String(ordinal + 1),
    },
    cost_policy_sha256: "6".repeat(64),
    counts_toward_raw: true,
    effective_trial_contribution: completed ? "0.75" : "1",
    failure_reason: completed ? null : `retained ${status} fixture reason`,
    feature_specification_sha256: "4".repeat(64),
    initiated_at_utc: `2026-01-0${ordinal + 1}T12:00:00Z`,
    initiated_by: "phase5-synthetic-registry",
    label_specification_sha256: "5".repeat(64),
    net_returns: completed ? ["0.008", "0"] : [],
    oos_return_state: completed ? "complete_common_calendar" : status,
    ordinal,
    parent_trial_ids: ordinal === 0 ? [] : [selectedTrialId],
    policy_sha256: "e".repeat(64),
    return_statuses: completed ? ["observed", "no_trade"] : [],
    return_timestamps_utc: completed
      ? ["2026-01-14T16:00:00Z", "2026-01-15T16:00:00Z"]
      : [],
    risk_policy_sha256: "7".repeat(64),
    selection_metric: "mean_net_return",
    selection_policy_sha256: "8".repeat(64),
    selection_scope: "synthetic_family_b_fixture_only",
    sharpe_convention: "per_period_sample_standard_deviation_v1",
    signal_specification_sha256: "9".repeat(64),
    status,
    strategy_family: "B_TIME_SERIES_MOMENTUM_REGIME",
    stress_policy_sha256: "0".repeat(64),
    trial_id:
      ordinal === 0
        ? selectedTrialId
        : `50000000-0000-5000-8000-${String(ordinal + 101).padStart(12, "0")}`,
    trial_key: ordinal === 0 ? "stable-primary" : `${status}-trial-${ordinal + 1}`,
    trial_sha256: String(ordinal + 1).repeat(64).slice(0, 64),
    ...overrides,
  };
}

const summariesResponse = [
  {
    artifact_id: artifactId,
    artifact_sha256: "a".repeat(64),
    created_at_utc: "2026-07-13T20:30:00Z",
    fixture_id: "phase5-reference-fixture",
    no_real_performance_claimed: true,
    promotion_state: "PASS_RESEARCH",
    reason_codes: [],
    synthetic: true,
    warning_count: 2,
  },
] satisfies EvaluationReportSummary[];

const blockedOutcomeResponse = {
  artifact_type: "blocked_synthetic_research_evaluation",
  code_version_git_sha: "b".repeat(40),
  created_at_utc: "2026-07-13T20:31:00Z",
  failure_stage: "snapshot_resolution",
  fixture_id: "phase5-reference-fixture",
  idempotency_sha256: "4".repeat(64),
  mapping_id: "50000000-0000-5000-8000-000000000004",
  no_real_performance_claimed: true,
  outcome_id: outcomeId,
  outcome_sha256: "5".repeat(64),
  policy_id: "50000000-0000-5000-8000-000000000003",
  policy_version: 1,
  promotion_state: "BLOCKED_UNCOMPUTABLE",
  reason_codes: ["required_snapshot_missing"],
  resolved_fixture_random_seed: 17,
  resolved_fixture_sha256: "f".repeat(64),
  resolved_policy_sha256: "e".repeat(64),
  resolved_raw_trial_count: 6,
  resolved_snapshots: [
    {
      mapping_id: "50000000-0000-5000-8000-000000000004",
      mapping_input_sha256: "1".repeat(64),
      mapping_version: 2,
      snapshot_id: snapshotId,
      snapshot_sha256: "d".repeat(64),
    },
  ],
  sanitized_message:
    "Phase 5 evaluation stopped because required evidence was unavailable.",
  schema_version: "phase5-blocked-evaluation-outcome-v1",
  snapshot_ids: [snapshotId, "50000000-0000-5000-8000-000000000802"],
  status: "blocked",
  submission_sha256: "6".repeat(64),
  synthetic: true,
} satisfies BlockedEvaluationOutcome;

const outcomesResponse = [blockedOutcomeResponse] satisfies BlockedEvaluationOutcome[];

const reportResponse = {
  artifact_id: artifactId,
  artifact_schema_version: "phase5-evaluation-report-v1",
  artifact_sha256: "a".repeat(64),
  artifact_type: "synthetic_research_evaluation",
  code_version_git_sha: "b".repeat(40),
  config_hash: "c".repeat(64),
  cost_ledger: [
    {
      allocation_input_sha256: "7".repeat(64),
      borrow_cost: "0.00002",
      capacity_breached: false,
      capacity_cost: "0",
      cost_entry_id: "50000000-0000-5000-8000-000000000501",
      cost_entry_sha256: "8".repeat(64),
      fee_cost: "0.00005",
      fill_status: "filled",
      filled_quantity: "100",
      gross_return: "0.008",
      hard_to_borrow_available: true,
      impact_cost: "0.00020",
      latency_cost: "0.00003",
      net_return: "0.00760",
      ordinal: 0,
      participation_rate: "0.001",
      rejected_quantity: "0",
      requested_quantity: "100",
      return_status: "observed",
      sample_id: "synthetic-oos-01",
      scenario: "baseline",
      spread_cost: "0.00010",
      total_cost: "0.00040",
      unfilled_quantity: "0",
    },
    {
      allocation_input_sha256: "7".repeat(64),
      borrow_cost: "0.00004",
      capacity_breached: false,
      capacity_cost: "0",
      cost_entry_id: "50000000-0000-5000-8000-000000000502",
      cost_entry_sha256: "9".repeat(64),
      fee_cost: "0.00010",
      fill_status: "filled",
      filled_quantity: "100",
      gross_return: "0.008",
      hard_to_borrow_available: true,
      impact_cost: "0.00040",
      latency_cost: "0.00006",
      net_return: "0.00720",
      ordinal: 1,
      participation_rate: "0.001",
      rejected_quantity: "0",
      requested_quantity: "100",
      return_status: "observed",
      sample_id: "synthetic-oos-01",
      scenario: "all_cost_stress",
      spread_cost: "0.00020",
      total_cost: "0.00080",
      unfilled_quantity: "0",
    },
    {
      allocation_input_sha256: "7".repeat(64),
      borrow_cost: "0",
      capacity_breached: true,
      capacity_cost: "0",
      cost_entry_id: "50000000-0000-5000-8000-000000000503",
      cost_entry_sha256: "0".repeat(64),
      fee_cost: "0",
      fill_status: "capacity_rejected",
      filled_quantity: "80",
      gross_return: "0",
      hard_to_borrow_available: true,
      impact_cost: "0",
      latency_cost: "0",
      net_return: "0",
      ordinal: 2,
      participation_rate: "0.002",
      rejected_quantity: "20",
      requested_quantity: "100",
      return_status: "observed",
      sample_id: "synthetic-oos-01",
      scenario: "liquidity_stress",
      spread_cost: "0",
      total_cost: "0",
      unfilled_quantity: "20",
    },
  ],
  created_at_utc: "2026-07-13T20:30:00Z",
  data_snapshots: [
    {
      adapter_id: "phase4-synthetic-pit-adapter",
      adapter_version: "phase4-synthetic-pit-adapter-v1",
      as_of_utc: "2026-07-12T00:00:00Z",
      capability: "ohlcv",
      dataset_id: "synthetic-ohlcv",
      dataset_schema_versions: ["phase4-ohlcv-bar-v1"],
      fixture_set_version: "phase4-synthetic-pit-fixtures-v1",
      product_id: "synthetic-pit-product",
      provider_id: "fable5-synthetic",
      quality_status: "data_quality_accepted",
      snapshot_id: snapshotId,
      snapshot_sha256: "d".repeat(64),
    },
    {
      adapter_id: "phase4-synthetic-pit-adapter",
      adapter_version: "phase4-synthetic-pit-adapter-v1",
      as_of_utc: "2026-07-12T00:00:00Z",
      capability: "universe_membership",
      dataset_id: "synthetic-universe-membership",
      dataset_schema_versions: ["phase4-universe-membership-v1"],
      fixture_set_version: "phase4-synthetic-pit-fixtures-v1",
      product_id: "synthetic-pit-product",
      provider_id: "fable5-synthetic",
      quality_status: "data_quality_accepted",
      snapshot_id: membershipSnapshotId,
      snapshot_sha256: membershipSourceObservationRef.snapshot_sha256,
    },
  ],
  decision_time_utc: "2026-07-12T00:00:00Z",
  disclaimer: "Synthetic research only; no real performance or investment advice.",
  effective_trial_count: "3.0",
  effective_trial_method: "bailey-average-correlation-interpolation-v1",
  evaluation_policy_id: "50000000-0000-5000-8000-000000000003",
  evaluation_policy_sha256: "e".repeat(64),
  evaluation_policy_version: 1,
  feature_specification: {
    availability_rule: "every input available_at must be at or before decision_time",
    content_sha256: "4".repeat(64),
    encoding_policy: "no_encoding_required_v1",
    feature_selection_policy: "no_feature_selection_v1",
    feature_specification_id: "50000000-0000-5000-8000-000000000601",
    formula_id: "synthetic-lagged-score-v1",
    hyperparameter_policy: "frozen_fixture_hyperparameters_v1",
    imputation_policy: "block_missing_feature_v1",
    lookback_rule: "two prior UTC decision sessions only",
    preprocessing_rules: ["phase5-train-only-standardizer-v1"],
    schema_version: "phase5-feature-specification-v1",
    source_fields: ["normalized_observation_reference", "lagged_numeric_value"],
    source_observation_binding_rule: "phase5-exact-snapshot-constituent-value-v1",
    version: "phase5-synthetic-feature-contract-v1",
  },
  fixture_id: "phase5-reference-fixture",
  fixture_sha256: "f".repeat(64),
  fixture_version: "phase5-synthetic-evaluation-fixtures-v1",
  folds: [
    {
      embargo_applied: true,
      embargo_duration_seconds: 172800,
      embargoed_sample_ids: ["synthetic-embargoed-01"],
      fold_id: foldId,
      fold_kind: "cpcv",
      fold_sha256: "5".repeat(64),
      ordinal: 0,
      parent_fold_id: null,
      purged_sample_ids: ["synthetic-purged-overlap-01"],
      test_end_utc: "2026-01-14T16:00:00Z",
      test_sample_ids: ["synthetic-oos-01"],
      test_start_utc: "2026-01-14T16:00:00Z",
      train_end_utc: "2026-01-18T16:00:00Z",
      train_sample_ids: ["synthetic-post-embargo-01", "synthetic-train-01"],
      train_start_utc: "2026-01-01T16:00:00Z",
    },
  ],
  gates: gateCodes.map((gateCode, index): GateResult => ({
    config_hash: "c".repeat(64),
    gate_code: gateCode,
    gate_result_id: `50000000-0000-5000-8000-${String(index + 10).padStart(12, "0")}`,
    gate_result_sha256: String(index).repeat(64).slice(0, 64),
    inputs: gateCode === "DSR" ? { estimated_sharpe: "0.42", sample_size: 24 } : { rows: 24 },
    ordinal: index,
    outcome: "pass",
    reason_codes: gateCode === "DSR" ? ["DSR_REFERENCE_MATCH"] : [],
    results: gateCode === "DSR" ? { probability: "0.97" } : { accepted: true },
    thresholds: gateCode === "DSR" ? { minimum_probability: "0.95" } : {},
    warnings: gateCode === "DSR" ? ["HAC sensitivity recorded"] : [],
  })),
  label_specification: {
    content_sha256: "5".repeat(64),
    delisting_return_policy: "require_explicit_delisting_outcome_v1",
    forecast_horizon: "two UTC decision sessions",
    formula_id: "synthetic-forward-two-session-return-v1",
    information_interval_rule: "closed interval from decision time through horizon end",
    label_specification_id: "50000000-0000-5000-8000-000000000602",
    missing_return_policy: "block_missing_return_v1",
    no_trade_return_policy: "explicit_zero_research_observation_v1",
    schema_version: "phase5-label-specification-v1",
    version: "phase5-synthetic-label-contract-v1",
  },
  mapping_id: "50000000-0000-5000-8000-000000000004",
  mapping_input_sha256: "1".repeat(64),
  mapping_version: 2,
  metrics: [
    {
      annualization_factor: 252,
      calendar: "XNYS",
      denominator: "stitched synthetic OOS observations",
      exclusions: ["failed trials have no fabricated return series"],
      formula_version: "bailey-lopez-de-prado-dsr-2014-eq2-v1",
      frequency: "daily",
      inputs: { sample_size: 24, effective_trials: "3.0" },
      metric_id: "dsr_probability",
      population: "deterministic synthetic outer-fold ledger",
      timezone: "UTC",
      units: "probability",
      value: "0.97",
    },
  ],
  no_real_performance_claimed: true,
  oos_ledger: [
    {
      baseline_net_return: "0.00760",
      decision_time_utc: "2026-01-14T16:00:00Z",
      delisting_return_handled: true,
      fold_id: foldId,
      gross_return: "0.008",
      information_end_utc: "2026-01-14T15:00:00Z",
      information_start_utc: "2026-01-14T15:00:00Z",
      label_t0_utc: "2026-01-14T16:00:00Z",
      label_t1_utc: "2026-01-16T16:00:00Z",
      ledger_entry_id: oosEntryId,
      ledger_entry_sha256: "a".repeat(64),
      ordinal: 0,
      predicted_value: "0.02",
      return_status: "observed",
      sample_id: "synthetic-oos-01",
      sample_sha256: sampleLineage[0].sample_sha256,
      source_observation_refs: [sourceObservationRef, membershipSourceObservationRef],
      trial_id: selectedTrialId,
    },
  ],
  parent_artifact_ids: ["50000000-0000-5000-8000-000000000005"],
  pass_research_is_not_paper_approval: true,
  preprocessing_fits: [
    {
      ddof: 1,
      fit_id: fitId,
      fit_preimage_canonical_json: fitPreimageCanonicalJson,
      fit_sha256: "bb1972591ed9322008367e8448123248e63906da9027bf81add63be890384f23",
      fold_id: foldId,
      fold_sha256: "5".repeat(64),
      mean: "0.125000000000000000000000",
      standard_deviation: "0.035355339059327376220042",
      statistics_sha256: "7f4ffee183d857dbd762f462bce24914a5b4452bc72ee69e093bc39d56511265",
      train_sample_ids: fitTrainSampleIds,
      train_sample_ids_canonical_json: JSON.stringify(fitTrainSampleIds),
      train_sample_ids_sha256: fitTrainSampleIdsSha256,
      train_sample_values: fitTrainSampleValues,
      transformer_id: "train-only-standardizer",
      transformer_version: "phase5-train-only-standardizer-v1",
    },
  ],
  promotion_state: "PASS_RESEARCH",
  provider_source_versions: ["phase4-synthetic-pit-fixtures-v1"],
  random_seed: 17,
  raw_trial_count: 6,
  reason_codes: ["ALL_REQUIRED_GATES_PASS"],
  request_fingerprint_sha256: "2".repeat(64),
  request_fingerprint_version: "phase5-evaluation-request-v1",
  sample_lineage: sampleLineage,
  sample_lineage_sha256: "a".repeat(64),
  snapshot_bundle_sha256: "3".repeat(64),
  source_observations: [sourceObservation, membershipSourceObservation],
  synthetic: true,
  trials: [
    trialRecord(0, "completed"),
    trialRecord(1, "completed"),
    trialRecord(2, "completed"),
    trialRecord(3, "completed"),
    trialRecord(4, "failed"),
    trialRecord(5, "abandoned"),
  ],
  warnings: [
    "PASS_RESEARCH is not paper approval.",
    "Synthetic fixture only; not real performance.",
  ],
} satisfies EvaluationReport;

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("read-only evaluation reports", () => {
  it("renders the complete synthetic report evidence from generated-contract endpoints", async () => {
    const fetchMock = vi.fn().mockImplementation(async (input: string) => {
      if (input.endsWith(`/v1/evaluation-reports/${artifactId}`)) {
        return { ok: true, json: async () => reportResponse, status: 200 };
      }
      if (input.endsWith("/v1/evaluation-reports")) {
        return { ok: true, json: async () => summariesResponse, status: 200 };
      }
      if (input.endsWith(`/v1/evaluation-outcomes/${outcomeId}`)) {
        return { ok: true, json: async () => blockedOutcomeResponse, status: 200 };
      }
      return { ok: true, json: async () => outcomesResponse, status: 200 };
    });
    vi.stubGlobal("fetch", fetchMock);

    const { container } = render(<EvaluationReports />);

    expect(screen.getByRole("status")).toHaveTextContent("Loading immutable evaluation evidence");
    expect(await screen.findByRole("heading", { name: "Evaluation state" })).toBeVisible();
    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8000/v1/evaluation-reports", {
      signal: expect.any(AbortSignal),
    });
    expect(fetchMock).toHaveBeenCalledWith(
      `http://localhost:8000/v1/evaluation-reports/${artifactId}`,
      { signal: expect.any(AbortSignal) },
    );
    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8000/v1/evaluation-outcomes", {
      signal: expect.any(AbortSignal),
    });
    expect(fetchMock).toHaveBeenCalledWith(
      `http://localhost:8000/v1/evaluation-outcomes/${outcomeId}`,
      { signal: expect.any(AbortSignal) },
    );

    expect(screen.getByText("Deterministic synthetic evidence")).toBeVisible();
    expect(screen.getAllByText("No real performance claimed").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/PASS_RESEARCH is not paper approval/i).length).toBeGreaterThan(0);
    expect(screen.getByText("PASS_RESEARCH", { selector: ".evaluationPromotionState" })).toBeVisible();

    const blockedOutcome = within(
      await screen.findByRole("article", {
        name: `Blocked evaluation outcome ${outcomeId}`,
      }),
    );
    expect(blockedOutcome.getByText("BLOCKED_UNCOMPUTABLE")).toBeVisible();
    expect(blockedOutcome.getByText("snapshot_resolution")).toBeVisible();
    expect(blockedOutcome.getByText("required_snapshot_missing")).toBeVisible();
    expect(blockedOutcome.getByText("4".repeat(64))).toBeVisible();
    expect(blockedOutcome.getByText("5".repeat(64))).toBeVisible();
    expect(blockedOutcome.getByText("6")).toBeVisible();

    expect(container.querySelectorAll(".evaluationGateCard")).toHaveLength(12);
    for (const heading of gateHeadings) {
      expect(screen.getByRole("heading", { name: heading })).toBeVisible();
    }
    const dsrGate = screen.getByRole("article", { name: "Deflated Sharpe Ratio gate" });
    expect(within(dsrGate).getByText("Inputs")).toBeVisible();
    expect(within(dsrGate).getByText("Thresholds")).toBeVisible();
    expect(within(dsrGate).getByText("Results")).toBeVisible();
    expect(within(dsrGate).getByText("0.42")).toBeVisible();
    expect(within(dsrGate).getByText("0.95")).toBeVisible();
    expect(within(dsrGate).getByText("0.97")).toBeVisible();
    expect(within(dsrGate).getByText("DSR_REFERENCE_MATCH")).toBeVisible();
    expect(within(dsrGate).getByText("HAC sensitivity recorded")).toBeVisible();

    const counts = screen.getByRole("heading", { name: "Trial counts" }).closest("section");
    expect(counts).not.toBeNull();
    expect(within(counts as HTMLElement).getByText("Raw trial count")).toBeVisible();
    expect(within(counts as HTMLElement).getByText("Effective trial count")).toBeVisible();
    expect(within(counts as HTMLElement).getByText("Failed")).toBeVisible();
    expect(within(counts as HTMLElement).getByText("Abandoned")).toBeVisible();

    const returnCounts = screen
      .getByRole("heading", { name: "Return status counts" })
      .closest("section");
    expect(returnCounts).not.toBeNull();
    const returnCountEvidence = within(returnCounts as HTMLElement);
    expect(
      within(returnCountEvidence.getByText("Trial Observed").closest("div") as HTMLElement).getByText(
        "4",
      ),
    ).toBeVisible();
    expect(
      within(returnCountEvidence.getByText("Trial No Trade").closest("div") as HTMLElement).getByText(
        "4",
      ),
    ).toBeVisible();
    expect(
      within(returnCountEvidence.getByText("OOS Observed").closest("div") as HTMLElement).getByText(
        "1",
      ),
    ).toBeVisible();
    expect(
      within(returnCountEvidence.getByText("Cost Observed").closest("div") as HTMLElement).getByText(
        "3",
      ),
    ).toBeVisible();

    const specifications = screen
      .getByRole("heading", { name: "Feature and label specifications" })
      .closest("section");
    expect(specifications).not.toBeNull();
    const specificationEvidence = within(specifications as HTMLElement);
    expect(specificationEvidence.getByText("synthetic-lagged-score-v1")).toBeVisible();
    expect(specificationEvidence.getByText("synthetic-forward-two-session-return-v1")).toBeVisible();
    expect(specificationEvidence.getByText("normalized_observation_reference")).toBeVisible();
    expect(specificationEvidence.getByText("phase5-train-only-standardizer-v1")).toBeVisible();
    expect(specificationEvidence.getByText("block_missing_feature_v1")).toBeVisible();
    expect(specificationEvidence.getByText("no_encoding_required_v1")).toBeVisible();
    expect(specificationEvidence.getByText("no_feature_selection_v1")).toBeVisible();
    expect(specificationEvidence.getByText("frozen_fixture_hyperparameters_v1")).toBeVisible();
    expect(specificationEvidence.getByText("two UTC decision sessions")).toBeVisible();
    expect(
      specificationEvidence.getByText("closed interval from decision time through horizon end"),
    ).toBeVisible();
    expect(specificationEvidence.getByText("4".repeat(64))).toBeVisible();
    expect(specificationEvidence.getByText("5".repeat(64))).toBeVisible();

    const trials = screen.getByRole("heading", { name: "Trial details" }).closest("section");
    expect(trials).not.toBeNull();
    expect((trials as HTMLElement).querySelectorAll(".evaluationEvidenceCard")).toHaveLength(6);
    const selectedTrial = within(
      within(trials as HTMLElement).getByRole("article", { name: "Trial stable-primary" }),
    );
    expect(selectedTrial.getByText(selectedTrialId)).toBeVisible();
    expect(selectedTrial.getByText("completed")).toBeVisible();
    expect(selectedTrial.getByText("mean_net_return")).toBeVisible();
    expect(selectedTrial.getByText("B_TIME_SERIES_MOMENTUM_REGIME")).toBeVisible();
    expect(selectedTrial.getByText("synthetic_family_b_fixture_only")).toBeVisible();
    expect(selectedTrial.getByText("2026-01-01T12:00:00Z")).toBeVisible();
    expect(selectedTrial.getByText("2026-01-14T16:00:00Z")).toBeVisible();
    expect(selectedTrial.getByText("0.008")).toBeVisible();
    expect(selectedTrial.getByText("Return status: observed")).toBeVisible();
    expect(selectedTrial.getByText("Return status: no_trade")).toBeVisible();
    expect(selectedTrial.getAllByText("synthetic-model-1").length).toBeGreaterThan(0);
    expect(selectedTrial.getByText("Configuration hash preimage")).toBeVisible();
    const failedTrial = within(
      within(trials as HTMLElement).getByRole("article", { name: "Trial failed-trial-5" }),
    );
    expect(failedTrial.getAllByText("failed")).toHaveLength(2);
    expect(failedTrial.getByText("retained failed fixture reason")).toBeVisible();
    expect(failedTrial.getByText("No return calendar recorded")).toBeVisible();
    const abandonedTrial = within(
      within(trials as HTMLElement).getByRole("article", { name: "Trial abandoned-trial-6" }),
    );
    expect(abandonedTrial.getByText("retained abandoned fixture reason")).toBeVisible();

    const folds = screen.getByRole("heading", { name: "Walk-forward folds" }).closest("section");
    expect(folds).not.toBeNull();
    const fold = within(
      within(folds as HTMLElement).getByRole("article", { name: `Fold ${foldId}` }),
    );
    expect(fold.getByText(foldId)).toBeVisible();
    expect(fold.getByText("Cpcv")).toBeVisible();
    expect(fold.getByText("embargo applied")).toBeVisible();
    expect(fold.getByText("172800")).toBeVisible();
    expect(fold.getByText("synthetic-purged-overlap-01")).toBeVisible();
    expect(fold.getByText("synthetic-embargoed-01")).toBeVisible();
    expect(fold.getByText("synthetic-train-01")).toBeVisible();
    expect(fold.getByText("synthetic-oos-01")).toBeVisible();
    expect(fold.getByText("2026-01-01T16:00:00Z")).toBeVisible();
    expect(fold.getAllByText("2026-01-14T16:00:00Z")).toHaveLength(2);

    const fits = screen.getByRole("heading", { name: "Preprocessing fits" }).closest("section");
    expect(fits).not.toBeNull();
    const fit = within(
      within(fits as HTMLElement).getByRole("article", { name: `Preprocessing fit ${fitId}` }),
    );
    expect(fit.getByText(fitId)).toBeVisible();
    expect(fit.getByText(foldId)).toBeVisible();
    expect(fit.getByText("train-only-standardizer")).toBeVisible();
    expect(fit.getByText("phase5-train-only-standardizer-v1")).toBeVisible();
    expect(fit.getByText("synthetic-train-01")).toBeVisible();
    expect(fit.getByText("0.125000000000000000000000")).toBeVisible();
    expect(fit.getByText("0.035355339059327376220042")).toBeVisible();
    expect(
      fit.getByText("bb1972591ed9322008367e8448123248e63906da9027bf81add63be890384f23"),
    ).toBeVisible();
    expect(fit.getByText(fitTrainSampleIdsSha256)).toBeVisible();
    expect(fit.getByText("1")).toBeVisible();

    const oosLedger = within(
      screen.getByRole("table", { name: "OOS prediction and return ledger" }),
    );
    expect(
      screen.getByRole("region", { name: "Scrollable OOS prediction and return ledger" }),
    ).toHaveAttribute("tabindex", "0");
    expect(oosLedger.getByText("synthetic-oos-01")).toBeVisible();
    expect(oosLedger.getByText(`Ledger ID: ${oosEntryId}`)).toBeVisible();
    expect(oosLedger.getByText(`Trial ID: ${selectedTrialId}`)).toBeVisible();
    expect(oosLedger.getByText(`Fold ID: ${foldId}`)).toBeVisible();
    expect(oosLedger.getByText("Predicted value: 0.02")).toBeVisible();
    expect(oosLedger.getByText("Gross return: 0.008")).toBeVisible();
    expect(oosLedger.getByText("Baseline net return: 0.00760")).toBeVisible();
    expect(oosLedger.getByText("Return status: observed")).toBeVisible();
    expect(oosLedger.getByText("Delisting return handled: true")).toBeVisible();
    expect(oosLedger.getByText(`Sample SHA-256: ${sampleLineage[0].sample_sha256}`)).toBeVisible();
    expect(oosLedger.getByText(new RegExp(`raw observation ${rawObservationId}`))).toBeVisible();

    const costLedger = within(screen.getByRole("table", { name: "Component cost ledger" }));
    expect(
      screen.getByRole("region", { name: "Scrollable component cost ledger" }),
    ).toHaveAttribute("tabindex", "0");
    expect(costLedger.getByText("baseline")).toBeVisible();
    expect(costLedger.getByText("all_cost_stress")).toBeVisible();
    expect(costLedger.getByText("liquidity_stress")).toBeVisible();
    const baselineRow = within(costLedger.getByText("baseline").closest("tr") as HTMLElement);
    expect(baselineRow.getByText("Fee: 0.00005")).toBeVisible();
    expect(baselineRow.getByText("Spread: 0.00010")).toBeVisible();
    expect(baselineRow.getByText("Impact: 0.00020")).toBeVisible();
    expect(baselineRow.getByText("Latency: 0.00003")).toBeVisible();
    expect(baselineRow.getByText("Borrow: 0.00002")).toBeVisible();
    expect(baselineRow.getByText("Capacity: 0")).toBeVisible();
    expect(baselineRow.getByText("Total: 0.00040")).toBeVisible();
    expect(baselineRow.getByText("Return status: observed")).toBeVisible();
    expect(baselineRow.getByText("Fill status: filled")).toBeVisible();
    expect(baselineRow.getByText("Requested quantity: 100")).toBeVisible();
    expect(baselineRow.getByText("Filled quantity: 100")).toBeVisible();
    expect(baselineRow.getByText("Rejected quantity: 0")).toBeVisible();
    expect(baselineRow.getByText("Unfilled quantity: 0")).toBeVisible();
    expect(baselineRow.getByText("Capacity breached: false")).toBeVisible();
    expect(baselineRow.getByText("Hard-to-borrow available: true")).toBeVisible();
    const scrollablePre = container.querySelectorAll(".evaluationCanonicalEvidence pre");
    expect(scrollablePre.length).toBeGreaterThan(0);
    for (const pre of scrollablePre) {
      expect(pre).toHaveAttribute("tabindex", "0");
    }

    expect(screen.getByRole("heading", { name: "dsr_probability" })).toBeVisible();
    expect(screen.getByText("bailey-lopez-de-prado-dsr-2014-eq2-v1")).toBeVisible();
    expect(screen.getByText("stitched synthetic OOS observations")).toBeVisible();
    expect(screen.getByRole("heading", { name: "ohlcv" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "universe_membership" })).toBeVisible();
    expect(screen.getAllByText("data_quality_accepted")).toHaveLength(2);
    expect(screen.getAllByText("phase4-ohlcv-bar-v1").length).toBeGreaterThan(0);

    const sourceObservations = within(
      screen.getByRole("heading", { name: "Phase 4 source observations" }).closest("section") as HTMLElement,
    );
    expect(sourceObservations.getAllByText(normalizedObservationId).length).toBeGreaterThan(0);
    expect(sourceObservations.getAllByText(rawObservationId).length).toBeGreaterThan(0);
    expect(sourceObservations.getAllByText(observationRevisionId).length).toBeGreaterThan(0);
    expect(
      sourceObservations.getAllByText(sourceObservationRef.raw_payload_sha256).length,
    ).toBeGreaterThan(0);
    expect(
      sourceObservations.getAllByText(sourceObservationRef.normalized_content_sha256).length,
    ).toBeGreaterThan(0);
    expect(sourceObservations.getByText(/"record_type": "ohlcv_bar"/)).toBeVisible();
    expect(
      sourceObservations.getAllByText(membershipNormalizedObservationId).length,
    ).toBeGreaterThan(0);
    expect(sourceObservations.getByText(/"record_type": "universe_membership"/)).toBeVisible();
    expect(sourceObservations.getByText(/"status": "included"/)).toBeVisible();

    const lineage = within(
      screen.getByRole("heading", { name: "Sample lineage" }).closest("section") as HTMLElement,
    );
    expect(lineage.getAllByText("a".repeat(64)).length).toBeGreaterThan(0);
    expect(lineage.getByText(sampleLineage[0].sample_sha256)).toBeVisible();
    expect(lineage.getAllByText(rawObservationId).length).toBeGreaterThan(0);
    expect(
      lineage.getAllByText("source-decimal-times-frozen-multiplier-v1").length,
    ).toBeGreaterThan(0);
    expect(
      lineage.getAllByText("deterministic-synthetic-research-ledger-input-v1").length,
    ).toBeGreaterThan(0);
    expect(lineage.getAllByText(/"membership_status": "included"/).length).toBeGreaterThan(0);
    expect(lineage.getAllByText(/"fundamental_revision": null/).length).toBeGreaterThan(0);
    expect(lineage.getAllByText(sampleLineage[0].feature_derivation.derivation_sha256).length).toBeGreaterThan(0);

    expect(screen.getAllByText("Code version Git SHA").length).toBeGreaterThan(0);
    expect(screen.getAllByText("b".repeat(40)).length).toBeGreaterThan(0);
    expect(screen.getByText("Random seed")).toBeVisible();
    expect(screen.getByText("Provider/source versions")).toBeVisible();
    expect(screen.getByText("ALL_REQUIRED_GATES_PASS")).toBeVisible();

    expect(container.querySelector("form")).toBeNull();
    expect(container.querySelector("button, input, select, textarea")).toBeNull();
    expect(container.textContent).not.toMatch(/\b(position|order|execution)\b/i);
  });

  it("shows a persisted blocked outcome when no completed report exists", async () => {
    const fetchMock = vi.fn().mockImplementation(async (input: string) => {
      if (input.endsWith("/v1/evaluation-reports")) {
        return { ok: true, json: async () => [], status: 200 };
      }
      if (input.endsWith(`/v1/evaluation-outcomes/${outcomeId}`)) {
        return { ok: true, json: async () => blockedOutcomeResponse, status: 200 };
      }
      return { ok: true, json: async () => outcomesResponse, status: 200 };
    });
    vi.stubGlobal("fetch", fetchMock);

    const { container } = render(<EvaluationReports />);

    expect(await screen.findByText("No immutable evaluation reports are available yet.")).toBeVisible();
    expect(
      await screen.findByRole("article", { name: `Blocked evaluation outcome ${outcomeId}` }),
    ).toBeVisible();
    expect(container.querySelector("form, button, input, select, textarea")).toBeNull();
  });

  it("renders empty and failure states without controls", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue({ ok: true, json: async () => [], status: 200 });
    vi.stubGlobal("fetch", fetchMock);

    const empty = render(<EvaluationReports />);
    expect(await screen.findByText("No immutable evaluation reports are available yet.")).toBeVisible();
    expect(
      await screen.findByText("No persisted blocked evaluation outcomes are available yet."),
    ).toBeVisible();
    expect(fetchMock).toHaveBeenCalledTimes(2);
    empty.unmount();

    fetchMock.mockImplementation(async (input: string) =>
      input.endsWith("/v1/evaluation-reports")
        ? { ok: false, status: 503 }
        : { ok: true, json: async () => [], status: 200 },
    );
    const failed = render(<EvaluationReports />);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Evaluation evidence could not be loaded",
    );
    expect(failed.container.querySelector("form")).toBeNull();
    expect(failed.container.querySelector("button, input, select, textarea")).toBeNull();
  });
});
