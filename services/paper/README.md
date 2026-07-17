# Local paper simulation

Phase 10 owns one synchronous deterministic simulation over server-owned synthetic fixtures. The
package has no network, provider, broker, credential, account, or live-trading dependency. A public
request contains only immutable approval evidence and an idempotency key; every simulated market,
signal, quantity, price, cost, and lifecycle value is resolved by the server.

The workflow freshly re-runs Phase 7 governance before producing an append-only local ledger. A
failed revalidation is persisted as a `BLOCKED` artifact with no ledger row.
