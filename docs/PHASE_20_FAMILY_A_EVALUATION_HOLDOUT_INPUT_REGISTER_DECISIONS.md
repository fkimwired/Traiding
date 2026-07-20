# Phase 20 Family A evaluation/holdout input-register decisions

## Accepted baseline and authority

Phase 20 starts only from the formally accepted Phase 19 identity:

- Commit: `86ddcafacff43b42fe56346745d7e6f08eaf3a52`
- Tree: `6b6c2693a969e80cac9013d441ba607565d8914a`
- Phase 19 artifact id: `0b3f9153-71cc-5052-9b47-f714ed17bb99`
- Phase 19 artifact SHA-256:
  `ed738badfb6e95feb4d7969d299bdc6186ef13ebf0f036134518e147803c72df`
- Phase 19 assessment-policy SHA-256:
  `78485a93a2fda0d81ea7d2d7fb179f60ef2aee97616f3981fadabfd72ca02438`
- Windows full Phase 19 verifier passed at that identity in 4,614.4 seconds with a clean
  post-cleanup repository and empty resource namespace.
- Ubuntu GitHub Actions run `29705348113`: `preflight`, `unit`, and `phase19-compose` passed at that
  identical identity; Compose acceptance took 1 hour 40 minutes 49 seconds and proved complete
  cleanup.

The user separately authorized Phase 20. This decision narrows that authority to one deterministic,
portable, read-only register of the still-missing inputs and future-only transition rules required
to create a complete non-synthetic Family A evaluation policy and an untouched confirmation-holdout
definition. It authorizes no input value, source or product choice, rights conclusion, external
request, credential, data access, policy creation or approval, holdout definition or opening,
qualification, research, promotion, risk decision, execution, order, or later phase.

## Decision and truthful result

Phase 20 is a metadata-only, database-free, network-disabled input register. It expands the accepted
Phase 19 blocked finding into an exact field-name contract and a closed set of future transition
rules without supplying any of those fields' operational or data-specific values.

The exact successful domain result is:

```text
outcome:               BLOCKED
register_state:        INPUTS_FROZEN
aggregate_conclusion: BLOCKED_MISSING_OPERATIONAL_AND_DATA_SPECIFIC_INPUTS
```

`INPUTS_FROZEN` means only that the required-input names, their current evidence classifications,
their future-only transition rules, and the blocked artifact bytes reproduce. It is not a complete
evaluation policy, a holdout definition, an approval, an input-state upgrade, a Phase 16 source-plan
step output, or authority to begin bounded qualification.

The artifact emits neither of the two reserved Phase 16 Step 3 hashes:

```text
non_synthetic_evaluation_policy_sha256       MISSING
confirmation_holdout_definition_sha256       MISSING
```

It also emits no `qualification_artifact_set_sha256`. Its own artifact, policy, record, manifest,
and committed-file hashes prove only register integrity and may not substitute for any of those
three absent outputs.

## Why Phase 20 cannot create a complete policy or holdout

The accepted Phase 18 result is `BLOCKED_NO_OPERATIONAL_SELECTION`. No exact operational product
composition, current executed rights, delivery, schema version, full target coverage contract,
decision calendar, availability/missingness semantics, or current product entitlement is present.
Public product metadata and a fixed-time technical terms review are not an operational selection or
account-specific right.

The Phase 5 `FrozenEvaluationPolicy` contract is explicitly synthetic-only through
`synthetic_fixture_policy=true`. Its dates, folds, thresholds, fee/spread/impact assumptions,
calibration ids, regimes, and risk limits are deterministic QA fixtures. Phase 20 may name the
future fields but cannot copy, relabel, approve, or hash those mock values as non-synthetic inputs.
No threshold may be invented simply to complete a schema.

The repository proves label-blind and single-use holdout mechanics only with synthetic source
references. A truthful pre-observation holdout definition requires an exact selected source/product
and schema, versioned decision calendar, contiguous interval, label-information boundaries,
exclusion rules, custodian/approval evidence, and confirmation that no observation or label was
inspected. Those facts do not exist. Phase 20 therefore cannot define, open, consume, or replace a
non-synthetic holdout.

## Exact input-requirement registry

