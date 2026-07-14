from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from statistics import fmean, stdev
from typing import Any
from uuid import UUID

import fable5_backtester.engine as engine_module
import fable5_backtester.leakage as leakage_module
import pytest
from fable5_backtester.canonical import (
    PHASE5_ARTIFACT_HASH_DOMAIN,
    PHASE5_ARTIFACT_NAMESPACE,
    PHASE5_CONFIG_HASH_DOMAIN,
    PHASE5_DEPENDENCY_GRAPH_HASH_DOMAIN,
    PHASE5_FIXTURE_HASH_DOMAIN,
    PHASE5_GATE_HASH_DOMAIN,
    PHASE5_GATE_NAMESPACE,
    PHASE5_LEAKAGE_EVIDENCE_HASH_DOMAIN,
    PHASE5_POLICY_HASH_DOMAIN,
    PHASE5_SAMPLE_LINEAGE_HASH_DOMAIN,
    canonical_json_text,
    domain_sha256,
    identity,
)
from fable5_backtester.contracts import (
    PHASE5_ADVERSARIAL_DEPENDENCY_REVIEW_HASH_DOMAIN,
    PHASE5_REPORT_HASH_EXCLUDED_FIELDS,
    CostScenario,
    EvaluationReport,
    FoldKind,
    FoldRecord,
    FrozenEvaluationPolicy,
    FundamentalRevisionEvidence,
    GateCode,
    GateOutcome,
    GateResult,
    LeakageCode,
    LeakageGateEvidence,
    PreprocessingFitRecord,
    PreprocessingFitSampleValue,
    PromotionState,
    ResearchReturnStatus,
    SampleSourceLineage,
    SourceFeatureDerivation,
    SourceObservationKey,
    SyntheticEvaluationFixture,
    SyntheticSample,
    SyntheticSourceObservationExpectation,
    SyntheticTrial,
    TrialRecord,
    TrialStatus,
)
from fable5_backtester.costs import build_cost_ledger
from fable5_backtester.engine import EvaluationEngineBlocked, evaluate_synthetic_fixture
from fable5_backtester.metrics import CORE_METRIC_IDS
from fable5_backtester.statistics import (
    PBOInputs,
    PBOSelectionMetric,
    PBOTiePolicy,
    compute_pbo,
)
from fable5_backtester.synthetic import REGISTERED_FIXTURE, REGISTERED_POLICY
from fable5_data.contracts import (
    AuthorizedMappingIdentity,
    ConstituentDisposition,
    DataCapability,
    OhlcvBarPayload,
    SnapshotBundle,
    SnapshotRequestParameters,
)
from fable5_data.quality import (
    QualityAcceptedResult,
    QualityReferenceCatalog,
    run_mandatory_data_quality,
)
from fable5_data.snapshots import SnapshotCandidate, build_snapshot_candidate
from fable5_data.synthetic import (
    SYNTHETIC_MOCK_CONFIGURATION,
    SyntheticPointInTimeAdapter,
    load_fixture_records,
)
from fable5_mapping.models import CanonicalFamily, ResearchVerdict
from pydantic import ValidationError

MAPPING_ID = UUID("aaaaaaaa-aaaa-5aaa-8aaa-aaaaaaaaaaaa")
AS_OF = datetime(2026, 7, 12, tzinfo=UTC)
CREATED_AT = datetime(2026, 7, 13, 20, 30, tzinfo=UTC)
CODE_VERSION = "a" * 40


@pytest.fixture(scope="module")
def mapping() -> AuthorizedMappingIdentity:
    return AuthorizedMappingIdentity(
        mapping_id=MAPPING_ID,
        mapping_version=1,
        mapping_input_sha256="1" * 64,
        mapper_rule_set_version="phase3-test-rules-v1",
        mapper_rule_set_sha256="2" * 64,
        canonical_family=CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING,
        verdict=ResearchVerdict.BUILD_RESEARCH,
    )


def _snapshot_bundle(
    mapping: AuthorizedMappingIdentity,
    capability: DataCapability = DataCapability.OHLCV,
    record_definitions: tuple[dict[str, object], ...] | None = None,
) -> SnapshotBundle:
    adapter = (
        SyntheticPointInTimeAdapter.for_mapping(mapping)
        if record_definitions is None
        else SyntheticPointInTimeAdapter(record_definitions)
    )
    request = SnapshotRequestParameters(
        mapping=mapping,
        as_of_utc=AS_OF,
        capability=capability,
        mock_configuration_id=SYNTHETIC_MOCK_CONFIGURATION.configuration_id,
    )
    adapter_result = adapter.fetch(capability)
    quality = run_mandatory_data_quality(
        request=request,
        result=adapter_result,
        configuration=SYNTHETIC_MOCK_CONFIGURATION,
        catalog=QualityReferenceCatalog.from_results(adapter.all_results()),
    )
    assert isinstance(quality, QualityAcceptedResult)
    candidate = build_snapshot_candidate(
        mapping=mapping,
        request=request,
        profile=adapter_result.profile,
        configuration=SYNTHETIC_MOCK_CONFIGURATION,
        batch=quality.batch,
        created_at_utc=CREATED_AT,
    )
    assert isinstance(candidate, SnapshotCandidate)
    return candidate.bundle


@pytest.fixture(scope="module")
def snapshot(mapping: AuthorizedMappingIdentity) -> SnapshotBundle:
    return _snapshot_bundle(mapping)


def _evaluate(
    mapping: AuthorizedMappingIdentity,
    snapshot: SnapshotBundle,
    fixture: SyntheticEvaluationFixture = REGISTERED_FIXTURE,
) -> EvaluationReport:
    return evaluate_synthetic_fixture(
        policy=REGISTERED_POLICY,
        fixture=fixture,
        mapping=mapping,
        snapshots=_required_snapshots(mapping, snapshot),
        code_version_git_sha=CODE_VERSION,
        created_at_utc=CREATED_AT,
    )


def _required_snapshots(
    mapping: AuthorizedMappingIdentity,
    primary: SnapshotBundle,
) -> tuple[SnapshotBundle, ...]:
    primary_capability = primary.snapshot.manifest.payload.request.capability
    by_capability = {primary_capability: primary}
    for capability in REGISTERED_POLICY.required_snapshot_capabilities:
        by_capability.setdefault(capability, _snapshot_bundle(mapping, capability))
    return tuple(by_capability[capability] for capability in sorted(by_capability, key=str))


@pytest.fixture(scope="module")
def report(mapping: AuthorizedMappingIdentity, snapshot: SnapshotBundle) -> EvaluationReport:
    return _evaluate(mapping, snapshot)


def _rehash_fixture(
    *,
    samples: tuple[SyntheticSample, ...],
    trials: tuple[SyntheticTrial, ...] | None = None,
    source_observation_expectations: tuple[SyntheticSourceObservationExpectation, ...]
    | None = None,
) -> SyntheticEvaluationFixture:
    content = REGISTERED_FIXTURE.model_dump(mode="python", exclude={"fixture_sha256"})
    content["samples"] = samples
    if trials is not None:
        content["trials"] = trials
    if source_observation_expectations is not None:
        content["source_observation_expectations"] = source_observation_expectations
    digest = domain_sha256(PHASE5_FIXTURE_HASH_DOMAIN, content)
    return SyntheticEvaluationFixture.model_validate({**content, "fixture_sha256": digest})


def _policy_with_minimum_oos(minimum: int) -> FrozenEvaluationPolicy:
    content = REGISTERED_POLICY.model_dump(
        mode="python",
        exclude={"policy_sha256", "policy_canonical_json"},
    )
    content["sample_adequacy"] = REGISTERED_POLICY.sample_adequacy.model_copy(
        update={"min_oos_observations": minimum}
    )
    digest = domain_sha256(PHASE5_POLICY_HASH_DOMAIN, content)
    return FrozenEvaluationPolicy.model_validate(
        {
            **content,
            "policy_sha256": digest,
            "policy_canonical_json": canonical_json_text(content),
        }
    )


def _return_evidence(trial: SyntheticTrial | TrialRecord, key: str) -> dict[str, Decimal]:
    decoded = json.loads(trial.configuration[key])
    assert isinstance(decoded, dict)
    return {str(sample_id): Decimal(str(value)) for sample_id, value in decoded.items()}


def _completed_net_returns(trial: SyntheticTrial | TrialRecord) -> tuple[Decimal, ...]:
    assert all(value is not None for value in trial.net_returns)
    return tuple(value for value in trial.net_returns if value is not None)


def _required_decimal(value: Decimal | None) -> Decimal:
    assert value is not None
    return value


def _replace_outer_gross_returns(
    trial: SyntheticTrial,
    replacements: dict[str, Decimal],
) -> SyntheticTrial:
    original = _return_evidence(trial, "outer_gross_returns_json")
    sample_ids = tuple(original)
    baseline_costs = {
        sample_id: original[sample_id] - _completed_net_returns(trial)[index]
        for index, sample_id in enumerate(sample_ids)
    }
    updated = {**original, **replacements}
    configuration = dict(trial.configuration)
    configuration["outer_gross_returns_json"] = canonical_json_text(updated)
    return trial.model_copy(
        update={
            "configuration": configuration,
            "net_returns": tuple(
                updated[sample_id] - baseline_costs[sample_id] for sample_id in sample_ids
            ),
        }
    )


