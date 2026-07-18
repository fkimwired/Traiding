# Phase 14 research-ingestion eligibility handoff

## Objective and exclusions

Implement one deterministic, synchronous, database-only assessment of an immutable Phase 13
qualification artifact. The result may be only `MOCK_PROOF_COMPLETE` or `BLOCKED`.

Do not add an external call, provider adapter, credential, licensed payload, research ingestion,
snapshot, strategy run, performance result, promotion, approval, risk mutation, broker/order/fill,
live path, frontend product control, deployment, publication, or later phase.

## Accepted input identity

Start only from the formally accepted Phase 13 identity:

- Commit: `47e8e6a9c878a3a8ca7a4b22be3e23ab0357716f`
- Tree: `d4ac6b6f4b6ba28f5359d8ea85c35845bdb9f285`
- Windows Phase 13 full verifier: passed.
- Ubuntu run `29623170681`: `preflight`, `unit`, and `phase13-compose` passed at that identity.

Authority sources:

- `AGENTS.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/EVALS.md`
- `docs/RISK_POLICY.md`
- `docs/DATA_SOURCES.md`
- `docs/COMPLIANCE_NOTES.md`
- `docs/PHASE_06_RESEARCH_DECISIONS.md`
- `docs/PHASE_07_APPROVAL_DECISIONS.md`
- `docs/PHASE_13_POINT_IN_TIME_DATA_QUALIFICATION_DECISIONS.md`
- `docs/PHASE_14_RESEARCH_INGESTION_ELIGIBILITY_DECISIONS.md`

## Exact write allowlist

Write only:

```text
.github/workflows/ci.yml
Makefile
README.md
docs/COMPLIANCE_NOTES.md
docs/DATA_SOURCES.md
docs/IMPLEMENTATION_PLAN.md
docs/PHASE_14_RESEARCH_INGESTION_ELIGIBILITY_DECISIONS.md
docs/RISK_POLICY.md
docs/handoffs/PHASE_14.md
packages/contracts/openapi.json
packages/contracts/src/api.generated.ts
packages/contracts/src/phase14-contract.type-test.ts
packages/contracts/src/runtime.generated.ts
scripts/assess_research_ingestion_eligibility.py
scripts/check.ps1
scripts/check.sh
scripts/verify_phase1.py
services/api/migrations/versions/0011_phase14_research_ingestion_eligibility.py
services/api/src/fable5_api/main.py
services/api/src/fable5_api/research_ingestion_eligibility.py
services/api/tests/test_phase14_openapi_contract.py
services/api/tests/test_phase14_routes.py
services/data/src/fable5_data/phase14/__init__.py
services/data/src/fable5_data/phase14/canonical.py
services/data/src/fable5_data/phase14/contracts.py
services/data/src/fable5_data/phase14/repository.py
services/data/src/fable5_data/phase14/workflow.py
services/data/tests/test_phase14_contracts.py
services/data/tests/test_phase14_postgres.py
services/data/tests/test_phase14_security.py
services/data/tests/test_phase14_workflow.py
services/frontend/e2e/phase8.accessibility.spec.ts
services/frontend/e2e/phase8.visual.spec.ts
tests/test_phase10_static.py
tests/test_phase11_static.py
tests/test_phase12_static.py
tests/test_phase13_static.py
tests/test_phase14_migration.py
tests/test_phase14_static.py
tests/test_phase5_postgres.py
tests/test_phase9_static.py
tests/test_repository_policy.py
```

Stop before any write outside this list. Do not modify Compose, dependencies, environment examples,
earlier migrations, accepted Phase 4-7/12/13 implementation, paper service, frontend product code,
visual baselines, or `scripts/run_phase_gate.py`.

## Contracts and invariants

Use exactly:

```text
outcomes: MOCK_PROOF_COMPLETE, BLOCKED
statuses: PASS, BLOCKED, UNCOMPUTABLE
```

Exact ordered checks:

```text
QUALIFICATION_IDENTITY_INTEGRITY
QUALIFICATION_SOURCE_KIND_ALLOWED
QUALIFICATION_OUTCOME_ELIGIBLE_OR_MOCK
CAPABILITY_MANIFEST_COMPLETE_PASSING
QUALIFICATION_CHECKS_COMPLETE_PASSING
EXTERNAL_REQUEST_EVIDENCE_COMPLETE_OR_MOCK
INDEPENDENT_RIGHTS_REFERENCE_PRESENT_OR_MOCK
USE_RIGHTS_CURRENT_OR_MOCK
USE_RIGHTS_SCOPE_SUFFICIENT_OR_MOCK
LICENSED_PAYLOAD_ABSENT
RESEARCH_SNAPSHOT_ABSENT
PROMOTION_EXECUTION_AUTHORITY_ABSENT
```

