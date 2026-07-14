from __future__ import annotations

import json
import os
from collections import Counter
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from threading import Barrier, get_ident
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from fable5_backtester.canonical import (
    PHASE5_ARTIFACT_HASH_DOMAIN,
    PHASE5_COST_HASH_DOMAIN,
    PHASE5_FEATURE_HASH_DOMAIN,
    PHASE5_FEATURE_NAMESPACE,
    PHASE5_FIT_HASH_DOMAIN,
    PHASE5_FIT_NAMESPACE,
    PHASE5_FIXTURE_HASH_DOMAIN,
    PHASE5_LABEL_HASH_DOMAIN,
    PHASE5_LABEL_NAMESPACE,
    PHASE5_LEDGER_HASH_DOMAIN,
    PHASE5_LEDGER_NAMESPACE,
    PHASE5_POLICY_HASH_DOMAIN,
    PHASE5_SAMPLE_HASH_DOMAIN,
    PHASE5_SAMPLE_LINEAGE_HASH_DOMAIN,
    PHASE5_TRAIN_ONLY_FIT_HASH_DOMAIN,
    PHASE5_TRIAL_HASH_DOMAIN,
    canonical_json_text,
    domain_sha256,
    identity,
)
from fable5_backtester.contracts import (
    EvaluationPolicyCreateRequest,
    EvaluationReport,
    EvaluationRunCreateRequest,
    FeatureSpecification,
    FrozenEvaluationPolicy,
    LabelSpecification,
    PreprocessingFitRecord,
    PreprocessingFitSampleValue,
    ResearchReturnStatus,
    SyntheticEvaluationFixture,
    TrialStatus,
)
from fable5_backtester.engine import (
    evaluate_synthetic_fixture,
    evaluation_report_hash_payload,
)
from fable5_backtester.outcomes import BlockedEvaluationOutcome
from fable5_backtester.repository import EvaluationRepository
from fable5_backtester.synthetic import REGISTERED_FIXTURE, REGISTERED_POLICY, resolve_fixture
from fable5_backtester.workflow import (
    EvaluationWorkflow,
    EvaluationWorkflowBlocked,
    EvaluationWorkflowConflict,
)
from fable5_data.canonical import canonicalize
from fable5_data.contracts import DataCapability, SnapshotBundle, SnapshotRequestParameters
from fable5_data.quality import (
    QualityAcceptedResult,
    QualityReferenceCatalog,
    run_mandatory_data_quality,
)
from fable5_data.repository import SnapshotRepository
from fable5_data.snapshots import SnapshotCandidate, build_snapshot_candidate
from fable5_data.synthetic import (
    SYNTHETIC_MOCK_CONFIGURATION,
    SyntheticPointInTimeAdapter,
)
from fable5_extraction.extractor import default_extraction_profile
from fable5_extraction.models import SourceAuthority, SourceIntakeRequest, SourceType
from fable5_extraction.repository import IdeaRepository
from fable5_extraction.workflow import process_extraction
from fable5_mapping.models import CanonicalFamily, MappingWithRationale, ResearchVerdict
from fable5_mapping.repository import MappingRepository
from sqlalchemy import Engine, create_engine, event, inspect, text
from sqlalchemy.exc import DBAPIError

DATABASE_URL = os.environ.get("FABLE5_TEST_DATABASE_URL")
CODE_VERSION_GIT_SHA = os.environ.get("FABLE5_CODE_VERSION_GIT_SHA", "a" * 40)
pytestmark = pytest.mark.skipif(
    DATABASE_URL is None,
    reason="set FABLE5_TEST_DATABASE_URL to an isolated PostgreSQL database",
)

AS_OF = datetime(2024, 1, 3, tzinfo=UTC)
PHASE5_TABLES = (
    "evaluation_policies",
    "evaluation_feature_specs",
    "evaluation_label_specs",
    "evaluation_blocked_outcomes",
    "evaluation_reports",
    "evaluation_report_snapshots",
    "evaluation_trials",
    "evaluation_folds",
    "evaluation_preprocessing_fits",
    "evaluation_oos_ledger",
    "evaluation_cost_ledger",
    "evaluation_gate_results",
)
POLICY_TABLES = PHASE5_TABLES[:3]
OUTCOME_TABLES = ("evaluation_blocked_outcomes",)
REPORT_TABLES = PHASE5_TABLES[4:]


def _upgrade_phase5(database_url: str) -> None:
    prior = os.environ.get("FABLE5_DATABASE_URL")
    os.environ["FABLE5_DATABASE_URL"] = database_url
    try:
        command.upgrade(Config("services/api/alembic.ini"), "0005_phase5")
    finally:
        if prior is None:
            os.environ.pop("FABLE5_DATABASE_URL", None)
        else:
            os.environ["FABLE5_DATABASE_URL"] = prior


def _create_family_a_mapping(
    ideas: IdeaRepository,
    mappings: MappingRepository,
    *,
    key: str,
) -> MappingWithRationale:
    _, source = ideas.create_source(
        SourceIntakeRequest(
            source_type=SourceType.SYNTHETIC_FIXTURE,
            source_authority=SourceAuthority.OTHER,
            raw_text=(
                "Rank stocks in a point-in-time universe and select the top-ranked group "
                "when scores are refreshed weekly. Include delisting-aware returns and "
                f"liquid shares. Synthetic PostgreSQL evidence key {key}."
            ),
            ingest_idempotency_key=key,
        )
    )
    request = ideas.create_extraction_request(
        source.source_version_id,
        default_extraction_profile(),
    )
    card = process_extraction(ideas, request.extraction_request_id)
    result = mappings.create_mapping(card.card_id)
    assert result.mapping.canonical_family is CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING
    assert result.mapping.verdict is ResearchVerdict.BUILD_RESEARCH
    return result


def _create_snapshot(
    repository: SnapshotRepository,
    mapping_id: UUID,
    capability: DataCapability,
) -> SnapshotBundle:
    mapping = repository.resolve_mapping(mapping_id, capability)
    adapter = SyntheticPointInTimeAdapter.for_mapping(mapping)
    request = SnapshotRequestParameters(
        mapping=mapping,
        as_of_utc=AS_OF,
        capability=capability,
        mock_configuration_id=SYNTHETIC_MOCK_CONFIGURATION.configuration_id,
    )
    result = adapter.fetch(capability)
    quality = run_mandatory_data_quality(
        request=request,
        result=result,
        configuration=SYNTHETIC_MOCK_CONFIGURATION,
        catalog=QualityReferenceCatalog.from_results(adapter.all_results()),
    )
    assert isinstance(quality, QualityAcceptedResult)
    candidate = build_snapshot_candidate(
        mapping=mapping,
        request=request,
        profile=result.profile,
        configuration=SYNTHETIC_MOCK_CONFIGURATION,
        batch=quality.batch,
        created_at_utc=AS_OF,
    )
    assert isinstance(candidate, SnapshotCandidate)
    return repository.create_snapshot(candidate)


def _unique_policy(token: str) -> FrozenEvaluationPolicy:
    suffix = token[:12]
    feature_content = REGISTERED_POLICY.feature_specification.model_dump(
        mode="python",
        exclude={"feature_specification_id", "content_sha256"},
    )
    feature_content["version"] = f"phase5-postgres-feature-{suffix}"
    feature_hash = domain_sha256(PHASE5_FEATURE_HASH_DOMAIN, feature_content)
    feature = FeatureSpecification.model_validate(
        {
            **feature_content,
            "feature_specification_id": identity(PHASE5_FEATURE_NAMESPACE, feature_hash),
            "content_sha256": feature_hash,
        }
    )

    label_content = REGISTERED_POLICY.label_specification.model_dump(
        mode="python",
        exclude={"label_specification_id", "content_sha256"},
    )
    label_content["version"] = f"phase5-postgres-label-{suffix}"
    label_hash = domain_sha256(PHASE5_LABEL_HASH_DOMAIN, label_content)
    label = LabelSpecification.model_validate(
        {
            **label_content,
            "label_specification_id": identity(PHASE5_LABEL_NAMESPACE, label_hash),
            "content_sha256": label_hash,
        }
    )

    policy_content = REGISTERED_POLICY.model_dump(
        mode="python",
        exclude={"policy_sha256", "policy_canonical_json"},
    )
    policy_content.update(
        {
            "policy_id": uuid4(),
            "selection_scope": f"synthetic-postgres-{suffix}",
            "feature_specification": feature,
            "label_specification": label,
        }
    )
    policy_hash = domain_sha256(PHASE5_POLICY_HASH_DOMAIN, policy_content)
    return FrozenEvaluationPolicy.model_validate(
        {
            **policy_content,
            "policy_sha256": policy_hash,
            "policy_canonical_json": canonical_json_text(policy_content),
        }
    )


