# Phase 18 Family A current-use-rights review decisions

## Accepted baseline and authority

Phase 18 starts only from the formally accepted Phase 17 identity:

- Commit: `fd89d3905e9c2ea12223e30b5822a0fdda795a26`
- Tree: `f2eb791785dd10cc9316d174505b65eda919fe71`
- Phase 17 artifact id: `19d213d5-ec44-53fc-a146-f4f77a06102d`
- Phase 17 artifact SHA-256:
  `48584cf614c7713b05417a6d9333ca400f2d1c19fb0d3f047ced42e9ef4eb8f4`
- Phase 17 policy SHA-256:
  `0a36f01630a40c55d20139117641abcc8313e5f8b5a0be5fce15fd4c8ad2b3cf`
- Phase 17 inventory SHA-256:
  `070f36391093385ccd0e7feafc54d18c08e71cc8aa145bd30acea07abbffc76c`
- Windows full Phase 17 verifier passed with complete cleanup and a clean worktree/index.
- Ubuntu GitHub Actions run `29682173053`: `preflight`, `unit`, and `phase17-compose` passed at the
  same commit/tree.

The user separately authorized Phase 18. That authority is narrowed to Phase 16 Step 2,
`REVIEW_CURRENT_USE_RIGHTS`, over the exact nine Phase 17 metadata identities. It permits a frozen
technical review of official public terms and product documentation only. It does not authorize
legal advice, provider contact, procurement, contract acceptance, an account, a credential, a
provider request, external data, sampling, capture, database work, a research run, execution, an
order, or any live path.

## Decision and truthful outcome

Phase 18 produces one deterministic, portable, database-free, network-disabled public-metadata
review bundle. It freezes the official-source facts as reviewed at exactly
`2026-07-19T15:58:18.5305832Z`; ordinary generation and verification never fetch those sources.
Official public web documentation was accessed read-only during the architectural review. Those
review HTTP reads were not an operational provider, account, entitlement, or data request. Runtime
generation, verification, tests, and acceptance remain network-disabled. The snapshot is not
continuous authentication of remote pages, legal advice, or a current account-specific license
grant.

The overall outcome is exactly `BLOCKED_NO_OPERATIONAL_SELECTION`. Phase 16 Steps 1 and 2 are
`OUTPUT_FROZEN`; Steps 3-7 remain `NOT_STARTED`. This is the successful and truthful Phase 18
result because:

1. Tiingo public terms do not grant the persistent database and derivative-data rights required by
   the planned immutable research snapshot, and no Fable5 account terms or entitlement were
   reviewed;
2. Morningstar/CRSP and LSEG product rights depend on executed private licenses that are absent;
3. FRED's current public terms prohibit the planned non-display software/system/model use,
   persistent storage, and derivative use; and
4. SEC public reuse guidance supports reuse of the described public content, but does not prove
   exact content scope, normalized point-in-time coverage, identity reconciliation, schema quality,
   current policy compliance, or Family A fitness.

The SEC finding does not select SEC, EDGAR, a provider, a source, or a product. A public-rights
finding is one prerequisite finding only; operational selection and every later Phase 16 step remain
false or not started.

## Review vocabulary and currentness

Every product dimension uses only:

- `ALLOWED_PUBLIC`: the reviewed public official source supports the stated use for its described
  public content, subject to the cited policy and later revalidation;
- `CONDITIONAL_ACCOUNT_LICENSE`: use depends on account, plan, API-key, or standard-license
  conditions and no Fable5 entitlement is implied;
- `PRIVATE_LICENSE_REQUIRED`: the exact use must be established by an executed private product
  license or written permission;
- `PROHIBITED_PUBLIC_TERMS`: the reviewed current public terms expressly conflict with that use; or
- `UNPROVEN`: the sources reviewed do not establish a conclusion.

These labels are technical evidence classifications, not legal opinions. For private-license rows,
revocation/currentness remains `UNPROVEN`, no license or account entitlement is verified, and no
expiry or renewal is inferred. An entitlement dimension of `PRIVATE_LICENSE_REQUIRED` records a
requirement, not an obtained entitlement. The artifact freezes
the URL, official title, publisher, stated update date when present, clause locator, applicable
product codes, conservative fact, and review timestamp. It hashes that canonical metadata, not the
remote HTML or PDF body.

