from __future__ import annotations

import os
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from threading import Lock
from typing import Any
from uuid import uuid4

import fable5_data.phase14.repository as repository_module
import pytest
from fable5_data.phase13.adapters import (
    DeterministicMockPointInTimeQualificationAdapter,
    MockQualificationScenario,
)
from fable5_data.phase13.contracts import (
    PointInTimeQualificationArtifact,
    PointInTimeQualificationCreateRequest,
)
from fable5_data.phase13.repository import (
    PointInTimeQualificationRepository,
    PointInTimeQualificationRepositoryConflict,
)
from fable5_data.phase13.workflow import PointInTimeQualificationWorkflow
from fable5_data.phase14.canonical import (
    PHASE14_ARTIFACT_HASH_DOMAIN,
    PHASE14_CHECK_HASH_DOMAIN,
    domain_sha256,
)
from fable5_data.phase14.contracts import (
    PHASE14_CHECK_ORDER,
    ResearchIngestionEligibilityArtifact,
    ResearchIngestionEligibilityCheck,
    ResearchIngestionEligibilityCreateRequest,
    ResearchIngestionEligibilityOutcome,
)
from fable5_data.phase14.repository import (
    ResearchIngestionEligibilityRepository,
)
from fable5_data.phase14.workflow import (
    ResearchIngestionEligibilityWorkflow,
    ResearchIngestionEligibilityWorkflowConflict,
)
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import DBAPIError

DATABASE_URL = os.environ.get("FABLE5_TEST_DATABASE_URL")
CODE_VERSION_GIT_SHA = os.environ.get("FABLE5_CODE_VERSION_GIT_SHA", "a" * 40)
APPEND_ONLY_ERROR = "Phase 14 research-ingestion eligibility artifacts are append-only"


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


class _CountingQualificationSource:
    def __init__(self, repository: PointInTimeQualificationRepository) -> None:
        self.repository = repository
        self.calls = 0
        self._lock = Lock()

    def get_qualification(self, qualification_id: object) -> PointInTimeQualificationArtifact:
        with self._lock:
            self.calls += 1
        return self.repository.get_qualification(qualification_id)  # type: ignore[arg-type]


class _EligibilityArtifactBuilderStore:
    def __init__(self) -> None:
        self.artifact: ResearchIngestionEligibilityArtifact | None = None

    @contextmanager
    def serialized_creation(self, key: str) -> Iterator[_EligibilityArtifactBuilderStore]:
        del key
        yield self

    def find_by_idempotency_key(self, key: str) -> None:
        del key
        return None

    def find_by_request_fingerprint(self, fingerprint: str) -> None:
        del fingerprint
        return None

    def create_assessment(
        self, artifact: ResearchIngestionEligibilityArtifact
    ) -> ResearchIngestionEligibilityArtifact:
        self.artifact = artifact
        return artifact

    def get_assessment(self, assessment_id: object) -> ResearchIngestionEligibilityArtifact:
        if self.artifact is None or self.artifact.assessment_id != assessment_id:
            raise LookupError("assessment not built")
        return self.artifact


def _mock_source(
    tag: str,
    *,
    scenario: MockQualificationScenario = MockQualificationScenario.COMPLETE,
) -> PointInTimeQualificationArtifact:
    store = _ArtifactBuilderStore()
    workflow = PointInTimeQualificationWorkflow(
        adapter=DeterministicMockPointInTimeQualificationAdapter(scenario),
        store=store,
        phase13_code_version_git_sha=CODE_VERSION_GIT_SHA,
    )
    return workflow.create_qualification(
        PointInTimeQualificationCreateRequest(qualification_idempotency_key=f"phase14-source-{tag}")
    )


def _require_postgres() -> str:
    if DATABASE_URL is None:
        pytest.skip("Phase 14 PostgreSQL URL is unavailable")
    assert DATABASE_URL is not None
    return DATABASE_URL