def _policy_resolver(policy: FrozenEvaluationPolicy):  # type: ignore[no-untyped-def]
    def resolve(policy_id: UUID, policy_version: int) -> FrozenEvaluationPolicy | None:
        if (policy_id, policy_version) == (policy.policy_id, policy.policy_version):
            return policy
        return None

    return resolve


def _fixture_with_no_trade() -> SyntheticEvaluationFixture:
    primary = REGISTERED_FIXTURE.trials[0]
    gross_evidence = {
        str(sample_id): value
        for sample_id, value in json.loads(
            primary.configuration["outer_gross_returns_json"],
            parse_float=Decimal,
        ).items()
    }
    sample_ids = tuple(gross_evidence)
    sample_id = "synthetic-sample-15"
    index = sample_ids.index(sample_id)
    gross_evidence[sample_id] = Decimal("0")
    configuration = dict(primary.configuration)
    configuration["outer_gross_returns_json"] = canonical_json_text(gross_evidence)
    net_returns = list(primary.net_returns)
    net_returns[index] = Decimal("0")
    return_statuses = list(primary.return_statuses)
    return_statuses[index] = ResearchReturnStatus.NO_TRADE
    no_trade_trial = primary.model_copy(
        update={
            "configuration": configuration,
            "net_returns": tuple(net_returns),
            "return_statuses": tuple(return_statuses),
        }
    )
    content = REGISTERED_FIXTURE.model_dump(mode="python", exclude={"fixture_sha256"})
    content["trials"] = (no_trade_trial, *REGISTERED_FIXTURE.trials[1:])
    digest = domain_sha256(PHASE5_FIXTURE_HASH_DOMAIN, content)
    return SyntheticEvaluationFixture.model_validate({**content, "fixture_sha256": digest})


def _workflow(
    evaluations: EvaluationRepository,
    snapshots: SnapshotRepository,
    policy: FrozenEvaluationPolicy,
    *,
    code_version_git_sha: str | None = CODE_VERSION_GIT_SHA,
    outcome_clock: Callable[[], datetime] | None = None,
) -> EvaluationWorkflow:
    return EvaluationWorkflow(
        repository=evaluations,
        snapshot_repository=snapshots,
        code_version_git_sha=code_version_git_sha,
        policy_resolver=_policy_resolver(policy),
        fixture_resolver=resolve_fixture,
        outcome_clock=outcome_clock,
    )


@dataclass(frozen=True)
class PersistedGraph:
    ideas: IdeaRepository
    mappings: MappingRepository
    snapshots: SnapshotRepository
    evaluations: EvaluationRepository
    mapping: MappingWithRationale
    snapshot: SnapshotBundle
    membership_snapshot: SnapshotBundle
    policy: FrozenEvaluationPolicy
    report: EvaluationReport


@pytest.fixture(scope="module")
def persisted_graph() -> Iterator[PersistedGraph]:
    assert DATABASE_URL is not None
    _upgrade_phase5(DATABASE_URL)
    ideas = IdeaRepository(DATABASE_URL)
    mappings = MappingRepository(DATABASE_URL)
    snapshots = SnapshotRepository(DATABASE_URL)
    evaluations = EvaluationRepository(DATABASE_URL)
    unique = uuid4().hex
    try:
        mapping = _create_family_a_mapping(
            ideas,
            mappings,
            key=f"phase5-postgres-roundtrip-{unique}",
        )
        snapshot = _create_snapshot(
            snapshots,
            mapping.mapping.mapping_id,
            DataCapability.OHLCV,
        )
        membership_snapshot = _create_snapshot(
            snapshots,
            mapping.mapping.mapping_id,
            DataCapability.UNIVERSE_MEMBERSHIP,
        )
        policy = _unique_policy(unique)
        workflow = _workflow(evaluations, snapshots, policy)
        stored_policy = workflow.create_policy(
            EvaluationPolicyCreateRequest(
                policy_id=policy.policy_id,
                policy_version=policy.policy_version,
            )
        )
        assert stored_policy == policy
        report = workflow.create_report(
            EvaluationRunCreateRequest(
                policy_id=policy.policy_id,
                policy_version=policy.policy_version,
                mapping_id=mapping.mapping.mapping_id,
                snapshot_ids=(
                    snapshot.snapshot.snapshot_id,
                    membership_snapshot.snapshot.snapshot_id,
                ),
                fixture_id=REGISTERED_FIXTURE.fixture_id,
            )
        )
        yield PersistedGraph(
            ideas=ideas,
            mappings=mappings,
            snapshots=snapshots,
            evaluations=evaluations,
            mapping=mapping,
            snapshot=snapshot,
            membership_snapshot=membership_snapshot,
            policy=policy,
            report=report,
        )
    finally:
        evaluations.dispose()
        snapshots.dispose()
        mappings.dispose()
        ideas.dispose()


def _graph_counts(
    engine: Engine,
    policy: FrozenEvaluationPolicy,
    report: EvaluationReport,
) -> dict[str, int]:
    counts: dict[str, int] = {}
    with engine.connect() as connection:
        for table in PHASE5_TABLES:
            if table in POLICY_TABLES:
                where = "policy_id = :policy_id AND policy_version = :policy_version"
                parameters = {
                    "policy_id": policy.policy_id,
                    "policy_version": policy.policy_version,
                }
            elif table in OUTCOME_TABLES:
                where = "policy_id = :policy_id AND policy_version = :policy_version"
                parameters = {
                    "policy_id": policy.policy_id,
                    "policy_version": policy.policy_version,
                }
            else:
                where = "report_id = :report_id"
                parameters = {"report_id": report.artifact_id}
            counts[table] = connection.execute(
                text(f"SELECT count(*) FROM {table} WHERE {where}"),
                parameters,
            ).scalar_one()
    return counts


def _expected_payloads(
    policy: FrozenEvaluationPolicy,
    report: EvaluationReport,
) -> dict[str, tuple[object, ...]]:
    policy_payload = policy.model_dump(
        mode="python",
        exclude={"policy_sha256", "policy_canonical_json"},
    )
    feature_payload = policy.feature_specification.model_dump(
        mode="python",
        exclude={"feature_specification_id", "content_sha256"},
    )
    label_payload = policy.label_specification.model_dump(
        mode="python",
        exclude={"label_specification_id", "content_sha256"},
    )
    snapshot_payloads = tuple(
        {
            "report_id": report.artifact_id,
            "ordinal": ordinal,
            "snapshot_evidence": evidence,
        }
        for ordinal, evidence in enumerate(report.data_snapshots)
    )
    fit_payloads = tuple(
        {
            "fit_sha256": fit.fit_sha256,
            "mean": fit.mean,
            "standard_deviation": fit.standard_deviation,
            "ddof": fit.ddof,
        }
        for fit in report.preprocessing_fits
    )
    return {
        "evaluation_policies": (policy_payload,),
        "evaluation_feature_specs": (feature_payload,),
        "evaluation_label_specs": (label_payload,),
        "evaluation_reports": (evaluation_report_hash_payload(report),),
        "evaluation_report_snapshots": snapshot_payloads,
        "evaluation_trials": tuple(
            item.model_dump(mode="python", exclude={"trial_id", "trial_sha256"})
            for item in report.trials
        ),
        "evaluation_folds": tuple(
            item.model_dump(mode="python", exclude={"fold_id", "fold_sha256"})
            for item in report.folds
        ),
        "evaluation_preprocessing_fits": fit_payloads,
        "evaluation_oos_ledger": tuple(
            item.model_dump(
                mode="python",
                exclude={"ledger_entry_id", "ledger_entry_sha256"},
            )
            for item in report.oos_ledger
        ),
        "evaluation_cost_ledger": tuple(
            item.model_dump(
                mode="python",
                exclude={"cost_entry_id", "cost_entry_sha256"},
            )
            for item in report.cost_ledger
        ),
        "evaluation_gate_results": tuple(
            item.model_dump(
                mode="python",
                exclude={"gate_result_id", "gate_result_sha256"},
            )
            for item in report.gates
        ),
    }


def test_phase5_online_migration_reaches_0005_and_creates_exact_table_set() -> None:
    assert DATABASE_URL is not None
    _upgrade_phase5(DATABASE_URL)
    engine = create_engine(DATABASE_URL)
    try:
        with engine.connect() as connection:
            revision = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
            assert revision == "0005_phase5"
        tables = set(inspect(engine).get_table_names())
        assert set(PHASE5_TABLES) <= tables
        assert len(PHASE5_TABLES) == 12
    finally:
        engine.dispose()


