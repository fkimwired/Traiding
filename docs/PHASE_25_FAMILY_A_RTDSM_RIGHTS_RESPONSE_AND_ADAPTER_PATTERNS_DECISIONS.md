# Phase 25 — RTDSM rights-response evidence intake and adapter-pattern feasibility

## Decision

Phase 25 is an evidence-intake and feasibility package only. The canonical outcome is `BLOCKED / RIGHTS_RESPONSE_EVIDENCE_MISSING` because no authenticated RTDSM clarification response or independently verified authority and exact-scope evidence was supplied. It selects no operational provider, grants no data rights, activates no adapter, and acquires no observations.

A later evaluated response can produce `PASS` only when every authority field, every one of the ten Phase 24 questions, and every exact-scope field is independently verified and mutually consistent. Even then, the determination is `RIGHTS_RESPONSE_VERIFIED_REQUIRES_SEPARATE_ACQUISITION_AUTHORITY`; Phase 25 itself never authorizes acquisition.

Requester authority is personal. It is not PwC authority or sponsorship and is not rights evidence from the Philadelphia Fed, BLS, Yahoo, an exchange, or any other provider. Employment, title, repository ownership, commits, PR approval, credential possession, and successful retrieval are expressly excluded as provider-rights evidence.

## Accepted lineage and preservation

- Accepted Phase 24 merge: `145f67f188befae46443d061d029c243858841b4`
- Accepted merge tree: `27392b6eb3239e01e533d07d42d164124fb7aa18`
- Accepted Phase 24 implementation: `c1dad09f08b18a5a7d527579ca677633b49184fb`
- Phase 24 artifact ID: `c7653056-2f58-5137-bc7a-29ea0e7b85a9`
- Phase 24 embedded artifact SHA-256: `936abe1205d9cc9fb956f7ae1577275062daa544b2a1361f9891b47029e93a52`
- Phase 24 artifact file SHA-256: `5ad6b7b8e5c60fa1b2e76445b11ef0428d68515dd97439e6b21fc487aea91417`

The merge and implementation have the same tree, the merge is an ancestor of Phase 25, and the Phase 24 artifact is checked byte-for-byte against the accepted merge.

## Strict evidence intake

The Pydantic intake accepts allowlisted metadata, not provider bodies or credentials. Authority evidence records:

- responder organization, stable identity, role, and verified basis of authority;
- rights-holding legal entity;
- UTC response and effective dates, plus expiry or an explicit no-expiry reason;
- governing agreement and terms version;
- immutable evidence ID and SHA-256;
- authenticated provenance type and hashed locator;
- independent verification status and hashed verifier identity; and
- explicit authentication of the responder identity and verification of the authority basis.

`EMAIL_ONLY`, `PUBLIC_WEBPAGE_ONLY`, `VERBAL_STATEMENT`, and `SCREENSHOT_ONLY` can be recorded but can never make authority verified. An account or entitlement is represented only by the normalized token `SANITIZED_HASH_ONLY` plus a SHA-256; raw identifiers are rejected. Unknown fields are rejected. The generator additionally rejects body, payload, credential, password, secret, cookie, crumb, raw-response, raw-account, and raw-entitlement key families before model validation.

Mutual consistency is a separate aggregate gate. A response must record `mutual_consistency_status=VERIFIED` and cite at least one independently verified immutable authority-evidence ID. `FAILED`, `UNVERIFIED`, a missing reference, or a reference to unverified authority evidence blocks the aggregate even when every individual question and scope row claims `PASS`.

## Phase 24 question evaluation

No response evidence was supplied, so every field is truthfully `MISSING` with no evidence ID and `satisfied=false`.

