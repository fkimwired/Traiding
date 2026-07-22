[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $PreflightOutput,

    [Parameter(Mandatory = $true)]
    [string] $EvidenceOutput,

    [switch] $ConfirmCredentialedProbe
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$failureMessage = "Paper smoke harness failed."
$mockFallbackMessage = "Mock fallback: MOCK_PROOF_COMPLETE proves the local contract only."
$keyName = "FABLE5_ALPACA_PAPER_API_KEY_ID"
$secretName = "FABLE5_ALPACA_PAPER_SECRET_KEY"
$keyPresent = Test-Path -LiteralPath ("Env:" + $keyName)
$secretPresent = Test-Path -LiteralPath ("Env:" + $secretName)

if ($ConfirmCredentialedProbe.IsPresent -and -not ($keyPresent -and $secretPresent)) {
    [Console]::Error.WriteLine($failureMessage)
    exit 2
}

$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"
$preflightScript = Join-Path $root "scripts\preflight_paper_smoke.py"
$captureScript = Join-Path $root "scripts\capture_paper_shadow_readiness.py"
$reportScript = Join-Path $root "scripts\report_paper_shadow_readiness.py"
$locationPushed = $false
$result = 0

try {
    $preflightOutputPath = [IO.Path]::GetFullPath($PreflightOutput)
    $evidenceOutputPath = [IO.Path]::GetFullPath($EvidenceOutput)
    if ($preflightOutputPath -eq $evidenceOutputPath) {
        throw [InvalidOperationException]::new("Output paths must be distinct.")
    }
    foreach ($requiredPath in @($python, $preflightScript, $captureScript, $reportScript)) {
        if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
            throw [IO.FileNotFoundException]::new("Required local command is unavailable.")
        }
    }

    Push-Location -LiteralPath $root
    $locationPushed = $true

    $preflightLines = @(
        & $python $preflightScript "--output" $preflightOutputPath 2>$null
    )
    $preflightExit = $LASTEXITCODE
    if ($preflightExit -ne 0) {
        throw [InvalidOperationException]::new("Preflight step failed.")
    }
    if (
        -not (Test-Path -LiteralPath $preflightOutputPath -PathType Leaf) -or
        (Get-Item -LiteralPath $preflightOutputPath).Length -le 0
    ) {
        throw [InvalidOperationException]::new("Preflight evidence is unavailable.")
    }
    $preflight = Get-Content -Raw -LiteralPath $preflightOutputPath | ConvertFrom-Json
    $preflightId = [Guid]::Empty
    if (
        $preflight.overall_status -ne "PASS" -or
        $preflight.execution_mode -ne "paper" -or
        $preflight.simulated_paper_only -ne $true -or
        $preflight.mock_readiness -ne "MOCK_PROOF_COMPLETE" -or
        $preflight.checks.Count -ne 7 -or
        $preflight.git_sha -notmatch "^[0-9a-f]{40}$" -or
        $preflight.generated_at_utc -notmatch "Z$" -or
        $preflight.config_sha256 -notmatch "^[0-9a-f]{64}$" -or
        $preflight.report_sha256 -notmatch "^[0-9a-f]{64}$" -or
        $null -ne $preflight.random_seed -or
        $null -ne $preflight.trial_count -or
        -not [Guid]::TryParse(
            [string] $preflight.mock_readiness_assessment_id,
            [ref] $preflightId
        )
    ) {
        throw [InvalidOperationException]::new("Preflight evidence is invalid.")
    }

    $assessmentId = $preflightId.ToString()
    if ($ConfirmCredentialedProbe.IsPresent) {
        $probeKey = "phase12-t004-" + [DateTimeOffset]::UtcNow.ToString(
            "yyyyMMddTHHmmssffffffZ",
            [Globalization.CultureInfo]::InvariantCulture
        )
        $captureLines = @(
            & $python $captureScript `
                "--idempotency-key" $probeKey `
                "--confirm-paper-only-readiness" 2>$null
        )
        $captureExit = $LASTEXITCODE
        if ($captureExit -ne 0) {
            throw [InvalidOperationException]::new("Credentialed step failed.")
        }
        $capture = ($captureLines -join [Environment]::NewLine) | ConvertFrom-Json
        $captureId = [Guid]::Empty
        if (
            $capture.outcome -notmatch "^(SHADOW_READY|BLOCKED)$" -or
            $capture.checks.Count -ne 8 -or
            $capture.strategy_execution_eligible -ne $false -or
            $capture.live_path_absent -ne $true -or
            $capture.no_personalized_investment_advice -ne $true -or
            $capture.no_real_performance_claimed -ne $true -or
            -not [Guid]::TryParse(
                [string] $capture.readiness_assessment_id,
                [ref] $captureId
            )
        ) {
            throw [InvalidOperationException]::new("Credentialed evidence is invalid.")
        }
        $assessmentId = $captureId.ToString()
    }
    else {
        [Console]::Out.WriteLine($mockFallbackMessage)
    }

    $renderedAtUtc = [DateTimeOffset]::UtcNow.ToUniversalTime().ToString(
        "yyyy-MM-ddTHH:mm:ss.ffffffZ",
        [Globalization.CultureInfo]::InvariantCulture
    )
    $reportLines = @(
        & $python $reportScript `
            "--assessment-id" $assessmentId `
            "--rendered-at-utc" $renderedAtUtc `
            "--output" $evidenceOutputPath 2>$null
    )
    $reportExit = $LASTEXITCODE
    if ($reportExit -ne 0) {
        throw [InvalidOperationException]::new("Report step failed.")
    }
    if (
        -not (Test-Path -LiteralPath $evidenceOutputPath -PathType Leaf) -or
        (Get-Item -LiteralPath $evidenceOutputPath).Length -le 0
    ) {
        throw [InvalidOperationException]::new("Report evidence is unavailable.")
    }
    $reportText = $reportLines -join [Environment]::NewLine
    $report = $reportText | ConvertFrom-Json
    $reportedId = [Guid]::Empty
    if (
        $report.simulated_paper_only -ne $true -or
        $report.checks.Count -ne 8 -or
        $report.phase12_code_version_git_sha -notmatch "^[0-9a-f]{40}$" -or
        $report.transport_profile_sha256 -notmatch "^[0-9a-f]{64}$" -or
        $report.rendered_at_utc -ne $renderedAtUtc -or
        $report.strategy_execution_eligible -ne $false -or
        $report.live_path_absent -ne $true -or
        $report.no_personalized_investment_advice -ne $true -or
        $report.no_real_performance_claimed -ne $true -or
        $report.report_sha256 -notmatch "^[0-9a-f]{64}$" -or
        -not [Guid]::TryParse([string] $report.readiness_assessment_id, [ref] $reportedId) -or
        $reportedId -ne [Guid] $assessmentId
    ) {
        throw [InvalidOperationException]::new("Report evidence is invalid.")
    }
    [Console]::Out.WriteLine($reportText)
}
catch {
    [Console]::Error.WriteLine($failureMessage)
    $result = 2
}
finally {
    if ($locationPushed) {
        Pop-Location
    }
}

exit $result
