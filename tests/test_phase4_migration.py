from __future__ import annotations

import ast
import hashlib
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_SRC = ROOT / "services/data/src"
sys.path.insert(0, str(DATA_SRC))

from fable5_data.contracts import (  # noqa: E402
    PHASE4_SCHEMA_CONSTANTS,
    PHASE6_DATA_CONTRACT_CONSTANTS,
    AvailabilityConvention,
    AvailabilityPrecision,
    ConstituentDisposition,
    DataCapability,
    DataQualityCode,
    DataQualityFinding,
    DataQualitySeverity,
    DataRecordType,
    DataSnapshot,
    FindingDisposition,
    MissingnessReason,
    NormalizedObservation,
    ObservationRevision,
    QualityFlag,
    RawObservation,
    SnapshotConstituent,
    SnapshotManifest,
    SnapshotQualityStatus,
)

MIGRATION = ROOT / "services/api/migrations/versions/0004_phase4_point_in_time_data.py"
PRIOR_MIGRATIONS = {
    "0001_phase1_audit_spine.py": (
        "5cd27e1bde6b03720f54fe5e1260cf5f9085e16a4eebed957aeeba1a3a7d17f8"
    ),
    "0002_phase2_source_extraction.py": (
        "d45c1cb0ade079cfba7492c75c1aff13fc714aaae0a81637f21942c175c4e5c8"
    ),
    "0003_phase3_canon_mapping.py": (
        "6859c63723dc31d6ede4cdd5528a42640f16e3c6103567b5d900a46741edf07d"
    ),
}
PHASE4_TABLES = {
    "data_snapshots",
    "data_raw_observations",
    "data_observation_revisions",
    "data_normalized_observations",
    "data_snapshot_constituents",
    "data_quality_findings",
    "data_snapshot_manifests",
}
ENVELOPE_COLUMNS = {
    "snapshot_id",
    "snapshot_sha256",
    "envelope_schema_version",
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
    "quality_flags",
    "field_missingness",
    "raw_payload_sha256",
}


def migration_source() -> str:
    return MIGRATION.read_text(encoding="utf-8")


def migration_tree() -> ast.Module:
    return ast.parse(migration_source())


def function_node(name: str) -> ast.FunctionDef:
    for node in migration_tree().body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"missing migration function {name}")


def function_source(name: str) -> str:
    rendered = ast.get_source_segment(migration_source(), function_node(name))
    assert rendered is not None
    return rendered


def literal_table_calls(function_name: str, operation: str) -> set[str]:
    result: set[str] = set()
    for call in ast.walk(function_node(function_name)):
        if (
            isinstance(call, ast.Call)
            and isinstance(call.func, ast.Attribute)
            and call.func.attr == operation
            and call.args
            and isinstance(call.args[0], ast.Constant)
            and isinstance(call.args[0].value, str)
        ):
            result.add(call.args[0].value)
    return result


def created_table_columns() -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for call in ast.walk(function_node("upgrade")):
        if not (
            isinstance(call, ast.Call)
            and isinstance(call.func, ast.Attribute)
            and call.func.attr == "create_table"
            and call.args
            and isinstance(call.args[0], ast.Constant)
        ):
            continue
        table = call.args[0].value
        columns: set[str] = set()
        for argument in call.args[1:]:
            if (
                isinstance(argument, ast.Call)
                and isinstance(argument.func, ast.Attribute)
                and argument.func.attr == "Column"
                and argument.args
                and isinstance(argument.args[0], ast.Constant)
            ):
                columns.add(argument.args[0].value)
            elif (
                isinstance(argument, ast.Starred)
                and isinstance(argument.value, ast.Call)
                and isinstance(argument.value.func, ast.Name)
                and argument.value.func.id == "_observation_envelope_columns"
            ):
                columns.update(ENVELOPE_COLUMNS)
            elif (
                isinstance(argument, ast.Call)
                and isinstance(argument.func, ast.Name)
                and argument.func.id == "_created_at"
            ):
                columns.add("created_at_utc")
        result[table] = columns
    return result


def enum_values(enum_type: type[Any]) -> tuple[str, ...]:
    return tuple(item.value for item in enum_type)


