from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from fable5_data.phase18.canonical import (
    PHASE18_ARTIFACT_HASH_DOMAIN,
    PHASE18_CURRENTNESS_HASH_DOMAIN,
    PHASE18_FINDING_HASH_DOMAIN,
    PHASE18_OUTPUT_HASH_DOMAIN,
    PHASE18_REVIEW_MANIFEST_HASH_DOMAIN,
    PHASE18_SOURCE_HASH_DOMAIN,
    PHASE18_SOURCES_MANIFEST_HASH_DOMAIN,
    PHASE18_STEP_HASH_DOMAIN,
    PHASE18_STEPS_MANIFEST_HASH_DOMAIN,
    domain_sha256,
)
from fable5_data.phase18.rights_review import canonical_current_use_rights_review_bytes

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/PHASE_18_FAMILY_A_CURRENT_USE_RIGHTS_REVIEW.json"
GENERATOR = ROOT / "scripts/generate_family_a_current_use_rights_review.py"
VERIFIER = ROOT / "scripts/verify_family_a_current_use_rights_review.py"
GENERATOR_FAILURE = b"Family A current-use rights review generation failed.\n"
VERIFIER_FAILURE = b"Family A current-use rights review verification failed.\n"


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


def _write_canonical(path: Path, payload: object) -> None:
    path.write_bytes(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        + b"\n"
    )


def _verify(path: Path) -> subprocess.CompletedProcess[bytes]:
    return _run(str(VERIFIER), "--review", str(path))


def _assert_closed_failure(result: subprocess.CompletedProcess[bytes]) -> None:
    assert result.returncode == 2
    assert result.stdout == b""
    assert result.stderr == VERIFIER_FAILURE


def _rehash_output(output: dict[str, Any]) -> None:
    output["output_sha256"] = domain_sha256(
        PHASE18_OUTPUT_HASH_DOMAIN,
        {key: value for key, value in output.items() if key != "output_sha256"},
    )


def _rehash_step(payload: dict[str, Any], index: int) -> None:
    step = payload["source_plan_steps"][index]
    step["step_sha256"] = domain_sha256(
        PHASE18_STEP_HASH_DOMAIN,
        {key: value for key, value in step.items() if key != "step_sha256"},
    )
    payload["steps_manifest_sha256"] = domain_sha256(
        PHASE18_STEPS_MANIFEST_HASH_DOMAIN,
        tuple(item["step_sha256"] for item in payload["source_plan_steps"]),
    )
    _rehash_artifact(payload)


def _rehash_review_outputs(payload: dict[str, Any]) -> None:
    sources_manifest = domain_sha256(
        PHASE18_SOURCES_MANIFEST_HASH_DOMAIN,
        tuple(item["source_sha256"] for item in payload["terms_sources"]),
    )
    payload["terms_sources_manifest_sha256"] = sources_manifest
    review_hash = domain_sha256(
        PHASE18_REVIEW_MANIFEST_HASH_DOMAIN,
        {
            "terms_sources_manifest_sha256": sources_manifest,
            "finding_sha256s": tuple(
                item["finding_sha256"] for item in payload["product_rights_findings"]
            ),
        },
    )
    currentness_hash = domain_sha256(
        PHASE18_CURRENTNESS_HASH_DOMAIN,
        {
            "terms_sources_manifest_sha256": sources_manifest,
            "reviewed_at_utc": payload["frozen_at_utc"],
            "currentness": "REVIEW_SNAPSHOT_ONLY",
            "rights_currentness_guaranteed": False,
            "operational_use_cleared": False,
            "revalidation_required_before_external_action": True,
        },
    )
    payload["independent_rights_review_sha256"] = review_hash
    payload["rights_currentness_sha256"] = currentness_hash
    first, second = payload["source_plan_steps"][1]["produced_outputs"]
    first["sha256"] = review_hash
    second["sha256"] = currentness_hash
    _rehash_output(first)
    _rehash_output(second)
    _rehash_step(payload, 1)


def _rehash_source(payload: dict[str, Any], index: int) -> None:
    source = payload["terms_sources"][index]
    source["source_sha256"] = domain_sha256(
        PHASE18_SOURCE_HASH_DOMAIN,
        {key: value for key, value in source.items() if key != "source_sha256"},
    )
    _rehash_review_outputs(payload)


