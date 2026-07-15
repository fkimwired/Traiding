import {
  type components,
  type paths,
  type SuccessfulJsonOperation,
  type SuccessfulJsonResponseByOperation,
  validateOpenApiResponse,
} from "@fable5/contracts";

export type ApiFailureKind =
  | "aborted"
  | "conflict"
  | "malformed"
  | "not-found"
  | "unavailable"
  | "validation";

export type ApiFailure = {
  kind: ApiFailureKind;
  message: string;
  retrySafe: boolean;
  status?: number;
};

export type ApiResult<T> =
  | { ok: true; data: T; retrySafe: boolean; status: number }
  | { ok: false; error: ApiFailure };

type RemoteValue<T> =
  | { status: "loading"; message: string; retrySafe: true }
  | { status: "empty"; message: string; retrySafe: true }
  | { status: "success"; data: T; retrySafe: true }
  | { status: "error"; error: ApiFailure; retrySafe: boolean };

export type RemoteState<T> = RemoteValue<T> & { reload: () => void };

type RequestOptions = {
  body?: unknown;
  pathParameters?: Readonly<Record<string, string | number>>;
  queryParameters?: Readonly<Record<string, string | number | null | undefined>>;
  retrySafe: boolean;
  signal?: AbortSignal;
};

type GetOperation = Extract<SuccessfulJsonOperation, `GET ${string}`>;
type PostOperation = Extract<SuccessfulJsonOperation, `POST ${string}`>;

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
export const API_REQUEST_TIMEOUT_MS = 60_000;

function composedRequestSignal(parentSignal?: AbortSignal) {
  const controller = new AbortController();
  let timedOut = false;
  const forwardAbort = () => controller.abort();

  if (parentSignal?.aborted) {
    forwardAbort();
  } else {
    parentSignal?.addEventListener("abort", forwardAbort, { once: true });
  }

  const timeoutId = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, API_REQUEST_TIMEOUT_MS);

  return {
    cleanup: () => {
      clearTimeout(timeoutId);
      parentSignal?.removeEventListener("abort", forwardAbort);
    },
    signal: controller.signal,
    timedOut: () => timedOut,
  };
}

function failureForStatus(status: number, retrySafe: boolean): ApiFailure {
  if (status === 409) {
    return {
      kind: "conflict",
      message: "The request conflicts with immutable persisted evidence.",
      retrySafe,
      status,
    };
  }

  if (status === 422) {
    return {
      kind: "validation",
      message: "The server rejected one or more request references or values.",
      retrySafe: false,
      status,
    };
  }

  if (status === 404) {
    return {
      kind: "not-found",
      message: "The referenced immutable record is unavailable.",
      retrySafe,
      status,
    };
  }

  return {
    kind: "unavailable",
    message:
      status === 503
        ? "The required deterministic service or adapter is unavailable."
        : "The API is unavailable for this request.",
    retrySafe,
    status,
  };
}

function operationRequest(
  operation: SuccessfulJsonOperation,
  pathParameters: Readonly<Record<string, string | number>> = {},
) {
  const separator = operation.indexOf(" ");
  const method = operation.slice(0, separator) as "GET" | "POST";
  const template = operation.slice(separator + 1);
  const used = new Set<string>();
  const path = template.replace(/\{([^}]+)\}/g, (_placeholder, name: string) => {
    const value = pathParameters[name];
    if (value === undefined) throw new Error(`Missing generated path parameter ${name}.`);
    used.add(name);
    return encodeURIComponent(String(value));
  });
  if (Object.keys(pathParameters).some((name) => !used.has(name))) {
    throw new Error("Unexpected generated path parameter.");
  }
  return { method, path };
}

async function requestJson<Operation extends SuccessfulJsonOperation>(
  operation: Operation,
  options: RequestOptions,
): Promise<ApiResult<SuccessfulJsonResponseByOperation[Operation]>> {
  const requestSignal = composedRequestSignal(options.signal);
  try {
    const { method, path } = operationRequest(operation, options.pathParameters);
    const request: RequestInit = { signal: requestSignal.signal };
    if (method === "POST") {
      request.method = "POST";
      if (options.body !== undefined) {
        request.body = JSON.stringify(options.body);
        request.headers = { "Content-Type": "application/json" };
      }
    }
    const response = await fetch(`${apiUrl}${path}${query(options.queryParameters ?? {})}`, request);

    if (!response.ok) {
      return { ok: false, error: failureForStatus(response.status, options.retrySafe) };
    }

    let body: unknown;
    try {
      body = await response.json();
    } catch (error) {
      if (
        requestSignal.timedOut() ||
        (error instanceof Error && error.name === "AbortError")
      ) {
        throw error;
      }
      return {
        ok: false,
        error: {
          kind: "malformed",
          message: "The API returned malformed JSON.",
          retrySafe: options.retrySafe,
          status: response.status,
        },
      };
    }

    if (!validateOpenApiResponse(operation, response.status, body)) {
      return {
        ok: false,
        error: {
          kind: "malformed",
          message: `The API response for ${operation} did not match its generated-contract schema.`,
          retrySafe: options.retrySafe,
          status: response.status,
        },
      };
    }

    return {
      ok: true,
      data: body as SuccessfulJsonResponseByOperation[Operation],
      retrySafe: options.retrySafe,
      status: response.status,
    };
  } catch (error) {
    if (requestSignal.timedOut()) {
      return {
        ok: false,
        error: {
          kind: "unavailable",
          message: "The API request timed out before deterministic evidence was available.",
          retrySafe: options.retrySafe,
        },
      };
    }

    if (error instanceof Error && error.name === "AbortError") {
      return {
        ok: false,
        error: {
          kind: "aborted",
          message: "The request was cancelled.",
          retrySafe: true,
        },
      };
    }

    return {
      ok: false,
      error: {
        kind: "unavailable",
        message: "The API could not be reached.",
        retrySafe: options.retrySafe,
      },
    };
  } finally {
    requestSignal.cleanup();
  }
}

