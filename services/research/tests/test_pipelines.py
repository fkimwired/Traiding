from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import UUID

import fable5_research.workflow as workflow_module
import pytest
from fable5_backtester.contracts import GateCode, GateOutcome, PromotionState, TrialStatus
from fable5_backtester.engine import evaluate_synthetic_fixture
from fable5_data.contracts import (
    AUTHORIZED_CAPABILITIES,
    AuthorizedMappingIdentity,
    DataCapability,
    SnapshotBundle,
    SnapshotRequestParameters,
)
from fable5_data.phase6_synthetic import (
    PHASE6_SYNTHETIC_MOCK_CONFIGURATION,
    resolve_phase6_synthetic_adapter,
)
from fable5_data.quality import (
    QualityAcceptedResult,
    run_mandatory_data_quality,
)
from fable5_data.snapshots import SnapshotCandidate, build_snapshot_candidate
from fable5_mapping.models import CanonicalFamily, ResearchVerdict
from fable5_research.artifacts import build_research_artifact
from fable5_research.canonical import PHASE6_ATTEMPT_HASH_DOMAIN, domain_sha256
from fable5_research.contracts import (
    FamilyAEvidence,
    FamilyBEvidence,
    FamilyCEvidence,
    ResearchConfigurationId,
    ResearchRunArtifact,
)
from fable5_research.phase5 import build_phase5_inputs
from fable5_research.preparation import prepare_research_pipeline
from fable5_research.workflow import (
    ResearchWorkflow,
    ResearchWorkflowBlocked,
    missing_official_corroboration_source_ids,
)
from pydantic import ValidationError

_CREATED_AT = datetime(2026, 7, 14, tzinfo=UTC)
_GIT_SHA = "2fc5cdbc90f24dc6bb88060069651456e8cf5350"
_SOURCE_ID = UUID("dddddddd-dddd-5ddd-8ddd-dddddddddddd")


def _mapping(family: CanonicalFamily) -> AuthorizedMappingIdentity:
    index = {
        CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING: "a",
        CanonicalFamily.B_TIME_SERIES_MOMENTUM_REGIME: "b",
        CanonicalFamily.C_OFFICIAL_EVENT_TEXT_OVERLAY: "c",
    }[family]
    return AuthorizedMappingIdentity(
        mapping_id=UUID(f"{index * 8}-{index * 4}-5{index * 3}-8{index * 3}-{index * 12}"),
        mapping_version=1,
        mapping_input_sha256="1" * 64,
        mapper_rule_set_version="phase6-pipeline-tests-v1",
        mapper_rule_set_sha256="2" * 64,
        canonical_family=family,
        verdict=ResearchVerdict.BUILD_RESEARCH,
        official_corroboration_source_version_ids=(
            (_SOURCE_ID,) if family is CanonicalFamily.C_OFFICIAL_EVENT_TEXT_OVERLAY else ()
        ),
    )


def _snapshots(mapping: AuthorizedMappingIdentity) -> tuple[SnapshotBundle, ...]:
    adapter, catalog = resolve_phase6_synthetic_adapter(mapping)
    snapshots = []
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


def test_c_fail_blocks_on_missing_exact_corroboration_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mapping = _mapping(CanonicalFamily.C_OFFICIAL_EVENT_TEXT_OVERLAY)
    snapshots = _snapshots(mapping)
    assert (
        missing_official_corroboration_source_ids(
            ResearchConfigurationId.C_PASS,
            snapshots,
        )
        == ()
    )
    missing = missing_official_corroboration_source_ids(
        ResearchConfigurationId.C_FAIL,
        snapshots,
    )
    assert len(missing) == 1
    assert missing[0] not in mapping.official_corroboration_source_version_ids

    snapshot_by_id = {item.snapshot.snapshot_id: item for item in snapshots}
    snapshot_store = MagicMock()
    snapshot_store.get_snapshot.side_effect = snapshot_by_id.__getitem__
    evaluation_store = MagicMock()
    repository = MagicMock()
    workflow = ResearchWorkflow(
        repository=repository,
        evaluation_repository=evaluation_store,
        snapshot_repository=snapshot_store,
        code_version_git_sha=_GIT_SHA,
    )
    request = {
        "mapping_id": mapping.mapping_id,
        "snapshot_ids": tuple(sorted(snapshot_by_id, key=str)),
        "research_configuration_id": ResearchConfigurationId.C_FAIL,
    }
    from fable5_research.contracts import ResearchRunCreateRequest

    with pytest.raises(ResearchWorkflowBlocked, match="official_corroboration_required"):
        workflow.create_run(ResearchRunCreateRequest.model_validate(request))
    evaluation_store.create_policy.assert_not_called()

    monkeypatch.setattr(
        workflow_module,
        "_C_FAIL_REQUIRED_OFFICIAL_SOURCE_VERSION_ID",
        mapping.official_corroboration_source_version_ids[0],
    )
    assert (
        missing_official_corroboration_source_ids(
            ResearchConfigurationId.C_FAIL,
            snapshots,
        )
        == ()
    )
    evaluation_store.create_policy.side_effect = RuntimeError("corroboration evidence gate passed")
    with pytest.raises(RuntimeError, match="corroboration evidence gate passed"):
        workflow.create_run(ResearchRunCreateRequest.model_validate(request))


