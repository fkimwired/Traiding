# Phase 27 Family A selected-composition rights and entitlement evidence intake decisions

## Decision and truthful outcome

Phase 27 freezes the evidence-intake contract for the exact Phase 26 composition
`FAMILY_A_CRSP_SEC_RTDSM_V1`. It records what independently verified evidence must establish for
Morningstar CRSP U.S. Stock Databases, SEC EDGAR, and Philadelphia Fed RTDSM before any later phase
may propose acquiring exact delivery bytes.

No CRSP executed agreement or Linux flat-file entitlement, authenticated RTDSM exact-scope response,
or current SEC policy-revalidation evidence was supplied to this phase. The truthful current result is:

```text
outcome:                    BLOCKED
determination:              COMPOSITION_RIGHTS_ENTITLEMENT_EVIDENCE_MISSING
verified_evidence_recorded: false
```

The deterministic canonical no-input artifact is pinned as:

```text
Phase 27 artifact id:         6d3bc146-67ad-5aa1-8836-dd5130d8736e
Phase 27 artifact SHA-256:    9721a4e1ebf1024a9d11695c9144f54046954e012470c7ca6c715f32a714925e
Phase 27 file SHA-256:        b2525ad22c1a0f1569188a7aefa3d735da1903d098725a8346c762d7c0d4214b
Phase 27 evidence bundle id:  63bc191d-03ef-54ae-afa6-599e4f287cfe
Phase 27 bundle SHA-256:      f2d6a793e0208f57b4675f2efffe6de330a2ea9a8d895420c4011c3b12e02d14
Phase 27 config SHA-256:      3792dffdf784c5354b973b0de3ecc6c5119cc97a67cdf065d2e826caede29505
```

A future complete and independently verified evidence set may reach only:

```text
outcome:                    BLOCKED
determination:              VERIFIED_EVIDENCE_RECORDED_REQUIRES_SEPARATE_ACQUISITION_AUTHORITY
verified_evidence_recorded: true
```

That positive substate would satisfy only the Phase 26
`CURRENT_EXECUTED_USE_RIGHTS_AND_REVOCATION` dependency. It would not authorize data acquisition,
qualify delivery bytes or schemas, establish point-in-time fitness, admit research, or authorize an
order. Phase 27 is an engineering evidence classification, not legal advice.

## Accepted baseline and authority

Phase 26 is formally accepted at the same identity on Windows and Ubuntu:

```text
accepted Phase 26 commit:     b1ad522c666f472f02ad5995d8fa52e3413c2cac
accepted Phase 26 tree:       d1b74532704708e97047e4abf704532102ba510a
same-SHA Ubuntu workflow run: 29952642818
Phase 26 artifact id:         3697996f-5ff7-5c14-b0af-db105b83ec30
Phase 26 artifact SHA-256:    ffa06ce79fa249c8d6e46f730c737160d052ee2a02a74465ba34a9b4aa8775a9
Phase 26 file SHA-256:        366206d2d0122e28ad95056765f840e3e12087ab1b29f17956f206ba27840175
Phase 26 policy SHA-256:      ead7fce5ee1a261277d49803f40e2a84983da8da7e83992441780817f83c4613
Phase 26 selection SHA-256:   6930d8525abafc66b68394de6b6b8ba3d79209916b3e4dee10d3e8a64beee98e
```

The repository owner's explicit authorization names Phase 27 and permits the offline portable
metadata intake/evaluator and its documentation. This `P27-DOC` unit owns documentation only. The
authorization does not supply provider evidence and does not authorize outreach, procurement,
accepting terms, account inspection, credential use, or a provider request.

Phase 27 preserves the exact Phase 26 selection:

| Capability | Product | Selected delivery |
|---|---|---|
| `security_master`, `universe_membership`, `ohlcv`, `corporate_actions`, `delistings` | `MORNINGSTAR_CRSP_US_STOCK_DATABASES` | `MORNINGSTAR_CRSP_US_STOCK_DATABASES_LINUX_FLAT_FILE` |
| `as_reported_fundamentals` | `SEC_EDGAR_SUBMISSIONS_AND_XBRL_DATA_APIS` | `SEC_EDGAR_NIGHTLY_SUBMISSIONS_BULK_ARCHIVE`; `SEC_EDGAR_NIGHTLY_COMPANYFACTS_BULK_ARCHIVE` |
| `macro_regime_inputs` | `PHILADELPHIA_FED_REAL_TIME_DATA_SET_FOR_MACROECONOMISTS` | `PHILADELPHIA_FED_RTDSM_PCPI_MONTHLY_VINTAGE_WORKBOOK` |

No product, delivery, capability, series, provider, or account may be added through evidence intake.

## Closed evaluation vocabulary

