from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from enum import StrEnum
from types import MappingProxyType
from typing import Annotated, ClassVar, Final, Literal, Self
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fable5_mapping.models import CanonicalFamily, ResearchVerdict
from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    StringConstraints,
    field_validator,
    model_validator,
)

from fable5_data.canonical import (
    CANONICAL_JSON_VERSION,
    CONFIGURATION_HASH_DOMAIN,
    SNAPSHOT_HASH_DOMAIN,
    canonical_json_bytes,
    domain_sha256,
    logical_record_id_from_sha256,
    normalized_observation_content_sha256,
    normalized_observation_id_from_sha256,
    quality_finding_id_from_sha256,
    quality_finding_sha256,
    raw_observation_content_sha256,
    raw_observation_id_from_sha256,
    raw_payload_sha256,
    request_fingerprint_sha256,
    revision_content_sha256,
    revision_id_from_sha256,
    snapshot_id_from_sha256,
)

SNAPSHOT_SCHEMA_VERSION: Final = "phase4-data-snapshot-v1"
RAW_OBSERVATION_SCHEMA_VERSION: Final = "phase4-raw-observation-v1"
NORMALIZED_OBSERVATION_SCHEMA_VERSION: Final = "phase4-normalized-observation-v1"
REVISION_SCHEMA_VERSION: Final = "phase4-observation-revision-v1"
QUALITY_RULE_SET_VERSION: Final = "phase4-data-quality-v1"
REQUEST_FINGERPRINT_VERSION: Final = "phase4-request-fingerprint-v1"
SYNTHETIC_ADAPTER_VERSION: Final = "phase4-synthetic-pit-adapter-v1"
SYNTHETIC_FIXTURE_SET_VERSION: Final = "phase4-synthetic-pit-fixtures-v1"
DATE_ONLY_AVAILABILITY_CONVENTION: Final = "phase4-date-only-next-day-v1"
SYNTHETIC_USE_RIGHTS_ID: Final = "phase4-synthetic-test-fixture-rights-v1"

INSTRUMENT_IDENTITY_SCHEMA_VERSION = "phase4-instrument-identity-v1"
LISTING_IDENTITY_SCHEMA_VERSION = "phase4-listing-identity-v1"
UNIVERSE_MEMBERSHIP_SCHEMA_VERSION = "phase4-universe-membership-v1"
OHLCV_BAR_SCHEMA_VERSION = "phase4-ohlcv-bar-v1"
CORPORATE_ACTION_SCHEMA_VERSION = "phase4-corporate-action-v1"
DELISTING_EVENT_SCHEMA_VERSION = "phase4-delisting-event-v1"
AS_REPORTED_FUNDAMENTAL_SCHEMA_VERSION = "phase4-as-reported-fundamental-v1"
CALENDAR_SESSION_SCHEMA_VERSION = "phase4-calendar-session-v1"
OFFICIAL_DOCUMENT_EVENT_SCHEMA_VERSION = "phase4-official-document-event-v1"
VOLATILITY_RETURN_INPUT_SCHEMA_VERSION = "phase4-volatility-return-input-v1"

# Phase 6 extends the normalized Phase 4 source boundary without changing any frozen
# Phase 4 envelope, identity, or hash domain.  These payload schemas remain source
# evidence only; they contain no feature, label, signal, model, or promotion output.
PHASE6_DATA_CONTRACT_VERSION: Final = "phase6-data-contract-prerequisites-v2"
PHASE6_DATA_QUALITY_RULE_SET_VERSION: Final = "phase6-data-contract-quality-v2"
SECTOR_CLASSIFICATION_SCHEMA_VERSION: Final = "phase6-sector-classification-v1"
OFFICIAL_DOCUMENT_CONTENT_SCHEMA_VERSION: Final = "phase6-official-document-content-v1"
SOCIAL_ATTENTION_SCHEMA_VERSION: Final = "phase6-social-attention-v1"
MACRO_RATE_OBSERVATION_SCHEMA_VERSION: Final = "phase6-macro-rate-observation-v1"
CRISIS_WINDOW_DEFINITION_SCHEMA_VERSION: Final = "phase6-crisis-window-definition-v1"
PHASE6_SYNTHETIC_ADAPTER_VERSION: Final = "phase6-synthetic-pit-adapter-v2"
PHASE6_SYNTHETIC_FIXTURE_SET_VERSION: Final = "phase6-synthetic-pit-fixtures-v2"
SyntheticFixtureSetVersion = Literal[
    "phase4-synthetic-pit-fixtures-v1",
    "phase6-synthetic-pit-fixtures-v1",
    "phase6-synthetic-pit-fixtures-v2",
]


def _identifier(value: str) -> str:
    forbidden = {"unknown", "n/a", "na", "null", "none", "undefined"}
    if value != value.strip() or not value.strip():
        raise ValueError("identifier must be nonblank and trimmed")
    if value.casefold() in forbidden:
        raise ValueError("sentinel strings are not valid identifiers")
    return value


def _timezone(value: str) -> str:
    value = _identifier(value)
    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError as exc:
        raise ValueError("source_timezone must be a valid IANA timezone") from exc
    return value


def _document_text(value: str) -> str:
    if not value.strip():
        raise ValueError("document_text must contain non-whitespace text")
    if "\x00" in value:
        raise ValueError("document_text cannot contain NUL characters")
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise ValueError("document_text must be valid UTF-8 text") from exc
    return value


Identifier = Annotated[
    str,
    StringConstraints(min_length=1, max_length=256),
    AfterValidator(_identifier),
]
IanaTimezone = Annotated[str, AfterValidator(_timezone)]
SHA256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
CurrencyCode = Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}$")]
CountryCode = Annotated[str, StringConstraints(pattern=r"^[A-Z]{2}$")]
ExchangeMic = Annotated[str, StringConstraints(pattern=r"^[A-Z0-9]{4}$")]
DocumentText = Annotated[
    str,
    StringConstraints(min_length=1, max_length=5_000_000),
    AfterValidator(_document_text),
]


def official_document_content_sha256(document_text: str) -> str:
    """Hash the exact UTF-8 document text represented by a content payload."""

    validated = _document_text(document_text)
    return hashlib.sha256(validated.encode("utf-8", errors="strict")).hexdigest()


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(UTC)


def conservative_date_available_at(source_date: date, source_timezone: str) -> datetime:
    try:
        timezone = ZoneInfo(source_timezone)
    except ZoneInfoNotFoundError as exc:
        raise ValueError("source_timezone must be a valid IANA timezone") from exc
    next_day = source_date + timedelta(days=1)
    return datetime.combine(next_day, time.min, tzinfo=timezone).astimezone(UTC)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class DataCapability(StrEnum):
    SECURITY_MASTER = "security_master"
    UNIVERSE_MEMBERSHIP = "universe_membership"
    OHLCV = "ohlcv"
    CORPORATE_ACTIONS = "corporate_actions"
    DELISTINGS = "delistings"
    AS_REPORTED_FUNDAMENTALS = "as_reported_fundamentals"
    TRADING_CALENDAR = "trading_calendar"
    VOLATILITY_RETURN_INPUTS = "volatility_return_inputs"
    OFFICIAL_DOCUMENT_EVENT_METADATA = "official_document_event_metadata"
    MACRO_REGIME_INPUTS = "macro_regime_inputs"


PHASE4_DATA_CAPABILITIES: Final = tuple(
    item for item in DataCapability if item is not DataCapability.MACRO_REGIME_INPUTS
)


PHASE4_AUTHORIZED_CAPABILITIES = MappingProxyType(
    {
        CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING: frozenset(
            {
                DataCapability.SECURITY_MASTER,
                DataCapability.UNIVERSE_MEMBERSHIP,
                DataCapability.OHLCV,
                DataCapability.CORPORATE_ACTIONS,
                DataCapability.DELISTINGS,
                DataCapability.AS_REPORTED_FUNDAMENTALS,
            }
        ),
        CanonicalFamily.B_TIME_SERIES_MOMENTUM_REGIME: frozenset(
            {
                DataCapability.OHLCV,
                DataCapability.CORPORATE_ACTIONS,
                DataCapability.DELISTINGS,
                DataCapability.TRADING_CALENDAR,
                DataCapability.VOLATILITY_RETURN_INPUTS,
            }
        ),
        CanonicalFamily.C_OFFICIAL_EVENT_TEXT_OVERLAY: frozenset(
            {DataCapability.OFFICIAL_DOCUMENT_EVENT_METADATA}
        ),
    }
)


AUTHORIZED_CAPABILITIES = MappingProxyType(
    {
        CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING: frozenset(
            {
                *PHASE4_AUTHORIZED_CAPABILITIES[CanonicalFamily.A_CROSS_SECTIONAL_EQUITY_RANKING],
                DataCapability.MACRO_REGIME_INPUTS,
            }
        ),
        CanonicalFamily.B_TIME_SERIES_MOMENTUM_REGIME: frozenset(
            {
                DataCapability.SECURITY_MASTER,
                DataCapability.UNIVERSE_MEMBERSHIP,
                DataCapability.OHLCV,
                DataCapability.CORPORATE_ACTIONS,
                DataCapability.DELISTINGS,
                DataCapability.TRADING_CALENDAR,
                DataCapability.VOLATILITY_RETURN_INPUTS,
            }
        ),
        CanonicalFamily.C_OFFICIAL_EVENT_TEXT_OVERLAY: frozenset(
            {
                DataCapability.SECURITY_MASTER,
                DataCapability.UNIVERSE_MEMBERSHIP,
                DataCapability.OHLCV,
                DataCapability.OFFICIAL_DOCUMENT_EVENT_METADATA,
            }
        ),
    }
)


class DataRecordType(StrEnum):
    INSTRUMENT_IDENTITY = "instrument_identity"
    LISTING_IDENTITY = "listing_identity"
    UNIVERSE_MEMBERSHIP = "universe_membership"
    OHLCV_BAR = "ohlcv_bar"
    CORPORATE_ACTION = "corporate_action"
    DELISTING_EVENT = "delisting_event"
    AS_REPORTED_FUNDAMENTAL = "as_reported_fundamental"
    CALENDAR_SESSION = "calendar_session"
    OFFICIAL_DOCUMENT_EVENT = "official_document_event"
    VOLATILITY_RETURN_INPUT = "volatility_return_input"
    SECTOR_CLASSIFICATION = "sector_classification"
    OFFICIAL_DOCUMENT_CONTENT = "official_document_content"
    SOCIAL_ATTENTION = "social_attention"
    MACRO_RATE_OBSERVATION = "macro_rate_observation"
    CRISIS_WINDOW_DEFINITION = "crisis_window_definition"


