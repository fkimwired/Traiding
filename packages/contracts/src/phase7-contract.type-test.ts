import type { components, paths } from "./api.generated";

type ApprovalAssessmentCreateRequest =
  components["schemas"]["ApprovalAssessmentCreateRequest"];
type ApprovalRevocationCreateRequest =
  components["schemas"]["ApprovalRevocationCreateRequest"];
type ApprovalAssessmentArtifact =
  components["schemas"]["ApprovalAssessmentArtifact"];
type ApprovalAssessmentSummary =
  components["schemas"]["ApprovalAssessmentSummary"];
type AuthorizationRevocationArtifact =
  components["schemas"]["AuthorizationRevocationArtifact"];
type AuthorizationRevocationSummary =
  components["schemas"]["AuthorizationRevocationSummary"];
type ApprovalValidationErrorResponse =
  components["schemas"]["ApprovalValidationErrorResponse"];
type ApprovalAssessmentOutcome =
  components["schemas"]["ApprovalAssessmentOutcome"];

type CreateAssessment = paths["/v1/approval-assessments"]["post"];
type ListAssessments = paths["/v1/approval-assessments"]["get"];
type GetAssessment = paths["/v1/approval-assessments/{assessment_id}"]["get"];
type CreateRevocation = paths["/v1/approval-revocations"]["post"];
type ListRevocations = paths["/v1/approval-revocations"]["get"];
type GetRevocation = paths["/v1/approval-revocations/{revocation_id}"]["get"];

const assessmentRequest: ApprovalAssessmentCreateRequest = {
  research_run_id: "aaaaaaaa-aaaa-5aaa-8aaa-aaaaaaaaaaaa",
  approval_policy_version_id: "bbbbbbbb-bbbb-5bbb-8bbb-bbbbbbbbbbbb",
  approval_scope_version_id: "cccccccc-cccc-5ccc-8ccc-cccccccccccc",
  human_authorization_evidence_id: "dddddddd-dddd-5ddd-8ddd-dddddddddddd",
  risk_input_id: "eeeeeeee-eeee-5eee-8eee-eeeeeeeeeeee",
};

const revocationRequest: ApprovalRevocationCreateRequest = {
  human_authorization_evidence_id: "dddddddd-dddd-5ddd-8ddd-dddddddddddd",
  revocation_evidence_id: "ffffffff-ffff-5fff-8fff-ffffffffffff",
};

const clientSuppliedApproval: ApprovalAssessmentCreateRequest = {
  ...assessmentRequest,
  // @ts-expect-error Approval is a server-computed assessment outcome.
  approval: "APPROVED_PAPER",
};

const clientSuppliedVerdict: ApprovalAssessmentCreateRequest = {
  ...assessmentRequest,
  // @ts-expect-error Phase 6 promotion state is resolved from the immutable research artifact.
  promotion_state: "PASS_RESEARCH",
};

const clientSuppliedHash: ApprovalAssessmentCreateRequest = {
  ...assessmentRequest,
  // @ts-expect-error Artifact hashes are derived from server-resolved immutable evidence.
  artifact_sha256: "0".repeat(64),
};

const clientSuppliedThresholds: ApprovalAssessmentCreateRequest = {
  ...assessmentRequest,
  // @ts-expect-error Risk thresholds come from the separately versioned server policy.
  thresholds: {},
};

const clientSuppliedTimestamp: ApprovalAssessmentCreateRequest = {
  ...assessmentRequest,
  // @ts-expect-error Assessment timestamps are server-owned UTC values.
  created_at_utc: "2026-07-14T00:00:00Z",
};

const clientSuppliedRiskResult: ApprovalAssessmentCreateRequest = {
  ...assessmentRequest,
  // @ts-expect-error Risk results are computed from the immutable risk input and policy.
  risk_results: [],
};

const clientSuppliedExpiry: ApprovalAssessmentCreateRequest = {
  ...assessmentRequest,
  // @ts-expect-error Expiry is resolved from immutable policy/scope/authorization evidence.
  expires_at_utc: "2026-07-15T00:00:00Z",
};

