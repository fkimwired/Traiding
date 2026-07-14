# Phase 4 data-contract decisions

Status: frozen for Phase 4 implementation
Decision date: 2026-07-13
Phase 3 baseline: `24e243e373ec6c6aacad22cf47505c50cc7bbcaa`

This record freezes the vendor-neutral, point-in-time contract boundary before any
adapter, persistence, API, or migration implementation. The executable authority is
`services/data/src/fable5_data/contracts.py` and
`services/data/src/fable5_data/canonical.py`.

## Scope and hard boundary

Phase 4 may acquire, normalize, quality-check, persist, and snapshot authorized data.
It does not define features, labels, signals, strategies, models, training, backtests,
performance metrics, portfolio or risk logic, approvals, brokers, positions, orders,
paper execution, or live capability. `BUILD_RESEARCH` authorizes data-contract work
only. It is not a profitability, advice, signal, approval, or paper-eligibility verdict.

The LLM is not part of any data adapter and cannot emit a trade instruction, position
size, or buy/sell call. No provider SDK type is permitted in these contracts.

## Frozen versions and identity namespaces

| Item | Frozen value |
|---|---|
| Canonical JSON | `phase4-canonical-json-v1` |
| Snapshot schema and hash domain | `phase4-data-snapshot-v1` |
| Raw observation envelope | `phase4-raw-observation-v1` |
| Normalized observation envelope and hash domain | `phase4-normalized-observation-v1` |
| Observation revision | `phase4-observation-revision-v1` |
| Data-quality rules | `phase4-data-quality-v1` |
| Request fingerprint version/domain | `phase4-request-fingerprint-v1` |
| Raw identity hash domain | `phase4-raw-observation-content-v1` |
| Revision content hash domain | `phase4-observation-revision-content-v1` |
| Normalized content hash domain | `phase4-normalized-observation-v1` |
| Quality-finding hash domain | `phase4-data-quality-finding-v1` |
| Logical-key hash domain | `phase4-logical-record-key-v1` |
| Synthetic adapter | `phase4-synthetic-pit-adapter-v1` |
| Synthetic fixtures | `phase4-synthetic-pit-fixtures-v1` |
| Synthetic use rights | `phase4-synthetic-test-fixture-rights-v1` |
| Date-only availability | `phase4-date-only-next-day-v1` |
| Mock-configuration hash domain | `phase4-mock-configuration-v1` |
| Snapshot UUID namespace | `db56962d-1bf7-5e22-a173-6629d0ff31f0` |
| Normalized-observation UUID namespace | `48c250b4-35ca-5b1c-a1fe-d9202aa009c7` |
| Raw-observation UUID namespace | `8087752b-5116-5683-bf09-341279373b14` |
| Revision UUID namespace | `bfbf0883-d241-5098-aef3-f737096bfb09` |
| Quality-finding UUID namespace | `c972a3e0-1991-590c-823d-b1bd73567457` |
| Logical-record UUID namespace | `29e71b4c-a922-5c9c-8465-1dbfb43810a8` |
| Request UUID namespace | `05238487-b285-5d41-8276-b09b65b020ff` |

Field schemas are frozen as:

- `phase4-instrument-identity-v1`
- `phase4-listing-identity-v1`
- `phase4-universe-membership-v1`
- `phase4-ohlcv-bar-v1`
- `phase4-corporate-action-v1`
- `phase4-delisting-event-v1`
- `phase4-as-reported-fundamental-v1`
- `phase4-calendar-session-v1`
- `phase4-official-document-event-v1`
- `phase4-volatility-return-input-v1`

## Authorized families and capabilities

Capability values are exact lowercase API values.

| Persisted Phase 3 family | Allowed capabilities |
|---|---|
| `A_CROSS_SECTIONAL_EQUITY_RANKING` | `security_master`, `universe_membership`, `ohlcv`, `corporate_actions`, `delistings`, `as_reported_fundamentals` |
| `B_TIME_SERIES_MOMENTUM_REGIME` | `ohlcv`, `corporate_actions`, `delistings`, `trading_calendar`, `volatility_return_inputs` |
| `C_OFFICIAL_EVENT_TEXT_OVERLAY` | `official_document_event_metadata` only, with exact persisted official-corroboration source-version IDs |

