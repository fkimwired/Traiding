# Evaluation and promotion contract

## Authority and posture

This document is the Phase 5 acceptance standard for every strategy family. It is intentionally
stricter than a metric checklist. A positive backtest is a research result; promotion to simulated
paper trading is a governed state transition that requires every gate below to pass.

No threshold is silently invented. A versioned evaluation policy must be frozen before the final
holdout is opened. Any required value that is missing, invalid, or uncomputable produces
`BLOCKED_UNCOMPUTABLE` or `BLOCKED_MISSING_POLICY`; neither state is promotion-eligible.

## 1. Required evaluation-policy fields

The Phase 5 implementation must validate these fields before running model selection:

| Group | Required fields |
|---|---|
| Identity | `policy_id`, `policy_version`, `strategy_family`, `selection_scope`, `created_at_utc`, `approved_by` |
| Time geometry | decision timezone/calendar, label definition, `[t0,t1]` rule, outer folds, inner folds, train mode, purge rule, optional embargo rule, final confirmation interval |
| Sample adequacy | `min_oos_observations`, `min_independent_events`, missing-return policy, no-trade return policy |
| Selection accounting | primary selection metric, raw-trial definition, effective-trial method, `dsr_min_probability`, CSCV block count, tie policy, `pbo_max` |
| Costs | fee schedule id/date, spread source/fallback, impact model/version/calibration, latency/delay rule, borrow source, hard-to-borrow rule, baseline capacity/participation assumptions |
| Stress vector | `all_cost_multiplier >= 2`, spread multiplier, volatility multiplier, ADV multiplier, impact-coefficient multiplier, latency stress, borrow stress |
| Stress gates | minimum stressed net P&L/return, minimum stressed Sharpe, maximum stressed drawdown, maximum participation/capacity breach |
| Regimes | volatility definition/cut, rate definition/cut, crisis windows chosen before results |
| Risk | position, gross, net, sector, turnover, volatility, loss, and drawdown limits appropriate to the strategy |

Changing a selection, cost, stress, regime, or promotion field after seeing outer-fold or confirmation
results creates a new policy version and a new trial. The previous record is retained.

## 2. Point-in-time data gate (`DATA_PIT`)

### Required temporal fields

Each observation used by a decision must carry, as applicable:

- `event_time`: when the economic event occurred;
- `available_at`: the earliest accepted/publicly usable timestamp;
- `ingested_at`: when this system obtained the record;
- `valid_from` and `valid_to`: historical validity for mutable classifications/identities;
- `revision_id`: the specific vintage or amendment;
- `source_id` or accession/document id;
- stable security/instrument id plus ticker, listing, and exchange history.

The engine must prove `available_at <= decision_time` for every feature input. Date-only data requires
a conservative availability convention frozen in policy; it cannot be assumed available at midnight.
Amendments and data revisions are later observations, never retroactive replacements.

### Universe and returns

- Reconstruct eligibility at each decision time. Current constituents cannot populate history.
- Include inactive and delisted securities and the history of names, share classes, exchanges,
  identifiers, listings, and corporate actions.
- Preserve raw prices and corporate-action records. Back-adjusted series may calculate realized total
  returns, but nominal price features must not learn actions that occurred later.
- Treat missing delisting return as a data-quality exception, not zero. For a legacy CRSP-style source,
  the common combination is `(1 + RET) * (1 + DLRET) - 1`; source formats that already incorporate
  delistings must be detected to avoid double counting.
- Fundamental inputs use as-reported/vintage values and accepted/availability time, not fiscal
  period-end or the latest restatement.
- Macro inputs that revise use real-time vintages/release availability (for example ALFRED semantics),
  not today's FRED series pulled backward through history.

### Gate outcome

Any unexplained missing temporal field, future availability, current-membership leakage, revision
overwrite, or unhandled delisting blocks the affected run. Report counts, rates, example record ids,
date ranges, and a reason code—not merely a caveat.

## 3. Label, feature, and preprocessing contract

Each strategy specification must state:

- decision timestamp and executable decision lag;
- target/label formula and horizon;
- the label information interval `[t0,t1]` for every sample;
- feature formulas, source fields, lookback windows, and availability rule;
- universe eligibility and exclusions;
- rebalance, holding, overlap, and no-trade behavior;
- train-only fit rules for scaling, imputation, encoding, feature selection, and hyperparameters.

