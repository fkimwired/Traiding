# T-007 - SEC EDGAR policy, currentness, and schema-qualification plan

## Purpose and governing boundary

This document is the T-007 documentation supplement to the completed Phase 27 metadata intake. It
defines a fail-closed plan for a later, separately authorized phase to revalidate current SEC EDGAR
policy and qualify the exact Phase 26 SEC delivery and point-in-time contract.

It is not legal advice, a policy grant, verified evidence, acquisition authority, schema
qualification, point-in-time qualification, research admission, or execution authority. The
repository owner stated on 2026-07-23 that they reviewed and documented their review of the SEC
pages. T-007 records that statement as operator context only. It does not ingest that external
review, store the supplied screenshot, set `sec.review_performed=true`, create an evidence record,
or claim independent verification.

The truthful canonical Phase 27 state remains:

```text
outcome: BLOCKED
determination: COMPOSITION_RIGHTS_ENTITLEMENT_EVIDENCE_MISSING
verified_evidence_recorded: false
```

## T-007 audit envelope

| Field | Value |
|---|---|
| Governing boundary | T-007 documentation only |
| Plan artifact ID | `ecdd57a5-a500-5cac-bd74-74848f6997b7` |
| Plan configuration SHA-256 | `cb3f9beae309cb346a76b626cb2c292189c6c4edb877d7f85f889c01b4201afd` |
| Baseline git SHA | `1d8aa00f80fdd60b2b5ab3d431448de28a872c17` |
| Baseline tree SHA | `d5e8ba303c03525aaa4cee65ddd090c858c2d2d6` |
| First-party pages retrieved for this plan | `2026-07-23T16:48:51.375Z` |
| Random seed | `0` - no stochastic work |
| Trial count | `0` - no experiment, retrieval trial, or data trial |
| Provider data requested or persisted | `false` |
| Schema captured or qualified | `false` |
| Research or execution authorized | `false` |
| Only permitted execution mode | `paper` |
| Live path | absent and categorically prohibited |

The plan configuration hash covers the task ID, documentation-only boundary, five accepted source
codes, exact Phase 26 product, two exact delivery IDs, and all twelve Phase 27 SEC requirement
codes. It is the SHA-256 of the following JSON serialized as UTF-8 with keys sorted
lexicographically and separators `,` and `:` with no insignificant whitespace:

```json
{
  "accepted_source_codes": [
    "SEC_PRIVACY_AND_DISSEMINATION",
    "SEC_WEBMASTER_REUSE_FAQ",
    "SEC_EDGAR_APIS",
    "SEC_DEVELOPER_RESOURCES",
    "SEC_ACCESSING_EDGAR"
  ],
  "boundary": "T-007_DOCUMENTATION_ONLY",
  "delivery_ids": [
    "SEC_EDGAR_NIGHTLY_SUBMISSIONS_BULK_ARCHIVE",
    "SEC_EDGAR_NIGHTLY_COMPANYFACTS_BULK_ARCHIVE"
  ],
  "phase26_product_id": "SEC_EDGAR_SUBMISSIONS_AND_XBRL_DATA_APIS",
  "requirement_codes": [
    "OFFICIAL_FIRST_PARTY_POLICY_PROVENANCE",
    "EXACT_SELECTED_BULK_PRODUCTS_AND_SURFACES",
    "POLICY_VERSION_EFFECTIVE_DATE_AND_CURRENTNESS",
    "FAIR_ACCESS_AGGREGATE_RATE",
    "DECLARED_USER_AGENT_AND_ADMIN_CONTACT",
    "AUTOMATED_BULK_RETRIEVAL",
    "PERSISTENT_STORAGE_BACKUPS_AND_INTERNAL_USE",
    "NORMALIZATION_DERIVED_OUTPUTS_AND_NON_DISPLAY_USE",
    "ATTRIBUTION_DISPLAY_AND_REDISTRIBUTION",
    "RETENTION_REVOCATION_AND_CHANGE_MONITORING",
    "CITATION_SEAL_LOGO_AND_NONAFFILIATION",
    "THIRD_PARTY_AND_CONTENT_SPECIFIC_EXCEPTIONS"
  ],
  "schema_version": "t007-sec-edgar-qualification-plan-v1",
  "task_id": "T-007"
}
```

The plan artifact ID is UUIDv5 in the standard URL namespace over
`fable5:t007-sec-edgar-qualification-plan:<configuration-sha256>`. Both values are recomputed by
the T-007 ownership verifier. They are plan provenance only and are not Phase 27 provider-evidence
identifiers or hashes.

