# Phase 28 Alpaca IEX observation-only candidate-screen pilot decisions

## Decision, baseline, and current disposition

Phase 28 is a CLI-only, observation-only pilot for deterministic candidate-screen responses from a
fixed Alpaca IEX market-data surface. It is anchored at the accepted T-010 commit
`e9f4d99d8c1bc5c5b4ac615cf3592d5f0ae3113e` and supersedes the previously reserved Phase 28
Family A acquisition/schema boundary. It does not change or satisfy the Phase 26 selected
CRSP/SEC/RTDSM composition.

No credentialed external observation is authorized or performed by this implementation task. The
truthful current external disposition is:

```text
outcome:       BLOCKED
determination: EXTERNAL_OBSERVATION_REQUIRES_SEPARATE_AUTHORIZATION
```

The deterministic mock is local contract proof only. A later separately authorized external run
may produce sanitized historical observation evidence, but neither a mock nor an external result
is research-qualified data, a strategy signal, an order instruction, execution authority, or
investment advice.

The accepted identities remain unchanged:

```text
Phase 12 commit: 37530a94f841d538a162447cb01ec3e11f375ead
Phase 27 commit: b887ed4c0a7552a784c4aeaf433aa4fb3e5569a4
Phase 27 tree:   4dd37c02cdfb76ccb69564031656c7131a0de2b9
T-009 commit:    1d8aa00f80fdd60b2b5ab3d431448de28a872c17
T-007 commit:    4180ce659aa621d6155cac1118f7011deb92aa9f
T-010 commit:    e9f4d99d8c1bc5c5b4ac615cf3592d5f0ae3113e
```

Phase 27 remains exactly `BLOCKED / COMPOSITION_RIGHTS_ENTITLEMENT_EVIDENCE_MISSING /
verified_evidence_recorded=false`. Phase 28 creates no evidence for that intake and cannot advance
Phase 27 or any Family A acquisition, schema, point-in-time, or research gate.

## Fixed observation surface

The pilot has no configurable universe, provider, host, path, feed, currency, timeframe, or request
method. Its universe is exactly, and in canonical order:

```text
AAPL
MSFT
SPY
```

The feed is exactly `iex` and the currency is exactly `USD`. The adapter permits the following six
requests, in this exact order, and no others:

| # | Method | Exact host | Exact target |
|---:|---|---|---|
| 1 | `GET` | `paper-api.alpaca.markets` | `/v2/assets/AAPL` |
| 2 | `GET` | `paper-api.alpaca.markets` | `/v2/assets/MSFT` |
| 3 | `GET` | `paper-api.alpaca.markets` | `/v2/assets/SPY` |
| 4 | `GET` | `data.alpaca.markets` | `/v2/stocks/bars/latest?symbols=AAPL%2CMSFT%2CSPY&feed=iex&currency=USD` |
| 5 | `GET` | `data.alpaca.markets` | `/v2/stocks/quotes/latest?symbols=AAPL%2CMSFT%2CSPY&feed=iex&currency=USD` |
| 6 | `GET` | `data.alpaca.markets` | `/v2/stocks/snapshots?symbols=AAPL%2CMSFT%2CSPY&feed=iex&currency=USD` |

The transport uses TLS with hostname and certificate verification, follows no redirect, sends no
request body, has no generic request method, and performs no retry, polling, websocket, scheduler,
or background refresh. It accepts only the fixed paper/data hosts and rejects userinfo, alternate
ports, alternate schemes, trailing-dot hosts, IP literals, and any order or account mutation
surface.

The CLI has only two explicit modes:

- deterministic mock, which performs zero network calls and cannot claim external observation; and
- separately authorized credentialed observation, which requires an explicit paper-only
  confirmation, the exact-use confirmation for the 2026-07-24 review, and both paper credential
  environment variables before the first transport call.

The credential names remain `FABLE5_ALPACA_PAPER_API_KEY_ID` and
`FABLE5_ALPACA_PAPER_SECRET_KEY`. Values are secret-typed, never accepted as command-line
arguments, and never included in reprs, errors, stdout, stderr, hashes, files, or evidence.

