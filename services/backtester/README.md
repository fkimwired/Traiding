# Backtester service boundary

Phase 5 owns a generic evaluation engine implementing `docs/EVALS.md`: immutable policies,
chronological folds, complete trial accounting, selection-aware statistics, synthetic cost stress,
fail-closed gates, and reproducible reports. It consumes only authorized immutable Phase 4 snapshots
and deterministic synthetic research ledgers.

This package does not implement an A/B/C strategy, generate a signal or model decision, construct a
position, place an order, approve paper trading, or expose any live capability. Missing policy,
point-in-time evidence, costs, risk limits, selection diagnostics, or audit identity blocks a run.
