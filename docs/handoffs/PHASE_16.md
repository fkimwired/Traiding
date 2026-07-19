# Phase 16 Family A point-in-time source-plan handoff

## Objective and exclusions

Implement one deterministic, database-free, network-disabled, portable Family A point-in-time source
plan. It binds the accepted Phase 15 artifact, freezes twelve source-plan requirements, seven
required capabilities, six candidate-only rows, seven ordered future steps, and all nineteen
unchanged Phase 15 gaps. The only outcomes are `PLAN_FROZEN` and `BLOCKED`.

The plan is not a source selection or data-admission decision. Do not add or use a credential,
provider call, transport, vendor SDK, external sample, licensed payload, dataset path, observation,
ingestion, normalization execution, quarantine execution, snapshot, evaluation threshold, embargo
decision, holdout, research run, performance result, promotion, approval, risk mutation,
broker/order/fill behavior, API, migration, frontend product control, live path, publication,
deployment, or later phase.

## Accepted input identity

Start only from the formally accepted Phase 15 identity:

- Commit: `5b3052eb8f020d77cc3750b34190b4b2fa5fc16c`
- Tree: `7fab5a2b2eb2f8f821b969d9cb031c806e064d28`
- Phase 15 artifact id: `c29b8139-da80-556b-b150-a5ca9603d265`
- Phase 15 artifact SHA-256: `575ce4c51e9102790d75edc4a330c3e9f1d9eb505eb33ccf22d8a9c9e50200d6`
- Phase 15 policy SHA-256: `ba4603caaffe90d561f3beaa566746b1f3b900e2cf7d5e24b2cd94537597821b`
- Phase 15 requirements-manifest SHA-256:
  `7743721c6fe46bc0847bb189c4db7dedc4325b4cc05aa6007c7921eb348f73b6`
- Phase 15 gaps-manifest SHA-256:
  `9c70f11f85eb66dad6eed15a0a4907dec3fa4edc7b0da3d6adbad768b88b2f86`
- Windows full Phase 15 verifier passed with complete cleanup and the same clean identity.
- Ubuntu run `29661065413`: `preflight`, `unit`, and `phase15-compose` passed at that identity.

Stop before editing if `HEAD`/tree differs, the worktree or index is dirty, branch state is ambiguous,
or the Phase 15 artifact does not reproduce those identities.

Authority sources:

- `AGENTS.md`
- `RESEARCH_SUPPLEMENT.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/EVALS.md`
- `docs/RISK_POLICY.md`
- `docs/DATA_SOURCES.md`
- `docs/COMPLIANCE_NOTES.md`
- `docs/PHASE_04_DATA_DECISIONS.md`
- `docs/PHASE_06_RESEARCH_DECISIONS.md`
- `docs/PHASE_13_POINT_IN_TIME_DATA_QUALIFICATION_DECISIONS.md`
- `docs/PHASE_14_RESEARCH_INGESTION_ELIGIBILITY_DECISIONS.md`
- `docs/PHASE_15_FAMILY_A_RESEARCH_ADMISSION_SPECIFICATION_DECISIONS.md`
- `docs/PHASE_16_FAMILY_A_POINT_IN_TIME_SOURCE_PLAN_DECISIONS.md`

## Exact write allowlist

Write only:

```text
.github/workflows/ci.yml
Makefile
README.md
docs/COMPLIANCE_NOTES.md
docs/DATA_SOURCES.md
docs/EVALS.md
docs/IMPLEMENTATION_PLAN.md
docs/PHASE_16_FAMILY_A_POINT_IN_TIME_SOURCE_PLAN.json
docs/PHASE_16_FAMILY_A_POINT_IN_TIME_SOURCE_PLAN_DECISIONS.md
docs/RISK_POLICY.md
docs/handoffs/PHASE_16.md
scripts/check.ps1
scripts/check.sh
scripts/generate_family_a_point_in_time_source_plan.py
scripts/verify_family_a_point_in_time_source_plan.py
scripts/verify_phase1.py
services/data/src/fable5_data/phase16/__init__.py
services/data/src/fable5_data/phase16/canonical.py
services/data/src/fable5_data/phase16/contracts.py
services/data/src/fable5_data/phase16/plan.py
services/data/tests/test_phase16_contracts.py
services/data/tests/test_phase16_plan.py
services/data/tests/test_phase16_security.py
services/frontend/e2e/phase8.accessibility.spec.ts
services/frontend/e2e/phase8.visual.spec.ts
tests/test_phase5_postgres.py
tests/test_phase9_static.py
tests/test_phase10_static.py
tests/test_phase11_static.py
tests/test_phase12_static.py
tests/test_phase13_static.py
tests/test_phase14_static.py
tests/test_phase15_static.py
tests/test_phase16_portable.py
tests/test_phase16_static.py
tests/test_repository_policy.py
```

