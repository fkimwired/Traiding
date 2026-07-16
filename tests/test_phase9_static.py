from __future__ import annotations

import ast
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PHASE_8_BASELINE_SHA = "94bcfaabf9de457aec47e49e332865a8dcc74f30"
EXPECTED_PHASE_8_TREE = "56d2cf38ba0ff3d5427fbf5f20aefa13d5224581"
PHASE_9_ALLOWED_WRITES = {
    ".github/workflows/ci.yml",
    "Makefile",
    "README.md",
    "docs/IMPLEMENTATION_PLAN.md",
    "docs/PHASE_09_RELEASE_ACCEPTANCE_DECISIONS.md",
    "docs/handoffs/PHASE_09.md",
    "scripts/check.ps1",
    "scripts/check.sh",
    "scripts/run_phase_gate.py",
    "scripts/verify_phase1.py",
    "tests/test_phase5_postgres.py",
    "tests/test_phase9_gate_runner.py",
    "tests/test_phase9_static.py",
    "tests/test_repository_policy.py",
}
CONTRACT_SHA256 = {
    "packages/contracts/openapi.json": (
        "d89a72e31778ed7d6edcaaf5611e99506aecdc49c640df336e2a622023a0bb25"
    ),
    "packages/contracts/src/api.generated.ts": (
        "5fa0ce5d903529705709dc2dc0f4c86d71830fc634548551d145cf3bb7a0003e"
    ),
    "packages/contracts/src/runtime.generated.ts": (
        "905810491adf9f52090ff8af109137df76c76367293a21cd39a71dc643a4b964"
    ),
    "packages/contracts/src/validate-response.ts": (
        "57f74259a7d8f00bd739099a01eebd25d4fa7fed01d2e12320d28d67620e3503"
    ),
}
MIGRATION_SHA256 = {
    "services/api/migrations/versions/0001_phase1_audit_spine.py": (
        "5cd27e1bde6b03720f54fe5e1260cf5f9085e16a4eebed957aeeba1a3a7d17f8"
    ),
    "services/api/migrations/versions/0002_phase2_source_extraction.py": (
        "d45c1cb0ade079cfba7492c75c1aff13fc714aaae0a81637f21942c175c4e5c8"
    ),
    "services/api/migrations/versions/0003_phase3_canon_mapping.py": (
        "6859c63723dc31d6ede4cdd5528a42640f16e3c6103567b5d900a46741edf07d"
    ),
    "services/api/migrations/versions/0004_phase4_point_in_time_data.py": (
        "78c52c613358708940d88cbd47069bdde9bc857046bf646d7461bd13b57b3008"
    ),
    "services/api/migrations/versions/0005_phase5_evaluation.py": (
        "b368edf97c35c5b7d7ac651073a02c204816b638855d3bcae4d7cabf265a1404"
    ),
    "services/api/migrations/versions/0006_phase6_research.py": (
        "7f4ab516a31208b7c5f5400b1b593d7675c75570fa839f524bfddea3152d7070"
    ),
    "services/api/migrations/versions/0007_phase7_approval_risk.py": (
        "4ef4e6301f205fb9a18f478ac3fa6d6920dbe0af462b6f371e83dd2d622a8090"
    ),
}
IMMUTABLE_PREFIXES = (
    "services/extraction/tests/fixtures/",
    "services/data/src/fable5_data/fixtures/",
    "services/frontend/e2e/__screenshots__/phase8.visual.spec.ts/",
)
IMMUTABLE_ARTIFACTS = (
    "docs/PHASE_02_SCHEMA_DECISIONS.md",
    "docs/PHASE_03_MAPPING_DECISIONS.md",
    "docs/PHASE_04_DATA_DECISIONS.md",
    "docs/PHASE_06_RESEARCH_DECISIONS.md",
    "docs/PHASE_07_APPROVAL_DECISIONS.md",
    "docs/PHASE_08_UI_DECISIONS.md",
    "docs/handoffs/PHASE_02.md",
    "docs/handoffs/PHASE_03.md",
    "docs/handoffs/PHASE_04.md",
    "docs/handoffs/PHASE_07.md",
    "docs/handoffs/PHASE_08.md",
)


