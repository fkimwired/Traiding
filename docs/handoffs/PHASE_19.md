# Phase 19 Family A Step 3 prerequisite-assessment handoff

## Objective and explicit exclusions

Implement one deterministic, portable, database-free, network-disabled assessment of the two
required prior-evidence hashes for Phase 16 Step 3. The only truthful successful result is:

```text
outcome:          BLOCKED
assessment_state: OUTPUT_FROZEN
conclusion:       BLOCKED_MISSING_EVALUATION_POLICY_AND_HOLDOUT
```

The assessment must prove that `non_synthetic_evaluation_policy_sha256` and
`confirmation_holdout_definition_sha256` are both missing. It must never produce, accept, derive,
or substitute values for either missing hash. Phase 16 Steps 1/2 remain `OUTPUT_FROZEN`; Steps 3-7
remain `NOT_STARTED`; all nineteen Phase 15 gap states remain unchanged.

Do not add or use a provider/account request, credential, transport, external sample, licensed
payload, dataset path, observation, capture, qualification, ingestion, snapshot, complete evaluation
policy, threshold, exact holdout interval, holdout opening, research run, performance result,
promotion, approval, risk mutation, broker/order/fill behavior, API, migration, frontend product
control, live path, publication, deployment, or Phase 20 behavior.

## Accepted input identity

Start only from the formally accepted Phase 18 identity:

- Commit: `16aac187fc3dbd6015306603c18be6e08cea8e4e`
- Tree: `b36ae615f13f39d0e661f18d1cc61e009b1aacf7`
- Artifact id: `7008240c-e7a2-5d4b-9345-8c40d2d4c359`
- Artifact SHA-256:
  `2def399ee8c57d7c6d80f5282e856eda1acf34a8504058fbfc8ea2dea4aa30ae`
- Policy SHA-256:
  `e175f9b70333899b8c9626e459f091ea5c440494e006c2684448fa15fe0a4fbb`
- Steps-manifest SHA-256:
  `581ff73113eff3c2d54728106df556734084c053f8e52f0f4a9e6928d7478167`
- Windows full Phase 18 verifier passed in 4,323.8 seconds with complete cleanup.
- Ubuntu run `29698090468`: `preflight`, `unit`, and `phase18-compose` passed at that same
  SHA/tree.

Stop before editing on any other identity or with ambiguous pre-existing changes. Preserve unrelated
user work.

Authority sources:

- `AGENTS.md`
- `RESEARCH_SUPPLEMENT.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/EVALS.md`
- `docs/RISK_POLICY.md`
- `docs/DATA_SOURCES.md`
- `docs/COMPLIANCE_NOTES.md`
- `docs/PHASE_15_FAMILY_A_RESEARCH_ADMISSION_SPECIFICATION_DECISIONS.md`
- `docs/PHASE_16_FAMILY_A_POINT_IN_TIME_SOURCE_PLAN_DECISIONS.md`
- `docs/PHASE_17_FAMILY_A_CANDIDATE_PRODUCT_INVENTORY_DECISIONS.md`
- `docs/PHASE_18_FAMILY_A_CURRENT_USE_RIGHTS_REVIEW_DECISIONS.md`
- `docs/PHASE_19_FAMILY_A_STEP3_PREREQUISITE_ASSESSMENT_DECISIONS.md`

## Exact write allowlist

Write only these 39 paths:

```text
.github/workflows/ci.yml
Makefile
README.md
docs/COMPLIANCE_NOTES.md
docs/DATA_SOURCES.md
docs/EVALS.md
docs/IMPLEMENTATION_PLAN.md
docs/PHASE_19_FAMILY_A_STEP3_PREREQUISITE_ASSESSMENT.json
docs/PHASE_19_FAMILY_A_STEP3_PREREQUISITE_ASSESSMENT_DECISIONS.md
docs/RISK_POLICY.md
docs/handoffs/PHASE_19.md
scripts/check.ps1
scripts/check.sh
scripts/generate_family_a_step3_prerequisite_assessment.py
scripts/verify_family_a_step3_prerequisite_assessment.py
scripts/verify_phase1.py
services/data/src/fable5_data/phase19/__init__.py
services/data/src/fable5_data/phase19/assessment.py
services/data/src/fable5_data/phase19/canonical.py
services/data/src/fable5_data/phase19/contracts.py
services/data/tests/test_phase19_assessment.py
services/data/tests/test_phase19_contracts.py
services/data/tests/test_phase19_security.py
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
tests/test_phase16_static.py
tests/test_phase17_static.py
tests/test_phase18_static.py
tests/test_phase19_portable.py
tests/test_phase19_static.py
tests/test_repository_policy.py
```

