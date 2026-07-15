"use client";

import type { components } from "@fable5/contracts";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  type ApiFailure,
  type ApiResult,
  fable5Api,
  type RemoteState,
  type RemoteValue,
} from "./api";

type TradingIdeaCard = components["schemas"]["TradingIdeaCard"];
type MappingWithRationale = components["schemas"]["MappingWithRationale"];
type DataSnapshot = components["schemas"]["DataSnapshot"];
type EvaluationReport = components["schemas"]["EvaluationReport"];
type EvaluationReportSummary = components["schemas"]["EvaluationReportSummary"];
type BlockedEvaluationOutcome = components["schemas"]["BlockedEvaluationOutcome"];
type ResearchRunArtifact = components["schemas"]["ResearchRunArtifact"];
type ResearchRunSummary = components["schemas"]["ResearchRunSummary"];
type ApprovalAssessmentArtifact = components["schemas"]["ApprovalAssessmentArtifact"];
type ApprovalAssessmentSummary = components["schemas"]["ApprovalAssessmentSummary"];
type ApprovalAssessmentEvidenceTimeline =
  components["schemas"]["ApprovalAssessmentEvidenceTimeline"];
type AuthorizationRevocationArtifact = components["schemas"]["AuthorizationRevocationArtifact"];
type AuthorizationRevocationSummary = components["schemas"]["AuthorizationRevocationSummary"];
type MappingEvidenceReference = components["schemas"]["MappingEvidenceReference"];
type SnapshotEvidence = components["schemas"]["SnapshotEvidence"];

export function mappingMatchesResearchRun(
  mapping: MappingWithRationale,
  run: ResearchRunArtifact,
) {
  return (
    mapping.mapping.mapping_id === run.mapping_id &&
    mapping.mapping.mapping_input_sha256 === run.mapping_input_sha256 &&
    mapping.mapping.mapping_version === run.mapping_version &&
    mapping.mapping.canonical_family === run.family
  );
}

export function mappingMatchesEvaluationReport(
  mapping: MappingWithRationale,
  report: EvaluationReport,
) {
  return (
    mapping.mapping.mapping_id === report.mapping_id &&
    mapping.mapping.mapping_input_sha256 === report.mapping_input_sha256 &&
    mapping.mapping.mapping_version === report.mapping_version
  );
}

function sameOrderedStrings(
  left: readonly string[] | undefined,
  right: readonly string[] | undefined,
) {
  if (left === undefined || right === undefined) return left === right;
  return left.length === right.length && left.every((value, index) => value === right[index]);
}

function sameNullableString(
  left: string | null | undefined,
  right: string | null | undefined,
) {
  return left === right || (left == null && right == null);
}

function structurallyEqual(left: unknown, right: unknown): boolean {
  if (Object.is(left, right)) return true;
  if (Array.isArray(left) || Array.isArray(right)) {
    return (
      Array.isArray(left) &&
      Array.isArray(right) &&
      left.length === right.length &&
      left.every((value, index) => structurallyEqual(value, right[index]))
    );
  }
  if (
    left !== null &&
    right !== null &&
    typeof left === "object" &&
    typeof right === "object"
  ) {
    const leftRecord = left as Record<string, unknown>;
    const rightRecord = right as Record<string, unknown>;
    const leftKeys = Object.keys(leftRecord).sort();
    const rightKeys = Object.keys(rightRecord).sort();
    return (
      sameOrderedStrings(leftKeys, rightKeys) &&
      leftKeys.every((key) => structurallyEqual(leftRecord[key], rightRecord[key]))
    );
  }
  return false;
}

function mappingEvidenceMatchesCard(
  reference: MappingEvidenceReference,
  card: TradingIdeaCard,
) {
  const claimIdsMatch = (claimIds: readonly string[]) =>
    sameOrderedStrings(reference.claim_ids, claimIds);
  const fieldEvidenceMatches = (
    evidence: { claim_ids: string[]; state: string; value: string | null },
  ) =>
    reference.state === evidence.state &&
    reference.value === evidence.value &&
    claimIdsMatch(evidence.claim_ids);

  switch (reference.phase2_field) {
    case "signal_family":
      return fieldEvidenceMatches(card.signal_family);
    case "forecast_horizon":
      return fieldEvidenceMatches(card.forecast_horizon);
    case "execution_style":
      return fieldEvidenceMatches(card.execution_style);
    case "required_data":
      return (
        reference.state === card.required_data.state &&
        reference.value !== null &&
        reference.value !== undefined &&
        card.required_data.values.includes(
          reference.value as (typeof card.required_data.values)[number],
        ) &&
        claimIdsMatch(card.required_data.claim_ids)
      );
    case "testability":
      return (
        reference.state == null &&
        reference.value !== null &&
        reference.value !== undefined &&
        card.testability_reason_codes.includes(
          reference.value as (typeof card.testability_reason_codes)[number],
        ) &&
        reference.claim_ids.length === 0
      );
    case "infra_risk":
      return (
        reference.state == null &&
        reference.value === card.infra_risk &&
        reference.claim_ids.length === 0
      );
    case "contribution_status":
      return (
        reference.state == null &&
        reference.value === card.contribution_status &&
        reference.claim_ids.length === 0
      );
    case "corroboration_status":
      return (
        reference.state == null &&
        reference.value === card.corroboration_status &&
        reference.claim_ids.length === 0
      );
  }
}

