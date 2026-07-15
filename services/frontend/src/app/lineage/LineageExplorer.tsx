"use client";

import type { components } from "@fable5/contracts";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import {
  HistoricalEvidenceTimeline,
  timelineFailureForAssessment,
} from "../../components/GovernanceEvidence";
import { fable5Api, type ApiFailure } from "../../lib/api";
import {
  evaluationOutcomeMatchesMapping,
  evaluationOutcomeMatchesResearchRun,
  evaluationEvidenceForResearchRun,
  evaluationReportMatchesResearchRun,
  type EvidenceIndex,
  mappingMatchesCard,
  mappingMatchesEvaluationReport,
  mappingMatchesResearchRun,
  researchRunMatchesAssessment,
  revocationMatchesAssessment,
  snapshotMatchesBlockedOutcomeEvidence,
  snapshotMatchesEvaluationReportEvidence,
  snapshotMatchesMapping,
  snapshotsForResearchRun,
  useEvidenceIndex,
} from "../../lib/evidence-index";
import { useEvidenceRetryFocus } from "../../lib/use-evidence-retry-focus";

type SourceVersion = components["schemas"]["SourceVersion"];
type Extraction = components["schemas"]["ExtractionRequestRecord"];
type TradingIdeaCard = components["schemas"]["TradingIdeaCard"];
type Mapping = components["schemas"]["MappingWithRationale"];
type EvaluationReport = components["schemas"]["EvaluationReport"];
type EvaluationOutcome = components["schemas"]["BlockedEvaluationOutcome"];
type ResearchRun = components["schemas"]["ResearchRunArtifact"];
type Assessment = components["schemas"]["ApprovalAssessmentArtifact"];
type Revocation = components["schemas"]["AuthorizationRevocationArtifact"];

export type LineageSelection = {
  assessment?: Assessment;
  card?: TradingIdeaCard;
  evaluationOutcome?: EvaluationOutcome;
  evaluationReport?: EvaluationReport;
  mapping?: Mapping;
  researchRun?: ResearchRun;
  revocation?: Revocation;
};

export type LineageBranchLink = {
  description: string;
  href: string;
  label: string;
};

export function resolveLineageSelection(
  index: EvidenceIndex,
  identifiers: Readonly<Record<string, string | null>>,
): LineageSelection | null {
  const hasEvaluationConflict = Boolean(
    identifiers.evaluation_report_id && identifiers.evaluation_outcome_id,
  );
  const revocationHasUpstreamIdentifier = Boolean(
    identifiers.revocation_id &&
      (identifiers.card_id ||
        identifiers.mapping_id ||
        identifiers.evaluation_report_id ||
        identifiers.evaluation_outcome_id ||
        identifiers.run_id),
  );
  if (
    hasEvaluationConflict ||
    (revocationHasUpstreamIdentifier && !identifiers.assessment_id)
  ) {
    return null;
  }

  const evaluationReport = identifiers.evaluation_report_id
    ? index.evaluationReports.find(
        (item) => item.artifact_id === identifiers.evaluation_report_id,
      )
    : undefined;
  const evaluationOutcome = identifiers.evaluation_outcome_id
    ? index.evaluationOutcomes.find(
        (item) => item.outcome_id === identifiers.evaluation_outcome_id,
      )
    : undefined;
  const revocation = identifiers.revocation_id
    ? index.revocations.find((item) => item.revocation_id === identifiers.revocation_id)
    : undefined;
  const assessment = identifiers.assessment_id
    ? index.assessments.find((item) => item.assessment_id === identifiers.assessment_id)
    : undefined;

  const explicitResearchRun = identifiers.run_id
    ? index.researchRuns.find((item) => item.run_id === identifiers.run_id)
    : undefined;
  const explicitMapping = identifiers.mapping_id
    ? index.mappings.find((item) => item.mapping.mapping_id === identifiers.mapping_id)
    : undefined;
  const explicitCard = identifiers.card_id
    ? index.cards.find((item) => item.card_id === identifiers.card_id)
    : undefined;

  const unresolvedExplicitIdentifier = Boolean(
    (identifiers.evaluation_report_id && !evaluationReport) ||
      (identifiers.evaluation_outcome_id && !evaluationOutcome) ||
      (identifiers.revocation_id && !revocation) ||
      (identifiers.assessment_id && !assessment) ||
      (identifiers.run_id && !explicitResearchRun) ||
      (identifiers.mapping_id && !explicitMapping) ||
      (identifiers.card_id && !explicitCard),
  );
  if (unresolvedExplicitIdentifier) return null;

  const researchRun = explicitResearchRun
    ? explicitResearchRun
    : assessment
      ? index.researchRuns.find((item) => researchRunMatchesAssessment(item, assessment))
      : undefined;

  const mapping = explicitMapping
    ? explicitMapping
    : researchRun
      ? index.mappings.find((item) => mappingMatchesResearchRun(item, researchRun))
      : evaluationReport
        ? index.mappings.find((item) => mappingMatchesEvaluationReport(item, evaluationReport))
        : evaluationOutcome
          ? index.mappings.find((item) =>
              evaluationOutcomeMatchesMapping(evaluationOutcome, item),
            )
          : undefined;

  const card = explicitCard
    ? explicitCard
    : mapping
      ? index.cards.find((item) => mappingMatchesCard(mapping, item))
      : undefined;

  const revocationAssessmentConnectionMissing = Boolean(
    revocationHasUpstreamIdentifier &&
      (!assessment ||
        !revocation ||
        !researchRun ||
        !researchRunMatchesAssessment(researchRun, assessment) ||
        !revocationMatchesAssessment(revocation, assessment) ||
        (identifiers.mapping_id &&
          (!mapping || !mappingMatchesResearchRun(mapping, researchRun))) ||
        (identifiers.card_id &&
          (!mapping ||
            !card ||
            !mappingMatchesResearchRun(mapping, researchRun) ||
            !mappingMatchesCard(mapping, card))) ||
        (identifiers.evaluation_report_id &&
          (!evaluationReport ||
            !evaluationReportMatchesResearchRun(evaluationReport, researchRun))) ||
        (identifiers.evaluation_outcome_id &&
          (!evaluationOutcome ||
            !evaluationOutcomeMatchesResearchRun(evaluationOutcome, researchRun)))),
  );
  if (revocationAssessmentConnectionMissing) return null;

  const explicitReferenceConflict = Boolean(
    (assessment && researchRun && !researchRunMatchesAssessment(researchRun, assessment)) ||
      (assessment &&
        revocation &&
        !revocationMatchesAssessment(revocation, assessment)) ||
      (researchRun && mapping && !mappingMatchesResearchRun(mapping, researchRun)) ||
      (evaluationReport &&
        mapping &&
        !mappingMatchesEvaluationReport(mapping, evaluationReport)) ||
      (evaluationOutcome &&
        mapping &&
        !evaluationOutcomeMatchesMapping(evaluationOutcome, mapping)) ||
      (mapping && card && !mappingMatchesCard(mapping, card)) ||
      (researchRun &&
        evaluationReport &&
        !evaluationReportMatchesResearchRun(evaluationReport, researchRun)) ||
      (researchRun &&
        evaluationOutcome &&
        !evaluationOutcomeMatchesResearchRun(evaluationOutcome, researchRun)),
  );
  if (explicitReferenceConflict) return null;

  if (
    !card &&
    !mapping &&
    !evaluationReport &&
    !evaluationOutcome &&
    !researchRun &&
    !assessment &&
    !revocation
  ) {
    return null;
  }
  return {
    assessment,
    card,
    evaluationOutcome,
    evaluationReport,
    mapping,
    researchRun,
    revocation,
  };
}