Stop before a write outside this list. Do not modify Compose, dependencies, environment examples,
migrations, API code/tests, OpenAPI, generated TypeScript, `scripts/run_phase_gate.py`, accepted Phase
4-18 production code, paper/research/risk services, frontend product code, or visual snapshots. The
two inherited Phase 8 browser specs are in scope only to extend the phase range without changing
product assertions or baselines.

## Exact assessment contract

Use these fixed identities:

```text
artifact schema/hash domain: phase19-family-a-step3-prerequisite-assessment-v1
prerequisite schema/domain:   phase19-family-a-step3-prerequisite-v1
required-evidence schema/domain:
                              phase19-family-a-step3-required-prior-evidence-v1
gap-binding schema/domain:    phase19-family-a-phase15-gap-binding-v1
step schema/domain:           phase19-family-a-source-plan-step-evidence-v1
output schema/domain:         phase19-family-a-source-plan-output-v1
prerequisites manifest:       phase19-step3-prerequisites-manifest-v1
required-evidence manifest:   phase19-step3-required-prior-evidence-manifest-v1
gap-bindings manifest:        phase19-phase15-gap-bindings-manifest-v1
steps manifest:               phase19-source-plan-steps-manifest-v1
assessment policy id/domain:  phase19-family-a-step3-prerequisite-assessment-policy-v1
artifact UUID namespace:      2c232226-c183-5f60-bbd0-35837b0b9ed1
fixed assessment timestamp:   2026-07-19T20:01:39.9672350Z
artifact id:                  0b3f9153-71cc-5052-9b47-f714ed17bb99
embedded artifact SHA-256:    ed738badfb6e95feb4d7969d299bdc6186ef13ebf0f036134518e147803c72df
assessment-policy SHA-256:    78485a93a2fda0d81ea7d2d7fb179f60ef2aee97616f3981fadabfd72ca02438
committed file SHA-256:       29cedb0c54c3adb5bafc36d5df4ee039b173ab11e865e1de40e27ed68d335264
committed artifact bytes:     25,596
```

The builder must reproduce those exact identities. The committed JSON is 25,596 bytes and must be
byte-identical to generator stdout plus one final newline. None of these artifact/policy/file
identities may substitute for either missing Step 3 prior-evidence hash.

Bind the accepted Phase 18 identity and complete relevant lineage. Freeze exactly:

```text
outcome                                      BLOCKED
assessment_state                             OUTPUT_FROZEN
conclusion                                   BLOCKED_MISSING_EVALUATION_POLICY_AND_HOLDOUT
non_synthetic_evaluation_policy              MISSING
confirmation_holdout_definition              MISSING
complete_non_synthetic_evaluation_policy     false
evaluation_policy_approved                   false
confirmation_holdout_defined                 false
confirmation_holdout_opened                  false
```

Use strict extra-forbid/frozen contracts and closed enum vocabularies. A missing prerequisite row may
name the expected future hash but must contain no value, placeholder, all-zero hash, synthetic policy
hash, Phase 15 requirements hash, Phase 18 rights hash, or arbitrary override. The artifact's own
hashes prove only assessment integrity.

Bind the methodology findings in
`docs/PHASE_19_FAMILY_A_STEP3_PREREQUISITE_ASSESSMENT_DECISIONS.md`: repository definitions and
synthetic mechanics exist for signal/horizon, chronology/purge, conditional embargo, train-only
preprocessing, complete trial accounting, DSR/PBO, costs/stress, leakage, holdout isolation, and
audit; none supplies non-synthetic policy approval, market calibration, performance, or holdout
definition. Never reuse the registered synthetic dates, fold sizes, thresholds, cost/calibration
identities, regimes, limits, or results as non-synthetic evidence.

