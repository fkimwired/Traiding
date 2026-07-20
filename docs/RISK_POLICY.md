# Risk and governance policy

## Scope

Fable5 is research software with simulated paper trading only. Risk controls are not a substitute for
valid research, and positive research statistics do not create authorization to simulate an order.
Phase 1 establishes the policy, paper-only configuration, and immutable audit spine. Phase 7 adds
only immutable approval and pre-order-risk assessment evidence. Phase 10 adds one deterministic
local mock-only simulation with immutable synthetic ledger evidence; it is not broker execution.
Phase 12 adds a short-lived read-only paper-environment readiness observation; it is not strategy
eligibility, pre-order risk, or order authority. Phase 14 adds only an offline assessment of whether
immutable Phase 13 evidence satisfies a frozen prerequisite policy for a later separately authorized
research-ingestion phase. Phase 15 adds only a portable Family A admission-requirements specification
and current-gap ledger; it is not data admission, research eligibility, risk clearance, or execution
authority. Phase 16 adds only a portable Family A point-in-time source plan; it selects no source,
verifies no right, and creates no data, research, risk, or execution authority. Phase 22 adds only
an additive metadata inventory entry for later review of a macro-vintage candidate; it neither
selects that candidate nor changes any risk, research, or execution state.

## Execution boundary

- The only valid execution-mode value is `paper`.
- There is no `live` enum member, broker production URL, arbitrary broker base URL, live credential,
  or live-order method.
- External adapters are read-only and phase-isolated: Phase 12's fixed six-method paper inspection
  boundary and Phase 13's fixed point-in-time qualification candidate. Neither has an
  order-submission, replacement, cancellation, liquidation, fill, position-mutation, strategy, or
  research-snapshot method. Phase 10's ledger is a local synthetic calculation only.
- “Disabled live trading” is insufficient because it implies a dormant path; the path must be absent.
- The UI and API describe paper activity as simulated and never as fills representative of live
  execution quality.

## Promotion states

```text
RESEARCH_DRAFT
  -> EVALUATION_BLOCKED | EVALUATION_FAILED | PASS_RESEARCH
PASS_RESEARCH
  -> APPROVED_PAPER | FAIL_REJECT (separate immutable Phase 7 assessment)
```

No automatic transition enters `APPROVED_PAPER`. Every approval records approver, timestamp, strategy
and policy hashes, data snapshot, code version, permitted universe/notional/window, expiry/review date,
and rationale. Any config/model/policy/material-data change requires new evidence. Revocation is an
append-only event; it does not mutate a historical assessment and blocks reuse of that authorization.
`APPROVED_PAPER` is synthetic governance evidence, not order authorization or execution readiness.

## Approval and pre-order-risk assessment (Phase 7)

Without creating any order or executable intent, the risk service must prove:

- the exact immutable Phase 6 artifact is `PASS_RESEARCH` and all authorization evidence is current;
- global, strategy, and data-quality control evidence is clear;
- the source research artifact and complete evaluation/audit chain match the approved hashes;
- the server-owned synthetic risk context passes notional, gross, net, sector, concentration, liquidity,
  turnover, and volatility constraints;
- daily loss and strategy drawdown stops are clear;
- data freshness, market calendar, and duplicate/idempotency checks pass;
- every decision and rejection is appended to the audit log.

If a policy limit is missing or cannot be computed, persist `FAIL_REJECT`. Limits are explicit,
versioned, synthetic inputs; this document does not invent universal percentages. No order object is
created by either outcome.

## Deterministic local simulation (Phase 10)

A Phase 10 request identifies only an immutable Phase 7 assessment and an idempotency key. The
server reruns the exact Phase 7 approval, currentness, revocation, and risk checks at the simulation
decision time and persists a separate hash-bound Phase 10 revalidation proof, then runs seven ordered
Phase 10 boundary checks. All must pass before the sole synthetic long-only mock ledger may exist. A
resolved stale, expired, revoked, uncomputable, mismatched, or otherwise ineligible source persists
`BLOCKED` with no ledger.

The configuration, synthetic observation, signal rule, notional, quantity, price, cost/slippage,
outcome, and audit identity are server-owned and hash-bound. Component costs, fill-price slippage,
cash, position, requested/filled/unfilled quantity, and the exact approved proposed notional must
reconcile. The workflow performs no network request and has no external routing or live path.