Before any separately authorized external action, a later phase must re-open the official pages,
compare current terms, and inspect the executed contract, order form, product schedule, and any
third-party rights for the exact legal entity, SKU, delivery, territory, intended use, storage,
non-display, derived-data, retention/deletion, redistribution, audit, termination, and revocation
scope. Any missing, changed, expired, or revoked term fails closed. SEC policy must be revalidated
immediately before any later SEC request.

## Frozen contract identities

Use exactly these schema, policy, hash-domain, and identity values; do not invent final artifact
hashes in documentation:

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

## Exact ordered product findings

The dimension order is storage; non-display/internal use; derived data; retention/deletion;
redistribution; revocation/currentness; delivery; entitlement.

| Product | Eight dimension states | Finding outcome |
|---|---|---|
| `TIINGO_END_OF_DAY` | `PROHIBITED_PUBLIC_TERMS`; `CONDITIONAL_ACCOUNT_LICENSE`; `PROHIBITED_PUBLIC_TERMS`; `UNPROVEN`; `PRIVATE_LICENSE_REQUIRED`; `CONDITIONAL_ACCOUNT_LICENSE`; `CONDITIONAL_ACCOUNT_LICENSE`; `UNPROVEN` | `BLOCKED_STANDARD_TERMS_DO_NOT_GRANT_PERSISTENT_DATABASE_RIGHTS` |
| `TIINGO_US_FUNDAMENTALS` | `PROHIBITED_PUBLIC_TERMS`; `CONDITIONAL_ACCOUNT_LICENSE`; `PROHIBITED_PUBLIC_TERMS`; `UNPROVEN`; `PRIVATE_LICENSE_REQUIRED`; `CONDITIONAL_ACCOUNT_LICENSE`; `CONDITIONAL_ACCOUNT_LICENSE`; `PRIVATE_LICENSE_REQUIRED` | `BLOCKED_ADDON_THIRD_PARTY_AND_PERSISTENCE_RIGHTS_UNPROVEN` |
| `TIINGO_DIVIDEND_CORPORATE_ACTIONS` | `PROHIBITED_PUBLIC_TERMS`; `CONDITIONAL_ACCOUNT_LICENSE`; `PROHIBITED_PUBLIC_TERMS`; `UNPROVEN`; `PRIVATE_LICENSE_REQUIRED`; `CONDITIONAL_ACCOUNT_LICENSE`; `CONDITIONAL_ACCOUNT_LICENSE`; `UNPROVEN` | `BLOCKED_ENTITLEMENT_CONFLICT_AND_PERSISTENCE_RIGHTS_UNPROVEN` |
| `TIINGO_SPLIT_CORPORATE_ACTIONS` | `PROHIBITED_PUBLIC_TERMS`; `CONDITIONAL_ACCOUNT_LICENSE`; `PROHIBITED_PUBLIC_TERMS`; `UNPROVEN`; `PRIVATE_LICENSE_REQUIRED`; `CONDITIONAL_ACCOUNT_LICENSE`; `CONDITIONAL_ACCOUNT_LICENSE`; `UNPROVEN` | `BLOCKED_ENTITLEMENT_CONFLICT_AND_PERSISTENCE_RIGHTS_UNPROVEN` |
| `MORNINGSTAR_CRSP_US_STOCK_DATABASES` | `PRIVATE_LICENSE_REQUIRED`; `PRIVATE_LICENSE_REQUIRED`; `PRIVATE_LICENSE_REQUIRED`; `UNPROVEN`; `PRIVATE_LICENSE_REQUIRED`; `UNPROVEN`; `CONDITIONAL_ACCOUNT_LICENSE`; `PRIVATE_LICENSE_REQUIRED` | `BLOCKED_PRODUCT_LICENSE_RIGHTS_UNAVAILABLE` |
| `MORNINGSTAR_CRSP_COMPUSTAT_MERGED` | `PRIVATE_LICENSE_REQUIRED`; `PRIVATE_LICENSE_REQUIRED`; `PRIVATE_LICENSE_REQUIRED`; `UNPROVEN`; `PRIVATE_LICENSE_REQUIRED`; `UNPROVEN`; `CONDITIONAL_ACCOUNT_LICENSE`; `PRIVATE_LICENSE_REQUIRED` | `BLOCKED_DUAL_PRODUCT_LICENSE_RIGHTS_UNAVAILABLE` |
| `SEC_EDGAR_SUBMISSIONS_AND_XBRL_DATA_APIS` | `ALLOWED_PUBLIC`; `ALLOWED_PUBLIC`; `ALLOWED_PUBLIC`; `ALLOWED_PUBLIC`; `ALLOWED_PUBLIC`; `UNPROVEN`; `ALLOWED_PUBLIC`; `ALLOWED_PUBLIC` | `RIGHTS_SUPPORTED_PUBLIC_POLICY_FITNESS_UNPROVEN` |
| `FRED_REALTIME_AND_VINTAGE_WEB_SERVICE` | `PROHIBITED_PUBLIC_TERMS`; `PROHIBITED_PUBLIC_TERMS`; `PROHIBITED_PUBLIC_TERMS`; `PROHIBITED_PUBLIC_TERMS`; `PROHIBITED_PUBLIC_TERMS`; `CONDITIONAL_ACCOUNT_LICENSE`; `CONDITIONAL_ACCOUNT_LICENSE`; `UNPROVEN` | `INELIGIBLE_CURRENT_TERMS_PROHIBIT_PERSISTENCE_AND_SOFTWARE_MODEL_USE` |
| `LSEG_TICK_HISTORY_INSTRUMENT_AND_VENUE_WEB_API` | `PRIVATE_LICENSE_REQUIRED`; `PRIVATE_LICENSE_REQUIRED`; `PRIVATE_LICENSE_REQUIRED`; `UNPROVEN`; `PRIVATE_LICENSE_REQUIRED`; `UNPROVEN`; `CONDITIONAL_ACCOUNT_LICENSE`; `PRIVATE_LICENSE_REQUIRED` | `BLOCKED_PRODUCT_VENUE_AND_NONDISPLAY_RIGHTS_UNAVAILABLE` |

