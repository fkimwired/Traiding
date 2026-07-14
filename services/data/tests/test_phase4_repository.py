from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import pytest
from fable5_data.contracts import (
    AuthorizedMappingIdentity,
    DataCapability,
    SnapshotRequestParameters,
)
from fable5_data.repository import (
    MappingNotFound,
    SnapshotAuthorization,
    SnapshotConflict,
    SnapshotLineage,
    SnapshotNotFound,
    SnapshotRepository,
    _assert_candidate_mapping,
    _authorize_mapping,
    _bundle_from_storage,
    _candidate_storage,
)
from fable5_data.snapshots import SnapshotCandidate, build_snapshot_candidate
from fable5_data.synthetic import (
    SYNTHETIC_MOCK_CONFIGURATION,
    SyntheticPointInTimeAdapter,
)
from fable5_mapping.models import CanonicalFamily, ResearchVerdict

AS_OF = datetime(2024, 1, 3, tzinfo=UTC)
MAPPING_ID = UUID("aaaaaaaa-aaaa-5aaa-8aaa-aaaaaaaaaaaa")
CORROBORATION_ID = UUID("cccccccc-cccc-5ccc-8ccc-cccccccccccc")


def _mapping(
    family: CanonicalFamily = CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING,
    *,
    mapping_id: UUID = MAPPING_ID,
    version: int = 1,
    corroborations: tuple[UUID, ...] = (),
) -> AuthorizedMappingIdentity:
    return AuthorizedMappingIdentity(
        mapping_id=mapping_id,
        mapping_version=version,
        mapping_input_sha256="a" * 64,
        mapper_rule_set_version="phase3-canon-mapping-v1",
        mapper_rule_set_sha256="b" * 64,
        canonical_family=family,
        verdict=ResearchVerdict.BUILD_RESEARCH,
        official_corroboration_source_version_ids=corroborations,
    )


def _candidate(
    capability: DataCapability = DataCapability.OHLCV,
    *,
    mapping: AuthorizedMappingIdentity | None = None,
    as_of_utc: datetime = AS_OF,
) -> SnapshotCandidate:
    if mapping is None:
        mapping = _mapping()
    result = SyntheticPointInTimeAdapter().fetch(capability)
    materialized = build_snapshot_candidate(
        mapping=mapping,
        request=SnapshotRequestParameters(
            mapping=mapping,
            as_of_utc=as_of_utc,
            capability=capability,
            mock_configuration_id=SYNTHETIC_MOCK_CONFIGURATION.configuration_id,
        ),
        profile=result.profile,
        configuration=SYNTHETIC_MOCK_CONFIGURATION,
        batch=result.batch,
        created_at_utc=AS_OF,
    )
    assert isinstance(materialized, SnapshotCandidate)
    return materialized


def test_candidate_storage_round_trip_maps_every_bound_contract_field_without_loss() -> None:
    candidate = _candidate()
    storage = _candidate_storage(candidate)

    assert set(type(candidate.bundle.raw_observations[0]).model_fields) <= set(
        storage.raw_observations[0]
    )
    assert set(type(candidate.bundle.revisions[0]).model_fields) <= set(storage.revisions[0])
    assert set(type(candidate.bundle.normalized_observations[0]).model_fields) <= set(
        storage.normalized_observations[0]
    )
    assert set(type(candidate.bundle.constituents[0]).model_fields) <= set(storage.constituents[0])
    assert storage.header["constituent_count"] == len(candidate.bundle.constituents)
    assert storage.manifest["identity_canonical_json"] == (
        candidate.canonical_identity_bytes.decode("utf-8")
    )

    reconstructed = _bundle_from_storage(
        storage,
        candidate.bundle.snapshot.manifest.payload.mapping,
    )
    assert reconstructed == candidate.bundle


class _RecordingResult:
    def __init__(self, value: object | None = None) -> None:
        self.value = value

    def scalar_one(self) -> object:
        return self.value


class _RecordingConnection:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def execute(self, statement: object, parameters: dict[str, Any]) -> _RecordingResult:
        self.calls.append((str(statement), parameters))
        return _RecordingResult(AS_OF)