## IEX and authority labels

Every human-readable and machine-readable result must communicate all of the following:

> IEX is a partial-market feed and does not represent the consolidated U.S. market. This
> observation is for paper-only testing, is not research-qualified, is not a trade signal, and is
> not investment advice.

The pilot is not a replacement for SIP or another consolidated feed. A `MATCH` result means only
that the fixed, non-actionable observation predicates matched on this partial-market sample. It
does not mean buy, sell, long, short, enter, exit, hold, rank, allocate, size, promote, approve,
execute, or submit.

## Deterministic predicates and closed outcomes

The predicate registry is fixed in code and hash-bound. It may inspect raw response values only in
memory to classify each symbol. The screen emits only the closed symbol outcome vocabulary:

```text
MATCH
NO_MATCH
INSUFFICIENT_DATA
```

The required predicates and canonical order are:

1. `ASSET_ACTIVE`: the symbol's current asset record is present, active, and exactly
   matches the fixed universe member;
2. `ASSET_TRADABLE`: the current asset record reports the symbol as tradable;
3. `LATEST_BAR_VALID_AND_FRESH`: the latest IEX/USD bar is structurally valid, time-consistent,
   and no older than the fixed 120-second freshness allowance;
4. `LATEST_QUOTE_VALID_AND_FRESH`: the latest IEX/USD quote is structurally valid, non-crossed,
   time-consistent, and no older than the fixed 120-second freshness allowance;
5. `SNAPSHOT_COMPLETE_AND_FRESH`: the IEX/USD snapshot contains the required latest trade, latest
   quote, minute bar, daily bar, and previous daily bar components; its quote and minute bar are no
   older than 120 seconds;
6. `CROSS_ENDPOINT_COHERENT`: the independently returned latest bar and snapshot `minuteBar`
   timestamps differ by no more than the fixed 60-second bucket-rollover tolerance, and the latest
   quote and snapshot `latestQuote` timestamps differ by no more than the fixed 30-second
   tolerance; bar and quote timestamps are never compared to each other;
7. `SESSION_DIRECTION_POSITIVE`: the snapshot daily close is greater than the previous daily
   close; and
8. `INTRADAY_DIRECTION_POSITIVE`: the snapshot minute close is greater than the daily open.

If any required field is missing, malformed, stale, scope-mismatched, duplicate, non-finite,
oversized, or otherwise uncomputable, the symbol is `INSUFFICIENT_DATA`. If all required data is
computable and every boolean predicate matches, the symbol is `MATCH`; otherwise it is
`NO_MATCH`. The evidence fixes `forecast_horizon=NONE_OBSERVATION_ONLY`; there is no tie-breaking,
ranking, scoring, forecast, position size, or execution mapping. The same validated input and
receipt timestamp must produce byte-identical classifications and evidence hashes.

Transport, schema, entitlement, authentication, or whole-response failure fails the complete run
closed. It does not silently turn unavailable symbols into `NO_MATCH`, retry, substitute a feed,
drop a symbol, or emit partial authority.

## Transient data and sanitized evidence

Raw response bodies, headers, prices, sizes, conditions, exchange codes, account data, asset IDs,
and provider timestamps are validated transiently and then discarded. They must not enter Git, a
database, cache, log, exception, fixture captured from the provider, report, or evidence artifact.
Phase 28 adds no migration, database table, API route, frontend component, generated contract, or
provider SDK dependency.

The sanitized JSON evidence contains only bounded classifications and audit metadata:

- evidence ID and evidence SHA-256;
- observation-snapshot ID, SHA-256, and kind
  `SANITIZED_OBSERVATION_METADATA_ONLY`;
- source kind and whether an external request was performed;
- fixed configuration, universe, predicate-registry, and transport-profile hashes, with the exact
  request manifest included in the transport profile and the exact-use review/deadline bound into
  the configuration hash;
- fixed feed/currency labels and the partial-market/paper-only/no-advice notice;
- `exact_use_review_confirmed_for_external_run` and the fixed
  `exact_use_review_revalidation_deadline_utc`;
