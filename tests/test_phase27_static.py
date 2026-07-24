from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BASELINE_SHA = "b1ad522c666f472f02ad5995d8fa52e3413c2cac"
BASELINE_TREE = "d1b74532704708e97047e4abf704532102ba510a"
PHASE26_ARTIFACT = ROOT / "docs/PHASE_26_FAMILY_A_OPERATIONAL_DATA_COMPOSITION_DECISION.json"
PHASE26_ARTIFACT_FILE_SHA256 = "366206d2d0122e28ad95056765f840e3e12087ab1b29f17956f206ba27840175"
PHASE27_ARTIFACT = ROOT / "docs/PHASE_27_FAMILY_A_RIGHTS_AND_ENTITLEMENT_EVIDENCE_INTAKE.json"
PHASE27_ARTIFACT_ID = "6d3bc146-67ad-5aa1-8836-dd5130d8736e"
PHASE27_ARTIFACT_SHA256 = "9721a4e1ebf1024a9d11695c9144f54046954e012470c7ca6c715f32a714925e"
PHASE27_ARTIFACT_FILE_SHA256 = "b2525ad22c1a0f1569188a7aefa3d735da1903d098725a8346c762d7c0d4214b"
PHASE27_EVIDENCE_BUNDLE_ID = "63bc191d-03ef-54ae-afa6-599e4f287cfe"
PHASE27_EVIDENCE_BUNDLE_SHA256 = "f2d6a793e0208f57b4675f2efffe6de330a2ea9a8d895420c4011c3b12e02d14"
PHASE27_POLICY_SHA256 = "3792dffdf784c5354b973b0de3ecc6c5119cc97a67cdf065d2e826caede29505"
T009_BASELINE_SHA = "b887ed4c0a7552a784c4aeaf433aa4fb3e5569a4"
T009_BASELINE_TREE = "4dd37c02cdfb76ccb69564031656c7131a0de2b9"
T009_BASELINE_PARENT_SHA = BASELINE_SHA
T009_DOCUMENTATION_PATH = "docs/RIGHTS_EVIDENCE_REQUIREMENTS_FAMILY_A.md"
T009_DOCUMENTATION_FILE_SHA256 = "870227c6dd0fdeb0d8e38108db9eff841c4089fed241e289816c2ec5549bf7e8"
T009_DOCUMENTATION_OWNERSHIP_PATH_MANIFEST_SHA256 = (
    "59e91f3f005f7380f6925efc05286aa13169561e0b32dc1c46bb17a919d3cab6"
)
EXPECTED_T009_DOCUMENTATION_OWNERSHIP_PATHS = frozenset(
    {
        T009_DOCUMENTATION_PATH,
        "scripts/verify_phase1.py",
        "tests/test_phase27_static.py",
        "tests/test_repository_policy.py",
    }
)
T007_BASELINE_SHA = "1d8aa00f80fdd60b2b5ab3d431448de28a872c17"
T007_BASELINE_TREE = "d5e8ba303c03525aaa4cee65ddd090c858c2d2d6"
T007_BASELINE_PARENT_SHA = T009_BASELINE_SHA
T007_DOCUMENTATION_PATH = "docs/PLAN_SEC_EDGAR_QUALIFICATION.md"
T007_DOCUMENTATION_FILE_SHA256 = "255bd1777085416d13017d5cd16ff67ca453314930c7cd0e028c10c6b41bee91"
T007_DOCUMENTATION_OWNERSHIP_PATH_MANIFEST_SHA256 = (
    "0b3125a55780cb3f092a203968bd6e4f5f528cacdaeeca02e2dedeb78adf4049"
)
T007_DOCUMENTATION_CONFIG_SHA256 = (
    "cb3f9beae309cb346a76b626cb2c292189c6c4edb877d7f85f889c01b4201afd"
)
T007_DOCUMENTATION_ARTIFACT_ID = "ecdd57a5-a500-5cac-bd74-74848f6997b7"
EXPECTED_T007_DOCUMENTATION_OWNERSHIP_PATHS = frozenset(
    {
        T007_DOCUMENTATION_PATH,
        "scripts/verify_phase1.py",
        "tests/test_phase27_static.py",
        "tests/test_repository_policy.py",
    }
)
T010_BASELINE_SHA = "4180ce659aa621d6155cac1118f7011deb92aa9f"
T010_BASELINE_TREE = "1c50bd2569dc635c3e5662179ab276f6b971230c"
T010_BASELINE_PARENT_SHA = T007_BASELINE_SHA
T010_CLAUDE_BASELINE_FILE_SHA256 = (
    "d54d22a79595c2b911deb9248bcc17e4049dccd1524b85e044ed5a57ad4d64d9"
)
T010_CLAUDE_FILE_SHA256 = "f6b8a657be1596f2547ea9d6711a36bafd171243f8f194476a7acdb4557ca9f2"
T010_STATUS_TEST_FILE_SHA256 = "5ed0f5efc8e112623a716a5f2631b8b2c36de374894198c1065b1ec277b4e958"
T010_EXTERNAL_RULES_HEADING = b"# External observation and free-source rules"
T010_EXTERNAL_RULES_SHA256 = "dae3a082ef1c5427d63ab3c2732c0a0e2cc0fae57854d6ef3569d26a13c44b99"
T010_OWNERSHIP_PATH_MANIFEST_SHA256 = (
    "ebaf7434a43533aa1248b4c6f1b1c964026e7c53be24bcec3c6b4cd076a92247"
)
EXPECTED_T010_OWNERSHIP_PATHS = frozenset(
    {
        "CLAUDE.md",
        "scripts/verify_phase1.py",
        "tests/test_phase27_static.py",
        "tests/test_repository_policy.py",
        "tests/test_status_currency.py",
    }
)
EXPECTED_T007_DOCUMENTATION_URLS = frozenset(
    {
        "https://www.sec.gov/about/developer-resources",
        "https://www.sec.gov/about/privacy-information",
        "https://www.sec.gov/about/webmaster-frequently-asked-questions",
        "https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip",
        "https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip",
        "https://www.sec.gov/search-filings/edgar-application-programming-interfaces",
        "https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data",
    }
)
EXPECTED_PHASE27_ALLOWED_WRITES = frozenset(
    {
        ".github/workflows/ci.yml",
        "DEVELOPMENT.md",
        "Makefile",
        "README.md",
        "docs/COMPLIANCE_NOTES.md",
        "docs/DATA_SOURCES.md",
        "docs/EVALS.md",
        "docs/IMPLEMENTATION_PLAN.md",
        "docs/PHASE_27_FAMILY_A_RIGHTS_AND_ENTITLEMENT_EVIDENCE_INTAKE.json",
        "docs/PHASE_27_FAMILY_A_RIGHTS_AND_ENTITLEMENT_EVIDENCE_INTAKE_DECISIONS.md",
        "docs/RISK_POLICY.md",
        "docs/handoffs/PHASE_27.md",
        "scripts/check.ps1",
        "scripts/check.sh",
        "scripts/generate_family_a_rights_and_entitlement_evidence_intake.py",
        "scripts/verify_family_a_rights_and_entitlement_evidence_intake.py",
        "scripts/verify_phase1.py",
        "services/data/src/fable5_data/phase27/__init__.py",
        "services/data/src/fable5_data/phase27/canonical.py",
        "services/data/src/fable5_data/phase27/contracts.py",
        "services/data/src/fable5_data/phase27/package.py",
        "services/data/tests/test_phase27_contracts.py",
        "services/data/tests/test_phase27_package.py",
        "services/data/tests/test_phase27_security.py",
        "services/frontend/e2e/phase8.accessibility.spec.ts",
        "services/frontend/e2e/phase8.visual.spec.ts",
        "tests/test_phase10_static.py",
        "tests/test_phase11_static.py",
        "tests/test_phase12_static.py",
        "tests/test_phase13_static.py",
        "tests/test_phase14_static.py",
        "tests/test_phase15_static.py",
        "tests/test_phase16_static.py",
        "tests/test_phase17_static.py",
        "tests/test_phase18_static.py",
        "tests/test_phase19_static.py",
        "tests/test_phase20_static.py",
        "tests/test_phase21_static.py",
        "tests/test_phase22_static.py",
        "tests/test_phase23_static.py",
        "tests/test_phase24_static.py",
        "tests/test_phase25_static.py",
        "tests/test_phase27_portable.py",
        "tests/test_phase27_static.py",
        "tests/test_phase5_postgres.py",
        "tests/test_phase9_static.py",
        "tests/test_repository_policy.py",
    }
)


