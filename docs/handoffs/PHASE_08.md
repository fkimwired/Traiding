# Phase 8 Handoff Prompt

Phase 7 acceptance is approved. Replace `<PHASE_7_BASELINE_SHA>` with the final clean Phase 7
commit SHA before using this prompt.

Treat commit `<PHASE_7_BASELINE_SHA>` as `PHASE_7_BASELINE_SHA`.

## Pre-phase closure

1. Confirm `HEAD` equals `PHASE_7_BASELINE_SHA` and `git status --porcelain` is empty.
2. Audit every working-tree change before staging. Stop on unrelated, ambiguous,
   generated-but-unexplained, or user-owned changes.
3. From the clean Phase 7 baseline rerun:

   ```powershell
   $env:FABLE5_VERIFY_PHASE = "7"
   .\scripts\check.ps1
   .\scripts\test.ps1
   npm run build
   .\.venv\Scripts\python.exe scripts\verify_phase1.py --static-only --phase 7
   .\.venv\Scripts\python.exe scripts\verify_phase1.py --phase 7
   ```

4. Stop if a gate fails or leaves the worktree dirty.

## Phase 8 objective and exclusions

Implement Phase 8 only: complete the four product workflows and their visual, accessibility,
responsive, and traceability QA using the existing immutable Phase 2-7 APIs:

1. Idea Intake;
2. Research Lab;
3. simulated Paper Trading status; and
4. Risk / Compliance.

This is a product-workflow and presentation phase. Do not add a broker, submission, fill, position,
executable paper intent, paper execution, provider credential, real-performance data, or live
capability. Do not add a signal or strategy engine, alter a research verdict, weaken a gate, or let an
LLM emit a label, approval, signal, recommendation, allocation, risk override, or execution
instruction. The simulated Paper Trading mode displays immutable approval status and blocking
evidence only; it cannot create or submit anything executable.

## Inputs and source authority

Read and preserve these authorities before editing:

- `AGENTS.md`, `docs/PRODUCT_BRIEF.md`, `FABLE5_BUILD_PROMPT.md`, and
  `docs/IMPLEMENTATION_PLAN.md` for the product and phase boundary;
- `docs/RESEARCH_SUPPLEMENT.md` and `docs/STRATEGY_CANON.md` for the six idea archetypes and honest
  build/defer/reject rationale;
- `docs/PHASE_02_SCHEMA_DECISIONS.md`, `docs/PHASE_03_MAPPING_DECISIONS.md`,
  `docs/PHASE_04_DATA_DECISIONS.md`, `docs/EVALS.md`, `docs/PHASE_06_RESEARCH_DECISIONS.md`,
  `docs/PHASE_07_APPROVAL_DECISIONS.md`, and `docs/RISK_POLICY.md` for immutable semantics and gate
  precedence;
- FastAPI/Pydantic OpenAPI and generated `packages/contracts` output as the only client-contract
  authority; and
- the six committed synthetic Phase 2 fixtures under `services/extraction/tests/fixtures` plus the
  persisted deterministic Phase 3-7 acceptance corpus as the only required data. Do not infer truth
  from fixture names or duplicate server-owned values in frontend code.

The six fixtures are ranking, trend/pattern, social/news, pairs, order flow, and unusual options. Use
their persisted API records; do not create a second frontend fixture authority.

## Write scope and migration posture

Phase 8 may change the frontend, frontend tests/assets, root UI test/build wiring, Phase 8 verifier
coverage, and Phase 8 documentation. Generated contracts may change only by regeneration from an
intentional FastAPI/Pydantic change that remains within this UI phase.

Do not change migrations `0001` through `0007`, prior artifact bytes, gate logic, fixture verdicts,
or persistence semantics. Do not add migration `0008`, a new database table, or an execution-shaped
API. The existing APIs are sufficient authority for this phase; if a required read relation is truly
unavailable, stop and report the exact missing contract instead of inventing parallel state. Preserve
all unrelated and user-owned files.

## Product and contract requirements

- Idea Intake lets a user enter or paste each of the six ideas, preserves the source and ambiguity,
  shows extraction/loading/error states, and renders the resulting normalized `TradingIdeaCard`.
- Every strategy card shows, in a coherent hierarchy: original post-derived claim, normalized
  interpretation, required data, testability status, mock backtest summary, cost sensitivity, risk
  status, simulated-paper status, and reason for build/defer/reject.