def _rehash_finding(payload: dict[str, Any], index: int) -> None:
    finding = payload["product_rights_findings"][index]
    finding["finding_sha256"] = domain_sha256(
        PHASE18_FINDING_HASH_DOMAIN,
        {key: value for key, value in finding.items() if key != "finding_sha256"},
    )
    _rehash_review_outputs(payload)


def _rehash_artifact(payload: dict[str, Any]) -> None:
    payload["artifact_sha256"] = domain_sha256(
        PHASE18_ARTIFACT_HASH_DOMAIN,
        {key: value for key, value in payload.items() if key != "artifact_sha256"},
    )


def test_generator_is_repeatable_and_matches_builder_and_committed_artifact() -> None:
    first = _run(str(GENERATOR), "--confirm-public-terms-review-only")
    second = _run(str(GENERATOR), "--confirm-public-terms-review-only")
    expected = canonical_current_use_rights_review_bytes()

    assert first.returncode == second.returncode == 0
    assert first.stderr == second.stderr == b""
    assert first.stdout == second.stdout == expected
    assert ARTIFACT.read_bytes() == expected


def test_offline_verifier_is_repeatable_and_emits_only_the_sanitized_receipt(
    tmp_path: Path,
) -> None:
    candidate = tmp_path / "review.json"
    candidate.write_bytes(canonical_current_use_rights_review_bytes())

    first = _verify(candidate)
    second = _verify(candidate)

    assert first.returncode == second.returncode == 0
    assert first.stderr == second.stderr == b""
    assert first.stdout == second.stdout
    assert json.loads(first.stdout) == {
        "aggregate_conclusion": "BLOCKED_NO_OPERATIONAL_SELECTION",
        "artifact_id": "7008240c-e7a2-5d4b-9345-8c40d2d4c359",
        "artifact_sha256": ("2def399ee8c57d7c6d80f5282e856eda1acf34a8504058fbfc8ea2dea4aa30ae"),
        "currentness": "review-snapshot-only",
        "independent_rights_review_sha256": (
            "a0c8808e865931cc88d9f71c578b42edcfb6e279e2426b4b30534d6c4626023b"
        ),
        "network": "disabled",
        "outcome": "BLOCKED",
        "rights_currentness_sha256": (
            "91b3b711e3c0b1b3b313e8ea45d9b73f96746ed4bd74478a7f6e7553510cdf63"
        ),
        "schema_version": "phase18-family-a-current-use-rights-review-v1",
        "status": "valid",
    }
    rendered = first.stdout.lower()
    for forbidden in (
        b"credential",
        b"token",
        b"account",
        b"provider body",
        b"terms body",
        b"official_url",
        b"conservative_fact",
    ):
        assert forbidden not in rendered