def test_phase5_policy_report_roundtrip_exact_counts_payloads_and_trial_registry(
    persisted_graph: PersistedGraph,
) -> None:
    graph = persisted_graph
    report = graph.report
    policy = graph.policy
    manifest = graph.snapshot.snapshot.manifest.payload

    assert manifest.mapping.mapping_id == graph.mapping.mapping.mapping_id
    assert manifest.mapping.canonical_family is CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING
    assert manifest.mapping.verdict is ResearchVerdict.BUILD_RESEARCH
    assert manifest.request.capability is DataCapability.OHLCV
    assert graph.snapshots.get_snapshot(graph.snapshot.snapshot.snapshot_id) == graph.snapshot
    assert (
        graph.snapshots.get_snapshot(graph.membership_snapshot.snapshot.snapshot_id)
        == graph.membership_snapshot
    )
    assert graph.evaluations.get_policy(policy.policy_id, policy.policy_version) == policy
    assert graph.evaluations.get_report(report.artifact_id) == report
    assert policy in graph.evaluations.list_policies(limit=100)
    assert report.artifact_id in {
        item.artifact_id for item in graph.evaluations.list_reports(limit=100)
    }
    required_capabilities = tuple(policy.required_snapshot_capabilities)
    assert required_capabilities == (
        DataCapability.OHLCV,
        DataCapability.UNIVERSE_MEMBERSHIP,
    )
    source_by_key = {item.key: item for item in report.source_observations}
    for lineage in report.sample_lineage:
        assert tuple(ref.capability for ref in lineage.source_observation_refs) == (
            required_capabilities
        )
        membership_source = source_by_key[lineage.membership_source_observation_key]
        feature_source = source_by_key[lineage.feature_derivation.source_observation_key]
        assert membership_source.normalized_observation.payload.record_type == (
            "universe_membership"
        )
        assert membership_source.normalized_observation.payload.status.value == "included"
        assert membership_source.normalized_observation.instrument_id == (
            feature_source.normalized_observation.instrument_id
        )
        assert membership_source.normalized_observation.listing_id == (
            feature_source.normalized_observation.listing_id
        )
        assert membership_source.normalized_observation.available_at <= lineage.decision_time_utc
        assert membership_source.normalized_observation.valid_from <= lineage.decision_time_utc
        assert (
            membership_source.normalized_observation.valid_to is None
            or lineage.decision_time_utc < membership_source.normalized_observation.valid_to
        )
    fits_by_fold = Counter(item.fold_id for item in report.preprocessing_fits)
    assert fits_by_fold == Counter({fold.fold_id: 1 for fold in report.folds})
    lineage_ids = {item.sample_id for item in report.sample_lineage}
    for fit in report.preprocessing_fits:
        fold = next(item for item in report.folds if item.fold_id == fit.fold_id)
        assert fit.train_sample_ids == fold.train_sample_ids
        assert set(fit.train_sample_ids).isdisjoint(
            {
                *fold.test_sample_ids,
                *fold.purged_sample_ids,
                *fold.embargoed_sample_ids,
            }
        )
        assert set(fit.train_sample_ids) <= lineage_ids

    expected_counts = {
        "evaluation_policies": 1,
        "evaluation_feature_specs": 1,
        "evaluation_label_specs": 1,
        "evaluation_blocked_outcomes": 0,
        "evaluation_reports": 1,
        "evaluation_report_snapshots": len(report.data_snapshots),
        "evaluation_trials": len(report.trials),
        "evaluation_folds": len(report.folds),
        "evaluation_preprocessing_fits": len(report.preprocessing_fits),
        "evaluation_oos_ledger": len(report.oos_ledger),
        "evaluation_cost_ledger": len(report.cost_ledger),
        "evaluation_gate_results": len(report.gates),
    }
    assert _graph_counts(graph.evaluations.engine, policy, report) == expected_counts

    expected_payloads = _expected_payloads(policy, report)
    with graph.evaluations.engine.connect() as connection:
        for table, payloads in expected_payloads.items():
            if table in POLICY_TABLES:
                where = "policy_id = :policy_id AND policy_version = :policy_version"
                parameters = {
                    "policy_id": policy.policy_id,
                    "policy_version": policy.policy_version,
                }
            else:
                where = "report_id = :report_id"
                parameters = {"report_id": report.artifact_id}
            order_by = (
                ""
                if table in {"evaluation_policies", "evaluation_reports"}
                else (" ORDER BY ordinal")
            )
            rows = connection.execute(
                text(f"SELECT canonical_json, payload FROM {table} WHERE {where}{order_by}"),
                parameters,
            ).mappings()
            assert [row["payload"] for row in rows] == [
                canonicalize(payload) for payload in payloads
            ]
            rows = connection.execute(
                text(f"SELECT canonical_json, payload FROM {table} WHERE {where}{order_by}"),
                parameters,
            ).mappings()
            assert [row["canonical_json"] for row in rows] == [
                canonical_json_text(payload) for payload in payloads
            ]

        header = connection.execute(
            text(
                "SELECT expected_snapshot_count, expected_trial_count, expected_fold_count, "
                "expected_preprocessing_fit_count, expected_oos_ledger_count, "
                "expected_cost_ledger_count, expected_gate_result_count, raw_trial_count, "
                "expected_source_observation_count, expected_sample_lineage_count, "
                "sample_lineage_sha256, sample_lineage_canonical_json, "
                "source_observations, sample_lineage "
                "FROM evaluation_reports WHERE report_id = :report_id"
            ),
            {"report_id": report.artifact_id},
        ).one()
        assert tuple(header) == (
            len(report.data_snapshots),
            len(report.trials),
            len(report.folds),
            len(report.preprocessing_fits),
            len(report.oos_ledger),
            len(report.cost_ledger),
            len(report.gates),
            len(report.trials),
            len(report.source_observations),
            len(report.sample_lineage),
            report.sample_lineage_sha256,
            canonical_json_text(report.sample_lineage),
            canonicalize(report.source_observations),
            canonicalize(report.sample_lineage),
        )
        fit_records = connection.execute(
            text(
                "SELECT record_payload FROM evaluation_preprocessing_fits "
                "WHERE report_id = :report_id ORDER BY ordinal"
            ),
            {"report_id": report.artifact_id},
        ).scalars()
        assert list(fit_records) == [canonicalize(item) for item in report.preprocessing_fits]

        trial_rows = (
            connection.execute(
                text(
                    "SELECT status, failure_reason, oos_return_state, net_returns, "
                    "return_statuses, return_timestamps_utc, return_observation_count, "
                    "missing_return_count, no_trade_count, payload "
                    "FROM evaluation_trials "
                    "WHERE report_id = :report_id ORDER BY ordinal"
                ),
                {"report_id": report.artifact_id},
            )
            .mappings()
            .all()
        )
        policy_return_rules = connection.execute(
            text(
                "SELECT missing_return_policy, no_trade_return_policy "
                "FROM evaluation_policies "
                "WHERE policy_id = :policy_id AND policy_version = :policy_version"
            ),
            {
                "policy_id": policy.policy_id,
                "policy_version": policy.policy_version,
            },
        ).one()
        oos_return_rows = connection.execute(
            text(
                "SELECT return_status, gross_return, baseline_net_return, sample_sha256, "
                "source_observation_refs "
                "FROM evaluation_oos_ledger WHERE report_id = :report_id"
            ),
            {"report_id": report.artifact_id},
        ).all()
        cost_return_rows = connection.execute(
            text(
                "SELECT return_status, fill_status FROM evaluation_cost_ledger "
                "WHERE report_id = :report_id"
            ),
            {"report_id": report.artifact_id},
        ).all()

    assert len(trial_rows) == report.raw_trial_count == 6
    assert tuple(policy_return_rules) == (
        "block_missing_return_v1",
        "explicit_zero_research_observation_v1",
    )
    assert Counter(row["status"] for row in trial_rows) == Counter(
        {
            TrialStatus.COMPLETED.value: 4,
            TrialStatus.FAILED.value: 1,
            TrialStatus.ABANDONED.value: 1,
        }
    )
    assert all(row["payload"]["counts_toward_raw"] is True for row in trial_rows)
    assert all(
        row["return_observation_count"]
        == len(row["net_returns"])
        == len(row["return_statuses"])
        == len(row["return_timestamps_utc"])
        for row in trial_rows
    )
    assert all(
        row["missing_return_count"] == row["return_statuses"].count("missing")
        and row["no_trade_count"] == row["return_statuses"].count("no_trade")
        for row in trial_rows
    )
    assert all(
        row["oos_return_state"]
        == ("complete_common_calendar" if row["status"] == "completed" else row["status"])
        for row in trial_rows
    )
    assert all(
        row["failure_reason"] and row["payload"]["net_returns"] == []
        for row in trial_rows
        if row["status"] in {TrialStatus.FAILED.value, TrialStatus.ABANDONED.value}
    )
    assert all(
        row[0] == "observed" and row[1] is not None and row[2] is not None
        for row in oos_return_rows
    )
    assert all(
        row[3] in {item.sample_sha256 for item in report.sample_lineage}
        and row[4]
        == canonicalize(
            next(
                item.source_observation_refs
                for item in report.sample_lineage
                if item.sample_sha256 == row[3]
            )
        )
        for row in oos_return_rows
    )
    assert all(
        row[0] == "observed" and row[1] in {"filled", "capacity_rejected"}
        for row in cost_return_rows
    )


