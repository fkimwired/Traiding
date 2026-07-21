# Implementation plan and handoff protocol

## Architecture decision

Use a monorepo with a thin control plane first. FastAPI owns schemas, OpenAPI generates shared
TypeScript contracts, PostgreSQL owns durable state, Redis/RQ owns background research work, and
Next.js owns the user interface. Provider and model code arrive only in the phase that defines their
contracts and acceptance tests.

## Dependency sequence

```text
Phase 1 control plane
  -> Phase 2 source extraction and persistence
  -> Phase 3 deterministic strategy canon mapping
  -> Phase 4 point-in-time provider interfaces and mocks
  -> Phase 5 evaluation engine and fail-closed gates
  -> Phase 6 A/B/C research strategies on mock/approved data
  -> Phase 7 fail-closed approval and pre-order risk assessment
  -> Phase 8 complete product workflows and visual QA
  -> Phase 9 single-flight release-acceptance evidence
  -> Phase 10 deterministic local mock-only paper simulation
  -> Phase 11 portable deterministic local simulation evidence verification
  -> Phase 12 external-paper shadow readiness (read-only)
  -> Phase 13 point-in-time data qualification (read-only, qualification-only)
  -> Phase 14 research-ingestion eligibility (offline, assessment-only)
  -> Phase 15 Family A research-admission specification (portable, policy-only)
  -> Phase 16 Family A point-in-time source plan (portable, plan-only)
  -> Phase 17 Family A candidate-product inventory (portable, metadata-only)
  -> Phase 18 Family A current-use-rights review (portable, public-metadata-only)
  -> Phase 19 Family A Step 3 prerequisite assessment (portable, assessment-only)
  -> Phase 20 Family A evaluation/holdout input register (portable, input-names-only)
  -> Phase 21 Family A operational-composition decision requirements (portable, requirements-only)
  -> Phase 22 Family A macro-vintage candidate inventory amendment (portable, metadata-only)
  -> Phase 23 Family A RTDSM current-use-rights review (portable, public-terms-only)
```

No phase may bypass an earlier contract. Deferred/rejected ideas remain visible research decisions but
do not receive executable scaffolds.

## Phase ownership and definitions of done

