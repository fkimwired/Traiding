from __future__ import annotations

import ast
import json
import os
import re
import shutil
import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final
from urllib.parse import urlsplit
from uuid import UUID

import pytest
from fable5_paper.phase12.contracts import PaperShadowReadinessArtifact

import scripts.preflight_paper_smoke as preflight
import scripts.report_paper_shadow_readiness as report_cli

ROOT: Final = Path(__file__).resolve().parents[1]
SURFACE_SPECS: Final = (
    "scripts/preflight_paper_smoke.py",
    "scripts/report_paper_shadow_readiness.py",
    "scripts/run_paper_smoke.ps1",
    "services/frontend/src/app/paper/readiness/**",
)
EXPECTED_TARGETS: Final = tuple(
    sorted(
        (
            "scripts/preflight_paper_smoke.py",
            "scripts/report_paper_shadow_readiness.py",
            "scripts/run_paper_smoke.ps1",
            ("services/frontend/src/app/paper/readiness/PaperReadinessWorkspace.module.css"),
            "services/frontend/src/app/paper/readiness/PaperReadinessWorkspace.tsx",
            "services/frontend/src/app/paper/readiness/page.tsx",
            "services/frontend/src/app/paper/readiness/readiness-api.ts",
        )
    )
)
READINESS_ROOT: Final = "services/frontend/src/app/paper/readiness"
READINESS_API_PATH: Final = f"{READINESS_ROOT}/readiness-api.ts"

KEY_ENV_NAME: Final = "FABLE5_ALPACA_PAPER_API_KEY_ID"
SECRET_ENV_NAME: Final = "FABLE5_ALPACA_PAPER_SECRET_KEY"
CREDENTIAL_ENV_NAMES: Final = frozenset((KEY_ENV_NAME, SECRET_ENV_NAME))
KEY_CANARY: Final = "CANARY_KEY_9f3"
SECRET_CANARY: Final = "CANARY_SECRET_7c1"
GIT_SHA: Final = "4d70b823947fd61d0ea17df14c9f1ff9f93fd45b"
DATABASE_URL: Final = "postgresql+psycopg://fable5:dev-only@127.0.0.1:5432/fable5"
FIXED_NOW: Final = datetime(2026, 7, 21, 22, 30, 0, 123456, tzinfo=UTC)
PYTHON_LAUNCHER: Final = ROOT / ".venv" / "Scripts" / "python.exe"
PYVENV_CONFIG: Final = ROOT / ".venv" / "pyvenv.cfg"
MOCK_ASSESSMENT_ID: Final = "55934e08-c4a2-548d-b9cd-13a1c824211b"
MOCK_FALLBACK_LINE: Final = "Mock fallback: MOCK_PROOF_COMPLETE proves the local contract only."

HARNESS_STUB_SOURCE: Final = r"""from __future__ import annotations

import json
import os
import sys
from pathlib import Path

MOCK_ID = "55934e08-c4a2-548d-b9cd-13a1c824211b"


def option(name: str) -> str:
    index = sys.argv.index(name)
    return sys.argv[index + 1]


script_name = Path(__file__).name
if script_name == "capture_paper_shadow_readiness.py":
    Path(os.environ["FABLE5_T005_CAPTURE_MARKER"]).write_text("called", encoding="utf-8")
    raise SystemExit(97)

if script_name == "preflight_paper_smoke.py":
    payload = {
        "schema_version": "fable5-paper-smoke-preflight-v1",
        "generated_at_utc": "2026-07-22T14:30:00.000000Z",
        "git_sha": "4d70b823947fd61d0ea17df14c9f1ff9f93fd45b",
        "dirty_tree": True,
        "execution_mode": "paper",
        "simulated_paper_only": True,
        "config_sha256": "1" * 64,
        "random_seed": None,
        "trial_count": None,
        "overall_status": "PASS",
        "credential_pair": "PRESENT_PAIR",
        "mock_readiness": "MOCK_PROOF_COMPLETE",
        "mock_readiness_assessment_id": MOCK_ID,
        "mock_readiness_artifact_sha256": "2" * 64,
        "checks": [{"status": "PASS"} for _ in range(7)],
        "report_sha256": "3" * 64,
    }
    rendered = json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
    output = Path(option("--output"))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    raise SystemExit(0)

if script_name == "report_paper_shadow_readiness.py":
    assessment_id = option("--assessment-id")
    rendered_at_utc = option("--rendered-at-utc")
    payload = {
        "readiness_assessment_id": assessment_id,
        "rendered_at_utc": rendered_at_utc,
        "simulated_paper_only": True,
        "checks": [{"status": "PASS"} for _ in range(8)],
        "phase12_code_version_git_sha": "4d70b823947fd61d0ea17df14c9f1ff9f93fd45b",
        "transport_profile_sha256": "4" * 64,
        "strategy_execution_eligible": False,
        "live_path_absent": True,
        "no_personalized_investment_advice": True,
        "no_real_performance_claimed": True,
        "report_sha256": "5" * 64,
    }
    output = Path(option("--output"))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "# Simulated / Paper Only / No Advice\n\n"
        f"- Readiness assessment ID: `{assessment_id}`\n"
        f"- Rendered at UTC: `{rendered_at_utc}`\n"
        f"- Report SHA-256: `{'5' * 64}`\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    raise SystemExit(0)

raise SystemExit(98)
"""