## What this plan does NOT do

T-007 performs no bulk download, API request, archive request, archive persistence, provider-data
capture, schema capture, policy-evidence ingestion, credential loading, account inspection,
adapter implementation, database change, generated-contract change, research, strategy,
performance calculation, recommendation, risk mutation, order operation, execution, or live
operation.

Nothing in this document instructs an operator or agent to fetch `submissions.zip`,
`companyfacts.zip`, an index, a filing, or an API response under T-007. Every future retrieval,
transient parse, schema snapshot, or data persistence step described below is explicitly
**NOT AUTHORIZED BY T-007** and requires a separately reviewed phase.

A page view, screenshot, API key, successful response, free access, or operator attestation is not
verified policy evidence and is not schema or point-in-time qualification. No current finding in
this plan changes the Phase 27 canonical artifact.

## Closed Phase 26 product and delivery scope

The exact selected product is:

```text
SEC_EDGAR_SUBMISSIONS_AND_XBRL_DATA_APIS
```

The only selected Phase 26 delivery IDs are:

```text
SEC_EDGAR_NIGHTLY_SUBMISSIONS_BULK_ARCHIVE
SEC_EDGAR_NIGHTLY_COMPANYFACTS_BULK_ARCHIVE
```

They correspond to the SEC-published nightly bulk files below. The URLs are identification and
citation only; they are not T-007 retrieval instructions.

| Phase 26 delivery | Exact identified bulk file | First-party support |
|---|---|---|
| `SEC_EDGAR_NIGHTLY_SUBMISSIONS_BULK_ARCHIVE` | `https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip` | The SEC describes the linked submissions archive as public filing history from the Submissions API and says bulk archives are recompiled nightly. [S3, retrieved 2026-07-23 UTC] |
| `SEC_EDGAR_NIGHTLY_COMPANYFACTS_BULK_ARCHIVE` | `https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip` | The SEC describes the companyfacts archive as containing data from the XBRL Frames and Company Facts APIs and says bulk archives are recompiled nightly. [S3, retrieved 2026-07-23 UTC] |

Daily, full, and quarterly EDGAR indexes are later point-in-time dependencies. They are not a third
selected Phase 26 delivery. A later finding that another archive, API, feed, raw filing, or index
must become a delivery is a composition-scope change and must stop for a new decision; it may not be
silently added by schema qualification.

## Accepted first-party policy source registry

Only the five exact Phase 18/27 source bindings below may populate the Phase 27 SEC policy intake.
The initial T-007 plan observations retained the accepted URL, title, publisher, and publisher
update date. That initial review did not store page bodies or compute new body hashes, so it does
not claim byte identity with Phase 18. A separately supplied historical working note is described
below without promoting its reported metadata to evidence.

