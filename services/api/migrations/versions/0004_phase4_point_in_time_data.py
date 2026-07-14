"""Add immutable Phase 4 point-in-time data snapshots.

Revision ID: 0004_phase4
Revises: 0003_phase3
Create Date: 2026-07-13 23:30:00+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_phase4"
down_revision: str | None = "0003_phase3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PHASE4_TABLES = (
    "data_snapshots",
    "data_raw_observations",
    "data_observation_revisions",
    "data_normalized_observations",
    "data_snapshot_constituents",
    "data_quality_findings",
    "data_snapshot_manifests",
)

PHASE4_CHILD_TABLES = (
    "data_raw_observations",
    "data_observation_revisions",
    "data_normalized_observations",
    "data_snapshot_constituents",
    "data_quality_findings",
)


def _created_at() -> sa.Column[object]:
    return sa.Column(
        "created_at_utc",
        sa.DateTime(timezone=True),
        server_default=sa.text("CURRENT_TIMESTAMP"),
        nullable=False,
    )


def _observation_envelope_columns() -> list[sa.Column[object]]:
    """Return a fresh copy of the frozen contract observation envelope."""

    return [
        sa.Column("snapshot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("snapshot_sha256", sa.String(length=64), nullable=False),
        sa.Column("envelope_schema_version", sa.String(length=64), nullable=False),
        sa.Column("logical_record_id", sa.String(length=256), nullable=False),
        sa.Column("logical_record_key_sha256", sa.String(length=64), nullable=False),
        sa.Column("provider_id", sa.String(length=256), nullable=False),
        sa.Column("adapter_id", sa.String(length=256), nullable=False),
        sa.Column("adapter_version", sa.String(length=256), nullable=False),
        sa.Column("dataset_id", sa.String(length=256), nullable=False),
        sa.Column("product_id", sa.String(length=256), nullable=False),
        sa.Column("dataset_schema_id", sa.String(length=256), nullable=False),
        sa.Column("dataset_schema_version", sa.String(length=256), nullable=False),
        sa.Column("entitlement_id", sa.String(length=256), nullable=False),
        sa.Column("use_rights_id", sa.String(length=256), nullable=False),
        sa.Column("source_record_id", sa.String(length=256), nullable=False),
        sa.Column("instrument_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("listing_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revision_id", sa.String(length=256), nullable=False),
        sa.Column("vintage_id", sa.String(length=256), nullable=False),
        sa.Column("source_timezone", sa.String(length=256), nullable=False),
        sa.Column("calendar_id", sa.String(length=256), nullable=True),
        sa.Column("unit", sa.String(length=256), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("availability_precision", sa.String(length=16), nullable=False),
        sa.Column("availability_convention", sa.String(length=128), nullable=False),
        sa.Column("availability_source_date", sa.Date(), nullable=True),
        sa.Column(
            "quality_flags",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "field_missingness",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("raw_payload_sha256", sa.String(length=64), nullable=False),
    ]


def _observation_checks(prefix: str) -> list[sa.CheckConstraint]:
    return [
        sa.CheckConstraint(
            "snapshot_sha256 ~ '^[0-9a-f]{64}$' "
            "AND logical_record_key_sha256 ~ '^[0-9a-f]{64}$' "
            "AND raw_payload_sha256 ~ '^[0-9a-f]{64}$'",
            name=f"ck_{prefix}_hashes",
        ),
        sa.CheckConstraint(
            "btrim(envelope_schema_version) <> '' "
            "AND btrim(logical_record_id) <> '' "
            "AND btrim(provider_id) <> '' "
            "AND btrim(adapter_id) <> '' "
            "AND btrim(adapter_version) <> '' "
            "AND btrim(dataset_id) <> '' "
            "AND btrim(product_id) <> '' "
            "AND btrim(dataset_schema_id) <> '' "
            "AND btrim(dataset_schema_version) <> '' "
            "AND btrim(entitlement_id) <> '' "
            "AND btrim(use_rights_id) <> '' "
            "AND btrim(source_record_id) <> '' "
            "AND btrim(revision_id) <> '' "
            "AND btrim(vintage_id) <> '' "
            "AND btrim(source_timezone) <> '' "
            "AND (calendar_id IS NULL OR btrim(calendar_id) <> '') "
            "AND (unit IS NULL OR btrim(unit) <> '')",
            name=f"ck_{prefix}_nonblank_identities",
        ),
        sa.CheckConstraint(
            "retrieved_at IS NULL OR retrieved_at >= available_at",
            name=f"ck_{prefix}_retrieval_order",
        ),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_to > valid_from",
            name=f"ck_{prefix}_valid_interval",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(quality_flags) = 'array' AND jsonb_typeof(field_missingness) = 'array'",
            name=f"ck_{prefix}_quality_missingness_arrays",
        ),
        sa.CheckConstraint(
            "currency IS NULL OR currency ~ '^[A-Z]{3}$'",
            name=f"ck_{prefix}_currency",
        ),
        sa.CheckConstraint(
            "(availability_precision = 'timestamp' "
            "AND availability_convention = 'source_timestamp' "
            "AND availability_source_date IS NULL) OR "
            "(availability_precision = 'date' "
            "AND availability_convention = 'phase4-date-only-next-day-v1' "
            "AND availability_source_date IS NOT NULL)",
            name=f"ck_{prefix}_availability_semantics",
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "data_snapshots",
        sa.Column("snapshot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("snapshot_sha256", sa.String(length=64), nullable=False),
        sa.Column("request_fingerprint_sha256", sa.String(length=64), nullable=False),
        sa.Column("request_fingerprint_version", sa.String(length=64), nullable=False),
        sa.Column(
            "request_fingerprint_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("request_fingerprint_canonical_json", sa.Text(), nullable=False),
        sa.Column("mapping_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mapping_version", sa.Integer(), nullable=False),
        sa.Column("mapping_input_sha256", sa.String(length=64), nullable=False),
        sa.Column("mapper_rule_set_version", sa.String(length=256), nullable=False),
        sa.Column("mapper_rule_set_sha256", sa.String(length=64), nullable=False),
        sa.Column("canonical_family", sa.String(length=64), nullable=False),
        sa.Column("verdict", sa.String(length=32), nullable=False),
        sa.Column(
            "official_corroboration_source_version_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("as_of_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("capability", sa.String(length=64), nullable=False),
        sa.Column("mock_configuration_id", sa.String(length=256), nullable=False),
        sa.Column("configuration_id", sa.String(length=256), nullable=False),
        sa.Column("configuration_sha256", sa.String(length=64), nullable=False),
        sa.Column("fixture_set_version", sa.String(length=64), nullable=False),
        sa.Column("provider_id", sa.String(length=256), nullable=False),
        sa.Column("adapter_id", sa.String(length=256), nullable=False),
        sa.Column("adapter_version", sa.String(length=256), nullable=False),
        sa.Column("dataset_id", sa.String(length=256), nullable=False),
        sa.Column("product_id", sa.String(length=256), nullable=False),
        sa.Column("synthetic", sa.Boolean(), nullable=False),
        sa.Column(
            "capabilities",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "schema_bindings",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("entitlement_id", sa.String(length=256), nullable=False),
        sa.Column("use_rights_id", sa.String(length=256), nullable=False),
        sa.Column("scope", sa.String(length=64), nullable=False),
        sa.Column("storage_allowed", sa.Boolean(), nullable=False),
        sa.Column("display_allowed", sa.Boolean(), nullable=False),
        sa.Column("non_display_allowed", sa.Boolean(), nullable=False),
        sa.Column("derived_data_allowed", sa.Boolean(), nullable=False),
        sa.Column("redistribution_allowed", sa.Boolean(), nullable=False),
        sa.Column("snapshot_schema_version", sa.String(length=64), nullable=False),
        sa.Column("canonicalization_version", sa.String(length=64), nullable=False),
        sa.Column(
            "date_only_availability_convention",
            sa.String(length=128),
            nullable=False,
        ),
        sa.Column("quality_status", sa.String(length=64), nullable=False),
        sa.Column("raw_observation_count", sa.Integer(), nullable=False),
        sa.Column("revision_count", sa.Integer(), nullable=False),
        sa.Column("normalized_observation_count", sa.Integer(), nullable=False),
        sa.Column("constituent_count", sa.Integer(), nullable=False),
        sa.Column("active_constituent_count", sa.Integer(), nullable=False),
        sa.Column("quality_finding_count", sa.Integer(), nullable=False),
        _created_at(),
        sa.CheckConstraint(
            "snapshot_sha256 ~ '^[0-9a-f]{64}$' "
            "AND request_fingerprint_sha256 ~ '^[0-9a-f]{64}$' "
            "AND mapping_input_sha256 ~ '^[0-9a-f]{64}$' "
            "AND mapper_rule_set_sha256 ~ '^[0-9a-f]{64}$' "
            "AND configuration_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_data_snapshot_hashes",
        ),
        sa.CheckConstraint(
            "mapping_version >= 1 "
            "AND raw_observation_count >= 0 "
            "AND revision_count >= 0 "
            "AND normalized_observation_count >= 0 "
            "AND constituent_count >= 0 "
            "AND active_constituent_count >= 0 "
            "AND active_constituent_count <= constituent_count "
            "AND quality_finding_count >= 0",
            name="ck_data_snapshot_counts_independent",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(request_fingerprint_payload) = 'object' "
            "AND jsonb_typeof(official_corroboration_source_version_ids) = 'array' "
            "AND jsonb_typeof(capabilities) = 'array' "
            "AND jsonb_typeof(schema_bindings) = 'array'",
            name="ck_data_snapshot_json_shapes",
        ),
        sa.CheckConstraint(
            "canonical_family IN ("
            "'A_CROSS_SECTIONAL_EQUITY_RANKING',"
            "'B_TIME_SERIES_MOMENTUM_REGIME',"
            "'C_OFFICIAL_EVENT_TEXT_OVERLAY') "
            "AND verdict = 'BUILD_RESEARCH'",
            name="ck_data_snapshot_authorized_mapping",
        ),
        sa.CheckConstraint(
            "capability IN ("
            "'security_master','universe_membership','ohlcv','corporate_actions',"
            "'delistings','as_reported_fundamentals','trading_calendar',"
            "'volatility_return_inputs','official_document_event_metadata')",
            name="ck_data_snapshot_capability",
        ),
        sa.CheckConstraint(
            "request_fingerprint_version = 'phase4-request-fingerprint-v1' "
            "AND snapshot_schema_version = 'phase4-data-snapshot-v1' "
            "AND canonicalization_version = 'phase4-canonical-json-v1' "
            "AND date_only_availability_convention = 'phase4-date-only-next-day-v1' "
            "AND fixture_set_version = 'phase4-synthetic-pit-fixtures-v1'",
            name="ck_data_snapshot_frozen_versions",
        ),
        sa.CheckConstraint(
            "quality_status IN ('data_quality_accepted','data_quality_accepted_with_warnings')",
            name="ck_data_snapshot_accepted_status",
        ),
        sa.CheckConstraint(
            "synthetic AND storage_allowed "
            "AND scope = 'internal_test_fixture_only' "
            "AND configuration_id = mock_configuration_id",
            name="ck_data_snapshot_synthetic_rights",
        ),
        sa.ForeignKeyConstraint(
            ["mapping_id"],
            ["research_mapping_versions.id"],
            name="fk_data_snapshot_mapping",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("snapshot_id", name="pk_data_snapshots"),
        sa.UniqueConstraint("snapshot_sha256", name="uq_data_snapshot_sha256"),
        sa.UniqueConstraint(
            "request_fingerprint_sha256",
            name="uq_data_snapshot_request_fingerprint",
        ),
    )
    op.create_index(
        "ix_data_snapshots_mapping_as_of",
        "data_snapshots",
        ["mapping_id", "as_of_utc", "snapshot_id"],
    )
    op.create_index(
        "ix_data_snapshots_created",
        "data_snapshots",
        ["created_at_utc", "snapshot_id"],
    )

    op.create_table(
        "data_raw_observations",
        sa.Column("raw_observation_id", postgresql.UUID(as_uuid=True), nullable=False),
        *_observation_envelope_columns(),
        sa.Column("raw_content_type", sa.String(length=256), nullable=False),
        sa.Column("raw_payload", sa.LargeBinary(), nullable=False),
        _created_at(),
        *_observation_checks("data_raw_observation"),
        sa.CheckConstraint(
            "envelope_schema_version = 'phase4-raw-observation-v1' "
            "AND btrim(raw_content_type) <> '' "
            "AND octet_length(raw_payload) > 0",
            name="ck_data_raw_observation_payload",
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["data_snapshots.snapshot_id"],
            name="fk_data_raw_observation_snapshot",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "snapshot_id",
            "raw_observation_id",
            name="pk_data_raw_observations",
        ),
    )
    op.create_index(
        "ix_data_raw_observations_snapshot_key",
        "data_raw_observations",
        ["snapshot_id", "logical_record_key_sha256"],
    )

    op.create_table(
        "data_observation_revisions",
        sa.Column("revision_record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("raw_observation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("revision_schema_version", sa.String(length=64), nullable=False),
        sa.Column("revision_content_sha256", sa.String(length=64), nullable=False),
        sa.Column("revision_sequence", sa.Integer(), nullable=False),
        sa.Column(
            "predecessor_revision_record_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        *_observation_envelope_columns(),
        _created_at(),
        *_observation_checks("data_observation_revision"),
        sa.CheckConstraint(
            "envelope_schema_version = 'phase4-normalized-observation-v1' "
            "AND revision_schema_version = 'phase4-observation-revision-v1' "
            "AND revision_content_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_data_observation_revision_versions_hash",
        ),
        sa.CheckConstraint(
            "(revision_sequence = 1 AND predecessor_revision_record_id IS NULL) OR "
            "(revision_sequence > 1 AND predecessor_revision_record_id IS NOT NULL)",
            name="ck_data_observation_revision_predecessor",
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["data_snapshots.snapshot_id"],
            name="fk_data_observation_revision_snapshot",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_id", "raw_observation_id"],
            [
                "data_raw_observations.snapshot_id",
                "data_raw_observations.raw_observation_id",
            ],
            name="fk_data_observation_revision_raw",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_id", "predecessor_revision_record_id"],
            [
                "data_observation_revisions.snapshot_id",
                "data_observation_revisions.revision_record_id",
            ],
            name="fk_data_observation_revision_predecessor",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "snapshot_id",
            "revision_record_id",
            name="pk_data_observation_revisions",
        ),
        sa.UniqueConstraint(
            "snapshot_id",
            "logical_record_key_sha256",
            "revision_sequence",
            name="uq_data_observation_revision_logical_sequence",
        ),
    )
    op.create_index(
        "ix_data_observation_revisions_snapshot_key",
        "data_observation_revisions",
        ["snapshot_id", "logical_record_key_sha256", "revision_sequence"],
    )

    op.create_table(
        "data_normalized_observations",
        sa.Column("normalized_observation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("raw_observation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("observation_revision_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("normalized_content_sha256", sa.String(length=64), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        *_observation_envelope_columns(),
        _created_at(),
        *_observation_checks("data_normalized_observation"),
        sa.CheckConstraint(
            "envelope_schema_version = 'phase4-normalized-observation-v1' "
            "AND normalized_content_sha256 ~ '^[0-9a-f]{64}$' "
            "AND jsonb_typeof(payload) = 'object'",
            name="ck_data_normalized_observation_content",
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["data_snapshots.snapshot_id"],
            name="fk_data_normalized_observation_snapshot",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_id", "raw_observation_id"],
            [
                "data_raw_observations.snapshot_id",
                "data_raw_observations.raw_observation_id",
            ],
            name="fk_data_normalized_observation_raw",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_id", "observation_revision_id"],
            [
                "data_observation_revisions.snapshot_id",
                "data_observation_revisions.revision_record_id",
            ],
            name="fk_data_normalized_observation_revision",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "snapshot_id",
            "normalized_observation_id",
            name="pk_data_normalized_observations",
        ),
    )
    op.create_index(
        "ix_data_normalized_observations_snapshot_key",
        "data_normalized_observations",
        ["snapshot_id", "logical_record_key_sha256"],
    )

    op.create_table(
        "data_snapshot_constituents",
        sa.Column("ordinal_position", sa.Integer(), nullable=False),
        sa.Column("record_type", sa.String(length=64), nullable=False),
        sa.Column("raw_observation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("observation_revision_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("normalized_observation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("normalized_content_sha256", sa.String(length=64), nullable=False),
        sa.Column("disposition", sa.String(length=64), nullable=False),
        sa.Column(
            "manifest_entry",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        *_observation_envelope_columns(),
        _created_at(),
        *_observation_checks("data_snapshot_constituent"),
        sa.CheckConstraint(
            "ordinal_position >= 1 "
            "AND envelope_schema_version = 'phase4-normalized-observation-v1' "
            "AND normalized_content_sha256 ~ '^[0-9a-f]{64}$' "
            "AND jsonb_typeof(manifest_entry) = 'object'",
            name="ck_data_snapshot_constituent_identity",
        ),
        sa.CheckConstraint(
            "record_type IN ("
            "'instrument_identity','listing_identity','universe_membership',"
            "'ohlcv_bar','corporate_action','delisting_event',"
            "'as_reported_fundamental','calendar_session',"
            "'official_document_event','volatility_return_input')",
            name="ck_data_snapshot_constituent_record_type",
        ),
        sa.CheckConstraint(
            "disposition IN ("
            "'included_as_of','retained_historical_vintage','explicit_missingness')",
            name="ck_data_snapshot_constituent_disposition",
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["data_snapshots.snapshot_id"],
            name="fk_data_snapshot_constituent_snapshot",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_id", "raw_observation_id"],
            [
                "data_raw_observations.snapshot_id",
                "data_raw_observations.raw_observation_id",
            ],
            name="fk_data_snapshot_constituent_raw",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_id", "observation_revision_id"],
            [
                "data_observation_revisions.snapshot_id",
                "data_observation_revisions.revision_record_id",
            ],
            name="fk_data_snapshot_constituent_revision",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_id", "normalized_observation_id"],
            [
                "data_normalized_observations.snapshot_id",
                "data_normalized_observations.normalized_observation_id",
            ],
            name="fk_data_snapshot_constituent_normalized",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "snapshot_id",
            "ordinal_position",
            name="pk_data_snapshot_constituents",
        ),
        sa.UniqueConstraint(
            "snapshot_id",
            "record_type",
            "logical_record_id",
            "logical_record_key_sha256",
            "revision_id",
            "vintage_id",
            "raw_payload_sha256",
            "normalized_content_sha256",
            "disposition",
            name="uq_data_snapshot_constituent_canonical_identity",
        ),
    )

    op.create_table(
        "data_quality_findings",
        sa.Column("snapshot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("snapshot_sha256", sa.String(length=64), nullable=False),
        sa.Column("ordinal_position", sa.Integer(), nullable=False),
        sa.Column("finding_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("finding_sha256", sa.String(length=64), nullable=False),
        sa.Column("rule_set_version", sa.String(length=256), nullable=False),
        sa.Column("rule_id", sa.String(length=256), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("affected_record_type", sa.String(length=64), nullable=True),
        sa.Column("affected_record_identity", sa.String(length=256), nullable=True),
        sa.Column("raw_payload_sha256", sa.String(length=64), nullable=True),
        sa.Column("normalized_content_sha256", sa.String(length=64), nullable=True),
        sa.Column("field_name", sa.String(length=256), nullable=True),
        sa.Column("disposition", sa.String(length=16), nullable=False),
        sa.Column("occurrence_count", sa.Integer(), nullable=False),
        sa.Column("occurrence_rate", sa.Numeric(precision=20, scale=18), nullable=True),
        sa.Column("range_start_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("range_end_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "sanitized_detail",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "manifest_entry",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        _created_at(),
        sa.CheckConstraint(
            "ordinal_position >= 1 "
            "AND snapshot_sha256 ~ '^[0-9a-f]{64}$' "
            "AND finding_sha256 ~ '^[0-9a-f]{64}$' "
            "AND (raw_payload_sha256 IS NULL "
            "OR raw_payload_sha256 ~ '^[0-9a-f]{64}$') "
            "AND (normalized_content_sha256 IS NULL "
            "OR normalized_content_sha256 ~ '^[0-9a-f]{64}$')",
            name="ck_data_quality_finding_hashes",
        ),
        sa.CheckConstraint(
            "rule_set_version = 'phase4-data-quality-v1' "
            "AND btrim(rule_id) <> '' "
            "AND (affected_record_identity IS NULL "
            "OR btrim(affected_record_identity) <> '') "
            "AND (field_name IS NULL OR btrim(field_name) <> '')",
            name="ck_data_quality_finding_identities",
        ),
        sa.CheckConstraint(
            "severity IN ('info','warning','error','blocking') "
            "AND disposition IN ('retained','excluded','blocked') "
            "AND (severity <> 'blocking' OR disposition = 'blocked') "
            "AND (disposition <> 'blocked' OR severity IN ('error','blocking'))",
            name="ck_data_quality_finding_severity_disposition",
        ),
        sa.CheckConstraint(
            "code IN ("
            "'synthetic_fixture','date_only_convention_applied',"
            "'future_availability_excluded','near_duplicate_retained',"
            "'exact_duplicate_key','required_field_missing','invalid_enum_value',"
            "'invalid_timestamp_order','orphan_reference',"
            "'raw_normalized_lineage_gap',"
            "'unit_currency_calendar_timezone_mismatch','schema_drift',"
            "'current_universe_leakage','restatement_leakage',"
            "'corporate_action_lookahead','missing_delisting_return',"
            "'future_availability_included','unnormalized_rejected')",
            name="ck_data_quality_finding_code",
        ),
        sa.CheckConstraint(
            "affected_record_type IS NULL OR affected_record_type IN ("
            "'instrument_identity','listing_identity','universe_membership',"
            "'ohlcv_bar','corporate_action','delisting_event',"
            "'as_reported_fundamental','calendar_session',"
            "'official_document_event','volatility_return_input')",
            name="ck_data_quality_finding_record_type",
        ),
        sa.CheckConstraint(
            "occurrence_count >= 1 "
            "AND (occurrence_rate IS NULL "
            "OR (occurrence_rate >= 0 AND occurrence_rate <= 1))",
            name="ck_data_quality_finding_occurrence",
        ),
        sa.CheckConstraint(
            "(range_start_utc IS NULL AND range_end_utc IS NULL) OR "
            "(range_start_utc IS NOT NULL AND range_end_utc IS NOT NULL "
            "AND range_end_utc >= range_start_utc)",
            name="ck_data_quality_finding_range",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(sanitized_detail) = 'object' "
            "AND jsonb_typeof(manifest_entry) = 'object' "
            "AND position('sk-' IN lower(sanitized_detail::text)) = 0 "
            "AND position('://' IN lower(sanitized_detail::text)) = 0 "
            "AND position('password' IN lower(sanitized_detail::text)) = 0",
            name="ck_data_quality_finding_sanitized",
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["data_snapshots.snapshot_id"],
            name="fk_data_quality_finding_snapshot",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "snapshot_id",
            "finding_id",
            name="pk_data_quality_findings",
        ),
        sa.UniqueConstraint(
            "snapshot_id",
            "ordinal_position",
            name="uq_data_quality_finding_ordinal",
        ),
        sa.UniqueConstraint(
            "snapshot_id",
            "finding_sha256",
            name="uq_data_quality_finding_hash",
        ),
    )

    op.create_table(
        "data_snapshot_manifests",
        sa.Column("snapshot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("snapshot_sha256", sa.String(length=64), nullable=False),
        sa.Column("request_fingerprint_sha256", sa.String(length=64), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "identity_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("identity_canonical_json", sa.Text(), nullable=False),
        sa.Column("raw_observation_count", sa.Integer(), nullable=False),
        sa.Column("revision_count", sa.Integer(), nullable=False),
        sa.Column("normalized_observation_count", sa.Integer(), nullable=False),
        sa.Column("constituent_count", sa.Integer(), nullable=False),
        sa.Column("active_constituent_count", sa.Integer(), nullable=False),
        sa.Column("quality_finding_count", sa.Integer(), nullable=False),
        sa.Column("quality_status", sa.String(length=64), nullable=False),
        sa.Column(
            "finalized_at_utc",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "snapshot_sha256 ~ '^[0-9a-f]{64}$' AND request_fingerprint_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_data_snapshot_manifest_hashes",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(payload) = 'object' "
            "AND jsonb_typeof(identity_payload) = 'object' "
            "AND btrim(identity_canonical_json) <> ''",
            name="ck_data_snapshot_manifest_payloads",
        ),
        sa.CheckConstraint(
            "raw_observation_count >= 0 "
            "AND revision_count >= 0 "
            "AND normalized_observation_count >= 0 "
            "AND constituent_count >= 0 "
            "AND active_constituent_count >= 0 "
            "AND active_constituent_count <= constituent_count "
            "AND quality_finding_count >= 0",
            name="ck_data_snapshot_manifest_counts_independent",
        ),
        sa.CheckConstraint(
            "quality_status IN ('data_quality_accepted','data_quality_accepted_with_warnings')",
            name="ck_data_snapshot_manifest_accepted_status",
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["data_snapshots.snapshot_id"],
            name="fk_data_snapshot_manifest_snapshot",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("snapshot_id", name="pk_data_snapshot_manifests"),
        sa.UniqueConstraint(
            "snapshot_sha256",
            name="uq_data_snapshot_manifest_hash",
        ),
    )

    op.execute(
        """
        CREATE FUNCTION validate_phase4_snapshot_request()
        RETURNS trigger AS $$
        DECLARE
            mapping record;
            expected_corroborations jsonb;
            expected_mapping jsonb;
            expected_rights jsonb;
            sorted_capabilities jsonb;
            sorted_schema_bindings jsonb;
        BEGIN
            SELECT
                version_number AS mapping_version,
                mapping_input_sha256,
                mapper_rule_set_version,
                mapper_rule_set_sha256,
                canonical_family,
                research_verdict AS verdict
            INTO mapping
            FROM research_mapping_versions
            WHERE id = NEW.mapping_id
            FOR KEY SHARE;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'Phase 4 mapping was not found';
            END IF;

            SELECT COALESCE(
                jsonb_agg(
                    official_source_version_id::text
                    ORDER BY official_source_version_id::text
                ),
                '[]'::jsonb
            ) INTO expected_corroborations
            FROM mapping_official_corroborations
            WHERE mapping_id = NEW.mapping_id;

            IF NEW.mapping_version IS DISTINCT FROM mapping.mapping_version
                OR NEW.mapping_input_sha256 IS DISTINCT FROM mapping.mapping_input_sha256
                OR NEW.mapper_rule_set_version
                    IS DISTINCT FROM mapping.mapper_rule_set_version
                OR NEW.mapper_rule_set_sha256
                    IS DISTINCT FROM mapping.mapper_rule_set_sha256
                OR NEW.canonical_family IS DISTINCT FROM mapping.canonical_family
                OR NEW.verdict IS DISTINCT FROM mapping.verdict
                OR NEW.official_corroboration_source_version_ids
                    IS DISTINCT FROM expected_corroborations THEN
                RAISE EXCEPTION 'Phase 4 persisted mapping lineage mismatch';
            END IF;
            IF mapping.verdict <> 'BUILD_RESEARCH' THEN
                RAISE EXCEPTION 'Phase 4 requires a BUILD_RESEARCH mapping';
            END IF;

            IF mapping.canonical_family = 'A_CROSS_SECTIONAL_EQUITY_RANKING' THEN
                IF NEW.capability NOT IN (
                    'security_master',
                    'universe_membership',
                    'ohlcv',
                    'corporate_actions',
                    'delistings',
                    'as_reported_fundamentals'
                ) THEN
                    RAISE EXCEPTION 'Phase 4 capability is not authorized for Family A';
                END IF;
            ELSIF mapping.canonical_family = 'B_TIME_SERIES_MOMENTUM_REGIME' THEN
                IF NEW.capability NOT IN (
                    'ohlcv',
                    'corporate_actions',
                    'delistings',
                    'trading_calendar',
                    'volatility_return_inputs'
                ) THEN
                    RAISE EXCEPTION 'Phase 4 capability is not authorized for Family B';
                END IF;
            ELSIF mapping.canonical_family = 'C_OFFICIAL_EVENT_TEXT_OVERLAY' THEN
                IF NEW.capability <> 'official_document_event_metadata' THEN
                    RAISE EXCEPTION 'Phase 4 capability is not authorized for Family C';
                END IF;
                IF jsonb_array_length(expected_corroborations) = 0 THEN
                    RAISE EXCEPTION 'Phase 4 Family C requires official corroboration';
                END IF;
            ELSE
                RAISE EXCEPTION 'Phase 4 mapping family is not authorized';
            END IF;

            SELECT COALESCE(jsonb_agg(value ORDER BY value), '[]'::jsonb)
            INTO sorted_capabilities
            FROM (
                SELECT DISTINCT value
                FROM jsonb_array_elements_text(NEW.capabilities)
            ) AS values;
            IF NEW.capabilities IS DISTINCT FROM sorted_capabilities
                OR NEW.capability NOT IN (
                    SELECT value FROM jsonb_array_elements_text(NEW.capabilities)
                ) THEN
                RAISE EXCEPTION 'Phase 4 adapter capabilities must be sorted and authoritative';
            END IF;

            IF EXISTS (
                SELECT 1
                FROM jsonb_array_elements_text(NEW.capabilities) AS item(value)
                WHERE value NOT IN (
                    'security_master','universe_membership','ohlcv','corporate_actions',
                    'delistings','as_reported_fundamentals','trading_calendar',
                    'volatility_return_inputs','official_document_event_metadata'
                )
            ) THEN
                RAISE EXCEPTION 'Phase 4 adapter capability vocabulary is closed';
            END IF;

            IF EXISTS (
                SELECT 1 FROM jsonb_array_elements(NEW.schema_bindings) AS item(value)
                WHERE jsonb_typeof(value) <> 'object'
                   OR btrim(value->>'dataset_schema_id') = ''
                   OR btrim(value->>'dataset_schema_version') = ''
            ) THEN
                RAISE EXCEPTION 'Phase 4 schema bindings are invalid';
            END IF;
            SELECT COALESCE(jsonb_agg(value ORDER BY value->>'dataset_schema_id',
                value->>'dataset_schema_version'), '[]'::jsonb)
            INTO sorted_schema_bindings
            FROM (
                SELECT DISTINCT value
                FROM jsonb_array_elements(NEW.schema_bindings) AS item(value)
            ) AS values;
            IF NEW.schema_bindings IS DISTINCT FROM sorted_schema_bindings THEN
                RAISE EXCEPTION 'Phase 4 schema bindings must be unique and sorted';
            END IF;

            expected_mapping := jsonb_build_object(
                'mapping_id', NEW.mapping_id::text,
                'mapping_version', NEW.mapping_version,
                'mapping_input_sha256', NEW.mapping_input_sha256,
                'mapper_rule_set_version', NEW.mapper_rule_set_version,
                'mapper_rule_set_sha256', NEW.mapper_rule_set_sha256,
                'canonical_family', NEW.canonical_family,
                'verdict', NEW.verdict,
                'official_corroboration_source_version_ids',
                    NEW.official_corroboration_source_version_ids
            );
            expected_rights := jsonb_build_object(
                'entitlement_id', NEW.entitlement_id,
                'use_rights_id', NEW.use_rights_id,
                'scope', NEW.scope,
                'storage_allowed', NEW.storage_allowed,
                'display_allowed', NEW.display_allowed,
                'non_display_allowed', NEW.non_display_allowed,
                'derived_data_allowed', NEW.derived_data_allowed,
                'redistribution_allowed', NEW.redistribution_allowed
            );

            IF NEW.request_fingerprint_canonical_json::jsonb
                    IS DISTINCT FROM NEW.request_fingerprint_payload
                OR encode(
                    sha256(
                        convert_to('phase4-request-fingerprint-v1', 'UTF8')
                        || decode('00', 'hex')
                        || convert_to(NEW.request_fingerprint_canonical_json, 'UTF8')
                    ),
                    'hex'
                ) IS DISTINCT FROM NEW.request_fingerprint_sha256 THEN
                RAISE EXCEPTION 'Phase 4 request fingerprint hash mismatch';
            END IF;
            IF NEW.request_fingerprint_payload->>'fingerprint_version'
                    <> NEW.request_fingerprint_version
                OR NEW.request_fingerprint_payload->>'snapshot_schema_version'
                    <> NEW.snapshot_schema_version
                OR NEW.request_fingerprint_payload->>'canonicalization_version'
                    <> NEW.canonicalization_version
                OR NEW.request_fingerprint_payload->>'date_only_availability_convention'
                    <> NEW.date_only_availability_convention
                OR NEW.request_fingerprint_payload#>'{request,mapping}'
                    IS DISTINCT FROM expected_mapping
                OR (NEW.request_fingerprint_payload#>>'{request,as_of_utc}')::timestamptz
                    IS DISTINCT FROM NEW.as_of_utc
                OR NEW.request_fingerprint_payload#>>'{request,capability}'
                    <> NEW.capability
                OR NEW.request_fingerprint_payload#>>'{request,mock_configuration_id}'
                    <> NEW.mock_configuration_id THEN
                RAISE EXCEPTION 'Phase 4 request fingerprint request mismatch';
            END IF;
            IF NEW.request_fingerprint_payload#>>'{adapter,provider_id}' <> NEW.provider_id
                OR NEW.request_fingerprint_payload#>>'{adapter,adapter_id}' <> NEW.adapter_id
                OR NEW.request_fingerprint_payload#>>'{adapter,adapter_version}'
                    <> NEW.adapter_version
                OR NEW.request_fingerprint_payload#>>'{adapter,dataset_id}' <> NEW.dataset_id
                OR NEW.request_fingerprint_payload#>>'{adapter,product_id}' <> NEW.product_id
                OR (NEW.request_fingerprint_payload#>>'{adapter,synthetic}')::boolean
                    IS DISTINCT FROM NEW.synthetic
                OR NEW.request_fingerprint_payload#>'{adapter,capabilities}'
                    IS DISTINCT FROM NEW.capabilities
                OR NEW.request_fingerprint_payload#>'{adapter,schema_bindings}'
                    IS DISTINCT FROM NEW.schema_bindings
                OR NEW.request_fingerprint_payload#>'{adapter,use_rights}'
                    IS DISTINCT FROM expected_rights
                OR NEW.request_fingerprint_payload->'schema_bindings'
                    IS DISTINCT FROM NEW.schema_bindings
                OR NEW.request_fingerprint_payload->'use_rights'
                    IS DISTINCT FROM expected_rights THEN
                RAISE EXCEPTION 'Phase 4 request fingerprint adapter mismatch';
            END IF;
            IF NEW.request_fingerprint_payload#>>'{configuration,configuration_id}'
                    <> NEW.configuration_id
                OR NEW.request_fingerprint_payload#>>'{configuration,configuration_sha256}'
                    <> NEW.configuration_sha256
                OR NEW.request_fingerprint_payload#>>'{configuration,fixture_set_version}'
                    <> NEW.fixture_set_version THEN
                RAISE EXCEPTION 'Phase 4 request fingerprint configuration mismatch';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER data_snapshots_10_request_gate
        BEFORE INSERT ON data_snapshots
        FOR EACH ROW EXECUTE FUNCTION validate_phase4_snapshot_request()
        """
    )

    op.execute(
        """
        CREATE FUNCTION guard_phase4_unfinalized_snapshot()
        RETURNS trigger AS $$
        BEGIN
            PERFORM 1
            FROM data_snapshots
            WHERE snapshot_id = NEW.snapshot_id
            FOR UPDATE;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'Phase 4 snapshot was not found';
            END IF;
            IF EXISTS (
                SELECT 1 FROM data_snapshot_manifests
                WHERE snapshot_id = NEW.snapshot_id
            ) THEN
                RAISE EXCEPTION 'Phase 4 snapshot is finalized and cannot accept rows';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    for table in PHASE4_CHILD_TABLES:
        op.execute(
            f"""
            CREATE TRIGGER {table}_00_unfinalized
            BEFORE INSERT ON {table}
            FOR EACH ROW EXECUTE FUNCTION guard_phase4_unfinalized_snapshot()
            """
        )

    op.execute(
        """
        CREATE FUNCTION validate_phase4_observation_envelope()
        RETURNS trigger AS $$
        DECLARE
            snapshot record;
        BEGIN
            SELECT * INTO snapshot
            FROM data_snapshots
            WHERE snapshot_id = NEW.snapshot_id;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'Phase 4 observation snapshot was not found';
            END IF;
            IF NEW.snapshot_sha256 IS DISTINCT FROM snapshot.snapshot_sha256
                OR NEW.provider_id IS DISTINCT FROM snapshot.provider_id
                OR NEW.adapter_id IS DISTINCT FROM snapshot.adapter_id
                OR NEW.adapter_version IS DISTINCT FROM snapshot.adapter_version
                OR NEW.dataset_id IS DISTINCT FROM snapshot.dataset_id
                OR NEW.product_id IS DISTINCT FROM snapshot.product_id
                OR NEW.entitlement_id IS DISTINCT FROM snapshot.entitlement_id
                OR NEW.use_rights_id IS DISTINCT FROM snapshot.use_rights_id THEN
                RAISE EXCEPTION 'Phase 4 observation snapshot provenance mismatch';
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM jsonb_array_elements(snapshot.schema_bindings) AS binding(value)
                WHERE value->>'dataset_schema_id' = NEW.dataset_schema_id
                  AND value->>'dataset_schema_version' = NEW.dataset_schema_version
            ) THEN
                RAISE EXCEPTION 'Phase 4 observation schema is not server-authorized';
            END IF;
            IF NEW.available_at > snapshot.as_of_utc THEN
                RAISE EXCEPTION 'Phase 4 future-available observation is ineligible';
            END IF;
            IF NEW.availability_precision = 'date'
                AND ((NEW.availability_source_date + 1)::timestamp
                    AT TIME ZONE NEW.source_timezone) IS DISTINCT FROM NEW.available_at THEN
                RAISE EXCEPTION 'Phase 4 date-only availability convention mismatch';
            END IF;

            IF EXISTS (
                SELECT 1 FROM jsonb_array_elements(NEW.quality_flags) AS flag(value)
                WHERE jsonb_typeof(value) <> 'string'
                   OR value #>> '{}' NOT IN (
                       'synthetic_fixture','date_only_convention_applied',
                       'future_availability_excluded','revision_replayed_as_of',
                       'near_duplicate_retained'
                   )
            ) OR jsonb_array_length(NEW.quality_flags) <> (
                SELECT count(DISTINCT value)
                FROM jsonb_array_elements(NEW.quality_flags) AS flag(value)
            ) THEN
                RAISE EXCEPTION 'Phase 4 quality flags are invalid or duplicated';
            END IF;
            IF EXISTS (
                SELECT 1 FROM jsonb_array_elements(NEW.field_missingness) AS missing(value)
                WHERE jsonb_typeof(value) <> 'object'
                   OR btrim(value->>'field_name') = ''
                   OR value->>'reason' NOT IN (
                       'not_applicable','not_provided_by_source',
                       'not_yet_available_as_of','entitlement_restricted',
                       'unresolved_identity','delisting_return_not_provided',
                       'provider_return_already_includes_delisting'
                   )
                   OR (value ? 'source_detail_code'
                       AND value->'source_detail_code' <> 'null'::jsonb
                       AND btrim(value->>'source_detail_code') = '')
            ) OR jsonb_array_length(NEW.field_missingness) <> (
                SELECT count(DISTINCT value->>'field_name')
                FROM jsonb_array_elements(NEW.field_missingness) AS missing(value)
            ) THEN
                RAISE EXCEPTION 'Phase 4 field missingness is invalid or duplicated';
            END IF;

            IF (NEW.retrieved_at IS NULL) <> EXISTS (
                SELECT 1 FROM jsonb_array_elements(NEW.field_missingness) AS missing(value)
                WHERE value->>'field_name' = 'retrieved_at'
            ) OR (NEW.instrument_id IS NULL) <> EXISTS (
                SELECT 1 FROM jsonb_array_elements(NEW.field_missingness) AS missing(value)
                WHERE value->>'field_name' = 'instrument_id'
            ) OR (NEW.listing_id IS NULL) <> EXISTS (
                SELECT 1 FROM jsonb_array_elements(NEW.field_missingness) AS missing(value)
                WHERE value->>'field_name' = 'listing_id'
            ) OR (NEW.valid_to IS NULL) <> EXISTS (
                SELECT 1 FROM jsonb_array_elements(NEW.field_missingness) AS missing(value)
                WHERE value->>'field_name' = 'valid_to'
            ) OR (NEW.calendar_id IS NULL) <> EXISTS (
                SELECT 1 FROM jsonb_array_elements(NEW.field_missingness) AS missing(value)
                WHERE value->>'field_name' = 'calendar_id'
            ) OR (NEW.unit IS NULL) <> EXISTS (
                SELECT 1 FROM jsonb_array_elements(NEW.field_missingness) AS missing(value)
                WHERE value->>'field_name' = 'unit'
            ) OR (NEW.currency IS NULL) <> EXISTS (
                SELECT 1 FROM jsonb_array_elements(NEW.field_missingness) AS missing(value)
                WHERE value->>'field_name' = 'currency'
            ) THEN
                RAISE EXCEPTION 'Phase 4 nullable envelope fields require exact missingness';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    for table in (
        "data_raw_observations",
        "data_observation_revisions",
        "data_normalized_observations",
        "data_snapshot_constituents",
    ):
        op.execute(
            f"""
            CREATE TRIGGER {table}_05_envelope
            BEFORE INSERT ON {table}
            FOR EACH ROW EXECUTE FUNCTION validate_phase4_observation_envelope()
            """
        )

    op.execute(
        """
        CREATE FUNCTION validate_phase4_raw_observation()
        RETURNS trigger AS $$
        BEGIN
            IF encode(sha256(NEW.raw_payload), 'hex')
                    IS DISTINCT FROM NEW.raw_payload_sha256 THEN
                RAISE EXCEPTION 'Phase 4 raw payload hash does not match exact bytes';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER data_raw_observations_10_validate
        BEFORE INSERT ON data_raw_observations
        FOR EACH ROW EXECUTE FUNCTION validate_phase4_raw_observation()
        """
    )

    op.execute(
        """
        CREATE FUNCTION validate_phase4_observation_revision()
        RETURNS trigger AS $$
        DECLARE
            raw_record record;
            predecessor record;
        BEGIN
            SELECT * INTO raw_record
            FROM data_raw_observations
            WHERE snapshot_id = NEW.snapshot_id
              AND raw_observation_id = NEW.raw_observation_id;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'Phase 4 revision raw observation was not found';
            END IF;
            IF NEW.logical_record_id IS DISTINCT FROM raw_record.logical_record_id
                OR NEW.logical_record_key_sha256
                    IS DISTINCT FROM raw_record.logical_record_key_sha256
                OR NEW.provider_id IS DISTINCT FROM raw_record.provider_id
                OR NEW.adapter_id IS DISTINCT FROM raw_record.adapter_id
                OR NEW.adapter_version IS DISTINCT FROM raw_record.adapter_version
                OR NEW.dataset_id IS DISTINCT FROM raw_record.dataset_id
                OR NEW.product_id IS DISTINCT FROM raw_record.product_id
                OR NEW.dataset_schema_id IS DISTINCT FROM raw_record.dataset_schema_id
                OR NEW.dataset_schema_version
                    IS DISTINCT FROM raw_record.dataset_schema_version
                OR NEW.entitlement_id IS DISTINCT FROM raw_record.entitlement_id
                OR NEW.use_rights_id IS DISTINCT FROM raw_record.use_rights_id
                OR NEW.source_record_id IS DISTINCT FROM raw_record.source_record_id
                OR NEW.instrument_id IS DISTINCT FROM raw_record.instrument_id
                OR NEW.listing_id IS DISTINCT FROM raw_record.listing_id
                OR NEW.event_time IS DISTINCT FROM raw_record.event_time
                OR NEW.available_at IS DISTINCT FROM raw_record.available_at
                OR NEW.retrieved_at IS DISTINCT FROM raw_record.retrieved_at
                OR NEW.valid_from IS DISTINCT FROM raw_record.valid_from
                OR NEW.valid_to IS DISTINCT FROM raw_record.valid_to
                OR NEW.revision_id IS DISTINCT FROM raw_record.revision_id
                OR NEW.vintage_id IS DISTINCT FROM raw_record.vintage_id
                OR NEW.source_timezone IS DISTINCT FROM raw_record.source_timezone
                OR NEW.calendar_id IS DISTINCT FROM raw_record.calendar_id
                OR NEW.unit IS DISTINCT FROM raw_record.unit
                OR NEW.currency IS DISTINCT FROM raw_record.currency
                OR NEW.availability_precision
                    IS DISTINCT FROM raw_record.availability_precision
                OR NEW.availability_convention
                    IS DISTINCT FROM raw_record.availability_convention
                OR NEW.availability_source_date
                    IS DISTINCT FROM raw_record.availability_source_date
                OR NEW.raw_payload_sha256 IS DISTINCT FROM raw_record.raw_payload_sha256 THEN
                RAISE EXCEPTION 'Phase 4 revision cannot alter raw lineage';
            END IF;

            IF NEW.revision_sequence > 1 THEN
                SELECT * INTO predecessor
                FROM data_observation_revisions
                WHERE snapshot_id = NEW.snapshot_id
                  AND revision_record_id = NEW.predecessor_revision_record_id;
                IF NOT FOUND THEN
                    RAISE EXCEPTION 'Phase 4 predecessor revision was not found';
                END IF;
                IF predecessor.logical_record_key_sha256
                        IS DISTINCT FROM NEW.logical_record_key_sha256
                    OR predecessor.revision_sequence + 1 <> NEW.revision_sequence THEN
                    RAISE EXCEPTION 'Phase 4 predecessor must be prior logical-key sequence';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER data_observation_revisions_10_validate
        BEFORE INSERT ON data_observation_revisions
        FOR EACH ROW EXECUTE FUNCTION validate_phase4_observation_revision()
        """
    )

    op.execute(
        """
        CREATE FUNCTION phase4_record_type_matches_capability(
            checked_record_type text,
            checked_capability text
        ) RETURNS boolean AS $$
            SELECT CASE checked_capability
                WHEN 'security_master' THEN checked_record_type IN (
                    'instrument_identity', 'listing_identity'
                )
                WHEN 'universe_membership' THEN
                    checked_record_type = 'universe_membership'
                WHEN 'ohlcv' THEN checked_record_type = 'ohlcv_bar'
                WHEN 'corporate_actions' THEN checked_record_type = 'corporate_action'
                WHEN 'delistings' THEN checked_record_type = 'delisting_event'
                WHEN 'as_reported_fundamentals' THEN
                    checked_record_type = 'as_reported_fundamental'
                WHEN 'trading_calendar' THEN checked_record_type = 'calendar_session'
                WHEN 'volatility_return_inputs' THEN
                    checked_record_type = 'volatility_return_input'
                WHEN 'official_document_event_metadata' THEN
                    checked_record_type = 'official_document_event'
                ELSE false
            END
        $$ LANGUAGE sql IMMUTABLE
        """
    )
    op.execute(
        """
        CREATE FUNCTION validate_phase4_normalized_observation()
        RETURNS trigger AS $$
        DECLARE
            raw_record record;
            revision record;
            snapshot_capability text;
            normalized_record_type text;
        BEGIN
            SELECT * INTO raw_record
            FROM data_raw_observations
            WHERE snapshot_id = NEW.snapshot_id
              AND raw_observation_id = NEW.raw_observation_id;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'Phase 4 normalized raw observation was not found';
            END IF;
            SELECT * INTO revision
            FROM data_observation_revisions
            WHERE snapshot_id = NEW.snapshot_id
              AND revision_record_id = NEW.observation_revision_id;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'Phase 4 normalized revision was not found';
            END IF;
            IF revision.raw_observation_id IS DISTINCT FROM NEW.raw_observation_id
                OR revision.logical_record_key_sha256
                    IS DISTINCT FROM NEW.logical_record_key_sha256 THEN
                RAISE EXCEPTION 'Phase 4 normalized raw/revision chain mismatch';
            END IF;
            IF NEW.logical_record_id IS DISTINCT FROM raw_record.logical_record_id
                OR NEW.logical_record_key_sha256
                    IS DISTINCT FROM raw_record.logical_record_key_sha256
                OR NEW.provider_id IS DISTINCT FROM raw_record.provider_id
                OR NEW.adapter_id IS DISTINCT FROM raw_record.adapter_id
                OR NEW.adapter_version IS DISTINCT FROM raw_record.adapter_version
                OR NEW.dataset_id IS DISTINCT FROM raw_record.dataset_id
                OR NEW.product_id IS DISTINCT FROM raw_record.product_id
                OR NEW.dataset_schema_id IS DISTINCT FROM raw_record.dataset_schema_id
                OR NEW.dataset_schema_version
                    IS DISTINCT FROM raw_record.dataset_schema_version
                OR NEW.entitlement_id IS DISTINCT FROM raw_record.entitlement_id
                OR NEW.use_rights_id IS DISTINCT FROM raw_record.use_rights_id
                OR NEW.source_record_id IS DISTINCT FROM raw_record.source_record_id
                OR NEW.instrument_id IS DISTINCT FROM raw_record.instrument_id
                OR NEW.listing_id IS DISTINCT FROM raw_record.listing_id
                OR NEW.event_time IS DISTINCT FROM raw_record.event_time
                OR NEW.available_at IS DISTINCT FROM raw_record.available_at
                OR NEW.retrieved_at IS DISTINCT FROM raw_record.retrieved_at
                OR NEW.valid_from IS DISTINCT FROM raw_record.valid_from
                OR NEW.valid_to IS DISTINCT FROM raw_record.valid_to
                OR NEW.revision_id IS DISTINCT FROM raw_record.revision_id
                OR NEW.vintage_id IS DISTINCT FROM raw_record.vintage_id
                OR NEW.source_timezone IS DISTINCT FROM raw_record.source_timezone
                OR NEW.calendar_id IS DISTINCT FROM raw_record.calendar_id
                OR NEW.unit IS DISTINCT FROM raw_record.unit
                OR NEW.currency IS DISTINCT FROM raw_record.currency
                OR NEW.availability_precision
                    IS DISTINCT FROM raw_record.availability_precision
                OR NEW.availability_convention
                    IS DISTINCT FROM raw_record.availability_convention
                OR NEW.availability_source_date
                    IS DISTINCT FROM raw_record.availability_source_date
                OR NEW.raw_payload_sha256 IS DISTINCT FROM raw_record.raw_payload_sha256 THEN
                RAISE EXCEPTION 'Phase 4 normalized observation cannot alter raw lineage';
            END IF;

            normalized_record_type := NEW.payload->>'record_type';
            SELECT capability INTO snapshot_capability
            FROM data_snapshots WHERE snapshot_id = NEW.snapshot_id;
            IF NOT phase4_record_type_matches_capability(
                normalized_record_type,
                snapshot_capability
            ) THEN
                RAISE EXCEPTION 'Phase 4 normalized record type conflicts with capability';
            END IF;
            IF normalized_record_type <> 'calendar_session'
                    AND NEW.instrument_id IS NULL
                OR normalized_record_type IN (
                    'listing_identity','universe_membership','ohlcv_bar',
                    'delisting_event','volatility_return_input'
                ) AND NEW.listing_id IS NULL
                OR normalized_record_type IN ('instrument_identity','calendar_session')
                    AND NEW.listing_id IS NOT NULL
                OR normalized_record_type = 'calendar_session'
                    AND NEW.instrument_id IS NOT NULL THEN
                RAISE EXCEPTION 'Phase 4 normalized stable identity scope is invalid';
            END IF;
            IF normalized_record_type = 'ohlcv_bar'
                    AND NEW.payload->>'adjustment_as_of' IS NOT NULL
                    AND (NEW.payload->>'adjustment_as_of')::timestamptz > NEW.available_at
                OR normalized_record_type = 'corporate_action'
                    AND (NEW.payload->>'announcement_at')::timestamptz > NEW.available_at
                OR normalized_record_type = 'as_reported_fundamental'
                    AND (NEW.payload->>'filing_accepted_at')::timestamptz > NEW.available_at
                OR normalized_record_type = 'official_document_event'
                    AND (NEW.payload->>'accepted_at')::timestamptz > NEW.available_at THEN
                RAISE EXCEPTION 'Phase 4 normalized payload contains future knowledge';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER data_normalized_observations_10_validate
        BEFORE INSERT ON data_normalized_observations
        FOR EACH ROW EXECUTE FUNCTION validate_phase4_normalized_observation()
        """
    )

    op.execute(
        """
        CREATE FUNCTION validate_phase4_snapshot_constituent()
        RETURNS trigger AS $$
        DECLARE
            normalized record;
            revision record;
        BEGIN
            SELECT * INTO normalized
            FROM data_normalized_observations
            WHERE snapshot_id = NEW.snapshot_id
              AND normalized_observation_id = NEW.normalized_observation_id;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'Phase 4 constituent normalized observation was not found';
            END IF;
            SELECT * INTO revision
            FROM data_observation_revisions
            WHERE snapshot_id = NEW.snapshot_id
              AND revision_record_id = NEW.observation_revision_id;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'Phase 4 constituent revision was not found';
            END IF;
            IF NEW.raw_observation_id IS DISTINCT FROM normalized.raw_observation_id
                OR NEW.observation_revision_id
                    IS DISTINCT FROM normalized.observation_revision_id
                OR revision.raw_observation_id IS DISTINCT FROM NEW.raw_observation_id
                OR NEW.logical_record_id IS DISTINCT FROM normalized.logical_record_id
                OR NEW.logical_record_key_sha256
                    IS DISTINCT FROM normalized.logical_record_key_sha256
                OR NEW.raw_payload_sha256 IS DISTINCT FROM normalized.raw_payload_sha256
                OR NEW.normalized_content_sha256
                    IS DISTINCT FROM normalized.normalized_content_sha256
                OR NEW.revision_id IS DISTINCT FROM normalized.revision_id
                OR NEW.vintage_id IS DISTINCT FROM normalized.vintage_id
                OR NEW.record_type IS DISTINCT FROM normalized.payload->>'record_type' THEN
                RAISE EXCEPTION 'Phase 4 constituent lineage mismatch';
            END IF;
            IF NOT phase4_record_type_matches_capability(
                NEW.record_type,
                (SELECT capability FROM data_snapshots WHERE snapshot_id = NEW.snapshot_id)
            ) THEN
                RAISE EXCEPTION 'Phase 4 constituent record type conflicts with capability';
            END IF;

            IF NEW.manifest_entry->>'envelope_schema_version'
                    IS DISTINCT FROM NEW.envelope_schema_version
                OR NEW.manifest_entry->>'logical_record_id'
                    IS DISTINCT FROM NEW.logical_record_id
                OR NEW.manifest_entry->>'logical_record_key_sha256'
                    IS DISTINCT FROM NEW.logical_record_key_sha256
                OR NEW.manifest_entry->>'provider_id' IS DISTINCT FROM NEW.provider_id
                OR NEW.manifest_entry->>'adapter_id' IS DISTINCT FROM NEW.adapter_id
                OR NEW.manifest_entry->>'adapter_version'
                    IS DISTINCT FROM NEW.adapter_version
                OR NEW.manifest_entry->>'dataset_id' IS DISTINCT FROM NEW.dataset_id
                OR NEW.manifest_entry->>'product_id' IS DISTINCT FROM NEW.product_id
                OR NEW.manifest_entry->>'dataset_schema_id'
                    IS DISTINCT FROM NEW.dataset_schema_id
                OR NEW.manifest_entry->>'dataset_schema_version'
                    IS DISTINCT FROM NEW.dataset_schema_version
                OR NEW.manifest_entry->>'entitlement_id'
                    IS DISTINCT FROM NEW.entitlement_id
                OR NEW.manifest_entry->>'use_rights_id'
                    IS DISTINCT FROM NEW.use_rights_id
                OR NEW.manifest_entry->>'source_record_id'
                    IS DISTINCT FROM NEW.source_record_id
                OR (NEW.manifest_entry->>'instrument_id')::uuid
                    IS DISTINCT FROM NEW.instrument_id
                OR (NEW.manifest_entry->>'listing_id')::uuid
                    IS DISTINCT FROM NEW.listing_id
                OR (NEW.manifest_entry->>'event_time')::timestamptz
                    IS DISTINCT FROM NEW.event_time
                OR (NEW.manifest_entry->>'available_at')::timestamptz
                    IS DISTINCT FROM NEW.available_at
                OR (NEW.manifest_entry->>'retrieved_at')::timestamptz
                    IS DISTINCT FROM NEW.retrieved_at
                OR (NEW.manifest_entry->>'valid_from')::timestamptz
                    IS DISTINCT FROM NEW.valid_from
                OR (NEW.manifest_entry->>'valid_to')::timestamptz
                    IS DISTINCT FROM NEW.valid_to
                OR NEW.manifest_entry->>'revision_id' IS DISTINCT FROM NEW.revision_id
                OR NEW.manifest_entry->>'vintage_id' IS DISTINCT FROM NEW.vintage_id
                OR NEW.manifest_entry->>'source_timezone'
                    IS DISTINCT FROM NEW.source_timezone
                OR NEW.manifest_entry->>'calendar_id' IS DISTINCT FROM NEW.calendar_id
                OR NEW.manifest_entry->>'unit' IS DISTINCT FROM NEW.unit
                OR NEW.manifest_entry->>'currency' IS DISTINCT FROM NEW.currency
                OR NEW.manifest_entry->>'availability_precision'
                    IS DISTINCT FROM NEW.availability_precision
                OR NEW.manifest_entry->>'availability_convention'
                    IS DISTINCT FROM NEW.availability_convention
                OR (NEW.manifest_entry->>'availability_source_date')::date
                    IS DISTINCT FROM NEW.availability_source_date
                OR NEW.manifest_entry->'quality_flags' IS DISTINCT FROM NEW.quality_flags
                OR NEW.manifest_entry->'field_missingness'
                    IS DISTINCT FROM NEW.field_missingness
                OR NEW.manifest_entry->>'raw_payload_sha256'
                    IS DISTINCT FROM NEW.raw_payload_sha256
                OR NEW.manifest_entry->>'record_type' IS DISTINCT FROM NEW.record_type
                OR (NEW.manifest_entry->>'raw_observation_id')::uuid
                    IS DISTINCT FROM NEW.raw_observation_id
                OR (NEW.manifest_entry->>'observation_revision_id')::uuid
                    IS DISTINCT FROM NEW.observation_revision_id
                OR (NEW.manifest_entry->>'normalized_observation_id')::uuid
                    IS DISTINCT FROM NEW.normalized_observation_id
                OR NEW.manifest_entry->>'normalized_content_sha256'
                    IS DISTINCT FROM NEW.normalized_content_sha256
                OR NEW.manifest_entry->>'disposition' IS DISTINCT FROM NEW.disposition THEN
                RAISE EXCEPTION 'Phase 4 constituent manifest entry mismatch';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER data_snapshot_constituents_10_validate
        BEFORE INSERT ON data_snapshot_constituents
        FOR EACH ROW EXECUTE FUNCTION validate_phase4_snapshot_constituent()
        """
    )

    op.execute(
        """
        CREATE FUNCTION validate_phase4_quality_finding()
        RETURNS trigger AS $$
        DECLARE
            snapshot_hash text;
        BEGIN
            SELECT snapshot_sha256 INTO snapshot_hash
            FROM data_snapshots WHERE snapshot_id = NEW.snapshot_id;
            IF NOT FOUND OR NEW.snapshot_sha256 IS DISTINCT FROM snapshot_hash THEN
                RAISE EXCEPTION 'Phase 4 quality finding snapshot mismatch';
            END IF;
            IF NEW.manifest_entry->>'finding_id' IS DISTINCT FROM NEW.finding_id::text
                OR NEW.manifest_entry->>'finding_sha256'
                    IS DISTINCT FROM NEW.finding_sha256
                OR NEW.manifest_entry->>'rule_set_version'
                    IS DISTINCT FROM NEW.rule_set_version
                OR NEW.manifest_entry->>'rule_id' IS DISTINCT FROM NEW.rule_id
                OR NEW.manifest_entry->>'severity' IS DISTINCT FROM NEW.severity
                OR NEW.manifest_entry->>'code' IS DISTINCT FROM NEW.code
                OR NEW.manifest_entry->>'affected_record_type'
                    IS DISTINCT FROM NEW.affected_record_type
                OR NEW.manifest_entry->>'affected_record_identity'
                    IS DISTINCT FROM NEW.affected_record_identity
                OR NEW.manifest_entry->>'raw_payload_sha256'
                    IS DISTINCT FROM NEW.raw_payload_sha256
                OR NEW.manifest_entry->>'normalized_content_sha256'
                    IS DISTINCT FROM NEW.normalized_content_sha256
                OR NEW.manifest_entry->>'field_name' IS DISTINCT FROM NEW.field_name
                OR NEW.manifest_entry->>'disposition' IS DISTINCT FROM NEW.disposition
                OR (NEW.manifest_entry->>'occurrence_count')::integer
                    IS DISTINCT FROM NEW.occurrence_count
                OR (NEW.manifest_entry->>'occurrence_rate')::numeric
                    IS DISTINCT FROM NEW.occurrence_rate
                OR (NEW.manifest_entry->>'range_start_utc')::timestamptz
                    IS DISTINCT FROM NEW.range_start_utc
                OR (NEW.manifest_entry->>'range_end_utc')::timestamptz
                    IS DISTINCT FROM NEW.range_end_utc
                OR NEW.manifest_entry->'sanitized_detail'
                    IS DISTINCT FROM NEW.sanitized_detail THEN
                RAISE EXCEPTION 'Phase 4 quality finding manifest entry mismatch';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER data_quality_findings_10_validate
        BEFORE INSERT ON data_quality_findings
        FOR EACH ROW EXECUTE FUNCTION validate_phase4_quality_finding()
        """
    )

    op.execute(
        """
        CREATE FUNCTION validate_phase4_snapshot_manifest()
        RETURNS trigger AS $$
        DECLARE
            snapshot record;
            actual_raw_count bigint;
            actual_revision_count bigint;
            actual_normalized_count bigint;
            actual_constituent_count bigint;
            actual_active_count bigint;
            actual_quality_count bigint;
            blocked_count bigint;
            warning_count bigint;
            full_constituents jsonb;
            full_findings jsonb;
            identity_constituents jsonb;
            identity_findings jsonb;
            expected_identity_payload jsonb;
        BEGIN
            SELECT * INTO snapshot
            FROM data_snapshots
            WHERE snapshot_id = NEW.snapshot_id
            FOR UPDATE;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'Phase 4 manifest snapshot was not found';
            END IF;
            IF EXISTS (
                SELECT 1 FROM data_snapshot_manifests
                WHERE snapshot_id = NEW.snapshot_id
            ) THEN
                RAISE EXCEPTION 'Phase 4 snapshot is already finalized';
            END IF;
            IF NEW.snapshot_sha256 IS DISTINCT FROM snapshot.snapshot_sha256
                OR NEW.request_fingerprint_sha256
                    IS DISTINCT FROM snapshot.request_fingerprint_sha256
                OR NEW.raw_observation_count
                    IS DISTINCT FROM snapshot.raw_observation_count
                OR NEW.revision_count IS DISTINCT FROM snapshot.revision_count
                OR NEW.normalized_observation_count
                    IS DISTINCT FROM snapshot.normalized_observation_count
                OR NEW.constituent_count IS DISTINCT FROM snapshot.constituent_count
                OR NEW.active_constituent_count
                    IS DISTINCT FROM snapshot.active_constituent_count
                OR NEW.quality_finding_count
                    IS DISTINCT FROM snapshot.quality_finding_count
                OR NEW.quality_status IS DISTINCT FROM snapshot.quality_status THEN
                RAISE EXCEPTION 'Phase 4 manifest does not match snapshot header';
            END IF;

            SELECT count(*) INTO actual_raw_count
            FROM data_raw_observations WHERE snapshot_id = NEW.snapshot_id;
            SELECT count(*) INTO actual_revision_count
            FROM data_observation_revisions WHERE snapshot_id = NEW.snapshot_id;
            SELECT count(*) INTO actual_normalized_count
            FROM data_normalized_observations WHERE snapshot_id = NEW.snapshot_id;
            SELECT
                count(*),
                count(*) FILTER (
                    WHERE disposition IN ('included_as_of','explicit_missingness')
                ),
                COALESCE(jsonb_agg(manifest_entry ORDER BY ordinal_position), '[]'::jsonb),
                COALESCE(
                    jsonb_agg(
                        jsonb_build_object(
                            'record_type', record_type,
                            'logical_record_id', logical_record_id,
                            'logical_record_key_sha256', logical_record_key_sha256,
                            'revision_id', revision_id,
                            'vintage_id', vintage_id,
                            'raw_payload_sha256', raw_payload_sha256,
                            'normalized_content_sha256', normalized_content_sha256,
                            'quality_flags', quality_flags,
                            'field_missingness', field_missingness,
                            'disposition', disposition
                        ) ORDER BY ordinal_position
                    ),
                    '[]'::jsonb
                )
            INTO
                actual_constituent_count,
                actual_active_count,
                full_constituents,
                identity_constituents
            FROM data_snapshot_constituents
            WHERE snapshot_id = NEW.snapshot_id;
            SELECT
                count(*),
                count(*) FILTER (
                    WHERE disposition = 'blocked' OR severity = 'blocking'
                ),
                count(*) FILTER (
                    WHERE severity IN ('warning','error') OR disposition = 'excluded'
                ),
                COALESCE(jsonb_agg(manifest_entry ORDER BY ordinal_position), '[]'::jsonb),
                COALESCE(
                    jsonb_agg(
                        jsonb_build_object('finding_sha256', finding_sha256)
                        ORDER BY ordinal_position
                    ),
                    '[]'::jsonb
                )
            INTO
                actual_quality_count,
                blocked_count,
                warning_count,
                full_findings,
                identity_findings
            FROM data_quality_findings
            WHERE snapshot_id = NEW.snapshot_id;

            IF actual_raw_count <> NEW.raw_observation_count
                OR actual_revision_count <> NEW.revision_count
                OR actual_normalized_count <> NEW.normalized_observation_count
                OR actual_constituent_count <> NEW.constituent_count
                OR actual_active_count <> NEW.active_constituent_count
                OR actual_quality_count <> NEW.quality_finding_count THEN
                RAISE EXCEPTION 'Phase 4 manifest independent count mismatch';
            END IF;
            IF blocked_count > 0 THEN
                RAISE EXCEPTION 'Phase 4 blocked quality findings cannot be persisted';
            END IF;
            IF (warning_count = 0
                    AND NEW.quality_status <> 'data_quality_accepted')
                OR (warning_count > 0
                    AND NEW.quality_status
                        <> 'data_quality_accepted_with_warnings') THEN
                RAISE EXCEPTION 'Phase 4 manifest quality status mismatch';
            END IF;

            IF EXISTS (
                SELECT 1 FROM (
                    SELECT
                        ordinal_position,
                        row_number() OVER (
                            ORDER BY
                                record_type,
                                logical_record_id,
                                logical_record_key_sha256,
                                revision_id,
                                vintage_id,
                                raw_payload_sha256,
                                normalized_content_sha256,
                                disposition
                        ) AS expected_ordinal
                    FROM data_snapshot_constituents
                    WHERE snapshot_id = NEW.snapshot_id
                ) AS ordered_constituents
                WHERE ordinal_position <> expected_ordinal
            ) THEN
                RAISE EXCEPTION 'Phase 4 constituent order is not canonical';
            END IF;
            IF EXISTS (
                SELECT 1 FROM (
                    SELECT
                        ordinal_position,
                        row_number() OVER (
                            ORDER BY
                                rule_set_version,
                                rule_id,
                                severity,
                                code,
                                COALESCE(affected_record_type, ''),
                                COALESCE(affected_record_identity, ''),
                                COALESCE(raw_payload_sha256, ''),
                                COALESCE(normalized_content_sha256, ''),
                                COALESCE(field_name, ''),
                                disposition,
                                finding_sha256
                        ) AS expected_ordinal
                    FROM data_quality_findings
                    WHERE snapshot_id = NEW.snapshot_id
                ) AS ordered_findings
                WHERE ordinal_position <> expected_ordinal
            ) THEN
                RAISE EXCEPTION 'Phase 4 quality finding order is not canonical';
            END IF;

            IF NEW.payload->>'canonicalization_version'
                    IS DISTINCT FROM snapshot.canonicalization_version
                OR NEW.payload->>'snapshot_schema_version'
                    IS DISTINCT FROM snapshot.snapshot_schema_version
                OR NEW.payload->>'request_fingerprint_sha256'
                    IS DISTINCT FROM snapshot.request_fingerprint_sha256
                OR NEW.payload->'mapping'
                    IS DISTINCT FROM snapshot.request_fingerprint_payload#>'{request,mapping}'
                OR NEW.payload->'request'
                    IS DISTINCT FROM snapshot.request_fingerprint_payload->'request'
                OR NEW.payload->'adapter'
                    IS DISTINCT FROM snapshot.request_fingerprint_payload->'adapter'
                OR NEW.payload->'schema_bindings'
                    IS DISTINCT FROM snapshot.request_fingerprint_payload->'schema_bindings'
                OR NEW.payload->'use_rights'
                    IS DISTINCT FROM snapshot.request_fingerprint_payload->'use_rights'
                OR NEW.payload->'configuration'
                    IS DISTINCT FROM snapshot.request_fingerprint_payload->'configuration'
                OR NEW.payload->'constituents' IS DISTINCT FROM full_constituents
                OR NEW.payload->'quality_findings' IS DISTINCT FROM full_findings THEN
                RAISE EXCEPTION 'Phase 4 manifest payload is not exact';
            END IF;

            expected_identity_payload :=
                (NEW.payload - 'constituents' - 'quality_findings')
                || jsonb_build_object(
                    'constituents', identity_constituents,
                    'quality_findings', identity_findings
                );
            IF NEW.identity_payload IS DISTINCT FROM expected_identity_payload
                OR NEW.identity_canonical_json::jsonb
                    IS DISTINCT FROM NEW.identity_payload
                OR encode(
                    sha256(
                        convert_to('phase4-data-snapshot-v1', 'UTF8')
                        || decode('00', 'hex')
                        || convert_to(NEW.identity_canonical_json, 'UTF8')
                    ),
                    'hex'
                ) IS DISTINCT FROM NEW.snapshot_sha256 THEN
                RAISE EXCEPTION 'Phase 4 canonical snapshot identity mismatch';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER data_snapshot_manifests_10_validate
        BEFORE INSERT ON data_snapshot_manifests
        FOR EACH ROW EXECUTE FUNCTION validate_phase4_snapshot_manifest()
        """
    )

    op.execute(
        """
        CREATE FUNCTION validate_phase4_snapshot_finalization()
        RETURNS trigger AS $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM data_snapshot_manifests
                WHERE snapshot_id = NEW.snapshot_id
            ) THEN
                RAISE EXCEPTION 'Phase 4 snapshot cannot commit without a manifest';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER data_snapshots_manifest_required
        AFTER INSERT ON data_snapshots
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION validate_phase4_snapshot_finalization()
        """
    )

    op.execute(
        """
        CREATE FUNCTION reject_phase4_data_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'Phase 4 data records are append-only';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    for table in PHASE4_TABLES:
        op.execute(
            f"""
            CREATE TRIGGER {table}_immutable
            BEFORE UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION reject_phase4_data_mutation()
            """
        )
        op.execute(
            f"""
            CREATE TRIGGER {table}_no_truncate
            BEFORE TRUNCATE ON {table}
            FOR EACH STATEMENT EXECUTE FUNCTION reject_phase4_data_mutation()
            """
        )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS data_snapshots_manifest_required ON data_snapshots")
    op.execute(
        "DROP TRIGGER IF EXISTS data_snapshot_manifests_10_validate ON data_snapshot_manifests"
    )
    op.execute("DROP TRIGGER IF EXISTS data_quality_findings_10_validate ON data_quality_findings")
    op.execute(
        "DROP TRIGGER IF EXISTS data_snapshot_constituents_10_validate "
        "ON data_snapshot_constituents"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS data_normalized_observations_10_validate "
        "ON data_normalized_observations"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS data_observation_revisions_10_validate "
        "ON data_observation_revisions"
    )
    op.execute("DROP TRIGGER IF EXISTS data_raw_observations_10_validate ON data_raw_observations")
    op.execute("DROP TRIGGER IF EXISTS data_snapshots_10_request_gate ON data_snapshots")
    for table in reversed(
        (
            "data_raw_observations",
            "data_observation_revisions",
            "data_normalized_observations",
            "data_snapshot_constituents",
        )
    ):
        op.execute(f"DROP TRIGGER IF EXISTS {table}_05_envelope ON {table}")
    for table in reversed(PHASE4_CHILD_TABLES):
        op.execute(f"DROP TRIGGER IF EXISTS {table}_00_unfinalized ON {table}")
    for table in reversed(PHASE4_TABLES):
        op.execute(f"DROP TRIGGER IF EXISTS {table}_no_truncate ON {table}")
        op.execute(f"DROP TRIGGER IF EXISTS {table}_immutable ON {table}")

    op.execute("DROP FUNCTION IF EXISTS reject_phase4_data_mutation()")
    op.execute("DROP FUNCTION IF EXISTS validate_phase4_snapshot_finalization()")
    op.execute("DROP FUNCTION IF EXISTS validate_phase4_snapshot_manifest()")
    op.execute("DROP FUNCTION IF EXISTS validate_phase4_quality_finding()")
    op.execute("DROP FUNCTION IF EXISTS validate_phase4_snapshot_constituent()")
    op.execute("DROP FUNCTION IF EXISTS validate_phase4_normalized_observation()")
    op.execute("DROP FUNCTION IF EXISTS phase4_record_type_matches_capability(text, text)")
    op.execute("DROP FUNCTION IF EXISTS validate_phase4_observation_revision()")
    op.execute("DROP FUNCTION IF EXISTS validate_phase4_raw_observation()")
    op.execute("DROP FUNCTION IF EXISTS validate_phase4_observation_envelope()")
    op.execute("DROP FUNCTION IF EXISTS guard_phase4_unfinalized_snapshot()")
    op.execute("DROP FUNCTION IF EXISTS validate_phase4_snapshot_request()")

    op.drop_table("data_snapshot_manifests")
    op.drop_table("data_quality_findings")
    op.drop_table("data_snapshot_constituents")
    op.drop_index(
        "ix_data_normalized_observations_snapshot_key",
        table_name="data_normalized_observations",
    )
    op.drop_table("data_normalized_observations")
    op.drop_index(
        "ix_data_observation_revisions_snapshot_key",
        table_name="data_observation_revisions",
    )
    op.drop_table("data_observation_revisions")
    op.drop_index(
        "ix_data_raw_observations_snapshot_key",
        table_name="data_raw_observations",
    )
    op.drop_table("data_raw_observations")
    op.drop_index("ix_data_snapshots_created", table_name="data_snapshots")
    op.drop_index("ix_data_snapshots_mapping_as_of", table_name="data_snapshots")
    op.drop_table("data_snapshots")
