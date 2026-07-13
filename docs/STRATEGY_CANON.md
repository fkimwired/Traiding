# Strategy canon

## Status and use

This is the research source of truth for interpreting the six Instagram-derived archetypes. The
labels are not strategies by themselves. Each record below states the economic claim, the canonical
family that could test it, its evidence posture, data contract, failure modes, capacity/implementation
limits, manipulation risk, and build/defer/reject verdict.

`BUILD` means “advance to deeper research,” not “profitable,” “approved,” or “trade.” No source post
was supplied with the original brief, so these are archetype briefs rather than fabricated
post-specific extractions. Phase 2 must preserve that distinction.

## Canon summary

| ID | Marketed archetype | Canonical test | Evidence posture | Key constraint | Verdict |
|---|---|---|---|---|---|
| A | Stock-picking AI | Cross-sectional equity ranking | Strongest family-level basis | Point-in-time characteristics and delistings | **BUILD first** |
| B | Price-pattern AI | Time-series momentum + regime + volatility control | Strong for momentum; weak for literal patterns | Reversal/crash and cost-aware turnover | **BUILD second** |
| C | Social/news AI | Event-driven official-text feature overlay | Mixed; official event text is more defensible than social | Corroboration, latency, licensing, manipulation | **BUILD as overlay** |
| D | Correlation-divergence AI | Pairs / statistical arbitrage | Historically documented, materially decayed | Borrow, breaks, crowding, thin net edge | **DEFER** |
| E | Order-flow AI | Limit-order-book / microstructure prediction | Real at a different horizon and stack | L2/L3 data, queue state, latency, colocation | **REJECT here** |
| F | Unusual-options AI | Options-flow and IV-versus-RV analytics | Real sub-effects; retail framing is noisy | OPRA-grade history, surfaces, greeks, tail risk | **DEFER read-only** |

## A. Stock-picking AI → cross-sectional equity ranking

**Marketed claim.** An AI can rank a stock universe and select tomorrow's or next month's winners.

**Canonical, testable claim.** At a fixed decision timestamp, rank a point-in-time eligible universe
by features known then; form a constrained long-only or long/short portfolio; measure future total
returns over a declared horizon. Compare a simple linear/rank baseline with a tree model to determine
whether nonlinear interactions add stable net-of-cost information.

