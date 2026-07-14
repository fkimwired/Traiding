# Phase 6 Research Decisions

## Scope and outcome vocabulary

Phase 6 implements research-only pipelines A, B, and C. It does not implement paper
approval, pre-order controls, a broker, positions, orders, paper execution, or live
execution. `PASS_RESEARCH` remains a Phase 5 research result and is never paper approval.
All reported values are deterministic synthetic QA evidence; none is a real-performance
claim or personalized investment advice.

The server-owned deterministic configurations are:

- `phase6-a-pass-v1` and `phase6-a-fail-cost-v1`
- `phase6-b-pass-v1` and `phase6-b-fail-crash-v1`
- `phase6-c-pass-v1` and `phase6-c-fail-corroboration-v1`

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
  eligibility, price-basis, label, and unchanged leakage-gate evidence.

The Phase 4 default fixture/profile/configuration remain frozen. A separately versioned
Phase 6 synthetic adapter supplies 1,195 deterministic records for a one-source mapping:
11 identity, listing, sector, and lifecycle records; five PIT membership records; 852 raw
nominal OHLCV bars; one corporate action; one delisting event; 12 as-reported fundamentals;
305 calendar sessions; three action-aware return bundles; and five official-event records
(two metadata records, two versioned document-content records, and one immutable social-
attention record). The 305-session history makes the frozen 252-session Family B lag
computable. Family C documents and social corroboration are rebound to exact persisted
official source-version ids. A mapping with two official sources adds five records for the
second source without changing any pre-existing observation.

## Phase 5 bridge

Every valid run is evaluated only by the unchanged Phase 5 engine and its exact ordered
gate vocabulary:

`DATA_PIT`, `CV_CHRONOLOGY`, `PREPROCESSING`, `TRIAL_REGISTRY`, `DSR`, `PBO`,
`COST_STRESS`, `LEAKAGE`, `SAMPLE_ADEQUACY`, `REGIME`, `RISK_LIMITS`, and
`REPRODUCIBILITY`.

The additive lineage bridge permits report-wide required-capability witnesses that need not be
misrepresented as an individual sample input, while every sample carries its exact same-entity PIT
feature subset. It does not special-case a gate. Every A/B/C sample carries real synthetic OHLCV
price-basis evidence and point-in-time universe-membership reconstruction, so the unchanged
L01 and L05 implementations run normally alongside L02, L03, L04, and L06. Pipeline feature
rows and labels are prepared first, then used as the exact Phase 5 samples and trial inputs;
the resulting fixture identity binds the complete prepared-pipeline input hash. Missing
policy, source, PIT, delisting, leakage, or computable gate evidence still blocks. The legacy
Phase 5 artifact, thresholds, gate calculations, and every Phase 5 gate implementation file
remain frozen byte-for-byte.

Phase 6 numeric source anchors use the additive
`source-decimal-times-frozen-multiplier-quantized-1e-12-v1` derivation contract. Its frozen
multiplier is stored at 1e-24 and its reproduced value is quantized at the prepared feature's
1e-12 precision, so canonical JSONB persistence/reload is byte-stable. The legacy unquantized
Phase 5 derivation formula and reports remain unchanged.

Every valid fixture retains six raw attempts: four completed, one failed, and one abandoned.
Their predictions and gross returns derive from the persisted prepared feature rows and
labels. Nested Phase 5 selection uses inner folds only; the reserved final confirmation interval is
nonempty and excluded from selection. Baseline comparisons are explicitly typed
`used_for_selection=false`: their all-prepared-row metrics are descriptive audit evidence and are
never consumed by the Phase 5 selection path.

## Family A: cross-sectional ranking

The frozen feature list is `liquidity`, `momentum`, `quality`, `turnover`, `value`, and
`volatility`. Each explainable score is an exact sum of feature contributions with source
references. Every unique Phase 5 timestamp also persists the complete PIT-eligible cross-section:
all member features, linear scores and ranks, forward labels, and exact label references. The
transparent candidate is `sector-relative-rank-linear-v1`; its concordance is computed only among
members sharing that fixed timestamp. The sole nonlinear comparison is a real frozen depth-two
momentum/quality/volatility tree with persisted nonzero member outputs, not a constant placeholder.
The versioned clipped within-sector transforms pool nine pre-evaluation observations across three
distinct PIT-eligible securities, bind those exact train entity/sample ids and source records, and
prohibit every Phase 5 evaluation id. The deterministic fixture intentionally uses one synthetic
`synthetic-diversified` sector so it can prove multi-security pooled-fit mechanics; it does not
claim sector breadth or real-market evidence. Universe evidence includes active, inactive, and delisted securities with
explicit delisting-return handling. Turnover, ADV participation, capacity, and concentration are
persisted. The pass fixture survives the transparent baseline and rejects the nonlinear comparison;
the negative fixture is rejected by the unchanged Phase 5 cost-stress gate.

## Family B: momentum and regime control

The frozen lag windows are 1, 5, 20, 63, 126, and 252 sessions, backed by the 305-session
calendar and at least 253 raw nominal bars for the evaluated active series. Raw unadjusted
nominal-price features remain separate from action-and-delisting-aware return construction.
The transparent features are lagged return, trend strength, realized volatility, and
drawdown. Corporate action, volatility/rate regime, and declared crash-window evidence is
persisted. A separate non-feature lifecycle test registry covers active, inactive, and delisted
series, requires explicit inception/termination timestamps, and binds delisting-return inputs.
Images, candlesticks, and named-chart-pattern classifiers
are prohibited. The pass fixture covers every declared regime. The negative fixture omits
complete crash evidence and therefore remains `RESEARCH_ONLY_REGIME_DEPENDENT`; it cannot
become `PASS_RESEARCH`.

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
- No claim is made that any family has real predictive or economic value.
- Capacity and regime evidence are contract/QA demonstrations, not market estimates.
- No Phase 7 approval or execution capability exists.
