from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from threading import Barrier, get_ident
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from fable5_data.contracts import (
    DataCapability,
    SnapshotRequestParameters,
)
from fable5_data.quality import (
    QualityAcceptedResult,
    QualityReferenceCatalog,
    run_mandatory_data_quality,
)
from fable5_data.repository import (
    MappingNotFound,
    SnapshotAuthorization,
    SnapshotConflict,
    SnapshotRepository,
    _candidate_storage,
    _insert_rows,
)
from fable5_data.snapshots import SnapshotCandidate, build_snapshot_candidate
from fable5_data.synthetic import (
    SYNTHETIC_MOCK_CONFIGURATION,
    SyntheticPointInTimeAdapter,
    load_fixture_records,
)
from fable5_extraction.extractor import default_extraction_profile
from fable5_extraction.models import (
    AuthorityVerificationMethod,
    SourceAuthority,
    SourceIntakeRequest,
    SourceType,
)
from fable5_extraction.repository import IdeaRepository
from fable5_extraction.workflow import process_extraction
from fable5_mapping.models import (
    CanonicalFamily,
    MappingWithRationale,
    ResearchVerdict,
)
from fable5_mapping.repository import MappingRepository
from sqlalchemy import event, text
from sqlalchemy.exc import DBAPIError

DATABASE_URL = os.environ.get("FABLE5_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    DATABASE_URL is None,
    reason="set FABLE5_TEST_DATABASE_URL to an isolated PostgreSQL database",
)

AS_OF = datetime(2024, 1, 3, tzinfo=UTC)
PHASE4_TABLES = (
    "data_snapshots",
    "data_raw_observations",
    "data_observation_revisions",
    "data_normalized_observations",
    "data_snapshot_constituents",
    "data_quality_findings",
    "data_snapshot_manifests",
)
HEADER_JSON_COLUMNS = frozenset(
    {
        "request_fingerprint_payload",
        "official_corroboration_source_version_ids",
        "capabilities",
        "schema_bindings",
    }
)


def _upgrade_head(database_url: str) -> None:
    prior = os.environ.get("FABLE5_DATABASE_URL")
    os.environ["FABLE5_DATABASE_URL"] = database_url
    try:
        command.upgrade(Config("services/api/alembic.ini"), "head")
    finally:
        if prior is None:
            os.environ.pop("FABLE5_DATABASE_URL", None)
        else:
            os.environ["FABLE5_DATABASE_URL"] = prior


def _create_mapping(
    ideas: IdeaRepository,
    mappings: MappingRepository,
    *,
    key: str,
    raw_text: str,
    authority: SourceAuthority = SourceAuthority.OTHER,
    official_corroborations: tuple[UUID, ...] = (),
) -> MappingWithRationale:
    _, source = ideas.create_source(
        SourceIntakeRequest(
            source_type=SourceType.SYNTHETIC_FIXTURE,
            source_authority=authority,
            raw_text=raw_text,
            official_corroboration_source_version_ids=official_corroborations,
            ingest_idempotency_key=key,
        )
    )
    request = ideas.create_extraction_request(
        source.source_version_id,
        default_extraction_profile(),
    )
    card = process_extraction(ideas, request.extraction_request_id)
    return mappings.create_mapping(card.card_id)


def _family_a_mapping(
    ideas: IdeaRepository,
    mappings: MappingRepository,
    *,
    key: str,
) -> MappingWithRationale:
    result = _create_mapping(
        ideas,
        mappings,
        key=key,
        raw_text=(
            "Rank stocks in a point-in-time universe and select the top-ranked group when "
            "scores are refreshed weekly. Include delisting-aware returns and liquid shares."
        ),
    )
    assert result.mapping.canonical_family is CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING
    assert result.mapping.verdict is ResearchVerdict.BUILD_RESEARCH
    return result


