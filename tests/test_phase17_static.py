from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import inspect
import json
import subprocess
from pathlib import Path
from types import ModuleType

import pytest
from fable5_data.phase17.canonical import (
    PHASE17_BOUNDARY_VALUES,
    PHASE17_PHASE16_STEP1_SHA256,
)
from fable5_data.phase17.inventory import (
    build_family_a_candidate_product_inventory,
    canonical_candidate_product_inventory_bytes,
)

ROOT = Path(__file__).resolve().parents[1]
BASELINE_SHA = "7c4df26733b4ad13c49c455ea5f28f627012ee44"
BASELINE_TREE = "c69b4a60237ae3588f8544272b75becbf0a763e8"
PHASE16_ARTIFACT_ID = "e106a766-5cfe-5a1c-94f6-ee1c2ac68652"
PHASE16_ARTIFACT_SHA256 = "74ddf4a51d722b494fd494241e2e5927bff6fde034f6932dcfd791bb3a0706bb"
PHASE16_POLICY_SHA256 = "57cfcfd09f2d4a87d9562fd536228b9f05693bb71b7e9d1867618a35da7d4efd"
PHASE16_STEPS_MANIFEST_SHA256 = "92e65795b453a63cb1c6b44b4522629226580f90d681caf0032dfd787b94725d"
PHASE16_STEP1_SHA256 = "b91451d90ea1ae672ccab878df742b91b62d1b33902f9be05a0b6e1395502ec1"
PHASE16_GAPS_MANIFEST_SHA256 = "c6df8bcc7d98b682b880484aef028d411f196aaaf414d01949912c969ac9e26d"
ARTIFACT_PATH = "docs/PHASE_17_FAMILY_A_CANDIDATE_PRODUCT_INVENTORY.json"

