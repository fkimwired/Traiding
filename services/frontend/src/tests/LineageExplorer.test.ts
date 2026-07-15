import { describe, expect, it } from "vitest";

import {
  lineageBranchLinks,
  resolveLineageSelection,
} from "../app/lineage/LineageExplorer";
import type { EvidenceIndex } from "../lib/evidence-index";

const cardId = "10000000-0000-4000-8000-000000000001";
const mappingId = "20000000-0000-4000-8000-000000000001";
const runId = "30000000-0000-4000-8000-000000000001";
const assessmentId = "40000000-0000-4000-8000-000000000001";
const revocationId = "50000000-0000-4000-8000-000000000001";
const authorizationId = "60000000-0000-4000-8000-000000000001";
const secondAssessmentId = "40000000-0000-4000-8000-000000000002";
const evaluationReportId = "70000000-0000-4000-8000-000000000001";
const evaluationOutcomeId = "80000000-0000-4000-8000-000000000001";
const mappingInputSha256 = "a".repeat(64);
const researchArtifactSha256 = "b".repeat(64);
const authorizationSha256 = "c".repeat(64);

const index = {
  assessmentTimelines: {},
  assessments: [
    {
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
      revocation_ids: [revocationId],
    },
    {
      assessment_id: secondAssessmentId,
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
    },
  ],
  cards: [{ card_id: cardId }],
  evaluationOutcomes: [],
  evaluationReports: [],
  mappings: [
    {
      mapping: {
        card_id: cardId,
        mapping_id: mappingId,
        mapping_input_sha256: mappingInputSha256,
        mapping_version: 1,
        rationale_template_version: "phase3-rationale-v1",
      },
      rationale: { mapping_id: mappingId, template_version: "phase3-rationale-v1" },
    },
  ],
  researchRunSummaries: [],
  researchRuns: [
    {
      artifact_sha256: researchArtifactSha256,
      mapping_id: mappingId,
      mapping_input_sha256: mappingInputSha256,
      mapping_version: 1,
      phase5_evaluation: {
        evaluation_outcome_id: null,
        evaluation_report_id: null,
        evaluation_report_sha256: null,
      },
      run_id: runId,
    },
  ],
  revocations: [
    {
      authorization_sha256: authorizationSha256,
      human_authorization_evidence_id: authorizationId,
      revocation_id: revocationId,
    },
  ],
  snapshots: [],
} as unknown as EvidenceIndex;