def test_phase5_no_trade_return_state_roundtrips_as_exact_zero_economics(
    persisted_graph: PersistedGraph,
) -> None:
    graph = persisted_graph
    fixture = _fixture_with_no_trade()
    report = evaluate_synthetic_fixture(
        policy=graph.policy,
        fixture=fixture,
        mapping=graph.snapshot.snapshot.manifest.payload.mapping,
        snapshots=(graph.snapshot, graph.membership_snapshot),
        code_version_git_sha="d" * 40,
        created_at_utc=datetime(2026, 7, 14, tzinfo=UTC),
    )

    stored = graph.evaluations.create_report(report)
    assert stored.artifact_id == report.artifact_id
    assert stored.artifact_sha256 == report.artifact_sha256

    with graph.evaluations.engine.connect() as connection:
        trial_row = (
            connection.execute(
                text(
                    "SELECT return_statuses, net_returns, no_trade_count "
                    "FROM evaluation_trials WHERE report_id = :report_id "
                    "AND return_statuses @> '[\"no_trade\"]'::jsonb"
                ),
                {"report_id": report.artifact_id},
            )
            .mappings()
            .one()
        )
        oos_row = (
            connection.execute(
                text(
                    "SELECT sample_id, return_status, gross_return, baseline_net_return "
                    "FROM evaluation_oos_ledger WHERE report_id = :report_id "
                    "AND return_status = 'no_trade'"
                ),
                {"report_id": report.artifact_id},
            )
            .mappings()
            .one()
        )
        cost_rows = connection.execute(
            text(
                "SELECT return_status, fill_status, requested_quantity, filled_quantity, "
                "rejected_quantity, unfilled_quantity, gross_return, fee_cost, spread_cost, "
                "impact_cost, latency_cost, borrow_cost, capacity_cost, total_cost, "
                "net_return, participation_rate, capacity_breached "
                "FROM evaluation_cost_ledger WHERE report_id = :report_id "
                "AND sample_id = :sample_id ORDER BY scenario"
            ),
            {"report_id": report.artifact_id, "sample_id": oos_row["sample_id"]},
        ).all()

    no_trade_index = trial_row["return_statuses"].index("no_trade")
    assert trial_row["net_returns"][no_trade_index] == "0"
    assert trial_row["no_trade_count"] == 1
    assert oos_row["return_status"] == "no_trade"
    assert oos_row["gross_return"] == oos_row["baseline_net_return"] == 0
    assert len(cost_rows) == 3
    assert all(row[0] == "no_trade" and row[1] == "no_trade" for row in cost_rows)
    assert all(all(value == 0 for value in row[2:16]) and row[16] is False for row in cost_rows)


def test_phase5_database_rejects_unsupported_frozen_return_policy() -> None:
    assert DATABASE_URL is not None
    _upgrade_phase5(DATABASE_URL)
    repository = EvaluationRepository(DATABASE_URL)
    policy = _unique_policy(uuid4().hex)
    mutation_applied = False

    def mutate_policy_insert(  # type: ignore[no-untyped-def]
        _connection,
        clauseelement,
        multiparams,
        params,
        _execution_options,
    ):
        nonlocal mutation_applied
        if str(clauseelement).startswith("INSERT INTO evaluation_policies"):
            mutation_applied = True
            params = dict(params)
            payload = dict(params["payload"])
            label = dict(payload["label_specification"])
            sample_adequacy = dict(payload["sample_adequacy"])
            label["missing_return_policy"] = "unsupported_missing_return_policy"
            sample_adequacy["missing_return_policy"] = "unsupported_missing_return_policy"
            payload["label_specification"] = label
            payload["sample_adequacy"] = sample_adequacy
            params["sample_adequacy_policy"] = sample_adequacy
            params["missing_return_policy"] = "unsupported_missing_return_policy"
            params["payload"] = payload
            params["canonical_json"] = canonical_json_text(payload)
            params["policy_sha256"] = domain_sha256(PHASE5_POLICY_HASH_DOMAIN, payload)
        return clauseelement, multiparams, params

    event.listen(
        repository.engine,
        "before_execute",
        mutate_policy_insert,
        retval=True,
    )
    try:
        with pytest.raises(EvaluationWorkflowConflict) as raised:
            repository.create_policy(policy)
    finally:
        event.remove(repository.engine, "before_execute", mutate_policy_insert)
        repository.dispose()

    assert mutation_applied
    assert "ck_eval_policy_return_handling" in str(raised.value.__cause__)


@pytest.mark.parametrize(
    ("table", "git_character", "expected_database_evidence"),
    [
        (
            "evaluation_trials",
            "e",
            "Phase 5 missing trial return must retain a null value",
        ),
        ("evaluation_oos_ledger", "f", "ck_eval_oos_return_handling"),
        ("evaluation_cost_ledger", "9", "ck_eval_cost_scenario"),
    ],
)
def test_phase5_database_rejects_inconsistent_return_status_artifacts(
    persisted_graph: PersistedGraph,
    table: str,
    git_character: str,
    expected_database_evidence: str,
) -> None:
    graph = persisted_graph
    report = evaluate_synthetic_fixture(
        policy=graph.policy,
        fixture=REGISTERED_FIXTURE,
        mapping=graph.snapshot.snapshot.manifest.payload.mapping,
        snapshots=(graph.snapshot, graph.membership_snapshot),
        code_version_git_sha=git_character * 40,
        created_at_utc=datetime(2026, 7, 14, 1, 0, tzinfo=UTC),
    )
    mutation_applied = False

    def mutate_child_insert(  # type: ignore[no-untyped-def]
        _connection,
        clauseelement,
        multiparams,
        params,
        _execution_options,
    ):
        nonlocal mutation_applied
        if mutation_applied or not str(clauseelement).startswith(f"INSERT INTO {table}"):
            return clauseelement, multiparams, params
        mutation_applied = True
        params = dict(params)
        payload = dict(params["payload"])
        if table == "evaluation_trials":
            return_statuses = list(payload["return_statuses"])
            return_statuses[0] = "missing"
            payload["return_statuses"] = return_statuses
            params["return_statuses"] = return_statuses
            params["missing_return_count"] = 1
            hash_column = "trial_sha256"
            hash_domain = PHASE5_TRIAL_HASH_DOMAIN
        elif table == "evaluation_oos_ledger":
            payload["return_status"] = "no_trade"
            params["return_status"] = "no_trade"
            hash_column = "oos_entry_sha256"
            hash_domain = PHASE5_LEDGER_HASH_DOMAIN
        else:
            payload["return_status"] = "no_trade"
            params["return_status"] = "no_trade"
            hash_column = "cost_entry_sha256"
            hash_domain = PHASE5_COST_HASH_DOMAIN
        params["payload"] = payload
        params["canonical_json"] = canonical_json_text(payload)
        params[hash_column] = domain_sha256(hash_domain, payload)
        return clauseelement, multiparams, params

    event.listen(
        graph.evaluations.engine,
        "before_execute",
        mutate_child_insert,
        retval=True,
    )
    try:
        with pytest.raises(EvaluationWorkflowConflict) as raised:
            graph.evaluations.create_report(report)
    finally:
        event.remove(graph.evaluations.engine, "before_execute", mutate_child_insert)

    assert mutation_applied
    assert expected_database_evidence in str(raised.value.__cause__)
    with graph.evaluations.engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT count(*) FROM evaluation_reports WHERE report_id = :report_id"),
                {"report_id": report.artifact_id},
            ).scalar_one()
            == 0
        )


@pytest.mark.parametrize(
    ("mutation", "git_character", "expected_database_evidence"),
    [
        (
            "source_payload_value",
            "7",
            "Phase 5 report columns are not bound by its frozen payload",
        ),
        (
            "oos_sample_lineage",
            "6",
            "Phase 5 OOS columns differ from hash preimage",
        ),
    ],
)
def test_phase5_database_rejects_source_and_oos_lineage_tampering_with_rollback(
    persisted_graph: PersistedGraph,
    mutation: str,
    git_character: str,
    expected_database_evidence: str,
) -> None:
    graph = persisted_graph
    report = evaluate_synthetic_fixture(
        policy=graph.policy,
        fixture=REGISTERED_FIXTURE,
        mapping=graph.snapshot.snapshot.manifest.payload.mapping,
        snapshots=(graph.snapshot, graph.membership_snapshot),
        code_version_git_sha=git_character * 40,
        created_at_utc=datetime(2026, 7, 14, 2, 0, tzinfo=UTC),
    )
    mutation_applied = False
    target_table = (
        "evaluation_reports" if mutation == "source_payload_value" else "evaluation_oos_ledger"
    )

    def mutate_lineage_insert(  # type: ignore[no-untyped-def]
        _connection,
        clauseelement,
        multiparams,
        params,
        _execution_options,
    ):
        nonlocal mutation_applied
        if mutation_applied or not str(clauseelement).startswith(f"INSERT INTO {target_table}"):
            return clauseelement, multiparams, params
        mutation_applied = True
        params = dict(params)
        if mutation == "source_payload_value":
            observations = list(params["source_observations"])
            source = dict(observations[0])
            normalized = dict(source["normalized_observation"])
            payload = dict(normalized["payload"])
            payload["open"] = "999999"
            normalized["payload"] = payload
            source["normalized_observation"] = normalized
            observations[0] = source
            params["source_observations"] = observations
        else:
            params["sample_sha256"] = "0" * 64
        return clauseelement, multiparams, params

    event.listen(
        graph.evaluations.engine,
        "before_execute",
        mutate_lineage_insert,
        retval=True,
    )
    try:
        with pytest.raises(EvaluationWorkflowConflict) as raised:
            graph.evaluations.create_report(report)
    finally:
        event.remove(graph.evaluations.engine, "before_execute", mutate_lineage_insert)

    assert mutation_applied
    assert expected_database_evidence in str(raised.value.__cause__)
    with graph.evaluations.engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT count(*) FROM evaluation_reports WHERE report_id = :report_id"),
                {"report_id": report.artifact_id},
            ).scalar_one()
            == 0
        )


