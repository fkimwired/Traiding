from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fable5_data.phase24.rights_clarification import (
    canonical_rtdsm_rights_clarification_requirements_bytes,
)

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "scripts/generate_family_a_rtdsm_rights_clarification_requirements.py"
VERIFIER = ROOT / "scripts/verify_family_a_rtdsm_rights_clarification_requirements.py"
ARTIFACT = ROOT / "docs/PHASE_24_FAMILY_A_RTDSM_RIGHTS_CLARIFICATION_REQUIREMENTS.json"
GENERATOR_FAILURE = b"Family A RTDSM rights-clarification requirements generation failed.\n"
VERIFIER_FAILURE = b"Family A RTDSM rights-clarification requirements verification failed.\n"


def _run(*arguments: str, cwd: Path = ROOT) -> subprocess.CompletedProcess[bytes]:
    environment = os.environ.copy()
    for name in tuple(environment):
        if any(token in name.upper() for token in ("TOKEN", "SECRET", "PASSWORD", "API_KEY")):
            environment.pop(name, None)
    return subprocess.run(
        [sys.executable, *arguments], cwd=cwd, env=environment, check=False, capture_output=True
    )


def test_phase24_generator_and_committed_artifact_are_exact() -> None:
    first = _run(str(GENERATOR), "--confirm-rights-clarification-requirements-only")
    second = _run(str(GENERATOR), "--confirm-rights-clarification-requirements-only")
    assert first.returncode == second.returncode == 0
    assert first.stderr == second.stderr == b""
    assert first.stdout == second.stdout == ARTIFACT.read_bytes()
    assert first.stdout == canonical_rtdsm_rights_clarification_requirements_bytes()


def test_phase24_verifier_accepts_only_the_canonical_artifact() -> None:
    result = _run(str(VERIFIER), "--requirements", str(ARTIFACT))
    assert result.returncode == 0 and result.stderr == b""
    payload = json.loads(result.stdout)
    assert (
        payload["status"] == "valid"
        and payload["network"] == "disabled"
        and payload["outcome"] == "BLOCKED"
    )
    assert (
        payload["proposed_use_disclosure_count"],
        payload["clarification_question_count"],
        payload["evidence_requirement_count"],
        payload["transition_rule_count"],
    ) == (8, 10, 6, 7)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda payload: payload.update({"rights_granted": True}),
        lambda payload: payload.update({"provider_contact_performed": True}),
        lambda payload: payload["clarification_questions"][0].update(
            {"state": "VERIFIED_PERMITTED"}
        ),
        lambda payload: payload["evidence_requirements"][0].update({"evidence_present": True}),
    ],
)
def test_phase24_verifier_rejects_semantic_tampering(tmp_path: Path, mutation: object) -> None:
    payload = json.loads(ARTIFACT.read_bytes())
    mutation(payload)  # type: ignore[operator]
    candidate = tmp_path / "tampered.json"
    candidate.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")
    result = _run(str(VERIFIER), "--requirements", str(candidate))
    assert result.returncode == 2 and result.stdout == b"" and result.stderr == VERIFIER_FAILURE


@pytest.mark.parametrize(
    "arguments",
    [(), ("--requirements",), ("--requirements", "a", "--requirements", "b"), ("--unknown",)],
)
def test_phase24_verifier_invalid_invocation_is_sanitized(arguments: tuple[str, ...]) -> None:
    result = _run(str(VERIFIER), *arguments)
    assert result.returncode == 2 and result.stdout == b"" and result.stderr == VERIFIER_FAILURE


@pytest.mark.parametrize(
    "arguments",
    [
        (),
        ("--confirm-rights-clarification-requirements-only", "x"),
        (
            "--confirm-rights-clarification-requirements-only",
            "--confirm-rights-clarification-requirements-only",
        ),
        ("--unknown",),
    ],
)
def test_phase24_generator_invalid_invocation_is_sanitized(arguments: tuple[str, ...]) -> None:
    result = _run(str(GENERATOR), *arguments)
    assert result.returncode == 2 and result.stdout == b"" and result.stderr == GENERATOR_FAILURE
