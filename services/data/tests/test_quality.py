from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

import pytest
from fable5_data.contracts import (
    AdapterAvailableResult,
    AdapterBatchDraft,
    AuthorizedMappingIdentity,
    ConstituentDisposition,
    DataCapability,
    DataQualityCode,
    DataRecordType,
    DelistingEventPayload,
    FindingDisposition,
    SnapshotBuildBlockedResult,
    SnapshotRequestParameters,
)
from fable5_data.quality import (
    DATASET_GRAIN_KEY_MATRIX,
    QualityAcceptedResult,
    QualityReferenceCatalog,
    constituent_sort_key,
    finding_sort_key,
    run_mandatory_data_quality,
)
from fable5_data.snapshots import SnapshotCandidate, build_snapshot_candidate
from fable5_data.synthetic import (
    SYNTHETIC_MOCK_CONFIGURATION,
    SyntheticPointInTimeAdapter,
    load_fixture_records,
)
from fable5_mapping.models import CanonicalFamily, ResearchVerdict

_OFFICIAL_SOURCE_VERSION_ID = UUID("cccccccc-cccc-5ccc-8ccc-cccccccccccc")


def _family(capability: DataCapability) -> CanonicalFamily:
    if capability is DataCapability.OFFICIAL_DOCUMENT_EVENT_METADATA:
        return CanonicalFamily.C_OFFICIAL_EVENT_TEXT_OVERLAY
    if capability in {
        DataCapability.TRADING_CALENDAR,
        DataCapability.VOLATILITY_RETURN_INPUTS,
    }:
        return CanonicalFamily.B_TIME_SERIES_MOMENTUM_REGIME
    return CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING


def _request(
    capability: DataCapability,
    *,
    as_of: datetime = datetime(2021, 1, 1, tzinfo=UTC),
    official_ids: tuple[UUID, ...] | None = None,
) -> SnapshotRequestParameters:
    family = _family(capability)
    if official_ids is None:
        official_ids = (
            (_OFFICIAL_SOURCE_VERSION_ID,)
            if family is CanonicalFamily.C_OFFICIAL_EVENT_TEXT_OVERLAY
            else ()
        )
    mapping = AuthorizedMappingIdentity(
        mapping_id=UUID("aaaaaaaa-aaaa-5aaa-8aaa-aaaaaaaaaaaa"),
        mapping_version=1,
        mapping_input_sha256="1" * 64,
        mapper_rule_set_version="phase3-test-rules",
        mapper_rule_set_sha256="2" * 64,
        canonical_family=family,
        verdict=ResearchVerdict.BUILD_RESEARCH,
        official_corroboration_source_version_ids=official_ids,
    )
    return SnapshotRequestParameters(
        mapping=mapping,
        as_of_utc=as_of,
        capability=capability,
        mock_configuration_id=SYNTHETIC_MOCK_CONFIGURATION.configuration_id,
    )


def _catalog(adapter: SyntheticPointInTimeAdapter) -> QualityReferenceCatalog:
    return QualityReferenceCatalog.from_results(adapter.all_results())


def _run(
    adapter: SyntheticPointInTimeAdapter,
    capability: DataCapability,
    *,
    as_of: datetime = datetime(2021, 1, 1, tzinfo=UTC),
    official_ids: tuple[UUID, ...] | None = None,
    result: AdapterAvailableResult | None = None,
) -> QualityAcceptedResult | SnapshotBuildBlockedResult:
    return run_mandatory_data_quality(
        request=_request(capability, as_of=as_of, official_ids=official_ids),
        result=adapter.fetch(capability) if result is None else result,
        configuration=SYNTHETIC_MOCK_CONFIGURATION,
        catalog=_catalog(adapter),
    )


def _record(records: list[dict[str, object]], alias: str) -> dict[str, object]:
    return next(item for item in records if item["alias"] == alias)


def _mutable_records() -> list[dict[str, object]]:
    return [deepcopy(item) for item in load_fixture_records()]


def _codes(result: SnapshotBuildBlockedResult) -> set[DataQualityCode]:
    return {item.code for item in result.quality_findings}


