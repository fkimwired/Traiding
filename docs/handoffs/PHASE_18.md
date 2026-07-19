# Phase 18 Family A current-use-rights review handoff

## Objective and explicit exclusions

Implement one deterministic, portable, database-free, network-disabled technical review of current
official public terms for the exact nine Phase 17 product identities. Attempt only Phase 16 Step 2,
`REVIEW_CURRENT_USE_RIGHTS`, and emit its two required outputs:
`independent_rights_review_sha256` and `rights_currentness_sha256`.

The successful truthful outcome is `BLOCKED_NO_OPERATIONAL_SELECTION`. Phase 16 Steps 1 and 2 are
`OUTPUT_FROZEN`; Steps 3-7 remain `NOT_STARTED`. Review selection and even a public-rights finding
are not operational source/provider/product selection.

Do not add or use legal advice, provider contact, procurement, an account, a credential, a contract
acceptance, a provider request, an external sample or payload, data capture, ingestion, normalization,
quarantine, snapshot execution, evaluation-policy or holdout work, research, performance, promotion,
approval, risk mutation, execution, order/fill behavior, migration, API, frontend product control,
publication, deployment, Phase 19 behavior, or a live path.

## Accepted input identity

Start only from the formally accepted Phase 17 identity:

- Commit: `fd89d3905e9c2ea12223e30b5822a0fdda795a26`
- Tree: `f2eb791785dd10cc9316d174505b65eda919fe71`
- Artifact id: `19d213d5-ec44-53fc-a146-f4f77a06102d`
- Artifact SHA-256:
  `48584cf614c7713b05417a6d9333ca400f2d1c19fb0d3f047ced42e9ef4eb8f4`
- Policy SHA-256:
  `0a36f01630a40c55d20139117641abcc8313e5f8b5a0be5fce15fd4c8ad2b3cf`
- Inventory SHA-256:
  `070f36391093385ccd0e7feafc54d18c08e71cc8aa145bd30acea07abbffc76c`
- Windows Phase 17 full verifier passed with complete cleanup and a clean worktree/index.
- Ubuntu run `29682173053`: `preflight`, `unit`, and `phase17-compose` passed at the same identity.

Stop before editing on a different identity, ambiguous pre-existing change, or non-reproducing Phase
17 artifact. Preserve unrelated user work.

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

## Exact write allowlist

Write only these 38 paths:

```text
.github/workflows/ci.yml
Makefile
README.md
docs/COMPLIANCE_NOTES.md
docs/DATA_SOURCES.md
docs/EVALS.md
docs/IMPLEMENTATION_PLAN.md
docs/PHASE_18_FAMILY_A_CURRENT_USE_RIGHTS_REVIEW.json
docs/PHASE_18_FAMILY_A_CURRENT_USE_RIGHTS_REVIEW_DECISIONS.md
docs/RISK_POLICY.md
docs/handoffs/PHASE_18.md
scripts/check.ps1
scripts/check.sh
scripts/generate_family_a_current_use_rights_review.py
scripts/verify_family_a_current_use_rights_review.py
scripts/verify_phase1.py
services/data/src/fable5_data/phase18/__init__.py
services/data/src/fable5_data/phase18/canonical.py
services/data/src/fable5_data/phase18/contracts.py
services/data/src/fable5_data/phase18/rights_review.py
services/data/tests/test_phase18_contracts.py
services/data/tests/test_phase18_rights_review.py
services/data/tests/test_phase18_security.py
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
tests/test_phase18_portable.py
tests/test_phase18_static.py
tests/test_repository_policy.py
```

Stop before a write outside this list. Do not modify Compose, dependencies, environment examples,
migrations, API code/tests, OpenAPI, generated TypeScript, `scripts/run_phase_gate.py`, accepted
Phase 4-17 production code, paper/research/risk services, frontend product code, or visual snapshots.
The inherited Phase 8 browser specs are in scope only to extend the phase range without changing
product assertions or baselines.

## Exact review contract

Bind the accepted Phase 17 inventory exactly. Use the fixed source-review timestamp
`2026-07-19T15:58:18.5305832Z`. It is the time at which official public metadata was reviewed, not a
runtime clock or a currentness guarantee.

Use these exact contract identities:

```text
artifact schema/hash domain: phase18-family-a-current-use-rights-review-v1
policy id/hash domain: phase18-family-a-current-use-rights-review-policy-v1
public-terms source schema/hash domain: phase18-family-a-public-terms-source-v1
product-rights finding schema/hash domain: phase18-family-a-product-rights-finding-v1
source-plan step schema/hash domain: phase18-family-a-source-plan-step-evidence-v1
source-plan output schema/hash domain: phase18-family-a-source-plan-output-v1
sources manifest domain: phase18-public-terms-sources-manifest-v1
review manifest domain: phase18-independent-rights-review-manifest-v1
currentness snapshot domain: phase18-rights-currentness-review-snapshot-v1
source-plan steps manifest domain: phase18-source-plan-steps-manifest-v1
artifact UUID namespace: 50f38b59-85dc-5a38-be19-e9e035ed9284
```

Do not invent final artifact, manifest, policy, or verifier hashes before deterministic generation.

The ordered products remain:

```text
TIINGO_END_OF_DAY
TIINGO_US_FUNDAMENTALS
TIINGO_DIVIDEND_CORPORATE_ACTIONS
TIINGO_SPLIT_CORPORATE_ACTIONS
MORNINGSTAR_CRSP_US_STOCK_DATABASES
MORNINGSTAR_CRSP_COMPUSTAT_MERGED
SEC_EDGAR_SUBMISSIONS_AND_XBRL_DATA_APIS
FRED_REALTIME_AND_VINTAGE_WEB_SERVICE
LSEG_TICK_HISTORY_INSTRUMENT_AND_VENUE_WEB_API
```

Each row contains exactly eight rights dimensions in this order: storage,
non-display/internal use, derived data, retention/deletion, redistribution,
revocation/currentness, delivery, and entitlement. Values are restricted to:

```text
ALLOWED_PUBLIC
CONDITIONAL_ACCOUNT_LICENSE
PRIVATE_LICENSE_REQUIRED
PROHIBITED_PUBLIC_TERMS
UNPROVEN
```

The exact matrix and exact finding outcomes are frozen in
`docs/PHASE_18_FAMILY_A_CURRENT_USE_RIGHTS_REVIEW_DECISIONS.md`. Do not weaken a restrictive state,
invent entitlement, infer private-license currentness, or translate SEC public reuse support into
operational selection. The aggregate outcome is only `BLOCKED_NO_OPERATIONAL_SELECTION`.

Bind the exact 24 official-source codes and metadata rows in the decision document. Each source row
has an HTTPS URL, official title, publisher, stated update date or `UNSTATED`, clause locator,
applicable product codes, conservative paraphrase, fixed reviewed-at timestamp, and a revalidation
requirement. Store no remote HTTP response body. Generation/verification must not browse.

The architecture review itself accessed those official public web pages read-only. Treat
`operational_external_request_performed=false` as no operational provider, account, entitlement, or
data request; do not misstate the official-document review as having made no HTTP request at all.
The generated artifact records inert metadata and paraphrases, not remote HTTP response bodies.

For the FRED row, freeze `non_display_internal_use=PROHIBITED_PUBLIC_TERMS` and conclusion
`INELIGIBLE_CURRENT_TERMS_PROHIBIT_PERSISTENCE_AND_SOFTWARE_MODEL_USE`. Bind general prohibition
(p) and API prohibition (k), which prohibit using FRED Services or API content in connection with
development or training of software systems or machine-learning models, in addition to the separate
persistence, derivative, retention, redistribution, third-party-series, and termination blockers.

Attribute the descriptive User-Agent containing company name and administrative contact to
`SEC_ACCESSING_EDGAR`. `SEC_DEVELOPER_RESOURCES` supports efficient needed-only requests, current
fair-access/security policy, the no-unclassified-bot rule, and the aggregate rate limit; do not bind
the declared-header fact to that row.

## Step and currentness semantics

Phase 18 freezes the Phase 16 Step 2 outputs without changing the original plan artifact:

```text
SELECT_CANDIDATE_PRODUCTS                           OUTPUT_FROZEN
REVIEW_CURRENT_USE_RIGHTS                          OUTPUT_FROZEN
QUALIFY_BOUNDED_READ_ONLY_SAMPLES                  NOT_STARTED
PRODUCE_FULL_HISTORY_COVERAGE_MANIFEST             NOT_STARTED
RECONCILE_TEMPORAL_IDENTITY_REVISION_SEMANTICS     NOT_STARTED
DESIGN_LOCAL_QUARANTINE_AND_CANONICAL_SNAPSHOT     NOT_STARTED
REQUEST_SEPARATE_INGESTION_AUTHORITY               NOT_STARTED
```

