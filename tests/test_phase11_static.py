from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
BASELINE_SHA = "3acd25f5bb4bcbeec684f672c3b816562d2366dc"
BASELINE_TREE = "88929434b0e13ea2a7c3e4baf9c00d08c69fb276"
BUNDLE_PATH = "/v1/local-simulations/{simulation_run_id}/evidence-bundle"
BUNDLE_VERSION = "phase11-local-simulation-evidence-bundle-v1"
BUNDLE_FIELDS = {
    "bundle_schema_version",
    "bundle_sha256",
    "simulation_run_id",
    "simulation_artifact_sha256",
    "simulation",
}
IMMUTABLE_PLAYWRIGHT_IMAGE = (
    "mcr.microsoft.com/playwright:v1.61.1-noble@"
    "sha256:5b8f294aff9041b7191c34a4bab3ac270157a28774d4b0660e9743297b697e48"
)


def normalized(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")


def imported_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", 1)[0])
    return roots


def verifier_module() -> ModuleType:
    path = ROOT / "scripts/verify_phase1.py"
    spec = importlib.util.spec_from_file_location("phase11_verifier", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_phase11_baseline_parser_and_exact_allowlist_are_frozen() -> None:
    verifier = verifier_module()
    assert verifier.PHASE_11_BASELINE_SHA == BASELINE_SHA
    assert verifier.EXPECTED_PHASE_11_BASELINE_TREE == BASELINE_TREE
    assert verifier.PHASE_11_BUNDLE_SCHEMA_VERSION == BUNDLE_VERSION
    assert verifier.PHASE_11_BUNDLE_PATH == BUNDLE_PATH
    assert [verifier.phase_number(str(phase)) for phase in range(1, 20)] == list(range(1, 20))
    for invalid in ("0", "20", "not-a-phase"):
        with pytest.raises(argparse.ArgumentTypeError):
            verifier.phase_number(invalid)

    expected_allowed_writes = {
        ".github/workflows/ci.yml",
        "Makefile",
        "README.md",
        "docs/IMPLEMENTATION_PLAN.md",
        "docs/PHASE_11_PORTABLE_SIMULATION_EVIDENCE_DECISIONS.md",
        "docs/handoffs/PHASE_11.md",
        "packages/contracts/openapi.json",
        "packages/contracts/src/api.generated.ts",
        "packages/contracts/src/phase11-contract.type-test.ts",
        "packages/contracts/src/runtime.generated.ts",
        "scripts/check.ps1",
        "scripts/check.sh",
        "scripts/verify_local_simulation_evidence.py",
        "scripts/verify_phase1.py",
        "services/api/src/fable5_api/local_simulations.py",
        "services/api/src/fable5_api/main.py",
        "services/api/tests/test_phase11_openapi_contract.py",
        "services/api/tests/test_phase11_routes.py",
        "services/frontend/e2e/phase8.accessibility.spec.ts",
        "services/frontend/e2e/phase8.visual.spec.ts",
        "services/frontend/e2e/phase11.accessibility.spec.ts",
        "services/frontend/e2e/phase11.fixtures.ts",
        "services/frontend/src/app/paper/PaperStatusWorkspace.tsx",
        "services/frontend/src/app/phase8.css",
        "services/frontend/src/components/LocalEvidenceBundleExport.tsx",
        "services/frontend/src/lib/api.ts",
        "services/frontend/src/lib/local-evidence-download.ts",
        "services/frontend/src/tests/ApiClient.test.ts",
        "services/frontend/src/tests/LocalEvidenceBundleExport.test.tsx",
        "services/frontend/src/tests/LocalEvidenceDownload.test.ts",
        "services/frontend/src/tests/PaperStatusWorkspace.test.tsx",
        "services/paper/README.md",
        "services/paper/src/fable5_paper/evidence.py",
        "services/paper/src/fable5_paper/workflow.py",
        "services/paper/tests/test_phase11_evidence_bundle.py",
        "tests/test_phase10_static.py",
        "tests/test_phase11_local_simulation_evidence.py",
        "tests/test_phase11_static.py",
        "tests/test_phase5_postgres.py",
        "tests/test_phase9_static.py",
        "tests/test_repository_policy.py",
    }
    assert verifier.PHASE_11_ALLOWED_WRITES == expected_allowed_writes


def test_phase11_openapi_bundle_and_generated_contract_are_exact() -> None:
    schema = json.loads((ROOT / "packages/contracts/openapi.json").read_text(encoding="utf-8"))
    path_item = schema["paths"][BUNDLE_PATH]
    assert set(path_item) & {"get", "post", "put", "patch", "delete"} == {"get"}
    operation = path_item["get"]
    assert "requestBody" not in operation
    assert len(operation["parameters"]) == 1
    parameter = operation["parameters"][0]
    assert parameter["name"] == "simulation_run_id"
    assert parameter["in"] == "path"
    assert parameter["required"] is True
    assert parameter["schema"]["type"] == "string"
    assert parameter["schema"]["format"] == "uuid"
    assert set(operation["responses"]) == {"200", "404", "409", "422"}

    bundle = schema["components"]["schemas"]["LocalSimulationEvidenceBundle"]
    assert set(bundle["properties"]) == BUNDLE_FIELDS
    assert set(bundle["required"]) == BUNDLE_FIELDS
    assert bundle["additionalProperties"] is False
    assert bundle["properties"]["bundle_schema_version"] == {
        "type": "string",
        "const": BUNDLE_VERSION,
        "title": "Bundle Schema Version",
    }
    assert bundle["properties"]["simulation"] == {
        "$ref": "#/components/schemas/PaperSimulationArtifact"
    }

    generated = normalized(ROOT / "packages/contracts/src/api.generated.ts")
    runtime = normalized(ROOT / "packages/contracts/src/runtime.generated.ts")
    type_test = normalized(ROOT / "packages/contracts/src/phase11-contract.type-test.ts")
    for required in ("LocalSimulationEvidenceBundle:", f'"{BUNDLE_PATH}"'):
        assert required in generated
    assert "LocalSimulationEvidenceBundle" in runtime
    assert "@ts-expect-error" in type_test


def test_phase11_is_database_free_network_disabled_and_preserved_by_phase12() -> None:
    evidence_path = ROOT / "services/paper/src/fable5_paper/evidence.py"
    cli_path = ROOT / "scripts/verify_local_simulation_evidence.py"
    forbidden_imports = {
        "aiohttp",
        "asyncio",
        "httpx",
        "requests",
        "socket",
        "sqlalchemy",
        "urllib",
        "urllib3",
    }
    assert not (imported_roots(evidence_path) & forbidden_imports)
    assert not (imported_roots(cli_path) & {"httpx", "requests", "sqlalchemy", "urllib"})

    cli = normalized(cli_path)
    for required in (
        "--bundle",
        "--expected-bundle-sha256",
        "MAX_BUNDLE_BYTES = 1024 * 1024",
        "MAX_NUMERIC_COEFFICIENT_DIGITS = 256",
        "MAX_NUMERIC_ABS_EXPONENT = 1_000",
        "sys.addaudithook",
        "socket.",
        "subprocess.Popen",
        "os.system",
    ):
        assert required in cli
    for forbidden in ("FABLE5_DATABASE_URL", "create_simulation"):
        assert forbidden not in cli

    migration_root = ROOT / "services/api/migrations/versions"
    migration = migration_root / "0008_phase10_local_paper.py"
    repository = ROOT / "services/paper/src/fable5_paper/repository.py"
    assert hashlib.sha256(migration.read_bytes()).hexdigest() == (
        "947293ff5c6b471045479aee280904346a6ef03733ec2b8e92dc03b87a30e405"
    )
    assert hashlib.sha256(repository.read_bytes()).hexdigest() == (
        "80c01c826bb4f6720fea332d0401a9896537de5f1bfec5b82607d68bdd953fe0"
    )


def test_phase11_linux_browser_is_read_only_pinned_and_never_updates_snapshots() -> None:
    verifier = verifier_module()
    command = verifier.phase11_linux_playwright_command(
        "phase11-test",
        "http://127.0.0.1:3000",
    )
    assert command[command.index("--mount") + 1].endswith(",readonly")
    assert command.count(IMMUTABLE_PLAYWRIGHT_IMAGE) == 1
    assert command.count("FABLE5_VERIFY_PHASE=11") == 1
    assert command.count("e2e/phase11.accessibility.spec.ts") == 1
    assert "FABLE5_UPDATE_SNAPSHOTS=1" not in command
    assert "FABLE5_VISUAL_CORPUS=synthetic" not in command

    workflow = normalized(ROOT / ".github/workflows/ci.yml")
    assert workflow.startswith("name: phase-19-ci\n")
    assert 'FABLE5_VERIFY_PHASE: "19"' in workflow
    assert "phase19-compose:" in workflow
    assert "timeout-minutes: 180" in workflow
    assert workflow.count(f"docker pull {IMMUTABLE_PLAYWRIGHT_IMAGE}") == 1
    assert workflow.count("python scripts/verify_phase1.py --phase 19") == 1
    assert "FABLE5_UPDATE_SNAPSHOTS" not in workflow
    assert "--update-snapshots" not in workflow


def test_phase11_full_verifier_binds_zero_write_cleanup_and_same_git_identity() -> None:
    source = normalized(ROOT / "scripts/verify_phase1.py")
    for required in (
        'phase10_clean_git_identity("preflight", phase=phase)',
        'verify_phase10_acceptance_resource_namespace(\n            "preflight"',
        "verify_phase11_api(",
        "verify_phase11_browser(",
        'verify_phase10_acceptance_resource_namespace(\n                        "post-cleanup"',
        'phase10_clean_git_identity(\n                        "post-cleanup"',
        "snapshot_tables(project, environment, all_tables)",
        "verify_phase9_compose_cleanup(project, environment, phase=phase)",
        'print("Full Compose Phase 11 verification passed.")',
    ):
        assert required in source
    assert "if phase in {10, 11, 12, 13, 14, 15, 16, 17, 18, 19}:" in source
    assert "if phase in {11, 12, 13, 14, 15, 16, 17, 18, 19}:" in source
    assert "verify_phase12_api(" in source
    assert 'default=os.environ.get("FABLE5_VERIFY_PHASE", "19")' in source


def test_phase11_docs_freeze_integrity_only_and_hard_stop() -> None:
    decisions = normalized(ROOT / "docs/PHASE_11_PORTABLE_SIMULATION_EVIDENCE_DECISIONS.md")
    handoff = normalized(ROOT / "docs/handoffs/PHASE_11.md")
    combined = decisions + handoff
    for required in (
        BASELINE_SHA,
        BASELINE_TREE,
        BUNDLE_VERSION,
        BUNDLE_PATH,
        "database-free",
        "network-disabled",
        "not a signature",
        "proof of current authority",
        "Local simulation evidence verification failed.",
        "no migration",
        "Stop after Phase 11",
        "Do not push",
        "Phase 12",
    ):
        assert required in combined
    for field in BUNDLE_FIELDS:
        assert f"`{field}`" in decisions
