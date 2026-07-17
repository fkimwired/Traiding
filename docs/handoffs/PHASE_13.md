# Phase 13 handoff: point-in-time data qualification

## Objective and explicit exclusions

Implement a manually initiated, synchronous, bounded point-in-time provider-qualification assessment
for the frozen Family A data profile. Add a vendor-neutral read-only adapter, deterministic mock,
exactly one Tiingo candidate implementation, sanitized append-only qualification evidence, one local
capture command, and one historical GET API.

Do not add research snapshot ingestion, strategy execution, feature/label/model/backtest work,
promotion, approval, risk, account, quote, position, broker, order, fill, reconciliation, scheduler,
worker, queue, WebSocket, retry loop, frontend product work, live path, deployment, publication,
release, or Phase 14 work.

## Inputs and source authority

- Accepted Phase 12 commit: `37530a94f841d538a162447cb01ec3e11f375ead`
- Accepted Phase 12 tree: `d8d747ffccb76c3d754cdd2cc14b8ec49fb97287`
- Ubuntu acceptance run: GitHub Actions `29613639340`
- `AGENTS.md`
- `docs/PHASE_13_POINT_IN_TIME_DATA_QUALIFICATION_DECISIONS.md`
- `docs/PHASE_04_DATA_DECISIONS.md`
- `docs/DATA_SOURCES.md`, `docs/EVALS.md`, `docs/RISK_POLICY.md`, and
  `docs/COMPLIANCE_NOTES.md`

Official Tiingo connection, EOD, fundamentals, dividend, split, and terms documentation is authority
only for candidate transport and response facts. It is not proof of entitlement, full historical
coverage, research eligibility, performance, or execution authority.

## Files/directories in scope

Writes are limited to this exact allowlist:

```text
.github/workflows/ci.yml
Makefile
README.md
docs/COMPLIANCE_NOTES.md
docs/DATA_SOURCES.md
docs/IMPLEMENTATION_PLAN.md
docs/PHASE_13_POINT_IN_TIME_DATA_QUALIFICATION_DECISIONS.md
docs/RISK_POLICY.md
docs/handoffs/PHASE_13.md
packages/contracts/openapi.json
packages/contracts/src/api.generated.ts
packages/contracts/src/phase13-contract.type-test.ts
packages/contracts/src/runtime.generated.ts
scripts/capture_point_in_time_data_qualification.py
scripts/check.ps1
scripts/check.sh
scripts/verify_phase1.py
services/api/migrations/versions/0010_phase13_point_in_time_data_qualification.py
services/api/src/fable5_api/data_qualifications.py
services/api/src/fable5_api/main.py
services/api/tests/test_phase13_openapi_contract.py
services/api/tests/test_phase13_routes.py
services/data/src/fable5_data/phase13/__init__.py
services/data/src/fable5_data/phase13/adapters.py
services/data/src/fable5_data/phase13/canonical.py
services/data/src/fable5_data/phase13/contracts.py
services/data/src/fable5_data/phase13/repository.py
services/data/src/fable5_data/phase13/settings.py
services/data/src/fable5_data/phase13/tiingo.py
services/data/src/fable5_data/phase13/workflow.py
services/data/tests/test_phase13_adapters.py
services/data/tests/test_phase13_contracts.py
services/data/tests/test_phase13_postgres.py
services/data/tests/test_phase13_security.py
services/data/tests/test_phase13_workflow.py
services/frontend/e2e/phase8.accessibility.spec.ts
services/frontend/e2e/phase8.visual.spec.ts
tests/test_phase10_static.py
tests/test_phase11_static.py
tests/test_phase12_static.py
tests/test_phase13_migration.py
tests/test_phase13_static.py
tests/test_phase5_postgres.py
tests/test_phase9_static.py
tests/test_repository_policy.py
```

Stop before any write outside this list. In particular, do not modify Compose, dependencies, an
earlier migration, Phase 4-7 implementation, paper service, frontend product code, or snapshot files.

## Contracts and invariants

- Sources: `DETERMINISTIC_MOCK`, `TIINGO_CANDIDATE_READ_ONLY`.
- Outcomes: `MOCK_PROOF_COMPLETE`, `EXTERNAL_SAMPLE_QUALIFIED`, `BLOCKED`.
- Check statuses: `PASS`, `BLOCKED`, `UNCOMPUTABLE`.
- Exact six-capability and twelve-check registries are frozen by the Phase 13 decision document.
- Mock evidence can never validate as `EXTERNAL_SAMPLE_QUALIFIED`.
- All timestamps are timezone-aware UTC and availability never exceeds its decision boundary.
- Raw provider bodies remain transient and are never persisted or returned.
- Every persisted root and child is canonical, hash-bound, append-only, and complete at commit.
- Credentials and rights fail before transport/socket/database construction.
- The GET API performs zero writes and zero external calls.
- All research, promotion, execution, and order authority fields remain false.

