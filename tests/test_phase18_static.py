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
from fable5_data.phase18.canonical import (
    PHASE18_ACCEPTED_PHASE17_COMMIT_SHA,
    PHASE18_ACCEPTED_PHASE17_TREE_SHA,
    PHASE18_ARTIFACT_SCHEMA_VERSION,
    PHASE18_BOUNDARY_VALUES,
    PHASE18_FROZEN_AT_UTC,
    PHASE18_PHASE16_STEP2_SHA256,
    PHASE18_POLICY_ID,
    PHASE18_PRODUCT_ROWS,
    PHASE18_SOURCE_ROWS,
    PHASE18_STEP_CODES,
    PHASE18_STEP_STATES,
)
from fable5_data.phase18.rights_review import (
    build_family_a_current_use_rights_review,
    canonical_current_use_rights_review_bytes,
)

ROOT = Path(__file__).resolve().parents[1]
BASELINE_SHA = "fd89d3905e9c2ea12223e30b5822a0fdda795a26"
BASELINE_TREE = "f2eb791785dd10cc9316d174505b65eda919fe71"
ARTIFACT_PATH = "docs/PHASE_18_FAMILY_A_CURRENT_USE_RIGHTS_REVIEW.json"
GENERATOR_PATH = "scripts/generate_family_a_current_use_rights_review.py"
PORTABLE_VERIFIER_PATH = "scripts/verify_family_a_current_use_rights_review.py"
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
        "docs/PHASE_18_FAMILY_A_CURRENT_USE_RIGHTS_REVIEW_DECISIONS.md",
        "docs/RISK_POLICY.md",
        "docs/handoffs/PHASE_18.md",
        "scripts/check.ps1",
        "scripts/check.sh",
        GENERATOR_PATH,
        PORTABLE_VERIFIER_PATH,
        "scripts/verify_phase1.py",
        "services/data/src/fable5_data/phase18/__init__.py",
        "services/data/src/fable5_data/phase18/canonical.py",
        "services/data/src/fable5_data/phase18/contracts.py",
        "services/data/src/fable5_data/phase18/rights_review.py",
        "services/data/tests/test_phase18_contracts.py",
        "services/data/tests/test_phase18_rights_review.py",
        "services/data/tests/test_phase18_security.py",
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
        "tests/test_phase18_portable.py",
        "tests/test_phase18_static.py",
        "tests/test_repository_policy.py",
    }
)