def test_phase4_revision_and_prior_migration_bytes_are_exact() -> None:
    source = migration_source()
    assignments = {
        node.target.id: node.value.value
        for node in migration_tree().body
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and isinstance(node.value, ast.Constant)
    }
    assert assignments["revision"] == "0004_phase4"
    assert assignments["down_revision"] == "0003_phase3"
    assert "create_all" not in source

    versions = ROOT / "services/api/migrations/versions"
    for filename, expected_hash in PRIOR_MIGRATIONS.items():
        assert hashlib.sha256((versions / filename).read_bytes()).hexdigest() == expected_hash


def test_phase4_owns_exactly_seven_tables_with_restrictive_snapshot_scoped_keys() -> None:
    source = migration_source()
    assert literal_table_calls("upgrade", "create_table") == PHASE4_TABLES
    assert literal_table_calls("downgrade", "drop_table") == PHASE4_TABLES
    assert source.count('ondelete="RESTRICT"') == 14
    for identity in (
        "raw_observation_id",
        "revision_record_id",
        "normalized_observation_id",
        "finding_id",
    ):
        assert f'"snapshot_id",\n            "{identity}"' in source
    assert "uq_data_observation_revision_logical_sequence" in source
    assert '"source_record_id",\n            "revision_sequence"' not in source


def test_phase4_sql_vocabularies_and_versions_equal_contract_authority() -> None:
    source = migration_source()
    for key in (
        "canonicalization_version",
        "snapshot_schema_version",
        "raw_observation_schema_version",
        "normalized_observation_schema_version",
        "revision_schema_version",
        "quality_rule_set_version",
        "request_fingerprint_version",
        "date_only_availability_convention",
    ):
        assert f"'{PHASE4_SCHEMA_CONSTANTS[key]}'" in source

    for key in (
        "capabilities",
        "record_types",
        "constituent_dispositions",
        "finding_dispositions",
        "quality_severities",
        "snapshot_quality_statuses",
    ):
        assert tuple(PHASE4_SCHEMA_CONSTANTS[key])
        for value in PHASE4_SCHEMA_CONSTANTS[key]:
            assert f"'{value}'" in source

    phase6_quality_codes = set(PHASE6_DATA_CONTRACT_CONSTANTS["additive_quality_codes"])
    phase4_enum_values = {
        DataRecordType: tuple(PHASE4_SCHEMA_CONSTANTS["record_types"]),
        DataQualityCode: tuple(
            value for value in enum_values(DataQualityCode) if value not in phase6_quality_codes
        ),
    }
    for enum_type in (
        DataCapability,
        ConstituentDisposition,
        FindingDisposition,
        DataQualitySeverity,
        SnapshotQualityStatus,
        MissingnessReason,
        QualityFlag,
        AvailabilityPrecision,
        AvailabilityConvention,
    ):
        for value in enum_values(enum_type):
            assert f"'{value}'" in source
    for values in phase4_enum_values.values():
        for value in values:
            assert f"'{value}'" in source

    for rejected_parallel_value in (
        "'SECURITY_MASTER'",
        "'OHLCV_BAR'",
        "'DATA_QUALITY_ACCEPTED'",
        "'SUPERSEDED_VINTAGE'",
        "'CRITICAL'",
        "'phase4-pit-schema-v1'",
        "'phase4-snapshot-c14n-v1'",
    ):
        assert rejected_parallel_value not in source


def test_phase4_bound_pydantic_models_have_column_storage_coverage() -> None:
    columns = created_table_columns()
    model_tables = {
        RawObservation: "data_raw_observations",
        ObservationRevision: "data_observation_revisions",
        NormalizedObservation: "data_normalized_observations",
        SnapshotConstituent: "data_snapshot_constituents",
        DataQualityFinding: "data_quality_findings",
        DataSnapshot: "data_snapshots",
        SnapshotManifest: "data_snapshot_manifests",
    }
    json_container_aliases = {
        (DataSnapshot, "manifest"): ("data_snapshot_manifests", "payload"),
        (SnapshotManifest, "payload"): ("data_snapshot_manifests", "payload"),
    }
    for model, table in model_tables.items():
        for field_name in model.model_fields:
            if field_name in columns[table]:
                continue
            alias = json_container_aliases.get((model, field_name))
            assert alias is not None, f"{model.__name__}.{field_name} has no storage mapping"
            alias_table, alias_column = alias
            assert alias_column in columns[alias_table]

    source = migration_source()
    for uuid_field in (
        "instrument_id",
        "listing_id",
        "raw_observation_id",
        "revision_record_id",
        "normalized_observation_id",
        "finding_id",
    ):
        assert re.search(
            rf'sa\.Column\("{uuid_field}", postgresql\.UUID\(as_uuid=True\)',
            source,
        )
    assert 'sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=True)' in source
    assert '"field_missingness",\n            postgresql.JSONB' in source
    assert '"dataset_schema_id"' in source
    assert '"dataset_schema_version"' in source