For the four Tiingo rows, the reviewed standard terms permit only bounded personal/internal use under
applicable plan conditions, prohibit systematic retrieval to build a database and derivative works,
and reserve redistribution for separate permission. Fundamentals additionally depends on an add-on
and an unnamed third party. Dividend and split documentation contains conflicting beta/early-release
and EOD-entitlement language, so neither availability nor entitlement may be inferred.

Morningstar documents CRSP delivery tools, but a delivery description is not an entitlement. The CCM
product requires both a CRSP US Stock subscription and a separate Compustat Xpressfeed license. LSEG
documents Tick History Web/API capabilities, but public marketing and website terms grant no product,
venue/contributor, non-display, derived, storage, retention, or redistribution right.

For FRED, general prohibition (p) and API prohibition (k) expressly bar using FRED Services or API
content in connection with development or training of software systems or machine-learning models.
The planned Fable5 research use therefore makes `non_display_internal_use` exactly
`PROHIBITED_PUBLIC_TERMS`, independently of the storage, derivative, retention, redistribution,
third-party-series, and termination blockers.

The SEC rows remain subject to a declared descriptive User-Agent and company contact, efficient
access, download of only needed content, the current aggregate limit of no more than ten requests per
second, and current privacy/security/fair-access policy. Reuse must cite the SEC, must not use its
seals or logos, and must not imply SEC affiliation. Those requirements are future pre-request gates,
not Phase 18 transport authorization.

## Frozen official-source catalog

The following official first-party sources were reviewed. `UNSTATED` means the page exposed no
explicit source update date; it is not a guessed publication date.