Stop before any write outside this list. Do not modify Compose, dependencies, environment examples,
any migration, API code/test, generated OpenAPI/TypeScript contract, `scripts/run_phase_gate.py`,
accepted Phase 4-15 production code, paper/research/risk services, frontend product code, or visual
baseline. The inherited browser specs are permitted only for the Phase 16 range; do not alter product
assertions or snapshots.

## Contracts and invariants

Use exactly:

```text
outcomes: PLAN_FROZEN, BLOCKED
requirement statuses: PASS, BLOCKED, UNCOMPUTABLE
candidate states: UNPROVEN, MISSING
Phase 15 gap states: PRESENT, MOCK_ONLY, STALE, MISSING, UNPROVEN
step state: NOT_STARTED
fixed timestamp: 2026-07-18T00:00:00Z
```

Exact schema/policy domains:

```text
phase16-family-a-point-in-time-source-plan-v1
phase16-family-a-point-in-time-source-plan-policy-v1
phase16-family-a-point-in-time-source-plan-requirement-v1
phase16-family-a-point-in-time-source-plan-capability-v1
phase16-family-a-point-in-time-source-plan-candidate-v1
phase16-family-a-point-in-time-source-plan-step-v1
phase16-family-a-point-in-time-source-plan-gap-binding-v1
phase16-source-plan-requirements-manifest-v1
phase16-source-plan-capabilities-manifest-v1
phase16-source-plan-candidates-manifest-v1
phase16-source-plan-steps-manifest-v1
phase16-source-plan-gap-bindings-manifest-v1
phase16-source-plan-evidence-v1
artifact UUID namespace: 657156b0-345e-5d6e-ae1b-1f27e32b40ac
artifact id: e106a766-5cfe-5a1c-94f6-ee1c2ac68652
artifact SHA-256: 74ddf4a51d722b494fd494241e2e5927bff6fde034f6932dcfd791bb3a0706bb
policy SHA-256: 57cfcfd09f2d4a87d9562fd536228b9f05693bb71b7e9d1867618a35da7d4efd
canonical size: 22,776 bytes
```

Bind the exact accepted Family A source specification:

```text
phase6-a_cross_sectional_equity_ranking-research-pipeline
v2
3967b3c0dffd6a27c4ac8012773621090b828e8bdc2f242611c34d81420b37bc
```

Exact ordered requirement registry:

```text
PHASE15_ADMISSION_SPECIFICATION_BOUND
FAMILY_A_CAPABILITY_SET_BOUND
SECURITY_MASTER_IDENTITY_HISTORY_REQUIRED
UNIVERSE_MEMBERSHIP_DELISTING_HISTORY_REQUIRED
RAW_OHLCV_CORPORATE_ACTION_HISTORY_REQUIRED
AS_REPORTED_FUNDAMENTAL_VINTAGES_REQUIRED
SECTOR_LIQUIDITY_HISTORY_REQUIRED
MACRO_VINTAGE_RELEASE_HISTORY_REQUIRED
TEMPORAL_REVISION_COVERAGE_MANIFEST_REQUIRED
INDEPENDENT_RIGHTS_CURRENTNESS_REVIEW_REQUIRED
QUARANTINE_CANONICALIZATION_RECONCILIATION_REQUIRED
CAPTURE_INGESTION_RESEARCH_EXECUTION_AUTHORITY_ABSENT
```

The complete artifact has all twelve requirements at `PASS` with exact reason
`frozen_source_plan_requirement`. Any `BLOCKED` or `UNCOMPUTABLE` requirement produces only
`BLOCKED`, with `requirement_blocked` or `requirement_uncomputable` respectively.

Exact ordered capability registry:

```text
security_master
universe_membership
ohlcv
corporate_actions
delistings
as_reported_fundamentals
macro_regime_inputs
```

Every capability is required and has `source_selected=false`. Capability completeness states only
that the plan row exists; it never qualifies a source or dataset.

Exact ordered candidate registry and states:

```text
TIINGO_PHASE13_BOUNDED_CANDIDATE                         UNPROVEN
MORNINGSTAR_CRSP_US_STOCK_DATABASES_CANDIDATE           UNPROVEN
MORNINGSTAR_CRSP_COMPUSTAT_MERGED_DATABASE_CANDIDATE    UNPROVEN
SEC_EDGAR_SUBMISSIONS_XBRL_CANDIDATE                    UNPROVEN
FEDERAL_RESERVE_ALFRED_VINTAGES_CANDIDATE               UNPROVEN
HISTORICAL_LIQUIDITY_PRODUCT_UNSELECTED                 MISSING
```

