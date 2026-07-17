# Phase 10 deterministic local paper-simulation decisions

## Authorized baseline and hard boundary

Phase 10 starts from the accepted Phase 9 commit
`12a87e9dfb71afd7bb02d1f947ffea63be56a0a3`, tree
`472792e0f53fc5c29ef8d4d73bdef60d6f25a1c9`. The implementation must remain
descended from that identity and must preserve the accepted Phase 9 release evidence as historical
evidence rather than reinterpret it.

This phase adds one deterministic, synchronous, local-only simulation workflow over synthetic data.
It adds no broker or provider adapter, network client, credential, account, venue, deployment,
background execution worker, real instrument, real quote, real performance claim, personalized
advice, or dormant real-money path. The only configured execution-mode literal remains `paper`.
External routing and a live path are absent, not disabled.

The public request is reference-only: a caller supplies an immutable Phase 7 assessment identifier
and a bounded idempotency key. Instrument, universe, model, signal, side, quantity, price, time,
notional, costs, slippage, policy, risk values, outcome, and lifecycle state are all server-owned.
Unknown request fields fail strict validation.

## Source authority and fresh governance

A historical `APPROVED_PAPER` label is necessary but never sufficient. Each request resolves and
hash-validates the selected Phase 7 artifact and its complete Phase 6 run. Immediately before local
simulation, the server reruns the exact 25 existing Phase 7 currentness, revocation, control, and
numeric-risk checks at one captured UTC decision time. It resolves the newest valid policy and scope
versions in the source assessment's logical authority families while retaining the historical
source human-authorization, risk-input, and research references. Any supersession therefore resolves
to explicit rejection evidence; it never silently adopts new human or risk authority.

Phase 7 assessments are intentionally content-addressed over immutable evidence and current check
states, not wall-clock time. An unchanged re-evaluation can therefore resolve to the same Phase 7
assessment identity; Phase 10 never fabricates a distinct Phase 7 row to imply freshness. Instead it
persists a separate content-addressed revalidation proof binding the source and resolved Phase 7
artifacts, currentness and revocation hashes, decision time, idempotency key, and Phase 10 code SHA.
That proof is part of the currentness hash, request fingerprint, transition check, root artifact, and
database validation.

Phase 10 then evaluates an ordered, hash-bound check registry:

1. `SOURCE_APPROVAL_EXACT`
2. `TRANSITION_APPROVAL_FRESH`
3. `RESEARCH_PREREQUISITES_COMPLETE`
4. `SIMULATION_CONFIGURATION_EXACT`
5. `RISK_CONTEXT_EXACT`
6. `COST_SLIPPAGE_COMPLETE`
7. `LOCAL_BOUNDARY_ENFORCED`

Every check must pass before a ledger entry may exist. A fully resolved but rejected, expired,
stale, revoked, uncomputable, or otherwise ineligible request persists a terminal `BLOCKED`
simulation artifact with no ledger entry. A missing reference returns 404; hash, lineage,
idempotency, or persistence conflicts return a sanitized 409. Neither failure creates partial
simulation state.

The historical source and decision-time Phase 10 revalidation proof remain distinct immutable facts;
the resolved Phase 7 assessment identity may be reused only when its complete evidence and check
state are unchanged. Phase 10 never mutates an assessment and never relabels `PASS_RESEARCH` as
approval or `APPROVED_PAPER` as a general execution authorization.

## Deterministic QA configuration

The sole server-owned configuration is `phase10-a-local-mock-qa-v1`. It is a conspicuously synthetic
QA rehearsal for the one eligible Family A research artifact, not a selected production strategy.
It binds the exact Phase 6 research artifact, specification, configuration, snapshot bundle, model,
cost/slippage declarations, random seed, trial counts, and Phase 10 code SHA.

