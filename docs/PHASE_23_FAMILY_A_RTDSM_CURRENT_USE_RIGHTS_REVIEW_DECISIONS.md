# Phase 23 Family A RTDSM current-use-rights review decisions

## Accepted baseline and objective

Phase 23 starts from the formally accepted Phase 22 implementation and its merge to `main`:

```text
accepted Phase 22 commit: 1c07fbe8e23950e8c9f910b30473c900c0bf3e21
accepted Phase 22 tree:   1261f5a9da883e14a894b33e583068681f8cf459
Phase 22 merge commit:    7f3bf3df029a894660f0e47dda1056bd32dca297
Phase 22 artifact id:     9d763c2d-af50-5403-9646-50a88c962bd7
Phase 22 artifact SHA:    6f6079b69838cdd292f3d426c0b1e23deeec35eaeed9f4129aa129585913abe1
```

The merge commit has two parents, includes the accepted Phase 22 commit as its second parent, and
has the exact accepted Phase 22 tree. Both Phase 22 Ubuntu workflows passed `preflight`, `unit`, and
`phase22-compose` before the merge.

The sole Phase 23 objective is the first ordered unresolved Phase 22 requirement:
`INDEPENDENT_CURRENT_USE_RIGHTS_AND_REVOCATION`. It freezes a conservative technical review of
current public Philadelphia Fed terms for the exact RTDSM candidate. This review is not a legal
opinion, rights grant, entitlement, product selection, data qualification, or operational approval.

## Decision and truthful result

The exact result is:

```text
outcome:              BLOCKED
review_state:         PUBLIC_TERMS_RIGHTS_REVIEW_FROZEN
aggregate_conclusion: BLOCKED_PUBLIC_TERMS_INSUFFICIENT_FOR_PERSISTENT_AUTOMATED_MODEL_USE
```

The official RTDSM overview expressly describes macroeconomic research, verification, policy
analysis, and forecasting uses. The current online terms also say that terms may change without
notice, require owner permission for copyrighted material, prohibit excessive access, and disclaim
noninfringement. A separate official changes page identifies PCPI and related indices as originating
from the Bureau of Labor Statistics.

Those public pages do not expressly resolve persistent storage, automated internal-model use,
derived data, retention or deletion, redistribution, attribution, or all third-party-content rights
for Fable5's exact intended use. Phase 23 therefore cannot truthfully produce a positive rights
finding. Absence of an express restriction is not converted into permission.

## Exact source registry and finding

The artifact freezes exactly three inert first-party citations, without storing their response
bodies or making a runtime request:

