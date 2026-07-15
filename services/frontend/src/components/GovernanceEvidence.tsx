import type { components } from "@fable5/contracts";

import type { ApiFailure } from "../lib/api";
import {
  type EvidenceIndex,
  revocationMatchesAssessment,
} from "../lib/evidence-index";

export type AssessmentArtifact = EvidenceIndex["assessments"][number];
export type RevocationArtifact = EvidenceIndex["revocations"][number];
export type AssessmentTimeline = components["schemas"]["ApprovalAssessmentEvidenceTimeline"];

function statusTone(status: AssessmentArtifact["checks"][number]["status"]) {
  return status === "PASS" ? "pass" : "critical";
}

export function timelineForAssessment(index: EvidenceIndex, assessmentId: string) {
  return index.assessmentTimelines[assessmentId];
}

export function timelineFailureForAssessment(index: EvidenceIndex, assessmentId: string) {
  return index.assessmentTimelineFailures[assessmentId];
}

export function revocationsForAssessment(index: EvidenceIndex, assessment: AssessmentArtifact) {
  return index.revocations.filter((revocation) =>
    revocationMatchesAssessment(revocation, assessment),
  );
}

export function missingBoundRevocationIds(
  index: EvidenceIndex,
  assessment: AssessmentArtifact,
) {
  const exactRevocations = revocationsForAssessment(index, assessment);
  return assessment.revocation_ids.filter(
    (revocationId) =>
      !exactRevocations.some((revocation) => revocation.revocation_id === revocationId),
  );
}

export function HistoricalEvidenceTimeline({
  assessmentId,
  failure,
  timeline,
}: Readonly<{
  assessmentId: string;
  failure?: ApiFailure;
  timeline: AssessmentTimeline | undefined;
}>) {
  if (failure) {
    return (
      <section
        className="timelineCard evidenceCard"
        data-blocking="true"
        aria-labelledby={`timeline-${assessmentId}`}
      >
        <div className="cardHeader">
          <div>
            <span className="cardKicker">Fail-closed server evidence read</span>
            <h3 id={`timeline-${assessmentId}`}>Evidence timeline unavailable</h3>
          </div>
          <span className="statusBadge" data-tone="critical">
            BLOCKED
          </span>
        </div>
        <div className="blockerBanner" role="alert">
          <strong>Historical timeline evidence was not resolved</strong>
          <p>{failure.message}</p>
          <p>
            Failure kind: {failure.kind}
            {failure.status ? ` (HTTP ${failure.status})` : ""}. No date, currentness,
            approval, expiry, revocation, or readiness state is inferred.
          </p>
        </div>
      </section>
    );
  }

  if (!timeline) {
    return (
      <section aria-labelledby={`timeline-${assessmentId}`}>
        <h3 id={`timeline-${assessmentId}`}>Evidence timeline unavailable</h3>
        <p className="statePanel" data-tone="critical">
          Historical timeline evidence is unavailable. No date or governance state is inferred.
        </p>
      </section>
    );
  }

  return (
    <section
      className="timelineCard evidenceCard"
      aria-labelledby={`timeline-${timeline.assessment_id}`}
    >
      <div className="cardHeader">
        <div>
          <span className="cardKicker">Server-owned historical evidence</span>
          <h3 id={`timeline-${timeline.assessment_id}`}>Evidence timeline</h3>
        </div>
      </div>
      <p className="formHint">
        Dates are rendered exactly as served. This view does not compare them with the device
        clock or recalculate any governance result.
      </p>
      <ol className="timelineList">
        <li>
          <div>
            <strong>Assessment created</strong>
            <time dateTime={timeline.assessment_created_at_utc}>
              {timeline.assessment_created_at_utc}
            </time>
            <code>{timeline.assessment_id}</code>
          </div>
        </li>
        <li>
          <div>
            <strong>Policy validity</strong>
            <time dateTime={timeline.policy.valid_from_utc}>
              Valid from {timeline.policy.valid_from_utc}
            </time>
            <time dateTime={timeline.policy.expires_at_utc}>
              Expires {timeline.policy.expires_at_utc}
            </time>
            <code>{timeline.policy.approval_policy_version_id}</code>
            <code>SHA-256 {timeline.policy.policy_sha256}</code>
          </div>
        </li>
        <li>
          <div>
            <strong>Scope validity</strong>
            <time dateTime={timeline.scope.valid_from_utc}>
              Valid from {timeline.scope.valid_from_utc}
            </time>
            <time dateTime={timeline.scope.expires_at_utc}>
              Expires {timeline.scope.expires_at_utc}
            </time>
            <code>{timeline.scope.approval_scope_version_id}</code>
            <code>SHA-256 {timeline.scope.scope_sha256}</code>
          </div>
        </li>
        <li>
          <div>
            <strong>Human authorization validity</strong>
            <time dateTime={timeline.authorization.authorized_at_utc}>
              Authorized {timeline.authorization.authorized_at_utc}
            </time>
            <time dateTime={timeline.authorization.review_at_utc}>
              Review {timeline.authorization.review_at_utc}
            </time>
            <time dateTime={timeline.authorization.expires_at_utc}>
              Expires {timeline.authorization.expires_at_utc}
            </time>
            <code>{timeline.authorization.human_authorization_evidence_id}</code>
            <code>SHA-256 {timeline.authorization.authorization_sha256}</code>
          </div>
        </li>
        <li>
          <div>
            <strong>Risk input observation</strong>
            <time dateTime={timeline.risk_input.observed_at_utc}>
              Observed {timeline.risk_input.observed_at_utc}
            </time>
            <code>{timeline.risk_input.risk_input_id}</code>
            <code>SHA-256 {timeline.risk_input.risk_input_sha256}</code>
          </div>
        </li>
      </ol>
    </section>
  );
}

