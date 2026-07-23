from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BASELINE_SHA = "b1ad522c666f472f02ad5995d8fa52e3413c2cac"
BASELINE_TREE = "d1b74532704708e97047e4abf704532102ba510a"
PHASE26_ARTIFACT = ROOT / "docs/PHASE_26_FAMILY_A_OPERATIONAL_DATA_COMPOSITION_DECISION.json"
PHASE26_ARTIFACT_FILE_SHA256 = "366206d2d0122e28ad95056765f840e3e12087ab1b29f17956f206ba27840175"
PHASE27_ARTIFACT = ROOT / "docs/PHASE_27_FAMILY_A_RIGHTS_AND_ENTITLEMENT_EVIDENCE_INTAKE.json"
PHASE27_ARTIFACT_ID = "6d3bc146-67ad-5aa1-8836-dd5130d8736e"
PHASE27_ARTIFACT_SHA256 = "9721a4e1ebf1024a9d11695c9144f54046954e012470c7ca6c715f32a714925e"
PHASE27_ARTIFACT_FILE_SHA256 = "b2525ad22c1a0f1569188a7aefa3d735da1903d098725a8346c762d7c0d4214b"
PHASE27_EVIDENCE_BUNDLE_ID = "63bc191d-03ef-54ae-afa6-599e4f287cfe"
PHASE27_EVIDENCE_BUNDLE_SHA256 = "f2d6a793e0208f57b4675f2efffe6de330a2ea9a8d895420c4011c3b12e02d14"
PHASE27_POLICY_SHA256 = "3792dffdf784c5354b973b0de3ecc6c5119cc97a67cdf065d2e826caede29505"
EXPECTED_PHASE27_ALLOWED_WRITES = frozenset(
    {
        ".github/workflows/ci.yml",
        "DEVELOPMENT.md",
        "Makefile",
        "README.md",
        "docs/COMPLIANCE_NOTES.md",
        "docs/DATA_SOURCES.md",
        "docs/EVALS.md",
        "docs/IMPLEMENTATION_PLAN.md",
        "docs/PHASE_27_FAMILY_A_RIGHTS_AND_ENTITLEMENT_EVIDENCE_INTAKE.json",
        "docs/PHASE_27_FAMILY_A_RIGHTS_AND_ENTITLEMENT_EVIDENCE_INTAKE_DECISIONS.md",
        "docs/RISK_POLICY.md",
        "docs/handoffs/PHASE_27.md",
        "scripts/check.ps1",
        "scripts/check.sh",
        "scripts/generate_family_a_rights_and_entitlement_evidence_intake.py",
        "scripts/verify_family_a_rights_and_entitlement_evidence_intake.py",
        "scripts/verify_phase1.py",
        "services/data/src/fable5_data/phase27/__init__.py",
        "services/data/src/fable5_data/phase27/canonical.py",
        "services/data/src/fable5_data/phase27/contracts.py",
        "services/data/src/fable5_data/phase27/package.py",
        "services/data/tests/test_phase27_contracts.py",
        "services/data/tests/test_phase27_package.py",
        "services/data/tests/test_phase27_security.py",
        "services/frontend/e2e/phase8.accessibility.spec.ts",
        "services/frontend/e2e/phase8.visual.spec.ts",
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
        "tests/test_phase22_static.py",
        "tests/test_phase23_static.py",
        "tests/test_phase24_static.py",
        "tests/test_phase25_static.py",
        "tests/test_phase27_portable.py",
        "tests/test_phase27_static.py",
        "tests/test_phase5_postgres.py",
        "tests/test_phase9_static.py",
        "tests/test_repository_policy.py",
    }
)


