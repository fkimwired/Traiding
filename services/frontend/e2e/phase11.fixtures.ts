import type { components } from "@fable5/contracts";

import {
  phase10BlockedArtifact,
  phase10CompletedArtifact,
  type PaperSimulationArtifact,
} from "./phase10.fixtures";

export type LocalSimulationEvidenceBundle =
  components["schemas"]["LocalSimulationEvidenceBundle"];

export const PHASE11_COMPLETED_BUNDLE_SHA256 =
  "8ad868297ec060d00067a5e17e40df83123a306898bfd9eacd869d0af543647c";
export const PHASE11_BLOCKED_BUNDLE_SHA256 =
  "35ca33153e7c46a6d0d7154b894020a0db8e1c4ac67d41db1869289771c43f3f";

export const phase11CompletedEvidenceBundle = {
  bundle_schema_version: "phase11-local-simulation-evidence-bundle-v1",
  bundle_sha256: PHASE11_COMPLETED_BUNDLE_SHA256,
  simulation: phase10CompletedArtifact,
  simulation_artifact_sha256: phase10CompletedArtifact.artifact_sha256,
  simulation_run_id: phase10CompletedArtifact.simulation_run_id,
} satisfies LocalSimulationEvidenceBundle;

export const phase11BlockedEvidenceBundle = {
  bundle_schema_version: "phase11-local-simulation-evidence-bundle-v1",
  bundle_sha256: PHASE11_BLOCKED_BUNDLE_SHA256,
  simulation: phase10BlockedArtifact,
  simulation_artifact_sha256: phase10BlockedArtifact.artifact_sha256,
  simulation_run_id: phase10BlockedArtifact.simulation_run_id,
} satisfies LocalSimulationEvidenceBundle;

export function phase11EvidenceBundleFor(
  artifact: PaperSimulationArtifact,
): LocalSimulationEvidenceBundle | undefined {
  if (artifact.simulation_run_id === phase10CompletedArtifact.simulation_run_id) {
    return phase11CompletedEvidenceBundle;
  }
  if (artifact.simulation_run_id === phase10BlockedArtifact.simulation_run_id) {
    return phase11BlockedEvidenceBundle;
  }
  return undefined;
}

export function phase11EvidenceFilename(bundle: LocalSimulationEvidenceBundle) {
  return (
    `fable5-local-simulation-evidence-${bundle.simulation_run_id}-` +
    `${bundle.bundle_sha256.slice(0, 12)}.json`
  );
}
