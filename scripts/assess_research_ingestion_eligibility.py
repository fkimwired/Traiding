"""Explicit one-shot Phase 14 offline eligibility assessment."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import NoReturn
from uuid import UUID

from fable5_data.phase13.repository import PointInTimeQualificationRepository
from fable5_data.phase14.contracts import (
    ResearchIngestionEligibilityCreateRequest,
    validate_code_git_sha,
)
from fable5_data.phase14.repository import ResearchIngestionEligibilityRepository
from fable5_data.phase14.workflow import ResearchIngestionEligibilityWorkflow

FAILURE_MESSAGE = "Research-ingestion eligibility assessment failed."


class AssessmentInvocationError(ValueError):
    """An invocation failure with no user-controlled rendering."""


class _SanitizedArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        del message
        raise AssessmentInvocationError


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
            raise AssessmentInvocationError
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
            raise AssessmentInvocationError
        setattr(namespace, self.dest, True)


def _parser() -> argparse.ArgumentParser:
    parser = _SanitizedArgumentParser(
        description=(
            "Assess one immutable Phase 13 artifact under the offline Phase 14 prerequisite "
            "policy. This command does not call a provider, ingest data, run research, promote a "
            "strategy, or submit an order."
        )
    )
    parser.add_argument(
        "--idempotency-key",
        action=_SingleValueAction,
        required=True,
    )
    parser.add_argument(
        "--qualification-id",
        action=_SingleValueAction,
        type=UUID,
        required=True,
    )
    parser.add_argument(
        "--confirm-research-eligibility-only",
        action=_SingleConfirmationAction,
        nargs=0,
        default=False,
        required=True,
    )
    return parser


def _required_environment(name: str) -> str:
    value = os.environ.get(name)
    if value is None or not value.strip():
        raise AssessmentInvocationError
    return value


def _assess(arguments: argparse.Namespace) -> dict[str, object]:
    if arguments.confirm_research_eligibility_only is not True:
        raise AssessmentInvocationError

    code_git_sha = validate_code_git_sha(_required_environment("FABLE5_CODE_VERSION_GIT_SHA"))
    dsn = _required_environment("FABLE5_DATABASE_URL")
    request = ResearchIngestionEligibilityCreateRequest(
        assessment_idempotency_key=arguments.idempotency_key,
        qualification_id=arguments.qualification_id,
    )
    qualification_repository = PointInTimeQualificationRepository(dsn)
    repository = ResearchIngestionEligibilityRepository(dsn)
    try:
        workflow = ResearchIngestionEligibilityWorkflow(
            qualification_source=qualification_repository,
            store=repository,
            phase14_code_version_git_sha=code_git_sha,
        )
        artifact = workflow.create_assessment(request)
        return artifact.model_dump(mode="json")
    finally:
        repository.dispose()
        qualification_repository.dispose()


def main(argv: list[str] | None = None) -> int:
    try:
        arguments = _parser().parse_args(argv)
        rendered = json.dumps(
            _assess(arguments),
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
