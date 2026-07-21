# Fable5

Fable5 is a research-to-paper-trading platform scaffold. It translates source claims into testable
research, rejects leakage and cost-fragile results, and allows only manually approved candidates near
a clearly simulated paper environment. It is **not** a live trading bot, does not provide personalized
investment advice, and contains no real-money order path.

## Phase 23 implementation status

The formally accepted Phase 22 identity and the authorized Phase 23 portable Family A RTDSM
current-use-rights review include:

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
  risk mutation, execution, or order path;
- one canonical Family A non-synthetic research-admission requirements artifact with fifteen ordered
  requirement rows and a nineteen-row current-gap ledger;
- deterministic stdout-only generation and database-free, network-disabled local verification of the
  committed portable JSON; and
- exact `REQUIREMENTS_FROZEN`/`BLOCKED` outcomes that freeze engineering requirements without adding
  research-data eligibility, external authority, a provider payload, snapshot, research run,
  performance result, promotion, risk clearance, execution, or order path;
- one canonical Family A point-in-time source plan with twelve ordered requirements, seven required
  capabilities, six candidate-only rows, seven `NOT_STARTED` future steps, and all nineteen Phase 15
  gap states unchanged;
- deterministic stdout-only generation and database-free, network-disabled local verification of the
  Phase 16 portable JSON; and
- exact `PLAN_FROZEN`/`BLOCKED` outcomes that select no source or product and verify no right,
  external request, payload, dataset, snapshot, evaluation policy, holdout, research result,
  promotion, risk clearance, execution, or order authority;
- one canonical Family A candidate-product inventory bound to the accepted Phase 16 plan and its
  exact `SELECT_CANDIDATE_PRODUCTS` step;
- exact Tiingo, Morningstar/CRSP, SEC EDGAR, Federal Reserve, and LSEG product/reference identities
  frozen from official documentation for independent rights review only; and
- a Step 1 `OUTPUT_FROZEN` state with `candidate_product_inventory_sha256`, while the overall
  artifact remains truthfully `BLOCKED` because delivery, entitlement, current-use rights, complete
  coverage, schema fitness, and every downstream prerequisite remain unproven;
- one canonical technical public-terms review of the exact nine Phase 17 identities, with 24 inert
  official-source metadata rows frozen at `2026-07-19T15:58:18.5305832Z`;
- exact five-state classifications for storage, non-display/internal use, derived data,
  retention/deletion, redistribution, revocation/currentness, delivery, and entitlement; and
- exact `BLOCKED_NO_OPERATIONAL_SELECTION`, Step 1/2 `OUTPUT_FROZEN`, and Step 3-7 `NOT_STARTED`
  states, with no operational provider/account/data request, data capture, database write, research,
  execution, order, or live path;
- one canonical Family A assessment of the two required prior-evidence hashes for Phase 16 Step 3;
- exact `BLOCKED`, assessment `OUTPUT_FROZEN`, and
  `BLOCKED_MISSING_EVALUATION_POLICY_AND_HOLDOUT` states while both expected hashes remain absent;
  and
- explicit proof that Phase 19 produces neither a complete non-synthetic evaluation-policy hash nor
  a confirmation-holdout-definition hash, leaves all nineteen Phase 15 gaps unchanged, and keeps
  Steps 3-7 `NOT_STARTED`;
- one canonical Family A evaluation/holdout input register with twenty ordered input-name rows, ten
  unapplied future-evidence transition rules, six blocked dependency groups, six blocked
  pre-observation construction gates, and eight forbidden substitute classes; and
- exact `BLOCKED`, register `INPUTS_FROZEN`, and
  `BLOCKED_MISSING_OPERATIONAL_AND_DATA_SPECIFIC_INPUTS` states while every input value remains
  absent, both Step 3 future-evidence hashes remain missing, all Phase 15 gaps remain unchanged, and
  Steps 3-7 remain `NOT_STARTED`;
- one canonical Family A operational-composition decision-requirements artifact binding six
  candidate groups, nine candidate-only product/right findings, seven unassigned capabilities, and
  eight absent decision fields without scoring, ranking, recommending, or selecting a product; and