@pytest.mark.parametrize(
    ("configuration_id", "expected_state", "expected_special_gate"),
    (
        (ResearchConfigurationId.A_PASS, PromotionState.PASS_RESEARCH, None),
        (ResearchConfigurationId.A_FAIL, PromotionState.FAIL_REJECT, GateCode.COST_STRESS),
        (ResearchConfigurationId.B_PASS, PromotionState.PASS_RESEARCH, None),
        (
            ResearchConfigurationId.B_FAIL,
            PromotionState.RESEARCH_ONLY_REGIME_DEPENDENT,
            GateCode.REGIME,
        ),
        (ResearchConfigurationId.C_PASS, PromotionState.PASS_RESEARCH, None),
    ),
)
def test_deterministic_family_pipelines_use_all_unchanged_phase5_gates(
    configuration_id: ResearchConfigurationId,
    expected_state: PromotionState,
    expected_special_gate: GateCode | None,
) -> None:
    family = {
        ResearchConfigurationId.A_PASS: CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING,
        ResearchConfigurationId.A_FAIL: CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING,
        ResearchConfigurationId.B_PASS: CanonicalFamily.B_TIME_SERIES_MOMENTUM_REGIME,
        ResearchConfigurationId.B_FAIL: CanonicalFamily.B_TIME_SERIES_MOMENTUM_REGIME,
        ResearchConfigurationId.C_PASS: CanonicalFamily.C_OFFICIAL_EVENT_TEXT_OVERLAY,
    }[configuration_id]
    mapping = _mapping(family)
    snapshots = _snapshots(mapping)
    prepared = prepare_research_pipeline(configuration_id, snapshots)
    policy, fixture = build_phase5_inputs(
        configuration_id=configuration_id,
        prepared=prepared,
        snapshots=snapshots,
    )
    report = evaluate_synthetic_fixture(
        policy=policy,
        fixture=fixture,
        mapping=mapping,
        snapshots=snapshots,
        code_version_git_sha=_GIT_SHA,
        created_at_utc=_CREATED_AT,
    )
    repeated = evaluate_synthetic_fixture(
        policy=policy,
        fixture=fixture,
        mapping=mapping,
        snapshots=snapshots,
        code_version_git_sha=_GIT_SHA,
        created_at_utc=_CREATED_AT,
    )

    assert report == repeated
    assert report.promotion_state is expected_state
    assert tuple(item.gate_code for item in report.gates) == tuple(GateCode)
    assert report.raw_trial_count == 6
    assert [item.status for item in report.trials].count(TrialStatus.FAILED) == 1
    assert [item.status for item in report.trials].count(TrialStatus.ABANDONED) == 1
    assert all(
        item.gate_code is GateCode.LEAKAGE or item.outcome is not GateOutcome.BLOCKED_UNCOMPUTABLE
        for item in report.gates
    )
    if expected_special_gate is not None:
        special = next(item for item in report.gates if item.gate_code is expected_special_gate)
        assert special.outcome in {GateOutcome.FAIL, GateOutcome.RESEARCH_ONLY}

    artifact = build_research_artifact(
        configuration_id=configuration_id,
        mapping=mapping,
        prepared=prepared,
        report=report,
    )
    assert artifact.phase5_evaluation.gate_codes == tuple(GateCode)
    assert artifact.phase5_evaluation.promotion_state is expected_state
    assert len(artifact.attempts) == report.raw_trial_count
    assert artifact.phase5_evaluation.phase5_trial_set_sha256 is not None
    assert len({item.phase5_trial_id for item in artifact.attempts}) == report.raw_trial_count
    assert len({item.phase5_trial_key for item in artifact.attempts}) == report.raw_trial_count
    assert tuple(
        (
            attempt.phase5_trial_id,
            attempt.phase5_trial_key,
            attempt.status.value,
            attempt.configuration_sha256,
        )
        for attempt in artifact.attempts
    ) == tuple(
        (trial.trial_id, trial.trial_key, trial.status.value, trial.config_sha256)
        for trial in report.trials
    )

    incomplete = artifact.model_dump(mode="python")
    incomplete["attempts"] = incomplete["attempts"][:-1]
    with pytest.raises(ValidationError, match="attempt count must equal"):
        ResearchRunArtifact.model_validate(incomplete)

    duplicate_identity = artifact.model_dump(mode="python")
    duplicate_identity["attempts"][1]["phase5_trial_id"] = duplicate_identity["attempts"][0][
        "phase5_trial_id"
    ]
    duplicate_identity["attempts"][1]["phase5_trial_key"] = duplicate_identity["attempts"][0][
        "phase5_trial_key"
    ]
    duplicate_content = {
        key: value
        for key, value in duplicate_identity["attempts"][1].items()
        if key != "attempt_sha256"
    }
    duplicate_identity["attempts"][1]["attempt_sha256"] = domain_sha256(
        PHASE6_ATTEMPT_HASH_DOMAIN,
        duplicate_content,
    )
    with pytest.raises(ValidationError, match="unique exact Phase 5 trial IDs and keys"):
        ResearchRunArtifact.model_validate(duplicate_identity)

    wrong_status = artifact.model_dump(mode="python")
    failed_index = next(
        index for index, attempt in enumerate(artifact.attempts) if attempt.status.value == "failed"
    )
    abandoned_index = next(
        index
        for index, attempt in enumerate(artifact.attempts)
        if attempt.status.value == "abandoned"
    )
    wrong_status["attempts"][failed_index]["status"] = "abandoned"
    wrong_status["attempts"][abandoned_index]["status"] = "failed"
    for index in (failed_index, abandoned_index):
        content = {
            key: value
            for key, value in wrong_status["attempts"][index].items()
            if key != "attempt_sha256"
        }
        wrong_status["attempts"][index]["attempt_sha256"] = domain_sha256(
            PHASE6_ATTEMPT_HASH_DOMAIN,
            content,
        )
    with pytest.raises(ValidationError, match="attempt set hash"):
        ResearchRunArtifact.model_validate(wrong_status)
    assert artifact.paper_approval_granted is False
    assert artifact.no_real_performance_claimed is True
    assert artifact.pass_research_is_not_paper_approval is True
    assert len(artifact.scores) == len(artifact.feature_rows)

    if isinstance(artifact.family_evidence, FamilyAEvidence):
        assert {item.listing_status for item in artifact.family_evidence.universe} == {
            "active",
            "inactive",
            "delisted",
        }
        assert all(item.delisting_return_handled for item in artifact.family_evidence.universe)
        assert {item.outcome.value for item in artifact.baseline_comparisons} == {
            "survives",
            "rejected",
        }
        assert artifact.family_evidence.capacity.capacity_limit_breached is False
        fit_ids = {item.fit_id for item in artifact.family_evidence.train_only_sector_fits}
        assert {item.feature_name for item in artifact.family_evidence.train_only_sector_fits} == {
            "liquidity",
            "momentum",
            "quality",
            "turnover",
            "value",
            "volatility",
        }
        assert all(
            value.train_fit_id is not None and value.train_fit_id in fit_ids
            for row in artifact.feature_rows
            for value in row.features
        )
    elif isinstance(artifact.family_evidence, FamilyBEvidence):
        assert artifact.family_evidence.lag_windows == (1, 5, 20, 63, 126, 252)
        assert artifact.family_evidence.nominal_feature_price_basis == "raw_unadjusted"
        assert artifact.family_evidence.no_image_candlestick_or_named_pattern_classifier
        assert {item.listing_status for item in artifact.family_evidence.lifecycle_tests} == {
            "active",
            "inactive",
            "delisted",
        }
        assert artifact.family_evidence.crash_evidence_complete is (
            configuration_id is ResearchConfigurationId.B_PASS
        )
        regime_gate = next(item for item in report.gates if item.gate_code is GateCode.REGIME)
        assert {item.regime_id for item in artifact.family_evidence.regime_results} == {
            item["regime"]
            for item in json.loads(str(regime_gate.results["regime_breakdowns_json"]))
        }
    else:
        assert isinstance(artifact.family_evidence, FamilyCEvidence)
        assert len(artifact.family_evidence.non_text_baseline) == len(artifact.feature_rows)
        assert all(
            item.baseline_output != 0 and item.used_for_selection is False
            for item in artifact.family_evidence.non_text_baseline
        )
        assert artifact.family_evidence.non_text_baseline_model_id == (
            "lagged-return-range-linear-baseline-v1"
        )
        assert {item.correction_sequence for item in artifact.family_evidence.extractions} == {
            0,
            1,
        }
        assert all(
            item.output_boundary == "structured_features_only"
            for item in artifact.family_evidence.extractions
        )
        assert all(
            item.exact_match and not item.contributes_standalone
            for item in artifact.family_evidence.corroborations
        )
        for row in artifact.feature_rows:
            extracted = max(
                (
                    item
                    for item in artifact.family_evidence.extractions
                    if item.available_at_utc <= row.decision_time_utc
                ),
                key=lambda item: item.available_at_utc,
            ).features
            values = {item.feature_name: item for item in row.features}
            assert values["direction"].raw_value == extracted.direction
            assert values["novelty"].raw_value == extracted.novelty
            assert values["risk_change"].raw_value == extracted.risk_change
            assert values["uncertainty"].raw_value == extracted.uncertainty
            assert values["event_tag"].raw_value == len(extracted.event_tags)
            assert all(item.raw_value == item.transformed_value for item in row.features)
        with pytest.raises(ValidationError, match="at least 1"):
            FamilyCEvidence.model_validate(
                {
                    **artifact.family_evidence.model_dump(mode="python"),
                    "corroborations": (),
                }
            )


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
    ),
)
def test_phase5_uses_exact_same_entity_feature_lineage_and_report_witnesses(
    configuration_id: ResearchConfigurationId,
    family: CanonicalFamily,
) -> None:
    mapping = _mapping(family)
    snapshots = _snapshots(mapping)
    prepared = prepare_research_pipeline(configuration_id, snapshots)
    policy, fixture = build_phase5_inputs(
        configuration_id=configuration_id,
        prepared=prepared,
        snapshots=snapshots,
    )
    expectations = {
        (item.key.capability, item.key.normalized_observation_id): item.normalized_observation
        for item in fixture.source_observation_expectations
    }
    assert {capability for capability, _observation_id in expectations} == set(
        policy.required_snapshot_capabilities
    )
    expected_feature_references = {
        (reference.capability, reference.normalized_observation_id)
        for row in prepared.feature_rows
        for feature in row.features
        for reference in feature.source_references
    }
    assert expected_feature_references.issubset(expectations)

    rows_by_sample = {item.sample_id: item for item in prepared.feature_rows}
    used_keys: set[tuple[DataCapability, UUID]] = set()
    for sample in fixture.samples:
        anchor_key = (
            sample.feature_derivation.source_observation_key.capability,
            sample.feature_derivation.source_observation_key.normalized_observation_id,
        )
        anchor = expectations[anchor_key]
        sample_keys = {
            (item.capability, item.normalized_observation_id)
            for item in sample.source_observation_keys
        }
        used_keys.update(sample_keys)
        for key in sample_keys:
            observation = expectations[key]
            if observation.instrument_id is not None:
                assert observation.instrument_id == anchor.instrument_id
                assert observation.listing_id == anchor.listing_id
        row = rows_by_sample[sample.sample_id]
        row_feature_keys = {
            (reference.capability, reference.normalized_observation_id)
            for feature in row.features
            for reference in feature.source_references
        }
        non_fundamental_keys = {
            key for key in row_feature_keys if key[0] is not DataCapability.AS_REPORTED_FUNDAMENTALS
        }
        assert non_fundamental_keys.issubset(sample_keys)
        fundamental_sample_keys = {
            key for key in sample_keys if key[0] is DataCapability.AS_REPORTED_FUNDAMENTALS
        }
        if family is CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING:
            assert len(fundamental_sample_keys) == 1
        else:
            assert not fundamental_sample_keys

    if family is CanonicalFamily.B_TIME_SERIES_MOMENTUM_REGIME:
        delisting_witnesses = {key for key in expectations if key[0] is DataCapability.DELISTINGS}
        assert delisting_witnesses
        assert delisting_witnesses.isdisjoint(used_keys)
