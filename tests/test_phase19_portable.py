from __future__ import annotations

import copy
import json
import ntpath
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from fable5_data.phase19.assessment import canonical_step3_prerequisite_assessment_bytes
from fable5_data.phase19.canonical import (
    PHASE19_ARTIFACT_HASH_DOMAIN,
    PHASE19_PREREQUISITE_HASH_DOMAIN,
    PHASE19_PREREQUISITES_MANIFEST_HASH_DOMAIN,
    PHASE19_STEP_HASH_DOMAIN,
    PHASE19_STEPS_MANIFEST_HASH_DOMAIN,
    domain_sha256,
)

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/PHASE_19_FAMILY_A_STEP3_PREREQUISITE_ASSESSMENT.json"
GENERATOR = ROOT / "scripts/generate_family_a_step3_prerequisite_assessment.py"
VERIFIER = ROOT / "scripts/verify_family_a_step3_prerequisite_assessment.py"
GENERATOR_FAILURE = b"Family A Step-3 prerequisite assessment generation failed.\n"
VERIFIER_FAILURE = b"Family A Step-3 prerequisite assessment verification failed.\n"


def _run(
    *arguments: str,
    environment: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [sys.executable, *arguments],
        cwd=ROOT,
        capture_output=True,
        check=False,
        env=environment,
    )


def _verify(path: Path) -> subprocess.CompletedProcess[bytes]:
    return _run(str(VERIFIER), "--assessment", str(path))


def _write_canonical(path: Path, payload: object) -> None:
    path.write_bytes(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        + b"\n"
    )


def _assert_closed_failure(result: subprocess.CompletedProcess[bytes]) -> None:
    assert result.returncode == 2
    assert result.stdout == b""
    assert result.stderr == VERIFIER_FAILURE


def _rehash_artifact(payload: dict[str, Any]) -> None:
    payload["artifact_sha256"] = domain_sha256(
        PHASE19_ARTIFACT_HASH_DOMAIN,
        {key: value for key, value in payload.items() if key != "artifact_sha256"},
    )


def test_generator_is_repeatable_and_matches_builder_and_committed_artifact() -> None:
    first = _run(str(GENERATOR), "--confirm-prerequisite-assessment-only")
    second = _run(str(GENERATOR), "--confirm-prerequisite-assessment-only")
    expected = canonical_step3_prerequisite_assessment_bytes()

    assert first.returncode == second.returncode == 0
    assert first.stderr == second.stderr == b""
    assert first.stdout == second.stdout == expected
    assert ARTIFACT.read_bytes() == expected


def test_offline_verifier_is_repeatable_and_emits_only_the_sanitized_receipt(
    tmp_path: Path,
) -> None:
    candidate = tmp_path / "assessment.json"
    candidate.write_bytes(canonical_step3_prerequisite_assessment_bytes())

    first = _verify(candidate)
    second = _verify(candidate)

    assert first.returncode == second.returncode == 0
    assert first.stderr == second.stderr == b""
    assert first.stdout == second.stdout
    assert json.loads(first.stdout) == {
        "aggregate_conclusion": "BLOCKED_MISSING_EVALUATION_POLICY_AND_HOLDOUT",
        "artifact_id": "0b3f9153-71cc-5052-9b47-f714ed17bb99",
        "artifact_sha256": "ed738badfb6e95feb4d7969d299bdc6186ef13ebf0f036134518e147803c72df",
        "assessment_state": "OUTPUT_FROZEN",
        "network": "disabled",
        "outcome": "BLOCKED",
        "prerequisite_count": 19,
        "required_prior_evidence": "missing",
        "schema_version": "phase19-family-a-step3-prerequisite-assessment-v1",
        "status": "valid",
        "step3_eligible": False,
    }
    rendered = first.stdout.lower()
    for forbidden in (
        b"non_synthetic_evaluation_policy_sha256",
        b"confirmation_holdout_definition_sha256",
        b"credential",
        b"token",
        b"account",
        b"provider_payload",
    ):
        assert forbidden not in rendered


