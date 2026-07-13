# Fable5 product brief

## Decision

Build a disciplined research-to-paper-trading platform. Do not build a live autonomous trading
bot. The product's value is the chain of evidence—including a defensible rejection—not the number
of strategies it promotes.

## Problem

Social-media trading claims often omit the information needed to test them: a timestamped source,
an explicit action rule, a forecast horizon, a point-in-time universe, realistic execution costs,
and selection-aware validation. A conventional backtest UI can make these omissions look like
performance. Fable5 turns a claim into an auditable research object and blocks progress when the
evidence is incomplete.

## Intended users

- Quant researchers who need reproducible experiment and data lineage.
- Investment-research teams that need clear build/defer/reject reasoning.
- Risk and compliance reviewers who need visible gates, approvals, and stop conditions.
- Engineers implementing data, evaluation, and paper-simulation infrastructure.

The product is not a personalized adviser and is not intended to generate or route live orders.

## Product modes

1. **Idea Intake** preserves the source and ambiguity before normalization.
2. **Research Lab** maps testable ideas to canonical families and evaluates them under
   point-in-time, cost-aware, selection-aware rules.
3. **Paper Trading** observes only manually approved research candidates in a conspicuously
   simulated environment.
4. **Risk / Compliance** exposes every blocking gate, approval, audit record, and stop condition.

## Strategy scope

### Build-first research candidates

- Cross-sectional equity ranking: lead candidate because its canonical factor family is the most
  empirically grounded and can operate at liquid daily/weekly/monthly horizons.
- Time-series momentum and regime: implement as trend, volatility targeting, and explicit reversal
  risk—not literal chart-pattern recognition.
- Event-driven text overlay: extract features from filings, earnings material, and reputable news;
  an LLM never emits an instruction and social attention cannot stand alone.

### Defer

- Pairs/statistical arbitrage: prototype later; short availability, borrow fees, and structural
  breaks are mandatory research inputs.
- Options-flow / implied-versus-realized analytics: read-only later; options data, surfaces, greeks,
  and licensing make it operationally heavy.

### Reject for this platform

- Order-flow / order-book prediction: the signal horizon and infrastructure belong to an HFT stack,
  not a retail-frequency research and paper-simulation platform. Do not scaffold it.

The full, evidence-backed briefs are in `docs/STRATEGY_CANON.md`.

## Non-goals

- Live execution, real-money orders, or a configurable broker production endpoint.
- Personalized recommendations, guarantees, or performance marketing.
- A chart-pattern classifier presented as a durable alpha source.
- A social-only sentiment strategy.
- HFT, exchange-depth replay, colocation, or queue-position simulation.
- Fabricated performance or vendor-backed claims when only mock data is present.

## Product principles

- **Fail closed.** Missing data lineage, policy thresholds, or statistics block promotion.
- **Warnings dominate.** A blocking leakage or cost flag visually outranks a positive Sharpe.
- **Point in time by construction.** Availability time, revision history, membership history, and
  delistings are data-contract fields, not report footnotes.
- **Selection is part of the model.** Abandoned and failed trials remain in the trial registry.
- **Simulation is explicit.** Every paper surface says simulated and no live path exists.
- **Traceability is a first-class route.** A later signal must link to source, extraction, config,
  data snapshot, code version, evaluation, approval, and audit entry.

## Phase 1 outcome

Phase 1 supplies the control-plane vertical slice only: Compose infrastructure, migrations, typed
health contracts, an idle research queue, accessible navigation, policy documentation, automated
checks, and an immutable audit schema. It contains no extraction, provider, strategy, backtest,
risk-engine, signal, broker, or order behavior.

## Success criteria

- The full local stack starts from one Compose command without external credentials.
- Liveness and dependency readiness have distinct, tested semantics.
- Frontend navigation renders all four modes and keeps the simulation boundary visible.
- FastAPI is the sole API-schema authority; generated TypeScript fails CI on drift.
- Both language test suites and lint/type checks run from root commands.
- The source supplement is copied without text drift and the hard gates are exact file prefixes.
- No executable Phase 2+ or live-order code exists.

