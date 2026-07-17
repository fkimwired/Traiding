from __future__ import annotations

import hashlib
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import fable5_paper.phase12.repository as repository_module
import pytest
from fable5_paper.phase12.adapters import DeterministicMockPaperBrokerAdapter
from fable5_paper.phase12.canonical import (
    PHASE12_ARTIFACT_HASH_DOMAIN,
    PHASE12_CHECK_HASH_DOMAIN,
    PHASE12_INSPECTION_HASH_DOMAIN,
    PHASE12_OBSERVATION_HASH_DOMAIN,
    PHASE12_RUN_NAMESPACE,
    PHASE12_TRANSPORT_PROFILE_SHA256,
    domain_sha256,
    identity,
)
from fable5_paper.phase12.contracts import (
    PHASE12_ARTIFACT_SCHEMA_VERSION,
    PHASE12_CHECK_ORDER,
    PHASE12_CHECK_SCHEMA_VERSION,
    PHASE12_DISCLAIMER,
    PHASE12_INSPECTION_ORDER,
    PHASE12_INSPECTION_SCHEMA_VERSION,
    PaperAccountObservation,
    PaperClockObservation,
    PaperInstrumentObservation,
    PaperInventoryObservation,
    PaperQuoteObservation,
    PaperShadowReadinessArtifact,
    PaperShadowReadinessCheck,
    PaperShadowReadinessCreateRequest,
    ReadinessCheckStatus,
    ReadinessInspectionEvidence,
    ReadinessInspectionStatus,
    ReadinessOutcome,
    ReadinessSourceKind,
    readiness_request_fingerprint,
)
from fable5_paper.phase12.repository import (
    PaperShadowReadinessRepository,
    PaperShadowReadinessRepositoryConflict,
)
from fable5_paper.phase12.workflow import PaperShadowReadinessWorkflow
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import DBAPIError

DATABASE_URL = os.environ.get("FABLE5_TEST_DATABASE_URL")
CODE_VERSION_GIT_SHA = os.environ.get("FABLE5_CODE_VERSION_GIT_SHA", "a" * 40)
APPEND_ONLY_ERROR = "Phase 12 paper shadow-readiness artifacts are append-only"


def _observation(model: type[Any], **payload: object) -> Any:
    return model.model_validate(
        {
            **payload,
            "observation_sha256": domain_sha256(PHASE12_OBSERVATION_HASH_DOMAIN, payload),
        }
    )