def _create_assessment(
    *,
    tag: str,
    source: PointInTimeQualificationArtifact,
    source_repository: PointInTimeQualificationRepository,
    repository: ResearchIngestionEligibilityRepository,
    key: str | None = None,
) -> ResearchIngestionEligibilityArtifact:
    source_repository.create_qualification(source)
    workflow = ResearchIngestionEligibilityWorkflow(
        qualification_source=source_repository,
        store=repository,
        phase14_code_version_git_sha=CODE_VERSION_GIT_SHA,
    )
    return workflow.create_assessment(
        ResearchIngestionEligibilityCreateRequest(
            assessment_idempotency_key=key or f"phase14-assessment-{tag}",
            qualification_id=source.qualification_id,
        )
    )


def _coherently_rehash_check_tamper(
    artifact: ResearchIngestionEligibilityArtifact,
    *,
    ordinal: int,
) -> ResearchIngestionEligibilityArtifact:
    original = artifact.checks[ordinal - 1]
    check_payload = original.model_dump(mode="python", exclude={"check_sha256"})
    check_payload["observed_value"] = f"tampered-{ordinal}"
    check_payload["evidence_sha256s"] = ("f" * 64,)
    tampered_check = ResearchIngestionEligibilityCheck.model_validate(
        {
            **check_payload,
            "check_sha256": domain_sha256(PHASE14_CHECK_HASH_DOMAIN, check_payload),
        }
    )
    checks = list(artifact.checks)
    checks[ordinal - 1] = tampered_check
    artifact_payload = artifact.model_dump(mode="python", exclude={"artifact_sha256"})
    artifact_payload["checks"] = tuple(checks)
    return artifact.model_copy(
        update={
            "checks": tuple(checks),
            "artifact_sha256": domain_sha256(PHASE14_ARTIFACT_HASH_DOMAIN, artifact_payload),
        }
    )


def test_phase14_repository_exposes_only_eligibility_persistence() -> None:
    repository = ResearchIngestionEligibilityRepository("sqlite+pysqlite:///:memory:")
    try:
        for method in (
            "serialized_creation",
            "find_by_idempotency_key",
            "find_by_request_fingerprint",
            "create_assessment",
            "get_assessment",
            "dispose",
        ):
            assert callable(getattr(repository, method))
        for forbidden in (
            "create_snapshot",
            "run_research",
            "promote_strategy",
            "submit_order",
            "replace_order",
            "cancel_order",
        ):
            assert not hasattr(repository, forbidden)
    finally:
        repository.dispose()


@pytest.mark.parametrize(
    ("scenario", "expected_outcome"),
    (
        (
            MockQualificationScenario.COMPLETE,
            ResearchIngestionEligibilityOutcome.MOCK_PROOF_COMPLETE,
        ),
        (
            MockQualificationScenario.MISSING_DELISTING_RETURN,
            ResearchIngestionEligibilityOutcome.BLOCKED,
        ),
    ),
)
def test_postgres_roundtrip_preserves_complete_and_blocked_source_bound_bundles(
    scenario: MockQualificationScenario,
    expected_outcome: ResearchIngestionEligibilityOutcome,
) -> None:
    database_url = _require_postgres()
    source_repository = PointInTimeQualificationRepository(database_url)
    repository = ResearchIngestionEligibilityRepository(database_url)
    tag = f"roundtrip-{scenario.value.lower()}-{uuid4().hex}"
    source = _mock_source(tag, scenario=scenario)
    try:
        artifact = _create_assessment(
            tag=tag,
            source=source,
            source_repository=source_repository,
            repository=repository,
        )
        assert artifact.outcome is expected_outcome
        assert not artifact.research_data_eligible
        assert not artifact.research_ingestion_authorized
        assert not artifact.performance_computed
        assert not artifact.pass_research_granted
        assert not artifact.execution_authorized
        assert not artifact.order_submission_authorized
        assert repository.create_assessment(artifact) == artifact
        assert repository.get_assessment(artifact.assessment_id) == artifact
        assert repository.find_by_idempotency_key(artifact.assessment_idempotency_key) == artifact
        with repository.engine.connect() as connection:
            counts = connection.execute(
                text(
                    "SELECT "
                    "(SELECT count(*) FROM research_ingestion_eligibility_payloads "
                    " WHERE assessment_id = :assessment_id), "
                    "(SELECT count(*) FROM research_ingestion_eligibility_checks "
                    " WHERE assessment_id = :assessment_id)"
                ),
                {"assessment_id": artifact.assessment_id},
            ).one()
        assert counts == (6, len(PHASE14_CHECK_ORDER))
    finally:
        repository.dispose()
        source_repository.dispose()


