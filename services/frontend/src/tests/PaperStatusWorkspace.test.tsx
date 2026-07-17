import type { components } from "@fable5/contracts";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { PaperStatusWorkspace } from "../app/paper/PaperStatusWorkspace";
import { fable5Api } from "../lib/api";
import { useEvidenceIndex } from "../lib/evidence-index";
import {
  approvedAssessment,
  approvedAssessmentId,
  governanceIndex,
  rejectedAssessmentId,
  revocationId,
} from "./governance-fixtures";

vi.mock("../lib/evidence-index", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/evidence-index")>();
  return { ...actual, useEvidenceIndex: vi.fn() };
});

const reload = vi.fn();
const simulationRunId = "90000000-0000-4000-8000-000000000001";
const transitionAssessmentId = "90000000-0000-4000-8000-000000000002";
const ledgerEntryId = "90000000-0000-4000-8000-000000000003";
const hash = (value: string) => value.repeat(64);

const completedSimulation = {
  approval_policy_sha256: hash("a"),
  approval_policy_version_id: "30000000-0000-4000-8000-000000000001",
  approval_scope_sha256: hash("b"),
  approval_scope_version_id: "40000000-0000-4000-8000-000000000001",
  artifact_schema_version: "phase10-local-paper-simulation-v1",
  artifact_sha256: hash("c"),
  authorization_sha256: hash("d"),
  checks: [
    {
      check_sha256: hash("e"),
      code: "LOCAL_BOUNDARY_ENFORCED",
      evidence_sha256s: [hash("f")],
      observed_value: "true",
      ordinal: 1,
      reason_code: "check_passed",
      schema_version: "phase10-local-simulation-check-v1",
      status: "PASS",
      threshold_value: "true",
    },
  ],
  configuration: {
    approved_proposed_notional: "1000.00000000",
    available_at_utc: "2026-07-16T11:59:00Z",
    average_daily_volume: "1000000.00000000",
    canonical_family: "synthetic_equity",
    configuration_id: "phase10-a-local-mock-qa-v1",
    configuration_instance_id: "90000000-0000-4000-8000-000000000004",
    configuration_sha256: hash("1"),
    decision_time_utc: "2026-07-16T12:00:00Z",
    effective_trial_count: "1",
    external_routing_absent: true,
    live_path_absent: true,
    llm_decision_role_absent: true,
    local_cost_model_id: "phase10-local-transparent-cost-v1",
    local_mock_only: true,
    local_slippage_model_id: "phase10-local-transparent-slippage-v1",
    mock_entity_id: "SYNTHETIC-ASSET-001",
    mock_observation_id: "90000000-0000-4000-8000-000000000005",
    mock_observation_sha256: hash("2"),
    mock_snapshot_id: "90000000-0000-4000-8000-000000000006",
    mock_snapshot_sha256: hash("3"),
    mock_universe_id: "phase10-local-mock-universe-v1",
    model_id: "sector-relative-rank-linear-v1",
    observed_at_utc: "2026-07-16T11:58:00Z",
    random_seed: 104729,
    raw_trial_count: 1,
    reference_price: "100.00000000",
    requested_quantity: "10.00000000",
    required_audit_fields: ["config_hash", "data_snapshot_id", "git_sha", "random_seed"],
    required_capabilities: ["point_in_time", "cost_model", "slippage_model"],
    research_artifact_sha256: hash("4"),
    research_configuration_id: "phase6-a-pass-v2",
    research_configuration_sha256: hash("5"),
    research_run_id: "20000000-0000-4000-8000-000000000002",
    research_snapshot_bundle_sha256: hash("6"),
    research_specification_sha256: hash("7"),
    schema_version: "phase10-local-simulation-configuration-v1",
    signal_definition_sha256: hash("8"),
    signal_rule_id: "phase6-a-score-positive-long-flat-v1",
    source_slippage_model_id: "phase5-stress-slippage-v1",
    source_snapshot_bindings: [],
    source_transaction_cost_model_id: "phase5-stress-cost-v1",
    starting_cash: "100000.00000000",
    synthetic: true,
    synthetic_model_output: "1.00000000",
    target_forecast_horizon: "5d",
    volatility: "0.20000000",
  },
  created_at_utc: "2026-07-16T12:00:01Z",
  currentness_state_sha256: hash("9"),
  decision_time_utc: "2026-07-16T12:00:00Z",
  disclaimer:
    "Deterministic synthetic local paper simulation only; no external routing, live trading, real performance claim, or personalized investment advice.",
  effective_trial_count: "1",
  external_routing_absent: true,
  external_submission: false,
  human_authorization_evidence_id: "50000000-0000-4000-8000-000000000002",
  ledger_entries: [
    {
      approved_proposed_notional: "1000.00000000",
      available_at_utc: "2026-07-16T11:59:00Z",
      average_daily_volume: "1000000.00000000",
      borrow_cost: "0.00000000",
      capacity_cost: "0.01000000",
      cash_after: "98998.10000000",
      cash_before: "100000.00000000",
      commission_cost: "0.50000000",
      decision_time_utc: "2026-07-16T12:00:00Z",
      entity_id: "SYNTHETIC-ASSET-001",
      external_submission: false,
      fill_status: "SIMULATED_FILLED",
      filled_quantity: "10.00000000",
      impact_cost: "0.20000000",
      latency_cost: "0.01000000",
      ledger_entry_id: ledgerEntryId,
      ledger_entry_sha256: hash("0"),
      live_path_absent: true,
      local_cost_model_id: "phase10-local-transparent-cost-v1",
      local_mock_only: true,
      local_slippage_model_id: "phase10-local-transparent-slippage-v1",
      mock_observation_id: "90000000-0000-4000-8000-000000000005",
      mock_observation_sha256: hash("2"),
      mock_snapshot_id: "90000000-0000-4000-8000-000000000006",
      mock_snapshot_sha256: hash("3"),
      model_id: "sector-relative-rank-linear-v1",
      observed_at_utc: "2026-07-16T11:58:00Z",
      ordinal: 1,
      participation_rate: "0.00001000",
      position_quantity_after: "10.00000000",
      position_quantity_before: "0.00000000",
      reference_price: "100.00000000",
      regulatory_fee_cost: "0.01000000",
      rejected_quantity: "0.00000000",
      requested_quantity: "10.00000000",
      schema_version: "phase10-local-simulation-ledger-v1",
      signal_rule_id: "phase6-a-score-positive-long-flat-v1",
      signal_state: "LONG",
      signal_value: "1.00000000",
      simulated_fill_price: "100.10000000",
      simulated_paper_only: true,
      simulated_side: "BUY",
      simulation_run_id: simulationRunId,
      source_slippage_model_id: "phase5-stress-slippage-v1",
      source_transaction_cost_model_id: "phase5-stress-cost-v1",
      spread_cost: "0.15000000",
      synthetic: true,
      total_cost: "0.88000000",
      unfilled_quantity: "0.00000000",
      universe_id: "phase10-local-mock-universe-v1",
      volatility: "0.20000000",
    },
  ],
  live_path_absent: true,
  local_mock_only: true,
  no_personalized_investment_advice: true,
  no_real_performance_claimed: true,
  outcome: "SIMULATED_COMPLETE",
  phase10_code_version_git_sha: "a".repeat(40),
  phase6_lineage_sha256: hash("b"),
  random_seed: 104729,
  raw_trial_count: 1,
  reason_codes: ["simulation_completed"],
  request_fingerprint_sha256: hash("c"),
  research_artifact_sha256: hash("4"),
  research_run_id: "20000000-0000-4000-8000-000000000002",
  risk_input_id: "60000000-0000-4000-8000-000000000001",
  risk_input_sha256: hash("d"),
  simulated_paper_only: true,
  simulation_idempotency_key: "phase10-ui-key",
  simulation_run_id: simulationRunId,
  source_assessment_artifact_sha256: approvedAssessment.artifact_sha256,
  source_assessment_id: approvedAssessmentId,
  synthetic: true,
  transition_assessment_artifact_sha256: hash("e"),
  transition_assessment_id: transitionAssessmentId,
  transition_currentness_state_sha256: hash("f"),
  transition_revocation_set_sha256: hash("1"),
} as unknown as components["schemas"]["PaperSimulationArtifact"];