function getJson<Operation extends GetOperation>(
  operation: Operation,
  options: Omit<RequestOptions, "body" | "retrySafe"> = {},
) {
  return requestJson(operation, {
    ...options,
    retrySafe: true,
  });
}

function postJson<Operation extends PostOperation>(
  operation: Operation,
  options: Omit<RequestOptions, "retrySafe"> & { retrySafe?: boolean },
) {
  return requestJson(operation, {
    ...options,
    retrySafe: options.retrySafe ?? true,
  });
}

function query(parameters: Readonly<Record<string, string | number | null | undefined>>) {
  const values = new URLSearchParams();
  Object.entries(parameters).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== "") {
      values.set(key, String(value));
    }
  });
  const encoded = values.toString();
  return encoded.length > 0 ? `?${encoded}` : "";
}

export function apiHref(path: string) {
  return `${apiUrl}${path}`;
}

type SourceIntakeRequest = NonNullable<
  paths["/v1/sources"]["post"]["requestBody"]
>["content"]["application/json"];
type SourceCorrectionRequest = NonNullable<
  paths["/v1/sources/{source_id}/versions"]["post"]["requestBody"]
>["content"]["application/json"];
type SnapshotCreateRequest = NonNullable<
  paths["/v1/data-snapshots"]["post"]["requestBody"]
>["content"]["application/json"];
type EvaluationPolicyCreateRequest = components["schemas"]["EvaluationPolicyCreateRequest"];
type EvaluationRunCreateRequest = components["schemas"]["EvaluationRunCreateRequest"];
type ResearchRunCreateRequest = components["schemas"]["ResearchRunCreateRequest"];
type ApprovalAssessmentCreateRequest = components["schemas"]["ApprovalAssessmentCreateRequest"];
type ApprovalRevocationCreateRequest = components["schemas"]["ApprovalRevocationCreateRequest"];

