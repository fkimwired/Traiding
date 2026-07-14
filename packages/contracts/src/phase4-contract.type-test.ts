import type { components, paths } from "./api.generated";

type SnapshotCreateRequest = components["schemas"]["SnapshotCreateRequest"];
type DataSnapshot = components["schemas"]["DataSnapshot"];
type SnapshotBundle = components["schemas"]["SnapshotBundle"];
type AdapterUnavailableResult = components["schemas"]["AdapterUnavailableResult"];
type AdapterProfile = components["schemas"]["AdapterProfile"];
type SnapshotBuildBlockedResult = components["schemas"]["SnapshotBuildBlockedResult"];
type SnapshotRequestError = components["schemas"]["SnapshotRequestError"];
type SnapshotValidationErrorResponse = components["schemas"]["SnapshotValidationErrorResponse"];
type CreateSnapshotOperation = paths["/v1/data-snapshots"]["post"];
type ListSnapshotsOperation = paths["/v1/data-snapshots"]["get"];
type GetSnapshotOperation = paths["/v1/data-snapshots/{snapshot_id}"]["get"];

const createRequest: SnapshotCreateRequest = {
  mapping_id: "aaaaaaaa-aaaa-5aaa-8aaa-aaaaaaaaaaaa",
  as_of_utc: "2021-01-01T00:00:00Z",
  capability: "ohlcv",
  mock_configuration_id: "phase4-synthetic-default-v1",
};

const clientSuppliedAuthority: SnapshotCreateRequest = {
  ...createRequest,
  // @ts-expect-error Family authorization is resolved from the persisted Phase 3 mapping.
  canonical_family: "A_CROSS_SECTIONAL_EQUITY_RANKING",
};

const clientSuppliedRecords: SnapshotCreateRequest = {
  ...createRequest,
  // @ts-expect-error Snapshot observations are resolved by the server-owned adapter.
  observations: [],
};

const optionsRequest: SnapshotCreateRequest = {
  ...createRequest,
  // @ts-expect-error Options data is outside the Phase 4 capability vocabulary.
  capability: "options",
};

const unavailable: AdapterUnavailableResult = {
  status: "unavailable",
  reason_code: "credentials_unavailable",
  capability: "ohlcv",
  provider_id: "synthetic-test-provider",
  adapter_id: "phase4-synthetic-pit-adapter",
  adapter_version: "phase4-synthetic-pit-adapter-v1",
  dataset_id: "phase4-synthetic-pit-fixtures",
  product_id: "phase4-synthetic-product",
  entitlement_id: "phase4-synthetic-test-fixture-rights-v1",
  use_rights_id: "phase4-synthetic-test-fixture-rights-v1",
  sanitized_message: "credentials unavailable before transport initialization",
};

const invalidUnavailableStatus: AdapterUnavailableResult = {
  ...unavailable,
  // @ts-expect-error Adapter-unavailable results cannot claim an available status.
  status: "available",
};

type Expect<Value extends true> = Value;
type Equal<Left, Right> =
  (<Type>() => Type extends Left ? 1 : 2) extends
  (<Type>() => Type extends Right ? 1 : 2)
    ? true
    : false;

type CreateBody = NonNullable<CreateSnapshotOperation["requestBody"]>["content"]["application/json"];
type Create201 = CreateSnapshotOperation["responses"][201]["content"]["application/json"];
type Create422 = CreateSnapshotOperation["responses"][422]["content"]["application/json"];
type Create503 = CreateSnapshotOperation["responses"][503]["content"]["application/json"];
type List200 = ListSnapshotsOperation["responses"][200]["content"]["application/json"];
type Get200 = GetSnapshotOperation["responses"][200]["content"]["application/json"];

type CreateBodyIsRequest = Expect<Equal<CreateBody, SnapshotCreateRequest>>;
type AdapterSyntheticIsRequiredBoolean = Expect<Equal<AdapterProfile["synthetic"], boolean>>;
type CreateReturnsBundle = Expect<Equal<Create201, SnapshotBundle>>;
type Create422IsTyped = Expect<
  Equal<
    Create422,
    SnapshotBuildBlockedResult | SnapshotRequestError | SnapshotValidationErrorResponse
  >
>;
type CreateCanReturnUnavailable = Expect<Equal<Create503, AdapterUnavailableResult>>;
type ListReturnsSnapshots = Expect<Equal<List200, DataSnapshot[]>>;
type GetReturnsBundle = Expect<Equal<Get200, SnapshotBundle>>;

declare const bundle: SnapshotBundle;
declare const snapshot: DataSnapshot;
const bundleHash: string = bundle.snapshot.snapshot_sha256;
const manifestAsOf: string = snapshot.manifest.payload.request.as_of_utc;
const rawLineageCount: number = bundle.raw_observations.length;

void [
  createRequest,
  clientSuppliedAuthority,
  clientSuppliedRecords,
  optionsRequest,
  unavailable,
  invalidUnavailableStatus,
  bundleHash,
  manifestAsOf,
  rawLineageCount,
];

export type {
  AdapterSyntheticIsRequiredBoolean,
  CreateBodyIsRequest,
  Create422IsTyped,
  CreateCanReturnUnavailable,
  CreateReturnsBundle,
  GetReturnsBundle,
  ListReturnsSnapshots,
};
