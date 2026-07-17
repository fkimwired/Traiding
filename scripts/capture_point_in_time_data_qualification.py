"""Explicit one-shot capture of sanitized Phase 13 external qualification evidence."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import NoReturn

from fable5_data.phase13.contracts import (
    PointInTimeQualificationCreateRequest,
    validate_code_git_sha,
)
from fable5_data.phase13.repository import PointInTimeQualificationRepository
from fable5_data.phase13.settings import TiingoQualificationSettings
from fable5_data.phase13.tiingo import build_tiingo_candidate_qualification_adapter
from fable5_data.phase13.workflow import PointInTimeQualificationWorkflow

FAILURE_MESSAGE = "Point-in-time data qualification capture failed."


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
            "Capture one read-only provider-qualification sample. This command does not create "
            "a research dataset, run a strategy, or submit an order."
        )
    )
    parser.add_argument(
        "--idempotency-key",
        action=_SingleValueAction,
        required=True,
    )
    parser.add_argument(
        "--confirm-read-only-qualification",
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
    if arguments.confirm_read_only_qualification is not True:
        raise CaptureInvocationError

    # The complete credential/rights gate must finish before transport or database construction.
    adapter = build_tiingo_candidate_qualification_adapter(TiingoQualificationSettings())
    code_git_sha = validate_code_git_sha(_required_environment("FABLE5_CODE_VERSION_GIT_SHA"))
    dsn = _required_environment("FABLE5_DATABASE_URL")
    request = PointInTimeQualificationCreateRequest(
        qualification_idempotency_key=arguments.idempotency_key
    )
    repository = PointInTimeQualificationRepository(dsn)
    try:
        workflow = PointInTimeQualificationWorkflow(
            adapter=adapter,
            store=repository,
            phase13_code_version_git_sha=code_git_sha,
        )
        artifact = workflow.create_qualification(request)
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
