from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from fable5_data.phase22.canonical import PHASE22_ARTIFACT_HASH_DOMAIN, domain_sha256
from fable5_data.phase22.inventory_amendment import (
    build_family_a_macro_vintage_candidate_inventory_amendment,
    canonical_macro_vintage_candidate_inventory_amendment_bytes,
)

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/PHASE_22_FAMILY_A_MACRO_VINTAGE_CANDIDATE_INVENTORY_AMENDMENT.json"
GENERATOR = ROOT / "scripts/generate_family_a_macro_vintage_candidate_inventory_amendment.py"
VERIFIER = ROOT / "scripts/verify_family_a_macro_vintage_candidate_inventory_amendment.py"
GENERATOR_FAILURE = b"Family A macro-vintage candidate-inventory amendment generation failed.\n"
VERIFIER_FAILURE = b"Family A macro-vintage candidate-inventory amendment verification failed.\n"


def _run(*arguments: str, cwd: Path = ROOT) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run([sys.executable, *arguments], cwd=cwd, capture_output=True, check=False)


def _verify(path: Path) -> subprocess.CompletedProcess[bytes]:
    return _run(str(VERIFIER), "--amendment", str(path), cwd=path.parent)


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
        PHASE22_ARTIFACT_HASH_DOMAIN,
        {key: value for key, value in payload.items() if key != "artifact_sha256"},
    )


def test_generator_is_repeatable_and_matches_builder_and_committed_artifact() -> None:
    args = (str(GENERATOR), "--confirm-candidate-inventory-amendment-only")
    first = _run(*args)
    second = _run(*args)
    expected = canonical_macro_vintage_candidate_inventory_amendment_bytes()
    assert first.returncode == second.returncode == 0
    assert first.stderr == second.stderr == b""
    assert first.stdout == second.stdout == expected
    assert ARTIFACT.read_bytes() == expected


def test_offline_verifier_is_repeatable_and_emits_only_sanitized_receipt(
    tmp_path: Path,
) -> None:
    candidate = tmp_path / "amendment.json"
    candidate.write_bytes(canonical_macro_vintage_candidate_inventory_amendment_bytes())
    artifact = build_family_a_macro_vintage_candidate_inventory_amendment()
    first = _verify(candidate)
    second = _verify(candidate)
    assert first.returncode == second.returncode == 0
    assert first.stderr == second.stderr == b""
    assert first.stdout == second.stdout
    assert json.loads(first.stdout) == {
        "aggregate_conclusion": (
            "BLOCKED_AWAITING_CURRENT_RIGHTS_FITNESS_REVIEW_AND_EXPLICIT_OPERATIONAL_COMPOSITION"
        ),
        "amendment_state": "CANDIDATE_INVENTORY_AMENDMENT_FROZEN",
        "artifact_id": str(artifact.artifact_id),
        "artifact_sha256": artifact.artifact_sha256,
        "candidate_group_amendment_count": 1,
        "candidate_product_count": 1,
        "future_review_requirement_count": 4,
        "network": "disabled",
        "official_source_count": 3,
        "outcome": "BLOCKED",
        "schema_version": ("phase22-family-a-macro-vintage-candidate-inventory-amendment-v1"),
        "status": "valid",
    }
    for forbidden in (b"credential", b"token", b"account", b"provider_payload"):
        assert forbidden not in first.stdout.lower()