Every candidate has `candidate_only=true`, `selected=false`, `rights_verified=false`, and
`external_verification_performed=false`. Official facts may identify documented candidate surfaces
only; they do not prove product scope, schema, complete history, quality, entitlement, or permitted
use. No candidate order expresses a preference or recommendation.

Exact ordered future steps, all `NOT_STARTED`:

```text
SELECT_CANDIDATE_PRODUCTS
REVIEW_CURRENT_USE_RIGHTS
QUALIFY_BOUNDED_READ_ONLY_SAMPLES
PRODUCE_FULL_HISTORY_COVERAGE_MANIFEST
RECONCILE_TEMPORAL_IDENTITY_REVISION_SEMANTICS
DESIGN_LOCAL_QUARANTINE_AND_CANONICAL_SNAPSHOT
REQUEST_SEPARATE_INGESTION_AUTHORITY
```

Preserve the exact prerequisites and required output-hash names frozen in the Phase 16 decision and
canonical implementation. No output is created in Phase 16, and no step may be marked complete.
Before `QUALIFY_BOUNDED_READ_ONLY_SAMPLES` can later start, its machine contract requires both
`non_synthetic_evaluation_policy_sha256` and `confirmation_holdout_definition_sha256`; Phase 16
creates neither value.

Copy and bind the exact nineteen Phase 15 gap codes, states, and row hashes. Every state remains
unchanged. In particular, the full dataset, sector/liquidity/macro history, independent rights,
snapshot persistence, non-synthetic policy/path, research authority, and rights currentness remain
`MISSING`; external qualification, membership/delisting, and embargo applicability remain
`UNPROVEN`; and synthetic mechanics remain `MOCK_ONLY`.

Freeze these fields false:

```text
external_request_performed
external_verification_performed
source_selected
provider_selected
product_selected
credentials_loaded
rights_verified
rights_granted
external_data_capture_authorized
provider_payload_persisted
licensed_data_persisted
research_ingestion_authorized
research_snapshot_created
research_data_eligible
evaluation_policy_approved
confirmation_holdout_defined
confirmation_holdout_opened
research_run_created
research_run_authorized
research_executed
performance_computed
pass_research_granted
strategy_promotion_authorized
paper_approval_granted
risk_clearance_granted
strategy_execution_eligible
execution_authorized
order_submission_authorized
```

Freeze `live_path_absent`, `no_personalized_investment_advice`, and
`no_real_performance_claimed` true.

## Implementation units

1. Strict canonical hashing and frozen contracts with no I/O dependencies.
2. One server-owned immutable plan builder covering the exact registries and unchanged gap bindings.
3. One generator that emits the canonical plan to stdout only.
4. One offline verifier for one supplied regular JSON plan.
5. One committed generated JSON artifact with byte-for-byte generator parity.
6. Static/full verifier, wrappers, inherited browser Phase 16 range, and Ubuntu CI through Phase 16.
7. Data, evaluation, compliance, risk, implementation, service-status, decision, and handoff docs.

## Generator and verifier

Generator:

```text
python scripts/generate_family_a_point_in_time_source_plan.py --confirm-plan-only
```

The confirmation is required and is the only accepted option. Canonical JSON plus one final newline
goes to stdout. No file, database, log, or network write is allowed. Invalid invocation exits 2 with
no stdout and exact stderr `Family A point-in-time source-plan generation failed.`

Verifier:

```text
python scripts/verify_family_a_point_in_time_source_plan.py --plan PATH
```

The verifier reads one regular UTF-8 JSON file of at most 512 KiB and rejects a BOM, duplicate keys, floats,
non-finite values, non-object roots, symbolic/non-regular files, and non-canonical bytes. It performs
strict model, ordering, identity, candidate, step, gap-binding, authority, canonical-byte, and hash
verification against the frozen implementation and emits only deterministic sanitized success JSON.
It has no expected-hash, repair, override, provider, credential, data, policy, authority, or output
option. Invalid input exits 2 with no stdout and exact stderr
`Family A point-in-time source-plan verification failed.` Help exits 0.

## Persistence, API, migration, and rollback

Phase 16 owns no persistence, API, or schema. Retain exactly migrations `0001` through
`0011_phase14`, all 57 inherited tables and all inherited functions, every earlier row, and all OpenAPI and generated
TypeScript bytes. Add no `0012`, route, API model, table, function, trigger, or database connection.

