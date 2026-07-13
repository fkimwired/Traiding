import { render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { IdeaMappings } from "../app/ideas/IdeaMappings";

const mappingResponse = [
  {
    mapping: {
      mapping_id: "30000000-0000-0000-0000-000000000001",
      mapping_version: 1,
      card_id: "30000000-0000-0000-0000-000000000002",
      extraction_request_id: "30000000-0000-0000-0000-000000000003",
      source_id: "30000000-0000-0000-0000-000000000004",
      source_version_id: "30000000-0000-0000-0000-000000000005",
      canonical_family: "official_event_text_overlay",
      verdict: "DEFER",
      matched_rule_ids: ["CANON_C", "RULE_03_SOCIAL_BLOCKED"],
      reason_codes: ["FIRST_REASON", "OFFICIAL_CORROBORATION_REQUIRED", "THIRD_REASON"],
      mapper_rule_set_version: "phase3-canon-v1",
      mapper_rule_set_sha256: "a".repeat(64),
      created_at_utc: "2026-07-13T12:00:00Z",
    },
    rationale: {
      rationale_id: "30000000-0000-0000-0000-000000000006",
      mapping_id: "30000000-0000-0000-0000-000000000001",
      template_version: "phase3-rationale-v1",
      markdown: "**Deterministic rationale**\n<strong>render as text</strong>",
      content_sha256: "b".repeat(64),
      created_at_utc: "2026-07-13T12:00:00Z",
    },
  },
];

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("deterministic idea mappings", () => {
  it("shows rationale, ordered evidence, lineage, and the research-only boundary", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mappingResponse,
    });
    vi.stubGlobal("fetch", fetchMock);

    const { container } = render(<IdeaMappings />);

    expect(screen.getByRole("status")).toHaveTextContent("Loading deterministic mappings");
    expect(await screen.findByText("official_event_text_overlay")).toBeVisible();
    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8000/v1/mappings", {
      signal: expect.any(AbortSignal),
    });

    const reasons = within(screen.getByLabelText("Ordered reason codes"))
      .getAllByRole("listitem")
      .map((item) => item.textContent);
    expect(reasons).toEqual([
      "FIRST_REASON",
      "OFFICIAL_CORROBORATION_REQUIRED",
      "THIRD_REASON",
    ]);
    expect(within(screen.getByLabelText("Matched rule IDs")).getAllByRole("listitem")).toHaveLength(
      2,
    );

    expect(screen.getByText(/\*\*Deterministic rationale\*\*/)).toBeVisible();
    expect(screen.getByText(/<strong>render as text<\/strong>/)).toBeVisible();
    expect(container.querySelector(".mappingRationale strong")).toBeNull();

    expect(screen.getByRole("link", { name: "Source" })).toHaveAttribute(
      "href",
      "http://localhost:8000/v1/sources/30000000-0000-0000-0000-000000000004",
    );
    expect(screen.getByRole("link", { name: "Source version" })).toHaveAttribute(
      "href",
      "http://localhost:8000/v1/source-versions/30000000-0000-0000-0000-000000000005",
    );
    expect(screen.getByRole("link", { name: "Card" })).toHaveAttribute(
      "href",
      "http://localhost:8000/v1/cards/30000000-0000-0000-0000-000000000002",
    );
    expect(screen.getByRole("link", { name: "Extraction" })).toHaveAttribute(
      "href",
      "http://localhost:8000/v1/extractions/30000000-0000-0000-0000-000000000003",
    );

    const boundary = screen.getByText("BUILD_RESEARCH").closest("p");
    expect(boundary).toHaveTextContent(
      "BUILD_RESEARCH authorizes only a later research specification",
    );
    expect(boundary).toHaveTextContent("does not indicate profitability");
    expect(boundary).toHaveTextContent("position sizing");
    expect(boundary).toHaveTextContent("paper-trading eligibility");
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
    expect(container.querySelector("form")).toBeNull();
  });

  it("renders empty and error states without adding actions", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: true, json: async () => [] })
      .mockResolvedValueOnce({ ok: false });
    vi.stubGlobal("fetch", fetchMock);

    const empty = render(<IdeaMappings />);
    expect(await screen.findByText("No deterministic mappings are available yet.")).toBeVisible();
    empty.unmount();

    render(<IdeaMappings />);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Deterministic mappings could not be loaded",
    );
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});
