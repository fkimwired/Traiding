import type { components, paths } from "./api.generated";
import type { SuccessfulJsonResponseByOperation } from "./runtime.generated";

type PaperSimulationCreateRequest = components["schemas"]["PaperSimulationCreateRequest"];
type PaperSimulationArtifact = components["schemas"]["PaperSimulationArtifact"];
type PaperSimulationSummary = components["schemas"]["PaperSimulationSummary"];
type PaperSimulationOutcome = components["schemas"]["PaperSimulationOutcome"];
type PaperSimulationConflictErrorResponse =
  components["schemas"]["PaperSimulationConflictErrorResponse"];
type PaperSimulationNotFoundErrorResponse =
  components["schemas"]["PaperSimulationNotFoundErrorResponse"];
type PaperSimulationValidationErrorResponse =
  components["schemas"]["PaperSimulationValidationErrorResponse"];

type ListSimulations = paths["/v1/local-simulations"]["get"];
type CreateSimulation = paths["/v1/local-simulations"]["post"];
type GetSimulation = paths["/v1/local-simulations/{simulation_run_id}"]["get"];

const request: PaperSimulationCreateRequest = {
  approval_assessment_id: "10000000-0000-4000-8000-000000000001",
  simulation_idempotency_key: "phase10-deterministic-request-001",
};

const clientSuppliedQuantity: PaperSimulationCreateRequest = {
  ...request,
  // @ts-expect-error Quantity is derived from immutable server-side research evidence.
  quantity: "10",
};

const clientSuppliedSide: PaperSimulationCreateRequest = {
  ...request,
  // @ts-expect-error Side is derived from the immutable signal rule, never supplied by the UI.
  side: "BUY",
};

const clientSuppliedEntity: PaperSimulationCreateRequest = {
  ...request,
  // @ts-expect-error The synthetic entity is fixed by the local mock configuration.
  entity_id: "SYNTHETIC-ASSET-001",
};

const clientSuppliedPrice: PaperSimulationCreateRequest = {
  ...request,
  // @ts-expect-error Prices are resolved from the immutable mock snapshot.
  reference_price: "100.00",
};

const clientSuppliedOutcome: PaperSimulationCreateRequest = {
  ...request,
  // @ts-expect-error Outcome is computed by the authoritative simulation service.
  outcome: "SIMULATED_COMPLETE",
};

const clientSuppliedRouting: PaperSimulationCreateRequest = {
  ...request,
  // @ts-expect-error External routing is absent and cannot be requested.
  broker: "example",
};

type Expect<Value extends true> = Value;
type Equal<Left, Right> =
  (<Type>() => Type extends Left ? 1 : 2) extends
  (<Type>() => Type extends Right ? 1 : 2)
    ? true
    : false;

type RequestFieldsAreReferencesOnly = Expect<
  Equal<
    keyof PaperSimulationCreateRequest,
    "approval_assessment_id" | "simulation_idempotency_key"
  >
>;
type ExactOutcome = Expect<
  Equal<PaperSimulationOutcome, "SIMULATED_COMPLETE" | "BLOCKED">
>;

type CreateBody =
  NonNullable<CreateSimulation["requestBody"]>["content"]["application/json"];
type Create201 = CreateSimulation["responses"][201]["content"]["application/json"];
type Create404 = CreateSimulation["responses"][404]["content"]["application/json"];
type Create409 = CreateSimulation["responses"][409]["content"]["application/json"];
type Create422 = CreateSimulation["responses"][422]["content"]["application/json"];
type List200 = ListSimulations["responses"][200]["content"]["application/json"];
type List409 = ListSimulations["responses"][409]["content"]["application/json"];
type List422 = ListSimulations["responses"][422]["content"]["application/json"];
type ListQuery = NonNullable<ListSimulations["parameters"]["query"]>;
type Get200 = GetSimulation["responses"][200]["content"]["application/json"];
type Get404 = GetSimulation["responses"][404]["content"]["application/json"];
type Get409 = GetSimulation["responses"][409]["content"]["application/json"];
type Get422 = GetSimulation["responses"][422]["content"]["application/json"];

type CreateBodyIsReferenceOnly = Expect<Equal<CreateBody, PaperSimulationCreateRequest>>;
type CreateReturnsArtifact = Expect<Equal<Create201, PaperSimulationArtifact>>;
type CreateNotFoundIsTyped = Expect<Equal<Create404, PaperSimulationNotFoundErrorResponse>>;
type CreateConflictIsTyped = Expect<Equal<Create409, PaperSimulationConflictErrorResponse>>;
type CreateValidationIsTyped = Expect<
  Equal<Create422, PaperSimulationValidationErrorResponse>
