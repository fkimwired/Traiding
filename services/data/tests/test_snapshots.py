from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from fable5_data.canonical import (
    logical_record_id_from_sha256,
    logical_record_key_sha256,
    normalized_observation_content_sha256,
    normalized_observation_id_from_sha256,
    quality_finding_id_from_sha256,
    quality_finding_sha256,
    raw_observation_content_sha256,
    raw_observation_id_from_sha256,
    raw_payload_sha256,
    revision_content_sha256,
    revision_id_from_sha256,
)
from fable5_data.contracts import (
    NORMALIZED_OBSERVATION_SCHEMA_VERSION,
    RAW_OBSERVATION_SCHEMA_VERSION,
    AdapterBatchDraft,
    AdapterProfile,
    AuthorizedMappingIdentity,
    ConstituentDisposition,
    DataCapability,
    DataQualityCode,
    DataQualityFindingDraft,
    DataQualitySeverity,
    FieldMissingness,
    FindingDisposition,
    MissingnessReason,
    MockConfigurationIdentity,
    NormalizedObservationDraft,
    ObservationRevisionDraft,
    OhlcvBarPayload,
    RawObservationDraft,
    SchemaBinding,
    SnapshotBuildBlockedResult,
    SnapshotConstituentDraft,
    SnapshotManifestDraft,
    SnapshotQualityStatus,
    SnapshotRequestParameters,
    UseRightsIdentity,
    UseRightsScope,
)
from fable5_data.snapshots import SnapshotCandidate, build_snapshot_candidate
from fable5_mapping.models import CanonicalFamily, ResearchVerdict

HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_C = "c" * 64
INSTRUMENT_ID = UUID("50000000-0000-0000-0000-000000000001")
LISTING_ID = UUID("50000000-0000-0000-0000-000000000002")
MAPPING_ID = UUID("50000000-0000-0000-0000-000000000003")
EVENT_TIME = datetime(2026, 7, 10, 20, tzinfo=UTC)
AVAILABLE_1 = datetime(2026, 7, 10, 21, tzinfo=UTC)
AVAILABLE_2 = datetime(2026, 7, 11, 21, tzinfo=UTC)
AS_OF = datetime(2026, 7, 12, 0, tzinfo=UTC)
LOGICAL_KEY = logical_record_key_sha256(
    {
        "record_type": "ohlcv_bar",
        "listing_id": str(LISTING_ID),
        "bar_end": EVENT_TIME,
        "adjustment_basis": "raw_unadjusted",
    }
)
LOGICAL_ID = str(logical_record_id_from_sha256(LOGICAL_KEY))


def _mapping(
    *,
    mapping_id: UUID = MAPPING_ID,
    version: int = 1,
    input_hash: str = HASH_A,
    rule_version: str = "phase3-mapper-rules-v1",
    rule_hash: str = HASH_B,
) -> AuthorizedMappingIdentity:
    return AuthorizedMappingIdentity(
        mapping_id=mapping_id,
        mapping_version=version,
        mapping_input_sha256=input_hash,
        mapper_rule_set_version=rule_version,
        mapper_rule_set_sha256=rule_hash,
        canonical_family=CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING,
        verdict=ResearchVerdict.BUILD_RESEARCH,
    )


def _use_rights(
    *,
    entitlement_id: str = "synthetic-entitlement",
    use_rights_id: str = "phase4-synthetic-test-fixture-rights-v1",
) -> UseRightsIdentity:
    return UseRightsIdentity(
        entitlement_id=entitlement_id,
        use_rights_id=use_rights_id,
        scope=UseRightsScope.INTERNAL_TEST_FIXTURE_ONLY,
        storage_allowed=True,
        display_allowed=True,
        non_display_allowed=True,
        derived_data_allowed=True,
        redistribution_allowed=False,
    )


def _profile(
    *,
    provider_id: str = "synthetic",
    adapter_id: str = "synthetic-pit",
    adapter_version: str = "phase4-synthetic-pit-adapter-v1",
    dataset_id: str = "synthetic-equity-daily",
    product_id: str = "synthetic-fixture-product",
    schema_version: str = "phase4-ohlcv-bar-v1",
    use_rights: UseRightsIdentity | None = None,
    capabilities: tuple[DataCapability, ...] = (DataCapability.OHLCV,),
    schemas: tuple[SchemaBinding, ...] | None = None,
) -> AdapterProfile:
    if schemas is None:
        schemas = (
            SchemaBinding(
                dataset_schema_id="ohlcv_bar",
                dataset_schema_version=schema_version,
            ),
        )
    return AdapterProfile(
        provider_id=provider_id,
        adapter_id=adapter_id,
        adapter_version=adapter_version,
        dataset_id=dataset_id,
        product_id=product_id,
        synthetic=True,
        capabilities=capabilities,
        schema_bindings=schemas,
        use_rights=_use_rights() if use_rights is None else use_rights,
    )


