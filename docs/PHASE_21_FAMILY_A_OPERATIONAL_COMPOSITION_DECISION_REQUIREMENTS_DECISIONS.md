# Phase 21 Family A operational-composition decision-requirements decisions

## Accepted baseline and authority

Phase 21 starts only from the formally accepted Phase 20 identity:

```text
commit:                    01ed1ff17b91ba6961e02cdf1df3aa3e6be4859a
tree:                      b7a68998f1c99ed8b19ab08ae8a725726f04c423
Phase 20 artifact id:      e501d4f8-bebe-5e68-9457-56f6a589f478
Phase 20 artifact SHA-256: 902fca99d4fec1943403cbed406259f86c0eee05c41cb835b6daf7d165db340b
Phase 20 policy SHA-256:   e6be914218dc8b16b2c019ff8d72338dcf495b7cf375cd95281651b89939a31a
```

The Phase 20 Windows verifier passed in 4,427.7 seconds with complete cleanup. GitHub Actions run
`29724765420` passed `preflight`, `unit`, and `phase20-compose` at the same commit and tree. Phase 21
must preserve that lineage exactly and stop on any other baseline, dirty pre-existing worktree, or
ambiguous change.

The user authorizes Phase 21 and its repository lifecycle actions. That authorization establishes
the phase boundary only. It does not supply an operational source/product composition, select a
candidate, approve a provider, grant a right, or fill any Phase 20 input value.

Authority sources are `AGENTS.md`, `RESEARCH_SUPPLEMENT.md`, `docs/IMPLEMENTATION_PLAN.md`,
`docs/EVALS.md`, `docs/RISK_POLICY.md`, `docs/DATA_SOURCES.md`, `docs/COMPLIANCE_NOTES.md`, and the
accepted Phase 15-20 decision records and artifacts.

## Decision and truthful result

Phase 21 is a deterministic, portable, database-free, network-disabled operational-composition
decision-requirements artifact. It joins the accepted Phase 17 candidate inventory, Phase 18
fixed-time public-rights findings, and Phase 20 `OPERATIONAL_SOURCE_PRODUCT_COMPOSITION` input row
to freeze what a later explicit human decision must contain.

The exact successful domain result is:

```text
outcome:               BLOCKED
requirements_state:    DECISION_REQUIREMENTS_FROZEN
aggregate_conclusion: BLOCKED_AWAITING_EXPLICIT_OPERATIONAL_SOURCE_PRODUCT_COMPOSITION
```

`DECISION_REQUIREMENTS_FROZEN` means only that candidate, rights-finding, capability, field,
dependency, gate, rule, substitute, and inherited-state bytes reproduce. It is not a submitted
decision, a recommendation, a ranking, an operational composition, current-rights evidence, or
authority to contact a provider or begin Phase 16 Step 3.

Every one of the nine product-rights bindings has `operationally_selected=false` and
`current_rights_verified=false`. Phase 21 makes no product-eligibility conclusion and emits no
eligibility count. This is a narrow statement about accepted repository evidence, not a claim that a
product is unavailable externally, legal advice, a permanent vendor decision, or a substitute for
fresh account-specific review. The SEC public-use finding remains candidate-only because schema,
fitness, complete coverage, current access-policy compliance, and operational selection are
unproven. The FRED conclusion is bound to the fixed Phase 18 review and must be revalidated before
any later decision.

Phase 21 freezes these facts false:

```text
operational_source_product_composition_selected
composition_ranked
composition_value_present
selection_evidence_produced
operational_composition_output_produced
provider_selected
product_selected
source_selected
delivery_selected
credentials_loaded
account_verified
rights_currentness_guaranteed
operational_external_request_performed
```

It produces no `selection_evidence_sha256`, operational-composition output hash,
`non_synthetic_evaluation_policy_sha256`, `confirmation_holdout_definition_sha256`, or
`qualification_artifact_set_sha256`.

## Exact candidate-group registry

