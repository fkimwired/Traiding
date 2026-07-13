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