function lineageHref(values: Readonly<Record<string, string | undefined>>) {
  const parameters = new URLSearchParams();
  for (const key of [
    "card_id",
    "mapping_id",
    "evaluation_report_id",
    "evaluation_outcome_id",
    "run_id",
    "assessment_id",
    "revocation_id",
  ]) {
    const value = values[key];
    if (value) parameters.set(key, value);
  }
  return `/lineage?${parameters.toString()}`;
}

function relatedRevocations(index: EvidenceIndex, assessment: Assessment) {
  return index.revocations.filter((revocation) =>
    revocationMatchesAssessment(revocation, assessment),
  );
}

function exactAncestors(index: EvidenceIndex, run: ResearchRun) {
  const mapping = index.mappings.find(
    (candidate) => mappingMatchesResearchRun(candidate, run),
  );
  const card = mapping
    ? index.cards.find((candidate) => mappingMatchesCard(mapping, candidate))
    : undefined;
  return { card, mapping };
}

function branchesForAssessment(
  index: EvidenceIndex,
  assessment: Assessment,
): LineageBranchLink[] {
  const run = index.researchRuns.find(
    (candidate) => researchRunMatchesAssessment(candidate, assessment),
  );
  const ancestors = run
    ? exactAncestors(index, run)
    : { card: undefined, mapping: undefined };
  const base = {
    assessment_id: assessment.assessment_id,
    card_id: ancestors.card?.card_id,
    mapping_id: ancestors.mapping?.mapping.mapping_id,
    run_id: run?.run_id,
  };
  const revocations = relatedRevocations(index, assessment);
  if (revocations.length === 0) {
    return [
      {
        description: "Complete immutable assessment artifact; no linked revocation was loaded.",
        href: lineageHref(base),
        label: `Assessment ${assessment.assessment_id}`,
      },
    ];
  }
  return revocations.map((revocation) => {
    const boundAtAssessment = assessment.revocation_ids.includes(revocation.revocation_id);
    return {
      description: boundAtAssessment
        ? "Revocation identifier is embedded in the immutable assessment artifact."
        : "Additional append-only revocation shares the exact authorization reference.",
      href: lineageHref({ ...base, revocation_id: revocation.revocation_id }),
      label: `${boundAtAssessment ? "Assessment-bound" : "Authorization-linked"} revocation ${revocation.revocation_id}`,
    };
  });
}

function branchesForRun(index: EvidenceIndex, run: ResearchRun): LineageBranchLink[] {
  const assessments = index.assessments.filter(
    (assessment) => researchRunMatchesAssessment(run, assessment),
  );
  if (assessments.length > 0) {
    return assessments.flatMap((assessment) => branchesForAssessment(index, assessment));
  }
  const ancestors = exactAncestors(index, run);
  return [
    {
      description: "Research is the last real immutable artifact on this branch.",
      href: lineageHref({
        card_id: ancestors.card?.card_id,
        mapping_id: ancestors.mapping?.mapping.mapping_id,
        run_id: run.run_id,
      }),
      label: `Research run ${run.run_id}`,
    },
  ];
}

