# Phase 8 product-workflow and presentation decisions

## Boundary

Phase 8 completes the Idea Intake, Research Lab, simulated Paper Trading status, and
Risk / Compliance workflows over immutable Phase 2-7 evidence. It introduces no
strategy calculation, signal, allocation, position, executable paper intent, order,
fill, broker, credential, real-performance source, or live path. The interface never
turns a research result or historical approval artifact into execution readiness.

FastAPI/Pydantic OpenAPI remains the sole client-contract authority. Frontend code may
join records only through server-issued immutable identifiers. It does not reproduce
gate logic, thresholds, hashes, timestamps, verdicts, currentness, or outcomes.
Runtime form options are generated from OpenAPI enum schemas alongside the generated
TypeScript contract; they are not maintained as a second handwritten list. The runtime
generator excludes the server-reserved `synthetic_fixture` source type from user intake
and fails contract generation if that reserved enum identity is missing or duplicated.
There is no migration 0008, audit writer, or backfill. Migrations 0001 through 0007 and
their persistence semantics remain unchanged. Phase 8 does not expose unrestricted
audit payloads, licensed or secret data, reviewer rationale, or unnecessary reviewer
identity.

## Audit semantics

For this phase, an immutable audit entry is the complete hash-bound domain artifact
returned by an existing GET-by-id operation. Evaluation reports, research artifacts,
approval assessments, and authorization revocations are displayed with their exact
artifact identifiers, hashes, server timestamps, code/configuration lineage, and
embedded ancestors.

For governance results, the audit entries are specifically the complete
`ApprovalAssessmentArtifact` and `AuthorizationRevocationArtifact`. The additive
evidence timeline is presentation evidence only; it does not replace, relabel, or
recompute either immutable governance artifact.

`PreparedPipelineReproductionAudit` retains its narrow Phase 6 meaning. It is labeled
only as a source-reproduction audit. The Phase 1 `research_audit_events` table has no
authoritative per-result application relation and is not exposed, inferred, seeded,
backfilled, or relabeled for Phase 8.

When processing blocks before a later artifact exists, the interface displays the
typed terminal state and the last real immutable ancestor. It never manufactures a
later-phase record.

## Additive evidence-timeline read contract

Phase 8 adds exactly one GET-only endpoint:

`GET /v1/approval-assessments/{assessment_id}/evidence-timeline`

The response contains only the assessment creation time and the server-owned evidence
identifiers, hashes, and historical timestamps needed to present:

- assessment creation time;
- approval-policy valid-from and expiry time;
- approval-scope valid-from and expiry time;
- human-authorization authorized-at, review-at, and expiry time; and
- risk-input observed-at time.

The resolver loads the assessment first, resolves each exact referenced evidence row,
and revalidates its stored canonical hash before returning anything. Missing evidence
uses the existing not-found behavior; conflicting identity or hash evidence uses the
existing conflict behavior. There is no request body and no client-supplied timestamp,
hash, threshold, verdict, or risk result.

The client renders these timestamps verbatim as historical evidence. It never compares
them with a browser clock or recomputes approval, currentness, expiry, revocation, or
execution readiness. The assessment's ordered checks, outcome, reasons, and linked
revocation artifacts remain authoritative.

## Client and state model

One generated-contract client owns every Phase 2-8 read/create request, including the
GET-only evidence timeline. Each request has a 60,000 ms deadline. HTTP and transport
failures map to a closed presentation vocabulary:

- `loading` and `empty` for deterministic read lifecycle;
- `validation` for HTTP 422;
- `conflict` for HTTP 409;
- `not-found` for HTTP 404;
- `unavailable` for transport and non-success responses not classified above; and
- `malformed` when any successful JSON response fails its generated route/status schema.

The client never invents an error DTO for routes whose runtime 404/409 body is not in
OpenAPI. It uses status, a sanitized generic message, and whether a request is safe to
retry. Source-intake retries reuse one stable idempotency key.