## External-paper shadow readiness (Phase 12)

Phase 12 may inspect only fixed paper account, clock, `AAPL` asset, positions, open-order inventory,
and IEX latest-quote surfaces. The result is sanitized historical connectivity/readiness evidence.
It never consumes or promotes a Phase 7, 10, or 11 artifact and never computes an order.

Every readiness artifact states `order_submission_authorized=false` and
`strategy_execution_eligible=false`. A deterministic mock may prove the local contract but can never
produce `SHADOW_READY`. External readiness expires after 60 seconds and still does not authorize a
later action. Nonempty positions/orders, a closed clock, blocked account, inactive instrument, stale
or invalid quote, transport/schema defect, or uncomputable check blocks readiness. Broker paper
observations cannot override local cost/slippage, leakage, governance, or risk gates.

## Point-in-time data qualification (Phase 13)

Phase 13 assesses only whether a bounded sample can evidence six frozen Family A data capabilities.
It never creates a research snapshot, computes a signal or return, promotes a strategy, or consumes
Phase 7/10/11/12 evidence as authority. A deterministic mock may prove the contract but can never
claim external qualification.

Every qualification artifact fixes `research_data_eligible=false`,
`strategy_promotion_authorized=false`, `strategy_execution_eligible=false`,
`execution_authorized=false`, and `order_submission_authorized=false`. Missing rights, historical
membership, delisting-return semantics, revisions, action timing, reconciliation, or schema
determinism blocks the qualification; a hash or superficially complete response cannot override a
failed/uncomputable check. Even an independently authorized `EXTERNAL_SAMPLE_QUALIFIED` result would
remain a historical sample assessment and could not supply current risk or execution authority.

## Research-ingestion eligibility (Phase 14)

Phase 14 performs no provider request and persists no provider observation. It revalidates one
immutable Phase 13 qualification artifact, projects only its sanitized capability evidence, and
records a frozen twelve-check prerequisite assessment.

The only outcomes are `MOCK_PROOF_COMPLETE` and `BLOCKED`. There is no positive research-eligibility
state because the repository has no authoritative non-synthetic dataset, policy, evaluation, current
human authority, or risk evidence capable of supporting one. A Phase 13 mock proves only the local
contract; external sample metadata remains blocked because it is not a research dataset and its
rights assertion is not an independently authenticated ingestion authority.

Every Phase 14 artifact fixes research ingestion, snapshot creation, research execution,
`PASS_RESEARCH`, promotion, paper approval, execution, and order submission to false. Phase 14 may
not change any Phase 4-7 or Phase 13 row and cannot create a research snapshot, evaluation, approval,
simulation, intent, order, fill, or reconciliation record.

## Family A research-admission specification (Phase 15)

Phase 15 is a portable engineering-policy freeze, not a risk decision or data-admission decision. It
records the exact Family A requirements and current gaps without loading a credential, contacting a
provider, persisting an observation, creating a snapshot, opening a holdout, or running research. Its
only outcomes are `REQUIREMENTS_FROZEN` and `BLOCKED`.

Every Phase 15 artifact fixes external requests, licensed-payload persistence, ingestion authority,
snapshot creation, research-data eligibility, research creation/authorization/execution, performance
calculation, `PASS_RESEARCH`, promotion, paper approval, risk clearance, execution, and order
submission to false. It also fixes the live path as absent and makes no advice or real-performance
claim. A `PASS` requirement status means only that one policy requirement is stated completely; it
does not mean its external prerequisite has been supplied. The separate gap state remains
authoritative about `MOCK_ONLY`, `MISSING`, `STALE`, or `UNPROVEN` evidence.

The `PRE_ORDER_RISK` gap is intentionally `MOCK_ONLY`: pre-order limits are not a prerequisite for a
requirements-only Phase 15 artifact and cannot be made real before valid non-synthetic research,
separate promotion governance, and a later explicitly authorized risk phase. Phase 15 must not import
or mutate Phase 7, 10, 11, or 12 evidence to manufacture current clearance.

## Family A point-in-time source plan (Phase 16)

Phase 16 is a portable plan freeze, not a provider, data, evaluation, governance, or risk decision.
Its candidate rows are unselected and rights-unverified, its seven future steps remain
`NOT_STARTED`, and all nineteen Phase 15 gap states remain unchanged. `PLAN_FROZEN` states only that
the source-plan contract is complete.