@pytest.mark.parametrize(
    ("collection", "index", "field", "value"),
    [
        ("official_sources", 0, "remote_body_included", True),
        ("candidate_group_amendments", 0, "operationally_selected", True),
        ("candidate_group_amendments", 0, "ranked", True),
        ("candidate_products", 0, "rights_state", "UNPROVEN"),
        ("candidate_products", 0, "operationally_selected", True),
        ("candidate_products", 0, "coverage_proven", True),
        ("candidate_products", 0, "schema_proven", True),
        ("candidate_products", 0, "current_availability_proven", True),
        ("candidate_products", 0, "external_sample_qualified", True),
        ("future_review_requirements", 0, "external_action_authorized", True),
        ("future_review_requirements", 3, "satisfied", True),
    ],
)
def test_verifier_rejects_row_tamper(
    tmp_path: Path,
    collection: str,
    index: int,
    field: str,
    value: object,
) -> None:
    payload = json.loads(canonical_macro_vintage_candidate_inventory_amendment_bytes())
    payload[collection][index][field] = value
    candidate = tmp_path / "tampered.json"
    _write_canonical(candidate, payload)
    _assert_closed_failure(_verify(candidate))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("accepted_phase21_commit_sha", "0" * 40),
        ("accepted_phase21_tree_sha", "0" * 40),
        ("amendment_policy_sha256", "0" * 64),
        ("outcome", "PASSED"),
        ("amendment_state", "COMPLETE"),
        ("aggregate_conclusion", "ELIGIBLE"),
        ("composition_ranked", True),
        ("operational_source_product_composition_selected", True),
        ("selection_evidence_produced", True),
        ("provider_selected", True),
        ("rights_review_performed", True),
        ("rights_verified", True),
        ("credentials_loaded", True),
        ("external_data_capture_authorized", True),
        ("provider_payload_persisted", True),
        ("research_executed", True),
        ("execution_authorized", True),
        ("order_submission_authorized", True),
        ("live_path_absent", False),
    ],
)
def test_verifier_rejects_fully_rehashed_identity_result_and_authority_tamper(
    tmp_path: Path, field: str, value: object
) -> None:
    payload = json.loads(canonical_macro_vintage_candidate_inventory_amendment_bytes())
    payload[field] = value
    _rehash_artifact(payload)
    candidate = tmp_path / f"tampered-{field}.json"
    _write_canonical(candidate, payload)
    _assert_closed_failure(_verify(candidate))


def test_verifier_rejects_forbidden_output_values_even_when_rehashed(
    tmp_path: Path,
) -> None:
    canonical = json.loads(canonical_macro_vintage_candidate_inventory_amendment_bytes())
    for field in (
        "selection_evidence_sha256",
        "operational_source_product_composition_sha256",
        "provider_payload",
        "captured_remote_body",
    ):
        payload = copy.deepcopy(canonical)
        payload[field] = "0" * 64
        _rehash_artifact(payload)
        candidate = tmp_path / f"forbidden-{field}.json"
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
    candidate.write_bytes(raw(canonical_macro_vintage_candidate_inventory_amendment_bytes()))
    _assert_closed_failure(_verify(candidate))


def test_verifier_rejects_symlink_directory_and_lexical_escape(tmp_path: Path) -> None:
    target = tmp_path / "target.json"
    target.write_bytes(canonical_macro_vintage_candidate_inventory_amendment_bytes())
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
    trusted = tmp_path / "trusted"
    trusted.mkdir()
    result = _run(
        str(VERIFIER),
        "--amendment",
        str(Path("..") / target.name),
        cwd=trusted,
    )
    _assert_closed_failure(result)


@pytest.mark.parametrize(
    "arguments",
    [
        (),
        ("--amendment",),
        ("--amendment", "a", "--amendment", "b"),
        ("--requirements", "a"),
        ("--unknown",),
    ],
)
def test_verifier_invalid_invocation_is_sanitized(arguments: tuple[str, ...]) -> None:
    result = _run(str(VERIFIER), *arguments)
    _assert_closed_failure(result)


@pytest.mark.parametrize(
    "arguments",
    [
        (),
        ("--confirm-candidate-inventory-amendment-only", "x"),
        (
            "--confirm-candidate-inventory-amendment-only",
            "--confirm-candidate-inventory-amendment-only",
        ),
        ("--unknown",),
    ],
)
def test_generator_invalid_invocation_is_sanitized(arguments: tuple[str, ...]) -> None:
    result = _run(str(GENERATOR), *arguments)
    assert result.returncode == 2
    assert result.stdout == b""
    assert result.stderr == GENERATOR_FAILURE
