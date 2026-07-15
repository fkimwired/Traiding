"use client";

import type { components } from "@fable5/contracts";
import { useEffect, useState } from "react";

import { fable5Api } from "../../lib/api";

type EvaluationReport = components["schemas"]["EvaluationReport"];
type EvaluationReportSummary = components["schemas"]["EvaluationReportSummary"];
type BlockedEvaluationOutcome = components["schemas"]["BlockedEvaluationOutcome"];
type GateCode = components["schemas"]["GateCode"];
type ResearchReturnStatus = components["schemas"]["ResearchReturnStatus"];
type ResolvedSourceObservationRef = components["schemas"]["ResolvedSourceObservationRef"];
type Scalar = string | number | boolean;

type ReportState =
  | { status: "loading" }
  | { status: "empty" }
  | { status: "error" }
  | {
      status: "loaded";
      report: EvaluationReport;
      summaries: EvaluationReportSummary[];
    };

type OutcomeState =
  | { status: "loading" }
  | { status: "empty" }
  | { status: "error" }
  | {
      status: "loaded";
      outcome: BlockedEvaluationOutcome;
      outcomes: BlockedEvaluationOutcome[];
    };

const gateLabels: Record<GateCode, string> = {
  DATA_PIT: "Point-in-time data",
  CV_CHRONOLOGY: "Walk-forward chronology",
  PREPROCESSING: "Train-only preprocessing",
  TRIAL_REGISTRY: "Complete trial registry",
  DSR: "Deflated Sharpe Ratio",
  PBO: "Backtest overfitting probability",
  COST_STRESS: "Cost and liquidity stress",
  LEAKAGE: "Leakage blockers",
  SAMPLE_ADEQUACY: "Sample adequacy",
  REGIME: "Regime evidence",
  RISK_LIMITS: "Risk limits",
  REPRODUCIBILITY: "Reproducibility",
};

const trialStatuses = ["completed", "failed", "abandoned", "no_return"] as const;
const returnStatuses = ["observed", "no_trade", "delisted", "missing"] as const satisfies readonly ResearchReturnStatus[];

function humanize(value: string) {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function scalarText(value: Scalar) {
  return typeof value === "boolean" ? (value ? "true" : "false") : String(value);
}

function countReturnStatuses(values: ResearchReturnStatus[]) {
  return Object.fromEntries(
    returnStatuses.map((status) => [
      status,
      values.filter((value) => value === status).length,
    ]),
  ) as Record<ResearchReturnStatus, number>;
}

function EvidenceList({ values, emptyLabel }: { values: string[]; emptyLabel: string }) {
  return values.length > 0 ? (
    <ul>
      {values.map((value) => (
        <li key={value}>{value}</li>
      ))}
    </ul>
  ) : (
    <p className="evaluationEmptyValue">{emptyLabel}</p>
  );
}

function KeyValueEvidence({
  heading,
  values,
}: {
  heading: string;
  values: Readonly<Record<string, Scalar>>;
}) {
  const entries = Object.entries(values);

  return (
    <section className="evaluationKeyValue">
      <h4>{heading}</h4>
      {entries.length > 0 ? (
        <dl>
          {entries.map(([key, value]) => (
            <div key={key}>
              <dt>{humanize(key)}</dt>
              <dd>{scalarText(value)}</dd>
            </div>
          ))}
        </dl>
      ) : (
        <p className="evaluationEmptyValue">None recorded</p>
      )}
    </section>
  );
}

function DetailGrid({
  values,
  className = "evaluationDetailGrid",
}: {
  values: ReadonlyArray<readonly [string, Scalar | null | undefined]>;
  className?: string;
}) {
  return (
    <dl className={className}>
      {values.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{value === null || value === undefined || value === "" ? "None recorded" : scalarText(value)}</dd>
        </div>
      ))}
    </dl>
  );
}

function EvidenceGroup({
  heading,
  values,
  emptyLabel = "None recorded",
}: {
  heading: string;
  values: string[];
  emptyLabel?: string;
}) {
  return (
    <section className="evaluationEvidenceGroup">
      <h4>{heading}</h4>
      <EvidenceList values={values} emptyLabel={emptyLabel} />
    </section>
  );
}

function SourceObservationReferences({
  references,
}: {
  references: ResolvedSourceObservationRef[];
}) {
  return (
    <div className="evaluationEvidenceList">
      {references.map((reference) => (
        <article
          className="evaluationEvidenceCard"
          aria-label={`Source observation reference ${reference.normalized_observation_id}`}
          key={`${reference.snapshot_id}-${reference.normalized_observation_id}`}
        >
          <header>
            <div>
              <span>{reference.capability}</span>
              <h4>{reference.normalized_observation_id}</h4>
            </div>
          </header>
          <DetailGrid
            values={[
              ["Snapshot ID", reference.snapshot_id],
              ["Snapshot SHA-256", reference.snapshot_sha256],
              ["Raw observation ID", reference.raw_observation_id],
              ["Observation revision ID", reference.observation_revision_id],
              ["Normalized observation ID", reference.normalized_observation_id],
              ["Raw payload SHA-256", reference.raw_payload_sha256],
              ["Normalized content SHA-256", reference.normalized_content_sha256],
            ]}
          />
        </article>
      ))}
    </div>
  );
}

