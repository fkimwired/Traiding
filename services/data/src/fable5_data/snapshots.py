from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from fable5_data.canonical import (
    canonical_json_bytes,
    normalized_observation_content_sha256,
    normalized_observation_id_from_sha256,
    quality_finding_id_from_sha256,
    quality_finding_sha256,
    raw_observation_content_sha256,
    raw_observation_id_from_sha256,
    revision_content_sha256,
    revision_id_from_sha256,
    snapshot_id_from_sha256,
)
from fable5_data.contracts import (
    AdapterAvailableResult,
    AdapterBatchDraft,
    AdapterProfile,
    AuthorizedMappingIdentity,
    ConstituentDisposition,
    DataQualityFinding,
    DataQualityFindingDraft,
    DataQualitySeverity,
    DataRecordType,
    DataSnapshot,
    FindingDisposition,
    MockConfigurationIdentity,
    NormalizedObservation,
    NormalizedObservationDraft,
    ObservationEnvelopeDraft,
    ObservationRevision,
    ObservationRevisionDraft,
    RawObservation,
    RawObservationDraft,
    RequestFingerprintInput,
    SnapshotBuildBlockedResult,
    SnapshotBundle,
    SnapshotConstituent,
    SnapshotConstituentDraft,
    SnapshotManifest,
    SnapshotManifestDraft,
    SnapshotQualityStatus,
    SnapshotRequestParameters,
    UseRightsScope,
)


@dataclass(frozen=True, slots=True)
class SnapshotCandidate:
    request_fingerprint_sha256: str
    snapshot_id: UUID
    snapshot_sha256: str
    canonical_identity_bytes: bytes
    bundle: SnapshotBundle


SnapshotMaterializationResult = SnapshotCandidate | SnapshotBuildBlockedResult


def constituent_sort_key(item: SnapshotConstituentDraft) -> tuple[str, ...]:
    """Return the exact canonical constituent order frozen by the contract."""

    return (
        item.record_type.value,
        item.logical_record_id,
        item.logical_record_key_sha256,
        item.revision_id,
        item.vintage_id,
        item.raw_payload_sha256,
        item.normalized_content_sha256,
        item.disposition.value,
    )


def quality_finding_sort_key(item: DataQualityFindingDraft) -> tuple[str, ...]:
    """Return the exact canonical quality-finding order frozen by the contract."""

    return (
        item.rule_set_version,
        item.rule_id,
        item.severity.value,
        item.code.value,
        "" if item.affected_record_type is None else item.affected_record_type.value,
        "" if item.affected_record_identity is None else item.affected_record_identity,
        "" if item.raw_payload_sha256 is None else item.raw_payload_sha256,
        "" if item.normalized_content_sha256 is None else item.normalized_content_sha256,
        "" if item.field_name is None else item.field_name,
        item.disposition.value,
        item.finding_sha256,
    )


def _normalize_created_at(value: datetime | None, request: SnapshotRequestParameters) -> datetime:
    if value is None:
        return request.as_of_utc
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("created_at_utc must be timezone-aware")
    return value.astimezone(UTC)


def _request_fingerprint(
    request: SnapshotRequestParameters,
    profile: AdapterProfile,
    configuration: MockConfigurationIdentity,
) -> str:
    return RequestFingerprintInput(
        request=request,
        adapter=profile,
        schema_bindings=profile.schema_bindings,
        use_rights=profile.use_rights,
        configuration=configuration,
    ).sha256()


def _validate_server_resolved_inputs(
    mapping: AuthorizedMappingIdentity,
    request: SnapshotRequestParameters,
    profile: AdapterProfile,
    configuration: MockConfigurationIdentity,
    batch: AdapterBatchDraft,
) -> None:
    if request.mapping != mapping:
        raise ValueError("snapshot request mapping must match the server-resolved mapping")
    if request.mock_configuration_id != configuration.configuration_id:
        raise ValueError("snapshot request configuration must match server-resolved configuration")
    AdapterAvailableResult(
        profile=profile,
        capability=request.capability,
        batch=batch,
    )
    if (
        not profile.synthetic
        or profile.use_rights.scope is not UseRightsScope.INTERNAL_TEST_FIXTURE_ONLY
    ):
        raise ValueError("Phase 4 snapshot persistence is limited to synthetic test fixtures")

    allowed_schemas = {
        (binding.dataset_schema_id, binding.dataset_schema_version)
        for binding in profile.schema_bindings
    }
    observations: tuple[
        RawObservationDraft | ObservationRevisionDraft | NormalizedObservationDraft, ...
    ] = (*batch.raw_observations, *batch.revisions, *batch.normalized_observations)
    for observation in observations:
        if (
            observation.provider_id != profile.provider_id
            or observation.adapter_id != profile.adapter_id
            or observation.adapter_version != profile.adapter_version
            or observation.dataset_id != profile.dataset_id
            or observation.product_id != profile.product_id
            or observation.entitlement_id != profile.use_rights.entitlement_id
            or observation.use_rights_id != profile.use_rights.use_rights_id
        ):
            raise ValueError(
                "observation provenance must match the server-resolved adapter profile"
            )
        schema = (observation.dataset_schema_id, observation.dataset_schema_version)
        if schema not in allowed_schemas:
            raise ValueError("observation schema must be declared by the adapter profile")


