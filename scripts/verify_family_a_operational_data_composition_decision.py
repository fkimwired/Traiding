"""Bounded offline verifier for the Phase 26 composition decision."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import NoReturn

FAILURE_MESSAGE = "Phase 26 operational data-composition verification failed.\n"
MAX_ARTIFACT_BYTES = 256 * 1024
_DENIED_AUDIT_EVENTS = frozenset({"os.system", "subprocess.Popen"})


class _InvalidInvocation(Exception):
    pass


class _OfflineBoundaryViolation(Exception):
    pass


class _Parser(argparse.ArgumentParser):
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
    parser = _Parser(description="Verify one canonical Phase 26 decision.", allow_abbrev=False)
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
        path = _parser().parse_args(argv).artifact
        size = path.stat().st_size
        if size <= 0 or size > MAX_ARTIFACT_BYTES or not path.is_file() or path.is_symlink():
            raise _InvalidInvocation
        raw = path.read_bytes()
        if len(raw) != size or b"\x00" in raw:
            raise _InvalidInvocation
        from fable5_data.phase26 import canonical as c
        from fable5_data.phase26.composition import canonical_phase26_decision_bytes
        from fable5_data.phase26.contracts import Phase26Decision

        artifact = Phase26Decision.model_validate_json(raw, strict=True)
        if raw != canonical_phase26_decision_bytes():
            raise _InvalidInvocation
        receipt = (
            c.canonical_json_bytes(
                {
                    "acquisition_authorized": artifact.acquisition_authorized,
                    "artifact_id": artifact.artifact_id,
                    "artifact_sha256": artifact.artifact_sha256,
                    "composition_id": artifact.capability_product_composition_id,
                    "decision_state": artifact.decision_state,
                    "outcome": artifact.outcome,
                    "selected_product_count": len(artifact.selected_products),
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