def _envelope(
    schema: str,
    *,
    source_record_id: str,
    available_at: datetime,
    revision_id: str,
    vintage_id: str,
    raw_hash: str,
    valid_to: datetime | None,
    field_missingness: tuple[FieldMissingness, ...] = (),
    quality_flags: tuple[str, ...] = (),
    logical_key: str = LOGICAL_KEY,
    logical_id: str = LOGICAL_ID,
    provider_id: str = "synthetic",
    adapter_id: str = "synthetic-pit",
    adapter_version: str = "phase4-synthetic-pit-adapter-v1",
    dataset_id: str = "synthetic-equity-daily",
    product_id: str = "synthetic-fixture-product",
    schema_version: str = "phase4-ohlcv-bar-v1",
    entitlement_id: str = "synthetic-entitlement",
    use_rights_id: str = "phase4-synthetic-test-fixture-rights-v1",
) -> dict[str, object]:
    return {
        "envelope_schema_version": schema,
        "logical_record_id": logical_id,
        "logical_record_key_sha256": logical_key,
        "provider_id": provider_id,
        "adapter_id": adapter_id,
        "adapter_version": adapter_version,
        "dataset_id": dataset_id,
        "product_id": product_id,
        "dataset_schema_id": "ohlcv_bar",
        "dataset_schema_version": schema_version,
        "entitlement_id": entitlement_id,
        "use_rights_id": use_rights_id,
        "source_record_id": source_record_id,
        "instrument_id": INSTRUMENT_ID,
        "listing_id": LISTING_ID,
        "event_time": EVENT_TIME,
        "available_at": available_at,
        "retrieved_at": available_at + timedelta(hours=1),
        "valid_from": EVENT_TIME,
        "valid_to": valid_to,
        "revision_id": revision_id,
        "vintage_id": vintage_id,
        "source_timezone": "America/New_York",
        "calendar_id": "XNYS",
        "unit": "usd_per_share",
        "currency": "USD",
        "availability_precision": "timestamp",
        "availability_convention": "source_timestamp",
        "availability_source_date": None,
        "quality_flags": quality_flags,
        "field_missingness": field_missingness,
        "raw_payload_sha256": raw_hash,
    }


def _raw(
    payload: bytes,
    *,
    source_record_id: str,
    available_at: datetime,
    revision_id: str,
    vintage_id: str,
    valid_to: datetime | None,
    field_missingness: tuple[FieldMissingness, ...] = (),
    quality_flags: tuple[str, ...] = (),
    logical_key: str = LOGICAL_KEY,
    logical_id: str = LOGICAL_ID,
) -> RawObservationDraft:
    values = {
        **_envelope(
            RAW_OBSERVATION_SCHEMA_VERSION,
            source_record_id=source_record_id,
            available_at=available_at,
            revision_id=revision_id,
            vintage_id=vintage_id,
            raw_hash=raw_payload_sha256(payload),
            valid_to=valid_to,
            field_missingness=field_missingness,
            quality_flags=quality_flags,
            logical_key=logical_key,
            logical_id=logical_id,
        ),
        "raw_content_type": "application/json",
        "raw_payload": payload,
    }
    identity = raw_observation_content_sha256(
        {key: value for key, value in values.items() if key != "raw_payload"}
    )
    values["raw_observation_id"] = raw_observation_id_from_sha256(identity)
    return RawObservationDraft.model_validate(values)


def _revision(
    raw: RawObservationDraft,
    *,
    sequence: int,
    predecessor: UUID | None,
) -> ObservationRevisionDraft:
    envelope = raw.model_dump(
        mode="python",
        exclude={"raw_observation_id", "raw_content_type", "raw_payload"},
    )
    envelope["envelope_schema_version"] = NORMALIZED_OBSERVATION_SCHEMA_VERSION
    values = {
        **envelope,
        "revision_schema_version": "phase4-observation-revision-v1",
        "raw_observation_id": raw.raw_observation_id,
        "revision_sequence": sequence,
        "predecessor_revision_record_id": predecessor,
    }
    content_hash = revision_content_sha256(values)
    values["revision_content_sha256"] = content_hash
    values["revision_record_id"] = revision_id_from_sha256(content_hash)
    return ObservationRevisionDraft.model_validate(values)