def _replace_outer_return_status(
    trial: SyntheticTrial,
    *,
    sample_id: str,
    status: ResearchReturnStatus,
) -> SyntheticTrial:
    gross_evidence = _return_evidence(trial, "outer_gross_returns_json")
    sample_ids = tuple(gross_evidence)
    index = sample_ids.index(sample_id)
    configuration = dict(trial.configuration)
    net_returns = list(trial.net_returns)
    return_statuses = list(trial.return_statuses)
    if status is ResearchReturnStatus.NO_TRADE:
        gross_evidence[sample_id] = Decimal("0")
        net_returns[index] = Decimal("0")
    elif status is ResearchReturnStatus.MISSING:
        net_returns[index] = None
    return_statuses[index] = status
    configuration["outer_gross_returns_json"] = canonical_json_text(gross_evidence)
    return trial.model_copy(
        update={
            "configuration": configuration,
            "net_returns": tuple(net_returns),
            "return_statuses": tuple(return_statuses),
        }
    )


def test_registered_evaluation_is_byte_identical_and_hash_identical(
    mapping: AuthorizedMappingIdentity,
    snapshot: SnapshotBundle,
) -> None:
    first = _evaluate(mapping, snapshot)
    second = _evaluate(mapping, snapshot)

    assert first == second
    assert first.model_dump_json().encode("utf-8") == second.model_dump_json().encode("utf-8")
    assert first.artifact_id == second.artifact_id
    assert first.artifact_sha256 == second.artifact_sha256
    assert first.request_fingerprint_sha256 == second.request_fingerprint_sha256
    assert first.config_hash == second.config_hash


def test_registered_report_contains_every_gate_family_and_passes_research(
    report: EvaluationReport,
) -> None:
    assert tuple(gate.ordinal for gate in report.gates) == tuple(range(len(GateCode)))
    assert tuple(gate.gate_code for gate in report.gates) == tuple(GateCode)
    assert all(gate.outcome is GateOutcome.PASS for gate in report.gates)
    assert all(len(gate.gate_result_sha256) == 64 for gate in report.gates)
    assert report.promotion_state is PromotionState.PASS_RESEARCH
    assert report.reason_codes == ()


def test_pass_research_is_explicitly_not_paper_approval(report: EvaluationReport) -> None:
    assert report.pass_research_is_not_paper_approval is True
    assert report.artifact_type == "synthetic_research_evaluation"
    assert "APPROVED_PAPER" not in {state.value for state in PromotionState}
    assert not hasattr(report, "paper_approval")
    assert any("not paper approval" in warning for warning in report.warnings)


def test_complete_trial_accounting_is_immutable_and_includes_failures(
    report: EvaluationReport,
) -> None:
    assert report.raw_trial_count == len(report.trials) == len(REGISTERED_FIXTURE.trials) == 6
    status_counts = {
        status: sum(trial.status is status for trial in report.trials) for status in TrialStatus
    }
    assert status_counts == {
        TrialStatus.COMPLETED: 4,
        TrialStatus.FAILED: 1,
        TrialStatus.ABANDONED: 1,
        TrialStatus.NO_RETURN: 0,
    }
    assert all(trial.counts_toward_raw is True for trial in report.trials)
    assert all(
        trial.failure_reason
        for trial in report.trials
        if trial.status in {TrialStatus.FAILED, TrialStatus.ABANDONED}
    )
    assert all(
        trial.net_returns == ()
        for trial in report.trials
        if trial.status in {TrialStatus.FAILED, TrialStatus.ABANDONED}
    )
    assert (
        sum((trial.effective_trial_contribution for trial in report.trials), Decimal("0"))
        == report.effective_trial_count
    )
    assert report.effective_trial_count == Decimal("3.060281566406074")

    trial_gate = next(gate for gate in report.gates if gate.gate_code is GateCode.TRIAL_REGISTRY)
    assert trial_gate.inputs["raw_trial_count"] == 6
    assert trial_gate.inputs["selection_evidence_scope"] == "nested_inner_validation_only"
    assert trial_gate.results["failed_count"] == 1
    assert trial_gate.results["abandoned_count"] == 1
    assert trial_gate.results["effective_trial_count"] == Decimal("3.060281566406074")
    selection_rows = json.loads(str(trial_gate.results["outer_fold_selection_json"]))
    assert len(selection_rows) == REGISTERED_POLICY.walk_forward.outer_fold_count
    with pytest.raises(ValidationError, match="frozen"):
        report.trials[0].status = TrialStatus.ABANDONED


def test_trial_registry_binds_configuration_and_selects_only_on_inner_validation(
    report: EvaluationReport,
) -> None:
    for trial in report.trials:
        assert domain_sha256(PHASE5_CONFIG_HASH_DOMAIN, trial.config_preimage) == (
            trial.config_sha256
        )
        assert trial.strategy_family is REGISTERED_POLICY.strategy_family
        assert trial.selection_scope == REGISTERED_POLICY.selection_scope
        assert trial.initiated_at_utc.tzinfo is not None
        assert trial.feature_specification_sha256 == (
            REGISTERED_POLICY.feature_specification.content_sha256
        )
        assert trial.label_specification_sha256 == (
            REGISTERED_POLICY.label_specification.content_sha256
        )

    trial_gate = next(gate for gate in report.gates if gate.gate_code is GateCode.TRIAL_REGISTRY)
    selection_rows = json.loads(str(trial_gate.results["outer_fold_selection_json"]))
    folds_by_id = {str(fold.fold_id): fold for fold in report.folds}
    completed_by_key = {
        trial.trial_key: trial for trial in report.trials if trial.status is TrialStatus.COMPLETED
    }
    fixture_samples_by_id = {sample.sample_id: sample for sample in REGISTERED_FIXTURE.samples}
    inner_sample_ids = tuple(
        dict.fromkeys(
            sample_id for row in selection_rows for sample_id in row["inner_validation_sample_ids"]
        )
    )
    inner_costs = {
        item.sample_id: item.total_cost
        for item in build_cost_ledger(
            tuple(fixture_samples_by_id[sample_id] for sample_id in inner_sample_ids),
            REGISTERED_POLICY.costs,
            REGISTERED_POLICY.stress,
        )
        if item.scenario is CostScenario.BASELINE
    }

    assert REGISTERED_POLICY.selection.primary_selection_metric == "mean_net_return"
    for row in selection_rows:
        outer_fold = folds_by_id[row["outer_fold_id"]]
        assert outer_fold.fold_kind in {FoldKind.OUTER, FoldKind.CPCV}
        validation_ids = tuple(row["inner_validation_sample_ids"])
        assert set(validation_ids) <= set(outer_fold.train_sample_ids)
        assert set(validation_ids).isdisjoint(outer_fold.test_sample_ids)
        scores = {
            trial_key: sum(
                (
                    _return_evidence(trial, "inner_validation_gross_returns_json")[sample_id]
                    - inner_costs[sample_id]
                    for sample_id in validation_ids
                ),
                Decimal("0"),
            )
            / Decimal(len(validation_ids))
            for trial_key, trial in completed_by_key.items()
        }
        assert row["selected_trial_key"] == max(scores, key=scores.__getitem__)
        assert row["selected_trial_key"] == "stable-primary"
        assert Decimal(row["selected_score"]) == scores["stable-primary"]
        selected_id = completed_by_key[row["selected_trial_key"]].trial_id
        ledger_ids = {
            entry.trial_id for entry in report.oos_ledger if entry.fold_id == outer_fold.fold_id
        }
        assert ledger_ids == {selected_id}


def test_outer_oos_outcomes_cannot_influence_inner_fold_selection(
    mapping: AuthorizedMappingIdentity,
    snapshot: SnapshotBundle,
) -> None:
    secondary = REGISTERED_FIXTURE.trials[1]
    shifted_gross = {
        sample_id: value + Decimal("0.05")
        for sample_id, value in _return_evidence(
            secondary,
            "outer_gross_returns_json",
        ).items()
    }
    shifted_secondary = _replace_outer_gross_returns(secondary, shifted_gross)
    trials = (
        REGISTERED_FIXTURE.trials[0],
        shifted_secondary,
        *REGISTERED_FIXTURE.trials[2:],
    )
    mutated = _evaluate(
        mapping,
        snapshot,
        _rehash_fixture(samples=REGISTERED_FIXTURE.samples, trials=trials),
    )
    completed_by_key = {
        trial.trial_key: trial for trial in mutated.trials if trial.status is TrialStatus.COMPLETED
    }
    secondary_mean = sum(
        _completed_net_returns(completed_by_key["stable-secondary"]),
        Decimal("0"),
    ) / Decimal(len(_completed_net_returns(completed_by_key["stable-secondary"])))
    primary_mean = sum(
        _completed_net_returns(completed_by_key["stable-primary"]),
        Decimal("0"),
    ) / Decimal(len(_completed_net_returns(completed_by_key["stable-primary"])))
    assert secondary_mean > primary_mean
    selected_trial_keys = {
        next(trial.trial_key for trial in mutated.trials if trial.trial_id == entry.trial_id)
        for entry in mutated.oos_ledger
    }
    assert selected_trial_keys == {"stable-primary"}