function branchesForMapping(index: EvidenceIndex, mapping: Mapping): LineageBranchLink[] {
  const mappingId = mapping.mapping.mapping_id;
  const cardId = index.cards.find((card) => mappingMatchesCard(mapping, card))?.card_id;
  const runs = index.researchRuns.filter((run) => mappingMatchesResearchRun(mapping, run));
  const links = runs.flatMap((run) => branchesForRun(index, run));
  const linkedReportIds = new Set(
    runs.flatMap((run) =>
      run.phase5_evaluation.evaluation_report_id &&
      index.evaluationReports.some(
        (report) =>
          evaluationReportMatchesResearchRun(report, run) &&
          mappingMatchesEvaluationReport(mapping, report),
      )
        ? [run.phase5_evaluation.evaluation_report_id]
        : [],
    ),
  );
  const linkedOutcomeIds = new Set(
    runs.flatMap((run) => {
      const outcome = index.evaluationOutcomes.find((candidate) =>
        evaluationOutcomeMatchesResearchRun(candidate, run),
      );
      return outcome && evaluationOutcomeMatchesMapping(outcome, mapping)
        ? [outcome.outcome_id]
        : [];
    }),
  );
  links.push(
    ...index.evaluationReports
      .filter(
        (report) =>
          mappingMatchesEvaluationReport(mapping, report) &&
          !linkedReportIds.has(report.artifact_id),
      )
      .map((report) => ({
        description: "Evaluation is the last real immutable artifact on this branch.",
        href: lineageHref({
          card_id: cardId,
          evaluation_report_id: report.artifact_id,
          mapping_id: mappingId,
        }),
        label: `Evaluation report ${report.artifact_id}`,
      })),
    ...index.evaluationOutcomes
      .filter(
        (outcome) =>
          evaluationOutcomeMatchesMapping(outcome, mapping) &&
          !linkedOutcomeIds.has(outcome.outcome_id),
      )
      .map((outcome) => ({
        description: "Blocked evaluation is the last real immutable artifact on this branch.",
        href: lineageHref({
          card_id: cardId,
          evaluation_outcome_id: outcome.outcome_id,
          mapping_id: mappingId,
        }),
        label: `Blocked evaluation ${outcome.outcome_id}`,
      })),
  );
  if (links.length === 0) {
    links.push({
      description: "Mapping is the last real immutable artifact on this branch.",
      href: lineageHref({ card_id: cardId, mapping_id: mappingId }),
      label: `Mapping ${mappingId}`,
    });
  }
  return links;
}

export function lineageBranchLinks(
  index: EvidenceIndex,
  selection: LineageSelection,
  identifiers: Readonly<Record<string, string | null>>,
): LineageBranchLink[] {
  let links: LineageBranchLink[] = [];
  if (identifiers.assessment_id && selection.assessment) {
    links = [];
  } else if (identifiers.revocation_id && selection.revocation) {
    links = index.assessments
      .filter(
        (assessment) =>
          selection.revocation !== undefined &&
          revocationMatchesAssessment(selection.revocation, assessment),
      )
      .flatMap((assessment) =>
        branchesForAssessment(index, assessment).filter((link) =>
          link.href.includes(`revocation_id=${selection.revocation?.revocation_id}`),
        ),
      );
  } else if (identifiers.run_id && selection.researchRun) {
    links = branchesForRun(index, selection.researchRun).filter(
      (link) => !link.href.endsWith(`run_id=${selection.researchRun?.run_id}`),
    );
  } else if (
    (identifiers.evaluation_report_id || identifiers.evaluation_outcome_id) &&
    (selection.evaluationReport || selection.evaluationOutcome)
  ) {
    const runs = index.researchRuns.filter((run) => {
      if (selection.evaluationReport) {
        return evaluationReportMatchesResearchRun(selection.evaluationReport, run);
      }
      return (
        selection.evaluationOutcome !== undefined &&
        evaluationOutcomeMatchesResearchRun(selection.evaluationOutcome, run)
      );
    });
    links = runs.flatMap((run) => branchesForRun(index, run));
  } else if (identifiers.mapping_id && selection.mapping) {
    links = branchesForMapping(index, selection.mapping).filter(
      (link) => !link.href.endsWith(`mapping_id=${selection.mapping?.mapping.mapping_id}`),
    );
  } else if (identifiers.card_id && selection.card) {
    links = index.mappings
      .filter(
        (mapping) =>
          selection.card !== undefined && mappingMatchesCard(mapping, selection.card),
      )
      .flatMap((mapping) => branchesForMapping(index, mapping));
  }

  return [...new Map(links.map((link) => [link.href, link])).values()];
}

function ArtifactDisclosure({
  artifact,
  defaultOpen = false,
  label,
}: {
  artifact: unknown;
  defaultOpen?: boolean;
  label: string;
}) {
  return (
    <details className="evidenceDisclosure" open={defaultOpen || undefined}>
      <summary>Inspect complete {label}</summary>
      <pre tabIndex={0}>{JSON.stringify(artifact, null, 2)}</pre>
    </details>
  );
}

