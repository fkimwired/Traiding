# Research Supplement — AI Trading Research & Paper-Trading Platform

**Purpose.** This document is the *source of truth* for the six Instagram-derived
trading ideas and for how the platform must validate any strategy before it is
allowed near paper trading. The build prompt references this file by name. Where
this document and marketing language on the original posts disagree, this
document wins.

**Standing position.** This is a research-to-paper-trading platform. Nothing here
is investment advice, and no strategy described below is asserted to be
profitable out of sample. The point of the platform is to *find out*, under
honest assumptions, and to reject ideas that only look good because of survivorship,
lookahead, cost-blindness, or multiple testing.

---

## Part 1 — The six idea archetypes, translated

Instagram "AI trading" content clusters into six recurring archetypes. Each is
restated as what it actually is in quant terms, graded on evidence and buildability,
and given a verdict. The verdicts drive the Strategy Canon and the build-order in
the prompt.

### Summary

| # | Post archetype ("what it's sold as") | Canonical family | Evidence base | Manipulation risk | Verdict |
|---|--------------------------------------|------------------|---------------|-------------------|---------|
| 1 | Price-pattern AI ("detects breakouts") | Medium-frequency trend / regime | Strong *for momentum*, weak for literal chart patterns | Low | **BUILD** (Strategy B) |
| 2 | Social/news sentiment AI | Filings/news NLP **overlay**, not standalone | Mixed; news > social; social is reflexive | **High** (social) | **BUILD as overlay** (Strategy C), social gated |
| 3 | Stock-picking AI ("ranks winners") | Cross-sectional equity ranking | Strongest of the six | Low | **BUILD** (Strategy A) — lead |
| 4 | Correlation-divergence AI | Pairs / stat-arb | Historically real, heavily decayed | Medium | **DEFER** (prototype only) |
| 5 | Order-flow AI ("smart money") | Microstructure / order-book | Real at sub-second scale, not reproducible at retail | Medium | **REJECT for this platform** |
| 6 | Unusual-options AI | Options-flow / IV-vs-RV | Real signals exist, buried in data/infra cost | Medium | **DEFER** (Phase 2 analytics, read-only) |

### 1. Price-pattern AI → time-series momentum & regime model

- **Marketed as:** an AI that "sees" chart patterns (flags, head-and-shoulders,
  breakouts) and predicts the next move.
- **What it actually is:** the only price-only effects with durable out-of-sample
  support are **time-series (absolute) momentum** and **cross-sectional momentum**.
  Literal visual chart-pattern detection has weak-to-no robust evidence and is a
  classic overfitting trap. Reframe the idea as trend/momentum with a volatility
  overlay, not pattern recognition.
- **Grounding:** Moskowitz, Ooi & Pedersen (2012), *Time Series Momentum*;
  Jegadeesh & Titman (1993) on relative momentum. Both document persistent but
  regime-dependent effects; both suffer periodic **momentum crashes** (e.g. the
  2009 rebound).
- **Required data:** adjusted OHLCV (split/dividend adjusted), corporate actions,
  a liquidity screen, a volatility estimator.
- **Failure modes:** overfitting to visual features; lookahead via adjusted-close
  built with future dividends; regime dependence; crash risk on sharp reversals.
- **Capacity:** moderate-to-high on liquid names at daily/weekly frequency.
- **Verdict: BUILD** as Strategy B, but only as momentum + regime classifier +
  volatility targeting + a hard max-drawdown guardrail. Do **not** build a
  "chart pattern classifier" as the alpha source.

### 2. Social/news sentiment AI → filings/news NLP overlay (not standalone)

- **Marketed as:** an AI that reads Twitter/Reddit/news and trades the mood.
- **What it actually is:** an NLP feature layer. News sentiment has modest
  short-horizon predictive value; **social-media sentiment is reflexive and
  manipulation-prone** and largely reflects price rather than leading it (the
  meme-stock dynamic). It must never be a standalone signal.
- **Grounding:** Tetlock (2007) on media pessimism predicting short-horizon
  returns and reversals; earnings-call tone literature. Social sentiment has far
  weaker, less stable evidence and documented pump-and-dump contamination.
