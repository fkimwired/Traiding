from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fable5_data.phase16.plan import canonical_source_plan_bytes

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "scripts/generate_family_a_point_in_time_source_plan.py"
VERIFIER = ROOT / "scripts/verify_family_a_point_in_time_source_plan.py"
GENERATOR_FAILURE = b"Family A point-in-time source-plan generation failed.\n"
VERIFIER_FAILURE = b"Family A point-in-time source-plan verification failed.\n"


def _run(*arguments: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run([sys.executable, *arguments], cwd=ROOT, capture_output=True, check=False)


def test_generator_is_repeatable_and_matches_canonical_builder() -> None:
    first = _run(str(GENERATOR), "--confirm-plan-only")
    second = _run(str(GENERATOR), "--confirm-plan-only")

    assert first.returncode == second.returncode == 0
    assert first.stderr == second.stderr == b""
    assert first.stdout == second.stdout == canonical_source_plan_bytes()


def test_offline_verifier_accepts_generated_plan_repeatably(tmp_path: Path) -> None:
    candidate = tmp_path / "plan.json"
    candidate.write_bytes(canonical_source_plan_bytes())

    first = _run(str(VERIFIER), "--plan", str(candidate))
    second = _run(str(VERIFIER), "--plan", str(candidate))

    assert first.returncode == second.returncode == 0
    assert first.stderr == second.stderr == b""
    assert first.stdout == second.stdout
    assert json.loads(first.stdout) == {
        "artifact_id": "e106a766-5cfe-5a1c-94f6-ee1c2ac68652",
        "artifact_sha256": "74ddf4a51d722b494fd494241e2e5927bff6fde034f6932dcfd791bb3a0706bb",
        "network": "disabled",
        "outcome": "PLAN_FROZEN",
        "schema_version": "phase16-family-a-point-in-time-source-plan-v1",
        "status": "valid",
    }


@pytest.mark.parametrize(
    ("collection", "field", "value"),
    [
        ("requirements", "definition", "forged definition"),
        ("capabilities", "source_selected", True),
        ("candidates", "selected", True),
        ("candidates", "state", "MISSING"),
        ("future_steps", "state", "COMPLETE"),
        ("phase15_gap_bindings", "state", "PRESENT"),
    ],
)
def test_verifier_rejects_row_tamper(
    tmp_path: Path, collection: str, field: str, value: object
) -> None:
    payload = json.loads(canonical_source_plan_bytes())
    payload[collection][0][field] = value
    candidate = tmp_path / "tampered.json"
    candidate.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    result = _run(str(VERIFIER), "--plan", str(candidate))
    assert result.returncode == 2
    assert result.stdout == b""
    assert result.stderr == VERIFIER_FAILURE


def test_verifier_rejects_duplicate_keys_bom_floats_and_noncanonical_json(tmp_path: Path) -> None:
    original = canonical_source_plan_bytes()
    candidates = (
        b'{"schema_version":"forged",' + original[1:],
        b"\xef\xbb\xbf" + original,
        b'{"forged":1.5,' + original[1:],
        json.dumps(json.loads(original), sort_keys=True, indent=2).encode() + b"\n",
    )
    for index, raw in enumerate(candidates):
        candidate = tmp_path / f"invalid-{index}.json"
        candidate.write_bytes(raw)
        result = _run(str(VERIFIER), "--plan", str(candidate))
        assert result.returncode == 2
        assert result.stdout == b""
        assert result.stderr == VERIFIER_FAILURE


def test_verifier_rejects_symlink_and_directory(tmp_path: Path) -> None:
    target = tmp_path / "target.json"
    target.write_bytes(canonical_source_plan_bytes())
    directory = tmp_path / "directory"
    directory.mkdir()
    assert _run(str(VERIFIER), "--plan", str(directory)).returncode == 2

    link = tmp_path / "link.json"
    try:
        os.symlink(target, link)
    except OSError:
        pytest.skip("symlink creation is unavailable on this host")
    assert _run(str(VERIFIER), "--plan", str(link)).returncode == 2


def test_clis_reject_missing_extra_and_forbidden_arguments_without_echoing_canary() -> None:
    canary = "phase16-secret-canary-do-not-emit"
    results = (
        (_run(str(GENERATOR)), GENERATOR_FAILURE),
        (_run(str(GENERATOR), "--confirm-plan-only", "--provider", canary), GENERATOR_FAILURE),
        (_run(str(VERIFIER), "--plan", canary, "--repair"), VERIFIER_FAILURE),
    )
    for result, failure in results:
        assert result.returncode == 2
        assert result.stdout == b""
        assert result.stderr == failure
        assert canary.encode() not in result.stderr