- exact `BLOCKED`, `DECISION_REQUIREMENTS_FROZEN`, and
  `BLOCKED_AWAITING_EXPLICIT_OPERATIONAL_SOURCE_PRODUCT_COMPOSITION` states with every product
  unselected and current-rights-unverified, three downstream dependencies and six gates blocked,
  eight future rules unapplied, and all inherited inputs, Step 3 hashes, gaps, and steps unchanged;
- one additive Philadelphia Fed RTDSM product and candidate-group metadata overlay for later
  independent rights and fitness review, mapped only to `macro_regime_inputs`; and
- exact `BLOCKED` and `CANDIDATE_INVENTORY_AMENDMENT_FROZEN` semantics with the added candidate
  unranked, operationally unselected, current-rights-unverified, and unqualified while every
  accepted Phase 17–21 artifact remains unchanged.

- one canonical public-terms-only technical review of the RTDSM candidate, with three inert official
  citations, one conservative rights finding, and four ordered future-requirement states; and
- exact `BLOCKED`, `PUBLIC_TERMS_RIGHTS_REVIEW_FROZEN`, and
  `BLOCKED_PUBLIC_TERMS_INSUFFICIENT_FOR_PERSISTENT_AUTOMATED_MODEL_USE` semantics, with no rights
  grant, entitlement, product selection, data access, qualification, research, order, or live path.

Intentionally absent: order intent, order submission/routing, cancellation, reconciliation, real
fills, position mutation, executable strategy parameters, schedulers, retries, and every live-order
capability. Phase 10's fill and position fields are local synthetic ledger calculations only; no
order leaves the process. Phase 12 may inspect sanitized paper-account readiness but persists no raw
account identity, order detail, position detail, quote price, credential, header, or response body.
`APPROVED_PAPER` is synthetic governance evidence and never implies general execution readiness.
Phase 11 adds no migration, simulation execution, replay, mutation, signing, publication,
asynchronous work, or deployment. A valid bundle hash is deterministic integrity evidence, not a
signature, authenticity proof, proof of current authority, or permission to replay or execute.

Phase 14 is formally accepted at commit `513fdfd515599e59db6911441aadf1cc30f7352c`, tree
`5870fd4c112b7c7bee05f6240c5cbd950eeaff04`, after clean Windows acceptance and successful GitHub
Actions run `29632035213` (`preflight`, `unit`, and `phase14-compose`) at that exact identity.
Phase 15 is formally accepted at commit `5b3052eb8f020d77cc3750b34190b4b2fa5fc16c`, tree
`7fab5a2b2eb2f8f821b969d9cb031c806e064d28`, after clean Windows acceptance and successful GitHub
Actions run `29661065413` (`preflight`, `unit`, and `phase15-compose`) at that exact identity.
Its portable artifact records deterministic repository requirements only and proves no
external Tiingo sample, entitlement, full-history coverage, non-synthetic evaluation, research
ingestion, or research eligibility. Phase 16 adds a plan for resolving those prerequisites without
selecting a source or performing any future step. Phase 16 is formally accepted at commit
`7c4df26733b4ad13c49c455ea5f28f627012ee44`, tree
`c69b4a60237ae3588f8544272b75becbf0a763e8`, after clean Windows acceptance and successful GitHub
Actions run `29675183969` (`preflight`, `unit`, and `phase16-compose`) at that exact identity.
Phase 17 is formally accepted at commit `fd89d3905e9c2ea12223e30b5822a0fdda795a26`, tree
`f2eb791785dd10cc9316d174505b65eda919fe71`, after clean Windows acceptance and successful GitHub
Actions run `29682173053` (`preflight`, `unit`, and `phase17-compose`) at that exact identity.
Phase 18 performs only the separately authorized technical review of official public terms. Official
web documentation was read during that review; the generated artifact, verifier, tests, and CI do not
browse. A public-rights finding, including the SEC row, is not operational provider/source/product
selection and grants no external-data or later-step authority. Phase 18 is formally accepted at
commit `16aac187fc3dbd6015306603c18be6e08cea8e4e`, tree
`b36ae615f13f39d0e661f18d1cc61e009b1aacf7`, after clean Windows acceptance and successful GitHub
Actions run `29698090468` (`preflight`, `unit`, and `phase18-compose`) at that exact identity.
Phase 19 assesses only the still-missing Step 3 prerequisites; it does not freeze an incomplete
policy or holdout and cannot start qualification. Phase 19 is formally accepted at commit
`86ddcafacff43b42fe56346745d7e6f08eaf3a52`, tree
`6b6c2693a969e80cac9013d441ba607565d8914a`, after clean Windows acceptance and successful GitHub
Actions run `29705348113` (`preflight`, `unit`, and `phase19-compose`) at that exact identity. Phase
20 names only missing operational/data-specific inputs and future transition constraints; it
supplies no value, applies no transition, creates neither reserved evidence hash, and cannot start
qualification. Phase 20 is formally accepted at commit
`01ed1ff17b91ba6961e02cdf1df3aa3e6be4859a`, tree
`b7a68998f1c99ed8b19ab08ae8a725726f04c423`, after clean Windows acceptance and successful GitHub
Actions run `29724765420` (`preflight`, `unit`, and `phase20-compose`) at that exact identity.
Phase 21 interprets only committed evidence. Its zero selected and zero current-rights-verified
bindings do not claim external unavailability, make an eligibility/legal conclusion, or permanently
reject any product. Phase 21 is formally accepted at commit
`a25ffb5cb68014c301a588c0e8cf7c7f18914e0a`, tree
`8744604b486dd7398cd8c5a003fe7c7b083fde86`, after clean Windows acceptance and successful GitHub
Actions run `29759697662` (`preflight`, `unit`, and `phase21-compose`) at that exact identity.
Phase 22 is formally accepted at commit `1c07fbe8e23950e8c9f910b30473c900c0bf3e21`, tree
`1261f5a9da883e14a894b33e583068681f8cf459`, after clean Windows acceptance and successful push and
pull-request Ubuntu workflows (`29782670821` and `29782755681`). PR #2 was merged to `main` as
`7f3bf3df029a894660f0e47dda1056bd32dca297`, whose tree is byte-identical to the accepted tree.

