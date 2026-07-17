# Fable5

Fable5 is a research-to-paper-trading platform scaffold. It translates source claims into testable
research, rejects leakage and cost-fragile results, and allows only manually approved candidates near
a clearly simulated paper environment. It is **not** a live trading bot, does not provide personalized
investment advice, and contains no real-money order path.

## Phase 9 implementation status

The accepted Phase 8 product surface and the Phase 9 release-acceptance tooling include:

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
- immutable Phase 5 evaluation policies and reports with purged/embargoed walk-forward geometry,
  cost/slippage stress, leakage blocking, risk limits, deterministic trial accounting, and complete
  audit lineage;
- deterministic Phase 6 Family A/B/C research pipelines whose artifacts preserve point-in-time
  source, preparation, trial, cost, gate, code, seed, and snapshot lineage without granting paper
  approval;
- a fail-closed Phase 7 approval and pre-order-risk assessment layer that considers only immutable
  Phase 6 `PASS_RESEARCH` evidence and separately versioned policy, scope, human authorization,
  currentness, revocation, and risk inputs;
- create/read/list-only approval-assessment and authorization-revocation APIs, with client requests
  limited to references to pre-existing immutable evidence; and
- reversible `0005_phase5`, `0006_phase6`, and `0007_phase7` persistence whose new records reject
  update, delete, and truncate while preserving every earlier row byte-for-byte;
- complete Idea Intake, Research Lab, simulated Paper Status, Risk / Compliance, and exact lineage
  workflows over generated contracts and immutable Phase 2-7 evidence;
- serial accessibility and deterministic visual QA across 24 win32 and 24 Linux baselines; and
- a standard-library, single-flight Phase 9 runner with external raw evidence, a strictly sanitized
  stage log, atomic manifest, exact SHA/tree/snapshot binding, and independent evidence verification.

Intentionally absent: real-provider implementations, brokers, order submission, fills, positions,
paper execution, and every live-order capability. `APPROVED_PAPER` is synthetic governance evidence;
it never authorizes an order and never implies execution readiness.

## Prerequisites

- Docker Desktop or another Docker Engine with Compose v2.
- For host-side development: Python 3.12 and Node.js 22.14 or newer.
- PowerShell on Windows, or `make`/POSIX shell on macOS/Linux.

No data-provider, LLM, broker, or commercial credential is needed for Phase 9. Local and CI evidence
is deterministic and synthetic. LLM use remains limited to structured extraction from text; no LLM
may emit an approval, label, signal, allocation, risk override, or execution instruction.

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

Run Python/frontend linting, type checks, generated-contract drift, and static Phase 9 policy checks:

```powershell
.\scripts\check.ps1
```

Run the isolated full-stack Phase 9 verifier through the single-flight runner. The evidence directory
must be a new absolute path outside this repository:

```powershell
$evidence = Join-Path $env:TEMP ("fable5-phase9-" + [guid]::NewGuid().ToString("N"))
.\.venv\Scripts\python.exe scripts\run_phase_gate.py run --phase 9 --evidence-dir $evidence --timeout-seconds 6300
.\.venv\Scripts\python.exe scripts\run_phase_gate.py verify-evidence --evidence-dir $evidence
```

`follow --evidence-dir $evidence` polls that same run without starting another verifier. Do not retry
or relaunch a delayed or failed run.

