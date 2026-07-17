from __future__ import annotations

import os
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from typing import Any
from uuid import uuid4

import fable5_data.phase13.repository as repository_module
import pytest
from fable5_data.phase13.adapters import (
    DeterministicMockPointInTimeQualificationAdapter,
    MockQualificationScenario,
)
from fable5_data.phase13.contracts import (
    PHASE13_CAPABILITY_ORDER,
    PHASE13_CHECK_ORDER,
    PointInTimeQualificationArtifact,
    PointInTimeQualificationCreateRequest,
    QualificationOutcome,
)
from fable5_data.phase13.repository import (
    PointInTimeQualificationRepository,
    PointInTimeQualificationRepositoryConflict,
)
from fable5_data.phase13.workflow import PointInTimeQualificationWorkflow
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import DBAPIError

DATABASE_URL = os.environ.get("FABLE5_TEST_DATABASE_URL")
CODE_VERSION_GIT_SHA = os.environ.get("FABLE5_CODE_VERSION_GIT_SHA", "a" * 40)
APPEND_ONLY_ERROR = "Phase 13 point-in-time qualification artifacts are append-only"


class _ArtifactBuilderStore:
    def __init__(self) -> None:
        self.artifact: PointInTimeQualificationArtifact | None = None

    @contextmanager
    def serialized_creation(self, key: str) -> Iterator[_ArtifactBuilderStore]:
        del key
        yield self

    def find_by_idempotency_key(self, key: str) -> PointInTimeQualificationArtifact | None:
        del key
        return self.artifact

    def create_qualification(
        self, artifact: PointInTimeQualificationArtifact
    ) -> PointInTimeQualificationArtifact:
        self.artifact = artifact
        return artifact

    def get_qualification(self, qualification_id: object) -> PointInTimeQualificationArtifact:
        if self.artifact is None or self.artifact.qualification_id != qualification_id:
            raise LookupError("qualification not built")
        return self.artifact


def _mock_artifact(
    tag: str,
    *,
    git_sha: str = CODE_VERSION_GIT_SHA,
    scenario: MockQualificationScenario = MockQualificationScenario.COMPLETE,
) -> PointInTimeQualificationArtifact:
    store = _ArtifactBuilderStore()
    workflow = PointInTimeQualificationWorkflow(
        adapter=DeterministicMockPointInTimeQualificationAdapter(scenario),
        store=store,
        phase13_code_version_git_sha=git_sha,
    )
    return workflow.create_qualification(
        PointInTimeQualificationCreateRequest(
            qualification_idempotency_key=f"phase13-postgres-{tag}"
        )
    )


def _require_postgres() -> str:
    if DATABASE_URL is None:
        pytest.skip("Phase 13 PostgreSQL URL is unavailable")
    assert DATABASE_URL is not None
    return DATABASE_URL


def test_phase13_repository_structurally_exposes_only_qualification_persistence() -> None:
    repository = PointInTimeQualificationRepository("sqlite+pysqlite:///:memory:")
    try:
        for method in (
            "serialized_creation",
            "find_by_idempotency_key",
            "create_qualification",
            "get_qualification",
            "dispose",
        ):
            assert callable(getattr(repository, method))
        for forbidden in (
            "create_snapshot",
            "promote_strategy",
            "submit_order",
            "replace_order",
            "cancel_order",
        ):
            assert not hasattr(repository, forbidden)
    finally:
        repository.dispose()


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    ("scenario", "expected_outcome"),
    (
        (MockQualificationScenario.COMPLETE, QualificationOutcome.MOCK_PROOF_COMPLETE),
        (MockQualificationScenario.MISSING_DELISTING_RETURN, QualificationOutcome.BLOCKED),
    ),
)
def test_postgres_roundtrip_preserves_complete_and_blocked_hash_bound_bundles(
    scenario: MockQualificationScenario,
    expected_outcome: QualificationOutcome,
) -> None:
    repository = PointInTimeQualificationRepository(_require_postgres())
    artifact = _mock_artifact(
        f"roundtrip-{scenario.value.lower()}-{uuid4().hex}", scenario=scenario
    )
    try:
        persisted = repository.create_qualification(artifact)
        assert persisted == artifact
        assert persisted.outcome is expected_outcome
        assert repository.create_qualification(artifact) == artifact
        assert repository.get_qualification(artifact.qualification_id) == artifact
        assert (
            repository.find_by_idempotency_key(artifact.qualification_idempotency_key) == artifact
        )
        with repository.engine.connect() as connection:
            counts = connection.execute(
                text(
                    "SELECT "
                    "(SELECT count(*) FROM point_in_time_qualification_payloads "
                    " WHERE qualification_id = :qualification_id), "
                    "(SELECT count(*) FROM point_in_time_qualification_checks "
                    " WHERE qualification_id = :qualification_id)"
                ),
                {"qualification_id": artifact.qualification_id},
            ).one()
        assert counts == (len(PHASE13_CAPABILITY_ORDER), len(PHASE13_CHECK_ORDER))
    finally:
        repository.dispose()


