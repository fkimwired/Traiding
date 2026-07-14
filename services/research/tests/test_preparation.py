from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from fable5_data.contracts import (
    AUTHORIZED_CAPABILITIES,
    AuthorizedMappingIdentity,
    OfficialDocumentContentPayload,
    SnapshotBundle,
    SnapshotRequestParameters,
    SocialAttentionPayload,
)
from fable5_data.phase6_synthetic import (
    PHASE6_SYNTHETIC_MOCK_CONFIGURATION,
    resolve_phase6_synthetic_adapter,
)
from fable5_data.quality import QualityAcceptedResult, run_mandatory_data_quality
from fable5_data.snapshots import SnapshotCandidate, build_snapshot_candidate
from fable5_mapping.models import CanonicalFamily, ResearchVerdict
from fable5_research.canonical import PHASE6_MODEL_OUTPUT_SET_HASH_DOMAIN, domain_sha256
from fable5_research.contracts import (
    BaselineOutcome,
    PreparedFamilyAInputs,
    PreparedFamilyBInputs,
    PreparedFamilyCInputs,
    PreparedResearchPipeline,
    ResearchConfigurationId,
    ResearchTransformFit,
)
from fable5_research.preparation import prepare_research_pipeline
from pydantic import ValidationError

_SOURCE_ID = UUID("dddddddd-dddd-5ddd-8ddd-dddddddddddd")


def _mapping(family: CanonicalFamily) -> AuthorizedMappingIdentity:
    digit = {
        CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING: "a",
        CanonicalFamily.B_TIME_SERIES_MOMENTUM_REGIME: "b",
        CanonicalFamily.C_OFFICIAL_EVENT_TEXT_OVERLAY: "c",
    }[family]
    return AuthorizedMappingIdentity(
        mapping_id=UUID(f"{digit * 8}-{digit * 4}-5{digit * 3}-8{digit * 3}-{digit * 12}"),
        mapping_version=1,
        mapping_input_sha256="1" * 64,
        mapper_rule_set_version="phase6-preparation-tests-v1",
        mapper_rule_set_sha256="2" * 64,
        canonical_family=family,
        verdict=ResearchVerdict.BUILD_RESEARCH,
        official_corroboration_source_version_ids=(
            (_SOURCE_ID,) if family is CanonicalFamily.C_OFFICIAL_EVENT_TEXT_OVERLAY else ()
        ),
    )


def _snapshots(mapping: AuthorizedMappingIdentity) -> tuple[SnapshotBundle, ...]:
    adapter, catalog = resolve_phase6_synthetic_adapter(mapping)
    snapshots: list[SnapshotBundle] = []
    for capability in sorted(AUTHORIZED_CAPABILITIES[mapping.canonical_family], key=str):
        request = SnapshotRequestParameters(
            mapping=mapping,
            as_of_utc=datetime(2022, 1, 1, tzinfo=UTC),
            capability=capability,
            mock_configuration_id=PHASE6_SYNTHETIC_MOCK_CONFIGURATION.configuration_id,
        )
        quality = run_mandatory_data_quality(
            request=request,
            result=adapter.fetch(capability),
            configuration=PHASE6_SYNTHETIC_MOCK_CONFIGURATION,
            catalog=catalog,
        )
        assert isinstance(quality, QualityAcceptedResult)
        candidate = build_snapshot_candidate(
            mapping=mapping,
            request=request,
            profile=adapter.profile,
            configuration=PHASE6_SYNTHETIC_MOCK_CONFIGURATION,
            batch=quality.batch,
        )
        assert isinstance(candidate, SnapshotCandidate)
        snapshots.append(candidate.bundle)
    return tuple(snapshots)


@pytest.mark.parametrize(
    ("configuration_id", "family"),
    (
        (
            ResearchConfigurationId.A_PASS,
            CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING,
        ),
        (
            ResearchConfigurationId.B_PASS,
            CanonicalFamily.B_TIME_SERIES_MOMENTUM_REGIME,
        ),
        (
            ResearchConfigurationId.C_PASS,
            CanonicalFamily.C_OFFICIAL_EVENT_TEXT_OVERLAY,
        ),
    ),
)
def test_prepared_pipeline_is_deterministic_and_has_unique_evaluation_geometry(
    configuration_id: ResearchConfigurationId,
    family: CanonicalFamily,
) -> None:
    snapshots = _snapshots(_mapping(family))
    prepared = prepare_research_pipeline(configuration_id, snapshots)
    repeated = prepare_research_pipeline(configuration_id, snapshots)

    assert prepared == repeated
    assert len(prepared.feature_rows) == 20
    assert len(prepared.scores) == 20
    assert len({item.sample_id for item in prepared.feature_rows}) == 20
    assert len({item.decision_time_utc for item in prepared.feature_rows}) == 20
    assert all(
        any(
            reference.available_at_utc > row.decision_time_utc
            for reference in row.label_source_references
        )
        for row in prepared.feature_rows
    )
    assert all(row.label_value is not None for row in prepared.feature_rows)
    assert all(
        item.candidate_output_sha256 != item.label_sha256 for item in prepared.baseline_comparisons
    )

    tampered = prepared.model_dump(mode="python")
    tampered["pipeline_input_sha256"] = "0" * 64
    with pytest.raises(ValidationError, match="pipeline input hash"):
        PreparedResearchPipeline.model_validate(tampered)