@pytest.mark.parametrize(
    ("mutation", "git_character", "expected_database_evidence"),
    [
        (
            "source_payload_value",
            "5",
            "Phase 5 source observation differs from immutable Phase 4 evidence",
        ),
        (
            "oos_sample_lineage",
            "4",
            "Phase 5 OOS row differs from frozen sample lineage",
        ),
    ],
)
def test_phase5_deferred_semantic_lineage_rejects_internally_rehashed_tampering(
    persisted_graph: PersistedGraph,
    mutation: str,
    git_character: str,
    expected_database_evidence: str,
) -> None:
    graph = persisted_graph
    report = evaluate_synthetic_fixture(
        policy=graph.policy,
        fixture=REGISTERED_FIXTURE,
        mapping=graph.snapshot.snapshot.manifest.payload.mapping,
        snapshots=(graph.snapshot, graph.membership_snapshot),
        code_version_git_sha=git_character * 40,
        created_at_utc=datetime(2026, 7, 14, 3, 0, tzinfo=UTC),
    )
    mutated_report_sha: str | None = None
    mutated_oos_sha: str | None = None

    def rehash_semantic_tamper(  # type: ignore[no-untyped-def]
        _connection,
        clauseelement,
        multiparams,
        params,
        _execution_options,
    ):
        nonlocal mutated_oos_sha, mutated_report_sha
        statement = str(clauseelement)
        params = dict(params)
        if statement.startswith("INSERT INTO evaluation_reports"):
            payload = dict(params["payload"])
            if mutation == "source_payload_value":
                observations = list(payload["source_observations"])
                source = dict(observations[0])
                normalized = dict(source["normalized_observation"])
                source_payload = dict(normalized["payload"])
                source_payload["open"] = "999999"
                normalized["payload"] = source_payload
                source["normalized_observation"] = normalized
                observations[0] = source
                payload["source_observations"] = observations
                params["source_observations"] = observations
            else:
                oos_rows = list(payload["oos_ledger"])
                first_oos = dict(oos_rows[0])
                first_oos["sample_sha256"] = "0" * 64
                oos_hash_payload = {
                    key: value
                    for key, value in first_oos.items()
                    if key not in {"ledger_entry_id", "ledger_entry_sha256"}
                }
                mutated_oos_sha = domain_sha256(
                    PHASE5_LEDGER_HASH_DOMAIN,
                    oos_hash_payload,
                )
                first_oos["ledger_entry_sha256"] = mutated_oos_sha
                oos_rows[0] = first_oos
                payload["oos_ledger"] = oos_rows
            mutated_report_sha = domain_sha256(PHASE5_ARTIFACT_HASH_DOMAIN, payload)
            params["report_sha256"] = mutated_report_sha
            params["canonical_json"] = canonical_json_text(payload)
            params["payload"] = payload
        elif mutated_report_sha is not None and "report_sha256" in params:
            params["report_sha256"] = mutated_report_sha
            if (
                mutation == "oos_sample_lineage"
                and statement.startswith("INSERT INTO evaluation_oos_ledger")
                and params["ordinal"] == 0
            ):
                oos_payload = dict(params["payload"])
                oos_payload["sample_sha256"] = "0" * 64
                params["sample_sha256"] = "0" * 64
                params["oos_entry_sha256"] = mutated_oos_sha
                params["canonical_json"] = canonical_json_text(oos_payload)
                params["payload"] = oos_payload
        return clauseelement, multiparams, params

    event.listen(
        graph.evaluations.engine,
        "before_execute",
        rehash_semantic_tamper,
        retval=True,
    )
    try:
        with pytest.raises(DBAPIError, match=expected_database_evidence):
            with graph.evaluations.engine.begin() as connection:
                EvaluationRepository._insert_report(connection, report)
    finally:
        event.remove(graph.evaluations.engine, "before_execute", rehash_semantic_tamper)

    assert mutated_report_sha is not None
    if mutation == "oos_sample_lineage":
        assert mutated_oos_sha is not None
    with graph.evaluations.engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT count(*) FROM evaluation_reports WHERE report_id = :report_id"),
                {"report_id": report.artifact_id},
            ).scalar_one()
            == 0
        )


@pytest.mark.parametrize(
    ("mutation", "git_character"),
    (
        ("required_capability_set", "3"),
        ("membership_role", "2"),
    ),
)
def test_phase5_deferred_lineage_rejects_rehashed_source_semantic_forgery(
    persisted_graph: PersistedGraph,
    mutation: str,
    git_character: str,
) -> None:
    graph = persisted_graph
    report = evaluate_synthetic_fixture(
        policy=graph.policy,
        fixture=REGISTERED_FIXTURE,
        mapping=graph.snapshot.snapshot.manifest.payload.mapping,
        snapshots=(graph.snapshot, graph.membership_snapshot),
        code_version_git_sha=git_character * 40,
        created_at_utc=datetime(2026, 7, 14, 4, 0, tzinfo=UTC),
    )
    mutated_report_sha: str | None = None

    def rehash_lineage_tamper(  # type: ignore[no-untyped-def]
        _connection,
        clauseelement,
        multiparams,
        params,
        _execution_options,
    ):
        nonlocal mutated_report_sha
        statement = str(clauseelement)
        params = dict(params)
        if statement.startswith("INSERT INTO evaluation_reports"):
            payload = dict(params["payload"])
            lineages = list(payload["sample_lineage"])
            first = dict(lineages[0])
            if mutation == "required_capability_set":
                first["source_observation_refs"] = [
                    ref
                    for ref in first["source_observation_refs"]
                    if ref["capability"] != DataCapability.UNIVERSE_MEMBERSHIP.value
                ]
            elif mutation == "membership_role":
                first["membership_source_observation_key"] = dict(
                    first["feature_derivation"]["source_observation_key"]
                )
            lineages[0] = first
            lineage_hash = domain_sha256(PHASE5_SAMPLE_LINEAGE_HASH_DOMAIN, lineages)
            payload["sample_lineage"] = lineages
            payload["sample_lineage_sha256"] = lineage_hash
            mutated_report_sha = domain_sha256(PHASE5_ARTIFACT_HASH_DOMAIN, payload)
            params["sample_lineage"] = lineages
            params["sample_lineage_canonical_json"] = canonical_json_text(lineages)
            params["sample_lineage_sha256"] = lineage_hash
            params["report_sha256"] = mutated_report_sha
            params["canonical_json"] = canonical_json_text(payload)
            params["payload"] = payload
        elif mutated_report_sha is not None and "report_sha256" in params:
            params["report_sha256"] = mutated_report_sha
        return clauseelement, multiparams, params

    event.listen(
        graph.evaluations.engine,
        "before_execute",
        rehash_lineage_tamper,
        retval=True,
    )
    try:
        with pytest.raises(
            DBAPIError,
            match="sample lineage contains unknown, unused, or invalid source evidence",
        ):
            with graph.evaluations.engine.begin() as connection:
                EvaluationRepository._insert_report(connection, report)
    finally:
        event.remove(
            graph.evaluations.engine,
            "before_execute",
            rehash_lineage_tamper,
        )

    assert mutated_report_sha is not None
    with graph.evaluations.engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT count(*) FROM evaluation_reports WHERE report_id = :report_id"),
                {"report_id": report.artifact_id},
            ).scalar_one()
            == 0
        )


