from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from fable5_data.canonical import canonical_json_bytes, raw_payload_sha256
from fable5_data.contracts import (
    AUTHORIZED_CAPABILITIES,
    CAPABILITY_RECORD_TYPES,
    PHASE4_DATA_CAPABILITIES,
    PHASE4_SCHEMA_CONSTANTS,
    PHASE6_DATA_CONTRACT_CONSTANTS,
    PHASE6_SYNTHETIC_FIXTURE_SET_VERSION,
    AuthorizedMappingIdentity,
    CrisisWindowDefinitionPayload,
    DataCapability,
    DataQualityCode,
    DataRecordType,
    MacroRateObservationPayload,
    OfficialDocumentContentPayload,
    SectorClassificationPayload,
    SnapshotBuildBlockedResult,
    SnapshotRequestParameters,
    SocialAttentionPayload,
    official_document_content_sha256,
)
from fable5_data.phase6_synthetic import (
    PHASE6_SYNTHETIC_MOCK_CONFIGURATION,
    Phase6SyntheticPointInTimeAdapter,
    phase6_fixture_set_sha256,
    resolve_phase6_synthetic_adapter,
)
from fable5_data.quality import (
    QualityAcceptedResult,
    QualityReferenceCatalog,
    run_mandatory_data_quality,
)
from fable5_data.synthetic import (
    SYNTHETIC_ADAPTER_PROFILE,
    SyntheticPointInTimeAdapter,
    build_synthetic_results,
    fixture_set_sha256,
)
from fable5_mapping.models import CanonicalFamily, ResearchVerdict
from pydantic import ValidationError

_PLACEHOLDER_SOURCE_ID = UUID("cccccccc-cccc-5ccc-8ccc-cccccccccccc")


def _mapping(
    family: CanonicalFamily,
    *,
    official_ids: tuple[UUID, ...] = (),
) -> AuthorizedMappingIdentity:
    return AuthorizedMappingIdentity(
        mapping_id=UUID("aaaaaaaa-aaaa-5aaa-8aaa-aaaaaaaaaaaa"),
        mapping_version=1,
        mapping_input_sha256="1" * 64,
        mapper_rule_set_version="phase6-source-contract-tests-v1",
        mapper_rule_set_sha256="2" * 64,
        canonical_family=family,
        verdict=ResearchVerdict.BUILD_RESEARCH,
        official_corroboration_source_version_ids=official_ids,
    )


def _family(capability: DataCapability) -> CanonicalFamily:
    if capability is DataCapability.OFFICIAL_DOCUMENT_EVENT_METADATA:
        return CanonicalFamily.C_OFFICIAL_EVENT_TEXT_OVERLAY
    if capability in {
        DataCapability.SECURITY_MASTER,
        DataCapability.TRADING_CALENDAR,
        DataCapability.VOLATILITY_RETURN_INPUTS,
    }:
        return CanonicalFamily.B_TIME_SERIES_MOMENTUM_REGIME
    return CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING


def _run(
    adapter: Phase6SyntheticPointInTimeAdapter,
    capability: DataCapability,
    *,
    result_override: object | None = None,
) -> QualityAcceptedResult | SnapshotBuildBlockedResult:
    family = _family(capability)
    mapping = _mapping(
        family,
        official_ids=(
            (_PLACEHOLDER_SOURCE_ID,)
            if family is CanonicalFamily.C_OFFICIAL_EVENT_TEXT_OVERLAY
            else ()
        ),
    )
    request = SnapshotRequestParameters(
        mapping=mapping,
        as_of_utc=datetime(2022, 1, 1, tzinfo=UTC),
        capability=capability,
        mock_configuration_id=PHASE6_SYNTHETIC_MOCK_CONFIGURATION.configuration_id,
    )
    result = adapter.fetch(capability) if result_override is None else result_override
    return run_mandatory_data_quality(
        request=request,
        result=result,  # type: ignore[arg-type]
        configuration=PHASE6_SYNTHETIC_MOCK_CONFIGURATION,
        catalog=QualityReferenceCatalog.from_results(adapter.all_results()),
    )


def _blocked_codes(result: SnapshotBuildBlockedResult) -> set[DataQualityCode]:
    return {item.code for item in result.quality_findings}


