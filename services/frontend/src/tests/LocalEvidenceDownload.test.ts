import type { components } from "@fable5/contracts";
import { afterEach, describe, expect, it, vi } from "vitest";

import completedSimulationFixture from "../../e2e/fixtures/phase10-completed.json";
import {
  downloadLocalEvidenceBundle,
  localEvidenceBundleMatchesArtifact,
  localEvidenceFilename,
  localEvidenceVerifierCommand,
  serializeLocalEvidenceBundle,
  type LocalSimulationEvidenceBundle,
} from "../lib/local-evidence-download";

type PaperSimulationArtifact = components["schemas"]["PaperSimulationArtifact"];

const completed = completedSimulationFixture as unknown as PaperSimulationArtifact;
const bundle = {
  bundle_schema_version: "phase11-local-simulation-evidence-bundle-v1",
  bundle_sha256: "8ad868297ec060d00067a5e17e40df83123a306898bfd9eacd869d0af543647c",
  simulation: completed,
  simulation_artifact_sha256: completed.artifact_sha256,
  simulation_run_id: completed.simulation_run_id,
} satisfies LocalSimulationEvidenceBundle;

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe("Phase 11 local evidence download", () => {
  it("serializes recursively sorted keys with one trailing LF", () => {
    const serialized = serializeLocalEvidenceBundle(bundle);

    expect(serialized.endsWith("\n")).toBe(true);
    expect(serialized.endsWith("\n\n")).toBe(false);
    expect(JSON.parse(serialized)).toEqual(bundle);
    expect(serialized.indexOf('"bundle_schema_version"')).toBeLessThan(
      serialized.indexOf('"bundle_sha256"'),
    );
    expect(serialized.indexOf('"bundle_sha256"')).toBeLessThan(
      serialized.indexOf('"simulation"'),
    );
    expect(serialized.indexOf('"artifact_schema_version"')).toBeLessThan(
      serialized.indexOf('"artifact_sha256"'),
    );
  });

  it("derives the deterministic filename and exact independent verifier command", () => {
    const filename =
      `fable5-local-simulation-evidence-${completed.simulation_run_id}-` +
      "8ad868297ec0.json";

    expect(localEvidenceFilename(bundle)).toBe(filename);
    expect(localEvidenceVerifierCommand(bundle)).toBe(
      `python scripts/verify_local_simulation_evidence.py --bundle "${filename}" ` +
        `--expected-bundle-sha256 ${bundle.bundle_sha256}`,
    );
  });

  it("requires complete semantic equality with the card artifact", () => {
    expect(localEvidenceBundleMatchesArtifact(bundle, completed)).toBe(true);
    expect(
      localEvidenceBundleMatchesArtifact(
        { ...bundle, simulation_artifact_sha256: "f".repeat(64) },
        completed,
      ),
    ).toBe(false);
    expect(
      localEvidenceBundleMatchesArtifact(
        {
          ...bundle,
          simulation: {
            ...completed,
            simulation_idempotency_key: "phase11-semantic-mismatch",
          },
        },
        completed,
      ),
    ).toBe(false);
  });

  it("writes one local Blob without a network request and revokes its URL later", () => {
    vi.useFakeTimers();
    const createObjectURL = vi.fn().mockReturnValue("blob:phase11-local-evidence");
    const revokeObjectURL = vi.fn();
    const fetchMock = vi.fn();
    vi.stubGlobal("URL", { createObjectURL, revokeObjectURL });
    vi.stubGlobal("fetch", fetchMock);
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);

    downloadLocalEvidenceBundle(bundle);

    expect(createObjectURL).toHaveBeenCalledTimes(1);
    expect(createObjectURL.mock.calls[0]?.[0]).toBeInstanceOf(Blob);
    expect(click).toHaveBeenCalledTimes(1);
    expect(fetchMock).not.toHaveBeenCalled();
    expect(revokeObjectURL).not.toHaveBeenCalled();
    expect(document.querySelector("a[download]")).toBeNull();

    vi.runOnlyPendingTimers();
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:phase11-local-evidence");
  });
});
