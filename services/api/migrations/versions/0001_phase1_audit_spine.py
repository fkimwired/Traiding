"""Create the Phase 1 immutable audit spine.

Revision ID: 0001_phase1
Revises:
Create Date: 2026-07-13 00:00:00+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_phase1"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "research_audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("config_hash", sa.String(length=64), nullable=False),
        sa.Column("data_snapshot_id", sa.String(length=128), nullable=False),
        sa.Column("git_sha", sa.String(length=64), nullable=False),
        sa.Column("random_seed", sa.BigInteger(), nullable=False),
        sa.Column("trial_count", sa.Integer(), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.CheckConstraint("trial_count >= 1", name="ck_audit_trial_count_positive"),
        sa.PrimaryKeyConstraint("id", name="pk_research_audit_events"),
    )
    op.create_index(
        "ix_research_audit_events_occurred_at",
        "research_audit_events",
        ["occurred_at"],
    )
    op.execute(
        """
        CREATE FUNCTION reject_audit_event_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'research_audit_events is append-only';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER research_audit_events_immutable
        BEFORE UPDATE OR DELETE ON research_audit_events
        FOR EACH ROW EXECUTE FUNCTION reject_audit_event_mutation()
        """
    )
    op.execute(
        """
        CREATE TRIGGER research_audit_events_no_truncate
        BEFORE TRUNCATE ON research_audit_events
        FOR EACH STATEMENT EXECUTE FUNCTION reject_audit_event_mutation()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS research_audit_events_no_truncate ON research_audit_events")
    op.execute("DROP TRIGGER IF EXISTS research_audit_events_immutable ON research_audit_events")
    op.execute("DROP FUNCTION IF EXISTS reject_audit_event_mutation()")
    op.drop_index("ix_research_audit_events_occurred_at", table_name="research_audit_events")
    op.drop_table("research_audit_events")
