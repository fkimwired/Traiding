import type { components } from "@fable5/contracts";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";

import { IdeaIntakeWorkspace } from "../app/ideas/IdeaIntakeWorkspace";
import { TradingIdeaCardView } from "../app/ideas/TradingIdeaCardView";
import { emptyEvidenceIndex, type EvidenceIndex } from "../lib/evidence-index";

type TradingIdeaCard = components["schemas"]["TradingIdeaCard"];
type MappingWithRationale = components["schemas"]["MappingWithRationale"];
type ResearchVerdict = components["schemas"]["ResearchVerdict"];
type SourceCreateResponse = components["schemas"]["SourceCreateResponse"];
type SourceAuthority = components["schemas"]["SourceAuthority"];

type Phase2Fixture = {
  expected_contribution: TradingIdeaCard["contribution_status"];
  expected_infra_risk: TradingIdeaCard["infra_risk"];
  expected_signal_family: NonNullable<TradingIdeaCard["signal_family"]["value"]>;
  expected_testability: TradingIdeaCard["testability_status"];
  fixture_id: string;
  raw_text: string;
  source_authority: SourceAuthority;
};

const phase2FixtureFiles = [
  "ranking.json",
  "trend.json",
  "social_news.json",
  "pairs.json",
  "order_flow.json",
  "unusual_options.json",
] as const;

const phase2Fixtures = phase2FixtureFiles.map((filename) =>
  JSON.parse(
    readFileSync(resolve(process.cwd(), "..", "extraction", "tests", "fixtures", filename), "utf8"),
  ) as Phase2Fixture,
);

const nonBuildVerdicts = [
  "DEFER",
  "DEFER_READ_ONLY",
  "REJECT_PLATFORM",
  "NON_TESTABLE",
] satisfies ResearchVerdict[];

const nonBuildReasonCode = {
  DEFER: "MISSING_CANONICAL_FAMILY",
  DEFER_READ_ONLY: "READ_ONLY_ANALYTICS_ONLY",
  NON_TESTABLE: "missing_action_rule",
  REJECT_PLATFORM: "PLATFORM_INFRASTRUCTURE_MISMATCH",
} satisfies Record<
  (typeof nonBuildVerdicts)[number],
  components["schemas"]["MappingReasonCode"]
>;

const sourceId = "10000000-0000-4000-8000-000000000001";
const sourceVersionId = "10000000-0000-4000-8000-000000000002";
const extractionId = "10000000-0000-4000-8000-000000000003";
const cardId = "10000000-0000-4000-8000-000000000004";
const mappingId = "10000000-0000-4000-8000-000000000005";
const sha = "a".repeat(64);

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
  extraction_config_sha256: sha,
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
      exact_text: "Rank a synthetic universe using lagged evidence.",
      kind: "claim",
      span: { end_byte: 48, segment_id: "segment-1", start_byte: 0, text_sha256: sha },
    },
  ],
  raw_text: "Rank a synthetic universe using lagged evidence.",
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

const mapping: MappingWithRationale = {
  mapping: {
    canonical_family: "A_CROSS_SECTIONAL_EQUITY_RANKING",
    card_id: cardId,
    card_sha256: sha,
    created_at_utc: "2026-07-14T12:00:01Z",
    extraction_config_sha256: sha,
    extraction_model_id: null,
    extraction_model_revision: null,
    extraction_prompt_sha256: null,
    extraction_prompt_version: null,
    extraction_request_fingerprint: sha,
    extraction_request_id: extractionId,
    extraction_schema_version: "phase2-trading-idea-card-v2",
    extractor_id: "fable5-deterministic-extractor",
    extractor_kind: "deterministic_mock",
    extractor_version: "1",
    mapper_rule_set_sha256: sha,
    mapper_rule_set_version: "phase3-canon-v1",
    mapping_id: mappingId,
    mapping_input_sha256: sha,
    mapping_version: 1,
    matched_rule_ids: ["P3-CANON-A"],
    official_corroboration_source_version_ids: [],
    rationale_template_version: "phase3-rationale-v1",
    reason_codes: ["CANON_A_RULE_MATCHED"],
    source_content_sha256: sha,
    source_evidence: [],
    source_id: sourceId,
    source_version: 1,
    source_version_id: sourceVersionId,
    verdict: "BUILD_RESEARCH",
  },
  rationale: {
    content_sha256: sha,
    created_at_utc: "2026-07-14T12:00:01Z",
    mapping_id: mappingId,
    markdown: "Build only an auditable research specification.",
    rationale_id: "10000000-0000-4000-8000-000000000006",
    template_version: "phase3-rationale-v1",
  },
};

const researchCodeSha = "b".repeat(40);
const phase5PolicyId = "15000000-0000-4000-8000-000000000001";

function evaluationReport(reportId: string): EvidenceIndex["evaluationReports"][number] {
  return {
    artifact_id: reportId,
    artifact_sha256: sha,
    code_version_git_sha: researchCodeSha,
    config_hash: sha,
    created_at_utc: "2026-07-14T12:00:00Z",
    data_snapshots: [],
    disclaimer: "Synthetic evaluation evidence only.",
    effective_trial_count: "1",
    evaluation_policy_id: phase5PolicyId,
    evaluation_policy_sha256: sha,
    evaluation_policy_version: 1,
    fixture_id: "phase6-a-pass-v2",
    fixture_sha256: sha,
    folds: [],
    gates: [],
    mapping_id: mappingId,
    mapping_input_sha256: sha,
    mapping_version: 1,
    metrics: [],
    promotion_state: "PASS_RESEARCH",
    random_seed: 7,
    raw_trial_count: 1,
    reason_codes: [],
    snapshot_bundle_sha256: sha,
    trials: [],
    warnings: [],
  } as unknown as EvidenceIndex["evaluationReports"][number];
}

