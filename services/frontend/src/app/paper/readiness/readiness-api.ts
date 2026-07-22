import {
  type SuccessfulJsonOperation,
  type SuccessfulJsonResponseByOperation,
  validateOpenApiResponse,
} from "@fable5/contracts";

import { API_REQUEST_TIMEOUT_MS, apiHref } from "../../../lib/api";

export const READINESS_OPERATION =
  "GET /v1/paper-shadow-readiness/{readiness_assessment_id}" satisfies SuccessfulJsonOperation;

export type PaperShadowReadinessArtifact =
  SuccessfulJsonResponseByOperation[typeof READINESS_OPERATION];

export type ReadinessFailureKind =
  | "conflict"
  | "malformed"
  | "not-found"
  | "unavailable"
  | "validation";

export type ReadinessFailure = {
  kind: ReadinessFailureKind;
  message: string;
  status?: number;
};

export type ReadinessResult =
  | { ok: true; artifact: PaperShadowReadinessArtifact }
  | { ok: false; error: ReadinessFailure };

function failureForStatus(status: number): ReadinessFailure {
  if (status === 404) {
    return {
      kind: "not-found",
      message: "No persisted readiness assessment exists for that identifier.",
      status,
    };
  }
  if (status === 409) {
    return {
      kind: "conflict",
      message: "The persisted readiness evidence conflicts with its immutable lineage.",
      status,
    };
  }
  if (status === 422) {
    return {
      kind: "validation",
      message: "The assessment identifier was rejected by the typed API boundary.",
      status,
    };
  }
  return {
    kind: "unavailable",
    message: "The read-only readiness evidence service is unavailable.",
    status,
  };
}

export async function loadPaperShadowReadiness(
  assessmentId: string,
  parentSignal?: AbortSignal,
): Promise<ReadinessResult> {
  const controller = new AbortController();
  const forwardAbort = () => controller.abort();
  if (parentSignal?.aborted) forwardAbort();
  else parentSignal?.addEventListener("abort", forwardAbort, { once: true });
  const timeoutId = setTimeout(() => controller.abort(), API_REQUEST_TIMEOUT_MS);
  try {
    const path = `/v1/paper-shadow-readiness/${encodeURIComponent(assessmentId)}`;
    const response = await fetch(apiHref(path), {
      headers: { Accept: "application/json" },
      credentials: "omit",
      method: "GET",
      signal: controller.signal,
    });
    if (!response.ok) return { ok: false, error: failureForStatus(response.status) };

    let body: unknown;
    try {
      body = await response.json();
    } catch {
      return {
        ok: false,
        error: {
          kind: "malformed",
          message: "The API returned malformed JSON.",
          status: response.status,
        },
      };
    }
    if (!validateOpenApiResponse(READINESS_OPERATION, response.status, body)) {
      return {
        ok: false,
        error: {
          kind: "malformed",
          message: "The API response did not match the generated readiness contract.",
          status: response.status,
        },
      };
    }
    const artifact = body as PaperShadowReadinessArtifact;
    if (
      artifact.readiness_assessment_id.toLowerCase() !== assessmentId.toLowerCase()
    ) {
      return {
        ok: false,
        error: {
          kind: "conflict",
          message: "The returned readiness identifier conflicts with the requested evidence.",
          status: response.status,
        },
      };
    }
    return { ok: true, artifact };
  } catch {
    return {
      ok: false,
      error: {
        kind: "unavailable",
        message: "The read-only readiness evidence service could not be reached.",
      },
    };
  } finally {
    clearTimeout(timeoutId);
    parentSignal?.removeEventListener("abort", forwardAbort);
  }
}