Input categories are exactly `UPSTREAM_CONTEXT`, `EVALUATION_POLICY_INPUT`,
`CONFIRMATION_HOLDOUT_INPUT`, and `APPROVAL_INPUT`. Evidence states are exactly `PRESENT`,
`MOCK_ONLY`, `MISSING`, `UNPROVEN`, and `STALE`. Phase 20 carries these twenty rows in this order.
Only the audit-schema row is `PRESENT` and satisfied; it cannot clear the aggregate or either
reserved evidence requirement.

| Ordinal | Category | Code | State | Satisfied | Reason |
|---:|---|---|---|---:|---|
| 1 | `UPSTREAM_CONTEXT` | `OPERATIONAL_SOURCE_PRODUCT_COMPOSITION` | `MISSING` | false | `phase18_no_operational_selection` |
| 2 | `UPSTREAM_CONTEXT` | `CURRENT_EXECUTED_USE_RIGHTS_AND_REVOCATION` | `MISSING` | false | `phase18_blocked_review_not_executed_rights` |
| 3 | `UPSTREAM_CONTEXT` | `EXACT_DELIVERY_AND_SCHEMA_VERSIONS` | `UNPROVEN` | false | `delivery_and_schema_unproven` |
| 4 | `UPSTREAM_CONTEXT` | `DECLARED_PIT_COVERAGE_CALENDAR_AVAILABILITY_MISSINGNESS` | `MISSING` | false | `data_specific_preobservation_contract_missing` |
| 5 | `EVALUATION_POLICY_INPUT` | `SIGNAL_ACTION_LABEL_AND_HORIZON` | `MOCK_ONLY` | false | `signal_and_horizon_mock_only` |
| 6 | `EVALUATION_POLICY_INPUT` | `FEATURE_LINEAGE_LOOKBACK_AND_PREPROCESSING` | `MOCK_ONLY` | false | `feature_policy_mock_only` |
| 7 | `EVALUATION_POLICY_INPUT` | `WALK_FORWARD_FOLD_GEOMETRY_AND_PURGE` | `MOCK_ONLY` | false | `walk_forward_geometry_mock_only` |
| 8 | `EVALUATION_POLICY_INPUT` | `EMBARGO_APPLICABILITY_AND_DURATION` | `UNPROVEN` | false | `embargo_applicability_unproven` |
| 9 | `EVALUATION_POLICY_INPUT` | `SAMPLE_ADEQUACY_AND_RETURN_HANDLING` | `MOCK_ONLY` | false | `sample_adequacy_mock_only` |
| 10 | `EVALUATION_POLICY_INPUT` | `TRIAL_ACCOUNTING_DSR_PBO_SELECTION` | `MOCK_ONLY` | false | `trial_dsr_pbo_policy_mock_only` |
| 11 | `EVALUATION_POLICY_INPUT` | `LEAKAGE_AND_DATA_QUALITY_BLOCKS` | `MOCK_ONLY` | false | `leakage_gates_mock_only` |
| 12 | `EVALUATION_POLICY_INPUT` | `MARKET_CALIBRATED_COST_SLIPPAGE_CAPACITY` | `MOCK_ONLY` | false | `cost_slippage_calibration_mock_only` |
| 13 | `EVALUATION_POLICY_INPUT` | `STRESS_VECTOR_AND_PROMOTION_GATES` | `MOCK_ONLY` | false | `stress_gate_policy_mock_only` |
| 14 | `EVALUATION_POLICY_INPUT` | `REGIME_AND_CRISIS_DEFINITIONS` | `MOCK_ONLY` | false | `regime_policy_mock_only` |
| 15 | `EVALUATION_POLICY_INPUT` | `COMPUTABLE_DATA_SPECIFIC_RISK_LIMITS` | `MOCK_ONLY` | false | `risk_limits_mock_only` |
| 16 | `EVALUATION_POLICY_INPUT` | `REPRODUCIBILITY_AUDIT_SCHEMA` | `PRESENT` | true | `audit_schema_present_only` |
| 17 | `CONFIRMATION_HOLDOUT_INPUT` | `SOURCE_BOUND_CONTIGUOUS_INTERVAL` | `MISSING` | false | `confirmation_interval_missing` |
| 18 | `CONFIRMATION_HOLDOUT_INPUT` | `DECISION_CALENDAR_LABEL_BOUNDARY_AND_EXCLUSIONS` | `MISSING` | false | `holdout_calendar_and_boundaries_missing` |
| 19 | `CONFIRMATION_HOLDOUT_INPUT` | `LABEL_BLIND_CONSUMPTION_REPLACEMENT_GOVERNANCE` | `MOCK_ONLY` | false | `holdout_rules_mock_only` |
| 20 | `APPROVAL_INPUT` | `INDEPENDENT_POLICY_AND_HOLDOUT_APPROVAL_RECORD` | `MISSING` | false | `independent_approval_missing` |