export function OrderedAssessmentChecks({
  assessment,
  heading = "Ordered server checks",
}: Readonly<{ assessment: AssessmentArtifact; heading?: string }>) {
  const checks = [...assessment.checks].sort((left, right) => left.ordinal - right.ordinal);

  return (
    <section aria-labelledby={`checks-${assessment.assessment_id}`}>
      <div className="sectionHeading">
        <h3 id={`checks-${assessment.assessment_id}`}>{heading}</h3>
        <p>
          Ordinals, statuses, values, hashes, and reasons are displayed from the immutable
          assessment. The client does not recalculate them.
        </p>
      </div>
      <ol className="checkList">
        {checks.map((check) => (
          <li key={`${check.ordinal}-${check.code}`}>
            <div>
              <strong>
                Server ordinal {check.ordinal}: {check.code}
              </strong>
              <p>Reason code: {check.reason_code}</p>
              <p>Observed value: {check.observed_value ?? "Not recorded"}</p>
              <p>Threshold value: {check.threshold_value ?? "Not recorded"}</p>
              <p className="mono">Check SHA-256: {check.check_sha256}</p>
              <p className="mono">
                Evidence SHA-256: {check.evidence_sha256s.join(", ") || "None recorded"}
              </p>
            </div>
            <span className="statusBadge" data-tone={statusTone(check.status)}>
              {check.status}
            </span>
          </li>
        ))}
      </ol>
    </section>
  );
}

export function AssessmentArtifactHashes({
  assessment,
}: Readonly<{ assessment: AssessmentArtifact }>) {
  return (
    <dl className="keyValueGrid">
      <div>
        <dt>Artifact SHA-256</dt>
        <dd className="artifactHash">{assessment.artifact_sha256}</dd>
      </div>
      <div>
        <dt>Request fingerprint SHA-256</dt>
        <dd className="artifactHash">{assessment.request_fingerprint_sha256}</dd>
      </div>
      <div>
        <dt>Currentness state SHA-256</dt>
        <dd className="artifactHash">{assessment.currentness_state_sha256}</dd>
      </div>
      <div>
        <dt>Revocation set SHA-256</dt>
        <dd className="artifactHash">{assessment.revocation_set_sha256}</dd>
      </div>
      <div>
        <dt>Approval policy SHA-256</dt>
        <dd className="artifactHash">{assessment.approval_policy_sha256}</dd>
      </div>
      <div>
        <dt>Approval scope SHA-256</dt>
        <dd className="artifactHash">{assessment.approval_scope_sha256}</dd>
      </div>
      <div>
        <dt>Authorization SHA-256</dt>
        <dd className="artifactHash">{assessment.authorization_sha256}</dd>
      </div>
      <div>
        <dt>Risk input SHA-256</dt>
        <dd className="artifactHash">{assessment.risk_input_sha256}</dd>
      </div>
    </dl>
  );
}