def _validate_deterministic_storage_ids(batch: AdapterBatchDraft) -> None:
    for raw in batch.raw_observations:
        content_hash = raw_observation_content_sha256(raw.identity_payload())
        if raw.raw_observation_id != raw_observation_id_from_sha256(content_hash):
            raise ValueError("raw observation storage identity is not deterministic")
    for revision in batch.revisions:
        content_hash = revision_content_sha256(revision.hash_payload())
        if revision.revision_content_sha256 != content_hash:
            raise ValueError("revision content hash is not deterministic")
        if revision.revision_record_id != revision_id_from_sha256(content_hash):
            raise ValueError("revision storage identity is not deterministic")
    for normalized in batch.normalized_observations:
        content_hash = normalized_observation_content_sha256(normalized.hash_payload())
        if normalized.normalized_content_sha256 != content_hash:
            raise ValueError("normalized content hash is not deterministic")
        if normalized.normalized_observation_id != normalized_observation_id_from_sha256(
            content_hash
        ):
            raise ValueError("normalized observation storage identity is not deterministic")
    for finding in batch.quality_findings:
        finding_hash = quality_finding_sha256(finding.hash_payload())
        if finding.finding_sha256 != finding_hash:
            raise ValueError("quality finding hash is not deterministic")
        if finding.finding_id != quality_finding_id_from_sha256(finding_hash):
            raise ValueError("quality finding storage identity is not deterministic")


def _eligible_lineage(
    batch: AdapterBatchDraft,
    as_of_utc: datetime,
) -> tuple[
    tuple[RawObservationDraft, ...],
    tuple[ObservationRevisionDraft, ...],
    tuple[NormalizedObservationDraft, ...],
]:
    raw = tuple(item for item in batch.raw_observations if item.available_at <= as_of_utc)
    raw_ids = {item.raw_observation_id for item in raw}
    revisions = tuple(
        item
        for item in batch.revisions
        if item.available_at <= as_of_utc and item.raw_observation_id in raw_ids
    )
    revision_ids = {item.revision_record_id for item in revisions}
    for revision in revisions:
        predecessor = revision.predecessor_revision_record_id
        if predecessor is not None and predecessor not in revision_ids:
            raise ValueError("eligible revision cannot omit its as-of predecessor")
    normalized = tuple(
        item
        for item in batch.normalized_observations
        if item.available_at <= as_of_utc
        and item.raw_observation_id in raw_ids
        and item.observation_revision_id in revision_ids
    )
    return raw, revisions, normalized


def _revision_sequences(
    revisions: tuple[ObservationRevisionDraft, ...],
) -> tuple[dict[UUID, ObservationRevisionDraft], dict[str, int]]:
    revisions_by_id = {item.revision_record_id: item for item in revisions}
    sequence_keys = [(item.logical_record_key_sha256, item.revision_sequence) for item in revisions]
    if len(sequence_keys) != len(set(sequence_keys)):
        raise ValueError("logical records cannot have duplicate revision sequences")
    maximum_by_key: dict[str, int] = {}
    for revision in revisions:
        maximum_by_key[revision.logical_record_key_sha256] = max(
            revision.revision_sequence,
            maximum_by_key.get(revision.logical_record_key_sha256, 0),
        )
    return revisions_by_id, maximum_by_key


def _is_excluded(
    normalized: NormalizedObservationDraft,
    findings: tuple[DataQualityFindingDraft, ...],
) -> bool:
    for finding in findings:
        if finding.disposition is not FindingDisposition.EXCLUDED:
            continue
        if finding.normalized_content_sha256 is not None:
            if finding.normalized_content_sha256 == normalized.normalized_content_sha256:
                return True
            continue
        if finding.raw_payload_sha256 is not None:
            if finding.raw_payload_sha256 == normalized.raw_payload_sha256:
                return True
            continue
        if finding.affected_record_identity == normalized.logical_record_id:
            return True
    return False


