# Implementation plan and handoff protocol

## Architecture decision

Use a monorepo with a thin control plane first. FastAPI owns schemas, OpenAPI generates shared
TypeScript contracts, PostgreSQL owns durable state, Redis/RQ owns background research work, and
Next.js owns the user interface. Provider and model code arrive only in the phase that defines their
contracts and acceptance tests.

## Dependency sequence

```text
Phase 1 control plane
  -> Phase 2 source extraction and persistence
  -> Phase 3 deterministic strategy canon mapping
  -> Phase 4 point-in-time provider interfaces and mocks
  -> Phase 5 evaluation engine and fail-closed gates
  -> Phase 6 A/B/C research strategies on mock/approved data
  -> Phase 7 risk, approval, audit, and paper-only adapter
  -> Phase 8 complete product workflows and visual QA
```

No phase may bypass an earlier contract. Deferred/rejected ideas remain visible research decisions but
do not receive executable scaffolds.

## Phase ownership and definitions of done

| Phase | Owned deliverables | Machine gate |
|---|---|---|
| 1 | Compose, API liveness/readiness, migrations, idle queue, shared contract, navigation, docs, CI | root check/test commands + isolated Compose verifier |
| 2 | Lossless input/source records, typed extraction card, six archetype fixtures, persistence, memos | unit/contract/migration tests; every output traces to immutable source input |
| 3 | deterministic family/verdict mapper and rationale UI | table-driven mapping tests cover build/defer/reject/non-testable outcomes |
| 4 | typed adapters, snapshots, PIT semantics, deterministic mocks, graceful credentials | provider conformance suite and mock end-to-end data run |
| 5 | nested walk-forward, trial registry, DSR, PBO, leakage, costs/stress, reports | all 12 checks in `docs/EVALS.md` section 14 |
| 6 | research-only A/B/C pipelines and explainable outputs | mock runs pass/failed reports; no paper approval or live path |
| 7 | limits, approvals, kill switch, immutable decisions, paper-only adapter | pre-order risk tests, endpoint allowlist, approval/kill-switch integration tests |
| 8 | full four-mode workflows and traceability | source-to-audit route in ≤2 clicks; visible gate precedence; accessibility/visual tests |

## Required handoff template

Every implementer task must include:

1. **Objective and explicit exclusions.** Name the one phase and list behavior that must remain absent.
2. **Inputs/source authority.** Link the governing docs, schemas, fixtures, and prior-phase outputs.
3. **Files/directories in scope.** Identify allowed writes and preserve unrelated/user files.
4. **Contracts and invariants.** State types, timestamps, identities, state transitions, failure modes,
   and audit fields.
5. **Implementation units.** Each bounded unit names its output and owner boundary.
6. **Acceptance tests.** Give literal commands and assertions, including negative/adversarial cases.
7. **Data/security posture.** Specify mock/real source, credentials, licensing, and secret behavior.
8. **Migration/rollback.** Require reversible schema changes and backward compatibility where needed.
9. **Handoff report.** Files changed, commands/results, known limitations, and the next phase prompt.
10. **Stop condition.** Stop immediately after the named phase; do not anticipate later behavior.

The ready-to-run Phase 2 handoff is in `docs/handoffs/PHASE_02.md`.

