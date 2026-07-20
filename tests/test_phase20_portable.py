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
from fable5_data.phase20.canonical import PHASE20_ARTIFACT_HASH_DOMAIN, domain_sha256
from fable5_data.phase20.input_register import (
    build_family_a_evaluation_holdout_input_register,
    canonical_evaluation_holdout_input_register_bytes,
)

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/PHASE_20_FAMILY_A_EVALUATION_HOLDOUT_INPUT_REGISTER.json"
GENERATOR = ROOT / "scripts/generate_family_a_evaluation_holdout_input_register.py"
VERIFIER = ROOT / "scripts/verify_family_a_evaluation_holdout_input_register.py"
GENERATOR_FAILURE = b"Family A evaluation/holdout input-register generation failed.\n"
VERIFIER_FAILURE = b"Family A evaluation/holdout input-register verification failed.\n"


def _run(
    *arguments: str,
    environment: dict[str, str] | None = None,
    cwd: Path = ROOT,
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [sys.executable, *arguments],
        cwd=cwd,
        capture_output=True,
        check=False,
        env=environment,
    )


def _verify(path: Path) -> subprocess.CompletedProcess[bytes]:
    return _run(str(VERIFIER), "--register", str(path), cwd=path.parent)


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
        PHASE20_ARTIFACT_HASH_DOMAIN,
        {key: value for key, value in payload.items() if key != "artifact_sha256"},
    )


def _create_directory_name_surrogate(link: Path, target: Path) -> None:
    try:
        os.symlink(target, link, target_is_directory=True)
        return
    except OSError:
        if os.name != "nt":
            raise
    result = subprocess.run(
        ["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(target)],
        check=False,
        capture_output=True,
    )
    if result.returncode != 0 or not link.exists():
        pytest.fail("could not create a Windows directory name-surrogate for the denial proof")


def test_generator_is_repeatable_and_matches_builder_and_committed_artifact() -> None:
    first = _run(str(GENERATOR), "--confirm-input-register-only")
    second = _run(str(GENERATOR), "--confirm-input-register-only")
    expected = canonical_evaluation_holdout_input_register_bytes()

    assert first.returncode == second.returncode == 0
    assert first.stderr == second.stderr == b""
    assert first.stdout == second.stdout == expected
    assert ARTIFACT.read_bytes() == expected


def test_offline_verifier_is_repeatable_and_emits_only_a_sanitized_receipt(
    tmp_path: Path,
) -> None:
    candidate = tmp_path / "input-register.json"
    candidate.write_bytes(canonical_evaluation_holdout_input_register_bytes())
    artifact = build_family_a_evaluation_holdout_input_register()

    first = _verify(candidate)
    second = _verify(candidate)

    assert first.returncode == second.returncode == 0
    assert first.stderr == second.stderr == b""
    assert first.stdout == second.stdout
    assert json.loads(first.stdout) == {
        "aggregate_conclusion": "BLOCKED_MISSING_OPERATIONAL_AND_DATA_SPECIFIC_INPUTS",
        "artifact_id": str(artifact.artifact_id),
        "artifact_sha256": artifact.artifact_sha256,
        "input_requirement_count": 20,
        "network": "disabled",
        "outcome": "BLOCKED",
        "register_state": "INPUTS_FROZEN",
        "required_prior_evidence": "missing",
        "schema_version": "phase20-family-a-evaluation-holdout-input-register-v1",
        "status": "valid",
        "step3_eligible": False,
        "transition_rule_count": 10,
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
        ("input_requirements", 0, "requirement_satisfied", True),
        ("input_requirements", 0, "evidence_state", "PRESENT"),
        ("input_requirements", 0, "input_value_present", True),
        ("input_requirements", 0, "resolves_reserved_evidence", True),
        ("transition_rules", 0, "applied", True),
        ("required_prior_evidence", 0, "state", "PRESENT"),
        ("required_prior_evidence", 1, "produced", True),
        ("phase15_gap_bindings", 0, "state", "PRESENT"),
        ("source_plan_steps", 2, "state", "OUTPUT_FROZEN"),
    ],
)
def test_verifier_rejects_input_transition_evidence_gap_and_step_tamper(
    tmp_path: Path,
    collection: str,
    index: int,
    field: str,
    value: object,
) -> None:
    payload = json.loads(canonical_evaluation_holdout_input_register_bytes())
    payload[collection][index][field] = value
    candidate = tmp_path / "tampered.json"
    _write_canonical(candidate, payload)
    _assert_closed_failure(_verify(candidate))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("accepted_phase19_commit_sha", "0" * 40),
        ("accepted_phase19_tree_sha", "0" * 40),
        ("outcome", "PASSED"),
        ("register_state", "COMPLETE"),
        ("aggregate_conclusion", "ELIGIBLE"),
        ("step3_required_prior_evidence_complete", True),
        ("step3_eligible", True),
        ("step3_external_action_authorized", True),
        ("provider_selected", True),
        ("credentials_loaded", True),
        ("external_sample_qualification_authorized", True),
        ("provider_data_request_performed", True),
        ("provider_payload_persisted", True),
        ("non_synthetic_evaluation_policy_created", True),
        ("confirmation_holdout_definition_created", True),
        ("confirmation_holdout_opened", True),
        ("research_executed", True),
        ("execution_authorized", True),
        ("order_submission_authorized", True),
        ("live_path_absent", False),
    ],
)
def test_verifier_rejects_fully_rehashed_identity_result_and_authority_tamper(
    tmp_path: Path,
    field: str,
    value: object,
) -> None:
    payload = json.loads(canonical_evaluation_holdout_input_register_bytes())
    payload[field] = value
    _rehash_artifact(payload)
    candidate = tmp_path / f"tampered-{field}.json"
    _write_canonical(candidate, payload)
    _assert_closed_failure(_verify(candidate))


