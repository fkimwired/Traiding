# Phase 24 Family A RTDSM rights-clarification requirements decisions

## Decision

Phase 24 freezes the exact inputs and fail-closed evaluation rules needed for a later independent
clarification of current use rights for the Phase 22 Philadelphia Fed RTDSM candidate. The truthful
result is:

```text
outcome:              BLOCKED
requirements_state:   RIGHTS_CLARIFICATION_REQUIREMENTS_FROZEN
aggregate_conclusion: BLOCKED_AWAITING_INDEPENDENT_CURRENT_USE_RIGHTS_CLARIFICATION
```

This is a requirements artifact, not a clarification request or response. It does not contact the
Philadelphia Fed, BLS, a provider representative, or counsel and does not infer permission from
public research-use language.

## Accepted baseline and authority

```text
accepted Phase 23 commit: d8d8d63a79457c7a54e0a3738a75f4eb613c602f
accepted Phase 23 tree:   4f3da35d31f352ea92d5f715149e0e439a57af3b
Phase 23 merge commit:    53d9f8641d98c729447661af9b7e561073a52226
Phase 23 artifact id:     e4fbd5af-c5ad-51fb-92cb-7308fafd017a
Phase 23 artifact SHA:    aafb6deadff7b4cd4f9b4e7c98c8ac31f0d957a60b1d5be59f3d7ebf2679cd2c
Phase 23 policy SHA:      624c553bc1a7777e33634464743b4e0d37115136afedca81c2cdbc43c819dd16
```

The user's separate instruction to begin the next phase authorizes this offline Phase 24
requirements freeze only. It is not authority to perform outreach, obtain an opinion, use a login
or credential, accept terms, inspect an account, request or download data, or persist a provider
payload.

## Frozen registries

Phase 24 records eight proposed-use disclosures. Every row is
`PROPOSED_NOT_AUTHORIZED`: research and simulated-paper purpose, candidate product scope,
potential automated access, persistent storage/backups, automated model processing, derived
outputs, display/redistribution, and retention/deletion/revocation. These statements describe the
scope that a later authorized reviewer must present; they do not select a product or authorize the
use.

The ten clarification questions are all `UNANSWERED` and require explicit product-specific yes/no
or conditional answers:

1. persistent storage and reproducibility copies;
2. automated internal feature/model/backtest/paper-simulation use;
3. derived data and model artifacts;
4. retention, deletion, backups, and termination;
5. redistribution, display, export, and internal sharing;
6. attribution and notices;
7. BLS-originated content and upstream rights;
8. automated access method and load limits;
9. effective terms, change notice, revocation, and revalidation; and
10. authority, exact product, series, delivery, account, user, and use scope.

All six evidence requirements are `MISSING`: authenticated rights-holder identity, exact product
scope, explicit intended-use coverage, effective/current governing terms, third-party rights
coverage, and enforceable revocation/retention/deletion obligations.

All seven transition rules are unapplied. Evidence presence is not verification; verification must
bind identity, authority, scope, currentness, and integrity; all questions are required; conditions
must be enforceable; prohibited or ambiguous answers fail closed; relevant changes force
revalidation; and a repository lifecycle event or generic public statement is never rights
authority.

## Persistence and security boundary

The generator requires `--confirm-rights-clarification-requirements-only`, writes only canonical
JSON to stdout, and performs no I/O. The verifier accepts one bounded local regular file through
`--requirements PATH`, rejects noncanonical or altered content, and returns a sanitized receipt.
Both install network and subprocess audit denial before loading the Phase 24 domain.

Phase 24 adds no migration, database row, API route, OpenAPI or TypeScript contract, dependency,
Compose service, provider adapter, credential loader, scheduler, worker, UI control, data file,
snapshot, policy, holdout, research path, risk mutation, paper order, or live path. The accepted
Phase 23 artifact and implementation remain byte-identical.

## Acceptance and stop condition

Acceptance requires deterministic generation, committed-file parity, strict 8/10/6/7 registry
counts and ordering, domain-separated hashes, exact Phase 23 lineage, all questions unanswered,
all evidence missing, all transitions unapplied, every external-authority field false, offline
operation, zero database/schema writes, unchanged inherited behavior, and clean Windows and Ubuntu
Phase 24 gates at one committed SHA/tree.

Stop after Phase 24. Do not contact a provider, BLS, rights holder, or counsel; send the packet;
load credentials; inspect an account/license; request, download, inspect, or persist data; assert or
verify rights; select a product/delivery/composition; perform fitness or BLS reconciliation; define
a policy or holdout; execute research; compute performance; promote a strategy; mutate risk;
submit or reconcile an order; begin Phase 25; publish Phase 24; or add a live capability without
separate authorization.
