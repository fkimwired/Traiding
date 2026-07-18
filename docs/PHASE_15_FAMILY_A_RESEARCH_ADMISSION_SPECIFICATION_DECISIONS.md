# Phase 15 Family A research-admission specification decisions

## Accepted baseline and authority

Phase 15 starts only from the formally accepted Phase 14 identity:

- Commit: `513fdfd515599e59db6911441aadf1cc30f7352c`
- Tree: `5870fd4c112b7c7bee05f6240c5cbd950eeaff04`
- Windows full Phase 14 verifier: passed at that identity in 4,090.1 seconds.
- Ubuntu GitHub Actions run `29632035213`: `preflight`, `unit`, and
  `phase14-compose` passed at that same identity.

The user authorized implementation through Phase 15. This decision narrows that authority to the
smallest safe prerequisite for non-synthetic Family A research. It does not authorize Phase 16,
external capture, data ingestion, research execution, paper execution, or a live path.

## Decision

Phase 15 is a database-free, network-disabled, portable engineering specification. It freezes the
exact data, temporal, licensing, evaluation, risk, and audit requirements that a later separately
authorized phase must satisfy before non-synthetic Family A research data can be admitted. It also
freezes a closed gap ledger that distinguishes repository proof from missing external evidence.

Phase 15 does not contact a provider, load a credential, accept a dataset path, persist licensed
content, create a Phase 4 snapshot, modify an evaluation policy, run a strategy, calculate a return,
grant `PASS_RESEARCH`, promote a strategy, approve paper activity, clear risk, or create an order.
The committed JSON is a requirements document, not a research dataset or a readiness certificate.

The only outcomes are:

- `REQUIREMENTS_FROZEN`: all fifteen requirement rows are present in exact order with status `PASS`
  and reason `frozen_repository_requirement`, all nineteen gap rows are present in exact order with
  their frozen evidence states, every authority field has its required false/true value, and all
  canonical hashes reproduce.
- `BLOCKED`: one or more requirement rows are `BLOCKED` or `UNCOMPUTABLE`, or any required identity,
  order, state, authority field, canonical preimage, or hash is invalid.

`REQUIREMENTS_FROZEN` states only that the engineering contract is complete. It is not a positive
research-ingestion, data-rights, research-data-eligibility, performance, promotion, approval, risk,
execution, or order state. Gap rows remain truthful even when every requirement row passes.

## Frozen identities, versions, and canonicalization

The exact versions and hash domains are:

```text
artifact schema/hash domain: phase15-family-a-research-admission-specification-v1
requirement schema/hash domain: phase15-family-a-research-admission-requirement-v1
gap schema/hash domain: phase15-family-a-research-admission-gap-v1
policy id/hash domain: phase15-family-a-research-admission-policy-v1
requirements manifest hash domain: phase15-family-a-research-admission-requirements-manifest-v1
gaps manifest hash domain: phase15-family-a-research-admission-gaps-manifest-v1
evidence hash domain: phase15-family-a-research-admission-evidence-v1
artifact UUID namespace: e681ce4e-94fa-5b7a-bb12-ce17b509037b
```

The accepted Family A source specification is bound exactly as:

```text
specification_id: phase6-a_cross_sectional_equity_ranking-research-pipeline
specification_version: v2
specification_sha256: 3967b3c0dffd6a27c4ac8012773621090b828e8bdc2f242611c34d81420b37bc
```

The artifact binds the accepted Phase 14 commit/tree above and the fixed policy timestamp
`2026-07-18T00:00:00Z`. No runtime clock, random value, UUID4, environment variable, current Git
state, database value, network response, directory discovery, or machine-specific path may affect
its bytes.

Canonical JSON is UTF-8 with lexicographically sorted object keys, no insignificant whitespace,
stable array order, exact declared enum text, and one final newline on CLI stdout and the committed
file. Each requirement and gap hash covers its
complete canonical content except its own hash under its exact domain. The policy hash covers the
complete ordered policy content except its own hash. The artifact hash covers the complete artifact
except its own hash. Extra, duplicate, missing, reordered, or unknown fields and rows are rejected.

The committed output is:

```text
docs/PHASE_15_FAMILY_A_RESEARCH_ADMISSION_SPECIFICATION.json
```

## Exact requirement registry

Requirement statuses are exactly `PASS`, `BLOCKED`, and `UNCOMPUTABLE`. The committed artifact has
the following fifteen rows in this exact order, each with `PASS` and
`frozen_repository_requirement`:

1. `FAMILY_A_SPECIFICATION_IDENTITY_BOUND`
2. `SIGNAL_ACTION_AND_HORIZON_REQUIREMENTS_BOUND`
3. `POINT_IN_TIME_CAPABILITY_REQUIREMENTS_FROZEN`
4. `INSTRUMENT_IDENTITY_AVAILABILITY_POLICY_FROZEN`
5. `UNIVERSE_DELISTING_CORPORATE_ACTION_POLICY_FROZEN`
6. `FUNDAMENTAL_REVISION_LAG_POLICY_FROZEN`
7. `MACRO_SECTOR_LIQUIDITY_REQUIREMENTS_FROZEN`
8. `FULL_HISTORY_SAMPLE_BOUNDARIES_FROZEN`
9. `SNAPSHOT_CANONICALIZATION_AUDIT_POLICY_FROZEN`
10. `USE_RIGHTS_RETENTION_DERIVED_DATA_POLICY_FROZEN`
11. `WALK_FORWARD_PURGE_EMBARGO_HOLDOUT_POLICY_FROZEN`
12. `TRIAL_ACCOUNTING_DSR_PBO_LEAKAGE_POLICY_FROZEN`
13. `COST_SLIPPAGE_STRESS_REGIME_POLICY_FROZEN`
14. `RISK_REPRODUCIBILITY_POLICY_FROZEN`
15. `INGESTION_RESEARCH_PROMOTION_EXECUTION_AUTHORITY_ABSENT`

Their exact definitions in the same order are:

1. `Bind the immutable Family A specification identity, version, hash, and canonical family.`
2. `Freeze the deterministic research-score rule, server-owned action semantics, and two-session forecast horizon without creating a trade instruction.`
3. `Require the complete seven-capability Family A point-in-time input registry before any non-synthetic research run.`
4. `Require stable instrument, listing, ticker, exchange, sector, and availability histories with explicit validity intervals.`
5. `Require historical universe membership, inactive and delisted coverage, delisting-return semantics, and announcement-time corporate-action revisions.`
6. `Require as-reported fundamental vintages with release or accepted timestamps and no retroactive restatement overwrite.`
7. `Require point-in-time macro vintages, sector history, liquidity depth, and explicit missingness before dataset admission.`
8. `Require predeclared full-history coverage, sample boundaries, decision calendar, and computable sample-adequacy thresholds.`
9. `Require immutable raw and normalized lineage, canonical snapshot hashes, source versions, availability times, and audit identities.`
10. `Require independently reviewed current storage, retention, non-display, and derived-data rights with revocation semantics.`
11. `Freeze nested past-only walk-forward geometry, label-interval purge, explicit embargo applicability, and an untouched confirmation holdout.`
12. `Require complete trial accounting plus computable DSR, PBO, leakage, and promotion-gate inputs under a frozen policy.`
13. `Require market-calibrated baseline and stressed transaction-cost, slippage, liquidity, and regime policies before promotion.`
14. `Require computable risk limits and complete reproducibility fields including config hash, snapshot identity, git SHA, seed, trial count, and UTC time.`
15. `Keep ingestion, research execution, performance, promotion, approval, risk clearance, execution, and order authority absent from Phase 15.`

A `PASS` means only that the requirement is stated completely and hash-bound. It never converts a
gap from `MOCK_ONLY`, `MISSING`, `STALE`, or `UNPROVEN` to `PRESENT`.

## Exact current gap ledger

Gap states are exactly `PRESENT`, `MOCK_ONLY`, `STALE`, `MISSING`, and `UNPROVEN`. The committed
artifact freezes these nineteen rows in exact order:

