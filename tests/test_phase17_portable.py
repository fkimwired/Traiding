from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from fable5_data.phase17.canonical import (
    PHASE17_ARTIFACT_HASH_DOMAIN,
    PHASE17_CANDIDATE_HASH_DOMAIN,
    PHASE17_CANDIDATES_MANIFEST_HASH_DOMAIN,
    PHASE17_OUTPUT_HASH_DOMAIN,
    PHASE17_PRODUCT_HASH_DOMAIN,
    PHASE17_PRODUCTS_MANIFEST_HASH_DOMAIN,
    PHASE17_STEP_HASH_DOMAIN,
    PHASE17_STEPS_MANIFEST_HASH_DOMAIN,
    domain_sha256,
)
from fable5_data.phase17.inventory import canonical_candidate_product_inventory_bytes

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/PHASE_17_FAMILY_A_CANDIDATE_PRODUCT_INVENTORY.json"
GENERATOR = ROOT / "scripts/generate_family_a_candidate_product_inventory.py"
VERIFIER = ROOT / "scripts/verify_family_a_candidate_product_inventory.py"
GENERATOR_FAILURE = b"Family A candidate-product inventory generation failed.\n"
VERIFIER_FAILURE = b"Family A candidate-product inventory verification failed.\n"


def _run(*arguments: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run([sys.executable, *arguments], cwd=ROOT, capture_output=True, check=False)


def _write_canonical(path: Path, payload: object) -> None:
    path.write_bytes(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        + b"\n"
    )


def _verify(path: Path) -> subprocess.CompletedProcess[bytes]:
    return _run(str(VERIFIER), "--inventory", str(path))


def _assert_closed_failure(result: subprocess.CompletedProcess[bytes]) -> None:
    assert result.returncode == 2
    assert result.stdout == b""
    assert result.stderr == VERIFIER_FAILURE


def _rehash_after_product_tamper(payload: dict[str, Any], index: int) -> None:
    product = payload["products"][index]
    product["product_sha256"] = domain_sha256(
        PHASE17_PRODUCT_HASH_DOMAIN,
        {key: value for key, value in product.items() if key != "product_sha256"},
    )
    inventory_sha256 = domain_sha256(
        PHASE17_PRODUCTS_MANIFEST_HASH_DOMAIN,
        tuple(item["product_sha256"] for item in payload["products"]),
    )
    payload["candidate_product_inventory_sha256"] = inventory_sha256

    first_step = payload["source_plan_steps"][0]
    output = first_step["produced_outputs"][0]
    output["sha256"] = inventory_sha256
    output["output_sha256"] = domain_sha256(
        PHASE17_OUTPUT_HASH_DOMAIN,
        {key: value for key, value in output.items() if key != "output_sha256"},
    )
    first_step["step_sha256"] = domain_sha256(
        PHASE17_STEP_HASH_DOMAIN,
        {key: value for key, value in first_step.items() if key != "step_sha256"},
    )
    payload["steps_manifest_sha256"] = domain_sha256(
        PHASE17_STEPS_MANIFEST_HASH_DOMAIN,
        tuple(item["step_sha256"] for item in payload["source_plan_steps"]),
    )
    payload["artifact_sha256"] = domain_sha256(
        PHASE17_ARTIFACT_HASH_DOMAIN,
        {key: value for key, value in payload.items() if key != "artifact_sha256"},
    )


def _rehash_product_manifest(payload: dict[str, Any]) -> None:
    inventory_sha256 = domain_sha256(
        PHASE17_PRODUCTS_MANIFEST_HASH_DOMAIN,
        tuple(item["product_sha256"] for item in payload["products"]),
    )
    payload["candidate_product_inventory_sha256"] = inventory_sha256
    output = payload["source_plan_steps"][0]["produced_outputs"][0]
    output["sha256"] = inventory_sha256
    output["output_sha256"] = domain_sha256(
        PHASE17_OUTPUT_HASH_DOMAIN,
        {key: value for key, value in output.items() if key != "output_sha256"},
    )
    _rehash_step_manifest(payload, 0)


def _rehash_candidate_manifest(payload: dict[str, Any], index: int) -> None:
    group = payload["candidate_groups"][index]
    group["candidate_group_sha256"] = domain_sha256(
        PHASE17_CANDIDATE_HASH_DOMAIN,
        {key: value for key, value in group.items() if key != "candidate_group_sha256"},
    )
    _rehash_candidate_groups_manifest(payload)


def _rehash_candidate_groups_manifest(payload: dict[str, Any]) -> None:
    payload["candidate_groups_manifest_sha256"] = domain_sha256(
        PHASE17_CANDIDATES_MANIFEST_HASH_DOMAIN,
        tuple(item["candidate_group_sha256"] for item in payload["candidate_groups"]),
    )
    _rehash_artifact(payload)


def _rehash_step_manifest(payload: dict[str, Any], index: int) -> None:
    step = payload["source_plan_steps"][index]
    step["step_sha256"] = domain_sha256(
        PHASE17_STEP_HASH_DOMAIN,
        {key: value for key, value in step.items() if key != "step_sha256"},
    )
    payload["steps_manifest_sha256"] = domain_sha256(
        PHASE17_STEPS_MANIFEST_HASH_DOMAIN,
        tuple(item["step_sha256"] for item in payload["source_plan_steps"]),
    )
    _rehash_artifact(payload)


def _rehash_artifact(payload: dict[str, Any]) -> None:
    payload["artifact_sha256"] = domain_sha256(
        PHASE17_ARTIFACT_HASH_DOMAIN,
        {key: value for key, value in payload.items() if key != "artifact_sha256"},
    )


def test_generator_is_repeatable_and_matches_builder_and_committed_artifact() -> None:
    first = _run(str(GENERATOR), "--confirm-metadata-only")
    second = _run(str(GENERATOR), "--confirm-metadata-only")
    expected = canonical_candidate_product_inventory_bytes()

    assert first.returncode == second.returncode == 0
    assert first.stderr == second.stderr == b""
    assert first.stdout == second.stdout == expected
    assert ARTIFACT.read_bytes() == expected


def test_offline_verifier_is_repeatable_and_emits_only_a_sanitized_receipt(
    tmp_path: Path,
) -> None:
    candidate = tmp_path / "inventory.json"
    candidate.write_bytes(canonical_candidate_product_inventory_bytes())

    first = _verify(candidate)
    second = _verify(candidate)
    payload = json.loads(canonical_candidate_product_inventory_bytes())

    assert first.returncode == second.returncode == 0
    assert first.stderr == second.stderr == b""
    assert first.stdout == second.stdout
    assert json.loads(first.stdout) == {
        "artifact_id": payload["artifact_id"],
        "artifact_sha256": payload["artifact_sha256"],
        "candidate_product_inventory_sha256": payload["candidate_product_inventory_sha256"],
        "network": "disabled",
        "outcome": "BLOCKED",
        "schema_version": "phase17-family-a-candidate-product-inventory-v1",
        "status": "valid",
    }
    rendered = first.stdout.lower()
    for forbidden in (b"credential", b"token", b"provider body", b"observation", b"price"):
        assert forbidden not in rendered


@pytest.mark.parametrize(
    ("collection", "index", "field", "value"),
    [
        ("products", 0, "official_name", "forged product"),
        ("products", 0, "official_documentation_url", "https://example.invalid/forged"),
        ("products", 0, "selected_for_independent_rights_review", False),
        ("products", 0, "operational_product_selected", True),
        ("products", 0, "rights_state", "PRESENT"),
        ("products", 0, "delivery_variant_state", "APPROVED"),
        ("candidate_groups", 0, "single_operational_selection", True),
        ("source_plan_steps", 0, "state", "NOT_STARTED"),
        ("source_plan_steps", 1, "state", "OUTPUT_FROZEN"),
        ("source_plan_steps", 1, "external_action_authorized", True),
    ],
)
def test_verifier_rejects_row_and_authority_tamper(
    tmp_path: Path,
    collection: str,
    index: int,
    field: str,
    value: object,
) -> None:
    payload = json.loads(canonical_candidate_product_inventory_bytes())
    payload[collection][index][field] = value
    candidate = tmp_path / "tampered.json"
    _write_canonical(candidate, payload)
    _assert_closed_failure(_verify(candidate))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("accepted_phase16_commit_sha", "0" * 40),
        ("accepted_phase16_tree_sha", "0" * 40),
        ("phase16_artifact_sha256", "0" * 64),
        ("phase16_policy_sha256", "0" * 64),
        ("phase16_steps_manifest_sha256", "0" * 64),
        ("phase16_step1_sha256", "0" * 64),
        ("phase16_gap_bindings_manifest_sha256", "0" * 64),
        ("outcome", "INVENTORY_FROZEN"),
        ("credentials_loaded", True),
        ("external_request_performed", True),
        ("provider_data_request_performed", True),
        ("entitlement_verification_performed", True),
        ("rights_verified", True),
        ("fitness_verified", True),
        ("licensed_data_persisted", True),
        ("research_data_eligible", True),
        ("research_executed", True),
        ("execution_authorized", True),
        ("order_submission_authorized", True),
        ("live_path_absent", False),
    ],
)
def test_verifier_rejects_identity_boundary_and_authority_tamper(
    tmp_path: Path, field: str, value: object
) -> None:
    payload = json.loads(canonical_candidate_product_inventory_bytes())
    payload[field] = value
    candidate = tmp_path / f"tampered-{field}.json"
    _write_canonical(candidate, payload)
    _assert_closed_failure(_verify(candidate))


