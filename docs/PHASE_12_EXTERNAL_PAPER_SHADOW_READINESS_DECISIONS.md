# Phase 12 external-paper shadow-readiness decisions

## Accepted baseline and authority

Phase 12 starts only from the formally accepted Phase 11 identity:

- Commit: `b8657abe34d3290a42cb92cb1ad751d0d9d73ad5`
- Tree: `b6f57d6448dea70911f6f80695100ae53c6b6513`
- Windows full verifier: passed at that identity.
- Ubuntu GitHub Actions run `29599118998`: `preflight`, `unit`, and `phase11-compose`
  passed at that same commit.

The user separately authorized Phase 12 after that acceptance. Phase 12 creates read-only historical
evidence about an external paper environment. It does not authorize or create an order.

## Decision

Phase 12 is the credentialed real-data and paper-environment shadow-readiness prerequisite. The first
externally routed paper-only order is deferred. Existing Phase 7 approval, Phase 10 local simulation,
and Phase 11 portable evidence remain synthetic or historical evidence and are not execution
authority.

Only these outcomes exist:

- `MOCK_PROOF_COMPLETE`: the deterministic mock proves the local contract and persistence path.
- `SHADOW_READY`: a credentialed external read sequence passed every bounded readiness check.
- `BLOCKED`: at least one readiness check did not pass.

A mock can never produce `SHADOW_READY`. Every artifact expires exactly 60 seconds after its
assessment completes. Expiry does not delete the artifact; it makes it historical evidence only.

Every result states these immutable literals:

```text
order_submission_authorized = false
strategy_execution_eligible = false
live_path_absent = true
no_personalized_investment_advice = true
no_real_performance_claimed = true
```

## Fixed read-only adapter boundary

`PaperBrokerAdapter` has exactly six argument-free inspection methods:

```text
inspect_account()
inspect_clock()
inspect_instrument()
inspect_positions()
inspect_open_orders()
inspect_latest_quote()
```

The package contains one deterministic mock and exactly one external implementation. The external
implementation uses standard-library HTTPS and can represent only these requests, in this order:

```text
GET https://paper-api.alpaca.markets/v2/account
GET https://paper-api.alpaca.markets/v2/clock
GET https://paper-api.alpaca.markets/v2/assets/AAPL
GET https://paper-api.alpaca.markets/v2/positions
GET https://paper-api.alpaca.markets/v2/orders?status=open&limit=500&direction=asc
GET https://data.alpaca.markets/v2/stocks/AAPL/quotes/latest?feed=iex&currency=USD
```

`AAPL` and `iex` are frozen connectivity probes. They are not a strategy instrument, recommendation,
order candidate, or authorization source. No URL, host, port, scheme, path, query, method, symbol,
feed, provider, retry, or redirect setting is exposed.

The adapter contains no submit, replace, cancel, liquidate, close-position, stream, polling, or
generic-request method. No strategy imports the adapter or a vendor SDK.

## Credential and transport security

Only the local capture command loads credentials, and only from:

```text
FABLE5_ALPACA_PAPER_API_KEY_ID
FABLE5_ALPACA_PAPER_SECRET_KEY
```

The values are represented by `SecretStr`. Missing, blank, or partial pairs fail before transport,
socket, or database construction. The API and frontend never load them. CI explicitly clears both
variables and proves only the deterministic mock path.

The fixed HTTPS transport:

- uses port 443 with certificate and hostname verification;
- inherits no proxy and follows no redirect;
- has a fixed timeout and response-size bound;
- accepts only HTTP 200 JSON for a successful observation;
- rejects malformed UTF-8, duplicate JSON keys, non-finite or unbounded numbers, schema drift, and
  control characters;
- retains only sanitized readiness fields, bounded request IDs, counts, and hashes;
- performs no automatic retry; and
- never logs or persists credentials, headers, raw bodies, account identifiers, order details, or
  raw position details.

HTTP failures, timeout, DNS/TLS failure, redirect, malformed/oversized data, blocked account, closed
clock, inactive or non-tradable instrument, nonempty positions or open orders, feed mismatch, invalid
quote, or stale quote can only produce `BLOCKED`. Raw exceptions are discarded in favor of fixed
reason codes.

