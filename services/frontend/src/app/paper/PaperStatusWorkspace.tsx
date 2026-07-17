"use client";

import type { components } from "@fable5/contracts";
import {
  type FormEvent,
  type RefObject,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import {
  AssessmentArtifactHashes,
  type AssessmentArtifact,
  HistoricalEvidenceTimeline,
  missingBoundRevocationIds,
  OrderedAssessmentChecks,
  RevocationEvidenceCard,
  revocationsForAssessment,
  timelineFailureForAssessment,
  timelineForAssessment,
} from "../../components/GovernanceEvidence";
import {
  type ApiFailure,
  fable5Api,
  type PaperSimulationCreateRequest,
} from "../../lib/api";
import {
  type EvidenceIndex,
  revocationMatchesAssessment,
  useEvidenceIndex,
} from "../../lib/evidence-index";
import { useEvidenceRetryFocus } from "../../lib/use-evidence-retry-focus";

type PaperSimulationArtifact = components["schemas"]["PaperSimulationArtifact"];
type PaperSimulationSummary = components["schemas"]["PaperSimulationSummary"];

type SimulationHistoryState =
  | { status: "loading" }
  | { status: "empty" }
  | { status: "success"; artifacts: PaperSimulationArtifact[] }
  | { status: "error"; error: ApiFailure };

type SimulationSubmissionState =
  | { status: "idle" }
  | { status: "working"; request: PaperSimulationCreateRequest }
  | { status: "error"; error: ApiFailure; request: PaperSimulationCreateRequest }
  | {
      status: "success";
      artifact: PaperSimulationArtifact;
      request: PaperSimulationCreateRequest;
    };

function simulationConflict(message: string): ApiFailure {
  return {
    kind: "conflict",
    message,
    retrySafe: false,
  };
}

function sameOrderedStrings(left: readonly string[], right: readonly string[]) {
  return left.length === right.length && left.every((value, index) => value === right[index]);
}

function summaryMatchesArtifact(
  summary: PaperSimulationSummary,
  artifact: PaperSimulationArtifact,
) {
  return (
    summary.artifact_sha256 === artifact.artifact_sha256 &&
    summary.configuration_id === artifact.configuration.configuration_id &&
    summary.created_at_utc === artifact.created_at_utc &&
    summary.decision_time_utc === artifact.decision_time_utc &&
    summary.external_submission === artifact.external_submission &&
    summary.live_path_absent === artifact.live_path_absent &&
    summary.local_mock_only === artifact.local_mock_only &&
    summary.no_personalized_investment_advice ===
      artifact.no_personalized_investment_advice &&
    summary.no_real_performance_claimed === artifact.no_real_performance_claimed &&
    summary.outcome === artifact.outcome &&
    sameOrderedStrings(summary.reason_codes, artifact.reason_codes) &&
    summary.simulated_paper_only === artifact.simulated_paper_only &&
    summary.simulation_run_id === artifact.simulation_run_id &&
    summary.source_assessment_id === artifact.source_assessment_id &&
    summary.synthetic === artifact.synthetic &&
    summary.transition_assessment_id === artifact.transition_assessment_id
  );
}

function artifactMatchesRequest(
  artifact: PaperSimulationArtifact,
  request: PaperSimulationCreateRequest,
) {
  return (
    artifact.source_assessment_id === request.approval_assessment_id &&
    artifact.simulation_idempotency_key === request.simulation_idempotency_key
  );
}

function assessmentHasKnownBlocker(index: EvidenceIndex, assessment: AssessmentArtifact) {
  return (
    assessment.outcome === "FAIL_REJECT" ||
    assessment.checks.some((check) => check.status !== "PASS") ||
    Boolean(timelineFailureForAssessment(index, assessment.assessment_id)) ||
    revocationsForAssessment(index, assessment).length > 0 ||
    missingBoundRevocationIds(index, assessment).length > 0
  );
}

function PaperAssessmentCard({
  assessment,
  index,
}: Readonly<{ assessment: AssessmentArtifact; index: EvidenceIndex }>) {
  const revocations = revocationsForAssessment(index, assessment);
  const missingBoundRevocations = missingBoundRevocationIds(index, assessment);
  const blockingChecks = assessment.checks.filter((check) => check.status !== "PASS");
  const timelineFailure = timelineFailureForAssessment(index, assessment.assessment_id);
  const hasBlockingEvidence = assessmentHasKnownBlocker(index, assessment);

  return (
    <article
      className="governanceCard"
      data-blocking={hasBlockingEvidence ? "true" : undefined}
      aria-labelledby={`paper-assessment-${assessment.assessment_id}`}
    >
      <div className="cardHeader">
        <div>
          <span className="cardKicker">Historical Phase 7 assessment</span>
          <h2 className="visualMask" id={`paper-assessment-${assessment.assessment_id}`}>
            {assessment.assessment_id}
          </h2>
        </div>
        <span
          className="statusBadge"
          data-tone={hasBlockingEvidence ? "critical" : "simulated"}
        >
          {assessment.outcome}
        </span>
      </div>

      {hasBlockingEvidence ? (
        <div className="blockerBanner">
          <strong>Blocking evidence dominates this historical result</strong>
          <p>
            {blockingChecks.length} non-passing server check(s); {revocations.length} immutable
            revocation artifact(s); {missingBoundRevocations.length} unresolved bound revocation
            reference(s); {timelineFailure ? 1 : 0} unresolved historical timeline.
          </p>
        </div>
      ) : null}

      <div className="boundaryNotice" data-tone="simulated">
        <strong>SIMULATED</strong>
        <p>
          APPROVED_PAPER is a stored governance label only. Phase 10 independently revalidates
          current immutable evidence before any local mock simulation.
        </p>
      </div>

      <dl className="keyValueGrid">
        <div>
          <dt>Assessment outcome</dt>
          <dd>{assessment.outcome}</dd>
        </div>
        <div>
          <dt>Created at UTC</dt>
          <dd>
            <time dateTime={assessment.created_at_utc}>{assessment.created_at_utc}</time>
          </dd>
        </div>
        <div>
          <dt>Simulated paper only</dt>
          <dd>{String(assessment.simulated_paper_only)}</dd>
        </div>
        <div>
          <dt>Research run ID</dt>
          <dd className="mono">{assessment.research_run_id}</dd>
        </div>
        <div>
          <dt>Phase 7 code version</dt>
          <dd className="mono">{assessment.phase7_code_version_git_sha}</dd>
        </div>
        <div>
          <dt>Revocations bound at assessment time</dt>
          <dd>{assessment.revocation_ids.length}</dd>
        </div>
      </dl>

      <section aria-labelledby={`reasons-${assessment.assessment_id}`}>
        <div className="sectionHeading">
          <h3 id={`reasons-${assessment.assessment_id}`}>Authoritative reason codes</h3>
          <p>These values are displayed unchanged from the immutable assessment.</p>
        </div>
        <ul className="reasonList">
          {assessment.reason_codes.map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>
      </section>

      <AssessmentArtifactHashes assessment={assessment} />
      <OrderedAssessmentChecks
        assessment={assessment}
        heading="Server currentness, revocation, and governance checks"
      />
      <HistoricalEvidenceTimeline
        assessmentId={assessment.assessment_id}
        failure={timelineFailure}
        timeline={timelineForAssessment(index, assessment.assessment_id)}
      />

      {revocations.length > 0 ? (
        <section aria-labelledby={`paper-revocations-${assessment.assessment_id}`}>
          <div className="sectionHeading">
            <h3 id={`paper-revocations-${assessment.assessment_id}`}>Revocation context</h3>
            <p>Linked by the immutable human authorization evidence identifier.</p>
          </div>
          <ul className="evidenceList">
            {revocations.map((revocation) => (
              <li key={revocation.revocation_id}>
                <strong className="visualMask">{revocation.revocation_id}</strong>
                <time dateTime={revocation.effective_at_utc}>
                  Effective {revocation.effective_at_utc}
                </time>
              </li>
            ))}
          </ul>
        </section>
      ) : (
        <p className="statePanel">
          No linked revocation artifact is present in the loaded historical corpus.
        </p>
      )}

      <div className="cardFooter">
        <span>Complete hash-bound assessment artifact</span>
        <a className="lineageLink" href={`/lineage?assessment_id=${assessment.assessment_id}`}>
          Trace source to artifact
        </a>
      </div>
    </article>
  );
}

function SimulationArtifactCard({
  artifact,
  focusRef,
}: Readonly<{
  artifact: PaperSimulationArtifact;
  focusRef?: RefObject<HTMLElement | null>;
}>) {
  const blocked = artifact.outcome === "BLOCKED";

  return (
    <article
      aria-labelledby={`simulation-${artifact.simulation_run_id}`}
      className="governanceCard simulationArtifact"
      data-blocking={blocked ? "true" : undefined}
      ref={focusRef}
      tabIndex={-1}
    >
      <div className="cardHeader">
        <div>
          <span className="cardKicker">SIMULATED / LOCAL MOCK</span>
          <h2 className="visualMask" id={`simulation-${artifact.simulation_run_id}`}>
            {artifact.simulation_run_id}
          </h2>
        </div>
        <span className="statusBadge" data-tone={blocked ? "critical" : "success"}>
          {artifact.outcome}
        </span>
      </div>

      {blocked ? (
        <div className="blockerBanner">
          <strong>BLOCKED - authoritative simulation checks did not pass</strong>
          <p>No simulated activity may be inferred from this artifact.</p>
        </div>
      ) : null}

      <div className="boundaryNotice" data-tone="simulated">
        <strong>SIMULATED / LOCAL MOCK</strong>
        <p>
          Deterministic synthetic paper simulation only. No external routing. No live path.
          No personalized investment advice and no real performance claim.
        </p>
      </div>

      <dl className="keyValueGrid simulationAuditGrid">
        <div>
          <dt>Source assessment ID</dt>
          <dd className="mono">{artifact.source_assessment_id}</dd>
        </div>
        <div>
          <dt>Transition assessment ID</dt>
          <dd className="mono">{artifact.transition_assessment_id}</dd>
        </div>
        <div>
          <dt>Created at UTC</dt>
          <dd>
            <time dateTime={artifact.created_at_utc}>{artifact.created_at_utc}</time>
          </dd>
        </div>
        <div>
          <dt>Decision time UTC</dt>
          <dd>
            <time dateTime={artifact.decision_time_utc}>{artifact.decision_time_utc}</time>
          </dd>
        </div>
        <div>
          <dt>Artifact SHA-256</dt>
          <dd className="mono">{artifact.artifact_sha256}</dd>
        </div>
        <div>
          <dt>Request fingerprint SHA-256</dt>
          <dd className="mono">{artifact.request_fingerprint_sha256}</dd>
        </div>
        <div>
          <dt>Research artifact SHA-256</dt>
          <dd className="mono">{artifact.research_artifact_sha256}</dd>
        </div>
        <div>
          <dt>Phase 6 lineage SHA-256</dt>
          <dd className="mono">{artifact.phase6_lineage_sha256}</dd>
        </div>
        <div>
          <dt>Transition currentness SHA-256</dt>
          <dd className="mono">{artifact.transition_currentness_state_sha256}</dd>
        </div>
        <div>
          <dt>Transition revocation set SHA-256</dt>
          <dd className="mono">{artifact.transition_revocation_set_sha256}</dd>
        </div>
        <div>
          <dt>Random seed</dt>
          <dd>{artifact.random_seed}</dd>
        </div>
        <div>
          <dt>Raw / effective trial count</dt>
          <dd>
            {artifact.raw_trial_count} / {artifact.effective_trial_count}
          </dd>
        </div>
        <div>
          <dt>Configuration ID</dt>
          <dd className="mono">{artifact.configuration.configuration_id}</dd>
        </div>
        <div>
          <dt>Configuration SHA-256</dt>
          <dd className="mono">{artifact.configuration.configuration_sha256}</dd>
        </div>
        <div>
          <dt>Phase 10 code version</dt>
          <dd className="mono">{artifact.phase10_code_version_git_sha}</dd>
        </div>
        <div>
          <dt>Idempotency key</dt>
          <dd className="mono">{artifact.simulation_idempotency_key}</dd>
        </div>
      </dl>

      <section aria-labelledby={`simulation-reasons-${artifact.simulation_run_id}`}>
        <div className="sectionHeading">
          <h3 id={`simulation-reasons-${artifact.simulation_run_id}`}>
            Authoritative reason codes
          </h3>
          <p>Displayed in the exact order returned by the persisted artifact.</p>
        </div>
        <ul className="reasonList">
          {artifact.reason_codes.map((reason, index) => (
            <li key={`${index}-${reason}`}>{reason}</li>
          ))}
        </ul>
      </section>

      <section aria-labelledby={`simulation-checks-${artifact.simulation_run_id}`}>
        <div className="sectionHeading">
          <h3 id={`simulation-checks-${artifact.simulation_run_id}`}>
            Ordered simulation checks
          </h3>
          <p>Server ordinals, outcomes, values, and evidence hashes remain unchanged.</p>
        </div>
        <ol className="checkList simulationCheckList">
          {artifact.checks.map((check) => (
            <li key={check.check_sha256}>
              <div>
                <strong>
                  Server ordinal {check.ordinal}: {check.code}
                </strong>
                <p>
                  Reason: <span className="mono">{check.reason_code}</span>
                </p>
                <p>
                  Observed: <span className="mono">{check.observed_value ?? "null"}</span>;
                  threshold: <span className="mono">{check.threshold_value ?? "null"}</span>
                </p>
                <p>
                  Check SHA-256: <span className="mono">{check.check_sha256}</span>
                </p>
                <ul className="chipList simulationCheckEvidence" aria-label="Evidence SHA-256 values">
                  {check.evidence_sha256s.map((sha256, index) => (
                    <li key={`${index}-${sha256}`}>{sha256}</li>
                  ))}
                </ul>
              </div>
              <span
                className="statusBadge"
                data-tone={check.status === "PASS" ? "pass" : "critical"}
              >
                {check.status}
              </span>
            </li>
          ))}
        </ol>
      </section>

      <section aria-labelledby={`simulation-config-${artifact.simulation_run_id}`}>
        <div className="sectionHeading">
          <h3 id={`simulation-config-${artifact.simulation_run_id}`}>Bound local configuration</h3>
          <p>All parameters are server-derived; this surface exposes no trade controls.</p>
        </div>
        <dl className="keyValueGrid">
          <div>
            <dt>Configuration instance ID</dt>
            <dd className="mono">{artifact.configuration.configuration_instance_id}</dd>
          </div>
          <div>
            <dt>Mock snapshot ID</dt>
            <dd className="mono">{artifact.configuration.mock_snapshot_id}</dd>
          </div>
          <div>
            <dt>Mock snapshot SHA-256</dt>
            <dd className="mono">{artifact.configuration.mock_snapshot_sha256}</dd>
          </div>
          <div>
            <dt>Mock observation ID</dt>
            <dd className="mono">{artifact.configuration.mock_observation_id}</dd>
          </div>
          <div>
            <dt>Mock observation SHA-256</dt>
            <dd className="mono">{artifact.configuration.mock_observation_sha256}</dd>
          </div>
          <div>
            <dt>Mock universe ID</dt>
            <dd className="mono">{artifact.configuration.mock_universe_id}</dd>
          </div>
          <div>
            <dt>Signal rule</dt>
            <dd className="mono">{artifact.configuration.signal_rule_id}</dd>
          </div>
          <div>
            <dt>Forecast horizon</dt>
            <dd>{artifact.configuration.target_forecast_horizon}</dd>
          </div>
          <div>
            <dt>Local cost model</dt>
            <dd className="mono">{artifact.configuration.local_cost_model_id}</dd>
          </div>
          <div>
            <dt>Local slippage model</dt>
            <dd className="mono">{artifact.configuration.local_slippage_model_id}</dd>
          </div>
          <div>
            <dt>Required capabilities</dt>
            <dd className="mono">{artifact.configuration.required_capabilities.join(", ")}</dd>
          </div>
          <div>
            <dt>Required audit fields</dt>
            <dd className="mono">{artifact.configuration.required_audit_fields.join(", ")}</dd>
          </div>
        </dl>
      </section>

      <section aria-labelledby={`simulation-ledger-${artifact.simulation_run_id}`}>
        <div className="sectionHeading">
          <h3 id={`simulation-ledger-${artifact.simulation_run_id}`}>
            Synthetic local ledger
          </h3>
          <p>{artifact.ledger_entries.length} exact persisted ledger entry or entries.</p>
        </div>
        {artifact.ledger_entries.length === 0 ? (
          <div className="statePanel" data-tone={blocked ? "critical" : undefined}>
            <strong>{blocked ? "BLOCKED - zero ledger entries" : "Zero ledger entries"}</strong>
            <p>The artifact records no simulated ledger activity.</p>
          </div>
        ) : (
          <div className="simulationLedgerGrid">
            {artifact.ledger_entries.map((entry) => (
              <article
                aria-labelledby={`ledger-${entry.ledger_entry_id}`}
                className="evidenceCard simulationLedgerEntry"
                key={entry.ledger_entry_id}
              >
                <div className="cardHeader">
                  <div>
                    <span className="cardKicker">SIMULATED ENTRY {entry.ordinal}</span>
                    <h4 className="visualMask" id={`ledger-${entry.ledger_entry_id}`}>
                      {entry.ledger_entry_id}
                    </h4>
                  </div>
                  <span className="statusBadge" data-tone="simulated">
                    {entry.fill_status}
                  </span>
                </div>
                <dl className="keyValueGrid">
                  <div>
                    <dt>Signal / side</dt>
                    <dd>
                      {entry.signal_state} / {entry.simulated_side}
                    </dd>
                  </div>
                  <div>
                    <dt>Requested / filled / unfilled / rejected</dt>
                    <dd>
                      {entry.requested_quantity} / {entry.filled_quantity} / {entry.unfilled_quantity}
                      {" / "}
                      {entry.rejected_quantity}
                    </dd>
                  </div>
                  <div>
                    <dt>Reference / simulated fill price</dt>
                    <dd>
                      {entry.reference_price} / {entry.simulated_fill_price}
                    </dd>
                  </div>
                  <div>
                    <dt>Approved proposed notional</dt>
                    <dd>{entry.approved_proposed_notional}</dd>
                  </div>
                  <div>
                    <dt>Position before / after</dt>
                    <dd>
                      {entry.position_quantity_before} / {entry.position_quantity_after}
                    </dd>
                  </div>
                  <div>
                    <dt>Cash before / after</dt>
                    <dd>
                      {entry.cash_before} / {entry.cash_after}
                    </dd>
                  </div>
                  <div>
                    <dt>Total cost</dt>
                    <dd>{entry.total_cost}</dd>
                  </div>
                  <div>
                    <dt>Commission / spread / impact</dt>
                    <dd>
                      {entry.commission_cost} / {entry.spread_cost} / {entry.impact_cost}
                    </dd>
                  </div>
                  <div>
                    <dt>Latency / capacity / borrow / regulatory</dt>
                    <dd>
                      {entry.latency_cost} / {entry.capacity_cost} / {entry.borrow_cost} /{" "}
                      {entry.regulatory_fee_cost}
                    </dd>
                  </div>
                  <div>
                    <dt>Participation rate</dt>
                    <dd>{entry.participation_rate}</dd>
                  </div>
                  <div>
                    <dt>Ledger entry SHA-256</dt>
                    <dd className="mono">{entry.ledger_entry_sha256}</dd>
                  </div>
                  <div>
                    <dt>External submission / live path absent</dt>
                    <dd>
                      {String(entry.external_submission)} / {String(entry.live_path_absent)}
                    </dd>
                  </div>
                </dl>
              </article>
            ))}
          </div>
        )}
      </section>

      <details className="evidenceDisclosure simulationArtifactDisclosure">
        <summary>Inspect exact persisted simulation artifact JSON</summary>
        <pre>{JSON.stringify(artifact, null, 2)}</pre>
      </details>

      <p className="simulationDisclaimer">{artifact.disclaimer}</p>
      <div className="cardFooter">
        <span>Complete hash-bound Phase 10 simulation artifact</span>
        <a
          className="lineageLink"
          href={`/lineage?assessment_id=${artifact.source_assessment_id}&simulation_run_id=${artifact.simulation_run_id}`}
        >
          Trace source to artifact
        </a>
      </div>
    </article>
  );
}

export function PaperStatusWorkspace({
  idempotencyKeyFactory = () => globalThis.crypto.randomUUID(),
}: Readonly<{ idempotencyKeyFactory?: () => string }>) {
  const evidence = useEvidenceIndex();
  const {
    retry: retryEvidenceLoad,
    setRetryButton: setEvidenceRetryButton,
  } = useEvidenceRetryFocus(evidence.status, evidence.reload);
  const [selectedAssessmentId, setSelectedAssessmentId] = useState("");
  const [submission, setSubmission] = useState<SimulationSubmissionState>({ status: "idle" });
  const [historyState, setHistoryState] = useState<SimulationHistoryState>({
    status: "loading",
  });
  const [historyVersion, setHistoryVersion] = useState(0);
  const submissionController = useRef<AbortController | null>(null);
  const resultRef = useRef<HTMLElement>(null);
  const errorRef = useRef<HTMLDivElement>(null);

  const reloadSimulationHistory = useCallback(() => {
    setHistoryVersion((version) => version + 1);
  }, []);

  useEffect(() => {
    const controller = new AbortController();

    async function loadSimulationHistory() {
      setHistoryState({ status: "loading" });
      const summariesResult = await fable5Api.listLocalSimulations(
        controller.signal,
        undefined,
        100,
      );
      if (!summariesResult.ok) {
        if (summariesResult.error.kind !== "aborted") {
          setHistoryState({ error: summariesResult.error, status: "error" });
        }
        return;
      }
      if (summariesResult.data.length === 0) {
        setHistoryState({ status: "empty" });
        return;
      }

      const detailResults = await Promise.all(
        summariesResult.data.map((summary) =>
          fable5Api.getLocalSimulation(summary.simulation_run_id, controller.signal),
        ),
      );
      const failedDetail = detailResults.find((result) => !result.ok);
      if (failedDetail && !failedDetail.ok) {
        if (failedDetail.error.kind !== "aborted") {
          setHistoryState({ error: failedDetail.error, status: "error" });
        }
        return;
      }

      const artifacts: PaperSimulationArtifact[] = [];
      for (const [index, detailResult] of detailResults.entries()) {
        if (!detailResult.ok) return;
        const summary = summariesResult.data[index];
        if (!summary || !summaryMatchesArtifact(summary, detailResult.data)) {
          setHistoryState({
            error: simulationConflict(
              "A persisted simulation detail conflicts with its immutable list summary. No result was inferred.",
            ),
            status: "error",
          });
          return;
        }
        artifacts.push(detailResult.data);
      }
      setHistoryState({ artifacts, status: "success" });
    }

    void loadSimulationHistory();
    return () => controller.abort();
  }, [historyVersion]);

  useEffect(() => () => submissionController.current?.abort(), []);

  useEffect(() => {
    if (submission.status === "success") {
      resultRef.current?.focus({ preventScroll: true });
    } else if (submission.status === "error") {
      errorRef.current?.focus({ preventScroll: true });
    }
  }, [submission]);

  const runSimulation = useCallback(
    async (request: PaperSimulationCreateRequest) => {
      submissionController.current?.abort();
      const controller = new AbortController();
      submissionController.current = controller;
      setSubmission({ request, status: "working" });

      const result = await fable5Api.createLocalSimulation(request, controller.signal);
      if (!result.ok) {
        if (result.error.kind !== "aborted") {
          setSubmission({ error: result.error, request, status: "error" });
        }
        return;
      }
      if (!artifactMatchesRequest(result.data, request)) {
        setSubmission({
          error: simulationConflict(
            "The returned simulation artifact conflicts with the exact assessment reference or idempotency key. No result was inferred.",
          ),
          request,
          status: "error",
        });
        return;
      }

      setSubmission({ artifact: result.data, request, status: "success" });
      reloadSimulationHistory();
    },
    [reloadSimulationHistory],
  );

  const selectedAssessment =
    evidence.status === "success"
      ? evidence.data.assessments.find(
          (assessment) => assessment.assessment_id === selectedAssessmentId,
        )
      : undefined;
  const selectedAssessmentBlocked =
    evidence.status === "success" && selectedAssessment
      ? assessmentHasKnownBlocker(evidence.data, selectedAssessment)
      : false;

  function submitSimulation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedAssessment || selectedAssessmentBlocked || evidence.status !== "success") return;
    void runSimulation({
      approval_assessment_id: selectedAssessment.assessment_id,
      simulation_idempotency_key: idempotencyKeyFactory(),
    });
  }

  const visibleArtifacts = useMemo(() => {
    const historyArtifacts = historyState.status === "success" ? historyState.artifacts : [];
    if (submission.status !== "success") return historyArtifacts;
    return [
      submission.artifact,
      ...historyArtifacts.filter(
        (artifact) => artifact.simulation_run_id !== submission.artifact.simulation_run_id,
      ),
    ];
  }, [historyState, submission]);

  return (
    <div
      className="pageShell"
      data-visual-corpus={
        evidence.status === "success" &&
        evidence.data.cards.length > 0 &&
        evidence.data.cards.every((card) => card.synthetic_fixture) &&
        visibleArtifacts.every((artifact) => artifact.synthetic)
          ? "synthetic"
          : "unverified"
      }
    >
      <header className="workspaceHeader">
        <div>
          <p className="eyebrow">Mode 03 - deterministic local mock paper simulation</p>
          <h1>Simulated Paper Status</h1>
        </div>
        <p>
          Select an immutable Phase 7 assessment and ask the authoritative server to revalidate it
          against a fixed synthetic Phase 10 configuration. There are no trade parameters.
        </p>
      </header>

      <div className="boundaryNotice" data-tone="simulated">
        <strong>SIMULATED</strong>
        <p>
          Historical synthetic evidence only. No executable controls, external routing, provider,
          broker, credential, or live path exists. Phase 10 is LOCAL MOCK only. This is not
          investment advice and does not claim real performance.
        </p>
      </div>

      {evidence.status === "success" ? (
        <section className="workflowPanel simulationControlPanel" aria-labelledby="simulation-form-heading">
        <div className="panelHeader">
          <div>
            <span className="cardKicker">Reference-only request</span>
            <h2 id="simulation-form-heading">Run a local mock simulation</h2>
          </div>
          <p>
            The server derives signal, side, quantity, snapshot, costs, slippage, and audit values
            from immutable evidence.
          </p>
        </div>

        <form className="formGrid" onSubmit={submitSimulation}>
          <div className="fieldGroup" data-span="full">
            <label htmlFor="paper-approval-assessment">Approval assessment</label>
            <select
              disabled={evidence.status !== "success" || submission.status === "working"}
              id="paper-approval-assessment"
              name="approval_assessment_id"
              onChange={(event) => setSelectedAssessmentId(event.currentTarget.value)}
              required
              value={selectedAssessmentId}
            >
              <option value="">Choose an immutable assessment</option>
              {evidence.status === "success"
                ? evidence.data.assessments.map((assessment) => {
                    const blocked = assessmentHasKnownBlocker(evidence.data, assessment);
                    return (
                      <option key={assessment.assessment_id} value={assessment.assessment_id}>
                        {assessment.assessment_id} - {assessment.outcome} - {blocked ? "known blocker" : "eligible for server revalidation"}
                      </option>
                    );
                  })
                : null}
            </select>
            <p className="fieldHint">
              Selection is not execution authority. Phase 10 performs a fresh, fail-closed server
              assessment before producing a local artifact.
            </p>
          </div>

          <div className="formActions">
            <button
              className="buttonPrimary"
              disabled={
                !selectedAssessment || selectedAssessmentBlocked || submission.status === "working"
              }
              type="submit"
            >
              {submission.status === "working"
                ? "Running deterministic local simulation..."
                : "Run deterministic local simulation"}
            </button>
          </div>
        </form>

        {selectedAssessment && selectedAssessmentBlocked ? (
          <div className="statePanel" data-tone="critical" role="alert">
            <strong>Known blocking evidence prevents submission</strong>
            <p>
              The selected historical assessment has a rejection, non-passing check, unresolved
              timeline, linked revocation, or unresolved bound revocation reference.
            </p>
          </div>
        ) : null}
        {selectedAssessment && !selectedAssessmentBlocked ? (
          <p className="statePanel" role="status">
            Eligible for authoritative server revalidation. This is not execution readiness.
          </p>
        ) : null}

        <div className="simulationBoundaryGrid" aria-label="Enforced simulation boundaries">
          <span>SIMULATED PAPER ONLY</span>
          <span>LOCAL MOCK ONLY</span>
          <span>EXTERNAL ROUTING ABSENT</span>
          <span>LIVE PATH ABSENT</span>
          <span>NO PERSONALIZED ADVICE</span>
          <span>NO REAL PERFORMANCE CLAIM</span>
        </div>

        <div aria-live="polite" aria-atomic="true">
          {submission.status === "idle" ? (
            <p className="statePanel">No local simulation request has been submitted in this session.</p>
          ) : null}
          {submission.status === "working" ? (
            <p className="statePanel" role="status">
              The server is revalidating immutable governance, research, risk, cost, slippage, and
              local-boundary evidence.
            </p>
          ) : null}
          {submission.status === "error" ? (
            <div className="statePanel" ref={errorRef} role="alert" tabIndex={-1}>
              <strong>Local simulation was not accepted.</strong>
              <p>{submission.error.message}</p>
              {submission.error.kind === "unavailable" ? (
                <button
                  className="buttonSecondary"
                  onClick={() => void runSimulation(submission.request)}
                  type="button"
                >
                  Retry exact simulation request
                </button>
              ) : null}
            </div>
          ) : null}
        </div>
        </section>
      ) : null}

      <section aria-labelledby="simulation-artifacts-heading">
        <div className="sectionHeading">
          <h2 id="simulation-artifacts-heading">Persisted local simulation artifacts</h2>
          <p>
            Completed and blocked artifacts are shown exactly after generated-schema validation and
            summary-to-detail reconciliation.
          </p>
        </div>

        {historyState.status === "loading" && submission.status !== "success" ? (
          <p className="statePanel" role="status">
            Loading immutable local simulation history...
          </p>
        ) : null}
        {historyState.status === "empty" && submission.status !== "success" ? (
          <p className="statePanel" role="status">
            No persisted local simulation artifacts are available.
          </p>
        ) : null}
        {historyState.status === "error" ? (
          <div className="statePanel" role="alert">
            <strong>Local simulation history could not be reconciled.</strong>
            <p>{historyState.error.message}</p>
            {historyState.error.kind === "unavailable" ? (
              <button
                className="buttonSecondary"
                onClick={reloadSimulationHistory}
                type="button"
              >
                Retry simulation history read
              </button>
            ) : null}
          </div>
        ) : null}

        {visibleArtifacts.length > 0 ? (
          <div className="simulationArtifactGrid">
            {visibleArtifacts.map((artifact) => (
              <SimulationArtifactCard
                artifact={artifact}
                focusRef={
                  submission.status === "success" &&
                  submission.artifact.simulation_run_id === artifact.simulation_run_id
                    ? resultRef
                    : undefined
                }
                key={artifact.simulation_run_id}
              />
            ))}
          </div>
        ) : null}
      </section>

      {evidence.status === "loading" || evidence.status === "empty" ? (
        <p className="statePanel" role="status" aria-live="polite">
          {evidence.message}
        </p>
      ) : null}

      {evidence.status === "error" ? (
        <div className="statePanel" role="alert">
          <strong>Historical governance evidence could not be loaded.</strong>
          <p>{evidence.error.message}</p>
          {evidence.retrySafe ? (
            <button
              className="buttonSecondary"
              onClick={retryEvidenceLoad}
              ref={setEvidenceRetryButton}
              type="button"
            >
              Retry read
            </button>
          ) : null}
        </div>
      ) : null}

      {evidence.status === "success" ? (
        <>
          <section aria-labelledby="paper-assessments-heading">
            <div className="sectionHeading">
              <h2 id="paper-assessments-heading">Historical assessment status</h2>
              <p>
                Blocking assessments and linked revocations appear first. Stored outcomes remain
                unchanged.
              </p>
            </div>
            {evidence.data.assessments.length === 0 ? (
              <p className="statePanel" role="status">
                No immutable approval assessments are available.
              </p>
            ) : (
              <div className="governanceGrid">
                {[...evidence.data.assessments]
                  .sort(
                    (left, right) =>
                      Number(assessmentHasKnownBlocker(evidence.data, right)) -
                      Number(assessmentHasKnownBlocker(evidence.data, left)),
                  )
                  .map((assessment) => (
                    <PaperAssessmentCard
                      key={assessment.assessment_id}
                      assessment={assessment}
                      index={evidence.data}
                    />
                  ))}
              </div>
            )}
          </section>

          <section aria-labelledby="paper-revocation-history-heading">
            <div className="sectionHeading">
              <h2 id="paper-revocation-history-heading">Immutable revocation history</h2>
              <p>Full persisted revocation artifacts remain blocking evidence.</p>
            </div>
            {evidence.data.revocations.length === 0 ? (
              <p className="statePanel" role="status">
                No immutable revocation artifacts are present in the loaded corpus.
              </p>
            ) : (
              <div className="governanceGrid">
                {evidence.data.revocations.map((revocation) => (
                  <RevocationEvidenceCard
                    assessmentIds={evidence.data.assessments
                      .filter((assessment) =>
                        revocationMatchesAssessment(revocation, assessment),
                      )
                      .map((assessment) => assessment.assessment_id)}
                    key={revocation.revocation_id}
                    revocation={revocation}
                  />
                ))}
              </div>
            )}
          </section>
        </>
      ) : null}
    </div>
  );
}