export function mappingMatchesCard(mapping: MappingWithRationale, card: TradingIdeaCard) {
  const artifact = mapping.mapping;
  return (
    artifact.card_id === card.card_id &&
    artifact.source_id === card.source_id &&
    artifact.source_version_id === card.source_version_id &&
    artifact.source_version === card.source_version &&
    artifact.extraction_request_id === card.extraction_request_id &&
    artifact.extraction_config_sha256 === card.extraction_config_sha256 &&
    artifact.extraction_schema_version === card.extraction_schema_version &&
    artifact.extractor_kind === card.extractor_kind &&
    artifact.extractor_id === card.extractor_id &&
    artifact.extractor_version === card.extractor_version &&
    sameNullableString(artifact.extraction_model_id, card.extraction_model_id) &&
    sameNullableString(artifact.extraction_model_revision, card.extraction_model_revision) &&
    sameNullableString(artifact.extraction_prompt_sha256, card.extraction_prompt_sha256) &&
    sameNullableString(artifact.extraction_prompt_version, card.extraction_prompt_version) &&
    sameOrderedStrings(
      artifact.official_corroboration_source_version_ids,
      card.official_corroboration_source_version_ids,
    ) &&
    (artifact.source_evidence ?? []).every((reference) =>
      mappingEvidenceMatchesCard(reference, card),
    ) &&
    ((mapping.rationale === undefined && artifact.rationale_template_version === undefined) ||
      (mapping.rationale?.mapping_id === artifact.mapping_id &&
        mapping.rationale.template_version === artifact.rationale_template_version))
  );
}

export function evaluationReportMatchesResearchRun(
  report: EvaluationReport,
  run: ResearchRunArtifact,
) {
  const evaluation = run.phase5_evaluation;
  const reportTrials = report.trials ?? [];
  const attempts = run.attempts ?? [];
  return (
    evaluation.evaluation_report_id === report.artifact_id &&
    evaluation.evaluation_report_sha256 === report.artifact_sha256 &&
    evaluation.evaluation_outcome_id === null &&
    report.mapping_id === run.mapping_id &&
    report.mapping_input_sha256 === run.mapping_input_sha256 &&
    report.mapping_version === run.mapping_version &&
    report.evaluation_policy_id === evaluation.policy_id &&
    report.evaluation_policy_version === evaluation.policy_version &&
    report.evaluation_policy_sha256 === evaluation.policy_sha256 &&
    report.fixture_id === evaluation.fixture_id &&
    report.fixture_sha256 === evaluation.fixture_sha256 &&
    report.config_hash === evaluation.config_hash &&
    report.snapshot_bundle_sha256 === evaluation.snapshot_bundle_sha256 &&
    report.promotion_state === evaluation.promotion_state &&
    sameOrderedStrings(
      report.gates?.map((gate) => gate.gate_code),
      evaluation.gate_codes,
    ) &&
    report.raw_trial_count === evaluation.raw_trial_count &&
    report.effective_trial_count === evaluation.effective_trial_count &&
    run.configuration_sha256 === report.config_hash &&
    run.snapshot_bundle_sha256 === report.snapshot_bundle_sha256 &&
    run.code_version_git_sha === report.code_version_git_sha &&
    run.random_seed === report.random_seed &&
    run.created_at_utc === report.created_at_utc &&
    reportTrials.length === attempts.length &&
    reportTrials.every((trial, index) => {
      const attempt = attempts[index];
      return (
        attempt !== undefined &&
        trial.trial_id === attempt.phase5_trial_id &&
        trial.trial_key === attempt.phase5_trial_key &&
        trial.status === attempt.status &&
        trial.config_sha256 === attempt.configuration_sha256
      );
    })
  );
}

export function evaluationOutcomeMatchesMapping(
  outcome: BlockedEvaluationOutcome,
  mapping: MappingWithRationale,
) {
  const artifact = mapping.mapping;
  const outcomeSnapshots = outcome.resolved_snapshots ?? [];
  return (
    outcome.mapping_id === artifact.mapping_id &&
    sameOrderedStrings(
      outcome.snapshot_ids,
      outcomeSnapshots.map((snapshot) => snapshot.snapshot_id),
    ) &&
    outcomeSnapshots.every(
      (snapshot) =>
        snapshot.mapping_id === artifact.mapping_id &&
        snapshot.mapping_input_sha256 === artifact.mapping_input_sha256 &&
        snapshot.mapping_version === artifact.mapping_version,
    )
  );
}

