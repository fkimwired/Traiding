# Phase 17 Family A candidate-product inventory handoff

## Objective and explicit exclusions

Implement one deterministic, portable, database-free, network-disabled metadata inventory that
attempts only Phase 16 Step 1, `SELECT_CANDIDATE_PRODUCTS`, and emits its required
`candidate_product_inventory_sha256` output. The artifact records exact officially documented
product names and routes them only to a future independent rights review.

The Step 1 output state is `OUTPUT_FROZEN`, but the artifact outcome is necessarily `BLOCKED`:
CRSP delivery variants and entitlements are unproven; the LSEG identity does not prove an obtainable
Fable5 delivery, schema, coverage, or use scope; and no candidate has independently reviewed current
rights or proven Family A fitness. A blocked artifact is the truthful deliverable, not a partial
success to upgrade.

Do not add or use a credential, provider call, transport, vendor SDK, account, subscription,
entitlement assertion, contract body, external sample, payload, observation, dataset path, capture,
ingestion, normalization execution, quarantine execution, snapshot, evaluation threshold, embargo
decision, holdout, feature, label, signal, trial, return, performance result, promotion, approval,
risk mutation, broker/order/fill behavior, API, migration, frontend product control, live path,
publication, deployment, or later phase.

## Accepted input identity

Start only from the formally accepted Phase 16 identity:

- Commit: `7c4df26733b4ad13c49c455ea5f28f627012ee44`
- Tree: `c69b4a60237ae3588f8544272b75becbf0a763e8`
- Phase 16 artifact id: `e106a766-5cfe-5a1c-94f6-ee1c2ac68652`
- Phase 16 artifact SHA-256:
  `74ddf4a51d722b494fd494241e2e5927bff6fde034f6932dcfd791bb3a0706bb`
- Phase 16 policy SHA-256:
  `57cfcfd09f2d4a87d9562fd536228b9f05693bb71b7e9d1867618a35da7d4efd`
- Phase 16 Step 1 SHA-256:
  `b91451d90ea1ae672ccab878df742b91b62d1b33902f9be05a0b6e1395502ec1`
- Windows full Phase 16 verifier passed with complete cleanup and that clean identity.
- Ubuntu run `29675183969`: `preflight`, `unit`, and `phase16-compose` passed at that same identity.

Stop before editing on a different SHA/tree, a dirty worktree or index, ambiguous changes, or a
non-reproducing Phase 16 artifact.

Authority sources:

- `AGENTS.md`
- `RESEARCH_SUPPLEMENT.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/EVALS.md`
- `docs/RISK_POLICY.md`
- `docs/DATA_SOURCES.md`
- `docs/COMPLIANCE_NOTES.md`
- `docs/PHASE_13_POINT_IN_TIME_DATA_QUALIFICATION_DECISIONS.md`
- `docs/PHASE_14_RESEARCH_INGESTION_ELIGIBILITY_DECISIONS.md`
- `docs/PHASE_15_FAMILY_A_RESEARCH_ADMISSION_SPECIFICATION_DECISIONS.md`
- `docs/PHASE_16_FAMILY_A_POINT_IN_TIME_SOURCE_PLAN_DECISIONS.md`
- `docs/PHASE_17_FAMILY_A_CANDIDATE_PRODUCT_INVENTORY_DECISIONS.md`

## Exact write allowlist

Write only these 37 paths:

```text
.github/workflows/ci.yml
Makefile
README.md
docs/COMPLIANCE_NOTES.md
docs/DATA_SOURCES.md
docs/EVALS.md
docs/IMPLEMENTATION_PLAN.md
docs/PHASE_17_FAMILY_A_CANDIDATE_PRODUCT_INVENTORY.json
docs/PHASE_17_FAMILY_A_CANDIDATE_PRODUCT_INVENTORY_DECISIONS.md
docs/RISK_POLICY.md
docs/handoffs/PHASE_17.md
scripts/check.ps1
scripts/check.sh
scripts/generate_family_a_candidate_product_inventory.py
scripts/verify_family_a_candidate_product_inventory.py
scripts/verify_phase1.py
services/data/src/fable5_data/phase17/__init__.py
services/data/src/fable5_data/phase17/canonical.py
services/data/src/fable5_data/phase17/contracts.py
services/data/src/fable5_data/phase17/inventory.py
services/data/tests/test_phase17_contracts.py
services/data/tests/test_phase17_inventory.py
services/data/tests/test_phase17_security.py
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
tests/test_phase17_portable.py
tests/test_phase17_static.py
tests/test_repository_policy.py
```

