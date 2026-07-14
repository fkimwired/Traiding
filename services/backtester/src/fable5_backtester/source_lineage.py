"""Exact Phase 4 observation/value lineage for synthetic Phase 5 samples."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fable5_data.contracts import (
    CAPABILITY_RECORD_TYPES,
    ConstituentDisposition,
    DataCapability,
    SnapshotBundle,
)

from fable5_backtester.canonical import (
    PHASE5_SAMPLE_HASH_DOMAIN,
    PHASE5_SAMPLE_LINEAGE_HASH_DOMAIN,
    domain_sha256,
)
from fable5_backtester.contracts import (
    PHASE5_SOURCE_OBSERVATION_BINDING_RULE,
    FrozenEvaluationPolicy,
    ResolvedSourceObservation,
    ResolvedSourceObservationRef,
    SampleSourceLineage,
    SourceObservationKey,
    SyntheticEvaluationFixture,
    SyntheticSample,
    SyntheticSourceObservationExpectation,
    derive_dependency_graph,
)


class SourceLineageError(ValueError):
    """Base fail-closed lineage error with one stable external reason code."""

    def __init__(self, reason_code: str) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code


class SourceLineagePolicyError(SourceLineageError):
    """The frozen policy omitted or changed the required lineage rule."""


class SourceLineageInputError(SourceLineageError):
    """A snapshot, fixture expectation, or sample cannot be reconciled exactly."""


@dataclass(frozen=True, slots=True)
class SourceLineageResolution:
    source_observations: tuple[ResolvedSourceObservation, ...]
    sample_lineage: tuple[SampleSourceLineage, ...]
    sample_lineage_sha256: str

    def lineage_for(self, sample_id: str) -> SampleSourceLineage:
        for lineage in self.sample_lineage:
            if lineage.sample_id == sample_id:
                return lineage
        raise KeyError(sample_id)


def sample_sha256(sample: SyntheticSample) -> str:
    """Hash every immutable synthetic sample field, including its source references."""

    return domain_sha256(PHASE5_SAMPLE_HASH_DOMAIN, sample)


def _key_tuple(key: SourceObservationKey) -> tuple[str, str]:
    return str(key.capability), str(key.normalized_observation_id)


def _reference_tuple(ref: ResolvedSourceObservationRef) -> tuple[str, str, str]:
    return str(ref.capability), str(ref.snapshot_id), str(ref.normalized_observation_id)


def _resolve_expectation(
    expectation: SyntheticSourceObservationExpectation,
    snapshots_by_capability: dict[DataCapability, SnapshotBundle],
) -> ResolvedSourceObservation:
    bundle = snapshots_by_capability.get(expectation.key.capability)
    if bundle is None:
        raise SourceLineageInputError("snapshot_observation_reference_unresolved")
    if expectation.normalized_observation.payload.record_type not in {
        item.value for item in CAPABILITY_RECORD_TYPES[expectation.key.capability]
    }:
        raise SourceLineageInputError("snapshot_observation_capability_mismatch")

    matches = tuple(
        observation
        for observation in bundle.normalized_observations
        if observation.normalized_observation_id == expectation.key.normalized_observation_id
    )
    constituents = tuple(
        constituent
        for constituent in bundle.constituents
        if constituent.normalized_observation_id == expectation.key.normalized_observation_id
    )
    if len(matches) != 1 or len(constituents) != 1:
        raise SourceLineageInputError("snapshot_observation_reference_unresolved")
    actual = matches[0]
    constituent = constituents[0]
    actual_content = actual.model_dump(
        mode="python",
        exclude={"snapshot_id", "snapshot_sha256"},
    )
    expected_content = expectation.normalized_observation.model_dump(mode="python")
    if actual_content != expected_content:
        raise SourceLineageInputError("snapshot_observation_value_mismatch")
    if expectation.required_disposition not in {
        ConstituentDisposition.INCLUDED_AS_OF,
        ConstituentDisposition.RETAINED_HISTORICAL_VINTAGE,
        ConstituentDisposition.EXPLICIT_MISSINGNESS,
    }:
        raise SourceLineageInputError("snapshot_observation_disposition_ineligible")
    if constituent.disposition is not expectation.required_disposition:
        raise SourceLineageInputError("snapshot_observation_disposition_mismatch")
    if (
        constituent.raw_observation_id != actual.raw_observation_id
        or constituent.observation_revision_id != actual.observation_revision_id
        or constituent.normalized_content_sha256 != actual.normalized_content_sha256
        or constituent.raw_payload_sha256 != actual.raw_payload_sha256
    ):
        raise SourceLineageInputError("snapshot_observation_constituent_lineage_mismatch")
    return ResolvedSourceObservation(
        key=expectation.key,
        normalized_observation=actual,
        disposition=constituent.disposition,
    )


def _validate_sample_binding(
    sample: SyntheticSample,
    expectation: SyntheticSourceObservationExpectation,
    resolved: ResolvedSourceObservation,
) -> None:
    observation = resolved.normalized_observation
    decision_time = sample.decision_time_utc
    if (
        observation.event_time > sample.feature_available_at_utc
        or observation.available_at > sample.feature_available_at_utc
        or observation.valid_from > decision_time
        or (observation.valid_to is not None and decision_time >= observation.valid_to)
    ):
        raise SourceLineageInputError("snapshot_observation_not_available_at_decision")

    for binding in expectation.value_bindings:
        source_value = getattr(observation.payload, binding.source_payload_field, None)
        sample_value = getattr(sample, binding.sample_field)
        if not isinstance(source_value, Decimal):
            raise SourceLineageInputError("snapshot_observation_value_uncomputable")
        if source_value * binding.multiplier != sample_value:
            raise SourceLineageInputError("snapshot_observation_value_mismatch")


def _validate_feature_derivation(
    sample: SyntheticSample,
    resolved_by_key: dict[tuple[str, str], ResolvedSourceObservation],
) -> None:
    derivation = sample.feature_derivation
    resolved = resolved_by_key.get(_key_tuple(derivation.source_observation_key))
    if resolved is None:
        raise SourceLineageInputError("snapshot_feature_derivation_unresolved")
    source_value = getattr(
        resolved.normalized_observation.payload,
        derivation.source_payload_field,
        None,
    )
    if not isinstance(source_value, Decimal) or not source_value.is_finite():
        raise SourceLineageInputError("snapshot_feature_value_uncomputable")
    derived_feature_value = source_value * derivation.multiplier
    if (
        derived_feature_value != derivation.derived_feature_value
        or derivation.derived_feature_value != sample.feature_value
    ):
        raise SourceLineageInputError("snapshot_feature_value_mismatch")


def resolve_source_lineage(
    *,
    policy: FrozenEvaluationPolicy,
    fixture: SyntheticEvaluationFixture,
    snapshots: tuple[SnapshotBundle, ...],
) -> SourceLineageResolution:
    """Resolve every fixture sample to exact snapshot constituents and values."""

    if (
        policy.feature_specification.source_observation_binding_rule
        != PHASE5_SOURCE_OBSERVATION_BINDING_RULE
    ):
        raise SourceLineagePolicyError("source_observation_binding_rule_unsupported")

    snapshots_by_capability: dict[DataCapability, SnapshotBundle] = {}
    for bundle in snapshots:
        capability = bundle.snapshot.manifest.payload.request.capability
        if capability in snapshots_by_capability:
            raise SourceLineageInputError("snapshot_observation_capability_ambiguous")
        snapshots_by_capability[capability] = bundle

    expectations = {
        _key_tuple(expectation.key): expectation
        for expectation in fixture.source_observation_expectations
    }
    expectation_capabilities = tuple(
        sorted({expectation.key.capability for expectation in expectations.values()}, key=str)
    )
    if expectation_capabilities != policy.required_snapshot_capabilities:
        raise SourceLineageInputError("fixture_source_capability_set_mismatch")
    resolved_by_key = {
        key: _resolve_expectation(expectation, snapshots_by_capability)
        for key, expectation in expectations.items()
    }
    source_observations = tuple(resolved_by_key[key] for key in sorted(resolved_by_key))

    sample_lineage: list[SampleSourceLineage] = []
    for sample in fixture.samples:
        if {_key_tuple(key) for key in sample.source_observation_keys} != set(expectations):
            raise SourceLineageInputError("sample_source_capability_coverage_incomplete")
        _validate_feature_derivation(sample, resolved_by_key)
        refs: list[ResolvedSourceObservationRef] = []
        membership_keys: list[SourceObservationKey] = []
        for source_key in sample.source_observation_keys:
            key = _key_tuple(source_key)
            expectation = expectations.get(key)
            resolved = resolved_by_key.get(key)
            if expectation is None or resolved is None:
                raise SourceLineageInputError("snapshot_observation_reference_unresolved")
            _validate_sample_binding(sample, expectation, resolved)
            refs.append(resolved.reference())
            if source_key.capability is DataCapability.UNIVERSE_MEMBERSHIP:
                membership_keys.append(source_key)
        if len(membership_keys) != 1:
            raise SourceLineageInputError("sample_membership_source_missing_or_ambiguous")
        ordered_refs = tuple(sorted(refs, key=_reference_tuple))
        sample_lineage.append(
            SampleSourceLineage(
                sample_id=sample.sample_id,
                sample_sha256=sample_sha256(sample),
                decision_time_utc=sample.decision_time_utc,
                feature_available_at_utc=sample.feature_available_at_utc,
                feature_derivation=sample.feature_derivation,
                reference_price=sample.reference_price,
                price_adjustment_basis=sample.price_adjustment_basis,
                adjustment_action_as_of_utc=sample.adjustment_action_as_of_utc,
                fundamental_revision=sample.fundamental_revision,
                feature_dependency_ids=sample.feature_dependency_ids,
                target_dependency_ids=sample.target_dependency_ids,
                universe_membership=sample.universe_membership,
                membership_source_observation_key=membership_keys[0],
                dependency_graph=derive_dependency_graph(
                    sample,
                    policy.feature_specification,
                    policy.label_specification,
                ),
                synthetic_ledger_value_rule=sample.synthetic_ledger_value_rule,
                source_observation_refs=ordered_refs,
            )
        )
    ordered_lineage = tuple(sorted(sample_lineage, key=lambda item: item.sample_id))
    return SourceLineageResolution(
        source_observations=source_observations,
        sample_lineage=ordered_lineage,
        sample_lineage_sha256=domain_sha256(
            PHASE5_SAMPLE_LINEAGE_HASH_DOMAIN,
            ordered_lineage,
        ),
    )


__all__ = [
    "SourceLineageError",
    "SourceLineageInputError",
    "SourceLineagePolicyError",
    "SourceLineageResolution",
    "resolve_source_lineage",
    "sample_sha256",
]