## Implementation units

1. Add Phase 13 canonical domains, strict contracts, deterministic mock, credential/rights settings,
   fixed Tiingo candidate transport, and synchronous workflow.
2. Add reversible migration `0010_phase13`, repository, single-flight idempotency, deferred
   completeness, scalar/payload/hash parity, and append-only guards.
3. Add the explicit local external capture command and exactly one historical GET route.
4. Regenerate FastAPI-owned OpenAPI and TypeScript/runtime contracts and add a Phase 13 type proof.
5. Add unit, security, API, migration, PostgreSQL, static, adversarial, network-denial, concurrency,
   and inherited browser regression tests.
6. Extend the phase-aware verifier, root wrappers, Makefile, and mock-only Ubuntu CI through Phase 13.
7. Update data, compliance, risk, implementation, service-status, and repository documentation.

## Acceptance tests

At minimum, prove:

- parser accepts 1-13 and rejects 0/14;
- exact fixed GET origin/method/path/query and no generic transport operation;
- deterministic complete and blocked mock bundles, and mock cannot externally qualify;
- absent/partial credentials or rights create zero transport/socket/database activity;
- external Tiingo candidate preserves membership and delisting gaps as blocked;
- malformed UTF-8/JSON, duplicate keys, non-finite/oversized numbers, redirect, timeout, HTTP failure,
  schema drift, ticker reuse, current-universe substitution, missing inactive/delisted cases, silent
  delisting zero, action lookahead, restatement overwrite, date-only lookahead, orphan/join/duplicate
  grain, reconciliation, and nondeterminism fail closed;
- token and rights canaries are absent from repr, errors, logs, rows, API, contracts, fixtures, build,
  and evidence;
- same-key single flight, conflicting reuse, concurrent creation, root/child tamper, missing/duplicate/
  reordered children, cross-lineage swaps, and direct update/delete/truncate rejection;
- repeated GET is byte-equivalent and causes zero writes/network;
- generated OpenAPI/TypeScript parity and mutation-method absence;
- inherited Phase 8/10/11/12 browser and safety regressions;
- nonempty `0009 -> 0010 -> 0009 -> 0010` preservation; and
- clean pre/post SHA/tree plus empty containers, networks, volumes, browsers, processes, credential
  variables, and temporary captures.

Run locally on Windows:

```powershell
$env:FABLE5_VERIFY_PHASE = "13"
.\scripts\check.ps1
.\scripts\test.ps1
npm run build
.\.venv\Scripts\python.exe scripts\verify_phase1.py --static-only --phase 13
```

After one honest local closure commit, run the full verifier from the clean committed tree:

```powershell
$env:FABLE5_VERIFY_PHASE = "13"
.\.venv\Scripts\python.exe scripts\verify_phase1.py --phase 13
git status --porcelain=v1
```

Ubuntu `phase13-compose` must pass at the same committed SHA/tree before formal acceptance.

## Data/security posture

CI and ordinary acceptance clear all Tiingo token/rights variables and prove only deterministic mock
and blocked paths under active socket denial. No licensed data or real metric enters fixtures,
contracts, logs, screenshots, or evidence. A real external capture requires existing credentials,
independently reviewed use rights, and explicit separate authorization; it must remain private and is
not required for implementation acceptance.

## Migration/rollback

`0010_phase13` directly revises `0009_phase12`, creates exactly the runs/payload-manifests/checks
tables, and installs only Phase 13-owned validation, completeness, lock, timestamp, and append-only
functions/triggers. Downgrade drops those objects only. All 51 inherited tables and relevant earlier
SQL function bodies must be byte-identical across the complete down/up cycle.

## Handoff report

Report final commit/tree, exact changed paths, host-gate counts, static/full verifier results,
deterministic complete/blocked artifact identities and hashes, migration/cleanup evidence, and every
limitation. State separately whether an external capture occurred and whether
`EXTERNAL_SAMPLE_QUALIFIED` was proven. State whether Ubuntu ran at the exact Phase 13 SHA/tree.

## Stop condition

Stop after Phase 13 is accepted on Windows and Ubuntu. Do not begin Phase 14 before that dependency
closes. Do not open a PR, tag, publish, release, deploy, create credentials, perform an unauthorized
external capture, add research-data ingestion, or add any order/live path.