function safeRevocationArtifact(revocation: Revocation) {
  const safe: Record<string, unknown> = { ...revocation };
  delete safe.reason;
  delete safe.revoked_by;
  safe.restricted_fields = ["reviewer rationale", "reviewer identity"];
  return safe;
}

function safeCardArtifact(card: TradingIdeaCard) {
  if (card.synthetic_fixture) return card;
  return {
    ...card,
    quoted_claims: card.quoted_claims.map((claim) => ({
      ...claim,
      exact_text: "[referenced by source span and SHA-256]",
    })),
    raw_text: "[referenced by content SHA-256]",
    source_url: card.source_url === null ? null : "[referenced by source ID]",
  };
}

function safeSourceVersionArtifact(sourceVersion: SourceVersion, syntheticFixture: boolean) {
  if (syntheticFixture) return sourceVersion;
  return {
    ...sourceVersion,
    raw_text:
      sourceVersion.raw_text === null ? null : "[referenced by content SHA-256]",
    source_url:
      sourceVersion.source_url === null ? null : "[referenced by source ID]",
  };
}

function HashValue({ children }: { children: string | null | undefined }) {
  return <span className="mono visualMask">{children ?? "Not persisted"}</span>;
}

type ArtifactState<T> =
  | { status: "loading" }
  | { status: "success"; artifact: T }
  | { status: "error"; error: ApiFailure };

function lineageReferenceConflict(artifactLabel: string): ApiFailure {
  return {
    kind: "conflict",
    message: `The returned ${artifactLabel} conflicts with the TradingIdeaCard's immutable references.`,
    retrySafe: true,
  };
}

function sameOrderedValues(left: readonly string[] = [], right: readonly string[] = []) {
  return left.length === right.length && left.every((value, index) => value === right[index]);
}

function sourceVersionMatchesCard(
  sourceVersion: SourceVersion,
  card: TradingIdeaCard,
  mapping?: Mapping,
) {
  return (
    sourceVersion.source_version_id === card.source_version_id &&
    sourceVersion.source_id === card.source_id &&
    sourceVersion.source_version === card.source_version &&
    sourceVersion.source_authority === card.source_authority &&
    sourceVersion.source_url === card.source_url &&
    sourceVersion.raw_text === card.raw_text &&
    sameOrderedValues(
      sourceVersion.official_corroboration_source_version_ids,
      card.official_corroboration_source_version_ids,
    ) &&
    (sourceVersion.source_type === "synthetic_fixture") === card.synthetic_fixture &&
    (mapping === undefined ||
      mapping.mapping.source_content_sha256 === sourceVersion.content_sha256)
  );
}

function extractionMatchesCard(
  extraction: Extraction,
  card: TradingIdeaCard,
  mapping?: Mapping,
) {
  return (
    extraction.extraction_request_id === card.extraction_request_id &&
    extraction.source_version_id === card.source_version_id &&
    extraction.latest_event === "succeeded" &&
    extraction.extraction_config_sha256 === card.extraction_config_sha256 &&
    extraction.extraction_schema_version === card.extraction_schema_version &&
    extraction.extractor_kind === card.extractor_kind &&
    extraction.extractor_id === card.extractor_id &&
    extraction.extractor_version === card.extractor_version &&
    extraction.extraction_model_id === card.extraction_model_id &&
    extraction.extraction_model_revision === card.extraction_model_revision &&
    extraction.extraction_prompt_sha256 === card.extraction_prompt_sha256 &&
    extraction.extraction_prompt_version === card.extraction_prompt_version &&
    (mapping === undefined ||
      mapping.mapping.extraction_request_fingerprint === extraction.request_fingerprint)
  );
}

function NormalizedCardEvidence({ card }: { card: TradingIdeaCard }) {
  return (
    <li>
      <div>
        <strong>Normalized TradingIdeaCard</strong>
        <p>{card.testability_status}</p>
        <p className="mono">Card ID: {card.card_id}</p>
        <HashValue>{card.extraction_config_sha256}</HashValue>
        <ArtifactDisclosure artifact={safeCardArtifact(card)} label="normalized card artifact" />
      </div>
    </li>
  );
}