describe("resolveLineageSelection", () => {
  it("does not choose one of multiple authorization-linked assessment branches", () => {
    const selection = resolveLineageSelection(index, { revocation_id: revocationId });

    expect(selection?.revocation?.revocation_id).toBe(revocationId);
    expect(selection?.assessment).toBeUndefined();
    expect(selection?.researchRun).toBeUndefined();
    expect(selection?.mapping).toBeUndefined();
    expect(selection?.card).toBeUndefined();

    const branches = lineageBranchLinks(index, selection!, {
      revocation_id: revocationId,
    });
    expect(branches).toHaveLength(2);
    expect(branches.map((branch) => branch.href)).toEqual(
      expect.arrayContaining([
        expect.stringContaining("assessment_id=" + assessmentId),
        expect.stringContaining("assessment_id=" + secondAssessmentId),
      ]),
    );
    expect(branches.every((branch) => branch.href.includes("revocation_id=" + revocationId))).toBe(
      true,
    );
  });

  it("does not link a same-ID authorization when its server-owned hash conflicts", () => {
    const conflictingIndex = {
      ...index,
      revocations: [
        {
          ...index.revocations[0],
          authorization_sha256: "f".repeat(64),
        },
      ],
    } as EvidenceIndex;
    const selection = resolveLineageSelection(conflictingIndex, {
      revocation_id: revocationId,
    });

    expect(selection?.revocation?.revocation_id).toBe(revocationId);
    expect(
      lineageBranchLinks(conflictingIndex, selection!, { revocation_id: revocationId }),
    ).toEqual([]);
    expect(
      resolveLineageSelection(conflictingIndex, {
        assessment_id: assessmentId,
        revocation_id: revocationId,
      }),
    ).toBeNull();
  });

  it("walks exact immutable ancestors from an explicitly selected assessment", () => {
    const selection = resolveLineageSelection(index, { assessment_id: assessmentId });

    expect(selection?.assessment?.assessment_id).toBe(assessmentId);
    expect(selection?.researchRun?.run_id).toBe(runId);
    expect(selection?.mapping?.mapping.mapping_id).toBe(mappingId);
    expect(selection?.card?.card_id).toBe(cardId);
  });

  it("stops at the assessment when a same-ID research artifact hash conflicts", () => {
    const conflictingIndex = {
      ...index,
      assessments: [
        {
          ...index.assessments[0],
          phase6_lineage: {
            ...index.assessments[0].phase6_lineage,
            research_artifact_sha256: "f".repeat(64),
          },
        },
        index.assessments[1],
      ],
    } as EvidenceIndex;

    const selection = resolveLineageSelection(conflictingIndex, {
      assessment_id: assessmentId,
    });

    expect(selection?.assessment?.assessment_id).toBe(assessmentId);
    expect(selection?.researchRun).toBeUndefined();
    expect(selection?.mapping).toBeUndefined();
    expect(selection?.card).toBeUndefined();
    expect(
      resolveLineageSelection(conflictingIndex, {
        assessment_id: assessmentId,
        run_id: runId,
      }),
    ).toBeNull();
  });

  it("stops at the run when a same-ID mapping input hash or version conflicts", () => {
    const conflictingIndex = {
      ...index,
      researchRuns: [
        {
          ...index.researchRuns[0],
          mapping_version: 2,
        },
      ],
    } as EvidenceIndex;

    const selection = resolveLineageSelection(conflictingIndex, { run_id: runId });

    expect(selection?.researchRun?.run_id).toBe(runId);
    expect(selection?.mapping).toBeUndefined();
    expect(selection?.card).toBeUndefined();
    expect(
      resolveLineageSelection(conflictingIndex, {
        mapping_id: mappingId,
        run_id: runId,
      }),
    ).toBeNull();
  });

  it("does not substitute a same-card-ID mapping with conflicting embedded Phase 2 lineage", () => {
    const exactIndex = {
      ...index,
      cards: [
        {
          ...index.cards[0],
          source_version_id: "91000000-0000-4000-8000-000000000001",
        },
      ],
      mappings: [
        {
          ...index.mappings[0],
          mapping: {
            ...index.mappings[0].mapping,
            source_version_id: "91000000-0000-4000-8000-000000000002",
          },
        },
      ],
    } as EvidenceIndex;

    const mappingSelection = resolveLineageSelection(exactIndex, { mapping_id: mappingId });
    expect(mappingSelection?.mapping?.mapping.mapping_id).toBe(mappingId);
    expect(mappingSelection?.card).toBeUndefined();

    const cardSelection = resolveLineageSelection(exactIndex, { card_id: cardId });
    expect(cardSelection?.card?.card_id).toBe(cardId);
    expect(lineageBranchLinks(exactIndex, cardSelection!, { card_id: cardId })).toEqual([]);
    expect(
      resolveLineageSelection(exactIndex, { card_id: cardId, mapping_id: mappingId }),
    ).toBeNull();
  });

  it("leaves descendants unselected for a source card with multiple possible branches", () => {
    const selection = resolveLineageSelection(index, { card_id: cardId });

    expect(selection?.card?.card_id).toBe(cardId);
    expect(selection?.mapping).toBeUndefined();
    expect(lineageBranchLinks(index, selection!, { card_id: cardId })).toHaveLength(2);
  });

  it("fails closed when any explicit identifier is missing", () => {
    expect(
      resolveLineageSelection(index, {
        assessment_id: "ffffffff-ffff-4fff-8fff-ffffffffffff",
      }),
    ).toBeNull();
    expect(
      resolveLineageSelection(index, {
        assessment_id: "ffffffff-ffff-4fff-8fff-ffffffffffff",
        revocation_id: revocationId,
      }),
    ).toBeNull();
  });

  it("fails closed when report and blocked-outcome identifiers are both supplied", () => {
    const indexWithBothEvaluationArtifacts = {
      ...index,
      evaluationOutcomes: [
        {
          mapping_id: mappingId,
          outcome_id: evaluationOutcomeId,
        },
      ],
      evaluationReports: [
        {
          artifact_id: evaluationReportId,
          artifact_sha256: "a".repeat(64),
          mapping_id: mappingId,
        },
      ],
    } as unknown as EvidenceIndex;

    expect(
      resolveLineageSelection(indexWithBothEvaluationArtifacts, {
        evaluation_outcome_id: evaluationOutcomeId,
        evaluation_report_id: evaluationReportId,
      }),
    ).toBeNull();
  });

  it("does not join a same-ID blocked outcome whose Phase 5 evidence conflicts", () => {
    const snapshotId = "92000000-0000-4000-8000-000000000001";
    const policyId = "93000000-0000-4000-8000-000000000001";
    const fixtureSha256 = "d".repeat(64);
    const policySha256 = "e".repeat(64);
    const snapshotSha256 = "f".repeat(64);
    const conflictingIndex = {
      ...index,
      evaluationOutcomes: [
        {
          fixture_id: "blocked-fixture",
          mapping_id: mappingId,
          outcome_id: evaluationOutcomeId,
          policy_id: policyId,
          policy_version: 1,
          promotion_state: "BLOCKED_UNCOMPUTABLE",
          resolved_fixture_sha256: "0".repeat(64),
          resolved_policy_sha256: policySha256,
          resolved_raw_trial_count: 0,
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
        },
      ],
      researchRuns: [
        {
          ...index.researchRuns[0],
          phase5_evaluation: {
            evaluation_outcome_id: evaluationOutcomeId,
            evaluation_report_id: null,
            evaluation_report_sha256: null,
            fixture_id: "blocked-fixture",
            fixture_sha256: fixtureSha256,
            policy_id: policyId,
            policy_sha256: policySha256,
            policy_version: 1,
            promotion_state: "BLOCKED_UNCOMPUTABLE",
            raw_trial_count: 0,
          },
          snapshot_bindings: [
            {
              mapping_id: mappingId,
              mapping_input_sha256: mappingInputSha256,
              snapshot_id: snapshotId,
              snapshot_sha256: snapshotSha256,
            },
          ],
        },
      ],
    } as unknown as EvidenceIndex;

    const outcomeSelection = resolveLineageSelection(conflictingIndex, {
      evaluation_outcome_id: evaluationOutcomeId,
    });
    expect(outcomeSelection?.evaluationOutcome?.outcome_id).toBe(evaluationOutcomeId);
    expect(outcomeSelection?.mapping?.mapping.mapping_id).toBe(mappingId);
    expect(
      lineageBranchLinks(conflictingIndex, outcomeSelection!, {
        evaluation_outcome_id: evaluationOutcomeId,
      }),
    ).toEqual([]);
    expect(
      resolveLineageSelection(conflictingIndex, {
        evaluation_outcome_id: evaluationOutcomeId,
        run_id: runId,
      }),
    ).toBeNull();
  });

  it("fails closed when a revocation is combined with upstream artifacts without an assessment", () => {
    expect(
      resolveLineageSelection(index, {
        revocation_id: revocationId,
        run_id: runId,
      }),
    ).toBeNull();
    expect(
      resolveLineageSelection(index, {
        card_id: cardId,
        revocation_id: revocationId,
      }),
    ).toBeNull();
  });

  it("accepts a revocation and upstream identifiers only through their explicit assessment", () => {
    const selection = resolveLineageSelection(index, {
      assessment_id: assessmentId,
      card_id: cardId,
      revocation_id: revocationId,
      run_id: runId,
    });

    expect(selection?.assessment?.assessment_id).toBe(assessmentId);
    expect(selection?.revocation?.revocation_id).toBe(revocationId);
    expect(selection?.researchRun?.run_id).toBe(runId);
    expect(selection?.card?.card_id).toBe(cardId);
  });
});