PHASE4_CAPABILITY_RECORD_TYPES = MappingProxyType(
    {
        DataCapability.SECURITY_MASTER: frozenset(
            {DataRecordType.INSTRUMENT_IDENTITY, DataRecordType.LISTING_IDENTITY}
        ),
        DataCapability.UNIVERSE_MEMBERSHIP: frozenset({DataRecordType.UNIVERSE_MEMBERSHIP}),
        DataCapability.OHLCV: frozenset({DataRecordType.OHLCV_BAR}),
        DataCapability.CORPORATE_ACTIONS: frozenset({DataRecordType.CORPORATE_ACTION}),
        DataCapability.DELISTINGS: frozenset({DataRecordType.DELISTING_EVENT}),
        DataCapability.AS_REPORTED_FUNDAMENTALS: frozenset(
            {DataRecordType.AS_REPORTED_FUNDAMENTAL}
        ),
        DataCapability.TRADING_CALENDAR: frozenset({DataRecordType.CALENDAR_SESSION}),
        DataCapability.VOLATILITY_RETURN_INPUTS: frozenset(
            {DataRecordType.VOLATILITY_RETURN_INPUT}
        ),
        DataCapability.OFFICIAL_DOCUMENT_EVENT_METADATA: frozenset(
            {DataRecordType.OFFICIAL_DOCUMENT_EVENT}
        ),
    }
)


CAPABILITY_RECORD_TYPES = MappingProxyType(
    {
        DataCapability.SECURITY_MASTER: frozenset(
            {
                DataRecordType.INSTRUMENT_IDENTITY,
                DataRecordType.LISTING_IDENTITY,
                DataRecordType.SECTOR_CLASSIFICATION,
            }
        ),
        DataCapability.UNIVERSE_MEMBERSHIP: frozenset({DataRecordType.UNIVERSE_MEMBERSHIP}),
        DataCapability.OHLCV: frozenset({DataRecordType.OHLCV_BAR}),
        DataCapability.CORPORATE_ACTIONS: frozenset({DataRecordType.CORPORATE_ACTION}),
        DataCapability.DELISTINGS: frozenset({DataRecordType.DELISTING_EVENT}),
        DataCapability.AS_REPORTED_FUNDAMENTALS: frozenset(
            {DataRecordType.AS_REPORTED_FUNDAMENTAL}
        ),
        DataCapability.TRADING_CALENDAR: frozenset({DataRecordType.CALENDAR_SESSION}),
        DataCapability.VOLATILITY_RETURN_INPUTS: frozenset(
            {DataRecordType.VOLATILITY_RETURN_INPUT}
        ),
        DataCapability.OFFICIAL_DOCUMENT_EVENT_METADATA: frozenset(
            {
                DataRecordType.OFFICIAL_DOCUMENT_EVENT,
                DataRecordType.OFFICIAL_DOCUMENT_CONTENT,
                DataRecordType.SOCIAL_ATTENTION,
            }
        ),
        DataCapability.MACRO_REGIME_INPUTS: frozenset(
            {
                DataRecordType.MACRO_RATE_OBSERVATION,
                DataRecordType.CRISIS_WINDOW_DEFINITION,
            }
        ),
    }
)


class MissingnessReason(StrEnum):
    NOT_APPLICABLE = "not_applicable"
    NOT_PROVIDED_BY_SOURCE = "not_provided_by_source"
    NOT_YET_AVAILABLE_AS_OF = "not_yet_available_as_of"
    ENTITLEMENT_RESTRICTED = "entitlement_restricted"
    UNRESOLVED_IDENTITY = "unresolved_identity"
    DELISTING_RETURN_NOT_PROVIDED = "delisting_return_not_provided"
    PROVIDER_RETURN_ALREADY_INCLUDES_DELISTING = "provider_return_already_includes_delisting"


class FieldMissingness(StrictModel):
    field_name: Identifier
    reason: MissingnessReason
    source_detail_code: Identifier | None = None


class QualityFlag(StrEnum):
    SYNTHETIC_FIXTURE = "synthetic_fixture"
    DATE_ONLY_CONVENTION_APPLIED = "date_only_convention_applied"
    FUTURE_AVAILABILITY_EXCLUDED = "future_availability_excluded"
    REVISION_REPLAYED_AS_OF = "revision_replayed_as_of"
    NEAR_DUPLICATE_RETAINED = "near_duplicate_retained"


class DataQualitySeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    BLOCKING = "blocking"


class DataQualityCode(StrEnum):
    SYNTHETIC_FIXTURE = "synthetic_fixture"
    DATE_ONLY_CONVENTION_APPLIED = "date_only_convention_applied"
    FUTURE_AVAILABILITY_EXCLUDED = "future_availability_excluded"
    NEAR_DUPLICATE_RETAINED = "near_duplicate_retained"
    EXACT_DUPLICATE_KEY = "exact_duplicate_key"
    REQUIRED_FIELD_MISSING = "required_field_missing"
    INVALID_ENUM_VALUE = "invalid_enum_value"
    INVALID_TIMESTAMP_ORDER = "invalid_timestamp_order"
    ORPHAN_REFERENCE = "orphan_reference"
    RAW_NORMALIZED_LINEAGE_GAP = "raw_normalized_lineage_gap"
    UNIT_CURRENCY_CALENDAR_TIMEZONE_MISMATCH = "unit_currency_calendar_timezone_mismatch"
    SCHEMA_DRIFT = "schema_drift"
    CURRENT_UNIVERSE_LEAKAGE = "current_universe_leakage"
    RESTATEMENT_LEAKAGE = "restatement_leakage"
    CORPORATE_ACTION_LOOKAHEAD = "corporate_action_lookahead"
    MISSING_DELISTING_RETURN = "missing_delisting_return"
    FUTURE_AVAILABILITY_INCLUDED = "future_availability_included"
    UNNORMALIZED_REJECTED = "unnormalized_rejected"
    PIT_CLASSIFICATION_INVALID = "pit_classification_invalid"
    DOCUMENT_CONTENT_HASH_MISMATCH = "document_content_hash_mismatch"
    DOCUMENT_CORRECTION_TIMING_INVALID = "document_correction_timing_invalid"
    OFFICIAL_CORROBORATION_MISMATCH = "official_corroboration_mismatch"


class ConstituentDisposition(StrEnum):
    INCLUDED_AS_OF = "included_as_of"
    RETAINED_HISTORICAL_VINTAGE = "retained_historical_vintage"
    EXPLICIT_MISSINGNESS = "explicit_missingness"


class FindingDisposition(StrEnum):
    RETAINED = "retained"
    EXCLUDED = "excluded"
    BLOCKED = "blocked"


class SnapshotQualityStatus(StrEnum):
    DATA_QUALITY_ACCEPTED = "data_quality_accepted"
    DATA_QUALITY_ACCEPTED_WITH_WARNINGS = "data_quality_accepted_with_warnings"


PHASE4_SCHEMA_CONSTANTS = MappingProxyType(
    {
        "canonicalization_version": CANONICAL_JSON_VERSION,
        "snapshot_schema_version": SNAPSHOT_SCHEMA_VERSION,
        "raw_observation_schema_version": RAW_OBSERVATION_SCHEMA_VERSION,
        "normalized_observation_schema_version": NORMALIZED_OBSERVATION_SCHEMA_VERSION,
        "revision_schema_version": REVISION_SCHEMA_VERSION,
        "quality_rule_set_version": QUALITY_RULE_SET_VERSION,
        "request_fingerprint_version": REQUEST_FINGERPRINT_VERSION,
        "date_only_availability_convention": DATE_ONLY_AVAILABILITY_CONVENTION,
        "capabilities": tuple(item.value for item in PHASE4_DATA_CAPABILITIES),
        "record_types": tuple(
            item.value
            for item in (
                DataRecordType.INSTRUMENT_IDENTITY,
                DataRecordType.LISTING_IDENTITY,
                DataRecordType.UNIVERSE_MEMBERSHIP,
                DataRecordType.OHLCV_BAR,
                DataRecordType.CORPORATE_ACTION,
                DataRecordType.DELISTING_EVENT,
                DataRecordType.AS_REPORTED_FUNDAMENTAL,
                DataRecordType.CALENDAR_SESSION,
                DataRecordType.OFFICIAL_DOCUMENT_EVENT,
                DataRecordType.VOLATILITY_RETURN_INPUT,
            )
        ),
        "constituent_dispositions": tuple(item.value for item in ConstituentDisposition),
        "finding_dispositions": tuple(item.value for item in FindingDisposition),
        "quality_severities": tuple(item.value for item in DataQualitySeverity),
        "snapshot_quality_statuses": tuple(item.value for item in SnapshotQualityStatus),
    }
)


