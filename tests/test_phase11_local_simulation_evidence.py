from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from fable5_paper.canonical import (
    PHASE10_ARTIFACT_HASH_DOMAIN,
    PHASE10_CHECK_HASH_DOMAIN,
    domain_sha256,
)
from fable5_paper.contracts import PaperSimulationArtifact, PaperSimulationCheck
from fable5_paper.evidence import (
    PHASE11_LOCAL_SIMULATION_EVIDENCE_BUNDLE_HASH_DOMAIN,
    build_local_simulation_evidence_bundle,
)

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify_local_simulation_evidence.py"
FAILURE_MESSAGE = "Local simulation evidence verification failed.\n"
MAX_BUNDLE_BYTES = 1024 * 1024
FIXTURE_PATHS = {
    "completed": ROOT / "services" / "frontend" / "e2e" / "fixtures" / "phase10-completed.json",
    "blocked": ROOT / "services" / "frontend" / "e2e" / "fixtures" / "phase10-blocked.json",
}
EXPECTED_BUNDLE_SHA256S = {
    "completed": "8ad868297ec060d00067a5e17e40df83123a306898bfd9eacd869d0af543647c",
    "blocked": "35ca33153e7c46a6d0d7154b894020a0db8e1c4ac67d41db1869289771c43f3f",
}


def _bundle(kind: str) -> dict[str, Any]:
    artifact = PaperSimulationArtifact.model_validate_json(
        FIXTURE_PATHS[kind].read_bytes(), strict=True
    )
    bundle = build_local_simulation_evidence_bundle(artifact)
    assert bundle.bundle_sha256 == EXPECTED_BUNDLE_SHA256S[kind]
    return bundle.model_dump(mode="json")


def _write_json(path: Path, payload: dict[str, Any], *, pretty: bool = False) -> Path:
    path.write_text(
        json.dumps(
            payload,
            indent=2 if pretty else None,
            separators=None if pretty else (",", ":"),
        ),
        encoding="utf-8",
        newline="\n",
    )
    return path


def _run(
    bundle_path: Path,
    expected_sha256: str,
    *,
    cwd: Path = ROOT,
    environment: dict[str, str] | None = None,
    timeout_seconds: float = 15,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--bundle",
            str(bundle_path),
            "--expected-bundle-sha256",
            expected_sha256,
        ],
        cwd=cwd,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout_seconds,
    )


def _run_args(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )


def _assert_invalid(result: subprocess.CompletedProcess[str], *secrets: str) -> None:
    assert result.returncode == 2
    assert result.stdout == ""
    assert result.stderr == FAILURE_MESSAGE
    combined = result.stdout + result.stderr
    for secret in secrets:
        assert secret not in combined


@pytest.mark.parametrize(
    ("kind", "outcome"),
    (("completed", "SIMULATED_COMPLETE"), ("blocked", "BLOCKED")),
)
def test_cli_accepts_both_canonical_phase10_fixture_bundles(
    tmp_path: Path, kind: str, outcome: str
) -> None:
    payload = _bundle(kind)
    path = _write_json(tmp_path / f"{kind}.json", payload)

    first = _run(path, EXPECTED_BUNDLE_SHA256S[kind])
    second = _run(path, EXPECTED_BUNDLE_SHA256S[kind])

    expected = {
        "bundle_sha256": EXPECTED_BUNDLE_SHA256S[kind],
        "network": "disabled",
        "outcome": outcome,
        "schema": "phase11-local-simulation-evidence-bundle-v1",
        "simulation_artifact_sha256": payload["simulation_artifact_sha256"],
        "simulation_run_id": payload["simulation_run_id"],
        "status": "valid",
    }
    expected_line = json.dumps(expected, sort_keys=True, separators=(",", ":")) + "\n"
    assert first.returncode == second.returncode == 0
    assert first.stdout == second.stdout == expected_line
    assert first.stderr == second.stderr == ""


def test_cli_is_portable_across_json_layout_and_working_directory(tmp_path: Path) -> None:
    payload = dict(reversed(tuple(_bundle("completed").items())))
    path = _write_json(tmp_path / "pretty-reordered.json", payload, pretty=True)

    result = _run(path, EXPECTED_BUNDLE_SHA256S["completed"], cwd=tmp_path)

    assert result.returncode == 0
    assert json.loads(result.stdout)["bundle_sha256"] == EXPECTED_BUNDLE_SHA256S["completed"]
    assert result.stderr == ""


