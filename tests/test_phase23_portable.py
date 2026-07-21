from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fable5_data.phase23.rights_review import canonical_rtdsm_current_use_rights_review_bytes

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "scripts/generate_family_a_rtdsm_current_use_rights_review.py"
VERIFIER = ROOT / "scripts/verify_family_a_rtdsm_current_use_rights_review.py"
ARTIFACT = ROOT / "docs/PHASE_23_FAMILY_A_RTDSM_CURRENT_USE_RIGHTS_REVIEW.json"
GENERATOR_FAILURE = b"Family A RTDSM current-use-rights review generation failed.\n"
VERIFIER_FAILURE = b"Family A RTDSM current-use-rights review verification failed.\n"


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


def test_phase23_generator_and_committed_artifact_are_exact() -> None:
    first = _run(str(GENERATOR), "--confirm-public-terms-rights-review-only")
    second = _run(str(GENERATOR), "--confirm-public-terms-rights-review-only")
    assert first.returncode == second.returncode == 0
    assert first.stderr == second.stderr == b""
    assert first.stdout == second.stdout == ARTIFACT.read_bytes()
    assert first.stdout == canonical_rtdsm_current_use_rights_review_bytes()


def test_phase23_verifier_accepts_only_the_canonical_artifact() -> None:
    result = _run(str(VERIFIER), "--review", str(ARTIFACT))
    assert result.returncode == 0
    assert result.stderr == b""
    payload = json.loads(result.stdout)
    assert payload["status"] == "valid"
    assert payload["network"] == "disabled"
    assert payload["outcome"] == "BLOCKED"
    assert payload["official_source_count"] == 3
    assert payload["rights_finding_count"] == 1
    assert payload["future_requirement_count"] == 4


@pytest.mark.parametrize(
    "mutation",
    [
        lambda payload: payload.update({"rights_granted": True}),
        lambda payload: payload["rights_findings"][0].update({"operational_use_cleared": True}),
        lambda payload: payload["future_requirements"][0].update({"satisfied": True}),
        lambda payload: payload["public_terms_sources"][0].update(
            {"url": "https://example.invalid"}
        ),
    ],
)
def test_phase23_verifier_rejects_semantic_tampering(tmp_path: Path, mutation: object) -> None:
    payload = json.loads(ARTIFACT.read_bytes())
    mutation(payload)  # type: ignore[operator]
    candidate = tmp_path / "tampered.json"
    candidate.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")
    result = _run(str(VERIFIER), "--review", str(candidate))
    assert result.returncode == 2
    assert result.stdout == b""
    assert result.stderr == VERIFIER_FAILURE


@pytest.mark.parametrize(
    "arguments",
    [(), ("--review",), ("--review", "a", "--review", "b"), ("--unknown",)],
)
def test_phase23_verifier_invalid_invocation_is_sanitized(arguments: tuple[str, ...]) -> None:
    result = _run(str(VERIFIER), *arguments)
    assert result.returncode == 2
    assert result.stdout == b""
    assert result.stderr == VERIFIER_FAILURE


@pytest.mark.parametrize(
    "arguments",
    [
        (),
        ("--confirm-public-terms-rights-review-only", "x"),
        (
            "--confirm-public-terms-rights-review-only",
            "--confirm-public-terms-rights-review-only",
        ),
        ("--unknown",),
    ],
)
def test_phase23_generator_invalid_invocation_is_sanitized(arguments: tuple[str, ...]) -> None:
    result = _run(str(GENERATOR), *arguments)
    assert result.returncode == 2
    assert result.stdout == b""
    assert result.stderr == GENERATOR_FAILURE
