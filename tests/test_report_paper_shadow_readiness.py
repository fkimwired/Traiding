from __future__ import annotations

import hashlib
import json
import socket
import warnings
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from fable5_paper.phase12.adapters import DeterministicMockPaperBrokerAdapter
from fable5_paper.phase12.canonical import canonical_json_bytes
from fable5_paper.phase12.contracts import (
    PHASE12_CHECK_ORDER,
    PHASE12_INSPECTION_ORDER,
    PaperShadowReadinessArtifact,
    PaperShadowReadinessCreateRequest,
)
from fable5_paper.phase12.repository import PaperShadowReadinessNotFound
from fable5_paper.phase12.workflow import (
    PaperShadowReadinessCreation,
    PaperShadowReadinessWorkflow,
)
from pydantic import ValidationError
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine

import scripts.report_paper_shadow_readiness as report_cli

GIT_SHA = "4d70b823947fd61d0ea17df14c9f1ff9f93fd45b"
DATABASE_URL = "postgresql+psycopg://fable5:dev-only@127.0.0.1:5432/fable5"
KEY_CANARY = "CANARY_KEY_9f3"
SECRET_CANARY = "CANARY_SECRET_7c1"
ENV_PREFIX_CANARY = "FABLE5_ALPACA"
FIXED_RENDER_TIME = datetime(2026, 7, 22, 14, 30, 0, 123456, tzinfo=UTC)


class _MemoryCreationStore:
    def __init__(self) -> None:
        self.by_key: dict[str, PaperShadowReadinessArtifact] = {}

    @contextmanager
    def serialized_creation(self, key: str) -> Iterator[PaperShadowReadinessCreation]:
        del key
        yield self

    def find_by_idempotency_key(self, key: str) -> PaperShadowReadinessArtifact | None:
        return self.by_key.get(key)

    def create_readiness(
        self, artifact: PaperShadowReadinessArtifact
    ) -> PaperShadowReadinessArtifact:
        self.by_key[artifact.readiness_idempotency_key] = artifact
        return artifact

    def get_readiness(self, readiness_assessment_id: UUID) -> PaperShadowReadinessArtifact:
        return next(
            artifact
            for artifact in self.by_key.values()
            if artifact.readiness_assessment_id == readiness_assessment_id
        )


def _mock_artifact() -> PaperShadowReadinessArtifact:
    return PaperShadowReadinessWorkflow(
        adapter=DeterministicMockPaperBrokerAdapter(),
        store=_MemoryCreationStore(),
        phase12_code_version_git_sha=GIT_SHA,
        clock=lambda: datetime(2024, 1, 2, 15, 0, tzinfo=UTC),
    ).create_readiness(
        PaperShadowReadinessCreateRequest(readiness_idempotency_key="phase12-t002-mock-evidence")
    )


class _AuditedReadRepository:
    def __init__(self, artifact: PaperShadowReadinessArtifact) -> None:
        self.artifact = artifact
        self.engine: Engine = create_engine("sqlite+pysqlite:///:memory:")
        self.statements: list[str] = []
        self.requested_ids: list[UUID] = []
        self.disposed = False
        event.listen(self.engine, "before_cursor_execute", self._audit_statement)

    def _audit_statement(
        self,
        connection: object,
        cursor: object,
        statement: str,
        parameters: object,
        context: object,
        executemany: bool,
    ) -> None:
        del connection, cursor, parameters, context, executemany
        self.statements.append(statement)

    def get_readiness(self, readiness_assessment_id: UUID) -> PaperShadowReadinessArtifact:
        self.requested_ids.append(readiness_assessment_id)
        with self.engine.connect() as connection:
            assert connection.exec_driver_sql("SELECT 1").scalar_one() == 1
        return self.artifact

    def dispose(self) -> None:
        self.disposed = True
        self.engine.dispose()


class _MissingReadRepository(_AuditedReadRepository):
    def get_readiness(self, readiness_assessment_id: UUID) -> PaperShadowReadinessArtifact:
        self.requested_ids.append(readiness_assessment_id)
        with self.engine.connect() as connection:
            assert connection.exec_driver_sql("SELECT 1").scalar_one() == 1
        raise PaperShadowReadinessNotFound(
            f"missing {KEY_CANARY} {SECRET_CANARY} {readiness_assessment_id}"
        )