PHASE6_DATA_CONTRACT_CONSTANTS = MappingProxyType(
    {
        "contract_version": PHASE6_DATA_CONTRACT_VERSION,
        "quality_rule_set_version": PHASE6_DATA_QUALITY_RULE_SET_VERSION,
        "additive_record_types": (
            DataRecordType.SECTOR_CLASSIFICATION.value,
            DataRecordType.OFFICIAL_DOCUMENT_CONTENT.value,
            DataRecordType.SOCIAL_ATTENTION.value,
            DataRecordType.MACRO_RATE_OBSERVATION.value,
            DataRecordType.CRISIS_WINDOW_DEFINITION.value,
        ),
        "additive_schema_versions": (
            (
                DataRecordType.SECTOR_CLASSIFICATION.value,
                SECTOR_CLASSIFICATION_SCHEMA_VERSION,
            ),
            (
                DataRecordType.OFFICIAL_DOCUMENT_CONTENT.value,
                OFFICIAL_DOCUMENT_CONTENT_SCHEMA_VERSION,
            ),
            (
                DataRecordType.SOCIAL_ATTENTION.value,
                SOCIAL_ATTENTION_SCHEMA_VERSION,
            ),
            (
                DataRecordType.MACRO_RATE_OBSERVATION.value,
                MACRO_RATE_OBSERVATION_SCHEMA_VERSION,
            ),
            (
                DataRecordType.CRISIS_WINDOW_DEFINITION.value,
                CRISIS_WINDOW_DEFINITION_SCHEMA_VERSION,
            ),
        ),
        "capability_record_type_additions": (
            (
                DataCapability.SECURITY_MASTER.value,
                DataRecordType.SECTOR_CLASSIFICATION.value,
            ),
            (
                DataCapability.OFFICIAL_DOCUMENT_EVENT_METADATA.value,
                DataRecordType.OFFICIAL_DOCUMENT_CONTENT.value,
            ),
            (
                DataCapability.OFFICIAL_DOCUMENT_EVENT_METADATA.value,
                DataRecordType.SOCIAL_ATTENTION.value,
            ),
            (
                DataCapability.MACRO_REGIME_INPUTS.value,
                DataRecordType.MACRO_RATE_OBSERVATION.value,
            ),
            (
                DataCapability.MACRO_REGIME_INPUTS.value,
                DataRecordType.CRISIS_WINDOW_DEFINITION.value,
            ),
        ),
        "family_a_capability_additions": (DataCapability.MACRO_REGIME_INPUTS.value,),
        "family_b_capability_additions": (
            DataCapability.SECURITY_MASTER.value,
            DataCapability.UNIVERSE_MEMBERSHIP.value,
        ),
        "family_c_capability_additions": (
            DataCapability.SECURITY_MASTER.value,
            DataCapability.UNIVERSE_MEMBERSHIP.value,
            DataCapability.OHLCV.value,
        ),
        "additive_quality_codes": (
            DataQualityCode.PIT_CLASSIFICATION_INVALID.value,
            DataQualityCode.DOCUMENT_CONTENT_HASH_MISMATCH.value,
            DataQualityCode.DOCUMENT_CORRECTION_TIMING_INVALID.value,
            DataQualityCode.OFFICIAL_CORROBORATION_MISMATCH.value,
        ),
        "synthetic_adapter_version": PHASE6_SYNTHETIC_ADAPTER_VERSION,
        "synthetic_fixture_set_version": PHASE6_SYNTHETIC_FIXTURE_SET_VERSION,
    }
)


class AvailabilityPrecision(StrEnum):
    TIMESTAMP = "timestamp"
    DATE = "date"


class AvailabilityConvention(StrEnum):
    SOURCE_TIMESTAMP = "source_timestamp"
    DATE_ONLY_NEXT_DAY = DATE_ONLY_AVAILABILITY_CONVENTION


class UseRightsScope(StrEnum):
    INTERNAL_TEST_FIXTURE_ONLY = "internal_test_fixture_only"
    INTERNAL_RESEARCH_ONLY = "internal_research_only"


class UseRightsIdentity(StrictModel):
    entitlement_id: Identifier
    use_rights_id: Identifier
    scope: UseRightsScope
    storage_allowed: bool
    display_allowed: bool
    non_display_allowed: bool
    derived_data_allowed: bool
    redistribution_allowed: bool

    @model_validator(mode="after")
    def require_snapshot_storage_rights(self) -> Self:
        if not self.storage_allowed:
            raise ValueError("Phase 4 snapshot use rights must permit storage")
        return self


class SchemaBinding(StrictModel):
    dataset_schema_id: Identifier
    dataset_schema_version: Identifier


class AdapterProfile(StrictModel):
    provider_id: Identifier
    adapter_id: Identifier
    adapter_version: Identifier
    dataset_id: Identifier
    product_id: Identifier
    synthetic: bool
    capabilities: tuple[DataCapability, ...]
    schema_bindings: tuple[SchemaBinding, ...]
    use_rights: UseRightsIdentity

    @model_validator(mode="after")
    def validate_unique_sorted_values(self) -> Self:
        if len(self.capabilities) != len(set(self.capabilities)):
            raise ValueError("adapter capabilities must be unique")
        if tuple(sorted(self.capabilities, key=str)) != self.capabilities:
            raise ValueError("adapter capabilities must be canonically sorted")
        schema_keys = [
            (item.dataset_schema_id, item.dataset_schema_version) for item in self.schema_bindings
        ]
        if len(schema_keys) != len(set(schema_keys)):
            raise ValueError("adapter schema bindings must be unique")
        if tuple(sorted(schema_keys)) != tuple(schema_keys):
            raise ValueError("adapter schema bindings must be canonically sorted")
        return self


class AuthorizedMappingIdentity(StrictModel):
    mapping_id: UUID
    mapping_version: int = Field(ge=1)
    mapping_input_sha256: SHA256
    mapper_rule_set_version: Identifier
    mapper_rule_set_sha256: SHA256
    canonical_family: CanonicalFamily
    verdict: ResearchVerdict
    official_corroboration_source_version_ids: tuple[UUID, ...] = ()

    @model_validator(mode="after")
    def validate_authorized_mapping(self) -> Self:
        if self.verdict is not ResearchVerdict.BUILD_RESEARCH:
            raise ValueError("Phase 4 requires a persisted BUILD_RESEARCH mapping")
        if self.canonical_family not in AUTHORIZED_CAPABILITIES:
            raise ValueError("Phase 4 is limited to authorized canonical families A, B, and C")
        if self.canonical_family is CanonicalFamily.C_OFFICIAL_EVENT_TEXT_OVERLAY:
            if not self.official_corroboration_source_version_ids:
                raise ValueError("Family C requires exact official corroboration versions")
        if len(self.official_corroboration_source_version_ids) != len(
            set(self.official_corroboration_source_version_ids)
        ):
            raise ValueError("official corroboration version identities must be unique")
        if tuple(sorted(self.official_corroboration_source_version_ids, key=str)) != (
            self.official_corroboration_source_version_ids
        ):
            raise ValueError("official corroboration version identities must be sorted")
        return self


class SnapshotCreateRequest(StrictModel):
    mapping_id: UUID
    as_of_utc: datetime
    capability: DataCapability
    mock_configuration_id: Identifier

    @field_validator("as_of_utc")
    @classmethod
    def normalize_as_of(cls, value: datetime) -> datetime:
        return _utc(value)


class SnapshotRequestParameters(StrictModel):
    mapping: AuthorizedMappingIdentity
    as_of_utc: datetime
    capability: DataCapability
    mock_configuration_id: Identifier

    @field_validator("as_of_utc")
    @classmethod
    def normalize_as_of(cls, value: datetime) -> datetime:
        return _utc(value)

    @model_validator(mode="after")
    def validate_capability(self) -> Self:
        if self.capability not in AUTHORIZED_CAPABILITIES[self.mapping.canonical_family]:
            raise ValueError("capability is not authorized for the persisted mapping family")
        return self


class MockConfigurationIdentity(StrictModel):
    configuration_id: Identifier
    configuration_sha256: SHA256
    fixture_set_version: SyntheticFixtureSetVersion = SYNTHETIC_FIXTURE_SET_VERSION


class RequestFingerprintInput(StrictModel):
    fingerprint_version: Literal["phase4-request-fingerprint-v1"] = REQUEST_FINGERPRINT_VERSION
    snapshot_schema_version: Literal["phase4-data-snapshot-v1"] = SNAPSHOT_SCHEMA_VERSION
    canonicalization_version: Literal["phase4-canonical-json-v1"] = CANONICAL_JSON_VERSION
    date_only_availability_convention: Literal["phase4-date-only-next-day-v1"] = (
        DATE_ONLY_AVAILABILITY_CONVENTION
    )
    request: SnapshotRequestParameters
    adapter: AdapterProfile
    schema_bindings: tuple[SchemaBinding, ...]
    use_rights: UseRightsIdentity
    configuration: MockConfigurationIdentity

    @model_validator(mode="after")
    def validate_server_resolved_inputs(self) -> Self:
        if self.request.mock_configuration_id != self.configuration.configuration_id:
            raise ValueError("request fingerprint configuration identity must match request")
        if self.schema_bindings != self.adapter.schema_bindings:
            raise ValueError("request fingerprint schemas must match adapter profile")
        if self.use_rights != self.adapter.use_rights:
            raise ValueError("request fingerprint use rights must match adapter profile")
        if self.request.capability not in self.adapter.capabilities:
            raise ValueError("request fingerprint capability must be declared by adapter")
        return self

    def sha256(self) -> str:
        return request_fingerprint_sha256(self)


class ObservationEnvelopeDraft(StrictModel):
    envelope_schema_version: Literal[
        "phase4-raw-observation-v1", "phase4-normalized-observation-v1"
    ]
    logical_record_id: Identifier
    logical_record_key_sha256: SHA256
    provider_id: Identifier
    adapter_id: Identifier
    adapter_version: Identifier
    dataset_id: Identifier
    product_id: Identifier
    dataset_schema_id: Identifier
    dataset_schema_version: Identifier
    entitlement_id: Identifier
    use_rights_id: Identifier
    source_record_id: Identifier
    instrument_id: UUID | None
    listing_id: UUID | None
    event_time: datetime
    available_at: datetime
    retrieved_at: datetime | None
    valid_from: datetime
    valid_to: datetime | None
    revision_id: Identifier
    vintage_id: Identifier
    source_timezone: IanaTimezone
    calendar_id: Identifier | None
    unit: Identifier | None
    currency: CurrencyCode | None
    availability_precision: AvailabilityPrecision
    availability_convention: AvailabilityConvention
    availability_source_date: date | None = None
    quality_flags: tuple[QualityFlag, ...] = ()
    field_missingness: tuple[FieldMissingness, ...] = ()
    raw_payload_sha256: SHA256

    @field_validator("event_time", "available_at", "retrieved_at", "valid_from", "valid_to")
    @classmethod
    def normalize_timestamps(cls, value: datetime | None) -> datetime | None:
        return None if value is None else _utc(value)

    @model_validator(mode="after")
    def validate_temporal_and_missingness_contract(self) -> Self:
        expected_logical_id = str(logical_record_id_from_sha256(self.logical_record_key_sha256))
        if self.logical_record_id != expected_logical_id:
            raise ValueError("logical_record_id must derive from logical_record_key_sha256")
        if self.retrieved_at is not None and self.retrieved_at < self.available_at:
            raise ValueError("retrieved_at must be at or after available_at")
        if self.valid_to is not None and self.valid_to <= self.valid_from:
            raise ValueError("valid_to must be after valid_from")
        if self.availability_precision is AvailabilityPrecision.DATE:
            if self.availability_convention is not AvailabilityConvention.DATE_ONLY_NEXT_DAY:
                raise ValueError("date-only availability requires the frozen next-day convention")
            if self.availability_source_date is None:
                raise ValueError("date-only availability requires availability_source_date")
            expected = conservative_date_available_at(
                self.availability_source_date, self.source_timezone
            )
            if self.available_at != expected:
                raise ValueError("available_at does not match the date-only convention")
        else:
            if self.availability_convention is not AvailabilityConvention.SOURCE_TIMESTAMP:
                raise ValueError("timestamp precision requires source_timestamp convention")
            if self.availability_source_date is not None:
                raise ValueError("timestamp precision cannot carry availability_source_date")

        missing_names = [item.field_name for item in self.field_missingness]
        if len(missing_names) != len(set(missing_names)):
            raise ValueError("field missingness entries must be unique by field name")
        optional_values = {
            "retrieved_at": self.retrieved_at,
            "instrument_id": self.instrument_id,
            "listing_id": self.listing_id,
            "valid_to": self.valid_to,
            "calendar_id": self.calendar_id,
            "unit": self.unit,
            "currency": self.currency,
        }
        missing_set = set(missing_names)
        for field_name, value in optional_values.items():
            if value is None and field_name not in missing_set:
                raise ValueError(f"{field_name} null requires an explicit missingness reason")
            if value is not None and field_name in missing_set:
                raise ValueError(f"{field_name} cannot be populated and marked missing")
        if len(self.quality_flags) != len(set(self.quality_flags)):
            raise ValueError("quality flags must be unique")
        return self

    def missingness_reason(self, field_name: str) -> MissingnessReason | None:
        for item in self.field_missingness:
            if item.field_name == field_name:
                return item.reason
        return None