const blockedSimulation = {
  ...completedSimulation,
  artifact_sha256: hash("2"),
  checks: completedSimulation.checks.map((check) => ({
    ...check,
    observed_value: "false",
    reason_code: "authorization_revoked",
    status: "BLOCKED" as const,
  })),
  ledger_entries: [],
  outcome: "BLOCKED" as const,
  reason_codes: ["authorization_revoked"],
  simulation_idempotency_key: "phase10-ui-blocked-key",
  simulation_run_id: "90000000-0000-4000-8000-000000000007",
} as components["schemas"]["PaperSimulationArtifact"];

function summaryFor(artifact: components["schemas"]["PaperSimulationArtifact"]) {
  return {
    artifact_sha256: artifact.artifact_sha256,
    configuration_id: artifact.configuration.configuration_id,
    created_at_utc: artifact.created_at_utc,
    decision_time_utc: artifact.decision_time_utc,
    external_submission: artifact.external_submission,
    live_path_absent: artifact.live_path_absent,
    local_mock_only: artifact.local_mock_only,
    no_personalized_investment_advice: artifact.no_personalized_investment_advice,
    no_real_performance_claimed: artifact.no_real_performance_claimed,
    outcome: artifact.outcome,
    reason_codes: artifact.reason_codes,
    simulated_paper_only: artifact.simulated_paper_only,
    simulation_run_id: artifact.simulation_run_id,
    source_assessment_id: artifact.source_assessment_id,
    synthetic: artifact.synthetic,
    transition_assessment_id: artifact.transition_assessment_id,
  } satisfies components["schemas"]["PaperSimulationSummary"];
}

