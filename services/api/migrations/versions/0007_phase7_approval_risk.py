"""Add immutable Phase 7 approval and pre-order risk artifacts.

Revision ID: 0007_phase7
Revises: 0006_phase6

The revision deliberately creates no execution, broker, order, fill, or
position state.  The rows below are synthetic governance evidence only.
"""

from __future__ import annotations

from collections.abc import Iterable

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_phase7"
down_revision: str | None = "0006_phase6"
branch_labels: str | None = None
depends_on: str | None = None


PHASE7_TABLES = (
    "approval_policies",
    "approval_scopes",
    "approval_authorizations",
    "approval_revocations",
    "approval_risk_inputs",
    "approval_assessments",
    "approval_checks",
)

PHASE7_CHECK_CODES = (
    "RESEARCH_PASS",
    "PHASE6_LINEAGE_COMPLETE",
    "POLICY_CURRENT",
    "POLICY_MATCH",
    "SCOPE_CURRENT",
    "SCOPE_MATCH",
    "AUTHORIZATION_CURRENT",
    "AUTHORIZATION_MATCH",
    "REVOCATION_CLEAR",
    "RISK_INPUT_FRESH",
    "GLOBAL_CONTROL_CLEAR",
    "STRATEGY_CONTROL_CLEAR",
    "DATA_QUALITY_CONTROL_CLEAR",
    "MARKET_CALENDAR_OPEN",
    "DUPLICATE_CONTEXT_CLEAR",
    "NOTIONAL_LIMIT",
    "GROSS_EXPOSURE_LIMIT",
    "NET_EXPOSURE_LIMIT",
    "SECTOR_EXPOSURE_LIMIT",
    "CONCENTRATION_LIMIT",
    "LIQUIDITY_MINIMUM",
    "TURNOVER_LIMIT",
    "VOLATILITY_LIMIT",
    "DAILY_LOSS_LIMIT",
    "DRAWDOWN_LIMIT",
)

PHASE7_APPEND_ONLY_ERROR = "Phase 7 approval and risk artifacts are append-only"


def _created_at() -> sa.Column[object]:
    return sa.Column(
        "created_at_utc",
        sa.DateTime(timezone=True),
        server_default=sa.text("CURRENT_TIMESTAMP"),
        nullable=False,
    )


def _payload(column_name: str = "payload") -> sa.Column[object]:
    return sa.Column(
        column_name,
        postgresql.JSONB(astext_type=sa.Text()),
        nullable=False,
    )


def _hash_check(columns: Iterable[str], *, name: str) -> sa.CheckConstraint:
    return sa.CheckConstraint(
        " AND ".join(f"{column} ~ '^[0-9a-f]{{64}}$'" for column in columns),
        name=name,
    )


def _decimal(column_name: str, *, nullable: bool = False) -> sa.Column[object]:
    return sa.Column(
        column_name,
        sa.Numeric(precision=38, scale=18),
        nullable=nullable,
    )


def _check_code_sql() -> str:
    return ",".join(f"'{code}'" for code in PHASE7_CHECK_CODES)


def _check_registry_json_sql() -> str:
    return "'" + "[" + ",".join(f'"{code}"' for code in PHASE7_CHECK_CODES) + "]'::jsonb"


