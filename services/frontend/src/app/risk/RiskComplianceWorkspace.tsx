"use client";

import type { components } from "@fable5/contracts";
import { type FormEvent, useState } from "react";

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
import { type ApiFailure, fable5Api } from "../../lib/api";
import {
  type EvidenceIndex,
  revocationMatchesAssessment,
  useEvidenceIndex,
} from "../../lib/evidence-index";
import { useEvidenceRetryFocus } from "../../lib/use-evidence-retry-focus";

type ApprovalAssessmentCreateRequest = components["schemas"]["ApprovalAssessmentCreateRequest"];
type ApprovalRevocationCreateRequest = components["schemas"]["ApprovalRevocationCreateRequest"];

type CreationState =
  | { status: "idle"; message: string }
  | { status: "loading"; message: string }
  | { status: "error"; error: ApiFailure }
  | {
      status: "success";
      artifactSha256: string;
      identifier: string;
      message: string;
    };

const emptyAssessmentRequest: ApprovalAssessmentCreateRequest = {
  approval_policy_version_id: "",
  approval_scope_version_id: "",
  human_authorization_evidence_id: "",
  research_run_id: "",
  risk_input_id: "",
};

const emptyRevocationRequest: ApprovalRevocationCreateRequest = {
  human_authorization_evidence_id: "",
  revocation_evidence_id: "",
};

function failureHeading(kind: ApiFailure["kind"]) {
  switch (kind) {
    case "validation":
      return "Validation blocked";
    case "conflict":
      return "Immutable evidence conflict";
    case "not-found":
      return "Referenced evidence unavailable";
    case "malformed":
      return "Malformed API response";
    case "aborted":
      return "Request cancelled";
    default:
      return "Governance API unavailable";
  }
}

function CreationFeedback({
  onRefresh,
  state,
}: Readonly<{ onRefresh: () => void; state: CreationState }>) {
  if (state.status === "error") {
    return (
      <div className="statePanel" role="alert">
        <strong>{failureHeading(state.error.kind)}</strong>
        <p>{state.error.message}</p>
        <p>{state.error.retrySafe ? "Retry-safe request." : "Review the references before retrying."}</p>
      </div>
    );
  }

  if (state.status === "success") {
    return (
      <div className="statePanel" data-tone="success" role="status" aria-live="polite">
        <strong>{state.message}</strong>
        <p className="mono">ID: {state.identifier}</p>
        <p className="mono">Artifact SHA-256: {state.artifactSha256}</p>
        <button className="buttonSecondary" type="button" onClick={onRefresh}>
          Refresh immutable index
        </button>
      </div>
    );
  }

  return (
    <p className="statePanel" role="status" aria-live="polite">
      {state.message}
    </p>
  );
}

function AssessmentReferenceForm({ reload }: Readonly<{ reload: () => void }>) {
  const [request, setRequest] = useState<ApprovalAssessmentCreateRequest>(emptyAssessmentRequest);
  const [state, setState] = useState<CreationState>({
    message: "No assessment create request has been sent.",
    status: "idle",
  });

  function update(field: keyof ApprovalAssessmentCreateRequest, value: string) {
    setRequest((current) => ({ ...current, [field]: value }));
  }

  async function createAssessment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setState({ message: "Resolving immutable assessment references...", status: "loading" });
    const result = await fable5Api.createApprovalAssessment(request);
    if (!result.ok) {
      setState({ error: result.error, status: "error" });
      return;
    }
    setState({
      artifactSha256: result.data.artifact_sha256,
      identifier: result.data.assessment_id,
      message: "Immutable assessment artifact returned by the server.",
      status: "success",
    });
    setRequest(emptyAssessmentRequest);
  }

  return (
    <section className="workflowPanel" aria-labelledby="assessment-create-heading">
      <div className="panelHeader">
        <div>
          <span className="cardKicker">References only</span>
          <h2 id="assessment-create-heading">Create assessment artifact</h2>
        </div>
        <p>Every outcome, check, value, hash, and timestamp is resolved by the server.</p>
      </div>
      <form onSubmit={createAssessment}>
        <div className="formGrid">
          <div className="fieldGroup">
            <label htmlFor="assessment-research-run-id">Research run ID</label>
            <input
              id="assessment-research-run-id"
              name="research_run_id"
              value={request.research_run_id}
              onChange={(event) => update("research_run_id", event.target.value)}
              required
              autoComplete="off"
              spellCheck={false}
            />
          </div>
          <div className="fieldGroup">
            <label htmlFor="assessment-policy-id">Approval policy version ID</label>
            <input
              id="assessment-policy-id"
              name="approval_policy_version_id"
              value={request.approval_policy_version_id}
              onChange={(event) => update("approval_policy_version_id", event.target.value)}
              required
              autoComplete="off"
              spellCheck={false}
            />
          </div>
          <div className="fieldGroup">
            <label htmlFor="assessment-scope-id">Approval scope version ID</label>
            <input
              id="assessment-scope-id"
              name="approval_scope_version_id"
              value={request.approval_scope_version_id}
              onChange={(event) => update("approval_scope_version_id", event.target.value)}
              required
              autoComplete="off"
              spellCheck={false}
            />
          </div>
          <div className="fieldGroup">
            <label htmlFor="assessment-authorization-id">Human authorization evidence ID</label>
            <input
              id="assessment-authorization-id"
              name="human_authorization_evidence_id"
              value={request.human_authorization_evidence_id}
              onChange={(event) =>
                update("human_authorization_evidence_id", event.target.value)
              }
              required
              autoComplete="off"
              spellCheck={false}
            />
          </div>
          <div className="fieldGroup">
            <label htmlFor="assessment-risk-input-id">Risk input ID</label>
            <input
              id="assessment-risk-input-id"
              name="risk_input_id"
              value={request.risk_input_id}
              onChange={(event) => update("risk_input_id", event.target.value)}
              required
              autoComplete="off"
              spellCheck={false}
            />
          </div>
          <div className="formActions">
            <button className="buttonPrimary" type="submit" disabled={state.status === "loading"}>
              Create from references
            </button>
            <p className="formHint">
              Input fields are the exact generated request identifiers. No client result fields
              exist.
            </p>
          </div>
        </div>
      </form>
      <CreationFeedback onRefresh={reload} state={state} />
    </section>
  );
}