def test_verifier_rejects_fully_rehashed_semantic_product_substitution(tmp_path: Path) -> None:
    payload = json.loads(canonical_candidate_product_inventory_bytes())
    payload["products"][8]["official_name"] = "Forged Liquidity Product"
    payload["products"][8]["official_documentation_url"] = "https://example.invalid/liquidity"
    _rehash_after_product_tamper(payload, 8)
    candidate = tmp_path / "rehashed-semantic-tamper.json"
    _write_canonical(candidate, payload)

    _assert_closed_failure(_verify(candidate))


def test_verifier_rejects_fully_rehashed_registry_and_step_tamper(tmp_path: Path) -> None:
    canonical = json.loads(canonical_candidate_product_inventory_bytes())
    cases: list[tuple[str, dict[str, Any]]] = []

    missing = copy.deepcopy(canonical)
    missing["products"].pop()
    _rehash_product_manifest(missing)
    cases.append(("missing-product", missing))

    duplicate = copy.deepcopy(canonical)
    duplicate["products"][-1] = copy.deepcopy(duplicate["products"][0])
    _rehash_product_manifest(duplicate)
    cases.append(("duplicate-product", duplicate))

    reordered = copy.deepcopy(canonical)
    reordered["products"][0], reordered["products"][1] = (
        reordered["products"][1],
        reordered["products"][0],
    )
    _rehash_product_manifest(reordered)
    cases.append(("reordered-products", reordered))

    unknown = copy.deepcopy(canonical)
    unknown["products"][0]["code"] = "UNKNOWN_PRODUCT"
    unknown["products"][0]["product_sha256"] = domain_sha256(
        PHASE17_PRODUCT_HASH_DOMAIN,
        {key: value for key, value in unknown["products"][0].items() if key != "product_sha256"},
    )
    _rehash_product_manifest(unknown)
    cases.append(("unknown-product", unknown))

    capability = copy.deepcopy(canonical)
    capability["products"][0]["capability_codes"] = ["macro_regime_inputs"]
    capability["products"][0]["product_sha256"] = domain_sha256(
        PHASE17_PRODUCT_HASH_DOMAIN,
        {key: value for key, value in capability["products"][0].items() if key != "product_sha256"},
    )
    _rehash_product_manifest(capability)
    cases.append(("cross-product-capability", capability))

    cross_group = copy.deepcopy(canonical)
    cross_group["candidate_groups"][1]["product_codes"] = [
        "LSEG_TICK_HISTORY_INSTRUMENT_AND_VENUE_WEB_API"
    ]
    _rehash_candidate_manifest(cross_group, 1)
    cases.append(("cross-row-candidate-group", cross_group))

    missing_group = copy.deepcopy(canonical)
    missing_group["candidate_groups"].pop()
    _rehash_candidate_groups_manifest(missing_group)
    cases.append(("missing-candidate-group", missing_group))

    duplicate_group = copy.deepcopy(canonical)
    duplicate_group["candidate_groups"][-1] = copy.deepcopy(duplicate_group["candidate_groups"][0])
    _rehash_candidate_groups_manifest(duplicate_group)
    cases.append(("duplicate-candidate-group", duplicate_group))

    reordered_groups = copy.deepcopy(canonical)
    reordered_groups["candidate_groups"][0], reordered_groups["candidate_groups"][1] = (
        reordered_groups["candidate_groups"][1],
        reordered_groups["candidate_groups"][0],
    )
    _rehash_candidate_groups_manifest(reordered_groups)
    cases.append(("reordered-candidate-groups", reordered_groups))

    unknown_group = copy.deepcopy(canonical)
    unknown_group["candidate_groups"][0]["phase16_candidate_code"] = "UNKNOWN_CANDIDATE"
    _rehash_candidate_manifest(unknown_group, 0)
    cases.append(("unknown-candidate-group", unknown_group))

    for label, field, value in (
        ("reason", "reason_code", "inventory_output_frozen_downstream_rights_review_required"),
        ("prerequisite", "prerequisite_codes", []),
        ("required-output", "required_outputs", ["forged_output_sha256"]),
        ("completed-later-step", "state", "OUTPUT_FROZEN"),
    ):
        step_tamper = copy.deepcopy(canonical)
        step_tamper["source_plan_steps"][1][field] = value
        _rehash_step_manifest(step_tamper, 1)
        cases.append((label, step_tamper))

    later_output = copy.deepcopy(canonical)
    later_output["source_plan_steps"][1]["produced_outputs"] = [
        copy.deepcopy(later_output["source_plan_steps"][0]["produced_outputs"][0])
    ]
    _rehash_step_manifest(later_output, 1)
    cases.append(("later-step-output", later_output))

    for label, payload in cases:
        candidate = tmp_path / f"{label}.json"
        _write_canonical(candidate, payload)
        _assert_closed_failure(_verify(candidate))