Each evidence requirement uses exactly `PASS`, `FAIL`, `CONDITIONAL`, or `MISSING`. Independent
verification uses exactly `VERIFIED`, `FAILED`, or `UNVERIFIED`.

- `PASS` requires one or more cited immutable evidence IDs whose authority and integrity are
  independently verified.
- `FAIL` requires independently verified evidence that conflicts with the required use and always
  blocks the aggregate.
- `CONDITIONAL` satisfies only when every condition has a stable condition ID, enforceable control
  ID, executable acceptance-test ID, `enforceable=true`, and `acceptance_test_passed=true`.
- `MISSING`, ambiguity, a missing evidence reference, uncontrolled conditions, expired evidence,
  conflicting scope, or failed mutual consistency blocks the aggregate.

For private rights evidence, acceptable authenticated provenance is an executed agreement,
authenticated provider portal record, cryptographically signed response, or rights-holder record.
`EMAIL_ONLY`, `PUBLIC_WEBPAGE_ONLY`, `VERBAL_STATEMENT`, and `SCREENSHOT_ONLY` may be recorded but
cannot verify CRSP or RTDSM authority. SEC public-policy evidence has a separate, SEC-only
first-party-policy classification and cannot be reused as private-license authority.

## Common authority and integrity evidence

Every private authority record must include:

1. responder organization, stable identity, role, and verified authority basis;
2. exact rights-holding legal entity and exact licensed party;
3. UTC response and effective dates, plus either an expiry date or an explicit no-expiry reason;
4. governing agreement, order form or product schedule, and terms version;
5. immutable evidence ID and SHA-256, authenticated provenance type, and hashed locator;
6. independent verification state and hashed verifier identity; and
7. explicit booleans proving responder identity authentication and authority-basis verification.

Raw agreement text, provider-response bodies, personal identifiers, credentials, cookies, account
numbers, and entitlement tokens do not belong in a repository artifact. Account or entitlement
identity is represented only as `SANITIZED_HASH_ONLY` plus a SHA-256. Evidence presence is not
verification, and a commit, PR, repository-owner instruction, credential, successful retrieval, or
public marketing page is not provider-rights evidence.

## CRSP U.S. Stock Databases requirements

A positive CRSP result requires mutually consistent, independently verified evidence for every row:

| Code | Exact requirement |
|---|---|
| `CRSP_RIGHTS_HOLDER_AND_LICENSEE` | Identify the exact rights-holding and licensed legal entities and authorized signers. |
| `CRSP_EXECUTED_AGREEMENT` | Bind an executed agreement, order form, product schedule, and governing terms version. |
| `CRSP_PRODUCT_AND_SKU` | Bind the entitlement to `MORNINGSTAR_CRSP_US_STOCK_DATABASES`, not a generic research-product catalog. |
| `CRSP_LINUX_FLAT_FILE_ENTITLEMENT` | Prove the exact `MORNINGSTAR_CRSP_US_STOCK_DATABASES_LINUX_FLAT_FILE` delivery entitlement. A page listing Linux as an available option does not pass. |
| `CRSP_CAPABILITY_SCOPE` | Cover the selected security-master, historical universe-membership, OHLCV, corporate-action, and delisting uses. |
| `CRSP_TERRITORY_USERS_DEVICES` | Specify territory, every permitted user, and device or installation limits. |
| `CRSP_ENVIRONMENTS` | Cover local development, test, internal research, backtest, and clearly simulated paper environments. |
| `CRSP_AUTOMATED_ACCESS_AND_LOAD` | Specify delivery, installation, update, frequency, concurrency, rate, and bulk-access constraints. |
| `CRSP_EXACT_BYTES_AND_SNAPSHOT_STORAGE` | Permit or prohibit exact delivery-byte storage, immutable point-in-time snapshots, and reproducibility copies separately. |
| `CRSP_BACKUPS_RETENTION_DELETION` | Specify backup handling, retention limits, deletion deadlines, and post-termination obligations. |
| `CRSP_NORMALIZATION_AND_POINT_IN_TIME` | Resolve normalization, identifier history, adjustment, revision, and point-in-time transformation rights. |
| `CRSP_NONDISPLAY_INTERNAL_RESEARCH` | Resolve automated internal feature generation, statistical modeling, backtesting, and simulated paper research. |
| `CRSP_DERIVED_ARTIFACTS` | Resolve derived features, aggregates, diagnostics, model parameters, and audit hashes. |
| `CRSP_DISPLAY_EXPORT_SHARING_REDISTRIBUTION` | Resolve display, export, internal sharing, publication, and redistribution separately for raw and derived outputs. |
| `CRSP_ATTRIBUTION_AND_NOTICES` | Record required source labels, notices, citations, and permitted use of names or marks. |
| `CRSP_THIRD_PARTY_RIGHTS` | Establish applicable exchange, contributor, and other upstream rights for the exact fields and uses. |
| `CRSP_AUDIT_AND_COMPLIANCE` | Specify audit, reporting, usage-measurement, and compliance-control obligations. |
| `CRSP_TERMINATION_REVOCATION_CURRENTNESS` | Specify term, renewal, change notice, suspension, revocation, cure, cessation, and revalidation requirements. |

