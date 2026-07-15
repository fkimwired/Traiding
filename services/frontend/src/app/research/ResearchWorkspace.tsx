"use client";

import type { components } from "@fable5/contracts";
import Link from "next/link";
import { type FormEvent, useMemo, useState } from "react";

import { fable5Api, type ApiFailure } from "../../lib/api";
import {
  evaluationEvidenceForResearchRun,
  type EvidenceIndex,
  snapshotMatchesMapping,
  snapshotsForResearchRun,
  useEvidenceIndex,
} from "../../lib/evidence-index";
import { useEvidenceRetryFocus } from "../../lib/use-evidence-retry-focus";

type ResearchRun = components["schemas"]["ResearchRunArtifact"];
type ResearchConfigurationId = components["schemas"]["ResearchConfigurationId"];
type Gate = components["schemas"]["GateResult"];

const blockingGateOutcomes = new Set<Gate["outcome"]>([
  "fail",
  "blocked_missing_policy",
  "blocked_uncomputable",
  "research_only",
]);

function humanize(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function textValue(value: string | number | boolean) {
  return typeof value === "boolean" ? (value ? "true" : "false") : String(value);
}

function gateTone(outcome: Gate["outcome"]) {
  if (outcome === "pass") return "pass";
  return "critical";
}

function runIsBlocked(run: ResearchRun) {
  return run.status === "blocked" || run.phase5_evaluation.promotion_state !== "PASS_RESEARCH";
}

function researchRunIsBlocking(index: EvidenceIndex, run: ResearchRun) {
  const evaluation = evaluationEvidenceForResearchRun(index, run);
  const snapshotEvidence = snapshotsForResearchRun(index, run);
  const referenceMissing =
    !run.phase5_evaluation.evaluation_report_id &&
    !run.phase5_evaluation.evaluation_outcome_id;
  const promotionConflict =
    (evaluation.report &&
      evaluation.report.promotion_state !== run.phase5_evaluation.promotion_state) ||
    (evaluation.outcome &&
      evaluation.outcome.promotion_state !== run.phase5_evaluation.promotion_state);
  return (
    runIsBlocked(run) ||
    evaluation.conflict ||
    snapshotEvidence.conflict ||
    referenceMissing ||
    Boolean(promotionConflict) ||
    Boolean(
      evaluation.report?.gates.some((gate) => blockingGateOutcomes.has(gate.outcome)),
    )
  );
}

function KeyValues({ values }: { values: Readonly<Record<string, string | number | boolean>> }) {
  const entries = Object.entries(values);
  if (entries.length === 0) return <p className="formHint">None recorded</p>;

  return (
    <dl className="keyValueGrid">
      {entries.map(([key, value]) => (
        <div key={key}>
          <dt>{humanize(key)}</dt>
          <dd>{textValue(value)}</dd>
        </div>
      ))}
    </dl>
  );
}

function GateCard({ gate }: { gate: Gate }) {
  const blocking = blockingGateOutcomes.has(gate.outcome);
  return (
    <article className="evidenceCard" data-blocking={blocking ? "true" : undefined}>
      <div className="cardHeader">
        <div>
          <span className="cardKicker">Server gate {gate.ordinal}</span>
          <h3>{gate.gate_code}</h3>
        </div>
        <span className="statusBadge" data-tone={gateTone(gate.outcome)}>
          {gate.outcome}
        </span>
      </div>
      {blocking ? (
        <div className="blockerBanner">
          <strong>Blocking gate</strong>
          <p>{gate.reason_codes.join(", ") || "The persisted gate did not pass."}</p>
        </div>
      ) : null}
      <h4>Results</h4>
      <KeyValues values={gate.results} />
      <h4>Server thresholds</h4>
      <KeyValues values={gate.thresholds} />
      <ul className="reasonList" aria-label={`${gate.gate_code} reason codes`}>
        {gate.reason_codes.map((reason) => (
          <li key={reason}>{reason}</li>
        ))}
      </ul>
      <p className="mono">Gate SHA-256: {gate.gate_result_sha256}</p>
    </article>
  );
}

function AttemptSummary({ run }: { run: ResearchRun }) {
  const statuses: components["schemas"]["ResearchAttemptStatus"][] = [
    "completed",
    "failed",
    "abandoned",
    "no_return",
    "blocked",
  ];

  return (
    <section aria-labelledby={`attempts-${run.run_id}`}>
      <div className="sectionHeading">
        <h3 id={`attempts-${run.run_id}`}>Complete trial attempts</h3>
        <p>Failed and abandoned attempts are retained; no survivor-only summary is used.</p>
      </div>
      <dl className="keyValueGrid">
        {statuses.map((status) => (
          <div key={status}>
            <dt>{humanize(status)}</dt>
            <dd>{run.attempts.filter((attempt) => attempt.status === status).length}</dd>
          </div>
        ))}
      </dl>
      <details className="evidenceDisclosure">
        <summary>Inspect every attempt</summary>
        <ol className="evidenceList">
          {run.attempts.map((attempt) => (
            <li key={`${attempt.ordinal}-${attempt.attempt_sha256}`}>
              <strong>
                {attempt.ordinal}. {attempt.status}
              </strong>
              <span>{attempt.failure_reason ?? "No failure reason recorded"}</span>
              <code className="mono"> {attempt.attempt_sha256}</code>
            </li>
          ))}
        </ol>
      </details>
    </section>
  );
}

export function ResearchRunCard({
  index,
  run,
}: {
  index: EvidenceIndex;
  run: ResearchRun;
}) {
  const evaluation = evaluationEvidenceForResearchRun(index, run);
  const snapshotEvidence = snapshotsForResearchRun(index, run);
  const report = evaluation.report;
  const gates = [...(report?.gates ?? [])].sort((left, right) => {
    const leftBlocked = blockingGateOutcomes.has(left.outcome) ? 0 : 1;
    const rightBlocked = blockingGateOutcomes.has(right.outcome) ? 0 : 1;
    return leftBlocked - rightBlocked || left.ordinal - right.ordinal;
  });
  const evaluationReferenceMissing =
    !run.phase5_evaluation.evaluation_report_id &&
    !run.phase5_evaluation.evaluation_outcome_id;
  const promotionConflict =
    (evaluation.report &&
      evaluation.report.promotion_state !== run.phase5_evaluation.promotion_state) ||
    (evaluation.outcome &&
      evaluation.outcome.promotion_state !== run.phase5_evaluation.promotion_state);
  const evidenceConflict =
    evaluation.conflict ||
    snapshotEvidence.conflict ||
    evaluationReferenceMissing ||
    Boolean(promotionConflict);
  const blocked = researchRunIsBlocking(index, run);
  const failedBaselines = run.baseline_comparisons.filter(
    (comparison) => comparison.outcome === "rejected",
  );

  return (
    <article
      className="governanceCard researchRunCard"
      data-blocking={blocked ? "true" : undefined}
      aria-labelledby={`research-run-${run.run_id}`}
    >
      <div className="cardHeader">
        <div>
          <span className="cardKicker">Immutable Phase 6 research artifact</span>
          <h2 id={`research-run-${run.run_id}`}>{run.family}</h2>
        </div>
        <span className="statusBadge" data-tone={blocked ? "critical" : "pass"}>
          {run.phase5_evaluation.promotion_state}
        </span>
      </div>

      {blocked ? (
        <div className="blockerBanner">
          <strong>Research is ineligible</strong>
          <p>
            {evidenceConflict
              ? "The run's exact evaluation or snapshot reference is missing, mismatched, or conflicts with its persisted lineage."
              : run.reason_codes.join(", ") || "A persisted prerequisite did not pass."}
          </p>
        </div>
      ) : (
        <div className="boundaryNotice" data-tone="critical">
          <strong>Prerequisite only</strong>
          <p>PASS_RESEARCH is not simulated-paper approval and grants no authorization.</p>
        </div>
      )}

      <dl className="keyValueGrid">
        <div>
          <dt>Run ID</dt>
          <dd className="mono visualMask">{run.run_id}</dd>
        </div>
        <div>
          <dt>Status</dt>
          <dd>{run.status}</dd>
        </div>
        <div>
          <dt>Configuration identity</dt>
          <dd className="mono">{run.configuration_id}</dd>
        </div>
        <div>
          <dt>Configuration SHA-256</dt>
          <dd className="artifactHash visualMask">{run.configuration_sha256}</dd>
        </div>
        <div>
          <dt>Code version Git SHA</dt>
          <dd className="mono visualMask">{run.code_version_git_sha}</dd>
        </div>
        <div>
          <dt>Artifact SHA-256</dt>
          <dd className="artifactHash visualMask">{run.artifact_sha256}</dd>
        </div>
        <div>
          <dt>Random seed</dt>
          <dd>{run.random_seed}</dd>
        </div>
        <div>
          <dt>Cost-sensitive trial ledgers</dt>
          <dd>{run.trial_economics.length}</dd>
        </div>
        <div>
          <dt>Baseline comparisons rejected</dt>
          <dd>{failedBaselines.length}</dd>
        </div>
        <div>
          <dt>Snapshot bundle SHA-256</dt>
          <dd className="artifactHash visualMask">{run.snapshot_bundle_sha256}</dd>
        </div>
      </dl>

      <AttemptSummary run={run} />

      {snapshotEvidence.conflict ? (
        <p className="statePanel" data-tone="critical" role="status">
          An embedded snapshot identifier, hash, or mapping conflicts with the loaded artifact. No
          mapping-level snapshot was substituted.
        </p>
      ) : null}

      <section aria-labelledby={`gates-${run.run_id}`}>
        <div className="sectionHeading">
          <h3 id={`gates-${run.run_id}`}>Evaluation gates</h3>
          <p>Blocking outcomes are ordered before passes, regardless of positive metrics.</p>
        </div>
        {evaluation.conflict ? (
          <p className="statePanel" data-tone="critical">
            An embedded evaluation identifier or hash conflicts with the loaded artifact. No
            substitute report is shown.
          </p>
        ) : gates.length > 0 ? (
          <div className="resultGrid">
            {gates.map((gate) => (
              <GateCard gate={gate} key={gate.gate_result_id} />
            ))}
          </div>
        ) : evaluation.outcome ? (
          <article className="evidenceCard" data-blocking="true">
            <div className="cardHeader">
              <div>
                <span className="cardKicker">Exact fail-closed evaluation artifact</span>
                <h3>{evaluation.outcome.promotion_state}</h3>
              </div>
              <span className="statusBadge" data-tone="critical">
                {evaluation.outcome.status}
              </span>
            </div>
            <div className="blockerBanner">
              <strong>Evaluation stopped</strong>
              <p>{evaluation.outcome.sanitized_message}</p>
            </div>
            <ul className="reasonList">
              {evaluation.outcome.reason_codes.map((reason) => (
                <li key={reason}>{reason}</li>
              ))}
            </ul>
            <p className="artifactHash visualMask">
              Outcome SHA-256: {evaluation.outcome.outcome_sha256}
            </p>
          </article>
        ) : (
          <p className="statePanel" data-tone="critical">
            No complete evaluation report was persisted for this run. The last real artifact is
            shown and no later result is inferred.
          </p>
        )}
      </section>

      <section aria-labelledby={`reproduction-${run.run_id}`}>
        <div className="sectionHeading">
          <h3 id={`reproduction-${run.run_id}`}>Phase 6 source-reproduction audit</h3>
          <p>This audit proves prepared-source reproduction only; it is not a general audit entry.</p>
        </div>
        <dl className="keyValueGrid">
          <div>
            <dt>Audit ID</dt>
            <dd className="mono visualMask">{run.source_reproduction_audit.audit_id}</dd>
          </div>
          <div>
            <dt>Exact match</dt>
            <dd>{String(run.source_reproduction_audit.exact_match)}</dd>
          </div>
          <div>
            <dt>Audit SHA-256</dt>
            <dd className="artifactHash visualMask">
              {run.source_reproduction_audit.audit_sha256}
            </dd>
          </div>
          <div>
            <dt>Prepared pipeline input SHA-256</dt>
            <dd className="artifactHash visualMask">{run.pipeline_input_sha256}</dd>
          </div>
        </dl>
      </section>

      <div className="cardFooter">
        <span>Synthetic evidence; no real performance claimed</span>
        <Link className="lineageLink" href={`/lineage?run_id=${run.run_id}`}>
          Trace source to artifact
        </Link>
      </div>
    </article>
  );
}

type SubmissionState =
  | { status: "idle" }
  | { status: "submitting" }
  | { status: "success"; runId: string }
  | { status: "error"; error: ApiFailure };

export function ResearchRunForm({ index, reload }: { index: EvidenceIndex; reload: () => void }) {
  const initialMapping = index.mappings[0];
  const initialMappingId = initialMapping?.mapping.mapping_id ?? "";
  const [mappingId, setMappingId] = useState(initialMappingId);
  const selectedMapping = useMemo(
    () => index.mappings.find(({ mapping }) => mapping.mapping_id === mappingId),
    [index.mappings, mappingId],
  );
  const researchConfigurations = useMemo(
    () => [...new Set(index.researchRuns.map((run) => run.configuration_id))],
    [index.researchRuns],
  );
  const [configurationId, setConfigurationId] = useState<ResearchConfigurationId | "">(
    researchConfigurations[0] ?? "",
  );
  const eligibleSnapshots = useMemo(
    () =>
      selectedMapping
        ? index.snapshots.filter((snapshot) =>
            snapshotMatchesMapping(snapshot, selectedMapping),
          )
        : [],
    [index.snapshots, selectedMapping],
  );
  const snapshotLineageConflict = useMemo(
    () =>
      Boolean(
        selectedMapping &&
          index.snapshots.some(
            (snapshot) => {
              const payload = snapshot.manifest.payload;
              const selectedMappingId = selectedMapping.mapping.mapping_id;
              return (
                (payload.mapping.mapping_id === selectedMappingId ||
                  payload.request?.mapping.mapping_id === selectedMappingId) &&
                !snapshotMatchesMapping(snapshot, selectedMapping)
              );
            },
          ),
      ),
    [index.snapshots, selectedMapping],
  );
  const [snapshotIds, setSnapshotIds] = useState<string[]>(() =>
    initialMapping
      ? index.snapshots
          .filter((snapshot) => snapshotMatchesMapping(snapshot, initialMapping))
          .map((snapshot) => snapshot.snapshot_id)
      : [],
  );
  const [submission, setSubmission] = useState<SubmissionState>({ status: "idle" });
  const selectedSnapshotsAreEligible =
    snapshotIds.length > 0 &&
    snapshotIds.every((snapshotId) =>
      eligibleSnapshots.some((snapshot) => snapshot.snapshot_id === snapshotId),
    );

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (
      !selectedMapping ||
      !configurationId ||
      snapshotLineageConflict ||
      !selectedSnapshotsAreEligible
    ) {
      return;
    }
    setSubmission({ status: "submitting" });
    const result = await fable5Api.createResearchRun({
      mapping_id: selectedMapping.mapping.mapping_id,
      research_configuration_id: configurationId,
      snapshot_ids: snapshotIds,
    });
    if (!result.ok) {
      setSubmission({ status: "error", error: result.error });
      return;
    }
    setSubmission({ status: "success", runId: result.data.run_id });
    reload();
  }

  return (
    <section className="workflowPanel" aria-labelledby="research-run-form-heading">
      <div className="panelHeader">
        <div>
          <span className="cardKicker">Reference-only deterministic request</span>
          <h2 id="research-run-form-heading">Run existing mock research</h2>
        </div>
        <p>The request contains only a mapping, snapshot identifiers, and a frozen configuration identity.</p>
      </div>
      <form onSubmit={submit}>
        <div className="formGrid">
          <div className="fieldGroup">
            <label htmlFor="research-mapping">Persisted mapping</label>
            <select
              className="visualMask"
              id="research-mapping"
              value={mappingId}
              onChange={(event) => {
                const nextMappingId = event.target.value;
                const nextMapping = index.mappings.find(
                  ({ mapping }) => mapping.mapping_id === nextMappingId,
                );
                setMappingId(nextMappingId);
                setSnapshotIds(
                  nextMapping
                    ? index.snapshots
                        .filter((snapshot) =>
                          snapshotMatchesMapping(snapshot, nextMapping),
                        )
                        .map((snapshot) => snapshot.snapshot_id)
                    : [],
                );
              }}
              required
            >
              {index.mappings.map(({ mapping }) => (
                <option key={mapping.mapping_id} value={mapping.mapping_id}>
                  {mapping.canonical_family ?? "Unmapped"} - {mapping.mapping_id}
                </option>
              ))}
            </select>
          </div>
          <div className="fieldGroup">
            <label htmlFor="research-configuration">Frozen configuration identity</label>
            <select
              id="research-configuration"
              value={configurationId}
              onChange={(event) =>
                setConfigurationId(event.target.value as ResearchConfigurationId)
              }
            >
              {researchConfigurations.map((configuration) => (
                <option key={configuration} value={configuration}>
                  {configuration}
                </option>
              ))}
            </select>
            <p className="fieldHint">Names are identities, never verdicts.</p>
          </div>
          <fieldset className="fieldGroup" data-span="full">
            <legend className="fieldLabel">Point-in-time snapshots</legend>
            {snapshotLineageConflict ? (
              <p className="statePanel" data-tone="critical" role="alert">
                Snapshot lineage conflict. A persisted snapshot shares this mapping ID but its
                immutable mapping hash, version, or identity conflicts with the selected mapping.
                No snapshot is eligible and the reference-only request remains unavailable.
              </p>
            ) : eligibleSnapshots.length > 0 ? (
              <div className="chipList">
                {eligibleSnapshots.map((snapshot) => (
                  <label className="evidenceChip" key={snapshot.snapshot_id}>
                    <input
                      checked={snapshotIds.includes(snapshot.snapshot_id)}
                      onChange={(event) =>
                        setSnapshotIds((current) =>
                          event.target.checked
                            ? [...current, snapshot.snapshot_id]
                            : current.filter((id) => id !== snapshot.snapshot_id),
                        )
                      }
                      type="checkbox"
                    />{" "}
                    {snapshot.manifest.payload.request.capability} (
                    <span className="mono visualMask">{snapshot.snapshot_id}</span>)
                  </label>
                ))}
              </div>
            ) : (
              <p className="statePanel" data-tone="critical" role="status" aria-live="polite">
                No persisted snapshots match this mapping. The request remains unavailable.
              </p>
            )}
          </fieldset>
          <div className="formActions">
            <button
              className="buttonPrimary"
              disabled={
                submission.status === "submitting" ||
                !selectedMapping ||
                !configurationId ||
                snapshotLineageConflict ||
                !selectedSnapshotsAreEligible
              }
              type="submit"
            >
              {submission.status === "submitting" ? "Running deterministic research..." : "Run mock research"}
            </button>
            <span className="formHint">No label, threshold, verdict, or approval is client supplied.</span>
          </div>
        </div>
      </form>
      <div aria-live="polite" aria-atomic="true">
        {submission.status === "submitting" ? (
          <p className="statePanel" role="status">
            Resolving references and running deterministic mock research...
          </p>
        ) : null}
        {submission.status === "success" ? (
          <p className="statePanel" data-tone="success">
            Immutable research artifact loaded: <span className="mono">{submission.runId}</span>
          </p>
        ) : null}
        {submission.status === "error" ? (
          <p className="statePanel" role="alert">
            {submission.error.message}
            {submission.error.retrySafe ? " This reference-only request can be retried safely." : ""}
          </p>
        ) : null}
      </div>
    </section>
  );
}