def normalized(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def verifier_module() -> ModuleType:
    path = ROOT / "scripts/verify_phase1.py"
    spec = importlib.util.spec_from_file_location("phase18_verifier", path)
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


def test_phase18_baseline_parser_allowlist_and_inherited_boundaries_are_exact() -> None:
    verifier = verifier_module()
    assert verifier.PHASE_18_BASELINE_SHA == BASELINE_SHA
    assert verifier.EXPECTED_PHASE_18_BASELINE_TREE == BASELINE_TREE
    assert verifier.PHASE_18_ARTIFACT_PATH == ARTIFACT_PATH
    assert verifier.PHASE_18_ALLOWED_WRITES == ALLOWED_WRITES
    assert len(verifier.PHASE_18_ALLOWED_WRITES) == 38
    assert verifier.PHASE_18_INHERITED_TABLES == verifier.PHASE_17_INHERITED_TABLES
    assert len(verifier.PHASE_18_INHERITED_TABLES) == 57
    assert [verifier.phase_number(str(value)) for value in range(1, 26)] == list(range(1, 26))
    for invalid in ("0", "26", "not-a-phase"):
        with pytest.raises(argparse.ArgumentTypeError):
            verifier.phase_number(invalid)

    phase17 = inspect.signature(verifier.verify_phase17_static).parameters
    assert tuple(phase17) == ("release_closure", "active_phase")
    assert phase17["release_closure"].default is True
    assert phase17["active_phase"].default == 17
    source = normalized(ROOT / "scripts/verify_phase1.py")
    branch = source.split("if phase == 18:", 1)[1].split("verify_static_inherited(phase)", 1)[0]
    for required in (
        "verify_static_inherited(18, announce=False)",
        "verify_phase10_static(release_closure=False, active_phase=18)",
        "verify_phase11_static(release_closure=False, active_phase=18)",
        "verify_phase12_static(release_closure=False, active_phase=18)",
        "verify_phase13_static(release_closure=False, active_phase=18)",
        "verify_phase14_static(release_closure=False, active_phase=18)",
        "verify_phase15_static(release_closure=False, active_phase=18)",
        "verify_phase16_static(release_closure=False, active_phase=18)",
        "verify_phase17_static(release_closure=False, active_phase=18)",
        "verify_phase18_static()",
    ):
        assert required in branch


def test_phase18_artifact_binds_exact_sources_findings_steps_and_closed_authority() -> None:
    committed = (ROOT / ARTIFACT_PATH).read_bytes()
    assert committed == canonical_current_use_rights_review_bytes()
    payload = json.loads(committed)
    artifact = build_family_a_current_use_rights_review()

    assert payload == artifact.model_dump(mode="json")
    assert payload["schema_version"] == PHASE18_ARTIFACT_SCHEMA_VERSION
    assert payload["policy_id"] == PHASE18_POLICY_ID
    assert payload["accepted_phase17_commit_sha"] == BASELINE_SHA
    assert payload["accepted_phase17_tree_sha"] == BASELINE_TREE
    assert PHASE18_ACCEPTED_PHASE17_COMMIT_SHA == BASELINE_SHA
    assert PHASE18_ACCEPTED_PHASE17_TREE_SHA == BASELINE_TREE
    assert payload["phase16_step2_sha256"] == PHASE18_PHASE16_STEP2_SHA256
    assert payload["outcome"] == "BLOCKED"
    assert payload["aggregate_conclusion"] == "BLOCKED_NO_OPERATIONAL_SELECTION"
    assert payload["frozen_at_utc"] == PHASE18_FROZEN_AT_UTC
    assert tuple(item["product_code"] for item in payload["product_rights_findings"]) == tuple(
        row[0] for row in PHASE18_PRODUCT_ROWS
    )
    assert tuple(item["code"] for item in payload["terms_sources"]) == tuple(
        row[0] for row in PHASE18_SOURCE_ROWS
    )
    assert "external_request_performed" not in payload
    assert payload["official_public_documentation_access_performed"] is True
    assert payload["operational_external_request_performed"] is False
    assert all("source_payload_persisted" not in source for source in payload["terms_sources"])
    assert all(
        source["remote_source_response_body_persisted"] is False
        for source in payload["terms_sources"]
    )
    for finding, product_row in zip(
        payload["product_rights_findings"], PHASE18_PRODUCT_ROWS, strict=True
    ):
        assert finding["phase17_product_sha256"] == product_row[1]
        assert tuple(finding["source_codes"]) == product_row[2]
        assert (
            tuple(
                finding[field]
                for field in (
                    "storage",
                    "non_display_internal_use",
                    "derived_data",
                    "retention",
                    "redistribution",
                    "revocation_currentness",
                    "delivery",
                    "entitlement",
                )
            )
            == product_row[3:11]
        )
        assert finding["conclusion"] == product_row[11]
        assert finding["conservative_finding"] == product_row[12]
    for source, source_row in zip(payload["terms_sources"], PHASE18_SOURCE_ROWS, strict=True):
        assert (
            source["code"],
            source["official_title"],
            source["publisher"],
            source["official_url"],
            tuple(source["applies_to_product_codes"]),
            source["publisher_last_updated"],
            source["locator"],
            source["conservative_fact"],
            source["reviewed_at_utc"],
        ) == source_row
    findings_by_code = {
        finding["product_code"]: finding for finding in payload["product_rights_findings"]
    }
    fred = findings_by_code["FRED_REALTIME_AND_VINTAGE_WEB_SERVICE"]
    assert fred["non_display_internal_use"] == "PROHIBITED_PUBLIC_TERMS"
    assert (
        fred["conclusion"] == "INELIGIBLE_CURRENT_TERMS_PROHIBIT_PERSISTENCE_AND_SOFTWARE_MODEL_USE"
    )
    sources_by_code = {source["code"]: source for source in payload["terms_sources"]}
    assert "User-Agent" not in sources_by_code["SEC_DEVELOPER_RESOURCES"]["conservative_fact"]
    assert (
        "request rate at or below ten requests per second"
        in (sources_by_code["SEC_DEVELOPER_RESOURCES"]["conservative_fact"])
    )
    assert "User-Agent" in sources_by_code["SEC_ACCESSING_EDGAR"]["conservative_fact"]
    assert tuple(item["code"] for item in payload["source_plan_steps"]) == PHASE18_STEP_CODES
    assert tuple(item["state"] for item in payload["source_plan_steps"]) == PHASE18_STEP_STATES
    assert PHASE18_STEP_STATES == (
        "OUTPUT_FROZEN",
        "OUTPUT_FROZEN",
        "NOT_STARTED",
        "NOT_STARTED",
        "NOT_STARTED",
        "NOT_STARTED",
        "NOT_STARTED",
    )
    assert tuple(item["name"] for item in payload["source_plan_steps"][1]["produced_outputs"]) == (
        "independent_rights_review_sha256",
        "rights_currentness_sha256",
    )
    assert all(not item["external_action_authorized"] for item in payload["source_plan_steps"])
    assert all(not item["produced_outputs"] for item in payload["source_plan_steps"][2:])
    assert {item["storage"] for item in payload["product_rights_findings"]} <= {
        "ALLOWED_PUBLIC",
        "CONDITIONAL_ACCOUNT_LICENSE",
        "PRIVATE_LICENSE_REQUIRED",
        "PROHIBITED_PUBLIC_TERMS",
        "UNPROVEN",
    }
    for field, expected in PHASE18_BOUNDARY_VALUES.items():
        assert payload[field] is expected


def test_phase18_adds_no_migration_api_contract_dependency_compose_or_runner_drift() -> None:
    frozen_scopes = (
        "compose.yaml",
        "package.json",
        "package-lock.json",
        "requirements.lock",
        "pyproject.toml",
        "scripts/run_phase_gate.py",
        "packages/contracts",
        "services/api",
        "services/frontend/src",
    )
    result = subprocess.run(
        ["git", "diff", "--name-only", BASELINE_SHA, "--", *frozen_scopes],
        cwd=ROOT,
        capture_output=True,
        check=True,
        text=True,
    )
    assert result.stdout == ""
    assert not any("alembic" in path.casefold() for path in ALLOWED_WRITES)
    assert "scripts/run_phase_gate.py" not in ALLOWED_WRITES
    assert not any(path.startswith("packages/contracts/") for path in ALLOWED_WRITES)
    assert not any(path.startswith("services/api/") for path in ALLOWED_WRITES)
    assert '"18": "0011_phase14"' in normalized(ROOT / "tests/test_phase5_postgres.py")
    openapi = json.loads((ROOT / "packages/contracts/openapi.json").read_text(encoding="utf-8"))
    assert not any(
        "phase18" in path.casefold() or "rights-review" in path.casefold()
        for path in openapi["paths"]
    )


def test_phase18_ast_and_cli_contract_deny_transport_database_and_mutation() -> None:
    domain_paths = tuple(sorted((ROOT / "services/data/src/fable5_data/phase18").glob("*.py")))
    generator_path = ROOT / GENERATOR_PATH
    verifier_path = ROOT / PORTABLE_VERIFIER_PATH
    shared_forbidden = {
        "aiohttp",
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
        "uvicorn",
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
    ):
        assert forbidden not in production
    generator = normalized(generator_path)
    portable_verifier = normalized(verifier_path)
    assert generator.count('"--confirm-public-terms-review-only"') == 1
    assert portable_verifier.count('"--review"') == 1
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
        "--account",
        "--entitlement",
        "--source",
        "--status",
        "--rights",
        "--terms",
        "--body",
        "--clock",
        "--time",
        "--hash",
        "--data",
        "--output",
        "--authority",
        "--repair",
        "--expected-hash",
        "--capture",
        "--ingestion",
        "--research",
        "--order",
    ):
        assert forbidden_option not in generator
        assert forbidden_option not in portable_verifier


