"""Add immutable Phase 3 canonical mapping records.

Revision ID: 0003_phase3
Revises: 0002_phase2
Create Date: 2026-07-13 22:00:00+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_phase3"
down_revision: str | None = "0002_phase2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PHASE3_TABLES = (
    "research_mapping_versions",
    "mapping_official_corroborations",
    "mapping_rationale_artifacts",
)


def _created_at() -> sa.Column[object]:
    return sa.Column(
        "created_at_utc",
        sa.DateTime(timezone=True),
        server_default=sa.text("CURRENT_TIMESTAMP"),
        nullable=False,
    )


def upgrade() -> None:
    op.create_table(
        "research_mapping_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("card_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("card_sha256", sa.String(length=64), nullable=False),
        sa.Column("mapping_input_sha256", sa.String(length=64), nullable=False),
        sa.Column("extraction_request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_version_number", sa.Integer(), nullable=False),
        sa.Column("source_content_sha256", sa.String(length=64), nullable=False),
        sa.Column("extractor_kind", sa.String(length=32), nullable=False),
        sa.Column("extractor_id", sa.String(length=128), nullable=False),
        sa.Column("extractor_version", sa.String(length=64), nullable=False),
        sa.Column("extraction_model_id", sa.String(length=128), nullable=True),
        sa.Column("extraction_model_revision", sa.String(length=128), nullable=True),
        sa.Column("extraction_prompt_version", sa.String(length=128), nullable=True),
        sa.Column("extraction_prompt_sha256", sa.String(length=64), nullable=True),
        sa.Column("extraction_schema_version", sa.String(length=128), nullable=False),
        sa.Column("extraction_config_sha256", sa.String(length=64), nullable=False),
        sa.Column("mapper_rule_set_version", sa.String(length=128), nullable=False),
        sa.Column("mapper_rule_set_sha256", sa.String(length=64), nullable=False),
        sa.Column("canonical_family", sa.String(length=64), nullable=True),
        sa.Column("research_verdict", sa.String(length=32), nullable=False),
        sa.Column("matched_rule_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("reason_codes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source_evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("rationale_template_version", sa.String(length=128), nullable=False),
        _created_at(),
        sa.CheckConstraint("version_number >= 1", name="ck_mapping_version_positive"),
        sa.CheckConstraint(
            "source_version_number >= 1",
            name="ck_mapping_source_version_positive",
        ),
        sa.CheckConstraint(
            "extractor_kind IN ('deterministic_mock','llm')",
            name="ck_mapping_extractor_kind",
        ),
        sa.CheckConstraint(
            "((extractor_kind = 'llm' AND extraction_model_id IS NOT NULL "
            "AND extraction_model_revision IS NOT NULL "
            "AND extraction_prompt_version IS NOT NULL "
            "AND extraction_prompt_sha256 IS NOT NULL) OR "
            "(extractor_kind = 'deterministic_mock' AND extraction_model_id IS NULL "
            "AND extraction_model_revision IS NULL "
            "AND extraction_prompt_version IS NULL "
            "AND extraction_prompt_sha256 IS NULL))",
            name="ck_mapping_extractor_provenance",
        ),
        sa.CheckConstraint(
            "card_sha256 ~ '^[0-9a-f]{64}$' "
            "AND mapping_input_sha256 ~ '^[0-9a-f]{64}$' "
            "AND request_fingerprint ~ '^[0-9a-f]{64}$' "
            "AND source_content_sha256 ~ '^[0-9a-f]{64}$' "
            "AND extraction_config_sha256 ~ '^[0-9a-f]{64}$' "
            "AND mapper_rule_set_sha256 ~ '^[0-9a-f]{64}$' "
            "AND (extraction_prompt_sha256 IS NULL "
            "OR extraction_prompt_sha256 ~ '^[0-9a-f]{64}$')",
            name="ck_mapping_version_hashes",
        ),
        sa.CheckConstraint(
            "canonical_family IS NULL OR canonical_family IN ("
            "'A_CROSS_SECTIONAL_EQUITY_RANKING',"
            "'B_TIME_SERIES_MOMENTUM_REGIME',"
            "'C_OFFICIAL_EVENT_TEXT_OVERLAY',"
            "'D_PAIRS_STATISTICAL_ARBITRAGE',"
            "'E_ORDER_BOOK_MICROSTRUCTURE',"
            "'F_OPTIONS_FLOW_IV_RV_ANALYTICS')",
            name="ck_mapping_canonical_family",
        ),
        sa.CheckConstraint(
            "research_verdict IN ("
            "'BUILD_RESEARCH','DEFER','DEFER_READ_ONLY','REJECT_PLATFORM','NON_TESTABLE')",
            name="ck_mapping_research_verdict",
        ),
        sa.CheckConstraint(
            "canonical_family IS NOT NULL OR research_verdict = 'NON_TESTABLE'",
            name="ck_mapping_null_family_non_testable",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(matched_rule_ids) = 'array' "
            "AND jsonb_array_length(matched_rule_ids) > 0 "
            "AND jsonb_typeof(reason_codes) = 'array' "
            "AND jsonb_array_length(reason_codes) > 0 "
            "AND jsonb_typeof(source_evidence) = 'array'",
            name="ck_mapping_ordered_arrays",
        ),
        sa.ForeignKeyConstraint(
            ["card_id"],
            ["trading_idea_cards.id"],
            name="fk_mapping_version_card",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["extraction_request_id"],
            ["extraction_requests.id"],
            name="fk_mapping_version_extraction_request",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["research_sources.id"],
            name="fk_mapping_version_source",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_version_id"],
            ["research_source_versions.id"],
            name="fk_mapping_version_source_version",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_research_mapping_versions"),
        sa.UniqueConstraint(
            "card_id",
            "mapper_rule_set_sha256",
            name="uq_mapping_version_card_rule_set",
        ),
        sa.UniqueConstraint(
            "card_id",
            "version_number",
            name="uq_mapping_version_card_number",
        ),
    )
    op.create_index(
        "ix_mapping_versions_card_created",
        "research_mapping_versions",
        ["card_id", "created_at_utc", "id"],
    )
    op.create_index(
        "ix_mapping_versions_created",
        "research_mapping_versions",
        ["created_at_utc", "id"],
    )

    op.execute(
        """
        CREATE FUNCTION validate_phase3_mapping_lineage()
        RETURNS trigger AS $$
        DECLARE
            lineage record;
        BEGIN
            SELECT
                c.extraction_request_id,
                c.card_sha256,
                e.request_fingerprint,
                e.source_version_id,
                e.extractor_kind,
                e.extractor_id,
                e.extractor_version,
                e.extraction_model_id,
                e.extraction_model_revision,
                e.extraction_prompt_version,
                e.extraction_prompt_sha256,
                e.extraction_schema_version,
                e.extraction_config_sha256,
                v.source_id,
                v.version_number AS source_version_number,
                v.content_sha256 AS source_content_sha256
            INTO lineage
            FROM trading_idea_cards AS c
            JOIN extraction_requests AS e ON e.id = c.extraction_request_id
            JOIN research_source_versions AS v ON v.id = e.source_version_id
            WHERE c.id = NEW.card_id;

            IF NOT FOUND THEN
                RAISE EXCEPTION 'Phase 3 mapping lineage card was not found';
            END IF;
            IF NEW.extraction_request_id IS DISTINCT FROM lineage.extraction_request_id THEN
                RAISE EXCEPTION 'Phase 3 mapping lineage mismatch: extraction_request_id';
            END IF;
            IF NEW.card_sha256 IS DISTINCT FROM lineage.card_sha256 THEN
                RAISE EXCEPTION 'Phase 3 mapping lineage mismatch: card_sha256';
            END IF;
            IF NEW.request_fingerprint IS DISTINCT FROM lineage.request_fingerprint THEN
                RAISE EXCEPTION 'Phase 3 mapping lineage mismatch: request_fingerprint';
            END IF;
            IF NEW.source_version_id IS DISTINCT FROM lineage.source_version_id THEN
                RAISE EXCEPTION 'Phase 3 mapping lineage mismatch: source_version_id';
            END IF;
            IF NEW.source_id IS DISTINCT FROM lineage.source_id THEN
                RAISE EXCEPTION 'Phase 3 mapping lineage mismatch: source_id';
            END IF;
            IF NEW.source_version_number IS DISTINCT FROM lineage.source_version_number THEN
                RAISE EXCEPTION 'Phase 3 mapping lineage mismatch: source_version_number';
            END IF;
            IF NEW.source_content_sha256 IS DISTINCT FROM lineage.source_content_sha256 THEN
                RAISE EXCEPTION 'Phase 3 mapping lineage mismatch: source_content_sha256';
            END IF;
            IF NEW.extractor_kind IS DISTINCT FROM lineage.extractor_kind THEN
                RAISE EXCEPTION 'Phase 3 mapping lineage mismatch: extractor_kind';
            END IF;
            IF NEW.extractor_id IS DISTINCT FROM lineage.extractor_id THEN
                RAISE EXCEPTION 'Phase 3 mapping lineage mismatch: extractor_id';
            END IF;
            IF NEW.extractor_version IS DISTINCT FROM lineage.extractor_version THEN
                RAISE EXCEPTION 'Phase 3 mapping lineage mismatch: extractor_version';
            END IF;
            IF NEW.extraction_model_id IS DISTINCT FROM lineage.extraction_model_id THEN
                RAISE EXCEPTION 'Phase 3 mapping lineage mismatch: extraction_model_id';
            END IF;
            IF NEW.extraction_model_revision IS DISTINCT FROM lineage.extraction_model_revision THEN
                RAISE EXCEPTION 'Phase 3 mapping lineage mismatch: extraction_model_revision';
            END IF;
            IF NEW.extraction_prompt_version IS DISTINCT FROM lineage.extraction_prompt_version THEN
                RAISE EXCEPTION 'Phase 3 mapping lineage mismatch: extraction_prompt_version';
            END IF;
            IF NEW.extraction_prompt_sha256 IS DISTINCT FROM lineage.extraction_prompt_sha256 THEN
                RAISE EXCEPTION 'Phase 3 mapping lineage mismatch: extraction_prompt_sha256';
            END IF;
            IF NEW.extraction_schema_version IS DISTINCT FROM lineage.extraction_schema_version THEN
                RAISE EXCEPTION 'Phase 3 mapping lineage mismatch: extraction_schema_version';
            END IF;
            IF NEW.extraction_config_sha256 IS DISTINCT FROM lineage.extraction_config_sha256 THEN
                RAISE EXCEPTION 'Phase 3 mapping lineage mismatch: extraction_config_sha256';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER research_mapping_versions_lineage
        BEFORE INSERT ON research_mapping_versions
        FOR EACH ROW EXECUTE FUNCTION validate_phase3_mapping_lineage()
        """
    )

    op.create_table(
        "mapping_official_corroborations",
        sa.Column("mapping_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("official_source_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        _created_at(),
        sa.ForeignKeyConstraint(
            ["mapping_id"],
            ["research_mapping_versions.id"],
            name="fk_mapping_corroboration_mapping",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["official_source_version_id"],
            ["research_source_versions.id"],
            name="fk_mapping_corroboration_official_version",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "mapping_id",
            "official_source_version_id",
            name="pk_mapping_official_corroborations",
        ),
    )
    op.create_index(
        "ix_mapping_corroborations_official_version",
        "mapping_official_corroborations",
        ["official_source_version_id", "mapping_id"],
    )

    op.create_table(
        "mapping_rationale_artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mapping_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("template_version", sa.String(length=128), nullable=False),
        sa.Column("markdown_content", sa.Text(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        _created_at(),
        sa.CheckConstraint(
            "content_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_mapping_rationale_sha256",
        ),
        sa.ForeignKeyConstraint(
            ["mapping_id"],
            ["research_mapping_versions.id"],
            name="fk_mapping_rationale_mapping",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_mapping_rationale_artifacts"),
        sa.UniqueConstraint("mapping_id", name="uq_mapping_rationale_mapping"),
    )

    op.execute(
        """
        CREATE FUNCTION reject_phase3_finalized_corroboration_append()
        RETURNS trigger AS $$
        BEGIN
            IF TG_TABLE_NAME = 'card_official_corroborations' THEN
                IF EXISTS (
                    SELECT 1 FROM research_memos WHERE card_id = NEW.card_id
                ) OR EXISTS (
                    SELECT 1 FROM research_mapping_versions WHERE card_id = NEW.card_id
                ) THEN
                    RAISE EXCEPTION 'Phase 3 corroboration lineage is finalized';
                END IF;
                RETURN NEW;
            END IF;

            IF EXISTS (
                SELECT 1 FROM mapping_rationale_artifacts
                WHERE mapping_id = NEW.mapping_id
            ) THEN
                RAISE EXCEPTION 'Phase 3 corroboration lineage is finalized';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER card_official_corroborations_phase3_finalized
        BEFORE INSERT ON card_official_corroborations
        FOR EACH ROW EXECUTE FUNCTION reject_phase3_finalized_corroboration_append()
        """
    )
    op.execute(
        """
        CREATE TRIGGER mapping_official_corroborations_phase3_finalized
        BEFORE INSERT ON mapping_official_corroborations
        FOR EACH ROW EXECUTE FUNCTION reject_phase3_finalized_corroboration_append()
        """
    )

    op.execute(
        """
        CREATE TRIGGER mapping_official_corroborations_official_only
        BEFORE INSERT ON mapping_official_corroborations
        FOR EACH ROW EXECUTE FUNCTION validate_phase2_official_corroboration()
        """
    )
    op.execute(
        """
        CREATE FUNCTION phase3_mapping_corroboration_set_matches(checked_mapping_id uuid)
        RETURNS boolean AS $$
            SELECT NOT EXISTS (
                SELECT c.official_source_version_id
                FROM research_mapping_versions AS m
                JOIN card_official_corroborations AS c ON c.card_id = m.card_id
                WHERE m.id = checked_mapping_id
                EXCEPT
                SELECT mc.official_source_version_id
                FROM mapping_official_corroborations AS mc
                WHERE mc.mapping_id = checked_mapping_id
            ) AND NOT EXISTS (
                SELECT mc.official_source_version_id
                FROM mapping_official_corroborations AS mc
                WHERE mc.mapping_id = checked_mapping_id
                EXCEPT
                SELECT c.official_source_version_id
                FROM research_mapping_versions AS m
                JOIN card_official_corroborations AS c ON c.card_id = m.card_id
                WHERE m.id = checked_mapping_id
            )
        $$ LANGUAGE sql STABLE
        """
    )
    op.execute(
        """
        CREATE FUNCTION validate_phase3_mapping_corroboration_set()
        RETURNS trigger AS $$
        DECLARE
            checked_mapping_id uuid;
        BEGIN
            IF TG_TABLE_NAME = 'card_official_corroborations' THEN
                FOR checked_mapping_id IN
                    SELECT id FROM research_mapping_versions WHERE card_id = NEW.card_id
                LOOP
                    IF NOT phase3_mapping_corroboration_set_matches(checked_mapping_id) THEN
                        RAISE EXCEPTION
                            'Phase 3 mapping corroboration set mismatch for mapping %',
                            checked_mapping_id;
                    END IF;
                END LOOP;
                RETURN NEW;
            END IF;

            IF TG_TABLE_NAME = 'research_mapping_versions' THEN
                checked_mapping_id := NEW.id;
            ELSE
                checked_mapping_id := NEW.mapping_id;
            END IF;
            IF NOT phase3_mapping_corroboration_set_matches(checked_mapping_id) THEN
                RAISE EXCEPTION
                    'Phase 3 mapping corroboration set mismatch for mapping %',
                    checked_mapping_id;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER research_mapping_versions_corroboration_set
        AFTER INSERT ON research_mapping_versions
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION validate_phase3_mapping_corroboration_set()
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER mapping_official_corroborations_exact_set
        AFTER INSERT ON mapping_official_corroborations
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION validate_phase3_mapping_corroboration_set()
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER card_official_corroborations_mapping_set
        AFTER INSERT ON card_official_corroborations
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION validate_phase3_mapping_corroboration_set()
        """
    )

    op.execute(
        """
        CREATE FUNCTION reject_phase3_mapping_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'Phase 3 mapping records are append-only';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    for table in PHASE3_TABLES:
        op.execute(
            f"""
            CREATE TRIGGER {table}_immutable
            BEFORE UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION reject_phase3_mapping_mutation()
            """
        )
        op.execute(
            f"""
            CREATE TRIGGER {table}_no_truncate
            BEFORE TRUNCATE ON {table}
            FOR EACH STATEMENT EXECUTE FUNCTION reject_phase3_mapping_mutation()
            """
        )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS card_official_corroborations_phase3_finalized "
        "ON card_official_corroborations"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS mapping_official_corroborations_phase3_finalized "
        "ON mapping_official_corroborations"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS card_official_corroborations_mapping_set "
        "ON card_official_corroborations"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS mapping_official_corroborations_exact_set "
        "ON mapping_official_corroborations"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS research_mapping_versions_corroboration_set "
        "ON research_mapping_versions"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS mapping_official_corroborations_official_only "
        "ON mapping_official_corroborations"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS research_mapping_versions_lineage ON research_mapping_versions"
    )
    for table in reversed(PHASE3_TABLES):
        op.execute(f"DROP TRIGGER IF EXISTS {table}_no_truncate ON {table}")
        op.execute(f"DROP TRIGGER IF EXISTS {table}_immutable ON {table}")
    op.execute("DROP FUNCTION IF EXISTS validate_phase3_mapping_corroboration_set()")
    op.execute("DROP FUNCTION IF EXISTS phase3_mapping_corroboration_set_matches(uuid)")
    op.execute("DROP FUNCTION IF EXISTS reject_phase3_finalized_corroboration_append()")

    op.drop_table("mapping_rationale_artifacts")
    op.drop_index(
        "ix_mapping_corroborations_official_version",
        table_name="mapping_official_corroborations",
    )
    op.drop_table("mapping_official_corroborations")
    op.drop_index("ix_mapping_versions_created", table_name="research_mapping_versions")
    op.drop_index("ix_mapping_versions_card_created", table_name="research_mapping_versions")
    op.drop_table("research_mapping_versions")
    op.execute("DROP FUNCTION IF EXISTS reject_phase3_mapping_mutation()")
    op.execute("DROP FUNCTION IF EXISTS validate_phase3_mapping_lineage()")
