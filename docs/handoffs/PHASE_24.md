# Phase 24 Family A RTDSM rights-clarification requirements handoff

## Objective and exclusions

Freeze one deterministic, portable, database-free, network-disabled requirements package for a
later independent RTDSM current-use-rights clarification. The exact result is `BLOCKED` /
`RIGHTS_CLARIFICATION_REQUIREMENTS_FROZEN` /
`BLOCKED_AWAITING_INDEPENDENT_CURRENT_USE_RIGHTS_CLARIFICATION`.

This phase records proposed-use disclosures, questions, acceptable evidence, and transition rules.
It does not perform outreach, receive or evaluate an answer, grant rights, select a product, inspect
data, qualify a source, create a policy/holdout, run research, change risk, or execute an order.

## Accepted input identity

```text
accepted Phase 23 commit: d8d8d63a79457c7a54e0a3738a75f4eb613c602f
accepted Phase 23 tree:   4f3da35d31f352ea92d5f715149e0e439a57af3b
Phase 23 merge commit:    53d9f8641d98c729447661af9b7e561073a52226
Phase 23 artifact id:     e4fbd5af-c5ad-51fb-92cb-7308fafd017a
Phase 23 artifact SHA:    aafb6deadff7b4cd4f9b4e7c98c8ac31f0d957a60b1d5be59f3d7ebf2679cd2c
```

Preserve the Phase 23 artifact and domain byte-for-byte. The merge commit must remain an ancestor
and must retain the accepted Phase 23 implementation as a parent at the same tree.

## Exact write allowlist

Write only the Phase 24 domain, artifact, decisions/handoff, generator/verifier, focused/static
tests, phase-aware verification/CI wrappers, inherited browser phase selectors, PostgreSQL head
mapping, repository status documentation, and historical static assertions that must recognize the
new active phase. No API, migration, schema, contract, dependency, Compose, runtime, provider, data,
research, risk, paper-order, or product behavior file may change.

## Required implementation and acceptance

- Strict frozen 8/10/6/7 disclosure/question/evidence/rule registries and aggregate artifact.
- Separate row, manifest, policy, and artifact hash domains with exact Phase 23 lineage.
- Stdout-only generator requiring `--confirm-rights-clarification-requirements-only`.
- Bounded offline verifier requiring `--requirements PATH` with sanitized failure behavior.
- Static/full Phase 24 acceptance inheriting Phase 23, proving zero schema/data writes, canonical
  parity, network/subprocess denial, and unchanged runtime surfaces.

Artifact output belongs only at
`docs/PHASE_24_FAMILY_A_RTDSM_RIGHTS_CLARIFICATION_REQUIREMENTS.json`.

Run focused tests, repository lint/format/type checks, and
`python scripts/verify_phase1.py --static-only --phase 24`. After an intentional commit, run the
complete Windows Phase 24 Compose gate and require Ubuntu `preflight`, `unit`, and
`phase24-compose` at the exact same commit/tree.

## Stop condition

Stop after Phase 24 implementation and same-SHA Windows/Ubuntu acceptance. Do not contact or send
the packet to any provider, rights holder, BLS, or counsel; use a login, credential, entitlement,
account, or subscription; request/download/persist data; verify rights; perform fitness or BLS
reconciliation; fill an operational composition; define a policy/holdout; execute research;
compute performance; promote a strategy; mutate risk/governance; submit or reconcile an order;
begin Phase 25; or add a live path without separate authorization.