def test_report_carries_exact_policy_audit_evidence(
    report: EvaluationReport,
    snapshot: SnapshotBundle,
) -> None:
    audit_evidence: dict[str, Any] = {
        "artifact_id": report.artifact_id,
        "artifact_type": report.artifact_type,
        "config_hash": report.config_hash,
        "evaluation_policy_id": report.evaluation_policy_id,
        "evaluation_policy_hash": report.evaluation_policy_sha256,
        "data_snapshot_id": tuple(item.snapshot_id for item in report.data_snapshots),
        "code_version_git_sha": report.code_version_git_sha,
        "random_seed": report.random_seed,
        "raw_trial_count": report.raw_trial_count,
        "effective_trial_count": report.effective_trial_count,
        "created_at_utc": report.created_at_utc,
        "parent_artifact_ids": report.parent_artifact_ids,
    }
    assert tuple(audit_evidence) == REGISTERED_POLICY.audit.required_fields
    assert snapshot.snapshot.snapshot_id in audit_evidence["data_snapshot_id"]
    assert len(audit_evidence["data_snapshot_id"]) == 2
    assert {item.capability for item in report.data_snapshots} == {
        DataCapability.OHLCV,
        DataCapability.UNIVERSE_MEMBERSHIP,
    }
    assert report.evaluation_policy_id == REGISTERED_POLICY.policy_id
    assert report.evaluation_policy_sha256 == REGISTERED_POLICY.policy_sha256
    assert report.fixture_id == REGISTERED_FIXTURE.fixture_id
    assert report.fixture_sha256 == REGISTERED_FIXTURE.fixture_sha256
    assert report.code_version_git_sha == CODE_VERSION
    assert report.random_seed == REGISTERED_FIXTURE.random_seed
    assert report.created_at_utc == CREATED_AT
    assert report.created_at_utc.utcoffset() == timedelta(0)
    assert len(report.artifact_sha256) == len(report.config_hash) == 64
    assert report.folds and report.preprocessing_fits and report.oos_ledger and report.cost_ledger
    assert report.metrics and report.gates

    reproducibility = next(
        gate for gate in report.gates if gate.gate_code is GateCode.REPRODUCIBILITY
    )
    assert reproducibility.results == {
        "complete_audit_fields": True,
        "source_derived_feature_bindings_verified": True,
        "synthetic_ledger_inputs_explicit": True,
    }
    assert reproducibility.inputs == {
        "config_hash": report.config_hash,
        "snapshot_bundle_sha256": report.snapshot_bundle_sha256,
        "sample_lineage_sha256": report.sample_lineage_sha256,
        "fixture_sha256": report.fixture_sha256,
        "git_sha": report.code_version_git_sha,
        "random_seed": report.random_seed,
        "feature_derivation_formula": report.feature_specification.formula_id,
        "synthetic_ledger_value_rule": ("deterministic-synthetic-research-ledger-input-v1"),
    }


def test_report_and_oos_rows_preserve_exact_snapshot_value_lineage(
    report: EvaluationReport,
    snapshot: SnapshotBundle,
) -> None:
    assert len(report.source_observations) == 2
    source = next(
        item for item in report.source_observations if item.key.capability is DataCapability.OHLCV
    )
    assert source.normalized_observation == snapshot.normalized_observations[0]
    assert source.normalized_observation.snapshot_id == snapshot.snapshot.snapshot_id
    assert source.normalized_observation.snapshot_sha256 == snapshot.snapshot.snapshot_sha256
    assert len(report.sample_lineage) == len(REGISTERED_FIXTURE.samples) == 20
    assert len(report.sample_lineage_sha256) == 64

    lineage_by_sample = {item.sample_id: item for item in report.sample_lineage}
    assert tuple(lineage_by_sample) == tuple(
        sample.sample_id for sample in REGISTERED_FIXTURE.samples
    )
    assert all(len(item.sample_sha256) == 64 for item in report.sample_lineage)
    assert all(
        item.source_observation_refs
        == tuple(source_item.reference() for source_item in report.source_observations)
        for item in report.sample_lineage
    )
    sample_by_id = {sample.sample_id: sample for sample in REGISTERED_FIXTURE.samples}
    source_payload = source.normalized_observation.payload
    assert isinstance(source_payload, OhlcvBarPayload)
    source_open = source_payload.open
    for lineage in report.sample_lineage:
        sample = sample_by_id[lineage.sample_id]
        assert lineage.feature_derivation == sample.feature_derivation
        assert lineage.synthetic_ledger_value_rule == sample.synthetic_ledger_value_rule
        assert (
            source_open * lineage.feature_derivation.multiplier
            == lineage.feature_derivation.derived_feature_value
            == sample.feature_value
        )
    assert len(report.oos_ledger) == 8
    for entry in report.oos_ledger:
        lineage = lineage_by_sample[entry.sample_id]
        assert entry.sample_sha256 == lineage.sample_sha256
        assert entry.source_observation_refs == lineage.source_observation_refs
        assert entry.decision_time_utc == lineage.decision_time_utc

    data_pit = next(gate for gate in report.gates if gate.gate_code is GateCode.DATA_PIT)
    assert data_pit.inputs["source_observation_count"] == 2
    assert data_pit.inputs["sample_lineage_sha256"] == report.sample_lineage_sha256
    assert data_pit.results["lineage_bound_sample_count"] == 20
    assert data_pit.results["source_derived_feature_count"] == 20
    assert data_pit.results["source_derived_feature_bindings_verified"] is True
    assert data_pit.results["predictions_and_returns_are_synthetic_ledger_inputs"] is True
    assert data_pit.results["oos_lineage_bound_count"] == 8


def test_mutated_source_derived_feature_value_fails_closed(
    mapping: AuthorizedMappingIdentity,
    snapshot: SnapshotBundle,
) -> None:
    original = REGISTERED_FIXTURE.samples[0]
    feature_value = original.feature_value + Decimal("0.0001")
    derivation_content = original.feature_derivation.model_dump(
        mode="python",
        exclude={"derivation_sha256"},
    )
    derivation_content["derived_feature_value"] = feature_value
    mutated_derivation = SourceFeatureDerivation.model_validate(
        {
            **derivation_content,
            "derivation_sha256": domain_sha256(
                "phase5-source-feature-derivation-v1",
                derivation_content,
            ),
        }
    )
    payload = original.model_dump(mode="python")
    payload.update(
        {
            "feature_value": feature_value,
            "feature_derivation": mutated_derivation,
        }
    )
    mutated = SyntheticSample.model_validate(payload)
    fixture = _rehash_fixture(samples=(mutated, *REGISTERED_FIXTURE.samples[1:]))

    with pytest.raises(EvaluationEngineBlocked) as raised:
        _evaluate(mapping, snapshot, fixture)

    assert raised.value.state is PromotionState.BLOCKED_UNCOMPUTABLE
    assert raised.value.reason_codes == ("snapshot_feature_value_mismatch",)


def test_unbound_source_feature_derivation_fails_closed() -> None:
    original = REGISTERED_FIXTURE.samples[0]
    derivation_content = original.feature_derivation.model_dump(
        mode="python",
        exclude={"derivation_sha256"},
    )
    derivation_content["source_observation_key"] = SourceObservationKey(
        capability=DataCapability.OHLCV,
        normalized_observation_id=UUID("ffffffff-ffff-5fff-8fff-ffffffffffff"),
    )
    unbound_derivation = SourceFeatureDerivation.model_validate(
        {
            **derivation_content,
            "derivation_sha256": domain_sha256(
                "phase5-source-feature-derivation-v1",
                derivation_content,
            ),
        }
    )
    payload = original.model_dump(mode="python")
    payload["feature_derivation"] = unbound_derivation
    with pytest.raises(
        ValidationError,
        match="feature derivation must reference a declared sample source observation",
    ):
        SyntheticSample.model_validate(payload)


def test_report_revalidates_derived_feature_against_persisted_source_evidence(
    report: EvaluationReport,
) -> None:
    original_lineage = report.sample_lineage[0]
    derivation_content = original_lineage.feature_derivation.model_dump(
        mode="python",
        exclude={"derivation_sha256"},
    )
    derivation_content["derived_feature_value"] = (
        original_lineage.feature_derivation.derived_feature_value + Decimal("0.0001")
    )
    mutated_derivation = SourceFeatureDerivation.model_validate(
        {
            **derivation_content,
            "derivation_sha256": domain_sha256(
                "phase5-source-feature-derivation-v1",
                derivation_content,
            ),
        }
    )
    mutated_lineage = original_lineage.model_copy(update={"feature_derivation": mutated_derivation})
    lineages = (mutated_lineage, *report.sample_lineage[1:])
    payload = report.model_dump(mode="python")
    payload.update(
        {
            "sample_lineage": lineages,
            "sample_lineage_sha256": domain_sha256(
                "phase5-sample-source-lineage-v1",
                lineages,
            ),
        }
    )

    with pytest.raises(
        ValidationError,
        match="sample feature derivation must reproduce from persisted source evidence",
    ):
        EvaluationReport.model_validate(payload)


def test_oos_minimum_is_a_floor_not_exact_geometry(
    mapping: AuthorizedMappingIdentity,
    snapshot: SnapshotBundle,
) -> None:
    policy = _policy_with_minimum_oos(7)
    report = evaluate_synthetic_fixture(
        policy=policy,
        fixture=REGISTERED_FIXTURE,
        mapping=mapping,
        snapshots=_required_snapshots(mapping, snapshot),
        code_version_git_sha=CODE_VERSION,
        created_at_utc=CREATED_AT,
    )

    sample_gate = next(gate for gate in report.gates if gate.gate_code is GateCode.SAMPLE_ADEQUACY)
    geometry_gate = next(gate for gate in report.gates if gate.gate_code is GateCode.CV_CHRONOLOGY)
    assert sample_gate.outcome is GateOutcome.PASS
    assert sample_gate.thresholds["min_oos_observations"] == 7
    assert sample_gate.inputs["oos_observations"] == 8
    assert geometry_gate.thresholds["minimum_oos_observations"] == 7
    assert geometry_gate.inputs["expected_outer_oos_observation_count"] == 8
    assert geometry_gate.results["observed_outer_oos_observation_count"] == 8


