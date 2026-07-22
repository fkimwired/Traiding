"""Render one sanitized report from persisted paper shadow-readiness evidence."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
import tempfile
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from enum import StrEnum
from ipaddress import ip_address
from pathlib import Path
from typing import Annotated, Final, Literal, NoReturn, Self
from uuid import UUID

from fable5_paper.phase12.canonical import (
    PHASE12_TRANSPORT_PROFILE_SHA256,
    canonical_json_bytes,
)
from fable5_paper.phase12.contracts import (
    PHASE12_CHECK_ORDER,
    PHASE12_INSPECTION_ORDER,
    PaperShadowReadinessArtifact,
    ReadinessCheckCode,
    ReadinessCheckStatus,
    ReadinessInspectionCode,
    ReadinessOutcome,
    ReadinessSourceKind,
)
from fable5_paper.phase12.repository import PaperShadowReadinessRepository
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)
from sqlalchemy.engine import make_url

FAILURE_MESSAGE: Final = "Paper shadow-readiness report failed."
PROJECTION_FAILURE_MESSAGE: Final = "Paper shadow-readiness report projection failed."
DATABASE_URL_ENV_NAME: Final = "FABLE5_DATABASE_URL"
BOUNDARY_LABEL: Final = "Simulated / Paper Only / No Advice"
MOCK_NOTICE: Final = "MOCK — proves the local contract only, not external readiness."

LIBPQ_ROUTING_ENV_NAMES: Final = (
    "PGHOST",
    "PGHOSTADDR",
    "PGSERVICE",
    "PGSERVICEFILE",
    "PGSYSCONFDIR",
)

_UNSAFE_MARKER_PATTERN: Final = re.compile(
    r"(?:fable5[_-]?alpaca|canary[_-]?(?:key|secret))", re.IGNORECASE
)
_UPPERCASE_TOKEN_PATTERN: Final = re.compile(r"(?<![A-Z0-9])[A-Z0-9]{20,}(?![A-Z0-9])")
_T004_GENERATED_IDEMPOTENCY_KEY_PATTERN: Final = re.compile(r"^phase12-t004-\d{8}T\d{12}Z$")
_RENDERED_AT_UTC_PATTERN: Final = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$"
)

SHA256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
GIT_SHA = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]
REQUEST_ID = Annotated[
    str,
    StringConstraints(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$"),
]


class ReportInvocationError(ValueError):
    """An invocation failure whose user-controlled details must not be rendered."""


class ReportProjectionError(ValueError):
    """A fixed projection failure that never includes source values."""


class _SanitizedArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        del message
        raise ReportInvocationError


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
            raise ReportInvocationError
        setattr(namespace, self.dest, values)


class StrictProjectionModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, revalidate_instances="always", strict=True
    )


class ExpiryState(StrEnum):
    CURRENT = "CURRENT"
    EXPIRED = "EXPIRED"


class ReportCheckProjection(StrictProjectionModel):
    ordinal: int = Field(ge=1, le=len(PHASE12_CHECK_ORDER))
    code: ReadinessCheckCode
    status: ReadinessCheckStatus
    check_sha256: SHA256


class ReportRequestEvidenceProjection(StrictProjectionModel):
    ordinal: int = Field(ge=1, le=len(PHASE12_INSPECTION_ORDER))
    code: ReadinessInspectionCode
    request_id: REQUEST_ID | None
    response_sha256: SHA256 | None

    @field_validator("request_id")
    @classmethod
    def reject_unsafe_request_id(cls, value: str | None) -> str | None:
        if value is not None:
            _assert_safe_text(value)
        return value


class ReadinessReportBody(StrictProjectionModel):
    readiness_assessment_id: UUID
    source_kind: ReadinessSourceKind
    outcome: ReadinessOutcome
    checks: tuple[ReportCheckProjection, ...] = Field(
        min_length=len(PHASE12_CHECK_ORDER), max_length=len(PHASE12_CHECK_ORDER)
    )
    request_evidence: tuple[ReportRequestEvidenceProjection, ...] = Field(
        min_length=len(PHASE12_INSPECTION_ORDER),
        max_length=len(PHASE12_INSPECTION_ORDER),
    )
    phase12_code_version_git_sha: GIT_SHA
    transport_profile_sha256: SHA256
    assessment_started_at_utc: datetime
    assessment_completed_at_utc: datetime
    expires_at_utc: datetime
    rendered_at_utc: datetime
    expiry_state: ExpiryState
    order_submission_authorized: Literal[False]
    strategy_execution_eligible: Literal[False]
    live_path_absent: Literal[True]
    no_personalized_investment_advice: Literal[True]
    no_real_performance_claimed: Literal[True]
    simulated_paper_only: Literal[True]
    boundary_label: Literal["Simulated / Paper Only / No Advice"]
    mock_notice: (
        Literal["MOCK — proves the local contract only, not external readiness."] | None
    ) = None

    @field_validator(
        "order_submission_authorized",
        "strategy_execution_eligible",
        "live_path_absent",
        "no_personalized_investment_advice",
        "no_real_performance_claimed",
        "simulated_paper_only",
        mode="before",
    )
    @classmethod
    def require_boolean_literals(cls, value: object) -> object:
        if type(value) is not bool:
            raise ValueError("report authority fields must be boolean literals")
        return value

    @field_validator(
        "assessment_started_at_utc",
        "assessment_completed_at_utc",
        "expires_at_utc",
        "rendered_at_utc",
    )
    @classmethod
    def normalize_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("report timestamps must be timezone-aware")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_report_body(self) -> Self:
        if self.transport_profile_sha256 != PHASE12_TRANSPORT_PROFILE_SHA256:
            raise ValueError("report transport profile is invalid")
        if (
            tuple(item.ordinal for item in self.checks)
            != tuple(range(1, len(PHASE12_CHECK_ORDER) + 1))
            or tuple(item.code for item in self.checks) != PHASE12_CHECK_ORDER
        ):
            raise ValueError("report check registry is invalid")
        if (
            tuple(item.ordinal for item in self.request_evidence)
            != tuple(range(1, len(PHASE12_INSPECTION_ORDER) + 1))
            or tuple(item.code for item in self.request_evidence) != PHASE12_INSPECTION_ORDER
        ):
            raise ValueError("report request registry is invalid")
        expected_expiry_state = (
            ExpiryState.EXPIRED
            if self.rendered_at_utc >= self.expires_at_utc
            else ExpiryState.CURRENT
        )
        if self.expiry_state is not expected_expiry_state:
            raise ValueError("report expiry state is invalid")
        expected_mock_notice = (
            MOCK_NOTICE if self.source_kind is ReadinessSourceKind.DETERMINISTIC_MOCK else None
        )
        if self.mock_notice != expected_mock_notice:
            raise ValueError("report source notice is invalid")
        return self


class ReadinessReport(ReadinessReportBody):
    report_sha256: SHA256

    @model_validator(mode="after")
    def validate_report_hash(self) -> Self:
        body = _report_body_payload(self)
        expected = hashlib.sha256(canonical_json_bytes(body)).hexdigest()
        if self.report_sha256 != expected:
            raise ValueError("report hash is invalid")
        return self


def _parser() -> argparse.ArgumentParser:
    parser = _SanitizedArgumentParser(
        description="Render one sanitized PAPER ONLY persisted readiness report.",
        allow_abbrev=False,
    )
    parser.add_argument("--assessment-id", action=_SingleValueAction, required=True)
    parser.add_argument("--rendered-at-utc", action=_SingleValueAction, required=True)
    parser.add_argument("--output", action=_SingleValueAction, required=True)
    return parser


def _required_environment(name: str) -> str:
    value = os.environ.get(name)
    if value is None or not value.strip():
        raise ReportInvocationError
    return value


def _database_url_is_local_postgresql(value: str) -> bool:
    if any(name in os.environ for name in LIBPQ_ROUTING_ENV_NAMES):
        return False
    try:
        parsed = make_url(value)
        if parsed.drivername != "postgresql+psycopg" or parsed.query:
            return False
        host = parsed.host
    except Exception:
        return False
    if host is None:
        return False
    normalized = host.rstrip(".").lower()
    if normalized == "localhost":
        return True
    try:
        return ip_address(normalized).is_loopback
    except ValueError:
        return False


def _parse_assessment_id(value: object) -> UUID:
    if not isinstance(value, str) or len(value) > 64:
        raise ReportInvocationError
    try:
        return UUID(value)
    except (AttributeError, TypeError, ValueError):
        raise ReportInvocationError from None


def _parse_rendered_at_utc(value: object) -> datetime:
    if (
        not isinstance(value, str)
        or len(value) > 64
        or _RENDERED_AT_UTC_PATTERN.fullmatch(value) is None
    ):
        raise ReportInvocationError
    candidate = f"{value[:-1]}+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(candidate)
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError
        return parsed.astimezone(UTC)
    except (OverflowError, TypeError, ValueError):
        raise ReportInvocationError from None


def _assert_safe_text(value: str) -> None:
    if _UNSAFE_MARKER_PATTERN.search(value) is not None:
        raise ReportProjectionError(PROJECTION_FAILURE_MESSAGE)
    for matched in _UPPERCASE_TOKEN_PATTERN.finditer(value):
        if any(character.isalpha() for character in matched.group(0)):
            raise ReportProjectionError(PROJECTION_FAILURE_MESSAGE)


def _assert_safe_value(value: object) -> None:
    if isinstance(value, str):
        _assert_safe_text(value)
        return
    if isinstance(value, BaseModel):
        _assert_safe_value(value.model_dump(mode="python"))
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            _assert_safe_text(str(key))
            _assert_safe_value(item)
        return
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, memoryview)):
        for item in value:
            _assert_safe_value(item)


def _assert_safe_artifact_source(artifact: PaperShadowReadinessArtifact) -> None:
    source = artifact.model_dump(mode="python")
    idempotency_key = source.get("readiness_idempotency_key")
    if (
        isinstance(idempotency_key, str)
        and _T004_GENERATED_IDEMPOTENCY_KEY_PATTERN.fullmatch(idempotency_key) is not None
    ):
        source["readiness_idempotency_key"] = "phase12-t004-generated-utc"
    _assert_safe_value(source)


def _report_body_payload(report: ReadinessReportBody) -> dict[str, object]:
    body = report.model_dump(mode="python", exclude={"report_sha256"})
    if body.get("mock_notice") is None:
        body.pop("mock_notice", None)
    return body


def _report_payload(report: ReadinessReport) -> dict[str, object]:
    payload = report.model_dump(mode="python")
    if payload.get("mock_notice") is None:
        payload.pop("mock_notice", None)
    return payload


def _project_artifact(
    artifact: PaperShadowReadinessArtifact,
    rendered_at_utc: datetime,
) -> ReadinessReport:
    try:
        validated = PaperShadowReadinessArtifact.model_validate(artifact)
        _assert_safe_artifact_source(validated)
        body = ReadinessReportBody(
            readiness_assessment_id=validated.readiness_assessment_id,
            source_kind=validated.source_kind,
            outcome=validated.outcome,
            checks=tuple(
                ReportCheckProjection(
                    ordinal=item.ordinal,
                    code=item.code,
                    status=item.status,
                    check_sha256=item.check_sha256,
                )
                for item in validated.checks
            ),
            request_evidence=tuple(
                ReportRequestEvidenceProjection(
                    ordinal=item.ordinal,
                    code=item.code,
                    request_id=item.request_id,
                    response_sha256=item.response_sha256,
                )
                for item in validated.inspections
            ),
            phase12_code_version_git_sha=validated.phase12_code_version_git_sha,
            transport_profile_sha256=validated.transport_profile_sha256,
            assessment_started_at_utc=validated.assessment_started_at_utc,
            assessment_completed_at_utc=validated.assessment_completed_at_utc,
            expires_at_utc=validated.expires_at_utc,
            rendered_at_utc=rendered_at_utc,
            expiry_state=(
                ExpiryState.EXPIRED
                if rendered_at_utc >= validated.expires_at_utc
                else ExpiryState.CURRENT
            ),
            order_submission_authorized=validated.order_submission_authorized,
            strategy_execution_eligible=validated.strategy_execution_eligible,
            live_path_absent=validated.live_path_absent,
            no_personalized_investment_advice=validated.no_personalized_investment_advice,
            no_real_performance_claimed=validated.no_real_performance_claimed,
            simulated_paper_only=True,
            boundary_label=BOUNDARY_LABEL,
            mock_notice=(
                MOCK_NOTICE
                if validated.source_kind is ReadinessSourceKind.DETERMINISTIC_MOCK
                else None
            ),
        )
        body_payload = _report_body_payload(body)
        report = ReadinessReport.model_validate(
            {
                **body_payload,
                "report_sha256": hashlib.sha256(canonical_json_bytes(body_payload)).hexdigest(),
            }
        )
        _assert_safe_value(_report_payload(report))
        return report
    except Exception:
        raise ReportProjectionError(PROJECTION_FAILURE_MESSAGE) from None


def _utc_text(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ReportProjectionError(PROJECTION_FAILURE_MESSAGE)
    return value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _optional_text(value: str | None) -> str:
    return "null" if value is None else value


def _render_markdown(report: ReadinessReport) -> bytes:
    try:
        lines = [
            f"# {report.boundary_label}",
            "",
            f"- Readiness assessment ID: `{report.readiness_assessment_id}`",
            f"- Source kind: `{report.source_kind.value}`",
            f"- Outcome: `{report.outcome.value}`",
            f"- Phase 12 code Git SHA: `{report.phase12_code_version_git_sha}`",
            f"- Transport-profile SHA-256: `{report.transport_profile_sha256}`",
            f"- Assessment started at UTC: `{_utc_text(report.assessment_started_at_utc)}`",
            f"- Assessment completed at UTC: `{_utc_text(report.assessment_completed_at_utc)}`",
            f"- Expires at UTC: `{_utc_text(report.expires_at_utc)}`",
            f"- Rendered at UTC: `{_utc_text(report.rendered_at_utc)}`",
            f"- Expiry state: `{report.expiry_state.value}`",
            f"- simulated_paper_only: `{str(report.simulated_paper_only).lower()}`",
            (f"- order_submission_authorized: `{str(report.order_submission_authorized).lower()}`"),
            (f"- strategy_execution_eligible: `{str(report.strategy_execution_eligible).lower()}`"),
            f"- live_path_absent: `{str(report.live_path_absent).lower()}`",
            (
                "- no_personalized_investment_advice: "
                f"`{str(report.no_personalized_investment_advice).lower()}`"
            ),
            (f"- no_real_performance_claimed: `{str(report.no_real_performance_claimed).lower()}`"),
        ]
        if report.mock_notice is not None:
            lines.extend((f"- Scope: {report.mock_notice}",))
        lines.extend(
            (
                "",
                "## Checks",
                "",
                "| Ordinal | Code | Status | Check SHA-256 |",
                "| ---: | --- | --- | --- |",
            )
        )
        lines.extend(
            f"| {item.ordinal} | `{item.code.value}` | `{item.status.value}` | "
            f"`{item.check_sha256}` |"
            for item in report.checks
        )
        lines.extend(
            (
                "",
                "## Request evidence",
                "",
                "| Ordinal | Code | Request ID | Response SHA-256 |",
                "| ---: | --- | --- | --- |",
            )
        )
        lines.extend(
            f"| {item.ordinal} | `{item.code.value}` | "
            f"`{_optional_text(item.request_id)}` | "
            f"`{_optional_text(item.response_sha256)}` |"
            for item in report.request_evidence
        )
        lines.extend(("", f"- Report SHA-256: `{report.report_sha256}`", ""))
        rendered = "\n".join(lines)
        _assert_safe_text(rendered)
        return rendered.encode("utf-8")
    except Exception:
        raise ReportProjectionError(PROJECTION_FAILURE_MESSAGE) from None


def _new_repository(database_url: str) -> PaperShadowReadinessRepository:
    return PaperShadowReadinessRepository(database_url)


def _read_and_project(
    assessment_id: UUID,
    rendered_at_utc: datetime,
) -> ReadinessReport:
    database_url = _required_environment(DATABASE_URL_ENV_NAME)
    if not _database_url_is_local_postgresql(database_url):
        raise ReportInvocationError
    repository = _new_repository(database_url)
    try:
        artifact = repository.get_readiness(assessment_id)
        return _project_artifact(artifact, rendered_at_utc)
    finally:
        repository.dispose()


def _atomic_write(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    try:
        arguments = _parser().parse_args(argv)
        assessment_id = _parse_assessment_id(arguments.assessment_id)
        rendered_at_utc = _parse_rendered_at_utc(arguments.rendered_at_utc)
        report = _read_and_project(assessment_id, rendered_at_utc)
        payload = _report_payload(report)
        rendered_json = canonical_json_bytes(payload) + b"\n"
        rendered_markdown = _render_markdown(report)
        _assert_safe_text(rendered_json.decode("utf-8"))
        _atomic_write(Path(arguments.output), rendered_markdown)
        sys.stdout.buffer.write(rendered_json)
        sys.stdout.buffer.flush()
        return 0
    except Exception:
        print(FAILURE_MESSAGE, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