export function evaluationOutcomeMatchesResearchRun(
  outcome: BlockedEvaluationOutcome,
  run: ResearchRunArtifact,
) {
  const evaluation = run.phase5_evaluation;
  const outcomeSnapshots = outcome.resolved_snapshots ?? [];
  const runSnapshots = run.snapshot_bindings ?? [];
  return (
    run.status === "blocked" &&
    evaluation.evaluation_outcome_id === outcome.outcome_id &&
    evaluation.evaluation_report_id === null &&
    evaluation.evaluation_report_sha256 === null &&
    evaluation.phase5_trial_set_sha256 === null &&
    (evaluation.gate_codes ?? []).length === 0 &&
    outcome.mapping_id === run.mapping_id &&
    outcome.fixture_id === evaluation.fixture_id &&
    outcome.resolved_fixture_sha256 === evaluation.fixture_sha256 &&
    outcome.policy_id === evaluation.policy_id &&
    outcome.policy_version === evaluation.policy_version &&
    outcome.resolved_policy_sha256 === evaluation.policy_sha256 &&
    outcome.promotion_state === evaluation.promotion_state &&
    outcome.resolved_raw_trial_count === evaluation.raw_trial_count &&
    run.snapshot_bundle_sha256 === evaluation.snapshot_bundle_sha256 &&
    outcomeSnapshots.length === runSnapshots.length &&
    sameOrderedStrings(
      outcome.snapshot_ids,
      outcomeSnapshots.map((snapshot) => snapshot.snapshot_id),
    ) &&
    sameOrderedStrings(
      outcome.snapshot_ids,
      runSnapshots.map((snapshot) => snapshot.snapshot_id),
    ) &&
    outcomeSnapshots.every((snapshot, index) => {
      const binding = runSnapshots[index];
      return (
        binding !== undefined &&
        snapshot.snapshot_id === binding.snapshot_id &&
        snapshot.snapshot_sha256 === binding.snapshot_sha256 &&
        snapshot.mapping_id === binding.mapping_id &&
        snapshot.mapping_id === run.mapping_id &&
        snapshot.mapping_input_sha256 === binding.mapping_input_sha256 &&
        snapshot.mapping_input_sha256 === run.mapping_input_sha256 &&
        snapshot.mapping_version === run.mapping_version
      );
    })
  );
}

export function researchRunMatchesAssessment(
  run: ResearchRunArtifact,
  assessment: ApprovalAssessmentArtifact,
) {
  const evaluation = run.phase5_evaluation;
  const lineage = assessment.phase6_lineage;
  const runSnapshots = run.snapshot_bindings;
  const lineageSnapshots = lineage.snapshot_bindings;
  return (
    run.run_id === assessment.research_run_id &&
    run.run_id === lineage.research_run_id &&
    run.artifact_sha256 === lineage.research_artifact_sha256 &&
    run.family === lineage.canonical_family &&
    run.code_version_git_sha === lineage.code_version_git_sha &&
    run.feature_lineage_sha256 === lineage.feature_lineage_sha256 &&
    run.mapping_id === lineage.mapping_id &&
    run.mapping_input_sha256 === lineage.mapping_input_sha256 &&
    run.mapping_version === lineage.mapping_version &&
    run.configuration_id === lineage.research_configuration_id &&
    run.configuration_sha256 === lineage.research_configuration_sha256 &&
    run.pipeline_input_sha256 === lineage.research_pipeline_input_sha256 &&
    run.request_fingerprint_sha256 === lineage.research_request_fingerprint_sha256 &&
    run.random_seed === lineage.random_seed &&
    run.status === lineage.research_status &&
    run.snapshot_bundle_sha256 === lineage.snapshot_bundle_sha256 &&
    run.source_reproduction_audit?.audit_sha256 ===
      lineage.source_reproduction_audit_sha256 &&
    run.specification?.specification_sha256 === lineage.specification_sha256 &&
    evaluation?.effective_trial_count === lineage.effective_trial_count &&
    sameNullableString(evaluation?.evaluation_report_id, lineage.evaluation_report_id) &&
    sameNullableString(
      evaluation?.evaluation_report_sha256,
      lineage.evaluation_report_sha256,
    ) &&
    evaluation?.fixture_id === lineage.phase5_fixture_id &&
    evaluation?.fixture_sha256 === lineage.phase5_fixture_sha256 &&
    evaluation?.policy_id === lineage.phase5_policy_id &&
    evaluation?.policy_sha256 === lineage.phase5_policy_sha256 &&
    evaluation?.policy_version === lineage.phase5_policy_version &&
    sameNullableString(
      evaluation?.phase5_trial_set_sha256,
      lineage.phase5_trial_set_sha256,
    ) &&
    evaluation?.promotion_state === lineage.promotion_state &&
    evaluation?.raw_trial_count === lineage.raw_trial_count &&
    sameOrderedStrings(evaluation?.gate_codes, lineage.gate_codes) &&
    (runSnapshots === undefined || lineageSnapshots === undefined
      ? runSnapshots === lineageSnapshots
      : runSnapshots.length === lineageSnapshots.length &&
        runSnapshots.every((binding, index) => {
          const item = lineageSnapshots[index];
          return (
            item !== undefined &&
            binding.as_of_utc === item.as_of_utc &&
            binding.binding_sha256 === item.binding_sha256 &&
            binding.capability === item.capability &&
            binding.mapping_id === item.mapping_id &&
            binding.mapping_input_sha256 === item.mapping_input_sha256 &&
            binding.ordinal === item.ordinal &&
            binding.quality_status === item.quality_status &&
            binding.snapshot_id === item.snapshot_id &&
            binding.snapshot_sha256 === item.snapshot_sha256
          );
        }))
  );
}

export function revocationMatchesAssessment(
  revocation: AuthorizationRevocationArtifact,
  assessment: ApprovalAssessmentArtifact,
) {
  return (
    revocation.human_authorization_evidence_id ===
      assessment.human_authorization_evidence_id &&
    revocation.authorization_sha256 === assessment.authorization_sha256
  );
}