def _has_explicit_measurement_missingness(
    normalized: NormalizedObservationDraft,
) -> bool:
    nullable_fields = getattr(type(normalized.payload), "nullable_measurement_fields", ())
    return any(
        getattr(normalized.payload, field_name.split(".")[-1]) is None
        for field_name in nullable_fields
    )


def _constituents(
    normalized: tuple[NormalizedObservationDraft, ...],
    revisions: tuple[ObservationRevisionDraft, ...],
    findings: tuple[DataQualityFindingDraft, ...],
) -> tuple[SnapshotConstituentDraft, ...]:
    revisions_by_id, maximum_by_key = _revision_sequences(revisions)
    envelope_fields = set(ObservationEnvelopeDraft.model_fields)
    result: list[SnapshotConstituentDraft] = []
    for observation in normalized:
        if _is_excluded(observation, findings):
            continue
        revision = revisions_by_id[observation.observation_revision_id]
        if revision.revision_sequence < maximum_by_key[revision.logical_record_key_sha256]:
            disposition = ConstituentDisposition.RETAINED_HISTORICAL_VINTAGE
        elif _has_explicit_measurement_missingness(observation):
            disposition = ConstituentDisposition.EXPLICIT_MISSINGNESS
        else:
            disposition = ConstituentDisposition.INCLUDED_AS_OF
        result.append(
            SnapshotConstituentDraft.model_validate(
                {
                    **observation.model_dump(
                        mode="python",
                        include=envelope_fields,
                    ),
                    "record_type": DataRecordType(observation.payload.record_type),
                    "raw_observation_id": observation.raw_observation_id,
                    "observation_revision_id": observation.observation_revision_id,
                    "normalized_observation_id": observation.normalized_observation_id,
                    "normalized_content_sha256": observation.normalized_content_sha256,
                    "disposition": disposition,
                }
            )
        )
    return tuple(sorted(result, key=constituent_sort_key))


def _raw_sort_key(item: RawObservationDraft) -> tuple[str, ...]:
    return (
        item.logical_record_id,
        item.logical_record_key_sha256,
        item.revision_id,
        item.vintage_id,
        item.raw_payload_sha256,
        item.source_record_id,
        item.raw_content_type,
    )


def _revision_sort_key(item: ObservationRevisionDraft) -> tuple[str | int, ...]:
    return (
        item.logical_record_id,
        item.logical_record_key_sha256,
        item.revision_sequence,
        item.revision_id,
        item.vintage_id,
        item.raw_payload_sha256,
        item.revision_content_sha256,
    )


def _normalized_sort_key(item: NormalizedObservationDraft) -> tuple[str, ...]:
    return (
        DataRecordType(item.payload.record_type).value,
        item.logical_record_id,
        item.logical_record_key_sha256,
        item.revision_id,
        item.vintage_id,
        item.raw_payload_sha256,
        item.normalized_content_sha256,
    )


def _bind[
    BoundT: (
        RawObservation,
        ObservationRevision,
        NormalizedObservation,
        SnapshotConstituent,
        DataQualityFinding,
    )
](
    model: type[BoundT],
    draft: (
        RawObservationDraft
        | ObservationRevisionDraft
        | NormalizedObservationDraft
        | SnapshotConstituentDraft
        | DataQualityFindingDraft
    ),
    snapshot_id: UUID,
    snapshot_sha256: str,
) -> BoundT:
    payload = draft.model_dump(mode="python")
    return model.model_validate(
        {
            **payload,
            "snapshot_id": snapshot_id,
            "snapshot_sha256": snapshot_sha256,
        }
    )


