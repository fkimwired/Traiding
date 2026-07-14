from __future__ import annotations

from datetime import UTC, date, datetime, timedelta, timezone
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
    snapshot_id_from_sha256,
)
from fable5_data.contracts import (
    AUTHORIZED_CAPABILITIES,
    CAPABILITY_RECORD_TYPES,
    NORMALIZED_OBSERVATION_SCHEMA_VERSION,
    PHASE4_AUTHORIZED_CAPABILITIES,
    PHASE4_CAPABILITY_RECORD_TYPES,
    PHASE4_SCHEMA_CONSTANTS,
    PHASE6_DATA_CONTRACT_CONSTANTS,
    RAW_OBSERVATION_SCHEMA_VERSION,
    AdapterAvailableResult,
    AdapterBatchDraft,
    AdapterProfile,
    AdapterResult,
    AdapterUnavailableResult,
    AuthorizedMappingIdentity,
    AvailabilityConvention,
    AvailabilityPrecision,
    ConstituentDisposition,
    DataCapability,
    DataQualityCode,
    DataQualityFindingDraft,
    DataQualitySeverity,
    DataRecordType,
    DataSnapshot,
    FieldMissingness,
    FindingDisposition,
    MissingnessReason,
    MockConfigurationIdentity,
    NormalizedObservationDraft,
    NormalizedPayload,
    ObservationRevisionDraft,
    OhlcvBarPayload,
    RawObservationDraft,
    RequestFingerprintInput,
    SchemaBinding,
    SnapshotBuildBlockedResult,
    SnapshotConstituentDraft,
    SnapshotCreateRequest,
    SnapshotManifest,
    SnapshotManifestDraft,
    SnapshotNondeterminismConflictResult,
    SnapshotQualityStatus,
    SnapshotRequestParameters,
    UseRightsIdentity,
    UseRightsScope,
    conservative_date_available_at,
    official_document_content_sha256,
)
from fable5_mapping.models import CanonicalFamily, ResearchVerdict
from pydantic import TypeAdapter, ValidationError

HASH_A = "a" * 64
HASH_B = "b" * 64
RAW_BYTES = b'{"record":"synthetic"}'
RAW_HASH = raw_payload_sha256(RAW_BYTES)
INSTRUMENT_ID = UUID("40000000-0000-0000-0000-000000000001")
LISTING_ID = UUID("40000000-0000-0000-0000-000000000002")
RAW_ID = UUID("40000000-0000-0000-0000-000000000003")
REVISION_ID = UUID("40000000-0000-0000-0000-000000000004")
NORMALIZED_ID = UUID("40000000-0000-0000-0000-000000000005")
EVENT_TIME = datetime(2026, 7, 10, 20, tzinfo=UTC)
AVAILABLE_AT = datetime(2026, 7, 10, 21, tzinfo=UTC)
RETRIEVED_AT = datetime(2026, 7, 11, 12, tzinfo=UTC)
LOGICAL_KEY_SHA256 = logical_record_key_sha256(
    {
        "record_type": "ohlcv_bar",
        "listing_id": str(LISTING_ID),
        "bar_end": EVENT_TIME,
        "adjustment_basis": "raw_unadjusted",
    }
)
LOGICAL_RECORD_ID = str(logical_record_id_from_sha256(LOGICAL_KEY_SHA256))


def _mapping(
    family: CanonicalFamily = CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING,
    verdict: ResearchVerdict = ResearchVerdict.BUILD_RESEARCH,
    corroboration: tuple[UUID, ...] = (),
) -> dict[str, object]:
    return {
        "mapping_id": UUID("40000000-0000-0000-0000-000000000010"),
        "mapping_version": 1,
        "mapping_input_sha256": HASH_A,
        "mapper_rule_set_version": "phase3-mapper-rules-v1",
        "mapper_rule_set_sha256": HASH_B,
        "canonical_family": family,
        "verdict": verdict,
        "official_corroboration_source_version_ids": corroboration,
    }


