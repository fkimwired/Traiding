# Phase 3 deterministic mapping decisions

## Scope and authority

This document freezes the Phase 3 mapping contract implemented from `AGENTS.md`,
`docs/STRATEGY_CANON.md`, `docs/handoffs/PHASE_03.md`, and immutable Phase 2 records. It defines a
research classification and deterministic rationale only. It does not define a strategy, signal,
feature, dataset, model, backtest, performance result, risk approval, position, paper order, broker,
or live capability.

`BUILD_RESEARCH` authorizes only a later research specification. It never means profitable,
approved, recommended, advised, or paper-eligible.

## Frozen rule-set identity

- Rule-set version: `phase3-canon-mapping-v1`
- Canonical SHA-256: `352afeee889857834f7453f2d37bbb6b40e414ac4da9befccce476cc2061674a`
- Rationale-template version: `phase3-mapping-rationale-v1`

The hash is computed once from canonical JSON containing the rule-set and template versions, the
exact normalized mapper-source SHA-256 identity, immutable typed family mappings, the ordered
predicate/outcome table, and Phase 2 reason ordering. Static verification recomputes the mapper
source digest, so executable predicate drift cannot retain the old rule-set hash. A changed table,
outcome, evaluator source, or version produces a different hash and therefore a new immutable
mapping version.

## Closed machine vocabularies

Canonical families serialize exactly as:

| Canon | Machine value |
|---|---|
| A | `A_CROSS_SECTIONAL_EQUITY_RANKING` |
| B | `B_TIME_SERIES_MOMENTUM_REGIME` |
| C | `C_OFFICIAL_EVENT_TEXT_OVERLAY` |
| D | `D_PAIRS_STATISTICAL_ARBITRAGE` |
| E | `E_ORDER_BOOK_MICROSTRUCTURE` |
| F | `F_OPTIONS_FLOW_IV_RV_ANALYTICS` |

The verdict vocabulary is exactly `BUILD_RESEARCH`, `DEFER`, `DEFER_READ_ONLY`,
`REJECT_PLATFORM`, and `NON_TESTABLE`.

An ambiguous or missing Phase 2 family does not select A–F. Its `canonical_family` is explicitly
`null`, its verdict is `NON_TESTABLE`, and its reason is `AMBIGUOUS_CANONICAL_FAMILY` or
`MISSING_CANONICAL_FAMILY`. Nullable family is therefore an unresolved evidence state, not a seventh
canonical family.

Phase 2 structural blockers retain their exact lowercase values and deterministic order:

1. `missing_raw_text`
2. `missing_action_rule`
3. `ambiguous_action_rule`
4. `missing_forecast_horizon`
5. `ambiguous_forecast_horizon`

Phase 3 adds only the family-resolution and canon reasons required by the handoff:
`MISSING_CANONICAL_FAMILY`, `AMBIGUOUS_CANONICAL_FAMILY`,
`PLATFORM_INFRASTRUCTURE_MISMATCH`, `OFFICIAL_CORROBORATION_REQUIRED`,
`BORROW_AND_BREAK_REQUIREMENTS`, `READ_ONLY_ANALYTICS_ONLY`, `CANON_A_RULE_MATCHED`,
`CANON_B_RULE_MATCHED`, and `CANON_C_RULE_MATCHED`.

## Rule IDs and precedence

The mapper evaluates these deterministic rules in order:

| Order | Rule ID | Outcome |
|---:|---|---|
| 1 | `P3-001-NON-TESTABLE-PRECEDENCE` | Preserve a supported family when possible, but return `NON_TESTABLE`; leave missing/ambiguous family null. |
| 2 | `P3-002-PLATFORM-MISMATCH` + `P3-CANON-E` | Normalized order-flow/HFT/sub-minute/full-depth/high-infrastructure evidence maps to E + `REJECT_PLATFORM`. |
| 3 | `P3-003-SOCIAL-CORROBORATION` + `P3-CANON-C` | Contribution-blocked C maps to `DEFER`. |
| 4 | `P3-004-PAIRS-REQUIREMENTS` + `P3-CANON-D` | D maps to `DEFER`. |
| 5 | `P3-005-OPTIONS-READ-ONLY` + `P3-CANON-F` | Structurally testable F maps to `DEFER_READ_ONLY`. |
| 6 | `P3-CANON-A`, `P3-CANON-B`, or `P3-CANON-C` | A, B, or contribution-eligible C maps to `BUILD_RESEARCH`. |