Every Phase 16 artifact fixes source/provider/product selection, credentials, external verification
and requests, rights verification/grant, capture, licensed persistence, ingestion, snapshot creation,
data eligibility, non-synthetic evaluation-policy approval, holdout definition/opening, research,
performance, promotion, paper approval, risk clearance, execution, and order submission to false.
It cannot consume Phase 7, 10, 11, or 12 evidence as clearance, and the `PRE_ORDER_RISK` gap remains
`MOCK_ONLY`.

## Family A candidate-product inventory (Phase 17)

Phase 17 is portable metadata, not a provider, rights, data, research, governance, or risk decision.
Its Step 1 `OUTPUT_FROZEN` state means only that exact product/reference identities and
`candidate_product_inventory_sha256` reproduce. Selection for independent rights review is not
operational source/provider/product selection and cannot create current authorization or a risk
input.

The artifact remains `BLOCKED` because delivery, entitlement, rights/currentness, complete coverage,
schema fitness, and downstream prerequisites are unproven. Every source/provider/product authority,
credential, external request, capture, licensed persistence, ingestion, snapshot, evaluation-policy
approval, holdout, research, performance, `PASS_RESEARCH`, promotion, paper approval, risk
clearance, execution, and order field remains false. Phase 17 cannot consume Phase 7, 10, 11, or 12
evidence as clearance, and `PRE_ORDER_RISK` remains `MOCK_ONLY`.

## Family A current-use-rights review (Phase 18)

Phase 18 is a fixed-time technical public-terms review, not a provider, source, legal, data,
governance, or risk decision. The exact aggregate is `BLOCKED_NO_OPERATIONAL_SELECTION`; Step 1 and
Step 2 are `OUTPUT_FROZEN`, while Steps 3-7 remain `NOT_STARTED`. The SEC public-rights row cannot
be interpreted as operational selection or a risk input. FRED remains incompatible with planned
non-display software/system/model use and persistence under current public terms, and the Tiingo,
Morningstar/CRSP, and LSEG blockers remain fail-closed.

Every operational selection, account/credential, entitlement/license verification, currentness,
provider/account/data request, capture, persistence, ingestion, snapshot, evaluation-policy,
holdout, research, performance, `PASS_RESEARCH`, promotion, paper approval, risk clearance,
execution, and order field remains false. Phase 18 cannot consume Phase 7, 10, 11, or 12 evidence as
clearance; `PRE_ORDER_RISK` remains `MOCK_ONLY`, and no risk limit is computed or mutated.

## Family A Step 3 prerequisite assessment (Phase 19)

Phase 19 is a portable missing-evidence assessment, not an evaluation, data, governance, or risk
decision. Its exact conclusion is `BLOCKED_MISSING_EVALUATION_POLICY_AND_HOLDOUT`. It records that
`non_synthetic_evaluation_policy_sha256` and `confirmation_holdout_definition_sha256` do not exist
and deliberately produces neither value.

No Phase 5/6 synthetic threshold, cost calibration, regime, holdout date, risk limit, `PASS_RESEARCH`
result, Phase 7 approval, Phase 10 local-simulation artifact, or Phase 12 readiness observation may
be reinterpreted as non-synthetic policy, holdout, or current clearance. All nineteen Phase 15 gap
states remain unchanged, including `PRE_ORDER_RISK=MOCK_ONLY`; Steps 1/2 remain `OUTPUT_FROZEN` and
Steps 3-7 remain `NOT_STARTED`.

Every operational selection, credential, external request, data, ingestion, snapshot, complete-policy
presence/approval, holdout definition/opening/label access, research, performance, promotion, paper
approval, risk clearance, execution, and order field remains false. Phase 19 computes and mutates no
risk limit and grants no authority to begin qualification.

## Family A evaluation/holdout input register (Phase 20)

Phase 20 is a portable input-name and future-rule freeze, not a policy, holdout, governance, data, or
risk decision. Its exact conclusion is
`BLOCKED_MISSING_OPERATIONAL_AND_DATA_SPECIFIC_INPUTS`. The `COMPUTABLE_DATA_SPECIFIC_RISK_LIMITS`
row remains `MOCK_ONLY`; it names the future position, gross, net, sector, turnover, volatility,
loss, drawdown, and approval fields but supplies no limit or approval value.