def build_snapshot_candidate(
    *,
    mapping: AuthorizedMappingIdentity,
    request: SnapshotRequestParameters,
    profile: AdapterProfile,
    configuration: MockConfigurationIdentity,
    batch: AdapterBatchDraft,
    created_at_utc: datetime | None = None,
) -> SnapshotMaterializationResult:
    """Materialize a deterministic, immutable Phase 4 snapshot candidate."""

    _validate_server_resolved_inputs(mapping, request, profile, configuration, batch)
    _validate_deterministic_storage_ids(batch)
    fingerprint = _request_fingerprint(request, profile, configuration)
    findings = tuple(sorted(batch.quality_findings, key=quality_finding_sort_key))
    if any(item.disposition is FindingDisposition.BLOCKED for item in findings):
        return SnapshotBuildBlockedResult(
            request_fingerprint_sha256=fingerprint,
            quality_findings=findings,
        )

    raw, revisions, normalized = _eligible_lineage(batch, request.as_of_utc)
    constituents = _constituents(normalized, revisions, findings)
    manifest_draft = SnapshotManifestDraft(
        request_fingerprint_sha256=fingerprint,
        mapping=mapping,
        request=request,
        adapter=profile,
        schema_bindings=profile.schema_bindings,
        use_rights=profile.use_rights,
        configuration=configuration,
        constituents=constituents,
        quality_findings=findings,
    )
    snapshot_sha256 = manifest_draft.sha256()
    snapshot_id = snapshot_id_from_sha256(snapshot_sha256)
    manifest = SnapshotManifest(
        snapshot_id=snapshot_id,
        snapshot_sha256=snapshot_sha256,
        payload=manifest_draft,
    )
    has_warning = any(
        item.severity in {DataQualitySeverity.WARNING, DataQualitySeverity.ERROR}
        or item.disposition is FindingDisposition.EXCLUDED
        for item in findings
    )
    quality_status = (
        SnapshotQualityStatus.DATA_QUALITY_ACCEPTED_WITH_WARNINGS
        if has_warning
        else SnapshotQualityStatus.DATA_QUALITY_ACCEPTED
    )
    active_constituent_count = sum(
        item.disposition
        in {
            ConstituentDisposition.INCLUDED_AS_OF,
            ConstituentDisposition.EXPLICIT_MISSINGNESS,
        }
        for item in constituents
    )
    snapshot = DataSnapshot(
        snapshot_id=snapshot_id,
        snapshot_sha256=snapshot_sha256,
        manifest=manifest,
        quality_status=quality_status,
        raw_observation_count=len(raw),
        revision_count=len(revisions),
        normalized_observation_count=len(normalized),
        active_constituent_count=active_constituent_count,
        quality_finding_count=len(findings),
        created_at_utc=_normalize_created_at(created_at_utc, request),
    )

    bound_raw = tuple(
        _bind(RawObservation, item, snapshot_id, snapshot_sha256)
        for item in sorted(raw, key=_raw_sort_key)
    )
    bound_revisions = tuple(
        _bind(ObservationRevision, item, snapshot_id, snapshot_sha256)
        for item in sorted(revisions, key=_revision_sort_key)
    )
    bound_normalized = tuple(
        _bind(NormalizedObservation, item, snapshot_id, snapshot_sha256)
        for item in sorted(normalized, key=_normalized_sort_key)
    )
    bound_constituents = tuple(
        _bind(SnapshotConstituent, item, snapshot_id, snapshot_sha256) for item in constituents
    )
    bound_findings = tuple(
        _bind(DataQualityFinding, item, snapshot_id, snapshot_sha256) for item in findings
    )
    bundle = SnapshotBundle(
        snapshot=snapshot,
        raw_observations=bound_raw,
        revisions=bound_revisions,
        normalized_observations=bound_normalized,
        constituents=bound_constituents,
        quality_findings=bound_findings,
    )
    return SnapshotCandidate(
        request_fingerprint_sha256=fingerprint,
        snapshot_id=snapshot_id,
        snapshot_sha256=snapshot_sha256,
        canonical_identity_bytes=canonical_json_bytes(manifest_draft.identity_payload()),
        bundle=bundle,
    )


def materialize_snapshot(
    *,
    mapping: AuthorizedMappingIdentity,
    request: SnapshotRequestParameters,
    profile: AdapterProfile,
    configuration: MockConfigurationIdentity,
    batch: AdapterBatchDraft,
    created_at_utc: datetime | None = None,
) -> SnapshotBundle | SnapshotBuildBlockedResult:
    """Return the bound bundle, or a nonpersisted blocked build result."""

    result = build_snapshot_candidate(
        mapping=mapping,
        request=request,
        profile=profile,
        configuration=configuration,
        batch=batch,
        created_at_utc=created_at_utc,
    )
    if isinstance(result, SnapshotBuildBlockedResult):
        return result
    return result.bundle


__all__ = [
    "SnapshotCandidate",
    "SnapshotMaterializationResult",
    "build_snapshot_candidate",
    "constituent_sort_key",
    "materialize_snapshot",
    "quality_finding_sort_key",
]