def test_phase6_payloads_are_strict_source_evidence_only() -> None:
    sector = SectorClassificationPayload(
        classification_scheme_id="synthetic-sector-scheme",
        classification_scheme_version="v1",
        sector_id="technology",
        sector_name="Technology",
    )
    assert sector.model_dump() == {
        "record_type": "sector_classification",
        "classification_scheme_id": "synthetic-sector-scheme",
        "classification_scheme_version": "v1",
        "sector_id": "technology",
        "sector_name": "Technology",
    }
    with pytest.raises(ValidationError, match="Extra inputs"):
        SectorClassificationPayload.model_validate({**sector.model_dump(), "signal": "forbidden"})

    text = "Exact synthetic filing text with Unicode Δ."
    content = OfficialDocumentContentPayload(
        official_document_id="document-1",
        official_event_id="event-1",
        official_source_version_id=_PLACEHOLDER_SOURCE_ID,
        document_type="regulatory_filing",
        event_type="filing",
        accession_id="accession-1",
        published_at=datetime(2020, 1, 1, 14, 55, tzinfo=UTC),
        accepted_at=datetime(2020, 1, 1, 15, tzinfo=UTC),
        corrected_at=None,
        correction_sequence=0,
        document_content_sha256=official_document_content_sha256(text),
        document_text=text,
        amendment_of_document_id=None,
    )
    assert content.document_content_sha256 == raw_payload_sha256(text.encode("utf-8"))
    with pytest.raises(ValidationError, match="exact UTF-8"):
        OfficialDocumentContentPayload.model_validate(
            {**content.model_dump(), "document_content_sha256": "0" * 64}
        )
    with pytest.raises(ValidationError, match="requires its timestamp and predecessor"):
        OfficialDocumentContentPayload.model_validate(
            {
                **content.model_dump(),
                "official_document_id": "document-2",
                "correction_sequence": 1,
            }
        )
    social = SocialAttentionPayload(
        social_attention_record_id="social-1",
        platform_id="synthetic-platform",
        observed_at=datetime(2020, 1, 1, 16, tzinfo=UTC),
        social_content_sha256="3" * 64,
        entity_id="entity-1",
        claimed_official_source_version_id=_PLACEHOLDER_SOURCE_ID,
    )
    assert social.manipulation_prone is True
    assert social.contributes_standalone is False
    with pytest.raises(ValidationError, match="Extra inputs"):
        SocialAttentionPayload.model_validate({**social.model_dump(), "signal": "forbidden"})