Preserve the exact nineteen-row prerequisite registry and order from the decision record: fifteen
`EVALUATION_POLICY` rows followed by four `CONFIRMATION_HOLDOUT` rows. Evidence-state vocabulary is
only `PRESENT`, `MOCK_ONLY`, `MISSING`, and `UNPROVEN`. Only
`REPRODUCIBILITY_AUDIT_SCHEMA` is `PRESENT`/satisfied; it cannot clear the aggregate. The two-row
required-evidence registry is exactly `MISSING`, `produced=false`, and structurally has no evidence
value/hash field.

Copy and hash-bind all nineteen accepted Phase 15 gap codes and states without upgrade. Bind the
Phase 16 step sequence exactly: Steps 1/2 `OUTPUT_FROZEN`; Steps 3-7 `NOT_STARTED`. Phase 19 is not a
source-plan step, produces no `qualification_artifact_set_sha256`, and cannot complete Step 3.

## Authority and security invariants

Freeze false every operational selection, account/credential, entitlement/license/currentness,
provider/account/data request, sample qualification, data capture, payload persistence, licensed
persistence, ingestion, snapshot, complete-policy presence/approval, holdout definition/opening/
label access, research creation/authorization/execution, performance, `PASS_RESEARCH`, promotion,
paper approval, risk clearance, execution, and order-submission field. Freeze live-path absence,
no-personalized-advice, no-real-performance-claim, metadata-only, and runtime-network-disabled fields
true.

No credential, secret-name value, account id, entitlement or contract body, provider response,
observation, dataset, feature, label, return, metric, signal, price, position, order, or fill may enter
source, fixtures, artifact, stdout/stderr, logs, build output, browser output, CI evidence, or
temporary files.

## Implementation units

1. Strict canonical policy, missing-prerequisite, methodology-finding, gap-binding, step-evidence,
   and artifact contracts with domain-separated hashes and no I/O dependency.
2. One immutable server-owned builder bound to accepted Phase 18 lineage, the fixed timestamp,
   blocked result, exact missing evidence, unchanged gaps/steps, and false-authority boundary.
3. One stdout-only generator with exactly `--confirm-prerequisite-assessment-only` and no semantic
   override.
4. One offline verifier for exactly `--assessment PATH`, reading one bounded regular canonical
   UTF-8 JSON file.
5. One committed generated artifact with exact repeated-run parity.
6. Focused contract/assessment/security tests and portable adversarial tests.
7. Static/full verifier, root wrappers, inherited browser range, and Ubuntu CI support through Phase
   19 while rejecting phases 0 and 20.
8. Decision, evaluation, data, risk, compliance, implementation, service-status, and handoff docs.

Generator/verifier code must not import or call database, socket, HTTP, subprocess, provider SDK,
credential, research-run, worker, queue, retry, broker, or execution surfaces. Their CLIs accept no
URL, provider, product, credential, data, output, expected hash, repair, policy, threshold, signal,
action, interval, holdout, result, authority, order, clock, seed, or arbitrary-hash override.

## Persistence, API, migration, rollback, and failure semantics

Phase 19 adds no migration, table, row, SQL function/trigger, database connection, API route,
Pydantic API response, OpenAPI path, generated TypeScript, dependency, Compose service, frontend
product control, transport, scheduler, worker, queue, or retry. Alembic head remains exactly
`0011_phase14`; all 57 inherited tables/functions, rows, migrations, API paths, and generated-contract
bytes remain unchanged.

Retain the inherited nonempty `0010_phase13 -> 0011_phase14 -> 0010_phase13 -> 0011_phase14` rollback
cycle. Phase 19 rollback deletes only its portable artifact/code/tests and wrapper/CI/documentation
registrations; no data or schema rollback exists.