`INPUTS_FROZEN` does not upgrade `PRE_ORDER_RISK=MOCK_ONLY`, satisfy a Phase 7 gate, create a current
authorization, or make a strategy executable. No Phase 5/6 fixture limit, Phase 7 approval, Phase 10
simulation result, Phase 12 readiness evidence, input-register hash, or operator assertion may be
substituted for a complete independently approved non-synthetic policy or current risk evidence.

All ten evidence-state transition rules are future-only and `applied=false`. In particular, a mock,
missing, unproven, or stale risk input cannot become present without the applicable complete,
approved, independently verified, current evidence, and later evidence becoming stale fails closed.
Both reserved Step 3 hashes remain missing; Steps 3-7 remain `NOT_STARTED`; all nineteen Phase 15 gap
states remain unchanged.

Every operational selection, credential, external request, actual input value, transition application,
data, ingestion, snapshot, complete-policy presence/approval, holdout definition/opening/consumption,
research, performance, promotion, paper approval, risk clearance, execution, and order field remains
false. Phase 20 computes and mutates no risk value and grants no authority to begin qualification.

## Family A operational-composition decision requirements (Phase 21)

Phase 21 freezes decision requirements, not a source decision, data decision, governance approval,
or risk decision. Its exact conclusion is
`BLOCKED_AWAITING_EXPLICIT_OPERATIONAL_SOURCE_PRODUCT_COMPOSITION`. Every candidate remains
unselected, every Phase 16 capability remains `UNASSIGNED`, and every Phase 20 composition field
remains absent.

The zero selected and zero current-rights-verified product bindings mean only that no operational
composition decision or current-rights evidence exists in the accepted repository. Phase 21 makes no
eligibility conclusion. It is not a vendor recommendation, permanent rejection, current external
fact, or legal opinion. Public-use metadata, including the SEC finding, cannot satisfy current
fitness, schema, coverage, currentness, or selection requirements.

`DECISION_REQUIREMENTS_FROZEN` cannot upgrade `PRE_ORDER_RISK=MOCK_ONLY`, satisfy a Phase 7 gate,
produce current authorization, or make a strategy executable. A phase authorization, artifact hash,
commit, PR, tag, release, publication, or isolated deployment identity is forbidden as operational
selection evidence. Even a future valid composition decision would grant neither current rights nor
provider, credential, data, policy, holdout, research, risk, execution, or order authority.

All eight Phase 21 rules remain future-only and unapplied. Both Step 3 hashes remain missing, Steps
3-7 remain `NOT_STARTED`, and all nineteen Phase 15 gaps remain unchanged. Phase 21 computes or
mutates no risk value and creates no execution or order path.

## Family A macro-vintage candidate inventory amendment (Phase 22)

Phase 22 names the Federal Reserve Bank of Philadelphia Real-Time Data Set for Macroeconomists as
one additional candidate for the `macro_regime_inputs` capability. The entry is candidate-only,
unranked, operationally unselected, and not current-rights-verified. Its public research-use and
vintage-history documentation cannot establish persistent-storage, model-use, derived-output,
exact-release-time, schema, coverage, availability, or fitness requirements.

`CANDIDATE_INVENTORY_AMENDMENT_FROZEN` proves only deterministic amendment integrity. Accepted
Phase 17 inventory, Phase 18 findings—including the FRED finding—and Phase 21 composition
requirements remain unchanged. All eight composition values remain absent; rights and fitness
review and an independent human composition decision remain future prerequisites. Phase 22
computes or mutates no risk value and creates no credential, provider transport, data, research,
execution, order, or live path.

## Kill switch

Global, strategy, and data-quality control states are independently supplied, immutable evidence.
Any active or uncomputable state fails the assessment. Phase 7 has no control-clearance API, pending
intent, queue, cancellation, or broker simulator.

## Audit requirements

Every signal, evaluation, approval assessment, revocation, and risk decision includes the immutable
fields in `docs/EVALS.md`. The Phase 1
`research_audit_events` table rejects updates/deletes; later migrations may add linked domain tables but
must not weaken immutability. Secrets and licensed payload text are referenced, not copied into logs.

## Review triggers

Re-evaluation and approval review are required after material model/config change, source/provider or
schema change, point-in-time correction, cost calibration change, new regime failure, DSR/PBO or trial
registry change, risk limit breach, stale data, or later explicitly authorized simulator behavior.