def _envelope(schema: str, **updates: object) -> dict[str, object]:
    values: dict[str, object] = {
        "envelope_schema_version": schema,
        "logical_record_id": LOGICAL_RECORD_ID,
        "logical_record_key_sha256": LOGICAL_KEY_SHA256,
        "provider_id": "synthetic",
        "adapter_id": "synthetic-pit",
        "adapter_version": "phase4-synthetic-pit-adapter-v1",
        "dataset_id": "synthetic-equity-daily",
        "product_id": "synthetic-fixture-product",
        "dataset_schema_id": "ohlcv_bar",
        "dataset_schema_version": "phase4-ohlcv-bar-v1",
        "entitlement_id": "synthetic-entitlement",
        "use_rights_id": "phase4-synthetic-test-fixture-rights-v1",
        "source_record_id": "ohlcv:synthetic:2026-07-10",
        "instrument_id": INSTRUMENT_ID,
        "listing_id": LISTING_ID,
        "event_time": EVENT_TIME,
        "available_at": AVAILABLE_AT,
        "retrieved_at": RETRIEVED_AT,
        "valid_from": EVENT_TIME,
        "valid_to": datetime(2026, 7, 11, 20, tzinfo=UTC),
        "revision_id": "original",
        "vintage_id": "2026-07-10-original",
        "source_timezone": "America/New_York",
        "calendar_id": "XNYS",
        "unit": "usd_per_share",
        "currency": "USD",
        "availability_precision": AvailabilityPrecision.TIMESTAMP,
        "availability_convention": AvailabilityConvention.SOURCE_TIMESTAMP,
        "availability_source_date": None,
        "quality_flags": (),
        "field_missingness": (),
        "raw_payload_sha256": RAW_HASH,
    }
    values.update(updates)
    return values


def _ohlcv_payload(**updates: object) -> OhlcvBarPayload:
    values: dict[str, object] = {
        "record_type": "ohlcv_bar",
        "bar_interval": "P1D",
        "bar_start": datetime(2026, 7, 10, 13, 30, tzinfo=UTC),
        "bar_end": EVENT_TIME,
        "open": "100",
        "high": "105",
        "low": "99",
        "close": "104",
        "volume": "1000",
        "adjustment_basis": "raw_unadjusted",
    }
    values.update(updates)
    return OhlcvBarPayload.model_validate(values)


def _normalized(
    *,
    payload: object | None = None,
    field_missingness: tuple[FieldMissingness, ...] = (),
    raw_observation_id: UUID = RAW_ID,
    observation_revision_id: UUID = REVISION_ID,
    **envelope_updates: object,
) -> NormalizedObservationDraft:
    values = _envelope(
        NORMALIZED_OBSERVATION_SCHEMA_VERSION,
        field_missingness=field_missingness,
        **envelope_updates,
    )
    values.update(
        {
            "raw_observation_id": raw_observation_id,
            "observation_revision_id": observation_revision_id,
            "payload": _ohlcv_payload() if payload is None else payload,
        }
    )
    normalized_hash = normalized_observation_content_sha256(values)
    values["normalized_content_sha256"] = normalized_hash
    values["normalized_observation_id"] = normalized_observation_id_from_sha256(normalized_hash)
    return NormalizedObservationDraft.model_validate(values)


def _raw(**envelope_updates: object) -> RawObservationDraft:
    values = {
        **_envelope(RAW_OBSERVATION_SCHEMA_VERSION, **envelope_updates),
        "raw_content_type": "application/json",
        "raw_payload": RAW_BYTES,
    }
    identity_values = {key: value for key, value in values.items() if key != "raw_payload"}
    identity_sha256 = raw_observation_content_sha256(identity_values)
    values["raw_observation_id"] = raw_observation_id_from_sha256(identity_sha256)
    return RawObservationDraft.model_validate(values)


def _revision(
    raw: RawObservationDraft,
    *,
    raw_observation_id: UUID | None = None,
    revision_sequence: int = 1,
    predecessor_revision_record_id: UUID | None = None,
    **envelope_updates: object,
) -> ObservationRevisionDraft:
    values = {
        **_envelope(NORMALIZED_OBSERVATION_SCHEMA_VERSION, **envelope_updates),
        "revision_schema_version": "phase4-observation-revision-v1",
        "raw_observation_id": raw.raw_observation_id
        if raw_observation_id is None
        else raw_observation_id,
        "revision_sequence": revision_sequence,
        "predecessor_revision_record_id": predecessor_revision_record_id,
    }
    revision_hash = revision_content_sha256(values)
    values["revision_content_sha256"] = revision_hash
    values["revision_record_id"] = revision_id_from_sha256(revision_hash)
    return ObservationRevisionDraft.model_validate(values)