def _family_c_mapping(
    ideas: IdeaRepository,
    mappings: MappingRepository,
    *,
    key: str,
) -> tuple[MappingWithRationale, UUID]:
    _, official = ideas.create_source(
        SourceIntakeRequest(
            source_type=SourceType.SYNTHETIC_FIXTURE,
            source_authority=SourceAuthority.OFFICIAL,
            authority_verification_method=AuthorityVerificationMethod.SYNTHETIC_FIXTURE,
            raw_text="Official issuer event evidence.",
            ingest_idempotency_key=f"{key}-official",
        )
    )
    result = _create_mapping(
        ideas,
        mappings,
        key=f"{key}-social",
        authority=SourceAuthority.SOCIAL,
        official_corroborations=(official.source_version_id,),
        raw_text=(
            "If social attention changes around an issuer event, evaluate the next day stock claim."
        ),
    )
    assert result.mapping.canonical_family is CanonicalFamily.C_OFFICIAL_EVENT_TEXT_OVERLAY
    assert result.mapping.verdict is ResearchVerdict.BUILD_RESEARCH
    return result, official.source_version_id


def _candidate(
    repository: SnapshotRepository,
    mapping_id: UUID,
    capability: DataCapability,
    *,
    as_of_utc: datetime = AS_OF,
    adapter: SyntheticPointInTimeAdapter | None = None,
    quality_gate: bool = False,
) -> SnapshotCandidate:
    adapter = adapter or SyntheticPointInTimeAdapter()
    mapping = repository.resolve_mapping(mapping_id, capability)
    request = SnapshotRequestParameters(
        mapping=mapping,
        as_of_utc=as_of_utc,
        capability=capability,
        mock_configuration_id=SYNTHETIC_MOCK_CONFIGURATION.configuration_id,
    )
    result = adapter.fetch(capability)
    batch = result.batch
    if quality_gate:
        accepted = run_mandatory_data_quality(
            request=request,
            result=result,
            configuration=SYNTHETIC_MOCK_CONFIGURATION,
            catalog=QualityReferenceCatalog.from_results(adapter.all_results()),
        )
        assert isinstance(accepted, QualityAcceptedResult)
        batch = accepted.batch
    materialized = build_snapshot_candidate(
        mapping=mapping,
        request=request,
        profile=result.profile,
        configuration=SYNTHETIC_MOCK_CONFIGURATION,
        batch=batch,
        created_at_utc=as_of_utc,
    )
    assert isinstance(materialized, SnapshotCandidate)
    return materialized


def _insert_header(connection: object, candidate: SnapshotCandidate) -> None:
    storage = _candidate_storage(candidate)
    header = dict(storage.header)
    header.pop("created_at_utc")
    _insert_rows(
        connection,  # type: ignore[arg-type]
        "data_snapshots",
        (header,),
        json_columns=HEADER_JSON_COLUMNS,
    )


def _repositories() -> tuple[IdeaRepository, MappingRepository, SnapshotRepository]:
    assert DATABASE_URL is not None
    _upgrade_head(DATABASE_URL)
    return (
        IdeaRepository(DATABASE_URL),
        MappingRepository(DATABASE_URL),
        SnapshotRepository(DATABASE_URL),
    )