- per-symbol `MATCH`, `NO_MATCH`, or `INSUFFICIENT_DATA` plus closed reason/predicate statuses;
- per-request endpoint hash, status, inspection timestamps, HTTP status, request-ID SHA-256,
  response SHA-256, sanitized-observation SHA-256, and inspection SHA-256, never the request ID,
  body, or value;
- code-version Git SHA, one observation UTC timestamp, and per-inspection UTC timestamps;
- random seed and trial count `0/0`; and
- explicit false authority and persistence fields.

The evidence must state at least:

```text
provider_payload_persisted=false
raw_price_persisted=false
research_qualified=false
strategy_execution_eligible=false
order_submission_authorized=false
live_path_absent=true
simulated_paper_only=true
no_personalized_investment_advice=true
no_real_performance_claimed=true
```

This evidence is an historical observation receipt. The `observation_snapshot_*` fields identify
only the sanitized inspection metadata; they are not a provider-data or research snapshot. The
receipt does not self-revalidate, become a point-in-time dataset, supply a backtest input, prove
performance, or establish current provider readiness after completion.

## First-party exact-use review

The exact-use review was performed on 2026-07-24 from current first-party Alpaca documentation and
disclosures only. No login, credential, data endpoint, provider contact, account inspection, terms
acceptance, or data retrieval occurred. The pilot's fail-closed internal revalidation deadline is
`2026-08-01T00:00:00Z`; this is a conservative engineering control, not a provider-stated expiry
or rights term.