def upgrade() -> None:
    # This exact pair is the Phase 7 lineage authority.  Independent unique
    # constraints on the two columns would permit a cross-row pairing.
    op.create_unique_constraint(
        "uq_research_pipeline_run_id_artifact_sha256",
        "research_pipeline_runs",
        ["id", "artifact_sha256"],
    )

    op.create_table(
        "approval_policies",
        sa.Column("approval_policy_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("policy_id", sa.String(length=256), nullable=False),
        sa.Column("policy_version", sa.Integer(), nullable=False),
        sa.Column("policy_sha256", sa.String(length=64), nullable=False),
        sa.Column("valid_from_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("risk_input_max_age_seconds", sa.Integer(), nullable=False),
        sa.Column("authorization_max_age_seconds", sa.Integer(), nullable=False),
        sa.Column(
            "required_check_codes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        _decimal("max_notional"),
        _decimal("max_gross_exposure"),
        _decimal("max_abs_net_exposure"),
        _decimal("max_sector_exposure"),
        _decimal("max_concentration"),
        _decimal("min_liquidity"),
        _decimal("max_turnover"),
        _decimal("max_volatility"),
        _decimal("max_daily_loss"),
        _decimal("max_drawdown"),
        sa.Column("synthetic", sa.Boolean(), nullable=False),
        _payload(),
        _created_at(),
        _hash_check(("policy_sha256",), name="ck_approval_policy_hash"),
        sa.CheckConstraint(
            "schema_version = 'phase7-approval-policy-v1' "
            "AND btrim(policy_id) <> '' AND policy_version >= 1 "
            "AND valid_from_utc < expires_at_utc "
            "AND risk_input_max_age_seconds >= 1 "
            "AND authorization_max_age_seconds >= 1 "
            f"AND required_check_codes = {_check_registry_json_sql()} "
            "AND max_notional >= 0 AND max_gross_exposure >= 0 "
            "AND max_abs_net_exposure >= 0 AND max_sector_exposure >= 0 "
            "AND max_concentration >= 0 AND min_liquidity >= 0 "
            "AND max_turnover >= 0 AND max_volatility >= 0 "
            "AND max_daily_loss >= 0 AND max_drawdown >= 0 "
            "AND synthetic AND jsonb_typeof(payload) = 'object'",
            name="ck_approval_policy_identity",
        ),
        sa.PrimaryKeyConstraint("approval_policy_version_id", name="pk_approval_policies"),
        sa.UniqueConstraint("policy_id", "policy_version", name="uq_approval_policy_version"),
        sa.UniqueConstraint("policy_sha256", name="uq_approval_policy_sha256"),
        sa.UniqueConstraint(
            "approval_policy_version_id",
            "policy_sha256",
            name="uq_approval_policy_version_id_sha256",
        ),
    )

    op.create_table(
        "approval_scopes",
        sa.Column("approval_scope_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("scope_id", sa.String(length=256), nullable=False),
        sa.Column("scope_version", sa.Integer(), nullable=False),
        sa.Column("scope_sha256", sa.String(length=64), nullable=False),
        sa.Column("research_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("research_artifact_sha256", sa.String(length=64), nullable=False),
        sa.Column("approval_policy_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "permitted_universe_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        _decimal("max_notional"),
        sa.Column("valid_from_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("synthetic", sa.Boolean(), nullable=False),
        _payload(),
        _created_at(),
        _hash_check(
            ("scope_sha256", "research_artifact_sha256"),
            name="ck_approval_scope_hashes",
        ),
        sa.CheckConstraint(
            "schema_version = 'phase7-approval-scope-v1' "
            "AND btrim(scope_id) <> '' AND scope_version >= 1 "
            "AND jsonb_typeof(permitted_universe_ids) = 'array' "
            "AND jsonb_array_length(permitted_universe_ids) >= 1 "
            "AND max_notional >= 0 AND valid_from_utc < expires_at_utc "
            "AND synthetic AND jsonb_typeof(payload) = 'object'",
            name="ck_approval_scope_identity",
        ),
        sa.ForeignKeyConstraint(
            ["research_run_id", "research_artifact_sha256"],
            ["research_pipeline_runs.id", "research_pipeline_runs.artifact_sha256"],
            name="fk_approval_scope_research_artifact",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["approval_policy_version_id"],
            ["approval_policies.approval_policy_version_id"],
            name="fk_approval_scope_policy",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("approval_scope_version_id", name="pk_approval_scopes"),
        sa.UniqueConstraint("scope_id", "scope_version", name="uq_approval_scope_version"),
        sa.UniqueConstraint("scope_sha256", name="uq_approval_scope_sha256"),
        sa.UniqueConstraint(
            "approval_scope_version_id",
            "scope_sha256",
            name="uq_approval_scope_version_id_sha256",
        ),
    )

    op.create_table(
        "approval_authorizations",
        sa.Column(
            "human_authorization_evidence_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("authorization_sha256", sa.String(length=64), nullable=False),
        sa.Column("research_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("research_artifact_sha256", sa.String(length=64), nullable=False),
        sa.Column("approval_policy_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("approval_scope_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("authorized_by", sa.String(length=256), nullable=False),
        sa.Column("authorized_role", sa.String(length=128), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("authorized_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("review_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("human_controlled", sa.Boolean(), nullable=False),
        sa.Column("synthetic", sa.Boolean(), nullable=False),
        _payload(),
        _created_at(),
        _hash_check(
            ("authorization_sha256", "research_artifact_sha256"),
            name="ck_approval_authorization_hashes",
        ),
        sa.CheckConstraint(
            "schema_version = 'phase7-human-authorization-evidence-v1' "
            "AND btrim(authorized_by) <> '' "
            "AND authorized_role = 'paper_risk_reviewer' "
            "AND btrim(rationale) <> '' "
            "AND authorized_at_utc < review_at_utc "
            "AND review_at_utc <= expires_at_utc "
            "AND human_controlled AND synthetic "
            "AND jsonb_typeof(payload) = 'object'",
            name="ck_approval_authorization_identity",
        ),
        sa.ForeignKeyConstraint(
            ["research_run_id", "research_artifact_sha256"],
            ["research_pipeline_runs.id", "research_pipeline_runs.artifact_sha256"],
            name="fk_approval_authorization_research_artifact",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["approval_policy_version_id"],
            ["approval_policies.approval_policy_version_id"],
            name="fk_approval_authorization_policy",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["approval_scope_version_id"],
            ["approval_scopes.approval_scope_version_id"],
            name="fk_approval_authorization_scope",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "human_authorization_evidence_id", name="pk_approval_authorizations"
        ),
        sa.UniqueConstraint("authorization_sha256", name="uq_approval_authorization_sha256"),
        sa.UniqueConstraint(
            "human_authorization_evidence_id",
            "authorization_sha256",
            name="uq_approval_authorization_id_sha256",
        ),
    )

    op.create_table(
        "approval_risk_inputs",
        sa.Column("risk_input_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("risk_input_sha256", sa.String(length=64), nullable=False),
        sa.Column("research_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("research_artifact_sha256", sa.String(length=64), nullable=False),
        sa.Column("approval_policy_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("approval_scope_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("universe_id", sa.String(length=256), nullable=False),
        sa.Column("observed_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("global_control_clear", sa.Boolean(), nullable=True),
        sa.Column("strategy_control_clear", sa.Boolean(), nullable=True),
        sa.Column("data_quality_control_clear", sa.Boolean(), nullable=True),
        sa.Column("market_calendar_open", sa.Boolean(), nullable=True),
        sa.Column("duplicate_context_clear", sa.Boolean(), nullable=True),
        _decimal("proposed_notional", nullable=True),
        _decimal("gross_exposure", nullable=True),
        _decimal("net_exposure", nullable=True),
        _decimal("sector_exposure", nullable=True),
        _decimal("concentration", nullable=True),
        _decimal("available_liquidity", nullable=True),
        _decimal("turnover", nullable=True),
        _decimal("volatility", nullable=True),
        _decimal("daily_loss", nullable=True),
        _decimal("drawdown", nullable=True),
        sa.Column("synthetic", sa.Boolean(), nullable=False),
        _payload(),
        _created_at(),
        _hash_check(
            ("risk_input_sha256", "research_artifact_sha256"),
            name="ck_approval_risk_input_hashes",
        ),
        sa.CheckConstraint(
            "schema_version = 'phase7-approval-risk-input-v1' "
            "AND btrim(universe_id) <> '' AND synthetic "
            "AND (proposed_notional IS NULL OR proposed_notional >= 0) "
            "AND (gross_exposure IS NULL OR gross_exposure >= 0) "
            "AND (sector_exposure IS NULL OR sector_exposure >= 0) "
            "AND (concentration IS NULL OR concentration >= 0) "
            "AND (available_liquidity IS NULL OR available_liquidity >= 0) "
            "AND (turnover IS NULL OR turnover >= 0) "
            "AND (volatility IS NULL OR volatility >= 0) "
            "AND (daily_loss IS NULL OR daily_loss >= 0) "
            "AND (drawdown IS NULL OR drawdown >= 0) "
            "AND jsonb_typeof(payload) = 'object'",
            name="ck_approval_risk_input_identity",
        ),
        sa.ForeignKeyConstraint(
            ["research_run_id", "research_artifact_sha256"],
            ["research_pipeline_runs.id", "research_pipeline_runs.artifact_sha256"],
            name="fk_approval_risk_input_research_artifact",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["approval_policy_version_id"],
            ["approval_policies.approval_policy_version_id"],
            name="fk_approval_risk_input_policy",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["approval_scope_version_id"],
            ["approval_scopes.approval_scope_version_id"],
            name="fk_approval_risk_input_scope",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("risk_input_id", name="pk_approval_risk_inputs"),
        sa.UniqueConstraint("risk_input_sha256", name="uq_approval_risk_input_sha256"),
        sa.UniqueConstraint(
            "risk_input_id",
            "risk_input_sha256",
            name="uq_approval_risk_input_id_sha256",
        ),
    )

    op.create_table(
        "approval_revocations",
        sa.Column("revocation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("artifact_schema_version", sa.String(length=64), nullable=False),
        sa.Column("artifact_sha256", sa.String(length=64), nullable=False),
        sa.Column("request_fingerprint_sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "human_authorization_evidence_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("authorization_sha256", sa.String(length=64), nullable=False),
        sa.Column("revocation_evidence_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("revocation_evidence_sha256", sa.String(length=64), nullable=False),
        sa.Column("revoked_by", sa.String(length=256), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("effective_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("phase7_code_version_git_sha", sa.String(length=40), nullable=False),
        sa.Column("synthetic", sa.Boolean(), nullable=False),
        sa.Column("simulated_paper_only", sa.Boolean(), nullable=False),
        sa.Column("execution_authorized", sa.Boolean(), nullable=False),
        sa.Column("execution_ready", sa.Boolean(), nullable=False),
        sa.Column("no_personalized_investment_advice", sa.Boolean(), nullable=False),
        sa.Column("no_real_performance_claimed", sa.Boolean(), nullable=False),
        _payload("artifact_payload"),
        _created_at(),
        _hash_check(
            (
                "artifact_sha256",
                "request_fingerprint_sha256",
                "authorization_sha256",
                "revocation_evidence_sha256",
            ),
            name="ck_approval_revocation_hashes",
        ),
        sa.CheckConstraint(
            "artifact_schema_version = 'phase7-authorization-revocation-v1' "
            "AND btrim(revoked_by) <> '' AND btrim(reason) <> '' "
            "AND phase7_code_version_git_sha ~ '^[0-9a-f]{40}$' "
            "AND synthetic AND simulated_paper_only "
            "AND NOT execution_authorized AND NOT execution_ready "
            "AND no_personalized_investment_advice "
            "AND no_real_performance_claimed "
            "AND jsonb_typeof(artifact_payload) = 'object'",
            name="ck_approval_revocation_boundary",
        ),
        sa.ForeignKeyConstraint(
            ["human_authorization_evidence_id", "authorization_sha256"],
            [
                "approval_authorizations.human_authorization_evidence_id",
                "approval_authorizations.authorization_sha256",
            ],
            name="fk_approval_revocation_authorization",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("revocation_id", name="pk_approval_revocations"),
        sa.UniqueConstraint("request_fingerprint_sha256", name="uq_approval_revocation_request"),
        sa.UniqueConstraint("artifact_sha256", name="uq_approval_revocation_artifact"),
        sa.UniqueConstraint(
            "human_authorization_evidence_id",
            "revocation_evidence_id",
            name="uq_approval_revocation_evidence_use",
        ),
    )

    op.create_table(
        "approval_assessments",
        sa.Column("assessment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("artifact_schema_version", sa.String(length=64), nullable=False),
        sa.Column("artifact_sha256", sa.String(length=64), nullable=False),
        sa.Column("request_fingerprint_sha256", sa.String(length=64), nullable=False),
        sa.Column("currentness_state_sha256", sa.String(length=64), nullable=False),
        sa.Column("revocation_set_sha256", sa.String(length=64), nullable=False),
        sa.Column("research_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("research_artifact_sha256", sa.String(length=64), nullable=False),
        sa.Column("approval_policy_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("approval_policy_sha256", sa.String(length=64), nullable=False),
        sa.Column("approval_scope_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("approval_scope_sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "human_authorization_evidence_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("authorization_sha256", sa.String(length=64), nullable=False),
        sa.Column("risk_input_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("risk_input_sha256", sa.String(length=64), nullable=False),
        sa.Column("phase6_lineage_sha256", sa.String(length=64), nullable=False),
        sa.Column("revocation_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("reason_codes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("phase7_code_version_git_sha", sa.String(length=40), nullable=False),
        sa.Column("synthetic", sa.Boolean(), nullable=False),
        sa.Column("simulated_paper_only", sa.Boolean(), nullable=False),
        sa.Column("execution_authorized", sa.Boolean(), nullable=False),
        sa.Column("execution_ready", sa.Boolean(), nullable=False),
        sa.Column("no_personalized_investment_advice", sa.Boolean(), nullable=False),
        sa.Column("no_real_performance_claimed", sa.Boolean(), nullable=False),
        _payload("artifact_payload"),
        _created_at(),
        _hash_check(
            (
                "artifact_sha256",
                "request_fingerprint_sha256",
                "currentness_state_sha256",
                "revocation_set_sha256",
                "research_artifact_sha256",
                "approval_policy_sha256",
                "approval_scope_sha256",
                "authorization_sha256",
                "risk_input_sha256",
                "phase6_lineage_sha256",
            ),
            name="ck_approval_assessment_hashes",
        ),
        sa.CheckConstraint(
            "artifact_schema_version = 'phase7-approval-assessment-v1' "
            "AND outcome IN ('APPROVED_PAPER','FAIL_REJECT') "
            "AND jsonb_typeof(revocation_ids) = 'array' "
            "AND jsonb_typeof(reason_codes) = 'array' "
            "AND jsonb_array_length(reason_codes) >= 1 "
            "AND phase7_code_version_git_sha ~ '^[0-9a-f]{40}$' "
            "AND synthetic AND simulated_paper_only "
            "AND NOT execution_authorized AND NOT execution_ready "
            "AND no_personalized_investment_advice "
            "AND no_real_performance_claimed "
            "AND jsonb_typeof(artifact_payload) = 'object'",
            name="ck_approval_assessment_boundary",
        ),
        sa.ForeignKeyConstraint(
            ["research_run_id", "research_artifact_sha256"],
            ["research_pipeline_runs.id", "research_pipeline_runs.artifact_sha256"],
            name="fk_approval_assessment_research_artifact",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["approval_policy_version_id", "approval_policy_sha256"],
            [
                "approval_policies.approval_policy_version_id",
                "approval_policies.policy_sha256",
            ],
            name="fk_approval_assessment_policy",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["approval_scope_version_id", "approval_scope_sha256"],
            [
                "approval_scopes.approval_scope_version_id",
                "approval_scopes.scope_sha256",
            ],
            name="fk_approval_assessment_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["human_authorization_evidence_id", "authorization_sha256"],
            [
                "approval_authorizations.human_authorization_evidence_id",
                "approval_authorizations.authorization_sha256",
            ],
            name="fk_approval_assessment_authorization",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["risk_input_id", "risk_input_sha256"],
            ["approval_risk_inputs.risk_input_id", "approval_risk_inputs.risk_input_sha256"],
            name="fk_approval_assessment_risk_input",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("assessment_id", name="pk_approval_assessments"),
        sa.UniqueConstraint("request_fingerprint_sha256", name="uq_approval_assessment_request"),
        sa.UniqueConstraint("artifact_sha256", name="uq_approval_assessment_artifact"),
        sa.UniqueConstraint(
            "assessment_id",
            "artifact_sha256",
            name="uq_approval_assessment_id_sha256",
        ),
    )
    op.create_index(
        "ix_approval_assessments_research_created",
        "approval_assessments",
        ["research_run_id", "created_at_utc", "assessment_id"],
    )

    op.create_table(
        "approval_checks",
        sa.Column("assessment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assessment_artifact_sha256", sa.String(length=64), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("reason_code", sa.String(length=256), nullable=False),
        sa.Column("observed_value", sa.String(length=500), nullable=True),
        sa.Column("threshold_value", sa.String(length=500), nullable=True),
        sa.Column("evidence_sha256s", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("check_sha256", sa.String(length=64), nullable=False),
        _payload(),
        _created_at(),
        _hash_check(
            ("assessment_artifact_sha256", "check_sha256"),
            name="ck_approval_check_hashes",
        ),
        sa.CheckConstraint(
            f"ordinal BETWEEN 1 AND {len(PHASE7_CHECK_CODES)} "
            f"AND code IN ({_check_code_sql()}) "
            "AND status IN ('PASS','FAIL','UNCOMPUTABLE','BLOCKED') "
            "AND btrim(reason_code) <> '' "
            "AND jsonb_typeof(evidence_sha256s) = 'array' "
            "AND jsonb_array_length(evidence_sha256s) >= 1 "
            "AND jsonb_typeof(payload) = 'object'",
            name="ck_approval_check_identity",
        ),
        sa.ForeignKeyConstraint(
            ["assessment_id", "assessment_artifact_sha256"],
            ["approval_assessments.assessment_id", "approval_assessments.artifact_sha256"],
            name="fk_approval_check_assessment",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("assessment_id", "ordinal", name="pk_approval_checks"),
        sa.UniqueConstraint("assessment_id", "code", name="uq_approval_check_code"),
        sa.UniqueConstraint("assessment_id", "check_sha256", name="uq_approval_check_hash"),
    )

    _install_validation_functions()
    _install_validation_triggers()
    _install_append_only_guards()


def _install_validation_functions() -> None:
    op.execute(
        """
        CREATE FUNCTION own_phase7_created_at_utc()
        RETURNS trigger AS $$
        BEGIN
            NEW.created_at_utc := clock_timestamp();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE FUNCTION phase7_lock_authorization_identity()
        RETURNS trigger AS $$
        BEGIN
            PERFORM pg_advisory_xact_lock(
                hashtextextended(NEW.human_authorization_evidence_id::text, 0)
            );
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE FUNCTION validate_phase7_research_eligibility()
        RETURNS trigger AS $$
        DECLARE
            run_row research_pipeline_runs%ROWTYPE;
        BEGIN
            SELECT * INTO run_row
            FROM research_pipeline_runs
            WHERE id = NEW.research_run_id
              AND artifact_sha256 = NEW.research_artifact_sha256
            FOR KEY SHARE;
            IF NOT FOUND THEN
                RAISE EXCEPTION
                    'Phase 7 evidence requires an exact persisted Phase 6 artifact';
            END IF;
            -- A complete negative assessment is itself valuable immutable
            -- evidence.  Non-PASS research and mutually conflicting evidence
            -- may therefore be recorded as FAIL_REJECT.  The positive branch
            -- alone is constrained to the eligible Phase 6 state.
            IF TG_TABLE_NAME = 'approval_assessments' THEN
                IF NEW.outcome = 'APPROVED_PAPER'
                   AND (
                        run_row.status <> 'completed'
                        OR run_row.promotion_state <> 'PASS_RESEARCH'
                        OR run_row.evaluation_report_id IS NULL
                        OR run_row.evaluation_outcome_id IS NOT NULL
                        OR NOT run_row.no_real_performance_claimed
                        OR run_row.paper_approval_granted
                   ) THEN
                    RAISE EXCEPTION
                        'Phase 7 positive approval requires exact eligible '
                        'Phase 6 PASS_RESEARCH lineage';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE FUNCTION validate_phase7_evidence_relationships()
        RETURNS trigger AS $$
        DECLARE
            policy_row approval_policies%ROWTYPE;
            scope_row approval_scopes%ROWTYPE;
            auth_row approval_authorizations%ROWTYPE;
            risk_row approval_risk_inputs%ROWTYPE;
            assessment_time timestamptz;
        BEGIN
            IF TG_TABLE_NAME <> 'approval_assessments' THEN
                RETURN NEW;
            END IF;
            IF NEW.outcome = 'FAIL_REJECT' THEN
                RETURN NEW;
            END IF;
            assessment_time := NEW.created_at_utc;
            IF assessment_time IS NULL THEN
                RAISE EXCEPTION
                    'Phase 7 positive approval requires a database-owned assessment time';
            END IF;

            SELECT * INTO policy_row
            FROM approval_policies
            WHERE approval_policy_version_id = NEW.approval_policy_version_id
            FOR KEY SHARE;
            SELECT * INTO scope_row
            FROM approval_scopes
            WHERE approval_scope_version_id = NEW.approval_scope_version_id
            FOR KEY SHARE;
            IF NOT FOUND
               OR scope_row.research_run_id <> NEW.research_run_id
               OR scope_row.research_artifact_sha256 <> NEW.research_artifact_sha256
               OR scope_row.approval_policy_version_id <> NEW.approval_policy_version_id THEN
                RAISE EXCEPTION 'Phase 7 scope lineage mismatch';
            END IF;

            SELECT * INTO auth_row
            FROM approval_authorizations
            WHERE human_authorization_evidence_id =
                    NEW.human_authorization_evidence_id
            FOR KEY SHARE;
            SELECT * INTO risk_row
            FROM approval_risk_inputs
            WHERE risk_input_id = NEW.risk_input_id
            FOR KEY SHARE;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'Phase 7 assessment risk input is missing';
            END IF;
            IF auth_row.human_authorization_evidence_id IS NULL
               OR auth_row.research_run_id <> NEW.research_run_id
               OR auth_row.research_artifact_sha256 <> NEW.research_artifact_sha256
               OR auth_row.approval_policy_version_id <> NEW.approval_policy_version_id
               OR auth_row.approval_scope_version_id <> NEW.approval_scope_version_id
               OR risk_row.research_run_id <> NEW.research_run_id
               OR risk_row.research_artifact_sha256 <> NEW.research_artifact_sha256
               OR risk_row.approval_policy_version_id <> NEW.approval_policy_version_id
               OR risk_row.approval_scope_version_id <> NEW.approval_scope_version_id THEN
                RAISE EXCEPTION 'Phase 7 assessment evidence lineage mismatch';
            END IF;
            -- The public workflow owns check calculation, but the database
            -- independently derives the positive branch from immutable
            -- evidence.  A direct writer cannot turn expired, stale,
            -- revoked, missing, or breached evidence into an all-PASS row by
            -- manufacturing self-consistent child hashes.
            IF policy_row.approval_policy_version_id IS NULL
               OR NOT (
                    policy_row.valid_from_utc <= assessment_time
                    AND assessment_time < policy_row.expires_at_utc
               )
               OR NOT (
                    scope_row.valid_from_utc <= assessment_time
                    AND assessment_time < scope_row.expires_at_utc
               )
               OR NOT (
                    auth_row.authorized_at_utc <= assessment_time
                    AND assessment_time < auth_row.review_at_utc
                    AND assessment_time < auth_row.expires_at_utc
               )
               OR EXTRACT(
                    EPOCH FROM (assessment_time - auth_row.authorized_at_utc)
                  ) > policy_row.authorization_max_age_seconds
               OR risk_row.observed_at_utc > assessment_time
               OR EXTRACT(
                    EPOCH FROM (assessment_time - risk_row.observed_at_utc)
                  ) > policy_row.risk_input_max_age_seconds
               OR risk_row.global_control_clear IS DISTINCT FROM TRUE
               OR risk_row.strategy_control_clear IS DISTINCT FROM TRUE
               OR risk_row.data_quality_control_clear IS DISTINCT FROM TRUE
               OR risk_row.market_calendar_open IS DISTINCT FROM TRUE
               OR risk_row.duplicate_context_clear IS DISTINCT FROM TRUE
               OR NOT (
                    scope_row.permitted_universe_ids
                    @> jsonb_build_array(to_jsonb(risk_row.universe_id))
               )
               OR risk_row.proposed_notional IS NULL
               OR risk_row.proposed_notional > LEAST(
                    policy_row.max_notional, scope_row.max_notional
               )
               OR risk_row.gross_exposure IS NULL
               OR risk_row.gross_exposure > policy_row.max_gross_exposure
               OR risk_row.net_exposure IS NULL
               OR abs(risk_row.net_exposure) > policy_row.max_abs_net_exposure
               OR risk_row.sector_exposure IS NULL
               OR risk_row.sector_exposure > policy_row.max_sector_exposure
               OR risk_row.concentration IS NULL
               OR risk_row.concentration > policy_row.max_concentration
               OR risk_row.available_liquidity IS NULL
               OR risk_row.available_liquidity < policy_row.min_liquidity
               OR risk_row.turnover IS NULL
               OR risk_row.turnover > policy_row.max_turnover
               OR risk_row.volatility IS NULL
               OR risk_row.volatility > policy_row.max_volatility
               OR risk_row.daily_loss IS NULL
               OR risk_row.daily_loss > policy_row.max_daily_loss
               OR risk_row.drawdown IS NULL
               OR risk_row.drawdown > policy_row.max_drawdown
               OR EXISTS (
                    SELECT 1
                    FROM approval_revocations AS revocation
                    WHERE revocation.human_authorization_evidence_id =
                            NEW.human_authorization_evidence_id
                      AND revocation.effective_at_utc <= assessment_time
               )
               OR EXISTS (
                    SELECT 1
                    FROM approval_policies AS later_policy
                    WHERE later_policy.policy_id = policy_row.policy_id
                      AND later_policy.policy_version > policy_row.policy_version
                      AND later_policy.valid_from_utc <= assessment_time
                      AND assessment_time < later_policy.expires_at_utc
               )
               OR EXISTS (
                    SELECT 1
                    FROM approval_scopes AS later_scope
                    WHERE later_scope.scope_id = scope_row.scope_id
                      AND later_scope.scope_version > scope_row.scope_version
                      AND later_scope.valid_from_utc <= assessment_time
                      AND assessment_time < later_scope.expires_at_utc
               ) THEN
                RAISE EXCEPTION
                    'Phase 7 positive approval evidence is stale, revoked, '
                    'uncomputable, superseded, or outside risk limits';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE FUNCTION validate_phase7_payload_consistency()
        RETURNS trigger AS $$
        BEGIN
            IF TG_TABLE_NAME = 'approval_policies' THEN
                IF (SELECT count(*) FROM jsonb_object_keys(NEW.payload)) <> 19
                   OR NOT NEW.payload ?& ARRAY[
                        'schema_version','policy_id','policy_version',
                        'valid_from_utc','expires_at_utc',
                        'authorization_max_age_seconds',
                        'risk_input_max_age_seconds','required_check_codes',
                        'max_notional','max_gross_exposure',
                        'max_abs_net_exposure','max_sector_exposure',
                        'max_concentration','min_liquidity','max_turnover',
                        'max_volatility','max_daily_loss','max_drawdown','synthetic'
                   ]
                   OR NEW.payload->>'schema_version' IS DISTINCT FROM NEW.schema_version
                   OR NEW.payload->>'policy_id' IS DISTINCT FROM NEW.policy_id
                   OR (NEW.payload->>'policy_version')::integer
                        IS DISTINCT FROM NEW.policy_version
                   OR (NEW.payload->>'valid_from_utc')::timestamptz
                        IS DISTINCT FROM NEW.valid_from_utc
                   OR (NEW.payload->>'expires_at_utc')::timestamptz
                        IS DISTINCT FROM NEW.expires_at_utc
                   OR (NEW.payload->>'authorization_max_age_seconds')::integer
                        IS DISTINCT FROM NEW.authorization_max_age_seconds
                   OR (NEW.payload->>'risk_input_max_age_seconds')::integer
                        IS DISTINCT FROM NEW.risk_input_max_age_seconds
                   OR NEW.payload->'required_check_codes'
                        IS DISTINCT FROM NEW.required_check_codes
                   OR (NEW.payload->>'max_notional')::numeric
                        IS DISTINCT FROM NEW.max_notional
                   OR (NEW.payload->>'max_gross_exposure')::numeric
                        IS DISTINCT FROM NEW.max_gross_exposure
                   OR (NEW.payload->>'max_abs_net_exposure')::numeric
                        IS DISTINCT FROM NEW.max_abs_net_exposure
                   OR (NEW.payload->>'max_sector_exposure')::numeric
                        IS DISTINCT FROM NEW.max_sector_exposure
                   OR (NEW.payload->>'max_concentration')::numeric
                        IS DISTINCT FROM NEW.max_concentration
                   OR (NEW.payload->>'min_liquidity')::numeric
                        IS DISTINCT FROM NEW.min_liquidity
                   OR (NEW.payload->>'max_turnover')::numeric
                        IS DISTINCT FROM NEW.max_turnover
                   OR (NEW.payload->>'max_volatility')::numeric
                        IS DISTINCT FROM NEW.max_volatility
                   OR (NEW.payload->>'max_daily_loss')::numeric
                        IS DISTINCT FROM NEW.max_daily_loss
                   OR (NEW.payload->>'max_drawdown')::numeric
                        IS DISTINCT FROM NEW.max_drawdown
                   OR (NEW.payload->>'synthetic')::boolean
                        IS DISTINCT FROM NEW.synthetic
                   OR phase6_domain_sha256(
                        'phase7-approval-policy-v1', NEW.payload
                      ) IS DISTINCT FROM NEW.policy_sha256
                   OR phase6_uuid5(
                        '5e62ae67-7d9f-5f07-9883-b0f8d00cd33a'::uuid,
                        NEW.policy_sha256
                      ) IS DISTINCT FROM NEW.approval_policy_version_id THEN
                    RAISE EXCEPTION 'Phase 7 policy payload mismatch';
                END IF;
            ELSIF TG_TABLE_NAME = 'approval_scopes' THEN
                IF (SELECT count(*) FROM jsonb_object_keys(NEW.payload)) <> 11
                   OR NOT NEW.payload ?& ARRAY[
                        'schema_version','scope_id','scope_version','research_run_id',
                        'research_artifact_sha256','approval_policy_version_id',
                        'permitted_universe_ids','max_notional','valid_from_utc',
                        'expires_at_utc','synthetic'
                   ]
                   OR NEW.payload->>'schema_version' IS DISTINCT FROM NEW.schema_version
                   OR NEW.payload->>'scope_id' IS DISTINCT FROM NEW.scope_id
                   OR (NEW.payload->>'scope_version')::integer
                        IS DISTINCT FROM NEW.scope_version
                   OR (NEW.payload->>'research_run_id')::uuid
                        IS DISTINCT FROM NEW.research_run_id
                   OR NEW.payload->>'research_artifact_sha256'
                        IS DISTINCT FROM NEW.research_artifact_sha256
                   OR (NEW.payload->>'approval_policy_version_id')::uuid
                        IS DISTINCT FROM NEW.approval_policy_version_id
                   OR NEW.payload->'permitted_universe_ids'
                        IS DISTINCT FROM NEW.permitted_universe_ids
                   OR (NEW.payload->>'max_notional')::numeric
                        IS DISTINCT FROM NEW.max_notional
                   OR (NEW.payload->>'valid_from_utc')::timestamptz
                        IS DISTINCT FROM NEW.valid_from_utc
                   OR (NEW.payload->>'expires_at_utc')::timestamptz
                        IS DISTINCT FROM NEW.expires_at_utc
                   OR (NEW.payload->>'synthetic')::boolean
                        IS DISTINCT FROM NEW.synthetic
                   OR phase6_domain_sha256(
                        'phase7-approval-scope-v1', NEW.payload
                      ) IS DISTINCT FROM NEW.scope_sha256
                   OR phase6_uuid5(
                        '13294abe-cf1d-5601-8d3d-a598a1c84d80'::uuid,
                        NEW.scope_sha256
                      ) IS DISTINCT FROM NEW.approval_scope_version_id THEN
                    RAISE EXCEPTION 'Phase 7 scope payload mismatch';
                END IF;
            ELSIF TG_TABLE_NAME = 'approval_authorizations' THEN
                IF (SELECT count(*) FROM jsonb_object_keys(NEW.payload)) <> 13
                   OR NOT NEW.payload ?& ARRAY[
                        'schema_version','research_run_id',
                        'research_artifact_sha256','approval_policy_version_id',
                        'approval_scope_version_id','authorized_by','authorized_role',
                        'rationale','authorized_at_utc','review_at_utc',
                        'expires_at_utc','human_controlled','synthetic'
                   ]
                   OR NEW.payload->>'schema_version' IS DISTINCT FROM NEW.schema_version
                   OR (NEW.payload->>'research_run_id')::uuid
                        IS DISTINCT FROM NEW.research_run_id
                   OR NEW.payload->>'research_artifact_sha256'
                        IS DISTINCT FROM NEW.research_artifact_sha256
                   OR (NEW.payload->>'approval_policy_version_id')::uuid
                        IS DISTINCT FROM NEW.approval_policy_version_id
                   OR (NEW.payload->>'approval_scope_version_id')::uuid
                        IS DISTINCT FROM NEW.approval_scope_version_id
                   OR NEW.payload->>'authorized_by' IS DISTINCT FROM NEW.authorized_by
                   OR NEW.payload->>'authorized_role' IS DISTINCT FROM NEW.authorized_role
                   OR NEW.payload->>'rationale' IS DISTINCT FROM NEW.rationale
                   OR (NEW.payload->>'authorized_at_utc')::timestamptz
                        IS DISTINCT FROM NEW.authorized_at_utc
                   OR (NEW.payload->>'review_at_utc')::timestamptz
                        IS DISTINCT FROM NEW.review_at_utc
                   OR (NEW.payload->>'expires_at_utc')::timestamptz
                        IS DISTINCT FROM NEW.expires_at_utc
                   OR (NEW.payload->>'human_controlled')::boolean
                        IS DISTINCT FROM NEW.human_controlled
                   OR (NEW.payload->>'synthetic')::boolean
                        IS DISTINCT FROM NEW.synthetic
                   OR phase6_domain_sha256(
                        'phase7-human-authorization-evidence-v1', NEW.payload
                      ) IS DISTINCT FROM NEW.authorization_sha256
                   OR phase6_uuid5(
                        'fa3bb88d-4b5f-5b59-a2ae-e2c18a2b052f'::uuid,
                        NEW.authorization_sha256
                      ) IS DISTINCT FROM NEW.human_authorization_evidence_id THEN
                    RAISE EXCEPTION 'Phase 7 authorization payload mismatch';
                END IF;
            ELSIF TG_TABLE_NAME = 'approval_risk_inputs' THEN
                IF (SELECT count(*) FROM jsonb_object_keys(NEW.payload)) <> 23
                   OR NOT NEW.payload ?& ARRAY[
                        'schema_version','research_run_id',
                        'research_artifact_sha256','approval_policy_version_id',
                        'approval_scope_version_id','universe_id','observed_at_utc',
                        'global_control_clear','strategy_control_clear',
                        'data_quality_control_clear','market_calendar_open',
                        'duplicate_context_clear','proposed_notional','gross_exposure',
                        'net_exposure','sector_exposure','concentration',
                        'available_liquidity','turnover','volatility','daily_loss',
                        'drawdown','synthetic'
                   ]
                   OR NEW.payload->>'schema_version' IS DISTINCT FROM NEW.schema_version
                   OR (NEW.payload->>'research_run_id')::uuid
                        IS DISTINCT FROM NEW.research_run_id
                   OR NEW.payload->>'research_artifact_sha256'
                        IS DISTINCT FROM NEW.research_artifact_sha256
                   OR (NEW.payload->>'approval_policy_version_id')::uuid
                        IS DISTINCT FROM NEW.approval_policy_version_id
                   OR (NEW.payload->>'approval_scope_version_id')::uuid
                        IS DISTINCT FROM NEW.approval_scope_version_id
                   OR NEW.payload->>'universe_id' IS DISTINCT FROM NEW.universe_id
                   OR (NEW.payload->>'observed_at_utc')::timestamptz
                        IS DISTINCT FROM NEW.observed_at_utc
                   OR (NEW.payload->>'global_control_clear')::boolean
                        IS DISTINCT FROM NEW.global_control_clear
                   OR (NEW.payload->>'strategy_control_clear')::boolean
                        IS DISTINCT FROM NEW.strategy_control_clear
                   OR (NEW.payload->>'data_quality_control_clear')::boolean
                        IS DISTINCT FROM NEW.data_quality_control_clear
                   OR (NEW.payload->>'market_calendar_open')::boolean
                        IS DISTINCT FROM NEW.market_calendar_open
                   OR (NEW.payload->>'duplicate_context_clear')::boolean
                        IS DISTINCT FROM NEW.duplicate_context_clear
                   OR (NEW.payload->>'proposed_notional')::numeric
                        IS DISTINCT FROM NEW.proposed_notional
                   OR (NEW.payload->>'gross_exposure')::numeric
                        IS DISTINCT FROM NEW.gross_exposure
                   OR (NEW.payload->>'net_exposure')::numeric
                        IS DISTINCT FROM NEW.net_exposure
                   OR (NEW.payload->>'sector_exposure')::numeric
                        IS DISTINCT FROM NEW.sector_exposure
                   OR (NEW.payload->>'concentration')::numeric
                        IS DISTINCT FROM NEW.concentration
                   OR (NEW.payload->>'available_liquidity')::numeric
                        IS DISTINCT FROM NEW.available_liquidity
                   OR (NEW.payload->>'turnover')::numeric
                        IS DISTINCT FROM NEW.turnover
                   OR (NEW.payload->>'volatility')::numeric
                        IS DISTINCT FROM NEW.volatility
                   OR (NEW.payload->>'daily_loss')::numeric
                        IS DISTINCT FROM NEW.daily_loss
                   OR (NEW.payload->>'drawdown')::numeric
                        IS DISTINCT FROM NEW.drawdown
                   OR (NEW.payload->>'synthetic')::boolean
                        IS DISTINCT FROM NEW.synthetic
                   OR phase6_domain_sha256(
                        'phase7-approval-risk-input-v1', NEW.payload
                      ) IS DISTINCT FROM NEW.risk_input_sha256
                   OR phase6_uuid5(
                        'b7bc3b85-b2d7-55ad-8ca1-89bb8e16577f'::uuid,
                        NEW.risk_input_sha256
                      ) IS DISTINCT FROM NEW.risk_input_id THEN
                    RAISE EXCEPTION 'Phase 7 risk-input payload mismatch';
                END IF;
            ELSIF TG_TABLE_NAME = 'approval_assessments' THEN
                IF (
                    SELECT count(*)
                    FROM jsonb_object_keys(NEW.artifact_payload)
                   ) <> 26
                   OR NOT NEW.artifact_payload ?& ARRAY[
                        'artifact_schema_version','request_fingerprint_sha256',
                        'currentness_state_sha256','revocation_set_sha256',
                        'research_run_id','approval_policy_version_id',
                        'approval_scope_version_id',
                        'human_authorization_evidence_id','risk_input_id',
                        'phase6_lineage','approval_policy_sha256',
                        'approval_scope_sha256','authorization_sha256',
                        'risk_input_sha256','revocation_ids','checks','outcome',
                        'reason_codes','phase7_code_version_git_sha','synthetic',
                        'simulated_paper_only','execution_authorized','execution_ready',
                        'no_personalized_investment_advice',
                        'no_real_performance_claimed','disclaimer'
                   ]
                   OR NEW.artifact_payload->>'artifact_schema_version'
                        IS DISTINCT FROM NEW.artifact_schema_version
                   OR NEW.artifact_payload->>'request_fingerprint_sha256'
                        IS DISTINCT FROM NEW.request_fingerprint_sha256
                   OR NEW.artifact_payload->>'currentness_state_sha256'
                        IS DISTINCT FROM NEW.currentness_state_sha256
                   OR NEW.artifact_payload->>'revocation_set_sha256'
                        IS DISTINCT FROM NEW.revocation_set_sha256
                   OR (NEW.artifact_payload->>'research_run_id')::uuid
                        IS DISTINCT FROM NEW.research_run_id
                   OR NEW.artifact_payload#>>
                        '{phase6_lineage,research_artifact_sha256}'
                        IS DISTINCT FROM NEW.research_artifact_sha256
                   OR (NEW.artifact_payload->>'approval_policy_version_id')::uuid
                        IS DISTINCT FROM NEW.approval_policy_version_id
                   OR NEW.artifact_payload->>'approval_policy_sha256'
                        IS DISTINCT FROM NEW.approval_policy_sha256
                   OR (NEW.artifact_payload->>'approval_scope_version_id')::uuid
                        IS DISTINCT FROM NEW.approval_scope_version_id
                   OR NEW.artifact_payload->>'approval_scope_sha256'
                        IS DISTINCT FROM NEW.approval_scope_sha256
                   OR (
                        NEW.artifact_payload->>'human_authorization_evidence_id'
                      )::uuid IS DISTINCT FROM NEW.human_authorization_evidence_id
                   OR NEW.artifact_payload->>'authorization_sha256'
                        IS DISTINCT FROM NEW.authorization_sha256
                   OR (NEW.artifact_payload->>'risk_input_id')::uuid
                        IS DISTINCT FROM NEW.risk_input_id
                   OR NEW.artifact_payload->>'risk_input_sha256'
                        IS DISTINCT FROM NEW.risk_input_sha256
                   OR NEW.artifact_payload#>>'{phase6_lineage,lineage_sha256}'
                        IS DISTINCT FROM NEW.phase6_lineage_sha256
                   OR NEW.artifact_payload->'revocation_ids'
                        IS DISTINCT FROM NEW.revocation_ids
                   OR NEW.artifact_payload->>'outcome' IS DISTINCT FROM NEW.outcome
                   OR NEW.artifact_payload->'reason_codes'
                        IS DISTINCT FROM NEW.reason_codes
                   OR NEW.artifact_payload->>'phase7_code_version_git_sha'
                        IS DISTINCT FROM NEW.phase7_code_version_git_sha
                   OR (NEW.artifact_payload->>'synthetic')::boolean
                        IS DISTINCT FROM NEW.synthetic
                   OR (NEW.artifact_payload->>'simulated_paper_only')::boolean
                        IS DISTINCT FROM NEW.simulated_paper_only
                   OR (NEW.artifact_payload->>'execution_authorized')::boolean
                        IS DISTINCT FROM NEW.execution_authorized
                   OR (NEW.artifact_payload->>'execution_ready')::boolean
                        IS DISTINCT FROM NEW.execution_ready
                   OR (
                        NEW.artifact_payload->>'no_personalized_investment_advice'
                      )::boolean IS DISTINCT FROM
                        NEW.no_personalized_investment_advice
                   OR (
                        NEW.artifact_payload->>'no_real_performance_claimed'
                      )::boolean IS DISTINCT FROM NEW.no_real_performance_claimed
                   OR phase6_domain_sha256(
                        'phase7-approval-assessment-v1', NEW.artifact_payload
                      ) IS DISTINCT FROM NEW.artifact_sha256
                   OR phase6_uuid5(
                        '88a24af5-ac54-5843-9280-c67cda6750fe'::uuid,
                        NEW.request_fingerprint_sha256
                      ) IS DISTINCT FROM NEW.assessment_id THEN
                    RAISE EXCEPTION 'Phase 7 assessment payload mismatch';
                END IF;
            ELSIF TG_TABLE_NAME = 'approval_revocations' THEN
                IF (
                    SELECT count(*)
                    FROM jsonb_object_keys(NEW.artifact_payload)
                   ) <> 16
                   OR NOT NEW.artifact_payload ?& ARRAY[
                        'artifact_schema_version','request_fingerprint_sha256',
                        'human_authorization_evidence_id','authorization_sha256',
                        'revocation_evidence_id','revocation_evidence_sha256',
                        'revoked_by','reason','effective_at_utc',
                        'phase7_code_version_git_sha','synthetic',
                        'simulated_paper_only','execution_authorized','execution_ready',
                        'no_personalized_investment_advice',
                        'no_real_performance_claimed'
                   ]
                   OR NEW.artifact_payload->>'artifact_schema_version'
                        IS DISTINCT FROM NEW.artifact_schema_version
                   OR NEW.artifact_payload->>'request_fingerprint_sha256'
                        IS DISTINCT FROM NEW.request_fingerprint_sha256
                   OR (NEW.artifact_payload->>'human_authorization_evidence_id')::uuid
                        IS DISTINCT FROM NEW.human_authorization_evidence_id
                   OR NEW.artifact_payload->>'authorization_sha256'
                        IS DISTINCT FROM NEW.authorization_sha256
                   OR (NEW.artifact_payload->>'revocation_evidence_id')::uuid
                        IS DISTINCT FROM NEW.revocation_evidence_id
                   OR NEW.artifact_payload->>'revocation_evidence_sha256'
                        IS DISTINCT FROM NEW.revocation_evidence_sha256
                   OR NEW.artifact_payload->>'revoked_by'
                        IS DISTINCT FROM NEW.revoked_by
                   OR NEW.artifact_payload->>'reason' IS DISTINCT FROM NEW.reason
                   OR (NEW.artifact_payload->>'effective_at_utc')::timestamptz
                        IS DISTINCT FROM NEW.effective_at_utc
                   OR NEW.artifact_payload->>'phase7_code_version_git_sha'
                        IS DISTINCT FROM NEW.phase7_code_version_git_sha
                   OR (NEW.artifact_payload->>'synthetic')::boolean
                        IS DISTINCT FROM NEW.synthetic
                   OR (NEW.artifact_payload->>'simulated_paper_only')::boolean
                        IS DISTINCT FROM NEW.simulated_paper_only
                   OR (NEW.artifact_payload->>'execution_authorized')::boolean
                        IS DISTINCT FROM NEW.execution_authorized
                   OR (NEW.artifact_payload->>'execution_ready')::boolean
                        IS DISTINCT FROM NEW.execution_ready
                   OR (
                        NEW.artifact_payload->>'no_personalized_investment_advice'
                      )::boolean IS DISTINCT FROM
                        NEW.no_personalized_investment_advice
                   OR (
                        NEW.artifact_payload->>'no_real_performance_claimed'
                      )::boolean IS DISTINCT FROM NEW.no_real_performance_claimed
                   OR phase6_domain_sha256(
                        'phase7-authorization-revocation-v1',
                        NEW.artifact_payload
                      ) IS DISTINCT FROM NEW.artifact_sha256
                   OR phase6_uuid5(
                        '971fe2ca-64c3-5c53-ac30-2c38a5ab04b8'::uuid,
                        NEW.request_fingerprint_sha256
                      ) IS DISTINCT FROM NEW.revocation_id THEN
                    RAISE EXCEPTION 'Phase 7 revocation payload mismatch';
                END IF;
            ELSIF TG_TABLE_NAME = 'approval_checks' THEN
                IF (SELECT count(*) FROM jsonb_object_keys(NEW.payload)) <> 8
                   OR NOT NEW.payload ?& ARRAY[
                        'ordinal','code','status','reason_code','observed_value',
                        'threshold_value','evidence_sha256s','check_sha256'
                   ]
                   OR (NEW.payload->>'ordinal')::integer IS DISTINCT FROM NEW.ordinal
                   OR NEW.payload->>'code' IS DISTINCT FROM NEW.code
                   OR NEW.payload->>'status' IS DISTINCT FROM NEW.status
                   OR NEW.payload->>'reason_code' IS DISTINCT FROM NEW.reason_code
                   OR NEW.payload->>'observed_value'
                        IS DISTINCT FROM NEW.observed_value
                   OR NEW.payload->>'threshold_value'
                        IS DISTINCT FROM NEW.threshold_value
                   OR NEW.payload->'evidence_sha256s'
                        IS DISTINCT FROM NEW.evidence_sha256s
                   OR NEW.payload->>'check_sha256' IS DISTINCT FROM NEW.check_sha256
                   OR phase6_domain_sha256(
                        'phase7-approval-check-v1',
                        NEW.payload - 'check_sha256'
                      ) IS DISTINCT FROM NEW.check_sha256 THEN
                    RAISE EXCEPTION 'Phase 7 check payload mismatch';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE FUNCTION validate_phase7_assessment_lineage()
        RETURNS trigger AS $$
        DECLARE
            run_row research_pipeline_runs%ROWTYPE;
            report_sha text;
            gate_codes jsonb;
            bindings jsonb;
            lineage jsonb;
        BEGIN
            SELECT * INTO run_row
            FROM research_pipeline_runs
            WHERE id = NEW.research_run_id
              AND artifact_sha256 = NEW.research_artifact_sha256
            FOR KEY SHARE;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'Phase 7 Phase 6 lineage target is missing';
            END IF;
            SELECT report_sha256 INTO report_sha
            FROM evaluation_reports
            WHERE report_id = run_row.evaluation_report_id;
            SELECT COALESCE(
                jsonb_agg(to_jsonb(gate_code) ORDER BY ordinal), '[]'::jsonb
            ) INTO gate_codes
            FROM evaluation_gate_results
            WHERE report_id = run_row.evaluation_report_id;
            SELECT COALESCE(jsonb_agg(payload ORDER BY ordinal), '[]'::jsonb)
            INTO bindings
            FROM research_pipeline_snapshot_bindings
            WHERE run_id = run_row.id;

            lineage := NEW.artifact_payload->'phase6_lineage';
            IF jsonb_typeof(lineage) IS DISTINCT FROM 'object'
               OR lineage->>'schema_version'
                    IS DISTINCT FROM 'phase7-phase6-approval-lineage-v1'
               OR lineage->>'lineage_sha256' IS DISTINCT FROM NEW.phase6_lineage_sha256
               OR phase6_domain_sha256(
                    'phase7-phase6-approval-lineage-v1',
                    lineage - 'lineage_sha256'
                  ) IS DISTINCT FROM NEW.phase6_lineage_sha256
               OR (lineage->>'research_run_id')::uuid IS DISTINCT FROM run_row.id
               OR lineage->>'research_artifact_sha256'
                    IS DISTINCT FROM run_row.artifact_sha256
               OR lineage->>'research_request_fingerprint_sha256'
                    IS DISTINCT FROM run_row.request_fingerprint_sha256
               OR lineage->>'research_configuration_id'
                    IS DISTINCT FROM run_row.configuration_id
               OR lineage->>'research_configuration_sha256'
                    IS DISTINCT FROM run_row.configuration_sha256
               OR lineage->>'research_status' IS DISTINCT FROM run_row.status
               OR lineage->>'promotion_state' IS DISTINCT FROM run_row.promotion_state
               OR (lineage->>'mapping_id')::uuid IS DISTINCT FROM run_row.mapping_id
               OR (lineage->>'mapping_version')::integer IS DISTINCT FROM
                    (run_row.artifact_payload->>'mapping_version')::integer
               OR lineage->>'mapping_input_sha256'
                    IS DISTINCT FROM run_row.artifact_payload->>'mapping_input_sha256'
               OR lineage->>'canonical_family' IS DISTINCT FROM run_row.canonical_family
               OR lineage->>'specification_sha256'
                    IS DISTINCT FROM run_row.specification_sha256
               OR lineage->>'research_pipeline_input_sha256'
                    IS DISTINCT FROM run_row.artifact_payload->>'pipeline_input_sha256'
               OR lineage->>'feature_lineage_sha256'
                    IS DISTINCT FROM run_row.feature_lineage_sha256
               OR lineage->>'snapshot_bundle_sha256'
                    IS DISTINCT FROM run_row.snapshot_bundle_sha256
               OR lineage->>'source_reproduction_audit_sha256'
                    IS DISTINCT FROM
                        run_row.artifact_payload#>>'{source_reproduction_audit,audit_sha256}'
               OR lineage->'snapshot_bindings' IS DISTINCT FROM bindings
               OR (lineage->>'phase5_policy_id')::uuid
                    IS DISTINCT FROM run_row.phase5_policy_id
               OR (lineage->>'phase5_policy_version')::integer
                    IS DISTINCT FROM run_row.phase5_policy_version
               OR lineage->>'phase5_policy_sha256'
                    IS DISTINCT FROM run_row.phase5_policy_sha256
               OR lineage->>'phase5_fixture_id' IS DISTINCT FROM run_row.phase5_fixture_id
               OR lineage->>'phase5_fixture_sha256'
                    IS DISTINCT FROM run_row.phase5_fixture_sha256
               OR (lineage->>'evaluation_report_id')::uuid
                    IS DISTINCT FROM run_row.evaluation_report_id
               OR lineage->>'evaluation_report_sha256' IS DISTINCT FROM report_sha
               OR lineage->>'phase5_trial_set_sha256' IS DISTINCT FROM
                    run_row.artifact_payload#>>'{phase5_evaluation,phase5_trial_set_sha256}'
               OR lineage->'gate_codes' IS DISTINCT FROM gate_codes
               OR lineage->>'code_version_git_sha'
                    IS DISTINCT FROM run_row.artifact_payload->>'code_version_git_sha'
               OR (lineage->>'random_seed')::bigint IS DISTINCT FROM
                    (run_row.artifact_payload->>'random_seed')::bigint
               OR (lineage->>'raw_trial_count')::integer IS DISTINCT FROM
                    (run_row.artifact_payload#>>'{phase5_evaluation,raw_trial_count}')::integer
               OR (lineage->>'effective_trial_count')::numeric IS DISTINCT FROM
                    (run_row.artifact_payload#>>
                        '{phase5_evaluation,effective_trial_count}')::numeric THEN
                RAISE EXCEPTION 'Phase 7 complete Phase 6 lineage mismatch';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        f"""
        CREATE FUNCTION validate_phase7_assessment_completeness()
        RETURNS trigger AS $$
        DECLARE
            checked_assessment_id uuid;
            assessment_row approval_assessments%ROWTYPE;
            actual_codes jsonb;
            actual_payloads jsonb;
            actual_reasons jsonb;
            actual_count bigint;
            minimum_ordinal integer;
            maximum_ordinal integer;
            all_pass boolean;
            revoked_ids jsonb;
            revocation_clear_status text;
            currentness_states jsonb;
            expected_revocation_set_sha256 text;
            expected_currentness_state_sha256 text;
            expected_request_fingerprint_sha256 text;
        BEGIN
            IF TG_TABLE_NAME = 'approval_assessments' THEN
                checked_assessment_id := NEW.assessment_id;
            ELSE
                checked_assessment_id := NEW.assessment_id;
            END IF;

            IF TG_TABLE_NAME = 'approval_checks'
               AND EXISTS (
                    SELECT 1 FROM approval_assessments AS current_assessment
                    WHERE current_assessment.assessment_id = checked_assessment_id
                      AND current_assessment.xmin = pg_current_xact_id()::xid
               ) THEN
                RETURN NEW;
            END IF;

            SELECT * INTO assessment_row
            FROM approval_assessments
            WHERE assessment_id = checked_assessment_id;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'Phase 7 assessment completeness target is missing';
            END IF;

            SELECT count(*), min(ordinal), max(ordinal),
                   COALESCE(jsonb_agg(to_jsonb(code) ORDER BY ordinal), '[]'::jsonb),
                   COALESCE(jsonb_agg(payload ORDER BY ordinal), '[]'::jsonb),
                   bool_and(status = 'PASS')
            INTO actual_count, minimum_ordinal, maximum_ordinal,
                 actual_codes, actual_payloads, all_pass
            FROM approval_checks
            WHERE assessment_id = checked_assessment_id;

            IF actual_count <> {len(PHASE7_CHECK_CODES)}
               OR minimum_ordinal <> 1
               OR maximum_ordinal <> {len(PHASE7_CHECK_CODES)}
               OR actual_codes IS DISTINCT FROM {_check_registry_json_sql()}
               OR actual_payloads IS DISTINCT FROM
                    assessment_row.artifact_payload->'checks'
               OR (assessment_row.outcome = 'APPROVED_PAPER') IS DISTINCT FROM all_pass THEN
                RAISE EXCEPTION
                    'Phase 7 assessment requires the exact complete ordered check registry';
            END IF;

            SELECT CASE
                WHEN all_pass THEN '["all_approval_and_risk_checks_passed"]'::jsonb
                ELSE COALESCE(
                    jsonb_agg(DISTINCT to_jsonb(reason_code) ORDER BY to_jsonb(reason_code))
                        FILTER (WHERE status <> 'PASS'),
                    '[]'::jsonb
                )
            END INTO actual_reasons
            FROM approval_checks
            WHERE assessment_id = checked_assessment_id;
            IF actual_reasons IS DISTINCT FROM assessment_row.reason_codes THEN
                RAISE EXCEPTION 'Phase 7 assessment reason registry mismatch';
            END IF;

            SELECT COALESCE(
                jsonb_agg(to_jsonb(revocation_id) ORDER BY revocation_id::text),
                '[]'::jsonb
            ) INTO revoked_ids
            FROM approval_revocations
            WHERE human_authorization_evidence_id =
                    assessment_row.human_authorization_evidence_id;
            IF revoked_ids IS DISTINCT FROM assessment_row.revocation_ids THEN
                RAISE EXCEPTION 'Phase 7 assessment revocation set mismatch';
            END IF;
            SELECT status INTO revocation_clear_status
            FROM approval_checks
            WHERE assessment_id = checked_assessment_id
              AND code = 'REVOCATION_CLEAR';
            IF (jsonb_array_length(revoked_ids) = 0
                    AND revocation_clear_status <> 'PASS')
               OR (jsonb_array_length(revoked_ids) > 0
                    AND revocation_clear_status = 'PASS') THEN
                RAISE EXCEPTION 'Phase 7 revocation check does not match immutable events';
            END IF;

            SELECT phase6_domain_sha256(
                'phase7-authorization-revocation-set-v1',
                COALESCE(
                    jsonb_agg(
                        jsonb_build_object(
                            'revocation_id', revocation_id::text,
                            'artifact_sha256', artifact_sha256,
                            'effective_at_utc', artifact_payload->'effective_at_utc'
                        )
                        ORDER BY revocation_id::text
                    ),
                    '[]'::jsonb
                )
            ) INTO expected_revocation_set_sha256
            FROM approval_revocations
            WHERE human_authorization_evidence_id =
                    assessment_row.human_authorization_evidence_id;
            IF expected_revocation_set_sha256 IS DISTINCT FROM
                    assessment_row.revocation_set_sha256 THEN
                RAISE EXCEPTION 'Phase 7 assessment revocation-set hash mismatch';
            END IF;

            SELECT COALESCE(
                jsonb_agg(
                    jsonb_build_object('code', code, 'status', status)
                    ORDER BY ordinal
                ) FILTER (
                    WHERE code IN (
                        'RESEARCH_PASS',
                        'PHASE6_LINEAGE_COMPLETE',
                        'POLICY_CURRENT',
                        'POLICY_MATCH',
                        'SCOPE_CURRENT',
                        'SCOPE_MATCH',
                        'AUTHORIZATION_CURRENT',
                        'AUTHORIZATION_MATCH',
                        'REVOCATION_CLEAR',
                        'RISK_INPUT_FRESH'
                    )
                ),
                '[]'::jsonb
            ) INTO currentness_states
            FROM approval_checks
            WHERE assessment_id = checked_assessment_id;
            expected_currentness_state_sha256 := phase6_domain_sha256(
                'phase7-approval-currentness-state-v1',
                jsonb_build_object(
                    'lineage_sha256', assessment_row.phase6_lineage_sha256,
                    'policy_sha256', assessment_row.approval_policy_sha256,
                    'scope_sha256', assessment_row.approval_scope_sha256,
                    'authorization_sha256', assessment_row.authorization_sha256,
                    'risk_input_sha256', assessment_row.risk_input_sha256,
                    'revocation_set_sha256', expected_revocation_set_sha256,
                    'states', currentness_states
                )
            );
            IF expected_currentness_state_sha256 IS DISTINCT FROM
                    assessment_row.currentness_state_sha256 THEN
                RAISE EXCEPTION 'Phase 7 assessment currentness-state hash mismatch';
            END IF;

            expected_request_fingerprint_sha256 := phase6_domain_sha256(
                'phase7-approval-assessment-request-v1',
                jsonb_build_object(
                    'request', jsonb_build_object(
                        'research_run_id', assessment_row.research_run_id::text,
                        'approval_policy_version_id',
                            assessment_row.approval_policy_version_id::text,
                        'approval_scope_version_id',
                            assessment_row.approval_scope_version_id::text,
                        'human_authorization_evidence_id',
                            assessment_row.human_authorization_evidence_id::text,
                        'risk_input_id', assessment_row.risk_input_id::text
                    ),
                    'lineage_sha256', assessment_row.phase6_lineage_sha256,
                    'policy_sha256', assessment_row.approval_policy_sha256,
                    'scope_sha256', assessment_row.approval_scope_sha256,
                    'authorization_sha256', assessment_row.authorization_sha256,
                    'risk_input_sha256', assessment_row.risk_input_sha256,
                    'revocation_set_sha256', expected_revocation_set_sha256,
                    'currentness_state_sha256', expected_currentness_state_sha256,
                    'phase7_code_version_git_sha',
                        assessment_row.phase7_code_version_git_sha
                )
            );
            IF expected_request_fingerprint_sha256 IS DISTINCT FROM
                    assessment_row.request_fingerprint_sha256 THEN
                RAISE EXCEPTION 'Phase 7 assessment request fingerprint mismatch';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )


def _install_validation_triggers() -> None:
    for table in PHASE7_TABLES:
        op.execute(
            f"""
            CREATE TRIGGER {table}_00_created_at_utc
            BEFORE INSERT ON {table}
            FOR EACH ROW EXECUTE FUNCTION own_phase7_created_at_utc()
            """
        )
    for table in (
        "approval_scopes",
        "approval_authorizations",
        "approval_risk_inputs",
        "approval_assessments",
    ):
        op.execute(
            f"""
            CREATE TRIGGER {table}_10_research_eligibility
            BEFORE INSERT ON {table}
            FOR EACH ROW EXECUTE FUNCTION validate_phase7_research_eligibility()
            """
        )
    for table in (
        "approval_scopes",
        "approval_authorizations",
        "approval_risk_inputs",
        "approval_assessments",
    ):
        op.execute(
            f"""
            CREATE TRIGGER {table}_20_relationships
            BEFORE INSERT ON {table}
            FOR EACH ROW EXECUTE FUNCTION validate_phase7_evidence_relationships()
            """
        )
    for table in PHASE7_TABLES:
        op.execute(
            f"""
            CREATE TRIGGER {table}_30_payload
            BEFORE INSERT ON {table}
            FOR EACH ROW EXECUTE FUNCTION validate_phase7_payload_consistency()
            """
        )
    op.execute(
        """
        CREATE TRIGGER approval_assessments_40_authorization_lock
        BEFORE INSERT ON approval_assessments
        FOR EACH ROW EXECUTE FUNCTION phase7_lock_authorization_identity()
        """
    )
    op.execute(
        """
        CREATE TRIGGER approval_revocations_40_authorization_lock
        BEFORE INSERT ON approval_revocations
        FOR EACH ROW EXECUTE FUNCTION phase7_lock_authorization_identity()
        """
    )
    op.execute(
        """
        CREATE TRIGGER approval_assessments_50_lineage
        BEFORE INSERT ON approval_assessments
        FOR EACH ROW EXECUTE FUNCTION validate_phase7_assessment_lineage()
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER approval_assessments_complete
        AFTER INSERT ON approval_assessments
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION validate_phase7_assessment_completeness()
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER approval_checks_assessment_complete
        AFTER INSERT ON approval_checks
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION validate_phase7_assessment_completeness()
        """
    )


def _install_append_only_guards() -> None:
    op.execute(
        f"""
        CREATE FUNCTION reject_phase7_approval_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION '{PHASE7_APPEND_ONLY_ERROR}';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    for table in PHASE7_TABLES:
        op.execute(
            f"""
            CREATE TRIGGER {table}_immutable
            BEFORE UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION reject_phase7_approval_mutation()
            """
        )
        op.execute(
            f"""
            CREATE TRIGGER {table}_no_truncate
            BEFORE TRUNCATE ON {table}
            FOR EACH STATEMENT EXECUTE FUNCTION reject_phase7_approval_mutation()
            """
        )


def downgrade() -> None:
    for table in reversed(PHASE7_TABLES):
        op.drop_table(table)
    for function_name in (
        "reject_phase7_approval_mutation()",
        "validate_phase7_assessment_completeness()",
        "validate_phase7_assessment_lineage()",
        "validate_phase7_payload_consistency()",
        "validate_phase7_evidence_relationships()",
        "validate_phase7_research_eligibility()",
        "phase7_lock_authorization_identity()",
        "own_phase7_created_at_utc()",
    ):
        op.execute(f"DROP FUNCTION IF EXISTS {function_name}")
    op.drop_constraint(
        "uq_research_pipeline_run_id_artifact_sha256",
        "research_pipeline_runs",
        type_="unique",
    )
