import type { components, paths } from "./api.generated";
import type { SuccessfulJsonResponseByOperation } from "./runtime.generated";

type ResearchIngestionEligibilityArtifact =
  components["schemas"]["ResearchIngestionEligibilityArtifact"];
type EligibilityConflict =
  components["schemas"]["ResearchIngestionEligibilityConflictErrorResponse"];
type EligibilityNotFound =
  components["schemas"]["ResearchIngestionEligibilityNotFoundErrorResponse"];
type EligibilityValidation =
  components["schemas"]["ResearchIngestionEligibilityValidationErrorResponse"];
type EligibilityPath =
  paths["/v1/research-ingestion-eligibility/{assessment_id}"];
type GetEligibility = EligibilityPath["get"];

type Expect<Value extends true> = Value;
type Equal<Left, Right> =
  (<Type>() => Type extends Left ? 1 : 2) extends
  (<Type>() => Type extends Right ? 1 : 2)
    ? true
    : false;

type ExactPathIdentity = Expect<
  Equal<GetEligibility["parameters"]["path"], { assessment_id: string }>
>;
type NoQuery = Expect<Equal<GetEligibility["parameters"]["query"], undefined>>;
type NoRequestBody = Expect<Equal<GetEligibility["requestBody"], undefined>>;
type GetReturnsEligibility = Expect<
  Equal<
    GetEligibility["responses"][200]["content"]["application/json"],
    ResearchIngestionEligibilityArtifact
  >
>;
type GetNotFoundIsTyped = Expect<
  Equal<
    GetEligibility["responses"][404]["content"]["application/json"],
    EligibilityNotFound
  >
>;
type GetConflictIsTyped = Expect<
  Equal<
    GetEligibility["responses"][409]["content"]["application/json"],
    EligibilityConflict
  >
>;
type GetValidationIsTyped = Expect<
  Equal<
    GetEligibility["responses"][422]["content"]["application/json"],
    EligibilityValidation
  >
>;
type GetOperationBinding = Expect<
  Equal<
    SuccessfulJsonResponseByOperation[
      "GET /v1/research-ingestion-eligibility/{assessment_id}"
    ],
    ResearchIngestionEligibilityArtifact
  >
>;
type ExactOutcome = Expect<
  Equal<
    ResearchIngestionEligibilityArtifact["outcome"],
    "MOCK_PROOF_COMPLETE" | "BLOCKED"
  >
>;
type NoPost = Expect<Equal<EligibilityPath["post"], undefined>>;
type NoPut = Expect<Equal<EligibilityPath["put"], undefined>>;
type NoPatch = Expect<Equal<EligibilityPath["patch"], undefined>>;
type NoDelete = Expect<Equal<EligibilityPath["delete"], undefined>>;

declare const eligibility: ResearchIngestionEligibilityArtifact;
const ingestionForbidden: false = eligibility.research_ingestion_authorized;
const snapshotForbidden: false = eligibility.research_snapshot_created;
const researchForbidden: false = eligibility.research_run_authorized;
const performanceForbidden: false = eligibility.performance_computed;
const promotionForbidden: false = eligibility.strategy_promotion_authorized;
const executionForbidden: false = eligibility.execution_authorized;
const submissionForbidden: false = eligibility.order_submission_authorized;
const livePathAbsent: true = eligibility.live_path_absent;
const clientSuppliedObservation: ResearchIngestionEligibilityArtifact = {
  ...eligibility,
  // @ts-expect-error Eligibility evidence carries no provider observation.
  observation_value: "forbidden",
};
const clientSuppliedOrder: ResearchIngestionEligibilityArtifact = {
  ...eligibility,
  // @ts-expect-error Eligibility evidence carries no order instruction.
  side: "BUY",
};

void [
  ingestionForbidden,
  snapshotForbidden,
  researchForbidden,
  performanceForbidden,
  promotionForbidden,
  executionForbidden,
  submissionForbidden,
  livePathAbsent,
  clientSuppliedObservation,
  clientSuppliedOrder,
];

export type {
  ExactOutcome,
  ExactPathIdentity,
  GetConflictIsTyped,
  GetNotFoundIsTyped,
  GetOperationBinding,
  GetReturnsEligibility,
  GetValidationIsTyped,
  NoDelete,
  NoPatch,
  NoPost,
  NoPut,
  NoQuery,
  NoRequestBody,
};
