# Phase 13 point-in-time data qualification decisions

## Accepted baseline and authority

Phase 13 starts only from the formally accepted Phase 12 identity:

- Commit: `37530a94f841d538a162447cb01ec3e11f375ead`
- Tree: `d8d747ffccb76c3d754cdd2cc14b8ec49fb97287`
- Windows full Phase 12 verifier: passed at that identity.
- Ubuntu GitHub Actions run `29613639340`: `preflight`, `unit`, and
  `phase12-compose` passed at that identity.

The user separately authorized implementation through Phase 14. Phase 13 must still be completed and
accepted on Windows and Ubuntu before Phase 14 implementation starts.

## Decision

Phase 13 is a qualification-only evidence harness for the frozen Family A point-in-time data profile.
It does not onboard provider observations as research snapshots, run a strategy, compute returns, or
promote research. Frozen Phase 4-7 tables and contracts remain truthfully synthetic and must not be
relaxed, rewritten, or relabeled.

Phase 13 implements one vendor-neutral read-only qualification adapter, one deterministic mock, and
one external candidate implementation for Tiingo. Tiingo remains a candidate, not an approved
provider. Ordinary acceptance is credential-free, mock-only, and network-denied. Without a separately
authorized external capture using existing credentials plus independently reviewed use-rights
evidence, external qualification remains unproven.

Only these outcomes exist:

- `MOCK_PROOF_COMPLETE`: deterministic fixtures prove the local contract and persistence path.
- `EXTERNAL_SAMPLE_QUALIFIED`: a credentialed external sample passed every frozen qualification
  check. It remains sample evidence only.
- `BLOCKED`: one or more checks failed or were uncomputable.

A mock can never produce `EXTERNAL_SAMPLE_QUALIFIED`. No Phase 13 outcome is a research dataset or
authority to promote, simulate, submit, or route an order.

Every artifact states immutable false authority fields:

```text
research_data_eligible = false
strategy_promotion_authorized = false
strategy_execution_eligible = false
execution_authorized = false
order_submission_authorized = false
live_path_absent = true
no_personalized_investment_advice = true
no_real_performance_claimed = true
```

## Frozen Family A qualification profile

The exact capability registry is:

1. `SECURITY_MASTER_STABLE_IDENTITY`
2. `POINT_IN_TIME_UNIVERSE_MEMBERSHIP`
3. `RAW_OHLCV_AVAILABILITY`
4. `CORPORATE_ACTION_ANNOUNCEMENT_REVISION`
5. `DELISTING_RETURN_SEMANTICS`
6. `AS_REPORTED_FUNDAMENTAL_REVISION`

The server owns the sample-plan identity, cases, symbols, date ranges, schemas, byte/record limits,
and expected semantics. The operator supplies only an idempotency key and explicit confirmation.
Current ticker lists must never substitute for historical membership. Adjusted prices must never
silently substitute for raw prices plus separately auditable actions. A missing delisting return must
remain explicit missingness and never become zero.

The exact ordered check registry is:

1. `SOURCE_KIND_EXACT`
2. `READ_ONLY_TRANSPORT_EXACT`
3. `USE_RIGHTS_CURRENT_SUFFICIENT`
4. `SECURITY_MASTER_STABLE_IDENTITY`
5. `POINT_IN_TIME_UNIVERSE_MEMBERSHIP`
6. `RAW_OHLCV_AVAILABILITY`
7. `CORPORATE_ACTION_ANNOUNCEMENT_REVISION`
8. `DELISTING_RETURN_SEMANTICS`
9. `AS_REPORTED_FUNDAMENTAL_REVISION`
10. `RAW_NORMALIZED_RECONCILIATION`
11. `NULL_SENTINEL_SCHEMA_DRIFT`
12. `DETERMINISTIC_CAPTURE_MANIFEST`

Check statuses are exactly `PASS`, `BLOCKED`, and `UNCOMPUTABLE`. External qualification requires
all twelve checks to pass. Capability, schema, temporal, identity, rights, or reconciliation gaps are
preserved as explicit sanitized evidence.

## Tiingo candidate boundary

Official Tiingo documentation currently describes token-authenticated REST data, raw and adjusted EOD
prices, dividend cash and split factors, a permanent ticker, active/delisted metadata, public release
dates, and as-reported statement behavior. Its detailed dividend/split endpoints are
entitlement-dependent. Those facts make Tiingo a candidate for a bounded capability test; they do not
prove historical universe membership, complete delisting-return treatment, or Fable5's storage and
derived-data rights.

The external adapter can represent only these fixed HTTPS GETs:

```text
GET https://api.tiingo.com/tiingo/fundamentals/meta?columns=permaTicker,ticker,isActive,statementLastUpdated,dailyLastUpdated
GET https://api.tiingo.com/tiingo/daily/AAPL/prices?startDate=2020-08-28&endDate=2020-09-01
GET https://api.tiingo.com/tiingo/corporate-actions/AAPL/distributions?startExDate=2020-01-01&endExDate=2020-12-31
GET https://api.tiingo.com/tiingo/corporate-actions/AAPL/splits?startExDate=2020-08-28&endExDate=2020-09-01
GET https://api.tiingo.com/tiingo/fundamentals/AAPL/statements?startDate=2019-01-01
```

`AAPL` and the frozen dates are qualification probes only. They are not a strategy universe,
recommendation, research result, or future order candidate. No documented endpoint is accepted as
proof of historical membership or delisting returns; those two capabilities remain blocked unless a
future independently reviewed provider contract and response semantics prove them.

