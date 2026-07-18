# Phase 14 research-ingestion eligibility decisions

## Accepted baseline and authority

Phase 14 starts only from the formally accepted Phase 13 identity:

- Commit: `47e8e6a9c878a3a8ca7a4b22be3e23ab0357716f`
- Tree: `d4ac6b6f4b6ba28f5359d8ea85c35845bdb9f285`
- Windows full Phase 13 verifier: passed at that identity in 3,806.7 seconds.
- Ubuntu GitHub Actions run `29623170681`: `preflight`, `unit`, and
  `phase13-compose` passed at that same identity.

The user authorized implementation through Phase 14. This document narrows that authority to the
smallest safe dependency that the accepted repository can truthfully implement.

## Decision

Phase 14 is a synchronous, database-only assessment of whether one immutable Phase 13
qualification artifact satisfies the frozen prerequisite policy for a later, separately authorized
research-ingestion phase. It creates no research dataset, snapshot, feature, label, signal, return,
trial, evaluation, promotion, approval, risk clearance, paper intent, order, or live path.

The previously proposed non-synthetic Family A research run cannot safely occur in Phase 14:

- Phase 13 persists sanitized sample-qualification evidence only and fixes
  `research_data_eligible=false`.
- Phase 13 covers six bounded sample capabilities; it does not persist licensed observations or the
  full Family A dataset, including macro-regime inputs, sector/liquidity depth, and complete history.
- Phase 4 snapshots, Phase 5 policies, Phase 6 research, and Phase 7 authority remain explicitly
  synthetic QA evidence.
- The frozen Family A specification has no applicable nonzero embargo declaration, and no approved
  non-synthetic policy resolves that prerequisite.
- No independently authenticated current dataset-rights review, production human authority,
  non-synthetic evaluation, or real pre-order-risk evidence exists.

Phase 14 therefore records only a deterministic mock proof or explicit blockers. It adds no positive
research-eligibility, `PASS_RESEARCH`, promotion, approval, execution, or order-authority state.

The only outcomes are:

- `MOCK_PROOF_COMPLETE`: a complete deterministic Phase 13 mock proves the Phase 14 contract,
  persistence, and retrieval path.
- `BLOCKED`: any non-mock, incomplete, unproven, stale, insufficient, or conflicting prerequisite
  remains explicitly blocked.

An external Phase 13 sample, even if separately captured and qualified later, is still not a research
dataset and cannot escape `BLOCKED` in Phase 14. A later phase must separately authorize licensed
data onboarding and define authoritative non-synthetic research policy before adding any positive
eligibility state.

## Frozen policy and check registry

The server-owned policy id is `phase14-research-ingestion-eligibility-policy-v1`. It binds the exact
Phase 13 qualification identity, artifact hash, capture-manifest hash, source kind, outcome, rights
reference when present, all six capability-manifest hashes, all twelve Phase 13 check hashes, the
Phase 14 code SHA, and the canonical request and artifact hashes.

The exact ordered Phase 14 check registry is:

1. `QUALIFICATION_IDENTITY_INTEGRITY`
2. `QUALIFICATION_SOURCE_KIND_ALLOWED`
3. `QUALIFICATION_OUTCOME_ELIGIBLE_OR_MOCK`
4. `CAPABILITY_MANIFEST_COMPLETE_PASSING`
5. `QUALIFICATION_CHECKS_COMPLETE_PASSING`
6. `EXTERNAL_REQUEST_EVIDENCE_COMPLETE_OR_MOCK`
7. `INDEPENDENT_RIGHTS_REFERENCE_PRESENT_OR_MOCK`
8. `USE_RIGHTS_CURRENT_OR_MOCK`
9. `USE_RIGHTS_SCOPE_SUFFICIENT_OR_MOCK`
10. `LICENSED_PAYLOAD_ABSENT`
11. `RESEARCH_SNAPSHOT_ABSENT`
12. `PROMOTION_EXECUTION_AUTHORITY_ABSENT`

Check statuses are exactly `PASS`, `BLOCKED`, and `UNCOMPUTABLE`. Mock-only external and rights
checks may pass only with a closed `mock_not_applicable` reason. Missing authoritative evidence is
`UNCOMPUTABLE`, never inferred as a pass. Any non-pass check produces `BLOCKED`; all twelve passes
can produce only `MOCK_PROOF_COMPLETE`, and only for a complete deterministic Phase 13 mock.

The six ordered child payloads are sanitized projections of the six Phase 13 capability manifests.
They contain only identity, status, reason, count/range, and hash evidence already permitted by
Phase 13. No raw provider body or licensed observation value is copied.