ALLOWED_EXTERNAL_HOSTS: Final = frozenset(("paper-api.alpaca.markets", "data.alpaca.markets"))
EXPECTED_CREDENTIAL_NAME_COUNTS: Final = {
    "scripts/preflight_paper_smoke.py": {KEY_ENV_NAME: 1, SECRET_ENV_NAME: 1},
    "scripts/report_paper_shadow_readiness.py": {KEY_ENV_NAME: 0, SECRET_ENV_NAME: 0},
    "scripts/run_paper_smoke.ps1": {KEY_ENV_NAME: 1, SECRET_ENV_NAME: 1},
}

URL_PATTERN: Final = re.compile(r"(?i)\b(?:https?|wss?)://[^\s\"'`<>()\[\]{}]+")
ALPACA_HOST_PATTERN: Final = re.compile(
    r"(?i)(?<![a-z0-9.-])(?:[a-z0-9-]+\.)*alpaca\.markets\.?(?![a-z0-9.-])"
)
QUOTED_LIVE_PATTERN: Final = re.compile(r"(?i)(?P<q>[\"'`])live(?P=q)")
LIVE_MODE_PATTERN: Final = re.compile(
    r"(?ix)(?:[\"']?execution[_-]?mode[\"']?|\$?executionmode)"
    r"\s*(?:=|:)\s*[\"'`]?live[\"'`]?|--execution-mode(?:=|\s+)live\b"
)
QUOTED_MUTATION_PATTERN: Final = re.compile(r"(?i)(?P<q>[\"'`])(?:POST|PUT|PATCH|DELETE)(?P=q)")
METHOD_PROPERTY_PATTERN: Final = re.compile(r"(?im)\bmethod\s*:\s*(?P<value>[^,}\r\n]+)")
FETCH_PATTERN: Final = re.compile(r"(?i)\b(?:[a-z_$][\w$]*\s*\.\s*)*fetch\s*\(")
FRONTEND_ALTERNATE_TRANSPORT_PATTERN: Final = re.compile(
    r"(?i)\b(?:XMLHttpRequest|WebSocket|EventSource|sendBeacon|axios|superagent|ky)\b"
)
FRONTEND_CREDENTIAL_READ_PATTERN: Final = re.compile(
    r"(?i)(?:process|import\.meta|Deno)\s*\.\s*env[^\r\n;]*(?:"
    + re.escape(KEY_ENV_NAME)
    + "|"
    + re.escape(SECRET_ENV_NAME)
    + r")"
)
POWERSHELL_DIRECT_ENV_PATTERN: Final = re.compile(
    r"(?i)\$env\s*:\s*(?:" + re.escape(KEY_ENV_NAME) + "|" + re.escape(SECRET_ENV_NAME) + r")"
)

MUTATION_METHODS: Final = frozenset(("post", "put", "patch", "delete"))
FORBIDDEN_ORDER_SURFACE_PATTERN: Final = re.compile(
    r"(?ix)(?:/(?:v\d+/)?orders(?:[/?#\"'`]|$)|"
    r"\b(?:submit|replace|cancel)[_-]?order\b|"
    r"\bclose[_-]?position\b|\bliquidat(?:e|ion)\b)"
)
LOG_SINK_NAMES: Final = frozenset(
    ("print", "pprint", "debug", "info", "warning", "error", "exception", "critical", "log")
)


@dataclass(frozen=True, order=True)
class Finding:
    relative_path: str
    rule_id: str

    def render(self) -> str:
        return f"{self.relative_path}: {self.rule_id}"


def _resolve_targets(root: Path) -> tuple[str, ...]:
    resolved: list[str] = []
    for spec in SURFACE_SPECS:
        if spec.endswith("/**"):
            directory = root / spec.removesuffix("/**")
            if directory.is_dir():
                resolved.extend(
                    path.relative_to(root).as_posix()
                    for path in directory.rglob("*")
                    if path.is_file() or path.is_symlink()
                )
        else:
            path = root / spec
            if path.is_file() or path.is_symlink():
                resolved.append(spec)
    return tuple(sorted(resolved))


