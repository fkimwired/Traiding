import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ResearchRunCard } from "../app/research/ResearchWorkspace";
import type { EvidenceIndex } from "../lib/evidence-index";

const sha = "a".repeat(64);
const runId = "10000000-0000-4000-8000-000000000001";
const mappingId = "20000000-0000-4000-8000-000000000001";
const snapshotId = "25000000-0000-4000-8000-000000000001";
const reportId = "30000000-0000-4000-8000-000000000001";
const policyId = "35000000-0000-4000-8000-000000000001";

function fixtureIndex() {
  const run = {
    artifact_sha256: sha,
    attempts: [
      {
        attempt_sha256: sha,
        configuration_sha256: sha,
        failure_reason: "synthetic cost stress failed",
        ordinal: 1,
        phase5_trial_id: "36000000-0000-4000-8000-000000000001",
        phase5_trial_key: "trial-1",
        status: "failed",
      },
      {
        attempt_sha256: "b".repeat(64),
        configuration_sha256: sha,
        failure_reason: "superseded deterministic trial",
        ordinal: 2,
        phase5_trial_id: "36000000-0000-4000-8000-000000000002",
        phase5_trial_key: "trial-2",
        status: "abandoned",
      },
    ],
    baseline_comparisons: [{ outcome: "rejected" }],
    code_version_git_sha: "c".repeat(40),
    configuration_id: "phase6-a-pass-v2",
    configuration_sha256: sha,
    created_at_utc: "2026-07-14T12:00:00Z",
    family: "A_CROSS_SECTIONAL_EQUITY_RANKING",
    mapping_id: mappingId,
    mapping_input_sha256: sha,
    mapping_version: 1,
    phase5_evaluation: {
      config_hash: sha,
      effective_trial_count: "2",
      evaluation_outcome_id: null,
      evaluation_report_id: reportId,
      evaluation_report_sha256: sha,
      fixture_id: "phase6-a-pass-v2",
      fixture_sha256: sha,
      gate_codes: ["DSR", "COST_STRESS"],
      phase5_trial_set_sha256: sha,
      policy_id: policyId,
      policy_sha256: sha,
      policy_version: 1,
      promotion_state: "FAIL_REJECT",
      raw_trial_count: 2,
      snapshot_bundle_sha256: sha,
    },
    pipeline_input_sha256: sha,
    random_seed: 5,
    reason_codes: ["cost_stress_failed"],
    run_id: runId,
    snapshot_bundle_sha256: sha,
    snapshot_bindings: [
      {
        as_of_utc: "2026-07-14T00:00:00Z",
        binding_sha256: sha,
        capability: "ohlcv",
        mapping_id: mappingId,
        mapping_input_sha256: sha,
        ordinal: 1,
        quality_status: "data_quality_accepted",
        snapshot_id: snapshotId,
        snapshot_sha256: sha,
      },
    ],
    source_reproduction_audit: {
      audit_id: "40000000-0000-4000-8000-000000000001",
      audit_sha256: sha,
      exact_match: true,
    },
    status: "completed",
    trial_economics: [{}],
  };
  const index = {
    assessmentTimelines: {},
    assessments: [],
    cards: [],
    evaluationOutcomes: [],
    evaluationReports: [
      {
        artifact_id: run.phase5_evaluation.evaluation_report_id,
        artifact_sha256: sha,
        code_version_git_sha: run.code_version_git_sha,
        config_hash: sha,
        created_at_utc: run.created_at_utc,
        data_snapshots: [],
        effective_trial_count: "2",
        evaluation_policy_id: policyId,
        evaluation_policy_sha256: sha,
        evaluation_policy_version: 1,
        fixture_id: "phase6-a-pass-v2",
        fixture_sha256: sha,
        gates: [
          {
            config_hash: sha,
            gate_code: "DSR",
            gate_result_id: "50000000-0000-4000-8000-000000000001",
            gate_result_sha256: sha,
            inputs: {},
            ordinal: 4,
            outcome: "pass",
            reason_codes: ["dsr_passed"],
            results: { dsr: "0.20" },
            thresholds: { minimum_dsr: "0.10" },
            warnings: [],
          },
          {
            config_hash: sha,
            gate_code: "COST_STRESS",
            gate_result_id: "50000000-0000-4000-8000-000000000002",
            gate_result_sha256: "b".repeat(64),
            inputs: {},
            ordinal: 7,
            outcome: "fail",
            reason_codes: ["stressed_net_performance_failed"],
            results: { stressed_net_pnl: "-1.00" },
            thresholds: { minimum_stressed_net_pnl: "0.00" },
            warnings: [],
          },
        ],
        mapping_id: mappingId,
        mapping_input_sha256: sha,
        mapping_version: 1,
        promotion_state: "FAIL_REJECT",
        random_seed: 5,
        raw_trial_count: 2,
        snapshot_bundle_sha256: sha,
        trials: [
          {
            config_sha256: sha,
            status: "failed",
            trial_id: "36000000-0000-4000-8000-000000000001",
            trial_key: "trial-1",
          },
          {
            config_sha256: sha,
            status: "abandoned",
            trial_id: "36000000-0000-4000-8000-000000000002",
            trial_key: "trial-2",
          },
        ],
      },
    ],
    mappings: [],
    researchRunSummaries: [],
    researchRuns: [run],
    revocations: [],
    snapshots: [
      {
        manifest: {
          payload: {
            mapping: {
              canonical_family: "A_CROSS_SECTIONAL_EQUITY_RANKING",
              mapping_id: mappingId,
              mapping_input_sha256: sha,
              mapping_version: 1,
            },
            request: {
              as_of_utc: "2026-07-14T00:00:00Z",
              capability: "ohlcv",
              mapping: {
                canonical_family: "A_CROSS_SECTIONAL_EQUITY_RANKING",
                mapping_id: mappingId,
                mapping_input_sha256: sha,
                mapping_version: 1,
              },
            },
          },
          snapshot_id: snapshotId,
          snapshot_sha256: sha,
        },
        quality_status: "data_quality_accepted",
        snapshot_id: snapshotId,
        snapshot_sha256: sha,
      },
    ],
  } as unknown as EvidenceIndex;
  return { index, run: index.researchRuns[0] };
}