def test_cli_requires_a_separate_matching_trust_anchor(tmp_path: Path) -> None:
    path = _write_json(tmp_path / "valid-but-untrusted.json", _bundle("completed"))

    result = _run(path, "0" * 64)

    _assert_invalid(result)


@pytest.mark.parametrize(
    "expected_sha256",
    (
        "",
        "0" * 63,
        "0" * 65,
        "g" * 64,
        EXPECTED_BUNDLE_SHA256S["completed"].upper(),
    ),
)
def test_cli_requires_exact_lowercase_sha256_trust_anchor(
    tmp_path: Path, expected_sha256: str
) -> None:
    path = _write_json(tmp_path / "bundle.json", _bundle("completed"))

    result = _run(path, expected_sha256)

    _assert_invalid(result)


def _tamper(payload: dict[str, Any], mutation: str) -> None:
    simulation = payload["simulation"]
    if mutation == "unknown_top_level":
        payload["unsupported"] = True
    elif mutation == "missing_top_level":
        payload.pop("bundle_schema_version")
    elif mutation == "unsupported_bundle_schema":
        payload["bundle_schema_version"] = "phase11-local-simulation-evidence-bundle-v2"
    elif mutation == "strict_top_level_type":
        payload["simulation_run_id"] = 7
    elif mutation == "cross_identity":
        payload["simulation_run_id"] = "00000000-0000-4000-8000-000000000000"
    elif mutation == "top_level_artifact_hash":
        payload["simulation_artifact_sha256"] = "0" * 64
    elif mutation == "unknown_nested":
        simulation["unsupported"] = True
    elif mutation == "missing_nested":
        simulation.pop("disclaimer")
    elif mutation == "unsupported_nested_literal":
        simulation["local_mock_only"] = False
    elif mutation == "nested_artifact_hash":
        simulation["artifact_sha256"] = "0" * 64
    elif mutation == "unsupported_outcome":
        simulation["outcome"] = "LIVE_COMPLETE"
    elif mutation == "ledger_value":
        simulation["ledger_entries"][0]["cash_after"] = "999999.00000000"
    elif mutation == "ordered_checks":
        simulation["checks"] = list(reversed(simulation["checks"]))
    else:
        raise AssertionError(f"unknown mutation: {mutation}")


@pytest.mark.parametrize(
    "mutation",
    (
        "unknown_top_level",
        "missing_top_level",
        "unsupported_bundle_schema",
        "strict_top_level_type",
        "cross_identity",
        "top_level_artifact_hash",
        "unknown_nested",
        "missing_nested",
        "unsupported_nested_literal",
        "nested_artifact_hash",
        "unsupported_outcome",
        "ledger_value",
        "ordered_checks",
    ),
)
def test_cli_rejects_schema_identity_hash_and_safety_tampering(
    tmp_path: Path, mutation: str
) -> None:
    payload = _bundle("completed")
    _tamper(payload, mutation)
    path = _write_json(tmp_path / f"tampered-{mutation}.json", payload)

    result = _run(path, EXPECTED_BUNDLE_SHA256S["completed"])

    _assert_invalid(result)


def _duplicate_top_level(text: str) -> str:
    return '{"bundle_schema_version":"phase11-local-simulation-evidence-bundle-v1",' + text[1:]


def _duplicate_nested(text: str) -> str:
    marker = '"simulation":{'
    duplicate = '"simulation_run_id":"00000000-0000-4000-8000-000000000000",'
    return text.replace(marker, marker + duplicate, 1)


def _duplicate_deep(text: str) -> str:
    marker = '"checks":[{'
    return text.replace(marker, marker + '"ordinal":1,', 1)


@pytest.mark.parametrize(
    "duplicator",
    (_duplicate_top_level, _duplicate_nested, _duplicate_deep),
    ids=("top-level", "nested", "deep"),
)
def test_cli_rejects_duplicate_json_keys_at_every_depth(
    tmp_path: Path, duplicator: Callable[[str], str]
) -> None:
    text = json.dumps(_bundle("completed"), separators=(",", ":"))
    path = tmp_path / "duplicate.json"
    path.write_text(duplicator(text), encoding="utf-8")

    result = _run(path, EXPECTED_BUNDLE_SHA256S["completed"])

    _assert_invalid(result)


