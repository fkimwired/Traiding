from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE_START = "1. **No live trading. Paper trading only.**"
GATE_END = "   are configured; never invent real results."
GATE_SHA256 = "1c6586b54c77c5a9df8e9838638631127cb2e5bc0af1c813b27b7f6af355d672"
REQUIRED_PATHS = (
    "README.md",
    "AGENTS.md",
    "CLAUDE.md",
    "compose.yaml",
    "pyproject.toml",
    "requirements.lock",
    "package.json",
    "docs/PRODUCT_BRIEF.md",
    "docs/STRATEGY_CANON.md",
    "docs/EVALS.md",
    "docs/RISK_POLICY.md",
    "docs/DATA_SOURCES.md",
    "docs/COMPLIANCE_NOTES.md",
    "docs/RESEARCH_SUPPLEMENT.md",
    "packages/contracts/openapi.json",
    "packages/contracts/src/api.generated.ts",
    "services/api/Dockerfile",
    "services/api/migrations/versions/0001_phase1_audit_spine.py",
    "services/api/src/fable5_api/main.py",
    "services/jobs/Dockerfile",
    "services/jobs/src/fable5_jobs/worker.py",
    "services/frontend/Dockerfile",
    "services/frontend/src/app/page.tsx",
    "services/backtester/README.md",
    "services/extraction/README.md",
    "services/risk/README.md",
    "strategy_specs/README.md",
)
FORBIDDEN_EXECUTABLE_PATTERNS = re.compile(
    r"submit_order|place_order|create_order|/v2/orders|api\.alpaca\.markets|"
    r"alpaca-py|ib_insync|\bibapi\b|\bccxt\b",
    re.IGNORECASE,
)
PHASE_1_ONLY_FORBIDDEN_PATTERNS = re.compile(r"TradingIdeaCard", re.IGNORECASE)


def phase_number(value: str) -> int:
    try:
        phase = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("phase must be 1 or 2") from exc
    if phase not in {1, 2}:
        raise argparse.ArgumentTypeError("phase must be 1 or 2")
    return phase