beforeEach(() => {
  vi.spyOn(fable5Api, "listLocalSimulations").mockImplementation(
    () => new Promise(() => undefined),
  );
  vi.spyOn(fable5Api, "getLocalSimulation").mockResolvedValue({
    error: { kind: "not-found", message: "not loaded", retrySafe: true, status: 404 },
    ok: false,
  });
  vi.spyOn(fable5Api, "createLocalSimulation").mockResolvedValue({
    error: { kind: "unavailable", message: "not configured", retrySafe: true },
    ok: false,
  });
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.clearAllMocks();
});

describe("simulated paper status workspace", () => {
  it("renders exact immutable status, timeline, blockers, and lineage without create fields", () => {
    vi.mocked(useEvidenceIndex).mockReturnValue({
      data: governanceIndex,
      reload,
      retrySafe: true,
      status: "success",
    });

    const { container } = render(<PaperStatusWorkspace />);

    expect(screen.getAllByText("SIMULATED").length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { name: "Simulated Paper Status" })).toBeVisible();
    const assessmentArticle = screen.getByRole("article", { name: rejectedAssessmentId });
    const assessment = within(assessmentArticle);
    expect(assessment.getAllByText("FAIL_REJECT").length).toBeGreaterThan(0);
    expect(
      assessment.getByText("Blocking evidence dominates this historical result"),
    ).toBeVisible();
    expect(assessment.queryByText("Execution authorized")).not.toBeInTheDocument();
    expect(assessment.queryByText("Execution ready")).not.toBeInTheDocument();
    expect(assessment.getByText("policy_expired")).toBeVisible();
    expect(assessment.getByText("authorization_revoked")).toBeVisible();
    expect(assessment.getByText("Review 2026-07-15T00:00:00Z")).toBeVisible();
    expect(assessment.getByText("Expires 2026-07-15T12:00:00Z")).toBeVisible();
    expect(assessment.getByText("Observed 2026-07-14T11:55:00Z")).toBeVisible();

    const checks = Array.from(assessmentArticle.querySelectorAll(".checkList > li strong")).map(
      (node) => node.textContent,
    );
    expect(checks).toEqual([
      "Server ordinal 1: RESEARCH_PASS",
      "Server ordinal 2: POLICY_CURRENT",
      "Server ordinal 3: REVOCATION_CLEAR",
    ]);

    const assessmentLink = assessment.getByRole("link", { name: "Trace source to artifact" });
    expect(assessmentLink).toHaveAttribute(
      "href",
      `/lineage?assessment_id=${rejectedAssessmentId}`,
    );
    const revocation = within(screen.getByRole("article", { name: revocationId }));
    expect(
      revocation.getByText("Immutable revocation evidence exists and remains blocking."),
    ).toBeVisible();
    expect(revocation.queryByText("Synthetic authorization was withdrawn.")).not.toBeInTheDocument();
    expect(revocation.getByRole("link", { name: "Trace source to artifact" })).toHaveAttribute(
      "href",
      `/lineage?assessment_id=${rejectedAssessmentId}&revocation_id=${revocationId}`,
    );

    expect(screen.getByLabelText("Approval assessment")).toBeVisible();
    expect(
      screen.getByRole("button", { name: "Run deterministic local simulation" }),
    ).toBeDisabled();
    expect(container.querySelectorAll("form select")).toHaveLength(1);
    expect(container.querySelector("form input, form textarea")).toBeNull();
    expect(container.querySelector("[name='quantity'], [name='side'], [name='symbol']")).toBeNull();
  });

  it("announces deterministic loading, empty, and retry-safe failure states", () => {
    vi.mocked(useEvidenceIndex).mockReturnValue({
      message: "Loading immutable evidence...",
      reload,
      retrySafe: true,
      status: "loading",
    });
    const loading = render(<PaperStatusWorkspace />);
    expect(screen.getAllByRole("status").some((node) => node.textContent?.includes("Loading immutable evidence"))).toBe(true);
    loading.unmount();

    vi.mocked(useEvidenceIndex).mockReturnValue({
      message: "No persisted Phase 2-7 evidence is available.",
      reload,
      retrySafe: true,
      status: "empty",
    });
    const empty = render(<PaperStatusWorkspace />);
    expect(
      screen
        .getAllByRole("status")
        .some((node) => node.textContent?.includes("No persisted Phase 2-7 evidence is available.")),
    ).toBe(true);
    empty.unmount();

    vi.mocked(useEvidenceIndex).mockReturnValue({
      error: {
        kind: "unavailable",
        message: "The API could not be reached.",
        retrySafe: true,
      },
      reload,
      retrySafe: true,
      status: "error",
    });
    const failed = render(<PaperStatusWorkspace />);
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Historical governance evidence could not be loaded",
    );
    fireEvent.click(screen.getByRole("button", { name: "Retry read" }));
    expect(reload).toHaveBeenCalledOnce();
    expect(failed.container.querySelector("form input, form textarea")).toBeNull();
  });

  it("lets a non-passing immutable check dominate a contradictory positive label", () => {
    const contradictoryAssessment = {
      ...approvedAssessment,
      checks: approvedAssessment.checks.map((check, index) =>
        index === 0
          ? {
              ...check,
              reason_code: "research_prerequisite_not_passed",
              status: "BLOCKED" as const,
            }
          : check,
      ),
    };
    vi.mocked(useEvidenceIndex).mockReturnValue({
      data: {
        ...governanceIndex,
        assessments: [contradictoryAssessment],
        revocations: [],
      },
      reload,
      retrySafe: true,
      status: "success",
    });

    render(<PaperStatusWorkspace />);

    const assessment = screen.getByRole("article", { name: approvedAssessmentId });
    expect(assessment).toHaveAttribute("data-blocking", "true");
    expect(assessment.querySelector(":scope > .cardHeader .statusBadge")).toHaveAttribute(
      "data-tone",
      "critical",
    );
    expect(
      within(assessment).getByText("Blocking evidence dominates this historical result"),
    ).toBeVisible();
    expect(within(assessment).getByText(/1 non-passing server check/)).toBeVisible();
    fireEvent.change(screen.getByLabelText("Approval assessment"), {
      target: { value: approvedAssessmentId },
    });
    expect(
      screen.getByRole("button", { name: "Run deterministic local simulation" }),
    ).toBeDisabled();
    expect(screen.getByText("Known blocking evidence prevents submission")).toBeVisible();
  });

  it("renders a timeline 404 as blocking without discarding the complete assessment", () => {
    vi.mocked(useEvidenceIndex).mockReturnValue({
      data: {
        ...governanceIndex,
        assessments: [approvedAssessment],
        assessmentTimelineFailures: {
          [approvedAssessmentId]: {
            kind: "not-found",
            message: "The referenced immutable record is unavailable.",
            retrySafe: true,
            status: 404,
          },
        },
        assessmentTimelines: {},
        revocations: [],
      },
      reload,
      retrySafe: true,
      status: "success",
    });

    render(<PaperStatusWorkspace />);

    const assessment = screen.getByRole("article", { name: approvedAssessmentId });
    expect(assessment).toHaveAttribute("data-blocking", "true");
    expect(within(assessment).getAllByText("APPROVED_PAPER").length).toBeGreaterThan(0);
    expect(within(assessment).getByText(approvedAssessment.artifact_sha256)).toBeVisible();
    const timelineAlert = within(assessment).getByRole("alert");
    expect(timelineAlert).toHaveTextContent("Historical timeline evidence was not resolved");
    expect(timelineAlert).toHaveTextContent("The referenced immutable record is unavailable.");
    expect(timelineAlert).toHaveTextContent("not-found (HTTP 404)");
    expect(within(assessment).getByText(/1 unresolved historical timeline/)).toBeVisible();
  });

  it("submits only an assessment reference and renders the exact completed artifact", async () => {
    vi.mocked(useEvidenceIndex).mockReturnValue({
      data: {
        ...governanceIndex,
        assessments: [approvedAssessment],
        revocations: [],
      },
      reload,
      retrySafe: true,
      status: "success",
    });
    vi.mocked(fable5Api.createLocalSimulation).mockResolvedValue({
      data: completedSimulation,
      ok: true,
      retrySafe: true,
      status: 201,
    });

    const { container } = render(
      <PaperStatusWorkspace idempotencyKeyFactory={() => "phase10-ui-key"} />,
    );
    fireEvent.change(screen.getByLabelText("Approval assessment"), {
      target: { value: approvedAssessmentId },
    });
    expect(screen.getByText(/Eligible for authoritative server revalidation/)).toBeVisible();
    fireEvent.click(
      screen.getByRole("button", { name: "Run deterministic local simulation" }),
    );

    await waitFor(() =>
      expect(fable5Api.createLocalSimulation).toHaveBeenCalledWith(
        {
          approval_assessment_id: approvedAssessmentId,
          simulation_idempotency_key: "phase10-ui-key",
        },
        expect.any(AbortSignal),
      ),
    );
    const artifact = await screen.findByRole("article", { name: simulationRunId });
    expect(artifact).toHaveFocus();
    expect(within(artifact).getByText("SIMULATED_COMPLETE")).toBeVisible();
    expect(within(artifact).getAllByText("SIMULATED / LOCAL MOCK").length).toBeGreaterThan(0);
    expect(within(artifact).getByText(/Server ordinal 1: LOCAL_BOUNDARY_ENFORCED/)).toBeVisible();
    expect(within(artifact).getByRole("article", { name: ledgerEntryId })).toBeVisible();
    expect(within(artifact).getByText("0.50000000 / 0.15000000 / 0.20000000")).toBeVisible();
    const disclosure = artifact.querySelector("details.simulationArtifactDisclosure");
    expect(disclosure).not.toBeNull();
    expect(disclosure).not.toHaveAttribute("open");
    const persistedJson = disclosure?.querySelector("pre");
    expect(persistedJson?.nextElementSibling).toHaveClass("localEvidenceExport");
    expect(
      within(disclosure as HTMLElement).getByRole("button", {
        hidden: true,
        name: "Prepare evidence bundle",
      }),
    ).toBeInTheDocument();
    expect(within(artifact).getByRole("link", { name: "Trace source to artifact" })).toHaveAttribute(
      "href",
      `/lineage?assessment_id=${approvedAssessmentId}&simulation_run_id=${simulationRunId}`,
    );
    expect(container.querySelectorAll("form select")).toHaveLength(1);
    expect(container.querySelector("form input, form textarea")).toBeNull();
  });

  it("retries an unavailable POST with the exact same idempotency key", async () => {
    vi.mocked(useEvidenceIndex).mockReturnValue({
      data: {
        ...governanceIndex,
        assessments: [approvedAssessment],
        revocations: [],
      },
      reload,
      retrySafe: true,
      status: "success",
    });
    vi.mocked(fable5Api.createLocalSimulation)
      .mockResolvedValueOnce({
        error: {
          kind: "unavailable",
          message: "The API request timed out before deterministic evidence was available.",
          retrySafe: true,
        },
        ok: false,
      })
      .mockResolvedValueOnce({
        data: completedSimulation,
        ok: true,
        retrySafe: true,
        status: 201,
      });

    render(<PaperStatusWorkspace idempotencyKeyFactory={() => "phase10-ui-key"} />);
    fireEvent.change(screen.getByLabelText("Approval assessment"), {
      target: { value: approvedAssessmentId },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "Run deterministic local simulation" }),
    );
    fireEvent.click(await screen.findByRole("button", { name: "Retry exact simulation request" }));

    await screen.findByRole("article", { name: simulationRunId });
    expect(fable5Api.createLocalSimulation).toHaveBeenCalledTimes(2);
    const firstRequest = vi.mocked(fable5Api.createLocalSimulation).mock.calls[0]?.[0];
    const retryRequest = vi.mocked(fable5Api.createLocalSimulation).mock.calls[1]?.[0];
    expect(firstRequest).toEqual({
      approval_assessment_id: approvedAssessmentId,
      simulation_idempotency_key: "phase10-ui-key",
    });
    expect(retryRequest).toEqual(firstRequest);
  });

  it("renders a blocked artifact as dominant evidence with an explicit zero-entry ledger", async () => {
    vi.mocked(useEvidenceIndex).mockReturnValue({
      data: {
        ...governanceIndex,
        assessments: [approvedAssessment],
        revocations: [],
      },
      reload,
      retrySafe: true,
      status: "success",
    });
    vi.mocked(fable5Api.createLocalSimulation).mockResolvedValue({
      data: blockedSimulation,
      ok: true,
      retrySafe: true,
      status: 201,
    });

    render(
      <PaperStatusWorkspace idempotencyKeyFactory={() => "phase10-ui-blocked-key"} />,
    );
    fireEvent.change(screen.getByLabelText("Approval assessment"), {
      target: { value: approvedAssessmentId },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "Run deterministic local simulation" }),
    );

    const artifact = await screen.findByRole("article", {
      name: blockedSimulation.simulation_run_id,
    });
    expect(artifact).toHaveAttribute("data-blocking", "true");
    expect(
      within(artifact).getByText("BLOCKED - authoritative simulation checks did not pass"),
    ).toBeVisible();
    expect(within(artifact).getByText("BLOCKED - zero ledger entries")).toBeVisible();
    expect(within(artifact).queryByText(/SIMULATED ENTRY/)).not.toBeInTheDocument();
  });

  it("fails closed when a persisted summary conflicts with its detail artifact", async () => {
    vi.mocked(useEvidenceIndex).mockReturnValue({
      data: {
        ...governanceIndex,
        assessments: [approvedAssessment],
        revocations: [],
      },
      reload,
      retrySafe: true,
      status: "success",
    });
    vi.mocked(fable5Api.listLocalSimulations).mockResolvedValue({
      data: [{ ...summaryFor(completedSimulation), artifact_sha256: hash("9") }],
      ok: true,
      retrySafe: true,
      status: 200,
    });
    vi.mocked(fable5Api.getLocalSimulation).mockResolvedValue({
      data: completedSimulation,
      ok: true,
      retrySafe: true,
      status: 200,
    });

    render(<PaperStatusWorkspace />);

    const message = await screen.findByText(/persisted simulation detail conflicts/);
    const alert = message.closest("[role='alert']");
    expect(alert).not.toBeNull();
    expect(within(alert as HTMLElement).queryByRole("button")).not.toBeInTheDocument();
    expect(screen.queryByRole("article", { name: simulationRunId })).not.toBeInTheDocument();
  });
});
