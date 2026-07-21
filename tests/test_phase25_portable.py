from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fable5_data.phase25.package import canonical_phase25_package_bytes

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "scripts/generate_family_a_rtdsm_rights_response_and_adapter_patterns.py"
VERIFIER = ROOT / "scripts/verify_family_a_rtdsm_rights_response_and_adapter_patterns.py"
ARTIFACT = ROOT / "docs/PHASE_25_FAMILY_A_RTDSM_RIGHTS_RESPONSE_AND_ADAPTER_PATTERNS.json"
GENERATOR_FAILURE = b"Phase 25 rights-response package generation failed.\n"
VERIFIER_FAILURE = b"Phase 25 rights-response package verification failed.\n"


def _run(*arguments: str, cwd: Path = ROOT) -> subprocess.CompletedProcess[bytes]:
    environment = os.environ.copy()
    for name in tuple(environment):
        if any(token in name.upper() for token in ("TOKEN", "SECRET", "PASSWORD", "API_KEY")):
            environment.pop(name, None)
    return subprocess.run(
        [sys.executable, *arguments],
        cwd=cwd,
        env=environment,
        check=False,
        capture_output=True,
    )


def test_phase25_generator_is_deterministic_and_matches_committed_artifact() -> None:
    args = (str(GENERATOR), "--confirm-evidence-intake-and-patterns-only")
    first = _run(*args)
    second = _run(*args)
    assert first.returncode == second.returncode == 0
    assert first.stderr == second.stderr == b""
    assert first.stdout == second.stdout == ARTIFACT.read_bytes()
    assert first.stdout == canonical_phase25_package_bytes()


def test_phase25_verifier_accepts_only_canonical_bytes() -> None:
    result = _run(str(VERIFIER), "--artifact", str(ARTIFACT))
    assert result.returncode == 0 and result.stderr == b""
    receipt = json.loads(result.stdout)
    assert receipt["verified"] is True
    assert receipt["outcome"] == "BLOCKED"
    assert receipt["rights_verified"] is False
    assert receipt["determination"] == "RIGHTS_RESPONSE_EVIDENCE_MISSING"


@pytest.mark.parametrize(
    "mutation",
    [
        lambda payload: payload.update({"rights_verified": True}),
        lambda payload: payload.update({"yahoo_rights_state": "VERIFIED"}),
        lambda payload: payload["question_evaluations"][0].update({"state": "PASS"}),
        lambda payload: payload["source_evidence"][0].update({"inspected_revision": "0" * 40}),
    ],
)
def test_phase25_verifier_rejects_tampering(tmp_path: Path, mutation: object) -> None:
    payload = json.loads(ARTIFACT.read_bytes())
    mutation(payload)  # type: ignore[operator]
    candidate = tmp_path / "tampered.json"
    candidate.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")
    result = _run(str(VERIFIER), "--artifact", str(candidate))
    assert result.returncode == 2 and result.stdout == b"" and result.stderr == VERIFIER_FAILURE


@pytest.mark.parametrize(
    "arguments",
    [(), ("--artifact",), ("--artifact", "a", "--artifact", "b"), ("--unknown",)],
)
def test_phase25_verifier_invalid_invocation_is_sanitized(arguments: tuple[str, ...]) -> None:
    result = _run(str(VERIFIER), *arguments)
    assert result.returncode == 2 and result.stdout == b"" and result.stderr == VERIFIER_FAILURE


@pytest.mark.parametrize(
    "arguments",
    [
        (),
        ("--confirm-evidence-intake-and-patterns-only", "x"),
        (
            "--confirm-evidence-intake-and-patterns-only",
            "--confirm-evidence-intake-and-patterns-only",
        ),
        ("--unknown",),
    ],
)
def test_phase25_generator_invalid_invocation_is_sanitized(arguments: tuple[str, ...]) -> None:
    result = _run(str(GENERATOR), *arguments)
    assert result.returncode == 2 and result.stdout == b"" and result.stderr == GENERATOR_FAILURE


@pytest.mark.parametrize("forbidden_key", ["provider_body", "credential", "raw_payload"])
def test_phase25_provider_bodies_and_credentials_never_cross_cli_boundary(
    tmp_path: Path, forbidden_key: str
) -> None:
    marker = "DO-NOT-LEAK-PROVIDER-BODY-OR-CREDENTIAL"
    intake = tmp_path / "intake.json"
    intake.write_text(
        json.dumps(
            {
                "schema_version": "phase25-rtdsm-rights-response-intake-v1",
                "response_received": False,
                forbidden_key: marker,
            }
        )
    )
    result = _run(
        str(GENERATOR),
        "--confirm-evidence-intake-and-patterns-only",
        "--response-metadata",
        str(intake),
    )
    assert result.returncode == 2 and result.stdout == b"" and result.stderr == GENERATOR_FAILURE
    assert marker.encode() not in result.stdout + result.stderr


def test_phase25_bounded_input_rejects_oversize_without_echo(tmp_path: Path) -> None:
    intake = tmp_path / "oversize.json"
    intake.write_bytes(b"x" * (128 * 1024 + 1))
    result = _run(
        str(GENERATOR),
        "--confirm-evidence-intake-and-patterns-only",
        "--response-metadata",
        str(intake),
    )
    assert result.returncode == 2 and result.stdout == b"" and result.stderr == GENERATOR_FAILURE