- Research Lab runs only existing deterministic mock research/evaluation workflows and displays
  abandoned/failed trials, leakage, PBO/DSR, cost stress, lineage, and blocking gates. A blocking
  result visually dominates every positive metric.
- Simulated Paper Trading is conspicuously labeled `SIMULATED`. It shows historical synthetic Phase 7
  status, expiry/review/revocation context, and reason codes, but no order ticket, quantity, side,
  submit control, execution-readiness claim, or performance promise.
- Risk / Compliance displays the complete ordered Phase 7 checks and immutable approval/revocation
  history. If it exposes the existing assessment or revocation creates, requests contain references
  only and the UI must never imply that the client supplied an approval, threshold, timestamp,
  verdict, risk result, or authorization state.
- Preserve the exact corpus truth: only `phase6-a-pass-v2` is `PASS_RESEARCH`; that prerequisite alone
  is never approval. Every rejected, blocked, expired, stale, revoked, conflicting, or uncomputable
  state remains visibly ineligible. Configuration ids containing `-pass-` are identities, not
  verdicts.
- From every visible result, a user can reach source input, extraction, mapping, point-in-time
  snapshot, configuration and code version, evaluation, research artifact, approval/revocation, and
  immutable audit entry in at most two interactions. Reference licensed or secret payloads; never
  copy them into frontend fixtures, bundles, screenshots, logs, or generated contracts.
- FastAPI/Pydantic remains the schema owner. Do not maintain handwritten response types or duplicate
  server thresholds, hashes, timestamps, outcome calculations, or lineage metrics in the client.
- Maintain keyboard navigation, visible focus, skip/landmark navigation, semantic heading order,
  accessible names and status announcements, non-color-only meaning, contrast, responsive layouts,
  empty/loading/error states, and reduced-motion behavior.
- Use no guarantees, hype, personalized advice, fabricated performance, or presentation that makes
  synthetic evidence look current or real.

## Bounded implementation units

1. Build one typed read/create client layer from generated contracts, with deterministic loading,
   empty, validation, conflict, unavailable, and retry-safe states.
2. Complete Idea Intake and the six `TradingIdeaCard` views without altering extraction authority.
3. Complete Research Lab with gate-first evaluation/research evidence and honest rejected/deferred
   cards.
4. Complete simulated Paper Trading and Risk / Compliance as governance/status workflows only.
5. Build a shared lineage route that meets the complete source-to-audit two-interaction requirement.
6. Establish the responsive visual system and reusable accessible status/gate components.
7. Add deterministic component, integration, accessibility, responsive, and visual-regression tests,
   then extend the Phase 8 verifier without weakening any Phase 1-7 assertion.

Each unit must have an executable acceptance test and preserve source evidence.

## Acceptance

Prove all of the following:

- all four modes work against deterministic API fixtures, and all six idea archetypes can be entered,
  normalized, and inspected with the required strategy-card anatomy;
- loading, empty, malformed, unavailable, conflict, rejected, blocked, stale, expired, revoked,
  uncomputable, and success states are deterministic and do not soften a blocker;
- the exact source-to-extraction-to-mapping-to-snapshot-to-config/code-to-evaluation-to-research-to-
  approval/revocation-to-audit route takes at most two interactions from each visible result;
- keyboard-only operation, focus order/restoration, landmarks/headings, accessible names/live status,
  contrast, reduced motion, and non-color-only gate meaning pass automated and focused manual checks;
- pinned mobile, tablet, and desktop viewport snapshots cover every mode and representative negative
  states; visual-regression output is deterministic and contains no licensed/secret source payload;
- server-owned OpenAPI and generated TypeScript remain byte-for-byte in parity, prior API schemas and
  migrations remain intact, and every Phase 1-7 test/verifier still passes; and
- static checks continue proving that broker, submission, fill, position, executable paper intent,
  paper-execution, and live paths are absent.

Run:

```powershell
$env:FABLE5_VERIFY_PHASE = "8"
.\scripts\check.ps1
.\scripts\test.ps1
npm run build
.\.venv\Scripts\python.exe scripts\verify_phase1.py --static-only --phase 8
.\.venv\Scripts\python.exe scripts\verify_phase1.py --phase 8
```

Stop after Phase 8. Report exact files changed, commands/results, visual and accessibility evidence,
known limitations, final clean commit SHA, and the next explicitly authorized prompt. Do not begin
any execution or broker phase.