Stop before any write outside this list. Do not modify Compose, dependencies, environment examples,
migrations, API code/tests, OpenAPI, generated TypeScript, `scripts/run_phase_gate.py`, accepted
Phase 4-16 production code, paper/research/risk services, frontend product code, or visual baselines.
The inherited Phase 8 browser specs are permitted only for the Phase 17 verifier range and must not
change product assertions or snapshots.

## Exact step semantics

Bind the accepted Phase 16 Step 1 exactly:

```text
code: SELECT_CANDIDATE_PRODUCTS
step SHA-256: b91451d90ea1ae672ccab878df742b91b62d1b33902f9be05a0b6e1395502ec1
prerequisites: none
required prior evidence: none
required output: candidate_product_inventory_sha256
definition: Select exact candidate products only after separately authorized current documentation review.
```

Phase 17 completes the implementation and evidence output for the step attempt. Its Step 1 output
state is `OUTPUT_FROZEN`; its overall outcome remains `BLOCKED`. The required inventory hash does
not imply that any rights, delivery, coverage, or fitness prerequisite passed. Keep Phase 16 Steps
2-7 `NOT_STARTED` and preserve all nineteen Phase 15 gap states carried by the Phase 16 plan.

`selected_for_independent_rights_review=true` means only that the documented product identity may be
sent to a later independent reviewer. It is never operational `source_selected`,
`provider_selected`, or `product_selected`; those authority fields remain false.

Use exactly:

```text
artifact: phase17-family-a-candidate-product-inventory-v1
policy: phase17-family-a-candidate-product-inventory-policy-v1
product: phase17-family-a-candidate-product-v1
candidate group: phase17-family-a-candidate-product-group-v1
source-plan step evidence: phase17-family-a-source-plan-step-evidence-v1
source-plan output: phase17-family-a-source-plan-output-v1
products manifest: phase17-candidate-products-manifest-v1
candidate-groups manifest: phase17-candidate-groups-manifest-v1
source-plan steps manifest: phase17-source-plan-steps-manifest-v1
artifact UUID namespace: d987843d-6474-5e17-a00d-bf1bf73fb7a8
fixed timestamp: 2026-07-19T00:00:00Z
```

The exact ordered product codes are:

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

Every product has `selected_for_independent_rights_review=true`, operational provider/product/source
selection false, and entitlement/rights/fitness `UNPROVEN`. Only the two Morningstar/CRSP rows have
delivery-variant state `UNPROVEN`; every other row has `DOCUMENTED_WEB_API_SURFACE`, which proves
only that the official page documents a Web/API surface. Every inherited Phase 16 candidate group
has `selection_state=NAMED_FOR_INDEPENDENT_RIGHTS_REVIEW` and
`single_operational_selection=false`.

## Exact product/reference inventory

Record only these current official product/reference sets:

