"""Offline verifier for one portable Phase 11 local-simulation evidence bundle."""

from __future__ import annotations

import argparse
import hmac
import json
import os
import re
import stat
import sys
from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path
from typing import Any, NoReturn

MAX_BUNDLE_BYTES = 1024 * 1024
MAX_NUMERIC_COEFFICIENT_DIGITS = 256
MAX_NUMERIC_ABS_EXPONENT = 1_000
FAILURE_MESSAGE = "Local simulation evidence verification failed.\n"
_LOWER_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_NUMERIC_TEXT = re.compile(r"[+-]?(?:(?:\d+(?:\.\d*)?)|(?:\.\d+))(?:[eE](?P<exponent>[+-]?\d+))?\Z")
_DENIED_AUDIT_EVENTS = frozenset({"os.system", "subprocess.Popen"})
_FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "alpaca",
    "boto3",
    "botocore",
    "ccxt",
    "fastapi",
    "fable5_api",
    "fable5_jobs",
    "fable5_paper.repository",
    "fable5_paper.workflow",
    "ftplib",
    "http",
    "httpx",
    "ibapi",
    "psycopg",
    "redis",
    "requests",
    "rq",
    "smtplib",
    "socketserver",
    "sqlalchemy",
    "sqlite3",
    "starlette",
    "urllib.request",
    "urllib3",
    "uvicorn",
    "yfinance",
)


class _InvalidEvidence(Exception):
    """Internal sentinel whose message is never exposed."""


class _OfflineBoundaryViolation(Exception):
    """Raised by the process-wide audit hook before a denied operation starts."""


class _SanitizedArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        del message
        raise _InvalidEvidence


class _SingleValueAction(argparse.Action):
    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: str | Sequence[Any] | None,
        option_string: str | None = None,
    ) -> None:
        del parser, option_string
        if not isinstance(values, str) or getattr(namespace, self.dest, None) is not None:
            raise _InvalidEvidence
        setattr(namespace, self.dest, values)


def _offline_audit_hook(event: str, args: tuple[object, ...]) -> None:
    del args
    if event.startswith("socket.") or event in _DENIED_AUDIT_EVENTS:
        raise _OfflineBoundaryViolation


def _install_offline_boundary() -> None:
    # This precedes every application import and every bundle-file operation.
    sys.addaudithook(_offline_audit_hook)


def _prove_socket_construction_is_denied() -> None:
    # Importing the standard-library module is harmless. Constructing a socket must
    # synchronously trip the audit hook before any operating-system handle exists.
    import socket

    candidate: socket.socket | None = None
    try:
        candidate = socket.socket()
    except _OfflineBoundaryViolation:
        return
    finally:
        if candidate is not None:
            candidate.close()
    raise _InvalidEvidence


def _parser() -> argparse.ArgumentParser:
    parser = _SanitizedArgumentParser(
        description="Verify one deterministic local-simulation evidence bundle offline."
    )
    parser.add_argument(
        "--bundle",
        action=_SingleValueAction,
        required=True,
        metavar="PATH",
    )
    parser.add_argument(
        "--expected-bundle-sha256",
        action=_SingleValueAction,
        required=True,
        metavar="LOWERHEX64",
    )
    return parser


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _InvalidEvidence
        result[key] = value
    return result


def _reject_nonstandard_constant(value: str) -> NoReturn:
    del value
    raise _InvalidEvidence


def _bounded_decimal(value: str) -> Decimal:
    match = _NUMERIC_TEXT.fullmatch(value)
    if match is None:
        raise _InvalidEvidence
    mantissa = value.split("e", 1)[0].split("E", 1)[0].lstrip("+-")
    coefficient_digits = mantissa.replace(".", "")
    if len(coefficient_digits) > MAX_NUMERIC_COEFFICIENT_DIGITS:
        raise _InvalidEvidence
    exponent_text = match.group("exponent") or "0"
    unsigned_exponent = exponent_text.lstrip("+-")
    if len(unsigned_exponent) > len(str(MAX_NUMERIC_ABS_EXPONENT)):
        raise _InvalidEvidence
    exponent = int(exponent_text)
    fraction_digits = len(mantissa.partition(".")[2])
    significant_digits = coefficient_digits.lstrip("0")
    effective_exponent = exponent - fraction_digits
    adjusted_exponent = effective_exponent + max(len(significant_digits) - 1, 0)
    if (
        abs(effective_exponent) > MAX_NUMERIC_ABS_EXPONENT
        or abs(adjusted_exponent) > MAX_NUMERIC_ABS_EXPONENT
    ):
        raise _InvalidEvidence
    try:
        return Decimal(value)
    except (ArithmeticError, ValueError):
        raise _InvalidEvidence from None


def _guard_numeric_strings(document: object) -> None:
    pending = [document]
    while pending:
        value = pending.pop()
        if isinstance(value, dict):
            pending.extend(value.values())
        elif isinstance(value, list):
            pending.extend(value)
        elif isinstance(value, str) and _NUMERIC_TEXT.fullmatch(value) is not None:
            _bounded_decimal(value)


