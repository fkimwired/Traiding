# Phase 20 Family A evaluation/holdout input-register handoff

## Objective and explicit exclusions

Implement one deterministic, portable, database-free, network-disabled register of the exact input
names and future-only transition rules required before a complete non-synthetic Family A evaluation
policy and untouched confirmation-holdout definition could be created. The sole truthful result is:

```text
outcome:               BLOCKED
register_state:        INPUTS_FROZEN
aggregate_conclusion: BLOCKED_MISSING_OPERATIONAL_AND_DATA_SPECIFIC_INPUTS
```

The register must supply no actual input value, apply no transition, create or approve no policy,
define/open/consume no holdout, and produce neither `non_synthetic_evaluation_policy_sha256` nor
`confirmation_holdout_definition_sha256`. Phase 16 Steps 1/2 remain `OUTPUT_FROZEN`; Steps 3-7
remain `NOT_STARTED`; all nineteen Phase 15 gap states remain unchanged.

Do not add or use an operational source/provider/product selection, counsel or rights conclusion,
account, credential, transport, external sample, licensed payload, observation, dataset, schema
value, calendar/date/threshold, qualification, capture, persistence, ingestion, snapshot, research,
performance, promotion, approval, risk mutation, broker/order/fill behavior, API, migration,
frontend product control, live path, publication, deployment, or Phase 21 behavior.

## Accepted input identity

Start only from the formally accepted Phase 19 identity:

- Commit: `86ddcafacff43b42fe56346745d7e6f08eaf3a52`
- Tree: `6b6c2693a969e80cac9013d441ba607565d8914a`
- Artifact id: `0b3f9153-71cc-5052-9b47-f714ed17bb99`
- Artifact SHA-256:
  `ed738badfb6e95feb4d7969d299bdc6186ef13ebf0f036134518e147803c72df`
- Assessment-policy SHA-256:
  `78485a93a2fda0d81ea7d2d7fb179f60ef2aee97616f3981fadabfd72ca02438`
- Windows full Phase 19 verifier passed in 4,614.4 seconds with complete cleanup.
- Ubuntu run `29705348113`: `preflight`, `unit`, and `phase19-compose` passed at the same SHA/tree;
  Compose acceptance took 1 hour 40 minutes 49 seconds and proved cleanup.

Stop before editing on any other identity, on a dirty worktree not attributable to the authorized
parallel Phase 20 units, or when changes are ambiguous. Preserve unrelated user work.

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
- `docs/PHASE_20_FAMILY_A_EVALUATION_HOLDOUT_INPUT_REGISTER_DECISIONS.md`

## Exact write allowlist

Write only these 40 paths:

```text
.github/workflows/ci.yml
Makefile
README.md
docs/COMPLIANCE_NOTES.md
docs/DATA_SOURCES.md
docs/EVALS.md
docs/IMPLEMENTATION_PLAN.md
docs/PHASE_20_FAMILY_A_EVALUATION_HOLDOUT_INPUT_REGISTER.json
docs/PHASE_20_FAMILY_A_EVALUATION_HOLDOUT_INPUT_REGISTER_DECISIONS.md
docs/RISK_POLICY.md
docs/handoffs/PHASE_20.md
scripts/check.ps1
scripts/check.sh
scripts/generate_family_a_evaluation_holdout_input_register.py
scripts/verify_family_a_evaluation_holdout_input_register.py
scripts/verify_phase1.py
services/data/src/fable5_data/phase20/__init__.py
services/data/src/fable5_data/phase20/canonical.py
services/data/src/fable5_data/phase20/contracts.py
services/data/src/fable5_data/phase20/input_register.py
services/data/tests/test_phase20_contracts.py
services/data/tests/test_phase20_input_register.py
services/data/tests/test_phase20_security.py
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
tests/test_phase19_static.py
tests/test_phase20_portable.py
tests/test_phase20_static.py
tests/test_repository_policy.py
```

Stop before a write outside this list. Do not modify Compose, dependencies, environment examples,
migrations, API code/tests, OpenAPI, generated TypeScript, `scripts/run_phase_gate.py`, accepted
Phase 4-19 production code, paper/research/risk services, frontend product code, or visual snapshots.
The two inherited Phase 8 browser specs may only extend the supported phase range; do not change
product assertions or baselines.

## Exact contract and current-state registry

Use these fixed identities:

