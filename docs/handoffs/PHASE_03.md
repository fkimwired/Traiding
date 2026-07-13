# Phase 3 handoff — deterministic canon mapping

## Objective and explicit exclusions

Implement Phase 3 only: map immutable Phase 2 `TradingIdeaCard` records to one canonical research
family and one deterministic research verdict, then present source-linked rationale in the existing
ideas UI.

Stop before provider adapters, datasets, feature pipelines, models, backtesting, performance,
signals, portfolio or risk enforcement, approvals, brokers, paper orders, or any live capability.
`BUILD_RESEARCH` authorizes only a later research specification; it never means profitable,
approved, recommended, or paper-eligible.

## Inputs and source authority

Read `AGENTS.md`, `docs/PRODUCT_BRIEF.md`, `docs/STRATEGY_CANON.md`, `docs/EVALS.md`,
`docs/IMPLEMENTATION_PLAN.md`, `docs/PHASE_02_SCHEMA_DECISIONS.md`, and the complete Phase 2
implementation/tests first. The only mapper inputs are persisted Phase 2 card, extraction-request,
source-version, exact corroboration-version, and extractor-schema identities.

Never reinterpret mutable request text, authenticate a URL, retrieve a source, or accept a family or
verdict from an LLM. Synthetic Phase 2 fixtures are the only required acceptance data.

## Files/directories in scope

Allowed writes for the Phase 3 task are limited to:

- a new `services/mapping/` domain package and its tests;
- Phase 3 create/read/list API routes and tests under `services/api/`;
- one new reversible `0003` Alembic revision under `services/api/migrations/versions/`;
- generated `packages/contracts/` artifacts;
- rationale presentation in `services/frontend/src/app/ideas/` and its tests;
- phase-aware verification/CI entry points and Phase 3 documentation.

Preserve the Phase 1/2 migrations, source/extraction records, and generated-contract ownership.
`services/backtester/`, `services/risk/`, provider code, broker code, and every execution-oriented path
are forbidden in this phase.

## Contracts and invariants

`ResearchVerdict` is a closed machine vocabulary with exactly these values:

| Value | Phase 3 meaning |
|---|---|
| `BUILD_RESEARCH` | Family may receive a later research specification only. |
| `DEFER` | Retain the mapped family, but a stated research prerequisite blocks build work. |
| `DEFER_READ_ONLY` | Retain only a future non-directional analytics presentation. |
| `REJECT_PLATFORM` | Record the platform mismatch and create no downstream scaffold. |
| `NON_TESTABLE` | Source evidence is structurally insufficient or family mapping is ambiguous. |

Priority prose such as “first,” “second,” or “third” is not a verdict. Later promotion-state values
from Phase 5 are not valid Phase 3 verdicts.

Apply this fail-closed precedence before lower rows:

| Precedence | Phase 2 condition/family | Machine verdict | Required reason |
|---:|---|---|---|
| 1 | `testability_status=non_testable` or ambiguous family | `NON_TESTABLE` | Exact missing/ambiguous Phase 2 reason code |
| 2 | E — order-flow, order-book, scalp, sub-minute, or HFT | `REJECT_PLATFORM` | `PLATFORM_INFRASTRUCTURE_MISMATCH` |
| 3 | C — social/news with contribution blocked | `DEFER` | `OFFICIAL_CORROBORATION_REQUIRED` |
| 4 | D — pairs/statistical arbitrage | `DEFER` | `BORROW_AND_BREAK_REQUIREMENTS` |
| 5 | F — options-flow/IV-versus-RV analytics | `DEFER_READ_ONLY` | `READ_ONLY_ANALYTICS_ONLY` |
| 6 | A, B, or corroboration-eligible C | `BUILD_RESEARCH` | Matched canonical rule IDs |

A structurally testable but uncorroborated social card retains family C and its Phase 2 testability;
the mapper must not turn it into `NON_TESTABLE` or `REJECT_PLATFORM`. Missing or ambiguous action
rule/horizon remains `NON_TESTABLE` before any family rule.