def test_phase5_deferred_lineage_rejects_fully_rehashed_source_availability_forgery(
    persisted_graph: PersistedGraph,
) -> None:
    graph = persisted_graph
    report = evaluate_synthetic_fixture(
        policy=graph.policy,
        fixture=REGISTERED_FIXTURE,
        mapping=graph.snapshot.snapshot.manifest.payload.mapping,
        snapshots=(graph.snapshot, graph.membership_snapshot),
        code_version_git_sha="1" * 40,
        created_at_utc=datetime(2026, 7, 14, 4, 15, tzinfo=UTC),
    )
    mutated_report_sha: str | None = None
    mutated_sample_sha: str | None = None
    forged_feature_available_at: datetime | None = None
    source_available_at: datetime | None = None
    mutated_fits: dict[str, PreprocessingFitRecord] = {}
    mutated_oos_rows: dict[str, dict[str, object]] = {}
    updated_fit_children: set[str] = set()
    updated_oos_children: set[str] = set()

    def rehash_source_availability_tamper(  # type: ignore[no-untyped-def]
        _connection,
        clauseelement,
        multiparams,
        params,
        _execution_options,
    ):
        nonlocal forged_feature_available_at, mutated_report_sha, mutated_sample_sha
        nonlocal source_available_at
        statement = str(clauseelement)
        params = dict(params)
        if statement.startswith("INSERT INTO evaluation_reports"):
            payload = dict(params["payload"])
            lineages = list(payload["sample_lineage"])
            target_lineage = dict(lineages[0])
            target_sample_id = target_lineage["sample_id"]
            ohlcv_source = next(
                source
                for source in payload["source_observations"]
                if source["key"]["capability"] == DataCapability.OHLCV.value
            )
            source_available_at = datetime.fromisoformat(
                ohlcv_source["normalized_observation"]["available_at"].replace("Z", "+00:00")
            )
            forged_feature_available_at = source_available_at - timedelta(microseconds=1)
            original_sample = next(
                sample
                for sample in REGISTERED_FIXTURE.samples
                if sample.sample_id == target_sample_id
            )
            mutated_sample = original_sample.model_copy(
                update={"feature_available_at_utc": forged_feature_available_at}
            )
            mutated_sample_sha = domain_sha256(PHASE5_SAMPLE_HASH_DOMAIN, mutated_sample)
            target_lineage["feature_available_at_utc"] = canonicalize(forged_feature_available_at)
            target_lineage["sample_sha256"] = mutated_sample_sha
            lineages[0] = target_lineage
            lineage_hash = domain_sha256(PHASE5_SAMPLE_LINEAGE_HASH_DOMAIN, lineages)
            payload["sample_lineage"] = lineages
            payload["sample_lineage_sha256"] = lineage_hash

            fit_payloads = list(payload["preprocessing_fits"])
            for index, original_fit in enumerate(report.preprocessing_fits):
                if target_sample_id not in original_fit.train_sample_ids:
                    continue
                mutated_fit = PreprocessingFitRecord.derive(
                    fold_id=original_fit.fold_id,
                    fold_sha256=original_fit.fold_sha256,
                    train_sample_values=tuple(
                        PreprocessingFitSampleValue(
                            sample_id=value.sample_id,
                            sample_sha256=(
                                mutated_sample_sha
                                if value.sample_id == target_sample_id
                                else value.sample_sha256
                            ),
                            value=value.value,
                        )
                        for value in original_fit.train_sample_values
                    ),
                )
                mutated_fits[str(original_fit.fit_id)] = mutated_fit
                fit_payloads[index] = canonicalize(mutated_fit)
            payload["preprocessing_fits"] = fit_payloads

            oos_rows = list(payload["oos_ledger"])
            for index, original_oos in enumerate(report.oos_ledger):
                if original_oos.sample_id != target_sample_id:
                    continue
                mutated_oos = dict(oos_rows[index])
                old_oos_id = str(original_oos.ledger_entry_id)
                mutated_oos["sample_sha256"] = mutated_sample_sha
                oos_hash_payload = {
                    key: value
                    for key, value in mutated_oos.items()
                    if key not in {"ledger_entry_id", "ledger_entry_sha256"}
                }
                oos_sha = domain_sha256(PHASE5_LEDGER_HASH_DOMAIN, oos_hash_payload)
                mutated_oos["ledger_entry_id"] = str(identity(PHASE5_LEDGER_NAMESPACE, oos_sha))
                mutated_oos["ledger_entry_sha256"] = oos_sha
                mutated_oos_rows[old_oos_id] = mutated_oos
                oos_rows[index] = mutated_oos
            payload["oos_ledger"] = oos_rows

            mutated_report_sha = domain_sha256(PHASE5_ARTIFACT_HASH_DOMAIN, payload)
            params["sample_lineage"] = lineages
            params["sample_lineage_canonical_json"] = canonical_json_text(lineages)
            params["sample_lineage_sha256"] = lineage_hash
            params["report_sha256"] = mutated_report_sha
            params["canonical_json"] = canonical_json_text(payload)
            params["payload"] = payload
        elif mutated_report_sha is not None and "report_sha256" in params:
            params["report_sha256"] = mutated_report_sha
            if statement.startswith("INSERT INTO evaluation_preprocessing_fits"):
                old_fit_id = str(params["fit_id"])
                mutated_fit = mutated_fits.get(old_fit_id)
                if mutated_fit is not None:
                    fit_statistics = {
                        "fit_sha256": mutated_fit.fit_sha256,
                        "mean": mutated_fit.mean,
                        "standard_deviation": mutated_fit.standard_deviation,
                        "ddof": mutated_fit.ddof,
                    }
                    params.update(
                        {
                            "fit_id": mutated_fit.fit_id,
                            "fit_sha256": mutated_fit.fit_sha256,
                            "statistics_sha256": mutated_fit.statistics_sha256,
                            "train_sample_ids": list(mutated_fit.train_sample_ids),
                            "train_sample_ids_sha256": mutated_fit.train_sample_ids_sha256,
                            "record_payload": canonicalize(mutated_fit),
                            "canonical_json": canonical_json_text(fit_statistics),
                            "payload": canonicalize(fit_statistics),
                        }
                    )
                    updated_fit_children.add(old_fit_id)
            elif statement.startswith("INSERT INTO evaluation_oos_ledger"):
                old_oos_id = str(params["oos_entry_id"])
                mutated_oos = mutated_oos_rows.get(old_oos_id)
                if mutated_oos is not None:
                    oos_payload = {
                        key: value
                        for key, value in mutated_oos.items()
                        if key not in {"ledger_entry_id", "ledger_entry_sha256"}
                    }
                    params.update(
                        {
                            "oos_entry_id": UUID(str(mutated_oos["ledger_entry_id"])),
                            "oos_entry_sha256": mutated_oos["ledger_entry_sha256"],
                            "sample_sha256": mutated_oos["sample_sha256"],
                            "canonical_json": canonical_json_text(oos_payload),
                            "payload": oos_payload,
                        }
                    )
                    updated_oos_children.add(old_oos_id)
        return clauseelement, multiparams, params

    event.listen(
        graph.evaluations.engine,
        "before_execute",
        rehash_source_availability_tamper,
        retval=True,
    )
    try:
        with pytest.raises(
            DBAPIError,
            match="sample lineage contains unknown, unused, or invalid source evidence",
        ):
            with graph.evaluations.engine.begin() as connection:
                EvaluationRepository._insert_report(connection, report)
    finally:
        event.remove(
            graph.evaluations.engine,
            "before_execute",
            rehash_source_availability_tamper,
        )

    assert mutated_report_sha is not None
    assert mutated_sample_sha is not None
    assert source_available_at is not None
    assert forged_feature_available_at == source_available_at - timedelta(microseconds=1)
    assert updated_fit_children == set(mutated_fits)
    assert updated_oos_children == set(mutated_oos_rows)
    with graph.evaluations.engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT count(*) FROM evaluation_reports WHERE report_id = :report_id"),
                {"report_id": report.artifact_id},
            ).scalar_one()
            == 0
        )