```text
artifact schema/hash domain: phase20-family-a-evaluation-holdout-input-register-v1
inherited prerequisite:      phase20-family-a-inherited-phase19-prerequisite-v1
input requirement schema:    phase20-family-a-evaluation-holdout-input-requirement-v1
missing-evidence schema:     phase20-family-a-missing-future-evidence-v1
transition-rule schema:      phase20-family-a-future-evidence-transition-rule-v1
dependency-group schema:     phase20-family-a-construction-dependency-group-v1
construction-gate schema:    phase20-family-a-evaluation-holdout-construction-gate-v1
forbidden-substitute schema: phase20-family-a-forbidden-substitute-v1
gap-binding schema:          phase20-family-a-phase15-gap-binding-v1
source-plan step schema:     phase20-family-a-source-plan-step-binding-v1
inherited prereq manifest:   phase20-inherited-phase19-prerequisites-manifest-v1
input manifest domain:       phase20-evaluation-holdout-input-requirements-manifest-v1
missing-evidence manifest:   phase20-missing-future-evidence-manifest-v1
transition manifest domain:  phase20-future-evidence-transition-rules-manifest-v1
dependency manifest domain:  phase20-construction-dependency-groups-manifest-v1
gate manifest domain:        phase20-evaluation-holdout-construction-gates-manifest-v1
substitute manifest domain:  phase20-forbidden-substitutes-manifest-v1
gap manifest domain:         phase20-phase15-gap-bindings-manifest-v1
step manifest domain:        phase20-source-plan-step-bindings-manifest-v1
register policy id/domain:   phase20-family-a-evaluation-holdout-input-register-policy-v1
fixed frozen timestamp:      2026-07-20T00:47:38.1976088Z
artifact id:                 e501d4f8-bebe-5e68-9457-56f6a589f478
embedded artifact SHA-256:   902fca99d4fec1943403cbed406259f86c0eee05c41cb835b6daf7d165db340b
register-policy SHA-256:     e6be914218dc8b16b2c019ff8d72338dcf495b7cf375cd95281651b89939a31a
inherited manifest SHA-256:  ee650453fc05597765164b965cd65ee3844b034f51b41b4064a001cda147efe9
input manifest SHA-256:      b4ffc11633c0ae41d351b7dd10380c29a47e44f368b9248bc74a412e81c4c0ad
missing manifest SHA-256:    ace85cba35e9ca4ea3a26fe7692591a2d02234b3437e8f2c2763e60aebbdff41
transition manifest SHA-256: b594a162a1c6124502aa6552634f0d1bba7832bf89e550a2e1f7d21b6f737955
dependency manifest SHA-256: 34b44a2d2995f288947eb7a8da6c21f5fb9c8653316172e3155edaa2b9077379
gate manifest SHA-256:       4e5bad5d5d9441c9e832b6c9511ab8aa9123a4875130b98a2fcdf43c8907692a
substitute manifest SHA-256: 044b07af06221878b11da497baf8bc838909043f1550cae29669056a84cf4b84
gap manifest SHA-256:        c98b37ca4a0aa8ab9a7641a865f9444e56422be74cadf239c33e3cd3a882334a
step manifest SHA-256:       e695c826fe23365bf6b89d09626003a8feac3c3aab589266bd56464e5cdaa4bf
committed file SHA-256:      a0b6987301f12e87963ee751cc9abb4f6be4af7702fad999092ad2d0c363a741
committed artifact bytes:    60,265
```

These are the exact deterministic generated identities. Bind the accepted Phase 19 identity and
relevant transitive Phase 15-19 manifests.

The exact ordered input registry is:

