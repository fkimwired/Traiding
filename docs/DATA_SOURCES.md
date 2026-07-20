# Data-source and adapter policy

**Landscape reviewed:** 2026-07-17
**Readiness posture:** No commercial entitlement or credential is proven by repository tests. Vendor names
below are candidates to evaluate, not configured dependencies or endorsements.

## Non-negotiable adapter boundary

Every source is accessed through a typed, domain-level interface with a deterministic mock. No
strategy imports a vendor SDK. Credentials come only from environment/secret storage, never code,
fixtures, logs, or frontend bundles. Missing credentials produce a clear unavailable state; the system
does not substitute fabricated values.

Each adapter response includes:

```text
provider_id + adapter_version
dataset/product id + schema version
entitlement/use-rights id
source record/document id
event_time
available_at
retrieved_at
revision/vintage id
data snapshot id + content hash
timezone/calendar/units
quality flags and missingness reason
```

Backtests require the historical availability and revision semantics, not merely current values.
Raw immutable payloads and normalized point-in-time tables remain separate.

## Capability matrix

| Need | Candidates to evaluate | Mandatory diligence before use |
|---|---|---|
| OHLCV + corporate actions | Massive (formerly Polygon.io), Tiingo, EODHD, Twelve Data, Alpha Vantage | adjustment convention; raw/action history; delisted/inactive coverage; timestamps; exchange coverage; storage/non-display rights |
| Point-in-time fundamentals | Tiingo, FMP, EODHD, Intrinio; CRSP/Morningstar as institutional reference tier | as-reported vs restated; accepted/release time; revision history; stable identifiers; delistings; field definitions; historical depth |
| SEC filings | SEC EDGAR submissions/XBRL APIs and document archives | identifying User-Agent; fair-access rate; accession/accepted timestamp; amendments; filing/document hash |
| Macro | FRED for current access; ALFRED/vintages and release semantics for historical research | vintage/revision handling; release time; API key; third-party series rights |
| News + event text | Finnhub, Alpha Vantage, EODHD, or another licensed feed | publication/correction time; syndication dedupe; entity linking; history; display/storage/redistribution rights |
| Earnings transcripts | FMP, Intrinio, or another entitled source | full-text entitlement (not only metadata/URL); correction time; display/storage rights; speaker/entity quality |
| Options analytics (deferred) | Massive, Intrinio, or another OPRA-entitled source | OPRA delay/fees; quote/trade history; symbology; IV/greek methodology; redistribution/non-display rights |
| Paper simulation (later) | Alpaca-shaped paper-only adapter | paper domain allowlist; paper credentials; market-data feed entitlement; simulator omissions; local cost/risk model |

Provider selection must be capability- and entitlement-tested on a small representative sample. Do
not choose by marketing-page breadth or a subjective “best/deepest/generous” claim.

## Current facts and cautions

### Massive / Polygon.io

