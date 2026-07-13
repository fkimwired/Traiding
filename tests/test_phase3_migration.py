from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "services/api/migrations/versions/0003_phase3_canon_mapping.py"
PHASE3_TABLES = {
    "research_mapping_versions",
    "mapping_official_corroborations",
    "mapping_rationale_artifacts",
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


def test_phase3_revision_is_exact_reversible_and_create_all_free() -> None:
    source = migration_source()
    tree = migration_tree()
    assignments = {
        node.target.id: node.value.value
        for node in tree.body
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and isinstance(node.value, ast.Constant)
    }

    assert assignments["revision"] == "0003_phase3"
    assert assignments["down_revision"] == "0002_phase2"
    assert len(function_node("upgrade").body) > 1
    assert len(function_node("downgrade").body) > 1
    assert "create_all" not in source


def test_phase3_mapping_schema_has_exact_lineage_identity_and_closed_vocabularies() -> None:
    source = migration_source()
    required_columns = {
        "id",
        "card_id",
        "version_number",
        "card_sha256",
        "mapping_input_sha256",
        "extraction_request_id",
        "request_fingerprint",
        "source_id",
        "source_version_id",
        "source_version_number",
        "source_content_sha256",
        "extractor_kind",
        "extractor_id",
        "extractor_version",
        "extraction_model_id",
        "extraction_model_revision",
        "extraction_prompt_version",
        "extraction_prompt_sha256",
        "extraction_schema_version",
        "extraction_config_sha256",
        "mapper_rule_set_version",
        "mapper_rule_set_sha256",
        "canonical_family",
        "research_verdict",
        "matched_rule_ids",
        "reason_codes",
        "source_evidence",
        "rationale_template_version",
        "created_at_utc",
    }
    for column in required_columns:
        assert f'"{column}"' in source

    families = {
        "A_CROSS_SECTIONAL_EQUITY_RANKING",
        "B_TIME_SERIES_MOMENTUM_REGIME",
        "C_OFFICIAL_EVENT_TEXT_OVERLAY",
        "D_PAIRS_STATISTICAL_ARBITRAGE",
        "E_ORDER_BOOK_MICROSTRUCTURE",
        "F_OPTIONS_FLOW_IV_RV_ANALYTICS",
    }
    verdicts = {
        "BUILD_RESEARCH",
        "DEFER",
        "DEFER_READ_ONLY",
        "REJECT_PLATFORM",
        "NON_TESTABLE",
    }
    for value in families | verdicts:
        assert f"'{value}'" in source

    assert "canonical_family IS NOT NULL OR research_verdict = 'NON_TESTABLE'" in source
    assert "jsonb_typeof(matched_rule_ids) = 'array'" in source
    assert "jsonb_array_length(matched_rule_ids) > 0" in source
    assert "jsonb_typeof(reason_codes) = 'array'" in source
    assert "jsonb_array_length(reason_codes) > 0" in source
    assert "jsonb_typeof(source_evidence) = 'array'" in source
    assert "jsonb_array_length(source_evidence) > 0" not in source


def test_phase3_mapping_constraints_enforce_hashes_versions_and_idempotency() -> None:
    source = migration_source()

    assert "version_number >= 1" in source
    assert "source_version_number >= 1" in source
    for hash_column in (
        "card_sha256",
        "mapping_input_sha256",
        "request_fingerprint",
        "source_content_sha256",
        "extraction_config_sha256",
        "mapper_rule_set_sha256",
        "content_sha256",
    ):
        assert f"{hash_column} ~ '^[0-9a-f]{{64}}$'" in source
    assert "extraction_prompt_sha256 IS NULL" in source

    assert '"card_id",\n            "mapper_rule_set_sha256"' in source
    assert '"card_id",\n            "version_number"' in source
    assert 'sa.UniqueConstraint("mapping_id", name="uq_mapping_rationale_mapping")' in source


def test_phase3_tables_use_restrictive_foreign_keys_and_database_owned_utc() -> None:
    source = migration_source()

    assert source.count('ondelete="RESTRICT"') == 7
    for target in (
        "trading_idea_cards.id",
        "extraction_requests.id",
        "research_sources.id",
        "research_source_versions.id",
        "research_mapping_versions.id",
    ):
        assert f'["{target}"]' in source
    assert 'server_default=sa.text("CURRENT_TIMESTAMP")' in source
    assert source.count("_created_at(),") == 3


def test_phase3_insert_trigger_enforces_exact_phase2_lineage() -> None:
    source = migration_source()
    downgrade = function_source("downgrade")

    assert "CREATE FUNCTION validate_phase3_mapping_lineage()" in source
    assert "CREATE TRIGGER research_mapping_versions_lineage" in source
    assert "BEFORE INSERT ON research_mapping_versions" in source
    assert "FOR EACH ROW EXECUTE FUNCTION validate_phase3_mapping_lineage()" in source
    assert "JOIN extraction_requests AS e ON e.id = c.extraction_request_id" in source
    assert "JOIN research_source_versions AS v ON v.id = e.source_version_id" in source
    for field in (
        "extraction_request_id",
        "card_sha256",
        "request_fingerprint",
        "source_version_id",
        "source_id",
        "source_version_number",
        "source_content_sha256",
        "extractor_kind",
        "extractor_id",
        "extractor_version",
        "extraction_model_id",
        "extraction_model_revision",
        "extraction_prompt_version",
        "extraction_prompt_sha256",
        "extraction_schema_version",
        "extraction_config_sha256",
    ):
        assert f"NEW.{field} IS DISTINCT FROM lineage.{field}" in source
        assert f"Phase 3 mapping lineage mismatch: {field}" in source

    trigger_drop = downgrade.index(
        '"DROP TRIGGER IF EXISTS research_mapping_versions_lineage ON research_mapping_versions"'
    )
    table_drop = downgrade.index('op.drop_table("research_mapping_versions")')
    function_drop = downgrade.index(
        'op.execute("DROP FUNCTION IF EXISTS validate_phase3_mapping_lineage()")'
    )
    assert trigger_drop < table_drop < function_drop


def test_phase3_all_tables_reject_update_delete_and_truncate() -> None:
    source = migration_source()

    for table in PHASE3_TABLES:
        assert f'"{table}"' in source
    assert "CREATE FUNCTION reject_phase3_mapping_mutation()" in source
    assert "Phase 3 mapping records are append-only" in source
    assert "CREATE TRIGGER {table}_immutable" in source
    assert "BEFORE UPDATE OR DELETE ON {table}" in source
    assert "CREATE TRIGGER {table}_no_truncate" in source
    assert "BEFORE TRUNCATE ON {table}" in source
    assert "DROP TRIGGER IF EXISTS {table}_no_truncate ON {table}" in source
    assert "DROP TRIGGER IF EXISTS {table}_immutable ON {table}" in source


def test_phase3_corroborations_accept_only_official_source_versions() -> None:
    source = migration_source()
    downgrade = function_source("downgrade")

    assert "CREATE TRIGGER mapping_official_corroborations_official_only" in source
    assert "BEFORE INSERT ON mapping_official_corroborations" in source
    assert "FOR EACH ROW EXECUTE FUNCTION validate_phase2_official_corroboration()" in source
    trigger_drop = downgrade.index(
        '"DROP TRIGGER IF EXISTS mapping_official_corroborations_official_only "'
    )
    table_drop = downgrade.index('op.drop_table("mapping_official_corroborations")')
    assert trigger_drop < table_drop


def test_phase3_corroboration_sets_are_exact_and_deferred_until_commit() -> None:
    source = migration_source()
    downgrade = function_source("downgrade")

    assert "CREATE FUNCTION phase3_mapping_corroboration_set_matches" in source
    assert "CREATE FUNCTION validate_phase3_mapping_corroboration_set()" in source
    assert source.count("\n                EXCEPT\n") == 2
    assert source.count("DEFERRABLE INITIALLY DEFERRED") == 3
    trigger_tables = {
        "research_mapping_versions_corroboration_set": "research_mapping_versions",
        "mapping_official_corroborations_exact_set": "mapping_official_corroborations",
        "card_official_corroborations_mapping_set": "card_official_corroborations",
    }
    for trigger, table in trigger_tables.items():
        assert f"CREATE CONSTRAINT TRIGGER {trigger}" in source
        assert f"AFTER INSERT ON {table}" in source
        assert f"DROP TRIGGER IF EXISTS {trigger} " in downgrade
        assert f'"ON {table}"' in downgrade
    assert "FOR EACH ROW EXECUTE FUNCTION validate_phase3_mapping_corroboration_set()" in source
    assert "Phase 3 mapping corroboration set mismatch" in source
    assert (
        'op.execute("DROP FUNCTION IF EXISTS validate_phase3_mapping_corroboration_set()")'
        in downgrade
    )
    assert (
        'op.execute("DROP FUNCTION IF EXISTS phase3_mapping_corroboration_set_matches(uuid)")'
        in downgrade
    )


def test_phase3_finalized_corroboration_lineage_rejects_coordinated_appends() -> None:
    source = migration_source()
    downgrade = function_source("downgrade")

    assert "CREATE FUNCTION reject_phase3_finalized_corroboration_append()" in source
    assert "Phase 3 corroboration lineage is finalized" in source
    assert "SELECT 1 FROM research_memos WHERE card_id = NEW.card_id" in source
    assert "SELECT 1 FROM research_mapping_versions WHERE card_id = NEW.card_id" in source
    assert "WHERE mapping_id = NEW.mapping_id" in source
    triggers = {
        "card_official_corroborations_phase3_finalized": "card_official_corroborations",
        "mapping_official_corroborations_phase3_finalized": ("mapping_official_corroborations"),
    }
    for trigger, table in triggers.items():
        assert f"CREATE TRIGGER {trigger}" in source
        assert f"BEFORE INSERT ON {table}" in source
        assert f"DROP TRIGGER IF EXISTS {trigger} " in downgrade
        assert f'"ON {table}"' in downgrade
    assert (
        'op.execute("DROP FUNCTION IF EXISTS reject_phase3_finalized_corroboration_append()")'
        in downgrade
    )


def test_phase3_downgrade_removes_only_phase3_objects_in_dependency_order() -> None:
    downgrade = function_source("downgrade")
    node = function_node("downgrade")
    dropped_tables = {
        call.args[0].value
        for call in ast.walk(node)
        if isinstance(call, ast.Call)
        and isinstance(call.func, ast.Attribute)
        and call.func.attr == "drop_table"
        and call.args
        and isinstance(call.args[0], ast.Constant)
    }

    assert dropped_tables == PHASE3_TABLES
    rationale_drop = downgrade.index('op.drop_table("mapping_rationale_artifacts")')
    corroboration_drop = downgrade.index('op.drop_table("mapping_official_corroborations")')
    mapping_drop = downgrade.index('op.drop_table("research_mapping_versions")')
    function_drop = downgrade.index(
        'op.execute("DROP FUNCTION IF EXISTS reject_phase3_mapping_mutation()")'
    )
    assert rationale_drop < mapping_drop
    assert corroboration_drop < mapping_drop
    assert mapping_drop < function_drop

    for phase2_table in (
        "research_audit_events",
        "research_sources",
        "research_source_versions",
        "extraction_requests",
        "extraction_events",
        "trading_idea_cards",
        "card_official_corroborations",
        "research_memos",
    ):
        assert f'op.drop_table("{phase2_table}")' not in downgrade
    for prior_function in (
        "reject_audit_event_mutation",
        "reject_phase2_record_mutation",
        "validate_phase2_official_corroboration",
        "validate_phase2_source_parent",
    ):
        assert f"DROP FUNCTION IF EXISTS {prior_function}" not in downgrade