export function SourceEvidence({ card, mapping }: { card: TradingIdeaCard; mapping?: Mapping }) {
  const [sourceState, setSourceState] = useState<ArtifactState<SourceVersion>>({
    status: "loading",
  });
  const [extractionState, setExtractionState] = useState<ArtifactState<Extraction>>({
    status: "loading",
  });

  useEffect(() => {
    const controller = new AbortController();
    void fable5Api.getSourceVersion(card.source_version_id, controller.signal).then((sourceResult) => {
      if (!sourceResult.ok) {
        if (sourceResult.error.kind !== "aborted") {
          setSourceState({ status: "error", error: sourceResult.error });
        }
        return;
      }

      if (!sourceVersionMatchesCard(sourceResult.data, card, mapping)) {
        setSourceState({
          status: "error",
          error: lineageReferenceConflict("source version"),
        });
        return;
      }

      setSourceState({ status: "success", artifact: sourceResult.data });
    });
    void fable5Api.getExtraction(card.extraction_request_id, controller.signal).then((extractionResult) => {
      if (!extractionResult.ok) {
        if (extractionResult.error.kind !== "aborted") {
          setExtractionState({ status: "error", error: extractionResult.error });
        }
        return;
      }

      if (!extractionMatchesCard(extractionResult.data, card, mapping)) {
        setExtractionState({
          status: "error",
          error: lineageReferenceConflict("extraction record"),
        });
        return;
      }

      setExtractionState({ status: "success", artifact: extractionResult.data });
    });
    return () => controller.abort();
  }, [card, mapping]);

  return (
    <>
      {sourceState.status === "loading" ? (
        <li>
          <p className="statePanel" role="status" aria-live="polite">
            Loading source and extraction evidence: source input pending.
          </p>
        </li>
      ) : null}
      {sourceState.status === "error" ? (
        <li>
          <strong>Source input unavailable</strong>
          <p className="statePanel" role="alert">
            {sourceState.error.message} The lineage stops at the last retrievable immutable
            identifier for this step; no substitute was inferred.
          </p>
          <p className="mono">Referenced source version ID: {card.source_version_id}</p>
        </li>
      ) : null}
      {sourceState.status === "success" ? (
        <li>
          <div>
            <strong>Source input</strong>
            <p>
              {sourceState.artifact.source_type} / {sourceState.artifact.source_authority}
            </p>
            <HashValue>{sourceState.artifact.content_sha256}</HashValue>
            <p className="mono">Source version ID: {sourceState.artifact.source_version_id}</p>
            <ArtifactDisclosure
              artifact={safeSourceVersionArtifact(sourceState.artifact, card.synthetic_fixture)}
              label="source version artifact"
            />
            {card.synthetic_fixture ? (
              <details className="evidenceDisclosure">
                <summary>Inspect committed synthetic source text</summary>
                <pre tabIndex={0}>{sourceState.artifact.raw_text ?? "No text persisted"}</pre>
              </details>
            ) : (
              <p className="formHint">
                Source content is referenced by identifier and hash; non-synthetic text is not
                reproduced in this lineage view.
              </p>
            )}
          </div>
        </li>
      ) : null}
      {extractionState.status === "loading" ? (
        <li>
          <p className="statePanel" role="status" aria-live="polite">
            Loading source and extraction evidence: extraction pending.
          </p>
        </li>
      ) : null}
      {extractionState.status === "error" ? (
        <li>
          <strong>Extraction unavailable</strong>
          <p className="statePanel" role="alert">
            {extractionState.error.message} The lineage stops at the last retrievable immutable
            identifier for this step; no substitute was inferred.
          </p>
          <p className="mono">Referenced request ID: {card.extraction_request_id}</p>
        </li>
      ) : null}
      {extractionState.status === "success" ? (
        <li>
          <div>
            <strong>Extraction</strong>
            <p>
              {extractionState.artifact.latest_event} / {extractionState.artifact.extractor_kind} /{" "}
              {extractionState.artifact.extractor_id}
            </p>
            <p className="mono">Request ID: {extractionState.artifact.extraction_request_id}</p>
            <HashValue>{extractionState.artifact.request_fingerprint}</HashValue>
            <ArtifactDisclosure artifact={extractionState.artifact} label="extraction record" />
          </div>
        </li>
      ) : null}
      <NormalizedCardEvidence card={card} />
    </>
  );
}

