"""Verify one canonical Phase 16 source-plan artifact completely offline."""

from __future__ import annotations

import argparse
import hmac
import json
import stat
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any, NoReturn

MAX_PLAN_BYTES = 512 * 1024
FAILURE_MESSAGE = "Family A point-in-time source-plan verification failed.\n"
_DENIED_AUDIT_EVENTS = frozenset({"os.system", "subprocess.Popen"})
_FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "fastapi",
    "fable5_api",
    "fable5_jobs",
    "fable5_paper",
    "httpx",
    "psycopg",
    "redis",
    "requests",
    "rq",
    "sqlalchemy",
    "sqlite3",
    "urllib.request",
    "urllib3",
    "uvicorn",
)


class _InvalidPlan(Exception):
    pass


class _OfflineBoundaryViolation(Exception):
    pass


class _SanitizedArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        del message
        raise _InvalidPlan


class _SingleValueAction(argparse.Action):
    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: object,
        option_string: str | None = None,
    ) -> None:
        del parser, option_string
        if not isinstance(values, str) or getattr(namespace, self.dest, None) is not None:
            raise _InvalidPlan
        setattr(namespace, self.dest, values)


def _offline_audit_hook(event: str, args: tuple[object, ...]) -> None:
    del args
    if event.startswith("socket.") or event in _DENIED_AUDIT_EVENTS:
        raise _OfflineBoundaryViolation


def _install_offline_boundary() -> None:
    sys.addaudithook(_offline_audit_hook)


def _prove_socket_construction_is_denied() -> None:
    import socket

    candidate: socket.socket | None = None
    try:
        candidate = socket.socket()
    except _OfflineBoundaryViolation:
        return
    finally:
        if candidate is not None:
            candidate.close()
    raise _InvalidPlan


def _parser() -> argparse.ArgumentParser:
    parser = _SanitizedArgumentParser(
        description="Verify one deterministic Phase 16 Family A source plan offline.",
        allow_abbrev=False,
    )
    parser.add_argument("--plan", action=_SingleValueAction, required=True, metavar="PATH")
    return parser


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _InvalidPlan
        result[key] = value
    return result


def _reject_float(value: str) -> NoReturn:
    del value
    raise _InvalidPlan


def _read_plan(path_text: str) -> bytes:
    path = Path(path_text)
    try:
        metadata = path.lstat()
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_size <= 0
            or metadata.st_size > MAX_PLAN_BYTES
        ):
            raise _InvalidPlan
        raw = path.read_bytes()
    except _InvalidPlan:
        raise
    except (OSError, OverflowError, ValueError):
        raise _InvalidPlan from None
    if len(raw) != metadata.st_size or raw.startswith(b"\xef\xbb\xbf"):
        raise _InvalidPlan
    try:
        decoded = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_float=_reject_float,
            parse_constant=_reject_float,
        )
    except _InvalidPlan:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError):
        raise _InvalidPlan from None
    if not isinstance(decoded, dict):
        raise _InvalidPlan
    return raw


def _matches_prefix(module_name: str, prefix: str) -> bool:
    return module_name == prefix or module_name.startswith(f"{prefix}.")


def _load_contract() -> tuple[Any, Any]:
    before = frozenset(sys.modules)
    contracts = __import__(
        "fable5_data.phase16.contracts", fromlist=["FamilyAPointInTimeSourcePlan"]
    )
    plan = __import__("fable5_data.phase16.plan", fromlist=["canonical_source_plan_bytes"])
    newly_imported = frozenset(sys.modules).difference(before)
    if any(
        _matches_prefix(module_name, prefix)
        for module_name in newly_imported
        for prefix in _FORBIDDEN_IMPORT_PREFIXES
    ):
        raise _InvalidPlan
    model = getattr(contracts, "FamilyAPointInTimeSourcePlan", None)
    canonical_bytes = getattr(plan, "canonical_source_plan_bytes", None)
    if model is None or canonical_bytes is None:
        raise _InvalidPlan
    return model, canonical_bytes


def _verify(path_text: str) -> dict[str, str]:
    raw = _read_plan(path_text)
    model, canonical_bytes = _load_contract()
    try:
        validated = model.model_validate_json(raw, strict=True)
    except Exception:
        raise _InvalidPlan from None
    if not hmac.compare_digest(raw, canonical_bytes()):
        raise _InvalidPlan
    return {
        "artifact_id": str(validated.artifact_id),
        "artifact_sha256": validated.artifact_sha256,
        "network": "disabled",
        "outcome": validated.outcome.value,
        "schema_version": validated.schema_version,
        "status": "valid",
    }


def _failure_exit() -> int:
    try:
        sys.stderr.buffer.write(FAILURE_MESSAGE.encode("ascii"))
        sys.stderr.buffer.flush()
    except BaseException:
        pass
    return 2


def main(argv: Sequence[str] | None = None) -> int:
    try:
        _install_offline_boundary()
        _prove_socket_construction_is_denied()
        arguments = _parser().parse_args(argv)
        result = _verify(arguments.plan)
    except SystemExit as exc:
        if exc.code in (None, 0):
            raise
        return _failure_exit()
    except BaseException:
        return _failure_exit()
    try:
        sys.stdout.write(json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n")
    except BaseException:
        return _failure_exit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