@pytest.mark.parametrize(
    ("collection", "index", "field", "value"),
    [
        ("prerequisites", 0, "requirement_satisfied", True),
        ("prerequisites", 14, "evidence_state", "PRESENT"),
        ("required_prior_evidence", 0, "state", "PRESENT"),
        ("required_prior_evidence", 1, "produced", True),
        ("phase15_gap_bindings", 0, "state", "PRESENT"),
        ("source_plan_steps", 1, "state", "NOT_STARTED"),
        ("source_plan_steps", 2, "state", "OUTPUT_FROZEN"),
        ("source_plan_steps", 2, "external_action_authorized", True),
    ],
)
def test_verifier_rejects_row_step_and_authority_tamper(
    tmp_path: Path,
    collection: str,
    index: int,
    field: str,
    value: object,
) -> None:
    payload = json.loads(canonical_step3_prerequisite_assessment_bytes())
    payload[collection][index][field] = value
    candidate = tmp_path / "tampered.json"
    _write_canonical(candidate, payload)
    _assert_closed_failure(_verify(candidate))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("accepted_phase18_commit_sha", "0" * 40),
        ("accepted_phase18_tree_sha", "0" * 40),
        ("outcome", "PASSED"),
        ("assessment_state", "COMPLETE"),
        ("aggregate_conclusion", "ELIGIBLE"),
        ("step3_required_prior_evidence_complete", True),
        ("step3_eligible", True),
        ("step3_external_action_authorized", True),
        ("provider_selected", True),
        ("credentials_loaded", True),
        ("external_sample_qualification_authorized", True),
        ("provider_data_request_performed", True),
        ("provider_payload_persisted", True),
        ("research_executed", True),
        ("execution_authorized", True),
        ("order_submission_authorized", True),
        ("live_path_absent", False),
    ],
)
def test_verifier_rejects_identity_boundary_and_authority_tamper(
    tmp_path: Path,
    field: str,
    value: object,
) -> None:
    payload = json.loads(canonical_step3_prerequisite_assessment_bytes())
    payload[field] = value
    candidate = tmp_path / f"tampered-{field}.json"
    _write_canonical(candidate, payload)
    _assert_closed_failure(_verify(candidate))


def test_verifier_rejects_fully_rehashed_prerequisite_step_and_boundary_tamper(
    tmp_path: Path,
) -> None:
    canonical = json.loads(canonical_step3_prerequisite_assessment_bytes())
    cases: list[tuple[str, dict[str, Any]]] = []

    prerequisite = copy.deepcopy(canonical)
    prerequisite["prerequisites"][0]["definition"] = "Forged satisfied prerequisite."
    prerequisite["prerequisites"][0]["prerequisite_sha256"] = domain_sha256(
        PHASE19_PREREQUISITE_HASH_DOMAIN,
        {
            key: value
            for key, value in prerequisite["prerequisites"][0].items()
            if key != "prerequisite_sha256"
        },
    )
    prerequisite["prerequisites_manifest_sha256"] = domain_sha256(
        PHASE19_PREREQUISITES_MANIFEST_HASH_DOMAIN,
        tuple(item["prerequisite_sha256"] for item in prerequisite["prerequisites"]),
    )
    _rehash_artifact(prerequisite)
    cases.append(("prerequisite", prerequisite))

    step = copy.deepcopy(canonical)
    step["source_plan_steps"][2]["state"] = "OUTPUT_FROZEN"
    step["source_plan_steps"][2]["step_sha256"] = domain_sha256(
        PHASE19_STEP_HASH_DOMAIN,
        {key: value for key, value in step["source_plan_steps"][2].items() if key != "step_sha256"},
    )
    step["steps_manifest_sha256"] = domain_sha256(
        PHASE19_STEPS_MANIFEST_HASH_DOMAIN,
        tuple(item["step_sha256"] for item in step["source_plan_steps"]),
    )
    _rehash_artifact(step)
    cases.append(("step", step))

    authority = copy.deepcopy(canonical)
    authority["step3_eligible"] = True
    _rehash_artifact(authority)
    cases.append(("authority", authority))

    for label, payload in cases:
        candidate = tmp_path / f"rehashed-{label}.json"
        _write_canonical(candidate, payload)
        _assert_closed_failure(_verify(candidate))


def test_verifier_rejects_reserved_step3_outputs_even_when_rehashed(tmp_path: Path) -> None:
    canonical = json.loads(canonical_step3_prerequisite_assessment_bytes())
    for reserved in (
        "non_synthetic_evaluation_policy_sha256",
        "confirmation_holdout_definition_sha256",
    ):
        payload = copy.deepcopy(canonical)
        payload["required_prior_evidence"][0][reserved] = "0" * 64
        _rehash_artifact(payload)
        candidate = tmp_path / f"reserved-{reserved}.json"
        _write_canonical(candidate, payload)
        _assert_closed_failure(_verify(candidate))


