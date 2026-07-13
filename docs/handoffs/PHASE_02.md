# Phase 2 handoff — TradingIdeaCard extraction

## Objective

Implement Phase 2 only: lossless source intake, typed `TradingIdeaCard` extraction, persistence, and a
traceable Markdown memo for each of the six canonical archetype fixtures. Stop before deterministic
Phase 3 mapping, provider adapters, backtesting, signals, risk enforcement, or any broker/order code.

## Governing sources

Read `AGENTS.md`, `CLAUDE.md`, `docs/PRODUCT_BRIEF.md`, `docs/STRATEGY_CANON.md`,
`docs/EVALS.md`, and the byte-identical `docs/RESEARCH_SUPPLEMENT.md` first. The hard gates bind the
task. Preserve every Phase 1 contract and test.

## Inputs and provenance

Accept one or more of:

- Instagram/source URL as provenance only (network retrieval is a separate explicit capability);
- pasted caption/transcript;
- manual notes;
- screenshot/video transcript text already supplied by the user.

Never claim to quote a post unless the exact text was supplied or lawfully retrieved and persisted.
Store the immutable raw input, content hash, source type, supplied/retrieved timestamp, and parent link
before extraction. A correction creates a new version; it does not overwrite the original.

## Typed output

Create one canonical Python/Pydantic schema and generate/update the OpenAPI TypeScript contract:

```text
source_id
source_url
source_version
raw_text
quoted_claims[]
paraphrased_claim
asset_class
forecast_horizon
signal_family
execution_style
required_data[]
action_rule
risk_assumptions[]
ambiguity_flags[]
testability_score
infra_risk
research_priority_score
official_corroboration_source_ids[]
extraction_model_id
extraction_prompt_version
created_at_utc
```

Optional/unknown values are represented explicitly; do not invent them. If an action rule or forecast
horizon cannot be supported by source text, mark the card non-testable. Sub-minute/order-book/scalping
claims receive high infrastructure risk. Social-only claims receive a manipulation flag and cannot
contribute without an official corroboration id. The LLM extracts fields only and never produces an
instruction, position size, or buy/sell call.

## Persistence and services

- Add a new reversible Alembic revision; never edit `0001_phase1`.
- Preserve immutable source versions separately from extraction versions/cards.
- Add Phase 2 endpoints for create/read/list only; no strategy mapping or signal endpoint.
- Put background extraction on the existing `research` queue with idempotent job keys.
- Use a deterministic rule-based/mock extractor in tests. Any real LLM provider is optional, behind a
  typed adapter, credential-gated, and never required for local or CI tests.
- Generate a Markdown research memo per card as a secondary audit artifact.

## Fixtures

Create six **clearly labeled synthetic archetype fixtures**—ranking, trend/pattern, social/news,
pairs, order-flow, unusual-options. They test extraction behavior and do not pretend to be the missing
Instagram posts. Include ambiguity, missing action-rule, HFT, and uncorroborated-social adversarial
fixtures.

## Acceptance tests

All must pass from a clean checkout:

```powershell
$env:FABLE5_VERIFY_PHASE = "2"
.\scripts\check.ps1
.\scripts\test.ps1
python scripts/verify_phase1.py --static-only --phase 2
docker compose up --build --wait
```

Add tests proving:

1. each accepted input is stored before extraction and traces by id/hash to every output;
2. all required schema fields and documented null/unknown states serialize through API/OpenAPI/TS;
3. missing action rule or horizon produces `non_testable` and no invented rule;
4. HFT/order-book/scalping text produces `infra_risk=high`;
5. social-only text produces manipulation/corroboration flags and cannot produce a contributing
   signal field;
6. prompt/model/schema versions are persisted for every LLM-derived extraction;
7. retries are idempotent and source correction creates a new version rather than mutation;
8. migrations upgrade, downgrade, and re-upgrade against PostgreSQL;
9. local/CI tests use mocks and no credential; missing optional credentials fail clearly;
10. no deterministic Phase 3 verdict mapper, backtester, strategy, paper broker, order, or live path
    exists.

## Stop condition

Stop after Phase 2 tests and summary. Report files changed, exact commands/results, limitations, and a
ready-to-paste Phase 3 task. Do not implement Phase 3.