export function ResearchWorkspace() {
  const evidence = useEvidenceIndex();
  const {
    retry: retryEvidenceLoad,
    setRetryButton: setEvidenceRetryButton,
  } = useEvidenceRetryFocus(evidence.status, evidence.reload);

  return (
    <div
      className="workflowStack"
      data-visual-corpus={
        evidence.status === "success" &&
        evidence.data.cards.length > 0 &&
        evidence.data.cards.every((card) => card.synthetic_fixture)
          ? "synthetic"
          : "unverified"
      }
    >
      <div className="boundaryNotice" data-tone="critical">
        <strong>Gate-first presentation</strong>
        <p>
          Leakage, failed cost stress, high PBO, uncomputable diagnostics, and missing policy
          evidence outrank every favorable statistic. PASS_RESEARCH alone is never approval.
        </p>
      </div>

      {evidence.status === "loading" ? (
        <p className="statePanel" role="status">
          {evidence.message}
        </p>
      ) : null}
      {evidence.status === "empty" ? (
        <p className="statePanel" role="status" aria-live="polite">
          {evidence.message}
        </p>
      ) : null}
      {evidence.status === "error" ? (
        <div className="statePanel" role="alert">
          <p>{evidence.error.message}</p>
          {evidence.retrySafe ? (
            <button
              className="buttonSecondary"
              onClick={retryEvidenceLoad}
              ref={setEvidenceRetryButton}
              type="button"
            >
              Retry evidence load
            </button>
          ) : null}
        </div>
      ) : null}

      {evidence.status === "success" ? (
        <>
          <ResearchRunForm index={evidence.data} reload={evidence.reload} />
          <section aria-labelledby="research-results-heading">
            <div className="sectionHeading">
              <h2 id="research-results-heading">Persisted research evidence</h2>
              <p>Complete hash-bound artifacts are shown; configuration names do not determine their outcome.</p>
            </div>
            {evidence.data.researchRuns.length > 0 ? (
              <div className="governanceGrid">
                {[...evidence.data.researchRuns]
                  .sort(
                    (left, right) =>
                      Number(researchRunIsBlocking(evidence.data, right)) -
                      Number(researchRunIsBlocking(evidence.data, left)),
                  )
                  .map((run) => (
                    <ResearchRunCard index={evidence.data} key={run.run_id} run={run} />
                  ))}
              </div>
            ) : (
              <p className="statePanel" role="status" aria-live="polite">
                No immutable research artifacts are available.
              </p>
            )}
          </section>
        </>
      ) : null}
    </div>
  );
}
