"""Explicit one-shot capture of sanitized external paper shadow-readiness evidence."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import NoReturn

from fable5_paper.phase12.alpaca import build_alpaca_paper_read_only_adapter
from fable5_paper.phase12.contracts import (
    PaperShadowReadinessCreateRequest,
    validate_code_git_sha,
)
from fable5_paper.phase12.repository import PaperShadowReadinessRepository
from fable5_paper.phase12.settings import PaperCredentialSettings
from fable5_paper.phase12.workflow import PaperShadowReadinessWorkflow

FAILURE_MESSAGE = "Paper shadow-readiness capture failed."


class CaptureInvocationError(ValueError):
    """An invocation failure with no user-controlled rendering."""


class _SanitizedArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        del message
        raise CaptureInvocationError


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
            raise CaptureInvocationError
        setattr(namespace, self.dest, values)


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
            raise CaptureInvocationError
        setattr(namespace, self.dest, True)


def _parser() -> argparse.ArgumentParser:
    parser = _SanitizedArgumentParser(
        description=(
            "Capture one PAPER ONLY read-only environment-readiness artifact. "
            "This command cannot submit an order."
        )
    )
    parser.add_argument(
        "--idempotency-key",
        action=_SingleValueAction,
        required=True,
    )
    parser.add_argument(
        "--confirm-paper-only-readiness",
        action=_SingleConfirmationAction,
        nargs=0,
        default=False,
        required=True,
    )
    return parser


def _required_environment(name: str) -> str:
    value = os.environ.get(name)
    if value is None or not value.strip():
        raise CaptureInvocationError
    return value


def _capture(arguments: argparse.Namespace) -> dict[str, object]:
    if arguments.confirm_paper_only_readiness is not True:
        raise CaptureInvocationError

    # This pair gate must complete before adapter, socket, or database construction.
    adapter = build_alpaca_paper_read_only_adapter(PaperCredentialSettings())
    dsn = _required_environment("FABLE5_DATABASE_URL")
    code_git_sha = validate_code_git_sha(_required_environment("FABLE5_CODE_VERSION_GIT_SHA"))
    request = PaperShadowReadinessCreateRequest(readiness_idempotency_key=arguments.idempotency_key)
    repository = PaperShadowReadinessRepository(dsn)
    try:
        workflow = PaperShadowReadinessWorkflow(
            adapter=adapter,
            store=repository,
            phase12_code_version_git_sha=code_git_sha,
        )
        artifact = workflow.create_readiness(request)
        return artifact.model_dump(mode="json")
    finally:
        repository.dispose()


def main(argv: list[str] | None = None) -> int:
    try:
        arguments = _parser().parse_args(argv)
        rendered = json.dumps(
            _capture(arguments),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except Exception:
        print(FAILURE_MESSAGE, file=sys.stderr)
        return 2
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
