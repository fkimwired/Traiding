# Phase 15 Family A research-admission specification handoff

## Objective and exclusions

Implement one deterministic, database-free, network-disabled, portable Family A research-admission
requirements artifact and closed current-gap ledger. The only outcomes are
`REQUIREMENTS_FROZEN` and `BLOCKED`.

Do not add an external call, provider adapter, credential, rights assertion, licensed payload, data
file input, observation, ingestion, snapshot, research run, performance result, promotion, approval,
risk mutation, broker/order/fill behavior, live path, API, migration, database write, frontend product
control, deployment, publication, or later phase.

## Accepted input identity

Start only from the formally accepted Phase 14 identity:

- Commit: `513fdfd515599e59db6911441aadf1cc30f7352c`
- Tree: `5870fd4c112b7c7bee05f6240c5cbd950eeaff04`
- Windows Phase 14 full verifier: passed in 4,090.1 seconds.
- Ubuntu run `29632035213`: `preflight`, `unit`, and `phase14-compose` passed at that identity.

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
docs/PHASE_15_FAMILY_A_RESEARCH_ADMISSION_SPECIFICATION.json
docs/PHASE_15_FAMILY_A_RESEARCH_ADMISSION_SPECIFICATION_DECISIONS.md
docs/RISK_POLICY.md
docs/handoffs/PHASE_15.md
scripts/check.ps1
scripts/check.sh
scripts/generate_family_a_research_admission_specification.py
scripts/verify_family_a_research_admission_specification.py
scripts/verify_phase1.py
services/data/src/fable5_data/phase15/__init__.py
services/data/src/fable5_data/phase15/canonical.py
services/data/src/fable5_data/phase15/contracts.py
services/data/src/fable5_data/phase15/specification.py
services/data/tests/test_phase15_contracts.py
services/data/tests/test_phase15_security.py
services/data/tests/test_phase15_specification.py
services/frontend/e2e/phase8.accessibility.spec.ts
services/frontend/e2e/phase8.visual.spec.ts
tests/test_phase5_postgres.py
tests/test_phase9_static.py
tests/test_phase10_static.py
tests/test_phase11_static.py
tests/test_phase12_static.py
tests/test_phase13_static.py
tests/test_phase14_static.py
tests/test_phase15_portable.py
tests/test_phase15_static.py
tests/test_repository_policy.py
```

Stop before any write outside this list. Do not modify Compose, dependencies, environment examples,
any migration, API code/test, generated OpenAPI/TypeScript contract, `scripts/run_phase_gate.py`,
accepted Phase 4-14 production code, paper/research/risk services, frontend product code, or visual
baseline. The two inherited browser specs are permitted only if their phase range must include Phase
15; do not alter product assertions or snapshots.

## Contracts and invariants

Use exactly:

```text
outcomes: REQUIREMENTS_FROZEN, BLOCKED
requirement statuses: PASS, BLOCKED, UNCOMPUTABLE
gap states: PRESENT, MOCK_ONLY, STALE, MISSING, UNPROVEN
fixed timestamp: 2026-07-18T00:00:00Z
```

Exact versions/domains:

```text
phase15-family-a-research-admission-specification-v1
phase15-family-a-research-admission-requirement-v1
phase15-family-a-research-admission-gap-v1
phase15-family-a-research-admission-policy-v1
phase15-family-a-research-admission-requirements-manifest-v1
phase15-family-a-research-admission-gaps-manifest-v1
phase15-family-a-research-admission-evidence-v1
artifact UUID namespace: e681ce4e-94fa-5b7a-bb12-ce17b509037b
```

Bind the exact Family A specification:

```text
phase6-a_cross_sectional_equity_ranking-research-pipeline
v2
3967b3c0dffd6a27c4ac8012773621090b828e8bdc2f242611c34d81420b37bc
```

Exact ordered requirement registry:

```text
FAMILY_A_SPECIFICATION_IDENTITY_BOUND
SIGNAL_ACTION_AND_HORIZON_REQUIREMENTS_BOUND
POINT_IN_TIME_CAPABILITY_REQUIREMENTS_FROZEN
INSTRUMENT_IDENTITY_AVAILABILITY_POLICY_FROZEN
UNIVERSE_DELISTING_CORPORATE_ACTION_POLICY_FROZEN
FUNDAMENTAL_REVISION_LAG_POLICY_FROZEN
MACRO_SECTOR_LIQUIDITY_REQUIREMENTS_FROZEN
FULL_HISTORY_SAMPLE_BOUNDARIES_FROZEN
SNAPSHOT_CANONICALIZATION_AUDIT_POLICY_FROZEN
USE_RIGHTS_RETENTION_DERIVED_DATA_POLICY_FROZEN
WALK_FORWARD_PURGE_EMBARGO_HOLDOUT_POLICY_FROZEN
TRIAL_ACCOUNTING_DSR_PBO_LEAKAGE_POLICY_FROZEN
COST_SLIPPAGE_STRESS_REGIME_POLICY_FROZEN
RISK_REPRODUCIBILITY_POLICY_FROZEN
INGESTION_RESEARCH_PROMOTION_EXECUTION_AUTHORITY_ABSENT
```

The complete artifact has all fifteen requirements at `PASS` with exact reason
`frozen_repository_requirement`. Any `BLOCKED` or `UNCOMPUTABLE` row produces only `BLOCKED`.

Exact ordered gap registry and frozen states:

```text
FAMILY_A_SIGNAL_AND_HORIZON                 MOCK_ONLY
FULL_POINT_IN_TIME_DATASET                  MISSING
EXTERNAL_CANDIDATE_QUALIFICATION            UNPROVEN
HISTORICAL_MEMBERSHIP_AND_DELISTING         UNPROVEN
SECTOR_LIQUIDITY_MACRO_HISTORY              MISSING
INDEPENDENT_CURRENT_USE_RIGHTS              MISSING
NON_SYNTHETIC_SNAPSHOT_PERSISTENCE           MISSING
NON_SYNTHETIC_EVALUATION_POLICY              MISSING
NON_SYNTHETIC_EVALUATION_PATH                MISSING
PURGED_WALK_FORWARD_MECHANICS                MOCK_ONLY
EMBARGO_APPLICABILITY_DECISION               UNPROVEN
LEAKAGE_FREE_RESULT                          MOCK_ONLY
MARKET_CALIBRATED_COST_SLIPPAGE              MOCK_ONLY
DSR_PBO_PROMOTION_GATES                      MOCK_ONLY
PHASE_15_IMPLEMENTATION_AUTHORITY            PRESENT
DATA_RIGHTS_AND_RESEARCH_AUTHORITY           MISSING
RIGHTS_CURRENTNESS_REVOCATION                MISSING
PRE_ORDER_RISK                               MOCK_ONLY
IMMUTABLE_AUDIT_SCHEMA                       PRESENT
```

Freeze these exact fields false:

```text
external_request_performed
external_data_capture_authorized
provider_payload_persisted
licensed_data_persisted
research_ingestion_authorized
research_snapshot_created
research_data_eligible
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
2. One server-owned immutable specification builder covering the exact requirement and gap registries.
3. One generator that emits the canonical artifact to stdout only.
4. One offline verifier for a supplied regular JSON file.
5. One committed generated JSON artifact with byte-for-byte generator parity.
6. Static/full verifier, wrappers, inherited browser phase range, and Ubuntu CI through Phase 15.
7. Data, evaluation, compliance, risk, implementation, service-status, and handoff documentation.