Invalid CLI arguments, phase values 0/20, malformed/noncanonical/nonregular/oversized files,
duplicate keys, floats/non-finite values, unstable reads, unknown fields, changed baseline/lineage,
missing/duplicate/reordered/substituted findings, gap or step drift, any fabricated prerequisite
hash, synthetic-policy substitution, incomplete-policy approval, defined/opened holdout, positive
gate/result, true authority bit, hash mismatch, dependency attempt, or secret/data canary must fail
closed with sanitized errors and no side effect. No repair, retry, fallback, partial success, or
operator override exists.

## Executable acceptance plan

Run focused checks first:

```powershell
.\.venv\Scripts\python.exe -m pytest `
  services/data/tests/test_phase19_contracts.py `
  services/data/tests/test_phase19_assessment.py `
  services/data/tests/test_phase19_security.py `
  tests/test_phase19_portable.py `
  tests/test_phase19_static.py -q
```

Prove deterministic stdout, repeated-run parity, committed parity, and offline verification:

```powershell
.\.venv\Scripts\python.exe scripts\generate_family_a_step3_prerequisite_assessment.py `
  --confirm-prerequisite-assessment-only > $env:TEMP\phase19-a.json
.\.venv\Scripts\python.exe scripts\generate_family_a_step3_prerequisite_assessment.py `
  --confirm-prerequisite-assessment-only > $env:TEMP\phase19-b.json
Get-FileHash $env:TEMP\phase19-a.json -Algorithm SHA256
Get-FileHash $env:TEMP\phase19-b.json -Algorithm SHA256
Compare-Object (Get-Content $env:TEMP\phase19-a.json -Raw) (Get-Content $env:TEMP\phase19-b.json -Raw)
.\.venv\Scripts\python.exe scripts\verify_family_a_step3_prerequisite_assessment.py `
  --assessment docs\PHASE_19_FAMILY_A_STEP3_PREREQUISITE_ASSESSMENT.json
```

Adversarial tests must reject forged values for either missing Step 3 hash, a substitute synthetic or
requirements hash, complete/approved policy, defined/opened holdout, holdout labels, changed finding,
upgraded gap, advanced step, invented threshold/calibration/interval, positive research/result/
authority state, semantic rehash tampering, duplicate/noncanonical JSON, symlink/directory/TOCTOU
input, network/database/subprocess dependency, and secret/licensed-data leakage.

Run host gates and build:

```powershell
$env:FABLE5_VERIFY_PHASE = "19"
.\scripts\check.ps1
.\scripts\test.ps1
npm run build
.\.venv\Scripts\python.exe scripts\verify_phase1.py --static-only --phase 19
```

Before the full gate, create one honest commit and confirm a clean index/worktree. Then run:

```powershell
.\.venv\Scripts\python.exe scripts\verify_phase1.py --phase 19
```

The direct Windows and Ubuntu `phase19-compose` gates must pass at one clean committed SHA/tree.
They must prove exact initial/final repository identity, generated parity, portable adversarial
verification, zero schema/row/API/generated-contract drift, inherited browser regressions at their
stage-local migration heads, no secret/data leakage, and complete cleanup of
`fable5_acceptance_*` containers, networks, volumes, processes, browser output, and temporary files.

## Handoff report and stop condition

Report final commit/tree, all changed paths, host/focused counts, generated artifact/manifest/policy/
receipt hashes, exact blocked result, missing-prerequisite proof, unchanged-gap/step proof,
false-authority and dependency-denial proof, no-schema/no-API/zero-write proof, inherited-browser and
cleanup proof, and same-SHA Ubuntu status.

State explicitly that Phase 19 produced neither `non_synthetic_evaluation_policy_sha256` nor
`confirmation_holdout_definition_sha256`; no incomplete policy or holdout was frozen; Step 3 remains
`NOT_STARTED`; and no credential, provider/account/data request, capture, database write, research,
performance, execution, order, or live path occurred.

Stop after Phase 19 is implemented and, when authorized, accepted on Windows and Ubuntu. Do not begin
Phase 20, advance Step 3, contact a provider, obtain/load a credential, inspect an account or data,
define/open a holdout, create a snapshot, run/promote research, modify approval/risk, submit/reconcile
an order, add live capability, open a PR, tag, sign, publish, release, or deploy.
