import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useSearchParams } from "next/navigation";
import { afterEach, describe, expect, it, vi } from "vitest";

import { LineageExplorer } from "../app/lineage/LineageExplorer";
import { useEvidenceIndex } from "../lib/evidence-index";
import {
  approvedAssessment,
  approvedAssessmentId,
  governanceIndex,
} from "./governance-fixtures";

vi.mock("next/navigation", () => ({ useSearchParams: vi.fn() }));
vi.mock("../lib/evidence-index", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/evidence-index")>();
  return { ...actual, useEvidenceIndex: vi.fn() };
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("lineage timeline failure evidence", () => {
  it("shows a timeline conflict beside the complete immutable assessment artifact", () => {
    vi.mocked(useSearchParams).mockReturnValue(
      new URLSearchParams(`assessment_id=${approvedAssessmentId}`) as ReturnType<
        typeof useSearchParams
      >,
    );
    vi.mocked(useEvidenceIndex).mockReturnValue({
      data: {
        ...governanceIndex,
        assessments: [approvedAssessment],
        assessmentTimelineFailures: {
          [approvedAssessmentId]: {
            kind: "conflict",
            message: "The request conflicts with immutable persisted evidence.",
            retrySafe: true,
            status: 409,
          },
        },
        assessmentTimelines: {},
        revocations: [],
      },
      reload: vi.fn(),
      retrySafe: true,
      status: "success",
    });

    render(<LineageExplorer />);

    const assessmentEvidence = screen
      .getByText("Approval assessment and historical evidence timeline")
      .closest("li");
    expect(assessmentEvidence).not.toBeNull();
    const evidence = within(assessmentEvidence!);
    expect(evidence.getByText(`Assessment ID: ${approvedAssessmentId}`)).toBeVisible();
    expect(evidence.getByText(approvedAssessment.artifact_sha256)).toBeVisible();
    const auditDisclosure = evidence
      .getByText(/complete immutable domain audit artifact/)
      .closest("details");
    expect(auditDisclosure).not.toBeNull();
    expect(auditDisclosure?.querySelector("pre")).toHaveAttribute("tabindex", "0");
    const timelineAlert = evidence.getByRole("alert");
    expect(timelineAlert).toHaveTextContent("Historical timeline evidence was not resolved");
    expect(timelineAlert).toHaveTextContent(
      "The request conflicts with immutable persisted evidence.",
    );
    expect(timelineAlert).toHaveTextContent("conflict (HTTP 409)");
  });

  it("restores focus to lineage retry after another retry-safe failure", async () => {
    const reload = vi.fn();
    const user = userEvent.setup();
    vi.mocked(useSearchParams).mockReturnValue(
      new URLSearchParams() as ReturnType<typeof useSearchParams>,
    );
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
    const view = render(<LineageExplorer />);
    const retry = screen.getByRole("button", { name: "Retry evidence load" });
    retry.focus();

    await user.keyboard("{Enter}");
    expect(reload).toHaveBeenCalledOnce();

    vi.mocked(useEvidenceIndex).mockReturnValue({
      message: "Loading immutable evidence...",
      reload,
      retrySafe: true,
      status: "loading",
    });
    view.rerender(<LineageExplorer />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading immutable evidence");

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
    view.rerender(<LineageExplorer />);

    const restoredRetry = screen.getByRole("button", { name: "Retry evidence load" });
    await waitFor(() => expect(restoredRetry).toHaveFocus());
  });
});