def test_phase4_mapping_and_request_fingerprint_are_fully_server_bound() -> None:
    source = migration_source()
    for field in (
        "mapping_version",
        "mapping_input_sha256",
        "mapper_rule_set_version",
        "mapper_rule_set_sha256",
        "official_corroboration_source_version_ids",
    ):
        assert f'"{field}"' in source
    assert "version_number AS mapping_version" in source
    assert "ORDER BY official_source_version_id::text" in source
    assert "NEW.official_corroboration_source_version_ids" in source
    assert "Phase 4 Family C requires official corroboration" in source
    assert "CREATE TRIGGER data_snapshots_10_request_gate" in source
    assert "request_fingerprint_canonical_json::jsonb" in source
    assert "convert_to('phase4-request-fingerprint-v1', 'UTF8')" in source
    assert "|| decode('00', 'hex')" in source
    assert "|| convert_to(NEW.request_fingerprint_canonical_json, 'UTF8')" in source
    for binding in (
        "request,mapping",
        "request,as_of_utc",
        "request,capability",
        "request,mock_configuration_id",
        "adapter,capabilities",
        "adapter,schema_bindings",
        "adapter,use_rights",
        "configuration,configuration_sha256",
    ):
        assert binding in source
    assert "adapter capabilities must be sorted and authoritative" in source
    assert "schema bindings must be unique and sorted" in source


def test_phase4_envelope_enforces_temporal_missingness_and_exact_raw_bytes() -> None:
    source = migration_source()
    assert "retrieved_at IS NULL OR retrieved_at >= available_at" in source
    assert "valid_to IS NULL OR valid_to > valid_from" in source
    assert "NEW.available_at > snapshot.as_of_utc" in source
    assert "(NEW.availability_source_date + 1)::timestamp" in source
    assert "AT TIME ZONE NEW.source_timezone" in source
    assert "jsonb_array_elements(NEW.field_missingness)" in source
    for optional_field in (
        "retrieved_at",
        "instrument_id",
        "listing_id",
        "valid_to",
        "calendar_id",
        "unit",
        "currency",
    ):
        assert f"NEW.{optional_field} IS NULL" in source
        assert f"value->>'field_name' = '{optional_field}'" in source
    assert "Phase 4 nullable envelope fields require exact missingness" in source
    assert "encode(sha256(NEW.raw_payload), 'hex')" in source
    assert "raw payload hash does not match exact bytes" in source


def test_phase4_revision_lineage_uses_logical_key_not_source_record_grouping() -> None:
    source = migration_source()
    assert "predecessor.logical_record_key_sha256" in source
    assert "predecessor.revision_sequence + 1 <> NEW.revision_sequence" in source
    assert "predecessor must be prior logical-key sequence" in source
    assert '"logical_record_key_sha256",\n            "revision_sequence"' in source
    predecessor_validation = source.split("IF NEW.revision_sequence > 1 THEN", maxsplit=1)[1].split(
        "RETURN NEW;", maxsplit=1
    )[0]
    assert "predecessor.source_record_id" not in predecessor_validation
    assert "predecessor.provider_id" not in predecessor_validation


