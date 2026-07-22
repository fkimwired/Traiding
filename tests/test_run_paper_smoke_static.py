from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Final

import pytest

ROOT: Final = Path(__file__).resolve().parents[1]
SCRIPT_PATH: Final = ROOT / "scripts" / "run_paper_smoke.ps1"
PYTHON_LAUNCHER: Final = ROOT / ".venv" / "Scripts" / "python.exe"
PYVENV_CONFIG: Final = ROOT / ".venv" / "pyvenv.cfg"

FIXED_FALLBACK_LINE: Final = "Mock fallback: MOCK_PROOF_COMPLETE proves the local contract only."
MOCK_ASSESSMENT_ID: Final = "55934e08-c4a2-548d-b9cd-13a1c824211b"
KEY_ENV_NAME: Final = "FABLE5_ALPACA_PAPER_API_KEY_ID"
SECRET_ENV_NAME: Final = "FABLE5_ALPACA_PAPER_SECRET_KEY"
KEY_CANARY: Final = "CANARY_KEY_9f3"
SECRET_CANARY: Final = "CANARY_SECRET_7c1"

_STUB_SOURCE: Final = r"""from __future__ import annotations

import json
import os
import sys
from pathlib import Path

MOCK_ASSESSMENT_ID = "55934e08-c4a2-548d-b9cd-13a1c824211b"
EXTERNAL_ASSESSMENT_ID = "e739e342-d757-51c7-99c2-75f76a7a113a"


def option_value(name: str) -> str:
    try:
        index = sys.argv.index(name)
        value = sys.argv[index + 1]
    except (IndexError, ValueError):
        raise SystemExit(91) from None
    return value


script_name = Path(__file__).name
log_path = Path(os.environ["FABLE5_SMOKE_STUB_LOG"])
log_path.parent.mkdir(parents=True, exist_ok=True)
with log_path.open("a", encoding="utf-8", newline="\n") as handle:
    handle.write(json.dumps({"script": script_name, "argv": sys.argv[1:]}) + "\n")

if script_name == "preflight_paper_smoke.py":
    exit_code = int(os.environ.get("FABLE5_STUB_PREFLIGHT_EXIT", "0"))
    payload = {
        "schema_version": "fable5-paper-smoke-preflight-v1",
        "generated_at_utc": "2026-07-22T14:30:00.000000Z",
        "git_sha": "c11e899a25732b49d9d7b3a95e2d12c4b6eff215",
        "git_dirty": True,
        "execution_mode": "paper",
        "simulated_paper_only": True,
        "config_sha256": "1" * 64,
        "random_seed": None,
        "trial_count": None,
        "overall_status": "PASS" if exit_code == 0 else "FAIL",
        "mock_readiness": "MOCK_PROOF_COMPLETE",
        "mock_readiness_assessment_id": MOCK_ASSESSMENT_ID,
        "mock_readiness_artifact_sha256": "2" * 64,
        "checks": [{"status": "PASS"} for _ in range(7)],
        "report_sha256": "3" * 64,
    }
    if exit_code == 0:
        output = Path(option_value("--output"))
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    raise SystemExit(exit_code)

if script_name == "capture_paper_shadow_readiness.py":
    exit_code = int(os.environ.get("FABLE5_STUB_CAPTURE_EXIT", "0"))
    print(
        json.dumps(
            {
                "readiness_assessment_id": EXTERNAL_ASSESSMENT_ID,
                "outcome": "SHADOW_READY",
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    raise SystemExit(exit_code)

if script_name == "report_paper_shadow_readiness.py":
    exit_code = int(os.environ.get("FABLE5_STUB_REPORT_EXIT", "0"))
    assessment_id = option_value("--assessment-id")
    rendered_at_utc = option_value("--rendered-at-utc")
    payload = {
        "readiness_assessment_id": assessment_id,
        "rendered_at_utc": rendered_at_utc,
        "simulated_paper_only": True,
        "checks": [{"status": "PASS"} for _ in range(8)],
        "phase12_code_version_git_sha": (
            "c11e899a25732b49d9d7b3a95e2d12c4b6eff215"
        ),
        "transport_profile_sha256": "5" * 64,
        "strategy_execution_eligible": False,
        "live_path_absent": True,
        "no_personalized_investment_advice": True,
        "no_real_performance_claimed": True,
        "report_sha256": "4" * 64,
    }
    if exit_code == 0:
        output = Path(option_value("--output"))
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            "# Simulated / Paper Only / No Advice\n\n"
            f"- Readiness assessment ID: `{assessment_id}`\n"
            f"- Rendered at UTC: `{rendered_at_utc}`\n"
            "- Report SHA-256: `" + "4" * 64 + "`\n",
            encoding="utf-8",
        )
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    raise SystemExit(exit_code)

raise SystemExit(92)
"""


