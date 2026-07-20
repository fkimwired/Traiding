from __future__ import annotations

import argparse
import importlib.util
import inspect
import json
from pathlib import Path
from types import ModuleType

import pytest
from fable5_data.phase16.plan import (
    build_family_a_point_in_time_source_plan,
    canonical_source_plan_bytes,
)

ROOT = Path(__file__).resolve().parents[1]
BASELINE_SHA = "5b3052eb8f020d77cc3750b34190b4b2fa5fc16c"
BASELINE_TREE = "7fab5a2b2eb2f8f821b969d9cb031c806e064d28"
ARTIFACT_PATH = "docs/PHASE_16_FAMILY_A_POINT_IN_TIME_SOURCE_PLAN.json"
REQUIREMENT_CODES = (
    "PHASE15_ADMISSION_SPECIFICATION_BOUND",
    "FAMILY_A_CAPABILITY_SET_BOUND",
    "SECURITY_MASTER_IDENTITY_HISTORY_REQUIRED",
    "UNIVERSE_MEMBERSHIP_DELISTING_HISTORY_REQUIRED",
    "RAW_OHLCV_CORPORATE_ACTION_HISTORY_REQUIRED",
    "AS_REPORTED_FUNDAMENTAL_VINTAGES_REQUIRED",
    "SECTOR_LIQUIDITY_HISTORY_REQUIRED",
    "MACRO_VINTAGE_RELEASE_HISTORY_REQUIRED",
    "TEMPORAL_REVISION_COVERAGE_MANIFEST_REQUIRED",
    "INDEPENDENT_RIGHTS_CURRENTNESS_REVIEW_REQUIRED",
    "QUARANTINE_CANONICALIZATION_RECONCILIATION_REQUIRED",
    "CAPTURE_INGESTION_RESEARCH_EXECUTION_AUTHORITY_ABSENT",
)
CAPABILITY_CODES = (
    "security_master",
    "universe_membership",
    "ohlcv",
    "corporate_actions",
    "delistings",
    "as_reported_fundamentals",
    "macro_regime_inputs",
)
CANDIDATE_ROWS = (
    ("TIINGO_PHASE13_BOUNDED_CANDIDATE", "UNPROVEN"),
    ("MORNINGSTAR_CRSP_US_STOCK_DATABASES_CANDIDATE", "UNPROVEN"),
    ("MORNINGSTAR_CRSP_COMPUSTAT_MERGED_DATABASE_CANDIDATE", "UNPROVEN"),
    ("SEC_EDGAR_SUBMISSIONS_XBRL_CANDIDATE", "UNPROVEN"),
    ("FEDERAL_RESERVE_ALFRED_VINTAGES_CANDIDATE", "UNPROVEN"),
    ("HISTORICAL_LIQUIDITY_PRODUCT_UNSELECTED", "MISSING"),
)
STEP_CODES = (
    "SELECT_CANDIDATE_PRODUCTS",
    "REVIEW_CURRENT_USE_RIGHTS",
    "QUALIFY_BOUNDED_READ_ONLY_SAMPLES",
    "PRODUCE_FULL_HISTORY_COVERAGE_MANIFEST",
    "RECONCILE_TEMPORAL_IDENTITY_REVISION_SEMANTICS",
    "DESIGN_LOCAL_QUARANTINE_AND_CANONICAL_SNAPSHOT",
    "REQUEST_SEPARATE_INGESTION_AUTHORITY",
)
GAP_CODES = (
    "FAMILY_A_SIGNAL_AND_HORIZON",
    "FULL_POINT_IN_TIME_DATASET",
    "EXTERNAL_CANDIDATE_QUALIFICATION",
    "HISTORICAL_MEMBERSHIP_AND_DELISTING",
    "SECTOR_LIQUIDITY_MACRO_HISTORY",
    "INDEPENDENT_CURRENT_USE_RIGHTS",
    "NON_SYNTHETIC_SNAPSHOT_PERSISTENCE",
    "NON_SYNTHETIC_EVALUATION_POLICY",
    "NON_SYNTHETIC_EVALUATION_PATH",
    "PURGED_WALK_FORWARD_MECHANICS",
    "EMBARGO_APPLICABILITY_DECISION",
    "LEAKAGE_FREE_RESULT",
    "MARKET_CALIBRATED_COST_SLIPPAGE",
    "DSR_PBO_PROMOTION_GATES",
    "PHASE_15_IMPLEMENTATION_AUTHORITY",
    "DATA_RIGHTS_AND_RESEARCH_AUTHORITY",
    "RIGHTS_CURRENTNESS_REVOCATION",
    "PRE_ORDER_RISK",
    "IMMUTABLE_AUDIT_SCHEMA",
)
GAP_STATES = (
    "MOCK_ONLY",
    "MISSING",
    "UNPROVEN",
    "UNPROVEN",
    "MISSING",
    "MISSING",
    "MISSING",
    "MISSING",
    "MISSING",
    "MOCK_ONLY",
    "UNPROVEN",
    "MOCK_ONLY",
    "MOCK_ONLY",
    "MOCK_ONLY",
    "PRESENT",
    "MISSING",
    "MISSING",
    "MOCK_ONLY",
    "PRESENT",
)
GAP_SOURCE_SHA256S = (
    "29c8594ba865b97d5421c381647bc91773ca3ef48388e65d563a5eaa085319d5",
    "4ddf94cbdadd7b61f51b97b9105e6adea6a590cc622271e002356a9352c7a49a",
    "9c110da463f048a8c577ebb16b65fdf4654aec2a93826ab2b5bfd0f1b936d580",
    "441afc30e509ebfedfbcb888a77537408e3c2d530d32470c98d2c1035636be61",
    "f36ddc92e8deffcf57bf1e98eeb9c2d0be91807ed0abdbc5690dda22ec97e801",
    "0472fddba255153f3e7cf3dabc0bc025c05714897762e2912cf3a887e48738ff",
    "3d0b7e6a74afe8fe70beb8cfa2cc4ae8d15c6a647ba43e45daa1b1c2f14b3c7b",
    "9a484c0596b92e7f659fac58198a707e9b8c8e372ace7af6f419cb15d31d81bb",
    "6fdcae7db872a98e629a1e93df9aa6ac75f83ed5902771b7efbce5b08a04102a",
    "233a469add2a3b0b0a216780f6c4a259e9d2cd9a81dbd0138be91b7fa81dd13a",
    "352dffce8463b24ae2e4eaba65a207c21d8ab4f53592619061f7e8180c38a73c",
    "bee9a7ac0ec623281bbc5b0293e349d0f926db5bf59ecf86af6888d0dcae726d",
    "041d3fdff4a5fc3f8b6f337de729890d3569ec9e619a70c2f06c342ecad53be4",
    "006adff9e34c540b58c641f84218bfcbbb66323c833da3de800e1e8029a8bf98",
    "27e71e37a9991fd04e25d61e005f5eeb167804be7adb5d5ef473089f077e0d8f",
    "f3d4a2625fcedf362a392ab761056a7e75257f9eb2fb51b1d11038060187868d",
    "870786a3addaf720aca5bbe20ec585643794bb46b78c64003f1a81df7875260a",
    "9afe4ae29601ccf3891f52719e2b0a7db5573f9ee96d3db7c8878f428dcf4fba",
    "617881a4d22da3e7e72e6f335519d66e6593c3607fdcfe398d91c28ef9810b20",
)