def test_oos_count_below_frozen_minimum_blocks_before_statistics(
    mapping: AuthorizedMappingIdentity,
    snapshot: SnapshotBundle,
) -> None:
    policy = _policy_with_minimum_oos(9)

    with pytest.raises(EvaluationEngineBlocked) as raised:
        evaluate_synthetic_fixture(
            policy=policy,
            fixture=REGISTERED_FIXTURE,
            mapping=mapping,
            snapshots=_required_snapshots(mapping, snapshot),
            code_version_git_sha=CODE_VERSION,
            created_at_utc=CREATED_AT,
        )

    assert raised.value.state is PromotionState.BLOCKED_UNCOMPUTABLE
    assert raised.value.reason_codes == ("insufficient_outer_oos_observations",)


def test_report_metrics_are_complete_and_dsr_uses_baseline_cost_oos(
    report: EvaluationReport,
) -> None:
    metric_ids = {metric.metric_id for metric in report.metrics}
    assert set(CORE_METRIC_IDS) <= metric_ids
    assert {
        "pnl:volatility:low:gross",
        "pnl:volatility:high:net",
        "pnl:rate:rising:gross",
        "pnl:rate:falling:net",
        "pnl:crisis:synthetic-stress-window-v1:net",
        "scenario:all_cost_stress:rejection_rate",
        "cost:liquidity_stress:capacity",
    } <= metric_ids
    assert all(
        metric.formula_version
        and metric.units
        and metric.frequency
        and metric.calendar
        and metric.population
        and metric.denominator
        for metric in report.metrics
    )

    baseline_returns = tuple(
        float(_required_decimal(entry.baseline_net_return)) for entry in report.oos_ledger
    )
    expected_sharpe = fmean(baseline_returns) / stdev(baseline_returns)
    dsr = next(gate for gate in report.gates if gate.gate_code is GateCode.DSR)
    assert dsr.inputs["estimated_sharpe"] == Decimal(str(expected_sharpe))
    assert dsr.inputs["T_nominal"] == len(baseline_returns)
    assert dsr.inputs["serial_correlation_method"] == (
        REGISTERED_POLICY.selection.serial_correlation_method
    )


def test_policy_specifications_and_regime_gate_are_explicit_and_complete(
    report: EvaluationReport,
) -> None:
    signal = REGISTERED_POLICY.signal_specification
    assert signal.executable_decision_lag
    assert signal.universe_eligibility_rule and signal.universe_exclusion_rule
    assert signal.rebalance_rule and signal.holding_rule and signal.overlap_rule
    feature = report.feature_specification
    assert feature.imputation_policy
    assert feature.encoding_policy
    assert feature.feature_selection_policy
    assert feature.hyperparameter_policy

    regime = next(gate for gate in report.gates if gate.gate_code is GateCode.REGIME)
    assert regime.outcome is GateOutcome.PASS
    assert json.loads(str(regime.results["observed_volatility_regimes_json"])) == [
        "high",
        "low",
    ]
    assert json.loads(str(regime.results["observed_rate_regimes_json"])) == [
        "falling",
        "rising",
    ]
    assert json.loads(str(regime.results["observed_crisis_windows_json"])) == [
        "synthetic-stress-window-v1"
    ]
    assert json.loads(str(regime.results["regime_breakdowns_json"]))


def test_cost_ledger_records_fill_rejection_borrow_and_capacity_state(
    report: EvaluationReport,
) -> None:
    assert all(entry.requested_quantity > 0 for entry in report.cost_ledger)
    assert all(
        entry.filled_quantity + entry.unfilled_quantity == entry.requested_quantity
        for entry in report.cost_ledger
    )
    assert all(entry.rejected_quantity == entry.unfilled_quantity for entry in report.cost_ledger)
    assert all(entry.hard_to_borrow_available for entry in report.cost_ledger)
    assert all(entry.capacity_cost == 0 for entry in report.cost_ledger)


def test_report_and_inputs_make_no_real_performance_claim(report: EvaluationReport) -> None:
    assert REGISTERED_FIXTURE.synthetic is True
    assert REGISTERED_FIXTURE.no_real_performance_claimed is True
    assert report.synthetic is True
    assert report.no_real_performance_claimed is True
    assert report.disclaimer == "Synthetic research only; no real performance or investment advice."
    assert any("not real performance" in warning for warning in report.warnings)


def test_missing_snapshots_fail_closed(mapping: AuthorizedMappingIdentity) -> None:
    with pytest.raises(EvaluationEngineBlocked) as raised:
        evaluate_synthetic_fixture(
            policy=REGISTERED_POLICY,
            fixture=REGISTERED_FIXTURE,
            mapping=mapping,
            snapshots=(),
            code_version_git_sha=CODE_VERSION,
            created_at_utc=CREATED_AT,
        )
    assert raised.value.state is PromotionState.BLOCKED_UNCOMPUTABLE
    assert raised.value.reason_codes == ("required_snapshot_missing",)


def test_return_policy_mismatch_fails_before_evaluation(
    mapping: AuthorizedMappingIdentity,
    snapshot: SnapshotBundle,
) -> None:
    mismatched_adequacy = REGISTERED_POLICY.sample_adequacy.model_copy(
        update={"missing_return_policy": "silently_drop_missing_returns"}
    )
    mismatched_policy = REGISTERED_POLICY.model_copy(
        update={"sample_adequacy": mismatched_adequacy}
    )

    with pytest.raises(EvaluationEngineBlocked) as raised:
        evaluate_synthetic_fixture(
            policy=mismatched_policy,
            fixture=REGISTERED_FIXTURE,
            mapping=mapping,
            snapshots=(snapshot,),
            code_version_git_sha=CODE_VERSION,
            created_at_utc=CREATED_AT,
        )

    assert raised.value.state is PromotionState.BLOCKED_MISSING_POLICY
    assert raised.value.reason_codes == ("return_policy_missing_or_mismatch",)


def test_missing_required_snapshot_capability_fails_closed(
    mapping: AuthorizedMappingIdentity,
    snapshot: SnapshotBundle,
) -> None:
    with pytest.raises(EvaluationEngineBlocked) as raised:
        evaluate_synthetic_fixture(
            policy=REGISTERED_POLICY,
            fixture=REGISTERED_FIXTURE,
            mapping=mapping,
            snapshots=(snapshot,),
            code_version_git_sha=CODE_VERSION,
            created_at_utc=CREATED_AT,
        )
    assert raised.value.state is PromotionState.BLOCKED_MISSING_POLICY
    assert raised.value.reason_codes == ("required_snapshot_capability_set_mismatch",)


def test_unrelated_snapshot_observation_cannot_satisfy_fixture_source_reference(
    mapping: AuthorizedMappingIdentity,
) -> None:
    records = list(load_fixture_records())
    bar = next(record for record in records if record.get("alias") == "bar_adjusted")
    payload = bar.get("payload")
    assert isinstance(payload, dict)
    payload["open"] = "50.5"
    unrelated_snapshot = _snapshot_bundle(
        mapping,
        record_definitions=tuple(records),
    )

    with pytest.raises(EvaluationEngineBlocked) as raised:
        _evaluate(mapping, unrelated_snapshot)

    assert raised.value.state is PromotionState.BLOCKED_UNCOMPUTABLE
    assert raised.value.reason_codes == ("snapshot_observation_reference_unresolved",)


def test_mutated_snapshot_value_with_stale_identity_fails_closed(
    mapping: AuthorizedMappingIdentity,
    snapshot: SnapshotBundle,
) -> None:
    original = snapshot.normalized_observations[0]
    tampered = original.model_copy(
        update={
            "payload": original.payload.model_copy(
                update={"open": Decimal("50.5")},
            )
        }
    )
    tampered_snapshot = snapshot.model_copy(update={"normalized_observations": (tampered,)})

    with pytest.raises(EvaluationEngineBlocked) as raised:
        _evaluate(mapping, tampered_snapshot)

    assert raised.value.state is PromotionState.BLOCKED_UNCOMPUTABLE
    assert raised.value.reason_codes == ("snapshot_observation_value_mismatch",)


def test_exact_retained_historical_vintage_is_eligible_when_pit_interval_passes(
    mapping: AuthorizedMappingIdentity,
    snapshot: SnapshotBundle,
) -> None:
    retained_constituents = tuple(
        constituent.model_copy(
            update={"disposition": ConstituentDisposition.RETAINED_HISTORICAL_VINTAGE}
        )
        for constituent in snapshot.constituents
    )
    retained_snapshot = snapshot.model_copy(update={"constituents": retained_constituents})
    expectation = REGISTERED_FIXTURE.source_observation_expectations[0].model_copy(
        update={"required_disposition": ConstituentDisposition.RETAINED_HISTORICAL_VINTAGE}
    )
    fixture = _rehash_fixture(
        samples=REGISTERED_FIXTURE.samples,
        source_observation_expectations=(
            expectation,
            *REGISTERED_FIXTURE.source_observation_expectations[1:],
        ),
    )

    result = _evaluate(mapping, retained_snapshot, fixture)

    assert result.promotion_state is PromotionState.PASS_RESEARCH
    retained_source = next(
        item for item in result.source_observations if item.key.capability is DataCapability.OHLCV
    )
    assert retained_source.disposition is (ConstituentDisposition.RETAINED_HISTORICAL_VINTAGE)


