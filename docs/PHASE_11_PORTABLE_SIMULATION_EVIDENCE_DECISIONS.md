# Phase 11 portable local-simulation evidence decisions

## Authorized baseline and hard boundary

Phase 11 starts only from accepted Phase 10 commit
`3acd25f5bb4bcbeec684f672c3b816562d2366dc`, tree
`88929434b0e13ea2a7c3e4baf9c00d08c69fb276`. The implementation must remain
descended from that clean identity. Existing Phase 10 simulation artifacts remain the sole source
authority; this phase packages and verifies them but never creates, updates, replays, or re-evaluates
a simulation.

Phase 11 adds one deterministic read-only evidence bundle, one GET-only API operation, an explicit
local JSON download, and a database-free, network-disabled local verifier. It adds no migration,
simulation execution, replay, mutation, strategy expansion, provider, external data, account,
credential, broker, order routing, signing, publication, deployment, asynchronous work, or live
path. The live path remains absent, not disabled. No Phase 12 implementation is authorized.

## Exact portable bundle

FastAPI/Pydantic remains the schema authority. `LocalSimulationEvidenceBundle` has exactly five
required fields and rejects missing or unknown fields:

| Field | Contract |
|---|---|
| `bundle_schema_version` | literal `phase11-local-simulation-evidence-bundle-v1` |
| `bundle_sha256` | lowercase 64-character SHA-256 |
| `simulation_run_id` | UUID, exactly equal to the nested artifact identifier |
| `simulation_artifact_sha256` | lowercase 64-character SHA-256, exactly equal to the nested artifact digest |
| `simulation` | the complete existing `PaperSimulationArtifact`, without projection or reinterpretation |

`bundle_schema_version` has no default. The deterministic bundle digest uses the schema-version
literal as its domain and canonicalizes the other four complete fields, excluding only
`bundle_sha256`. The nested artifact includes its stored creation time and all checks, evidence
hashes, lineage, outcome, and optional ledger exactly as persisted.

Portable semantic validation binds the bundle to the existing Phase 10 contract. It requires the
nested identifiers and digests to match, decision time not to follow creation time, the exact seven
ordered Phase 10 checks, and the exact evidence sets derivable from the immutable simulation,
approval, research, configuration, risk, cost, and local-code evidence. A completed artifact must
have the one exact reconciled synthetic ledger already required by Phase 10. A blocked artifact must
have no ledger. Nothing in Phase 11 promotes or changes either outcome.

The SHA-256 values prove deterministic integrity only. They are not a signature, proof of
authenticity, publication receipt, proof of current authority, or permission to execute or replay a
simulation. A valid historical bundle can become stale relative to later governance; Phase 11 does
not perform current-authority resolution.

## Read-only API and local download

FastAPI owns exactly one Phase 11 operation:

```text
GET /v1/local-simulations/{simulation_run_id}/evidence-bundle
```

The operation has no request body or query parameter. It reads one existing Phase 10 artifact,
constructs the strict bundle in memory, and returns it. Missing artifacts return sanitized 404;
stored-evidence or projection conflicts return sanitized 409; malformed identifiers return 422.
There is no Phase 11 POST, PUT, PATCH, DELETE, retry, submit, replay, sign, publish, or export-server
operation. The existing Phase 10 API remains unchanged.

The UI prepares the bundle with one generated-contract GET and offers an explicit local JSON
download. The file uses recursively sorted keys, UTF-8, two-space indentation, LF line endings, and
one trailing newline. Download uses the already prepared in-memory object and performs no second
request. The surface states that it is `SIMULATED`, `LOCAL MOCK`, historical integrity evidence
only, and neither investment advice nor current authority. Preparing or downloading a bundle causes
no API mutation and no database write.

## Offline verifier

The standalone verifier is invoked with both the untrusted bundle and an independently supplied
expected digest:

```text
python scripts/verify_local_simulation_evidence.py --bundle PATH --expected-bundle-sha256 LOWERHEX64
```

It accepts one regular UTF-8 JSON file of at most 1 MiB. It rejects a byte-order mark, duplicate
keys, non-object roots, non-finite numbers, missing or unknown fields, unsupported schema versions,
schema violations, semantic inconsistencies, nested or bundle hash tampering, and a mismatch with
the separately supplied expected digest. Before model hashing, it bounds numeric coefficient and
exponent magnitude so a tiny hostile token cannot amplify into an unbounded canonical decimal.
Valid input exits 0 with deterministic sanitized JSON.
Invalid input and invalid invocation exit 2, emit no stdout, and emit exactly the generic stderr
`Local simulation evidence verification failed.` with no input path, payload, credential, stack
trace, or parser internals; `--help` exits 0.

The verifier imports no database, Redis, HTTP, provider, broker, or vendor client. It requires no
environment credential and performs no database access. A process audit hook denies socket creation,
process spawning, and shell execution, and startup actively proves socket denial. Acceptance runs it
with database and Redis variables removed and proves valid completed and blocked bundles as well as
adversarial field, ordering, identifier, ledger, hash, schema-version, duplicate-key, and expected-
digest tampering. No verifier code path executes or replays the simulation.

## Acceptance and stop condition

Phase 11 acceptance requires generated-contract parity; Python/frontend checks and tests; production
build; static policy; completed and blocked bundle/API/CLI proofs; adversarial tamper rejection; zero
database writes across bundle API, download, and browser checks; active network-denial proof;
inherited Phase 8 and Phase 10 browser regressions; immutable migration and repository proofs;
complete container, network, volume, temporary-file, and browser cleanup; and clean Windows and
Ubuntu results at one committed SHA/tree.

The closure verifier binds and prints the clean preflight identity and requires that identical clean
identity after cleanup. It rejects pre-existing or remaining `fable5_acceptance_*` resources.
Windows evidence does not substitute for Ubuntu evidence. Until Ubuntu CI passes at the same
committed identity, the implementation must be described as implemented but not formally accepted.

Stop after Phase 11. Do not push, open a pull request, tag, sign, publish, release, or deploy without
separate authorization. Do not create a Phase 12 plan or implementation as part of this phase.