def normalized(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def verifier_module():
    spec = importlib.util.spec_from_file_location(
        "verify_phase1_phase27_static", ROOT / "scripts/verify_phase1.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def baseline_bytes(path: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"{BASELINE_SHA}:{path}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout


def test_phase27_baseline_parser_allowlist_and_inheritance_are_exact() -> None:
    verifier = verifier_module()
    assert verifier.PHASE_27_BASELINE_SHA == BASELINE_SHA
    assert verifier.EXPECTED_PHASE_27_BASELINE_TREE == BASELINE_TREE
    assert set(verifier.PHASE_27_REQUIRED_PATHS) <= verifier.PHASE_27_ALLOWED_WRITES
    assert verifier.PHASE_27_ALLOWED_WRITES == EXPECTED_PHASE27_ALLOWED_WRITES
    assert len(verifier.PHASE_27_ALLOWED_WRITES) == 47
    assert verifier.PHASE_27_INHERITED_TABLES == verifier.PHASE_26_INHERITED_TABLES
    assert len(verifier.PHASE_27_INHERITED_TABLES) == 57
    assert [verifier.phase_number(str(value)) for value in range(1, 28)] == list(range(1, 28))
    for invalid in ("0", "28", "not-a-phase"):
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


def test_phase27_changed_paths_stay_inside_the_exact_allowlist() -> None:
    verifier = verifier_module()
    changed: set[str] = set()
    for command in (
        ["git", "diff", "--name-only", BASELINE_SHA, "--"],
        ["git", "diff", "--cached", "--name-only", "--"],
        ["git", "ls-files", "--others", "--exclude-standard", "--"],
    ):
        result = subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)
        changed.update(path.replace("\\", "/") for path in result.stdout.splitlines() if path)
    assert not changed - verifier.PHASE_27_ALLOWED_WRITES
    assert not verifier.PHASE_27_ALLOWED_WRITES - changed
    assert "services/api/live_order_submit.py" not in verifier.PHASE_27_ALLOWED_WRITES
    assert "docs/handoffs/PHASE_28.md" not in verifier.PHASE_27_ALLOWED_WRITES


def test_phase27_freezes_phase26_and_all_but_the_governance_overlay_delta() -> None:
    verifier = verifier_module()
    assert hashlib.sha256(PHASE26_ARTIFACT.read_bytes()).hexdigest() == (
        PHASE26_ARTIFACT_FILE_SHA256
    )
    assert PHASE26_ARTIFACT.read_bytes() == baseline_bytes(
        PHASE26_ARTIFACT.relative_to(ROOT).as_posix()
    )
    assert verifier.PHASE_26_MAINTENANCE_OVERLAY_PATHS & verifier.PHASE_27_ALLOWED_WRITES == {
        "DEVELOPMENT.md"
    }
    for relative in verifier.PHASE_26_MAINTENANCE_OVERLAY_PATHS - {"DEVELOPMENT.md"}:
        assert (ROOT / relative).read_bytes() == baseline_bytes(relative)
    planted = set(verifier.PHASE_27_ALLOWED_WRITES) | {
        "services/frontend/src/app/paper/readiness/order-submit.ts"
    }
    assert planted - verifier.PHASE_27_ALLOWED_WRITES == {
        "services/frontend/src/app/paper/readiness/order-submit.ts"
    }


def test_phase27_artifact_is_canonical_blocked_and_has_zero_operational_authority() -> None:
    from fable5_data.phase27 import canonical as c
    from fable5_data.phase27.contracts import Phase27RightsEntitlementEvidencePackage
    from fable5_data.phase27.package import (
        build_phase27_package,
        canonical_phase27_package_bytes,
    )

    raw = PHASE27_ARTIFACT.read_bytes()
    artifact = Phase27RightsEntitlementEvidencePackage.model_validate_json(raw, strict=True)
    assert raw == canonical_phase27_package_bytes()
    assert hashlib.sha256(raw).hexdigest() == PHASE27_ARTIFACT_FILE_SHA256
    assert artifact == build_phase27_package()
    assert str(artifact.artifact_id) == PHASE27_ARTIFACT_ID
    assert artifact.artifact_sha256 == PHASE27_ARTIFACT_SHA256
    assert str(artifact.evidence_bundle_id) == PHASE27_EVIDENCE_BUNDLE_ID
    assert artifact.evidence_bundle_sha256 == PHASE27_EVIDENCE_BUNDLE_SHA256
    assert artifact.policy_sha256 == PHASE27_POLICY_SHA256
    assert artifact.composition_id == "FAMILY_A_CRSP_SEC_RTDSM_V1"
    assert artifact.outcome.value == "BLOCKED"
    assert artifact.determination.value == "COMPOSITION_RIGHTS_ENTITLEMENT_EVIDENCE_MISSING"
    assert not artifact.verified_evidence_recorded
    assert not artifact.current_rights_evidence_for_exact_composition
    payload = artifact.model_dump(mode="python")
    assert all(payload[name] is expected for name, expected in c.BOUNDARY_VALUES.items())


def test_phase27_full_compose_reaches_every_inherited_acceptance_guard() -> None:
    source = normalized(ROOT / "scripts/verify_phase1.py")
    guarded_actions = (
        (8, r"verify_phase8_browser\("),
        (10, r'with phase9_stage\(phase, "phase10_acceptance"\)'),
        (11, r'with phase9_stage\(phase, "phase11_acceptance"\)'),
        (12, r'with phase9_stage\(phase, "phase12_acceptance"\)'),
        (13, r'with phase9_stage\(phase, "phase13_acceptance"\)'),
        (14, r'with phase9_stage\(phase, "phase14_acceptance"\)'),
    )
    for first_phase, action in guarded_actions:
        match = re.search(
            rf"if phase in \{{(?P<phases>[^}}]+)\}}:\s*{action}",
            source,
        )
        assert match is not None
        assert {int(value) for value in re.findall(r"\d+", match.group("phases"))} == (
            set(range(first_phase, 26)) | {27}
        )


def test_phase27_linux_phase8_inheritance_uses_the_pinned_container(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    verifier = verifier_module()
    captured: list[tuple[list[str], dict[str, str]]] = []
    cleaned: list[str] = []
    monkeypatch.setattr(verifier.sys, "platform", "linux")
    monkeypatch.setattr(verifier.shutil, "which", lambda _: "/usr/bin/npm")
    monkeypatch.setattr(
        verifier,
        "snapshot_tables",
        lambda project, environment, tables: {"stable": (1, "a" * 64)},
    )
    monkeypatch.setattr(
        verifier,
        "run",
        lambda command, *, env: captured.append((command, env.copy())),
    )
    monkeypatch.setattr(
        verifier,
        "cleanup_phase11_linux_playwright_container",
        lambda project, environment: cleaned.append(project),
    )

    environment = {"FABLE5_VERIFY_PHASE": "27"}
    verifier.verify_phase8_browser(
        "phase27-inherited",
        environment,
        "http://127.0.0.1:3000",
    )

    command, command_environment = captured[-1]
    assert command[:2] == ["docker", "run"]
    assert command.count(verifier.PHASE_9_LINUX_PLAYWRIGHT_IMAGE) == 1
    assert command.count("FABLE5_VERIFY_PHASE=27") == 1
    assert command.count("e2e/phase8.accessibility.spec.ts") == 1
    assert command.count("e2e/phase8.visual.spec.ts") == 1
    assert command[command.index("--mount") + 1].endswith(",readonly")
    assert command_environment["FABLE5_VERIFY_PHASE"] == "27"
    assert cleaned == ["phase27-inherited"]


def test_phase27_domain_and_clis_are_offline_clockless_and_sanitized() -> None:
    domain = ROOT / "services/data/src/fable5_data/phase27"
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
        "yfinance",
    }
    domain_source = "\n".join(normalized(path) for path in domain.glob("*.py"))
    for forbidden in ("datetime.now", "datetime.utcnow", "date.today"):
        assert forbidden not in domain_source

    generator = normalized(
        ROOT / "scripts/generate_family_a_rights_and_entitlement_evidence_intake.py"
    )
    portable = normalized(
        ROOT / "scripts/verify_family_a_rights_and_entitlement_evidence_intake.py"
    )
    for source in (generator, portable):
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
        '"header"',
        '"credential"',
        '"secret"',
        '"token"',
        '"cookie"',
        '"raw_account"',
        '"raw_entitlement"',
    ):
        assert denied in generator