export function timelineMatchesAssessment(
  timeline: ApprovalAssessmentEvidenceTimeline,
  assessment: ApprovalAssessmentArtifact,
) {
  return (
    timeline.assessment_id === assessment.assessment_id &&
    timeline.assessment_created_at_utc === assessment.created_at_utc &&
    timeline.policy.approval_policy_version_id === assessment.approval_policy_version_id &&
    timeline.policy.policy_sha256 === assessment.approval_policy_sha256 &&
    timeline.scope.approval_scope_version_id === assessment.approval_scope_version_id &&
    timeline.scope.scope_sha256 === assessment.approval_scope_sha256 &&
    timeline.authorization.human_authorization_evidence_id ===
      assessment.human_authorization_evidence_id &&
    timeline.authorization.authorization_sha256 === assessment.authorization_sha256 &&
    timeline.risk_input.risk_input_id === assessment.risk_input_id &&
    timeline.risk_input.risk_input_sha256 === assessment.risk_input_sha256
  );
}

export function snapshotMatchesMapping(snapshot: DataSnapshot, mapping: MappingWithRationale) {
  if (
    snapshot.snapshot_id !== snapshot.manifest.snapshot_id ||
    snapshot.snapshot_sha256 !== snapshot.manifest.snapshot_sha256
  ) {
    return false;
  }
  const matchesIdentity = (
    snapshotMapping: DataSnapshot["manifest"]["payload"]["mapping"] | undefined,
  ) =>
    snapshotMapping !== undefined &&
    snapshotMapping.mapping_id === mapping.mapping.mapping_id &&
    snapshotMapping.mapping_input_sha256 === mapping.mapping.mapping_input_sha256 &&
    snapshotMapping.mapping_version === mapping.mapping.mapping_version &&
    snapshotMapping.canonical_family === mapping.mapping.canonical_family &&
    snapshotMapping.mapper_rule_set_sha256 === mapping.mapping.mapper_rule_set_sha256 &&
    snapshotMapping.mapper_rule_set_version === mapping.mapping.mapper_rule_set_version &&
    snapshotMapping.verdict === mapping.mapping.verdict &&
    sameOrderedStrings(
      snapshotMapping.official_corroboration_source_version_ids,
      mapping.mapping.official_corroboration_source_version_ids,
    );
  const payload = snapshot.manifest.payload;
  return (
    matchesIdentity(payload.mapping) &&
    matchesIdentity(payload.request?.mapping) &&
    structurallyEqual(payload.mapping, payload.request.mapping)
  );
}

function snapshotMatchesExpectedMapping(
  snapshot: DataSnapshot,
  expected: {
    family?: ResearchRunArtifact["family"];
    mapping_id: string;
    mapping_input_sha256: string;
    mapping_version: number;
  },
) {
  const payload = snapshot.manifest?.payload;
  const mapping = payload?.mapping;
  const requestMapping = payload?.request?.mapping;
  return (
    snapshot.snapshot_id === snapshot.manifest?.snapshot_id &&
    snapshot.snapshot_sha256 === snapshot.manifest?.snapshot_sha256 &&
    mapping !== undefined &&
    requestMapping !== undefined &&
    structurallyEqual(mapping, requestMapping) &&
    mapping.mapping_id === expected.mapping_id &&
    mapping.mapping_input_sha256 === expected.mapping_input_sha256 &&
    mapping.mapping_version === expected.mapping_version &&
    (expected.family === undefined || mapping.canonical_family === expected.family)
  );
}

export function snapshotMatchesEvaluationReportEvidence(
  snapshot: DataSnapshot,
  reference: SnapshotEvidence,
  report: EvaluationReport,
) {
  const payload = snapshot.manifest?.payload;
  if (!payload || !snapshotMatchesExpectedMapping(snapshot, report)) {
    return false;
  }
  const schemaVersions = payload.schema_bindings.map(
    (binding) => `${binding.dataset_schema_id}:${binding.dataset_schema_version}`,
  );
  return (
    snapshot.snapshot_id === reference.snapshot_id &&
    snapshot.snapshot_sha256 === reference.snapshot_sha256 &&
    payload.adapter.adapter_id === reference.adapter_id &&
    payload.adapter.adapter_version === reference.adapter_version &&
    payload.adapter.provider_id === reference.provider_id &&
    payload.adapter.dataset_id === reference.dataset_id &&
    payload.adapter.product_id === reference.product_id &&
    structurallyEqual(payload.adapter.schema_bindings, payload.schema_bindings) &&
    sameOrderedStrings(schemaVersions, reference.dataset_schema_versions) &&
    payload.configuration.fixture_set_version === reference.fixture_set_version &&
    payload.request.as_of_utc === reference.as_of_utc &&
    payload.request.capability === reference.capability &&
    snapshot.quality_status === reference.quality_status
  );
}