| Ref | Phase 27 source code | Exact title and URL | Accepted Phase 18 source SHA-256 | Publisher-stated currentness date | T-007 retrieval and disposition |
|---|---|---|---|---|---|
| S1 | `SEC_PRIVACY_AND_DISSEMINATION` | [SEC.gov \| Privacy Information](https://www.sec.gov/about/privacy-information), U.S. Securities and Exchange Commission | `0984a4c7658634d6403eb1ec4f36b8626977732bda583349d3021fb9335a9c0c` | Last reviewed or updated `2023-11-29` | Retrieved `2026-07-23 UTC`; no URL/title/publisher-date delta observed; content hash not captured |
| S2 | `SEC_WEBMASTER_REUSE_FAQ` | [SEC.gov \| Webmaster Frequently Asked Questions](https://www.sec.gov/about/webmaster-frequently-asked-questions), U.S. Securities and Exchange Commission | `71960ed3481d9dfdb5bf05bb01f1c99d9a33eb1fd210c1d4f78e66c4da72a425` | Last reviewed or updated `2024-08-23` | Retrieved `2026-07-23 UTC`; no URL/title/publisher-date delta observed; content hash not captured |
| S3 | `SEC_EDGAR_APIS` | [SEC.gov \| EDGAR Application Programming Interfaces (APIs)](https://www.sec.gov/search-filings/edgar-application-programming-interfaces), U.S. Securities and Exchange Commission | `dbf6644b4a354746fae64019244f8290e3e2d93f20ade509b5b09612bb84f098` | Last reviewed or updated `2025-04-08` | Retrieved `2026-07-23 UTC`; no URL/title/publisher-date delta observed; content hash not captured |
| S4 | `SEC_DEVELOPER_RESOURCES` | [SEC.gov \| Developer Resources](https://www.sec.gov/about/developer-resources), U.S. Securities and Exchange Commission | `83513446683733fc70b93accbcdd9edac2be72f55ae5a01ba3d0688e6cd8b684` | Last reviewed or updated `2025-03-10` | Retrieved `2026-07-23 UTC`; no URL/title/publisher-date delta observed; content hash not captured |
| S5 | `SEC_ACCESSING_EDGAR` | [SEC.gov \| Accessing EDGAR Data](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data), U.S. Securities and Exchange Commission | `b4826d9200b61932d49804a10c5252bcc066675385db3069a5b3401378fb4442` | Last reviewed or updated `2024-06-26` | Retrieved `2026-07-23 UTC`; no URL/title/publisher-date delta observed; content hash not captured |

The exact `SECPolicyDocumentInput.official_title` literals are:

```text
SEC.gov | Privacy Information
SEC.gov | Webmaster Frequently Asked Questions
SEC.gov | EDGAR Application Programming Interfaces (APIs)
SEC.gov | Developer Resources
SEC.gov | Accessing EDGAR Data
```

The accepted Phase 18 source SHA-256 values bind the source catalog row, not current remote page
bytes. A later evidence record still needs its own transiently calculated `content_sha256`,
`policy_version`, provenance hash, delta, independent-verification status, and revalidation horizon.

## Operator-supplied historical assistant retrieval metadata (2026-07-23 18:12 UTC)

An operator-supplied working note reports that a separate assistant session re-accessed the same
five first-party policy pages on 2026-07-23 at approximately 18:12 UTC. The reported observations
are distinct from the initial T-007 plan review recorded above at
`2026-07-23T16:48:51.375Z`. The repository does not contain immutable response provenance that
independently proves the reported historical requests, so this subsection treats the working note
as unverified historical context.

This subsection records **sanitized retrieval metadata**: the reported per-source UTC timestamps
and HTTP statuses. No response body or page-content hash is persisted here, and no
`sec.policy_documents[]` record is instantiated. The reported observations are **not** independent
verification, do not create an evidence record, do not set the SEC review-performed flag, and do
not change the Phase 27 canonical artifact or its blocked, no-evidence result. The working note
reports read-only HTTPS access with a declared administrative-contact User-Agent; raw contact
details and contact-derived identifiers are intentionally excluded. The reported timestamps are
approximately 1.8 to 2.0 seconds apart, below the stated 10-requests-per-second guideline.

| Ref | Phase 27 source code | Reported historical retrieval timestamp (UTC) | Reported HTTP |
|---|---|---|---|
| S1 | `SEC_PRIVACY_AND_DISSEMINATION` | `2026-07-23T18:12:10.935359Z` | 200 |
| S2 | `SEC_WEBMASTER_REUSE_FAQ` | `2026-07-23T18:12:12.746169Z` | 200 |
| S3 | `SEC_EDGAR_APIS` | `2026-07-23T18:12:14.577776Z` | 200 |
| S4 | `SEC_DEVELOPER_RESOURCES` | `2026-07-23T18:12:16.395838Z` | 200 |
| S5 | `SEC_ACCESSING_EDGAR` | `2026-07-23T18:12:18.425454Z` | 200 |

The working note reportedly calculated per-source content hashes, but neither those hashes nor raw
response bodies are recorded here. Raw response bodies must never be persisted or committed.
Sanitized hashes may be recorded only by a separately authorized evidence workflow with the exact
Phase 27 provenance and independent-verification fields; unverified working-note hashes must not be
promoted as evidence. Only such a later authorized workflow could instantiate these timestamps as
`sec.policy_documents[].retrieved_at_utc`. Their presence here is not verification and grants no
acquisition, schema, point-in-time, research, order, execution, or live authority.

## Current first-party findings to revalidate

These are bounded summaries of the cited pages as observed on the T-007 retrieval date. They are
inputs to a future review, not a legal conclusion or current Phase 27 evidence.

1. The SEC says government-created SEC.gov content and EDGAR public-filing content are free to
   access and reuse, while identifying examples of content with separate restrictions. [S2,
   retrieved 2026-07-23 UTC]
2. The SEC says information presented on SEC.gov is public information that may be copied or
   further distributed, asks users to consider citation, prohibits misuse of SEC seals/logos, and
   restricts uses that imply SEC affiliation or approval. [S1, retrieved 2026-07-23 UTC]
3. The EDGAR data APIs require no authentication or API key. The APIs update through the day, and
   the two identified bulk archives are republished nightly at approximately 3:00 a.m. ET. [S3,
   retrieved 2026-07-23 UTC]
4. Current fair-access guidance limits aggregate access to no more than 10 requests per second,
   regardless of machine count; asks for efficient, needed-only retrieval; permits rate limiting or
   blocking; and disallows unclassified automated tools. [S1, S4, S5, retrieved 2026-07-23 UTC]
5. Automated requests must declare a descriptive User-Agent containing an organization/company
   identity and administrative contact. The example shown by the SEC is illustrative and must not
   be copied as an operational identity. [S5, retrieved 2026-07-23 UTC]
6. `data.sec.gov` does not support CORS, so any later authorized integration must remain server-side
   and within the typed provider-adapter boundary. [S3, retrieved 2026-07-23 UTC]
7. EDGAR daily indexes are built nightly; full and quarterly indexes are rebuilt weekly to
   incorporate some post-acceptance corrections and deletions. [S5, retrieved 2026-07-23 UTC]
8. The EDGAR filer system records an acceptance date and time, but the SEC says there is no
   timestamp that identifies when filing content first became available on SEC.gov; typical
   availability lag is not guaranteed. [S2, retrieved 2026-07-23 UTC]

The pages do not, by their mere presence, independently resolve every selected-archive question
about storage, backups, normalized outputs, non-display use, retention, all third-party content, or
revision-safe point-in-time sufficiency. Any row without exact, independently reviewed support
remains `MISSING`, `FAIL`, or controlled `CONDITIONAL`; it must not be inferred into `PASS`.

## Required Phase 27 policy-document fields

For a later authorized evidence workflow, each of the five sources must map to one
`SECPolicyDocumentInput` under `Phase27EvidenceIntake.sec.policy_documents[]` with exactly:

| Evidence requirement | Exact Phase 27 field |
|---|---|
| Immutable sanitized evidence identity | `sec.policy_documents[].evidence_id` |
| Closed source binding | `source_code`, `source_url`, `official_title`, `publisher` |
| Publisher and review timing | `publisher_stated_date`, `retrieved_at_utc`, `effective_at_utc`, `revalidation_due_at_utc` |
| Version and clause binding | `policy_version`, `clause_locator` |
| Integrity and Phase 18 lineage | `content_sha256`, `phase18_source_sha256`, `provenance_locator_sha256` |
| Sanitized interpretation | `normalized_finding`, `normalized_delta` |
| Independent review | `independent_verification_status`, `independent_verifier_identity_sha256` |

The group additionally uses:

```text
sec.schema_version
sec.review_performed
sec.requirement_answers[]
sec.mutual_consistency_status
sec.mutual_consistency_evidence_ids
```

Each `sec.requirement_answers[]` row must use the existing `RequirementAnswerInput` fields:
`code`, `state`, `normalized_finding`, `normalized_value_sha256`, `evidence_ids`, and `conditions`.
`normalized_value_sha256` must be the existing Phase 27 normalized-finding domain hash; it is not a
free-form evidence or document hash.

The composition-level review envelope also retains the existing
`Phase27EvidenceIntake.evaluated_at_utc`, `recorded_at_utc`,
`composition_consistency_status`, and `composition_consistency_evidence_ids` fields.
No parallel SEC evidence or requirement fields may be invented.

T-007 does not populate any of these fields. In particular, the user's review statement is not
converted into `review_performed=true`, and the screenshot is not assigned an `evidence_id`.

## Exact Phase 27 requirement-to-source mapping

Every row below must be independently decided in a later authorized evidence workflow. Structural
acceptance of metadata is not proof that the finding is correct.

| Phase 27 requirement code | Exact canonical requirement | Primary accepted sources and exact intake mapping | T-007 disposition |
|---|---|---|---|
| `OFFICIAL_FIRST_PARTY_POLICY_PROVENANCE` | Policy evidence is from an exact official first-party SEC HTTPS source. | S1-S5; `sec.policy_documents[].source_code`, `source_url`, `official_title`, `publisher`, `phase18_source_sha256`; `sec.requirement_answers[code=OFFICIAL_FIRST_PARTY_POLICY_PROVENANCE]` | `UNVERIFIED`; no evidence rows created |
| `EXACT_SELECTED_BULK_PRODUCTS_AND_SURFACES` | The review covers nightly submissions and companyfacts bulk archives. | S3; exact Phase 26 delivery IDs; `sec.requirement_answers[code=EXACT_SELECTED_BULK_PRODUCTS_AND_SURFACES]` | `UNVERIFIED`; scope documented only |
| `POLICY_VERSION_EFFECTIVE_DATE_AND_CURRENTNESS` | Policy version, effective date, retrieval time, and revalidation horizon are explicit. | S1-S5; `publisher_stated_date`, `retrieved_at_utc`, `effective_at_utc`, `revalidation_due_at_utc`, `policy_version`, `normalized_delta`; matching requirement row | `UNVERIFIED`; no current content hashes or independent review |
| `FAIR_ACCESS_AGGREGATE_RATE` | The current aggregate fair-access rate is recorded. | S1, S4, S5; matching requirement row with evidence IDs | Current page text observed; still `UNVERIFIED` as Phase 27 evidence |
| `DECLARED_USER_AGENT_AND_ADMIN_CONTACT` | The declared User-Agent and administrative-contact requirement is recorded. | S5; matching requirement row; operational contact remains environment/config outside evidence | Current page text observed; no operational identity or evidence created |
| `AUTOMATED_BULK_RETRIEVAL` | Automated bulk retrieval constraints are recorded. | S1, S3, S4, S5; matching requirement row | `UNVERIFIED`; no request mechanism authorized |
| `PERSISTENT_STORAGE_BACKUPS_AND_INTERNAL_USE` | Storage, backups, and internal-use treatment are recorded. | S1, S2 plus exact-content review; matching requirement row | `UNVERIFIED`; general reuse language is not silently expanded into an exact-scope pass |
| `NORMALIZATION_DERIVED_OUTPUTS_AND_NON_DISPLAY_USE` | Normalization, derived outputs, and non-display treatment are recorded. | S1, S2 plus exact-content review; matching requirement row | `UNVERIFIED`; no derived-use authority inferred |
| `ATTRIBUTION_DISPLAY_AND_REDISTRIBUTION` | Attribution, display, and redistribution treatment are recorded. | S1, S2; matching requirement row | `UNVERIFIED`; no redistribution or publication authorized |
| `RETENTION_REVOCATION_AND_CHANGE_MONITORING` | Retention, revocation, currentness, and policy-change monitoring are recorded. | S1, S4, S5; timestamps/delta fields; matching requirement row | `UNVERIFIED`; internal revalidation controls below are proposals, not SEC terms |
| `CITATION_SEAL_LOGO_AND_NONAFFILIATION` | SEC citation, seal and logo restrictions, and non-affiliation language are recorded. | S1; matching requirement row | Current page text observed; still `UNVERIFIED` as Phase 27 evidence |
| `THIRD_PARTY_AND_CONTENT_SPECIFIC_EXCEPTIONS` | Third-party and content-specific exceptions for the selected archives are resolved. | S1, S2 plus exact archive/content review; matching requirement row | `UNVERIFIED`; examples on SEC.gov do not prove the selected archives exception-free |

A future positive SEC substate requires all twelve rows satisfied, every cited evidence ID present,
all policy records current and independently verified, and
`sec.mutual_consistency_status=VERIFIED` with nonempty verified
`sec.mutual_consistency_evidence_ids`. It still grants no acquisition, schema, point-in-time,
research, order, execution, or live authority.

## Proposed future fair-access controls

The following are conservative Fable5 controls for a later separately authorized phase. They are
not claims that the SEC mandates the stricter internal values, and they are not active under T-007.

1. Re-open and independently verify all five accepted policy pages immediately before the first
   request in any authorized observation window.
2. Fail closed on any URL, title, publisher date, clause, content hash, rate guidance, declared
   identity requirement, archive path, or exception delta.
3. Use one server-side worker, concurrency `1`, and an internal ceiling of `5` aggregate SEC
   requests per second, leaving headroom below the currently stated `10` requests/second maximum.
4. Use only an operator-configured descriptive User-Agent and administrative contact. Never place
   the contact value in logs, evidence, fixtures, generated contracts, or commits.
5. Permit only exact allowlisted first-party HTTPS hosts and paths. Reject redirects, generic
   request methods, crawling, directory discovery, and any unclassified automation.
6. Request only the exact bytes needed by the separately authorized scope. A rate-limit response,
   block, policy drift, unexpected content type, oversized response, or archive-integrity failure
   stops the run without a retry loop.
7. Revalidate again at each new UTC acquisition date and no later than 24 hours after the prior
   review. This 24-hour value is a proposed internal maximum, not an SEC-published policy duration.

Any later authorization must restate the exact methods, request count, URLs, size limits, time
window, storage destination, retention, cleanup, and evidence path. T-007 supplies none of those
operational permissions.

## Future schema-freeze method - NOT AUTHORIZED BY T-007

A separately authorized schema-qualification phase may evaluate only the two selected archive
identities. Its schema gate should use this deterministic sequence:

1. **Prerequisite closure.** Require exact accepted repository lineage, current independently
   verified Phase 27 evidence for all applicable SEC rows, an explicit acquisition/schema
   authorization, and an empty data-quarantine target. Stop if CRSP/RTDSM/SEC aggregate
   prerequisites or the new phase's authority are incomplete.
2. **Exact capture identity.** Bind each response to the exact Phase 26 delivery ID and allowlisted
   URL. Record sanitized response metadata, retrieval UTC, byte count, exact archive SHA-256, and
   immutable capture ID. Do not commit response headers, bodies, archive bytes, or member values.
3. **Archive safety.** Before extraction, reject path traversal, absolute paths, duplicate member
   paths, encrypted members, unsupported compression, excessive nesting, member-count overflow,
   per-member overflow, aggregate expanded-size overflow, or compression-ratio abuse.
4. **Deterministic member manifest.** Sort normalized member paths by UTF-8 byte order and hash a
   manifest of path, compressed size, expanded size, member SHA-256, and media classification.
   Member values, names that contain personal identifiers, and raw snippets must not enter the
   repository artifact.
5. **Whole-archive structural inventory.** Validate every JSON member, not a favorable sample.
   Record only structural paths, JSON types, required/optional occurrence counts, array/object
   cardinality bounds, nullability, and format/domain classifications. Reject duplicate JSON keys,
   non-finite numbers, invalid Unicode, unbounded depth, or nondeterministic parsing.
6. **Canonical JSON Schema.** Produce separate deterministic JSON Schema Draft 2020-12 snapshots for
   the submissions and companyfacts archives. Canonicalize key order and numeric/text
   representation, then record schema IDs, schema SHA-256 values, generator version, and source
   archive/manifests. Do not embed provider records or example values.
7. **Existing schema binding.** Bind each accepted schema through the existing
   `SchemaBinding.dataset_schema_id`, `SchemaBinding.dataset_schema_version`,
   `AdapterProfile.schema_bindings`, `ObservationEnvelopeDraft.dataset_id`, `product_id`,
   `dataset_schema_id`, and `dataset_schema_version` fields. Keep the archive schema and the
   separately hash-bound raw-to-normalized mapping distinct.
8. **Cross-member conformance.** Revalidate every member against the derived candidate schema. Any
   conflicting type, unexplained missing required field, unexpected root shape, or unclassified
   extension blocks qualification. Sampling can be diagnostic only and cannot pass the gate.
9. **Selected-capability sufficiency.** Prove that the exact fields required for
   `as_reported_fundamentals` and revision lineage exist and can be joined without a new provider
   surface. Schema stability alone is insufficient.
10. **Drift policy.** A new archive SHA may be normal; a schema SHA, field-domain, archive-layout, or
   semantics change creates a new candidate schema version and blocks automatic use until reviewed.
   Emit the existing blocking `DataQualityCode.SCHEMA_DRIFT` where applicable. Never widen a schema,
   coerce a changed type, zero-fill a missing value, drop an unknown field, or use a fallback parser
   to preserve a prior pass.
11. **Evidence closeout.** Produce a sanitized artifact with configuration hash, capture/snapshot
    IDs, archive and schema hashes, git SHA, deterministic UTC times, seed/trial count `0/0`, exact
    command results, and explicit false authority fields for research, strategy, execution, orders,
    and live capability.

Archive access, transient extraction, data persistence, and JSON Schema generation remain prohibited
until that later phase is expressly authorized.

## Point-in-time and availability qualification

The existing Phase 4 contract keeps event/acceptance, availability, and retrieval distinct:

```text
AsReportedFundamentalPayload.filing_accepted_at
ObservationEnvelopeDraft.event_time
ObservationEnvelopeDraft.available_at
ObservationEnvelopeDraft.retrieved_at
ObservationEnvelopeDraft.valid_from
ObservationEnvelopeDraft.valid_to
ObservationEnvelopeDraft.revision_id
ObservationEnvelopeDraft.vintage_id
```

`AsReportedFundamentalPayload` also requires `official_document_id`, `as_reported=true`,
`amendment_sequence`, and optional `restates_revision_id`. The existing validator rejects a
fundamental whose `filing_accepted_at` is later than its observation `available_at`, and the Phase 5
`FundamentalRevisionEvidence`/L02 leakage gate keeps `accepted_at_utc`,
`available_at_utc`, revision trace, and decision time separate.

The future SEC qualification must therefore apply these semantics:

1. Map the source `<ACCEPTANCE-DATETIME>` only to
   `AsReportedFundamentalPayload.filing_accepted_at` after an independently verified timezone and
   UTC-normalization rule.
2. Do not set `available_at` earlier than `filing_accepted_at`.
3. Permit `available_at == filing_accepted_at` only if a later qualification proves a unique
   accession-level join, authoritative timezone/DST interpretation, and that the acceptance value
   is a valid public-dissemination availability boundary for the intended point-in-time rule.
4. Otherwise do not assume `available_at == filing_accepted_at`. The accepted SEC page says no timestamp
   identifies first SEC.gov availability and that observed lag is not guaranteed. [S2, retrieved
   2026-07-23 UTC]
5. For a nightly archive observation, use the earliest independently evidenced time at which the
   exact archive bytes were available to the authorized process. If no trustworthy publication
   time exists, use the first successful bounded retrieval time, never an estimated 3:00 a.m.
   schedule.
6. Set `retrieved_at` to the actual retrieval time and enforce
   `retrieved_at >= available_at >= filing_accepted_at`.
7. If only a source date is available, use the existing `AvailabilityPrecision.DATE` and
   `AvailabilityConvention.DATE_ONLY_NEXT_DAY`; do not invent an intraday timestamp.
8. Preserve each accession/amendment/revision separately. Never replace an earlier observation with
   the latest Company Facts value or use a later correction at an earlier decision time.
9. Reconcile daily/full index behavior and post-acceptance corrections as PIT dependencies without
   silently adding them as Phase 26 deliveries.
10. Prove that every training/evaluation row satisfies
   `source.available_at <= decision_time_utc` and carries an unbroken revision trace.

The exact timezone semantics of the SEC acceptance header, the presence and casing of an
acceptance field in each selected bulk archive, and the archive-level public-availability evidence
are `UNVERIFIED` under T-007. They must be resolved by first-party technical documentation and the
later schema capture. Guessing EST/EDT conversion, substituting filing date, or subtracting a
typical lag is a lookahead defect.

## Exact delivery sufficiency gate

The later qualification must answer all of the following from the two exact selected archives and
permitted PIT dependencies:

- Can each fundamental fact be bound to an immutable accession/document identity?
- Can the original filing acceptance time be recovered and normalized without guessing?
- Can amendments and later restatements be ordered without overwriting the earlier state?
- Can `available_at` be evidenced conservatively for the exact bytes used?
- Can a fact be reconstructed as known at an arbitrary historical decision time?
- Can missingness, taxonomy changes, units, periods, dimensions, and custom extensions be
  represented without silent coercion?
- Can post-acceptance corrections and deletions be detected and retained as revision history?
- Can the required Phase 4 and Phase 5 audit fields be populated without another provider surface?

The append-only revision proof must use the existing `source_record_id`, `logical_record_key_sha256`,
`revision_id`, `vintage_id`, `raw_payload_sha256`, `normalized_content_sha256`,
`ObservationRevisionDraft.revision_sequence`,
`ObservationRevisionDraft.predecessor_revision_record_id`,
`AsReportedFundamentalPayload.amendment_sequence`, and
`AsReportedFundamentalPayload.restates_revision_id` fields. A later correction cannot inherit an
earlier availability time unless independent evidence establishes that exact timing.

Any `NO`, `UNVERIFIED`, ambiguous, sampled-only, or scope-mismatched answer keeps
`EXACT_DELIVERY_AND_SCHEMA_VERSIONS` and
`DECLARED_PIT_COVERAGE_CALENDAR_AVAILABILITY_MISSINGNESS` blocked. The process must not add a raw
filing feed, API call, index delivery, commercial product, or other source to make the selected
composition appear sufficient.

## Fail-closed decision table

| Condition | Required disposition |
|---|---|
| One accepted policy page is missing, stale, changed, unverifiable, or outside the exact source binding | `BLOCKED`; no request |
| The user's review exists but no independently verified Phase 27 evidence records exist | Keep `verified_evidence_recorded=false` |
| A page loads successfully or an archive URL is publicly reachable | No rights, acquisition, schema, PIT, or research authority |
| A policy row is structurally valid but its normalized finding is unsupported | `FAIL` or `MISSING`; never promote metadata presence |
| The SEC substate is complete but CRSP or RTDSM evidence remains missing | Composition remains `BLOCKED` |
| Policy evidence is complete but separate acquisition/schema authorization is absent | No request and no archive capture |
| One archive, member, or schema violates a bound or cannot be parsed deterministically | Reject the entire qualification attempt |
| Only a sample conforms | `BLOCKED`; exact whole-archive conformance is unproven |
| Acceptance time exists but public availability cannot be evidenced | `BLOCKED`; do not equate acceptance with availability |
| Latest values cannot be separated from historical as-reported revisions | `BLOCKED`; lookahead risk |
| Exact selected archives require another delivery to satisfy the capability | Stop for a new composition decision |
| A schema passes | This grants no research, strategy, performance, risk, order, execution, or live authority |
| Any step would introduce credentials, PII, a generic network client, a mutation, an order path, or live capability | Stop immediately |

## Required future evidence artifacts

A later policy-revalidation artifact must contain only sanitized Phase 27 metadata:

- all five `SECPolicyDocumentInput` records and twelve exact requirement answers;
- configuration/policy hash, immutable evidence IDs and content/provenance hashes;
- accepted Phase 18/26/27 lineage and current git SHA;
- retrieval, effective, expiry/revalidation, evaluation, and recording UTC timestamps;
- independent-verifier identity hash and mutual-consistency evidence IDs;
- random seed `0` and trial count `0`; and
- explicit false authority fields for acquisition, schema/PIT qualification, research, strategy,
  performance, risk mutation, order submission, execution, and live capability.

A separately authorized schema/PIT artifact must additionally bind exact capture IDs, archive
SHA-256 values, member-manifest hashes, schema IDs/hashes, coverage results, availability rules,
revision-trace results, command outcomes, cleanup status, and the same audit envelope. It must not
contain raw agreements, credentials, contacts, response headers/bodies, archive bytes, filing
values, personal identifiers, account numbers, tokens, or raw schema examples.

## T-007 acceptance checklist

- [x] Exact Phase 26 SEC product named.
- [x] Both exact selected nightly bulk delivery IDs named.
- [x] Daily/full/quarterly indexes identified only as later PIT dependencies.
- [x] All five accepted Phase 18/27 first-party source rows cited with `2026-07-23 UTC` retrieval.
- [x] Current fair-access, declared User-Agent, archive cadence, CORS, reuse, citation, and
  exception topics recorded without treating them as verified evidence.
- [x] All twelve exact Phase 27 SEC requirement codes mapped to existing Pydantic fields.
- [x] Exact `SECPolicyDocumentInput`, `SECPolicyRevalidationIntake`, and
  `RequirementAnswerInput` field mappings recorded.
- [x] Deterministic schema-freeze method specified without performing schema capture.
- [x] Acceptance time kept distinct from conservative observed availability.
- [x] Revision, correction, missingness, whole-archive, and no-lookahead gates specified.
- [x] "What this plan does NOT do" names download, persistence, and qualification.
- [x] T-007 records and authorizes no bulk, archive, filing, or EDGAR data-API request and creates
  no request/download implementation path, archive, schema, evidence intake, credential, research,
  order, execution, or live path. Only unverified historical metadata for five reported read-only
  policy-page GETs is documented.

Repository acceptance commands for this documentation unit are:

```powershell
git diff --check
.\.venv\Scripts\python.exe -m pytest `
  services\data\tests\test_phase27_contracts.py `
  services\data\tests\test_phase27_package.py `
  services\data\tests\test_phase27_security.py `
  tests\test_phase27_portable.py `
  tests\test_phase27_static.py `
  tests\test_repository_policy.py -q
.\.venv\Scripts\python.exe scripts\verify_family_a_rights_and_entitlement_evidence_intake.py `
  --artifact docs\PHASE_27_FAMILY_A_RIGHTS_AND_ENTITLEMENT_EVIDENCE_INTAKE.json
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m mypy
.\.venv\Scripts\python.exe scripts\verify_phase1.py --static-only --phase 27
```

The Phase 26 command historically listed for T-007 in `DEVELOPMENT.md` predates the accepted Phase
27 and T-009 lineage and is not the active post-baseline closure gate. On this accepted lineage it
fails an inherited browser-coverage dispatch check unrelated to T-007. The Phase 27 command above
is the applicable inherited static closure and preserves the original Phase 27 and T-009
identities and allowlists. T-007 does not edit `DEVELOPMENT.md`.

## Stop condition

Stop T-007 after this document and its documentation/static review. Do not ingest the user's review
as evidence, change the Phase 27 canonical artifact, retrieve an archive, inspect archive contents,
capture a schema, implement a transport or adapter, persist data, begin T-010, or begin Phase 28.

Policy evidence acquisition, archive acquisition, schema qualification, point-in-time
qualification, and research admission each require separate authorization and independent
acceptance. Real-money trading and live capability remain categorically prohibited.