def test_source_observation_from_after_decision_time_fails_closed(
    mapping: AuthorizedMappingIdentity,
    snapshot: SnapshotBundle,
) -> None:
    original = REGISTERED_FIXTURE.samples[0]
    decision_time = datetime(2019, 1, 2, 16, tzinfo=UTC)
    mutated = original.model_copy(
        update={
            "decision_time_utc": decision_time,
            "feature_available_at_utc": decision_time - timedelta(hours=1),
            "label_t0_utc": decision_time,
            "label_t1_utc": decision_time + timedelta(days=2),
        }
    )
    fixture = _rehash_fixture(
        samples=(mutated, *REGISTERED_FIXTURE.samples[1:]),
    )

    with pytest.raises(EvaluationEngineBlocked) as raised:
        _evaluate(mapping, snapshot, fixture)

    assert raised.value.state is PromotionState.BLOCKED_UNCOMPUTABLE
    assert raised.value.reason_codes == ("snapshot_observation_not_available_at_decision",)


def test_trial_returns_must_share_the_exact_outer_oos_calendar(
    mapping: AuthorizedMappingIdentity,
    snapshot: SnapshotBundle,
) -> None:
    original = REGISTERED_FIXTURE.trials[0]
    shifted = original.model_copy(
        update={
            "return_timestamps_utc": (
                original.return_timestamps_utc[0] + timedelta(microseconds=1),
                *original.return_timestamps_utc[1:],
            )
        }
    )
    fixture = _rehash_fixture(
        samples=REGISTERED_FIXTURE.samples,
        trials=(shifted, *REGISTERED_FIXTURE.trials[1:]),
    )

    with pytest.raises(EvaluationEngineBlocked) as raised:
        _evaluate(mapping, snapshot, fixture)

    assert raised.value.state is PromotionState.BLOCKED_UNCOMPUTABLE
    assert raised.value.reason_codes == ("trial_common_calendar_mismatch",)


def test_pbo_trial_net_return_without_matching_cost_lineage_fails_closed(
    mapping: AuthorizedMappingIdentity,
    snapshot: SnapshotBundle,
) -> None:
    secondary = REGISTERED_FIXTURE.trials[1]
    corrupted = secondary.model_copy(
        update={
            "net_returns": (
                _completed_net_returns(secondary)[0] + Decimal("0.000001"),
                *secondary.net_returns[1:],
            )
        }
    )
    fixture = _rehash_fixture(
        samples=REGISTERED_FIXTURE.samples,
        trials=(
            REGISTERED_FIXTURE.trials[0],
            corrupted,
            *REGISTERED_FIXTURE.trials[2:],
        ),
    )

    with pytest.raises(EvaluationEngineBlocked) as raised:
        _evaluate(mapping, snapshot, fixture)

    assert raised.value.state is PromotionState.BLOCKED_UNCOMPUTABLE
    assert raised.value.reason_codes == ("trial_baseline_net_return_lineage_mismatch",)


def test_inner_missing_return_blocks_before_outer_selection(
    mapping: AuthorizedMappingIdentity,
    snapshot: SnapshotBundle,
) -> None:
    primary = REGISTERED_FIXTURE.trials[0]
    configuration = dict(primary.configuration)
    statuses = json.loads(configuration["inner_validation_return_statuses_json"])
    assert isinstance(statuses, dict)
    statuses["synthetic-sample-09"] = ResearchReturnStatus.MISSING.value
    configuration["inner_validation_return_statuses_json"] = canonical_json_text(statuses)
    missing_inner = primary.model_copy(update={"configuration": configuration})
    fixture = _rehash_fixture(
        samples=REGISTERED_FIXTURE.samples,
        trials=(missing_inner, *REGISTERED_FIXTURE.trials[1:]),
    )

    with pytest.raises(EvaluationEngineBlocked) as raised:
        _evaluate(mapping, snapshot, fixture)

    assert raised.value.state is PromotionState.BLOCKED_UNCOMPUTABLE
    assert raised.value.reason_codes == ("required_inner_return_missing",)


def test_nonselected_trial_missing_cell_blocks_synchronous_pbo(
    mapping: AuthorizedMappingIdentity,
    snapshot: SnapshotBundle,
) -> None:
    missing_secondary = _replace_outer_return_status(
        REGISTERED_FIXTURE.trials[1],
        sample_id="synthetic-sample-15",
        status=ResearchReturnStatus.MISSING,
    )
    fixture = _rehash_fixture(
        samples=REGISTERED_FIXTURE.samples,
        trials=(
            REGISTERED_FIXTURE.trials[0],
            missing_secondary,
            *REGISTERED_FIXTURE.trials[2:],
        ),
    )

    with pytest.raises(EvaluationEngineBlocked) as raised:
        _evaluate(mapping, snapshot, fixture)

    assert raised.value.state is PromotionState.BLOCKED_UNCOMPUTABLE
    assert raised.value.reason_codes == ("required_trial_return_missing",)


def test_no_return_trial_on_common_calendar_blocks_statistics(
    mapping: AuthorizedMappingIdentity,
    snapshot: SnapshotBundle,
) -> None:
    original = REGISTERED_FIXTURE.trials[4]
    common_calendar = REGISTERED_FIXTURE.trials[0].return_timestamps_utc
    no_return = original.model_copy(
        update={
            "status": TrialStatus.NO_RETURN,
            "net_returns": tuple(None for _ in common_calendar),
            "return_statuses": tuple(ResearchReturnStatus.MISSING for _ in common_calendar),
            "return_timestamps_utc": common_calendar,
            "failure_reason": "synthetic common-calendar returns unavailable",
        }
    )
    fixture = _rehash_fixture(
        samples=REGISTERED_FIXTURE.samples,
        trials=(*REGISTERED_FIXTURE.trials[:4], no_return, REGISTERED_FIXTURE.trials[5]),
    )

    with pytest.raises(EvaluationEngineBlocked) as raised:
        _evaluate(mapping, snapshot, fixture)

    assert raised.value.state is PromotionState.BLOCKED_UNCOMPUTABLE
    assert raised.value.reason_codes == ("required_trial_return_missing",)


def test_selected_oos_missing_return_fails_before_costing(
    mapping: AuthorizedMappingIdentity,
    snapshot: SnapshotBundle,
) -> None:
    sample_index = 14
    original = REGISTERED_FIXTURE.samples[sample_index]
    missing = original.model_copy(
        update={
            "return_status": ResearchReturnStatus.MISSING,
            "gross_return": None,
        }
    )
    samples = (
        *REGISTERED_FIXTURE.samples[:sample_index],
        missing,
        *REGISTERED_FIXTURE.samples[sample_index + 1 :],
    )

    with pytest.raises(EvaluationEngineBlocked) as raised:
        _evaluate(mapping, snapshot, _rehash_fixture(samples=samples))

    assert raised.value.state is PromotionState.BLOCKED_UNCOMPUTABLE
    assert raised.value.reason_codes == ("required_selected_oos_return_missing",)


def test_no_trade_is_zero_in_trial_pbo_oos_costs_and_metrics(
    mapping: AuthorizedMappingIdentity,
    snapshot: SnapshotBundle,
) -> None:
    no_trade_primary = _replace_outer_return_status(
        REGISTERED_FIXTURE.trials[0],
        sample_id="synthetic-sample-15",
        status=ResearchReturnStatus.NO_TRADE,
    )
    fixture = _rehash_fixture(
        samples=REGISTERED_FIXTURE.samples,
        trials=(no_trade_primary, *REGISTERED_FIXTURE.trials[1:]),
    )
    result = _evaluate(mapping, snapshot, fixture)
    oos_entry = next(
        entry for entry in result.oos_ledger if entry.sample_id == "synthetic-sample-15"
    )
    no_trade_costs = tuple(
        entry for entry in result.cost_ledger if entry.sample_id == oos_entry.sample_id
    )
    gates = {gate.gate_code: gate for gate in result.gates}
    metrics = {metric.metric_id: metric for metric in result.metrics}

    assert oos_entry.return_status is ResearchReturnStatus.NO_TRADE
    assert oos_entry.gross_return == oos_entry.baseline_net_return == 0
    assert len(no_trade_costs) == len(CostScenario)
    assert all(entry.return_status is ResearchReturnStatus.NO_TRADE for entry in no_trade_costs)
    assert all(entry.fill_status == "no_trade" for entry in no_trade_costs)
    assert all(entry.total_cost == entry.net_return == 0 for entry in no_trade_costs)
    assert gates[GateCode.DSR].inputs["T_nominal"] == len(result.oos_ledger)
    assert gates[GateCode.PBO].inputs["matrix_missing_return_count"] == 0
    assert gates[GateCode.PBO].inputs["matrix_no_trade_count"] == 1
    assert len(str(gates[GateCode.PBO].inputs["return_status_matrix_sha256"])) == 64
    assert gates[GateCode.SAMPLE_ADEQUACY].inputs["no_trade_count"] == 1
    assert metrics["sample:missing_return_count"].value == 0
    assert metrics["sample:no_trade_count"].value == 1


