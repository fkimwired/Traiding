from __future__ import annotations

import argparse
import ast
import importlib.util
import inspect
import json
import subprocess
from pathlib import Path
from types import ModuleType

import pytest
from fable5_data.phase19.assessment import (
    build_family_a_step3_prerequisite_assessment,
    canonical_step3_prerequisite_assessment_bytes,
)
from fable5_data.phase19.canonical import (
    PHASE19_ACCEPTED_PHASE18_COMMIT_SHA,
    PHASE19_ACCEPTED_PHASE18_TREE_SHA,
    PHASE19_AGGREGATE_CONCLUSION,
    PHASE19_ARTIFACT_SCHEMA_VERSION,
    PHASE19_ASSESSMENT_POLICY_ID,
    PHASE19_ASSESSMENT_STATE,
    PHASE19_BOUNDARY_VALUES,
    PHASE19_FROZEN_AT_UTC,
    PHASE19_GAP_CODES,
    PHASE19_GAP_STATES,
    PHASE19_OUTCOME,
    PHASE19_PREREQUISITE_ROWS,
    PHASE19_REQUIRED_EVIDENCE_ROWS,
    PHASE19_SOURCE_GAP_SHA256S,
    PHASE19_STEP_CODES,
    PHASE19_STEP_STATES,
)
from fable5_data.phase19.contracts import (
    gap_bindings_manifest_sha256,
    prerequisites_manifest_sha256,
    required_evidence_manifest_sha256,
    steps_manifest_sha256,
)

ROOT = Path(__file__).resolve().parents[1]
BASELINE_SHA = "16aac187fc3dbd6015306603c18be6e08cea8e4e"
BASELINE_TREE = "b36ae615f13f39d0e661f18d1cc61e009b1aacf7"
ARTIFACT_PATH = "docs/PHASE_19_FAMILY_A_STEP3_PREREQUISITE_ASSESSMENT.json"
GENERATOR_PATH = "scripts/generate_family_a_step3_prerequisite_assessment.py"
PORTABLE_VERIFIER_PATH = "scripts/verify_family_a_step3_prerequisite_assessment.py"
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
        "docs/PHASE_19_FAMILY_A_STEP3_PREREQUISITE_ASSESSMENT_DECISIONS.md",
        "docs/RISK_POLICY.md",
        "docs/handoffs/PHASE_19.md",
        "scripts/check.ps1",
        "scripts/check.sh",
        GENERATOR_PATH,
        PORTABLE_VERIFIER_PATH,
        "scripts/verify_phase1.py",
        "services/data/src/fable5_data/phase19/__init__.py",
        "services/data/src/fable5_data/phase19/assessment.py",
        "services/data/src/fable5_data/phase19/canonical.py",
        "services/data/src/fable5_data/phase19/contracts.py",
        "services/data/tests/test_phase19_assessment.py",
        "services/data/tests/test_phase19_contracts.py",
        "services/data/tests/test_phase19_security.py",
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
        "tests/test_phase19_portable.py",
        "tests/test_phase19_static.py",
        "tests/test_repository_policy.py",
    }
)