function RevocationReferenceForm({ reload }: Readonly<{ reload: () => void }>) {
  const [request, setRequest] = useState<ApprovalRevocationCreateRequest>(emptyRevocationRequest);
  const [state, setState] = useState<CreationState>({
    message: "No revocation create request has been sent.",
    status: "idle",
  });

  function update(field: keyof ApprovalRevocationCreateRequest, value: string) {
    setRequest((current) => ({ ...current, [field]: value }));
  }

  async function createRevocation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setState({ message: "Resolving immutable revocation references...", status: "loading" });
    const result = await fable5Api.createApprovalRevocation(request);
    if (!result.ok) {
      setState({ error: result.error, status: "error" });
      return;
    }
    setState({
      artifactSha256: result.data.artifact_sha256,
      identifier: result.data.revocation_id,
      message: "Immutable revocation artifact returned by the server.",
      status: "success",
    });
    setRequest(emptyRevocationRequest);
  }

  return (
    <section className="workflowPanel" aria-labelledby="revocation-create-heading">
      <div className="panelHeader">
        <div>
          <span className="cardKicker">References only</span>
          <h2 id="revocation-create-heading">Create revocation artifact</h2>
        </div>
        <p>The server resolves authorization and revocation evidence and derives the artifact.</p>
      </div>
      <form onSubmit={createRevocation}>
        <div className="formGrid">
          <div className="fieldGroup">
            <label htmlFor="revocation-authorization-id">Human authorization evidence ID</label>
            <input
              id="revocation-authorization-id"
              name="human_authorization_evidence_id"
              value={request.human_authorization_evidence_id}
              onChange={(event) =>
                update("human_authorization_evidence_id", event.target.value)
              }
              required
              autoComplete="off"
              spellCheck={false}
            />
          </div>
          <div className="fieldGroup">
            <label htmlFor="revocation-evidence-id">Revocation evidence ID</label>
            <input
              id="revocation-evidence-id"
              name="revocation_evidence_id"
              value={request.revocation_evidence_id}
              onChange={(event) => update("revocation_evidence_id", event.target.value)}
              required
              autoComplete="off"
              spellCheck={false}
            />
          </div>
          <div className="formActions">
            <button className="buttonPrimary" type="submit" disabled={state.status === "loading"}>
              Create from references
            </button>
            <p className="formHint">
              The client supplies identifiers only; it cannot set revocation state or evidence
              contents.
            </p>
          </div>
        </div>
      </form>
      <CreationFeedback onRefresh={reload} state={state} />
    </section>
  );
}

