from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fable5_data.phase27 import canonical as c
from fable5_data.phase27.package import build_phase27_package, canonical_phase27_package_bytes

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "scripts/generate_family_a_rights_and_entitlement_evidence_intake.py"
VERIFIER = ROOT / "scripts/verify_family_a_rights_and_entitlement_evidence_intake.py"
ARTIFACT = ROOT / "docs/PHASE_27_FAMILY_A_RIGHTS_AND_ENTITLEMENT_EVIDENCE_INTAKE.json"
GENERATOR_FAILURE = b"Phase 27 rights-and-entitlement evidence generation failed.\n"
VERIFIER_FAILURE = b"Phase 27 rights-and-entitlement evidence verification failed.\n"
CONFIRMATION = "--confirm-rights-and-entitlement-evidence-intake-only"


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


def test_phase27_generator_is_deterministic_and_matches_artifact() -> None:
    arguments = (str(GENERATOR), CONFIRMATION)
    first = _run(*arguments)
    second = _run(*arguments)
    assert first.returncode == second.returncode == 0
    assert first.stderr == second.stderr == b""
    assert first.stdout == second.stdout == ARTIFACT.read_bytes()
    assert first.stdout == canonical_phase27_package_bytes()


def test_phase27_generator_accepts_only_strict_sanitized_optional_metadata(
    tmp_path: Path,
) -> None:
    intake = tmp_path / "evidence-metadata.json"
    intake.write_text(build_phase27_package().intake.model_dump_json(), encoding="utf-8")
    result = _run(str(GENERATOR), CONFIRMATION, "--evidence-metadata", str(intake))
    assert result.returncode == 0 and result.stderr == b""
    assert result.stdout == ARTIFACT.read_bytes()


def test_phase27_verifier_returns_only_the_sanitized_blocked_receipt() -> None:
    artifact = build_phase27_package()
    result = _run(str(VERIFIER), "--artifact", str(ARTIFACT))
    assert result.returncode == 0 and result.stderr == b""
    assert json.loads(result.stdout) == {
        "acquisition_authorized": False,
        "artifact_id": str(artifact.artifact_id),
        "artifact_sha256": artifact.artifact_sha256,
        "composition_id": "FAMILY_A_CRSP_SEC_RTDSM_V1",
        "determination": "COMPOSITION_RIGHTS_ENTITLEMENT_EVIDENCE_MISSING",
        "evidence_bundle_id": str(artifact.evidence_bundle_id),
        "evidence_bundle_sha256": artifact.evidence_bundle_sha256,
        "outcome": "BLOCKED",
        "verified": True,
        "verified_evidence_recorded": False,
    }


@pytest.mark.parametrize(
    "mutation",
    [
        lambda payload: payload.update({"acquisition_authorized": True}),
        lambda payload: payload.update({"research_ingestion_authorized": True}),
        lambda payload: payload.update({"order_submission_authorized": True}),
        lambda payload: payload.update({"live_path_absent": False}),
        lambda payload: payload.update({"verified_evidence_recorded": True}),
        lambda payload: payload.update({"artifact_sha256": "0" * 64}),
        lambda payload: payload.update({"product_ids": list(reversed(payload["product_ids"]))}),
    ],
)
def test_phase27_verifier_rejects_tampering(tmp_path: Path, mutation: object) -> None:
    payload = json.loads(ARTIFACT.read_bytes())
    mutation(payload)  # type: ignore[operator]
    candidate = tmp_path / "tampered.json"
    candidate.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8"
    )
    result = _run(str(VERIFIER), "--artifact", str(candidate))
    assert result.returncode == 2 and result.stdout == b"" and result.stderr == VERIFIER_FAILURE


def test_phase27_verifier_rejects_rehashed_semantic_authority_tampering(tmp_path: Path) -> None:
    payload = json.loads(ARTIFACT.read_bytes())
    payload["block_reason"] = "Acquisition and live execution are authorized."
    unhashed = {
        key: value
        for key, value in payload.items()
        if key not in {"artifact_id", "artifact_sha256"}
    }
    replacement_hash = c.domain_sha256(c.ARTIFACT_DOMAIN, unhashed)
    payload["artifact_sha256"] = replacement_hash
    payload["artifact_id"] = str(c.uuid_from_sha256(c.ARTIFACT_NAMESPACE, replacement_hash))
    candidate = tmp_path / "rehashed-semantic-tamper.json"
    candidate.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8"
    )
    result = _run(str(VERIFIER), "--artifact", str(candidate))
    assert result.returncode == 2 and result.stdout == b"" and result.stderr == VERIFIER_FAILURE


