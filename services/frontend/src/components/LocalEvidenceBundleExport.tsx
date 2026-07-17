"use client";

import type { components } from "@fable5/contracts";
import { useCallback, useEffect, useRef, useState } from "react";

import { fable5Api, type LocalSimulationEvidenceBundle } from "../lib/api";
import {
  downloadLocalEvidenceBundle,
  localEvidenceBundleMatchesArtifact,
  localEvidenceFilename,
  localEvidenceVerifierCommand,
} from "../lib/local-evidence-download";

type PaperSimulationArtifact = components["schemas"]["PaperSimulationArtifact"];

type BundleState =
  | { status: "idle" }
  | { status: "preparing" }
  | { status: "ready"; bundle: LocalSimulationEvidenceBundle }
  | { status: "error"; message: string; retrySafe: boolean };

export function LocalEvidenceBundleExport({
  artifact,
}: Readonly<{ artifact: PaperSimulationArtifact }>) {
  const artifactIdentity = `${artifact.simulation_run_id}:${artifact.artifact_sha256}`;
  return <LocalEvidenceBundleExportSession artifact={artifact} key={artifactIdentity} />;
}

function LocalEvidenceBundleExportSession({
  artifact,
}: Readonly<{ artifact: PaperSimulationArtifact }>) {
  const [state, setState] = useState<BundleState>({ status: "idle" });
  const controllerRef = useRef<AbortController | null>(null);
  const requestVersionRef = useRef(0);
  const headingId = `local-evidence-bundle-${artifact.simulation_run_id}`;

  useEffect(
    () => () => {
      requestVersionRef.current += 1;
      controllerRef.current?.abort();
    },
    [],
  );

  const prepare = useCallback(async () => {
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    const requestVersion = ++requestVersionRef.current;
    setState({ status: "preparing" });

    const result = await fable5Api.getLocalSimulationEvidenceBundle(
      artifact.simulation_run_id,
      controller.signal,
    );
    if (controller.signal.aborted || requestVersion !== requestVersionRef.current) return;
    controllerRef.current = null;

    if (!result.ok) {
      if (result.error.kind !== "aborted") {
        setState({
          message: result.error.message,
          retrySafe: result.error.retrySafe,
          status: "error",
        });
      }
      return;
    }
    if (!localEvidenceBundleMatchesArtifact(result.data, artifact)) {
      setState({
        message:
          "The prepared evidence bundle does not match this exact persisted simulation artifact. No file is available.",
        retrySafe: false,
        status: "error",
      });
      return;
    }
    setState({ bundle: result.data, status: "ready" });
  }, [artifact]);

  return (
    <section
      aria-busy={state.status === "preparing"}
      aria-labelledby={headingId}
      className="localEvidenceExport"
    >
      <div className="localEvidenceExportHeader">
        <div>
          <span className="cardKicker">PHASE 11 / READ-ONLY GET</span>
          <h3 id={headingId}>Prepare local evidence bundle</h3>
        </div>
        <span className="statusBadge" data-tone="neutral">
          HISTORICAL INTEGRITY
        </span>
      </div>

      <p>
        This bundle proves historical artifact integrity only. It does not rerun or replay the
        simulation, establish current authority, authorize execution, or refresh any evidence.
      </p>
      <p>
        Preparation performs one read-only local API GET and no API or database mutation. Download
        writes one JSON file to your device only. The bundle hash is an integrity digest, not a
        signature.
      </p>
      <p className="localEvidenceBoundary">
        SIMULATED / LOCAL MOCK only. No live path, no personalized investment advice, and no real
        performance claim.
      </p>
      {artifact.outcome === "BLOCKED" ? (
        <p className="localEvidenceBlocked">
          BLOCKED historical evidence: zero simulated ledger entries are present.
        </p>
      ) : null}

      <div className="localEvidenceActions">
        <button
          aria-disabled={state.status === "preparing"}
          className="buttonSecondary"
          onClick={() => {
            if (state.status !== "preparing") void prepare();
          }}
          type="button"
        >
          {state.status === "preparing" ? "Preparing evidence bundle..." : "Prepare evidence bundle"}
        </button>
        {state.status === "ready" ? (
          <button
            className="buttonPrimary"
            onClick={() => downloadLocalEvidenceBundle(state.bundle)}
            type="button"
          >
            Download validated JSON
          </button>
        ) : null}
      </div>

      {state.status === "idle" ? (
        <p aria-live="polite" className="localEvidenceStatus" role="status">
          No bundle has been prepared.
        </p>
      ) : null}
      {state.status === "preparing" ? (
        <p aria-live="polite" className="localEvidenceStatus" role="status">
          Reading and validating the immutable server bundle.
        </p>
      ) : null}
      {state.status === "error" ? (
        <div className="localEvidenceError" role="alert">
          <strong>Evidence bundle unavailable.</strong>
          <p>{state.message}</p>
          {state.retrySafe ? (
            <button className="buttonSecondary" onClick={() => void prepare()} type="button">
              Retry read-only preparation
            </button>
          ) : null}
        </div>
      ) : null}
      {state.status === "ready" ? (
        <div aria-live="polite" className="localEvidenceReady" role="status">
          <strong>Validated historical bundle ready.</strong>
          <dl className="auditGrid localEvidenceAuditGrid">
            <div>
              <dt>Bundle schema</dt>
              <dd>{state.bundle.bundle_schema_version}</dd>
            </div>
            <div>
              <dt>Filename</dt>
              <dd className="mono visualMask">{localEvidenceFilename(state.bundle)}</dd>
            </div>
            <div>
              <dt>Server bundle SHA-256</dt>
              <dd className="mono visualMask">{state.bundle.bundle_sha256}</dd>
            </div>
          </dl>
          <p>Independent verification command:</p>
          <code className="localEvidenceCommand visualMask">
            {localEvidenceVerifierCommand(state.bundle)}
          </code>
        </div>
      ) : null}
    </section>
  );
}
