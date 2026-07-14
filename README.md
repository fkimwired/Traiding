# Fable5

Fable5 is a research-to-paper-trading platform scaffold. It translates source claims into testable
research, rejects leakage and cost-fragile results, and allows only manually approved candidates near
a clearly simulated paper environment. It is **not** a live trading bot, does not provide personalized
investment advice, and contains no real-money order path.

## Phase 4 implementation status

Implemented and verified by the full isolated Compose acceptance gate:

- Docker Compose control plane with PostgreSQL, Redis, one-shot migrations, FastAPI, an RQ research
  worker, and Next.js;
- distinct `GET /health` liveness and `GET /ready` dependency-readiness endpoints;
- reversible PostgreSQL baseline migration with an append-only research audit spine;
- FastAPI-owned OpenAPI with generated TypeScript contracts and drift checks;
- four-mode frontend navigation with a persistent simulation/advice boundary;
- Python/frontend unit tests, lint/type checks, CI, and a phase-aware verifier;
- substantive strategy, validation, risk, provider, compliance, and handoff documentation.
- lossless URL/text intake with immutable, correction-aware source versions and exact UTF-8 hashes;
- a canonical Pydantic `TradingIdeaCard` with explicit evidence, testability, infrastructure-risk,
  and social-corroboration states;
- deterministic synthetic/mock extraction on the existing `research` queue, idempotent extraction
  fingerprints, append-only events, and deterministic Markdown memos;
- reversible Phase 2 persistence whose source, extraction, card, corroboration, and memo records
  reject update, delete, and truncate;
- create/read/list-only Phase 2 APIs and regenerated TypeScript contracts;
- six clearly labeled synthetic archetype fixtures plus adversarial safety and provenance tests.
- a pure, table-driven canon mapper whose closed family/verdict vocabulary cannot be overridden by
  source text, clients, or an LLM;
- fail-closed mapping precedence for non-testable/ambiguous, HFT, social-corroboration, pairs, and
  read-only-options outcomes;
- immutable, versioned mapping and deterministic rationale records with exact Phase 2 lineage;
- create/read/list-only Phase 3 mapping APIs and source-linked rationale presentation in Idea Intake.
- field-specific, vendor-neutral point-in-time contracts for the authorized Family A/B/C surfaces;
- deterministic synthetic adapters, explicit entitlements, typed credential-unavailable results, and
  a mandatory data-quality gate with leakage and revision-replay checks;
- immutable raw, revision, normalized, constituent, quality-finding, and canonical snapshot lineage;
- create/read/list-only Phase 4 snapshot APIs and regenerated TypeScript contracts;
- reversible `0004_phase4` persistence with concurrent idempotence, deterministic hashes, and
  database rejection of update, delete, and truncate across all seven Phase 4 tables.

Intentionally absent: real-provider implementations, features or labels, backtesting, alpha models,
signals or strategies, performance metrics, portfolio/risk logic, approvals, brokers, positions,
paper orders, and every live-order capability.

## Prerequisites

- Docker Desktop or another Docker Engine with Compose v2.
- For host-side development: Python 3.12 and Node.js 22.14 or newer.
- PowerShell on Windows, or `make`/POSIX shell on macOS/Linux.

No data-provider, LLM, broker, or commercial credential is needed for Phase 4. Local and CI extraction
and point-in-time data use deterministic synthetic implementations; mapping is pure deterministic
code; source URLs are stored as provenance and are not fetched.

## Start the full stack

Defaults are safe for local development, so copying the environment file is optional. To customize
host ports or browser-facing origins:

```powershell
Copy-Item .env.example .env
```

Start all six services and wait for readiness:

```powershell
docker compose up --build --wait
```

Plain `docker compose up` also builds missing images on the first run. Open:

- Frontend: <http://127.0.0.1:3000>
- API liveness: <http://127.0.0.1:8000/health>
- API docs: <http://127.0.0.1:8000/docs>

Verify the stable liveness body:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Expected JSON:

```json
{"status":"ok","service":"api","mode":"research-paper-only"}
```

Stop without deleting local database/Redis volumes:

```powershell
docker compose down
```

## Test and quality commands

### Windows

Create a host virtual environment and install the tested, transitively constrained dependency set:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --constraint requirements.lock -e ".[dev]"
$env:npm_config_cache = "$env:TEMP\fable5-npm-cache"
npm ci
```

Run both test suites:

```powershell
.\scripts\test.ps1
```

Run Python/frontend linting, type checks, generated-contract drift, and static Phase 4 policy checks:

```powershell
.\scripts\check.ps1
```

Run the isolated full-stack Phase 4 acceptance verifier (it creates and removes its own Compose
project and volumes):

```powershell
.\.venv\Scripts\python.exe scripts\verify_phase1.py --phase 4
```

### macOS/Linux/CI

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install --constraint requirements.lock -e ".[dev]"
npm ci
make check
make test
make smoke
```

The documented equivalent of `make test` on Windows is `.\scripts\test.ps1`. Both run `pytest` and
non-watch Vitest tests and propagate failure.

