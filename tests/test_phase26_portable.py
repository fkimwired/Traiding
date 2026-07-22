from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fable5_data.phase26.composition import canonical_phase26_decision_bytes

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "scripts/generate_family_a_operational_data_composition_decision.py"
VERIFIER = ROOT / "scripts/verify_family_a_operational_data_composition_decision.py"
ARTIFACT = ROOT / "docs/PHASE_26_FAMILY_A_OPERATIONAL_DATA_COMPOSITION_DECISION.json"
GENERATOR_FAILURE = b"Phase 26 operational data-composition generation failed.\n"
VERIFIER_FAILURE = b"Phase 26 operational data-composition verification failed.\n"


def _run(*arguments: str) -> subprocess.CompletedProcess[bytes]:
    environment = os.environ.copy()
    for name in tuple(environment):
        if any(token in name.upper() for token in ("TOKEN", "SECRET", "PASSWORD", "API_KEY")):
            environment.pop(name, None)
    return subprocess.run(
        [sys.executable, *arguments],
        cwd=ROOT,
        env=environment,
        check=False,
        capture_output=True,
    )


def test_phase26_generator_is_deterministic_and_matches_artifact() -> None:
    arguments = (str(GENERATOR), "--confirm-operational-composition-decision-only")
    first = _run(*arguments)
    second = _run(*arguments)
    assert first.returncode == second.returncode == 0
    assert first.stderr == second.stderr == b""
    assert first.stdout == second.stdout == ARTIFACT.read_bytes()
    assert first.stdout == canonical_phase26_decision_bytes()


def test_phase26_verifier_returns_sanitized_blocked_receipt() -> None:
    result = _run(str(VERIFIER), "--artifact", str(ARTIFACT))
    assert result.returncode == 0 and result.stderr == b""
    receipt = json.loads(result.stdout)
    assert receipt == {
        "acquisition_authorized": False,
        "artifact_id": "3697996f-5ff7-5c14-b0af-db105b83ec30",
        "artifact_sha256": "ffa06ce79fa249c8d6e46f730c737160d052ee2a02a74465ba34a9b4aa8775a9",
        "composition_id": "FAMILY_A_CRSP_SEC_RTDSM_V1",
        "decision_state": "OPERATIONAL_COMPOSITION_SELECTED",
        "outcome": "BLOCKED",
        "selected_product_count": 3,
        "verified": True,
    }


@pytest.mark.parametrize(
    "mutation",
    [
        lambda payload: payload.update({"acquisition_authorized": True}),
        lambda payload: payload.update({"product_ids": list(reversed(payload["product_ids"]))}),
        lambda payload: payload["capability_assignments"][0].update(
            {"assigned_product_code": "SEC_EDGAR_SUBMISSIONS_AND_XBRL_DATA_APIS"}
        ),
        lambda payload: payload["decision_gates"][3].update({"passed": True, "state": "PASS"}),
    ],
)
def test_phase26_verifier_rejects_tampering(tmp_path: Path, mutation: object) -> None:
    payload = json.loads(ARTIFACT.read_bytes())
    mutation(payload)  # type: ignore[operator]
    candidate = tmp_path / "tampered.json"
    candidate.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")
    result = _run(str(VERIFIER), "--artifact", str(candidate))
    assert result.returncode == 2 and result.stdout == b"" and result.stderr == VERIFIER_FAILURE


@pytest.mark.parametrize(
    ("script", "arguments", "failure"),
    [
        (GENERATOR, (), GENERATOR_FAILURE),
        (GENERATOR, ("--unknown",), GENERATOR_FAILURE),
        (VERIFIER, (), VERIFIER_FAILURE),
        (VERIFIER, ("--artifact",), VERIFIER_FAILURE),
    ],
)
def test_phase26_invalid_invocation_is_sanitized(
    script: Path, arguments: tuple[str, ...], failure: bytes
) -> None:
    result = _run(str(script), *arguments)
    assert result.returncode == 2 and result.stdout == b"" and result.stderr == failure
