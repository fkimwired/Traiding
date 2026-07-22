"""Run the sanitized, paper-only operator preflight for the local smoke test."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from ipaddress import ip_address
from pathlib import Path
from typing import Final, NoReturn

from fable5_paper.phase12.adapters import DeterministicMockPaperBrokerAdapter
from fable5_paper.phase12.canonical import canonical_json_bytes
from fable5_paper.phase12.contracts import (
    PaperShadowReadinessCreateRequest,
    ReadinessOutcome,
)
from fable5_paper.phase12.repository import PaperShadowReadinessRepository
from fable5_paper.phase12.workflow import PaperShadowReadinessWorkflow
from sqlalchemy.engine import make_url

ROOT: Final = Path(__file__).resolve().parents[1]
FAILURE_MESSAGE: Final = "Paper smoke preflight failed."
SCHEMA_VERSION: Final = "fable5-paper-smoke-preflight-v1"

PAPER_CREDENTIAL_ENV_NAMES: Final = (
    "FABLE5_ALPACA_PAPER_API_KEY_ID",
    "FABLE5_ALPACA_PAPER_SECRET_KEY",
)
DATABASE_URL_ENV_NAME: Final = "FABLE5_DATABASE_URL"
LIBPQ_ROUTING_ENV_NAMES: Final = (
    "PGHOST",
    "PGHOSTADDR",
    "PGSERVICE",
    "PGSERVICEFILE",
    "PGSYSCONFDIR",
)

PYTHON_REQUIRED_MAJOR_MINOR: Final = (3, 12)
NODE_MINIMUM_VERSION: Final = (22, 14, 0)
NODE_VERSION_PATTERN: Final = re.compile(r"^v?(\d{1,10})\.(\d{1,10})\.(\d{1,10})$")
GIT_SHA_PATTERN: Final = re.compile(r"^[0-9a-f]{40}$")

CHECK_ORDER: Final = (
    "python_version",
    "node_version",
    "docker_compose_config",
    "phase26_static_verification",
    "credential_pair",
    "database_reachability",
    "mock_readiness",
)

PREFLIGHT_CONFIG: Final = {
    "schema_version": SCHEMA_VERSION,
    "execution_mode": "paper",
    "check_order": CHECK_ORDER,
    "python_required_major_minor": PYTHON_REQUIRED_MAJOR_MINOR,
    "node_minimum_version": NODE_MINIMUM_VERSION,
    "static_verification_phase": 26,
    "database_scope": "loopback_postgresql_only",
    "mock_required_outcome": ReadinessOutcome.MOCK_PROOF_COMPLETE.value,
}
CONFIG_SHA256: Final = hashlib.sha256(canonical_json_bytes(PREFLIGHT_CONFIG)).hexdigest()


class PreflightInvocationError(ValueError):
    """An invocation failure whose user-controlled details must not be rendered."""


class _SanitizedArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        del message
        raise PreflightInvocationError


class _SingleValueAction(argparse.Action):
    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: object,
        option_string: str | None = None,
    ) -> None:
        del parser, option_string
        if getattr(namespace, self.dest, None) is not None:
            raise PreflightInvocationError
        setattr(namespace, self.dest, values)


@dataclass(frozen=True, slots=True)
class CheckResult:
    name: str
    status: str
    reason_code: str
    observed_version: str | None = None

    def as_report_value(self) -> dict[str, object]:
        value: dict[str, object] = {
            "name": self.name,
            "status": self.status,
            "reason_code": self.reason_code,
        }
        if self.observed_version is not None:
            value["observed_version"] = self.observed_version
        return value


@dataclass(frozen=True, slots=True)
class MockProof:
    check: CheckResult
    outcome: str
    readiness_assessment_id: str | None = None
    artifact_sha256: str | None = None


def _parser() -> argparse.ArgumentParser:
    parser = _SanitizedArgumentParser(
        description=(
            "Run one local PAPER ONLY preflight and emit sanitized deterministic mock evidence."
        ),
        allow_abbrev=False,
    )
    parser.add_argument("--output", action=_SingleValueAction)
    return parser


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _current_python_version() -> tuple[int, int, int]:
    return sys.version_info.major, sys.version_info.minor, sys.version_info.micro


def _sanitized_child_environment() -> dict[str, str]:
    excluded = frozenset((*PAPER_CREDENTIAL_ENV_NAMES, DATABASE_URL_ENV_NAME))
    return {name: os.environ[name] for name in os.environ if name not in excluded}


def _run_command(command: tuple[str, ...]) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            list(command),
            cwd=ROOT,
            env=_sanitized_child_environment(),
            shell=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None


def _python_version_check() -> CheckResult:
    version = _current_python_version()
    observed = ".".join(str(part) for part in version)
    if version[:2] == PYTHON_REQUIRED_MAJOR_MINOR:
        return CheckResult("python_version", "PASS", "PYTHON_VERSION_SUPPORTED", observed)
    return CheckResult("python_version", "FAIL", "PYTHON_VERSION_UNSUPPORTED", observed)


def _node_version_check() -> CheckResult:
    completed = _run_command(("node", "--version"))
    if completed is None or completed.returncode != 0 or not isinstance(completed.stdout, str):
        return CheckResult("node_version", "FAIL", "NODE_VERSION_CHECK_FAILED")
    matched = NODE_VERSION_PATTERN.fullmatch(completed.stdout.strip())
    if matched is None:
        return CheckResult("node_version", "FAIL", "NODE_VERSION_CHECK_FAILED")
    version = tuple(int(part) for part in matched.groups())
    observed = ".".join(str(part) for part in version)
    if version >= NODE_MINIMUM_VERSION:
        return CheckResult("node_version", "PASS", "NODE_VERSION_SUPPORTED", observed)
    return CheckResult("node_version", "FAIL", "NODE_VERSION_UNSUPPORTED", observed)


def _command_check(
    *, name: str, command: tuple[str, ...], pass_reason: str, fail_reason: str
) -> CheckResult:
    completed = _run_command(command)
    if completed is not None and completed.returncode == 0:
        return CheckResult(name, "PASS", pass_reason)
    return CheckResult(name, "FAIL", fail_reason)


def _credential_pair_check() -> tuple[str, CheckResult]:
    first_present, second_present = (name in os.environ for name in PAPER_CREDENTIAL_ENV_NAMES)
    if first_present and second_present:
        state = "PRESENT_PAIR"
        status = "PASS"
    elif not first_present and not second_present:
        state = "ABSENT_PAIR"
        status = "WARN"
    else:
        state = "INCOMPLETE_PAIR"
        status = "FAIL"
    return state, CheckResult("credential_pair", status, state)


def _database_url_is_local_postgresql(value: str) -> bool:
    if any(name in os.environ for name in LIBPQ_ROUTING_ENV_NAMES):
        return False
    try:
        parsed = make_url(value)
        if parsed.drivername != "postgresql+psycopg" or parsed.query:
            return False
        host = parsed.host
    except Exception:
        return False
    if host is None:
        return False
    normalized = host.rstrip(".").lower()
    if normalized == "localhost":
        return True
    try:
        return ip_address(normalized).is_loopback
    except ValueError:
        return False


def _new_repository(database_url: str) -> PaperShadowReadinessRepository:
    return PaperShadowReadinessRepository(database_url)


def _dispose_repository(repository: PaperShadowReadinessRepository) -> None:
    try:
        repository.dispose()
    except Exception:
        pass


def _database_reachability_check(
    database_url: str | None,
) -> tuple[CheckResult, PaperShadowReadinessRepository | None]:
    if database_url is None:
        return CheckResult("database_reachability", "FAIL", "DATABASE_URL_MISSING"), None
    if not _database_url_is_local_postgresql(database_url):
        return CheckResult("database_reachability", "FAIL", "DATABASE_URL_NOT_LOCAL"), None

    repository: PaperShadowReadinessRepository | None = None
    try:
        repository = _new_repository(database_url)
        with repository.engine.connect() as connection:
            value = connection.exec_driver_sql("SELECT 1").scalar_one()
        if value != 1:
            raise RuntimeError
    except Exception:
        if repository is not None:
            _dispose_repository(repository)
        return CheckResult("database_reachability", "FAIL", "DATABASE_UNREACHABLE"), None
    return CheckResult("database_reachability", "PASS", "DATABASE_REACHABLE"), repository


def _git_metadata() -> tuple[str | None, bool]:
    sha_result = _run_command(("git", "rev-parse", "--verify", "HEAD"))
    status_result = _run_command(("git", "status", "--porcelain=v1", "--untracked-files=all"))
    if (
        sha_result is None
        or sha_result.returncode != 0
        or status_result is None
        or status_result.returncode != 0
    ):
        return None, True
    git_sha = sha_result.stdout.strip()
    if GIT_SHA_PATTERN.fullmatch(git_sha) is None:
        return None, True
    return git_sha, bool(status_result.stdout)


def _mock_readiness_check(
    repository: PaperShadowReadinessRepository | None, git_sha: str | None
) -> MockProof:
    if repository is None or git_sha is None:
        return MockProof(
            check=CheckResult("mock_readiness", "FAIL", "MOCK_PROOF_NOT_RUN"),
            outcome="NOT_PROVEN",
        )
    try:
        workflow = PaperShadowReadinessWorkflow(
            adapter=DeterministicMockPaperBrokerAdapter(),
            store=repository,
            phase12_code_version_git_sha=git_sha,
        )
        request = PaperShadowReadinessCreateRequest(
            readiness_idempotency_key=f"phase12-preflight-mock-proof-{git_sha}"
        )
        artifact = workflow.create_readiness(request)
        persisted = repository.get_readiness(artifact.readiness_assessment_id)
        if artifact.outcome is not ReadinessOutcome.MOCK_PROOF_COMPLETE or persisted != artifact:
            raise RuntimeError
    except Exception:
        return MockProof(
            check=CheckResult("mock_readiness", "FAIL", "MOCK_PROOF_FAILED"),
            outcome="NOT_PROVEN",
        )
    return MockProof(
        check=CheckResult("mock_readiness", "PASS", "MOCK_PROOF_COMPLETE"),
        outcome=ReadinessOutcome.MOCK_PROOF_COMPLETE.value,
        readiness_assessment_id=str(artifact.readiness_assessment_id),
        artifact_sha256=artifact.artifact_sha256,
    )


def _rendered_utc(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError
    return value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _run_preflight() -> tuple[dict[str, object], int]:
    checks: list[CheckResult] = []
    checks.append(_python_version_check())
    checks.append(_node_version_check())
    checks.append(
        _command_check(
            name="docker_compose_config",
            command=("docker", "compose", "config", "--quiet"),
            pass_reason="COMPOSE_CONFIG_VALID",
            fail_reason="COMPOSE_CONFIG_FAILED",
        )
    )
    checks.append(
        _command_check(
            name="phase26_static_verification",
            command=(
                sys.executable,
                str(ROOT / "scripts" / "verify_phase1.py"),
                "--static-only",
                "--phase",
                "26",
            ),
            pass_reason="PHASE_26_STATIC_VERIFICATION_PASSED",
            fail_reason="PHASE_26_STATIC_VERIFICATION_FAILED",
        )
    )
    credential_pair, credential_check = _credential_pair_check()
    checks.append(credential_check)

    database_url = os.environ.get(DATABASE_URL_ENV_NAME)
    database_check, repository = _database_reachability_check(database_url)
    checks.append(database_check)
    git_sha, dirty_tree = _git_metadata()
    try:
        mock_proof = _mock_readiness_check(repository, git_sha)
    finally:
        if repository is not None:
            _dispose_repository(repository)
    checks.append(mock_proof.check)

    if tuple(check.name for check in checks) != CHECK_ORDER:
        raise RuntimeError
    overall_status = "FAIL" if any(check.status == "FAIL" for check in checks) else "PASS"
    body: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": _rendered_utc(_utc_now()),
        "git_sha": git_sha if git_sha is not None else "UNAVAILABLE",
        "dirty_tree": dirty_tree,
        "execution_mode": "paper",
        "simulated_paper_only": True,
        "no_personalized_investment_advice": True,
        "config_sha256": CONFIG_SHA256,
        "random_seed": None,
        "trial_count": None,
        "overall_status": overall_status,
        "credential_pair": credential_pair,
        "mock_readiness": mock_proof.outcome,
        "mock_readiness_assessment_id": mock_proof.readiness_assessment_id,
        "mock_readiness_artifact_sha256": mock_proof.artifact_sha256,
        "checks": [check.as_report_value() for check in checks],
    }
    report_sha256 = hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    return {**body, "report_sha256": report_sha256}, 0 if overall_status == "PASS" else 1


def _atomic_write(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    try:
        arguments = _parser().parse_args(argv)
        report, exit_code = _run_preflight()
        rendered = canonical_json_bytes(report) + b"\n"
        if arguments.output is not None:
            _atomic_write(Path(arguments.output), rendered)
        sys.stdout.buffer.write(rendered)
        sys.stdout.buffer.flush()
        return exit_code
    except Exception:
        print(FAILURE_MESSAGE, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
