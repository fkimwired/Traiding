import { afterEach, describe, expect, it, vi } from "vitest";

import {
  emptyEvidenceIndex,
  evidenceForCard,
  evaluationEvidenceForResearchRun,
  evaluationReportMatchesResearchRun,
  loadEvidenceIndex,
  mappingMatchesCard,
  snapshotMatchesEvaluationReportEvidence,
  snapshotsForResearchRun,
  type EvidenceIndex,
} from "../lib/evidence-index";
import { fable5Api, type ApiResult } from "../lib/api";
import {
  approvedAssessment,
  approvedAssessmentId,
  governanceIndex,
  rejectedAssessment,
  rejectedAssessmentId,
  revocation,
} from "./governance-fixtures";

function success<T>(data: T): ApiResult<T> {
  return { data, ok: true, retrySafe: true, status: 200 };
}

function mockEmptyEvidenceReads() {
  vi.spyOn(fable5Api, "listCards").mockResolvedValue(success([]));
  vi.spyOn(fable5Api, "listMappings").mockResolvedValue(success([]));
  vi.spyOn(fable5Api, "listSnapshots").mockResolvedValue(success([]));
  vi.spyOn(fable5Api, "listEvaluationReports").mockResolvedValue(success([]));
  vi.spyOn(fable5Api, "listEvaluationOutcomes").mockResolvedValue(success([]));
  vi.spyOn(fable5Api, "listResearchRuns").mockResolvedValue(success([]));
  const listAssessments = vi
    .spyOn(fable5Api, "listApprovalAssessments")
    .mockResolvedValue(success([]));
  const listRevocations = vi
    .spyOn(fable5Api, "listApprovalRevocations")
    .mockResolvedValue(success([]));
  return { listAssessments, listRevocations };
}

function assessmentSummary(assessment: EvidenceIndex["assessments"][number]) {
  return {
    artifact_sha256: assessment.artifact_sha256,
    assessment_id: assessment.assessment_id,
    created_at_utc: assessment.created_at_utc,
    execution_authorized: false as const,
    execution_ready: false as const,
    no_personalized_investment_advice: true as const,
    no_real_performance_claimed: true as const,
    outcome: assessment.outcome,
    reason_codes: assessment.reason_codes,
    research_configuration_id: "phase6-a-pass-v2",
    research_run_id: assessment.research_run_id,
    simulated_paper_only: true as const,
    synthetic: true as const,
  };
}