def test_future_feature_availability_fails_pit_and_leakage_gates(
    mapping: AuthorizedMappingIdentity,
    snapshot: SnapshotBundle,
) -> None:
    original = REGISTERED_FIXTURE.samples[0]
    mutated = original.model_copy(
        update={"feature_available_at_utc": original.decision_time_utc + timedelta(microseconds=1)}
    )
    samples = (mutated, *REGISTERED_FIXTURE.samples[1:])
    result = _evaluate(mapping, snapshot, _rehash_fixture(samples=samples))
    gates = {gate.gate_code: gate for gate in result.gates}

    assert result.promotion_state is PromotionState.FAIL_REJECT
    assert gates[GateCode.DATA_PIT].outcome is GateOutcome.FAIL
    assert gates[GateCode.DATA_PIT].reason_codes == ("pit_or_delisting_defect",)
    assert gates[GateCode.LEAKAGE].outcome is GateOutcome.FAIL
    assert gates[GateCode.LEAKAGE].reason_codes == ("leakage_l03",)


def _concrete_leakage_mutation(
    original: SyntheticSample,
    code: LeakageCode,
) -> SyntheticSample:
    if code is LeakageCode.L01:
        return original.model_copy(
            update={
                "price_adjustment_basis": "raw_unadjusted",
                "adjustment_action_as_of_utc": original.decision_time_utc
                + timedelta(microseconds=1),
            }
        )
    if code is LeakageCode.L02:
        dependency = "phase4-as-reported-fundamental.revenue"
        revision_id = "synthetic-late-fundamental-revision"
        return original.model_copy(
            update={
                "feature_dependency_ids": tuple(
                    sorted((*original.feature_dependency_ids, dependency))
                ),
                "fundamental_revision": FundamentalRevisionEvidence(
                    dependency_ids=(dependency,),
                    revision_id=revision_id,
                    accepted_at_utc=original.decision_time_utc - timedelta(microseconds=1),
                    available_at_utc=original.decision_time_utc + timedelta(microseconds=1),
                    revision_trace_ids=(
                        "synthetic-parent-fundamental-revision",
                        revision_id,
                    ),
                ),
            }
        )
    if code is LeakageCode.L03:
        return original.model_copy(
            update={
                "feature_available_at_utc": original.decision_time_utc + timedelta(microseconds=1)
            }
        )
    if code is LeakageCode.L04:
        return original.model_copy(
            update={
                "target_dependency_ids": tuple(
                    sorted((*original.target_dependency_ids, original.feature_dependency_ids[0]))
                )
            }
        )
    assert code is LeakageCode.L05
    membership = original.universe_membership
    assert membership is not None
    return original.model_copy(
        update={
            "universe_membership": membership.model_copy(
                update={"as_of_utc": original.decision_time_utc + timedelta(microseconds=1)}
            )
        }
    )


@pytest.mark.parametrize("code", tuple(LeakageCode)[:5])
def test_each_l01_l05_concrete_fixture_defect_blocks_full_engine_promotion(
    mapping: AuthorizedMappingIdentity,
    snapshot: SnapshotBundle,
    code: LeakageCode,
) -> None:
    original = REGISTERED_FIXTURE.samples[0]
    mutated = _concrete_leakage_mutation(original, code)
    result = _evaluate(
        mapping,
        snapshot,
        _rehash_fixture(samples=(mutated, *REGISTERED_FIXTURE.samples[1:])),
    )
    leakage_gate = next(gate for gate in result.gates if gate.gate_code is GateCode.LEAKAGE)

    assert result.promotion_state is PromotionState.FAIL_REJECT
    assert leakage_gate.outcome is GateOutcome.FAIL
    expected_codes = (LeakageCode.L02, LeakageCode.L04) if code is LeakageCode.L02 else (code,)
    assert leakage_gate.reason_codes == tuple(f"leakage_{item.lower()}" for item in expected_codes)
    assert leakage_gate.results["blocking_check_count"] == len(expected_codes)
    assert leakage_gate.results["blocking_check_rate"] == Decimal(len(expected_codes)) / Decimal(
        "6"
    )
    evidence = json.loads(str(leakage_gate.inputs["per_check_evidence_json"]))
    finding = next(item for item in evidence if item["code"] == code.value)
    assert finding["affected_sample_ids"] == [original.sample_id]
    assert len(finding["evidence_records"]) == len(REGISTERED_FIXTURE.samples)
    defective_record = next(
        item for item in finding["evidence_records"] if item.get("sample_id") == original.sample_id
    )
    assert defective_record["passed"] is False
    assert defective_record["reason_codes"]


def test_leakage_gate_persists_complete_clean_structured_evidence(
    report: EvaluationReport,
) -> None:
    leakage_gate = next(gate for gate in report.gates if gate.gate_code is GateCode.LEAKAGE)
    evidence = json.loads(str(leakage_gate.inputs["per_check_evidence_json"]))

    assert [finding["code"] for finding in evidence] == [code.value for code in LeakageCode]
    assert all(finding["blocked"] is False for finding in evidence)
    assert all(finding["evidence_records"] for finding in evidence)
    assert all(
        record["passed"] is True and record["reason_codes"] == []
        for finding in evidence
        for record in finding["evidence_records"]
    )
    l01 = evidence[0]["evidence_records"][0]
    assert l01["source_snapshot_id"] == str(report.data_snapshots[0].snapshot_id)
    assert l01["source_adjustment_basis"] == "as_of_adjusted"
    assert l01["effective_price_basis"] == "adjusted_for_corporate_action"
    l04 = evidence[3]["evidence_records"][0]
    assert l04["adversarial_review"]["review_complete"] is True
    assert len(l04["adversarial_review"]["review_sha256"]) == 64


def test_report_canonical_json_round_trip_preserves_exact_leakage_evidence(
    report: EvaluationReport,
) -> None:
    serialized = canonical_json_text(report.model_dump(mode="python"))

    rehydrated = EvaluationReport.model_validate(json.loads(serialized))

    assert canonical_json_text(rehydrated.model_dump(mode="python")) == serialized


def _rehashed_report_payload_with_leakage_findings(
    report: EvaluationReport,
    findings: list[dict[str, Any]],
    *,
    sample_lineage: tuple[SampleSourceLineage, ...] | None = None,
) -> dict[str, object]:
    leakage_gate = next(gate for gate in report.gates if gate.gate_code is GateCode.LEAKAGE)
    gate_content = leakage_gate.model_dump(
        mode="python",
        exclude={"gate_result_id", "gate_result_sha256"},
    )
    gate_content["inputs"] = {
        **gate_content["inputs"],
        "per_check_evidence_json": canonical_json_text(tuple(findings)),
    }
    gate_sha256 = domain_sha256(PHASE5_GATE_HASH_DOMAIN, gate_content)
    mutated_gate = GateResult.model_validate(
        {
            **gate_content,
            "gate_result_id": identity(PHASE5_GATE_NAMESPACE, gate_sha256),
            "gate_result_sha256": gate_sha256,
        }
    )

    report_payload = report.model_dump(mode="python")
    if sample_lineage is not None:
        report_payload["sample_lineage"] = sample_lineage
        report_payload["sample_lineage_sha256"] = domain_sha256(
            PHASE5_SAMPLE_LINEAGE_HASH_DOMAIN,
            sample_lineage,
        )
    report_payload["gates"] = tuple(
        mutated_gate if gate.gate_code is GateCode.LEAKAGE else gate for gate in report.gates
    )
    artifact_content = {
        key: value
        for key, value in report_payload.items()
        if key not in PHASE5_REPORT_HASH_EXCLUDED_FIELDS
    }
    artifact_sha256 = domain_sha256(PHASE5_ARTIFACT_HASH_DOMAIN, artifact_content)
    report_payload["artifact_sha256"] = artifact_sha256
    report_payload["artifact_id"] = identity(PHASE5_ARTIFACT_NAMESPACE, artifact_sha256)
    return report_payload


def _typed_leakage_findings(report: EvaluationReport) -> list[dict[str, Any]]:
    leakage_gate = next(gate for gate in report.gates if gate.gate_code is GateCode.LEAKAGE)
    typed_evidence = LeakageGateEvidence.model_validate(
        {"findings": json.loads(str(leakage_gate.inputs["per_check_evidence_json"]))}
    )
    return [finding.model_dump(mode="python") for finding in typed_evidence.findings]


def _replace_rehashed_evidence_record(
    findings: list[dict[str, Any]],
    finding_index: int,
    record: dict[str, Any],
) -> None:
    evidence_content = {key: value for key, value in record.items() if key != "evidence_sha256"}
    record["evidence_sha256"] = domain_sha256(
        PHASE5_LEAKAGE_EVIDENCE_HASH_DOMAIN,
        evidence_content,
    )
    records = list(findings[finding_index]["evidence_records"])
    records[0] = record
    findings[finding_index]["evidence_records"] = tuple(records)


def test_report_rejects_coherently_rehashed_l01_price_forgery(
    report: EvaluationReport,
) -> None:
    findings = _typed_leakage_findings(report)
    record = dict(findings[0]["evidence_records"][0])
    source_price = record["source_price"]
    effective_price = record["effective_price"]
    assert isinstance(source_price, Decimal)
    assert isinstance(effective_price, Decimal)
    record["source_price"] = source_price + Decimal("1")
    record["effective_price"] = effective_price + Decimal("1")
    _replace_rehashed_evidence_record(findings, 0, record)

    with pytest.raises(ValidationError, match="must reproduce from exact report source lineage"):
        EvaluationReport.model_validate(
            _rehashed_report_payload_with_leakage_findings(report, findings)
        )