```text
 1 UPSTREAM_CONTEXT            OPERATIONAL_SOURCE_PRODUCT_COMPOSITION                         MISSING
 2 UPSTREAM_CONTEXT            CURRENT_EXECUTED_USE_RIGHTS_AND_REVOCATION                    MISSING
 3 UPSTREAM_CONTEXT            EXACT_DELIVERY_AND_SCHEMA_VERSIONS                            UNPROVEN
 4 UPSTREAM_CONTEXT            DECLARED_PIT_COVERAGE_CALENDAR_AVAILABILITY_MISSINGNESS       MISSING
 5 EVALUATION_POLICY_INPUT     SIGNAL_ACTION_LABEL_AND_HORIZON                               MOCK_ONLY
 6 EVALUATION_POLICY_INPUT     FEATURE_LINEAGE_LOOKBACK_AND_PREPROCESSING                    MOCK_ONLY
 7 EVALUATION_POLICY_INPUT     WALK_FORWARD_FOLD_GEOMETRY_AND_PURGE                          MOCK_ONLY
 8 EVALUATION_POLICY_INPUT     EMBARGO_APPLICABILITY_AND_DURATION                            UNPROVEN
 9 EVALUATION_POLICY_INPUT     SAMPLE_ADEQUACY_AND_RETURN_HANDLING                           MOCK_ONLY
10 EVALUATION_POLICY_INPUT     TRIAL_ACCOUNTING_DSR_PBO_SELECTION                            MOCK_ONLY
11 EVALUATION_POLICY_INPUT     LEAKAGE_AND_DATA_QUALITY_BLOCKS                               MOCK_ONLY
12 EVALUATION_POLICY_INPUT     MARKET_CALIBRATED_COST_SLIPPAGE_CAPACITY                      MOCK_ONLY
13 EVALUATION_POLICY_INPUT     STRESS_VECTOR_AND_PROMOTION_GATES                             MOCK_ONLY
14 EVALUATION_POLICY_INPUT     REGIME_AND_CRISIS_DEFINITIONS                                 MOCK_ONLY
15 EVALUATION_POLICY_INPUT     COMPUTABLE_DATA_SPECIFIC_RISK_LIMITS                          MOCK_ONLY
16 EVALUATION_POLICY_INPUT     REPRODUCIBILITY_AUDIT_SCHEMA                                  PRESENT
17 CONFIRMATION_HOLDOUT_INPUT  SOURCE_BOUND_CONTIGUOUS_INTERVAL                              MISSING
18 CONFIRMATION_HOLDOUT_INPUT  DECISION_CALENDAR_LABEL_BOUNDARY_AND_EXCLUSIONS               MISSING
19 CONFIRMATION_HOLDOUT_INPUT  LABEL_BLIND_CONSUMPTION_REPLACEMENT_GOVERNANCE                MOCK_ONLY
20 APPROVAL_INPUT              INDEPENDENT_POLICY_AND_HOLDOUT_APPROVAL_RECORD                 MISSING
```

Only row 16 is satisfied, and only as an audit-schema requirement. Every row carries field names,
not values; no row resolves either reserved evidence requirement. Preserve the definitions,
current-state reasons, related Phase 19 prerequisites/gaps, and exact field-name coverage from the
decision record. Use strict extra-forbid/frozen contracts, closed enums, canonical row ordering, and
domain-separated hashes.

For every row, require nonempty `related_phase19_prerequisite_codes` and
`related_phase15_gap_codes` tuples, closed inherited enum vocabularies, exact canonical tuple order,
and inclusion of both tuples in the complete `requirement_sha256` preimage. Reject missing, empty,
duplicate, reordered, unknown, or cross-row relation content. Traceability cannot upgrade evidence.

The exact future-only transition rules are:

```text
 1 NO_PLAN_OR_ARTIFACT_HASH_UPGRADE
 2 MOCK_ONLY_TO_PRESENT_REQUIRES_APPROVED_NON_SYNTHETIC_EVIDENCE
 3 MISSING_TO_PRESENT_REQUIRES_COMPLETE_REQUIRED_EVIDENCE
 4 UNPROVEN_TO_PRESENT_REQUIRES_INDEPENDENT_VERIFICATION
 5 STALE_TO_PRESENT_REQUIRES_FRESH_REVALIDATION
 6 PRESENT_TO_STALE_ON_CURRENTNESS_OR_VERSION_DRIFT
 7 HOLDOUT_DEFINITION_REQUIRES_SOURCE_CALENDAR_BINDING_AND_ZERO_OBSERVATION_LABEL_ACCESS
 8 POLICY_COMPLETION_REQUIRES_ALL_POLICY_INPUTS_AND_UNOPENED_HOLDOUT_REFERENCE
 9 STEP3_REQUIRES_BOTH_RESERVED_HASHES_AND_SEPARATE_EXTERNAL_ACTION_AUTHORITY
10 LATER_SOURCE_PLAN_STEPS_CANNOT_SKIP_OR_IMPLY_PREDECESSORS
```

Every rule has `applied=false`; the artifact applies no transition. The two missing-future-evidence rows
are exactly `MISSING`, `produced=false`, and structurally contain no value/evidence-hash field. Do not
create a placeholder, all-zero hash, Phase 5 synthetic-policy hash, Phase 15 requirements hash,
Phase 19 assessment hash, register hash, or arbitrary override.

Bind these six ordered dependency groups, all `BLOCKED`:

```text
OPERATIONAL_COMPOSITION_AND_RIGHTS
SOURCE_COVERAGE_AND_CALENDAR
EVALUATION_METHODOLOGY
COST_STRESS_REGIME_AND_RISK
AUDIT_AND_HOLDOUT_GOVERNANCE
INDEPENDENT_JOINT_APPROVAL
```

Bind these six construction gates, all `BLOCKED`, `passed=false`, and
`required_before_observation=true`:

```text
OPERATIONAL_COMPOSITION_CURRENT_RIGHTS_GATE
SOURCE_COVERAGE_CALENDAR_GATE
NON_SYNTHETIC_METHODOLOGY_GATE
MARKET_CALIBRATION_STRESS_RISK_GATE
UNTOUCHED_HOLDOUT_GOVERNANCE_GATE
INDEPENDENT_JOINT_APPROVAL_GATE
```

Bind these eight forbidden substitutes for both future output classes:

```text
PHASE15_REQUIREMENTS_HASH
PHASE19_ASSESSMENT_HASH
SYNTHETIC_POLICY_OR_RESULT_HASH
PUBLIC_DOCUMENTATION_OR_RIGHTS_REVIEW_HASH
CANDIDATE_INVENTORY_HASH
PROTOCOL_OR_TEMPLATE_HASH
PLACEHOLDER_OR_ALL_ZERO_HASH
OPERATOR_OVERRIDE_OR_ARBITRARY_HASH
```

Copy and hash-bind all nineteen accepted Phase 15 gap codes and states without upgrade. Preserve the
Phase 16 step sequence exactly: Steps 1/2 `OUTPUT_FROZEN`; Steps 3-7 `NOT_STARTED`. Phase 20 is not a
source-plan step and produces no `qualification_artifact_set_sha256`.

## Authority and security invariants

Freeze false every operational selection, account/credential, entitlement/license/currentness,
provider/account/data request, qualification, capture, payload persistence, licensed persistence,
ingestion, snapshot, actual input value, transition application, complete-policy presence/approval,
holdout definition/opening/consumption/label access, research creation/authorization/execution,
performance, `PASS_RESEARCH`, promotion, paper approval, risk clearance, execution, and order field.
Freeze `metadata_only`, `requirements_only`, `runtime_network_disabled`, `live_path_absent`,
`no_personalized_investment_advice`, and `no_real_performance_claimed` true.

No credential, secret-name value, account id, entitlement/contract/license body, provider response,
observation, dataset, schema payload, calendar/date/interval value, feature, label, return, metric,
signal value, price, position, order, or fill may enter source, fixtures, artifact, stdout/stderr,
logs, build output, browser output, CI evidence, or temporary files.

## Implementation units

1. Strict canonical inherited-prerequisite, input-requirement, missing-future-evidence,
   future-transition-rule, dependency-group, construction-gate, forbidden-substitute, gap-binding,
   source-plan-step-binding, and root-artifact contracts with no I/O dependency.
2. One immutable server-owned builder bound to accepted Phase 19 lineage, fixed timestamp, exact
   blocked result, twenty input rows, ten unapplied rules, missing evidence, unchanged gaps/steps,
   and closed authority boundary.
3. One stdout-only generator with exactly `--confirm-input-register-only` and no semantic override.
4. One offline verifier for exactly `--register PATH`, reading one bounded local regular canonical
   UTF-8 JSON file.
5. One committed generated artifact with exact repeated-run parity.
6. Focused contract/input-register/security tests plus portable adversarial tests.
7. Static/full verifier, root wrappers, inherited browser range, and Ubuntu CI support through Phase
   20 while rejecting phases 0 and 21.
8. Decision, evaluation, data, risk, compliance, implementation, service-status, and handoff docs.

Generator/verifier code must not import or call database, socket, HTTP, subprocess, provider SDK,
credential, research-run, worker, queue, retry, broker, or execution surfaces. Their CLIs accept no
URL, provider, product, credential, account, entitlement, data, output, expected hash, repair,
policy value, threshold, signal, action, interval, holdout, result, authority, order, clock, seed, or
arbitrary-hash override.

## Persistence, API, migration, rollback, and failure semantics

Phase 20 adds no migration, table, row, SQL function/trigger, database connection, API route,
Pydantic API response, OpenAPI path, generated TypeScript, dependency, Compose service, frontend
product control, transport, scheduler, worker, queue, retry, broker, or execution behavior. Alembic
head remains exactly `0011_phase14`; all 57 inherited tables/functions, rows, migrations, API paths,
and generated-contract bytes remain unchanged.