The adapter has no generic request method. It accepts no provider, URL, host, path, query, symbol,
date, capability, timeout, retry, or redirect configuration. It uses the standard library, fixed port
443, TLS hostname/certificate verification, no proxy inheritance, no redirect, one bounded attempt,
strict UTF-8/JSON parsing, duplicate-key and non-finite-number rejection, and sanitized failures.

## Credentials, rights, and payload handling

Only the local capture command may load:

```text
FABLE5_TIINGO_RESEARCH_API_TOKEN
FABLE5_TIINGO_RESEARCH_RIGHTS_ATTESTATION_ID
FABLE5_TIINGO_RESEARCH_RIGHTS_ATTESTATION_SHA256
FABLE5_TIINGO_RESEARCH_RIGHTS_VALID_FROM_UTC
FABLE5_TIINGO_RESEARCH_RIGHTS_EXPIRES_AT_UTC
FABLE5_TIINGO_RESEARCH_STORAGE_ALLOWED
FABLE5_TIINGO_RESEARCH_NON_DISPLAY_ALLOWED
FABLE5_TIINGO_RESEARCH_DERIVED_DATA_ALLOWED
```

The token is a `SecretStr`. Missing, blank, partial, expired, or insufficient credential/rights input
fails before transport, socket, or database construction. Environment assertions are captured as
attestation evidence but are not themselves proof that a provider granted an entitlement; external
acceptance must report that limitation.

Raw external bodies exist only transiently in bounded memory. Persistence retains sanitized timings,
status, record/count ranges, missingness and revision counts, schema identities, raw-body hashes,
normalized-evidence hashes, and manifest hashes. It stores no licensed body, token, authorization
header, token-bearing URL, exception text, raw price, issuer statement value, or redistributable data.

## Persistence, idempotency, API, and CLI

Migration `0010_phase13` directly revises `0009_phase12` and owns only:

```text
point_in_time_qualification_runs
point_in_time_qualification_payloads
point_in_time_qualification_checks
```

All three tables are append-only and reject `UPDATE`, `DELETE`, and `TRUNCATE`. Composite
identifier/hash foreign keys prevent lineage swapping. Deferred completeness requires exactly six
ordered capability manifests and twelve ordered checks at commit. Database-owned creation time,
canonical hashes, deterministic UUID identities, and exact scalar/payload parity are mandatory.

Single-flight creation locks the idempotency key before adapter activity. The same key and fingerprint
returns the existing complete artifact without another adapter sequence. Conflicting reuse fails before
transport. No partial artifact survives transport, validation, or persistence failure.

The sole Phase 13 API route is:

```text
GET /v1/point-in-time-data-qualifications/{qualification_id}
```

It returns persisted sanitized evidence only, performs zero writes and zero external calls, and has
typed 200/404/409/422 responses. Mutation methods return 405.

The sole external creator is:

```text
python scripts/capture_point_in_time_data_qualification.py \
  --idempotency-key KEY \
  --confirm-read-only-qualification
```

It accepts no provider, URL, symbol, date, capability, credential, rights flag, strategy, action,
side, quantity, price, allocation, retry, broker, or execution argument. There is no scheduler,
worker, queue, poller, WebSocket, retry loop, or asynchronous path.

## Explicit exclusions

Phase 13 adds no real-data research snapshot ingestion, feature, label, signal, model, strategy,
backtest, evaluation, promotion, approval, risk, paper-broker, quote, account, position, order, fill,
reconciliation, credential UI, frontend product surface, vendor SDK, dependency, arbitrary URL,
alternate provider, live path, deployment, publication, release, tag, or Phase 14 scaffold.

Phase 4-7 migrations, contracts, synthetic flags, source artifacts, and SQL functions remain
byte-identical. `PASS_RESEARCH`, `APPROVED_PAPER`, Phase 10/11 evidence, and Phase 12 readiness are not
qualification shortcuts.

## Failure and rollback semantics

Missing credentials or rights create no artifact. HTTP, timeout, DNS/TLS, redirect, malformed,
oversized, duplicate-key, non-finite, schema-drift, current-universe, missing-history, temporal,
identity, action, delisting, revision, reconciliation, rights, or nondeterminism defects can only
produce sanitized `BLOCKED` evidence or a pre-artifact generic failure. There is no automatic retry.

Acceptance proves the nonempty cycle:

```text
0009_phase12 -> 0010_phase13 -> 0009_phase12 -> 0010_phase13
```

Every inherited row and prior SQL function body must remain byte-identical. Downgrade drops only the
three Phase 13 tables plus Phase 13-owned triggers and functions.

## Acceptance and stop condition

Acceptance requires generated-contract parity; deterministic complete/blocked and mock-cannot-
qualify proofs; fixed-target and secret-canary tests; active network denial; temporal, membership,
revision, action, delisting, null, schema-drift, reconciliation, nondeterminism, idempotency,
concurrency, tamper, append-only, migration, zero-write GET, inherited browser, exact identity, and
resource-cleanup proofs on Windows and Ubuntu at one committed SHA/tree.

An external Tiingo result is not required for implementation acceptance and is not authorized without
existing credentials and independently reviewed rights evidence. Without it,
`EXTERNAL_SAMPLE_QUALIFIED` remains unproven. Stop after Phase 13 acceptance before implementing
Phase 14, even though the user has already authorized Phase 14.