## Prerequisites

- Docker Desktop or another Docker Engine with Compose v2.
- For host-side development: Python 3.12 and Node.js 22.14 or newer.
- PowerShell on Windows, or `make`/POSIX shell on macOS/Linux.

No data-provider, LLM, broker, or commercial credential is needed for Phase 23 local or CI
acceptance. The Phase 23 artifact operations are portable, database-free, and network-denied; the
full closure gate still starts the inherited Compose/PostgreSQL stack solely to prove zero schema or
row drift. A separately authorized
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

Run Python/frontend linting, type checks, generated-contract drift, and static Phase 23 policy checks:

```powershell
$env:FABLE5_VERIFY_PHASE = "23"
.\scripts\check.ps1
```

Run the complete Phase 23 closure sequence from a clean committed tree. The full verifier is direct;
the single-flight runner remains a Phase 9-only historical evidence tool and rejects Phase 23:

```powershell
$env:FABLE5_VERIFY_PHASE = "23"
.\scripts\check.ps1
.\scripts\test.ps1
npm run build
.\.venv\Scripts\python.exe scripts\verify_phase1.py --static-only --phase 23
.\.venv\Scripts\python.exe scripts\verify_phase1.py --phase 23
```

The full verifier fails closed unless the worktree and index are clean before startup and after
cleanup, binds and reports the same commit SHA/tree at both points, and rejects any pre-existing or
remaining `fable5_acceptance_*` container, network, or volume. On Linux, Phase 11 uses
`mcr.microsoft.com/playwright:v1.61.1-noble@sha256:5b8f294aff9041b7191c34a4bab3ac270157a28774d4b0660e9743297b697e48`.
Normal acceptance mounts the repository read-only and keeps browser output inside the container.
Phase 23 rechecks the unaffected inherited Phase 8 modes/shared layout, Phase 10 completed/blocked
paper-simulation behavior, and Phase 11 evidence-download accessibility. Windows uses the native
pinned Playwright installation. Ubuntu CI pre-pulls that digest-qualified image exactly once and
never updates snapshots. Phase 23 does not rewrite the frozen Phase 8 or Phase 10 visual baselines.

### Family A admission specification

Generate the frozen artifact to stdout only:

```powershell
.\.venv\Scripts\python.exe scripts\generate_family_a_research_admission_specification.py `
  --confirm-requirements-only