@pytest.mark.parametrize(
    "raw",
    [
        pytest.param(
            lambda original: b'{"schema_version":"forged",' + original[1:],
            id="duplicate-key",
        ),
        pytest.param(lambda original: b"\xef\xbb\xbf" + original, id="bom"),
        pytest.param(lambda original: b'{"forged":1.5,' + original[1:], id="float"),
        pytest.param(lambda original: b'{"forged":NaN,' + original[1:], id="nan"),
        pytest.param(lambda original: b'{"forged":Infinity,' + original[1:], id="infinity"),
        pytest.param(lambda _original: b"[]\n", id="non-object"),
        pytest.param(lambda _original: b"", id="empty"),
        pytest.param(lambda _original: b"\xff", id="invalid-utf8"),
        pytest.param(
            lambda original: (
                json.dumps(json.loads(original), sort_keys=True, indent=2).encode() + b"\n"
            ),
            id="noncanonical",
        ),
        pytest.param(lambda _original: b"{" + b" " * (512 * 1024) + b"}\n", id="oversized"),
    ],
)
def test_verifier_rejects_strict_input_failures(tmp_path: Path, raw: Any) -> None:
    candidate = tmp_path / "invalid.json"
    candidate.write_bytes(raw(canonical_step3_prerequisite_assessment_bytes()))
    _assert_closed_failure(_verify(candidate))