function researchRun(
  runId: string,
  reportId: string | null = null,
  snapshotBindings: EvidenceIndex["researchRuns"][number]["snapshot_bindings"] = [],
): EvidenceIndex["researchRuns"][number] {
  return {
    artifact_sha256: sha,
    attempts: [],
    code_version_git_sha: researchCodeSha,
    configuration_id: "phase6-a-pass-v2",
    configuration_sha256: sha,
    created_at_utc: "2026-07-14T12:00:00Z",
    family: "A_CROSS_SECTIONAL_EQUITY_RANKING",
    mapping_id: mappingId,
    mapping_input_sha256: sha,
    mapping_version: 1,
    phase5_evaluation: {
      config_hash: sha,
      effective_trial_count: "1",
      evaluation_outcome_id: null,
      evaluation_report_id: reportId,
      evaluation_report_sha256: reportId ? sha : null,
      fixture_id: "phase6-a-pass-v2",
      fixture_sha256: sha,
      gate_codes: [],
      phase5_trial_set_sha256: reportId ? sha : null,
      policy_id: phase5PolicyId,
      policy_sha256: sha,
      policy_version: 1,
      promotion_state: "PASS_RESEARCH",
      raw_trial_count: 1,
      snapshot_bundle_sha256: sha,
    },
    random_seed: 7,
    reason_codes: [],
    run_id: runId,
    snapshot_bindings: snapshotBindings,
    snapshot_bundle_sha256: sha,
    status: "completed",
  } as unknown as EvidenceIndex["researchRuns"][number];
}

function assessmentLineage(
  run: EvidenceIndex["researchRuns"][number],
): EvidenceIndex["assessments"][number]["phase6_lineage"] {
  return {
    canonical_family: run.family,
    code_version_git_sha: run.code_version_git_sha,
    effective_trial_count: run.phase5_evaluation.effective_trial_count,
    evaluation_report_id: run.phase5_evaluation.evaluation_report_id,
    evaluation_report_sha256: run.phase5_evaluation.evaluation_report_sha256,
    gate_codes: run.phase5_evaluation.gate_codes,
    mapping_id: run.mapping_id,
    mapping_input_sha256: run.mapping_input_sha256,
    mapping_version: run.mapping_version,
    phase5_fixture_id: run.phase5_evaluation.fixture_id,
    phase5_fixture_sha256: run.phase5_evaluation.fixture_sha256,
    phase5_policy_id: run.phase5_evaluation.policy_id,
    phase5_policy_sha256: run.phase5_evaluation.policy_sha256,
    phase5_policy_version: run.phase5_evaluation.policy_version,
    phase5_trial_set_sha256: run.phase5_evaluation.phase5_trial_set_sha256,
    promotion_state: run.phase5_evaluation.promotion_state,
    random_seed: run.random_seed,
    raw_trial_count: run.phase5_evaluation.raw_trial_count,
    research_artifact_sha256: run.artifact_sha256,
    research_configuration_id: run.configuration_id,
    research_configuration_sha256: run.configuration_sha256,
    research_run_id: run.run_id,
    research_status: run.status,
    snapshot_bindings: run.snapshot_bindings,
    snapshot_bundle_sha256: run.snapshot_bundle_sha256,
  } as unknown as EvidenceIndex["assessments"][number]["phase6_lineage"];
}

const sourceResponse: SourceCreateResponse = {
  extraction: {
    extraction_config_sha256: sha,
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
    request_fingerprint: sha,
    requested_at_utc: "2026-07-14T12:00:00Z",
    rq_job_id: "job-1",
    source_version_id: sourceVersionId,
  },
  source: { created_at_utc: "2026-07-14T12:00:00Z", source_id: sourceId },
  source_version: {
    authority_verification_method: null,
    content_sha256: sha,
    content_state: "supplied_text",
    created_at_utc: "2026-07-14T12:00:00Z",
    official_corroboration_source_version_ids: [],
    parent_source_version_id: null,
    raw_text: "Rank a synthetic universe using lagged evidence.",
    retrieved_at_utc: null,
    source_authority: "unknown",
    source_id: sourceId,
    source_type: "manual_notes",
    source_url: null,
    source_version: 1,
    source_version_id: sourceVersionId,
    supplied_at_utc: "2026-07-14T12:00:00Z",
  },
};

function phase2ServerArtifacts(fixture: Phase2Fixture) {
  const normalizedClaim = `Server-returned normalized record for ${fixture.fixture_id}.`;
  const returnedCard: TradingIdeaCard = {
    ...card,
    contribution_status: fixture.expected_contribution,
    infra_risk: fixture.expected_infra_risk,
    paraphrased_claim: normalizedClaim,
    quoted_claims: card.quoted_claims.map((claim) => ({
      ...claim,
      exact_text: fixture.raw_text,
    })),
    raw_text: fixture.raw_text,
    signal_family: {
      ...card.signal_family,
      value: fixture.expected_signal_family,
    },
    source_authority: fixture.source_authority,
    synthetic_fixture: false,
    testability_status: fixture.expected_testability,
  };
  const returnedSource: SourceCreateResponse = {
    ...sourceResponse,
    source_version: {
      ...sourceResponse.source_version,
      raw_text: fixture.raw_text,
      source_authority: fixture.source_authority,
    },
  };

  return { normalizedClaim, returnedCard, returnedSource };
}