Retain the inherited nonempty `0010_phase13 -> 0011_phase14 -> 0010_phase13 -> 0011_phase14`
rollback cycle. Phase 20 rollback deletes only its portable artifact/code/tests and wrapper/CI/docs
registrations; no data or schema rollback exists.

Invalid CLI arguments, phase values 0/21, malformed/noncanonical/nonregular/remote/oversized files,
duplicate keys, floats/non-finite values, unstable reads, unknown fields, changed baseline/lineage,
missing/duplicate/reordered/substituted inputs or rules, any actual input value, synthetic
substitution, reserved hash, transition application, state upgrade, policy/holdout completion,
defined/opened/consumed holdout, Step 3 start/output, later-step advance, gap drift, positive result
or authority, hash mismatch, dependency attempt, or secret/data canary must fail closed with a
sanitized error and no side effect. No repair, retry, fallback, partial success, or operator override
exists.

## Executable acceptance plan

Run focused checks first:

```powershell
.\.venv\Scripts\python.exe -m pytest `
  services/data/tests/test_phase20_contracts.py `
  services/data/tests/test_phase20_input_register.py `
  services/data/tests/test_phase20_security.py `
  tests/test_phase20_portable.py `
  tests/test_phase20_static.py -q
```

Prove deterministic stdout, repeated-run parity, committed parity, and offline verification:

```powershell
.\.venv\Scripts\python.exe scripts\generate_family_a_evaluation_holdout_input_register.py `
  --confirm-input-register-only > $env:TEMP\phase20-a.json
.\.venv\Scripts\python.exe scripts\generate_family_a_evaluation_holdout_input_register.py `
  --confirm-input-register-only > $env:TEMP\phase20-b.json
Get-FileHash $env:TEMP\phase20-a.json -Algorithm SHA256
Get-FileHash $env:TEMP\phase20-b.json -Algorithm SHA256
Compare-Object (Get-Content $env:TEMP\phase20-a.json -Raw) (Get-Content $env:TEMP\phase20-b.json -Raw)
.\.venv\Scripts\python.exe scripts\verify_family_a_evaluation_holdout_input_register.py `
  --register docs\PHASE_20_FAMILY_A_EVALUATION_HOLDOUT_INPUT_REGISTER.json
```

Adversarial tests must reject any supplied input value; fabricated/substituted reserved hash;
complete/approved policy; defined/opened/consumed holdout; copied synthetic date, threshold,
calibration, regime, risk, signal, or result; changed input/rule; applied transition; upgraded gap;
advanced step; positive research/result/authority state; semantic rehash tampering; duplicate or
noncanonical JSON; symlink/directory/UNC/device/different-drive/TOCTOU input; network/database/
subprocess dependency; and secret, contract, provider-body, or licensed-data leakage.

Run host gates and build:

```powershell
$env:FABLE5_VERIFY_PHASE = "20"
.\scripts\check.ps1
.\scripts\test.ps1
npm run build
.\.venv\Scripts\python.exe scripts\verify_phase1.py --static-only --phase 20
```

Before the full gate, create one honest commit and confirm a clean index/worktree. Then run:

```powershell
.\.venv\Scripts\python.exe scripts\verify_phase1.py --phase 20
```

The direct Windows and Ubuntu `phase20-compose` gates must pass at one clean committed SHA/tree.
They must prove exact initial/final repository identity, generated parity, portable adversarial
verification, zero schema/row/API/generated-contract drift, inherited browser regressions at their
stage-local migration heads, no secret/data leakage, and complete cleanup of
`fable5_acceptance_*` containers, networks, volumes, processes, browser output, and temporary files.

## Handoff report and stop condition

Report final commit/tree, all changed paths, focused/host counts, generated artifact/manifest/policy/
receipt hashes, exact blocked result, twenty-input/ten-rule proof, missing-future-evidence proof,
unchanged-gap/step proof, false-authority and dependency-denial proof, no-schema/no-API/zero-write
proof, inherited-browser and cleanup proof, and same-SHA Ubuntu status.

State explicitly that Phase 20 produced neither reserved Step 3 hash, supplied no input value,
applied no transition, created no policy or holdout, and performed no credential, provider/account/
data request, capture, database write, research, performance, execution, order, or live behavior.

Stop after Phase 20 is implemented and, when authorized, accepted on Windows and Ubuntu. Do not
begin Phase 21, advance Step 3, contact a provider or counsel, obtain/load a credential, inspect an
account or data, choose input values, define/open a holdout, create a snapshot, run/promote research,
modify approval/risk, submit/reconcile an order, add live capability, open a PR, tag, sign, publish,
release, or deploy.