- **Required data:** reputable news feed, SEC EDGAR filings, earnings-call
  transcripts. Social sentiment permitted **only** as a secondary "attention"
  feature and **only** when corroborated by an official-source event.
- **Failure modes:** manipulation/coordinated posting; reflexivity; latency
  (sentiment lagging price); source licensing and redistribution limits.
- **Capacity:** low-to-moderate; edge decays within days.
- **Verdict: BUILD as Strategy C (event-driven NLP overlay).** Any purely social
  signal is flagged manipulation-prone and blocked from producing a signal
  without official-data corroboration. The LLM extracts structured features; it
  never emits trade instructions.

### 3. Stock-picking AI → cross-sectional equity ranking

- **Marketed as:** an AI that ranks stocks and picks the winners.
- **What it actually is:** the best-founded idea of the six — a cross-sectional
  ML model ranking a universe on engineered factors, rebalanced periodically.
- **Grounding:** Gu, Kelly & Xiu (2020), *Empirical Asset Pricing via Machine
  Learning*, and the broader factor literature (momentum, value, quality,
  low-volatility, size). ML adds value mainly through non-linear interactions of
  known factors, not by discovering magic.
- **Required data:** **point-in-time** fundamentals (as-reported, lagged from
  *filing date* not period-end), adjusted OHLCV, sector classifications,
  corporate actions, and **delisting-aware total returns** for a survivorship-free
  universe.
- **Failure modes:** survivorship bias; using restated fundamentals (lookahead);
  crowded factors; costs eating a thin cross-sectional spread; multiple testing
  across large feature sets.
- **Capacity:** high at monthly/weekly rebalance on large-cap.
- **Verdict: BUILD as Strategy A — the flagship.** Baseline linear/tree model
  first, gradient-boosted model as the stronger placeholder, sector-relative
  z-scored features, explicit turnover control.

### 4. Correlation-divergence AI → pairs / statistical arbitrage

- **Marketed as:** an AI that finds correlated pairs that diverged and bets on
  reconvergence.
- **What it actually is:** classic pairs/stat-arb — historically profitable,
  cointegration-based, but heavily arbitraged away since the early 2000s.
- **Grounding:** Gatev, Goetzmann & Rouwenhorst (2006). Documents real historical
  profits *and* their post-decay; profitability is now marginal and cost-sensitive.
- **Required data:** adjusted OHLCV, corporate actions, **borrow fees and
  hard-to-borrow status** (this strategy requires shorting), sector maps.
- **Failure modes:** cointegration breakdown; structural breaks (an M&A blows up
  a "pair"); crowding; borrow cost and availability; needs short-side infra the
  first three strategies don't.
- **Capacity:** low-to-moderate, decayed.
- **Verdict: DEFER.** Build a *prototype and backtest only* in a later phase, with
  borrow-fee modeling mandatory. Not in the top-three pack.

### 5. Order-flow AI → microstructure / order-book prediction

- **Marketed as:** an AI that reads "smart money" order flow.
- **What it actually is:** order-flow imbalance genuinely predicts returns — at
  the **sub-second horizon**, requiring L2/L3 book data, colocation, and an HFT
  stack. Retail "order-flow" feeds are noisy and mostly marketing. This is not
  reproducible on a research-to-paper platform.
- **Grounding:** Cont, Kukanov & Stoikov on order-flow imbalance. The effect is
  real and the infrastructure requirement is the whole point — it does not
  survive translation to a retail, non-colocated setting.
- **Required data:** full-depth tick/book data (expensive, licensed), a
  low-latency execution path.
- **Failure modes:** infrastructure cost; latency arms race; adverse selection;
  PFOF/regulatory scrutiny; non-reproducibility.
- **Infra risk: HIGH.**
- **Verdict: REJECT for this platform.** Out of mission. Record the rejection and
  its rationale in the Strategy Canon so the decision is auditable; do not scaffold it.

### 6. Unusual-options AI → options-flow / IV-vs-RV

