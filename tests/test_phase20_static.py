from __future__ import annotations

import argparse
import ast
import importlib.util
import inspect
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest
from fable5_data.phase20.canonical import (
    PHASE20_ACCEPTED_PHASE19_COMMIT_SHA,
    PHASE20_ACCEPTED_PHASE19_TREE_SHA,
    PHASE20_AGGREGATE_CONCLUSION,
    PHASE20_ARTIFACT_SCHEMA_VERSION,
    PHASE20_BOUNDARY_VALUES,
    PHASE20_FUTURE_EVIDENCE_ROWS,
    PHASE20_INPUT_REQUIREMENT_ROWS,
    PHASE20_OUTCOME,
    PHASE20_REGISTER_POLICY_ID,
    PHASE20_REGISTER_STATE,
    PHASE20_TRANSITION_RULE_ROWS,
)
from fable5_data.phase20.input_register import (
    build_family_a_evaluation_holdout_input_register,
    canonical_evaluation_holdout_input_register_bytes,
)

ROOT = Path(__file__).resolve().parents[1]
BASELINE_SHA = "86ddcafacff43b42fe56346745d7e6f08eaf3a52"
BASELINE_TREE = "6b6c2693a969e80cac9013d441ba607565d8914a"
ARTIFACT_PATH = "docs/PHASE_20_FAMILY_A_EVALUATION_HOLDOUT_INPUT_REGISTER.json"
GENERATOR_PATH = "scripts/generate_family_a_evaluation_holdout_input_register.py"
PORTABLE_VERIFIER_PATH = "scripts/verify_family_a_evaluation_holdout_input_register.py"
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
        "docs/PHASE_20_FAMILY_A_EVALUATION_HOLDOUT_INPUT_REGISTER_DECISIONS.md",
        "docs/RISK_POLICY.md",
        "docs/handoffs/PHASE_20.md",
        "scripts/check.ps1",
        "scripts/check.sh",
        GENERATOR_PATH,
        PORTABLE_VERIFIER_PATH,
        "scripts/verify_phase1.py",
        "services/data/src/fable5_data/phase20/__init__.py",
        "services/data/src/fable5_data/phase20/canonical.py",
        "services/data/src/fable5_data/phase20/contracts.py",
        "services/data/src/fable5_data/phase20/input_register.py",
        "services/data/tests/test_phase20_contracts.py",
        "services/data/tests/test_phase20_input_register.py",
        "services/data/tests/test_phase20_security.py",
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
        "tests/test_phase20_portable.py",
        "tests/test_phase20_static.py",
        "tests/test_repository_policy.py",
    }
)