export function snapshotMatchesBlockedOutcomeEvidence(
  snapshot: DataSnapshot,
  reference: BlockedEvaluationOutcome["resolved_snapshots"][number],
  outcome: BlockedEvaluationOutcome,
) {
  const payload = snapshot.manifest?.payload;
  const mapping = payload?.mapping;
  return (
    snapshot.snapshot_id === snapshot.manifest?.snapshot_id &&
    snapshot.snapshot_sha256 === snapshot.manifest?.snapshot_sha256 &&
    snapshot.snapshot_id === reference.snapshot_id &&
    snapshot.snapshot_sha256 === reference.snapshot_sha256 &&
    mapping !== undefined &&
    structurallyEqual(mapping, payload.request?.mapping) &&
    mapping.mapping_id === outcome.mapping_id &&
    mapping.mapping_id === reference.mapping_id &&
    mapping.mapping_input_sha256 === reference.mapping_input_sha256 &&
    mapping.mapping_version === reference.mapping_version
  );
}

export type EvidenceIndex = {
  cards: TradingIdeaCard[];
  mappings: MappingWithRationale[];
  snapshots: DataSnapshot[];
  evaluationReports: EvaluationReport[];
  evaluationOutcomes: BlockedEvaluationOutcome[];
  researchRuns: ResearchRunArtifact[];
  researchRunSummaries: ResearchRunSummary[];
  assessments: ApprovalAssessmentArtifact[];
  assessmentTimelineFailures: Record<string, ApiFailure>;
  assessmentTimelines: Record<string, ApprovalAssessmentEvidenceTimeline>;
  revocations: AuthorizationRevocationArtifact[];
};

export type CardEvidence = {
  assessmentConflicts: ApprovalAssessmentArtifact[];
  evaluationOutcomeConflicts: BlockedEvaluationOutcome[];
  evaluationReportConflicts: EvaluationReport[];
  mappings: MappingWithRationale[];
  mappingConflicts: MappingWithRationale[];
  researchRunConflicts: ResearchRunArtifact[];
  snapshotConflicts: DataSnapshot[];
  snapshots: DataSnapshot[];
  evaluationReports: EvaluationReport[];
  evaluationOutcomes: BlockedEvaluationOutcome[];
  researchRuns: ResearchRunArtifact[];
  researchRunSummaries: ResearchRunSummary[];
  assessments: ApprovalAssessmentArtifact[];
  assessmentTimelineFailures: Record<string, ApiFailure>;
  assessmentTimelines: Record<string, ApprovalAssessmentEvidenceTimeline>;
  revocations: AuthorizationRevocationArtifact[];
};

export type ExactRunEvaluationEvidence = {
  conflict: boolean;
  outcome?: BlockedEvaluationOutcome;
  report?: EvaluationReport;
};

export function evaluationEvidenceForResearchRun(
  index: EvidenceIndex,
  run: ResearchRunArtifact,
): ExactRunEvaluationEvidence {
  const reportId = run.phase5_evaluation.evaluation_report_id;
  const outcomeId = run.phase5_evaluation.evaluation_outcome_id;
  const report = reportId
    ? index.evaluationReports.find(
        (candidate) => evaluationReportMatchesResearchRun(candidate, run),
      )
    : undefined;
  const outcome = outcomeId
    ? index.evaluationOutcomes.find(
        (candidate) => evaluationOutcomeMatchesResearchRun(candidate, run),
      )
    : undefined;

  return {
    conflict: Boolean((reportId && !report) || (outcomeId && !outcome)),
    outcome,
    report,
  };
}

export function snapshotsForResearchRun(
  index: EvidenceIndex,
  run: ResearchRunArtifact,
): { conflict: boolean; snapshots: DataSnapshot[] } {
  const snapshots = (run.snapshot_bindings ?? []).flatMap((binding, bindingIndex) => {
    const snapshot = index.snapshots.find(
      (candidate) =>
        candidate.snapshot_id === binding.snapshot_id &&
        candidate.snapshot_sha256 === binding.snapshot_sha256 &&
        snapshotMatchesExpectedMapping(candidate, run) &&
        binding.mapping_id === run.mapping_id &&
        binding.mapping_input_sha256 === run.mapping_input_sha256 &&
        binding.ordinal === bindingIndex + 1 &&
        binding.as_of_utc === candidate.manifest.payload.request.as_of_utc &&
        binding.capability === candidate.manifest.payload.request.capability &&
        binding.quality_status === candidate.quality_status,
    );
    return snapshot ? [snapshot] : [];
  });
  return {
    conflict: snapshots.length !== (run.snapshot_bindings ?? []).length,
    snapshots,
  };
}

export function emptyEvidenceIndex(): EvidenceIndex {
  return {
    assessments: [],
    assessmentTimelineFailures: {},
    assessmentTimelines: {},
    cards: [],
    evaluationOutcomes: [],
    evaluationReports: [],
    mappings: [],
    researchRuns: [],
    researchRunSummaries: [],
    revocations: [],
    snapshots: [],
  };
}

type AssessmentTimelineHydration = {
  failures: Record<string, ApiFailure>;
  timelines: Record<string, ApprovalAssessmentEvidenceTimeline>;
};

const EVIDENCE_HYDRATION_CONCURRENCY = 4;
type HydrationTask = () => Promise<ApiFailure | undefined>;

function detailSummaryConflict(): ApiFailure {
  return {
    kind: "conflict",
    message: "The detail response conflicts with its immutable list summary.",
    retrySafe: true,
  };
}