function BlockedOutcomePanel({ state }: { state: OutcomeState }) {
  return (
    <section className="evaluationPanel" aria-labelledby="blocked-outcomes-heading">
      <div className="evaluationSectionHeading">
        <div>
          <p className="eyebrow">Fail-closed request record</p>
          <h3 id="blocked-outcomes-heading">Persisted blocked evaluation outcomes</h3>
        </div>
        {state.status === "loaded" ? (
          <span>{state.outcomes.length} immutable outcome(s)</span>
        ) : null}
      </div>

      {state.status === "loading" ? (
        <p className="evaluationEmptyValue">Loading persisted blocked outcomes...</p>
      ) : null}
      {state.status === "empty" ? (
        <p className="evaluationEmptyValue">
          No persisted blocked evaluation outcomes are available yet.
        </p>
      ) : null}
      {state.status === "error" ? (
        <p className="evaluationLoadState evaluationLoadError" role="alert">
          Persisted blocked evaluation outcomes could not be loaded.
        </p>
      ) : null}

      {state.status === "loaded" ? (
        <article
          className="evaluationEvidenceCard"
          aria-label={`Blocked evaluation outcome ${state.outcome.outcome_id}`}
        >
          <header>
            <div>
              <span>{state.outcome.failure_stage}</span>
              <h4>{state.outcome.promotion_state}</h4>
            </div>
            <code>{state.outcome.status}</code>
          </header>
          <p>{state.outcome.sanitized_message}</p>
          <DetailGrid
            values={[
              ["Outcome ID", state.outcome.outcome_id],
              ["Outcome SHA-256", state.outcome.outcome_sha256],
              ["Idempotency SHA-256", state.outcome.idempotency_sha256],
              ["Submission SHA-256", state.outcome.submission_sha256],
              ["Artifact type", state.outcome.artifact_type],
              ["Schema version", state.outcome.schema_version],
              ["Policy ID", state.outcome.policy_id],
              ["Policy version", state.outcome.policy_version],
              ["Resolved policy SHA-256", state.outcome.resolved_policy_sha256],
              ["Mapping ID", state.outcome.mapping_id],
              ["Fixture ID", state.outcome.fixture_id],
              ["Resolved fixture SHA-256", state.outcome.resolved_fixture_sha256],
              ["Resolved fixture random seed", state.outcome.resolved_fixture_random_seed],
              ["Resolved raw trial count", state.outcome.resolved_raw_trial_count],
              ["Code version Git SHA", state.outcome.code_version_git_sha],
              ["Synthetic evidence", state.outcome.synthetic],
              ["No real performance claimed", state.outcome.no_real_performance_claimed],
              ["Created at UTC", state.outcome.created_at_utc],
            ]}
          />
          <div className="evaluationEvidenceColumns">
            <EvidenceGroup heading="Requested snapshot IDs" values={state.outcome.snapshot_ids} />
            <EvidenceGroup heading="Reason codes" values={state.outcome.reason_codes} />
          </div>
          <section className="evaluationEvidenceGroup">
            <h4>Resolved snapshot evidence</h4>
            {(state.outcome.resolved_snapshots ?? []).length > 0 ? (
              <div className="evaluationEvidenceList">
                {(state.outcome.resolved_snapshots ?? []).map((snapshot) => (
                  <article className="evaluationEvidenceCard" key={snapshot.snapshot_id}>
                    <DetailGrid
                      values={[
                        ["Snapshot ID", snapshot.snapshot_id],
                        ["Snapshot SHA-256", snapshot.snapshot_sha256],
                        ["Mapping ID", snapshot.mapping_id],
                        ["Mapping version", snapshot.mapping_version],
                        ["Mapping input SHA-256", snapshot.mapping_input_sha256],
                      ]}
                    />
                  </article>
                ))}
              </div>
            ) : (
              <p className="evaluationEmptyValue">None resolved before the request stopped</p>
            )}
          </section>
        </article>
      ) : null}
    </section>
  );
}

