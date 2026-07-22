# DEVELOPMENT.md — canonical near-term task queue

Prepared 2026-07-21 (UTC). This file is the canonical near-term Codex task queue for the
2026-07-23 external live-data paper test (Track A) and the immediately following documentation and
evidence work (Track B preparation). It is planning documentation only. It is subordinate to
`AGENTS.md`; nothing in this file weakens, reinterprets, or bypasses any rule there or in any
accepted phase decision document. No task in this file authorizes an order path, a live mode, a
credential outside the documented capture commands, provider-data persistence, or any Family A
research-admission step.

## 1. Current verified baseline (2026-07-21)

- Branch: `codex/phase-25-rtdsm-rights-response-adapter-patterns`. The Phase 25 baseline is
  `4d70b823947fd61d0ea17df14c9f1ff9f93fd45b` ("Implement Phase 25 rights evidence and adapter
  patterns"); current committed HEAD is `c11e899a25732b49d9d7b3a95e2d12c4b6eff215` ("Add
  read-only paper readiness view").
- Formal acceptance ladder recorded in-repo: Phases 1–22 accepted with exact commit/tree (and,
  from Phase 14 on, same-SHA Ubuntu run IDs); Phase 24 accepted at
  `c1dad09f08b18a5a7d527579ca677633b49184fb` (merge `145f67f1…`). Phase 12 — the boundary Track A
  uses — is formally accepted at commit `37530a94f841d538a162447cb01ec3e11f375ead`.
- Phase 25 is implemented at its baseline commit but has **no recorded same-SHA acceptance run**:
  implemented, not formally accepted.
- Phase 26 (`FAMILY_A_CRSP_SEC_RTDSM_V1` composition decision) exists **only as uncommitted
  working-tree changes**. On 2026-07-21 its local gates passed:
  `pytest services/data/tests/test_phase26_composition.py tests/test_phase26_portable.py`
  (18 passed), `scripts/verify_family_a_operational_data_composition_decision.py` (verified true),
  and `scripts/verify_phase1.py --static-only --phase 26` (passed). It has no committed SHA, no CI
  run, and no formal acceptance evidence. **These working-tree changes must be preserved exactly.**
- What the product can demonstrate today, locally, with no credentials: the full Compose stack;
  four-mode frontend over immutable Phase 2–14 evidence; deterministic local mock paper simulation
  (Phase 10) with evidence bundles and offline verification (Phase 11); deterministic mock paper
  shadow-readiness capture (Phase 12); and the portable Family A artifacts (Phases 15–26).
- The accepted Phase 12 credentialed external-readiness capture
  (`scripts/capture_paper_shadow_readiness.py`) and historical GET
  (`GET /v1/paper-shadow-readiness/{readiness_assessment_id}`) now have uncommitted maintenance
  overlays for preflight, reporting, a read-only frontend consumer, a smoke harness, and static
  policy sweeps (T-001–T-005). These overlays do not change Phase 12 authority.
- The frontend already carries a persistent simulation banner ("Paper status is historical and
  simulated.", `services/frontend/src/app/layout.tsx`) and simulated-boundary notices in the Paper
  Status workspace.

### Task status

- **T-001 — implemented and independently verified 2026-07-21.** Files:
  `scripts/preflight_paper_smoke.py`, `tests/test_preflight_paper_smoke.py` (exactly the allowed
  set). Verification: 29/29 task tests, 19/19 repository-policy + Phase 12 static tests, ruff
  clean, canary-leak tests pass, accepted Phase 12 diff empty, Phase 26 working tree
  byte-identical. A real preflight run produced `MOCK_PROOF_COMPLETE` with report SHA-256
  `6a9e7a9389c145dd4257e9bb3facd678ca355decfab8cc744903720662b501c7`. The implementation exceeds
  spec safely: subprocesses receive a sanitized environment stripped of both credential variables
  and `FABLE5_DATABASE_URL`, the database URL is restricted to loopback `postgresql+psycopg` with
  ambient libpq routing variables rejected, and the report records `random_seed`/`trial_count` as
  explicitly null. Known limitation: the credential presence check treats a present-but-empty
  variable as `PRESENT_PAIR`; the accepted Phase 12 settings still reject blank values before any
  transport, so this is cosmetic only.
- **T-002, T-004, and T-005 — implemented and validated in the working tree.**
- **T-003 — implemented, clock-authority repaired, and baseline-reconciled 2026-07-22.** Its
  initial commit is `c11e899a25732b49d9d7b3a95e2d12c4b6eff215`; the immutable Phase 17/18
  commit-to-commit boundaries remain frozen, while the exact later T-003 frontend overlay and the
  exact clock-authority repair delta are enforced by repository-policy tests.
- T-006–T-010: not started.

### Local Alpaca CLI disposition (2026-07-22)

The separately installed Alpaca CLI source checkout (`alpacahq/cli`) was not adopted as Fable5
tooling because its checkout
contains order-submission and order-cancellation surfaces, which are prohibited by `AGENTS.md` even
for a dormant dependency. It was moved recoverably out of this repository from `Trade/cli` to
`C:\Users\leero\OneDrive\Desktop\AlpacaBrokerCLI-quarantine-20260722`. Its clean nested Git HEAD
remains `dc33c945a09d614a6ce8c6e81d805fa914571873`; the 109-file, 2,957,799-byte manifest remained
byte-identical with SHA-256
`d689d9b55a5733436645950a0237f8e89ef83b52957615649cec98bf1412f698`. It is not an authorized
provider, adapter, or execution dependency for Fable5.

The separate ignored, user-owned `OpenAlice/` checkout was quarantined recoverably outside Fable5
at `C:\Users\leero\OneDrive\Desktop\OpenAlice-quarantine-20260722`. Its pre/post manifest is
58,953 files, 1,134,987,753 bytes, SHA-256
`345e7a62b8d533c58802f8109afda3a47af72c84edf2a9653061745aa6239c92`; both nested Git identities,
remotes, and dirty/clean statuses were preserved. Neither `OpenAlice/` nor `cli/` now exists under
`Trade/`. The quarantined code remains prohibited and is not adopted as a dependency or provider.

### End-of-week paper-readiness stabilization units (authorized 2026-07-22)

These units are limited to the Phase 26 verification boundary and accepted earlier-phase
maintenance. They authorize no Phase 27 work, credential read, provider call, raw payload, order
operation, live mode, or external observation.

1. **U26-OVERLAY - exact 29-path maintenance reconciliation.** Governing boundary: Phase 26
   verification maintenance. Keep baseline `4d70b823947fd61d0ea17df14c9f1ff9f93fd45b`, tree
   `84426ba04f4dbb686878852357410880327b5713`, and `PHASE_26_ALLOWED_WRITES` unchanged; enforce a
   separate, exact, content-pinned 29-path overlay for two governance paths, T-001 (2), T-002 (2),
   T-003 (20), T-004 (2), and T-005 (1). Acceptance commands:
   `pytest tests/test_repository_policy.py -k "phase26 and maintenance" -q` and
   `python scripts/verify_phase1.py --static-only --phase 26`. Literal adversarial assertion:
   adding `services/api/live_order_submit.py`, adding any 30th path, removing one accepted path, or
   changing one pinned byte digest must fail. Evidence: the external Phase 26 closeout JSON with
   config hash, evidence ID, HEAD SHA, seed/trial count `0/0`, UTC time, path digest, content digest,
   and all 29 dispositions. Stop if this requires a baseline/tree change, weakening an inherited
   check, admitting a 30th path, or crossing into Phase 27.
2. **U12-FORMAT - three formatting-only repairs.** Governing boundary: accepted Phase 12
   T-001/T-004 maintenance. Format only `scripts/preflight_paper_smoke.py`,
   `tests/test_preflight_paper_smoke.py`, and `tests/test_run_paper_smoke_static.py`. Acceptance:
   `ruff format --check .` plus the three paper-smoke test modules. Literal negative assertion:
   each Python AST digest before and after formatting is identical; no provider, credential,
   request, or behavior changes. Evidence: before/after AST digests and command results in the
   external closeout JSON. Stop if formatting changes a parsed AST or a focused test fails.
3. **U1-QUARANTINE - prohibited nested-checkout isolation.** Governing boundary: Phase 1 hard-gate
   and repository-policy maintenance. Inventory the exact ignored `OpenAlice/` checkout, then move
   that whole checkout recoverably to a verified sibling path outside `Trade/`. Acceptance:
   source absent, destination present, pre/post file count and byte manifest identical, nested Git
   HEAD/status/remotes preserved, and repository policy tests passing. Literal negative assertion:
   neither `OpenAlice/` nor `cli/` exists beneath the Fable5 root, and no order/live-capable file is
   copied into it. Evidence: sanitized source/destination identities and manifest hashes in the
   external closeout JSON. Stop before any delete, selective rewrite, destination overwrite, or
   operation on a path other than the exact top-level ignored checkout.
4. **U26-CLOSEOUT - reproducible offline verification evidence.** Governing boundary: Phase 26
   verification closeout. Run the complete Phase 26 static/full gates plus relevant Python,
   frontend, formatting, typing, and regression suites. Literal negative assertion: no test or
   evidence step reads credentials, contacts Alpaca or another provider, persists raw data, or
   exposes submission/replacement/cancellation/liquidation/live authority. Evidence: a sanitized
   JSON outside the checkout containing required audit fields and exact command results. Stop and
   report the honest blocker on any nonzero applicable gate; do not claim external connectivity or
   paper readiness from local tests alone.

### Preflight reconciliation requirement

The preflight's check 3 runs `verify_phase1.py --static-only --phase 26` and diffs the tree against
the accepted Phase 25 baseline. U26-OVERLAY keeps the implementation allowlist unchanged and
separately requires the complete 29-path set with pinned contents, so omission, substitution,
content drift, or a 30th path is a hard failure. Before that repair the verifier truthfully reported
the 29 governance/T-001-T-005 paths and exited nonzero; it now passes only when both the original
Phase 26 policy and this exact maintenance policy pass. Any future nonzero result remains a NO-GO.
No stabilization step reads credentials or performs an external request.

### Current closeout state (2026-07-22)

The exact-29 static policy, repository-policy tests, formatting, lint, typing, focused and full
regressions, frontend build, and isolated credential-free Compose smoke all pass. After the
repository owner authorized a reviewed commit, the preserved tree received a clean Git identity
and `python scripts/verify_phase1.py --phase 26` passed, including its post-cleanup identity and
zero-resource checks. This clears the repository gate to `READY_FOR_CREDENTIALED_PROBE`; it is not
an external-readiness result. The operator must still satisfy H1-H4, rerun preflight, confirm the
accepted market-clock window and paper-only credentials, and perform no more than the separately
authorized one-shot read-only observation. This closeout did not read credentials, contact Alpaca,
or infer provider readiness from local tests.

### Historical known condition before the 2026-07-22 reconciliation

Before U26-OVERLAY, the preflight's check 3 ran
`verify_phase1.py --static-only --phase 26`, diffed the tree against the accepted Phase 25
baseline, and enforced the then-current exact path allowlist. The planning
documents and operator-tooling files were outside that allowlist, so **check 3 failed
with `PHASE_26_STATIC_VERIFICATION_FAILED`, and the preflight's overall exit was nonzero, on any
tree containing them — no commit sequencing removes them from the diff against the frozen
baseline.** This was the guardrail telling the truth; the verifier was not edited to conceal it.
The plan then stated that only a separately authorized later phase would advance
the verifier baseline/allowlist. That earlier plan is superseded: the baseline and implementation
allowlist were not advanced; a separate exact and content-pinned maintenance policy now passes
while retaining every downstream Phase 26 check.

The then-current fail-closed handling for the 2026-07-23 test required the operator to run the
verifier directly and
confirms the failure message names **exactly** the paths attributable to this file — `AGENTS.md`,
`DEVELOPMENT.md`, and the "Files allowed to change" entries of implemented tasks T-001–T-005 in
§9. The T-003 initial overlay, its repair delta, and its Phase 17/18 frozen-scope intersection are
independently pinned by `tests/test_repository_policy.py`, `tests/test_phase17_static.py`, and
`tests/test_phase18_static.py`. The exact path list must be recorded as evidence, but it may not be
acknowledged, waived, or relabeled as a pass. A nonzero verifier result is a mandatory NO-GO for
the credentialed probe even when it contains only the documented paths. The separate ignored
`OpenAlice/` checkout is an additional NO-GO. Run the mock demonstration only and stop before
reading credentials or making an external request. This historical instruction is superseded by
U26-OVERLAY and U1-QUARANTINE above: the baseline and implementation allowlist remain frozen, the
separate exact-29 content policy passes, and both prohibited checkout names are absent from Fable5.

### Validation record for this planning change (2026-07-21)

Commands run after the 2026-07-21 planning-documentation edits:

- `pytest tests/test_repository_policy.py tests/test_phase26_portable.py
  services/data/tests/test_phase26_composition.py tests/test_phase25_static.py` — **38 passed**
  (the pinned AGENTS.md hard-gate prefix is intact; the Phase 26 suites are unaffected).
- `scripts/verify_family_a_operational_data_composition_decision.py` — verified true.
- `scripts/verify_phase1.py --static-only --phase 26` — **passed before** these planning edits;
  **after** them it reports, by design: "Phase 26 changed paths outside the exact allowlist:
  AGENTS.md, DEVELOPMENT.md". This is the Phase 26 guardrail correctly detecting that the planning
  documents are a separately authorized change, not Phase 26 implementation. That historical
  sequencing note no longer describes the current `c11e899…`-descended tree with T-001–T-005
  overlays. That was the honest 2026-07-21 result. The 2026-07-22 reconciliation instead kept the
  baseline and implementation allowlist fixed and added a separately enforced exact maintenance
  policy in `scripts/verify_phase1.py`; it did not waive, relabel, or conceal the failure.

### T-003 formal reconciliation validation (2026-07-22)

- Full Python regression: **2,073 passed, 116 skipped, 0 failed**.
- Requested readiness regression set: **104 passed**. Phase 17/18 plus repository-policy focused
  set: **32 passed**, including adversarial clock/timer/polling and timestamp-comparison canaries.
- Frontend: **170 unit tests passed**; lint, typecheck, generated-contract check, and production
  build passed. The isolated readiness browser suite finished with **18 passed, 6 intentional
  project skips**; all 12 synthetic visual baselines matched exactly after excluding framework-only
  development/focus chrome from capture.
- At that T-003-only handoff, Python lint and mypy passed, while repository-wide
  `ruff format --check .` was nonzero only for three then-untouched user-owned files:
  `scripts/preflight_paper_smoke.py`, `tests/test_preflight_paper_smoke.py`, and
  `tests/test_run_paper_smoke_static.py`. The three files changed for formal baseline-policy
  reconciliation were format-clean.
- At that same handoff, `verify_phase1.py --static-only --phase 26` was nonzero with the exact 29
  documented T-001–T-005/planning paths, and the ignored `OpenAlice/` checkout remained a separate
  NO-GO. Those were genuine blockers then. U12-FORMAT, U26-OVERLAY, and U1-QUARANTINE have since
  cleared all three without changing the accepted Phase 12 authority or performing an external
  request.
- No provider request, credential read, order operation, commit, push, or publication occurred.

## 2. Terminology

- **External live-data paper test**: read-only observation of a paper-only external environment
  using real-time or recently updated external data, with all simulated behavior clearly labeled.
  Never live trading; no live endpoint, live credential, live execution mode, or real order path.
- **Track A**: the 2026-07-23 operator acceptance activity inside the formally accepted Phase 12
  read-only boundary (six allowlisted GETs against `paper-api.alpaca.markets` /
  `data.alpaca.markets`, sanitized append-only evidence, explicit local capture).
- **Track B**: the Family A research-data path continuing from the Phase 26 composition
  `FAMILY_A_CRSP_SEC_RTDSM_V1`. Blocked behind rights/entitlement, schema, and point-in-time
  qualification gates. Track A implies nothing about Track B.
- **`MOCK_PROOF_COMPLETE` / `SHADOW_READY` / `BLOCKED`**: the only Phase 12 outcomes. A mock can
  never produce `SHADOW_READY`. Successful artifacts expire 60 seconds after completion and then
  remain historical evidence only.
- **Demonstration data vs research-qualified data**: readiness/connectivity observations (including
  the frozen `AAPL`/IEX quote probe) are demonstration data. They are never persisted as raw
  prices and never become research snapshots, backtest inputs, or strategy signals.

## 3. Objective for 2026-07-23

Produce, during the regular market window reported by the accepted Phase 12 market-clock check
(expected 09:30–16:00 ET; 13:30–20:00 UTC; 2026-07-23 is a Thursday),
one credentialed, sanitized, append-only Phase 12 readiness artifact from the external Alpaca paper
environment — honestly `SHADOW_READY` or honestly `BLOCKED` — observed end-to-end by the operator
via the runbook in §10, retrieved through the historical GET, presented with a clear
"Simulated / Paper Only / No Advice" boundary, and summarized in a sanitized post-test evidence
report carrying hashes and UTC timestamps. If credentials are unavailable, the deterministic mock
path is the fallback demonstration and is labeled `MOCK_PROOF_COMPLETE`, never external readiness.

## 4. Explicit exclusions

No order intent, submission, replacement, cancellation, liquidation, or position mutation — not
even paper orders. No live endpoint, enum, flag, credential, dependency, configuration branch, or
dormant implementation. No new vendor methods, symbols, URLs, query parameters, mutations, or
generic transport. No persistence of credentials, headers, raw bodies, account identifiers, order
details, position details, or quote prices. No use of any quote or free source as a strategy input
or research snapshot. No LLM trade instruction, position size, or buy/sell output. No Family A
step: no provider contact, no data download, no CRSP/RTDSM/SEC acquisition, no evaluation policy,
no holdout, no research admission. No Phase 27 or later implementation. No commit, push, PR, or
publication as part of the test itself.

## 5. Assumptions and human prerequisites (blockers if unmet)

| # | Prerequisite | Owner | Status |
|---|---|---|---|
| H1 | Explicit authorization for the credentialed external probe (Phase 12 defines it as separately authorized work) | Repository owner | REQUIRED — record before the credentialed step |
| H2 | Alpaca **paper** account and paper-only API key pair, obtained by the human and exported only as `FABLE5_ALPACA_PAPER_API_KEY_ID` / `FABLE5_ALPACA_PAPER_SECRET_KEY` in the operator shell; never committed, logged, or pasted into files | Operator | REQUIRED for `SHADOW_READY`; mock fallback otherwise |
| H3 | The paper account has **zero positions and zero open orders** (checks 6–7 block otherwise); reset/confirm in the broker dashboard, not via this codebase | Operator | REQUIRED for `SHADOW_READY` |
| H4 | Test window inside regular market hours (check 4 `MARKET_CLOCK_OPEN` blocks otherwise) | Operator | Plan 09:30–16:00 ET |
| H5 | Docker Desktop running; `.venv` and `npm ci` provisioned per README | Operator | Verified 2026-07-21 (`.venv` present) |
| H6 | Decision: commit the Phase 26 working-tree changes at one honest SHA before the test (recommended, so evidence binds a clean SHA), or run on the dirty tree (acceptable for an operator activity; the evidence then binds HEAD while the tree is dirty — record that fact in the evidence report) | Repository owner | OPEN |

## 6. Ranked feature table

Scoring: each criterion 0–3, higher is better. TR = tomorrow readiness, UV = user-visible value,
RC = reuse of accepted code, EF = low effort, LC = licensing certainty, SR = low security risk,
PIT = point-in-time relevance, REV = reversibility, TST = testability. Max 27.

| Feature | TR | UV | RC | EF | LC | SR | PIT | REV | TST | Total | Priority |
|---|---|---|---|---|---|---|---|---|---|---|---|
| F1 One-command operator preflight + runbook (T-001) | 3 | 2 | 3 | 3 | 3 | 2 | 0 | 3 | 3 | 22 | **P0** |
| F2 Sanitized post-test evidence report (T-002) | 3 | 2 | 3 | 2 | 3 | 2 | 0 | 3 | 3 | 21 | **P0** |
| F3 Read-only readiness UI with Simulated/Paper-Only banner (T-003) | 2 | 3 | 2 | 2 | 3 | 2 | 0 | 2 | 2 | 18 | **P0** |
| F4 End-to-end mock + optional credentialed smoke harness (T-004) | 2 | 1 | 3 | 2 | 3 | 2 | 0 | 3 | 2 | 18 | P1 |
| F5 Secret-leak / forbidden-live-path static sweep (T-005) | 2 | 0 | 2 | 2 | 3 | 3 | 0 | 3 | 3 | 18 | P1 |
| F6 Source-health / freshness evidence CLI (T-006) | 1 | 1 | 3 | 2 | 3 | 2 | 0 | 3 | 2 | 17 | P1 |
| F7 SEC policy/currentness + schema qualification plan (T-007) | 1 | 0 | 1 | 2 | 2 | 3 | 3 | 3 | 1 | 16 | P1 |
| F8 CRSP + RTDSM rights/entitlement evidence package (T-009) | 1 | 0 | 2 | 2 | 1 | 3 | 3 | 3 | 1 | 16 | P1 |
| F9 Documentation/status reconciliation + stale-status check (T-010) | 2 | 1 | 1 | 2 | 3 | 3 | 0 | 3 | 3 | 18 | P1 |
| F10 BLS release-time corroboration feasibility memo (T-008) | 1 | 0 | 0 | 2 | 2 | 3 | 2 | 3 | 1 | 14 | P2 |

F4 and F5 tie F3 on raw score; F3 takes the third P0 slot because the mission of 2026-07-23 is an
*externally observed* demonstration, and the UI presentation is the only user-visible surface among
the three. No more than three tasks are P0.

## 7. Free-source comparison (verified 2026-07-21 UTC)

See `docs/DATA_SOURCES.md` § "Current free-source candidate matrix (2026-07-21 UTC)" for the full
source-backed matrix with citations. Summary statuses used by this plan:

| Source | Tomorrow (Track A) | Monitoring | Research (Track B) | Point-in-time | Status |
|---|---|---|---|---|---|
| Alpaca paper API + Basic/IEX data | YES — the accepted Phase 12 boundary | YES (clock/readiness only) | NO | NO | `TOMORROW_READ_ONLY_CANDIDATE` |
| SEC EDGAR APIs + bulk archives | Not needed | YES (release/index cadence) | Selected in Phase 26; gates open | Candidate (acceptance timestamps) | `RESEARCH_ADMISSION_BLOCKED` |
| BLS Public Data API v2 | Not needed | YES (release-time corroboration) | NO (not a vintage source) | NO (current revised values) | `OPERATIONAL_MONITORING_CANDIDATE` / `POINT_IN_TIME_INADEQUATE` |
| Philadelphia Fed RTDSM (PCPI) | NO | NO | Selected in Phase 26; rights blocked | YES (vintages) | `RIGHTS_UNVERIFIED` / `RESEARCH_ADMISSION_BLOCKED` |
| CRSP U.S. Stock Databases (Morningstar) | NO (not free; no entitlement) | NO | Selected in Phase 26; entitlement blocked | YES (reference tier) | `RIGHTS_UNVERIFIED` / `RESEARCH_ADMISSION_BLOCKED` |
| FRED / ALFRED | NO | NO | NO | ALFRED vintages exist but terms block use | `REJECTED` for the planned persistent/model use (re-verify before any revisit) |
| Yahoo Finance via yfinance | NO | NO | NO | NO | `REJECTED` operationally; `RIGHTS_UNVERIFIED`; architectural reference only |

## 8. Track A / Track B boundary

Track A uses only the formally accepted Phase 12 surface: the six allowlisted GETs, the frozen
`AAPL`/`feed=iex` connectivity probe, `SecretStr` credential handling, sanitized append-only
evidence, the explicit capture command, and the historical GET. Track A adds no vendor method,
symbol, URL, query, mutation, raw-payload persistence, price-as-strategy-input, or order authority.

Track B continues from `FAMILY_A_CRSP_SEC_RTDSM_V1` and is blocked behind, separately: CRSP exact
Linux flat-file entitlement and current executed rights; the authenticated RTDSM exact-scope rights
response (Phase 24's ten questions; Phase 25 outcome remains
`BLOCKED / RIGHTS_RESPONSE_EVIDENCE_MISSING`); current SEC policy/fair-access revalidation; exact
delivery/schema freeze; the coverage/calendar/availability/missingness contract; point-in-time
qualification; the non-synthetic evaluation policy; the unopened confirmation holdout; and research
admission. **A successful Track A demonstration must never be described as progress on any Track B
gate.**

## 9. Codex-ready tasks

Common invariants for every task below: only execution mode `paper` exists; no live enum, endpoint,
credential, or dormant path may be introduced; no order submission/replacement/cancellation/
liquidation/close code; no LLM trade instruction, size, or buy/sell output; secrets never printed,
logged, persisted, or committed; raw provider payloads never persisted; the uncommitted Phase 26
working-tree changes are preserved exactly; every evidence artifact carries config hash,
snapshot/evidence ID, git SHA, seed and trial count where applicable, and UTC timestamp. Every task
stops at its named boundary; none authorizes a commit or push by Codex.

---

### T-001 (P0) — Operator preflight command and 2026-07-23 runbook wiring

- **Task ID**: T-001
- **Title**: One-command paper-environment preflight with sanitized report
- **Target phase/boundary**: maintenance inside the accepted Phase 12 boundary (no new vendor
  surface); Phase 1 static-check conventions
- **Priority**: P0
- **Estimated effort**: 3–5 h
- **User-visible outcome**: the operator runs one command and gets a PASS/FAIL preflight report
  proving the environment is ready for the smoke test, with zero secrets displayed.
- **Objective**: create `scripts/preflight_paper_smoke.py` that checks, in order: (1) Python and
  Node versions per README; (2) `docker compose config --quiet` succeeds; (3)
  `scripts/verify_phase1.py --static-only --phase 26` exits 0; (4) presence-only validation of the
  credential pair `FABLE5_ALPACA_PAPER_API_KEY_ID` / `FABLE5_ALPACA_PAPER_SECRET_KEY` reporting
  exactly `PRESENT_PAIR`, `ABSENT_PAIR`, or `INCOMPLETE_PAIR` without echoing any value or length;
  (5) database reachability at `FABLE5_DATABASE_URL`; (6) a deterministic mock readiness roundtrip
  by composing the existing `DeterministicMockPaperBrokerAdapter`,
  `PaperShadowReadinessWorkflow`, and `PaperShadowReadinessRepository`
  (`services/paper/src/fable5_paper/phase12/`), asserting `MOCK_PROOF_COMPLETE`. Emit a sanitized
  JSON report (stdout + optional `--output`) with UTC timestamp, git SHA, dirty-tree flag,
  per-check status, and a SHA-256 of the canonical report body. Exit 0 only if every check passes
  (credential absence is a WARN, not a failure, because the mock fallback remains valid).
- **Explicit exclusions**: does not modify `scripts/capture_paper_shadow_readiness.py` (its frozen
  CLI is part of the accepted Phase 12 surface); makes no external network request; adds no
  provider method/URL/symbol; no retry loops; no scheduler.
- **Prerequisite evidence**: Phase 12 acceptance (`docs/handoffs/PHASE_12.md`,
  `docs/PHASE_12_EXTERNAL_PAPER_SHADOW_READINESS_DECISIONS.md`).
- **Source authority**: those two documents plus `AGENTS.md` and this file.
- **Files allowed to change**: `scripts/preflight_paper_smoke.py` (new),
  `tests/test_preflight_paper_smoke.py` (new), `DEVELOPMENT.md` (status note only).
- **Contracts and invariants**: report schema is deterministic and canonically serialized; no
  environment-variable value, prefix, suffix, or length appears anywhere in stdout/stderr/report;
  network sockets are never opened (the mock roundtrip is local DB only).
- **Implementation steps**: (1) argument parser modeled on the sanitized parser in
  `capture_paper_shadow_readiness.py`; (2) sequential checks with fixed reason codes; (3) canonical
  JSON emission + hash; (4) tests.
- **Data/licensing/security posture**: no provider contact; dev-only DB credentials from
  `compose.yaml`; credential handling is presence-only.
- **Migration/rollback**: no migration; delete the two new files to roll back.
- **Acceptance commands**:
  `.\.venv\Scripts\python.exe -m pytest tests/test_preflight_paper_smoke.py -q`;
  `.\.venv\Scripts\python.exe scripts/preflight_paper_smoke.py --output preflight.json` (with stack
  up); `.\.venv\Scripts\python.exe scripts/verify_phase1.py --static-only --phase 26`.
- **Positive assertions (literal)**: report JSON contains `"mock_readiness": "MOCK_PROOF_COMPLETE"`
  and `"credential_pair"` in `{"PRESENT_PAIR","ABSENT_PAIR","INCOMPLETE_PAIR"}`; exit code 0 on the
  all-pass mock path.
- **Negative/adversarial assertions (literal)**: with
  `FABLE5_ALPACA_PAPER_API_KEY_ID=CANARY_KEY_9f3` and
  `FABLE5_ALPACA_PAPER_SECRET_KEY=CANARY_SECRET_7c1` exported, the strings `CANARY_KEY_9f3` and
  `CANARY_SECRET_7c1` appear nowhere in stdout, stderr, the report file, or test capture; with only
  one variable set, the report says `INCOMPLETE_PAIR` and exit code is nonzero; with the database
  down, exit code is nonzero and no partial artifact row exists; a monkeypatched
  `socket.create_connection` proves no external socket is attempted.
- **Audit evidence**: the preflight report itself (UTC timestamp, git SHA, dirty flag, report
  SHA-256).
- **Definition of done**: all acceptance commands pass on Windows; negative assertions proven in
  tests; no change to any accepted Phase 12 file.
- **Stop condition**: stop after the preflight command and tests; do not begin T-002, do not run a
  credentialed capture, do not commit.
- **Dependencies**: none.

---

### T-002 (P0) — Sanitized post-test evidence report over existing Phase 12 evidence

- **Task ID**: T-002
- **Title**: Read-only readiness evidence report generator
- **Target phase/boundary**: maintenance inside the accepted Phase 12 boundary
- **Priority**: P0
- **Estimated effort**: 3–4 h
- **User-visible outcome**: after any capture (mock or credentialed), the operator produces one
  Markdown + JSON evidence report suitable for sharing, containing hashes and timestamps and
  provably no secrets, account identifiers, raw bodies, order details, or quote prices.
- **Objective**: create `scripts/report_paper_shadow_readiness.py --assessment-id <UUID>
  --output <path>` that reads the persisted artifact via
  `PaperShadowReadinessRepository` (read-only; zero writes; zero external calls) and renders:
  assessment ID, source kind, outcome, the eight ordered checks with statuses and content hashes,
  bounded request IDs, response hashes, code git SHA, transport-profile hash, created/completed/
  expiry UTC timestamps, expiry state at render time, the five false/true authority literals, and a
  SHA-256 over the canonical report. The report must state "Simulated / Paper Only / No Advice"
  and, for mock artifacts, "MOCK — proves the local contract only, not external readiness."
- **Explicit exclusions**: no new API route; no DB write; no external request; no raw price,
  position, order, account, header, or body field may be selected even if present in sanitized
  form elsewhere.
- **Prerequisite evidence**: Phase 12 acceptance; T-001 merged into the working tree.
- **Source authority**: `docs/PHASE_12_EXTERNAL_PAPER_SHADOW_READINESS_DECISIONS.md` (sanitized
  field inventory).
- **Files allowed to change**: `scripts/report_paper_shadow_readiness.py` (new),
  `tests/test_report_paper_shadow_readiness.py` (new).
- **Contracts and invariants**: output is deterministic for a given artifact and render time input;
  render time must be passed explicitly (`--rendered-at-utc`) so the report is reproducible.
- **Implementation steps**: repository read → strict Pydantic projection listing ONLY the allowed
  fields → canonical JSON + Markdown render → hash.
- **Data/licensing/security posture**: reads only sanitized fields already persisted by the
  accepted Phase 12 schema.
- **Migration/rollback**: none; delete files to roll back.
- **Acceptance commands**: `.\.venv\Scripts\python.exe -m pytest
  tests/test_report_paper_shadow_readiness.py -q`; then, against a mock artifact created by T-001's
  roundtrip, run the report command and inspect output.
- **Positive assertions (literal)**: report JSON contains `"outcome"`, exactly eight `"checks"`
  entries in canonical order, and `"simulated_paper_only": true`.
- **Negative/adversarial assertions (literal)**: a fixture artifact whose sanitized fields are
  seeded with canary strings in disallowed positions fails the projection with a fixed error; the
  strings `FABLE5_ALPACA` and any 20+ character uppercase key-like token never appear in the
  report; requesting a nonexistent ID exits 2 with the fixed message and no stack trace; the
  command performs zero INSERT/UPDATE/DELETE (asserted via a read-only DB role or statement audit).
- **Audit evidence**: the report itself (hashes + UTC timestamps + git SHA).
- **Definition of done**: acceptance commands pass; negative assertions proven; zero writes proven.
- **Stop condition**: stop after the report generator; do not begin UI work; do not commit.
- **Dependencies**: T-001.

---

### T-003 (P0) — Sanitized read-only readiness presentation in the frontend

- **Task ID**: T-003
- **Title**: External paper-readiness view (new route, generated contracts, prominent boundary
  banner)
- **Target phase/boundary**: maintenance inside the accepted Phase 12 + Phase 8 boundaries;
  additive UI only
- **Priority**: P0
- **Estimated effort**: 5–8 h
- **User-visible outcome**: the operator (and any observer) opens
  `http://127.0.0.1:3000/paper/readiness`, pastes an assessment ID, and sees the eight checks,
  outcome, market-clock state, feed identity, the recorded expiry timestamp, and a prominent
  "Simulated / Paper Only / No Advice" banner — with no credential field and no mutation control.
- **Objective**: add a new Next.js route `services/frontend/src/app/paper/readiness/` that calls
  `GET /v1/paper-shadow-readiness/{id}` through the **generated** TypeScript contracts
  (`packages/contracts`), renders sanitized evidence exactly as returned, labels mock artifacts
  "MOCK — local contract proof only", renders `BLOCKED` reasons verbatim, and states
  `Historical readiness evidence. Browser time is not authority for currentness or expiry.` The UI
  may show `expires_at_utc`, but only a fresh accepted observation or explicitly time-bound
  server/CLI report can establish currentness. No polling; one fetch per explicit user action.
- **Explicit exclusions**: do not modify the existing Paper Status page, shared layout, or any
  frozen Phase 8/10 visual baseline; no credential input; no capture trigger from the browser
  (capture stays a local CLI); no websocket; no auto-refresh; no new API route; no hand-written
  response types.
- **Prerequisite evidence**: Phase 12 generated contracts exist in `packages/contracts`
  (README records Phase 12 readiness contracts as generated).
- **Source authority**: `docs/PHASE_08_UI_DECISIONS.md`,
  `docs/PHASE_12_EXTERNAL_PAPER_SHADOW_READINESS_DECISIONS.md`.
- **Files allowed to change**: `services/frontend/src/app/paper/readiness/**` (new),
  `services/frontend/src/tests/**` (new test files only), new e2e spec files for this route only.
- **Contracts and invariants**: generated contracts are the only type authority; the route is
  additive; existing pages remain byte-identical; accessibility per the repository's serial a11y
  conventions; both light/dark themes. No browser clock, timer, hydration calculation, or timestamp
  comparison may classify historical evidence as current or expired.
- **Implementation steps**: route + client component → contract client call → render states
  (loading, 404, 409, 422, 200-completed, 200-blocked, historical, mock) → a11y labels → new-route e2e
  accessibility and visual specs with fresh baselines for this route only.
- **Data/licensing/security posture**: displays only sanitized persisted evidence; no vendor call
  from the browser; no raw quote price exists in the evidence to display.
- **Migration/rollback**: none; delete the new route directory to roll back.
- **Acceptance commands**: `npm test`; `npm run typecheck`; `npm run contracts:check`;
  `npm run build`; the new-route e2e specs on Windows.
- **Positive assertions (literal)**: the rendered page contains the exact strings
  `Simulated / Paper Only / No Advice`, `order_submission_authorized = false` (or its labeled
  equivalent rendered from the contract fields),
  `Historical readiness evidence. Browser time is not authority for currentness or expiry.`, and
  all eight check names from the frozen registry.
- **Negative/adversarial assertions (literal)**: the page source and bundle contain no
  `FABLE5_ALPACA` string and no credential-shaped input element; entering a malformed ID renders
  the typed 422 state without a network retry loop; the existing Paper Status page snapshot remains
  unchanged (`git diff --stat` shows no modification to existing frontend files); mutation verbs
  are absent from the route's network activity (e2e network log shows GET only); the readiness
  route contains no `Date.now`, `new Date`, `performance.now`, `setTimeout`, or `setInterval` token.
- **Frozen-baseline reconciliation**: Phase 17 is evaluated only from
  `7c4df26733b4ad13c49c455ea5f28f627012ee44` to its accepted commit
  `fd89d3905e9c2ea12223e30b5822a0fdda795a26`; Phase 18 is evaluated only from that commit to its
  accepted commit `16aac187fc3dbd6015306603c18be6e08cea8e4e`. Both historical diffs remain
  empty across their frozen frontend/API/contract scopes. Their present-day guard admits exactly
  the six later T-003 files under `services/frontend/src` and rejects every missing or additional
  path; the full 20-path initial overlay and subsequent repair delta are separately pinned in
  `tests/test_repository_policy.py`.
- **Audit evidence**: e2e artifacts for the new route plus `npm run contracts:check` output.
- **Definition of done**: all acceptance commands pass on Windows; existing pages and baselines
  untouched; new-route specs committed alongside.
- **Stop condition**: stop after this route; do not restyle other modes; do not add capture
  controls; do not commit.
- **Dependencies**: none (parallel to T-001/T-002); the runbook uses it if ready, else the GET via
  `curl`/browser JSON suffices.

---

### T-004 (P1) — End-to-end smoke harness (mock always; credentialed only when authorized)

- **Task ID**: T-004
- **Title**: Scripted end-to-end smoke: preflight → capture → report
- **Target phase/boundary**: maintenance inside the accepted Phase 12 boundary
- **Priority**: P1
- **Estimated effort**: 2–3 h
- **User-visible outcome**: one documented command sequence (PowerShell script) that runs T-001
  preflight, then either the mock roundtrip or — only with credentials present and explicit
  `-ConfirmCredentialedProbe` — the accepted capture command, then T-002's report.
- **Objective**: `scripts/run_paper_smoke.ps1` orchestrating existing commands; no new Python
  surface. The credentialed branch requires both the switch and the env pair; otherwise it prints
  the fixed line `Mock fallback: MOCK_PROOF_COMPLETE proves the local contract only.` and runs the
  mock path.
- **Explicit exclusions**: no retries; no scheduling; no capture-CLI modification; the script never
  reads or echoes credential values; no commit.
- **Prerequisite evidence**: T-001, T-002 complete.
- **Source authority**: this file §10 runbook.
- **Files allowed to change**: `scripts/run_paper_smoke.ps1` (new),
  `tests/test_run_paper_smoke_static.py` (new; static assertions on the script text).
- **Contracts and invariants**: the script is a thin sequencer; every step's exit code is checked;
  failure stops the sequence.
- **Implementation steps**: script; static test asserting the script contains no credential echo,
  no non-paper host, no order verb.
- **Data/licensing/security posture**: as T-001/T-002.
- **Migration/rollback**: delete files.
- **Acceptance commands**: `.\.venv\Scripts\python.exe -m pytest
  tests/test_run_paper_smoke_static.py -q`; a mock-path run end-to-end.
- **Positive assertions (literal)**: mock path exits 0 and produces both a preflight report and an
  evidence report.
- **Negative/adversarial assertions (literal)**: script text contains none of `api.alpaca.markets`
  (the non-paper host as a standalone literal), `POST`, `DELETE`, `order`, `submit`; running with
  `-ConfirmCredentialedProbe` but absent credentials exits nonzero before any network activity.
- **Audit evidence**: both reports.
- **Definition of done**: mock path proven end-to-end on Windows.
- **Stop condition**: stop after the harness; do not run the credentialed branch inside CI or
  tests.
- **Dependencies**: T-001, T-002.

---

### T-005 (P1) — Secret-leak and forbidden-live-path static sweep

- **Task ID**: T-005
- **Title**: Repository-wide static assertions against live paths and secret leakage in the new
  operator surface
- **Target phase/boundary**: Phase 1 static-check conventions; additive tests only
- **Priority**: P1
- **Estimated effort**: 2–3 h
- **User-visible outcome**: CI-runnable proof that the new operator scripts and UI introduce no
  live endpoint, mutation verb, or credential echo.
- **Objective**: add `tests/test_paper_smoke_static.py` asserting, over
  `scripts/preflight_paper_smoke.py`, `scripts/report_paper_shadow_readiness.py`,
  `scripts/run_paper_smoke.ps1`, and `services/frontend/src/app/paper/readiness/**`: only the two
  documented paper/data hosts may appear; no `live` execution-mode token; no
  `requests.post|put|delete` or fetch with a mutation method; no `print`/log of either credential
  variable's value; canary-based leak tests for all report outputs.
- **Explicit exclusions**: do not modify `scripts/verify_phase1.py` (its phase-locked checks are
  part of the accepted/pending Phase 26 surface); do not relax any existing static test.
- **Prerequisite evidence**: T-001–T-004 file names fixed.
- **Source authority**: `AGENTS.md` § External observation and free-source rules.
- **Files allowed to change**: `tests/test_paper_smoke_static.py` (new).
- **Contracts and invariants**: assertions are literal string/AST checks; failures name the file
  and pattern with no secret echo.
- **Implementation steps**: AST walk + literal scans; fixtures with canaries.
- **Data/licensing/security posture**: static only.
- **Migration/rollback**: delete the file.
- **Acceptance commands**: `.\.venv\Scripts\python.exe -m pytest tests/test_paper_smoke_static.py
  -q`; full `pytest` remains green.
- **Positive assertions (literal)**: test module enumerates exactly the files listed above and
  passes.
- **Negative/adversarial assertions (literal)**: planting the literal `https://api.alpaca.markets`
  or `execution_mode = "live"` in any swept file makes the sweep fail (proven via a tmp-copy
  fixture, not by editing real files).
- **Audit evidence**: pytest output.
- **Definition of done**: sweep passes and its self-test (fixture-injection) proves it can fail.
- **Stop condition**: stop after the sweep; do not extend to unrelated directories.
- **Dependencies**: T-001, T-002, T-003, T-004 (file paths).

---

### T-006 (P1) — Source-health / freshness evidence without strategy use

- **Task ID**: T-006
- **Title**: Read-only readiness-history freshness summary CLI
- **Target phase/boundary**: maintenance inside the accepted Phase 12 boundary
- **Priority**: P1
- **Estimated effort**: 2–3 h
- **User-visible outcome**: the operator lists all persisted readiness assessments with age,
  expiry state, source kind, and outcome — evidence of source health over time with no strategy
  interpretation.
- **Objective**: `scripts/list_paper_shadow_readiness.py` reading the append-only tables (SELECT
  only), printing a sanitized table plus canonical JSON: assessment ID, source kind, outcome,
  created/expiry UTC, expired flag, check pass counts. Includes the fixed disclaimer line
  `Source-health evidence only. Not market data, not a strategy input, not advice.`
- **Explicit exclusions**: no external call; no write; no aggregation that reconstructs prices; no
  new API route.
- **Prerequisite evidence**: Phase 12 acceptance.
- **Source authority**: Phase 12 decisions (sanitized field inventory).
- **Files allowed to change**: `scripts/list_paper_shadow_readiness.py` (new),
  `tests/test_list_paper_shadow_readiness.py` (new).
- **Contracts and invariants**: deterministic ordering (created UTC, then ID); zero writes.
- **Implementation steps**: repository query → projection → render; tests over mock-created rows.
- **Data/licensing/security posture**: sanitized persisted fields only.
- **Migration/rollback**: delete files.
- **Acceptance commands**: `.\.venv\Scripts\python.exe -m pytest
  tests/test_list_paper_shadow_readiness.py -q`.
- **Positive assertions (literal)**: output contains the disclaimer line and one row per persisted
  root.
- **Negative/adversarial assertions (literal)**: output contains no field named or valued like
  price/quote/position/order-detail; zero INSERT/UPDATE/DELETE statements issued.
- **Audit evidence**: command output with UTC timestamps and git SHA header.
- **Definition of done**: tests pass; zero-write proof.
- **Stop condition**: stop after the CLI.
- **Dependencies**: T-001 (mock rows for testing).

---

### T-007 (P1) — SEC EDGAR policy/currentness and schema-qualification plan (documentation only)

- **Task ID**: T-007
- **Title**: `docs/PLAN_SEC_EDGAR_QUALIFICATION.md`
- **Target phase/boundary**: documentation feeding the proposed Phase 27; no implementation
- **Priority**: P1
- **Estimated effort**: 2–4 h
- **User-visible outcome**: a plan any later authorized phase can execute to revalidate SEC policy
  and freeze EDGAR schemas for the Phase 26 `as_reported_fundamentals` capability.
- **Objective**: document, with first-party citations and UTC retrieval dates: the exact bulk
  products (nightly `submissions.zip`, `companyfacts.zip`, indexes), documented fair-access limits
  and declared User-Agent policy, update cadence, acceptance-datetime semantics as the
  point-in-time availability field, the planned schema-freeze method (JSON Schema snapshots +
  hashes), and the exact evidence rows a Phase 27 intake would require.
- **Explicit exclusions**: no bulk download; no schema capture; no code; no claim that policy
  review equals qualification.
- **Prerequisite evidence**: `docs/DATA_SOURCES.md` candidate matrix (2026-07-21).
- **Source authority**: SEC first-party pages cited in the matrix.
- **Files allowed to change**: `docs/PLAN_SEC_EDGAR_QUALIFICATION.md` (new).
- **Contracts and invariants**: every factual claim carries a first-party URL + retrieval date;
  unverifiable items are labeled `RIGHTS_UNVERIFIED` or `UNVERIFIED`.
- **Implementation steps**: draft → cite → cross-check against Phase 18's SEC row → record deltas.
- **Data/licensing/security posture**: documentation-only.
- **Migration/rollback**: delete the file.
- **Acceptance commands**: `.\.venv\Scripts\python.exe scripts/verify_phase1.py --static-only
  --phase 26` (still green); markdown renders.
- **Positive assertions (literal)**: the document contains a "What this plan does NOT do" section
  naming download, persistence, and qualification.
- **Negative/adversarial assertions (literal)**: the document contains no instruction to fetch
  bulk data before Phase 27 authorization.
- **Audit evidence**: citations with UTC dates.
- **Definition of done**: plan complete, cited, consistent with Phase 26 dependency 3.
- **Stop condition**: stop at the document.
- **Dependencies**: none.

---

### T-008 (P2) — BLS release-time corroboration feasibility memo (documentation only)

- **Task ID**: T-008
- **Title**: `docs/MEMO_BLS_RELEASE_TIME_CORROBORATION.md`
- **Target phase/boundary**: documentation feeding later RTDSM vintage reconciliation; no
  implementation
- **Priority**: P2
- **Estimated effort**: 2–3 h
- **User-visible outcome**: a memo stating whether and how official BLS release schedules and API
  metadata can corroborate RTDSM PCPI vintage timing.
- **Objective**: document the BLS Public Data API v2 registered/unregistered limits, terms, the
  official CPI news-release schedule as the release-time source, and the exact reconciliation
  procedure a later phase could run — while stating plainly that BLS current-value series are
  **not** vintages and cannot substitute for RTDSM vintage data
  (`POINT_IN_TIME_INADEQUATE` for research).
- **Explicit exclusions**: no API registration, no API calls, no data download; no vintage
  substitution claim.
- **Prerequisite evidence**: `docs/DATA_SOURCES.md` matrix; Phase 22/26 RTDSM boundary text.
- **Source authority**: BLS first-party pages cited in the matrix.
- **Files allowed to change**: `docs/MEMO_BLS_RELEASE_TIME_CORROBORATION.md` (new).
- **Contracts and invariants**: citations + UTC dates; the sentence "BLS API values are current
  revised values, not vintages" must appear.
- **Implementation steps**: draft → cite → align with Phase 26's "exact BLS release-time
  reconciliation" dependency wording.
- **Data/licensing/security posture**: documentation-only.
- **Migration/rollback**: delete the file.
- **Acceptance commands**: static verifier stays green; markdown renders.
- **Positive assertions (literal)**: memo contains the exact sentence above.
- **Negative/adversarial assertions (literal)**: memo contains no statement that BLS data
  satisfies any Phase 15 gap.
- **Audit evidence**: citations with UTC dates.
- **Definition of done**: memo complete and consistent with Phase 22–26 language.
- **Stop condition**: stop at the memo.
- **Dependencies**: none.

---

### T-009 (P1) — CRSP and RTDSM rights/entitlement evidence-requirements package (documentation only)

- **Task ID**: T-009
- **Title**: `docs/RIGHTS_EVIDENCE_REQUIREMENTS_FAMILY_A.md`
- **Target phase/boundary**: documentation feeding the proposed Phase 27; no outreach, no
  implementation
- **Priority**: P1
- **Estimated effort**: 3–4 h
- **User-visible outcome**: the repository owner gets exact checklists of what evidence to obtain
  from CRSP/Morningstar and the Philadelphia Fed, in the format the Phase 25 intake models already
  accept.
- **Objective**: enumerate, per provider: the exact executed-agreement fields required (legal
  entity, SKU/product, Linux flat-file delivery entitlement, territory, permitted uses —
  storage/non-display/derived/retention/redistribution — audit and termination terms) for CRSP;
  the authenticated exact-scope response answering all ten Phase 24 questions for RTDSM; the
  acceptable-evidence forms per Phase 25 (`EMAIL_ONLY` etc. can be recorded but never verify
  authority); and how each item maps to Phase 25's Pydantic intake fields.
- **Explicit exclusions**: no provider contact by Codex; no drafting of outbound email as a sent
  artifact; no recording of any claimed response without independent verification fields.
- **Prerequisite evidence**: Phase 24 questions, Phase 25 intake models, Phase 26 dependencies.
- **Source authority**: `docs/PHASE_24_…DECISIONS.md`, `docs/PHASE_25_…DECISIONS.md`,
  `docs/PHASE_26_…DECISIONS.md`.
- **Files allowed to change**: `docs/RIGHTS_EVIDENCE_REQUIREMENTS_FAMILY_A.md` (new).
- **Contracts and invariants**: every checklist row cites the phase artifact field it satisfies.
- **Implementation steps**: extract fields from Phase 24/25 docs → tabulate → map.
- **Data/licensing/security posture**: documentation-only; no credential, no PII beyond the
  already-defined `REQUESTING_REPOSITORY_OWNER` identity convention.
- **Migration/rollback**: delete the file.
- **Acceptance commands**: static verifier stays green.
- **Positive assertions (literal)**: all ten Phase 24 question codes appear; all three Phase 26
  post-selection dependencies appear.
- **Negative/adversarial assertions (literal)**: the document nowhere states that public research
  language, an API key, or retrieval success is rights evidence.
- **Audit evidence**: field-mapping table.
- **Definition of done**: checklists complete and mapped.
- **Stop condition**: stop at the document; outreach is a human action outside this repo.
- **Dependencies**: none.

---

### T-010 (P1) — Documentation/status reconciliation and automated stale-status check

- **Task ID**: T-010
- **Title**: Status-currency test + CLAUDE.md mirror decision
- **Target phase/boundary**: Phase 1 documentation conventions; additive test only
- **Priority**: P1
- **Estimated effort**: 2–3 h
- **User-visible outcome**: CI fails whenever README's "Next step" stops mentioning the highest
  phase present under `docs/handoffs/`, preventing the staleness found on 2026-07-21.
- **Objective**: add `tests/test_status_currency.py` asserting: (1) the maximum `PHASE_NN` in
  `docs/handoffs/` is mentioned in README's `## Next step` section; (2) README contains exactly one
  `## Next step` heading; (3) `AGENTS.md` and `CLAUDE.md` both begin with the pinned hard-gate
  prefix (reusing the existing helper). Additionally, mirror the 2026-07-21 "External observation
  and free-source rules" section from `AGENTS.md` into `CLAUDE.md` verbatim so the two files do not
  diverge (both begin with the identical pinned prefix; the mirror is additive).
- **Explicit exclusions**: do not rewrite history sections; do not touch accepted phase decision
  docs; do not change the pinned gate text.
- **Prerequisite evidence**: `tests/test_repository_policy.py::test_hard_gates_are_exact_file_prefixes`.
- **Source authority**: `AGENTS.md`; this file.
- **Files allowed to change**: `tests/test_status_currency.py` (new), `CLAUDE.md` (append the
  mirrored section only).
- **Contracts and invariants**: the new test must pass on the current working tree after the
  2026-07-21 documentation updates.
- **Implementation steps**: glob handoffs → regex README → assert; append mirror; run policy
  tests.
- **Data/licensing/security posture**: documentation/tests only.
- **Migration/rollback**: delete the test; revert the CLAUDE.md append.
- **Acceptance commands**: `.\.venv\Scripts\python.exe -m pytest tests/test_status_currency.py
  tests/test_repository_policy.py -q`.
- **Positive assertions (literal)**: both files still start with the gate text whose SHA-256 is
  `1c6586b54c77c5a9df8e9838638631127cb2e5bc0af1c813b27b7f6af355d672`.
- **Negative/adversarial assertions (literal)**: temporarily renaming a copy of
  `docs/handoffs/PHASE_26.md` to `PHASE_27.md` in a tmp fixture makes the currency assertion fail.
- **Audit evidence**: pytest output.
- **Definition of done**: tests pass; mirror applied; no other doc changed.
- **Stop condition**: stop after the test and mirror.
- **Dependencies**: none.

## 10. Runbook — 2026-07-23 external live-data paper smoke test

Operator: repository owner. Window: 09:30–16:00 ET (13:30–20:00 UTC). All commands from the
repository root in PowerShell. **This runbook submits no order and cannot.** If any step fails,
record the failure and consult §11/§12 — do not improvise.

1. **Authorize.** Record (a dated line in your own notes is sufficient) the explicit human
   authorization for one credentialed read-only readiness probe under the accepted Phase 12
   boundary (prerequisite H1).
2. **Preserve the tree.** `git status --short` — confirm the Phase 26 working-tree files are
   present and untouched. Confirm both `OpenAlice/` and `cli/` are absent beneath `Trade/`; their
   verified quarantine directories are outside the repository and must not be copied back, adopted,
   edited, or deleted through this runbook. Any reappearance is an immediate NO-GO.
3. **Start the stack.** `docker compose up --build --wait`, then confirm
   `Invoke-RestMethod http://127.0.0.1:8000/health` returns
   `{"status":"ok","service":"api","mode":"research-paper-only"}`.
4. **Preflight.** With the stack up:
   `$env:FABLE5_DATABASE_URL = "postgresql+psycopg://fable5:fable5_dev_only@127.0.0.1:5432/fable5"`;
   `$env:FABLE5_CODE_VERSION_GIT_SHA = (git rev-parse HEAD)`;
   `.\.venv\Scripts\python.exe scripts\preflight_paper_smoke.py --output preflight.json` (T-001,
   implemented). The current repository expectation is that `phase26_static_verification` passes
   through the unchanged implementation policy plus the exact content-pinned 29-path maintenance
   policy. Any nonzero preflight or direct
   `.\.venv\Scripts\python.exe scripts\verify_phase1.py --static-only --phase 26` result is a
   mandatory NO-GO: do not inspect credentials or run step 7; continue only to the mock
   demonstration in step 5, record the blocker, and stop.
5. **Mock demonstration (always).** Run the mock roundtrip (T-001 or the Phase 12 mock tests) and
   confirm `MOCK_PROOF_COMPLETE`. Say out loud what it is: local contract proof, not external
   readiness.
6. **Credentials (only if H1–H3 hold).** In the operator shell only:
   `$env:FABLE5_ALPACA_PAPER_API_KEY_ID = "<paper key id>"`;
   `$env:FABLE5_ALPACA_PAPER_SECRET_KEY = "<paper secret>"`. Never echo them; never write them to a
   file. Confirm in the Alpaca dashboard that the keys are for the **paper** environment and the
   paper account has zero positions and zero open orders.
7. **Credentialed capture.**
   `.\.venv\Scripts\python.exe scripts\capture_paper_shadow_readiness.py --idempotency-key
   smoke-2026-07-23-01 --confirm-paper-only-readiness`. Expected within market hours on a clean
   paper account: outcome `SHADOW_READY` with all eight checks `PASS`. Any other honest result is
   `BLOCKED` with fixed reason codes — that is a valid test result, not an error to route around.
8. **Retrieve evidence.** Take `readiness_assessment_id` from the capture output and fetch
   `http://127.0.0.1:8000/v1/paper-shadow-readiness/<id>` (browser or `Invoke-RestMethod`). Note
   the artifact expires 60 s after completion; expiry is expected and makes it historical evidence.
9. **Present.** If T-003 is deployed, open `http://127.0.0.1:3000/paper/readiness`, load the ID,
   and confirm the "Simulated / Paper Only / No Advice" banner and the eight checks. Otherwise
   present the GET JSON plus the existing Paper Status banner.
10. **Report.** `.\.venv\Scripts\python.exe scripts\report_paper_shadow_readiness.py
    --assessment-id <id> --rendered-at-utc <now> --output evidence-2026-07-23.md` (T-002). Verify
    the report contains hashes, UTC timestamps, and the git SHA — and no credential, account
    identifier, raw body, order detail, or quote price.
11. **Close.** `Remove-Item Env:FABLE5_ALPACA_PAPER_API_KEY_ID`;
    `Remove-Item Env:FABLE5_ALPACA_PAPER_SECRET_KEY`; `docker compose down`. Store the two report
    files outside the repo or leave untracked; do not commit them with secrets-adjacent shell
    history, and never commit credential material.

## 11. Go / no-go checklist

GO requires all of: repository acceptance checks pass — the Phase 12/26 pytest suites,
repository-policy tests, `verify_phase1.py --static-only --phase 26`, and the clean-identity full
`verify_phase1.py --phase 26` gate must all exit zero;
credentials provably paper-only (dashboard-confirmed paper keys; the
adapter itself refuses non-paper hosts by construction); no live endpoint or live execution
configuration anywhere; Phase 26 working-tree changes intact before and after; no secret in any
log, output, artifact, or report; no accepted redirect or unexpected host (the transport refuses
both); adapter exposes only the six inspections (no mutation or generic request); no raw
account/order/position/provider body persisted; no quote treated as strategy-valid data; UI/report
carries the simulated-paper/no-advice label; evidence carries config/transport hash, evidence ID,
git SHA, and UTC timestamps (seed/trial count not applicable to Phase 12 readiness and recorded as
such); no ignored or nested checkout inside the repository exposes an order, liquidation, generic
mutation, or live-money path. The current tree satisfies this checkout-location gate because both
`OpenAlice/` and `cli/` are absent; either path reappearing fails it immediately.

NO-GO if any item above fails, if the operator cannot confirm H1–H4, or if any step would require
modifying accepted Phase 12 files or discarding Phase 26 work. On NO-GO: run the mock
demonstration only (step 5), record the blocking condition in the evidence report, and stop.

## 12. Rollback and incident procedure

- **Normal rollback**: `docker compose down` (volumes persist); remove the two credential env vars
  from the shell; readiness evidence is append-only historical data and is intentionally not
  deleted. New scripts/routes from T-001–T-006 are additive; deleting the new files is a complete
  rollback. Never `git reset`/`checkout --`/`clean` — the Phase 26 working tree must survive.
- **Suspected secret exposure** (a credential value appears in any output, file, or terminal
  capture): immediately revoke/regenerate the paper keys in the Alpaca dashboard; delete the
  contaminated local file or clear terminal history; record an incident note (UTC time, what
  leaked, where, remediation); do not commit anything until resolved.
- **Unexpected external behavior** (redirects, wrong host, oversized responses): the transport
  fails closed to `BLOCKED`; keep the artifact as evidence; do not retry in a loop; file the
  reason code in the report.
- **Database incident**: a persistence failure after reads creates no authority and no partial
  artifact per Phase 12 semantics; rerun requires a fresh explicit idempotency key.

## 13. Definition of success (2026-07-23)

1. One preflight report with zero secret leakage and every required gate at exit zero. A documented
   nonzero result remains a failure and cannot be acknowledged into success.
2. One mock artifact `MOCK_PROOF_COMPLETE`, labeled as local contract proof.
3. If authorized/credentialed: one external artifact with an honest `SHADOW_READY` or `BLOCKED`
   outcome retrieved via the GET, presented with the simulated/no-advice boundary.
4. One sanitized evidence report with hashes, UTC timestamps, and git SHA — and provably no
   credential, account identifier, raw body, order detail, or quote price.
5. Phase 26 working tree byte-identical before/after; no commit, push, or publication occurred.
6. Nobody claimed Track B progress, research qualification, or execution readiness.

## 14. Deferred and rejected ideas

- **Deferred**: websocket/streaming market data (new vendor surface; new rights review);
  scheduled/recurring readiness captures (Phase 12 forbids schedulers; revisit only with a new
  authorized phase); multi-assessment readiness dashboards with history charts (needs a list API —
  new surface); Tiingo credentialed qualification capture (already authorized machinery exists in
  Phase 13, but it is a separate activity that would dilute tomorrow's scope).
- **Rejected**: any external paper **order** demonstration (excluded by AGENTS.md and this plan's
  rules; would require its own separately authorized phase decision package and is not proposed
  here); persisting IEX quotes for charts or "warm-up" research (raw-price persistence is
  forbidden; demo data ≠ research data); FRED/ALFRED integration under current terms (documented
  prohibitions on the planned software/model/persistent use); yfinance as an operational source
  (software license ≠ data rights; unofficial surface; `RIGHTS_UNVERIFIED`); changing the frozen
  `AAPL`/IEX probe to a "more interesting" symbol (the probe is frozen by accepted Phase 12
  decisions and is not a strategy input); relabeling readiness or qualification evidence as
  research eligibility (forbidden by Phases 13–15 semantics).