def _collapse_simple_string_joins(source: str) -> str:
    previous = source
    for _ in range(8):
        collapsed = re.sub(r"[\"'`]\s*\+\s*[\"'`]", "", previous)
        if collapsed == previous:
            return collapsed
        previous = collapsed
    return previous


def _dotted_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _dotted_name(node.value)
        return f"{parent}.{node.attr}" if parent is not None else node.attr
    return None


def _constant_string(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _constant_string(node.left)
        right = _constant_string(node.right)
        if left is not None and right is not None:
            return left + right
    if isinstance(node, ast.JoinedStr) and all(
        isinstance(item, ast.Constant) for item in node.values
    ):
        values = [item.value for item in node.values]
        if all(isinstance(item, str) for item in values):
            return "".join(values)
    return None


def _assigned_names(node: ast.AST) -> set[str]:
    if isinstance(node, ast.Name):
        return {node.id}
    if isinstance(node, (ast.Tuple, ast.List)):
        return {name for item in node.elts for name in _assigned_names(item)}
    return set()


def _references_credential_name(node: ast.AST, aliases: set[str]) -> bool:
    for child in ast.walk(node):
        if isinstance(child, ast.Name) and child.id in aliases:
            return True
        if isinstance(child, ast.Constant) and child.value in CREDENTIAL_ENV_NAMES:
            return True
        if _constant_string(child) in CREDENTIAL_ENV_NAMES:
            return True
    return False


def _credential_aliases(tree: ast.AST) -> set[str]:
    aliases = {"PAPER_CREDENTIAL_ENV_NAMES"}
    changed = True
    while changed:
        changed = False
        for node in ast.walk(tree):
            targets: set[str] = set()
            value: ast.AST | None = None
            if isinstance(node, ast.Assign):
                targets = {name for target in node.targets for name in _assigned_names(target)}
                value = node.value
            elif isinstance(node, ast.AnnAssign):
                targets = _assigned_names(node.target)
                value = node.value
            if value is not None and _references_credential_name(value, aliases):
                before = len(aliases)
                aliases.update(targets)
                changed = changed or len(aliases) != before
    return aliases


def _is_credential_value_read(node: ast.AST, aliases: set[str]) -> bool:
    if isinstance(node, ast.Subscript) and _dotted_name(node.value) == "os.environ":
        return _references_credential_name(node.slice, aliases)
    if not isinstance(node, ast.Call):
        return False
    called = (_dotted_name(node.func) or "").casefold()
    if called in {"os.getenv", "os.environ.get", "os.environ.__getitem__"}:
        return bool(node.args) and _references_credential_name(node.args[0], aliases)
    if called.endswith(".get_secret_value"):
        return True
    if called in {"os.environ.copy", "os.environ.items", "os.environ.values"}:
        return True
    return False


def _loop_scoped_credential_reads(tree: ast.AST, aliases: set[str]) -> set[int]:
    reads: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.For, ast.AsyncFor)) and _references_credential_name(
            node.iter, aliases
        ):
            local_aliases = aliases | _assigned_names(node.target)
            for statement in (*node.body, *node.orelse):
                reads.update(
                    id(child)
                    for child in ast.walk(statement)
                    if _is_credential_value_read(child, local_aliases)
                )
        if isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            local_aliases = set(aliases)
            for generator in node.generators:
                if _references_credential_name(generator.iter, local_aliases):
                    local_aliases.update(_assigned_names(generator.target))
            reads.update(
                id(child)
                for child in ast.walk(node)
                if _is_credential_value_read(child, local_aliases)
            )
    return reads