def test_family_a_uses_actual_frozen_features_and_pooled_train_only_sector_fits() -> None:
    prepared = prepare_research_pipeline(
        ResearchConfigurationId.A_PASS,
        _snapshots(_mapping(CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING)),
    )
    inputs = prepared.family_inputs
    assert isinstance(inputs, PreparedFamilyAInputs)
    assert len(inputs.train_only_sector_fits) == 6
    assert {item.feature_name for item in inputs.train_only_sector_fits} == {
        "liquidity",
        "momentum",
        "quality",
        "turnover",
        "value",
        "volatility",
    }
    fit_ids = {item.fit_id for item in inputs.train_only_sector_fits}
    assert all(
        value.train_fit_id in fit_ids for row in prepared.feature_rows for value in row.features
    )
    first_decision = min(item.decision_time_utc for item in prepared.feature_rows)
    prohibited_ids = {item.sample_id for item in prepared.feature_rows}
    expected_train_ids = {
        f"phase6-a-train-{entity_ordinal:02d}-{position:02d}"
        for entity_ordinal in range(1, 4)
        for position in range(1, 4)
    }
    assert {item.sector_id for item in inputs.universe} == {"synthetic-diversified"}
    assert all(
        len(fit.train_entity_ids) == len(set(fit.train_entity_ids)) == 3
        and set(fit.train_sample_ids) == expected_train_ids
        and set(fit.prohibited_sample_ids) == prohibited_ids
        and not set(fit.train_sample_ids) & set(fit.prohibited_sample_ids)
        and {
            reference.listing_id
            for reference in fit.source_references
            if reference.listing_id is not None
        }
        == set(fit.train_entity_ids)
        for fit in inputs.train_only_sector_fits
    )
    assert all(
        reference.available_at_utc < first_decision
        for fit in inputs.train_only_sector_fits
        for reference in fit.source_references
    )
    assert {item.transform_id for item in inputs.train_only_sector_fits} == {
        "phase6-within-sector-pooled-standardizer-clipped-3-v2"
    }
    invalid_fit = inputs.train_only_sector_fits[0].model_dump(mode="python")
    invalid_fit["train_entity_ids"] = invalid_fit["train_entity_ids"][:1]
    with pytest.raises(ValidationError, match="at least 2 items"):
        ResearchTransformFit.model_validate(invalid_fit)
    assert len(inputs.cross_section_ranks) == len(prepared.feature_rows) == 20
    assert [len(item.eligible_members) for item in inputs.cross_section_ranks] == [
        *([3] * 15),
        *([2] * 5),
    ]
    assert all(
        section.decision_time_utc == row.decision_time_utc
        and section.selected_entity_id == row.entity_id
        and tuple(
            member.linear_rank
            for member in sorted(
                section.eligible_members,
                key=lambda member: member.linear_rank,
            )
        )
        == tuple(range(1, len(section.eligible_members) + 1))
        for section, row in zip(inputs.cross_section_ranks, prepared.feature_rows, strict=True)
    )
    assert all(
        member.label_t1_utc > section.decision_time_utc
        and any(
            reference.available_at_utc > section.decision_time_utc
            for reference in member.label_source_references
        )
        for section in inputs.cross_section_ranks
        for member in section.eligible_members
    )
    nonlinear_scores = {
        member.nonlinear_score
        for section in inputs.cross_section_ranks
        for member in section.eligible_members
    }
    assert nonlinear_scores == {
        Decimal("-0.35"),
        Decimal("0.15"),
        Decimal("0.35"),
    }
    assert all(
        comparison.evaluation_scope == "descriptive_all_prepared_rows_not_used_for_selection"
        and comparison.used_for_selection is False
        for comparison in prepared.baseline_comparisons
    )
    assert prepared.baseline_comparisons[0].outcome is BaselineOutcome.SURVIVES
    assert prepared.baseline_comparisons[1].outcome is BaselineOutcome.REJECTED


