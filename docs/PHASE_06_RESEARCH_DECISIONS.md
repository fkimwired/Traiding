# Phase 6 Research Decisions

## Scope and outcome vocabulary

Phase 6 implements research-only pipelines A, B, and C. It does not implement paper
approval, pre-order controls, a broker, positions, orders, paper execution, or live
execution. `PASS_RESEARCH` remains a Phase 5 research result and is never paper approval.
All reported values are deterministic synthetic QA evidence; none is a real-performance
claim or personalized investment advice.

The server-owned deterministic configurations are:

- `phase6-a-pass-v2` and `phase6-a-fail-cost-v2`
- `phase6-b-pass-v2` and `phase6-b-fail-crash-v2`
- `phase6-c-pass-v2` and `phase6-c-fail-corroboration-v2`

These configuration ids are immutable fixture identities, not expected or promised verdicts.
The accepted deterministic outcomes are exact: `phase6-a-pass-v2` is the one synthetic
`PASS_RESEARCH` artifact; `phase6-a-fail-cost-v2`, both Family B configurations, and
`phase6-c-pass-v2` are `FAIL_REJECT`; and `phase6-c-fail-corroboration-v2` blocks before
persistence with `official_corroboration_required`. The `-pass-` token in the B and C ids is
therefore not a verdict. None of these synthetic outcomes is a real-performance claim, paper
approval, or execution authorization.

Clients supply only a persisted `BUILD_RESEARCH` mapping id, a canonically sorted set of
immutable Phase 4 snapshot ids, and one configuration id. The server resolves all policy,
threshold, hash, time, trial, metric, report, and verdict fields.

## Authorized source generalizations

Migration 0006 preserves migrations 0001 through 0005 and adds only the Phase 6
prerequisites authorized for this phase:

- `sector_classification` under `security_master`, with PIT validity in the immutable
  observation envelope;
- `official_document_content` under `official_document_event_metadata`, with exact UTF-8
  content hash, availability time, correction time, correction sequence, and predecessor;
- `social_attention` under `official_document_event_metadata`, with an immutable content
  hash, observation time, resolved entity, claimed official source id, manipulation-risk
  flag, and a constant non-standalone boundary;
- `security_master` and `universe_membership` authorization for Family B lifecycle and PIT
  eligibility evidence; and
- `security_master`, `universe_membership`, and `ohlcv` authorization for Family C entity,
  eligibility, price-basis, label, and unchanged leakage-gate evidence; and
- `macro_regime_inputs` authorization for Family A only, with immutable PIT
  `macro_rate_observation` vintages and a `crisis_window_definition` declared before the
  window begins.

The Phase 4 default fixture/profile/configuration remain frozen. A separately versioned
Phase 6 synthetic adapter supplies 1,198 deterministic records for a one-source mapping:
11 identity, listing, sector, and lifecycle records; five PIT membership records; 852 raw
nominal OHLCV bars; one corporate action; one delisting event; 12 as-reported fundamentals;
305 calendar sessions; three action-aware return bundles; and five official-event records
(two metadata records, two versioned document-content records, and one immutable social-
attention record); plus two PIT macro-rate vintages and one predeclared crisis-window
definition. The frozen fixture-set version is `phase6-synthetic-pit-fixtures-v2`, and its exact
one-source fixture-set SHA-256 is
`010c4edf621f5a75cbb1913a5a513e3c2472e8da9a53b143345b2fb91f6fed5d`. The 305-session
history makes the frozen 252-session Family B lag computable. Family C documents and social
corroboration are rebound to exact persisted official source-version ids. A mapping with two
official sources adds five records for the second source without changing any pre-existing
observation.

## Phase 5 bridge

Every valid run is evaluated only by the unchanged Phase 5 engine and its exact ordered
gate vocabulary:

`DATA_PIT`, `CV_CHRONOLOGY`, `PREPROCESSING`, `TRIAL_REGISTRY`, `DSR`, `PBO`,
`COST_STRESS`, `LEAKAGE`, `SAMPLE_ADEQUACY`, `REGIME`, `RISK_LIMITS`, and
`REPRODUCIBILITY`.

The additive lineage bridge partitions the complete prepared source graph into exact
sample-scoped inputs and hash-bound report-scoped roles. Report-scoped evidence is permitted for
prepared labels, train-only transforms, lifecycle tests, official corroboration, and prepared
features that cannot truthfully be attributed to one evaluation sample. The two partitions are
disjoint and their union must equal the complete prepared source graph. Every A/B/C sample carries
its exact same-entity synthetic OHLCV price-basis evidence and point-in-time universe-membership
reconstruction, so the unchanged L01 and L05 implementations run normally alongside L02, L03,
L04, and L06. Pipeline feature rows, labels, label-independent model outputs, and output-times-
label ledger cells are prepared first; the resulting fixture identity binds the complete prepared
pipeline input hash. Missing policy, source, PIT, delisting, leakage, or computable gate evidence
still blocks. The legacy Phase 5 artifact, thresholds, gate calculations, and every Phase 5 gate
implementation file remain frozen byte-for-byte.