## Contracts

FastAPI/Pydantic is the sole API-contract authority. Never hand-maintain a duplicate frontend response
interface.

```powershell
npm run contracts:generate
npm run contracts:check
```

The first command writes deterministic `packages/contracts/openapi.json` and generated TypeScript.
The second regenerates to memory/temporary output and fails if committed artifacts drift.

## Migrations

The one-shot `migrate` Compose service runs Alembic before the API starts. The application never calls
`metadata.create_all()`. The baseline `0001_phase1` revision creates `research_audit_events` with the
required config/data/code/seed/trial/time fields and PostgreSQL triggers that reject updates, deletes,
and truncation. Its fixed development-only database identity intentionally has no independent `.env`
overrides, preventing bootstrap credentials and the application URL from silently diverging.

Useful commands while the stack is running:

```powershell
docker compose run --rm migrate alembic -c services/api/alembic.ini current
docker compose run --rm migrate alembic -c services/api/alembic.ini upgrade head
```

Applied revisions are immutable. `0002_phase2` adds append-only source, source-version,
corroboration, extraction-request/event, card, and memo records without editing the Phase 1 baseline.
`0003_phase3` adds append-only mapping versions, database-validated parent lineage, deferred exact
corroboration-set equality, post-finalization append guards, and deterministic rationale artifacts.
`0004_phase4` adds immutable point-in-time snapshot headers, raw observations, revisions, normalized
observations, constituents, quality findings, and manifests with exact canonical-hash validation.
The Phase 4 acceptance cycle runs real concurrency, lineage, and append-only tests, snapshots every
Phase 1-3 row, downgrades specifically to `0003_phase3`, proves those rows are byte-identical, and
re-upgrades to head.

## Architecture

| Component | Current responsibility | Boundary |
|---|---|---|
| `frontend` | Navigation, simulation disclosure, and source-linked deterministic rationale | no actionable paper-order controls |
| `api` | Health/readiness plus typed source/card/mapping/snapshot create/read/list authority | no signal, performance, or execution endpoint |
| `migrate` | one-shot Alembic upgrade | API never creates schema at startup |
| `worker` | deterministic extraction on the `research` queue | no strategy/backtest/trading queue |
| `postgres` | Immutable audit, provenance, mapping, and point-in-time snapshot lineage | no evaluation, risk, or order records |
| `redis` | queue/cache connectivity | no trading queue exists |
| `packages/contracts` | generated OpenAPI TypeScript | never a second schema authority |

Model tracking will use an MLflow-compatible interface when Phase 5 defines experiment artifacts; no
MLflow service or dependency is added prematurely.

## Repository guide

- `AGENTS.md` / `CLAUDE.md`: exact hard gates, followed by durable build conventions.
- `docs/STRATEGY_CANON.md`: defensible briefs for all six archetypes and their verdicts.
- `docs/EVALS.md`: point-in-time, nested chronological, DSR, PBO, leakage, costs, and promotion gates.
- `docs/DATA_SOURCES.md`: current provider landscape, adapter metadata, and entitlement cautions.
- `docs/IMPLEMENTATION_PLAN.md`: phase dependencies and the required handoff template.
- `docs/PHASE_02_SCHEMA_DECISIONS.md`: frozen evidence, null, testability, and corroboration semantics.
- `docs/PHASE_03_MAPPING_DECISIONS.md`: frozen family, rule, reason, precedence, and rationale semantics.
- `docs/PHASE_04_DATA_DECISIONS.md`: frozen point-in-time schemas, authorization, canonicalization,
  availability, revision, entitlement, quality, and snapshot semantics.
- `docs/handoffs/PHASE_04.md`: authoritative Phase 4 acceptance boundary and inputs.
- `services/extraction`: canonical Phase 2 schema, mock extractor, persistence, workflow, and tests.
- `services/mapping`: pure Phase 3 mapper, immutable persistence boundary, and tests.
- `services/data`: vendor-neutral Phase 4 contracts, synthetic adapters, quality gate, immutable
  snapshot materializer/repository/workflow, fixtures, and tests.
- `strategy_specs/`: reserved for source-specific Phase 2 artifacts, not invented post content.

## Validation posture

The research supplement's strategy verdicts are preserved. `docs/RESEARCH_VALIDATION_NOTES.md`
clarifies the exact time geometry for purging/embargo, the additional information needed for DSR and
PBO, point-in-time availability/vintage requirements, cost-model calibration, and provider facts as of
2026-07-13. Numeric promotion thresholds not supplied by the research are required versioned policy
inputs; missing values block promotion rather than receiving optimistic defaults.

## Next step

After the full Phase 4 acceptance gate passes, Phase 5 may define feature/label contracts and the
evaluation harness only after freezing signal definitions, horizons, required data, realistic costs
and slippage, purged/embargoed walk-forward reports, risk limits, and audit output. Do not add paper
execution, brokers, positions, orders, or any live capability.
