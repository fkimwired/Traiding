# Phase 10 deterministic local paper-simulation handoff

## Authorized baseline and boundary

Phase 10 starts from accepted Phase 9 commit
`12a87e9dfb71afd7bb02d1f947ffea63be56a0a3`, tree
`472792e0f53fc5c29ef8d4d73bdef60d6f25a1c9`. The governing design is
`docs/PHASE_10_LOCAL_PAPER_DECISIONS.md`.

This phase owns one synchronous deterministic simulation over a frozen synthetic Family A fixture.
It adds no broker/provider adapter, account, credential, external request, real instrument, real
quote, asynchronous execution, deployment, or live path. The request contains only an immutable
Phase 7 assessment reference and an idempotency key. The server owns every simulation value.

`PASS_RESEARCH` remains research-only. A historical `APPROVED_PAPER` assessment is only a source
reference: the workflow reruns the exact Phase 7 checks immediately before simulation. Every Phase
10 check must pass before the sole synthetic ledger entry may exist. Any resolved but no-longer-current
source persists `BLOCKED` with no ledger.

Phase 7 content-addressing may return the same assessment identity when the immutable evidence and
check states are unchanged. Freshness is therefore recorded by a separate Phase 10 revalidation
proof bound to the decision time, idempotency key, resolved Phase 7 state, and code SHA; the workflow
does not fabricate a new Phase 7 identity.

## Owned contract

FastAPI owns exactly:

```text
POST /v1/local-simulations
GET  /v1/local-simulations
GET  /v1/local-simulations/{simulation_run_id}
```

Alembic `0008_phase10` owns exactly `paper_simulation_runs`, `paper_simulation_checks`, and
`paper_simulation_ledger_entries`. All three are append-only. Deferred database validation requires
the exact ordered seven-check registry and either one fully reconciled ledger for
`SIMULATED_COMPLETE` or no ledger for `BLOCKED`. Downgrade removes only these Phase 10 objects.

The UI exposes one assessment selector and `Run deterministic local simulation`; it exposes no
symbol, side, quantity, price, notional, risk override, or outcome control. All states remain visibly
`SIMULATED` and `LOCAL MOCK`, with no external routing, no live path, no real-performance claim, and
no personalized investment advice.

## Closure gate

Run from a clean committed Phase 10 tree with the phase set inside the same shell:

```powershell
$env:FABLE5_VERIFY_PHASE = "10"
.\scripts\check.ps1
.\scripts\test.ps1
npm run build
.\.venv\Scripts\python.exe scripts\verify_phase1.py --static-only --phase 10
.\.venv\Scripts\python.exe scripts\verify_phase1.py --phase 10
```

The full verifier is direct. `scripts/run_phase_gate.py` remains the accepted Phase 9 evidence
runner and must continue rejecting Phase 10. The Phase 10 verifier must prove the reversible
`0007 -> 0008 -> 0007 -> 0008` cycle over nonempty Phase 1-7 rows, earlier SQL-body fidelity,
completed and revoked-source blocked APIs, concurrent idempotency, direct-SQL completeness and
immutability, targeted accessibility/visual behavior, zero browser database writes, and complete
Compose cleanup.

Static-only verification remains usable while developing an allowlisted Phase 10 diff. The full
verifier is a closure gate: it rejects a dirty worktree or index before startup and after cleanup,
prints the bound `HEAD` SHA/tree at both points, and fails if either identity changes. It also rejects
any pre-existing or remaining container, network, or volume in the complete
`fable5_acceptance_*` verifier namespace, not only resources owned by the current random project.
Phase 10 reruns the unaffected Phase 8 modes and shared-layout browser contract before running the
dedicated Phase 10 paper-simulation browser contract; Phase 10's paper control intentionally
supersedes only the historical Phase 8 no-control assertion.

The Ubuntu `phase10-compose` job must pass at the identical closure SHA/tree. Windows acceptance is
not a substitute for Ubuntu acceptance. Stop on any dirty pre/post state, residual container/network/
volume, generated-contract drift, snapshot mismatch, migration mutation, missing safety literal, or
unexpected external/live surface.

## Stop condition and next planning gate

Phase 10 is accepted only after the local gates and Ubuntu CI pass at one committed identity. No
Phase 11 implementation is authorized by this handoff. After acceptance, the only permitted next
work is a read-only Phase 11 decision plan that preserves the paper-only, mock-only boundary until
the user separately authorizes a named implementation phase. Do not tag, release, deploy, add real
providers/data, or create any real-money path.
