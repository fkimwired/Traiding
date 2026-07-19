# Phase 17 Family A candidate-product inventory decisions

## Accepted baseline and authority

Phase 17 starts only from the formally accepted Phase 16 identity:

- Commit: `7c4df26733b4ad13c49c455ea5f28f627012ee44`
- Tree: `c69b4a60237ae3588f8544272b75becbf0a763e8`
- Phase 16 artifact id: `e106a766-5cfe-5a1c-94f6-ee1c2ac68652`
- Phase 16 artifact SHA-256:
  `74ddf4a51d722b494fd494241e2e5927bff6fde034f6932dcfd791bb3a0706bb`
- Phase 16 policy SHA-256:
  `57cfcfd09f2d4a87d9562fd536228b9f05693bb71b7e9d1867618a35da7d4efd`
- Phase 16 Step 1 SHA-256:
  `b91451d90ea1ae672ccab878df742b91b62d1b33902f9be05a0b6e1395502ec1`
- Windows full Phase 16 verifier: passed at that identity with complete cleanup and a clean
  worktree/index.
- Ubuntu GitHub Actions run `29675183969`: `preflight`, `unit`, and `phase16-compose` passed at the
  same commit/tree.

The user separately authorized Phase 17. This decision narrows that authority to the first future
step frozen by Phase 16, `SELECT_CANDIDATE_PRODUCTS`, and to its sole required output,
`candidate_product_inventory_sha256`. The separately authorized current-documentation review may
identify exact product names and official documentation surfaces. It does not authorize a
credential, account, procurement, provider request, sample, payload, data capture, contract
acceptance, rights attestation, ingestion, snapshot, evaluation policy, holdout, research run,
performance result, promotion, risk clearance, paper order, or live path.

## Decision and truthful outcome

Phase 17 is one deterministic, portable, database-free, network-disabled metadata inventory. It
binds the accepted Phase 16 artifact and records which exact documented product sets are suitable
only for a later independent current-use-rights review.

Phase 17 completes the implementation and evidence output for the Phase 16 Step 1 attempt. Its Step
1 output state is `OUTPUT_FROZEN`, and the artifact carries
`candidate_product_inventory_sha256`. The artifact's truthful overall outcome remains `BLOCKED`
because:

1. CRSP delivery variants and every CRSP/Morningstar entitlement remain unproven;
2. the selected-for-review LSEG delivery identity does not prove the exact instruments, venues,
   fields, dates, schema, availability, entitlement, or retained-use scope Fable5 could obtain;
3. every candidate's storage, non-display, derived-data, retention, revocation, and current-use
   rights remain unreviewed; and
4. documentation cannot prove complete point-in-time coverage, schema fitness, quality, or Family A
   research eligibility.

`BLOCKED` is an expected, successful representation of the current evidence. It is not an error to
repair with an optimistic default. The Phase 16 steps `REVIEW_CURRENT_USE_RIGHTS` through
`REQUEST_SEPARATE_INGESTION_AUTHORITY` remain `NOT_STARTED`.

## Selection vocabulary

`selected_for_independent_rights_review` is a metadata-routing state only. It means that the exact
named product surface is sufficiently identified for an independent reviewer to investigate its
current contract and rights. It does **not** mean:

- operational source, provider, or product selection;
- procurement approval, subscription, entitlement, account availability, or credential issuance;
- accepted delivery method, schema, historical coverage, quality, or availability;
- permission to access, download, retain, normalize, display, redistribute, or derive data;
- research-data eligibility, snapshot admission, performance evidence, promotion, risk clearance,
  execution eligibility, or order authority.

The artifact therefore keeps the global `source_selected`, `provider_selected`, and
`product_selected` authority fields false. It also keeps every rights, external access, data,
research, promotion, risk, execution, and order authority false.

## Frozen identities and exact registries

Use these canonical identities:

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

The exact ordered product registry is:

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
selection false, and entitlement, rights, and fitness states `UNPROVEN`. The CRSP U.S. Stock and CCM
delivery variants remain `UNPROVEN`; each other row binds only a
`DOCUMENTED_WEB_API_SURFACE`. A documented Web/API surface is not a verified available delivery or
an entitlement.

The exact six inherited Phase 16 candidate-group mappings are preserved. Each group has
`selection_state=NAMED_FOR_INDEPENDENT_RIGHTS_REVIEW`,
`selected_for_independent_rights_review=true`, and `single_operational_selection=false`. The
inherited code `HISTORICAL_LIQUIDITY_PRODUCT_UNSELECTED` remains the Phase 16 lineage key even though
Phase 17 maps it to the exact LSEG product for rights review; the inherited name is not a claim that
Phase 17 failed to produce its metadata output.

## Current official product inventory

The documentation facts below were reviewed on 2026-07-19 against official vendor, bank,
or regulator pages. They are frozen provenance for product identity only. Runtime generation and
verification do not browse or revalidate these links.

### Tiingo Phase 13 bounded candidate

The five fixed Phase 13 GET probes map to this exact documented product set:

