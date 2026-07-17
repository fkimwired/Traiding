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
