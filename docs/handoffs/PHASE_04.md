# Phase 4 handoff — point-in-time data contracts and deterministic adapters

## Objective and explicit exclusions

Implement Phase 4 only: define typed, vendor-neutral point-in-time data interfaces, immutable data
snapshots, deterministic mock adapters, and clear credential-unavailable behavior for the research
families that Phase 3 can authorize for later specification.

Stop before features, labels, signals, models, strategy implementations, backtests, performance
metrics, portfolio or risk logic, approvals, paper orders, brokers, or any live capability. A Phase 3
`BUILD_RESEARCH` mapping permits data-contract work only; it is not evidence of profitability,
approval, advice, or paper eligibility.

## Inputs and source authority

Read `AGENTS.md`, `docs/PRODUCT_BRIEF.md`, `docs/STRATEGY_CANON.md`, `docs/DATA_SOURCES.md`,
`docs/EVALS.md`, `docs/IMPLEMENTATION_PLAN.md`, `docs/PHASE_02_SCHEMA_DECISIONS.md`, the Phase 3
mapping decisions and handoff report, and the complete Phase 1–3 implementation/tests first.

The Phase 4 contracts must consume persisted Phase 3 mapping identities without changing their
family or verdict. Provider marketing pages are not schema authority. Any current provider fact or
entitlement assumption must be reverified from primary documentation before it is recorded.

## Files/directories in scope

Allowed writes are limited to a new data-domain package and its tests; typed adapter interfaces and
deterministic mock implementations; Phase 4 snapshot create/read/list APIs and tests; one reversible
`0004` Alembic revision; generated contracts; phase-aware verification/CI; and Phase 4 documentation.

Do not add files under `services/backtester/`, `services/risk/`, `strategy_specs/`, or any broker,
order, portfolio, or execution-oriented path. Strategy code must not import a vendor SDK. No
commercial credential is required by local tests or CI.

## Contracts and invariants

Every adapter response and stored observation must carry, where applicable:

- provider and adapter identities/versions;
- dataset/product, schema, entitlement/use-rights, and source-record identities;
- stable instrument/security identity plus historical symbol/listing context;
- `event_time`, explicit `available_at`, `retrieved_at`, and UTC normalization;
- `valid_from`/`valid_to` and revision/vintage identity for mutable records;
- timezone, calendar, units, quality flags, and an explicit missingness reason;
- immutable raw-payload hash and deterministic data-snapshot identity/hash.

Raw immutable observations and normalized point-in-time records remain separate. Revisions append;
they never overwrite an earlier vintage. Date-only inputs use a conservative, documented
availability convention. No interface may silently substitute current constituents, latest
restatements, zero delisting returns, adjusted-price future knowledge, or fabricated provider data.

The initial adapter families must be vendor-neutral and no broader than the minimum A/B/C research
data contracts: security master/universe history; OHLCV, corporate actions, and delisting-aware
return inputs; as-reported fundamentals with filing availability; and official document/event
metadata with immutable content hashes. Social content remains non-contributing without exact
official corroboration. Options and order-book acquisition remain absent.

Configuration is environment-driven. Missing optional credentials produce a typed `unavailable`
result before any network call. Deterministic mocks are clearly labeled synthetic and return the
same snapshot/hash for the same fixture and adapter version.

## Implementation units

1. Freeze field-specific PIT observation, revision, quality, entitlement, and snapshot models.
2. Define vendor-neutral typed adapter protocols with explicit capability and unavailable states.
3. Implement deterministic synthetic adapters for the approved A/B/C data-contract surfaces.
4. Persist immutable raw/normalized snapshot lineage in a reversible, append-only `0004` revision.
5. Add snapshot create/read/list APIs and regenerate FastAPI-owned TypeScript contracts.
6. Extend static/full verification for PIT semantics, mock determinism, append-only enforcement, and
   `0004 → 0003 → 0004` preservation of all Phase 1–3 records.

Each unit must include an executable acceptance test and preserve source, schema, entitlement, and
availability evidence.

## Acceptance tests

Before editing, run the complete Phase 3 gate. Phase 4 tests must prove:

1. every observation has explicit event/availability/retrieval semantics and normalizes to UTC;
2. a revision appends a new vintage and cannot mutate the earlier record;
3. future availability, current-universe leakage, latest-restatement substitution, and missing
   delisting handling each fail closed;
4. raw and normalized records trace to the same immutable snapshot and content hash;
5. identical synthetic fixture/config input reproduces the same snapshot identity and payload;
6. missing credentials return a sanitized unavailable state and make no network request;
7. adapter interfaces expose no vendor SDK type to mapping or future strategy packages;
8. OpenAPI contains only Phase 4 create/read/list snapshot paths and generated contracts;
9. `0004` downgrade to `0003_phase3` and re-upgrade preserve every Phase 1–3 row byte-identically;
10. no feature, label, signal, model, backtest, performance, risk, position, provider-specific
    strategy import, broker, paper-order, or live capability exists.

Run the phase-aware root checks, tests, production frontend build, static verifier, and full isolated
PostgreSQL/Redis verifier exactly as documented by the Phase 4 implementation.

## Data/security posture

Local and CI acceptance uses only clearly labeled synthetic fixtures. Real adapters are optional and
credential-gated; tests must not require a network call. Secrets never enter URLs, errors, logs,
fixtures, snapshots, frontend bundles, or generated contracts. Entitlement and redistribution
metadata is mandatory and never inferred from provider availability.

## Migration/rollback

Add `0004` with `down_revision="0003_phase3"`; never edit `0001`, `0002`, or `0003`. Snapshot,
revision, raw-record, and normalized-record tables are append-only and reject update, delete, and
truncate. Downgrade removes only Phase 4 objects and supports immediate re-upgrade without changing
any earlier-phase row.

## Handoff report

Report exact files changed; commands/results; adapter/schema/snapshot versions and hashes; mock
fixture matrix; PIT/leakage test evidence; credential-unavailable evidence; migration preservation;
generated-contract evidence; provider facts that remain unverified; safety/data limitations; review
disagreements; and a ready Phase 5 task.

## Stop condition

Stop after point-in-time contracts, deterministic mocks, immutable snapshots, create/read/list APIs,
generated contracts, documentation, and tests. Do not begin features, models, evaluation,
strategies, risk/execution, paper orders, brokers, or live capability.