The verifier owns one acceptance-only browser timeout profile: inherited Phase 8 runs keep the
20-minute exhaustive-lineage test deadline, while Phase 9 selects 35 minutes for that test alone.
Assertions, coverage, serial order, retries, workers, and application behavior are unchanged.
On Linux, Phase 9 runs Playwright 1.61.1 in the immutable
`mcr.microsoft.com/playwright:v1.61.1-noble@sha256:5b8f294aff9041b7191c34a4bab3ac270157a28774d4b0660e9743297b697e48`
image that matches the frozen Linux visual baselines. The repository mount is read-only, browser
output stays in the container, and the verifier explicitly forwards only the base URL, Phase 9
timeout flag, and `CI=true` as acceptance values. Inherited Phase 8 runs and Phase 9 on Windows
continue to use the native npm command. Ubuntu CI pre-pulls that exact digest before starting the
single-flight evidence clock; the verifier still runs only the digest-qualified image.

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
`0005_phase5` adds versioned evaluation policy, reports, trial/fold/fit/ledger/gate evidence, and
blocked outcomes. `0006_phase6` adds immutable research runs and their complete source, feature,
attempt, score, comparison, extraction, and corroboration lineage. `0007_phase7` adds independently
versioned policy, scope, human authorization, revocation, risk-input, assessment, and check evidence.
The acceptance cycles exercise each reversible boundary and prove all prior rows remain byte-identical.

## Architecture

| Component | Current responsibility | Boundary |
|---|---|---|
| `frontend` | Complete four-mode workflows, exact lineage, simulation disclosure, and read-only research/risk context | no actionable paper-order controls |
| `api` | Typed create/read/list authority plus the Phase 8 GET-only evidence timeline | no broker, order, fill, position, or execution endpoint |
| `migrate` | one-shot Alembic upgrade | API never creates schema at startup |
| `worker` | deterministic extraction on the `research` queue | no trading or execution queue |
| `postgres` | Immutable Phase 1-7 research, evaluation, approval, and risk evidence | no broker, order, fill, position, or execution records |
| `redis` | queue/cache connectivity | no trading queue exists |
| `packages/contracts` | generated OpenAPI TypeScript | never a second schema authority |

No execution adapter, broker dependency, or order-state abstraction is present.

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
- `docs/PHASE_06_RESEARCH_DECISIONS.md`: frozen Phase 6 research-only evidence and gate semantics.
- `docs/PHASE_07_APPROVAL_DECISIONS.md`: frozen Phase 7 eligibility, human-authorization,
  currentness, revocation, scope, risk-check, and non-execution semantics.
- `docs/PHASE_08_UI_DECISIONS.md`: frozen Phase 8 presentation, lineage, generated-client,
  accessibility, and visual-QA semantics.
- `docs/PHASE_09_RELEASE_ACCEPTANCE_DECISIONS.md`: frozen Phase 9 runner, evidence, immutability,
  CI, and cross-platform acceptance semantics.
- `docs/handoffs/PHASE_09.md`: local closure and Ubuntu evidence boundary; it authorizes no later
  phase.
- `services/extraction`: canonical Phase 2 schema, mock extractor, persistence, workflow, and tests.
- `services/mapping`: pure Phase 3 mapper, immutable persistence boundary, and tests.
- `services/data`: vendor-neutral Phase 4 contracts, synthetic adapters, quality gate, immutable
  snapshot materializer/repository/workflow, fixtures, and tests.
- `services/backtester`: deterministic Phase 5 evaluation gates and immutable evidence.
- `services/research`: deterministic Phase 6 research workflows and immutable lineage.
- `services/risk`: fail-closed Phase 7 approval and pre-order-risk assessment, without execution.
- `strategy_specs/`: reserved for source-specific Phase 2 artifacts, not invented post content.

## Validation posture

The research supplement's strategy verdicts are preserved. `docs/RESEARCH_VALIDATION_NOTES.md`
clarifies the exact time geometry for purging/embargo, the additional information needed for DSR and
PBO, point-in-time availability/vintage requirements, cost-model calibration, and provider facts as of
2026-07-13. Numeric promotion thresholds not supplied by the research are required versioned policy
inputs; missing values block promotion rather than receiving optimistic defaults.

## Next step

Complete the local Phase 9 gate and then obtain the required Ubuntu CI evidence at the identical final
SHA and tree. Windows evidence alone does not accept Phase 9. Without separate repository-publication
authority, stop after local verification and report Phase 9 as awaiting CI. Do not push, open a pull
request, merge, tag, publish, deploy, begin a later phase, or add brokers, orders, fills, positions,
paper execution, or any live capability.