Polygon.io renamed to Massive; the official
[changelog dates the rename](https://www.massive.com/changelog). Preserve legacy naming only as an
adapter alias and never leak vendor-specific names into strategy logic. Options availability does not
imply that OPRA delay, licensing, history, or redistribution is included in every plan.

### IEX Cloud and viaNexus

IEX Cloud ended on 2024-08-30. Blue-Sky acquired assets and technology, and its current successor
product is [viaNexus](https://www.blueskyapi.com/) with separate
[current documentation](https://console.blueskyapi.com/docs). Do not write “migrated to Bluesky API”
as though accounts, entitlements, schemas, or integrations transferred automatically. IEX Cloud is not
a new integration candidate.

### SEC EDGAR

Official [`data.sec.gov` APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
cover submissions and XBRL JSON without an API key. EDGAR
[full-text search](https://www.sec.gov/edgar/search/index.html) is a separate interface. Follow the
SEC's [developer/fair-access guidance](https://www.sec.gov/about/developer-resources) and
[Accessing EDGAR Data](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data).
The latter requires a declared User-Agent with company name and administrative contact; current
fair-access guidance limits aggregate access to no more than 10 requests per second. Persist
accession and accepted time; filing period-end is not availability.

### FRED and ALFRED

The [FRED API](https://fred.stlouisfed.org/docs/api/fred/) is authoritative for many macro series, but
today's historical values can include later revisions. Use
[real-time periods](https://fred.stlouisfed.org/docs/api/fred/realtime_period.html) and
[vintage dates](https://fred.stlouisfed.org/docs/api/fred/series_vintagedates.html) for point-in-time
research. An API key is required for Version 1, and the
[terms](https://fred.stlouisfed.org/legal/terms/) note that third-party series can have
additional rights. Current general prohibition (p) and API prohibition (k) also prohibit using FRED
Services or API content in connection with development or training of software systems or machine-
learning models; separate provisions prohibit the planned persistent database use.

### Alpaca paper simulation

Alpaca paper uses both separate credentials and the paper endpoint; see
[authentication](https://docs.alpaca.markets/us/v1.1/docs/authentication-1) and
[paper-trading documentation](https://docs.alpaca.markets/us/docs/paper-trading). Paper-only accounts
may receive IEX rather than consolidated SIP market data. The simulator does not model all market
impact, information leakage, latency/queue state, price improvement, regulatory fees, dividends, or
borrow fees. It therefore cannot supply the platform's cost-realism gate; local evaluation and risk
models remain authoritative. Phase 12 adds one fixed read-only paper/data adapter for six readiness
GETs. It freezes `AAPL` and `feed=iex` as connectivity probes, stores only sanitized status/count/hash
evidence, and has no order or generic request method. Mock/fake-transport tests do not prove a real
entitlement or external `SHADOW_READY`; that probe requires separate authorization.

### Point-in-time reference data

CRSP is a reference tier for inactive securities, identifier histories, delistings, and research-grade
returns. Morningstar completed its CRSP acquisition in February 2026 and announced the
[research-data product migration](https://www.crsp.org/introducing-the-new-home-for-crsp-research-data-products/)
in June 2026; procurement and delivery assumptions must be revalidated. Tiingo's
[fundamentals documentation](https://www.tiingo.com/documentation/fundamentals) advertises
`asReported`, release dates, delisted instruments, and stable identifiers, making it a candidate for a
capability test—not proof that every field has complete point-in-time coverage.

### Phase 13 qualification boundary

Phase 13 freezes Tiingo as one qualification candidate, not an approved research provider. Its fixed
sample plan uses header-only token authentication and bounded GETs against the documented EOD,
fundamentals, distribution, and split surfaces. No URL, symbol, date, dataset, entitlement, or
capability is supplied by the operator. Provider bodies are validated transiently, reduced to
sanitized counts/ranges/hashes/findings, and discarded rather than stored or returned.

The candidate is blocked unless independently reviewed current evidence proves storage,
non-display, and derived-data rights. Tiingo's documented stable identity, active/delisted metadata,
raw/adjusted EOD fields, release dates, and as-reported values are candidate capabilities only.
Official documentation does not by itself prove historical universe reconstruction, delisting-return
semantics, full revision coverage, account entitlement, or Fable5's permitted use. Missing or
unproven capabilities remain explicit `BLOCKED`/`UNCOMPUTABLE` checks; current membership can never
substitute for historical membership.

Deterministic mock acceptance proves the local contract only and always leaves research-data
eligibility, strategy promotion, execution, and order authority false. A separately authorized real
sample could at most prove `EXTERNAL_SAMPLE_QUALIFIED`; it would remain qualification evidence, not a
Phase 4 snapshot or performance result.

### Phase 14 offline eligibility boundary

Phase 14 performs no provider call and does not onboard data. It evaluates only immutable sanitized
Phase 13 qualification evidence under a frozen local policy. It projects capability identities,
statuses, ranges/counts, and hashes without copying a provider body or observation value.

The Phase 14 vocabulary contains no positive research-eligibility result. A mock can prove only the
local contract, and an external sample remains blocked because sample qualification is not a complete
licensed Family A dataset or independently authenticated ingestion authority. Real point-in-time
onboarding, macro-regime inputs, sector/liquidity depth, non-synthetic evaluation policy, and current
human authority require a later separately authorized phase.

### Phase 15 portable admission-specification boundary

Phase 15 freezes a provider-neutral, metadata-only description of the data, temporal, quality,
licensing, retention, and evaluation evidence a future non-synthetic Family A onboarding phase would
need. It performs no provider request, loads no credential, accepts no data location, reads no
licensed observation, creates no Phase 4 snapshot, and approves no provider or entitlement. The
committed artifact is a deterministic engineering requirements package, not a data package.

Its current gap ledger preserves the full point-in-time dataset, external qualification, historical
membership and delisting coverage, sector/liquidity/macro history, independent current use rights,
non-synthetic persistence, and non-synthetic evaluation paths as `MISSING` or `UNPROVEN` where the
repository has no authoritative evidence. Synthetic Phase 4-6 proofs remain `MOCK_ONLY` and may not
be relabeled. `REQUIREMENTS_FROZEN` means only that this distinction is complete and hash-bound; it
does not authorize capture, ingestion, storage, research use, display, derived-data use, or
redistribution.

Any later onboarding phase must separately name and verify the provider product, schemas, complete
coverage, independently reviewed rights and retention terms, currentness/revocation evidence, and
quarantine/normalization behavior. Provider documentation, a token, a Phase 13 sample hash, or a
Phase 15 requirement hash is insufficient on its own.

### Phase 16 portable point-in-time source-plan boundary

Phase 16 freezes the order and evidence outputs for future Family A source selection without
performing any of those steps. Its exact candidates are the existing bounded Phase 13 Tiingo
candidate, Morningstar/CRSP US Stock Databases, Morningstar/CRSP Compustat Merged Database, SEC EDGAR
submissions/XBRL, Federal Reserve ALFRED vintages, and one explicitly unselected historical-liquidity
product slot. Candidate order is not a ranking or recommendation.

Morningstar's CRSP acquisition and research-product migration, SEC EDGAR's submissions/XBRL
surfaces, and Federal Reserve real-time/vintage documentation are official candidate facts only.
They do not prove current product availability, schemas, complete point-in-time coverage, account
entitlement, storage/non-display/derived-data rights, retention, redistribution, or fitness for
Family A. The five named candidate rows remain `UNPROVEN`; the liquidity-product row remains
`MISSING`. Every row is unselected and rights-unverified.

`PLAN_FROZEN` means only that the exact requirements, seven capabilities, six candidate rows, seven
future steps, and unchanged Phase 15 gaps reproduce. Phase 16 performs no provider request, loads no
credential, accepts no data path, reads no observation, and creates no qualification, coverage
manifest, quarantine, snapshot, evaluation policy, holdout, or research artifact. Future product
selection, rights review, bounded qualification, and data admission each require separate authority.

### Phase 17 portable candidate-product inventory boundary

Phase 17 attempts only Phase 16 Step 1 and freezes one deterministic metadata inventory with
`candidate_product_inventory_sha256`. Its Step 1 output is `OUTPUT_FROZEN`, while the artifact
remains `BLOCKED` because the exact delivery, entitlement, independently reviewed current rights,
complete coverage, schemas, quality, and Family A fitness are not proven.

The exact identities selected only for independent rights review are Tiingo End-of-Day,
Fundamentals, Dividend, and Split APIs; Morningstar CRSP US Stock Databases; Morningstar
CRSP/Compustat Merged Database; SEC EDGAR Submissions/XBRL and bulk surfaces; Federal Reserve FRED
real-time/vintage surfaces; and
[LSEG Tick History — Instrument & Venue Access via Web/API](https://www.lseg.com/en/data-analytics/market-data/data-feeds/tick-history).
LSEG's official page describes 580+ venues and contributors, Level 1/2 history reaching as far back
as January 1996, and instrument or venue-by-day extracts. Those public descriptions identify a
review candidate only; they do not prove the Fable5 instrument/venue/field/date scope, delivery
availability, schema, entitlement, use rights, quality, or point-in-time fitness.

Tiingo's public terms remain internal-use/plan dependent; CCM depends on both CRSP US Stock and
Compustat Xpressfeed licenses; SEC access remains subject to current fair-access policy; and FRED's
current terms prohibit the planned software/system/model use, restrict storage/cache/archive/
database use, and preserve third-party series owners' rights. Each item therefore requires an
independent exact-product current-use-rights and
currentness review. `selected_for_independent_rights_review` is not operational source, provider, or
product selection and authorizes no credential, provider request, sample, capture, ingestion,
snapshot, evaluation, holdout, research, performance, promotion, risk, execution, or order.

### Phase 18 portable current-use-rights review boundary

Phase 18 performs the technical public-metadata review for Phase 16 Step 2 only. Official first-party
web pages were accessed read-only and their exact URLs, titles, publishers, stated update dates,
clause locators, applicable product codes, and conservative facts were frozen at
`2026-07-19T15:58:18.5305832Z`. Runtime generation, verification, tests, and CI do not browse, and the
artifact stores no remote HTTP response body, contract, license, entitlement, provider response, or
data.

The aggregate is `BLOCKED_NO_OPERATIONAL_SELECTION`. Tiingo standard terms prohibit the persistent
database and derivative-work use required by the planned snapshot and leave account-specific terms
unverified. Morningstar CRSP and LSEG uses require private product licenses that have not been
reviewed. FRED public terms prohibit the planned non-display software/system/model use, storage,
retention, and derivative use. SEC
public guidance supports reuse of the described public content, but that single rights finding does
not prove normalized point-in-time coverage, identity/schema/quality fitness, current access-policy
compliance, or operational selection.

Each product freezes eight dimensions using only `ALLOWED_PUBLIC`,
`CONDITIONAL_ACCOUNT_LICENSE`, `PRIVATE_LICENSE_REQUIRED`, `PROHIBITED_PUBLIC_TERMS`, or
`UNPROVEN`: storage, non-display/internal use, derived data, retention/deletion, redistribution,
revocation/currentness, delivery, and entitlement. These are technical evidence states, not legal
opinions or grants. Every source requires later revalidation; any exact executed license must bind
the Fable5 legal entity, SKU, delivery, territory, intended use, third-party rights, persistence,
non-display, derived, retention/deletion, redistribution, audit, termination, and revocation scope.

Phase 16 Steps 1/2 are `OUTPUT_FROZEN`; Steps 3-7 remain `NOT_STARTED`. Phase 18 performs no
operational provider/account/data request, credential loading, sample qualification, data capture,
database write, ingestion, snapshot, evaluation, holdout, research, promotion, risk, execution, or
order operation. All nineteen inherited Phase 15 gaps remain unchanged.

### Phase 19 portable Step 3 prerequisite-assessment boundary

Phase 19 performs no source-plan step and makes no provider, source, or product choice. It binds the
accepted Phase 18 blocked result and assesses only the two required prior-evidence names for Phase 16
Step 3. Both remain missing:

```text
non_synthetic_evaluation_policy_sha256
confirmation_holdout_definition_sha256
```

The artifact never supplies a value for either name. Candidate metadata, public-terms findings,
requirements hashes, synthetic policy hashes, and assessment hashes cannot substitute for the
missing evidence. Because there is still no operational selection, current executed-rights proof,
exact schema, full history/calendar coverage, or market calibration, Phase 19 cannot freeze a
complete data-specific policy. Because there is no approved exact interval/calendar, it cannot
define or open a non-synthetic confirmation holdout.

Steps 1/2 remain `OUTPUT_FROZEN`; Steps 3-7 remain `NOT_STARTED`; all nineteen Phase 15 gap states
remain unchanged. Phase 19 performs no provider/account/data request, credential loading, sample
qualification, capture, persistence, database write, ingestion, snapshot, policy approval, holdout
access, research, performance, promotion, risk, execution, or order operation.

### Phase 20 portable evaluation/holdout input-register boundary

Phase 20 records only the exact names and current evidence classes of twenty inputs needed before a
complete non-synthetic policy and unopened holdout could be frozen. The four upstream-context rows
remain `MISSING` or `UNPROVEN`: operational source/product composition, current executed rights and
revocation evidence, exact delivery/schema versions, and a declared point-in-time coverage/calendar/
availability/missingness contract. Phase 20 chooses no candidate, provider, product, delivery,
schema, instrument scope, history range, calendar, availability rule, or missingness value.

The input register is not a provider qualification or data manifest. A future field name such as a
schema version, source binding, history boundary, or calibration vintage contains no value and proves
no availability, entitlement, coverage, quality, or fitness. The accepted Phase 17 product inventory,
Phase 18 public-terms findings, Phase 19 assessment, and Phase 20 row/manifest hashes cannot substitute
for current account-specific rights, exact schemas, or data-specific evidence.

The result remains `BLOCKED_MISSING_OPERATIONAL_AND_DATA_SPECIFIC_INPUTS`. Both reserved Step 3
evidence hashes remain missing without values, Steps 1/2 remain `OUTPUT_FROZEN`, Steps 3-7 remain
`NOT_STARTED`, and all nineteen Phase 15 gaps remain unchanged. Phase 20 performs no browsing,
provider/account request, credential loading, sample qualification, data capture, payload or database
persistence, ingestion, snapshot creation, policy/holdout creation, research, risk, execution, or
order operation.

### Phase 21 portable operational-composition decision-requirements boundary

Phase 21 joins only committed Phase 17 candidate claims, Phase 18 fixed-time public-rights findings,
and the Phase 20 operational-composition field-name requirement. It binds six candidate groups and
nine products without ranking, recommending, defaulting, or selecting any of them. All seven Phase 16
capabilities remain `UNASSIGNED`, and all eight composition decision fields remain required but
absent (`value_present=false`, `evidence_produced=false`).

Every product binding remains `operationally_selected=false` and
`current_rights_verified=false`. Phase 21 derives no product-eligibility state or count. These fields
do not assert that a product is commercially unavailable, make a legal conclusion, or permanently
exclude it. The SEC public-use finding still lacks complete schema, coverage, fitness, currentness,
and operational-selection evidence. The fixed-time FRED finding and every other public-rights
classification require fresh review before any later action.

The exact result is `BLOCKED` / `DECISION_REQUIREMENTS_FROZEN` /
`BLOCKED_AWAITING_EXPLICIT_OPERATIONAL_SOURCE_PRODUCT_COMPOSITION`. Current rights, exact delivery
and schema, and the complete coverage/calendar contract remain blocked downstream dependencies. A
Phase 21 artifact, commit, PR, tag, release, publication, or isolated deployment cannot substitute
for a human decision or current account-specific evidence. Phase 21 performs no browsing,
provider/counsel contact, credential/account access, sample request, capture, persistence, ingestion,
snapshot, policy/holdout construction, Step 3 action, research, risk, execution, or order operation.

## Data-quality acceptance before provider approval

For a representative universe including ticker changes, mergers, delistings, late filings, amendments,
and corporate actions, an adapter must demonstrate:

1. stable identity and point-in-time membership reconstruction;
2. explicit event/availability/retrieval time and timezone;
3. revision/vintage replay without overwriting history;
4. delisting and corporate-action reconciliation against a trusted reference;
5. documented null/sentinel behavior and no silent zero fill;
6. raw-to-normalized counts, join coverage, duplicate-grain checks, and schema-drift behavior;
7. deterministic snapshot ids and repeatable mock fixtures;
8. documented display, storage, non-display, derived-data, and redistribution rights.

An adapter that supplies current dashboards but cannot reconstruct what was knowable historically is
not approved for strategy validation.
