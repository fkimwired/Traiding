# Phase 16 Family A point-in-time source-plan decisions

## Accepted baseline and authority

Phase 16 starts only from the formally accepted Phase 15 identity:

- Commit: `5b3052eb8f020d77cc3750b34190b4b2fa5fc16c`
- Tree: `7fab5a2b2eb2f8f821b969d9cb031c806e064d28`
- Phase 15 artifact id: `c29b8139-da80-556b-b150-a5ca9603d265`
- Phase 15 artifact SHA-256: `575ce4c51e9102790d75edc4a330c3e9f1d9eb505eb33ccf22d8a9c9e50200d6`
- Phase 15 gaps-manifest SHA-256: `9c70f11f85eb66dad6eed15a0a4907dec3fa4edc7b0da3d6adbad768b88b2f86`
- Windows full Phase 15 verifier: passed at that identity with an empty post-cleanup
  resource namespace and the same clean SHA/tree.
- Ubuntu GitHub Actions run `29661065413`: `preflight`, `unit`, and
  `phase15-compose` passed at that same identity.

The user separately authorized implementation of the next phase. This decision narrows that
authority to Phase 16 only and to the smallest safe prerequisite before any non-synthetic data
access: a portable source plan. It does not authorize a credential, provider request, source
selection, licensed payload, data capture, ingestion, snapshot, evaluation-policy approval, holdout,
research run, performance result, promotion, risk decision, paper order, or live path.

## Decision

Phase 16 is a deterministic, database-free, network-disabled Family A point-in-time source plan. It
turns the provider-neutral Phase 15 requirements into a closed sequence for identifying candidate
products, reviewing rights, qualifying bounded read-only samples, proving full-history coverage,
reconciling temporal semantics, and designing a later quarantine/canonical-snapshot boundary.

The plan records candidate-only official facts. It does not select or approve a source and cannot
verify an entitlement, commercial product scope, schema, historical coverage, data quality, or use
right. A provider document, public API description, token, Phase 13 sample hash, Phase 15 artifact
hash, or completed plan row is never research-data eligibility.

The only outcomes are:

- `PLAN_FROZEN`: the exact requirements, capabilities, candidate-only facts, seven future steps,
  unchanged Phase 15 gap bindings, authority fields, and canonical hashes are complete.
- `BLOCKED`: one or more plan requirements are `BLOCKED` or `UNCOMPUTABLE`, or an identity, order,
  candidate fact, capability mapping, gap binding, step, authority field, canonical preimage, or hash
  is invalid.

`PLAN_FROZEN` means only that an acquisition and qualification plan is complete. It is not a source
selection, procurement decision, contract review, entitlement, external qualification, data-admission
decision, evaluation-policy approval, research authorization, or execution authority. Every future
step remains `NOT_STARTED`, and every Phase 15 gap retains its accepted state.

## Frozen identities and canonicalization

Use these exact schema and policy identities:

```text
artifact: phase16-family-a-point-in-time-source-plan-v1
policy: phase16-family-a-point-in-time-source-plan-policy-v1
requirement: phase16-family-a-point-in-time-source-plan-requirement-v1
capability: phase16-family-a-point-in-time-source-plan-capability-v1
candidate: phase16-family-a-point-in-time-source-plan-candidate-v1
step: phase16-family-a-point-in-time-source-plan-step-v1
Phase 15 gap binding: phase16-family-a-point-in-time-source-plan-gap-binding-v1
requirements manifest: phase16-source-plan-requirements-manifest-v1
capabilities manifest: phase16-source-plan-capabilities-manifest-v1
candidates manifest: phase16-source-plan-candidates-manifest-v1
steps manifest: phase16-source-plan-steps-manifest-v1
gap-bindings manifest: phase16-source-plan-gap-bindings-manifest-v1
evidence: phase16-source-plan-evidence-v1
artifact UUID namespace: 657156b0-345e-5d6e-ae1b-1f27e32b40ac
fixed timestamp: 2026-07-18T00:00:00Z
```