def _mock_artifact(
    tag: str, *, git_sha: str = CODE_VERSION_GIT_SHA
) -> PaperShadowReadinessArtifact:
    completed = datetime.now(UTC) - timedelta(seconds=1)
    started = completed - timedelta(seconds=6)
    empty_inventory_hash = hashlib.sha256(b"[]").hexdigest()
    account = _observation(
        PaperAccountObservation,
        schema_version="phase12-paper-account-observation-v1",
        status="ACTIVE",
        account_blocked=False,
        trading_blocked=False,
        trade_suspended_by_user=False,
    )
    clock = _observation(
        PaperClockObservation,
        schema_version="phase12-paper-clock-observation-v1",
        is_open=True,
        provider_timestamp_utc=completed,
        next_open_utc=completed + timedelta(days=1),
        next_close_utc=completed + timedelta(hours=6),
    )
    instrument = _observation(
        PaperInstrumentObservation,
        schema_version="phase12-paper-instrument-observation-v1",
        asset_id=UUID("b0b6dd9d-8b9b-48a9-ba46-b9d54906e415"),
        symbol="AAPL",
        exchange="NASDAQ",
        status="ACTIVE",
        active=True,
        tradable=True,
    )
    positions = _observation(
        PaperInventoryObservation,
        schema_version="phase12-paper-inventory-observation-v1",
        inventory_kind="POSITIONS",
        item_count=0,
        inventory_sha256=empty_inventory_hash,
    )
    open_orders = _observation(
        PaperInventoryObservation,
        schema_version="phase12-paper-inventory-observation-v1",
        inventory_kind="OPEN_ORDERS",
        item_count=0,
        inventory_sha256=empty_inventory_hash,
    )
    latest_quote = _observation(
        PaperQuoteObservation,
        schema_version="phase12-paper-quote-observation-v1",
        symbol="AAPL",
        feed="iex",
        event_time_utc=completed - timedelta(seconds=1),
        received_at_utc=completed,
        age_seconds=Decimal("1"),
        freshness_ttl_seconds=60,
        fresh=True,
        bid_price_valid=True,
        ask_price_valid=True,
        non_crossed=True,
    )
    observations = (account, clock, instrument, positions, open_orders, latest_quote)
    inspections: list[ReadinessInspectionEvidence] = []
    for ordinal, (code, observed) in enumerate(
        zip(PHASE12_INSPECTION_ORDER, observations, strict=True),
        start=1,
    ):
        payload = {
            "schema_version": PHASE12_INSPECTION_SCHEMA_VERSION,
            "ordinal": ordinal,
            "code": code,
            "status": ReadinessInspectionStatus.OBSERVED,
            "method": "GET",
            "external_request_performed": False,
            "request_started_at_utc": started + timedelta(seconds=ordinal - 1),
            "request_completed_at_utc": started + timedelta(seconds=ordinal),
            "http_status": None,
            "request_id": None,
            "response_sha256": None,
            "observation_sha256": observed.observation_sha256,
            "failure_reason": None,
        }
        inspections.append(
            ReadinessInspectionEvidence.model_validate(
                {
                    **payload,
                    "inspection_sha256": domain_sha256(
                        PHASE12_INSPECTION_HASH_DOMAIN,
                        payload,
                    ),
                }
            )
        )
    evidence = (
        PHASE12_TRANSPORT_PROFILE_SHA256,
        PHASE12_TRANSPORT_PROFILE_SHA256,
        account.observation_sha256,
        clock.observation_sha256,
        instrument.observation_sha256,
        positions.observation_sha256,
        open_orders.observation_sha256,
        latest_quote.observation_sha256,
    )
    checks: list[PaperShadowReadinessCheck] = []
    for ordinal, (code, evidence_sha256) in enumerate(
        zip(PHASE12_CHECK_ORDER, evidence, strict=True),
        start=1,
    ):
        payload = {
            "schema_version": PHASE12_CHECK_SCHEMA_VERSION,
            "ordinal": ordinal,
            "code": code,
            "status": ReadinessCheckStatus.PASS,
            "reason_code": f"{code.value.lower()}_passed",
            "observed_value": "ready",
            "threshold_value": "required",
            "evidence_sha256s": (evidence_sha256,),
        }
        checks.append(
            PaperShadowReadinessCheck.model_validate(
                {
                    **payload,
                    "check_sha256": domain_sha256(PHASE12_CHECK_HASH_DOMAIN, payload),
                }
            )
        )
    request = PaperShadowReadinessCreateRequest(readiness_idempotency_key=f"phase12-postgres-{tag}")
    fingerprint = readiness_request_fingerprint(
        request=request,
        source_kind=ReadinessSourceKind.DETERMINISTIC_MOCK,
        transport_profile_sha256=PHASE12_TRANSPORT_PROFILE_SHA256,
        phase12_code_version_git_sha=git_sha,
    )
    payload = {
        "artifact_schema_version": PHASE12_ARTIFACT_SCHEMA_VERSION,
        "request_fingerprint_sha256": fingerprint,
        "readiness_idempotency_key": request.readiness_idempotency_key,
        "source_kind": ReadinessSourceKind.DETERMINISTIC_MOCK,
        "transport_profile_sha256": PHASE12_TRANSPORT_PROFILE_SHA256,
        "inspections": tuple(inspections),
        "account": account,
        "clock": clock,
        "instrument": instrument,
        "positions": positions,
        "open_orders": open_orders,
        "latest_quote": latest_quote,
        "checks": tuple(checks),
        "outcome": ReadinessOutcome.MOCK_PROOF_COMPLETE,
        "reason_codes": ("all_mock_readiness_checks_passed",),
        "phase12_code_version_git_sha": git_sha,
        "assessment_started_at_utc": started,
        "assessment_completed_at_utc": completed,
        "expires_at_utc": completed + timedelta(seconds=60),
        "order_submission_authorized": False,
        "strategy_execution_eligible": False,
        "live_path_absent": True,
        "no_personalized_investment_advice": True,
        "no_real_performance_claimed": True,
        "disclaimer": PHASE12_DISCLAIMER,
    }
    return PaperShadowReadinessArtifact.model_validate(
        {
            **payload,
            "readiness_assessment_id": identity(PHASE12_RUN_NAMESPACE, fingerprint),
            "artifact_sha256": domain_sha256(PHASE12_ARTIFACT_HASH_DOMAIN, payload),
        }
    )


def _require_postgres() -> str:
    if DATABASE_URL is None:
        pytest.skip("Phase 12 PostgreSQL URL is unavailable")
    return DATABASE_URL


def test_phase12_repository_structurally_exposes_only_readiness_persistence() -> None:
    repository = PaperShadowReadinessRepository("sqlite+pysqlite:///:memory:")
    try:
        for method in (
            "serialized_creation",
            "find_by_idempotency_key",
            "create_readiness",
            "get_readiness",
            "dispose",
        ):
            assert callable(getattr(repository, method))
        for forbidden in ("submit_order", "replace_order", "cancel_order", "close_position"):
            assert not hasattr(repository, forbidden)
    finally:
        repository.dispose()


def test_postgres_roundtrip_and_repeat_preserve_exact_hash_bound_children() -> None:
    repository = PaperShadowReadinessRepository(_require_postgres())
    artifact = _mock_artifact(f"roundtrip-{uuid4().hex}")
    try:
        persisted = repository.create_readiness(artifact)
        assert persisted == artifact
        assert repository.create_readiness(artifact) == artifact
        assert repository.get_readiness(artifact.readiness_assessment_id) == artifact
        assert repository.find_by_idempotency_key(artifact.readiness_idempotency_key) == artifact
        with repository.engine.connect() as connection:
            assert connection.scalar(
                text(
                    "SELECT count(*) FROM paper_shadow_readiness_checks "
                    "WHERE readiness_assessment_id = :assessment_id"
                ),
                {"assessment_id": artifact.readiness_assessment_id},
            ) == len(PHASE12_CHECK_ORDER)
    finally:
        repository.dispose()