```

Verify a supplied regular UTF-8 JSON file offline:

```powershell
.\.venv\Scripts\python.exe scripts\verify_family_a_research_admission_specification.py `
  --specification .\docs\PHASE_15_FAMILY_A_RESEARCH_ADMISSION_SPECIFICATION.json
```

The generator is byte-deterministic and writes only canonical JSON plus one newline to stdout. The
verifier accepts no expected-hash, repair, authority, provider, credential, data, or output override.
Both deny database, network, subprocess, clock, randomness, credential, provider, research, broker,
and execution dependencies. `REQUIREMENTS_FROZEN` means only that the engineering requirements and
current gap ledger reproduce; it is not data-rights approval or research-data eligibility.

### Family A point-in-time source plan

Generate the frozen source plan to stdout only:

```powershell
.\.venv\Scripts\python.exe scripts\generate_family_a_point_in_time_source_plan.py `
  --confirm-plan-only
```

Verify one supplied regular canonical UTF-8 JSON plan offline:

```powershell
.\.venv\Scripts\python.exe scripts\verify_family_a_point_in_time_source_plan.py `
  --plan .\docs\PHASE_16_FAMILY_A_POINT_IN_TIME_SOURCE_PLAN.json
```

`PLAN_FROZEN` means only that the exact source-plan requirements, candidate-only facts, future
steps, and unchanged Phase 15 gap bindings reproduce. All candidates remain unselected and
rights-unverified, every future step remains `NOT_STARTED`, and no credential, network, provider,
data, database, evaluation, research, risk, broker, or execution dependency is permitted.

### Family A current-use-rights review

Generate the frozen public-terms review to stdout only:

```powershell
.\.venv\Scripts\python.exe scripts\generate_family_a_current_use_rights_review.py `
  --confirm-public-terms-review-only
```

Verify one supplied regular canonical UTF-8 JSON review offline:

```powershell
.\.venv\Scripts\python.exe scripts\verify_family_a_current_use_rights_review.py `
  --review .\docs\PHASE_18_FAMILY_A_CURRENT_USE_RIGHTS_REVIEW.json
```

The official pages were reviewed read-only at the fixed artifact timestamp, but ordinary generation,
verification, tests, and CI do not browse. `BLOCKED_NO_OPERATIONAL_SELECTION` is the only valid
aggregate outcome: SEC public reuse support does not prove fitness or selection; FRED prohibits the
planned non-display software/system/model use and persistence; and all operational authority remains
false.

### Family A Step 3 prerequisite assessment

Generate the frozen blocked assessment to stdout only:

```powershell
.\.venv\Scripts\python.exe scripts\generate_family_a_step3_prerequisite_assessment.py `
  --confirm-prerequisite-assessment-only
```

Verify one supplied regular canonical UTF-8 JSON assessment offline:

```powershell
.\.venv\Scripts\python.exe scripts\verify_family_a_step3_prerequisite_assessment.py `
  --assessment .\docs\PHASE_19_FAMILY_A_STEP3_PREREQUISITE_ASSESSMENT.json
```

The only valid conclusion is `BLOCKED_MISSING_EVALUATION_POLICY_AND_HOLDOUT`. The artifact names
`non_synthetic_evaluation_policy_sha256` and `confirmation_holdout_definition_sha256` only as missing
future evidence and supplies no value for either. It leaves all Phase 15 gap states unchanged,
Steps 1/2 `OUTPUT_FROZEN`, Steps 3-7 `NOT_STARTED`, and every data/research/execution authority false.

### Family A evaluation/holdout input register

Generate the frozen blocked input register to stdout only:

```powershell
.\.venv\Scripts\python.exe scripts\generate_family_a_evaluation_holdout_input_register.py `
  --confirm-input-register-only
```

Verify one supplied regular canonical UTF-8 JSON register offline:

```powershell
.\.venv\Scripts\python.exe scripts\verify_family_a_evaluation_holdout_input_register.py `
  --register .\docs\PHASE_20_FAMILY_A_EVALUATION_HOLDOUT_INPUT_REGISTER.json
```