def git(*args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=check,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def baseline_bytes(path: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"{PHASE_8_BASELINE_SHA}:{path}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout


def tracked_baseline_paths() -> set[str]:
    return set(git("ls-tree", "-r", "--name-only", PHASE_8_BASELINE_SHA).splitlines())


def current_changed_paths() -> set[str]:
    changed = set(git("diff", "--name-only", PHASE_8_BASELINE_SHA, "--").splitlines())
    changed.update(git("diff", "--cached", "--name-only", "--").splitlines())
    changed.update(git("ls-files", "--others", "--exclude-standard", "--").splitlines())
    return {path.replace("\\", "/") for path in changed if path}


def test_phase8_baseline_tree_is_the_authorized_source() -> None:
    assert git("show", "-s", "--format=%T", PHASE_8_BASELINE_SHA) == EXPECTED_PHASE_8_TREE


def test_phase9_worktree_diff_stays_inside_the_exact_allowlist() -> None:
    assert current_changed_paths() <= PHASE_9_ALLOWED_WRITES


def test_phase9_contracts_and_migrations_are_exact_phase8_bytes() -> None:
    migration_root = ROOT / "services/api/migrations/versions"
    assert {
        path.as_posix().removeprefix(f"{ROOT.as_posix()}/") for path in migration_root.glob("*.py")
    } == set(MIGRATION_SHA256)
    assert not list(migration_root.glob("0008*.py"))

    for path, expected_hash in {**CONTRACT_SHA256, **MIGRATION_SHA256}.items():
        current = (ROOT / path).read_bytes()
        assert current == baseline_bytes(path)
        assert hashlib.sha256(current).hexdigest() == expected_hash


def test_phase9_fixtures_artifacts_and_all_48_snapshots_are_phase8_bytes() -> None:
    baseline_paths = tracked_baseline_paths()
    immutable_paths = sorted(path for path in baseline_paths if path.startswith(IMMUTABLE_PREFIXES))
    assert immutable_paths
    for path in immutable_paths:
        assert (ROOT / path).read_bytes() == baseline_bytes(path)
    for path in IMMUTABLE_ARTIFACTS:
        assert (ROOT / path).read_bytes() == baseline_bytes(path)

    snapshot_prefix = IMMUTABLE_PREFIXES[-1]
    snapshots = [path for path in immutable_paths if path.startswith(snapshot_prefix)]
    assert len(snapshots) == 48
    assert sum(path.endswith("-win32.png") for path in snapshots) == 24
    assert sum(path.endswith("-linux.png") for path in snapshots) == 24


def test_phase9_verifier_runs_inherited_static_first_and_full_cleanup_last() -> None:
    source = (ROOT / "scripts/verify_phase1.py").read_text(encoding="utf-8")
    assert "PHASE_8_BASELINE_SHA" in source
    assert "PHASE_9_ALLOWED_WRITES" in source
    assert "def verify_phase9_static" in source
    assert "verify_static_inherited(8)" in source
    wrapper = source.split("def verify_static(phase: int = 1)", maxsplit=1)[1].split(
        "def run(", maxsplit=1
    )[0]
    assert wrapper.index("verify_static_inherited(8)") < wrapper.index("verify_phase9_static()")
    assert "Full Compose Phase 8 verification passed." in source
    assert "Full Compose Phase 9 verification passed." in source
    assert source.index("verify_phase9_compose_cleanup") < source.index(
        'print("Full Compose Phase 9 verification passed.")'
    )
    assert "FABLE5_PHASE9_STAGE" in source


def verify_compose_named_calls(source: str) -> list[str]:
    tree = ast.parse(source)
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "verify_compose"
    )
    calls: list[str] = []

    class CallVisitor(ast.NodeVisitor):
        def visit_Call(self, node: ast.Call) -> None:
            if isinstance(node.func, ast.Name):
                calls.append(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.append(node.func.attr)
            self.generic_visit(node)

    CallVisitor().visit(function)
    return calls


def test_phase9_full_verifier_preserves_the_inherited_phase1_8_call_sequence() -> None:
    baseline = baseline_bytes("scripts/verify_phase1.py").decode("utf-8")
    current = (ROOT / "scripts/verify_phase1.py").read_text(encoding="utf-8")
    baseline_calls = verify_compose_named_calls(baseline)
    phase9_only_calls = {"phase9_stage", "verify_phase9_compose_cleanup"}
    current_inherited_calls = [
        name for name in verify_compose_named_calls(current) if name not in phase9_only_calls
    ]
    assert current_inherited_calls[: len(baseline_calls)] == baseline_calls
    assert current_inherited_calls[len(baseline_calls) :] == ["AssertionError", "print"]


def test_phase9_preserves_serial_browser_configuration() -> None:
    source = (ROOT / "services/frontend/playwright.config.ts").read_text(encoding="utf-8")
    assert "fullyParallel: false" in source
    assert "retries: 0" in source
    assert "workers: 1" in source


def test_phase9_wrappers_default_validate_and_forward_phase9() -> None:
    for path in ("scripts/check.ps1", "scripts/check.sh", "Makefile"):
        source = (ROOT / path).read_text(encoding="utf-8")
        assert "FABLE5_VERIFY_PHASE" in source
        assert "--phase" in source
        assert "9" in source
    assert "${FABLE5_VERIFY_PHASE:-9}" in (ROOT / "scripts/check.sh").read_text(encoding="utf-8")
    assert "${FABLE5_VERIFY_PHASE:-9}" in (ROOT / "Makefile").read_text(encoding="utf-8")
    assert 'else { "9" }' in (ROOT / "scripts/check.ps1").read_text(encoding="utf-8")

    for unchanged in ("scripts/test.ps1", "scripts/test.sh"):
        assert (ROOT / unchanged).read_bytes() == baseline_bytes(unchanged)


def test_phase9_ci_is_split_pinned_serial_and_uploads_only_sanitized_evidence() -> None:
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert workflow.startswith("name: phase-9-ci\n")
    assert "permissions:\n  contents: read" in workflow
    assert 'FABLE5_VERIFY_PHASE: "9"' in workflow
    assert "fetch-depth: 0" in workflow
    assert "preflight:" in workflow
    assert "unit:" in workflow and "needs: preflight" in workflow
    assert "phase9-compose:" in workflow
    assert "timeout-minutes: 90" in workflow
    assert "run_phase_gate.py run --phase 9" in workflow
    assert "run_phase_gate.py verify-evidence" in workflow
    assert "retention-days: 14" in workflow
    assert "if-no-files-found: error" in workflow
    assert "phase-gate.manifest.json" in workflow
    assert "phase-gate.sanitized.log" in workflow
    assert "phase-gate.raw.log" not in workflow
    assert "runner_exit" in workflow and "evidence_exit" in workflow
    assert "cancel-in-progress: ${{ github.event_name == 'pull_request' }}" in workflow

    action_lines = [line.strip() for line in workflow.splitlines() if "uses:" in line]
    assert action_lines
    for line in action_lines:
        revision = line.split("@", 1)[1].split()[0]
        assert len(revision) == 40
        int(revision, 16)
        assert "# v" in line


def test_phase9_decisions_and_handoff_keep_the_release_boundary_closed() -> None:
    for path in (
        "docs/PHASE_09_RELEASE_ACCEPTANCE_DECISIONS.md",
        "docs/handoffs/PHASE_09.md",
    ):
        body = (ROOT / path).read_text(encoding="utf-8")
        assert PHASE_8_BASELINE_SHA in body
        assert "Phase 9" in body
        assert "Ubuntu" in body
        assert "not accepted" in body
        for forbidden in (
            "live trading",
            "broker integration",
            "order submission",
            "paper execution",
        ):
            assert forbidden in body.lower()


def test_phase9_expected_contract_hashes_are_documented_verbatim() -> None:
    decisions = (ROOT / "docs/PHASE_09_RELEASE_ACCEPTANCE_DECISIONS.md").read_text(encoding="utf-8")
    for path, digest in CONTRACT_SHA256.items():
        assert path in decisions
        assert digest in decisions


def test_phase9_snapshot_matrix_names_are_stable_json_safe_strings() -> None:
    names = sorted(
        path.name
        for path in (ROOT / "services/frontend/e2e/__screenshots__/phase8.visual.spec.ts").glob(
            "*.png"
        )
    )
    assert json.loads(json.dumps(names)) == names
