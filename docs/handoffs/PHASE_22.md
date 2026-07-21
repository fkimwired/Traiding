# Phase 22 Family A macro-vintage candidate-inventory amendment handoff

## Objective and explicit exclusions

Implement one deterministic, portable, database-free, network-disabled metadata amendment that
adds exactly one Philadelphia Fed RTDSM macro-vintage candidate to the accepted candidate lineage.
The exact truthful result is:

```text
outcome:               BLOCKED
amendment_state:       CANDIDATE_INVENTORY_AMENDMENT_FROZEN
aggregate_conclusion: BLOCKED_AWAITING_CURRENT_RIGHTS_FITNESS_REVIEW_AND_EXPLICIT_OPERATIONAL_COMPOSITION
```

This phase identifies a candidate for a later independent rights and fitness review. It does not
rank, recommend, select, qualify, subscribe to, request, access, or download that product. It does
not populate an operational composition, start Phase 16 Step 3, or change an inherited gap, gate,
input, rights finding, capability assignment, or source-plan state.

Do not add or use a login, subscription, account, credential, provider request, sales/counsel
contact, sample, payload, observation, data capture, persistence, ingestion, normalization,
snapshot, policy, holdout, research run, performance result, promotion, risk mutation, execution,
order, API, migration, frontend product behavior, publication, deployment, or live path.

## Accepted input identity

Start only from the formally accepted Phase 21 identity:

```text
commit:                  a25ffb5cb68014c301a588c0e8cf7c7f18914e0a
tree:                    8744604b486dd7398cd8c5a003fe7c7b083fde86
Phase 21 artifact id:    50086eea-4598-5e6b-b168-616321c7a068
Phase 21 artifact SHA:   44b5c4541febe6f6e389480102346b802bb4627b81e8d38cab4110cb2eab6a6e
Phase 21 policy SHA:     22773ad7e58c4baa2c2f7d84bb68c7992d343676f93dc780374ce8e1125f99cf
```

The Phase 21 Windows verifier passed in approximately 47 minutes 10 seconds with complete cleanup.
GitHub Actions run `29759697662` passed `preflight`, `unit`, and `phase21-compose` at that same
commit/tree. Stop before editing on any other baseline, ambiguous pre-existing change, or inherited
artifact mismatch. Preserve authorized parallel Phase 22 changes and unrelated user work.

Authority sources:

- `AGENTS.md`
- `RESEARCH_SUPPLEMENT.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/EVALS.md`
- `docs/RISK_POLICY.md`
- `docs/DATA_SOURCES.md`
- `docs/COMPLIANCE_NOTES.md`
- accepted Phase 15-21 decisions and artifacts
- `docs/PHASE_22_FAMILY_A_MACRO_VINTAGE_CANDIDATE_INVENTORY_AMENDMENT_DECISIONS.md`

## Exact write allowlist

Write only these 42 paths:

```text
.github/workflows/ci.yml
Makefile
README.md
docs/COMPLIANCE_NOTES.md
docs/DATA_SOURCES.md
docs/EVALS.md
docs/IMPLEMENTATION_PLAN.md
docs/PHASE_22_FAMILY_A_MACRO_VINTAGE_CANDIDATE_INVENTORY_AMENDMENT.json
docs/PHASE_22_FAMILY_A_MACRO_VINTAGE_CANDIDATE_INVENTORY_AMENDMENT_DECISIONS.md
docs/RISK_POLICY.md
docs/handoffs/PHASE_22.md
scripts/check.ps1
scripts/check.sh
scripts/generate_family_a_macro_vintage_candidate_inventory_amendment.py
scripts/verify_family_a_macro_vintage_candidate_inventory_amendment.py
scripts/verify_phase1.py
services/data/src/fable5_data/phase22/__init__.py
services/data/src/fable5_data/phase22/canonical.py
services/data/src/fable5_data/phase22/contracts.py
services/data/src/fable5_data/phase22/inventory_amendment.py
services/data/tests/test_phase22_contracts.py
services/data/tests/test_phase22_inventory_amendment.py
services/data/tests/test_phase22_security.py
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
tests/test_phase20_static.py
tests/test_phase21_static.py
tests/test_phase22_portable.py
tests/test_phase22_static.py
tests/test_repository_policy.py
```

Stop before any write outside this list. Do not modify Compose, dependencies, environment examples,
migrations, API code/tests, OpenAPI, generated TypeScript, accepted Phase 4-21 production/domain
files, paper/research/risk services, frontend product code, or visual snapshots. The two inherited
Phase 8 browser specs may only extend the supported phase range.

## Exact candidate and source contract

Freeze exactly one candidate group and one product:

```text
group:          PHILADELPHIA_FED_RTDSM_MACRO_VINTAGES_CANDIDATE
product:        PHILADELPHIA_FED_REAL_TIME_DATA_SET_FOR_MACROECONOMISTS
name:           Federal Reserve Bank of Philadelphia Real-Time Data Set for Macroeconomists (RTDSM)
capabilities:   (macro_regime_inputs,)
delivery state: DOCUMENTED_DOWNLOAD_SURFACE
review routing: NAMED_FOR_INDEPENDENT_CURRENT_RIGHTS_AND_FITNESS_REVIEW
entitlement:    UNPROVEN
rights:         NOT_REVIEWED
fitness:        UNPROVEN
```

