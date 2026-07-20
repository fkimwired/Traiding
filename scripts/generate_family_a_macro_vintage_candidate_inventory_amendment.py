"""Generate the canonical Phase 22 macro-vintage candidate amendment."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from typing import NoReturn

FAILURE_MESSAGE = "Family A macro-vintage candidate-inventory amendment generation failed.\n"
_DENIED_AUDIT_EVENTS = frozenset({"os.system", "subprocess.Popen"})


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
            "Generate the deterministic Phase 22 metadata-only candidate amendment without "
            "selecting, ranking, requesting, capturing, persisting, researching, executing, "
            "or ordering."
        ),
        allow_abbrev=False,
    )
    parser.add_argument(
        "--confirm-candidate-inventory-amendment-only",
        action=_SingleConfirmationAction,
        nargs=0,
        default=False,
        required=True,
    )
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
        if arguments.confirm_candidate_inventory_amendment_only is not True:
            raise _InvalidInvocation
        from fable5_data.phase22.inventory_amendment import (
            canonical_macro_vintage_candidate_inventory_amendment_bytes,
        )

        rendered = canonical_macro_vintage_candidate_inventory_amendment_bytes()
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