The only valid conclusion is `BLOCKED_MISSING_OPERATIONAL_AND_DATA_SPECIFIC_INPUTS` with
`register_state=INPUTS_FROZEN`. The artifact carries twenty field-name-only input requirements, ten
unapplied transition rules, blocked construction dependencies/gates, and forbidden substitutions.
It supplies no input value or reserved Step 3 hash, preserves every Phase 15 gap and Phase 16 step,
and grants no external-data, research, risk, execution, or order authority.

### Family A operational-composition decision requirements

Generate the frozen blocked requirements artifact to stdout only:

```powershell
.\.venv\Scripts\python.exe `
  scripts\generate_family_a_operational_composition_decision_requirements.py `
  --confirm-decision-requirements-only
```

Verify one supplied regular canonical UTF-8 JSON artifact offline:

```powershell
.\.venv\Scripts\python.exe `
  scripts\verify_family_a_operational_composition_decision_requirements.py `
  --requirements `
  .\docs\PHASE_21_FAMILY_A_OPERATIONAL_COMPOSITION_DECISION_REQUIREMENTS.json
```

The only valid conclusion is
`BLOCKED_AWAITING_EXPLICIT_OPERATIONAL_SOURCE_PRODUCT_COMPOSITION` with
`requirements_state=DECISION_REQUIREMENTS_FROZEN`. Six candidate groups and nine product-rights
findings remain unselected, seven capabilities remain `UNASSIGNED`, and all eight decision fields
remain absent. The zero selected and zero current-rights-verified bindings describe accepted
repository evidence only; they are not a recommendation, eligibility/legal conclusion, or
external-currentness claim. No lifecycle identity can substitute for a human decision or authorize
provider, data, policy, holdout, research, risk, execution, or order activity.

### Family A macro-vintage candidate inventory amendment

Generate the frozen blocked amendment artifact to stdout only:

```powershell
.\.venv\Scripts\python.exe `
  scripts\generate_family_a_macro_vintage_candidate_inventory_amendment.py `
  --confirm-candidate-inventory-amendment-only
```

Verify one supplied regular canonical UTF-8 JSON artifact offline:

```powershell
.\.venv\Scripts\python.exe `
  scripts\verify_family_a_macro_vintage_candidate_inventory_amendment.py `
  --amendment `
  .\docs\PHASE_22_FAMILY_A_MACRO_VINTAGE_CANDIDATE_INVENTORY_AMENDMENT.json
```

The only valid result is `BLOCKED` with
`amendment_state=CANDIDATE_INVENTORY_AMENDMENT_FROZEN`. The sole RTDSM entry is candidate-only,
unranked, operationally unselected, current-rights-unverified, and unqualified. Validity proves
portable metadata integrity only; it grants no product recommendation, entitlement, data access,
composition value, research, execution, or order authority.

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
Phase 15 adds no migration and keeps Alembic head at `0011_phase14`. Its generator and verifier are
database-free; acceptance proves the complete inherited schema, rows, SQL functions, OpenAPI, and
generated contracts remain unchanged. Phases 16-21 also add no migration, API, or generated
contract; their portable operations preserve the same head and all 57 inherited tables/functions.

## Architecture

| Component | Current responsibility | Boundary |
|---|---|---|
| `frontend` | Complete four-mode workflows, exact lineage, one deterministic local simulation action, and explicit local evidence download | no client-authored trade parameters, server export, or real/live controls |
| `api` | Typed create/read/list authority, Phase 8 evidence timeline, terminal local-simulation artifacts, and read-only Phase 11/12/13/14 evidence GETs | unchanged by Phases 15-21; no credential loading, vendor call, qualification mutation, order, external routing, or live endpoint |
| `migrate` | one-shot Alembic upgrade | API never creates schema at startup |
| `worker` | deterministic extraction on the `research` queue | no trading or execution queue |
| `postgres` | Immutable Phase 1-7 evidence, Phase 10 local simulation/check/ledger artifacts, sanitized Phase 12 readiness, Phase 13 qualification, and Phase 14 eligibility evidence | unchanged by database-free Phases 15-21; no credential, raw provider payload, executable order, fill, or live record |
| `redis` | queue/cache connectivity | no trading queue exists |
| `packages/contracts` | generated OpenAPI TypeScript, including strict Phase 11 bundle, Phase 12 readiness, Phase 13 qualification, and Phase 14 eligibility contracts | unchanged by Phases 15-21; never a second schema authority |