The request fails closed unless the mapping is persisted, resolves to exactly one of
these families, and has verdict `BUILD_RESEARCH`. `DEFER`, `DEFER_READ_ONLY`,
`REJECT_PLATFORM`, `NON_TESTABLE`, unresolved families, Family D pairs, Family E
order-book data, Family F options data, and social-only data are not authorized.
Mapping identity always binds mapping version and mapping-input SHA-256. Family C's exact
official-corroboration source-version UUID tuple is unique and canonically sorted; the
same mapping lineage is carried through the request fingerprint and persisted snapshot.

Capability-to-record binding is also exact:

| Capability | Permitted normalized record types |
|---|---|
| `security_master` | `instrument_identity`, `listing_identity` |
| `universe_membership` | `universe_membership` |
| `ohlcv` | `ohlcv_bar` |
| `corporate_actions` | `corporate_action` |
| `delistings` | `delisting_event` |
| `as_reported_fundamentals` | `as_reported_fundamental` |
| `trading_calendar` | `calendar_session` |
| `volatility_return_inputs` | `volatility_return_input` |
| `official_document_event_metadata` | `official_document_event` |

## Canonical serialization and hashing

Canonical JSON uses UTF-8, lexicographically sorted object keys, no insignificant
whitespace, and Unicode characters without ASCII escaping. It has these typed rules:

- aware datetimes are converted to UTC and rendered with six fractional digits and `Z`;
- dates use ISO `YYYY-MM-DD`;
- UUIDs and enum values use lowercase UUID text and their declared string value;
- finite decimals use a non-exponent string with insignificant trailing zeros removed;
- negative decimal zero becomes `0`;
- sets are sorted by the canonical JSON form of each member;
- tuple/list order remains significant;
- binary floats, raw bytes, naive datetimes, non-finite decimals, non-string object keys,
  and unsupported values are rejected.

A domain hash is `SHA256(ASCII(domain) || NUL || canonical_json_bytes(value))`.
Raw payload hashes are instead SHA-256 over the exact original bytes. Raw, revision,
normalized, quality-finding, logical-record, request, and snapshot storage identities use
separate frozen domains and UUIDv5 namespaces. Arbitrary UUID4 storage values never enter
canonical snapshot identity.

## Shared observation envelope

Every raw, revision, normalized, and snapshot-constituent record carries the following
lineage fields. Nullable fields require an explicit `FieldMissingness` entry and may
never use blank text, `unknown`, `n/a`, zero, or another sentinel.

- deterministic logical-record ID and logical-record-key SHA-256;
- provider, adapter ID/version, dataset, product, and dataset schema ID/version;
- entitlement ID and use-rights ID;
- source-record ID and stable instrument/listing IDs where applicable;
- `event_time`, `available_at`, `retrieved_at`, `valid_from`, and optional `valid_to`;
- immutable revision ID and vintage ID;
- source IANA timezone, calendar ID, unit, and ISO currency where applicable;
- quality flags, field-level missingness, and exact raw-payload hash.

All timestamps are aware and normalized to UTC. `available_at > event_time` is valid.
`retrieved_at` is nullable; when present it must be at or after `available_at`, and when
absent it has explicit field missingness. There is no redundant `retrieval_occurred`
boolean. `valid_to`, when present, must be after `valid_from`.

Timestamp-precision sources use their source timestamp. A source that supplies only an
availability date uses the documented conservative rule
`phase4-date-only-next-day-v1`: availability is midnight at the start of the next
calendar date in the declared source IANA timezone, converted to UTC. The source date
is retained and the convention is explicit.

## Grain, keys, units, missingness, and revision matrix

The shared provider/source/revision/vintage identities are part of every physical key.
The logical keys below identify the fact whose vintages must be replayable.