Every successful JSON response is structurally checked against route/status schemas
generated directly from the committed OpenAPI document, including each collection
member and nested detail/timeline artifact. A mismatch becomes the deterministic
`malformed` state; there are no handwritten response guards or client-owned schema
semantics. Each operation key also generates its exact success-response TypeScript
type, and the client derives the request method and path template from that same key;
the URL, validator schema, and returned type cannot drift independently.

One narrow wire-compatibility rule is required for immutable Phase 6 Decimal values.
Pydantic's existing response serializer may emit a finite Decimal string in scientific
notation even though its generated fixed-notation string pattern excludes an exponent.
Only when that exact generated Decimal pattern is encountered does the runtime checker
also accept a syntactically valid finite decimal exponent. Other patterns, formats,
types, enums, required fields, and route/status schemas remain strict. This leaves the
existing API, OpenAPI, generated TypeScript, artifact bytes, and hashes unchanged.

The shared evidence index hydrates list results and then their complete GET-by-id
artifacts. It joins cards, mappings, snapshots, evaluations, research runs,
assessments, timelines, and revocations only by immutable IDs present in those
responses. Runtime UUIDs are discovered; fixture filenames and configuration names
are not treated as outcomes. Every hydrated detail must repeat its list summary's
identifier and every summary hash or binding available for that artifact. A shape-valid
wrong detail is a conflict, never a substitute. Source-version and extraction reads in
the lineage route likewise must match the selected card's complete embedded source,
version, authority, request, schema, extractor, model, prompt, and terminal-state
references before their payload is displayed.

All detail and timeline hydration passes through one four-worker queue. Output order
still follows the authoritative list responses, global detail failures stop the load
fail closed, and timeline 404/409/unavailable results remain attached to the exact
assessment while its complete assessment artifact stays visible. Each request has a
composed deadline; a deadline is a sanitized retry-safe unavailable state, while a
caller cancellation remains an aborted request.

## Workflow presentation

### Idea Intake

The form preserves exact submitted text and explicit source provenance. Source type and
authority choices come from generated OpenAPI runtime contracts; `unknown` remains an
explicit ambiguity-preserving choice rather than a client inference. The UI
polls the immutable extraction record, loads the resulting card, and requests the
bodyless deterministic mapping. It never supplies a family, verdict, rationale, or
downstream research state.

Every visible strategy card includes original evidence, normalized interpretation,
required data, structural testability, linked synthetic evaluation, cost-stress gate,
linked Phase 7 status, historical simulated-paper status, and the exact mapping
verdict/reasons. Missing later artifacts are labeled unavailable rather than inferred.

### Research Lab

The only runnable workflow is the existing reference-only deterministic Phase 6
request. Configuration identifiers are shown as identities, not verdicts. Research
cards lead with the exact Phase 5 promotion state and first persisted blocking gate,
then display failed/abandoned attempts, leakage, DSR, PBO, cost stress, snapshot/code
lineage, and the complete immutable report.

In the persisted acceptance corpus, `PASS_RESEARCH` occurs only for configuration
identity `phase6-a-pass-v2`. That prerequisite is never presented as approval, and an
identifier containing `-pass-` is never interpreted as a verdict.

### Simulated Paper Trading

This mode has no create form. It displays historical synthetic assessment and
revocation evidence with an always-visible `SIMULATED` label. It contains no side,
quantity, order ticket, submission control, fill, position, execution-readiness claim,
or performance promise.

### Risk / Compliance

Assessment and revocation creation, when shown, accepts only the exact reference IDs
defined by generated request schemas. Complete artifacts display every Phase 7 check in
server ordinal order. A failing, blocked, or uncomputable check remains visually and
textually dominant over passing checks. A revocation identifier bound into an
assessment but absent from the exact loaded revocation artifacts is itself a visible
fail-closed blocker in the strategy, Risk / Compliance, and simulated-paper views.

## Lineage interaction contract