| # | Code | State | Phase 24 field |
|---:|---|---|---|
| 1 | `PERSISTENT_STORAGE` | `MISSING` | `persistent_storage` |
| 2 | `AUTOMATED_MODEL_INTERNAL_USE` | `MISSING` | `automated_model_internal_use` |
| 3 | `DERIVED_DATA_AND_MODEL_ARTIFACTS` | `MISSING` | `derived_data` |
| 4 | `RETENTION_DELETION` | `MISSING` | `retention_deletion` |
| 5 | `REDISTRIBUTION_AND_DISPLAY` | `MISSING` | `redistribution` |
| 6 | `ATTRIBUTION` | `MISSING` | `attribution` |
| 7 | `THIRD_PARTY_BLS_CONTENT` | `MISSING` | `third_party_content` |
| 8 | `AUTOMATED_ACCESS_AND_LOAD` | `MISSING` | `access_load` |
| 9 | `REVOCATION_AND_CURRENTNESS` | `MISSING` | `revocation_currentness` |
| 10 | `AUTHORITY_AND_PRODUCT_SCOPE` | `MISSING` | `operational_use_cleared` |

The artifact preserves the full wording of all ten questions. Evaluated states are exactly `PASS`, `FAIL`, `CONDITIONAL`, or `MISSING`, and every state carries evidence IDs where applicable. A `CONDITIONAL` field satisfies only if every condition has an enforceable control ID, acceptance-test ID, `enforceable=true`, and `acceptance_test_passed=true`.

## Exact-scope evaluation

All nineteen required scope elements are independently represented: product; requested series; PCPI and other BLS origin; delivery method and surface; individual licensed party; hashed account or entitlement; users and devices; local development, test, and simulated paper environments; access frequency/concurrency/rate/bulk limits; raw storage; immutable snapshots; backups; normalization and point-in-time transformation; internal feature/model/backtest/paper-simulation uses; derived artifacts; display/export/sharing/publication/redistribution; attribution; retention/deletion/termination; and revocation/revalidation. Every canonical field is `MISSING` and unsatisfied.

Positive product scope must equal `Federal Reserve Bank of Philadelphia Real-Time Data Set for Macroeconomists (RTDSM)`. Positive licensed-party scope must equal `INDIVIDUAL_ACCOUNT_HOLDER`. Missing, conflicting, unsupported, or uncontrolled conditional scope keeps the aggregate blocked.

## Research method and source snapshot

Network access was used only for an explicit metadata/documentation research step on 2026-07-21 UTC. Four maintained public repositories were inspected at immutable commits and six official documents were captured only as content hashes. No RTDSM or Yahoo observation file, response body fixture, credential, entitlement, or provider SDK was persisted. Generation, verification, tests, and runtime remain network-disabled.