| Code | Official title; publisher | URL | Stated date | Clause/section locator | Applies to |
|---|---|---|---|---|---|
| `TIINGO_TERMS_OF_USE` | Tiingo™ Terms of Use; Tiingo Inc. | https://app.tiingo.com/tos/ | `2026-02-18` | introductory change notice; sections 1, 1.4, 5.3, 7.3 | all four Tiingo rows |
| `TIINGO_GENERAL_API_DOCUMENTATION` | Stock Market Tools \| Tiingo; Tiingo Inc. | https://www.tiingo.com/documentation/general | `UNSTATED` | sections 1.1.2, 1.1.3, 1.1.4, 1.1.6 | all four Tiingo rows |
| `TIINGO_API_PRICING` | Tiingo API Pricing \| Tiingo; Tiingo Inc. | https://www.tiingo.com/about/pricing | `UNSTATED` | plans, commercial use, redistribution | all four Tiingo rows |
| `TIINGO_EOD_DOCUMENTATION` | End-of-Day (EOD) Stock Price API Documentation \| Tiingo; Tiingo Inc. | https://www.tiingo.com/documentation/end-of-day | `UNSTATED` | product overview and request/authentication documentation | `TIINGO_END_OF_DAY` |
| `TIINGO_FUNDAMENTALS_DOCUMENTATION` | U.S. Fundamental Data API Documentation \| Tiingo; Tiingo Inc. | https://www.tiingo.com/documentation/fundamentals | `UNSTATED` | overview, access/add-on, third-party disclosure | `TIINGO_US_FUNDAMENTALS` |
| `TIINGO_DIVIDEND_DOCUMENTATION` | Stock, ETF, and Mutual Fund Dividend API Documentation \| Tiingo; Tiingo Inc. | https://www.tiingo.com/documentation/corporate-actions/dividends | `UNSTATED` | overview and entitlement/release statements | dividend row |
| `TIINGO_SPLIT_DOCUMENTATION` | Stock, ETF, and Mutual Fund Split API Documentation \| Tiingo; Tiingo Inc. | https://www.tiingo.com/documentation/corporate-actions/splits | `UNSTATED` | overview and entitlement/release statements | split row |
| `MORNINGSTAR_WEBSITE_TERMS` | Legal Notices \| Morningstar (H1 Terms and Conditions); Morningstar | https://www.morningstar.com/company/terms-and-conditions | `UNSTATED` | website license/use and third-party-content provisions | both Morningstar rows |
| `MORNINGSTAR_CRSP_DATA_ACCESS` | Research Data Products \| Morningstar Indexes; Morningstar | https://indexes.morningstar.com/research-data-products | `UNSTATED` | Research Data Products; Data Access Options | both Morningstar rows |
| `MORNINGSTAR_CRSP_US_STOCK_PRODUCT` | CRSP US Stock Databases \| Morningstar Indexes; Morningstar | https://indexes.morningstar.com/research-data-products/crsp-us-stock-databases | `UNSTATED` | overview, coverage, identifiers, subscription access | CRSP US Stock row |
| `MORNINGSTAR_CCM_PRODUCT` | CRSP/Compustat Merged Database \| Morningstar Indexes; Morningstar | https://indexes.morningstar.com/research-data-products/crsp-compustat-merged-database | `UNSTATED` | overview and subscription requirements | CCM row |
| `SEC_PRIVACY_AND_DISSEMINATION` | SEC.gov \| Privacy Information; U.S. SEC | https://www.sec.gov/about/privacy-information | `2023-11-29` | Website Dissemination | SEC row |
| `SEC_WEBMASTER_REUSE_FAQ` | SEC.gov \| Webmaster Frequently Asked Questions; U.S. SEC | https://www.sec.gov/about/webmaster-frequently-asked-questions | `2024-08-23` | reuse of sec.gov and EDGAR content | SEC row |
| `SEC_EDGAR_APIS` | SEC.gov \| EDGAR Application Programming Interfaces (APIs); U.S. SEC | https://www.sec.gov/search-filings/edgar-application-programming-interfaces | `2025-04-08` | Submissions, Companyfacts, bulk archives | SEC row |
| `SEC_DEVELOPER_RESOURCES` | SEC.gov \| Developer Resources; U.S. SEC | https://www.sec.gov/about/developer-resources | `2025-03-10` | Fair Access; Internet Security Policy reference | SEC row |
| `SEC_ACCESSING_EDGAR` | SEC.gov \| Accessing EDGAR Data; U.S. SEC | https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data | `2024-06-26` | Fair access; declared request headers; Data APIs and bulk access | SEC row |
| `FRED_TERMS` | Legal Notices, Information and Disclaimers \| FRED \| St. Louis Fed; Federal Reserve Bank of St. Louis | https://fred.stlouisfed.org/legal/terms/ | `UNSTATED` | Property Rights and Licenses; general prohibitions (p)-(r); API prohibitions (k)-(m); termination | FRED row |
| `FRED_API_OVERVIEW` | St. Louis Fed Web Services: FRED® API Overview; Federal Reserve Bank of St. Louis | https://fred.stlouisfed.org/docs/api/fred/overview.html | `UNSTATED` | overview and API-key requirement | FRED row |
| `FRED_REALTIME_PERIODS` | St. Louis Fed Web Services: FRED® API Real-Time Periods; Federal Reserve Bank of St. Louis | https://fred.stlouisfed.org/docs/api/fred/realtime_period.html | `UNSTATED` | real-time period model | FRED row |
| `FRED_SERIES_VINTAGE_DATES` | St. Louis Fed Web Services: fred/series/vintagedates; Federal Reserve Bank of St. Louis | https://fred.stlouisfed.org/docs/api/fred/series_vintagedates.html | `UNSTATED` | endpoint parameters and vintage dates | FRED row |
| `LSEG_TICK_HISTORY` | Tick History Data \| Data Analytics; LSEG | https://www.lseg.com/en/data-analytics/market-data/data-feeds/tick-history | `UNSTATED` | overview, Instrument & Venue, Web/API, FAQs | LSEG row |
| `LSEG_DATA_REDISTRIBUTION` | Data Redistribution Solutions for Market Data \| Data Analytics; LSEG | https://www.lseg.com/en/data-analytics/market-data/data-redistribution | `UNSTATED` | redistribution and derived-data licensing | LSEG row |
| `LSEG_WEBSITE_TERMS` | Website Terms of Use \| LSEG; London Stock Exchange Group plc | https://www.lseg.com/en/policies/website-terms-of-use | `UNSTATED` | website license, personal/non-professional use, IP, changes | LSEG row |
| `LSEG_NONDISPLAY_DERIVED_GUIDANCE` | How to optimise financial data for AI; LSEG Academy | https://www.lseg.com/content/dam/lseg/learning-centre/documents/how-to-optimise-financial-data-for-ai-presentation-slides.pdf | `UNSTATED` | non-display, derived, redistribution/application-use licensing | LSEG row |