## Authority and data invariants

Every artifact fixes:

```text
external_request_performed = false
provider_payload_persisted = false
research_ingestion_authorized = false
research_snapshot_created = false
research_data_eligible = false
research_run_created = false
research_run_authorized = false
research_executed = false
performance_computed = false
pass_research_granted = false
strategy_promotion_authorized = false
paper_approval_granted = false
strategy_execution_eligible = false
execution_authorized = false
order_submission_authorized = false
live_path_absent = true
no_personalized_investment_advice = true
no_real_performance_claimed = true
```

Phase 14 imports no provider adapter, HTTP/TLS/socket client, credential setting, worker, queue,
scheduler, WebSocket, retry, research workflow, backtester, broker, or paper-execution component.
Active network denial is an acceptance requirement.

## Operator, API, and persistence boundary

The sole creator is:

```text
python scripts/assess_research_ingestion_eligibility.py \
  --idempotency-key KEY \
  --qualification-id UUID \
  --confirm-research-eligibility-only
```

It accepts no provider, URL, host, path, symbol, date, credential, rights override, data file,
strategy, configuration, signal, feature, threshold, action, side, quantity, price, allocation,
broker, order, retry, execution, ingestion, or promotion argument.

The sole API surface is:

```text
GET /v1/research-ingestion-eligibility/{assessment_id}
```

It returns persisted historical evidence only, performs zero writes and zero external calls, and has
typed 200/404/409/422 responses. Mutation methods return 405.

Migration `0011_phase14` directly revises `0010_phase13` and owns only:

```text
research_ingestion_eligibility_assessments
research_ingestion_eligibility_payloads
research_ingestion_eligibility_checks
```

All three tables are append-only and reject `UPDATE`, `DELETE`, and `TRUNCATE`. Composite Phase 13
identifier/hash foreign keys prevent qualification swapping. Deferred completeness requires exactly
six ordered payloads and twelve ordered checks. Database-owned creation time, deterministic UUIDs,
canonical hashes, exact scalar/payload parity, advisory-lock single flight, and complete source
revalidation are mandatory.

The same idempotency key and fingerprint returns the existing artifact without rebuilding it. A
conflicting key reuse fails before Phase 13 source resolution. The same semantic fingerprint under a
different key also fails. Missing, corrupt, cross-lineage, or tampered source evidence leaves no
partial Phase 14 artifact.

## Explicit exclusions

Phase 14 adds no external capture, provider transport, provider credential, licensed payload,
research-data ingestion, Phase 4 snapshot, macro dataset, strategy change, signal/action rule,
backtest, performance metric, DSR/PBO calculation, cost/slippage calibration, promotion, approval,
revocation, risk mutation, broker/account/quote/position surface, paper intent, order, fill,
reconciliation, live enum/origin/path, frontend product control, dependency, Compose change,
publication, deployment, release, tag, PR, or later-phase scaffold.

Accepted Phase 4-7, 12, and 13 implementations and migrations remain byte-identical. Phase 13
`EXTERNAL_SAMPLE_QUALIFIED`, Phase 6 `PASS_RESEARCH`, Phase 7 `APPROVED_PAPER`, and Phase 10/11/12
artifacts are never general execution or ingestion authority.

## Failure, rollback, and acceptance semantics

A blocked Phase 13 artifact, mock/external substitution, incomplete capability/check registry,
missing request evidence, unverified independent rights, stale or insufficient rights, scalar/hash
conflict, policy drift, network attempt, licensed payload presence, snapshot creation, or authority
flag drift produces `BLOCKED` or a sanitized pre-artifact conflict. There is no retry or repair path.

Acceptance proves the nonempty cycle:

```text
0010_phase13 -> 0011_phase14 -> 0010_phase13 -> 0011_phase14
```

Every inherited row and prior SQL function body must remain byte-identical. Downgrade drops only the
three Phase 14 tables plus Phase 14-owned triggers and functions.

Acceptance also requires generated-contract parity; deterministic mock-complete and blocked proofs;
mock-cannot-grant-eligibility proof; active network denial; idempotency/concurrency/tamper/append-only
tests; zero-write GET and source-table proofs; inherited browser regressions; exact clean identity;
and complete Phase 14 acceptance-resource cleanup on Windows and Ubuntu at one committed SHA/tree.

Stop after Phase 14 same-SHA acceptance. Do not perform an external capture, ingest data, run or
promote a strategy, modify governance/risk, add an order path, or begin a later phase.
