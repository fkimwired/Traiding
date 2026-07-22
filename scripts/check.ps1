$ErrorActionPreference = "Stop"
$Python = if (Test-Path ".venv\Scripts\python.exe") { ".venv\Scripts\python.exe" } else { "python" }
$VerifyPhase = if ($env:FABLE5_VERIFY_PHASE) { $env:FABLE5_VERIFY_PHASE } else { "26" }

if ($VerifyPhase -notmatch "^(?:[1-9]|10|11|12|13|14|15|16|17|18|19|20|21|22|23|24|25|26)$") {
    Write-Host "FABLE5_VERIFY_PHASE must be one of 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, or 26."
    exit 2
}

& $Python -m ruff check .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $Python -m ruff format --check .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $Python -m mypy
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
npm run lint
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
npm run typecheck
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $Python scripts/export_openapi.py --check
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
npm run check --workspace @fable5/contracts
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $Python scripts/verify_phase1.py --static-only --phase $VerifyPhase
exit $LASTEXITCODE