function revocationSummary(item: EvidenceIndex["revocations"][number]) {
  return {
    artifact_sha256: item.artifact_sha256,
    created_at_utc: item.created_at_utc,
    effective_at_utc: item.effective_at_utc,
    execution_authorized: false as const,
    execution_ready: false as const,
    human_authorization_evidence_id: item.human_authorization_evidence_id,
    revocation_evidence_id: item.revocation_evidence_id,
    revocation_id: item.revocation_id,
    simulated_paper_only: true as const,
    synthetic: true as const,
  };
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("immutable evidence index", () => {
  it("hydrates one generated evidence timeline for every assessment summary", async () => {
    const assessments = [approvedAssessment, rejectedAssessment];
    const assessmentIds = [approvedAssessmentId, rejectedAssessmentId];
    const assessmentTimelines: EvidenceIndex["assessmentTimelines"] =
      governanceIndex.assessmentTimelines;
    const { listAssessments } = mockEmptyEvidenceReads();
    listAssessments.mockResolvedValue(success(assessments.map(assessmentSummary)));
    vi.spyOn(fable5Api, "getApprovalAssessment").mockImplementation(async (assessmentId) =>
      success(assessments.find((assessment) => assessment.assessment_id === assessmentId)!),
    );
    const timeline = vi
      .spyOn(fable5Api, "getApprovalAssessmentEvidenceTimeline")
      .mockImplementation(async (assessmentId) => success(assessmentTimelines[assessmentId]));

    const result = await loadEvidenceIndex();

    expect(result.ok, JSON.stringify(result)).toBe(true);
    if (result.ok) {
      expect(Object.keys(result.data.assessmentTimelines)).toEqual(assessmentIds);
      expect(result.data.assessmentTimelines[approvedAssessmentId].assessment_id).toBe(
        approvedAssessmentId,
      );
    }
    expect(timeline).toHaveBeenCalledTimes(2);
  });

  it("uses one bounded queue for details and timelines while preserving summary order", async () => {
    const assessmentIds = Array.from(
      { length: 8 },
      (_, index) => `10000000-0000-4000-8000-${String(index + 1).padStart(12, "0")}`,
    );
    const assessments = assessmentIds.map(
      (assessmentId) =>
        ({
          ...approvedAssessment,
          assessment_id: assessmentId,
        }) as EvidenceIndex["assessments"][number],
    );
    const timelines = Object.fromEntries(
      assessmentIds.map((assessmentId) => [
        assessmentId,
        {
          ...governanceIndex.assessmentTimelines[approvedAssessmentId],
          assessment_id: assessmentId,
        },
      ]),
    ) as EvidenceIndex["assessmentTimelines"];
    const { listAssessments } = mockEmptyEvidenceReads();
    listAssessments.mockResolvedValue(success(assessments.map(assessmentSummary)));
    let active = 0;
    let peak = 0;
    const delayed = async <T,>(value: T) => {
      active += 1;
      peak = Math.max(peak, active);
      await Promise.resolve();
      active -= 1;
      return success(value);
    };
    vi.spyOn(fable5Api, "getApprovalAssessment").mockImplementation(async (assessmentId) =>
      delayed(assessments.find((assessment) => assessment.assessment_id === assessmentId)!),
    );
    vi.spyOn(fable5Api, "getApprovalAssessmentEvidenceTimeline").mockImplementation(
      async (assessmentId) => delayed(timelines[assessmentId]),
    );

    const result = await loadEvidenceIndex();

    expect(result.ok, JSON.stringify(result)).toBe(true);
    if (result.ok) {
      expect(result.data.assessments.map(({ assessment_id }) => assessment_id)).toEqual(
        assessmentIds,
      );
      expect(Object.keys(result.data.assessmentTimelines).sort()).toEqual(
        [...assessmentIds].sort(),
      );
    }
    expect(peak).toBe(4);
  });

  it.each([
    [
      "identifier",
      {
        ...approvedAssessment,
        assessment_id: "10000000-0000-4000-8000-000000000099",
      },
    ],
    [
      "artifact hash",
      {
        ...approvedAssessment,
        artifact_sha256: "f".repeat(64),
      },
    ],
    [
      "creation time",
      {
        ...approvedAssessment,
        created_at_utc: "2026-07-14T12:05:01Z",
      },
    ],
    [
      "outcome",
      {
        ...approvedAssessment,
        outcome: "FAIL_REJECT" as const,
      },
    ],
    [
      "ordered reason codes",
      {
        ...approvedAssessment,
        reason_codes: ["conflicting_reason"],
      },
    ],
    [
      "research configuration identity",
      {
        ...approvedAssessment,
        phase6_lineage: {
          ...approvedAssessment.phase6_lineage,
          research_configuration_id: "phase6-a-fail-cost-v2",
        },
      },
    ],
  ] as const)(
    "fails closed when an assessment detail conflicts with its list-summary %s",
    async (_field, conflictingAssessment) => {
      const { listAssessments } = mockEmptyEvidenceReads();
      listAssessments.mockResolvedValue(success([assessmentSummary(approvedAssessment)]));
      vi.spyOn(fable5Api, "getApprovalAssessment").mockResolvedValue(
        success(conflictingAssessment as EvidenceIndex["assessments"][number]),
      );
      vi.spyOn(fable5Api, "getApprovalAssessmentEvidenceTimeline").mockResolvedValue(
        success(governanceIndex.assessmentTimelines[approvedAssessmentId]),
      );

      const result = await loadEvidenceIndex();

      expect(result).toEqual({
        error: {
          kind: "conflict",
          message: "The detail response conflicts with its immutable list summary.",
          retrySafe: true,
        },
        ok: false,
      });
    },
  );

  it.each([
    ["artifact hash", { ...revocation, artifact_sha256: "f".repeat(64) }],
    [
      "effective time",
      { ...revocation, effective_at_utc: "2026-07-14T13:00:01Z" },
    ],
    [
      "authorization identity",
      {
        ...revocation,
        human_authorization_evidence_id: "90000000-0000-4000-8000-000000000001",
      },
    ],
    [
      "revocation evidence identity",
      {
        ...revocation,
        revocation_evidence_id: "90000000-0000-4000-8000-000000000002",
      },
    ],
  ] as const)("fails closed when a revocation detail %s conflicts with its list summary", async (_field, conflictingRevocation) => {
    const { listRevocations } = mockEmptyEvidenceReads();
    listRevocations.mockResolvedValue(success([revocationSummary(revocation)]));
    vi.spyOn(fable5Api, "getApprovalRevocation").mockResolvedValue(
      success(conflictingRevocation as EvidenceIndex["revocations"][number]),
    );

    const result = await loadEvidenceIndex();

    expect(result).toEqual({
      error: {
        kind: "conflict",
        message: "The detail response conflicts with its immutable list summary.",
        retrySafe: true,
      },
      ok: false,
    });
  });

  it("fails closed when evaluation-report shared summary fields conflict", async () => {
    mockEmptyEvidenceReads();
    const reportId = "91000000-0000-4000-8000-000000000011";
    const report = {
      artifact_id: reportId,
      artifact_sha256: "1".repeat(64),
      created_at_utc: "2026-07-14T12:00:00Z",
      fixture_id: "phase6-a-pass-v2",
      no_real_performance_claimed: true,
      promotion_state: "PASS_RESEARCH",
      reason_codes: ["research_gates_passed_not_paper_approval"],
      synthetic: true,
      warnings: ["synthetic evidence"],
    } as unknown as EvidenceIndex["evaluationReports"][number];
    vi.mocked(fable5Api.listEvaluationReports).mockResolvedValue(
      success([
        {
          artifact_id: reportId,
          artifact_sha256: report.artifact_sha256,
          created_at_utc: report.created_at_utc,
          fixture_id: report.fixture_id,
          no_real_performance_claimed: true,
          promotion_state: report.promotion_state,
          reason_codes: report.reason_codes,
          synthetic: true,
          warning_count: 1,
        },
      ]),
    );
    vi.spyOn(fable5Api, "getEvaluationReport").mockResolvedValue(
      success({ ...report, created_at_utc: "2026-07-14T12:00:01Z" }),
    );

    const result = await loadEvidenceIndex();

    expect(result).toMatchObject({ error: { kind: "conflict" }, ok: false });
  });

  it("fails closed when research-run shared summary fields conflict", async () => {
    mockEmptyEvidenceReads();
    const runId = "92000000-0000-4000-8000-000000000011";
    const run = {
      artifact_sha256: "2".repeat(64),
      configuration_id: "phase6-a-pass-v2",
      created_at_utc: "2026-07-14T12:00:00Z",
      family: "A_CROSS_SECTIONAL_EQUITY_RANKING",
      no_real_performance_claimed: true,
      pass_research_is_not_paper_approval: true,
      phase5_evaluation: { promotion_state: "PASS_RESEARCH" },
      reason_codes: ["research_gates_passed_not_paper_approval"],
      run_id: runId,
      status: "completed",
      synthetic: true,
    } as unknown as EvidenceIndex["researchRuns"][number];
    vi.mocked(fable5Api.listResearchRuns).mockResolvedValue(
      success([
        {
          artifact_sha256: run.artifact_sha256,
          configuration_id: run.configuration_id,
          created_at_utc: run.created_at_utc,
          family: run.family,
          no_real_performance_claimed: true,
          pass_research_is_not_paper_approval: true,
          promotion_state: "PASS_RESEARCH",
          reason_codes: run.reason_codes,
          run_id: runId,
          status: "blocked",
          synthetic: true,
        },
      ]),
    );
    vi.spyOn(fable5Api, "getResearchRun").mockResolvedValue(success(run));

    const result = await loadEvidenceIndex();

    expect(result).toMatchObject({ error: { kind: "conflict" }, ok: false });
  });

  it("requires complete structural equality between blocked-outcome list and detail records", async () => {
    mockEmptyEvidenceReads();
    const outcome = {
      outcome_id: "93000000-0000-4000-8000-000000000011",
      outcome_sha256: "3".repeat(64),
      reason_codes: ["policy_missing"],
      resolved_snapshots: [],
      snapshot_ids: [],
    } as unknown as EvidenceIndex["evaluationOutcomes"][number];
    vi.mocked(fable5Api.listEvaluationOutcomes).mockResolvedValue(success([outcome]));
    vi.spyOn(fable5Api, "getEvaluationOutcome").mockResolvedValue(
      success({ ...outcome, reason_codes: ["different_reason"] }),
    );

    const result = await loadEvidenceIndex();

    expect(result).toMatchObject({ error: { kind: "conflict" }, ok: false });
  });

  it.each([
    [404, "not-found", "The referenced immutable record is unavailable."],
    [409, "conflict", "The request conflicts with immutable persisted evidence."],
    [503, "unavailable", "The required deterministic service or adapter is unavailable."],
  ] as const)(
    "retains the complete assessment and ancestors when its timeline returns %s",
    async (status, kind, message) => {
      const assessmentId = approvedAssessmentId;
      const { listAssessments } = mockEmptyEvidenceReads();
      listAssessments.mockResolvedValue(success([assessmentSummary(approvedAssessment)]));
      vi.spyOn(fable5Api, "getApprovalAssessment").mockResolvedValue(
        success(approvedAssessment),
      );
      vi.spyOn(fable5Api, "getApprovalAssessmentEvidenceTimeline").mockResolvedValue({
        error: { kind, message, retrySafe: true, status },
        ok: false,
      });

      const result = await loadEvidenceIndex();

      expect(result.ok, JSON.stringify(result)).toBe(true);
      if (result.ok) {
        expect(result.data.assessments).toEqual([approvedAssessment]);
        expect(result.data.assessmentTimelines).toEqual({});
        expect(result.data.assessmentTimelineFailures[assessmentId]).toMatchObject({
          kind,
          message,
          retrySafe: true,
          status,
        });
      }
    },
  );

  it("fails closed when a shape-valid timeline conflicts with assessment-owned hashes", async () => {
    const { listAssessments } = mockEmptyEvidenceReads();
    listAssessments.mockResolvedValue(success([assessmentSummary(approvedAssessment)]));
    vi.spyOn(fable5Api, "getApprovalAssessment").mockResolvedValue(
      success(approvedAssessment),
    );
    vi.spyOn(fable5Api, "getApprovalAssessmentEvidenceTimeline").mockResolvedValue(
      success({
        ...governanceIndex.assessmentTimelines[approvedAssessmentId],
        policy: {
          ...governanceIndex.assessmentTimelines[approvedAssessmentId].policy,
          policy_sha256: "f".repeat(64),
        },
      }),
    );

    const result = await loadEvidenceIndex();

    expect(result.ok, JSON.stringify(result)).toBe(true);
    if (result.ok) {
      expect(result.data.assessments).toEqual([approvedAssessment]);
      expect(result.data.assessmentTimelines).toEqual({});
      expect(result.data.assessmentTimelineFailures[approvedAssessmentId]).toEqual({
        kind: "conflict",
        message: "The historical timeline conflicts with immutable assessment references.",
        retrySafe: true,
      });
    }
  });

  it("resolves a run only through its embedded evaluation and snapshot identities", () => {
    const exactReportId = "10000000-0000-4000-8000-000000000001";
    const unrelatedReportId = "10000000-0000-4000-8000-000000000002";
    const exactSnapshotId = "20000000-0000-4000-8000-000000000001";
    const unrelatedSnapshotId = "20000000-0000-4000-8000-000000000002";
    const mappingId = "30000000-0000-4000-8000-000000000001";
    const sha = "a".repeat(64);
    const run = {
      mapping_id: mappingId,
      mapping_input_sha256: sha,
      mapping_version: 1,
      phase5_evaluation: {
        evaluation_outcome_id: null,
        evaluation_report_id: exactReportId,
        evaluation_report_sha256: sha,
      },
      snapshot_bindings: [
        {
          as_of_utc: "2026-07-14T00:00:00Z",
          capability: "ohlcv",
          mapping_id: mappingId,
          mapping_input_sha256: sha,
          ordinal: 1,
          quality_status: "data_quality_accepted",
          snapshot_id: exactSnapshotId,
          snapshot_sha256: sha,
        },
      ],
    } as unknown as EvidenceIndex["researchRuns"][number];
    const index = {
      evaluationOutcomes: [],
      evaluationReports: [
        {
          artifact_id: unrelatedReportId,
          artifact_sha256: sha,
          mapping_id: mappingId,
          mapping_input_sha256: sha,
          mapping_version: 1,
        },
      ],
      snapshots: [
        {
          manifest: {
            snapshot_id: unrelatedSnapshotId,
            snapshot_sha256: sha,
            payload: {
              mapping: {
                mapping_id: mappingId,
                mapping_input_sha256: sha,
                mapping_version: 1,
              },
              request: {
                as_of_utc: "2026-07-14T00:00:00Z",
                capability: "ohlcv",
                mapping: {
                  mapping_id: mappingId,
                  mapping_input_sha256: sha,
                  mapping_version: 1,
                },
              },
            },
          },
          quality_status: "data_quality_accepted",
          snapshot_id: unrelatedSnapshotId,
          snapshot_sha256: sha,
        },
      ],
    } as unknown as EvidenceIndex;

    expect(evaluationEvidenceForResearchRun(index, run)).toEqual({
      conflict: true,
      outcome: undefined,
      report: undefined,
    });
    expect(snapshotsForResearchRun(index, run)).toEqual({ conflict: true, snapshots: [] });

    index.evaluationReports.push({
      artifact_id: exactReportId,
      artifact_sha256: sha,
      mapping_id: mappingId,
      mapping_input_sha256: sha,
      mapping_version: 1,
    } as EvidenceIndex["evaluationReports"][number]);
    index.snapshots.push({
      manifest: {
        snapshot_id: exactSnapshotId,
        snapshot_sha256: sha,
        payload: {
          mapping: {
            mapping_id: mappingId,
            mapping_input_sha256: sha,
            mapping_version: 1,
          },
          request: {
            as_of_utc: "2026-07-14T00:00:00Z",
            capability: "ohlcv",
            mapping: {
              mapping_id: mappingId,
              mapping_input_sha256: sha,
              mapping_version: 1,
            },
          },
        },
      },
      quality_status: "data_quality_accepted",
      snapshot_id: exactSnapshotId,
      snapshot_sha256: sha,
    } as EvidenceIndex["snapshots"][number]);

    expect(evaluationEvidenceForResearchRun(index, run).report?.artifact_id).toBe(exactReportId);
    expect(snapshotsForResearchRun(index, run).snapshots.map(({ snapshot_id }) => snapshot_id)).toEqual([
      exactSnapshotId,
    ]);
  });

  it("rejects a same-ID blocked outcome when its embedded Phase 5 evidence conflicts", () => {
    const index = emptyEvidenceIndex();
    const outcomeId = "71000000-0000-4000-8000-000000000001";
    const mappingId = "72000000-0000-4000-8000-000000000001";
    const snapshotId = "73000000-0000-4000-8000-000000000001";
    const policyId = "74000000-0000-4000-8000-000000000001";
    const fixtureSha256 = "1".repeat(64);
    const policySha256 = "2".repeat(64);
    const mappingInputSha256 = "3".repeat(64);
    const snapshotSha256 = "4".repeat(64);
    const run = {
      mapping_id: mappingId,
      mapping_input_sha256: mappingInputSha256,
      mapping_version: 1,
      phase5_evaluation: {
        evaluation_outcome_id: outcomeId,
        evaluation_report_id: null,
        evaluation_report_sha256: null,
        fixture_id: "blocked-fixture",
        fixture_sha256: fixtureSha256,
        policy_id: policyId,
        policy_sha256: policySha256,
        policy_version: 2,
        promotion_state: "BLOCKED_UNCOMPUTABLE",
        gate_codes: [],
        phase5_trial_set_sha256: null,
        raw_trial_count: 3,
        snapshot_bundle_sha256: "5".repeat(64),
      },
      snapshot_bundle_sha256: "5".repeat(64),
      status: "blocked",
      snapshot_bindings: [
        {
          mapping_id: mappingId,
          mapping_input_sha256: mappingInputSha256,
          snapshot_id: snapshotId,
          snapshot_sha256: snapshotSha256,
        },
      ],
    } as unknown as EvidenceIndex["researchRuns"][number];
    const outcome = {
      fixture_id: "blocked-fixture",
      mapping_id: mappingId,
      outcome_id: outcomeId,
      policy_id: policyId,
      policy_version: 2,
      promotion_state: "BLOCKED_UNCOMPUTABLE",
      resolved_fixture_sha256: fixtureSha256,
      resolved_policy_sha256: policySha256,
      resolved_raw_trial_count: 3,
      resolved_snapshots: [
        {
          mapping_id: mappingId,
          mapping_input_sha256: mappingInputSha256,
          mapping_version: 1,
          snapshot_id: snapshotId,
          snapshot_sha256: snapshotSha256,
        },
      ],
      snapshot_ids: [snapshotId],
    } as EvidenceIndex["evaluationOutcomes"][number];
    index.evaluationOutcomes.push(outcome);

    expect(evaluationEvidenceForResearchRun(index, run)).toMatchObject({
      conflict: false,
      outcome,
    });

    index.evaluationOutcomes[0] = {
      ...outcome,
      resolved_fixture_sha256: "f".repeat(64),
    };
    expect(evaluationEvidenceForResearchRun(index, run)).toEqual({
      conflict: true,
      outcome: undefined,
      report: undefined,
    });
  });

  it("includes later append-only revocations linked by the exact authorization reference", () => {
    const index = emptyEvidenceIndex();
    const cardId = "81000000-0000-4000-8000-000000000001";
    const mappingId = "82000000-0000-4000-8000-000000000001";
    const runId = "83000000-0000-4000-8000-000000000001";
    const authorizationId = "84000000-0000-4000-8000-000000000001";
    const assessmentId = "85000000-0000-4000-8000-000000000001";
    const revocationId = "86000000-0000-4000-8000-000000000001";
    const authorizationSha256 = "a".repeat(64);
    const mappingInputSha256 = "b".repeat(64);
    const researchArtifactSha256 = "c".repeat(64);
    index.mappings.push({
      mapping: {
        card_id: cardId,
        mapping_id: mappingId,
        mapping_input_sha256: mappingInputSha256,
        mapping_version: 1,
      },
    } as unknown as EvidenceIndex["mappings"][number]);
    index.researchRuns.push({
      artifact_sha256: researchArtifactSha256,
      mapping_id: mappingId,
      mapping_input_sha256: mappingInputSha256,
      mapping_version: 1,
      run_id: runId,
    } as unknown as EvidenceIndex["researchRuns"][number]);
    index.assessments.push({
      assessment_id: assessmentId,
      authorization_sha256: authorizationSha256,
      human_authorization_evidence_id: authorizationId,
      phase6_lineage: {
        mapping_id: mappingId,
        mapping_input_sha256: mappingInputSha256,
        mapping_version: 1,
        research_artifact_sha256: researchArtifactSha256,
        research_run_id: runId,
      },
      research_run_id: runId,
      revocation_ids: [],
    } as unknown as EvidenceIndex["assessments"][number]);
    index.revocations.push({
      authorization_sha256: authorizationSha256,
      human_authorization_evidence_id: authorizationId,
      revocation_id: revocationId,
    } as unknown as EvidenceIndex["revocations"][number]);

    const card = { card_id: cardId } as EvidenceIndex["cards"][number];
    const evidence = evidenceForCard(index, card);

    expect(evidence.assessments.map(({ assessment_id }) => assessment_id)).toEqual([assessmentId]);
    expect(evidence.revocations.map(({ revocation_id }) => revocation_id)).toEqual([revocationId]);
    expect(evidence.assessments[0].revocation_ids).toEqual([]);

    index.revocations[0].authorization_sha256 = "f".repeat(64);
    expect(evidenceForCard(index, card).revocations).toEqual([]);
  });

  it("rejects same-ID card descendants when server-owned hashes or versions conflict", () => {
    const index = emptyEvidenceIndex();
    const cardId = "91000000-0000-4000-8000-000000000001";
    const mappingId = "92000000-0000-4000-8000-000000000001";
    const runId = "93000000-0000-4000-8000-000000000001";
    const reportId = "94000000-0000-4000-8000-000000000001";
    const snapshotId = "95000000-0000-4000-8000-000000000001";
    const mappingInputSha256 = "d".repeat(64);
    const researchArtifactSha256 = "e".repeat(64);
    const conflictSha256 = "f".repeat(64);

    index.mappings.push({
      mapping: {
        card_id: cardId,
        mapping_id: mappingId,
        mapping_input_sha256: mappingInputSha256,
        mapping_version: 1,
      },
    } as unknown as EvidenceIndex["mappings"][number]);
    index.researchRuns.push({
      artifact_sha256: researchArtifactSha256,
      mapping_id: mappingId,
      mapping_input_sha256: mappingInputSha256,
      mapping_version: 2,
      run_id: runId,
    } as unknown as EvidenceIndex["researchRuns"][number]);
    index.researchRunSummaries.push({
      artifact_sha256: conflictSha256,
      run_id: runId,
    } as unknown as EvidenceIndex["researchRunSummaries"][number]);
    index.assessments.push({
      assessment_id: "96000000-0000-4000-8000-000000000001",
      phase6_lineage: {
        research_artifact_sha256: conflictSha256,
        research_run_id: runId,
      },
      research_run_id: runId,
    } as unknown as EvidenceIndex["assessments"][number]);
    index.evaluationReports.push({
      artifact_id: reportId,
      mapping_id: mappingId,
      mapping_input_sha256: conflictSha256,
      mapping_version: 1,
    } as unknown as EvidenceIndex["evaluationReports"][number]);
    index.snapshots.push({
      manifest: {
        payload: {
          mapping: {
            mapping_id: mappingId,
            mapping_input_sha256: conflictSha256,
            mapping_version: 1,
          },
        },
      },
      snapshot_id: snapshotId,
    } as unknown as EvidenceIndex["snapshots"][number]);

    const card = { card_id: cardId } as EvidenceIndex["cards"][number];
    let evidence = evidenceForCard(index, card);

    expect(evidence.mappings).toHaveLength(1);
    expect(evidence.snapshots).toEqual([]);
    expect(evidence.evaluationReports).toEqual([]);
    expect(evidence.researchRuns).toEqual([]);
    expect(evidence.researchRunSummaries).toEqual([]);
    expect(evidence.assessments).toEqual([]);

    index.researchRuns[0].mapping_version = 1;
    evidence = evidenceForCard(index, card);
    expect(evidence.researchRuns.map(({ run_id }) => run_id)).toEqual([runId]);
    expect(evidence.researchRunSummaries).toEqual([]);
    expect(evidence.assessments).toEqual([]);
  });

  it("binds mapping source evidence and rationale identity to the normalized card", () => {
    const cardId = "a1000000-0000-4000-8000-000000000001";
    const mappingId = "a2000000-0000-4000-8000-000000000001";
    const exactCard = {
      card_id: cardId,
      contribution_status: "not_blocked_by_corroboration",
      corroboration_status: "not_required",
      infra_risk: "low",
      required_data: {
        claim_ids: ["claim-required"],
        state: "source_supported",
        values: ["ohlcv"],
      },
      signal_family: {
        claim_ids: ["claim-signal"],
        state: "source_supported",
        value: "cross_sectional_ranking_claim",
      },
      testability_reason_codes: [],
    } as unknown as EvidenceIndex["cards"][number];
    const exactMapping = {
      mapping: {
        card_id: cardId,
        mapping_id: mappingId,
        rationale_template_version: "phase3-rationale-v1",
        source_evidence: [
          {
            claim_ids: ["claim-signal"],
            phase2_field: "signal_family",
            state: "source_supported",
            value: "cross_sectional_ranking_claim",
          },
          {
            claim_ids: ["claim-required"],
            phase2_field: "required_data",
            state: "source_supported",
            value: "ohlcv",
          },
          { claim_ids: [], phase2_field: "infra_risk", state: null, value: "low" },
        ],
      },
      rationale: {
        mapping_id: mappingId,
        template_version: "phase3-rationale-v1",
      },
    } as unknown as EvidenceIndex["mappings"][number];

    expect(mappingMatchesCard(exactMapping, exactCard)).toBe(true);
    expect(
      mappingMatchesCard(
        {
          ...exactMapping,
          mapping: {
            ...exactMapping.mapping,
            source_evidence: [
              {
                ...exactMapping.mapping.source_evidence[0],
                claim_ids: ["different-claim"],
              },
            ],
          },
        },
        exactCard,
      ),
    ).toBe(false);
    expect(
      mappingMatchesCard(
        {
          ...exactMapping,
          rationale: {
            ...exactMapping.rationale,
            mapping_id: "a3000000-0000-4000-8000-000000000001",
          },
        },
        exactCard,
      ),
    ).toBe(false);
  });

  it("reconciles the complete copied Phase 5 report relation before joining a research run", () => {
    const reportId = "b1000000-0000-4000-8000-000000000001";
    const mappingId = "b2000000-0000-4000-8000-000000000001";
    const policyId = "b3000000-0000-4000-8000-000000000001";
    const trialId = "b4000000-0000-4000-8000-000000000001";
    const report = {
      artifact_id: reportId,
      artifact_sha256: "1".repeat(64),
      code_version_git_sha: "2".repeat(40),
      config_hash: "3".repeat(64),
      created_at_utc: "2026-07-14T12:00:00Z",
      effective_trial_count: "1",
      evaluation_policy_id: policyId,
      evaluation_policy_sha256: "4".repeat(64),
      evaluation_policy_version: 2,
      fixture_id: "phase6-a-pass-v2",
      fixture_sha256: "5".repeat(64),
      gates: [{ gate_code: "DATA_PIT" }, { gate_code: "COST_STRESS" }],
      mapping_id: mappingId,
      mapping_input_sha256: "6".repeat(64),
      mapping_version: 3,
      promotion_state: "PASS_RESEARCH",
      random_seed: 17,
      raw_trial_count: 1,
      snapshot_bundle_sha256: "7".repeat(64),
      trials: [
        {
          config_sha256: "8".repeat(64),
          status: "completed",
          trial_id: trialId,
          trial_key: "trial-1",
        },
      ],
    } as unknown as EvidenceIndex["evaluationReports"][number];
    const run = {
      attempts: [
        {
          configuration_sha256: "8".repeat(64),
          phase5_trial_id: trialId,
          phase5_trial_key: "trial-1",
          status: "completed",
        },
      ],
      code_version_git_sha: report.code_version_git_sha,
      configuration_sha256: report.config_hash,
      created_at_utc: report.created_at_utc,
      mapping_id: mappingId,
      mapping_input_sha256: report.mapping_input_sha256,
      mapping_version: report.mapping_version,
      phase5_evaluation: {
        config_hash: report.config_hash,
        effective_trial_count: report.effective_trial_count,
        evaluation_outcome_id: null,
        evaluation_report_id: reportId,
        evaluation_report_sha256: report.artifact_sha256,
        fixture_id: report.fixture_id,
        fixture_sha256: report.fixture_sha256,
        gate_codes: ["DATA_PIT", "COST_STRESS"],
        policy_id: policyId,
        policy_sha256: report.evaluation_policy_sha256,
        policy_version: report.evaluation_policy_version,
        promotion_state: report.promotion_state,
        raw_trial_count: report.raw_trial_count,
        snapshot_bundle_sha256: report.snapshot_bundle_sha256,
      },
      random_seed: report.random_seed,
      snapshot_bundle_sha256: report.snapshot_bundle_sha256,
    } as unknown as EvidenceIndex["researchRuns"][number];

    expect(evaluationReportMatchesResearchRun(report, run)).toBe(true);
    const conflicts = [
      { ...report, code_version_git_sha: "f".repeat(40) },
      { ...report, fixture_sha256: "f".repeat(64) },
      { ...report, created_at_utc: "2026-07-14T12:00:01Z" },
      { ...report, gates: [...report.gates].reverse() },
      {
        ...report,
        trials: [{ ...report.trials[0], status: "failed" as const }],
      },
    ];
    for (const conflict of conflicts) {
      expect(evaluationReportMatchesResearchRun(conflict, run)).toBe(false);
    }
    expect(
      evaluationReportMatchesResearchRun(report, {
        ...run,
        phase5_evaluation: {
          ...run.phase5_evaluation,
          evaluation_outcome_id: "b5000000-0000-4000-8000-000000000001",
        },
      }),
    ).toBe(false);
  });

  it("reconciles snapshot outer identity, complete mapping, binding metadata, and report metadata", () => {
    const snapshotId = "c1000000-0000-4000-8000-000000000001";
    const mappingId = "c2000000-0000-4000-8000-000000000001";
    const mappingIdentity = {
      canonical_family: "A_CROSS_SECTIONAL_EQUITY_RANKING",
      mapper_rule_set_sha256: "1".repeat(64),
      mapper_rule_set_version: "phase3-canon-v1",
      mapping_id: mappingId,
      mapping_input_sha256: "2".repeat(64),
      mapping_version: 1,
      official_corroboration_source_version_ids: [],
      verdict: "BUILD_RESEARCH",
    } as const;
    const snapshot = {
      manifest: {
        payload: {
          adapter: {
            adapter_id: "synthetic-adapter",
            adapter_version: "1",
            dataset_id: "synthetic-dataset",
            product_id: "synthetic-product",
            provider_id: "synthetic-provider",
            schema_bindings: [
              { dataset_schema_id: "ohlcv", dataset_schema_version: "1" },
            ],
          },
          configuration: { fixture_set_version: "phase6-synthetic-pit-fixtures-v2" },
          mapping: mappingIdentity,
          request: {
            as_of_utc: "2026-07-14T00:00:00Z",
            capability: "ohlcv",
            mapping: mappingIdentity,
          },
          schema_bindings: [
            { dataset_schema_id: "ohlcv", dataset_schema_version: "1" },
          ],
        },
        snapshot_id: snapshotId,
        snapshot_sha256: "3".repeat(64),
      },
      quality_status: "data_quality_accepted",
      snapshot_id: snapshotId,
      snapshot_sha256: "3".repeat(64),
    } as unknown as EvidenceIndex["snapshots"][number];
    const report = {
      mapping_id: mappingId,
      mapping_input_sha256: mappingIdentity.mapping_input_sha256,
      mapping_version: 1,
    } as EvidenceIndex["evaluationReports"][number];
    const reference = {
      adapter_id: "synthetic-adapter",
      adapter_version: "1",
      as_of_utc: "2026-07-14T00:00:00Z",
      capability: "ohlcv",
      dataset_id: "synthetic-dataset",
      dataset_schema_versions: ["ohlcv:1"],
      fixture_set_version: "phase6-synthetic-pit-fixtures-v2",
      product_id: "synthetic-product",
      provider_id: "synthetic-provider",
      quality_status: "data_quality_accepted",
      snapshot_id: snapshotId,
      snapshot_sha256: "3".repeat(64),
    } as EvidenceIndex["evaluationReports"][number]["data_snapshots"][number];

    expect(snapshotMatchesEvaluationReportEvidence(snapshot, reference, report)).toBe(true);
    expect(
      snapshotMatchesEvaluationReportEvidence(
        { ...snapshot, snapshot_sha256: "f".repeat(64) },
        reference,
        report,
      ),
    ).toBe(false);
    expect(
      snapshotMatchesEvaluationReportEvidence(
        snapshot,
        { ...reference, dataset_schema_versions: ["ohlcv:2"] },
        report,
      ),
    ).toBe(false);

    const run = {
      family: mappingIdentity.canonical_family,
      mapping_id: mappingId,
      mapping_input_sha256: mappingIdentity.mapping_input_sha256,
      mapping_version: 1,
      snapshot_bindings: [
        {
          as_of_utc: "2026-07-14T00:00:00Z",
          capability: "ohlcv",
          mapping_id: mappingId,
          mapping_input_sha256: mappingIdentity.mapping_input_sha256,
          ordinal: 1,
          quality_status: "data_quality_accepted",
          snapshot_id: snapshotId,
          snapshot_sha256: "3".repeat(64),
        },
      ],
    } as EvidenceIndex["researchRuns"][number];
    const snapshotIndex = { ...emptyEvidenceIndex(), snapshots: [snapshot] };
    expect(snapshotsForResearchRun(snapshotIndex, run).conflict).toBe(false);
    run.snapshot_bindings[0].as_of_utc = "2026-07-14T00:00:01Z";
    expect(snapshotsForResearchRun(snapshotIndex, run).conflict).toBe(true);
  });
});