def test_family_b_separates_raw_nominal_and_action_aware_inputs() -> None:
    prepared = prepare_research_pipeline(
        ResearchConfigurationId.B_PASS,
        _snapshots(_mapping(CanonicalFamily.B_TIME_SERIES_MOMENTUM_REGIME)),
    )
    inputs = prepared.family_inputs
    assert isinstance(inputs, PreparedFamilyBInputs)
    assert inputs.lag_windows == (1, 5, 20, 63, 126, 252)
    assert inputs.raw_nominal_bar_count >= 253
    assert inputs.adjusted_return_observation_count >= 252
    assert {item.listing_status for item in inputs.lifecycle_tests} == {
        "active",
        "inactive",
        "delisted",
    }
    assert all(item.used_as_feature is False for item in inputs.lifecycle_tests)
    assert all(
        (item.termination_at_utc is None) == (item.listing_status == "active")
        for item in inputs.lifecycle_tests
    )
    delisted_test = next(
        item for item in inputs.lifecycle_tests if item.listing_status == "delisted"
    )
    assert delisted_test.delisting_return_handled is True
    assert {reference.record_type for reference in delisted_test.source_references} >= {
        "delisting_event",
        "listing_identity",
        "universe_membership",
        "volatility_return_input",
    }
    for row in prepared.feature_rows:
        features = {item.feature_name: item for item in row.features}
        assert {item.record_type for item in features["trend_strength"].source_references} == {
            "ohlcv_bar"
        }
        assert {item.record_type for item in features["drawdown"].source_references} == {
            "ohlcv_bar"
        }
        adjusted_types = {
            item.record_type for item in features["realized_volatility"].source_references
        }
        assert {"ohlcv_bar", "corporate_action", "volatility_return_input"}.issubset(adjusted_types)
        assert "1-5-20-63-126-252" in features["lagged_return"].formula_id


def test_family_c_uses_exact_social_records_and_latest_known_document_version() -> None:
    snapshots = _snapshots(_mapping(CanonicalFamily.C_OFFICIAL_EVENT_TEXT_OVERLAY))
    prepared = prepare_research_pipeline(ResearchConfigurationId.C_PASS, snapshots)
    inputs = prepared.family_inputs
    assert isinstance(inputs, PreparedFamilyCInputs)
    actual_social_ids = {
        observation.payload.social_attention_record_id
        for snapshot in snapshots
        for observation in snapshot.normalized_observations
        if isinstance(observation.payload, SocialAttentionPayload)
    }
    assert {item.social_attention_record_id for item in inputs.corroborations} == actual_social_ids
    assert all(
        item.social_source_reference.record_type == "social_attention"
        for item in inputs.corroborations
    )
    assert all(
        item.official_source_reference.record_type == "official_document_content"
        for item in inputs.corroborations
    )
    assert {item.correction_sequence for item in inputs.extractions} == {0, 1}
    extraction_by_hash = {item.document_content_sha256: item for item in inputs.extractions}
    document_hash_by_observation_id = {
        observation.normalized_observation_id: observation.payload.document_content_sha256
        for snapshot in snapshots
        for observation in snapshot.normalized_observations
        if isinstance(observation.payload, OfficialDocumentContentPayload)
    }
    for row in prepared.feature_rows:
        observation_id = row.features[0].source_references[0].normalized_observation_id
        assert document_hash_by_observation_id[observation_id] in extraction_by_hash
    assert all(item.score_semantics == "research_score_only" for item in prepared.scores)
    assert len(extraction_by_hash) == 2
    non_text = inputs.non_text_baseline
    assert len(non_text) == len(prepared.feature_rows) == 20
    assert all(item.baseline_output != 0 and item.used_for_selection is False for item in non_text)
    assert all(
        len(item.source_references) == 2
        and {reference.record_type for reference in item.source_references} == {"ohlcv_bar"}
        and all(
            reference.available_at_utc <= item.decision_time_utc
            for reference in item.source_references
        )
        for item in non_text
    )
    comparison = prepared.baseline_comparisons[0]
    assert comparison.outcome is BaselineOutcome.SURVIVES
    assert comparison.baseline_model_id == "lagged-return-range-linear-baseline-v1"
    assert comparison.used_for_selection is False
    assert comparison.baseline_output_sha256 == domain_sha256(
        PHASE6_MODEL_OUTPUT_SET_HASH_DOMAIN,
        tuple((item.sample_id, item.baseline_output) for item in non_text),
    )