@pytest.mark.parametrize("capability", tuple(DataCapability))
def test_all_nine_capabilities_pass_mandatory_quality_on_point_in_time_fixtures(
    capability: DataCapability,
) -> None:
    adapter = SyntheticPointInTimeAdapter()

    result = _run(adapter, capability)

    assert isinstance(result, QualityAcceptedResult)
    assert result.constituents == tuple(sorted(result.constituents, key=constituent_sort_key))
    assert result.batch.quality_findings == tuple(
        sorted(result.batch.quality_findings, key=finding_sort_key)
    )
    assert all(
        item.available_at <= datetime(2021, 1, 1, tzinfo=UTC)
        for item in result.batch.normalized_observations
    )


@pytest.mark.parametrize("capability", tuple(DataCapability))
def test_quality_and_snapshot_materialization_preserve_identical_constituent_dispositions(
    capability: DataCapability,
) -> None:
    adapter = SyntheticPointInTimeAdapter()
    request = _request(capability)
    adapter_result = adapter.fetch(capability)
    quality = run_mandatory_data_quality(
        request=request,
        result=adapter_result,
        configuration=SYNTHETIC_MOCK_CONFIGURATION,
        catalog=_catalog(adapter),
    )
    assert isinstance(quality, QualityAcceptedResult)

    candidate = build_snapshot_candidate(
        mapping=request.mapping,
        request=request,
        profile=adapter_result.profile,
        configuration=SYNTHETIC_MOCK_CONFIGURATION,
        batch=quality.batch,
    )
    assert isinstance(candidate, SnapshotCandidate)
    expected = tuple(
        (item.normalized_content_sha256, item.disposition) for item in quality.constituents
    )
    actual = tuple(
        (item.normalized_content_sha256, item.disposition) for item in candidate.bundle.constituents
    )
    assert actual == expected


def test_grain_key_matrix_covers_every_record_type_with_nonempty_natural_keys() -> None:
    assert set(DATASET_GRAIN_KEY_MATRIX) == set(DataRecordType)
    assert all(item.grain and item.natural_key_fields for item in DATASET_GRAIN_KEY_MATRIX.values())
    assert DATASET_GRAIN_KEY_MATRIX[DataRecordType.UNIVERSE_MEMBERSHIP].natural_key_fields == (
        "payload.universe_id",
        "listing_id",
        "valid_from",
    )
    assert (
        "payload.fiscal_period_end"
        in DATASET_GRAIN_KEY_MATRIX[DataRecordType.AS_REPORTED_FUNDAMENTAL].natural_key_fields
    )


def test_future_availability_is_excluded_and_fundamental_vintages_replay_as_of() -> None:
    adapter = SyntheticPointInTimeAdapter()

    before_amendment = _run(adapter, DataCapability.AS_REPORTED_FUNDAMENTALS)
    after_amendment = _run(
        adapter,
        DataCapability.AS_REPORTED_FUNDAMENTALS,
        as_of=datetime(2023, 1, 1, tzinfo=UTC),
    )

    assert isinstance(before_amendment, QualityAcceptedResult)
    assert len(before_amendment.batch.normalized_observations) == 1
    assert before_amendment.batch.normalized_observations[0].revision_id.endswith("r1")
    assert any(
        finding.code is DataQualityCode.FUTURE_AVAILABILITY_EXCLUDED
        and finding.disposition is FindingDisposition.EXCLUDED
        for finding in before_amendment.batch.quality_findings
    )
    assert isinstance(after_amendment, QualityAcceptedResult)
    assert len(after_amendment.batch.normalized_observations) == 2
    dispositions = {item.revision_id: item.disposition for item in after_amendment.constituents}
    assert dispositions["fundamental-revenue-2019-r1"] is (
        ConstituentDisposition.RETAINED_HISTORICAL_VINTAGE
    )
    assert dispositions["fundamental-revenue-2019-r2"] is (ConstituentDisposition.INCLUDED_AS_OF)