def _install_repository(
    monkeypatch: pytest.MonkeyPatch,
    repository: _AuditedReadRepository,
) -> None:
    monkeypatch.setenv(report_cli.DATABASE_URL_ENV_NAME, DATABASE_URL)

    def new_repository(database_url: str) -> _AuditedReadRepository:
        assert database_url == DATABASE_URL
        return repository

    monkeypatch.setattr(report_cli, "_new_repository", new_repository)


def _parse_stdout(value: str) -> dict[str, Any]:
    parsed = json.loads(value)
    assert isinstance(parsed, dict)
    return parsed


def _render_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    *,
    rendered_at_utc: str = "2026-07-22T14:30:00.123456Z",
) -> tuple[dict[str, Any], str, _AuditedReadRepository, Path]:
    artifact = _mock_artifact()
    repository = _AuditedReadRepository(artifact)
    _install_repository(monkeypatch, repository)
    output_path = tmp_path / "readiness-evidence.md"
    result = report_cli.main(
        [
            "--assessment-id",
            str(artifact.readiness_assessment_id),
            "--rendered-at-utc",
            rendered_at_utc,
            "--output",
            str(output_path),
        ]
    )
    captured = capsys.readouterr()
    assert result == 0
    assert captured.err == ""
    return _parse_stdout(captured.out), captured.out, repository, output_path


def test_main_renders_canonical_json_and_markdown_from_one_select_only_read(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv(f"{ENV_PREFIX_CANARY}_PAPER_API_KEY_ID", KEY_CANARY)
    monkeypatch.setenv(f"{ENV_PREFIX_CANARY}_PAPER_SECRET_KEY", SECRET_CANARY)

    def deny_external_socket(*args: object, **kwargs: object) -> socket.socket:
        del args, kwargs
        raise AssertionError("external socket attempted")

    monkeypatch.setattr(socket, "create_connection", deny_external_socket)
    parsed, stdout, repository, output_path = _render_success(monkeypatch, tmp_path, capsys)
    markdown = output_path.read_text(encoding="utf-8")

    assert set(parsed) == {
        "assessment_completed_at_utc",
        "assessment_started_at_utc",
        "boundary_label",
        "checks",
        "expires_at_utc",
        "expiry_state",
        "live_path_absent",
        "mock_notice",
        "no_personalized_investment_advice",
        "no_real_performance_claimed",
        "order_submission_authorized",
        "outcome",
        "phase12_code_version_git_sha",
        "readiness_assessment_id",
        "rendered_at_utc",
        "report_sha256",
        "request_evidence",
        "simulated_paper_only",
        "source_kind",
        "strategy_execution_eligible",
        "transport_profile_sha256",
    }
    assert parsed["outcome"] == "MOCK_PROOF_COMPLETE"
    assert parsed["simulated_paper_only"] is True
    assert parsed["boundary_label"] == report_cli.BOUNDARY_LABEL
    assert parsed["mock_notice"] == report_cli.MOCK_NOTICE
    assert len(parsed["checks"]) == 8
    assert [item["code"] for item in parsed["checks"]] == [
        item.value for item in PHASE12_CHECK_ORDER
    ]
    assert [set(item) for item in parsed["checks"]] == [
        {"ordinal", "code", "status", "check_sha256"}
    ] * 8
    assert len(parsed["request_evidence"]) == 6
    assert [item["code"] for item in parsed["request_evidence"]] == [
        item.value for item in PHASE12_INSPECTION_ORDER
    ]
    assert [set(item) for item in parsed["request_evidence"]] == [
        {"ordinal", "code", "request_id", "response_sha256"}
    ] * 6
    assert all(item["request_id"] is None for item in parsed["request_evidence"])
    assert all(item["response_sha256"] is None for item in parsed["request_evidence"])
    assert parsed["order_submission_authorized"] is False
    assert parsed["strategy_execution_eligible"] is False
    assert parsed["live_path_absent"] is True
    assert parsed["no_personalized_investment_advice"] is True
    assert parsed["no_real_performance_claimed"] is True

    body = dict(parsed)
    report_sha256 = body.pop("report_sha256")
    assert report_sha256 == hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    assert stdout.encode("utf-8") == canonical_json_bytes(parsed) + b"\n"
    assert report_cli.BOUNDARY_LABEL in markdown
    assert report_cli.MOCK_NOTICE in markdown
    assert report_sha256 in markdown
    assert repository.requested_ids == [UUID(parsed["readiness_assessment_id"])]
    assert repository.disposed is True
    assert repository.statements == ["SELECT 1"]
    assert not any(
        statement.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))
        for statement in repository.statements
    )
    assert not output_path.with_suffix(".json").exists()

    rendered = stdout + markdown
    for forbidden in (ENV_PREFIX_CANARY, KEY_CANARY, SECRET_CANARY):
        assert forbidden not in rendered