- **Marketed as:** an AI that spots "unusual options activity" and follows it.
- **What it actually is:** "unusual options activity" as a retail signal is mostly
  noise. There *are* real effects — the variance risk premium, IV-minus-RV spread,
  and informed options trading — but extracting them needs clean options data
  (OPRA), an IV surface, and greeks, and it is easy to fool yourself backtesting.
- **Grounding:** Pan & Poteshman on informed options trading; the variance
  risk-premium literature.
- **Required data:** options chains (OPRA), IV surfaces, greeks — licensed and
  operationally heavy.
- **Failure modes:** data cost/complexity; dealer-flow reflexivity; hard to
  backtest cleanly; high self-deception risk.
- **Verdict: DEFER to Phase 2 analytics, read-only.** Surface IV-vs-RV and flow
  *analytics* in the UI; do not generate trade signals from them in the first pass.

---

## Part 2 — Validation methodology (the part that keeps the platform honest)

The original scope lists good metrics. Metrics are necessary but not sufficient.
The dominant risk in a project that screens six ideas across many feature sets and
several models is **data snooping** — the near-certainty that *something* looks
great by chance. Every item below is a hard requirement, not a "nice to have."
These map directly to the eval gates in the build prompt.

### 2.1 Point-in-time data & survivorship discipline

- Universe reconstruction must be **point-in-time**: include names that were
  listed *at the time*, including those later delisted.
- Returns must be **delisting-aware** (incorporate the delisting return, not
  silently drop the name).
- Fundamentals must be **as-reported** and lagged from the **filing/availability
  date**, never the fiscal period-end. Using restated data is lookahead.
- Price adjustments must not use future corporate actions to build a
  "current-adjusted" series that a past date could not have known.

### 2.2 Purged + embargoed walk-forward cross-validation

- Splits are **date-based** and strictly forward-walking.
- Where labels overlap in time (any multi-day forward return), **purge** training
  observations whose label window overlaps the test window, then apply an
  **embargo** gap after the test window before training resumes.
- Reference: López de Prado, *Advances in Financial Machine Learning* — purged
  k-fold and embargo. This is required for any strategy with overlapping labels
  (all of A/B/C qualify).

### 2.3 Multiple-testing correction — Deflated Sharpe Ratio

- The platform will try many configurations. A raw Sharpe and its naive p-value
  are meaningless under many trials.
- Log a first-class **trial count** — the number of *distinct* strategy/feature/model
  configurations evaluated against the data — and compute the **Deflated Sharpe
  Ratio** (Bailey & López de Prado), which adjusts the observed Sharpe for the
  number of trials, the sample length, and the return distribution's skew and
  kurtosis.
- **Gate:** a strategy whose Deflated Sharpe does not clear the configured
  threshold is flagged and **cannot** be promoted to paper trading.

### 2.4 Probability of Backtest Overfitting (PBO)

- For each strategy family, report **PBO** via Combinatorially-Symmetric
  Cross-Validation (CSCV). PBO estimates the probability that the
  best-in-sample configuration underperforms the median out of sample.
- **Gate:** high PBO is a hard flag regardless of headline Sharpe.

### 2.5 Cost realism as a gate, not a metric

- Model, at minimum: bid-ask spread, commissions, and **slippage via a
  participation/impact model** (a square-root market-impact term keyed to ADV
  participation). For any short leg, model **borrow fees** and hard-to-borrow.
- Run a **cost stress test**: the strategy must survive at least **2× baseline
  costs** and a **spread-widening (stress) regime**. If net performance
  evaporates under stress, the strategy is rejected or flagged — this is the
  single most common reason an Instagram strategy is fake.

### 2.6 Capacity & turnover realism

- Report a **capacity proxy** tied to ADV participation and a **turnover** metric.
- Penalize high-turnover strategies whose net-of-cost edge is fragile; a strategy
  that only works at unrealistic size or turnover is flagged.

### 2.7 Regime robustness

- Break performance down across, at minimum: **low-vol vs high-vol** (a VIX-style
  regime split) and a **rising- vs falling-rate** split.