def test_phase4_default_fixture_profile_and_every_record_identity_remain_byte_identical() -> None:
    expected = (
        (
            "security_master",
            "e62fb9ec-313e-51d1-84ad-5c729f784fff",
            "16e4d0e4ee86024baf13a7e8bae4fac6fce4380b2e88c9567f3a13eb166ef22e",
            "fee1d039-ae71-55eb-b1b1-21508a0eff8e",
            "7bfac80540e2905611cef38431414d92601388db8e1ada2a8a797cd7bbfe9023",
        ),
        (
            "security_master",
            "e70a9b75-bb60-532d-8671-6ee408806678",
            "7db2f1aca7ebd5f6338d63adf2c1e03fd305b2181480ef2555ecfd527099de20",
            "0b907aff-9e6f-5891-bf27-6ed0474d7c04",
            "10eb8fe4a03204a5c28cbde53211b08f57746a8d6583b2337a5084677155cb96",
        ),
        (
            "universe_membership",
            "62b27683-7bac-5713-81db-6ea3a0aeb40e",
            "12f0c824e7fd1a73b9494568df800e850bb3d7381a49eb62e1de2a8ff03151b2",
            "407f9f7b-7477-53e2-a5b7-fa2f09b5f9e8",
            "2970c86791bf916287231ffab6f5d42f42731375b070e5ca5df4ec483a3f5971",
        ),
        (
            "universe_membership",
            "f41e2ff4-11ea-52b8-a18b-d08f24b6ca77",
            "35f071893767d39f55cc740ed7c2b0b0edb35b4eaacfc4f153a9e095ae554110",
            "2f54f983-0312-5d80-9b09-0097c17d4359",
            "28527bcc14d0627b31c8ef406498d92f7ade5043465cb10dffc654cfdb7f2f4d",
        ),
        (
            "ohlcv",
            "d9d555d6-92a1-58e0-aa9c-4d1968f8a268",
            "56be3d4757eef80f7f2d74aa5f5d2cdb6d0d073086e1d3ad188b72168ef0a2c4",
            "ef369f97-be24-5a11-b28f-a09ec1994e38",
            "bffeefac3aec4ce84e80dac9d02cbdc51b9b29ff71b6f84b09a7ac584fd03d30",
        ),
        (
            "corporate_actions",
            "a0e2eb3b-ad56-54ba-8e36-68b759c26126",
            "ead452eea1b297af8e0ef3ab064db5cd27e58f55bf72d89c512c242e70e9922d",
            "433c8cb7-37c3-5e3a-9acc-f74000511546",
            "994c33073351ed2d57d6202d4030b219acf837373571ff161d812e5b06df4897",
        ),
        (
            "delistings",
            "9018de65-7d99-5b48-af28-3c6d0e35d52e",
            "b71a1b33b42cf929377f6a0926475dc5dba85ed56c5e972dc6a29079284f3691",
            "6ae060c1-fe95-5f37-9605-0a45e3f6b967",
            "6979715a24ea25849780ec574ae2f5739d302ac21f2f139ddafd32f3a58dc3e9",
        ),
        (
            "as_reported_fundamentals",
            "e2af8a64-5233-51b5-85a2-cf3156f2bce1",
            "71b71b136a5d0c4ada133108901f3b945c5a7a0532c57db48c1e5b872fae5e89",
            "a4b62c7a-197e-58f1-b66d-56acac81a863",
            "cdde2985eb1dd33c5601383d515d5ac97edc6576d318e2b89c10aae940c25d11",
        ),
        (
            "as_reported_fundamentals",
            "0309922e-6a97-5555-a0eb-d8ccdf8b29a7",
            "d60f608035fa820b02952da3b18e6a68a0399ab15f825963b153c5ea8b6470af",
            "30c67455-eeab-5da3-800e-dd3df3e49ce3",
            "6bfe7830271db112272bff0771ed960fe6000cc2ebea134d3239b50cf31c4159",
        ),
        (
            "trading_calendar",
            "131d3bd6-0bfb-5175-96e3-36af31649933",
            "7a5668c23914a407bb97cbfa4c85be0e8417667b5151b81634b5213a59b4a68b",
            "f8c366bb-f849-5cd9-a179-d9bc6a673457",
            "c89938be7e27615dd16a0880319450c06e5653fa12d39d9cce168e82e3eee24f",
        ),
        (
            "volatility_return_inputs",
            "4cc615f2-748f-5fcc-9059-ec17ae0f8160",
            "d9378cf5fa5d5e5d94c4ad511a4ce18955c8e9eb2c9d8745fe355b334f211214",
            "ba08d64f-b2b6-5587-99f2-b12e5fd77a4a",
            "a37e56d2d57af1a30fc708f3461025fcd128141dd68e224f9ced44e0bfe4deb7",
        ),
        (
            "official_document_event_metadata",
            "2e92e9e3-653f-5389-bb2d-7cbda2834d17",
            "65e3fc66d5042c41d45d4909c7cab40168285627c03db5bda2700cddf2aac0c6",
            "2b5605a8-5c9b-551a-8dbe-a3605ec82add",
            "185795adc8625a26f4af4f5be3d36e1d85aed4e1bdce9af61ce9760da80a1c89",
        ),
    )
    actual = tuple(
        (
            capability.value,
            str(item.normalized_observation_id),
            item.normalized_content_sha256,
            str(item.raw_observation_id),
            item.raw_payload_sha256,
        )
        for capability, result in build_synthetic_results().items()
        for item in result.batch.normalized_observations
    )

    assert (
        fixture_set_sha256() == "d86c0ad18228c05ef199abba7b4e25e761c4d4f190b0bf30617c435a550172f9"
    )
    assert raw_payload_sha256(canonical_json_bytes(SYNTHETIC_ADAPTER_PROFILE)) == (
        "35d350236c42ff4c35cbb58fee4f603fbe3e335a636ed78f58dcf094de8e1bd3"
    )
    assert actual == expected
    assert SyntheticPointInTimeAdapter().all_results() == tuple(
        build_synthetic_results()[capability] for capability in PHASE4_DATA_CAPABILITIES
    )
    assert PHASE4_SCHEMA_CONSTANTS["record_types"] == (
        "instrument_identity",
        "listing_identity",
        "universe_membership",
        "ohlcv_bar",
        "corporate_action",
        "delisting_event",
        "as_reported_fundamental",
        "calendar_session",
        "official_document_event",
        "volatility_return_input",
    )


