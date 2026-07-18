# Fable5

Fable5 is a research-to-paper-trading platform scaffold. It translates source claims into testable
research, rejects leakage and cost-fragile results, and allows only manually approved candidates near
a clearly simulated paper environment. It is **not** a live trading bot, does not provide personalized
investment advice, and contains no real-money order path.

## Phase 14 implementation status

The formally accepted Phase 13 identity and the authorized Phase 14 offline eligibility-assessment
surface include:

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
  stage log, atomic manifest, exact SHA/tree/snapshot binding, and independent evidence verification;
- one synchronous, deterministic, server-owned local mock simulation over a frozen synthetic Family A
  fixture, with fresh Phase 7 check re-evaluation captured by a decision-time Phase 10 proof;
- immutable Phase 10 simulation roots, seven ordered checks, and either one exactly reconciled local
  synthetic ledger entry or a blocked artifact with no ledger; and
- dedicated completed/blocked Phase 10 accessibility and visual coverage on Windows and Linux, while
  the unaffected Phase 8 modes and shared layout remain under inherited regression coverage;
- one strict five-field deterministic evidence bundle over a complete existing Phase 10 artifact;
- one GET-only `/v1/local-simulations/{simulation_run_id}/evidence-bundle` operation with generated
  TypeScript contract parity and no body, query, mutation, or work-starting behavior;
- an explicit deterministic local JSON download that uses the already prepared object and makes no
  second API request; and
- a database-free, network-disabled offline verifier that requires an independently supplied digest
  and rejects malformed, inconsistent, completed/blocked, and adversarially tampered evidence;
- a vendor-neutral six-method read-only paper-environment adapter contract, deterministic mock, and
  exactly one fixed Alpaca paper/data implementation using six allowlisted GET requests;
- strict paper-only credential validation before transport, socket, or database construction, with
  no credentials in the API, frontend, logs, artifacts, or generated contracts;
- append-only Phase 12 readiness roots and eight ordered checks, with advisory-lock idempotency,
  deferred completeness, composite hash lineage, and 60-second historical readiness expiry; and
- one GET-only `/v1/paper-shadow-readiness/{readiness_assessment_id}` operation that reads persisted
  sanitized evidence without a database write or external request;
- a vendor-neutral point-in-time qualification boundary, deterministic mock, and exactly one fixed
  Tiingo read-only candidate whose provider bodies remain transient;
- append-only Phase 13 qualification roots, six ordered capability manifests, and twelve ordered
  checks whose mock evidence can never claim external qualification; and
- one GET-only `/v1/point-in-time-data-qualifications/{qualification_id}` operation plus an explicit
  local capture command, with all research, promotion, execution, and order authority held false;
- one database-only Phase 14 assessment that revalidates immutable Phase 13 qualification evidence,
  projects six sanitized capability payloads, and evaluates twelve frozen prerequisite checks;
- append-only Phase 14 eligibility roots whose only outcomes are `MOCK_PROOF_COMPLETE` and
  `BLOCKED`, with no positive research-eligibility state; and
- one GET-only `/v1/research-ingestion-eligibility/{assessment_id}` operation plus an explicit local
  assessment command, with no provider call, ingestion, snapshot, research run, promotion, approval,
  risk mutation, execution, or order path.

Intentionally absent: order intent, order submission/routing, cancellation, reconciliation, real
fills, position mutation, executable strategy parameters, schedulers, retries, and every live-order
capability. Phase 10's fill and position fields are local synthetic ledger calculations only; no
order leaves the process. Phase 12 may inspect sanitized paper-account readiness but persists no raw
account identity, order detail, position detail, quote price, credential, header, or response body.
`APPROVED_PAPER` is synthetic governance evidence and never implies general execution readiness.
Phase 11 adds no migration, simulation execution, replay, mutation, signing, publication,
asynchronous work, or deployment. A valid bundle hash is deterministic integrity evidence, not a
signature, authenticity proof, proof of current authority, or permission to replay or execute.

Phase 13 is formally accepted at commit `47e8e6a9c878a3a8ca7a4b22be3e23ab0357716f`, tree
`d4ac6b6f4b6ba28f5359d8ea85c35845bdb9f285`, after clean Windows acceptance and successful GitHub
Actions run `29623170681` (`preflight`, `unit`, and `phase13-compose`) at that exact identity.
Fake-transport or deterministic-mock results prove only local contract behavior; no external Tiingo
sample, entitlement, full-history coverage, research ingestion, or research eligibility is thereby
proven. Phase 14 remains unaccepted until its complete Windows and Ubuntu gates pass at one later
committed SHA/tree.