Any missing executed private license, product/SKU mismatch, generic rather than Linux-specific
delivery evidence, or unresolved third-party right blocks CRSP.

## RTDSM requirements

Phase 27 preserves the Phase 24/25 fail-closed response model. All ten questions require explicit,
independently verified answers:

| # | Code | Phase 24 field |
|---:|---|---|
| 1 | `PERSISTENT_STORAGE` | `persistent_storage` |
| 2 | `AUTOMATED_MODEL_INTERNAL_USE` | `automated_model_internal_use` |
| 3 | `DERIVED_DATA_AND_MODEL_ARTIFACTS` | `derived_data` |
| 4 | `RETENTION_DELETION` | `retention_deletion` |
| 5 | `REDISTRIBUTION_AND_DISPLAY` | `redistribution` |
| 6 | `ATTRIBUTION` | `attribution` |
| 7 | `THIRD_PARTY_BLS_CONTENT` | `third_party_content` |
| 8 | `AUTOMATED_ACCESS_AND_LOAD` | `access_load` |
| 9 | `REVOCATION_AND_CURRENTNESS` | `revocation_currentness` |
| 10 | `AUTHORITY_AND_PRODUCT_SCOPE` | `operational_use_cleared` |

All nineteen exact-scope codes also require independently verified answers:

```text
PRODUCT
REQUESTED_SERIES
PCPI_AND_BLS_ORIGIN
DELIVERY_METHOD_AND_SURFACE
LICENSED_PARTY
ACCOUNT_OR_ENTITLEMENT
PERMITTED_USERS_AND_DEVICES
ENVIRONMENTS
AUTOMATED_ACCESS_LIMITS
RAW_PAYLOAD_STORAGE
IMMUTABLE_SNAPSHOT_STORAGE
BACKUPS_AND_REPRODUCIBILITY
NORMALIZATION_AND_POINT_IN_TIME
INTERNAL_RESEARCH_USES
DERIVED_ARTIFACTS
DISPLAY_EXPORT_SHARING_PUBLICATION_REDISTRIBUTION
ATTRIBUTION
RETENTION_DELETION_TERMINATION
REVOCATION_AND_REVALIDATION
```

Positive scope must bind the exact RTDSM product, requested series `PCPI`, delivery
`PHILADELPHIA_FED_RTDSM_PCPI_MONTHLY_VINTAGE_WORKBOOK`, and licensed party
`INDIVIDUAL_ACCOUNT_HOLDER`. The `PCPI_AND_BLS_ORIGIN` determination must be exactly
`PCPI_BLS_ORIGIN_EXPLICITLY_COVERED`. Every question and scope row must cite verified immutable
authority evidence, and the mutual-consistency gate must be `VERIFIED` with at least one verified
evidence reference.

## SEC EDGAR requirements

Phase 27 may classify only independently reviewed metadata from the accepted first-party source set:

```text
SEC_PRIVACY_AND_DISSEMINATION
SEC_WEBMASTER_REUSE_FAQ
SEC_EDGAR_APIS
SEC_DEVELOPER_RESOURCES
SEC_ACCESSING_EDGAR
```

Each current-policy record must include source code, exact URL, official title, publisher,
publisher-stated date, UTC retrieval/effective/revalidation-due dates, policy version, clause locator,
content SHA-256, exact accepted Phase 18 source SHA-256, hashed provenance locator, normalized finding
and delta, and independent verification metadata. A retrieval date or successful HTTP response alone
is not currentness or authority. The intake stores no remote page body.

The evaluation must bind only the two selected nightly bulk archives and independently satisfy every
closed requirement:

| Code | Exact requirement |
|---|---|
| `OFFICIAL_FIRST_PARTY_POLICY_PROVENANCE` | Bind policy evidence to the exact accepted official first-party SEC HTTPS source set. |
| `EXACT_SELECTED_BULK_PRODUCTS_AND_SURFACES` | Cover nightly submissions and companyfacts bulk archives, without adding a delivery. |
| `POLICY_VERSION_EFFECTIVE_DATE_AND_CURRENTNESS` | Record policy version, effective/retrieval time, and revalidation horizon. |
| `FAIR_ACCESS_AGGREGATE_RATE` | Record the current aggregate fair-access rate. |
| `DECLARED_USER_AGENT_AND_ADMIN_CONTACT` | Record the declared User-Agent and administrative-contact requirement. |
| `AUTOMATED_BULK_RETRIEVAL` | Resolve automated bulk-retrieval constraints. |
| `PERSISTENT_STORAGE_BACKUPS_AND_INTERNAL_USE` | Resolve storage, backups, and internal-use treatment. |
| `NORMALIZATION_DERIVED_OUTPUTS_AND_NON_DISPLAY_USE` | Resolve normalization, derived outputs, and non-display treatment. |
| `ATTRIBUTION_DISPLAY_AND_REDISTRIBUTION` | Resolve attribution, display, and redistribution treatment. |
| `RETENTION_REVOCATION_AND_CHANGE_MONITORING` | Resolve retention, revocation, currentness, and policy-change monitoring. |
| `CITATION_SEAL_LOGO_AND_NONAFFILIATION` | Record citation, seal/logo restrictions, and non-affiliation language. |
| `THIRD_PARTY_AND_CONTENT_SPECIFIC_EXCEPTIONS` | Resolve third-party and content-specific exceptions for the selected archives. |