def normalized(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def verifier_module() -> ModuleType:
    path = ROOT / "scripts/verify_phase1.py"
    spec = importlib.util.spec_from_file_location("phase20_verifier", path)
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


def test_phase20_baseline_parser_allowlist_and_static_inheritance_are_exact() -> None:
    verifier = verifier_module()
    assert verifier.PHASE_20_BASELINE_SHA == BASELINE_SHA
    assert verifier.EXPECTED_PHASE_20_BASELINE_TREE == BASELINE_TREE
    assert verifier.PHASE_20_ARTIFACT_PATH == ARTIFACT_PATH
    assert verifier.PHASE_20_ALLOWED_WRITES == ALLOWED_WRITES
    assert len(verifier.PHASE_20_ALLOWED_WRITES) == 40
    assert verifier.PHASE_20_INHERITED_TABLES == verifier.PHASE_19_INHERITED_TABLES
    assert len(verifier.PHASE_20_INHERITED_TABLES) == 57
    assert [verifier.phase_number(str(value)) for value in range(1, 25)] == list(range(1, 25))
    for invalid in ("0", "25", "not-a-phase"):
        with pytest.raises(argparse.ArgumentTypeError):
            verifier.phase_number(invalid)

    phase19 = inspect.signature(verifier.verify_phase19_static).parameters
    assert tuple(phase19) == ("release_closure", "active_phase")
    assert phase19["release_closure"].default is True
    assert phase19["active_phase"].default == 19
    phase20 = inspect.signature(verifier.verify_phase20_static).parameters
    assert tuple(phase20) == ("release_closure", "active_phase")
    assert phase20["release_closure"].default is True
    assert phase20["active_phase"].default == 20
    source = normalized(ROOT / "scripts/verify_phase1.py")
    branch = source.split("if phase == 20:", 1)[1].split("verify_static_inherited(phase)", 1)[0]
    for required in (
        "verify_static_inherited(20, announce=False)",
        "verify_phase10_static(release_closure=False, active_phase=20)",
        "verify_phase11_static(release_closure=False, active_phase=20)",
        "verify_phase12_static(release_closure=False, active_phase=20)",
        "verify_phase13_static(release_closure=False, active_phase=20)",
        "verify_phase14_static(release_closure=False, active_phase=20)",
        "verify_phase15_static(release_closure=False, active_phase=20)",
        "verify_phase16_static(release_closure=False, active_phase=20)",
        "verify_phase17_static(release_closure=False, active_phase=20)",
        "verify_phase18_static(release_closure=False, active_phase=20)",
        "verify_phase19_static(release_closure=False, active_phase=20)",
        "verify_phase20_static()",
    ):
        assert required in branch


def test_phase20_artifact_binds_exact_registers_and_closed_authority() -> None:
    committed = (ROOT / ARTIFACT_PATH).read_bytes()
    assert committed == canonical_evaluation_holdout_input_register_bytes()
    payload = json.loads(committed)
    artifact = build_family_a_evaluation_holdout_input_register()

    assert payload == artifact.model_dump(mode="json")
    assert payload["schema_version"] == PHASE20_ARTIFACT_SCHEMA_VERSION
    assert payload["input_register_policy_id"] == PHASE20_REGISTER_POLICY_ID
    assert payload["accepted_phase19_commit_sha"] == BASELINE_SHA
    assert payload["accepted_phase19_tree_sha"] == BASELINE_TREE
    assert PHASE20_ACCEPTED_PHASE19_COMMIT_SHA == BASELINE_SHA
    assert PHASE20_ACCEPTED_PHASE19_TREE_SHA == BASELINE_TREE
    assert payload["outcome"] == PHASE20_OUTCOME == "BLOCKED"
    assert payload["register_state"] == PHASE20_REGISTER_STATE == "INPUTS_FROZEN"
    assert payload["aggregate_conclusion"] == PHASE20_AGGREGATE_CONCLUSION
    assert len(payload["input_requirements"]) == len(PHASE20_INPUT_REQUIREMENT_ROWS) == 20
    assert tuple(item["code"] for item in payload["input_requirements"]) == tuple(
        row[1] for row in PHASE20_INPUT_REQUIREMENT_ROWS
    )
    assert tuple(item["evidence_state"] for item in payload["input_requirements"]) == tuple(
        row[3] for row in PHASE20_INPUT_REQUIREMENT_ROWS
    )
    assert all(not item["input_value_present"] for item in payload["input_requirements"])
    assert all(not item["resolves_reserved_evidence"] for item in payload["input_requirements"])
    assert len(payload["transition_rules"]) == len(PHASE20_TRANSITION_RULE_ROWS) == 10
    assert tuple(item["code"] for item in payload["transition_rules"]) == tuple(
        row[0] for row in PHASE20_TRANSITION_RULE_ROWS
    )
    assert all(not item["applied"] for item in payload["transition_rules"])
    assert (
        tuple(
            (item["name"], item["state"], item["produced"], item["reason_code"])
            for item in payload["required_prior_evidence"]
        )
        == PHASE20_FUTURE_EVIDENCE_ROWS
    )
    assert all(
        not {"value", "evidence_sha256", "produced_sha256", "output_sha256"}.intersection(item)
        for item in payload["required_prior_evidence"]
    )
    assert len(payload["inherited_phase19_prerequisites"]) == 19
    assert all(item["unchanged"] for item in payload["inherited_phase19_prerequisites"])
    assert len(payload["construction_dependency_groups"]) == 6
    assert all(item["state"] == "BLOCKED" for item in payload["construction_dependency_groups"])
    assert len(payload["construction_gates"]) == 6
    assert all(
        item["state"] == "BLOCKED" and not item["passed"] for item in payload["construction_gates"]
    )
    assert len(payload["forbidden_substitutes"]) == 8
    assert all(item["forbidden"] for item in payload["forbidden_substitutes"])
    assert len(payload["phase15_gap_bindings"]) == 19
    assert all(not item["changed_in_phase20"] for item in payload["phase15_gap_bindings"])
    assert len(payload["source_plan_steps"]) == 7
    assert all(not item["changed_in_phase20"] for item in payload["source_plan_steps"])
    assert all(not item["external_action_authorized"] for item in payload["source_plan_steps"])
    assert tuple(item["state"] for item in payload["source_plan_steps"]) == (
        "OUTPUT_FROZEN",
        "OUTPUT_FROZEN",
        "NOT_STARTED",
        "NOT_STARTED",
        "NOT_STARTED",
        "NOT_STARTED",
        "NOT_STARTED",
    )
    assert "qualification_artifact_set_sha256" not in json.dumps(payload, sort_keys=True)
    assert "non_synthetic_evaluation_policy_sha256" not in payload
    assert "confirmation_holdout_definition_sha256" not in payload
    for field, expected in PHASE20_BOUNDARY_VALUES.items():
        assert payload[field] is expected


def test_phase20_has_no_api_migration_dependency_compose_or_runner_surface() -> None:
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
    for path in expected_migrations:
        assert (ROOT / path).read_bytes() == git_blob(BASELINE_SHA, path)
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
        "docs/PHASE_19_FAMILY_A_STEP3_PREREQUISITE_ASSESSMENT.json",
    ):
        assert (ROOT / frozen_path).read_bytes() == git_blob(BASELINE_SHA, frozen_path)
    openapi = json.loads((ROOT / "packages/contracts/openapi.json").read_text(encoding="utf-8"))
    assert not any(
        "phase20" in path.casefold()
        or "input-register" in path.casefold()
        or "evaluation-holdout" in path.casefold()
        for path in openapi["paths"]
    )
    assert '"20": "0011_phase14"' in normalized(ROOT / "tests/test_phase5_postgres.py")
    runner = normalized(ROOT / "scripts/run_phase_gate.py")
    assert "choices=(9,)" in runner
    assert '"--phase", "20"' not in runner


