from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest
from fable5_backtester.canonical import domain_sha256
from fable5_backtester.contracts import (
    PHASE6_REPORT_SCOPE_SOURCE_EVIDENCE_HASH_DOMAIN,
    ReportScopeSourceEvidence,
    ReportScopeSourceRole,
    SourceObservationKey,
    SyntheticEvaluationFixture,
    SyntheticSourceObservationExpectation,
)
from fable5_backtester.source_lineage import (
    SourceLineageInputError,
    resolve_source_lineage,
)
from fable5_backtester.synthetic import REGISTERED_FIXTURE, REGISTERED_POLICY
from fable5_data.contracts import (
    AuthorizedMappingIdentity,
    DataCapability,
    NormalizedObservationDraft,
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
)
from fable5_mapping.models import CanonicalFamily, ResearchVerdict

MAPPING = AuthorizedMappingIdentity(
    mapping_id=UUID("aaaaaaaa-aaaa-5aaa-8aaa-aaaaaaaaaaaa"),
    mapping_version=1,
    mapping_input_sha256="1" * 64,
    mapper_rule_set_version="phase3-test-rules-v1",
    mapper_rule_set_sha256="2" * 64,
    canonical_family=CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING,
    verdict=ResearchVerdict.BUILD_RESEARCH,
)
AS_OF = datetime(2026, 7, 12, tzinfo=UTC)
CREATED_AT = datetime(2026, 7, 13, 20, 30, tzinfo=UTC)
PIPELINE_SHA256 = "9" * 64


def _snapshot(capability: DataCapability) -> SnapshotBundle:
    adapter = SyntheticPointInTimeAdapter.for_mapping(MAPPING)
    request = SnapshotRequestParameters(
        mapping=MAPPING,
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
        mapping=MAPPING,
        request=request,
        profile=adapter_result.profile,
        configuration=SYNTHETIC_MOCK_CONFIGURATION,
        batch=quality.batch,
        created_at_utc=CREATED_AT,
    )
    assert isinstance(candidate, SnapshotCandidate)
    return candidate.bundle


@pytest.fixture(scope="module")
def snapshots() -> tuple[SnapshotBundle, ...]:
    return tuple(
        _snapshot(capability) for capability in REGISTERED_POLICY.required_snapshot_capabilities
    )


def _future_membership_expectation(
    snapshots: tuple[SnapshotBundle, ...],
) -> SyntheticSourceObservationExpectation:
    membership_snapshot = next(
        item
        for item in snapshots
        if item.snapshot.manifest.payload.request.capability is DataCapability.UNIVERSE_MEMBERSHIP
    )
    sample_key_ids = {
        key.normalized_observation_id
        for sample in REGISTERED_FIXTURE.samples
        for key in sample.source_observation_keys
    }
    observation = next(
        item
        for item in membership_snapshot.normalized_observations
        if item.normalized_observation_id not in sample_key_ids
    )
    constituent = next(
        item
        for item in membership_snapshot.constituents
        if item.normalized_observation_id == observation.normalized_observation_id
    )
    draft = NormalizedObservationDraft.model_validate(
        observation.model_dump(
            mode="python",
            exclude={"snapshot_id", "snapshot_sha256"},
        )
    )
    return SyntheticSourceObservationExpectation(
        key=SourceObservationKey(
            capability=DataCapability.UNIVERSE_MEMBERSHIP,
            normalized_observation_id=observation.normalized_observation_id,
        ),
        normalized_observation=draft,
        required_disposition=constituent.disposition,
    )


def _scope_evidence(
    *keys: SourceObservationKey,
    role: ReportScopeSourceRole = ReportScopeSourceRole.LIFECYCLE_TEST,
    pipeline_sha256: str = PIPELINE_SHA256,
) -> ReportScopeSourceEvidence:
    content = {
        "schema_version": "phase6-report-scope-source-evidence-v1",
        "role": role,
        "prepared_pipeline_input_sha256": pipeline_sha256,
        "source_observation_keys": keys,
    }
    return ReportScopeSourceEvidence.model_validate(
        {
            **content,
            "evidence_sha256": domain_sha256(
                PHASE6_REPORT_SCOPE_SOURCE_EVIDENCE_HASH_DOMAIN,
                content,
            ),
        }
    )


def _fixture_with_scope(
    expectation: SyntheticSourceObservationExpectation,
    evidence: tuple[ReportScopeSourceEvidence, ...],
    *,
    add_confirmation_sample: bool = True,
) -> SyntheticEvaluationFixture:
    expectations = tuple(
        sorted(
            (*REGISTERED_FIXTURE.source_observation_expectations, expectation),
            key=lambda item: (
                str(item.key.capability),
                str(item.key.normalized_observation_id),
            ),
        )
    )
    samples = REGISTERED_FIXTURE.samples
    if add_confirmation_sample:
        confirmation_time = datetime(2020, 2, 11, 16, tzinfo=UTC)
        confirmation_sample = samples[-1].model_copy(
            update={
                "decision_time_utc": confirmation_time,
                "feature_available_at_utc": datetime(2020, 2, 11, 15, tzinfo=UTC),
                "label_t0_utc": confirmation_time,
                "label_t1_utc": datetime(2020, 2, 13, 16, tzinfo=UTC),
            }
        )
        samples = (*samples[:-1], confirmation_sample)
    return REGISTERED_FIXTURE.model_copy(
        update={
            "source_observation_expectations": expectations,
            "report_scope_source_evidence": evidence,
            "samples": samples,
        }
    )