| Phase | Owned deliverables | Machine gate |
|---|---|---|
| 1 | Compose, API liveness/readiness, migrations, idle queue, shared contract, navigation, docs, CI | root check/test commands + isolated Compose verifier |
| 2 | Lossless input/source records, typed extraction card, six archetype fixtures, persistence, memos | unit/contract/migration tests; every output traces to immutable source input |
| 3 | deterministic family/verdict mapper and rationale UI | table-driven mapping tests cover build/defer/reject/non-testable outcomes |
| 4 | typed adapters, snapshots, PIT semantics, deterministic mocks, graceful credentials | provider conformance suite and mock end-to-end data run |
| 5 | nested walk-forward, trial registry, DSR, PBO, leakage, costs/stress, reports | all 12 checks in `docs/EVALS.md` section 14 |
| 6 | research-only A/B/C pipelines and explainable outputs | mock runs pass/failed reports; no paper approval or live path |
| 7 | versioned policy, human authorization, revocation, immutable approval and pre-order risk decisions | fail-closed eligibility, currentness, revocation, lineage, and risk-rule tests; no adapter or execution path |
| 8 | full four-mode workflows and traceability | source-to-audit route in ≤2 clicks; visible gate precedence; accessibility/visual tests |
| 9 | assertion-preserving release-gate orchestration and evidence | single-flight Windows/Ubuntu runner; verified sanitized manifests at one SHA/tree |
| 10 | deterministic local mock-only simulation with fresh governance and immutable ledger | direct Windows/Ubuntu verifier; reversible migration, exact completed/blocked artifacts, idempotency, append-only and browser proof |
| 11 | deterministic read-only bundle, GET-only retrieval, local JSON download, and offline verification of existing Phase 10 artifacts | generated contracts; completed/blocked and tamper proof; zero writes; network denial; inherited browser and cross-platform cleanup proof |
| 12 | fixed paper-environment read adapter, deterministic mock, sanitized append-only readiness evidence, local capture, and one historical GET | exact six-read contract; credential/secret/network denial; idempotency/tamper/migration proof; inherited browser and cross-platform cleanup proof; no order path |
| 13 | frozen Family A PIT qualification profile, deterministic mock, fixed Tiingo candidate reads, sanitized append-only manifests/checks, local capture, and one historical GET | exact six-capability/twelve-check contract; mock-cannot-qualify; rights/credential/secret/network denial; migration/tamper/zero-write/inherited-browser/cross-platform proof; no research ingestion or order path |
| 14 | offline eligibility assessment over immutable Phase 13 qualification evidence, sanitized projections/checks, explicit local assessment, and one historical GET | exact six-payload/twelve-check contract; mock-complete/blocked only; no positive eligibility state; migration/tamper/zero-write/network-denial/inherited-browser/cross-platform proof; no ingestion, research run, promotion, or order path |
| 15 | canonical Family A non-synthetic research-admission requirements and a closed current-gap ledger | deterministic generated JSON and offline verification; exact `REQUIREMENTS_FROZEN`/`BLOCKED` outcomes; no migration, API, provider, credential, payload, snapshot, research run, performance result, promotion, execution, or live path |
| 16 | canonical Family A point-in-time source plan with candidate-only facts, ordered future steps, and unchanged Phase 15 gaps | deterministic generated JSON and offline verification; exact `PLAN_FROZEN`/`BLOCKED` outcomes; no source selection, credential, network, data, migration, API, snapshot, evaluation policy, holdout, research, promotion, risk, execution, or live path |
| 17 | canonical Family A product/reference identities for Phase 16 Step 1 and independent-rights-review routing only | deterministic generated JSON and offline verification; exact Step 1 `OUTPUT_FROZEN` plus overall `BLOCKED`; no operational source/provider/product selection, credential, network, data, migration, API, rights grant, qualification, snapshot, research, risk, execution, or live path |
| 18 | canonical technical current-use-rights review of the exact Phase 17 identities and official public-source metadata for Phase 16 Step 2 only | deterministic generated JSON and offline verification; exact Steps 1/2 `OUTPUT_FROZEN`, Steps 3-7 `NOT_STARTED`, and `BLOCKED_NO_OPERATIONAL_SELECTION`; no operational provider/account/data request, credential, migration, API, capture, persistence, research, risk, execution, order, or live path |
| 19 | canonical assessment of the two required prior-evidence hashes for Phase 16 Step 3 | deterministic generated JSON and offline verification; exact `BLOCKED`, assessment `OUTPUT_FROZEN`, missing policy/holdout conclusion, unchanged gaps and Steps 1/2 frozen plus 3-7 not started; neither missing hash is produced and no policy, holdout, data, research, execution, order, or live path is added |
| 20 | canonical register of the exact Family A evaluation/holdout input names and future-only evidence-state transition rules | deterministic generated JSON and offline verification; exact `BLOCKED` / `INPUTS_FROZEN` / `BLOCKED_MISSING_OPERATIONAL_AND_DATA_SPECIFIC_INPUTS`; twenty input rows and ten unapplied rules; no input value, missing Step 3 hash, qualification output, policy, holdout, data, research, execution, order, or live path |
| 21 | canonical requirements for a later explicit Family A operational source/product composition decision | deterministic generated JSON and offline verification; exact `BLOCKED` / `DECISION_REQUIREMENTS_FROZEN` / `BLOCKED_AWAITING_EXPLICIT_OPERATIONAL_SOURCE_PRODUCT_COMPOSITION`; 6 candidate groups, 9 unselected and current-rights-unverified product-rights bindings, 7 unassigned capabilities, 8 absent decision fields, 3 blocked dependencies, 6 blocked gates, 8 unapplied rules, and 10 forbidden substitutes; no selection, provider/counsel contact, credential, data, policy, holdout, Step 3, research, execution, order, or live path |
| 22 | additive Family A macro-vintage candidate inventory amendment naming the Philadelphia Fed RTDSM for later independent review | deterministic generated JSON and offline verification; exact `BLOCKED` / `CANDIDATE_INVENTORY_AMENDMENT_FROZEN`; one candidate-only, unranked, unselected RTDSM product bound to inert official-source metadata while accepted Phase 17–21 artifacts remain unchanged; no rights grant, operational composition, credential, external data request, capture, persistence, research, execution, order, or live path |