def _normalized(
    raw: RawObservationDraft,
    revision: ObservationRevisionDraft,
    *,
    close: str,
) -> NormalizedObservationDraft:
    envelope = raw.model_dump(
        mode="python",
        exclude={"raw_observation_id", "raw_content_type", "raw_payload"},
    )
    envelope["envelope_schema_version"] = NORMALIZED_OBSERVATION_SCHEMA_VERSION
    payload = OhlcvBarPayload(
        bar_interval="P1D",
        bar_start=EVENT_TIME - timedelta(hours=6, minutes=30),
        bar_end=EVENT_TIME,
        open=Decimal("100"),
        high=Decimal("106"),
        low=Decimal("99"),
        close=Decimal(close),
        volume=Decimal("1000"),
        adjustment_basis="raw_unadjusted",
    )
    values = {
        **envelope,
        "raw_observation_id": raw.raw_observation_id,
        "observation_revision_id": revision.revision_record_id,
        "payload": payload,
    }
    content_hash = normalized_observation_content_sha256(values)
    values["normalized_content_sha256"] = content_hash
    values["normalized_observation_id"] = normalized_observation_id_from_sha256(content_hash)
    return NormalizedObservationDraft.model_validate(values)


def _finding(
    normalized: NormalizedObservationDraft,
    *,
    rule_id: str = "phase4-synthetic-warning",
    severity: DataQualitySeverity = DataQualitySeverity.WARNING,
    disposition: FindingDisposition = FindingDisposition.RETAINED,
) -> DataQualityFindingDraft:
    values: dict[str, object] = {
        "rule_set_version": "phase4-data-quality-v1",
        "rule_id": rule_id,
        "severity": severity,
        "code": DataQualityCode.NEAR_DUPLICATE_RETAINED,
        "affected_record_type": "ohlcv_bar",
        "affected_record_identity": normalized.logical_record_id,
        "raw_payload_sha256": normalized.raw_payload_sha256,
        "normalized_content_sha256": normalized.normalized_content_sha256,
        "field_name": "payload.close",
        "disposition": disposition,
        "occurrence_count": 1,
        "occurrence_rate": Decimal("0.5"),
        "range_start_utc": normalized.event_time,
        "range_end_utc": normalized.available_at,
        "sanitized_detail": {"dataset": "synthetic", "rule": rule_id},
    }
    finding_hash = quality_finding_sha256(values)
    values["finding_sha256"] = finding_hash
    values["finding_id"] = quality_finding_id_from_sha256(finding_hash)
    return DataQualityFindingDraft.model_validate(values)