def _batch() -> AdapterBatchDraft:
    raw = _raw()
    revision = _revision(raw)
    return AdapterBatchDraft(
        raw_observations=(raw,),
        normalized_observations=(
            _normalized(
                raw_observation_id=raw.raw_observation_id,
                observation_revision_id=revision.revision_record_id,
            ),
        ),
        revisions=(revision,),
        quality_findings=(),
    )


def _profile() -> AdapterProfile:
    return AdapterProfile(
        provider_id="synthetic",
        adapter_id="synthetic-pit",
        adapter_version="phase4-synthetic-pit-adapter-v1",
        dataset_id="synthetic-equity-daily",
        product_id="synthetic-fixture-product",
        synthetic=True,
        capabilities=(DataCapability.OHLCV,),
        schema_bindings=(
            SchemaBinding(
                dataset_schema_id="ohlcv_bar",
                dataset_schema_version="phase4-ohlcv-bar-v1",
            ),
        ),
        use_rights=UseRightsIdentity(
            entitlement_id="synthetic-entitlement",
            use_rights_id="phase4-synthetic-test-fixture-rights-v1",
            scope=UseRightsScope.INTERNAL_TEST_FIXTURE_ONLY,
            storage_allowed=True,
            display_allowed=True,
            non_display_allowed=True,
            derived_data_allowed=True,
            redistribution_allowed=False,
        ),
    )


def _finding(
    *,
    severity: DataQualitySeverity = DataQualitySeverity.WARNING,
    disposition: FindingDisposition = FindingDisposition.RETAINED,
) -> DataQualityFindingDraft:
    values: dict[str, object] = {
        "rule_set_version": "phase4-data-quality-v1",
        "rule_id": "phase4-test-rule",
        "severity": severity,
        "code": DataQualityCode.NEAR_DUPLICATE_RETAINED,
        "affected_record_type": DataRecordType.OHLCV_BAR,
        "affected_record_identity": LOGICAL_RECORD_ID,
        "raw_payload_sha256": RAW_HASH,
        "normalized_content_sha256": HASH_A,
        "field_name": "payload.close",
        "disposition": disposition,
        "occurrence_count": 2,
        "occurrence_rate": "0.5",
        "range_start_utc": EVENT_TIME,
        "range_end_utc": AVAILABLE_AT,
        "sanitized_detail": {"dataset": "synthetic", "rows": [1, 2]},
    }
    finding_hash = quality_finding_sha256(values)
    values["finding_sha256"] = finding_hash
    values["finding_id"] = quality_finding_id_from_sha256(finding_hash)
    return DataQualityFindingDraft.model_validate(values)


def _manifest(
    constituent: SnapshotConstituentDraft | None = None,
) -> SnapshotManifestDraft:
    batch = _batch()
    normalized = batch.normalized_observations[0]
    if constituent is None:
        constituent = SnapshotConstituentDraft.model_validate(
            {
                **_envelope(NORMALIZED_OBSERVATION_SCHEMA_VERSION),
                "record_type": "ohlcv_bar",
                "raw_observation_id": normalized.raw_observation_id,
                "observation_revision_id": normalized.observation_revision_id,
                "normalized_observation_id": normalized.normalized_observation_id,
                "normalized_content_sha256": normalized.normalized_content_sha256,
                "disposition": ConstituentDisposition.INCLUDED_AS_OF,
            }
        )
    mapping = AuthorizedMappingIdentity.model_validate(_mapping())
    request = SnapshotRequestParameters(
        mapping=mapping,
        as_of_utc=RETRIEVED_AT,
        capability=DataCapability.OHLCV,
        mock_configuration_id="default",
    )
    profile = _profile()
    configuration = MockConfigurationIdentity(
        configuration_id="default",
        configuration_sha256=HASH_A,
    )
    fingerprint = RequestFingerprintInput(
        request=request,
        adapter=profile,
        schema_bindings=profile.schema_bindings,
        use_rights=profile.use_rights,
        configuration=configuration,
    ).sha256()
    return SnapshotManifestDraft(
        request_fingerprint_sha256=fingerprint,
        mapping=mapping,
        request=request,
        adapter=profile,
        schema_bindings=profile.schema_bindings,
        use_rights=profile.use_rights,
        configuration=configuration,
        constituents=(constituent,),
        quality_findings=(),
    )


