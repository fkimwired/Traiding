import type { components } from "@fable5/contracts";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import blockedSimulationFixture from "../../e2e/fixtures/phase10-blocked.json";
import completedSimulationFixture from "../../e2e/fixtures/phase10-completed.json";
import { LocalEvidenceBundleExport } from "../components/LocalEvidenceBundleExport";
import { fable5Api, type LocalSimulationEvidenceBundle } from "../lib/api";
import * as downloadModule from "../lib/local-evidence-download";

type PaperSimulationArtifact = components["schemas"]["PaperSimulationArtifact"];

const completed = completedSimulationFixture as unknown as PaperSimulationArtifact;
const blocked = blockedSimulationFixture as unknown as PaperSimulationArtifact;

function bundleFor(
  artifact: PaperSimulationArtifact,
  bundleSha256 = "8ad868297ec060d00067a5e17e40df83123a306898bfd9eacd869d0af543647c",
) {
  return {
    bundle_schema_version: "phase11-local-simulation-evidence-bundle-v1",
    bundle_sha256: bundleSha256,
    simulation: artifact,
    simulation_artifact_sha256: artifact.artifact_sha256,
    simulation_run_id: artifact.simulation_run_id,
  } satisfies LocalSimulationEvidenceBundle;
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.clearAllMocks();
});

describe("Phase 11 evidence bundle export control", () => {
  it("prepares with one GET, preserves focus, and downloads without another GET", async () => {
    const bundle = bundleFor(completed);
    const getBundle = vi.spyOn(fable5Api, "getLocalSimulationEvidenceBundle").mockResolvedValue({
      data: bundle,
      ok: true,
      retrySafe: true,
      status: 200,
    });
    const download = vi
      .spyOn(downloadModule, "downloadLocalEvidenceBundle")
      .mockImplementation(() => undefined);
    render(<LocalEvidenceBundleExport artifact={completed} />);
    const prepare = screen.getByRole("button", { name: "Prepare evidence bundle" });
    prepare.focus();

    fireEvent.click(prepare);

    expect(screen.getByRole("region", { name: "Prepare local evidence bundle" })).toHaveAttribute(
      "aria-busy",
      "true",
    );
    await screen.findByText("Validated historical bundle ready.");
    expect(document.activeElement).toBe(prepare);
    expect(getBundle).toHaveBeenCalledTimes(1);
    expect(getBundle).toHaveBeenCalledWith(completed.simulation_run_id, expect.any(AbortSignal));
    expect(screen.getByText(bundle.bundle_sha256)).toBeVisible();
    expect(screen.getByText(bundle.bundle_schema_version)).toBeVisible();
    expect(screen.getByText(/verify_local_simulation_evidence\.py/)).toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: "Download validated JSON" }));

    expect(download).toHaveBeenCalledWith(bundle);
    expect(getBundle).toHaveBeenCalledTimes(1);
  });

  it("renders blocked evidence as a zero-ledger historical bundle", async () => {
    const bundle = bundleFor(
      blocked,
      "35ca33153e7c46a6d0d7154b894020a0db8e1c4ac67d41db1869289771c43f3f",
    );
    vi.spyOn(fable5Api, "getLocalSimulationEvidenceBundle").mockResolvedValue({
      data: bundle,
      ok: true,
      retrySafe: true,
      status: 200,
    });
    render(<LocalEvidenceBundleExport artifact={blocked} />);

    expect(screen.getByText(/BLOCKED historical evidence: zero simulated ledger entries/)).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Prepare evidence bundle" }));

    await screen.findByRole("button", { name: "Download validated JSON" });
    expect(screen.getByText(bundle.bundle_sha256)).toBeVisible();
  });

  it("fails closed on a schema-valid bundle that does not equal the card", async () => {
    const mismatched = bundleFor(blocked);
    vi.spyOn(fable5Api, "getLocalSimulationEvidenceBundle").mockResolvedValue({
      data: mismatched,
      ok: true,
      retrySafe: true,
      status: 200,
    });
    render(<LocalEvidenceBundleExport artifact={completed} />);

    fireEvent.click(screen.getByRole("button", { name: "Prepare evidence bundle" }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/does not match this exact persisted simulation artifact/);
    expect(screen.queryByRole("button", { name: "Download validated JSON" })).not.toBeInTheDocument();
  });

  it("shows retry-safe GET failures without manufacturing a bundle", async () => {
    const getBundle = vi
      .spyOn(fable5Api, "getLocalSimulationEvidenceBundle")
      .mockResolvedValueOnce({
        error: { kind: "unavailable", message: "The API is unavailable.", retrySafe: true },
        ok: false,
      })
      .mockResolvedValueOnce({
        data: bundleFor(completed),
        ok: true,
        retrySafe: true,
        status: 200,
      });
    render(<LocalEvidenceBundleExport artifact={completed} />);
    fireEvent.click(screen.getByRole("button", { name: "Prepare evidence bundle" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("The API is unavailable.");
    expect(screen.queryByRole("button", { name: "Download validated JSON" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retry read-only preparation" }));

    await screen.findByRole("button", { name: "Download validated JSON" });
    expect(getBundle).toHaveBeenCalledTimes(2);
  });

  it("aborts stale preparation when the artifact changes", async () => {
    const signals: AbortSignal[] = [];
    vi.spyOn(fable5Api, "getLocalSimulationEvidenceBundle").mockImplementation(
      (_simulationRunId, signal) => {
        if (signal) signals.push(signal);
        return new Promise<
          Awaited<ReturnType<typeof fable5Api.getLocalSimulationEvidenceBundle>>
        >(() => undefined);
      },
    );
    const view = render(<LocalEvidenceBundleExport artifact={completed} />);
    fireEvent.click(screen.getByRole("button", { name: "Prepare evidence bundle" }));

    view.rerender(<LocalEvidenceBundleExport artifact={blocked} />);

    await waitFor(() => expect(signals[0]?.aborted).toBe(true));
    expect(screen.getByText("No bundle has been prepared.")).toBeVisible();
  });
});
