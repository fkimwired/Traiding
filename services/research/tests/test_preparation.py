from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from fable5_data.contracts import (
    AUTHORIZED_CAPABILITIES,
    AsReportedFundamentalPayload,
    AuthorizedMappingIdentity,
    CorporateActionPayload,
    MembershipStatus,
    OfficialDocumentContentPayload,
    OhlcvBarPayload,
    SnapshotBundle,
    SnapshotRequestParameters,
    SocialAttentionPayload,
    UniverseMembershipPayload,
)
from fable5_data.phase6_synthetic import (
    PHASE6_SYNTHETIC_MOCK_CONFIGURATION,
    resolve_phase6_synthetic_adapter,
)
from fable5_data.quality import QualityAcceptedResult, run_mandatory_data_quality
from fable5_data.snapshots import SnapshotCandidate, build_snapshot_candidate
from fable5_mapping.models import CanonicalFamily, ResearchVerdict
from fable5_research.canonical import (
    PHASE6_CROSS_SECTION_MEMBER_HASH_DOMAIN,
    PHASE6_CROSS_SECTION_RANK_HASH_DOMAIN,
    PHASE6_FIT_NAMESPACE,
    PHASE6_MODEL_OUTPUT_SET_HASH_DOMAIN,
    PHASE6_PIPELINE_INPUT_HASH_DOMAIN,
    PHASE6_TRANSFORM_FIT_HASH_DOMAIN,
    domain_sha256,
    identity,
)
from fable5_research.contracts import (
    PHASE6_LEDGER_CELL_NAMESPACE,
    PHASE6_MODEL_OUTPUT_SET_NAMESPACE,
    BaselineOutcome,
    CrossSectionRankEvidence,
    PreparedFamilyAInputs,
    PreparedFamilyBInputs,
    PreparedFamilyCInputs,
    PreparedResearchPipeline,
    ResearchConfigurationId,
    ResearchTransformFit,
    ResearchTransformTrainingSample,
    frozen_trial_allocation,
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
    assert len(prepared.feature_rows) == 18
    assert len(prepared.scores) == 18
    assert len(prepared.model_output_sets) == 4
    assert all(
        tuple(item.sample_id for item in output_set.outputs)
        == tuple(item.sample_id for item in prepared.feature_rows)
        and tuple(item.sample_id for item in output_set.ledger_cells)
        == tuple(item.sample_id for item in prepared.feature_rows)
        and all(
            cell.synthetic_gross_return
            == (cell.synthetic_research_weight * cell.label_value).quantize(
                Decimal("0.000000000001")
            )
            for cell in output_set.ledger_cells
        )
        for output_set in prepared.model_output_sets
    )
    assert len({item.sample_id for item in prepared.feature_rows}) == 18
    assert len({item.decision_time_utc for item in prepared.feature_rows}) == 18
    assert all(
        any(
            reference.available_at_utc > row.decision_time_utc
            for reference in row.label_source_references
        )
        for row in prepared.feature_rows
    )
    assert all(row.label_value is not None for row in prepared.feature_rows)
    assert prepared.confirmation_interval.label_value is None
    assert prepared.confirmation_interval.label_source_references == ()
    assert prepared.confirmation_interval.label_opened is False
    assert len(prepared.boundary_exclusions) == 1
    assert prepared.boundary_exclusions[0].label_value is None
    assert prepared.boundary_exclusions[0].label_source_references == ()
    assert prepared.boundary_exclusions[0].label_opened is False
    forbidden_ids = {
        prepared.confirmation_interval.sample_id,
        *(item.sample_id for item in prepared.boundary_exclusions),
    }
    assert not forbidden_ids & {item.sample_id for item in prepared.feature_rows}
    assert all(
        not forbidden_ids & {item.sample_id for item in output_set.ledger_cells}
        for output_set in prepared.model_output_sets
    )
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
    prohibited_ids = {
        *(item.sample_id for item in prepared.feature_rows),
        prepared.confirmation_interval.sample_id,
        *(item.sample_id for item in prepared.boundary_exclusions),
    }
    expected_train_ids = {
        f"phase6-a-train-{entity_ordinal:02d}-{position:02d}"
        for entity_ordinal in range(1, 4)
        for position in range(1, 4)
    }
    assert {item.sector_id for item in inputs.universe} == {"synthetic-diversified"}
    assert all(
        len(fit.train_entity_ids) == len(set(fit.train_entity_ids)) == 3
        and set(fit.train_sample_ids) == expected_train_ids
        and tuple(item.sample_id for item in fit.train_samples) == fit.train_sample_ids
        and tuple(item.ordinal for item in fit.train_samples)
        == tuple(range(1, len(fit.train_samples) + 1))
        and {item.entity_id for item in fit.train_samples} == set(fit.train_entity_ids)
        and all(
            reference.available_at_utc <= sample.information_time_utc
            for sample in fit.train_samples
            for reference in sample.source_references
        )
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
    quantum = Decimal("0.000000000001")
    for fit in inputs.train_only_sector_fits:
        raw_values = tuple(item.raw_value for item in fit.train_samples)
        exact_mean = sum(raw_values, Decimal("0")) / Decimal(len(raw_values))
        variance = sum(
            ((item - exact_mean) ** 2 for item in raw_values),
            Decimal("0"),
        ) / Decimal(len(raw_values))
        expected_deviation = variance.sqrt()
        assert fit.mean == exact_mean.quantize(quantum)
        assert fit.standard_deviation == (
            expected_deviation.quantize(quantum)
            if expected_deviation > 0
            else Decimal("1.000000000000")
        )
        assert {
            reference.normalized_observation_id
            for sample in fit.train_samples
            for reference in sample.source_references
        } == {reference.normalized_observation_id for reference in fit.source_references}
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
    assert len(inputs.cross_section_ranks) == len(prepared.feature_rows) == 18
    assert [len(item.eligible_members) for item in inputs.cross_section_ranks] == [
        *([3] * 15),
        *([2] * 3),
    ]
    assert all(
        section.decision_time_utc == row.decision_time_utc
        and section.selected_entity_id == row.entity_id
        and section.selected_linear_rank == 1
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
        and member.membership_status == "included"
        and member.membership_source_reference.record_type == "universe_membership"
        and member.membership_source_reference.listing_id == member.listing_id
        and member.membership_source_reference.available_at_utc <= section.decision_time_utc
        and member.membership_source_reference.valid_from_utc <= section.decision_time_utc
        and (
            member.membership_source_reference.valid_to_utc is None
            or section.decision_time_utc < member.membership_source_reference.valid_to_utc
        )
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
    assert all(
        tuple(item.sample_id for item in comparison.candidate_outputs)
        == tuple(item.sample_id for item in comparison.baseline_outputs)
        for comparison in prepared.baseline_comparisons
    )


def test_family_a_rank_one_selection_is_contract_enforced() -> None:
    prepared = prepare_research_pipeline(
        ResearchConfigurationId.A_PASS,
        _snapshots(_mapping(CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING)),
    )
    inputs = prepared.family_inputs
    assert isinstance(inputs, PreparedFamilyAInputs)
    assert all(section.selected_linear_rank == 1 for section in inputs.cross_section_ranks)

    payload = inputs.cross_section_ranks[0].model_dump(mode="python")
    rank_two = next(member for member in payload["eligible_members"] if member["linear_rank"] == 2)
    payload["selected_entity_id"] = rank_two["entity_id"]
    payload["selected_linear_rank"] = rank_two["linear_rank"]
    payload["selected_nonlinear_score"] = rank_two["nonlinear_score"]
    content = {key: value for key, value in payload.items() if key != "evidence_sha256"}
    payload["evidence_sha256"] = domain_sha256(
        PHASE6_CROSS_SECTION_RANK_HASH_DOMAIN,
        content,
    )
    with pytest.raises(ValidationError, match="linear rank one"):
        CrossSectionRankEvidence.model_validate(payload)


def test_family_a_rejects_a_fundamental_unavailable_at_training_information_time() -> None:
    mapping = _mapping(CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING)
    snapshots = _snapshots(mapping)
    baseline = prepare_research_pipeline(ResearchConfigurationId.A_PASS, snapshots)
    inputs = baseline.family_inputs
    assert isinstance(inputs, PreparedFamilyAInputs)

    target = next(
        observation
        for snapshot in snapshots
        for observation in snapshot.normalized_observations
        if isinstance(observation.payload, AsReportedFundamentalPayload)
        and observation.payload.concept_id == "net_income"
    )
    assert target.listing_id is not None
    entity_training_times = tuple(
        sample.information_time_utc
        for sample in inputs.train_only_sector_fits[0].train_samples
        if sample.entity_id == target.listing_id
    )
    delayed_availability = max(entity_training_times) + timedelta(minutes=1)
    first_evaluation = min(row.decision_time_utc for row in baseline.feature_rows)
    assert delayed_availability < first_evaluation

    modified_snapshots = tuple(
        snapshot.model_copy(
            update={
                "normalized_observations": tuple(
                    (
                        observation.model_copy(update={"available_at": delayed_availability})
                        if observation.normalized_observation_id == target.normalized_observation_id
                        else observation
                    )
                    for observation in snapshot.normalized_observations
                )
            }
        )
        for snapshot in snapshots
    )
    with pytest.raises(ValueError, match="as-reported quality/value inputs are incomplete"):
        prepare_research_pipeline(ResearchConfigurationId.A_PASS, modified_snapshots)

    sample_payload = inputs.train_only_sector_fits[0].train_samples[0].model_dump(mode="python")
    sample_payload["information_time_utc"] = min(
        reference["available_at_utc"] for reference in sample_payload["source_references"]
    ) - timedelta(microseconds=1)
    with pytest.raises(ValidationError, match="available by its information time"):
        ResearchTransformTrainingSample.model_validate(sample_payload)


def test_family_a_excludes_a_bar_present_member_from_exact_pit_membership() -> None:
    mapping = _mapping(CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING)
    snapshots = _snapshots(mapping)
    baseline = prepare_research_pipeline(ResearchConfigurationId.A_PASS, snapshots)
    baseline_inputs = baseline.family_inputs
    assert isinstance(baseline_inputs, PreparedFamilyAInputs)
    first_section = baseline_inputs.cross_section_ranks[0]
    target_listing_id = UUID("44444444-4444-5444-8444-444444444444")
    assert str(target_listing_id) != first_section.selected_entity_id
    assert str(target_listing_id) in {member.entity_id for member in first_section.eligible_members}
    decision = first_section.decision_time_utc
    resume_decision = baseline_inputs.cross_section_ranks[1].decision_time_utc
    assert any(
        observation.listing_id == target_listing_id
        and isinstance(observation.payload, OhlcvBarPayload)
        and observation.available_at <= decision
        for snapshot in snapshots
        for observation in snapshot.normalized_observations
    )

    found_statuses: set[MembershipStatus] = set()
    modified_snapshots: list[SnapshotBundle] = []
    for snapshot in snapshots:
        modified_observations = []
        for observation in snapshot.normalized_observations:
            if observation.listing_id != target_listing_id or not isinstance(
                observation.payload,
                UniverseMembershipPayload,
            ):
                modified_observations.append(observation)
                continue
            found_statuses.add(observation.payload.status)
            if observation.payload.status is MembershipStatus.INCLUDED:
                modified_observations.append(observation.model_copy(update={"valid_to": decision}))
                modified_observations.append(
                    observation.model_copy(
                        update={
                            "normalized_observation_id": UUID(
                                "77777777-7777-5777-8777-777777777777"
                            ),
                            "event_time": resume_decision,
                            "available_at": resume_decision,
                            "valid_from": resume_decision,
                        }
                    )
                )
            else:
                modified_observations.append(
                    observation.model_copy(
                        update={
                            "event_time": decision,
                            "available_at": decision,
                            "valid_from": decision,
                            "valid_to": resume_decision,
                        }
                    )
                )
        modified_snapshots.append(
            snapshot.model_copy(update={"normalized_observations": tuple(modified_observations)})
        )
    assert found_statuses == {MembershipStatus.INCLUDED, MembershipStatus.EXCLUDED}

    prepared = prepare_research_pipeline(
        ResearchConfigurationId.A_PASS,
        tuple(modified_snapshots),
    )
    inputs = prepared.family_inputs
    assert isinstance(inputs, PreparedFamilyAInputs)
    assert str(target_listing_id) not in {
        member.entity_id for member in inputs.cross_section_ranks[0].eligible_members
    }
    assert len(inputs.cross_section_ranks[0].eligible_members) == 2


def test_family_a_rejects_coherently_rehashed_fit_and_transform_tampering() -> None:
    prepared = prepare_research_pipeline(
        ResearchConfigurationId.A_PASS,
        _snapshots(_mapping(CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING)),
    )
    inputs = prepared.family_inputs
    assert isinstance(inputs, PreparedFamilyAInputs)

    fit_payload = inputs.train_only_sector_fits[0].model_dump(mode="python")
    fit_payload["mean"] += Decimal("1")
    fit_content = {
        key: value
        for key, value in fit_payload.items()
        if key not in {"fit_id", "statistic_sha256"}
    }
    fit_digest = domain_sha256(PHASE6_TRANSFORM_FIT_HASH_DOMAIN, fit_content)
    fit_payload["fit_id"] = identity(PHASE6_FIT_NAMESPACE, fit_digest)
    fit_payload["statistic_sha256"] = fit_digest
    with pytest.raises(ValidationError, match="statistics must derive"):
        ResearchTransformFit.model_validate(fit_payload)

    pipeline_payload = prepared.model_dump(mode="python")
    section = pipeline_payload["family_inputs"]["cross_section_ranks"][0]
    member = next(
        item
        for item in section["eligible_members"]
        if item["entity_id"] != section["selected_entity_id"]
    )
    liquidity = next(item for item in member["features"] if item["feature_name"] == "liquidity")
    liquidity["transformed_value"] += Decimal("0.25")
    member_content = {key: value for key, value in member.items() if key != "member_sha256"}
    member["member_sha256"] = domain_sha256(
        PHASE6_CROSS_SECTION_MEMBER_HASH_DOMAIN,
        member_content,
    )
    section_content = {key: value for key, value in section.items() if key != "evidence_sha256"}
    section["evidence_sha256"] = domain_sha256(
        PHASE6_CROSS_SECTION_RANK_HASH_DOMAIN,
        section_content,
    )
    pipeline_content = {
        key: value for key, value in pipeline_payload.items() if key != "pipeline_input_sha256"
    }
    pipeline_payload["pipeline_input_sha256"] = domain_sha256(
        PHASE6_PIPELINE_INPUT_HASH_DOMAIN,
        pipeline_content,
    )
    with pytest.raises(ValidationError, match="transformed value must derive"):
        PreparedResearchPipeline.model_validate(pipeline_payload)


def test_family_a_label_lineage_includes_every_action_in_the_payoff_window() -> None:
    mapping = _mapping(CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING)
    snapshots = _snapshots(mapping)
    baseline = prepare_research_pipeline(ResearchConfigurationId.A_PASS, snapshots)
    inputs = baseline.family_inputs
    assert isinstance(inputs, PreparedFamilyAInputs)
    action_listing_id = UUID("22222222-2222-5222-8222-222222222222")
    section = next(
        item
        for item in inputs.cross_section_ranks
        if item.selected_entity_id == str(action_listing_id)
    )
    effective_at = section.decision_time_utc + timedelta(hours=12)
    assert effective_at < next(
        member.label_t1_utc
        for member in section.eligible_members
        if member.entity_id == section.selected_entity_id
    )

    found_action = False
    modified_snapshots: list[SnapshotBundle] = []
    for snapshot in snapshots:
        observations = []
        for observation in snapshot.normalized_observations:
            if observation.listing_id == action_listing_id and isinstance(
                observation.payload,
                CorporateActionPayload,
            ):
                found_action = True
                observations.append(
                    observation.model_copy(
                        update={
                            "payload": observation.payload.model_copy(
                                update={"effective_at": effective_at}
                            )
                        }
                    )
                )
            else:
                observations.append(observation)
        modified_snapshots.append(
            snapshot.model_copy(update={"normalized_observations": tuple(observations)})
        )
    assert found_action

    prepared = prepare_research_pipeline(
        ResearchConfigurationId.A_PASS,
        tuple(modified_snapshots),
    )
    prepared_inputs = prepared.family_inputs
    assert isinstance(prepared_inputs, PreparedFamilyAInputs)
    prepared_section = next(
        item for item in prepared_inputs.cross_section_ranks if item.ordinal == section.ordinal
    )
    action_member = next(
        member
        for member in prepared_section.eligible_members
        if member.entity_id == str(action_listing_id)
    )
    assert "corporate_action" in {
        reference.record_type for reference in action_member.label_source_references
    }
    if prepared_section.selected_entity_id == str(action_listing_id):
        assert prepared.feature_rows[section.ordinal - 1].label_source_references == (
            action_member.label_source_references
        )


def test_phase5_model_output_registry_rejects_coherent_cell_rehash() -> None:
    prepared = prepare_research_pipeline(
        ResearchConfigurationId.B_PASS,
        _snapshots(_mapping(CanonicalFamily.B_TIME_SERIES_MOMENTUM_REGIME)),
    )
    payload = prepared.model_dump(mode="python")
    output_set = payload["model_output_sets"][0]
    output_set["outputs"][0]["output_value"] += Decimal("0.125")
    output_values = tuple(
        sorted((item["sample_id"], item["output_value"]) for item in output_set["outputs"])
    )
    output_set["model_output_sha256"] = domain_sha256(
        PHASE6_MODEL_OUTPUT_SET_HASH_DOMAIN,
        output_values,
    )
    for cell in output_set["ledger_cells"]:
        cell["model_output_sha256"] = output_set["model_output_sha256"]
        if cell["sample_id"] == output_set["outputs"][0]["sample_id"]:
            cell["model_output"] += Decimal("0.125")
            weight, rule = frozen_trial_allocation(
                trial_key=cell["trial_key"],
                model_id=cell["model_id"],
                sample_id=cell["sample_id"],
                model_output=cell["model_output"],
            )
            cell["synthetic_research_weight"] = weight
            cell["allocation_rule_id"] = rule
            cell["return_status"] = "observed" if weight == 1 else "no_trade"
            cell["synthetic_gross_return"] = (weight * cell["label_value"]).quantize(
                Decimal("0.000000000001")
            )
        cell_content = {
            key: value for key, value in cell.items() if key not in {"cell_id", "cell_sha256"}
        }
        cell_digest = domain_sha256("phase6-research-ledger-cell-v2", cell_content)
        cell["cell_id"] = identity(PHASE6_LEDGER_CELL_NAMESPACE, cell_digest)
        cell["cell_sha256"] = cell_digest
    output_content = {
        key: value
        for key, value in output_set.items()
        if key not in {"output_set_id", "output_set_sha256"}
    }
    output_digest = domain_sha256(
        "phase6-phase5-model-output-registry-entry-v2",
        output_content,
    )
    output_set["output_set_id"] = identity(PHASE6_MODEL_OUTPUT_SET_NAMESPACE, output_digest)
    output_set["output_set_sha256"] = output_digest
    pipeline_content = {
        key: value for key, value in payload.items() if key != "pipeline_input_sha256"
    }
    payload["pipeline_input_sha256"] = domain_sha256(
        PHASE6_PIPELINE_INPUT_HASH_DOMAIN,
        pipeline_content,
    )
    with pytest.raises(ValidationError, match="label-independent cell"):
        PreparedResearchPipeline.model_validate(payload)


def test_research_ledger_rejects_coherently_rehashed_label_cell() -> None:
    prepared = prepare_research_pipeline(
        ResearchConfigurationId.C_PASS,
        _snapshots(_mapping(CanonicalFamily.C_OFFICIAL_EVENT_TEXT_OVERLAY)),
    )
    payload = prepared.model_dump(mode="python")
    output_set = payload["model_output_sets"][0]
    cell = output_set["ledger_cells"][0]
    cell["label_value"] += Decimal("0.05")
    cell["label_sha256"] = domain_sha256(
        "phase6-research-ledger-label-v1",
        (
            cell["sample_id"],
            cell["label_value"],
            cell["label_t0_utc"],
            cell["label_t1_utc"],
            cell["label_source_references"],
        ),
    )
    cell["synthetic_gross_return"] = (
        cell["synthetic_research_weight"] * cell["label_value"]
    ).quantize(Decimal("0.000000000001"))
    cell_content = {
        key: value for key, value in cell.items() if key not in {"cell_id", "cell_sha256"}
    }
    cell_digest = domain_sha256("phase6-research-ledger-cell-v2", cell_content)
    cell["cell_id"] = identity(PHASE6_LEDGER_CELL_NAMESPACE, cell_digest)
    cell["cell_sha256"] = cell_digest
    output_content = {
        key: value
        for key, value in output_set.items()
        if key not in {"output_set_id", "output_set_sha256"}
    }
    output_digest = domain_sha256(
        "phase6-phase5-model-output-registry-entry-v2",
        output_content,
    )
    output_set["output_set_id"] = identity(PHASE6_MODEL_OUTPUT_SET_NAMESPACE, output_digest)
    output_set["output_set_sha256"] = output_digest
    pipeline_content = {
        key: value for key, value in payload.items() if key != "pipeline_input_sha256"
    }
    payload["pipeline_input_sha256"] = domain_sha256(
        PHASE6_PIPELINE_INPUT_HASH_DOMAIN,
        pipeline_content,
    )
    with pytest.raises(ValidationError, match="bind the exact prepared labels"):
        PreparedResearchPipeline.model_validate(payload)


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
            "calendar_session",
            "ohlcv_bar",
        }
        assert {item.record_type for item in features["drawdown"].source_references} == {
            "calendar_session",
            "ohlcv_bar",
        }
        adjusted_types = {
            item.record_type for item in features["realized_volatility"].source_references
        }
        assert {
            "calendar_session",
            "ohlcv_bar",
            "corporate_action",
            "volatility_return_input",
        }.issubset(adjusted_types)
        assert "1-5-20-63-126-252" in features["lagged_return"].formula_id
        assert (
            sum(
                item.record_type == "calendar_session"
                for item in features["trend_strength"].source_references
            )
            == 253
        )
        assert (
            sum(
                item.record_type == "ohlcv_bar"
                for item in features["trend_strength"].source_references
            )
            == 253
        )
        assert (
            sum(item.record_type == "calendar_session" for item in row.label_source_references) == 3
        )
        assert sum(item.record_type == "ohlcv_bar" for item in row.label_source_references) == 3


def test_family_b_rejects_a_missing_mid_window_open_session_bar() -> None:
    mapping = _mapping(CanonicalFamily.B_TIME_SERIES_MOMENTUM_REGIME)
    snapshots = _snapshots(mapping)
    baseline = prepare_research_pipeline(ResearchConfigurationId.B_PASS, snapshots)
    first_row = baseline.feature_rows[0]
    trend = next(item for item in first_row.features if item.feature_name == "trend_strength")
    ordered_bar_references = tuple(
        sorted(
            (item for item in trend.source_references if item.record_type == "ohlcv_bar"),
            key=lambda item: item.available_at_utc,
        )
    )
    assert len(ordered_bar_references) == 253
    missing_reference = ordered_bar_references[126]
    instrument_bar_count = sum(
        observation.instrument_id == missing_reference.instrument_id
        and isinstance(observation.payload, OhlcvBarPayload)
        for snapshot in snapshots
        for observation in snapshot.normalized_observations
    )
    assert instrument_bar_count - 1 >= 255

    modified_snapshots = tuple(
        snapshot.model_copy(
            update={
                "normalized_observations": tuple(
                    observation
                    for observation in snapshot.normalized_observations
                    if observation.normalized_observation_id
                    != missing_reference.normalized_observation_id
                )
            }
        )
        for snapshot in snapshots
    )
    with pytest.raises(ValueError, match="every exact lag and label session"):
        prepare_research_pipeline(ResearchConfigurationId.B_PASS, modified_snapshots)


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
    assert len(non_text) == len(prepared.feature_rows) == 18
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
