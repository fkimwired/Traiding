"use client";

import { type FormEvent, useEffect, useRef, useState } from "react";

import styles from "./PaperReadinessWorkspace.module.css";
import {
  loadPaperShadowReadiness,
  type PaperShadowReadinessArtifact,
  type ReadinessFailure,
} from "./readiness-api";

type ViewState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; error: ReadinessFailure }
  | { status: "success"; artifact: PaperShadowReadinessArtifact };

const failureTitles: Record<ReadinessFailure["kind"], string> = {
  conflict: "Conflict (409)",
  malformed: "Malformed response",
  "not-found": "Not found (404)",
  unavailable: "Unavailable",
  validation: "Validation (422)",
};

function booleanText(value: boolean) {
  return value ? "true" : "false";
}

function checkTone(status: string) {
  if (status === "PASS") return "pass";
  if (status === "BLOCKED") return "blocked";
  return "warning";
}

function EvidenceTime({ value }: Readonly<{ value: string }>) {
  return <time dateTime={value}>{value}</time>;
}

function ReadinessEvidence({ artifact }: Readonly<{ artifact: PaperShadowReadinessArtifact }>) {
  const isMock = artifact.source_kind === "DETERMINISTIC_MOCK";

  return (
    <section className={styles.evidence} aria-labelledby="readiness-result-heading">
      <div className={styles.resultHeader}>
        <div>
          <p className={styles.eyebrow}>Persisted Phase 12 evidence</p>
          <h2 id="readiness-result-heading">Assessment {artifact.readiness_assessment_id}</h2>
        </div>
        <span className={styles.outcome} data-tone={artifact.outcome.toLowerCase()}>
          {artifact.outcome}
        </span>
      </div>

      <div className={styles.scopeGrid}>
        <p className={styles.scopeNotice} data-tone={isMock ? "mock" : "paper"}>
          <strong>{isMock ? "MOCK — local contract proof only" : "PAPER — read-only observation"}</strong>
          <span>
            {isMock
              ? "This artifact does not prove external readiness."
              : "This artifact records historical paper-environment observations only."}
          </span>
        </p>
        <p className={styles.expiryNotice} data-tone="historical">
          <strong>HISTORICAL READINESS EVIDENCE</strong>
          <span>
            Historical readiness evidence. Browser time is not authority for currentness or
            expiry. Recorded expiry: <EvidenceTime value={artifact.expires_at_utc} />. Currentness
            requires a fresh accepted observation or an explicitly time-bound server/CLI report.
          </span>
        </p>
      </div>

      {artifact.outcome === "BLOCKED" ? (
        <div className={styles.blocker} role="alert">
          <strong>Readiness is blocked</strong>
          <ul>
            {artifact.reason_codes.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <section className={styles.section} aria-labelledby="checks-heading">
        <div className={styles.sectionHeading}>
          <div>
            <p className={styles.eyebrow}>Canonical registry</p>
            <h3 id="checks-heading">Eight ordered readiness checks</h3>
          </div>
          <p>Server order, statuses, reasons, and content hashes are rendered verbatim.</p>
        </div>
        <ol className={styles.checks} data-testid="readiness-checks">
          {artifact.checks.map((check) => (
            <li key={`${check.ordinal}-${check.code}`} data-tone={checkTone(check.status)}>
              <div className={styles.checkIdentity}>
                <span className={styles.ordinal}>{String(check.ordinal).padStart(2, "0")}</span>
                <div>
                  <strong>{check.code}</strong>
                  <span>{check.reason_code}</span>
                </div>
              </div>
              <span className={styles.checkStatus} data-tone={checkTone(check.status)}>
                {check.status}
              </span>
              <dl className={styles.checkDetails}>
                <div>
                  <dt>Check SHA-256</dt>
                  <dd><code>{check.check_sha256}</code></dd>
                </div>
                <div>
                  <dt>Evidence SHA-256s</dt>
                  <dd>{check.evidence_sha256s.map((value) => <code key={value}>{value}</code>)}</dd>
                </div>
                {check.observed_value != null ? (
                  <div>
                    <dt>Observed</dt>
                    <dd>{check.observed_value}</dd>
                  </div>
                ) : null}
                {check.threshold_value != null ? (
                  <div>
                    <dt>Threshold</dt>
                    <dd>{check.threshold_value}</dd>
                  </div>
                ) : null}
              </dl>
            </li>
          ))}
        </ol>
      </section>

      <div className={styles.observationGrid}>
        <section className={styles.observation} aria-labelledby="clock-heading">
          <p className={styles.eyebrow}>Market clock</p>
          <h3 id="clock-heading">
            {artifact.clock ? (artifact.clock.is_open ? "OPEN" : "CLOSED") : "NOT OBSERVED"}
          </h3>
          {artifact.clock ? (
            <dl className={styles.factList}>
              <div><dt>Provider timestamp</dt><dd><EvidenceTime value={artifact.clock.provider_timestamp_utc} /></dd></div>
              <div><dt>Next open</dt><dd><EvidenceTime value={artifact.clock.next_open_utc} /></dd></div>
              <div><dt>Next close</dt><dd><EvidenceTime value={artifact.clock.next_close_utc} /></dd></div>
              <div><dt>Observation SHA-256</dt><dd><code>{artifact.clock.observation_sha256}</code></dd></div>
            </dl>
          ) : <p>No clock observation was retained.</p>}
        </section>

        <section className={styles.observation} aria-labelledby="quote-heading">
          <p className={styles.eyebrow}>Quote connectivity</p>
          <h3 id="quote-heading">
            {artifact.latest_quote
              ? `${artifact.latest_quote.symbol} / ${artifact.latest_quote.feed}`
              : "NOT OBSERVED"}
          </h3>
          {artifact.latest_quote ? (
            <dl className={styles.factList}>
              <div><dt>Fresh</dt><dd>{booleanText(artifact.latest_quote.fresh)}</dd></div>
              <div><dt>Age / TTL seconds</dt><dd>{artifact.latest_quote.age_seconds} / {artifact.latest_quote.freshness_ttl_seconds}</dd></div>
              <div><dt>Event time</dt><dd><EvidenceTime value={artifact.latest_quote.event_time_utc} /></dd></div>
              <div><dt>Received time</dt><dd><EvidenceTime value={artifact.latest_quote.received_at_utc} /></dd></div>
              <div><dt>Bid valid</dt><dd>{booleanText(artifact.latest_quote.bid_price_valid)}</dd></div>
              <div><dt>Ask valid</dt><dd>{booleanText(artifact.latest_quote.ask_price_valid)}</dd></div>
              <div><dt>Non-crossed</dt><dd>{booleanText(artifact.latest_quote.non_crossed)}</dd></div>
              <div><dt>Observation SHA-256</dt><dd><code>{artifact.latest_quote.observation_sha256}</code></dd></div>
            </dl>
          ) : <p>No quote observation was retained.</p>}
        </section>
      </div>

      <section className={styles.section} aria-labelledby="authority-heading">
        <div className={styles.sectionHeading}>
          <div>
            <p className={styles.eyebrow}>Immutable authority boundary</p>
            <h3 id="authority-heading">No execution authority</h3>
          </div>
          <p>{artifact.disclaimer}</p>
        </div>
        <ul className={styles.authorityList}>
          <li><code>order_submission_authorized = {booleanText(artifact.order_submission_authorized)}</code></li>
          <li><code>strategy_execution_eligible = {booleanText(artifact.strategy_execution_eligible)}</code></li>
          <li><code>live_path_absent = {booleanText(artifact.live_path_absent)}</code></li>
          <li><code>no_personalized_investment_advice = {booleanText(artifact.no_personalized_investment_advice)}</code></li>
          <li><code>no_real_performance_claimed = {booleanText(artifact.no_real_performance_claimed)}</code></li>
        </ul>
      </section>

      <section className={styles.section} aria-labelledby="audit-heading">
        <div className={styles.sectionHeading}>
          <div>
            <p className={styles.eyebrow}>Evidence lineage</p>
            <h3 id="audit-heading">Hashes and UTC timestamps</h3>
          </div>
          <p>Identifiers are historical evidence, never promotion or execution authority.</p>
        </div>
        <dl className={styles.auditGrid}>
          <div><dt>Artifact SHA-256</dt><dd><code>{artifact.artifact_sha256}</code></dd></div>
          <div><dt>Request fingerprint SHA-256</dt><dd><code>{artifact.request_fingerprint_sha256}</code></dd></div>
          <div><dt>Transport profile SHA-256</dt><dd><code>{artifact.transport_profile_sha256}</code></dd></div>
          <div><dt>Phase 12 Git SHA</dt><dd><code>{artifact.phase12_code_version_git_sha}</code></dd></div>
          <div><dt>Assessment started</dt><dd><EvidenceTime value={artifact.assessment_started_at_utc} /></dd></div>
          <div><dt>Assessment completed</dt><dd><EvidenceTime value={artifact.assessment_completed_at_utc} /></dd></div>
          <div><dt>Evidence expires</dt><dd><EvidenceTime value={artifact.expires_at_utc} /></dd></div>
          <div><dt>Source kind</dt><dd><code>{artifact.source_kind}</code></dd></div>
        </dl>
      </section>

      <details className={styles.transportEvidence}>
        <summary>Inspect six sanitized read-only transport records</summary>
        <ol>
          {artifact.inspections.map((inspection) => (
            <li key={`${inspection.ordinal}-${inspection.code}`}>
              <strong>{inspection.ordinal}. {inspection.code}</strong>
              <span>{inspection.method} / {inspection.status}</span>
              <dl>
                <div><dt>Request ID</dt><dd><code>{inspection.request_id ?? "not retained"}</code></dd></div>
                <div><dt>Response SHA-256</dt><dd><code>{inspection.response_sha256 ?? "not retained"}</code></dd></div>
                <div><dt>Inspection SHA-256</dt><dd><code>{inspection.inspection_sha256}</code></dd></div>
              </dl>
            </li>
          ))}
        </ol>
      </details>
    </section>
  );
}

export function PaperReadinessWorkspace() {
  const [assessmentId, setAssessmentId] = useState("");
  const [state, setState] = useState<ViewState>({ status: "idle" });
  const activeRequest = useRef<AbortController | null>(null);
  const requestVersion = useRef(0);
  const errorRegion = useRef<HTMLElement | null>(null);
  const resultRegion = useRef<HTMLDivElement | null>(null);

  useEffect(
    () => () => {
      requestVersion.current += 1;
      activeRequest.current?.abort();
    },
    [],
  );
  useEffect(() => {
    if (state.status === "error") errorRegion.current?.focus();
    if (state.status === "success") resultRegion.current?.focus();
  }, [state.status]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedId = assessmentId.trim();
    if (normalizedId.length === 0) {
      setState({
        status: "error",
        error: {
          kind: "validation",
          message: "Enter a canonical assessment UUID before loading evidence.",
          status: 422,
        },
      });
      return;
    }

    activeRequest.current?.abort();
    const controller = new AbortController();
    activeRequest.current = controller;
    const version = requestVersion.current + 1;
    requestVersion.current = version;
    setState({ status: "loading" });
    const result = await loadPaperShadowReadiness(normalizedId, controller.signal);
    if (requestVersion.current !== version) return;
    activeRequest.current = null;
    setState(
      result.ok
        ? {
            status: "success",
            artifact: result.artifact,
          }
        : { status: "error", error: result.error },
    );
  }

  return (
    <div className={styles.workspace} data-readiness-surface="paper-only">
      <header className={styles.hero}>
        <div>
          <p className={styles.eyebrow}>Read-only historical evidence</p>
          <h1>Paper shadow readiness</h1>
          <p>
            Retrieve one immutable Phase 12 assessment. This page cannot initiate a capture,
            mutate an account, or confer execution authority.
          </p>
        </div>
        <div className={styles.boundaryBanner} role="note">
          <strong>Simulated / Paper Only / No Advice</strong>
          <span>Observation evidence is separate from execution authority.</span>
        </div>
      </header>

      <section className={styles.lookup} aria-labelledby="lookup-heading">
        <div>
          <p className={styles.eyebrow}>Explicit one-shot read</p>
          <h2 id="lookup-heading">Load an assessment</h2>
          <p>One explicit action performs one generated-contract GET. There is no polling or automatic refresh.</p>
        </div>
        <form onSubmit={handleSubmit} noValidate aria-busy={state.status === "loading"}>
          <label htmlFor="readiness-assessment-id">Readiness assessment ID</label>
          <div className={styles.inputRow}>
            <input
              id="readiness-assessment-id"
              name="assessment-id"
              type="text"
              autoComplete="off"
              inputMode="text"
              maxLength={128}
              spellCheck={false}
              value={assessmentId}
              onChange={(event) => setAssessmentId(event.target.value)}
              placeholder="00000000-0000-0000-0000-000000000000"
            />
            <button type="submit" disabled={state.status === "loading"}>
              {state.status === "loading" ? "Loading…" : "Load readiness evidence"}
            </button>
          </div>
          <p>Use the immutable assessment UUID returned by the local capture or mock proof.</p>
        </form>
      </section>

      {state.status === "idle" ? (
        <p className={styles.emptyState}>No assessment loaded. Enter an immutable identifier to begin a read.</p>
      ) : null}
      {state.status === "loading" ? (
        <p className={styles.loadingState} role="status" aria-live="polite">Loading immutable readiness evidence…</p>
      ) : null}
      {state.status === "error" ? (
        <section
          className={styles.errorState}
          role="alert"
          aria-labelledby="readiness-error-heading"
          ref={errorRegion}
          tabIndex={-1}
        >
          <h2 id="readiness-error-heading">{failureTitles[state.error.kind]}</h2>
          <p>{state.error.message}</p>
        </section>
      ) : null}
      {state.status === "success" ? (
        <div ref={resultRegion} tabIndex={-1} className={styles.resultFocus}>
          <ReadinessEvidence artifact={state.artifact} />
        </div>
      ) : null}
    </div>
  );
}