PRODUCT_CODES = (
    "TIINGO_END_OF_DAY",
    "TIINGO_US_FUNDAMENTALS",
    "TIINGO_DIVIDEND_CORPORATE_ACTIONS",
    "TIINGO_SPLIT_CORPORATE_ACTIONS",
    "MORNINGSTAR_CRSP_US_STOCK_DATABASES",
    "MORNINGSTAR_CRSP_COMPUSTAT_MERGED",
    "SEC_EDGAR_SUBMISSIONS_AND_XBRL_DATA_APIS",
    "FRED_REALTIME_AND_VINTAGE_WEB_SERVICE",
    "LSEG_TICK_HISTORY_INSTRUMENT_AND_VENUE_WEB_API",
)
OFFICIAL_URLS = (
    "https://www.tiingo.com/documentation/end-of-day",
    "https://www.tiingo.com/documentation/fundamentals",
    "https://www.tiingo.com/documentation/corporate-actions/dividends",
    "https://www.tiingo.com/documentation/corporate-actions/splits",
    "https://indexes.morningstar.com/research-data-products/crsp-us-stock-databases",
    "https://indexes.morningstar.com/research-data-products/crsp-compustat-merged-database",
    "https://www.sec.gov/search-filings/edgar-application-programming-interfaces",
    "https://fred.stlouisfed.org/docs/api/fred/overview.html",
    "https://www.lseg.com/en/data-analytics/market-data/data-feeds/tick-history",
)
MAPPING_DOMAINS = (
    "security_master",
    "universe_membership",
    "ohlcv",
    "corporate_actions",
    "delistings",
    "as_reported_fundamentals",
    "macro_regime_inputs",
    "sector_classification_history",
    "historical_liquidity_depth",
)
CANDIDATE_CODES = (
    "TIINGO_PHASE13_BOUNDED_CANDIDATE",
    "MORNINGSTAR_CRSP_US_STOCK_DATABASES_CANDIDATE",
    "MORNINGSTAR_CRSP_COMPUSTAT_MERGED_DATABASE_CANDIDATE",
    "SEC_EDGAR_SUBMISSIONS_XBRL_CANDIDATE",
    "FEDERAL_RESERVE_ALFRED_VINTAGES_CANDIDATE",
    "HISTORICAL_LIQUIDITY_PRODUCT_UNSELECTED",
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

ALLOWED_WRITES = {
    ".github/workflows/ci.yml",
    "Makefile",
    "README.md",
    "docs/COMPLIANCE_NOTES.md",
    "docs/DATA_SOURCES.md",
    "docs/EVALS.md",
    "docs/IMPLEMENTATION_PLAN.md",
    ARTIFACT_PATH,
    "docs/PHASE_17_FAMILY_A_CANDIDATE_PRODUCT_INVENTORY_DECISIONS.md",
    "docs/RISK_POLICY.md",
    "docs/handoffs/PHASE_17.md",
    "scripts/check.ps1",
    "scripts/check.sh",
    "scripts/generate_family_a_candidate_product_inventory.py",
    "scripts/verify_family_a_candidate_product_inventory.py",
    "scripts/verify_phase1.py",
    "services/data/src/fable5_data/phase17/__init__.py",
    "services/data/src/fable5_data/phase17/canonical.py",
    "services/data/src/fable5_data/phase17/contracts.py",
    "services/data/src/fable5_data/phase17/inventory.py",
    "services/data/tests/test_phase17_contracts.py",
    "services/data/tests/test_phase17_inventory.py",
    "services/data/tests/test_phase17_security.py",
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
    "tests/test_phase17_portable.py",
    "tests/test_phase17_static.py",
    "tests/test_repository_policy.py",
}

PHASE16_FROZEN_SHA256S = {
    "docs/PHASE_16_FAMILY_A_POINT_IN_TIME_SOURCE_PLAN.json": (
        "dcaffdccae6b1a530575eebc4bc1e6dd57e77426165bf32f5d5394bcff42f733"
    ),
    "docs/PHASE_16_FAMILY_A_POINT_IN_TIME_SOURCE_PLAN_DECISIONS.md": (
        "7f31441343f7d3942bb829fe8ce5c2afde893e0b5a3893d617e3086b76d491db"
    ),
    "docs/handoffs/PHASE_16.md": (
        "d81b4cb81c855e33c12a7dbc13b0a1811990903b71991490abbcde510fdca53e"
    ),
    "scripts/generate_family_a_point_in_time_source_plan.py": (
        "beadbffc81ad15b8a7f34bd75c97e1a69366499f77d52c35e650997b2e77660f"
    ),
    "scripts/verify_family_a_point_in_time_source_plan.py": (
        "c4a49dff18f4de42174fc1c3163ccdcf5b1494462f06f662b19f1826123d0ea8"
    ),
    "services/data/src/fable5_data/phase16/__init__.py": (
        "3274c8c9a7bd4ce6da6b2942b0c570e39ba332486e2f8488947a34b2cc3ffa5f"
    ),
    "services/data/src/fable5_data/phase16/canonical.py": (
        "445ceefcaad522af43ec7b1ed799e7948f777f621db58dd1b40a4614901635ee"
    ),
    "services/data/src/fable5_data/phase16/contracts.py": (
        "b3a81c5422d443f4763f1de3974f8b50ca55930175bc77d31e6eb9d4fa37f16c"
    ),
    "services/data/src/fable5_data/phase16/plan.py": (
        "eed61570012fe8470ca3d2d300068ada02a0b33eb6f7974dd410865c87690c9f"
    ),
    "services/data/tests/test_phase16_contracts.py": (
        "542730daf2cab6e9f78a6755c8285f17e75dc43bbdf9fcdd4bbf77e1523d5089"
    ),
    "services/data/tests/test_phase16_plan.py": (
        "7a90bb8013ff1f0bc3731e889be2f43361d6f6a94716168efcf7931f9f639c6b"
    ),
    "services/data/tests/test_phase16_security.py": (
        "46cb68813a2f1e7a98c38944fdba5aa1d4f6cefa9b48b8bd6497ba420e858983"
    ),
    "tests/test_phase16_portable.py": (
        "9bc4644415fcb69c30ce0a90457e467196dad4e8159d406ec5782452533ce61a"
    ),
}


def normalized(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def verifier_module() -> ModuleType:
    path = ROOT / "scripts/verify_phase1.py"
    spec = importlib.util.spec_from_file_location("phase17_verifier", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _imports(paths: tuple[Path, ...]) -> set[str]:
    imported: set[str] = set()
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imported.add(node.module)
    return imported


def test_phase17_parser_baseline_allowlist_and_inherited_release_boundary_are_exact() -> None:
    verifier = verifier_module()
    assert verifier.PHASE_17_BASELINE_SHA == BASELINE_SHA
    assert verifier.EXPECTED_PHASE_17_BASELINE_TREE == BASELINE_TREE
    assert verifier.PHASE_17_ARTIFACT_PATH == ARTIFACT_PATH
    assert verifier.PHASE_17_ALLOWED_WRITES == ALLOWED_WRITES
    assert len(verifier.PHASE_17_ALLOWED_WRITES) == 37
    assert verifier.PHASE_17_INHERITED_TABLES == verifier.PHASE_16_INHERITED_TABLES
    assert len(verifier.PHASE_17_INHERITED_TABLES) == 57
    assert [verifier.phase_number(str(value)) for value in range(1, 26)] == list(range(1, 26))
    for invalid in ("0", "26", "not-a-phase"):
        with pytest.raises(argparse.ArgumentTypeError):
            verifier.phase_number(invalid)

    phase16 = inspect.signature(verifier.verify_phase16_static).parameters
    assert tuple(phase16) == ("release_closure", "active_phase")
    assert phase16["release_closure"].default is True
    assert phase16["active_phase"].default == 16
    phase17 = inspect.signature(verifier.verify_phase17_static).parameters
    assert tuple(phase17) == ("release_closure", "active_phase")
    assert phase17["release_closure"].default is True
    assert phase17["active_phase"].default == 17
    source = normalized(ROOT / "scripts/verify_phase1.py")
    branch = source.split("if phase == 17:", 1)[1].split("verify_static_inherited(phase)", 1)[0]
    for required in (
        "verify_static_inherited(17, announce=False)",
        "verify_phase10_static(release_closure=False, active_phase=17)",
        "verify_phase11_static(release_closure=False, active_phase=17)",
        "verify_phase12_static(release_closure=False, active_phase=17)",
        "verify_phase13_static(release_closure=False, active_phase=17)",
        "verify_phase14_static(release_closure=False, active_phase=17)",
        "verify_phase15_static(release_closure=False, active_phase=17)",
        "verify_phase16_static(release_closure=False, active_phase=17)",
        "verify_phase17_static()",
    ):
        assert required in branch


def test_phase17_artifact_binds_exact_products_mappings_steps_and_phase16_gap_lineage() -> None:
    committed = (ROOT / ARTIFACT_PATH).read_bytes()
    assert committed == canonical_candidate_product_inventory_bytes()
    payload = json.loads(committed)
    artifact = build_family_a_candidate_product_inventory()

    assert payload["artifact_sha256"] == artifact.artifact_sha256
    assert payload["outcome"] == "BLOCKED"
    assert payload["accepted_phase16_commit_sha"] == BASELINE_SHA
    assert payload["accepted_phase16_tree_sha"] == BASELINE_TREE
    assert payload["phase16_artifact_id"] == PHASE16_ARTIFACT_ID
    assert payload["phase16_artifact_sha256"] == PHASE16_ARTIFACT_SHA256
    assert payload["phase16_policy_sha256"] == PHASE16_POLICY_SHA256
    assert payload["phase16_steps_manifest_sha256"] == PHASE16_STEPS_MANIFEST_SHA256
    assert payload["phase16_step1_sha256"] == PHASE16_STEP1_SHA256
    assert PHASE17_PHASE16_STEP1_SHA256 == PHASE16_STEP1_SHA256
    assert payload["phase16_gap_bindings_manifest_sha256"] == PHASE16_GAPS_MANIFEST_SHA256

    assert tuple(item["code"] for item in payload["products"]) == PRODUCT_CODES
    assert (
        tuple(item["official_documentation_url"] for item in payload["products"]) == OFFICIAL_URLS
    )
    assert tuple(item["phase16_candidate_code"] for item in payload["candidate_groups"]) == (
        CANDIDATE_CODES
    )
    observed_domains = {
        capability for item in payload["products"] for capability in item["capability_codes"]
    }
    assert observed_domains == set(MAPPING_DOMAINS)
    assert len(observed_domains) == 9
    assert payload["products"][-1]["code"] == ("LSEG_TICK_HISTORY_INSTRUMENT_AND_VENUE_WEB_API")
    assert payload["products"][-1]["capability_codes"] == ["historical_liquidity_depth"]

    assert all(
        item["selected_for_independent_rights_review"] is True for item in payload["products"]
    )
    assert all(item["operational_provider_selected"] is False for item in payload["products"])
    assert all(item["operational_product_selected"] is False for item in payload["products"])
    assert all(item["operational_source_selected"] is False for item in payload["products"])
    assert all(item["coverage_proven"] is False for item in payload["products"])
    assert all(item["schema_proven"] is False for item in payload["products"])
    assert all(item["current_availability_proven"] is False for item in payload["products"])
    assert all(item["external_sample_qualified"] is False for item in payload["products"])
    assert all(item["entitlement_state"] == "UNPROVEN" for item in payload["products"])
    assert all(item["rights_state"] == "UNPROVEN" for item in payload["products"])
    assert all(item["fitness_state"] == "UNPROVEN" for item in payload["products"])

    assert tuple(item["code"] for item in payload["source_plan_steps"]) == STEP_CODES
    assert tuple(item["state"] for item in payload["source_plan_steps"]) == (
        "OUTPUT_FROZEN",
        "NOT_STARTED",
        "NOT_STARTED",
        "NOT_STARTED",
        "NOT_STARTED",
        "NOT_STARTED",
        "NOT_STARTED",
    )
    first_step = payload["source_plan_steps"][0]
    assert first_step["required_outputs"] == ["candidate_product_inventory_sha256"]
    assert first_step["required_prior_evidence"] == []
    assert len(first_step["produced_outputs"]) == 1
    assert first_step["produced_outputs"][0]["name"] == "candidate_product_inventory_sha256"
    assert (
        first_step["produced_outputs"][0]["sha256"] == payload["candidate_product_inventory_sha256"]
    )
    assert all(item["produced_outputs"] == [] for item in payload["source_plan_steps"][1:])

    phase16 = json.loads(
        (ROOT / "docs/PHASE_16_FAMILY_A_POINT_IN_TIME_SOURCE_PLAN.json").read_bytes()
    )
    assert len(phase16["phase15_gap_bindings"]) == 19
    assert phase16["gap_bindings_manifest_sha256"] == PHASE16_GAPS_MANIFEST_SHA256

    assert payload["official_public_documentation_review_performed"] is True
    for field, expected in PHASE17_BOUNDARY_VALUES.items():
        assert payload[field] is expected
    for field in (
        "credentials_loaded",
        "external_request_performed",
        "provider_data_request_performed",
        "provider_account_verification_performed",
        "entitlement_verification_performed",
        "rights_verified",
        "rights_granted",
        "external_data_capture_authorized",
        "licensed_data_persisted",
        "research_ingestion_authorized",
        "research_data_eligible",
        "research_executed",
        "execution_authorized",
        "order_submission_authorized",
    ):
        assert payload[field] is False


def test_phase16_portable_surface_is_byte_frozen() -> None:
    for relative, expected in PHASE16_FROZEN_SHA256S.items():
        actual = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
        assert actual == expected, relative


def test_phase17_adds_no_migration_api_openapi_contract_dependency_compose_or_runner_drift() -> (
    None
):
    frozen_scopes = (
        "compose.yaml",
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


def test_phase17_portable_ast_denies_transport_database_subprocess_and_execution_capabilities() -> (
    None
):
    phase17_paths = tuple(sorted((ROOT / "services/data/src/fable5_data/phase17").glob("*.py")))
    generator_path = ROOT / "scripts/generate_family_a_candidate_product_inventory.py"
    verifier_path = ROOT / "scripts/verify_family_a_candidate_product_inventory.py"
    cli_paths = (generator_path, verifier_path)
    domain_imports = _imports(phase17_paths)
    generator_imports = _imports((generator_path,))
    verifier_imports = _imports((verifier_path,))
    shared_forbidden_imports = {
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
    assert not {
        name
        for name in domain_imports
        if any(
            name == denied or name.startswith(f"{denied}.")
            for denied in (*shared_forbidden_imports, "os", "secrets", "socket", "ssl")
        )
    }
    for imported, additionally_forbidden in (
        (generator_imports, ("os", "secrets", "ssl")),
        (verifier_imports, ("secrets", "ssl")),
    ):
        assert not {
            name
            for name in imported
            if any(
                name == denied or name.startswith(f"{denied}.")
                for denied in (*shared_forbidden_imports, *additionally_forbidden)
            )
        }

    production = "\n".join(path.read_text(encoding="utf-8") for path in phase17_paths)
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

    for cli_path in cli_paths:
        cli = cli_path.read_text(encoding="utf-8")
        for required_boundary in (
            'event.startswith("socket.")',
            'frozenset({"os.system", "subprocess.Popen"})',
            "sys.addaudithook(_offline_audit_hook)",
            "_install_offline_boundary()",
            "_prove_socket_construction_is_denied()",
        ):
            assert required_boundary in cli
        assert cli.index("_install_offline_boundary()", cli.index("def main")) < cli.index(
            "_parser().parse_args", cli.index("def main")
        )
        assert cli.index(
            "_prove_socket_construction_is_denied()", cli.index("def main")
        ) < cli.index("_parser().parse_args", cli.index("def main"))
        for forbidden_call in (
            "os.getenv(",
            "os.environ",
            "os.system(",
            "subprocess.Popen(",
            "subprocess.run(",
        ):
            assert forbidden_call not in cli


def test_phase17_ci_wrappers_browser_ranges_and_secret_denial_are_active(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    verifier = verifier_module()
    source = normalized(ROOT / "scripts/verify_phase1.py")
    for required in (
        "verify_phase17_portable_acceptance(",
        "verify_phase17_offline_network_denial(",
        "snapshot_phase17_inherited_state(",
        "verify_phase17_no_schema_drift_and_zero_writes(",
        'version != "0011_phase14"',
        'print("Full Compose Phase 17 verification passed.")',
        'default=os.environ.get("FABLE5_VERIFY_PHASE", "25")',
    ):
        assert required in source

    for name in (
        *verifier.PHASE_12_CREDENTIAL_ENV_NAMES,
        *verifier.PHASE_13_CREDENTIAL_ENV_NAMES,
        "FABLE5_DATABASE_URL",
        "FABLE5_REDIS_URL",
    ):
        assert name not in verifier.phase17_offline_environment()
    assert verifier.phase17_offline_environment()["FABLE5_VERIFY_PHASE"] == "17"
    for name in verifier.PHASE_17_CREDENTIAL_ENV_NAMES:
        monkeypatch.setenv(name, "phase17-ambient-secret-canary")
    acceptance, _api_url, _frontend_url = verifier.acceptance_environment(17)
    assert all(name not in acceptance for name in verifier.PHASE_17_CREDENTIAL_ENV_NAMES)

    workflow = normalized(ROOT / ".github/workflows/ci.yml")
    assert workflow.startswith("name: phase-25-ci\n")
    assert 'FABLE5_VERIFY_PHASE: "25"' in workflow
    assert "phase25-compose:" in workflow
    assert workflow.count("python scripts/verify_phase1.py --phase 25") == 1
    assert workflow.count("python scripts/verify_phase1.py --static-only --phase 25") == 1
    assert "timeout-minutes: 180" in workflow
    assert "fetch-depth: 0" in workflow
    for credential_name in verifier.PHASE_17_CREDENTIAL_ENV_NAMES:
        assert f'{credential_name}: ""' in workflow
    for forbidden in (
        "secrets.",
        "FABLE5_UPDATE_SNAPSHOTS",
    ):
        assert forbidden not in workflow

    for entrypoint in ("scripts/check.ps1", "scripts/check.sh", "Makefile"):
        wrapper = normalized(ROOT / entrypoint)
        assert "FABLE5_VERIFY_PHASE" in wrapper
        assert "--phase" in wrapper
        assert "18" in wrapper

    for path in (
        ROOT / "services/frontend/e2e/phase8.accessibility.spec.ts",
        ROOT / "services/frontend/e2e/phase8.visual.spec.ts",
    ):
        browser = normalized(path)
        assert 'process.env.FABLE5_VERIFY_PHASE ?? "25"' in browser
        assert '"20",\n  "21",\n  "22",' in browser

    runner = normalized(ROOT / "scripts/run_phase_gate.py")
    assert "choices=(9,)" in runner
    assert '"--phase", "17"' not in runner
