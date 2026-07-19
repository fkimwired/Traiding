"""Generate the sole canonical Phase 17 candidate-product inventory."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from typing import NoReturn

FAILURE_MESSAGE = "Family A candidate-product inventory generation failed.\n"
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
    raise _InvalidInvocation


def _parser() -> argparse.ArgumentParser:
    parser = _SanitizedArgumentParser(
        description=(
            "Generate deterministic Phase 17 Family A candidate-product metadata. This performs "
            "no provider request, account check, entitlement check, data capture, or selection."
        ),
        allow_abbrev=False,
    )
    parser.add_argument(
        "--confirm-metadata-only",
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
        _install_offline_boundary()
        _prove_socket_construction_is_denied()
        arguments = _parser().parse_args(argv)
        if arguments.confirm_metadata_only is not True:
            raise _InvalidInvocation
        from fable5_data.phase17.inventory import canonical_candidate_product_inventory_bytes

        rendered = canonical_candidate_product_inventory_bytes()
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
