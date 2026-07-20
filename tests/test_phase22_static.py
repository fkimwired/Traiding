from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest
from fable5_data.phase22.canonical import (
    PHASE22_ACCEPTED_PHASE21_COMMIT_SHA,
    PHASE22_ACCEPTED_PHASE21_TREE_SHA,
    PHASE22_AGGREGATE_CONCLUSION,
    PHASE22_AMENDMENT_STATE,
    PHASE22_ARTIFACT_SCHEMA_VERSION,
    PHASE22_BOUNDARY_VALUES,
    PHASE22_CANDIDATE_GROUP_ROWS,
    PHASE22_OUTCOME,
    PHASE22_PRODUCT_ROWS,
    PHASE22_REQUIREMENT_ROWS,
    PHASE22_SOURCE_ROWS,
)
from fable5_data.phase22.inventory_amendment import (
    build_family_a_macro_vintage_candidate_inventory_amendment,
    canonical_macro_vintage_candidate_inventory_amendment_bytes,
)

ROOT = Path(__file__).resolve().parents[1]
BASELINE_SHA = "a25ffb5cb68014c301a588c0e8cf7c7f18914e0a"
BASELINE_TREE = "8744604b486dd7398cd8c5a003fe7c7b083fde86"
ARTIFACT_PATH = "docs/PHASE_22_FAMILY_A_MACRO_VINTAGE_CANDIDATE_INVENTORY_AMENDMENT.json"
GENERATOR_PATH = "scripts/generate_family_a_macro_vintage_candidate_inventory_amendment.py"
PORTABLE_VERIFIER_PATH = "scripts/verify_family_a_macro_vintage_candidate_inventory_amendment.py"
ALLOWED_WRITES = frozenset(
    {
        ".github/workflows/ci.yml",
        "Makefile",
        "README.md",
        "docs/COMPLIANCE_NOTES.md",
        "docs/DATA_SOURCES.md",
        "docs/EVALS.md",
        "docs/IMPLEMENTATION_PLAN.md",
        ARTIFACT_PATH,
        "docs/PHASE_22_FAMILY_A_MACRO_VINTAGE_CANDIDATE_INVENTORY_AMENDMENT_DECISIONS.md",
        "docs/RISK_POLICY.md",
        "docs/handoffs/PHASE_22.md",
        "scripts/check.ps1",
        "scripts/check.sh",
        GENERATOR_PATH,
        PORTABLE_VERIFIER_PATH,
        "scripts/verify_phase1.py",
        "services/data/src/fable5_data/phase22/__init__.py",
        "services/data/src/fable5_data/phase22/canonical.py",
        "services/data/src/fable5_data/phase22/contracts.py",
        "services/data/src/fable5_data/phase22/inventory_amendment.py",
        "services/data/tests/test_phase22_contracts.py",
        "services/data/tests/test_phase22_inventory_amendment.py",
        "services/data/tests/test_phase22_security.py",
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
        "tests/test_phase16_static.py",
        "tests/test_phase17_static.py",
        "tests/test_phase18_static.py",
        "tests/test_phase19_static.py",
        "tests/test_phase20_static.py",
        "tests/test_phase21_static.py",
        "tests/test_phase22_portable.py",
        "tests/test_phase22_static.py",
        "tests/test_repository_policy.py",
    }
)


