import type { components } from "@fable5/contracts";

import blockedAssessmentFixture from "./fixtures/phase10-blocked-assessment.json";
import blockedFixture from "./fixtures/phase10-blocked.json";
import completedFixture from "./fixtures/phase10-completed.json";
import sourceAssessmentFixture from "./fixtures/phase10-source-assessment.json";
import syntheticCardFixture from "./fixtures/phase10-synthetic-card.json";

export type ApprovalAssessmentArtifact = components["schemas"]["ApprovalAssessmentArtifact"];
export type ApprovalAssessmentEvidenceTimeline =
  components["schemas"]["ApprovalAssessmentEvidenceTimeline"];
export type ApprovalAssessmentSummary = components["schemas"]["ApprovalAssessmentSummary"];
export type PaperSimulationArtifact = components["schemas"]["PaperSimulationArtifact"];
export type PaperSimulationSummary = components["schemas"]["PaperSimulationSummary"];
export type TradingIdeaCard = components["schemas"]["TradingIdeaCard"];

export const phase10SourceAssessment =
  sourceAssessmentFixture as unknown as ApprovalAssessmentArtifact;
export const phase10BlockedAssessment =
  blockedAssessmentFixture as unknown as ApprovalAssessmentArtifact;
export const phase10SyntheticCard = syntheticCardFixture as unknown as TradingIdeaCard;
export const phase10CompletedArtifact = completedFixture as unknown as PaperSimulationArtifact;
export const phase10BlockedArtifact = blockedFixture as unknown as PaperSimulationArtifact;

export const PHASE10_COMPLETED_RUN_ID = phase10CompletedArtifact.simulation_run_id;
export const PHASE10_BLOCKED_RUN_ID = phase10BlockedArtifact.simulation_run_id;
export const PHASE10_COMPLETED_IDEMPOTENCY_KEY =
  phase10CompletedArtifact.simulation_idempotency_key;
export const PHASE10_SOURCE_ASSESSMENT_ID = phase10CompletedArtifact.source_assessment_id;

export function phase10AssessmentSummaryFor(
  artifact: ApprovalAssessmentArtifact,
): ApprovalAssessmentSummary {
  return {
    artifact_sha256: artifact.artifact_sha256,
    assessment_id: artifact.assessment_id,
    created_at_utc: artifact.created_at_utc,
    execution_authorized: artifact.execution_authorized,
    execution_ready: artifact.execution_ready,
    no_personalized_investment_advice: artifact.no_personalized_investment_advice,
    no_real_performance_claimed: artifact.no_real_performance_claimed,
    outcome: artifact.outcome,
    reason_codes: artifact.reason_codes,
    research_configuration_id: artifact.phase6_lineage.research_configuration_id,
    research_run_id: artifact.research_run_id,
    simulated_paper_only: artifact.simulated_paper_only,
    synthetic: artifact.synthetic,
  };
}

export function phase10TimelineFor(
  artifact: ApprovalAssessmentArtifact,
): ApprovalAssessmentEvidenceTimeline {
  return {
    assessment_created_at_utc: artifact.created_at_utc,
    assessment_id: artifact.assessment_id,
    authorization: {
      authorization_sha256: artifact.authorization_sha256,
      authorized_at_utc: "2026-07-14T11:00:00Z",
      expires_at_utc: "2026-07-15T12:00:00Z",
      human_authorization_evidence_id: artifact.human_authorization_evidence_id,
      review_at_utc: "2026-07-15T00:00:00Z",
    },
    policy: {
      approval_policy_version_id: artifact.approval_policy_version_id,
      expires_at_utc: "2026-07-21T12:00:00Z",
      policy_sha256: artifact.approval_policy_sha256,
      valid_from_utc: "2026-07-07T12:00:00Z",
    },
    risk_input: {
      observed_at_utc: "2026-07-14T11:55:00Z",
      risk_input_id: artifact.risk_input_id,
      risk_input_sha256: artifact.risk_input_sha256,
    },
    scope: {
      approval_scope_version_id: artifact.approval_scope_version_id,
      expires_at_utc: "2026-07-16T12:00:00Z",
      scope_sha256: artifact.approval_scope_sha256,
      valid_from_utc: "2026-07-12T12:00:00Z",
    },
  };
}

export function phase10SummaryFor(artifact: PaperSimulationArtifact): PaperSimulationSummary {
  return {
    artifact_sha256: artifact.artifact_sha256,
    configuration_id: artifact.configuration.configuration_id,
    created_at_utc: artifact.created_at_utc,
    decision_time_utc: artifact.decision_time_utc,
    external_submission: artifact.external_submission,
    live_path_absent: artifact.live_path_absent,
    local_mock_only: artifact.local_mock_only,
    no_personalized_investment_advice: artifact.no_personalized_investment_advice,
    no_real_performance_claimed: artifact.no_real_performance_claimed,
    outcome: artifact.outcome,
    reason_codes: artifact.reason_codes,
    simulated_paper_only: artifact.simulated_paper_only,
    simulation_run_id: artifact.simulation_run_id,
    source_assessment_id: artifact.source_assessment_id,
    synthetic: artifact.synthetic,
    transition_assessment_id: artifact.transition_assessment_id,
  };
}