def test_exact_key_vintage_duplicate_blocks_but_near_duplicate_is_retained_with_warning() -> None:
    exact_records = _mutable_records()
    exact_copy = deepcopy(_record(exact_records, "bar_adjusted"))
    exact_copy.update(
        {
            "alias": "bar_adjusted_exact_copy",
            "source_record_id": "synthetic-bar-exact-copy",
            "revision_id": "bar-adjusted-exact-copy-r1",
        }
    )
    exact_records.append(exact_copy)
    exact_adapter = SyntheticPointInTimeAdapter(tuple(exact_records))

    exact_result = _run(exact_adapter, DataCapability.OHLCV)

    assert isinstance(exact_result, SnapshotBuildBlockedResult)
    assert DataQualityCode.EXACT_DUPLICATE_KEY in _codes(exact_result)

    near_records = _mutable_records()
    near_copy = deepcopy(_record(near_records, "bar_adjusted"))
    near_key = cast(dict[str, object], near_copy["logical_key"])
    near_copy.update(
        {
            "alias": "bar_adjusted_near_copy",
            "source_record_id": "synthetic-bar-near-copy",
            "logical_key": {**near_key, "source_feed": "secondary"},
            "revision_id": "bar-adjusted-near-copy-r1",
            "vintage_id": "bar-adjusted-near-copy-v1",
        }
    )
    near_records.append(near_copy)
    near_adapter = SyntheticPointInTimeAdapter(tuple(near_records))

    near_result = _run(near_adapter, DataCapability.OHLCV)

    assert isinstance(near_result, QualityAcceptedResult)
    assert len(near_result.batch.normalized_observations) == 2
    assert any(
        item.code is DataQualityCode.NEAR_DUPLICATE_RETAINED
        and item.disposition is FindingDisposition.RETAINED
        for item in near_result.batch.quality_findings
    )


def test_timestamp_order_required_identifiers_and_metadata_consistency_fail_closed() -> None:
    adapter = SyntheticPointInTimeAdapter()
    original = adapter.fetch(DataCapability.OHLCV)
    observation = original.batch.normalized_observations[0]
    invalid = observation.model_copy(
        update={
            "retrieved_at": observation.available_at - timedelta(seconds=1),
            "source_record_id": "",
            "calendar_id": "XNAS",
        }
    )
    batch = original.batch.model_copy(update={"normalized_observations": (invalid,)})
    malformed = original.model_copy(update={"batch": batch})

    result = _run(adapter, DataCapability.OHLCV, result=malformed)

    assert isinstance(result, SnapshotBuildBlockedResult)
    assert {
        DataQualityCode.INVALID_TIMESTAMP_ORDER,
        DataQualityCode.REQUIRED_FIELD_MISSING,
        DataQualityCode.UNIT_CURRENCY_CALENDAR_TIMEZONE_MISMATCH,
    }.issubset(_codes(result))


def test_orphan_instrument_and_listing_reference_is_blocked() -> None:
    records = _mutable_records()
    bar = _record(records, "bar_adjusted")
    bar["instrument_id"] = "99999999-9999-5999-8999-999999999999"
    adapter = SyntheticPointInTimeAdapter(tuple(records))

    result = _run(adapter, DataCapability.OHLCV)

    assert isinstance(result, SnapshotBuildBlockedResult)
    assert DataQualityCode.ORPHAN_REFERENCE in _codes(result)


def test_current_universe_substitution_is_blocked_when_no_historical_interval_covers_as_of() -> (
    None
):
    adapter = SyntheticPointInTimeAdapter()

    result = _run(
        adapter,
        DataCapability.UNIVERSE_MEMBERSHIP,
        as_of=datetime(2018, 6, 1, tzinfo=UTC),
    )

    assert isinstance(result, SnapshotBuildBlockedResult)
    assert DataQualityCode.CURRENT_UNIVERSE_LEAKAGE in _codes(result)


def test_fundamental_amendment_must_restate_exact_earlier_same_key_revision() -> None:
    records = _mutable_records()
    amendment = _record(records, "fundamental_amendment")
    payload = cast(dict[str, object], amendment["payload"])
    payload["restates_revision_alias"] = "corporate_action_split"
    adapter = SyntheticPointInTimeAdapter(tuple(records))

    result = _run(
        adapter,
        DataCapability.AS_REPORTED_FUNDAMENTALS,
        as_of=datetime(2023, 1, 1, tzinfo=UTC),
    )

    assert isinstance(result, SnapshotBuildBlockedResult)
    assert DataQualityCode.RESTATEMENT_LEAKAGE in _codes(result)