const clientSuppliedPhase6Metrics: ApprovalAssessmentCreateRequest = {
  ...assessmentRequest,
  // @ts-expect-error Phase 6 metrics are copied only from the exact persisted artifact lineage.
  phase6_metrics: {},
};

const clientSuppliedRevocationState: ApprovalRevocationCreateRequest = {
  ...revocationRequest,
  // @ts-expect-error Revocation state is derived from human-controlled server evidence.
  revoked: true,
};

type Expect<Value extends true> = Value;
type Equal<Left, Right> =
  (<Type>() => Type extends Left ? 1 : 2) extends
  (<Type>() => Type extends Right ? 1 : 2)
    ? true
    : false;

type AssessmentRequestFieldsAreReferencesOnly = Expect<
  Equal<
    keyof ApprovalAssessmentCreateRequest,
    | "research_run_id"
    | "approval_policy_version_id"
    | "approval_scope_version_id"
    | "human_authorization_evidence_id"
    | "risk_input_id"
  >
>;
type RevocationRequestFieldsAreReferencesOnly = Expect<
  Equal<
    keyof ApprovalRevocationCreateRequest,
    "human_authorization_evidence_id" | "revocation_evidence_id"
  >
>;
type ExactAssessmentOutcome = Expect<
  Equal<ApprovalAssessmentOutcome, "APPROVED_PAPER" | "FAIL_REJECT">
>;

type AssessmentBody =
  NonNullable<CreateAssessment["requestBody"]>["content"]["application/json"];
type Assessment201 = CreateAssessment["responses"][201]["content"]["application/json"];
type Assessment422 = CreateAssessment["responses"][422]["content"]["application/json"];
type AssessmentList200 =
  ListAssessments["responses"][200]["content"]["application/json"];
type AssessmentList422 =
  ListAssessments["responses"][422]["content"]["application/json"];
type AssessmentGet200 =
  GetAssessment["responses"][200]["content"]["application/json"];
type AssessmentGet422 =
  GetAssessment["responses"][422]["content"]["application/json"];
type RevocationBody =
  NonNullable<CreateRevocation["requestBody"]>["content"]["application/json"];
type Revocation201 = CreateRevocation["responses"][201]["content"]["application/json"];
type Revocation422 = CreateRevocation["responses"][422]["content"]["application/json"];
type RevocationList200 =
  ListRevocations["responses"][200]["content"]["application/json"];
type RevocationList422 =
  ListRevocations["responses"][422]["content"]["application/json"];
type RevocationGet200 =
  GetRevocation["responses"][200]["content"]["application/json"];
type RevocationGet422 =
  GetRevocation["responses"][422]["content"]["application/json"];

type AssessmentBodyIsReferenceOnly = Expect<
  Equal<AssessmentBody, ApprovalAssessmentCreateRequest>
>;
type AssessmentReturnsArtifact = Expect<Equal<Assessment201, ApprovalAssessmentArtifact>>;
type AssessmentValidationIsTyped = Expect<
  Equal<Assessment422, ApprovalValidationErrorResponse>
>;
type AssessmentListReturnsSummaries = Expect<
  Equal<AssessmentList200, ApprovalAssessmentSummary[]>
>;
type AssessmentListValidationIsTyped = Expect<
  Equal<AssessmentList422, ApprovalValidationErrorResponse>
>;
type AssessmentGetReturnsArtifact = Expect<
  Equal<AssessmentGet200, ApprovalAssessmentArtifact>
>;
type AssessmentGetValidationIsTyped = Expect<
  Equal<AssessmentGet422, ApprovalValidationErrorResponse>
>;
type RevocationBodyIsReferenceOnly = Expect<
  Equal<RevocationBody, ApprovalRevocationCreateRequest>
>;
type RevocationReturnsArtifact = Expect<
  Equal<Revocation201, AuthorizationRevocationArtifact>
>;
type RevocationValidationIsTyped = Expect<
  Equal<Revocation422, ApprovalValidationErrorResponse>
>;
type RevocationListReturnsSummaries = Expect<
  Equal<RevocationList200, AuthorizationRevocationSummary[]>
>;
type RevocationListValidationIsTyped = Expect<
  Equal<RevocationList422, ApprovalValidationErrorResponse>
>;
type RevocationGetReturnsArtifact = Expect<
  Equal<RevocationGet200, AuthorizationRevocationArtifact>
