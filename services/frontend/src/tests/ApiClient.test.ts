import type { components } from "@fable5/contracts";
import { afterEach, describe, expect, it, vi } from "vitest";

import { API_REQUEST_TIMEOUT_MS, fable5Api } from "../lib/api";

function response(status: number, body: unknown = {}) {
  return {
    json: async () => body,
    ok: status >= 200 && status < 300,
    status,
  };
}

function pendingAbortableFetch() {
  return vi.fn((_input: RequestInfo | URL, init?: RequestInit) =>
    new Promise((_resolve, reject) => {
      const rejectAbort = () => {
        const error = new Error("request aborted");
        error.name = "AbortError";
        reject(error);
      };
      if (init?.signal?.aborted) {
        rejectAbort();
      } else {
        init?.signal?.addEventListener("abort", rejectAbort, { once: true });
      }
    }),
  );
}

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("generated-contract API client failure states", () => {
  it.each([
    [409, "conflict", true],
    [422, "validation", false],
    [503, "unavailable", true],
    [404, "not-found", true],
  ] as const)("classifies HTTP %s as %s", async (status, kind, retrySafe) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(status)));

    const result = await fable5Api.createSource({
      ingest_idempotency_key: "stable-intake-key",
      raw_text: "Exact source text.",
      source_authority: "unknown",
      source_type: "manual_notes",
    });

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error).toMatchObject({ kind, retrySafe, status });
    }
  });

  it("classifies transport and malformed payload failures without trusting response prose", async () => {
    const fetchMock = vi
      .fn()
      .mockRejectedValueOnce(new Error("network secret"))
      .mockResolvedValueOnce({
        json: async () => {
          throw new SyntaxError("bad json");
        },
        ok: true,
        status: 200,
      })
      .mockResolvedValueOnce(response(200, { not: "an array" }));
    vi.stubGlobal("fetch", fetchMock);

    const network = await fable5Api.listCards();
    const malformedJson = await fable5Api.listCards();
    const malformedShape = await fable5Api.listCards();

    expect(network).toMatchObject({ ok: false, error: { kind: "unavailable" } });
    expect(malformedJson).toMatchObject({ ok: false, error: { kind: "malformed" } });
    expect(malformedShape).toMatchObject({ ok: false, error: { kind: "malformed" } });
  });

  it("turns the internal request deadline into a retry-safe unavailable state", async () => {
    vi.useFakeTimers();
    vi.stubGlobal("fetch", pendingAbortableFetch());

    const pending = fable5Api.listCards();
    await vi.advanceTimersByTimeAsync(API_REQUEST_TIMEOUT_MS);
    const result = await pending;

    expect(result).toEqual({
      error: {
        kind: "unavailable",
        message: "The API request timed out before deterministic evidence was available.",
        retrySafe: true,
      },
      ok: false,
    });
    expect(vi.getTimerCount()).toBe(0);
  });

  it("preserves an explicit caller cancellation as aborted instead of unavailable", async () => {
    vi.useFakeTimers();
    vi.stubGlobal("fetch", pendingAbortableFetch());
    const controller = new AbortController();

    const pending = fable5Api.listCards(controller.signal);
    controller.abort();
    const result = await pending;

    expect(result).toEqual({
      error: {
        kind: "aborted",
        message: "The request was cancelled.",
        retrySafe: true,
      },
      ok: false,
    });
    expect(vi.getTimerCount()).toBe(0);
  });

  it("rejects malformed collection members, detail artifacts, and evidence timelines", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(response(200, [{}]))
      .mockResolvedValueOnce(response(200, { card_id: "not-a-complete-card" }))
      .mockResolvedValueOnce(
        response(200, {
          assessment_id: "10000000-0000-4000-8000-000000000001",
          policy: {},
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    const malformedMember = await fable5Api.listCards();
    const malformedDetail = await fable5Api.getCard(
      "10000000-0000-4000-8000-000000000002",
    );
    const malformedTimeline = await fable5Api.getApprovalAssessmentEvidenceTimeline(
      "10000000-0000-4000-8000-000000000003",
    );

    expect(malformedMember).toMatchObject({ ok: false, error: { kind: "malformed" } });
    expect(malformedDetail).toMatchObject({ ok: false, error: { kind: "malformed" } });
    expect(malformedTimeline).toMatchObject({ ok: false, error: { kind: "malformed" } });
  });

  it("accepts valid generated timestamps and rejects impossible date-times", async () => {
    const assessmentId = "10000000-0000-4000-8000-000000000001";
    const policyId = "20000000-0000-4000-8000-000000000001";
    const scopeId = "30000000-0000-4000-8000-000000000001";
    const authorizationId = "40000000-0000-4000-8000-000000000001";
    const riskInputId = "50000000-0000-4000-8000-000000000001";
    const sha = "a".repeat(64);
    const timeline = {
      assessment_created_at_utc: "2026-07-14T12:00:00Z",
      assessment_id: assessmentId,
      authorization: {
        authorization_sha256: sha,
        authorized_at_utc: "2026-07-14T11:00:00Z",
        expires_at_utc: "2026-07-15T12:00:00Z",
        human_authorization_evidence_id: authorizationId,
        review_at_utc: "2026-07-15T00:00:00Z",
      },
      policy: {
        approval_policy_version_id: policyId,
        expires_at_utc: "2026-07-21T12:00:00Z",
        policy_sha256: sha,
        valid_from_utc: "2026-07-07T12:00:00Z",
      },
      risk_input: {
        observed_at_utc: "2026-07-14T11:55:00Z",
        risk_input_id: riskInputId,
        risk_input_sha256: sha,
      },
      scope: {
        approval_scope_version_id: scopeId,
        expires_at_utc: "2026-07-16T12:00:00Z",
        scope_sha256: sha,
        valid_from_utc: "2026-07-12T12:00:00Z",
      },
    } satisfies components["schemas"]["ApprovalAssessmentEvidenceTimeline"];
    const fetchMock = vi.fn().mockResolvedValue(response(200, timeline));
    vi.stubGlobal("fetch", fetchMock);

    const result = await fable5Api.getApprovalAssessmentEvidenceTimeline(assessmentId);

    expect(result).toEqual({ data: timeline, ok: true, retrySafe: true, status: 200 });
    expect(fetchMock.mock.calls[0]?.[0]).toBe(
      `http://localhost:8000/v1/approval-assessments/${assessmentId}/evidence-timeline`,
    );

    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        response(200, {
          ...timeline,
          assessment_created_at_utc: "2026-02-30T25:61:61+24:00",
        }),
      ),
    );
    const impossibleTimestamp = await fable5Api.getApprovalAssessmentEvidenceTimeline(
      assessmentId,
    );
    expect(impossibleTimestamp).toMatchObject({
      error: { kind: "malformed" },
      ok: false,
    });
  });
});
