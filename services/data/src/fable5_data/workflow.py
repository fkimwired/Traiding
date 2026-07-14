"""Server-resolved Phase 4 snapshot orchestration.

The workflow accepts only an immutable Phase 3 mapping identity, an as-of time, a
vendor-neutral capability, and a registered deterministic mock configuration.  Adapter
payloads, provenance, entitlement claims, hashes, and timestamps are never accepted from
the client.
"""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from fable5_data.adapters import Phase4DataAdapter
from fable5_data.contracts import (
    AdapterUnavailableReason,
    AdapterUnavailableResult,
    AuthorizedMappingIdentity,
    DataSnapshot,
    MockConfigurationIdentity,
    SnapshotBuildBlockedResult,
    SnapshotBundle,
    SnapshotCreateRequest,
    SnapshotRequestParameters,
    UseRightsScope,
)
from fable5_data.quality import (
    QualityAcceptedResult,
    QualityReferenceCatalog,
    run_mandatory_data_quality,
)
from fable5_data.repository import SnapshotLineage, SnapshotRepository
from fable5_data.snapshots import SnapshotCandidate, build_snapshot_candidate

AdapterResolver = Callable[
    [AuthorizedMappingIdentity],
    tuple[Phase4DataAdapter, QualityReferenceCatalog],
]
ConfigurationResolver = Callable[[str], MockConfigurationIdentity | None]
ConfiguredAdapterResolver = Callable[
    [AuthorizedMappingIdentity, MockConfigurationIdentity],
    tuple[Phase4DataAdapter, QualityReferenceCatalog],
]


class SnapshotAdapterUnavailable(RuntimeError):
    """A sanitized, typed adapter/configuration unavailability result."""

    def __init__(self, result: AdapterUnavailableResult) -> None:
        super().__init__(result.sanitized_message)
        self.result = result


class SnapshotQualityBlocked(RuntimeError):
    """A non-persistable data-quality result with inspectable blocking evidence."""

    def __init__(self, result: SnapshotBuildBlockedResult) -> None:
        super().__init__("mandatory Phase 4 data-quality checks blocked snapshot creation")
        self.result = result


class SnapshotWorkflow:
    def __init__(
        self,
        repository: SnapshotRepository,
        adapter: Phase4DataAdapter,
        configuration: MockConfigurationIdentity,
        quality_catalog: QualityReferenceCatalog,
        adapter_resolver: AdapterResolver | None = None,
        configuration_resolver: ConfigurationResolver | None = None,
        configured_adapter_resolver: ConfiguredAdapterResolver | None = None,
    ) -> None:
        self.repository = repository
        self.adapter = adapter
        self.configuration = configuration
        self.quality_catalog = quality_catalog
        self.adapter_resolver = adapter_resolver
        self.configuration_resolver = configuration_resolver
        self.configured_adapter_resolver = configured_adapter_resolver

    def _configuration_unavailable(
        self,
        request: SnapshotCreateRequest,
    ) -> SnapshotAdapterUnavailable:
        profile = self.adapter.profile
        rights = profile.use_rights
        return SnapshotAdapterUnavailable(
            AdapterUnavailableResult(
                reason_code=AdapterUnavailableReason.CONFIGURATION_UNAVAILABLE,
                capability=request.capability,
                provider_id=profile.provider_id,
                adapter_id=profile.adapter_id,
                adapter_version=profile.adapter_version,
                dataset_id=profile.dataset_id,
                product_id=profile.product_id,
                entitlement_id=rights.entitlement_id,
                use_rights_id=rights.use_rights_id,
                sanitized_message="deterministic mock configuration unavailable",
            )
        )

    def create_snapshot(self, request: SnapshotCreateRequest) -> SnapshotBundle:
        configuration = self.configuration
        if request.mock_configuration_id != configuration.configuration_id:
            if self.configuration_resolver is None:
                raise self._configuration_unavailable(request)
            resolved_configuration = self.configuration_resolver(request.mock_configuration_id)
            if resolved_configuration is None:
                raise self._configuration_unavailable(request)
            configuration = resolved_configuration

        # Resolve and authorize the immutable Phase 3 mapping before adapter access.
        mapping = self.repository.resolve_mapping(request.mapping_id, request.capability)
        adapter = self.adapter
        quality_catalog = self.quality_catalog
        if self.configured_adapter_resolver is not None:
            adapter, quality_catalog = self.configured_adapter_resolver(mapping, configuration)
        elif self.adapter_resolver is not None:
            adapter, quality_catalog = self.adapter_resolver(mapping)
        parameters = SnapshotRequestParameters(
            mapping=mapping,
            as_of_utc=request.as_of_utc,
            capability=request.capability,
            mock_configuration_id=request.mock_configuration_id,
        )
        adapter_result = adapter.fetch(request.capability)
        if isinstance(adapter_result, AdapterUnavailableResult):
            raise SnapshotAdapterUnavailable(adapter_result)
        if (
            not adapter_result.profile.synthetic
            or adapter_result.profile.use_rights.scope
            is not UseRightsScope.INTERNAL_TEST_FIXTURE_ONLY
        ):
            profile = adapter_result.profile
            rights = profile.use_rights
            raise SnapshotAdapterUnavailable(
                AdapterUnavailableResult(
                    reason_code=AdapterUnavailableReason.ENTITLEMENT_UNAVAILABLE,
                    capability=request.capability,
                    provider_id=profile.provider_id,
                    adapter_id=profile.adapter_id,
                    adapter_version=profile.adapter_version,
                    dataset_id=profile.dataset_id,
                    product_id=profile.product_id,
                    entitlement_id=rights.entitlement_id,
                    use_rights_id=rights.use_rights_id,
                    sanitized_message="Phase 4 persistence entitlement unavailable",
                )
            )

        quality_result = run_mandatory_data_quality(
            request=parameters,
            result=adapter_result,
            configuration=configuration,
            catalog=quality_catalog,
        )
        if isinstance(quality_result, SnapshotBuildBlockedResult):
            raise SnapshotQualityBlocked(quality_result)
        if not isinstance(quality_result, QualityAcceptedResult):  # pragma: no cover - closed union
            raise SnapshotLineage("unrecognized quality-gate result")

        materialized = build_snapshot_candidate(
            mapping=mapping,
            request=parameters,
            profile=adapter_result.profile,
            configuration=configuration,
            batch=quality_result.batch,
        )
        if not isinstance(materialized, SnapshotCandidate):
            raise SnapshotQualityBlocked(materialized)

        quality_constituents = tuple(
            (item.normalized_content_sha256, item.disposition)
            for item in quality_result.constituents
        )
        snapshot_constituents = tuple(
            (item.normalized_content_sha256, item.disposition)
            for item in materialized.bundle.constituents
        )
        if snapshot_constituents != quality_constituents:
            raise SnapshotLineage(
                "quality-gate constituents differ from canonical snapshot constituents"
            )
        return self.repository.create_snapshot(materialized)

    def get_snapshot(self, snapshot_id: UUID) -> SnapshotBundle:
        return self.repository.get_snapshot(snapshot_id)

    def list_snapshots(
        self,
        *,
        mapping_id: UUID | None,
        limit: int,
    ) -> list[DataSnapshot]:
        return [
            bundle.snapshot
            for bundle in self.repository.list_snapshots(mapping_id=mapping_id, limit=limit)
        ]


__all__ = [
    "AdapterResolver",
    "ConfigurationResolver",
    "ConfiguredAdapterResolver",
    "SnapshotAdapterUnavailable",
    "SnapshotQualityBlocked",
    "SnapshotWorkflow",
]
