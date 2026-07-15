import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { PaperStatusWorkspace } from "../app/paper/PaperStatusWorkspace";
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

afterEach(() => {
  cleanup();
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

    expect(container.querySelector("form, input, select, textarea, button")).toBeNull();
    expect(container.textContent).not.toMatch(
      /\b(buy|sell|quantity|side|position|fill|broker)\b|order ticket/i,
    );
  });

  it("announces deterministic loading, empty, and retry-safe failure states", () => {
    vi.mocked(useEvidenceIndex).mockReturnValue({
      message: "Loading immutable evidence...",
      reload,
      retrySafe: true,
      status: "loading",
    });
    const loading = render(<PaperStatusWorkspace />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading immutable evidence");
    loading.unmount();

    vi.mocked(useEvidenceIndex).mockReturnValue({
      message: "No persisted Phase 2-7 evidence is available.",
      reload,
      retrySafe: true,
      status: "empty",
    });
    const empty = render(<PaperStatusWorkspace />);
    expect(screen.getByRole("status")).toHaveTextContent(
      "No persisted Phase 2-7 evidence is available.",
    );
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
    expect(failed.container.querySelector("form, input, select, textarea")).toBeNull();
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
});