def normalized(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def verifier_module() -> ModuleType:
    path = ROOT / "scripts/verify_phase1.py"
    spec = importlib.util.spec_from_file_location("phase19_verifier", path)
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


def test_phase19_baseline_parser_allowlist_and_inherited_boundaries_are_exact() -> None:
    verifier = verifier_module()
    assert verifier.PHASE_19_BASELINE_SHA == BASELINE_SHA
    assert verifier.EXPECTED_PHASE_19_BASELINE_TREE == BASELINE_TREE
    assert verifier.PHASE_19_ARTIFACT_PATH == ARTIFACT_PATH
    assert verifier.PHASE_19_ALLOWED_WRITES == ALLOWED_WRITES
    assert len(verifier.PHASE_19_ALLOWED_WRITES) == 39
    assert verifier.PHASE_19_INHERITED_TABLES == verifier.PHASE_18_INHERITED_TABLES
    assert len(verifier.PHASE_19_INHERITED_TABLES) == 57
    assert [verifier.phase_number(str(value)) for value in range(1, 22)] == list(range(1, 22))
    for invalid in ("0", "22", "not-a-phase"):
        with pytest.raises(argparse.ArgumentTypeError):
            verifier.phase_number(invalid)

    phase18 = inspect.signature(verifier.verify_phase18_static).parameters
    assert tuple(phase18) == ("release_closure", "active_phase")
    assert phase18["release_closure"].default is True
    assert phase18["active_phase"].default == 18
    phase19 = inspect.signature(verifier.verify_phase19_static).parameters
    assert tuple(phase19) == ("release_closure", "active_phase")
    assert phase19["release_closure"].default is True
    assert phase19["active_phase"].default == 19
    source = normalized(ROOT / "scripts/verify_phase1.py")
    branch = source.split("if phase == 19:", 1)[1].split("verify_static_inherited(phase)", 1)[0]
    for required in (
        "verify_static_inherited(19, announce=False)",
        "verify_phase10_static(release_closure=False, active_phase=19)",
        "verify_phase11_static(release_closure=False, active_phase=19)",
        "verify_phase12_static(release_closure=False, active_phase=19)",
        "verify_phase13_static(release_closure=False, active_phase=19)",
        "verify_phase14_static(release_closure=False, active_phase=19)",
        "verify_phase15_static(release_closure=False, active_phase=19)",
        "verify_phase16_static(release_closure=False, active_phase=19)",
        "verify_phase17_static(release_closure=False, active_phase=19)",
        "verify_phase18_static(release_closure=False, active_phase=19)",
        "verify_phase19_static()",
    ):
        assert required in branch


def test_phase19_artifact_binds_exact_registries_manifests_and_closed_authority() -> None:
    committed = (ROOT / ARTIFACT_PATH).read_bytes()
    assert committed == canonical_step3_prerequisite_assessment_bytes()
    payload = json.loads(committed)
    artifact = build_family_a_step3_prerequisite_assessment()

    assert payload == artifact.model_dump(mode="json")
    assert payload["schema_version"] == PHASE19_ARTIFACT_SCHEMA_VERSION
    assert payload["assessment_policy_id"] == PHASE19_ASSESSMENT_POLICY_ID
    assert payload["accepted_phase18_commit_sha"] == BASELINE_SHA
    assert payload["accepted_phase18_tree_sha"] == BASELINE_TREE
    assert PHASE19_ACCEPTED_PHASE18_COMMIT_SHA == BASELINE_SHA
    assert PHASE19_ACCEPTED_PHASE18_TREE_SHA == BASELINE_TREE
    assert payload["frozen_at_utc"] == PHASE19_FROZEN_AT_UTC
    assert payload["outcome"] == PHASE19_OUTCOME == "BLOCKED"
    assert payload["assessment_state"] == PHASE19_ASSESSMENT_STATE == "OUTPUT_FROZEN"
    assert payload["aggregate_conclusion"] == PHASE19_AGGREGATE_CONCLUSION
    assert tuple(item["code"] for item in payload["prerequisites"]) == tuple(
        row[1] for row in PHASE19_PREREQUISITE_ROWS
    )
    assert (
        tuple(
            (item["name"], item["state"], item["produced"], item["reason_code"])
            for item in payload["required_prior_evidence"]
        )
        == PHASE19_REQUIRED_EVIDENCE_ROWS
    )
    assert tuple(item["code"] for item in payload["phase15_gap_bindings"]) == PHASE19_GAP_CODES
    assert tuple(item["state"] for item in payload["phase15_gap_bindings"]) == PHASE19_GAP_STATES
    assert (
        tuple(item["source_gap_sha256"] for item in payload["phase15_gap_bindings"])
        == PHASE19_SOURCE_GAP_SHA256S
    )
    assert tuple(item["code"] for item in payload["source_plan_steps"]) == PHASE19_STEP_CODES
    assert tuple(item["state"] for item in payload["source_plan_steps"]) == PHASE19_STEP_STATES
    assert tuple(
        len(payload[collection])
        for collection in (
            "prerequisites",
            "required_prior_evidence",
            "phase15_gap_bindings",
            "source_plan_steps",
        )
    ) == (19, 2, 19, 7)
    assert artifact.prerequisites_manifest_sha256 == prerequisites_manifest_sha256(
        artifact.prerequisites
    )
    assert artifact.required_prior_evidence_manifest_sha256 == (
        required_evidence_manifest_sha256(artifact.required_prior_evidence)
    )
    assert artifact.phase15_gap_bindings_manifest_sha256 == gap_bindings_manifest_sha256(
        artifact.phase15_gap_bindings
    )
    assert artifact.steps_manifest_sha256 == steps_manifest_sha256(artifact.source_plan_steps)
    assert all(not item["produced_outputs"] for item in payload["source_plan_steps"][2:])
    assert all(not item["external_action_authorized"] for item in payload["source_plan_steps"])
    assert all(not item["produced"] for item in payload["required_prior_evidence"])
    assert "non_synthetic_evaluation_policy_sha256" not in payload
    assert "confirmation_holdout_definition_sha256" not in payload
    for item in payload["required_prior_evidence"]:
        assert not {"value", "evidence_sha256", "produced_sha256"}.intersection(item)
    for field, expected in PHASE19_BOUNDARY_VALUES.items():
        assert payload[field] is expected


def test_phase19_has_no_api_migration_dependency_compose_or_runner_surface() -> None:
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
        "docs/PHASE_18_FAMILY_A_CURRENT_USE_RIGHTS_REVIEW.json",
    ):
        assert (ROOT / frozen_path).read_bytes() == git_blob(BASELINE_SHA, frozen_path)
    openapi = json.loads((ROOT / "packages/contracts/openapi.json").read_text(encoding="utf-8"))
    assert not any(
        "phase19" in path.casefold()
        or "step3" in path.casefold()
        or "prerequisite-assessment" in path.casefold()
        for path in openapi["paths"]
    )
    assert '"19": "0011_phase14"' in normalized(ROOT / "tests/test_phase5_postgres.py")
    runner = normalized(ROOT / "scripts/run_phase_gate.py")
    assert "choices=(9,)" in runner
    assert '"--phase", "19"' not in runner