@pytest.mark.parametrize(
    "raw",
    [
        pytest.param(
            lambda original: b'{"schema_version":"forged",' + original[1:], id="duplicate-key"
        ),
        pytest.param(lambda original: b"\xef\xbb\xbf" + original, id="bom"),
        pytest.param(lambda original: b'{"forged":1.5,' + original[1:], id="float"),
        pytest.param(lambda original: b'{"forged":NaN,' + original[1:], id="nan"),
        pytest.param(lambda original: b'{"forged":Infinity,' + original[1:], id="infinity"),
        pytest.param(lambda _original: b"[]\n", id="non-object"),
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
    candidate.write_bytes(raw(canonical_candidate_product_inventory_bytes()))
    _assert_closed_failure(_verify(candidate))


def test_verifier_rejects_symlink_and_directory(tmp_path: Path) -> None:
    target = tmp_path / "target.json"
    target.write_bytes(canonical_candidate_product_inventory_bytes())
    directory = tmp_path / "directory"
    directory.mkdir()
    _assert_closed_failure(_verify(directory))

    link = tmp_path / "link.json"
    try:
        os.symlink(target, link)
    except OSError:
        pytest.skip("symlink creation is unavailable on this host")
    _assert_closed_failure(_verify(link))


def test_clis_reject_missing_extra_and_forbidden_arguments_without_canary_disclosure() -> None:
    canary = "phase17-secret-and-licensed-data-canary-do-not-emit"
    results = (
        (_run(str(GENERATOR)), GENERATOR_FAILURE),
        (
            _run(
                str(GENERATOR),
                "--confirm-metadata-only",
                "--confirm-metadata-only",
            ),
            GENERATOR_FAILURE,
        ),
        (
            _run(
                str(GENERATOR),
                "--confirm-metadata-only",
                "--provider",
                canary,
            ),
            GENERATOR_FAILURE,
        ),
        (_run(str(VERIFIER)), VERIFIER_FAILURE),
        (
            _run(
                str(VERIFIER),
                "--inventory",
                str(ARTIFACT),
                "--inventory",
                str(ARTIFACT),
            ),
            VERIFIER_FAILURE,
        ),
        (_run(str(VERIFIER), "--inventory", canary, "--repair"), VERIFIER_FAILURE),
        (
            _run(
                str(VERIFIER),
                "--inventory",
                canary,
                "--expected-hash",
                "0" * 64,
            ),
            VERIFIER_FAILURE,
        ),
    )
    for result, failure in results:
        assert result.returncode == 2
        assert result.stdout == b""
        assert result.stderr == failure
        assert canary.encode() not in result.stderr


@pytest.mark.parametrize(
    "module_name",
    [
        "scripts.generate_family_a_candidate_product_inventory",
        "scripts.verify_family_a_candidate_product_inventory",
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
    result = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout.splitlines() == [b"denied"]
    assert result.stderr == b""