@pytest.mark.parametrize(
    ("mutation", "git_character", "expected_database_evidence"),
    (
        (
            "test_partition_in_fit",
            "1",
            "preprocessing fit does not exactly match its frozen train fold",
        ),
        (
            "mean_with_all_hashes_recomputed",
            "0",
            "preprocessing statistics are not derived from exact train values",
        ),
    ),
)
def test_phase5_preprocessing_rejects_internally_rehashed_semantic_tamper(
    persisted_graph: PersistedGraph,
    mutation: str,
    git_character: str,
    expected_database_evidence: str,
) -> None:
    graph = persisted_graph
    report = evaluate_synthetic_fixture(
        policy=graph.policy,
        fixture=REGISTERED_FIXTURE,
        mapping=graph.snapshot.snapshot.manifest.payload.mapping,
        snapshots=(graph.snapshot, graph.membership_snapshot),
        code_version_git_sha=git_character * 40,
        created_at_utc=datetime(2026, 7, 14, 5, 0, tzinfo=UTC),
    )
    original = report.preprocessing_fits[0]
    if mutation == "test_partition_in_fit":
        fold = next(item for item in report.folds if item.fold_id == original.fold_id)
        test_lineage = next(
            item for item in report.sample_lineage if item.sample_id == fold.test_sample_ids[0]
        )
        tampered_model = PreprocessingFitRecord.derive(
            fold_id=fold.fold_id,
            fold_sha256=fold.fold_sha256,
            train_sample_values=tuple(
                sorted(
                    (
                        *original.train_sample_values,
                        PreprocessingFitSampleValue(
                            sample_id=test_lineage.sample_id,
                            sample_sha256=test_lineage.sample_sha256,
                            value=test_lineage.feature_derivation.derived_feature_value,
                        ),
                    ),
                    key=lambda item: item.sample_id,
                )
            ),
        )
        tampered = tampered_model.model_dump(mode="python")
    else:
        tampered = original.model_dump(mode="python")
        tampered["mean"] = original.mean + Decimal("0.01")
        fit_preimage = {
            key: value
            for key, value in tampered.items()
            if key
            not in {
                "fit_id",
                "fit_sha256",
                "train_sample_ids_canonical_json",
                "fit_preimage_canonical_json",
                "statistics_sha256",
            }
        }
        tampered["fit_preimage_canonical_json"] = canonical_json_text(fit_preimage)
        tampered["fit_sha256"] = domain_sha256(
            PHASE5_TRAIN_ONLY_FIT_HASH_DOMAIN,
            fit_preimage,
        )
        tampered["fit_id"] = identity(PHASE5_FIT_NAMESPACE, tampered["fit_sha256"])
        tampered["statistics_sha256"] = domain_sha256(
            PHASE5_FIT_HASH_DOMAIN,
            {
                "fit_sha256": tampered["fit_sha256"],
                "mean": tampered["mean"],
                "standard_deviation": tampered["standard_deviation"],
                "ddof": tampered["ddof"],
            },
        )

    statistics_payload = {
        "fit_sha256": tampered["fit_sha256"],
        "mean": tampered["mean"],
        "standard_deviation": tampered["standard_deviation"],
        "ddof": tampered["ddof"],
    }
    mutated_report_sha: str | None = None

    def rehash_fit_tamper(  # type: ignore[no-untyped-def]
        _connection,
        clauseelement,
        multiparams,
        params,
        _execution_options,
    ):
        nonlocal mutated_report_sha
        statement = str(clauseelement)
        params = dict(params)
        if statement.startswith("INSERT INTO evaluation_reports"):
            payload = dict(params["payload"])
            fits = list(payload["preprocessing_fits"])
            fits[0] = canonicalize(tampered)
            payload["preprocessing_fits"] = fits
            mutated_report_sha = domain_sha256(PHASE5_ARTIFACT_HASH_DOMAIN, payload)
            params["report_sha256"] = mutated_report_sha
            params["canonical_json"] = canonical_json_text(payload)
            params["payload"] = payload
        elif mutated_report_sha is not None and "report_sha256" in params:
            params["report_sha256"] = mutated_report_sha
            if (
                statement.startswith("INSERT INTO evaluation_preprocessing_fits")
                and params["ordinal"] == 0
            ):
                params.update(
                    {
                        "fit_id": tampered["fit_id"],
                        "fit_sha256": tampered["fit_sha256"],
                        "statistics_sha256": tampered["statistics_sha256"],
                        "fold_id": tampered["fold_id"],
                        "transformer_id": tampered["transformer_id"],
                        "transformer_version": tampered["transformer_version"],
                        "training_row_count": len(tampered["train_sample_ids"]),
                        "train_sample_ids": list(tampered["train_sample_ids"]),
                        "train_sample_ids_sha256": tampered["train_sample_ids_sha256"],
                        "mean": tampered["mean"],
                        "standard_deviation": tampered["standard_deviation"],
                        "ddof": tampered["ddof"],
                        "record_payload": canonicalize(tampered),
                        "canonical_json": canonical_json_text(statistics_payload),
                        "payload": canonicalize(statistics_payload),
                    }
                )
        return clauseelement, multiparams, params

    event.listen(
        graph.evaluations.engine,
        "before_execute",
        rehash_fit_tamper,
        retval=True,
    )
    try:
        with pytest.raises(DBAPIError, match=expected_database_evidence):
            with graph.evaluations.engine.begin() as connection:
                EvaluationRepository._insert_report(connection, report)
    finally:
        event.remove(
            graph.evaluations.engine,
            "before_execute",
            rehash_fit_tamper,
        )

    assert mutated_report_sha is not None
    with graph.evaluations.engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT count(*) FROM evaluation_reports WHERE report_id = :report_id"),
                {"report_id": report.artifact_id},
            ).scalar_one()
            == 0
        )


def test_phase5_concurrent_policy_and_run_creation_use_distinct_connections_idempotently() -> None:
    assert DATABASE_URL is not None
    _upgrade_phase5(DATABASE_URL)
    ideas = IdeaRepository(DATABASE_URL)
    mappings = MappingRepository(DATABASE_URL)
    seed_snapshots = SnapshotRepository(DATABASE_URL)
    unique = uuid4().hex
    repositories = (EvaluationRepository(DATABASE_URL), EvaluationRepository(DATABASE_URL))
    snapshot_repositories = (SnapshotRepository(DATABASE_URL), SnapshotRepository(DATABASE_URL))
    try:
        mapping = _create_family_a_mapping(
            ideas,
            mappings,
            key=f"phase5-postgres-concurrent-{unique}",
        )
        snapshot = _create_snapshot(
            seed_snapshots,
            mapping.mapping.mapping_id,
            DataCapability.OHLCV,
        )
        membership_snapshot = _create_snapshot(
            seed_snapshots,
            mapping.mapping.mapping_id,
            DataCapability.UNIVERSE_MEMBERSHIP,
        )
        policy = _unique_policy(unique)
        workflows = tuple(
            _workflow(repositories[index], snapshot_repositories[index], policy)
            for index in range(2)
        )
        policy_request = EvaluationPolicyCreateRequest(
            policy_id=policy.policy_id,
            policy_version=policy.policy_version,
        )
        report_request = EvaluationRunCreateRequest(
            policy_id=policy.policy_id,
            policy_version=policy.policy_version,
            mapping_id=mapping.mapping.mapping_id,
            snapshot_ids=(
                snapshot.snapshot.snapshot_id,
                membership_snapshot.snapshot.snapshot_id,
            ),
            fixture_id=REGISTERED_FIXTURE.fixture_id,
        )
        policy_barrier = Barrier(2)
        report_barrier = Barrier(2)

        def worker(index: int) -> tuple[int, int, FrozenEvaluationPolicy, EvaluationReport]:
            with repositories[index].engine.connect() as connection:
                backend_pid = connection.execute(text("SELECT pg_backend_pid() ")).scalar_one()
            policy_barrier.wait(timeout=15)
            stored_policy = workflows[index].create_policy(policy_request)
            report_barrier.wait(timeout=15)
            stored_report = workflows[index].create_report(report_request)
            return get_ident(), backend_pid, stored_policy, stored_report

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(worker, index) for index in range(2)]
            results = [future.result(timeout=60) for future in futures]

        assert len({thread_id for thread_id, _, _, _ in results}) == 2
        assert len({backend_pid for _, backend_pid, _, _ in results}) == 2
        assert {stored_policy for _, _, stored_policy, _ in results} == {policy}
        reports = tuple(stored_report for _, _, _, stored_report in results)
        assert reports[0] == reports[1]
        assert _graph_counts(repositories[0].engine, policy, reports[0]) == {
            "evaluation_policies": 1,
            "evaluation_feature_specs": 1,
            "evaluation_label_specs": 1,
            "evaluation_blocked_outcomes": 0,
            "evaluation_reports": 1,
            "evaluation_report_snapshots": len(reports[0].data_snapshots),
            "evaluation_trials": len(reports[0].trials),
            "evaluation_folds": len(reports[0].folds),
            "evaluation_preprocessing_fits": len(reports[0].preprocessing_fits),
            "evaluation_oos_ledger": len(reports[0].oos_ledger),
            "evaluation_cost_ledger": len(reports[0].cost_ledger),
            "evaluation_gate_results": len(reports[0].gates),
        }
        with repositories[0].engine.connect() as connection:
            assert (
                connection.execute(
                    text(
                        "SELECT count(*) FROM evaluation_reports "
                        "WHERE run_fingerprint_sha256 = :fingerprint"
                    ),
                    {"fingerprint": reports[0].request_fingerprint_sha256},
                ).scalar_one()
                == 1
            )
    finally:
        for snapshot_repository in snapshot_repositories:
            snapshot_repository.dispose()
        for evaluation_repository in repositories:
            evaluation_repository.dispose()
        seed_snapshots.dispose()
        mappings.dispose()
        ideas.dispose()