## Generator and verifier

Generator:

```text
python scripts/generate_family_a_research_admission_specification.py \
  --confirm-requirements-only
```

The confirmation is required and is the only accepted option. Canonical JSON plus one final newline
goes to stdout. No file, database, log, or network write is allowed.

Verifier:

```text
python scripts/verify_family_a_research_admission_specification.py \
  --specification PATH
```

The verifier reads one regular UTF-8 JSON file of at most 512 KiB and rejects a BOM, duplicate keys,
floats, non-finite values, non-object roots, symbolic/non-regular files, and non-canonical bytes. It
performs strict model, ordering, identity, canonical-byte, and hash verification against the frozen
implementation and emits only deterministic sanitized success JSON. It has no expected-hash, repair,
override, provider, credential, data, policy, authority, or output option. Invalid generator/verifier
input exits 2 with no stdout and their exact generic one-line failure message; help exits 0.

## Persistence, API, migration, and rollback

Phase 15 has no persistence, API, or schema ownership. Retain exactly migrations `0001` through
`0011_phase14`, the complete inherited table/function catalog, every earlier row, and all OpenAPI and
generated TypeScript bytes. Add no `0012`, route, Pydantic API model, table, function, trigger, or
database connection.

The inherited nonempty `0010_phase13 -> 0011_phase14 -> 0010_phase13 -> 0011_phase14` cycle remains
the rollback proof. Phase 15 acceptance adds a no-schema/no-API-drift proof and zero-write snapshots
around every portable and inherited browser stage.

