from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest
from fable5_data.phase21.canonical import (
    PHASE21_ACCEPTED_PHASE20_COMMIT_SHA,
    PHASE21_ACCEPTED_PHASE20_TREE_SHA,
    PHASE21_AGGREGATE_CONCLUSION,
    PHASE21_ARTIFACT_SCHEMA_VERSION,
    PHASE21_BOUNDARY_VALUES,
    PHASE21_CANDIDATE_GROUP_ROWS,
    PHASE21_CAPABILITY_ROWS,
    PHASE21_DECISION_FIELD_ROWS,
    PHASE21_FORBIDDEN_SUBSTITUTE_ROWS,
    PHASE21_FUTURE_RULE_ROWS,
    PHASE21_GATE_ROWS,
    PHASE21_OUTCOME,
    PHASE21_POST_SELECTION_DEPENDENCY_ROWS,
    PHASE21_PRODUCT_RIGHTS_ROWS,
    PHASE21_REQUIREMENTS_STATE,
)
from fable5_data.phase21.decision_requirements import (
    build_family_a_operational_composition_decision_requirements,
    canonical_operational_composition_decision_requirements_bytes,
)

ROOT = Path(__file__).resolve().parents[1]
BASELINE_SHA = "01ed1ff17b91ba6961e02cdf1df3aa3e6be4859a"
BASELINE_TREE = "b7a68998f1c99ed8b19ab08ae8a725726f04c423"
ARTIFACT_PATH = "docs/PHASE_21_FAMILY_A_OPERATIONAL_COMPOSITION_DECISION_REQUIREMENTS.json"
GENERATOR_PATH = "scripts/generate_family_a_operational_composition_decision_requirements.py"
PORTABLE_VERIFIER_PATH = "scripts/verify_family_a_operational_composition_decision_requirements.py"
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
        "docs/PHASE_21_FAMILY_A_OPERATIONAL_COMPOSITION_DECISION_REQUIREMENTS_DECISIONS.md",
        "docs/RISK_POLICY.md",
        "docs/handoffs/PHASE_21.md",
        "scripts/check.ps1",
        "scripts/check.sh",
        GENERATOR_PATH,
        PORTABLE_VERIFIER_PATH,
        "scripts/verify_phase1.py",
        "services/data/src/fable5_data/phase21/__init__.py",
        "services/data/src/fable5_data/phase21/canonical.py",
        "services/data/src/fable5_data/phase21/contracts.py",
        "services/data/src/fable5_data/phase21/decision_requirements.py",
        "services/data/tests/test_phase21_contracts.py",
        "services/data/tests/test_phase21_decision_requirements.py",
        "services/data/tests/test_phase21_security.py",
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
        "tests/test_phase21_portable.py",
        "tests/test_phase21_static.py",
        "tests/test_repository_policy.py",
    }
)


