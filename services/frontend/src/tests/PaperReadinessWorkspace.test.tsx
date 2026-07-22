import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { PaperReadinessWorkspace } from "../app/paper/readiness/PaperReadinessWorkspace";
import {
  blockedPaperReadinessFixture,
  PAPER_READINESS_ASSESSMENT_ID,
  PAPER_READINESS_CHECK_CODES,
  paperReadinessArtifact,
  paperReadinessFixture,
} from "./paper-readiness-fixture";

const RESPONSE_CANARY = "CANARY_KEY_9f3";
const MISMATCHED_ASSESSMENT_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";

const fetchMock = vi.fn<typeof fetch>();

function response(status: number, body: unknown): Response {
  return {
    json: vi.fn().mockResolvedValue(body),
    ok: status >= 200 && status < 300,
    status,
  } as unknown as Response;
}

function malformedResponse(): Response {
  return {
    json: vi.fn().mockRejectedValue(new SyntaxError(`invalid ${RESPONSE_CANARY}`)),
    ok: true,
    status: 200,
  } as unknown as Response;
}

function setAssessmentId(value: string) {
  fireEvent.change(screen.getByRole("textbox", { name: "Readiness assessment ID" }), {
    target: { value },
  });
}

function submitAssessment() {
  fireEvent.click(screen.getByRole("button", { name: "Load readiness evidence" }));
}

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
  vi.spyOn(Date, "now").mockReturnValue(Date.parse("2026-07-22T12:00:00Z"));
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("paper shadow-readiness workspace", () => {
  it("stays read-only on mount and input changes and exposes no authority control", () => {
    const { container } = render(<PaperReadinessWorkspace />);

    expect(screen.getByText("Simulated / Paper Only / No Advice")).toBeVisible();
    expect(fetchMock).not.toHaveBeenCalled();

    const assessmentInput = screen.getByRole("textbox", {
      name: "Readiness assessment ID",
    });
    fireEvent.change(assessmentInput, {
      target: { value: PAPER_READINESS_ASSESSMENT_ID },
    });
    expect(assessmentInput).toHaveValue(PAPER_READINESS_ASSESSMENT_ID);
    expect(fetchMock).not.toHaveBeenCalled();

    expect(container.querySelectorAll("input")).toHaveLength(1);
    expect(assessmentInput).toHaveAttribute("type", "text");
    expect(
      container.querySelector(
        "input[type='password'], input[name*='credential' i], input[name*='secret' i], " +
          "input[name*='key' i], input[name*='token' i]",
      ),
    ).toBeNull();
    expect(container.querySelector("form[action]")).toBeNull();
    expect(screen.getAllByRole("button")).toHaveLength(1);
    expect(
      screen.queryByRole("button", {
        name: /capture|credential|mutate|order|position|quote|retry|refresh/i,
      }),
    ).not.toBeInTheDocument();
  });

  it("performs exactly one generated-contract GET per explicit submit and renders the mock proof", async () => {
    fetchMock.mockImplementation(async () => response(200, paperReadinessFixture));
    render(<PaperReadinessWorkspace />);

    const uppercaseAssessmentId = PAPER_READINESS_ASSESSMENT_ID.toUpperCase();
    setAssessmentId(uppercaseAssessmentId);
    expect(fetchMock).not.toHaveBeenCalled();
    submitAssessment();

    expect(
      await screen.findByRole("heading", {
        name: `Assessment ${PAPER_READINESS_ASSESSMENT_ID}`,
      }),
    ).toBeVisible();
    expect(fetchMock).toHaveBeenCalledTimes(1);

    const [url, options] = fetchMock.mock.calls[0] ?? [];
    expect(String(url)).toBe(
      `http://localhost:8000/v1/paper-shadow-readiness/${uppercaseAssessmentId}`,
    );
    expect(options).toMatchObject({
      credentials: "omit",
      headers: { Accept: "application/json" },
      method: "GET",
    });
    expect(options?.body).toBeUndefined();

    expect(screen.getByText("MOCK — local contract proof only")).toBeVisible();
    expect(screen.getByText("EXPIRED — historical evidence only")).toBeVisible();
    expect(screen.getByText("MOCK_PROOF_COMPLETE")).toBeVisible();
    expect(screen.getByRole("heading", { name: "OPEN" })).toBeVisible();
    const quoteObservation = screen
      .getByRole("heading", { name: "AAPL / iex" })
      .closest("section");
    expect(quoteObservation).not.toBeNull();
    const quote = within(quoteObservation as HTMLElement);
    expect(quote.getByText("Fresh").parentElement).toHaveTextContent("Freshtrue");
    expect(quote.getByText("1.0 / 60")).toBeVisible();
    expect(screen.getByText("order_submission_authorized = false")).toBeVisible();
    expect(screen.getByText("strategy_execution_eligible = false")).toBeVisible();
    expect(screen.getByText("live_path_absent = true")).toBeVisible();
    expect(
      screen.getByText("no_personalized_investment_advice = true"),
    ).toBeVisible();
    expect(screen.getByText("no_real_performance_claimed = true")).toBeVisible();

    const checks = screen.getByTestId("readiness-checks");
    const checkItems = Array.from(checks.children);
    expect(checkItems).toHaveLength(8);
    expect(
      checkItems.map((item) => item.querySelector("strong")?.textContent),
    ).toEqual(PAPER_READINESS_CHECK_CODES);
    expect(
      checkItems.map((item) => item.getAttribute("data-tone")),
    ).toEqual(Array.from({ length: 8 }, () => "pass"));

    expect(fetchMock).toHaveBeenCalledTimes(1);
    submitAssessment();
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    expect(fetchMock.mock.calls.map((call) => call[1]?.method)).toEqual(["GET", "GET"]);
  });

  it("captures expiry state once at the response and never auto-flips on a later rerender", async () => {
    vi.mocked(Date.now).mockReturnValue(Date.parse("2024-01-02T15:00:30Z"));
    fetchMock.mockResolvedValue(response(200, paperReadinessFixture));
    render(<PaperReadinessWorkspace />);
    setAssessmentId(PAPER_READINESS_ASSESSMENT_ID);

    submitAssessment();

    expect(
      await screen.findByText("EXPIRY TIMESTAMP — no execution authority"),
    ).toBeVisible();
    expect(
      screen.queryByText("EXPIRED — historical evidence only"),
    ).not.toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(1);

    vi.mocked(Date.now).mockReturnValue(Date.parse("2024-01-02T15:02:00Z"));
    setAssessmentId(`${PAPER_READINESS_ASSESSMENT_ID} `);

    expect(screen.getByText("EXPIRY TIMESTAMP — no execution authority")).toBeVisible();
    expect(
      screen.queryByText("EXPIRED — historical evidence only"),
    ).not.toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("renders a local typed 422 for an empty identifier without fetching", () => {
    render(<PaperReadinessWorkspace />);

    submitAssessment();

    expect(screen.getByRole("alert")).toHaveTextContent("Validation (422)");
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Enter a canonical assessment UUID before loading evidence.",
    );
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it.each([
    [404, "Not found (404)"],
    [409, "Conflict (409)"],
    [422, "Validation (422)"],
  ] as const)(
    "renders the fixed typed HTTP %s state once without echoing response prose",
    async (status, title) => {
      fetchMock.mockResolvedValue(
        response(status, { detail: `provider failure ${RESPONSE_CANARY}` }),
      );
      render(<PaperReadinessWorkspace />);
      setAssessmentId(PAPER_READINESS_ASSESSMENT_ID);

      submitAssessment();

      const alert = await screen.findByRole("alert");
      expect(alert).toHaveTextContent(title);
      expect(alert).not.toHaveTextContent(RESPONSE_CANARY);
      expect(document.body).not.toHaveTextContent(RESPONSE_CANARY);
      expect(fetchMock).toHaveBeenCalledTimes(1);
      expect(screen.queryByRole("button", { name: /retry/i })).not.toBeInTheDocument();
    },
  );

  it.each([
    ["malformed JSON", () => malformedResponse()],
    [
      "a schema-extra canary",
      () =>
        response(200, {
          ...paperReadinessFixture,
          credential_material: RESPONSE_CANARY,
        }),
    ],
  ] as const)("rejects %s with one fixed non-echoing error", async (_case, factory) => {
    fetchMock.mockResolvedValue(factory());
    render(<PaperReadinessWorkspace />);
    setAssessmentId(PAPER_READINESS_ASSESSMENT_ID);

    submitAssessment();

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Malformed response");
    expect(alert).not.toHaveTextContent(RESPONSE_CANARY);
    expect(document.body).not.toHaveTextContent(RESPONSE_CANARY);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(screen.queryByText("MOCK_PROOF_COMPLETE")).not.toBeInTheDocument();
  });

  it("fails closed when a shape-valid response carries a different assessment ID", async () => {
    fetchMock.mockResolvedValue(
      response(
        200,
        paperReadinessArtifact({
          readiness_assessment_id: MISMATCHED_ASSESSMENT_ID,
        }),
      ),
    );
    render(<PaperReadinessWorkspace />);
    setAssessmentId(PAPER_READINESS_ASSESSMENT_ID);

    submitAssessment();

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Conflict (409)");
    expect(alert).toHaveTextContent(
      "The returned readiness identifier conflicts with the requested evidence.",
    );
    expect(document.body).not.toHaveTextContent(MISMATCHED_ASSESSMENT_ID);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("renders BLOCKED reason codes verbatim and makes the blocker an alert", async () => {
    fetchMock.mockResolvedValue(response(200, blockedPaperReadinessFixture));
    render(<PaperReadinessWorkspace />);
    setAssessmentId(PAPER_READINESS_ASSESSMENT_ID);

    submitAssessment();

    await screen.findByRole("heading", {
      name: `Assessment ${PAPER_READINESS_ASSESSMENT_ID}`,
    });
    const blocker = screen.getByRole("alert");
    expect(blocker).toHaveTextContent("Readiness is blocked");
    expect(within(blocker).getAllByRole("listitem").map((item) => item.textContent)).toEqual([
      "market_clock_closed_verbatim",
      "quote_freshness_blocked_verbatim",
    ]);
    expect(screen.getAllByText("BLOCKED").length).toBeGreaterThan(0);
    expect(screen.getAllByText("market_clock_closed_verbatim")).toHaveLength(2);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("renders null clock and quote evidence explicitly as NOT OBSERVED", async () => {
    fetchMock.mockResolvedValue(
      response(
        200,
        paperReadinessArtifact({
          clock: null,
          latest_quote: null,
        }),
      ),
    );
    render(<PaperReadinessWorkspace />);
    setAssessmentId(PAPER_READINESS_ASSESSMENT_ID);

    submitAssessment();

    await screen.findByRole("heading", {
      name: `Assessment ${PAPER_READINESS_ASSESSMENT_ID}`,
    });
    expect(screen.getAllByRole("heading", { name: "NOT OBSERVED" })).toHaveLength(2);
    expect(screen.getByText("No clock observation was retained.")).toBeVisible();
    expect(screen.getByText("No quote observation was retained.")).toBeVisible();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