def _source() -> str:
    return SCRIPT_PATH.read_text(encoding="utf-8")


def _powershell() -> str:
    executable = shutil.which("powershell")
    if executable is None:
        pytest.skip("Windows PowerShell is required for the T-004 harness test")
    return executable


def _prepare_stub_root(tmp_path: Path) -> tuple[Path, Path]:
    smoke_root = tmp_path / "paper-smoke-root"
    scripts = smoke_root / "scripts"
    venv_scripts = smoke_root / ".venv" / "Scripts"
    scripts.mkdir(parents=True)
    venv_scripts.mkdir(parents=True)
    shutil.copy2(SCRIPT_PATH, scripts / SCRIPT_PATH.name)
    shutil.copy2(PYTHON_LAUNCHER, venv_scripts / "python.exe")
    shutil.copy2(PYVENV_CONFIG, smoke_root / ".venv" / "pyvenv.cfg")
    for name in (
        "preflight_paper_smoke.py",
        "capture_paper_shadow_readiness.py",
        "report_paper_shadow_readiness.py",
    ):
        (scripts / name).write_text(_STUB_SOURCE, encoding="utf-8")
    return smoke_root, scripts / SCRIPT_PATH.name


def _run_stubbed(
    tmp_path: Path,
    *,
    credentials: tuple[str | None, str | None] = (None, None),
    arguments: tuple[str, ...] = (),
    preflight_exit: int = 0,
    report_exit: int = 0,
) -> tuple[subprocess.CompletedProcess[str], list[dict[str, object]], Path, Path]:
    smoke_root, script = _prepare_stub_root(tmp_path)
    log_path = smoke_root / "stub-calls.jsonl"
    preflight_output = smoke_root / "artifacts" / "preflight.json"
    evidence_output = smoke_root / "artifacts" / "evidence.md"
    environment = os.environ.copy()
    environment.pop(KEY_ENV_NAME, None)
    environment.pop(SECRET_ENV_NAME, None)
    if credentials[0] is not None:
        environment[KEY_ENV_NAME] = credentials[0]
    if credentials[1] is not None:
        environment[SECRET_ENV_NAME] = credentials[1]
    environment.update(
        {
            "FABLE5_SMOKE_STUB_LOG": str(log_path),
            "FABLE5_STUB_PREFLIGHT_EXIT": str(preflight_exit),
            "FABLE5_STUB_REPORT_EXIT": str(report_exit),
        }
    )
    result = subprocess.run(
        [
            _powershell(),
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
            "-PreflightOutput",
            str(preflight_output),
            "-EvidenceOutput",
            str(evidence_output),
            *arguments,
        ],
        cwd=smoke_root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    calls = (
        [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
        if log_path.exists()
        else []
    )
    return result, calls, preflight_output, evidence_output


def _argument_value(arguments: object, name: str) -> str:
    assert isinstance(arguments, list)
    index = arguments.index(name)
    value = arguments[index + 1]
    assert isinstance(value, str)
    return value


def test_script_is_the_only_new_powershell_surface_and_names_existing_clis() -> None:
    source = _source()

    assert SCRIPT_PATH.is_file()
    assert "preflight_paper_smoke.py" in source
    assert "capture_paper_shadow_readiness.py" in source
    assert "report_paper_shadow_readiness.py" in source
    assert "ConfirmCredentialedProbe" in source
    assert "PreflightOutput" in source
    assert "EvidenceOutput" in source
    assert source.count(FIXED_FALLBACK_LINE) == 1


def test_script_is_fail_closed_and_has_no_retry_or_scheduler_surface() -> None:
    source = _source()
    folded = source.casefold()

    assert "set-strictmode" in folded
    assert "$erroractionpreference" in folded
    assert folded.count("$lastexitcode") >= 3
    assert folded.count("-ne 0") >= 3
    assert "exit" in folded
    for exit_variable in ("$preflightexit", "$captureexit", "$reportexit"):
        assert folded.count(exit_variable) >= 2
    assert "phase_26_static" not in folded
    for forbidden in (
        "retry",
        "scheduler",
        "scheduledtask",
        "start-job",
        "register-objectevent",
        "invoke-restmethod",
        "invoke-webrequest",
        "curl",
        "wget",
        "http://",
        "https://",
        "socket",
        "--provider",
        "--url",
        "--symbol",
    ):
        assert forbidden not in folded


def test_script_contains_no_nonpaper_host_or_mutation_literal() -> None:
    source = _source()
    folded = source.casefold()

    assert re.search(r"(?<!paper-)api\.alpaca\.markets", folded) is None
    for forbidden in ("post", "delete", "order", "submit"):
        assert forbidden not in folded


def test_credentials_are_checked_by_name_only_and_values_cannot_be_retrieved() -> None:
    source = _source()
    folded = source.casefold()

    assert KEY_ENV_NAME.casefold() in folded
    assert SECRET_ENV_NAME.casefold() in folded
    assert "test-path" in folded
    for line in source.splitlines():
        if "env:" in line.casefold():
            assert "test-path" in line.casefold()
    for name in (KEY_ENV_NAME, SECRET_ENV_NAME):
        assert re.search(rf"\$env\s*:\s*{re.escape(name)}", source, re.IGNORECASE) is None
        assert (
            re.search(
                rf"getenvironmentvariable\s*\([^\r\n]*{re.escape(name)}",
                source,
                re.IGNORECASE,
            )
            is None
        )
    for forbidden in (
        "getenvironmentvariables",
        "get-childitem env:",
        "get-item env:",
        "write-output env:",
    ):
        assert forbidden not in folded


def test_mock_path_is_one_pass_and_produces_both_reports_without_secret_leak(
    tmp_path: Path,
) -> None:
    result, calls, preflight_output, evidence_output = _run_stubbed(
        tmp_path,
        credentials=(KEY_CANARY, SECRET_CANARY),
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines().count(FIXED_FALLBACK_LINE) == 1
    assert [call["script"] for call in calls] == [
        "preflight_paper_smoke.py",
        "report_paper_shadow_readiness.py",
    ]
    assert preflight_output.is_file()
    assert evidence_output.is_file()
    preflight = json.loads(preflight_output.read_text(encoding="utf-8"))
    assert preflight["mock_readiness"] == "MOCK_PROOF_COMPLETE"
    assert preflight["mock_readiness_assessment_id"] == MOCK_ASSESSMENT_ID

    report_arguments = calls[1]["argv"]
    assert _argument_value(report_arguments, "--assessment-id") == MOCK_ASSESSMENT_ID
    rendered_at_utc = _argument_value(report_arguments, "--rendered-at-utc")
    assert re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z",
        rendered_at_utc,
    )
    assert Path(_argument_value(report_arguments, "--output")) == evidence_output

    rendered = (
        result.stdout
        + result.stderr
        + preflight_output.read_text(encoding="utf-8")
        + evidence_output.read_text(encoding="utf-8")
    )
    assert KEY_CANARY not in rendered
    assert SECRET_CANARY not in rendered


@pytest.mark.parametrize(
    "credentials",
    (
        (None, None),
        (KEY_CANARY, None),
        (None, SECRET_CANARY),
    ),
    ids=("absent-pair", "key-only", "secret-only"),
)
def test_confirm_switch_without_complete_pair_exits_before_any_child(
    tmp_path: Path,
    credentials: tuple[str | None, str | None],
) -> None:
    result, calls, preflight_output, evidence_output = _run_stubbed(
        tmp_path,
        credentials=credentials,
        arguments=("-ConfirmCredentialedProbe",),
    )

    assert result.returncode != 0
    assert calls == []
    assert preflight_output.exists() is False
    assert evidence_output.exists() is False
    rendered = result.stdout + result.stderr
    assert "Traceback" not in rendered
    assert KEY_CANARY not in rendered
    assert SECRET_CANARY not in rendered
    assert KEY_ENV_NAME not in rendered
    assert SECRET_ENV_NAME not in rendered


def test_preflight_nonzero_stops_before_report(tmp_path: Path) -> None:
    result, calls, preflight_output, evidence_output = _run_stubbed(
        tmp_path,
        preflight_exit=17,
    )

    assert result.returncode != 0
    assert [call["script"] for call in calls] == ["preflight_paper_smoke.py"]
    assert preflight_output.exists() is False
    assert evidence_output.exists() is False


def test_report_nonzero_is_propagated(tmp_path: Path) -> None:
    result, calls, preflight_output, evidence_output = _run_stubbed(
        tmp_path,
        report_exit=19,
    )

    assert result.returncode != 0
    assert [call["script"] for call in calls] == [
        "preflight_paper_smoke.py",
        "report_paper_shadow_readiness.py",
    ]
    assert preflight_output.is_file()
    assert evidence_output.exists() is False
