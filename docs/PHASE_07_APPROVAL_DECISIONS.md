# Phase 7 Approval and Risk Decisions

## Boundary

Phase 7 adds a fail-closed governance assessment for synthetic simulated-paper research. It does
not add a broker, submission, fill, position, executable paper intent, paper-execution path, or any
live capability. A positive assessment is historical synthetic QA evidence only: it grants no
execution authority, is not execution readiness, is not investment advice, and makes no real-
performance claim.

The Phase 5 promotion vocabulary remains unchanged. `APPROVED_PAPER` is a separate Phase 7
assessment outcome and is never written back into an immutable Phase 5 or Phase 6 artifact.

## Source authority and eligibility

The only eligibility authority is an exact persisted Phase 6 artifact loaded by `research_run_id`.
The workflow validates its complete immutable payload and derives the prerequisite from its actual
Phase 5 `promotion_state`. Configuration ids are retained only as lineage. Their spelling, including
the token `-pass-`, never determines eligibility.

The accepted deterministic Phase 6 corpus therefore has one research-eligible prerequisite:
`phase6-a-pass-v2`. `phase6-a-fail-cost-v2`, both Family B artifacts, and
`phase6-c-pass-v2` remain `FAIL_REJECT`. The corroboration-negative Family C request has no persisted
run to reference. Supplying the A artifact alone is structurally incomplete and cannot create an
assessment.

## Independent evidence

An assessment request contains only immutable references to:

- the exact Phase 6 run;
- one versioned approval policy;
- one versioned approval scope;
- one human-controlled synthetic authorization-evidence artifact; and
- one server-owned synthetic risk-input artifact.

Those evidence rows exist independently of an assessment. The server owns every threshold, hash,
timestamp, expiry/review value, revocation state, risk input, calculation, check result, outcome, and
copied Phase 6 metric. The deterministic human identities are QA fixtures because no production
identity provider or reviewer-authentication system is configured.

Revocation is an append-only event against the authorization evidence. It never mutates the
historical positive assessment, but it invalidates reuse of that authorization. Assessment creation
and revocation serialize on the same authorization identity so a positive decision cannot race a
revocation.

## Complete lineage

Every assessment copies and hash-binds the Phase 6 run id and artifact hash; request, pipeline,
configuration, mapping, specification, feature-lineage, and snapshot hashes; the exact ordered
snapshot bindings; Phase 5 policy, fixture, report, promotion state, all twelve ordered gate codes,
trial-set hash and trial counts; source Phase 6 git SHA and random seed; and the Phase 7 decision-
engine git SHA. Missing or inconsistent lineage blocks the assessment.

## Fail-closed rules

Every fully resolved assessment persists the exact ordered check registry. It covers research
eligibility, lineage completeness, policy/scope/authorization matching and currentness, authorization
review and revocation, risk-input freshness, global/strategy/data-quality controls, market-calendar
state, duplicate-context evidence, and synthetic notional, gross, net, sector, concentration,
liquidity, turnover, volatility, daily-loss, and drawdown limits.

Each check is `PASS`, `FAIL`, `UNCOMPUTABLE`, or `BLOCKED`. `APPROVED_PAPER` is possible only when
every required check is `PASS`; every other complete assessment is `FAIL_REJECT` with explicit reason
codes. The synthetic thresholds demonstrate policy mechanics only and are not recommended or
production limits.

## Persistence and API

Migration 0007 directly revises `0006_phase6` and adds seven append-only tables for policies, scopes,
human authorization evidence, revocations, risk inputs, assessments, and checks. Every table rejects
`UPDATE`, `DELETE`, and `TRUNCATE`; foreign keys use `RESTRICT`; deferred completeness validation
prevents partial assessments.

The public surface is create/read/list only:

- `POST /v1/approval-assessments`
- `GET /v1/approval-assessments`
- `GET /v1/approval-assessments/{assessment_id}`
- `POST /v1/approval-revocations`
- `GET /v1/approval-revocations`
- `GET /v1/approval-revocations/{revocation_id}`

FastAPI/Pydantic OpenAPI remains the only TypeScript contract authority. No update, delete, action,
broker, or execution endpoint exists.

## Known limitations

- All approval, reviewer, policy, scope, switch, calendar, exposure, and risk evidence is
  deterministic synthetic QA data.
- No production authentication, reviewer identity provider, real risk telemetry, provider
  credentials, or current-market input is configured.
- Revocation uses one frozen server-owned synthetic evidence profile; no production revocation
  authentication or per-reviewer capability service is configured.
- The deterministic corpus has one synthetic policy version per policy id and one scope version per
  scope id; a production policy/scope supersession registry is not configured.
- The default API captures fresh UTC once for each assessment or revocation. A positive artifact
  still records only its request-time outcome; consumers must not interpret the immutable historical
  row as current authorization or execution readiness.
- No paper adapter or execution workflow exists.
