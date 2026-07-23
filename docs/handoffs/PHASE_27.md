# Phase 27 Family A rights and entitlement evidence-intake handoff

## Objective and current result

Freeze the offline, metadata-only evidence-intake contract for the exact Phase 26 composition
`FAMILY_A_CRSP_SEC_RTDSM_V1`. No provider evidence was supplied, so the truthful result is:

```text
outcome:                    BLOCKED
determination:              COMPOSITION_RIGHTS_ENTITLEMENT_EVIDENCE_MISSING
verified_evidence_recorded: false
```

```text
Phase 27 artifact id:         6d3bc146-67ad-5aa1-8836-dd5130d8736e
Phase 27 artifact SHA-256:    9721a4e1ebf1024a9d11695c9144f54046954e012470c7ca6c715f32a714925e
Phase 27 file SHA-256:        b2525ad22c1a0f1569188a7aefa3d735da1903d098725a8346c762d7c0d4214b
Phase 27 evidence bundle id:  63bc191d-03ef-54ae-afa6-599e4f287cfe
Phase 27 bundle SHA-256:      f2d6a793e0208f57b4675f2efffe6de330a2ea9a8d895420c4011c3b12e02d14
Phase 27 config SHA-256:      3792dffdf784c5354b973b0de3ecc6c5119cc97a67cdf065d2e826caede29505
```

The contract requires current executed CRSP rights and the exact Linux flat-file entitlement, an
authenticated RTDSM response satisfying all ten Phase 24 questions and nineteen Phase 25 scope rows,
and current SEC first-party policy evidence for the two selected nightly EDGAR bulk archives.

## Accepted input identity

```text
accepted Phase 26 commit:     b1ad522c666f472f02ad5995d8fa52e3413c2cac
accepted Phase 26 tree:       d1b74532704708e97047e4abf704532102ba510a
same-SHA Ubuntu workflow run: 29952642818
Phase 26 artifact id:         3697996f-5ff7-5c14-b0af-db105b83ec30
Phase 26 artifact SHA-256:    ffa06ce79fa249c8d6e46f730c737160d052ee2a02a74465ba34a9b4aa8775a9
Phase 26 file SHA-256:        366206d2d0122e28ad95056765f840e3e12087ab1b29f17956f206ba27840175
```

The accepted Phase 26 decision and artifact remain unchanged.

## Scope and evidence boundary

The governing record is
`docs/PHASE_27_FAMILY_A_RIGHTS_AND_ENTITLEMENT_EVIDENCE_INTAKE_DECISIONS.md`. It defines the exact
CRSP, RTDSM, and SEC evidence requirements, fail-closed evaluation vocabulary, authority and
integrity metadata, audit fields, negative assertions, and transition rules.

Phase 27 adds a strict offline portable metadata intake/evaluator, stdout-only generator, bounded
offline verifier, focused tests, one deterministic canonical no-input artifact, and this
documentation. It commits no provider-supplied intake or evidence body and performs no outreach,
network request, account inspection, credential loading, procurement or terms acceptance, provider
observation, data or page-body persistence, adapter work, schema capture, point-in-time
qualification, evaluation-policy or holdout work, research, candidate screening, performance
calculation, risk mutation, order, or execution. The `P27-DOC` implementation unit changes
documentation only.

Any future verified result may use only determination
`VERIFIED_EVIDENCE_RECORDED_REQUIRES_SEPARATE_ACQUISITION_AUTHORITY`; the package outcome remains
`BLOCKED`, and exact delivery/schema authority remains false. It satisfies only the first Phase 26
post-selection dependency and creates no acquisition or research authority.

## Audit requirements

The canonical package must bind the accepted Phase 26 identity; its own policy/config,
artifact, provider-manifest, and evidence-bundle hashes; git SHA; deterministic UTC times; seed and
trial count `0/0`; independently verified immutable evidence IDs; and explicit false fields for every
provider-data, research, execution, order, and live authority. Raw agreements, provider bodies,
personal identifiers, credentials, and entitlement tokens are prohibited; account/entitlement
identity is hash-only.

## Acceptance commands

```powershell
git diff --check
.\.venv\Scripts\python.exe -m pytest `
  services\data\tests\test_phase27_contracts.py `
  services\data\tests\test_phase27_package.py `
  services\data\tests\test_phase27_security.py `
  tests\test_phase27_portable.py `
  tests\test_phase27_static.py -q
.\.venv\Scripts\python.exe scripts\verify_family_a_rights_and_entitlement_evidence_intake.py `
  --artifact docs\PHASE_27_FAMILY_A_RIGHTS_AND_ENTITLEMENT_EVIDENCE_INTAKE.json
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m mypy
.\.venv\Scripts\python.exe scripts\verify_phase1.py --static-only --phase 27
.\.venv\Scripts\python.exe -m pytest -q
npm test
npm run lint
npm run typecheck
npm run contracts:check
npm run build
```

After the reviewed Phase 27 diff is committed, and before it is pushed, the clean-tree closure gate
is:

```powershell
git status --short
.\.venv\Scripts\python.exe scripts\verify_phase1.py --phase 27
git status --short
```

Both status commands must be empty. The full verifier deliberately rejects an uncommitted or staged
tree, binds the same commit/tree before and after acceptance, and proves inherited Compose cleanup.

Literal adversarial assertion: adding a credential field, provider URL fetch, raw body, data file,
schema sample, research/candidate output, order surface, execution flag, or live path is outside Phase
27 and fails review.

## Stop condition

Stop after Phase 27. The boundary ends with the offline package, generator, verifier, tests,
documentation, and acceptance
evidence. Do not commit provider-supplied intake or evidence JSON beyond the canonical no-input
artifact, supply or fabricate provider evidence, contact a provider, load credentials, or make an
external request. Phase 28 requires separate authorization for a
bounded acquisition and exact-delivery/schema-qualification contract, and even that phase must stop
before point-in-time qualification, research admission, performance, promotion, orders, execution,
or any live capability.
