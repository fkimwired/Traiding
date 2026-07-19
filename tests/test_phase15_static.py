from __future__ import annotations

import argparse
import ast
import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest
from fable5_data.phase15.canonical import (
    PHASE15_ARTIFACT_SCHEMA_VERSION,
    PHASE15_BOUNDARY_VALUES,
    PHASE15_FROZEN_AT_UTC,
    PHASE15_GAP_CODES,
    PHASE15_GAP_SCHEMA_VERSION,
    PHASE15_GAP_STATES,
    PHASE15_POLICY_ID,
    PHASE15_REQUIREMENT_CODES,
    PHASE15_REQUIREMENT_SCHEMA_VERSION,
)
from fable5_data.phase15.contracts import FamilyAResearchAdmissionSpecification
from fable5_data.phase15.specification import canonical_specification_bytes

ROOT = Path(__file__).resolve().parents[1]
BASELINE_SHA = "513fdfd515599e59db6911441aadf1cc30f7352c"
BASELINE_TREE = "5870fd4c112b7c7bee05f6240c5cbd950eeaff04"
ARTIFACT_PATH = "docs/PHASE_15_FAMILY_A_RESEARCH_ADMISSION_SPECIFICATION.json"


def normalized(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")


def verifier_module() -> ModuleType:
    path = ROOT / "scripts/verify_phase1.py"
    spec = importlib.util.spec_from_file_location("phase15_verifier", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_phase15_baseline_parser_registries_and_exact_allowlist_are_frozen() -> None:
    verifier = verifier_module()
    assert verifier.PHASE_15_BASELINE_SHA == BASELINE_SHA
    assert verifier.EXPECTED_PHASE_15_BASELINE_TREE == BASELINE_TREE
    assert verifier.PHASE_15_ARTIFACT_PATH == ARTIFACT_PATH
    assert verifier.PHASE_15_OUTCOMES == {"REQUIREMENTS_FROZEN", "BLOCKED"}
    assert verifier.PHASE_15_REQUIREMENT_STATUSES == {"PASS", "BLOCKED", "UNCOMPUTABLE"}
    assert verifier.PHASE_15_GAP_STATES == {
        "PRESENT",
        "MOCK_ONLY",
        "STALE",
        "MISSING",
        "UNPROVEN",
    }
    assert verifier.PHASE_15_REQUIREMENT_CODES == PHASE15_REQUIREMENT_CODES
    assert verifier.PHASE_15_GAP_CODES == PHASE15_GAP_CODES
    assert verifier.PHASE_15_GAP_EXPECTED_STATES == PHASE15_GAP_STATES
    assert verifier.PHASE_15_BOUNDARY_VALUES == PHASE15_BOUNDARY_VALUES
    assert verifier.PHASE_15_ARTIFACT_SCHEMA_VERSION == PHASE15_ARTIFACT_SCHEMA_VERSION
    assert verifier.PHASE_15_REQUIREMENT_SCHEMA_VERSION == PHASE15_REQUIREMENT_SCHEMA_VERSION
    assert verifier.PHASE_15_GAP_SCHEMA_VERSION == PHASE15_GAP_SCHEMA_VERSION
    assert verifier.PHASE_15_POLICY_ID == PHASE15_POLICY_ID
    assert verifier.PHASE_15_FROZEN_AT_UTC == PHASE15_FROZEN_AT_UTC.isoformat().replace(
        "+00:00", "Z"
    )
    assert len(verifier.PHASE_15_INHERITED_TABLES) == 57
    assert len(set(verifier.PHASE_15_INHERITED_TABLES)) == 57
    assert [verifier.phase_number(str(phase)) for phase in range(1, 20)] == list(range(1, 20))
    for invalid in ("0", "20", "not-a-phase"):
        with pytest.raises(argparse.ArgumentTypeError):
            verifier.phase_number(invalid)

    assert verifier.PHASE_15_ALLOWED_WRITES == {
        ".github/workflows/ci.yml",
        "Makefile",
        "README.md",
        "docs/COMPLIANCE_NOTES.md",
        "docs/DATA_SOURCES.md",
        "docs/EVALS.md",
        "docs/IMPLEMENTATION_PLAN.md",
        "docs/PHASE_15_FAMILY_A_RESEARCH_ADMISSION_SPECIFICATION_DECISIONS.md",
        ARTIFACT_PATH,
        "docs/RISK_POLICY.md",
        "docs/handoffs/PHASE_15.md",
        "scripts/check.ps1",
        "scripts/check.sh",
        "scripts/generate_family_a_research_admission_specification.py",
        "scripts/verify_family_a_research_admission_specification.py",
        "scripts/verify_phase1.py",
        "services/data/src/fable5_data/phase15/__init__.py",
        "services/data/src/fable5_data/phase15/canonical.py",
        "services/data/src/fable5_data/phase15/contracts.py",
        "services/data/src/fable5_data/phase15/specification.py",
        "services/data/tests/test_phase15_contracts.py",
        "services/data/tests/test_phase15_security.py",
        "services/data/tests/test_phase15_specification.py",
        "services/frontend/e2e/phase8.accessibility.spec.ts",
        "services/frontend/e2e/phase8.visual.spec.ts",
        "tests/test_phase5_postgres.py",
        "tests/test_phase9_static.py",
        "tests/test_phase10_static.py",
        "tests/test_phase11_static.py",
        "tests/test_phase12_static.py",
        "tests/test_phase13_static.py",
        "tests/test_phase14_static.py",
        "tests/test_phase15_portable.py",
        "tests/test_phase15_static.py",
        "tests/test_repository_policy.py",
    }


def test_phase15_committed_artifact_is_exact_canonical_closed_evidence() -> None:
    committed = (ROOT / ARTIFACT_PATH).read_bytes()
    assert committed == canonical_specification_bytes()
    artifact = FamilyAResearchAdmissionSpecification.model_validate(json.loads(committed))
    assert artifact.outcome.value == "REQUIREMENTS_FROZEN"
    assert tuple(item.code.value for item in artifact.requirements) == PHASE15_REQUIREMENT_CODES
    assert {item.status.value for item in artifact.requirements} == {"PASS"}
    assert tuple(item.code.value for item in artifact.gaps) == PHASE15_GAP_CODES
    assert tuple(item.state.value for item in artifact.gaps) == PHASE15_GAP_STATES
    rendered = artifact.model_dump(mode="json")
    for field, expected in PHASE15_BOUNDARY_VALUES.items():
        assert rendered[field] is expected


def test_phase15_domain_and_clis_are_portable_pure_and_authority_closed() -> None:
    root = ROOT / "services/data/src/fable5_data/phase15"
    forbidden_imports = {
        "aiohttp",
        "alpaca",
        "asyncio",
        "fastapi",
        "fable5_paper",
        "fable5_research",
        "http",
        "httpx",
        "os",
        "psycopg",
        "random",
        "requests",
        "secrets",
        "socket",
        "sqlalchemy",
        "ssl",
        "subprocess",
        "time",
        "urllib",
        "websocket",
        "websockets",
    }
    imported: set[str] = set()
    production = ""
    for path in sorted(root.glob("*.py")):
        source = normalized(path)
        production += source.casefold()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".", 1)[0])
    assert imported.isdisjoint(forbidden_imports)
    for forbidden in (
        "create_engine",
        "datetime.now",
        "datetime.utcnow",
        "getenv",
        "glob(",
        "rglob(",
        "uuid4",
        "submit_order",
        "place_order",
        "create_order",
        "retry",
    ):
        assert forbidden not in production

    generator = normalized(ROOT / "scripts/generate_family_a_research_admission_specification.py")
    portable = normalized(ROOT / "scripts/verify_family_a_research_admission_specification.py")
    assert "--confirm-requirements-only" in generator
    assert "--specification" in portable
    for forbidden in (
        "--provider",
        "--url",
        "--credential",
        "--right",
        "--data",
        "--output",
        "--strategy",
        "--signal",
        "--side",
        "--quantity",
        "--price",
        "--allocation",
        "--broker",
        "--retry",
        "--execution",
        "--ingestion",
        "--promotion",
        "--expected-hash",
        "--repair",
    ):
        assert forbidden not in generator
        assert forbidden not in portable