`OUTPUT_FROZEN` means only that deterministic metadata outputs exist. The aggregate rights review is
blocked, not passed. Public pages are frozen provenance but are not continuously authenticated.
Private license, account, entitlement, renewal, revocation, and expiry state are unproven. Any later
separately authorized action must re-review current official policy and the exact executed contract,
order form, schedule, third-party rights, legal entity, SKU, delivery, territory, use, storage,
non-display, derived, retention/deletion, redistribution, audit, termination, and revocation scope.
Missing, changed, expired, or revoked evidence fails closed.

All Phase 15 gaps carried through Phase 17 remain unchanged. In particular, do not mark
`INDEPENDENT_CURRENT_USE_RIGHTS`, `RIGHTS_CURRENTNESS_REVOCATION`, complete point-in-time coverage,
schema/quality fitness, evaluation policy, confirmation holdout, or research-data eligibility passed.

## Authority and security invariants

Freeze false: operational source/provider/product selection; account verification; credential
loading; subscription/entitlement verification; executed-license, counsel, currentness, or rights
verification/grant; delivery/coverage/schema/fitness proof; operational provider/account/data
request, sample, or capture; provider
or licensed-payload persistence; ingestion/snapshot; evaluation-policy/holdout; research/performance;
`PASS_RESEARCH`; promotion; paper approval; risk clearance; execution; and order submission. Freeze
live-path absence, no personalized advice, and no real-performance claims true.

No credential, secret-name value, account identifier, entitlement document, contract/license body,
provider response, observation, dataset, schema sample, price, position, feature, label, signal,
return, performance metric, order, or fill may enter source, fixtures, artifact, stdout/stderr, logs,
builds, browser output, CI evidence, or temporary files.

## Implementation units

1. Strict canonical source, finding, step, output, policy, and artifact contracts with domain-separated
   hashes and no I/O dependency.
2. One immutable server-owned review builder bound to accepted Phase 17 lineage, exact source catalog,
   exact rights matrix, fixed timestamp, blocked outcome, and false authority boundary.
3. One stdout-only deterministic generator with no override that can change facts, authority, time,
   hashes, products, sources, or outcomes.
4. One offline verifier for one bounded regular canonical UTF-8 JSON file.
5. One committed generated artifact with exact repeated-run byte parity.
6. Focused contract/review/security tests and portable adversarial tests.
7. Static/full verifier, root wrappers, inherited browser range, and Ubuntu CI support through Phase
   18.
8. Decision, source, evaluation, risk, compliance, implementation, service-status, and handoff docs.

The generator/verifier accept no URL, source, product, status, rights, credential, provider, account,
data, output, repair, expected-hash, authority, strategy, threshold, holdout, order, clock, random seed,
or arbitrary-hash override. Deny network, socket, database, subprocess, credential, provider SDK,
research, broker, and execution dependencies.

## Persistence, API, migration, rollback, and failures

Phase 18 owns no persistence, API, schema, OpenAPI, generated contract, dependency, Compose, or
frontend product surface. Retain migrations `0001` through `0011_phase14`, all 57 inherited
tables/functions, all existing rows, and all generated-contract bytes. Add no `0012`, route, model,
connection, table, function, trigger, scheduler, transport, or vendor SDK.

Phase 18 adds no migration; Alembic head remains exactly `0011_phase14`.

The inherited nonempty `0010_phase13 -> 0011_phase14 -> 0010_phase13 -> 0011_phase14` cycle remains
the rollback proof. Phase 18 rollback removes only its portable files and wrapper/CI registrations;
it cannot require data or schema rollback.

Invalid CLI arguments, unsupported phase values 0/19, malformed/noncanonical files, nonregular files,
oversized inputs, unknown fields, changed source/product order, rights inflation, hash mismatch,
network/database/subprocess attempts, credentials, later-step completion, or any true authority bit
must fail closed with sanitized errors and no side effect. A valid blocked artifact returns success;
`BLOCKED_NO_OPERATIONAL_SELECTION` is the required domain result, not verifier failure.

## Executable acceptance plan

