"""Deterministic, network-free point-in-time fixtures for Phase 4 tests and local use."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import date, datetime
from importlib.resources import files
from typing import Literal, cast
from uuid import UUID

from fable5_mapping.models import CanonicalFamily
from pydantic import TypeAdapter

from fable5_data.canonical import (
    canonical_json_bytes,
    logical_record_id_from_sha256,
    logical_record_key_sha256,
    normalized_observation_content_sha256,
    normalized_observation_id_from_sha256,
    raw_observation_content_sha256,
    raw_observation_id_from_sha256,
    raw_payload_sha256,
    revision_content_sha256,
    revision_id_from_sha256,
)
from fable5_data.contracts import (
    AS_REPORTED_FUNDAMENTAL_SCHEMA_VERSION,
    CALENDAR_SESSION_SCHEMA_VERSION,
    CORPORATE_ACTION_SCHEMA_VERSION,
    DELISTING_EVENT_SCHEMA_VERSION,
    INSTRUMENT_IDENTITY_SCHEMA_VERSION,
    LISTING_IDENTITY_SCHEMA_VERSION,
    OFFICIAL_DOCUMENT_EVENT_SCHEMA_VERSION,
    OHLCV_BAR_SCHEMA_VERSION,
    REVISION_SCHEMA_VERSION,
    SYNTHETIC_ADAPTER_VERSION,
    SYNTHETIC_FIXTURE_SET_VERSION,
    SYNTHETIC_USE_RIGHTS_ID,
    UNIVERSE_MEMBERSHIP_SCHEMA_VERSION,
    VOLATILITY_RETURN_INPUT_SCHEMA_VERSION,
    AdapterAvailableResult,
    AdapterBatchDraft,
    AdapterProfile,
    AuthorizedMappingIdentity,
    AvailabilityConvention,
    AvailabilityPrecision,
    DataCapability,
    DataRecordType,
    FieldMissingness,
    MissingnessReason,
    MockConfigurationIdentity,
    NormalizedObservationDraft,
    NormalizedPayload,
    ObservationEnvelopeDraft,
    ObservationRevisionDraft,
    QualityFlag,
    RawObservationDraft,
    SchemaBinding,
    UseRightsIdentity,
    UseRightsScope,
    conservative_date_available_at,
    mock_configuration_sha256,
)

_FIXTURE_PATH = "fixtures/phase4_synthetic_pit_v1.json"
_PROVIDER_ID = "fable5-synthetic-provider"
_ADAPTER_ID = "fable5-synthetic-point-in-time-adapter"
_DATASET_ID = "fable5-phase4-synthetic-point-in-time"
_PRODUCT_ID = "fable5-phase4-local-test-fixtures"
_ENTITLEMENT_ID = "phase4-synthetic-test-entitlement-v1"
_RAW_CONTENT_TYPE = "application/vnd.fable5.phase4.synthetic+json"

SCHEMA_VERSION_BY_RECORD_TYPE: dict[DataRecordType, str] = {
    DataRecordType.INSTRUMENT_IDENTITY: INSTRUMENT_IDENTITY_SCHEMA_VERSION,
    DataRecordType.LISTING_IDENTITY: LISTING_IDENTITY_SCHEMA_VERSION,
    DataRecordType.UNIVERSE_MEMBERSHIP: UNIVERSE_MEMBERSHIP_SCHEMA_VERSION,
    DataRecordType.OHLCV_BAR: OHLCV_BAR_SCHEMA_VERSION,
    DataRecordType.CORPORATE_ACTION: CORPORATE_ACTION_SCHEMA_VERSION,
    DataRecordType.DELISTING_EVENT: DELISTING_EVENT_SCHEMA_VERSION,
    DataRecordType.AS_REPORTED_FUNDAMENTAL: AS_REPORTED_FUNDAMENTAL_SCHEMA_VERSION,
    DataRecordType.CALENDAR_SESSION: CALENDAR_SESSION_SCHEMA_VERSION,
    DataRecordType.OFFICIAL_DOCUMENT_EVENT: OFFICIAL_DOCUMENT_EVENT_SCHEMA_VERSION,
    DataRecordType.VOLATILITY_RETURN_INPUT: VOLATILITY_RETURN_INPUT_SCHEMA_VERSION,
}

SCHEMA_ID_BY_RECORD_TYPE: dict[DataRecordType, str] = {
    record_type: f"fable5.{record_type.value.replace('_', '-')}" for record_type in DataRecordType
}

SYNTHETIC_ADAPTER_PROFILE = AdapterProfile(
    provider_id=_PROVIDER_ID,
    adapter_id=_ADAPTER_ID,
    adapter_version=SYNTHETIC_ADAPTER_VERSION,
    dataset_id=_DATASET_ID,
    product_id=_PRODUCT_ID,
    synthetic=True,
    capabilities=tuple(sorted(DataCapability, key=str)),
    schema_bindings=tuple(
        sorted(
            (
                SchemaBinding(
                    dataset_schema_id=SCHEMA_ID_BY_RECORD_TYPE[record_type],
                    dataset_schema_version=version,
                )
                for record_type, version in SCHEMA_VERSION_BY_RECORD_TYPE.items()
            ),
            key=lambda item: (item.dataset_schema_id, item.dataset_schema_version),
        )
    ),
    use_rights=UseRightsIdentity(
        entitlement_id=_ENTITLEMENT_ID,
        use_rights_id=SYNTHETIC_USE_RIGHTS_ID,
        scope=UseRightsScope.INTERNAL_TEST_FIXTURE_ONLY,
        storage_allowed=True,
        display_allowed=True,
        non_display_allowed=True,
        derived_data_allowed=True,
        redistribution_allowed=False,
    ),
)

SYNTHETIC_MOCK_CONFIGURATION = MockConfigurationIdentity(
    configuration_id="phase4-synthetic-default-v1",
    configuration_sha256=mock_configuration_sha256(
        {
            "configuration_id": "phase4-synthetic-default-v1",
            "fixture_set_version": SYNTHETIC_FIXTURE_SET_VERSION,
            "adapter_version": SYNTHETIC_ADAPTER_VERSION,
        }
    ),
)

_PAYLOAD_ADAPTER: TypeAdapter[NormalizedPayload] = TypeAdapter(NormalizedPayload)
_OPTIONAL_ENVELOPE_FIELDS = (
    "instrument_id",
    "listing_id",
    "valid_to",
    "calendar_id",
    "unit",
    "currency",
)


def _read_fixture() -> dict[str, object]:
    content = files("fable5_data").joinpath(_FIXTURE_PATH).read_text(encoding="utf-8")
    parsed = json.loads(content)
    if not isinstance(parsed, dict):
        raise ValueError("synthetic fixture root must be an object")
    return cast(dict[str, object], parsed)


def load_fixture_records() -> tuple[dict[str, object], ...]:
    """Return a defensive copy suitable for deterministic negative-test mutations."""

    fixture = _read_fixture()
    records = fixture.get("records")
    if not isinstance(records, list) or not all(isinstance(item, dict) for item in records):
        raise ValueError("synthetic fixture records must be a list of objects")
    return tuple(deepcopy(cast(list[dict[str, object]], records)))


def fixture_set_sha256() -> str:
    """Hash the exact fixture bytes used by the deterministic adapter."""

    payload = files("fable5_data").joinpath(_FIXTURE_PATH).read_bytes()
    return raw_payload_sha256(payload)


def _required_str(record: dict[str, object], key: str) -> str:
    value = record.get(key)
    if not isinstance(value, str):
        raise ValueError(f"synthetic record {key} must be a string")
    return value


def _optional_str(record: dict[str, object], key: str) -> str | None:
    value = record.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"synthetic record {key} must be null or a string")
    return value


def _payload_dict(record: dict[str, object]) -> dict[str, object]:
    value = record.get("payload")
    if not isinstance(value, dict):
        raise ValueError("synthetic record payload must be an object")
    return deepcopy(cast(dict[str, object], value))


def _alias_tuple(payload: dict[str, object], key: str) -> tuple[str, ...]:
    value = payload.pop(key, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{key} must be a list of aliases")
    return tuple(cast(list[str], value))


def _resolve_payload(
    record: dict[str, object],
    built: dict[str, NormalizedObservationDraft],
) -> NormalizedPayload:
    payload = _payload_dict(record)
    record_type = DataRecordType(_required_str(record, "record_type"))
    if record_type is DataRecordType.OHLCV_BAR:
        aliases = _alias_tuple(payload, "corporate_action_revision_aliases")
        payload["corporate_action_revision_ids"] = tuple(
            built[alias].revision_id for alias in aliases
        )
    elif record_type is DataRecordType.AS_REPORTED_FUNDAMENTAL:
        alias = payload.pop("restates_revision_alias", None)
        if alias is not None:
            if not isinstance(alias, str):
                raise ValueError("restates_revision_alias must be a string")
            payload["restates_revision_id"] = built[alias].revision_id
    elif record_type is DataRecordType.VOLATILITY_RETURN_INPUT:
        for aliases_key, ids_key in (
            ("bar_observation_aliases", "bar_observation_ids"),
            ("corporate_action_observation_aliases", "corporate_action_observation_ids"),
            ("delisting_observation_aliases", "delisting_observation_ids"),
            ("calendar_observation_aliases", "calendar_observation_ids"),
        ):
            aliases = _alias_tuple(payload, aliases_key)
            payload[ids_key] = tuple(built[alias].normalized_observation_id for alias in aliases)
    return _PAYLOAD_ADAPTER.validate_python(payload)


def _field_missingness(record: dict[str, object]) -> tuple[FieldMissingness, ...]:
    entries: dict[str, MissingnessReason] = {}
    for field_name in _OPTIONAL_ENVELOPE_FIELDS:
        if record.get(field_name) is None:
            entries[field_name] = MissingnessReason.NOT_APPLICABLE
    payload_missingness = record.get("payload_missingness", {})
    if not isinstance(payload_missingness, dict):
        raise ValueError("payload_missingness must be an object")
    for field_name, reason in cast(dict[str, object], payload_missingness).items():
        if not isinstance(reason, str):
            raise ValueError("payload missingness reasons must be strings")
        entries[field_name] = MissingnessReason(reason)
    return tuple(
        FieldMissingness(field_name=field_name, reason=reason)
        for field_name, reason in sorted(entries.items())
    )


def _envelope(
    record: dict[str, object],
    *,
    fixture: dict[str, object],
    raw_hash: str,
    normalized: bool,
) -> ObservationEnvelopeDraft:
    record_type = DataRecordType(_required_str(record, "record_type"))
    source_timezone = _required_str(record, "source_timezone")
    precision = AvailabilityPrecision(_required_str(record, "availability_precision"))
    source_date: date | None = None
    if precision is AvailabilityPrecision.DATE:
        source_date = date.fromisoformat(_required_str(record, "availability_source_date"))
        available_at = conservative_date_available_at(source_date, source_timezone)
        convention = AvailabilityConvention.DATE_ONLY_NEXT_DAY
    else:
        available_at = datetime.fromisoformat(_required_str(record, "available_at"))
        convention = AvailabilityConvention.SOURCE_TIMESTAMP

    logical_key = record.get("logical_key")
    if not isinstance(logical_key, dict):
        raise ValueError("synthetic logical_key must be an object")
    logical_hash = logical_record_key_sha256(cast(dict[str, object], logical_key))
    retrieved_at = fixture.get("retrieved_at")
    if not isinstance(retrieved_at, str):
        raise ValueError("synthetic fixture retrieved_at must be a string")

    flags = [QualityFlag.SYNTHETIC_FIXTURE]
    if precision is AvailabilityPrecision.DATE:
        flags.append(QualityFlag.DATE_ONLY_CONVENTION_APPLIED)

    envelope_version: Literal["phase4-raw-observation-v1", "phase4-normalized-observation-v1"]
    if normalized:
        envelope_version = "phase4-normalized-observation-v1"
    else:
        envelope_version = "phase4-raw-observation-v1"
    return ObservationEnvelopeDraft(
        envelope_schema_version=envelope_version,
        logical_record_id=str(logical_record_id_from_sha256(logical_hash)),
        logical_record_key_sha256=logical_hash,
        provider_id=_PROVIDER_ID,
        adapter_id=_ADAPTER_ID,
        adapter_version=SYNTHETIC_ADAPTER_VERSION,
        dataset_id=_DATASET_ID,
        product_id=_PRODUCT_ID,
        dataset_schema_id=SCHEMA_ID_BY_RECORD_TYPE[record_type],
        dataset_schema_version=SCHEMA_VERSION_BY_RECORD_TYPE[record_type],
        entitlement_id=_ENTITLEMENT_ID,
        use_rights_id=SYNTHETIC_USE_RIGHTS_ID,
        source_record_id=_required_str(record, "source_record_id"),
        instrument_id=(
            None
            if _optional_str(record, "instrument_id") is None
            else UUID(_required_str(record, "instrument_id"))
        ),
        listing_id=(
            None
            if _optional_str(record, "listing_id") is None
            else UUID(_required_str(record, "listing_id"))
        ),
        event_time=datetime.fromisoformat(_required_str(record, "event_time")),
        available_at=available_at,
        retrieved_at=datetime.fromisoformat(retrieved_at),
        valid_from=datetime.fromisoformat(_required_str(record, "valid_from")),
        valid_to=(
            None
            if _optional_str(record, "valid_to") is None
            else datetime.fromisoformat(_required_str(record, "valid_to"))
        ),
        revision_id=_required_str(record, "revision_id"),
        vintage_id=_required_str(record, "vintage_id"),
        source_timezone=source_timezone,
        calendar_id=_optional_str(record, "calendar_id"),
        unit=_optional_str(record, "unit"),
        currency=_optional_str(record, "currency"),
        availability_precision=precision,
        availability_convention=convention,
        availability_source_date=source_date,
        quality_flags=tuple(flags),
        field_missingness=_field_missingness(record),
        raw_payload_sha256=raw_hash,
    )


def _build_record(
    record: dict[str, object],
    *,
    fixture: dict[str, object],
    built: dict[str, NormalizedObservationDraft],
) -> tuple[RawObservationDraft, ObservationRevisionDraft, NormalizedObservationDraft]:
    raw_payload = canonical_json_bytes(
        {
            "fixture_set_version": SYNTHETIC_FIXTURE_SET_VERSION,
            "source_record": record,
        }
    )
    raw_hash = raw_payload_sha256(raw_payload)
    raw_envelope = _envelope(record, fixture=fixture, raw_hash=raw_hash, normalized=False)
    raw_values = raw_envelope.model_dump(mode="python")
    raw_identity = {**raw_values, "raw_content_type": _RAW_CONTENT_TYPE}
    raw_identity_hash = raw_observation_content_sha256(raw_identity)
    raw = RawObservationDraft(
        **raw_values,
        raw_observation_id=raw_observation_id_from_sha256(raw_identity_hash),
        raw_content_type=_RAW_CONTENT_TYPE,
        raw_payload=raw_payload,
    )

    normalized_envelope = _envelope(record, fixture=fixture, raw_hash=raw_hash, normalized=True)
    envelope_values = normalized_envelope.model_dump(mode="python")
    predecessor_alias = record.get("predecessor_alias")
    predecessor_id = None
    if predecessor_alias is not None:
        if not isinstance(predecessor_alias, str):
            raise ValueError("predecessor_alias must be a string")
        predecessor_id = built[predecessor_alias].observation_revision_id
    revision_sequence = record.get("revision_sequence", 1)
    if not isinstance(revision_sequence, int):
        raise ValueError("revision_sequence must be an integer")
    revision_values: dict[str, object] = {
        **envelope_values,
        "revision_schema_version": REVISION_SCHEMA_VERSION,
        "raw_observation_id": raw.raw_observation_id,
        "revision_sequence": revision_sequence,
        "predecessor_revision_record_id": predecessor_id,
    }
    revision_hash = revision_content_sha256(revision_values)
    revision = ObservationRevisionDraft.model_validate(
        {
            **revision_values,
            "revision_record_id": revision_id_from_sha256(revision_hash),
            "revision_content_sha256": revision_hash,
        }
    )

    payload = _resolve_payload(record, built)
    normalized_values: dict[str, object] = {
        **envelope_values,
        "raw_observation_id": raw.raw_observation_id,
        "observation_revision_id": revision.revision_record_id,
        "payload": payload,
    }
    normalized_hash = normalized_observation_content_sha256(normalized_values)
    normalized = NormalizedObservationDraft.model_validate(
        {
            **normalized_values,
            "normalized_observation_id": normalized_observation_id_from_sha256(normalized_hash),
            "normalized_content_sha256": normalized_hash,
        }
    )
    return raw, revision, normalized


def build_synthetic_results(
    record_definitions: tuple[dict[str, object], ...] | None = None,
) -> dict[DataCapability, AdapterAvailableResult]:
    """Build every capability from frozen definitions without time or network dependencies."""

    fixture = _read_fixture()
    if fixture.get("fixture_set_version") != SYNTHETIC_FIXTURE_SET_VERSION:
        raise ValueError("synthetic fixture set version does not match the frozen contract")
    records = load_fixture_records() if record_definitions is None else deepcopy(record_definitions)
    grouped_raw: dict[DataCapability, list[RawObservationDraft]] = {
        capability: [] for capability in DataCapability
    }
    grouped_revisions: dict[DataCapability, list[ObservationRevisionDraft]] = {
        capability: [] for capability in DataCapability
    }
    grouped_normalized: dict[DataCapability, list[NormalizedObservationDraft]] = {
        capability: [] for capability in DataCapability
    }
    built: dict[str, NormalizedObservationDraft] = {}

    for record in records:
        alias = _required_str(record, "alias")
        if alias in built:
            raise ValueError("synthetic fixture aliases must be unique")
        capability = DataCapability(_required_str(record, "capability"))
        raw, revision, normalized = _build_record(record, fixture=fixture, built=built)
        grouped_raw[capability].append(raw)
        grouped_revisions[capability].append(revision)
        grouped_normalized[capability].append(normalized)
        built[alias] = normalized

    return {
        capability: AdapterAvailableResult(
            profile=SYNTHETIC_ADAPTER_PROFILE,
            capability=capability,
            batch=AdapterBatchDraft(
                raw_observations=tuple(grouped_raw[capability]),
                revisions=tuple(grouped_revisions[capability]),
                normalized_observations=tuple(grouped_normalized[capability]),
                quality_findings=(),
            ),
        )
        for capability in DataCapability
    }


def mapping_bound_record_definitions(
    mapping: AuthorizedMappingIdentity,
) -> tuple[dict[str, object], ...]:
    """Bind synthetic official metadata to exact server-resolved Family C evidence.

    The committed fixture retains a stable placeholder UUID for standalone contract tests.  A
    persisted Family C mapping instead receives one deterministic synthetic metadata record for
    each exact official source-version identity carried by that mapping.  No client value is used.
    """

    records = list(load_fixture_records())
    if mapping.canonical_family is not CanonicalFamily.C_OFFICIAL_EVENT_TEXT_OVERLAY:
        return tuple(records)

    official_records = [
        item
        for item in records
        if item.get("capability") == DataCapability.OFFICIAL_DOCUMENT_EVENT_METADATA.value
    ]
    if len(official_records) != 1:
        raise ValueError("synthetic fixture must contain exactly one official metadata template")
    template = official_records[0]
    records.remove(template)
    for source_version_id in mapping.official_corroboration_source_version_ids:
        suffix = source_version_id.hex
        record = deepcopy(template)
        accession_id = f"synthetic-accession-{suffix}"
        record.update(
            {
                "alias": f"official_document_{suffix}",
                "source_record_id": f"synthetic-official-document-{suffix}",
                "logical_key": {"accession_id": accession_id},
                "revision_id": f"official-document-{suffix}-r1",
                "vintage_id": f"official-document-{suffix}-v1",
            }
        )
        payload = record.get("payload")
        if not isinstance(payload, dict):
            raise ValueError("synthetic official metadata payload must be an object")
        payload.update(
            {
                "official_document_id": f"synthetic-document-{suffix}",
                "official_event_id": f"synthetic-event-{suffix}",
                "official_source_version_id": str(source_version_id),
                "accession_id": accession_id,
                "document_content_sha256": hashlib.sha256(
                    f"phase4-synthetic-official-content:{source_version_id}".encode()
                ).hexdigest(),
            }
        )
        records.append(record)
    return tuple(records)


class SyntheticPointInTimeAdapter:
    """A deterministic adapter whose only input is a versioned local fixture set."""

    __slots__ = ("_results",)

    def __init__(
        self,
        record_definitions: tuple[dict[str, object], ...] | None = None,
    ) -> None:
        self._results = build_synthetic_results(record_definitions)

    @classmethod
    def for_mapping(cls, mapping: AuthorizedMappingIdentity) -> SyntheticPointInTimeAdapter:
        return cls(mapping_bound_record_definitions(mapping))

    @property
    def profile(self) -> AdapterProfile:
        return SYNTHETIC_ADAPTER_PROFILE

    def fetch(self, capability: DataCapability) -> AdapterAvailableResult:
        return self._results[capability]

    def all_results(self) -> tuple[AdapterAvailableResult, ...]:
        return tuple(self._results[capability] for capability in DataCapability)


__all__ = [
    "SCHEMA_ID_BY_RECORD_TYPE",
    "SCHEMA_VERSION_BY_RECORD_TYPE",
    "SYNTHETIC_ADAPTER_PROFILE",
    "SYNTHETIC_MOCK_CONFIGURATION",
    "SyntheticPointInTimeAdapter",
    "build_synthetic_results",
    "fixture_set_sha256",
    "load_fixture_records",
    "mapping_bound_record_definitions",
]
