# Risk and governance policy

## Scope

Fable5 is research software with simulated paper trading only. Risk controls are not a substitute for
valid research, and positive research statistics do not create authorization to simulate an order.
Phase 1 establishes the policy, paper-only configuration, and immutable audit spine; executable
portfolio controls and approvals are Phase 7 work.

## Execution boundary

- The only valid execution-mode value is `paper`.
- There is no `live` enum member, broker production URL, arbitrary broker base URL, live credential,
  or live-order method.
- A later paper adapter must allowlist its paper endpoint and reject every other endpoint.
- “Disabled live trading” is insufficient because it implies a dormant path; the path must be absent.
- The UI and API describe paper activity as simulated and never as fills representative of live
  execution quality.

## Promotion states

```text
RESEARCH_DRAFT
  -> EVALUATION_BLOCKED | EVALUATION_FAILED | PASS_RESEARCH
PASS_RESEARCH
  -> APPROVED_PAPER (manual, attributable, expiring approval only)
APPROVED_PAPER
  -> PAUSED | REVOKED
```

No automatic transition enters `APPROVED_PAPER`. Every approval records approver, timestamp, strategy
and policy hashes, data snapshot, code version, permitted universe/notional/window, expiry/review date,
and rationale. Any config/model/policy/material-data change invalidates approval until reviewed.

## Pre-paper order gate (Phase 7 acceptance target)

Before a simulated order object can exist, the risk service must prove:

- strategy state is `APPROVED_PAPER` and approval is current;
- global and strategy kill switches are clear;
- source signal and latest evaluation/audit chain match the approved hashes;
- proposed position and order pass maximum position, gross, net, sector, concentration, liquidity,
  turnover, and volatility constraints;
- daily loss and strategy drawdown stops are clear;
- data freshness, market calendar, duplicate/idempotency, and paper endpoint checks pass;
- every decision and rejection is appended to the audit log.

If a policy limit is missing or cannot be computed, reject the simulated order. Limits are explicit,
versioned inputs; this document does not invent universal percentages.

## Kill switch

Provide global, strategy, and data-quality kill switches. Activation blocks new simulated orders,
cancels/marks pending simulated intents as policy permits, and cannot be cleared by the same automated
component that triggered it. Activation and clearance are manual/audited events with reasons. Risk
checks run before queueing any paper intent, not after a broker simulator responds.

## Audit requirements

Every signal, evaluation, approval, risk decision, paper intent, simulated broker response, pause, and
kill-switch event includes the immutable fields in `docs/EVALS.md`. The Phase 1
`research_audit_events` table rejects updates/deletes; later migrations may add linked domain tables but
must not weaken immutability. Secrets and licensed payload text are referenced, not copied into logs.

## Review triggers

Re-evaluation and approval review are required after material model/config change, source/provider or
schema change, point-in-time correction, cost calibration change, new regime failure, DSR/PBO or trial
registry change, risk limit breach, stale data, or unexpected paper-simulator behavior.