def test_phase6_fixture_is_complete_deterministic_and_quality_accepted_for_every_capability() -> (
    None
):
    first = Phase6SyntheticPointInTimeAdapter()
    second = Phase6SyntheticPointInTimeAdapter()

    assert first.all_results() == second.all_results()
    assert phase6_fixture_set_sha256() == (
        "010c4edf621f5a75cbb1913a5a513e3c2472e8da9a53b143345b2fb91f6fed5d"
    )
    assert PHASE6_SYNTHETIC_MOCK_CONFIGURATION.fixture_set_version == (
        PHASE6_SYNTHETIC_FIXTURE_SET_VERSION
    )
    assert PHASE6_DATA_CONTRACT_CONSTANTS["additive_record_types"] == (
        "sector_classification",
        "official_document_content",
        "social_attention",
        "macro_rate_observation",
        "crisis_window_definition",
    )
    assert (
        DataCapability.SECURITY_MASTER
        in AUTHORIZED_CAPABILITIES[CanonicalFamily.B_TIME_SERIES_MOMENTUM_REGIME]
    )
    assert (
        DataCapability.UNIVERSE_MEMBERSHIP
        in AUTHORIZED_CAPABILITIES[CanonicalFamily.B_TIME_SERIES_MOMENTUM_REGIME]
    )
    assert (
        DataCapability.MACRO_REGIME_INPUTS
        in AUTHORIZED_CAPABILITIES[CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING]
    )
    assert AUTHORIZED_CAPABILITIES[CanonicalFamily.C_OFFICIAL_EVENT_TEXT_OVERLAY] == {
        DataCapability.SECURITY_MASTER,
        DataCapability.UNIVERSE_MEMBERSHIP,
        DataCapability.OHLCV,
        DataCapability.OFFICIAL_DOCUMENT_EVENT_METADATA,
    }

    all_observations = tuple(
        item for result in first.all_results() for item in result.batch.normalized_observations
    )
    record_types = [DataRecordType(item.payload.record_type) for item in all_observations]
    assert len({item.instrument_id for item in all_observations if item.instrument_id}) == 3
    assert record_types.count(DataRecordType.SECTOR_CLASSIFICATION) == 3
    assert record_types.count(DataRecordType.OHLCV_BAR) == 852
    assert record_types.count(DataRecordType.CALENDAR_SESSION) == 305
    assert record_types.count(DataRecordType.AS_REPORTED_FUNDAMENTAL) == 12
    assert record_types.count(DataRecordType.VOLATILITY_RETURN_INPUT) == 3
    assert record_types.count(DataRecordType.OFFICIAL_DOCUMENT_EVENT) == 2
    assert record_types.count(DataRecordType.OFFICIAL_DOCUMENT_CONTENT) == 2
    assert record_types.count(DataRecordType.SOCIAL_ATTENTION) == 1
    assert record_types.count(DataRecordType.MACRO_RATE_OBSERVATION) == 2
    assert record_types.count(DataRecordType.CRISIS_WINDOW_DEFINITION) == 1
    macro_payloads = [
        item.payload
        for item in all_observations
        if item.payload.record_type == "macro_rate_observation"
    ]
    assert all(isinstance(item, MacroRateObservationPayload) for item in macro_payloads)
    assert {
        item.rate_change for item in macro_payloads if isinstance(item, MacroRateObservationPayload)
    } == {
        Decimal("-0.20"),
        Decimal("0.10"),
    }
    crisis_payload = next(
        item.payload
        for item in all_observations
        if item.payload.record_type == "crisis_window_definition"
    )
    assert isinstance(crisis_payload, CrisisWindowDefinitionPayload)
    assert crisis_payload.declared_at < crisis_payload.window_start < crisis_payload.window_end
    listing_statuses = {
        item.payload.status.value
        for item in all_observations
        if item.payload.record_type == "listing_identity"
    }
    assert listing_statuses == {"active", "inactive", "delisted"}
    assert all(
        item.payload.adjustment_basis.value == "raw_unadjusted"
        for item in all_observations
        if item.payload.record_type == "ohlcv_bar"
    )
    assert all(
        {
            DataRecordType(item.payload.record_type)
            for item in first.fetch(capability).batch.normalized_observations
        }
        == CAPABILITY_RECORD_TYPES[capability]
        for capability in DataCapability
    )

    for capability in DataCapability:
        quality = _run(first, capability)
        assert isinstance(quality, QualityAcceptedResult), capability


