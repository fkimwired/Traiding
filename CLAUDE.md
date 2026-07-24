1. **No live trading. Paper trading only.** No code path may place a real-money
   order. Paper and live are separated by an enforced flag; the live path is
   absent, not merely disabled.
2. **The LLM is not the alpha engine.** LLMs are used only for extraction,
   summarization, classification, and feature generation from unstructured text.
   An LLM may **never** output a trade instruction, position size, or buy/sell call.
3. **No strategy proceeds without all of:** explicit signal definition, target
   forecast horizon, required data, transaction-cost model, slippage model,
   walk-forward test report (purged + embargoed), risk limits, and audit-log
   output. If any is missing, **stop and create it before writing execution code.**
4. **Cost realism is a gate.** Any strategy whose net performance disappears under
   the stress-cost assumptions (§ Phase 5) is rejected or flagged — never promoted.
5. **Survivorship and lookahead are defects, not caveats.** Point-in-time universe,
   delisting-aware returns, filing-date-lagged fundamentals, train-only
   normalization. The leakage checklist (§ Phase 5) runs automatically and blocks
   on any hit.
6. **Social-media sentiment is never a standalone signal.** It is flagged
   manipulation-prone and requires official-source corroboration to contribute.
7. **Every signal, backtest, and paper trade is auditable** and carries: config
   hash, data-snapshot id, git SHA, random seed, trial count, UTC timestamp.
8. **Never imply personalized investment advice.** The UI labels paper trading as
   simulated and shows no advice, guarantees, or hype.
9. **Do not fabricate performance.** Use mock data until real provider credentials
   are configured; never invent real results.

# Build conventions

- Phase boundaries are hard. Implement only the phase named by the active task.
- FastAPI/Pydantic owns the API schema. Regenerate TypeScript contracts; never maintain
  parallel handwritten response types.
- Database changes use reversible Alembic revisions. Never call `create_all()` at runtime.
- Configuration is environment-driven and validated at startup. The only permitted
  execution mode is `paper`; no live endpoint, enum value, dependency, or code path exists.
- Keep provider access behind typed adapters once Phase 4 begins. Strategy code must never
  import a vendor SDK directly.
- Every delegated unit includes an executable acceptance test and preserves source evidence.
- Use UTC for stored timestamps and make availability timestamps explicit for point-in-time data.
- Run `python scripts/verify_phase1.py --static-only` before handing off Phase 1 changes.

# External observation and free-source rules

- An **external live-data paper test** is a read-only observation of a paper-only external
  environment (for example, the accepted Phase 12 six-GET Alpaca paper boundary) combined with
  clearly labeled simulated behavior. It is never live trading. No live endpoint, live credential,
  live enum/flag/configuration branch, order submission, replacement, cancellation, liquidation, or
  position-closing path may exist, even dormant, and "live testing" language never authorizes one.
- Read-only external observation and execution are different capabilities. Observation evidence
  (readiness checks, connectivity, freshness) never becomes execution, promotion, or order
  authority, and an expired or historical observation never revalidates itself.
- A free source may be selected for a use only after a current first-party terms review covering
  the exact intended use: storage, internal/non-display, derived data, retention, attribution,
  redistribution, and revocation/currentness. Free access, an API key, an open-source client
  library, or successful retrieval is never evidence of data rights.
- Demonstration or connectivity data is never research-qualified data. A quote or telemetry value
  used to prove readiness must not be persisted as, or later relabeled into, a research snapshot,
  backtest input, or strategy signal.
- Secrets load only through the explicitly authorized local commands from the documented
  environment variables, are represented as secret types, and never appear in stdout, logs,
  persisted rows, artifacts, generated contracts, fixtures, builds, or commits. Raw provider
  payloads (bodies, headers, account/order/position details, raw prices) are validated transiently
  and reduced to sanitized statuses, counts, and hashes; they are never persisted or committed.
- Every delegated implementation task must name: the one governing phase or accepted earlier-phase
  maintenance boundary, executable acceptance commands, at least one literal negative/adversarial
  assertion, the required evidence artifact with config hash, snapshot/evidence id, git SHA, seed
  and trial count where applicable, and UTC timestamp, and an explicit stop condition.