Phase 6 numeric source anchors use the additive
`source-decimal-times-frozen-multiplier-quantized-1e-12-v1` derivation contract. Its frozen
multiplier is stored at 1e-24 and its reproduced value is quantized at the prepared feature's
1e-12 precision, so canonical JSONB persistence/reload is byte-stable. The legacy unquantized
Phase 5 derivation formula and reports remain unchanged.

Every valid fixture retains six raw attempts: four completed, one failed, and one abandoned.
Each completed attempt binds one immutable model-output set. Model outputs are recomputable from
the prepared feature graph without reading labels. A frozen label-independent allocation rule maps
each output to a synthetic long/flat research weight of exactly zero or one; each gross-return cell
is then exactly `quantize(weight * label_value, 1e-12)` and binds the exact label interval and
source references. A zero weight is `NO_TRADE`: requested, filled, rejected, and unfilled quantity,
all six cost components, participation, gross return, and net return are all exactly zero. Each
completed trial persists its own baseline, all-cost-stress, and liquidity-stress ledger for every
prepared sample. Typed trial-economics artifacts, trial inner-validation and outer-return maps,
selected OOS predictions, selected trial-specific cost rows, and OOS returns all reconcile to the
same cells. Nested Phase 5 selection uses inner folds only.

Final confirmation is an explicit label-blind contract outside the feature-row, score,
model-output, trial, fit, and fold registries. It carries only pre-opening PIT geometry sources;
`label_value` is null, `label_source_references` is empty, and `label_opened` is false. Every
earlier feature row whose label interval intersects that reserved interval is represented by a
separate label-blind boundary-exclusion contract and is removed before fixture construction. A
hash-bound reproduction audit rebuilds the prepared payload from the exact immutable snapshot set
and requires byte-identical canonical payload and pipeline-input hashes. Baseline comparisons are
explicitly typed `used_for_selection=false`: their all-prepared-row metrics are descriptive audit
evidence and are never consumed by the Phase 5 selection path.

## Family A: cross-sectional ranking

The frozen feature list is `liquidity`, `momentum`, `quality`, `turnover`, `value`, and
`volatility`. Each explainable score is an exact sum of feature contributions with source
references. Every unique Phase 5 timestamp also persists the complete PIT-eligible cross-section:
all member features, linear scores and ranks, forward labels, and exact label references. The
transparent candidate is `sector-relative-rank-linear-v1`; its concordance is computed only among
members sharing that fixed timestamp. The sole nonlinear comparison is a real frozen depth-two
momentum/quality/volatility tree, `frozen-depth-two-tree-v2`, with persisted nonzero member
outputs, not a constant placeholder.
The versioned clipped within-sector transforms pool nine pre-evaluation observations across three
distinct PIT-eligible securities, persist the ordered raw train values and exact sources, and
recompute their frozen mean and standard deviation from that evidence. They bind the exact train
entity/sample ids and prohibit every Phase 5 evaluation id. The deterministic fixture intentionally uses one synthetic
`synthetic-diversified` sector so it can prove multi-security pooled-fit mechanics; it does not
claim sector breadth or real-market evidence. Universe evidence includes active, inactive, and delisted securities with
explicit delisting-return handling. Turnover, ADV participation, capacity, and concentration are
persisted; Family A uses the declared one-percent ADV participation limit consistently in the
prepared inputs and Phase 5 cost ledger. Family A also carries actual PIT rate evidence in both
directions (`+0.10` and `-0.20`) and the predeclared
`synthetic-predeclared-stress-2020-01` window, so its REGIME gate uses observations rather than a
compatibility projection. Baseline comparisons remain descriptive only. `phase6-a-pass-v2`
passes all 12 unchanged gates. `phase6-a-fail-cost-v2` uses the same research evidence but a
server-owned synthetic QA stress-policy variant and is rejected only by `COST_STRESS`; that
variant is not a production threshold.

## Family B: momentum and regime control