The artifact binds the accepted Phase 15 commit, tree, artifact id, artifact hash, and gaps-manifest
hash above. No runtime clock, random value, UUID4, environment value, current Git state, database
value, network response, directory discovery, or machine-specific path may affect its bytes.

Canonical JSON is UTF-8 with lexicographically sorted object keys, stable array order, exact enum
text, no insignificant whitespace, and one final newline on CLI stdout and the committed file. Every
row and manifest hash covers its complete canonical content except its own hash under its declared
domain. The artifact hash covers the complete artifact except its own hash. Extra, duplicate,
missing, reordered, or unknown fields and rows are invalid.

The committed output is:

```text
docs/PHASE_16_FAMILY_A_POINT_IN_TIME_SOURCE_PLAN.json
artifact id: e106a766-5cfe-5a1c-94f6-ee1c2ac68652
artifact SHA-256: 74ddf4a51d722b494fd494241e2e5927bff6fde034f6932dcfd791bb3a0706bb
policy SHA-256: 57cfcfd09f2d4a87d9562fd536228b9f05693bb71b7e9d1867618a35da7d4efd
canonical size: 22,776 bytes
```

## Exact requirement registry

Requirement statuses are exactly `PASS`, `BLOCKED`, and `UNCOMPUTABLE`. The complete plan contains
these twelve requirements in this exact order:

1. `PHASE15_ADMISSION_SPECIFICATION_BOUND`
2. `FAMILY_A_CAPABILITY_SET_BOUND`
3. `SECURITY_MASTER_IDENTITY_HISTORY_REQUIRED`
4. `UNIVERSE_MEMBERSHIP_DELISTING_HISTORY_REQUIRED`
5. `RAW_OHLCV_CORPORATE_ACTION_HISTORY_REQUIRED`
6. `AS_REPORTED_FUNDAMENTAL_VINTAGES_REQUIRED`
7. `SECTOR_LIQUIDITY_HISTORY_REQUIRED`
8. `MACRO_VINTAGE_RELEASE_HISTORY_REQUIRED`
9. `TEMPORAL_REVISION_COVERAGE_MANIFEST_REQUIRED`
10. `INDEPENDENT_RIGHTS_CURRENTNESS_REVIEW_REQUIRED`
11. `QUARANTINE_CANONICALIZATION_RECONCILIATION_REQUIRED`
12. `CAPTURE_INGESTION_RESEARCH_EXECUTION_AUTHORITY_ABSENT`

Their definitions, in the same order, are:

1. `Bind the accepted Phase 15 admission specification and its complete unchanged gap ledger.`
2. `Bind the exact seven Family A point-in-time capabilities without selecting a source.`
3. `Require stable security, listing, ticker, exchange, and sector identity histories.`
4. `Require point-in-time membership, inactive coverage, delisting events, and delisting returns.`
5. `Require raw OHLCV plus separately auditable announcement-time corporate-action history.`
6. `Require as-reported fundamental vintages, release timestamps, amendments, and revisions.`
7. `Require point-in-time sector classification and market-calibrated liquidity-depth history.`
8. `Require macro vintages with release availability and revision history.`
9. `Require full-history boundaries, temporal fields, revision semantics, and coverage manifests.`
10. `Require independently reviewed current rights, retention scope, and revocation evidence.`
11. `Require local quarantine, deterministic canonicalization, lineage, and reconciliation design.`
12. `Keep source selection, capture, ingestion, research, promotion, risk, execution, and orders absent.`

A `PASS` means only that the plan requirement is stated completely and hash-bound. It does not prove
that a candidate, product, schema, dataset, right, reviewer, or future step exists.

## Exact capability registry

The capability registry is exactly:

1. `security_master`
2. `universe_membership`
3. `ohlcv`
4. `corporate_actions`
5. `delistings`
6. `as_reported_fundamentals`
7. `macro_regime_inputs`

Every capability is required and has `source_selected=false`. Candidate references are planning
evidence only; no capability is qualified or data-admissible. Point-in-time sector history and
liquidity depth remain explicit missing requirements and are not inferred from another capability or
candidate.

## Exact candidate-only registry

The candidate registry and frozen evidence states are exactly:

```text
TIINGO_PHASE13_BOUNDED_CANDIDATE                         UNPROVEN
MORNINGSTAR_CRSP_US_STOCK_DATABASES_CANDIDATE           UNPROVEN
MORNINGSTAR_CRSP_COMPUSTAT_MERGED_DATABASE_CANDIDATE    UNPROVEN
SEC_EDGAR_SUBMISSIONS_XBRL_CANDIDATE                    UNPROVEN
FEDERAL_RESERVE_ALFRED_VINTAGES_CANDIDATE               UNPROVEN
HISTORICAL_LIQUIDITY_PRODUCT_UNSELECTED                 MISSING
```

Every row has `candidate_only=true`, `selected=false`, `rights_verified=false`, and
`external_verification_performed=false`. The official facts are narrowly limited to:

- Phase 13 already names Tiingo as a bounded candidate and records no authorized external
  qualification. That historical candidate identity does not select a Phase 16 product or prove
  complete Family A coverage.
- Morningstar completed its acquisition of CRSP and announced migration of CRSP research-data
  products. The US Stock Databases and CRSP/Compustat Merged Database names are candidate references
  only. They do not prove which product Fable5 could obtain, its delivery method, schemas, current
  availability, complete history, entitlement, or permitted use.
- Official SEC EDGAR surfaces expose submissions and XBRL JSON with accession and accepted-time
  semantics. That does not prove a complete normalized as-reported fundamental history, issuer/
  security reconciliation, retention/display/derived-data rights for all linked content, or fitness
  for Family A.
- Federal Reserve documentation describes real-time periods and ALFRED/vintage-date semantics. API
  access, third-party series
  rights, full release-time history, exact regime-series coverage, and permitted storage/use remain
  unproven.
- No historical liquidity product has been selected or documented; that candidate slot remains
  `MISSING`.

No candidate has a selected product id, accepted schema version, rights-review id, credential,
endpoint configuration, approved coverage manifest, or data location. Candidate order is not a
ranking or recommendation.

