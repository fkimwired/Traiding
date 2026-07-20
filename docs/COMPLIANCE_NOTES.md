# Compliance and communication notes

These notes are engineering boundaries, not legal advice. Counsel must review any move beyond internal
research/simulation, any customer-facing use, or any market-data distribution.

## Required product language

- Use “research candidate,” “failed,” “blocked,” “deferred,” “rejected,” or “simulated paper status.”
- Every paper surface visibly says **simulated** and **not investment advice**.
- Never say or imply guaranteed returns, proven profit, safe alpha, smart-money certainty, or a live
  fill expectation.
- Explain that backtests and broker paper simulators omit or approximate real execution conditions.
- A green performance metric cannot visually override a leakage, cost, overfitting, approval, or risk
  failure.

## LLM boundary

An LLM may extract, classify, normalize, and summarize text into versioned features. It cannot emit a
trade instruction, position size, personalized recommendation, or buy/sell call, and it cannot be the
sole determinant of a signal. Social content requires official-source corroboration even to
contribute. Persist prompt/model/schema version and trace every derived feature to the source text.

## Data and licensing

- Provider API access does not establish rights to display, store indefinitely, redistribute, or use
  data non-display in a model.
- Record entitlement and use-rights metadata with each snapshot. Do not expose licensed raw news,
  transcripts, or exchange data through the UI/API unless the entitlement permits it.
- Respect SEC fair-access requirements, vendor rate limits, source attribution, correction history,
  privacy terms, and deletion obligations.
- Never ship vendor credentials, paper credentials, or secrets to the browser or repository.
- Phase 12 paper credentials may be loaded only by the explicit local capture command from the two
  paper-specific environment/secret names. Missing or partial pairs fail before transport or database
  construction; API, frontend, CI evidence, logs, errors, and persisted rows remain credential-free.
- Phase 13 candidate credentials and rights attestations may be loaded only by its explicit local
  qualification command. The complete token/current-rights tuple must validate before transport,
  socket, or database construction. CI clears those variables and proves the mock/blocking paths
  while outbound network is denied.
- Phase 14 has no credential or external transport. It may copy only sanitized identity/hash/status
  evidence from an immutable Phase 13 artifact. A Phase 13 rights assertion is not independently
  authenticated ingestion authority and cannot produce positive research eligibility.
- Phase 15 has no credential, transport, database, provider payload, or data-file input. Its portable
  artifact freezes required rights fields and the fact that current independent rights evidence is
  missing; it does not attest that Fable5 has any entitlement or authorize storage, non-display use,
  derived-data use, display, or redistribution.
- Phase 16 records only candidate identities, public documentation facts, missing/unproven evidence,
  and future review steps. It selects no provider or product, performs no external verification,
  loads no credential, and does not treat public documentation, a Phase 13 artifact, or a canonical
  hash as an entitlement or independent rights review.
- Phase 17 records exact official product/reference identities and marks them only as selected for
  independent rights review. That marker is not operational source/provider/product selection,
  procurement, contract acceptance, entitlement, use-rights approval, or permission to contact a
  provider or obtain data.
- Phase 18 records a technical fixed-time review of official public terms. Those official pages were
  accessed read-only during the architecture review;
  `operational_external_request_performed=false` means no operational provider, account,
  entitlement, or data request. The generator, verifier, tests, and CI do not browse and store no
  remote HTTP response body.
- The Phase 18 aggregate is `BLOCKED_NO_OPERATIONAL_SELECTION`. SEC public reuse support remains
  subject to current fair-access/security policy and does not prove fitness or selection. Tiingo
  public terms make internal use conditional and prohibit the planned persistent-database and
  derived use; FRED public terms prohibit the planned non-display software/system/model use,
  persistence, and derived use. Morningstar/CRSP and LSEG exact uses require private licenses that
  were not reviewed. These technical classifications are not
  legal advice, current entitlement, or authority to contact a provider or obtain data.
- Phase 19 is an offline assessment of two missing Phase 16 Step 3 prior-evidence hashes. It produces
  neither `non_synthetic_evaluation_policy_sha256` nor
  `confirmation_holdout_definition_sha256`, contacts no provider or counsel, reads no account or
  data, and cannot convert a public-terms classification into operational selection, permitted use,
  policy approval, holdout authority, or research authority.
- Phase 20 is an offline register of required input names and unapplied future transition rules. A
  field name is not an operational/product/license/schema/calendar/threshold value, `INPUTS_FROZEN`
  is not policy or holdout approval, and an artifact or manifest hash cannot replace either missing
  Step 3 hash. It contacts no provider or counsel, reads no account or data, and grants no data,
  research, risk, execution, or order authority.
- Current public caveats remain binding review inputs: Tiingo use is plan/entitlement dependent;
  CRSP/CCM is licensed and CCM also requires Compustat Xpressfeed; SEC automation must follow current
  fair-access policy, with the declared User-Agent/company-contact requirement sourced to Accessing
  EDGAR Data; FRED general prohibition (p) and API prohibition (k) prohibit using its content in
  connection with software-system or machine-learning development/training, while separate terms
  restrict storage/cache/archive/database use and preserve third-party rights; and LSEG Tick History
  public coverage claims do not establish a Fable5 license, exact delivery, or permitted retained use.
- Derived-data rights are provider-specific and require review before external distribution.

## Scope-change review