1. `TIINGO_PHASE13_BOUNDED_CANDIDATE`
   - [End-of-Day Stock Price API](https://www.tiingo.com/documentation/end-of-day)
   - [U.S. Fundamental Data API](https://www.tiingo.com/documentation/fundamentals)
   - [Dividend API](https://www.tiingo.com/documentation/corporate-actions/dividends)
   - [Split API](https://www.tiingo.com/documentation/corporate-actions/splits)
   - [Terms of Use](https://app.tiingo.com/tos/)
   - selected only for independent rights review; token, add-on, beta/early-release, commercial-plan,
     internal-use, and redistribution limitations remain explicit.
2. `MORNINGSTAR_CRSP_US_STOCK_DATABASES_CANDIDATE`
   - [CRSP US Stock Databases](https://indexes.morningstar.com/research-data-products/crsp-us-stock-databases)
   - [Morningstar migration notice](https://www.crsp.org/introducing-the-new-home-for-crsp-research-data-products/)
   - selected only for independent rights review; SKU, delivery variant, entitlement, and all use
     rights remain unproven.
3. `MORNINGSTAR_CRSP_COMPUSTAT_MERGED_DATABASE_CANDIDATE`
   - [CRSP/Compustat Merged Database](https://indexes.morningstar.com/research-data-products/crsp-compustat-merged-database)
   - selected only for independent rights review; it requires CRSP US Stock and Compustat
     Xpressfeed licenses and is not a stand-alone entitlement.
4. `SEC_EDGAR_SUBMISSIONS_XBRL_CANDIDATE`
   - [EDGAR APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
   - [SEC developer resources](https://www.sec.gov/about/developer-resources)
   - [reuse guidance](https://www.sec.gov/about/webmaster-frequently-asked-questions)
   - selected only for independent rights/access-policy review; no-key public access and reuse do
     not prove normalized point-in-time fitness.
5. `FEDERAL_RESERVE_ALFRED_VINTAGES_CANDIDATE`
   - [FRED API overview](https://fred.stlouisfed.org/docs/api/fred/overview.html)
   - [FRED real-time periods](https://fred.stlouisfed.org/docs/api/fred/realtime_period.html)
   - [`fred/series/vintagedates`](https://fred.stlouisfed.org/docs/api/fred/series_vintagedates.html)
   - [FRED terms](https://fred.stlouisfed.org/legal/terms/)
   - selected only for independent rights review; registered API key, third-party series rights, and
     the current storage/cache/archive/database prohibition remain explicit.
6. `HISTORICAL_LIQUIDITY_PRODUCT_UNSELECTED`
   - [LSEG Tick History — Instrument & Venue Access via Web/API](https://www.lseg.com/en/data-analytics/market-data/data-feeds/tick-history)
     is selected only for independent rights review.
   - the official page describes 580+ venues, Level 1/2 history reaching as far back as January 1996,
     raw/normalized formats, and instrument or venue-by-day Web/API extracts.
   - exact Fable5 delivery availability, instruments, venues, fields, dates, schema, entitlement,
     rights, currentness, quality, and Family A fitness remain unproven; do not contact sales or
     request an extract.

No row may claim accepted schema, full-history coverage, data quality, current entitlement, delivery
availability, storage/non-display/derived/retention/redistribution rights, or Family A fitness.

## Authority and security invariants

Freeze global source/provider/product selection false despite the review-routing markers. Freeze
credentials, rights verification/grant, external request/capture, payload persistence, licensed-data
persistence, ingestion, snapshot, data eligibility, evaluation-policy approval, holdout,
research/performance, `PASS_RESEARCH`, promotion, paper approval, risk clearance, execution, and
order submission false. Freeze live-path absence and no-advice/no-real-performance statements true.

The artifact may contain only fixed public metadata and hashes. No environment variable, local
secret, entitlement document, contract text, provider body, observation value, account, price,
position, order, return, or metric may enter the artifact, stdout, stderr, logs, build, CI evidence,
browser evidence, or temporary output.

## Implementation units

1. Strict canonical contracts and hash domains with no I/O dependency.
2. One server-owned immutable inventory builder bound to the accepted Phase 16 identity and exact
   Step 1.
3. One stdout-only deterministic generator.
4. One offline verifier for one supplied bounded regular canonical JSON file.
5. One committed generated JSON artifact with byte-for-byte generator parity.
6. Static/full verifier integration, wrappers, inherited browser range, and Ubuntu CI through Phase
   17.
7. Data, evaluation, compliance, risk, implementation, service-status, decision, and handoff docs.

The generator/verifier accept no provider, product, URL, rights, credential, data, output, network,
authority, repair, expected-hash, strategy, threshold, holdout, order, clock, seed, or arbitrary-hash
override. The implementation must deny network, database, subprocess, credential, provider,
research, broker, and execution dependencies.

## Persistence, API, migration, and rollback

Phase 17 owns no persistence, API, or schema. Retain migrations `0001` through `0011_phase14`, all 57
inherited tables/functions, all earlier rows, and all OpenAPI/generated TypeScript bytes. Add no
`0012`, route, API model, database connection, table, function, or trigger.

The inherited nonempty `0010_phase13 -> 0011_phase14 -> 0010_phase13 -> 0011_phase14` cycle remains
the rollback proof. Phase 17 rollback deletes only its portable files and wrapper/CI registrations;
it cannot require a data or schema rollback.

## Acceptance

Require:

- parser/wrappers accept Phases 1-17 and reject 0/18/malformed input with exit 2;
- exact allowlist and accepted Phase 16 baseline ancestry;
- deterministic committed-file/generator parity across repeated runs and platforms;
- exact Phase 16 Step 1 identity, `OUTPUT_FROZEN` output state, and
  `candidate_product_inventory_sha256` output;
- only the truthful overall `BLOCKED` outcome, with all delivery/coverage/rights/fitness limitations
  preserved;
- exact product names, official URLs, review-selection semantics, and source caveats above;
- Phase 16 Steps 2-7 remain `NOT_STARTED`; all inherited gap states remain unchanged;
- source/provider/product operational selection and every external/data/research/risk/execution/order
  authority remain false;
- missing, duplicate, reordered, substituted, unknown, cross-row, URL, fact, state, reason,
  prerequisite, output, authority, canonical-preimage, and hash tampering is rejected;
- product substitution, composite undocumented products, rights inflation, coverage inflation, and
  completed later steps are rejected;
- active network/database denial, absence of transport/SQLAlchemy/FastAPI/vendor SDK/subprocess
  dependencies, and secret/licensed-data canary protection;
- no migration, table, row, SQL function, API/OpenAPI, generated-contract, dependency, Compose,
  product UI, or visual-baseline drift;
- inherited Phase 8/10/11 browser/accessibility/visual regressions run at their correct stage-local
  migration heads and leave the final `0011_phase14` head unchanged;
- repository identity and all database resources remain unchanged around portable/browser stages;
- clean Windows and Ubuntu gates pass at one committed SHA/tree with complete container, network,
  volume, process, browser, and temporary-output cleanup.

## Data and security posture

Official documentation was used only to freeze public metadata. Ordinary generation, verification,
tests, and CI use no credentials and deny external network. No documentation link is dynamically
fetched during acceptance. A valid canonical hash proves only deterministic integrity of the
metadata inventory; it is not source authenticity, legal advice, contract acceptance, entitlement,
or data authority.

## Handoff report

Report final commit/tree, exact changed paths, host-gate counts, generator/artifact/verifier hashes,
blocked/tamper evidence, exact official-source bindings, LSEG identity-only proof, rights/fitness
limitations, unchanged-step/gap proof, no-schema/no-API/zero-write proof, inherited-browser proof,
cleanup evidence, and Ubuntu status at the exact Phase 17 identity.

State explicitly that review selection is not operational selection and that no credential,
provider call, data capture, ingestion, snapshot, evaluation policy, holdout, research run,
performance computation, promotion, approval, risk mutation, order, or live path occurred.

## Stop condition

Stop after Phase 17 is accepted on Windows and Ubuntu. Do not begin Phase 18, obtain or load a
credential, contact a provider, qualify a sample, ingest or persist non-synthetic data, freeze an
incomplete evaluation policy, open a holdout, run or promote research, modify governance/risk, add an
order path, add a live capability, open a PR, tag, publish, release, or deploy.

If separately authorized later, Phase 18 may perform only an independent current-use-rights and
currentness review over these metadata identities. It may not perform sampling, capture, ingestion,
research, execution, or any other Phase 16 future step.
