# Phase 2 local Qwen review record

## Review boundary

- Model: locally installed Ollama `qwen3:14b-q4_K_M`.
- Role: untrusted secondary architecture/schema/code reviewer only.
- Allowed review topics: requirement coverage, lineage, migrations, idempotency, validation, tests,
  and Phase 2 safety boundaries.
- Excluded: signals, recommendations, position sizes, execution instructions, backtesting decisions,
  paper orders, brokers, personalized advice, and every live capability.
- Repository authority: `AGENTS.md`, the Phase 2 handoff, frozen schema decisions, source code, and
  executable tests always overrode model output.

The review was split into bounded schema, extractor/memo, persistence/workflow, and migration/API
slices so evidence fit the local model context. Raw model prose is not a product artifact and was not
copied into an extraction, card, memo, or strategy record.

## Accepted recommendation

The Phase 2 closure review was bounded to schema semantics, intake validation, database ownership,
contract generation, documentation, and adversarial tests. Qwen agreed that the six card fields need
field-specific evidence models and enum vocabularies at both the public Pydantic boundary and the
untrusted extraction-draft boundary. It also supported rejecting blank supplied text without trimming
accepted content, requiring URL-only clients to omit `raw_text`, making `supplied_at_utc` a
database-generated output, and exercising the same rules through OpenAPI and generated TypeScript.
Repository models, migrations, generated artifacts, and executable tests independently confirmed
each accepted point.

Qwen noted that substring matching could confuse a term embedded in a larger word. Repository review
confirmed a reproducible example: `optional` could match the `option` vocabulary item. The extractor
now uses token/phrase boundaries, with
`test_closed_vocabulary_matching_does_not_classify_substrings` as its executable acceptance test.

Earlier planning recommendations for explicit validators, immutable foreign-key lineage, idempotent
fingerprints, deterministic memos, OpenAPI/TypeScript parity, and adversarial tests were retained only
after they were independently verified against repository requirements.

A final bounded review asked only whether URL-only versions could reach the queue and whether reuse of
an ingest idempotency key could silently change trust metadata. Qwen identified both inconsistencies.
Repository inspection confirmed them in `IdeaRepository.create_extraction_request` and
`IdeaRepository._assert_ingest_matches`. The implementation now rejects URL-only extraction before a
request/job exists and rejects reuse of a key when content state, retrieval time, verification method,
or exact corroborating source-version IDs differ.

The preserved acceptance evidence is executable:

- `test_url_only_source_cannot_create_manual_extraction_request` and
  `test_url_only_manual_extraction_request_fails_closed` cover the no-text boundary;
- `test_idempotency_key_rejects_changed_immutable_provenance` covers trust metadata;
- the opt-in PostgreSQL round trip repeats the corroboration collision through the real repository.

The review assumed that URL-only provenance remains a valid stored artifact and that corroboration ID
ordering is not semantic. A first intake's database-generated `supplied_at_utc` remains authoritative
on an exact retry; an idempotency retry does not rewrite it.

## Rejected or corrected recommendations

- In the final bounded closure review, Qwen ignored the Phase 2-only instruction and proposed a
  Phase 3 mapper, `0003` persistence, and Phase 3 acceptance implementation. The entire proposal was
  rejected. It also invented an `ambiguous` testability status and generic reason labels that are not
  in the Phase 2 contract. No Phase 3 code or schema was added, and the response supplied no concrete
  Phase 2 defect supported by the provided artifacts.
- Qwen treated HTTP(S) URL-format validation as potentially outside the immediate closure. That was
  rejected because the existing Phase 2 provenance contract already requires absolute HTTP(S) URLs.
- Qwen's illustrative cross-field enum values were vague and did not match the repository canon.
  They were not copied. The named Pydantic enums, generated schemas, and fixture-backed tests are the
  authority.
- Qwen questioned whether downgrade/re-upgrade evidence belonged with schema closure. That concern
  was rejected because reversible Phase 2 persistence is an explicit acceptance requirement; no
  Phase 3 behavior is introduced by testing the `0002` cycle.
- A Qwen finding labeled existing out-of-range UTF-8 rejection as a high-severity defect even though
  its proposed test asserted the current behavior. No change was made.
- It treated multi-label classification as an unexplained defect. Phase 2 intentionally emits
  `ambiguous` plus exact source claims rather than selecting a family; deterministic family mapping is
  Phase 3.
- It suggested a fallback paraphrase for absent classifications. The current explicit `null` is the
  fail-closed behavior and was retained.
- It repeatedly reported missing source-row locking, parent validation, official-source validation,
  LLM provenance checks, null-priority enforcement, and append-only mutation checks. Each was already
  present in repository code or the `0002_phase2` migration; targeted tests/static checks preserve
  those controls.
- Free-form rewritten action rules, mutable `updated_at` status records, provider-specific data
  requirements, automatic coupling of social corroboration to structural testability, generic CRUD,
  and root-level file layouts were rejected as conflicting with the governing Phase 2 contract.
- HFT and uncorroborated social inputs are persisted and blocked/classified as required; they are not
  discarded with request errors.
- The final Qwen response proposed treating a changed payload under the same idempotency key as a
  separate record. That was rejected: one key cannot name two immutable provenance records, so the
  repository raises `IdempotencyConflictError` instead.

## Independent review fixes beyond Qwen

Repository review additionally tightened exact claim-reference validation, social gate invariants,
UTC normalization, verification-method enums, HTTP(S)-only provenance URLs, idempotency-key reuse,
concurrent extraction request recovery, ordered append-only events, card/request/memo lineage checks,
and non-overlapping sentence segmentation. A final independent audit also found that content-based
social-risk detection disagreed with the card validator and that `HFT`, `sub-minute`, and `scalping`
spellings escaped the high-infrastructure-risk gate. Those findings were not supplied by Qwen; the
predicate and vocabulary were corrected and now have focused regression tests. These changes are
covered by host-side tests and the full Compose verifier.

The closure audit additionally normalized the Phase 3 handoff vocabulary to exactly
`BUILD_RESEARCH`, `DEFER`, `DEFER_READ_ONLY`, `REJECT_PLATFORM`, and `NON_TESTABLE`, with fail-closed
precedence and all required handoff sections. This is documentation-only; no mapper or Phase 3 code
was added.

## Unresolved risks and blockers

- Phase 2 cannot independently retrieve or authenticate an official URL because network retrieval is
  explicitly out of scope. A real source remains unverified unless a persisted manual attestation is
  supplied; synthetic fixtures use the explicit synthetic verification method.

The final Docker Compose verifier passed against real PostgreSQL and Redis. It proved a finished RQ
job with terminal extraction events, enabled append-only triggers plus rejected update/delete/truncate
operations on all eight Phase 2 tables, downgrade to `0001_phase1`, and re-upgrade to
`0002_phase2`. An initial verifier probe used plain `TRUNCATE` on a foreign-key parent and was rejected
by PostgreSQL before its trigger could fire; the acceptance probe now uses schema-qualified
`TRUNCATE ... CASCADE` in the isolated disposable database and requires the exact trigger error.