Obtain specialized legal/compliance review before personalized advice, customer-specific portfolios,
real-money routing, custody, adviser/broker claims, external marketing of performance, social-media
communications, or third-party real-time/exchange data display. The live execution path is outside this
repository's mission and must not be added as an “optional” mode.

## Evidence and audit retention

Retain source/version lineage, model/config lineage, approvals, evaluation reports, risk decisions, and
communication-safe explanations according to an approved retention policy. Immutable audit events
must not contain credentials, unnecessary personal data, or licensed full text.

Phase 12 readiness evidence also excludes raw account identifiers, headers, provider bodies, order
details, position details, and raw quote prices. `SHADOW_READY` is short-lived historical evidence,
not investment advice, a performance claim, strategy eligibility, or permission to submit an order.

Phase 13 qualification evidence stores only sanitized bounded manifests, checks, hashes, counts,
ranges, and closed reason codes. Raw provider bodies, token-bearing URLs, headers, exception text,
and licensed observations are neither persisted nor returned. `MOCK_PROOF_COMPLETE` proves only the
local contract. `EXTERNAL_SAMPLE_QUALIFIED`, if separately authorized and actually proven, would not
establish full-history coverage, research eligibility, performance, personalized advice, execution
readiness, or permission to submit an order.

Phase 14 eligibility evidence stores only the Phase 13 identity/hash lineage, six sanitized
capability projections, twelve closed checks, and false authority fields. It contains no licensed
provider body, observation value, research snapshot, return, performance metric, signal, approval,
risk clearance, order, or fill. `MOCK_PROOF_COMPLETE` proves contract mechanics only; every other
current input is truthfully `BLOCKED`.

Phase 15 admission-specification evidence is a committed canonical requirements document plus a
closed gap ledger. It contains policy identifiers, requirement/gap codes, statuses, reason codes,
hashes, and false authority fields only. It contains no account, credential, provider response,
entitlement document, contract text, observation value, data snapshot, feature, label, return,
performance result, approval, risk clearance, order, or fill. `REQUIREMENTS_FROZEN` means the
engineering contract is complete; it is not counsel review, a license, data eligibility, research
authority, or evidence that any missing prerequisite has been obtained.

Phase 16 source-plan evidence contains only plan requirements, required capability codes,
candidate-only facts, missing/unproven states, `NOT_STARTED` future steps, unchanged Phase 15 gap
bindings, identities, hashes, and false authority fields. It contains no provider contract, license,
credential, payload, observation, dataset, evaluation policy, holdout, performance result, approval,
risk clearance, order, or fill. `PLAN_FROZEN` is neither legal review nor permission to select,
contact, capture from, store, normalize, display, derive from, or redistribute any source.

Phase 17 candidate-product evidence contains only accepted Phase 16 lineage, fixed public product
names and official URLs, narrow documentation facts, review-routing states, closed reasons, hashes,
unchanged downstream steps/gaps, and false authority fields. `OUTPUT_FROZEN` proves only the Step 1
metadata output; the artifact remains `BLOCKED`. It contains no contract body, credential,
entitlement, provider response, licensed data, observation, schema sample, evaluation policy,
holdout, performance result, approval, risk clearance, order, or fill. Independent counsel/rights
review remains required before any access, storage, non-display use, derived-data use, retention,
redistribution, or revocation conclusion.

Phase 18 current-use-rights evidence contains only accepted Phase 17 lineage, 24 inert official-
source metadata rows, conservative paraphrases, eight technical dimension states per product,
blocked findings, step states, identities, and hashes. It contains no remote HTTP response body,
legal opinion,
executed contract, account, credential, entitlement, provider response, licensed data, observation,
schema sample, evaluation policy, holdout, performance result, approval, risk clearance, order, or
fill. Public-source facts were reviewed at `2026-07-19T15:58:18.5305832Z` but are not continuously
authenticated. Any later action must revalidate current official policy and exact executed rights;
the artifact itself grants no operational provider/source/product selection or later-step authority.

Phase 19 Step 3 prerequisite-assessment evidence contains only accepted Phase 18 lineage, fixed
repository-methodology findings, the two missing prerequisite names without values, unchanged Phase
15 gap bindings, unchanged Phase 16 step states, identities, hashes, and false authority fields. Its
`OUTPUT_FROZEN` assessment state proves only that the blocked assessment reproduces. It contains no
legal opinion, account, credential, entitlement, contract body, provider response, observation,
dataset, schema sample, complete evaluation policy, approved threshold, exact holdout interval,
holdout label, feature, signal, return, metric, performance result, approval, risk clearance, order,
or fill. It does not authorize Step 3 or any external action.

Phase 20 evaluation/holdout input-register evidence contains only accepted Phase 19 lineage, twenty
required input-name rows, ten unapplied future-only transition rules, two missing prerequisite names
without values, unchanged Phase 15 gap bindings, unchanged Phase 16 step states, identities, hashes,
and false authority fields. `INPUTS_FROZEN` proves only that the blocked register reproduces. It
contains no selected provider/product/delivery/schema, legal opinion, executed contract, account,
credential, entitlement, provider response, observation, dataset, calendar/date/interval value,
threshold, cost calibration, regime, risk value, feature, signal, label, return, metric, complete
policy, holdout definition or label, performance result, approval, order, or fill. It applies no
state transition and authorizes neither Step 3 nor any external action.
