import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { RiskComplianceWorkspace } from "../app/risk/RiskComplianceWorkspace";
import { fable5Api } from "../lib/api";
import { useEvidenceIndex } from "../lib/evidence-index";
import {
  approvedAssessment,
  approvedAssessmentId,
  approvedAuthorizationId,
  approvedResearchRunId,
  governanceIndex,
  policyId,
  rejectedAssessmentId,
  revocationEvidenceId,
  revocationId,
  riskInputId,
  scopeId,
} from "./governance-fixtures";

vi.mock("../lib/evidence-index", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/evidence-index")>();
  return { ...actual, useEvidenceIndex: vi.fn() };
});

const reload = vi.fn();

beforeEach(() => {
  vi.mocked(useEvidenceIndex).mockReturnValue({
    data: governanceIndex,
    reload,
    retrySafe: true,
    status: "success",
  });
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  reload.mockReset();
});

describe("risk and compliance workspace", () => {
  it("puts blockers first and preserves complete ordered checks, timelines, hashes, and links", () => {
    const { container } = render(<RiskComplianceWorkspace />);

    expect(screen.getByRole("heading", { name: "Risk / Compliance" })).toBeVisible();
    const articles = screen.getAllByRole("article");
    expect(articles[0]).toHaveAccessibleName(rejectedAssessmentId);
    expect(articles[1]).toHaveAccessibleName(approvedAssessmentId);

    const rejected = within(articles[0]);
    expect(rejected.getByText("Blocking evidence first")).toBeVisible();
    expect(rejected.getByText(/stored outcome remains FAIL_REJECT/)).toBeVisible();
    expect(rejected.getByText(/RESEARCH_PASS: FAIL/)).toBeVisible();
    expect(rejected.getByText(/POLICY_CURRENT: BLOCKED/)).toBeVisible();
    expect(rejected.getByText("Review 2026-07-15T00:00:00Z")).toBeVisible();
    expect(rejected.getByText("c".repeat(64))).toBeVisible();

    const orderedCodes = Array.from(articles[0].querySelectorAll(".checkList > li strong")).map(
      (node) => node.textContent,
    );
    expect(orderedCodes).toEqual([
      "Server ordinal 1: RESEARCH_PASS",
      "Server ordinal 2: POLICY_CURRENT",
      "Server ordinal 3: REVOCATION_CLEAR",
    ]);

    expect(screen.getByRole("article", { name: revocationId })).toBeVisible();
    expect(screen.getAllByRole("link", { name: "Trace source to artifact" })).toHaveLength(3);
    expect(
      rejected.getByRole("link", { name: "Trace source to artifact" }),
    ).toHaveAttribute("href", `/lineage?assessment_id=${rejectedAssessmentId}`);

    const inputNames = Array.from(container.querySelectorAll("input"))
      .map((input) => input.name)
      .sort();
    expect(inputNames).toEqual(
      [
        "approval_policy_version_id",
        "approval_scope_version_id",
        "human_authorization_evidence_id",
        "human_authorization_evidence_id",
        "research_run_id",
        "revocation_evidence_id",
        "risk_input_id",
      ].sort(),
    );
    expect(inputNames.join(" ")).not.toMatch(
      /timestamp|hash|threshold|verdict|currentness|risk_result|outcome|status/,
    );
    expect(
      Array.from(container.querySelectorAll("input")).every(
        (input) => !input.hasAttribute("pattern"),
      ),
    ).toBe(true);
  });

  it("sends an assessment create containing generated-contract reference IDs only", async () => {
    const create = vi.spyOn(fable5Api, "createApprovalAssessment").mockResolvedValue({
      data: approvedAssessment,
      ok: true,
      retrySafe: true,
      status: 201,
    });
    const user = userEvent.setup();
    render(<RiskComplianceWorkspace />);

    const panel = screen
      .getByRole("heading", { name: "Create assessment artifact" })
      .closest("section");
    expect(panel).not.toBeNull();
    const form = within(panel as HTMLElement);
    await user.type(form.getByLabelText("Research run ID"), approvedResearchRunId);
    await user.type(form.getByLabelText("Approval policy version ID"), policyId);
    await user.type(form.getByLabelText("Approval scope version ID"), scopeId);
    await user.type(form.getByLabelText("Human authorization evidence ID"), approvedAuthorizationId);
    await user.type(form.getByLabelText("Risk input ID"), riskInputId);
    await user.click(form.getByRole("button", { name: "Create from references" }));

    expect(create).toHaveBeenCalledWith({
      approval_policy_version_id: policyId,
      approval_scope_version_id: scopeId,
      human_authorization_evidence_id: approvedAuthorizationId,
      research_run_id: approvedResearchRunId,
      risk_input_id: riskInputId,
    });
    expect(
      await form.findByText("Immutable assessment artifact returned by the server."),
    ).toBeVisible();
    expect(form.getByText(`ID: ${approvedAssessmentId}`)).toBeVisible();
    expect(reload).not.toHaveBeenCalled();
    await user.click(form.getByRole("button", { name: "Refresh immutable index" }));
    expect(reload).toHaveBeenCalledOnce();
  });

  it.each([
    ["validation", "Validation blocked", false],
    ["conflict", "Immutable evidence conflict", true],
    ["unavailable", "Governance API unavailable", true],
  ] as const)(
    "announces %s revocation-create failures without inventing a result",
    async (kind, heading, retrySafe) => {
      vi.spyOn(fable5Api, "createApprovalRevocation").mockResolvedValue({
        error: {
          kind,
          message: `Deterministic ${kind} response.`,
          retrySafe,
          status: kind === "validation" ? 422 : kind === "conflict" ? 409 : 503,
        },
        ok: false,
      });
      const user = userEvent.setup();
      render(<RiskComplianceWorkspace />);

      const panel = screen
        .getByRole("heading", { name: "Create revocation artifact" })
        .closest("section");
      expect(panel).not.toBeNull();
      const form = within(panel as HTMLElement);
      await user.type(form.getByLabelText("Human authorization evidence ID"), approvedAuthorizationId);
      await user.type(form.getByLabelText("Revocation evidence ID"), revocationEvidenceId);
      await user.click(form.getByRole("button", { name: "Create from references" }));

      const alert = await form.findByRole("alert");
      expect(alert).toHaveTextContent(heading);
      expect(alert).toHaveTextContent(`Deterministic ${kind} response.`);
      expect(alert).not.toHaveTextContent("Artifact SHA-256");
      expect(reload).not.toHaveBeenCalled();
    },
  );

  it("renders a timeline 409 as blocking without discarding the complete assessment", () => {
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
      reload,
      retrySafe: true,
      status: "success",
    });

    render(<RiskComplianceWorkspace />);

    const assessment = screen.getByRole("article", { name: approvedAssessmentId });
    expect(assessment).toHaveAttribute("data-blocking", "true");
    expect(assessment.querySelector(":scope > .cardHeader .statusBadge")).toHaveAttribute(
      "data-tone",
      "critical",
    );
    expect(within(assessment).getAllByText("APPROVED_PAPER").length).toBeGreaterThan(0);
    expect(within(assessment).getByText(approvedAssessment.artifact_sha256)).toBeVisible();
    const timelineAlert = within(assessment).getByRole("alert");
    expect(timelineAlert).toHaveTextContent("Historical timeline evidence was not resolved");
    expect(timelineAlert).toHaveTextContent(
      "The request conflicts with immutable persisted evidence.",
    );
    expect(timelineAlert).toHaveTextContent("conflict (HTTP 409)");
    expect(within(assessment).getByText(/1 unresolved historical timeline/)).toBeVisible();
  });

  it("announces loading, empty, and unavailable read states", () => {
    vi.mocked(useEvidenceIndex).mockReturnValue({
      message: "Loading immutable evidence...",
      reload,
      retrySafe: true,
      status: "loading",
    });
    const loading = render(<RiskComplianceWorkspace />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading immutable evidence");
    loading.unmount();

    vi.mocked(useEvidenceIndex).mockReturnValue({
      message: "No persisted Phase 2-7 evidence is available.",
      reload,
      retrySafe: true,
      status: "empty",
    });
    const empty = render(<RiskComplianceWorkspace />);
    expect(screen.getByRole("status")).toHaveTextContent("No persisted Phase 2-7 evidence");
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
    render(<RiskComplianceWorkspace />);
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Governance evidence could not be loaded",
    );
  });
});
