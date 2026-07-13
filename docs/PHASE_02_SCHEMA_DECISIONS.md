# Phase 2 schema decisions

## Scope

This document freezes the lossless source-intake and `TradingIdeaCard` extraction semantics for
Phase 2. It does not define a strategy, signal, verdict, backtest, risk approval, position, order, or
paper-execution state. Those remain absent.

The governing requirements are `AGENTS.md`, `docs/handoffs/PHASE_02.md`,
`docs/PRODUCT_BRIEF.md`, `docs/STRATEGY_CANON.md`, and `docs/RESEARCH_SUPPLEMENT.md`.

## Source and evidence boundary

- A `SourceVersion` is immutable. It stores the exact supplied UTF-8 bytes without newline or Unicode
  normalization, their SHA-256 digest, provenance, supplied/retrieved timestamps, and its parent
  version. A correction appends a version. Supplied text must contain at least one non-whitespace
  character; validation does not trim or otherwise rewrite accepted text.
- `supplied_at_utc` is output-only and database-owned. Intake and correction schemas reject it as an
  extra client field, the repository never binds it, and PostgreSQL supplies its UTC value.
- A URL is provenance only. Phase 2 never retrieves it. URL-only intake is persisted without an
  extraction request; `raw_text` must be omitted rather than sent as JSON null. An explicit extraction
  attempt fails with HTTP 422 and creates no request or job.
- Source text is deterministically segmented into zero-based, half-open UTF-8 byte spans. An
  extraction adapter may return only segment IDs, classifications, and enums. It may not return quote
  text, action-rule prose, a side, quantity, position size, order type, recommendation, or instruction.
- The server validates every segment against the immutable content hash and reconstructs exact
  quotations. `action_rule` is an evidence state plus claim IDs only; it has no free-text value.
- `paraphrased_claim` is rendered from a fixed neutral template. It identifies an unverified source
  claim and never turns it into advice or an instruction.

## Explicit unknown semantics

Evidence-bearing fields use one of:

- `source_supported`: a normalized classification/value and one or more claim IDs are present;
- `not_stated`: the value is explicitly null (or the list is empty) and no evidence is cited;
- `ambiguous`: the normalized value is null/empty and one or more claims show the ambiguity;
- `not_applicable`: the value is null/empty and no evidence is cited.

The sentinel string `unknown` is not a field value. Missing scalar evidence serializes as JSON
`null`; missing list evidence serializes as `[]`. All response keys remain present.

The public schema uses six field-specific evidence contracts. Scalar fields are
`AssetClassEvidence`, `ForecastHorizonEvidence`, `SignalFamilyEvidence`, and
`ExecutionStyleEvidence`; list fields are `RequiredDataEvidence` and `RiskAssumptionsEvidence`.
Each contract owns a distinct closed enum, so a value valid for one field is rejected by every other
field. The untrusted extractor-draft boundary mirrors the same separation. The resulting card schema
version is `phase2-trading-idea-card-v2`.

## Testability and corroboration

- `testability_status=testable` only when both `action_rule` and `forecast_horizon` are
  `source_supported`. Otherwise it is `non_testable` with machine-readable missing/ambiguous reason
  codes.
- `testability_score` is evidence completeness only: one half for a source-supported action rule and
  one half for a source-supported horizon. It is not performance, quality, or promotion probability.
  The method is `phase2-testability-v1`.
- `research_priority_score` is always explicitly null in Phase 2. No priority rubric is invented.
- Social provenance or source-supported social-media language always carries
  `social_manipulation_risk`. Testability remains independent: a social claim can be structurally
  testable while still blocked from contribution.
- Social content is not blocked by corroboration only when it links to an exact immutable source
  version classified as official and carrying a non-LLM verification method. A bare URL is
  insufficient. Otherwise `contribution_status=blocked_official_corroboration_required`.
- High-frequency, sub-minute, scalping, or order-book language is persisted and classified
  `infra_risk=high`; it is not rejected at intake and creates no downstream scaffold.

## Versioning and idempotency

Every extraction stores extractor kind/id/version, schema version, configuration hash, and—only for
an LLM extractor—model and prompt identifiers/hashes. Rule-based/mock extractors store the LLM fields
as null rather than fabricating model provenance.

The extraction fingerprint is the SHA-256 of the canonical tuple containing the immutable source
version and content hash plus all extractor/model/prompt/schema/config versions. An identical retry
returns the existing extraction/card; a source correction or version/config change creates a new
immutable extraction. Reusing an intake idempotency key with changed content state, retrieval time,
authority verification, or exact corroborating versions is a conflict rather than a silent retry or
new record. The first source version's database-generated supplied timestamp remains authoritative.

## Review disposition and remaining assumption

Local Qwen review was treated as untrusted input. Its recommendations for field-specific schemas,
explicit nonblank validation, database-generated timestamps, lineage, idempotency, and adversarial
tests were retained only after repository verification. Its vague cross-field enum examples and
suggestion that URL syntax validation might be outside this closure were rejected; the repository's
closed enums and existing HTTP(S)-only provenance rule remain authoritative. Free-form rewritten
action rules, mutable timestamps, provider-specific data requirements, automatic
social/non-testable coupling, and unsupported priority scores were also rejected.

Phase 2 can record supplied authority evidence but cannot independently retrieve or authenticate an
official URL. Real sources therefore default to unverified unless a non-LLM verification method is
persisted. Synthetic fixtures may use the explicit `synthetic_fixture` verification method.