def test_phase5_concurrent_blocked_creation_persists_one_full_audit_artifact() -> None:
    assert DATABASE_URL is not None
    _upgrade_phase5(DATABASE_URL)
    repositories = (EvaluationRepository(DATABASE_URL), EvaluationRepository(DATABASE_URL))
    snapshot_repositories = (SnapshotRepository(DATABASE_URL), SnapshotRepository(DATABASE_URL))
    policy = _unique_policy(uuid4().hex)
    timestamps = (
        datetime(2026, 7, 14, 1, 0, tzinfo=UTC),
        datetime(2026, 7, 14, 1, 0, 1, tzinfo=UTC),
    )
    workflows = tuple(
        _workflow(
            repositories[index],
            snapshot_repositories[index],
            policy,
            code_version_git_sha=None,
            outcome_clock=lambda value=timestamps[index]: value,  # type: ignore[misc]
        )
        for index in range(2)
    )
    request = EvaluationRunCreateRequest(
        policy_id=policy.policy_id,
        policy_version=policy.policy_version,
        mapping_id=uuid4(),
        snapshot_ids=(uuid4(),),
        fixture_id=REGISTERED_FIXTURE.fixture_id,
    )
    barrier = Barrier(2)

    def worker(index: int) -> tuple[int, int, BlockedEvaluationOutcome]:
        with repositories[index].engine.connect() as connection:
            backend_pid = connection.execute(text("SELECT pg_backend_pid() ")).scalar_one()
        barrier.wait(timeout=15)
        try:
            workflows[index].create_report(request)
        except EvaluationWorkflowBlocked as exc:
            assert exc.outcome is not None
            return get_ident(), backend_pid, exc.outcome
        raise AssertionError("missing code SHA must fail closed")

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(worker, index) for index in range(2)]
            results = [future.result(timeout=30) for future in futures]

        assert len({thread_id for thread_id, _, _ in results}) == 2
        assert len({backend_pid for _, backend_pid, _ in results}) == 2
        outcomes = tuple(outcome for _, _, outcome in results)
        assert outcomes[0] == outcomes[1]
        assert outcomes[0].created_at_utc in timestamps
        assert repositories[0].get_outcome(outcomes[0].outcome_id) == outcomes[0]
        assert outcomes[0] in repositories[0].list_outcomes(limit=100)
        with repositories[0].engine.connect() as connection:
            assert (
                connection.execute(
                    text(
                        "SELECT count(*) FROM evaluation_blocked_outcomes "
                        "WHERE idempotency_sha256 = :idempotency_sha256"
                    ),
                    {"idempotency_sha256": outcomes[0].idempotency_sha256},
                ).scalar_one()
                == 1
            )
        outcome_columns = tuple(
            column["name"]
            for column in inspect(repositories[0].engine).get_columns("evaluation_blocked_outcomes")
        )
        tampered_select = ", ".join(
            (
                ":new_outcome_id"
                if column == "outcome_id"
                else (
                    ":bad_idempotency_sha256" if column == "idempotency_sha256" else f'"{column}"'
                )
            )
            for column in outcome_columns
        )
        quoted_columns = ", ".join(f'"{column}"' for column in outcome_columns)
        with repositories[0].engine.connect() as connection:
            with pytest.raises(DBAPIError, match="blocked idempotency hash mismatch"):
                connection.execute(
                    text(
                        "INSERT INTO evaluation_blocked_outcomes "
                        f"({quoted_columns}) SELECT {tampered_select} "
                        "FROM evaluation_blocked_outcomes WHERE outcome_id = :source_outcome_id"
                    ),
                    {
                        "new_outcome_id": uuid4(),
                        "bad_idempotency_sha256": "0" * 64,
                        "source_outcome_id": outcomes[0].outcome_id,
                    },
                )
            connection.rollback()
    finally:
        for snapshot_repository in snapshot_repositories:
            snapshot_repository.dispose()
        for evaluation_repository in repositories:
            evaluation_repository.dispose()


def test_phase5_hash_and_lineage_tamper_fail_and_partial_child_write_rolls_back(
    persisted_graph: PersistedGraph,
) -> None:
    graph = persisted_graph
    unpersisted_policy = _unique_policy(uuid4().hex)
    bad_policy = unpersisted_policy.model_copy(update={"policy_sha256": "0" * 64})
    with pytest.raises(EvaluationWorkflowConflict, match="hash does not match payload"):
        graph.evaluations.create_policy(bad_policy)
    with graph.evaluations.engine.connect() as connection:
        assert (
            connection.execute(
                text(
                    "SELECT count(*) FROM evaluation_policies "
                    "WHERE policy_id = :policy_id AND policy_version = :policy_version"
                ),
                {
                    "policy_id": unpersisted_policy.policy_id,
                    "policy_version": unpersisted_policy.policy_version,
                },
            ).scalar_one()
            == 0
        )

    with graph.evaluations.engine.connect() as connection:
        with pytest.raises(DBAPIError, match="child report lineage mismatch"):
            connection.execute(
                text(
                    "INSERT INTO evaluation_trials "
                    "(trial_id, trial_sha256, report_id, report_sha256, ordinal, trial_key, "
                    "status, config_sha256, configuration, failure_reason, canonical_json, "
                    "payload) "
                    "VALUES (:trial_id, :trial_sha256, :report_id, :report_sha256, 999, "
                    "'lineage-tamper', 'completed', :config_sha256, '{}'::jsonb, NULL, "
                    "'{}', '{}'::jsonb)"
                ),
                {
                    "trial_id": uuid4(),
                    "trial_sha256": "1" * 64,
                    "report_id": graph.report.artifact_id,
                    "report_sha256": "2" * 64,
                    "config_sha256": "3" * 64,
                },
            )
        connection.rollback()

    alternate_git_sha = "b" * 40 if CODE_VERSION_GIT_SHA != "b" * 40 else "c" * 40
    rollback_report = evaluate_synthetic_fixture(
        policy=graph.policy,
        fixture=REGISTERED_FIXTURE,
        mapping=graph.snapshot.snapshot.manifest.payload.mapping,
        snapshots=(graph.snapshot, graph.membership_snapshot),
        code_version_git_sha=alternate_git_sha,
        created_at_utc=datetime(2026, 7, 13, tzinfo=UTC),
    )

    def fail_before_trial_insert(
        _connection: object,
        _cursor: object,
        statement: str,
        _parameters: object,
        _context: object,
        _executemany: bool,
    ) -> None:
        if statement.startswith("INSERT INTO evaluation_trials"):
            raise RuntimeError("injected Phase 5 partial-child persistence failure")

    event.listen(graph.evaluations.engine, "before_cursor_execute", fail_before_trial_insert)
    try:
        with pytest.raises(RuntimeError, match="partial-child persistence failure"):
            graph.evaluations.create_report(rollback_report)
    finally:
        event.remove(
            graph.evaluations.engine,
            "before_cursor_execute",
            fail_before_trial_insert,
        )

    with graph.evaluations.engine.connect() as connection:
        for table in REPORT_TABLES:
            assert (
                connection.execute(
                    text(f"SELECT count(*) FROM {table} WHERE report_id = :report_id"),
                    {"report_id": rollback_report.artifact_id},
                ).scalar_one()
                == 0
            )


def test_phase5_all_twelve_tables_reject_update_delete_and_truncate(
    persisted_graph: PersistedGraph,
) -> None:
    graph = persisted_graph
    blocked_workflow = _workflow(
        graph.evaluations,
        graph.snapshots,
        graph.policy,
        code_version_git_sha=None,
        outcome_clock=lambda: datetime(2026, 7, 14, 2, 0, tzinfo=UTC),
    )
    with pytest.raises(EvaluationWorkflowBlocked) as raised:
        blocked_workflow.create_report(
            EvaluationRunCreateRequest(
                policy_id=graph.policy.policy_id,
                policy_version=graph.policy.policy_version,
                mapping_id=graph.mapping.mapping.mapping_id,
                snapshot_ids=(
                    graph.snapshot.snapshot.snapshot_id,
                    graph.membership_snapshot.snapshot.snapshot_id,
                ),
                fixture_id=REGISTERED_FIXTURE.fixture_id,
            )
        )
    outcome = raised.value.outcome
    assert outcome is not None

    for table in PHASE5_TABLES:
        if table in POLICY_TABLES:
            where = "policy_id = :policy_id AND policy_version = :policy_version"
            parameters = {
                "policy_id": graph.policy.policy_id,
                "policy_version": graph.policy.policy_version,
            }
        elif table in OUTCOME_TABLES:
            where = "outcome_id = :outcome_id"
            parameters = {"outcome_id": outcome.outcome_id}
        else:
            where = "report_id = :report_id"
            parameters = {"report_id": graph.report.artifact_id}
        for statement in (
            f"UPDATE {table} SET created_at_utc = created_at_utc WHERE {where}",
            f"DELETE FROM {table} WHERE {where}",
            f"TRUNCATE {table} CASCADE",
        ):
            with graph.evaluations.engine.connect() as connection:
                with pytest.raises(DBAPIError, match="append-only"):
                    connection.execute(text(statement), parameters)
                connection.rollback()