def normalized(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")


def verifier_module() -> ModuleType:
    path = ROOT / "scripts/verify_phase1.py"
    spec = importlib.util.spec_from_file_location("phase21_verifier", path)
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


def test_phase21_baseline_parser_allowlist_and_static_inheritance_are_exact() -> None:
    verifier = verifier_module()
    assert verifier.PHASE_21_BASELINE_SHA == BASELINE_SHA
    assert verifier.EXPECTED_PHASE_21_BASELINE_TREE == BASELINE_TREE
    assert verifier.PHASE_21_ARTIFACT_PATH == ARTIFACT_PATH
    assert verifier.PHASE_21_ALLOWED_WRITES == ALLOWED_WRITES
    assert len(verifier.PHASE_21_ALLOWED_WRITES) == 41
    assert verifier.PHASE_21_INHERITED_TABLES == verifier.PHASE_20_INHERITED_TABLES
    assert len(verifier.PHASE_21_INHERITED_TABLES) == 57
    assert [verifier.phase_number(str(value)) for value in range(1, 22)] == list(range(1, 22))
    for invalid in ("0", "22", "not-a-phase"):
        with pytest.raises(argparse.ArgumentTypeError):
            verifier.phase_number(invalid)

    source = normalized(ROOT / "scripts/verify_phase1.py")
    branch = source.split("if phase == 21:", 1)[1].split("verify_static_inherited(phase)", 1)[0]
    for phase in range(10, 21):
        assert f"verify_phase{phase}_static(release_closure=False, active_phase=21)" in branch
    for required in (
        "verify_static_inherited(21, announce=False)",
        "verify_phase21_static()",
        'print("Static repository policy checks passed for Phase 21.")',
    ):
        assert required in branch


def test_phase21_artifact_binds_exact_requirements_and_closed_authority() -> None:
    committed = (ROOT / ARTIFACT_PATH).read_bytes()
    assert committed == canonical_operational_composition_decision_requirements_bytes()
    payload = json.loads(committed)
    artifact = build_family_a_operational_composition_decision_requirements()

    assert payload == artifact.model_dump(mode="json")
    assert payload["schema_version"] == PHASE21_ARTIFACT_SCHEMA_VERSION
    assert payload["accepted_phase20_commit_sha"] == BASELINE_SHA
    assert payload["accepted_phase20_tree_sha"] == BASELINE_TREE
    assert PHASE21_ACCEPTED_PHASE20_COMMIT_SHA == BASELINE_SHA
    assert PHASE21_ACCEPTED_PHASE20_TREE_SHA == BASELINE_TREE
    assert payload["outcome"] == PHASE21_OUTCOME == "BLOCKED"
    assert (
        payload["requirements_state"]
        == PHASE21_REQUIREMENTS_STATE
        == "DECISION_REQUIREMENTS_FROZEN"
    )
    assert payload["aggregate_conclusion"] == PHASE21_AGGREGATE_CONCLUSION
    assert payload["aggregate_conclusion"] == (
        "BLOCKED_AWAITING_EXPLICIT_OPERATIONAL_SOURCE_PRODUCT_COMPOSITION"
    )

    assert len(payload["candidate_group_bindings"]) == len(PHASE21_CANDIDATE_GROUP_ROWS) == 6
    assert len(payload["product_rights_bindings"]) == len(PHASE21_PRODUCT_RIGHTS_ROWS) == 9
    assert len(payload["capability_assignments"]) == len(PHASE21_CAPABILITY_ROWS) == 7
    assert len(payload["decision_fields"]) == len(PHASE21_DECISION_FIELD_ROWS) == 8
    assert (
        len(payload["post_selection_dependencies"])
        == len(PHASE21_POST_SELECTION_DEPENDENCY_ROWS)
        == 3
    )
    assert len(payload["decision_gates"]) == len(PHASE21_GATE_ROWS) == 6
    assert len(payload["future_rules"]) == len(PHASE21_FUTURE_RULE_ROWS) == 8
    assert len(payload["forbidden_substitutes"]) == len(PHASE21_FORBIDDEN_SUBSTITUTE_ROWS) == 10
    assert len(payload["inherited_phase20_input_requirements"]) == 20
    assert len(payload["required_prior_evidence"]) == 2
    assert len(payload["phase15_gap_bindings"]) == 19
    assert len(payload["source_plan_steps"]) == 7

    assert all(
        item["candidate_only"] and not item["operationally_selected"] and not item["ranked"]
        for item in payload["candidate_group_bindings"]
    )
    assert all(
        not item["operationally_selected"] and not item["current_rights_verified"]
        for item in payload["product_rights_bindings"]
    )
    assert all(
        item["assignment_state"] == "UNASSIGNED"
        and item["assigned_product_codes"] == []
        and not item["assignment_value_present"]
        for item in payload["capability_assignments"]
    )
    assert all(
        item["required"] and not item["value_present"] and not item["evidence_produced"]
        for item in payload["decision_fields"]
    )
    assert all(
        item["state"] == "BLOCKED_BY_MISSING_COMPOSITION" and not item["satisfied"]
        for item in payload["post_selection_dependencies"]
    )
    assert all(
        item["state"] == "BLOCKED" and not item["passed"] for item in payload["decision_gates"]
    )
    assert all(
        item["future_only"] and not item["applied"] and not item["external_action_authorized"]
        for item in payload["future_rules"]
    )
    assert all(item["forbidden"] for item in payload["forbidden_substitutes"])
    assert all(item["unchanged"] for item in payload["inherited_phase20_input_requirements"])
    assert all(not item["changed_in_phase21"] for item in payload["phase15_gap_bindings"])
    assert tuple(item["state"] for item in payload["source_plan_steps"]) == (
        "OUTPUT_FROZEN",
        "OUTPUT_FROZEN",
        "NOT_STARTED",
        "NOT_STARTED",
        "NOT_STARTED",
        "NOT_STARTED",
        "NOT_STARTED",
    )
    for field, expected in PHASE21_BOUNDARY_VALUES.items():
        assert payload[field] is expected
    assert "operational_composition_output_sha256" not in payload
    assert "selection_evidence_sha256" not in payload


def test_phase21_frozen_surfaces_have_no_api_migration_dependency_or_runner_drift() -> None:
    verifier = verifier_module()
    assert set(verifier.PHASE_21_REQUIRED_PATHS) <= ALLOWED_WRITES
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
        "docs/PHASE_20_FAMILY_A_EVALUATION_HOLDOUT_INPUT_REGISTER.json",
    ):
        assert (ROOT / frozen_path).read_bytes() == git_blob(BASELINE_SHA, frozen_path)
    for phase20_path in sorted((ROOT / "services/data/src/fable5_data/phase20").glob("*.py")):
        relative = phase20_path.relative_to(ROOT).as_posix()
        assert phase20_path.read_bytes() == git_blob(BASELINE_SHA, relative)

    openapi = json.loads((ROOT / "packages/contracts/openapi.json").read_text(encoding="utf-8"))
    assert not any(
        "phase21" in path.casefold()
        or "operational-composition" in path.casefold()
        or "decision-requirements" in path.casefold()
        for path in openapi["paths"]
    )
    assert '"21": "0011_phase14"' in normalized(ROOT / "tests/test_phase5_postgres.py")
    runner = normalized(ROOT / "scripts/run_phase_gate.py")
    assert "choices=(9,)" in runner
    assert '"--phase", "21"' not in runner