export const fable5Api = {
  getHealth: (signal?: AbortSignal) => getJson("GET /health", { signal }),
  listSources: (signal?: AbortSignal, limit?: number) =>
    getJson("GET /v1/sources", { queryParameters: { limit }, signal }),
  createSource: (body: SourceIntakeRequest, signal?: AbortSignal) =>
    postJson("POST /v1/sources", {
      body,
      retrySafe: Boolean(body.ingest_idempotency_key),
      signal,
    }),
  getSource: (sourceId: string, signal?: AbortSignal) =>
    getJson("GET /v1/sources/{source_id}", {
      pathParameters: { source_id: sourceId },
      signal,
    }),
  addSourceVersion: (sourceId: string, body: SourceCorrectionRequest, signal?: AbortSignal) =>
    postJson("POST /v1/sources/{source_id}/versions", {
      body,
      pathParameters: { source_id: sourceId },
      signal,
    }),
  getSourceVersion: (sourceVersionId: string, signal?: AbortSignal) =>
    getJson("GET /v1/source-versions/{source_version_id}", {
      pathParameters: { source_version_id: sourceVersionId },
      signal,
    }),
  listExtractions: (signal?: AbortSignal, limit?: number) =>
    getJson("GET /v1/extractions", {
      queryParameters: { limit },
      signal,
    }),
  createExtraction: (sourceVersionId: string, signal?: AbortSignal) =>
    postJson("POST /v1/source-versions/{source_version_id}/extractions", {
      pathParameters: { source_version_id: sourceVersionId },
      signal,
    }),
  getExtraction: (requestId: string, signal?: AbortSignal) =>
    getJson("GET /v1/extractions/{request_id}", {
      pathParameters: { request_id: requestId },
      signal,
    }),
  listCards: (signal?: AbortSignal, limit?: number) =>
    getJson("GET /v1/cards", { queryParameters: { limit }, signal }),
  getCard: (cardId: string, signal?: AbortSignal) =>
    getJson("GET /v1/cards/{card_id}", {
      pathParameters: { card_id: cardId },
      signal,
    }),
  getMemo: (cardId: string, signal?: AbortSignal) =>
    getJson("GET /v1/cards/{card_id}/memo", {
      pathParameters: { card_id: cardId },
      signal,
    }),
  listMappings: (signal?: AbortSignal, cardId?: string, limit?: number) =>
    getJson("GET /v1/mappings", {
      queryParameters: { card_id: cardId, limit },
      signal,
    }),
  createMapping: (cardId: string, signal?: AbortSignal) =>
    postJson("POST /v1/cards/{card_id}/mappings", {
      pathParameters: { card_id: cardId },
      signal,
    }),
  getMapping: (mappingId: string, signal?: AbortSignal) =>
    getJson("GET /v1/mappings/{mapping_id}", {
      pathParameters: { mapping_id: mappingId },
      signal,
    }),
  listSnapshots: (signal?: AbortSignal, mappingId?: string, limit?: number) =>
    getJson("GET /v1/data-snapshots", {
      queryParameters: { limit, mapping_id: mappingId },
      signal,
    }),
  createSnapshot: (body: SnapshotCreateRequest, signal?: AbortSignal) =>
    postJson("POST /v1/data-snapshots", { body, signal }),
  getSnapshot: (snapshotId: string, signal?: AbortSignal) =>
    getJson("GET /v1/data-snapshots/{snapshot_id}", {
      pathParameters: { snapshot_id: snapshotId },
      signal,
    }),
  listEvaluationPolicies: (signal?: AbortSignal, limit?: number) =>
    getJson("GET /v1/evaluation-policies", {
      queryParameters: { limit },
      signal,
    }),
  createEvaluationPolicy: (body: EvaluationPolicyCreateRequest, signal?: AbortSignal) =>
    postJson("POST /v1/evaluation-policies", { body, signal }),
  getEvaluationPolicy: (policyId: string, policyVersion: number, signal?: AbortSignal) =>
    getJson("GET /v1/evaluation-policies/{policy_id}/versions/{policy_version}", {
      pathParameters: { policy_id: policyId, policy_version: policyVersion },
      signal,
    }),
  listEvaluationReports: (signal?: AbortSignal, limit?: number) =>
    getJson("GET /v1/evaluation-reports", {
      queryParameters: { limit },
      signal,
    }),
  createEvaluationReport: (body: EvaluationRunCreateRequest, signal?: AbortSignal) =>
    postJson("POST /v1/evaluation-reports", { body, signal }),
  getEvaluationReport: (artifactId: string, signal?: AbortSignal) =>
    getJson("GET /v1/evaluation-reports/{artifact_id}", {
      pathParameters: { artifact_id: artifactId },
      signal,
    }),
  listEvaluationOutcomes: (signal?: AbortSignal, limit?: number) =>
    getJson("GET /v1/evaluation-outcomes", {
      queryParameters: { limit },
      signal,
    }),
  getEvaluationOutcome: (outcomeId: string, signal?: AbortSignal) =>
    getJson("GET /v1/evaluation-outcomes/{outcome_id}", {
      pathParameters: { outcome_id: outcomeId },
      signal,
    }),
  listResearchRuns: (signal?: AbortSignal, limit?: number) =>
    getJson("GET /v1/research-runs", {
      queryParameters: { limit },
      signal,
    }),
  createResearchRun: (body: ResearchRunCreateRequest, signal?: AbortSignal) =>
    postJson("POST /v1/research-runs", { body, signal }),
  getResearchRun: (runId: string, signal?: AbortSignal) =>
    getJson("GET /v1/research-runs/{run_id}", {
      pathParameters: { run_id: runId },
      signal,
    }),
  listApprovalAssessments: (signal?: AbortSignal, limit?: number) =>
    getJson("GET /v1/approval-assessments", {
      queryParameters: { limit },
      signal,
    }),
  createApprovalAssessment: (body: ApprovalAssessmentCreateRequest, signal?: AbortSignal) =>
    postJson("POST /v1/approval-assessments", { body, signal }),
  getApprovalAssessment: (assessmentId: string, signal?: AbortSignal) =>
    getJson("GET /v1/approval-assessments/{assessment_id}", {
      pathParameters: { assessment_id: assessmentId },
      signal,
    }),
  getApprovalAssessmentEvidenceTimeline: (assessmentId: string, signal?: AbortSignal) =>
    getJson("GET /v1/approval-assessments/{assessment_id}/evidence-timeline", {
      pathParameters: { assessment_id: assessmentId },
      signal,
    }),
  listApprovalRevocations: (
    signal?: AbortSignal,
    humanAuthorizationEvidenceId?: string,
    limit?: number,
  ) =>
    getJson("GET /v1/approval-revocations", {
      queryParameters: {
        human_authorization_evidence_id: humanAuthorizationEvidenceId,
        limit,
      },
      signal,
    }),
  createApprovalRevocation: (body: ApprovalRevocationCreateRequest, signal?: AbortSignal) =>
    postJson("POST /v1/approval-revocations", { body, signal }),
  getApprovalRevocation: (revocationId: string, signal?: AbortSignal) =>
    getJson("GET /v1/approval-revocations/{revocation_id}", {
      pathParameters: { revocation_id: revocationId },
      signal,
    }),
};

export type { RemoteValue, SourceIntakeRequest };