>;
type RevocationGetValidationIsTyped = Expect<
  Equal<RevocationGet422, ApprovalValidationErrorResponse>
>;

declare const assessment: ApprovalAssessmentArtifact;
const syntheticAssessment: true = assessment.synthetic;
const simulatedPaperOnlyAssessment: true = assessment.simulated_paper_only;
const assessmentDoesNotAuthorizeExecution: false = assessment.execution_authorized;
const assessmentDoesNotClaimExecutionReadiness: false = assessment.execution_ready;
const assessmentIsNotAdvice: true = assessment.no_personalized_investment_advice;
const assessmentClaimsNoRealPerformance: true = assessment.no_real_performance_claimed;
const completePhase6Lineage = assessment.phase6_lineage;
const exactOrderedChecks = assessment.checks;

declare const revocation: AuthorizationRevocationArtifact;
const syntheticRevocation: true = revocation.synthetic;
const simulatedPaperOnlyRevocation: true = revocation.simulated_paper_only;
const revocationDoesNotAuthorizeExecution: false = revocation.execution_authorized;
const revocationDoesNotClaimExecutionReadiness: false = revocation.execution_ready;
const revocationIsNotAdvice: true = revocation.no_personalized_investment_advice;
const revocationClaimsNoRealPerformance: true = revocation.no_real_performance_claimed;

type NoAssessmentUpdate = Expect<
  Equal<paths["/v1/approval-assessments/{assessment_id}"]["put"], undefined>
>;
type NoAssessmentPatch = Expect<
  Equal<paths["/v1/approval-assessments/{assessment_id}"]["patch"], undefined>
>;
type NoAssessmentDelete = Expect<
  Equal<paths["/v1/approval-assessments/{assessment_id}"]["delete"], undefined>
>;
type NoRevocationUpdate = Expect<
  Equal<paths["/v1/approval-revocations/{revocation_id}"]["put"], undefined>
>;
type NoRevocationPatch = Expect<
  Equal<paths["/v1/approval-revocations/{revocation_id}"]["patch"], undefined>
>;
type NoRevocationDelete = Expect<
  Equal<paths["/v1/approval-revocations/{revocation_id}"]["delete"], undefined>
>;

void [
  assessmentRequest,
  revocationRequest,
  clientSuppliedApproval,
  clientSuppliedVerdict,
  clientSuppliedHash,
  clientSuppliedThresholds,
  clientSuppliedTimestamp,
  clientSuppliedRiskResult,
  clientSuppliedExpiry,
  clientSuppliedPhase6Metrics,
  clientSuppliedRevocationState,
  syntheticAssessment,
  simulatedPaperOnlyAssessment,
  assessmentDoesNotAuthorizeExecution,
  assessmentDoesNotClaimExecutionReadiness,
  assessmentIsNotAdvice,
  assessmentClaimsNoRealPerformance,
  completePhase6Lineage,
  exactOrderedChecks,
  syntheticRevocation,
  simulatedPaperOnlyRevocation,
  revocationDoesNotAuthorizeExecution,
  revocationDoesNotClaimExecutionReadiness,
  revocationIsNotAdvice,
  revocationClaimsNoRealPerformance,
];

export type {
  AssessmentBodyIsReferenceOnly,
  AssessmentGetReturnsArtifact,
  AssessmentGetValidationIsTyped,
  AssessmentListReturnsSummaries,
  AssessmentListValidationIsTyped,
  AssessmentRequestFieldsAreReferencesOnly,
  AssessmentReturnsArtifact,
  AssessmentValidationIsTyped,
  ExactAssessmentOutcome,
  NoAssessmentDelete,
  NoAssessmentPatch,
  NoAssessmentUpdate,
  NoRevocationDelete,
  NoRevocationPatch,
  NoRevocationUpdate,
  RevocationBodyIsReferenceOnly,
  RevocationGetReturnsArtifact,
  RevocationGetValidationIsTyped,
  RevocationListReturnsSummaries,
  RevocationListValidationIsTyped,
  RevocationRequestFieldsAreReferencesOnly,
  RevocationReturnsArtifact,
  RevocationValidationIsTyped,
};