export function RevocationEvidenceCard({
  assessmentIds = [],
  revocation,
  showNonCapabilityFlags = false,
}: Readonly<{
  assessmentIds?: string[];
  revocation: RevocationArtifact;
  showNonCapabilityFlags?: boolean;
}>) {
  return (
    <article
      className="governanceCard"
      data-blocking="true"
      aria-labelledby={`revocation-${revocation.revocation_id}`}
    >
      <div className="cardHeader">
        <div>
          <span className="cardKicker">Immutable revocation artifact</span>
          <h3 className="visualMask" id={`revocation-${revocation.revocation_id}`}>
            {revocation.revocation_id}
          </h3>
        </div>
        <span className="statusBadge" data-tone="critical">
          Revoked
        </span>
      </div>
      <div className="blockerBanner">
        <strong>Revocation evidence</strong>
        <p>Immutable revocation evidence exists and remains blocking.</p>
      </div>
      <dl className="keyValueGrid">
        <div>
          <dt>Effective at UTC</dt>
          <dd>
            <time dateTime={revocation.effective_at_utc}>{revocation.effective_at_utc}</time>
          </dd>
        </div>
        <div>
          <dt>Created at UTC</dt>
          <dd>
            <time dateTime={revocation.created_at_utc}>{revocation.created_at_utc}</time>
          </dd>
        </div>
        <div>
          <dt>Human authorization evidence ID</dt>
          <dd className="mono">{revocation.human_authorization_evidence_id}</dd>
        </div>
        <div>
          <dt>Revocation evidence ID</dt>
          <dd className="mono">{revocation.revocation_evidence_id}</dd>
        </div>
        <div>
          <dt>Artifact SHA-256</dt>
          <dd className="artifactHash">{revocation.artifact_sha256}</dd>
        </div>
        <div>
          <dt>Request fingerprint SHA-256</dt>
          <dd className="artifactHash">{revocation.request_fingerprint_sha256}</dd>
        </div>
        <div>
          <dt>Revocation evidence SHA-256</dt>
          <dd className="artifactHash">{revocation.revocation_evidence_sha256}</dd>
        </div>
        <div>
          <dt>Authorization SHA-256</dt>
          <dd className="artifactHash">{revocation.authorization_sha256}</dd>
        </div>
        <div>
          <dt>Phase 7 code version</dt>
          <dd className="mono">{revocation.phase7_code_version_git_sha}</dd>
        </div>
        {showNonCapabilityFlags ? (
          <>
            <div>
              <dt>Execution authorized</dt>
              <dd>{String(revocation.execution_authorized)}</dd>
            </div>
            <div>
              <dt>Execution ready</dt>
              <dd>{String(revocation.execution_ready)}</dd>
            </div>
          </>
        ) : null}
      </dl>
      <div className="cardFooter">
        <span>Complete hash-bound domain artifact</span>
        {assessmentIds.length > 0 ? (
          assessmentIds.map((assessmentId) => (
            <a
              className="lineageLink"
              href={`/lineage?assessment_id=${assessmentId}&revocation_id=${revocation.revocation_id}`}
              key={assessmentId}
            >
              Trace source to artifact
            </a>
          ))
        ) : (
          <a className="lineageLink" href={`/lineage?revocation_id=${revocation.revocation_id}`}>
            Trace source to artifact
          </a>
        )}
      </div>
    </article>
  );
}