- [Tiingo End-of-Day Stock Price API](https://www.tiingo.com/documentation/end-of-day)
- [Tiingo U.S. Fundamental Data API](https://www.tiingo.com/documentation/fundamentals)
- [Tiingo Stock, ETF, and Mutual Fund Dividend API](https://www.tiingo.com/documentation/corporate-actions/dividends)
- [Tiingo Stock, ETF, and Mutual Fund Split API](https://www.tiingo.com/documentation/corporate-actions/splits)

This set is selected only for independent rights review. A token is required; fundamentals is an
add-on subscription; and the detailed dividend and split surfaces are documented as beta/early-
release, entitlement-dependent products. Tiingo's
[Terms of Use](https://app.tiingo.com/tos/) describe API data as internal-consumption only, require an
organization to use a commercial plan, and require separate permission for redistribution. Those
public terms do not prove storage, non-display, derived-data, retention, revocation, account
entitlement, historical membership, delisting returns, stable-identity completeness, or full-history
fitness. Phase 13's `tiingo-candidate-qualification-products` is an internal placeholder, not a
vendor product id.

### Morningstar/CRSP US Stock Databases

The exact named product is
[CRSP US Stock Databases](https://indexes.morningstar.com/research-data-products/crsp-us-stock-databases).
The official page describes daily and monthly market data, corporate actions, active and inactive
securities, and PERMNO/PERMCO identifiers. It is selected only for independent rights review.

The page describes a subscription product delivered to licensees and does not identify a Fable5
entitlement, licensed SKU, delivery/format variant, storage or derived-data permission, exact fields,
full-history boundary, delisting-return semantics, point-in-time membership, or sector history.
Morningstar's
[June 30 migration notice](https://www.crsp.org/introducing-the-new-home-for-crsp-research-data-products/)
states that the research-data product names remain unchanged after migration to Morningstar. It is
not an entitlement or assurance that a delivery variant is currently available to Fable5.

### Morningstar/CRSP-Compustat Merged Database

The exact named product is the
[CRSP/Compustat Merged (CCM) Database](https://indexes.morningstar.com/research-data-products/crsp-compustat-merged-database).
It is selected only for independent rights review. The official page states that access depends on
both a CRSP US Stock subscription and a Compustat Xpressfeed license; CCM is not a stand-alone
fundamental-data entitlement.

No current entitlement, delivery variant, as-reported/revision completeness, filing-availability
timestamp semantics, permitted retention, non-display use, derived-data use, or revocation behavior
is proven.

### SEC EDGAR submissions and XBRL

The exact public surfaces selected only for independent rights and access-policy review are the
EDGAR Submissions API, the XBRL Companyfacts API, and their documented nightly bulk archives on the
[SEC EDGAR API page](https://www.sec.gov/search-filings/edgar-application-programming-interfaces).
The APIs require no API key. The SEC's
[developer resources](https://www.sec.gov/about/developer-resources) require efficient classified
automation and currently limit aggregate automated access to no more than ten requests per second.
The SEC's
[webmaster FAQ](https://www.sec.gov/about/webmaster-frequently-asked-questions) says government-
created and EDGAR public-filing content is free to access and reuse.

Those facts do not prove a normalized as-reported fundamentals dataset, stable issuer-to-security
reconciliation, amendment/revision completeness, taxonomy stability, exact history, data quality,
or Family A fitness.

### Federal Reserve FRED/ALFRED vintages

The exact documented identity selected only for independent rights review is the
[FRED API real-time and vintage web service](https://fred.stlouisfed.org/docs/api/fred/overview.html),
supported by its
[real-time-period model](https://fred.stlouisfed.org/docs/api/fred/realtime_period.html) and
[`fred/series/vintagedates`](https://fred.stlouisfed.org/docs/api/fred/series_vintagedates.html).
The official documentation does not define a separate ALFRED API product; ALFRED behavior is exposed
through FRED API real-time parameters. A registered API key is required.

The current [FRED terms](https://fred.stlouisfed.org/legal/terms/) state that API access does not
override third-party series owners' restrictions and prohibit use of the API to store, cache, or
archive FRED content or incorporate it into a database. Those terms are incompatible with the
planned canonical-snapshot persistence unless a later independent review establishes separate
written authority for the exact selected series and use. No regime-series set, full release-time
history, series-owner permission, or persistent-use right is proven.

### LSEG historical-liquidity candidate

The exact product/delivery identity selected only for independent rights review is
[LSEG Tick History — Instrument & Venue Access via Web/API](https://www.lseg.com/en/data-analytics/market-data/data-feeds/tick-history).
The official page describes trades, quotes, and market-depth data across more than 580 global venues,
Level 1 and Level 2 history reaching as far back as January 1996, raw and normalized formats, and
instrument-based or venue-by-day Web/API extracts.

Those public facts identify a plausible historical-liquidity product for review; they do not prove
the exact Fable5 instrument universe, venue set, field set, date range, delivery availability,
schema, symbology reconciliation, point-in-time completeness, data quality, account entitlement,
storage/non-display/derived-data/retention/redistribution rights, currentness, revocation behavior,
or Family A fitness. The product page invites a request for details, but Phase 17 does not contact
sales, submit a form, create an account, request an extract, or perform any provider call.

## Phase 16 step and gap preservation

Phase 17 binds the exact Phase 16 `SELECT_CANDIDATE_PRODUCTS` step identity and produces only its
required inventory hash. The bound Step 1 SHA-256 is
`b91451d90ea1ae672ccab878df742b91b62d1b33902f9be05a0b6e1395502ec1`. It does not alter the Phase
16 plan artifact. The remaining ordered steps
stay exactly:

```text
REVIEW_CURRENT_USE_RIGHTS                         NOT_STARTED
QUALIFY_BOUNDED_READ_ONLY_SAMPLES                 NOT_STARTED
PRODUCE_FULL_HISTORY_COVERAGE_MANIFEST            NOT_STARTED
RECONCILE_TEMPORAL_IDENTITY_REVISION_SEMANTICS    NOT_STARTED
DESIGN_LOCAL_QUARANTINE_AND_CANONICAL_SNAPSHOT    NOT_STARTED
REQUEST_SEPARATE_INGESTION_AUTHORITY              NOT_STARTED
```

All nineteen Phase 15 gap bindings carried by Phase 16 remain unchanged. In particular,
`FULL_POINT_IN_TIME_DATASET`, `SECTOR_LIQUIDITY_MACRO_HISTORY`,
`INDEPENDENT_CURRENT_USE_RIGHTS`, `DATA_RIGHTS_AND_RESEARCH_AUTHORITY`, and
`RIGHTS_CURRENTNESS_REVOCATION` remain missing or unproven as previously frozen. A product name,
official URL, review-selection marker, or valid hash cannot upgrade a gap.

## Portable artifact and authority boundary

The committed artifact is `docs/PHASE_17_FAMILY_A_CANDIDATE_PRODUCT_INVENTORY.json`. It contains
only accepted Phase 16 lineage, fixed product names, official documentation URLs, narrowly scoped
documented facts, candidate/review states, closed reasons, unchanged future-step and gap evidence,
false authority fields, and canonical hashes. It contains no credential, account, entitlement
document, contract body, vendor response, API payload, observation, dataset, schema sample, price,
return, performance metric, feature, label, signal, allocation, order, or fill.

Generation is stdout-only and deterministic. Verification reads one bounded regular canonical JSON
file. Both are database-free, network-disabled, subprocess-free, environment-independent, and
machine-portable. No runtime clock, random value, UUID4, Git discovery, filesystem discovery, local
path, environment value, or external response may affect the bytes.

Freeze false at minimum:

```text
source_selected
provider_selected
product_selected
credentials_loaded
rights_verified
rights_granted
external_request_performed
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

## Persistence, API, migration, and UI boundary

Phase 17 adds no migration, table, SQL function, trigger, database row, API route, Pydantic API model,
OpenAPI path, generated TypeScript contract, frontend product control, provider adapter, transport,
credential setting, vendor SDK, dependency, Compose service, scheduler, worker, queue, retry, or
asynchronous path. Alembic head remains `0011_phase14`; all 57 inherited tables/functions, every
earlier row, API/OpenAPI/generated-contract byte, and accepted production implementation remain
unchanged.

## Exact write allowlist

The complete Phase 17 implementation may write only these 37 paths:

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

No migration, API, generated contract, dependency, Compose file, accepted Phase 4-16 production
implementation, paper/research/risk service, frontend product code, or visual baseline is in scope.

## Failure and acceptance semantics

Fail closed on a changed Phase 16 identity; a missing, duplicate, reordered, substituted, or unknown
product/reference row; an unbound official URL; a changed current
fact; rights, entitlement, coverage, fitness, or authority inflation; a later step marked started;
non-canonical bytes; nondeterminism; network/database/subprocess use; secret or licensed-data
canaries; or any write outside the allowlist.

Acceptance requires deterministic generated-file parity, the exact `OUTPUT_FROZEN` Step 1 state,
`BLOCKED` artifact outcome, and inventory hash; adversarial tamper rejection; exact official-source
bindings; preserved delivery, coverage, fitness, and rights limitations; database/network denial;
zero writes; no migration/API/generated-contract drift;
inherited browser regressions at their stage-local migration heads, a clean committed identity,
complete cleanup, and Windows/Ubuntu acceptance at the same SHA/tree.

## Nearest separately authorized next step

Phase 18 is not implemented or authorized by this decision. If separately authorized after Phase 17
is formally accepted, its maximum safe objective is Phase 16 Step 2 only:
`REVIEW_CURRENT_USE_RIGHTS`. It must obtain independent, current, exact-product evidence for storage,
non-display, derived-data, retention, redistribution, revocation, delivery, and entitlement scope.
It may truthfully remain blocked, especially for FRED persistence and LSEG delivery/use rights.

Phase 18 must not load a credential, contact a provider API, request or inspect a sample, capture or
ingest data, create a snapshot, freeze an incomplete evaluation policy, open a holdout, run research,
compute performance, promote a strategy, mutate governance/risk, submit an order, or add a live path.

Stop after Phase 17 same-SHA Windows/Ubuntu acceptance. Do not begin Phase 18 without separate
authorization; do not open a PR, tag, publish, release, or deploy.