def test_postgres_same_key_workflow_replay_is_byte_identical_and_source_read_only() -> None:
    database_url = _require_postgres()
    source_repository = PointInTimeQualificationRepository(database_url)
    repository = ResearchIngestionEligibilityRepository(database_url)
    tag = f"replay-{uuid4().hex}"
    source = _mock_source(tag)
    source_repository.create_qualification(source)
    workflow = ResearchIngestionEligibilityWorkflow(
        qualification_source=source_repository,
        store=repository,
        phase14_code_version_git_sha=CODE_VERSION_GIT_SHA,
    )
    request = ResearchIngestionEligibilityCreateRequest(
        assessment_idempotency_key=f"phase14-assessment-{tag}",
        qualification_id=source.qualification_id,
    )
    try:
        with repository.engine.connect() as connection:
            before = connection.execute(
                text(
                    "SELECT count(*), min(artifact_sha256), max(artifact_sha256) "
                    "FROM point_in_time_qualification_runs"
                )
            ).one()
        artifact = workflow.create_assessment(request)
        assert workflow.create_assessment(request) == artifact
        assert workflow.get_assessment(artifact.assessment_id) == artifact
        with repository.engine.connect() as connection:
            after = connection.execute(
                text(
                    "SELECT count(*), min(artifact_sha256), max(artifact_sha256) "
                    "FROM point_in_time_qualification_runs"
                )
            ).one()
        assert after == before
    finally:
        repository.dispose()
        source_repository.dispose()


def test_postgres_concurrent_same_key_invokes_one_assessment_and_stores_one_graph() -> None:
    database_url = _require_postgres()
    source_repository = PointInTimeQualificationRepository(database_url)
    first = ResearchIngestionEligibilityRepository(database_url)
    second = ResearchIngestionEligibilityRepository(database_url)
    tag = f"concurrent-{uuid4().hex}"
    source = _mock_source(tag)
    source_repository.create_qualification(source)
    counting_source = _CountingQualificationSource(source_repository)
    request = ResearchIngestionEligibilityCreateRequest(
        assessment_idempotency_key=f"phase14-assessment-{tag}",
        qualification_id=source.qualification_id,
    )
    first_workflow = ResearchIngestionEligibilityWorkflow(
        qualification_source=counting_source,
        store=first,
        phase14_code_version_git_sha=CODE_VERSION_GIT_SHA,
    )
    second_workflow = ResearchIngestionEligibilityWorkflow(
        qualification_source=counting_source,
        store=second,
        phase14_code_version_git_sha=CODE_VERSION_GIT_SHA,
    )
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = tuple(
                future.result(timeout=30)
                for future in (
                    executor.submit(first_workflow.create_assessment, request),
                    executor.submit(second_workflow.create_assessment, request),
                )
            )
        assert results[0] == results[1]
        assert counting_source.calls == 1
        with first.engine.connect() as connection:
            counts = connection.execute(
                text(
                    "SELECT "
                    "(SELECT count(*) FROM research_ingestion_eligibility_assessments "
                    " WHERE assessment_idempotency_key = :key), "
                    "(SELECT count(*) FROM research_ingestion_eligibility_payloads "
                    " WHERE assessment_id = :assessment_id), "
                    "(SELECT count(*) FROM research_ingestion_eligibility_checks "
                    " WHERE assessment_id = :assessment_id)"
                ),
                {
                    "key": request.assessment_idempotency_key,
                    "assessment_id": results[0].assessment_id,
                },
            ).one()
        assert counts == (1, 6, 12)
    finally:
        second.dispose()
        first.dispose()
        source_repository.dispose()