>;
type ListReturnsSummaries = Expect<Equal<List200, PaperSimulationSummary[]>>;
type ListConflictIsTyped = Expect<Equal<List409, PaperSimulationConflictErrorResponse>>;
type ListValidationIsTyped = Expect<
  Equal<List422, PaperSimulationValidationErrorResponse>
>;
type ListFilterIsAssessmentReference = Expect<
  Equal<ListQuery["approval_assessment_id"], string | null | undefined>
>;
type GetReturnsArtifact = Expect<Equal<Get200, PaperSimulationArtifact>>;
type GetNotFoundIsTyped = Expect<Equal<Get404, PaperSimulationNotFoundErrorResponse>>;
type GetConflictIsTyped = Expect<Equal<Get409, PaperSimulationConflictErrorResponse>>;
type GetValidationIsTyped = Expect<Equal<Get422, PaperSimulationValidationErrorResponse>>;

type ListOperationBinding = Expect<
  Equal<
    SuccessfulJsonResponseByOperation["GET /v1/local-simulations"],
    PaperSimulationSummary[]
  >
>;
type CreateOperationBinding = Expect<
  Equal<
    SuccessfulJsonResponseByOperation["POST /v1/local-simulations"],
    PaperSimulationArtifact
  >
>;
type GetOperationBinding = Expect<
  Equal<
    SuccessfulJsonResponseByOperation["GET /v1/local-simulations/{simulation_run_id}"],
    PaperSimulationArtifact
  >
>;

declare const artifact: PaperSimulationArtifact;
const simulatedPaperOnly: true = artifact.simulated_paper_only;
const localMockOnly: true = artifact.local_mock_only;
const synthetic: true = artifact.synthetic;
const externalRoutingAbsent: true = artifact.external_routing_absent;
const externalSubmission: false = artifact.external_submission;
const livePathAbsent: true = artifact.live_path_absent;
const noPersonalizedAdvice: true = artifact.no_personalized_investment_advice;
const noRealPerformanceClaimed: true = artifact.no_real_performance_claimed;

type NoCollectionUpdate = Expect<
  Equal<paths["/v1/local-simulations"]["put"], undefined>
>;
type NoCollectionPatch = Expect<
  Equal<paths["/v1/local-simulations"]["patch"], undefined>
>;
type NoCollectionDelete = Expect<
  Equal<paths["/v1/local-simulations"]["delete"], undefined>
>;
type NoArtifactUpdate = Expect<
  Equal<paths["/v1/local-simulations/{simulation_run_id}"]["put"], undefined>
>;
type NoArtifactPatch = Expect<
  Equal<paths["/v1/local-simulations/{simulation_run_id}"]["patch"], undefined>
>;
type NoArtifactDelete = Expect<
  Equal<paths["/v1/local-simulations/{simulation_run_id}"]["delete"], undefined>
>;

void [
  request,
  clientSuppliedQuantity,
  clientSuppliedSide,
  clientSuppliedEntity,
  clientSuppliedPrice,
  clientSuppliedOutcome,
  clientSuppliedRouting,
  simulatedPaperOnly,
  localMockOnly,
  synthetic,
  externalRoutingAbsent,
  externalSubmission,
  livePathAbsent,
  noPersonalizedAdvice,
  noRealPerformanceClaimed,
];

export type {
  CreateBodyIsReferenceOnly,
  CreateConflictIsTyped,
  CreateNotFoundIsTyped,
  CreateOperationBinding,
  CreateReturnsArtifact,
  CreateValidationIsTyped,
  ExactOutcome,
  GetOperationBinding,
  GetConflictIsTyped,
  GetNotFoundIsTyped,
  GetReturnsArtifact,
  GetValidationIsTyped,
  ListFilterIsAssessmentReference,
  ListConflictIsTyped,
  ListOperationBinding,
  ListReturnsSummaries,
  ListValidationIsTyped,
  NoArtifactDelete,
  NoArtifactPatch,
  NoArtifactUpdate,
  NoCollectionDelete,
  NoCollectionPatch,
  NoCollectionUpdate,
  RequestFieldsAreReferencesOnly,
};