@pytest.mark.parametrize(
    ("collection", "index", "field", "value"),
    [
        ("terms_sources", 0, "official_title", "forged title"),
        ("terms_sources", 0, "official_url", "https://example.invalid/forged"),
        ("terms_sources", 0, "remote_source_response_body_persisted", True),
        ("terms_sources", 0, "source_content_bytes_captured", True),
        ("terms_sources", 0, "content_byte_authenticity_proven", True),
        ("product_rights_findings", 0, "storage", "ALLOWED_PUBLIC"),
        ("product_rights_findings", 0, "operational_use_cleared", True),
        ("product_rights_findings", 6, "revocation_currentness", "ALLOWED_PUBLIC"),
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
    payload = json.loads(canonical_current_use_rights_review_bytes())
    payload[collection][index][field] = value
    candidate = tmp_path / "tampered.json"
    _write_canonical(candidate, payload)
    _assert_closed_failure(_verify(candidate))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("accepted_phase17_commit_sha", "0" * 40),
        ("accepted_phase17_tree_sha", "0" * 40),
        ("phase17_artifact_sha256", "0" * 64),
        ("phase17_candidate_product_inventory_sha256", "0" * 64),
        ("phase16_step2_sha256", "0" * 64),
        ("outcome", "PASSED"),
        ("aggregate_conclusion", "RIGHTS_CLEARED"),
        ("operational_external_request_performed", True),
        ("provider_data_request_performed", True),
        ("provider_selected", True),
        ("product_selected", True),
        ("source_selected", True),
        ("credentials_loaded", True),
        ("entitlement_verified", True),
        ("rights_verified", True),
        ("rights_granted", True),
        ("fitness_verified", True),
        ("external_data_capture_authorized", True),
        ("provider_payload_persisted", True),
        ("licensed_data_persisted", True),
        ("research_ingestion_authorized", True),
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
    payload = json.loads(canonical_current_use_rights_review_bytes())
    payload[field] = value
    candidate = tmp_path / f"tampered-{field}.json"
    _write_canonical(candidate, payload)
    _assert_closed_failure(_verify(candidate))


def test_verifier_rejects_fully_rehashed_source_finding_and_semantic_inflation(
    tmp_path: Path,
) -> None:
    canonical = json.loads(canonical_current_use_rights_review_bytes())
    cases: list[tuple[str, dict[str, Any]]] = []

    source = copy.deepcopy(canonical)
    source["terms_sources"][0]["conservative_fact"] = "Forged operational permission."
    _rehash_source(source, 0)
    cases.append(("source", source))

    finding = copy.deepcopy(canonical)
    finding["product_rights_findings"][0]["storage"] = "ALLOWED_PUBLIC"
    finding["product_rights_findings"][0]["conclusion"] = (
        "RIGHTS_SUPPORTED_PUBLIC_POLICY_FITNESS_UNPROVEN"
    )
    _rehash_finding(finding, 0)
    cases.append(("finding", finding))

    sec_inflation = copy.deepcopy(canonical)
    sec_inflation["product_rights_findings"][6]["revocation_currentness"] = "ALLOWED_PUBLIC"
    sec_inflation["product_rights_findings"][6]["operational_use_cleared"] = True
    _rehash_finding(sec_inflation, 6)
    cases.append(("public-rights-inflation", sec_inflation))

    for label, payload in cases:
        candidate = tmp_path / f"rehashed-{label}.json"
        _write_canonical(candidate, payload)
        _assert_closed_failure(_verify(candidate))


def test_verifier_rejects_fully_rehashed_registry_and_step_tamper(tmp_path: Path) -> None:
    canonical = json.loads(canonical_current_use_rights_review_bytes())
    cases: list[tuple[str, dict[str, Any]]] = []

    missing_source = copy.deepcopy(canonical)
    missing_source["terms_sources"].pop()
    _rehash_review_outputs(missing_source)
    cases.append(("missing-source", missing_source))

    reordered_sources = copy.deepcopy(canonical)
    reordered_sources["terms_sources"][0], reordered_sources["terms_sources"][1] = (
        reordered_sources["terms_sources"][1],
        reordered_sources["terms_sources"][0],
    )
    _rehash_review_outputs(reordered_sources)
    cases.append(("reordered-sources", reordered_sources))

    duplicate_source = copy.deepcopy(canonical)
    duplicate_source["terms_sources"][-1] = copy.deepcopy(duplicate_source["terms_sources"][0])
    _rehash_review_outputs(duplicate_source)
    cases.append(("duplicate-source", duplicate_source))

    unknown_source = copy.deepcopy(canonical)
    unknown_source["terms_sources"][0]["code"] = "UNKNOWN_PUBLIC_TERMS_SOURCE"
    _rehash_source(unknown_source, 0)
    cases.append(("unknown-source", unknown_source))

    cross_source_applicability = copy.deepcopy(canonical)
    cross_source_applicability["terms_sources"][3]["applies_to_product_codes"] = [
        "LSEG_TICK_HISTORY_INSTRUMENT_AND_VENUE_WEB_API"
    ]
    _rehash_source(cross_source_applicability, 3)
    cases.append(("cross-source-applicability", cross_source_applicability))

    missing_finding = copy.deepcopy(canonical)
    missing_finding["product_rights_findings"].pop()
    _rehash_review_outputs(missing_finding)
    cases.append(("missing-finding", missing_finding))

    reordered_findings = copy.deepcopy(canonical)
    (
        reordered_findings["product_rights_findings"][0],
        reordered_findings["product_rights_findings"][1],
    ) = (
        reordered_findings["product_rights_findings"][1],
        reordered_findings["product_rights_findings"][0],
    )
    _rehash_review_outputs(reordered_findings)
    cases.append(("reordered-findings", reordered_findings))

    duplicate_finding = copy.deepcopy(canonical)
    duplicate_finding["product_rights_findings"][-1] = copy.deepcopy(
        duplicate_finding["product_rights_findings"][0]
    )
    _rehash_review_outputs(duplicate_finding)
    cases.append(("duplicate-finding", duplicate_finding))

    unknown_product = copy.deepcopy(canonical)
    unknown_product["product_rights_findings"][0]["product_code"] = "UNKNOWN_PRODUCT"
    _rehash_finding(unknown_product, 0)
    cases.append(("unknown-product", unknown_product))

    cross_product_sources = copy.deepcopy(canonical)
    cross_product_sources["product_rights_findings"][0]["source_codes"] = [
        "LSEG_TICK_HISTORY",
        "LSEG_DATA_REDISTRIBUTION",
        "LSEG_WEBSITE_TERMS",
        "LSEG_NONDISPLAY_DERIVED_GUIDANCE",
    ]
    _rehash_finding(cross_product_sources, 0)
    cases.append(("cross-product-source-codes", cross_product_sources))

    completed_later = copy.deepcopy(canonical)
    completed_later["source_plan_steps"][2]["state"] = "OUTPUT_FROZEN"
    _rehash_step(completed_later, 2)
    cases.append(("completed-later-step", completed_later))

    later_output = copy.deepcopy(canonical)
    later_output["source_plan_steps"][2]["produced_outputs"] = [
        copy.deepcopy(later_output["source_plan_steps"][1]["produced_outputs"][0])
    ]
    _rehash_step(later_output, 2)
    cases.append(("later-step-output", later_output))

    for label, payload in cases:
        candidate = tmp_path / f"{label}.json"
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
    candidate.write_bytes(raw(canonical_current_use_rights_review_bytes()))
    _assert_closed_failure(_verify(candidate))


def test_verifier_rejects_symlink_and_directory(tmp_path: Path) -> None:
    target = tmp_path / "target.json"
    target.write_bytes(canonical_current_use_rights_review_bytes())
    directory = tmp_path / "directory"
    directory.mkdir()
    _assert_closed_failure(_verify(directory))

    link = tmp_path / "link.json"
    try:
        os.symlink(target, link)
    except OSError:
        pytest.skip("symlink creation is unavailable on this host")
    _assert_closed_failure(_verify(link))


def test_verifier_rejects_a_pre_post_read_stability_change(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import scripts.verify_family_a_current_use_rights_review as verifier

    candidate = tmp_path / "review.json"
    candidate.write_bytes(canonical_current_use_rights_review_bytes())
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
    with pytest.raises(verifier._InvalidReview):
        verifier._read_review(str(candidate))
    assert calls == 2


def test_clis_reject_missing_extra_and_forbidden_arguments_without_canary_disclosure() -> None:
    canary = "phase18-secret-and-licensed-data-canary-do-not-emit"
    results = (
        (_run(str(GENERATOR)), GENERATOR_FAILURE),
        (
            _run(
                str(GENERATOR),
                "--confirm-public-terms-review-only",
                "--confirm-public-terms-review-only",
            ),
            GENERATOR_FAILURE,
        ),
        (
            _run(
                str(GENERATOR),
                "--confirm-public-terms-review-only",
                "--provider",
                canary,
            ),
            GENERATOR_FAILURE,
        ),
        (_run(str(VERIFIER)), VERIFIER_FAILURE),
        (
            _run(
                str(VERIFIER),
                "--review",
                str(ARTIFACT),
                "--review",
                str(ARTIFACT),
            ),
            VERIFIER_FAILURE,
        ),
        (_run(str(VERIFIER), "--review", canary, "--repair"), VERIFIER_FAILURE),
        (
            _run(
                str(VERIFIER),
                "--review",
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
        "scripts.generate_family_a_current_use_rights_review",
        "scripts.verify_family_a_current_use_rights_review",
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


def test_clis_ignore_ambient_environment_canaries() -> None:
    environment = os.environ.copy()
    canary = "phase18-ambient-secret-canary-do-not-emit"
    environment.update(
        {
            "FABLE5_PROVIDER_CREDENTIAL": canary,
            "FABLE5_DATABASE_URL": canary,
            "FABLE5_REVIEW_TIMESTAMP": "2099-01-01T00:00:00Z",
        }
    )
    generated = _run(
        str(GENERATOR),
        "--confirm-public-terms-review-only",
        environment=environment,
    )
    verified = _run(str(VERIFIER), "--review", str(ARTIFACT), environment=environment)

    assert generated.returncode == verified.returncode == 0
    assert generated.stdout == canonical_current_use_rights_review_bytes()
    assert verified.stderr == generated.stderr == b""
    assert canary.encode() not in generated.stdout
    assert canary.encode() not in verified.stdout