def test_phase21_ast_and_cli_contract_deny_transport_database_and_mutation() -> None:
    domain_paths = tuple(sorted((ROOT / "services/data/src/fable5_data/phase21").glob("*.py")))
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
    assert generator.count('"--confirm-decision-requirements-only"') == 1
    assert portable_verifier.count('"--requirements"') == 1
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


def test_phase21_ci_wrappers_browser_zero_write_cleanup_and_phase22_denial_are_active(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    verifier = verifier_module()
    source = normalized(ROOT / "scripts/verify_phase1.py")
    for required in (
        "verify_phase21_portable_acceptance(",
        "verify_phase21_offline_network_denial(",
        "snapshot_phase21_inherited_state(",
        "verify_phase21_no_schema_drift_and_zero_writes(",
        'version != "0011_phase14"',
        'print("Full Compose Phase 21 verification passed.")',
        'default=os.environ.get("FABLE5_VERIFY_PHASE", "21")',
    ):
        assert required in source
    assert verifier.phase21_offline_environment()["FABLE5_VERIFY_PHASE"] == "21"
    for name in verifier.PHASE_21_CREDENTIAL_ENV_NAMES:
        monkeypatch.setenv(name, "phase21-ambient-secret-canary")
    acceptance, _api_url, _frontend_url = verifier.acceptance_environment(21)
    assert all(name not in acceptance for name in verifier.PHASE_21_CREDENTIAL_ENV_NAMES)

    workflow = normalized(ROOT / ".github/workflows/ci.yml")
    assert workflow.startswith("name: phase-21-ci\n")
    assert 'FABLE5_VERIFY_PHASE: "21"' in workflow
    assert "phase21-compose:" in workflow
    assert workflow.count("python scripts/verify_phase1.py --phase 21") == 1
    assert workflow.count("python scripts/verify_phase1.py --static-only --phase 21") == 1
    assert "timeout-minutes: 180" in workflow
    assert "fetch-depth: 0" in workflow
    assert "secrets." not in workflow
    assert "run_phase_gate.py run --phase 21" not in workflow
    for credential_name in verifier.PHASE_21_CREDENTIAL_ENV_NAMES:
        assert f'{credential_name}: ""' in workflow
    for entrypoint in ("scripts/check.ps1", "scripts/check.sh", "Makefile"):
        wrapper = normalized(ROOT / entrypoint)
        assert "FABLE5_VERIFY_PHASE" in wrapper
        assert "--phase" in wrapper
        assert "20, or 21" in wrapper
        assert "22" not in wrapper.split("must be one of", 1)[1].split(".", 1)[0]
    for path in (
        ROOT / "services/frontend/e2e/phase8.accessibility.spec.ts",
        ROOT / "services/frontend/e2e/phase8.visual.spec.ts",
    ):
        browser = normalized(path)
        assert 'process.env.FABLE5_VERIFY_PHASE ?? "21"' in browser
        assert '"19",\n  "20",\n  "21",' in browser

    runner = ROOT / "scripts/run_phase_gate.py"
    for phase in (21, 22):
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


def test_phase21_docs_stop_before_phase22_and_preserve_requirements_only_semantics() -> None:
    decisions = normalized(
        ROOT / "docs/PHASE_21_FAMILY_A_OPERATIONAL_COMPOSITION_DECISION_REQUIREMENTS_DECISIONS.md"
    )
    handoff = normalized(ROOT / "docs/handoffs/PHASE_21.md")
    combined = decisions + handoff
    for required in (
        BASELINE_SHA,
        BASELINE_TREE,
        ARTIFACT_PATH,
        "DECISION_REQUIREMENTS_FROZEN",
        "BLOCKED_AWAITING_EXPLICIT_OPERATIONAL_SOURCE_PRODUCT_COMPOSITION",
        "adds no migration",
        "Stop after Phase 21",
        "Phase 22",
    ):
        assert required in combined
    assert "do not begin" in " ".join(combined.casefold().split())
    assert not (ROOT / "docs/handoffs/PHASE_22.md").exists()
    assert not (ROOT / "services/data/src/fable5_data/phase22").exists()
