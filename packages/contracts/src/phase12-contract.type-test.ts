import type { components, paths } from "./api.generated";
import type { SuccessfulJsonResponseByOperation } from "./runtime.generated";

type ReadinessArtifact = components["schemas"]["PaperShadowReadinessArtifact"];
type ReadinessConflict =
  components["schemas"]["PaperShadowReadinessConflictErrorResponse"];
type ReadinessNotFound =
  components["schemas"]["PaperShadowReadinessNotFoundErrorResponse"];
type ReadinessValidation =
  components["schemas"]["PaperShadowReadinessValidationErrorResponse"];
type ReadinessPath =
  paths["/v1/paper-shadow-readiness/{readiness_assessment_id}"];
type GetReadiness = ReadinessPath["get"];

type Expect<Value extends true> = Value;
type Equal<Left, Right> =
  (<Type>() => Type extends Left ? 1 : 2) extends
  (<Type>() => Type extends Right ? 1 : 2)
    ? true
    : false;

type ExactPathIdentity = Expect<
  Equal<GetReadiness["parameters"]["path"], { readiness_assessment_id: string }>
>;
type NoQuery = Expect<Equal<GetReadiness["parameters"]["query"], undefined>>;
type NoRequestBody = Expect<Equal<GetReadiness["requestBody"], undefined>>;
type GetReturnsReadiness = Expect<
  Equal<
    GetReadiness["responses"][200]["content"]["application/json"],
    ReadinessArtifact
  >
>;
type GetNotFoundIsTyped = Expect<
  Equal<
    GetReadiness["responses"][404]["content"]["application/json"],
    ReadinessNotFound
  >
>;
type GetConflictIsTyped = Expect<
  Equal<
    GetReadiness["responses"][409]["content"]["application/json"],
    ReadinessConflict
  >
>;
type GetValidationIsTyped = Expect<
  Equal<
    GetReadiness["responses"][422]["content"]["application/json"],
    ReadinessValidation
  >
>;
type GetOperationBinding = Expect<
  Equal<
    SuccessfulJsonResponseByOperation[
      "GET /v1/paper-shadow-readiness/{readiness_assessment_id}"
    ],
    ReadinessArtifact
  >
>;
type ExactOutcome = Expect<
  Equal<
    ReadinessArtifact["outcome"],
    "MOCK_PROOF_COMPLETE" | "SHADOW_READY" | "BLOCKED"
  >
>;
type NoPost = Expect<Equal<ReadinessPath["post"], undefined>>;
type NoPut = Expect<Equal<ReadinessPath["put"], undefined>>;
type NoPatch = Expect<Equal<ReadinessPath["patch"], undefined>>;
type NoDelete = Expect<Equal<ReadinessPath["delete"], undefined>>;

declare const readiness: ReadinessArtifact;
const submissionForbidden: false = readiness.order_submission_authorized;
const strategyForbidden: false = readiness.strategy_execution_eligible;
const livePathAbsent: true = readiness.live_path_absent;
const clientSuppliedOrder: ReadinessArtifact = {
  ...readiness,
  // @ts-expect-error Readiness evidence carries no order instruction.
  side: "BUY",
};
const clientSuppliedCredential: ReadinessArtifact = {
  ...readiness,
  // @ts-expect-error Credentials never enter the generated API contract.
  api_key: "forbidden",
};

void [
  submissionForbidden,
  strategyForbidden,
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
  GetReturnsReadiness,
  GetValidationIsTyped,
  NoDelete,
  NoPatch,
  NoPost,
  NoPut,
  NoQuery,
  NoRequestBody,
};