Bind these six Phase 17 groups in exact order. Every row has `candidate_only=true`,
`operationally_selected=false`, `ranked=false`, and preserves its accepted Phase 17 group hash and
product order:

```text
1 TIINGO_PHASE13_BOUNDED_CANDIDATE
2 MORNINGSTAR_CRSP_US_STOCK_DATABASES_CANDIDATE
3 MORNINGSTAR_CRSP_COMPUSTAT_MERGED_DATABASE_CANDIDATE
4 SEC_EDGAR_SUBMISSIONS_XBRL_CANDIDATE
5 FEDERAL_RESERVE_ALFRED_VINTAGES_CANDIDATE
6 HISTORICAL_LIQUIDITY_PRODUCT_UNSELECTED
```

Candidate enumeration is not a short list, recommendation, procurement choice, or permission to
contact a provider.

## Exact product-rights registry

Bind these nine Phase 17 products to the exact corresponding Phase 18 finding hashes:

```text
1 TIINGO_END_OF_DAY
2 TIINGO_US_FUNDAMENTALS
3 TIINGO_DIVIDEND_CORPORATE_ACTIONS
4 TIINGO_SPLIT_CORPORATE_ACTIONS
5 MORNINGSTAR_CRSP_US_STOCK_DATABASES
6 MORNINGSTAR_CRSP_COMPUSTAT_MERGED
7 SEC_EDGAR_SUBMISSIONS_AND_XBRL_DATA_APIS
8 FRED_REALTIME_AND_VINTAGE_WEB_SERVICE
9 LSEG_TICK_HISTORY_INSTRUMENT_AND_VENUE_WEB_API
```

Every binding has `operationally_selected=false`, `current_rights_verified=false`, and no score,
rank, or eligibility field. It preserves the exact accepted Phase 17 product and Phase 18 finding
hashes; it performs no new terms review and makes no external-currentness claim.

## Exact capability registry

Bind the seven Phase 16 required capabilities in exact order:

```text
1 security_master
2 universe_membership
3 ohlcv
4 corporate_actions
5 delistings
6 as_reported_fundamentals
7 macro_regime_inputs
```

Every row is `UNASSIGNED`, has `assigned_product_codes=()`, and
`assignment_value_present=false`. A candidate claim is not qualified coverage. Phase 21 must not emit selected product codes,
delivery ids, coverage dates, schema versions, availability values, or an inferred complete
composition. The Phase 15 `SECTOR_LIQUIDITY_MACRO_HISTORY` gap remains `MISSING`; candidate metadata
for sector or liquidity products does not upgrade it.

## Exact decision-field registry

The decision-field registry contains exactly these eight Phase 20 row-1 names in order:

```text
1 capability_product_composition_id
2 source_ids
3 product_ids
4 delivery_ids
5 selection_scope
6 selected_at_utc
7 selected_by
8 selection_evidence_sha256
```

Each row has `required=true`, `value_present=false`, and `evidence_produced=false`; its strict schema
has no decision-value field. A requirements-artifact hash is not `selection_evidence_sha256`.

## Exact post-selection dependencies

These three dependencies remain ordered and `BLOCKED_BY_MISSING_COMPOSITION`:

```text
1 CURRENT_EXECUTED_USE_RIGHTS_AND_REVOCATION
2 EXACT_DELIVERY_AND_SCHEMA_VERSIONS
3 DECLARED_PIT_COVERAGE_CALENDAR_AVAILABILITY_MISSINGNESS
```

Phase 21 does not start or satisfy them. A later explicit composition decision would still require
separate current-rights, schema/version, coverage/calendar, and external-action authority.

## Exact decision gates

The six decision gates are all `BLOCKED`, `passed=false`:

```text
1 EXPLICIT_HUMAN_COMPOSITION_DECISION
2 SINGLE_CLOSED_COMPOSITION
3 COMPLETE_CAPABILITY_ASSIGNMENT
4 CURRENT_RIGHTS_FOR_EXACT_COMPOSITION
5 INDEPENDENT_DECISION_EVIDENCE
6 POST_SELECTION_REVALIDATION
```