def test_phase18_ci_wrappers_browser_zero_write_and_secret_denial_are_active(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    verifier = verifier_module()
    source = normalized(ROOT / "scripts/verify_phase1.py")
    for required in (
        "verify_phase18_portable_acceptance(",
        "verify_phase18_offline_network_denial(",
        "snapshot_phase18_inherited_state(",
        "verify_phase18_no_schema_drift_and_zero_writes(",
        'version != "0011_phase14"',
        'print("Full Compose Phase 18 verification passed.")',
        'default=os.environ.get("FABLE5_VERIFY_PHASE", "25")',
    ):
        assert required in source
    assert verifier.phase18_offline_environment()["FABLE5_VERIFY_PHASE"] == "18"
    for name in verifier.PHASE_18_CREDENTIAL_ENV_NAMES:
        monkeypatch.setenv(name, "phase18-ambient-secret-canary")
    acceptance, _api_url, _frontend_url = verifier.acceptance_environment(18)
    assert all(name not in acceptance for name in verifier.PHASE_18_CREDENTIAL_ENV_NAMES)

    workflow = normalized(ROOT / ".github/workflows/ci.yml")
    assert workflow.startswith("name: phase-25-ci\n")
    assert 'FABLE5_VERIFY_PHASE: "25"' in workflow
    assert "phase25-compose:" in workflow
    assert workflow.count("python scripts/verify_phase1.py --phase 25") == 1
    assert workflow.count("python scripts/verify_phase1.py --static-only --phase 25") == 1
    assert "timeout-minutes: 180" in workflow
    assert "fetch-depth: 0" in workflow
    assert "secrets." not in workflow
    for credential_name in verifier.PHASE_18_CREDENTIAL_ENV_NAMES:
        assert f'{credential_name}: ""' in workflow
    for entrypoint in ("scripts/check.ps1", "scripts/check.sh", "Makefile"):
        wrapper = normalized(ROOT / entrypoint)
        assert "FABLE5_VERIFY_PHASE" in wrapper
        assert "--phase" in wrapper
        assert "23, 24, or 25" in wrapper
    for path in (
        ROOT / "services/frontend/e2e/phase8.accessibility.spec.ts",
        ROOT / "services/frontend/e2e/phase8.visual.spec.ts",
    ):
        browser = normalized(path)
        assert 'process.env.FABLE5_VERIFY_PHASE ?? "25"' in browser
        assert '"20",\n  "21",\n  "22",' in browser
    runner = normalized(ROOT / "scripts/run_phase_gate.py")
    assert '"--phase", "18"' not in runner


def test_phase18_docs_stop_before_phase19_and_preserve_review_only_semantics() -> None:
    decisions = normalized(ROOT / "docs/PHASE_18_FAMILY_A_CURRENT_USE_RIGHTS_REVIEW_DECISIONS.md")
    handoff = normalized(ROOT / "docs/handoffs/PHASE_18.md")
    combined = decisions + handoff
    for required in (
        BASELINE_SHA,
        BASELINE_TREE,
        ARTIFACT_PATH,
        "REVIEW_CURRENT_USE_RIGHTS",
        "OUTPUT_FROZEN",
        "BLOCKED_NO_OPERATIONAL_SELECTION",
        "adds no migration",
        "Stop after Phase 18",
        "Do not begin Phase 19",
    ):
        assert required in combined
    assert (ROOT / "docs/handoffs/PHASE_19.md").exists()
    assert (ROOT / "services/data/src/fable5_data/phase19").exists()
