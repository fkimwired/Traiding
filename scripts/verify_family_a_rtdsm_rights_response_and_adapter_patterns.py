"""Bounded offline verifier for a canonical Phase 25 package."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import NoReturn

FAILURE_MESSAGE = "Phase 25 rights-response package verification failed.\n"
MAX_ARTIFACT_BYTES = 1024 * 1024
_DENIED_AUDIT_EVENTS = frozenset({"os.system", "subprocess.Popen"})


class _InvalidInvocation(Exception):
    pass


class _OfflineBoundaryViolation(Exception):
    pass


class _SanitizedArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        del message
        raise _InvalidInvocation


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
            "Verify one bounded canonical Phase 25 package without network or subprocesses."
        ),
        allow_abbrev=False,
    )
    parser.add_argument("--artifact", type=Path, required=True)
    return parser


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
        size = arguments.artifact.stat().st_size
        if size <= 0 or size > MAX_ARTIFACT_BYTES:
            raise _InvalidInvocation
        raw = arguments.artifact.read_bytes()
        if len(raw) != size or b"\x00" in raw:
            raise _InvalidInvocation
        from fable5_data.phase25 import canonical as c
        from fable5_data.phase25.contracts import Phase25Package

        artifact = Phase25Package.model_validate_json(raw)
        if c.canonical_json_bytes(artifact) + b"\n" != raw:
            raise _InvalidInvocation
        receipt = (
            c.canonical_json_bytes(
                {
                    "artifact_id": artifact.artifact_id,
                    "artifact_sha256": artifact.artifact_sha256,
                    "determination": artifact.determination,
                    "evidence_snapshot_id": artifact.evidence_snapshot_id,
                    "evidence_snapshot_sha256": artifact.evidence_snapshot_sha256,
                    "outcome": artifact.outcome,
                    "rights_verified": artifact.rights_verified,
                    "source_snapshot_id": artifact.source_snapshot_id,
                    "source_snapshot_sha256": artifact.source_snapshot_sha256,
                    "verified": True,
                }
            )
            + b"\n"
        )
    except SystemExit as exc:
        if exc.code in (None, 0):
            raise
        return _failure_exit()
    except BaseException:
        return _failure_exit()
    try:
        sys.stdout.buffer.write(receipt)
        sys.stdout.buffer.flush()
    except BaseException:
        return _failure_exit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