def test_capability_vocabulary_and_family_authorization_are_frozen() -> None:
    assert {item.value for item in DataCapability} == {
        "security_master",
        "universe_membership",
        "ohlcv",
        "corporate_actions",
        "delistings",
        "as_reported_fundamentals",
        "trading_calendar",
        "volatility_return_inputs",
        "official_document_event_metadata",
        "macro_regime_inputs",
    }
    assert set(AUTHORIZED_CAPABILITIES) == {
        CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING,
        CanonicalFamily.B_TIME_SERIES_MOMENTUM_REGIME,
        CanonicalFamily.C_OFFICIAL_EVENT_TEXT_OVERLAY,
    }
    assert PHASE4_CAPABILITY_RECORD_TYPES[DataCapability.SECURITY_MASTER] == {
        DataRecordType.INSTRUMENT_IDENTITY,
        DataRecordType.LISTING_IDENTITY,
    }
    assert CAPABILITY_RECORD_TYPES[DataCapability.SECURITY_MASTER] == {
        DataRecordType.INSTRUMENT_IDENTITY,
        DataRecordType.LISTING_IDENTITY,
        DataRecordType.SECTOR_CLASSIFICATION,
    }
    assert (
        DataCapability.SECURITY_MASTER
        not in PHASE4_AUTHORIZED_CAPABILITIES[CanonicalFamily.B_TIME_SERIES_MOMENTUM_REGIME]
    )
    assert (
        DataCapability.SECURITY_MASTER
        in AUTHORIZED_CAPABILITIES[CanonicalFamily.B_TIME_SERIES_MOMENTUM_REGIME]
    )
    assert PHASE6_DATA_CONTRACT_CONSTANTS["additive_record_types"] == (
        "sector_classification",
        "official_document_content",
        "social_attention",
        "macro_rate_observation",
        "crisis_window_definition",
    )


def test_mapping_and_server_resolved_request_fail_closed() -> None:
    with pytest.raises(ValidationError, match="BUILD_RESEARCH"):
        AuthorizedMappingIdentity.model_validate(_mapping(verdict=ResearchVerdict.DEFER))
    with pytest.raises(ValidationError, match="families A, B, and C"):
        AuthorizedMappingIdentity.model_validate(
            _mapping(family=CanonicalFamily.D_PAIRS_STATISTICAL_ARBITRAGE)
        )
    with pytest.raises(ValidationError, match="official corroboration"):
        AuthorizedMappingIdentity.model_validate(
            _mapping(family=CanonicalFamily.C_OFFICIAL_EVENT_TEXT_OVERLAY)
        )

    mapping = AuthorizedMappingIdentity.model_validate(_mapping())
    with pytest.raises(ValidationError, match="not authorized"):
        SnapshotRequestParameters(
            mapping=mapping,
            as_of_utc=AVAILABLE_AT,
            capability=DataCapability.TRADING_CALENDAR,
            mock_configuration_id="default",
        )

    request = SnapshotCreateRequest.model_validate(
        {
            "mapping_id": mapping.mapping_id,
            "as_of_utc": datetime(2026, 7, 10, 17, tzinfo=timezone(-timedelta(hours=4))),
            "capability": "ohlcv",
            "mock_configuration_id": "default",
        }
    )
    assert request.as_of_utc == AVAILABLE_AT
    with pytest.raises(ValidationError, match="Extra inputs"):
        SnapshotCreateRequest.model_validate(
            {**request.model_dump(), "provider_id": "client-controlled"}
        )