def _python_findings(relative_path: str, source: str) -> set[Finding]:
    findings: set[Finding] = set()
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        findings.add(Finding(relative_path, "python_syntax_invalid"))
        return findings

    request_functions: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module in {"requests", "httpx"}:
            for imported in node.names:
                if imported.name.casefold() in MUTATION_METHODS:
                    request_functions[imported.asname or imported.name] = imported.name.casefold()

    aliases = _credential_aliases(tree)
    credential_reads = {
        id(node) for node in ast.walk(tree) if _is_credential_value_read(node, aliases)
    }
    credential_reads.update(_loop_scoped_credential_reads(tree, aliases))
    if credential_reads:
        findings.add(Finding(relative_path, "credential_value_read"))

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        called = _dotted_name(node.func) or ""
        called_parts = called.casefold().split(".")
        final_name = called_parts[-1] if called_parts else ""
        if final_name in MUTATION_METHODS or called in request_functions:
            findings.add(Finding(relative_path, "python_mutation_call"))
        if final_name == "request":
            candidates = list(node.args[:1]) + [
                keyword.value for keyword in node.keywords if keyword.arg == "method"
            ]
            if any(
                (value := _constant_string(candidate)) is not None
                and value.casefold() in MUTATION_METHODS
                for candidate in candidates
            ):
                findings.add(Finding(relative_path, "python_mutation_call"))
        if called == "getattr" and len(node.args) >= 2:
            method = _constant_string(node.args[1])
            if method is not None and method.casefold() in MUTATION_METHODS:
                findings.add(Finding(relative_path, "python_mutation_call"))
        if final_name in LOG_SINK_NAMES and any(
            id(child) in credential_reads
            for argument in (*node.args, *(item.value for item in node.keywords))
            for child in ast.walk(argument)
        ):
            findings.add(Finding(relative_path, "credential_value_sink"))

    for node in ast.walk(tree):
        value = _constant_string(node)
        if value is None:
            continue
        if value.casefold() == "live":
            findings.add(Finding(relative_path, "live_execution_mode"))
        if "alpaca.markets" in value.casefold():
            findings.update(_host_findings(relative_path, value))
    return findings


def _host_findings(relative_path: str, source: str) -> set[Finding]:
    findings: set[Finding] = set()
    for match in URL_PATTERN.finditer(source):
        parsed = urlsplit(match.group(0).rstrip(".,;:"))
        hostname = (parsed.hostname or "").rstrip(".").casefold()
        if parsed.scheme.casefold() != "https" or hostname not in ALLOWED_EXTERNAL_HOSTS:
            findings.add(Finding(relative_path, "forbidden_host_literal"))
    for match in ALPACA_HOST_PATTERN.finditer(source):
        if match.group(0).rstrip(".").casefold() not in ALLOWED_EXTERNAL_HOSTS:
            findings.add(Finding(relative_path, "forbidden_host_literal"))
    return findings


def _frontend_findings(relative_path: str, source: str) -> set[Finding]:
    findings: set[Finding] = set()
    fetch_count = len(FETCH_PATTERN.findall(source))
    if relative_path == READINESS_API_PATH:
        if fetch_count != 1:
            findings.add(Finding(relative_path, "browser_fetch_inventory_invalid"))
    elif fetch_count:
        findings.add(Finding(relative_path, "browser_fetch_inventory_invalid"))
    for match in METHOD_PROPERTY_PATTERN.finditer(source):
        if re.fullmatch(r"[\"'`]GET[\"'`]", match.group("value").strip(), re.IGNORECASE) is None:
            findings.add(Finding(relative_path, "browser_mutation_fetch"))
    for match in re.finditer(r"(?im)\bcredentials\s*:\s*(?P<value>[^,}\r\n]+)", source):
        if re.fullmatch(r"[\"'`]omit[\"'`]", match.group("value").strip(), re.IGNORECASE) is None:
            findings.add(Finding(relative_path, "browser_credentials_not_omitted"))
    if FRONTEND_ALTERNATE_TRANSPORT_PATTERN.search(source):
        findings.add(Finding(relative_path, "browser_transport_not_allowed"))
    if re.search(r"(?i)\b(?:dangerouslySetInnerHTML|innerHTML|response\.text)\b", source):
        findings.add(Finding(relative_path, "unsanitized_browser_output"))
    if re.search(r"(?i)\bconsole\s*\.", source):
        findings.add(Finding(relative_path, "browser_console_sink"))
    if FRONTEND_CREDENTIAL_READ_PATTERN.search(source):
        findings.add(Finding(relative_path, "credential_value_read"))
    if "FABLE5_ALPACA" in source.upper():
        findings.add(Finding(relative_path, "credential_name_in_browser"))
    return findings


def _powershell_findings(relative_path: str, source: str) -> set[Finding]:
    findings: set[Finding] = set()
    if POWERSHELL_DIRECT_ENV_PATTERN.search(source):
        findings.add(Finding(relative_path, "credential_value_read"))
    if re.search(r"(?i)GetEnvironmentVariables?\s*\(", source):
        findings.add(Finding(relative_path, "credential_value_read"))
    if re.search(r"(?i)\bGet-(?:Item|ChildItem|Content)\s+Env\s*:", source):
        findings.add(Finding(relative_path, "credential_value_read"))
    for line in source.splitlines():
        if "env:" in line.casefold() and "test-path" not in line.casefold():
            findings.add(Finding(relative_path, "credential_presence_boundary_invalid"))
        if re.search(r"(?i)(?:Write-|Out-|Tee-|Console).*\$(?:key|secret)(?:Name|Present)\b", line):
            findings.add(Finding(relative_path, "credential_value_sink"))
    if re.search(
        r"(?i)\b(?:Invoke-RestMethod|Invoke-WebRequest|Invoke-Expression|curl|wget)\b", source
    ):
        findings.add(Finding(relative_path, "powershell_transport_not_allowed"))
    if re.search(
        r"(?i)\b(?:HttpClient|HttpWebRequest|WebRequest|TcpClient|"
        r"SendAsync|PostAsync|PutAsync|PatchAsync|DeleteAsync)\b",
        source,
    ):
        findings.add(Finding(relative_path, "powershell_transport_not_allowed"))
    return findings