def test_verifier_rejects_reserved_outputs_and_value_fields_even_when_rehashed(
    tmp_path: Path,
) -> None:
    canonical = json.loads(canonical_evaluation_holdout_input_register_bytes())
    cases: list[tuple[str, dict[str, Any]]] = []
    for reserved in (
        "non_synthetic_evaluation_policy_sha256",
        "confirmation_holdout_definition_sha256",
        "qualification_artifact_set_sha256",
    ):
        payload = copy.deepcopy(canonical)
        payload[reserved] = "0" * 64
        _rehash_artifact(payload)
        cases.append((reserved, payload))
    value_payload = copy.deepcopy(canonical)
    value_payload["required_prior_evidence"][0]["value"] = "0" * 64
    _rehash_artifact(value_payload)
    cases.append(("value", value_payload))

    for label, payload in cases:
        candidate = tmp_path / f"reserved-{label}.json"
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
    candidate.write_bytes(raw(canonical_evaluation_holdout_input_register_bytes()))
    _assert_closed_failure(_verify(candidate))


def test_verifier_rejects_symlink_directory_and_pre_post_read_change(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import scripts.verify_family_a_evaluation_holdout_input_register as verifier

    monkeypatch.chdir(tmp_path)
    target = tmp_path / "target.json"
    target.write_bytes(canonical_evaluation_holdout_input_register_bytes())
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

    descriptor = os.open(target, os.O_RDONLY | getattr(os, "O_CLOEXEC", 0))
    original_fstat = verifier.os.fstat
    calls = 0

    def unstable_fstat(open_descriptor: int) -> object:
        nonlocal calls
        calls += 1
        metadata = original_fstat(open_descriptor)
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

    try:
        monkeypatch.setattr(verifier.os, "fstat", unstable_fstat)
        with pytest.raises(verifier._InvalidRegister):
            verifier._read_descriptor(descriptor)
        assert calls == 2
    finally:
        os.close(descriptor)


def test_verifier_rejects_an_intermediate_directory_name_surrogate(tmp_path: Path) -> None:
    trusted_root = tmp_path / "trusted"
    outside = tmp_path / "outside"
    trusted_root.mkdir()
    outside.mkdir()
    target = outside / "register.json"
    target.write_bytes(canonical_evaluation_holdout_input_register_bytes())
    surrogate = trusted_root / "surrogate"
    _create_directory_name_surrogate(surrogate, outside)

    result = _run(
        str(VERIFIER),
        "--register",
        str(Path("surrogate") / target.name),
        cwd=trusted_root,
    )
    _assert_closed_failure(result)


def test_lexical_escape_is_rejected_before_target_filesystem_access(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import scripts.verify_family_a_evaluation_holdout_input_register as verifier

    trusted_root = tmp_path / "trusted"
    trusted_root.mkdir()
    outside = tmp_path / "outside.json"
    outside.write_bytes(canonical_evaluation_holdout_input_register_bytes())
    monkeypatch.chdir(trusted_root)
    touched: list[str] = []

    def target_filesystem_call_forbidden(*args: object, **kwargs: object) -> bytes:
        del args, kwargs
        touched.append("target")
        raise AssertionError("lexical escape reached target filesystem traversal")

    monkeypatch.setattr(verifier, "_read_windows_register", target_filesystem_call_forbidden)
    monkeypatch.setattr(verifier, "_read_posix_register", target_filesystem_call_forbidden)
    with pytest.raises(verifier._InvalidRegister):
        verifier._read_register(str(outside))
    assert touched == []


@pytest.mark.skipif(os.name == "nt", reason="POSIX openat leaf-swap proof")
def test_posix_leaf_name_swap_is_rejected_after_handle_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import scripts.verify_family_a_evaluation_holdout_input_register as verifier

    monkeypatch.chdir(tmp_path)
    target = tmp_path / "register.json"
    replacement = tmp_path / "replacement.json"
    canonical = canonical_evaluation_holdout_input_register_bytes()
    target.write_bytes(canonical)
    replacement.write_bytes(canonical)
    original_open = verifier.os.open
    swapped = False

    def swapping_open(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal swapped
        if dir_fd is None:
            descriptor = original_open(path, flags, mode)
        else:
            descriptor = original_open(path, flags, mode, dir_fd=dir_fd)
        if (
            not swapped
            and dir_fd is not None
            and os.fspath(path) == target.name
            and not flags & getattr(os, "O_DIRECTORY", 0)
        ):
            os.replace(replacement, target)
            swapped = True
        return descriptor

    monkeypatch.setattr(verifier.os, "open", swapping_open)
    with pytest.raises(verifier._InvalidRegister):
        verifier._read_register(target.name)
    assert swapped is True


@pytest.mark.skipif(os.name != "nt", reason="Windows handle-sharing policy proof")
def test_windows_component_handles_are_nofollow_and_deny_delete_sharing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import scripts.verify_family_a_evaluation_holdout_input_register as verifier

    monkeypatch.chdir(tmp_path)
    nested = tmp_path / "nested"
    nested.mkdir()
    target = nested / "register.json"
    target.write_bytes(canonical_evaluation_holdout_input_register_bytes())
    original_create_file = verifier._windows_create_file
    calls: list[tuple[str, int, int]] = []

    def recording_create_file(
        path_text: str,
        desired_access: int,
        share_mode: int,
        flags_and_attributes: int,
    ) -> int:
        calls.append((path_text, share_mode, flags_and_attributes))
        return original_create_file(
            path_text,
            desired_access,
            share_mode,
            flags_and_attributes,
        )

    monkeypatch.setattr(verifier, "_windows_create_file", recording_create_file)
    assert verifier._read_register(str(Path("nested") / target.name)) == target.read_bytes()
    assert len(calls) == 3
    for _path, share_mode, flags in calls:
        assert share_mode == (
            verifier._WINDOWS_FILE_SHARE_READ | verifier._WINDOWS_FILE_SHARE_WRITE
        )
        assert flags & verifier._WINDOWS_FILE_FLAG_OPEN_REPARSE_POINT
    assert all(
        flags & verifier._WINDOWS_FILE_FLAG_BACKUP_SEMANTICS for _path, _share, flags in calls[:2]
    )
    assert not calls[-1][2] & verifier._WINDOWS_FILE_FLAG_BACKUP_SEMANTICS


@pytest.mark.skipif(os.name != "nt", reason="Windows no-share-delete leaf-swap proof")
def test_windows_leaf_handle_blocks_a_name_swap_during_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import scripts.verify_family_a_evaluation_holdout_input_register as verifier

    monkeypatch.chdir(tmp_path)
    target = tmp_path / "register.json"
    replacement = tmp_path / "replacement.json"
    canonical = canonical_evaluation_holdout_input_register_bytes()
    target.write_bytes(canonical)
    replacement.write_bytes(canonical)
    original_open_component = verifier._windows_open_component
    swap_result: list[str] = []

    def swapping_open_component(path_text: str, *, directory: bool) -> int:
        handle = original_open_component(path_text, directory=directory)
        if not directory and not swap_result:
            try:
                os.replace(replacement, target)
            except OSError:
                swap_result.append("blocked")
            else:
                swap_result.append("succeeded")
        return handle

    monkeypatch.setattr(verifier, "_windows_open_component", swapping_open_component)
    assert verifier._read_register(target.name) == canonical
    assert swap_result == ["blocked"]
    assert target.read_bytes() == canonical
    assert replacement.exists()


@pytest.mark.parametrize(
    "path_text",
    [
        pytest.param(r"\\attacker.invalid\share\register.json", id="unc-backslash"),
        pytest.param("//attacker.invalid/share/register.json", id="unc-forward-slash"),
        pytest.param(r"\\?\UNC\attacker.invalid\share\register.json", id="extended-unc"),
        pytest.param(r"\\.\GLOBALROOT\Device\Mup\register.json", id="device-namespace"),
    ],
)
def test_verifier_rejects_remote_path_syntax_before_any_filesystem_call(
    path_text: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import scripts.verify_family_a_evaluation_holdout_input_register as verifier

    touched: list[str] = []

    def filesystem_call_forbidden(*args: object, **kwargs: object) -> object:
        del args, kwargs
        touched.append("filesystem")
        raise AssertionError("remote path reached the filesystem")

    monkeypatch.setattr(verifier.os, "getcwd", filesystem_call_forbidden)
    monkeypatch.setattr(verifier.Path, "lstat", filesystem_call_forbidden)
    monkeypatch.setattr(verifier.os, "open", filesystem_call_forbidden)

    with pytest.raises(verifier._InvalidRegister):
        verifier._read_register(path_text)
    assert touched == []


def test_windows_different_drive_is_rejected_before_target_filesystem_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import scripts.verify_family_a_evaluation_holdout_input_register as verifier

    current_drive = "C:"
    different_drive = "D:"
    assert ntpath.splitdrive(f"{different_drive}\\register.json")[0] != current_drive
    touched: list[str] = []

    def target_filesystem_call_forbidden(*args: object, **kwargs: object) -> object:
        del args, kwargs
        touched.append("target")
        raise AssertionError("different-drive path reached the filesystem")

    monkeypatch.setattr(verifier, "_IS_WINDOWS", True)
    monkeypatch.setattr(verifier.os, "getcwd", lambda: f"{current_drive}\\repo")
    monkeypatch.setattr(verifier.Path, "lstat", target_filesystem_call_forbidden)
    monkeypatch.setattr(verifier.os, "open", target_filesystem_call_forbidden)

    with pytest.raises(verifier._InvalidRegister):
        verifier._read_register(f"{different_drive}\\register.json")
    assert touched == []


@pytest.mark.parametrize(
    "path_text",
    [
        pytest.param(r"C:register.json", id="drive-relative"),
        pytest.param(r"register.json:stream", id="alternate-data-stream"),
        pytest.param("register.json.", id="trailing-dot"),
        pytest.param("register.json ", id="trailing-space"),
        pytest.param(r"..\register.json", id="parent-component"),
    ],
)
def test_windows_ambiguous_local_syntax_is_rejected_before_path_construction(
    path_text: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import scripts.verify_family_a_evaluation_holdout_input_register as verifier

    touched: list[str] = []

    def path_construction_forbidden(*args: object, **kwargs: object) -> object:
        del args, kwargs
        touched.append("path")
        raise AssertionError("ambiguous Windows syntax reached path construction")

    monkeypatch.setattr(verifier, "_IS_WINDOWS", True)
    monkeypatch.setattr(verifier.os, "getcwd", lambda: r"C:\trusted")
    monkeypatch.setattr(verifier, "Path", path_construction_forbidden)
    with pytest.raises(verifier._InvalidRegister):
        verifier._local_register_path(path_text)
    assert touched == []


def test_verifier_accepts_relative_committed_path_and_same_drive_absolute_temp_path(
    tmp_path: Path,
) -> None:
    relative = ARTIFACT.relative_to(ROOT)
    relative_result = _run(str(VERIFIER), "--register", str(relative))
    assert relative_result.returncode == 0
    assert relative_result.stderr == b""

    candidate = tmp_path / "same-drive-register.json"
    candidate.write_bytes(canonical_evaluation_holdout_input_register_bytes())
    absolute_result = _verify(candidate)
    assert absolute_result.returncode == 0
    assert absolute_result.stderr == b""


def test_clis_reject_bad_arguments_without_canary_disclosure() -> None:
    canary = "phase20-secret-and-provider-data-canary-do-not-emit"
    results = (
        (_run(str(GENERATOR)), GENERATOR_FAILURE),
        (
            _run(
                str(GENERATOR),
                "--confirm-input-register-only",
                "--confirm-input-register-only",
            ),
            GENERATOR_FAILURE,
        ),
        (
            _run(str(GENERATOR), "--confirm-input-register-only", "--provider", canary),
            GENERATOR_FAILURE,
        ),
        (_run(str(VERIFIER)), VERIFIER_FAILURE),
        (
            _run(str(VERIFIER), "--register", str(ARTIFACT), "--register", str(ARTIFACT)),
            VERIFIER_FAILURE,
        ),
        (_run(str(VERIFIER), "--register", canary, "--repair"), VERIFIER_FAILURE),
        (
            _run(str(VERIFIER), "--register", canary, "--expected-hash", "0" * 64),
            VERIFIER_FAILURE,
        ),
    )
    for result, failure in results:
        assert result.returncode == 2
        assert result.stdout == b""
        assert result.stderr == failure
        assert canary.encode() not in result.stderr


def test_ambient_environment_cannot_change_generator_or_verifier_output(
    tmp_path: Path,
) -> None:
    candidate = tmp_path / "input-register.json"
    candidate.write_bytes(canonical_evaluation_holdout_input_register_bytes())
    clean_generator = _run(str(GENERATOR), "--confirm-input-register-only")
    clean_verifier = _verify(candidate)
    environment = dict(os.environ)
    environment.update(
        {
            "FABLE5_PHASE20_FAKE_CREDENTIAL": "phase20-secret-canary",
            "DATABASE_URL": "postgresql://phase20-secret-canary",
            "HTTP_PROXY": "http://phase20-secret-canary.invalid",
        }
    )

    ambient_generator = _run(
        str(GENERATOR),
        "--confirm-input-register-only",
        environment=environment,
    )
    ambient_verifier = _run(
        str(VERIFIER),
        "--register",
        str(candidate),
        environment=environment,
        cwd=candidate.parent,
    )

    assert ambient_generator.stdout == clean_generator.stdout
    assert ambient_generator.stderr == clean_generator.stderr == b""
    assert ambient_verifier.stdout == clean_verifier.stdout
    assert ambient_verifier.stderr == clean_verifier.stderr == b""
    assert b"phase20-secret-canary" not in ambient_generator.stdout + ambient_verifier.stdout


@pytest.mark.parametrize(
    "module_name",
    [
        "scripts.generate_family_a_evaluation_holdout_input_register",
        "scripts.verify_family_a_evaluation_holdout_input_register",
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