def test_future_report_scope_source_resolves_without_sample_time_binding(
    snapshots: tuple[SnapshotBundle, ...],
) -> None:
    expectation = _future_membership_expectation(snapshots)
    evidence = _scope_evidence(expectation.key)
    fixture = _fixture_with_scope(expectation, (evidence,))

    assert expectation.normalized_observation.available_at > max(
        sample.feature_available_at_utc for sample in fixture.samples
    )
    resolution = resolve_source_lineage(
        policy=REGISTERED_POLICY,
        fixture=fixture,
        snapshots=snapshots,
    )

    resolved_scope = next(
        item for item in resolution.source_observations if item.key == expectation.key
    )
    scope_ref = resolved_scope.reference()
    samples_by_id = {sample.sample_id: sample for sample in fixture.samples}
    assert all(
        scope_ref not in lineage.source_observation_refs for lineage in resolution.sample_lineage
    )
    assert all(
        lineage.source_observation_keys == samples_by_id[lineage.sample_id].source_observation_keys
        for lineage in resolution.sample_lineage
    )


def test_report_scope_source_requires_confirmation_sample(
    snapshots: tuple[SnapshotBundle, ...],
) -> None:
    expectation = _future_membership_expectation(snapshots)
    fixture = _fixture_with_scope(
        expectation,
        (_scope_evidence(expectation.key),),
        add_confirmation_sample=False,
    )

    with pytest.raises(
        SourceLineageInputError,
        match="report_scope_confirmation_sample_missing",
    ):
        resolve_source_lineage(
            policy=REGISTERED_POLICY,
            fixture=fixture,
            snapshots=snapshots,
        )


def test_report_scope_source_cannot_overlap_sample_lineage(
    snapshots: tuple[SnapshotBundle, ...],
) -> None:
    sample_key = REGISTERED_FIXTURE.samples[0].source_observation_keys[0]
    fixture = REGISTERED_FIXTURE.model_copy(
        update={"report_scope_source_evidence": (_scope_evidence(sample_key),)}
    )

    with pytest.raises(SourceLineageInputError, match="report_scope_sample_source_overlap"):
        resolve_source_lineage(
            policy=REGISTERED_POLICY,
            fixture=fixture,
            snapshots=snapshots,
        )


def test_source_expectation_union_rejects_orphan_and_undeclared_scope_key(
    snapshots: tuple[SnapshotBundle, ...],
) -> None:
    expectation = _future_membership_expectation(snapshots)
    orphan_fixture = _fixture_with_scope(expectation, (), add_confirmation_sample=False)

    with pytest.raises(
        SourceLineageInputError,
        match="fixture_source_expectation_orphaned_or_missing",
    ):
        resolve_source_lineage(
            policy=REGISTERED_POLICY,
            fixture=orphan_fixture,
            snapshots=snapshots,
        )

    undeclared_key = SourceObservationKey(
        capability=DataCapability.OHLCV,
        normalized_observation_id=UUID("11111111-1111-5111-8111-111111111111"),
    )
    undeclared_scope_fixture = REGISTERED_FIXTURE.model_copy(
        update={"report_scope_source_evidence": (_scope_evidence(undeclared_key),)}
    )
    with pytest.raises(
        SourceLineageInputError,
        match="fixture_source_expectation_orphaned_or_missing",
    ):
        resolve_source_lineage(
            policy=REGISTERED_POLICY,
            fixture=undeclared_scope_fixture,
            snapshots=snapshots,
        )


def test_duplicate_expectation_and_scope_role_are_ambiguous(
    snapshots: tuple[SnapshotBundle, ...],
) -> None:
    duplicate_expectation_fixture = REGISTERED_FIXTURE.model_copy(
        update={
            "source_observation_expectations": (
                *REGISTERED_FIXTURE.source_observation_expectations,
                REGISTERED_FIXTURE.source_observation_expectations[-1],
            )
        }
    )
    with pytest.raises(SourceLineageInputError, match="fixture_source_expectation_ambiguous"):
        resolve_source_lineage(
            policy=REGISTERED_POLICY,
            fixture=duplicate_expectation_fixture,
            snapshots=snapshots,
        )

    expectation = _future_membership_expectation(snapshots)
    duplicate_scope_fixture = _fixture_with_scope(
        expectation,
        (
            _scope_evidence(expectation.key),
            _scope_evidence(
                expectation.key,
                role=ReportScopeSourceRole.PREPARED_LABEL_GRAPH,
            ),
        ),
    )
    with pytest.raises(SourceLineageInputError, match="report_scope_source_role_ambiguous"):
        resolve_source_lineage(
            policy=REGISTERED_POLICY,
            fixture=duplicate_scope_fixture,
            snapshots=snapshots,
        )


def test_report_scope_evidence_requires_one_prepared_pipeline_hash(
    snapshots: tuple[SnapshotBundle, ...],
) -> None:
    expectation = _future_membership_expectation(snapshots)
    undeclared_key = SourceObservationKey(
        capability=DataCapability.OHLCV,
        normalized_observation_id=UUID("11111111-1111-5111-8111-111111111111"),
    )
    fixture = _fixture_with_scope(
        expectation,
        (
            _scope_evidence(expectation.key),
            _scope_evidence(
                undeclared_key,
                role=ReportScopeSourceRole.PREPARED_LABEL_GRAPH,
                pipeline_sha256="8" * 64,
            ),
        ),
    )

    with pytest.raises(
        SourceLineageInputError,
        match="report_scope_prepared_pipeline_hash_ambiguous",
    ):
        resolve_source_lineage(
            policy=REGISTERED_POLICY,
            fixture=fixture,
            snapshots=snapshots,
        )
