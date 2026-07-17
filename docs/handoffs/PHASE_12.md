# Phase 12 handoff: external-paper shadow readiness

## Objective and explicit exclusions

Implement a manually initiated, bounded, synchronous, read-only paper-environment readiness
assessment. Add a vendor-neutral read-only adapter, deterministic mock, one fixed Alpaca paper/data
implementation, append-only sanitized evidence, a local capture command, and one historical GET API.

Do not add any order intent or mutation, strategy eligibility, side/quantity/price/allocation,
submission, cancellation, reconciliation, scheduler, retry loop, WebSocket, real-data research,
production/live path, arbitrary URL, vendor SDK, frontend credential/control surface, Phase 13 work,
publication, deployment, or Phase 12 push.

## Inputs and source authority

- Accepted Phase 11 commit: `b8657abe34d3290a42cb92cb1ad751d0d9d73ad5`
- Accepted Phase 11 tree: `b6f57d6448dea70911f6f80695100ae53c6b6513`
- Ubuntu acceptance run: GitHub Actions `29599118998`
- `AGENTS.md`
- `docs/PHASE_12_EXTERNAL_PAPER_SHADOW_READINESS_DECISIONS.md`
- `docs/PHASE_11_PORTABLE_SIMULATION_EVIDENCE_DECISIONS.md`
- `docs/PHASE_10_LOCAL_PAPER_DECISIONS.md`
- `docs/PHASE_07_APPROVAL_DECISIONS.md`
- `docs/RISK_POLICY.md`, `docs/EVALS.md`, `docs/DATA_SOURCES.md`, and
  `docs/COMPLIANCE_NOTES.md`

Official Alpaca documentation is authority only for the frozen paper/read endpoints, credentials,
response semantics, IEX feed, and simulator limitations. It is not strategy or execution authority.

## Files/directories in scope

Writes are limited to the exact allowlist authorized in the Phase 12 decision package. In particular,
the migration owns only `0009_phase12_external_paper_shadow_readiness.py`; Phase 10/11 contracts and
all earlier migrations remain immutable. No dependency, Compose, environment-example, frontend
product, fixture, or strategy file may change.

## Contracts and invariants

- Source kinds: `DETERMINISTIC_MOCK`, `ALPACA_PAPER_READ_ONLY`.
- Outcomes: `MOCK_PROOF_COMPLETE`, `SHADOW_READY`, `BLOCKED`.
- Check statuses: `PASS`, `BLOCKED`, `UNCOMPUTABLE`.
- Exact eight-check registry and six-inspection registry are frozen by the decision document.
- A mock never validates as `SHADOW_READY`.
- Successful evidence expires exactly 60 seconds after completion.
- All timestamps are timezone-aware UTC.
- Request identity is determined before network activity and contains no secret.
- Every persisted root and child is canonical, hash-bound, append-only, and complete at commit.
- Only fixed `GET` requests can be represented; no generic transport operation is public.
- Credentials are a validated pair and fail before transport/socket/database construction.
- API retrieval causes zero writes and zero external calls.
- Authority literals are always false/true exactly as specified; readiness never authorizes an order.

## Implementation units

1. Add Phase 12 canonical domains, strict contracts, deterministic mock, settings, fixed HTTPS adapter,
   and synchronous workflow.
2. Add reversible migration `0009_phase12`, repository, advisory-lock single-flight idempotency,
   deferred completeness, and append-only guards.
3. Add the local external capture command and exactly one historical GET route.
4. Regenerate FastAPI-owned OpenAPI and TypeScript/runtime contracts and add a Phase 12 type proof.
5. Add unit, security, API, migration, PostgreSQL, static, adversarial, network-denial, and inherited
   browser regression tests.
6. Extend the phase-aware verifier and mock-only Ubuntu CI through Phase 12.
7. Update the implementation, risk, data, compliance, service, and repository status documentation.

## Acceptance tests

At minimum, prove:

- parser accepts 1-12 and rejects 0/13;
- exact six ordered GETs and no representable alternate method/route/host/query;
- deterministic mock and fake external ready/blocked cases;
- missing/partial credentials cause zero transport/socket/database construction;
- malformed, duplicate-key, non-finite, oversized, redirected, stale, blocked, closed, nonempty,
  feed-mismatched, and schema-drift responses fail closed;
- secret canaries are absent from output, errors, logs, rows, API, contracts, fixtures, and builds;
- same-key idempotency avoids another adapter sequence and conflicting reuse fails before reads;
- concurrent writers create one root and exact children;
- root/child tamper, missing/duplicate/reordered checks, and lineage swaps fail;
- direct update/delete/truncate fail;
- GET repetition is byte-equivalent and causes zero writes/network;
- generated OpenAPI/TypeScript parity and mutation-method absence;
- inherited Phase 8/10/11 browser tests and safety language;
- nonempty `0008 -> 0009 -> 0008 -> 0009` preservation; and
- clean pre/post SHA/tree plus empty containers, networks, volumes, browsers, processes, and temp data.

Run locally on Windows:

```powershell
$env:FABLE5_VERIFY_PHASE = "12"
.\scripts\check.ps1
.\scripts\test.ps1
npm run build
.\.venv\Scripts\python.exe scripts\verify_phase1.py --static-only --phase 12
```

After one honest local closure commit, run the full verifier from the clean committed tree:

```powershell
$env:FABLE5_VERIFY_PHASE = "12"
.\.venv\Scripts\python.exe scripts\verify_phase1.py --phase 12
git status --porcelain=v1
```

Ubuntu `phase12-compose` must later pass at the same committed SHA/tree before formal acceptance.

## Data/security posture

CI and normal acceptance are deterministic mock-only and remove both paper credential variables. A
credentialed external probe is separately authorized and must never upload or commit its artifact.
No raw external payload, account identity, secret, order detail, position detail, or raw quote price is
persisted. `AAPL`/IEX is a connectivity probe only. Broker paper observations never replace Fable5's
point-in-time research, cost/slippage, governance, or risk gates.

## Migration/rollback

`0009_phase12` directly revises `0008_phase10`, creates exactly the runs/checks tables, and installs
only Phase 12-owned validation, completeness, and append-only functions/triggers. Downgrade drops
checks, runs, and those functions only. Earlier rows and function bodies must be byte-identical across
the complete down/up cycle.

## Handoff report

Report the final commit/tree, exact changed paths, host-gate counts, static/full verifier results,
cleanup evidence, and all limitations. State separately whether external `SHADOW_READY` was proven
(it is not authorized in this implementation) and whether Ubuntu ran at the Phase 12 SHA (a Phase 12
push is excluded in this run).

## Stop condition

Stop after Phase 12. Do not push the Phase 12 commit, open a pull request, tag, publish, release,
deploy, perform a credentialed external probe, submit or reconcile any order, or begin Phase 13
without separate user authorization.