Freeze these conservative source facts exactly in substance:

- `TIINGO_TERMS_OF_USE`: standard terms limit use to personal/internal consumption, prohibit
  derivative works and systematic retrieval to build a database, and reserve redistribution for
  separate permission/fees; supplemental terms may control.
- `TIINGO_GENERAL_API_DOCUMENTATION`: documents token-based API use and plan/licensing distinctions,
  but is not a Fable5 entitlement or persistent-use grant.
- `TIINGO_API_PRICING`: describes public access tiers and separate redistribution licensing; it
  proves no current Fable5 plan or entitlement.
- `TIINGO_EOD_DOCUMENTATION`: identifies the EOD product/API surface but grants no Fable5
  persistence, derived-data, retention, or redistribution right.
- `TIINGO_FUNDAMENTALS_DOCUMENTATION`: describes an add-on coordinated with an unnamed third-party
  provider; its DOW30 evaluation is neither entitlement nor use-rights authority.
- `TIINGO_DIVIDEND_DOCUMENTATION`: identifies the dividend surface but contains ambiguous beta/
  early-release and EOD-entitlement statements; current availability and entitlement are unproven.
- `TIINGO_SPLIT_DOCUMENTATION`: identifies the split surface but contains ambiguous beta/early-
  release and EOD-entitlement statements; current availability and entitlement are unproven.
- `MORNINGSTAR_WEBSITE_TERMS`: general website terms are not a product-data license and establish no
  Fable5 research-product rights.