The public candidate facts above were checked only against official documentation: CRSP's
[research-product catalog](https://www.crsp.org/research/) and
[Morningstar migration notice](https://www.crsp.org/introducing-the-new-home-for-crsp-research-data-products/),
the SEC's [EDGAR API documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces),
and the Federal Reserve Bank of St. Louis [FRED/ALFRED API overview](https://fred.stlouisfed.org/docs/api/fred/overview.html).
These links are provenance for names and documented surfaces only; they are not entitlement,
current-use-rights, coverage, quality, schema, retention, or availability evidence.

## Exact future-step registry

Every step has state `NOT_STARTED`. The exact code, prerequisite codes, and required future output
hash names are:

| Ordinal | Step | Step prerequisites | Required prior evidence | Required future output hashes |
|---:|---|---|---|---|
| 1 | `SELECT_CANDIDATE_PRODUCTS` | none | none | `candidate_product_inventory_sha256` |
| 2 | `REVIEW_CURRENT_USE_RIGHTS` | `SELECT_CANDIDATE_PRODUCTS` | none | `independent_rights_review_sha256`, `rights_currentness_sha256` |
| 3 | `QUALIFY_BOUNDED_READ_ONLY_SAMPLES` | steps 1-2 | `non_synthetic_evaluation_policy_sha256`, `confirmation_holdout_definition_sha256` | `qualification_artifact_set_sha256` |
| 4 | `PRODUCE_FULL_HISTORY_COVERAGE_MANIFEST` | step 3 | none | `full_history_coverage_manifest_sha256` |
| 5 | `RECONCILE_TEMPORAL_IDENTITY_REVISION_SEMANTICS` | step 4 | none | `temporal_identity_revision_reconciliation_sha256` |
| 6 | `DESIGN_LOCAL_QUARANTINE_AND_CANONICAL_SNAPSHOT` | steps 2 and 5 | none | `quarantine_canonical_snapshot_design_sha256` |
| 7 | `REQUEST_SEPARATE_INGESTION_AUTHORITY` | step 6 | none | `separate_ingestion_authority_evidence_sha256` |

Their exact definitions, in the same order, are:

1. `Select exact candidate products only after separately authorized current documentation review.`
2. `Obtain independent current storage, non-display, derived-data, retention, and revocation review.`
3. `Only after a complete non-synthetic evaluation policy and untouched confirmation holdout definition are hash-frozen, run separately authorized bounded read-only qualification without treating a sample as a dataset.`
4. `Produce a complete point-in-time history and missingness manifest for every required capability.`
5. `Reconcile stable identity, availability, revision, corporate-action, and delisting semantics.`
6. `Design rights-gated local quarantine and canonical snapshot behavior before any ingestion.`
7. `Request separate authority only after every prior evidence output is complete and current.`

Later completion of one step cannot skip, imply, or authorize another. Product selection and rights
review must precede any separately authorized external sample. A complete data-specific evaluation
policy, explicit embargo applicability, and untouched confirmation interval must be frozen after the
source/product metadata is known but before any admitted observations or holdout are opened.

## Exact Phase 15 gap bindings

Phase 16 copies and hash-binds these accepted states without modifying them:

```text
FAMILY_A_SIGNAL_AND_HORIZON                 MOCK_ONLY
FULL_POINT_IN_TIME_DATASET                  MISSING
EXTERNAL_CANDIDATE_QUALIFICATION            UNPROVEN
HISTORICAL_MEMBERSHIP_AND_DELISTING         UNPROVEN
SECTOR_LIQUIDITY_MACRO_HISTORY              MISSING
INDEPENDENT_CURRENT_USE_RIGHTS               MISSING
NON_SYNTHETIC_SNAPSHOT_PERSISTENCE           MISSING
NON_SYNTHETIC_EVALUATION_POLICY              MISSING
NON_SYNTHETIC_EVALUATION_PATH                MISSING
PURGED_WALK_FORWARD_MECHANICS                MOCK_ONLY
EMBARGO_APPLICABILITY_DECISION               UNPROVEN
LEAKAGE_FREE_RESULT                          MOCK_ONLY
MARKET_CALIBRATED_COST_SLIPPAGE              MOCK_ONLY
DSR_PBO_PROMOTION_GATES                      MOCK_ONLY
PHASE_15_IMPLEMENTATION_AUTHORITY            PRESENT
DATA_RIGHTS_AND_RESEARCH_AUTHORITY           MISSING
RIGHTS_CURRENTNESS_REVOCATION                MISSING
PRE_ORDER_RISK                               MOCK_ONLY
IMMUTABLE_AUDIT_SCHEMA                       PRESENT
```

Plan completeness, a public documentation fact, or a valid hash must not upgrade a gap. Phase 16
does not amend the Phase 15 artifact.

## Evaluation-policy sequencing

Phase 16 does not freeze a non-synthetic evaluation policy. A complete policy requires the exact
selected products, schemas, history/calendar coverage, availability and missingness semantics,
confirmation interval, fee/spread/impact/borrow calibration sources and vintages, regimes, sample
adequacy, and appropriate limits. Those facts are not currently present.

Reusing Phase 5/6 synthetic thresholds would be a false upgrade. Choosing an embargo rule without a
complete data-specific policy would leave the Phase 15 applicability gap unproven. The safe sequence
is therefore:

1. freeze this metadata-only source plan;
2. separately select exact products and obtain independent current rights review;
3. freeze the complete non-synthetic evaluation policy before observing admitted data or opening a
   holdout;
4. separately authorize bounded external qualification;
5. separately authorize quarantine/admission and canonical snapshot creation; and
6. only after every preceding gate passes, separately consider a non-synthetic research run.

## Authority and security invariants

The artifact records no selected source and no positive external authority. It must keep external
requests, credentials, provider payload persistence, licensed-data persistence, data capture,
ingestion, snapshot creation, data eligibility, evaluation-policy approval, holdout opening, research
creation/authorization/execution, performance, `PASS_RESEARCH`, promotion, paper approval, risk
clearance, execution, and order submission false. It keeps the live path absent and makes no advice
or real-performance claim.

No environment variable, local secret, entitlement document, contract text, provider body,
observation value, account, order, feature, label, return, or metric enters the artifact, logs,
errors, repository, build output, CI evidence, or temporary output.

## Persistence, API, and inherited-code boundary

Phase 16 adds no migration, table, SQL function, trigger, database row, API route, Pydantic API model,
OpenAPI path, generated TypeScript contract, frontend product control, dependency, Compose service,
provider adapter, transport, worker, queue, or retry mechanism. Alembic head remains
`0011_phase14`. All 57 inherited tables/functions, every earlier row, OpenAPI, generated contract,
and accepted production implementation remain unchanged.

The portable implementation belongs under `services/data/src/fable5_data/phase16` and may perform
only pure canonical construction. The generator emits the plan to stdout only. The verifier reads
one bounded regular canonical JSON file and emits only deterministic sanitized success evidence.

The sole generator confirmation is `--confirm-plan-only`; invalid invocation exits 2 with no stdout
and exact stderr `Family A point-in-time source-plan generation failed.` The sole verifier input is
`--plan PATH`; it accepts one regular UTF-8 canonical JSON file of at most 512 KiB and rejects a BOM,
duplicate keys, floats, non-finite values, non-object roots, symbolic/non-regular files, and
non-canonical bytes. Invalid verification exits 2 with no stdout and exact stderr
`Family A point-in-time source-plan verification failed.` Both commands deny database, network,
subprocess, credential, provider, research, broker, and execution dependencies.

## Explicit exclusions

Phase 16 adds no credential, secret, arbitrary provider/product/URL/path input, network call, vendor
SDK, external capture, entitlement assertion, contract ingestion, licensed payload, observation,
local dataset import, normalization execution, quarantine execution, data admission, snapshot,
evaluation threshold, embargo decision, holdout, feature, label, signal, trial, backtest, return,
metric, cost calibration, performance claim, promotion, approval, revocation mutation, risk mutation,
account, quote, position, intent, broker, order, fill, reconciliation, scheduler, asynchronous work,
live enum/origin/path, publication, deployment, release, tag, PR, or later-phase scaffold.

## Failure and acceptance semantics

Missing, duplicate, reordered, unknown, or extra rows; a changed Phase 15 identity or gap state;
candidate selection; optimistic rights/coverage claims; completed future steps; authority drift;
non-canonical JSON; nondeterminism; database/network/subprocess access; or secret/licensed-data canary
leakage fails closed. No repair, fallback, retry, partial-success plan, or operator override exists.

Acceptance requires deterministic generated-file parity, complete/blocked and adversarial tamper
proofs, active network and database denial, exact unchanged Phase 15 gap bindings, no schema/API/
contract drift, zero database writes, inherited browser regressions at their stage-local migration
heads, exact repository identity, and complete Windows/Ubuntu cleanup at one committed SHA/tree.

Stop after Phase 16 same-SHA acceptance. Do not select a source, load a credential, contact a
provider, capture or ingest data, freeze an incomplete evaluation policy, open a holdout, run or
promote research, modify governance/risk, add an order path, or begin Phase 17.