@pytest.mark.parametrize(
    ("script", "arguments", "failure"),
    [
        (GENERATOR, (), GENERATOR_FAILURE),
        (GENERATOR, (CONFIRMATION, CONFIRMATION), GENERATOR_FAILURE),
        (GENERATOR, ("--unknown",), GENERATOR_FAILURE),
        (VERIFIER, (), VERIFIER_FAILURE),
        (VERIFIER, ("--artifact",), VERIFIER_FAILURE),
        (VERIFIER, ("--unknown",), VERIFIER_FAILURE),
    ],
)
def test_phase27_invalid_invocation_is_sanitized(
    script: Path, arguments: tuple[str, ...], failure: bytes
) -> None:
    result = _run(str(script), *arguments)
    assert result.returncode == 2 and result.stdout == b"" and result.stderr == failure


@pytest.mark.parametrize(
    "forbidden_key",
    [
        "raw_body",
        "raw_header",
        "raw_account",
        "raw_entitlement",
        "raw_agreement",
        "personal_identifier",
        "provider_fetch_url",
        "data_file",
        "schema_sample",
        "research_output",
        "candidate_screen_output",
        "strategy_output",
        "performance_result",
        "risk_promotion",
        "order_submission",
        "execution",
        "cancellation",
        "liquidation",
        "live_path",
        "credential",
        "secret",
        "token",
        "cookie",
    ],
)
def test_phase27_sensitive_metadata_is_rejected_without_echo(
    tmp_path: Path, forbidden_key: str
) -> None:
    marker = "DO-NOT-LEAK-PHASE27-SENSITIVE-MATERIAL"
    intake = tmp_path / "sensitive.json"
    intake.write_text(json.dumps({forbidden_key: marker}), encoding="utf-8")
    result = _run(str(GENERATOR), CONFIRMATION, "--evidence-metadata", str(intake))
    assert result.returncode == 2 and result.stdout == b"" and result.stderr == GENERATOR_FAILURE
    assert marker.encode() not in result.stdout + result.stderr


@pytest.mark.parametrize(
    "marker",
    [
        "token=DO-NOT-ECHO-THIS-PHASE27-MARKER",
        "Bearer DO-NOT-ECHO-THIS-PHASE27-MARKER",
        "PKABCDEFGHIJKLMNOPQRSTUVWXYZ123456",
    ],
)
def test_phase27_secret_shaped_text_is_rejected_without_echo(tmp_path: Path, marker: str) -> None:
    intake = tmp_path / "secret-shaped.json"
    intake.write_text(json.dumps({"note": marker}), encoding="utf-8")
    result = _run(str(GENERATOR), CONFIRMATION, "--evidence-metadata", str(intake))
    assert result.returncode == 2 and result.stdout == b"" and result.stderr == GENERATOR_FAILURE
    assert marker.encode() not in result.stdout + result.stderr


def test_phase27_duplicate_metadata_keys_are_rejected(tmp_path: Path) -> None:
    intake = tmp_path / "duplicate.json"
    intake.write_bytes(b'{"crsp":{},"crsp":{}}')
    result = _run(str(GENERATOR), CONFIRMATION, "--evidence-metadata", str(intake))
    assert result.returncode == 2 and result.stdout == b"" and result.stderr == GENERATOR_FAILURE


@pytest.mark.parametrize("invalid_kind", ["oversize", "nul"])
def test_phase27_bounded_input_rejects_oversize_and_nul(tmp_path: Path, invalid_kind: str) -> None:
    content = (
        b"x" * (128 * 1024 + 1) if invalid_kind == "oversize" else b'{"safe":"value\\u0000"}\x00'
    )
    intake = tmp_path / "invalid.json"
    intake.write_bytes(content)
    result = _run(str(GENERATOR), CONFIRMATION, "--evidence-metadata", str(intake))
    assert result.returncode == 2 and result.stdout == b"" and result.stderr == GENERATOR_FAILURE


@pytest.mark.parametrize("invalid_kind", ["oversize", "nul", "noncanonical"])
def test_phase27_verifier_rejects_bounded_and_noncanonical_artifacts(
    tmp_path: Path, invalid_kind: str
) -> None:
    if invalid_kind == "oversize":
        content = b"x" * (1024 * 1024 + 1)
    elif invalid_kind == "nul":
        content = ARTIFACT.read_bytes() + b"\x00"
    else:
        content = json.dumps(json.loads(ARTIFACT.read_bytes()), indent=2).encode() + b"\n"
    candidate = tmp_path / "invalid-artifact.json"
    candidate.write_bytes(content)
    result = _run(str(VERIFIER), "--artifact", str(candidate))
    assert result.returncode == 2 and result.stdout == b"" and result.stderr == VERIFIER_FAILURE