def test_postgres_deterministic_mock_workflow_persists_historical_proof() -> None:
    repository = PaperShadowReadinessRepository(_require_postgres())
    workflow = PaperShadowReadinessWorkflow(
        adapter=DeterministicMockPaperBrokerAdapter(),
        store=repository,
        phase12_code_version_git_sha=CODE_VERSION_GIT_SHA,
    )
    request = PaperShadowReadinessCreateRequest(
        readiness_idempotency_key=f"phase12-postgres-workflow-{uuid4().hex}"
    )
    try:
        artifact = workflow.create_readiness(request)
        assert artifact.outcome is ReadinessOutcome.MOCK_PROOF_COMPLETE
        assert artifact.assessment_completed_at_utc.year == 2024
        assert workflow.create_readiness(request) == artifact
        assert repository.get_readiness(artifact.readiness_assessment_id) == artifact
    finally:
        repository.dispose()


def test_postgres_two_writers_store_one_complete_idempotent_bundle() -> None:
    database_url = _require_postgres()
    first = PaperShadowReadinessRepository(database_url)
    second = PaperShadowReadinessRepository(database_url)
    artifact = _mock_artifact(f"concurrent-{uuid4().hex}")
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = tuple(
                future.result(timeout=30)
                for future in (
                    executor.submit(first.create_readiness, artifact),
                    executor.submit(second.create_readiness, artifact),
                )
            )
        assert results == (artifact, artifact)
        with first.engine.connect() as connection:
            assert (
                connection.scalar(
                    text(
                        "SELECT count(*) FROM paper_shadow_readiness_runs "
                        "WHERE readiness_idempotency_key = :key"
                    ),
                    {"key": artifact.readiness_idempotency_key},
                )
                == 1
            )
            assert connection.scalar(
                text(
                    "SELECT count(*) FROM paper_shadow_readiness_checks "
                    "WHERE readiness_assessment_id = :assessment_id"
                ),
                {"assessment_id": artifact.readiness_assessment_id},
            ) == len(PHASE12_CHECK_ORDER)
    finally:
        second.dispose()
        first.dispose()


def test_postgres_same_key_with_different_fingerprint_conflicts() -> None:
    repository = PaperShadowReadinessRepository(_require_postgres())
    tag = f"conflict-{uuid4().hex}"
    original = _mock_artifact(tag)
    alternate_sha = "b" * 40 if CODE_VERSION_GIT_SHA != "b" * 40 else "c" * 40
    conflicting = _mock_artifact(tag, git_sha=alternate_sha)
    try:
        assert repository.create_readiness(original) == original
        with pytest.raises(
            PaperShadowReadinessRepositoryConflict,
            match="different request fingerprint",
        ):
            repository.create_readiness(conflicting)
        assert repository.find_by_idempotency_key(original.readiness_idempotency_key) == original
    finally:
        repository.dispose()


def test_postgres_deferred_completeness_rolls_back_a_missing_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = PaperShadowReadinessRepository(_require_postgres())
    artifact = _mock_artifact(f"incomplete-{uuid4().hex}")
    original_insert = repository_module._insert_row

    def incomplete_insert(
        connection: Connection,
        table: str,
        row: dict[str, Any],
        *,
        json_columns: frozenset[str] = frozenset(),
    ) -> None:
        if table != "paper_shadow_readiness_checks" or row["ordinal"] != 8:
            original_insert(connection, table, row, json_columns=json_columns)

    monkeypatch.setattr(repository_module, "_insert_row", incomplete_insert)
    try:
        with pytest.raises(DBAPIError, match="exact complete ordered checks"):
            with repository.engine.begin() as connection:
                PaperShadowReadinessRepository._insert_readiness(connection, artifact)
        assert repository.find_by_idempotency_key(artifact.readiness_idempotency_key) is None
    finally:
        repository.dispose()


def test_postgres_phase12_rows_reject_update_delete_and_truncate() -> None:
    repository = PaperShadowReadinessRepository(_require_postgres())
    artifact = _mock_artifact(f"immutable-{uuid4().hex}")
    try:
        repository.create_readiness(artifact)
        for table in ("paper_shadow_readiness_runs", "paper_shadow_readiness_checks"):
            for statement in (
                text(
                    f"UPDATE {table} SET created_at_utc = created_at_utc "
                    "WHERE readiness_assessment_id = :assessment_id"
                ),
                text(f"DELETE FROM {table} WHERE readiness_assessment_id = :assessment_id"),
                text(f"TRUNCATE TABLE {table} CASCADE"),
            ):
                with pytest.raises(DBAPIError, match=APPEND_ONLY_ERROR):
                    with repository.engine.begin() as connection:
                        connection.execute(
                            statement,
                            {"assessment_id": artifact.readiness_assessment_id},
                        )
        assert repository.get_readiness(artifact.readiness_assessment_id) == artifact
    finally:
        repository.dispose()
