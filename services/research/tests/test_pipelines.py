from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from unittest.mock import MagicMock
from uuid import UUID

import fable5_research.integrity as integrity_module
import fable5_research.phase5 as phase5_module
import fable5_research.workflow as workflow_module
import pytest
from fable5_backtester.contracts import (
    CostScenario,
    EvaluationReport,
    GateCode,
    GateOutcome,
    PromotionState,
    ResearchReturnStatus,
    TrialStatus,
)
from fable5_backtester.engine import evaluate_synthetic_fixture
from fable5_backtester.evaluation_geometry import build_evaluation_geometry
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
    PreparedFamilyAInputs,
    ResearchConfigurationId,
    ResearchRunArtifact,
    ResearchRunCreateRequest,
)
from fable5_research.integrity import (
    Phase6IntegrityError,
    validate_phase6_evaluation_bridge,
)
from fable5_research.phase5 import build_phase5_inputs
from fable5_research.preparation import prepare_research_pipeline
from fable5_research.specification import (
    FAMILY_B_COST_VOLATILITY_PROJECTION_ID,
    FAMILY_B_COST_VOLATILITY_QUANTUM,
    FAMILY_B_COST_VOLATILITY_QUANTUM_TEXT,
    FAMILY_B_TRANSACTION_COST_MODEL_ID,
)
from fable5_research.workflow import (
    ResearchWorkflow,
    ResearchWorkflowBlocked,
    ResearchWorkflowConflict,
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


def test_phase5_bridge_reserves_a_real_confirmation_and_purges_boundary_labels() -> None:
    mapping = _mapping(CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING)
    snapshots = _snapshots(mapping)
    prepared = prepare_research_pipeline(ResearchConfigurationId.A_PASS, snapshots)
    confirmation = prepared.confirmation_interval
    boundary_ids = {item.sample_id for item in prepared.boundary_exclusions}
    assert boundary_ids
    assert confirmation.label_value is None
    assert confirmation.label_source_references == ()
    assert confirmation.label_opened is False

    policy, fixture = build_phase5_inputs(
        configuration_id=ResearchConfigurationId.A_PASS,
        prepared=prepared,
        snapshots=snapshots,
    )
    geometry = build_evaluation_geometry(
        policy=policy,
        walk_forward=policy.walk_forward,
        fixture=fixture,
    )
    assert geometry.validation.passed
    assert geometry.confirmation_sample_ids == (confirmation.sample_id,)
    assert policy.walk_forward.final_confirmation_start_utc == confirmation.interval_start_utc
    assert policy.walk_forward.final_confirmation_end_utc == confirmation.interval_end_utc
    assert not boundary_ids & {sample.sample_id for sample in fixture.samples}
    selected_ids = {
        sample_id
        for fold in geometry.folds
        for sample_id in (
            *fold.train_sample_ids,
            *fold.test_sample_ids,
            *fold.purged_sample_ids,
            *fold.embargoed_sample_ids,
        )
    }
    reserved_ids = {*boundary_ids, confirmation.sample_id}
    assert not reserved_ids & selected_ids
    research_samples = tuple(
        sample for sample in fixture.samples if sample.sample_id != confirmation.sample_id
    )
    assert research_samples
    assert max(sample.label_t1_utc for sample in research_samples) < (
        policy.walk_forward.final_confirmation_start_utc
    )

    report = evaluate_synthetic_fixture(
        policy=policy,
        fixture=fixture,
        mapping=mapping,
        snapshots=snapshots,
        code_version_git_sha=_GIT_SHA,
        created_at_utc=_CREATED_AT,
    )
    assert not reserved_ids & {item.sample_id for item in report.oos_ledger}
    assert all(not reserved_ids & set(item.train_sample_ids) for item in report.preprocessing_fits)
    reserved_times = {
        confirmation.interval_start_utc,
        *(item.decision_time_utc for item in prepared.boundary_exclusions),
    }
    assert all(not reserved_times & set(trial.return_timestamps_utc) for trial in report.trials)


def test_phase5_bridge_uses_family_a_declared_participation_in_evaluated_costs() -> None:
    mapping = _mapping(CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING)
    snapshots = _snapshots(mapping)
    prepared = prepare_research_pipeline(ResearchConfigurationId.A_PASS, snapshots)
    inputs = prepared.family_inputs
    assert isinstance(inputs, PreparedFamilyAInputs)
    assert inputs.capacity.adv_participation == Decimal("0.01")
    policy, fixture = build_phase5_inputs(
        configuration_id=ResearchConfigurationId.A_PASS,
        prepared=prepared,
        snapshots=snapshots,
    )
    research_samples = tuple(
        sample
        for sample in fixture.samples
        if sample.sample_id != prepared.confirmation_interval.sample_id
    )
    assert {
        sample.research_allocation_units / sample.daily_adv_units for sample in research_samples
    } == {inputs.capacity.adv_participation}

    report = evaluate_synthetic_fixture(
        policy=policy,
        fixture=fixture,
        mapping=mapping,
        snapshots=snapshots,
        code_version_git_sha=_GIT_SHA,
        created_at_utc=_CREATED_AT,
    )
    baseline = tuple(item for item in report.cost_ledger if item.scenario is CostScenario.BASELINE)
    liquidity = tuple(
        item for item in report.cost_ledger if item.scenario is CostScenario.LIQUIDITY_STRESS
    )
    assert baseline and liquidity
    assert {item.participation_rate for item in baseline} == {Decimal("0.01")}
    assert {item.participation_rate for item in liquidity} == {
        Decimal("0.01") / policy.stress.adv_multiplier
    }
    assert not any(item.capacity_breached for item in (*baseline, *liquidity))


def test_phase5_bridge_derives_family_b_volatility_and_marks_regime_inputs_unavailable() -> None:
    mapping = _mapping(CanonicalFamily.B_TIME_SERIES_MOMENTUM_REGIME)
    snapshots = _snapshots(mapping)
    prepared = prepare_research_pipeline(ResearchConfigurationId.B_PASS, snapshots)
    raw_volatility_by_sample = {
        row.sample_id: next(
            item.raw_value for item in row.features if item.feature_name == "realized_volatility"
        )
        for row in prepared.feature_rows
    }
    policy, fixture = build_phase5_inputs(
        configuration_id=ResearchConfigurationId.B_PASS,
        prepared=prepared,
        snapshots=snapshots,
    )
    rows = {row.sample_id: row for row in prepared.feature_rows}
    for sample in fixture.samples:
        if sample.sample_id == prepared.confirmation_interval.sample_id:
            assert sample.return_status.value == "no_trade"
            continue
        volatility = next(
            item
            for item in rows[sample.sample_id].features
            if item.feature_name == "realized_volatility"
        )
        with localcontext() as decimal_context:
            decimal_context.prec = 80
            expected_cost_volatility = volatility.raw_value.quantize(
                FAMILY_B_COST_VOLATILITY_QUANTUM,
                rounding=ROUND_HALF_EVEN,
            )
        assert sample.daily_volatility == expected_cost_volatility
        assert volatility.raw_value == raw_volatility_by_sample[sample.sample_id]
        assert sample.rate_change == 0
        assert sample.rate_available_at_utc == sample.decision_time_utc
        assert sample.crisis_window_ids == ()
    regime_evidence = fixture.phase6_regime_evidence
    assert regime_evidence is not None
    assert regime_evidence.rate_evidence_available is False
    assert regime_evidence.rate_evidence_reason == "rate_regime_source_unavailable"
    assert regime_evidence.rate_compatibility_projection == "zero-at-decision-not-observed-v1"
    assert regime_evidence.crisis_geometry_available is False
    assert regime_evidence.crisis_evidence_reason == "crisis_window_geometry_unavailable"
    assert regime_evidence.crisis_compatibility_projection == ("empty-membership-not-observed-v1")
    assert policy.regimes.rate_definition == "unavailable-no-authorized-pit-rate-source-v1"
    assert policy.regimes.crisis_windows == ("unavailable-no-frozen-crisis-window-geometry-v1",)
    assert prepared.specification.transaction_cost_model_id == FAMILY_B_TRANSACTION_COST_MODEL_ID

    report = evaluate_synthetic_fixture(
        policy=policy,
        fixture=fixture,
        mapping=mapping,
        snapshots=snapshots,
        code_version_git_sha=_GIT_SHA,
        created_at_utc=_CREATED_AT,
    )
    regime = next(item for item in report.gates if item.gate_code is GateCode.REGIME)
    assert regime.outcome is GateOutcome.RESEARCH_ONLY
    assert {
        "rate_regime_coverage_missing",
        "crisis_window_coverage_missing",
    }.issubset(regime.reason_codes)
    assert report.promotion_state is PromotionState.FAIL_REJECT
    assert next(item for item in report.gates if item.gate_code is GateCode.PBO).outcome is (
        GateOutcome.FAIL
    )
    completed_trials = tuple(item for item in report.trials if item.status is TrialStatus.COMPLETED)
    assert completed_trials
    assert {
        item.configuration["phase6_cost_volatility_projection_id"] for item in completed_trials
    } == {FAMILY_B_COST_VOLATILITY_PROJECTION_ID}
    assert {item.configuration["phase6_cost_volatility_quantum"] for item in completed_trials} == {
        FAMILY_B_COST_VOLATILITY_QUANTUM_TEXT
    }


def test_family_a_uses_exact_pit_macro_regimes_and_blocks_projection_tampering() -> None:
    mapping = _mapping(CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING)
    snapshots = _snapshots(mapping)
    prepared = prepare_research_pipeline(ResearchConfigurationId.A_PASS, snapshots)
    evidence = prepared.regime_evidence
    assert evidence.evidence_state == "available"
    assert {item.rate_change for item in evidence.rate_observations} == {
        Decimal("-0.20"),
        Decimal("0.10"),
    }
    assert len(evidence.crisis_windows) == 1
    assert all(
        item.source_reference.capability is DataCapability.MACRO_REGIME_INPUTS
        for item in (*evidence.rate_observations, *evidence.crisis_windows)
    )
    policy, fixture = build_phase5_inputs(
        configuration_id=ResearchConfigurationId.A_PASS,
        prepared=prepared,
        snapshots=snapshots,
    )
    assert fixture.phase6_regime_evidence is not None
    assert fixture.phase6_regime_evidence.rate_evidence_available is True
    assert fixture.phase6_regime_evidence.crisis_geometry_available is True
    assert {item.rate_change for item in fixture.samples} == {
        Decimal("-0.20"),
        Decimal("0.10"),
    }
    assert any(item.crisis_window_ids for item in fixture.samples)
    report = evaluate_synthetic_fixture(
        policy=policy,
        fixture=fixture,
        mapping=mapping,
        snapshots=snapshots,
        code_version_git_sha=_GIT_SHA,
        created_at_utc=_CREATED_AT,
    )
    assert next(item for item in report.gates if item.gate_code is GateCode.REGIME).outcome is (
        GateOutcome.PASS
    )
    altered_sample = fixture.samples[0].model_copy(
        update={"rate_change": fixture.samples[0].rate_change + Decimal("0.01")}
    )
    with pytest.raises(
        Phase6IntegrityError,
        match="phase6_observed_regime_projection_mismatch",
    ):
        validate_phase6_evaluation_bridge(
            policy=policy,
            fixture=fixture.model_copy(update={"samples": (altered_sample, *fixture.samples[1:])}),
            prepared=prepared,
            report=report,
        )


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


def test_workflow_rejects_substituted_persisted_report_before_artifact_creation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mapping = _mapping(CanonicalFamily.B_TIME_SERIES_MOMENTUM_REGIME)
    snapshot_id = UUID("eeeeeeee-eeee-5eee-8eee-eeeeeeeeeeee")
    snapshot = MagicMock()
    snapshot.snapshot.manifest.payload.mapping = mapping
    snapshot_store = MagicMock()
    evaluation_store = MagicMock()
    repository = MagicMock()
    workflow = ResearchWorkflow(
        repository=repository,
        evaluation_repository=evaluation_store,
        snapshot_repository=snapshot_store,
        code_version_git_sha=_GIT_SHA,
    )
    prepared = object()
    policy = object()
    fixture = object()
    report = MagicMock(spec=EvaluationReport)
    substituted_report = MagicMock(spec=EvaluationReport)
    report.model_dump.return_value = {"artifact_sha256": "1" * 64}
    substituted_report.model_dump.return_value = {"artifact_sha256": "2" * 64}
    evaluation_store.create_policy.return_value = policy
    evaluation_store.create_report.return_value = substituted_report
    monkeypatch.setattr(workflow, "_resolve_snapshots", MagicMock(return_value=(snapshot,)))
    monkeypatch.setattr(
        workflow_module,
        "missing_official_corroboration_source_ids",
        MagicMock(return_value=()),
    )
    prepare = MagicMock(return_value=prepared)
    phase5_inputs = MagicMock(return_value=(policy, fixture))
    evaluate = MagicMock(return_value=report)
    validate = MagicMock()
    build_artifact = MagicMock()
    monkeypatch.setattr(workflow_module, "prepare_research_pipeline", prepare)
    monkeypatch.setattr(workflow_module, "build_phase5_inputs", phase5_inputs)
    monkeypatch.setattr(workflow_module, "evaluate_synthetic_fixture", evaluate)
    monkeypatch.setattr(workflow_module, "validate_phase6_evaluation_bridge", validate)
    monkeypatch.setattr(workflow_module, "build_research_artifact", build_artifact)
    request = ResearchRunCreateRequest(
        mapping_id=mapping.mapping_id,
        snapshot_ids=(snapshot_id,),
        research_configuration_id=ResearchConfigurationId.B_PASS,
    )

    with pytest.raises(ResearchWorkflowConflict, match="persisted Phase 5 report changed"):
        workflow.create_run(request)

    evaluation_store.create_report.assert_called_once_with(report)
    validate.assert_called_once_with(
        policy=policy,
        fixture=fixture,
        prepared=prepared,
        report=report,
    )
    build_artifact.assert_not_called()
    repository.create_run.assert_not_called()


def test_report_idempotency_accepts_only_the_first_server_timestamp() -> None:
    candidate = MagicMock(spec=EvaluationReport)
    persisted = MagicMock(spec=EvaluationReport)
    candidate_content = {
        "artifact_sha256": "1" * 64,
        "decision_time_utc": _CREATED_AT,
        "untyped_json_evidence": {
            "threshold": Decimal("0.50"),
            "family": CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING,
        },
    }
    persisted_content = {
        **candidate_content,
        "untyped_json_evidence": {
            "threshold": "0.5",
            "family": "A_CROSS_SECTIONAL_EQUITY_RANKING",
        },
    }
    candidate.model_dump.return_value = candidate_content
    persisted.model_dump.return_value = persisted_content

    assert workflow_module._same_evaluation_report_content(persisted, candidate)
    expected_kwargs = {"mode": "python", "exclude": {"created_at_utc"}}
    persisted.model_dump.assert_called_once_with(**expected_kwargs)
    candidate.model_dump.assert_called_once_with(**expected_kwargs)

    persisted.model_dump.return_value = {
        **persisted_content,
        "untyped_json_evidence": {
            "threshold": "0.6",
            "family": "A_CROSS_SECTIONAL_EQUITY_RANKING",
        },
    }
    assert not workflow_module._same_evaluation_report_content(persisted, candidate)

    persisted.model_dump.return_value = {
        **persisted_content,
        "decision_time_utc": _CREATED_AT + timedelta(seconds=1),
    }
    assert not workflow_module._same_evaluation_report_content(persisted, candidate)


@pytest.mark.parametrize(
    ("configuration_id", "expected_state", "expected_special_gate"),
    (
        (
            ResearchConfigurationId.A_PASS,
            PromotionState.PASS_RESEARCH,
            None,
        ),
        (ResearchConfigurationId.A_FAIL, PromotionState.FAIL_REJECT, GateCode.COST_STRESS),
        (
            ResearchConfigurationId.B_PASS,
            PromotionState.FAIL_REJECT,
            GateCode.PBO,
        ),
        (
            ResearchConfigurationId.B_FAIL,
            PromotionState.FAIL_REJECT,
            GateCode.PBO,
        ),
        (
            ResearchConfigurationId.C_PASS,
            PromotionState.FAIL_REJECT,
            GateCode.DSR,
        ),
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
    if configuration_id in {ResearchConfigurationId.B_PASS, ResearchConfigurationId.B_FAIL}:
        phase5_numeric_quantum = Decimal("1e-30")
        numeric_values = (
            tuple(
                value
                for entry in report.oos_ledger
                for value in (
                    entry.predicted_value,
                    entry.gross_return,
                    entry.baseline_net_return,
                )
                if value is not None
            )
            + tuple(
                value
                for trial in report.trials
                if trial.status is TrialStatus.COMPLETED
                for value in trial.net_returns
                if value is not None
            )
            + tuple(
                getattr(entry, field_name)
                for entry in report.cost_ledger
                for field_name in (
                    "requested_quantity",
                    "filled_quantity",
                    "rejected_quantity",
                    "unfilled_quantity",
                    "gross_return",
                    "fee_cost",
                    "spread_cost",
                    "impact_cost",
                    "latency_cost",
                    "borrow_cost",
                    "capacity_cost",
                    "total_cost",
                    "net_return",
                    "participation_rate",
                )
            )
        )
        with localcontext() as decimal_context:
            decimal_context.prec = 80
            assert all(
                value == value.quantize(phase5_numeric_quantum, rounding=ROUND_HALF_EVEN)
                for value in numeric_values
            )
        assert {item.scenario for item in report.cost_ledger} == set(CostScenario)
        assert all(
            item.filled_quantity + item.unfilled_quantity == item.requested_quantity
            and item.rejected_quantity == item.unfilled_quantity
            and item.total_cost
            == sum(
                (
                    item.fee_cost,
                    item.spread_cost,
                    item.impact_cost,
                    item.latency_cost,
                    item.borrow_cost,
                    item.capacity_cost,
                ),
                Decimal("0"),
            )
            and item.net_return == item.gross_return - item.total_cost
            for item in report.cost_ledger
        )
        baseline_by_sample = {
            item.sample_id: item
            for item in report.cost_ledger
            if item.scenario is CostScenario.BASELINE
        }
        assert all(
            item.baseline_net_return == baseline_by_sample[item.sample_id].net_return
            for item in report.oos_ledger
        )
        validate_phase6_evaluation_bridge(
            policy=policy,
            fixture=fixture,
            prepared=prepared,
            report=report,
        )
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
        snapshots=snapshots,
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
    assert len(artifact.trial_economics) == 4
    assert artifact.source_reproduction_audit.exact_match is True
    assert all(
        len(item.sample_economics) == len(artifact.feature_rows)
        for item in artifact.trial_economics
    )

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
        assert artifact.family_evidence.crash_evidence_complete is False
        assert artifact.family_evidence.crash_concentration is None
        assert artifact.family_evidence.crash_concentration_limit is None
        assert artifact.family_evidence.rate_evidence_available is False
        assert artifact.family_evidence.rate_evidence_reason == ("rate_regime_source_unavailable")
        assert artifact.family_evidence.crisis_geometry_available is False
        regime_gate = next(item for item in report.gates if item.gate_code is GateCode.REGIME)
        assert {item.regime_id for item in artifact.family_evidence.regime_results} == {
            item["regime"]
            for item in json.loads(str(regime_gate.results["regime_breakdowns_json"]))
            if str(item["regime"]).startswith("volatility:")
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
        if sample.sample_id == prepared.confirmation_interval.sample_id:
            assert sample.return_status.value == "no_trade"
            continue
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


def test_phase5_bridge_rejects_coherent_source_reference_metadata_tampering() -> None:
    mapping = _mapping(CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING)
    snapshots = _snapshots(mapping)
    prepared = prepare_research_pipeline(ResearchConfigurationId.A_PASS, snapshots)
    reference = prepared.feature_rows[0].features[0].source_references[0]
    indexed = phase5_module._source_index(snapshots)
    metadata_tampers: tuple[dict[str, object], ...] = (
        {"record_type": f"{reference.record_type}-tampered"},
        {"source_record_id": f"{reference.source_record_id}-tampered"},
        {"instrument_id": (None if reference.instrument_id is not None else UUID(int=0))},
        {"listing_id": None if reference.listing_id is not None else UUID(int=0)},
        {"available_at_utc": reference.available_at_utc + timedelta(microseconds=1)},
        {"valid_from_utc": reference.valid_from_utc + timedelta(microseconds=1)},
        {
            "valid_to_utc": (
                None
                if reference.valid_to_utc is not None
                else reference.valid_from_utc + timedelta(microseconds=1)
            )
        },
    )
    for update in metadata_tampers:
        with pytest.raises(
            ValueError,
            match="prepared source reference conflicts with immutable Phase 4 lineage",
        ):
            phase5_module._entry_for_reference(
                reference.model_copy(update=update),
                indexed,
            )


def test_phase6_integrity_reconciles_and_rejects_selected_output_or_trial_tampering() -> None:
    mapping = _mapping(CanonicalFamily.B_TIME_SERIES_MOMENTUM_REGIME)
    snapshots = _snapshots(mapping)
    prepared = prepare_research_pipeline(ResearchConfigurationId.B_PASS, snapshots)
    policy, fixture = build_phase5_inputs(
        configuration_id=ResearchConfigurationId.B_PASS,
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
    validate_phase6_evaluation_bridge(
        policy=policy,
        fixture=fixture,
        prepared=prepared,
        report=report,
    )

    projected_sample_index = next(
        index
        for index, sample in enumerate(fixture.samples)
        if sample.sample_id != prepared.confirmation_interval.sample_id
    )
    projected_sample = fixture.samples[projected_sample_index]
    altered_projected_sample = projected_sample.model_copy(
        update={
            "daily_volatility": (
                projected_sample.daily_volatility + FAMILY_B_COST_VOLATILITY_QUANTUM
            )
        }
    )
    altered_fixture_samples = list(fixture.samples)
    altered_fixture_samples[projected_sample_index] = altered_projected_sample
    with pytest.raises(
        Phase6IntegrityError,
        match="phase6_volatility_regime_source_mismatch",
    ):
        validate_phase6_evaluation_bridge(
            policy=policy,
            fixture=fixture.model_copy(update={"samples": tuple(altered_fixture_samples)}),
            prepared=prepared,
            report=report,
        )

    first_oos = report.oos_ledger[0]
    tampered_oos = first_oos.model_copy(
        update={"predicted_value": first_oos.predicted_value + Decimal("1")}
    )
    with pytest.raises(
        Phase6IntegrityError,
        match="phase6_oos_model_output_or_return_mismatch",
    ):
        validate_phase6_evaluation_bridge(
            policy=policy,
            fixture=fixture,
            prepared=prepared,
            report=report.model_copy(update={"oos_ledger": (tampered_oos, *report.oos_ledger[1:])}),
        )

    completed_index = next(
        index for index, trial in enumerate(report.trials) if trial.status is TrialStatus.COMPLETED
    )
    completed = report.trials[completed_index]
    for binding in (
        "phase6_model_output_sha256",
        "phase6_output_set_sha256",
        "phase6_ledger_cell_set_sha256",
        "phase6_payoff_formula_id",
        "phase6_cost_volatility_projection_id",
        "phase6_cost_volatility_quantum",
    ):
        bad_configuration = {**completed.configuration, binding: "tampered"}
        bad_trial = completed.model_copy(update={"configuration": bad_configuration})
        bad_trials = list(report.trials)
        bad_trials[completed_index] = bad_trial
        with pytest.raises(
            Phase6IntegrityError,
            match="phase6_trial_configuration_lineage_mismatch",
        ):
            validate_phase6_evaluation_bridge(
                policy=policy,
                fixture=fixture,
                prepared=prepared,
                report=report.model_copy(update={"trials": tuple(bad_trials)}),
            )

    weights = json.loads(completed.configuration["phase6_trial_weights_json"])
    weight_sample_id = next(iter(weights))
    weights[weight_sample_id] = "0" if weights[weight_sample_id] == "1" else "1"
    bad_weight_trial = completed.model_copy(
        update={
            "configuration": {
                **completed.configuration,
                "phase6_trial_weights_json": json.dumps(
                    weights,
                    sort_keys=True,
                    separators=(",", ":"),
                ),
            }
        }
    )
    bad_weight_trials = list(report.trials)
    bad_weight_trials[completed_index] = bad_weight_trial
    with pytest.raises(Phase6IntegrityError, match="phase6_trial_allocation_lineage_mismatch"):
        validate_phase6_evaluation_bridge(
            policy=policy,
            fixture=fixture,
            prepared=prepared,
            report=report.model_copy(update={"trials": tuple(bad_weight_trials)}),
        )

    noncanonical_weight_trial = completed.model_copy(
        update={
            "configuration": {
                **completed.configuration,
                "phase6_trial_weights_json": (
                    completed.configuration["phase6_trial_weights_json"] + " "
                ),
            }
        }
    )
    noncanonical_weight_trials = list(report.trials)
    noncanonical_weight_trials[completed_index] = noncanonical_weight_trial
    with pytest.raises(Phase6IntegrityError, match="phase6_trial_weight_evidence_invalid"):
        validate_phase6_evaluation_bridge(
            policy=policy,
            fixture=fixture,
            prepared=prepared,
            report=report.model_copy(update={"trials": tuple(noncanonical_weight_trials)}),
        )

    allocation_rules = json.loads(completed.configuration["phase6_allocation_rules_json"])
    allocation_rules[next(iter(allocation_rules))] = "tampered-rule"
    bad_rule_trial = completed.model_copy(
        update={
            "configuration": {
                **completed.configuration,
                "phase6_allocation_rules_json": json.dumps(
                    allocation_rules,
                    sort_keys=True,
                    separators=(",", ":"),
                ),
            }
        }
    )
    bad_rule_trials = list(report.trials)
    bad_rule_trials[completed_index] = bad_rule_trial
    with pytest.raises(Phase6IntegrityError, match="phase6_trial_allocation_lineage_mismatch"):
        validate_phase6_evaluation_bridge(
            policy=policy,
            fixture=fixture,
            prepared=prepared,
            report=report.model_copy(update={"trials": tuple(bad_rule_trials)}),
        )

    configured_costs = json.loads(completed.configuration["phase6_trial_cost_ledger_json"])
    configured_costs[0]["hard_to_borrow_available"] = not configured_costs[0][
        "hard_to_borrow_available"
    ]
    bad_cost_trial = completed.model_copy(
        update={
            "configuration": {
                **completed.configuration,
                "phase6_trial_cost_ledger_json": json.dumps(
                    configured_costs,
                    sort_keys=True,
                    separators=(",", ":"),
                ),
            }
        }
    )
    bad_cost_trials = list(report.trials)
    bad_cost_trials[completed_index] = bad_cost_trial
    with pytest.raises(Phase6IntegrityError, match="phase6_trial_cost_component_mismatch"):
        validate_phase6_evaluation_bridge(
            policy=policy,
            fixture=fixture,
            prepared=prepared,
            report=report.model_copy(update={"trials": tuple(bad_cost_trials)}),
        )

    bad_cost_hash_trial = completed.model_copy(
        update={
            "configuration": {
                **completed.configuration,
                "phase6_trial_cost_set_sha256": "0" * 64,
            }
        }
    )
    bad_cost_hash_trials = list(report.trials)
    bad_cost_hash_trials[completed_index] = bad_cost_hash_trial
    with pytest.raises(Phase6IntegrityError, match="phase6_trial_cost_set_hash_mismatch"):
        validate_phase6_evaluation_bridge(
            policy=policy,
            fixture=fixture,
            prepared=prepared,
            report=report.model_copy(update={"trials": tuple(bad_cost_hash_trials)}),
        )

    active_cost_index = next(
        index
        for index, item in enumerate(report.cost_ledger)
        if item.scenario is CostScenario.BASELINE
        and item.return_status is ResearchReturnStatus.OBSERVED
    )
    active_cost = report.cost_ledger[active_cost_index]
    cost_delta = Decimal("0.000001")
    tampered_active_cost = active_cost.model_copy(
        update={
            "fee_cost": active_cost.fee_cost + cost_delta,
            "total_cost": active_cost.total_cost + cost_delta,
            "net_return": active_cost.net_return - cost_delta,
        }
    )
    tampered_report_costs = list(report.cost_ledger)
    tampered_report_costs[active_cost_index] = tampered_active_cost
    with pytest.raises(
        Phase6IntegrityError,
        match="phase6_oos_component_cost_ledger_mismatch",
    ):
        validate_phase6_evaluation_bridge(
            policy=policy,
            fixture=fixture,
            prepared=prepared,
            report=report.model_copy(update={"cost_ledger": tuple(tampered_report_costs)}),
        )

    flat_cost_index = next(
        index
        for index, item in enumerate(report.cost_ledger)
        if item.scenario is CostScenario.BASELINE
        and item.return_status is ResearchReturnStatus.NO_TRADE
    )
    flat_cost = report.cost_ledger[flat_cost_index]
    tampered_flat_cost = flat_cost.model_copy(update={"participation_rate": Decimal("0.1")})
    tampered_flat_costs = list(report.cost_ledger)
    tampered_flat_costs[flat_cost_index] = tampered_flat_cost
    with pytest.raises(
        Phase6IntegrityError,
        match="phase6_oos_component_cost_ledger_mismatch",
    ):
        validate_phase6_evaluation_bridge(
            policy=policy,
            fixture=fixture,
            prepared=prepared,
            report=report.model_copy(update={"cost_ledger": tuple(tampered_flat_costs)}),
        )

    with pytest.raises(Phase6IntegrityError, match="phase6_oos_outer_calendar_mismatch"):
        validate_phase6_evaluation_bridge(
            policy=policy,
            fixture=fixture,
            prepared=prepared,
            report=report.model_copy(update={"oos_ledger": report.oos_ledger[1:]}),
        )

    shortened_trial = completed.model_copy(
        update={
            "return_timestamps_utc": completed.return_timestamps_utc[:-1],
            "net_returns": completed.net_returns[:-1],
            "return_statuses": completed.return_statuses[:-1],
        }
    )
    shortened_trials = list(report.trials)
    shortened_trials[completed_index] = shortened_trial
    with pytest.raises(Phase6IntegrityError, match="phase6_trial_calendar_lineage_mismatch"):
        validate_phase6_evaluation_bridge(
            policy=policy,
            fixture=fixture,
            prepared=prepared,
            report=report.model_copy(update={"trials": tuple(shortened_trials)}),
        )

    first_fold_id = report.oos_ledger[0].fold_id
    selected_trial_id = report.oos_ledger[0].trial_id
    alternative = next(
        trial
        for trial in report.trials
        if trial.status is TrialStatus.COMPLETED and trial.trial_id != selected_trial_id
    )
    alternative_cells = {
        item.sample_id: item
        for item in next(
            item for item in prepared.model_output_sets if item.trial_key == alternative.trial_key
        ).ledger_cells
    }
    baseline_costs = {
        item.sample_id: item.total_cost
        for item in report.cost_ledger
        if item.scenario is CostScenario.BASELINE
    }
    switched_oos = tuple(
        entry.model_copy(
            update={
                "trial_id": alternative.trial_id,
                "predicted_value": alternative_cells[entry.sample_id].model_output,
                "gross_return": alternative_cells[entry.sample_id].synthetic_gross_return,
                "baseline_net_return": (
                    alternative_cells[entry.sample_id].synthetic_gross_return
                    - baseline_costs[entry.sample_id]
                ),
            }
        )
        if entry.fold_id == first_fold_id
        else entry
        for entry in report.oos_ledger
    )
    with pytest.raises(
        Phase6IntegrityError,
        match="phase6_oos_selected_trial_selection_mismatch",
    ):
        validate_phase6_evaluation_bridge(
            policy=policy,
            fixture=fixture,
            prepared=prepared,
            report=report.model_copy(update={"oos_ledger": switched_oos}),
        )


def test_phase6_integrity_rejects_scope_or_empty_confirmation_tampering() -> None:
    mapping = _mapping(CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING)
    snapshots = _snapshots(mapping)
    prepared = prepare_research_pipeline(ResearchConfigurationId.A_PASS, snapshots)
    policy, fixture = build_phase5_inputs(
        configuration_id=ResearchConfigurationId.A_PASS,
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
    scope = fixture.report_scope_source_evidence[0]
    reduced_scope = scope.model_copy(
        update={"source_observation_keys": scope.source_observation_keys[1:]}
    )
    with pytest.raises(
        Phase6IntegrityError,
        match="phase6_report_scope_source_graph_mismatch",
    ):
        validate_phase6_evaluation_bridge(
            policy=policy,
            fixture=fixture.model_copy(
                update={
                    "report_scope_source_evidence": (
                        reduced_scope,
                        *fixture.report_scope_source_evidence[1:],
                    )
                }
            ),
            prepared=prepared,
            report=report,
        )

    after_last = prepared.feature_rows[-1].label_t1_utc
    empty_walk_forward = policy.walk_forward.model_copy(
        update={
            "final_confirmation_start_utc": after_last,
            "final_confirmation_end_utc": after_last + timedelta(microseconds=1),
        }
    )
    with pytest.raises(
        Phase6IntegrityError,
        match="phase6_final_confirmation_policy_mismatch",
    ):
        validate_phase6_evaluation_bridge(
            policy=policy.model_copy(update={"walk_forward": empty_walk_forward}),
            fixture=fixture,
            prepared=prepared,
            report=report,
        )


def test_phase6_family_a_capacity_projection_is_conditional_on_selected_activity() -> None:
    mapping = _mapping(CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING)
    snapshots = _snapshots(mapping)
    prepared = prepare_research_pipeline(ResearchConfigurationId.A_PASS, snapshots)
    policy, fixture = build_phase5_inputs(
        configuration_id=ResearchConfigurationId.A_PASS,
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
    flat_sample_id = report.oos_ledger[0].sample_id
    flat_oos = tuple(
        item.model_copy(
            update={
                "return_status": ResearchReturnStatus.NO_TRADE,
                "gross_return": Decimal("0"),
                "baseline_net_return": Decimal("0"),
            }
        )
        if item.sample_id == flat_sample_id
        else item
        for item in report.oos_ledger
    )
    flat_costs = tuple(
        item.model_copy(
            update={
                "return_status": ResearchReturnStatus.NO_TRADE,
                "requested_quantity": Decimal("0"),
                "filled_quantity": Decimal("0"),
                "rejected_quantity": Decimal("0"),
                "unfilled_quantity": Decimal("0"),
                "fill_status": "no_trade",
                "gross_return": Decimal("0"),
                "fee_cost": Decimal("0"),
                "spread_cost": Decimal("0"),
                "impact_cost": Decimal("0"),
                "latency_cost": Decimal("0"),
                "borrow_cost": Decimal("0"),
                "capacity_cost": Decimal("0"),
                "total_cost": Decimal("0"),
                "net_return": Decimal("0"),
                "participation_rate": Decimal("0"),
                "capacity_breached": False,
            }
        )
        if item.sample_id == flat_sample_id and item.scenario is CostScenario.BASELINE
        else item
        for item in report.cost_ledger
    )
    flat_report = report.model_copy(update={"oos_ledger": flat_oos, "cost_ledger": flat_costs})
    fixture_sample = next(item for item in fixture.samples if item.sample_id == flat_sample_id)
    flat_fixture = fixture.model_copy(
        update={
            "samples": tuple(
                item.model_copy(
                    update={
                        "research_allocation_units": item.research_allocation_units * Decimal("2")
                    }
                )
                if item.sample_id == flat_sample_id
                else item
                for item in fixture.samples
            )
        }
    )
    assert fixture_sample.research_allocation_units > 0
    integrity_module._validate_capacity_projection(
        fixture=flat_fixture,
        prepared=prepared,
        report=flat_report,
    )

    bad_flat_costs = tuple(
        item.model_copy(update={"participation_rate": Decimal("0.1")})
        if item.sample_id == flat_sample_id and item.scenario is CostScenario.BASELINE
        else item
        for item in flat_costs
    )
    with pytest.raises(Phase6IntegrityError, match="phase6_capacity_flat_economics_mismatch"):
        integrity_module._validate_capacity_projection(
            fixture=flat_fixture,
            prepared=prepared,
            report=flat_report.model_copy(update={"cost_ledger": bad_flat_costs}),
        )