def test_all_field_specific_payloads_use_a_discriminator() -> None:
    samples = [
        {
            "record_type": "instrument_identity",
            "instrument_type": "common_stock",
            "issuer_id": "issuer-1",
            "legal_name": "Synthetic Corp",
            "country_code": "US",
            "share_class_id": "class-a",
        },
        {
            "record_type": "listing_identity",
            "symbol": "SYN",
            "exchange_mic": "XNYS",
            "status": "active",
            "primary_listing": True,
        },
        {
            "record_type": "universe_membership",
            "universe_id": "synthetic-large-cap",
            "status": "included",
        },
        _ohlcv_payload().model_dump(mode="python"),
        {
            "record_type": "corporate_action",
            "corporate_action_id": "split-1",
            "action_type": "split",
            "announcement_at": AVAILABLE_AT,
            "effective_at": AVAILABLE_AT + timedelta(days=5),
            "split_ratio": "2",
        },
        {
            "record_type": "delisting_event",
            "delisting_event_id": "delist-1",
            "delisting_type": "exchange_removal",
            "last_trade_at": EVENT_TIME,
            "effective_at": AVAILABLE_AT,
            "return_inclusion": "separate_return_required",
            "delisting_return": "-0.25",
        },
        {
            "record_type": "as_reported_fundamental",
            "concept_id": "revenue",
            "fiscal_period_start": date(2026, 1, 1),
            "fiscal_period_end": date(2026, 3, 31),
            "fiscal_period_type": "quarter",
            "official_document_id": "filing-1",
            "filing_accepted_at": AVAILABLE_AT,
            "amendment_sequence": 0,
            "value": "1000000",
        },
        {
            "record_type": "calendar_session",
            "session_date": date(2026, 7, 10),
            "status": "open",
            "open_at": datetime(2026, 7, 10, 13, 30, tzinfo=UTC),
            "close_at": EVENT_TIME,
            "early_close": False,
        },
        {
            "record_type": "official_document_event",
            "official_document_id": "filing-1",
            "official_event_id": "event-1",
            "official_source_version_id": UUID("40000000-0000-0000-0000-000000000020"),
            "document_type": "regulatory_filing",
            "event_type": "filing",
            "accession_id": "accession-1",
            "published_at": EVENT_TIME,
            "accepted_at": AVAILABLE_AT,
            "document_content_sha256": HASH_A,
        },
        {
            "record_type": "volatility_return_input",
            "window_start": EVENT_TIME - timedelta(days=5),
            "window_end": EVENT_TIME,
            "bar_observation_ids": (NORMALIZED_ID,),
            "calendar_observation_ids": (REVISION_ID,),
        },
        {
            "record_type": "sector_classification",
            "classification_scheme_id": "synthetic-sector-scheme",
            "classification_scheme_version": "v1",
            "sector_id": "technology",
            "sector_name": "Technology",
        },
        {
            "record_type": "official_document_content",
            "official_document_id": "filing-1",
            "official_event_id": "event-1",
            "official_source_version_id": UUID("40000000-0000-0000-0000-000000000020"),
            "document_type": "regulatory_filing",
            "event_type": "filing",
            "accession_id": "accession-1",
            "published_at": EVENT_TIME,
            "accepted_at": AVAILABLE_AT,
            "corrected_at": None,
            "correction_sequence": 0,
            "document_content_sha256": official_document_content_sha256(
                "Synthetic official filing body."
            ),
            "document_text": "Synthetic official filing body.",
            "amendment_of_document_id": None,
        },
        {
            "record_type": "social_attention",
            "social_attention_record_id": "social-1",
            "platform_id": "synthetic-social-platform",
            "observed_at": AVAILABLE_AT,
            "social_content_sha256": HASH_A,
            "entity_id": "issuer-1",
            "claimed_official_source_version_id": UUID("40000000-0000-0000-0000-000000000020"),
            "manipulation_prone": True,
            "contributes_standalone": False,
        },
        {
            "record_type": "macro_rate_observation",
            "series_id": "synthetic-policy-rate",
            "observation_period_end": date(2026, 6, 30),
            "released_at": AVAILABLE_AT,
            "vintage_id": "synthetic-rate-vintage-1",
            "rate_value": "1.5",
            "previous_rate_value": "1.4",
            "rate_change": "0.1",
        },
        {
            "record_type": "crisis_window_definition",
            "crisis_window_id": "synthetic-stress-window",
            "definition_method_id": "predeclared-calendar-window-v1",
            "declared_at": EVENT_TIME - timedelta(days=10),
            "window_start": EVENT_TIME - timedelta(days=5),
            "window_end": AVAILABLE_AT,
        },
    ]
    adapter = TypeAdapter(NormalizedPayload)
    assert {DataRecordType(adapter.validate_python(item).record_type) for item in samples} == set(
        DataRecordType
    )
    with pytest.raises(ValidationError, match="Extra inputs"):
        adapter.validate_python({**samples[0], "signal": "buy"})