def test_phase15_ci_full_verifier_browser_no_schema_and_cleanup_are_bound() -> None:
    verifier = normalized(ROOT / "scripts/verify_phase1.py")
    for required in (
        "verify_phase15_static(",
        "verify_phase15_portable_acceptance(",
        "verify_phase15_offline_network_denial(",
        "verify_phase15_no_schema_drift_and_zero_writes(",
        'print("Full Compose Phase 15 verification passed.")',
        "if phase in {",
        "if phase in {10, 11, 12, 13, 14, 15, 16, 17, 18, 19}:",
        "if phase in {11, 12, 13, 14, 15, 16, 17, 18, 19}:",
        "if phase in {12, 13, 14, 15, 16, 17, 18, 19}:",
        "if phase in {13, 14, 15, 16, 17, 18, 19}:",
        "if phase in {14, 15, 16, 17, 18, 19}:",
        'default=os.environ.get("FABLE5_VERIFY_PHASE", "19")',
        'version_before != "0011_phase14"',
        "len(PHASE_15_INHERITED_TABLES) != 57",
    ):
        assert required in verifier

    browser_boundaries = (
        ("def verify_phase8_browser(", "def phase10_linux_playwright_container_name("),
        ("def verify_phase10_browser(", "def verify_phase11_browser("),
        ("def verify_phase11_browser(", "def verify_phase3_changed_rule_version("),
    )
    for start_marker, end_marker in browser_boundaries:
        browser_source = verifier[verifier.index(start_marker) : verifier.index(end_marker)]
        assert "PHASE_15_INHERITED_TABLES" not in browser_source
        assert "snapshot_tables(project, environment, all_tables)" in browser_source

    workflow = normalized(ROOT / ".github/workflows/ci.yml")
    assert workflow.startswith("name: phase-19-ci\n")
    assert 'FABLE5_VERIFY_PHASE: "19"' in workflow
    assert "phase19-compose:" in workflow
    assert workflow.count("python scripts/verify_phase1.py --phase 19") == 1
    assert workflow.count("python scripts/verify_phase1.py --static-only --phase 19") == 1
    assert "secrets." not in workflow
    assert "FABLE5_UPDATE_SNAPSHOTS" not in workflow

    for path in (
        ROOT / "services/frontend/e2e/phase8.accessibility.spec.ts",
        ROOT / "services/frontend/e2e/phase8.visual.spec.ts",
    ):
        source = normalized(path)
        assert 'process.env.FABLE5_VERIFY_PHASE ?? "19"' in source
        assert 'new Set(["10", "11", "12", "13", "14", "15", "16", "17", "18", "19"])' in source

    runner = normalized(ROOT / "scripts/run_phase_gate.py")
    assert "choices=(9,)" in runner
    assert '"--phase", "15"' not in runner
