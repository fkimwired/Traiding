# Phase 28 Alpaca IEX observation-only candidate-screen pilot handoff

## Objective and current result

Implement one CLI-only pilot that classifies a fixed `AAPL`/`MSFT`/`SPY` universe from fixed
GET-only Alpaca asset, latest-bar, latest-quote, and snapshot responses using exactly `iex` and
`USD`. Raw provider data is transient; output is sanitized historical evidence labeled
partial-market, paper-only, and no-advice.

No credentialed external observation is part of this task. The current external disposition is:

```text
outcome:       BLOCKED
determination: EXTERNAL_OBSERVATION_REQUIRES_SEPARATE_AUTHORIZATION
```

The local deterministic mock can prove only the contract. It cannot claim external connectivity,
current provider state, research qualification, a trade signal, or execution readiness.

## Accepted input identity and supersession

```text
accepted T-010 commit: e9f4d99d8c1bc5c5b4ac615cf3592d5f0ae3113e
accepted T-010 CI run: 30060339481
accepted T-007 commit: 4180ce659aa621d6155cac1118f7011deb92aa9f
accepted T-009 commit: 1d8aa00f80fdd60b2b5ab3d431448de28a872c17
accepted Phase 27:     b887ed4c0a7552a784c4aeaf433aa4fb3e5569a4
accepted Phase 12:     37530a94f841d538a162447cb01ec3e11f375ead
```

The repository owner's authorization explicitly supersedes the previously reserved Phase 28
Family A acquisition/schema boundary with this pilot. It does not modify the accepted
CRSP/SEC/RTDSM composition or the Phase 27 determination:

```text
BLOCKED / COMPOSITION_RIGHTS_ENTITLEMENT_EVIDENCE_MISSING / false
```

## Exact request and classification contracts

The request manifest is exactly:

```text
GET paper-api.alpaca.markets /v2/assets/AAPL
GET paper-api.alpaca.markets /v2/assets/MSFT
GET paper-api.alpaca.markets /v2/assets/SPY
GET data.alpaca.markets /v2/stocks/bars/latest?symbols=AAPL%2CMSFT%2CSPY&feed=iex&currency=USD
GET data.alpaca.markets /v2/stocks/quotes/latest?symbols=AAPL%2CMSFT%2CSPY&feed=iex&currency=USD
GET data.alpaca.markets /v2/stocks/snapshots?symbols=AAPL%2CMSFT%2CSPY&feed=iex&currency=USD
```

No CLI or environment setting can alter that manifest. The decoded canonical `symbols` value is
exactly `AAPL,MSFT,SPY`; `%2C` is only its fixed wire encoding. Each symbol has exactly these
ordered predicates: `ASSET_ACTIVE`, `ASSET_TRADABLE`,
`LATEST_BAR_VALID_AND_FRESH`, `LATEST_QUOTE_VALID_AND_FRESH`,
`SNAPSHOT_COMPLETE_AND_FRESH`,
`CROSS_ENDPOINT_COHERENT`, `SESSION_DIRECTION_POSITIVE`, and
`INTRADAY_DIRECTION_POSITIVE`. The only symbol outcomes are `MATCH`, `NO_MATCH`, and
`INSUFFICIENT_DATA`. Invalid, missing, stale, mismatched, duplicate, or uncomputable required data
produces `INSUFFICIENT_DATA`; otherwise every predicate must match for `MATCH`, and a computable
nonmatch produces `NO_MATCH`.

The latest bar, latest quote, snapshot trade, snapshot quote, and snapshot minute bar use the exact
120-second freshness allowance. Cross-endpoint coherence compares like-for-like only: latest bar
versus snapshot `minuteBar` has a fixed 60-second bucket-rollover tolerance, while latest quote
versus snapshot `latestQuote` has a fixed 30-second tolerance. The workflow never compares a bar
timestamp with a quote timestamp. Snapshot completeness requires `latestTrade`, `latestQuote`,
`minuteBar`, `dailyBar`, and `prevDailyBar`.

These are observation predicates with no predictive horizon, ranking, action mapping, strategy,
position size, or order meaning. The evidence fixes that boundary as
`forecast_horizon=NONE_OBSERVATION_ONLY`.

## Data, security, and exact-use posture

All raw response bodies, headers, prices, sizes, conditions, exchange codes, asset identifiers, and
provider timestamps are discarded after in-memory validation and classification. No provider SDK,
database, cache, API, frontend, generated contract, migration, retry, polling, websocket, scheduler,
or generic request method is added.

Credentialed mode loads only `FABLE5_ALPACA_PAPER_API_KEY_ID` and
`FABLE5_ALPACA_PAPER_SECRET_KEY`, rejects a missing/blank/partial pair before transport, and requires
both `--confirm-credentialed-paper-only-external-observation` and
`--confirm-2026-07-24-exact-use-review`. CI and this implementation task clear or deny credentials
and network access. An external invocation additionally requires separate human authorization.

The first-party exact-use review dated 2026-07-24 is recorded in
`docs/PHASE_28_ALPACA_IEX_OBSERVATION_ONLY_CANDIDATE_SCREEN_DECISIONS.md`. It narrowly supports only
transient local personal/non-commercial observation with no raw display, persistence, or
redistribution. That classification is not legal advice or provider-rights evidence. External mode
must remain blocked when intended use or current terms differ or cannot be confirmed. The internal
revalidation deadline is `2026-08-01T00:00:00Z`; at or after that instant, transport must fail
closed until a refreshed first-party review and separately reviewed code update replace the expired
control. A CLI confirmation cannot extend the deadline.

Every output must include:

> IEX is a partial-market feed and does not represent the consolidated U.S. market. This
> observation is for paper-only testing, is not research-qualified, is not a trade signal, and is
> not investment advice.

## Sanitized evidence

The JSON artifact includes an evidence ID/hash; an observation-snapshot ID/hash/kind fixed to
`SANITIZED_OBSERVATION_METADATA_ONLY`; fixed config, universe, predicate, and
transport-profile hashes; Git SHA; one observation UTC timestamp and per-inspection UTC timestamps;
seed/trial count `0/0`; source kind; per-request endpoint/status/HTTP/request-ID SHA-256/response
SHA-256/sanitized-observation SHA-256/inspection SHA-256 metadata; per-symbol closed outcomes and
reasons; exact-use review confirmation and revalidation-deadline fields; fixed labels; and explicit
false persistence, research, execution, order, and live-authority fields. The configuration hash
binds the exact-use review hash and deadline.

It includes no credential, header, body, account identifier, raw price/size/timestamp, provider
payload fragment, order detail, strategy output, performance value, or personal identifier. The
observation-snapshot fields identify sanitized inspection metadata, not provider data or a research
snapshot. The artifact is historical evidence and never self-revalidates.

## Implementation units and acceptance

### P28-CORE

Governing phase: Phase 28 only. Own the isolated Phase 28 paper-service package, CLI, and focused
tests. Literal negative assertion: a planted non-GET request, non-paper host, alternate symbol/feed,
raw numeric output, order operation, database/API/frontend import, or live-money token fails.

Required evidence: one deterministic sanitized mock artifact or its exact test fixture assertion
containing all required hashes, evidence and sanitized-observation-snapshot IDs/hashes, Git SHA,
seed/trial count `0/0`, UTC timestamp, `forecast_horizon=NONE_OBSERVATION_ONLY`, labels, outcomes,
and false authority fields.

Stop on any need for credentials, an external request, a seventh request, a fourth symbol, raw
persistence, provider SDK, strategy/execution logic, or another project layer.

### P28-DOC

Governing phase: Phase 28 documentation/status maintenance only. Literal negative assertion: no
source may be described as consolidated, research-qualified, rights-cleared for broader use, or
capable of orders or live execution.

Required evidence: exact source URLs and review date, accepted identities, source-path/content
manifest, Git SHA, seed/trial count `0/0`, and UTC verification time. Stop if an accepted artifact
or accepted Phase 12/27/T-007/T-009/T-010 identity would change.

### P28-VERIFY

Governing phase: Phase 28 verifier/CI/direct-policy maintenance only. Literal negative assertion:
CI performs no provider request, reads no credential, and rejects scope drift, secret leakage,
raw-data output, order/execution/live tokens, and accepted-identity drift.

Required evidence: Phase 28 exact-path/content manifest, preserved hashes, command results, Git SHA,
seed/trial count `0/0`, and UTC time. Stop rather than weaken an inherited gate or expand scope.

## Acceptance commands

Run targeted gates first, using the exact focused test paths present in the implementation:

```powershell
git diff --check
.\.venv\Scripts\python.exe -m pytest `
  services\paper\tests\test_phase28_contracts.py `
  services\paper\tests\test_phase28_adapters.py `
  services\paper\tests\test_phase28_workflow.py `
  services\paper\tests\test_phase28_security.py `
  tests\test_phase28_static.py -q
.\.venv\Scripts\python.exe -m pytest `
  tests\test_status_currency.py `
  tests\test_repository_policy.py `
  tests\test_phase27_static.py -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m mypy
.\.venv\Scripts\python.exe scripts\verify_phase1.py --static-only --phase 28
```

Run the deterministic mock only; it must make zero socket calls:

```powershell
$env:FABLE5_CODE_VERSION_GIT_SHA = (git rev-parse HEAD)
.\.venv\Scripts\python.exe scripts\capture_alpaca_iex_observation_pilot.py --deterministic-mock
Remove-Item Env:FABLE5_CODE_VERSION_GIT_SHA
```

Then run the relevant full Python, frontend, contract, build, secret-scan, and repository verification
paths documented by CI. A later clean committed-tree full Phase 28 verifier is required before
formal acceptance. Do not invoke the credentialed CLI mode during implementation or CI.

## Mandatory adversarial coverage

Tests must prove:

- exactly six GETs, exact order/hosts/targets, no body, redirect, retry, polling, websocket, or
  proxy;
- exact fixed universe/feed/currency and exact response symbol set;
- credential pair validation and canary secrecy before transport;
- malformed, duplicate, non-finite, oversized, stale, scope-mismatched, or partial data fails
  closed;
- deterministic mock cannot claim external observation;
- raw numeric and credential canaries never reach output, logs, evidence, or files;
- no database/API/frontend/provider-SDK/order/execution/cancellation/liquidation/live-money surface;
  and
- Phase 12, Phase 27, T-007, T-009, T-010, and the accepted Phase 27 result remain unchanged.

## Migration, rollback, and external-run boundary

There is no migration. Removing only the isolated Phase 28 files and status integration is the
implementation rollback; accepted earlier-phase bytes remain untouched.

A credentialed external run is a separate operator action requiring separate explicit authorization,
current exact-use confirmation, paper credential confirmation, and a clean passing Phase 28 gate.
It may occur once only when the authorization says so. It may not be inferred from this handoff,
the presence of credentials, a successful mock, or a green CI run.

## Stop condition

Stop after Phase 28 local implementation, deterministic mock proof, documentation, tests, and
verification integration. Do not contact Alpaca, inspect an account, load credentials, perform an
external request, store raw data, create a research snapshot, begin Family A acquisition/schema
work, add an API/frontend/database surface, calculate performance, promote risk, submit an order,
or add any real-money path.