def test_postgres_deterministic_mock_workflow_is_idempotent_and_historical() -> None:
    repository = PointInTimeQualificationRepository(_require_postgres())
    workflow = PointInTimeQualificationWorkflow(
        adapter=DeterministicMockPointInTimeQualificationAdapter(),
        store=repository,
        phase13_code_version_git_sha=CODE_VERSION_GIT_SHA,
    )
    request = PointInTimeQualificationCreateRequest(
        qualification_idempotency_key=f"phase13-postgres-workflow-{uuid4().hex}"
    )
    try:
        artifact = workflow.create_qualification(request)
        assert artifact.outcome is QualificationOutcome.MOCK_PROOF_COMPLETE
        assert artifact.completed_at_utc.year == 2024
        assert not artifact.research_data_eligible
        assert not artifact.strategy_promotion_authorized
        assert not artifact.execution_authorized
        assert not artifact.order_submission_authorized
        assert workflow.create_qualification(request) == artifact
        assert workflow.get_qualification(artifact.qualification_id) == artifact
    finally:
        repository.dispose()


def test_postgres_two_writers_store_one_complete_idempotent_bundle() -> None:
    database_url = _require_postgres()
    first = PointInTimeQualificationRepository(database_url)
    second = PointInTimeQualificationRepository(database_url)
    artifact = _mock_artifact(f"concurrent-{uuid4().hex}")
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = tuple(
                future.result(timeout=30)
                for future in (
                    executor.submit(first.create_qualification, artifact),
                    executor.submit(second.create_qualification, artifact),
                )
            )
        assert results == (artifact, artifact)
        with first.engine.connect() as connection:
            assert (
                connection.scalar(
                    text(
                        "SELECT count(*) FROM point_in_time_qualification_runs "
                        "WHERE qualification_idempotency_key = :key"
                    ),
                    {"key": artifact.qualification_idempotency_key},
                )
                == 1
            )
    finally:
        second.dispose()
        first.dispose()


def test_postgres_same_key_with_different_fingerprint_conflicts() -> None:
    repository = PointInTimeQualificationRepository(_require_postgres())
    tag = f"conflict-{uuid4().hex}"
    original = _mock_artifact(tag)
    alternate_sha = "b" * 40 if CODE_VERSION_GIT_SHA != "b" * 40 else "c" * 40
    conflicting = _mock_artifact(tag, git_sha=alternate_sha)
    try:
        assert repository.create_qualification(original) == original
        with pytest.raises(
            PointInTimeQualificationRepositoryConflict,
            match="different request fingerprint",
        ):
            repository.create_qualification(conflicting)
        assert (
            repository.find_by_idempotency_key(original.qualification_idempotency_key) == original
        )
    finally:
        repository.dispose()