| Scope | First-party source |
|---|---|
| Asset-by-symbol GET | [Alpaca asset reference](https://docs.alpaca.markets/us/reference/get-v2-assets-symbol_or_asset_id) |
| Latest multi-symbol bars GET | [Alpaca latest-bars reference](https://docs.alpaca.markets/us/v1.1/reference/stocklatestbars-1) |
| Latest multi-symbol quotes GET | [Alpaca latest-quotes reference](https://docs.alpaca.markets/us/reference/stocklatestquotes-1) |
| Multi-symbol snapshots GET | [Alpaca snapshots reference](https://docs.alpaca.markets/us/reference/stocksnapshots-1) |
| IEX feed scope and market-data plans | [Alpaca Market Data FAQ](https://docs.alpaca.markets/us/docs/market-data-faq) |
| Personal/non-commercial service terms and availability limitations | [Alpaca Terms and Conditions](https://files.alpaca.markets/disclosures/library/TermsAndConditions.pdf) |
| Market-data proprietary-interest and reproduction/distribution restrictions | [Alpaca customer agreement](https://files.alpaca.markets/disclosures/library/AcctAppMarginAndCustAgmt.pdf) |
| Redistribution restriction | [Alpaca redistribution support answer](https://alpaca.markets/support/redistribute-alpaca-api) |

This is a narrow technical/operator classification, not legal advice and not a declaration of
provider rights. For the exact Phase 28 pilot only, the reviewed first-party material supports
proceeding fail-closed with a transient, local, personal/non-commercial observation that displays
no raw provider value and redistributes no provider data. It does not support raw persistence,
research-dataset creation, public or commercial display, redistribution, a multi-user product,
performance claims, strategy use, or execution.

The CLI represents that currentness gate as
`--confirm-2026-07-24-exact-use-review`; it must accompany
`--confirm-credentialed-paper-only-external-observation`. The external mode remains blocked if the
operator's actual intended use is commercial, public,
multi-user, redistributive, or otherwise broader; if the account or market-data plan does not cover
the fixed requests; if the current terms differ from this review; if access is revoked; or if any
scope/currentness fact cannot be confirmed. At or after `2026-08-01T00:00:00Z`, a refreshed
first-party exact-use review and separately reviewed code update are required before transport;
the confirmation flag cannot extend the deadline. An API key, successful retrieval, open-source
client, or free access is not rights evidence and cannot override that block.

## Security and adversarial decisions

The implementation and tests must reject:

- any method other than the six exact `GET` requests or any request body;
- any endpoint, host, path, query, symbol, feed, currency, or order different from the fixed
  manifest;
- missing, blank, or partial credentials before network initialization;
- redirects, non-200 responses, wrong content type, duplicate JSON keys, non-finite or out-of-range
  numbers, control characters, oversized bodies, schema drift, stale data, symbol mismatch, missing
  symbols, extra symbols, and duplicate symbols;
- proxy routing, retries, sleeps, loops that repeat transport, polling, websockets, and schedulers;
- credentials influencing hashes or appearing in errors, logs, files, evidence, or reprs; raw
  provider literals appearing in any of those surfaces; approved one-way response, request-ID,
  and sanitized-observation hashes are the only retained derivatives;
- any database, API, frontend, generic vendor-SDK, order, execution, cancellation, liquidation,
  position-closing, live-money, or live-host surface; and
- output vocabulary such as `BUY`, `SELL`, `LONG`, `SHORT`, position size, quantity, price target,
  allocation, time in force, or order instruction.

Literal negative assertion: Phase 28 contains no order API or execution surface, and the real-money
path is absent rather than disabled.

## Implementation units

### P28-CORE - fixed adapter, contracts, workflow, CLI, and focused tests

Governing phase: Phase 28 only. The unit owns only the isolated Phase 28 paper-service package, its
CLI capture entry point, and focused Phase 28 tests. Acceptance commands are the focused contract,
adapter, workflow, security, and static tests named in `docs/handoffs/PHASE_28.md`, followed by Ruff
and mypy. Literal adversarial assertion: planting `/v2/orders`, a non-GET method, a fourth symbol,
`feed=sip`, a raw numeric value in evidence, or a database/API/frontend import must fail.

Evidence: the CLI's sanitized JSON artifact with config, universe, predicate, and transport-profile
hashes; evidence and sanitized-observation-snapshot IDs/hashes; Git SHA; seed/trial count `0/0`;
UTC timestamps; exact-use confirmation/deadline fields; `forecast_horizon=NONE_OBSERVATION_ONLY`;
fixed labels;
closed outcomes; and false authority fields. Stop if implementation needs a provider SDK, another
symbol/request, persistence, API/frontend work, a strategy or order concept, a live path, or a
credentialed external call.

### P28-DOC - decisions, handoff, and status reconciliation

Governing phase: Phase 28 documentation and accepted status maintenance only. Acceptance commands
are `git diff --check`, focused policy/static tests, and the Phase 28 static verifier. Literal
adversarial assertion: the documents cannot claim consolidated coverage, research qualification,
provider rights, performance, advice, execution, order, or live authority.

Evidence: documentation source URLs and 2026-07-24 review date, the accepted T-010 baseline SHA,
the Phase 28 source-path manifest and content hashes produced by verification, Git SHA, seed/trial
count `0/0`, and UTC verification timestamp. Stop if documentation maintenance requires changing a
preserved artifact or accepted Phase 12, Phase 27, T-007, T-009, or T-010 identity.

### P28-VERIFY - verifier, CI, and directly affected policy tests

Governing phase: Phase 28 verification integration only. Acceptance commands are the focused Phase
28 tests, repository-policy/status tests, `scripts/verify_phase1.py --static-only --phase 28`, and
the complete local Phase 28 verification path from a clean committed tree when one is later
authorized. Literal adversarial assertion: omission, substitution, extra-path drift, secret-shaped
content, provider traffic in CI, accepted-identity drift, or any order/live token fails closed.

Evidence: exact path and content manifests, preserved-identity hashes, command results, Git SHA,
seed/trial count `0/0`, and UTC timestamp. Stop if a passing gate would require weakening an earlier
guardrail, changing an accepted artifact/allowlist, or authorizing an external request.

## Stop condition

Stop after the CLI-only Phase 28 implementation, deterministic mock proof, documentation, focused
tests, and verification integration. Do not perform a credentialed external run without separate
authorization. Do not add a database, API, frontend, raw-data artifact, research snapshot,
strategy, performance calculation, risk promotion, order, execution, cancellation, liquidation,
or live-money surface. Do not begin a replacement Family A acquisition/schema phase.
