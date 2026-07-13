# Phase 3 local Qwen review record

## Review boundary

- Model: locally installed Ollama `qwen3:14b-q4_K_M`.
- Role: untrusted secondary reviewer only.
- Supplied scope: Phase 3 deterministic mapping requirements, frozen decisions, domain models/rules,
  pure mapper, rationale renderer, repository, `0003` migration, and create/read/list routes.
- Allowed topics: precedence, lineage, idempotency, append-only persistence, rollback, client-override
  paths, phase boundaries, and missing executable tests.
- Excluded topics: strategies, signals, recommendations, position sizes, performance, providers,
  brokers, paper orders, and live execution.
- Authority: repository requirements, deterministic code, and executable tests always override model
  output.

## Review result

The bounded review produced no actionable Phase 3 finding. Despite an explicit review instruction and
the supplied governing handoff, Qwen treated the input as an unspecified user question and asked for
clarification. It offered generic topics such as understanding the code, debugging, extending
functionality, and best practices, but did not identify a concrete defect with file/function evidence.
No code or contract change was made from that response.

## Rejected or inapplicable suggestions

- Qwen suggested that the user might want to add updating behavior. That conflicts with the explicit
  immutable create/read/list-only contract and was rejected; Phase 3 tables and routes intentionally
  expose no update or delete path.
- It suggested possible integration with other systems without tying the suggestion to a verified
  requirement. Provider, strategy, backtest, broker, paper-order, and live integrations are outside
  Phase 3 and remain absent.
- It summarized that unique constraints and triggers appeared to provide immutability, but supplied
  no catalog, concurrency, or rollback evidence. Executable PostgreSQL checks—not the model summary—
  are the acceptance authority.

## Independent review findings

Repository and parallel human-style code audits found and resolved issues that Qwen did not report:

- the handoff's non-testable precedence conflicts with an unqualified options acceptance sentence;
  the implementation preserves precedence and adds a separate testable F case;
- Phase 2 has no missing/ambiguous family reason code, so Phase 3 adds explicit resolution codes and
  leaves the canonical family null rather than inventing A–F;
- an initial descriptive, shallowly mutable rule document did not cryptographically identify the
  executable predicates; it was replaced by frozen typed family/rule/outcome tables plus a verified
  normalized mapper-source digest, all covered by the final canonical rule-set hash;
- the Phase 3 corroboration junction now has database-level official-source validation in addition to
  repository checks, and deferred constraints enforce exact equality with the parent card's
  corroboration set; immediate finalization guards reject later one-sided or coordinated appends;
- the Phase 3 loader recomputes the immutable Phase 2 card hash and cross-checks JSON payload,
  normalized columns, extraction identity, source identity, schema/config, and exact corroboration
  rows before mapping or returning a read/list result; the database independently validates all
  copied scalar lineage on insert;
- mapping-version allocation locks the immutable parent card, identical card/rule-set requests are
  idempotent, and a changed rule-set hash appends a version; two simultaneous-connection tests cover
  identical and different hashes;
- rationale is rendered as safe deterministic text, and the API accepts no client family, verdict,
  rule set, reason, or rationale body.

These controls are preserved by unit, API, generated-contract, live PostgreSQL lineage/race/trigger,
and migration-cycle tests. Qwen is not part of the mapper or any runtime path.