def test_postgres_conflicting_key_and_semantic_fingerprint_reuse_fail_closed() -> None:
    database_url = _require_postgres()
    source_repository = PointInTimeQualificationRepository(database_url)
    repository = ResearchIngestionEligibilityRepository(database_url)
    first_source = _mock_source(f"conflict-a-{uuid4().hex}")
    second_source = _mock_source(f"conflict-b-{uuid4().hex}")
    source_repository.create_qualification(first_source)
    source_repository.create_qualification(second_source)
    workflow = ResearchIngestionEligibilityWorkflow(
        qualification_source=source_repository,
        store=repository,
        phase14_code_version_git_sha=CODE_VERSION_GIT_SHA,
    )
    key = f"phase14-conflict-{uuid4().hex}"
    first_request = ResearchIngestionEligibilityCreateRequest(
        assessment_idempotency_key=key,
        qualification_id=first_source.qualification_id,
    )
    try:
        original = workflow.create_assessment(first_request)
        with pytest.raises(
            ResearchIngestionEligibilityWorkflowConflict,
            match="idempotency key conflicts",
        ):
            workflow.create_assessment(
                ResearchIngestionEligibilityCreateRequest(
                    assessment_idempotency_key=key,
                    qualification_id=second_source.qualification_id,
                )
            )
        with pytest.raises(
            ResearchIngestionEligibilityWorkflowConflict,
            match="semantic fingerprint already has a different idempotency key",
        ):
            workflow.create_assessment(
                ResearchIngestionEligibilityCreateRequest(
                    assessment_idempotency_key=f"phase14-alternate-{uuid4().hex}",
                    qualification_id=first_source.qualification_id,
                )
            )
        assert repository.get_assessment(original.assessment_id) == original
    finally:
        repository.dispose()
        source_repository.dispose()


@pytest.mark.parametrize(
    ("builder_name", "field", "expected_error"),
    (
        ("_artifact_payload", "research_data_eligible", "root or source payload mismatch"),
        ("_eligibility_payload", "record_count", "eligibility payload mismatch"),
        ("_check_payload", "observed_value", "eligibility check payload mismatch"),
    ),
)
def test_postgres_root_and_child_payload_tamper_rolls_back_completely(
    monkeypatch: pytest.MonkeyPatch,
    builder_name: str,
    field: str,
    expected_error: str,
) -> None:
    database_url = _require_postgres()
    source_repository = PointInTimeQualificationRepository(database_url)
    repository = ResearchIngestionEligibilityRepository(database_url)
    tag = f"tamper-{builder_name}-{uuid4().hex}"
    source = _mock_source(tag)
    source_repository.create_qualification(source)
    builder_store: dict[str, ResearchIngestionEligibilityArtifact] = {}

    class _Store:
        @contextmanager
        def serialized_creation(self, key: str) -> Iterator[_Store]:
            del key
            yield self

        def find_by_idempotency_key(self, key: str) -> None:
            del key
            return None

        def find_by_request_fingerprint(self, fingerprint: str) -> None:
            del fingerprint
            return None

        def create_assessment(
            self, artifact: ResearchIngestionEligibilityArtifact
        ) -> ResearchIngestionEligibilityArtifact:
            builder_store["artifact"] = artifact
            return artifact

        def get_assessment(self, assessment_id: object) -> ResearchIngestionEligibilityArtifact:
            del assessment_id
            return builder_store["artifact"]

    artifact = ResearchIngestionEligibilityWorkflow(
        qualification_source=source_repository,
        store=_Store(),
        phase14_code_version_git_sha=CODE_VERSION_GIT_SHA,
    ).create_assessment(
        ResearchIngestionEligibilityCreateRequest(
            assessment_idempotency_key=f"phase14-assessment-{tag}",
            qualification_id=source.qualification_id,
        )
    )
    original_builder = getattr(repository_module, builder_name)

    def tampered_payload(value: object) -> dict[str, Any]:
        payload: dict[str, Any] = original_builder(value)
        if field == "research_data_eligible":
            payload[field] = True
        elif field == "record_count":
            payload[field] = int(payload[field]) + 1
        else:
            payload[field] = "tampered"
        return payload

    monkeypatch.setattr(repository_module, builder_name, tampered_payload)
    try:
        with pytest.raises(DBAPIError, match=expected_error):
            with repository.engine.begin() as connection:
                ResearchIngestionEligibilityRepository._insert_assessment(connection, artifact)
        assert repository.find_by_idempotency_key(artifact.assessment_idempotency_key) is None
    finally:
        repository.dispose()
        source_repository.dispose()