def _scan_source(relative_path: str, source: str) -> tuple[Finding, ...]:
    findings = _host_findings(relative_path, source)
    collapsed = _collapse_simple_string_joins(source)
    if collapsed != source:
        findings.update(_host_findings(relative_path, collapsed))
    if QUOTED_LIVE_PATTERN.search(source) or LIVE_MODE_PATTERN.search(collapsed):
        findings.add(Finding(relative_path, "live_execution_mode"))
    if QUOTED_MUTATION_PATTERN.search(collapsed):
        findings.add(Finding(relative_path, "mutation_method_literal"))
    if FORBIDDEN_ORDER_SURFACE_PATTERN.search(collapsed):
        findings.add(Finding(relative_path, "forbidden_order_surface"))

    expected_counts = EXPECTED_CREDENTIAL_NAME_COUNTS.get(
        relative_path, {KEY_ENV_NAME: 0, SECRET_ENV_NAME: 0}
    )
    if any(collapsed.count(name) != expected_counts[name] for name in CREDENTIAL_ENV_NAMES):
        findings.add(Finding(relative_path, "credential_name_inventory_invalid"))

    suffix = Path(relative_path).suffix.casefold()
    if suffix == ".py":
        findings.update(_python_findings(relative_path, source))
    elif suffix == ".ps1":
        findings.update(_powershell_findings(relative_path, source))
    elif suffix in {".ts", ".tsx"}:
        findings.update(_frontend_findings(relative_path, source))
    return tuple(sorted(findings))


def _scan_surface(root: Path) -> tuple[Finding, ...]:
    findings: set[Finding] = set()
    resolved = _resolve_targets(root)
    if resolved != EXPECTED_TARGETS:
        findings.add(Finding(".", "target_inventory_invalid"))
    for relative_path in EXPECTED_TARGETS:
        path = root / relative_path
        if not path.is_file() or path.is_symlink():
            findings.add(Finding(relative_path, "target_not_regular_file"))
            continue
        try:
            source = path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError):
            findings.add(Finding(relative_path, "target_text_unreadable"))
            continue
        findings.update(_scan_source(relative_path, source))
    return tuple(sorted(findings))


def _render_findings(findings: tuple[Finding, ...]) -> str:
    return "\n".join(finding.render() for finding in findings)