def normalized(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")


def canonical_gates() -> str:
    prompt = normalized(ROOT / "FABLE5_BUILD_PROMPT.md")
    start = prompt.index(GATE_START)
    end = prompt.index(GATE_END, start) + len(GATE_END)
    gates = prompt[start:end]
    digest = hashlib.sha256(gates.encode()).hexdigest()
    if digest != GATE_SHA256:
        raise AssertionError(f"Unexpected hard-gate source block hash: {digest}")
    return gates


def verify_static(phase: int = 1) -> None:
    missing = [path for path in REQUIRED_PATHS if not (ROOT / path).exists()]
    if missing:
        raise AssertionError(f"Missing Phase 1 paths: {', '.join(missing)}")

    gates = canonical_gates()
    for filename in ("AGENTS.md", "CLAUDE.md"):
        body = normalized(ROOT / filename)
        if not body.startswith(gates + "\n\n"):
            raise AssertionError(f"{filename} does not begin with the verbatim hard gates")

    if normalized(ROOT / "RESEARCH_SUPPLEMENT.md") != normalized(
        ROOT / "docs" / "RESEARCH_SUPPLEMENT.md"
    ):
        raise AssertionError("docs/RESEARCH_SUPPLEMENT.md drifted from its source")

    scan_roots = [
        ROOT / "services",
        ROOT / "packages",
        ROOT / "pyproject.toml",
        ROOT / "package.json",
    ]
    violations: list[str] = []
    for scan_root in scan_roots:
        candidates = [scan_root] if scan_root.is_file() else scan_root.rglob("*")
        for path in candidates:
            if not path.is_file() or "tests" in path.parts:
                continue
            if path.suffix not in {".py", ".ts", ".tsx", ".js", ".mjs", ".json", ".toml"}:
                continue
            body = path.read_text(encoding="utf-8")
            patterns = [FORBIDDEN_EXECUTABLE_PATTERNS]
            if phase == 1:
                patterns.append(PHASE_1_ONLY_FORBIDDEN_PATTERNS)
            for pattern in patterns:
                match = pattern.search(body)
                if match:
                    violations.append(f"{path.relative_to(ROOT)}: {match.group(0)}")
                    break
    if violations:
        raise AssertionError(f"Forbidden code found for Phase {phase}: " + "; ".join(violations))

    print(f"Static repository policy checks passed for Phase {phase}.")


def run(
    command: list[str],
    *,
    project: str | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    if project is not None:
        command = ["docker", "compose", "--project-name", project, *command]
    print("+", " ".join(command))
    return subprocess.run(command, cwd=ROOT, check=True, text=True, env=env)


def acceptance_environment() -> tuple[dict[str, str], str, str]:
    sockets: list[socket.socket] = []
    try:
        for _ in range(4):
            listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            listener.bind(("127.0.0.1", 0))
            sockets.append(listener)
        api_port, frontend_port, postgres_port, redis_port = (
            listener.getsockname()[1] for listener in sockets
        )
    finally:
        for listener in sockets:
            listener.close()

    api_url = f"http://127.0.0.1:{api_port}"
    frontend_url = f"http://127.0.0.1:{frontend_port}"
    environment = os.environ.copy()
    environment.update(
        {
            "API_PORT": str(api_port),
            "FRONTEND_PORT": str(frontend_port),
            "POSTGRES_PORT": str(postgres_port),
            "REDIS_PORT": str(redis_port),
            "POSTGRES_DB": "fable5",
            "POSTGRES_USER": "fable5",
            "POSTGRES_PASSWORD": "fable5_dev_only",
            "FABLE5_ENVIRONMENT": "test",
            "FABLE5_EXECUTION_MODE": "paper",
            "FABLE5_DATABASE_URL": (
                "postgresql+psycopg://fable5:fable5_dev_only@postgres:5432/fable5"
            ),
            "FABLE5_REDIS_URL": "redis://redis:6379/0",
            "FABLE5_CORS_ORIGINS": json.dumps(
                [
                    f"http://localhost:{frontend_port}",
                    frontend_url,
                ]
            ),
            "NEXT_PUBLIC_API_URL": api_url,
        }
    )
    return environment, api_url, frontend_url


def fetch_json(url: str) -> dict[str, object]:
    with urllib.request.urlopen(url, timeout=5) as response:
        if response.status != 200:
            raise AssertionError(f"{url} returned {response.status}")
        if "application/json" not in response.headers.get("content-type", ""):
            raise AssertionError(f"{url} did not return JSON")
        return json.load(response)


def wait_for_frontend(url: str, timeout: int = 60) -> str:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                if response.status == 200:
                    return response.read().decode("utf-8")
        except Exception as exc:  # pragma: no cover - integration-only polling
            last_error = exc
        time.sleep(2)
    raise AssertionError(f"Frontend did not become ready: {last_error}")


def verify_compose() -> None:
    if shutil.which("docker") is None:
        raise RuntimeError("Docker is required for full verification; use --static-only otherwise.")

    project = f"fable5_acceptance_{uuid.uuid4().hex[:8]}"
    environment, api_url, frontend_url = acceptance_environment()
    try:
        run(["config", "--quiet"], project=project, env=environment)
        run(
            ["up", "--detach", "--build", "--wait", "--wait-timeout", "240"],
            project=project,
            env=environment,
        )

        health = fetch_json(f"{api_url}/health")
        expected_health = {
            "status": "ok",
            "service": "api",
            "mode": "research-paper-only",
        }
        if health != expected_health:
            raise AssertionError(f"Unexpected health response: {health}")

        ready = fetch_json(f"{api_url}/ready")
        if ready.get("status") != "ready":
            raise AssertionError(f"Unexpected readiness response: {ready}")

        html = wait_for_frontend(frontend_url)
        for label in ("Idea Intake", "Research Lab", "Paper Trading", "Risk / Compliance"):
            if label not in html:
                raise AssertionError(f"Frontend HTML is missing navigation label: {label}")

        pong = subprocess.run(
            [
                "docker",
                "compose",
                "--project-name",
                project,
                "exec",
                "-T",
                "redis",
                "redis-cli",
                "ping",
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            env=environment,
        ).stdout.strip()
        if pong != "PONG":
            raise AssertionError(f"Redis health check returned {pong!r}")

        run(
            ["exec", "-T", "api", "alembic", "-c", "services/api/alembic.ini", "downgrade", "base"],
            project=project,
            env=environment,
        )
        run(
            ["exec", "-T", "api", "alembic", "-c", "services/api/alembic.ini", "upgrade", "head"],
            project=project,
            env=environment,
        )
        print("Full Compose Phase 1 verification passed.")
    finally:
        subprocess.run(
            ["docker", "compose", "--project-name", project, "down", "--volumes"],
            cwd=ROOT,
            check=False,
            text=True,
            env=environment,
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify phase-aware repository policy and services."
    )
    parser.add_argument("--static-only", action="store_true")
    parser.add_argument(
        "--phase",
        type=phase_number,
        default=os.environ.get("FABLE5_VERIFY_PHASE", "1"),
        help=(
            "Apply repository policy checks for phase 1 or 2 (default: FABLE5_VERIFY_PHASE or 1)."
        ),
    )
    args = parser.parse_args()
    verify_static(args.phase)
    if not args.static_only:
        verify_compose()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"Repository verification failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