The inherited nonempty `0010_phase13 -> 0011_phase14 -> 0010_phase13 -> 0011_phase14` cycle remains
the rollback proof. Phase 16 acceptance adds no-schema/no-API-drift proof and zero-write snapshots
around every portable and inherited-browser stage. Phase 8 browser checks remain stage-local at
`0007_phase7`; Phase 10/11 browser checks remain stage-local at `0008_phase10`. Do not defer them to
the final Phase 16 migration head.

## Acceptance

Require:

- Parser/wrappers accept Phases 1-16 and reject 0/17/malformed input with exit 2.
- Exact Phase 16 allowlist and accepted Phase 15 baseline ancestry.
- Every inherited migration, API/OpenAPI/generated contract, Compose/dependency file, and accepted
  production implementation outside the allowlist remains byte-identical.
- Generated committed JSON is byte-identical to generator stdout across repeated runs and platforms.
- Exact two outcomes, three requirement statuses, twelve ordered requirements, seven ordered
  capabilities, six ordered candidates/states, seven ordered `NOT_STARTED` steps, nineteen unchanged
  Phase 15 gap bindings, fixed timestamp, Family A identity, policy, baseline, and authority flags.
- Complete plan produces `PLAN_FROZEN`; requirement `BLOCKED`/`UNCOMPUTABLE` variants produce only
  `BLOCKED`.
- Missing, duplicate, reordered, unknown, extra, cross-row, policy, source, state, reason, evidence,
  prerequisite, output, authority, canonical-preimage, and hash tampering is rejected.
- No candidate can be selected, approved, rights-verified, externally verified, or substituted; no
  future step can be completed; no Phase 15 gap can change.
- Generator/verifier reject provider, product, URL, credential, rights, data, output, strategy,
  threshold, holdout, action, order, retry, execution, ingestion, promotion, clock, seed, and arbitrary
  hash arguments.
- Active socket denial and static absence of SQLAlchemy/PostgreSQL, FastAPI, transport, provider,
  credential, worker, queue, retry, broker, research-run, and execution imports.
- Clock/random/UUID4/environment/filesystem/Git-state changes cannot alter output.
- Secret and licensed-data canaries are absent from stdout, stderr, errors, repository files, build,
  CI, browser evidence, and temporary output.
- Generator, verifier, Phase 16 tests, and inherited browser checks leave all database tables, the
  migration head, generated contracts, and repository status unchanged.
- Inherited Phase 8/10/11 browser/accessibility/visual regressions run at the correct stage-local
  migration heads without frontend product or visual-baseline changes.
- Clean Windows and Ubuntu gates pass at one committed SHA/tree.
- Complete Phase 16 container/network/volume/process/browser/temp cleanup preserves the user's
  pre-existing development stack.

Closure commands:

```powershell
$env:FABLE5_VERIFY_PHASE = "16"
.\scripts\check.ps1
.\scripts\test.ps1
npm run build
.\.venv\Scripts\python.exe scripts\verify_phase1.py --static-only --phase 16
```

After one honest closure commit, run from the clean committed tree:

```powershell
$env:FABLE5_VERIFY_PHASE = "16"
.\.venv\Scripts\python.exe scripts\verify_phase1.py --phase 16
git status --porcelain=v1
```

After the Windows committed-tree gate passes, push only the exact Phase 16 SHA authorized by this
task and require Ubuntu `preflight`, `unit`, and `phase16-compose` at that same SHA/tree.

## Data and security posture

The committed artifact contains only plan requirements, capability codes, candidate-only official
facts, closed states, future-step definitions, unchanged Phase 15 gap bindings, identities, reasons,
hashes, and false authority fields. It contains no credential, entitlement document, contract text,
licensed provider body, observation value, account, price, position, order, fill, feature, label,
return, or performance metric. Phase 16 tests and CI require no credential and actively deny network
and database access for the portable surface.

## Handoff report

Report final commit/tree, exact changed paths, host-gate counts, generator/artifact/verifier hashes,
portable complete/blocked/tamper evidence, unchanged-gap proof, no-schema/no-API/zero-write proof,
inherited browser proof, cleanup evidence, and every limitation. State explicitly that no source was
selected, no rights were verified, and no credential, provider call, data capture, ingestion,
snapshot, evaluation policy, holdout, research run, performance calculation, promotion, approval,
risk mutation, order, or live path occurred. State whether Ubuntu ran at the exact Phase 16 SHA/tree.

## Stop condition

Stop after Phase 16 is accepted on Windows and Ubuntu. Do not select a source/product, create or load
a credential, contact a provider, qualify a sample, ingest or persist non-synthetic data, implement
quarantine/snapshot behavior, freeze an incomplete evaluation policy, open a holdout, run or promote
research, modify governance/risk, create an order path, add a live capability, begin Phase 17, open a
PR, tag, publish, release, or deploy.