Project exactly six ordered sanitized Phase 13 capability payloads. Bind the complete Phase 13
qualification ID/hash/capture/source/outcome/rights/capability/check lineage and the frozen Phase 14
policy. Do not persist provider observations.

A complete deterministic mock may produce only `MOCK_PROOF_COMPLETE`. Every non-mock source and any
missing, failed, uncomputable, stale, insufficient, or unverified prerequisite produces `BLOCKED`.
There is no positive research-eligibility vocabulary.

Every artifact carries all false authority/data/action fields and true live-absence/no-advice/
no-performance fields from the decisions document.

## Implementation units

1. Strict canonical hashing and frozen contracts.
2. Database-only workflow with Phase 13 full-source revalidation.
3. Three-table append-only repository and reversible migration `0011_phase14`.
4. Explicit local assessment CLI with only idempotency key, qualification UUID, and confirmation.
5. One GET-only FastAPI route and generated OpenAPI/TypeScript contracts.
6. Static/full verifier, wrappers, inherited browser gates, and Ubuntu CI.

## Persistence and rollback

Own only:

```text
research_ingestion_eligibility_assessments
research_ingestion_eligibility_payloads
research_ingestion_eligibility_checks
```

Require exact six/twelve deferred completeness, composite Phase 13 ID/hash lineage, canonical
scalar/payload parity, database-owned timestamps, deterministic identities, advisory-lock
single-flight idempotency, and direct-SQL mutation rejection. Prove the nonempty
`0010 -> 0011 -> 0010 -> 0011` cycle with all inherited rows and SQL function bodies unchanged.

## CLI and API

Creator:

```text
python scripts/assess_research_ingestion_eligibility.py \
  --idempotency-key KEY \
  --qualification-id UUID \
  --confirm-research-eligibility-only
```

Retrieval:

```text
GET /v1/research-ingestion-eligibility/{assessment_id}
```

The API is historical read-only evidence. It performs zero writes and zero external calls and owns
typed 200/404/409/422 responses. Mutation methods return 405.

## Acceptance

Require:

- Parser/wrappers accept Phases 1-14 and reject 0/15 with exit 2.
- Exact Phase 14 allowlist and accepted Phase 13 baseline ancestry.
- Generated FastAPI/OpenAPI/TypeScript/runtime contract parity.
- Complete Phase 13 mock -> `MOCK_PROOF_COMPLETE` and blocked mock -> `BLOCKED`.
- Proof that mock or external sample metadata cannot create positive research eligibility.
- Missing/corrupt/cross-lineage source evidence leaves zero Phase 14 rows.
- Same-key replay is byte-identical; conflicting key/fingerprint reuse fails closed.
- Concurrent same-key creation invokes one assessment and creates one complete graph.
- Root/child/source/policy/hash/ordinal/status/reason/rights/scalar tamper rejection.
- Missing, duplicate, reordered, or cross-assessment children fail at commit.
- Update/delete/truncate rejection on all three tables.
- No writes to Phase 1-13 tables; no research snapshot, evaluation, approval, paper, or order row.
- Active socket denial and static absence of transport/provider/credential/worker/retry imports.
- Secret/licensed-data canaries absent from errors, logs, rows, API, generated contracts, build, and
  browser evidence.
- GET 200/404/409/422, 405 mutations, repeated byte-equivalence, zero writes, and zero network.
- Inherited Phase 8/10/11 browser/accessibility/visual regressions.
- Clean Windows and Ubuntu gates at one committed SHA/tree.
- Complete Phase 14 container/network/volume/process/browser/temp cleanup without deleting the
  user's pre-existing development stack.

Closure commands:

```powershell
$env:FABLE5_VERIFY_PHASE = "14"
.\scripts\check.ps1
.\scripts\test.ps1
npm run build
.\.venv\Scripts\python.exe scripts\verify_phase1.py --static-only --phase 14
.\.venv\Scripts\python.exe scripts\verify_phase1.py --phase 14
git status --porcelain=v1
```

After the Windows committed-tree gate passes, push only the exact Phase 14 SHA authorized by this
task and require Ubuntu `preflight`, `unit`, and `phase14-compose` at that same SHA/tree.

## Stop condition

Stop after Phase 14 same-SHA Windows and Ubuntu acceptance. Do not perform an external capture,
ingest provider observations, create a research snapshot, run or promote a strategy, modify approval
or risk state, add broker/order/fill/reconciliation behavior, add a live path, publish, deploy, or
begin a later phase.