Every stateful transform implements `fit(train)` and `transform(other)` semantics. Full-sample
normalization, imputation, winsorization, sector statistics, feature selection, or threshold tuning is
a leakage defect.

## 4. Nested chronological evaluation (`CV_CHRONOLOGY`)

### Primary outer evaluation

Use rolling or expanding **past-only** walk-forward folds. For outer fold `k`:

1. Freeze a contiguous test interval strictly after its training/validation history.
2. Remove any candidate training sample whose label interval intersects the test interval. In the
   ordinary past-only case, this means purging boundary samples with `t1 >= test_start`.
3. Run feature fitting, model selection, and hyperparameter selection only inside nested chronological
   training/validation folds.
4. Fit the selected configuration on the permitted pre-test sample and predict the untouched outer
   test interval once.
5. Append predictions/returns to an OOS ledger without revising earlier folds.

The purge is derived from actual information intervals, not a hard-coded number of rows.

### Embargo semantics

A post-test embargo is used only for a purged K-fold or combinatorial-purged design in which samples
after the test interval are eligible to enter a training set. Those observations are excluded for the
policy-defined embargo duration. A strict past-only fold has no post-test training segment; calling a
future gap an “embargo” does not add protection.

### Final confirmation interval

Reserve at least one contiguous temporal confirmation interval before research begins. It is excluded
from feature design, hyperparameter choice, model choice, policy-threshold selection, and narrative
selection. Opening it consumes the holdout. A subsequent change creates a new research generation and
requires a new future confirmation interval.

