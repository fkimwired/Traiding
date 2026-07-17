# Local paper simulation

Phase 10 owns one synchronous deterministic simulation over server-owned synthetic fixtures. The
package has no network, provider, broker, credential, account, or live-trading dependency. A public
request contains only immutable approval evidence and an idempotency key; every simulated market,
signal, quantity, price, cost, and lifecycle value is resolved by the server.

The workflow freshly re-runs Phase 7 governance before producing an append-only local ledger. A
failed revalidation is persisted as a `BLOCKED` artifact with no ledger row.

Phase 11 adds only a deterministic read projection of an already persisted Phase 10 artifact. The
five-field `LocalSimulationEvidenceBundle` is content-hashed, performs no clock, UUID, network,
filesystem, or database write, and remains available only through a JSON GET route. It does not
refresh governance, create an export record, or add an execution capability.

Phase 12 adds a separate read-only paper-environment shadow-readiness package. Its vendor-neutral
protocol exposes exactly six inspection methods, with one deterministic mock and one fixed Alpaca
paper/data implementation. The external adapter has no generic request or order mutation method and
uses only paper-specific credentials loaded by the explicit local capture command.

Readiness artifacts persist sanitized status, timing, counts, and hashes in two append-only tables.
They always state that order submission and strategy execution are unauthorized. A mock can only
produce `MOCK_PROOF_COMPLETE`; external `SHADOW_READY` expires after 60 seconds and remains historical
evidence. The package adds no order intent, side, quantity, price, scheduler, retry, strategy import,
vendor SDK, or live path.