No order submission adapter, vendor SDK, execution intent, or order-state abstraction is present.
The Phase 12 adapter exposes only six fixed paper-readiness inspections. Phase 13 adds a separate
qualification-only adapter whose candidate origin, methods, paths, queries, and bounded sample plan
are server-owned and fixed. Phase 14 adds no adapter or transport; it reads immutable Phase 13
evidence from PostgreSQL only.

Phase 15 adds only pure Family A admission-specification contracts, a committed canonical JSON
artifact, and offline generator/verifier commands. It adds no API, provider, database, research, risk,
paper, or frontend product surface.

Phase 16 adds only pure Family A point-in-time source-plan contracts, a committed canonical JSON
artifact, and offline generator/verifier commands. It selects no source, performs no future step, and
adds no API, provider, database, evaluation, research, risk, paper, or frontend product surface.

Phase 17 adds only a pure Family A candidate-product metadata inventory, a committed canonical JSON
artifact, and offline generator/verifier commands. Its exact product identities are selected only
for future independent rights review. It adds no operational provider/source/product selection,
credential, transport, data, API, database, evaluation, research, risk, paper, or frontend product
surface.

Phase 18 adds only a pure Family A public-terms rights-review artifact, contracts, and offline
generator/verifier commands. It freezes a fixed-time technical review and blocked result; it adds no
operational selection, credential, provider/account/data request, data, API, database, evaluation,
research, risk, paper, order, or frontend product surface.

Phase 19 adds only a pure Family A Step 3 prerequisite-assessment artifact, contracts, and offline
generator/verifier commands. It freezes the truthful absence of the complete evaluation-policy and
holdout-definition hashes; it adds no policy, holdout, data, API, database, research, risk, paper,
order, or frontend product surface.

Phase 20 adds only a pure Family A evaluation/holdout input register, a committed canonical JSON
artifact, and offline generator/verifier commands. It freezes twenty required-input names and ten
future-only transition rules while supplying no input value and applying no transition. Its exact
result is `BLOCKED` / `INPUTS_FROZEN` /
`BLOCKED_MISSING_OPERATIONAL_AND_DATA_SPECIFIC_INPUTS`; it adds no policy, holdout, provider,
credential, data, API, database, research, risk, paper, order, or frontend product surface.

Phase 21 adds only pure Family A operational-composition decision requirements, a committed
canonical JSON artifact, and offline generator/verifier commands. It binds already committed
candidate/right facts without selecting, ranking, recommending, contacting, or loading anything.
It adds no provider, counsel, credential, account, license, data, policy, holdout, Step 3, API,
database, research, risk, paper, order, runtime, deployment configuration, or frontend product
surface.

Phase 22 adds only the accepted RTDSM candidate metadata overlay. Phase 23 adds only its
public-terms technical rights review. The Phase 23 result is conservatively blocked because the
public pages do not expressly resolve the exact persistent-storage, automated-model, derived-data,
retention/deletion, attribution, and third-party-content rights needed for operational use.

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
- `docs/PHASE_15_FAMILY_A_RESEARCH_ADMISSION_SPECIFICATION_DECISIONS.md`: frozen portable Family A
  requirements, current-gap, canonicalization, authority, and no-ingestion decisions.
- `docs/handoffs/PHASE_15.md`: Phase 15 implementation/acceptance contract and hard stop boundary.
- `docs/PHASE_16_FAMILY_A_POINT_IN_TIME_SOURCE_PLAN_DECISIONS.md`: frozen source-plan registries,
  candidate-only facts, future steps, unchanged gaps, authority, and no-data decisions.
- `docs/handoffs/PHASE_16.md`: Phase 16 implementation/acceptance contract and hard stop boundary.
- `docs/PHASE_17_FAMILY_A_CANDIDATE_PRODUCT_INVENTORY_DECISIONS.md`: frozen product identities,
  official-source facts, review-selection semantics, blocked outcome, and no-data decisions.
- `docs/handoffs/PHASE_17.md`: Phase 17 implementation/acceptance contract and hard stop boundary.
- `docs/PHASE_18_FAMILY_A_CURRENT_USE_RIGHTS_REVIEW_DECISIONS.md`: fixed official-source metadata,
  exact rights classifications, blocked outcome, currentness limits, and false-authority decisions.