| Record | Declared grain and logical key | Time semantics | Units and missingness | Revision rule |
|---|---|---|---|---|
| Instrument identity | one stable instrument/share class over a validity interval; instrument ID + `valid_from` | identity event and validity interval | identifiers; listing/calendar/unit/currency are explicitly not applicable | new source identity vintage appends; never rewrites an earlier interval |
| Listing identity | one instrument listing on an exchange over a validity interval; listing ID + `valid_from` | listing-status event and validity interval | symbol, MIC, status; non-applicable measures are explicit | symbol, venue, or status changes append a new vintage |
| Universe membership | one listing in one universe over an interval; universe ID + listing ID + `valid_from` | membership effective time and source availability | included/excluded enum; measures not applicable | additions, removals, and corrections append; no current-constituent substitution |
| OHLCV bar | one listing + interval + bar start/end + adjustment basis + vintage | bar end is the market event; availability is provider publication | prices use declared currency/unit, volume is nonnegative shares, missing fields are explicit | raw bars never carry adjustment knowledge; adjusted bars bind exact action-revision IDs and an adjustment-as-of time |
| Corporate action | one action ID + revision/vintage | announcement and effective times are distinct; availability cannot precede announcement | split ratio or cash amount is type-specific; currency is explicit for cash | corrections append and retain the earlier announced vintage |
| Delisting event | one listing + delisting-event ID + vintage | last-trade and effective times are distinct | return is decimal and cannot be below -1; missing return has a specific reason and is never silently zero | corrections append; provider-total-return inclusion is explicit |
| As-reported fundamental | one instrument + concept + fiscal period + filing/amendment vintage | fiscal period is not availability; filing acceptance gates availability | declared unit/currency; null value has explicit source/as-of missingness | each accepted filing/amendment is retained; no latest-restatement substitution |
| Calendar session | one calendar + session date + vintage | session date with optional ordered open/close timestamps | timezone/calendar explicit; measurement units not applicable | corrections append; closed sessions cannot carry market hours |
| Official document/event metadata | one official source version + accession/document/event + vintage | publication, acceptance, event, and availability remain distinct | immutable document-content SHA-256; measures not applicable | amendments link to prior documents; content is never overwritten |
| Volatility/return input | one listing + window + exact referenced observation set + vintage | window start/end and input availability are explicit | contains observation references only, not a computed feature, label, return, volatility, or signal | any changed referenced vintage creates a new immutable input record |

## Immutable lineage and revision replay

The direction is fixed:

`RawObservation` → `ObservationRevision` → `NormalizedObservation` →
`SnapshotConstituent`.

- A raw observation stores exact payload bytes, content type, and payload hash. Its storage
  ID derives from canonical raw identity content, never an arbitrary UUID.
- An observation revision identifies its raw observation, logical-record-key hash,
  positive sequence, revision-content hash, and optional immutable predecessor revision.
- A normalized observation identifies both its raw observation and observation revision.
  Its content hash covers its complete canonical content except its own ID and hash, and
  its storage ID derives from that hash.
- A snapshot constituent identifies the raw observation, revision, normalized observation,
  logical key, raw hash, normalized hash, and quality disposition.

Every derived envelope must preserve the raw provider, adapter, dataset, schema,
entitlement, source, temporal, revision/vintage, unit, currency, and payload-hash lineage.
Revision predecessors must be the immediately prior sequence for the same logical-key
hash. A corrected vintage may have a different provider `source_record_id`; predecessor
grouping never relies on source-record identity.
No raw observation, revision, normalized observation, or snapshot is mutable.
Persistence reserves table names `data_raw_observations` and
`data_normalized_observations`; migration and trigger details are implemented separately.

## Snapshot identity and as-of rule

A request fingerprint is computed before adapter output. It binds every server-resolved
input: mapping ID/version/input hash/rule-set version and hash, as-of UTC, capability,
provider/adapter/dataset/product identity, adapter version, ordered schema bindings,
entitlement/use-rights identity, mock-configuration ID/hash and fixture version, snapshot
schema version, canonicalization version, and date-only convention. It deliberately does
not bind constituents or findings. The same fingerprint with a different snapshot output
is a typed nondeterminism conflict; the candidate snapshot hash still changes.

A snapshot manifest binds all of the following:

- the persisted mapping ID/version/input hash and mapping rule-set version/hash;
- requested as-of UTC, capability, and server-resolved mock-configuration ID;
- adapter/provider/product identity and adapter version;
- exact ordered schema bindings;
- entitlement and use-rights identity and permissions;
- mock-configuration hash and fixture-set version;
- canonically ordered constituent identities, logical keys, raw/content hashes,
  revision/vintage identities, complete temporal/missingness metadata, and disposition;
- canonically ordered quality findings and the data-quality rule-set version.

