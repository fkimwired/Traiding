import type { components, paths } from "./api.generated";

type EvaluationPolicyCreateRequest = components["schemas"]["EvaluationPolicyCreateRequest"];
type EvaluationRunCreateRequest = components["schemas"]["EvaluationRunCreateRequest"];
type FrozenEvaluationPolicy = components["schemas"]["FrozenEvaluationPolicy"];
type EvaluationReport = components["schemas"]["EvaluationReport"];
type EvaluationReportSummary = components["schemas"]["EvaluationReportSummary"];
type EvaluationBlockedResult = components["schemas"]["EvaluationBlockedResult"];
type BlockedEvaluationOutcome = components["schemas"]["BlockedEvaluationOutcome"];
type EvaluationValidationErrorResponse =
  components["schemas"]["EvaluationValidationErrorResponse"];

type CreatePolicy = paths["/v1/evaluation-policies"]["post"];
type ListPolicies = paths["/v1/evaluation-policies"]["get"];
type GetPolicy = paths["/v1/evaluation-policies/{policy_id}/versions/{policy_version}"]["get"];
type CreateReport = paths["/v1/evaluation-reports"]["post"];
type ListReports = paths["/v1/evaluation-reports"]["get"];
type GetReport = paths["/v1/evaluation-reports/{artifact_id}"]["get"];
type ListOutcomes = paths["/v1/evaluation-outcomes"]["get"];
type GetOutcome = paths["/v1/evaluation-outcomes/{outcome_id}"]["get"];

const policyRequest: EvaluationPolicyCreateRequest = {
  policy_id: "b4e2146e-f1da-5c15-ada2-01bfd61ead9e",
  policy_version: 1,
};

const runRequest: EvaluationRunCreateRequest = {
  policy_id: policyRequest.policy_id,
  policy_version: policyRequest.policy_version,
  mapping_id: "aaaaaaaa-aaaa-5aaa-8aaa-aaaaaaaaaaaa",
  snapshot_ids: ["bbbbbbbb-bbbb-5bbb-8bbb-bbbbbbbbbbbb"],
  fixture_id: "phase5-deterministic-research-ledger-v1",
};

const clientSuppliedVerdict: EvaluationRunCreateRequest = {
  ...runRequest,
  // @ts-expect-error Promotion outcomes are derived only by the server evaluator.
  promotion_state: "PASS_RESEARCH",
};

const clientSuppliedMetrics: EvaluationRunCreateRequest = {
  ...runRequest,
  // @ts-expect-error Metrics and performance results are never client-authoritative.
  metrics: [],
};

type Expect<Value extends true> = Value;
type Equal<Left, Right> =
  (<Type>() => Type extends Left ? 1 : 2) extends
  (<Type>() => Type extends Right ? 1 : 2)
    ? true
    : false;

type PolicyBody = NonNullable<CreatePolicy["requestBody"]>["content"]["application/json"];
type Policy201 = CreatePolicy["responses"][201]["content"]["application/json"];
type Policy422 = CreatePolicy["responses"][422]["content"]["application/json"];
type PolicyList200 = ListPolicies["responses"][200]["content"]["application/json"];
type PolicyGet200 = GetPolicy["responses"][200]["content"]["application/json"];
type ReportBody = NonNullable<CreateReport["requestBody"]>["content"]["application/json"];
type Report201 = CreateReport["responses"][201]["content"]["application/json"];
type Report422 = CreateReport["responses"][422]["content"]["application/json"];
type ReportList200 = ListReports["responses"][200]["content"]["application/json"];
type ReportGet200 = GetReport["responses"][200]["content"]["application/json"];
type OutcomeList200 = ListOutcomes["responses"][200]["content"]["application/json"];
type OutcomeGet200 = GetOutcome["responses"][200]["content"]["application/json"];

type PolicyBodyIsIdentityOnly = Expect<Equal<PolicyBody, EvaluationPolicyCreateRequest>>;
type PolicyCreateIsFrozen = Expect<Equal<Policy201, FrozenEvaluationPolicy>>;
type PolicyBlockedIsTyped = Expect<
  Equal<Policy422, EvaluationBlockedResult | EvaluationValidationErrorResponse>
>;
type PolicyListIsFrozen = Expect<Equal<PolicyList200, FrozenEvaluationPolicy[]>>;
type PolicyGetIsFrozen = Expect<Equal<PolicyGet200, FrozenEvaluationPolicy>>;
type ReportBodyIsIdentityOnly = Expect<Equal<ReportBody, EvaluationRunCreateRequest>>;
type ReportCreateIsComplete = Expect<Equal<Report201, EvaluationReport>>;
type ReportBlockedIsTyped = Expect<
  Equal<Report422, BlockedEvaluationOutcome | EvaluationValidationErrorResponse>
>;
type ReportListIsSummary = Expect<Equal<ReportList200, EvaluationReportSummary[]>>;
type ReportGetIsComplete = Expect<Equal<ReportGet200, EvaluationReport>>;
type OutcomeListIsImmutable = Expect<Equal<OutcomeList200, BlockedEvaluationOutcome[]>>;
type OutcomeGetIsImmutable = Expect<Equal<OutcomeGet200, BlockedEvaluationOutcome>>;

declare const report: EvaluationReport;
const allGates = report.gates;
const auditHash: string = report.config_hash;
const isSynthetic: true = report.synthetic;
const noRealPerformance: true = report.no_real_performance_claimed;
const notPaperApproval: true = report.pass_research_is_not_paper_approval;
const sampleLineageHash: string = report.sample_lineage_sha256;
const returnStatuses: components["schemas"]["ResearchReturnStatus"][] =
  report.trials[0]?.return_statuses ?? [];

void [
  policyRequest,
  runRequest,
  clientSuppliedVerdict,
  clientSuppliedMetrics,
  allGates,
  auditHash,
  isSynthetic,
  noRealPerformance,
  notPaperApproval,
  sampleLineageHash,
  returnStatuses,
];

export type {
  PolicyBlockedIsTyped,
  PolicyBodyIsIdentityOnly,
  PolicyCreateIsFrozen,
  PolicyGetIsFrozen,
  PolicyListIsFrozen,
  OutcomeGetIsImmutable,
  OutcomeListIsImmutable,
  ReportBlockedIsTyped,
  ReportBodyIsIdentityOnly,
  ReportCreateIsComplete,
  ReportGetIsComplete,
  ReportListIsSummary,
};