def test_phase4_postgres_round_trip_idempotency_revision_replay_and_hash_sensitivity() -> None:
    ideas, mappings, snapshots = _repositories()
    unique = uuid4().hex
    try:
        mapping = _family_a_mapping(ideas, mappings, key=f"phase4-roundtrip-{unique}")
        mapping_id = mapping.mapping.mapping_id
        first_candidate = _candidate(snapshots, mapping_id, DataCapability.OHLCV)

        insert_started_at = datetime.now(UTC)
        first = snapshots.create_snapshot(first_candidate)
        insert_finished_at = datetime.now(UTC)
        repeated = snapshots.create_snapshot(first_candidate)
        loaded = snapshots.get_snapshot(first.snapshot.snapshot_id)
        listed = snapshots.list_snapshots(mapping_id=mapping_id)

        assert repeated == first
        assert loaded == first
        assert [item.snapshot.snapshot_id for item in listed] == [first.snapshot.snapshot_id]
        assert first.snapshot.snapshot_sha256 == first_candidate.snapshot_sha256
        assert insert_started_at <= first.snapshot.created_at_utc <= insert_finished_at
        assert repeated.snapshot.created_at_utc == first.snapshot.created_at_utc

        fundamentals_candidate = _candidate(
            snapshots,
            mapping_id,
            DataCapability.AS_REPORTED_FUNDAMENTALS,
            as_of_utc=datetime(2023, 1, 1, tzinfo=UTC),
        )
        fundamentals = snapshots.create_snapshot(fundamentals_candidate)
        revisions = sorted(
            (item.revision_sequence, item.predecessor_revision_record_id)
            for item in fundamentals.revisions
        )
        assert [sequence for sequence, _ in revisions] == [1, 2]
        assert revisions[0][1] is None
        assert revisions[1][1] is not None
        assert {item.revision_id for item in fundamentals.constituents} == {
            "fundamental-revenue-2019-r1",
            "fundamental-revenue-2019-r2",
        }

        changed_candidate = _candidate(
            snapshots,
            mapping_id,
            DataCapability.OHLCV,
            as_of_utc=AS_OF + timedelta(seconds=1),
        )
        changed = snapshots.create_snapshot(changed_candidate)
        assert changed.snapshot.snapshot_id != first.snapshot.snapshot_id
        assert changed.snapshot.snapshot_sha256 != first.snapshot.snapshot_sha256
        assert (
            changed.snapshot.manifest.payload.request_fingerprint_sha256
            != first.snapshot.manifest.payload.request_fingerprint_sha256
        )
    finally:
        snapshots.dispose()
        mappings.dispose()
        ideas.dispose()


def test_phase4_postgres_family_c_exact_corroboration_and_fail_closed_authorization() -> None:
    ideas, mappings, snapshots = _repositories()
    unique = uuid4().hex
    try:
        family_c, official_id = _family_c_mapping(
            ideas,
            mappings,
            key=f"phase4-family-c-{unique}",
        )
        records = list(load_fixture_records())
        official_record = next(
            item
            for item in records
            if item["capability"] == DataCapability.OFFICIAL_DOCUMENT_EVENT_METADATA.value
        )
        payload = deepcopy(official_record["payload"])
        assert isinstance(payload, dict)
        payload["official_source_version_id"] = str(official_id)
        official_record["payload"] = payload
        adapter = SyntheticPointInTimeAdapter(tuple(records))
        candidate = _candidate(
            snapshots,
            family_c.mapping.mapping_id,
            DataCapability.OFFICIAL_DOCUMENT_EVENT_METADATA,
            adapter=adapter,
            quality_gate=True,
        )
        persisted = snapshots.create_snapshot(candidate)
        manifest_mapping = persisted.snapshot.manifest.payload.mapping
        assert manifest_mapping.official_corroboration_source_version_ids == (official_id,)
        assert (
            persisted.normalized_observations[0].payload.official_source_version_id == official_id
        )

        unauthorized = _create_mapping(
            ideas,
            mappings,
            key=f"phase4-uncorroborated-{unique}",
            authority=SourceAuthority.SOCIAL,
            raw_text=(
                "If Reddit attention rises around an issuer event, the post claims news "
                "sentiment predicts the next day for stocks."
            ),
        )
        assert unauthorized.mapping.verdict is ResearchVerdict.DEFER
        with pytest.raises(SnapshotAuthorization, match="not authorized"):
            snapshots.resolve_mapping(
                unauthorized.mapping.mapping_id,
                DataCapability.OFFICIAL_DOCUMENT_EVENT_METADATA,
            )
        resolved_ohlcv = snapshots.resolve_mapping(
            family_c.mapping.mapping_id,
            DataCapability.OHLCV,
        )
        assert resolved_ohlcv.mapping_id == family_c.mapping.mapping_id
        assert resolved_ohlcv.canonical_family is CanonicalFamily.C_OFFICIAL_EVENT_TEXT_OVERLAY
        with pytest.raises(SnapshotAuthorization, match="not authorized"):
            snapshots.resolve_mapping(
                family_c.mapping.mapping_id,
                DataCapability.CORPORATE_ACTIONS,
            )
        with pytest.raises(MappingNotFound, match="was not found"):
            snapshots.resolve_mapping(uuid4(), DataCapability.OHLCV)
    finally:
        snapshots.dispose()
        mappings.dispose()
        ideas.dispose()