Bind exactly these three ordered public first-party source codes and URLs:

```text
PHILADELPHIA_FED_RTDSM_OVERVIEW
https://www.philadelphiafed.org/surveys-and-data/real-time-data-research/real-time-data-set-for-macroeconomists

PHILADELPHIA_FED_RTDSM_PCPI
https://www.philadelphiafed.org/surveys-and-data/real-time-data-research/pcpi

PHILADELPHIA_FED_ONLINE_TERMS
https://www.philadelphiafed.org/about-us/privacy-notice
```

The narrow allowed facts are only that RTDSM documents vintages/snapshots and complete
per-vintage-history downloads for research; PCPI documents seasonally adjusted monthly vintages
from `1998:M11` with a complete history in each vintage column; and the Philadelphia Fed site terms
permit informational, educational, and research use while warning about third-party copyright.

Do not record LSEG or S&P as a second Phase 22 candidate. Do not record BLS as a candidate product.
The BLS CPI release archive is only a future reconciliation source because RTDSM's month-vintage
labels do not prove exact release timestamps.

## Exact frozen requirements and lineage

Bind these ordered future requirements:

```text
INDEPENDENT_CURRENT_USE_RIGHTS_AND_REVOCATION                NOT_STARTED
EXACT_SERIES_DELIVERY_SCHEMA_COVERAGE_AND_AVAILABILITY      NOT_STARTED
BLS_RELEASE_ARCHIVE_RECONCILIATION                           NOT_STARTED
EXPLICIT_OPERATIONAL_SOURCE_PRODUCT_COMPOSITION              BLOCKED
```

Preserve exactly:

- Phase 21 accepted commit/tree, artifact, policy, candidate-group, product-rights, capability,
  decision-field, gate, and rule identities;
- all six base candidate groups and nine base products without mutating their artifacts;
- the inherited product `FRED_REALTIME_AND_VINTAGE_WEB_SERVICE`, product SHA-256
  `dce1fbcdf188230ce03862a61b723d7ed63ffab76dc851294c027902de50ffcc`, finding SHA-256
  `7e286484a11ea083479e3a032d0b74ebbaf76bc0c4061298e746b73a09e2828d`, and conclusion
  `INELIGIBLE_CURRENT_TERMS_PROHIBIT_PERSISTENCE_AND_SOFTWARE_MODEL_USE`;
- every Phase 21 capability as `UNASSIGNED`, every decision value absent, every selection/current-
  rights marker false, and the existing Phase 15/16 missing/not-started state.

The amendment does not replace FRED or claim that FRED facts are current forever. It supplies a
new candidate for a later review; it does not apply that candidate to the operational composition.

## Contract and implementation shape

Use exactly:

```text
artifact:              phase22-family-a-macro-vintage-candidate-inventory-amendment-v1
source:                phase22-family-a-official-source-citation-v1
candidate group:       phase22-family-a-candidate-group-amendment-v1
candidate product:     phase22-family-a-macro-vintage-candidate-product-v1
future requirement:    phase22-family-a-future-review-requirement-v1
policy:                phase22-family-a-macro-vintage-candidate-inventory-amendment-policy-v1
sources manifest:      phase22-official-sources-manifest-v1
groups manifest:       phase22-candidate-groups-amendment-manifest-v1
products manifest:     phase22-candidate-products-amendment-manifest-v1
requirements manifest: phase22-future-review-requirements-manifest-v1
UUID namespace:        105305b7-a755-57d0-a5e0-9d3594b68db3
fixed timestamp:       2026-07-20T18:00:00.000000Z
reviewed on:           2026-07-20
artifact id:           9d763c2d-af50-5403-9646-50a88c962bd7
artifact SHA-256:      6f6079b69838cdd292f3d426c0b1e23deeec35eaeed9f4129aa129585913abe1
policy SHA-256:        dbd7f77b646d3386d17e889cd81a3a25aed099bfc3451c37844d02d87404ba5f
sources manifest:      870a238d76b5dc09630eee32c74f12d0e284b43ef6afee048b28817d62e7308a
groups manifest:       c1bc22f14d613a5af982b2a81dafa51e71da936418ef6624d41fb10c2713a5c8
products manifest:     138d492ed2e0975fe30534ab92724d822e4765e1a76137324f837272c0278796
requirements manifest: 109f4681e68ccc045c3e96eb662fb6023d4ef42f30d07a6339a696571d0d4d27
committed file SHA:     a28c7b2c3b398db8a64d05be7f7d625b52dcca178b2cccf2be4f614913f46111
committed bytes:        10,249
```

Implement:

1. Closed, extra-forbid Pydantic contracts for one citation, group, product, future requirement,
   manifests, and the root artifact.
2. One pure immutable builder bound to fixed source rows, the accepted Phase 21 identity, exact
   inherited FRED evidence, exact 3/1/1/4 counts, and the blocked result.