def _read_bundle(path_text: str) -> tuple[bytes, dict[str, object]]:
    path = Path(path_text)
    try:
        path_metadata = path.lstat()
        if not stat.S_ISREG(path_metadata.st_mode):
            raise _InvalidEvidence
        if path_metadata.st_size <= 0 or path_metadata.st_size > MAX_BUNDLE_BYTES:
            raise _InvalidEvidence
        with path.open("rb") as handle:
            opened_metadata = os.fstat(handle.fileno())
            if not stat.S_ISREG(opened_metadata.st_mode):
                raise _InvalidEvidence
            if (
                opened_metadata.st_size <= 0
                or opened_metadata.st_size > MAX_BUNDLE_BYTES
                or (opened_metadata.st_dev, opened_metadata.st_ino)
                != (path_metadata.st_dev, path_metadata.st_ino)
            ):
                raise _InvalidEvidence
            raw = handle.read(MAX_BUNDLE_BYTES + 1)
        if len(raw) != opened_metadata.st_size or len(raw) > MAX_BUNDLE_BYTES:
            raise _InvalidEvidence
    except _InvalidEvidence:
        raise
    except (OSError, OverflowError, ValueError):
        raise _InvalidEvidence from None

    if raw.startswith(b"\xef\xbb\xbf"):
        raise _InvalidEvidence
    try:
        text = raw.decode("utf-8", errors="strict")
        decoded = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_float=_bounded_decimal,
            parse_int=_bounded_decimal,
            parse_constant=_reject_nonstandard_constant,
        )
        _guard_numeric_strings(decoded)
    except _InvalidEvidence:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError):
        raise _InvalidEvidence from None
    if not isinstance(decoded, dict):
        raise _InvalidEvidence
    return raw, decoded


def _require_complete_schema(decoded: object, validated: object) -> None:
    model_fields = getattr(type(validated), "model_fields", None)
    if isinstance(model_fields, dict):
        if not isinstance(decoded, dict) or set(decoded) != set(model_fields):
            raise _InvalidEvidence
        for field_name in model_fields:
            _require_complete_schema(decoded[field_name], getattr(validated, field_name))
        return
    if isinstance(validated, (tuple, list)):
        if not isinstance(decoded, list) or len(decoded) != len(validated):
            raise _InvalidEvidence
        for decoded_item, validated_item in zip(decoded, validated, strict=True):
            _require_complete_schema(decoded_item, validated_item)
        return
    if isinstance(validated, dict):
        if not isinstance(decoded, dict) or set(decoded) != set(validated):
            raise _InvalidEvidence
        for key, value in validated.items():
            _require_complete_schema(decoded[key], value)


def _matches_prefix(module_name: str, prefix: str) -> bool:
    return module_name == prefix or module_name.startswith(f"{prefix}.")


def _load_bundle_type() -> Any:
    before = frozenset(sys.modules)
    module = __import__(
        "fable5_paper.evidence",
        fromlist=["LocalSimulationEvidenceBundle"],
    )
    newly_imported = frozenset(sys.modules).difference(before)
    if any(
        _matches_prefix(module_name, prefix)
        for module_name in newly_imported
        for prefix in _FORBIDDEN_IMPORT_PREFIXES
    ):
        raise _InvalidEvidence
    bundle_type = getattr(module, "LocalSimulationEvidenceBundle", None)
    if bundle_type is None:
        raise _InvalidEvidence
    return bundle_type


def _verify(path_text: str, expected_bundle_sha256: str) -> dict[str, str]:
    if _LOWER_SHA256.fullmatch(expected_bundle_sha256) is None:
        raise _InvalidEvidence
    raw, decoded = _read_bundle(path_text)
    bundle_type = _load_bundle_type()
    bundle = bundle_type.model_validate_json(raw, strict=True)
    _require_complete_schema(decoded, bundle)
    if not hmac.compare_digest(bundle.bundle_sha256, expected_bundle_sha256):
        raise _InvalidEvidence
    return {
        "bundle_sha256": bundle.bundle_sha256,
        "network": "disabled",
        "outcome": bundle.simulation.outcome.value,
        "schema": bundle.bundle_schema_version,
        "simulation_artifact_sha256": bundle.simulation_artifact_sha256,
        "simulation_run_id": str(bundle.simulation_run_id),
        "status": "valid",
    }


def _failure_exit() -> int:
    try:
        sys.stderr.write(FAILURE_MESSAGE)
    except BaseException:
        pass
    return 2


def main(argv: Sequence[str] | None = None) -> int:
    try:
        _install_offline_boundary()
        _prove_socket_construction_is_denied()
        arguments = _parser().parse_args(argv)
        result = _verify(arguments.bundle, arguments.expected_bundle_sha256)
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
