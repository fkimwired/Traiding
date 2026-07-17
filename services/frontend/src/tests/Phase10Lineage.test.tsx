import type { components } from "@fable5/contracts";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { useSearchParams } from "next/navigation";
import { afterEach, describe, expect, it, vi } from "vitest";

import { LineageExplorer } from "../app/lineage/LineageExplorer";
import { fable5Api } from "../lib/api";
import { type EvidenceIndex, useEvidenceIndex } from "../lib/evidence-index";
import { approvedAssessment, approvedAssessmentId, governanceIndex } from "./governance-fixtures";

vi.mock("next/navigation", () => ({ useSearchParams: vi.fn() }));
vi.mock("../lib/evidence-index", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/evidence-index")>();
  return { ...actual, useEvidenceIndex: vi.fn() };
});
vi.mock("../lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/api")>();
  return {
    ...actual,
    fable5Api: { ...actual.fable5Api, getLocalSimulation: vi.fn() },
  };
});

const simulationRunId = "90000000-0000-4000-8000-000000000010";
const researchArtifactSha256 = "a".repeat(64);
const lineageSha256 = "b".repeat(64);
const simulationArtifactSha256 = "c".repeat(64);

const assessment = {
  ...approvedAssessment,
  phase6_lineage: {
    ...approvedAssessment.phase6_lineage,
    lineage_sha256: lineageSha256,
    research_artifact_sha256: researchArtifactSha256,
    research_run_id: approvedAssessment.research_run_id,
  },
} as EvidenceIndex["assessments"][number];

const artifact = {
  artifact_sha256: simulationArtifactSha256,
  checks: [
    {
      check_sha256: "d".repeat(64),
      code: "SOURCE_APPROVAL_EXACT",
      ordinal: 1,
      status: "PASS",
    },
  ],
  configuration: {
    research_artifact_sha256: researchArtifactSha256,
    research_run_id: assessment.research_run_id,
  },
  ledger_entries: [{ ledger_entry_id: "91000000-0000-4000-8000-000000000010" }],
  outcome: "SIMULATED_COMPLETE",
  phase6_lineage_sha256: lineageSha256,
  research_artifact_sha256: researchArtifactSha256,
  research_run_id: assessment.research_run_id,
  simulation_run_id: simulationRunId,
  source_assessment_artifact_sha256: assessment.artifact_sha256,
  source_assessment_id: approvedAssessmentId,
  transition_assessment_id: "92000000-0000-4000-8000-000000000010",
} as components["schemas"]["PaperSimulationArtifact"];

function mockEvidence() {
  vi.mocked(useEvidenceIndex).mockReturnValue({
    data: {
      ...governanceIndex,
      assessments: [assessment],
      assessmentTimelineFailures: {},
      assessmentTimelines: {},
      cards: [],
      evaluationOutcomes: [],
      evaluationReports: [],
      mappings: [],
      researchRunSummaries: [],
      researchRuns: [],
      revocations: [],
      snapshots: [],
    },
    reload: vi.fn(),
    retrySafe: true,
    status: "success",
  });
}

function mockParameters() {
  vi.mocked(useSearchParams).mockReturnValue(
    new URLSearchParams(
      `assessment_id=${approvedAssessmentId}&simulation_run_id=${simulationRunId}`,
    ) as ReturnType<typeof useSearchParams>,
  );
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("Phase 10 simulation lineage terminal", () => {
  it("fetches and renders the exact source-bound simulation artifact", async () => {
    mockEvidence();
    mockParameters();
    vi.mocked(fable5Api.getLocalSimulation).mockResolvedValue({
      data: artifact,
      ok: true,
      retrySafe: true,
      status: 200,
    });

    render(<LineageExplorer />);

    expect(
      await screen.findByText("Deterministic local mock paper simulation terminal"),
    ).toBeVisible();
    expect(vi.mocked(fable5Api.getLocalSimulation).mock.calls[0]?.[0]).toBe(simulationRunId);
    expect(screen.getByText("SIMULATED_COMPLETE")).toBeVisible();
    expect(screen.getByText(`Simulation run ID: ${simulationRunId}`)).toBeVisible();
    expect(screen.getByText(simulationArtifactSha256)).toBeVisible();
    expect(screen.getByText(/No external routing. No live path./)).toBeVisible();
    expect(screen.getByText(/Server ordinal 1: SOURCE_APPROVAL_EXACT/)).toBeVisible();
  });

  it("fails closed when the simulation does not bind the selected assessment artifact", async () => {
    mockEvidence();
    mockParameters();
    vi.mocked(fable5Api.getLocalSimulation).mockResolvedValue({
      data: {
        ...artifact,
        source_assessment_artifact_sha256: "f".repeat(64),
      },
      ok: true,
      retrySafe: true,
      status: 200,
    });

    render(<LineageExplorer />);

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(
      "The returned Phase 10 simulation conflicts with the exact source assessment lineage.",
    );
    expect(alert).toHaveTextContent("No simulation terminal or substitute artifact was inferred.");
    await waitFor(() =>
      expect(
        screen.queryByText("Deterministic local mock paper simulation terminal"),
      ).not.toBeInTheDocument(),
    );
  });
});