def test_phase20_ast_and_cli_contract_deny_transport_database_and_mutation() -> None:
    domain_paths = tuple(sorted((ROOT / "services/data/src/fable5_data/phase20").glob("*.py")))
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
    assert generator.count('"--confirm-input-register-only"') == 1
    assert portable_verifier.count('"--register"') == 1
    for cli in (generator, portable_verifier):
        for required in (
            'event.startswith("socket.")',
            'frozenset({"os.system", "subprocess.Popen"})',
            "sys.addaudithook(_offline_audit_hook)",
            "_install_offline_boundary()",
            "_prove_socket_construction_is_denied()",
            "_prove_subprocess_construction_is_denied()",
        ):
            assert required in cli
        assert cli.index("_install_offline_boundary()", cli.index("def main")) < cli.index(
            "_parser().parse_args", cli.index("def main")
        )
        assert cli.index(
            "_prove_subprocess_construction_is_denied()", cli.index("def main")
        ) < cli.index("_parser().parse_args", cli.index("def main"))
        assert cli.count("subprocess.Popen(") == 1
        assert "subprocess.run(" not in cli
    for forbidden_option in (
        "--provider",
        "--product",
        "--url",
        "--credential",
        "--token",
        "--secret",
        "--rights",
        "--data",
        "--output",
        "--authority",
        "--policy",
        "--threshold",
        "--interval",
        "--holdout",
        "--strategy",
        "--signal",
        "--side",
        "--quantity",
        "--broker",
        "--order",
        "--execution",
        "--ingestion",
        "--promotion",
        "--expected-hash",
        "--repair",
    ):
        assert forbidden_option not in generator
        assert forbidden_option not in portable_verifier