def _batch(
    *,
    logical_variant: str = "base",
    raw_suffix: str = "base",
    current_close: str = "104",
    current_revision_id: str = "correction-1",
    current_vintage_id: str = "2026-07-11-correction",
    current_missingness_reason: MissingnessReason = MissingnessReason.NOT_APPLICABLE,
    current_quality_flags: tuple[str, ...] = (),
    findings: str = "none",
) -> AdapterBatchDraft:
    logical_key = logical_record_key_sha256(
        {
            "record_type": "ohlcv_bar",
            "listing_id": str(LISTING_ID),
            "bar_end": EVENT_TIME,
            "adjustment_basis": "raw_unadjusted",
            "variant": logical_variant,
        }
    )
    logical_id = str(logical_record_id_from_sha256(logical_key))
    original_raw = _raw(
        f'{{"close":"103","variant":"{raw_suffix}"}}'.encode(),
        source_record_id="ohlcv:synthetic:2026-07-10:original",
        available_at=AVAILABLE_1,
        revision_id="original",
        vintage_id="2026-07-10-original",
        valid_to=AVAILABLE_2,
        logical_key=logical_key,
        logical_id=logical_id,
    )
    original_revision = _revision(original_raw, sequence=1, predecessor=None)
    original_normalized = _normalized(
        original_raw,
        original_revision,
        close="103",
    )
    missingness = (
        FieldMissingness(
            field_name="valid_to",
            reason=current_missingness_reason,
        ),
    )
    current_raw = _raw(
        b'{"close":"104","variant":"correction"}',
        source_record_id="ohlcv:synthetic:2026-07-10:correction",
        available_at=AVAILABLE_2,
        revision_id=current_revision_id,
        vintage_id=current_vintage_id,
        valid_to=None,
        field_missingness=missingness,
        quality_flags=current_quality_flags,
        logical_key=logical_key,
        logical_id=logical_id,
    )
    current_revision = _revision(
        current_raw,
        sequence=2,
        predecessor=original_revision.revision_record_id,
    )
    current_normalized = _normalized(
        current_raw,
        current_revision,
        close=current_close,
    )
    extra_key = logical_record_key_sha256({"record_type": "ohlcv_bar", "source": "rejected-extra"})
    extra_raw = _raw(
        b'{"rejected":true}',
        source_record_id="ohlcv:synthetic:rejected-extra",
        available_at=AVAILABLE_1,
        revision_id="rejected",
        vintage_id="rejected-v1",
        valid_to=AVAILABLE_2,
        logical_key=extra_key,
        logical_id=str(logical_record_id_from_sha256(extra_key)),
    )
    quality_findings: tuple[DataQualityFindingDraft, ...] = ()
    if findings == "warning":
        quality_findings = (_finding(current_normalized),)
    elif findings == "two":
        quality_findings = (
            _finding(current_normalized, rule_id="phase4-z-warning"),
            _finding(original_normalized, rule_id="phase4-a-warning"),
        )
    elif findings == "blocked":
        quality_findings = (
            _finding(
                current_normalized,
                rule_id="phase4-blocking",
                severity=DataQualitySeverity.BLOCKING,
                disposition=FindingDisposition.BLOCKED,
            ),
        )
    return AdapterBatchDraft(
        raw_observations=(original_raw, current_raw, extra_raw),
        revisions=(original_revision, current_revision),
        normalized_observations=(original_normalized, current_normalized),
        quality_findings=quality_findings,
    )


def _candidate(
    *,
    batch: AdapterBatchDraft | None = None,
    mapping: AuthorizedMappingIdentity | None = None,
    request: SnapshotRequestParameters | None = None,
    profile: AdapterProfile | None = None,
    configuration: MockConfigurationIdentity | None = None,
    created_at_utc: datetime | None = None,
) -> SnapshotCandidate:
    mapping = _mapping() if mapping is None else mapping
    profile = _profile() if profile is None else profile
    configuration = (
        MockConfigurationIdentity(
            configuration_id="default",
            configuration_sha256=HASH_C,
        )
        if configuration is None
        else configuration
    )
    request = (
        SnapshotRequestParameters(
            mapping=mapping,
            as_of_utc=AS_OF,
            capability=DataCapability.OHLCV,
            mock_configuration_id=configuration.configuration_id,
        )
        if request is None
        else request
    )
    result = build_snapshot_candidate(
        mapping=mapping,
        request=request,
        profile=profile,
        configuration=configuration,
        batch=_batch() if batch is None else batch,
        created_at_utc=created_at_utc,
    )
    assert isinstance(result, SnapshotCandidate)
    return result


def _empty_candidate(**changes: object) -> SnapshotCandidate:
    mapping = _mapping(
        mapping_id=changes.get("mapping_id", MAPPING_ID),
        version=changes.get("mapping_version", 1),
        input_hash=changes.get("mapping_input_sha256", HASH_A),
        rule_version=changes.get("rule_version", "phase3-mapper-rules-v1"),
        rule_hash=changes.get("rule_hash", HASH_B),
    )
    rights = _use_rights(
        entitlement_id=changes.get("entitlement_id", "synthetic-entitlement"),
        use_rights_id=changes.get("use_rights_id", "phase4-synthetic-test-fixture-rights-v1"),
    )
    schema_version = changes.get("schema_version", "phase4-ohlcv-bar-v1")
    schemas = (
        SchemaBinding(
            dataset_schema_id="corporate_action",
            dataset_schema_version="phase4-corporate-action-v1",
        ),
        SchemaBinding(
            dataset_schema_id="ohlcv_bar",
            dataset_schema_version=schema_version,
        ),
    )
    profile = _profile(
        provider_id=changes.get("provider_id", "synthetic"),
        adapter_id=changes.get("adapter_id", "synthetic-pit"),
        adapter_version=changes.get("adapter_version", "phase4-synthetic-pit-adapter-v1"),
        dataset_id=changes.get("dataset_id", "synthetic-equity-daily"),
        product_id=changes.get("product_id", "synthetic-fixture-product"),
        use_rights=rights,
        capabilities=(DataCapability.CORPORATE_ACTIONS, DataCapability.OHLCV),
        schemas=schemas,
    )
    configuration = MockConfigurationIdentity(
        configuration_id=changes.get("configuration_id", "default"),
        configuration_sha256=changes.get("configuration_sha256", HASH_C),
    )
    request = SnapshotRequestParameters(
        mapping=mapping,
        as_of_utc=changes.get("as_of_utc", AS_OF),
        capability=changes.get("capability", DataCapability.OHLCV),
        mock_configuration_id=configuration.configuration_id,
    )
    return _candidate(
        batch=AdapterBatchDraft(
            raw_observations=(),
            revisions=(),
            normalized_observations=(),
            quality_findings=(),
        ),
        mapping=mapping,
        request=request,
        profile=profile,
        configuration=configuration,
    )


