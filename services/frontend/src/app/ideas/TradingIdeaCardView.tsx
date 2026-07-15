import type { components } from "@fable5/contracts";
import Link from "next/link";

import { missingBoundRevocationIds } from "../../components/GovernanceEvidence";
import {
  type EvidenceIndex,
  emptyEvidenceIndex,
  evidenceForCard,
  evaluationEvidenceForResearchRun,
  revocationMatchesAssessment,
  snapshotsForResearchRun,
} from "../../lib/evidence-index";

type TradingIdeaCard = components["schemas"]["TradingIdeaCard"];
type MappingWithRationale = components["schemas"]["MappingWithRationale"];

function humanize(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function EvidenceValues({ values, empty }: { values: string[]; empty: string }) {
  return values.length > 0 ? (
    <ul className="evidenceList">
      {values.map((value, index) => (
        <li key={`${index}-${value}`}>{value}</li>
      ))}
    </ul>
  ) : (
    <p className="formHint">{empty}</p>
  );
}

export function TradingIdeaCardView({
  card,
  evidenceIndex = emptyEvidenceIndex(),
  mappingOverride,
}: {
  card: TradingIdeaCard;
  evidenceIndex?: EvidenceIndex;
  mappingOverride?: MappingWithRationale;
}) {
  const related = evidenceForCard(evidenceIndex, card);
  const mappings = mappingOverride
    ? [
        mappingOverride,
        ...related.mappings.filter(
          ({ mapping }) => mapping.mapping_id !== mappingOverride.mapping.mapping_id,
        ),
      ]
    : related.mappings;
  const nonBuildMappings = mappings.filter(
    ({ mapping }) => mapping.verdict !== "BUILD_RESEARCH",
  );
  const hasBlockingEvidence =
    card.testability_status !== "testable" ||
    related.mappingConflicts.length > 0 ||
    related.snapshotConflicts.length > 0 ||
    related.evaluationReportConflicts.length > 0 ||
    related.evaluationOutcomeConflicts.length > 0 ||
    related.researchRunConflicts.length > 0 ||
    related.assessmentConflicts.length > 0 ||
    nonBuildMappings.length > 0 ||
    related.evaluationOutcomes.length > 0 ||
    related.evaluationReports.some(
      (report) =>
        report.promotion_state !== "PASS_RESEARCH" ||
        report.gates.some((gate) => gate.outcome !== "pass"),
    ) ||
    related.researchRunSummaries.some(
      (summary) => summary.promotion_state !== "PASS_RESEARCH",
    ) ||
    related.researchRuns.some((run) => {
      const evaluation = evaluationEvidenceForResearchRun(evidenceIndex, run);
      const snapshots = snapshotsForResearchRun(evidenceIndex, run);
      return (
        run.status === "blocked" ||
        run.phase5_evaluation.promotion_state !== "PASS_RESEARCH" ||
        (!run.phase5_evaluation.evaluation_report_id &&
          !run.phase5_evaluation.evaluation_outcome_id) ||
        evaluation.conflict ||
        snapshots.conflict
      );
    }) ||
    related.assessments.some(
      (assessment) =>
        assessment.outcome !== "APPROVED_PAPER" ||
        assessment.checks.some((check) => check.status !== "PASS") ||
        missingBoundRevocationIds(evidenceIndex, assessment).length > 0,
    ) ||
    Object.keys(related.assessmentTimelineFailures).length > 0 ||
    related.revocations.length > 0;

  return (
    <article
      className="strategyCard"
      data-blocking={hasBlockingEvidence ? "true" : undefined}
      data-synthetic-fixture={card.synthetic_fixture ? "true" : "false"}
      aria-labelledby={`idea-card-${card.card_id}`}
    >
      <header className="cardHeader">
        <div>
          <span className="cardKicker">Normalized TradingIdeaCard</span>
          <h2 id={`idea-card-${card.card_id}`}>
            {card.signal_family.value
              ? humanize(card.signal_family.value)
              : "Unresolved source claim"}
          </h2>
        </div>
        <span
          className="statusBadge"
          data-tone={card.testability_status === "testable" ? "success" : "critical"}
        >
          {card.testability_status}
        </span>
      </header>

      {card.testability_status !== "testable" ? (
        <div className="blockerBanner">
          <strong>TradingIdeaCard is structurally non-testable</strong>
          <p>
            The server-owned testability status is {card.testability_status}. No later positive
            metric can make this source claim eligible.
          </p>
        </div>
      ) : null}

      {related.snapshotConflicts.length > 0 ||
      related.evaluationReportConflicts.length > 0 ||
      related.evaluationOutcomeConflicts.length > 0 ||
      related.researchRunConflicts.length > 0 ||
      related.assessmentConflicts.length > 0 ? (
        <div className="blockerBanner" role="alert">
          <strong>Fail-closed descendant lineage conflict</strong>
          <p>
            Same-ID immutable evidence disagrees with an embedded ancestor reference. Conflicting
            snapshots ({related.snapshotConflicts.length}), reports (
            {related.evaluationReportConflicts.length}), blocked outcomes (
            {related.evaluationOutcomeConflicts.length}), research runs (
            {related.researchRunConflicts.length}), and assessments (
            {related.assessmentConflicts.length}) remain ineligible and are not presented as absent.
          </p>
        </div>
      ) : null}

      <section className="evidenceCard" aria-labelledby={`claim-${card.card_id}`}>
        <h3 id={`claim-${card.card_id}`}>Original post-derived claim</h3>
        {card.synthetic_fixture && card.raw_text ? (
          <blockquote>{card.raw_text}</blockquote>
        ) : card.quoted_claims.length > 0 ? (
          <div className="quotedClaimList">
            {card.quoted_claims.map((claim) => (
              <dl className="keyValueGrid" key={claim.claim_id}>
                <div>
                  <dt>Claim ID</dt>
                  <dd className="mono visualMask">{claim.claim_id}</dd>
                </div>
                <div>
                  <dt>Source byte span</dt>
                  <dd>
                    {claim.span.start_byte}:{claim.span.end_byte}
                  </dd>
                </div>
                <div>
                  <dt>Source text SHA-256</dt>
                  <dd className="artifactHash">{claim.span.text_sha256}</dd>
                </div>
                <div>
                  <dt>Payload handling</dt>
                  <dd>Exact non-synthetic text is referenced, not reproduced.</dd>
                </div>
              </dl>
            ))}
          </div>
        ) : (
          <p className="formHint">
            No exact quoted claim is present. The source remains referenced by immutable IDs.
          </p>
        )}
        <dl className="keyValueGrid">
          <div>
            <dt>Source ID</dt>
            <dd className="mono visualMask">{card.source_id}</dd>
          </div>
          <div>
            <dt>Source version ID</dt>
            <dd className="mono visualMask">{card.source_version_id}</dd>
          </div>
          <div>
            <dt>Extraction request ID</dt>
            <dd className="mono visualMask">{card.extraction_request_id}</dd>
          </div>
          <div>
            <dt>Source authority</dt>
            <dd>{card.source_authority}</dd>
          </div>
        </dl>
      </section>

      <section className="evidenceCard" aria-labelledby={`normalized-${card.card_id}`}>
        <h3 id={`normalized-${card.card_id}`}>Normalized interpretation</h3>
        <p>{card.paraphrased_claim ?? "No normalized paraphrase was extracted."}</p>
        <dl className="keyValueGrid">
          <div>
            <dt>Signal family</dt>
            <dd>{card.signal_family.value ?? card.signal_family.state}</dd>
          </div>
          <div>
            <dt>Forecast horizon</dt>
            <dd>{card.forecast_horizon.value ?? card.forecast_horizon.state}</dd>
          </div>
          <div>
            <dt>Action rule evidence</dt>
            <dd>{card.action_rule.state}</dd>
          </div>
          <div>
            <dt>Asset class</dt>
            <dd>{card.asset_class.value ?? card.asset_class.state}</dd>
          </div>
        </dl>
        <h4>Preserved ambiguity</h4>
        <EvidenceValues values={card.ambiguity_flags} empty="No ambiguity flags were recorded." />
      </section>

      <section className="evidenceCard" aria-labelledby={`requirements-${card.card_id}`}>
        <h3 id={`requirements-${card.card_id}`}>Required data and testability</h3>
        <EvidenceValues
          values={card.required_data.values}
          empty={`Required data state: ${card.required_data.state}`}
        />
        <dl className="keyValueGrid">
          <div>
            <dt>Testability status</dt>
            <dd>{card.testability_status}</dd>
          </div>
          <div>
            <dt>Testability score</dt>
            <dd>{card.testability_score}</dd>
          </div>
          <div>
            <dt>Method</dt>
            <dd>{card.testability_score_method}</dd>
          </div>
          <div>
            <dt>Corroboration status</dt>
            <dd>{card.corroboration_status}</dd>
          </div>
        </dl>
        <EvidenceValues
          values={card.testability_reason_codes}
          empty="No testability blockers were recorded."
        />
      </section>

      <section className="evidenceCard" aria-labelledby={`mapping-${card.card_id}`}>
        <h3 id={`mapping-${card.card_id}`}>Build, defer, or reject rationale</h3>
        {related.mappingConflicts.length > 0 ? (
          <div className="blockerBanner">
            <strong>Exact mapping lineage conflict</strong>
            <p>
              {related.mappingConflicts.length} same-ID mapping artifact(s) conflict with the
              TradingIdeaCard&apos;s embedded Phase 2 lineage. No mapping was substituted.
            </p>
          </div>
        ) : null}
        {mappings.length === 0 ? (
          <p className="formHint">
            No immutable mapping exists. No build, defer, or reject verdict is inferred.
          </p>
        ) : (
          mappings.map(({ mapping, rationale }) => {
            const mappingBlocked = mapping.verdict !== "BUILD_RESEARCH";
            return (
              <article
                className="evidenceCard"
                data-blocking={mappingBlocked ? "true" : undefined}
                key={mapping.mapping_id}
              >
                <header>
                  <span
                    className="statusBadge"
                    data-tone={mappingBlocked ? "critical" : "pass"}
                  >
                    {mapping.verdict}
                  </span>
                  <span>{mapping.canonical_family ?? "UNRESOLVED"}</span>
                </header>
                {mappingBlocked ? (
                  <div className="blockerBanner">
                    <strong>Phase 3 verdict is ineligible</strong>
                    <p>
                      {mapping.verdict} is a persisted non-build outcome. It cannot be softened by
                      testability or later positive metrics.
                    </p>
                  </div>
                ) : (
                  <div className="boundaryNotice" data-tone="critical">
                    <strong>Research specification only</strong>
                    <p>BUILD_RESEARCH is not approval, a signal, or executable authority.</p>
                  </div>
                )}
                <p>{rationale.markdown}</p>
                <h4>Ordered reason codes</h4>
                <EvidenceValues values={mapping.reason_codes} empty="No mapping reason codes." />
                <Link className="lineageLink" href={`/lineage?mapping_id=${mapping.mapping_id}`}>
                  Trace mapping artifact
                </Link>
              </article>
            );
          })
        )}
      </section>

      <section className="evidenceCard" aria-labelledby={`evaluation-${card.card_id}`}>
        <h3 id={`evaluation-${card.card_id}`}>Mock evaluation and cost sensitivity</h3>
        {related.evaluationOutcomeConflicts.length > 0 ? (
          <div className="blockerBanner">
            <strong>Exact blocked-evaluation lineage conflict</strong>
            <p>
              {related.evaluationOutcomeConflicts.length} same-mapping outcome artifact(s)
              conflict with the mapping input, version, or resolved snapshots. No outcome was
              substituted.
            </p>
            <ul className="reasonList" aria-label="Conflicting blocked evaluation artifacts">
              {related.evaluationOutcomeConflicts.map((outcome) => (
                <li key={outcome.outcome_id}>
                  <Link
                    aria-label={`Trace conflicting blocked evaluation artifact ${outcome.outcome_id}`}
                    className="lineageLink"
                    href={`/lineage?evaluation_outcome_id=${outcome.outcome_id}`}
                  >
                    Trace conflicting blocked evaluation artifact
                    <span className="mono visualMask"> {outcome.outcome_id}</span>
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
        {related.evaluationReports.length === 0 && related.evaluationOutcomes.length === 0 ? (
          <p className="formHint">
            No linked mock evaluation exists. This absence does not imply a passing result.
          </p>
        ) : null}
        {related.evaluationOutcomes.map((outcome) => (
          <article className="evidenceCard" data-blocking="true" key={outcome.outcome_id} role="status">
            <strong>{outcome.promotion_state}</strong>
            <p>{outcome.sanitized_message}</p>
            <EvidenceValues values={outcome.reason_codes} empty="No blocker reason codes recorded." />
            <Link
              className="lineageLink"
              href={`/lineage?evaluation_outcome_id=${outcome.outcome_id}`}
            >
              Trace blocked evaluation artifact
            </Link>
          </article>
        ))}
        {related.evaluationReports.map((report) => {
          const costStress = report.gates.find((gate) => gate.gate_code === "COST_STRESS");
          const blockingGates = report.gates.filter((gate) => gate.outcome !== "pass");
          const reportBlocked =
            report.promotion_state !== "PASS_RESEARCH" || blockingGates.length > 0;
          return (
            <article
              className="evidenceCard"
              data-blocking={reportBlocked ? "true" : undefined}
              key={report.artifact_id}
            >
              <header>
                <strong>{report.promotion_state}</strong>
                <span>Synthetic fixture {report.fixture_id}</span>
              </header>
              {reportBlocked ? (
                <div className="blockerBanner">
                  <strong>Blocking evaluation evidence</strong>
                  <p>
                    {blockingGates.length} non-passing persisted gate(s); promotion state{" "}
                    {report.promotion_state}.
                  </p>
                </div>
              ) : (
                <div className="boundaryNotice" data-tone="critical">
                  <strong>Research prerequisite only</strong>
                  <p>PASS_RESEARCH is not simulated-paper approval or executable authority.</p>
                </div>
              )}
              <p>{report.disclaimer}</p>
              <dl className="keyValueGrid" aria-label="Server-owned mock backtest summary">
                <div>
                  <dt>Raw trial count</dt>
                  <dd>{report.raw_trial_count}</dd>
                </div>
                <div>
                  <dt>Effective trial count</dt>
                  <dd>{report.effective_trial_count}</dd>
                </div>
                <div>
                  <dt>Walk-forward fold count</dt>
                  <dd>{report.folds.length}</dd>
                </div>
                <div>
                  <dt>Server metric count</dt>
                  <dd>{report.metrics.length}</dd>
                </div>
              </dl>
              <details>
                <summary>Inspect server-owned mock metrics</summary>
                <ul className="evidenceList">
                  {report.metrics.map((metric) => (
                    <li key={metric.metric_id}>
                      <strong>{metric.metric_id}</strong>
                      <span>
                        {metric.value} {metric.units}
                      </span>
                    </li>
                  ))}
                </ul>
              </details>
              {costStress ? (
                <section aria-label="COST_STRESS gate evidence">
                  <h4>
                    COST_STRESS: {costStress.outcome}
                  </h4>
                  <EvidenceValues
                    values={costStress.reason_codes}
                    empty="No COST_STRESS reason codes recorded."
                  />
                  <details>
                    <summary>Exact server-owned cost evidence</summary>
                    <pre>{JSON.stringify({
                      inputs: costStress.inputs,
                      results: costStress.results,
                      thresholds: costStress.thresholds,
                    }, null, 2)}</pre>
                  </details>
                </section>
              ) : (
                <p className="formHint">No COST_STRESS gate is present in this artifact.</p>
              )}
              <Link
                className="lineageLink"
                href={`/lineage?evaluation_report_id=${report.artifact_id}`}
              >
                Trace evaluation artifact
              </Link>
            </article>
          );
        })}
      </section>

      <section className="evidenceCard" aria-labelledby={`research-${card.card_id}`}>
        <h3 id={`research-${card.card_id}`}>Deterministic research artifacts</h3>
        {related.researchRuns.length === 0 ? (
          <p className="formHint">
            No linked research artifact exists. Configuration identity is not treated as a verdict.
          </p>
        ) : (
          related.researchRuns.map((run) => {
            const summary = related.researchRunSummaries.find(({ run_id }) => run_id === run.run_id);
            const evaluation = evaluationEvidenceForResearchRun(evidenceIndex, run);
            const snapshots = snapshotsForResearchRun(evidenceIndex, run);
            const runBlocked =
              summary?.promotion_state !== "PASS_RESEARCH" ||
              run.phase5_evaluation.promotion_state !== "PASS_RESEARCH" ||
              (!run.phase5_evaluation.evaluation_report_id &&
                !run.phase5_evaluation.evaluation_outcome_id) ||
              evaluation.conflict ||
              snapshots.conflict;
            return (
              <article
                className="evidenceCard"
                data-blocking={runBlocked ? "true" : undefined}
                key={run.run_id}
              >
                <header>
                  <strong>{summary?.promotion_state ?? run.status}</strong>
                  <span>{run.configuration_id}</span>
                </header>
                {evaluation.conflict ? (
                  <div className="blockerBanner">
                    <strong>Exact evaluation conflict</strong>
                    <p>No same-mapping evaluation artifact was substituted.</p>
                  </div>
                ) : null}
                {snapshots.conflict ? (
                  <div className="blockerBanner">
                    <strong>Exact snapshot conflict</strong>
                    <p>
                      An embedded snapshot identifier, hash, or mapping conflicts with the loaded
                      immutable artifact. No mapping-level snapshot was substituted.
                    </p>
                  </div>
                ) : null}
                <dl className="keyValueGrid">
                  <div>
                    <dt>Run ID</dt>
                    <dd className="mono visualMask">{run.run_id}</dd>
                  </div>
                  <div>
                    <dt>Code version Git SHA</dt>
                    <dd className="mono visualMask">{run.code_version_git_sha}</dd>
                  </div>
                  <div>
                    <dt>Configuration SHA-256</dt>
                    <dd className="artifactHash visualMask">{run.configuration_sha256}</dd>
                  </div>
                  <div>
                    <dt>Attempt count</dt>
                    <dd>{run.attempts.length}</dd>
                  </div>
                </dl>
                <EvidenceValues values={run.reason_codes} empty="No research reason codes recorded." />
                <Link className="lineageLink" href={`/lineage?run_id=${run.run_id}`}>
                  Trace research artifact
                </Link>
              </article>
            );
          })
        )}
      </section>

      <section className="evidenceCard" aria-labelledby={`risk-${card.card_id}`}>
        <h3 id={`risk-${card.card_id}`}>Risk / Compliance status</h3>
        {related.assessments.length === 0 ? (
          <p className="formHint">
            No linked Phase 7 assessment exists. Missing governance evidence is not approval.
          </p>
        ) : (
          related.assessments.map((assessment) => {
            const linkedRevocations = related.revocations.filter((revocation) =>
              revocationMatchesAssessment(revocation, assessment),
            );
            const assessmentBoundCount = linkedRevocations.filter((revocation) =>
              assessment.revocation_ids.includes(revocation.revocation_id),
            ).length;
            const additionalLinkedCount = linkedRevocations.length - assessmentBoundCount;
            const nonPassingChecks = assessment.checks.filter(
              (check) => check.status !== "PASS",
            );
            const missingBoundRevocations = missingBoundRevocationIds(
              evidenceIndex,
              assessment,
            );
            const timelineFailure =
              related.assessmentTimelineFailures[assessment.assessment_id];
            const assessmentBlocked =
              assessment.outcome !== "APPROVED_PAPER" ||
              nonPassingChecks.length > 0 ||
              linkedRevocations.length > 0 ||
              missingBoundRevocations.length > 0 ||
              Boolean(timelineFailure);
            return (
              <article
                className="evidenceCard"
                data-blocking={assessmentBlocked ? "true" : undefined}
                key={assessment.assessment_id}
              >
              <header>
                <strong>{assessment.outcome}</strong>
                <time dateTime={assessment.created_at_utc}>{assessment.created_at_utc}</time>
              </header>
              {timelineFailure ? (
                <div className="blockerBanner" role="alert">
                  <strong>Historical timeline evidence was not resolved</strong>
                  <p>
                    {timelineFailure.message} No date or governance state was inferred.
                  </p>
                </div>
              ) : null}
              {missingBoundRevocations.length > 0 ? (
                <div className="blockerBanner">
                  <strong>Unresolved bound revocation evidence</strong>
                  <p>
                    {missingBoundRevocations.length} assessment-bound revocation identifier(s)
                    did not resolve to an artifact with the exact authorization reference. No
                    substitute was inferred.
                  </p>
                </div>
              ) : null}
              {nonPassingChecks.length > 0 ? (
                <div className="blockerBanner">
                  <strong>Non-passing ordered checks</strong>
                  <p>{nonPassingChecks.length} persisted Phase 7 check(s) did not pass.</p>
                </div>
              ) : null}
              {linkedRevocations.length > 0 ? (
                <div className="blockerBanner">
                  <strong>Linked revocation evidence</strong>
                  <p>
                    {assessmentBoundCount} ID(s) are bound in the assessment artifact;{" "}
                    {additionalLinkedCount} additional append-only artifact(s) share its exact
                    authorization reference.
                  </p>
                </div>
              ) : assessment.outcome !== "APPROVED_PAPER" ? (
                <div className="blockerBanner">
                  <strong>Assessment is ineligible</strong>
                  <p>The server-owned assessment outcome is not APPROVED_PAPER.</p>
                </div>
              ) : null}
              <EvidenceValues
                values={assessment.reason_codes}
                empty="No assessment reason codes recorded."
              />
              <details>
                <summary>Complete ordered Phase 7 checks</summary>
                <ol className="evidenceList">
                  {assessment.checks.map((check) => (
                    <li key={`${check.ordinal}-${check.code}`}>
                      {check.ordinal}. {check.code}: {check.status} - {check.reason_code}
                    </li>
                  ))}
                </ol>
              </details>
              <Link
                className="lineageLink"
                href={`/lineage?assessment_id=${assessment.assessment_id}`}
              >
                Trace assessment artifact
              </Link>
              </article>
            );
          })
        )}
      </section>

      <section className="evidenceCard" aria-labelledby={`paper-${card.card_id}`}>
        <h3 id={`paper-${card.card_id}`}>SIMULATED paper status</h3>
        <div className="boundaryNotice" data-tone="simulated">
          <strong>SIMULATED</strong>
          <p>Historical synthetic governance status only. No executable paper action exists.</p>
        </div>
        {related.assessments.length === 0 ? (
          <p className="formHint">No historical simulated-paper assessment is linked.</p>
        ) : (
          related.assessments.map((assessment) => {
            const linkedRevocations = related.revocations.filter((revocation) =>
              revocationMatchesAssessment(revocation, assessment),
            );
            const nonPassingChecks = assessment.checks.filter(
              (check) => check.status !== "PASS",
            );
            const missingBoundRevocations = missingBoundRevocationIds(
              evidenceIndex,
              assessment,
            );
            const timelineFailure =
              related.assessmentTimelineFailures[assessment.assessment_id];
            const paperBlocked =
              assessment.outcome !== "APPROVED_PAPER" ||
              nonPassingChecks.length > 0 ||
              linkedRevocations.length > 0 ||
              missingBoundRevocations.length > 0 ||
              Boolean(timelineFailure);
            return (
            <article
              className="evidenceCard"
              data-blocking={paperBlocked ? "true" : undefined}
              key={`paper-${assessment.assessment_id}`}
            >
              <strong>{assessment.outcome}</strong>
              <span className="mono visualMask"> - assessment {assessment.assessment_id}</span>
              {timelineFailure ? (
                <div className="blockerBanner" role="alert">
                  <strong>Historical timeline evidence was not resolved</strong>
                  <p>
                    {timelineFailure.message} No date, currentness, expiry, revocation, or
                    readiness state was inferred.
                  </p>
                </div>
              ) : null}
              {missingBoundRevocations.length > 0 ? (
                <div className="blockerBanner">
                  <strong>Unresolved bound revocation evidence</strong>
                  <p>
                    {missingBoundRevocations.length} assessment-bound revocation identifier(s)
                    did not resolve to an artifact with the exact authorization reference. No
                    substitute was inferred.
                  </p>
                </div>
              ) : null}
              {nonPassingChecks.length > 0 ? (
                <div className="blockerBanner">
                  <strong>Non-passing ordered checks</strong>
                  <p>{nonPassingChecks.length} persisted Phase 7 check(s) did not pass.</p>
                </div>
              ) : null}
              {linkedRevocations.length > 0 ? (
                <div className="blockerBanner">
                  <strong>Linked revocation evidence</strong>
                  <p>Immutable revocation evidence makes this historical status ineligible.</p>
                </div>
              ) : assessment.outcome !== "APPROVED_PAPER" ? (
                <div className="blockerBanner">
                  <strong>Simulated-paper status is ineligible</strong>
                  <p>The server-owned assessment outcome is not APPROVED_PAPER.</p>
                </div>
              ) : null}
              {related.assessmentTimelines[assessment.assessment_id] ? (
                <dl className="keyValueGrid">
                  <div>
                    <dt>Authorization review at UTC</dt>
                    <dd>
                      {
                        related.assessmentTimelines[assessment.assessment_id].authorization
                          .review_at_utc
                      }
                    </dd>
                  </div>
                  <div>
                    <dt>Authorization expires at UTC</dt>
                    <dd>
                      {
                        related.assessmentTimelines[assessment.assessment_id].authorization
                          .expires_at_utc
                      }
                    </dd>
                  </div>
                  <div>
                    <dt>Policy expires at UTC</dt>
                    <dd>
                      {related.assessmentTimelines[assessment.assessment_id].policy.expires_at_utc}
                    </dd>
                  </div>
                  <div>
                    <dt>Scope expires at UTC</dt>
                    <dd>
                      {related.assessmentTimelines[assessment.assessment_id].scope.expires_at_utc}
                    </dd>
                  </div>
                </dl>
              ) : timelineFailure ? null : (
                <p className="formHint">No linked expiry/review timeline is available.</p>
              )}
            </article>
            );
          })
        )}
        {related.revocations.length > 0 ? (
          <div className="blockerBanner">
            <strong>Immutable revocation history</strong>
            {related.revocations.map((revocation) => (
              <p key={revocation.revocation_id}>
                Revocation <span className="mono visualMask">{revocation.revocation_id}</span>{" "}
                effective{" "}
                <time dateTime={revocation.effective_at_utc}>{revocation.effective_at_utc}</time>
                {" "}
                <Link href={`/lineage?revocation_id=${revocation.revocation_id}`}>
                  Trace revocation artifact
                </Link>
              </p>
            ))}
          </div>
        ) : (
          <p className="formHint">No linked revocation artifact is present.</p>
        )}
      </section>

      <footer className="cardFooter">
        <Link
          className="lineageLink"
          href={`/lineage?card_id=${encodeURIComponent(card.card_id)}`}
        >
          Open complete immutable lineage
        </Link>
      </footer>
    </article>
  );
}