def test_temporal_date_only_and_missingness_rules_are_exact() -> None:
    assert conservative_date_available_at(date(2026, 3, 8), "America/New_York") == datetime(
        2026, 3, 9, 4, tzinfo=UTC
    )
    with pytest.raises(ValidationError, match="at or after available_at"):
        RawObservationDraft.model_validate(
            {
                **_envelope(
                    RAW_OBSERVATION_SCHEMA_VERSION,
                    retrieved_at=AVAILABLE_AT - timedelta(seconds=1),
                ),
                "raw_observation_id": RAW_ID,
                "raw_content_type": "application/json",
                "raw_payload": RAW_BYTES,
            }
        )
    with pytest.raises(ValidationError, match="timezone-aware"):
        SnapshotCreateRequest(
            mapping_id=UUID("40000000-0000-0000-0000-000000000010"),
            as_of_utc=datetime(2026, 7, 10),
            capability=DataCapability.OHLCV,
            mock_configuration_id="default",
        )
    with pytest.raises(ValidationError, match="valid_to null requires"):
        RawObservationDraft.model_validate(
            {
                **_envelope(RAW_OBSERVATION_SCHEMA_VERSION, valid_to=None),
                "raw_observation_id": RAW_ID,
                "raw_content_type": "application/json",
                "raw_payload": RAW_BYTES,
            }
        )
    not_retrieved = _raw(
        retrieved_at=None,
        field_missingness=(
            FieldMissingness(
                field_name="retrieved_at",
                reason=MissingnessReason.NOT_YET_AVAILABLE_AS_OF,
            ),
        ),
    )
    assert not_retrieved.retrieved_at is None
    assert "retrieval_occurred" not in RawObservationDraft.model_fields


def test_hashes_and_raw_revision_normalized_lineage_are_enforced() -> None:
    batch = _batch()
    assert len(batch.raw_observations) == len(batch.normalized_observations) == 1
    with pytest.raises(ValidationError, match="raw payload hash"):
        RawObservationDraft.model_validate(
            {
                **_envelope(RAW_OBSERVATION_SCHEMA_VERSION),
                "raw_observation_id": RAW_ID,
                "raw_content_type": "application/json",
                "raw_payload": b"changed",
            }
        )

    orphan_revision = _revision(
        batch.raw_observations[0],
        raw_observation_id=UUID("40000000-0000-0000-0000-000000000099"),
    )
    with pytest.raises(ValidationError, match="orphan or alter raw lineage"):
        AdapterBatchDraft(
            raw_observations=batch.raw_observations,
            normalized_observations=batch.normalized_observations,
            revisions=(orphan_revision,),
            quality_findings=(),
        )
    extra_raw = _raw(
        source_record_id="ohlcv:synthetic:2026-07-10:rejected",
        revision_id="source-correction",
        vintage_id="2026-07-10-correction",
    )
    unequal = AdapterBatchDraft(
        raw_observations=(*batch.raw_observations, extra_raw),
        normalized_observations=batch.normalized_observations,
        revisions=batch.revisions,
        quality_findings=(),
    )
    assert len(unequal.raw_observations) == 2
    assert len(unequal.revisions) == len(unequal.normalized_observations) == 1