Each row contains only immutable requirement metadata: its ordinal, category, code, definition,
current evidence state, satisfaction bit, reason code, related Phase 19 prerequisite/gap codes, the
exact names of fields a future separately authorized evidence artifact must supply, and a
domain-separated row hash. A `required_field_names` entry names a future field; it never supplies
its value. Every row has `input_value_present=false` and
`resolves_reserved_evidence=false` in Phase 20. Row 16 is satisfied only because the repository's
audit schema exists; the register still carries no audit-field value.

Every row's `related_phase19_prerequisite_codes` and `related_phase15_gap_codes` tuples are nonempty,
closed to the inherited enum vocabularies, fixed in canonical order, and bound inside that row's
complete `requirement_sha256` preimage. Missing, empty, duplicate, reordered, unknown, or cross-row
relation content is invalid; a relation proves traceability only and cannot upgrade evidence.

The field-name coverage is complete at the following group boundary:

1. operational capability-to-product composition, source/product/delivery identities, and selection
   approval metadata;
2. executed agreement/schedule scope for storage, non-display, derived data, retention/deletion,
   redistribution, third-party rights, currentness, termination, and revocation;
3. exact delivery/schema versions, field manifests, temporal mappings, and stable identity mappings;
4. declared target history boundaries, timezone/calendar, availability, validity, revision,
   missingness, and date-only conventions;
5. deterministic research-score semantics, label and horizon, executable lag, universe, rebalance,
   holding, overlap, and no-trade rules, without a trade instruction;
6. feature formulas, source fields, lookbacks, availability, train-only preprocessing, imputation,
   encoding, feature-selection, and hyperparameter rules;
7. outer/inner fold geometry, train mode/window, test geometry, and actual-label-interval purge;
8. an explicit embargo applicability decision and positive duration only when later observations can
   enter training;
9. minimum OOS, independent-event and synchronized-trial adequacy plus missing/no-trade handling;
10. selection metric, complete raw/effective-trial accounting, DSR/PBO thresholds and calculation
    conventions, CSCV blocks, ties, frequency, annualization, and serial-correlation handling;
11. L01-L06 plus duplicate grain, future time, revisions, identity joins, delistings, staleness, and
    schema-drift blocking rules;
12. market-calibrated fee, spread, impact, delay, borrow, participation, capacity, and vintage inputs;
13. all-cost and liquidity stresses plus predeclared net-return, Sharpe, drawdown, and capacity gates;
14. predeclared volatility/rate definitions and cuts, crisis windows, and dependency handling;
15. position, gross, net, sector, turnover, volatility, loss, and drawdown limits;
16. immutable config/policy/snapshot/code/seed/trial/time/lineage and numeric-metadata requirements;
17. one source/schema/calendar-bound contiguous unopened confirmation interval;
18. exact label-information boundaries and exclusion/purge rules around that interval;
19. label-blind exclusion, custodian, single-use consumption, replacement/new-generation rules; and
20. independent policy and holdout approval identities, versions, timestamps, and immutable evidence.

The exact `required_field_names` tuples by ordinal are:

```text
 1 (capability_product_composition_id, source_ids, product_ids, delivery_ids, selection_scope,
    selected_at_utc, selected_by, selection_evidence_sha256)
 2 (legal_entity_id, executed_agreement_id, product_schedule_ids, storage_right,
    non_display_internal_use_right, derived_data_right, retention_deletion_rule,
    redistribution_right, third_party_rights, effective_at_utc, expires_at_utc,
    revocation_currentness_rule, reviewed_at_utc, reviewed_by, rights_evidence_sha256)
 3 (delivery_method_ids, schema_ids, schema_versions, schema_effective_at_utc,
    schema_field_manifest_sha256, temporal_field_mapping_sha256,
    instrument_identity_mapping_sha256)
 4 (target_history_start_utc, target_history_end_utc, decision_timezone, decision_calendar_id,
    decision_calendar_version, event_time_rule, available_at_rule, ingested_at_rule,
    validity_interval_rule, revision_rule, missingness_rule, date_only_availability_rule,
    coverage_requirement_sha256)
 5 (signal_specification_id, signal_version, deterministic_formula_id, output_semantics,
    forecast_horizon, executable_decision_lag, label_formula_id, label_information_interval_rule,
    universe_eligibility_rule, universe_exclusion_rule, rebalance_rule, holding_rule,
    overlap_rule, no_trade_rule)
 6 (feature_specification_id, feature_version, feature_formula_ids, source_field_ids,
    lookback_rules, availability_rules, source_observation_binding_rule, preprocessing_rules,
    imputation_policy, encoding_policy, feature_selection_policy, hyperparameter_policy)
 7 (decision_timezone, decision_calendar_id, outer_fold_count, inner_fold_count,
    minimum_train_observations, outer_test_observations, inner_test_observations,
    rolling_train_observations, train_mode, purge_rule)
 8 (train_mode, embargo_applicability, embargo_rule, embargo_duration,
    embargo_decision_rationale)
 9 (min_oos_observations, min_independent_events, min_synchronized_trials,
    missing_return_policy, no_trade_return_policy, sample_adequacy_approval_id)
10 (primary_selection_metric, raw_trial_definition, effective_trial_method, dsr_min_probability,
    cscv_block_count, pbo_tie_policy, pbo_rank_orientation, pbo_max, return_frequency,
    annualization_factor, serial_correlation_method)
11 (leakage_check_ids, duplicate_grain_rule, future_timestamp_rule, revision_backfill_rule,
    identifier_break_rule, join_integrity_rule, delisting_outcome_rule, stale_partition_rule,
    schema_drift_rule, data_quality_severity_rule)
12 (fee_schedule_id, fee_schedule_effective_date, spread_source, spread_fallback_rule,
    impact_model_id, impact_model_version, impact_calibration_id, impact_calibration_vintage,
    latency_rule, slippage_model_id, borrow_source, hard_to_borrow_rule,
    baseline_max_participation, capacity_rule)
13 (all_cost_multiplier, spread_multiplier, volatility_multiplier, adv_multiplier,
    impact_coefficient_multiplier, latency_multiplier, borrow_multiplier, min_stressed_net_pnl,
    min_stressed_annual_return, min_stressed_sharpe, max_stressed_drawdown,
    max_capacity_breach_rate)
14 (volatility_definition, volatility_cut, rate_definition, rate_cut, crisis_window_ids,
    crisis_declaration_times, dependency_rule)
15 (max_single_observation_exposure, max_gross_exposure, max_net_exposure,
    max_sector_exposure, max_turnover, max_volatility, max_loss, max_drawdown,
    risk_policy_approval_id)
16 (artifact_id, artifact_type, config_hash, evaluation_policy_id, evaluation_policy_sha256,
    data_snapshot_id, source_versions, code_version_git_sha, random_seed, raw_trial_count,
    effective_trial_count, effective_trial_method, created_at_utc, decision_time_utc,
    parent_artifact_ids, numeric_metadata_rule, append_only_rule)
17 (holdout_definition_id, source_product_composition_sha256, delivery_schema_manifest_sha256,
    decision_calendar_id, decision_calendar_version, interval_start_utc, interval_end_utc,
    research_generation_id, frozen_at_utc)
18 (label_information_interval_rule, boundary_exclusion_rule, purge_intersection_rule,
    confirmation_sample_eligibility_rule, decision_timezone, decision_calendar_id)
19 (label_blind_exclusion_rule, feature_design_exclusion, model_selection_exclusion,
    threshold_selection_exclusion, narrative_selection_exclusion, label_access_prohibited,
    opening_rule, single_use_rule, consumption_rule, replacement_rule, custodian_id)
20 (policy_approval_id, policy_approved_by, policy_approved_at_utc, holdout_approval_id,
    holdout_approved_by, holdout_approved_at_utc, approval_scope, approval_version,
    approval_evidence_sha256)
```

No product name, provider choice, contract/license value, account or credential, schema value,
calendar id, date, interval, threshold, fold size, embargo duration, cost/calibration id, regime
window, risk number, signal, action, feature, label, return, or metric may populate these rows.

## Exact future-only transition-rule registry

Phase 20 freezes these ten rules in this exact order. Every rule has `applied=false`; none changes an
input state, produces evidence, or starts a source-plan step.