def test_phase19_ast_and_cli_contract_deny_transport_database_and_mutation() -> None:
    domain_paths = tuple(sorted((ROOT / "services/data/src/fable5_data/phase19").glob("*.py")))
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
    assert not (
        imported_module_roots((generator_path,)) & (shared_forbidden | {"os", "secrets", "ssl"})
    )
    assert not (imported_module_roots((verifier_path,)) & (shared_forbidden | {"secrets", "ssl"}))
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
        "Popen(",
        "system(",
        "urlopen(",
        "submit_order",
        "place_order",
        "create_order",
    ):
        assert forbidden not in production
    generator = normalized(generator_path)
    portable_verifier = normalized(verifier_path)
    assert generator.count('"--confirm-prerequisite-assessment-only"') == 1
    assert portable_verifier.count('"--assessment"') == 1
    for cli in (generator, portable_verifier):
        for required in (
            'event.startswith("socket.")',
            'frozenset({"os.system", "subprocess.Popen"})',
            "sys.addaudithook(_offline_audit_hook)",
            "_install_offline_boundary()",
            "_prove_socket_construction_is_denied()",
        ):
            assert required in cli
        assert cli.index("_install_offline_boundary()", cli.index("def main")) < cli.index(
            "_parser().parse_args", cli.index("def main")
        )
        for forbidden_call in (
            "os.getenv(",
            "os.environ",
            "os.system(",
            "subprocess.Popen(",
            "subprocess.run(",
        ):
            assert forbidden_call not in cli
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


def test_phase19_ci_wrappers_browser_zero_write_and_secret_denial_are_active(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    verifier = verifier_module()
    source = normalized(ROOT / "scripts/verify_phase1.py")
    for required in (
        "verify_phase19_portable_acceptance(",
        "verify_phase19_offline_network_denial(",
        "snapshot_phase19_inherited_state(",
        "verify_phase19_no_schema_drift_and_zero_writes(",
        'version != "0011_phase14"',
        'print("Full Compose Phase 19 verification passed.")',
        'default=os.environ.get("FABLE5_VERIFY_PHASE", "21")',
    ):
        assert required in source
    assert verifier.phase19_offline_environment()["FABLE5_VERIFY_PHASE"] == "19"
    for name in verifier.PHASE_19_CREDENTIAL_ENV_NAMES:
        monkeypatch.setenv(name, "phase19-ambient-secret-canary")
    acceptance, _api_url, _frontend_url = verifier.acceptance_environment(19)
    assert all(name not in acceptance for name in verifier.PHASE_19_CREDENTIAL_ENV_NAMES)

    workflow = normalized(ROOT / ".github/workflows/ci.yml")
    assert workflow.startswith("name: phase-21-ci\n")
    assert 'FABLE5_VERIFY_PHASE: "21"' in workflow
    assert "phase21-compose:" in workflow
    assert workflow.count("python scripts/verify_phase1.py --phase 21") == 1
    assert workflow.count("python scripts/verify_phase1.py --static-only --phase 21") == 1
    assert "timeout-minutes: 180" in workflow
    assert "fetch-depth: 0" in workflow
    assert "secrets." not in workflow
    assert "run_phase_gate.py run --phase 19" not in workflow
    for credential_name in verifier.PHASE_19_CREDENTIAL_ENV_NAMES:
        assert f'{credential_name}: ""' in workflow
    for entrypoint in ("scripts/check.ps1", "scripts/check.sh", "Makefile"):
        wrapper = normalized(ROOT / entrypoint)
        assert "FABLE5_VERIFY_PHASE" in wrapper
        assert "--phase" in wrapper
        assert "20, or 21" in wrapper
    for path in (
        ROOT / "services/frontend/e2e/phase8.accessibility.spec.ts",
        ROOT / "services/frontend/e2e/phase8.visual.spec.ts",
    ):
        browser = normalized(path)
        assert 'process.env.FABLE5_VERIFY_PHASE ?? "21"' in browser
        assert '"19",\n  "20",\n  "21",' in browser


def test_phase19_docs_stop_before_phase20_and_preserve_assessment_only_semantics() -> None:
    decisions = normalized(
        ROOT / "docs/PHASE_19_FAMILY_A_STEP3_PREREQUISITE_ASSESSMENT_DECISIONS.md"
    )
    handoff = normalized(ROOT / "docs/handoffs/PHASE_19.md")
    combined = decisions + handoff
    for required in (
        BASELINE_SHA,
        BASELINE_TREE,
        ARTIFACT_PATH,
        "QUALIFY_BOUNDED_READ_ONLY_SAMPLES",
        "OUTPUT_FROZEN",
        "BLOCKED_MISSING_EVALUATION_POLICY_AND_HOLDOUT",
        "adds no migration",
        "Stop after Phase 19",
        "Do not begin",
        "Phase 20",
    ):
        assert required in combined
    assert (ROOT / "docs/handoffs/PHASE_20.md").exists()
    assert (ROOT / "services/data/src/fable5_data/phase20").exists()
