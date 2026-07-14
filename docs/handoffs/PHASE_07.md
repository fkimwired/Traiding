# Phase 7 Handoff Prompt

Phase 6 acceptance is approved. Replace `<PHASE_6_BASELINE_SHA>` below with the final clean
Phase 6 commit SHA before using this prompt.

Treat commit `<PHASE_6_BASELINE_SHA>` as `PHASE_6_BASELINE_SHA`.

## Pre-phase closure

1. Confirm `HEAD` equals `PHASE_6_BASELINE_SHA` and `git status --porcelain` is empty.
2. Audit every working-tree change before staging; stop on unrelated, ambiguous,
   generated-but-unexplained, or user-owned changes.
3. From the clean Phase 6 baseline rerun:

   ```powershell
   $env:FABLE5_VERIFY_PHASE = "6"
   .\scripts\check.ps1
   .\scripts\test.ps1
   npm run build
   .\.venv\Scripts\python.exe scripts\verify_phase1.py --static-only --phase 6
   .\.venv\Scripts\python.exe scripts\verify_phase1.py --phase 6
   ```

4. Stop if a gate fails or leaves the worktree dirty.

## Phase 7 objective

Implement Phase 7 only: a fail-closed approval and pre-order risk layer for simulated paper
trading. Do not implement a broker, order submission, fills, positions, paper execution, or
any live capability. The live path must remain absent.

Only immutable Phase 6 `PASS_RESEARCH` artifacts may be considered, and `PASS_RESEARCH` alone
must never grant approval. Approval requires a separately versioned policy, human-controlled
authorization evidence, expiry, revocation, scope, complete Phase 6 lineage, and pre-order
risk rules. Missing, stale, revoked, conflicting, or uncomputable evidence must fail closed.

The accepted Phase 6 deterministic corpus contains exactly one persisted synthetic
`PASS_RESEARCH` artifact: `phase6-a-pass-v2`. `phase6-a-fail-cost-v2`, both Family B artifacts,
and `phase6-c-pass-v2` are `FAIL_REJECT`; the corroboration-negative Family C request blocks
before persistence. Configuration ids containing `-pass-` are immutable fixture identities, not
verdicts. Phase 7 must derive eligibility from the immutable Phase 6 promotion state and complete
lineage, never from an id token. It must not relabel, special-case, or manufacture a Phase 6
result.

`phase6-a-pass-v2` may exercise only the research-eligibility prerequisite. A request containing
that artifact alone must still fail closed. A positive approval artifact may be created only when
the same pre-existing immutable Phase 6 result is accompanied by every separately required,
valid human authorization, policy, scope, expiry, revocation, lineage, and pre-order-risk input.
The result remains synthetic and cannot authorize an order or imply execution readiness.

Preserve migrations 0001 through 0006, all existing rows, all Phase 5 gates, all Phase 6
artifacts, and generated-contract authority. If schema changes are required, add reversible
migration 0007 with `down_revision="0006_phase6"`. New approval/risk artifacts must be
append-only and reject `UPDATE`, `DELETE`, and `TRUNCATE`.

Phase 6 research scores remain synthetic research evidence. Do not claim real performance,
personalized investment advice, execution readiness, or approval from a research result.

The LLM boundary remains unchanged: extraction and structured text features only. An LLM may
never emit approval, a label, signal, buy/sell call, allocation, position size, risk override,
or execution instruction. Social content remains non-standalone and exactly corroborated.

Expose create/read/list APIs only. Clients cannot supply approvals, verdicts, hashes,
thresholds, timestamps, risk results, expiry/revocation states, or Phase 6 metrics. Generate
TypeScript only from FastAPI/Pydantic OpenAPI.

Prove that every `FAIL_REJECT` or blocked Phase 6 fixture is ineligible; that
`phase6-a-pass-v2` alone cannot approve; and that any positive approval path requires the exact
pre-existing A artifact plus all independently valid approval evidence. Also prove two-writer
idempotency, revocation/expiry/staleness behavior, complete Phase 6 lineage, immutable prior-row
bytes, append-only rejection, the `0007 -> 0006 -> 0007` migration cycle if 0007 exists,
generated-contract parity, and the continued absence of broker/order/position/paper-execution and
live paths. Do not weaken or replace a Phase 5/6 gate to exercise an approval branch.

Run:

```powershell
$env:FABLE5_VERIFY_PHASE = "7"
.\scripts\check.ps1
.\scripts\test.ps1
npm run build
.\.venv\Scripts\python.exe scripts\verify_phase1.py --static-only --phase 7
.\.venv\Scripts\python.exe scripts\verify_phase1.py --phase 7
```

Stop after Phase 7 and report exact evidence, limitations, final clean commit SHA, and a
ready-to-paste Phase 8 prompt.
