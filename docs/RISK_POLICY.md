# Risk and governance policy

## Scope

Fable5 is research software with simulated paper trading only. Risk controls are not a substitute for
valid research, and positive research statistics do not create authorization to simulate an order.
Phase 1 establishes the policy, paper-only configuration, and immutable audit spine; executable
portfolio or order controls remain absent. Phase 7 adds only immutable approval and pre-order-risk
assessment evidence.

## Execution boundary

- The only valid execution-mode value is `paper`.
- There is no `live` enum member, broker production URL, arbitrary broker base URL, live credential,
  or live-order method.
- No paper adapter, broker endpoint, order-submission method, fill, or position path exists.
- “Disabled live trading” is insufficient because it implies a dormant path; the path must be absent.
- The UI and API describe paper activity as simulated and never as fills representative of live
  execution quality.

## Promotion states

```text
RESEARCH_DRAFT
  -> EVALUATION_BLOCKED | EVALUATION_FAILED | PASS_RESEARCH
PASS_RESEARCH
  -> APPROVED_PAPER | FAIL_REJECT (separate immutable Phase 7 assessment)
```

No automatic transition enters `APPROVED_PAPER`. Every approval records approver, timestamp, strategy
and policy hashes, data snapshot, code version, permitted universe/notional/window, expiry/review date,
and rationale. Any config/model/policy/material-data change requires new evidence. Revocation is an
append-only event; it does not mutate a historical assessment and blocks reuse of that authorization.
`APPROVED_PAPER` is synthetic governance evidence, not order authorization or execution readiness.

## Approval and pre-order-risk assessment (Phase 7)

Without creating any order or executable intent, the risk service must prove:

- the exact immutable Phase 6 artifact is `PASS_RESEARCH` and all authorization evidence is current;
- global, strategy, and data-quality control evidence is clear;
- the source research artifact and complete evaluation/audit chain match the approved hashes;
- the server-owned synthetic risk context passes notional, gross, net, sector, concentration, liquidity,
  turnover, and volatility constraints;
- daily loss and strategy drawdown stops are clear;
- data freshness, market calendar, and duplicate/idempotency checks pass;
- every decision and rejection is appended to the audit log.

If a policy limit is missing or cannot be computed, persist `FAIL_REJECT`. Limits are explicit,
versioned, synthetic inputs; this document does not invent universal percentages. No order object is
created by either outcome.

## Kill switch

Global, strategy, and data-quality control states are independently supplied, immutable evidence.
Any active or uncomputable state fails the assessment. Phase 7 has no control-clearance API, pending
intent, queue, cancellation, or broker simulator.

## Audit requirements

Every signal, evaluation, approval assessment, revocation, and risk decision includes the immutable
fields in `docs/EVALS.md`. The Phase 1
`research_audit_events` table rejects updates/deletes; later migrations may add linked domain tables but
must not weaken immutability. Secrets and licensed payload text are referenced, not copied into logs.

## Review triggers

Re-evaluation and approval review are required after material model/config change, source/provider or
schema change, point-in-time correction, cost calibration change, new regime failure, DSR/PBO or trial
registry change, risk limit breach, stale data, or later explicitly authorized simulator behavior.