export function EvaluationReports() {
  const [reportState, setReportState] = useState<ReportState>({ status: "loading" });
  const [outcomeState, setOutcomeState] = useState<OutcomeState>({ status: "loading" });

  useEffect(() => {
    const controller = new AbortController();

    async function loadReports() {
      const summariesResult = await fable5Api.listEvaluationReports(controller.signal);
      if (!summariesResult.ok) {
        if (summariesResult.error.kind !== "aborted") {
          setReportState({ status: "error" });
        }
        return;
      }

      const summaries = summariesResult.data;
      if (summaries.length === 0) {
        setReportState({ status: "empty" });
        return;
      }

      const reportResult = await fable5Api.getEvaluationReport(
        summaries[0].artifact_id,
        controller.signal,
      );
      if (!reportResult.ok) {
        if (reportResult.error.kind !== "aborted") {
          setReportState({ status: "error" });
        }
        return;
      }

      setReportState({ status: "loaded", report: reportResult.data, summaries });
    }

    async function loadOutcomes() {
      const outcomesResult = await fable5Api.listEvaluationOutcomes(controller.signal);
      if (!outcomesResult.ok) {
        if (outcomesResult.error.kind !== "aborted") {
          setOutcomeState({ status: "error" });
        }
        return;
      }

      const outcomes = outcomesResult.data;
      if (outcomes.length === 0) {
        setOutcomeState({ status: "empty" });
        return;
      }

      const outcomeResult = await fable5Api.getEvaluationOutcome(
        outcomes[0].outcome_id,
        controller.signal,
      );
      if (!outcomeResult.ok) {
        if (outcomeResult.error.kind !== "aborted") {
          setOutcomeState({ status: "error" });
        }
        return;
      }

      setOutcomeState({ status: "loaded", outcome: outcomeResult.data, outcomes });
    }

    void loadReports();
    void loadOutcomes();
    return () => controller.abort();
  }, []);

  return (
    <section className="evaluationSection" aria-labelledby="evaluation-heading">
      <div className="evaluationBoundary">
        <p className="eyebrow">Phase 5 read-only evidence</p>
        <h2 id="evaluation-heading">Immutable evaluation report</h2>
        <p>
          This view presents deterministic synthetic research evidence. No real performance is
          claimed, and the report cannot change research state.
        </p>
        <div className="evaluationBoundaryFlags" aria-label="Evaluation boundaries">
          <strong>Deterministic synthetic evidence</strong>
          <strong>No real performance claimed</strong>
          <strong>PASS_RESEARCH is not paper approval</strong>
        </div>
      </div>

      {reportState.status === "loading" ? (
        <p className="evaluationLoadState" role="status">
          Loading immutable evaluation evidence...
        </p>
      ) : null}

      {reportState.status === "error" ? (
        <p className="evaluationLoadState evaluationLoadError" role="alert">
          Evaluation evidence could not be loaded. No research state was changed.
        </p>
      ) : null}

      {reportState.status === "empty" ? (
        <p className="evaluationLoadState">No immutable evaluation reports are available yet.</p>
      ) : null}

      {reportState.status === "loaded" ? (
        <EvaluationReportDetail report={reportState.report} summaries={reportState.summaries} />
      ) : null}

      <BlockedOutcomePanel state={outcomeState} />
    </section>
  );
}