Every result is immutable and carries mapper rule-set version/hash, input card/extraction/source
version IDs, matched rule IDs, verdict, ordered reason codes, rationale-template version, and a
server-owned UTC creation timestamp. Identical card plus rule-set hash is idempotent; a changed rule
set creates a new mapping version. No free-form model output may choose or override a result.

## Implementation units

1. Define field-specific mapping input/output models, the closed family/verdict vocabularies, reason
   codes, precedence, and a canonical rule-set hash.
2. Implement a table-driven pure mapper over persisted Phase 2 fields; it performs no I/O and calls
   no LLM.
3. Persist immutable mapping versions and rationale artifacts through a reversible `0003` revision.
4. Add create/read/list mapping APIs and regenerate OpenAPI/TypeScript from FastAPI/Pydantic.
5. Present family, verdict, reasons, source lineage, and the research-only boundary in the ideas UI.
6. Extend static/full verification for mapping idempotency, append-only PostgreSQL enforcement, and
   downgrade/re-upgrade while preserving Phase 1/2 records.

Each unit must include an executable acceptance test and preserve its source/rule evidence.

## Acceptance tests

Before editing, run the complete Phase 2 acceptance gate:

```powershell
.\.venv\Scripts\python.exe scripts\verify_phase1.py --phase 2
```

Phase 3 tests must prove:

1. the six synthetic Phase 2 fixtures map to the exact family/verdict table above;
2. non-testable and ambiguous-family precedence wins over every family match;
3. uncorroborated social maps to family C plus `DEFER` and
   `OFFICIAL_CORROBORATION_REQUIRED`, never a contributing/build result;
4. order-flow/HFT maps to `REJECT_PLATFORM` and creates no executable scaffold;
5. options maps to `DEFER_READ_ONLY`, while pairs maps to `DEFER`;
6. identical card/rule-set input is idempotent and changed rules append a new version;
7. every result traces to exact source/card/extraction/rule IDs;
8. OpenAPI contains only create/read/list mapping paths and generated field-specific contracts;
9. `0003` upgrade, downgrade to `0002_phase2`, and re-upgrade preserve all Phase 1/2 records;
10. no performance, advice, signal, position, provider, broker, paper-order, or live capability exists.

The task must add Phase 3 support to the phase-aware verifier, then run literally:

```powershell
$env:FABLE5_VERIFY_PHASE = "3"
.\scripts\check.ps1
.\scripts\test.ps1
npm run build
.\.venv\Scripts\python.exe scripts\verify_phase1.py --static-only --phase 3
.\.venv\Scripts\python.exe scripts\verify_phase1.py --phase 3
```

## Data/security posture

Use only clearly labeled synthetic fixtures and persisted Phase 2 artifacts. Make no network call and
require no provider, broker, model, or commercial credential. Do not add an LLM runtime dependency,
copy licensed source text into fixtures, expose secrets in errors/logs, or claim real performance.
Rationale is deterministic template output from matched rule IDs, not generated advice.

## Migration/rollback

Add `0003` with `down_revision="0002_phase2"`; do not edit `0001` or `0002`. Mapping and rationale
records are append-only and reject update, delete, and truncate. Downgrade removes only Phase 3
objects/functions/triggers, leaves every Phase 1/2 row byte-identical, and supports immediate
re-upgrade. The application must never call `create_all()`.

## Handoff report

Report the exact files changed; commands and results; rule-set/version hashes; fixture mapping matrix;
migration downgrade/re-upgrade evidence; generated-contract evidence; unresolved ambiguity; safety
and data limitations; Qwen or other LLM review disagreements; and the next ready-to-paste Phase 4
task. Do not claim completion unless the full Phase 3 verifier passes against PostgreSQL and Redis.

## Stop condition

Stop after deterministic mapping, immutable rationale presentation, migrations, generated contracts,
and tests. Do not begin provider work, data acquisition, features, models, evaluation, strategy
research, risk/execution work, paper orders, or any live capability.