1. `NO_PLAN_OR_ARTIFACT_HASH_UPGRADE`
2. `MOCK_ONLY_TO_PRESENT_REQUIRES_APPROVED_NON_SYNTHETIC_EVIDENCE`
3. `MISSING_TO_PRESENT_REQUIRES_COMPLETE_REQUIRED_EVIDENCE`
4. `UNPROVEN_TO_PRESENT_REQUIRES_INDEPENDENT_VERIFICATION`
5. `STALE_TO_PRESENT_REQUIRES_FRESH_REVALIDATION`
6. `PRESENT_TO_STALE_ON_CURRENTNESS_OR_VERSION_DRIFT`
7. `HOLDOUT_DEFINITION_REQUIRES_SOURCE_CALENDAR_BINDING_AND_ZERO_OBSERVATION_LABEL_ACCESS`
8. `POLICY_COMPLETION_REQUIRES_ALL_POLICY_INPUTS_AND_UNOPENED_HOLDOUT_REFERENCE`
9. `STEP3_REQUIRES_BOTH_RESERVED_HASHES_AND_SEPARATE_EXTERNAL_ACTION_AUTHORITY`
10. `LATER_SOURCE_PLAN_STEPS_CANNOT_SKIP_OR_IMPLY_PREDECESSORS`

The rules mean:

- a plan, requirements document, public fact, synthetic fixture, row/manifest hash, or operator
  assertion cannot upgrade evidence;
- `MOCK_ONLY`, `MISSING`, `UNPROVEN`, and `STALE` become `PRESENT` only through the exact complete,
  approved, independently verified, current evidence named by the applicable rule;
- evidence that loses currentness or whose source/product/schema/policy version changes degrades to
  `STALE` and fails closed;
- a holdout definition can be created only after source/schema/calendar binding and while observation
  access, label access, opening, and consumption remain false;
- a complete policy must bind every applicable input and the unopened holdout definition rather than
  embed a fabricated or synthetic substitute; and
- even both future hashes would not start Step 3 without a later, separate authorization for the
  bounded external action. No later step can bypass an incomplete predecessor.

The register additionally binds six ordered construction dependency groups, all `BLOCKED`:

```text
OPERATIONAL_COMPOSITION_AND_RIGHTS
SOURCE_COVERAGE_AND_CALENDAR
EVALUATION_METHODOLOGY
COST_STRESS_REGIME_AND_RISK
AUDIT_AND_HOLDOUT_GOVERNANCE
INDEPENDENT_JOINT_APPROVAL
```

It binds six corresponding pre-observation construction gates, all `BLOCKED`, `passed=false`, and
`required_before_observation=true`:

```text
OPERATIONAL_COMPOSITION_CURRENT_RIGHTS_GATE
SOURCE_COVERAGE_CALENDAR_GATE
NON_SYNTHETIC_METHODOLOGY_GATE
MARKET_CALIBRATION_STRESS_RISK_GATE
UNTOUCHED_HOLDOUT_GOVERNANCE_GATE
INDEPENDENT_JOINT_APPROVAL_GATE
```

Eight substitute classes are unconditionally forbidden for both future output classes:

```text
PHASE15_REQUIREMENTS_HASH
PHASE19_ASSESSMENT_HASH
SYNTHETIC_POLICY_OR_RESULT_HASH
PUBLIC_DOCUMENTATION_OR_RIGHTS_REVIEW_HASH
CANDIDATE_INVENTORY_HASH
PROTOCOL_OR_TEMPLATE_HASH
PLACEHOLDER_OR_ALL_ZERO_HASH
OPERATOR_OVERRIDE_OR_ARBITRARY_HASH
```

These dependency, gate, and substitute records are metadata and integrity constraints only. They
create no construction output, approval, input transition, or authority.

## Missing future evidence, gaps, and source-plan steps

The missing-future-evidence registry has exactly two rows. Both are `MISSING`, `produced=false`, and
their strict schema has no value, evidence-hash, placeholder, or override field:

| Name | Reason |
|---|---|
| `non_synthetic_evaluation_policy_sha256` | `complete_non_synthetic_evaluation_policy_not_created` |
| `confirmation_holdout_definition_sha256` | `untouched_confirmation_holdout_definition_not_created` |