- `docs/handoffs/PHASE_18.md`: Phase 18 implementation/acceptance contract and Phase 19 stop boundary.
- `docs/PHASE_19_FAMILY_A_STEP3_PREREQUISITE_ASSESSMENT_DECISIONS.md`: exact missing-prerequisite,
  unchanged-gap/step, assessment-only, and false-authority decisions.
- `docs/handoffs/PHASE_19.md`: Phase 19 implementation/acceptance contract and Phase 20 stop boundary.
- `docs/PHASE_20_FAMILY_A_EVALUATION_HOLDOUT_INPUT_REGISTER_DECISIONS.md`: exact input-name,
  future-transition, unchanged-gap/step, register-only, and false-authority decisions.
- `docs/handoffs/PHASE_20.md`: Phase 20 implementation/acceptance contract and Phase 21 stop boundary.
- `docs/PHASE_21_FAMILY_A_OPERATIONAL_COMPOSITION_DECISION_REQUIREMENTS_DECISIONS.md`: exact
  candidate/right bindings, unassigned capabilities, absent decision fields, blocked dependencies,
  future rules, lifecycle non-substitution, and false-authority decisions.
- `docs/handoffs/PHASE_21.md`: Phase 21 implementation/acceptance contract and Phase 22 stop boundary.
- `docs/PHASE_22_FAMILY_A_MACRO_VINTAGE_CANDIDATE_INVENTORY_AMENDMENT_DECISIONS.md`: exact
  additive RTDSM candidate, official-source metadata, conservative limitations, unchanged-prior-
  evidence, blocked-result, and false-authority decisions.
- `docs/handoffs/PHASE_22.md`: Phase 22 implementation/acceptance contract and Phase 23 stop boundary.
- `docs/PHASE_23_FAMILY_A_RTDSM_CURRENT_USE_RIGHTS_REVIEW_DECISIONS.md`: exact public-terms
  evidence, conservative classifications, blocked result, deterministic identities, and
  false-authority boundary.
- `docs/handoffs/PHASE_23.md`: Phase 23 implementation/acceptance contract and Phase 24 stop boundary.
- `docs/PHASE_24_FAMILY_A_RTDSM_RIGHTS_CLARIFICATION_REQUIREMENTS_DECISIONS.md`: exact proposed-use,
  clarification-question, acceptable-evidence, transition-rule, and false-authority decisions.
- `docs/handoffs/PHASE_24.md`: Phase 24 implementation/acceptance contract and Phase 25 stop boundary.
- `services/extraction`: canonical Phase 2 schema, mock extractor, persistence, workflow, and tests.
- `services/mapping`: pure Phase 3 mapper, immutable persistence boundary, and tests.
- `services/data`: vendor-neutral Phase 4 contracts and synthetic snapshots plus isolated Phase 13
  qualification, Phase 14 offline eligibility, and pure Phase 15 portable admission-specification
  plus Phase 16 portable source-plan, Phase 17 candidate inventory, Phase 18 public-terms review,
  Phase 19 Step 3 prerequisite assessment, Phase 20 evaluation/holdout input-register, and Phase 21
  operational-composition decision-requirements, the Phase 22 additive macro-vintage candidate
  inventory amendment, the Phase 23 RTDSM public-terms rights review, and the Phase 24 RTDSM
  rights-clarification requirements contracts and tests.
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

Phase 23 is formally accepted at commit `d8d8d63a79457c7a54e0a3738a75f4eb613c602f`, tree
`4f3da35d31f352ea92d5f715149e0e439a57af3b`, and merge commit
`53d9f8641d98c729447661af9b7e561073a52226`. Complete the direct local Phase 24 gate from one
honest committed SHA/tree, then require same-SHA Ubuntu acceptance before formal acceptance. Stop
after Phase 24; do not send the clarification packet, contact a provider/rights holder/BLS/counsel,
claim rights, use credentials, inspect or request data, perform fitness or BLS reconciliation,
select an operational composition, run research, mutate risk, submit an order, begin Phase 25,
publish Phase 24, or add any live capability without separate authority.
