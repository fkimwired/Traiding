from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BASELINE_SHA = "53d9f8641d98c729447661af9b7e561073a52226"
BASELINE_TREE = "4f3da35d31f352ea92d5f715149e0e439a57af3b"
ACCEPTED_PHASE23_SHA = "d8d8d63a79457c7a54e0a3738a75f4eb613c602f"
ARTIFACT = ROOT / "docs/PHASE_24_FAMILY_A_RTDSM_RIGHTS_CLARIFICATION_REQUIREMENTS.json"


def normalized(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def verifier_module():
    spec = importlib.util.spec_from_file_location(
        "verify_phase1_phase24_static", ROOT / "scripts/verify_phase1.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_phase24_baseline_parser_allowlist_and_static_inheritance_are_exact() -> None:
    verifier = verifier_module()
    assert verifier.PHASE_24_BASELINE_SHA == BASELINE_SHA
    assert verifier.EXPECTED_PHASE_24_BASELINE_TREE == BASELINE_TREE
    assert verifier.PHASE_24_ACCEPTED_PHASE23_SHA == ACCEPTED_PHASE23_SHA
    assert len(verifier.PHASE_24_ALLOWED_WRITES) == 44
    assert set(verifier.PHASE_24_REQUIRED_PATHS) <= verifier.PHASE_24_ALLOWED_WRITES
    assert verifier.PHASE_24_INHERITED_TABLES == verifier.PHASE_23_INHERITED_TABLES
    assert len(verifier.PHASE_24_INHERITED_TABLES) == 57
    assert [verifier.phase_number(str(value)) for value in range(1, 29)] == list(range(1, 29))
    for invalid in ("0", "29", "not-a-phase"):
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
    parents = subprocess.run(
        ["git", "show", "-s", "--format=%P", BASELINE_SHA],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split()
    assert ACCEPTED_PHASE23_SHA in parents


def test_phase24_artifact_is_canonical_blocked_and_all_inputs_are_unresolved() -> None:
    from fable5_data.phase24 import canonical as c
    from fable5_data.phase24.contracts import FamilyARTDSMRightsClarificationRequirements
    from fable5_data.phase24.rights_clarification import (
        build_family_a_rtdsm_rights_clarification_requirements,
        canonical_rtdsm_rights_clarification_requirements_bytes,
    )

    raw = ARTIFACT.read_bytes()
    artifact = FamilyARTDSMRightsClarificationRequirements.model_validate_json(raw, strict=True)
    assert raw == canonical_rtdsm_rights_clarification_requirements_bytes()
    assert artifact == build_family_a_rtdsm_rights_clarification_requirements()
    assert artifact.outcome.value == "BLOCKED"
    assert artifact.requirements_state.value == "RIGHTS_CLARIFICATION_REQUIREMENTS_FROZEN"
    assert (
        artifact.aggregate_conclusion.value
        == "BLOCKED_AWAITING_INDEPENDENT_CURRENT_USE_RIGHTS_CLARIFICATION"
    )
    assert (
        len(artifact.proposed_use_disclosures),
        len(artifact.clarification_questions),
        len(artifact.evidence_requirements),
        len(artifact.transition_rules),
    ) == (8, 10, 6, 7)
    assert all(
        row.status.value == "PROPOSED_NOT_AUTHORIZED" and not row.satisfied
        for row in artifact.proposed_use_disclosures
    )
    assert all(
        row.state.value == "UNANSWERED"
        and not row.answer_evidence_present
        and not row.independently_verified
        and not row.satisfied
        for row in artifact.clarification_questions
    )
    assert all(
        row.state.value == "MISSING"
        and not row.evidence_present
        and not row.independently_verified
        and not row.satisfied
        for row in artifact.evidence_requirements
    )
    assert all(not row.applied and not row.satisfied for row in artifact.transition_rules)
    dumped = artifact.model_dump(mode="python")
    for field, expected in c.PHASE24_BOUNDARY_VALUES.items():
        assert dumped[field] is expected


def test_phase24_domain_and_clis_have_no_transport_database_execution_or_secret_surface() -> None:
    domain = ROOT / "services/data/src/fable5_data/phase24"
    imported: set[str] = set()
    production = ""
    for path in domain.glob("*.py"):
        source = normalized(path)
        production += source
        tree = ast.parse(source, filename=str(path))
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
    }
    for forbidden in (
        "datetime.now",
        "getenv(",
        "uuid4(",
        "create_engine(",
        "submit_order",
        "place_order",
        "create_order",
    ):
        assert forbidden not in production
    generator = normalized(
        ROOT / "scripts/generate_family_a_rtdsm_rights_clarification_requirements.py"
    )
    portable = normalized(
        ROOT / "scripts/verify_family_a_rtdsm_rights_clarification_requirements.py"
    )
    assert generator.count('"--confirm-rights-clarification-requirements-only"') == 1
    assert portable.count('"--requirements"') == 1
    for source in (generator, portable):
        assert 'event.startswith("socket.")' in source
        assert 'frozenset({"os.system", "subprocess.Popen"})' in source
        assert source.count("subprocess.Popen(") == 1
        assert "subprocess.run(" not in source
        main = source.index("def main")
        parse = source.index("_parser().parse_args", main)
        assert source.index("sys.addaudithook(_offline_audit_hook)", main) < parse
        assert source.index("_prove_offline_boundary()", main) < parse


def test_phase24_verifier_dispatch_and_zero_write_acceptance_are_bound() -> None:
    source = normalized(ROOT / "scripts/verify_phase1.py")
    for required in (
        "def verify_phase24_static()",
        "verify_phase24_static()",
        "def phase24_offline_environment()",
        "def verify_phase24_portable_acceptance(",
        "def verify_phase24_offline_network_denial(",
        "def snapshot_phase24_inherited_state(",
        "def verify_phase24_no_schema_drift_and_zero_writes(",
        'print("Full Compose Phase 24 verification passed.")',
        'default=os.environ.get("FABLE5_VERIFY_PHASE", "27")',
    ):
        assert required in source
    assert re.search(
        r"if phase in \{\s*8,\s*9,\s*10,\s*11,\s*12,\s*13,\s*14,\s*15,\s*"
        r"16,\s*17,\s*18,\s*19,\s*20,\s*21,\s*22,\s*23,\s*24,\s*25,\s*27,\s*\}:\s*"
        r"verify_phase8_browser\(",
        source,
    )
    assert verifier_module().phase24_offline_environment()["FABLE5_VERIFY_PHASE"] == "24"
    workflow = normalized(ROOT / ".github/workflows/ci.yml")
    assert workflow.startswith("name: phase-27-ci\n")
    assert 'FABLE5_VERIFY_PHASE: "27"' in workflow
    assert "phase27-compose:" in workflow
    assert workflow.count("python scripts/verify_phase1.py --static-only --phase 27") == 1
    assert workflow.count("python scripts/verify_phase1.py --phase 27") == 1
    assert "timeout-minutes: 180" in workflow and "fetch-depth: 0" in workflow
    assert "secrets." not in workflow and "FABLE5_UPDATE_SNAPSHOTS" not in workflow


def test_phase24_is_frozen_while_phase25_wrappers_and_browser_inheritance_are_active() -> None:
    for entrypoint in ("scripts/check.ps1", "scripts/check.sh", "Makefile"):
        source = normalized(ROOT / entrypoint)
        assert "FABLE5_VERIFY_PHASE" in source and "--phase" in source
        assert "25, 26, 27, or 28" in source
        assert "29" not in source.split("must be one of", 1)[1].split(".", 1)[0]
    for path in (
        ROOT / "services/frontend/e2e/phase8.accessibility.spec.ts",
        ROOT / "services/frontend/e2e/phase8.visual.spec.ts",
    ):
        source = normalized(path)
        assert 'process.env.FABLE5_VERIFY_PHASE ?? "27"' in source
        assert '"23",\n  "24",\n  "25",' in source
    combined = normalized(
        ROOT / "docs/PHASE_24_FAMILY_A_RTDSM_RIGHTS_CLARIFICATION_REQUIREMENTS_DECISIONS.md"
    ) + normalized(ROOT / "docs/handoffs/PHASE_24.md")
    for required in (
        BASELINE_SHA,
        BASELINE_TREE,
        ACCEPTED_PHASE23_SHA,
        "RIGHTS_CLARIFICATION_REQUIREMENTS_FROZEN",
        "BLOCKED_AWAITING_INDEPENDENT_CURRENT_USE_RIGHTS_CLARIFICATION",
        "adds no migration",
        "Stop after Phase 24",
    ):
        assert required in combined
    assert (ROOT / "docs/handoffs/PHASE_25.md").exists()
    assert (ROOT / "services/data/src/fable5_data/phase25").exists()
    runner = normalized(ROOT / "scripts/run_phase_gate.py")
    assert "choices=(9,)" in runner and '"--phase", "24"' not in runner


def test_phase24_frozen_inherited_surfaces_match_baseline() -> None:
    for relative in (
        "compose.yaml",
        "package.json",
        "package-lock.json",
        "packages/contracts/openapi.json",
        "packages/contracts/src/api.generated.ts",
        "packages/contracts/src/runtime.generated.ts",
        "pyproject.toml",
        "requirements.lock",
        "scripts/run_phase_gate.py",
        "docs/PHASE_23_FAMILY_A_RTDSM_CURRENT_USE_RIGHTS_REVIEW.json",
    ):
        current = (ROOT / relative).read_bytes()
        baseline = subprocess.run(
            ["git", "show", f"{BASELINE_SHA}:{relative}"], cwd=ROOT, check=True, capture_output=True
        ).stdout
        assert current == baseline
    assert json.loads((ROOT / "packages/contracts/openapi.json").read_text())["paths"]
