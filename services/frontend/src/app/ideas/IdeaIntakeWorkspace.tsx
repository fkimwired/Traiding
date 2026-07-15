"use client";

import {
  sourceAuthorities,
  type components,
  userIntakeSourceTypes,
} from "@fable5/contracts";
import { type FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";

import { type ApiFailure, type ApiResult, fable5Api, type SourceIntakeRequest } from "../../lib/api";
import {
  emptyEvidenceIndex,
  mappingMatchesCard,
  useEvidenceIndex,
} from "../../lib/evidence-index";
import { useEvidenceRetryFocus } from "../../lib/use-evidence-retry-focus";
import { TradingIdeaCardView } from "./TradingIdeaCardView";

type ExtractionRequestRecord = components["schemas"]["ExtractionRequestRecord"];
type SourceCreateResponse = components["schemas"]["SourceCreateResponse"];
type SourceVersion = components["schemas"]["SourceVersion"];
type TradingIdeaCard = components["schemas"]["TradingIdeaCard"];
type MappingWithRationale = components["schemas"]["MappingWithRationale"];
type SourceAuthority = components["schemas"]["SourceAuthority"];
type SourceType = components["schemas"]["SourceType"];

type SubmissionState =
  | { status: "idle" }
  | { status: "working"; message: string; request: SourceIntakeRequest }
  | { status: "error"; error: ApiFailure; request: SourceIntakeRequest }
  | {
      status: "success";
      card: TradingIdeaCard;
      mapping: MappingWithRationale;
      request: SourceIntakeRequest;
    };

function failed<T>(error: ApiFailure): ApiResult<T> {
  return { ok: false, error };
}

function workflowFailure(message: string, retrySafe: boolean): ApiFailure {
  return { kind: "unavailable", message, retrySafe };
}

function lineageConflict(artifactLabel: string): ApiFailure {
  return {
    kind: "conflict",
    message: `The returned ${artifactLabel} conflicts with the exact submitted source or immutable provenance chain. No downstream evidence was inferred.`,
    retrySafe: false,
  };
}

function sameNullableValue(
  left: string | null | undefined,
  right: string | null | undefined,
) {
  return (left ?? null) === (right ?? null);
}

function sameOrderedValues(left: readonly string[] = [], right: readonly string[] = []) {
  return left.length === right.length && left.every((value, index) => value === right[index]);
}

function sourceResponseMatchesRequest(
  response: SourceCreateResponse,
  request: SourceIntakeRequest,
) {
  const sourceVersion = response.source_version;
  const expectedContentState =
    request.raw_text === undefined
      ? "url_only_unretrieved"
      : request.retrieved_at_utc == null
        ? "supplied_text"
        : "retrieved_text";

  return (
    response.source.source_id === sourceVersion.source_id &&
    sourceVersion.source_type === request.source_type &&
    sourceVersion.source_authority === request.source_authority &&
    sourceVersion.raw_text === (request.raw_text ?? null) &&
    sourceVersion.source_url === (request.source_url ?? null) &&
    sourceVersion.content_state === expectedContentState &&
    sourceVersion.retrieved_at_utc === (request.retrieved_at_utc ?? null) &&
    sourceVersion.authority_verification_method ===
      (request.authority_verification_method ?? null) &&
    sameOrderedValues(
      sourceVersion.official_corroboration_source_version_ids,
      request.official_corroboration_source_version_ids,
    )
  );
}

function extractionMatchesSourceVersion(
  extraction: ExtractionRequestRecord,
  sourceVersion: SourceVersion,
) {
  return extraction.source_version_id === sourceVersion.source_version_id;
}

function extractionMatchesInitial(
  candidate: ExtractionRequestRecord,
  initial: ExtractionRequestRecord,
) {
  return (
    candidate.extraction_request_id === initial.extraction_request_id &&
    candidate.source_version_id === initial.source_version_id &&
    candidate.request_fingerprint === initial.request_fingerprint &&
    candidate.rq_job_id === initial.rq_job_id &&
    candidate.requested_at_utc === initial.requested_at_utc &&
    candidate.extraction_config_sha256 === initial.extraction_config_sha256 &&
    candidate.extraction_schema_version === initial.extraction_schema_version &&
    candidate.extractor_kind === initial.extractor_kind &&
    candidate.extractor_id === initial.extractor_id &&
    candidate.extractor_version === initial.extractor_version &&
    sameNullableValue(candidate.extraction_model_id, initial.extraction_model_id) &&
    sameNullableValue(candidate.extraction_model_revision, initial.extraction_model_revision) &&
    sameNullableValue(candidate.extraction_prompt_sha256, initial.extraction_prompt_sha256) &&
    sameNullableValue(candidate.extraction_prompt_version, initial.extraction_prompt_version)
  );
}

function cardMatchesProvenanceChain(
  card: TradingIdeaCard,
  response: SourceCreateResponse,
  extraction: ExtractionRequestRecord,
) {
  const sourceVersion = response.source_version;
  return (
    card.source_id === response.source.source_id &&
    card.source_version_id === sourceVersion.source_version_id &&
    card.source_version === sourceVersion.source_version &&
    card.source_authority === sourceVersion.source_authority &&
    card.source_url === sourceVersion.source_url &&
    card.raw_text === sourceVersion.raw_text &&
    card.synthetic_fixture ===
      !userIntakeSourceTypes.some((sourceType) => sourceType === sourceVersion.source_type) &&
    sameOrderedValues(
      card.official_corroboration_source_version_ids,
      sourceVersion.official_corroboration_source_version_ids,
    ) &&
    card.extraction_request_id === extraction.extraction_request_id &&
    card.source_version_id === extraction.source_version_id &&
    card.extraction_config_sha256 === extraction.extraction_config_sha256 &&
    card.extraction_schema_version === extraction.extraction_schema_version &&
    card.extractor_kind === extraction.extractor_kind &&
    card.extractor_id === extraction.extractor_id &&
    card.extractor_version === extraction.extractor_version &&
    sameNullableValue(card.extraction_model_id, extraction.extraction_model_id) &&
    sameNullableValue(card.extraction_model_revision, extraction.extraction_model_revision) &&
    sameNullableValue(card.extraction_prompt_sha256, extraction.extraction_prompt_sha256) &&
    sameNullableValue(card.extraction_prompt_version, extraction.extraction_prompt_version)
  );
}

function waitFor(delayMs: number, signal: AbortSignal) {
  return new Promise<void>((resolve, reject) => {
    const timeout = window.setTimeout(resolve, delayMs);
    signal.addEventListener(
      "abort",
      () => {
        window.clearTimeout(timeout);
        reject(new DOMException("The request was cancelled.", "AbortError"));
      },
      { once: true },
    );
  });
}

async function pollExtraction(
  initial: ExtractionRequestRecord,
  signal: AbortSignal,
  delayMs: number,
  onState: (message: string) => void,
): Promise<ApiResult<ExtractionRequestRecord>> {
  let record = initial;

  for (let attempt = 0; attempt < 25; attempt += 1) {
    onState(`Extraction state: ${record.latest_event}. Waiting for immutable result...`);
    if (record.latest_event === "succeeded") {
      return { ok: true, data: record, retrySafe: true, status: 200 };
    }
    if (record.latest_event === "failed" || record.latest_event === "enqueue_failed") {
      return failed(
        workflowFailure(
          `Extraction stopped in the server-owned ${record.latest_event} state. No card was inferred.`,
          true,
        ),
      );
    }

    try {
      await waitFor(delayMs, signal);
    } catch {
      return failed({
        kind: "aborted",
        message: "The extraction request was cancelled.",
        retrySafe: true,
      });
    }

    const next = await fable5Api.getExtraction(record.extraction_request_id, signal);
    if (!next.ok) return next;
    if (!extractionMatchesInitial(next.data, initial)) {
      return failed(lineageConflict("extraction record"));
    }
    record = next.data;
  }

  return failed(
    workflowFailure(
      "Extraction is still pending. Retry reuses the exact source request and idempotency key.",
      true,
    ),
  );
}

async function findExtractedCard(
  extractionRequestId: string,
  signal: AbortSignal,
  delayMs: number,
): Promise<ApiResult<TradingIdeaCard>> {
  for (let attempt = 0; attempt < 12; attempt += 1) {
    const cards = await fable5Api.listCards(signal);
    if (!cards.ok) return cards;
    const card = cards.data.find(
      (candidate) => candidate.extraction_request_id === extractionRequestId,
    );
    if (card) return { ok: true, data: card, retrySafe: true, status: 200 };

    if (attempt < 11) {
      try {
        await waitFor(delayMs, signal);
      } catch {
        return failed({
          kind: "aborted",
          message: "The card lookup was cancelled.",
          retrySafe: true,
        });
      }
    }
  }

  return failed(
    workflowFailure(
      "Extraction completed, but its normalized TradingIdeaCard is not available yet.",
      true,
    ),
  );
}

export function IdeaIntakeWorkspace({
  idempotencyKeyFactory = () => globalThis.crypto.randomUUID(),
  pollDelayMs = 250,
}: {
  idempotencyKeyFactory?: () => string;
  pollDelayMs?: number;
}) {
  const evidenceState = useEvidenceIndex();
  const {
    retry: retryEvidenceLoad,
    setRetryButton: setEvidenceRetryButton,
  } = useEvidenceRetryFocus(evidenceState.status, evidenceState.reload);
  const [rawText, setRawText] = useState("");
  const [sourceType, setSourceType] = useState<SourceType | "">("");
  const [sourceAuthority, setSourceAuthority] = useState<SourceAuthority | "">("");
  const [submission, setSubmission] = useState<SubmissionState>({ status: "idle" });
  const submissionController = useRef<AbortController | null>(null);

  useEffect(() => () => submissionController.current?.abort(), []);

  const runSubmission = useCallback(
    async (request: SourceIntakeRequest) => {
      submissionController.current?.abort();
      const controller = new AbortController();
      submissionController.current = controller;

      const announce = (message: string) =>
        setSubmission({ message, request, status: "working" });

      announce("Preserving the exact source text and immutable provenance...");
      const sourceResult = await fable5Api.createSource(request, controller.signal);
      if (!sourceResult.ok) {
        if (sourceResult.error.kind !== "aborted") {
          setSubmission({ error: sourceResult.error, request, status: "error" });
        }
        return;
      }

      if (!sourceResponseMatchesRequest(sourceResult.data, request)) {
        setSubmission({
          error: lineageConflict("source record"),
          request,
          status: "error",
        });
        return;
      }

      let extraction = sourceResult.data.extraction;
      if (!extraction) {
        announce("Requesting extraction from the persisted source version...");
        const extractionResult = await fable5Api.createExtraction(
          sourceResult.data.source_version.source_version_id,
          controller.signal,
        );
        if (!extractionResult.ok) {
          if (extractionResult.error.kind !== "aborted") {
            setSubmission({ error: extractionResult.error, request, status: "error" });
          }
          return;
        }
        extraction = extractionResult.data;
      }

      if (!extractionMatchesSourceVersion(extraction, sourceResult.data.source_version)) {
        setSubmission({
          error: lineageConflict("extraction record"),
          request,
          status: "error",
        });
        return;
      }

      const completedExtraction = await pollExtraction(
        extraction,
        controller.signal,
        pollDelayMs,
        announce,
      );
      if (!completedExtraction.ok) {
        if (completedExtraction.error.kind !== "aborted") {
          setSubmission({ error: completedExtraction.error, request, status: "error" });
        }
        return;
      }

      announce("Loading the normalized TradingIdeaCard from persisted API records...");
      const cardResult = await findExtractedCard(
        completedExtraction.data.extraction_request_id,
        controller.signal,
        pollDelayMs,
      );
      if (!cardResult.ok) {
        if (cardResult.error.kind !== "aborted") {
          setSubmission({ error: cardResult.error, request, status: "error" });
        }
        return;
      }

      if (
        !cardMatchesProvenanceChain(
          cardResult.data,
          sourceResult.data,
          completedExtraction.data,
        )
      ) {
        setSubmission({
          error: lineageConflict("TradingIdeaCard"),
          request,
          status: "error",
        });
        return;
      }

      announce("Applying the existing deterministic canon mapping...");
      const mappingResult = await fable5Api.createMapping(cardResult.data.card_id, controller.signal);
      if (!mappingResult.ok) {
        if (mappingResult.error.kind !== "aborted") {
          setSubmission({ error: mappingResult.error, request, status: "error" });
        }
        return;
      }

      if (
        !mappingMatchesCard(mappingResult.data, cardResult.data) ||
        mappingResult.data.mapping.extraction_request_fingerprint !==
          completedExtraction.data.request_fingerprint ||
        mappingResult.data.mapping.source_content_sha256 !==
          sourceResult.data.source_version.content_sha256
      ) {
        setSubmission({
          error: lineageConflict("mapping record"),
          request,
          status: "error",
        });
        return;
      }

      setSubmission({
        card: cardResult.data,
        mapping: mappingResult.data,
        request,
        status: "success",
      });
      evidenceState.reload();
    },
    [evidenceState, pollDelayMs],
  );

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!sourceType || !sourceAuthority) return;
    if (rawText.trim().length === 0) {
      const request: SourceIntakeRequest = {
        ingest_idempotency_key: idempotencyKeyFactory(),
        raw_text: rawText,
        source_authority: sourceAuthority,
        source_type: sourceType,
      };
      setSubmission({
        error: {
          kind: "validation",
          message: "Enter or paste exact source text before requesting extraction.",
          retrySafe: false,
        },
        request,
        status: "error",
      });
      return;
    }

    const request: SourceIntakeRequest = {
      ingest_idempotency_key: idempotencyKeyFactory(),
      raw_text: rawText,
      source_authority: sourceAuthority,
      source_type: sourceType,
    };
    void runSubmission(request);
  }

  const evidenceIndex = evidenceState.status === "success" ? evidenceState.data : emptyEvidenceIndex();
  const cards = useMemo(() => {
    if (submission.status !== "success") return evidenceIndex.cards;
    return evidenceIndex.cards.some(({ card_id }) => card_id === submission.card.card_id)
      ? evidenceIndex.cards
      : [submission.card, ...evidenceIndex.cards];
  }, [evidenceIndex.cards, submission]);

  return (
    <div
      className="workflowStack"
      data-visual-corpus={
        evidenceState.status === "success" &&
        evidenceState.data.cards.length > 0 &&
        evidenceState.data.cards.every((card) => card.synthetic_fixture)
          ? "synthetic"
          : "unverified"
      }
    >
      <section className="workflowPanel" aria-labelledby="idea-intake-form-heading">
        <div className="panelHeader">
          <div>
            <span className="cardKicker">Exact source intake</span>
            <h2 id="idea-intake-form-heading">Enter or paste an idea for extraction</h2>
          </div>
          <p>
            The client submits source text and provenance only. Extraction and mapping values remain
            server-owned; no signal, recommendation, allocation, or instruction is accepted here.
          </p>
        </div>

        <form className="formGrid" onSubmit={submit}>
          <div className="fieldGroup" data-span="full">
            <label htmlFor="idea-source-text">Exact source text</label>
            <textarea
              id="idea-source-text"
              name="raw_text"
              onChange={(event) => setRawText(event.currentTarget.value)}
              required
              rows={7}
              value={rawText}
            />
            <p className="fieldHint">Whitespace and punctuation are sent exactly as supplied.</p>
          </div>
          <div className="fieldGroup">
            <label htmlFor="idea-source-type">Source type</label>
              <select
                id="idea-source-type"
                name="source_type"
                onChange={(event) => setSourceType(event.currentTarget.value as SourceType)}
                value={sourceType}
                required
              >
                <option value="">Choose a server-defined source type</option>
                {userIntakeSourceTypes.map((value) => (
                  <option key={value} value={value}>
                    {value.replaceAll("_", " ")}
                  </option>
                ))}
              </select>
          </div>
          <div className="fieldGroup">
            <label htmlFor="idea-source-authority">Source authority</label>
              <select
                id="idea-source-authority"
                name="source_authority"
                onChange={(event) => setSourceAuthority(event.currentTarget.value as SourceAuthority)}
                value={sourceAuthority}
                required
              >
                <option value="">Choose a server-defined authority</option>
                {sourceAuthorities.map((value) => (
                  <option key={value} value={value}>
                    {value}
                  </option>
                ))}
              </select>
          </div>
          <div className="formActions">
            <button
              className="buttonPrimary"
              disabled={submission.status === "working"}
              type="submit"
            >
              {submission.status === "working" ? "Extracting..." : "Normalize idea"}
            </button>
          </div>
        </form>

        <div className="workflowAnnouncement" aria-live="polite" aria-atomic="true">
          {submission.status === "idle" ? (
            <p>No source request has been submitted in this session.</p>
          ) : null}
          {submission.status === "working" ? <p role="status">{submission.message}</p> : null}
          {submission.status === "error" ? (
            <div className="statePanel" data-tone="critical" role="alert">
              <strong>{submission.error.kind}</strong>
              <p>{submission.error.message}</p>
              {submission.error.retrySafe ? (
                <button
                  className="buttonSecondary"
                  type="button"
                  onClick={() => void runSubmission(submission.request)}
                >
                  Retry exact request
                </button>
              ) : null}
            </div>
          ) : null}
          {submission.status === "success" ? (
            <p role="status">
              Source preserved, extraction completed, and card {submission.card.card_id} loaded.
            </p>
          ) : null}
        </div>
      </section>

      <section className="workflowPanel" aria-labelledby="persisted-cards-heading">
        <div className="panelHeader">
          <div>
            <span className="cardKicker">Persisted Phase 2-7 evidence</span>
            <h2 id="persisted-cards-heading">Normalized idea cards</h2>
          </div>
        </div>

        {evidenceState.status === "loading" ? (
          <p className="statePanel" role="status">
            {evidenceState.message}
          </p>
        ) : null}
        {evidenceState.status === "empty" && submission.status !== "success" ? (
          <p className="statePanel" role="status" aria-live="polite">
            {evidenceState.message}
          </p>
        ) : null}
        {evidenceState.status === "error" ? (
          <div className="statePanel" data-tone="critical" role="alert">
            <p>{evidenceState.error.message}</p>
            {evidenceState.retrySafe ? (
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

        {cards.length > 0 ? (
          <div className="strategyGrid">
            {cards.map((card) => (
              <TradingIdeaCardView
                card={card}
                evidenceIndex={evidenceIndex}
                key={card.card_id}
                mappingOverride={
                  submission.status === "success" &&
                  mappingMatchesCard(submission.mapping, card)
                    ? submission.mapping
                    : undefined
                }
              />
            ))}
          </div>
        ) : null}
      </section>
    </div>
  );
}
