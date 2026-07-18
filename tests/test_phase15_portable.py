from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPECIFICATION = ROOT / "docs/PHASE_15_FAMILY_A_RESEARCH_ADMISSION_SPECIFICATION.json"
GENERATOR = ROOT / "scripts/generate_family_a_research_admission_specification.py"
VERIFIER = ROOT / "scripts/verify_family_a_research_admission_specification.py"


def _run(*arguments: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [sys.executable, *arguments],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )


def test_committed_specification_is_exact_generator_output() -> None:
    generated = _run(str(GENERATOR), "--confirm-requirements-only")

    assert generated.returncode == 0
    assert generated.stderr == b""
    assert generated.stdout == SPECIFICATION.read_bytes()


def test_offline_verifier_accepts_committed_specification_repeatably() -> None:
    first = _run(str(VERIFIER), "--specification", str(SPECIFICATION))
    second = _run(str(VERIFIER), "--specification", str(SPECIFICATION))

    assert first.returncode == second.returncode == 0
    assert first.stderr == second.stderr == b""
    assert first.stdout == second.stdout
    result = json.loads(first.stdout)
    assert result == {
        "artifact_id": "c29b8139-da80-556b-b150-a5ca9603d265",
        "artifact_sha256": "575ce4c51e9102790d75edc4a330c3e9f1d9eb505eb33ccf22d8a9c9e50200d6",
        "network": "disabled",
        "outcome": "REQUIREMENTS_FROZEN",
        "schema_version": "phase15-family-a-research-admission-specification-v1",
        "status": "valid",
    }


@pytest.mark.parametrize(
    ("collection", "field", "value"),
    [
        ("requirements", "definition", "forged definition"),
        ("requirements", "status", "BLOCKED"),
        ("gaps", "state", "PRESENT"),
        ("gaps", "summary", "forged summary"),
        ("gaps", "evidence_refs", ["docs/forged.md#forged"]),
    ],
)
def test_verifier_rejects_row_tamper(
    tmp_path: Path,
    collection: str,
    field: str,
    value: object,
) -> None:
    payload = json.loads(SPECIFICATION.read_bytes())
    payload[collection][0][field] = value
    candidate = tmp_path / "tampered.json"
    candidate.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    result = _run(str(VERIFIER), "--specification", str(candidate))

    assert result.returncode == 2
    assert result.stdout == b""
    assert result.stderr == b"Family A research-admission specification verification failed.\n"


def test_verifier_rejects_duplicate_keys_bom_and_noncanonical_json(tmp_path: Path) -> None:
    original = SPECIFICATION.read_bytes()
    candidates = (
        b'{"schema_version":"forged",' + original[1:],
        b"\xef\xbb\xbf" + original,
        json.dumps(json.loads(original), sort_keys=True, indent=2).encode() + b"\n",
    )
    for index, raw in enumerate(candidates):
        candidate = tmp_path / f"invalid-{index}.json"
        candidate.write_bytes(raw)
        result = _run(str(VERIFIER), "--specification", str(candidate))
        assert result.returncode == 2
        assert result.stdout == b""


def test_clis_reject_extra_or_missing_arguments_without_echoing_canary() -> None:
    canary = "phase15-secret-canary-do-not-emit"
    generator = _run(
        str(GENERATOR),
        "--confirm-requirements-only",
        "--provider",
        canary,
    )
    verifier = _run(str(VERIFIER), "--specification", canary, "--extra")

    for result, message in (
        (generator, b"Family A research-admission specification generation failed.\n"),
        (verifier, b"Family A research-admission specification verification failed.\n"),
    ):
        assert result.returncode == 2
        assert result.stdout == b""
        assert result.stderr == message
        assert canary.encode() not in result.stderr