| Ordinal | Gap code | State | Repository truth |
|---:|---|---|---|
| 1 | `FAMILY_A_SIGNAL_AND_HORIZON` | `MOCK_ONLY` | Family A has a deterministic mock research-score definition and two-session horizon, but no externally validated action rule. |
| 2 | `FULL_POINT_IN_TIME_DATASET` | `MISSING` | No complete licensed non-synthetic point-in-time Family A dataset is present. |
| 3 | `EXTERNAL_CANDIDATE_QUALIFICATION` | `UNPROVEN` | The fixed external candidate has not produced an authorized complete qualification artifact. |
| 4 | `HISTORICAL_MEMBERSHIP_AND_DELISTING` | `UNPROVEN` | Historical membership and delisting-return coverage remain unproven for an external dataset. |
| 5 | `SECTOR_LIQUIDITY_MACRO_HISTORY` | `MISSING` | Complete sector, liquidity-depth, and point-in-time macro history is missing. |
| 6 | `INDEPENDENT_CURRENT_USE_RIGHTS` | `MISSING` | No independently authenticated current use-rights decision is present. |
| 7 | `NON_SYNTHETIC_SNAPSHOT_PERSISTENCE` | `MISSING` | The accepted snapshot persistence path is synthetic-only and has no non-synthetic admission path. |
| 8 | `NON_SYNTHETIC_EVALUATION_POLICY` | `MISSING` | No approved non-synthetic evaluation policy freezes data-specific coverage and thresholds. |
| 9 | `NON_SYNTHETIC_EVALUATION_PATH` | `MISSING` | No non-synthetic dataset-to-evaluation workflow exists. |
| 10 | `PURGED_WALK_FORWARD_MECHANICS` | `MOCK_ONLY` | Purged nested walk-forward mechanics are proven only with deterministic mock evidence. |
| 11 | `EMBARGO_APPLICABILITY_DECISION` | `UNPROVEN` | Embargo is documented as inapplicable to strict past-only folds, but no non-synthetic policy decision is approved. |
| 12 | `LEAKAGE_FREE_RESULT` | `MOCK_ONLY` | Leakage-free results exist only for deterministic mock research evidence. |
| 13 | `MARKET_CALIBRATED_COST_SLIPPAGE` | `MOCK_ONLY` | Cost and slippage realism is calibrated only for deterministic mock evidence, not an external market dataset. |
| 14 | `DSR_PBO_PROMOTION_GATES` | `MOCK_ONLY` | DSR and PBO gates are mechanically proven only on deterministic mock research artifacts. |
| 15 | `PHASE_15_IMPLEMENTATION_AUTHORITY` | `PRESENT` | The user has explicitly authorized implementation through Phase 15. |
| 16 | `DATA_RIGHTS_AND_RESEARCH_AUTHORITY` | `MISSING` | Data-rights evidence does not grant research ingestion or research-run authority. |
| 17 | `RIGHTS_CURRENTNESS_REVOCATION` | `MISSING` | No current rights-revocation and revalidation evidence exists for a non-synthetic dataset. |
| 18 | `PRE_ORDER_RISK` | `MOCK_ONLY` | Pre-order risk mechanics are mock-only and cannot authorize ingestion, research, or an order. |
| 19 | `IMMUTABLE_AUDIT_SCHEMA` | `PRESENT` | The repository has immutable hash-bound audit schemas that Phase 15 must preserve. |

No gap is silently upgraded because a requirement is complete, a file hashes correctly, or a mock
test passes. `STALE` remains part of the closed vocabulary for adversarial verification even though
the frozen current ledger contains no stale row.

## Walk-forward and embargo boundary

The Family A synthetic specification uses expanding past-only folds and declares no embargo. Phase 15
does not promote that synthetic geometry to a non-synthetic policy. It freezes the governing rule:

- a future approved strictly past-only design has no post-test training segment and must explicitly
  record embargo as inapplicable; and
- a future approved CPCV, purged K-fold, or other design allowing later observations in training must
  freeze a positive embargo duration before any holdout is opened.

The current `EMBARGO_APPLICABILITY_DECISION` gap stays `UNPROVEN` until the complete non-synthetic
evaluation policy is separately approved. Phase 15 opens no confirmation interval and consumes no
holdout.

## Authority invariants

Every artifact fixes these fields to false:

```text
external_request_performed
external_data_capture_authorized
provider_payload_persisted
licensed_data_persisted
research_ingestion_authorized
research_snapshot_created
research_data_eligible
research_run_created
research_run_authorized
research_executed
performance_computed
pass_research_granted
strategy_promotion_authorized
paper_approval_granted
risk_clearance_granted
strategy_execution_eligible
execution_authorized
order_submission_authorized
```

Every artifact fixes these fields to true:

```text
live_path_absent
no_personalized_investment_advice
no_real_performance_claimed
```

Any authority-field drift is invalid input and must never be represented as a second positive state.

## Generator and verifier boundary

The sole generator invocation is:

```text
python scripts/generate_family_a_research_admission_specification.py \
  --confirm-requirements-only
```

It accepts no provider, URL, host, path, symbol, date, credential, right, entitlement, data location,
output path, strategy parameter, feature, threshold, action, side, quantity, price, allocation,
broker, retry, execution, ingestion, promotion, clock, seed, or arbitrary hash. It writes only the
canonical artifact plus one final newline to stdout. Repeated invocations are byte-identical.

The sole verifier invocation is:

```text
python scripts/verify_family_a_research_admission_specification.py \
  --specification PATH
```

It reads one regular UTF-8 JSON file of at most 512 KiB, rejects a BOM, duplicate keys, floats,
non-finite values, non-object roots, symbolic/non-regular files, and non-canonical bytes, validates
strict contract/canonical/hash parity against the frozen implementation, and writes deterministic
sanitized success JSON only after complete validation. It has no expected-hash override and accepts
no authority or repair option. Invalid input and invalid invocation exit 2 with no stdout and exact
generic stderr `Family A research-admission specification verification failed.` Generator failures
use `Family A research-admission specification generation failed.` Help exits 0.

Both commands are database-free and deny network, subprocess, provider, credential, worker, queue,
retry, broker, research, and execution dependencies. Import or runtime attempts to reach those
surfaces are acceptance failures.

## Persistence, API, and inherited-code boundary

Phase 15 adds no migration, table, SQL function, trigger, database row, API route, Pydantic API
response, OpenAPI path, or generated TypeScript contract. Alembic head remains `0011_phase14`, every
inherited migration remains byte-identical, and the complete inherited Phase 1-14 table/function
catalog must remain unchanged through acceptance.

Phase 15 does not modify the accepted Phase 4 snapshot workflow, Phase 5 evaluation engine, Phase 6
research workflow, Phase 7 governance/risk workflow, Phase 10/11 local simulation evidence, Phase 12
paper readiness, Phase 13 qualification, or Phase 14 eligibility implementation.

## Explicit exclusions

Phase 15 adds no external capture, provider adapter, generic or fixed transport, credential, secret,
rights assertion, entitlement proof, licensed payload, local dataset-file import, observation,
normalization, quarantine, research ingestion, snapshot, feature, label, signal, model, trial,
backtest, return, metric, DSR/PBO result, cost calibration, performance claim, promotion, approval,
revocation, risk mutation, account, quote, position, intent, broker, order, fill, reconciliation,
scheduler, worker, queue, retry, WebSocket, live enum/origin/path, frontend product control,
dependency, Compose change, migration, API route, generated contract change, publication, deployment,
release, tag, PR, or later-phase scaffold.

## Failure and acceptance semantics

Missing, duplicate, reordered, unknown, or extra requirement/gap rows; invalid states; a changed
Family A identity; baseline, version, policy, authority, timestamp, reason, evidence, or hash drift;
non-canonical JSON; extra model fields; nondeterministic output; database access; a network or
subprocess attempt; or secret/licensed-data canary leakage fails closed. No repair, retry, fallback,
or partial-success artifact is allowed.

Acceptance requires generated-file parity, deterministic generator/verifier bytes, complete and
blocked/adversarial proofs, active socket denial, secret and licensed-data canaries, no schema/API/
contract drift, zero database writes, inherited browser regressions, exact repository identity, and
complete acceptance-resource cleanup on Windows and Ubuntu at one committed SHA/tree.

Stop after Phase 15 same-SHA acceptance. Do not contact a provider, create credentials, ingest data,
generalize the research engine, run or promote a strategy, modify governance/risk state, add an order
path, or begin a later phase.