def test_adjusted_bar_cannot_reference_corporate_action_available_after_adjustment_as_of() -> None:
    records = _mutable_records()
    action = _record(records, "corporate_action_split")
    action["event_time"] = "2020-01-20T21:01:00Z"
    action["available_at"] = "2020-01-20T21:02:00Z"
    payload = cast(dict[str, object], action["payload"])
    payload["announcement_at"] = "2020-01-20T21:01:00Z"
    adapter = SyntheticPointInTimeAdapter(tuple(records))

    result = _run(adapter, DataCapability.OHLCV)

    assert isinstance(result, SnapshotBuildBlockedResult)
    assert DataQualityCode.CORPORATE_ACTION_LOOKAHEAD in _codes(result)


def test_delisting_null_is_explicit_and_never_synthesized_to_zero() -> None:
    adapter = SyntheticPointInTimeAdapter()

    result = _run(
        adapter,
        DataCapability.DELISTINGS,
        as_of=datetime(2024, 1, 1, tzinfo=UTC),
    )

    assert isinstance(result, QualityAcceptedResult)
    assert len(result.batch.normalized_observations) == 1
    observation = result.batch.normalized_observations[0]
    assert isinstance(observation.payload, DelistingEventPayload)
    assert observation.payload.delisting_return is None
    assert result.constituents[0].disposition is ConstituentDisposition.EXPLICIT_MISSINGNESS
    assert any(
        item.code is DataQualityCode.MISSING_DELISTING_RETURN
        and item.disposition is FindingDisposition.RETAINED
        for item in result.batch.quality_findings
    )


def test_volatility_inputs_require_exact_typed_available_references() -> None:
    records = _mutable_records()
    volatility = _record(records, "volatility_input")
    payload = cast(dict[str, object], volatility["payload"])
    payload["bar_observation_aliases"] = ["official_document"]
    adapter = SyntheticPointInTimeAdapter(tuple(records))

    result = _run(adapter, DataCapability.VOLATILITY_RETURN_INPUTS)

    assert isinstance(result, SnapshotBuildBlockedResult)
    assert DataQualityCode.ORPHAN_REFERENCE in _codes(result)


def test_family_c_requires_exact_persisted_official_source_version_set() -> None:
    adapter = SyntheticPointInTimeAdapter()

    result = _run(
        adapter,
        DataCapability.OFFICIAL_DOCUMENT_EVENT_METADATA,
        official_ids=(UUID("dddddddd-dddd-5ddd-8ddd-dddddddddddd"),),
    )

    assert isinstance(result, SnapshotBuildBlockedResult)
    assert DataQualityCode.ORPHAN_REFERENCE in _codes(result)


def test_unaccounted_raw_and_revision_rows_block_normalization_coverage() -> None:
    adapter = SyntheticPointInTimeAdapter()
    original = adapter.fetch(DataCapability.AS_REPORTED_FUNDAMENTALS)
    original_only = original.batch.normalized_observations[:1]
    incomplete_batch = AdapterBatchDraft(
        raw_observations=original.batch.raw_observations,
        revisions=original.batch.revisions,
        normalized_observations=original_only,
        quality_findings=(),
    )
    incomplete = AdapterAvailableResult(
        profile=original.profile,
        capability=original.capability,
        batch=incomplete_batch,
    )

    result = _run(
        adapter,
        DataCapability.AS_REPORTED_FUNDAMENTALS,
        as_of=datetime(2023, 1, 1, tzinfo=UTC),
        result=incomplete,
    )

    assert isinstance(result, SnapshotBuildBlockedResult)
    assert DataQualityCode.RAW_NORMALIZED_LINEAGE_GAP in _codes(result)


def test_quality_results_and_sanitized_findings_are_reproducible() -> None:
    adapter = SyntheticPointInTimeAdapter()

    first = _run(adapter, DataCapability.AS_REPORTED_FUNDAMENTALS)
    second = _run(adapter, DataCapability.AS_REPORTED_FUNDAMENTALS)

    assert first == second
    assert isinstance(first, QualityAcceptedResult)
    rendered = first.model_dump_json().casefold()
    assert "sk-" not in rendered
    assert "://" not in rendered
    assert "password" not in rendered
    for finding in first.batch.quality_findings:
        assert finding.occurrence_count >= 1
        assert finding.occurrence_rate is not None
        assert (finding.range_start_utc is None) == (finding.range_end_utc is None)