All nineteen accepted Phase 15 gap states remain exact and unchanged:

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
PURGED_WALK_FORWARD_MECHANICS               MOCK_ONLY
EMBARGO_APPLICABILITY_DECISION              UNPROVEN
LEAKAGE_FREE_RESULT                          MOCK_ONLY
MARKET_CALIBRATED_COST_SLIPPAGE              MOCK_ONLY
DSR_PBO_PROMOTION_GATES                      MOCK_ONLY
PHASE_15_IMPLEMENTATION_AUTHORITY            PRESENT
DATA_RIGHTS_AND_RESEARCH_AUTHORITY           MISSING
RIGHTS_CURRENTNESS_REVOCATION                MISSING
PRE_ORDER_RISK                               MOCK_ONLY
IMMUTABLE_AUDIT_SCHEMA                       PRESENT
```

The Phase 16 source-plan sequence also remains exact:

```text
SELECT_CANDIDATE_PRODUCTS                           OUTPUT_FROZEN
REVIEW_CURRENT_USE_RIGHTS                          OUTPUT_FROZEN
QUALIFY_BOUNDED_READ_ONLY_SAMPLES                  NOT_STARTED
PRODUCE_FULL_HISTORY_COVERAGE_MANIFEST             NOT_STARTED
RECONCILE_TEMPORAL_IDENTITY_REVISION_SEMANTICS     NOT_STARTED
DESIGN_LOCAL_QUARANTINE_AND_CANONICAL_SNAPSHOT     NOT_STARTED
REQUEST_SEPARATE_INGESTION_AUTHORITY               NOT_STARTED
```

Phase 20 is not a source-plan step. It produces no Step 3 output and does not reinterpret the Phase
17 inventory, Phase 18 blocked rights outputs, Phase 19 assessment, audit schema, or its own register
hash as a source-plan prerequisite.

## Frozen identities and canonicalization

The fixed contract identities are:

```text
artifact schema/hash domain: phase20-family-a-evaluation-holdout-input-register-v1
inherited prerequisite:      phase20-family-a-inherited-phase19-prerequisite-v1
input requirement schema:    phase20-family-a-evaluation-holdout-input-requirement-v1
missing-evidence schema:     phase20-family-a-missing-future-evidence-v1
transition-rule schema:      phase20-family-a-future-evidence-transition-rule-v1
dependency-group schema:     phase20-family-a-construction-dependency-group-v1
construction-gate schema:    phase20-family-a-evaluation-holdout-construction-gate-v1
forbidden-substitute schema: phase20-family-a-forbidden-substitute-v1
gap-binding schema:          phase20-family-a-phase15-gap-binding-v1
source-plan step schema:     phase20-family-a-source-plan-step-binding-v1
inherited prereq manifest:   phase20-inherited-phase19-prerequisites-manifest-v1
input manifest domain:       phase20-evaluation-holdout-input-requirements-manifest-v1
missing-evidence manifest:   phase20-missing-future-evidence-manifest-v1
transition manifest domain:  phase20-future-evidence-transition-rules-manifest-v1
dependency manifest domain:  phase20-construction-dependency-groups-manifest-v1
gate manifest domain:        phase20-evaluation-holdout-construction-gates-manifest-v1
substitute manifest domain:  phase20-forbidden-substitutes-manifest-v1
gap manifest domain:         phase20-phase15-gap-bindings-manifest-v1
step manifest domain:        phase20-source-plan-step-bindings-manifest-v1
register policy id/domain:   phase20-family-a-evaluation-holdout-input-register-policy-v1
fixed frozen timestamp:      2026-07-20T00:47:38.1976088Z
artifact id:                 e501d4f8-bebe-5e68-9457-56f6a589f478
embedded artifact SHA-256:   902fca99d4fec1943403cbed406259f86c0eee05c41cb835b6daf7d165db340b
register-policy SHA-256:     e6be914218dc8b16b2c019ff8d72338dcf495b7cf375cd95281651b89939a31a
inherited manifest SHA-256:  ee650453fc05597765164b965cd65ee3844b034f51b41b4064a001cda147efe9
input manifest SHA-256:      b4ffc11633c0ae41d351b7dd10380c29a47e44f368b9248bc74a412e81c4c0ad
missing manifest SHA-256:    ace85cba35e9ca4ea3a26fe7692591a2d02234b3437e8f2c2763e60aebbdff41
transition manifest SHA-256: b594a162a1c6124502aa6552634f0d1bba7832bf89e550a2e1f7d21b6f737955
dependency manifest SHA-256: 34b44a2d2995f288947eb7a8da6c21f5fb9c8653316172e3155edaa2b9077379
gate manifest SHA-256:       4e5bad5d5d9441c9e832b6c9511ab8aa9123a4875130b98a2fcdf43c8907692a
substitute manifest SHA-256: 044b07af06221878b11da497baf8bc838909043f1550cae29669056a84cf4b84
gap manifest SHA-256:        c98b37ca4a0aa8ab9a7641a865f9444e56422be74cadf239c33e3cd3a882334a
step manifest SHA-256:       e695c826fe23365bf6b89d09626003a8feac3c3aab589266bd56464e5cdaa4bf
committed file SHA-256:      a0b6987301f12e87963ee751cc9abb4f6be4af7702fad999092ad2d0c363a741
committed artifact bytes:    60,265
```

These are the exact deterministic generated identities. The timestamp is a fixed architecture
register time, not a runtime clock, evidence-currentness claim, policy approval, rights revalidation,
holdout definition/opening time, or external-action time.

Canonical JSON is UTF-8 with lexicographically sorted object keys, stable array order, exact closed
enum text, no floats or non-finite values, no insignificant whitespace, and one final newline for
the committed artifact and generator stdout. Domain-separated hashes cover complete canonical
preimages except their own hash fields. Missing, duplicate, extra, reordered, unknown, substituted,
or cross-row content fails closed.

## Generator and verifier boundary

The sole generator invocation is:

```text
python scripts/generate_family_a_evaluation_holdout_input_register.py \
  --confirm-input-register-only