def test_phase4_postgres_concurrent_identical_is_one_row_and_changed_output_conflicts() -> None:
    ideas, mappings, snapshots = _repositories()
    unique = uuid4().hex
    try:
        mapping = _family_a_mapping(ideas, mappings, key=f"phase4-concurrent-{unique}")
        candidate = _candidate(snapshots, mapping.mapping.mapping_id, DataCapability.OHLCV)
        repositories = (SnapshotRepository(DATABASE_URL), SnapshotRepository(DATABASE_URL))
        barrier = Barrier(2)

        def worker(index: int) -> tuple[int, UUID]:
            barrier.wait(timeout=15)
            bundle = repositories[index].create_snapshot(candidate)
            return get_ident(), bundle.snapshot.snapshot_id

        try:
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = [executor.submit(worker, index) for index in range(2)]
                results = [future.result(timeout=30) for future in futures]
        finally:
            for repository in repositories:
                repository.dispose()

        assert len({thread_id for thread_id, _ in results}) == 2
        assert {snapshot_id for _, snapshot_id in results} == {candidate.snapshot_id}
        with snapshots.engine.connect() as connection:
            count = connection.execute(
                text(
                    "SELECT count(*) FROM data_snapshots "
                    "WHERE request_fingerprint_sha256 = :fingerprint"
                ),
                {"fingerprint": candidate.request_fingerprint_sha256},
            ).scalar_one()
        assert count == 1

        records = list(load_fixture_records())
        bar = next(item for item in records if item["alias"] == "bar_adjusted")
        payload = deepcopy(bar["payload"])
        assert isinstance(payload, dict)
        payload["volume"] = int(payload["volume"]) + 1
        bar["payload"] = payload
        changed_adapter = SyntheticPointInTimeAdapter(tuple(records))
        changed = _candidate(
            snapshots,
            mapping.mapping.mapping_id,
            DataCapability.OHLCV,
            adapter=changed_adapter,
        )
        assert changed.request_fingerprint_sha256 == candidate.request_fingerprint_sha256
        assert changed.snapshot_sha256 != candidate.snapshot_sha256
        with pytest.raises(SnapshotConflict, match="different snapshot hash"):
            snapshots.create_snapshot(changed)
    finally:
        snapshots.dispose()
        mappings.dispose()
        ideas.dispose()