From the repository root, use the pinned virtual environment and run focused checks first:

```powershell
.\.venv\Scripts\python.exe -m pytest `
  services/data/tests/test_phase18_contracts.py `
  services/data/tests/test_phase18_rights_review.py `
  services/data/tests/test_phase18_security.py `
  tests/test_phase18_portable.py `
  tests/test_phase18_static.py -q
```

Prove stdout generation, repeated-run parity, committed-artifact parity, and offline verification:

```powershell
.\.venv\Scripts\python.exe scripts\generate_family_a_current_use_rights_review.py `
  --confirm-public-terms-review-only > $env:TEMP\phase18-a.json
.\.venv\Scripts\python.exe scripts\generate_family_a_current_use_rights_review.py `
  --confirm-public-terms-review-only > $env:TEMP\phase18-b.json
Get-FileHash $env:TEMP\phase18-a.json -Algorithm SHA256
Get-FileHash $env:TEMP\phase18-b.json -Algorithm SHA256
Compare-Object (Get-Content $env:TEMP\phase18-a.json -Raw) (Get-Content $env:TEMP\phase18-b.json -Raw)
.\.venv\Scripts\python.exe scripts\verify_family_a_current_use_rights_review.py `
  --review docs\PHASE_18_FAMILY_A_CURRENT_USE_RIGHTS_REVIEW.json
```

The tests must exercise the valid blocked domain path and adversarially reject any forged completed
or cleared operational-rights state plus missing, duplicate, reordered, substituted, unknown, cross-row,
applicability, URL, title, publisher, date, locator, fact, status, outcome, currentness, step, output,
authority, canonical-preimage, and hash tampering. Prove remote-body, credential, secret, and licensed-
payload canaries never enter artifacts or diagnostics. Monkeypatch network/socket, database,
subprocess, environment-credential, runtime-clock/random, Git, and filesystem-discovery surfaces to
raise if touched.

Run the host gates and build:

```powershell
$env:FABLE5_VERIFY_PHASE = "18"
.\scripts\check.ps1
.\scripts\test.ps1
npm run build
.\.venv\Scripts\python.exe scripts\verify_phase1.py --static-only --phase 18
```

Before the full gate, create one honest commit and confirm a clean index/worktree. Then run exactly:

```powershell
.\.venv\Scripts\python.exe scripts\verify_phase1.py --phase 18
```

The full verifier must bind initial/final HEAD and tree, prove clean status, no migrations/schema/row
or API/generated-contract drift, zero writes around portable and browser stages, the inherited
nonempty migration cycle, stage-local Phase 8/10/11 browser/accessibility/visual regressions, and
complete cleanup of `fable5_acceptance_*` containers, networks, volumes, processes, browser outputs,
and temporary files. It must reject dirty identity and stale resources before startup.

Push only if separately authorized for acceptance. Ubuntu Actions must run `preflight`, `unit`, and
`phase18-compose` at the identical committed SHA/tree and show the same artifact hashes and cleanup.
Until both Windows and Ubuntu pass at that identity, report Phase 18 as implemented but not formally
accepted.

## Handoff report

Report final commit/tree, exact changed paths, host and focused-test counts, artifact/generator/
verifier hashes, exact official-source bindings and timestamp, all nine rights findings, aggregate
blocked result, Step 1/2 frozen and Step 3-7 not-started evidence, false-authority proof, tamper and
network/database/secret denial proof, no-schema/no-API/zero-write proof, inherited-browser proof,
cleanup proof, and same-SHA Ubuntu status.

State explicitly that review selection is not operational selection; public sources were reviewed at
a fixed time but are not continuously authenticated; the SEC row grants no operational selection;
FRED prohibits the planned software/model use and persistence; and no credential, operational
provider/account/data request, data capture, database write, research, execution, order, or live path
occurred.

## Stop condition

Stop after Phase 18 is implemented and, when authorized, accepted on Windows and Ubuntu. Do not
begin Phase 19, obtain/load a credential, contact a provider or counsel, inspect an account, accept a
contract, make a provider/data request, qualify or capture a sample, persist or ingest non-synthetic
data, create a snapshot, freeze an incomplete evaluation policy, open a holdout, run/promote research,
modify approval/risk, submit/reconcile an order, add live capability, open a PR, tag, publish,
release, or deploy without separate explicit authority.