- Hold out at least one **designated crisis window** (e.g. 2008, 2020, 2022) as a
  stress period and report performance there separately. A strategy that only
  works in one regime is labeled as such.

### 2.8 Leakage red-flags checklist (run automatically, block on any hit)

The backtester must run and log this checklist for every strategy:

1. Adjusted-close / corporate-action lookahead.
2. Fundamentals timed to period-end instead of filing date.
3. Any feature computed using data dated after the decision timestamp.
4. Target variable leaking into the feature set.
5. Universe/index reconstitution leakage (using today's index membership in the past).
6. Normalization/scaling statistics computed over the full sample instead of
   train-only.

Any hit blocks promotion and is written to the decision log.

### 2.9 Reproducibility & audit fields

Every backtest artifact and every paper signal must carry, in an immutable log:
**config hash, data-snapshot id, code version (git SHA), random seed, trial
count, and UTC timestamp.** This is what makes the "immutable decision logs,"
"model versioning," and adversarial-audit requirements real rather than
decorative, and it is what lets a later run reproduce or contest an earlier one.

---

## Part 3 — LLM role boundaries

The LLM is a text-processing component, **not** the alpha engine.

- **Allowed:** extract structured features from unstructured text (filings, news,
  transcripts) — novelty score, direction score, uncertainty score, risk-factor
  delta, event tags; summarize; classify; normalize idea text into a
  `TradingIdeaCard`.
- **Forbidden:** emitting trade instructions, position sizes, or buy/sell calls;
  being the sole determinant of a signal; consuming social-media text as a
  standalone signal without official-source corroboration.
- Every LLM-derived feature is versioned (prompt + model id) and logged so a
  signal can be traced back to the exact extraction that produced it.

---

## Part 4 — Data-source landscape (current)

Do not hard-code vendor credentials; use environment variables and mock providers
for local tests, and fail gracefully on missing credentials. The following is the
current, practical landscape by data need. Names and terms change — confirm
licensing (display, redistribution, storage, commercial use) before any real
integration.

| Data need | Current options (verify licensing) | Notes / cautions |
|-----------|-----------------------------------|------------------|
| Historical OHLCV + corporate actions | Alpha Vantage, EODHD, Twelve Data, Polygon.io (now **Massive**), Tiingo | **Do not use IEX Cloud — shut down Aug 2024, migrated to Bluesky API.** For adjusted history, confirm split/dividend handling. |
| Fundamentals (point-in-time) | Financial Modeling Prep (FMP), EODHD, Intrinio | FMP has the deepest publicly available fundamentals. Confirm *as-reported vs restated* and filing-date timing before trusting it for backtests. |
| SEC filings | **SEC EDGAR** (official, free — `data.sec.gov` JSON + full-text search) | Official, stable, no cost. Respect fair-access rate limits and the required User-Agent header. |
| Macro | **FRED** (official, free API) | Official, stable. |
| News + sentiment | Finnhub (generous free tier, news+sentiment), Alpha Vantage NEWS_SENTIMENT, EODHD | Use as *overlay* input only. Check redistribution terms if news text is shown in the UI. |
| Earnings-call transcripts | Financial Modeling Prep (full-text transcripts), Intrinio | Transcripts are unusually hard to source elsewhere; licensing matters if displayed. |
| Options / OPRA | Polygon.io/Massive, Intrinio | Only relevant for the deferred options analytics (idea 6). Expensive and heavy — defer. |
| Broker paper-trading | **Alpaca** | Paper account uses a separate API key from live and the same API spec — swap only the base URL to the paper endpoint. Free, resettable balance, real-time simulation. **Realism caveat:** Alpaca's paper fills do not check order size against available NBBO liquidity, so your own slippage/impact model (§2.5) is what enforces cost realism, not the broker sandbox. |

**Provider abstraction rule.** Access every source behind a typed adapter
interface with a mock implementation. No strategy code imports a vendor SDK
directly; it depends on the interface. This keeps vendor churn (see IEX Cloud,
Polygon→Massive) from touching research code.