def test_phase6_macro_regime_payloads_reject_false_change_and_ex_post_window() -> None:
    with pytest.raises(ValidationError, match="current minus previous"):
        MacroRateObservationPayload(
            series_id="synthetic-policy-rate",
            observation_period_end=datetime(2020, 1, 1, tzinfo=UTC).date(),
            released_at=datetime(2020, 1, 2, tzinfo=UTC),
            vintage_id="synthetic-vintage",
            rate_value=Decimal("1.5"),
            previous_rate_value=Decimal("1.4"),
            rate_change=Decimal("0.2"),
        )
    with pytest.raises(ValidationError, match="declared before"):
        CrisisWindowDefinitionPayload(
            crisis_window_id="synthetic-window",
            definition_method_id="predeclared-calendar-window-v1",
            declared_at=datetime(2020, 1, 2, tzinfo=UTC),
            window_start=datetime(2020, 1, 1, tzinfo=UTC),
            window_end=datetime(2020, 1, 3, tzinfo=UTC),
        )


def test_phase6_resolver_binds_original_and_later_correction_to_exact_mapping_sources() -> None:
    source_ids = (
        UUID("dddddddd-dddd-5ddd-8ddd-dddddddddddd"),
        UUID("eeeeeeee-eeee-5eee-8eee-eeeeeeeeeeee"),
    )
    mapping = _mapping(
        CanonicalFamily.C_OFFICIAL_EVENT_TEXT_OVERLAY,
        official_ids=source_ids,
    )
    adapter, catalog = resolve_phase6_synthetic_adapter(mapping)
    official = adapter.fetch(DataCapability.OFFICIAL_DOCUMENT_EVENT_METADATA)

    assert len(catalog.observations) == 1203
    official_source_ids = {
        item.payload.official_source_version_id
        for item in official.batch.normalized_observations
        if isinstance(item.payload, OfficialDocumentContentPayload)
    }
    social_source_ids = {
        item.payload.claimed_official_source_version_id
        for item in official.batch.normalized_observations
        if isinstance(item.payload, SocialAttentionPayload)
    }
    assert official_source_ids == social_source_ids == set(source_ids)
    for source_id in source_ids:
        source_records = [
            item
            for item in official.batch.normalized_observations
            if getattr(item.payload, "official_source_version_id", None) == source_id
            or getattr(item.payload, "claimed_official_source_version_id", None) == source_id
        ]
        assert len(source_records) == 5
        content = [
            item.payload
            for item in source_records
            if isinstance(item.payload, OfficialDocumentContentPayload)
        ]
        assert [item.correction_sequence for item in content] == [0, 1]
        assert content[1].amendment_of_document_id == content[0].official_document_id
        assert content[1].corrected_at is not None
        assert content[1].corrected_at > content[0].accepted_at

    request = SnapshotRequestParameters(
        mapping=mapping,
        as_of_utc=datetime(2022, 1, 1, tzinfo=UTC),
        capability=DataCapability.OFFICIAL_DOCUMENT_EVENT_METADATA,
        mock_configuration_id=PHASE6_SYNTHETIC_MOCK_CONFIGURATION.configuration_id,
    )
    quality = run_mandatory_data_quality(
        request=request,
        result=official,
        configuration=PHASE6_SYNTHETIC_MOCK_CONFIGURATION,
        catalog=catalog,
    )
    assert isinstance(quality, QualityAcceptedResult)


