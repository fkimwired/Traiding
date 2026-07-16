# Phase 9 release-acceptance decisions

## Boundary and source authority

Phase 9 hardens release acceptance for the accepted Phase 8 repository. Its source baseline is commit
`94bcfaabf9de457aec47e49e332865a8dcc74f30`, with tree
`56d2cf38ba0ff3d5427fbf5f20aefa13d5224581`. The baseline must be present in full Git history and
must be an ancestor of the Phase 9 commit.

This phase changes acceptance orchestration, evidence, and one exact browser-test timeout expression
only. It adds no application behavior, data, migration, API, contract, dependency, provider,
credential, identity system, strategy, research family, or execution capability. Live trading,
broker integration, order submission, and paper execution remain absent. `PASS_RESEARCH` remains a
research prerequisite only. `APPROVED_PAPER` remains historical synthetic governance evidence only.
Neither is an execution authorization.

Phase 9 is not accepted on Windows evidence alone. Acceptance requires a verified Ubuntu CI bundle
from the exact same final commit SHA and tree. Publishing a branch or creating a pull request requires
separate authority.

## Immutable Phase 8 surface

The Phase 9 verifier first executes the complete Phase 1-8 static verifier. The full verifier then
executes the inherited Phase 1-8 Compose, PostgreSQL, API, browser, table-immutability, and cleanup
path in its existing order. It preserves the exact Phase 8 final marker and emits the Phase 9 final
marker only after cleanup succeeds and the project has no remaining container, network, or volume.
No Phase 9 database work exists.

The only permitted Phase 9 writes are the files named by the implementation authorization. A diff
from the exact Phase 8 baseline containing any other path fails. Every production application and
frontend file, Phase 1-8 decision, handoff, source artifact, fixture, visual baseline, and persistence
artifact outside that allowlist remains a baseline byte. The sole inherited-test exception is
`services/frontend/e2e/phase8.accessibility.spec.ts`: the verifier reconstructs its expected bytes
from the Phase 8 Git blob by replacing exactly one 20-minute exhaustive-lineage timeout expression
with the Phase 9-profile conditional. Any other byte in that file fails static verification. The
verifier also compares the contract files, migrations 0001-0007, synthetic fixture files, and all 48
visual PNGs directly with their Phase 8 Git blobs.

There is no migration 0008. The Alembic head remains `0007_phase7`; Phase 9 maps isolated PostgreSQL
acceptance to that existing revision. The browser remains serial with `workers: 1`,
`fullyParallel: false`, and `retries: 0`. Each platform must have exactly 24 expected snapshot names:
Windows checks the win32 files and Ubuntu checks the Linux files.

The frozen generated-contract hashes are:

| Path | SHA-256 |
|---|---|
| `packages/contracts/openapi.json` | `d89a72e31778ed7d6edcaaf5611e99506aecdc49c640df336e2a622023a0bb25` |
| `packages/contracts/src/api.generated.ts` | `5fa0ce5d903529705709dc2dc0f4c86d71830fc634548551d145cf3bb7a0003e` |
| `packages/contracts/src/runtime.generated.ts` | `905810491adf9f52090ff8af109137df76c76367293a21cd39a71dc643a4b964` |
| `packages/contracts/src/validate-response.ts` | `57f74259a7d8f00bd739099a01eebd25d4fa7fed01d2e12320d28d67620e3503` |

## Structured stage evidence

Only a Phase 9 verifier emits `FABLE5_PHASE9_STAGE` records. Each record is one canonical JSON object
with exactly these fields:

- `stage`: a lowercase machine name;
- `start_utc` and `end_utc`: explicit UTC timestamps;
- `elapsed_seconds`: a finite nonnegative duration; and
- `result`: `pass` or `fail`.

The required stages are inherited static checks, Phase 9 static checks, Compose startup, Phase 2
through Phase 8 acceptance, and Compose cleanup. Phase 6 additionally requires sanitized nested
records for its schema cycle, API verification, isolated PostgreSQL tests, and append-only proof.
Phase 8 additionally requires nested records for the evidence-timeline API, browser pre-snapshot,
Playwright suite, and browser post-snapshot immutability proof. These records localize an
inherited-gate failure without exposing raw verifier output. The stage stream cannot contain
environment values, credentials, source payloads, licensed data, arbitrary exception text, or
command output.