function evaluationReportMatchesSummary(
  summary: EvaluationReportSummary,
  detail: EvaluationReport,
) {
  return (
    summary.artifact_id === detail.artifact_id &&
    summary.artifact_sha256 === detail.artifact_sha256 &&
    summary.created_at_utc === detail.created_at_utc &&
    summary.fixture_id === detail.fixture_id &&
    summary.no_real_performance_claimed === detail.no_real_performance_claimed &&
    summary.promotion_state === detail.promotion_state &&
    sameOrderedStrings(summary.reason_codes, detail.reason_codes) &&
    summary.synthetic === detail.synthetic &&
    summary.warning_count === detail.warnings.length
  );
}

function researchRunMatchesSummary(summary: ResearchRunSummary, detail: ResearchRunArtifact) {
  return (
    summary.run_id === detail.run_id &&
    summary.artifact_sha256 === detail.artifact_sha256 &&
    summary.configuration_id === detail.configuration_id &&
    summary.created_at_utc === detail.created_at_utc &&
    summary.family === detail.family &&
    summary.no_real_performance_claimed === detail.no_real_performance_claimed &&
    summary.pass_research_is_not_paper_approval ===
      detail.pass_research_is_not_paper_approval &&
    summary.promotion_state === detail.phase5_evaluation.promotion_state &&
    sameOrderedStrings(summary.reason_codes, detail.reason_codes) &&
    summary.status === detail.status &&
    summary.synthetic === detail.synthetic
  );
}

function assessmentMatchesSummary(
  summary: ApprovalAssessmentSummary,
  detail: ApprovalAssessmentArtifact,
) {
  return (
    summary.assessment_id === detail.assessment_id &&
    summary.artifact_sha256 === detail.artifact_sha256 &&
    summary.created_at_utc === detail.created_at_utc &&
    summary.execution_authorized === detail.execution_authorized &&
    summary.execution_ready === detail.execution_ready &&
    summary.no_personalized_investment_advice ===
      detail.no_personalized_investment_advice &&
    summary.no_real_performance_claimed === detail.no_real_performance_claimed &&
    summary.outcome === detail.outcome &&
    sameOrderedStrings(summary.reason_codes, detail.reason_codes) &&
    summary.research_configuration_id === detail.phase6_lineage.research_configuration_id &&
    summary.research_run_id === detail.research_run_id &&
    summary.simulated_paper_only === detail.simulated_paper_only &&
    summary.synthetic === detail.synthetic
  );
}

function revocationMatchesSummary(
  summary: AuthorizationRevocationSummary,
  detail: AuthorizationRevocationArtifact,
) {
  return (
    summary.revocation_id === detail.revocation_id &&
    summary.artifact_sha256 === detail.artifact_sha256 &&
    summary.created_at_utc === detail.created_at_utc &&
    summary.effective_at_utc === detail.effective_at_utc &&
    summary.execution_authorized === detail.execution_authorized &&
    summary.execution_ready === detail.execution_ready &&
    summary.human_authorization_evidence_id === detail.human_authorization_evidence_id &&
    summary.revocation_evidence_id === detail.revocation_evidence_id &&
    summary.simulated_paper_only === detail.simulated_paper_only &&
    summary.synthetic === detail.synthetic
  );
}

function reconcileAssessmentTimelines(
  assessments: ApprovalAssessmentArtifact[],
  hydration: AssessmentTimelineHydration,
): AssessmentTimelineHydration {
  const failures = { ...hydration.failures };
  const timelines: Record<string, ApprovalAssessmentEvidenceTimeline> = {};

  for (const assessment of assessments) {
    const timeline = hydration.timelines[assessment.assessment_id];
    if (!timeline) continue;
    if (timelineMatchesAssessment(timeline, assessment)) {
      timelines[assessment.assessment_id] = timeline;
      continue;
    }
    failures[assessment.assessment_id] = {
      kind: "conflict",
      message: "The historical timeline conflicts with immutable assessment references.",
      retrySafe: true,
    };
  }

  return { failures, timelines };
}

function failed<T>(error: ApiFailure): ApiResult<T> {
  return { ok: false, error };
}

function abortedFailure(): ApiFailure {
  return {
    kind: "aborted",
    message: "The request was cancelled.",
    retrySafe: true,
  };
}

async function runHydrationQueue(
  tasks: HydrationTask[],
  signal?: AbortSignal,
): Promise<ApiResult<undefined>> {
  let cursor = 0;
  let failure: ApiFailure | undefined;

  const worker = async () => {
    while (!failure) {
      if (signal?.aborted) {
        failure ??= abortedFailure();
        return;
      }
      const taskIndex = cursor;
      cursor += 1;
      if (taskIndex >= tasks.length) return;
      const taskFailure = await tasks[taskIndex]();
      if (taskFailure) failure ??= taskFailure;
    }
  };

  await Promise.all(
    Array.from(
      { length: Math.min(EVIDENCE_HYDRATION_CONCURRENCY, Math.max(tasks.length, 1)) },
      worker,
    ),
  );
  return failure
    ? failed(failure)
    : { data: undefined, ok: true, retrySafe: true, status: 200 };
}

