# Phase 19 Family A Step 3 prerequisite-assessment decisions

## Accepted baseline and authority

Phase 19 starts only from the formally accepted Phase 18 identity:

- Commit: `16aac187fc3dbd6015306603c18be6e08cea8e4e`
- Tree: `b36ae615f13f39d0e661f18d1cc61e009b1aacf7`
- Phase 18 artifact id: `7008240c-e7a2-5d4b-9345-8c40d2d4c359`
- Phase 18 artifact SHA-256:
  `2def399ee8c57d7c6d80f5282e856eda1acf34a8504058fbfc8ea2dea4aa30ae`
- Phase 18 policy SHA-256:
  `e175f9b70333899b8c9626e459f091ea5c440494e006c2684448fa15fe0a4fbb`
- Phase 18 steps-manifest SHA-256:
  `581ff73113eff3c2d54728106df556734084c053f8e52f0f4a9e6928d7478167`
- Windows full Phase 18 verifier passed at that identity in 4,323.8 seconds with clean
  post-cleanup repository and resource state.
- Ubuntu GitHub Actions run `29698090468`: `preflight`, `unit`, and
  `phase18-compose` passed at that identical identity.

The user separately authorized Phase 19. This decision narrows that authority to one portable,
read-only assessment of whether the two prior-evidence hashes required before Phase 16 Step 3 exist.
It does not authorize Phase 16 Step 3, Phase 20, an external request, a credential, data access,
policy invention, holdout selection or opening, research, performance, promotion, execution, or an
order.

## Decision

Phase 19 is a deterministic, database-free, network-disabled prerequisite assessment. It binds the
accepted Phase 18 lineage and the repository's existing Phase 5 and Phase 15-18 evidence, then
truthfully records that both required Phase 16 Step 3 inputs are still absent:

```text
non_synthetic_evaluation_policy_sha256       MISSING
confirmation_holdout_definition_sha256       MISSING
```

Those exact names identify missing future evidence. Phase 19 never emits either hash as a value,
never substitutes a requirements hash, policy-template hash, protocol hash, synthetic policy hash,
or artifact hash for either one, and never marks the evidence present.

The exact successful domain result is:

```text
outcome:             BLOCKED
assessment_state:    OUTPUT_FROZEN
conclusion:          BLOCKED_MISSING_EVALUATION_POLICY_AND_HOLDOUT
```

`OUTPUT_FROZEN` means only that the blocked assessment bytes and hashes reproduce. It is not the
`OUTPUT_FROZEN` completion of a Phase 16 source-plan step, a non-synthetic evaluation-policy
approval, a holdout definition, data eligibility, or authority to begin bounded qualification.

## Why a complete policy cannot be frozen now

The existing Phase 5 implementation proves mechanics using deterministic synthetic evidence. Its
registered policy is explicitly `synthetic_fixture_policy=true`; its dates, fold sizes, thresholds,
fees, spreads, impact calibration, borrow inputs, regimes, and risk limits are fixture values. They
must not be relabeled or copied as a non-synthetic policy.

A complete non-synthetic Family A policy requires facts that Phase 18 does not provide: an
operationally selected product set and exact schemas, current executed rights, full history and
decision-calendar coverage, availability and missingness semantics, exact sample boundaries, an
untouched confirmation interval, market-calibrated fee/spread/impact/latency/borrow sources and
vintages, regime inputs, sample-adequacy thresholds, promotion thresholds, and appropriate risk
limits. Phase 18 instead ended with `BLOCKED_NO_OPERATIONAL_SELECTION`.

Likewise, the repository defines the holdout safety protocol but no non-synthetic holdout. A valid
definition must bind an approved exact contiguous interval and decision calendar before any admitted
observation is inspected. It must remain label-blind, excluded from feature, model, threshold, and
narrative selection, and single-use. Because no exact interval/calendar is approved, Phase 19 cannot
truthfully produce `confirmation_holdout_definition_sha256` or set either
`confirmation_holdout_defined` or `confirmation_holdout_opened` true.

## Repository methodology assessment

The assessment classifies repository evidence without upgrading it:

