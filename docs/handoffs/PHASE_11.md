# Phase 11 portable local-simulation evidence handoff

## Authorized baseline and boundary

Phase 11 starts only from accepted Phase 10 commit
`3acd25f5bb4bcbeec684f672c3b816562d2366dc`, tree
`88929434b0e13ea2a7c3e4baf9c00d08c69fb276`. Its governing design is
`docs/PHASE_11_PORTABLE_SIMULATION_EVIDENCE_DECISIONS.md`.

This phase packages an existing immutable Phase 10 artifact into a deterministic portable bundle
and verifies that bundle locally. It adds no migration, simulation execution, replay, mutation,
strategy expansion, provider, external data, account, credential, broker, order routing, signing,
publication, deployment, asynchronous work, or live path. Phase 10 remains the only simulation
authority; Phase 11 is read-only.

## Owned contract

`LocalSimulationEvidenceBundle` has exactly five required fields:

```text
bundle_schema_version
bundle_sha256
simulation_run_id
simulation_artifact_sha256
simulation
```

The version literal is `phase11-local-simulation-evidence-bundle-v1`, has no default, and domains
the canonical digest of the other four fields. The nested value is the complete generated
`PaperSimulationArtifact`. Completed artifacts retain exactly one reconciled synthetic ledger;
blocked artifacts retain none. Hashes establish deterministic integrity, not a signature,
authenticity, current authority, replay permission, or execution authority.

FastAPI owns exactly one new operation:

```text
GET /v1/local-simulations/{simulation_run_id}/evidence-bundle
```

It has no request body or query parameter and returns only existing Phase 10 evidence. The frontend
uses the generated client to prepare it once and explicitly download deterministic local JSON from
the held object without a second request. Neither operation writes to the database or starts work.

The offline verifier requires a bundle path and a separately supplied expected digest:

```text
python scripts/verify_local_simulation_evidence.py --bundle PATH --expected-bundle-sha256 LOWERHEX64
```

It is database-free and network-disabled. It fails closed on malformed JSON, duplicate or unknown
fields, schema or semantic drift, completed/blocked inconsistency, tampering, or an independent
digest mismatch. Numeric coefficient and exponent bounds apply before model hashing to prevent
hostile canonical-decimal amplification. Success emits deterministic sanitized JSON. Invalid input and invalid invocation
exit 2 with no stdout and exact generic stderr
`Local simulation evidence verification failed.`; help exits 0.

## Closure gate

Run from a clean committed Phase 11 tree with the phase selected in the same shell:

```powershell
$env:FABLE5_VERIFY_PHASE = "11"
.\scripts\check.ps1
.\scripts\test.ps1
npm run build
.\.venv\Scripts\python.exe scripts\verify_phase1.py --static-only --phase 11
.\.venv\Scripts\python.exe scripts\verify_phase1.py --phase 11
```

The full verifier must prove both completed and blocked bundles through API and offline CLI; generated
contract parity; independent expected-digest comparison; adversarial nested, ledger, identifier,
schema-version, duplicate-key, and digest tamper rejection; active socket denial; zero database
writes; unchanged Alembic head `0008_phase10`; inherited browser regressions; and complete cleanup.
The repository, index, SHA, and tree must remain clean and identical from preflight through cleanup.

Ubuntu `phase11-compose` must pass at the same closure SHA/tree as Windows. The CI job has a
180-minute timeout, pre-pulls exactly one digest-qualified Playwright runtime, never updates
snapshots, and invokes the direct `--phase 11` verifier. If the commit has not been pushed, Ubuntu
acceptance remains pending and Phase 11 must not be called formally accepted.

## Stop condition

Stop after Phase 11. Do not push, open a pull request, tag, sign, publish, release, deploy, add a
migration, or begin Phase 12 unless separately authorized. Preserve the absent live path and the
local mock-only paper boundary.