| 23 | technical current-use-rights review of the exact Phase 22 RTDSM candidate using official public terms only | deterministic generated JSON and offline verification; exact `BLOCKED` / `PUBLIC_TERMS_RIGHTS_REVIEW_FROZEN` / `BLOCKED_PUBLIC_TERMS_INSUFFICIENT_FOR_PERSISTENT_AUTOMATED_MODEL_USE`; three inert citations, one conservative finding, and four requirement states; no legal opinion, rights grant, credential, data request, qualification, composition, research, execution, order, or live path |

## Required handoff template

Every implementer task must include:

1. **Objective and explicit exclusions.** Name the one phase and list behavior that must remain absent.
2. **Inputs/source authority.** Link the governing docs, schemas, fixtures, and prior-phase outputs.
3. **Files/directories in scope.** Identify allowed writes and preserve unrelated/user files.
4. **Contracts and invariants.** State types, timestamps, identities, state transitions, failure modes,
   and audit fields.
5. **Implementation units.** Each bounded unit names its output and owner boundary.
6. **Acceptance tests.** Give literal commands and assertions, including negative/adversarial cases.
7. **Data/security posture.** Specify mock/real source, credentials, licensing, and secret behavior.
8. **Migration/rollback.** Require reversible schema changes and backward compatibility where needed.
9. **Handoff report.** Files changed, commands/results, known limitations, and the next phase prompt.
10. **Stop condition.** Stop immediately after the named phase; do not anticipate later behavior.