No gate may be inferred from candidate enumeration, a public-rights finding, a phase authorization,
or a repository lifecycle identity.

## Exact future-only transition rules

All eight rules have `future_only=true`, `applied=false`, and grant no external authority:

```text
1 CANDIDATE_REVIEW_IS_NOT_OPERATIONAL_SELECTION
2 RIGHTS_FINDING_IS_NOT_CURRENT_ACCOUNT_RIGHTS
3 ALL_DECISION_FIELDS_REQUIRED_TOGETHER
4 CAPABILITIES_REQUIRE_EXPLICIT_ASSIGNMENT
5 ONE_COMPOSITION_NO_RANKING
6 DECISION_EVIDENCE_MUST_BE_INDEPENDENT
7 POST_SELECTION_DEPENDENCIES_RUN_AFTER_DECISION
8 SEPARATE_AUTHORITY_REQUIRED_FOR_EXTERNAL_ACTION
```

## Exact forbidden-substitute registry

All ten rows are forbidden for operational-composition selection evidence:

```text
1 PHASE17_CANDIDATE_INVENTORY_IDENTITY
2 PHASE18_RIGHTS_REVIEW_IDENTITY
3 PHASE19_ASSESSMENT_IDENTITY
4 PHASE20_INPUT_REGISTER_IDENTITY
5 CANDIDATE_NAME_OR_PUBLIC_URL
6 SCORE_RANK_RECOMMENDATION_OR_DEFAULT
7 PLACEHOLDER_OR_ALL_ZERO_HASH
8 OPERATOR_OVERRIDE_OR_SELF_ATTESTATION
9 PR_TAG_RELEASE_PUBLICATION_DEPLOYMENT_IDENTITY
10 CREDENTIAL_ACCOUNT_REQUEST_OR_PROVIDER_RESPONSE
```

A commit, tree, PR, tag, release asset, published JSON, or isolated deployment proves only lifecycle
identity. None is an operational selection or external evidence.

## Inherited state preservation

Copy and hash-bind all twenty Phase 20 input rows without changing state or supplying values. Bind
both reserved Step 3 records as `MISSING`, `produced=false`, with no value/hash field. Preserve all
nineteen Phase 15 gap states exactly and all seven Phase 16 source-plan steps exactly:

```text
SELECT_CANDIDATE_PRODUCTS                           OUTPUT_FROZEN
REVIEW_CURRENT_USE_RIGHTS                          OUTPUT_FROZEN
QUALIFY_BOUNDED_READ_ONLY_SAMPLES                  NOT_STARTED
PRODUCE_FULL_HISTORY_COVERAGE_MANIFEST             NOT_STARTED
RECONCILE_TEMPORAL_IDENTITY_REVISION_SEMANTICS     NOT_STARTED
DESIGN_LOCAL_QUARANTINE_AND_CANONICAL_SNAPSHOT     NOT_STARTED
REQUEST_SEPARATE_INGESTION_AUTHORITY               NOT_STARTED
```

Phase 21 is not a source-plan step and cannot reinterpret Steps 1/2 as operational selection or
current executed rights.

## Frozen identities and canonicalization

Use these exact deterministic domains and generated identities:

```text
artifact schema/domain:        phase21-family-a-operational-composition-decision-requirements-v1
candidate-group schema:        phase21-family-a-candidate-group-binding-v1
product-rights schema:         phase21-family-a-product-rights-binding-v1
capability schema:             phase21-family-a-capability-assignment-v1
decision-field schema:         phase21-family-a-decision-field-requirement-v1
dependency schema:             phase21-family-a-post-selection-dependency-v1
gate schema:                   phase21-family-a-composition-decision-gate-v1
transition schema:             phase21-family-a-future-composition-rule-v1
forbidden-substitute schema:   phase21-family-a-forbidden-substitute-v1
inherited-input schema:        phase21-family-a-phase20-input-binding-v1
prior-evidence schema:         phase21-family-a-prior-evidence-binding-v1
gap-binding schema:            phase21-family-a-phase15-gap-binding-v1
step-binding schema:           phase21-family-a-source-plan-step-binding-v1
requirements-policy domain:    phase21-family-a-operational-composition-decision-requirements-policy-v1
candidate-groups manifest:     phase21-candidate-groups-manifest-v1
product-rights manifest:       phase21-product-rights-manifest-v1
capabilities manifest:         phase21-capabilities-manifest-v1
decision-fields manifest:      phase21-decision-fields-manifest-v1
dependencies manifest:         phase21-dependencies-manifest-v1
gates manifest:                phase21-gates-manifest-v1
rules manifest:                phase21-rules-manifest-v1
substitutes manifest:          phase21-substitutes-manifest-v1
inherited-inputs manifest:     phase21-phase20-inputs-manifest-v1
prior-evidence manifest:       phase21-prior-evidence-manifest-v1
gap-bindings manifest:         phase21-phase15-gaps-manifest-v1
source-plan-steps manifest:    phase21-source-plan-steps-manifest-v1
fixed timestamp:               2026-07-20T09:30:00.000000Z
artifact id:                   50086eea-4598-5e6b-b168-616321c7a068
embedded artifact SHA-256:     44b5c4541febe6f6e389480102346b802bb4627b81e8d38cab4110cb2eab6a6e
requirements-policy SHA-256:   22773ad7e58c4baa2c2f7d84bb68c7992d343676f93dc780374ce8e1125f99cf
candidate-groups SHA-256:      cab4f26a8ea1da3442048fac20dc9c9896ca557687d144ebb49414d6a68f854f
product-rights SHA-256:        c44f58b14c9cd9922dcd87792e5ef4fd4d36e62a85313307884ce7d3b402bf19
capabilities SHA-256:          fe06d66e62e0c30368deb1af49c878d3a8a916381a7dd4b07c87474b279a0163
decision-fields SHA-256:       cdfd17ee7b77941e205a9c08fdc4f3ca72f71fa62112c2e4647727b2c5694227
dependencies SHA-256:          bdff0734d441844b9ae62cdbff24ad26e0edfcb4a3fe4f76dcaf35ad9fe2c87c
gates SHA-256:                 cf5a3235fc4f2106114d7b6384dc667b09f58ff09dd78bce212aaf612d28186a
rules SHA-256:                 0626c8f647c8203beb4ba6fcdde0ac51d9d333b201cfdcccb0ebffac42aec7f5
substitutes SHA-256:           6c58f81c8ad17947701cd0ad0c97e9e6af633e7956974486622f222582e03e7f
inherited-inputs SHA-256:      b9443cbaedad4bbe3dfa04335b0a07a3fab136cc424db73891fb7872ed9614a2
prior-evidence SHA-256:        367f756349f564409264db00835ae4495ef35fc8ef230fe89f9a579f192366ae
gap-bindings SHA-256:          ca11abadf72ded8526b1abebbe7120e10595e804bbcb01582a80fd6fb2771c85
source-plan-steps SHA-256:     d8f56aeca7ffe5771149c523256adb5ecb4b7d961b45e3878fc6f87ec03d198c
committed file SHA-256:        3993469ed00646a5ff1c02bfec69f524ea95d239590fcd4eca15b7c47f7413d8
committed artifact bytes:      59,557
```

Every row and manifest uses a distinct domain-separated SHA-256 preimage. Contracts are frozen,
extra-forbid, length-bounded, and closed-enum. Root validation enforces exact tuple order, counts,
lineage, manifest parity, false authority, zero values, and the blocked result. Runtime clock,
randomness, Git discovery, environment values, filesystem discovery, and machine paths cannot
affect artifact bytes.

## Generator and verifier boundary

