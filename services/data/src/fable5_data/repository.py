from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ValidationError
from sqlalchemy import Engine, bindparam, create_engine, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import Connection, RowMapping
from sqlalchemy.exc import DBAPIError, IntegrityError

from fable5_data.canonical import canonical_json_bytes, canonicalize
from fable5_data.contracts import (
    AUTHORIZED_CAPABILITIES,
    DATE_ONLY_AVAILABILITY_CONVENTION,
    REQUEST_FINGERPRINT_VERSION,
    AuthorizedMappingIdentity,
    DataCapability,
    DataQualityFinding,
    DataSnapshot,
    NormalizedObservation,
    ObservationRevision,
    RawObservation,
    RequestFingerprintInput,
    SnapshotBundle,
    SnapshotConstituent,
    SnapshotManifest,
    SnapshotManifestDraft,
)
from fable5_data.snapshots import SnapshotCandidate


class SnapshotNotFound(LookupError):
    pass


class MappingNotFound(LookupError):
    pass


class SnapshotAuthorization(PermissionError):
    pass


class SnapshotLineage(ValueError):
    pass


class SnapshotConflict(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class _SnapshotStorage:
    header: Mapping[str, Any]
    raw_observations: tuple[Mapping[str, Any], ...]
    revisions: tuple[Mapping[str, Any], ...]
    normalized_observations: tuple[Mapping[str, Any], ...]
    constituents: tuple[Mapping[str, Any], ...]
    quality_findings: tuple[Mapping[str, Any], ...]
    manifest: Mapping[str, Any]


def _observation_envelope(
    item: RawObservation | ObservationRevision | NormalizedObservation | SnapshotConstituent,
) -> dict[str, Any]:
    return {
        "snapshot_id": item.snapshot_id,
        "snapshot_sha256": item.snapshot_sha256,
        "envelope_schema_version": item.envelope_schema_version,
        "logical_record_id": item.logical_record_id,
        "logical_record_key_sha256": item.logical_record_key_sha256,
        "provider_id": item.provider_id,
        "adapter_id": item.adapter_id,
        "adapter_version": item.adapter_version,
        "dataset_id": item.dataset_id,
        "product_id": item.product_id,
        "dataset_schema_id": item.dataset_schema_id,
        "dataset_schema_version": item.dataset_schema_version,
        "entitlement_id": item.entitlement_id,
        "use_rights_id": item.use_rights_id,
        "source_record_id": item.source_record_id,
        "instrument_id": item.instrument_id,
        "listing_id": item.listing_id,
        "event_time": item.event_time,
        "available_at": item.available_at,
        "retrieved_at": item.retrieved_at,
        "valid_from": item.valid_from,
        "valid_to": item.valid_to,
        "revision_id": item.revision_id,
        "vintage_id": item.vintage_id,
        "source_timezone": item.source_timezone,
        "calendar_id": item.calendar_id,
        "unit": item.unit,
        "currency": item.currency,
        "availability_precision": item.availability_precision.value,
        "availability_convention": item.availability_convention.value,
        "availability_source_date": item.availability_source_date,
        "quality_flags": [value.value for value in item.quality_flags],
        "field_missingness": [value.model_dump(mode="json") for value in item.field_missingness],
        "raw_payload_sha256": item.raw_payload_sha256,
    }


def _request_fingerprint_input(manifest: SnapshotManifestDraft) -> RequestFingerprintInput:
    return RequestFingerprintInput(
        request=manifest.request,
        adapter=manifest.adapter,
        schema_bindings=manifest.schema_bindings,
        use_rights=manifest.use_rights,
        configuration=manifest.configuration,
    )


def _candidate_storage(candidate: SnapshotCandidate) -> _SnapshotStorage:
    bundle = candidate.bundle
    snapshot = bundle.snapshot
    manifest = snapshot.manifest.payload
    fingerprint_input = _request_fingerprint_input(manifest)
    fingerprint_bytes = canonical_json_bytes(fingerprint_input)
    identity_bytes = canonical_json_bytes(manifest.identity_payload())
    if candidate.request_fingerprint_sha256 != fingerprint_input.sha256():
        raise SnapshotLineage("snapshot candidate request fingerprint is not deterministic")
    if candidate.request_fingerprint_sha256 != manifest.request_fingerprint_sha256:
        raise SnapshotLineage("snapshot candidate request fingerprint lineage mismatch")
    if candidate.snapshot_id != snapshot.snapshot_id:
        raise SnapshotLineage("snapshot candidate identity mismatch")
    if candidate.snapshot_sha256 != snapshot.snapshot_sha256:
        raise SnapshotLineage("snapshot candidate hash mismatch")
    if candidate.canonical_identity_bytes != identity_bytes:
        raise SnapshotLineage("snapshot candidate canonical identity bytes mismatch")

    mapping = manifest.mapping
    request = manifest.request
    adapter = manifest.adapter
    rights = manifest.use_rights
    configuration = manifest.configuration
    header: dict[str, Any] = {
        "snapshot_id": snapshot.snapshot_id,
        "snapshot_sha256": snapshot.snapshot_sha256,
        "request_fingerprint_sha256": manifest.request_fingerprint_sha256,
        "request_fingerprint_version": REQUEST_FINGERPRINT_VERSION,
        "request_fingerprint_payload": canonicalize(fingerprint_input),
        "request_fingerprint_canonical_json": fingerprint_bytes.decode("utf-8"),
        "mapping_id": mapping.mapping_id,
        "mapping_version": mapping.mapping_version,
        "mapping_input_sha256": mapping.mapping_input_sha256,
        "mapper_rule_set_version": mapping.mapper_rule_set_version,
        "mapper_rule_set_sha256": mapping.mapper_rule_set_sha256,
        "canonical_family": mapping.canonical_family.value,
        "verdict": mapping.verdict.value,
        "official_corroboration_source_version_ids": [
            str(value) for value in mapping.official_corroboration_source_version_ids
        ],
        "as_of_utc": request.as_of_utc,
        "capability": request.capability.value,
        "mock_configuration_id": request.mock_configuration_id,
        "configuration_id": configuration.configuration_id,
        "configuration_sha256": configuration.configuration_sha256,
        "fixture_set_version": configuration.fixture_set_version,
        "provider_id": adapter.provider_id,
        "adapter_id": adapter.adapter_id,
        "adapter_version": adapter.adapter_version,
        "dataset_id": adapter.dataset_id,
        "product_id": adapter.product_id,
        "synthetic": adapter.synthetic,
        "capabilities": [value.value for value in adapter.capabilities],
        "schema_bindings": [value.model_dump(mode="json") for value in adapter.schema_bindings],
        "entitlement_id": rights.entitlement_id,
        "use_rights_id": rights.use_rights_id,
        "scope": rights.scope.value,
        "storage_allowed": rights.storage_allowed,
        "display_allowed": rights.display_allowed,
        "non_display_allowed": rights.non_display_allowed,
        "derived_data_allowed": rights.derived_data_allowed,
        "redistribution_allowed": rights.redistribution_allowed,
        "snapshot_schema_version": manifest.snapshot_schema_version,
        "canonicalization_version": manifest.canonicalization_version,
        "date_only_availability_convention": DATE_ONLY_AVAILABILITY_CONVENTION,
        "quality_status": snapshot.quality_status.value,
        "raw_observation_count": snapshot.raw_observation_count,
        "revision_count": snapshot.revision_count,
        "normalized_observation_count": snapshot.normalized_observation_count,
        "constituent_count": len(bundle.constituents),
        "active_constituent_count": snapshot.active_constituent_count,
        "quality_finding_count": snapshot.quality_finding_count,
        "created_at_utc": snapshot.created_at_utc,
    }

    raw_rows = tuple(
        {
            "raw_observation_id": item.raw_observation_id,
            **_observation_envelope(item),
            "raw_content_type": item.raw_content_type,
            "raw_payload": item.raw_payload,
        }
        for item in bundle.raw_observations
    )
    revision_rows = tuple(
        {
            "revision_record_id": item.revision_record_id,
            "raw_observation_id": item.raw_observation_id,
            "revision_schema_version": item.revision_schema_version,
            "revision_content_sha256": item.revision_content_sha256,
            "revision_sequence": item.revision_sequence,
            "predecessor_revision_record_id": item.predecessor_revision_record_id,
            **_observation_envelope(item),
        }
        for item in bundle.revisions
    )
    normalized_rows = tuple(
        {
            "normalized_observation_id": item.normalized_observation_id,
            "raw_observation_id": item.raw_observation_id,
            "observation_revision_id": item.observation_revision_id,
            "normalized_content_sha256": item.normalized_content_sha256,
            "payload": item.payload.model_dump(mode="json"),
            **_observation_envelope(item),
        }
        for item in bundle.normalized_observations
    )
    constituent_rows = tuple(
        {
            "ordinal_position": index,
            "record_type": item.record_type.value,
            "raw_observation_id": item.raw_observation_id,
            "observation_revision_id": item.observation_revision_id,
            "normalized_observation_id": item.normalized_observation_id,
            "normalized_content_sha256": item.normalized_content_sha256,
            "disposition": item.disposition.value,
            "manifest_entry": canonicalize(
                item.model_dump(mode="python", exclude={"snapshot_id", "snapshot_sha256"})
            ),
            **_observation_envelope(item),
        }
        for index, item in enumerate(bundle.constituents, start=1)
    )
    finding_rows = tuple(
        {
            "snapshot_id": item.snapshot_id,
            "snapshot_sha256": item.snapshot_sha256,
            "ordinal_position": index,
            "finding_id": item.finding_id,
            "finding_sha256": item.finding_sha256,
            "rule_set_version": item.rule_set_version,
            "rule_id": item.rule_id,
            "severity": item.severity.value,
            "code": item.code.value,
            "affected_record_type": (
                None if item.affected_record_type is None else item.affected_record_type.value
            ),
            "affected_record_identity": item.affected_record_identity,
            "raw_payload_sha256": item.raw_payload_sha256,
            "normalized_content_sha256": item.normalized_content_sha256,
            "field_name": item.field_name,
            "disposition": item.disposition.value,
            "occurrence_count": item.occurrence_count,
            "occurrence_rate": item.occurrence_rate,
            "range_start_utc": item.range_start_utc,
            "range_end_utc": item.range_end_utc,
            "sanitized_detail": item.sanitized_detail,
            "manifest_entry": canonicalize(
                item.model_dump(mode="python", exclude={"snapshot_id", "snapshot_sha256"})
            ),
        }
        for index, item in enumerate(bundle.quality_findings, start=1)
    )
    manifest_row = {
        "snapshot_id": snapshot.snapshot_id,
        "snapshot_sha256": snapshot.snapshot_sha256,
        "request_fingerprint_sha256": manifest.request_fingerprint_sha256,
        "payload": canonicalize(manifest),
        "identity_payload": canonicalize(manifest.identity_payload()),
        "identity_canonical_json": identity_bytes.decode("utf-8"),
        "raw_observation_count": snapshot.raw_observation_count,
        "revision_count": snapshot.revision_count,
        "normalized_observation_count": snapshot.normalized_observation_count,
        "constituent_count": len(bundle.constituents),
        "active_constituent_count": snapshot.active_constituent_count,
        "quality_finding_count": snapshot.quality_finding_count,
        "quality_status": snapshot.quality_status.value,
    }
    return _SnapshotStorage(
        header=header,
        raw_observations=raw_rows,
        revisions=revision_rows,
        normalized_observations=normalized_rows,
        constituents=constituent_rows,
        quality_findings=finding_rows,
        manifest=manifest_row,
    )


def _model_values(model: type[BaseModel], row: Mapping[str, Any]) -> dict[str, Any]:
    return {field: row[field] for field in model.model_fields}


def _bundle_from_storage(
    storage: _SnapshotStorage,
    persisted_mapping: AuthorizedMappingIdentity,
) -> SnapshotBundle:
    try:
        header = storage.header
        manifest_row = storage.manifest
        manifest_draft = SnapshotManifestDraft.model_validate(manifest_row["payload"])
        if manifest_draft.mapping != persisted_mapping:
            raise ValueError("snapshot manifest mapping differs from persisted mapping")
        manifest = SnapshotManifest(
            snapshot_id=header["snapshot_id"],
            snapshot_sha256=header["snapshot_sha256"],
            payload=manifest_draft,
        )
        raw = tuple(
            RawObservation.model_validate(
                {
                    **_model_values(RawObservation, row),
                    "raw_payload": bytes(row["raw_payload"]),
                }
            )
            for row in storage.raw_observations
        )
        revisions = tuple(
            ObservationRevision.model_validate(_model_values(ObservationRevision, row))
            for row in storage.revisions
        )
        normalized = tuple(
            NormalizedObservation.model_validate(_model_values(NormalizedObservation, row))
            for row in storage.normalized_observations
        )
        constituents = tuple(
            SnapshotConstituent.model_validate(_model_values(SnapshotConstituent, row))
            for row in storage.constituents
        )
        findings = tuple(
            DataQualityFinding.model_validate(_model_values(DataQualityFinding, row))
            for row in storage.quality_findings
        )
        snapshot = DataSnapshot(
            snapshot_id=header["snapshot_id"],
            snapshot_sha256=header["snapshot_sha256"],
            manifest=manifest,
            quality_status=header["quality_status"],
            raw_observation_count=header["raw_observation_count"],
            revision_count=header["revision_count"],
            normalized_observation_count=header["normalized_observation_count"],
            active_constituent_count=header["active_constituent_count"],
            quality_finding_count=header["quality_finding_count"],
            created_at_utc=header["created_at_utc"],
        )
        bundle = SnapshotBundle(
            snapshot=snapshot,
            raw_observations=raw,
            revisions=revisions,
            normalized_observations=normalized,
            constituents=constituents,
            quality_findings=findings,
        )

        fingerprint_input = _request_fingerprint_input(manifest_draft)
        expected_fingerprint_payload = canonicalize(fingerprint_input)
        expected_fingerprint_json = canonical_json_bytes(fingerprint_input).decode("utf-8")
        expected_identity = canonicalize(manifest_draft.identity_payload())
        expected_identity_json = canonical_json_bytes(manifest_draft.identity_payload()).decode(
            "utf-8"
        )
        if header["request_fingerprint_sha256"] != fingerprint_input.sha256():
            raise ValueError("request fingerprint hash changed")
        if header["request_fingerprint_payload"] != expected_fingerprint_payload:
            raise ValueError("request fingerprint payload changed")
        if header["request_fingerprint_canonical_json"] != expected_fingerprint_json:
            raise ValueError("request fingerprint canonical bytes changed")
        if manifest_row["identity_payload"] != expected_identity:
            raise ValueError("manifest identity payload changed")
        if manifest_row["identity_canonical_json"] != expected_identity_json:
            raise ValueError("manifest canonical identity bytes changed")
        if manifest_row["snapshot_sha256"] != manifest.snapshot_sha256:
            raise ValueError("manifest snapshot hash changed")

        expected_counts = {
            "raw_observation_count": len(raw),
            "revision_count": len(revisions),
            "normalized_observation_count": len(normalized),
            "constituent_count": len(constituents),
            "active_constituent_count": snapshot.active_constituent_count,
            "quality_finding_count": len(findings),
        }
        for field, expected in expected_counts.items():
            if header[field] != expected or manifest_row[field] != expected:
                raise ValueError(f"persisted {field} changed")
        if manifest_row["quality_status"] != snapshot.quality_status.value:
            raise ValueError("persisted quality status changed")

        expected_header = _candidate_storage(
            SnapshotCandidate(
                request_fingerprint_sha256=fingerprint_input.sha256(),
                snapshot_id=snapshot.snapshot_id,
                snapshot_sha256=snapshot.snapshot_sha256,
                canonical_identity_bytes=canonical_json_bytes(manifest_draft.identity_payload()),
                bundle=bundle,
            )
        ).header
        for field, expected in expected_header.items():
            if header[field] != expected:
                raise ValueError(f"persisted snapshot header changed: {field}")
        return bundle
    except SnapshotLineage:
        raise
    except (KeyError, TypeError, ValueError, ValidationError) as exc:
        raise SnapshotLineage("persisted snapshot failed immutable lineage validation") from exc


def _authorize_mapping(
    mapping: AuthorizedMappingIdentity,
    capability: DataCapability,
) -> None:
    allowed = AUTHORIZED_CAPABILITIES.get(mapping.canonical_family)
    if allowed is None or capability not in allowed:
        raise SnapshotAuthorization("capability is not authorized for persisted mapping")


def _assert_candidate_mapping(
    persisted: AuthorizedMappingIdentity,
    candidate: SnapshotCandidate,
) -> None:
    manifest = candidate.bundle.snapshot.manifest.payload
    _authorize_mapping(persisted, manifest.request.capability)
    if manifest.mapping != persisted or manifest.request.mapping != persisted:
        raise SnapshotLineage("snapshot candidate does not match fresh persisted mapping lineage")


def _json_statement(sql: str, *names: str) -> Any:
    statement = text(sql)
    return statement.bindparams(*(bindparam(name, type_=postgresql.JSONB) for name in names))


def _insert_rows(
    connection: Connection,
    table: str,
    rows: tuple[Mapping[str, Any], ...],
    *,
    json_columns: frozenset[str] = frozenset(),
) -> None:
    if not rows:
        return
    columns = tuple(rows[0])
    if any(tuple(row) != columns for row in rows):
        raise SnapshotLineage(f"inconsistent storage fields for {table}")
    rendered_columns = ", ".join(columns)
    rendered_values = ", ".join(f":{column}" for column in columns)
    statement = _json_statement(
        f"INSERT INTO {table} ({rendered_columns}) VALUES ({rendered_values})",
        *(column for column in columns if column in json_columns),
    )
    for row in rows:
        connection.execute(statement, dict(row))


class SnapshotRepository:
    def __init__(self, database_url: str | None = None, *, engine: Engine | None = None) -> None:
        if database_url is None and engine is None:
            raise ValueError("database_url or engine is required")
        self.engine = engine or create_engine(str(database_url), pool_pre_ping=True)
        self._owns_engine = engine is None

    def dispose(self) -> None:
        if self._owns_engine:
            self.engine.dispose()

    @staticmethod
    def _mapping_corroborations(
        connection: Connection,
        mapping_id: UUID,
    ) -> tuple[UUID, ...]:
        return tuple(
            connection.execute(
                text(
                    "SELECT official_source_version_id "
                    "FROM mapping_official_corroborations "
                    "WHERE mapping_id = :mapping_id "
                    "ORDER BY official_source_version_id::text"
                ),
                {"mapping_id": mapping_id},
            ).scalars()
        )

    @classmethod
    def _load_mapping(
        cls,
        connection: Connection,
        mapping_id: UUID,
        *,
        lock: bool,
    ) -> AuthorizedMappingIdentity:
        query = "SELECT * FROM research_mapping_versions WHERE id = :mapping_id"
        if lock:
            query += " FOR UPDATE"
        row = connection.execute(text(query), {"mapping_id": mapping_id}).mappings().one_or_none()
        if row is None:
            raise MappingNotFound(f"mapping {mapping_id} was not found")
        try:
            return AuthorizedMappingIdentity(
                mapping_id=row["id"],
                mapping_version=row["version_number"],
                mapping_input_sha256=row["mapping_input_sha256"],
                mapper_rule_set_version=row["mapper_rule_set_version"],
                mapper_rule_set_sha256=row["mapper_rule_set_sha256"],
                canonical_family=row["canonical_family"],
                verdict=row["research_verdict"],
                official_corroboration_source_version_ids=cls._mapping_corroborations(
                    connection, row["id"]
                ),
            )
        except (ValueError, ValidationError) as exc:
            raise SnapshotAuthorization("persisted mapping is not authorized for Phase 4") from exc

    def resolve_mapping(
        self,
        mapping_id: UUID,
        capability: DataCapability,
    ) -> AuthorizedMappingIdentity:
        with self.engine.connect() as connection:
            mapping = self._load_mapping(connection, mapping_id, lock=False)
            _authorize_mapping(mapping, capability)
            return mapping

    @staticmethod
    def _insert_storage(connection: Connection, storage: _SnapshotStorage) -> None:
        header = dict(storage.header)
        header.pop("created_at_utc")
        columns = tuple(header)
        statement = _json_statement(
            "INSERT INTO data_snapshots ("
            + ", ".join(columns)
            + ") VALUES ("
            + ", ".join(f":{column}" for column in columns)
            + ") RETURNING created_at_utc",
            "request_fingerprint_payload",
            "official_corroboration_source_version_ids",
            "capabilities",
            "schema_bindings",
        )
        connection.execute(statement, header).scalar_one()
        _insert_rows(
            connection,
            "data_raw_observations",
            storage.raw_observations,
            json_columns=frozenset({"quality_flags", "field_missingness"}),
        )
        _insert_rows(
            connection,
            "data_observation_revisions",
            storage.revisions,
            json_columns=frozenset({"quality_flags", "field_missingness"}),
        )
        _insert_rows(
            connection,
            "data_normalized_observations",
            storage.normalized_observations,
            json_columns=frozenset({"payload", "quality_flags", "field_missingness"}),
        )
        _insert_rows(
            connection,
            "data_snapshot_constituents",
            storage.constituents,
            json_columns=frozenset({"manifest_entry", "quality_flags", "field_missingness"}),
        )
        _insert_rows(
            connection,
            "data_quality_findings",
            storage.quality_findings,
            json_columns=frozenset({"sanitized_detail", "manifest_entry"}),
        )
        _insert_rows(
            connection,
            "data_snapshot_manifests",
            (storage.manifest,),
            json_columns=frozenset({"payload", "identity_payload"}),
        )

    @staticmethod
    def _load_storage(connection: Connection, snapshot_id: UUID) -> _SnapshotStorage:
        header_row = (
            connection.execute(
                text("SELECT * FROM data_snapshots WHERE snapshot_id = :snapshot_id"),
                {"snapshot_id": snapshot_id},
            )
            .mappings()
            .one_or_none()
        )
        if header_row is None:
            raise SnapshotNotFound(f"snapshot {snapshot_id} was not found")
        manifest_row = (
            connection.execute(
                text("SELECT * FROM data_snapshot_manifests WHERE snapshot_id = :snapshot_id"),
                {"snapshot_id": snapshot_id},
            )
            .mappings()
            .one_or_none()
        )
        if manifest_row is None:
            raise SnapshotLineage("persisted snapshot has no final manifest")

        def rows(query: str) -> tuple[Mapping[str, Any], ...]:
            return tuple(
                dict(row)
                for row in connection.execute(
                    text(query),
                    {"snapshot_id": snapshot_id},
                ).mappings()
            )

        return _SnapshotStorage(
            header=dict(header_row),
            raw_observations=rows(
                "SELECT * FROM data_raw_observations "
                "WHERE snapshot_id = :snapshot_id "
                "ORDER BY logical_record_id, logical_record_key_sha256, revision_id, "
                "vintage_id, raw_payload_sha256, source_record_id, raw_content_type"
            ),
            revisions=rows(
                "SELECT * FROM data_observation_revisions "
                "WHERE snapshot_id = :snapshot_id "
                "ORDER BY logical_record_id, logical_record_key_sha256, revision_sequence, "
                "revision_id, vintage_id, raw_payload_sha256, revision_content_sha256"
            ),
            normalized_observations=rows(
                "SELECT * FROM data_normalized_observations "
                "WHERE snapshot_id = :snapshot_id "
                "ORDER BY payload->>'record_type', logical_record_id, "
                "logical_record_key_sha256, revision_id, vintage_id, "
                "raw_payload_sha256, normalized_content_sha256"
            ),
            constituents=rows(
                "SELECT * FROM data_snapshot_constituents "
                "WHERE snapshot_id = :snapshot_id ORDER BY ordinal_position"
            ),
            quality_findings=rows(
                "SELECT * FROM data_quality_findings "
                "WHERE snapshot_id = :snapshot_id ORDER BY ordinal_position"
            ),
            manifest=dict(manifest_row),
        )

    @classmethod
    def _load_bundle(
        cls,
        connection: Connection,
        snapshot_id: UUID,
        *,
        persisted_mapping: AuthorizedMappingIdentity | None = None,
    ) -> SnapshotBundle:
        storage = cls._load_storage(connection, snapshot_id)
        capability = DataCapability(storage.header["capability"])
        mapping = persisted_mapping or cls._load_mapping(
            connection,
            storage.header["mapping_id"],
            lock=False,
        )
        _authorize_mapping(mapping, capability)
        return _bundle_from_storage(storage, mapping)

    @staticmethod
    def _existing_request(
        connection: Connection,
        fingerprint: str,
    ) -> RowMapping | None:
        return (
            connection.execute(
                text(
                    "SELECT snapshot_id, snapshot_sha256 FROM data_snapshots "
                    "WHERE request_fingerprint_sha256 = :fingerprint"
                ),
                {"fingerprint": fingerprint},
            )
            .mappings()
            .one_or_none()
        )

    @classmethod
    def _return_existing(
        cls,
        connection: Connection,
        existing: RowMapping,
        candidate: SnapshotCandidate,
        mapping: AuthorizedMappingIdentity | None = None,
    ) -> SnapshotBundle:
        if existing["snapshot_sha256"] != candidate.snapshot_sha256:
            raise SnapshotConflict(
                "request fingerprint already resolves to a different snapshot hash"
            )
        bundle = cls._load_bundle(
            connection,
            existing["snapshot_id"],
            persisted_mapping=mapping,
        )
        if bundle.snapshot.snapshot_sha256 != candidate.snapshot_sha256:
            raise SnapshotConflict("existing snapshot failed deterministic hash revalidation")
        return bundle

    def create_snapshot(self, candidate: SnapshotCandidate) -> SnapshotBundle:
        storage = _candidate_storage(candidate)
        try:
            with self.engine.begin() as connection:
                mapping_id = candidate.bundle.snapshot.manifest.payload.mapping.mapping_id
                mapping = self._load_mapping(connection, mapping_id, lock=True)
                _assert_candidate_mapping(mapping, candidate)
                connection.execute(
                    text("SELECT pg_advisory_xact_lock(hashtextextended(:request_fingerprint, 0))"),
                    {"request_fingerprint": candidate.request_fingerprint_sha256},
                )
                existing = self._existing_request(
                    connection,
                    candidate.request_fingerprint_sha256,
                )
                if existing is not None:
                    return self._return_existing(connection, existing, candidate, mapping)
                self._insert_storage(connection, storage)
                return self._load_bundle(
                    connection,
                    candidate.snapshot_id,
                    persisted_mapping=mapping,
                )
        except (
            MappingNotFound,
            SnapshotAuthorization,
            SnapshotConflict,
            SnapshotLineage,
        ):
            raise
        except IntegrityError as exc:
            with self.engine.connect() as connection:
                existing = self._existing_request(
                    connection,
                    candidate.request_fingerprint_sha256,
                )
                if existing is not None:
                    return self._return_existing(connection, existing, candidate)
            raise SnapshotConflict("immutable snapshot insert conflicted") from exc
        except DBAPIError as exc:
            raise SnapshotConflict("immutable snapshot could not be persisted") from exc

    def get_snapshot(self, snapshot_id: UUID) -> SnapshotBundle:
        with self.engine.connect() as connection:
            return self._load_bundle(connection, snapshot_id)

    def list_snapshots(
        self,
        *,
        mapping_id: UUID | None = None,
        limit: int = 100,
    ) -> list[SnapshotBundle]:
        if limit < 1 or limit > 100:
            raise ValueError("snapshot list limit must be between 1 and 100")
        query = "SELECT snapshot_id FROM data_snapshots"
        parameters: dict[str, Any] = {"limit": limit}
        if mapping_id is not None:
            query += " WHERE mapping_id = :mapping_id"
            parameters["mapping_id"] = mapping_id
        query += " ORDER BY created_at_utc DESC, snapshot_id DESC LIMIT :limit"
        with self.engine.connect() as connection:
            snapshot_ids = connection.execute(text(query), parameters).scalars()
            return [self._load_bundle(connection, snapshot_id) for snapshot_id in snapshot_ids]


__all__ = [
    "MappingNotFound",
    "SnapshotAuthorization",
    "SnapshotConflict",
    "SnapshotLineage",
    "SnapshotNotFound",
    "SnapshotRepository",
]