The accepted Phase 10 boundary remains recorded in `docs/handoffs/PHASE_10.md`. The separately
authorized and accepted Phase 11 read-only boundary and direct cross-platform closure gate are in
`docs/handoffs/PHASE_11.md`. The separately authorized Phase 12 read-only external-paper readiness
boundary is in `docs/handoffs/PHASE_12.md`. Phase 12 is formally accepted at commit
`37530a94f841d538a162447cb01ec3e11f375ead`, tree
`d8d747ffccb76c3d754cdd2cc14b8ec49fb97287`. The Phase 13 qualification-only boundary is in
`docs/handoffs/PHASE_13.md`; Phase 13 is formally accepted at commit
`47e8e6a9c878a3a8ca7a4b22be3e23ab0357716f`, tree
`d4ac6b6f4b6ba28f5359d8ea85c35845bdb9f285`. The authorized Phase 14 offline eligibility boundary
is in `docs/handoffs/PHASE_14.md`; it authorizes neither external capture, research-data ingestion,
strategy execution, promotion, approval, risk mutation, nor an order path. Phase 14 is formally
accepted at commit `513fdfd515599e59db6911441aadf1cc30f7352c`, tree
`5870fd4c112b7c7bee05f6240c5cbd950eeaff04`. The separately authorized Phase 15 portable
requirements boundary is in `docs/handoffs/PHASE_15.md`; it freezes an engineering admission
specification and current gap evidence only, not data rights, research-data eligibility, ingestion,
research execution, performance, promotion, approval, risk clearance, or order authority. Phase 15
is formally accepted at commit `5b3052eb8f020d77cc3750b34190b4b2fa5fc16c`, tree
`7fab5a2b2eb2f8f821b969d9cb031c806e064d28`, after clean Windows acceptance and Ubuntu run
`29661065413` (`preflight`, `unit`, and `phase15-compose`) at that exact identity. The separately
authorized Phase 16 portable source-plan boundary is in `docs/handoffs/PHASE_16.md`; it names only
candidate facts and future evidence steps, leaves every Phase 15 gap unchanged, and selects no source
or product. Phase 16 is formally accepted at commit
`7c4df26733b4ad13c49c455ea5f28f627012ee44`, tree
`c69b4a60237ae3588f8544272b75becbf0a763e8`, after clean Windows acceptance and Ubuntu run
`29675183969` (`preflight`, `unit`, and `phase16-compose`) at that exact identity. The separately
authorized Phase 17 portable inventory boundary is in `docs/handoffs/PHASE_17.md`; it performs only
Phase 16 Step 1 metadata output and grants no operational selection or external/data authority.
Phase 17 is formally accepted at commit `fd89d3905e9c2ea12223e30b5822a0fdda795a26`, tree
`f2eb791785dd10cc9316d174505b65eda919fe71`, after clean Windows acceptance and Ubuntu run
`29682173053` (`preflight`, `unit`, and `phase17-compose`) at that exact identity. The separately
authorized Phase 18 boundary is in `docs/handoffs/PHASE_18.md`; it freezes a technical review of
official public terms for Phase 16 Step 2 only. It is not legal advice or operational selection and
grants no credential, provider/account/data request, capture, persistence, research, execution, or
order authority. Phase 18 is formally accepted at commit
`16aac187fc3dbd6015306603c18be6e08cea8e4e`, tree
`b36ae615f13f39d0e661f18d1cc61e009b1aacf7`, after clean Windows acceptance and Ubuntu run
`29698090468` (`preflight`, `unit`, and `phase18-compose`) at that exact identity. The separately
authorized Phase 19 boundary is in `docs/handoffs/PHASE_19.md`; it assesses only whether the two
required Phase 16 Step 3 prior-evidence hashes exist. It must report both missing, preserve all gap
and step states, and must not manufacture a non-synthetic evaluation policy, define/open a holdout,
or grant external-data, research, risk, execution, or order authority. Phase 19 is formally accepted
at commit `86ddcafacff43b42fe56346745d7e6f08eaf3a52`, tree
`6b6c2693a969e80cac9013d441ba607565d8914a`, after clean Windows acceptance and Ubuntu run
`29705348113` (`preflight`, `unit`, and `phase19-compose`) at that exact identity. The separately
authorized Phase 20 boundary is in `docs/handoffs/PHASE_20.md`; it may freeze only required input
names, current evidence classifications, and unapplied future transition rules. It must supply no
input value, create neither reserved Step 3 hash, preserve every gap and source-plan step, and grant
no provider, credential, data, research, risk, execution, order, or live authority.
Phase 20 is formally accepted at commit `01ed1ff17b91ba6961e02cdf1df3aa3e6be4859a`, tree
`b7a68998f1c99ed8b19ab08ae8a725726f04c423`, after clean Windows acceptance and Ubuntu run
`29724765420` (`preflight`, `unit`, and `phase20-compose`) at that exact identity. The separately
authorized Phase 21 boundary is in `docs/handoffs/PHASE_21.md`; it may freeze only operational-
composition decision requirements over already committed metadata. It must keep every candidate
unselected, every capability unassigned, every decision field absent, all inherited gaps/steps
unchanged, and all provider, rights, data, research, risk, execution, order, and live authority false.
Phase 21 is formally accepted at commit `a25ffb5cb68014c301a588c0e8cf7c7f18914e0a`, tree
`8744604b486dd7398cd8c5a003fe7c7b083fde86`, after clean Windows acceptance and Ubuntu run
`29759697662` (`preflight`, `unit`, and `phase21-compose`) at that exact identity. The separately
authorized Phase 22 boundary is in `docs/handoffs/PHASE_22.md`; it may add only one metadata-only
macro-vintage candidate overlay. It does not replace accepted inventories or rights findings, make
an operational selection, verify a right, load a credential, request or persist data, or advance
policy, holdout, qualification, research, risk, execution, order, or live authority.
Phase 22 is formally accepted at commit `1c07fbe8e23950e8c9f910b30473c900c0bf3e21`, tree
`1261f5a9da883e14a894b33e583068681f8cf459`, and merged as
`7f3bf3df029a894660f0e47dda1056bd32dca297` with the same tree. The authorized Phase 23 boundary is
in `docs/handoffs/PHASE_23.md`; it may freeze only a public-terms technical review of the RTDSM
candidate. It grants no right, entitlement, product selection, data access, or later-step authority.