Every result card links directly to `/lineage` with immutable identifiers. Exact
ancestors are resolved from the selected artifact's own references. If a source,
mapping, evaluation, run, or revocation has multiple exact descendants, the route lists
every branch instead of selecting the first array element; one direct branch link then
opens the complete source, extraction, mapping, point-in-time snapshot, configuration
and code version, evaluation, research, assessment/revocation, and hash-bound domain
artifact chain. Assessment views include both revocation IDs bound when the assessment
formed and later append-only revocations sharing its exact authorization reference,
with those relations labeled separately. Every cross-artifact association checks the
embedded server-owned identifier, SHA-256, mapping version, and mapping-input hash
available for that relation. A same-ID hash or version mismatch stops the chain and is
rendered as a conflict rather than substituted.

When multiple blocked evaluation outcomes share a mapping identity but conflict with
its exact immutable input, version, or snapshot bindings, every outcome remains visibly
blocking and receives its own direct `evaluation_outcome_id` lineage link. No conflicting
outcome is hidden, selected as canonical, or substituted for another.

Synthetic source text is available behind one native disclosure; non-synthetic payload
text remains referenced only. Governance domain-artifact disclosures are expanded on
arrival. A visible result therefore reaches its exact terminal chain in no more than two
interactions without an inferred descendant or manufactured later record.

## Accessibility and visual QA

The shell provides a skip link, named primary navigation, a focusable main landmark,
semantic heading order, visible focus, and a persistent simulation notice. Async and
mutation states use status/alert live regions. Every status includes an icon and text,
so color is never the sole meaning. Retry controls in every mode and the lineage route
restore focus after asynchronous replacement.

Reusable cards and forms preserve 44-pixel minimum controls, explicit labels, native
keyboard behavior, responsive reading order, control boundaries above the non-text
contrast threshold, and a dual-color focus indicator that remains visible over every
status surface.
Reduced-motion media rules remove meaningful animation and smooth scrolling.

Playwright runs against the isolated Compose acceptance corpus. Configuration rejects
non-local browser targets, snapshot updates require an explicit synthetic-corpus guard,
the rendered workflow must declare that every loaded card is synthetic before capture,
and retained browser traces are disabled. Chromium snapshots are
pinned for mobile, tablet, and desktop viewports for all four modes and representative
negative states on both win32 and Linux: 4 modes x 2 states x 3 viewports x 2 platforms,
for exactly 48 PNG baselines (24 per platform). The verifier requires exact filename-set
equality, so both missing and unexpected baselines fail. Dynamic IDs, hashes, and
timestamps are masked only in screenshot comparison; semantic tests still assert their
presence. Screenshot-only styles preserve every masked element's layout box. After a
permitted transport retry, the visual helper removes transient focus and restores the
top viewport before the mode capture; it then scrolls the first blocker into view for
the negative capture. Retry focus restoration remains covered separately by keyboard
and accessibility tests. Browser axe checks cover landmarks, names, contrast, and
structural accessibility. Screenshot inputs are the committed deterministic synthetic
corpus only and contain no licensed or secret source payload.

The Playwright default test timeout is 240,000 ms with framework retries disabled.
Long-running exhaustive lineage checks use explicit 1,200,000 ms and 420,000 ms bounds.
Visual and accessibility wait helpers may perform at most one explicit UI retry, and
only for the exact sanitized retry-safe timeout or API-unreachable alerts. Validation,
conflict, malformed, and not-found states remain terminal, as does a second transport
failure.

Browser QA is deliberately GET/HEAD/OPTIONS-only and snapshots every Phase 1-7 table
before and after the run. Reference-only create forms are exercised in deterministic
component integration tests with mocked generated-contract responses, so browser QA
cannot append acceptance-corpus state merely to prove presentation behavior.

## Known limitations

- All visible data and results are deterministic synthetic QA evidence.
- The evidence timeline is historical and cannot establish current authorization.
- The API has bounded `limit=100` lists and no cursor pagination; the Phase 8 acceptance
  corpus fits that contract.
- The client has a 60-second per-request deadline; on a slower host, one explicit retry
  is available only for retry-safe transport states and the UI otherwise remains fail
  closed.
- The response validator includes a narrow scientific-notation compatibility bridge
  for finite immutable Phase 6 Decimal strings emitted by the pre-existing Pydantic
  serializer; all other generated OpenAPI constraints remain strict.
- There is no production identity provider, provider credential, current market input,
  broker, paper adapter, or execution workflow.