```

It writes one deterministic register to stdout and accepts no provider, product, source, URL,
credential, account, entitlement, contract, data, path, policy, input value, threshold, signal,
action, interval, holdout, result, repair, authority, order, clock, seed, or output override.

The sole verifier invocation is:

```text
python scripts/verify_family_a_evaluation_holdout_input_register.py \
  --register PATH
```

It reads one bounded regular canonical UTF-8 JSON file; rejects a BOM, duplicate keys, floats,
non-finite values, non-object roots, symbolic/non-regular files, remote/UNC/device paths, oversized
input, and unstable reads; and validates strict contract, deterministic-builder, canonical-byte,
lineage, registry, state, transition, authority, and hash parity. Invalid input or invocation exits
2 with no stdout and one generic sanitized error. A valid blocked register exits 0 because `BLOCKED`
is the truthful domain result. Its receipt reports `input_requirement_count=20`,
`transition_rule_count=10`, both future-evidence records missing, and `step3_eligible=false`.

Generation and verification deny network, socket, database, subprocess, credential, provider,
research, broker, and execution dependencies. Runtime clock, randomness, Git discovery, environment
values, filesystem discovery, and machine paths cannot affect the bytes.

## Authority and security invariants

Freeze false every operational source/provider/product selection, account/credential access,
entitlement/executed-license/currentness verification, provider/account/data request, external
sample qualification, data capture, provider or licensed-payload persistence, ingestion, snapshot,
input-value presence, transition application, complete-policy presence/approval, holdout definition/
opening/consumption/label access, research creation/authorization/execution, performance,
`PASS_RESEARCH`, promotion, paper approval, risk clearance, execution, and order submission.

Freeze true `metadata_only`, `requirements_only`, `runtime_network_disabled`, `live_path_absent`,
`no_personalized_investment_advice`, and `no_real_performance_claimed`.

No secret, credential name value, account id, entitlement/contract/license body, provider response,
observation, dataset, schema payload, feature, label, return, metric, signal value, price, position,
order, or fill may enter source, fixtures, artifact, diagnostics, logs, build output, browser output,
CI evidence, or temporary output.

## Persistence, API, migration, and rollback

Phase 20 owns no database persistence, migration, table, SQL function, trigger, API route, Pydantic
API response, OpenAPI path, generated TypeScript contract, dependency, Compose service, transport,
frontend product surface, scheduler, worker, queue, retry, broker, or execution behavior. Alembic
head remains exactly `0011_phase14`; all 57 inherited tables/functions, rows, migrations, API paths,
and generated-contract bytes remain unchanged.

The inherited nonempty `0010_phase13 -> 0011_phase14 -> 0010_phase13 -> 0011_phase14` cycle remains
the schema rollback proof. Phase 20 rollback removes only its portable artifact/code/tests and
wrapper/CI/documentation registrations; it requires no data or schema rollback.

## Exact write allowlist

Write only these 40 paths:

```text
.github/workflows/ci.yml
Makefile
README.md
docs/COMPLIANCE_NOTES.md
docs/DATA_SOURCES.md
docs/EVALS.md
docs/IMPLEMENTATION_PLAN.md
docs/PHASE_20_FAMILY_A_EVALUATION_HOLDOUT_INPUT_REGISTER.json
docs/PHASE_20_FAMILY_A_EVALUATION_HOLDOUT_INPUT_REGISTER_DECISIONS.md
docs/RISK_POLICY.md
docs/handoffs/PHASE_20.md
scripts/check.ps1
scripts/check.sh
scripts/generate_family_a_evaluation_holdout_input_register.py
scripts/verify_family_a_evaluation_holdout_input_register.py
scripts/verify_phase1.py
services/data/src/fable5_data/phase20/__init__.py
services/data/src/fable5_data/phase20/canonical.py
services/data/src/fable5_data/phase20/contracts.py
services/data/src/fable5_data/phase20/input_register.py
services/data/tests/test_phase20_contracts.py
services/data/tests/test_phase20_input_register.py
services/data/tests/test_phase20_security.py
services/frontend/e2e/phase8.accessibility.spec.ts
services/frontend/e2e/phase8.visual.spec.ts
tests/test_phase5_postgres.py
tests/test_phase9_static.py
tests/test_phase10_static.py
tests/test_phase11_static.py
tests/test_phase12_static.py
tests/test_phase13_static.py
tests/test_phase14_static.py
tests/test_phase15_static.py
tests/test_phase16_static.py
tests/test_phase17_static.py
tests/test_phase18_static.py
tests/test_phase19_static.py
tests/test_phase20_portable.py
tests/test_phase20_static.py
tests/test_repository_policy.py
```

Stop before a write outside this list. In particular, do not modify Compose, dependencies,
environment examples, migrations, API code/tests, OpenAPI, generated TypeScript, accepted Phase
4-19 production code, paper/research/risk services, frontend product code, or visual snapshots. The
two inherited Phase 8 browser specs are in scope only to extend the supported phase range without
changing product assertions or baselines.

## Acceptance and adversarial failure semantics

Acceptance requires repeated deterministic generation and committed-file parity; offline verifier
success; exact Phase 19 ancestry; the exact twenty input rows and ten unapplied transition rules;
both reserved evidence records missing without values; exact unchanged gaps and steps; and every
authority field false.

Adversarial tests must reject:

- any selected provider/product/delivery/schema or current rights claim;
- any credential, account, license/contract value, calendar/date/interval, fold size, embargo
  duration, threshold, cost/calibration id, regime window, risk value, signal/action/feature/label,
  observation, return, metric, performance, order, or fill;
- any copied Phase 5/6 synthetic value or synthetic/requirements/artifact hash substituted for a
  non-synthetic input or either reserved Step 3 hash;
- any policy presence/approval, holdout definition/opening/consumption, input-state upgrade,
  `applied=true` transition, Step 3 start/output, later-step advance, gap drift, positive result, or
  positive authority bit;
- malformed, duplicate, noncanonical, float/non-finite, BOM, oversized, symbolic, directory,
  remote/UNC/device/different-drive, or read-race input;
- network, database, subprocess, environment, runtime-clock, randomness, Git-discovery, provider,
  research, broker, or execution dependency;
- secret, contract/license, provider-body, observation, or licensed-data canaries;
- migration, schema, row, API, OpenAPI, generated-contract, dependency, browser-baseline, or
  inherited behavior drift;
- unsupported phase values 0 and 21; and
- any remaining acceptance container, network, volume, verifier process, browser output, or
  temporary evidence resource.

No repair, retry, fallback, partial success, operator override, or positive alternate result exists.
Windows and Ubuntu `phase20-compose` must pass at one clean committed SHA/tree and prove complete
resource cleanup before Phase 20 is formally accepted.

## Stop condition

Stop after Phase 20 is implemented and, when authorized, accepted at the same Windows/Ubuntu
identity. Do not begin Phase 21 or Step 3, create either missing Step 3 hash, contact a provider or counsel,
obtain/load a credential, inspect an account or data, choose input values, define/open a holdout,
create a snapshot, run/promote research, modify governance/risk, submit/reconcile an order, add a
live capability, open a PR, tag, sign, publish, release, or deploy.
