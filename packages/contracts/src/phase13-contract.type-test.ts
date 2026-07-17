import type { components, paths } from "./api.generated";
import type { SuccessfulJsonResponseByOperation } from "./runtime.generated";

type PointInTimeQualificationArtifact =
  components["schemas"]["PointInTimeQualificationArtifact"];
type QualificationConflict =
  components["schemas"]["PointInTimeQualificationConflictErrorResponse"];
type QualificationNotFound =
  components["schemas"]["PointInTimeQualificationNotFoundErrorResponse"];
type QualificationValidation =
  components["schemas"]["PointInTimeQualificationValidationErrorResponse"];
type QualificationPath =
  paths["/v1/point-in-time-data-qualifications/{qualification_id}"];
type GetQualification = QualificationPath["get"];

type Expect<Value extends true> = Value;
type Equal<Left, Right> =
  (<Type>() => Type extends Left ? 1 : 2) extends
  (<Type>() => Type extends Right ? 1 : 2)
    ? true
    : false;

type ExactPathIdentity = Expect<
  Equal<GetQualification["parameters"]["path"], { qualification_id: string }>
>;
type NoQuery = Expect<Equal<GetQualification["parameters"]["query"], undefined>>;
type NoRequestBody = Expect<Equal<GetQualification["requestBody"], undefined>>;
type GetReturnsQualification = Expect<
  Equal<
    GetQualification["responses"][200]["content"]["application/json"],
    PointInTimeQualificationArtifact
  >
>;
type GetNotFoundIsTyped = Expect<
  Equal<
    GetQualification["responses"][404]["content"]["application/json"],
    QualificationNotFound
  >
>;
type GetConflictIsTyped = Expect<
  Equal<
    GetQualification["responses"][409]["content"]["application/json"],
    QualificationConflict
  >
>;
type GetValidationIsTyped = Expect<
  Equal<
    GetQualification["responses"][422]["content"]["application/json"],
    QualificationValidation
  >
>;
type GetOperationBinding = Expect<
  Equal<
    SuccessfulJsonResponseByOperation[
      "GET /v1/point-in-time-data-qualifications/{qualification_id}"
    ],
    PointInTimeQualificationArtifact
  >
>;
type ExactOutcome = Expect<
  Equal<
    PointInTimeQualificationArtifact["outcome"],
    "MOCK_PROOF_COMPLETE" | "EXTERNAL_SAMPLE_QUALIFIED" | "BLOCKED"
  >
>;
type NoPost = Expect<Equal<QualificationPath["post"], undefined>>;
type NoPut = Expect<Equal<QualificationPath["put"], undefined>>;
type NoPatch = Expect<Equal<QualificationPath["patch"], undefined>>;
type NoDelete = Expect<Equal<QualificationPath["delete"], undefined>>;

declare const qualification: PointInTimeQualificationArtifact;
const researchDataForbidden: false = qualification.research_data_eligible;
const promotionForbidden: false = qualification.strategy_promotion_authorized;
const strategyForbidden: false = qualification.strategy_execution_eligible;
const executionForbidden: false = qualification.execution_authorized;
const submissionForbidden: false = qualification.order_submission_authorized;
const livePathAbsent: true = qualification.live_path_absent;
const clientSuppliedOrder: PointInTimeQualificationArtifact = {
  ...qualification,
  // @ts-expect-error Qualification evidence carries no order instruction.
  side: "BUY",
};
const clientSuppliedCredential: PointInTimeQualificationArtifact = {
  ...qualification,
  // @ts-expect-error Credentials never enter the generated API contract.
  api_token: "forbidden",
};

void [
  researchDataForbidden,
  promotionForbidden,
  strategyForbidden,
  executionForbidden,
  submissionForbidden,
  livePathAbsent,
  clientSuppliedOrder,
  clientSuppliedCredential,
];

export type {
  ExactOutcome,
  ExactPathIdentity,
  GetConflictIsTyped,
  GetNotFoundIsTyped,
  GetOperationBinding,
  GetReturnsQualification,
  GetValidationIsTyped,
  NoDelete,
  NoPatch,
  NoPost,
  NoPut,
  NoQuery,
  NoRequestBody,
};