def test_materialization_is_order_invariant_retry_identical_and_fully_bound() -> None:
    batch = _batch(findings="two")
    first = _candidate(batch=batch, created_at_utc=AS_OF + timedelta(hours=1))
    reversed_batch = AdapterBatchDraft(
        raw_observations=tuple(reversed(batch.raw_observations)),
        revisions=tuple(reversed(batch.revisions)),
        normalized_observations=tuple(reversed(batch.normalized_observations)),
        quality_findings=tuple(reversed(batch.quality_findings)),
    )
    retry = _candidate(
        batch=reversed_batch,
        created_at_utc=AS_OF + timedelta(hours=1),
    )

    assert first == retry
    assert first.canonical_identity_bytes == retry.canonical_identity_bytes
    assert first.bundle.model_dump_json() == retry.bundle.model_dump_json()
    binding = (first.snapshot_id, first.snapshot_sha256)
    for collection in (
        first.bundle.raw_observations,
        first.bundle.revisions,
        first.bundle.normalized_observations,
        first.bundle.constituents,
        first.bundle.quality_findings,
    ):
        assert all((item.snapshot_id, item.snapshot_sha256) == binding for item in collection)

    assert first.bundle.snapshot.raw_observation_count == 3
    assert first.bundle.snapshot.revision_count == 2
    assert first.bundle.snapshot.normalized_observation_count == 2
    assert first.bundle.snapshot.active_constituent_count == 1
    assert {item.disposition for item in first.bundle.constituents} == {
        ConstituentDisposition.RETAINED_HISTORICAL_VINTAGE,
        ConstituentDisposition.INCLUDED_AS_OF,
    }
    assert first.bundle.snapshot.quality_status is (
        SnapshotQualityStatus.DATA_QUALITY_ACCEPTED_WITH_WARNINGS
    )


def test_exact_exclusion_hash_does_not_exclude_an_earlier_revision() -> None:
    batch = _batch()
    original, current = batch.normalized_observations
    exact_current_exclusion = _finding(
        current,
        rule_id="phase4-exact-current-exclusion",
        disposition=FindingDisposition.EXCLUDED,
    )
    candidate = _candidate(
        batch=AdapterBatchDraft(
            raw_observations=batch.raw_observations,
            revisions=batch.revisions,
            normalized_observations=batch.normalized_observations,
            quality_findings=(exact_current_exclusion,),
        )
    )

    assert [item.normalized_content_sha256 for item in candidate.bundle.constituents] == [
        original.normalized_content_sha256
    ]


