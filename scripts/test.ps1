$ErrorActionPreference = "Stop"
$Python = if (Test-Path ".venv\Scripts\python.exe") { ".venv\Scripts\python.exe" } else { "python" }

& $Python -m pytest
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

npm test
exit $LASTEXITCODE