**Empirical grounding.** Cross-sectional return prediction has the best family-level basis of the six.
Gu, Kelly, and Xiu find that nonlinear methods can exploit interactions among established predictors,
with momentum, liquidity, and volatility among important groups. This supports a research candidate,
not an assertion that a chosen feature library or modern sample will survive costs. See the
[published RFS article](https://academic.oup.com/rfs/article/33/5/2223/5758276).

**Minimum data contract.** Stable security identifiers; listing, exchange, ticker, and membership
history; inactive/delisted securities; raw prices; corporate actions; delisting-aware total returns;
filing accepted/availability timestamps; as-reported values plus revisions; sector history; shares,
volume, and ADV. Every feature row needs `available_at <= decision_time`.

**First research design.** Liquid U.S. equities; sector-relative train-only transforms; multi-horizon
momentum, realized volatility, liquidity/turnover, and a deliberately small group of as-reported
quality/value features; weekly or monthly rebalance baseline; explicit turnover penalty. The model
must beat naive rank and equal-weight baselines out of sample after costs.

**Failure and falsification.** Current-index survivorship; restated fundamentals; period-end timing;
cross-sectional scaling fit on the full sample; delisting returns silently set to zero; feature-set
mining; microcap concentration; factor crash; sector/size proxy masquerading as idiosyncratic alpha;
spread and impact consuming a thin long-short spread. Kill the research claim if the rank IC and
portfolio edge fail across independent temporal folds, regimes, and calibrated cost stresses.

**Capacity and risk.** Potentially high on liquid names at slower cadence, but capacity must be
estimated from portfolio-level ADV participation and concentration. “High capacity” is a hypothesis,
not a fixed label.

**Manipulation risk.** Low for core market/fundamental features; higher for optional alternative data.

**Verdict.** **BUILD first.** This is the flagship research family because it is diversified,
testable, and compatible with ordinary infrastructure. It remains promotion-blocked until the
complete evaluation contract in `docs/EVALS.md` passes.

## B. Price-pattern AI → time-series momentum and regime control

**Marketed claim.** An AI recognizes flags, breakouts, or other chart shapes before price moves.

**Canonical, testable claim.** Trend direction and strength computed from lagged returns may predict
the sign or magnitude of future returns; volatility scaling and an explicitly trained regime model
may improve risk-adjusted net results. Literal named chart shapes are not the alpha premise.

**Empirical grounding.** Time-series momentum has documented evidence across futures and asset
classes in Moskowitz, Ooi, and Pedersen's
[Journal of Financial Economics paper](https://www.sciencedirect.com/science/article/pii/S0304405X11002613).
Relative momentum originates in a separate cross-sectional family. Evidence is regime dependent and
does not remove reversal or implementation risk.

**Minimum data contract.** As-of raw and adjusted OHLCV; corporate-action records; decision calendar;
liquidity/ADV; realized-volatility inputs; instrument inception/termination; optional macro releases
with vintage/availability time. Back-adjusted return calculation and nominal price features must be
kept conceptually separate.

**First research design.** Liquid ETFs or equities at daily cadence; 1/5/20/63/126/252-day lagged
returns, realized volatility, drawdown depth, and transparent trend-strength baselines; volatility
target; maximum-drawdown guardrail; no image or candlestick classifier.

**Failure and falsification.** Trend crashes in sharp rebounds; exposure levering when volatility is
temporarily low; future corporate actions leaking through nominal price features; parameter selection
on crisis outcomes; high turnover at short horizons; a regime classifier that merely restates current
returns. Kill or narrow the claim if the edge is concentrated in one era, one asset, or one volatility
scaling choice.

**Capacity and risk.** Moderate to high in liquid products at daily/weekly horizons. Capacity declines
as rebalance speed, concentration, and volatility targeting amplify turnover.

**Manipulation risk.** Low. The important risks are specification, regime, and execution realism.

**Verdict.** **BUILD second** as momentum/regime/volatility research, explicitly rejecting the literal
chart-pattern premise.

## C. Social/news sentiment AI → official-event text overlay

**Marketed claim.** An AI reads social posts and news mood, then trades bullish or bearish sentiment.

**Canonical, testable claim.** Text released before a decision time can produce versioned structured
features—novelty, direction, uncertainty, risk-factor change, and event tags—that may add incremental
forecast value to a non-text baseline. Social content may measure attention only after an official
source corroborates the event; it can never independently create a signal.

**Empirical grounding.** Tetlock documents short-horizon relationships between media pessimism and
market outcomes in the
[Journal of Finance article](https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.2007.01232.x).
This supports a narrow, testable information channel. It does not validate arbitrary social feeds,
LLM-generated directions, or durable standalone sentiment alpha.

**Minimum data contract.** SEC accession and accepted timestamps; earnings releases/transcripts with
availability time; licensed reputable news with publication/correction history; entity resolution;
document hashes; ingestion time; prompt, model, and extraction-schema versions; official-source link
for any social attention record.

**First research design.** Use filings, issuer releases, transcripts, and licensed news. Freeze the
text and extraction version. Train a conventional downstream model on structured features. Test
incremental value over event, price, and fundamental baselines. Treat revised/corrected documents as
new later observations.

**Failure and falsification.** Coordinated promotion; bots; duplicated syndicated stories; revision
and timestamp leakage; entity mistakes; LLM prompt drift; sentiment that follows price; redistributing
licensed text; an embedding/model trained on future documents; uncorroborated social content. Reject
the feature block if it does not add stable incremental OOS value after latency and costs.

**Capacity and risk.** Low to moderate because event signals decay and may cluster. Latency is measured
from source availability to feasible decision, not from ingestion convenience.

**Manipulation risk.** **High for social media.** Official documents are lower-manipulation sources but
still require timestamp, correction, and issuer-claim labeling.

**Verdict.** **BUILD third, overlay only.** The LLM is a traceable feature extractor, never the alpha
engine or instruction generator.

## D. Correlation-divergence AI → pairs/statistical arbitrage

**Marketed claim.** Correlated securities that diverge will reliably snap back.

**Canonical, testable claim.** A pair or basket selected without future information may exhibit a
stable relative-value relation; a bounded residual deviation may mean-revert after spreads, impact,
short borrow, and structural-break controls.

**Empirical grounding.** Gatev, Goetzmann, and Rouwenhorst document historical pairs results in the
[RFS article](https://academic.oup.com/rfs/article/19/3/797/1646694). The original evidence does not
guarantee a contemporary edge; later crowding, costs, and changing market structure are central to the
current test.

**Minimum data contract.** Point-in-time universe and corporate actions; delistings; synchronized
prices; sector/corporate-event history; borrow rate, locate/availability, and hard-to-borrow state;
short-sale constraints.

**Failure and falsification.** Selecting pairs over the full sample; confusing correlation with a
stable relation; M&A or business-model breaks; crowded unwind; stale/absent borrow; short squeeze;
portfolio overlap and hidden factor exposure. A missing borrow observation is unavailable, not free.

**Capacity and risk.** Low to moderate and highly name-dependent. Both legs' liquidity and borrow bind.

**Manipulation risk.** Medium; not usually content manipulation, but thin-name prices and short
availability can make apparent convergence non-executable.

**Verdict.** **DEFER.** A later prototype may backtest only when borrow and break handling are first-
class. It is not in the top-three pack.

## E. Order-flow AI → limit-order-book microstructure prediction

**Marketed claim.** Retail-visible order flow reveals “smart money” and supports repeatable scalps.

**Canonical, testable claim.** Full-depth book and message state can predict very short-horizon price
or order-flow outcomes conditional on queue position and execution latency.

**Empirical grounding.** Order-flow imbalance is a legitimate microstructure variable; for example,
Cont, Kukanov, and Stoikov analyze its relationship with price changes in
[The Financial Review](https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6288.2012.00343.x).
The evidence's horizon and data requirements are the reason this is out of scope.

**Minimum data contract.** Licensed L2/L3 messages, venue sequence and clock synchronization, order
state, queue reconstruction, cancels, trades, fees/rebates, and realistic colocated latency.

**Failure and falsification.** Aggregated retail feed substituted for book state; midpoint fills;
missing queue priority; ignoring adverse selection; model latency greater than signal half-life;
unavailable exchange rights; a simulator that grants fills without liquidity.

**Capacity and risk.** Low per signal and operationally specialized. Infrastructure is inseparable
from the strategy.

**Manipulation risk.** Medium through spoofing and transient displayed liquidity; infrastructure risk
is **high**.

**Verdict.** **REJECT for this platform.** Record the rationale; create no service, adapter, model, or
strategy scaffold for it.

## F. Unusual-options AI → options-flow and IV-versus-RV analytics

**Marketed claim.** Unusual option volume reveals informed “smart money” that should be followed.

**Canonical, testable claim.** Specific, carefully defined options variables—signed volume with
classification uncertainty, implied-versus-realized volatility, skew, term structure, and event
context—may contain information after fees, surfaces, exercise/assignment, and tail risk.

**Empirical grounding.** Pan and Poteshman study information in option volume in the
[RFS article](https://academic.oup.com/rfs/article/19/3/871/1646718). That evidence does not validate
retail “unusual activity” alerts, whose side, hedge, roll, spread legs, and intent are often unknown.

**Minimum data contract.** Licensed OPRA-grade chains/trades/quotes; symbology history; corporate
actions; rates and dividends; IV surface; greeks with model version; open interest timing; exercise,
assignment, fees, spreads, and event calendar.

**Failure and falsification.** Treating multi-leg/hedging flow as directional; using final open
interest before it was available; survivorship in expired contracts; stale or crossed quotes; model
surface instability; ignoring spread/tail losses; double counting dealer-flow narratives.

**Capacity and risk.** Data- and contract-specific; wide spreads and tail exposure can dominate.

**Manipulation risk.** Medium. Interpretation risk is exceptionally high.

**Verdict.** **DEFER to read-only analytics.** A later phase may display IV/RV and flow diagnostics;
the first strategy pack must not emit option signals.

## Deterministic verdict rules for Phase 3

The closed machine verdict vocabulary is `BUILD_RESEARCH`, `DEFER`, `DEFER_READ_ONLY`,
`REJECT_PLATFORM`, and `NON_TESTABLE`. “Build first/second/third” remains research-priority prose, not
additional verdict values. Phase 5 promotion states are a separate later contract.

- A structurally non-testable or ambiguously classified card maps to `NON_TESTABLE` before family
  rules; deterministic mapping must not invent an action rule or horizon.
- Price-pattern framing maps to B with `BUILD_RESEARCH` and explicitly excludes literal chart images
  as alpha.
- Stock-picking/ranking framing maps to A with `BUILD_RESEARCH`.
- Social/news framing maps to C with `BUILD_RESEARCH` only when its Phase 2 contribution gate is
  clear; otherwise it maps to `DEFER` with `OFFICIAL_CORROBORATION_REQUIRED`.
- Correlation-divergence framing maps to D with `DEFER` and mandatory borrow requirements.
- Order-flow/book/scalp/sub-second framing maps to E with `REJECT_PLATFORM` and no scaffold.
- Unusual-options framing maps to F with `DEFER_READ_ONLY`.
