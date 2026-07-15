"use client";

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
  type EvidenceIndex,
  revocationMatchesAssessment,
  useEvidenceIndex,
} from "../../lib/evidence-index";
import { useEvidenceRetryFocus } from "../../lib/use-evidence-retry-focus";

function PaperAssessmentCard({
  assessment,
  index,
}: Readonly<{ assessment: AssessmentArtifact; index: EvidenceIndex }>) {
  const revocations = revocationsForAssessment(index, assessment);
  const missingBoundRevocations = missingBoundRevocationIds(index, assessment);
  const blockingChecks = assessment.checks.filter((check) => check.status !== "PASS");
  const timelineFailure = timelineFailureForAssessment(index, assessment.assessment_id);
  const hasBlockingEvidence =
    assessment.outcome === "FAIL_REJECT" ||
    blockingChecks.length > 0 ||
    Boolean(timelineFailure) ||
    revocations.length > 0 ||
    missingBoundRevocations.length > 0;

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
          APPROVED_PAPER is a stored governance label only. It does not grant executable authority,
          and no executable controls exist on this surface.
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

export function PaperStatusWorkspace() {
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
          <p className="eyebrow">Mode 03 - Governance history only</p>
          <h1>Simulated Paper Status</h1>
        </div>
        <p>
          Review immutable Phase 7 assessment and revocation evidence. This read-only workspace
          cannot create executable activity or change a governance result.
        </p>
      </header>

      <div className="boundaryNotice" data-tone="simulated">
        <strong>SIMULATED</strong>
        <p>
          Historical synthetic evidence only. No executable controls, readiness claim, guarantee,
          or personalized investment advice.
        </p>
      </div>

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
                  .sort((left, right) => {
                    const leftBlocked =
                      left.outcome === "FAIL_REJECT" ||
                      left.checks.some((check) => check.status !== "PASS") ||
                      Boolean(
                        timelineFailureForAssessment(evidence.data, left.assessment_id),
                      ) ||
                      revocationsForAssessment(evidence.data, left).length > 0 ||
                      missingBoundRevocationIds(evidence.data, left).length > 0;
                    const rightBlocked =
                      right.outcome === "FAIL_REJECT" ||
                      right.checks.some((check) => check.status !== "PASS") ||
                      Boolean(
                        timelineFailureForAssessment(evidence.data, right.assessment_id),
                      ) ||
                      revocationsForAssessment(evidence.data, right).length > 0 ||
                      missingBoundRevocationIds(evidence.data, right).length > 0;
                    return Number(rightBlocked) - Number(leftBlocked);
                  })
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
                      .filter(
                        (assessment) => revocationMatchesAssessment(revocation, assessment),
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