def test_report_is_byte_deterministic_and_normalizes_render_offset(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    first, first_stdout, _, first_path = _render_success(
        monkeypatch,
        tmp_path / "first",
        capsys,
        rendered_at_utc="2026-07-22T10:30:00.123456-04:00",
    )
    first_markdown = first_path.read_bytes()
    second, second_stdout, _, second_path = _render_success(
        monkeypatch,
        tmp_path / "second",
        capsys,
        rendered_at_utc="2026-07-22T14:30:00.123456Z",
    )

    assert first == second
    assert first_stdout == second_stdout
    assert first_markdown == second_path.read_bytes()
    assert first["rendered_at_utc"] == "2026-07-22T14:30:00.123456Z"


def test_expiry_boundary_uses_only_the_supplied_render_time() -> None:
    artifact = _mock_artifact()
    current = report_cli._project_artifact(
        artifact, artifact.expires_at_utc - timedelta(microseconds=1)
    )
    expired = report_cli._project_artifact(artifact, artifact.expires_at_utc)

    assert current.expiry_state is report_cli.ExpiryState.CURRENT
    assert expired.expiry_state is report_cli.ExpiryState.EXPIRED
    assert "datetime.now" not in Path(report_cli.__file__).read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "arguments",
    (
        [],
        ["--unknown", KEY_CANARY],
        [
            "--assessment-id",
            KEY_CANARY,
            "--rendered-at-utc",
            "2026-07-22T14:30:00Z",
            "--output",
            "unused.md",
        ],
        [
            "--assessment-id",
            "55934e08-c4a2-548d-b9cd-13a1c824211b",
            "--rendered-at-utc",
            SECRET_CANARY,
            "--output",
            "unused.md",
        ],
        [
            "--assessment-id",
            "55934e08-c4a2-548d-b9cd-13a1c824211b",
            "--rendered-at-utc",
            "2026-07-22X14:30:00Z",
            "--output",
            "unused.md",
        ],
        [
            "--assessment-id",
            "55934e08-c4a2-548d-b9cd-13a1c824211b",
            "--rendered-at-utc",
            "2026-07-22T14:30:00",
            "--output",
            "unused.md",
        ],
        [
            "--assessment-id",
            "55934e08-c4a2-548d-b9cd-13a1c824211b",
            "--assessment-id",
            "55934e08-c4a2-548d-b9cd-13a1c824211b",
            "--rendered-at-utc",
            "2026-07-22T14:30:00Z",
            "--output",
            "unused.md",
        ],
    ),
)
def test_malformed_or_repeated_arguments_exit_two_without_echo(
    capsys: pytest.CaptureFixture[str], arguments: list[str]
) -> None:
    assert report_cli.main(arguments) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == f"{report_cli.FAILURE_MESSAGE}\n"
    assert "Traceback" not in captured.err
    assert KEY_CANARY not in captured.err
    assert SECRET_CANARY not in captured.err


