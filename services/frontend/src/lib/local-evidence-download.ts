import type { components } from "@fable5/contracts";

type JsonValue = boolean | null | number | string | JsonValue[] | { [key: string]: JsonValue };
type LocalSimulationEvidenceBundle = components["schemas"]["LocalSimulationEvidenceBundle"];
type PaperSimulationArtifact = components["schemas"]["PaperSimulationArtifact"];

function sortedJsonValue(value: unknown): JsonValue {
  if (value === null || typeof value === "boolean" || typeof value === "number" || typeof value === "string") {
    return value;
  }
  if (Array.isArray(value)) return value.map(sortedJsonValue);
  if (typeof value === "object") {
    const entries = Object.entries(value as Record<string, unknown>)
      .sort(([left], [right]) => (left < right ? -1 : left > right ? 1 : 0))
      .map(([key, item]) => [key, sortedJsonValue(item)] as const);
    return Object.fromEntries(entries) as { [key: string]: JsonValue };
  }
  throw new TypeError("Evidence bundle contains a non-JSON value.");
}

function sortedCompactJson(value: unknown) {
  return JSON.stringify(sortedJsonValue(value));
}

export function localEvidenceFilename(bundle: LocalSimulationEvidenceBundle) {
  return (
    `fable5-local-simulation-evidence-${bundle.simulation_run_id}-` +
    `${bundle.bundle_sha256.slice(0, 12)}.json`
  );
}

export function localEvidenceVerifierCommand(bundle: LocalSimulationEvidenceBundle) {
  const filename = localEvidenceFilename(bundle);
  return (
    `python scripts/verify_local_simulation_evidence.py --bundle "${filename}" ` +
    `--expected-bundle-sha256 ${bundle.bundle_sha256}`
  );
}

export function localEvidenceBundleMatchesArtifact(
  bundle: LocalSimulationEvidenceBundle,
  artifact: PaperSimulationArtifact,
) {
  return (
    bundle.simulation_run_id === artifact.simulation_run_id &&
    bundle.simulation_artifact_sha256 === artifact.artifact_sha256 &&
    bundle.simulation.simulation_run_id === artifact.simulation_run_id &&
    bundle.simulation.artifact_sha256 === artifact.artifact_sha256 &&
    sortedCompactJson(bundle.simulation) === sortedCompactJson(artifact)
  );
}

export function serializeLocalEvidenceBundle(bundle: LocalSimulationEvidenceBundle) {
  return `${JSON.stringify(sortedJsonValue(bundle), null, 2)}\n`;
}

export function downloadLocalEvidenceBundle(bundle: LocalSimulationEvidenceBundle) {
  const contents = serializeLocalEvidenceBundle(bundle);
  const blob = new Blob([contents], { type: "application/json;charset=utf-8" });
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.download = localEvidenceFilename(bundle);
  anchor.href = objectUrl;
  anchor.hidden = true;
  document.body.append(anchor);
  try {
    anchor.click();
  } finally {
    anchor.remove();
    globalThis.setTimeout(() => URL.revokeObjectURL(objectUrl), 0);
  }
}

export type { LocalSimulationEvidenceBundle };
