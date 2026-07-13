# Research validation notes

**As of:** 2026-07-13  
**Posture:** Operational clarification of `RESEARCH_SUPPLEMENT.md`; strategy verdicts are unchanged.

The supplement is directionally strong. The following refinements are normative for implementation
because they remove ambiguity or update time-sensitive provider facts.

## Methodology clarifications

1. Store every sample's information interval `[t0, t1]`. In the primary strictly past-only
   walk-forward evaluation, remove training observations whose label interval crosses the next test
   boundary (`t1 >= test_start`). A post-test embargo is relevant only to a purged K-fold/CPCV design
   that permits later observations in the training set. Do not mechanically apply both concepts where
   the time geometry does not support them.
2. Deflated Sharpe requires the complete selection history, the distribution/variance of trial Sharpe
   values, and an effective-independent-trial method. A raw trial count alone is necessary but not
   sufficient. The gate is a configured DSR probability and fails closed when uncomputable.
3. PBO via CSCV requires a synchronous return matrix for all configurations, an even block count,
   a fixed selection metric, rank/tie policy, and configured `pbo_max`. It evaluates the selection
   procedure and complements rather than replaces chronological walk-forward testing.
4. Filing date is not precise enough for point-in-time data. Persist accepted/availability time,
   ingestion time, revision identity, source/accession identity, and validity range. Enforce
   `available_at <= decision_time`.
5. Current FRED values can be revised. Historical research must use ALFRED/vintage and release
   semantics where revisions would affect the feature.
6. Square-root impact and 2× cost stress are research approximations/governance rules, not universal
   laws. Calibrate parameters and define exact pass/fail outcomes before opening the holdout.

The full implementation contract is in `docs/EVALS.md`.

## Provider corrections

- IEX Cloud ended on 2024-08-30. Blue-Sky acquired assets/technology; the current successor product is
  viaNexus. Do not imply automatic account or integration migration.
- Polygon.io's rename to Massive is current; preserve a vendor alias at the adapter boundary.
- SEC submissions/XBRL APIs at `data.sec.gov` and EDGAR full-text search are distinct interfaces.
- Alpaca paper uses a separate paper domain and paper credentials; a paper-only account may receive
  IEX rather than SIP data. Its simulator omits material execution and accounting effects, so it
  cannot validate cost realism.
- Claims such as “deepest fundamentals” or “generous free tier” are unsupported without a dated,
  entitlement-specific comparison and are not used in platform documentation.

Primary links and adapter requirements are recorded in `docs/DATA_SOURCES.md`.