- `MORNINGSTAR_CRSP_DATA_ACCESS`: documents licensee delivery choices including Windows/Linux, flat
  files, CLI/libraries, Snowflake, WRDS, MOVEit, and CHASS; exact Fable5 delivery and entitlement are
  unproven.
- `MORNINGSTAR_CRSP_US_STOCK_PRODUCT`: identifies a subscription product with active/inactive
  securities and PERMNO/PERMCO, but publishes no Fable5 grant for the eight reviewed dimensions.
- `MORNINGSTAR_CCM_PRODUCT`: states that CCM requires both CRSP US Stock and a separate Compustat
  Xpressfeed license; neither license nor its rights scope was reviewed.
- `SEC_PRIVACY_AND_DISSEMINATION`: says SEC-created website information is public and may be copied/
  further distributed without permission; reuse should cite SEC and must not misuse seals/logos or
  imply affiliation.
- `SEC_WEBMASTER_REUSE_FAQ`: says Government-created sec.gov content and EDGAR public-filing content
  are free to access and reuse; this does not establish data fitness.
- `SEC_EDGAR_APIS`: documents no-key Submissions and Companyfacts JSON APIs plus nightly bulk
  archives; technical availability is not selection or point-in-time proof.
- `SEC_DEVELOPER_RESOURCES`: requires efficient, needed-only retrieval, current security/fair-access
  compliance, no unclassified bots, and no more than ten requests per second aggregate.
- `SEC_ACCESSING_EDGAR`: requires a declared User-Agent containing the company name and
  administrative contact, documents automated/API/bulk access methods, and requires rechecking
  current fair-access policy before later access.
- `FRED_TERMS`: prohibits use of FRED Services or API content in connection with development or
  training of software systems or machine-learning models, and prohibits API storage/cache/archive/
  database incorporation, derivative works, and redistribution; it requires destruction on
  termination, preserves third-party-series restrictions, and allows change/termination.
- `FRED_API_OVERVIEW`: documents the web service and registered API-key requirement but cannot
  override legal restrictions.
- `FRED_REALTIME_PERIODS`: documents real-time period semantics but grants no persistence or third-
  party-series rights.
- `FRED_SERIES_VINTAGE_DATES`: documents vintage-date retrieval but does not authorize an immutable
  canonical snapshot.
- `LSEG_TICK_HISTORY`: documents technical Tick History Web/API capabilities, but the exact product,
  venue/contributor, field, delivery, entitlement, and use scope require private agreement.
- `LSEG_DATA_REDISTRIBUTION`: states that redistribution and derived uses operate inside licensing
  frameworks; it grants no Fable5 right.
- `LSEG_WEBSITE_TERMS`: permits only narrow personal/non-professional website use and is not a Tick
  History product license.
- `LSEG_NONDISPLAY_DERIVED_GUIDANCE`: warns that non-display, derived, application, and redistribution
  uses may require additional licensing; executed contracts control and none was reviewed.

The artifact stores conservative paraphrases only. It stores no remote HTTP response body,
contract, license, provider message, or legal memorandum. Technical product/delivery documentation
cannot override applicable terms or executed agreements.

## Phase 16 step and gap preservation

Phase 18 binds the exact accepted Phase 17 inventory and Phase 16 Step 2 identity. The only new step
outputs are `independent_rights_review_sha256` and `rights_currentness_sha256`. Step 1 and Step 2 are
`OUTPUT_FROZEN`; the remaining order stays:

```text
QUALIFY_BOUNDED_READ_ONLY_SAMPLES                 NOT_STARTED
PRODUCE_FULL_HISTORY_COVERAGE_MANIFEST            NOT_STARTED
RECONCILE_TEMPORAL_IDENTITY_REVISION_SEMANTICS    NOT_STARTED
DESIGN_LOCAL_QUARANTINE_AND_CANONICAL_SNAPSHOT    NOT_STARTED
REQUEST_SEPARATE_INGESTION_AUTHORITY              NOT_STARTED
```

