"""Add immutable Phase 2 source extraction records.

Revision ID: 0002_phase2
Revises: 0001_phase1
Create Date: 2026-07-13 20:00:00+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_phase2"
down_revision: str | None = "0001_phase1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PHASE2_TABLES = (
    "research_sources",
    "research_source_versions",
    "research_source_version_corroborations",
    "extraction_requests",
    "extraction_events",
    "trading_idea_cards",
    "card_official_corroborations",
    "research_memos",
)


def _created_at(name: str = "created_at_utc") -> sa.Column[object]:
    return sa.Column(
        name,
        sa.DateTime(timezone=True),
        server_default=sa.text("CURRENT_TIMESTAMP"),
        nullable=False,
    )


def upgrade() -> None:
    op.create_table(
        "research_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        _created_at(),
        sa.PrimaryKeyConstraint("id", name="pk_research_sources"),
    )
    op.create_table(
        "research_source_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("parent_source_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_authority", sa.String(length=16), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("content_state", sa.String(length=32), nullable=False),
        sa.Column("raw_content", sa.LargeBinary(), nullable=True),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "supplied_at_utc",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("retrieved_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("authority_verification_method", sa.String(length=64), nullable=True),
        sa.Column("ingest_idempotency_key", sa.String(length=128), nullable=False),
        _created_at(),
        sa.CheckConstraint("version_number >= 1", name="ck_source_version_positive"),
        sa.CheckConstraint(
            "source_type IN ('pasted_caption','transcript','manual_notes',"
            "'screenshot_transcript','url_provenance','synthetic_fixture')",
            name="ck_source_version_type",
        ),
        sa.CheckConstraint(
            "source_authority IN ('official','social','news','other','unknown')",
            name="ck_source_version_authority",
        ),
        sa.CheckConstraint(
            "content_state IN ('supplied_text','retrieved_text','url_only_unretrieved')",
            name="ck_source_version_content_state",
        ),
        sa.CheckConstraint(
            "((content_state = 'url_only_unretrieved' AND raw_content IS NULL "
            "AND source_url IS NOT NULL) OR "
            "(content_state IN ('supplied_text','retrieved_text') AND raw_content IS NOT NULL))",
            name="ck_source_version_content_presence",
        ),
        sa.CheckConstraint(
            "content_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_source_version_sha256",
        ),
        sa.CheckConstraint(
            "authority_verification_method IS NULL OR source_authority = 'official'",
            name="ck_source_version_verification_authority",
        ),
        sa.CheckConstraint(
            "authority_verification_method IS NULL OR authority_verification_method IN "
            "('manual_user_attestation','synthetic_fixture')",
            name="ck_source_version_verification_method",
        ),
        sa.CheckConstraint(
            "authority_verification_method <> 'synthetic_fixture' "
            "OR source_type = 'synthetic_fixture'",
            name="ck_source_version_synthetic_verification",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["research_sources.id"],
            name="fk_source_versions_source",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["parent_source_version_id"],
            ["research_source_versions.id"],
            name="fk_source_versions_parent",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_research_source_versions"),
        sa.UniqueConstraint("source_id", "version_number", name="uq_source_versions_source_number"),
        sa.UniqueConstraint("ingest_idempotency_key", name="uq_source_versions_ingest_idempotency"),
    )
    op.create_index(
        "ix_source_versions_source_created",
        "research_source_versions",
        ["source_id", "created_at_utc"],
    )
    op.create_table(
        "research_source_version_corroborations",
        sa.Column("source_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("official_source_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        _created_at(),
        sa.CheckConstraint(
            "source_version_id <> official_source_version_id",
            name="ck_source_corroboration_not_self",
        ),
        sa.ForeignKeyConstraint(
            ["source_version_id"],
            ["research_source_versions.id"],
            name="fk_source_corroboration_source_version",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["official_source_version_id"],
            ["research_source_versions.id"],
            name="fk_source_corroboration_official_version",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "source_version_id",
            "official_source_version_id",
            name="pk_source_version_corroborations",
        ),
    )
    op.create_table(
        "extraction_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("extractor_kind", sa.String(length=32), nullable=False),
        sa.Column("extractor_id", sa.String(length=128), nullable=False),
        sa.Column("extractor_version", sa.String(length=64), nullable=False),
        sa.Column("extraction_model_id", sa.String(length=128), nullable=True),
        sa.Column("extraction_model_revision", sa.String(length=128), nullable=True),
        sa.Column("extraction_prompt_version", sa.String(length=128), nullable=True),
        sa.Column("extraction_prompt_sha256", sa.String(length=64), nullable=True),
        sa.Column("extraction_schema_version", sa.String(length=128), nullable=False),
        sa.Column("extraction_config_sha256", sa.String(length=64), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("rq_job_id", sa.String(length=128), nullable=False),
        _created_at("requested_at_utc"),
        sa.CheckConstraint(
            "extractor_kind IN ('deterministic_mock','llm')",
            name="ck_extraction_request_kind",
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
            name="ck_extraction_request_conditional_llm_provenance",
        ),
        sa.CheckConstraint(
            "extraction_config_sha256 ~ '^[0-9a-f]{64}$' "
            "AND request_fingerprint ~ '^[0-9a-f]{64}$' "
            "AND (extraction_prompt_sha256 IS NULL "
            "OR extraction_prompt_sha256 ~ '^[0-9a-f]{64}$')",
            name="ck_extraction_request_hashes",
        ),
        sa.ForeignKeyConstraint(
            ["source_version_id"],
            ["research_source_versions.id"],
            name="fk_extraction_requests_source_version",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_extraction_requests"),
        sa.UniqueConstraint("request_fingerprint", name="uq_extraction_request_fingerprint"),
        sa.UniqueConstraint("rq_job_id", name="uq_extraction_request_rq_job"),
    )
    op.create_table(
        "extraction_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_sequence", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("extraction_request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column(
            "payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"
        ),
        _created_at("occurred_at_utc"),
        sa.CheckConstraint("attempt_number >= 1", name="ck_extraction_event_attempt"),
        sa.CheckConstraint(
            "event_type IN ('requested','queued','enqueue_failed','started','succeeded','failed')",
            name="ck_extraction_event_type",
        ),
        sa.ForeignKeyConstraint(
            ["extraction_request_id"],
            ["extraction_requests.id"],
            name="fk_extraction_events_request",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_extraction_events"),
        sa.UniqueConstraint("event_sequence", name="uq_extraction_event_sequence"),
    )
    op.create_index(
        "ix_extraction_events_request_time",
        "extraction_events",
        ["extraction_request_id", "event_sequence"],
    )
    op.create_table(
        "trading_idea_cards",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("extraction_request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("testability_status", sa.String(length=32), nullable=False),
        sa.Column("testability_score", sa.Float(), nullable=False),
        sa.Column("infra_risk", sa.String(length=16), nullable=False),
        sa.Column("corroboration_status", sa.String(length=32), nullable=False),
        sa.Column("contribution_status", sa.String(length=64), nullable=False),
        sa.Column("research_priority_score", sa.Float(), nullable=True),
        sa.Column("card_sha256", sa.String(length=64), nullable=False),
        sa.Column("draft_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        _created_at(),
        sa.CheckConstraint(
            "testability_status IN ('testable','non_testable')",
            name="ck_card_testability_status",
        ),
        sa.CheckConstraint(
            "testability_score >= 0.0 AND testability_score <= 1.0",
            name="ck_card_testability_score",
        ),
        sa.CheckConstraint(
            "infra_risk IN ('unknown','low','medium','high')",
            name="ck_card_infra_risk",
        ),
        sa.CheckConstraint(
            "corroboration_status IN ('not_required','missing','linked_unverified','verified')",
            name="ck_card_corroboration_status",
        ),
        sa.CheckConstraint(
            "contribution_status IN ('not_blocked_by_corroboration',"
            "'blocked_official_corroboration_required')",
            name="ck_card_contribution_status",
        ),
        sa.CheckConstraint(
            "research_priority_score IS NULL",
            name="ck_card_no_phase2_priority_score",
        ),
        sa.CheckConstraint("card_sha256 ~ '^[0-9a-f]{64}$'", name="ck_card_sha256"),
        sa.ForeignKeyConstraint(
            ["extraction_request_id"],
            ["extraction_requests.id"],
            name="fk_cards_extraction_request",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_trading_idea_cards"),
        sa.UniqueConstraint("extraction_request_id", name="uq_card_extraction_request"),
    )
    op.create_table(
        "card_official_corroborations",
        sa.Column("card_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("official_source_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        _created_at(),
        sa.ForeignKeyConstraint(
            ["card_id"],
            ["trading_idea_cards.id"],
            name="fk_card_corroboration_card",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["official_source_version_id"],
            ["research_source_versions.id"],
            name="fk_card_corroboration_official_version",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "card_id", "official_source_version_id", name="pk_card_corroborations"
        ),
    )
    op.create_table(
        "research_memos",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("card_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("template_version", sa.String(length=64), nullable=False),
        sa.Column("markdown_content", sa.Text(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        _created_at(),
        sa.CheckConstraint("content_sha256 ~ '^[0-9a-f]{64}$'", name="ck_memo_sha256"),
        sa.ForeignKeyConstraint(
            ["card_id"],
            ["trading_idea_cards.id"],
            name="fk_memos_card",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_research_memos"),
        sa.UniqueConstraint("card_id", name="uq_memo_card"),
    )

    op.execute(
        """
        CREATE FUNCTION validate_phase2_source_parent()
        RETURNS trigger AS $$
        DECLARE
            parent_source uuid;
            parent_version integer;
        BEGIN
            IF NEW.version_number = 1 THEN
                IF NEW.parent_source_version_id IS NOT NULL THEN
                    RAISE EXCEPTION 'source version 1 cannot have a parent';
                END IF;
                RETURN NEW;
            END IF;
            IF NEW.parent_source_version_id IS NULL THEN
                RAISE EXCEPTION 'source version % requires a parent', NEW.version_number;
            END IF;
            SELECT source_id, version_number INTO parent_source, parent_version
            FROM research_source_versions WHERE id = NEW.parent_source_version_id;
            IF parent_source IS NULL OR parent_source <> NEW.source_id
               OR parent_version <> NEW.version_number - 1 THEN
                RAISE EXCEPTION 'source version parent must be the immediately prior version';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER research_source_versions_parent_chain
        BEFORE INSERT ON research_source_versions
        FOR EACH ROW EXECUTE FUNCTION validate_phase2_source_parent()
        """
    )
    op.execute(
        """
        CREATE FUNCTION validate_phase2_official_corroboration()
        RETURNS trigger AS $$
        DECLARE
            authority text;
        BEGIN
            SELECT source_authority INTO authority
            FROM research_source_versions WHERE id = NEW.official_source_version_id;
            IF authority IS DISTINCT FROM 'official' THEN
                RAISE EXCEPTION 'corroboration must reference an official source version';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    for table in (
        "research_source_version_corroborations",
        "card_official_corroborations",
    ):
        op.execute(
            f"""
            CREATE TRIGGER {table}_official_only
            BEFORE INSERT ON {table}
            FOR EACH ROW EXECUTE FUNCTION validate_phase2_official_corroboration()
            """
        )

    op.execute(
        """
        CREATE FUNCTION reject_phase2_record_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'Phase 2 research records are append-only';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    for table in PHASE2_TABLES:
        op.execute(
            f"""
            CREATE TRIGGER {table}_immutable
            BEFORE UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION reject_phase2_record_mutation()
            """
        )
        op.execute(
            f"""
            CREATE TRIGGER {table}_no_truncate
            BEFORE TRUNCATE ON {table}
            FOR EACH STATEMENT EXECUTE FUNCTION reject_phase2_record_mutation()
            """
        )


def downgrade() -> None:
    for table in reversed(PHASE2_TABLES):
        op.execute(f"DROP TRIGGER IF EXISTS {table}_no_truncate ON {table}")
        op.execute(f"DROP TRIGGER IF EXISTS {table}_immutable ON {table}")
    for table in (
        "card_official_corroborations",
        "research_source_version_corroborations",
    ):
        op.execute(f"DROP TRIGGER IF EXISTS {table}_official_only ON {table}")
    op.execute(
        "DROP TRIGGER IF EXISTS research_source_versions_parent_chain ON research_source_versions"
    )
    op.drop_table("research_memos")
    op.drop_table("card_official_corroborations")
    op.drop_table("trading_idea_cards")
    op.drop_index("ix_extraction_events_request_time", table_name="extraction_events")
    op.drop_table("extraction_events")
    op.drop_table("extraction_requests")
    op.drop_table("research_source_version_corroborations")
    op.drop_index("ix_source_versions_source_created", table_name="research_source_versions")
    op.drop_table("research_source_versions")
    op.drop_table("research_sources")
    op.execute("DROP FUNCTION IF EXISTS reject_phase2_record_mutation()")
    op.execute("DROP FUNCTION IF EXISTS validate_phase2_official_corroboration()")
    op.execute("DROP FUNCTION IF EXISTS validate_phase2_source_parent()")