def test_phase4_normalized_and_constituent_triggers_enforce_pit_contracts() -> None:
    source = migration_source()
    assert "revision.raw_observation_id IS DISTINCT FROM NEW.raw_observation_id" in source
    assert "normalized observation cannot alter raw lineage" in source
    assert "phase4_record_type_matches_capability" in source
    assert "normalized stable identity scope is invalid" in source
    assert "normalized payload contains future knowledge" in source
    for future_field in (
        "adjustment_as_of",
        "announcement_at",
        "filing_accepted_at",
        "accepted_at",
    ):
        assert future_field in source
    assert "constituent lineage mismatch" in source
    assert "constituent manifest entry mismatch" in source
    assert "uq_data_snapshot_constituent_canonical_identity" in source


def test_phase4_quality_findings_match_rich_lowercase_contract() -> None:
    source = migration_source()
    for field_name in DataQualityFinding.model_fields:
        assert f'"{field_name}"' in source
    assert "occurrence_count >= 1" in source
    assert "occurrence_rate IS NULL" in source
    assert "range_start_utc IS NULL AND range_end_utc IS NULL" in source
    assert "severity <> 'blocking' OR disposition = 'blocked'" in source
    assert "disposition <> 'blocked' OR severity IN ('error','blocking')" in source
    assert "position('sk-' IN lower(sanitized_detail::text)) = 0" in source
    assert "position('://' IN lower(sanitized_detail::text)) = 0" in source
    assert "quality finding manifest entry mismatch" in source


def test_phase4_manifest_uses_exact_contract_order_and_independent_counts() -> None:
    source = migration_source()
    assert "Phase 4 manifest independent count mismatch" in source
    assert "revision_count = raw_observation_count" not in source
    assert "normalized_observation_count = raw_observation_count" not in source
    assert "constituent_count = raw_observation_count" not in source
    for field in (
        "raw_observation_count",
        "revision_count",
        "normalized_observation_count",
        "constituent_count",
        "active_constituent_count",
        "quality_finding_count",
    ):
        assert f'"{field}"' in source
    constituent_order = (
        "record_type,\n"
        "                                logical_record_id,\n"
        "                                logical_record_key_sha256,\n"
        "                                revision_id,\n"
        "                                vintage_id,\n"
        "                                raw_payload_sha256,\n"
        "                                normalized_content_sha256,\n"
        "                                disposition"
    )
    assert constituent_order in source
    assert "raw_observation_id," not in constituent_order
    assert "normalized_observation_id," not in constituent_order
    assert "NEW.payload->'constituents' IS DISTINCT FROM full_constituents" in source
    assert "NEW.payload->'quality_findings' IS DISTINCT FROM full_findings" in source
    assert "(NEW.payload - 'constituents' - 'quality_findings')" in source
    assert "convert_to('phase4-data-snapshot-v1', 'UTF8')" in source
    assert "|| convert_to(NEW.identity_canonical_json, 'UTF8')" in source
    assert "blocked quality findings cannot be persisted" in source


def test_phase4_finalization_immutability_and_downgrade_are_closed() -> None:
    source = migration_source()
    downgrade = function_source("downgrade")
    assert "CREATE CONSTRAINT TRIGGER data_snapshots_manifest_required" in source
    assert "DEFERRABLE INITIALLY DEFERRED" in source
    assert "snapshot cannot commit without a manifest" in source
    assert "snapshot is finalized and cannot accept rows" in source
    assert "CREATE TRIGGER {table}_immutable" in source
    assert "BEFORE UPDATE OR DELETE ON {table}" in source
    assert "CREATE TRIGGER {table}_no_truncate" in source
    assert "BEFORE TRUNCATE ON {table}" in source

    first_table_drop = min(downgrade.index(f'op.drop_table("{table}")') for table in PHASE4_TABLES)
    assert downgrade.rindex("DROP TRIGGER IF EXISTS") < first_table_drop
    assert downgrade.rindex("DROP FUNCTION IF EXISTS") < first_table_drop
    ordered_tables = (
        "data_snapshot_manifests",
        "data_quality_findings",
        "data_snapshot_constituents",
        "data_normalized_observations",
        "data_observation_revisions",
        "data_raw_observations",
        "data_snapshots",
    )
    positions = [downgrade.index(f'op.drop_table("{table}")') for table in ordered_tables]
    assert positions == sorted(positions)
    assert not re.search(r'op\.drop_table\("(?:research|extraction|trading|mapping)', downgrade)