def normalized(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def verifier_module():
    spec = importlib.util.spec_from_file_location(
        "verify_phase1_phase27_static", ROOT / "scripts/verify_phase1.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def baseline_bytes(path: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"{BASELINE_SHA}:{path}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout


def test_phase27_baseline_parser_allowlist_and_inheritance_are_exact() -> None:
    verifier = verifier_module()
    assert verifier.PHASE_27_BASELINE_SHA == BASELINE_SHA
    assert verifier.EXPECTED_PHASE_27_BASELINE_TREE == BASELINE_TREE
    assert set(verifier.PHASE_27_REQUIRED_PATHS) <= verifier.PHASE_27_ALLOWED_WRITES
    assert verifier.PHASE_27_ALLOWED_WRITES == EXPECTED_PHASE27_ALLOWED_WRITES
    assert len(verifier.PHASE_27_ALLOWED_WRITES) == 47
    assert verifier.T009_DOCUMENTATION_BASELINE_SHA == T009_BASELINE_SHA
    assert verifier.EXPECTED_T009_DOCUMENTATION_BASELINE_TREE == T009_BASELINE_TREE
    assert verifier.T009_DOCUMENTATION_BASELINE_PARENT_SHA == T009_BASELINE_PARENT_SHA
    assert verifier.T009_DOCUMENTATION_PATH == T009_DOCUMENTATION_PATH
    assert (
        verifier.T009_DOCUMENTATION_OWNERSHIP_PATHS == EXPECTED_T009_DOCUMENTATION_OWNERSHIP_PATHS
    )
    assert verifier.T009_DOCUMENTATION_OVERLAY_PATHS == {T009_DOCUMENTATION_PATH}
    assert len(verifier.T009_DOCUMENTATION_OVERLAY_PATHS) == 1
    assert len(verifier.T009_DOCUMENTATION_MECHANISM_PATHS) == 3
    assert len(verifier.T009_DOCUMENTATION_OWNERSHIP_PATHS) == 4
    assert not (verifier.T009_DOCUMENTATION_OVERLAY_PATHS & verifier.PHASE_27_ALLOWED_WRITES)
    assert verifier.T009_DOCUMENTATION_MECHANISM_PATHS <= verifier.PHASE_27_ALLOWED_WRITES
    assert verifier.T007_DOCUMENTATION_BASELINE_SHA == T007_BASELINE_SHA
    assert verifier.EXPECTED_T007_DOCUMENTATION_BASELINE_TREE == T007_BASELINE_TREE
    assert verifier.T007_DOCUMENTATION_BASELINE_PARENT_SHA == T007_BASELINE_PARENT_SHA
    assert verifier.T007_DOCUMENTATION_PATH == T007_DOCUMENTATION_PATH
    assert (
        verifier.T007_DOCUMENTATION_OWNERSHIP_PATHS == EXPECTED_T007_DOCUMENTATION_OWNERSHIP_PATHS
    )
    assert verifier.T007_DOCUMENTATION_OVERLAY_PATHS == {T007_DOCUMENTATION_PATH}
    assert len(verifier.T007_DOCUMENTATION_OVERLAY_PATHS) == 1
    assert len(verifier.T007_DOCUMENTATION_MECHANISM_PATHS) == 3
    assert len(verifier.T007_DOCUMENTATION_OWNERSHIP_PATHS) == 4
    assert not (verifier.T007_DOCUMENTATION_OVERLAY_PATHS & verifier.PHASE_27_ALLOWED_WRITES)
    assert not (
        verifier.T007_DOCUMENTATION_OVERLAY_PATHS & verifier.T009_DOCUMENTATION_OVERLAY_PATHS
    )
    assert verifier.T007_DOCUMENTATION_MECHANISM_PATHS == (
        verifier.T009_DOCUMENTATION_MECHANISM_PATHS
    )
    assert verifier.T007_DOCUMENTATION_REQUIRED_URLS == EXPECTED_T007_DOCUMENTATION_URLS
    assert verifier.T010_STATUS_CURRENCY_BASELINE_SHA == T010_BASELINE_SHA
    assert verifier.EXPECTED_T010_STATUS_CURRENCY_BASELINE_TREE == T010_BASELINE_TREE
    assert verifier.T010_STATUS_CURRENCY_BASELINE_PARENT_SHA == T010_BASELINE_PARENT_SHA
    assert verifier.T010_STATUS_CURRENCY_OWNERSHIP_PATHS == EXPECTED_T010_OWNERSHIP_PATHS
    assert verifier.T010_STATUS_CURRENCY_OVERLAY_PATHS == {
        "CLAUDE.md",
        "tests/test_status_currency.py",
    }
    assert len(verifier.T010_STATUS_CURRENCY_OVERLAY_PATHS) == 2
    assert len(verifier.T010_STATUS_CURRENCY_MECHANISM_PATHS) == 3
    assert len(verifier.T010_STATUS_CURRENCY_OWNERSHIP_PATHS) == 5
    assert not (verifier.T010_STATUS_CURRENCY_OVERLAY_PATHS & verifier.PHASE_27_ALLOWED_WRITES)
    assert not (
        verifier.T010_STATUS_CURRENCY_OVERLAY_PATHS & verifier.T009_DOCUMENTATION_OVERLAY_PATHS
    )
    assert not (
        verifier.T010_STATUS_CURRENCY_OVERLAY_PATHS & verifier.T007_DOCUMENTATION_OVERLAY_PATHS
    )
    assert verifier.T010_STATUS_CURRENCY_MECHANISM_PATHS == (
        verifier.T007_DOCUMENTATION_MECHANISM_PATHS
    )
    assert verifier.PHASE_27_INHERITED_TABLES == verifier.PHASE_26_INHERITED_TABLES
    assert len(verifier.PHASE_27_INHERITED_TABLES) == 57
    assert [verifier.phase_number(str(value)) for value in range(1, 28)] == list(range(1, 28))
    for invalid in ("0", "28", "not-a-phase"):
        with pytest.raises(argparse.ArgumentTypeError):
            verifier.phase_number(invalid)
    assert (
        subprocess.run(
            ["git", "show", "-s", "--format=%T", BASELINE_SHA],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        == BASELINE_TREE
    )
    assert (
        subprocess.run(
            ["git", "show", "-s", "--format=%T", T009_BASELINE_SHA],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        == T009_BASELINE_TREE
    )
    assert (
        subprocess.run(
            ["git", "show", "-s", "--format=%P", T009_BASELINE_SHA],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        == T009_BASELINE_PARENT_SHA
    )
    assert (
        subprocess.run(
            ["git", "show", "-s", "--format=%T", T007_BASELINE_SHA],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        == T007_BASELINE_TREE
    )
    assert (
        subprocess.run(
            ["git", "show", "-s", "--format=%P", T007_BASELINE_SHA],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        == T007_BASELINE_PARENT_SHA
    )
    assert (
        subprocess.run(
            ["git", "show", "-s", "--format=%T", T010_BASELINE_SHA],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        == T010_BASELINE_TREE
    )
    assert (
        subprocess.run(
            ["git", "show", "-s", "--format=%P", T010_BASELINE_SHA],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        == T010_BASELINE_PARENT_SHA
    )


def test_phase27_changed_paths_stay_inside_the_exact_allowlist() -> None:
    verifier = verifier_module()
    changed: set[str] = set()
    for command in (
        ["git", "diff", "--name-only", BASELINE_SHA, "--"],
        ["git", "diff", "--cached", "--name-only", "--"],
        ["git", "ls-files", "--others", "--exclude-standard", "--"],
    ):
        result = subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)
        changed.update(path.replace("\\", "/") for path in result.stdout.splitlines() if path)
    assert not (
        changed
        - verifier.PHASE_27_ALLOWED_WRITES
        - verifier.T009_DOCUMENTATION_OVERLAY_PATHS
        - verifier.T007_DOCUMENTATION_OVERLAY_PATHS
        - verifier.T010_STATUS_CURRENCY_OVERLAY_PATHS
    )
    assert not verifier.PHASE_27_ALLOWED_WRITES - changed
    assert verifier.T009_DOCUMENTATION_OVERLAY_PATHS <= changed
    assert verifier.T007_DOCUMENTATION_OVERLAY_PATHS <= changed
    assert verifier.T010_STATUS_CURRENCY_OVERLAY_PATHS <= changed
    assert "services/api/live_order_submit.py" not in verifier.PHASE_27_ALLOWED_WRITES
    assert "docs/handoffs/PHASE_28.md" not in verifier.PHASE_27_ALLOWED_WRITES


def test_t009_documentation_ownership_is_exact_and_content_pinned() -> None:
    verifier = verifier_module()
    assert (
        verifier.T009_DOCUMENTATION_OWNERSHIP_PATH_MANIFEST_SHA256
        == T009_DOCUMENTATION_OWNERSHIP_PATH_MANIFEST_SHA256
    )
    assert (
        verifier.t009_documentation_path_manifest_sha256(
            verifier.T009_DOCUMENTATION_OWNERSHIP_PATHS
        )
        == T009_DOCUMENTATION_OWNERSHIP_PATH_MANIFEST_SHA256
    )
    changed: set[str] = set()
    for command in (
        ["git", "diff", "--name-only", T009_BASELINE_SHA, "--"],
        ["git", "diff", "--cached", "--name-only", "--"],
        ["git", "ls-files", "--others", "--exclude-standard", "--"],
    ):
        result = subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)
        changed.update(path.replace("\\", "/") for path in result.stdout.splitlines() if path)
    assert verifier.t009_documentation_ownership_delta(
        changed
        - verifier.T007_DOCUMENTATION_OVERLAY_PATHS
        - verifier.T010_STATUS_CURRENCY_OVERLAY_PATHS
    ) == (set(), set())
    document = ROOT / T009_DOCUMENTATION_PATH
    assert document.is_file()
    assert not document.is_symlink()
    assert verifier.T009_DOCUMENTATION_FILE_SHA256 == T009_DOCUMENTATION_FILE_SHA256
    raw = document.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == T009_DOCUMENTATION_FILE_SHA256
    assert hashlib.sha256(raw + b"\n").hexdigest() != T009_DOCUMENTATION_FILE_SHA256
    assert PHASE27_ARTIFACT.relative_to(ROOT).as_posix() not in (
        verifier.T009_DOCUMENTATION_OWNERSHIP_PATHS
    )
    accepted_phase27_artifact = subprocess.run(
        ["git", "show", f"{T009_BASELINE_SHA}:{PHASE27_ARTIFACT.relative_to(ROOT).as_posix()}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout
    assert PHASE27_ARTIFACT.read_bytes() == accepted_phase27_artifact


def test_t009_documentation_ownership_rejects_missing_and_prohibited_paths() -> None:
    verifier = verifier_module()
    missing = set(verifier.T009_DOCUMENTATION_OWNERSHIP_PATHS) - {T009_DOCUMENTATION_PATH}
    assert verifier.t009_documentation_ownership_delta(missing) == (
        {T009_DOCUMENTATION_PATH},
        set(),
    )
    live_path = "services/api/live_order_submit.py"
    planted = set(verifier.T009_DOCUMENTATION_OWNERSHIP_PATHS) | {live_path}
    assert verifier.t009_documentation_ownership_delta(planted) == (
        set(),
        {live_path},
    )
    second_doc = "docs/T009_UNOWNED_COMPANION.md"
    planted.add(second_doc)
    assert verifier.t009_documentation_ownership_delta(planted) == (
        set(),
        {live_path, second_doc},
    )
    phase28_path = "docs/handoffs/PHASE_28.md"
    planted.add(phase28_path)
    assert verifier.t009_documentation_ownership_delta(planted) == (
        set(),
        {live_path, phase28_path, second_doc},
    )


def test_t009_documentation_rejects_external_action_and_positive_authority_canaries() -> None:
    verifier = verifier_module()
    document = (ROOT / T009_DOCUMENTATION_PATH).read_text(encoding="utf-8")
    assert verifier.t009_documentation_prohibited_findings(document) == set()
    canaries = (
        ("external-url", "https://provider.invalid/rights"),
        ("external-email", "mailto:rights@example.invalid"),
        ("network-command", "Invoke-WebRequest provider.invalid"),
        ("network-call", "requests.get(provider_url)"),
        ("credential-assignment", "$env:FABLE5_API_KEY = 'canary'"),
        ("http-mutation", "POST /v1/orders"),
        ("positive-authority", "outcome: PASS"),
        ("positive-authority", "outcome: READY"),
        ("positive-authority", "verified_evidence_recorded: true"),
        ("positive-authority", "acquisition_authorized: true"),
        (
            "positive-authority",
            "current_rights_evidence_for_exact_composition: true",
        ),
    )
    for expected, canary in canaries:
        assert verifier.t009_documentation_prohibited_findings(canary) == {expected}


def test_t007_documentation_ownership_is_exact_and_content_pinned() -> None:
    verifier = verifier_module()
    assert (
        verifier.T007_DOCUMENTATION_OWNERSHIP_PATH_MANIFEST_SHA256
        == T007_DOCUMENTATION_OWNERSHIP_PATH_MANIFEST_SHA256
    )
    assert (
        verifier.t007_documentation_path_manifest_sha256(
            verifier.T007_DOCUMENTATION_OWNERSHIP_PATHS
        )
        == T007_DOCUMENTATION_OWNERSHIP_PATH_MANIFEST_SHA256
    )
    changed: set[str] = set()
    for command in (
        ["git", "diff", "--name-only", T007_BASELINE_SHA, "--"],
        ["git", "diff", "--cached", "--name-only", "--"],
        ["git", "ls-files", "--others", "--exclude-standard", "--"],
    ):
        result = subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)
        changed.update(path.replace("\\", "/") for path in result.stdout.splitlines() if path)
    assert verifier.t007_documentation_ownership_delta(
        changed - verifier.T010_STATUS_CURRENCY_OVERLAY_PATHS
    ) == (set(), set())
    document = ROOT / T007_DOCUMENTATION_PATH
    assert document.is_file()
    assert not document.is_symlink()
    assert verifier.T007_DOCUMENTATION_FILE_SHA256 == T007_DOCUMENTATION_FILE_SHA256
    raw = document.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == T007_DOCUMENTATION_FILE_SHA256
    assert hashlib.sha256(raw + b"\n").hexdigest() != T007_DOCUMENTATION_FILE_SHA256
    assert verifier.t007_documentation_config_sha256() == T007_DOCUMENTATION_CONFIG_SHA256
    assert verifier.T007_DOCUMENTATION_CONFIG_SHA256 == T007_DOCUMENTATION_CONFIG_SHA256
    assert verifier.t007_documentation_artifact_id() == T007_DOCUMENTATION_ARTIFACT_ID
    assert verifier.T007_DOCUMENTATION_ARTIFACT_ID == T007_DOCUMENTATION_ARTIFACT_ID
    source = raw.decode("utf-8")
    expected_config_block = (
        "```json\n"
        + json.dumps(
            verifier.T007_DOCUMENTATION_CONFIG,
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )
        + "\n```"
    )
    assert expected_config_block in source
    assert f"`{T007_DOCUMENTATION_CONFIG_SHA256}`" in source
    assert f"`{T007_DOCUMENTATION_ARTIFACT_ID}`" in source
    assert PHASE27_ARTIFACT.relative_to(ROOT).as_posix() not in (
        verifier.T007_DOCUMENTATION_OWNERSHIP_PATHS
    )
    assert T009_DOCUMENTATION_PATH not in verifier.T007_DOCUMENTATION_OWNERSHIP_PATHS
    accepted_phase27_artifact = subprocess.run(
        ["git", "show", f"{T007_BASELINE_SHA}:{PHASE27_ARTIFACT.relative_to(ROOT).as_posix()}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout
    assert PHASE27_ARTIFACT.read_bytes() == accepted_phase27_artifact
    accepted_t009_document = subprocess.run(
        ["git", "show", f"{T007_BASELINE_SHA}:{T009_DOCUMENTATION_PATH}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout
    assert (ROOT / T009_DOCUMENTATION_PATH).read_bytes() == accepted_t009_document


def test_t007_historical_retrieval_metadata_is_unverified_sanitized_and_exact() -> None:
    source = (ROOT / T007_DOCUMENTATION_PATH).read_text(encoding="utf-8")
    normalized_source = " ".join(source.split())
    for required_literal in (
        "## Operator-supplied historical assistant retrieval metadata (2026-07-23 18:12 UTC)",
        "An operator-supplied working note reports",
        "unverified historical context",
        "This subsection records **sanitized retrieval metadata**",
        "No response body or page-content hash is persisted here",
        "The reported observations are **not** independent verification",
        "raw contact details and contact-derived identifiers are intentionally excluded",
        "Raw response bodies must never be persisted or committed.",
        "unverified working-note hashes must not be promoted as evidence",
        "T-007 records and authorizes no bulk, archive, filing, or EDGAR data-API request",
    ):
        assert required_literal in normalized_source
    for prohibited_literal in (
        "Agent independent re-retrieval",
        "**timestamps only**",
        "No page body, no new content hash",
        "28cc20d265e1d4e66956f3171928fe18c7b494cba0e7c11714c0a810832eb1b7",
        "No request, download, archive",
        "content hashes for this re-retrieval exist only",
    ):
        assert prohibited_literal not in normalized_source
    assert re.findall(
        r"^\| S[1-5] \| `([^`]+)` \| `(2026-07-23T18:12:[^`]+Z)` \| 200 \|$",
        source,
        re.MULTILINE,
    ) == [
        ("SEC_PRIVACY_AND_DISSEMINATION", "2026-07-23T18:12:10.935359Z"),
        ("SEC_WEBMASTER_REUSE_FAQ", "2026-07-23T18:12:12.746169Z"),
        ("SEC_EDGAR_APIS", "2026-07-23T18:12:14.577776Z"),
        ("SEC_DEVELOPER_RESOURCES", "2026-07-23T18:12:16.395838Z"),
        ("SEC_ACCESSING_EDGAR", "2026-07-23T18:12:18.425454Z"),
    ]


def test_t007_documentation_ownership_rejects_missing_and_prohibited_paths() -> None:
    verifier = verifier_module()
    missing = set(verifier.T007_DOCUMENTATION_OWNERSHIP_PATHS) - {T007_DOCUMENTATION_PATH}
    assert verifier.t007_documentation_ownership_delta(missing) == (
        {T007_DOCUMENTATION_PATH},
        set(),
    )
    live_path = "services/api/live_order_submit.py"
    planted = set(verifier.T007_DOCUMENTATION_OWNERSHIP_PATHS) | {live_path}
    assert verifier.t007_documentation_ownership_delta(planted) == (
        set(),
        {live_path},
    )
    second_doc = "docs/T007_UNOWNED_COMPANION.md"
    planted.add(second_doc)
    assert verifier.t007_documentation_ownership_delta(planted) == (
        set(),
        {live_path, second_doc},
    )
    phase28_path = "docs/handoffs/PHASE_28.md"
    planted.add(phase28_path)
    assert verifier.t007_documentation_ownership_delta(planted) == (
        set(),
        {live_path, phase28_path, second_doc},
    )


def test_t010_status_currency_ownership_and_content_are_exact() -> None:
    verifier = verifier_module()
    assert (
        verifier.T010_STATUS_CURRENCY_OWNERSHIP_PATH_MANIFEST_SHA256
        == T010_OWNERSHIP_PATH_MANIFEST_SHA256
    )
    assert (
        verifier.t010_status_currency_path_manifest_sha256(
            verifier.T010_STATUS_CURRENCY_OWNERSHIP_PATHS
        )
        == T010_OWNERSHIP_PATH_MANIFEST_SHA256
    )
    changed: set[str] = set()
    for command in (
        ["git", "diff", "--name-only", T010_BASELINE_SHA, "--"],
        ["git", "diff", "--cached", "--name-only", "--"],
        ["git", "ls-files", "--others", "--exclude-standard", "--"],
    ):
        result = subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)
        changed.update(path.replace("\\", "/") for path in result.stdout.splitlines() if path)
    assert verifier.t010_status_currency_ownership_delta(changed) == (set(), set())
    assert changed == EXPECTED_T010_OWNERSHIP_PATHS

    claude = ROOT / "CLAUDE.md"
    status_test = ROOT / "tests/test_status_currency.py"
    for path in (claude, status_test):
        assert path.is_file()
        assert not path.is_symlink()
    assert verifier.T010_CLAUDE_BASELINE_FILE_SHA256 == T010_CLAUDE_BASELINE_FILE_SHA256
    assert verifier.T010_CLAUDE_FILE_SHA256 == T010_CLAUDE_FILE_SHA256
    assert verifier.T010_STATUS_TEST_FILE_SHA256 == T010_STATUS_TEST_FILE_SHA256
    assert hashlib.sha256(claude.read_bytes()).hexdigest() == T010_CLAUDE_FILE_SHA256
    assert hashlib.sha256(status_test.read_bytes()).hexdigest() == T010_STATUS_TEST_FILE_SHA256

    accepted_claude = subprocess.run(
        ["git", "show", f"{T010_BASELINE_SHA}:CLAUDE.md"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout
    assert hashlib.sha256(accepted_claude).hexdigest() == T010_CLAUDE_BASELINE_FILE_SHA256
    external_rules = verifier.t010_external_rules_section((ROOT / "AGENTS.md").read_bytes())
    assert external_rules.startswith(T010_EXTERNAL_RULES_HEADING)
    assert hashlib.sha256(external_rules).hexdigest() == T010_EXTERNAL_RULES_SHA256
    assert claude.read_bytes() == accepted_claude + external_rules

    for preserved in (
        PHASE27_ARTIFACT.relative_to(ROOT).as_posix(),
        T009_DOCUMENTATION_PATH,
        T007_DOCUMENTATION_PATH,
    ):
        accepted = subprocess.run(
            ["git", "show", f"{T010_BASELINE_SHA}:{preserved}"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout
        assert (ROOT / preserved).read_bytes() == accepted


def test_t010_status_currency_ownership_rejects_missing_extra_live_and_phase28_paths() -> None:
    verifier = verifier_module()
    missing = set(verifier.T010_STATUS_CURRENCY_OWNERSHIP_PATHS) - {"tests/test_status_currency.py"}
    assert verifier.t010_status_currency_ownership_delta(missing) == (
        {"tests/test_status_currency.py"},
        set(),
    )

    planted = set(verifier.T010_STATUS_CURRENCY_OWNERSHIP_PATHS)
    extra_path = "README.md"
    planted.add(extra_path)
    assert verifier.t010_status_currency_ownership_delta(planted) == (
        set(),
        {extra_path},
    )

    live_order_path = "services/api/live_order_submit.py"
    planted.add(live_order_path)
    assert verifier.t010_status_currency_ownership_delta(planted) == (
        set(),
        {extra_path, live_order_path},
    )

    phase28_path = "docs/handoffs/PHASE_28.md"
    planted.add(phase28_path)
    assert verifier.t010_status_currency_ownership_delta(planted) == (
        set(),
        {extra_path, live_order_path, phase28_path},
    )


def test_t007_documentation_allows_only_exact_sec_citations_and_rejects_action_canaries() -> None:
    verifier = verifier_module()
    document = (ROOT / T007_DOCUMENTATION_PATH).read_text(encoding="utf-8")
    assert verifier.t007_documentation_prohibited_findings(document) == set()
    assert verifier.t007_documentation_urls(document) == EXPECTED_T007_DOCUMENTATION_URLS
    allowed_url = next(iter(EXPECTED_T007_DOCUMENTATION_URLS))
    assert verifier.t007_documentation_urls(f"<{allowed_url}>") == {allowed_url}
    removed_url = next(iter(EXPECTED_T007_DOCUMENTATION_URLS))
    assert verifier.t007_documentation_prohibited_findings(
        document.replace(removed_url, "REMOVED_REQUIRED_URL", 1)
    ) == {"missing-required-url"}
    canaries = (
        ("external-url", "https://provider.invalid/archive.zip"),
        ("external-url", "http://provider.invalid/archive.zip"),
        ("external-url", "[archive](//provider.invalid/archive.zip)"),
        ("external-url", "https://www.sec.gov/unowned-surface"),
        ("external-email", "mailto:admin@example.invalid"),
        ("network-command", "Invoke-WebRequest https://www.sec.gov/about/developer-resources"),
        ("network-command", "iwr https://www.sec.gov/about/developer-resources"),
        ("network-call", "requests.get(policy_url)"),
        ("network-call", "urllib.request.urlopen(policy_url)"),
        ("credential-assignment", "$env:FABLE5_SEC_API_KEY = 'canary'"),
        ("credential-assignment", "FABLE5_SEC_API_KEY: canary"),
        ("http-mutation", "POST /v1/orders"),
        ("positive-authority", "outcome: PASS"),
        ("positive-authority", "- outcome: PASS"),
        ("positive-authority", "verified_evidence_recorded: true"),
        ("positive-authority", "acquisition_authorized: true"),
        ("positive-authority", "| acquisition_authorized: true |"),
        ("positive-authority", "exact_schema_qualified: true"),
        ("positive-authority", "point_in_time_qualified: true"),
        ("positive-authority", "execution_authorized: true"),
        ("positive-authority", "order_submission_authorized: true"),
        ("positive-authority", "live_path_absent: false"),
        ("positive-authority", "paper_only: false"),
    )
    for expected, canary in canaries:
        findings = verifier.t007_documentation_prohibited_findings(f"{document}\n{canary}")
        assert expected in findings


def test_phase27_freezes_phase26_and_all_but_the_governance_overlay_delta() -> None:
    verifier = verifier_module()
    assert hashlib.sha256(PHASE26_ARTIFACT.read_bytes()).hexdigest() == (
        PHASE26_ARTIFACT_FILE_SHA256
    )
    assert PHASE26_ARTIFACT.read_bytes() == baseline_bytes(
        PHASE26_ARTIFACT.relative_to(ROOT).as_posix()
    )
    assert verifier.PHASE_26_MAINTENANCE_OVERLAY_PATHS & verifier.PHASE_27_ALLOWED_WRITES == {
        "DEVELOPMENT.md"
    }
    for relative in verifier.PHASE_26_MAINTENANCE_OVERLAY_PATHS - {"DEVELOPMENT.md"}:
        assert (ROOT / relative).read_bytes() == baseline_bytes(relative)
    planted = set(verifier.PHASE_27_ALLOWED_WRITES) | {
        "services/frontend/src/app/paper/readiness/order-submit.ts"
    }
    assert planted - verifier.PHASE_27_ALLOWED_WRITES == {
        "services/frontend/src/app/paper/readiness/order-submit.ts"
    }


def test_phase27_artifact_is_canonical_blocked_and_has_zero_operational_authority() -> None:
    from fable5_data.phase27 import canonical as c
    from fable5_data.phase27.contracts import Phase27RightsEntitlementEvidencePackage
    from fable5_data.phase27.package import (
        build_phase27_package,
        canonical_phase27_package_bytes,
    )

    raw = PHASE27_ARTIFACT.read_bytes()
    artifact = Phase27RightsEntitlementEvidencePackage.model_validate_json(raw, strict=True)
    assert raw == canonical_phase27_package_bytes()
    assert hashlib.sha256(raw).hexdigest() == PHASE27_ARTIFACT_FILE_SHA256
    assert artifact == build_phase27_package()
    assert str(artifact.artifact_id) == PHASE27_ARTIFACT_ID
    assert artifact.artifact_sha256 == PHASE27_ARTIFACT_SHA256
    assert str(artifact.evidence_bundle_id) == PHASE27_EVIDENCE_BUNDLE_ID
    assert artifact.evidence_bundle_sha256 == PHASE27_EVIDENCE_BUNDLE_SHA256
    assert artifact.policy_sha256 == PHASE27_POLICY_SHA256
    assert artifact.composition_id == "FAMILY_A_CRSP_SEC_RTDSM_V1"
    assert artifact.outcome.value == "BLOCKED"
    assert artifact.determination.value == "COMPOSITION_RIGHTS_ENTITLEMENT_EVIDENCE_MISSING"
    assert not artifact.verified_evidence_recorded
    assert not artifact.current_rights_evidence_for_exact_composition
    payload = artifact.model_dump(mode="python")
    assert all(payload[name] is expected for name, expected in c.BOUNDARY_VALUES.items())


def test_phase27_full_compose_reaches_every_inherited_acceptance_guard() -> None:
    source = normalized(ROOT / "scripts/verify_phase1.py")
    guarded_actions = (
        (8, r"verify_phase8_browser\("),
        (10, r'with phase9_stage\(phase, "phase10_acceptance"\)'),
        (11, r'with phase9_stage\(phase, "phase11_acceptance"\)'),
        (12, r'with phase9_stage\(phase, "phase12_acceptance"\)'),
        (13, r'with phase9_stage\(phase, "phase13_acceptance"\)'),
        (14, r'with phase9_stage\(phase, "phase14_acceptance"\)'),
    )
    for first_phase, action in guarded_actions:
        match = re.search(
            rf"if phase in \{{(?P<phases>[^}}]+)\}}:\s*{action}",
            source,
        )
        assert match is not None
        assert {int(value) for value in re.findall(r"\d+", match.group("phases"))} == (
            set(range(first_phase, 26)) | {27}
        )


def test_phase27_linux_phase8_inheritance_uses_the_pinned_container(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    verifier = verifier_module()
    captured: list[tuple[list[str], dict[str, str]]] = []
    cleaned: list[str] = []
    monkeypatch.setattr(verifier.sys, "platform", "linux")
    monkeypatch.setattr(verifier.shutil, "which", lambda _: "/usr/bin/npm")
    monkeypatch.setattr(
        verifier,
        "snapshot_tables",
        lambda project, environment, tables: {"stable": (1, "a" * 64)},
    )
    monkeypatch.setattr(
        verifier,
        "run",
        lambda command, *, env: captured.append((command, env.copy())),
    )
    monkeypatch.setattr(
        verifier,
        "cleanup_phase11_linux_playwright_container",
        lambda project, environment: cleaned.append(project),
    )

    environment = {"FABLE5_VERIFY_PHASE": "27"}
    verifier.verify_phase8_browser(
        "phase27-inherited",
        environment,
        "http://127.0.0.1:3000",
    )

    command, command_environment = captured[-1]
    assert command[:2] == ["docker", "run"]
    assert command.count(verifier.PHASE_9_LINUX_PLAYWRIGHT_IMAGE) == 1
    assert command.count("FABLE5_VERIFY_PHASE=27") == 1
    assert command.count("e2e/phase8.accessibility.spec.ts") == 1
    assert command.count("e2e/phase8.visual.spec.ts") == 1
    assert command[command.index("--mount") + 1].endswith(",readonly")
    assert command_environment["FABLE5_VERIFY_PHASE"] == "27"
    assert cleaned == ["phase27-inherited"]


def test_phase27_domain_and_clis_are_offline_clockless_and_sanitized() -> None:
    domain = ROOT / "services/data/src/fable5_data/phase27"
    imported: set[str] = set()
    for path in domain.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".", 1)[0])
    assert not imported & {
        "aiohttp",
        "asyncio",
        "fastapi",
        "httpx",
        "os",
        "psycopg",
        "requests",
        "socket",
        "sqlalchemy",
        "subprocess",
        "urllib",
        "yfinance",
    }
    domain_source = "\n".join(normalized(path) for path in domain.glob("*.py"))
    for forbidden in ("datetime.now", "datetime.utcnow", "date.today"):
        assert forbidden not in domain_source

    generator = normalized(
        ROOT / "scripts/generate_family_a_rights_and_entitlement_evidence_intake.py"
    )
    portable = normalized(
        ROOT / "scripts/verify_family_a_rights_and_entitlement_evidence_intake.py"
    )
    for source in (generator, portable):
        assert 'event.startswith("socket.")' in source
        assert 'frozenset({"os.system", "subprocess.Popen"})' in source
        assert source.count("subprocess.Popen(") == 1
        assert "subprocess.run(" not in source
        main = source.index("def main")
        parse = source.index("_parser().parse_args", main)
        assert source.index("sys.addaudithook(_offline_audit_hook)", main) < parse
        assert source.index("_prove_offline_boundary()", main) < parse
    for denied in (
        '"body"',
        '"header"',
        '"credential"',
        '"secret"',
        '"token"',
        '"cookie"',
        '"raw_account"',
        '"raw_entitlement"',
    ):
        assert denied in generator


def test_phase27_active_dispatch_ci_wrappers_and_phase28_stop_are_exact() -> None:
    verifier = normalized(ROOT / "scripts/verify_phase1.py")
    for required in (
        "def verify_phase27_static()",
        "verify_phase27_static()",
        'default=os.environ.get("FABLE5_VERIFY_PHASE", "27")',
        'print("Static repository policy checks passed for Phase 27.")',
        'print("Full Compose Phase 27 verification passed.")',
    ):
        assert required in verifier
    workflow = normalized(ROOT / ".github/workflows/ci.yml")
    assert workflow.startswith("name: phase-27-ci\n")
    assert 'FABLE5_VERIFY_PHASE: "27"' in workflow
    assert "phase27-compose:" in workflow
    assert workflow.count("python scripts/verify_phase1.py --static-only --phase 27") == 1
    assert workflow.count("python scripts/verify_phase1.py --phase 27") == 1
    assert "secrets." not in workflow
    for entrypoint in ("scripts/check.ps1", "scripts/check.sh", "Makefile"):
        source = normalized(ROOT / entrypoint)
        assert "FABLE5_VERIFY_PHASE" in source and "--phase" in source
        assert "25, 26, or 27" in source
    for path in (
        ROOT / "services/frontend/e2e/phase8.accessibility.spec.ts",
        ROOT / "services/frontend/e2e/phase8.visual.spec.ts",
    ):
        source = normalized(path)
        assert 'process.env.FABLE5_VERIFY_PHASE ?? "27"' in source
        assert '"27",' in source
    assert not (ROOT / "docs/handoffs/PHASE_28.md").exists()
    assert not (ROOT / "services/data/src/fable5_data/phase28").exists()
