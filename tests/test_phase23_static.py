from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import subprocess
from pathlib import Path
from types import ModuleType

import pytest
from fable5_data.phase23 import canonical as c
from fable5_data.phase23.contracts import FamilyARTDSMCurrentUseRightsReview
from fable5_data.phase23.rights_review import (
    build_family_a_rtdsm_current_use_rights_review,
    canonical_rtdsm_current_use_rights_review_bytes,
)

ROOT = Path(__file__).resolve().parents[1]
BASELINE_SHA = "7f3bf3df029a894660f0e47dda1056bd32dca297"
BASELINE_TREE = "1261f5a9da883e14a894b33e583068681f8cf459"
ACCEPTED_PHASE22_SHA = "1c07fbe8e23950e8c9f910b30473c900c0bf3e21"
ARTIFACT_PATH = "docs/PHASE_23_FAMILY_A_RTDSM_CURRENT_USE_RIGHTS_REVIEW.json"


def normalized(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")


def verifier_module() -> ModuleType:
    path = ROOT / "scripts/verify_phase1.py"
    spec = importlib.util.spec_from_file_location("phase23_verifier", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git_blob(commit: str, path: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout


def imported_module_roots(paths: tuple[Path, ...]) -> set[str]:
    imported: set[str] = set()
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".", 1)[0])
    return imported


def test_phase23_baseline_parser_and_static_dispatch_are_exact() -> None:
    verifier = verifier_module()
    assert verifier.PHASE_23_BASELINE_SHA == BASELINE_SHA
    assert verifier.EXPECTED_PHASE_23_BASELINE_TREE == BASELINE_TREE
    assert verifier.PHASE_23_ACCEPTED_PHASE22_SHA == ACCEPTED_PHASE22_SHA
    assert verifier.PHASE_23_ARTIFACT_PATH == ARTIFACT_PATH
    assert set(verifier.PHASE_23_REQUIRED_PATHS) <= verifier.PHASE_23_ALLOWED_WRITES
    assert verifier.PHASE_23_INHERITED_TABLES == verifier.PHASE_22_INHERITED_TABLES
    assert len(verifier.PHASE_23_INHERITED_TABLES) == 57
    assert [verifier.phase_number(str(value)) for value in range(1, 24)] == list(range(1, 24))
    for invalid in ("0", "24", "not-a-phase"):
        with pytest.raises(argparse.ArgumentTypeError):
            verifier.phase_number(invalid)

    source = normalized(ROOT / "scripts/verify_phase1.py")
    branch = source.split("if phase == 23:", 1)[1].split("verify_static_inherited(phase)", 1)[0]
    for phase in range(10, 22):
        assert f"verify_phase{phase}_static(release_closure=False, active_phase=23)" in branch
    for required in (
        "verify_static_inherited(23, announce=False)",
        "verify_phase23_static()",
        'print("Static repository policy checks passed for Phase 23.")',
    ):
        assert required in branch


def test_phase23_artifact_is_canonical_conservative_and_hash_bound() -> None:
    committed = (ROOT / ARTIFACT_PATH).read_bytes()
    assert committed == canonical_rtdsm_current_use_rights_review_bytes()
    payload = json.loads(committed)
    artifact = build_family_a_rtdsm_current_use_rights_review()
    assert (
        FamilyARTDSMCurrentUseRightsReview.model_validate_json(committed, strict=True) == artifact
    )
    assert payload["accepted_phase22_commit_sha"] == ACCEPTED_PHASE22_SHA
    assert payload["accepted_phase22_tree_sha"] == BASELINE_TREE
    assert payload["phase22_merge_commit_sha"] == BASELINE_SHA
    assert payload["outcome"] == "BLOCKED"
    assert payload["review_state"] == "PUBLIC_TERMS_RIGHTS_REVIEW_FROZEN"
    assert payload["aggregate_conclusion"] == (
        "BLOCKED_PUBLIC_TERMS_INSUFFICIENT_FOR_PERSISTENT_AUTOMATED_MODEL_USE"
    )
    assert len(payload["public_terms_sources"]) == 3
    assert len(payload["rights_findings"]) == 1
    assert len(payload["future_requirements"]) == 4
    assert all(
        row["official_source"]
        and row["citation_inert"]
        and not row["terms_body_persisted"]
        and not row["remote_response_body_persisted"]
        for row in payload["public_terms_sources"]
    )
    finding = payload["rights_findings"][0]
    assert finding["research_purpose"] == "EXPRESSLY_PERMITTED_RESEARCH_PURPOSE_ONLY"
    for field in (
        "persistent_storage",
        "automated_model_internal_use",
        "derived_data",
        "retention_deletion",
        "redistribution",
        "attribution",
    ):
        assert finding[field] == "NOT_EXPRESSLY_ADDRESSED"
    assert not finding["operational_use_cleared"]
    assert [row["state"] for row in payload["future_requirements"]] == [
        "OUTPUT_FROZEN_BLOCKED",
        "NOT_STARTED",
        "NOT_STARTED",
        "BLOCKED",
    ]
    assert all(not row["satisfied"] for row in payload["future_requirements"])
    for field, expected in c.PHASE23_BOUNDARY_VALUES.items():
        assert payload[field] is expected


def test_phase23_freezes_api_migrations_dependencies_and_phase22() -> None:
    verifier = verifier_module()
    migration_root = ROOT / "services/api/migrations/versions"
    expected_migrations = set(verifier.PHASE_1_7_MIGRATION_SHA256) | {
        "services/api/migrations/versions/0008_phase10_local_paper.py",
        verifier.PHASE_12_MIGRATION,
        verifier.PHASE_13_MIGRATION,
        verifier.PHASE_14_MIGRATION,
    }
    assert {path.relative_to(ROOT).as_posix() for path in migration_root.glob("*.py")} == (
        expected_migrations
    )
    for frozen_path in (
        "compose.yaml",
        "package.json",
        "package-lock.json",
        "packages/contracts/openapi.json",
        "packages/contracts/src/api.generated.ts",
        "packages/contracts/src/runtime.generated.ts",
        "pyproject.toml",
        "requirements.lock",
        "scripts/run_phase_gate.py",
        "docs/PHASE_22_FAMILY_A_MACRO_VINTAGE_CANDIDATE_INVENTORY_AMENDMENT.json",
    ):
        assert (ROOT / frozen_path).read_bytes() == git_blob(BASELINE_SHA, frozen_path)
    for path in sorted((ROOT / "services/data/src/fable5_data/phase22").glob("*.py")):
        relative = path.relative_to(ROOT).as_posix()
        assert path.read_bytes() == git_blob(BASELINE_SHA, relative)
    openapi = json.loads((ROOT / "packages/contracts/openapi.json").read_text(encoding="utf-8"))
    assert not any(
        "phase23" in path.casefold() or "rtdsm" in path.casefold() for path in openapi["paths"]
    )
    assert '"23": "0011_phase14"' in normalized(ROOT / "tests/test_phase5_postgres.py")


def test_phase23_domain_and_cli_deny_transport_database_and_mutation() -> None:
    domain_paths = tuple(sorted((ROOT / "services/data/src/fable5_data/phase23").glob("*.py")))
    generator = ROOT / "scripts/generate_family_a_rtdsm_current_use_rights_review.py"
    verifier = ROOT / "scripts/verify_family_a_rtdsm_current_use_rights_review.py"
    forbidden = {
        "aiohttp",
        "asyncio",
        "fastapi",
        "fable5_api",
        "fable5_jobs",
        "fable5_paper",
        "fable5_research",
        "http",
        "httpx",
        "os",
        "psycopg",
        "random",
        "redis",
        "requests",
        "rq",
        "secrets",
        "socket",
        "sqlalchemy",
        "sqlite3",
        "ssl",
        "subprocess",
        "time",
        "urllib",
    }
    assert not imported_module_roots(domain_paths) & forbidden
    generator_source = normalized(generator)
    verifier_source = normalized(verifier)
    assert generator_source.count('"--confirm-public-terms-rights-review-only"') == 1
    assert verifier_source.count('"--review"') == 1
    for source in (generator_source, verifier_source):
        assert 'event.startswith("socket.")' in source
        assert 'frozenset({"os.system", "subprocess.Popen"})' in source
        assert "sys.addaudithook(_offline_audit_hook)" in source
        assert "_prove_offline_boundary()" in source
        assert source.count("subprocess.Popen(") == 1
        assert "subprocess.run(" not in source


def test_phase23_ci_wrappers_full_gate_and_docs_are_active(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    verifier = verifier_module()
    source = normalized(ROOT / "scripts/verify_phase1.py")
    for required in (
        "verify_phase23_portable_acceptance(",
        "verify_phase23_offline_network_denial(",
        "snapshot_phase23_inherited_state(",
        "verify_phase23_no_schema_drift_and_zero_writes(",
        'print("Full Compose Phase 23 verification passed.")',
        'default=os.environ.get("FABLE5_VERIFY_PHASE", "23")',
    ):
        assert required in source
    assert verifier.phase23_offline_environment()["FABLE5_VERIFY_PHASE"] == "23"
    for name in verifier.PHASE_23_CREDENTIAL_ENV_NAMES:
        monkeypatch.setenv(name, "phase23-ambient-secret-canary")
    acceptance, _api_url, _frontend_url = verifier.acceptance_environment(23)
    assert all(name not in acceptance for name in verifier.PHASE_23_CREDENTIAL_ENV_NAMES)

    workflow = normalized(ROOT / ".github/workflows/ci.yml")
    assert workflow.startswith("name: phase-23-ci\n")
    assert 'FABLE5_VERIFY_PHASE: "23"' in workflow
    assert "phase23-compose:" in workflow
    assert workflow.count("python scripts/verify_phase1.py --phase 23") == 1
    assert workflow.count("python scripts/verify_phase1.py --static-only --phase 23") == 1
    assert "secrets." not in workflow
    for entrypoint in ("scripts/check.ps1", "scripts/check.sh", "Makefile"):
        wrapper = normalized(ROOT / entrypoint)
        assert "FABLE5_VERIFY_PHASE" in wrapper
        assert "21, 22, or 23" in wrapper
    for path in (
        ROOT / "services/frontend/e2e/phase8.accessibility.spec.ts",
        ROOT / "services/frontend/e2e/phase8.visual.spec.ts",
    ):
        browser = normalized(path)
        assert 'process.env.FABLE5_VERIFY_PHASE ?? "23"' in browser
        assert '"21",\n  "22",\n  "23",' in browser

    decisions = normalized(
        ROOT / "docs/PHASE_23_FAMILY_A_RTDSM_CURRENT_USE_RIGHTS_REVIEW_DECISIONS.md"
    )
    handoff = normalized(ROOT / "docs/handoffs/PHASE_23.md")
    combined = decisions + handoff
    for required in (
        ACCEPTED_PHASE22_SHA,
        BASELINE_TREE,
        BASELINE_SHA,
        ARTIFACT_PATH,
        "PUBLIC_TERMS_RIGHTS_REVIEW_FROZEN",
        "BLOCKED_PUBLIC_TERMS_INSUFFICIENT_FOR_PERSISTENT_AUTOMATED_MODEL_USE",
        "adds no migration",
        "Stop after Phase 23",
        "Phase 24",
    ):
        assert required in combined
    assert not (ROOT / "docs/handoffs/PHASE_24.md").exists()
    assert not (ROOT / "services/data/src/fable5_data/phase24").exists()