def test_insert_order_is_atomic_lineage_order_and_creation_time_is_database_owned() -> None:
    storage = _candidate_storage(_candidate())
    connection = _RecordingConnection()

    SnapshotRepository._insert_storage(connection, storage)  # type: ignore[arg-type]

    insert_tables = [call[0].split()[2] for call in connection.calls]
    assert insert_tables == [
        "data_snapshots",
        *["data_raw_observations"] * len(storage.raw_observations),
        *["data_observation_revisions"] * len(storage.revisions),
        *["data_normalized_observations"] * len(storage.normalized_observations),
        *["data_snapshot_constituents"] * len(storage.constituents),
        *["data_quality_findings"] * len(storage.quality_findings),
        "data_snapshot_manifests",
    ]
    header_sql, header_parameters = connection.calls[0]
    assert "RETURNING created_at_utc" in header_sql
    assert "created_at_utc" not in header_parameters
    assert insert_tables[-1] == "data_snapshot_manifests"


@pytest.mark.parametrize(
    "tamper",
    ("raw_payload", "request_fingerprint", "manifest_identity", "count"),
)
def test_storage_revalidation_rejects_any_hash_lineage_or_count_tamper(tamper: str) -> None:
    candidate = _candidate()
    storage = _candidate_storage(candidate)
    header = deepcopy(dict(storage.header))
    raw = [deepcopy(dict(row)) for row in storage.raw_observations]
    manifest = deepcopy(dict(storage.manifest))
    if tamper == "raw_payload":
        raw[0]["raw_payload"] = b"tampered"
    elif tamper == "request_fingerprint":
        header["request_fingerprint_canonical_json"] += " "
    elif tamper == "manifest_identity":
        manifest["identity_canonical_json"] += " "
    else:
        header["raw_observation_count"] += 1
    changed = replace(
        storage,
        header=header,
        raw_observations=tuple(raw),
        manifest=manifest,
    )

    with pytest.raises(SnapshotLineage, match="immutable lineage validation"):
        _bundle_from_storage(changed, candidate.bundle.snapshot.manifest.payload.mapping)


def test_authorization_uses_fresh_exact_mapping_family_capability_and_corroborations() -> None:
    family_a = _mapping()
    _authorize_mapping(family_a, DataCapability.SECURITY_MASTER)
    with pytest.raises(SnapshotAuthorization, match="not authorized"):
        _authorize_mapping(family_a, DataCapability.OFFICIAL_DOCUMENT_EVENT_METADATA)

    family_c = _mapping(
        CanonicalFamily.C_OFFICIAL_EVENT_TEXT_OVERLAY,
        corroborations=(CORROBORATION_ID,),
    )
    _authorize_mapping(family_c, DataCapability.OFFICIAL_DOCUMENT_EVENT_METADATA)
    candidate = _candidate(
        DataCapability.OFFICIAL_DOCUMENT_EVENT_METADATA,
        mapping=family_c,
    )
    _assert_candidate_mapping(family_c, candidate)

    changed_version = _mapping(version=2)
    with pytest.raises(SnapshotLineage, match="fresh persisted mapping"):
        _assert_candidate_mapping(changed_version, _candidate(mapping=family_a))
    changed_corroboration = _mapping(
        CanonicalFamily.C_OFFICIAL_EVENT_TEXT_OVERLAY,
        corroborations=(UUID("dddddddd-dddd-5ddd-8ddd-dddddddddddd"),),
    )
    with pytest.raises(SnapshotLineage, match="fresh persisted mapping"):
        _assert_candidate_mapping(changed_corroboration, candidate)


def test_repository_exposes_closed_typed_error_surface() -> None:
    assert issubclass(SnapshotNotFound, LookupError)
    assert issubclass(MappingNotFound, LookupError)
    assert issubclass(SnapshotAuthorization, PermissionError)
    assert issubclass(SnapshotLineage, ValueError)
    assert issubclass(SnapshotConflict, RuntimeError)


def test_repository_source_contains_request_lock_idempotency_and_full_read_revalidation() -> None:
    source = __import__("inspect").getsource(
        __import__("fable5_data.repository", fromlist=["SnapshotRepository"])
    )
    assert "FOR UPDATE" in source
    assert "pg_advisory_xact_lock" in source
    assert "request_fingerprint_sha256" in source
    assert "different snapshot hash" in source
    assert "_load_bundle" in source
    assert "_bundle_from_storage" in source
