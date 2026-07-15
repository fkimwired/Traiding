import type { components } from "@fable5/contracts";
import { render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { SourceEvidence } from "../app/lineage/LineageExplorer";

type TradingIdeaCard = components["schemas"]["TradingIdeaCard"];
type Extraction = components["schemas"]["ExtractionRequestRecord"];
type Mapping = components["schemas"]["MappingWithRationale"];
type SourceVersion = components["schemas"]["SourceVersion"];

const sourceId = "10000000-0000-4000-8000-000000000001";
const sourceVersionId = "10000000-0000-4000-8000-000000000002";
const extractionId = "10000000-0000-4000-8000-000000000003";
const cardId = "10000000-0000-4000-8000-000000000004";
const cardHash = "a".repeat(64);
const sourceHash = "b".repeat(64);
const extractionHash = "c".repeat(64);
const restrictedSourceText = "Rank a licensed universe using lagged evidence.";

const card: TradingIdeaCard = {
  action_rule: { claim_ids: ["claim-1"], state: "source_supported" },
  ambiguity_flags: [],
  asset_class: { claim_ids: ["claim-1"], state: "source_supported", value: "equity" },
  card_id: cardId,
  contribution_status: "not_blocked_by_corroboration",
  corroboration_status: "not_required",
  created_at_utc: "2026-07-14T12:00:00Z",
  execution_style: {
    claim_ids: ["claim-1"],
    state: "source_supported",
    value: "periodic_research_claim",
  },
  extraction_config_sha256: cardHash,
  extraction_model_id: null,
  extraction_model_revision: null,
  extraction_prompt_sha256: null,
  extraction_prompt_version: null,
  extraction_request_id: extractionId,
  extraction_schema_version: "phase2-trading-idea-card-v2",
  extractor_id: "fable5-deterministic-extractor",
  extractor_kind: "deterministic_mock",
  extractor_version: "1",
  forecast_horizon: {
    claim_ids: ["claim-1"],
    state: "source_supported",
    value: "multi_day",
  },
  infra_risk: "low",
  official_corroboration_source_ids: [],
  official_corroboration_source_version_ids: [],
  paraphrased_claim: "A normalized, testable ranking claim.",
  quoted_claims: [
    {
      claim_id: "claim-1",
      exact_text: restrictedSourceText,
      kind: "claim",
      span: { end_byte: 47, segment_id: "segment-1", start_byte: 0, text_sha256: cardHash },
    },
  ],
  raw_text: restrictedSourceText,
  required_data: { claim_ids: ["claim-1"], state: "source_supported", values: ["ohlcv"] },
  research_priority_score: null,
  risk_assumptions: {
    claim_ids: ["claim-1"],
    state: "source_supported",
    values: ["liquidity"],
  },
  signal_family: {
    claim_ids: ["claim-1"],
    state: "source_supported",
    value: "cross_sectional_ranking_claim",
  },
  source_authority: "unknown",
  source_id: sourceId,
  source_url: null,
  source_version: 1,
  source_version_id: sourceVersionId,
  synthetic_fixture: false,
  testability_reason_codes: [],
  testability_score: 1,
  testability_score_method: "phase2-testability-v1",
  testability_status: "testable",
};

const sourceVersion: SourceVersion = {
  authority_verification_method: null,
  content_sha256: sourceHash,
  content_state: "supplied_text",
  created_at_utc: "2026-07-14T12:00:00Z",
  official_corroboration_source_version_ids: [],
  parent_source_version_id: null,
  raw_text: restrictedSourceText,
  retrieved_at_utc: null,
  source_authority: "unknown",
  source_id: sourceId,
  source_type: "pasted_caption",
  source_url: null,
  source_version: 1,
  source_version_id: sourceVersionId,
  supplied_at_utc: "2026-07-14T12:00:00Z",
};

const extraction: Extraction = {
  extraction_config_sha256: cardHash,
  extraction_model_id: null,
  extraction_model_revision: null,
  extraction_prompt_sha256: null,
  extraction_prompt_version: null,
  extraction_request_id: extractionId,
  extraction_schema_version: "phase2-trading-idea-card-v2",
  extractor_id: "fable5-deterministic-extractor",
  extractor_kind: "deterministic_mock",
  extractor_version: "1",
  latest_event: "succeeded",
  request_fingerprint: extractionHash,
  requested_at_utc: "2026-07-14T12:00:00Z",
  rq_job_id: "synthetic-job-1",
  source_version_id: sourceVersionId,
};

const mapping = {
  mapping: {
    extraction_request_fingerprint: extractionHash,
    source_content_sha256: sourceHash,
  },
} as Mapping;

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("lineage source evidence degradation", () => {
  it.each(["source", "extraction"] as const)(
    "keeps the immutable normalized card visible while %s evidence is unavailable",
    async (failedRequest) => {
      vi.stubGlobal(
        "fetch",
        vi.fn(async (input: string | URL | Request) => {
          const url = String(input);
          const isFailedRequest =
            failedRequest === "source"
              ? url.includes("/v1/source-versions/")
              : url.includes("/v1/extractions/");

          if (isFailedRequest) {
            return { ok: false, status: 503 };
          }

          const artifact = url.includes("/v1/source-versions/") ? sourceVersion : extraction;
          return { ok: true, status: 200, json: async () => artifact };
        }),
      );

      render(
        <ol>
          <SourceEvidence card={card} />
        </ol>,
      );

      expect(screen.getAllByRole("status")).toHaveLength(2);
      expect(screen.getAllByRole("status")[0]).toHaveTextContent(
        "Loading source and extraction evidence",
      );
      const normalizedCard = screen.getByText("Normalized TradingIdeaCard").closest("li");
      expect(normalizedCard).not.toBeNull();
      expect(within(normalizedCard!).getByText(`Card ID: ${cardId}`)).toBeVisible();
      expect(within(normalizedCard!).getByText(cardHash)).toBeVisible();
      expect(
        within(normalizedCard!).getByText("Inspect complete normalized card artifact"),
      ).toBeVisible();

      expect(await screen.findByRole("alert")).toHaveTextContent(
        "lineage stops at the last retrievable immutable identifier",
      );
      expect(within(normalizedCard!).getByText(`Card ID: ${cardId}`)).toBeVisible();

      const successfulSibling = screen
        .getByText(failedRequest === "source" ? "Extraction" : "Source input", { exact: true })
        .closest("li");
      expect(successfulSibling).not.toBeNull();
      if (failedRequest === "source") {
        expect(within(successfulSibling!).getByText(`Request ID: ${extractionId}`)).toBeVisible();
        expect(within(successfulSibling!).getByText(extractionHash)).toBeVisible();
        const extractionArtifact = within(successfulSibling!).getByText(
          "Inspect complete extraction record",
        ).parentElement;
        expect(extractionArtifact).not.toBeNull();
        expect(
          within(extractionArtifact!).getByText(
            new RegExp(`"extraction_request_id": "${extractionId}"`),
          ),
        ).toBeInTheDocument();
      } else {
        expect(
          within(successfulSibling!).getByText(`Source version ID: ${sourceVersionId}`),
        ).toBeVisible();
        expect(within(successfulSibling!).getByText(sourceHash)).toBeVisible();
        const sourceArtifact = within(successfulSibling!).getByText(
          "Inspect complete source version artifact",
        ).parentElement;
        expect(sourceArtifact).not.toBeNull();
        expect(
          within(sourceArtifact!).getByText(
            new RegExp(`"source_version_id": "${sourceVersionId}"`),
          ),
        ).toBeInTheDocument();
        expect(within(sourceArtifact!).getByText(/referenced by content SHA-256/)).toBeInTheDocument();
        expect(
          within(sourceArtifact!).queryByText(new RegExp(restrictedSourceText)),
        ).not.toBeInTheDocument();
      }

      const artifact = within(normalizedCard!).getByText(
        "Inspect complete normalized card artifact",
      ).parentElement;
      expect(artifact).not.toBeNull();
      expect(within(artifact!).getByText(new RegExp(`"card_id": "${cardId}"`))).toBeInTheDocument();
      expect(within(artifact!).getByText(/referenced by source span and SHA-256/)).toBeInTheDocument();
      expect(within(artifact!).getByText(/referenced by content SHA-256/)).toBeInTheDocument();
      expect(within(artifact!).queryByText(new RegExp(restrictedSourceText))).not.toBeInTheDocument();
    },
  );

  it.each([
    {
      conflictingArtifact: {
        ...sourceVersion,
        source_version_id: "10000000-0000-4000-8000-000000000099",
      },
      failedRequest: "source",
      label: "shape-valid wrong source-version ID",
      message: "returned source version conflicts",
    },
    {
      conflictingArtifact: {
        ...extraction,
        extraction_config_sha256: "d".repeat(64),
      },
      failedRequest: "extraction",
      label: "shape-valid wrong extraction configuration hash",
      message: "returned extraction record conflicts",
    },
  ] as const)("fails closed on a $label without rendering it", async (testCase) => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: string | URL | Request) => {
        const url = String(input);
        if (url.includes("/v1/source-versions/")) {
          return {
            json: async () =>
              testCase.failedRequest === "source"
                ? testCase.conflictingArtifact
                : sourceVersion,
            ok: true,
            status: 200,
          };
        }
        return {
          json: async () =>
            testCase.failedRequest === "extraction"
              ? testCase.conflictingArtifact
              : extraction,
          ok: true,
          status: 200,
        };
      }),
    );

    render(
      <ol>
        <SourceEvidence card={card} />
      </ol>,
    );

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(testCase.message);
    expect(alert).toHaveTextContent("no substitute was inferred");
    expect(
      screen.queryByText(testCase.failedRequest === "source" ? "Source input" : "Extraction", {
        exact: true,
      }),
    ).not.toBeInTheDocument();
    expect(screen.getByText("Normalized TradingIdeaCard")).toBeVisible();
  });

  it.each([
    {
      failedRequest: "source",
      label: "source URL",
      returnedSource: { ...sourceVersion, source_url: "https://example.invalid/conflict" },
    },
    {
      failedRequest: "source",
      label: "raw source text",
      returnedSource: { ...sourceVersion, raw_text: "Conflicting source text." },
    },
    {
      failedRequest: "source",
      label: "ordered corroboration identities",
      returnedSource: {
        ...sourceVersion,
        official_corroboration_source_version_ids: [
          "90000000-0000-4000-8000-000000000001",
        ],
      },
    },
    {
      failedRequest: "source",
      label: "synthetic source classification",
      returnedSource: { ...sourceVersion, source_type: "synthetic_fixture" as const },
    },
    {
      failedRequest: "source",
      label: "mapping-owned source content hash",
      returnedMapping: {
        mapping: { ...mapping.mapping, source_content_sha256: "d".repeat(64) },
      } as Mapping,
    },
    {
      failedRequest: "extraction",
      label: "mapping-owned extraction fingerprint",
      returnedMapping: {
        mapping: { ...mapping.mapping, extraction_request_fingerprint: "e".repeat(64) },
      } as Mapping,
    },
  ] as const)("fails closed on conflicting $label lineage", async (testCase) => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: string | URL | Request) => {
        const url = String(input);
        return {
          json: async () =>
            url.includes("/v1/source-versions/")
              ? (testCase.returnedSource ?? sourceVersion)
              : extraction,
          ok: true,
          status: 200,
        };
      }),
    );

    render(
      <ol>
        <SourceEvidence card={card} mapping={testCase.returnedMapping ?? mapping} />
      </ol>,
    );

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(
      testCase.failedRequest === "source"
        ? "returned source version conflicts"
        : "returned extraction record conflicts",
    );
    expect(alert).toHaveTextContent("no substitute was inferred");
  });

});