1. `PHILADELPHIA_FED_ONLINE_TERMS` —
   [Online Terms of Use and Privacy Notice](https://www.philadelphiafed.org/about-us/privacy-notice)
2. `PHILADELPHIA_FED_RTDSM_OVERVIEW` —
   [Real-Time Data Set for Macroeconomists](https://www.philadelphiafed.org/surveys-and-data/real-time-data-research/real-time-data-set-for-macroeconomists)
3. `PHILADELPHIA_FED_RTDSM_CHANGES` —
   [Changes to the Real-Time Data Set](https://www.philadelphiafed.org/surveys-and-data/real-time-data-research/changes-to-the-real-time-data-set)

The sole finding remains bound to product
`PHILADELPHIA_FED_REAL_TIME_DATA_SET_FOR_MACROECONOMISTS` and the accepted Phase 22 product hash.
Research purpose is classified `EXPRESSLY_PERMITTED_RESEARCH_PURPOSE_ONLY`; storage, automated
model use, derived data, retention/deletion, redistribution, and attribution are
`NOT_EXPRESSLY_ADDRESSED`; copyrighted third-party content is
`OWNER_PERMISSION_REQUIRED_WHEN_COPYRIGHTED`; currentness is
`CHANGE_WITHOUT_NOTICE_REVALIDATION_REQUIRED`; and `operational_use_cleared=false`.

## Requirement progression

Only the first Phase 22 requirement receives an output. No requirement is satisfied and no
external action is authorized:

```text
INDEPENDENT_CURRENT_USE_RIGHTS_AND_REVOCATION                OUTPUT_FROZEN_BLOCKED
EXACT_SERIES_DELIVERY_SCHEMA_COVERAGE_AND_AVAILABILITY      NOT_STARTED
BLS_RELEASE_ARCHIVE_RECONCILIATION                           NOT_STARTED
EXPLICIT_OPERATIONAL_SOURCE_PRODUCT_COMPOSITION              BLOCKED
```

The blocked output does not authorize a sample, download, provider request, account inspection,
credential use, data persistence, schema/coverage review, BLS reconciliation, source selection, or
operational composition. Any later clarification, executed agreement, or legal assessment must be
separately authorized and independently revalidated before it can supersede this public-terms-only
finding.

## Frozen identities

```text
artifact schema/domain:     phase23-family-a-rtdsm-current-use-rights-review-v1
source schema/domain:       phase23-family-a-rtdsm-public-terms-source-v1
finding schema/domain:      phase23-family-a-rtdsm-rights-finding-v1
requirement schema/domain:  phase23-family-a-future-requirement-status-v1
policy domain:              phase23-family-a-rtdsm-current-use-rights-review-policy-v1
sources manifest domain:    phase23-rtdsm-public-terms-sources-manifest-v1
findings manifest domain:   phase23-rtdsm-rights-findings-manifest-v1
requirements manifest:      phase23-rtdsm-future-requirements-manifest-v1
artifact UUID namespace:    94ac57dc-a239-5b13-b76e-32fb57ba1e3e
fixed timestamp:            2026-07-21T00:30:00.000000Z
reviewed on:                2026-07-20
artifact id:                e4fbd5af-c5ad-51fb-92cb-7308fafd017a
embedded artifact SHA-256:  aafb6deadff7b4cd4f9b4e7c98c8ac31f0d957a60b1d5be59f3d7ebf2679cd2c
policy SHA-256:             624c553bc1a7777e33634464743b4e0d37115136afedca81c2cdbc43c819dd16
sources manifest SHA-256:   18b31182eef9f8c9344eee8c4f71794679f716e62d127d74e8eb0bbc11371092
findings manifest SHA-256:  43e8f5dc60ce6de114510b8c763d28da371b9d57a82854c62e4b6b746ffcb06b
requirements manifest SHA: 17bb6f314ed053f6a4d7683af361e151deb948805b35009593a823967f85ae9f
committed file SHA-256:     e1e19d17faf46e76460f43f1ccdd3cb0e32e6aa0341f582adbb72dab20db24e6
committed artifact bytes:   9,840
```

All identities are domain-separated and deterministic. The strict frozen Pydantic contracts reject
unknown fields, reordering, altered lineage, authority upgrades, positive-rights claims, and hash or
manifest drift.

## Persistence and security boundary

The generator accepts only `--confirm-public-terms-rights-review-only` and writes canonical bytes to
stdout. The verifier accepts only `--review PATH`, reads one bounded local regular canonical JSON
file, and emits a sanitized receipt. Both install network and subprocess audit denial before loading
the Phase 23 domain. Invalid invocations and artifacts exit 2 with no stdout and one generic stderr
line. The expected blocked artifact exits 0 because `BLOCKED` is the truthful result.

Phase 23 adds no migration, dependency, database access, row, API route, OpenAPI change, generated
contract, Compose service, provider adapter, worker, scheduler, queue, UI control, snapshot update,
research path, strategy parameter, risk mutation, broker path, paper order, or live path. Alembic
remains at `0011_phase14`, and all 57 inherited tables/functions remain byte-identical.

## Acceptance and stop condition

Acceptance requires repeated byte-identical generation, committed-file parity, strict model and
manifest validation, exact Phase 22 lineage, the 3/1/4 source/finding/requirement counts, the blocked
rights result, all authority boundaries false, offline operation, zero database writes or schema
drift, unchanged inherited behavior, and clean Windows and Ubuntu Phase 23 gates at one committed
SHA/tree.

Stop after Phase 23. Do not begin Phase 24; contact a provider or counsel; use a login, credential,
subscription, entitlement, or account; request or download data; persist a provider payload;
perform data fitness or BLS reconciliation; select an operational composition; define a policy or
holdout; execute research; compute performance; promote a strategy; mutate risk/governance; submit
or reconcile an order; or add a live capability without separate authorization.