| Area | Repository evidence | Phase 19 finding |
|---|---|---|
| Signal and horizon | Family A has six named point-in-time features, research-score-only semantics, and a two-session horizon in the synthetic Phase 6 specification. | `MOCK_ONLY`; no externally validated deterministic action rule exists. |
| Point-in-time data | Seven required capability contracts and temporal rules are frozen. | `MISSING`/`UNPROVEN`; no complete licensed non-synthetic dataset, selected schema, or coverage proof exists. |
| Walk-forward and purge | Nested chronological mechanics purge actual overlapping label intervals and are adversarially tested. | `MOCK_ONLY` for non-synthetic research. |
| Embargo | Strict past-only folds correctly have no post-test embargo; combinatorial designs apply a positive configured embargo to later training rows. | `UNPROVEN`; no complete non-synthetic policy chooses the applicable geometry. |
| Preprocessing | Fold-scoped `fit(train)`/`transform(other)` behavior, exact train ids, and L06 blocking are implemented. | Mechanics are synthetic proof only; no non-synthetic fit or result exists. |
| Trial registry | `M_raw` includes every selection-influencing completed, failed, abandoned, and no-return trial; `N_eff` and lineage are immutable. | Definition/mechanics exist, but no non-synthetic trial registry or trial set exists. |
| DSR and PBO | Reproducible formula/input and fail-closed mechanics exist. | `MOCK_ONLY`; synthetic `0.50`/`0.25` thresholds and synthetic results are not reusable. |
| Costs and slippage | Baseline component ledgers, at-least-two-times all-cost stress, and independent liquidity stress are implemented. | `MOCK_ONLY`; no market-calibrated fee, spread, impact, latency, ADV, borrow, or venue vintage exists. |
| Leakage | L01-L06 and related point-in-time/data-quality checks fail closed. | The only leakage-free result is synthetic. |
| Sample, regime, and risk limits | Required policy fields and gate mechanics exist. | Data-specific boundaries, adequacy, regimes, and limits are missing or unproven. |
| Confirmation holdout | Synthetic label-blind exclusion and single-use semantics are implemented. | No exact non-synthetic interval/calendar is defined or opened. |
| Audit | Config, policy, snapshot, Git SHA, seed, raw/effective trial counts, UTC time, and parent lineage are immutable requirements. | `PRESENT` as schema requirements; no non-synthetic result is implied. |

Phase 19 may freeze these findings and the existing safety requirements. It must not create a signal,
feature weight, action, allocation, threshold, fold boundary, cost calibration, performance number,
or holdout date.

## Exact prerequisite registry

Prerequisite categories are exactly `EVALUATION_POLICY` and `CONFIRMATION_HOLDOUT`. Evidence states
are exactly `PRESENT`, `MOCK_ONLY`, `MISSING`, and `UNPROVEN`. The artifact carries these nineteen
rows in this order; only the audit-schema row is satisfied, and that row does not satisfy either
Step 3 prior-evidence requirement:

| Ordinal | Category | Code | State | Satisfied | Reason |
|---:|---|---|---|---|---|
| 1 | `EVALUATION_POLICY` | `OPERATIONAL_SOURCE_PRODUCT_COMPOSITION` | `MISSING` | false | `phase18_no_operational_selection` |
| 2 | `EVALUATION_POLICY` | `CURRENT_EXECUTED_USE_RIGHTS_AND_REVOCATION` | `MISSING` | false | `phase18_rights_review_blocked` |
| 3 | `EVALUATION_POLICY` | `EXACT_DELIVERY_AND_SCHEMA_VERSIONS` | `UNPROVEN` | false | `delivery_and_schema_unproven` |
| 4 | `EVALUATION_POLICY` | `FULL_POINT_IN_TIME_COVERAGE_AND_MISSINGNESS` | `MISSING` | false | `non_synthetic_dataset_missing` |
| 5 | `EVALUATION_POLICY` | `SIGNAL_ACTION_LABEL_AND_HORIZON` | `MOCK_ONLY` | false | `signal_and_horizon_mock_only` |
| 6 | `EVALUATION_POLICY` | `DECISION_CALENDAR_SAMPLE_BOUNDARIES_AND_ADEQUACY` | `MISSING` | false | `data_specific_geometry_missing` |
| 7 | `EVALUATION_POLICY` | `PURGED_WALK_FORWARD_MECHANICS` | `MOCK_ONLY` | false | `walk_forward_mechanics_mock_only` |
| 8 | `EVALUATION_POLICY` | `EMBARGO_APPLICABILITY` | `UNPROVEN` | false | `embargo_applicability_unproven` |
| 9 | `EVALUATION_POLICY` | `COMPLETE_TRIAL_ACCOUNTING_DSR_PBO_POLICY` | `MOCK_ONLY` | false | `trial_dsr_pbo_policy_mock_only` |
| 10 | `EVALUATION_POLICY` | `LEAKAGE_AND_DATA_QUALITY_GATES` | `MOCK_ONLY` | false | `leakage_gates_mock_only` |
| 11 | `EVALUATION_POLICY` | `MARKET_CALIBRATED_COST_SLIPPAGE_CAPACITY` | `MOCK_ONLY` | false | `cost_slippage_calibration_mock_only` |
| 12 | `EVALUATION_POLICY` | `STRESS_REGIME_CRISIS_THRESHOLDS` | `MOCK_ONLY` | false | `stress_and_regime_policy_mock_only` |
| 13 | `EVALUATION_POLICY` | `COMPUTABLE_DATA_SPECIFIC_RISK_LIMITS` | `MOCK_ONLY` | false | `risk_limits_mock_only` |
| 14 | `EVALUATION_POLICY` | `REPRODUCIBILITY_AUDIT_SCHEMA` | `PRESENT` | true | `audit_schema_present_only` |
| 15 | `EVALUATION_POLICY` | `NON_SYNTHETIC_EVALUATION_POLICY` | `MISSING` | false | `evaluation_policy_hash_missing` |
| 16 | `CONFIRMATION_HOLDOUT` | `SOURCE_BOUND_CONTIGUOUS_CONFIRMATION_INTERVAL` | `MISSING` | false | `confirmation_interval_missing` |
| 17 | `CONFIRMATION_HOLDOUT` | `HOLDOUT_DECISION_CALENDAR_AND_LABEL_BOUNDARIES` | `MISSING` | false | `holdout_calendar_and_boundaries_missing` |
| 18 | `CONFIRMATION_HOLDOUT` | `HOLDOUT_EXCLUSION_CONSUMPTION_AND_REPLACEMENT_RULES` | `MOCK_ONLY` | false | `holdout_rules_mock_only` |
| 19 | `CONFIRMATION_HOLDOUT` | `UNTOUCHED_CONFIRMATION_HOLDOUT_DEFINITION` | `MISSING` | false | `confirmation_holdout_hash_missing` |

The required-evidence registry has exactly two rows, both `MISSING`, `produced=false`, and without a
value/hash field in their schema:

| Name | Reason |
|---|---|
| `non_synthetic_evaluation_policy_sha256` | `complete_non_synthetic_evaluation_policy_not_created` |
| `confirmation_holdout_definition_sha256` | `untouched_confirmation_holdout_definition_not_created` |

## Phase 15 gap and Phase 16 step preservation

All nineteen accepted Phase 15 gap states remain exact and unchanged:

```text
FAMILY_A_SIGNAL_AND_HORIZON                 MOCK_ONLY
FULL_POINT_IN_TIME_DATASET                  MISSING
EXTERNAL_CANDIDATE_QUALIFICATION            UNPROVEN
HISTORICAL_MEMBERSHIP_AND_DELISTING         UNPROVEN
SECTOR_LIQUIDITY_MACRO_HISTORY              MISSING
INDEPENDENT_CURRENT_USE_RIGHTS              MISSING
NON_SYNTHETIC_SNAPSHOT_PERSISTENCE          MISSING
NON_SYNTHETIC_EVALUATION_POLICY             MISSING
NON_SYNTHETIC_EVALUATION_PATH               MISSING
PURGED_WALK_FORWARD_MECHANICS               MOCK_ONLY
EMBARGO_APPLICABILITY_DECISION              UNPROVEN
LEAKAGE_FREE_RESULT                         MOCK_ONLY
MARKET_CALIBRATED_COST_SLIPPAGE             MOCK_ONLY
DSR_PBO_PROMOTION_GATES                     MOCK_ONLY
PHASE_15_IMPLEMENTATION_AUTHORITY           PRESENT
DATA_RIGHTS_AND_RESEARCH_AUTHORITY          MISSING
RIGHTS_CURRENTNESS_REVOCATION               MISSING
PRE_ORDER_RISK                              MOCK_ONLY
IMMUTABLE_AUDIT_SCHEMA                      PRESENT
```