def test_bound_public_hash_payloads_exclude_snapshot_binding_regression() -> None:
    batch = _batch(findings="warning")
    candidate = _candidate(batch=batch)
    for draft, bound in zip(
        sorted(batch.raw_observations, key=lambda item: item.raw_payload_sha256),
        sorted(candidate.bundle.raw_observations, key=lambda item: item.raw_payload_sha256),
        strict=True,
    ):
        assert draft.identity_payload() == bound.identity_payload()
    for draft, bound in zip(
        sorted(batch.revisions, key=lambda item: item.revision_content_sha256),
        sorted(candidate.bundle.revisions, key=lambda item: item.revision_content_sha256),
        strict=True,
    ):
        assert draft.hash_payload() == bound.hash_payload()
    for draft, bound in zip(
        sorted(batch.normalized_observations, key=lambda item: item.normalized_content_sha256),
        sorted(
            candidate.bundle.normalized_observations,
            key=lambda item: item.normalized_content_sha256,
        ),
        strict=True,
    ):
        assert draft.hash_payload() == bound.hash_payload()
    assert batch.quality_findings[0].hash_payload() == (
        candidate.bundle.quality_findings[0].hash_payload()
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"mapping_id": UUID("50000000-0000-0000-0000-000000000099")},
        {"mapping_version": 2},
        {"mapping_input_sha256": HASH_B},
        {"rule_version": "phase3-mapper-rules-v2"},
        {"rule_hash": HASH_A},
        {"as_of_utc": AS_OF + timedelta(seconds=1)},
        {"capability": DataCapability.CORPORATE_ACTIONS},
        {"adapter_id": "synthetic-pit-v2"},
        {"adapter_version": "phase4-synthetic-pit-adapter-v2"},
        {"schema_version": "phase4-ohlcv-bar-v2"},
        {"provider_id": "synthetic-provider-v2"},
        {"dataset_id": "synthetic-equity-daily-v2"},
        {"product_id": "synthetic-fixture-product-v2"},
        {"entitlement_id": "synthetic-entitlement-v2"},
        {"use_rights_id": "phase4-synthetic-test-fixture-rights-v2"},
        {"configuration_id": "alternate"},
        {"configuration_sha256": HASH_A},
    ],
)
def test_each_server_resolved_input_changes_fingerprint_and_snapshot(
    changes: dict[str, object],
) -> None:
    baseline = _empty_candidate()
    changed = _empty_candidate(**changes)
    assert changed.request_fingerprint_sha256 != baseline.request_fingerprint_sha256
    assert changed.snapshot_sha256 != baseline.snapshot_sha256


@pytest.mark.parametrize(
    "batch",
    [
        _batch(logical_variant="changed"),
        _batch(raw_suffix="raw-changed"),
        _batch(current_close="105"),
        _batch(current_revision_id="correction-2"),
        _batch(current_vintage_id="2026-07-11-correction-v2"),
        _batch(current_quality_flags=("synthetic_fixture",)),
        _batch(current_missingness_reason=MissingnessReason.NOT_PROVIDED_BY_SOURCE),
        _batch(findings="warning"),
    ],
)
def test_each_output_record_or_quality_change_changes_snapshot_not_request(
    batch: AdapterBatchDraft,
) -> None:
    baseline = _candidate(batch=_batch())
    changed = _candidate(batch=batch)
    assert changed.request_fingerprint_sha256 == baseline.request_fingerprint_sha256
    assert changed.snapshot_sha256 != baseline.snapshot_sha256


def test_created_at_and_storage_uuids_do_not_change_snapshot_identity() -> None:
    first = _candidate(created_at_utc=AS_OF + timedelta(hours=1))
    later = _candidate(created_at_utc=AS_OF + timedelta(hours=2))
    assert first.snapshot_sha256 == later.snapshot_sha256
    assert first.canonical_identity_bytes == later.canonical_identity_bytes
    assert first.bundle.snapshot.created_at_utc != later.bundle.snapshot.created_at_utc

    manifest = first.bundle.snapshot.manifest.payload
    constituent = manifest.constituents[0]
    changed_ids = SnapshotConstituentDraft.model_validate(
        {
            **constituent.model_dump(),
            "raw_observation_id": UUID("50000000-0000-0000-0000-000000000091"),
            "observation_revision_id": UUID("50000000-0000-0000-0000-000000000092"),
            "normalized_observation_id": UUID("50000000-0000-0000-0000-000000000093"),
        }
    )
    changed_manifest = SnapshotManifestDraft.model_validate(
        {**manifest.model_dump(), "constituents": (changed_ids, *manifest.constituents[1:])}
    )
    assert changed_manifest.sha256() == manifest.sha256()


def test_same_request_changed_output_is_repository_conflict_evidence() -> None:
    baseline = _candidate(batch=_batch())
    changed = _candidate(batch=_batch(current_close="105"))
    assert baseline.request_fingerprint_sha256 == changed.request_fingerprint_sha256
    assert baseline.snapshot_sha256 != changed.snapshot_sha256


def test_blocking_quality_returns_nonpersisted_result() -> None:
    mapping = _mapping()
    configuration = MockConfigurationIdentity(
        configuration_id="default",
        configuration_sha256=HASH_C,
    )
    request = SnapshotRequestParameters(
        mapping=mapping,
        as_of_utc=AS_OF,
        capability=DataCapability.OHLCV,
        mock_configuration_id=configuration.configuration_id,
    )
    result = build_snapshot_candidate(
        mapping=mapping,
        request=request,
        profile=_profile(),
        configuration=configuration,
        batch=_batch(findings="blocked"),
    )
    assert isinstance(result, SnapshotBuildBlockedResult)
    assert result.status == "blocked"