Constituents are sorted by record type, deterministic logical-record ID/key, revision,
vintage, raw hash, normalized hash, and disposition. Canonical snapshot identity binds
those values plus quality flags and explicit missingness, but excludes raw/revision/
normalized storage UUIDs. Findings are sorted by rule set/rule ID, severity, closed code,
affected record identity, hashes, field, disposition, and deterministic finding hash.
Unsorted or duplicate canonical constituents are rejected.

Constituent dispositions are exactly `included_as_of`,
`retained_historical_vintage`, and `explicit_missingness`. Active constituent count
includes `included_as_of` and `explicit_missingness`; historical vintages remain auditable
but are not active. Raw, revision, normalized, and constituent counts are stored
independently and are never forced equal.

The hard point-in-time rule is `constituent.available_at <= requested.as_of_utc`.
Future-available records are excluded before manifest construction and may be represented
only by sanitized quality evidence. A changed record, vintage, schema, adapter,
entitlement, configuration, as-of time, mapping, disposition, or finding changes the
snapshot hash and deterministic ID.

Persisted snapshot quality status is exactly `data_quality_accepted` or
`data_quality_accepted_with_warnings`. A blocked finding produces a nonpersisted
`SnapshotBuildBlockedResult`; no blocked snapshot row or manifest is persisted.

## Data-quality finding contract

Each finding carries lowercase severity `info`, `warning`, `error`, or `blocking`; frozen
rule-set version and rule ID; a closed `DataQualityCode`; affected record type and logical
identity; optional raw and normalized hashes and field; disposition `retained`, `excluded`,
or `blocked`; positive occurrence count, optional rate from zero through one, optional UTC
time range, and sanitized canonical JSON detail. The finding SHA-256 covers all of that
content except its own ID/hash, and its UUIDv5 ID derives from the finding hash. Blocking
severity requires blocked disposition. Secrets, URLs, and credential-shaped content are
rejected from detail.

## Adapter result and credential boundary

`AdapterResult` is a discriminator on `status`:

- `available` carries an adapter profile, one declared capability, and an immutable batch
  of raw observations, revisions, normalized observations, and quality findings;
- `unavailable` carries a typed reason (`credentials_unavailable`,
  `capability_unavailable`, `entitlement_unavailable`, or
  `configuration_unavailable`) plus sanitized provider, adapter/version, dataset, product,
  entitlement, and use-rights identities and a sanitized one-line message.

Every vendor-neutral adapter profile explicitly declares whether it is synthetic. Use-rights
scope distinguishes `internal_test_fixture_only` from the generic, provider-fact-free
`internal_research_only`; any real entitlement selection would require separate primary-source
verification. Phase 4 persistence accepts only `synthetic: true`, test-fixture-scoped,
storage-permitted profiles, while the adapter boundary can represent a credential-gated
non-synthetic profile returning `unavailable` before any persistence. The returned capability
must be declared by the adapter and every
normalized record must match that capability. Missing credentials must produce the typed
unavailable branch before transport construction or any network call. Transport and zero-call
spy behavior belong to the adapter implementation tests, not this contract unit.

No real provider is selected or implied by these decisions. The only frozen entitlement
assumption is for clearly labeled deterministic synthetic fixtures: internal test use,
storage, display, non-display, and derived-data use are allowed; redistribution is not.
There are no unverified current provider product, credential, licensing, or entitlement
claims in this record.

## API authority and known limitations

The public create request accepts only mapping ID, as-of UTC, requested capability, and
deterministic mock-configuration ID. Family, verdict, observations, provider results,
hashes, entitlements, timestamps, versions, and findings are server-resolved and are not
client-authoritative. Phase 4 APIs are create/read/list only.

For a persisted Family C mapping, the local synthetic adapter deterministically derives one
official metadata fixture record per exact server-resolved corroboration source-version UUID.
This keeps the synthetic evidence set equal to the immutable Phase 3 mapping without accepting
client-supplied corroboration identities. The committed standalone fixture retains a fixed UUID
only for isolated contract tests.

`PHASE4_SCHEMA_CONSTANTS` is the cross-layer export for migration and static parity tests.
It freezes schema/canonical/request/date versions and all lowercase capability, record,
severity, disposition, and persisted-quality-status vocabularies. Database code must
match it exactly rather than invent parallel uppercase values.

The implemented adapter, repository, migration, API route, generated TypeScript contract, and
end-to-end quality runner preserve this freeze. Synthetic datasets remain mock evidence; no real
market-data coverage or performance result is claimed.