def test_phase4_postgres_database_lineage_guards_and_required_finalization() -> None:
    ideas, mappings, snapshots = _repositories()
    unique = uuid4().hex
    try:
        mapping = _family_a_mapping(ideas, mappings, key=f"phase4-guards-{unique}")
        candidate = _candidate(snapshots, mapping.mapping.mapping_id, DataCapability.OHLCV)
        storage = _candidate_storage(candidate)

        spoofed = dict(storage.header)
        spoofed.pop("created_at_utc")
        spoofed["mapping_version"] += 1
        with snapshots.engine.connect() as connection:
            with pytest.raises(DBAPIError, match="persisted mapping lineage mismatch"):
                _insert_rows(
                    connection,
                    "data_snapshots",
                    (spoofed,),
                    json_columns=HEADER_JSON_COLUMNS,
                )
            connection.rollback()

        with snapshots.engine.connect() as connection:
            transaction = connection.begin()
            _insert_header(connection, candidate)
            mutated_raw = dict(storage.raw_observations[0])
            mutated_raw["raw_payload"] = b"different exact bytes"
            with pytest.raises(DBAPIError, match="raw payload hash does not match exact bytes"):
                _insert_rows(
                    connection,
                    "data_raw_observations",
                    (mutated_raw,),
                    json_columns=frozenset({"quality_flags", "field_missingness"}),
                )
            transaction.rollback()

        with snapshots.engine.connect() as connection:
            transaction = connection.begin()
            _insert_header(connection, candidate)
            with pytest.raises(DBAPIError, match="normalized raw observation was not found"):
                _insert_rows(
                    connection,
                    "data_normalized_observations",
                    (storage.normalized_observations[0],),
                    json_columns=frozenset({"payload", "quality_flags", "field_missingness"}),
                )
            transaction.rollback()

        with snapshots.engine.connect() as connection:
            transaction = connection.begin()
            _insert_header(connection, candidate)
            future_raw = dict(storage.raw_observations[0])
            future_raw["available_at"] = AS_OF + timedelta(seconds=1)
            future_raw["retrieved_at"] = AS_OF + timedelta(seconds=2)
            with pytest.raises(DBAPIError, match="future-available observation is ineligible"):
                _insert_rows(
                    connection,
                    "data_raw_observations",
                    (future_raw,),
                    json_columns=frozenset({"quality_flags", "field_missingness"}),
                )
            transaction.rollback()

        with snapshots.engine.connect() as connection:
            transaction = connection.begin()
            _insert_header(connection, candidate)
            with pytest.raises(DBAPIError, match="cannot commit without a manifest"):
                transaction.commit()

        rollback_candidate = _candidate(
            snapshots,
            mapping.mapping.mapping_id,
            DataCapability.CORPORATE_ACTIONS,
        )

        def fail_before_revision_insert(
            _connection: object,
            _cursor: object,
            statement: str,
            _parameters: object,
            _context: object,
            _executemany: bool,
        ) -> None:
            if statement.startswith("INSERT INTO data_observation_revisions"):
                raise RuntimeError("injected repository persistence failure")

        event.listen(snapshots.engine, "before_cursor_execute", fail_before_revision_insert)
        try:
            with pytest.raises(RuntimeError, match="injected repository persistence failure"):
                snapshots.create_snapshot(rollback_candidate)
        finally:
            event.remove(
                snapshots.engine,
                "before_cursor_execute",
                fail_before_revision_insert,
            )
        with snapshots.engine.connect() as connection:
            rolled_back = connection.execute(
                text(
                    "SELECT count(*) FROM data_snapshots "
                    "WHERE request_fingerprint_sha256 = :fingerprint"
                ),
                {"fingerprint": rollback_candidate.request_fingerprint_sha256},
            ).scalar_one()
        assert rolled_back == 0
    finally:
        snapshots.dispose()
        mappings.dispose()
        ideas.dispose()


def test_phase4_postgres_all_tables_reject_update_delete_and_truncate() -> None:
    ideas, mappings, snapshots = _repositories()
    unique = uuid4().hex
    try:
        mapping = _family_a_mapping(ideas, mappings, key=f"phase4-immutable-{unique}")
        candidate = _candidate(
            snapshots,
            mapping.mapping.mapping_id,
            DataCapability.OHLCV,
            as_of_utc=datetime(2021, 1, 1, tzinfo=UTC),
            quality_gate=True,
        )
        persisted = snapshots.create_snapshot(candidate)
        snapshot_id = persisted.snapshot.snapshot_id
        assert persisted.quality_findings

        for table in PHASE4_TABLES:
            for statement in (
                f"UPDATE {table} SET snapshot_id = snapshot_id WHERE snapshot_id = :snapshot_id",
                f"DELETE FROM {table} WHERE snapshot_id = :snapshot_id",
                f"TRUNCATE {table} CASCADE",
            ):
                with snapshots.engine.connect() as connection:
                    with pytest.raises(DBAPIError, match="append-only"):
                        connection.execute(text(statement), {"snapshot_id": snapshot_id})
                    connection.rollback()
    finally:
        snapshots.dispose()
        mappings.dispose()
        ideas.dispose()