def test_verifier_rejects_symlink_directory_and_pre_post_read_change(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import scripts.verify_family_a_step3_prerequisite_assessment as verifier

    target = tmp_path / "target.json"
    target.write_bytes(canonical_step3_prerequisite_assessment_bytes())
    directory = tmp_path / "directory"
    directory.mkdir()
    _assert_closed_failure(_verify(directory))

    link = tmp_path / "link.json"
    try:
        os.symlink(target, link)
    except OSError:
        pass
    else:
        _assert_closed_failure(_verify(link))

    original_fstat = verifier.os.fstat
    calls = 0

    def unstable_fstat(descriptor: int) -> object:
        nonlocal calls
        calls += 1
        metadata = original_fstat(descriptor)
        if calls == 1:
            return metadata

        class ChangedMetadata:
            st_dev = metadata.st_dev
            st_ino = metadata.st_ino
            st_mode = metadata.st_mode
            st_size = metadata.st_size
            st_mtime_ns = metadata.st_mtime_ns
            st_ctime_ns = metadata.st_ctime_ns + 1

        return ChangedMetadata()

    monkeypatch.setattr(verifier.os, "fstat", unstable_fstat)
    with pytest.raises(verifier._InvalidAssessment):
        verifier._read_assessment(str(target))
    assert calls == 2


@pytest.mark.parametrize(
    "path_text",
    [
        pytest.param(r"\\attacker.invalid\share\assessment.json", id="unc-backslash"),
        pytest.param("//attacker.invalid/share/assessment.json", id="unc-forward-slash"),
        pytest.param(
            r"\\?\UNC\attacker.invalid\share\assessment.json",
            id="extended-unc",
        ),
        pytest.param(r"\\.\GLOBALROOT\Device\Mup\assessment.json", id="device-namespace"),
    ],
)
def test_verifier_rejects_remote_path_syntax_before_any_filesystem_call(
    path_text: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import scripts.verify_family_a_step3_prerequisite_assessment as verifier

    touched: list[str] = []

    def filesystem_call_forbidden(*args: object, **kwargs: object) -> object:
        del args, kwargs
        touched.append("filesystem")
        raise AssertionError("remote path reached the filesystem")

    monkeypatch.setattr(verifier.os, "getcwd", filesystem_call_forbidden)
    monkeypatch.setattr(verifier.Path, "lstat", filesystem_call_forbidden)
    monkeypatch.setattr(verifier.os, "open", filesystem_call_forbidden)

    with pytest.raises(verifier._InvalidAssessment):
        verifier._read_assessment(path_text)
    assert touched == []


def test_windows_different_drive_is_rejected_before_target_filesystem_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import scripts.verify_family_a_step3_prerequisite_assessment as verifier

    current_drive = "C:"
    different_drive = "D:"
    assert ntpath.splitdrive(f"{different_drive}\\assessment.json")[0] != current_drive
    touched: list[str] = []

    def target_filesystem_call_forbidden(*args: object, **kwargs: object) -> object:
        del args, kwargs
        touched.append("target")
        raise AssertionError("different-drive path reached the filesystem")

    monkeypatch.setattr(verifier, "_IS_WINDOWS", True)
    monkeypatch.setattr(verifier.os, "getcwd", lambda: f"{current_drive}\\repo")
    monkeypatch.setattr(verifier.Path, "lstat", target_filesystem_call_forbidden)
    monkeypatch.setattr(verifier.os, "open", target_filesystem_call_forbidden)

    with pytest.raises(verifier._InvalidAssessment):
        verifier._read_assessment(f"{different_drive}\\assessment.json")
    assert touched == []


def test_verifier_accepts_relative_committed_path_and_same_drive_absolute_temp_path(
    tmp_path: Path,
) -> None:
    relative = ARTIFACT.relative_to(ROOT)
    relative_result = _run(str(VERIFIER), "--assessment", str(relative))
    assert relative_result.returncode == 0
    assert relative_result.stderr == b""

    candidate = tmp_path / "same-drive-assessment.json"
    candidate.write_bytes(canonical_step3_prerequisite_assessment_bytes())
    absolute_result = _verify(candidate)
    assert absolute_result.returncode == 0
    assert absolute_result.stderr == b""


def test_clis_reject_bad_arguments_without_canary_disclosure() -> None:
    canary = "phase19-secret-and-provider-data-canary-do-not-emit"
    results = (
        (_run(str(GENERATOR)), GENERATOR_FAILURE),
        (
            _run(
                str(GENERATOR),
                "--confirm-prerequisite-assessment-only",
                "--confirm-prerequisite-assessment-only",
            ),
            GENERATOR_FAILURE,
        ),
        (
            _run(
                str(GENERATOR),
                "--confirm-prerequisite-assessment-only",
                "--provider",
                canary,
            ),
            GENERATOR_FAILURE,
        ),
        (_run(str(VERIFIER)), VERIFIER_FAILURE),
        (
            _run(
                str(VERIFIER),
                "--assessment",
                str(ARTIFACT),
                "--assessment",
                str(ARTIFACT),
            ),
            VERIFIER_FAILURE,
        ),
        (_run(str(VERIFIER), "--assessment", canary, "--repair"), VERIFIER_FAILURE),
        (
            _run(str(VERIFIER), "--assessment", canary, "--expected-hash", "0" * 64),
            VERIFIER_FAILURE,
        ),
    )
    for result, failure in results:
        assert result.returncode == 2
        assert result.stdout == b""
        assert result.stderr == failure
        assert canary.encode() not in result.stderr


def test_ambient_environment_cannot_change_generator_or_verifier_output(tmp_path: Path) -> None:
    candidate = tmp_path / "assessment.json"
    candidate.write_bytes(canonical_step3_prerequisite_assessment_bytes())
    clean_generator = _run(str(GENERATOR), "--confirm-prerequisite-assessment-only")
    clean_verifier = _verify(candidate)
    environment = dict(os.environ)
    environment.update(
        {
            "FABLE5_PHASE19_FAKE_CREDENTIAL": "phase19-secret-canary",
            "DATABASE_URL": "postgresql://phase19-secret-canary",
            "HTTP_PROXY": "http://phase19-secret-canary.invalid",
        }
    )

    ambient_generator = _run(
        str(GENERATOR),
        "--confirm-prerequisite-assessment-only",
        environment=environment,
    )
    ambient_verifier = _run(
        str(VERIFIER),
        "--assessment",
        str(candidate),
        environment=environment,
    )

    assert ambient_generator.stdout == clean_generator.stdout
    assert ambient_generator.stderr == clean_generator.stderr == b""
    assert ambient_verifier.stdout == clean_verifier.stdout
    assert ambient_verifier.stderr == clean_verifier.stderr == b""
    assert b"phase19-secret-canary" not in ambient_generator.stdout + ambient_verifier.stdout


@pytest.mark.parametrize(
    "module_name",
    [
        "scripts.generate_family_a_step3_prerequisite_assessment",
        "scripts.verify_family_a_step3_prerequisite_assessment",
    ],
)
def test_cli_audit_hook_denies_subprocess_creation_in_an_isolated_process(
    module_name: str,
) -> None:
    probe = (
        f"import {module_name} as target\n"
        "import subprocess\n"
        "import sys\n"
        "target._install_offline_boundary()\n"
        "try:\n"
        "    subprocess.run([sys.executable, '-c', 'pass'], check=False)\n"
        "except target._OfflineBoundaryViolation:\n"
        "    print('denied')\n"
        "else:\n"
        "    raise SystemExit(1)\n"
    )
    result = _run("-c", probe)
    assert result.returncode == 0
    expected = b"denied\r\n" if os.name == "nt" else b"denied\n"
    assert result.stdout == expected
    assert result.stderr == b""