## Acceptance

Require:

- Parser/wrappers accept Phases 1-15 and reject 0/16/malformed input with exit 2.
- Exact Phase 15 allowlist and accepted Phase 14 baseline ancestry.
- All inherited migrations, API/OpenAPI/generated contracts, Compose, dependencies, and production
  implementations remain byte-identical.
- Generated committed JSON is byte-identical to generator stdout across repeated runs and platforms.
- Exact two outcomes, three requirement statuses, five gap states, fifteen ordered requirements,
  nineteen ordered gaps/states, fixed timestamp, Family A identity, policy, baseline, and authority
  flags.
- Complete artifact produces `REQUIREMENTS_FROZEN`; requirement `BLOCKED`/`UNCOMPUTABLE` variants
  produce only `BLOCKED`.
- Missing, duplicate, reordered, unknown, extra, cross-row, policy, source, state, reason, evidence,
  authority, canonical-preimage, and hash tampering is rejected.
- Generator/verifier reject provider, URL, credential, rights, data, output, strategy, threshold,
  action, order, retry, execution, ingestion, promotion, clock, seed, and arbitrary-hash arguments.
- Active socket denial and static absence of SQLAlchemy/PostgreSQL, FastAPI, transport, provider,
  credential, worker, queue, retry, broker, research-run, and execution imports.
- Clock/random/UUID4/environment/filesystem/Git-state changes cannot alter output.
- Secret and licensed-data canaries are absent from stdout, stderr, errors, repository files, build,
  CI, browser evidence, and temporary output.
- Generator, verifier, Phase 15 tests, and inherited browser checks leave all database tables, the
  migration head, generated contracts, and repository status unchanged.
- Inherited Phase 8/10/11 browser/accessibility/visual regressions run without frontend product or
  visual-baseline changes.
- Clean Windows and Ubuntu gates pass at one committed SHA/tree.
- Complete Phase 15 container/network/volume/process/browser/temp cleanup preserves the user's
  pre-existing development stack.

Closure commands:

```powershell
$env:FABLE5_VERIFY_PHASE = "15"
.\scripts\check.ps1
.\scripts\test.ps1
npm run build
.\.venv\Scripts\python.exe scripts\verify_phase1.py --static-only --phase 15
```

After one honest closure commit, run from the clean committed tree:

```powershell
$env:FABLE5_VERIFY_PHASE = "15"
.\.venv\Scripts\python.exe scripts\verify_phase1.py --phase 15
git status --porcelain=v1
```

After the Windows committed-tree gate passes, push only the exact Phase 15 SHA authorized by this
task and require Ubuntu `preflight`, `unit`, and `phase15-compose` at that same SHA/tree.

## Data and security posture

The committed artifact contains requirements, closed evidence states, identities, reasons, hashes,
and false authority fields only. It contains no credential, entitlement document, licensed text,
provider body, observation value, price, account, position, order, fill, feature, label, return, or
performance metric. Phase 15 tests and CI require no credential and actively deny external network.

## Handoff report

Report final commit/tree, exact changed paths, host-gate counts, generator/artifact/verifier hashes,
portable complete/blocked/tamper evidence, no-schema/no-API/zero-write proof, inherited browser proof,
cleanup evidence, and every limitation. State explicitly that no external capture, data ingestion,
snapshot, research run, performance calculation, promotion, approval, risk mutation, order, or live
path occurred. State whether Ubuntu ran at the exact Phase 15 SHA/tree.

## Stop condition

Stop after Phase 15 is accepted on Windows and Ubuntu. Do not begin Phase 16, create or load a
credential, contact a provider, ingest or persist non-synthetic data, generalize Phase 4-6 execution
paths, open a holdout, run or promote research, modify governance/risk, create an order path, add a
live capability, open a PR, tag, publish, release, or deploy.