class InstrumentType(StrEnum):
    COMMON_STOCK = "common_stock"
    ETF = "etf"


class InstrumentIdentityPayload(StrictModel):
    record_type: Literal["instrument_identity"] = "instrument_identity"
    instrument_type: InstrumentType
    issuer_id: Identifier
    legal_name: Identifier
    country_code: CountryCode
    share_class_id: Identifier


class ListingStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DELISTED = "delisted"


class ListingIdentityPayload(StrictModel):
    record_type: Literal["listing_identity"] = "listing_identity"
    symbol: Identifier
    exchange_mic: ExchangeMic
    status: ListingStatus
    primary_listing: bool


class MembershipStatus(StrEnum):
    INCLUDED = "included"
    EXCLUDED = "excluded"


class UniverseMembershipPayload(StrictModel):
    record_type: Literal["universe_membership"] = "universe_membership"
    universe_id: Identifier
    status: MembershipStatus


class BarInterval(StrEnum):
    ONE_DAY = "P1D"


class AdjustmentBasis(StrEnum):
    RAW_UNADJUSTED = "raw_unadjusted"
    AS_OF_ADJUSTED = "as_of_adjusted"


class OhlcvBarPayload(StrictModel):
    record_type: Literal["ohlcv_bar"] = "ohlcv_bar"
    bar_interval: BarInterval
    bar_start: datetime
    bar_end: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal = Field(ge=0)
    volume_unit: Literal["shares"] = "shares"
    adjustment_basis: AdjustmentBasis
    adjustment_as_of: datetime | None = None
    corporate_action_revision_ids: tuple[Identifier, ...] = ()

    @field_validator("bar_start", "bar_end", "adjustment_as_of")
    @classmethod
    def normalize_timestamps(cls, value: datetime | None) -> datetime | None:
        return None if value is None else _utc(value)

    @model_validator(mode="after")
    def validate_bar(self) -> Self:
        if self.bar_end <= self.bar_start:
            raise ValueError("bar_end must be after bar_start")
        if min(self.open, self.high, self.low, self.close) < 0:
            raise ValueError("OHLC prices cannot be negative")
        if self.high < max(self.open, self.low, self.close):
            raise ValueError("high must be at least every other OHLC price")
        if self.low > min(self.open, self.high, self.close):
            raise ValueError("low must be no greater than every other OHLC price")
        if self.adjustment_basis is AdjustmentBasis.RAW_UNADJUSTED:
            if self.adjustment_as_of is not None or self.corporate_action_revision_ids:
                raise ValueError("raw bars cannot carry adjustment knowledge")
        elif self.adjustment_as_of is None:
            raise ValueError("as-of adjusted bars require adjustment_as_of")
        if len(self.corporate_action_revision_ids) != len(set(self.corporate_action_revision_ids)):
            raise ValueError("corporate-action revision references must be unique")
        return self


class CorporateActionType(StrEnum):
    SPLIT = "split"
    CASH_DIVIDEND = "cash_dividend"
    MERGER = "merger"
    SPINOFF = "spinoff"


class CorporateActionPayload(StrictModel):
    record_type: Literal["corporate_action"] = "corporate_action"
    corporate_action_id: Identifier
    action_type: CorporateActionType
    announcement_at: datetime
    effective_at: datetime
    split_ratio: Decimal | None = None
    cash_amount: Decimal | None = None
    target_instrument_id: UUID | None = None

    @field_validator("announcement_at", "effective_at")
    @classmethod
    def normalize_timestamps(cls, value: datetime) -> datetime:
        return _utc(value)

    @model_validator(mode="after")
    def validate_action_fields(self) -> Self:
        if self.action_type is CorporateActionType.SPLIT:
            if self.split_ratio is None or self.split_ratio <= 0 or self.cash_amount is not None:
                raise ValueError("split actions require only a positive split_ratio")
        elif self.action_type is CorporateActionType.CASH_DIVIDEND:
            if self.cash_amount is None or self.cash_amount < 0 or self.split_ratio is not None:
                raise ValueError("cash dividends require only a nonnegative cash_amount")
        elif self.split_ratio is not None or self.cash_amount is not None:
            raise ValueError("merger/spinoff actions cannot use split or dividend fields")
        return self


class DelistingType(StrEnum):
    MERGER = "merger"
    BANKRUPTCY = "bankruptcy"
    LIQUIDATION = "liquidation"
    EXCHANGE_REMOVAL = "exchange_removal"
    OTHER = "other"


class DelistingReturnInclusion(StrEnum):
    SEPARATE_RETURN_REQUIRED = "separate_return_required"
    PROVIDER_TOTAL_RETURN_INCLUDES = "provider_total_return_includes"


class DelistingEventPayload(StrictModel):
    record_type: Literal["delisting_event"] = "delisting_event"
    delisting_event_id: Identifier
    delisting_type: DelistingType
    last_trade_at: datetime
    effective_at: datetime
    return_inclusion: DelistingReturnInclusion
    delisting_return: Decimal | None

    nullable_measurement_fields: ClassVar[tuple[str, ...]] = ("payload.delisting_return",)

    @field_validator("last_trade_at", "effective_at")
    @classmethod
    def normalize_timestamps(cls, value: datetime) -> datetime:
        return _utc(value)

    @model_validator(mode="after")
    def validate_delisting(self) -> Self:
        if self.effective_at < self.last_trade_at:
            raise ValueError("delisting effective time cannot precede the last trade")
        if self.delisting_return is not None and self.delisting_return < Decimal("-1"):
            raise ValueError("delisting return cannot be below -1")
        if (
            self.return_inclusion is DelistingReturnInclusion.PROVIDER_TOTAL_RETURN_INCLUDES
            and self.delisting_return is not None
        ):
            raise ValueError(
                "provider-included delisting returns cannot also be supplied separately"
            )
        return self


class FiscalPeriodType(StrEnum):
    QUARTER = "quarter"
    YEAR = "year"
    TRAILING_TWELVE_MONTHS = "trailing_twelve_months"


class AsReportedFundamentalPayload(StrictModel):
    record_type: Literal["as_reported_fundamental"] = "as_reported_fundamental"
    concept_id: Identifier
    fiscal_period_start: date
    fiscal_period_end: date
    fiscal_period_type: FiscalPeriodType
    official_document_id: Identifier
    filing_accepted_at: datetime
    as_reported: Literal[True] = True
    amendment_sequence: int = Field(ge=0)
    restates_revision_id: Identifier | None = None
    value: Decimal | None

    nullable_measurement_fields: ClassVar[tuple[str, ...]] = ("payload.value",)

    @field_validator("filing_accepted_at")
    @classmethod
    def normalize_accepted_at(cls, value: datetime) -> datetime:
        return _utc(value)

    @model_validator(mode="after")
    def validate_period_and_revision(self) -> Self:
        if self.fiscal_period_end < self.fiscal_period_start:
            raise ValueError("fiscal period end cannot precede its start")
        if self.amendment_sequence == 0 and self.restates_revision_id is not None:
            raise ValueError("an original filing cannot restate another revision")
        if self.amendment_sequence > 0 and self.restates_revision_id is None:
            raise ValueError("an amendment must identify the revision it restates")
        return self


class CalendarSessionStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"


class CalendarSessionPayload(StrictModel):
    record_type: Literal["calendar_session"] = "calendar_session"
    session_date: date
    status: CalendarSessionStatus
    open_at: datetime | None
    close_at: datetime | None
    early_close: bool

    @field_validator("open_at", "close_at")
    @classmethod
    def normalize_timestamps(cls, value: datetime | None) -> datetime | None:
        return None if value is None else _utc(value)

    @model_validator(mode="after")
    def validate_session(self) -> Self:
        if self.status is CalendarSessionStatus.OPEN:
            if self.open_at is None or self.close_at is None or self.close_at <= self.open_at:
                raise ValueError("open sessions require ordered open and close timestamps")
        elif self.open_at is not None or self.close_at is not None or self.early_close:
            raise ValueError("closed sessions cannot carry market hours")
        return self