## Deterministic contracts and checks

The exact check registry is:

1. `SOURCE_KIND_EXACT`
2. `READ_ONLY_TRANSPORT_EXACT`
3. `ACCOUNT_READY`
4. `MARKET_CLOCK_OPEN`
5. `INSTRUMENT_ACTIVE_TRADABLE`
6. `POSITIONS_EMPTY`
7. `OPEN_ORDERS_EMPTY`
8. `IEX_QUOTE_FRESH_VALID`

Checks are ordered, content-hashed, and complete at transaction commit. Request fingerprints are
computed before network activity and bind only the idempotency key, source kind, fixed transport
profile hash, and Phase 12 Git SHA. They never bind credentials.

The artifact retains sanitized inspection timing, response status, bounded request ID, response hash,
account blocking state, clock state, instrument identity/status, aggregate inventory counts/hashes,
quote feed/event/receipt/freshness validity, outcome/reasons, code SHA, and expiry. It retains no raw
price because Phase 12 is not a market-data snapshot or strategy input.

## Persistence, idempotency, and API

Migration `0009_phase12` directly revises `0008_phase10` and owns only:

```text
paper_shadow_readiness_runs
paper_shadow_readiness_checks
```

Both tables are append-only: direct update, delete, and truncate fail. Composite identifier/hash
foreign keys prevent child-lineage swapping, and deferred completeness requires the exact eight
checks in canonical order. No earlier table receives a trigger or constraint.

The workflow acquires an idempotency-key advisory lock before any adapter call. The same key and
fingerprint returns the existing artifact without another inspection sequence. Reusing the key with a
different fingerprint fails with a sanitized conflict before adapter activity.

The only public Phase 12 API route is:

```text
GET /v1/paper-shadow-readiness/{readiness_assessment_id}
```

It reads persisted evidence only and performs no write or external call. Its typed outcomes are 200,
404, 409, and 422; mutation methods return 405.

The local operator command is:

```text
python scripts/capture_paper_shadow_readiness.py \
  --idempotency-key KEY \
  --confirm-paper-only-readiness
```

It accepts no provider, URL, symbol, account, credential, strategy, side, quantity, allocation, price,
retry, submission, or cancellation argument. The command never falls back from missing external
credentials to mock evidence.

## Explicit exclusions

Phase 12 adds no:

- order intent, submission, replacement, cancellation, liquidation, fill, mutation, or reconciliation;
- side, quantity, allocation, limit/stop price, or executable strategy parameter;
- scheduler, worker, queue, WebSocket, polling loop, retry loop, or asynchronous process;
- real historical strategy ingestion, backtest, promotion, or strategy expansion;
- production/live origin, live enum, live credential, live dependency, branch, or dormant path;
- arbitrary broker configuration or vendor SDK;
- browser credential field, browser-to-vendor call, or API mutation endpoint;
- raw account identifier, raw header/body, licensed payload, secret, order, fill, or price persistence;
- claim that paper performance predicts real performance; or
- Phase 13 work, deployment, publication, tag, release, or Phase 12 push without later authority.

## Migration and failure semantics

Acceptance proves the nonempty cycle:

```text
0008_phase10 -> 0009_phase12 -> 0008_phase10 -> 0009_phase12
```

Every inherited table and relevant earlier SQL function body must remain byte-identical. Downgrade
drops only Phase 12 tables, triggers, constraints, and functions.

Missing credentials create no artifact. A persistence failure after reads creates no authority.
Operator rerun requires an explicit command and key; there is no automatic retry. A stale successful
artifact remains immutable historical evidence and never becomes permission to submit.

## Acceptance and stop condition

Phase 12 acceptance requires generated-contract parity, deterministic mock proof, adversarial blocked
cases, credential canaries absent from all artifacts/logs/contracts/build output, active socket denial
for mock and API paths, PostgreSQL hash/tamper/idempotency/append-only proof, inherited browser
regressions, complete resource cleanup, and Windows/Ubuntu gates at one committed SHA/tree.

A real external `SHADOW_READY` probe is separately authorized work and is not part of CI or this
implementation run. Stop after Phase 12. Do not submit an order or begin Phase 13.
