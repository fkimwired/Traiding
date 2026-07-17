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