def normalized(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")


def verifier_module() -> ModuleType:
    path = ROOT / "scripts/verify_phase1.py"
    spec = importlib.util.spec_from_file_location("phase22_verifier", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def imported_module_roots(paths: tuple[Path, ...]) -> set[str]:
    imported: set[str] = set()
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imported.add(node.module.split(".", 1)[0])
    return imported


def git_blob(commit: str, path: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout


def test_phase22_baseline_parser_allowlist_and_static_inheritance_are_exact() -> None:
    verifier = verifier_module()
    assert verifier.PHASE_22_BASELINE_SHA == BASELINE_SHA
    assert verifier.EXPECTED_PHASE_22_BASELINE_TREE == BASELINE_TREE
    assert verifier.PHASE_22_ARTIFACT_PATH == ARTIFACT_PATH
    assert verifier.PHASE_22_ALLOWED_WRITES == ALLOWED_WRITES
    assert len(verifier.PHASE_22_ALLOWED_WRITES) == 42
    assert verifier.PHASE_22_INHERITED_TABLES == verifier.PHASE_21_INHERITED_TABLES
    assert len(verifier.PHASE_22_INHERITED_TABLES) == 57
    assert [verifier.phase_number(str(value)) for value in range(1, 23)] == list(range(1, 23))
    for invalid in ("0", "23", "not-a-phase"):
        with pytest.raises(argparse.ArgumentTypeError):
            verifier.phase_number(invalid)

    source = normalized(ROOT / "scripts/verify_phase1.py")
    branch = source.split("if phase == 22:", 1)[1].split("verify_static_inherited(phase)", 1)[0]
    for phase in range(10, 22):
        assert f"verify_phase{phase}_static(release_closure=False, active_phase=22)" in branch
    for required in (
        "verify_static_inherited(22, announce=False)",
        "verify_phase22_static()",
        'print("Static repository policy checks passed for Phase 22.")',
    ):
        assert required in branch


def test_phase22_artifact_is_additive_candidate_only_and_preserves_prior_states() -> None:
    committed = (ROOT / ARTIFACT_PATH).read_bytes()
    assert committed == canonical_macro_vintage_candidate_inventory_amendment_bytes()
    payload = json.loads(committed)
    artifact = build_family_a_macro_vintage_candidate_inventory_amendment()
    assert artifact.__class__.model_validate_json(committed, strict=True) == artifact
    assert payload["schema_version"] == PHASE22_ARTIFACT_SCHEMA_VERSION
    assert payload["accepted_phase21_commit_sha"] == BASELINE_SHA
    assert payload["accepted_phase21_tree_sha"] == BASELINE_TREE
    assert PHASE22_ACCEPTED_PHASE21_COMMIT_SHA == BASELINE_SHA
    assert PHASE22_ACCEPTED_PHASE21_TREE_SHA == BASELINE_TREE
    assert payload["outcome"] == PHASE22_OUTCOME == "BLOCKED"
    assert payload["amendment_state"] == PHASE22_AMENDMENT_STATE
    assert payload["aggregate_conclusion"] == PHASE22_AGGREGATE_CONCLUSION
    assert len(payload["official_sources"]) == len(PHASE22_SOURCE_ROWS) == 3
    assert len(payload["candidate_group_amendments"]) == len(PHASE22_CANDIDATE_GROUP_ROWS) == 1
    assert len(payload["candidate_products"]) == len(PHASE22_PRODUCT_ROWS) == 1
    assert len(payload["future_review_requirements"]) == len(PHASE22_REQUIREMENT_ROWS) == 4
    assert all(
        row["official_source"] and row["citation_inert"] and not row["remote_body_included"]
        for row in payload["official_sources"]
    )
    assert all(
        row["candidate_only"] and not row["operationally_selected"] and not row["ranked"]
        for row in payload["candidate_group_amendments"]
    )
    product = payload["candidate_products"][0]
    assert product["product_code"] == "PHILADELPHIA_FED_REAL_TIME_DATA_SET_FOR_MACROECONOMISTS"
    assert product["capability_codes"] == ["macro_regime_inputs"]
    assert product["candidate_only"] is True
    assert product["review_routing_state"] == (
        "NAMED_FOR_INDEPENDENT_CURRENT_RIGHTS_AND_FITNESS_REVIEW"
    )
    assert product["operationally_selected"] is False
    assert product["ranked"] is False
    assert product["entitlement_state"] == "UNPROVEN"
    assert product["rights_state"] == "NOT_REVIEWED"
    assert product["fitness_state"] == "UNPROVEN"
    assert product["month_vintage_labels_are_exact_release_timestamps"] is False
    assert product["bls_release_archive_reconciliation_required"] is True
    for field in (
        "coverage_proven",
        "schema_proven",
        "current_availability_proven",
        "external_sample_qualified",
        "persistent_storage_model_derived_retention_rights_reviewed",
    ):
        assert product[field] is False
    assert all(
        not row["external_action_authorized"] and not row["satisfied"]
        for row in payload["future_review_requirements"]
    )
    for field, expected in PHASE22_BOUNDARY_VALUES.items():
        assert payload[field] is expected
    assert payload["inherited_fred_finding_unchanged"] is True
    assert payload["phase21_decision_requirements_unchanged"] is True
    assert "selection_evidence_sha256" not in payload
    assert "operational_source_product_composition_sha256" not in payload
    assert "phase18_rights_finding_sha256" not in product


def test_phase22_frozen_surfaces_have_no_api_migration_dependency_or_runner_drift() -> None:
    verifier = verifier_module()
    assert set(verifier.PHASE_22_REQUIRED_PATHS) <= ALLOWED_WRITES
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
        "docs/PHASE_21_FAMILY_A_OPERATIONAL_COMPOSITION_DECISION_REQUIREMENTS.json",
    ):
        assert (ROOT / frozen_path).read_bytes() == git_blob(BASELINE_SHA, frozen_path)
    for phase21_path in sorted((ROOT / "services/data/src/fable5_data/phase21").glob("*.py")):
        relative = phase21_path.relative_to(ROOT).as_posix()
        assert phase21_path.read_bytes() == git_blob(BASELINE_SHA, relative)

    openapi = json.loads((ROOT / "packages/contracts/openapi.json").read_text(encoding="utf-8"))
    assert not any(
        "phase22" in path.casefold()
        or "macro-vintage" in path.casefold()
        or "inventory-amendment" in path.casefold()
        for path in openapi["paths"]
    )
    assert '"22": "0011_phase14"' in normalized(ROOT / "tests/test_phase5_postgres.py")
    runner = normalized(ROOT / "scripts/run_phase_gate.py")
    assert "choices=(9,)" in runner
    assert '"--phase", "22"' not in runner


def test_phase22_ast_and_cli_contract_deny_transport_database_and_mutation() -> None:
    domain_paths = tuple(sorted((ROOT / "services/data/src/fable5_data/phase22").glob("*.py")))
    generator_path = ROOT / GENERATOR_PATH
    verifier_path = ROOT / PORTABLE_VERIFIER_PATH
    shared_forbidden = {
        "aiohttp",
        "alpaca",
        "asyncio",
        "fastapi",
        "fable5_api",
        "fable5_jobs",
        "fable5_paper",
        "fable5_research",
        "http",
        "httpx",
        "psycopg",
        "random",
        "redis",
        "requests",
        "rq",
        "sqlalchemy",
        "sqlite3",
        "subprocess",
        "time",
        "urllib",
        "websocket",
        "websockets",
    }
    assert not (
        imported_module_roots(domain_paths)
        & (shared_forbidden | {"os", "secrets", "socket", "ssl"})
    )
    cli_forbidden = shared_forbidden - {"subprocess"}
    assert not (
        imported_module_roots((generator_path,)) & (cli_forbidden | {"os", "secrets", "ssl"})
    )
    assert not (imported_module_roots((verifier_path,)) & (cli_forbidden | {"secrets", "ssl"}))
    production = "\n".join(path.read_text(encoding="utf-8") for path in domain_paths)
    for forbidden in (
        "datetime.now",
        "datetime.utcnow",
        "getenv(",
        "environ[",
        "uuid4(",
        "create_engine(",
        "FastAPI(",
        "requests.",
        "httpx.",
        "socket.",
        "subprocess.",
        "submit_order",
        "place_order",
        "create_order",
    ):
        assert forbidden not in production
    generator = normalized(generator_path)
    portable_verifier = normalized(verifier_path)
    assert generator.count('"--confirm-candidate-inventory-amendment-only"') == 1
    assert portable_verifier.count('"--amendment"') == 1
    for cli in (generator, portable_verifier):
        for required in (
            'event.startswith("socket.")',
            'frozenset({"os.system", "subprocess.Popen"})',
            "sys.addaudithook(_offline_audit_hook)",
            "_prove_offline_boundary()",
        ):
            assert required in cli
        main = cli.index("def main")
        parser = cli.index("_parser().parse_args", main)
        assert cli.index("sys.addaudithook(_offline_audit_hook)", main) < parser
        assert cli.index("_prove_offline_boundary()", main) < parser
        assert cli.count("subprocess.Popen(") == 1
        assert "subprocess.run(" not in cli


def test_phase22_ci_wrappers_browser_zero_write_cleanup_and_phase23_denial_are_active(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    verifier = verifier_module()
    source = normalized(ROOT / "scripts/verify_phase1.py")
    for required in (
        "verify_phase22_portable_acceptance(",
        "verify_phase22_offline_network_denial(",
        "snapshot_phase22_inherited_state(",
        "verify_phase22_no_schema_drift_and_zero_writes(",
        'version != "0011_phase14"',
        'print("Full Compose Phase 22 verification passed.")',
        'default=os.environ.get("FABLE5_VERIFY_PHASE", "22")',
    ):
        assert required in source
    assert verifier.phase22_offline_environment()["FABLE5_VERIFY_PHASE"] == "22"
    for name in verifier.PHASE_22_CREDENTIAL_ENV_NAMES:
        monkeypatch.setenv(name, "phase22-ambient-secret-canary")
    acceptance, _api_url, _frontend_url = verifier.acceptance_environment(22)
    assert all(name not in acceptance for name in verifier.PHASE_22_CREDENTIAL_ENV_NAMES)

    workflow = normalized(ROOT / ".github/workflows/ci.yml")
    assert workflow.startswith("name: phase-22-ci\n")
    assert 'FABLE5_VERIFY_PHASE: "22"' in workflow
    assert "phase22-compose:" in workflow
    assert workflow.count("python scripts/verify_phase1.py --phase 22") == 1
    assert workflow.count("python scripts/verify_phase1.py --static-only --phase 22") == 1
    assert "timeout-minutes: 180" in workflow
    assert "fetch-depth: 0" in workflow
    assert "secrets." not in workflow
    assert "run_phase_gate.py run --phase 22" not in workflow
    for credential_name in verifier.PHASE_22_CREDENTIAL_ENV_NAMES:
        assert f'{credential_name}: ""' in workflow
    for entrypoint in ("scripts/check.ps1", "scripts/check.sh", "Makefile"):
        wrapper = normalized(ROOT / entrypoint)
        assert "FABLE5_VERIFY_PHASE" in wrapper
        assert "--phase" in wrapper
        assert "20, 21, or 22" in wrapper
        assert "23" not in wrapper.split("must be one of", 1)[1].split(".", 1)[0]
    for path in (
        ROOT / "services/frontend/e2e/phase8.accessibility.spec.ts",
        ROOT / "services/frontend/e2e/phase8.visual.spec.ts",
    ):
        browser = normalized(path)
        assert 'process.env.FABLE5_VERIFY_PHASE ?? "22"' in browser
        assert '"20",\n  "21",\n  "22",' in browser
    assert re.search(
        r"if phase in \{\s*8,\s*9,\s*10,\s*11,\s*12,\s*13,\s*14,\s*15,\s*"
        r"16,\s*17,\s*18,\s*19,\s*20,\s*21,\s*22,\s*\}:\s*"
        r"verify_phase8_browser\(",
        source,
    )

    runner = ROOT / "scripts/run_phase_gate.py"
    for phase in (22, 23):
        result = subprocess.run(
            [
                sys.executable,
                str(runner),
                "run",
                "--phase",
                str(phase),
                "--evidence-dir",
                str(ROOT.parent / f"phase{phase}-forbidden-runner-evidence"),
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 2
        assert result.stdout == ""


def test_phase22_docs_stop_before_phase23_and_preserve_candidate_only_semantics() -> None:
    decisions = normalized(
        ROOT / "docs/PHASE_22_FAMILY_A_MACRO_VINTAGE_CANDIDATE_INVENTORY_AMENDMENT_DECISIONS.md"
    )
    handoff = normalized(ROOT / "docs/handoffs/PHASE_22.md")
    combined = decisions + handoff
    for required in (
        BASELINE_SHA,
        BASELINE_TREE,
        ARTIFACT_PATH,
        "CANDIDATE_INVENTORY_AMENDMENT_FROZEN",
        "BLOCKED_AWAITING_CURRENT_RIGHTS_FITNESS_REVIEW_AND_EXPLICIT_OPERATIONAL_COMPOSITION",
        "adds no migration",
        "Stop after Phase 22",
        "Phase 23",
    ):
        assert required in combined
    assert "candidate-only" in combined.casefold()
    assert not (ROOT / "docs/handoffs/PHASE_23.md").exists()
    assert not (ROOT / "services/data/src/fable5_data/phase23").exists()