class MacroRateObservationPayload(StrictModel):
    """Vintage-aware synthetic policy-rate input, never a signal or model decision."""

    record_type: Literal["macro_rate_observation"] = "macro_rate_observation"
    series_id: Identifier
    observation_period_end: date
    released_at: datetime
    vintage_id: Identifier
    rate_value: Decimal
    previous_rate_value: Decimal
    rate_change: Decimal

    @field_validator("released_at")
    @classmethod
    def normalize_released_at(cls, value: datetime) -> datetime:
        return _utc(value)

    @model_validator(mode="after")
    def validate_rate_vintage(self) -> Self:
        values = (self.rate_value, self.previous_rate_value, self.rate_change)
        if any(not value.is_finite() for value in values):
            raise ValueError("macro rate values must be finite")
        if self.rate_change != self.rate_value - self.previous_rate_value:
            raise ValueError("macro rate change must equal current minus previous vintage value")
        return self


class CrisisWindowDefinitionPayload(StrictModel):
    """Predeclared synthetic stress-window geometry, not an ex-post result label."""

    record_type: Literal["crisis_window_definition"] = "crisis_window_definition"
    crisis_window_id: Identifier
    definition_method_id: Identifier
    declared_at: datetime
    window_start: datetime
    window_end: datetime

    @field_validator("declared_at", "window_start", "window_end")
    @classmethod
    def normalize_window_times(cls, value: datetime) -> datetime:
        return _utc(value)

    @model_validator(mode="after")
    def validate_predeclared_window(self) -> Self:
        if self.window_end <= self.window_start:
            raise ValueError("crisis window must be positive")
        if self.declared_at >= self.window_start:
            raise ValueError("crisis window geometry must be declared before it begins")
        return self


class OfficialDocumentType(StrEnum):
    REGULATORY_FILING = "regulatory_filing"
    ISSUER_RELEASE = "issuer_release"
    EARNINGS_TRANSCRIPT_METADATA = "earnings_transcript_metadata"


class OfficialEventType(StrEnum):
    FILING = "filing"
    EARNINGS = "earnings"
    CORPORATE_EVENT = "corporate_event"


class OfficialDocumentEventPayload(StrictModel):
    record_type: Literal["official_document_event"] = "official_document_event"
    official_document_id: Identifier
    official_event_id: Identifier
    official_source_version_id: UUID
    document_type: OfficialDocumentType
    event_type: OfficialEventType
    accession_id: Identifier
    published_at: datetime
    accepted_at: datetime
    document_content_sha256: SHA256
    amendment_of_document_id: Identifier | None = None

    @field_validator("published_at", "accepted_at")
    @classmethod
    def normalize_timestamps(cls, value: datetime) -> datetime:
        return _utc(value)

    @model_validator(mode="after")
    def validate_document_times(self) -> Self:
        if self.accepted_at < self.published_at:
            raise ValueError("official acceptance cannot precede publication")
        return self


class SectorClassificationPayload(StrictModel):
    """Point-in-time sector identity; temporal validity lives in the source envelope."""

    record_type: Literal["sector_classification"] = "sector_classification"
    classification_scheme_id: Identifier
    classification_scheme_version: Identifier
    sector_id: Identifier
    sector_name: Identifier


class OfficialDocumentContentPayload(StrictModel):
    """Immutable official text evidence, never an LLM label or trading output."""

    record_type: Literal["official_document_content"] = "official_document_content"
    official_document_id: Identifier
    official_event_id: Identifier
    official_source_version_id: UUID
    document_type: OfficialDocumentType
    event_type: OfficialEventType
    accession_id: Identifier
    published_at: datetime
    accepted_at: datetime
    corrected_at: datetime | None
    correction_sequence: int = Field(ge=0)
    document_content_sha256: SHA256
    document_text: DocumentText
    amendment_of_document_id: Identifier | None = None

    @field_validator("published_at", "accepted_at", "corrected_at")
    @classmethod
    def normalize_timestamps(cls, value: datetime | None) -> datetime | None:
        return None if value is None else _utc(value)

    @model_validator(mode="after")
    def validate_content_and_correction(self) -> Self:
        if self.accepted_at < self.published_at:
            raise ValueError("official acceptance cannot precede publication")
        if self.document_content_sha256 != official_document_content_sha256(self.document_text):
            raise ValueError("document_content_sha256 must hash the exact UTF-8 document_text")
        if self.correction_sequence == 0:
            if self.corrected_at is not None or self.amendment_of_document_id is not None:
                raise ValueError("an original document cannot carry correction fields")
        else:
            if self.corrected_at is None or self.amendment_of_document_id is None:
                raise ValueError("a corrected document requires its timestamp and predecessor")
            if self.corrected_at < self.published_at or self.accepted_at < self.corrected_at:
                raise ValueError("corrected_at must be between publication and official acceptance")
            if self.amendment_of_document_id == self.official_document_id:
                raise ValueError("a corrected document cannot amend itself")
        return self


class SocialAttentionPayload(StrictModel):
    """Immutable synthetic social-attention metadata requiring official corroboration."""

    record_type: Literal["social_attention"] = "social_attention"
    social_attention_record_id: Identifier
    platform_id: Identifier
    observed_at: datetime
    social_content_sha256: SHA256
    entity_id: Identifier
    claimed_official_source_version_id: UUID
    manipulation_prone: Literal[True] = True
    contributes_standalone: Literal[False] = False

    @field_validator("observed_at")
    @classmethod
    def normalize_observed_at(cls, value: datetime) -> datetime:
        return _utc(value)


class VolatilityReturnInputPayload(StrictModel):
    record_type: Literal["volatility_return_input"] = "volatility_return_input"
    window_start: datetime
    window_end: datetime
    bar_observation_ids: tuple[UUID, ...]
    corporate_action_observation_ids: tuple[UUID, ...] = ()
    delisting_observation_ids: tuple[UUID, ...] = ()
    calendar_observation_ids: tuple[UUID, ...]

    @field_validator("window_start", "window_end")
    @classmethod
    def normalize_timestamps(cls, value: datetime) -> datetime:
        return _utc(value)

    @model_validator(mode="after")
    def validate_input_references(self) -> Self:
        if self.window_end <= self.window_start:
            raise ValueError("input window must be forward and non-empty")
        if not self.bar_observation_ids or not self.calendar_observation_ids:
            raise ValueError("volatility/return inputs require bar and calendar references")
        for values in (
            self.bar_observation_ids,
            self.corporate_action_observation_ids,
            self.delisting_observation_ids,
            self.calendar_observation_ids,
        ):
            if len(values) != len(set(values)):
                raise ValueError("volatility/return input references must be unique")
        return self


NormalizedPayload = Annotated[
    InstrumentIdentityPayload
    | ListingIdentityPayload
    | UniverseMembershipPayload
    | OhlcvBarPayload
    | CorporateActionPayload
    | DelistingEventPayload
    | AsReportedFundamentalPayload
    | CalendarSessionPayload
    | OfficialDocumentEventPayload
    | VolatilityReturnInputPayload
    | SectorClassificationPayload
    | OfficialDocumentContentPayload
    | SocialAttentionPayload
    | MacroRateObservationPayload
    | CrisisWindowDefinitionPayload,
    Field(discriminator="record_type"),
]


class RawObservationDraft(ObservationEnvelopeDraft):
    envelope_schema_version: Literal["phase4-raw-observation-v1"] = RAW_OBSERVATION_SCHEMA_VERSION
    raw_observation_id: UUID
    raw_content_type: Identifier
    raw_payload: bytes

    def identity_payload(self) -> dict[str, object]:
        return self.model_dump(
            mode="python",
            exclude={
                "raw_observation_id",
                "raw_payload",
                "snapshot_id",
                "snapshot_sha256",
            },
        )

    @model_validator(mode="after")
    def validate_raw_hash(self) -> Self:
        if not self.raw_payload:
            raise ValueError("raw payload must be nonempty")
        if raw_payload_sha256(self.raw_payload) != self.raw_payload_sha256:
            raise ValueError("raw payload hash does not match exact payload bytes")
        identity_sha256 = raw_observation_content_sha256(self.identity_payload())
        if self.raw_observation_id != raw_observation_id_from_sha256(identity_sha256):
            raise ValueError("raw observation ID must derive from canonical raw content")
        return self