def _copy_surface(destination: Path) -> None:
    for relative_path in EXPECTED_TARGETS:
        source = ROOT / relative_path
        target = destination / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def _prepare_harness_stub_root(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    if not PYTHON_LAUNCHER.is_file() or not PYVENV_CONFIG.is_file():
        pytest.skip("the repository virtual environment is required for the T-004 canary proof")
    harness_root = tmp_path / "paper-smoke-harness"
    scripts_root = harness_root / "scripts"
    venv_root = harness_root / ".venv"
    venv_scripts = venv_root / "Scripts"
    scripts_root.mkdir(parents=True)
    venv_scripts.mkdir(parents=True)
    shutil.copy2(ROOT / "scripts" / "run_paper_smoke.ps1", scripts_root)
    shutil.copy2(PYTHON_LAUNCHER, venv_scripts / "python.exe")
    shutil.copy2(PYVENV_CONFIG, venv_root / "pyvenv.cfg")
    for name in (
        "preflight_paper_smoke.py",
        "capture_paper_shadow_readiness.py",
        "report_paper_shadow_readiness.py",
    ):
        (scripts_root / name).write_text(HARNESS_STUB_SOURCE, encoding="utf-8")
    return (
        scripts_root / "run_paper_smoke.ps1",
        harness_root / "preflight.json",
        harness_root / "evidence.md",
        harness_root / "capture-called.txt",
    )


class _ScalarResult:
    def scalar_one(self) -> int:
        return 1


class _Connection:
    def __enter__(self) -> _Connection:
        return self

    def __exit__(self, *args: object) -> None:
        del args

    def exec_driver_sql(self, statement: str) -> _ScalarResult:
        assert statement == "SELECT 1"
        return _ScalarResult()


class _Engine:
    def connect(self) -> _Connection:
        return _Connection()


class _MemoryReadinessRepository:
    def __init__(self) -> None:
        self.engine = _Engine()
        self.by_key: dict[str, PaperShadowReadinessArtifact] = {}
        self.by_id: dict[UUID, PaperShadowReadinessArtifact] = {}

    @contextmanager
    def serialized_creation(self, key: str) -> Iterator[_MemoryReadinessRepository]:
        del key
        yield self

    def find_by_idempotency_key(self, key: str) -> PaperShadowReadinessArtifact | None:
        return self.by_key.get(key)

    def create_readiness(
        self, artifact: PaperShadowReadinessArtifact
    ) -> PaperShadowReadinessArtifact:
        self.by_key[artifact.readiness_idempotency_key] = artifact
        self.by_id[artifact.readiness_assessment_id] = artifact
        return artifact

    def get_readiness(self, readiness_assessment_id: UUID) -> PaperShadowReadinessArtifact:
        return self.by_id[readiness_assessment_id]

    def dispose(self) -> None:
        return None


def _successful_local_command(command: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
    if command == ("node", "--version"):
        stdout = "v22.14.0"
    elif command[:2] == ("git", "rev-parse"):
        stdout = GIT_SHA
    elif command[:2] == ("git", "status"):
        stdout = " M AGENTS.md\n"
    elif command[:3] == ("docker", "compose", "config") or "verify_phase1.py" in command[1]:
        stdout = f"{KEY_CANARY}:{SECRET_CANARY}"
    else:
        raise AssertionError("unexpected local preflight command")
    return subprocess.CompletedProcess(list(command), 0, stdout, f"{SECRET_CANARY}:{KEY_CANARY}")


def _assert_no_canary_output(rendered: str) -> None:
    forbidden = (
        KEY_CANARY,
        SECRET_CANARY,
        "CANARY_KEY",
        "CANARY_SECRET",
        "9f3",
        "7c1",
        "FABLE5_ALPACA",
    )
    if any(value in rendered for value in forbidden):
        raise AssertionError("paper smoke output contained forbidden credential material")


def test_target_inventory_is_exact_and_current_surface_passes() -> None:
    assert SURFACE_SPECS == (
        "scripts/preflight_paper_smoke.py",
        "scripts/report_paper_shadow_readiness.py",
        "scripts/run_paper_smoke.ps1",
        "services/frontend/src/app/paper/readiness/**",
    )
    assert ALLOWED_EXTERNAL_HOSTS == frozenset(("paper-api.alpaca.markets", "data.alpaca.markets"))
    assert _resolve_targets(ROOT) == EXPECTED_TARGETS
    findings = _scan_surface(ROOT)
    assert findings == (), _render_findings(findings)


@pytest.mark.parametrize("relative_path", EXPECTED_TARGETS, ids=EXPECTED_TARGETS)
@pytest.mark.parametrize(
    ("case_id", "expected_rule"),
    (("forbidden-host", "forbidden_host_literal"), ("live-mode", "live_execution_mode")),
    ids=("forbidden-host", "live-mode"),
)
def test_mandated_literals_fail_in_every_temporary_target(
    tmp_path: Path,
    relative_path: str,
    case_id: str,
    expected_rule: str,
) -> None:
    payloads = {
        "forbidden-host": "https://api.alpaca.markets",
        "live-mode": 'execution_mode = "live"',
    }
    _copy_surface(tmp_path)
    target = tmp_path / relative_path
    with target.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write("\n" + payloads[case_id] + "\n")

    findings = _scan_surface(tmp_path)
    rendered = _render_findings(findings)
    if Finding(relative_path, expected_rule) not in findings:
        raise AssertionError("temporary-copy injection was not detected")
    if payloads[case_id] in rendered:
        raise AssertionError("finding output reproduced planted input")


def test_only_the_two_documented_hosts_are_accepted(tmp_path: Path) -> None:
    _copy_surface(tmp_path)
    target = tmp_path / f"{READINESS_ROOT}/PaperReadinessWorkspace.module.css"
    with target.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write("\n/* https://paper-api.alpaca.markets https://data.alpaca.markets */\n")
    findings = _scan_surface(tmp_path)
    assert (
        Finding(target.relative_to(tmp_path).as_posix(), "forbidden_host_literal") not in findings
    )


@pytest.mark.parametrize(
    ("case_id", "relative_path", "expected_rule"),
    (
        ("requests-alias", "scripts/preflight_paper_smoke.py", "python_mutation_call"),
        ("requests-import", "scripts/report_paper_shadow_readiness.py", "python_mutation_call"),
        ("fetch-mutation", READINESS_API_PATH, "browser_mutation_fetch"),
        ("fetch-dynamic", READINESS_API_PATH, "browser_mutation_fetch"),
        ("python-credential", "scripts/preflight_paper_smoke.py", "credential_value_read"),
        ("python-credential-loop", "scripts/preflight_paper_smoke.py", "credential_value_read"),
        ("python-credential-split", "scripts/preflight_paper_smoke.py", "credential_value_read"),
        ("powershell-credential", "scripts/run_paper_smoke.ps1", "credential_value_read"),
        ("browser-credential", READINESS_API_PATH, "credential_value_read"),
        (
            "browser-credential-split",
            READINESS_API_PATH,
            "credential_name_inventory_invalid",
        ),
        ("browser-qualified-fetch", READINESS_API_PATH, "browser_mutation_fetch"),
        ("browser-ky", READINESS_API_PATH, "browser_transport_not_allowed"),
        (
            "powershell-httpclient",
            "scripts/run_paper_smoke.ps1",
            "powershell_transport_not_allowed",
        ),
        ("order-route", READINESS_API_PATH, "forbidden_order_surface"),
        (
            "trailing-dot-host",
            f"{READINESS_ROOT}/PaperReadinessWorkspace.module.css",
            "forbidden_host_literal",
        ),
    ),
    ids=(
        "requests-alias",
        "requests-import",
        "fetch-mutation",
        "fetch-dynamic",
        "python-credential",
        "python-credential-loop",
        "python-credential-split",
        "powershell-credential",
        "browser-credential",
        "browser-credential-split",
        "browser-qualified-fetch",
        "browser-ky",
        "powershell-httpclient",
        "order-route",
        "trailing-dot-host",
    ),
)
def test_language_specific_adversarial_injections_fail_safely(
    tmp_path: Path,
    case_id: str,
    relative_path: str,
    expected_rule: str,
) -> None:
    payloads = {
        "requests-alias": 'import requests as rq\nrq.post("/local-only")',
        "requests-import": 'from requests import delete as remove\nremove("/local-only")',
        "fetch-mutation": 'fetch("/local-only", { method: "POST" });',
        "fetch-dynamic": 'const verb = "GET"; fetch("/local-only", { method: verb });',
        "python-credential": (
            "credential_value = os.environ[PAPER_CREDENTIAL_ENV_NAMES[0]]\nprint(credential_value)"
        ),
        "python-credential-loop": (
            "for credential_name in PAPER_CREDENTIAL_ENV_NAMES:\n"
            "    print(os.environ[credential_name])"
        ),
        "python-credential-split": (
            'credential_name = "FABLE5_" + "ALPACA_PAPER_API_KEY_ID"\n'
            "print(os.environ[credential_name])"
        ),
        "powershell-credential": f"Write-Output $env:{KEY_ENV_NAME}",
        "browser-credential": f"console.log(process.env.{SECRET_ENV_NAME});",
        "browser-credential-split": (
            'const credentialName = "FABLE5_" + "ALPACA_" + "PAPER_API_KEY_ID";\n'
            "const leaked = process.env[credentialName];"
        ),
        "browser-qualified-fetch": 'window.fetch("/local-only", { method: "POST" });',
        "browser-ky": 'ky.post("/local-only");',
        "powershell-httpclient": (
            "[Net.Http.HttpClient]::new().PostAsync("
            '"https://paper-api.alpaca.markets/v2/orders", $null)'
        ),
        "order-route": 'const forbiddenPath = "/v2/orders";',
        "trailing-dot-host": "api.alpaca.markets.",
    }
    _copy_surface(tmp_path)
    target = tmp_path / relative_path
    with target.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write("\n" + payloads[case_id] + "\n")

    findings = _scan_surface(tmp_path)
    rendered = _render_findings(findings)
    if Finding(relative_path, expected_rule) not in findings:
        raise AssertionError("language-specific injection was not detected")
    if payloads[case_id] in rendered or KEY_CANARY in rendered or SECRET_CANARY in rendered:
        raise AssertionError("finding output reproduced adversarial input")


def test_real_preflight_and_report_outputs_hide_canaries(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = _MemoryReadinessRepository()
    workflow_type = preflight.PaperShadowReadinessWorkflow
    monkeypatch.setattr(preflight, "_current_python_version", lambda: (3, 12, 13))
    monkeypatch.setattr(preflight, "_utc_now", lambda: FIXED_NOW)
    monkeypatch.setattr(preflight, "_run_command", _successful_local_command)
    monkeypatch.setattr(preflight, "_new_repository", lambda database_url: repository)
    monkeypatch.setattr(
        preflight,
        "PaperShadowReadinessWorkflow",
        lambda **kwargs: workflow_type(**kwargs, clock=lambda: FIXED_NOW),
    )
    monkeypatch.setenv(preflight.DATABASE_URL_ENV_NAME, DATABASE_URL)
    monkeypatch.setenv(KEY_ENV_NAME, KEY_CANARY)
    monkeypatch.setenv(SECRET_ENV_NAME, SECRET_CANARY)
    for name in preflight.LIBPQ_ROUTING_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)

    preflight_path = tmp_path / "preflight.json"
    preflight_exit = preflight.main(["--output", str(preflight_path)])
    preflight_capture = capsys.readouterr()
    preflight_text = preflight_path.read_text(encoding="utf-8") if preflight_path.is_file() else ""
    _assert_no_canary_output(preflight_capture.out + preflight_capture.err + preflight_text)
    assert preflight_exit == 0
    assert preflight_path.is_file()
    preflight_payload = json.loads(preflight_text)
    assessment_id = UUID(preflight_payload["mock_readiness_assessment_id"])

    monkeypatch.setattr(report_cli, "_new_repository", lambda database_url: repository)
    monkeypatch.setenv(report_cli.DATABASE_URL_ENV_NAME, DATABASE_URL)
    report_path = tmp_path / "readiness-evidence.md"
    report_exit = report_cli.main(
        [
            "--assessment-id",
            str(assessment_id),
            "--rendered-at-utc",
            "2026-07-22T14:30:00.123456Z",
            "--output",
            str(report_path),
        ]
    )
    report_capture = capsys.readouterr()
    report_text = report_path.read_text(encoding="utf-8") if report_path.is_file() else ""
    _assert_no_canary_output(report_capture.out + report_capture.err + report_text)
    assert report_exit == 0
    assert report_path.is_file()
    report_payload = json.loads(report_capture.out)
    assert preflight_payload["credential_pair"] == "PRESENT_PAIR"
    assert preflight_payload["mock_readiness"] == "MOCK_PROOF_COMPLETE"
    assert preflight_payload["git_sha"] == GIT_SHA
    assert preflight_payload["random_seed"] is None
    assert preflight_payload["trial_count"] is None
    assert re.fullmatch(r"[0-9a-f]{64}", preflight_payload["config_sha256"])
    assert re.fullmatch(r"[0-9a-f]{64}", preflight_payload["report_sha256"])
    assert report_payload["readiness_assessment_id"] == str(assessment_id)
    assert report_payload["phase12_code_version_git_sha"] == GIT_SHA
    assert re.fullmatch(r"[0-9a-f]{64}", report_payload["report_sha256"])
    assert report_payload["rendered_at_utc"] == "2026-07-22T14:30:00.123456Z"


def test_mock_harness_composition_hides_canaries_without_credentialed_capture(
    tmp_path: Path,
) -> None:
    powershell = shutil.which("powershell")
    if powershell is None:
        pytest.skip("Windows PowerShell is required for the T-004 canary proof")
    script, preflight_path, report_path, capture_marker = _prepare_harness_stub_root(tmp_path)
    environment = os.environ.copy()
    environment[KEY_ENV_NAME] = KEY_CANARY
    environment[SECRET_ENV_NAME] = SECRET_CANARY
    environment["FABLE5_T005_CAPTURE_MARKER"] = str(capture_marker)
    try:
        result = subprocess.run(
            [
                powershell,
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script),
                "-PreflightOutput",
                str(preflight_path),
                "-EvidenceOutput",
                str(report_path),
            ],
            cwd=script.parents[1],
            env=environment,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        stdout = error.stdout if isinstance(error.stdout, str) else ""
        stderr = error.stderr if isinstance(error.stderr, str) else ""
        _assert_no_canary_output(stdout + stderr)
        raise AssertionError("paper smoke harness canary proof timed out") from None

    preflight_text = preflight_path.read_text(encoding="utf-8") if preflight_path.is_file() else ""
    report_text = report_path.read_text(encoding="utf-8") if report_path.is_file() else ""
    _assert_no_canary_output(result.stdout + result.stderr + preflight_text + report_text)
    assert result.returncode == 0
    assert capture_marker.exists() is False
    assert preflight_path.is_file()
    assert report_path.is_file()
    assert result.stdout.splitlines().count(MOCK_FALLBACK_LINE) == 1
    assert json.loads(preflight_text)["mock_readiness"] == "MOCK_PROOF_COMPLETE"