function MappingEvidence({ mapping }: { mapping: Mapping }) {
  return (
    <li>
      <div>
        <strong>Deterministic mapping</strong>
        <p>
          {mapping.mapping.verdict} / {mapping.mapping.canonical_family ?? "No canonical family"}
        </p>
        <p className="mono">Mapping ID: {mapping.mapping.mapping_id}</p>
        <HashValue>{mapping.mapping.mapping_input_sha256}</HashValue>
        <ul className="reasonList" aria-label="Mapping reason codes">
          {mapping.mapping.reason_codes.map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>
        <ArtifactDisclosure artifact={mapping} label="mapping artifact and rationale" />
      </div>
    </li>
  );
}

function terminalMessage(
  selection: LineageSelection,
  branchLinks: LineageBranchLink[],
  lineageRevocations: Revocation[],
  hasAncestorConflict: boolean,
) {
  if (hasAncestorConflict) {
    return "An exact ancestor reference is unavailable. The chain stops at the last real immutable artifact; no substitute was inferred.";
  }
  if (branchLinks.length > 0) {
    return "Exact descendant branches are listed above. No branch was selected or described as absent automatically.";
  }
  if (lineageRevocations.length > 0) {
    return "Immutable revocation evidence is the final persisted governance evidence and remains blocking.";
  }
  if (selection.revocation) return "Revocation is the final persisted governance artifact.";
  if (selection.assessment) return "Assessment is the final persisted governance artifact.";
  if (selection.researchRun) return "No later governance artifact was persisted for this branch.";
  if (selection.evaluationReport || selection.evaluationOutcome) {
    return "No later research artifact was persisted for this evaluation branch.";
  }
  if (selection.mapping) return "No later research artifact was persisted for this branch.";
  return "No later mapping artifact was persisted for this source claim.";
}

export function LineageExplorer() {
  const parameters = useSearchParams();
  const evidence = useEvidenceIndex();
  const {
    retry: retryEvidenceLoad,
    setRetryButton: setEvidenceRetryButton,
  } = useEvidenceRetryFocus(evidence.status, evidence.reload);
  const identifiers = useMemo(
    () => ({
      assessment_id: parameters.get("assessment_id"),
      card_id: parameters.get("card_id"),
      evaluation_outcome_id: parameters.get("evaluation_outcome_id"),
      evaluation_report_id: parameters.get("evaluation_report_id"),
      mapping_id: parameters.get("mapping_id"),
      revocation_id: parameters.get("revocation_id"),
      run_id: parameters.get("run_id"),
    }),
    [parameters],
  );

  if (evidence.status === "loading") {
    return (
      <p className="statePanel" role="status">
        {evidence.message}
      </p>
    );
  }
  if (evidence.status === "empty") {
    return (
      <p className="statePanel" role="status" aria-live="polite">
        {evidence.message}
      </p>
    );
  }
  if (evidence.status === "error") {
    return (
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
    );
  }

  const selection = resolveLineageSelection(evidence.data, identifiers);
  if (!selection) {
    const hasIdentifier = Object.values(identifiers).some(Boolean);
    return (
      <section className="workflowPanel" aria-labelledby="lineage-selection-heading">
        <div className="panelHeader">
          <h2 id="lineage-selection-heading">
            {hasIdentifier ? "Referenced result was not found" : "Choose a persisted result"}
          </h2>
        </div>
        {hasIdentifier ? (
          <p className="statePanel" data-tone="critical" role="status" aria-live="polite">
            No relationship was inferred and no unrelated artifact was substituted.
          </p>
        ) : (
          <div className="resultGrid">
            {evidence.data.cards.map((card) => (
              <article className="evidenceCard" key={card.card_id}>
                <span className="cardKicker">TradingIdeaCard</span>
                <h3>
                  {card.paraphrased_claim ??
                    "Persisted claim referenced by immutable source evidence"}
                </h3>
                <Link className="lineageLink" href={`/lineage?card_id=${card.card_id}`}>
                  Open lineage
                </Link>
              </article>
            ))}
          </div>
        )}
      </section>
    );
  }

  const exactSnapshots = (
    references: ReadonlyArray<{ snapshot_id: string }>,
    matches: (snapshot: EvidenceIndex["snapshots"][number], index: number) => boolean,
    internalConflict = false,
  ) => {
    const snapshots = references.flatMap((reference, referenceIndex) => {
      const snapshot = evidence.data.snapshots.find(
        (candidate) =>
          candidate.snapshot_id === reference.snapshot_id &&
          matches(candidate, referenceIndex),
      );
      return snapshot ? [snapshot] : [];
    });
    return {
      conflict: internalConflict || snapshots.length !== references.length,
      snapshots,
    };
  };
  const snapshotEvidence = selection.researchRun
    ? snapshotsForResearchRun(evidence.data, selection.researchRun)
    : selection.evaluationReport
        ? exactSnapshots(
            selection.evaluationReport.data_snapshots,
            (snapshot, referenceIndex) =>
              snapshotMatchesEvaluationReportEvidence(
                snapshot,
                selection.evaluationReport!.data_snapshots[referenceIndex],
                selection.evaluationReport!,
              ),
          )
        : selection.evaluationOutcome
          ? exactSnapshots(
              selection.evaluationOutcome.resolved_snapshots,
              (snapshot, referenceIndex) =>
                snapshotMatchesBlockedOutcomeEvidence(
                  snapshot,
                  selection.evaluationOutcome!.resolved_snapshots[referenceIndex],
                  selection.evaluationOutcome!,
                ),
              !sameOrderedValues(
                selection.evaluationOutcome.snapshot_ids,
                selection.evaluationOutcome.resolved_snapshots.map(
                  (snapshot) => snapshot.snapshot_id,
                ),
              ),
            )
          : selection.mapping
            ? (() => {
                const candidates = evidence.data.snapshots.filter(
                  (snapshot) =>
                    snapshot.manifest.payload.mapping.mapping_id ===
                    selection.mapping!.mapping.mapping_id,
                );
                const snapshots = candidates.filter((snapshot) =>
                  snapshotMatchesMapping(snapshot, selection.mapping!),
                );
                return { conflict: snapshots.length !== candidates.length, snapshots };
              })()
            : { conflict: false, snapshots: [] };
  const exactEvaluation = selection.researchRun
    ? evaluationEvidenceForResearchRun(evidence.data, selection.researchRun)
    : {
        conflict: false,
        outcome: selection.evaluationOutcome,
        report: selection.evaluationReport,
      };
  const evaluation = exactEvaluation.report;
  const blockedOutcome = exactEvaluation.outcome;
  const timeline = selection.assessment
    ? evidence.data.assessmentTimelines[selection.assessment.assessment_id]
    : undefined;
  const timelineFailure = selection.assessment
    ? timelineFailureForAssessment(evidence.data, selection.assessment.assessment_id)
    : undefined;
  const lineageRevocations = selection.assessment
    ? relatedRevocations(evidence.data, selection.assessment)
    : selection.revocation
      ? [selection.revocation]
      : [];
  const missingBoundRevocations = selection.assessment
    ? selection.assessment.revocation_ids.filter(
        (revocationId) =>
          !lineageRevocations.some(
            (revocation) => revocation.revocation_id === revocationId,
          ),
      )
    : [];
  const ancestorConflicts = [
    selection.assessment && !selection.researchRun
      ? "Assessment research-run ID or artifact hash did not match a loaded immutable artifact."
      : null,
    (selection.researchRun || selection.evaluationReport || selection.evaluationOutcome) &&
    !selection.mapping
      ? "Research or evaluation mapping ID, input hash, or version did not match loaded evidence."
      : null,
    selection.mapping && !selection.card
      ? "Mapping evidence references a TradingIdeaCard that was not loaded."
      : null,
    selection.card &&
    evidence.data.mappings.some(
      (mapping) =>
        mapping.mapping.card_id === selection.card!.card_id &&
        !mappingMatchesCard(mapping, selection.card!),
    )
      ? "A same-card-ID mapping conflicts with the TradingIdeaCard's immutable lineage."
      : null,
    selection.mapping &&
    (evidence.data.evaluationReports.some(
      (report) =>
        report.mapping_id === selection.mapping!.mapping.mapping_id &&
        !mappingMatchesEvaluationReport(selection.mapping!, report),
    ) ||
      evidence.data.evaluationOutcomes.some(
        (outcome) =>
          outcome.mapping_id === selection.mapping!.mapping.mapping_id &&
          !evaluationOutcomeMatchesMapping(outcome, selection.mapping!),
      ) ||
      evidence.data.researchRuns.some(
        (run) =>
          run.mapping_id === selection.mapping!.mapping.mapping_id &&
          !mappingMatchesResearchRun(selection.mapping!, run),
      ))
      ? "A same-mapping-ID evaluation or research artifact conflicts with immutable mapping evidence."
      : null,
    selection.researchRun &&
    evidence.data.assessments.some(
      (assessment) =>
        assessment.research_run_id === selection.researchRun!.run_id &&
        !researchRunMatchesAssessment(selection.researchRun!, assessment),
    )
      ? "A same-run-ID assessment conflicts with the complete immutable research lineage."
      : null,
    selection.evaluationReport &&
    evidence.data.researchRuns.some(
      (run) =>
        run.phase5_evaluation.evaluation_report_id === selection.evaluationReport!.artifact_id &&
        !evaluationReportMatchesResearchRun(selection.evaluationReport!, run),
    )
      ? "A research run references this report ID but conflicts with its complete Phase 5 evidence."
      : null,
    selection.evaluationOutcome &&
    evidence.data.researchRuns.some(
      (run) =>
        run.phase5_evaluation.evaluation_outcome_id === selection.evaluationOutcome!.outcome_id &&
        !evaluationOutcomeMatchesResearchRun(selection.evaluationOutcome!, run),
    )
      ? "A research run references this blocked outcome ID but conflicts with its fail-closed evidence."
      : null,
  ].filter((message): message is string => Boolean(message));
  const branchLinks = lineageBranchLinks(evidence.data, selection, identifiers);

  return (
    <section aria-labelledby="lineage-heading">
      <div className="boundaryNotice">
        <strong>At most two interactions</strong>
        <p>
          The result link opened its exact evidence. When multiple immutable descendants exist,
          every branch is listed for one direct follow-up; no first match is chosen automatically.
        </p>
      </div>
      <div className="sectionHeading">
        <h2 id="lineage-heading">Source-to-audit evidence chain</h2>
        <p>Only exact embedded identifiers are joined. No audit row or later-phase record is invented.</p>
      </div>

      {branchLinks.length > 0 ? (
        <section className="workflowPanel" aria-labelledby="lineage-branches-heading">
          <div className="panelHeader">
            <div>
              <span className="cardKicker">Exact immutable descendants</span>
              <h3 id="lineage-branches-heading">Choose a source-to-terminal branch</h3>
            </div>
            <p>Every exact branch is listed; none is selected by array order or inferred identity.</p>
          </div>
          <ul className="evidenceList">
            {branchLinks.map((branch) => (
              <li key={branch.href}>
                <Link className="lineageLink" href={branch.href}>
                  {branch.label}
                </Link>
                <span>{branch.description}</span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <ol className="timelineList lineageTimeline">
        {selection.card ? (
          <SourceEvidence
            card={selection.card}
            key={selection.card.card_id}
            mapping={selection.mapping}
          />
        ) : null}
        {selection.mapping ? <MappingEvidence mapping={selection.mapping} /> : null}
        {ancestorConflicts.map((message) => (
          <li key={message}>
            <div>
              <strong>Fail-closed ancestor conflict</strong>
              <p>{message} No unrelated ancestor is shown.</p>
            </div>
          </li>
        ))}
        {snapshotEvidence.snapshots.map((snapshot) => (
          <li key={snapshot.snapshot_id}>
            <div>
              <strong>Point-in-time snapshot</strong>
              <p>
                {snapshot.manifest.payload.request.capability} / {snapshot.quality_status}
              </p>
              <p className="mono">Snapshot ID: {snapshot.snapshot_id}</p>
              <HashValue>{snapshot.snapshot_sha256}</HashValue>
              <ArtifactDisclosure artifact={snapshot} label="snapshot artifact" />
            </div>
          </li>
        ))}
        {snapshotEvidence.conflict ? (
          <li>
            <div>
              <strong>Fail-closed snapshot conflict</strong>
              <p>
                A run-owned snapshot identifier or hash did not match the loaded artifact. No
                mapping-level substitute is shown.
              </p>
            </div>
          </li>
        ) : null}
        {exactEvaluation.conflict ? (
          <li>
            <div>
              <strong>Fail-closed evaluation conflict</strong>
              <p>
                The run&apos;s embedded evaluation identifier or hash did not match a loaded artifact.
                No same-mapping substitute is shown.
              </p>
            </div>
          </li>
        ) : null}
        {evaluation ? (
          <li>
            <div>
              <strong>Configuration, code, and evaluation</strong>
              <p>{evaluation.promotion_state}</p>
              <p className="mono">Evaluation artifact ID: {evaluation.artifact_id}</p>
              <p className="mono">Code version: {evaluation.code_version_git_sha}</p>
              <HashValue>{evaluation.artifact_sha256}</HashValue>
              <ArtifactDisclosure artifact={evaluation} label="evaluation artifact" />
            </div>
          </li>
        ) : blockedOutcome ? (
          <li>
            <div>
              <strong>Fail-closed evaluation terminal</strong>
              <p>{blockedOutcome.promotion_state}</p>
              <p>{blockedOutcome.sanitized_message}</p>
              <HashValue>{blockedOutcome.outcome_sha256}</HashValue>
              <ArtifactDisclosure artifact={blockedOutcome} label="blocked evaluation artifact" />
            </div>
          </li>
        ) : null}
        {selection.researchRun ? (
          <li>
            <div>
              <strong>Research artifact</strong>
              <p>
                {selection.researchRun.status} / {selection.researchRun.phase5_evaluation.promotion_state}
              </p>
              <p className="mono">Run ID: {selection.researchRun.run_id}</p>
              <p className="mono">Configuration: {selection.researchRun.configuration_id}</p>
              <p className="mono">Code version: {selection.researchRun.code_version_git_sha}</p>
              <HashValue>{selection.researchRun.artifact_sha256}</HashValue>
              <details className="evidenceDisclosure">
                <summary>Inspect Phase 6 source-reproduction audit</summary>
                <pre tabIndex={0}>
                  {JSON.stringify(selection.researchRun.source_reproduction_audit, null, 2)}
                </pre>
              </details>
              <ArtifactDisclosure artifact={selection.researchRun} label="research artifact" />
            </div>
          </li>
        ) : null}
        {selection.assessment ? (
          <li>
            <div>
              <strong>Approval assessment and historical evidence timeline</strong>
              <p>{selection.assessment.outcome}</p>
              <p className="mono">Assessment ID: {selection.assessment.assessment_id}</p>
              <HashValue>{selection.assessment.artifact_sha256}</HashValue>
              {timelineFailure ? (
                <HistoricalEvidenceTimeline
                  assessmentId={selection.assessment.assessment_id}
                  failure={timelineFailure}
                  timeline={undefined}
                />
              ) : timeline ? (
                <ArtifactDisclosure artifact={timeline} label="server evidence timeline" />
              ) : (
                <p className="statePanel" data-tone="critical">
                  Timeline evidence was not resolved; no date or currentness state is inferred.
                </p>
              )}
              <ArtifactDisclosure
                artifact={selection.assessment}
                defaultOpen
                label="complete immutable domain audit artifact"
              />
            </div>
          </li>
        ) : null}
        {missingBoundRevocations.length > 0 ? (
          <li>
            <div>
              <strong>Fail-closed revocation conflict</strong>
              <p>
                {missingBoundRevocations.length} assessment-bound revocation identifier(s) were
                unavailable. No replacement was inferred.
              </p>
            </div>
          </li>
        ) : null}
        {lineageRevocations.map((revocation) => {
          const boundAtAssessment = Boolean(
            selection.assessment?.revocation_ids.includes(revocation.revocation_id),
          );
          return (
            <li key={revocation.revocation_id}>
              <div>
                <strong>Authorization revocation</strong>
                <p>
                  {boundAtAssessment
                    ? "This revocation ID is bound in the assessment artifact."
                    : "This append-only revocation shares the exact authorization reference."}{" "}
                  Immutable revocation evidence remains blocking.
                </p>
                <p className="mono">Revocation ID: {revocation.revocation_id}</p>
                <HashValue>{revocation.artifact_sha256}</HashValue>
                <ArtifactDisclosure
                  artifact={safeRevocationArtifact(revocation)}
                  defaultOpen
                  label="hash-bound domain audit evidence (restricted fields referenced by hash)"
                />
              </div>
            </li>
          );
        })}
        <li>
          <div>
            <strong>Fail-closed terminal state</strong>
            <p>
              {terminalMessage(
                selection,
                branchLinks,
                lineageRevocations,
                ancestorConflicts.length > 0 || missingBoundRevocations.length > 0,
              )}
            </p>
          </div>
        </li>
      </ol>
    </section>
  );
}
