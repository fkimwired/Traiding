# Phase 26 handoff

## Outcome

Phase 26 selects the exact Family A operational composition
`FAMILY_A_CRSP_SEC_RTDSM_V1`: CRSP U.S. Stock Databases for the point-in-time equity spine, SEC EDGAR
nightly bulk archives for as-filed fundamentals, and Philadelphia Fed RTDSM PCPI monthly vintages for
macro-regime input.

The composition decision itself is complete. The truthful overall result is still:

```text
outcome:              BLOCKED
decision_state:       OPERATIONAL_COMPOSITION_SELECTED
aggregate_conclusion: COMPOSITION_SELECTED_ACQUISITION_BLOCKED_PENDING_RIGHTS_AND_QUALIFICATION
```

No provider observation was requested or persisted, no credential was loaded, and no adapter,
research, performance, execution, order, or live surface was added.

## Acceptance commands

```powershell
.venv\Scripts\python.exe -m pytest services/data/tests/test_phase26_composition.py tests/test_phase26_portable.py
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m ruff format --check .
.venv\Scripts\python.exe -m mypy
.venv\Scripts\python.exe scripts/verify_phase1.py --static-only --phase 26
```

Canonical generation and verification:

```powershell
.venv\Scripts\python.exe scripts/generate_family_a_operational_data_composition_decision.py --confirm-operational-composition-decision-only
.venv\Scripts\python.exe scripts/verify_family_a_operational_data_composition_decision.py --artifact docs/PHASE_26_FAMILY_A_OPERATIONAL_DATA_COMPOSITION_DECISION.json
```

## Next blocker

Current rights and entitlement are now evaluated against a closed scope rather than a candidate
inventory: CRSP Linux flat-file entitlement, RTDSM exact-scope rights, and SEC policy currentness.
After rights pass, exact schema and point-in-time qualification still remain separate gates.

Stop after Phase 26. Phase 27 requires separate authorization.