## Prerequisites

- Docker Desktop or another Docker Engine with Compose v2.
- For host-side development: Python 3.12 and Node.js 22.14 or newer.
- PowerShell on Windows, or `make`/POSIX shell on macOS/Linux.

No data-provider, LLM, broker, or commercial credential is needed for Phase 14 local or CI
acceptance. Phase 14 is database-only and network-denied. A separately authorized
external qualification capture requires an existing token plus independently reviewed current
use-rights evidence and never falls back to mock evidence.
LLM use remains limited to structured extraction from text; no LLM may emit an approval, label,
signal, allocation, risk override, or execution instruction.

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

Run Python/frontend linting, type checks, generated-contract drift, and static Phase 14 policy checks:

```powershell
$env:FABLE5_VERIFY_PHASE = "14"
.\scripts\check.ps1
```

Run the complete Phase 14 closure sequence from a clean committed tree. The full verifier is direct;
the single-flight runner remains a Phase 9-only historical evidence tool and rejects Phase 14:

```powershell
$env:FABLE5_VERIFY_PHASE = "14"
.\scripts\check.ps1
.\scripts\test.ps1
npm run build
.\.venv\Scripts\python.exe scripts\verify_phase1.py --static-only --phase 14
.\.venv\Scripts\python.exe scripts\verify_phase1.py --phase 14
```

The full verifier fails closed unless the worktree and index are clean before startup and after
cleanup, binds and reports the same commit SHA/tree at both points, and rejects any pre-existing or
remaining `fable5_acceptance_*` container, network, or volume. On Linux, Phase 11 uses
`mcr.microsoft.com/playwright:v1.61.1-noble@sha256:5b8f294aff9041b7191c34a4bab3ac270157a28774d4b0660e9743297b697e48`.
Normal acceptance mounts the repository read-only and keeps browser output inside the container.
Phase 14 rechecks the unaffected inherited Phase 8 modes/shared layout, Phase 10 completed/blocked
paper-simulation behavior, and Phase 11 evidence-download accessibility. Windows uses the native
pinned Playwright installation. Ubuntu CI pre-pulls that digest-qualified image exactly once and
never updates snapshots. Phase 14 does not rewrite the frozen Phase 8 or Phase 10 visual baselines.

### Local evidence verification

Prepare an evidence bundle with the GET-only API or the explicit browser download. Verify the local
file against a digest obtained through an independent trusted channel:

```powershell
.\.venv\Scripts\python.exe scripts\verify_local_simulation_evidence.py `
  --bundle .\local-simulation-evidence.json `
  --expected-bundle-sha256 <lowercase-64-character-sha256>
```

The verifier accepts one regular UTF-8 JSON file of at most 1 MiB. It performs no database access
and denies network and subprocess activity. Numeric coefficient and exponent bounds apply before
model hashing to prevent hostile canonical-decimal amplification. Success emits deterministic sanitized JSON. Invalid
input and invalid invocation exit 2 with no stdout and exact generic stderr
`Local simulation evidence verification failed.`; help exits 0. Verification does not establish a
signature, authenticity, current governance authority, or permission to replay the historical
simulation.

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
`0008_phase10` adds only append-only deterministic local simulation roots, checks, and synthetic
ledger evidence. Phase 11 adds no migration. Its acceptance pins the Alembic head at `0008_phase10`
and proves the bundle API, download, and verifier leave all database rows byte-identical.
`0009_phase12` adds only append-only paper shadow-readiness roots and ordered checks. It does not
reference Phase 7, 10, or 11 artifacts as authority and does not store credentials, raw provider
payloads, order details, position details, or raw quote prices. `0010_phase13` adds only append-only
point-in-time qualification roots, six sanitized capability manifests, and twelve ordered checks.
It neither changes Phase 4 snapshots nor makes any provider observation research-consumable.
`0011_phase14` adds only append-only research-ingestion eligibility roots, six sanitized Phase 13
capability projections, and twelve ordered prerequisite checks. It creates no provider observation,
research snapshot, performance result, promotion, approval, risk clearance, or execution authority.

## Architecture