The inherited Phase 6 transport deadlines remain 240 seconds for research creation, 60 seconds for
large immutable-detail reads, and 10 seconds for validation reads in Phases 6 through 8. Only the
Phase 9 full verifier uses 480, 180, and 30 seconds respectively to tolerate constrained CI compute.
The verifier also removes any caller-provided `FABLE5_PHASE9_BROWSER_TIMEOUT_PROFILE` value and sets
it to exactly `1` only for the Phase 9 browser child. That profile changes the single exhaustive
lineage test from its inherited 20-minute deadline to 25 minutes. It changes no assertion, coverage,
request payload, test order, concurrency proof, retry policy, worker count, global Playwright
timeout, or application behavior. The outer single-flight deadline is 6,300 seconds so the bounded
browser allowance does not race the runner deadline.

## Single-flight runner

`scripts/run_phase_gate.py` is a standard-library-only runner with three commands:

```text
run --phase 9 --evidence-dir ABSOLUTE_PATH --timeout-seconds 6300
follow --evidence-dir ABSOLUTE_PATH
verify-evidence --evidence-dir ABSOLUTE_PATH
```

An evidence directory must be absolute, new or empty, outside the canonical repository, and reached
without any symlink, junction, or other reparse-point component. The runner acquires one nonblocking
operating-system file lock keyed by the canonical repository path. The lock is acquired before the
single verifier child is spawned. A competing invocation reports the active run identifier and exact
follow command without spawning a child. `follow` reads only that run's heartbeat, sanitized log, or
manifest and never launches verification.

The runner never retries or relaunches. On timeout or interruption it signals the same child, allows
the inherited verifier to execute cleanup, checks the verifier resource namespace, records failure,
and returns nonzero. A dirty pre-run or post-run worktree, pre-existing verifier resource, nonzero
child exit, missing marker, missing stage, cleanup residue, or evidence mismatch remains a failure.

## Local and portable evidence

The evidence directory contains:

- a frequently replaced atomic heartbeat;
- a raw local log, retained outside the repository and never published by CI;
- a strictly allowlisted sanitized stage log; and
- an atomically replaced manifest.

The manifest binds the Phase 8 baseline, Phase 9 commit SHA and tree, empty pre/post status, exact
child command, platform and tool versions, UTC start/end, stage durations, the current platform's
24 exact snapshot names and SHA-256 values, sanitized-log SHA-256, child exit, both final markers,
timeout/interruption flags, and cleanup result. Its own SHA-256 is computed over canonical manifest
content excluding the self-digest field. Evidence verification recomputes both digests and compares
the bundle to the current repository, platform, command, and snapshot corpus. Rewriting the manifest
cannot make a forged SHA, tree, platform, run identifier, command, or snapshot inventory valid because
the sanitized start event and current repository context must agree independently.

The sanitized log permits only runner start/end identities, exact inherited/final success markers,
and validated structured stage records. Credential-like output, arbitrary payload-bearing output,
URLs, database output, and raw verifier lines cannot enter the sanitized artifact.

## CI orchestration

CI is named `phase-9-ci`, has read-only contents permission, and checks out full history. Every GitHub
Action reference is an immutable full commit SHA with its major tag recorded as a comment. Preflight
owns lint, formatting, type checks, generated-contract drift, frontend build, Phase 9 static
verification, and Compose configuration. After preflight, the Python/frontend unit job and the full
Ubuntu Phase 9 Compose job run concurrently and remain independently required. Because the frozen
cross-platform lock contains only the Windows Rolldown binary record, the Ubuntu unit job hydrates the
exact Linux binary version after `npm ci` with scripts and persistence disabled, then proves that no
package manifest or lockfile changed before running the unchanged frontend tests.

The Compose job has a 120-minute timeout and invokes exactly one runner. It always attempts to upload
only the sanitized manifest and log for 14 days with missing files treated as an error. The runner and
evidence-verifier exit codes are retained and enforced after artifact upload, so upload cannot hide a
verification failure. Only superseded pull-request runs share a cancellable concurrency group; main
and independently identified runs are never superseded by that policy.

## Rollback and acceptance boundary

Phase 9 has no schema or data rollback because it creates neither. Reverting the Phase 9 tooling and
documentation restores the exact Phase 8 code and acceptance behavior. A timed-out or interrupted
run is acceptable evidence only of failure and cleanup; it is never promoted to a passing bundle.

Windows-local completion proves runner behavior and the 24 win32 snapshots. Phase 9 remains not
accepted until Ubuntu CI at the same SHA/tree passes the runner and evidence verifier and supplies the
24 Linux snapshot hashes. Phase 10, release publication, deployment, and every execution-shaped
concept remain outside this decision.