function EvaluationReportDetail({
  report,
  summaries,
}: {
  report: EvaluationReport;
  summaries: EvaluationReportSummary[];
}) {
  const trialCounts = Object.fromEntries(
    trialStatuses.map((status) => [
      status,
      report.trials.filter((trial) => trial.status === status).length,
    ]),
  );
  const trialReturnCounts = countReturnStatuses(
    report.trials.flatMap((trial) => trial.return_statuses),
  );
  const oosReturnCounts = countReturnStatuses(
    report.oos_ledger.map((entry) => entry.return_status ?? "observed"),
  );
  const costReturnCounts = countReturnStatuses(
    report.cost_ledger.map((entry) => entry.return_status),
  );
  const auditFields = [
    ["Artifact ID", report.artifact_id],
    ["Artifact type", report.artifact_type],
    ["Artifact schema", report.artifact_schema_version],
    ["Artifact SHA-256", report.artifact_sha256],
    ["Config hash", report.config_hash],
    ["Request fingerprint", report.request_fingerprint_sha256],
    ["Request fingerprint version", report.request_fingerprint_version],
    ["Policy ID", report.evaluation_policy_id],
    ["Policy version", String(report.evaluation_policy_version)],
    ["Policy SHA-256", report.evaluation_policy_sha256],
    ["Mapping ID", report.mapping_id],
    ["Mapping version", String(report.mapping_version)],
    ["Mapping input SHA-256", report.mapping_input_sha256],
    ["Snapshot bundle SHA-256", report.snapshot_bundle_sha256],
    ["Code version Git SHA", report.code_version_git_sha],
    ["Random seed", String(report.random_seed)],
    ["Created at UTC", report.created_at_utc],
    ["Decision time UTC", report.decision_time_utc],
    ["Fixture ID", report.fixture_id],
    ["Fixture version", report.fixture_version],
    ["Fixture SHA-256", report.fixture_sha256],
  ] as const;

  return (
    <div className="evaluationReport">
      <header className="evaluationStatePanel">
        <div>
          <span>Latest of {summaries.length} immutable report(s)</span>
          <h3>Evaluation state</h3>
        </div>
        <code className="evaluationPromotionState">{report.promotion_state}</code>
        <p>{report.disclaimer}</p>
      </header>

      <section className="evaluationPanel" aria-labelledby="trial-counts-heading">
        <div className="evaluationSectionHeading">
          <div>
            <p className="eyebrow">Complete registry</p>
            <h3 id="trial-counts-heading">Trial counts</h3>
          </div>
          <span>{report.trials.length} persisted trial records</span>
        </div>
        <dl className="evaluationCountGrid">
          <div>
            <dt>Raw trial count</dt>
            <dd>{report.raw_trial_count}</dd>
          </div>
          <div>
            <dt>Effective trial count</dt>
            <dd>{report.effective_trial_count}</dd>
          </div>
          {trialStatuses.map((status) => (
            <div key={status}>
              <dt>{humanize(status)}</dt>
              <dd>{trialCounts[status]}</dd>
            </div>
          ))}
        </dl>
        <p className="evaluationMethod">
          Effective-trial method: <code>{report.effective_trial_method}</code>
        </p>
      </section>

      <section className="evaluationPanel" aria-labelledby="return-status-counts-heading">
        <div className="evaluationSectionHeading">
          <div>
            <p className="eyebrow">Explicit return accounting</p>
            <h3 id="return-status-counts-heading">Return status counts</h3>
          </div>
          <span>Trial, OOS, and cost rows</span>
        </div>
        <dl className="evaluationCountGrid">
          {returnStatuses.flatMap((status) => [
            <div key={`trial-${status}`}>
              <dt>Trial {humanize(status)}</dt>
              <dd>{trialReturnCounts[status]}</dd>
            </div>,
            <div key={`oos-${status}`}>
              <dt>OOS {humanize(status)}</dt>
              <dd>{oosReturnCounts[status]}</dd>
            </div>,
            <div key={`cost-${status}`}>
              <dt>Cost {humanize(status)}</dt>
              <dd>{costReturnCounts[status]}</dd>
            </div>,
          ])}
        </dl>
      </section>

      <section className="evaluationPanel" aria-labelledby="specifications-heading">
        <div className="evaluationSectionHeading">
          <div>
            <p className="eyebrow">Frozen research contract</p>
            <h3 id="specifications-heading">Feature and label specifications</h3>
          </div>
          <span>Server-authored immutable definitions</span>
        </div>
        <div className="evaluationEvidenceCardGrid">
          <article className="evaluationEvidenceCard" aria-label="Feature specification">
            <header>
              <div>
                <span>Feature specification</span>
                <h4>{report.feature_specification.formula_id}</h4>
              </div>
              <code>{report.feature_specification.version}</code>
            </header>
            <DetailGrid
              values={[
                ["Specification ID", report.feature_specification.feature_specification_id],
                ["Schema version", report.feature_specification.schema_version],
                ["Content SHA-256", report.feature_specification.content_sha256],
                ["Lookback rule", report.feature_specification.lookback_rule],
                ["Availability rule", report.feature_specification.availability_rule],
                ["Imputation policy", report.feature_specification.imputation_policy],
                ["Encoding policy", report.feature_specification.encoding_policy],
                ["Feature selection policy", report.feature_specification.feature_selection_policy],
                ["Hyperparameter policy", report.feature_specification.hyperparameter_policy],
              ]}
            />
            <div className="evaluationEvidenceColumns">
              <EvidenceGroup
                heading="Source fields"
                values={report.feature_specification.source_fields}
              />
              <EvidenceGroup
                heading="Preprocessing rules"
                values={report.feature_specification.preprocessing_rules}
              />
            </div>
          </article>
          <article className="evaluationEvidenceCard" aria-label="Label specification">
            <header>
              <div>
                <span>Label specification</span>
                <h4>{report.label_specification.formula_id}</h4>
              </div>
              <code>{report.label_specification.version}</code>
            </header>
            <DetailGrid
              values={[
                ["Specification ID", report.label_specification.label_specification_id],
                ["Schema version", report.label_specification.schema_version],
                ["Content SHA-256", report.label_specification.content_sha256],
                ["Forecast horizon", report.label_specification.forecast_horizon],
                ["Information interval rule", report.label_specification.information_interval_rule],
                ["Missing return policy", report.label_specification.missing_return_policy],
                ["No-trade return policy", report.label_specification.no_trade_return_policy],
                ["Delisting return policy", report.label_specification.delisting_return_policy],
              ]}
            />
          </article>
        </div>
      </section>

      <section className="evaluationPanel" aria-labelledby="trial-details-heading">
        <div className="evaluationSectionHeading">
          <div>
            <p className="eyebrow">Append-only registry</p>
            <h3 id="trial-details-heading">Trial details</h3>
          </div>
          <span>{report.trials.length} immutable trial artifact(s)</span>
        </div>
        <div className="evaluationEvidenceList">
          {report.trials.map((trial) => {
            const calendarRows = trial.net_returns.map((netReturn, index) => ({
              netReturn,
              returnStatus: trial.return_statuses[index],
              timestamp: trial.return_timestamps_utc[index],
            }));

            return (
              <article
                className="evaluationEvidenceCard"
                aria-label={`Trial ${trial.trial_key}`}
                key={trial.trial_id}
              >
                <header>
                  <div>
                    <span>Trial {trial.ordinal + 1}</span>
                    <h4>{trial.trial_key}</h4>
                  </div>
                  <code>{trial.status}</code>
                </header>
                <DetailGrid
                  values={[
                    ["Trial ID", trial.trial_id],
                    ["Trial SHA-256", trial.trial_sha256],
                    ["Config SHA-256", trial.config_sha256],
                    ["Policy SHA-256", trial.policy_sha256],
                    ["Strategy family", trial.strategy_family],
                    ["Selection scope", trial.selection_scope],
                    ["Counts toward raw", trial.counts_toward_raw],
                    ["Effective contribution", trial.effective_trial_contribution],
                    ["Selection metric", trial.selection_metric],
                    ["Sharpe convention", trial.sharpe_convention],
                    ["OOS return state", trial.oos_return_state],
                    ["Initiated at UTC", trial.initiated_at_utc],
                    ["Initiated by", trial.initiated_by],
                    ["Failure reason", trial.failure_reason],
                    ["Signal specification SHA-256", trial.signal_specification_sha256],
                    ["Feature specification SHA-256", trial.feature_specification_sha256],
                    ["Label specification SHA-256", trial.label_specification_sha256],
                    ["Selection policy SHA-256", trial.selection_policy_sha256],
                    ["Cost policy SHA-256", trial.cost_policy_sha256],
                    ["Stress policy SHA-256", trial.stress_policy_sha256],
                    ["Risk policy SHA-256", trial.risk_policy_sha256],
                  ]}
                />
                <KeyValueEvidence heading="Configuration" values={trial.configuration} />
                <section className="evaluationCanonicalEvidence">
                  <h4>Configuration hash preimage</h4>
                  <pre tabIndex={0}>{JSON.stringify(trial.config_preimage, null, 2)}</pre>
                </section>
                <div className="evaluationEvidenceColumns">
                  <EvidenceGroup heading="Parent trial IDs" values={trial.parent_trial_ids} />
                  <section className="evaluationEvidenceGroup">
                    <h4>Trial return calendar and net returns</h4>
                    {calendarRows.length > 0 ? (
                      <ol className="evaluationCalendarList">
                        {calendarRows.map((row, index) => (
                          <li key={`${trial.trial_id}-${index}`}>
                            <time>{row.timestamp ?? "Calendar timestamp unavailable"}</time>
                            <span>Return status: {row.returnStatus ?? "missing"}</span>
                            <code>{row.netReturn ?? "null"}</code>
                          </li>
                        ))}
                      </ol>
                    ) : (
                      <p className="evaluationEmptyValue">No return calendar recorded</p>
                    )}
                  </section>
                </div>
              </article>
            );
          })}
        </div>
      </section>

      <section className="evaluationPanel" aria-labelledby="folds-heading">
        <div className="evaluationSectionHeading">
          <div>
            <p className="eyebrow">Purged chronology</p>
            <h3 id="folds-heading">Walk-forward folds</h3>
          </div>
          <span>{report.folds.length} immutable fold artifact(s)</span>
        </div>
        <div className="evaluationEvidenceList">
          {report.folds.map((fold) => (
            <article
              className="evaluationEvidenceCard"
              aria-label={`Fold ${fold.fold_id}`}
              key={fold.fold_id}
            >
              <header>
                <div>
                  <span>Fold {fold.ordinal + 1}</span>
                  <h4>{humanize(fold.fold_kind)}</h4>
                </div>
                <code>{fold.embargo_applied ? "embargo applied" : "no embargo"}</code>
              </header>
              <DetailGrid
                values={[
                  ["Fold ID", fold.fold_id],
                  ["Fold SHA-256", fold.fold_sha256],
                  ["Parent fold ID", fold.parent_fold_id],
                  ["Train start UTC", fold.train_start_utc],
                  ["Train end UTC", fold.train_end_utc],
                  ["Test start UTC", fold.test_start_utc],
                  ["Test end UTC", fold.test_end_utc],
                  ["Embargo applied", fold.embargo_applied],
                  ["Embargo duration seconds", fold.embargo_duration_seconds],
                ]}
              />
              <div className="evaluationSampleGrid">
                <EvidenceGroup heading="Train sample IDs" values={fold.train_sample_ids} />
                <EvidenceGroup heading="Test sample IDs" values={fold.test_sample_ids} />
                <EvidenceGroup heading="Purged sample IDs" values={fold.purged_sample_ids} />
                <EvidenceGroup heading="Embargoed sample IDs" values={fold.embargoed_sample_ids} />
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="evaluationPanel" aria-labelledby="fits-heading">
        <div className="evaluationSectionHeading">
          <div>
            <p className="eyebrow">Train-only state</p>
            <h3 id="fits-heading">Preprocessing fits</h3>
          </div>
          <span>{report.preprocessing_fits.length} immutable fit artifact(s)</span>
        </div>
        <div className="evaluationEvidenceList">
          {report.preprocessing_fits.map((fit) => (
            <article
              className="evaluationEvidenceCard"
              aria-label={`Preprocessing fit ${fit.fit_id}`}
              key={fit.fit_id}
            >
              <header>
                <div>
                  <span>Transformer</span>
                  <h4>{fit.transformer_id}</h4>
                </div>
                <code>{fit.transformer_version}</code>
              </header>
              <DetailGrid
                values={[
                  ["Fit ID", fit.fit_id],
                  ["Fit SHA-256", fit.fit_sha256],
                  ["Fold ID", fit.fold_id],
                  ["Train sample IDs SHA-256", fit.train_sample_ids_sha256],
                  ["Mean", fit.mean],
                  ["Standard deviation", fit.standard_deviation],
                  ["Degrees of freedom", fit.ddof],
                  ["Statistics SHA-256", fit.statistics_sha256],
                ]}
              />
              <EvidenceGroup heading="Train sample IDs" values={fit.train_sample_ids} />
            </article>
          ))}
        </div>
      </section>

      <section className="evaluationPanel" aria-labelledby="oos-ledger-heading">
        <div className="evaluationSectionHeading">
          <div>
            <p className="eyebrow">Untouched outer folds</p>
            <h3 id="oos-ledger-heading">OOS prediction and return ledger</h3>
          </div>
          <span>{report.oos_ledger.length} append-only row(s)</span>
        </div>
        <div
          aria-label="Scrollable OOS prediction and return ledger"
          className="evaluationTableScroll"
          role="region"
          tabIndex={0}
        >
          <table className="evaluationDataTable" aria-label="OOS prediction and return ledger">
            <thead>
              <tr>
                <th>Identity</th>
                <th>Information and label intervals</th>
                <th>Values</th>
                <th>Return state</th>
              </tr>
            </thead>
            <tbody>
              {report.oos_ledger.map((entry) => (
                <tr key={entry.ledger_entry_id}>
                  <td>
                    <strong>{entry.sample_id}</strong>
                    <span>Sample SHA-256: {entry.sample_sha256}</span>
                    <span>Ledger ID: {entry.ledger_entry_id}</span>
                    <span>Ledger SHA-256: {entry.ledger_entry_sha256}</span>
                    <span>Trial ID: {entry.trial_id}</span>
                    <span>Fold ID: {entry.fold_id}</span>
                    {entry.source_observation_refs.map((reference, index) => (
                      <span key={`${entry.ledger_entry_id}-${reference.normalized_observation_id}`}>
                        Source ref {index + 1}: {reference.capability}; snapshot {reference.snapshot_id};
                        snapshot SHA-256 {reference.snapshot_sha256}; raw observation {reference.raw_observation_id};
                        observation revision {reference.observation_revision_id}; normalized observation {reference.normalized_observation_id};
                        raw payload SHA-256 {reference.raw_payload_sha256}; normalized content SHA-256 {reference.normalized_content_sha256}
                      </span>
                    ))}
                  </td>
                  <td>
                    <span>Information: {entry.information_start_utc}</span>
                    <span>through {entry.information_end_utc}</span>
                    <span>Decision: {entry.decision_time_utc}</span>
                    <span>Label: {entry.label_t0_utc}</span>
                    <span>through {entry.label_t1_utc}</span>
                  </td>
                  <td>
                    <span>Predicted value: {entry.predicted_value}</span>
                    <span>Gross return: {entry.gross_return ?? "null"}</span>
                    <span>Baseline net return: {entry.baseline_net_return ?? "null"}</span>
                  </td>
                  <td>
                    <span>Return status: {entry.return_status ?? "observed"}</span>
                    <span>
                      Delisting return handled: {scalarText(entry.delisting_return_handled)}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="evaluationPanel" aria-labelledby="cost-ledger-heading">
        <div className="evaluationSectionHeading">
          <div>
            <p className="eyebrow">Component-separated stress evidence</p>
            <h3 id="cost-ledger-heading">Component cost ledger</h3>
          </div>
          <span>{report.cost_ledger.length} append-only row(s)</span>
        </div>
        <div
          aria-label="Scrollable component cost ledger"
          className="evaluationTableScroll"
          role="region"
          tabIndex={0}
        >
          <table className="evaluationDataTable" aria-label="Component cost ledger">
            <thead>
              <tr>
                <th>Scenario and identity</th>
                <th>Return values</th>
                <th>Cost components</th>
                <th>Capacity state</th>
              </tr>
            </thead>
            <tbody>
              {report.cost_ledger.map((entry) => (
                <tr key={entry.cost_entry_id}>
                  <td>
                    <strong>{entry.scenario}</strong>
                    <span>Sample ID: {entry.sample_id}</span>
                    <span>Cost entry ID: {entry.cost_entry_id}</span>
                    <span>Cost entry SHA-256: {entry.cost_entry_sha256}</span>
                    <span>Allocation input SHA-256: {entry.allocation_input_sha256}</span>
                  </td>
                  <td>
                    <span>Gross return: {entry.gross_return}</span>
                    <span>Net return: {entry.net_return}</span>
                    <span>Return status: {entry.return_status}</span>
                  </td>
                  <td>
                    <span>Fee: {entry.fee_cost}</span>
                    <span>Spread: {entry.spread_cost}</span>
                    <span>Impact: {entry.impact_cost}</span>
                    <span>Latency: {entry.latency_cost}</span>
                    <span>Borrow: {entry.borrow_cost}</span>
                    <span>Capacity: {entry.capacity_cost}</span>
                    <span>Total: {entry.total_cost}</span>
                  </td>
                  <td>
                    <span>Fill status: {entry.fill_status}</span>
                    <span>Requested quantity: {entry.requested_quantity}</span>
                    <span>Filled quantity: {entry.filled_quantity}</span>
                    <span>Rejected quantity: {entry.rejected_quantity}</span>
                    <span>Unfilled quantity: {entry.unfilled_quantity}</span>
                    <span>Participation rate: {entry.participation_rate}</span>
                    <span>Capacity breached: {scalarText(entry.capacity_breached)}</span>
                    <span>
                      Hard-to-borrow available: {scalarText(entry.hard_to_borrow_available)}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="evaluationPanel" aria-labelledby="gates-heading">
        <div className="evaluationSectionHeading">
          <div>
            <p className="eyebrow">Fail-closed review</p>
            <h3 id="gates-heading">All 12 required gates</h3>
          </div>
          <span>{report.gates.length} recorded outcomes</span>
        </div>
        <ol className="evaluationGateList" aria-label="Evaluation gates">
          {report.gates.map((gate) => (
            <li key={gate.gate_result_id}>
              <article
                className="evaluationGateCard"
                data-outcome={gate.outcome}
                aria-label={`${gateLabels[gate.gate_code]} gate`}
              >
                <header>
                  <div>
                    <span>{gate.gate_code}</span>
                    <h3>{gateLabels[gate.gate_code]}</h3>
                  </div>
                  <code>{gate.outcome}</code>
                </header>
                <div className="evaluationGateEvidence">
                  <KeyValueEvidence heading="Inputs" values={gate.inputs} />
                  <KeyValueEvidence heading="Thresholds" values={gate.thresholds} />
                  <KeyValueEvidence heading="Results" values={gate.results} />
                </div>
                <div className="evaluationGateMessages">
                  <section>
                    <h4>Reason codes</h4>
                    <EvidenceList values={gate.reason_codes} emptyLabel="None recorded" />
                  </section>
                  <section>
                    <h4>Warnings</h4>
                    <EvidenceList values={gate.warnings} emptyLabel="None recorded" />
                  </section>
                </div>
                <dl className="evaluationGateAudit">
                  <div>
                    <dt>Gate result ID</dt>
                    <dd>{gate.gate_result_id}</dd>
                  </div>
                  <div>
                    <dt>Gate result SHA-256</dt>
                    <dd>{gate.gate_result_sha256}</dd>
                  </div>
                  <div>
                    <dt>Config hash</dt>
                    <dd>{gate.config_hash}</dd>
                  </div>
                </dl>
              </article>
            </li>
          ))}
        </ol>
      </section>

      <section className="evaluationPanel" aria-labelledby="metrics-heading">
        <div className="evaluationSectionHeading">
          <div>
            <p className="eyebrow">Calculation evidence</p>
            <h3 id="metrics-heading">Metrics and metadata</h3>
          </div>
          <span>{report.metrics.length} immutable metric record(s)</span>
        </div>
        <div className="evaluationMetricList">
          {report.metrics.map((metric) => (
            <article className="evaluationMetricCard" key={metric.metric_id}>
              <header>
                <h4>{metric.metric_id}</h4>
                <strong>
                  {metric.value} {metric.units}
                </strong>
              </header>
              <dl>
                <div>
                  <dt>Formula version</dt>
                  <dd>{metric.formula_version}</dd>
                </div>
                <div>
                  <dt>Frequency</dt>
                  <dd>{metric.frequency}</dd>
                </div>
                <div>
                  <dt>Annualization factor</dt>
                  <dd>{metric.annualization_factor}</dd>
                </div>
                <div>
                  <dt>Calendar / timezone</dt>
                  <dd>
                    {metric.calendar} / {metric.timezone}
                  </dd>
                </div>
                <div>
                  <dt>Population</dt>
                  <dd>{metric.population}</dd>
                </div>
                <div>
                  <dt>Denominator</dt>
                  <dd>{metric.denominator}</dd>
                </div>
              </dl>
              <KeyValueEvidence heading="Metric inputs" values={metric.inputs} />
              <section className="evaluationMetricExclusions">
                <h5>Exclusions</h5>
                <EvidenceList values={metric.exclusions} emptyLabel="None recorded" />
              </section>
            </article>
          ))}
        </div>
      </section>

      <section className="evaluationPanel" aria-labelledby="snapshots-heading">
        <div className="evaluationSectionHeading">
          <div>
            <p className="eyebrow">Point-in-time lineage</p>
            <h3 id="snapshots-heading">Snapshot evidence</h3>
          </div>
          <span>{report.data_snapshots.length} bound snapshot(s)</span>
        </div>
        <div className="evaluationSnapshotList">
          {report.data_snapshots.map((snapshot) => (
            <article className="evaluationSnapshotCard" key={snapshot.snapshot_id}>
              <header>
                <h4>{snapshot.capability}</h4>
                <code>{snapshot.quality_status}</code>
              </header>
              <dl>
                <div>
                  <dt>Snapshot ID</dt>
                  <dd>{snapshot.snapshot_id}</dd>
                </div>
                <div>
                  <dt>Snapshot SHA-256</dt>
                  <dd>{snapshot.snapshot_sha256}</dd>
                </div>
                <div>
                  <dt>Provider / product</dt>
                  <dd>
                    {snapshot.provider_id} / {snapshot.product_id}
                  </dd>
                </div>
                <div>
                  <dt>Dataset</dt>
                  <dd>{snapshot.dataset_id}</dd>
                </div>
                <div>
                  <dt>Adapter</dt>
                  <dd>
                    {snapshot.adapter_id} / {snapshot.adapter_version}
                  </dd>
                </div>
                <div>
                  <dt>Fixture set version</dt>
                  <dd>{snapshot.fixture_set_version}</dd>
                </div>
                <div>
                  <dt>As of UTC</dt>
                  <dd>{snapshot.as_of_utc}</dd>
                </div>
                <div>
                  <dt>Dataset schema versions</dt>
                  <dd>{snapshot.dataset_schema_versions.join(", ")}</dd>
                </div>
              </dl>
            </article>
          ))}
        </div>
      </section>

      <section className="evaluationPanel" aria-labelledby="source-observations-heading">
        <div className="evaluationSectionHeading">
          <div>
            <p className="eyebrow">Exact persisted inputs</p>
            <h3 id="source-observations-heading">Phase 4 source observations</h3>
          </div>
          <span>{report.source_observations.length} resolved observation(s)</span>
        </div>
        <div className="evaluationEvidenceList">
          {report.source_observations.map((source) => {
            const observation = source.normalized_observation;
            return (
              <article
                className="evaluationEvidenceCard"
                aria-label={`Source observation ${observation.normalized_observation_id}`}
                key={`${source.key.capability}-${observation.normalized_observation_id}`}
              >
                <header>
                  <div>
                    <span>{source.key.capability}</span>
                    <h4>{observation.normalized_observation_id}</h4>
                  </div>
                  <code>{source.disposition}</code>
                </header>
                <DetailGrid
                  values={[
                    ["Resolved schema version", source.schema_version],
                    ["Snapshot ID", observation.snapshot_id],
                    ["Snapshot SHA-256", observation.snapshot_sha256],
                    ["Normalized observation ID", observation.normalized_observation_id],
                    ["Normalized content SHA-256", observation.normalized_content_sha256],
                    ["Raw observation ID", observation.raw_observation_id],
                    ["Observation revision ID", observation.observation_revision_id],
                    ["Raw payload SHA-256", observation.raw_payload_sha256],
                    ["Logical record ID", observation.logical_record_id],
                    ["Logical record key SHA-256", observation.logical_record_key_sha256],
                    ["Provider ID", observation.provider_id],
                    ["Adapter", `${observation.adapter_id} / ${observation.adapter_version}`],
                    ["Dataset", `${observation.dataset_id} / ${observation.product_id}`],
                    ["Dataset schema ID", observation.dataset_schema_id],
                    ["Dataset schema version", observation.dataset_schema_version],
                    ["Source record ID", observation.source_record_id],
                    ["Revision ID", observation.revision_id],
                    ["Vintage ID", observation.vintage_id],
                    ["Event time", observation.event_time],
                    ["Available at", observation.available_at],
                    ["Retrieved at", observation.retrieved_at],
                    ["Valid from", observation.valid_from],
                    ["Valid to", observation.valid_to],
                  ]}
                />
                <section className="evaluationCanonicalEvidence">
                  <h4>Exact persisted source observation</h4>
                  <pre tabIndex={0}>{JSON.stringify(source, null, 2)}</pre>
                </section>
              </article>
            );
          })}
        </div>
      </section>

      <section className="evaluationPanel" aria-labelledby="sample-lineage-heading">
        <div className="evaluationSectionHeading">
          <div>
            <p className="eyebrow">Sample-to-source binding</p>
            <h3 id="sample-lineage-heading">Sample lineage</h3>
          </div>
          <span>{report.sample_lineage.length} sample record(s)</span>
        </div>
        <DetailGrid values={[["Sample lineage SHA-256", report.sample_lineage_sha256]]} />
        <div className="evaluationEvidenceList">
          {report.sample_lineage.map((lineage) => (
            <article
              className="evaluationEvidenceCard"
              aria-label={`Sample lineage ${lineage.sample_id}`}
              key={lineage.sample_id}
            >
              <header>
                <div>
                  <span>Sample</span>
                  <h4>{lineage.sample_id}</h4>
                </div>
              </header>
              <DetailGrid
                values={[
                  ["Sample SHA-256", lineage.sample_sha256],
                  ["Decision time UTC", lineage.decision_time_utc],
                  ["Synthetic ledger value rule", lineage.synthetic_ledger_value_rule],
                  ["Feature derivation SHA-256", lineage.feature_derivation.derivation_sha256],
                  ["Feature derivation schema", lineage.feature_derivation.schema_version],
                  ["Feature derivation formula", lineage.feature_derivation.formula_id],
                  [
                    "Feature source observation",
                    lineage.feature_derivation.source_observation_key.normalized_observation_id,
                  ],
                  ["Feature source payload field", lineage.feature_derivation.source_payload_field],
                  ["Feature multiplier", lineage.feature_derivation.multiplier],
                  ["Derived feature value", lineage.feature_derivation.derived_feature_value],
                  ["Source reference count", lineage.source_observation_refs.length],
                ]}
              />
              <SourceObservationReferences references={lineage.source_observation_refs} />
              <section className="evaluationCanonicalEvidence">
                <h4>Exact sample lineage record</h4>
                <pre tabIndex={0}>{JSON.stringify(lineage, null, 2)}</pre>
              </section>
            </article>
          ))}
        </div>
      </section>

      <section className="evaluationPanel" aria-labelledby="audit-heading">
        <div className="evaluationSectionHeading">
          <div>
            <p className="eyebrow">Immutable lineage</p>
            <h3 id="audit-heading">Audit fields</h3>
          </div>
        </div>
        <dl className="evaluationAuditGrid">
          {auditFields.map(([label, value]) => (
            <div key={label}>
              <dt>{label}</dt>
              <dd>{value}</dd>
            </div>
          ))}
        </dl>
        <div className="evaluationEvidenceColumns">
          <section>
            <h4>Provider/source versions</h4>
            <EvidenceList
              values={report.provider_source_versions}
              emptyLabel="None recorded"
            />
          </section>
          <section>
            <h4>Parent artifact IDs</h4>
            <EvidenceList values={report.parent_artifact_ids} emptyLabel="None recorded" />
          </section>
          <section>
            <h4>Report reason codes</h4>
            <EvidenceList values={report.reason_codes} emptyLabel="None recorded" />
          </section>
          <section>
            <h4>Report warnings</h4>
            <EvidenceList values={report.warnings} emptyLabel="None recorded" />
          </section>
        </div>
      </section>
    </div>
  );
}
