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
SEC's [developer/fair-access guidance](https://www.sec.gov/about/developer-resources), including an
identifying User-Agent and no more than 10 requests per second. Persist accession and accepted time;
filing period-end is not availability.

### FRED and ALFRED

The [FRED API](https://fred.stlouisfed.org/docs/api/fred/) is authoritative for many macro series, but
today's historical values can include later revisions. Use
[real-time periods](https://fred.stlouisfed.org/docs/api/fred/realtime_period.html) and
[vintage dates](https://fred.stlouisfed.org/docs/api/fred/series_vintagedates.html) for point-in-time
research. An API key is required for Version 1, and the
[terms](https://fred.stlouisfed.org/docs/api/terms_of_use.html) note that third-party series can have
additional rights.

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
current terms restrict storage/cache/archive/database use and preserve third-party series owners'
rights. Each item therefore requires an independent exact-product current-use-rights and
currentness review. `selected_for_independent_rights_review` is not operational source, provider, or
product selection and authorizes no credential, provider request, sample, capture, ingestion,
snapshot, evaluation, holdout, research, performance, promotion, risk, execution, or order.

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