| Component | Current responsibility | Boundary |
|---|---|---|
| `frontend` | Complete four-mode workflows, exact lineage, one deterministic local simulation action, and explicit local evidence download | no client-authored trade parameters, server export, or real/live controls |
| `api` | Typed create/read/list authority, Phase 8 evidence timeline, terminal local-simulation artifacts, and read-only Phase 11/12/13/14 evidence GETs | no credential loading, vendor call, qualification mutation, order, external routing, or live endpoint |
| `migrate` | one-shot Alembic upgrade | API never creates schema at startup |
| `worker` | deterministic extraction on the `research` queue | no trading or execution queue |
| `postgres` | Immutable Phase 1-7 evidence, Phase 10 local simulation/check/ledger artifacts, sanitized Phase 12 readiness, Phase 13 qualification, and Phase 14 eligibility evidence | no credential, raw provider payload, executable order, fill, or live record |
| `redis` | queue/cache connectivity | no trading queue exists |
| `packages/contracts` | generated OpenAPI TypeScript, including strict Phase 11 bundle, Phase 12 readiness, Phase 13 qualification, and Phase 14 eligibility contracts | never a second schema authority |

No order submission adapter, vendor SDK, execution intent, or order-state abstraction is present.
The Phase 12 adapter exposes only six fixed paper-readiness inspections. Phase 13 adds a separate
qualification-only adapter whose candidate origin, methods, paths, queries, and bounded sample plan
are server-owned and fixed. Phase 14 adds no adapter or transport; it reads immutable Phase 13
evidence from PostgreSQL only.

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
- `docs/PHASE_10_LOCAL_PAPER_DECISIONS.md`: frozen Phase 10 fresh-governance, deterministic fixture,
  immutable ledger, API, UI, and non-execution semantics.
- `docs/handoffs/PHASE_10.md`: direct Windows/Ubuntu Phase 10 closure gate and Phase 11 stop boundary.
- `docs/PHASE_11_PORTABLE_SIMULATION_EVIDENCE_DECISIONS.md`: frozen five-field bundle, GET-only API,
  deterministic download, offline verifier, and non-execution semantics.
- `docs/handoffs/PHASE_11.md`: direct Windows/Ubuntu Phase 11 closure gate and hard stop boundary.
- `docs/PHASE_12_EXTERNAL_PAPER_SHADOW_READINESS_DECISIONS.md`: fixed adapter, credential,
  transport, evidence, persistence, and no-order decisions.
- `docs/handoffs/PHASE_12.md`: Phase 12 implementation/acceptance contract and hard stop boundary.
- `docs/PHASE_13_POINT_IN_TIME_DATA_QUALIFICATION_DECISIONS.md`: frozen qualification profile,
  candidate transport, sanitized evidence, persistence, and false-authority decisions.
- `docs/handoffs/PHASE_13.md`: Phase 13 implementation/acceptance contract and dependency boundary.
- `docs/PHASE_14_RESEARCH_INGESTION_ELIGIBILITY_DECISIONS.md`: frozen offline eligibility policy,
  evidence, persistence, and false-authority decisions.
- `docs/handoffs/PHASE_14.md`: Phase 14 implementation/acceptance contract and hard stop boundary.
- `services/extraction`: canonical Phase 2 schema, mock extractor, persistence, workflow, and tests.
- `services/mapping`: pure Phase 3 mapper, immutable persistence boundary, and tests.
- `services/data`: vendor-neutral Phase 4 contracts and synthetic snapshots plus the isolated Phase
  13 qualification and Phase 14 offline eligibility contracts, repositories, workflows, and tests.
- `services/backtester`: deterministic Phase 5 evaluation gates and immutable evidence.
- `services/research`: deterministic Phase 6 research workflows and immutable lineage.
- `services/risk`: fail-closed Phase 7 approval and pre-order-risk assessment, without execution.
- `services/paper`: deterministic local simulation and Phase 11 bundle evidence, plus the Phase 12
  six-read shadow-readiness contract, deterministic mock, fixed paper adapter, sanitized persistence,
  and explicit local capture workflow; no order or live path.
- `strategy_specs/`: reserved for source-specific Phase 2 artifacts, not invented post content.

## Validation posture

The research supplement's strategy verdicts are preserved. `docs/RESEARCH_VALIDATION_NOTES.md`
clarifies the exact time geometry for purging/embargo, the additional information needed for DSR and
PBO, point-in-time availability/vintage requirements, cost-model calibration, and provider facts as of
2026-07-13. Numeric promotion thresholds not supplied by the research are required versioned policy
inputs; missing values block promotion rather than receiving optimistic defaults.

## Next step

Complete the direct local Phase 14 gate from one honest committed SHA/tree, then require same-SHA
Ubuntu acceptance. Stop after Phase 14. Do not open a pull request, tag, sign, publish, release,
deploy, perform an unauthorized credentialed probe, ingest data, run or promote a strategy, submit or
reconcile an order, begin a later phase, or add any live capability. Until both Phase 14 gates pass,
report Phase 14 as implemented but not formally accepted.
