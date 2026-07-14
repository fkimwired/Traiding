from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from fable5_data.adapters import CredentialGatedAdapter, Phase4DataAdapter
from fable5_data.contracts import (
    AdapterAvailableResult,
    AdapterProfile,
    AdapterResult,
    AdapterUnavailableReason,
    AuthorizedMappingIdentity,
    DataCapability,
    SnapshotCreateRequest,
    UseRightsScope,
)
from fable5_data.quality import QualityReferenceCatalog
from fable5_data.repository import SnapshotAuthorization, SnapshotRepository
from fable5_data.snapshots import SnapshotCandidate
from fable5_data.synthetic import (
    SYNTHETIC_ADAPTER_PROFILE,
    SYNTHETIC_MOCK_CONFIGURATION,
    SyntheticPointInTimeAdapter,
    load_fixture_records,
)
from fable5_data.workflow import (
    SnapshotAdapterUnavailable,
    SnapshotQualityBlocked,
    SnapshotWorkflow,
)
from fable5_mapping.models import CanonicalFamily, ResearchVerdict

MAPPING_ID = UUID("aaaaaaaa-aaaa-5aaa-8aaa-aaaaaaaaaaaa")
AS_OF = datetime(2021, 1, 1, tzinfo=UTC)


class _CountingAdapter:
    def __init__(self) -> None:
        self.delegate = SyntheticPointInTimeAdapter()
        self.fetch_calls = 0

    @property
    def profile(self) -> AdapterProfile:
        return self.delegate.profile

    def fetch(self, capability: DataCapability) -> AdapterResult:
        self.fetch_calls += 1
        return self.delegate.fetch(capability)


def _mapping() -> AuthorizedMappingIdentity:
    return AuthorizedMappingIdentity(
        mapping_id=MAPPING_ID,
        mapping_version=1,
        mapping_input_sha256="1" * 64,
        mapper_rule_set_version="phase3-test-rules",
        mapper_rule_set_sha256="2" * 64,
        canonical_family=CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING,
        verdict=ResearchVerdict.BUILD_RESEARCH,
    )


def _request(
    *,
    configuration_id: str = SYNTHETIC_MOCK_CONFIGURATION.configuration_id,
) -> SnapshotCreateRequest:
    return SnapshotCreateRequest(
        mapping_id=MAPPING_ID,
        as_of_utc=AS_OF,
        capability=DataCapability.OHLCV,
        mock_configuration_id=configuration_id,
    )


def _repository() -> MagicMock:
    repository = MagicMock(spec=SnapshotRepository)
    repository.resolve_mapping.return_value = _mapping()
    repository.create_snapshot.side_effect = lambda candidate: candidate.bundle
    return repository


def _workflow(
    repository: SnapshotRepository,
    adapter: Phase4DataAdapter,
    *,
    catalog_adapter: SyntheticPointInTimeAdapter | None = None,
) -> SnapshotWorkflow:
    source = catalog_adapter or SyntheticPointInTimeAdapter()
    return SnapshotWorkflow(
        repository=repository,
        adapter=adapter,
        configuration=SYNTHETIC_MOCK_CONFIGURATION,
        quality_catalog=QualityReferenceCatalog.from_results(source.all_results()),
    )


def test_create_resolves_mapping_runs_quality_and_persists_only_server_built_candidate() -> None:
    adapter = SyntheticPointInTimeAdapter()
    repository = _repository()
    workflow = _workflow(repository, adapter, catalog_adapter=adapter)

    first = workflow.create_snapshot(_request())
    second = workflow.create_snapshot(_request())

    assert first.snapshot.snapshot_id == second.snapshot.snapshot_id
    assert first.snapshot.snapshot_sha256 == second.snapshot.snapshot_sha256
    repository.resolve_mapping.assert_called_with(MAPPING_ID, DataCapability.OHLCV)
    assert repository.create_snapshot.call_count == 2
    candidates = [call.args[0] for call in repository.create_snapshot.call_args_list]
    assert all(isinstance(item, SnapshotCandidate) for item in candidates)
    assert candidates[0].canonical_identity_bytes == candidates[1].canonical_identity_bytes


def test_unknown_mock_configuration_is_typed_unavailable_before_database_or_adapter() -> None:
    adapter = _CountingAdapter()
    repository = _repository()
    workflow = _workflow(repository, adapter)

    with pytest.raises(SnapshotAdapterUnavailable) as raised:
        workflow.create_snapshot(_request(configuration_id="unregistered-configuration"))

    assert raised.value.result.reason_code is AdapterUnavailableReason.CONFIGURATION_UNAVAILABLE
    repository.resolve_mapping.assert_not_called()
    assert adapter.fetch_calls == 0


def test_mapping_authorization_fails_before_adapter_fetch() -> None:
    adapter = _CountingAdapter()
    repository = _repository()
    repository.resolve_mapping.side_effect = SnapshotAuthorization("not authorized")
    workflow = _workflow(repository, adapter)

    with pytest.raises(SnapshotAuthorization):
        workflow.create_snapshot(_request())

    assert adapter.fetch_calls == 0
    repository.create_snapshot.assert_not_called()