def test_report_rejects_coherently_rehashed_l02_fundamental_forgery(
    report: EvaluationReport,
) -> None:
    findings = _typed_leakage_findings(report)
    record = dict(findings[1]["evidence_records"][0])
    forged_ref = report.sample_lineage[0].source_observation_refs[0].model_dump(mode="python")
    forged_ref["capability"] = DataCapability.AS_REPORTED_FUNDAMENTALS
    decision_time = record["decision_time_utc"]
    assert isinstance(decision_time, datetime)
    dependency_id = "phase4-as-reported-fundamentals.forged_revenue"
    record.update(
        {
            "fundamental_dependency_ids": (dependency_id,),
            "applicable": True,
            "non_applicability_reason": None,
            "source_observation_refs": (forged_ref,),
            "evidence_dependency_ids": (dependency_id,),
            "revision_id": "forged-revision",
            "accepted_at_utc": decision_time - timedelta(hours=2),
            "available_at_utc": decision_time - timedelta(hours=1),
            "revision_trace_ids": ("forged-parent-revision", "forged-revision"),
            "declared_revision_evidence_present": True,
            "declared_revision_matches_source": True,
        }
    )
    _replace_rehashed_evidence_record(findings, 1, record)

    with pytest.raises(ValidationError, match="must reproduce from exact report source lineage"):
        EvaluationReport.model_validate(
            _rehashed_report_payload_with_leakage_findings(report, findings)
        )


def test_report_context_l03_blocks_mismatched_exact_source_reference(
    report: EvaluationReport,
) -> None:
    original = report.sample_lineage[0]
    original_ref = next(
        item for item in original.source_observation_refs if item.capability is DataCapability.OHLCV
    )
    forged_ref = original_ref.model_copy(update={"raw_payload_sha256": "0" * 64})
    refs = tuple(
        forged_ref if item == original_ref else item for item in original.source_observation_refs
    )
    mutated = original.model_copy(update={"source_observation_refs": refs})

    finding = leakage_module.evaluate_leakage_context(
        (mutated,),
        report.source_observations,
        feature_specification=report.feature_specification,
        label_specification=report.label_specification,
    )[2]
    record = finding.evidence_records[0]

    assert finding.blocked is True
    assert record.reason_codes == ("l03_source_observation_ref_mismatch",)
    interval = next(
        item
        for item in record.source_information_intervals
        if item.source_observation_key.capability is DataCapability.OHLCV
    )
    assert interval.declared_source_observation_ref == forged_ref
    assert interval.resolved_source_observation_ref == original_ref
    assert interval.exact_reference_matches is False


def test_report_rejects_rehashed_feature_timestamp_before_exact_source_availability(
    report: EvaluationReport,
) -> None:
    original = report.sample_lineage[0]
    source = next(
        item
        for item in report.source_observations
        if item.key == original.feature_derivation.source_observation_key
    )
    forged_feature_time = source.normalized_observation.available_at - timedelta(microseconds=1)
    assert source.normalized_observation.event_time <= forged_feature_time
    mutated = original.model_copy(update={"feature_available_at_utc": forged_feature_time})
    lineages = (mutated, *report.sample_lineage[1:])

    findings = _typed_leakage_findings(report)
    record = dict(findings[2]["evidence_records"][0])
    record["feature_available_at_utc"] = forged_feature_time
    intervals = [dict(item) for item in record["source_information_intervals"]]
    source_interval = next(
        item
        for item in intervals
        if item["source_observation_key"] == source.key.model_dump(mode="python")
    )
    source_interval["source_available_at_utc"] = forged_feature_time
    record["source_information_intervals"] = tuple(intervals)
    record["passed"] = True
    record["reason_codes"] = ()
    _replace_rehashed_evidence_record(findings, 2, record)

    with pytest.raises(ValidationError, match="must reproduce from exact report source lineage"):
        EvaluationReport.model_validate(
            _rehashed_report_payload_with_leakage_findings(
                report,
                findings,
                sample_lineage=lineages,
            )
        )


def test_report_rejects_coherently_rehashed_l04_dependency_graph_forgery(
    report: EvaluationReport,
) -> None:
    findings = _typed_leakage_findings(report)
    record = dict(findings[3]["evidence_records"][0])
    graph = dict(record["dependency_graph"])
    feature_node = dict(graph["feature_nodes"][0])
    forged_dependency_id = "phase4-ohlcv.volume"
    feature_node["dependency_id"] = forged_dependency_id
    feature_node["source_payload_field"] = "volume"
    graph["feature_nodes"] = (feature_node,)
    graph_content = {key: value for key, value in graph.items() if key != "graph_sha256"}
    graph["graph_sha256"] = domain_sha256(PHASE5_DEPENDENCY_GRAPH_HASH_DOMAIN, graph_content)

    review = dict(record["adversarial_review"])
    review["dependency_graph_sha256"] = graph["graph_sha256"]
    review["baseline_feature_dependency_ids"] = (forged_dependency_id,)
    review["probes"] = tuple(
        {
            **probe,
            "injected_feature_dependency_ids": tuple(
                sorted((forged_dependency_id, probe["candidate_dependency_id"]))
            ),
        }
        for probe in review["probes"]
    )
    review_content = {key: value for key, value in review.items() if key != "review_sha256"}
    review["review_sha256"] = domain_sha256(
        PHASE5_ADVERSARIAL_DEPENDENCY_REVIEW_HASH_DOMAIN,
        review_content,
    )
    record.update(
        {
            "dependency_graph": graph,
            "declared_feature_dependency_ids": (forged_dependency_id,),
            "derived_feature_dependency_ids": (forged_dependency_id,),
            "adversarial_review": review,
        }
    )
    _replace_rehashed_evidence_record(findings, 3, record)

    with pytest.raises(ValidationError, match="must reproduce from exact report source lineage"):
        EvaluationReport.model_validate(
            _rehashed_report_payload_with_leakage_findings(report, findings)
        )


def test_report_rejects_coherently_rehashed_l05_membership_forgery(
    report: EvaluationReport,
) -> None:
    findings = _typed_leakage_findings(report)
    record = dict(findings[4]["evidence_records"][0])
    record["membership_id"] = "invented-membership"
    record["universe_id"] = "invented-universe"
    _replace_rehashed_evidence_record(findings, 4, record)

    with pytest.raises(ValidationError, match="must reproduce from exact report source lineage"):
        EvaluationReport.model_validate(
            _rehashed_report_payload_with_leakage_findings(report, findings)
        )


def test_missing_leakage_evidence_persists_fail_closed_findings(
    mapping: AuthorizedMappingIdentity,
    snapshot: SnapshotBundle,
) -> None:
    original = REGISTERED_FIXTURE.samples[0]
    dependency = "phase4-as-reported-fundamental.revenue"
    mutated = original.model_copy(
        update={
            "price_adjustment_basis": None,
            "feature_dependency_ids": tuple(sorted((*original.feature_dependency_ids, dependency))),
            "fundamental_revision": None,
            "universe_membership": None,
        }
    )
    result = _evaluate(
        mapping,
        snapshot,
        _rehash_fixture(samples=(mutated, *REGISTERED_FIXTURE.samples[1:])),
    )
    leakage_gate = next(gate for gate in result.gates if gate.gate_code is GateCode.LEAKAGE)
    evidence = {
        item["code"]: item
        for item in json.loads(str(leakage_gate.inputs["per_check_evidence_json"]))
    }

    assert result.promotion_state is PromotionState.FAIL_REJECT
    assert leakage_gate.reason_codes == ("leakage_l01", "leakage_l04", "leakage_l05")
    assert (
        "l01_effective_price_basis_missing"
        in (evidence["L01"]["evidence_records"][0]["reason_codes"])
    )
    assert evidence["L02"]["evidence_records"][0]["reason_codes"] == []
    assert evidence["L04"]["evidence_records"][0]["reason_codes"] == [
        "l04_feature_dependency_graph_mismatch"
    ]
    assert evidence["L05"]["evidence_records"][0]["reason_codes"] == [
        "l05_declared_membership_mismatch"
    ]


