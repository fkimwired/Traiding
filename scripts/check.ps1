$ErrorActionPreference = "Stop"
$Python = if (Test-Path ".venv\Scripts\python.exe") { ".venv\Scripts\python.exe" } else { "python" }

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
& $Python scripts/verify_phase1.py --static-only --phase 4
exit $LASTEXITCODE