def test_credential_unavailable_makes_zero_transport_and_persistence_calls() -> None:
    factory = MagicMock()
    adapter = CredentialGatedAdapter(
        profile=SYNTHETIC_ADAPTER_PROFILE,
        credentials_available=False,
        transport_factory=factory,
    )
    repository = _repository()
    workflow = _workflow(repository, adapter)

    with pytest.raises(SnapshotAdapterUnavailable) as raised:
        workflow.create_snapshot(_request())

    assert raised.value.result.reason_code is AdapterUnavailableReason.CREDENTIALS_UNAVAILABLE
    factory.assert_not_called()
    repository.create_snapshot.assert_not_called()


def test_available_non_synthetic_profile_is_typed_entitlement_unavailable() -> None:
    synthetic = SyntheticPointInTimeAdapter()
    profile_values = synthetic.profile.model_dump(mode="python")
    profile_values["synthetic"] = False
    profile_values["use_rights"] = {
        **synthetic.profile.use_rights.model_dump(mode="python"),
        "scope": UseRightsScope.INTERNAL_RESEARCH_ONLY,
    }
    profile = AdapterProfile.model_validate(profile_values)
    available = AdapterAvailableResult(
        profile=profile,
        capability=DataCapability.OHLCV,
        batch=synthetic.fetch(DataCapability.OHLCV).batch,
    )
    adapter = MagicMock(spec=Phase4DataAdapter)
    adapter.fetch.return_value = available
    repository = _repository()
    workflow = _workflow(repository, adapter)

    with pytest.raises(SnapshotAdapterUnavailable) as raised:
        workflow.create_snapshot(_request())

    assert raised.value.result.reason_code is AdapterUnavailableReason.ENTITLEMENT_UNAVAILABLE
    repository.create_snapshot.assert_not_called()


def test_blocking_quality_result_is_never_persisted() -> None:
    records = [deepcopy(item) for item in load_fixture_records()]
    adjusted = next(item for item in records if item["alias"] == "bar_adjusted")
    duplicate = deepcopy(adjusted)
    duplicate.update(
        {
            "alias": "bar_adjusted_exact_copy",
            "source_record_id": "synthetic-bar-exact-copy",
            "revision_id": "bar-adjusted-exact-copy-r1",
        }
    )
    records.append(duplicate)
    adapter = SyntheticPointInTimeAdapter(tuple(records))
    repository = _repository()
    workflow = _workflow(repository, adapter, catalog_adapter=adapter)

    with pytest.raises(SnapshotQualityBlocked) as raised:
        workflow.create_snapshot(_request())

    assert raised.value.result.status == "blocked"
    repository.create_snapshot.assert_not_called()


def test_family_c_synthetic_records_bind_exact_persisted_corroboration_versions() -> None:
    official_ids = tuple(
        sorted(
            (
                UUID("11111111-aaaa-5aaa-8aaa-111111111111"),
                UUID("22222222-bbbb-5bbb-8bbb-222222222222"),
            ),
            key=str,
        )
    )
    mapping = AuthorizedMappingIdentity(
        mapping_id=MAPPING_ID,
        mapping_version=1,
        mapping_input_sha256="1" * 64,
        mapper_rule_set_version="phase3-test-rules",
        mapper_rule_set_sha256="2" * 64,
        canonical_family=CanonicalFamily.C_OFFICIAL_EVENT_TEXT_OVERLAY,
        verdict=ResearchVerdict.BUILD_RESEARCH,
        official_corroboration_source_version_ids=official_ids,
    )
    repository = _repository()
    repository.resolve_mapping.return_value = mapping
    base_adapter = SyntheticPointInTimeAdapter()

    def resolve_adapter(
        resolved_mapping: AuthorizedMappingIdentity,
    ) -> tuple[Phase4DataAdapter, QualityReferenceCatalog]:
        bound = SyntheticPointInTimeAdapter.for_mapping(resolved_mapping)
        return bound, QualityReferenceCatalog.from_results(bound.all_results())

    workflow = SnapshotWorkflow(
        repository=repository,
        adapter=base_adapter,
        configuration=SYNTHETIC_MOCK_CONFIGURATION,
        quality_catalog=QualityReferenceCatalog.from_results(base_adapter.all_results()),
        adapter_resolver=resolve_adapter,
    )
    request = SnapshotCreateRequest(
        mapping_id=MAPPING_ID,
        as_of_utc=AS_OF,
        capability=DataCapability.OFFICIAL_DOCUMENT_EVENT_METADATA,
        mock_configuration_id=SYNTHETIC_MOCK_CONFIGURATION.configuration_id,
    )

    bundle = workflow.create_snapshot(request)

    observed_ids = {
        getattr(item.payload, "official_source_version_id", None)
        for item in bundle.normalized_observations
    }
    assert observed_ids == set(official_ids)
    assert bundle.snapshot.manifest.payload.mapping == mapping
