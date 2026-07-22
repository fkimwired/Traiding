from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BASELINE_SHA = "145f67f188befae46443d061d029c243858841b4"
BASELINE_TREE = "27392b6eb3239e01e533d07d42d164124fb7aa18"
ACCEPTED_PHASE24_SHA = "c1dad09f08b18a5a7d527579ca677633b49184fb"
PHASE24_FILE_SHA256 = "5ad6b7b8e5c60fa1b2e76445b11ef0428d68515dd97439e6b21fc487aea91417"
ARTIFACT = ROOT / "docs/PHASE_25_FAMILY_A_RTDSM_RIGHTS_RESPONSE_AND_ADAPTER_PATTERNS.json"


def normalized(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def verifier_module():
    spec = importlib.util.spec_from_file_location(
        "verify_phase1_phase25_static", ROOT / "scripts/verify_phase1.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_phase25_baseline_parser_allowlist_and_inheritance_are_exact() -> None:
    verifier = verifier_module()
    assert verifier.PHASE_25_BASELINE_SHA == BASELINE_SHA
    assert verifier.EXPECTED_PHASE_25_BASELINE_TREE == BASELINE_TREE
    assert verifier.PHASE_25_ACCEPTED_PHASE24_SHA == ACCEPTED_PHASE24_SHA
    assert set(verifier.PHASE_25_REQUIRED_PATHS) <= verifier.PHASE_25_ALLOWED_WRITES
    assert verifier.PHASE_25_INHERITED_TABLES == verifier.PHASE_24_INHERITED_TABLES
    assert len(verifier.PHASE_25_INHERITED_TABLES) == 57
    assert [verifier.phase_number(str(value)) for value in range(1, 27)] == list(range(1, 27))
    for invalid in ("0", "27", "not-a-phase"):
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
    assert ACCEPTED_PHASE24_SHA in parents


def test_phase25_phase24_merge_and_artifact_are_ancestors_and_unchanged() -> None:
    ancestry = subprocess.run(
        ["git", "merge-base", "--is-ancestor", BASELINE_SHA, "HEAD"],
        cwd=ROOT,
        check=False,
    )
    assert ancestry.returncode == 0
    assert (
        subprocess.run(
            ["git", "show", "-s", "--format=%T", ACCEPTED_PHASE24_SHA],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        == BASELINE_TREE
    )
    phase24 = ROOT / "docs/PHASE_24_FAMILY_A_RTDSM_RIGHTS_CLARIFICATION_REQUIREMENTS.json"
    assert hashlib.sha256(phase24.read_bytes()).hexdigest() == PHASE24_FILE_SHA256
    baseline = subprocess.run(
        ["git", "show", f"{BASELINE_SHA}:{phase24.relative_to(ROOT).as_posix()}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout
    assert phase24.read_bytes() == baseline


def test_phase25_canonical_artifact_is_blocked_complete_and_metadata_only() -> None:
    from fable5_data.phase25.contracts import EvaluationState, Phase25Package
    from fable5_data.phase25.package import canonical_phase25_package_bytes

    raw = ARTIFACT.read_bytes()
    artifact = Phase25Package.model_validate_json(raw, strict=True)
    assert raw == canonical_phase25_package_bytes()
    assert artifact.outcome.value == "BLOCKED"
    assert artifact.determination.value == "RIGHTS_RESPONSE_EVIDENCE_MISSING"
    assert not artifact.response_received and not artifact.rights_verified
    assert (len(artifact.question_evaluations), len(artifact.scope_evaluations)) == (10, 19)
    assert (len(artifact.source_evidence), len(artifact.adapter_patterns)) == (10, 11)
    assert all(row.state is EvaluationState.MISSING for row in artifact.question_evaluations)
    assert all(row.state is EvaluationState.MISSING for row in artifact.scope_evaluations)
    assert not artifact.provider_observations_downloaded
    assert not artifact.provider_observations_persisted
    assert not artifact.credentials_loaded
    assert not artifact.production_adapter_activated
    assert artifact.yahoo_rights_state == "RIGHTS_UNVERIFIED"
    assert not artifact.yfinance_dependency_added
    assert artifact.runtime_network_disabled


def test_phase25_domain_and_clis_have_no_runtime_provider_or_secret_surface() -> None:
    domain = ROOT / "services/data/src/fable5_data/phase25"
    imported: set[str] = set()
    for path in domain.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".", 1)[0])
    assert not imported & {
        "aiohttp",
        "fastapi",
        "httpx",
        "openbb",
        "requests",
        "socket",
        "sqlalchemy",
        "subprocess",
        "tradingagents",
        "urllib",
        "yfinance",
    }
    generator = normalized(
        ROOT / "scripts/generate_family_a_rtdsm_rights_response_and_adapter_patterns.py"
    )
    verifier = normalized(
        ROOT / "scripts/verify_family_a_rtdsm_rights_response_and_adapter_patterns.py"
    )
    for source in (generator, verifier):
        assert 'event.startswith("socket.")' in source
        assert 'frozenset({"os.system", "subprocess.Popen"})' in source
        assert source.count("subprocess.Popen(") == 1
        assert "subprocess.run(" not in source
        main = source.index("def main")
        parse = source.index("_parser().parse_args", main)
        assert source.index("sys.addaudithook(_offline_audit_hook)", main) < parse
        assert source.index("_prove_offline_boundary()", main) < parse
    for denied in (
        '"body"',
        '"credential"',
        '"cookie"',
        '"crumb"',
        '"raw_response"',
        '"raw_account"',
        '"raw_entitlement"',
    ):
        assert denied in generator


def test_phase25_source_registry_and_pattern_inventory_preserve_evidence() -> None:
    payload = json.loads(ARTIFACT.read_bytes())
    assert {row["code"] for row in payload["source_evidence"]} == {
        "YFINANCE",
        "OPENBB",
        "FINROBOT",
        "TRADINGAGENTS",
        "PHILADELPHIA_FED_RTDSM_PAGE",
        "PHILADELPHIA_FED_ONLINE_TERMS",
        "PHILADELPHIA_FED_PCPI_DOCUMENTATION",
        "PHILADELPHIA_FED_RELEASE_VALUES_DOCUMENTATION",
        "YAHOO_API_TERMS",
        "YAHOO_GENERAL_TERMS",
    }
    required_fields = {
        "url",
        "inspected_revision",
        "software_license",
        "provider_abstraction",
        "request_session_ownership",
        "timeout_retry_backoff_rate_limit",
        "schema_validation_normalization",
        "timestamp_timezone",
        "corporate_action_revision",
        "caching_persistence",
        "error_sanitization",
        "deterministic_testing",
        "rights_warning",
        "unresolved_limitations",
        "source_sha256",
    }
    assert all(required_fields <= row.keys() for row in payload["source_evidence"])
    assert all(row["status"] == "DOCUMENTED_NOT_IMPLEMENTED" for row in payload["adapter_patterns"])


def test_phase25_is_frozen_while_phase26_dispatch_is_active() -> None:
    verifier = normalized(ROOT / "scripts/verify_phase1.py")
    for required in (
        "def verify_phase25_static()",
        "verify_phase25_static()",
        'default=os.environ.get("FABLE5_VERIFY_PHASE", "26")',
        'print("Static repository policy checks passed for Phase 25.")',
        'print("Full Compose Phase 25 verification passed.")',
    ):
        assert required in verifier
    workflow = normalized(ROOT / ".github/workflows/ci.yml")
    assert workflow.startswith("name: phase-26-ci\n")
    assert 'FABLE5_VERIFY_PHASE: "26"' in workflow
    assert "phase26-compose:" in workflow
    assert workflow.count("python scripts/verify_phase1.py --static-only --phase 26") == 1
    assert workflow.count("python scripts/verify_phase1.py --phase 26") == 1
    for entrypoint in ("scripts/check.ps1", "scripts/check.sh", "Makefile"):
        source = normalized(ROOT / entrypoint)
        assert "FABLE5_VERIFY_PHASE" in source and "--phase" in source
        assert "24, 25, or 26" in source
    for path in (
        ROOT / "services/frontend/e2e/phase8.accessibility.spec.ts",
        ROOT / "services/frontend/e2e/phase8.visual.spec.ts",
    ):
        source = normalized(path)
        assert 'process.env.FABLE5_VERIFY_PHASE ?? "26"' in source
        assert '"23",\n  "24",\n  "25",' in source
    combined = normalized(
        ROOT / "docs/PHASE_25_FAMILY_A_RTDSM_RIGHTS_RESPONSE_AND_ADAPTER_PATTERNS_DECISIONS.md"
    ) + normalized(ROOT / "docs/handoffs/PHASE_25.md")
    for required in (
        BASELINE_SHA,
        BASELINE_TREE,
        ACCEPTED_PHASE24_SHA,
        PHASE24_FILE_SHA256,
        "RIGHTS_RESPONSE_EVIDENCE_MISSING",
        "RIGHTS_UNVERIFIED",
        "Stop after Phase 25",
    ):
        assert required in combined
    assert (ROOT / "docs/handoffs/PHASE_26.md").is_file()
    assert (ROOT / "services/data/src/fable5_data/phase26").is_dir()
    assert not (ROOT / "docs/handoffs/PHASE_27.md").exists()
    assert not (ROOT / "services/data/src/fable5_data/phase27").exists()
