import type { components } from "@fable5/contracts";

import type { EvidenceIndex } from "../lib/evidence-index";

export const rejectedAssessmentId = "10000000-0000-4000-8000-000000000001";
export const approvedAssessmentId = "10000000-0000-4000-8000-000000000002";
export const rejectedResearchRunId = "20000000-0000-4000-8000-000000000001";
export const approvedResearchRunId = "20000000-0000-4000-8000-000000000002";
export const policyId = "30000000-0000-4000-8000-000000000001";
export const scopeId = "40000000-0000-4000-8000-000000000001";
export const rejectedAuthorizationId = "50000000-0000-4000-8000-000000000001";
export const approvedAuthorizationId = "50000000-0000-4000-8000-000000000002";
export const riskInputId = "60000000-0000-4000-8000-000000000001";
export const revocationId = "70000000-0000-4000-8000-000000000001";
export const revocationEvidenceId = "80000000-0000-4000-8000-000000000001";

const hash = (value: string) => value.repeat(64);

const rejectedChecks = [
  {
    check_sha256: hash("1"),
    code: "RESEARCH_PASS",
    evidence_sha256s: [hash("a")],
    observed_value: "FAIL_RESEARCH",
    ordinal: 1,
    reason_code: "research_prerequisite_not_passed",
    status: "FAIL",
    threshold_value: "PASS_RESEARCH",
  },
  {
    check_sha256: hash("2"),
    code: "POLICY_CURRENT",
    evidence_sha256s: [hash("b")],
    observed_value: "historical_false",
    ordinal: 2,
    reason_code: "policy_expired",
    status: "BLOCKED",
    threshold_value: "historical_true",
  },
  {
    check_sha256: hash("3"),
    code: "REVOCATION_CLEAR",
    evidence_sha256s: [hash("c")],
    observed_value: "revoked",
    ordinal: 3,
    reason_code: "authorization_revoked",
    status: "FAIL",
    threshold_value: "clear",
  },
] as EvidenceIndex["assessments"][number]["checks"];

export const rejectedAssessment = {
  approval_policy_sha256: hash("a"),
  approval_policy_version_id: policyId,
  approval_scope_sha256: hash("b"),
  approval_scope_version_id: scopeId,
  artifact_schema_version: "phase7-approval-assessment-v1",
  artifact_sha256: hash("c"),
  assessment_id: rejectedAssessmentId,
  authorization_sha256: hash("d"),
  checks: rejectedChecks,
  created_at_utc: "2026-07-14T12:00:00Z",
  currentness_state_sha256: hash("e"),
  disclaimer:
    "Synthetic simulated-paper governance evidence only; no order, execution readiness, real performance claim, or investment advice.",
  execution_authorized: false,
  execution_ready: false,
  human_authorization_evidence_id: rejectedAuthorizationId,
  no_personalized_investment_advice: true,
  no_real_performance_claimed: true,
  outcome: "FAIL_REJECT",
  phase6_lineage: { research_configuration_id: "phase6-a-pass-v2" },
  phase7_code_version_git_sha: "f".repeat(40),
  reason_codes: [
    "authorization_revoked",
    "policy_expired",
    "research_prerequisite_not_passed",
  ],
  request_fingerprint_sha256: hash("1"),
  research_run_id: rejectedResearchRunId,
  revocation_ids: [revocationId],
  revocation_set_sha256: hash("2"),
  risk_input_id: riskInputId,
  risk_input_sha256: hash("3"),
  simulated_paper_only: true,
  synthetic: true,
} as EvidenceIndex["assessments"][number];

export const approvedAssessment = {
  ...rejectedAssessment,
  artifact_sha256: hash("4"),
  assessment_id: approvedAssessmentId,
  authorization_sha256: hash("5"),
  checks: rejectedChecks.map((check) => ({
    ...check,
    observed_value: "historical_true",
    reason_code: "check_passed",
    status: "PASS" as const,
  })),
  created_at_utc: "2026-07-14T12:05:00Z",
  human_authorization_evidence_id: approvedAuthorizationId,
  outcome: "APPROVED_PAPER",
  reason_codes: ["all_approval_and_risk_checks_passed"],
  research_run_id: approvedResearchRunId,
  revocation_ids: [],
} as EvidenceIndex["assessments"][number];

export const revocation = {
  artifact_schema_version: "phase7-authorization-revocation-v1",
  artifact_sha256: hash("6"),
  authorization_sha256: rejectedAssessment.authorization_sha256,
  created_at_utc: "2026-07-14T13:01:00Z",
  effective_at_utc: "2026-07-14T13:00:00Z",
  execution_authorized: false,
  execution_ready: false,
  human_authorization_evidence_id: rejectedAuthorizationId,
  no_personalized_investment_advice: true,
  no_real_performance_claimed: true,
  phase7_code_version_git_sha: "f".repeat(40),
  reason: "Synthetic authorization was withdrawn.",
  request_fingerprint_sha256: hash("7"),
  revocation_evidence_id: revocationEvidenceId,
  revocation_evidence_sha256: hash("8"),
  revocation_id: revocationId,
  revoked_by: "synthetic-governance-fixture",
  simulated_paper_only: true,
  synthetic: true,
} as EvidenceIndex["revocations"][number];

function timeline(
  assessmentId: string,
  authorizationId: string,
  authorizationSha256: string,
): components["schemas"]["ApprovalAssessmentEvidenceTimeline"] {
  return {
    assessment_created_at_utc:
      assessmentId === rejectedAssessmentId ? "2026-07-14T12:00:00Z" : "2026-07-14T12:05:00Z",
    assessment_id: assessmentId,
    authorization: {
      authorization_sha256: authorizationSha256,
      authorized_at_utc: "2026-07-14T11:00:00Z",
      expires_at_utc: "2026-07-15T12:00:00Z",
      human_authorization_evidence_id: authorizationId,
      review_at_utc: "2026-07-15T00:00:00Z",
    },
    policy: {
      approval_policy_version_id: policyId,
      expires_at_utc: "2026-07-21T12:00:00Z",
      policy_sha256: rejectedAssessment.approval_policy_sha256,
      valid_from_utc: "2026-07-07T12:00:00Z",
    },
    risk_input: {
      observed_at_utc: "2026-07-14T11:55:00Z",
      risk_input_id: riskInputId,
      risk_input_sha256: rejectedAssessment.risk_input_sha256,
    },
    scope: {
      approval_scope_version_id: scopeId,
      expires_at_utc: "2026-07-16T12:00:00Z",
      scope_sha256: rejectedAssessment.approval_scope_sha256,
      valid_from_utc: "2026-07-12T12:00:00Z",
    },
  };
}

export const governanceIndex = {
  assessmentTimelineFailures: {},
  assessmentTimelines: {
    [approvedAssessmentId]: timeline(
      approvedAssessmentId,
      approvedAuthorizationId,
      approvedAssessment.authorization_sha256,
    ),
    [rejectedAssessmentId]: timeline(
      rejectedAssessmentId,
      rejectedAuthorizationId,
      rejectedAssessment.authorization_sha256,
    ),
  },
  assessments: [approvedAssessment, rejectedAssessment],
  cards: [],
  evaluationOutcomes: [],
  evaluationReports: [],
  mappings: [],
  researchRunSummaries: [],
  researchRuns: [],
  revocations: [revocation],
  snapshots: [],
} satisfies EvidenceIndex;