The Phase 16 step sequence also remains exact:

```text
SELECT_CANDIDATE_PRODUCTS                           OUTPUT_FROZEN
REVIEW_CURRENT_USE_RIGHTS                          OUTPUT_FROZEN
QUALIFY_BOUNDED_READ_ONLY_SAMPLES                  NOT_STARTED
PRODUCE_FULL_HISTORY_COVERAGE_MANIFEST             NOT_STARTED
RECONCILE_TEMPORAL_IDENTITY_REVISION_SEMANTICS     NOT_STARTED
DESIGN_LOCAL_QUARANTINE_AND_CANONICAL_SNAPSHOT     NOT_STARTED
REQUEST_SEPARATE_INGESTION_AUTHORITY               NOT_STARTED
```

Step 3 remains `NOT_STARTED` because its two required prior-evidence hashes are missing. Phase 19
produces no source-plan step output and does not reinterpret the Phase 18 rights-review hashes as
Step 3 evidence.

## Frozen identities and canonicalization

The exact fixed identities are:

```text
artifact schema/hash domain: phase19-family-a-step3-prerequisite-assessment-v1
prerequisite schema/domain:   phase19-family-a-step3-prerequisite-v1
required-evidence schema/domain:
                              phase19-family-a-step3-required-prior-evidence-v1
gap-binding schema/domain:    phase19-family-a-phase15-gap-binding-v1
step schema/domain:           phase19-family-a-source-plan-step-evidence-v1
output schema/domain:         phase19-family-a-source-plan-output-v1
prerequisites manifest:       phase19-step3-prerequisites-manifest-v1
required-evidence manifest:   phase19-step3-required-prior-evidence-manifest-v1
gap-bindings manifest:        phase19-phase15-gap-bindings-manifest-v1
steps manifest:               phase19-source-plan-steps-manifest-v1
assessment policy id/domain:  phase19-family-a-step3-prerequisite-assessment-policy-v1
artifact UUID namespace:      2c232226-c183-5f60-bbd0-35837b0b9ed1
assessment timestamp:         2026-07-19T20:01:39.9672350Z
Phase 16 original Step 3 SHA:  331fafa9aa1d2e12871222257562eff7311435dad8e492fc4af58e5de4d28cec
Phase 18 Step 3 evidence SHA:  0b7d8e73aebb70cba4144a2864b98cae58aefa06b3b0db5c16472bcbe1a37548
artifact id:                  0b3f9153-71cc-5052-9b47-f714ed17bb99
embedded artifact SHA-256:    ed738badfb6e95feb4d7969d299bdc6186ef13ebf0f036134518e147803c72df
assessment-policy SHA-256:    78485a93a2fda0d81ea7d2d7fb179f60ef2aee97616f3981fadabfd72ca02438
committed file SHA-256:       29cedb0c54c3adb5bafc36d5df4ee039b173ab11e865e1de40e27ed68d335264
committed artifact bytes:     25,596
```

The timestamp is a fixed architecture-assessment time, not a runtime clock, data-currentness claim,
rights revalidation, or holdout timestamp. The final artifact identity and hashes above are the
deterministically generated values; they are assessment integrity, not either missing Step 3 hash.

Canonical JSON is UTF-8 with lexicographically sorted object keys, stable array order, exact enum
text, no floats or non-finite values, no insignificant whitespace, and one final newline for the
committed artifact and generator stdout. Domain-separated hashes cover complete canonical preimages
except their own hash fields. Missing, duplicate, extra, reordered, unknown, substituted, or
cross-row content fails closed.

## Generator and verifier boundary

The sole generator invocation is:

```text
python scripts/generate_family_a_step3_prerequisite_assessment.py \
  --confirm-prerequisite-assessment-only
```

It writes one deterministic assessment to stdout and accepts no provider, product, URL, credential,
data, path, policy, hash, threshold, signal, action, interval, holdout, result, repair, authority,
order, clock, seed, or output override.