Daily or quarterly indexes may be referenced as later point-in-time qualification dependencies, but
Phase 27 must not silently add them to the closed Phase 26 composition. SEC policy evidence remains
historical evidence: even a verified Phase 27 row must be revalidated immediately before any later,
separately authorized SEC request. Policy review is not schema or point-in-time qualification.

## Aggregate transition rules

The verified-evidence determination requires every CRSP, RTDSM, and SEC row to satisfy; every cited
evidence ID to exist and be independently verified; and one independently evidenced
mutual-consistency result across legal entity, product, delivery, user, environment, use, retention,
and currentness scope. The package outcome remains `BLOCKED`. Any product, delivery, licensed-party,
terms, rights-holder, expiry, revocation, or selected-use change forces revalidation and blocks
reliance on the earlier result.

The current no-evidence state leaves all three provider groups missing and keeps the Phase 26 schema
and point-in-time dependencies blocked. An artifact identity, public statement, subscription payment,
API key, or successful retrieval cannot substitute for a provider-specific evidence row.

## Required audit fields

The Phase 27 canonical package must carry:

- accepted Phase 26 commit/tree; artifact ID, embedded/file SHA-256, policy SHA-256,
  selection-evidence SHA-256, composition ID, and source-snapshot ID/SHA-256;
- Phase 27 schema version, artifact ID/SHA-256, policy/config ID and SHA-256;
- CRSP, RTDSM, and SEC evidence-manifest SHA-256 values plus an aggregate evidence-bundle ID and
  SHA-256;
- generation git SHA, deterministic UTC generation time, evidence response/effective/expiry or
  retrieval UTC values, random seed `0`, and trial count `0`; and
- explicit false authority fields for credential loading, provider contact by generation or
  verification, terms acceptance, observation request/download/persistence, acquisition, schema and
  point-in-time qualification, adapter activation, research ingestion/run, performance, promotion,
  risk mutation, order submission, and execution, with `paper_only=true` and
  `live_path_absent=true`.

The separate Phase 27 evaluator derives a canonical, hash-bound package in memory, its generator
writes canonical JSON only to stdout, and the repository commits the deterministic no-input artifact.
No provider-supplied intake or evidence body is committed. The implementation remains database-free
and network-disabled and adds no migration, API, generated contract, runtime adapter, credential
loader, dependency, or UI. This decision record does not fabricate provider responses, current
terms, or rights.

## Acceptance and literal negative assertion

This documentation unit is accepted only when the Phase 26 formal-acceptance identity is exact; all
three evidence groups and the current missing outcome are present; documentation references agree;
the write set contains documentation only; and repository hard gates remain intact.

Run from the repository root:

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

After the reviewed Phase 27 diff is committed, and before push, run the clean-tree closure:

```powershell
git status --short
.\.venv\Scripts\python.exe scripts\verify_phase1.py --phase 27
git status --short
```

Both status commands must be empty; the full verifier binds the same commit/tree before and after
acceptance and proves inherited Compose cleanup.

Literal negative assertion:

> Phase 27 authorizes no credential loading, provider outreach, terms acceptance, provider
> observation request, download or persistence, acquisition, schema or point-in-time qualification,
> adapter, snapshot, evaluation policy, holdout, research run, candidate screen, performance claim,
> recommendation, risk mutation, order, execution, or live path.

## Stop condition and Phase 28 boundary

Stop this `P27-DOC` unit after the decisions, handoff, and status reconciliation. Do not use the
documentation unit to create or alter the separate Phase 27 evaluator, generator, verifier, tests,
CI, credential path, provider request, evidence file, or data file.

If a later Phase 27 evidence artifact truthfully reaches the verified substate, Phase 28 still requires
separate authorization to define a bounded acquisition and exact-delivery/schema qualification. It
must revalidate current SEC policy immediately before any request and must stop independently before
point-in-time qualification, research admission, research execution, performance, promotion, risk
mutation, paper-order capability, execution, or any live path.
