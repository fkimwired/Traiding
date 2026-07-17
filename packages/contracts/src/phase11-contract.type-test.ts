import type { components, paths } from "./api.generated";
import type { SuccessfulJsonResponseByOperation } from "./runtime.generated";

type LocalSimulationEvidenceBundle =
  components["schemas"]["LocalSimulationEvidenceBundle"];
type PaperSimulationArtifact = components["schemas"]["PaperSimulationArtifact"];
type PaperSimulationConflictErrorResponse =
  components["schemas"]["PaperSimulationConflictErrorResponse"];
type PaperSimulationNotFoundErrorResponse =
  components["schemas"]["PaperSimulationNotFoundErrorResponse"];
type PaperSimulationValidationErrorResponse =
  components["schemas"]["PaperSimulationValidationErrorResponse"];
type EvidencePath = paths["/v1/local-simulations/{simulation_run_id}/evidence-bundle"];
type GetEvidence = EvidencePath["get"];

type Expect<Value extends true> = Value;
type Equal<Left, Right> =
  (<Type>() => Type extends Left ? 1 : 2) extends
  (<Type>() => Type extends Right ? 1 : 2)
    ? true
    : false;

type ExactBundleFields = Expect<
  Equal<
    keyof LocalSimulationEvidenceBundle,
    | "bundle_schema_version"
    | "bundle_sha256"
    | "simulation_run_id"
    | "simulation_artifact_sha256"
    | "simulation"
  >
>;
type ExactSchemaLiteral = Expect<
  Equal<
    LocalSimulationEvidenceBundle["bundle_schema_version"],
    "phase11-local-simulation-evidence-bundle-v1"
  >
>;
type FullNestedArtifact = Expect<
  Equal<LocalSimulationEvidenceBundle["simulation"], PaperSimulationArtifact>
>;
type ExactPathIdentity = Expect<
  Equal<GetEvidence["parameters"]["path"], { simulation_run_id: string }>
>;
type NoQuery = Expect<Equal<GetEvidence["parameters"]["query"], undefined>>;
type NoRequestBody = Expect<Equal<GetEvidence["requestBody"], undefined>>;
type GetReturnsBundle = Expect<
  Equal<
    GetEvidence["responses"][200]["content"]["application/json"],
    LocalSimulationEvidenceBundle
  >
>;
type GetNotFoundIsTyped = Expect<
  Equal<
    GetEvidence["responses"][404]["content"]["application/json"],
    PaperSimulationNotFoundErrorResponse
  >
>;
type GetConflictIsTyped = Expect<
  Equal<
    GetEvidence["responses"][409]["content"]["application/json"],
    PaperSimulationConflictErrorResponse
  >
>;
type GetValidationIsTyped = Expect<
  Equal<
    GetEvidence["responses"][422]["content"]["application/json"],
    PaperSimulationValidationErrorResponse
  >
>;
type GetOperationBinding = Expect<
  Equal<
    SuccessfulJsonResponseByOperation[
      "GET /v1/local-simulations/{simulation_run_id}/evidence-bundle"
    ],
    LocalSimulationEvidenceBundle
  >
>;
type NoPost = Expect<Equal<EvidencePath["post"], undefined>>;
type NoPut = Expect<Equal<EvidencePath["put"], undefined>>;
type NoPatch = Expect<Equal<EvidencePath["patch"], undefined>>;
type NoDelete = Expect<Equal<EvidencePath["delete"], undefined>>;

declare const bundle: LocalSimulationEvidenceBundle;
const schemaLiteral: "phase11-local-simulation-evidence-bundle-v1" =
  bundle.bundle_schema_version;
const nestedArtifact: PaperSimulationArtifact = bundle.simulation;
const clientSuppliedReplay: LocalSimulationEvidenceBundle = {
  ...bundle,
  // @ts-expect-error A portable evidence bundle carries no replay instruction.
  replay: true,
};
const clientSuppliedSignature: LocalSimulationEvidenceBundle = {
  ...bundle,
  // @ts-expect-error The deterministic digest is not a signature.
  signature: "forbidden",
};

void [schemaLiteral, nestedArtifact, clientSuppliedReplay, clientSuppliedSignature];

export type {
  ExactBundleFields,
  ExactPathIdentity,
  ExactSchemaLiteral,
  FullNestedArtifact,
  GetConflictIsTyped,
  GetNotFoundIsTyped,
  GetOperationBinding,
  GetReturnsBundle,
  GetValidationIsTyped,
  NoDelete,
  NoPatch,
  NoPost,
  NoPut,
  NoQuery,
  NoRequestBody,
};