@pytest.mark.parametrize("ordinal", range(1, len(PHASE14_CHECK_ORDER) + 1))
def test_postgres_rejects_coherently_rehashed_source_policy_check_tamper(
    ordinal: int,
) -> None:
    database_url = _require_postgres()
    source_repository = PointInTimeQualificationRepository(database_url)
    repository = ResearchIngestionEligibilityRepository(database_url)
    tag = f"semantic-check-{ordinal}-{uuid4().hex}"
    source = _mock_source(tag)
    source_repository.create_qualification(source)
    builder = _EligibilityArtifactBuilderStore()
    artifact = ResearchIngestionEligibilityWorkflow(
        qualification_source=source_repository,
        store=builder,
        phase14_code_version_git_sha=CODE_VERSION_GIT_SHA,
    ).create_assessment(
        ResearchIngestionEligibilityCreateRequest(
            assessment_idempotency_key=f"phase14-assessment-{tag}",
            qualification_id=source.qualification_id,
        )
    )
    tampered = _coherently_rehash_check_tamper(artifact, ordinal=ordinal)
    try:
        with pytest.raises(DBAPIError, match="exact complete source-bound evidence"):
            with repository.engine.begin() as connection:
                ResearchIngestionEligibilityRepository._insert_assessment(connection, tampered)
        assert repository.find_by_idempotency_key(tampered.assessment_idempotency_key) is None
    finally:
        repository.dispose()
        source_repository.dispose()


def test_postgres_deferred_completeness_rejects_missing_payload_without_residue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = _require_postgres()
    source_repository = PointInTimeQualificationRepository(database_url)
    repository = ResearchIngestionEligibilityRepository(database_url)
    tag = f"missing-child-{uuid4().hex}"
    source = _mock_source(tag)
    source_repository.create_qualification(source)
    artifact = _create_assessment(
        tag=f"builder-{uuid4().hex}",
        source=_mock_source(f"builder-source-{uuid4().hex}"),
        source_repository=source_repository,
        repository=repository,
    )
    # Build a fresh semantic artifact with an in-memory store, then skip one child on insert.
    fresh_source = _mock_source(f"fresh-{uuid4().hex}")
    source_repository.create_qualification(fresh_source)
    holder: dict[str, ResearchIngestionEligibilityArtifact] = {}

    class _Store:
        @contextmanager
        def serialized_creation(self, key: str) -> Iterator[_Store]:
            del key
            yield self

        def find_by_idempotency_key(self, key: str) -> None:
            del key
            return None

        def find_by_request_fingerprint(self, fingerprint: str) -> None:
            del fingerprint
            return None

        def create_assessment(
            self, value: ResearchIngestionEligibilityArtifact
        ) -> ResearchIngestionEligibilityArtifact:
            holder["artifact"] = value
            return value

        def get_assessment(self, assessment_id: object) -> ResearchIngestionEligibilityArtifact:
            del assessment_id
            return holder["artifact"]

    fresh_artifact = ResearchIngestionEligibilityWorkflow(
        qualification_source=source_repository,
        store=_Store(),
        phase14_code_version_git_sha=CODE_VERSION_GIT_SHA,
    ).create_assessment(
        ResearchIngestionEligibilityCreateRequest(
            assessment_idempotency_key=f"phase14-missing-{uuid4().hex}",
            qualification_id=fresh_source.qualification_id,
        )
    )
    original_insert = repository_module._insert_row

    def incomplete_insert(
        connection: Connection,
        table: str,
        row: dict[str, Any],
        *,
        json_columns: frozenset[str] = frozenset(),
    ) -> None:
        if table != "research_ingestion_eligibility_payloads" or row["ordinal"] != 6:
            original_insert(connection, table, row, json_columns=json_columns)

    monkeypatch.setattr(repository_module, "_insert_row", incomplete_insert)
    try:
        with pytest.raises(DBAPIError, match="exact complete source-bound evidence"):
            with repository.engine.begin() as connection:
                ResearchIngestionEligibilityRepository._insert_assessment(
                    connection, fresh_artifact
                )
        assert repository.find_by_idempotency_key(fresh_artifact.assessment_idempotency_key) is None
        assert repository.get_assessment(artifact.assessment_id) == artifact
    finally:
        repository.dispose()
        source_repository.dispose()