All nineteen Phase 15 gap bindings inherited through Phases 16 and 17 remain unchanged. In
particular, `INDEPENDENT_CURRENT_USE_RIGHTS` and `RIGHTS_CURRENTNESS_REVOCATION` cannot become passed:
the aggregate review is blocked and the snapshot is not continuously authenticated. SEC's row does
not satisfy coverage, schema, identity, quality, evaluation-policy, holdout, or ingestion gaps.

## Portable artifact and authority boundary

The committed artifact is
`docs/PHASE_18_FAMILY_A_CURRENT_USE_RIGHTS_REVIEW.json`. It contains accepted Phase 17 lineage, exact
public-source metadata, conservative rights classifications, blocked outcomes, unchanged future-step
evidence, transitive unchanged-gap lineage through the accepted Phase 17 artifact, false authority
fields, and canonical hashes only. It does not duplicate direct Phase 15 gap rows or a gap manifest.

Generation is stdout-only and deterministic. Verification reads one bounded regular UTF-8 canonical
JSON file. Both are database-free, network-disabled, subprocess-free, environment-independent, and
machine-portable. No runtime clock, random value, Git discovery, filesystem discovery, local path,
environment value, credential, provider response, or remote content may affect the bytes.

Freeze false at minimum: source/provider/product selection; credential loading; account,
subscription, entitlement, executed-license, counsel, currentness, rights, delivery, coverage,
schema, fitness, operational provider/account/data request, sample, capture, payload persistence,
ingestion, snapshot, evaluation-policy, holdout, research, performance, `PASS_RESEARCH`, promotion,
paper approval, risk clearance, execution, and order authority. Freeze `live_path_absent=true`,
`no_personalized_investment_advice=true`, and `no_real_performance_claimed=true`.

## Persistence, API, migration, and rollback

Phase 18 owns no persistence, API, schema, OpenAPI, generated TypeScript, dependency, Compose, or
frontend product surface. Retain migrations `0001` through `0011_phase14`, all 57 inherited
tables/functions, every prior row, and all generated-contract bytes. Add no `0012`, route, model,
database connection, table, function, trigger, scheduler, transport, or SDK.

Phase 18 adds no migration; Alembic head remains exactly `0011_phase14`.

The inherited nonempty `0010_phase13 -> 0011_phase14 -> 0010_phase13 -> 0011_phase14` cycle remains
the rollback proof. Phase 18 rollback deletes only its portable artifact/code/tests and its
wrapper/CI/documentation registrations. No data or schema rollback is possible or required.

## Acceptance and failure semantics

Phase 18 acceptance requires parser/wrapper support through 18 while rejecting 0, 19, and malformed
values with exit 2; exact allowlist enforcement; accepted Phase 17 ancestry; deterministic repeated
generator/committed-file parity; offline verification; exact product/source order, dimension states,
finding outcomes, and fixed timestamp; canonical hash preimage checks; Step 1/2 `OUTPUT_FROZEN` and
Steps 3-7 `NOT_STARTED`; all false authority fields; and the aggregate
`BLOCKED_NO_OPERATIONAL_SELECTION` result.

Tests must reject missing, duplicate, reordered, substituted, unknown, cross-row, stale-date,
applicability, URL, title, publisher, locator, fact, status, outcome, step, output, currentness,
authority, canonical-preimage, and hash tampering. They must reject rights inflation, operational
selection, completed later steps, remote-content embedding, credentials, licensed payloads, and any
network/database/subprocess/provider/research/broker dependency.

The direct Windows and Ubuntu `phase18-compose` gates must pass at one clean committed SHA/tree,
prove generator parity and adversarial verification, run inherited browser/accessibility/visual
regressions at their correct migration heads, demonstrate zero schema/row/API/generated-contract
drift, and fully clean containers, networks, volumes, processes, browser outputs, and temporary
files. Until both gates pass, Phase 18 is implemented but not formally accepted.

## Stop condition

Stop after Phase 18. Do not begin Phase 19, contact a provider or counsel, obtain or load a
credential, inspect an account, accept a contract, make a provider/data request, qualify a sample,
capture or persist non-synthetic data, ingest, freeze an incomplete evaluation policy, open a
holdout, run or promote research, modify governance/risk, submit or reconcile an order, add a live
capability, open a pull request, tag, publish, release, or deploy.