The sole verifier invocation is:

```text
python scripts/verify_family_a_step3_prerequisite_assessment.py \
  --assessment PATH
```

It reads one bounded regular canonical UTF-8 JSON file, rejects a BOM, duplicate keys, floats,
non-finite values, non-object roots, symbolic/non-regular files, oversized input, and unstable reads,
and validates strict contract, deterministic-builder, canonical-byte, state, lineage, and hash
parity. Invalid input or invocation exits 2 with no stdout and one generic sanitized error. A valid
blocked assessment exits 0 because `BLOCKED` is the truthful domain result.

Generation and verification deny network, socket, database, subprocess, credential, provider,
research, broker, and execution dependencies. Runtime clock, randomness, Git discovery, environment
values, filesystem discovery, and machine paths cannot affect the bytes.

## Authority and security invariants

The artifact keeps operational source/provider/product selection, account and credential access,
entitlement/executed-license/currentness verification, provider/account/data requests, external
sample qualification, data capture, provider or licensed-payload persistence, ingestion, snapshot,
complete evaluation-policy presence/approval, holdout definition/opening/label access, research
creation/authorization/execution, performance, `PASS_RESEARCH`, promotion, paper approval, risk
clearance, execution, and order submission false.

It keeps the live path absent, personalized-advice language absent, real-performance claims absent,
runtime network disabled, and the assessment metadata-only. No secret, credential name value,
account identifier, contract/license body, provider response, observation, dataset, feature, label,
return, metric, signal, price, position, order, or fill may enter source, fixtures, artifact,
diagnostics, build output, browser output, CI evidence, or temporary output.

## Persistence, API, migration, and rollback

Phase 19 owns no database persistence, migration, table, SQL function, trigger, API route, Pydantic
API response, OpenAPI path, generated TypeScript contract, dependency, Compose service, transport,
frontend product surface, scheduler, worker, queue, or retry behavior. Alembic head remains exactly
`0011_phase14`; all 57 inherited tables/functions, rows, migrations, API paths, and generated-contract
bytes remain unchanged.

The inherited nonempty `0010_phase13 -> 0011_phase14 -> 0010_phase13 -> 0011_phase14` cycle remains
the schema rollback proof. Phase 19 rollback removes only its portable artifact/code/tests and
wrapper/CI/documentation registrations; it cannot require data or schema rollback.

## Explicit exclusions

Phase 19 adds no legal advice, provider contact, procurement, credential, entitlement, contract
acceptance, operational selection, request, transport, sample, data capture, provider payload,
licensed data, local dataset import, observation, schema qualification, full-history manifest,
normalization, quarantine, ingestion, snapshot, evaluation path, complete policy, threshold,
embargo-applicability decision, exact holdout interval, holdout opening, feature, label, signal,
action, allocation, trial, backtest, return, metric, cost calibration, performance claim, promotion,
approval, revocation, risk mutation, broker, order, fill, reconciliation, scheduler, asynchronous
work, live enum/origin/path, PR, tag, signing, publication, release, deployment, or Phase 20 scaffold.

## Acceptance and failure semantics

Acceptance requires deterministic repeated generation and committed-file parity; offline verifier
success; exact Phase 18 ancestry; exact missing-prerequisite, unchanged-gap, and unchanged-step
states; and adversarial rejection of a forged prerequisite hash, complete policy, defined/opened
holdout, copied synthetic threshold/calibration, resolved embargo, advanced Step 3, positive gate,
performance, authority, or later-step state.

Tests also reject malformed/noncanonical/bounded-file attacks, semantic rehash tampering, secret or
licensed-data canaries, network/database/subprocess/provider/research/broker imports or calls, schema/
API/generated-contract drift, any database write, unsupported phase values 0/20, and incomplete
resource cleanup. Windows and Ubuntu `phase19-compose` must pass at one clean committed SHA/tree.

Stop after Phase 19 same-SHA acceptance. Do not produce either missing Step 3 prerequisite hash,
begin Step 3, contact a provider, obtain or inspect data, define/open a holdout, run/promote research,
modify governance/risk, submit/reconcile an order, add a live capability, or begin Phase 20.
