# Phase 25 handoff

## Outcome

Phase 25 implements the deterministic RTDSM rights-response evidence-intake and open-source adapter-pattern feasibility package. The committed no-response artifact is truthfully `BLOCKED / RIGHTS_RESPONSE_EVIDENCE_MISSING`.

No provider was selected. No RTDSM or Yahoo observation was requested, downloaded, stored, normalized, or tested. No credential loader, database migration, API route, production adapter, scheduled fetcher, snapshot, research run, strategy, risk change, paper order, execution authority, or live surface was added.

## Lineage

- Phase 24 merge: `145f67f188befae46443d061d029c243858841b4`
- Phase 24 merge/implementation tree: `27392b6eb3239e01e533d07d42d164124fb7aa18`
- Accepted Phase 24 implementation: `c1dad09f08b18a5a7d527579ca677633b49184fb`
- Preserved Phase 24 artifact file SHA-256: `5ad6b7b8e5c60fa1b2e76445b11ef0428d68515dd97439e6b21fc487aea91417`

Canonical Phase 25 identity:

- Artifact ID: `6f825560-680f-5d53-ac40-3327121e46e0`
- Embedded artifact SHA-256: `5bc60a4067b3b802ea9ab3063c42d71143dabc3d303d0cff40c05d813b698a9c`
- Canonical file SHA-256: `56939ffdb1c30453518279d20782de2c8e8625cdd30e04c0de0dce8016aab7ee`
- Policy/config SHA-256: `bd15924027b572c4220d54ec6c8659b60d7978d6376145a53fecfe6e53242ff9`
- Source snapshot ID/SHA-256: `c0569f73-2b4d-543e-ba33-170f42a2fea7` / `53c96736222ff7c6af061872716d68c2306d49c7cab288b8077bce59f020b456`
- Evidence snapshot ID/SHA-256: `7ad4a698-ab77-5076-9f82-2e0b6c7c2ff5` / `35cf46ac4005edd461281ba1434fd4dbfbd2ebfef758be7eed8024049b7c454b`

The Phase 25 static verifier proves the merge is an ancestor, both accepted Phase 24 commits resolve to the frozen tree, and the Phase 24 artifact remains byte-for-byte identical to the merge.

## Deliverables

- Strict frozen Pydantic authority, response, question, exact-scope, source, pattern, rule, and aggregate models.
- Canonical artifact: `docs/PHASE_25_FAMILY_A_RTDSM_RIGHTS_RESPONSE_AND_ADAPTER_PATTERNS.json`.
- Stdout-only bounded generator and offline verifier.
- Ten-entry immutable source-evidence registry covering four repositories and six official documents.
- Eleven-entry provider-neutral adapter-pattern inventory, with no adapter implementation.
- Field-by-field evaluation of all ten Phase 24 questions and nineteen exact-scope requirements.
- Explicit `PASS`, `FAIL`, `CONDITIONAL`, and `MISSING` semantics with independently verified evidence IDs.
- Fail-closed conditional controls and transition rules.
- Focused service, portable, security, and static tests.

Every artifact carries config/policy SHA-256, evidence and source snapshot IDs/SHA-256, the accepted generation git SHA, random seed `0`, trial count `0`, and fixed UTC timestamps. Randomness is not used.

## Intake procedure

Only sanitized metadata may be passed with `--response-metadata`; never save or pass a provider response body or credential. Each authority row must include authenticated provenance and independent verification. Each question and scope answer must cite a verified immutable evidence ID. Account/entitlement scope is only `SANITIZED_HASH_ONLY` plus its SHA-256. Unknown or sensitive fields fail with a fixed error that echoes no inputs.

The response can pass only if all ten questions, all nineteen scope elements, all authority records, and the independently evidenced mutual-consistency gate satisfy. `CONDITIONAL` satisfies only with an enforceable control and a passed acceptance test. Even a pass remains evidence-only and requires separately authorized acquisition work.

## Research evidence boundary

The explicit network research step ended before generation and testing. Repository revisions, official-document content hashes, license metadata, and normalized findings were persisted; repository clones and official source bodies were not committed. Yahoo remains `RIGHTS_UNVERIFIED`; yfinance is absent from dependencies and runtime.

## Verification contract

Run from the repository root:

```powershell
.venv\Scripts\python.exe -m pytest services/data/tests/test_phase25_contracts.py services/data/tests/test_phase25_package.py services/data/tests/test_phase25_security.py tests/test_phase25_portable.py tests/test_phase25_static.py
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m ruff format --check .
.venv\Scripts\python.exe -m mypy
.venv\Scripts\python.exe scripts/verify_phase1.py --static-only --phase 25
```

The canonical generator and verifier are:

```powershell
.venv\Scripts\python.exe scripts/generate_family_a_rtdsm_rights_response_and_adapter_patterns.py --confirm-evidence-intake-and-patterns-only
.venv\Scripts\python.exe scripts/verify_family_a_rtdsm_rights_response_and_adapter_patterns.py --artifact docs/PHASE_25_FAMILY_A_RTDSM_RIGHTS_RESPONSE_AND_ADAPTER_PATTERNS.json
```

## Stop condition

Stop after Phase 25. Do not begin Phase 26 or acquire provider observations without separate authorization and a passing rights response followed by a separately authorized acquisition phase.
