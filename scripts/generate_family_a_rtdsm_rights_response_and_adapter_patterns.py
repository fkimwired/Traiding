"""Generate a deterministic Phase 25 rights-response evaluation package to stdout."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import NoReturn

FAILURE_MESSAGE = "Phase 25 rights-response package generation failed.\n"
MAX_INTAKE_BYTES = 128 * 1024
_DENIED_AUDIT_EVENTS = frozenset({"os.system", "subprocess.Popen"})
_FORBIDDEN_KEY_PARTS = (
    "body",
    "payload",
    "credential",
    "password",
    "secret",
    "cookie",
    "crumb",
    "raw_response",
    "raw_account",
    "raw_entitlement",
)
_SECRET_TEXT = re.compile(
    r"(?i)(?:api[_-]?key|authorization|bearer|password|secret|cookie|crumb|token)\s*[:=]"
)


class _InvalidInvocation(Exception):
    pass


class _OfflineBoundaryViolation(Exception):
    pass


class _SanitizedArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        del message
        raise _InvalidInvocation


class _SingleConfirmationAction(argparse.Action):
    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: object,
        option_string: str | None = None,
    ) -> None:
        del parser, values, option_string
        if getattr(namespace, self.dest, False) is True:
            raise _InvalidInvocation
        setattr(namespace, self.dest, True)


def _offline_audit_hook(event: str, args: tuple[object, ...]) -> None:
    del args
    if event.startswith("socket.") or event in _DENIED_AUDIT_EVENTS:
        raise _OfflineBoundaryViolation


def _prove_offline_boundary() -> None:
    import socket
    import subprocess

    candidate: socket.socket | None = None
    try:
        candidate = socket.socket()
    except _OfflineBoundaryViolation:
        pass
    else:
        candidate.close()
        raise _InvalidInvocation
    process: subprocess.Popen[bytes] | None = None
    try:
        process = subprocess.Popen(
            [sys.executable, "-c", "pass"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except _OfflineBoundaryViolation:
        return
    finally:
        if process is not None:
            process.kill()
            process.wait()
    raise _InvalidInvocation


def _parser() -> argparse.ArgumentParser:
    parser = _SanitizedArgumentParser(
        description=(
            "Generate a deterministic Phase 25 metadata-only rights-response evaluation and "
            "adapter-pattern package. No provider body, credential, observation, or network access."
        ),
        allow_abbrev=False,
    )
    parser.add_argument(
        "--confirm-evidence-intake-and-patterns-only",
        action=_SingleConfirmationAction,
        nargs=0,
        default=False,
        required=True,
    )
    parser.add_argument("--response-metadata", type=Path)
    return parser


def _reject_sensitive_content(value: object) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = str(key).casefold()
            if any(part in normalized for part in _FORBIDDEN_KEY_PARTS):
                raise _InvalidInvocation
            _reject_sensitive_content(item)
    elif isinstance(value, list):
        for item in value:
            _reject_sensitive_content(item)
    elif isinstance(value, str) and _SECRET_TEXT.search(value):
        raise _InvalidInvocation


def _read_intake(path: Path) -> object:
    size = path.stat().st_size
    if size <= 0 or size > MAX_INTAKE_BYTES:
        raise _InvalidInvocation
    raw = path.read_bytes()
    if len(raw) != size or b"\x00" in raw:
        raise _InvalidInvocation
    parsed = json.loads(raw)
    _reject_sensitive_content(parsed)
    return parsed


def _failure_exit() -> int:
    try:
        sys.stderr.buffer.write(FAILURE_MESSAGE.encode("ascii"))
        sys.stderr.buffer.flush()
    except BaseException:
        pass
    return 2


def main(argv: Sequence[str] | None = None) -> int:
    try:
        sys.addaudithook(_offline_audit_hook)
        _prove_offline_boundary()
        arguments = _parser().parse_args(argv)
        if arguments.confirm_evidence_intake_and_patterns_only is not True:
            raise _InvalidInvocation
        from fable5_data.phase25.contracts import RightsResponseIntake
        from fable5_data.phase25.package import canonical_phase25_package_bytes

        intake = None
        if arguments.response_metadata is not None:
            intake = RightsResponseIntake.model_validate(_read_intake(arguments.response_metadata))
        rendered = canonical_phase25_package_bytes(intake)
    except SystemExit as exc:
        if exc.code in (None, 0):
            raise
        return _failure_exit()
    except BaseException:
        return _failure_exit()
    try:
        sys.stdout.buffer.write(rendered)
        sys.stdout.buffer.flush()
    except BaseException:
        return _failure_exit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
