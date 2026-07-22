# Phase 26 — Family A operational data-composition decision

## Decision

Phase 26 records one exact, closed operational composition for Family A:
`FAMILY_A_CRSP_SEC_RTDSM_V1`. The explicit human decision, single-composition, complete-assignment,
and independent decision-evidence gates pass. This resolves the missing composition identified in
Phase 21.

The selection-evidence hash binds the requesting human's authorization outside the generated
artifact to the exact composition fields; a commit, artifact identity, or model-authored default is
not used as substitute decision evidence. `REQUESTING_REPOSITORY_OWNER` is the stable,
privacy-preserving accountable identity recorded for this repository-scoped decision.

The domain outcome remains `BLOCKED`, with aggregate conclusion
`COMPOSITION_SELECTED_ACQUISITION_BLOCKED_PENDING_RIGHTS_AND_QUALIFICATION`. Selection is not a
rights grant, entitlement, schema qualification, data-acquisition authority, adapter activation,
research run, performance result, or order authority.

## Exact composition

| Capability | Selected operational product | Exact target delivery |
|---|---|---|
| `security_master` | Morningstar CRSP U.S. Stock Databases | Linux flat file |
| `universe_membership` | Morningstar CRSP U.S. Stock Databases | Linux flat file |
| `ohlcv` | Morningstar CRSP U.S. Stock Databases | Linux flat file |
| `corporate_actions` | Morningstar CRSP U.S. Stock Databases | Linux flat file |
| `delistings` | Morningstar CRSP U.S. Stock Databases | Linux flat file |
| `as_reported_fundamentals` | SEC EDGAR Submissions and XBRL Data APIs | Nightly submissions and companyfacts bulk archives |
| `macro_regime_inputs` | Philadelphia Fed RTDSM | PCPI monthly-vintage workbook |

CRSP is selected for the equity spine because permanent identifiers, inactive securities,
historical membership, actions, and delistings are required to prevent survivorship defects. SEC
EDGAR is selected for as-filed fundamentals because it avoids duplicating paid Compustat coverage
and preserves filing availability for later point-in-time qualification. RTDSM PCPI is selected as
the bounded macro-vintage input already reviewed in Phases 22–25; its vintage labels still require
exact BLS release-time reconciliation.

Tiingo, CRSP/Compustat Merged, FRED, LSEG, Yahoo, and yfinance are not selected by this composition.
They remain candidate, rejected-for-this-composition, or architectural-reference surfaces according
to the accepted evidence. This is not a claim that they are categorically unavailable.

## Rights and acquisition boundary

The exact composition creates three mandatory post-selection dependencies:

1. Verify current executed CRSP use rights and the exact Linux delivery entitlement, obtain an
   authenticated RTDSM exact-scope rights response, and revalidate SEC fair-access/reuse policy.
2. Qualify exact delivery bytes and freeze provider schema versions.
3. Prove point-in-time coverage, calendars, filing/release availability, revision behavior, and
   missingness.

Until all three pass, no credential may be loaded and no provider observation may be requested,
downloaded, stored, normalized, or ingested. Phase 25's missing RTDSM response remains a real blocker;
Phase 26 does not reinterpret public research-use language as operational permission.

## Audit identity

- Accepted Phase 25 commit: `4d70b823947fd61d0ea17df14c9f1ff9f93fd45b`
- Accepted Phase 25 tree: `84426ba04f4dbb686878852357410880327b5713`
- Phase 25 artifact SHA-256: `5bc60a4067b3b802ea9ab3063c42d71143dabc3d303d0cff40c05d813b698a9c`
- Phase 26 artifact ID: `3697996f-5ff7-5c14-b0af-db105b83ec30`
- Phase 26 artifact SHA-256: `ffa06ce79fa249c8d6e46f730c737160d052ee2a02a74465ba34a9b4aa8775a9`
- Selection-evidence SHA-256: `6930d8525abafc66b68394de6b6b8ba3d79209916b3e4dee10d3e8a64beee98e`
- Source-snapshot ID: `e81356c5-4833-57a8-9051-cfcfbb181a6d`
- Source-snapshot SHA-256: `c8f7d475deb8be880e61524c1ed1de24b2b0083dedf3d981e550b13eca0a101a`
- Random seed / trial count: `0 / 0`
- UTC decision time: `2026-07-21T20:00:00.000000Z`

## Technical boundary

Phase 26 is deterministic, portable, database-free, and network-disabled. It adds no migration,
table, API route, generated TypeScript contract, dependency, credential loader, provider SDK,
transport, production adapter, scheduler, worker, frontend control, execution path, or live mode.
The only permitted execution mode remains paper, and no order path is added.

## Stop condition

Stop after Phase 26. A later phase requires separate authorization and must address current rights
and exact entitlement for this selected composition before any acquisition implementation. Do not
load a credential, contact a provider, fetch a sample, activate an adapter, create a non-synthetic
snapshot, run research, compute performance, promote a strategy, change risk, or submit an order.