function enqueueDetails<Summary, Detail>(
  tasks: HydrationTask[],
  summaries: Summary[],
  details: Detail[],
  id: (summary: Summary) => string,
  getDetail: (identifier: string) => Promise<ApiResult<Detail>>,
  matchesSummary: (summary: Summary, detail: Detail) => boolean,
): void {
  summaries.forEach((summary, index) => {
    tasks.push(async () => {
      const result = await getDetail(id(summary));
      if (!result.ok) return result.error;
      if (!matchesSummary(summary, result.data)) return detailSummaryConflict();
      details[index] = result.data;
      return undefined;
    });
  });
}

export async function loadEvidenceIndex(signal?: AbortSignal): Promise<ApiResult<EvidenceIndex>> {
  const [
    cardsResult,
    mappingsResult,
    snapshotsResult,
    reportSummariesResult,
    outcomesResult,
    researchSummariesResult,
    assessmentSummariesResult,
    revocationSummariesResult,
  ] = await Promise.all([
    fable5Api.listCards(signal),
    fable5Api.listMappings(signal),
    fable5Api.listSnapshots(signal),
    fable5Api.listEvaluationReports(signal),
    fable5Api.listEvaluationOutcomes(signal),
    fable5Api.listResearchRuns(signal),
    fable5Api.listApprovalAssessments(signal),
    fable5Api.listApprovalRevocations(signal),
  ]);

  if (!cardsResult.ok) return failed(cardsResult.error);
  if (!mappingsResult.ok) return failed(mappingsResult.error);
  if (!snapshotsResult.ok) return failed(snapshotsResult.error);
  if (!reportSummariesResult.ok) return failed(reportSummariesResult.error);
  if (!outcomesResult.ok) return failed(outcomesResult.error);
  if (!researchSummariesResult.ok) return failed(researchSummariesResult.error);
  if (!assessmentSummariesResult.ok) return failed(assessmentSummariesResult.error);
  if (!revocationSummariesResult.ok) return failed(revocationSummariesResult.error);

  const evaluationReports = new Array<EvaluationReport>(reportSummariesResult.data.length);
  const evaluationOutcomes = new Array<BlockedEvaluationOutcome>(outcomesResult.data.length);
  const researchRuns = new Array<ResearchRunArtifact>(researchSummariesResult.data.length);
  const assessments = new Array<ApprovalAssessmentArtifact>(assessmentSummariesResult.data.length);
  const revocations = new Array<AuthorizationRevocationArtifact>(
    revocationSummariesResult.data.length,
  );
  const assessmentTimelineHydration: AssessmentTimelineHydration = {
    failures: {},
    timelines: {},
  };
  const hydrationTasks: HydrationTask[] = [];

  enqueueDetails(
    hydrationTasks,
    reportSummariesResult.data,
    evaluationReports,
    (summary) => summary.artifact_id,
    (artifactId) => fable5Api.getEvaluationReport(artifactId, signal),
    evaluationReportMatchesSummary,
  );
  enqueueDetails(
    hydrationTasks,
    outcomesResult.data,
    evaluationOutcomes,
    (outcome) => outcome.outcome_id,
    (outcomeId) => fable5Api.getEvaluationOutcome(outcomeId, signal),
    structurallyEqual,
  );
  enqueueDetails(
    hydrationTasks,
    researchSummariesResult.data,
    researchRuns,
    (summary) => summary.run_id,
    (runId) => fable5Api.getResearchRun(runId, signal),
    researchRunMatchesSummary,
  );
  enqueueDetails(
    hydrationTasks,
    assessmentSummariesResult.data,
    assessments,
    (summary) => summary.assessment_id,
    (assessmentId) => fable5Api.getApprovalAssessment(assessmentId, signal),
    assessmentMatchesSummary,
  );
  assessmentSummariesResult.data.forEach(({ assessment_id: assessmentId }) => {
    hydrationTasks.push(async () => {
      const result = await fable5Api.getApprovalAssessmentEvidenceTimeline(assessmentId, signal);
      if (result.ok) {
        assessmentTimelineHydration.timelines[assessmentId] = result.data;
      } else if (result.error.kind === "aborted") {
        return result.error;
      } else {
        assessmentTimelineHydration.failures[assessmentId] = result.error;
      }
      return undefined;
    });
  });
  enqueueDetails(
    hydrationTasks,
    revocationSummariesResult.data,
    revocations,
    (summary) => summary.revocation_id,
    (revocationId) => fable5Api.getApprovalRevocation(revocationId, signal),
    revocationMatchesSummary,
  );

  const hydrationResult = await runHydrationQueue(hydrationTasks, signal);
  if (!hydrationResult.ok) return failed(hydrationResult.error);
  const reconciledTimelines = reconcileAssessmentTimelines(
    assessments,
    assessmentTimelineHydration,
  );

  return {
    ok: true,
    data: {
      assessments,
      assessmentTimelineFailures: reconciledTimelines.failures,
      assessmentTimelines: reconciledTimelines.timelines,
      cards: cardsResult.data,
      evaluationOutcomes,
      evaluationReports,
      mappings: mappingsResult.data,
      researchRuns,
      researchRunSummaries: researchSummariesResult.data,
      revocations,
      snapshots: snapshotsResult.data,
    },
    retrySafe: true,
    status: 200,
  };
}