def test_nonexistent_assessment_is_generic_exit_two_and_disposes_repository(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    artifact = _mock_artifact()
    repository = _MissingReadRepository(artifact)
    _install_repository(monkeypatch, repository)
    output_path = tmp_path / "must-not-exist.md"

    assert (
        report_cli.main(
            [
                "--assessment-id",
                str(artifact.readiness_assessment_id),
                "--rendered-at-utc",
                "2026-07-22T14:30:00Z",
                "--output",
                str(output_path),
            ]
        )
        == 2
    )
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == f"{report_cli.FAILURE_MESSAGE}\n"
    assert "Traceback" not in captured.err
    assert KEY_CANARY not in captured.err
    assert SECRET_CANARY not in captured.err
    assert output_path.exists() is False
    assert repository.disposed is True
    assert repository.statements == ["SELECT 1"]


@pytest.mark.parametrize(
    "canary",
    (KEY_CANARY, SECRET_CANARY, "ABCDEFGHIJKLMNOPQRST"),
)
def test_canary_in_disallowed_source_position_fails_closed_with_fixed_error(
    canary: str,
) -> None:
    artifact = _mock_artifact()
    tampered = artifact.model_copy(update={"readiness_idempotency_key": canary})

    with pytest.raises(report_cli.ReportProjectionError) as raised:
        report_cli._project_artifact(tampered, FIXED_RENDER_TIME)

    assert str(raised.value) == report_cli.PROJECTION_FAILURE_MESSAGE
    assert canary not in str(raised.value)


def test_invalid_nested_canary_emits_no_warning_or_input_echo() -> None:
    artifact = _mock_artifact()
    tampered = artifact.model_copy(update={"account": KEY_CANARY})

    with warnings.catch_warnings(record=True) as observed:
        warnings.simplefilter("always")
        with pytest.raises(report_cli.ReportProjectionError) as raised:
            report_cli._project_artifact(tampered, FIXED_RENDER_TIME)

    assert observed == []
    assert str(raised.value) == report_cli.PROJECTION_FAILURE_MESSAGE
    assert KEY_CANARY not in str(raised.value)


def test_unexpected_source_extra_fails_instead_of_being_silently_dropped() -> None:
    artifact = _mock_artifact()
    tampered = artifact.model_copy(update={"raw_body": SECRET_CANARY})

    with pytest.raises(report_cli.ReportProjectionError) as raised:
        report_cli._project_artifact(tampered, FIXED_RENDER_TIME)

    assert str(raised.value) == report_cli.PROJECTION_FAILURE_MESSAGE
    assert SECRET_CANARY not in str(raised.value)


def test_projection_models_forbid_unenumerated_output_fields() -> None:
    report = report_cli._project_artifact(_mock_artifact(), FIXED_RENDER_TIME)
    payload = report_cli._report_body_payload(report)
    payload["raw_body"] = "safe-but-disallowed"

    with pytest.raises(ValidationError):
        report_cli.ReadinessReportBody.model_validate(payload)


def test_projection_models_reject_type_coercion() -> None:
    report = report_cli._project_artifact(_mock_artifact(), FIXED_RENDER_TIME)
    payload = report_cli._report_body_payload(report)
    payload["simulated_paper_only"] = 1

    with pytest.raises(ValidationError):
        report_cli.ReadinessReportBody.model_validate(payload)

    second_payload = report_cli._report_body_payload(report)
    checks = list(second_payload["checks"])
    first_check = dict(checks[0])
    first_check["ordinal"] = "1"
    checks[0] = first_check
    second_payload["checks"] = checks
    with pytest.raises(ValidationError):
        report_cli.ReadinessReportBody.model_validate(second_payload)


def test_remote_database_routing_is_rejected_before_repository_or_socket(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    artifact = _mock_artifact()
    monkeypatch.setenv(
        report_cli.DATABASE_URL_ENV_NAME,
        "postgresql+psycopg://fable5:do-not-render@database.example:5432/fable5",
    )

    def forbidden_repository(database_url: str) -> _AuditedReadRepository:
        del database_url
        raise AssertionError("repository construction attempted")

    def forbidden_socket(*args: object, **kwargs: object) -> socket.socket:
        del args, kwargs
        raise AssertionError("socket attempted")

    monkeypatch.setattr(report_cli, "_new_repository", forbidden_repository)
    monkeypatch.setattr(socket, "create_connection", forbidden_socket)

    assert (
        report_cli.main(
            [
                "--assessment-id",
                str(artifact.readiness_assessment_id),
                "--rendered-at-utc",
                "2026-07-22T14:30:00Z",
                "--output",
                str(tmp_path / "unused.md"),
            ]
        )
        == 2
    )
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == f"{report_cli.FAILURE_MESSAGE}\n"
    assert "do-not-render" not in captured.err


def test_script_has_no_external_provider_or_mutation_surface() -> None:
    source = Path(report_cli.__file__).read_text(encoding="utf-8")
    lowered = source.casefold()
    assert ENV_PREFIX_CANARY not in source
    for forbidden in (
        "phase12.alpaca",
        "paper-api.alpaca.markets",
        "data.alpaca.markets",
        "--provider",
        "--url",
        "--symbol",
        "requests.",
        "urllib",
        "socket.",
        "create_readiness(",
        "submit_order(",
        "replace_order(",
        "cancel_order(",
        "close_position(",
        "scheduler",
        "retry",
    ):
        assert forbidden not in lowered