The configuration uses the already frozen transparent Family A model
`sector-relative-rank-linear-v1` and its declared positive-score long/flat rule against a new local
point-in-time mock observation. It does not reuse Phase 6 label-bearing research ledger cells as a
current signal. The mock security, score, quote, ADV, volatility, cash, and timing are synthetic and
versioned. The requested reference notional must exactly equal the immutable Phase 7 proposed-risk
context; it is not accepted merely because it falls below a limit.

The local matcher produces at most one long-only simulated fill. Sell, short, options, leverage,
multi-asset, partial-fill, cancellation, amendment, and asynchronous state are outside this phase.
The result records requested/filled/unfilled quantities, reference/fill prices, participation,
position and cash before/after, commission, regulatory fee, spread, impact, latency, borrow,
capacity, and total cost. Quantity, cash, position, and component costs must reconcile exactly.

Determinism is conditional on the immutable evidence, captured decision time, configuration, code
SHA, and idempotency key. The server performs no external read and uses no nondeterministic market
input. Retrying an uncertain transport result with the same key returns the same persisted artifact;
reusing a key for different resolved evidence fails closed.

## Persistence and API

Alembic revision `0008_phase10` is additive and reversible over `0007_phase7`. It owns exactly:

- `paper_simulation_runs`;
- `paper_simulation_checks`; and
- `paper_simulation_ledger_entries`.

Rows are append-only and reject update, delete, and truncate. The root stores the complete canonical
artifact payload and exact source/resolved-assessment, revalidation-proof, research, configuration,
currentness, and audit identities. Child completeness is enforced at commit: `SIMULATED_COMPLETE`
requires the full ordered all-pass check registry and exactly one valid ledger row; `BLOCKED`
requires the full check registry and zero ledger rows. Composite identifier/hash foreign keys prevent
cross-row lineage pairing. Downgrade to `0007_phase7` removes only Phase 10 objects; re-upgrade
restores exact SQL while preserving nonempty Phase 1-7 rows byte-for-byte.

FastAPI owns exactly these Phase 10 operations:

```text
POST /v1/local-simulations
GET  /v1/local-simulations
GET  /v1/local-simulations/{simulation_run_id}
```

There is no update, delete, submit, cancel, retry, broker, account, credential, fill, position, live,
or provider route. The POST atomically returns one terminal artifact. TypeScript contracts are
generated from FastAPI; no parallel handwritten response contract is allowed.

## Product surface

The Simulated Paper Status workspace gains one assessment selector and one action labeled
`Run deterministic local simulation`. It exposes no trade parameter. Known historical blockers
disable deliberate creation, but the server always performs authoritative fresh revalidation.
Completed and blocked artifacts display exact hashes, check evidence, ledger reconciliation, and a
source-to-simulation lineage link. `BLOCKED` evidence visually dominates every positive historical
label.

Every simulation surface says `SIMULATED`, `LOCAL MOCK`, no external routing, no live path, no real
performance, and no personalized investment advice. A transport-uncertain retry reuses the exact
idempotency key; validation, missing-evidence, conflict, and malformed-success states never silently
retry a POST.

## Acceptance and stop condition

Phase 10 acceptance requires formatting, lint, typing, generated-contract parity, Python/frontend
unit tests, production frontend build, Phase 10 static policy, reversible migration, concurrent
idempotency, direct-SQL immutability/completeness/adversarial proofs, API completed and blocked paths,
browser accessibility/visual checks, cleanup, a clean committed tree, and Ubuntu CI at that exact
SHA/tree.

The direct full verifier binds and prints the clean preflight `HEAD` SHA/tree, requires the identical
clean identity after cleanup, and rejects any pre-existing or remaining `fable5_acceptance_*`
container, network, or volume. Static-only verification does not impose the clean closure condition.
Browser acceptance retains the unaffected Phase 8 modes and shared-layout regression corpus while
the dedicated Phase 10 corpus owns the intentionally superseding local-simulation paper surface.

Phase 11 implementation, external providers, accounts, credentials, deployment, real data, strategy
expansion, asynchronous simulation, and any real-money behavior remain excluded. After Phase 10 is
accepted, only a read-only Phase 11 plan may be prepared until the user separately authorizes it.