3. Domain-separated canonical row/manifest/policy/artifact hashes and a deterministic UUIDv5-style
   identity derived from the fixed namespace and policy hash.
4. One stdout-only generator with an exact confirmation-only CLI and one local-file verifier with
   bounded canonical UTF-8 reading, stable-read checks, path hardening, and sanitized failures.
5. Pure-domain, contract, security, portable parity, static integration, inherited PostgreSQL,
   browser regression, and repository-policy tests.

The generator and verifier must install active network/socket/database/subprocess/credential denial
before importing Phase 22 domain code. They accept no source/product override, score, rank,
selection, right, account, credential, URL, download, time, seed, expected hash, or semantic escape.
The committed artifact contains metadata and hashes only.

## Authority, persistence, migration, rollback, and failure semantics

Freeze true `metadata_only`, `candidate_inventory_amendment_only`,
`official_public_documentation_review_performed`, `runtime_network_disabled`,
`prior_candidate_inventory_unchanged`, `prior_rights_findings_unchanged`,
`phase21_decision_requirements_unchanged`, `inherited_fred_finding_unchanged`,
`live_path_absent`, `no_personalized_investment_advice`, and `no_real_performance_claimed`.

Freeze false every rank, recommendation, composition/selection, selection evidence, current-rights
review/grant/currentness, credential/account, external request/capture, provider-payload persistence,
ingestion, research, performance, promotion, risk, execution, and order field.

No migration or persistence change is permitted. Alembic stays at `0011_phase14`; the exact 57
inherited tables/functions, rows, migrations, API paths, generated contracts, and dependencies must
remain unchanged. Rollback removes only Phase 22 artifact/code/tests and the narrow wrapper, CI,
browser-range, and prose updates. It never rewrites an accepted migration, artifact, or baseline.

Invalid CLI arguments, missing/unsafe/unstable/oversized files, malformed or noncanonical JSON,
duplicate keys, floats/non-finite values, model/order/hash mismatch, any authority upgrade, or any
denied capability exits 2 with no stdout and exactly one generic sanitized stderr line. A canonical
blocked artifact exits 0.

## Executable acceptance plan

From the repository root, use the workspace Python when available and clear every provider, broker,
database, and cloud credential variable before testing. Generate twice and require exact bytes:

```powershell
$Python = if (Test-Path ".venv\Scripts\python.exe") { ".venv\Scripts\python.exe" } else { "python" }
$a = & $Python scripts/generate_family_a_macro_vintage_candidate_inventory_amendment.py --confirm-candidate-inventory-amendment-only
$b = & $Python scripts/generate_family_a_macro_vintage_candidate_inventory_amendment.py --confirm-candidate-inventory-amendment-only
if ($LASTEXITCODE -ne 0 -or $a -cne $b) { throw "Phase 22 generation drifted" }
```

Then require committed parity and portable verification:

```powershell
$committed = Get-Content docs/PHASE_22_FAMILY_A_MACRO_VINTAGE_CANDIDATE_INVENTORY_AMENDMENT.json -Raw
if (($a -join "`n") + "`n" -cne $committed) { throw "Phase 22 committed artifact drifted" }
& $Python scripts/verify_family_a_macro_vintage_candidate_inventory_amendment.py --amendment docs/PHASE_22_FAMILY_A_MACRO_VINTAGE_CANDIDATE_INVENTORY_AMENDMENT.json
if ($LASTEXITCODE -ne 0) { throw "Phase 22 portable verifier failed" }
```

Run focused and inherited checks:

```powershell
& $Python -m pytest services/data/tests/test_phase22_contracts.py services/data/tests/test_phase22_inventory_amendment.py services/data/tests/test_phase22_security.py tests/test_phase22_portable.py tests/test_phase22_static.py
.\scripts\check.ps1
.\scripts\test.ps1
npm run build
& $Python scripts/verify_phase1.py --static-only --phase 22
git diff --check
```

Commit one clean Phase 22 SHA/tree and run the complete Windows gate:

```powershell
& $Python scripts/verify_phase1.py --phase 22
```

The full gate must prove repeated canonical generation, portable verifier parity, exact lineage and
registries, denial-boundary adversarial cases, zero writes across all 57 inherited tables, migration
head `0011_phase14`, unchanged API/contracts/dependencies, inherited browser regressions, unsupported
phase 0/23 exit 2, and complete resource/evidence cleanup. Ubuntu `preflight`, `unit`, and
`phase22-compose` must then pass at the identical committed SHA/tree before Phase 22 is accepted.

## Stop condition

Stop after Phase 22 implementation and same-SHA Windows/Ubuntu acceptance. Do not treat candidate
inventory as operational selection. Do not contact a provider or counsel; use a login/credential;
request a subscription, quote, entitlement, sample, or data; download or persist provider bytes;
perform the future rights/fitness review or BLS reconciliation; populate a Phase 21 decision field;
start Phase 16 Step 3; define a policy/holdout; execute research; compute performance; promote a
strategy; mutate risk/governance; submit/reconcile an order; add a live path; or begin Phase 23
without separate authorization.