def test_phase20_inherited_ci_wrappers_browser_zero_write_cleanup_and_runner_denial_are_active(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    verifier = verifier_module()
    source = normalized(ROOT / "scripts/verify_phase1.py")
    for required in (
        "verify_phase20_portable_acceptance(",
        "verify_phase20_offline_network_denial(",
        "snapshot_phase20_inherited_state(",
        "verify_phase20_no_schema_drift_and_zero_writes(",
        'version != "0011_phase14"',
        'print("Full Compose Phase 20 verification passed.")',
        'default=os.environ.get("FABLE5_VERIFY_PHASE", "24")',
    ):
        assert required in source
    assert verifier.phase20_offline_environment()["FABLE5_VERIFY_PHASE"] == "20"
    for name in verifier.PHASE_20_CREDENTIAL_ENV_NAMES:
        monkeypatch.setenv(name, "phase20-ambient-secret-canary")
    acceptance, _api_url, _frontend_url = verifier.acceptance_environment(20)
    assert all(name not in acceptance for name in verifier.PHASE_20_CREDENTIAL_ENV_NAMES)

    workflow = normalized(ROOT / ".github/workflows/ci.yml")
    assert workflow.startswith("name: phase-24-ci\n")
    assert 'FABLE5_VERIFY_PHASE: "24"' in workflow
    assert "phase24-compose:" in workflow
    assert workflow.count("python scripts/verify_phase1.py --phase 24") == 1
    assert workflow.count("python scripts/verify_phase1.py --static-only --phase 24") == 1
    assert "timeout-minutes: 180" in workflow
    assert "fetch-depth: 0" in workflow
    assert "secrets." not in workflow
    assert "run_phase_gate.py run --phase 20" not in workflow
    for credential_name in verifier.PHASE_20_CREDENTIAL_ENV_NAMES:
        assert f'{credential_name}: ""' in workflow
    for entrypoint in ("scripts/check.ps1", "scripts/check.sh", "Makefile"):
        wrapper = normalized(ROOT / entrypoint)
        assert "FABLE5_VERIFY_PHASE" in wrapper
        assert "--phase" in wrapper
        assert "22, 23, or 24" in wrapper
        assert "25" not in wrapper.split("must be one of", 1)[1].split(".", 1)[0]
    for path in (
        ROOT / "services/frontend/e2e/phase8.accessibility.spec.ts",
        ROOT / "services/frontend/e2e/phase8.visual.spec.ts",
    ):
        browser = normalized(path)
        assert 'process.env.FABLE5_VERIFY_PHASE ?? "24"' in browser
        assert '"20",\n  "21",\n  "22",' in browser

    runner = ROOT / "scripts/run_phase_gate.py"
    for phase in (20, 21, 22):
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


def test_phase20_docs_preserve_register_only_semantics_after_phase21_authorization() -> None:
    decisions = normalized(
        ROOT / "docs/PHASE_20_FAMILY_A_EVALUATION_HOLDOUT_INPUT_REGISTER_DECISIONS.md"
    )
    handoff = normalized(ROOT / "docs/handoffs/PHASE_20.md")
    combined = decisions + handoff
    for required in (
        BASELINE_SHA,
        BASELINE_TREE,
        ARTIFACT_PATH,
        "INPUTS_FROZEN",
        "BLOCKED_MISSING_OPERATIONAL_AND_DATA_SPECIFIC_INPUTS",
        "adds no migration",
        "Stop after Phase 20",
        "Phase 21",
    ):
        assert required in combined
    assert "do not begin" in " ".join(combined.casefold().split())
    assert (ROOT / "docs/handoffs/PHASE_21.md").exists()
    assert (ROOT / "services/data/src/fable5_data/phase21").exists()