The mapper never scans `raw_text`, mutable request text, a URL, or rationale prose. Its only
classification inputs are persisted structured Phase 2 fields and identities. It performs no I/O
and has no model, provider, broker, or execution dependency.

## Resolved handoff ambiguities

The Phase 3 handoff says both that non-testable precedence wins and that options map to
`DEFER_READ_ONLY`. The persisted `trend.json` and `unusual_options.json` fixtures are explicitly
non-testable: trend lacks a horizon and options lacks an action rule. Precedence is authoritative, so
their existing-fixture outcomes are B/`NON_TESTABLE` and F/`NON_TESTABLE`. Separate structurally
testable B and F cases prove B/`BUILD_RESEARCH` and F/`DEFER_READ_ONLY`.

Phase 2 has no missing/ambiguous signal-family reason code because family resolution was reserved for
Phase 3. The two Phase 3 family-resolution codes above close that gap without altering the immutable
Phase 2 vocabulary or fabricating a family.

## Synthetic acceptance matrix

| Phase 2 fixture | Canonical family | Verdict | Ordered reason codes |
|---|---|---|---|
| `ranking.json` | A | `BUILD_RESEARCH` | `CANON_A_RULE_MATCHED` |
| `trend.json` | B | `NON_TESTABLE` | `missing_forecast_horizon` |
| `social_news.json` | C | `DEFER` | `OFFICIAL_CORROBORATION_REQUIRED` |
| `pairs.json` | D | `DEFER` | `BORROW_AND_BREAK_REQUIREMENTS` |
| `order_flow.json` | E | `REJECT_PLATFORM` | `PLATFORM_INFRASTRUCTURE_MISMATCH` |
| `unusual_options.json` | F | `NON_TESTABLE` | `missing_action_rule` |

Additional acceptance cases cover testable B/F, verified official C, ambiguous family combined with
HFT evidence, and non-testable E. Structural/family ambiguity always wins before the platform rule;
social testability remains independent of corroboration.

## Immutable input and output identity

Each mapping records the immutable card ID/hash; extraction request ID/fingerprint; source and source
version IDs/number/content hash; exact official corroboration version IDs; extractor kind, ID,
version, model/prompt identities when applicable, schema version, and configuration hash; mapping
input hash; rule-set version/hash; matched rule IDs; ordered reason codes; source-evidence claim IDs;
family; verdict; rationale-template version; and database-owned UTC creation time.

`(card_id, mapper_rule_set_sha256)` is idempotent. The database serializes mapping-version allocation
per immutable card. A changed rule set appends the next version. Two-connection tests prove that
identical concurrent hashes produce one row and different concurrent hashes produce gap-free
versions. A `BEFORE INSERT` trigger validates every copied card/request/source/profile identity, and
deferred constraint triggers require the mapping's official-corroboration set to equal the card's
set exactly at commit. Card corroboration closes when its Phase 2 memo is finalized, and mapping
corroboration closes when its rationale is finalized, so a coordinated append cannot rewrite both
sides of historical lineage. Create retries and read/list paths also rebuild fresh Phase 2 lineage
and fail closed on any mismatch. Mapping, corroboration, and rationale tables reject update, delete,
and truncate.

## API and rationale boundary

The only Phase 3 routes are:

- `POST /v1/cards/{card_id}/mappings` with no request body;
- `GET /v1/mappings/{mapping_id}`;
- `GET /v1/mappings` with optional card filter and bounded limit.

Clients cannot submit a family, verdict, reason, rule set, or rationale. The rationale is a fixed
template rendered from the persisted deterministic result and displays source/card/extraction/rule
lineage. The frontend renders it as plain preformatted text and exposes no form, button, order, or
paper action.

## Data and security limitations

Acceptance data is clearly labeled synthetic. Phase 3 makes no network call and authenticates no
URL. It introduces no credential, provider SDK, LLM runtime, commercial source, or real performance.
Official-source status remains limited by the evidence and verification method persisted in Phase 2.
No mapping outcome bypasses later point-in-time data, evaluation, cost, leakage, risk, approval, and
paper-only gates.