| Source | Exact revision | License / terms | Principal finding and limitation |
|---|---|---|---|
| [yfinance](https://github.com/ranaroussi/yfinance) | `38c73ce33fb1ee77d37a0998c95c06e60356298e` | Apache-2.0 software | Shared session/cookie/crumb owner, finite timeout, typed rate-limit error, caches, timezone and action handling. README warns it is unaffiliated and personal-use oriented. Apache-2.0 does not grant Yahoo data rights. |
| [OpenBB](https://github.com/OpenBB-finance/OpenBB) | `3e071fcc2cd9f891cac6040ae60296dba76dab46` | AGPL-3.0-only | Strong query/extract/transform provider lifecycle, Pydantic boundaries, secret filtering, and scrubbed VCR tests. Transport guarantees vary by provider; AGPL and provider-data rights remain separate. |
| [FinRobot](https://github.com/AI4Finance-Foundation/FinRobot) | `297a8d28d099be328c8a8eb658b4f782b93f3651` | Apache-2.0 | Useful anti-pattern inventory: global clients/credentials, unbounded requests, mixed schemas, local caches, and error/URL leakage risks. No production design was copied. |
| [TradingAgents](https://github.com/TauricResearch/TradingAgents) | `a33fd4c0f134485a43553a2c23a63cb14adbd88f` | Apache-2.0 | Typed data-routing errors, finite timeouts, rate-limit backoff, normalization, cache-freshness tests. Data plumbing only was studied; LLM trade decisions, sizes, and orders are rejected. |
| [Philadelphia Fed RTDSM page](https://www.philadelphiafed.org/surveys-and-data/real-time-data-research/real-time-data-set-for-macroeconomists) | SHA-256 `fd2215999b11ecd106ea634a511261e61a8451082fee5bbb74ce779e84ba7cb6` | Provider content, license unspecified | Official product/vintage/file documentation; not an authenticated exact-scope rights grant. |
| [Philadelphia Fed online terms](https://www.philadelphiafed.org/about-us/privacy-notice) | SHA-256 `acde615dcde889dd1f848242a982c816ceaf92344f6afeba33bf356d33813a98` | Provider content, license unspecified | Research-use language and third-party-content warning do not resolve automation, storage, or BLS rights. |
| [PCPI documentation](https://www.philadelphiafed.org/-/media/FRBP/Assets/Surveys-And-Data/real-time-data/data-files/PCPI/Specific_Documentation_PCPI.pdf) | SHA-256 `e843206d329ff0913580f5fe2161089a593b1b4cd4f0612dbaa852b2dc67acde` | Provider content, license unspecified | Confirms BLS origin and revision behavior; does not establish upstream rights coverage. |
| [Release-value documentation](https://www.philadelphiafed.org/-/media/frbp/assets/surveys-and-data/real-time-data/data-files/documentation/documentation_first_second_third_release_values.pdf) | SHA-256 `306460c8403545c57761e2c88d0957b2e78ae42bb5187bd20d4cf8d388b1be7f` | Provider content, license unspecified | Documents vintages and revisions; does not grant operational use rights. |
| [Yahoo API terms](https://legal.yahoo.com/us/en/yahoo/terms/product-atos/apiforydn/index.html) | SHA-256 `f88226275015c97165d3856db07402eb45f5f86d63e4e95a18e5c5248c1c2f1b` | Proprietary terms | General API terms do not establish a current Yahoo Finance market-data entitlement for the exact use. |
| [Yahoo general terms](https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html) | SHA-256 `8e2e79ccae307771e43be015f98965e28561a9066cd23d3c70057513babc5c54` | Proprietary terms | General personal/revocable service terms do not establish storage, modeling, backtest, or redistribution rights. |

The canonical source registry preserves, for every row, URL and revision; license; provider abstraction; request/session ownership; timeout, retry, backoff and rate-limit behavior; schema validation/normalization; timestamp/timezone handling; actions or revisions; caching/persistence; error sanitization; deterministic tests; rights warnings; inspected paths; and unresolved limitations. Repository license file paths and blob object IDs are also hash-bound.

## Provider-neutral pattern inventory

The package documents eleven patterns, all `DOCUMENTED_NOT_IMPLEMENTED`: provider-neutral fetcher lifecycle; call-scoped transport ownership; bounded timeout/retry/rate limit; strict boundary schema; UTC availability and source time; raw/normalized/revision separation; rights-gated cache/snapshot; sanitized error/evidence boundary; offline synthetic contract tests; LLM non-alpha boundary; and Yahoo disabled until verified.

These are attributed architectural observations or independent-reimplementation requirements, not copied production code. OpenBB-derived ideas require an explicit AGPL analysis if adapted. TradingAgents and FinRobot are never authority for LLM trade decisions: this repository continues to prohibit any LLM trade instruction, position size, or order.

## Yahoo/yfinance decision

`yfinance` remains an architectural reference and possible later personal-use candidate only. It is not a dependency, runtime import, strategy import, approved provider, authoritative data source, or rights proof. Yahoo exact current terms, Finance product surface, account entitlement, intended-use rights, persistence, derived use, rate limits, attribution, retention, and continued availability were not independently verified. The artifact therefore records `yahoo_rights_state=RIGHTS_UNVERIFIED`, `yfinance_dependency_added=false`, and `production_adapter_activated=false`.

## Fail-closed transition

Any missing or ambiguous authority; any unverified evidence reference; any `FAIL` or `MISSING`; any uncontrolled condition; or any change to terms, product, series, delivery, party, entitlement, users, use, rights holder, expiry, or revocation blocks the result. A positive evidence evaluation only permits a later acquisition proposal. It does not download, store, ingest, research, backtest, select, promote, change risk, submit a paper order, or authorize execution.

Stop after Phase 25. Phase 26 requires separate authorization.