def normalized(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def verifier_module() -> ModuleType:
    path = ROOT / "scripts/verify_phase1.py"
    spec = importlib.util.spec_from_file_location("phase16_verifier", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_phase16_baseline_parser_counts_boundaries_and_exact_allowlist_are_frozen() -> None:
    verifier = verifier_module()
    assert verifier.PHASE_16_BASELINE_SHA == BASELINE_SHA
    assert verifier.EXPECTED_PHASE_16_BASELINE_TREE == BASELINE_TREE
    assert verifier.PHASE_16_ARTIFACT_PATH == ARTIFACT_PATH
    assert verifier.PHASE_16_ARTIFACT_SCHEMA_VERSION == (
        "phase16-family-a-point-in-time-source-plan-v1"
    )
    assert verifier.PHASE_16_POLICY_ID == "phase16-family-a-point-in-time-source-plan-policy-v1"
    assert verifier.PHASE_16_OUTCOMES == {"PLAN_FROZEN", "BLOCKED"}
    assert verifier.PHASE_16_STATUSES == {"PASS", "BLOCKED", "UNCOMPUTABLE"}
    assert verifier.PHASE_16_EXPECTED_ARTIFACT_ID == "e106a766-5cfe-5a1c-94f6-ee1c2ac68652"
    assert verifier.PHASE_16_EXPECTED_ARTIFACT_SHA256 == (
        "74ddf4a51d722b494fd494241e2e5927bff6fde034f6932dcfd791bb3a0706bb"
    )
    assert verifier.PHASE_16_EXPECTED_POLICY_SHA256 == (
        "57cfcfd09f2d4a87d9562fd536228b9f05693bb71b7e9d1867618a35da7d4efd"
    )
    assert verifier.PHASE_16_REQUIREMENT_CODES == REQUIREMENT_CODES
    assert verifier.PHASE_16_CAPABILITY_CODES == CAPABILITY_CODES
    assert verifier.PHASE_16_CANDIDATE_ROWS == CANDIDATE_ROWS
    assert verifier.PHASE_16_STEP_CODES == STEP_CODES
    assert verifier.PHASE_16_GAP_CODES == GAP_CODES
    assert verifier.PHASE_16_GAP_STATES == GAP_STATES
    assert verifier.PHASE_16_GAP_SOURCE_SHA256S == GAP_SOURCE_SHA256S
    assert verifier.PHASE_16_COLLECTION_COUNTS == {
        "requirements": 12,
        "capabilities": 7,
        "candidates": 6,
        "future_steps": 7,
        "phase15_gap_bindings": 19,
    }
    assert verifier.PHASE_16_INHERITED_TABLES == verifier.PHASE_15_INHERITED_TABLES
    assert len(verifier.PHASE_16_INHERITED_TABLES) == 57
    assert len(set(verifier.PHASE_16_INHERITED_TABLES)) == 57
    assert [verifier.phase_number(str(phase)) for phase in range(1, 21)] == list(range(1, 21))
    for invalid in ("0", "21", "not-a-phase"):
        with pytest.raises(argparse.ArgumentTypeError):
            verifier.phase_number(invalid)

    assert verifier.PHASE_16_ALLOWED_WRITES == {
        ".github/workflows/ci.yml",
        "Makefile",
        "README.md",
        "docs/COMPLIANCE_NOTES.md",
        "docs/DATA_SOURCES.md",
        "docs/EVALS.md",
        "docs/IMPLEMENTATION_PLAN.md",
        ARTIFACT_PATH,
        "docs/PHASE_16_FAMILY_A_POINT_IN_TIME_SOURCE_PLAN_DECISIONS.md",
        "docs/RISK_POLICY.md",
        "docs/handoffs/PHASE_16.md",
        "scripts/check.ps1",
        "scripts/check.sh",
        "scripts/generate_family_a_point_in_time_source_plan.py",
        "scripts/verify_family_a_point_in_time_source_plan.py",
        "scripts/verify_phase1.py",
        "services/data/src/fable5_data/phase16/__init__.py",
        "services/data/src/fable5_data/phase16/canonical.py",
        "services/data/src/fable5_data/phase16/contracts.py",
        "services/data/src/fable5_data/phase16/plan.py",
        "services/data/tests/test_phase16_contracts.py",
        "services/data/tests/test_phase16_plan.py",
        "services/data/tests/test_phase16_security.py",
        "services/frontend/e2e/phase8.accessibility.spec.ts",
        "services/frontend/e2e/phase8.visual.spec.ts",
        "tests/test_phase5_postgres.py",
        "tests/test_phase9_static.py",
        "tests/test_phase10_static.py",
        "tests/test_phase11_static.py",
        "tests/test_phase12_static.py",
        "tests/test_phase13_static.py",
        "tests/test_phase14_static.py",
        "tests/test_phase15_static.py",
        "tests/test_phase16_portable.py",
        "tests/test_phase16_static.py",
        "tests/test_repository_policy.py",
    }


def test_phase16_committed_artifact_is_exact_canonical_closed_evidence() -> None:
    committed = (ROOT / ARTIFACT_PATH).read_bytes()
    assert committed == canonical_source_plan_bytes()
    payload = json.loads(committed)
    artifact = build_family_a_point_in_time_source_plan()
    assert payload["artifact_sha256"] == artifact.artifact_sha256
    assert payload["schema_version"] == "phase16-family-a-point-in-time-source-plan-v1"
    assert payload["policy_id"] == "phase16-family-a-point-in-time-source-plan-policy-v1"
    assert payload["outcome"] == "PLAN_FROZEN"
    assert payload["accepted_phase15_commit_sha"] == BASELINE_SHA
    assert payload["accepted_phase15_tree_sha"] == BASELINE_TREE
    assert tuple(item["code"] for item in payload["requirements"]) == REQUIREMENT_CODES
    assert tuple(item["code"] for item in payload["capabilities"]) == CAPABILITY_CODES
    assert tuple((item["code"], item["state"]) for item in payload["candidates"]) == (
        CANDIDATE_ROWS
    )
    assert all(item["candidate_only"] is True for item in payload["candidates"])
    assert tuple(item["code"] for item in payload["future_steps"]) == STEP_CODES
    assert payload["future_steps"][2]["required_prior_evidence"] == [
        "non_synthetic_evaluation_policy_sha256",
        "confirmation_holdout_definition_sha256",
    ]
    assert tuple(item["code"] for item in payload["phase15_gap_bindings"]) == GAP_CODES
    assert tuple(item["state"] for item in payload["phase15_gap_bindings"]) == GAP_STATES
    assert tuple(item["source_gap_sha256"] for item in payload["phase15_gap_bindings"]) == (
        GAP_SOURCE_SHA256S
    )
    for collection_name, expected_count in {
        "requirements": 12,
        "capabilities": 7,
        "candidates": 6,
        "future_steps": 7,
        "phase15_gap_bindings": 19,
    }.items():
        assert len(payload[collection_name]) == expected_count
    assert {item["status"] for item in payload["requirements"]} == {"PASS"}

    verifier = verifier_module()
    for field in verifier.PHASE_16_FALSE_AUTHORITY_FIELDS:
        assert payload[field] is False
    for field in verifier.PHASE_16_TRUE_BOUNDARY_FIELDS:
        assert payload[field] is True


def test_phase16_inherited_static_release_checks_are_deactivated_narrowly() -> None:
    verifier = verifier_module()
    phase15_parameters = inspect.signature(verifier.verify_phase15_static).parameters
    assert tuple(phase15_parameters) == ("release_closure", "active_phase")
    assert phase15_parameters["release_closure"].default is True
    assert phase15_parameters["active_phase"].default == 15
    phase16_parameters = inspect.signature(verifier.verify_phase16_static).parameters
    assert tuple(phase16_parameters) == ("release_closure", "active_phase")
    assert phase16_parameters["release_closure"].default is True
    assert phase16_parameters["active_phase"].default == 16

    source = normalized(ROOT / "scripts/verify_phase1.py")
    phase16_branch = source.split("if phase == 16:", 1)[1].split(
        "verify_static_inherited(phase)", 1
    )[0]
    for required in (
        "verify_static_inherited(16, announce=False)",
        "verify_phase10_static(release_closure=False, active_phase=16)",
        "verify_phase11_static(release_closure=False, active_phase=16)",
        "verify_phase12_static(release_closure=False, active_phase=16)",
        "verify_phase13_static(release_closure=False, active_phase=16)",
        "verify_phase14_static(release_closure=False, active_phase=16)",
        "verify_phase15_static(release_closure=False, active_phase=16)",
        "verify_phase16_static()",
    ):
        assert required in phase16_branch


def test_phase16_browser_gates_remain_stage_local_and_active() -> None:
    source = normalized(ROOT / "scripts/verify_phase1.py")
    browser_boundaries = (
        ("def verify_phase8_browser(", "def phase10_linux_playwright_container_name("),
        ("def verify_phase10_browser(", "def verify_phase11_browser("),
        ("def verify_phase11_browser(", "def verify_phase3_changed_rule_version("),
    )
    for start_marker, end_marker in browser_boundaries:
        browser_source = source[source.index(start_marker) : source.index(end_marker)]
        assert "PHASE_16_INHERITED_TABLES" not in browser_source
        assert "snapshot_tables(project, environment, all_tables)" in browser_source

    for required in (
        "if phase in {",
        "if phase in {10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20}:",
        "if phase in {11, 12, 13, 14, 15, 16, 17, 18, 19, 20}:",
        "if phase in {12, 13, 14, 15, 16, 17, 18, 19, 20}:",
        "if phase in {13, 14, 15, 16, 17, 18, 19, 20}:",
        "if phase in {14, 15, 16, 17, 18, 19, 20}:",
        "if phase in {15, 16, 17, 18, 19, 20}:",
    ):
        assert required in source

    for path in (
        ROOT / "services/frontend/e2e/phase8.accessibility.spec.ts",
        ROOT / "services/frontend/e2e/phase8.visual.spec.ts",
    ):
        browser = normalized(path)
        assert 'process.env.FABLE5_VERIFY_PHASE ?? "20"' in browser
        assert (
            'new Set(["10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20"])' in browser
        )


def test_phase16_portable_no_schema_identity_cleanup_and_ci_are_bound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    verifier = verifier_module()
    for name in (
        *verifier.PHASE_12_CREDENTIAL_ENV_NAMES,
        *verifier.PHASE_13_CREDENTIAL_ENV_NAMES,
        "FABLE5_DATABASE_URL",
        "FABLE5_REDIS_URL",
    ):
        monkeypatch.setenv(name, "must-be-removed")
    offline = verifier.phase16_offline_environment()
    assert offline["FABLE5_VERIFY_PHASE"] == "16"
    assert all(offline.get(name) is None for name in verifier.PHASE_12_CREDENTIAL_ENV_NAMES)
    assert all(offline.get(name) is None for name in verifier.PHASE_13_CREDENTIAL_ENV_NAMES)
    assert "FABLE5_DATABASE_URL" not in offline
    assert "FABLE5_REDIS_URL" not in offline

    source = normalized(ROOT / "scripts/verify_phase1.py")
    phase5_postgres_acceptance = source.split("def verify_phase5_postgres_acceptance(", 1)[1].split(
        "def verify_phase6_postgres_acceptance(", 1
    )[0]
    assert (
        'test_environment["FABLE5_VERIFY_PHASE"] = environment["FABLE5_VERIFY_PHASE"]'
        in phase5_postgres_acceptance
    )
    for required in (
        "verify_phase16_portable_acceptance(",
        "verify_phase16_offline_network_denial(",
        "snapshot_phase16_inherited_state(",
        "verify_phase16_no_schema_drift_and_zero_writes(",
        'version != "0011_phase14"',
        "len(PHASE_16_INHERITED_TABLES) != 57",
        'phase10_clean_git_identity("preflight", phase=phase)',
        'verify_phase10_acceptance_resource_namespace(\n            "preflight"',
        'verify_phase10_acceptance_resource_namespace(\n                        "post-cleanup"',
        'print("Full Compose Phase 16 verification passed.")',
        'default=os.environ.get("FABLE5_VERIFY_PHASE", "20")',
    ):
        assert required in source

    workflow = normalized(ROOT / ".github/workflows/ci.yml")
    assert workflow.startswith("name: phase-20-ci\n")
    assert 'FABLE5_VERIFY_PHASE: "20"' in workflow
    assert "phase20-compose:" in workflow
    assert workflow.count("python scripts/verify_phase1.py --phase 20") == 1
    assert workflow.count("python scripts/verify_phase1.py --static-only --phase 20") == 1
    assert "timeout-minutes: 180" in workflow
    assert "fetch-depth: 0" in workflow
    assert "secrets." not in workflow
    assert "FABLE5_UPDATE_SNAPSHOTS" not in workflow

    runner = normalized(ROOT / "scripts/run_phase_gate.py")
    assert "choices=(9,)" in runner
    assert '"--phase", "16"' not in runner