function jsonResponse(status: number, body: unknown) {
  return { json: async () => body, ok: status >= 200 && status < 300, status };
}

function isListPath(url: string) {
  return [
    "/v1/mappings",
    "/v1/data-snapshots",
    "/v1/evaluation-reports",
    "/v1/evaluation-outcomes",
    "/v1/research-runs",
    "/v1/approval-assessments",
    "/v1/approval-revocations",
  ].some((path) => url.includes(path));
}

async function submitManualIdea(
  user: ReturnType<typeof userEvent.setup>,
  rawText = "Rank a synthetic universe using lagged evidence.",
) {
  await user.type(screen.getByRole("textbox", { name: "Exact source text" }), rawText);
  await user.selectOptions(
    screen.getByRole("combobox", { name: "Source type" }),
    "manual_notes",
  );
  await user.selectOptions(
    screen.getByRole("combobox", { name: "Source authority" }),
    "unknown",
  );
  await user.click(screen.getByRole("button", { name: "Normalize idea" }));
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("Idea Intake workspace", () => {
  it("preserves exact text, uses generated API records, and renders the normalized card", async () => {
    let sourceCreated = false;
    const fetchMock = vi.fn().mockImplementation(async (input: string, init?: RequestInit) => {
      const url = String(input);
      if (url.includes("/v1/sources") && init?.method === "POST") {
        sourceCreated = true;
        return jsonResponse(201, sourceResponse);
      }
      if (url.includes(`/v1/cards/${cardId}/mappings`) && init?.method === "POST") {
        return jsonResponse(201, mapping);
      }
      if (url.includes("/v1/cards")) {
        return jsonResponse(200, sourceCreated ? [card] : []);
      }
      if (url.includes("/v1/mappings")) {
        return jsonResponse(200, sourceCreated ? [mapping] : []);
      }
      if (isListPath(url)) return jsonResponse(200, []);
      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    const { container } = render(
      <IdeaIntakeWorkspace idempotencyKeyFactory={() => "stable-key"} pollDelayMs={0} />,
    );
    await screen.findByText("No persisted Phase 2-7 evidence is available.");

    expect(
      within(screen.getByRole("combobox", { name: "Source type" })).queryByRole("option", {
        name: "synthetic fixture",
      }),
    ).not.toBeInTheDocument();

    const exactText = "Rank a synthetic universe using lagged evidence.";
    await user.type(screen.getByRole("textbox", { name: "Exact source text" }), exactText);
    await user.selectOptions(
      screen.getByRole("combobox", { name: "Source type" }),
      "manual_notes",
    );
    await user.selectOptions(
      screen.getByRole("combobox", { name: "Source authority" }),
      "unknown",
    );
    await user.click(screen.getByRole("button", { name: "Normalize idea" }));

    expect(await screen.findByText("A normalized, testable ranking claim.")).toBeVisible();
    expect(screen.getByText("BUILD_RESEARCH")).toBeVisible();
    expect(screen.getByText("Build only an auditable research specification.")).toBeVisible();
    expect(screen.getByText(/Missing governance evidence is not approval/)).toBeVisible();
    const normalizedCard = screen.getByRole("article", {
      name: "Cross Sectional Ranking Claim",
    });
    expect(within(normalizedCard).queryByText(exactText)).not.toBeInTheDocument();
    expect(
      within(normalizedCard).getByText("Exact non-synthetic text is referenced, not reproduced."),
    ).toBeVisible();
    expect(screen.getByRole("link", { name: "Open complete immutable lineage" })).toHaveAttribute(
      "href",
      `/lineage?card_id=${cardId}`,
    );
    expect(container.querySelector("[name='side'], [name='quantity']")).toBeNull();

    const sourceCall = fetchMock.mock.calls.find(
      ([input, init]) => String(input).includes("/v1/sources") && init?.method === "POST",
    );
    const request = JSON.parse(String(sourceCall?.[1]?.body));
    expect(request).toEqual({
      ingest_idempotency_key: "stable-key",
      raw_text: exactText,
      source_authority: "unknown",
      source_type: "manual_notes",
    });
  });

  it.each(phase2Fixtures)(
    "submits, extracts, normalizes, and exposes the persisted $fixture_id card",
    async (fixture) => {
      const { normalizedClaim, returnedCard, returnedSource } = phase2ServerArtifacts(fixture);
      let sourceCreated = false;
      const fetchMock = vi.fn().mockImplementation(async (input: string, init?: RequestInit) => {
        const url = String(input);
        if (url.includes("/v1/sources") && init?.method === "POST") {
          sourceCreated = true;
          return jsonResponse(201, returnedSource);
        }
        if (url.includes(`/v1/cards/${cardId}/mappings`) && init?.method === "POST") {
          // Mapping truth remains owned by the mapping service and its verifier. This constant,
          // generated-contract-shaped response only proves that the client renders server output.
          return jsonResponse(201, mapping);
        }
        if (url.includes("/v1/cards")) {
          return jsonResponse(200, sourceCreated ? [returnedCard] : []);
        }
        if (url.includes("/v1/mappings")) {
          return jsonResponse(200, sourceCreated ? [mapping] : []);
        }
        if (isListPath(url)) return jsonResponse(200, []);
        throw new Error(`Unexpected request: ${url}`);
      });
      vi.stubGlobal("fetch", fetchMock);
      const user = userEvent.setup();

      render(
        <IdeaIntakeWorkspace
          idempotencyKeyFactory={() => `intake-${fixture.fixture_id}`}
          pollDelayMs={0}
        />,
      );
      await screen.findByText("No persisted Phase 2-7 evidence is available.");

      const sourceInput = screen.getByRole("textbox", { name: "Exact source text" });
      await user.type(sourceInput, fixture.raw_text);
      await user.selectOptions(
        screen.getByRole("combobox", { name: "Source type" }),
        "manual_notes",
      );
      await user.selectOptions(
        screen.getByRole("combobox", { name: "Source authority" }),
        fixture.source_authority,
      );
      await user.click(screen.getByRole("button", { name: "Normalize idea" }));

      const normalized = await screen.findByText(normalizedClaim);
      const strategyCard = normalized.closest<HTMLElement>(".strategyCard");
      expect(strategyCard).not.toBeNull();
      expect(within(strategyCard!).getByText(fixture.expected_signal_family)).toBeVisible();
      expect(within(strategyCard!).getAllByText(fixture.expected_testability).length).toBeGreaterThan(
        0,
      );
      expect(
        within(strategyCard!).getByRole("heading", { name: "Build, defer, or reject rationale" }),
      ).toBeVisible();
      expect(
        within(strategyCard!).getByRole("link", { name: "Open complete immutable lineage" }),
      ).toHaveAttribute("href", `/lineage?card_id=${cardId}`);
      expect(within(strategyCard!).queryByText(fixture.raw_text)).not.toBeInTheDocument();
      expect(sourceInput).toHaveValue(fixture.raw_text);

      const sourceCall = fetchMock.mock.calls.find(
        ([input, init]) => String(input).includes("/v1/sources") && init?.method === "POST",
      );
      expect(JSON.parse(String(sourceCall?.[1]?.body))).toEqual({
        ingest_idempotency_key: `intake-${fixture.fixture_id}`,
        raw_text: fixture.raw_text,
        source_authority: fixture.source_authority,
        source_type: "manual_notes",
      });
      const mappingCall = fetchMock.mock.calls.find(
        ([input, init]) =>
          String(input).includes(`/v1/cards/${cardId}/mappings`) && init?.method === "POST",
      );
      expect(mappingCall?.[1]?.body).toBeUndefined();
    },
  );

  it.each([
    {
      label: "source identity",
      response: {
        ...sourceResponse,
        source: {
          ...sourceResponse.source,
          source_id: "11000000-0000-4000-8000-000000000001",
        },
      } satisfies SourceCreateResponse,
    },
    {
      label: "submitted text provenance",
      response: {
        ...sourceResponse,
        source_version: {
          ...sourceResponse.source_version,
          raw_text: "A different shape-valid source payload.",
        },
      } satisfies SourceCreateResponse,
    },
  ])("fails closed when source creation swaps $label", async ({ response }) => {
    const fetchMock = vi.fn().mockImplementation(async (input: string, init?: RequestInit) => {
      const url = String(input);
      if (url.includes("/v1/sources") && init?.method === "POST") {
        return jsonResponse(201, response);
      }
      if (url.includes("/v1/cards") || isListPath(url)) return jsonResponse(200, []);
      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(<IdeaIntakeWorkspace idempotencyKeyFactory={() => "source-conflict"} pollDelayMs={0} />);
    await screen.findByText("No persisted Phase 2-7 evidence is available.");
    await submitManualIdea(user);

    const alert = await screen.findByRole("alert");
    expect(within(alert).getByText("conflict")).toBeVisible();
    expect(within(alert).getByText(/returned source record conflicts/i)).toBeVisible();
    expect(within(alert).queryByRole("button", { name: "Retry exact request" })).toBeNull();
    expect(
      fetchMock.mock.calls.filter(
        ([input, init]) =>
          String(input).includes("/mappings") && init?.method === "POST",
      ),
    ).toHaveLength(0);
  });

  it("fails closed when extraction creation returns another source-version identity", async () => {
    const responseWithoutExtraction: SourceCreateResponse = {
      ...sourceResponse,
      extraction: null,
    };
    const swappedExtraction = {
      ...sourceResponse.extraction!,
      source_version_id: "12000000-0000-4000-8000-000000000001",
    };
    const fetchMock = vi.fn().mockImplementation(async (input: string, init?: RequestInit) => {
      const url = String(input);
      if (url.includes("/v1/sources") && init?.method === "POST") {
        return jsonResponse(201, responseWithoutExtraction);
      }
      if (url.includes(`/v1/source-versions/${sourceVersionId}/extractions`)) {
        return jsonResponse(202, swappedExtraction);
      }
      if (url.includes("/v1/cards") || isListPath(url)) return jsonResponse(200, []);
      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(
      <IdeaIntakeWorkspace idempotencyKeyFactory={() => "extraction-create-conflict"} pollDelayMs={0} />,
    );
    await screen.findByText("No persisted Phase 2-7 evidence is available.");
    await submitManualIdea(user);

    const alert = await screen.findByRole("alert");
    expect(within(alert).getByText("conflict")).toBeVisible();
    expect(within(alert).getByText(/returned extraction record conflicts/i)).toBeVisible();
    expect(
      fetchMock.mock.calls.filter(
        ([input, init]) =>
          String(input).includes("/mappings") && init?.method === "POST",
      ),
    ).toHaveLength(0);
  });

  it("fails closed when a polled extraction swaps immutable request provenance", async () => {
    const queuedResponse: SourceCreateResponse = {
      ...sourceResponse,
      extraction: { ...sourceResponse.extraction!, latest_event: "queued" },
    };
    const swappedExtraction = {
      ...sourceResponse.extraction!,
      latest_event: "succeeded" as const,
      request_fingerprint: "b".repeat(64),
    };
    const fetchMock = vi.fn().mockImplementation(async (input: string, init?: RequestInit) => {
      const url = String(input);
      if (url.includes("/v1/sources") && init?.method === "POST") {
        return jsonResponse(201, queuedResponse);
      }
      if (url.includes(`/v1/extractions/${extractionId}`)) {
        return jsonResponse(200, swappedExtraction);
      }
      if (url.includes("/v1/cards") || isListPath(url)) return jsonResponse(200, []);
      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(
      <IdeaIntakeWorkspace idempotencyKeyFactory={() => "extraction-poll-conflict"} pollDelayMs={0} />,
    );
    await screen.findByText("No persisted Phase 2-7 evidence is available.");
    await submitManualIdea(user);

    const alert = await screen.findByRole("alert");
    expect(within(alert).getByText("conflict")).toBeVisible();
    expect(within(alert).getByText(/returned extraction record conflicts/i)).toBeVisible();
    expect(
      fetchMock.mock.calls.filter(
        ([input, init]) =>
          String(input).includes("/mappings") && init?.method === "POST",
      ),
    ).toHaveLength(0);
  });

  it.each([
    {
      label: "source identity",
      response: {
        ...card,
        source_id: "13000000-0000-4000-8000-000000000001",
      } satisfies TradingIdeaCard,
    },
    {
      label: "extraction configuration",
      response: {
        ...card,
        extraction_config_sha256: "b".repeat(64),
      } satisfies TradingIdeaCard,
    },
  ])("fails closed when card lookup swaps $label lineage", async ({ response }) => {
    let sourceCreated = false;
    const fetchMock = vi.fn().mockImplementation(async (input: string, init?: RequestInit) => {
      const url = String(input);
      if (url.includes("/v1/sources") && init?.method === "POST") {
        sourceCreated = true;
        return jsonResponse(201, sourceResponse);
      }
      if (url.includes("/v1/cards")) {
        return jsonResponse(200, sourceCreated ? [response] : []);
      }
      if (isListPath(url)) return jsonResponse(200, []);
      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(<IdeaIntakeWorkspace idempotencyKeyFactory={() => "card-conflict"} pollDelayMs={0} />);
    await screen.findByText("No persisted Phase 2-7 evidence is available.");
    await submitManualIdea(user);

    const alert = await screen.findByRole("alert");
    expect(within(alert).getByText("conflict")).toBeVisible();
    expect(within(alert).getByText(/returned TradingIdeaCard conflicts/i)).toBeVisible();
    expect(
      fetchMock.mock.calls.filter(
        ([input, init]) =>
          String(input).includes("/mappings") && init?.method === "POST",
      ),
    ).toHaveLength(0);
  });

  it.each([
    {
      label: "card lineage",
      response: {
        ...mapping,
        mapping: {
          ...mapping.mapping,
          source_version_id: "14000000-0000-4000-8000-000000000001",
        },
      } satisfies MappingWithRationale,
    },
    {
      label: "extraction fingerprint",
      response: {
        ...mapping,
        mapping: {
          ...mapping.mapping,
          extraction_request_fingerprint: "b".repeat(64),
        },
      } satisfies MappingWithRationale,
    },
    {
      label: "source content hash",
      response: {
        ...mapping,
        mapping: {
          ...mapping.mapping,
          source_content_sha256: "c".repeat(64),
        },
      } satisfies MappingWithRationale,
    },
  ])("does not accept a mapping response with conflicting $label", async ({ response }) => {
    let sourceCreated = false;
    const fetchMock = vi.fn().mockImplementation(async (input: string, init?: RequestInit) => {
      const url = String(input);
      if (url.includes("/v1/sources") && init?.method === "POST") {
        sourceCreated = true;
        return jsonResponse(201, sourceResponse);
      }
      if (url.includes(`/v1/cards/${cardId}/mappings`) && init?.method === "POST") {
        return jsonResponse(201, response);
      }
      if (url.includes("/v1/cards")) {
        return jsonResponse(200, sourceCreated ? [card] : []);
      }
      if (isListPath(url)) return jsonResponse(200, []);
      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(<IdeaIntakeWorkspace idempotencyKeyFactory={() => "mapping-conflict"} pollDelayMs={0} />);
    await screen.findByText("No persisted Phase 2-7 evidence is available.");
    await submitManualIdea(user);

    const alert = await screen.findByRole("alert");
    expect(within(alert).getByText("conflict")).toBeVisible();
    expect(within(alert).getByText(/returned mapping record conflicts/i)).toBeVisible();
    expect(within(alert).queryByRole("button", { name: "Retry exact request" })).toBeNull();
    expect(screen.queryByText("Source preserved, extraction completed")).toBeNull();
    expect(
      fetchMock.mock.calls.filter(
        ([input, init]) =>
          String(input).includes(`/v1/cards/${cardId}/mappings`) && init?.method === "POST",
      ),
    ).toHaveLength(1);
  });

  it("makes a server-owned non-testable card visibly and structurally blocking", () => {
    const nonTestableCard: TradingIdeaCard = {
      ...card,
      testability_status: "non_testable",
    };

    const { container } = render(<TradingIdeaCardView card={nonTestableCard} />);
    const strategyCard = container.querySelector<HTMLElement>(".strategyCard");

    expect(strategyCard).toHaveAttribute("data-blocking", "true");
    expect(
      strategyCard?.querySelector(":scope > .cardHeader .statusBadge"),
    ).toHaveAttribute("data-tone", "critical");
    expect(
      within(strategyCard!).getByText("TradingIdeaCard is structurally non-testable"),
    ).toBeVisible();
    expect(
      within(strategyCard!).getByText(/No later positive metric can make this source claim eligible/),
    ).toBeVisible();
  });

  it("fails closed when a same-ID mapping conflicts with the card's embedded lineage", () => {
    const evidence = emptyEvidenceIndex();
    evidence.mappings.push({
      ...mapping,
      mapping: {
        ...mapping.mapping,
        source_version_id: "10000000-0000-4000-8000-000000000099",
      },
    });

    const { container } = render(<TradingIdeaCardView card={card} evidenceIndex={evidence} />);

    expect(container.querySelector(".strategyCard")).toHaveAttribute("data-blocking", "true");
    expect(screen.getByText("Exact mapping lineage conflict")).toBeVisible();
    expect(screen.getByText(/No mapping was substituted/)).toBeVisible();
    expect(screen.getByText(/No immutable mapping exists/)).toBeVisible();
    expect(screen.queryByRole("link", { name: "Trace mapping artifact" })).not.toBeInTheDocument();
  });

  it("links every conflicting blocked evaluation artifact without substituting it", () => {
    const evidence = emptyEvidenceIndex();
    const outcomeId = "10000000-0000-4000-8000-000000000007";
    const secondOutcomeId = "10000000-0000-4000-8000-000000000009";
    const snapshotId = "10000000-0000-4000-8000-000000000008";
    const secondSnapshotId = "10000000-0000-4000-8000-000000000010";
    evidence.mappings.push(mapping);
    const conflictingOutcome: EvidenceIndex["evaluationOutcomes"][number] = {
      artifact_type: "blocked_synthetic_research_evaluation",
      code_version_git_sha: researchCodeSha,
      created_at_utc: "2026-07-14T12:00:02Z",
      failure_stage: "snapshot_resolution",
      fixture_id: "phase5-reference-fixture",
      idempotency_sha256: sha,
      mapping_id: mappingId,
      no_real_performance_claimed: true,
      outcome_id: outcomeId,
      outcome_sha256: sha,
      policy_id: phase5PolicyId,
      policy_version: 1,
      promotion_state: "BLOCKED_UNCOMPUTABLE",
      reason_codes: ["required_snapshot_missing"],
      resolved_fixture_random_seed: 7,
      resolved_fixture_sha256: sha,
      resolved_policy_sha256: sha,
      resolved_raw_trial_count: 1,
      resolved_snapshots: [
        {
          mapping_id: mappingId,
          mapping_input_sha256: "f".repeat(64),
          mapping_version: mapping.mapping.mapping_version,
          snapshot_id: snapshotId,
          snapshot_sha256: sha,
        },
      ],
      sanitized_message: "Phase 5 evaluation stopped because required evidence was unavailable.",
      schema_version: "phase5-blocked-evaluation-outcome-v1",
      snapshot_ids: [snapshotId],
      status: "blocked",
      submission_sha256: sha,
      synthetic: true,
    };
    evidence.evaluationOutcomes.push(conflictingOutcome, {
      ...conflictingOutcome,
      outcome_id: secondOutcomeId,
      resolved_snapshots: [
        {
          ...conflictingOutcome.resolved_snapshots[0]!,
          snapshot_id: secondSnapshotId,
        },
      ],
      snapshot_ids: [secondSnapshotId],
    });

    const { container } = render(<TradingIdeaCardView card={card} evidenceIndex={evidence} />);
    const conflict = screen.getByText("Exact blocked-evaluation lineage conflict").parentElement;
    const link = within(conflict!).getByRole("link", {
      name: `Trace conflicting blocked evaluation artifact ${outcomeId}`,
    });

    expect(container.querySelector(".strategyCard")).toHaveAttribute("data-blocking", "true");
    expect(within(conflict!).getByText(/No outcome was substituted/)).toBeVisible();
    expect(link).toHaveAttribute("href", `/lineage?evaluation_outcome_id=${outcomeId}`);
    expect(
      within(conflict!).getByRole("link", {
        name: `Trace conflicting blocked evaluation artifact ${secondOutcomeId}`,
      }),
    ).toHaveAttribute(
      "href",
      `/lineage?evaluation_outcome_id=${secondOutcomeId}`,
    );
    expect(
      within(conflict!).getAllByRole("link", {
        name: /^Trace conflicting blocked evaluation artifact /,
      }),
    ).toHaveLength(2);
  });

  it.each(nonBuildVerdicts)(
    "makes the persisted %s mapping verdict dominate positive testability",
    (verdict) => {
      const evidence = emptyEvidenceIndex();
      evidence.mappings.push({
        mapping: {
          ...mapping.mapping,
          canonical_family: verdict === "NON_TESTABLE" ? null : mapping.mapping.canonical_family,
          reason_codes: [nonBuildReasonCode[verdict]],
          verdict,
        },
        rationale: {
          ...mapping.rationale,
          markdown: `Server-owned rationale for ${verdict}.`,
        },
      });

      const { container } = render(
        <TradingIdeaCardView card={card} evidenceIndex={evidence} />,
      );
      const strategyCard = container.querySelector<HTMLElement>(".strategyCard");
      const mappingHeading = screen.getByRole("heading", {
        name: "Build, defer, or reject rationale",
      });
      const mappingCard = mappingHeading.parentElement?.querySelector<HTMLElement>("article");

      expect(strategyCard).toHaveAttribute("data-blocking", "true");
      expect(
        strategyCard?.querySelector(":scope > .cardHeader .statusBadge"),
      ).toHaveAttribute("data-tone", "success");
      expect(mappingCard).toHaveAttribute("data-blocking", "true");
      expect(within(mappingCard!).getByText(verdict, { exact: true })).toHaveAttribute(
        "data-tone",
        "critical",
      );
      expect(within(mappingCard!).getByText("Phase 3 verdict is ineligible")).toBeVisible();
      expect(
        within(mappingCard!).getByText(
          `${verdict} is a persisted non-build outcome. It cannot be softened by testability or later positive metrics.`,
        ),
      ).toBeVisible();
    },
  );

  it("reuses the exact idempotent request when an unavailable response is retried", async () => {
    const sourceBodies: string[] = [];
    const fetchMock = vi.fn().mockImplementation(async (input: string, init?: RequestInit) => {
      const url = String(input);
      if (url.includes("/v1/sources") && init?.method === "POST") {
        sourceBodies.push(String(init.body));
        return jsonResponse(503, { detail: "not rendered" });
      }
      if (url.includes("/v1/cards") || isListPath(url)) return jsonResponse(200, []);
      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(<IdeaIntakeWorkspace idempotencyKeyFactory={() => "same-key"} pollDelayMs={0} />);
    await screen.findByText("No persisted Phase 2-7 evidence is available.");
    await user.type(screen.getByRole("textbox", { name: "Exact source text" }), "Exact retry text");
    await user.selectOptions(
      screen.getByRole("combobox", { name: "Source type" }),
      "manual_notes",
    );
    await user.selectOptions(
      screen.getByRole("combobox", { name: "Source authority" }),
      "unknown",
    );
    await user.click(screen.getByRole("button", { name: "Normalize idea" }));

    const alert = await screen.findByRole("alert");
    expect(within(alert).getByText("unavailable")).toBeVisible();
    await user.click(within(alert).getByRole("button", { name: "Retry exact request" }));
    await screen.findByRole("alert");

    expect(sourceBodies).toHaveLength(2);
    expect(sourceBodies[1]).toBe(sourceBodies[0]);
    expect(JSON.parse(sourceBodies[0]).ingest_idempotency_key).toBe("same-key");
  });

  it("lets a later authorization-linked revocation block an otherwise approved card", () => {
    const evidence = emptyEvidenceIndex();
    const runId = "20000000-0000-4000-8000-000000000001";
    const assessmentId = "30000000-0000-4000-8000-000000000001";
    const authorizationId = "40000000-0000-4000-8000-000000000001";
    const revocationId = "50000000-0000-4000-8000-000000000001";
    evidence.mappings.push(mapping);
    evidence.researchRuns.push(researchRun(runId));
    evidence.researchRunSummaries.push({
      artifact_sha256: sha,
      promotion_state: "PASS_RESEARCH",
      run_id: runId,
    } as unknown as EvidenceIndex["researchRunSummaries"][number]);
    evidence.assessments.push({
      assessment_id: assessmentId,
      authorization_sha256: sha,
      checks: [],
      created_at_utc: "2026-07-14T12:00:00Z",
      human_authorization_evidence_id: authorizationId,
      outcome: "APPROVED_PAPER",
      phase6_lineage: assessmentLineage(evidence.researchRuns[0]),
      reason_codes: [],
      research_run_id: runId,
      revocation_ids: [],
    } as unknown as EvidenceIndex["assessments"][number]);
    evidence.revocations.push({
      authorization_sha256: sha,
      effective_at_utc: "2026-07-14T13:00:00Z",
      human_authorization_evidence_id: authorizationId,
      revocation_id: revocationId,
    } as unknown as EvidenceIndex["revocations"][number]);

    const { container } = render(<TradingIdeaCardView card={card} evidenceIndex={evidence} />);

    expect(container.querySelector(".strategyCard")).toHaveAttribute("data-blocking", "true");
    expect(screen.getAllByText("Linked revocation evidence")).toHaveLength(2);
    const riskStatus = screen.getByRole("heading", { name: "Risk / Compliance status" })
      .parentElement;
    expect(riskStatus?.querySelector(".blockerBanner p")).toHaveTextContent(
      "0 ID(s) are bound in the assessment artifact; 1 additional append-only artifact(s)",
    );
    const paperStatus = screen.getByRole("heading", { name: "SIMULATED paper status" }).parentElement;
    expect(paperStatus?.querySelector("article[data-blocking='true']")).not.toBeNull();
    expect(screen.queryByText(/revoked after assessment/i)).not.toBeInTheDocument();
  });

  it("fails closed when an otherwise approved card has an unresolved bound revocation", () => {
    const evidence = emptyEvidenceIndex();
    const runId = "51000000-0000-4000-8000-000000000001";
    const reportId = "52000000-0000-4000-8000-000000000001";
    const assessmentId = "53000000-0000-4000-8000-000000000001";
    const missingRevocationId = "54000000-0000-4000-8000-000000000001";
    evidence.mappings.push(mapping);
    evidence.evaluationReports.push(evaluationReport(reportId));
    evidence.researchRuns.push(researchRun(runId, reportId));
    evidence.researchRunSummaries.push({
      artifact_sha256: sha,
      promotion_state: "PASS_RESEARCH",
      run_id: runId,
    } as unknown as EvidenceIndex["researchRunSummaries"][number]);
    evidence.assessments.push({
      assessment_id: assessmentId,
      authorization_sha256: sha,
      checks: [],
      created_at_utc: "2026-07-14T12:00:00Z",
      human_authorization_evidence_id: "55000000-0000-4000-8000-000000000001",
      outcome: "APPROVED_PAPER",
      phase6_lineage: assessmentLineage(evidence.researchRuns[0]),
      reason_codes: [],
      research_run_id: runId,
      revocation_ids: [missingRevocationId],
    } as unknown as EvidenceIndex["assessments"][number]);

    const { container } = render(<TradingIdeaCardView card={card} evidenceIndex={evidence} />);

    expect(container.querySelector(".strategyCard")).toHaveAttribute("data-blocking", "true");
    expect(screen.getAllByText("Unresolved bound revocation evidence")).toHaveLength(2);
    expect(screen.getAllByText(/1 assessment-bound revocation identifier/)).toHaveLength(2);
    expect(
      container.querySelector(
        `section[aria-labelledby='risk-${card.card_id}'] article[data-blocking='true']`,
      ),
    ).not.toBeNull();
    expect(
      container.querySelector(
        `section[aria-labelledby='paper-${card.card_id}'] article[data-blocking='true']`,
      ),
    ).not.toBeNull();
  });

  it("marks a rejected simulated-paper assessment blocking without revocation evidence", () => {
    const evidence = emptyEvidenceIndex();
    const runId = "60000000-0000-4000-8000-000000000001";
    evidence.mappings.push(mapping);
    evidence.researchRuns.push(researchRun(runId));
    evidence.assessments.push({
      assessment_id: "70000000-0000-4000-8000-000000000001",
      checks: [],
      created_at_utc: "2026-07-14T12:00:00Z",
      human_authorization_evidence_id: "80000000-0000-4000-8000-000000000001",
      outcome: "FAIL_REJECT",
      phase6_lineage: assessmentLineage(evidence.researchRuns[0]),
      reason_codes: ["policy_expired"],
      research_run_id: runId,
      revocation_ids: [],
    } as unknown as EvidenceIndex["assessments"][number]);

    render(<TradingIdeaCardView card={card} evidenceIndex={evidence} />);

    expect(screen.getByText("Simulated-paper status is ineligible")).toBeVisible();
    expect(
      screen.getAllByText("The server-owned assessment outcome is not APPROVED_PAPER."),
    ).toHaveLength(2);
  });

  it("fails closed when a research run's exact snapshot binding conflicts", () => {
    const evidence = emptyEvidenceIndex();
    const runId = "91000000-0000-4000-8000-000000000001";
    const reportId = "92000000-0000-4000-8000-000000000001";
    const snapshotId = "93000000-0000-4000-8000-000000000001";
    evidence.mappings.push(mapping);
    evidence.evaluationReports.push(evaluationReport(reportId));
    evidence.researchRuns.push(
      researchRun(runId, reportId, [
        {
          as_of_utc: "2026-07-14T00:00:00Z",
          binding_sha256: sha,
          capability: "ohlcv",
          mapping_id: mappingId,
          mapping_input_sha256: sha,
          ordinal: 1,
          quality_status: "data_quality_accepted",
          snapshot_id: snapshotId,
          snapshot_sha256: "b".repeat(64),
        },
      ]),
    );
    evidence.researchRunSummaries.push({
      artifact_sha256: sha,
      promotion_state: "PASS_RESEARCH",
      run_id: runId,
    } as unknown as EvidenceIndex["researchRunSummaries"][number]);
    evidence.snapshots.push({
      manifest: {
        payload: {
          mapping: {
            mapping_id: mappingId,
            mapping_input_sha256: sha,
            mapping_version: 1,
          },
        },
      },
      snapshot_id: snapshotId,
      snapshot_sha256: sha,
    } as unknown as EvidenceIndex["snapshots"][number]);

    const { container } = render(<TradingIdeaCardView card={card} evidenceIndex={evidence} />);

    expect(container.querySelector(".strategyCard")).toHaveAttribute("data-blocking", "true");
    expect(screen.getByText("Exact snapshot conflict")).toBeVisible();
    expect(screen.getByText(/No mapping-level snapshot was substituted/i)).toBeVisible();
  });

  it("keeps a timeline conflict blocking on the strategy card without recomputing status", () => {
    const evidence = emptyEvidenceIndex();
    const runId = "94000000-0000-4000-8000-000000000001";
    const reportId = "95000000-0000-4000-8000-000000000001";
    const assessmentId = "96000000-0000-4000-8000-000000000001";
    evidence.mappings.push(mapping);
    evidence.evaluationReports.push(evaluationReport(reportId));
    evidence.researchRuns.push(researchRun(runId, reportId));
    evidence.researchRunSummaries.push({
      artifact_sha256: sha,
      promotion_state: "PASS_RESEARCH",
      run_id: runId,
    } as unknown as EvidenceIndex["researchRunSummaries"][number]);
    evidence.assessments.push({
      assessment_id: assessmentId,
      checks: [],
      created_at_utc: "2026-07-14T12:00:00Z",
      human_authorization_evidence_id: "97000000-0000-4000-8000-000000000001",
      outcome: "APPROVED_PAPER",
      phase6_lineage: assessmentLineage(evidence.researchRuns[0]),
      reason_codes: ["all_approval_and_risk_checks_passed"],
      research_run_id: runId,
      revocation_ids: [],
    } as unknown as EvidenceIndex["assessments"][number]);
    evidence.assessmentTimelineFailures[assessmentId] = {
      kind: "conflict",
      message: "The request conflicts with immutable persisted evidence.",
      retrySafe: true,
      status: 409,
    };

    const { container } = render(<TradingIdeaCardView card={card} evidenceIndex={evidence} />);

    expect(container.querySelector(".strategyCard")).toHaveAttribute("data-blocking", "true");
    expect(screen.getAllByText("Historical timeline evidence was not resolved")).toHaveLength(2);
    expect(screen.getAllByText(/No date or governance state was inferred/)).toHaveLength(1);
    expect(screen.getByText(/No date, currentness, expiry, revocation, or readiness/)).toBeVisible();
  });
});