class NormalizedObservationDraft(ObservationEnvelopeDraft):
    envelope_schema_version: Literal["phase4-normalized-observation-v1"] = (
        NORMALIZED_OBSERVATION_SCHEMA_VERSION
    )
    normalized_observation_id: UUID
    raw_observation_id: UUID
    observation_revision_id: UUID
    normalized_content_sha256: SHA256
    payload: NormalizedPayload

    def hash_payload(self) -> dict[str, object]:
        return self.model_dump(
            mode="python",
            exclude={
                "normalized_observation_id",
                "normalized_content_sha256",
                "snapshot_id",
                "snapshot_sha256",
            },
        )

    @model_validator(mode="after")
    def validate_normalized_hash_and_missingness(self) -> Self:
        expected = normalized_observation_content_sha256(self.hash_payload())
        if self.normalized_content_sha256 != expected:
            raise ValueError("normalized content hash does not match canonical observation content")
        if self.normalized_observation_id != normalized_observation_id_from_sha256(expected):
            raise ValueError("normalized observation ID must derive from normalized content")
        missing = {item.field_name: item.reason for item in self.field_missingness}
        nullable_fields = getattr(type(self.payload), "nullable_measurement_fields", ())
        for field_name in nullable_fields:
            attribute = field_name.split(".")[-1]
            value = getattr(self.payload, attribute)
            if value is None and field_name not in missing:
                raise ValueError(f"{field_name} null requires explicit field missingness")
            if value is not None and field_name in missing:
                raise ValueError(f"{field_name} cannot be populated and marked missing")
        if (
            isinstance(self.payload, DelistingEventPayload)
            and self.payload.delisting_return is None
        ):
            reason = missing.get("payload.delisting_return")
            expected_reason = (
                MissingnessReason.PROVIDER_RETURN_ALREADY_INCLUDES_DELISTING
                if self.payload.return_inclusion
                is DelistingReturnInclusion.PROVIDER_TOTAL_RETURN_INCLUDES
                else MissingnessReason.DELISTING_RETURN_NOT_PROVIDED
            )
            if reason is not expected_reason:
                raise ValueError("delisting-return missingness conflicts with inclusion semantics")

        record_type = DataRecordType(self.payload.record_type)
        instrument_required = record_type not in {
            DataRecordType.CALENDAR_SESSION,
            DataRecordType.MACRO_RATE_OBSERVATION,
            DataRecordType.CRISIS_WINDOW_DEFINITION,
        }
        listing_required = record_type in {
            DataRecordType.LISTING_IDENTITY,
            DataRecordType.UNIVERSE_MEMBERSHIP,
            DataRecordType.OHLCV_BAR,
            DataRecordType.DELISTING_EVENT,
            DataRecordType.VOLATILITY_RETURN_INPUT,
            DataRecordType.SOCIAL_ATTENTION,
        }
        if instrument_required and self.instrument_id is None:
            raise ValueError(f"{record_type.value} requires stable instrument identity")
        if listing_required and self.listing_id is None:
            raise ValueError(f"{record_type.value} requires stable listing identity")
        if (
            record_type
            in {
                DataRecordType.INSTRUMENT_IDENTITY,
                DataRecordType.CALENDAR_SESSION,
                DataRecordType.SECTOR_CLASSIFICATION,
                DataRecordType.MACRO_RATE_OBSERVATION,
                DataRecordType.CRISIS_WINDOW_DEFINITION,
            }
            and self.listing_id is not None
        ):
            raise ValueError(f"{record_type.value} cannot be listing-scoped")
        if record_type is DataRecordType.CALENDAR_SESSION and self.instrument_id is not None:
            raise ValueError("calendar sessions cannot be instrument-scoped")

        if (
            isinstance(self.payload, OhlcvBarPayload)
            and self.payload.adjustment_as_of is not None
            and self.payload.adjustment_as_of > self.available_at
        ):
            raise ValueError("adjusted bars cannot contain future corporate-action knowledge")
        if (
            isinstance(self.payload, CorporateActionPayload)
            and self.payload.announcement_at > self.available_at
        ):
            raise ValueError("corporate actions cannot be available before announcement")
        if (
            isinstance(self.payload, AsReportedFundamentalPayload)
            and self.payload.filing_accepted_at > self.available_at
        ):
            raise ValueError("fundamentals cannot be available before filing acceptance")
        if (
            isinstance(self.payload, OfficialDocumentEventPayload)
            and self.payload.accepted_at > self.available_at
        ):
            raise ValueError("official metadata cannot be available before acceptance")
        if isinstance(self.payload, OfficialDocumentContentPayload):
            if self.payload.accepted_at > self.available_at:
                raise ValueError("official content cannot be available before acceptance")
            if (
                self.payload.corrected_at is not None
                and self.payload.corrected_at > self.available_at
            ):
                raise ValueError("official corrections cannot be available before correction")
        if (
            isinstance(self.payload, SocialAttentionPayload)
            and self.payload.observed_at > self.available_at
        ):
            raise ValueError("social attention cannot be available before it is observed")
        return self


class ObservationRevisionDraft(ObservationEnvelopeDraft):
    envelope_schema_version: Literal["phase4-normalized-observation-v1"] = (
        NORMALIZED_OBSERVATION_SCHEMA_VERSION
    )
    revision_schema_version: Literal["phase4-observation-revision-v1"] = REVISION_SCHEMA_VERSION
    revision_record_id: UUID
    revision_content_sha256: SHA256
    raw_observation_id: UUID
    revision_sequence: int = Field(ge=1)
    predecessor_revision_record_id: UUID | None = None

    def hash_payload(self) -> dict[str, object]:
        return self.model_dump(
            mode="python",
            exclude={
                "revision_record_id",
                "revision_content_sha256",
                "snapshot_id",
                "snapshot_sha256",
            },
        )

    @model_validator(mode="after")
    def validate_revision_chain(self) -> Self:
        if self.revision_sequence == 1 and self.predecessor_revision_record_id is not None:
            raise ValueError("the first revision cannot have a predecessor")
        if self.revision_sequence > 1 and self.predecessor_revision_record_id is None:
            raise ValueError("later revisions require an immutable predecessor")
        if self.predecessor_revision_record_id == self.revision_record_id:
            raise ValueError("a revision cannot be its own predecessor")
        expected = revision_content_sha256(self.hash_payload())
        if self.revision_content_sha256 != expected:
            raise ValueError("revision content hash does not match canonical revision content")
        if self.revision_record_id != revision_id_from_sha256(expected):
            raise ValueError("revision record ID must derive from revision content")
        return self


class SnapshotConstituentDraft(ObservationEnvelopeDraft):
    envelope_schema_version: Literal["phase4-normalized-observation-v1"] = (
        NORMALIZED_OBSERVATION_SCHEMA_VERSION
    )
    record_type: DataRecordType
    raw_observation_id: UUID
    observation_revision_id: UUID
    normalized_observation_id: UUID
    normalized_content_sha256: SHA256
    disposition: ConstituentDisposition


class DataQualityFindingDraft(StrictModel):
    finding_id: UUID
    finding_sha256: SHA256
    rule_set_version: Literal[
        "phase4-data-quality-v1",
        "phase6-data-contract-quality-v1",
        "phase6-data-contract-quality-v2",
    ] = QUALITY_RULE_SET_VERSION
    rule_id: Identifier
    severity: DataQualitySeverity
    code: DataQualityCode
    affected_record_type: DataRecordType | None = None
    affected_record_identity: Identifier | None = None
    raw_payload_sha256: SHA256 | None = None
    normalized_content_sha256: SHA256 | None = None
    field_name: Identifier | None = None
    disposition: FindingDisposition
    occurrence_count: int = Field(ge=1)
    occurrence_rate: Decimal | None = Field(default=None, ge=0, le=1)
    range_start_utc: datetime | None = None
    range_end_utc: datetime | None = None
    sanitized_detail: dict[str, JsonValue]

    @field_validator("range_start_utc", "range_end_utc")
    @classmethod
    def normalize_range_timestamps(cls, value: datetime | None) -> datetime | None:
        return None if value is None else _utc(value)

    def hash_payload(self) -> dict[str, object]:
        return self.model_dump(
            mode="python",
            exclude={
                "finding_id",
                "finding_sha256",
                "snapshot_id",
                "snapshot_sha256",
            },
        )

    @model_validator(mode="after")
    def validate_finding_identity_and_detail(self) -> Self:
        if (self.range_start_utc is None) != (self.range_end_utc is None):
            raise ValueError("finding time ranges require both start and end")
        if (
            self.range_start_utc is not None
            and self.range_end_utc is not None
            and self.range_end_utc < self.range_start_utc
        ):
            raise ValueError("finding time range end cannot precede its start")
        detail_bytes = canonical_json_bytes(self.sanitized_detail)
        lowered = detail_bytes.decode("utf-8").casefold()
        if "sk-" in lowered or "://" in lowered or "password" in lowered:
            raise ValueError("finding detail must be sanitized JSON")
        if (
            self.severity is DataQualitySeverity.BLOCKING
            and self.disposition is not FindingDisposition.BLOCKED
        ):
            raise ValueError("blocking findings require blocked disposition")
        if self.disposition is FindingDisposition.BLOCKED and self.severity not in {
            DataQualitySeverity.ERROR,
            DataQualitySeverity.BLOCKING,
        }:
            raise ValueError("blocked disposition requires error or blocking severity")
        expected = quality_finding_sha256(self.hash_payload())
        if self.finding_sha256 != expected:
            raise ValueError("finding hash does not match canonical finding content")
        if self.finding_id != quality_finding_id_from_sha256(expected):
            raise ValueError("finding ID must derive from finding hash")
        return self


_LINEAGE_ENVELOPE_FIELDS = (
    "logical_record_id",
    "logical_record_key_sha256",
    "provider_id",
    "adapter_id",
    "adapter_version",
    "dataset_id",
    "product_id",
    "dataset_schema_id",
    "dataset_schema_version",
    "entitlement_id",
    "use_rights_id",
    "source_record_id",
    "instrument_id",
    "listing_id",
    "event_time",
    "available_at",
    "retrieved_at",
    "valid_from",
    "valid_to",
    "revision_id",
    "vintage_id",
    "source_timezone",
    "calendar_id",
    "unit",
    "currency",
    "availability_precision",
    "availability_convention",
    "availability_source_date",
    "raw_payload_sha256",
)


def _same_lineage_envelope(
    raw: RawObservationDraft,
    derived: ObservationRevisionDraft | NormalizedObservationDraft,
) -> bool:
    return all(getattr(raw, field) == getattr(derived, field) for field in _LINEAGE_ENVELOPE_FIELDS)


def _validate_observation_lineage(
    raw_observations: tuple[RawObservationDraft, ...],
    revisions: tuple[ObservationRevisionDraft, ...],
    normalized_observations: tuple[NormalizedObservationDraft, ...],
) -> None:
    raw_by_id = {item.raw_observation_id: item for item in raw_observations}
    revisions_by_id = {item.revision_record_id: item for item in revisions}
    normalized_ids = {item.normalized_observation_id for item in normalized_observations}
    if len(raw_by_id) != len(raw_observations):
        raise ValueError("raw observation IDs must be unique")
    if len(revisions_by_id) != len(revisions):
        raise ValueError("observation revision IDs must be unique")
    if len(normalized_ids) != len(normalized_observations):
        raise ValueError("normalized observation IDs must be unique")

    for revision in revisions:
        raw = raw_by_id.get(revision.raw_observation_id)
        if raw is None or not _same_lineage_envelope(raw, revision):
            raise ValueError("revision records cannot orphan or alter raw lineage")
        predecessor_id = revision.predecessor_revision_record_id
        if predecessor_id is not None:
            predecessor = revisions_by_id.get(predecessor_id)
            if predecessor is None:
                raise ValueError("revision predecessor must exist in immutable lineage")
            if (
                predecessor.logical_record_key_sha256 != revision.logical_record_key_sha256
                or predecessor.revision_sequence + 1 != revision.revision_sequence
            ):
                raise ValueError("revision predecessor must be the prior logical-key sequence")

    for normalized in normalized_observations:
        raw = raw_by_id.get(normalized.raw_observation_id)
        normalized_revision = revisions_by_id.get(normalized.observation_revision_id)
        if raw is None or normalized_revision is None:
            raise ValueError("normalized observations cannot orphan raw/revision lineage")
        if normalized_revision.raw_observation_id != normalized.raw_observation_id:
            raise ValueError("normalized raw lineage must match its observation revision")
        if normalized.logical_record_key_sha256 != normalized_revision.logical_record_key_sha256:
            raise ValueError("normalized logical key must match its observation revision")
        if not _same_lineage_envelope(raw, normalized):
            raise ValueError("normalized observations cannot alter raw provenance")