def test_postgres_revalidates_tampered_phase13_source_before_any_phase14_insert() -> None:
    database_url = _require_postgres()
    source_repository = PointInTimeQualificationRepository(database_url)
    repository = ResearchIngestionEligibilityRepository(database_url)
    source = _mock_source(f"source-tamper-{uuid4().hex}")
    source_repository.create_qualification(source)
    holder: dict[str, ResearchIngestionEligibilityArtifact] = {}

    class _Store:
        @contextmanager
        def serialized_creation(self, key: str) -> Iterator[_Store]:
            del key
            yield self

        def find_by_idempotency_key(self, key: str) -> None:
            del key
            return None

        def find_by_request_fingerprint(self, fingerprint: str) -> None:
            del fingerprint
            return None

        def create_assessment(
            self, value: ResearchIngestionEligibilityArtifact
        ) -> ResearchIngestionEligibilityArtifact:
            holder["artifact"] = value
            return value

        def get_assessment(self, assessment_id: object) -> ResearchIngestionEligibilityArtifact:
            del assessment_id
            return holder["artifact"]

    artifact = ResearchIngestionEligibilityWorkflow(
        qualification_source=source_repository,
        store=_Store(),
        phase14_code_version_git_sha=CODE_VERSION_GIT_SHA,
    ).create_assessment(
        ResearchIngestionEligibilityCreateRequest(
            assessment_idempotency_key=f"phase14-source-tamper-{uuid4().hex}",
            qualification_id=source.qualification_id,
        )
    )
    try:
        with repository.engine.connect() as connection:
            transaction = connection.begin()
            try:
                connection.execute(
                    text(
                        "ALTER TABLE point_in_time_qualification_payloads "
                        "DISABLE TRIGGER point_in_time_qualification_payloads_90_append_only_row"
                    )
                )
                connection.execute(
                    text(
                        "UPDATE point_in_time_qualification_payloads "
                        "SET record_count = record_count + 1 "
                        "WHERE qualification_id = :qualification_id AND ordinal = 1"
                    ),
                    {"qualification_id": source.qualification_id},
                )
                with pytest.raises(
                    PointInTimeQualificationRepositoryConflict,
                    match="capability column record_count conflicts",
                ):
                    ResearchIngestionEligibilityRepository._insert_assessment(connection, artifact)
            finally:
                transaction.rollback()
        assert repository.find_by_idempotency_key(artifact.assessment_idempotency_key) is None
        assert source_repository.get_qualification(source.qualification_id) == source
    finally:
        repository.dispose()
        source_repository.dispose()


def test_postgres_phase14_rows_reject_update_delete_and_truncate() -> None:
    database_url = _require_postgres()
    source_repository = PointInTimeQualificationRepository(database_url)
    repository = ResearchIngestionEligibilityRepository(database_url)
    tag = f"immutable-{uuid4().hex}"
    source = _mock_source(tag)
    try:
        artifact = _create_assessment(
            tag=tag,
            source=source,
            source_repository=source_repository,
            repository=repository,
        )
        for table in (
            "research_ingestion_eligibility_assessments",
            "research_ingestion_eligibility_payloads",
            "research_ingestion_eligibility_checks",
        ):
            for statement in (
                text(
                    f"UPDATE {table} SET created_at_utc = created_at_utc "
                    "WHERE assessment_id = :assessment_id"
                ),
                text(f"DELETE FROM {table} WHERE assessment_id = :assessment_id"),
                text(f"TRUNCATE TABLE {table} CASCADE"),
            ):
                with pytest.raises(DBAPIError, match=APPEND_ONLY_ERROR):
                    with repository.engine.begin() as connection:
                        connection.execute(
                            statement,
                            {"assessment_id": artifact.assessment_id},
                        )
        assert repository.get_assessment(artifact.assessment_id) == artifact
    finally:
        repository.dispose()
        source_repository.dispose()


def test_postgres_unknown_fingerprint_lookup_is_nonrevealing() -> None:
    repository = ResearchIngestionEligibilityRepository(_require_postgres())
    try:
        assert repository.find_by_request_fingerprint("0" * 64) is None
    finally:
        repository.dispose()