@pytest.mark.parametrize("constant", ("NaN", "Infinity", "-Infinity"))
def test_cli_rejects_nonstandard_nonfinite_json_constants(tmp_path: Path, constant: str) -> None:
    text = json.dumps(_bundle("completed"), separators=(",", ":"))
    text = text.replace('"random_seed":607', f'"random_seed":{constant}', 1)
    path = tmp_path / "nonfinite.json"
    path.write_text(text, encoding="utf-8")

    result = _run(path, EXPECTED_BUNDLE_SHA256S["completed"])

    _assert_invalid(result)


@pytest.mark.parametrize("representation", ("string", "number"))
def test_cli_bounds_numeric_resource_amplification_before_model_hashing(
    tmp_path: Path,
    representation: str,
) -> None:
    payload = _bundle("completed")
    if representation == "string":
        payload["simulation"]["configuration"]["approved_proposed_notional"] = "1E+999999"
        text = json.dumps(payload, separators=(",", ":"))
    else:
        text = json.dumps(payload, separators=(",", ":")).replace(
            '"random_seed":607',
            '"random_seed":1e999999',
            1,
        )
    path = tmp_path / f"numeric-amplification-{representation}.json"
    path.write_text(text, encoding="utf-8")

    result = _run(
        path,
        EXPECTED_BUNDLE_SHA256S["completed"],
        timeout_seconds=3,
    )

    _assert_invalid(result)


@pytest.mark.parametrize(
    "raw",
    (
        b"",
        b"{",
        b"{} trailing",
        b"[]",
        b'"not-an-object"',
        b"null",
    ),
)
def test_cli_rejects_empty_malformed_trailing_and_non_object_json(
    tmp_path: Path, raw: bytes
) -> None:
    path = tmp_path / "invalid.json"
    path.write_bytes(raw)

    result = _run(path, EXPECTED_BUNDLE_SHA256S["completed"])

    _assert_invalid(result)


@pytest.mark.parametrize(
    "raw",
    (
        b"\xef\xbb\xbf{}",
        b'{"invalid":"\xff"}',
    ),
    ids=("utf8-bom", "invalid-utf8"),
)
def test_cli_rejects_bom_and_invalid_utf8(tmp_path: Path, raw: bytes) -> None:
    path = tmp_path / "encoding.json"
    path.write_bytes(raw)

    result = _run(path, EXPECTED_BUNDLE_SHA256S["completed"])

    _assert_invalid(result)


def test_cli_rejects_oversized_input_without_parsing_it(tmp_path: Path) -> None:
    path = tmp_path / "oversized.json"
    path.write_bytes(b"{" + (b" " * MAX_BUNDLE_BYTES) + b"}")

    result = _run(path, EXPECTED_BUNDLE_SHA256S["completed"])

    _assert_invalid(result)


def test_cli_rejects_non_regular_bundle_path(tmp_path: Path) -> None:
    result = _run(tmp_path, EXPECTED_BUNDLE_SHA256S["completed"])

    _assert_invalid(result, str(tmp_path))


def _sophisticated_rehashed_forgery() -> tuple[dict[str, Any], str]:
    original = build_local_simulation_evidence_bundle(
        PaperSimulationArtifact.model_validate_json(
            FIXTURE_PATHS["completed"].read_bytes(), strict=True
        )
    )
    simulation = original.simulation
    check_payload = simulation.checks[0].model_dump(mode="python", exclude={"check_sha256"})
    check_payload["evidence_sha256s"] = ("0" * 64,)
    forged_check = PaperSimulationCheck.model_validate(
        {
            **check_payload,
            "check_sha256": domain_sha256(PHASE10_CHECK_HASH_DOMAIN, check_payload),
        }
    )
    object.__setattr__(simulation, "checks", (forged_check, *simulation.checks[1:]))
    simulation_payload = simulation.model_dump(
        mode="python",
        exclude={"simulation_run_id", "artifact_sha256", "created_at_utc"},
    )
    object.__setattr__(
        simulation,
        "artifact_sha256",
        domain_sha256(PHASE10_ARTIFACT_HASH_DOMAIN, simulation_payload),
    )
    forged_simulation = PaperSimulationArtifact.model_validate(simulation.model_dump(mode="python"))
    bundle_payload = {
        "bundle_schema_version": original.bundle_schema_version,
        "simulation_run_id": forged_simulation.simulation_run_id,
        "simulation_artifact_sha256": forged_simulation.artifact_sha256,
        "simulation": forged_simulation,
    }
    forged_bundle_sha256 = domain_sha256(
        PHASE11_LOCAL_SIMULATION_EVIDENCE_BUNDLE_HASH_DOMAIN,
        bundle_payload,
    )
    return (
        {
            "bundle_schema_version": original.bundle_schema_version,
            "bundle_sha256": forged_bundle_sha256,
            "simulation_run_id": str(forged_simulation.simulation_run_id),
            "simulation_artifact_sha256": forged_simulation.artifact_sha256,
            "simulation": forged_simulation.model_dump(mode="json"),
        },
        forged_bundle_sha256,
    )