def test_postgres_root_payload_tamper_is_rejected_before_child_storage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = PointInTimeQualificationRepository(_require_postgres())
    artifact = _mock_artifact(f"root-tamper-{uuid4().hex}")
    original_payload = repository_module._artifact_payload

    def tampered_payload(value: PointInTimeQualificationArtifact) -> dict[str, Any]:
        payload = original_payload(value)
        payload["execution_authorized"] = True
        return payload

    monkeypatch.setattr(repository_module, "_artifact_payload", tampered_payload)
    try:
        with pytest.raises(DBAPIError, match="root payload mismatch"):
            with repository.engine.begin() as connection:
                PointInTimeQualificationRepository._insert_qualification(connection, artifact)
        assert repository.find_by_idempotency_key(artifact.qualification_idempotency_key) is None
    finally:
        repository.dispose()


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    ("payload_builder", "tampered_field", "expected_error"),
    (
        (
            "_manifest_payload",
            "record_count",
            "capability manifest payload mismatch",
        ),
        (
            "_check_payload",
            "observed_value",
            "qualification check payload mismatch",
        ),
    ),
)
def test_postgres_child_payload_tamper_is_rejected_and_fully_rolled_back(
    monkeypatch: pytest.MonkeyPatch,
    payload_builder: str,
    tampered_field: str,
    expected_error: str,
) -> None:
    repository = PointInTimeQualificationRepository(_require_postgres())
    artifact = _mock_artifact(f"child-tamper-{payload_builder}-{uuid4().hex}")
    original_builder = getattr(repository_module, payload_builder)

    def tampered_payload(value: object) -> dict[str, Any]:
        payload = original_builder(value)
        payload[tampered_field] = "tampered" if tampered_field == "observed_value" else 0
        return payload

    monkeypatch.setattr(repository_module, payload_builder, tampered_payload)
    try:
        with pytest.raises(DBAPIError, match=expected_error):
            with repository.engine.begin() as connection:
                PointInTimeQualificationRepository._insert_qualification(connection, artifact)
        assert repository.find_by_idempotency_key(artifact.qualification_idempotency_key) is None
    finally:
        repository.dispose()


def test_postgres_deferred_completeness_rolls_back_a_missing_capability(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = PointInTimeQualificationRepository(_require_postgres())
    artifact = _mock_artifact(f"incomplete-{uuid4().hex}")
    original_insert = repository_module._insert_row

    def incomplete_insert(
        connection: Connection,
        table: str,
        row: dict[str, Any],
        *,
        json_columns: frozenset[str] = frozenset(),
    ) -> None:
        if table != "point_in_time_qualification_payloads" or row["ordinal"] != 6:
            original_insert(connection, table, row, json_columns=json_columns)

    monkeypatch.setattr(repository_module, "_insert_row", incomplete_insert)
    try:
        with pytest.raises(DBAPIError, match="exact complete ordered evidence"):
            with repository.engine.begin() as connection:
                PointInTimeQualificationRepository._insert_qualification(connection, artifact)
        assert repository.find_by_idempotency_key(artifact.qualification_idempotency_key) is None
    finally:
        repository.dispose()


def test_postgres_phase13_rows_reject_update_delete_and_truncate() -> None:
    repository = PointInTimeQualificationRepository(_require_postgres())
    artifact = _mock_artifact(f"immutable-{uuid4().hex}")
    try:
        repository.create_qualification(artifact)
        for table in (
            "point_in_time_qualification_runs",
            "point_in_time_qualification_payloads",
            "point_in_time_qualification_checks",
        ):
            for statement in (
                text(
                    f"UPDATE {table} SET created_at_utc = created_at_utc "
                    "WHERE qualification_id = :qualification_id"
                ),
                text(f"DELETE FROM {table} WHERE qualification_id = :qualification_id"),
                text(f"TRUNCATE TABLE {table} CASCADE"),
            ):
                with pytest.raises(DBAPIError, match=APPEND_ONLY_ERROR):
                    with repository.engine.begin() as connection:
                        connection.execute(
                            statement,
                            {"qualification_id": artifact.qualification_id},
                        )
        assert repository.get_qualification(artifact.qualification_id) == artifact
    finally:
        repository.dispose()