def test_failed_independent_adversarial_review_persists_and_blocks(
    mapping: AuthorizedMappingIdentity,
    snapshot: SnapshotBundle,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(leakage_module, "_adversarial_overlap_scan", lambda *_: ())
    result = _evaluate(mapping, snapshot)
    leakage_gate = next(gate for gate in result.gates if gate.gate_code is GateCode.LEAKAGE)
    evidence = json.loads(str(leakage_gate.inputs["per_check_evidence_json"]))
    finding = next(item for item in evidence if item["code"] == LeakageCode.L04.value)

    assert result.promotion_state is PromotionState.FAIL_REJECT
    assert leakage_gate.reason_codes == ("leakage_l04",)
    assert finding["blocked"] is True
    assert all(
        not record["adversarial_review"]["review_complete"]
        and record["reason_codes"] == ["l04_adversarial_review_incomplete"]
        for record in finding["evidence_records"]
    )


def test_l06_fold_fit_contamination_blocks_full_engine_promotion(
    mapping: AuthorizedMappingIdentity,
    snapshot: SnapshotBundle,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_builder = engine_module._build_preprocessing_fits

    def contaminated_builder(
        folds: tuple[FoldRecord, ...],
        fixture: SyntheticEvaluationFixture,
    ) -> tuple[PreprocessingFitRecord, ...]:
        fits = real_builder(folds, fixture)
        fold = folds[0]
        fit_index = next(index for index, fit in enumerate(fits) if fit.fold_id == fold.fold_id)
        fit = fits[fit_index]
        unexpected_sample_id = fold.test_sample_ids[0]
        unexpected_sample = next(
            sample for sample in fixture.samples if sample.sample_id == unexpected_sample_id
        )
        contaminated = PreprocessingFitRecord.derive(
            fold_id=fold.fold_id,
            fold_sha256=fold.fold_sha256,
            train_sample_values=tuple(
                sorted(
                    (
                        *fit.train_sample_values,
                        PreprocessingFitSampleValue(
                            sample_id=unexpected_sample.sample_id,
                            sample_sha256=domain_sha256(
                                "phase5-synthetic-sample-v1",
                                unexpected_sample,
                            ),
                            value=unexpected_sample.feature_value,
                        ),
                    ),
                    key=lambda item: item.sample_id,
                )
            ),
        )
        return (*fits[:fit_index], contaminated, *fits[fit_index + 1 :])

    monkeypatch.setattr(engine_module, "_build_preprocessing_fits", contaminated_builder)
    result = _evaluate(mapping, snapshot)
    gates = {gate.gate_code: gate for gate in result.gates}
    leakage_gate = gates[GateCode.LEAKAGE]

    assert result.promotion_state is PromotionState.FAIL_REJECT
    assert gates[GateCode.DATA_PIT].outcome is GateOutcome.PASS
    assert gates[GateCode.PREPROCESSING].outcome is GateOutcome.FAIL
    assert leakage_gate.outcome is GateOutcome.FAIL
    assert leakage_gate.reason_codes == ("leakage_l06",)
    evidence = json.loads(str(leakage_gate.inputs["per_check_evidence_json"]))
    finding = next(item for item in evidence if item["code"] == LeakageCode.L06.value)
    assert finding["affected_sample_ids"]
    assert finding["evidence_records"]


def test_unhandled_delisting_fails_data_pit_gate(
    mapping: AuthorizedMappingIdentity,
    snapshot: SnapshotBundle,
) -> None:
    original = REGISTERED_FIXTURE.samples[0]
    mutated = original.model_copy(update={"delisting_return_handled": False})
    samples = (mutated, *REGISTERED_FIXTURE.samples[1:])
    result = _evaluate(mapping, snapshot, _rehash_fixture(samples=samples))
    gates = {gate.gate_code: gate for gate in result.gates}

    assert result.promotion_state is PromotionState.FAIL_REJECT
    assert gates[GateCode.DATA_PIT].outcome is GateOutcome.FAIL
    assert gates[GateCode.DATA_PIT].results["blocking_sample_count"] == 1
    assert gates[GateCode.DATA_PIT].results["blocking_sample_ids_json"] == (
        '["synthetic-sample-01"]'
    )
    assert gates[GateCode.LEAKAGE].outcome is GateOutcome.PASS


def test_nonpositive_stressed_edge_is_rejected(
    mapping: AuthorizedMappingIdentity,
    snapshot: SnapshotBundle,
) -> None:
    primary = REGISTERED_FIXTURE.trials[0]
    low_edge_gross = {
        sample_id: Decimal("0.001") if index % 2 == 0 else Decimal("-0.001")
        for index, sample_id in enumerate(_return_evidence(primary, "outer_gross_returns_json"))
    }
    low_edge_primary = _replace_outer_gross_returns(primary, low_edge_gross)
    trials = (
        low_edge_primary,
        *REGISTERED_FIXTURE.trials[1:],
    )
    result = _evaluate(
        mapping,
        snapshot,
        _rehash_fixture(samples=REGISTERED_FIXTURE.samples, trials=trials),
    )
    gates = {gate.gate_code: gate for gate in result.gates}
    cost_gate = gates[GateCode.COST_STRESS]

    assert result.promotion_state is PromotionState.FAIL_REJECT
    assert cost_gate.outcome is GateOutcome.FAIL
    assert cost_gate.reason_codes == ("stressed_edge_non_positive_or_policy_limit",)
    for metric_name in (
        "all_cost_net_return",
        "all_cost_net_sharpe",
        "liquidity_net_return",
        "liquidity_net_sharpe",
    ):
        metric_value = cost_gate.results[metric_name]
        assert isinstance(metric_value, Decimal)
        assert metric_value <= 0


def test_dsr_pbo_and_cost_gates_retain_complete_reproducible_numeric_evidence(
    report: EvaluationReport,
) -> None:
    gates = {gate.gate_code: gate for gate in report.gates}
    dsr = gates[GateCode.DSR]
    assert dsr.inputs["formula_version"] == "bailey-lopez-de-prado-dsr-2014-eq2-v1"
    assert dsr.inputs["estimator"] == "per_period_mean_over_sample_standard_deviation_ddof_1"
    assert {"estimated_sharpe", "T", "skew", "ordinary_kurtosis", "V_SR", "N_eff"} <= set(
        dsr.inputs
    )
    assert {
        "expected_maximum_sharpe",
        "z_score",
        "dsr_probability",
        "naive_dsr_probability",
        "passes",
    } == set(dsr.results)

    pbo = gates[GateCode.PBO]
    assert pbo.inputs["selection_metric"] == "mean_return"
    assert pbo.inputs["tie_policy"] == "fail"
    assert pbo.inputs["return_basis"] == "synchronous_baseline_cost_net_returns"
    assert pbo.inputs["trial_ledger_lineage_verified"] is True
    assert len(json.loads(str(pbo.inputs["configuration_order_json"]))) == 4
    assert len(json.loads(str(pbo.inputs["observation_timestamps_utc_json"]))) == 8
    assert len(json.loads(str(pbo.inputs["blocks_json"]))) == 4
    split_details = json.loads(str(pbo.results["split_details_json"]))
    assert len(split_details) == pbo.inputs["split_count"] == 6
    assert all("out_of_sample_ranks" in split and "logit" in split for split in split_details)

    completed = tuple(trial for trial in report.trials if trial.status is TrialStatus.COMPLETED)
    pbo_matrix = tuple(
        tuple(float(_completed_net_returns(trial)[row]) for trial in completed)
        for row in range(len(completed[0].net_returns))
    )
    recomputed_pbo = compute_pbo(
        PBOInputs(
            matrix=pbo_matrix,
            configuration_ids=tuple(trial.trial_key for trial in completed),
            block_count=REGISTERED_POLICY.selection.cscv_block_count,
            selection_metric=PBOSelectionMetric.MEAN_RETURN,
            tie_policy=PBOTiePolicy.FAIL,
            maximum_probability=float(REGISTERED_POLICY.selection.pbo_max),
        )
    )
    assert recomputed_pbo.matrix_sha256 == pbo.inputs["matrix_sha256"]
    baseline_costs = {
        entry.sample_id: entry.total_cost
        for entry in report.cost_ledger
        if entry.scenario is CostScenario.BASELINE
    }
    oos_sample_ids = tuple(entry.sample_id for entry in report.oos_ledger)
    for trial in completed:
        gross_evidence = _return_evidence(trial, "outer_gross_returns_json")
        assert trial.net_returns == tuple(
            gross_evidence[sample_id] - baseline_costs[sample_id] for sample_id in oos_sample_ids
        )
    trials_by_id = {trial.trial_id: trial for trial in completed}
    for index, entry in enumerate(report.oos_ledger):
        selected_trial = trials_by_id[entry.trial_id]
        assert entry.baseline_net_return == selected_trial.net_returns[index]
        assert entry.baseline_net_return == (
            _required_decimal(entry.gross_return) - baseline_costs[entry.sample_id]
        )

    cost = gates[GateCode.COST_STRESS]
    assert set(cost.thresholds) == {
        "min_stressed_net_pnl",
        "min_stressed_annual_return",
        "min_stressed_sharpe",
        "max_stressed_drawdown",
        "max_capacity_breach_rate",
    }
    assert {
        "all_cost_net_return",
        "all_cost_annualized_net_return",
        "all_cost_net_sharpe",
        "all_cost_maximum_drawdown",
        "all_cost_capacity_breach_rate",
        "liquidity_net_return",
        "liquidity_annualized_net_return",
        "liquidity_net_sharpe",
        "liquidity_maximum_drawdown",
        "liquidity_capacity_breach_rate",
        "all_cost_fill_rate",
        "all_cost_rejection_rate",
        "liquidity_fill_rate",
        "liquidity_rejection_rate",
    } <= set(cost.results)


def test_cost_ledger_contains_all_scenarios_with_preserved_allocations(
    report: EvaluationReport,
) -> None:
    allocation_hashes = {
        scenario: tuple(
            entry.allocation_input_sha256
            for entry in report.cost_ledger
            if entry.scenario is scenario
        )
        for scenario in CostScenario
    }
    assert len(set(allocation_hashes.values())) == 1
    cost_gate = next(gate for gate in report.gates if gate.gate_code is GateCode.COST_STRESS)
    assert cost_gate.inputs["allocation_inputs_preserved"] is True
    all_cost_multiplier = cost_gate.inputs["all_cost_multiplier"]
    assert isinstance(all_cost_multiplier, Decimal)
    assert all_cost_multiplier >= Decimal("2")
