"""Mandatory, deterministic Phase 4 point-in-time data-quality gate."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from itertools import pairwise
from typing import Literal, cast
from uuid import UUID

from fable5_mapping.models import CanonicalFamily
from pydantic import JsonValue, model_validator

from fable5_data.canonical import (
    canonical_json_bytes,
    quality_finding_id_from_sha256,
    quality_finding_sha256,
    raw_payload_sha256,
)
from fable5_data.contracts import (
    OFFICIAL_DOCUMENT_CONTENT_SCHEMA_VERSION,
    PHASE6_DATA_QUALITY_RULE_SET_VERSION,
    SOCIAL_ATTENTION_SCHEMA_VERSION,
    AdapterAvailableResult,
    AdapterBatchDraft,
    AsReportedFundamentalPayload,
    ConstituentDisposition,
    CorporateActionPayload,
    DataCapability,
    DataQualityCode,
    DataQualityFindingDraft,
    DataQualitySeverity,
    DataRecordType,
    DelistingEventPayload,
    DelistingReturnInclusion,
    FindingDisposition,
    ListingIdentityPayload,
    MissingnessReason,
    MockConfigurationIdentity,
    NormalizedObservationDraft,
    OfficialDocumentContentPayload,
    OfficialDocumentEventPayload,
    OhlcvBarPayload,
    RequestFingerprintInput,
    SectorClassificationPayload,
    SnapshotBuildBlockedResult,
    SnapshotConstituentDraft,
    SnapshotRequestParameters,
    SocialAttentionPayload,
    StrictModel,
    UniverseMembershipPayload,
    VolatilityReturnInputPayload,
    official_document_content_sha256,
)


@dataclass(frozen=True, slots=True)
class DatasetGrain:
    """Frozen, vendor-neutral declaration used by executable uniqueness checks."""

    record_type: DataRecordType
    grain: str
    natural_key_fields: tuple[str, ...]


DATASET_GRAIN_KEY_MATRIX: dict[DataRecordType, DatasetGrain] = {
    DataRecordType.INSTRUMENT_IDENTITY: DatasetGrain(
        DataRecordType.INSTRUMENT_IDENTITY,
        "one instrument identity vintage per stable instrument and validity start",
        ("instrument_id", "valid_from"),
    ),
    DataRecordType.LISTING_IDENTITY: DatasetGrain(
        DataRecordType.LISTING_IDENTITY,
        "one listing identity vintage per stable listing and validity start",
        ("listing_id", "valid_from"),
    ),
    DataRecordType.UNIVERSE_MEMBERSHIP: DatasetGrain(
        DataRecordType.UNIVERSE_MEMBERSHIP,
        "one historical membership interval per universe, listing, and validity start",
        ("payload.universe_id", "listing_id", "valid_from"),
    ),
    DataRecordType.OHLCV_BAR: DatasetGrain(
        DataRecordType.OHLCV_BAR,
        "one bar vintage per listing, interval, start, and adjustment basis",
        (
            "listing_id",
            "payload.bar_interval",
            "payload.bar_start",
            "payload.adjustment_basis",
        ),
    ),
    DataRecordType.CORPORATE_ACTION: DatasetGrain(
        DataRecordType.CORPORATE_ACTION,
        "one action vintage per stable corporate-action identity",
        ("payload.corporate_action_id",),
    ),
    DataRecordType.DELISTING_EVENT: DatasetGrain(
        DataRecordType.DELISTING_EVENT,
        "one delisting vintage per stable delisting-event identity",
        ("payload.delisting_event_id",),
    ),
    DataRecordType.AS_REPORTED_FUNDAMENTAL: DatasetGrain(
        DataRecordType.AS_REPORTED_FUNDAMENTAL,
        "one as-reported filing vintage per instrument, concept, and fiscal period",
        (
            "instrument_id",
            "payload.concept_id",
            "payload.fiscal_period_end",
            "payload.fiscal_period_type",
        ),
    ),
    DataRecordType.CALENDAR_SESSION: DatasetGrain(
        DataRecordType.CALENDAR_SESSION,
        "one session vintage per calendar and session date",
        ("calendar_id", "payload.session_date"),
    ),
    DataRecordType.OFFICIAL_DOCUMENT_EVENT: DatasetGrain(
        DataRecordType.OFFICIAL_DOCUMENT_EVENT,
        "one immutable official source version per accession and event",
        (
            "payload.accession_id",
            "payload.official_event_id",
            "payload.official_source_version_id",
        ),
    ),
    DataRecordType.VOLATILITY_RETURN_INPUT: DatasetGrain(
        DataRecordType.VOLATILITY_RETURN_INPUT,
        "one exact input bundle per listing and return window",
        ("listing_id", "payload.window_start", "payload.window_end"),
    ),
    DataRecordType.SECTOR_CLASSIFICATION: DatasetGrain(
        DataRecordType.SECTOR_CLASSIFICATION,
        "one point-in-time sector classification per instrument, scheme, and validity start",
        (
            "instrument_id",
            "payload.classification_scheme_id",
            "payload.classification_scheme_version",
            "valid_from",
        ),
    ),
    DataRecordType.OFFICIAL_DOCUMENT_CONTENT: DatasetGrain(
        DataRecordType.OFFICIAL_DOCUMENT_CONTENT,
        "one immutable official UTF-8 document body per source version and correction sequence",
        (
            "payload.official_document_id",
            "payload.official_source_version_id",
            "payload.correction_sequence",
        ),
    ),
    DataRecordType.SOCIAL_ATTENTION: DatasetGrain(
        DataRecordType.SOCIAL_ATTENTION,
        "one immutable social-attention observation per platform record and observation time",
        (
            "payload.social_attention_record_id",
            "payload.platform_id",
            "payload.observed_at",
        ),
    ),
    DataRecordType.MACRO_RATE_OBSERVATION: DatasetGrain(
        DataRecordType.MACRO_RATE_OBSERVATION,
        "one immutable rate vintage per series, observation period, and release",
        (
            "payload.series_id",
            "payload.observation_period_end",
            "payload.released_at",
            "payload.vintage_id",
        ),
    ),
    DataRecordType.CRISIS_WINDOW_DEFINITION: DatasetGrain(
        DataRecordType.CRISIS_WINDOW_DEFINITION,
        "one predeclared stress-window geometry per stable window identity",
        ("payload.crisis_window_id", "payload.declared_at"),
    ),
}


def constituent_sort_key(item: SnapshotConstituentDraft) -> tuple[str, ...]:
    return (
        item.record_type.value,
        item.logical_record_id,
        item.logical_record_key_sha256,
        item.revision_id,
        item.vintage_id,
        item.raw_payload_sha256,
        item.normalized_content_sha256,
        item.disposition.value,
    )


def finding_sort_key(item: DataQualityFindingDraft) -> tuple[str, ...]:
    return (
        item.rule_set_version,
        item.rule_id,
        item.severity.value,
        item.code.value,
        "" if item.affected_record_type is None else item.affected_record_type.value,
        "" if item.affected_record_identity is None else item.affected_record_identity,
        "" if item.raw_payload_sha256 is None else item.raw_payload_sha256,
        "" if item.normalized_content_sha256 is None else item.normalized_content_sha256,
        "" if item.field_name is None else item.field_name,
        item.disposition.value,
        item.finding_sha256,
    )


class QualityAcceptedResult(StrictModel):
    """A quality-gated batch that is safe to hand to snapshot materialization."""

    status: Literal["accepted"] = "accepted"
    request_fingerprint_sha256: str
    batch: AdapterBatchDraft
    constituents: tuple[SnapshotConstituentDraft, ...]

    @model_validator(mode="after")
    def validate_canonical_order(self) -> QualityAcceptedResult:
        if tuple(sorted(self.constituents, key=constituent_sort_key)) != self.constituents:
            raise ValueError("quality-gated constituents must be canonically sorted")
        if tuple(sorted(self.batch.quality_findings, key=finding_sort_key)) != (
            self.batch.quality_findings
        ):
            raise ValueError("quality findings must be canonically sorted")
        if any(
            item.disposition is FindingDisposition.BLOCKED for item in self.batch.quality_findings
        ):
            raise ValueError("accepted quality results cannot contain blocked findings")
        return self


QualityGateResult = QualityAcceptedResult | SnapshotBuildBlockedResult


@dataclass(frozen=True, slots=True)
class QualityReferenceCatalog:
    """Exact normalized records available to cross-dataset integrity checks."""

    observations: tuple[NormalizedObservationDraft, ...]

    @classmethod
    def from_results(
        cls,
        results: tuple[AdapterAvailableResult, ...],
    ) -> QualityReferenceCatalog:
        observations = {
            item.normalized_observation_id: item
            for result in results
            for item in result.batch.normalized_observations
        }
        return cls(
            tuple(
                sorted(
                    observations.values(),
                    key=lambda item: (
                        item.payload.record_type,
                        str(item.normalized_observation_id),
                    ),
                )
            )
        )


def _finding(
    *,
    rule_id: str,
    severity: DataQualitySeverity,
    code: DataQualityCode,
    disposition: FindingDisposition,
    detail: dict[str, JsonValue],
    occurrence_count: int,
    total_count: int,
    affected: NormalizedObservationDraft | None = None,
    field_name: str | None = None,
    range_start: datetime | None = None,
    range_end: datetime | None = None,
    rule_set_version: str = "phase4-data-quality-v1",
) -> DataQualityFindingDraft:
    values: dict[str, object] = {
        "rule_set_version": rule_set_version,
        "rule_id": rule_id,
        "severity": severity,
        "code": code,
        "affected_record_type": (
            None if affected is None else DataRecordType(affected.payload.record_type)
        ),
        "affected_record_identity": None if affected is None else affected.logical_record_id,
        "raw_payload_sha256": None if affected is None else affected.raw_payload_sha256,
        "normalized_content_sha256": (
            None if affected is None else affected.normalized_content_sha256
        ),
        "field_name": field_name,
        "disposition": disposition,
        "occurrence_count": occurrence_count,
        "occurrence_rate": Decimal(occurrence_count)
        / Decimal(max(total_count, occurrence_count, 1)),
        "range_start_utc": range_start,
        "range_end_utc": range_end,
        "sanitized_detail": detail,
    }
    finding_hash = quality_finding_sha256(values)
    return DataQualityFindingDraft.model_validate(
        {
            **values,
            "finding_id": quality_finding_id_from_sha256(finding_hash),
            "finding_sha256": finding_hash,
        }
    )


def _utc_order_findings(
    observations: tuple[NormalizedObservationDraft, ...],
) -> list[DataQualityFindingDraft]:
    findings: list[DataQualityFindingDraft] = []
    total = len(observations)
    for observation in observations:
        timestamps = (
            observation.event_time,
            observation.available_at,
            observation.retrieved_at,
            observation.valid_from,
            observation.valid_to,
        )
        aware_utc = all(
            value is None
            or (value.tzinfo is not None and value.utcoffset() == UTC.utcoffset(value))
            for value in timestamps
        )
        ordered = (
            observation.retrieved_at is None or observation.retrieved_at >= observation.available_at
        ) and (observation.valid_to is None or observation.valid_to > observation.valid_from)
        if not aware_utc or not ordered:
            findings.append(
                _finding(
                    rule_id="phase4.utc-and-timestamp-order",
                    severity=DataQualitySeverity.BLOCKING,
                    code=DataQualityCode.INVALID_TIMESTAMP_ORDER,
                    disposition=FindingDisposition.BLOCKED,
                    detail={"check": "utc-aware-retrieval-validity-order"},
                    occurrence_count=1,
                    total_count=total,
                    affected=observation,
                    range_start=observation.event_time,
                    range_end=observation.event_time,
                )
            )
    return findings


def _required_and_schema_findings(
    result: AdapterAvailableResult,
) -> list[DataQualityFindingDraft]:
    findings: list[DataQualityFindingDraft] = []
    total = len(result.batch.normalized_observations)
    allowed_schemas = {
        (item.dataset_schema_id, item.dataset_schema_version)
        for item in result.profile.schema_bindings
    }
    forbidden = {"", "unknown", "n/a", "na", "null", "none", "undefined"}
    for observation in result.batch.normalized_observations:
        required_identifiers = (
            observation.logical_record_id,
            observation.provider_id,
            observation.adapter_id,
            observation.adapter_version,
            observation.dataset_id,
            observation.product_id,
            observation.dataset_schema_id,
            observation.dataset_schema_version,
            observation.entitlement_id,
            observation.use_rights_id,
            observation.source_record_id,
            observation.revision_id,
            observation.vintage_id,
        )
        if any(value.strip().casefold() in forbidden for value in required_identifiers):
            findings.append(
                _finding(
                    rule_id="phase4.required-field-completeness",
                    severity=DataQualitySeverity.BLOCKING,
                    code=DataQualityCode.REQUIRED_FIELD_MISSING,
                    disposition=FindingDisposition.BLOCKED,
                    detail={"check": "nonblank-nonsentinel-required-identifiers"},
                    occurrence_count=1,
                    total_count=total,
                    affected=observation,
                )
            )
        try:
            record_type = DataRecordType(observation.payload.record_type)
        except ValueError:
            findings.append(
                _finding(
                    rule_id="phase4.closed-value-sets",
                    severity=DataQualitySeverity.BLOCKING,
                    code=DataQualityCode.INVALID_ENUM_VALUE,
                    disposition=FindingDisposition.BLOCKED,
                    detail={"check": "record-type-closed-value-set"},
                    occurrence_count=1,
                    total_count=total,
                    affected=observation,
                    field_name="payload.record_type",
                )
            )
            continue
        if (
            observation.dataset_schema_id,
            observation.dataset_schema_version,
        ) not in allowed_schemas:
            findings.append(
                _finding(
                    rule_id="phase4.schema-binding",
                    severity=DataQualitySeverity.BLOCKING,
                    code=DataQualityCode.SCHEMA_DRIFT,
                    disposition=FindingDisposition.BLOCKED,
                    detail={"check": "adapter-declared-schema-binding"},
                    occurrence_count=1,
                    total_count=total,
                    affected=observation,
                )
            )
        if record_type not in DATASET_GRAIN_KEY_MATRIX:
            findings.append(
                _finding(
                    rule_id="phase4.declared-grain",
                    severity=DataQualitySeverity.BLOCKING,
                    code=DataQualityCode.SCHEMA_DRIFT,
                    disposition=FindingDisposition.BLOCKED,
                    detail={"check": "declared-grain-and-natural-key"},
                    occurrence_count=1,
                    total_count=total,
                    affected=observation,
                )
            )
    return findings


def _duplicate_findings(
    observations: tuple[NormalizedObservationDraft, ...],
) -> list[DataQualityFindingDraft]:
    findings: list[DataQualityFindingDraft] = []
    total = len(observations)
    exact: dict[tuple[str, str], list[NormalizedObservationDraft]] = defaultdict(list)
    semantic: dict[str, list[NormalizedObservationDraft]] = defaultdict(list)
    for observation in observations:
        exact[(observation.logical_record_key_sha256, observation.vintage_id)].append(observation)
        signature = raw_payload_sha256(
            canonical_json_bytes(
                {
                    "record_type": observation.payload.record_type,
                    "instrument_id": observation.instrument_id,
                    "listing_id": observation.listing_id,
                    "event_time": observation.event_time,
                    "payload": observation.payload,
                }
            )
        )
        semantic[signature].append(observation)

    for group in exact.values():
        if len(group) < 2:
            continue
        ordered = sorted(group, key=lambda item: str(item.normalized_observation_id))
        findings.append(
            _finding(
                rule_id="phase4.exact-key-vintage-uniqueness",
                severity=DataQualitySeverity.BLOCKING,
                code=DataQualityCode.EXACT_DUPLICATE_KEY,
                disposition=FindingDisposition.BLOCKED,
                detail={"check": "logical-key-plus-vintage-unique"},
                occurrence_count=len(ordered),
                total_count=total,
                affected=ordered[0],
                range_start=min(item.event_time for item in ordered),
                range_end=max(item.event_time for item in ordered),
            )
        )
    for group in semantic.values():
        logical_keys = {item.logical_record_key_sha256 for item in group}
        if len(group) < 2 or len(logical_keys) < 2:
            continue
        ordered = sorted(group, key=lambda item: str(item.normalized_observation_id))
        findings.append(
            _finding(
                rule_id="phase4.near-duplicate-retention",
                severity=DataQualitySeverity.WARNING,
                code=DataQualityCode.NEAR_DUPLICATE_RETAINED,
                disposition=FindingDisposition.RETAINED,
                detail={"check": "semantic-duplicate-retained-with-distinct-key"},
                occurrence_count=len(ordered),
                total_count=total,
                affected=ordered[0],
                range_start=min(item.event_time for item in ordered),
                range_end=max(item.event_time for item in ordered),
            )
        )
    return findings


def _lineage_coverage_findings(
    result: AdapterAvailableResult,
) -> list[DataQualityFindingDraft]:
    batch = result.batch
    normalized_raw = {item.raw_observation_id for item in batch.normalized_observations}
    normalized_revisions = {item.observation_revision_id for item in batch.normalized_observations}
    exclusions = {
        item.raw_payload_sha256
        for item in batch.quality_findings
        if item.code is DataQualityCode.UNNORMALIZED_REJECTED
        and item.disposition is FindingDisposition.EXCLUDED
    }
    findings: list[DataQualityFindingDraft] = []
    total = max(len(batch.raw_observations), 1)
    for raw in batch.raw_observations:
        if (
            raw.raw_observation_id not in normalized_raw
            and raw.raw_payload_sha256 not in exclusions
        ):
            findings.append(
                _finding(
                    rule_id="phase4.raw-normalized-lineage-coverage",
                    severity=DataQualitySeverity.BLOCKING,
                    code=DataQualityCode.RAW_NORMALIZED_LINEAGE_GAP,
                    disposition=FindingDisposition.BLOCKED,
                    detail={"check": "raw-row-accounted-for-by-normalization-or-rejection"},
                    occurrence_count=1,
                    total_count=total,
                    field_name="raw_observation_id",
                    range_start=raw.event_time,
                    range_end=raw.event_time,
                )
            )
    for revision in batch.revisions:
        if (
            revision.revision_record_id not in normalized_revisions
            and revision.raw_payload_sha256 not in exclusions
        ):
            findings.append(
                _finding(
                    rule_id="phase4.revision-normalized-lineage-coverage",
                    severity=DataQualitySeverity.BLOCKING,
                    code=DataQualityCode.RAW_NORMALIZED_LINEAGE_GAP,
                    disposition=FindingDisposition.BLOCKED,
                    detail={"check": "revision-accounted-for-by-normalization-or-rejection"},
                    occurrence_count=1,
                    total_count=max(len(batch.revisions), 1),
                    field_name="revision_record_id",
                    range_start=revision.event_time,
                    range_end=revision.event_time,
                )
            )
    return findings


def _referential_and_consistency_findings(
    observations: tuple[NormalizedObservationDraft, ...],
    catalog: QualityReferenceCatalog,
) -> list[DataQualityFindingDraft]:
    findings: list[DataQualityFindingDraft] = []
    total = len(observations)
    instruments: dict[UUID, list[NormalizedObservationDraft]] = defaultdict(list)
    listings: dict[UUID, list[NormalizedObservationDraft]] = defaultdict(list)
    for item in catalog.observations:
        if (
            item.instrument_id is not None
            and DataRecordType(item.payload.record_type) is DataRecordType.INSTRUMENT_IDENTITY
        ):
            instruments[item.instrument_id].append(item)
        if item.listing_id is not None and isinstance(item.payload, ListingIdentityPayload):
            listings[item.listing_id].append(item)
    currency_required = {
        DataRecordType.OHLCV_BAR,
        DataRecordType.DELISTING_EVENT,
        DataRecordType.AS_REPORTED_FUNDAMENTAL,
        DataRecordType.VOLATILITY_RETURN_INPUT,
    }
    for observation in observations:
        record_type = DataRecordType(observation.payload.record_type)
        instrument_candidates = (
            []
            if observation.instrument_id is None
            else instruments.get(observation.instrument_id, [])
        )
        instrument = next(
            (
                item
                for item in instrument_candidates
                if item.available_at <= observation.available_at
                and item.valid_from <= observation.event_time
                and (item.valid_to is None or observation.event_time < item.valid_to)
            ),
            None,
        )
        if record_type not in {
            DataRecordType.CALENDAR_SESSION,
            DataRecordType.INSTRUMENT_IDENTITY,
            DataRecordType.MACRO_RATE_OBSERVATION,
            DataRecordType.CRISIS_WINDOW_DEFINITION,
        } and (instrument is None or instrument.available_at > observation.available_at):
            findings.append(
                _finding(
                    rule_id="phase4.instrument-referential-integrity",
                    severity=DataQualitySeverity.BLOCKING,
                    code=DataQualityCode.ORPHAN_REFERENCE,
                    disposition=FindingDisposition.BLOCKED,
                    detail={"check": "stable-instrument-exists-without-lookahead"},
                    occurrence_count=1,
                    total_count=total,
                    affected=observation,
                    field_name="instrument_id",
                )
            )
        listing_candidates = (
            [] if observation.listing_id is None else listings.get(observation.listing_id, [])
        )
        listing = next(
            (
                item
                for item in listing_candidates
                if item.instrument_id == observation.instrument_id
                and item.available_at <= observation.available_at
                and item.valid_from <= observation.event_time
                and (item.valid_to is None or observation.event_time < item.valid_to)
            ),
            None,
        )
        if (
            observation.listing_id is not None
            and record_type is not DataRecordType.LISTING_IDENTITY
            and listing is None
        ):
            findings.append(
                _finding(
                    rule_id="phase4.listing-referential-integrity",
                    severity=DataQualitySeverity.BLOCKING,
                    code=DataQualityCode.ORPHAN_REFERENCE,
                    disposition=FindingDisposition.BLOCKED,
                    detail={"check": "stable-listing-exists-and-matches-instrument"},
                    occurrence_count=1,
                    total_count=total,
                    affected=observation,
                    field_name="listing_id",
                )
            )
        mismatch = observation.unit is None or observation.calendar_id is None
        if record_type in currency_required and observation.currency is None:
            mismatch = True
        if listing is not None and record_type is not DataRecordType.LISTING_IDENTITY:
            mismatch = mismatch or observation.source_timezone != listing.source_timezone
            mismatch = mismatch or observation.calendar_id != listing.calendar_id
            if observation.currency is not None and listing.currency is not None:
                mismatch = mismatch or observation.currency != listing.currency
        if mismatch:
            findings.append(
                _finding(
                    rule_id="phase4.units-currency-calendar-timezone-consistency",
                    severity=DataQualitySeverity.BLOCKING,
                    code=DataQualityCode.UNIT_CURRENCY_CALENDAR_TIMEZONE_MISMATCH,
                    disposition=FindingDisposition.BLOCKED,
                    detail={"check": "applicable-metadata-present-and-listing-consistent"},
                    occurrence_count=1,
                    total_count=total,
                    affected=observation,
                )
            )
    return findings


def _membership_findings(
    request: SnapshotRequestParameters,
    observations: tuple[NormalizedObservationDraft, ...],
) -> list[DataQualityFindingDraft]:
    memberships = [
        item for item in observations if isinstance(item.payload, UniverseMembershipPayload)
    ]
    grouped: dict[tuple[UUID, str], list[NormalizedObservationDraft]] = defaultdict(list)
    for observation in memberships:
        if observation.listing_id is not None:
            payload = cast(UniverseMembershipPayload, observation.payload)
            grouped[(observation.listing_id, payload.universe_id)].append(observation)
    findings: list[DataQualityFindingDraft] = []
    for group in grouped.values():
        covering = [
            item
            for item in group
            if item.available_at <= request.as_of_utc
            and item.valid_from <= request.as_of_utc
            and (item.valid_to is None or request.as_of_utc < item.valid_to)
        ]
        if covering:
            continue
        ordered = sorted(group, key=lambda item: item.valid_from)
        findings.append(
            _finding(
                rule_id="phase4.historical-universe-membership",
                severity=DataQualitySeverity.BLOCKING,
                code=DataQualityCode.CURRENT_UNIVERSE_LEAKAGE,
                disposition=FindingDisposition.BLOCKED,
                detail={"check": "historical-interval-covers-requested-as-of"},
                occurrence_count=1,
                total_count=max(len(memberships), 1),
                affected=ordered[0],
                range_start=min(item.valid_from for item in ordered),
                range_end=max(item.valid_from for item in ordered),
            )
        )
    return findings


def _sector_classification_findings(
    observations: tuple[NormalizedObservationDraft, ...],
) -> list[DataQualityFindingDraft]:
    sectors = [
        item for item in observations if isinstance(item.payload, SectorClassificationPayload)
    ]
    findings: list[DataQualityFindingDraft] = []
    total = max(len(sectors), 1)
    for observation in sectors:
        if observation.instrument_id is None or observation.listing_id is not None:
            findings.append(
                _finding(
                    rule_id="phase6.sector-classification-instrument-scope",
                    severity=DataQualitySeverity.BLOCKING,
                    code=DataQualityCode.PIT_CLASSIFICATION_INVALID,
                    disposition=FindingDisposition.BLOCKED,
                    detail={"check": "instrument-scoped-sector-history"},
                    occurrence_count=1,
                    total_count=total,
                    affected=observation,
                    field_name="instrument_id",
                    rule_set_version=PHASE6_DATA_QUALITY_RULE_SET_VERSION,
                )
            )

    # Multiple vintages of one logical classification are revision history.  Only the
    # latest available vintage for each logical key participates in interval overlap checks.
    latest_by_key: dict[str, NormalizedObservationDraft] = {}
    for observation in sectors:
        current = latest_by_key.get(observation.logical_record_key_sha256)
        if current is None or (
            observation.available_at,
            str(observation.normalized_observation_id),
        ) > (current.available_at, str(current.normalized_observation_id)):
            latest_by_key[observation.logical_record_key_sha256] = observation

    grouped: dict[tuple[UUID, str, str], list[NormalizedObservationDraft]] = defaultdict(list)
    for observation in latest_by_key.values():
        if observation.instrument_id is None:
            continue
        payload = cast(SectorClassificationPayload, observation.payload)
        grouped[
            (
                observation.instrument_id,
                payload.classification_scheme_id,
                payload.classification_scheme_version,
            )
        ].append(observation)
    for group in grouped.values():
        ordered = sorted(
            group,
            key=lambda item: (item.valid_from, str(item.normalized_observation_id)),
        )
        for previous, current in pairwise(ordered):
            if previous.valid_to is None or current.valid_from < previous.valid_to:
                findings.append(
                    _finding(
                        rule_id="phase6.sector-classification-nonoverlap",
                        severity=DataQualitySeverity.BLOCKING,
                        code=DataQualityCode.PIT_CLASSIFICATION_INVALID,
                        disposition=FindingDisposition.BLOCKED,
                        detail={"check": "nonoverlapping-point-in-time-validity-intervals"},
                        occurrence_count=2,
                        total_count=total,
                        affected=current,
                        field_name="valid_from",
                        range_start=previous.valid_from,
                        range_end=current.valid_from,
                        rule_set_version=PHASE6_DATA_QUALITY_RULE_SET_VERSION,
                    )
                )
    return findings


def _fundamental_findings(
    observations: tuple[NormalizedObservationDraft, ...],
    catalog: QualityReferenceCatalog,
) -> list[DataQualityFindingDraft]:
    fundamentals = {
        item.revision_id: item
        for item in catalog.observations
        if isinstance(item.payload, AsReportedFundamentalPayload)
    }
    findings: list[DataQualityFindingDraft] = []
    for observation in observations:
        if not isinstance(observation.payload, AsReportedFundamentalPayload):
            continue
        payload = observation.payload
        if payload.amendment_sequence == 0:
            continue
        predecessor = fundamentals.get(payload.restates_revision_id or "")
        if (
            predecessor is None
            or predecessor.logical_record_key_sha256 != observation.logical_record_key_sha256
            or predecessor.available_at >= observation.available_at
            or not isinstance(predecessor.payload, AsReportedFundamentalPayload)
            or predecessor.payload.amendment_sequence + 1 != payload.amendment_sequence
        ):
            findings.append(
                _finding(
                    rule_id="phase4.fundamental-revision-vintage-replay",
                    severity=DataQualitySeverity.BLOCKING,
                    code=DataQualityCode.RESTATEMENT_LEAKAGE,
                    disposition=FindingDisposition.BLOCKED,
                    detail={"check": "amendment-restates-existing-earlier-vintage"},
                    occurrence_count=1,
                    total_count=max(len(fundamentals), 1),
                    affected=observation,
                    field_name="payload.restates_revision_id",
                )
            )
    return findings


def _corporate_action_findings(
    request: SnapshotRequestParameters,
    observations: tuple[NormalizedObservationDraft, ...],
    catalog: QualityReferenceCatalog,
) -> list[DataQualityFindingDraft]:
    actions = {
        item.revision_id: item
        for item in catalog.observations
        if isinstance(item.payload, CorporateActionPayload)
    }
    findings: list[DataQualityFindingDraft] = []
    for observation in observations:
        if not isinstance(observation.payload, OhlcvBarPayload):
            continue
        payload = observation.payload
        if payload.adjustment_as_of is None:
            continue
        for revision_id in payload.corporate_action_revision_ids:
            action = actions.get(revision_id)
            if (
                action is None
                or action.instrument_id != observation.instrument_id
                or (action.listing_id is not None and action.listing_id != observation.listing_id)
                or action.available_at > payload.adjustment_as_of
                or action.available_at > request.as_of_utc
            ):
                findings.append(
                    _finding(
                        rule_id="phase4.corporate-action-adjustment-as-of",
                        severity=DataQualitySeverity.BLOCKING,
                        code=DataQualityCode.CORPORATE_ACTION_LOOKAHEAD,
                        disposition=FindingDisposition.BLOCKED,
                        detail={"check": "referenced-action-exists-and-was-available"},
                        occurrence_count=1,
                        total_count=max(len(payload.corporate_action_revision_ids), 1),
                        affected=observation,
                        field_name="payload.corporate_action_revision_ids",
                    )
                )
    return findings


def _delisting_findings(
    observations: tuple[NormalizedObservationDraft, ...],
) -> list[DataQualityFindingDraft]:
    delistings = [item for item in observations if isinstance(item.payload, DelistingEventPayload)]
    findings: list[DataQualityFindingDraft] = []
    for observation in delistings:
        payload = cast(DelistingEventPayload, observation.payload)
        if payload.delisting_return is not None:
            continue
        expected = (
            MissingnessReason.PROVIDER_RETURN_ALREADY_INCLUDES_DELISTING
            if payload.return_inclusion is DelistingReturnInclusion.PROVIDER_TOTAL_RETURN_INCLUDES
            else MissingnessReason.DELISTING_RETURN_NOT_PROVIDED
        )
        if observation.missingness_reason("payload.delisting_return") is not expected:
            severity = DataQualitySeverity.BLOCKING
            disposition = FindingDisposition.BLOCKED
        else:
            severity = DataQualitySeverity.WARNING
            disposition = FindingDisposition.RETAINED
        findings.append(
            _finding(
                rule_id="phase4.delisting-return-explicit-missingness",
                severity=severity,
                code=DataQualityCode.MISSING_DELISTING_RETURN,
                disposition=disposition,
                detail={"check": "null-retained-with-explicit-domain-reason-no-zero-fill"},
                occurrence_count=1,
                total_count=max(len(delistings), 1),
                affected=observation,
                field_name="payload.delisting_return",
            )
        )
    return findings


def _volatility_reference_findings(
    request: SnapshotRequestParameters,
    observations: tuple[NormalizedObservationDraft, ...],
    catalog: QualityReferenceCatalog,
) -> list[DataQualityFindingDraft]:
    by_id = {item.normalized_observation_id: item for item in catalog.observations}
    findings: list[DataQualityFindingDraft] = []
    for observation in observations:
        if not isinstance(observation.payload, VolatilityReturnInputPayload):
            continue
        payload = observation.payload
        reference_sets = (
            (payload.bar_observation_ids, DataRecordType.OHLCV_BAR, "bar_observation_ids"),
            (
                payload.corporate_action_observation_ids,
                DataRecordType.CORPORATE_ACTION,
                "corporate_action_observation_ids",
            ),
            (
                payload.delisting_observation_ids,
                DataRecordType.DELISTING_EVENT,
                "delisting_observation_ids",
            ),
            (
                payload.calendar_observation_ids,
                DataRecordType.CALENDAR_SESSION,
                "calendar_observation_ids",
            ),
        )
        for identities, expected_type, field_name in reference_sets:
            for identity in identities:
                referenced = by_id.get(identity)
                mismatched_scope = (
                    referenced is not None
                    and expected_type is not DataRecordType.CALENDAR_SESSION
                    and (
                        referenced.instrument_id != observation.instrument_id
                        or referenced.listing_id != observation.listing_id
                    )
                )
                if (
                    referenced is None
                    or DataRecordType(referenced.payload.record_type) is not expected_type
                    or referenced.available_at > observation.available_at
                    or referenced.available_at > request.as_of_utc
                    or mismatched_scope
                ):
                    findings.append(
                        _finding(
                            rule_id="phase4.volatility-input-exact-references",
                            severity=DataQualitySeverity.BLOCKING,
                            code=DataQualityCode.ORPHAN_REFERENCE,
                            disposition=FindingDisposition.BLOCKED,
                            detail={"check": "exact-typed-reference-exists-without-lookahead"},
                            occurrence_count=1,
                            total_count=max(sum(len(values) for values, _, _ in reference_sets), 1),
                            affected=observation,
                            field_name=f"payload.{field_name}",
                        )
                    )
    return findings


def _official_document_content_findings(
    observations: tuple[NormalizedObservationDraft, ...],
    catalog: QualityReferenceCatalog,
) -> list[DataQualityFindingDraft]:
    contents = [
        item for item in observations if isinstance(item.payload, OfficialDocumentContentPayload)
    ]
    if not contents:
        return []
    total = len(contents)
    findings: list[DataQualityFindingDraft] = []
    metadata = [
        item
        for item in catalog.observations
        if isinstance(item.payload, OfficialDocumentEventPayload)
    ]
    all_contents = [
        item
        for item in catalog.observations
        if isinstance(item.payload, OfficialDocumentContentPayload)
    ]

    for observation in contents:
        payload = cast(OfficialDocumentContentPayload, observation.payload)
        try:
            expected_hash = official_document_content_sha256(payload.document_text)
        except ValueError:
            expected_hash = ""
        if payload.document_content_sha256 != expected_hash:
            findings.append(
                _finding(
                    rule_id="phase6.official-document-content-utf8-sha256",
                    severity=DataQualitySeverity.BLOCKING,
                    code=DataQualityCode.DOCUMENT_CONTENT_HASH_MISMATCH,
                    disposition=FindingDisposition.BLOCKED,
                    detail={"check": "exact-utf8-document-text-sha256"},
                    occurrence_count=1,
                    total_count=total,
                    affected=observation,
                    field_name="payload.document_content_sha256",
                    rule_set_version=PHASE6_DATA_QUALITY_RULE_SET_VERSION,
                )
            )

        matching_metadata = [
            item
            for item in metadata
            if isinstance(item.payload, OfficialDocumentEventPayload)
            and item.payload.official_document_id == payload.official_document_id
            and item.payload.official_event_id == payload.official_event_id
            and item.payload.official_source_version_id == payload.official_source_version_id
            and item.payload.document_type is payload.document_type
            and item.payload.event_type is payload.event_type
            and item.payload.accession_id == payload.accession_id
            and item.payload.document_content_sha256 == payload.document_content_sha256
            and item.payload.amendment_of_document_id == payload.amendment_of_document_id
            and item.instrument_id == observation.instrument_id
            and item.listing_id == observation.listing_id
            and item.available_at <= observation.available_at
        ]
        if not matching_metadata:
            findings.append(
                _finding(
                    rule_id="phase6.official-document-content-metadata-lineage",
                    severity=DataQualitySeverity.BLOCKING,
                    code=DataQualityCode.OFFICIAL_CORROBORATION_MISMATCH,
                    disposition=FindingDisposition.BLOCKED,
                    detail={"check": "exact-official-metadata-content-lineage"},
                    occurrence_count=1,
                    total_count=total,
                    affected=observation,
                    field_name="payload.official_document_id",
                    rule_set_version=PHASE6_DATA_QUALITY_RULE_SET_VERSION,
                )
            )

        if payload.correction_sequence == 0:
            correction_valid = (
                payload.corrected_at is None and payload.amendment_of_document_id is None
            )
        else:
            predecessors = [
                item
                for item in all_contents
                if isinstance(item.payload, OfficialDocumentContentPayload)
                and item.payload.official_document_id == payload.amendment_of_document_id
                and item.payload.official_event_id == payload.official_event_id
                and item.payload.official_source_version_id == payload.official_source_version_id
                and item.payload.correction_sequence + 1 == payload.correction_sequence
                and item.instrument_id == observation.instrument_id
                and item.listing_id == observation.listing_id
                and item.available_at < observation.available_at
                and item.payload.accepted_at < payload.accepted_at
                and payload.corrected_at is not None
                and item.payload.accepted_at < payload.corrected_at
            ]
            correction_valid = bool(predecessors)
        if not correction_valid:
            findings.append(
                _finding(
                    rule_id="phase6.official-document-correction-sequence",
                    severity=DataQualitySeverity.BLOCKING,
                    code=DataQualityCode.DOCUMENT_CORRECTION_TIMING_INVALID,
                    disposition=FindingDisposition.BLOCKED,
                    detail={"check": "strictly-later-immutable-correction-chain"},
                    occurrence_count=1,
                    total_count=total,
                    affected=observation,
                    field_name="payload.amendment_of_document_id",
                    rule_set_version=PHASE6_DATA_QUALITY_RULE_SET_VERSION,
                )
            )
    return findings


def _official_corroboration_findings(
    request: SnapshotRequestParameters,
    result: AdapterAvailableResult,
    eligible: tuple[NormalizedObservationDraft, ...],
) -> list[DataQualityFindingDraft]:
    if (
        request.mapping.canonical_family is not CanonicalFamily.C_OFFICIAL_EVENT_TEXT_OVERLAY
        or request.capability is not DataCapability.OFFICIAL_DOCUMENT_EVENT_METADATA
    ):
        return []
    expected = set(request.mapping.official_corroboration_source_version_ids)
    actual = {
        item.payload.official_source_version_id
        for item in eligible
        if isinstance(item.payload, OfficialDocumentEventPayload)
    }
    findings: list[DataQualityFindingDraft] = []
    if actual != expected:
        affected = next(
            (item for item in eligible if isinstance(item.payload, OfficialDocumentEventPayload)),
            None,
        )
        findings.append(
            _finding(
                rule_id="phase4.family-c-exact-official-corroboration",
                severity=DataQualitySeverity.BLOCKING,
                code=DataQualityCode.ORPHAN_REFERENCE,
                disposition=FindingDisposition.BLOCKED,
                detail={
                    "check": "exact-persisted-official-source-version-set",
                    "expected_count": len(expected),
                    "actual_count": len(actual),
                },
                occurrence_count=max(len(expected.symmetric_difference(actual)), 1),
                total_count=max(len(expected.union(actual)), 1),
                affected=affected,
                field_name="payload.official_source_version_id",
            )
        )

    content_schema_declared = any(
        item.dataset_schema_version == OFFICIAL_DOCUMENT_CONTENT_SCHEMA_VERSION
        for item in result.profile.schema_bindings
    )
    content_actual = {
        item.payload.official_source_version_id
        for item in eligible
        if isinstance(item.payload, OfficialDocumentContentPayload)
    }
    if content_schema_declared and content_actual != expected:
        affected = next(
            (item for item in eligible if isinstance(item.payload, OfficialDocumentContentPayload)),
            None,
        )
        findings.append(
            _finding(
                rule_id="phase6.family-c-exact-official-content-corroboration",
                severity=DataQualitySeverity.BLOCKING,
                code=DataQualityCode.OFFICIAL_CORROBORATION_MISMATCH,
                disposition=FindingDisposition.BLOCKED,
                detail={
                    "check": "exact-persisted-official-content-source-version-set",
                    "expected_count": len(expected),
                    "actual_count": len(content_actual),
                },
                occurrence_count=max(len(expected.symmetric_difference(content_actual)), 1),
                total_count=max(len(expected.union(content_actual)), 1),
                affected=affected,
                field_name="payload.official_source_version_id",
                rule_set_version=PHASE6_DATA_QUALITY_RULE_SET_VERSION,
            )
        )
    social_schema_declared = any(
        item.dataset_schema_version == SOCIAL_ATTENTION_SCHEMA_VERSION
        for item in result.profile.schema_bindings
    )
    social_records = [item for item in eligible if isinstance(item.payload, SocialAttentionPayload)]
    social_actual = {
        cast(SocialAttentionPayload, item.payload).claimed_official_source_version_id
        for item in social_records
    }
    if social_schema_declared and social_actual != expected:
        affected = social_records[0] if social_records else None
        findings.append(
            _finding(
                rule_id="phase6.family-c-social-attention-exact-official-source-set",
                severity=DataQualitySeverity.BLOCKING,
                code=DataQualityCode.OFFICIAL_CORROBORATION_MISMATCH,
                disposition=FindingDisposition.BLOCKED,
                detail={
                    "check": "every-social-attention-record-has-exact-official-source",
                    "expected_count": len(expected),
                    "actual_count": len(social_actual),
                },
                occurrence_count=max(len(expected.symmetric_difference(social_actual)), 1),
                total_count=max(len(expected.union(social_actual)), 1),
                affected=affected,
                field_name="payload.claimed_official_source_version_id",
                rule_set_version=PHASE6_DATA_QUALITY_RULE_SET_VERSION,
            )
        )
    for observation in social_records:
        payload = cast(SocialAttentionPayload, observation.payload)
        matching_official = [
            item
            for item in eligible
            if isinstance(item.payload, OfficialDocumentContentPayload)
            and item.payload.official_source_version_id
            == payload.claimed_official_source_version_id
            and item.instrument_id == observation.instrument_id
            and item.listing_id == observation.listing_id
            and item.available_at <= observation.available_at
        ]
        if not matching_official or payload.contributes_standalone:
            findings.append(
                _finding(
                    rule_id="phase6.family-c-social-attention-official-document-lineage",
                    severity=DataQualitySeverity.BLOCKING,
                    code=DataQualityCode.OFFICIAL_CORROBORATION_MISMATCH,
                    disposition=FindingDisposition.BLOCKED,
                    detail={"check": "exact-official-document-precedes-social-attention"},
                    occurrence_count=1,
                    total_count=max(len(social_records), 1),
                    affected=observation,
                    field_name="payload.social_attention_record_id",
                    rule_set_version=PHASE6_DATA_QUALITY_RULE_SET_VERSION,
                )
            )
    return findings


def _future_findings(
    request: SnapshotRequestParameters,
    future: tuple[NormalizedObservationDraft, ...],
    total: int,
) -> list[DataQualityFindingDraft]:
    findings: list[DataQualityFindingDraft] = []
    by_type: dict[DataRecordType, list[NormalizedObservationDraft]] = defaultdict(list)
    for item in future:
        by_type[DataRecordType(item.payload.record_type)].append(item)
    for group in by_type.values():
        ordered = sorted(
            group, key=lambda item: (item.available_at, str(item.normalized_observation_id))
        )
        findings.append(
            _finding(
                rule_id="phase4.future-availability-exclusion",
                severity=DataQualitySeverity.WARNING,
                code=DataQualityCode.FUTURE_AVAILABILITY_EXCLUDED,
                disposition=FindingDisposition.EXCLUDED,
                detail={
                    "check": "available-at-not-after-requested-as-of",
                    "requested_as_of_utc": request.as_of_utc.isoformat(),
                },
                occurrence_count=len(ordered),
                total_count=total,
                affected=ordered[0],
                range_start=min(item.available_at for item in ordered),
                range_end=max(item.available_at for item in ordered),
            )
        )
    return findings


def _informational_findings(
    observations: tuple[NormalizedObservationDraft, ...],
) -> list[DataQualityFindingDraft]:
    if not observations:
        return []
    findings = [
        _finding(
            rule_id="phase4.synthetic-fixture-provenance",
            severity=DataQualitySeverity.INFO,
            code=DataQualityCode.SYNTHETIC_FIXTURE,
            disposition=FindingDisposition.RETAINED,
            detail={
                "check": "clearly-labeled-deterministic-synthetic-data",
                "raw_count": len({item.raw_observation_id for item in observations}),
                "revision_count": len({item.observation_revision_id for item in observations}),
                "normalized_count": len(observations),
            },
            occurrence_count=len(observations),
            total_count=len(observations),
            affected=observations[0],
            range_start=min(item.event_time for item in observations),
            range_end=max(item.event_time for item in observations),
        )
    ]
    date_only = [item for item in observations if item.availability_precision.value == "date"]
    if date_only:
        findings.append(
            _finding(
                rule_id="phase4.conservative-date-only-availability",
                severity=DataQualitySeverity.INFO,
                code=DataQualityCode.DATE_ONLY_CONVENTION_APPLIED,
                disposition=FindingDisposition.RETAINED,
                detail={"check": "source-date-available-next-local-day"},
                occurrence_count=len(date_only),
                total_count=len(observations),
                affected=date_only[0],
                range_start=min(item.available_at for item in date_only),
                range_end=max(item.available_at for item in date_only),
            )
        )
    return findings


def _eligible_batch(
    result: AdapterAvailableResult,
    eligible: tuple[NormalizedObservationDraft, ...],
    findings: tuple[DataQualityFindingDraft, ...],
) -> AdapterBatchDraft:
    raw_ids = {item.raw_observation_id for item in eligible}
    revision_ids = {item.observation_revision_id for item in eligible}
    raw = tuple(
        sorted(
            (item for item in result.batch.raw_observations if item.raw_observation_id in raw_ids),
            key=lambda item: str(item.raw_observation_id),
        )
    )
    revisions = tuple(
        sorted(
            (item for item in result.batch.revisions if item.revision_record_id in revision_ids),
            key=lambda item: (
                item.logical_record_key_sha256,
                item.revision_sequence,
                str(item.revision_record_id),
            ),
        )
    )
    normalized = tuple(
        sorted(
            eligible,
            key=lambda item: (
                item.payload.record_type,
                item.logical_record_key_sha256,
                item.available_at,
                str(item.normalized_observation_id),
            ),
        )
    )
    return AdapterBatchDraft(
        raw_observations=raw,
        revisions=revisions,
        normalized_observations=normalized,
        quality_findings=findings,
    )


def _constituents(
    eligible: tuple[NormalizedObservationDraft, ...],
    batch: AdapterBatchDraft,
) -> tuple[SnapshotConstituentDraft, ...]:
    revision_sequence = {
        item.revision_record_id: item.revision_sequence for item in batch.revisions
    }
    grouped: dict[str, list[NormalizedObservationDraft]] = defaultdict(list)
    for item in eligible:
        grouped[item.logical_record_key_sha256].append(item)
    latest_ids: set[UUID] = set()
    for group in grouped.values():
        latest = max(
            group,
            key=lambda item: (
                item.available_at,
                revision_sequence[item.observation_revision_id],
                str(item.normalized_observation_id),
            ),
        )
        latest_ids.add(latest.normalized_observation_id)

    constituents: list[SnapshotConstituentDraft] = []
    for item in eligible:
        nullable_fields = getattr(type(item.payload), "nullable_measurement_fields", ())
        explicit_missing = any(
            getattr(item.payload, field_name.split(".")[-1]) is None
            for field_name in nullable_fields
        )
        if item.normalized_observation_id not in latest_ids:
            disposition = ConstituentDisposition.RETAINED_HISTORICAL_VINTAGE
        elif explicit_missing:
            disposition = ConstituentDisposition.EXPLICIT_MISSINGNESS
        else:
            disposition = ConstituentDisposition.INCLUDED_AS_OF
        envelope = item.model_dump(
            mode="python",
            exclude={
                "normalized_observation_id",
                "raw_observation_id",
                "observation_revision_id",
                "normalized_content_sha256",
                "payload",
            },
        )
        constituents.append(
            SnapshotConstituentDraft(
                **envelope,
                record_type=DataRecordType(item.payload.record_type),
                raw_observation_id=item.raw_observation_id,
                observation_revision_id=item.observation_revision_id,
                normalized_observation_id=item.normalized_observation_id,
                normalized_content_sha256=item.normalized_content_sha256,
                disposition=disposition,
            )
        )
    return tuple(sorted(constituents, key=constituent_sort_key))


def run_mandatory_data_quality(
    *,
    request: SnapshotRequestParameters,
    result: AdapterAvailableResult,
    configuration: MockConfigurationIdentity,
    catalog: QualityReferenceCatalog,
) -> QualityGateResult:
    """Run all mandatory Phase 4 gates and fail closed without persistence on any block."""

    fingerprint = RequestFingerprintInput(
        request=request,
        adapter=result.profile,
        schema_bindings=result.profile.schema_bindings,
        use_rights=result.profile.use_rights,
        configuration=configuration,
    ).sha256()
    observations = result.batch.normalized_observations
    eligible = tuple(item for item in observations if item.available_at <= request.as_of_utc)
    future = tuple(item for item in observations if item.available_at > request.as_of_utc)

    findings: list[DataQualityFindingDraft] = list(result.batch.quality_findings)
    findings.extend(_required_and_schema_findings(result))
    findings.extend(_utc_order_findings(observations))
    findings.extend(_duplicate_findings(observations))
    findings.extend(_lineage_coverage_findings(result))
    findings.extend(_referential_and_consistency_findings(observations, catalog))
    findings.extend(_membership_findings(request, observations))
    findings.extend(_sector_classification_findings(observations))
    findings.extend(_fundamental_findings(observations, catalog))
    findings.extend(_corporate_action_findings(request, observations, catalog))
    findings.extend(_delisting_findings(eligible))
    findings.extend(_volatility_reference_findings(request, observations, catalog))
    findings.extend(_official_document_content_findings(observations, catalog))
    findings.extend(_official_corroboration_findings(request, result, eligible))
    findings.extend(_future_findings(request, future, len(observations)))
    findings.extend(_informational_findings(eligible))
    unique_findings = {item.finding_sha256: item for item in findings}
    ordered_findings = tuple(sorted(unique_findings.values(), key=finding_sort_key))

    if any(item.disposition is FindingDisposition.BLOCKED for item in ordered_findings):
        return SnapshotBuildBlockedResult(
            request_fingerprint_sha256=fingerprint,
            quality_findings=ordered_findings,
        )
    gated_batch = _eligible_batch(result, eligible, ordered_findings)
    return QualityAcceptedResult(
        request_fingerprint_sha256=fingerprint,
        batch=gated_batch,
        constituents=_constituents(eligible, gated_batch),
    )


__all__ = [
    "DATASET_GRAIN_KEY_MATRIX",
    "DatasetGrain",
    "QualityAcceptedResult",
    "QualityGateResult",
    "QualityReferenceCatalog",
    "constituent_sort_key",
    "finding_sort_key",
    "run_mandatory_data_quality",
]
