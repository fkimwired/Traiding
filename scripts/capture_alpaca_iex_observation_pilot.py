"""Run one deterministic mock or explicitly confirmed external Phase 28 observation."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import NoReturn

from fable5_paper.phase28.adapters import DeterministicMockObservationAdapter
from fable5_paper.phase28.alpaca import build_alpaca_iex_observation_only_adapter
from fable5_paper.phase28.canonical import PHASE28_EXACT_USE_REVIEW_EXPIRES_AT_UTC
from fable5_paper.phase28.settings import Phase28PaperCredentialSettings
from fable5_paper.phase28.workflow import Phase28ObservationWorkflow

FAILURE_MESSAGE = "Phase 28 observation-only pilot failed."
EXACT_USE_ATTESTATION = (
    "I confirm the 2026-07-24 first-party review still matches personal/noncommercial, "
    "transient in-process observation only, with no raw persistence, display, or redistribution."
)
_MOCK_TIME = datetime(2024, 1, 2, 15, 0, tzinfo=UTC) + timedelta(seconds=1)


class PilotInvocationError(ValueError):
    """A sanitized invocation failure."""


class _SanitizedArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        del message
        raise PilotInvocationError


def _parser() -> argparse.ArgumentParser:
    parser = _SanitizedArgumentParser(
        description=(
            "Produce sanitized PAPER ONLY / NO ADVICE candidate-observation evidence. "
            "IEX is partial-market data. This command has no execution surface."
        )
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--deterministic-mock", action="store_true")
    mode.add_argument(
        "--confirm-credentialed-paper-only-external-observation",
        action="store_true",
    )
    parser.add_argument(
        "--confirm-2026-07-24-exact-use-review",
        action="store_true",
        help=EXACT_USE_ATTESTATION,
    )
    return parser


def _required_environment(name: str) -> str:
    value = os.environ.get(name)
    if value is None or not value.strip():
        raise PilotInvocationError
    return value


def _system_utc_now() -> datetime:
    return datetime.now(UTC)


def _capture(
    arguments: argparse.Namespace,
    *,
    clock: Callable[[], datetime] = _system_utc_now,
) -> dict[str, object]:
    code_sha = _required_environment("FABLE5_CODE_VERSION_GIT_SHA")
    if arguments.deterministic_mock:
        if arguments.confirm_2026_07_24_exact_use_review:
            raise PilotInvocationError
        workflow = Phase28ObservationWorkflow(
            adapter=DeterministicMockObservationAdapter(),
            code_version_git_sha=code_sha,
            clock=lambda: _MOCK_TIME,
        )
    else:
        if (
            arguments.confirm_credentialed_paper_only_external_observation is not True
            or arguments.confirm_2026_07_24_exact_use_review is not True
        ):
            raise PilotInvocationError
        now = clock()
        if (
            now.tzinfo is None
            or now.utcoffset() is None
            or now.astimezone(UTC) >= PHASE28_EXACT_USE_REVIEW_EXPIRES_AT_UTC
        ):
            raise PilotInvocationError
        # The complete pair gate runs before adapter or socket construction.
        adapter = build_alpaca_iex_observation_only_adapter(
            Phase28PaperCredentialSettings(),
            exact_use_review_confirmed=True,
            clock=clock,
        )
        workflow = Phase28ObservationWorkflow(
            adapter=adapter,
            code_version_git_sha=code_sha,
            clock=clock,
        )
    return workflow.run().model_dump(mode="json")


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