def test_finding_and_snapshot_identities_are_deterministic_and_storage_id_free() -> None:
    finding = _finding()
    assert finding.finding_id == quality_finding_id_from_sha256(finding.finding_sha256)
    blocked = _finding(
        severity=DataQualitySeverity.BLOCKING,
        disposition=FindingDisposition.BLOCKED,
    )
    assert (
        SnapshotBuildBlockedResult(
            request_fingerprint_sha256=HASH_A,
            quality_findings=(blocked,),
        ).status
        == "blocked"
    )

    manifest = _manifest()
    constituent = manifest.constituents[0]
    changed_storage_ids = SnapshotConstituentDraft.model_validate(
        {
            **constituent.model_dump(),
            "raw_observation_id": UUID("40000000-0000-0000-0000-000000000091"),
            "observation_revision_id": UUID("40000000-0000-0000-0000-000000000092"),
            "normalized_observation_id": UUID("40000000-0000-0000-0000-000000000093"),
        }
    )
    same_request_and_output = _manifest(changed_storage_ids)
    assert same_request_and_output.request_fingerprint_sha256 == (
        manifest.request_fingerprint_sha256
    )
    assert same_request_and_output.sha256() == manifest.sha256()

    changed_output = SnapshotConstituentDraft.model_validate(
        {**constituent.model_dump(), "normalized_content_sha256": "c" * 64}
    )
    changed_manifest = _manifest(changed_output)
    assert changed_manifest.request_fingerprint_sha256 == (manifest.request_fingerprint_sha256)
    assert changed_manifest.sha256() != manifest.sha256()
    conflict = SnapshotNondeterminismConflictResult(
        request_fingerprint_sha256=manifest.request_fingerprint_sha256,
        existing_snapshot_sha256=manifest.sha256(),
        candidate_snapshot_sha256=changed_manifest.sha256(),
    )
    assert conflict.status == "nondeterminism_conflict"

    snapshot_hash = manifest.sha256()
    bound_manifest = SnapshotManifest(
        snapshot_id=snapshot_id_from_sha256(snapshot_hash),
        snapshot_sha256=snapshot_hash,
        payload=manifest,
    )
    snapshot = DataSnapshot(
        snapshot_id=bound_manifest.snapshot_id,
        snapshot_sha256=snapshot_hash,
        manifest=bound_manifest,
        quality_status=SnapshotQualityStatus.DATA_QUALITY_ACCEPTED,
        raw_observation_count=2,
        revision_count=1,
        normalized_observation_count=1,
        active_constituent_count=1,
        quality_finding_count=0,
        created_at_utc=RETRIEVED_AT,
    )
    assert snapshot.raw_observation_count != snapshot.revision_count
    assert PHASE4_SCHEMA_CONSTANTS["snapshot_quality_statuses"] == (
        "data_quality_accepted",
        "data_quality_accepted_with_warnings",
    )


def test_adjustment_lookahead_and_delisting_missingness_fail_closed() -> None:
    with pytest.raises(ValidationError, match="future corporate-action knowledge"):
        _normalized(
            payload=_ohlcv_payload(
                adjustment_basis="as_of_adjusted",
                adjustment_as_of=AVAILABLE_AT + timedelta(seconds=1),
                corporate_action_revision_ids=("split-original",),
            )
        )

    delisting = {
        "record_type": "delisting_event",
        "delisting_event_id": "delist-1",
        "delisting_type": "bankruptcy",
        "last_trade_at": EVENT_TIME,
        "effective_at": AVAILABLE_AT,
        "return_inclusion": "separate_return_required",
        "delisting_return": None,
    }
    with pytest.raises(ValidationError, match="null requires explicit field missingness"):
        _normalized(payload=delisting)
    normalized = _normalized(
        payload=delisting,
        field_missingness=(
            FieldMissingness(
                field_name="payload.delisting_return",
                reason=MissingnessReason.DELISTING_RETURN_NOT_PROVIDED,
            ),
        ),
    )
    assert normalized.payload.delisting_return is None


def test_adapter_results_are_discriminated_and_unavailable_messages_are_sanitized() -> None:
    available = TypeAdapter(AdapterResult).validate_python(
        AdapterAvailableResult(
            profile=_profile(),
            capability=DataCapability.OHLCV,
            batch=_batch(),
        ).model_dump()
    )
    assert isinstance(available, AdapterAvailableResult)
    unavailable = TypeAdapter(AdapterResult).validate_python(
        {
            "status": "unavailable",
            "reason_code": "credentials_unavailable",
            "capability": "ohlcv",
            "provider_id": "synthetic",
            "adapter_id": "synthetic-pit",
            "adapter_version": "phase4-synthetic-pit-adapter-v1",
            "dataset_id": "synthetic-equity-daily",
            "product_id": "synthetic-fixture-product",
            "entitlement_id": "synthetic-entitlement",
            "use_rights_id": "phase4-synthetic-test-fixture-rights-v1",
            "sanitized_message": "required credentials are unavailable",
        }
    )
    assert isinstance(unavailable, AdapterUnavailableResult)
    with pytest.raises(ValidationError, match="sanitized"):
        AdapterUnavailableResult.model_validate(
            {
                **unavailable.model_dump(),
                "sanitized_message": "see https://example.invalid?key=sk-secret",
            }
        )