def test_phase6_quality_blocks_sector_overlap_content_tampering_and_correction_timing() -> None:
    adapter = Phase6SyntheticPointInTimeAdapter()

    security = adapter.fetch(DataCapability.SECURITY_MASTER)
    sectors = [
        item
        for item in security.batch.normalized_observations
        if item.payload.record_type == "sector_classification"
    ]
    overlapping = sectors[1].model_copy(update={"instrument_id": sectors[0].instrument_id})
    malformed_security = security.model_copy(
        update={
            "batch": security.batch.model_copy(
                update={
                    "normalized_observations": tuple(
                        overlapping if item is sectors[1] else item
                        for item in security.batch.normalized_observations
                    )
                }
            )
        }
    )
    sector_result = _run(
        adapter,
        DataCapability.SECURITY_MASTER,
        result_override=malformed_security,
    )
    assert isinstance(sector_result, SnapshotBuildBlockedResult)
    assert DataQualityCode.PIT_CLASSIFICATION_INVALID in _blocked_codes(sector_result)

    official = adapter.fetch(DataCapability.OFFICIAL_DOCUMENT_EVENT_METADATA)
    contents = [
        item
        for item in official.batch.normalized_observations
        if item.payload.record_type == "official_document_content"
    ]
    tampered_payload = contents[0].payload.model_copy(update={"document_content_sha256": "0" * 64})
    tampered = contents[0].model_copy(update={"payload": tampered_payload})
    malformed_official = official.model_copy(
        update={
            "batch": official.batch.model_copy(
                update={
                    "normalized_observations": tuple(
                        tampered if item is contents[0] else item
                        for item in official.batch.normalized_observations
                    )
                }
            )
        }
    )
    hash_result = _run(
        adapter,
        DataCapability.OFFICIAL_DOCUMENT_EVENT_METADATA,
        result_override=malformed_official,
    )
    assert isinstance(hash_result, SnapshotBuildBlockedResult)
    assert DataQualityCode.DOCUMENT_CONTENT_HASH_MISMATCH in _blocked_codes(hash_result)

    broken_correction_payload = contents[1].payload.model_copy(
        update={"amendment_of_document_id": "missing-predecessor"}
    )
    broken_correction = contents[1].model_copy(update={"payload": broken_correction_payload})
    malformed_correction = official.model_copy(
        update={
            "batch": official.batch.model_copy(
                update={
                    "normalized_observations": tuple(
                        broken_correction if item is contents[1] else item
                        for item in official.batch.normalized_observations
                    )
                }
            )
        }
    )
    correction_result = _run(
        adapter,
        DataCapability.OFFICIAL_DOCUMENT_EVENT_METADATA,
        result_override=malformed_correction,
    )
    assert isinstance(correction_result, SnapshotBuildBlockedResult)
    assert DataQualityCode.DOCUMENT_CORRECTION_TIMING_INVALID in _blocked_codes(correction_result)


def test_phase6_quality_requires_exact_content_corroboration_source_set() -> None:
    adapter = Phase6SyntheticPointInTimeAdapter()
    official = adapter.fetch(DataCapability.OFFICIAL_DOCUMENT_EVENT_METADATA)
    content = next(
        item
        for item in official.batch.normalized_observations
        if item.payload.record_type == "official_document_content"
    )
    mismatched_payload = content.payload.model_copy(
        update={"official_source_version_id": UUID("dddddddd-dddd-5ddd-8ddd-dddddddddddd")}
    )
    mismatched = content.model_copy(update={"payload": mismatched_payload})
    malformed = official.model_copy(
        update={
            "batch": official.batch.model_copy(
                update={
                    "normalized_observations": tuple(
                        mismatched if item is content else item
                        for item in official.batch.normalized_observations
                    )
                }
            )
        }
    )

    result = _run(
        adapter,
        DataCapability.OFFICIAL_DOCUMENT_EVENT_METADATA,
        result_override=malformed,
    )

    assert isinstance(result, SnapshotBuildBlockedResult)
    assert DataQualityCode.OFFICIAL_CORROBORATION_MISMATCH in _blocked_codes(result)


def test_phase6_quality_blocks_unofficial_social_attention_lineage() -> None:
    adapter = Phase6SyntheticPointInTimeAdapter()
    official = adapter.fetch(DataCapability.OFFICIAL_DOCUMENT_EVENT_METADATA)
    social = next(
        item
        for item in official.batch.normalized_observations
        if isinstance(item.payload, SocialAttentionPayload)
    )
    mismatched_payload = social.payload.model_copy(
        update={"claimed_official_source_version_id": UUID("dddddddd-dddd-5ddd-8ddd-dddddddddddd")}
    )
    mismatched = social.model_copy(update={"payload": mismatched_payload})
    malformed = official.model_copy(
        update={
            "batch": official.batch.model_copy(
                update={
                    "normalized_observations": tuple(
                        mismatched if item is social else item
                        for item in official.batch.normalized_observations
                    )
                }
            )
        }
    )

    result = _run(
        adapter,
        DataCapability.OFFICIAL_DOCUMENT_EVENT_METADATA,
        result_override=malformed,
    )

    assert isinstance(result, SnapshotBuildBlockedResult)
    assert DataQualityCode.OFFICIAL_CORROBORATION_MISMATCH in _blocked_codes(result)