export function evidenceForCard(index: EvidenceIndex, card: TradingIdeaCard): CardEvidence {
  const mappings = index.mappings.filter((mapping) => mappingMatchesCard(mapping, card));
  const mappingConflicts = index.mappings.filter(
    ({ mapping }) => mapping.card_id === card.card_id,
  ).filter((mapping) => !mappingMatchesCard(mapping, card));
  const snapshots = index.snapshots.filter((snapshot) =>
    mappings.some((mapping) => snapshotMatchesMapping(snapshot, mapping)),
  );
  const exactMappingIds = new Set(mappings.map(({ mapping }) => mapping.mapping_id));
  const snapshotConflicts = index.snapshots.filter(
    (snapshot) =>
      exactMappingIds.has(snapshot.manifest.payload.mapping.mapping_id) &&
      !mappings.some((mapping) => snapshotMatchesMapping(snapshot, mapping)),
  );
  const evaluationReports = index.evaluationReports.filter((report) =>
    mappings.some((mapping) => mappingMatchesEvaluationReport(mapping, report)),
  );
  const evaluationReportConflicts = index.evaluationReports.filter(
    (report) =>
      exactMappingIds.has(report.mapping_id) &&
      !mappings.some((mapping) => mappingMatchesEvaluationReport(mapping, report)),
  );
  const evaluationOutcomes = index.evaluationOutcomes.filter((outcome) =>
    mappings.some((mapping) => evaluationOutcomeMatchesMapping(outcome, mapping)),
  );
  const evaluationOutcomeConflicts = index.evaluationOutcomes.filter(
    (outcome) =>
      exactMappingIds.has(outcome.mapping_id) &&
      !mappings.some((mapping) => evaluationOutcomeMatchesMapping(outcome, mapping)),
  );
  const researchRuns = index.researchRuns.filter((run) =>
    mappings.some((mapping) => mappingMatchesResearchRun(mapping, run)),
  );
  const researchRunConflicts = index.researchRuns.filter(
    (run) =>
      exactMappingIds.has(run.mapping_id) &&
      !mappings.some((mapping) => mappingMatchesResearchRun(mapping, run)),
  );
  const researchRunSummaries = index.researchRunSummaries.filter((summary) =>
    researchRuns.some(
      (run) => run.run_id === summary.run_id && run.artifact_sha256 === summary.artifact_sha256,
    ),
  );
  const assessments = index.assessments.filter((assessment) =>
    researchRuns.some((run) => researchRunMatchesAssessment(run, assessment)),
  );
  const exactResearchRunIds = new Set(researchRuns.map((run) => run.run_id));
  const assessmentConflicts = index.assessments.filter(
    (assessment) =>
      exactResearchRunIds.has(assessment.research_run_id) &&
      !researchRuns.some((run) => researchRunMatchesAssessment(run, assessment)),
  );
  const assessmentTimelines = Object.fromEntries(
    assessments.flatMap((assessment) => {
      const timeline = index.assessmentTimelines[assessment.assessment_id];
      return timeline ? [[assessment.assessment_id, timeline]] : [];
    }),
  );
  const assessmentTimelineFailures = Object.fromEntries(
    assessments.flatMap((assessment) => {
      const failure = index.assessmentTimelineFailures[assessment.assessment_id];
      return failure ? [[assessment.assessment_id, failure]] : [];
    }),
  );
  const revocations = index.revocations.filter(
    (revocation) =>
      assessments.some((assessment) => revocationMatchesAssessment(revocation, assessment)),
  );

  return {
    assessmentConflicts,
    assessments,
    assessmentTimelineFailures,
    assessmentTimelines,
    evaluationOutcomeConflicts,
    evaluationOutcomes,
    evaluationReportConflicts,
    evaluationReports,
    mappings,
    mappingConflicts,
    researchRunConflicts,
    researchRuns,
    researchRunSummaries,
    revocations,
    snapshotConflicts,
    snapshots,
  };
}

export function useEvidenceIndex(): RemoteState<EvidenceIndex> {
  const [reloadVersion, setReloadVersion] = useState(0);
  const [value, setValue] = useState<RemoteValue<EvidenceIndex>>({
    message: "Loading immutable evidence...",
    retrySafe: true,
    status: "loading",
  });

  const reload = useCallback(() => {
    setValue({
      message: "Loading immutable evidence...",
      retrySafe: true,
      status: "loading",
    });
    setReloadVersion((version) => version + 1);
  }, []);

  useEffect(() => {
    const controller = new AbortController();

    void loadEvidenceIndex(controller.signal).then((result) => {
      if (!result.ok) {
        if (result.error.kind !== "aborted") {
          setValue({
            error: result.error,
            retrySafe: result.error.retrySafe,
            status: "error",
          });
        }
        return;
      }

      const count =
        result.data.cards.length +
        result.data.mappings.length +
        result.data.snapshots.length +
        result.data.evaluationReports.length +
        result.data.evaluationOutcomes.length +
        result.data.researchRuns.length +
        result.data.assessments.length +
        result.data.revocations.length +
        Object.keys(result.data.assessmentTimelines).length +
        Object.keys(result.data.assessmentTimelineFailures).length;
      if (count === 0) {
        setValue({
          message: "No persisted Phase 2-7 evidence is available.",
          retrySafe: true,
          status: "empty",
        });
        return;
      }

      setValue({ data: result.data, retrySafe: true, status: "success" });
    });

    return () => controller.abort();
  }, [reloadVersion]);

  return useMemo(() => ({ ...value, reload }), [reload, value]);
}
