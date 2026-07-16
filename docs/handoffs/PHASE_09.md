# Phase 9 release-acceptance handoff

## Authorized baseline and boundary

Phase 9 starts from accepted Phase 8 commit
`94bcfaabf9de457aec47e49e332865a8dcc74f30`, tree
`56d2cf38ba0ff3d5427fbf5f20aefa13d5224581`. This handoff records the Phase 9 verification boundary;
it does not authorize Phase 10, publication, deployment, real providers, credentials, identity work,
additional research, simulated execution, live trading, broker integration, order submission, or
paper execution.

The only Phase 9 outcome is reproducible release-acceptance evidence. Production application,
frontend, API, contract, migration, fixture, snapshot, and Phase 1-8 artifact bytes remain unchanged.
The sole test-only exception is an exact baseline-derived timeout expression in
`services/frontend/e2e/phase8.accessibility.spec.ts`; any other byte drift in that file fails static
verification. The Alembic head is still `0007_phase7`, and no migration 0008 exists. `PASS_RESEARCH`
is not approval and `APPROVED_PAPER` is not execution readiness.

## Local closure gate

From a clean committed Phase 9 tree, run exactly:

```powershell
$env:FABLE5_VERIFY_PHASE = "9"
.\scripts\check.ps1
.\scripts\test.ps1
npm run build
.\.venv\Scripts\python.exe scripts\verify_phase1.py --static-only --phase 9
```

Create a unique absolute evidence directory beneath `$env:TEMP`, outside the repository, and launch
the full verifier once:

```powershell
.\.venv\Scripts\python.exe scripts\run_phase_gate.py run --phase 9 --evidence-dir <ABSOLUTE_TEMP_DIR> --timeout-seconds 6300
```

If observation is needed, poll only the same directory:

```powershell
.\.venv\Scripts\python.exe scripts\run_phase_gate.py follow --evidence-dir <ABSOLUTE_TEMP_DIR>
```

After the runner returns, verify the same evidence bundle:

```powershell
.\.venv\Scripts\python.exe scripts\run_phase_gate.py verify-evidence --evidence-dir <ABSOLUTE_TEMP_DIR>
```

Do not retry a delayed or failed run. Stop on a dirty pre/post state, nonzero exit, missing Phase 8 or
Phase 9 marker, snapshot mismatch, manifest/log mutation, missing artifact, cleanup residue, or any
write outside the Phase 9 allowlist.

## Cross-platform acceptance

The Windows run proves only Windows behavior and exactly the 24 win32 baselines. The Ubuntu
`phase9-compose` job must run at the identical final SHA and tree and prove exactly the 24 Linux
baselines. Both manifests must bind that same identity. CI publishes only
`phase-gate.manifest.json` and `phase-gate.sanitized.log`; the raw local log, heartbeat, secrets,
environment values, and source payloads are not artifacts.

The Ubuntu unit job may hydrate only the exact frozen Linux Rolldown binary after `npm ci` and must
prove that package manifests and the lockfile remain unchanged. The Phase 9 full verifier alone uses
wider Phase 6 transport deadlines and emits required nested Phase 6 and Phase 8 stage records. It
owns the browser timeout flag, scrubs arbitrary caller values, and selects 25 minutes only for the
exhaustive-lineage test; inherited Phase 8 remains at 20 minutes. Assertions, coverage, test order,
concurrency, retries, workers, and application behavior remain unchanged. The outer runner deadline
is 6,300 seconds and the Ubuntu Compose job deadline is 120 minutes.

Until that Ubuntu job and its evidence verifier pass at the same final identity, Phase 9 is not accepted.
If repository publication authority is absent, stop after local implementation and report
the remaining CI requirement. Do not push, open a pull request, merge, tag, publish, or deploy.

## Required closure report

Report the exact changed files; commands and exit results; structured stage durations; Windows
evidence directory plus manifest and sanitized-log hashes; final SHA/tree and clean status; any
bottleneck; and the outstanding Ubuntu requirement. Stop after Phase 9. No later-phase prompt is
authorized by this handoff.