class SnapshotBinding(StrictModel):
    snapshot_id: UUID
    snapshot_sha256: SHA256


class RawObservation(RawObservationDraft):
    snapshot_id: UUID
    snapshot_sha256: SHA256


class NormalizedObservation(NormalizedObservationDraft):
    snapshot_id: UUID
    snapshot_sha256: SHA256


class ObservationRevision(ObservationRevisionDraft):
    snapshot_id: UUID
    snapshot_sha256: SHA256


class SnapshotConstituent(SnapshotConstituentDraft):
    snapshot_id: UUID
    snapshot_sha256: SHA256


class DataQualityFinding(DataQualityFindingDraft):
    snapshot_id: UUID
    snapshot_sha256: SHA256


class SnapshotManifestDraft(StrictModel):
    canonicalization_version: Literal["phase4-canonical-json-v1"] = CANONICAL_JSON_VERSION
    snapshot_schema_version: Literal["phase4-data-snapshot-v1"] = SNAPSHOT_SCHEMA_VERSION
    request_fingerprint_sha256: SHA256
    mapping: AuthorizedMappingIdentity
    request: SnapshotRequestParameters
    adapter: AdapterProfile
    schema_bindings: tuple[SchemaBinding, ...]
    use_rights: UseRightsIdentity
    configuration: MockConfigurationIdentity
    constituents: tuple[SnapshotConstituentDraft, ...]
    quality_findings: tuple[DataQualityFindingDraft, ...]

    @model_validator(mode="after")
    def validate_manifest_identity_and_order(self) -> Self:
        if self.mapping != self.request.mapping:
            raise ValueError("manifest mapping and request mapping must be identical")
        if self.use_rights != self.adapter.use_rights:
            raise ValueError("manifest use rights must match the adapter profile")
        if self.schema_bindings != self.adapter.schema_bindings:
            raise ValueError("manifest schemas must match the adapter profile")
        if self.request.capability not in self.adapter.capabilities:
            raise ValueError("requested capability must be declared by the adapter")
        fingerprint = RequestFingerprintInput(
            request=self.request,
            adapter=self.adapter,
            schema_bindings=self.schema_bindings,
            use_rights=self.use_rights,
            configuration=self.configuration,
        ).sha256()
        if self.request_fingerprint_sha256 != fingerprint:
            raise ValueError("request fingerprint does not match server-resolved inputs")
        allowed_record_types = CAPABILITY_RECORD_TYPES[self.request.capability]
        if any(item.record_type not in allowed_record_types for item in self.constituents):
            raise ValueError("constituent record type conflicts with requested capability")
        if any(item.available_at > self.request.as_of_utc for item in self.constituents):
            raise ValueError("snapshot constituents cannot include future-available records")
        constituent_keys = [
            (
                item.record_type.value,
                item.logical_record_id,
                item.logical_record_key_sha256,
                item.revision_id,
                item.vintage_id,
                item.raw_payload_sha256,
                item.normalized_content_sha256,
                item.disposition.value,
            )
            for item in self.constituents
        ]
        if tuple(sorted(constituent_keys)) != tuple(constituent_keys):
            raise ValueError("snapshot constituents must be canonically sorted")
        if len(constituent_keys) != len(set(constituent_keys)):
            raise ValueError("snapshot constituent canonical identities must be unique")
        finding_keys = [
            (
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
            for item in self.quality_findings
        ]
        if tuple(sorted(finding_keys)) != tuple(finding_keys):
            raise ValueError("quality findings must be canonically sorted")
        return self

    def identity_payload(self) -> dict[str, object]:
        payload = self.model_dump(
            mode="python",
            exclude={"constituents", "quality_findings"},
        )
        payload["constituents"] = [
            {
                "record_type": item.record_type,
                "logical_record_id": item.logical_record_id,
                "logical_record_key_sha256": item.logical_record_key_sha256,
                "revision_id": item.revision_id,
                "vintage_id": item.vintage_id,
                "raw_payload_sha256": item.raw_payload_sha256,
                "normalized_content_sha256": item.normalized_content_sha256,
                "quality_flags": item.quality_flags,
                "field_missingness": item.field_missingness,
                "disposition": item.disposition,
            }
            for item in self.constituents
        ]
        payload["quality_findings"] = [
            {"finding_sha256": item.finding_sha256} for item in self.quality_findings
        ]
        return payload

    def sha256(self) -> str:
        return domain_sha256(SNAPSHOT_HASH_DOMAIN, self.identity_payload())


class SnapshotManifest(SnapshotBinding):
    payload: SnapshotManifestDraft

    @model_validator(mode="after")
    def validate_manifest_hash(self) -> Self:
        if self.snapshot_sha256 != self.payload.sha256():
            raise ValueError("snapshot hash does not match its canonical manifest")
        if self.snapshot_id != snapshot_id_from_sha256(self.snapshot_sha256):
            raise ValueError("snapshot ID does not match the frozen UUID namespace")
        return self


class DataSnapshotDraft(StrictModel):
    manifest: SnapshotManifestDraft
    quality_status: SnapshotQualityStatus
    raw_observation_count: int = Field(ge=0)
    normalized_observation_count: int = Field(ge=0)
    revision_count: int = Field(ge=0)
    active_constituent_count: int = Field(ge=0)
    quality_finding_count: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_persistable_quality(self) -> Self:
        findings = self.manifest.quality_findings
        if any(item.disposition is FindingDisposition.BLOCKED for item in findings):
            raise ValueError("blocked data-quality builds cannot become persisted snapshots")
        expected_active = sum(
            item.disposition
            in {
                ConstituentDisposition.INCLUDED_AS_OF,
                ConstituentDisposition.EXPLICIT_MISSINGNESS,
            }
            for item in self.manifest.constituents
        )
        if self.active_constituent_count != expected_active:
            raise ValueError("active constituent count does not match manifest")
        has_warning = any(
            item.severity in {DataQualitySeverity.WARNING, DataQualitySeverity.ERROR}
            or item.disposition is FindingDisposition.EXCLUDED
            for item in findings
        )
        expected_status = (
            SnapshotQualityStatus.DATA_QUALITY_ACCEPTED_WITH_WARNINGS
            if has_warning
            else SnapshotQualityStatus.DATA_QUALITY_ACCEPTED
        )
        if self.quality_status is not expected_status:
            raise ValueError("snapshot quality status conflicts with findings")
        return self


class DataSnapshot(SnapshotBinding):
    manifest: SnapshotManifest
    quality_status: SnapshotQualityStatus
    raw_observation_count: int = Field(ge=0)
    normalized_observation_count: int = Field(ge=0)
    revision_count: int = Field(ge=0)
    active_constituent_count: int = Field(ge=0)
    quality_finding_count: int = Field(ge=0)
    created_at_utc: datetime

    @field_validator("created_at_utc")
    @classmethod
    def normalize_created_at(cls, value: datetime) -> datetime:
        return _utc(value)

    @model_validator(mode="after")
    def validate_snapshot_binding(self) -> Self:
        if (
            self.manifest.snapshot_id != self.snapshot_id
            or self.manifest.snapshot_sha256 != self.snapshot_sha256
        ):
            raise ValueError("snapshot and manifest bindings must match")
        if self.quality_finding_count != len(self.manifest.payload.quality_findings):
            raise ValueError("snapshot finding count does not match its manifest")
        expected_active = sum(
            item.disposition
            in {
                ConstituentDisposition.INCLUDED_AS_OF,
                ConstituentDisposition.EXPLICIT_MISSINGNESS,
            }
            for item in self.manifest.payload.constituents
        )
        if self.active_constituent_count != expected_active:
            raise ValueError("active constituent count does not match its manifest")
        findings = self.manifest.payload.quality_findings
        if any(item.disposition is FindingDisposition.BLOCKED for item in findings):
            raise ValueError("blocked data-quality builds cannot become persisted snapshots")
        has_warning = any(
            item.severity in {DataQualitySeverity.WARNING, DataQualitySeverity.ERROR}
            or item.disposition is FindingDisposition.EXCLUDED
            for item in findings
        )
        expected_status = (
            SnapshotQualityStatus.DATA_QUALITY_ACCEPTED_WITH_WARNINGS
            if has_warning
            else SnapshotQualityStatus.DATA_QUALITY_ACCEPTED
        )
        if self.quality_status is not expected_status:
            raise ValueError("snapshot quality status conflicts with its findings")
        return self


class SnapshotBuildBlockedResult(StrictModel):
    status: Literal["blocked"] = "blocked"
    request_fingerprint_sha256: SHA256
    quality_findings: tuple[DataQualityFindingDraft, ...]

    @model_validator(mode="after")
    def require_blocking_finding(self) -> Self:
        if not any(
            item.disposition is FindingDisposition.BLOCKED for item in self.quality_findings
        ):
            raise ValueError("blocked build result requires a blocked quality finding")
        return self


class SnapshotNondeterminismConflictResult(StrictModel):
    status: Literal["nondeterminism_conflict"] = "nondeterminism_conflict"
    request_fingerprint_sha256: SHA256
    existing_snapshot_sha256: SHA256
    candidate_snapshot_sha256: SHA256

    @model_validator(mode="after")
    def require_changed_output(self) -> Self:
        if self.existing_snapshot_sha256 == self.candidate_snapshot_sha256:
            raise ValueError("nondeterminism conflict requires changed snapshot output")
        return self


class SnapshotBundle(StrictModel):
    snapshot: DataSnapshot
    raw_observations: tuple[RawObservation, ...]
    normalized_observations: tuple[NormalizedObservation, ...]
    revisions: tuple[ObservationRevision, ...]
    constituents: tuple[SnapshotConstituent, ...]
    quality_findings: tuple[DataQualityFinding, ...]

    @model_validator(mode="after")
    def validate_complete_snapshot_lineage(self) -> Self:
        binding = (self.snapshot.snapshot_id, self.snapshot.snapshot_sha256)
        for collection in (
            self.raw_observations,
            self.normalized_observations,
            self.revisions,
            self.constituents,
            self.quality_findings,
        ):
            for item in collection:
                if (item.snapshot_id, item.snapshot_sha256) != binding:
                    raise ValueError("every bundle record must carry the snapshot binding")
        if self.snapshot.raw_observation_count != len(self.raw_observations):
            raise ValueError("raw observation count does not match bundle")
        if self.snapshot.normalized_observation_count != len(self.normalized_observations):
            raise ValueError("normalized observation count does not match bundle")
        if self.snapshot.revision_count != len(self.revisions):
            raise ValueError("revision count does not match bundle")
        if self.snapshot.quality_finding_count != len(self.quality_findings):
            raise ValueError("quality finding count does not match bundle")

        _validate_observation_lineage(
            self.raw_observations,
            self.revisions,
            self.normalized_observations,
        )
        normalized_by_id = {
            item.normalized_observation_id: item for item in self.normalized_observations
        }
        for constituent in self.constituents:
            normalized = normalized_by_id.get(constituent.normalized_observation_id)
            if normalized is None:
                raise ValueError("snapshot constituents cannot orphan normalized lineage")
            if (
                constituent.raw_observation_id != normalized.raw_observation_id
                or constituent.observation_revision_id != normalized.observation_revision_id
                or constituent.logical_record_id != normalized.logical_record_id
                or constituent.logical_record_key_sha256 != normalized.logical_record_key_sha256
                or constituent.raw_payload_sha256 != normalized.raw_payload_sha256
                or constituent.normalized_content_sha256 != normalized.normalized_content_sha256
                or constituent.revision_id != normalized.revision_id
                or constituent.vintage_id != normalized.vintage_id
                or constituent.record_type.value != normalized.payload.record_type
            ):
                raise ValueError("snapshot constituent lineage must match normalized content")
        manifest_constituents = tuple(
            item.model_dump(mode="python", exclude={"snapshot_id", "snapshot_sha256"})
            for item in self.constituents
        )
        expected_constituents = tuple(
            item.model_dump(mode="python") for item in self.snapshot.manifest.payload.constituents
        )
        if manifest_constituents != expected_constituents:
            raise ValueError("bound constituents must exactly match the canonical manifest")
        manifest_findings = tuple(
            item.model_dump(mode="python", exclude={"snapshot_id", "snapshot_sha256"})
            for item in self.quality_findings
        )
        expected_findings = tuple(
            item.model_dump(mode="python")
            for item in self.snapshot.manifest.payload.quality_findings
        )
        if manifest_findings != expected_findings:
            raise ValueError("bound findings must exactly match the canonical manifest")
        return self


class AdapterUnavailableReason(StrEnum):
    CREDENTIALS_UNAVAILABLE = "credentials_unavailable"
    CAPABILITY_UNAVAILABLE = "capability_unavailable"
    ENTITLEMENT_UNAVAILABLE = "entitlement_unavailable"
    CONFIGURATION_UNAVAILABLE = "configuration_unavailable"


class AdapterBatchDraft(StrictModel):
    raw_observations: tuple[RawObservationDraft, ...]
    normalized_observations: tuple[NormalizedObservationDraft, ...]
    revisions: tuple[ObservationRevisionDraft, ...]
    quality_findings: tuple[DataQualityFindingDraft, ...]

    @model_validator(mode="after")
    def validate_batch_lineage(self) -> Self:
        _validate_observation_lineage(
            self.raw_observations,
            self.revisions,
            self.normalized_observations,
        )
        return self


class AdapterAvailableResult(StrictModel):
    status: Literal["available"] = "available"
    profile: AdapterProfile
    capability: DataCapability
    batch: AdapterBatchDraft

    @model_validator(mode="after")
    def validate_available_capability(self) -> Self:
        if self.capability not in self.profile.capabilities:
            raise ValueError("available result capability must be declared by the adapter")
        allowed_record_types = CAPABILITY_RECORD_TYPES[self.capability]
        if any(
            DataRecordType(item.payload.record_type) not in allowed_record_types
            for item in self.batch.normalized_observations
        ):
            raise ValueError("available result contains records outside its capability")
        return self


class AdapterUnavailableResult(StrictModel):
    status: Literal["unavailable"] = "unavailable"
    reason_code: AdapterUnavailableReason
    capability: DataCapability
    provider_id: Identifier
    adapter_id: Identifier
    adapter_version: Identifier
    dataset_id: Identifier
    product_id: Identifier
    entitlement_id: Identifier
    use_rights_id: Identifier
    sanitized_message: Identifier

    @field_validator("sanitized_message")
    @classmethod
    def validate_sanitized_message(cls, value: str) -> str:
        lowered = value.casefold()
        if "\n" in value or "\r" in value or "://" in value or "sk-" in lowered:
            raise ValueError("unavailable messages must be sanitized and single-line")
        return value

    @model_validator(mode="after")
    def validate_sanitized_identities(self) -> Self:
        values = (
            self.provider_id,
            self.adapter_id,
            self.adapter_version,
            self.dataset_id,
            self.product_id,
            self.entitlement_id,
            self.use_rights_id,
        )
        if any("sk-" in value.casefold() or "://" in value for value in values):
            raise ValueError("unavailable result identities must be sanitized")
        return self


AdapterResult = Annotated[
    AdapterAvailableResult | AdapterUnavailableResult,
    Field(discriminator="status"),
]


def mock_configuration_sha256(payload: object) -> str:
    return domain_sha256(CONFIGURATION_HASH_DOMAIN, payload)


__all__ = [
    "AS_REPORTED_FUNDAMENTAL_SCHEMA_VERSION",
    "AUTHORIZED_CAPABILITIES",
    "CALENDAR_SESSION_SCHEMA_VERSION",
    "CANONICAL_JSON_VERSION",
    "CAPABILITY_RECORD_TYPES",
    "CORPORATE_ACTION_SCHEMA_VERSION",
    "CRISIS_WINDOW_DEFINITION_SCHEMA_VERSION",
    "DATE_ONLY_AVAILABILITY_CONVENTION",
    "DELISTING_EVENT_SCHEMA_VERSION",
    "INSTRUMENT_IDENTITY_SCHEMA_VERSION",
    "LISTING_IDENTITY_SCHEMA_VERSION",
    "MACRO_RATE_OBSERVATION_SCHEMA_VERSION",
    "NORMALIZED_OBSERVATION_SCHEMA_VERSION",
    "OFFICIAL_DOCUMENT_CONTENT_SCHEMA_VERSION",
    "OFFICIAL_DOCUMENT_EVENT_SCHEMA_VERSION",
    "OHLCV_BAR_SCHEMA_VERSION",
    "PHASE4_AUTHORIZED_CAPABILITIES",
    "PHASE4_CAPABILITY_RECORD_TYPES",
    "PHASE4_DATA_CAPABILITIES",
    "PHASE4_SCHEMA_CONSTANTS",
    "PHASE6_DATA_CONTRACT_CONSTANTS",
    "PHASE6_DATA_CONTRACT_VERSION",
    "PHASE6_DATA_QUALITY_RULE_SET_VERSION",
    "PHASE6_SYNTHETIC_ADAPTER_VERSION",
    "PHASE6_SYNTHETIC_FIXTURE_SET_VERSION",
    "QUALITY_RULE_SET_VERSION",
    "RAW_OBSERVATION_SCHEMA_VERSION",
    "REQUEST_FINGERPRINT_VERSION",
    "REVISION_SCHEMA_VERSION",
    "SECTOR_CLASSIFICATION_SCHEMA_VERSION",
    "SNAPSHOT_SCHEMA_VERSION",
    "SOCIAL_ATTENTION_SCHEMA_VERSION",
    "SYNTHETIC_ADAPTER_VERSION",
    "SYNTHETIC_FIXTURE_SET_VERSION",
    "SYNTHETIC_USE_RIGHTS_ID",
    "UNIVERSE_MEMBERSHIP_SCHEMA_VERSION",
    "VOLATILITY_RETURN_INPUT_SCHEMA_VERSION",
    "AdapterAvailableResult",
    "AdapterBatchDraft",
    "AdapterProfile",
    "AdapterResult",
    "AdapterUnavailableReason",
    "AdapterUnavailableResult",
    "AdjustmentBasis",
    "AsReportedFundamentalPayload",
    "AuthorizedMappingIdentity",
    "AvailabilityConvention",
    "AvailabilityPrecision",
    "CalendarSessionPayload",
    "CalendarSessionStatus",
    "ConstituentDisposition",
    "CorporateActionPayload",
    "CorporateActionType",
    "CrisisWindowDefinitionPayload",
    "DataCapability",
    "DataQualityCode",
    "DataQualityFinding",
    "DataQualityFindingDraft",
    "DataQualitySeverity",
    "DataRecordType",
    "DataSnapshot",
    "DataSnapshotDraft",
    "DelistingEventPayload",
    "DelistingReturnInclusion",
    "DelistingType",
    "FieldMissingness",
    "FindingDisposition",
    "FiscalPeriodType",
    "InstrumentIdentityPayload",
    "InstrumentType",
    "ListingIdentityPayload",
    "ListingStatus",
    "MacroRateObservationPayload",
    "MembershipStatus",
    "MissingnessReason",
    "MockConfigurationIdentity",
    "NormalizedObservation",
    "NormalizedObservationDraft",
    "NormalizedPayload",
    "ObservationEnvelopeDraft",
    "ObservationRevision",
    "ObservationRevisionDraft",
    "OfficialDocumentContentPayload",
    "OfficialDocumentEventPayload",
    "OfficialDocumentType",
    "OfficialEventType",
    "OhlcvBarPayload",
    "QualityFlag",
    "RawObservation",
    "RawObservationDraft",
    "RequestFingerprintInput",
    "SchemaBinding",
    "SectorClassificationPayload",
    "SnapshotBinding",
    "SnapshotBuildBlockedResult",
    "SnapshotBundle",
    "SnapshotConstituent",
    "SnapshotConstituentDraft",
    "SnapshotCreateRequest",
    "SnapshotManifest",
    "SnapshotManifestDraft",
    "SnapshotNondeterminismConflictResult",
    "SnapshotQualityStatus",
    "SnapshotRequestParameters",
    "SocialAttentionPayload",
    "StrictModel",
    "SyntheticFixtureSetVersion",
    "UniverseMembershipPayload",
    "UseRightsIdentity",
    "UseRightsScope",
    "VolatilityReturnInputPayload",
    "conservative_date_available_at",
    "mock_configuration_sha256",
    "official_document_content_sha256",
]