Primary reference: López de Prado, *Advances in Financial Machine Learning*, Chapter 7
([publisher page](https://www.wiley-vch.de/en/areas-interest/finance-economics-law/finance-investments-13fi/finance-investments-special-topics-13fiz/advances-in-financial-machine-learning-978-1-119-48208-6)).

## 5. Complete trial registry (`TRIAL_REGISTRY`)

### Trial definition

`M_raw` counts every distinct strategy/feature/label/model/hyperparameter/portfolio/cost/filter
configuration that influenced selection against shared data. Count failed jobs, abandoned variants,
manual spreadsheet checks, negative results, and variants run outside the main UI. A unique immutable
config hash identifies each trial; deleting or resetting the registry is prohibited.

Each trial record stores:

- config and policy hashes;
- family and selection scope;
- OOS return series or explicit failure/no-return state on the common calendar;
- selection metric and Sharpe convention;
- parent/lineage links and timestamps;
- who/what initiated it;
- failure reason when incomplete.

Selection may occur within a family and across families. The report must show both scopes where both
influenced the winner.

### Effective trials

Raw correlated variants are not independent. The policy names and versions the method used to
estimate `N_eff`; the report includes `M_raw`, `N_eff`, cross-trial Sharpe variance `V_SR`, and the
inputs needed to reproduce the estimate. Setting `N_eff = 1` without evidence is a blocking defect.

## 6. Deflated Sharpe Ratio (`DSR`)

Compute DSR on stitched, net-of-baseline-cost outer-fold OOS returns using one documented return
frequency. The statistic is a probability, not a “haircut Sharpe.” With per-period estimated Sharpe
`SR_hat`, sample length `T`, return skew, and ordinary kurtosis (normal = 3), the probability uses:

```text
DSR = Φ(
  ((SR_hat - SR_0) * sqrt(T - 1))
  / sqrt(1 - skew*SR_hat + ((kurtosis - 1)/4)*SR_hat²)
)
```

The multiple-testing benchmark is estimated from cross-trial Sharpe variance and effective trials,
approximately:

```text
SR_0 = sqrt(V_SR) * [
  (1 - γ_EM) Φ⁻¹(1 - 1/N_eff)
  + γ_EM Φ⁻¹(1 - 1/(N_eff * e))
]
```

where `γ_EM` is the Euler–Mascheroni constant. The implementation records the exact finite-sample
formula, estimator, annualization convention, `T`, skew, kurtosis, `V_SR`, `M_raw`, and `N_eff`.

Serial correlation can invalidate naive square-root annualization and overstate effective sample
size. Report autocorrelation and apply the policy's HAC/effective-sample or block-bootstrap
sensitivity; do not silently mix annualized and per-period Sharpe in the formula.

**Pass:** `DSR >= dsr_min_probability`. Missing trial history, zero/invalid trial variance,
unestimable inputs, or an unset threshold blocks promotion.

Primary source: Bailey and López de Prado,
[“The Deflated Sharpe Ratio”](https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf).

## 7. Probability of Backtest Overfitting (`PBO`)

PBO evaluates the optimization/selection procedure, not one isolated strategy. Build a synchronous
`T × N` matrix of net returns for all `N` eligible configurations on a common calendar. Missing and
no-trade values follow a policy fixed before calculation.

For an even number `S` of contiguous blocks (minimum adequacy chosen in policy):

1. Enumerate the `C(S, S/2)` symmetric train/test block combinations.
2. Choose the best in-sample configuration under the frozen selection metric.
3. Rank that same configuration out of sample using the frozen tie rule.
4. Define normalized OOS rank `ω = rank_OOS / (N + 1)` and logit
   `λ = log(ω / (1 - ω))` under the documented rank orientation.
5. Report `PBO = mean(λ < 0)` plus the full logit/rank distribution and degradation plot data.

The artifact stores the matrix hash, configuration order, timestamps, `S`, split combinations,
selection metric, tie rule, and all ranks. PBO does not repair leakage or unrealistic costs and does
not replace chronological walk-forward evaluation.

**Pass:** `PBO <= pbo_max`. Too few synchronized trials/blocks, an unset threshold, or a missing
matrix is promotion-blocking.

Primary source: Bailey et al.,
[“The Probability of Backtest Overfitting”](https://escholarship.org/content/qt4w1110bb/qt4w1110bb.pdf).

## 8. Cost, liquidity, and capacity gate (`COST_STRESS`)

### Baseline cost ledger

For every simulated fill, separately record:

- commissions and applicable regulatory/exchange fees;
- quote-derived half-spread or documented fallback spread;
- market impact, including model and calibrated parameter vintage;
- latency/delay and opportunity cost;
- borrow/locate fee and hard-to-borrow availability for shorts;
- rejected/unfilled quantity and participation/capacity state.

A square-root proxy may be used as a research model:

```text
terminal_impact ≈ Y * daily_volatility * sqrt(order_quantity / daily_ADV)
```

`Y` must be calibrated by asset, venue/order style, and regime. Terminal impact is not automatically
average execution shortfall. Quote slippage, delay, and impact components must be defined so the same
effect is not counted twice. Missing borrow or hard-to-borrow state means the short is unavailable,
not free.

### Required stress scenarios

At minimum rerun identical positions under:

1. **All-cost stress:** every applicable baseline commission, spread, impact, delay, and borrow
   component multiplied by at least `2.0`.
2. **Spread/liquidity stress:** independently widen spread, reduce ADV, increase volatility and the
   impact coefficient, increase latency, and stress borrow using the frozen vector.

The 2× scenario is a governance heuristic, not a universal empirical law. Parameters and exact gates
are approved before the holdout. Report gross P&L, each cost component, net P&L, net Sharpe,
drawdown, turnover, fill/rejection rates, and capacity for baseline and every stress.

**Minimum universal failure definition:** the edge has disappeared if stressed aggregate OOS net P&L
or annualized net return is non-positive, or stressed net Sharpe is non-positive. The policy may set
stricter positive minima and drawdown/capacity limits. Any required stress failure blocks promotion.

Useful empirical references include Almgren et al.
([transaction-cost estimation](https://www.cis.upenn.edu/~mkearns/finread/costestim.pdf)) and Bucci
et al. ([linear-to-square-root crossover](https://arxiv.org/abs/1811.05230)).

## 9. Leakage red-flag gate (`LEAKAGE`)

Run all checks on every fold and final artifact. One hit blocks promotion.

| ID | Blocking check | Minimum evidence |
|---|---|---|
| `L01` | Corporate-action/adjusted-price lookahead | raw/action/as-of series comparison and action timestamps |
| `L02` | Fundamental period-end or restatement leakage | accepted/availability timestamp and revision trace |
| `L03` | Feature available after decision | row-level `available_at <= decision_time` assertion |
| `L04` | Target or future proxy in features | lineage/column dependency scan plus adversarial feature review |
| `L05` | Current universe/index membership in history | point-in-time membership reconstruction test |
| `L06` | Full-sample preprocessing statistics | fold-scoped fit ids and train-only statistic assertions |

Also report duplicate grain, future timestamps, unexpected revisions/backfills, identifier breaks,
join multiplication/loss, missing delisting outcomes, stale partitions, and source-schema drift. These
data-quality issues receive severity and can independently block the run when decision-relevant.

## 10. Regime, crisis, exposure, and robustness reporting

At minimum report:

- low/high volatility under a predeclared observable rule;
- rising/falling rate under vintage-aware release/market data;
- each predeclared crisis/stress window separately;
- calendar subperiod and outer-fold performance;
- long/short leg, sector, size, beta/factor, gross/net exposure, and concentration where applicable;
- turnover and capacity by regime;
- result sensitivity to reasonable label, rebalance, and cost choices without selecting on the final
  confirmation interval.

Crisis windows are chosen before results and excluded from design when designated as holdouts. A
strategy that works in one regime may remain a labeled research candidate, but the dependency must be
visible and promotion policy determines eligibility.

## 11. Required metrics and calculation metadata

Every report includes gross and net versions where meaningful:

- Sharpe, Sortino, Calmar, annualized return, volatility, maximum drawdown and duration;
- turnover, hit ratio, average win/loss, gross/net exposure, concentration, participation and capacity;
- P&L by outer fold, calendar period, strategy leg, and required regime;
- commission, spread, impact, delay, borrow, and total cost attribution;
- slippage/cost sensitivity and every stress-vector outcome;
- `M_raw`, `N_eff`, `V_SR`, DSR probability/inputs, PBO/inputs;
- sample size, independent-event estimate, missing/no-trade counts, and autocorrelation diagnostics.

Each number records formula id/version, units, frequency, annualization factor, timezone/calendar,
population, exclusions, and denominator. Do not average group-level ratios without correct weights.

## 12. Reproducibility artifact

Every signal, backtest report, and eventual paper trade carries:

```text
artifact_id
artifact_type
config_hash
evaluation_policy_id + hash
data_snapshot_id + provider/source versions
code_version_git_sha
random_seed
raw_trial_count
effective_trial_count + method
created_at_utc
decision_time_utc (when applicable)
parent_artifact_ids
```

The report also saves fold boundaries, sample ids/hashes, feature/prompt/model versions, prediction
ledger, position/fill/cost ledger, metrics inputs, gate thresholds, numeric results, reason codes, and
warnings. The append-only database table established in Phase 1 is a foundation; Phase 5 must add the
full domain artifacts without mutating past records.

## 13. Promotion state machine

| State | Meaning | Paper eligible? |
|---|---|---|
| `PASS_RESEARCH` | Every required data, chronology, leakage, cost, DSR, PBO, risk, and reproducibility gate passes | Only after Phase 7 manual approval |
| `FAIL_REJECT` | A numeric/evidence gate fails under the frozen policy | No |
| `BLOCKED_MISSING_POLICY` | A required threshold, source, interval, or rule was not frozen | No |
| `BLOCKED_UNCOMPUTABLE` | Required DSR/PBO/cost/data result cannot be computed reliably | No |
| `RESEARCH_ONLY_REGIME_DEPENDENT` | Valid evidence is too narrow for promotion but useful for monitoring | No |

“Flagged” always means blocked. A warning cannot be used to bypass a hard gate. Phase 7 never mutates
this Phase 5 state machine: it may append a separate historical `APPROVED_PAPER` assessment only when
all independent evidence passes. A later revocation is another immutable event and blocks reuse of
the authorization without changing either historical artifact.

## 14. Machine-checkable Phase 5 definition of done

The Phase 5 handoff must provide commands/tests that prove:

1. a fixture with overlapping labels has the exact expected purged rows;
2. past-only folds contain no observation at or after the test boundary, while a CPCV fixture applies
   the configured post-test embargo only where later training rows exist;
3. preprocessing statistics differ by fold and are fit only on train ids;
4. a point-in-time fixture catches all six leakage defects and each blocks promotion;
5. trial count includes failed/abandoned variants and cannot be reset or deleted;
6. published/synthetic reference inputs reproduce DSR and PBO within declared numeric tolerances;
7. DSR/PBO missing inputs and unset thresholds fail closed;
8. baseline, ≥2× all-cost, and independent liquidity stress reruns preserve positions and expose
   component-level cost changes;
9. any stressed non-positive edge blocks promotion;
10. a full mock run writes all reproducibility fields, numeric gate inputs/outcomes, warnings, and
    reason codes and is visible through the API/UI;
11. identical config/data/code/seed reproduces the artifact hash and metrics within tolerance;
12. no real performance is claimed and no live execution code exists.