def test_cli_rejects_fully_rehashed_cross_invariant_forgery(tmp_path: Path) -> None:
    payload, forged_bundle_sha256 = _sophisticated_rehashed_forgery()
    path = _write_json(tmp_path / "fully-rehashed-forgery.json", payload)

    result = _run(path, forged_bundle_sha256)

    _assert_invalid(result)


@pytest.mark.parametrize(
    "args",
    (
        (),
        ("--bundle", "only-path"),
        ("--expected-bundle-sha256", "0" * 64),
        ("--unsupported", "value"),
        (
            "--bundle",
            "one",
            "--bundle",
            "two",
            "--expected-bundle-sha256",
            "0" * 64,
        ),
    ),
)
def test_cli_usage_failures_are_exit_two_and_sanitized(args: tuple[str, ...]) -> None:
    result = _run_args(*args)

    _assert_invalid(result, *args)


def test_cli_help_is_the_only_nonverification_zero_exit() -> None:
    result = _run_args("--help")

    assert result.returncode == 0
    assert result.stderr == ""
    assert "--bundle PATH" in result.stdout
    assert "--expected-bundle-sha256 LOWERHEX64" in result.stdout


def test_cli_failure_never_exposes_path_payload_or_exception(tmp_path: Path) -> None:
    secret_path_token = "PRIVATE-BUNDLE-PATH-9127"
    secret_payload_token = "PRIVATE-PAYLOAD-4381"
    path = tmp_path / f"{secret_path_token}.json"
    path.write_text(f'{{"secret":"{secret_payload_token}",', encoding="utf-8")

    result = _run(path, EXPECTED_BUNDLE_SHA256S["completed"])

    _assert_invalid(
        result,
        str(path),
        secret_path_token,
        secret_payload_token,
        "JSONDecodeError",
        "Traceback",
    )


def test_fresh_process_retains_socket_subprocess_and_system_denials(tmp_path: Path) -> None:
    payload = _bundle("completed")
    path = _write_json(tmp_path / "bundle.json", payload)
    probe = textwrap.dedent(
        """
        import os
        import runpy
        import socket
        import subprocess
        import sys

        script, bundle, digest = sys.argv[1:]
        sys.argv = [
            script,
            "--bundle",
            bundle,
            "--expected-bundle-sha256",
            digest,
        ]
        try:
            runpy.run_path(script, run_name="__main__")
        except SystemExit as exc:
            cli_status = int(exc.code or 0)
        if cli_status != 0:
            raise SystemExit(90)

        attempts = (
            lambda: socket.socket(),
            lambda: os.system(""),
            lambda: subprocess.run(
                [sys.executable, "-c", "raise SystemExit(91)"], check=False
            ),
        )
        for attempt in attempts:
            try:
                value = attempt()
            except BaseException:
                continue
            if hasattr(value, "close"):
                value.close()
            raise SystemExit(99)
        sys.stderr.write("AUDIT_BOUNDARY_OK\\n")
        """
    )

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            probe,
            str(SCRIPT),
            str(path),
            EXPECTED_BUNDLE_SHA256S["completed"],
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )

    assert result.returncode == 0
    assert json.loads(result.stdout)["network"] == "disabled"
    assert result.stderr == "AUDIT_BOUNDARY_OK\n"


def test_cli_rejects_new_database_imports_from_the_bundle_module(tmp_path: Path) -> None:
    fake_package = tmp_path / "fake" / "fable5_paper"
    fake_package.mkdir(parents=True)
    (fake_package / "__init__.py").write_text("", encoding="utf-8")
    (fake_package / "evidence.py").write_text(
        "import sqlite3\nclass LocalSimulationEvidenceBundle:\n    pass\n",
        encoding="utf-8",
    )
    path = _write_json(tmp_path / "bundle.json", _bundle("completed"))
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(tmp_path / "fake")

    result = _run(
        path,
        EXPECTED_BUNDLE_SHA256S["completed"],
        cwd=tmp_path,
        environment=environment,
    )

    _assert_invalid(result)