def test_phase27_active_dispatch_ci_wrappers_and_phase28_stop_are_exact() -> None:
    verifier = normalized(ROOT / "scripts/verify_phase1.py")
    for required in (
        "def verify_phase27_static()",
        "verify_phase27_static()",
        'default=os.environ.get("FABLE5_VERIFY_PHASE", "27")',
        'print("Static repository policy checks passed for Phase 27.")',
        'print("Full Compose Phase 27 verification passed.")',
    ):
        assert required in verifier
    workflow = normalized(ROOT / ".github/workflows/ci.yml")
    assert workflow.startswith("name: phase-27-ci\n")
    assert 'FABLE5_VERIFY_PHASE: "27"' in workflow
    assert "phase27-compose:" in workflow
    assert workflow.count("python scripts/verify_phase1.py --static-only --phase 27") == 1
    assert workflow.count("python scripts/verify_phase1.py --phase 27") == 1
    assert "secrets." not in workflow
    for entrypoint in ("scripts/check.ps1", "scripts/check.sh", "Makefile"):
        source = normalized(ROOT / entrypoint)
        assert "FABLE5_VERIFY_PHASE" in source and "--phase" in source
        assert "25, 26, or 27" in source
    for path in (
        ROOT / "services/frontend/e2e/phase8.accessibility.spec.ts",
        ROOT / "services/frontend/e2e/phase8.visual.spec.ts",
    ):
        source = normalized(path)
        assert 'process.env.FABLE5_VERIFY_PHASE ?? "27"' in source
        assert '"27",' in source
    assert not (ROOT / "docs/handoffs/PHASE_28.md").exists()
    assert not (ROOT / "services/data/src/fable5_data/phase28").exists()