function RiskAssessmentCard({
  assessment,
  index,
}: Readonly<{ assessment: AssessmentArtifact; index: EvidenceIndex }>) {
  const blockingChecks = assessment.checks.filter((check) => check.status !== "PASS");
  const revocations = revocationsForAssessment(index, assessment);
  const missingBoundRevocations = missingBoundRevocationIds(index, assessment);
  const timelineFailure = timelineFailureForAssessment(index, assessment.assessment_id);
  const blocking =
    blockingChecks.length > 0 ||
    assessment.outcome === "FAIL_REJECT" ||
    Boolean(timelineFailure) ||
    revocations.length > 0 ||
    missingBoundRevocations.length > 0;

  return (
    <article
      className="governanceCard"
      data-blocking={blocking ? "true" : undefined}
      aria-labelledby={`risk-assessment-${assessment.assessment_id}`}
    >
      <div className="cardHeader">
        <div>
          <span className="cardKicker">Complete immutable assessment</span>
          <h2 className="visualMask" id={`risk-assessment-${assessment.assessment_id}`}>
            {assessment.assessment_id}
          </h2>
        </div>
        <span
          className="statusBadge"
          data-tone={blocking ? "critical" : "simulated"}
        >
          {assessment.outcome}
        </span>
      </div>

      {blocking ? (
        <div className="blockerBanner">
          <strong>Blocking evidence first</strong>
          <p>
            {blockingChecks.length} non-passing check(s); {revocations.length} linked revocation
            artifact(s); {missingBoundRevocations.length} unresolved bound revocation reference(s);{" "}
            {timelineFailure ? 1 : 0} unresolved historical timeline. The stored outcome remains{" "}
            {assessment.outcome}.
          </p>
          {blockingChecks.length > 0 ? (
            <ul className="reasonList">
              {blockingChecks.map((check) => (
                <li key={`${check.ordinal}-${check.code}`}>
                  {check.code}: {check.status} ({check.reason_code})
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : (
        <div className="boundaryNotice" data-tone="simulated">
          <strong>Historical simulated status</strong>
          <p>A positive stored outcome is governance evidence, never executable authority.</p>
        </div>
      )}

      <dl className="keyValueGrid">
        <div>
          <dt>Outcome</dt>
          <dd>{assessment.outcome}</dd>
        </div>
        <div>
          <dt>Created at UTC</dt>
          <dd>
            <time dateTime={assessment.created_at_utc}>{assessment.created_at_utc}</time>
          </dd>
        </div>
        <div>
          <dt>Research run ID</dt>
          <dd className="mono">{assessment.research_run_id}</dd>
        </div>
        <div>
          <dt>Approval policy version ID</dt>
          <dd className="mono">{assessment.approval_policy_version_id}</dd>
        </div>
        <div>
          <dt>Approval scope version ID</dt>
          <dd className="mono">{assessment.approval_scope_version_id}</dd>
        </div>
        <div>
          <dt>Human authorization evidence ID</dt>
          <dd className="mono">{assessment.human_authorization_evidence_id}</dd>
        </div>
        <div>
          <dt>Risk input ID</dt>
          <dd className="mono">{assessment.risk_input_id}</dd>
        </div>
        <div>
          <dt>Phase 7 code version</dt>
          <dd className="mono">{assessment.phase7_code_version_git_sha}</dd>
        </div>
        <div>
          <dt>Execution authorized</dt>
          <dd>{String(assessment.execution_authorized)}</dd>
        </div>
        <div>
          <dt>Execution ready</dt>
          <dd>{String(assessment.execution_ready)}</dd>
        </div>
      </dl>

      <section aria-labelledby={`risk-reasons-${assessment.assessment_id}`}>
        <div className="sectionHeading">
          <h3 id={`risk-reasons-${assessment.assessment_id}`}>Assessment reason codes</h3>
          <p>Immutable server-derived reasons, shown without client interpretation.</p>
        </div>
        <ul className="reasonList">
          {assessment.reason_codes.map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>
      </section>

      <AssessmentArtifactHashes assessment={assessment} />
      <OrderedAssessmentChecks assessment={assessment} />
      <HistoricalEvidenceTimeline
        assessmentId={assessment.assessment_id}
        failure={timelineFailure}
        timeline={timelineForAssessment(index, assessment.assessment_id)}
      />

      <section aria-labelledby={`bound-revocations-${assessment.assessment_id}`}>
        <div className="sectionHeading">
          <h3 id={`bound-revocations-${assessment.assessment_id}`}>
            Immutable revocation references
          </h3>
          <p>Assessment-bound identifiers remain part of the artifact.</p>
        </div>
        {assessment.revocation_ids.length > 0 ? (
          <ul className="chipList">
            {assessment.revocation_ids.map((revocationId) => (
              <li className="visualMask" key={revocationId}>
                {revocationId}
              </li>
            ))}
          </ul>
        ) : (
          <p className="statePanel">No revocation identifier was bound when this artifact formed.</p>
        )}
      </section>

      <div className="cardFooter">
        <span>Complete hash-bound domain artifact</span>
        <a className="lineageLink" href={`/lineage?assessment_id=${assessment.assessment_id}`}>
          Trace source to artifact
        </a>
      </div>
    </article>
  );
}

export function RiskComplianceWorkspace() {
  const evidence = useEvidenceIndex();
  const {
    retry: retryEvidenceLoad,
    setRetryButton: setEvidenceRetryButton,
  } = useEvidenceRetryFocus(evidence.status, evidence.reload);

  return (
    <div
      className="pageShell"
      data-visual-corpus={
        evidence.status === "success" &&
        evidence.data.cards.length > 0 &&
        evidence.data.cards.every((card) => card.synthetic_fixture)
          ? "synthetic"
          : "unverified"
      }
    >
      <header className="workspaceHeader">
        <div>
          <p className="eyebrow">Mode 04 - Immutable governance</p>
          <h1>Risk / Compliance</h1>
        </div>
        <p>
          Inspect ordered Phase 7 checks, historical evidence dates, immutable hashes, and
          revocation history. Missing or conflicting evidence remains fail-closed.
        </p>
      </header>

      <div className="boundaryNotice" data-tone="critical">
        <strong>Governance boundary</strong>
        <p>
          Blocking evidence is presented before positive metrics. Nothing on this surface grants
          executable authority or changes a persisted result.
        </p>
      </div>

      {evidence.status === "loading" || evidence.status === "empty" ? (
        <p className="statePanel" role="status" aria-live="polite">
          {evidence.message}
        </p>
      ) : null}

      {evidence.status === "error" ? (
        <div className="statePanel" role="alert">
          <strong>Governance evidence could not be loaded.</strong>
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
          <section aria-labelledby="risk-assessments-heading">
            <div className="sectionHeading">
              <h2 id="risk-assessments-heading">Complete assessment history</h2>
              <p>
                Blocking artifacts appear first. Every stored assessment and exact server ordinal
                remains visible.
              </p>
            </div>
            {evidence.data.assessments.length === 0 ? (
              <p className="statePanel" role="status">
                No immutable approval assessments are available.
              </p>
            ) : (
              <div className="governanceGrid">
                {[...evidence.data.assessments]
                  .sort((left, right) => {
                    const leftBlocking =
                      left.checks.some((check) => check.status !== "PASS") ||
                      left.outcome === "FAIL_REJECT" ||
                      Boolean(
                        timelineFailureForAssessment(evidence.data, left.assessment_id),
                      ) ||
                      revocationsForAssessment(evidence.data, left).length > 0 ||
                      missingBoundRevocationIds(evidence.data, left).length > 0;
                    const rightBlocking =
                      right.checks.some((check) => check.status !== "PASS") ||
                      right.outcome === "FAIL_REJECT" ||
                      Boolean(
                        timelineFailureForAssessment(evidence.data, right.assessment_id),
                      ) ||
                      revocationsForAssessment(evidence.data, right).length > 0 ||
                      missingBoundRevocationIds(evidence.data, right).length > 0;
                    return Number(rightBlocking) - Number(leftBlocking);
                  })
                  .map((assessment) => (
                    <RiskAssessmentCard
                      key={assessment.assessment_id}
                      assessment={assessment}
                      index={evidence.data}
                    />
                  ))}
              </div>
            )}
          </section>

          <section aria-labelledby="risk-revocations-heading">
            <div className="sectionHeading">
              <h2 id="risk-revocations-heading">Immutable revocation history</h2>
              <p>Each complete artifact links directly to its source-to-artifact lineage route.</p>
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
                      .filter(
                        (assessment) => revocationMatchesAssessment(revocation, assessment),
                      )
                      .map((assessment) => assessment.assessment_id)}
                    key={revocation.revocation_id}
                    revocation={revocation}
                    showNonCapabilityFlags
                  />
                ))}
              </div>
            )}
          </section>

          <section aria-labelledby="reference-creates-heading">
            <div className="sectionHeading">
              <h2 id="reference-creates-heading">Reference-only governance creates</h2>
              <p>
                Generated request contracts permit exact evidence identifiers only. The client
                supplies no timestamps, hashes, thresholds, verdicts, currentness, or risk results.
              </p>
            </div>
            <div className="governanceGrid">
              <AssessmentReferenceForm reload={evidence.reload} />
              <RevocationReferenceForm reload={evidence.reload} />
            </div>
          </section>
        </>
      ) : null}
    </div>
  );
}
