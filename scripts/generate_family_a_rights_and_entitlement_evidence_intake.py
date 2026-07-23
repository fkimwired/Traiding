"""Generate a deterministic Phase 27 rights-and-entitlement evidence package."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import NoReturn

FAILURE_MESSAGE = "Phase 27 rights-and-entitlement evidence generation failed.\n"
MAX_INTAKE_BYTES = 128 * 1024
_DENIED_AUDIT_EVENTS = frozenset({"os.system", "subprocess.Popen"})
_FORBIDDEN_KEY_PARTS = (
    "agreement_text",
    "body",
    "cancel",
    "candidate_screen",
    "header",
    "payload",
    "credential",
    "data_file",
    "dataset",
    "execution",
    "fetch_url",
    "liquidat",
    "live_path",
    "password",
    "personal_identifier",
    "provider_url",
    "raw_agreement",
    "secret",
    "schema_sample",
    "cookie",
    "crumb",
    "performance",
    "research_output",
    "risk_promotion",
    "strategy",
    "token",
    "raw_response",
    "raw_account",
    "raw_entitlement",
)
_SECRET_TEXT = re.compile(
    r"(?i)\b(?:api[_ -]?key|authorization|bearer|basic|password|secret|cookie|crumb|token)\b"
    r"(?:\s*[:=]|\s+[A-Za-z0-9._~+/=-]{8,})"
)
_OPAQUE_SECRET_TEXT = re.compile(
    r"(?<![A-Z0-9])(?=[A-Z0-9]{20,}(?![A-Z0-9]))(?=[A-Z0-9]*[A-Z])"
    r"(?=[A-Z0-9]*[0-9])[A-Z0-9]+"
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
            "Generate a deterministic Phase 27 metadata-only rights-and-entitlement evidence "
            "package. No provider body, header, account, entitlement, credential, observation, "
            "or network access."
        ),
        allow_abbrev=False,
    )
    parser.add_argument(
        "--confirm-rights-and-entitlement-evidence-intake-only",
        action=_SingleConfirmationAction,
        nargs=0,
        default=False,
        required=True,
    )
    parser.add_argument("--evidence-metadata", type=Path)
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
    elif isinstance(value, str):
        if _SECRET_TEXT.search(value) or _OPAQUE_SECRET_TEXT.search(value):
            raise _InvalidInvocation


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    parsed: dict[str, object] = {}
    for key, value in pairs:
        if key in parsed:
            raise _InvalidInvocation
        parsed[key] = value
    return parsed


def _read_intake(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise _InvalidInvocation
    size = path.stat().st_size
    if size <= 0 or size > MAX_INTAKE_BYTES:
        raise _InvalidInvocation
    raw = path.read_bytes()
    if len(raw) != size or b"\x00" in raw:
        raise _InvalidInvocation
    parsed = json.loads(raw, object_pairs_hook=_unique_object)
    _reject_sensitive_content(parsed)
    return raw


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
        if arguments.confirm_rights_and_entitlement_evidence_intake_only is not True:
            raise _InvalidInvocation
        from fable5_data.phase27.contracts import Phase27EvidenceIntake
        from fable5_data.phase27.package import canonical_phase27_package_bytes

        intake = None
        if arguments.evidence_metadata is not None:
            intake = Phase27EvidenceIntake.model_validate_json(
                _read_intake(arguments.evidence_metadata), strict=True
            )
        rendered = canonical_phase27_package_bytes(intake)
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