describe("ResearchRunCard", () => {
  it("uses the persisted outcome instead of treating a pass-like configuration identity as truth", () => {
    const { index, run } = fixtureIndex();
    render(<ResearchRunCard index={index} run={run} />);

    expect(screen.getByText("Research is ineligible")).toBeInTheDocument();
    expect(screen.getByText("FAIL_REJECT")).toBeInTheDocument();
    expect(screen.getByText("phase6-a-pass-v2")).toBeInTheDocument();
    expect(screen.getAllByText("stressed_net_performance_failed")).toHaveLength(2);
  });

  it("retains failed and abandoned trials and labels the reproduction audit narrowly", () => {
    const { index, run } = fixtureIndex();
    render(<ResearchRunCard index={index} run={run} />);

    expect(screen.getByText("Complete trial attempts")).toBeInTheDocument();
    expect(screen.getByText("Phase 6 source-reproduction audit")).toBeInTheDocument();
    expect(
      screen.getByText("This audit proves prepared-source reproduction only; it is not a general audit entry."),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Trace source to artifact" })).toHaveAttribute(
      "href",
      `/lineage?run_id=${runId}`,
    );
  });

  it("shows the exact blocked outcome and never substitutes a same-mapping report", () => {
    const { index, run } = fixtureIndex();
    run.phase5_evaluation.evaluation_report_id = null;
    run.phase5_evaluation.evaluation_report_sha256 = null;
    run.phase5_evaluation.evaluation_outcome_id = "70000000-0000-4000-8000-000000000001";
    run.phase5_evaluation.gate_codes = [];
    run.phase5_evaluation.phase5_trial_set_sha256 = null;
    run.phase5_evaluation.promotion_state = "BLOCKED_UNCOMPUTABLE";
    run.status = "blocked";
    index.evaluationOutcomes.push({
      fixture_id: run.phase5_evaluation.fixture_id,
      mapping_id: mappingId,
      outcome_id: run.phase5_evaluation.evaluation_outcome_id,
      outcome_sha256: "d".repeat(64),
      policy_id: run.phase5_evaluation.policy_id,
      policy_version: run.phase5_evaluation.policy_version,
      promotion_state: "BLOCKED_UNCOMPUTABLE",
      reason_codes: ["pbo_uncomputable"],
      resolved_fixture_sha256: run.phase5_evaluation.fixture_sha256,
      resolved_policy_sha256: run.phase5_evaluation.policy_sha256,
      resolved_raw_trial_count: run.phase5_evaluation.raw_trial_count,
      resolved_snapshots: [
        {
          mapping_id: mappingId,
          mapping_input_sha256: sha,
          mapping_version: 1,
          snapshot_id: snapshotId,
          snapshot_sha256: sha,
        },
      ],
      sanitized_message: "Selection diagnostics were uncomputable.",
      snapshot_ids: [snapshotId],
      status: "blocked",
    } as unknown as EvidenceIndex["evaluationOutcomes"][number]);

    render(<ResearchRunCard index={index} run={run} />);

    expect(screen.getByText("Exact fail-closed evaluation artifact")).toBeInTheDocument();
    expect(screen.getByText("Selection diagnostics were uncomputable.")).toBeInTheDocument();
    expect(screen.queryByText("DSR")).not.toBeInTheDocument();
  });

  it("treats research-only gates as blocking and critical before positive gates", () => {
    const { index, run } = fixtureIndex();
    index.evaluationReports[0].gates.push({
      config_hash: sha,
      gate_code: "REGIME",
      gate_result_id: "50000000-0000-4000-8000-000000000003",
      gate_result_sha256: "c".repeat(64),
      inputs: {},
      ordinal: 9,
      outcome: "research_only",
      reason_codes: ["regime_dependent"],
      results: {},
      thresholds: {},
      warnings: [],
    });
    run.phase5_evaluation.gate_codes.push("REGIME");

    render(<ResearchRunCard index={index} run={run} />);

    const regimeCard = screen.getByText("REGIME").closest("article");
    expect(regimeCard).toHaveAttribute("data-blocking", "true");
    expect(within(regimeCard!).getByText("Blocking gate")).toBeVisible();
    expect(within(regimeCard!).getByText("research_only")).toHaveAttribute(
      "data-tone",
      "critical",
    );
    const gateHeadings = screen.getAllByRole("heading", { level: 3 }).map((heading) => heading.textContent);
    expect(gateHeadings.indexOf("REGIME")).toBeLessThan(gateHeadings.indexOf("DSR"));
  });

  it("lets an exact evaluation conflict dominate an otherwise positive run", () => {
    const { index, run } = fixtureIndex();
    run.status = "completed";
    run.reason_codes = [];
    run.phase5_evaluation.promotion_state = "PASS_RESEARCH";
    run.phase5_evaluation.evaluation_report_sha256 = "f".repeat(64);
    index.evaluationReports[0].promotion_state = "PASS_RESEARCH";

    const { container } = render(<ResearchRunCard index={index} run={run} />);

    expect(container.querySelector(".researchRunCard")).toHaveAttribute("data-blocking", "true");
    expect(screen.getByText("Research is ineligible")).toBeVisible();
    expect(screen.getByText(/exact evaluation or snapshot reference is missing, mismatched/i)).toBeVisible();
    expect(screen.queryByText("Prerequisite only")).not.toBeInTheDocument();
  });

  it("lets an exact snapshot conflict dominate an otherwise positive run", () => {
    const { index, run } = fixtureIndex();
    run.status = "completed";
    run.reason_codes = [];
    run.phase5_evaluation.promotion_state = "PASS_RESEARCH";
    index.evaluationReports[0].promotion_state = "PASS_RESEARCH";
    run.snapshot_bindings[0].snapshot_sha256 = "f".repeat(64);

    const { container } = render(<ResearchRunCard index={index} run={run} />);

    expect(container.querySelector(".researchRunCard")).toHaveAttribute("data-blocking", "true");
    expect(screen.getByText("Research is ineligible")).toBeVisible();
    expect(screen.getByText(/exact evaluation or snapshot reference is missing/i)).toBeVisible();
    expect(screen.getByText(/No mapping-level snapshot was substituted/i)).toBeVisible();
    expect(screen.queryByText("Prerequisite only")).not.toBeInTheDocument();
  });
});