The frozen lag windows are 1, 5, 20, 63, 126, and 252 sessions, backed by the 305-session
calendar and at least 253 raw nominal bars for the evaluated active series. Raw unadjusted
nominal-price features remain separate from action-and-delisting-aware return construction.
The transparent features are lagged return, trend strength, realized volatility, and
drawdown. Corporate-action evidence and source-derived volatility-regime results are persisted.
The prepared `realized_volatility` feature retains its exact source-derived 1e-12 value. Only
the copy supplied to the unchanged Phase 5 component-cost engine is projected, half-even, to
1e-8 under `phase6-family-b-cost-volatility-1e-8-half-even-v1`. The fixture hash and every
completed trial configuration bind that projection id and quantum; the Family B specification's
transaction-cost-model id composes the unchanged Phase 5 model id with the same projection id.
This is a deterministic persistence-precision contract, not a policy threshold or performance
adjustment: it keeps every baseline, all-cost-stress, and liquidity-stress component, total, net
return, and OOS return exactly representable by the existing `NUMERIC(38,30)` columns while
preserving exact component totals and gross-minus-cost reconciliation. The Phase 5 engine and
migration remain unchanged.
Family B is not authorized to consume the Family A macro capability, so rate and crisis evidence
are explicitly recorded as unavailable; the numeric compatibility projection used to call the
unchanged Phase 5 engine is also hash-bound and is not represented as an observation. A separate
non-feature lifecycle test registry covers active, inactive, and delisted
series, requires explicit inception/termination timestamps, and binds delisting-return inputs.
Images, candlesticks, and named-chart-pattern classifiers
are prohibited. Family B reports only source-derived `volatility:*` regimes, never fabricated
rate or crisis results. Both Family B configurations finish `FAIL_REJECT`: PBO is `2/3`, above the
frozen `0.25` maximum, and REGIME remains `research_only` because volatility coverage plus the
unavailable rate/crisis inputs are incomplete. Their deterministic DSR probability is
approximately `0.6235247397449625` (numeric-reference tolerance `1e-12`), above the frozen
`0.50` minimum; DSR is not the blocker.

## Family C: official-event text overlay

The only text outputs are versioned structured features: novelty, direction, uncertainty,
risk change, and event tags. Every extraction records the exact source-version id, document
hash, availability/correction times, extractor and model version, prompt version/hash,
schema version, and entity-resolution method. The current extractor is a deterministic mock
because no provider credentials are approved. It cannot emit labels, signals, model
decisions, calls, allocations, sizes, promotion outcomes, or execution instructions.

A conventional linear downstream model consumes the versioned extracted features and is
compared descriptively with a frozen, nonzero one-session raw-OHLCV return-minus-range baseline.
Every baseline output persists the exact two PIT bar references, formula inputs, output, and
hash; `used_for_selection=false`, so neither baseline metric nor comparison outcome can touch
model selection. The extractor never supplies its label, score, or verdict.
Original and corrected documents remain distinct later observations, and extractor, model,
prompt, schema, entity-resolution, and content hashes make any drift visible. Every synthetic
social-attention record is a separate immutable Phase 4 observation linked to an exact prior
official source/document hash, marked manipulation-prone, and fixed at
`contributes_standalone=false`. The corroboration-negative configuration fails closed with
`official_corroboration_required` before a run is persisted. That block is derived by checking
the frozen negative requirement against exact official/social source-version, entity, listing,
and availability evidence; it is not an unconditional verdict keyed only by configuration id.
`phase6-c-pass-v2` truthfully finishes `FAIL_REJECT`: its DSR probability is approximately
`0.44167434869901306`, below the frozen `0.50` minimum; PBO is `2/3`, above the frozen `0.25`
maximum; and its unavailable rate/crisis inputs leave REGIME `research_only`. Family C's
successful cost stress and corroboration checks do not override those blockers.

## Persistence and API

Migration 0006 creates eight append-only tables for runs, snapshot bindings, attempts,
feature rows, scores, baseline comparisons, text extractions, and corroborations. Every table
rejects `UPDATE`, `DELETE`, and `TRUNCATE` with the exact message
`Phase 6 research artifacts are append-only`. Foreign keys use `RESTRICT`; lineage triggers
reconcile the exact mapping, snapshots, complete prepared artifact, Phase 5
policy/fixture/report or blocked outcome, the complete exact report-scoped trial ID/key/status
set, social observation, and
official source. Deferred completeness triggers require the exact child counts, arrays, and
ordinals at commit. Child identities and hashes are scoped by run so deterministic
configurations can coexist.

The API is create/read/list only:

- `POST /v1/research-runs`
- `GET /v1/research-runs`
- `GET /v1/research-runs/{run_id}`

FastAPI/Pydantic OpenAPI is the only TypeScript source. Research artifacts state that they are
synthetic, make no real-performance claim, grant no paper approval, and provide no investment
advice.

## Known limitations

- All data and results are deterministic mocks; no approved provider credentials are present.
- The sole synthetic `PASS_RESEARCH` artifact is `phase6-a-pass-v2`; it is research evidence only,
  not paper approval, execution readiness, or a claim of economic value.
- No claim is made that any family has real predictive or economic value.
- Capacity and available volatility-regime evidence are contract/QA demonstrations, not market
  estimates. Family A's rate/crisis evidence is synthetic PIT QA data; Family B and C record those
  inputs as unavailable and fail closed where required.
- No Phase 7 approval or execution capability exists.