The stdout-only generator accepts exactly `--confirm-decision-requirements-only`; it accepts no
product, selection, score, rank, value, evidence, provider, credential, account, URL, path, output,
clock, seed, expected hash, or semantic override.

The verifier accepts exactly:

```text
python scripts/verify_family_a_operational_composition_decision_requirements.py --requirements PATH
```

It reads one bounded local regular canonical UTF-8 JSON file. Generation and verification deny
network, socket, database, subprocess, credential, provider, research, broker, and execution
dependencies. Invalid input exits 2 with no stdout and one generic sanitized error. A valid blocked
artifact exits 0 because `BLOCKED` is the truthful domain result.

## Authority, persistence, and security invariants

Freeze false every selection, submission, rank, score, recommendation, provider/counsel contact,
account/credential access, entitlement/license/currentness verification, external request, sample,
capture, persistence, ingestion, snapshot, input value, transition application, policy/holdout
creation or approval, Step 3 start, research, performance, promotion, paper approval, risk clearance,
execution, and order field. Freeze true `metadata_only`, `requirements_only`,
`runtime_network_disabled`, `live_path_absent`, `no_personalized_investment_advice`, and
`no_real_performance_claimed`.

No secret, account id, credential name value, contract/license body, provider response, observation,
dataset, schema payload, date/interval value, label, return, metric, price, position, order, or fill may
enter source, fixtures, artifact, diagnostics, logs, build output, browser output, CI evidence, or
temporary output.

Phase 21 adds no migration, table, row, database connection, API route, OpenAPI path, generated
TypeScript, dependency, Compose service, frontend control, scheduler, worker, queue, retry, transport,
broker, or runtime behavior. Alembic remains `0011_phase14`; all 57 inherited tables/functions, rows,
migrations, API paths, and generated-contract bytes remain unchanged.

## Lifecycle publication and deployment boundary

After clean Windows and Ubuntu acceptance at one committed SHA/tree, a PR, tag, release, or
publication may expose only that exact blocked artifact and its documentation. Release text must
state the three blocked result fields conspicuously and must not claim operational readiness,
entitlement, performance, or external-data authority.

The only Phase 21 deployment permitted is an isolated loopback Compose instance used after
acceptance to reproduce the inherited product and blocked artifact. It is not an external,
production, cloud, provider-connected, or continuously running deployment. It creates no new
deployment code or configuration and must be completely cleaned up. A deployment identity is
forbidden as selection evidence.

## Acceptance and adversarial failure semantics

Acceptance requires repeated deterministic generation and committed-file parity; exact accepted
Phase 20 lineage; exact 6/9/7/8/3/6/8/10 registry counts and order; zero selected and zero
current-rights-verified product bindings; all capabilities unassigned and fields absent; exact
unchanged inputs, missing evidence, gaps, and steps; every transition unapplied; and every positive
authority field false.

Adversarial tests reject any selected product or source, ranking/score/default, decision value,
positive eligibility, current-rights assertion, external-currentness claim, state upgrade,
substitute hash, Step 3 advance, policy/holdout output, secret/data canary, database/network/
subprocess dependency, malformed or noncanonical JSON, duplicate key, float/non-finite value, BOM,
oversize, symbolic/nonregular/remote/UNC/device/different-drive path, or unstable read. They also
reject migration, row, API, OpenAPI, generated-contract, dependency, browser-baseline, inherited
behavior, cleanup, or unsupported phase 0/22 drift.

Windows and Ubuntu `phase21-compose` must pass at one clean committed SHA/tree and prove complete
container, network, volume, process, and temporary-evidence cleanup before Phase 21 is accepted.

## Stop condition

Stop after Phase 21 and its explicitly authorized lifecycle closure. Do not begin Phase 22, submit an
operational composition, contact a provider or counsel, load a credential, inspect an account or
license, request or capture data, create either Step 3 hash, advance Step 3, define/open a holdout,
run/promote research, change risk/governance, submit/reconcile an order, or add a live capability.
